from __future__ import annotations

import base64
import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from ithildin_api.database import initialize_database
from ithildin_api.node_configuration import NodeConfigurationStore
from ithildin_api.node_configuration_trust import (
    NodeConfigurationTrustTransitionStore,
)
from ithildin_api.nodes import (
    EnrollmentCodeIssuePayload,
    NodeEnrollmentPayload,
    NodeStore,
)
from ithildin_audit_core import AuditWriteError, AuditWriter
from ithildin_schemas import JsonObject, canonical_json

from scripts import (
    local_v1_lv1_003_o4_attempt008_quarantine_revocation as recovery,
)

NODE_ID = "node_" + "a" * 32
TEST_DOCKER = "/private/tmp/ithildin-test-sealed/docker"
IDS = {
    "ithildin-api": "1" * 64,
    "ithildin-ui": "2" * 64,
    "ithildin-node": "3" * 64,
    "hermes": "4" * 64,
}


class MemoryJournal:
    def __init__(self) -> None:
        self.payloads: dict[str, JsonObject] = {}
        self.created: list[str] = []

    def peek(self, event: str) -> JsonObject | None:
        return self.payloads.get(event)

    def record(
        self,
        event: str,
        proposed: JsonObject,
    ) -> tuple[JsonObject, bool]:
        existing = self.payloads.get(event)
        if existing is not None:
            return existing, False
        self.payloads[event] = proposed
        self.created.append(event)
        return proposed, True


def _projection(
    service: str,
    *,
    running: bool,
    container_id: str | None = None,
    image_id: str | None = None,
    project: str = recovery.PROJECT,
) -> str:
    contract = recovery.port_release.SERVICES[service]
    ports: JsonObject = {}
    if running and contract.container_port is not None:
        ports = {
            contract.container_port: [
                {
                    "HostIp": "127.0.0.1",
                    "HostPort": contract.host_port,
                }
            ]
        }
    values: list[object] = [
        container_id or IDS[service],
        image_id or recovery.port_release.SERVICES[service].image_id,
        project,
        service,
        running,
        "running" if running else "exited",
        ports,
    ]
    return "\t".join(json.dumps(value, separators=(",", ":")) for value in values) + "\n"


class FakeDockerExecutor:
    def __init__(self) -> None:
        self._known_ids: set[str] = set()
        self.running = {service: True for service in recovery.SERVICES}
        self.stop_calls: list[tuple[str, str]] = []
        self.services = list(recovery.SERVICES)
        self.image_overrides: dict[str, str] = {}
        self.project_overrides: dict[str, str] = {}

    def bind_ids(self, values: set[str]) -> None:
        if self._known_ids:
            raise AssertionError("ids already bound")
        self._known_ids = set(values)

    def query(self) -> recovery.port_release.CommandResult:
        return recovery.port_release.CommandResult(
            0,
            "".join(f"{IDS[service]}\n" for service in self.services),
        )

    def inspect(
        self,
        container_id: str,
    ) -> recovery.port_release.CommandResult:
        service = next(
            (candidate for candidate, expected_id in IDS.items() if expected_id == container_id),
            "",
        )
        if not service:
            return recovery.port_release.CommandResult(1, "")
        return recovery.port_release.CommandResult(
            0,
            _projection(
                service,
                running=self.running[service],
                image_id=self.image_overrides.get(service),
                project=self.project_overrides.get(
                    service,
                    recovery.PROJECT,
                ),
            ),
        )

    def stop(
        self,
        service: str,
        container_id: str,
    ) -> recovery.port_release.CommandResult:
        self.stop_calls.append((service, container_id))
        self.running[service] = False
        return recovery.port_release.CommandResult(0, "")


def _reconciliation_documents(
    *,
    node_id: str = NODE_ID,
    classification: str = "identity_bound_active_quarantine_required",
) -> tuple[JsonObject, JsonObject]:
    identity_digest = recovery._sha256(  # noqa: SLF001
        b"ITHILDIN-ATTEMPT008-NODE-ID-V1\x00" + node_id.encode()
    )
    consumed: JsonObject = {
        "schema_version": "1",
        "record_type": "attempt008_node_identity_reconciliation_consumption",
        "reconciliation_id": recovery.identity.RECONCILIATION_ID,
        "candidate_commit": recovery.RECONCILIATION_COMMIT,
        "candidate_tree": recovery.RECONCILIATION_TREE,
        "run_id": recovery.RUN_ID,
        "compose_project": recovery.PROJECT,
        "consumed_before_database_open": True,
        "attempt_budget": 0,
        "retry_authorized": False,
        "release_allowed": False,
        "uat_complete": False,
    }
    result: JsonObject = {
        "schema_version": "1",
        "record_type": "attempt008_node_identity_reconciliation_result",
        "reconciliation_id": recovery.identity.RECONCILIATION_ID,
        "candidate_commit": recovery.RECONCILIATION_COMMIT,
        "candidate_tree": recovery.RECONCILIATION_TREE,
        "database_snapshot_size": 4096,
        "database_snapshot_sha256": "sha256:" + "b" * 64,
        "database_source_unchanged": True,
        "database_sidecars_absent": True,
        "classification": classification,
        "node_id": node_id,
        "node_identity_digest": identity_digest,
        "principal_id": f"agent:node.{node_id}",
        "workspace_id": recovery.WORKSPACE_ID,
        "display_name": recovery.DISPLAY_NAME,
        "descriptor_digest": recovery.EXPECTED_DESCRIPTOR_DIGEST,
        "status": "enrolled",
        "evidence_status": "complete",
        "enrolled_at": "2026-07-26T00:20:00+00:00",
        "revoked_at": None,
        "quarantine_confirmed": False,
        "revocation_authorized": False,
        "cleanup_authorized": False,
        "successor_o4_authorized": False,
        "release_allowed": False,
        "uat_complete": False,
    }
    return consumed, result


def _mkdir_private(path: Path) -> None:
    path.mkdir(mode=0o700)
    path.chmod(0o700)


def _always_quiesced() -> None:
    return None


def _storage_fixture(
    tmp_path: Path,
) -> tuple[
    recovery.ReceiptSession,
    recovery.StorageAliases,
    recovery.ReconciledIdentity,
]:
    repo_root = tmp_path / "repo"
    _mkdir_private(repo_root)
    current = repo_root
    for component in recovery.RUNTIME_VAR_COMPONENTS:
        current = current / component
        _mkdir_private(current)
    database_directory = current / recovery.DATABASE_DIRECTORY
    audit_directory = current / recovery.AUDIT_DIRECTORY
    _mkdir_private(database_directory)
    _mkdir_private(audit_directory)
    database_path = database_directory / recovery.DATABASE_NAME
    audit_path = audit_directory / recovery.AUDIT_NAME

    initialize_database(database_path)
    node_store = NodeStore(database_path)
    node_store.initialize()
    NodeConfigurationStore(database_path).initialize()
    NodeConfigurationTrustTransitionStore(database_path).initialize()
    writer = AuditWriter(database_path, audit_path)
    writer.initialize()
    audit_path.write_bytes(b"")

    now = datetime(2026, 7, 26, 0, 20, tzinfo=UTC)
    issued = node_store.issue_enrollment_code(
        EnrollmentCodeIssuePayload(
            workspace_id=recovery.WORKSPACE_ID,
            display_name=recovery.DISPLAY_NAME,
        ),
        expires_in_seconds=600,
        now=now,
    )
    node_store.mark_enrollment_code_evidence_complete(issued.code_id)
    record = node_store.enroll(
        NodeEnrollmentPayload(
            enrollment_code=issued.enrollment_code,
            public_key=base64.b64encode(b"\x01" * 32).decode(),
            protocol_version="1",
            node_version="0.1.0",
            runner_adapter="hermes",
            deployment_topology="docker_sidecar",
        ),
        now=now,
    )
    node_store.mark_node_evidence_complete(record.node_id)
    assert record.descriptor_hash == recovery.EXPECTED_DESCRIPTOR_DIGEST
    database_path.chmod(0o600)
    audit_path.chmod(0o600)
    snapshot = database_path.read_bytes()
    projected = recovery.identity.project_identity(snapshot)
    assert projected["classification"] == "identity_bound_active_quarantine_required"

    receipt_base = repo_root / "var/local-v1-lv1-003-o4-reconciliation-receipts"
    _mkdir_private(receipt_base)
    receipt_directory = receipt_base / recovery.RECOVERY_RECEIPT_DIRECTORY
    _mkdir_private(receipt_directory)
    receipt_fd = os.open(
        receipt_directory,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
    )
    session = recovery.ReceiptSession(
        repo_root=repo_root,
        receipt_fd=receipt_fd,
        held=[receipt_fd],
        candidate_commit="c" * 40,
        candidate_tree="d" * 40,
    )
    aliases = recovery.StorageAliases.bind(session)
    reconciled = recovery.ReconciledIdentity(
        node_id=record.node_id,
        principal_id=record.principal_id,
        identity_digest=str(projected["node_identity_digest"]),
        database_size=len(snapshot),
        database_digest=recovery._sha256(snapshot),  # noqa: SLF001
    )
    return session, aliases, reconciled


def test_authorization_is_closed_six_path_and_no_new_power() -> None:
    record = recovery._expected_authorization()  # noqa: SLF001
    assert len(recovery.CANDIDATE_PATH_ALLOWLIST) == 6
    assert record["candidate_path_allowlist"] == recovery.CANDIDATE_PATH_ALLOWLIST
    assert record["attempt_budget"] == 1
    assert record["retry_authorized"] is False
    assert record["same_operation_resume_authorized"] is True
    assert record["single_active_invocation_required"] is True
    assert record["review_binding"] == {
        "git_tag": recovery.REVIEW_TAG,
        "required_for_live_execution": True,
        "tag_move_authorized": False,
    }
    assert record["audit_lifecycle_repair_authorized"] is False
    assert record["cleanup_authorized"] is False
    assert record["successor_o4_authorized"] is False
    assert record["tool_count"] == 24
    assert len(list((recovery.ROOT / "tool-manifests").glob("*.yaml"))) == 24
    assert record["release_allowed"] is False
    assert record["uat_complete"] is False
    assert recovery.AUTHORITY_TRUE == {
        "descriptor_bound_storage_aliases",
        "exact_project_container_inspection",
        "exact_project_service_stop",
        "exact_reconciliation_receipt_validation",
        "exact_tracked_artifact_validation",
        "owner_only_recovery_receipts",
        "reviewed_candidate_git_ref_binding",
        "same_operation_resume",
        "single_active_invocation_lock",
        "single_node_offline_revocation",
        "single_node_revocation_audit",
    }
    assert {
        "container_start",
        "container_restart",
        "container_exec",
        "container_deletion",
        "compose_use",
        "project_down",
        "arbitrary_sql",
        "database_repair",
        "evidence_deletion",
        "runtime_cleanup",
        "successor_o4_attempt",
        "release",
        "uat",
    } <= recovery.AUTHORITY_FALSE
    recovery.validate_authorization(recovery.ROOT)


def test_release_check_parser_sees_authoritative_target_before_compatibility_alias() -> None:
    makefile = (recovery.ROOT / "Makefile").read_text()
    release_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    assert "manifest-lock-check" in release_body
    assert "release-guardrails" in release_body
    assert "tool-surface-invariant-gate" in release_body
    assert "docs-site" in release_body
    assert makefile.index("\nrelease-check:") < makefile.index(
        "\nlocal-v1-lv1-003-o4-attempt008-port-release-check:"
    )


def test_reconciliation_validation_is_closed_and_secret_safe() -> None:
    consumed, result = _reconciliation_documents()
    reconciled = recovery.validate_reconciliation_documents(
        consumed,
        result,
    )
    assert reconciled.node_id == NODE_ID
    assert reconciled.principal_id == f"agent:node.{NODE_ID}"
    assert reconciled.identity_digest == result["node_identity_digest"]

    result["classification"] = "identity_bound_revoked"
    with pytest.raises(
        recovery.RecoveryError,
        match="reconciliation_receipt_invalid",
    ):
        recovery.validate_reconciliation_documents(consumed, result)

    with pytest.raises(
        recovery.RecoveryError,
        match="reconciliation_receipt_invalid",
    ):
        recovery._closed_json(  # noqa: SLF001
            b'{"node_id":"first","node_id":"second"}',
            error_code="reconciliation_receipt_invalid",
        )


def test_bound_receipt_read_rejects_symlink_and_hardlink(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    _mkdir_private(repo_root)
    components = ("var", "receipts", "lane")
    current = repo_root
    for component in components:
        current = current / component
        _mkdir_private(current)
    content = b'{"closed":true}\n'
    leaf = current / "result.json"
    leaf.write_bytes(content)
    leaf.chmod(0o600)
    digest = recovery._sha256(content)  # noqa: SLF001

    assert (
        recovery._read_bound_leaf(  # noqa: SLF001
            repo_root,
            components,
            "result.json",
            expected_size=len(content),
            expected_digest=digest,
        )
        == content
    )

    leaf.rename(current / "source.json")
    leaf.symlink_to("source.json")
    with pytest.raises(
        recovery.RecoveryError,
        match="reconciliation_receipt_invalid",
    ):
        recovery._read_bound_leaf(  # noqa: SLF001
            repo_root,
            components,
            "result.json",
            expected_size=len(content),
            expected_digest=digest,
        )

    leaf.unlink()
    os.link(current / "source.json", leaf)
    with pytest.raises(
        recovery.RecoveryError,
        match="reconciliation_receipt_invalid",
    ):
        recovery._read_bound_leaf(  # noqa: SLF001
            repo_root,
            components,
            "result.json",
            expected_size=len(content),
            expected_digest=digest,
        )


def test_static_report_does_not_enter_live_seams(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        recovery,
        "validate_static_candidate",
        lambda _repo_root: ("c" * 40, "d" * 40),
    )
    monkeypatch.setattr(
        recovery,
        "validate_review_binding",
        lambda _repo_root, *, candidate_commit, candidate_tree: None,
    )

    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("live seam entered")

    monkeypatch.setattr(recovery, "_read_bound_leaf", forbidden)
    monkeypatch.setattr(
        recovery.port_release,
        "_local_docker_socket",
        forbidden,
    )
    monkeypatch.setattr(recovery.StorageAliases, "bind", forbidden)

    report = recovery.build_report(recovery.ROOT)

    assert report["static_candidate_valid"] is True
    assert report["review_binding_valid"] is True
    assert report["execution_available"] is True
    assert report["static_validation_reads_runtime"] is False


def test_review_binding_requires_exact_fixed_tag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commit = "c" * 40
    tree = "d" * 40

    def exact_tag(
        _repo_root: Path,
        *arguments: str,
    ) -> str:
        ref = arguments[-1]
        if ref == f"refs/tags/{recovery.REVIEW_TAG}^{{commit}}":
            return commit
        if ref == f"refs/tags/{recovery.REVIEW_TAG}^{{tree}}":
            return tree
        raise AssertionError(arguments)

    monkeypatch.setattr(recovery, "_git", exact_tag)
    recovery.validate_review_binding(
        recovery.ROOT,
        candidate_commit=commit,
        candidate_tree=tree,
    )
    with pytest.raises(recovery.RecoveryError, match="review_binding_invalid"):
        recovery.validate_review_binding(
            recovery.ROOT,
            candidate_commit="e" * 40,
            candidate_tree=tree,
        )


def test_operation_lock_rejects_concurrent_invocation(tmp_path: Path) -> None:
    receipt = tmp_path / "receipt"
    _mkdir_private(receipt)
    receipt_fd = os.open(
        receipt,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
    )
    first = -1
    try:
        first = recovery._acquire_operation_lock(receipt_fd)  # noqa: SLF001
        with pytest.raises(
            recovery.RecoveryError,
            match="operation_already_active",
        ):
            recovery._acquire_operation_lock(receipt_fd)  # noqa: SLF001
    finally:
        if first >= 0:
            os.close(first)
        os.close(receipt_fd)


def test_quarantine_plan_has_only_exact_query_inspect_and_stop() -> None:
    plan = recovery.QuarantinePlan(TEST_DOCKER)
    query = plan.query()
    assert query == (
        TEST_DOCKER,
        "ps",
        "--all",
        "--quiet",
        "--no-trunc",
        "--filter",
        f"label=com.docker.compose.project={recovery.PROJECT}",
    )
    for service in recovery.SERVICES:
        container_id = IDS[service]
        inspect = plan.inspect(container_id)
        stop = plan.stop(service, container_id)
        assert inspect[1:3] == ("container", "inspect")
        assert stop == (
            TEST_DOCKER,
            "container",
            "stop",
            "--time",
            "10",
            container_id,
        )
        assert not {
            "start",
            "restart",
            "exec",
            "rm",
            "compose",
            "down",
        }.intersection(inspect + stop)


def test_quiescence_stops_exact_four_once_and_resumes_without_duplicate() -> None:
    executor = FakeDockerExecutor()
    journal = MemoryJournal()

    recorded = recovery.quiesce_project(executor, journal)  # type: ignore[arg-type]

    assert set(recorded) == set(recovery.SERVICES)
    assert [service for service, _container in executor.stop_calls] == list(recovery.SERVICES)
    assert not any(executor.running.values())
    initial_stop_count = len(executor.stop_calls)

    resumed = recovery.quiesce_project(executor, journal)  # type: ignore[arg-type]

    assert resumed == recorded
    assert len(executor.stop_calls) == initial_stop_count
    assert all(
        journal.payloads[f"{service}-stop-result"]["stop_issued"] is True
        for service in recovery.SERVICES
    )


@pytest.mark.parametrize(
    "mutation",
    ["missing", "wrong_image", "wrong_project"],
)
def test_quiescence_rejects_changed_project(mutation: str) -> None:
    executor = FakeDockerExecutor()
    if mutation == "missing":
        executor.services.remove("hermes")
    elif mutation == "wrong_image":
        executor.image_overrides["ithildin-api"] = "sha256:" + "f" * 64
    else:
        executor.project_overrides["ithildin-api"] = "other-project"

    with pytest.raises(recovery.RecoveryError):
        recovery.quiesce_project(  # type: ignore[arg-type]
            executor,
            MemoryJournal(),  # type: ignore[arg-type]
        )
    assert executor.stop_calls == []


def test_existing_stop_result_never_reissues_stop_after_restart() -> None:
    executor = FakeDockerExecutor()
    journal = MemoryJournal()
    recovery.quiesce_project(executor, journal)  # type: ignore[arg-type]
    stop_count = len(executor.stop_calls)
    executor.running["ithildin-api"] = True

    with pytest.raises(
        recovery.RecoveryError,
        match="project_restarted_after_quiescence",
    ):
        recovery.quiesce_project(executor, journal)  # type: ignore[arg-type]
    assert len(executor.stop_calls) == stop_count


def test_durable_journal_resumes_legal_prefix_and_rejects_tamper(
    tmp_path: Path,
) -> None:
    receipt_directory = tmp_path / "receipt"
    _mkdir_private(receipt_directory)
    receipt_fd = os.open(
        receipt_directory,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
    )
    session = recovery.ReceiptSession(
        repo_root=tmp_path,
        receipt_fd=receipt_fd,
        held=[receipt_fd],
        candidate_commit="c" * 40,
        candidate_tree="d" * 40,
    )
    journal = recovery.DurableJournal(session)
    first = {
        "identity_digest": "sha256:" + "a" * 64,
    }
    assert journal.record(
        "identity-receipts-validated",
        first,
    ) == (first, True)
    journal.close()

    resumed = recovery.DurableJournal(session)
    assert resumed.peek("identity-receipts-validated") == first
    assert resumed.record(
        "identity-receipts-validated",
        {"wrong": True},
    ) == (first, False)
    resumed.close()

    journal_path = (
        receipt_directory / recovery.JOURNAL_DIRECTORY / "0001-identity-receipts-validated.json"
    )
    document = json.loads(journal_path.read_text())
    document["event"] = "tampered"
    journal_path.write_text(canonical_json(document) + "\n")
    journal_path.chmod(0o600)
    tampered = recovery.DurableJournal(session)
    with pytest.raises(recovery.RecoveryError, match="journal_invalid"):
        tampered.peek("identity-receipts-validated")
    tampered.close()
    session.close()


def test_storage_transition_revokes_once_audits_once_and_emits_no_raw_id(
    tmp_path: Path,
) -> None:
    session, aliases, reconciled = _storage_fixture(tmp_path)
    journal = MemoryJournal()
    quiescence_checks = 0

    def count_quiescence_check() -> None:
        nonlocal quiescence_checks
        quiescence_checks += 1

    try:
        with sqlite3.connect(aliases.database_path) as connection:
            node_columns = [str(row[1]) for row in connection.execute("PRAGMA table_info(nodes)")]
            before_node = dict(
                zip(
                    node_columns,
                    connection.execute(
                        "SELECT * FROM nodes WHERE node_id = ?",
                        (reconciled.node_id,),
                    ).fetchone(),
                    strict=True,
                )
            )
            before_enrollment = connection.execute("SELECT * FROM node_enrollment_codes").fetchall()
        result = recovery.execute_storage_transition(  # type: ignore[arg-type]
            aliases,
            reconciled,
            journal,  # type: ignore[arg-type]
            count_quiescence_check,
        )
        assert quiescence_checks >= 7
        record = NodeStore(aliases.database_path).get(reconciled.node_id)
        assert record.status == "revoked"
        assert record.evidence_status == "complete"
        events = AuditWriter(
            aliases.database_path,
            aliases.audit_path,
        ).list_events(limit=10)
        assert len(events) == 1
        assert events[0]["event_type"] == "node.revoked"
        assert result["node_status"] == "revoked"
        assert result["node_evidence_status"] == "complete"
        assert result["cleanup_completed"] is False
        assert result["successor_o4_authorized"] is False
        assert NODE_ID not in canonical_json(journal.payloads)
        assert reconciled.node_id not in canonical_json(result)
        with sqlite3.connect(aliases.database_path) as connection:
            after_node = dict(
                zip(
                    node_columns,
                    connection.execute(
                        "SELECT * FROM nodes WHERE node_id = ?",
                        (reconciled.node_id,),
                    ).fetchone(),
                    strict=True,
                )
            )
            after_enrollment = connection.execute("SELECT * FROM node_enrollment_codes").fetchall()
        changed_node_columns = {
            column for column in node_columns if before_node[column] != after_node[column]
        }
        assert changed_node_columns == {
            "status",
            "updated_at",
            "revoked_at",
        }
        assert before_node["evidence_status"] == "complete"
        assert after_node["evidence_status"] == "complete"
        assert before_enrollment == after_enrollment
    finally:
        aliases.close()
        session.close()


def test_storage_transition_resumes_after_revoke_without_duplicate_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session, aliases, reconciled = _storage_fixture(tmp_path)
    journal = MemoryJournal()
    original_write = AuditWriter.write_event

    def fail_before_audit(
        self: AuditWriter,
        **_kwargs: Any,
    ) -> Any:
        raise AuditWriteError("synthetic interruption")

    try:
        monkeypatch.setattr(AuditWriter, "write_event", fail_before_audit)
        with pytest.raises(
            recovery.RecoveryError,
            match="audit_lifecycle_recovery_required",
        ):
            recovery.execute_storage_transition(  # type: ignore[arg-type]
                aliases,
                reconciled,
                journal,  # type: ignore[arg-type]
                _always_quiesced,
            )
        pending = NodeStore(aliases.database_path).get(reconciled.node_id)
        assert pending.status == "revoked"
        assert pending.evidence_status == "pending"

        monkeypatch.setattr(AuditWriter, "write_event", original_write)
        result = recovery.execute_storage_transition(  # type: ignore[arg-type]
            aliases,
            reconciled,
            journal,  # type: ignore[arg-type]
            _always_quiesced,
        )
        assert result["node_evidence_status"] == "complete"
        events = AuditWriter(
            aliases.database_path,
            aliases.audit_path,
        ).list_events(limit=10)
        assert len(events) == 1
    finally:
        aliases.close()
        session.close()


def test_audit_orphan_remains_terminal_and_node_stays_pending(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session, aliases, reconciled = _storage_fixture(tmp_path)
    journal = MemoryJournal()

    def fail_before_audit(
        self: AuditWriter,
        **_kwargs: Any,
    ) -> Any:
        raise AuditWriteError("synthetic interruption")

    try:
        monkeypatch.setattr(AuditWriter, "write_event", fail_before_audit)
        with pytest.raises(recovery.RecoveryError):
            recovery.execute_storage_transition(  # type: ignore[arg-type]
                aliases,
                reconciled,
                journal,  # type: ignore[arg-type]
                _always_quiesced,
            )
        aliases.audit_path.write_bytes(b'{"orphan":true}\n')
        with pytest.raises(
            recovery.RecoveryError,
            match="audit_lifecycle_recovery_required",
        ):
            recovery.execute_storage_transition(  # type: ignore[arg-type]
                aliases,
                reconciled,
                journal,  # type: ignore[arg-type]
                _always_quiesced,
            )
        pending = NodeStore(aliases.database_path).get(reconciled.node_id)
        assert pending.status == "revoked"
        assert pending.evidence_status == "pending"
        assert aliases.audit_path.read_bytes() == b'{"orphan":true}\n'
    finally:
        aliases.close()
        session.close()


def test_storage_aliases_reject_directory_replacement(tmp_path: Path) -> None:
    session, aliases, _reconciled = _storage_fixture(tmp_path)
    database_directory = (
        session.repo_root / Path(*recovery.RUNTIME_VAR_COMPONENTS) / recovery.DATABASE_DIRECTORY
    )
    moved = database_directory.with_name("db-moved")
    try:
        database_directory.rename(moved)
        _mkdir_private(database_directory)
        with pytest.raises(
            recovery.RecoveryError,
            match="storage_identity_changed",
        ):
            aliases.revalidate()
    finally:
        aliases.close()
        session.close()


def test_storage_aliases_reject_sqlite_sidecar(tmp_path: Path) -> None:
    session, aliases, _reconciled = _storage_fixture(tmp_path)
    sidecar = (
        session.repo_root
        / Path(*recovery.RUNTIME_VAR_COMPONENTS)
        / recovery.DATABASE_DIRECTORY
        / f"{recovery.DATABASE_NAME}-wal"
    )
    try:
        sidecar.write_bytes(b"synthetic")
        sidecar.chmod(0o600)
        with pytest.raises(recovery.RecoveryError):
            aliases.revalidate()
    finally:
        aliases.close()
        session.close()


def test_ambient_authority_environment_is_rejected() -> None:
    with pytest.raises(
        recovery.RecoveryError,
        match="ambient_authority_environment_rejected",
    ):
        recovery._reject_ambient_authority(  # noqa: SLF001
            {"DOCKER_HOST": "unix:///allowed", "API_TOKEN": "secret"}
        )


def test_public_main_never_prints_raw_node_identity(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run(
        _repo_root: Path = recovery.ROOT,
        *,
        environment: Any = None,
    ) -> JsonObject:
        del environment
        return {
            "status": "completed",
            "identity_digest": "sha256:" + "a" * 64,
        }

    monkeypatch.setattr(recovery, "run_live", fake_run)
    assert recovery.main([]) == 0
    output = capsys.readouterr().out
    assert output == ("attempt008_quarantine_revocation_status: completed\n")
    assert NODE_ID not in output


def test_live_refuses_invalid_static_candidate_before_consumption(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        recovery,
        "build_report",
        lambda _repo_root: {
            "static_candidate_valid": False,
            "execution_available": False,
        },
    )

    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("live action entered")

    monkeypatch.setattr(recovery, "consume_or_resume", forbidden)
    monkeypatch.setattr(recovery, "read_reconciled_identity", forbidden)
    monkeypatch.setattr(
        recovery.port_release,
        "_local_docker_socket",
        forbidden,
    )

    with pytest.raises(
        recovery.RecoveryError,
        match="quarantine_revocation_not_authorized",
    ):
        recovery.run_live(recovery.ROOT, environment={})


def test_source_contains_no_start_cleanup_or_successor_authority() -> None:
    source = (recovery.ROOT / recovery.SCRIPT_PATH).read_text()
    makefile = (recovery.ROOT / "Makefile").read_text()
    assert ".start(" not in source
    assert 'container", "start' not in source
    assert 'container", "restart' not in source
    assert 'container", "exec' not in source
    assert 'compose", "down' not in source
    assert "NodeStore.initialize" not in source
    assert "AuditWriter.initialize" not in source
    assert 'successor_o4_authorized": True' not in source
    assert 'release_allowed": True' not in source
    assert 'uat_complete": True' not in source
    live_target = makefile.partition(f"\n{recovery.RUN_TARGET}:\n")[2].partition("\n\n")[0]
    assert "uv run --offline --frozen python -m" in live_target

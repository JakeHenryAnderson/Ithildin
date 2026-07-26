from __future__ import annotations

import base64
import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest
from ithildin_api.database import initialize_database
from ithildin_api.node_configuration import NodeConfigurationStore
from ithildin_api.node_configuration_trust import (
    NodeConfigurationTrustTransitionStore,
)
from ithildin_api.nodes import (
    EnrollmentCodeIssuePayload,
    NodeConflictError,
    NodeEnrollmentPayload,
    NodeStore,
)
from ithildin_audit_core import AuditWriteError, AuditWriter
from ithildin_schemas import JsonObject, canonical_json

from scripts import (
    local_v1_lv1_003_o4_attempt008_node_identity_reconciliation as identity,
)
from scripts import (
    local_v1_lv1_003_o4_attempt008_port_release as port_release,
)
from scripts import (
    local_v1_lv1_003_o4_attempt008_quarantine_revocation as quarantine,
)
from scripts import (
    local_v1_lv1_003_o4_attempt008_two_container_revocation as recovery,
)

NODE_ID = "node_" + "a" * 32


class MemoryJournal:
    def __init__(self) -> None:
        self.payloads: dict[str, JsonObject] = {}

    def peek(self, event: str) -> JsonObject | None:
        return self.payloads.get(event)

    def record(
        self,
        event: str,
        proposed_payload: JsonObject,
    ) -> tuple[JsonObject, bool]:
        existing = self.payloads.get(event)
        if existing is not None:
            return existing, False
        self.payloads[event] = proposed_payload
        return proposed_payload, True


def _mkdir_private(path: Path) -> None:
    path.mkdir(mode=0o700)
    path.chmod(0o700)


def _always_quiesced() -> None:
    return None


def _storage_fixture(
    tmp_path: Path,
) -> tuple[
    recovery.ReceiptSession,
    quarantine.StorageAliases,
    quarantine.ReconciledIdentity,
]:
    repo_root = tmp_path / "repo"
    _mkdir_private(repo_root)
    current = repo_root
    for component in quarantine.RUNTIME_VAR_COMPONENTS:
        current = current / component
        _mkdir_private(current)
    database_directory = current / quarantine.DATABASE_DIRECTORY
    audit_directory = current / quarantine.AUDIT_DIRECTORY
    _mkdir_private(database_directory)
    _mkdir_private(audit_directory)
    database_path = database_directory / quarantine.DATABASE_NAME
    audit_path = audit_directory / quarantine.AUDIT_NAME

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
            workspace_id=quarantine.WORKSPACE_ID,
            display_name=quarantine.DISPLAY_NAME,
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
    assert record.descriptor_hash == quarantine.EXPECTED_DESCRIPTOR_DIGEST
    database_path.chmod(0o600)
    audit_path.chmod(0o600)
    snapshot = database_path.read_bytes()
    projected = identity.project_identity(snapshot)
    assert projected["classification"] == "identity_bound_active_quarantine_required"

    receipt_base = repo_root / "var/local-v1-lv1-003-o4-reconciliation-receipts"
    _mkdir_private(receipt_base)
    receipt_directory = receipt_base / recovery.RECEIPT_DIRECTORY
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
    aliases = quarantine.StorageAliases.bind(cast(Any, session))
    reconciled = quarantine.ReconciledIdentity(
        node_id=record.node_id,
        principal_id=record.principal_id,
        identity_digest=cast(str, projected["node_identity_digest"]),
        database_size=len(snapshot),
        database_digest=quarantine._sha256(snapshot),  # noqa: SLF001
    )
    return session, aliases, reconciled


def _projection(
    service: str,
    *,
    running: bool = False,
    container_id: str | None = None,
    image_id: str | None = None,
    projected_service: str | None = None,
    status: str | None = None,
    ports: JsonObject | None = None,
    project: str = recovery.PROJECT,
) -> str:
    expected_id, expected_image = recovery.EXPECTED_CONTAINERS[service]
    values: list[object] = [
        container_id or expected_id,
        image_id or expected_image,
        project,
        projected_service or service,
        running,
        status or ("running" if running else "exited"),
        {} if ports is None else ports,
    ]
    return "\t".join(json.dumps(value, separators=(",", ":")) for value in values) + "\n"


class FakeObservationExecutor:
    def __init__(self) -> None:
        self.services = ["ithildin-api", "ithildin-ui"]
        self.running: dict[str, bool] = {service: False for service in self.services}
        self.image_overrides: dict[str, str] = {}
        self.id_overrides: dict[str, str] = {}
        self.service_overrides: dict[str, str] = {}
        self.status_overrides: dict[str, str] = {}
        self.port_overrides: dict[str, JsonObject] = {}
        self.project_overrides: dict[str, str] = {}
        self.extra_ids: list[str] = []

    def query(self) -> port_release.CommandResult:
        return port_release.CommandResult(
            0,
            "".join(
                f"{self.id_overrides.get(service, recovery.EXPECTED_CONTAINERS[service][0])}\n"
                for service in self.services
            )
            + "".join(f"{container_id}\n" for container_id in self.extra_ids),
        )

    def inspect(self, container_id: str) -> port_release.CommandResult:
        service = next(
            (
                candidate
                for candidate in self.services
                if self.id_overrides.get(
                    candidate,
                    recovery.EXPECTED_CONTAINERS[candidate][0],
                )
                == container_id
            ),
            "",
        )
        if not service:
            return port_release.CommandResult(1, "")
        return port_release.CommandResult(
            0,
            _projection(
                service,
                running=self.running[service],
                container_id=container_id,
                image_id=self.image_overrides.get(service),
                projected_service=self.service_overrides.get(service),
                status=self.status_overrides.get(service),
                ports=self.port_overrides.get(service),
                project=self.project_overrides.get(
                    service,
                    recovery.PROJECT,
                ),
            ),
        )


def test_authorization_and_failed_predecessor_closure_are_closed() -> None:
    authorization = recovery._expected_authorization()  # noqa: SLF001
    closure = recovery._expected_predecessor_closure()  # noqa: SLF001
    assert len(recovery.CANDIDATE_PATH_ALLOWLIST) == 8
    assert authorization["container_stop_authorized"] is False
    assert authorization["docker_mutation_authorized"] is False
    assert authorization["attempt_budget"] == 1
    assert authorization["retry_authorized"] is False
    assert authorization["same_operation_resume_authorized"] is True
    assert authorization["generic_container_absence_claimed"] is False
    assert authorization["generic_process_absence_claimed"] is False
    assert authorization["cleanup_authorized"] is False
    assert authorization["successor_o4_authorized"] is False
    assert authorization["tool_count"] == 24
    assert authorization["release_allowed"] is False
    assert authorization["uat_complete"] is False
    assert closure["record_status"] == "CONSUMED_FAILED_CLOSED"
    assert closure["invocations"] == [
        {
            "sequence": 1,
            "result": "docker_trust_boundary_invalid",
            "last_durable_stage": "identity-receipts-validated",
            "docker_command_executed": False,
            "storage_mutation_executed": False,
        },
        {
            "sequence": 2,
            "result": "project_container_set_invalid",
            "last_durable_stage": "identity-receipts-validated",
            "exact_project_query_executed": True,
            "docker_mutation_executed": False,
            "storage_mutation_executed": False,
        },
    ]
    recovery.validate_tracked_records(recovery.ROOT)


def test_static_report_requires_fixed_review_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        recovery,
        "validate_static_candidate",
        lambda _root: ("c" * 40, "d" * 40),
    )

    def missing(_root: Path, *, candidate_commit: str, candidate_tree: str) -> None:
        del candidate_commit, candidate_tree
        raise recovery.RecoveryError("review_binding_invalid")

    monkeypatch.setattr(recovery, "validate_review_binding", missing)
    report = recovery.build_report()
    assert report["static_candidate_valid"] is True
    assert report["review_binding_valid"] is False
    assert report["execution_available"] is False
    assert report["attempt_budget"] == 0


def test_predecessor_receipt_validation_is_exact_and_absence_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    current = repo_root
    current.mkdir(mode=0o700)
    for component in recovery.PREDECESSOR_RECEIPT_COMPONENTS:
        current = current / component
        current.mkdir(mode=0o700)
    journal = current / quarantine.JOURNAL_DIRECTORY
    journal.mkdir(mode=0o700)
    consumed: JsonObject = {
        "schema_version": "1",
        "record_type": "attempt008_quarantine_revocation_consumption",
        "recovery_id": quarantine.RECOVERY_ID,
        "candidate_commit": recovery.PARENT_COMMIT,
        "candidate_tree": recovery.PARENT_TREE,
        "consumed_before_live_access": True,
        "attempt_budget": 0,
        "retry_authorized": False,
        "same_operation_resume_authorized": True,
        "cleanup_authorized": False,
        "successor_o4_authorized": False,
        "release_allowed": False,
        "uat_complete": False,
    }
    journal_record: JsonObject = {
        "schema_version": "1",
        "record_type": "attempt008_quarantine_revocation_journal",
        "recovery_id": quarantine.RECOVERY_ID,
        "sequence": 1,
        "event": "identity-receipts-validated",
        "payload": {"identity_digest": "sha256:" + "a" * 64},
    }

    def fixed_leaf(
        _root: Path,
        components: tuple[str, ...],
        name: str,
        *,
        expected_size: int,
        expected_digest: str,
    ) -> bytes:
        del _root, expected_size, expected_digest
        if name == quarantine.CONSUMED_RECEIPT:
            assert components == recovery.PREDECESSOR_RECEIPT_COMPONENTS
            return (canonical_json(consumed) + "\n").encode()
        assert components[-1] == quarantine.JOURNAL_DIRECTORY
        return (canonical_json(journal_record) + "\n").encode()

    monkeypatch.setattr(quarantine, "_read_bound_leaf", fixed_leaf)
    recovery._validate_predecessor_receipts(repo_root)  # noqa: SLF001

    (journal / "0002-project-preinspection.json").write_text("{}")
    with pytest.raises(recovery.RecoveryError, match="predecessor_receipt_invalid"):
        recovery._validate_predecessor_receipts(repo_root)  # noqa: SLF001
    (journal / "0002-project-preinspection.json").unlink()
    final_sequence = len(quarantine.JOURNAL_EVENTS)
    final_name = f"{final_sequence:04d}-{quarantine.JOURNAL_EVENTS[-1]}.json"
    (journal / final_name).write_text("{}")
    with pytest.raises(recovery.RecoveryError, match="predecessor_receipt_invalid"):
        recovery._validate_predecessor_receipts(repo_root)  # noqa: SLF001


def test_observation_plan_exposes_no_mutation_command() -> None:
    plan = recovery.ObservationPlan("/private/reviewed/docker")
    assert plan.query()[1] == "ps"
    for container_id, _image in recovery.EXPECTED_CONTAINERS.values():
        assert plan.inspect(container_id)[1:3] == ("container", "inspect")
    assert not hasattr(plan, "stop")
    source = (recovery.ROOT / recovery.SCRIPT_PATH).read_text()
    assert '"stop"' not in source
    assert '"start"' not in source
    assert '"restart"' not in source
    assert '"exec"' not in source
    assert '"compose"' not in source


def test_exact_two_container_projection_is_accepted() -> None:
    observed = recovery.observe_exact_project(FakeObservationExecutor())
    assert set(observed) == {"ithildin-api", "ithildin-ui"}
    assert all(
        isinstance(projection, dict) and projection.get("running") is False
        for projection in observed.values()
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "zero",
        "one",
        "third",
        "duplicate",
        "running",
        "wrong_image",
        "wrong_id",
        "wrong_service",
        "created",
        "dead",
        "ports",
        "wrong_project",
    ],
)
def test_project_projection_rejects_every_nonexact_shape(mutation: str) -> None:
    executor = FakeObservationExecutor()
    if mutation == "zero":
        executor.services.clear()
    elif mutation == "one":
        executor.services.pop()
    elif mutation == "third":
        executor.extra_ids.append("9" * 64)
    elif mutation == "duplicate":
        executor.services.append("ithildin-api")
    elif mutation == "running":
        executor.running["ithildin-api"] = True
    elif mutation == "wrong_image":
        executor.image_overrides["ithildin-api"] = "sha256:" + "f" * 64
    elif mutation == "wrong_id":
        executor.id_overrides["ithildin-api"] = "f" * 64
    elif mutation == "wrong_service":
        executor.service_overrides["ithildin-api"] = "ithildin-ui"
    elif mutation == "created":
        executor.status_overrides["ithildin-api"] = "created"
    elif mutation == "dead":
        executor.status_overrides["ithildin-api"] = "dead"
    elif mutation == "ports":
        executor.port_overrides["ithildin-api"] = {
            "8000/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8000"}]
        }
    else:
        executor.project_overrides["ithildin-api"] = "wrong-project"
    with pytest.raises(recovery.RecoveryError):
        recovery.observe_exact_project(executor)


def test_storage_transition_revokes_and_audits_once_with_phase_checks(
    tmp_path: Path,
) -> None:
    session, aliases, reconciled = _storage_fixture(tmp_path)
    journal = MemoryJournal()
    checks = 0

    def require_quiesced() -> None:
        nonlocal checks
        checks += 1

    try:
        result = recovery.execute_storage_transition(
            aliases,
            reconciled,
            journal,
            require_quiesced,
        )
        record = NodeStore(aliases.database_path).get(reconciled.node_id)
        assert record.status == "revoked"
        assert record.evidence_status == "complete"
        events = AuditWriter(aliases.database_path, aliases.audit_path).list_events(limit=10)
        assert len(events) == 1
        assert events[0]["event_type"] == "node.revoked"
        assert result["node_status"] == "revoked"
        assert result["cleanup_completed"] is False
        assert result["successor_o4_authorized"] is False
        assert checks >= 7
        assert reconciled.node_id not in canonical_json(cast(JsonObject, journal.payloads))
        assert reconciled.node_id not in canonical_json(result)
    finally:
        aliases.close()
        session.close()


def test_storage_transition_preserves_exact_node_column_boundary(
    tmp_path: Path,
) -> None:
    session, aliases, reconciled = _storage_fixture(tmp_path)
    try:
        with sqlite3.connect(aliases.database_path) as connection:
            columns = [str(row[1]) for row in connection.execute("PRAGMA table_info(nodes)")]
            before = dict(
                zip(
                    columns,
                    connection.execute(
                        "SELECT * FROM nodes WHERE node_id = ?",
                        (reconciled.node_id,),
                    ).fetchone(),
                    strict=True,
                )
            )
        recovery.execute_storage_transition(
            aliases,
            reconciled,
            MemoryJournal(),
            lambda: None,
        )
        with sqlite3.connect(aliases.database_path) as connection:
            after = dict(
                zip(
                    columns,
                    connection.execute(
                        "SELECT * FROM nodes WHERE node_id = ?",
                        (reconciled.node_id,),
                    ).fetchone(),
                    strict=True,
                )
            )
        assert {column for column in columns if before[column] != after[column]} == {
            "status",
            "updated_at",
            "revoked_at",
        }
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
            recovery.execute_storage_transition(
                aliases,
                reconciled,
                journal,
                _always_quiesced,
            )
        pending = NodeStore(aliases.database_path).get(reconciled.node_id)
        assert pending.status == "revoked"
        assert pending.evidence_status == "pending"

        monkeypatch.setattr(AuditWriter, "write_event", original_write)
        result = recovery.execute_storage_transition(
            aliases,
            reconciled,
            journal,
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
            recovery.execute_storage_transition(
                aliases,
                reconciled,
                journal,
                _always_quiesced,
            )
        aliases.audit_path.write_bytes(b'{"orphan":true}\n')
        with pytest.raises(
            recovery.RecoveryError,
            match="audit_lifecycle_recovery_required",
        ):
            recovery.execute_storage_transition(
                aliases,
                reconciled,
                journal,
                _always_quiesced,
            )
        pending = NodeStore(aliases.database_path).get(reconciled.node_id)
        assert pending.status == "revoked"
        assert pending.evidence_status == "pending"
        assert aliases.audit_path.read_bytes() == b'{"orphan":true}\n'
    finally:
        aliases.close()
        session.close()


def test_resume_rejects_tampered_pending_journal_payload(
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
            recovery.execute_storage_transition(
                aliases,
                reconciled,
                journal,
                _always_quiesced,
            )
        journal.payloads["node-revocation-observed-pending"]["extra"] = True
        with pytest.raises(recovery.RecoveryError, match="journal_invalid"):
            recovery.execute_storage_transition(
                aliases,
                reconciled,
                journal,
                _always_quiesced,
            )
    finally:
        aliases.close()
        session.close()


def test_resume_rejects_storage_drift_before_revocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session, aliases, reconciled = _storage_fixture(tmp_path)
    journal = MemoryJournal()
    original_revoke = NodeStore.revoke

    def fail_revoke(
        self: NodeStore,
        node_id: str,
        *,
        now: datetime,
    ) -> Any:
        del self, node_id, now
        raise NodeConflictError("synthetic interruption")

    try:
        monkeypatch.setattr(NodeStore, "revoke", fail_revoke)
        with pytest.raises(
            recovery.RecoveryError,
            match="node_revocation_failed",
        ):
            recovery.execute_storage_transition(
                aliases,
                reconciled,
                journal,
                _always_quiesced,
            )
        with sqlite3.connect(aliases.database_path) as connection:
            connection.execute("PRAGMA user_version = 1")
        monkeypatch.setattr(NodeStore, "revoke", original_revoke)
        with pytest.raises(
            recovery.RecoveryError,
            match="storage_resume_snapshot_changed",
        ):
            recovery.execute_storage_transition(
                aliases,
                reconciled,
                journal,
                _always_quiesced,
            )
    finally:
        aliases.close()
        session.close()


def test_terminal_receipt_follows_post_intent_projection_check(
    tmp_path: Path,
) -> None:
    session, aliases, _reconciled = _storage_fixture(tmp_path)
    journal = MemoryJournal()
    checks = 0
    postinspection: JsonObject = {
        "ithildin-api": {"running": False},
        "ithildin-ui": {"running": False},
    }

    def require_quiesced() -> None:
        nonlocal checks
        checks += 1
        assert "disposition-intent" in journal.payloads
        assert not (session.root_path / recovery.DISPOSITION_RECEIPT).exists()

    try:
        disposition = recovery._finalize(  # noqa: SLF001
            session,
            journal,
            postinspection=postinspection,
            storage={"node_status": "revoked"},
            require_quiesced=require_quiesced,
        )
        assert checks == 1
        assert disposition["status"] == "completed"
        assert (session.root_path / recovery.DISPOSITION_RECEIPT).is_file()
    finally:
        aliases.close()
        session.close()


def test_live_refuses_before_consumption_without_review_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        recovery,
        "build_report",
        lambda _root: {
            "static_candidate_valid": True,
            "review_binding_valid": False,
            "execution_available": False,
        },
    )

    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("live seam entered")

    monkeypatch.setattr(recovery, "consume_or_resume", forbidden)
    with pytest.raises(
        recovery.RecoveryError,
        match="two_container_revocation_not_authorized",
    ):
        recovery.run_live(recovery.ROOT, environment={})


def test_public_main_never_prints_raw_node_identity(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        recovery,
        "run_live",
        lambda *_args, **_kwargs: {
            "status": "completed",
            "identity_digest": "sha256:" + "a" * 64,
        },
    )
    assert recovery.main([]) == 0
    output = capsys.readouterr().out
    assert output == "attempt008_two_container_revocation_status: completed\n"
    assert NODE_ID not in output


def test_live_config_is_created_beneath_new_private_receipt_root() -> None:
    source = (recovery.ROOT / recovery.SCRIPT_PATH).read_text()
    assert "dir=session.root_path" in source
    makefile = (recovery.ROOT / "Makefile").read_text()
    assert "uv run --offline --frozen python -m" in makefile
    assert 'container_stop_authorized": True' not in source
    assert 'docker_mutation_authorized": True' not in source
    assert 'successor_o4_authorized": True' not in source
    assert 'release_allowed": True' not in source
    assert 'uat_complete": True' not in source

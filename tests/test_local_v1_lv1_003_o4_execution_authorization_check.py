from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import local_v1_lv1_003_o4_execution_authorization_check as gate

ROOT = Path(".")


def _contract() -> dict[str, object]:
    document = json.loads(gate.CONTRACT.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _run_git(repo: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _attempt_009_closure_child_repository(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "candidate"
    subprocess.run(
        ["git", "clone", "-q", str(Path.cwd()), str(repo)],
        check=True,
    )
    _run_git(repo, "checkout", "--detach", gate.ATTEMPT_009_CANDIDATE_COMMIT)
    for relative in gate.ATTEMPT_009_CLOSURE_CONTROL_PATH_ALLOWLIST:
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, destination)
    _run_git(repo, "add", "--", *gate.ATTEMPT_009_CLOSURE_CONTROL_PATH_ALLOWLIST)
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: exact O4 Attempt 009 closure child",
    )
    shutil.copytree(
        Path.cwd() / gate.ATTEMPT_002_RECEIPT_BASE,
        repo / gate.ATTEMPT_002_RECEIPT_BASE,
        copy_function=shutil.copy2,
    )
    runtime_base = repo / gate.ATTEMPT_002_RUNTIME_BASE
    runtime_base.mkdir(parents=True, mode=0o700)
    runtime_base.chmod(0o700)
    (runtime_base / gate.ATTEMPT_008_RUN_ID).mkdir(mode=0o700)
    shutil.copy2(
        Path.cwd() / gate.IMAGE_RECOVERY_CONSUMPTION_RECEIPT,
        repo / gate.IMAGE_RECOVERY_CONSUMPTION_RECEIPT,
    )
    return (
        repo,
        _run_git(repo, "rev-parse", "HEAD"),
        _run_git(repo, "show", "-s", "--format=%T", "HEAD"),
    )


def test_attempt_009_exact_child_closes_all_live_authority(
    tmp_path: Path,
) -> None:
    repo, execution_commit, execution_tree = _attempt_009_closure_child_repository(tmp_path)
    report = gate.build_report(repo)

    assert report["failures"] == []
    assert report["valid"] is True
    assert report["record_status"] == (
        "ATTEMPT_009_CONSUMED_REQUIRED_LOOPBACK_PORT_UNAVAILABLE_"
        "NO_RECOVERY_NO_LIVE_AUTHORITY"
    )
    assert report["reviewed_implementation_commit"] == gate.REVIEWED_IMPLEMENTATION_COMMIT
    assert report["code_authorization_commit"] == gate.CODE_AUTHORIZATION_COMMIT
    assert report["attempt_id"] == gate.ATTEMPT_009_ID
    assert report["attempted_candidate_commit"] == gate.ATTEMPT_009_CANDIDATE_COMMIT
    assert report["attempted_candidate_tree"] == gate.ATTEMPT_009_CANDIDATE_TREE
    assert report["attempt_002_attempted_candidate_commit"] == gate.ATTEMPT_002_CANDIDATE_COMMIT
    assert report["attempt_002_attempted_candidate_tree"] == gate.ATTEMPT_002_CANDIDATE_TREE
    assert report["attempt_001_history"] == {
        "attempt_id": gate.ATTEMPT_001_ID,
        "attempted_candidate_commit": gate.ATTEMPT_001_CANDIDATE_COMMIT,
        "attempted_candidate_tree": gate.ATTEMPT_001_CANDIDATE_TREE,
        "attempt_consumed": True,
    }
    assert report["attempt_001_consumed"] is True
    assert report["attempt_002_consumed"] is True
    assert report["attempt_003_consumed"] is True
    assert report["attempt_004_consumed"] is True
    assert report["attempt_005_consumed"] is True
    assert report["attempt_006_consumed"] is True
    assert report["attempt_007_consumed"] is True
    assert report["attempt_008_consumed"] is True
    assert report["attempt_009_consumed"] is True
    assert report["attempt_consumed"] is True
    assert report["retry_authorized"] is False
    contract = _contract()
    assert (
        contract["code_authorization_origin_record_sha256"]
        == gate.CODE_AUTHORIZATION_ORIGIN_RECORD_DIGEST
    )
    assert contract["code_authorization_record_sha256"] == gate.CODE_AUTHORIZATION_RECORD_DIGEST
    assert contract["candidate_parent_commit"] == gate.ATTEMPT_009_CANDIDATE_COMMIT
    assert contract["candidate_parent_tree"] == gate.ATTEMPT_009_CANDIDATE_TREE
    assert contract["enrollment_output_projection_contract"] == {
        "field_names": ["node_id", "principal_id", "workspace_id"],
        "field_types": {
            "node_id": "string",
            "principal_id": "string",
            "workspace_id": "string",
        },
        "principal_id_derivation": "agent:node.{node_id}",
        "canonical_json_terminated_by_one_lf": True,
        "extra_fields_allowed": False,
    }
    assert (
        contract["historical_post_review_candidate_parent_commit"]
        == gate.HISTORICAL_CANDIDATE_PARENT_COMMIT
    )
    assert (
        contract["historical_post_review_candidate_parent_tree"]
        == gate.HISTORICAL_CANDIDATE_PARENT_TREE
    )
    assert report["execution_checkout_commit"] == execution_commit
    assert report["execution_checkout_tree"] == execution_tree
    assert report["execution_attempt_budget"] == 0
    assert report["live_execution_authorized"] is False
    assert report["docker_lifecycle_authorized"] is False
    assert report["provider_access_authorized"] is False
    assert report["o4_evidence_execution_authorized"] is False
    assert report["new_governed_tool"] is False
    assert report["release_allowed"] is False
    assert report["uat_complete"] is False
    authority = _contract()["authority"]
    assert isinstance(authority, dict)
    assert set(authority) == gate.AUTHORITY_FIELDS
    assert {key for key, value in authority.items() if value is True} == gate.TRUE_AUTHORITY_FIELDS
    assert (
        gate._file_digest(gate.ATTEMPT_001_DISPOSITION_JSON, [])  # noqa: SLF001
        == gate.ATTEMPT_001_DISPOSITION_JSON_DIGEST
    )
    assert (
        gate._file_digest(gate.ATTEMPT_001_DISPOSITION_DOCUMENT, [])  # noqa: SLF001
        == gate.ATTEMPT_001_DISPOSITION_DOCUMENT_DIGEST
    )
    with pytest.raises(gate.O4ExecutionAuthorizationError):
        gate.assert_live_execution_authorized(
            repo,
            candidate_commit=execution_commit,
            candidate_tree=execution_tree,
        )


def test_enrollment_repair_review_binds_three_field_derived_principal_projection() -> None:
    document = gate.ENROLLMENT_OUTPUT_PROJECTION_REPAIR_REVIEW.read_text(encoding="utf-8")
    normalized = " ".join(document.split())

    assert (
        "exactly three string fields: `node_id`, `principal_id`, and `workspace_id`" in normalized
    )
    assert "`principal_id` must equal `agent:node.{node_id}`" in normalized
    for stale in ("`agent_id`", "`gateway`", "`registered`", "five-field"):
        assert stale not in normalized


def test_attempt_009_rejects_node_cli_repair_path_drift(tmp_path: Path) -> None:
    repo, _, _ = _attempt_009_closure_child_repository(tmp_path)
    node_cli = repo / "apps/node/src/ithildin_node/__main__.py"
    node_cli.write_text(
        node_cli.read_text(encoding="utf-8") + "\n# forbidden repair drift\n",
        encoding="utf-8",
    )

    report = gate.build_report(repo)

    assert report["valid"] is False
    assert any(
        "O4 enrollment-output projection repair differs for "
        "apps/node/src/ithildin_node/__main__.py" in failure
        for failure in report["failures"]
    )
    assert report["execution_attempt_budget"] == 0
    assert report["live_execution_authorized"] is False


def test_real_retained_attempt_002_and_003_evidence_is_exact() -> None:
    failures: list[str] = []

    gate._validate_retained_attempt_evidence(ROOT, failures)  # noqa: SLF001

    assert failures == []


def test_attempt_009_disposition_is_closed_and_exact() -> None:
    disposition = json.loads(gate.ATTEMPT_009_DISPOSITION_JSON.read_text(encoding="utf-8"))
    failures: list[str] = []

    gate._validate_attempt_009_disposition(  # type: ignore[arg-type] # noqa: SLF001
        disposition,
        gate.ATTEMPT_009_DISPOSITION_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert failures == []
    assert disposition["attempt_contract"]["execution_attempt_budget"] == 0
    assert disposition["attempt_contract"]["attempt_consumed"] is True
    assert disposition["authority"] == gate.CLOSED_AUTHORITY


def test_attempt_009_retained_diagnostic_rejects_drift(tmp_path: Path) -> None:
    repo, _, _ = _attempt_009_closure_child_repository(tmp_path)
    diagnostic = repo / gate.ATTEMPT_009_RECEIPT_ROOT / "diagnostic.json"
    diagnostic.write_bytes(b"x" * gate.ATTEMPT_009_DIAGNOSTIC_SIZE)
    diagnostic.chmod(0o600)

    report = gate.build_report(repo)

    assert report["valid"] is False
    assert any("O4 Attempt 009 failure diagnostic" in failure for failure in report["failures"])
    assert report["execution_attempt_budget"] == 0
    assert report["live_execution_authorized"] is False


def test_attempt_009_exact_runtime_root_presence_is_rejected(tmp_path: Path) -> None:
    repo, _, _ = _attempt_009_closure_child_repository(tmp_path)
    (repo / gate.ATTEMPT_009_RUNTIME_ROOT).mkdir(mode=0o700)

    report = gate.build_report(repo)

    assert report["valid"] is False
    assert any(
        "O4 exact Attempt 009 runtime root is present" in failure
        for failure in report["failures"]
    )
    assert report["execution_attempt_budget"] == 0
    assert report["live_execution_authorized"] is False


def test_additional_retained_attempt_run_refuses_attempt_004(
    tmp_path: Path,
) -> None:
    repo, _, _ = _attempt_009_closure_child_repository(tmp_path)
    receipt_base = repo / gate.ATTEMPT_002_RECEIPT_BASE
    (receipt_base / "unknown-attempt").mkdir(mode=0o700)

    report = gate.build_report(repo)

    assert report["valid"] is False
    assert any("receipt base entries are not exact" in failure for failure in report["failures"])
    assert report["execution_attempt_budget"] == 0
    assert report["live_execution_authorized"] is False
    assert report["docker_lifecycle_authorized"] is False
    assert report["provider_access_authorized"] is False
    assert report["o4_evidence_execution_authorized"] is False


@pytest.mark.parametrize(
    "mutation",
    ["tampered", "symlink", "special", "extra_child"],
)
def test_attempt_003_retained_receipt_rejects_tamper_symlink_or_special(
    tmp_path: Path,
    mutation: str,
) -> None:
    repo, _, _ = _attempt_009_closure_child_repository(tmp_path)
    receipt_root = repo / gate.ATTEMPT_003_RECEIPT_ROOT
    disposition = receipt_root / "disposition.json"
    if mutation == "tampered":
        disposition.write_bytes(b"x" * len(gate.ATTEMPT_003_DISPOSITION_BYTES))
        disposition.chmod(0o600)
    elif mutation == "symlink":
        disposition.unlink()
        external = tmp_path / "external-disposition.json"
        external.write_bytes(gate.ATTEMPT_003_DISPOSITION_BYTES)
        disposition.symlink_to(external)
    elif mutation == "special":
        disposition.unlink()
        os.mkfifo(disposition, 0o600)
    else:
        extra = receipt_root / "unknown.json"
        extra.write_text("{}\n", encoding="utf-8")
        extra.chmod(0o600)

    report = gate.build_report(repo)

    assert report["valid"] is False
    assert report["execution_attempt_budget"] == 0
    assert report["live_execution_authorized"] is False
    assert report["docker_lifecycle_authorized"] is False
    assert report["provider_access_authorized"] is False
    assert report["o4_evidence_execution_authorized"] is False


@pytest.mark.parametrize(
    "mutation",
    ["missing", "tampered", "symlink", "special", "extra_child"],
)
def test_attempt_004_diagnostic_rejects_any_drift(
    tmp_path: Path,
    mutation: str,
) -> None:
    repo, _, _ = _attempt_009_closure_child_repository(tmp_path)
    receipt_root = repo / gate.ATTEMPT_004_RECEIPT_ROOT
    diagnostic = receipt_root / "diagnostic.json"
    if mutation == "missing":
        diagnostic.unlink()
    elif mutation == "tampered":
        diagnostic.write_bytes(b"x" * gate.ATTEMPT_004_DIAGNOSTIC_SIZE)
        diagnostic.chmod(0o600)
    elif mutation == "symlink":
        diagnostic.unlink()
        external = tmp_path / "external-diagnostic.json"
        external.write_bytes(b"x" * gate.ATTEMPT_004_DIAGNOSTIC_SIZE)
        diagnostic.symlink_to(external)
    elif mutation == "special":
        diagnostic.unlink()
        os.mkfifo(diagnostic, 0o600)
    else:
        extra = receipt_root / "unknown.json"
        extra.write_text("{}\n", encoding="utf-8")
        extra.chmod(0o600)

    report = gate.build_report(repo)

    assert report["valid"] is False
    assert report["execution_attempt_budget"] == 0
    assert report["live_execution_authorized"] is False
    assert report["docker_lifecycle_authorized"] is False
    assert report["provider_access_authorized"] is False
    assert report["o4_evidence_execution_authorized"] is False


def test_attempt_007_retained_receipt_rejects_missing_marker_drift(
    tmp_path: Path,
) -> None:
    repo, _, _ = _attempt_009_closure_child_repository(tmp_path)
    diagnostic = repo / gate.ATTEMPT_007_RECEIPT_ROOT / "diagnostic.json"
    contents = diagnostic.read_bytes()
    assert b"application_startup_stage_missing" in contents
    diagnostic.write_bytes(
        contents.replace(
            b"application_startup_stage_missing",
            b"application_startup_stage_present",
            1,
        )
    )
    diagnostic.chmod(0o600)

    report = gate.build_report(repo)

    assert report["valid"] is False
    assert any("O4 Attempt 007 failure diagnostic" in failure for failure in report["failures"])
    assert report["execution_attempt_budget"] == 0
    assert report["live_execution_authorized"] is False
    assert report["docker_lifecycle_authorized"] is False
    assert report["provider_access_authorized"] is False
    assert report["o4_evidence_execution_authorized"] is False


@pytest.mark.parametrize(
    "mutation",
    ["missing", "tampered", "chmod", "symlink", "special", "extra"],
)
def test_recovery_consumption_receipt_rejects_any_drift(
    tmp_path: Path,
    mutation: str,
) -> None:
    repo, _, _ = _attempt_009_closure_child_repository(tmp_path)
    receipt = repo / gate.IMAGE_RECOVERY_CONSUMPTION_RECEIPT
    runtime_base = receipt.parent
    if mutation == "missing":
        receipt.unlink()
    elif mutation == "tampered":
        receipt.write_bytes(b"x" * len(gate.IMAGE_RECOVERY_CONSUMPTION_RECEIPT_BYTES))
        receipt.chmod(0o600)
    elif mutation == "chmod":
        receipt.chmod(0o644)
    elif mutation == "symlink":
        receipt.unlink()
        external = tmp_path / "external-recovery-receipt.json"
        external.write_bytes(gate.IMAGE_RECOVERY_CONSUMPTION_RECEIPT_BYTES)
        receipt.symlink_to(external)
    elif mutation == "special":
        receipt.unlink()
        os.mkfifo(receipt, 0o600)
    else:
        (runtime_base / "unknown").write_text("x\n", encoding="utf-8")

    report = gate.build_report(repo)

    assert report["valid"] is False
    assert report["execution_attempt_budget"] == 0
    assert report["live_execution_authorized"] is False
    assert report["docker_lifecycle_authorized"] is False
    assert report["provider_access_authorized"] is False
    assert report["o4_evidence_execution_authorized"] is False


@pytest.mark.parametrize(
    "posture",
    ["empty_base", "unknown_file", "unknown_directory", "symlinked_base"],
)
def test_any_report_base_posture_refuses_attempt_004(
    tmp_path: Path,
    posture: str,
) -> None:
    repo, _, _ = _attempt_009_closure_child_repository(tmp_path)
    report_base = repo / gate.ATTEMPT_002_REPORT_BASE
    if posture == "symlinked_base":
        external = tmp_path / "external-report-base"
        external.mkdir()
        report_base.symlink_to(external, target_is_directory=True)
    else:
        report_base.mkdir(parents=True)
        if posture == "unknown_file":
            (report_base / "unknown-report.json").write_text(
                "{}\n",
                encoding="utf-8",
            )
        elif posture == "unknown_directory":
            (report_base / "unknown-run").mkdir()

    report = gate.build_report(repo)

    assert report["valid"] is False
    assert "O4 published report base is present" in report["failures"]
    assert report["execution_attempt_budget"] == 0
    assert report["live_execution_authorized"] is False
    assert report["docker_lifecycle_authorized"] is False
    assert report["provider_access_authorized"] is False
    assert report["o4_evidence_execution_authorized"] is False


def test_invalid_retained_evidence_never_reopens_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject_retained_evidence(_: Path, failures: list[str]) -> None:
        failures.append("retained evidence rejected for test")

    monkeypatch.setattr(
        gate,
        "_validate_retained_attempt_evidence",
        reject_retained_evidence,
    )

    report = gate.build_report(ROOT)

    assert report["valid"] is False
    assert "retained evidence rejected for test" in report["failures"]
    assert report["execution_attempt_budget"] == 0
    assert report["live_execution_authorized"] is False
    assert report["docker_lifecycle_authorized"] is False
    assert report["provider_access_authorized"] is False
    assert report["o4_evidence_execution_authorized"] is False
    assert report["release_allowed"] is False
    assert report["uat_complete"] is False


def test_live_gate_refuses_consumed_attempt_002() -> None:
    with pytest.raises(
        gate.O4ExecutionAuthorizationError,
        match="o4_live_execution_not_authorized",
    ):
        gate.assert_live_execution_authorized(
            ROOT,
            candidate_commit=gate.ATTEMPT_002_CANDIDATE_COMMIT,
            candidate_tree=gate.ATTEMPT_002_CANDIDATE_TREE,
        )


@pytest.mark.parametrize(
    ("mutate", "failure_fragment"),
    [
        (
            lambda value: value.__setitem__("execution_candidate_commit", "a" * 40),
            "fields are not closed",
        ),
        (
            lambda value: value.__setitem__("execution_attempt_budget", 2),
            "execution_attempt_budget",
        ),
        (
            lambda value: value.__setitem__("execution_attempt_budget", True),
            "execution_attempt_budget",
        ),
        (
            lambda value: value.__setitem__("record_status", "AUTHORIZED_EXACT_CANDIDATE"),
            "record_status",
        ),
        (
            lambda value: value.__setitem__("candidate_parent_commit", "a" * 40),
            "candidate_parent_commit",
        ),
        (
            lambda value: value.__setitem__(
                "historical_post_review_candidate_parent_commit", "a" * 40
            ),
            "historical_post_review_candidate_parent_commit",
        ),
        (
            lambda value: value.__setitem__("attempt_001_attempted_candidate_commit", "a" * 40),
            "attempt_001_attempted_candidate_commit",
        ),
        (
            lambda value: value["attempt_001_invocation"].__setitem__(  # type: ignore[union-attr]
                "command", "python scripts/local_v1_lv1_003_o4_producer.py"
            ),
            "attempt_001_invocation",
        ),
        (
            lambda value: value["attempt_001_invocation"].__setitem__(  # type: ignore[union-attr]
                "classification", "SUCCESS"
            ),
            "attempt_001_invocation",
        ),
        (
            lambda value: value["attempt_001_root_absence"]["absent_roots"].pop(),  # type: ignore[index,union-attr]
            "attempt_001_root_absence",
        ),
        (
            lambda value: value.__setitem__("attempt_consumed", False),
            "attempt_consumed",
        ),
        (
            lambda value: value.__setitem__("attempt_004_execution_authorized", True),
            "attempt_004_execution_authorized",
        ),
        (
            lambda value: value.__setitem__(
                "image_recovery_closure_json_sha256", "sha256:" + "0" * 64
            ),
            "image_recovery_closure_json_sha256",
        ),
        (
            lambda value: value.__setitem__(
                "runtime_native_repair_review_sha256", "sha256:" + "0" * 64
            ),
            "runtime_native_repair_review_sha256",
        ),
        (
            lambda value: value.__setitem__(
                "execution_candidate_binding_mode", "dynamic_current_head_after_all_checks"
            ),
            "execution_candidate_binding_mode",
        ),
        (
            lambda value: value.__setitem__(
                "enrollment_output_projection_repair_review_sha256",
                "sha256:" + "0" * 64,
            ),
            "enrollment_output_projection_repair_review_sha256",
        ),
        (
            lambda value: value["enrollment_output_projection_repair_path_digests"].__setitem__(  # type: ignore[union-attr]
                "tests/test_node_cli.py", "sha256:" + "0" * 64
            ),
            "enrollment_output_projection_repair_path_digests",
        ),
        (
            lambda value: value["enrollment_output_projection_contract"].__setitem__(  # type: ignore[union-attr]
                "field_names",
                ["node_id", "principal_id", "workspace_id", "registered"],
            ),
            "enrollment_output_projection_contract",
        ),
        (
            lambda value: value.__setitem__("attempt_009_execution_authorized", True),
            "attempt_009_execution_authorized",
        ),
        (
            lambda value: value.__setitem__("retry_authorized", True),
            "retry_authorized",
        ),
        (
            lambda value: value.__setitem__("attempt_002_candidate_parent_commit", "a" * 40),
            "attempt_002_candidate_parent_commit",
        ),
        (
            lambda value: value.__setitem__(
                "attempt_002_operator_command", gate.FAILED_FILE_PATH_INVOCATION
            ),
            "attempt_002_operator_command",
        ),
        (
            lambda value: value.__setitem__(
                "attempt_002_module_command", gate.FAILED_FILE_PATH_INVOCATION
            ),
            "attempt_002_module_command",
        ),
        (
            lambda value: value.__setitem__(
                "entrypoint_repair_review_sha256", "sha256:" + "0" * 64
            ),
            "entrypoint_repair_review_sha256",
        ),
        (
            lambda value: value.__setitem__(
                "attempt_002_disposition_json_sha256", "sha256:" + "0" * 64
            ),
            "attempt_002_disposition_json_sha256",
        ),
        (
            lambda value: value.__setitem__("attempt_002_execution_authorized", True),
            "attempt_002_execution_authorized",
        ),
        (
            lambda value: value["producer_entrypoint_repair"].__setitem__(  # type: ignore[union-attr]
                "module_invocation", gate.FAILED_FILE_PATH_INVOCATION
            ),
            "producer_entrypoint_repair",
        ),
        (
            lambda value: value["producer_entrypoint_repair"].__setitem__(  # type: ignore[union-attr]
                "failed_file_path_invocation_authorized", True
            ),
            "producer_entrypoint_repair",
        ),
        (
            lambda value: value["profile"].__setitem__(  # type: ignore[union-attr]
                "provider_model", "different-model"
            ),
            "profile binding",
        ),
        (
            lambda value: value["profile"].__setitem__(  # type: ignore[union-attr]
                "unexpected", False
            ),
            "profile binding",
        ),
        (
            lambda value: value["profile"]["hermes_platform_digests"].__setitem__(  # type: ignore[index,union-attr]
                "linux/ppc64le", "sha256:" + "0" * 64
            ),
            "profile binding",
        ),
        (
            lambda value: value["command_contract"]["fixed_actions"].append(  # type: ignore[index,union-attr]
                "arbitrary_exec"
            ),
            "command contract",
        ),
        (
            lambda value: value["command_contract"]["dynamic_values"].append(  # type: ignore[index,union-attr]
                "unbounded"
            ),
            "command contract",
        ),
        (
            lambda value: value["command_contract"].__setitem__(  # type: ignore[union-attr]
                "absent_image_id_probe_stdout_allowlist", [""]
            ),
            "command contract",
        ),
        (
            lambda value: value["command_contract"]["base_service_start_diagnostic"][  # type: ignore[index,union-attr]
                "compose_arguments"
            ].append("--environment"),  # type: ignore[union-attr]
            "command contract",
        ),
        (
            lambda value: value["command_contract"]["base_service_start_diagnostic"].__setitem__(  # type: ignore[index,union-attr]
                "raw_output_persisted", True
            ),
            "command contract",
        ),
        (
            lambda value: value["command_contract"].__setitem__(  # type: ignore[union-attr]
                "unexpected", False
            ),
            "command contract",
        ),
        (
            lambda value: value.__setitem__("external_preflight_requirements", []),
            "external_preflight_requirements",
        ),
        (
            lambda value: value["evidence_contract"].__setitem__(  # type: ignore[union-attr]
                "hermes_execution_attempts_maximum", 2
            ),
            "evidence contract",
        ),
        (
            lambda value: value["evidence_contract"].__setitem__(  # type: ignore[union-attr]
                "mission_count", True
            ),
            "evidence contract",
        ),
        (
            lambda value: value["evidence_contract"].__setitem__(  # type: ignore[union-attr]
                "gateway_agent_run_record_status", "completed"
            ),
            "evidence contract",
        ),
        (
            lambda value: value["evidence_contract"].__setitem__(  # type: ignore[union-attr]
                "gateway_completed_timeline_event_count", 1
            ),
            "evidence contract",
        ),
        (
            lambda value: value["evidence_contract"].__setitem__(  # type: ignore[union-attr]
                "hermes_stdout_destination", "PIPE"
            ),
            "evidence contract",
        ),
        (
            lambda value: value["evidence_contract"].__setitem__(  # type: ignore[union-attr]
                "current_assembler_usable_for_live_producer", False
            ),
            "evidence contract",
        ),
        (
            lambda value: value["evidence_contract"]["bounded_image_metadata_fields"].append(
                "sbom_digest"
            ),  # type: ignore[index,union-attr]
            "evidence contract",
        ),
        (
            lambda value: value["evidence_contract"][
                "current_tracked_license_inventory_inputs"
            ].append("requirements.txt"),  # type: ignore[index,union-attr]
            "evidence contract",
        ),
        (
            lambda value: value["evidence_contract"].__setitem__(  # type: ignore[union-attr]
                "transient_malicious_same_uid_mutation_during_docker_context_read_proven_absent",
                True,
            ),
            "evidence contract",
        ),
        (
            lambda value: value["evidence_contract"].__setitem__(  # type: ignore[union-attr]
                "unexpected", False
            ),
            "evidence contract",
        ),
        (
            lambda value: value["cleanup_contract"].__setitem__(  # type: ignore[union-attr]
                "runtime_plaintext_absent_required", False
            ),
            "cleanup contract",
        ),
        (
            lambda value: value["cleanup_contract"].__setitem__(  # type: ignore[union-attr]
                "chmod_only_publication_rollback_success_allowed", True
            ),
            "cleanup contract",
        ),
        (
            lambda value: value["cleanup_contract"].__setitem__(  # type: ignore[union-attr]
                "confirmed_node_revocation_required_before_destructive_cleanup",
                False,
            ),
            "cleanup contract",
        ),
        (
            lambda value: value["cleanup_contract"].__setitem__(  # type: ignore[union-attr]
                "unexpected", True
            ),
            "cleanup contract",
        ),
        (
            lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
                "docker_lifecycle_authorized", True
            ),
            "not exact for Attempt 009",
        ),
        (
            lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
                "producer_code_authorized", True
            ),
            "not exact for Attempt 009",
        ),
        (
            lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
                "shell_execution_authorized", True
            ),
            "not exact for Attempt 009",
        ),
        (
            lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
                "release_allowed", 0
            ),
            "not exact for Attempt 009",
        ),
        (
            lambda value: value.__setitem__("unexpected", False),
            "fields are not closed",
        ),
    ],
)
def test_supervised_attempt_contract_rejects_authority_or_scope_drift(
    mutate: object,
    failure_fragment: str,
) -> None:
    contract = copy.deepcopy(_contract())
    assert callable(mutate)
    mutate(contract)
    failures: list[str] = []

    gate._validate_contract(contract, failures)  # type: ignore[arg-type] # noqa: SLF001

    assert any(failure_fragment in failure for failure in failures)


@pytest.mark.parametrize(
    ("legacy_field", "explicit_field"),
    [
        ("attempt_disposition_json", "attempt_001_disposition_json"),
        ("attempt_disposition_json_sha256", "attempt_001_disposition_json_sha256"),
        ("attempt_disposition_document", "attempt_001_disposition_document"),
        (
            "attempt_disposition_document_sha256",
            "attempt_001_disposition_document_sha256",
        ),
        ("attempt_id", "attempt_001_id"),
        ("attempted_candidate_commit", "attempt_001_attempted_candidate_commit"),
        ("attempted_candidate_tree", "attempt_001_attempted_candidate_tree"),
        (
            "attempted_authorization_contract_sha256",
            "attempt_001_attempted_authorization_contract_sha256",
        ),
        ("attempt_invocation", "attempt_001_invocation"),
        ("attempt_root_absence", "attempt_001_root_absence"),
    ],
)
def test_contract_rejects_ambiguous_legacy_attempt_001_top_level_fields(
    legacy_field: str,
    explicit_field: str,
) -> None:
    contract = copy.deepcopy(_contract())
    contract[legacy_field] = copy.deepcopy(contract[explicit_field])
    failures: list[str] = []

    gate._validate_contract(contract, failures)  # type: ignore[arg-type] # noqa: SLF001

    assert "O4 execution authorization fields are not closed" in failures


def test_authorization_json_rejects_duplicate_keys(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text('{"schema_version":"1","schema_version":"2"}\n', encoding="utf-8")
    failures: list[str] = []

    result = gate._read_contract(path, failures)  # noqa: SLF001

    assert result == {}
    assert failures == ["O4 execution authorization JSON is unavailable or ambiguous"]


def test_disposition_rejects_static_child_self_reference() -> None:
    disposition = json.loads(gate.DISPOSITION_JSON.read_text(encoding="utf-8"))
    disposition["execution_candidate_commit"] = "a" * 40
    failures: list[str] = []

    gate._validate_disposition(  # noqa: SLF001
        disposition,
        gate.DISPOSITION_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert "O4 post-review disposition is not closed and exact" in failures


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value["attempt_contract"].__setitem__(  # type: ignore[union-attr]
            "maximum_supervised_invocations", True
        ),
        lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
            "producer_code_authorized", 1
        ),
        lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
            "release_allowed", 0
        ),
    ],
)
def test_disposition_rejects_bool_int_type_substitution(mutate: object) -> None:
    disposition = json.loads(gate.DISPOSITION_JSON.read_text(encoding="utf-8"))
    assert callable(mutate)
    mutate(disposition)
    failures: list[str] = []

    gate._validate_disposition(  # noqa: SLF001
        disposition,
        gate.DISPOSITION_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert "O4 post-review disposition is not closed and exact" in failures


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.__setitem__("attempted_candidate_commit", "a" * 40),
        lambda value: value["invocation"].__setitem__(  # type: ignore[union-attr]
            "command", "uv run python wrong.py"
        ),
        lambda value: value["invocation"].__setitem__(  # type: ignore[union-attr]
            "classification", "SUCCESS"
        ),
        lambda value: value["invocation"].__setitem__(  # type: ignore[union-attr]
            "exit_code", 0
        ),
        lambda value: value["observed_root_absence"]["roots"][0].__setitem__(  # type: ignore[index,union-attr]
            "exists", True
        ),
        lambda value: value["external_action_observation"].__setitem__(  # type: ignore[union-attr]
            "docker_action_performed", True
        ),
        lambda value: value["external_action_observation"].__setitem__(  # type: ignore[union-attr]
            "runtime_created", True
        ),
        lambda value: value["attempt_contract"].__setitem__(  # type: ignore[union-attr]
            "attempt_consumed", False
        ),
        lambda value: value["attempt_contract"].__setitem__(  # type: ignore[union-attr]
            "retry_authorized", True
        ),
        lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
            "o4_evidence_execution_authorized", True
        ),
        lambda value: value.__setitem__("closure_commit", "b" * 40),
    ],
)
def test_attempt_001_disposition_rejects_false_or_expansive_claims(
    mutate: object,
) -> None:
    disposition = json.loads(gate.ATTEMPT_001_DISPOSITION_JSON.read_text(encoding="utf-8"))
    assert callable(mutate)
    mutate(disposition)
    failures: list[str] = []

    gate._validate_attempt_001_disposition(  # noqa: SLF001
        disposition,
        gate.ATTEMPT_001_DISPOSITION_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert "O4 Attempt 001 disposition is not closed and exact" in failures


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.__setitem__("candidate_parent_commit", "a" * 40),
        lambda value: value.__setitem__("operator_command", gate.FAILED_FILE_PATH_INVOCATION),
        lambda value: value.__setitem__("module_command", gate.FAILED_FILE_PATH_INVOCATION),
        lambda value: value.__setitem__("failed_file_path_command_authorized", True),
        lambda value: value["attempt_001_history"].__setitem__(  # type: ignore[union-attr]
            "disposition_json_sha256", "sha256:" + "0" * 64
        ),
        lambda value: value["attempt_001_history"].__setitem__(  # type: ignore[union-attr]
            "consumed", False
        ),
        lambda value: value["attempt_contract"].__setitem__(  # type: ignore[union-attr]
            "maximum_supervised_invocations", 2
        ),
        lambda value: value["attempt_contract"].__setitem__(  # type: ignore[union-attr]
            "maximum_supervised_invocations", True
        ),
        lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
            "producer_code_authorized", False
        ),
        lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
            "shell_execution_authorized", True
        ),
        lambda value: value.__setitem__("execution_candidate_commit", "b" * 40),
    ],
)
def test_attempt_002_disposition_rejects_lineage_command_history_or_authority_drift(
    mutate: object,
) -> None:
    disposition = json.loads(gate.ATTEMPT_002_DISPOSITION_JSON.read_text(encoding="utf-8"))
    assert callable(mutate)
    mutate(disposition)
    failures: list[str] = []

    gate._validate_attempt_002_disposition(  # noqa: SLF001
        disposition,
        gate.ATTEMPT_002_DISPOSITION_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert "O4 Attempt 002 disposition is not closed and exact" in failures


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.__setitem__("record_status", "SUCCESS"),
        lambda value: value.__setitem__("attempted_candidate_commit", "a" * 40),
        lambda value: value.__setitem__("operator_command", gate.PRODUCER_MODULE_INVOCATION),
        lambda value: value.__setitem__("failure_code", "success"),
        lambda value: value["read_only_residue_observation"].__setitem__(  # type: ignore[union-attr]
            "cleanup_completed_claimed", True
        ),
        lambda value: value["read_only_residue_observation"].__setitem__(  # type: ignore[union-attr]
            "general_docker_absence_claimed", True
        ),
        lambda value: value["read_only_residue_observation"].__setitem__(  # type: ignore[union-attr]
            "exact_project_label_containers", 1
        ),
        lambda value: value["external_action_observation"].__setitem__(  # type: ignore[union-attr]
            "docker_mutation_performed", True
        ),
        lambda value: value["external_action_observation"].__setitem__(  # type: ignore[union-attr]
            "successful_evidence_created", True
        ),
        lambda value: value["retained_receipt"].__setitem__(  # type: ignore[union-attr]
            "candidate_manifest_sha256", "sha256:" + "0" * 64
        ),
        lambda value: value["attempt_contract"].__setitem__(  # type: ignore[union-attr]
            "attempt_consumed", False
        ),
        lambda value: value["attempt_contract"].__setitem__(  # type: ignore[union-attr]
            "retry_authorized", True
        ),
        lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
            "docker_lifecycle_authorized", True
        ),
    ],
)
def test_attempt_002_closure_rejects_false_or_expansive_claims(
    mutate: object,
) -> None:
    closure = json.loads(gate.ATTEMPT_002_CLOSURE_JSON.read_text(encoding="utf-8"))
    assert callable(mutate)
    mutate(closure)
    failures: list[str] = []

    gate._validate_attempt_002_closure(  # noqa: SLF001
        closure,
        gate.ATTEMPT_002_CLOSURE_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert "O4 Attempt 002 closure is not closed and exact" in failures


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.__setitem__("candidate_parent_commit", "a" * 40),
        lambda value: value.__setitem__("compose_repair_review_sha256", "sha256:" + "0" * 64),
        lambda value: value["repaired_source_digests"].__setitem__(  # type: ignore[union-attr]
            "overlay_compose_sha256", "sha256:" + "0" * 64
        ),
        lambda value: value["attempt_002_history"].__setitem__(  # type: ignore[union-attr]
            "consumed", False
        ),
        lambda value: value["control_path_allowlist"].pop(),  # type: ignore[union-attr]
        lambda value: value["prior_attempt_evidence_contract"].__setitem__(  # type: ignore[union-attr]
            "attempt_002_retained_evidence_required", False
        ),
        lambda value: value["prior_attempt_evidence_contract"].__setitem__(  # type: ignore[union-attr]
            "unknown_or_additional_attempt_roots_authorized", True
        ),
        lambda value: value["attempt_contract"].__setitem__(  # type: ignore[union-attr]
            "maximum_supervised_invocations", 2
        ),
        lambda value: value["attempt_contract"].__setitem__(  # type: ignore[union-attr]
            "automatic_retry_authorized", True
        ),
        lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
            "docker_lifecycle_authorized", False
        ),
        lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
            "shell_execution_authorized", True
        ),
    ],
)
def test_attempt_003_disposition_rejects_scope_history_or_authority_drift(
    mutate: object,
) -> None:
    disposition = json.loads(gate.ATTEMPT_003_DISPOSITION_JSON.read_text(encoding="utf-8"))
    assert callable(mutate)
    mutate(disposition)
    failures: list[str] = []

    gate._validate_attempt_003_disposition(  # noqa: SLF001
        disposition,
        gate.ATTEMPT_003_DISPOSITION_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert "O4 Attempt 003 disposition is not closed and exact" in failures


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value["diagnosis"].__setitem__(  # type: ignore[union-attr]
            "bridge_image_build_failure_proven", True
        ),
        lambda value: value["diagnosis"].__setitem__(  # type: ignore[union-attr]
            "primary_error_presence_known", True
        ),
        lambda value: value["diagnosis"].__setitem__(  # type: ignore[union-attr]
            "primary_error_value_known", True
        ),
        lambda value: value["diagnosis"].__setitem__(  # type: ignore[union-attr]
            "final_recovery_required_may_have_replaced_primary_or_originated_in_cleanup",
            False,
        ),
        lambda value: value["read_only_residue_observation"].__setitem__(  # type: ignore[union-attr]
            "current_live_truth_claimed", True
        ),
        lambda value: value["read_only_residue_observation"].__setitem__(  # type: ignore[union-attr]
            "images_removed", True
        ),
        lambda value: value["tracked_closure_scope"].pop(),  # type: ignore[union-attr]
        lambda value: value["attempt_contract"].__setitem__(  # type: ignore[union-attr]
            "recovery_action_authorized", True
        ),
        lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
            "docker_lifecycle_authorized", True
        ),
    ],
)
def test_attempt_003_closure_rejects_diagnosis_scope_or_authority_drift(
    mutate: object,
) -> None:
    closure = json.loads(gate.ATTEMPT_003_CLOSURE_JSON.read_text(encoding="utf-8"))
    assert callable(mutate)
    mutate(closure)
    failures: list[str] = []

    gate._validate_attempt_003_closure(  # noqa: SLF001
        closure,
        gate.ATTEMPT_003_CLOSURE_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert "O4 Attempt 003 closure is not closed and exact" in failures


def test_image_recovery_history_rejects_receipt_or_authority_drift() -> None:
    authorization = json.loads(gate.IMAGE_RECOVERY_AUTHORIZATION.read_text(encoding="utf-8"))
    closure = json.loads(gate.IMAGE_RECOVERY_CLOSURE.read_text(encoding="utf-8"))
    authorization["durable_consumption_receipt"]["receipt_sha256"] = (  # type: ignore[index]
        "sha256:" + "0" * 64
    )
    closure["o4_authority"]["docker_lifecycle_authorized"] = True  # type: ignore[index]
    failures: list[str] = []

    gate._validate_image_recovery_history(  # noqa: SLF001
        authorization,
        gate.IMAGE_RECOVERY_AUTHORIZATION_DOCUMENT.read_text(encoding="utf-8"),
        closure,
        gate.IMAGE_RECOVERY_CLOSURE_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert "O4 image recovery authorization closure is not exact" in failures
    assert "O4 image recovery result closure is not exact" in failures


def test_runtime_native_repair_review_is_exact() -> None:
    failures: list[str] = []

    gate._validate_runtime_native_repair_review(  # noqa: SLF001
        gate.RUNTIME_NATIVE_REPAIR_REVIEW.read_text(encoding="utf-8"),
        failures,
    )

    assert failures == []


@pytest.mark.parametrize(
    "mutation",
    [
        "candidate",
        "primary_failure",
        "cleanup_claim",
        "image_recovery",
        "authority",
        "scope",
    ],
)
def test_attempt_004_disposition_rejects_false_or_expansive_claims(
    mutation: str,
) -> None:
    disposition = json.loads(gate.ATTEMPT_004_DISPOSITION_JSON.read_text(encoding="utf-8"))
    if mutation == "candidate":
        disposition["attempted_candidate_commit"] = "a" * 40
    elif mutation == "primary_failure":
        disposition["diagnostic_facts"]["primary_failure_code"] = "success"
    elif mutation == "cleanup_claim":
        disposition["point_in_time_post_attempt_observation"]["cleanup_completed_claimed"] = True
    elif mutation == "image_recovery":
        disposition["attempt_contract"]["image_recovery_authorized"] = True
    elif mutation == "authority":
        disposition["authority"]["docker_lifecycle_authorized"] = True
    else:
        disposition["tracked_closure_scope"].pop()
    failures: list[str] = []

    gate._validate_attempt_004_disposition(  # noqa: SLF001
        disposition,
        gate.ATTEMPT_004_DISPOSITION_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert failures


def _snapshot_expectation(content: bytes) -> tuple[int, str, bytes]:
    return (
        0o400,
        "sha256:" + hashlib.sha256(content).hexdigest(),
        content,
    )


def _small_snapshot(
    tmp_path: Path,
) -> tuple[
    Path,
    dict[str, tuple[int, str, bytes]],
]:
    root = tmp_path / "candidate"
    nested = root / "nested"
    nested.mkdir(parents=True)
    (root / "input.txt").write_bytes(b"alpha")
    (nested / "data.bin").write_bytes(b"\x00\x01")
    (root / "input.txt").chmod(0o400)
    (nested / "data.bin").chmod(0o400)
    nested.chmod(0o500)
    root.chmod(0o500)
    return root, {
        "input.txt": _snapshot_expectation(b"alpha"),
        "nested/data.bin": _snapshot_expectation(b"\x00\x01"),
    }


def _unlock_snapshot(root: Path) -> None:
    for directory, directories, files in os.walk(root, topdown=False):
        for name in files:
            path = Path(directory) / name
            if not path.is_symlink():
                path.chmod(0o600)
        for name in directories:
            path = Path(directory) / name
            if not path.is_symlink():
                path.chmod(0o700)
        Path(directory).chmod(0o700)


def test_small_snapshot_no_follow_validator_accepts_exact_tree(
    tmp_path: Path,
) -> None:
    root, expected = _small_snapshot(tmp_path)
    failures: list[str] = []
    descriptor = gate._open_owned_directory(  # noqa: SLF001
        root,
        0o500,
        "test snapshot",
        failures,
    )
    assert descriptor is not None
    try:
        observed = gate._validate_snapshot_directory(  # noqa: SLF001
            descriptor,
            expected,
            failures,
        )
    finally:
        os.close(descriptor)
        _unlock_snapshot(root)

    assert observed == set(expected)
    assert failures == []


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "tampered",
        "chmod",
        "extra",
        "extra_directory",
        "symlink",
        "special",
    ],
)
def test_small_snapshot_no_follow_validator_rejects_tree_drift(
    tmp_path: Path,
    mutation: str,
) -> None:
    root, expected = _small_snapshot(tmp_path)
    nested = root / "nested"
    if mutation == "missing":
        nested.chmod(0o700)
        (nested / "data.bin").unlink()
        nested.chmod(0o500)
    elif mutation == "tampered":
        target = root / "input.txt"
        target.chmod(0o600)
        target.write_bytes(b"omega")
        target.chmod(0o400)
    elif mutation == "chmod":
        (root / "input.txt").chmod(0o600)
    else:
        root.chmod(0o700)
        if mutation == "extra":
            (root / "extra.txt").write_text("extra\n", encoding="utf-8")
            (root / "extra.txt").chmod(0o400)
        elif mutation == "extra_directory":
            (root / "extra").mkdir(mode=0o500)
        elif mutation == "symlink":
            (root / "extra").symlink_to("input.txt")
        else:
            os.mkfifo(root / "extra", 0o400)
        root.chmod(0o500)
    failures: list[str] = []
    descriptor = gate._open_owned_directory(  # noqa: SLF001
        root,
        0o500,
        "test snapshot",
        failures,
    )
    assert descriptor is not None
    try:
        observed = gate._validate_snapshot_directory(  # noqa: SLF001
            descriptor,
            expected,
            failures,
        )
    finally:
        os.close(descriptor)
        _unlock_snapshot(root)

    assert failures or observed != set(expected)


@pytest.mark.parametrize(
    "mutation",
    [
        "extra_runtime_entry",
        "tampered_recovery_receipt",
        "run_directory",
        "published_report",
        "runtime_chmod",
    ],
)
def test_runtime_posture_rejects_population_report_or_mode_drift(
    tmp_path: Path,
    mutation: str,
) -> None:
    runtime_base = tmp_path / gate.ATTEMPT_002_RUNTIME_BASE
    runtime_base.mkdir(parents=True, mode=0o700)
    runtime_base.chmod(0o700)
    recovery_receipt = tmp_path / gate.IMAGE_RECOVERY_CONSUMPTION_RECEIPT
    recovery_receipt.write_bytes(gate.IMAGE_RECOVERY_CONSUMPTION_RECEIPT_BYTES)
    recovery_receipt.chmod(0o600)
    if mutation == "extra_runtime_entry":
        (runtime_base / "unexpected").write_text("x\n", encoding="utf-8")
    elif mutation == "tampered_recovery_receipt":
        recovery_receipt.write_bytes(b"x" * len(gate.IMAGE_RECOVERY_CONSUMPTION_RECEIPT_BYTES))
        recovery_receipt.chmod(0o600)
    elif mutation == "run_directory":
        (tmp_path / gate.ATTEMPT_002_RUNTIME_ROOT).mkdir(mode=0o700)
    elif mutation == "published_report":
        (tmp_path / gate.ATTEMPT_002_REPORT_ROOT).mkdir(
            parents=True,
            mode=0o700,
        )
    else:
        runtime_base.chmod(0o755)
    failures: list[str] = []

    gate._validate_attempt_002_runtime_posture(tmp_path, failures)  # noqa: SLF001

    assert failures


def test_descriptor_traversal_rejects_symlinked_var(
    tmp_path: Path,
) -> None:
    target_var = tmp_path / "target-var"
    runtime_base = target_var / "local-v1-lv1-003-o4-runtime"
    runtime_base.mkdir(parents=True, mode=0o700)
    runtime_base.chmod(0o700)
    (tmp_path / "var").symlink_to(target_var, target_is_directory=True)
    failures: list[str] = []

    gate._validate_attempt_002_runtime_posture(tmp_path, failures)  # noqa: SLF001

    assert failures
    assert any("component var" in failure or "ancestor" in failure for failure in failures)


def test_descriptor_traversal_rejects_symlinked_receipt_base(
    tmp_path: Path,
) -> None:
    var = tmp_path / "var"
    var.mkdir()
    runtime_base = var / "local-v1-lv1-003-o4-runtime"
    runtime_base.mkdir(mode=0o700)
    external_receipts = tmp_path / "external-receipts"
    external_receipts.mkdir(mode=0o700)
    (var / "local-v1-lv1-003-o4-receipts").symlink_to(
        external_receipts,
        target_is_directory=True,
    )
    failures: list[str] = []

    gate._validate_retained_attempt_evidence(tmp_path, failures)  # noqa: SLF001

    assert failures
    assert any("local-v1-lv1-003-o4-receipts" in failure for failure in failures)


def test_evidence_ignore_patterns_and_closure_scopes_are_exact() -> None:
    failures: list[str] = []

    gate._validate_evidence_ignore_patterns(ROOT, failures)  # noqa: SLF001
    closure = json.loads(gate.ATTEMPT_002_CLOSURE_JSON.read_text(encoding="utf-8"))

    assert failures == []
    assert closure["tracked_closure_scope"] == gate.CLOSURE_CONTROL_PATH_ALLOWLIST
    assert len(gate.CLOSURE_CONTROL_PATH_ALLOWLIST) == 7
    assert gate.CLOSURE_CONTROL_PATH_ALLOWLIST[0] == ".gitignore"
    attempt_003_closure = json.loads(gate.ATTEMPT_003_CLOSURE_JSON.read_text(encoding="utf-8"))
    assert (
        attempt_003_closure["tracked_closure_scope"]
        == gate.ATTEMPT_003_CLOSURE_CONTROL_PATH_ALLOWLIST
    )
    assert len(gate.ATTEMPT_003_CLOSURE_CONTROL_PATH_ALLOWLIST) == 6
    assert gate.ATTEMPT_004_CONTROL_PATH_ALLOWLIST == [
        "Makefile",
        "README.md",
        gate.CONTRACT.as_posix(),
        gate.DOCUMENT.as_posix(),
        gate.RUNTIME_NATIVE_REPAIR_REVIEW.as_posix(),
        "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
        "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
    ]
    assert gate.ATTEMPT_004_CLOSURE_CONTROL_PATH_ALLOWLIST == [
        "Makefile",
        "README.md",
        gate.ATTEMPT_004_DISPOSITION_JSON.as_posix(),
        gate.ATTEMPT_004_DISPOSITION_DOCUMENT.as_posix(),
        gate.CONTRACT.as_posix(),
        gate.DOCUMENT.as_posix(),
        "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
        "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
    ]
    assert gate.ATTEMPT_005_CLOSURE_CONTROL_PATH_ALLOWLIST == [
        "Makefile",
        "README.md",
        gate.ATTEMPT_005_DISPOSITION_JSON.as_posix(),
        gate.ATTEMPT_005_DISPOSITION_DOCUMENT.as_posix(),
        gate.CONTRACT.as_posix(),
        gate.DOCUMENT.as_posix(),
        "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
        "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
    ]
    assert gate.ATTEMPT_006_CONTROL_PATH_ALLOWLIST == [
        "Makefile",
        "README.md",
        gate.API_CONTAINER_STATE_DIAGNOSTIC_REVIEW.as_posix(),
        gate.CONTRACT.as_posix(),
        gate.DOCUMENT.as_posix(),
        "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
        "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
    ]
    assert gate.ATTEMPT_006_CLOSURE_CONTROL_PATH_ALLOWLIST == [
        "Makefile",
        "README.md",
        gate.ATTEMPT_006_DISPOSITION_JSON.as_posix(),
        gate.ATTEMPT_006_DISPOSITION_DOCUMENT.as_posix(),
        gate.CONTRACT.as_posix(),
        gate.DOCUMENT.as_posix(),
        "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
        "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
    ]
    assert gate.ATTEMPT_007_CONTROL_PATH_ALLOWLIST == [
        "Makefile",
        "README.md",
        gate.APPLICATION_STARTUP_STAGE_DIAGNOSTIC_REVIEW.as_posix(),
        gate.CONTRACT.as_posix(),
        gate.DOCUMENT.as_posix(),
        "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
        "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
    ]
    assert gate.ATTEMPT_007_CLOSURE_CONTROL_PATH_ALLOWLIST == [
        "Makefile",
        "README.md",
        gate.ATTEMPT_007_DISPOSITION_JSON.as_posix(),
        gate.ATTEMPT_007_DISPOSITION_DOCUMENT.as_posix(),
        gate.CONTRACT.as_posix(),
        gate.DOCUMENT.as_posix(),
        "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
        "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
    ]
    assert gate.ATTEMPT_008_CONTROL_PATH_ALLOWLIST == [
        "Makefile",
        "README.md",
        gate.CONTRACT.as_posix(),
        gate.DOCUMENT.as_posix(),
        gate.IMAGE_READABILITY_REPAIR_REVIEW.as_posix(),
        "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
        "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
    ]
    assert gate.ATTEMPT_008_CLOSURE_CONTROL_PATH_ALLOWLIST == [
        "Makefile",
        "README.md",
        gate.ATTEMPT_008_DISPOSITION_JSON.as_posix(),
        gate.ATTEMPT_008_DISPOSITION_DOCUMENT.as_posix(),
        gate.CONTRACT.as_posix(),
        gate.DOCUMENT.as_posix(),
        "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
        "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
    ]
    assert gate.ATTEMPT_009_CONTROL_PATH_ALLOWLIST == [
        "Makefile",
        "README.md",
        gate.ENROLLMENT_OUTPUT_PROJECTION_REPAIR_REVIEW.as_posix(),
        gate.CONTRACT.as_posix(),
        gate.DOCUMENT.as_posix(),
        "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
        "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
    ]
    assert gate.ATTEMPT_009_CLOSURE_CONTROL_PATH_ALLOWLIST == [
        "Makefile",
        "README.md",
        gate.ATTEMPT_009_DISPOSITION_JSON.as_posix(),
        gate.ATTEMPT_009_DISPOSITION_DOCUMENT.as_posix(),
        gate.CONTRACT.as_posix(),
        gate.DOCUMENT.as_posix(),
        "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
        "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
    ]


@pytest.mark.parametrize(
    "contents",
    [
        "\n".join(gate.EVIDENCE_IGNORE_PATTERNS[1:]) + "\n",
        "\n".join(gate.EVIDENCE_IGNORE_PATTERNS + ["var/**"]) + "\n",
        "\n".join(gate.EVIDENCE_IGNORE_PATTERNS + [gate.EVIDENCE_IGNORE_PATTERNS[0]]) + "\n",
    ],
)
def test_evidence_ignore_patterns_reject_missing_broad_or_duplicate_rules(
    tmp_path: Path,
    contents: str,
) -> None:
    (tmp_path / ".gitignore").write_text(contents, encoding="utf-8")
    failures: list[str] = []

    gate._validate_evidence_ignore_patterns(tmp_path, failures)  # noqa: SLF001

    assert failures


def test_attempt_001_history_files_remain_byte_exact() -> None:
    failures: list[str] = []

    assert (
        gate._file_digest(gate.ATTEMPT_001_DISPOSITION_JSON, failures)  # noqa: SLF001
        == gate.ATTEMPT_001_DISPOSITION_JSON_DIGEST
    )
    assert (
        gate._file_digest(gate.ATTEMPT_001_DISPOSITION_DOCUMENT, failures)  # noqa: SLF001
        == gate.ATTEMPT_001_DISPOSITION_DOCUMENT_DIGEST
    )
    assert failures == []


def test_bound_review_or_disposition_digest_drift_is_rejected(
    tmp_path: Path,
) -> None:
    for relative in (
        gate.PRODUCER_EXACT_REVIEW,
        gate.DISPOSITION_JSON,
        gate.DISPOSITION_DOCUMENT,
        gate.ATTEMPT_001_DISPOSITION_JSON,
        gate.ATTEMPT_001_DISPOSITION_DOCUMENT,
        gate.ENTRYPOINT_REPAIR_REVIEW,
        gate.ATTEMPT_002_DISPOSITION_JSON,
        gate.ATTEMPT_002_DISPOSITION_DOCUMENT,
        gate.ATTEMPT_002_CLOSURE_JSON,
        gate.ATTEMPT_002_CLOSURE_DOCUMENT,
        gate.COMPOSE_REPAIR_REVIEW,
        gate.ATTEMPT_003_DISPOSITION_JSON,
        gate.ATTEMPT_003_DISPOSITION_DOCUMENT,
        gate.ATTEMPT_003_CLOSURE_JSON,
        gate.ATTEMPT_003_CLOSURE_DOCUMENT,
        gate.IMAGE_RECOVERY_AUTHORIZATION,
        gate.IMAGE_RECOVERY_AUTHORIZATION_DOCUMENT,
        gate.IMAGE_RECOVERY_CLOSURE,
        gate.IMAGE_RECOVERY_CLOSURE_DOCUMENT,
        gate.RUNTIME_NATIVE_REPAIR_REVIEW,
        gate.ATTEMPT_004_DISPOSITION_JSON,
        gate.ATTEMPT_004_DISPOSITION_DOCUMENT,
        gate.DIAGNOSTIC_REPAIR_REVIEW,
        gate.IMAGE_READABILITY_REPAIR_REVIEW,
        gate.ATTEMPT_008_DISPOSITION_JSON,
        gate.ATTEMPT_008_DISPOSITION_DOCUMENT,
        gate.ENROLLMENT_OUTPUT_PROJECTION_REPAIR_REVIEW,
        gate.ATTEMPT_009_DISPOSITION_JSON,
        gate.ATTEMPT_009_DISPOSITION_DOCUMENT,
    ):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, destination)
    (tmp_path / gate.ENROLLMENT_OUTPUT_PROJECTION_REPAIR_REVIEW).write_text(
        "altered\n",
        encoding="utf-8",
    )
    failures: list[str] = []

    gate._validate_bound_documents(tmp_path, failures)  # noqa: SLF001

    assert any(
        "enrollment-output projection repair exact review digest" in value for value in failures
    )


def test_execution_checkout_rejects_descendant_dirty_and_extra_path(
    tmp_path: Path,
) -> None:
    repo, _, _ = _attempt_009_closure_child_repository(tmp_path)
    (repo / "extra-control.txt").write_text("extra\n", encoding="utf-8")
    failures: list[str] = []
    gate._validate_execution_checkout(repo, failures)  # noqa: SLF001
    assert any("not clean" in value for value in failures)

    _run_git(repo, "add", "extra-control.txt")
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: forbidden descendant",
    )
    failures = []
    gate._validate_execution_checkout(repo, failures)  # noqa: SLF001
    assert any("not a single immediate child" in value for value in failures)
    assert any("not the exact control allowlist" in value for value in failures)


def test_execution_checkout_rejects_sibling_of_reviewed_parent(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "sibling"
    subprocess.run(["git", "clone", "-q", str(Path.cwd()), str(repo)], check=True)
    _run_git(
        repo,
        "checkout",
        "--detach",
        f"{gate.ATTEMPT_009_CANDIDATE_COMMIT}^",
    )
    for relative in gate.ATTEMPT_009_CLOSURE_CONTROL_PATH_ALLOWLIST:
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, destination)
    _run_git(repo, "add", "--", *gate.ATTEMPT_009_CLOSURE_CONTROL_PATH_ALLOWLIST)
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: wrong sibling",
    )
    failures: list[str] = []

    gate._validate_execution_checkout(repo, failures)  # noqa: SLF001

    assert any("not a single immediate child" in value for value in failures)


def test_execution_checkout_rejects_non_control_drift(tmp_path: Path) -> None:
    repo, _, _ = _attempt_009_closure_child_repository(tmp_path)
    makefile = repo / "Makefile"
    makefile.write_text(
        makefile.read_text(encoding="utf-8") + "\n# repair drift\n",
        encoding="utf-8",
    )
    _run_git(repo, "add", "Makefile")
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: forbidden repair drift",
    )
    failures: list[str] = []

    gate._validate_execution_checkout(repo, failures)  # noqa: SLF001

    assert any("not a single immediate child" in value for value in failures)
    assert any("not the exact control allowlist" in value for value in failures)


def test_execution_checkout_rejects_runtime_byte_drift(tmp_path: Path) -> None:
    repo = tmp_path / "tiny-runtime"
    repo.mkdir()
    _run_git(repo, "init", "-q")
    (repo / "runtime.txt").write_text("reviewed\n", encoding="utf-8")
    _run_git(repo, "add", "runtime.txt")
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "reviewed runtime",
    )
    reviewed = _run_git(repo, "rev-parse", "HEAD")
    parent_tree = _run_git(repo, "show", "-s", "--format=%T", "HEAD")
    (repo / "control.txt").write_text("control\n", encoding="utf-8")
    (repo / "runtime.txt").write_text("drift\n", encoding="utf-8")
    _run_git(repo, "add", "control.txt", "runtime.txt")
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "candidate drift",
    )
    failures: list[str] = []

    gate._validate_execution_checkout(  # noqa: SLF001
        repo,
        failures,
        candidate_parent_commit=reviewed,
        candidate_parent_tree=parent_tree,
        reviewed_commit=reviewed,
        runtime_paths=["runtime.txt"],
        control_paths=["control.txt", "runtime.txt"],
        repair_paths=[],
    )

    assert any("runtime differs from the exact reviewed candidate" in value for value in failures)


def test_prior_attempt_roots_fail_closed_on_retained_or_unsafe_evidence(
    tmp_path: Path,
) -> None:
    safe_root = tmp_path / gate.PRIOR_ATTEMPT_ROOTS[0]
    safe_root.mkdir(parents=True, mode=0o700)
    safe_root.chmod(0o700)
    failures: list[str] = []
    gate._validate_prior_attempt_posture(tmp_path, failures)  # noqa: SLF001
    assert failures == []

    (safe_root / "attempt.json").write_text("{}\n", encoding="utf-8")
    failures = []
    gate._validate_prior_attempt_posture(tmp_path, failures)  # noqa: SLF001
    assert any("prior attempt or success evidence exists" in value for value in failures)

    (safe_root / "attempt.json").unlink()
    safe_root.chmod(0o755)
    failures = []
    gate._validate_prior_attempt_posture(tmp_path, failures)  # noqa: SLF001
    assert any("mode is not 0700" in value for value in failures)


def test_attempt_001_recorded_root_absence_rejects_any_present_root(
    tmp_path: Path,
) -> None:
    failures: list[str] = []
    gate._validate_recorded_root_absence(tmp_path, failures)  # noqa: SLF001
    assert failures == []

    present = tmp_path / gate.PRIOR_ATTEMPT_ROOTS[1]
    present.mkdir(parents=True)
    failures = []
    gate._validate_recorded_root_absence(tmp_path, failures)  # noqa: SLF001

    assert failures == [
        "O4 Attempt 001 observed-absent root is now present: var/local-v1-lv1-003-o4-runtime"
    ]


def test_source_binding_rejects_profile_or_compose_drift(tmp_path: Path) -> None:
    contract = _contract()
    for _, (relative, _) in gate.SOURCE_DIGESTS.items():
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, destination)
    overlay = tmp_path / "deploy/hermes-node-bridge/compose.yaml"
    overlay.write_text(overlay.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8")
    failures: list[str] = []

    gate._validate_source_bindings(  # noqa: SLF001
        tmp_path,
        contract,  # type: ignore[arg-type]
        failures,
    )

    assert any("overlay_compose_sha256" in failure for failure in failures)


def test_producer_contract_closes_sequence_no_retry_and_runtime_unknowns() -> None:
    document = gate.PRODUCER_CONTRACT.read_text(encoding="utf-8")
    failures: list[str] = []

    gate._validate_producer_contract(  # noqa: SLF001
        document,
        _contract(),  # type: ignore[arg-type]
        failures,
    )

    assert failures == []
    assert gate._digest(document) == gate.PRODUCER_CONTRACT_DIGEST  # noqa: SLF001
    assert document.count("Hermes service exactly once") == 1
    assert "There is no automatic retry" in " ".join(document.split())
    assert "Runtime-Only Facts Still Unproven" in document
    assert (
        "do not prove absence of transient malicious same-UID mutation while Docker reads "
        "the build context"
    ) in " ".join(document.split())
    assert "writes and verifies `node-revocation-recovery.json`" in " ".join(document.split())


@pytest.mark.parametrize(
    "drift",
    [
        lambda document: document.replace("17. Write", "18. Write", 1),
        lambda document: document.replace(
            "Agent Run record status\n    `active`",
            "Agent Run record status\n    `completed`",
            1,
        ),
        lambda document: document.replace(
            "route stdout and stderr directly to\n    `DEVNULL`",
            "capture stdout and stderr",
            1,
        ),
    ],
)
def test_producer_contract_rejects_stage_truth_or_output_custody_drift(
    drift: object,
) -> None:
    document = gate.PRODUCER_CONTRACT.read_text(encoding="utf-8")
    assert callable(drift)
    failures: list[str] = []
    drifted = drift(document)
    assert drifted != document

    gate._validate_producer_contract(  # noqa: SLF001
        drifted,
        _contract(),  # type: ignore[arg-type,operator]
        failures,
    )

    assert failures


def test_producer_contract_digest_is_bound_in_gate() -> None:
    contract = _contract()
    failures: list[str] = []
    contract["producer_contract_sha256"] = "sha256:" + "0" * 64

    gate._validate_producer_contract(  # noqa: SLF001
        gate.PRODUCER_CONTRACT.read_text(encoding="utf-8"),
        contract,  # type: ignore[arg-type]
        failures,
    )

    assert "O4 producer contract digest binding is invalid" in failures


def test_make_wiring_is_non_live_and_not_a_release_dependency() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    release_header = next(
        line for line in makefile.splitlines() if line.startswith("release-check:")
    )

    assert gate.AUTHORIZATION_TARGET not in release_header
    assert gate.PRODUCER_STATIC_TARGET not in release_header
    assert "local-v1-lv1-003-o4-live" not in makefile
    assert "docker compose" not in gate._target_body(  # noqa: SLF001
        makefile,
        gate.AUTHORIZATION_TARGET,
    )
    assert "docker compose" not in gate._target_body(  # noqa: SLF001
        makefile,
        gate.PRODUCER_STATIC_TARGET,
    )


def test_module_entrypoint_imports_without_executing_main_or_creating_runtime() -> None:
    run_root = ROOT / "var/local-v1-lv1-003-o4-runtime" / gate.ATTEMPT_002_RUN_ID
    disposition = (
        ROOT / "var/local-v1-lv1-003-o4-receipts" / gate.ATTEMPT_002_RUN_ID / "disposition.json"
    )
    manifest = disposition.with_name("candidate-manifest.json")
    assert not run_root.exists()
    disposition_digest = gate._file_digest(disposition, [])  # noqa: SLF001
    manifest_digest = gate._file_digest(manifest, [])  # noqa: SLF001

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from scripts import local_v1_lv1_003_o4_producer as producer;"
                "assert callable(producer.main)"
            ),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
    assert not run_root.exists()
    assert gate._file_digest(disposition, []) == disposition_digest  # noqa: SLF001
    assert gate._file_digest(manifest, []) == manifest_digest  # noqa: SLF001


def test_live_module_make_target_is_exact_unique_and_not_transitively_wired() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert makefile.count(gate.PRODUCER_RUN_TARGET) == 2
    assert sum(line == f"{gate.PRODUCER_RUN_TARGET}:" for line in makefile.splitlines()) == 1
    assert (
        gate._target_body(  # noqa: SLF001
            makefile,
            gate.PRODUCER_RUN_TARGET,
        ).strip()
        == gate.PRODUCER_MODULE_INVOCATION
    )
    assert gate.FAILED_FILE_PATH_INVOCATION not in gate._target_body(  # noqa: SLF001
        makefile,
        gate.PRODUCER_RUN_TARGET,
    )
    for parent_target in (
        "release-check",
        "local-v1-milestone-check",
        gate.PRODUCER_STATIC_TARGET,
        gate.AUTHORIZATION_TARGET,
    ):
        assert gate.PRODUCER_RUN_TARGET not in gate._target_body(  # noqa: SLF001
            makefile,
            parent_target,
        )
    assert (
        sum(
            gate.PRODUCER_RUN_TARGET in line.split()
            for line in makefile.splitlines()
            if line.startswith(".PHONY:")
        )
        == 1
    )


@pytest.mark.parametrize(
    "parent_target",
    [
        "release-check",
        "local-v1-milestone-check",
        gate.PRODUCER_STATIC_TARGET,
        gate.AUTHORIZATION_TARGET,
    ],
)
def test_live_module_make_token_rejects_forbidden_prerequisite_headers(
    tmp_path: Path,
    parent_target: str,
) -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    drifted = makefile.replace(
        f"{parent_target}:",
        f"{parent_target}: {gate.PRODUCER_RUN_TARGET}",
        1,
    )
    failures = _wiring_failures(tmp_path, drifted)

    assert any("occurs outside its exact PHONY token" in value for value in failures)
    assert any("occurrence allowlist is not exact" in value for value in failures)


def test_live_module_make_token_rejects_recipe_reference(tmp_path: Path) -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    drifted = makefile.replace(
        "test-fast:\n",
        f"test-fast:\n\t$(MAKE) {gate.PRODUCER_RUN_TARGET}\n",
        1,
    )

    failures = _wiring_failures(tmp_path, drifted)

    assert any("occurs outside its exact PHONY token" in value for value in failures)


def test_live_module_make_token_rejects_intermediate_alias_dependency(
    tmp_path: Path,
) -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    drifted = makefile + f"\no4-producer-alias: {gate.PRODUCER_RUN_TARGET}\n"

    failures = _wiring_failures(tmp_path, drifted)

    assert any("occurs outside its exact PHONY token" in value for value in failures)


def _wiring_failures(tmp_path: Path, makefile: str) -> list[str]:
    (tmp_path / "Makefile").write_text(makefile, encoding="utf-8")
    (tmp_path / "README.md").write_text(
        Path("README.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    failures: list[str] = []
    gate._validate_wiring(tmp_path, failures)  # noqa: SLF001
    return failures


def test_wiring_rejects_stale_make_attempt_comment(tmp_path: Path) -> None:
    makefile = (
        Path("Makefile")
        .read_text(encoding="utf-8")
        .replace(
            gate.PRODUCER_RUN_COMMENT,
            "# LIVE, gate-protected operator entrypoint. Attempt 001 currently refuses.",
            1,
        )
    )

    failures = _wiring_failures(tmp_path, makefile)

    assert "O4 live producer Make target comment is not exact" in failures


def test_wiring_rejects_stale_readme_attempt_guidance(tmp_path: Path) -> None:
    (tmp_path / "Makefile").write_text(
        Path("Makefile").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    readme = (
            Path("README.md")
            .read_text(encoding="utf-8")
            .replace(
                "current closure always refuses execution",
                "currently refuses because Attempt 001 is consumed",
                1,
            )
    )
    (tmp_path / "README.md").write_text(readme, encoding="utf-8")
    failures: list[str] = []

    gate._validate_wiring(tmp_path, failures)  # noqa: SLF001

    assert any(
        "README is missing current O4 Attempt 009 guidance" in failure for failure in failures
    )


def test_wiring_rejects_direct_release_dependency(tmp_path: Path) -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    drifted = makefile.replace(
        "release-check:",
        f"release-check: {gate.AUTHORIZATION_TARGET} ",
        1,
    )
    (tmp_path / "Makefile").write_text(drifted, encoding="utf-8")
    (tmp_path / "README.md").write_text(
        Path("README.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    failures: list[str] = []

    gate._validate_wiring(tmp_path, failures)  # noqa: SLF001

    assert any("must not be wired into release-check" in failure for failure in failures)

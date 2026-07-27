from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from ithildin_node.client import StoredNodeConfiguration

from scripts import local_v1_failure_recovery_check as evidence_check
from scripts import local_v1_failure_recovery_journey as journey


def test_evidence_root_is_confined_to_one_run_child(tmp_path: Path) -> None:
    run_id = "20260727T120000Z-abcdef12"
    selected = journey.EVIDENCE_BASE / run_id

    assert journey.selected_evidence_root(selected, run_id=run_id) == selected.resolve()
    with pytest.raises(ValueError, match="outside the confined base"):
        journey.selected_evidence_root(tmp_path / run_id, run_id=run_id)
    with pytest.raises(ValueError, match="identity is invalid"):
        journey.selected_evidence_root(selected, run_id="../escape")


def test_evidence_root_rejects_symlinked_base(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    (repository / "var").mkdir(parents=True)
    external = tmp_path / "external"
    external.mkdir()
    base = repository / "var/local-v1-failure-recovery"
    base.symlink_to(external, target_is_directory=True)
    run_id = "20260727T120000Z-abcdef12"
    monkeypatch.setattr(journey, "ROOT", repository)
    monkeypatch.setattr(journey, "EVIDENCE_BASE", base)

    with pytest.raises(ValueError, match="contains a symlink"):
        journey.selected_evidence_root(base / run_id, run_id=run_id)


def test_evidence_root_rejects_symlinked_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    base = repository / "var/local-v1-failure-recovery"
    base.mkdir(parents=True)
    external = tmp_path / "external"
    external.mkdir()
    run_id = "20260727T120000Z-abcdef12"
    (base / run_id).symlink_to(external, target_is_directory=True)
    monkeypatch.setattr(journey, "ROOT", repository)
    monkeypatch.setattr(journey, "EVIDENCE_BASE", base)

    with pytest.raises(ValueError, match="contains a symlink"):
        journey.selected_evidence_root(base / run_id, run_id=run_id)


def test_evidence_tree_rejects_symlinked_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    base = repository / "var/local-v1-failure-recovery"
    run_id = "20260727T120000Z-abcdef12"
    evidence = base / run_id / "evidence"
    evidence.mkdir(parents=True)
    external = tmp_path / "external.json"
    external.write_text("{}\n", encoding="utf-8")
    (evidence / "report.json").symlink_to(external)
    monkeypatch.setattr(journey, "ROOT", repository)
    monkeypatch.setattr(journey, "EVIDENCE_BASE", base)

    with pytest.raises(ValueError, match="contains a symlink"):
        journey.validate_evidence_tree(base / run_id)


def test_checker_rejects_symlinked_file_before_base_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    base = repository / "var/local-v1-failure-recovery"
    run_id = "20260727T120000Z-abcdef12"
    evidence = base / run_id / "evidence"
    evidence.mkdir(parents=True)
    external = tmp_path / "external.json"
    external.write_text("{}\n", encoding="utf-8")
    (evidence / journey.REPORT_JSON).symlink_to(external)
    monkeypatch.setattr(journey, "ROOT", repository)
    monkeypatch.setattr(journey, "EVIDENCE_BASE", base)
    monkeypatch.setattr(
        evidence_check.mcc_check,
        "build_report",
        lambda *_: pytest.fail("base checker must not inspect a symlinked tree"),
    )

    report = evidence_check.build_report(
        repository,
        base / run_id,
        expected_candidate="a" * 40,
    )

    assert report["valid"] is False
    assert any("contains a symlink" in failure for failure in report["failures"])
    assert all(value is False for value in report["authority"].values())


def test_nofollow_regular_file_probe_accepts_regular_file(tmp_path: Path) -> None:
    root = tmp_path / "run"
    evidence = root / "evidence"
    evidence.mkdir(parents=True)
    (evidence / "report.json").write_text("{}\n", encoding="utf-8")

    assert evidence_check._is_regular_nofollow(  # noqa: SLF001
        root,
        Path("evidence/report.json"),
    )


def test_missing_evidence_fails_closed_with_all_authority_false(tmp_path: Path) -> None:
    report = evidence_check.build_report(
        Path("."),
        tmp_path,
        expected_candidate="a" * 40,
    )

    assert report["valid"] is False
    assert report["claim_level"] == "local_v1_failure_recovery_candidate_evidence"
    assert all(value is False for value in report["authority"].values())
    assert "No release, production, promotion" in report["nonclaims"][-1]


def test_closed_documents_validate_all_six_recovery_observations() -> None:
    now = datetime(2026, 7, 27, 12, 5, tzinfo=UTC)
    commit = "a" * 40
    tree = "b" * 40
    report = _report(commit, tree)
    documents = _documents()

    checks = evidence_check.validate_documents(
        report=report,
        **documents,
        expected_candidate=commit,
        current_commit=commit,
        current_tree=tree,
        current_clean=True,
        rollback_configuration_mode=0o600,
        now=now,
    )

    assert checks
    assert all(checks.values()), checks


@pytest.mark.parametrize(
    ("document_name", "field", "replacement", "failed_check"),
    [
        (
            "rollback",
            "automatic",
            True,
            "manual_rollback_is_fresh_signed_generation",
        ),
        (
            "stale_rollback",
            "status_code",
            200,
            "stale_rollback_conflict_rejected",
        ),
        (
            "stale_configuration",
            "status_code",
            200,
            "stale_configuration_acknowledgment_rejected",
        ),
        (
            "rollback_acknowledged",
            "enforcement_proven",
            True,
            "rollback_acknowledged_as_stored_not_enforced",
        ),
    ],
)
def test_recovery_document_drift_fails_closed(
    document_name: str,
    field: str,
    replacement: object,
    failed_check: str,
) -> None:
    commit = "a" * 40
    tree = "b" * 40
    documents = _documents()
    documents[document_name][field] = replacement

    checks = evidence_check.validate_documents(
        report=_report(commit, tree),
        **documents,
        expected_candidate=commit,
        current_commit=commit,
        current_tree=tree,
        current_clean=True,
        rollback_configuration_mode=0o600,
        now=datetime(2026, 7, 27, 12, 5, tzinfo=UTC),
    )

    assert checks[failed_check] is False


def test_authority_or_identity_overclaim_fails_closed() -> None:
    commit = "a" * 40
    tree = "b" * 40
    report = _report(commit, tree)
    report["authority"]["runner_launch_authorized"] = True
    report["identity_digests"]["node"] = "node_" + ("c" * 32)

    checks = evidence_check.validate_documents(
        report=report,
        **_documents(),
        expected_candidate=commit,
        current_commit=commit,
        current_tree=tree,
        current_clean=True,
        rollback_configuration_mode=0o600,
        now=datetime(2026, 7, 27, 12, 5, tzinfo=UTC),
    )

    assert checks["all_authority_remains_false"] is False
    assert checks["identity_evidence_is_digest_only"] is False


@pytest.mark.parametrize(
    "appended",
    [
        "\nOperator note: proceed.\n",
        "\nRelease and UAT are authorized by this evidence.\n",
        "\nObserved node_extra_private_identifier.\n",
    ],
)
def test_operator_markdown_rejects_appended_content(appended: str) -> None:
    commit = "a" * 40
    tree = "b" * 40
    documents = _documents()
    documents["markdown"] += appended

    checks = evidence_check.validate_documents(
        report=_report(commit, tree),
        **documents,
        expected_candidate=commit,
        current_commit=commit,
        current_tree=tree,
        current_clean=True,
        rollback_configuration_mode=0o600,
        now=datetime(2026, 7, 27, 12, 5, tzinfo=UTC),
    )

    assert checks["operator_markdown_matches_safe_report"] is False


def test_configuration_recovery_uses_fresh_rollback_and_rejects_stale_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "evidence").mkdir()
    (tmp_path / "client").mkdir()
    first = _configuration(generation=1, digest_character="1")
    recovered = _configuration(
        generation=3,
        digest_character="1",
        assignment_kind="manual_rollback",
        rollback_source_generation=1,
    )
    state = SimpleNamespace(
        node_id="node_" + ("a" * 32),
        gateway_configuration_key_id="key_current",
    )
    admin_calls: list[tuple[str, object]] = []

    def admin_request(path: str, payload: object = None) -> dict[str, Any]:
        admin_calls.append((path, payload))
        if path.endswith("/configurations/rollback"):
            return {
                "generation": 3,
                "configuration_digest": first.configuration_digest,
                "assignment_kind": "manual_rollback",
                "rollback_source_generation": 1,
            }
        if path.endswith("/configurations"):
            return {"generation": 2}
        return {"configuration_state": "configuration_drift"}

    def request_outcome(*_: object, **__: object) -> tuple[int, dict[str, str]]:
        return 409, {"detail": "desired configuration changed"}

    def signed_outcome(*_: object, **__: object) -> tuple[int, dict[str, str]]:
        return 409, {"detail": "configuration acknowledgment is not current"}

    class FakeClient:
        def pull_configuration(self, *_: object, **__: object) -> StoredNodeConfiguration:
            return recovered

        def acknowledge_configuration(self, *_: object, **__: object) -> dict[str, str]:
            return {
                "configuration_acknowledgment_status": "stored_not_enforced",
                "configuration_state": "stored_current_not_enforced",
            }

        def heartbeat(self, *_: object, **__: object) -> dict[str, str]:
            return {"observed_state": "observed_connected"}

    monkeypatch.setattr(journey.mcc_poc, "_admin_request", admin_request)
    monkeypatch.setattr(journey.mcc_poc, "_request_outcome", request_outcome)
    monkeypatch.setattr(journey.mcc_poc, "_signed_request_outcome", signed_outcome)
    monkeypatch.setattr(journey.mcc_poc, "_node_client", lambda: FakeClient())

    actual, rollback = journey.exercise_configuration_recovery(
        tmp_path,
        state,  # type: ignore[arg-type]
        first,
    )

    assert actual.generation == 3
    assert rollback["automatic"] is False
    assert (tmp_path / "client/rollback-configuration.json").stat().st_mode & 0o777 == 0o600
    stale = json.loads(
        (tmp_path / "evidence/stale-configuration-rejection.json").read_text(
            encoding="utf-8"
        )
    )
    assert stale["status_code"] == 409
    assert len(admin_calls) == 3


def _report(commit: str, tree: str) -> dict[str, Any]:
    return {
        "schema_version": journey.SCHEMA_VERSION,
        "run_id": "20260727T120000Z-abcdef12",
        "result": "passed",
        "candidate": {
            "commit": commit,
            "tree": tree,
            "clean_at_start": True,
            "commit_at_finish": commit,
            "tree_at_finish": tree,
            "clean_at_finish": True,
            "started_at_utc": "2026-07-27T12:00:00+00:00",
            "finished_at_utc": "2026-07-27T12:04:00+00:00",
        },
        "identity_digests": {
            "node": "sha256:" + ("1" * 64),
            "mission": "sha256:" + ("2" * 64),
        },
        "observations": {
            "restart_continuity": "passed",
            "replay_rejection": "passed",
            "partition_failure": "passed",
            "revocation": "passed",
            "stale_configuration_rejection": "passed",
            "manual_rollback": "passed",
            "rollback_generation": 3,
            "rollback_configuration_digest": "sha256:" + ("3" * 64),
            "configuration_enforcement": "stored_not_enforced",
            "gateway_truth_authoritative": True,
            "runner_state_authority": "runner_reported_only",
            "model_provider_state": "unknown",
        },
        "authority": dict(journey.AUTHORITY),
        "nonclaims": list(journey.NONCLAIMS),
    }


def _documents() -> dict[str, Any]:
    commit = "a" * 40
    tree = "b" * 40
    report = _report(commit, tree)
    return {
        "drift": {
            "acknowledged_generation": 1,
            "desired_generation": 2,
            "configuration_state": "configuration_drift",
            "enforcement_proven": False,
        },
        "rollback": {
            "generation": 3,
            "assignment_kind": "manual_rollback",
            "rollback_source_generation": 1,
            "replaced_desired_generation": 2,
            "configuration_digest_matches_source": True,
            "automatic": False,
            "enforcement_proven": False,
        },
        "stale_rollback": {
            "status_code": 409,
            "detail": "desired configuration changed",
            "automatic_retry_used": False,
        },
        "stale_configuration": {
            "status_code": 409,
            "detail": "configuration acknowledgment is not current",
            "stale_generation": 1,
            "desired_generation": 3,
            "automatic_retry_used": False,
        },
        "rollback_acknowledged": {
            "generation": 3,
            "assignment_kind": "manual_rollback",
            "rollback_source_generation": 1,
            "configuration_digest_matches_source": True,
            "configuration_acknowledgment_status": "stored_not_enforced",
            "configuration_state": "stored_current_not_enforced",
            "heartbeat_observed_state": "observed_connected",
            "enforcement_proven": False,
        },
        "markdown": journey.render_markdown(report),
    }


def _configuration(
    *,
    generation: int,
    digest_character: str,
    assignment_kind: str = "assignment",
    rollback_source_generation: int | None = None,
) -> StoredNodeConfiguration:
    return StoredNodeConfiguration(
        bundle={
            "configuration_id": f"ncfg_{generation}",
            "generation": generation,
            "configuration_digest": "sha256:" + (digest_character * 64),
            "expires_at": "2026-07-27T13:00:00+00:00",
            "signature": {"key_id": "key_current"},
            "assignment_kind": assignment_kind,
            "rollback_source_generation": rollback_source_generation,
        }
    )

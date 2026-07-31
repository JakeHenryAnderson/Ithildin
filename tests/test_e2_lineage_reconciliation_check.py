from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import e2_lineage_reconciliation_check as reconciliation

SCRIPT = reconciliation.ROOT / "scripts/e2_lineage_reconciliation_check.py"


def _record() -> dict[str, object]:
    return reconciliation.load_record(reconciliation.ROOT / reconciliation.RECORD_REL)


def _successful_summaries() -> dict[str, str]:
    return {label: f"{label} passed" for label in reconciliation.EXPECTED_FROZEN_GATE_LABELS}


def _mock_mandatory_boundaries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        reconciliation,
        "_protected_ref_verification",
        lambda _root: ([], copy.deepcopy(reconciliation.EXPECTED_LIVE_REF_EVIDENCE)),
    )
    monkeypatch.setattr(
        reconciliation,
        "run_frozen_gates",
        lambda _root: ([], _successful_summaries()),
    )


def _run_script(*arguments: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        cwd=cwd or reconciliation.ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=1_800,
    )


def _run_main_with_boundary_patch(patch: str) -> subprocess.CompletedProcess[str]:
    source = f"""
import copy
import sys
from scripts import e2_lineage_reconciliation_check as reconciliation
{patch}
sys.argv = [str(reconciliation.ROOT / 'scripts/e2_lineage_reconciliation_check.py'), '--json']
raise SystemExit(reconciliation.main())
"""
    return subprocess.run(
        [sys.executable, "-c", source],
        cwd=reconciliation.ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=1_800,
    )


def test_live_reconciliation_candidate_is_exact_and_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_mandatory_boundaries(monkeypatch)

    report = reconciliation.build_authoritative_report(reconciliation.ROOT)

    assert report["authoritative"] is True
    assert report["valid"] is True, report["failures"]
    assert report["record_status"] == "candidate_independent_review_pending"
    assert report["candidate_branch"] == reconciliation.BRANCH
    assert report["raw_parents"] == [reconciliation.REJECTED_COMMIT]
    assert report["governed_tool_count"] == 24
    assert report["runtime_authority"] == "Gateway"
    assert report["human_uat_complete"] is False
    assert report["release_allowed"] is False
    assert report["e2_id_005a_implementation_authorized"] is False
    assert report["live_ref_verification"] == reconciliation.EXPECTED_LIVE_REF_EVIDENCE
    assert set(report["frozen_gate_summaries"]) == set(
        reconciliation.EXPECTED_FROZEN_GATE_LABELS
    )


def test_record_is_closed_and_rejects_extra_keys() -> None:
    record = _record()
    assert record == reconciliation.EXPECTED_RECORD
    record["unexpected"] = True

    assert reconciliation.validate_record(record) == [
        "E2 lineage reconciliation record keys or values are not exact"
    ]


@pytest.mark.parametrize(
    "field",
    [
        "e2_id_005a_implementation_authorized",
        "pis_collection_action_authorized",
        "remote_transport_allowed",
        "production_identity_allowed",
        "runtime_postgres_allowed",
        "release_allowed",
        "production_allowed",
        "production_promotion_allowed",
        "human_uat_complete",
    ],
)
def test_record_rejects_any_true_authority_field(field: str) -> None:
    record = copy.deepcopy(_record())
    authority = record["authority"]
    assert isinstance(authority, dict)
    authority[field] = True

    assert reconciliation.validate_record(record) == [
        "E2 lineage reconciliation record keys or values are not exact"
    ]


def test_record_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"schema_version":"1","schema_version":"2"}\n')

    with pytest.raises(ValueError, match="duplicate JSON key: schema_version"):
        reconciliation.load_record(duplicate)


def test_frozen_artifact_validation_rejects_product_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = reconciliation._git_blob  # noqa: SLF001

    def drifted(root: Path, revision: str, relative: str) -> bytes:
        value = original(root, revision, relative)
        if relative == reconciliation.PRODUCT_ARTIFACTS[0]:
            return value + b"drift"
        return value

    monkeypatch.setattr(reconciliation, "_git_blob", drifted)

    assert any(
        failure.startswith("product checkpoint artifact drifted:")
        for failure in reconciliation.validate_frozen_artifacts(reconciliation.ROOT)
    )


def test_protected_ref_validation_rejects_local_tracking_and_live_movement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(reconciliation, "_git_or_none", lambda *_args: "0" * 40)

    failures, evidence = reconciliation._protected_ref_verification(  # noqa: SLF001
        reconciliation.ROOT
    )

    local_failures = [
        failure for failure in failures if "protected local or tracking ref moved" in failure
    ]
    assert len(local_failures) == len(reconciliation.PROTECTED_REFS)
    assert evidence["status"] == "failed"
    assert evidence["local_tracking_live_match"] is False


def test_git_validation_rejects_wrong_candidate_parent_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(reconciliation, "REJECTED_COMMIT", "0" * 40)
    monkeypatch.setattr(
        reconciliation,
        "_protected_ref_verification",
        lambda _root: ([], copy.deepcopy(reconciliation.EXPECTED_LIVE_REF_EVIDENCE)),
    )

    report = reconciliation.validate_git_bindings(reconciliation.ROOT)

    assert report["failures"]
    assert any(
        "reconciliation candidate branch, identity, or sole parent is invalid" in failure
        for failure in report["failures"]
    )


@pytest.mark.parametrize(
    "arguments",
    [
        ("--skip-frozen-gates",),
        ("--skip-live-refs",),
        ("--skip-frozen-gates", "--skip-live-refs"),
    ],
)
def test_production_cli_rejects_bypass_arguments(arguments: tuple[str, ...]) -> None:
    result = _run_script(*arguments, "--json")

    assert result.returncode != 0
    assert "unrecognized arguments" in result.stderr
    assert '"valid": true' not in result.stdout.lower()


@pytest.mark.parametrize(
    "argument",
    [
        "--skip-frozen",
        "--skip-live",
        "--no-frozen-gates",
        "--no-live-refs",
        "--quiet",
    ],
)
def test_production_cli_rejects_aliases_abbreviations_and_quiet_mode(argument: str) -> None:
    result = _run_script(argument, "--json")

    assert result.returncode != 0
    assert "unrecognized arguments" in result.stderr
    assert '"valid": true' not in result.stdout.lower()


def test_help_exposes_no_bypass_control() -> None:
    result = _run_script("--help")

    assert result.returncode == 0
    assert "--json" in result.stdout
    assert "skip" not in result.stdout.lower()
    assert "bypass" not in result.stdout.lower()


def test_direct_script_execution_resolves_repo_from_an_external_cwd(tmp_path: Path) -> None:
    result = _run_script("--help", cwd=tmp_path)

    assert result.returncode == 0
    assert "e2_lineage_reconciliation_check.py" in result.stdout


def test_production_entry_rejects_missing_frozen_gate_evidence_in_subprocess() -> None:
    result = _run_main_with_boundary_patch(
        "reconciliation._protected_ref_verification = "
        "lambda _root: ([], copy.deepcopy(reconciliation.EXPECTED_LIVE_REF_EVIDENCE))\n"
        "reconciliation.run_frozen_gates = lambda _root: ([], {})"
    )

    assert result.returncode != 0
    report = json.loads(result.stdout)
    assert report["authoritative"] is True
    assert report["valid"] is False
    assert report["frozen_gate_summaries"] == {}
    assert "frozen gate summary inventory" in "\n".join(report["failures"])


def test_production_entry_rejects_missing_live_ref_evidence_in_subprocess() -> None:
    summaries = repr(_successful_summaries())
    result = _run_main_with_boundary_patch(
        "reconciliation._protected_ref_verification = lambda _root: ([], {})\n"
        f"reconciliation.run_frozen_gates = lambda _root: ([], {summaries})"
    )

    assert result.returncode != 0
    report = json.loads(result.stdout)
    assert report["authoritative"] is True
    assert report["valid"] is False
    assert report["live_ref_verification"] == {}
    assert "live protected-ref verification evidence" in "\n".join(report["failures"])


@pytest.mark.parametrize(
    "summaries",
    [
        {},
        {"exact_product_checkpoint": "passed"},
        {label: "" for label in reconciliation.EXPECTED_FROZEN_GATE_LABELS},
        {
            **_successful_summaries(),
            "unexpected_gate": "passed",
        },
    ],
)
def test_frozen_summary_inventory_fails_closed(summaries: dict[str, str]) -> None:
    assert reconciliation._frozen_evidence_failures(summaries)  # noqa: SLF001


@pytest.mark.parametrize(
    "evidence",
    [
        {},
        {"status": "verified"},
        {**reconciliation.EXPECTED_LIVE_REF_EVIDENCE, "status": "failed"},
        {**reconciliation.EXPECTED_LIVE_REF_EVIDENCE, "unexpected": True},
    ],
)
def test_live_ref_evidence_inventory_fails_closed(evidence: dict[str, object]) -> None:
    assert reconciliation._live_ref_evidence_failures(evidence)  # noqa: SLF001


def test_checker_source_has_no_alternate_cli_or_environment_bypass() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "parse_known_args" not in source
    assert "argparse.SUPPRESS" not in source
    assert "--skip-" not in source
    assert "run_external_gates" not in source
    assert "verify_live_refs" not in source
    assert "os.getenv" not in source
    assert "os.environ.get" not in source
    assert "build_report" not in source


def test_normal_json_subprocess_contains_all_mandatory_evidence() -> None:
    result = _run_script("--json")

    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["authoritative"] is True
    assert report["valid"] is True
    assert set(report["frozen_gate_summaries"]) == set(
        reconciliation.EXPECTED_FROZEN_GATE_LABELS
    )
    assert all(report["frozen_gate_summaries"].values())
    assert report["live_ref_verification"] == reconciliation.EXPECTED_LIVE_REF_EVIDENCE

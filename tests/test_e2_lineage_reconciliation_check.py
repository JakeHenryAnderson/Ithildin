from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import e2_lineage_reconciliation_check as reconciliation

SCRIPT = reconciliation.ROOT / "scripts/e2_lineage_reconciliation_check.py"


def _record() -> dict[str, object]:
    return reconciliation.load_record(reconciliation.ROOT / reconciliation.RECORD_REL)


def _successful_summaries() -> dict[str, dict[str, object]]:
    summaries: dict[str, dict[str, object]] = {
        label: {
            "status": "passed",
            "exit_code": 0,
            "summary": f"{label} passed",
        }
        for label in reconciliation.EXPECTED_FROZEN_GATE_LABELS
    }
    summaries["complete_repaired_pis_fixture_matrix"] = {
        "status": "passed",
        "exit_code": 0,
        "summary": "93 passed in 1.00s",
        "passed_test_count": 93,
    }
    return summaries


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


def _run_script(
    *arguments: str,
    cwd: Path | None = None,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        cwd=cwd or reconciliation.ROOT,
        env=environment,
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
    assert report["raw_parents"] == [reconciliation.REPAIR_1_COMMIT]
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
    monkeypatch.setattr(reconciliation, "REPAIR_1_COMMIT", "0" * 40)
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
    "arguments",
    [
        ("--json", "--skip-frozen-gates"),
        ("--json", "--skip-live-refs"),
        ("--json", "--skip-frozen-gates", "--skip-live-refs"),
    ],
)
def test_production_cli_rejects_bypass_arguments_after_json(
    arguments: tuple[str, ...],
) -> None:
    result = _run_script(*arguments)

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
        {
            "exact_product_checkpoint": {
                "status": "passed",
                "exit_code": 0,
                "summary": "passed",
            }
        },
        {
            label: {"status": "passed", "exit_code": 0, "summary": ""}
            for label in reconciliation.EXPECTED_FROZEN_GATE_LABELS
        },
        {
            **_successful_summaries(),
            "unexpected_gate": {
                "status": "passed",
                "exit_code": 0,
                "summary": "passed",
            },
        },
        dict(reversed(tuple(_successful_summaries().items()))),
    ],
)
def test_frozen_summary_inventory_fails_closed(
    summaries: dict[str, dict[str, object]],
) -> None:
    assert reconciliation._frozen_evidence_failures(summaries)  # noqa: SLF001


@pytest.mark.parametrize(
    ("summary", "output"),
    [
        ("93 tests collected in 0.40s", "93 tests collected in 0.40s"),
        ("93 deselected in 0.40s", "93 deselected in 0.40s"),
        ("93 skipped in 0.40s", "93 skipped in 0.40s"),
        ("no tests ran in 0.40s", "no tests ran in 0.40s"),
        ("92 passed in 0.40s", "92 passed in 0.40s"),
        ("1 passed in 0.40s", "1 passed in 0.40s"),
        ("93 xpassed in 0.40s", "93 xpassed in 0.40s"),
        ("arbitrary nonempty success", "arbitrary nonempty success"),
        ("93 passed in 0.40s", "forged plugin: 93 tests collected\n93 passed in 0.40s"),
        ("93 passed, 1 warning in 0.40s", "93 passed, 1 warning in 0.40s"),
    ],
)
def test_zero_exit_forged_matrix_output_is_rejected(summary: str, output: str) -> None:
    result = {"status": "passed", "exit_code": 0, "summary": summary}

    assert reconciliation._matrix_pass_count(result, output) is None  # noqa: SLF001


def test_exact_matrix_pass_output_is_accepted() -> None:
    result = {"status": "passed", "exit_code": 0, "summary": "93 passed in 1.25s"}

    assert reconciliation._matrix_pass_count(result, ".\n93 passed in 1.25s") == 93  # noqa: SLF001


@pytest.mark.parametrize(
    "matrix",
    [
        {
            "status": "passed",
            "exit_code": 0,
            "summary": "93 tests collected in 0.40s",
            "passed_test_count": 93,
        },
        {
            "status": "passed",
            "exit_code": 0,
            "summary": "93 passed in 0.40s",
            "passed_test_count": 92,
        },
        {
            "status": "passed",
            "exit_code": 0,
            "summary": "no tests ran in 0.40s",
            "passed_test_count": None,
        },
        {
            "status": "passed",
            "exit_code": 0,
            "summary": "93 passed in 0.40s",
            "passed_test_count": 93,
            "unexpected": True,
        },
    ],
)
def test_forged_matrix_result_cannot_close_authoritative_evidence(
    matrix: dict[str, object],
) -> None:
    summaries = _successful_summaries()
    summaries["complete_repaired_pis_fixture_matrix"] = matrix

    assert reconciliation._frozen_evidence_failures(summaries)  # noqa: SLF001


def test_matrix_command_neutralizes_config_addopts_plugins_and_color(tmp_path: Path) -> None:
    test_path = tmp_path / "test_contract.py"
    command = reconciliation._matrix_command(  # noqa: SLF001
        test_path, reconciliation.ROOT
    )

    assert command[:3] == [sys.executable, "-m", "pytest"]
    assert command[3] == str(test_path)
    assert command[command.index("--rootdir") + 1] == str(reconciliation.ROOT)
    assert command[command.index("-c") + 1] == os.devnull
    assert command[command.index("-o") + 1] == "addopts="
    assert command[command.index("-p") + 1] == "no:cacheprovider"
    assert "--color=no" in command
    assert "--collect-only" not in command


def test_authoritative_command_timeout_is_structured_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def timeout(*_args: object, **_kwargs: object) -> None:
        raise subprocess.TimeoutExpired(["python"], 1_800)

    monkeypatch.setattr(reconciliation.subprocess, "run", timeout)

    result, _output = reconciliation._run_command(  # noqa: SLF001
        [sys.executable, "-c", "pass"], reconciliation.ROOT
    )

    assert result["status"] == "failed"
    assert result["exit_code"] is None
    assert "timed out" in str(result["summary"])


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


def test_authoritative_child_environment_is_closed_and_hostile_inputs_are_removed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hostile = {
        "PYTEST_ADDOPTS": "--collect-only",
        "PYTEST_PLUGINS": "forged_plugin",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "0",
        "PYTEST_DEBUG": "1",
        "PYTEST_THEME": "hostile",
        "PYTHONHOME": "/tmp/hostile-python-home",
        "PYTHONPATH": "/tmp/hostile-python-path",
        "PYTHONSTARTUP": "/tmp/hostile-python-startup",
        "PYTHONUSERBASE": "/tmp/hostile-python-userbase",
        "PYTHONWARNINGS": "ignore",
        "COVERAGE_PROCESS_START": "/tmp/hostile-coveragerc",
        "GIT_CONFIG_GLOBAL": "/tmp/hostile-gitconfig",
        "GIT_CONFIG_SYSTEM": "/tmp/hostile-system-gitconfig",
    }
    for key, value in hostile.items():
        monkeypatch.setenv(key, value)
    command = [
        sys.executable,
        "-c",
        "import json, os; print(json.dumps(dict(os.environ), sort_keys=True))",
    ]

    result, output = reconciliation._run_command(  # noqa: SLF001
        command,
        reconciliation.ROOT,
        pythonpath=reconciliation.ROOT,
    )

    assert result["status"] == "passed"
    child = json.loads(output)
    assert child["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
    assert child["PYTHONPATH"] == str(reconciliation.ROOT.resolve())
    assert child["PYTHONNOUSERSITE"] == "1"
    assert child["HOME"] != os.environ.get("HOME")
    assert set(child) <= {
        "HOME",
        "LANG",
        "LC_ALL",
        "PATH",
        "PYTHONDONTWRITEBYTECODE",
        "PYTHONHASHSEED",
        "PYTHONNOUSERSITE",
        "PYTHONPATH",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
        "TMPDIR",
        "__CF_USER_TEXT_ENCODING",
    }
    for key in hostile:
        if key not in {"PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTHONPATH"}:
            assert key not in child


def test_checker_source_has_no_alternate_cli_or_environment_bypass() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "parse_known_args" not in source
    assert "argparse.SUPPRESS" not in source
    assert "--skip-" not in source
    assert "run_external_gates" not in source
    assert "verify_live_refs" not in source
    assert "os.getenv" not in source
    assert "os.environ.get" not in source
    assert "os.environ.copy" not in source
    assert "build_report" not in source


def test_module_entry_rejects_bypass_arguments() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.e2_lineage_reconciliation_check",
            "--skip-frozen-gates",
            "--json",
        ],
        cwd=reconciliation.ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=1_800,
    )

    assert result.returncode != 0
    assert "unrecognized arguments" in result.stderr
    assert '"valid": true' not in result.stdout.lower()


def test_normal_json_subprocess_contains_all_mandatory_evidence_under_hostile_parent(
    tmp_path: Path,
) -> None:
    hostile_environment = os.environ.copy()
    hostile_environment.update(
        {
            "PYTEST_ADDOPTS": "--collect-only",
            "PYTEST_PLUGINS": "forged_plugin",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "0",
            "PYTEST_DEBUG": "1",
            "PYTEST_THEME": "hostile",
            "PYTHONPATH": str(tmp_path),
            "PYTHONSTARTUP": str(tmp_path / "startup.py"),
            "PYTHONUSERBASE": str(tmp_path / "userbase"),
            "PYTHONWARNINGS": "error",
            "COVERAGE_PROCESS_START": str(tmp_path / "coveragerc"),
        }
    )

    result = _run_script("--json", environment=hostile_environment)

    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["authoritative"] is True
    assert report["valid"] is True
    assert set(report["frozen_gate_summaries"]) == set(
        reconciliation.EXPECTED_FROZEN_GATE_LABELS
    )
    matrix = report["frozen_gate_summaries"]["complete_repaired_pis_fixture_matrix"]
    assert matrix == {
        "exit_code": 0,
        "passed_test_count": 93,
        "status": "passed",
        "summary": matrix["summary"],
    }
    assert matrix["summary"].startswith("93 passed in ")
    assert "collected" not in matrix["summary"]
    assert report["live_ref_verification"] == reconciliation.EXPECTED_LIVE_REF_EVIDENCE

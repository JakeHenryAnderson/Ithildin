from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path

from pytest import MonkeyPatch

from scripts import local_v1_o2_disposition_check as o2_check

ROOT = Path(__file__).resolve().parents[1]


def _disposition() -> dict[str, object]:
    value: dict[str, object] = json.loads(
        (ROOT / o2_check.DISPOSITION_REL).read_text(encoding="utf-8")
    )
    return value


def test_o2_disposition_contract_is_exact_and_authority_false() -> None:
    failures: list[str] = []

    candidate, binding = o2_check.validate_disposition_contract(
        _disposition(),
        failures,
    )

    assert failures == []
    assert tuple(candidate["paths"]) == o2_check.EXPECTED_EVIDENCE_PATHS
    assert binding["checker_result"] == "valid"


def test_o2_disposition_contract_rejects_observation_and_authority_drift() -> None:
    disposition = copy.deepcopy(_disposition())
    observations = disposition["observations"]
    authority = disposition["authority"]
    assert isinstance(observations, dict)
    assert isinstance(authority, dict)
    observations["approval_request_not_executed"] = False
    authority["release_allowed"] = True
    failures: list[str] = []

    o2_check.validate_disposition_contract(disposition, failures)

    assert "O2 required observation is missing" in failures
    assert "O2 authority is not entirely false" in failures


def test_o2_disposition_contract_rejects_extra_or_unbound_approval_evidence() -> None:
    disposition = copy.deepcopy(_disposition())
    observations = disposition["observations"]
    binding = disposition["private_evidence_binding"]
    assert isinstance(observations, dict)
    assert isinstance(binding, dict)
    observations["approval_count"] = 2
    binding["report_sha256"] = "sha256:invalid"
    failures: list[str] = []

    o2_check.validate_disposition_contract(disposition, failures)

    assert "O2 approval count is not exactly one" in failures
    assert "O2 private report digest is invalid" in failures


def test_private_report_binding_requires_exact_mode_size_and_digest(
    tmp_path: Path,
) -> None:
    report = tmp_path / "local-v1-real-agent.json"
    payload = b'{"result":"synthetic"}\n'
    report.write_bytes(payload)
    os.chmod(report, 0o600)
    binding = {
        "report_size_bytes": len(payload),
        "report_sha256": f"sha256:{hashlib.sha256(payload).hexdigest()}",
    }
    failures: list[str] = []

    assert o2_check.validate_private_report_binding(report, binding, failures) is True
    assert failures == []

    os.chmod(report, 0o644)
    failures = []
    assert o2_check.validate_private_report_binding(report, binding, failures) is False
    assert failures == ["O2 private report does not match its digest-safe binding"]


def test_private_report_selection_is_digest_bound_not_latest(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    repo_root = tmp_path.resolve()
    base = repo_root / "var/local-v1-real-agent"
    base.mkdir(parents=True)
    os.chmod(base, 0o755)
    older = base / ("20260727T120000Z-" + "1" * 32)
    selected = base / ("20260727T130000Z-" + "2" * 32)
    newer = base / ("20260727T140000Z-" + "3" * 32)
    for run_root in (older, selected, newer):
        run_root.mkdir()
        os.chmod(run_root, 0o700)
    payload = b'{"result":"synthetic"}\n'
    report = selected / o2_check.real_agent.REPORT_NAME
    report.write_bytes(payload)
    os.chmod(report, 0o600)
    binding = {
        "report_size_bytes": len(payload),
        "report_sha256": f"sha256:{hashlib.sha256(payload).hexdigest()}",
    }
    monkeypatch.setattr(o2_check.real_agent, "ROOT", repo_root)
    monkeypatch.setattr(o2_check.real_agent, "EVIDENCE_BASE", base)
    failures: list[str] = []

    assert (
        o2_check.select_bound_private_report(repo_root, binding, failures) == report
    )
    assert failures == []


def test_duplicate_disposition_keys_are_rejected() -> None:
    try:
        o2_check._reject_duplicate_keys(  # noqa: SLF001
            [("record_status", "first"), ("record_status", "second")]
        )
    except ValueError as exc:
        assert str(exc) == "duplicate JSON key: record_status"
    else:
        raise AssertionError("duplicate disposition key was accepted")


def test_candidate_inventory_uses_current_o2_evidence_not_ambient_hermes_runtime() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    inventory = makefile.split("local-v1-candidate-inventory:", 1)[1].split(
        "\nlocal-v1-candidate-check:",
        1,
    )[0]

    assert "$(MAKE) local-v1-o2-evidence-check" in inventory
    assert "$(MAKE) local-v1-hermes-evidence-check" not in inventory
    assert "$(MAKE) local-v1-test-fast" in inventory
    assert "$(MAKE) test-fast" not in inventory
    assert "$(MAKE) local-v1-typecheck" in inventory
    assert "$(MAKE) typecheck" not in inventory
    typecheck = makefile.split("local-v1-typecheck:", 1)[1].split(
        "\nlocal-v1-hermes-evidence-check:",
        1,
    )[0]
    assert typecheck.count("uv run mypy --strict") == 3
    assert "tests/" not in typecheck
    assert "--exclude" not in typecheck
    for legacy_evidence_target in (
        "track-b-node-evidence-check",
        "track-b-node-configuration-evidence-check",
        "track-b-node-governed-access-evidence-check",
        "track-b-node-configuration-trust-rotation-evidence-check",
        "track-b-node-version-posture-evidence-check",
        "track-b-node-identity-key-rotation-evidence-check",
        "track-b-node-service-lifecycle-evidence-check",
        "track-b-node-release-artifact-evidence-check",
        "mission-command-control-plane-poc-check",
    ):
        assert f"$(MAKE) {legacy_evidence_target}" not in inventory
    assert "$(MAKE) mission-command-control-plane-plan-check" in inventory
    assert "$(MAKE) mission-command-control-plane-focused-gates" in inventory
    assert o2_check.EXPECTED_QUALIFICATION_PATHS == (
        "Makefile",
        "docs/codex/local-v1-completion-contract.md",
        "docs/codex/local-v1-lv1-007-o2-disposition.json",
        "docs/codex/local-v1-lv1-007-o2-disposition.md",
        "scripts/local_v1_contract_check.py",
        "scripts/local_v1_o2_disposition_check.py",
        "tests/test_local_v1_contract.py",
        "tests/test_local_v1_golden_path.py",
        "tests/test_local_v1_o2_disposition_check.py",
        "tests/test_release_readiness.py",
    )

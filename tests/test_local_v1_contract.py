from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from scripts import local_v1_contract_check

ROOT = Path(__file__).resolve().parents[1]
RELEASE_FIXTURE_PATHS = (
    Path("Makefile"),
    Path("README.md"),
    Path("tool-manifests.lock.json"),
    Path("scripts/build_docs_site.py"),
    Path("scripts/local_v1_contract_check.py"),
    Path("scripts/review_docs.py"),
    Path("tests/test_local_v1_contract.py"),
    Path("docs/codex/review-docs-index.md"),
    Path("docs/codex/enterprise-progress-model.md"),
    Path("docs/codex/enterprise-north-star-roadmap.md"),
    Path("docs/codex/enterprise-current-checkpoint.md"),
    Path("docs/codex/v1.0-rc-status.md"),
    Path("docs/codex/v1.0-progress-assessment.md"),
    Path("docs/codex/technical-mvp-execution-board.md"),
    local_v1_contract_check.CONTRACT_REL,
    local_v1_contract_check.DISPOSITION_REL,
)


def test_live_local_v1_contract_is_internally_consistent_at_any_lifecycle_stage() -> None:
    report = local_v1_contract_check.build_report(ROOT)

    assert report["valid"] is True, report["failures"]
    assert report["active_delivery_target"] == "Ithildin Local v1.0"
    assert report["tool_count"] == 24
    assert report["outcomes_total"] == 8
    assert report["milestones_total"] == 8
    assert report["disposition_valid"] is True
    assert report["runtime_authority_granted"] is False
    assert report["new_governed_powers_authorized"] is False
    assert report["pis_wait_blocks_local_v1"] is False
    assert set(report["outcome_statuses"]) == set(local_v1_contract_check.OUTCOME_IDS)
    assert set(report["milestone_statuses"]) == set(
        local_v1_contract_check.MILESTONE_IDS
    )
    assert set(report["outcome_statuses"].values()).issubset(
        local_v1_contract_check.ALLOWED_OUTCOME_STATUSES
    )
    assert set(report["milestone_statuses"].values()).issubset(
        local_v1_contract_check.ALLOWED_OUTCOME_STATUSES
    )
    assert report["outcomes_complete"] == sum(
        status == "complete" for status in report["outcome_statuses"].values()
    )
    assert report["milestones_complete"] == sum(
        status == "complete" for status in report["milestone_statuses"].values()
    )
    expected_next = next(
        (
            milestone
            for milestone in local_v1_contract_check.MILESTONE_IDS
            if report["milestone_statuses"][milestone] != "complete"
        ),
        "release_decision",
    )
    assert report["active_next_action"] == expected_next
    expected_candidate_ready = all(
        report["outcome_statuses"][outcome] == "complete"
        for outcome in local_v1_contract_check.OUTCOME_IDS[:-1]
    ) and report["outcome_statuses"]["O8"] in {
        "in_progress",
        "candidate_ready",
        "complete",
    }
    assert report["candidate_ready"] == expected_candidate_ready
    if report["release_ready"]:
        assert report["outcomes_complete"] == report["outcomes_total"]
        assert report["release_disposition_complete"] is True
        assert report["human_uat_complete"] is True
        assert report["release_accepted"] is True


def test_uninitialized_local_v1_release_check_fails_closed() -> None:
    report = local_v1_contract_check.build_report(
        ROOT,
        require_release=True,
        contract_override=_contract_for_stage("uninitialized"),
        disposition_override=_disposition_for_stage(
            _read_disposition(), "uninitialized"
        ),
    )

    assert report["valid"] is False
    assert report["release_ready"] is False
    assert any(
        "all eight outcomes, genuine human UAT" in failure
        for failure in report["failures"]
    )


def test_uninitialized_local_v1_candidate_check_fails_closed() -> None:
    report = local_v1_contract_check.build_report(
        ROOT,
        require_candidate=True,
        contract_override=_contract_for_stage("uninitialized"),
        disposition_override=_disposition_for_stage(
            _read_disposition(), "uninitialized"
        ),
    )

    assert report["valid"] is False
    assert report["candidate_ready"] is False
    assert any("outcomes O1-O7 must be complete" in failure for failure in report["failures"])


def test_local_v1_contract_rejects_percentage_forecasts() -> None:
    contract = (ROOT / local_v1_contract_check.CONTRACT_REL).read_text(
        encoding="utf-8"
    )

    failures, _, _ = local_v1_contract_check.validate_contract_text(
        contract + "\nActive forecast: 35-50%\n"
    )

    assert "Local-v1 contract contains a percentage-band delivery estimate" in failures


def test_local_v1_contract_rejects_authority_and_outcome_drift() -> None:
    contract = (ROOT / local_v1_contract_check.CONTRACT_REL).read_text(
        encoding="utf-8"
    )
    drifted = re.sub(
        r"`MCC-007` remains a later, separate bounded capability\s+decision",
        "`MCC-007` is authorized for implementation",
        contract,
    ).replace("| `O8` |", "| `O7` |", 1)

    failures, _, _ = local_v1_contract_check.validate_contract_text(drifted)

    assert any("MCC-007" in failure for failure in failures)
    assert "Local-v1 contract must contain exactly outcome rows O1 through O8" in failures


def test_local_v1_release_topology_does_not_modify_full_release_dependency() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    full_release_header = next(
        line for line in makefile.splitlines() if line.startswith("release-check:")
    )

    assert "local-v1-" not in full_release_header
    assert "local-v1-release-check:" in makefile
    assert "local-v1-candidate-check:" in makefile
    assert "local-v1-candidate-inventory:" in makefile
    assert "local-v1-release-slices:" not in makefile


def test_local_v1_candidate_inventory_is_exact_and_excludes_live_reproduction() -> None:
    report = local_v1_contract_check.build_report(ROOT)
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    body = local_v1_contract_check._target_body(  # noqa: SLF001
        makefile, "local-v1-candidate-inventory"
    )
    actual = tuple(
        re.findall(r"^\t\$\(MAKE\) ([a-z0-9][a-z0-9-]*)$", body, re.MULTILINE)
    )

    assert report["valid"] is True, report["failures"]
    assert actual == local_v1_contract_check.LOCAL_V1_CANDIDATE_TARGETS
    assert "mission-command-control-plane-poc" not in actual
    assert "hermes-poc-run" not in actual
    assert not any(target.startswith("enterprise-") for target in actual)
    assert not any("production-identity-storage" in target for target in actual)
    assert not any("sandbox-vm" in target for target in actual)
    assert not any("trusted-host" in target for target in actual)


def test_local_v1_candidate_inventory_rejects_added_enterprise_target() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    drifted = makefile.replace(
        "\t$(MAKE) agent-workflow-check\n\nlocal-v1-candidate-check:",
        "\t$(MAKE) agent-workflow-check\n"
        "\t$(MAKE) enterprise-current-checkpoint\n\n"
        "local-v1-candidate-check:",
    )

    failures = local_v1_contract_check.validate_candidate_inventory(drifted)

    assert any("candidate inventory drifted" in failure for failure in failures)
    assert any("forbidden target: enterprise-" in failure for failure in failures)


def test_release_status_prose_cannot_false_green_without_bound_evidence() -> None:
    contract = _contract_for_stage("uninitialized")
    green_prose = (
        contract.replace("Release outcomes complete: `0/8`", "Release outcomes complete: `8/8`")
        .replace(
            "Critical-path milestones complete: `0/8`",
            "Critical-path milestones complete: `8/8`",
        )
        .replace("Latest completed milestone: `none`", "Latest completed milestone: `LV1-007`")
        .replace("Active next action: `LV1-000`", "Active next action: `release_decision`")
        .replace("Local-v1 release gate: `blocked`", "Local-v1 release gate: `complete`")
        .replace("Human UAT: `not_started`", "Human UAT: `complete`")
        .replace("Release acceptance: `false`", "Release acceptance: `true`")
    )
    green_prose = re.sub(
        r"^(\| `O[1-8]` \| [^|]+ \|) `(?:not_started|in_progress)` (\|)",
        r"\1 `complete` \2",
        green_prose,
        flags=re.MULTILINE,
    )
    green_prose = re.sub(
        r"^(\| `LV1-\d{3}` \| [^|]+ \|) `(?:not_started|in_progress)` (\|)",
        r"\1 `complete` \2",
        green_prose,
        flags=re.MULTILINE,
    )
    disposition = _disposition_for_stage(
        _read_disposition(),
        "uninitialized",
    )

    report = local_v1_contract_check.build_report(
        ROOT,
        require_release=True,
        contract_override=green_prose,
        disposition_override=disposition,
    )

    assert report["valid"] is False
    assert report["release_ready"] is False
    assert report["release_disposition_complete"] is False
    assert any("O8 cannot be complete" in failure for failure in report["failures"])
    assert any("human UAT without bound" in failure for failure in report["failures"])
    assert any("release acceptance without bound" in failure for failure in report["failures"])
    assert any("complete release gate without bound" in failure for failure in report["failures"])


def test_release_authority_cannot_be_set_without_bound_evidence() -> None:
    disposition = _disposition_for_stage(
        _read_disposition(),
        "uninitialized",
    )
    drifted = copy.deepcopy(disposition)
    drifted["authority"]["candidate_qualified"] = True
    drifted["authority"]["release_allowed"] = True

    failures, state = local_v1_contract_check.validate_disposition(ROOT, drifted)

    assert state["release_evidence_complete"] is False
    assert any("candidate authority is true" in failure for failure in failures)
    assert any("release authority is true" in failure for failure in failures)


def test_release_lineage_purposes_are_closed_and_exact() -> None:
    disposition = _disposition_for_stage(
        _read_disposition(),
        "uninitialized",
    )
    drifted = copy.deepcopy(disposition)
    drifted["disposition_lineage"]["allowed_descendant_purposes"].append(
        "unbounded_docs_or_code_change"
    )

    failures, state = local_v1_contract_check.validate_disposition(ROOT, drifted)

    assert state["release_evidence_complete"] is False
    assert "Local-v1 disposition allowed descendant purposes drifted" in failures


@pytest.mark.parametrize(
    "stage",
    ("uninitialized", "candidate_recorded", "reviewed", "uat_complete", "accepted"),
)
def test_disposition_accepts_each_exact_lifecycle_stage(
    accepted_release_repo: tuple[Path, dict[str, Any]],
    stage: str,
) -> None:
    repo, accepted = accepted_release_repo
    payload = _disposition_for_stage(accepted, stage)

    failures, state = local_v1_contract_check.validate_disposition(repo, payload)

    assert failures == []
    stage_index = (
        "uninitialized",
        "candidate_recorded",
        "reviewed",
        "uat_complete",
        "accepted",
    ).index(stage)
    assert state["candidate_evidence_complete"] == (stage_index >= 1)
    assert state["independent_review_evidence_complete"] == (stage_index >= 2)
    assert state["human_uat_evidence_complete"] == (stage_index >= 3)
    assert state["human_acceptance_evidence_complete"] == (stage_index >= 4)
    assert state["release_evidence_complete"] == (stage_index == 4)


@pytest.mark.parametrize(
    ("evidence_stage", "declared_status"),
    (
        ("uninitialized", "candidate_recorded"),
        ("candidate_recorded", "uninitialized"),
        ("reviewed", "candidate_recorded"),
        ("uat_complete", "reviewed"),
        ("accepted", "uat_complete"),
    ),
)
def test_disposition_rejects_premature_or_stale_status_at_every_stage(
    accepted_release_repo: tuple[Path, dict[str, Any]],
    evidence_stage: str,
    declared_status: str,
) -> None:
    repo, accepted = accepted_release_repo
    payload = _disposition_for_stage(accepted, evidence_stage)
    payload["record_status"] = declared_status

    failures, state = local_v1_contract_check.validate_disposition(repo, payload)

    assert state["valid"] is False
    assert any("record_status mismatch" in failure for failure in failures)


def test_disposition_rejects_out_of_order_evidence_and_authority(
    accepted_release_repo: tuple[Path, dict[str, Any]],
) -> None:
    repo, accepted = accepted_release_repo
    payload = _disposition_for_stage(accepted, "reviewed")
    payload["authority"]["candidate_qualified"] = False

    failures, state = local_v1_contract_check.validate_disposition(repo, payload)

    assert state["valid"] is False
    assert any("do not match any valid" in failure for failure in failures)


def test_future_accepted_candidate_passes_release_gate_without_code_changes(
    accepted_release_repo: tuple[Path, dict[str, Any]],
) -> None:
    repo, disposition = accepted_release_repo

    report = local_v1_contract_check.build_report(repo, require_release=True)
    frozen_candidate = disposition["candidate"]["frozen_commit"]
    candidate_descendant_paths = _git(
        repo, "diff", "--name-only", frozen_candidate, "HEAD"
    ).splitlines()

    assert report["valid"] is True, report["failures"]
    assert report["outcomes_complete"] == 8
    assert report["milestones_complete"] == 8
    assert report["active_next_action"] == "release_decision"
    assert report["release_disposition_complete"] is True
    assert report["release_ready"] is True
    assert candidate_descendant_paths
    assert all(
        path.startswith("docs/codex/local-v1-")
        for path in candidate_descendant_paths
    )


@pytest.fixture
def accepted_release_repo(tmp_path: Path) -> tuple[Path, dict[str, Any]]:
    repo = tmp_path / "local-v1-release-repo"
    for relative_path in RELEASE_FIXTURE_PATHS:
        target = repo / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative_path, target)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Local v1 Test")
    _git(repo, "config", "user.email", "local-v1-test@example.invalid")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "freeze candidate")
    candidate = _git(repo, "rev-parse", "HEAD")

    identity_path = Path("docs/codex/local-v1-candidate-identity.txt")
    gate_path = Path("docs/codex/local-v1-candidate-gate.txt")
    _write(
        repo,
        identity_path,
        f"frozen Local v1 candidate identity: {candidate}\n",
    )
    _write(
        repo,
        gate_path,
        "\n".join(
            (
                f"candidate_commit={candidate}",
                "candidate_tree_clean=true",
                "local_v1_candidate_gate_returncode=0",
                "",
            )
        ),
    )
    candidate_record_commit = _commit_docs(repo, "record candidate gate")

    review_path = Path("docs/codex/local-v1-independent-review.txt")
    _write(repo, review_path, f"GO independent review for {candidate}\n")
    review_record_commit = _commit_docs(repo, "record independent review")

    uat_path = Path("docs/codex/local-v1-human-uat.txt")
    _write(repo, uat_path, f"PASS human UAT for {candidate}\n")
    uat_record_commit = _commit_docs(repo, "record human UAT")

    acceptance_path = Path("docs/codex/local-v1-human-acceptance.txt")
    _write(repo, acceptance_path, f"Human accepted Local v1 candidate {candidate}\n")
    acceptance_record_commit = _commit_docs(repo, "record human acceptance")

    payload = _disposition_for_stage(_read_disposition(), "uninitialized")
    payload["record_status"] = "accepted"
    payload["candidate"] = {
        "frozen_commit": candidate,
        "identity_evidence_path": identity_path.as_posix(),
        "identity_evidence_sha256": _sha256(repo / identity_path),
        "clean_tree_observed": True,
        "clean_tree_observation_method": "candidate_gate_transcript",
        "clean_tree_observation_commit": candidate,
    }
    payload["candidate_gate"] = {
        "passed": True,
        "candidate_commit": candidate,
        "transcript_path": gate_path.as_posix(),
        "transcript_sha256": _sha256(repo / gate_path),
    }
    payload["independent_review"] = {
        "completed": True,
        "reviewed_candidate_commit": candidate,
        "disposition": "GO",
        "record_path": review_path.as_posix(),
        "record_sha256": _sha256(repo / review_path),
        "critical_findings": 0,
        "high_findings": 0,
        "medium_findings": 0,
        "low_findings": 0,
    }
    payload["human_uat"] = {
        "completed": True,
        "tested_candidate_commit": candidate,
        "result": "PASS",
        "record_path": uat_path.as_posix(),
        "record_sha256": _sha256(repo / uat_path),
    }
    payload["human_acceptance"] = {
        "accepted": True,
        "accepted_candidate_commit": candidate,
        "record_path": acceptance_path.as_posix(),
        "record_sha256": _sha256(repo / acceptance_path),
    }
    payload["disposition_lineage"] = {
        "disposition_parent_commit": acceptance_record_commit,
        "declared_candidate_descendants": [
            {
                "commit": candidate_record_commit,
                "purpose": "candidate_gate_record",
            },
            {
                "commit": review_record_commit,
                "purpose": "independent_review_record",
            },
            {"commit": uat_record_commit, "purpose": "human_uat_record"},
            {
                "commit": acceptance_record_commit,
                "purpose": "human_acceptance_record",
            },
        ],
        "allowed_descendant_purposes": list(
            local_v1_contract_check.ALLOWED_DESCENDANT_PURPOSES
        ),
    }
    payload["authority"] = {
        "candidate_qualified": True,
        "release_allowed": True,
        "promotion_allowed": False,
        "production_allowed": False,
        "uat_authority_inherited": False,
        "new_governed_powers_allowed": False,
    }
    _write(repo, local_v1_contract_check.CONTRACT_REL, _contract_for_stage("accepted"))
    _write(
        repo,
        local_v1_contract_check.DISPOSITION_REL,
        json.dumps(payload, indent=2) + "\n",
    )
    _git(repo, "add", local_v1_contract_check.CONTRACT_REL.as_posix())
    _git(repo, "add", local_v1_contract_check.DISPOSITION_REL.as_posix())
    _git(repo, "commit", "-q", "-m", "record final disposition")
    assert _git(repo, "status", "--porcelain=v1") == ""
    return repo, payload


def _read_disposition() -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(
        (ROOT / local_v1_contract_check.DISPOSITION_REL).read_text(encoding="utf-8")
    )
    return payload


def _disposition_for_stage(
    accepted_payload: dict[str, Any], stage: str
) -> dict[str, Any]:
    stages = (
        "uninitialized",
        "candidate_recorded",
        "reviewed",
        "uat_complete",
        "accepted",
    )
    stage_index = stages.index(stage)
    payload = copy.deepcopy(accepted_payload)
    payload["record_status"] = stage
    if stage_index < 1:
        payload["candidate"] = {
            "frozen_commit": None,
            "identity_evidence_path": None,
            "identity_evidence_sha256": None,
            "clean_tree_observed": False,
            "clean_tree_observation_method": None,
            "clean_tree_observation_commit": None,
        }
        payload["candidate_gate"] = {
            "passed": False,
            "candidate_commit": None,
            "transcript_path": None,
            "transcript_sha256": None,
        }
    if stage_index < 2:
        payload["independent_review"] = {
            "completed": False,
            "reviewed_candidate_commit": None,
            "disposition": None,
            "record_path": None,
            "record_sha256": None,
            "critical_findings": None,
            "high_findings": None,
            "medium_findings": None,
            "low_findings": None,
        }
    if stage_index < 3:
        payload["human_uat"] = {
            "completed": False,
            "tested_candidate_commit": None,
            "result": None,
            "record_path": None,
            "record_sha256": None,
        }
    if stage_index < 4:
        payload["human_acceptance"] = {
            "accepted": False,
            "accepted_candidate_commit": None,
            "record_path": None,
            "record_sha256": None,
        }
        payload["disposition_lineage"] = {
            "disposition_parent_commit": None,
            "declared_candidate_descendants": [],
            "allowed_descendant_purposes": list(
                local_v1_contract_check.ALLOWED_DESCENDANT_PURPOSES
            ),
        }
    payload["authority"] = {
        "candidate_qualified": stage_index >= 1,
        "release_allowed": stage_index == 4,
        "promotion_allowed": False,
        "production_allowed": False,
        "uat_authority_inherited": False,
        "new_governed_powers_allowed": False,
    }
    return payload


def _contract_for_stage(stage: str) -> str:
    contract = (ROOT / local_v1_contract_check.CONTRACT_REL).read_text(
        encoding="utf-8"
    )
    accepted = stage == "accepted"
    outcome_status = "complete" if accepted else "not_started"
    contract = re.sub(
        r"^- Release outcomes complete: `[^`]+`$",
        f"- Release outcomes complete: `{'8/8' if accepted else '0/8'}`",
        contract,
        flags=re.MULTILINE,
    )
    contract = re.sub(
        r"^- Critical-path milestones complete: `[^`]+`$",
        f"- Critical-path milestones complete: `{'8/8' if accepted else '0/8'}`",
        contract,
        flags=re.MULTILINE,
    )
    contract = re.sub(
        r"^- Latest completed milestone: `[^`]+`$",
        f"- Latest completed milestone: `{'LV1-007' if accepted else 'none'}`",
        contract,
        flags=re.MULTILINE,
    )
    contract = re.sub(
        r"^- Active next action: `[^`]+`$",
        f"- Active next action: `{'release_decision' if accepted else 'LV1-000'}`",
        contract,
        flags=re.MULTILINE,
    )
    contract = re.sub(
        r"^- Local-v1 release gate: `[^`]+`$",
        f"- Local-v1 release gate: `{'complete' if accepted else 'blocked'}`",
        contract,
        flags=re.MULTILINE,
    )
    contract = re.sub(
        r"^- Human UAT: `[^`]+`$",
        f"- Human UAT: `{'complete' if accepted else 'not_started'}`",
        contract,
        flags=re.MULTILINE,
    )
    contract = re.sub(
        r"^- Release acceptance: `[^`]+`$",
        f"- Release acceptance: `{'true' if accepted else 'false'}`",
        contract,
        flags=re.MULTILINE,
    )
    contract = re.sub(
        r"^(\| `O[1-8]` \| [^|]+ \|) `[^`]+` (\|)",
        rf"\1 `{outcome_status}` \2",
        contract,
        flags=re.MULTILINE,
    )
    milestone_number = 0

    def replace_milestone(match: re.Match[str]) -> str:
        nonlocal milestone_number
        status = "complete" if accepted else (
            "in_progress" if milestone_number == 0 else "not_started"
        )
        milestone_number += 1
        return f"{match.group(1)} `{status}` {match.group(2)}"

    return re.sub(
        r"^(\| `LV1-\d{3}` \| [^|]+ \|) `[^`]+` (\|)",
        replace_milestone,
        contract,
        flags=re.MULTILINE,
    )


def _write(repo: Path, relative_path: Path, content: str) -> None:
    path = repo / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _commit_docs(repo: Path, message: str) -> str:
    _git(repo, "add", "docs/codex")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()

from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts import (
    live_demo_preflight,
    local_v1_contract_check,
    local_v1_golden_path_check,
)

ROOT = Path(__file__).resolve().parents[1]


def _golden() -> str:
    return (ROOT / local_v1_golden_path_check.GOLDEN_PATH_REL).read_text(
        encoding="utf-8"
    )


def test_live_local_v1_golden_path_is_valid_and_fail_closed() -> None:
    report = local_v1_golden_path_check.build_report(ROOT)

    assert report["valid"] is True, report["failures"]
    assert report["tool_count"] == 24
    assert report["two_leg_path"] is True
    assert report["real_hermes_through_node_claimed"] is False
    assert report["mcc_007_implementation_authorized"] is False
    assert report["runtime_authority_granted"] is False
    assert report["release_authority_granted"] is False
    assert report["uat_complete"] is False


def test_golden_path_rejects_integrated_runner_and_authority_claims() -> None:
    drifted = (
        _golden()
        + "\nA real Hermes-through-Node mission is proven.\n"
        + "MCC-007 implementation is authorized.\n"
        + "Human UAT is complete.\n"
    )

    failures = local_v1_golden_path_check.validate_golden_text(drifted)

    assert any("real Hermes-through-Node mission is proven" in failure for failure in failures)
    assert any("MCC-007 implementation is authorized" in failure for failure in failures)
    assert any("human UAT is complete" in failure for failure in failures)


def test_golden_path_rejects_cleanup_before_start() -> None:
    golden = _golden()
    drifted = golden.replace(
        "make compose-up",
        "make compose-order-marker",
        1,
    ).replace(
        "make compose-down",
        "make compose-up",
        1,
    ).replace(
        "make compose-order-marker",
        "make compose-down",
        1,
    )

    failures = local_v1_golden_path_check.validate_golden_text(drifted)

    assert any(
        "commands are out of order" in failure or "cleanup appears before" in failure
        for failure in failures
    )


def test_golden_path_rejects_destructive_sequential_env_setup() -> None:
    safe_block = """```sh
if [ -e .env ]; then
  chmod 600 .env
else
  install -m 600 .env.example .env
fi
make admin-token-generate
```"""
    destructive_block = """```sh
test ! -e .env
install -m 600 .env.example .env
make admin-token-generate
```"""
    drifted = _golden().replace(safe_block, destructive_block, 1)

    failures = local_v1_golden_path_check.validate_golden_text(drifted)

    assert any("missing the fail-closed non-overwrite" in failure for failure in failures)
    assert any("destructive sequential .env setup" in failure for failure in failures)


def test_golden_path_rejects_embedded_credentials() -> None:
    drifted = _golden() + "\nITHILDIN_ADMIN_TOKEN=should-never-be-committed\n"

    failures = local_v1_golden_path_check.validate_golden_text(drifted)

    assert any("credential-like text" in failure for failure in failures)


def test_golden_path_rejects_unbound_legacy_freshness_claims() -> None:
    drifted = (
        _golden()
        + "\nValidate existing immutable evidence.\n"
        + "Hermes evidence is current-candidate fresh.\n"
        + "Legacy evidence proves current-candidate provenance.\n"
    )

    failures = local_v1_golden_path_check.validate_golden_text(drifted)

    assert any("existing immutable evidence" in failure for failure in failures)
    assert any("Hermes evidence is current-candidate fresh" in failure for failure in failures)
    assert any(
        "legacy evidence proves current-candidate provenance" in failure
        for failure in failures
    )


def test_golden_path_evidence_bindings_match_current_sources() -> None:
    failures = local_v1_golden_path_check._validate_evidence_source_bindings(  # noqa: SLF001
        demo_flow=(ROOT / "scripts/demo_flow.py").read_text(encoding="utf-8"),
        hermes_checker=(ROOT / "scripts/hermes_poc_evidence_check.py").read_text(
            encoding="utf-8"
        ),
        node_checker=(
            ROOT / "scripts/node_governed_access_poc_evidence_check.py"
        ).read_text(encoding="utf-8"),
        node_release_checker=(
            ROOT / "scripts/node_release_artifact_poc_evidence_check.py"
        ).read_text(encoding="utf-8"),
        mission_checker=(
            ROOT / "scripts/mission_command_control_plane_poc_evidence_check.py"
        ).read_text(encoding="utf-8"),
    )

    assert failures == []


def test_node_release_artifact_partial_binding_drift_is_rejected() -> None:
    demo_flow = (ROOT / "scripts/demo_flow.py").read_text(encoding="utf-8")
    hermes_checker = (ROOT / "scripts/hermes_poc_evidence_check.py").read_text(
        encoding="utf-8"
    )
    node_checker = (
        ROOT / "scripts/node_governed_access_poc_evidence_check.py"
    ).read_text(encoding="utf-8")
    release_checker = (
        ROOT / "scripts/node_release_artifact_poc_evidence_check.py"
    ).read_text(encoding="utf-8")
    mission_checker = (
        ROOT / "scripts/mission_command_control_plane_poc_evidence_check.py"
    ).read_text(encoding="utf-8")

    missing_binding = local_v1_golden_path_check._validate_evidence_source_bindings(  # noqa: SLF001
        demo_flow=demo_flow,
        hermes_checker=hermes_checker,
        node_checker=node_checker,
        node_release_checker=release_checker.replace(
            'current_artifact.get("source_dirty") is False',
            'current_artifact.get("source_dirty") is True',
            1,
        ),
        mission_checker=mission_checker,
    )
    newly_clean_bound = local_v1_golden_path_check._validate_evidence_source_bindings(  # noqa: SLF001
        demo_flow=demo_flow,
        hermes_checker=hermes_checker,
        node_checker=node_checker,
        node_release_checker=release_checker + "\ncurrent_worktree_clean = True\n",
        mission_checker=mission_checker,
    )

    assert any("partial commit binding" in failure for failure in missing_binding)
    assert any("partial-binding claim is stale" in failure for failure in newly_clean_bound)


def test_operator_entry_docs_route_to_golden_path_without_full_release_prerequisite() -> None:
    quickstart = (ROOT / local_v1_golden_path_check.QUICKSTART_REL).read_text(
        encoding="utf-8"
    )
    trial = (ROOT / local_v1_golden_path_check.TRIAL_REL).read_text(encoding="utf-8")

    assert "local-v1-golden-path.md" in quickstart
    assert "local-v1-golden-path.md" in trial
    assert "make local-v1-golden-path-check" in quickstart
    assert "make local-v1-golden-path-check" in trial
    assert re.search(r"(?m)^make release-check$", trial) is None
    assert "make local-v1-candidate-check" in trial


def test_golden_path_target_is_in_milestone_and_exact_candidate_inventory() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    milestone_body = local_v1_golden_path_check._target_body(  # noqa: SLF001
        makefile, "local-v1-milestone-check"
    )
    inventory_body = local_v1_golden_path_check._target_body(  # noqa: SLF001
        makefile, "local-v1-candidate-inventory"
    )
    inventory_targets = tuple(
        re.findall(r"^\t\$\(MAKE\) ([a-z0-9][a-z0-9-]*)$", inventory_body, re.MULTILINE)
    )

    assert "$(MAKE) local-v1-golden-path-check" in milestone_body
    assert "$(MAKE) local-v1-golden-path-check" in inventory_body
    assert len(inventory_targets) == 36
    assert inventory_targets == local_v1_contract_check.LOCAL_V1_CANDIDATE_TARGETS
    assert "mission-command-control-plane-poc" not in inventory_targets
    assert "hermes-poc-run" not in inventory_targets
    assert "compose-up" not in inventory_targets


def test_live_demo_preflight_accepts_owner_only_env_mode(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("# operator-owned local configuration\n", encoding="utf-8")
    env_path.chmod(0o600)
    failures: list[str] = []

    mode = live_demo_preflight._check_existing_env_permissions(  # noqa: SLF001
        env_path, failures
    )

    assert mode == 0o600
    assert failures == []


@pytest.mark.parametrize("mode", [0o640, 0o604, 0o666])
def test_live_demo_preflight_rejects_group_or_world_env_bits(
    tmp_path: Path,
    mode: int,
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("# operator-owned local configuration\n", encoding="utf-8")
    env_path.chmod(mode)
    failures: list[str] = []

    observed = live_demo_preflight._check_existing_env_permissions(  # noqa: SLF001
        env_path, failures
    )

    assert observed == mode
    assert len(failures) == 1
    assert "group/world permission bits" in failures[0]
    assert f"{mode:04o}" in failures[0]

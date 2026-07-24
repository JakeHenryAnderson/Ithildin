from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from scripts import local_v1_lv1_003_o4_execution_authorization_check as gate

ROOT = Path(".")


def _contract() -> dict[str, object]:
    document = json.loads(gate.CONTRACT.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def test_live_o4_execution_gate_is_valid_prepare_review_and_non_authorizing() -> None:
    report = gate.build_report(ROOT)

    assert report["valid"] is True, report["failures"]
    assert report["record_status"] == "PREPARE_REVIEW"
    assert report["reviewed_implementation_commit"] == gate.REVIEWED_IMPLEMENTATION_COMMIT
    assert report["code_authorization_commit"] == gate.CODE_AUTHORIZATION_COMMIT
    assert report["future_execution_candidate_commit"] is None
    assert report["future_execution_candidate_tree"] is None
    assert report["execution_attempt_budget"] == 0
    assert report["live_execution_authorized"] is False
    assert report["docker_lifecycle_authorized"] is False
    assert report["provider_access_authorized"] is False
    assert report["o4_evidence_execution_authorized"] is False
    assert report["new_governed_tool"] is False
    assert report["release_allowed"] is False
    assert report["uat_complete"] is False


def test_live_gate_refuses_before_any_future_candidate_is_bound() -> None:
    with pytest.raises(
        gate.O4ExecutionAuthorizationError,
        match="o4_live_execution_not_authorized",
    ):
        gate.assert_live_execution_authorized(
            ROOT,
            candidate_commit="a" * 40,
            candidate_tree="b" * 40,
        )


@pytest.mark.parametrize(
    ("mutate", "failure_fragment"),
    [
        (
            lambda value: value.__setitem__(
                "future_execution_candidate_commit", "a" * 40
            ),
            "future_execution_candidate_commit",
        ),
        (
            lambda value: value.__setitem__(
                "future_execution_candidate_tree", "b" * 40
            ),
            "future_execution_candidate_tree",
        ),
        (
            lambda value: value.__setitem__("record_status", "AUTHORIZED_EXACT_CANDIDATE"),
            "record_status",
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
                "current_assembler_usable_for_live_producer", True
            ),
            "evidence contract",
        ),
        (
            lambda value: value["evidence_contract"][
                "bounded_image_metadata_fields"
            ].append("sbom_digest"),  # type: ignore[index,union-attr]
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
                "unexpected", True
            ),
            "cleanup contract",
        ),
        (
            lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
                "docker_lifecycle_authorized", True
            ),
            "authority must remain all false",
        ),
        (
            lambda value: value.__setitem__("unexpected", False),
            "fields are not closed",
        ),
    ],
)
def test_prepare_review_contract_rejects_authority_or_scope_drift(
    mutate: object,
    failure_fragment: str,
) -> None:
    contract = copy.deepcopy(_contract())
    assert callable(mutate)
    mutate(contract)
    failures: list[str] = []

    gate._validate_contract(contract, failures)  # type: ignore[arg-type] # noqa: SLF001

    assert any(failure_fragment in failure for failure in failures)


def test_authorization_json_rejects_duplicate_keys(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text('{"schema_version":"1","schema_version":"2"}\n', encoding="utf-8")
    failures: list[str] = []

    result = gate._read_contract(path, failures)  # noqa: SLF001

    assert result == {}
    assert failures == [
        "O4 execution authorization JSON is unavailable or ambiguous"
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

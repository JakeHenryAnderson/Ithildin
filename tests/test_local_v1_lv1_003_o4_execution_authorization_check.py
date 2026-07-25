from __future__ import annotations

import copy
import json
import shutil
import subprocess
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


def _authorized_child_repository(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "candidate"
    subprocess.run(
        ["git", "clone", "-q", str(Path.cwd()), str(repo)],
        check=True,
    )
    _run_git(repo, "checkout", "--detach", gate.CANDIDATE_PARENT_COMMIT)
    for relative in gate.CONTROL_PATH_ALLOWLIST:
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, destination)
    _run_git(repo, "add", "--", *gate.CONTROL_PATH_ALLOWLIST)
    _run_git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: exact O4 disposition child",
    )
    return repo, _run_git(repo, "rev-parse", "HEAD"), _run_git(
        repo, "show", "-s", "--format=%T", "HEAD"
    )


def test_attempt_001_closure_is_valid_and_all_authority_is_false() -> None:
    report = gate.build_report(ROOT)

    assert report["valid"] is True
    assert report["failures"] == []
    assert report["record_status"] == "ATTEMPT_CONSUMED_PRE_GATE_IMPORT_FAILURE"
    assert report["reviewed_implementation_commit"] == gate.REVIEWED_IMPLEMENTATION_COMMIT
    assert report["code_authorization_commit"] == gate.CODE_AUTHORIZATION_COMMIT
    assert report["attempt_id"] == gate.ATTEMPT_ID
    assert report["attempted_candidate_commit"] == gate.ATTEMPTED_CANDIDATE_COMMIT
    assert report["attempted_candidate_tree"] == gate.ATTEMPTED_CANDIDATE_TREE
    assert report["attempt_consumed"] is True
    assert report["retry_authorized"] is False
    contract = _contract()
    assert (
        contract["code_authorization_origin_record_sha256"]
        == gate.CODE_AUTHORIZATION_ORIGIN_RECORD_DIGEST
    )
    assert (
        contract["code_authorization_record_sha256"]
        == gate.CODE_AUTHORIZATION_RECORD_DIGEST
    )
    assert report["execution_checkout_commit"] is None
    assert report["execution_checkout_tree"] is None
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
    assert not any(value is True for value in authority.values())


def test_live_gate_refuses_consumed_attempt() -> None:
    with pytest.raises(
        gate.O4ExecutionAuthorizationError,
        match="o4_live_execution_not_authorized",
    ):
        gate.assert_live_execution_authorized(
            ROOT,
            candidate_commit=gate.ATTEMPTED_CANDIDATE_COMMIT,
            candidate_tree=gate.ATTEMPTED_CANDIDATE_TREE,
        )


@pytest.mark.parametrize(
    ("mutate", "failure_fragment"),
    [
        (
            lambda value: value.__setitem__(
                "execution_candidate_commit", "a" * 40
            ),
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
            lambda value: value.__setitem__("attempted_candidate_commit", "a" * 40),
            "attempted_candidate_commit",
        ),
        (
            lambda value: value["attempt_invocation"].__setitem__(  # type: ignore[union-attr]
                "command", "python scripts/local_v1_lv1_003_o4_producer.py"
            ),
            "attempt_invocation",
        ),
        (
            lambda value: value["attempt_invocation"].__setitem__(  # type: ignore[union-attr]
                "classification", "SUCCESS"
            ),
            "attempt_invocation",
        ),
        (
            lambda value: value["attempt_root_absence"]["absent_roots"].pop(),  # type: ignore[index,union-attr]
            "attempt_root_absence",
        ),
        (
            lambda value: value.__setitem__("attempt_consumed", False),
            "attempt_consumed",
        ),
        (
            lambda value: value.__setitem__("retry_authorized", True),
            "retry_authorized",
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
            "all false after Attempt 001",
        ),
        (
            lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
                "producer_code_authorized", 1
            ),
            "all false after Attempt 001",
        ),
        (
            lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
                "shell_execution_authorized", True
            ),
            "all false after Attempt 001",
        ),
        (
            lambda value: value["authority"].__setitem__(  # type: ignore[union-attr]
                "release_allowed", 0
            ),
            "all false after Attempt 001",
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


def test_authorization_json_rejects_duplicate_keys(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text('{"schema_version":"1","schema_version":"2"}\n', encoding="utf-8")
    failures: list[str] = []

    result = gate._read_contract(path, failures)  # noqa: SLF001

    assert result == {}
    assert failures == [
        "O4 execution authorization JSON is unavailable or ambiguous"
    ]


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
    disposition = json.loads(
        gate.ATTEMPT_DISPOSITION_JSON.read_text(encoding="utf-8")
    )
    assert callable(mutate)
    mutate(disposition)
    failures: list[str] = []

    gate._validate_attempt_disposition(  # noqa: SLF001
        disposition,
        gate.ATTEMPT_DISPOSITION_DOCUMENT.read_text(encoding="utf-8"),
        failures,
    )

    assert "O4 Attempt 001 disposition is not closed and exact" in failures


def test_bound_review_or_disposition_digest_drift_is_rejected(
    tmp_path: Path,
) -> None:
    for relative in (
        gate.PRODUCER_EXACT_REVIEW,
        gate.DISPOSITION_JSON,
        gate.DISPOSITION_DOCUMENT,
        gate.ATTEMPT_DISPOSITION_JSON,
        gate.ATTEMPT_DISPOSITION_DOCUMENT,
    ):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, destination)
    (tmp_path / gate.ATTEMPT_DISPOSITION_DOCUMENT).write_text(
        "altered\n",
        encoding="utf-8",
    )
    failures: list[str] = []

    gate._validate_bound_documents(tmp_path, failures)  # noqa: SLF001

    assert any("Attempt 001 disposition document digest" in value for value in failures)


def test_execution_checkout_rejects_descendant_dirty_and_extra_path(
    tmp_path: Path,
) -> None:
    repo, _, _ = _authorized_child_repository(tmp_path)
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
        "O4 Attempt 001 observed-absent root is now present: "
        "var/local-v1-lv1-003-o4-runtime"
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
    assert "writes and verifies `node-revocation-recovery.json`" in " ".join(
        document.split()
    )


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

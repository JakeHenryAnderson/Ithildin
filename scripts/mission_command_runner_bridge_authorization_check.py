"""Validate the candidate-bound MCC-007 code-only authorization record."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import mission_command_runner_bridge_decision_check as decision_check  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TARGET = "mission-command-runner-bridge-authorization-check"
AUTHORIZATION = "docs/codex/mission-command-runner-bridge-authorization-record.md"
REVIEW_DOCUMENT = "docs/codex/local-v1-lv1-003-o4-producer-exact-review.md"
PREVIOUS_REVIEW_DOCUMENT = "docs/codex/local-v1-lv1-003-exact-review.md"
START = "<!-- mission-command-runner-bridge-authorization:start -->"
END = "<!-- mission-command-runner-bridge-authorization:end -->"
PREVIOUS_REVIEWED_COMMIT = "da5fd021bddb48ad663aa0a409da036bc854b516"
PREVIOUS_REVIEWED_TREE = "f489dee60235d04eb8bc64cc6bb55e8534db1f8e"
REVIEWED_COMMIT = "5dab3654391c14fe214a9dfe302c099d0fe5fbf8"
REVIEWED_PARENT = "7b293a30823b20aef7a32a2f22910b66f822c35f"
REVIEWED_TREE = "f9a0cb66ac12e6e0ecca7fc23a0071be0dbe3075"
PREVIOUS_DECISION_DIGEST = (
    "sha256:2a5792c80b672e9e44b24e9ef1e7201990386c90c89e496f17ac2073e04efc72"
)
PREVIOUS_REVIEW_DOCUMENT_DIGEST = (
    "sha256:3b9bb240810995ce97a963445912e7d0f7431def2e84f590c1e8e60e0e5990c5"
)
CURRENT_DECISION_DIGEST = (
    "sha256:2a5792c80b672e9e44b24e9ef1e7201990386c90c89e496f17ac2073e04efc72"
)
ALLOWED_RUNTIME_PATHS = [
    *decision_check.IMPLEMENTATION_PATHS,
    "scripts/local_v1_lv1_003_o4_producer.py",
    "tests/test_local_v1_lv1_003_o4_producer.py",
]
REVIEWED_PATH_INVENTORY = [
    "Makefile",
    "README.md",
    "docs/codex/local-v1-lv1-003-o4-execution-authorization.json",
    "docs/codex/local-v1-lv1-003-o4-execution-authorization.md",
    "docs/codex/local-v1-lv1-003-o4-producer-contract.md",
    "scripts/local_v1_constrained_mission_journey.py",
    "scripts/local_v1_lv1_003_o4_execution_authorization_check.py",
    "scripts/local_v1_lv1_003_o4_producer.py",
    "tests/test_local_v1_constrained_mission_journey.py",
    "tests/test_local_v1_lv1_003_o4_execution_authorization_check.py",
    "tests/test_local_v1_lv1_003_o4_producer.py",
]
REVIEW_LINEAGE = [
    {
        "stage": "initial_dirty_audit",
        "critical": 0,
        "high": 3,
        "medium": 1,
        "low": 1,
        "disposition": "NO_GO",
    },
    {
        "stage": "first_exact_review",
        "critical": 0,
        "high": 2,
        "medium": 1,
        "low": 1,
        "disposition": "NO_GO",
    },
    {
        "stage": "exact_rereview",
        "critical": 0,
        "high": 0,
        "medium": 1,
        "low": 0,
        "disposition": "NO_GO",
    },
    {
        "stage": "final_exact_review",
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "disposition": "GO",
    },
    {
        "stage": "producer_exact_review",
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "disposition": "GO",
    },
]
FORBIDDEN_RUNTIME_PATHS = [
    "pyproject.toml",
    "uv.lock",
    "apps/api/src/ithildin_api",
    "policies",
    "tool-manifests",
    "tool-manifests.lock.json",
]
TRUE_FIELDS = (
    "code_implementation_authorized",
    "runtime_adapter_code_authorized",
    "runner_bridge_code_authorized",
    "exact_implementation_review_required",
    "exact_implementation_review_complete",
    "separate_live_evidence_authorization_required",
)
FALSE_FIELDS = (
    "live_hermes_execution_authorized",
    "docker_lifecycle_authorized",
    "o4_evidence_execution_authorized",
    "runner_lifecycle_authority",
    "model_provider_authority",
    "prompt_output_evidence_custody_authorized",
    "arbitrary_host_control_authorized",
    "generic_process_control_authorized",
    "shell_execution_authorized",
    "docker_socket_authorized",
    "network_non_bypass_claimed",
    "filesystem_non_bypass_claimed",
    "gateway_api_change_authorized",
    "gateway_schema_change_authorized",
    "policy_change_authorized",
    "manifest_change_authorized",
    "dependency_change_authorized",
    "package_mapping_change_authorized",
    "new_governed_tool",
    "production_identity_authorized",
    "release_allowed",
    "production_promotion_allowed",
    "uat_complete",
    "sol_ultra_authorized",
)
EXPECTED_KEYS = {
    "document_type",
    "schema_version",
    "ticket_id",
    "decision",
    "tool_count",
    "authority_source",
    "previous_reviewed_candidate_commit",
    "previous_reviewed_candidate_tree",
    "previous_decision_sha256",
    "previous_review_document",
    "previous_review_document_sha256",
    "current_decision_sha256",
    "reviewed_candidate_commit",
    "reviewed_candidate_parent",
    "reviewed_candidate_tree",
    "review_document",
    "reviewer",
    "review_disposition",
    "review_lineage",
    *TRUE_FIELDS,
    *FALSE_FIELDS,
    "allowed_runtime_paths",
    "forbidden_runtime_paths",
    "reviewed_path_inventory",
}


class AuthorizationContractError(ValueError):
    """Raised when the authorization contract is ambiguous."""


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    authorization_text = _read(repo_root / AUTHORIZATION, failures)
    decision_text = _read(repo_root / decision_check.DECISION, failures)
    review_text = _read(repo_root / REVIEW_DOCUMENT, failures)
    previous_review_text = _read(repo_root / PREVIOUS_REVIEW_DOCUMENT, failures)
    try:
        authorization = _contract(authorization_text)
    except AuthorizationContractError as exc:
        failures.append(str(exc))
        authorization = {}

    _validate_contract(authorization, decision_text, failures)
    decision_report = decision_check.build_report(repo_root)
    if not decision_report["valid"]:
        failures.append("reviewed runner-bridge decision is not currently valid")
    if decision_report["implementation_authorized"] is not False:
        failures.append("decision candidate must remain non-authorizing")

    reviewed_tree = _git(
        repo_root,
        ["show", "-s", "--format=%T", PREVIOUS_REVIEWED_COMMIT],
        failures,
    )
    if reviewed_tree != PREVIOUS_REVIEWED_TREE:
        failures.append("reviewed candidate Git tree does not match authorization")
    reviewed_decision = _git(
        repo_root,
        ["show", f"{PREVIOUS_REVIEWED_COMMIT}:{decision_check.DECISION}"],
        failures,
        strip=False,
    )
    if reviewed_decision and _digest(reviewed_decision) != PREVIOUS_DECISION_DIGEST:
        failures.append("reviewed candidate decision digest does not match authorization")
    ancestry = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "merge-base",
            "--is-ancestor",
            PREVIOUS_REVIEWED_COMMIT,
            "HEAD",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if ancestry.returncode != 0:
        failures.append("reviewed decision candidate is not an ancestor of HEAD")

    reviewed_tree = _git(
        repo_root,
        ["show", "-s", "--format=%T", REVIEWED_COMMIT],
        failures,
    )
    if reviewed_tree != REVIEWED_TREE:
        failures.append("exact reviewed implementation tree does not match authorization")
    reviewed_parent = _git(
        repo_root,
        ["show", "-s", "--format=%P", REVIEWED_COMMIT],
        failures,
    )
    if reviewed_parent != REVIEWED_PARENT:
        failures.append("exact reviewed implementation parent does not match authorization")
    reviewed_decision = _git(
        repo_root,
        ["show", f"{REVIEWED_COMMIT}:{decision_check.DECISION}"],
        failures,
        strip=False,
    )
    if reviewed_decision and _digest(reviewed_decision) != CURRENT_DECISION_DIGEST:
        failures.append(
            "exact reviewed implementation decision digest does not match authorization"
        )
    reviewed_paths = _git(
        repo_root,
        ["diff-tree", "--no-commit-id", "--name-only", "-r", REVIEWED_COMMIT],
        failures,
    ).splitlines()
    if reviewed_paths != REVIEWED_PATH_INVENTORY:
        failures.append("exact reviewed implementation path inventory does not match authorization")
    candidate_ancestry = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "merge-base",
            "--is-ancestor",
            REVIEWED_COMMIT,
            "HEAD",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if candidate_ancestry.returncode != 0:
        failures.append("exact reviewed implementation candidate is not an ancestor of HEAD")

    authorized_runtime_matches_reviewed_candidate = _validate_authorized_runtime_state(
        repo_root,
        failures,
    )
    _validate_text(authorization_text, failures)
    _validate_review_text(review_text, failures)
    if _digest(previous_review_text) != PREVIOUS_REVIEW_DOCUMENT_DIGEST:
        failures.append("historical runner-bridge exact review digest is invalid")
    _validate_wiring(repo_root, failures)
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "tool_count": authorization.get("tool_count"),
        "reviewed_candidate_commit": authorization.get(
            "reviewed_candidate_commit"
        ),
        "authorized_runtime_matches_reviewed_candidate": (
            authorized_runtime_matches_reviewed_candidate
        ),
        "code_implementation_authorized": authorization.get(
            "code_implementation_authorized"
        ),
        "live_hermes_execution_authorized": authorization.get(
            "live_hermes_execution_authorized"
        ),
        "docker_lifecycle_authorized": authorization.get(
            "docker_lifecycle_authorized"
        ),
        "o4_evidence_execution_authorized": authorization.get(
            "o4_evidence_execution_authorized"
        ),
        "new_governed_tool": authorization.get("new_governed_tool"),
        "release_allowed": authorization.get("release_allowed"),
        "uat_complete": authorization.get("uat_complete"),
    }


def _validate_contract(
    authorization: dict[str, Any],
    decision_text: str,
    failures: list[str],
) -> None:
    if _digest(decision_text) != CURRENT_DECISION_DIGEST:
        failures.append("current runner-bridge decision does not match review-needed digest")
    expected: dict[str, object] = {
        "document_type": "runner_bridge_authorization_record",
        "schema_version": "1",
        "ticket_id": "MCC-007",
        "decision": "exact_candidate_go_code_only",
        "tool_count": 24,
        "authority_source": "user_local_v1_to_uat_direction_and_standing_delegation",
        "previous_reviewed_candidate_commit": PREVIOUS_REVIEWED_COMMIT,
        "previous_reviewed_candidate_tree": PREVIOUS_REVIEWED_TREE,
        "previous_decision_sha256": PREVIOUS_DECISION_DIGEST,
        "previous_review_document": PREVIOUS_REVIEW_DOCUMENT,
        "previous_review_document_sha256": PREVIOUS_REVIEW_DOCUMENT_DIGEST,
        "current_decision_sha256": CURRENT_DECISION_DIGEST,
        "reviewed_candidate_commit": REVIEWED_COMMIT,
        "reviewed_candidate_parent": REVIEWED_PARENT,
        "reviewed_candidate_tree": REVIEWED_TREE,
        "review_document": REVIEW_DOCUMENT,
        "reviewer": "independent GPT-5.6 Sol xhigh",
        "review_disposition": "GO_CODE_ONLY",
        "review_lineage": REVIEW_LINEAGE,
        "allowed_runtime_paths": ALLOWED_RUNTIME_PATHS,
        "forbidden_runtime_paths": FORBIDDEN_RUNTIME_PATHS,
        "reviewed_path_inventory": REVIEWED_PATH_INVENTORY,
    }
    if set(authorization) != EXPECTED_KEYS:
        failures.append("runner-bridge authorization contract fields are not closed")
    for key, value in expected.items():
        if authorization.get(key) != value:
            failures.append(f"runner-bridge authorization {key} must equal {value!r}")
    for key in TRUE_FIELDS:
        if authorization.get(key) is not True:
            failures.append(f"runner-bridge authorization {key} must be true")
    for key in FALSE_FIELDS:
        if authorization.get(key) is not False:
            failures.append(f"runner-bridge authorization {key} must remain false")


def _contract(text: str) -> dict[str, Any]:
    if text.count(START) != 1 or text.count(END) != 1:
        raise AuthorizationContractError("authorization markers must occur exactly once")
    payload = text.split(START, 1)[1].split(END, 1)[0].strip()
    try:
        value = json.loads(payload, object_pairs_hook=_reject_duplicates)
    except (json.JSONDecodeError, AuthorizationContractError) as exc:
        raise AuthorizationContractError("authorization must be unambiguous JSON") from exc
    if not isinstance(value, dict):
        raise AuthorizationContractError("authorization must be an object")
    return value


def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise AuthorizationContractError(f"duplicate authorization key: {key}")
        value[key] = item
    return value


def _validate_text(text: str, failures: list[str]) -> None:
    for token in (
        "authorizes only the exact-reviewed code candidate",
        "It does not authorize a live",
        "`0/3/1/1`",
        "`0/2/1/1`",
        "`0/0/1/0`",
        "`0/0/0/0`",
        "`producer_exact_review`",
        "`GO_CODE_ONLY`",
        "Any staged, unstaged, deleted, renamed, or",
        "untracked runtime-path delta invalidates code authority",
        "If an implementation owner needs any unauthorized path or power",
        "separate live-evidence",
        "Sol Ultra remains prohibited",
    ):
        if token not in text:
            failures.append(f"runner-bridge authorization is missing required token: {token}")


def _validate_review_text(text: str, failures: list[str]) -> None:
    for token in (
        "Status: `GO`",
        REVIEWED_COMMIT,
        REVIEWED_PARENT,
        REVIEWED_TREE,
        CURRENT_DECISION_DIGEST,
        "independent GPT-5.6 Sol xhigh",
        f"Producer exact review | Candidate `{REVIEWED_COMMIT}` | 0 | 0 | 0 | 0 | `GO`",
        "exact 11-path candidate",
        "`LV1-003` remains `in_progress`",
        "`O4` remains `not_started`",
        "separately reviewed live-evidence authorization",
        "All live Hermes/provider, Docker lifecycle",
    ):
        if token not in text:
            failures.append(f"runner-bridge exact review is missing required token: {token}")
    for path in REVIEWED_PATH_INVENTORY:
        if text.count(f"`{path}`") != 1:
            failures.append(
                f"runner-bridge exact review must name reviewed path exactly once: {path}"
            )


def _validate_authorized_runtime_state(
    repo_root: Path,
    failures: list[str],
    *,
    reviewed_commit: str = REVIEWED_COMMIT,
) -> bool:
    initial_failure_count = len(failures)
    cached = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "diff",
            "--cached",
            "--quiet",
            "--no-ext-diff",
            reviewed_commit,
            "--",
            *ALLOWED_RUNTIME_PATHS,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if cached.returncode == 1:
        failures.append(
            "authorized runtime index differs from exact reviewed implementation candidate"
        )
    elif cached.returncode != 0:
        failures.append("authorized runtime index comparison failed")

    worktree = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "diff",
            "--quiet",
            "--no-ext-diff",
            "--",
            *ALLOWED_RUNTIME_PATHS,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if worktree.returncode == 1:
        failures.append(
            "authorized runtime worktree differs from the reviewed index state"
        )
    elif worktree.returncode != 0:
        failures.append("authorized runtime worktree comparison failed")

    untracked = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "ls-files",
            "--others",
            "--exclude-standard",
            "--",
            *ALLOWED_RUNTIME_PATHS,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if untracked.returncode != 0:
        failures.append("authorized runtime untracked-path comparison failed")
    elif untracked.stdout.splitlines():
        failures.append(
            "authorized runtime paths contain untracked files outside the exact reviewed candidate"
        )
    return len(failures) == initial_failure_count


def _validate_wiring(repo_root: Path, failures: list[str]) -> None:
    makefile = _read(repo_root / "Makefile", failures)
    target_definitions = sum(
        line.startswith(f"{TARGET}:") for line in makefile.splitlines()
    )
    if target_definitions != 1:
        failures.append(
            "runner-bridge authorization check must have exactly one Make target definition"
        )
    milestone_body = decision_check._target_body(  # noqa: SLF001
        makefile, "local-v1-milestone-check"
    )
    invocation = f"\t$(MAKE) {TARGET}"
    if milestone_body.count(invocation) != 1:
        failures.append(
            "runner-bridge authorization check must occur exactly once in "
            "local-v1-milestone-check"
        )
    release_dependencies = [
        dependency
        for line in makefile.splitlines()
        if line.startswith("release-check:")
        for dependency in line.split(":", 1)[1].split()
    ]
    if release_dependencies.count(TARGET) != 1:
        failures.append(
            "runner-bridge authorization check must occur exactly once as a "
            "release-check dependency"
        )
    for path in (
        repo_root / "README.md",
        repo_root / "scripts/build_docs_site.py",
        repo_root / "scripts/review_docs.py",
        repo_root / "docs/codex/review-docs-index.md",
    ):
        text = _read(path, failures)
        if AUTHORIZATION not in text and Path(AUTHORIZATION).name not in text:
            failures.append(f"{path} is missing the runner-bridge authorization record")


def _git(
    repo_root: Path,
    args: list[str],
    failures: list[str],
    *,
    strip: bool = True,
) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        failures.append(f"git {' '.join(args)} failed")
        return ""
    return result.stdout.rstrip("\n") if strip else result.stdout


def _read(path: Path, failures: list[str]) -> str:
    if not path.is_file():
        failures.append(f"missing runner-bridge authorization input: {path}")
        return ""
    return path.read_text(encoding="utf-8")


def _digest(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "MCC-007 fixed runner-bridge authorization check",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report['tool_count']}",
        "code_implementation_authorized: "
        f"{str(report['code_implementation_authorized']).lower()}",
        "authorized_runtime_matches_reviewed_candidate: "
        f"{str(report['authorized_runtime_matches_reviewed_candidate']).lower()}",
        "live_hermes_execution_authorized: "
        f"{str(report['live_hermes_execution_authorized']).lower()}",
        f"docker_lifecycle_authorized: {str(report['docker_lifecycle_authorized']).lower()}",
        "o4_evidence_execution_authorized: "
        f"{str(report['o4_evidence_execution_authorized']).lower()}",
        f"new_governed_tool: {str(report['new_governed_tool']).lower()}",
        f"release_allowed: {str(report['release_allowed']).lower()}",
        f"uat_complete: {str(report['uat_complete']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def main() -> int:
    report = build_report(ROOT)
    print(render_report(report))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

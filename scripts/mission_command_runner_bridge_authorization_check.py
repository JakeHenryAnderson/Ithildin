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
START = "<!-- mission-command-runner-bridge-authorization:start -->"
END = "<!-- mission-command-runner-bridge-authorization:end -->"
REVIEWED_COMMIT = "6cc8a4f1f9deceee231b185cf0d7f0acd63bb313"
REVIEWED_TREE = "542f6d3b146b8bb5fa07f7cd73f80329d6de8ab6"
DECISION_DIGEST = "sha256:3edb0ce71c01e9e3763a622642ab531b64bfa1d001575e9cad9a601f05101b98"
ALLOWED_RUNTIME_PATHS = decision_check.IMPLEMENTATION_PATHS
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
    "reviewed_candidate_commit",
    "reviewed_candidate_tree",
    "decision_sha256",
    "review_disposition",
    "critical_findings",
    "high_findings",
    "medium_findings",
    "low_findings",
    *TRUE_FIELDS,
    *FALSE_FIELDS,
    "allowed_runtime_paths",
    "forbidden_runtime_paths",
}


class AuthorizationContractError(ValueError):
    """Raised when the authorization contract is ambiguous."""


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    authorization_text = _read(repo_root / AUTHORIZATION, failures)
    decision_text = _read(repo_root / decision_check.DECISION, failures)
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

    reviewed_tree = _git(repo_root, ["show", "-s", "--format=%T", REVIEWED_COMMIT], failures)
    if reviewed_tree != REVIEWED_TREE:
        failures.append("reviewed candidate Git tree does not match authorization")
    reviewed_decision = _git(
        repo_root,
        ["show", f"{REVIEWED_COMMIT}:{decision_check.DECISION}"],
        failures,
        strip=False,
    )
    if reviewed_decision and _digest(reviewed_decision) != DECISION_DIGEST:
        failures.append("reviewed candidate decision digest does not match authorization")
    ancestry = subprocess.run(
        ["git", "-C", str(repo_root), "merge-base", "--is-ancestor", REVIEWED_COMMIT, "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if ancestry.returncode != 0:
        failures.append("reviewed decision candidate is not an ancestor of HEAD")

    _validate_text(authorization_text, failures)
    _validate_wiring(repo_root, failures)
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "tool_count": authorization.get("tool_count"),
        "reviewed_candidate_commit": authorization.get("reviewed_candidate_commit"),
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
    expected: dict[str, object] = {
        "document_type": "runner_bridge_authorization_record",
        "schema_version": "1",
        "ticket_id": "MCC-007",
        "decision": "bounded_code_implementation_authorized",
        "tool_count": 24,
        "authority_source": "user_local_v1_to_uat_direction_and_standing_delegation",
        "reviewed_candidate_commit": REVIEWED_COMMIT,
        "reviewed_candidate_tree": REVIEWED_TREE,
        "decision_sha256": _digest(decision_text),
        "review_disposition": "GO",
        "critical_findings": 0,
        "high_findings": 0,
        "medium_findings": 0,
        "low_findings": 0,
        "allowed_runtime_paths": ALLOWED_RUNTIME_PATHS,
        "forbidden_runtime_paths": FORBIDDEN_RUNTIME_PATHS,
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
        "authorizes only the code, tests, deployment profile, evidence harness",
        "It does not authorize a live",
        "rejected decision candidate",
        "If an implementation owner needs any unauthorized path or power",
        "live-evidence authorization",
        "Sol Ultra remains prohibited",
    ):
        if token not in text:
            failures.append(f"runner-bridge authorization is missing required token: {token}")


def _validate_wiring(repo_root: Path, failures: list[str]) -> None:
    makefile = _read(repo_root / "Makefile", failures)
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

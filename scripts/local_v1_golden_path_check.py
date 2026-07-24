"""Validate the operator-facing Ithildin Local-v1 golden path."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_PATH_REL = Path("docs/codex/local-v1-golden-path.md")
QUICKSTART_REL = Path("docs/codex/v1.0-operator-quickstart.md")
TRIAL_REL = Path("docs/codex/v1.0-operator-trial-checklist.md")
CONTRACT_REL = Path("docs/codex/local-v1-completion-contract.md")

REQUIRED_REPOSITORY_PATHS = (
    Path(".env.example"),
    Path("deploy/docker-compose.yml"),
    Path("deploy/hermes-poc/README.md"),
    Path("docs/codex/governed-external-agent-hermes-poc-observed-results.md"),
    Path("docs/codex/track-b-node-governed-access-observed-results.md"),
    Path("docs/codex/mission-command-control-plane-poc-evidence-contract.md"),
    Path("docs/codex/mission-command-runner-bridge-candidate-evaluation.md"),
    Path("scripts/demo_flow.py"),
    Path("scripts/hermes_poc_evidence_check.py"),
    Path("scripts/mission_command_control_plane_poc_evidence_check.py"),
    Path("scripts/node_governed_access_poc_evidence_check.py"),
    Path("scripts/node_release_artifact_poc_evidence_check.py"),
)

REQUIRED_MAKE_TARGETS = (
    "admin-token-generate",
    "local-v1-golden-path-check",
    "live-demo-preflight",
    "demo-readiness-summary",
    "demo-seed",
    "compose-up",
    "compose-smoke",
    "demo-operator-walkthrough",
    "demo-flow",
    "live-demo-status",
    "demo-evidence-packet",
    "workbench-evidence-packet",
    "hermes-governance-poc-plan-check",
    "local-v1-hermes-evidence-check",
    "hermes-poc-image",
    "hermes-poc-config-check",
    "hermes-poc-run",
    "hermes-poc-stop",
    "track-b-node-evidence-check",
    "track-b-node-configuration-evidence-check",
    "track-b-node-governed-access-evidence-check",
    "track-b-node-configuration-trust-rotation-evidence-check",
    "track-b-node-version-posture-evidence-check",
    "track-b-node-identity-key-rotation-evidence-check",
    "track-b-node-service-lifecycle-evidence-check",
    "track-b-node-release-artifact-evidence-check",
    "mission-command-control-plane-plan-check",
    "mission-command-control-plane-poc",
    "mission-command-control-plane-poc-check",
    "compose-down",
)

REQUIRED_PHRASES = (
    "Status: `LV1-001` operator walkthrough, implementation candidate.",
    "Leg A — real agent compatibility",
    "Leg B — synthetic Node and Mission Command evidence",
    "does not claim or demonstrate a real Hermes-through-Node mission",
    "`MCC-007` remains deferred",
    "bounded 24-tool surface",
    "does not sandbox the host",
    "control arbitrary processes",
    "if [ -e .env ]; then",
    "install -m 600 .env.example .env",
    "never copies over an existing `.env`",
    "chmod 600 .env",
    "private, non-captured terminal",
    "no group/world permission bits",
    "ITHILDIN_POSTGRES_DSN",
    "Do not reuse production data or keys.",
    "An allowed read completed and a redaction check passed.",
    "`make demo-flow` does not execute a denied request",
    "The scripted lifecycle is automatically completed",
    "no approval is left pending for the operator",
    "historical Hermes baseline",
    "bounded export",
    "retained ignored local evidence",
    "does not embed or verify a source-candidate commit",
    "does not establish current-candidate freshness or provenance",
    "legacy Node checkers",
    "Most legacy Node content checkers do not bind",
    "Node release-artifact checker",
    "recorded current and rollback artifact `source_commit`",
    "recorded `source_dirty` values to be false",
    "does not require the current worktree to be clean",
    "not exact-current-clean-candidate evidence",
    "MCC-006 checker is uniquely stronger",
    "requires the embedded candidate commit to equal the current commit",
    "exact current clean source candidate",
    "Reproduction is a separate, deliberate operator action.",
    "cannot safely self-enroll",
    "optional `ithildin-node` service's environment variables or command arguments",
    "normal `ithildin-api` service is different",
    "Gateway-derived agent identity and workspace",
    "The Mission Command POC is isolated from the normal stack",
    "not visible in the normal Command Center",
    "**Gateway truth**",
    "**Node connectivity**",
    "**Runner-reported state**",
    "**Model-provider state**",
    "make compose-down",
    "make hermes-poc-stop",
    "What This Path Proves",
    "What This Path Does Not Prove",
    "does not qualify a release candidate",
    "complete human UAT",
    "The deferred runtime seam remains `LV1-003`",
)

ORDERED_COMMANDS = (
    "make local-v1-golden-path-check",
    "make live-demo-preflight",
    "make demo-readiness-summary",
    "make demo-seed",
    "make compose-up",
    "make compose-smoke",
    "make demo-operator-walkthrough",
    "make demo-flow",
    "make live-demo-status",
    "make demo-evidence-packet",
    "make workbench-evidence-packet",
    "make compose-down",
)

FORBIDDEN_CLAIMS = (
    "real Hermes-through-Node mission is proven",
    "MCC-007 is authorized",
    "MCC-007 implementation is authorized",
    "runner bridge is authorized",
    "human UAT is complete",
    "Local v1.0 is accepted",
    "release candidate qualified",
    "production ready",
    "production-ready",
    "secure sandbox",
    "arbitrary host control is authorized",
    "existing immutable evidence",
    "Hermes evidence is current-candidate fresh",
    "Node evidence is current-candidate fresh",
    "legacy evidence proves current-candidate provenance",
)

SECRET_PATTERNS = (
    re.compile(r"ITHILDIN_ADMIN_TOKEN=(?!<generated value>)[^\s`]+"),
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"postgres(?:ql)?://[^\s`]+", re.IGNORECASE),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |ED25519 )?PRIVATE KEY-----"),
    re.compile(r"\b(?:sk|ghp|github_pat)_[A-Za-z0-9_-]{16,}\b"),
)

SAFE_ENV_SETUP_PATTERN = re.compile(
    r"```sh\n"
    r"if \[ -e \.env \]; then\n"
    r"  chmod 600 \.env\n"
    r"else\n"
    r"  install -m 600 \.env\.example \.env\n"
    r"fi\n"
    r"make admin-token-generate\n"
    r"```"
)
DESTRUCTIVE_ENV_SETUP_PATTERN = re.compile(
    r"```sh\n"
    r"test ! -e \.env\n"
    r"install -m 600 \.env\.example \.env\n"
    r"make admin-token-generate\n"
    r"```"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report(ROOT)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(repo_root: Path, *, golden_override: str | None = None) -> dict[str, Any]:
    failures: list[str] = []
    golden = (
        golden_override
        if golden_override is not None
        else _read(repo_root / GOLDEN_PATH_REL, failures)
    )
    quickstart = _read(repo_root / QUICKSTART_REL, failures)
    trial = _read(repo_root / TRIAL_REL, failures)
    contract = _read(repo_root / CONTRACT_REL, failures)
    makefile = _read(repo_root / "Makefile", failures)
    demo_flow = _read(repo_root / "scripts/demo_flow.py", failures)
    hermes_checker = _read(repo_root / "scripts/hermes_poc_evidence_check.py", failures)
    node_checker = _read(
        repo_root / "scripts/node_governed_access_poc_evidence_check.py", failures
    )
    node_release_checker = _read(
        repo_root / "scripts/node_release_artifact_poc_evidence_check.py", failures
    )
    mission_checker = _read(
        repo_root / "scripts/mission_command_control_plane_poc_evidence_check.py",
        failures,
    )
    docs_site = _read(repo_root / "scripts/build_docs_site.py", failures)
    review_docs = _read(repo_root / "scripts/review_docs.py", failures)
    review_index = _read(repo_root / "docs/codex/review-docs-index.md", failures)
    lock = _read_json(repo_root / "tool-manifests.lock.json", failures)

    failures.extend(validate_golden_text(golden))
    failures.extend(
        _validate_evidence_source_bindings(
            demo_flow=demo_flow,
            hermes_checker=hermes_checker,
            node_checker=node_checker,
            node_release_checker=node_release_checker,
            mission_checker=mission_checker,
        )
    )

    manifests = lock.get("manifests") if isinstance(lock, dict) else None
    tool_count = len(manifests) if isinstance(manifests, list) else None
    if tool_count != 24:
        failures.append(f"tool manifest lock contains {tool_count!r} tools, expected 24")

    for relative_path in REQUIRED_REPOSITORY_PATHS:
        if not (repo_root / relative_path).is_file():
            failures.append(f"referenced repository path is missing: {relative_path}")

    failures.extend(_validate_local_links(repo_root, golden))

    for target in REQUIRED_MAKE_TARGETS:
        if not re.search(rf"(?m)^{re.escape(target)}(?:\s[^:]*)?:", makefile):
            failures.append(f"referenced Make target is missing: {target}")

    golden_rel = GOLDEN_PATH_REL.as_posix()
    for label, text in (
        ("operator quickstart", quickstart),
        ("operator trial checklist", trial),
        ("docs-site inputs", docs_site),
        ("review-doc inputs", review_docs),
    ):
        if golden_rel not in text and "local-v1-golden-path.md" not in text:
            failures.append(f"{label} does not navigate to the Local-v1 golden path")
    if "Ithildin Local v1.0 Golden Path" not in review_index:
        failures.append("review-docs index does not navigate to the Local-v1 golden path")

    if re.search(r"(?m)^make release-check$", trial):
        failures.append("ordinary Local-v1 operator trial still requires make release-check")
    if "make local-v1-golden-path-check" not in quickstart:
        failures.append("operator quickstart does not begin with the golden-path checker")
    if "make local-v1-golden-path-check" not in trial:
        failures.append("operator trial checklist does not require the golden-path checker")

    failures.extend(_validate_contract_stage(contract))
    normalized_contract = " ".join(contract.split())
    for phrase in (
        "All runtime, release, promotion, credential-custody, external-system, and UAT authorities",
        "remain false",
        "this contract does not authorize its implementation",
    ):
        if phrase not in normalized_contract:
            failures.append(f"Local-v1 contract lost authority ceiling phrase: {phrase}")

    milestone_body = _target_body(makefile, "local-v1-milestone-check")
    if "$(MAKE) local-v1-golden-path-check" not in milestone_body:
        failures.append("Local-v1 milestone gate does not include the golden-path check")
    inventory_body = _target_body(makefile, "local-v1-candidate-inventory")
    if "$(MAKE) local-v1-golden-path-check" not in inventory_body:
        failures.append("Local-v1 candidate inventory does not include the golden-path check")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "golden_path": golden_rel,
        "tool_count": tool_count,
        "two_leg_path": True,
        "real_hermes_through_node_claimed": False,
        "mcc_007_implementation_authorized": False,
        "runtime_authority_granted": False,
        "release_authority_granted": False,
        "uat_complete": False,
    }


def validate_golden_text(text: str) -> list[str]:
    failures: list[str] = []
    normalized = " ".join(text.split())
    for phrase in REQUIRED_PHRASES:
        if phrase not in normalized:
            failures.append(f"golden path is missing phrase: {phrase}")
    if not SAFE_ENV_SETUP_PATTERN.search(text):
        failures.append("golden path is missing the fail-closed non-overwrite .env conditional")
    if DESTRUCTIVE_ENV_SETUP_PATTERN.search(text):
        failures.append("golden path contains the destructive sequential .env setup")

    positions = [text.find(command) for command in ORDERED_COMMANDS]
    if any(position < 0 for position in positions):
        missing = [
            command for command, position in zip(ORDERED_COMMANDS, positions, strict=True)
            if position < 0
        ]
        failures.append(f"golden path is missing ordered command(s): {missing}")
    elif positions != sorted(positions):
        failures.append("golden path start/exercise/export/cleanup commands are out of order")

    if text.find("make compose-down") < text.find("make compose-up"):
        failures.append("Compose cleanup appears before Compose start")
    if text.find("make hermes-poc-stop") < text.find("make hermes-poc-run"):
        failures.append("Hermes cleanup appears before Hermes start")

    lowered = text.lower()
    for claim in FORBIDDEN_CLAIMS:
        if claim.lower() in lowered:
            failures.append(f"golden path contains forbidden claim: {claim}")
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            failures.append(f"golden path contains credential-like text: {pattern.pattern}")

    if text.count("Hermes-through-Node") < 2:
        failures.append("golden path does not repeat the real Hermes-through-Node non-claim")
    if text.count("24-tool") < 2:
        failures.append("golden path does not repeat the fixed 24-tool boundary")
    return failures


def _validate_contract_stage(contract: str) -> list[str]:
    failures: list[str] = []
    lv1_row = next(
        (line for line in contract.splitlines() if line.startswith("| `LV1-001` |")),
        "",
    )
    status_match = re.search(r"\| `(in_progress|complete)` \|", lv1_row)
    if status_match is None:
        return ["LV1-001 must be in_progress or complete in the Local-v1 contract"]

    count_match = re.search(
        r"Critical-path milestones complete: `(\d+)/8`",
        contract,
    )
    next_match = re.search(r"Active next action: `([^`]+)`", contract)
    if count_match is None:
        failures.append("Local-v1 contract is missing the 8-milestone completion count")
        return failures
    if next_match is None:
        failures.append("Local-v1 contract is missing the active next action")
        return failures

    completed_count = int(count_match.group(1))
    active_next = next_match.group(1)
    if status_match.group(1) == "in_progress":
        if completed_count != 1:
            failures.append(
                "LV1-001 in_progress requires exactly one completed Local-v1 milestone"
            )
        if active_next != "LV1-001":
            failures.append("LV1-001 in_progress must remain the active next action")
    else:
        if completed_count < 2:
            failures.append(
                "LV1-001 complete requires at least two completed Local-v1 milestones"
            )
        if active_next == "LV1-001":
            failures.append("LV1-001 complete cannot remain the active next action")
    return failures


def _validate_evidence_source_bindings(
    *,
    demo_flow: str,
    hermes_checker: str,
    node_checker: str,
    node_release_checker: str,
    mission_checker: str,
) -> list[str]:
    failures: list[str] = []
    demo_markers = (
        'adapter.call_tool("fs.read"',
        'api.post("/policy/preview"',
        'f"/approvals/{approval_id}/approve"',
        'adapter.call_tool("fs.patch.apply", {"approval_id": approval_id})',
        '"- patch_apply_status: `completed`"',
    )
    for marker in demo_markers:
        if marker not in demo_flow:
            failures.append(f"demo-flow source no longer establishes documented behavior: {marker}")

    current_candidate_marker = "candidate_commit_matches_current"
    if current_candidate_marker in hermes_checker:
        failures.append("Hermes checker provenance changed; golden-path legacy claim is stale")
    if current_candidate_marker in node_checker:
        failures.append("Node checker provenance changed; golden-path legacy claim is stale")
    release_markers = (
        '"artifacts_bind_exact_current_commit"',
        'current_artifact.get("source_commit")',
        'rollback_artifact.get("source_commit")',
        'current_artifact.get("source_dirty") is False',
        'rollback_artifact.get("source_dirty") is False',
        '["git", "rev-parse", "HEAD"]',
    )
    for marker in release_markers:
        if marker not in node_release_checker:
            failures.append(
                "Node release-artifact checker no longer establishes its documented partial "
                f"commit binding: {marker}"
            )
    for marker in (
        "candidate_and_current_tree_clean",
        "current_worktree_clean",
        '["git", "status"',
        "_git_status(",
    ):
        if marker in node_release_checker:
            failures.append(
                "Node release-artifact checker now inspects current worktree cleanliness; "
                f"golden-path partial-binding claim is stale: {marker}"
            )
    for marker in (
        current_candidate_marker,
        "candidate_and_current_tree_clean",
        'current_commit = _git(repo_root, "rev-parse", "HEAD")',
    ):
        if marker not in mission_checker:
            failures.append(
                f"MCC-006 checker no longer establishes exact-current-candidate binding: {marker}"
            )
    return failures


def _validate_local_links(repo_root: Path, text: str) -> list[str]:
    failures: list[str] = []
    source_dir = repo_root / GOLDEN_PATH_REL.parent
    for raw_target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
        target = raw_target.split("#", 1)[0]
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        resolved = (source_dir / target).resolve()
        try:
            resolved.relative_to(repo_root.resolve())
        except ValueError:
            failures.append(f"golden-path link escapes the repository: {raw_target}")
            continue
        if not resolved.is_file():
            failures.append(f"golden-path link target is missing: {raw_target}")
    return failures


def _read(path: Path, failures: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        failures.append(f"unable to read {path}: {exc}")
        return ""


def _read_json(path: Path, failures: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        failures.append(f"unable to read JSON {path}: {exc}")
        return {}
    if not isinstance(payload, dict):
        failures.append(f"JSON root must be an object: {path}")
        return {}
    return payload


def _target_body(makefile: str, target: str) -> str:
    match = re.search(
        rf"(?ms)^{re.escape(target)}(?:\s[^:]*)?:[^\n]*\n(?P<body>(?:\t[^\n]*\n|[ \t]*\n)*)",
        makefile,
    )
    return match.group("body") if match else ""


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Local v1.0 golden path check",
        f"valid: {str(report['valid']).lower()}",
        f"golden_path: {report['golden_path']}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        "two_leg_path: true",
        "real_hermes_through_node_claimed: false",
        "mcc_007_implementation_authorized: false",
        "runtime_authority_granted: false",
        "release_authority_granted: false",
        "uat_complete: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

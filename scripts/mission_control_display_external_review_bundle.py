"""Build a reviewer-friendly ERG-002 Mission Control display launch bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    enterprise_external_review_queue_check,
    mission_control_display_disposition_closure_check,
    mission_control_display_disposition_packet,
    mission_control_display_external_response_intake_check,
    mission_control_display_response_dry_run,
    mission_control_display_review_packet,
    mission_control_handoff_reference_validator,
    mission_control_integration_readiness_packet,
)

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/mission-control-display-external-review")
HASH_MANIFEST = "mission-control-display-external-review-artifact-hashes.json"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
ARTIFACTS = [
    "00_MISSION_CONTROL_DISPLAY_EXTERNAL_REVIEW_INDEX.md",
    "01_MISSION_CONTROL_DISPLAY_EXTERNAL_REVIEW_PROMPT.md",
    "02_MISSION_CONTROL_DISPLAY_REVIEW_PACKET.md",
    "03_MISSION_CONTROL_DISPLAY_DISPOSITION_PACKET.md",
    "04_MISSION_CONTROL_INTEGRATION_READINESS_PACKET.md",
    "05_MISSION_CONTROL_CONTRACTS_AND_HANDOFFS.md",
    "06_MISSION_CONTROL_RESPONSE_CLOSURE_DRY_RUN.md",
    "07_MISSION_CONTROL_REPRODUCTION_QUEUE_STATUS.md",
    "08_MISSION_CONTROL_DISPLAY_COMMAND_EVIDENCE.md",
    "09_MISSION_CONTROL_REFERENCE_VALIDATOR.md",
]


class MissionControlDisplayExternalReviewBundleError(RuntimeError):
    """Raised when the launch bundle cannot be built."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--skip-commands", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    try:
        if args.check:
            report = build_check_report(Path.cwd().resolve())
            print(render_check_report(report))
            return 0 if report["valid"] else 1
        output_dir = build_bundle(
            repo_root=Path.cwd().resolve(),
            output_dir=args.output_dir,
            allow_dirty=args.allow_dirty,
            run_commands=not args.skip_commands,
        )
    except MissionControlDisplayExternalReviewBundleError as exc:
        print(f"Mission Control display external-review bundle failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built Mission Control display external-review bundle at {output_dir}")
    return 0


def build_check_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_docs = _read(repo_root / "scripts/review_docs.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    runway = _read(repo_root / "docs/codex/enterprise-readiness-runway.md")
    gap_matrix = _read(repo_root / "docs/codex/enterprise-readiness-gap-matrix.md")
    queue = _read(repo_root / "docs/codex/enterprise-external-review-queue.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "mission-control-display-external-review"
        try:
            build_bundle(
                repo_root=repo_root,
                output_dir=output_dir,
                allow_dirty=True,
                run_commands=False,
            )
        except MissionControlDisplayExternalReviewBundleError as exc:
            failures.append(str(exc))
            artifact_names: set[str] = set()
            hashes: dict[str, Any] = {"artifacts": []}
            contents: dict[str, str] = {}
        else:
            artifact_names = {path.name for path in output_dir.iterdir()}
            hashes = json.loads((output_dir / HASH_MANIFEST).read_text(encoding="utf-8"))
            contents = {
                name: (output_dir / name).read_text(encoding="utf-8") for name in ARTIFACTS
            }

    expected = set(ARTIFACTS) | {HASH_MANIFEST}
    missing = expected - artifact_names
    if missing:
        failures.append("external-review bundle missing artifacts: " + ", ".join(sorted(missing)))
    hashed = {entry["path"] for entry in hashes.get("artifacts", [])}
    if HASH_MANIFEST in hashed:
        failures.append("hash manifest must not hash itself")
    if set(ARTIFACTS) - hashed:
        failures.append("artifact hashes do not cover generated markdown files")

    prompt = contents.get("01_MISSION_CONTROL_DISPLAY_EXTERNAL_REVIEW_PROMPT.md", "")
    index = contents.get("00_MISSION_CONTROL_DISPLAY_EXTERNAL_REVIEW_INDEX.md", "")
    evidence = contents.get("08_MISSION_CONTROL_DISPLAY_COMMAND_EVIDENCE.md", "")
    validator = contents.get("09_MISSION_CONTROL_REFERENCE_VALIDATOR.md", "")
    response = contents.get("06_MISSION_CONTROL_RESPONSE_CLOSURE_DRY_RUN.md", "")
    reproduction = contents.get("07_MISSION_CONTROL_REPRODUCTION_QUEUE_STATUS.md", "")

    for phrase in [
        "Finding namespace: `EXT-MC-DISPLAY-###`",
        "Can `ERG-002` continue Mission Control-side display/import planning",
        "Do not approve Mission Control runtime importer behavior",
        "Mission Control execution authority",
    ]:
        if phrase not in prompt:
            failures.append(f"external-review prompt is missing phrase: {phrase}")
    for phrase in [
        "Tool count remains `24`",
        "What This Bundle Does Not Prove",
        "does not close `ERG-002`",
        "approve Mission Control runtime importer behavior",
    ]:
        if phrase not in index:
            failures.append(f"external-review index is missing phrase: {phrase}")
    for phrase in [
        "mission-control-display-external-response-intake.md",
        "mission-control-display-disposition-closure-gate.md",
        "mission-control-display-response-dry-run.md",
    ]:
        if phrase not in response:
            failures.append(f"response/closure/dry-run bundle is missing phrase: {phrase}")
    for phrase in [
        "enterprise-external-review-queue.md",
        "mission-control-side-handoff-plan.md",
        "mission-control-integration-implementation-ticket.md",
    ]:
        if phrase not in reproduction:
            failures.append(f"reproduction/queue bundle is missing phrase: {phrase}")
    for phrase in [
        "Mission Control Handoff Reference Validator",
        "make mission-control-handoff-reference-validator",
        "MC-HANDOFF-VALID-001",
        "MC-HANDOFF-NEG-014",
        "does not approve Mission Control runtime importer behavior",
    ]:
        if phrase not in validator:
            failures.append(f"reference validator bundle is missing phrase: {phrase}")
    for phrase in [
        '"runtime_changes_allowed": false',
        '"mission_control_runtime_allowed": false',
        '"mission_control_execution_authority_allowed": false',
        '"mission_control_policy_authority_allowed": false',
        '"mission_control_approval_authority_allowed": false',
        '"mission_control_audit_authority_allowed": false',
        '"local_model_invocation_allowed": false',
        '"sandbox_orchestration_allowed": false',
        '"trusted_host_promotion_allowed": false',
        '"siem_adapter_allowed": false',
        '"new_power_classes_allowed": false',
        '"closes_erg_002": false',
        '"response_dry_run"',
        '"reference_validator_check"',
        '"valid_fixture_accepted": true',
        '"negative_cases_rejected": 14',
        '"valid_response_accepts": true',
    ]:
        if phrase not in evidence:
            failures.append(f"command evidence is missing phrase: {phrase}")

    target = "mission-control-display-external-review-bundle"
    check_target = f"{target}-check"
    for make_target in [f"{target}:", f"{check_target}:"]:
        if make_target not in makefile:
            failures.append(f"Make target is missing: {make_target.rstrip(':')}")
    if check_target not in release_check_body and f"release-check: {check_target}" not in makefile:
        failures.append(f"{check_target} missing from release-check")
    if f"$(MAKE) {target}" not in review_candidate_body:
        failures.append(f"{target} missing from review-candidate")
    if check_target not in release_guardrails:
        failures.append(f"release guardrails do not require {check_target}")
    if f"$(MAKE) {target}" not in release_guardrails:
        failures.append(f"release guardrails do not require review-candidate {target}")
    doc_rel = "docs/codex/mission-control-display-external-review-bundle.md"
    if doc_rel not in docs_site:
        failures.append("external-review bundle doc is missing from docs-site inputs")
    if doc_rel not in review_docs:
        failures.append("external-review bundle doc is missing from review docs")
    if "Mission Control Display External Review Bundle" not in review_index:
        failures.append("review-docs index is missing external-review bundle entry")
    if f"make {target}" not in readme:
        failures.append("README is missing external-review bundle command")
    for text, source in [
        (readme, "README"),
        (runway, "enterprise runway"),
        (gap_matrix, "enterprise gap matrix"),
        (queue, "enterprise external-review queue"),
    ]:
        if "mission-control-display-external-review-bundle" not in text:
            failures.append(f"{source} is missing external-review bundle pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "output_dir": str(DEFAULT_OUTPUT_DIR),
        "artifact_count": len(expected),
        "tool_count": 24,
        "erg_002_status": "planning_only",
        "recommended_next_review": "ERG-002",
        "runtime_changes_allowed": False,
        "mission_control_planning_allowed": True,
        "mission_control_runtime_allowed": False,
        "mission_control_execution_authority_allowed": False,
        "mission_control_policy_authority_allowed": False,
        "mission_control_approval_authority_allowed": False,
        "mission_control_audit_authority_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
        "closes_erg_002": False,
    }


def build_bundle(
    *,
    repo_root: Path,
    output_dir: Path,
    allow_dirty: bool = False,
    run_commands: bool = True,
) -> Path:
    _require_project_root(repo_root)
    commit = _git(repo_root, ["rev-parse", "HEAD"])
    dirty = bool(_git(repo_root, ["status", "--short"]))
    if dirty and not allow_dirty:
        raise MissionControlDisplayExternalReviewBundleError(
            "working tree is dirty; commit before external-review bundle handoff"
        )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        review_dir = tmp_root / "display-review"
        disposition_dir = tmp_root / "disposition"
        readiness_dir = tmp_root / "readiness"
        mission_control_display_review_packet.build_packet(
            repo_root=repo_root,
            output_dir=review_dir,
            allow_dirty=True,
            run_commands=run_commands,
        )
        mission_control_display_disposition_packet.build_packet(
            repo_root=repo_root,
            output_dir=disposition_dir,
            allow_dirty=True,
            run_commands=run_commands,
        )
        mission_control_integration_readiness_packet.build_packet(
            repo_root=repo_root,
            output_dir=readiness_dir,
            allow_dirty=True,
            run_commands=run_commands,
        )
        command_reports = _build_command_reports(repo_root, run_commands=run_commands)

        files = {
            "00_MISSION_CONTROL_DISPLAY_EXTERNAL_REVIEW_INDEX.md": _index(commit, dirty),
            "01_MISSION_CONTROL_DISPLAY_EXTERNAL_REVIEW_PROMPT.md": _prompt(commit),
            "02_MISSION_CONTROL_DISPLAY_REVIEW_PACKET.md": _packet_bundle(
                "Display Review Packet Contents", review_dir
            ),
            "03_MISSION_CONTROL_DISPLAY_DISPOSITION_PACKET.md": _packet_bundle(
                "Disposition Packet Contents", disposition_dir
            ),
            "04_MISSION_CONTROL_INTEGRATION_READINESS_PACKET.md": _packet_bundle(
                "Integration Readiness Packet Contents", readiness_dir
            ),
            "05_MISSION_CONTROL_CONTRACTS_AND_HANDOFFS.md": _docs_bundle(
                "Contracts And Handoffs",
                repo_root,
                [
                    "docs/codex/mission-control-display-integration-proposal.md",
                    "docs/codex/mission-control-display-importer-plan.md",
                    "docs/codex/mission-control-side-handoff-plan.md",
                    "docs/codex/mission-control-integration-implementation-ticket.md",
                    "docs/codex/mission-control-handoff-schema-contract.md",
                    "docs/codex/mission-control-handoff-negative-fixtures.md",
                    "docs/codex/hello-world-mission-control-handoff.md",
                ],
            ),
            "06_MISSION_CONTROL_RESPONSE_CLOSURE_DRY_RUN.md": _docs_bundle(
                "Response Intake, Closure Gate, And Dry Run",
                repo_root,
                [
                    "docs/codex/mission-control-display-external-response-intake.md",
                    "docs/codex/mission-control-display-disposition-closure-gate.md",
                    "docs/codex/mission-control-display-response-dry-run.md",
                ],
            ),
            "07_MISSION_CONTROL_REPRODUCTION_QUEUE_STATUS.md": _docs_bundle(
                "Reproduction And Queue Status",
                repo_root,
                [
                    "docs/codex/mission-control-side-handoff-plan.md",
                    "docs/codex/mission-control-integration-implementation-ticket.md",
                    "docs/codex/enterprise-external-review-queue.md",
                    "docs/codex/enterprise-readiness-gap-matrix.md",
                    "docs/codex/post-rc-decision-register.md",
                ],
            ),
            "08_MISSION_CONTROL_DISPLAY_COMMAND_EVIDENCE.md": _command_evidence(
                command_reports
            ),
            "09_MISSION_CONTROL_REFERENCE_VALIDATOR.md": _docs_bundle(
                "Reference Validator",
                repo_root,
                [
                    "docs/codex/mission-control-handoff-reference-validator.md",
                ],
            ),
        }

    for name, content in files.items():
        (output_dir / name).write_text(content, encoding="utf-8")
    _write_hashes(output_dir)
    return output_dir


def _index(commit: str, dirty: bool) -> str:
    return f"""# Mission Control Display External Review Bundle

Status: reviewer launch bundle for `ERG-002`.

Reviewed commit: `{commit}`
Dirty state when generated: `{str(dirty).lower()}`

Tool count remains `24`.

Current selected capability: `not selected`.

Current `ERG-002` status before reviewer disposition: `planning_only`.

Recommended next review: `ERG-002` Mission Control display/importer planning disposition.

## Reading Order

1. `01_MISSION_CONTROL_DISPLAY_EXTERNAL_REVIEW_PROMPT.md`
2. `02_MISSION_CONTROL_DISPLAY_REVIEW_PACKET.md`
3. `03_MISSION_CONTROL_DISPLAY_DISPOSITION_PACKET.md`
4. `04_MISSION_CONTROL_INTEGRATION_READINESS_PACKET.md`
5. `05_MISSION_CONTROL_CONTRACTS_AND_HANDOFFS.md`
6. `06_MISSION_CONTROL_RESPONSE_CLOSURE_DRY_RUN.md`
7. `07_MISSION_CONTROL_REPRODUCTION_QUEUE_STATUS.md`
8. `08_MISSION_CONTROL_DISPLAY_COMMAND_EVIDENCE.md`
9. `09_MISSION_CONTROL_REFERENCE_VALIDATOR.md`
10. `mission-control-display-external-review-artifact-hashes.json`

## What This Bundle Does Not Prove

This bundle does not prove that external review has happened, does not close `ERG-002`, and does
not approve Mission Control runtime importer behavior, API callbacks, MCP transports, Mission
Control execution authority, policy authority, approval authority, audit authority, local model
invocation, VM/container lifecycle management, sandbox orchestration, trusted-host promotion, SIEM
adapters, production identity, runtime Postgres, hosted telemetry, remote MCP, compliance
automation, public/security-product positioning, or any new governed tool power.

This bundle does not approve Mission Control runtime importer behavior.
"""


def _prompt(commit: str) -> str:
    return f"""# Mission Control Display External Review Prompt

You are reviewing Ithildin as an external/source reviewer for `ERG-002` only: the Mission Control
display/importer planning lane.

Reviewed commit: `{commit}`

Finding namespace: `EXT-MC-DISPLAY-###`

## Scope

Review the attached display review packet, disposition packet, integration readiness packet,
contracts, handoff docs, negative fixtures, response intake, closure gate, dry-run evidence, queue
status, and command evidence.

Please answer:

1. Did you inspect the display/importer review packet and the docs/source pointers it names?
2. Is the Mission Control handoff schema complete enough for display-only import planning?
3. Are stale/mismatched packet fixtures, unsafe attachment paths, content leaks, and authority
   overclaims covered well enough for the next Mission Control-side planning step?
4. Does every artifact preserve Ithildin as execution, policy, approval, and audit authority?
5. Are there any critical/high findings?
6. Does the response/closure path correctly keep `ERG-002` planning-only until a later committed
   disposition records real source-level evidence?
7. Can `ERG-002` continue Mission Control-side display/import planning while runtime implementation
   remains blocked?

Do not approve Mission Control runtime importer behavior. Do not approve API callbacks. Do not
approve Mission Control execution authority. Do not approve Mission Control policy authority. Do
not approve Mission Control approval authority. Do not approve Mission Control audit authority. Do
not approve local model invocation. Do not approve sandbox orchestration. Do not approve
trusted-host promotion. Do not approve SIEM adapters. Do not approve public/security-product
positioning.

Use this finding namespace for actionable findings: `EXT-MC-DISPLAY-###`.

For each finding, include severity, area, affected files/functions, blocking status, disposition,
and recommended fix.
"""


def _packet_bundle(title: str, packet_dir: Path) -> str:
    parts = [f"# {title}\n"]
    for path in sorted(packet_dir.iterdir()):
        if path.suffix.lower() not in {".md", ".json"}:
            continue
        content = path.read_text(encoding="utf-8")
        parts.append(f"\n## {path.name}\n\n```{_fence_lang(path)}\n{content}\n```\n")
    return "".join(parts)


def _docs_bundle(title: str, repo_root: Path, rel_paths: list[str]) -> str:
    parts = [f"# {title}\n"]
    for rel in rel_paths:
        path = repo_root / rel
        content = path.read_text(encoding="utf-8")
        parts.append(f"\n## {rel}\n\n```{_fence_lang(path)}\n{content}\n```\n")
    return "".join(parts)


def _build_command_reports(repo_root: Path, *, run_commands: bool) -> dict[str, Any]:
    reports: dict[str, Any] = {
        "display_review_packet_check": mission_control_display_review_packet.build_check_report(
            repo_root
        ),
        "disposition_packet_check": mission_control_display_disposition_packet.build_check_report(
            repo_root
        ),
        "integration_readiness_packet_check": (
            mission_control_integration_readiness_packet.build_check_report(repo_root)
        ),
        "external_response_intake_check": (
            mission_control_display_external_response_intake_check.build_report(repo_root)
        ),
        "closure_gate_check": mission_control_display_disposition_closure_check.build_report(
            repo_root
        ),
        "response_dry_run": mission_control_display_response_dry_run.run_dry_run(repo_root),
        "reference_validator_check": mission_control_handoff_reference_validator.build_report(
            repo_root
        ),
        "enterprise_external_review_queue_check": (
            enterprise_external_review_queue_check.build_report(repo_root)
        ),
    }
    reports["shell_commands"] = (
        _run_shell_commands(repo_root)
        if run_commands
        else [{"command": "command execution skipped for fixture/test packet generation"}]
    )
    return reports


def _command_evidence(reports: dict[str, Any]) -> str:
    payload = json.dumps(reports, indent=2, sort_keys=True)
    return f"# Command Evidence\n\n```json\n{payload}\n```\n"


def _run_shell_commands(repo_root: Path) -> list[dict[str, Any]]:
    commands = [
        ["make", "mission-control-display-review-packet-check"],
        ["make", "mission-control-display-disposition-packet-check"],
        ["make", "mission-control-integration-readiness-packet-check"],
        ["make", "mission-control-display-external-response-intake-check"],
        ["make", "mission-control-display-disposition-closure-check"],
        ["make", "mission-control-display-response-dry-run"],
        ["make", "mission-control-handoff-reference-validator"],
        ["make", "enterprise-external-review-queue-check"],
        ["make", "no-new-powers-guardrail"],
        ["make", "tool-surface-invariant-gate"],
    ]
    results: list[dict[str, Any]] = []
    for command in commands:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        results.append(
            {
                "command": " ".join(command),
                "returncode": completed.returncode,
                "stdout_tail": completed.stdout[-4000:],
                "stderr_tail": completed.stderr[-2000:],
            }
        )
        if completed.returncode != 0:
            raise MissionControlDisplayExternalReviewBundleError(
                f"command failed while building bundle: {' '.join(command)}"
            )
    return results


def _write_hashes(output_dir: Path) -> None:
    artifacts = []
    for path in sorted(output_dir.iterdir()):
        if path.name == HASH_MANIFEST:
            continue
        if not path.is_file():
            continue
        data = path.read_bytes()
        artifacts.append(
            {
                "path": path.name,
                "sha256": "sha256:" + hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            }
        )
    (output_dir / HASH_MANIFEST).write_text(
        json.dumps({"artifacts": artifacts}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _require_project_root(repo_root: Path) -> None:
    missing = [str(marker) for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        raise MissionControlDisplayExternalReviewBundleError(
            "not an Ithildin repo root; missing: " + ", ".join(missing)
        )


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _fence_lang(path: Path) -> str:
    return "json" if path.suffix.lower() == ".json" else "markdown"


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Mission Control display external-review bundle check",
        f"valid: {str(report['valid']).lower()}",
        f"output_dir: {report['output_dir']}",
        f"artifact_count: {report['artifact_count']}",
        f"tool_count: {report['tool_count']}",
        f"erg_002_status: {report['erg_002_status']}",
        f"recommended_next_review: {report['recommended_next_review']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "mission_control_planning_allowed: "
        f"{str(report['mission_control_planning_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        "mission_control_execution_authority_allowed: "
        f"{str(report['mission_control_execution_authority_allowed']).lower()}",
        "mission_control_policy_authority_allowed: "
        f"{str(report['mission_control_policy_authority_allowed']).lower()}",
        "mission_control_approval_authority_allowed: "
        f"{str(report['mission_control_approval_authority_allowed']).lower()}",
        "mission_control_audit_authority_allowed: "
        f"{str(report['mission_control_audit_authority_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        "trusted_host_promotion_allowed: "
        f"{str(report['trusted_host_promotion_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"closes_erg_002: {str(report['closes_erg_002']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

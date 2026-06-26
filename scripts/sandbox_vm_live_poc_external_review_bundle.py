"""Build a reviewer-friendly ERG-004 live sandbox/VM POC launch bundle."""

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

from scripts import sandbox_vm_live_poc_decision_packet

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/sandbox-vm-live-poc-external-review")
HASH_MANIFEST = "sandbox-vm-live-poc-external-review-artifact-hashes.json"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
ARTIFACTS = [
    "00_SANDBOX_VM_LIVE_POC_EXTERNAL_REVIEW_INDEX.md",
    "01_SANDBOX_VM_LIVE_POC_EXTERNAL_REVIEW_PROMPT.md",
    "02_SANDBOX_VM_LIVE_POC_DECISION_PACKET.md",
    "03_SANDBOX_VM_LIVE_POC_CONTRACTS_AND_PRECONDITIONS.md",
    "04_SANDBOX_VM_LIVE_POC_RESPONSE_CLOSURE_DRY_RUN.md",
    "05_SANDBOX_VM_LIVE_POC_QUEUE_AND_BOUNDARY_STATUS.md",
    "06_SANDBOX_VM_LIVE_POC_COMMAND_EVIDENCE.md",
]


class SandboxVmLivePocExternalReviewBundleError(RuntimeError):
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
            print(render_report(report))
            return 0 if report["valid"] else 1
        output_dir = build_bundle(
            repo_root=Path.cwd().resolve(),
            output_dir=args.output_dir,
            allow_dirty=args.allow_dirty,
            run_commands=not args.skip_commands,
        )
    except SandboxVmLivePocExternalReviewBundleError as exc:
        print(f"sandbox/VM live POC external-review bundle failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built sandbox/VM live POC external-review bundle at {output_dir}")
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
    register = _read(repo_root / "docs/codex/post-rc-decision-register.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "sandbox-vm-live-poc-external-review"
        try:
            build_bundle(
                repo_root=repo_root,
                output_dir=output_dir,
                allow_dirty=True,
                run_commands=False,
            )
        except SandboxVmLivePocExternalReviewBundleError as exc:
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

    index = contents.get("00_SANDBOX_VM_LIVE_POC_EXTERNAL_REVIEW_INDEX.md", "")
    prompt = contents.get("01_SANDBOX_VM_LIVE_POC_EXTERNAL_REVIEW_PROMPT.md", "")
    packet = contents.get("02_SANDBOX_VM_LIVE_POC_DECISION_PACKET.md", "")
    contracts = contents.get("03_SANDBOX_VM_LIVE_POC_CONTRACTS_AND_PRECONDITIONS.md", "")
    response = contents.get("04_SANDBOX_VM_LIVE_POC_RESPONSE_CLOSURE_DRY_RUN.md", "")
    queue_status = contents.get("05_SANDBOX_VM_LIVE_POC_QUEUE_AND_BOUNDARY_STATUS.md", "")
    evidence = contents.get("06_SANDBOX_VM_LIVE_POC_COMMAND_EVIDENCE.md", "")

    for phrase in [
        "Tool count remains `24`",
        "Current `ERG-004` status remains `blocked`",
        "What This Bundle Does Not Prove",
        "does not close `ERG-004`",
        "does not approve live VM/container inspection",
    ]:
        if phrase not in index:
            failures.append(f"external-review index is missing phrase: {phrase}")
    for phrase in [
        "Finding namespace: `EXT-LIVE-POC-###`",
        "Does the reviewer agree `ERG-004` remains blocked",
        "Do not approve live VM/container inspection",
        "Do not approve local model invocation",
        "Do not approve sandbox orchestration",
    ]:
        if phrase not in prompt:
            failures.append(f"external-review prompt is missing phrase: {phrase}")
    for phrase in [
        "SANDBOX_VM_LIVE_POC_DECISION_PROMPT",
        "What This Packet Does Not Prove",
    ]:
        if phrase not in packet:
            failures.append(f"decision packet bundle is missing phrase: {phrase}")
    for phrase in [
        "sandbox-vm-live-poc-evidence-contract.md",
        "sandbox-vm-live-poc-preconditions-map.md",
        "sandbox-vm-live-poc-preconditions-ready-check.md",
        "enterprise-sandbox-control-plane-readiness.md",
    ]:
        if phrase not in contracts:
            failures.append(f"contracts/preconditions bundle is missing phrase: {phrase}")
    for phrase in [
        "sandbox-vm-live-poc-external-response-intake.md",
        "sandbox-vm-live-poc-decision-closure-gate.md",
        "sandbox-vm-live-poc-response-dry-run.md",
        "sandbox-vm-live-poc-prerequisite-disposition-dry-run.md",
    ]:
        if phrase not in response:
            failures.append(f"response/closure/dry-run bundle is missing phrase: {phrase}")
    for phrase in [
        "enterprise-external-review-queue.md",
        "sandbox-vm-static-preflight-disposition-record-skeleton.md",
        "post-rc-decision-register.md",
    ]:
        if phrase not in queue_status:
            failures.append(f"queue/boundary bundle is missing phrase: {phrase}")
    for phrase in [
        '"runtime_changes_allowed": false',
        '"implementation_planning_allowed": false',
        '"live_vm_inspection_allowed": false',
        '"mission_control_runtime_allowed": false',
        '"local_model_invocation_allowed": false',
        '"sandbox_orchestration_allowed": false',
        '"trusted_host_promotion_allowed": false',
        '"new_power_classes_allowed": false',
        '"erg_004_unblocked": false',
        '"closes_erg_004": false',
        '"erg_003_closed": false',
        '"sandbox-vm-live-poc-preconditions-ready-check"',
        '"ready_for_implementation_planning": false',
        '"response_dry_run"',
        '"valid_response_accepts": true',
    ]:
        if phrase not in evidence:
            failures.append(f"command evidence is missing phrase: {phrase}")

    target = "sandbox-vm-live-poc-external-review-bundle"
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
    doc_rel = "docs/codex/sandbox-vm-live-poc-external-review-bundle.md"
    if doc_rel not in docs_site:
        failures.append("external-review bundle doc is missing from docs-site inputs")
    if doc_rel not in review_docs:
        failures.append("external-review bundle doc is missing from review docs")
    if "Sandbox/VM Live POC External Review Bundle" not in review_index:
        failures.append("review-docs index is missing live POC external-review bundle entry")
    if f"make {target}" not in readme:
        failures.append("README is missing live POC external-review bundle command")
    for text, source in [
        (readme, "README"),
        (runway, "enterprise runway"),
        (gap_matrix, "enterprise gap matrix"),
        (queue, "enterprise external-review queue"),
        (register, "post-RC decision register"),
    ]:
        if "sandbox-vm-live-poc-external-review-bundle" not in text:
            failures.append(f"{source} is missing external-review bundle pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "output_dir": str(DEFAULT_OUTPUT_DIR),
        "artifact_count": len(expected),
        "tool_count": 24,
        "erg_004_status": "blocked",
        "recommended_next_review": "ERG-004",
        "runtime_changes_allowed": False,
        "implementation_planning_allowed": False,
        "live_vm_inspection_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
        "erg_003_closed": False,
        "erg_004_unblocked": False,
        "closes_erg_004": False,
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
        raise SandboxVmLivePocExternalReviewBundleError(
            "working tree is dirty; commit before external-review bundle handoff"
        )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        decision_dir = Path(tmp) / "decision"
        sandbox_vm_live_poc_decision_packet.build_packet(
            repo_root=repo_root,
            output_dir=decision_dir,
            allow_dirty=True,
            run_commands=run_commands,
        )
        command_reports = _build_command_reports(repo_root, run_commands=run_commands)

        files = {
            "00_SANDBOX_VM_LIVE_POC_EXTERNAL_REVIEW_INDEX.md": _index(commit, dirty),
            "01_SANDBOX_VM_LIVE_POC_EXTERNAL_REVIEW_PROMPT.md": _prompt(commit),
            "02_SANDBOX_VM_LIVE_POC_DECISION_PACKET.md": _packet_bundle(
                "Decision Packet Contents", decision_dir
            ),
            "03_SANDBOX_VM_LIVE_POC_CONTRACTS_AND_PRECONDITIONS.md": _docs_bundle(
                "Contracts And Preconditions",
                repo_root,
                [
                    "docs/codex/sandbox-vm-live-poc-decision-intake.md",
                    "docs/codex/sandbox-vm-live-poc-evidence-contract.md",
                    "docs/codex/sandbox-vm-live-poc-preconditions-map.md",
                    "docs/codex/sandbox-vm-live-poc-preconditions-ready-check.md",
                    "docs/codex/enterprise-sandbox-control-plane-readiness.md",
                ],
            ),
            "04_SANDBOX_VM_LIVE_POC_RESPONSE_CLOSURE_DRY_RUN.md": _docs_bundle(
                "Response Intake, Closure Gate, And Dry Runs",
                repo_root,
                [
                    "docs/codex/sandbox-vm-live-poc-external-response-intake.md",
                    "docs/codex/sandbox-vm-live-poc-decision-closure-gate.md",
                    "docs/codex/sandbox-vm-live-poc-decision-record-skeleton.md",
                    "docs/codex/sandbox-vm-live-poc-response-dry-run.md",
                    "docs/codex/sandbox-vm-live-poc-prerequisite-disposition-dry-run.md",
                ],
            ),
            "05_SANDBOX_VM_LIVE_POC_QUEUE_AND_BOUNDARY_STATUS.md": _docs_bundle(
                "Queue, Prerequisite, And Boundary Status",
                repo_root,
                [
                    "docs/codex/enterprise-external-review-queue.md",
                    "docs/codex/enterprise-readiness-gap-matrix.md",
                    "docs/codex/enterprise-readiness-runway.md",
                    "docs/codex/post-rc-decision-register.md",
                    "docs/codex/sandbox-vm-static-preflight-disposition-record-skeleton.md",
                    "docs/codex/sandbox-vm-static-preflight-disposition-closure-gate.md",
                ],
            ),
            "06_SANDBOX_VM_LIVE_POC_COMMAND_EVIDENCE.md": _command_evidence(
                commit, dirty, command_reports
            ),
        }

        for name, content in files.items():
            (output_dir / name).write_text(content, encoding="utf-8")

    _write_hashes(output_dir)
    return output_dir


def _index(commit: str, dirty: bool) -> str:
    return f"""# Sandbox/VM Live POC External Review Bundle

Reviewed commit: `{commit}`

Dirty at generation: `{str(dirty).lower()}`

Tool count remains `24`.

Current `ERG-004` status remains `blocked`.

This bundle packages the blocked live sandbox/VM worker proof-of-concept decision lane for
external/source review. It exists so a reviewer can inspect the decision packet, contracts,
preconditions, response path, dry-run evidence, queue status, and command evidence in one place.

## Artifacts

{_artifact_list()}

## What This Bundle Does Not Prove

This bundle does not prove external review happened, does not close `ERG-004`, does not unblock
`ERG-004`, and does not approve live VM/container inspection, VM/container lifecycle management,
sandbox orchestration, Mission Control runtime behavior, local model invocation, trusted-host
promotion, SIEM adapter behavior, new governed tool powers, production identity, runtime Postgres,
hosted telemetry, remote MCP, compliance automation, or public/security-product positioning.
"""


def _prompt(commit: str) -> str:
    return f"""# Sandbox/VM Live POC External Review Prompt

You are reviewing Ithildin as an external/source reviewer for the blocked `ERG-004` live
sandbox/VM worker proof-of-concept lane only.

Reviewed commit: `{commit}`

Finding namespace: `EXT-LIVE-POC-###`

## Scope

Please inspect the attached decision packet, evidence contract, preconditions map, response intake,
closure gate, prerequisite dry run, queue status, and command evidence.

Please answer:

1. Does the reviewer agree `ERG-004` remains blocked unless a favorable `ERG-003` static preflight
   disposition exists?
2. Is the evidence contract complete enough for a later implementation-planning-only decision
   record, if and only if prerequisites are satisfied?
3. Are the role boundaries clear between Ithildin, Mission Control, the operator-managed VM, and
   any local model worker?
4. Are the stop conditions strict enough to prevent accidental runtime authorization?
5. What findings, if any, must be fixed before this lane can continue design-only planning?

Do not approve live VM/container inspection. Do not approve local model invocation. Do not approve
sandbox orchestration. Do not approve Mission Control runtime behavior. Do not approve trusted-host
promotion. Do not approve new governed tool powers, shell, Docker, Kubernetes, browser automation,
arbitrary HTTP, broad writes, production identity, runtime Postgres, hosted telemetry, remote MCP,
SIEM adapter behavior, compliance automation, or public/security-product positioning.
Do not approve sandbox orchestration in any form.

Use this table shape for findings:

| Finding ID | Severity | Area | Affected files/functions |
| --- | --- | --- | --- |
| EXT-LIVE-POC-### | critical/high/medium/low/informational | sandbox-vm-live-poc | path/function |

| Blocking status | Disposition | Recommended fix |
| --- | --- | --- |
| blocking/should-fix/later/advisory | open | fix summary |
"""


def _packet_bundle(title: str, directory: Path) -> str:
    lines = [f"# {title}", ""]
    for path in sorted(directory.iterdir()):
        if path.name.endswith(".json"):
            continue
        lines.extend([f"## {path.name}", "", path.read_text(encoding="utf-8"), ""])
    return "\n".join(lines)


def _docs_bundle(title: str, repo_root: Path, docs: list[str]) -> str:
    lines = [f"# {title}", ""]
    for rel in docs:
        path = repo_root / rel
        if not path.exists():
            raise SandboxVmLivePocExternalReviewBundleError(f"missing bundled doc: {rel}")
        lines.extend([f"## {rel}", "", path.read_text(encoding="utf-8"), ""])
    return "\n".join(lines)


def _build_command_reports(repo_root: Path, *, run_commands: bool) -> list[dict[str, Any]]:
    commands = [
        ["make", "sandbox-vm-live-poc-decision-packet-check"],
        ["make", "sandbox-vm-live-poc-preconditions-ready-check"],
        ["make", "sandbox-vm-live-poc-decision-closure-check"],
        ["make", "sandbox-vm-live-poc-response-dry-run"],
        ["make", "sandbox-vm-live-poc-prerequisite-disposition-dry-run"],
        ["make", "sandbox-vm-static-preflight-disposition-closure-check"],
        ["make", "enterprise-external-review-queue-check"],
        ["make", "no-new-powers-guardrail"],
        ["make", "tool-surface-invariant-gate"],
    ]
    reports: list[dict[str, Any]] = []
    for command in commands:
        if run_commands:
            result = subprocess.run(
                command,
                cwd=repo_root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            reports.append(
                {
                    "command": " ".join(command),
                    "returncode": result.returncode,
                    "output": result.stdout,
                }
            )
            if result.returncode != 0:
                raise SandboxVmLivePocExternalReviewBundleError(
                    f"command failed: {' '.join(command)}"
                )
        else:
            reports.append(
                {
                    "command": " ".join(command),
                    "returncode": 0,
                    "output": "Command execution skipped for packet check mode.",
                }
            )
    return reports


def _command_evidence(commit: str, dirty: bool, reports: list[dict[str, Any]]) -> str:
    evidence = {
        "schema_version": "1",
        "commit": commit,
        "dirty": dirty,
        "boundary": {
            "runtime_changes_allowed": False,
            "implementation_planning_allowed": False,
            "ready_for_implementation_planning": False,
            "live_vm_inspection_allowed": False,
            "mission_control_runtime_allowed": False,
            "local_model_invocation_allowed": False,
            "sandbox_orchestration_allowed": False,
            "trusted_host_promotion_allowed": False,
            "siem_adapter_allowed": False,
            "new_power_classes_allowed": False,
            "erg_003_closed": False,
            "erg_004_unblocked": False,
            "closes_erg_004": False,
        },
        "preconditions_ready_check": "sandbox-vm-live-poc-preconditions-ready-check",
        "response_dry_run": {
            "valid_response_accepts": True,
            "unfavorable_response_rejects_closure": True,
            "temporary_fixtures_only": True,
        },
        "commands": reports,
    }
    return "# Sandbox/VM Live POC Command Evidence\n\n```json\n" + json.dumps(
        evidence, indent=2, sort_keys=True
    ) + "\n```\n"


def _write_hashes(output_dir: Path) -> None:
    artifacts: list[dict[str, Any]] = []
    for name in ARTIFACTS:
        path = output_dir / name
        data = path.read_bytes()
        artifacts.append(
            {
                "path": name,
                "bytes": len(data),
                "sha256": "sha256:" + hashlib.sha256(data).hexdigest(),
            }
        )
    (output_dir / HASH_MANIFEST).write_text(
        json.dumps({"schema_version": "1", "artifacts": artifacts}, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


def _artifact_list() -> str:
    lines = []
    for index, name in enumerate(ARTIFACTS + [HASH_MANIFEST], start=1):
        lines.append(f"{index}. `{name}`")
    return "\n".join(lines)


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


def _require_project_root(repo_root: Path) -> None:
    missing = [str(marker) for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        raise SandboxVmLivePocExternalReviewBundleError(
            "not an Ithildin project root; missing " + ", ".join(missing)
        )


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM live POC external-review bundle check",
        f"valid: {str(report['valid']).lower()}",
        f"output_dir: {report['output_dir']}",
        f"artifact_count: {report['artifact_count']}",
        f"tool_count: {report['tool_count']}",
        f"erg_004_status: {report['erg_004_status']}",
        f"recommended_next_review: {report['recommended_next_review']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "implementation_planning_allowed: "
        f"{str(report['implementation_planning_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"erg_003_closed: {str(report['erg_003_closed']).lower()}",
        f"erg_004_unblocked: {str(report['erg_004_unblocked']).lower()}",
        f"closes_erg_004: {str(report['closes_erg_004']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

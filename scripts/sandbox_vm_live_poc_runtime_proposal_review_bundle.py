"""Build the ERG-004 runtime-proposal external-review bundle."""

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

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/sandbox-vm-live-poc-runtime-proposal-review")
HASH_MANIFEST = "sandbox-vm-live-poc-runtime-proposal-review-artifact-hashes.json"
DOC_REL = "docs/codex/sandbox-vm-live-poc-runtime-proposal-review-bundle.md"
DOC_TITLE = "Sandbox/VM Live POC Runtime Proposal Review Bundle"
TARGET = "sandbox-vm-live-poc-runtime-proposal-review-bundle"
CHECK_TARGET = "sandbox-vm-live-poc-runtime-proposal-review-bundle-check"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
ARTIFACTS = [
    "00_SANDBOX_VM_LIVE_POC_RUNTIME_PROPOSAL_REVIEW_INDEX.md",
    "01_SANDBOX_VM_LIVE_POC_RUNTIME_PROPOSAL_REVIEW_PROMPT.md",
    "02_ERG004_RUNTIME_PROPOSAL.md",
    "03_ERG004_PLANNING_AND_DECISION_CONTEXT.md",
    "04_ERG004_CONTRACTS_AND_NEGATIVE_PLAN.md",
    "05_ERG004_RUNTIME_PROPOSAL_COMMAND_EVIDENCE.md",
]
COMMANDS = [
    (
        "sandbox-vm-live-poc-runtime-proposal-check",
        ["make", "sandbox-vm-live-poc-runtime-proposal-check"],
    ),
    (
        "sandbox-vm-live-poc-implementation-plan-check",
        ["make", "sandbox-vm-live-poc-implementation-plan-check"],
    ),
    ("enterprise-active-route-clarity", ["make", "enterprise-active-route-clarity"]),
]
FORBIDDEN_APPROVAL_PHRASES = [
    "runtime implementation is approved",
    "live VM/container inspection is approved",
    "VM/container lifecycle management is approved",
    "sandbox orchestration is approved",
    "Mission Control runtime behavior is approved",
    "local model invocation is approved",
    "trusted-host promotion is approved",
    "new governed tool powers are approved",
    "public security product approved",
]


class SandboxVmLivePocRuntimeProposalReviewBundleError(RuntimeError):
    """Raised when the runtime-proposal bundle cannot be built."""


def build_bundle(
    *,
    repo_root: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    allow_dirty: bool = False,
    run_commands: bool = True,
) -> Path:
    _require_project_root(repo_root)
    commit = _git(repo_root, ["rev-parse", "HEAD"])
    dirty = bool(_git(repo_root, ["status", "--short"]))
    if dirty and not allow_dirty:
        raise SandboxVmLivePocRuntimeProposalReviewBundleError(
            "working tree is dirty; commit before ERG-004 runtime-proposal review handoff"
        )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    command_reports = _build_command_reports(repo_root, run_commands=run_commands)
    files = {
        "00_SANDBOX_VM_LIVE_POC_RUNTIME_PROPOSAL_REVIEW_INDEX.md": _index(commit, dirty),
        "01_SANDBOX_VM_LIVE_POC_RUNTIME_PROPOSAL_REVIEW_PROMPT.md": _prompt(commit),
        "02_ERG004_RUNTIME_PROPOSAL.md": _docs_bundle(
            "ERG-004 Runtime Proposal",
            repo_root,
            ["docs/codex/sandbox-vm-live-poc-runtime-proposal.md"],
        ),
        "03_ERG004_PLANNING_AND_DECISION_CONTEXT.md": _docs_bundle(
            "ERG-004 Planning And Decision Context",
            repo_root,
            [
                "docs/codex/sandbox-vm-live-poc-decision-record.md",
                "docs/codex/sandbox-vm-live-poc-implementation-plan.md",
                "docs/codex/enterprise-active-route-clarity.md",
            ],
        ),
        "04_ERG004_CONTRACTS_AND_NEGATIVE_PLAN.md": _docs_bundle(
            "ERG-004 Historical Contracts And Negative Plan",
            repo_root,
            [
                "docs/codex/sandbox-vm-live-poc-evidence-contract.md",
                "docs/codex/sandbox-vm-live-poc-preconditions-map.md",
                "docs/codex/sandbox-vm-live-poc-preconditions-ready-check.md",
                "docs/codex/enterprise-sandbox-control-plane-readiness.md",
            ],
        )
        + "\n"
        + _negative_plan_summary(),
        "05_ERG004_RUNTIME_PROPOSAL_COMMAND_EVIDENCE.md": _command_evidence(
            commit, dirty, command_reports
        ),
    }
    for name, content in files.items():
        _write(output_dir / name, content)
    _write_hashes(output_dir)
    return output_dir


def build_check_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_docs = _read(repo_root / "scripts/review_docs.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "runtime-proposal-review"
        try:
            build_bundle(
                repo_root=repo_root,
                output_dir=output_dir,
                allow_dirty=True,
                run_commands=False,
            )
        except SandboxVmLivePocRuntimeProposalReviewBundleError as exc:
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
        failures.append(
            "runtime-proposal review bundle missing artifacts: " + ", ".join(sorted(missing))
        )
    hashed = {entry.get("path") for entry in hashes.get("artifacts", [])}
    if set(ARTIFACTS) - hashed:
        failures.append("artifact hashes do not cover generated markdown files")
    if HASH_MANIFEST in hashed:
        failures.append("hash manifest must not hash itself")

    index = contents.get("00_SANDBOX_VM_LIVE_POC_RUNTIME_PROPOSAL_REVIEW_INDEX.md", "")
    prompt = contents.get("01_SANDBOX_VM_LIVE_POC_RUNTIME_PROPOSAL_REVIEW_PROMPT.md", "")
    proposal = contents.get("02_ERG004_RUNTIME_PROPOSAL.md", "")
    context = contents.get("03_ERG004_PLANNING_AND_DECISION_CONTEXT.md", "")
    contracts = contents.get("04_ERG004_CONTRACTS_AND_NEGATIVE_PLAN.md", "")
    evidence = contents.get("05_ERG004_RUNTIME_PROPOSAL_COMMAND_EVIDENCE.md", "")

    for phrase in [
        "Tool count remains `24`",
        "Current `ERG-004` status: `ready_for_runtime_proposal_review`",
        "What This Bundle Does Not Prove",
    ]:
        if phrase not in index:
            failures.append(f"runtime-proposal index is missing phrase: {phrase}")
    for phrase in [
        "Finding namespace: `EXT-LIVE-RUNTIME-###`",
        "runtime implementation ticket to be drafted",
        "Do not approve runtime implementation",
        "Do not approve live VM/container inspection",
        "Do not approve local model invocation",
    ]:
        if phrase not in prompt:
            failures.append(f"runtime-proposal prompt is missing phrase: {phrase}")
    for phrase in [
        "sandbox-vm-live-poc-runtime-proposal.md",
        "ready_for_runtime_proposal_review",
        "descriptor_source: operator_supplied",
        "ithildin_live_inspection_performed: false",
    ]:
        if phrase not in proposal:
            failures.append(f"runtime proposal bundle is missing phrase: {phrase}")
    for phrase in [
        "sandbox-vm-live-poc-decision-record.md",
        "sandbox-vm-live-poc-implementation-plan.md",
        "enterprise-active-route-clarity.md",
        "ready_for_implementation_planning_only",
    ]:
        if phrase not in context:
            failures.append(f"planning context bundle is missing phrase: {phrase}")
    for phrase in [
        "ERG-004 Historical Contracts And Negative Plan",
        "Current packet status: `ready_for_runtime_proposal_review`.",
        "sandbox-vm-live-poc-evidence-contract.md",
        "sandbox-vm-live-poc-preconditions-map.md",
        "attempted live VM/container",
        "raw secret, prompt, model response",
    ]:
        if phrase not in contracts:
            failures.append(f"contracts/negative plan bundle is missing phrase: {phrase}")
    for phrase in [
        '"sandbox-vm-live-poc-runtime-proposal-check"',
        '"runtime_changes_allowed": false',
        '"runtime_implementation_allowed": false',
        '"runtime_ticket_allowed": false',
        '"live_vm_inspection_allowed": false',
        '"sandbox_orchestration_allowed": false',
        '"new_power_classes_allowed": false',
    ]:
        if phrase not in evidence:
            failures.append(f"command evidence is missing phrase: {phrase}")

    generated_text = "\n".join(contents.values())
    for phrase in FORBIDDEN_APPROVAL_PHRASES:
        if phrase.lower() in generated_text.lower():
            failures.append(f"runtime-proposal bundle contains forbidden phrase: {phrase}")

    for make_target in [f"{TARGET}:", f"{CHECK_TARGET}:"]:
        if make_target not in makefile:
            failures.append(f"Make target is missing: {make_target.rstrip(':')}")
    if CHECK_TARGET not in release_check_body and f"release-check: {CHECK_TARGET}" not in makefile:
        failures.append(f"{CHECK_TARGET} missing from release-check")
    if f"$(MAKE) {TARGET}" not in review_candidate_body:
        failures.append(f"{TARGET} missing from review-candidate")
    if CHECK_TARGET not in release_guardrails:
        failures.append(f"release guardrails do not require {CHECK_TARGET}")
    if f"$(MAKE) {TARGET}" not in release_guardrails:
        failures.append(f"release guardrails do not require review-candidate {TARGET}")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing runtime-proposal review bundle command")
    if DOC_REL not in readme:
        failures.append("README is missing runtime-proposal review bundle doc")
    if DOC_REL not in docs_site:
        failures.append("runtime-proposal review bundle doc is missing from docs-site inputs")
    if DOC_REL not in review_docs:
        failures.append("runtime-proposal review bundle doc is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing runtime-proposal review bundle entry")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "output_dir": str(DEFAULT_OUTPUT_DIR),
        "artifact_count": len(expected),
        "tool_count": 24,
        "erg_004_status": "ready_for_runtime_proposal_review",
        "finding_namespace": "EXT-LIVE-RUNTIME-###",
        "vm_first": True,
        "operator_managed": True,
        "container_profiles_deferred": True,
        "runtime_proposal_allowed": True,
        "runtime_changes_allowed": False,
        "runtime_implementation_allowed": False,
        "runtime_ticket_allowed": False,
        "live_vm_inspection_allowed": False,
        "vm_container_lifecycle_allowed": False,
        "sandbox_orchestration_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "trusted_host_promotion_allowed": False,
        "host_writes_allowed": False,
        "api_mcp_profile_loading_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
        "external_review_required_before_runtime": True,
        "closes_erg_004": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM live POC runtime-proposal review bundle",
        f"valid: {str(report['valid']).lower()}",
        f"output_dir: {report['output_dir']}",
        f"artifact_count: {report['artifact_count']}",
        f"tool_count: {report['tool_count']}",
        f"erg_004_status: {report['erg_004_status']}",
        f"finding_namespace: {report['finding_namespace']}",
        f"vm_first: {str(report['vm_first']).lower()}",
        f"operator_managed: {str(report['operator_managed']).lower()}",
        f"runtime_proposal_allowed: {str(report['runtime_proposal_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"runtime_implementation_allowed: {str(report['runtime_implementation_allowed']).lower()}",
        f"runtime_ticket_allowed: {str(report['runtime_ticket_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        "external_review_required_before_runtime: "
        f"{str(report['external_review_required_before_runtime']).lower()}",
        f"closes_erg_004: {str(report['closes_erg_004']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _index(commit: str, dirty: bool) -> str:
    return f"""# Sandbox/VM Live POC Runtime Proposal Review Bundle

Reviewed commit: `{commit}`

Dirty at generation: `{str(dirty).lower()}`

Tool count remains `24`.

Current `ERG-004` status: `ready_for_runtime_proposal_review`.

This bundle packages the VM-first and operator-managed `ERG-004` runtime proposal for external
review. It asks whether a bounded runtime implementation ticket may be drafted for a later runtime
gate.

## Artifacts

{_artifact_list()}

## What This Bundle Does Not Prove

This bundle does not prove external review happened, does not close `ERG-004`, and does not approve
runtime implementation, live VM/container inspection, VM/container lifecycle management, sandbox
orchestration, Mission Control runtime behavior, local model invocation, trusted-host promotion,
host writes, network expansion, API/MCP profile loading, SIEM adapter behavior, production identity,
runtime Postgres, hosted telemetry, remote MCP, compliance automation, shell/Docker/Kubernetes/
browser governed powers, arbitrary HTTP, broad filesystem writes, plugin SDK behavior, new governed
tool powers, or public/security-product positioning.
"""


def _prompt(commit: str) -> str:
    return f"""# Sandbox/VM Live POC Runtime Proposal Review Prompt

You are reviewing Ithildin as an external/source reviewer for the `ERG-004` live sandbox/VM worker
runtime-proposal lane only.

Reviewed commit: `{commit}`

Finding namespace: `EXT-LIVE-RUNTIME-###`

## Scope

Please inspect the attached runtime proposal, implementation-planning context, decision record,
active-route clarity note, evidence contracts, negative plan, and command evidence.

Please answer:

1. Are the artifacts complete enough for a bounded runtime implementation ticket to be drafted for a
   later runtime gate?
2. Are the operator-managed VM boundaries clear enough?
3. Are Ithildin live inspection, lifecycle control, local model invocation, Mission Control runtime,
   trusted-host promotion, host writes, and network expansion still excluded?
4. Are the descriptor fields, cleanup/failure transcript plans, and negative cases sufficient for
   later source review?
5. What findings, if any, must be fixed before a runtime implementation ticket may be drafted?

Do not approve runtime implementation. Do not approve live VM/container inspection. Do not approve
VM/container lifecycle management. Do not approve local model invocation. Do not approve sandbox
orchestration. Do not approve Mission Control runtime behavior. Do not approve trusted-host
promotion. Do not approve host writes, network expansion, API/MCP profile loading, SIEM adapter
behavior, new governed tool powers, shell, Docker, Kubernetes, browser automation, arbitrary HTTP,
broad writes, production identity, runtime Postgres, hosted telemetry, remote MCP, compliance
automation, or public/security-product positioning.

Use finding IDs `EXT-LIVE-RUNTIME-###`.
"""


def _negative_plan_summary() -> str:
    return """# ERG-004 Runtime Proposal Negative Plan Summary

Current packet status: `ready_for_runtime_proposal_review`.

The bundled contract and precondition docs above are prerequisite/historical context. Older
`blocked` status labels in those source docs describe their original lane state, not the current
runtime-proposal review packet status.

The runtime proposal requires negative transcripts or fixtures for attempted live VM/container
inspection by Ithildin, attempted VM/container lifecycle management by Ithildin, attempted local
model invocation by Ithildin, attempted Mission Control execution/approval/policy/audit authority,
attempted trusted-host promotion, attempted host write or artifact promotion, arbitrary network
expansion, shell/Docker/Kubernetes/browser execution, cleanup failure, mismatched transcript hashes,
packet hash mismatch, and raw secret, prompt, model response, file content, diff, transcript, raw
path, dependency name, package script value, or directory listing leakage.
"""


def _docs_bundle(title: str, repo_root: Path, docs: list[str]) -> str:
    lines = [f"# {title}", ""]
    for rel in docs:
        path = repo_root / rel
        if not path.exists():
            raise SandboxVmLivePocRuntimeProposalReviewBundleError(
                f"missing bundled doc: {rel}"
            )
        lines.extend([f"## {rel}", "", path.read_text(encoding="utf-8"), ""])
    return "\n".join(lines)


def _command_evidence(
    commit: str, dirty: bool, command_reports: list[dict[str, Any]]
) -> str:
    payload = {
        "schema_version": "1",
        "commit": commit,
        "dirty": dirty,
        "tool_count": 24,
        "erg_004_status": "ready_for_runtime_proposal_review",
        "commands": command_reports,
        "runtime_proposal_allowed": True,
        "runtime_changes_allowed": False,
        "runtime_implementation_allowed": False,
        "runtime_ticket_allowed": False,
        "live_vm_inspection_allowed": False,
        "vm_container_lifecycle_allowed": False,
        "sandbox_orchestration_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "trusted_host_promotion_allowed": False,
        "api_mcp_profile_loading_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
        "external_review_required_before_runtime": True,
        "closes_erg_004": False,
    }
    return "# ERG-004 Runtime Proposal Command Evidence\n\n```json\n" + json.dumps(
        payload, indent=2, sort_keys=True
    ) + "\n```\n"


def _build_command_reports(repo_root: Path, *, run_commands: bool) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for name, command in COMMANDS:
        if not run_commands:
            reports.append({"name": name, "command": command, "skipped": True})
            continue
        completed = subprocess.run(
            command,
            cwd=repo_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=180,
        )
        reports.append(
            {
                "name": name,
                "command": command,
                "returncode": completed.returncode,
                "output_tail": completed.stdout[-4000:],
                "skipped": False,
            }
        )
        if completed.returncode != 0:
            raise SandboxVmLivePocRuntimeProposalReviewBundleError(
                f"command failed for bundle evidence: {name}"
            )
    return reports


def _artifact_list() -> str:
    lines = []
    for index, name in enumerate(ARTIFACTS, start=1):
        lines.append(f"{index}. `{name}`")
    lines.append(f"{len(ARTIFACTS) + 1}. `{HASH_MANIFEST}`")
    return "\n".join(lines)


def _write_hashes(output_dir: Path) -> None:
    artifacts = []
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
    _write(
        output_dir / HASH_MANIFEST,
        json.dumps({"schema_version": "1", "artifacts": artifacts}, indent=2) + "\n",
    )


def _require_project_root(repo_root: Path) -> None:
    missing = [marker.as_posix() for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        raise SandboxVmLivePocRuntimeProposalReviewBundleError(
            "not an Ithildin project root; missing " + ", ".join(missing)
        )


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


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
    except SandboxVmLivePocRuntimeProposalReviewBundleError as exc:
        print(f"sandbox/VM live POC runtime-proposal bundle failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built sandbox/VM live POC runtime-proposal review bundle at {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

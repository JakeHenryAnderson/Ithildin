"""Build the ERG-004 runtime-ticket review bundle."""

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

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/sandbox-vm-live-poc-runtime-ticket-review")
HASH_MANIFEST = "sandbox-vm-live-poc-runtime-ticket-review-artifact-hashes.json"
DOC_REL = "docs/codex/sandbox-vm-live-poc-runtime-ticket-review-bundle.md"
DOC_TITLE = "Sandbox/VM Live POC Runtime Ticket Review Bundle"
TARGET = "sandbox-vm-live-poc-runtime-ticket-review-bundle"
CHECK_TARGET = "sandbox-vm-live-poc-runtime-ticket-review-bundle-check"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
ARTIFACTS = [
    "00_SANDBOX_VM_LIVE_POC_RUNTIME_TICKET_REVIEW_INDEX.md",
    "01_SANDBOX_VM_LIVE_POC_RUNTIME_TICKET_REVIEW_PROMPT.md",
    "02_ERG004_RUNTIME_TICKET.md",
    "03_ERG004_RUNTIME_CONTEXT.md",
    "04_ERG004_TICKET_EVIDENCE_AND_NEGATIVE_PLAN.md",
    "05_ERG004_RUNTIME_TICKET_COMMAND_EVIDENCE.md",
]
COMMANDS = [
    (
        "sandbox-vm-live-poc-runtime-ticket-check",
        ["make", "sandbox-vm-live-poc-runtime-ticket-check"],
    ),
    (
        "sandbox-vm-live-poc-runtime-proposal-check",
        ["make", "sandbox-vm-live-poc-runtime-proposal-check"],
    ),
    (
        "sandbox-vm-live-poc-implementation-plan-check",
        ["make", "sandbox-vm-live-poc-implementation-plan-check"],
    ),
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


class SandboxVmLivePocRuntimeTicketReviewBundleError(RuntimeError):
    """Raised when the runtime-ticket review bundle cannot be built."""


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
        raise SandboxVmLivePocRuntimeTicketReviewBundleError(
            "working tree is dirty; commit before ERG-004 runtime-ticket review handoff"
        )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    command_reports = _build_command_reports(repo_root, run_commands=run_commands)
    files = {
        "00_SANDBOX_VM_LIVE_POC_RUNTIME_TICKET_REVIEW_INDEX.md": _index(commit, dirty),
        "01_SANDBOX_VM_LIVE_POC_RUNTIME_TICKET_REVIEW_PROMPT.md": _prompt(commit),
        "02_ERG004_RUNTIME_TICKET.md": _docs_bundle(
            "ERG-004 Runtime Ticket",
            repo_root,
            ["docs/codex/sandbox-vm-live-poc-runtime-ticket.md"],
        ),
        "03_ERG004_RUNTIME_CONTEXT.md": _docs_bundle(
            "ERG-004 Runtime Context",
            repo_root,
            [
                "docs/codex/sandbox-vm-live-poc-runtime-proposal.md",
                "docs/codex/sandbox-vm-live-poc-decision-record.md",
                "docs/codex/sandbox-vm-live-poc-implementation-plan.md",
            ],
        ),
        "04_ERG004_TICKET_EVIDENCE_AND_NEGATIVE_PLAN.md": _docs_bundle(
            "ERG-004 Ticket Evidence And Negative Plan",
            repo_root,
            [
                "docs/codex/sandbox-vm-live-poc-evidence-contract.md",
                "docs/codex/sandbox-vm-live-poc-preconditions-map.md",
                "docs/codex/enterprise-sandbox-control-plane-readiness.md",
            ],
        )
        + "\n"
        + _negative_plan_summary(),
        "05_ERG004_RUNTIME_TICKET_COMMAND_EVIDENCE.md": _command_evidence(
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
    review_candidate_body = makefile.partition("review-candidate:")[2].partition(
        "\n\n"
    )[0]

    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "runtime-ticket-review"
        try:
            build_bundle(
                repo_root=repo_root,
                output_dir=output_dir,
                allow_dirty=True,
                run_commands=False,
            )
        except SandboxVmLivePocRuntimeTicketReviewBundleError as exc:
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
            "runtime-ticket review bundle missing artifacts: "
            + ", ".join(sorted(missing))
        )
    hashed = {entry.get("path") for entry in hashes.get("artifacts", [])}
    if set(ARTIFACTS) - hashed:
        failures.append("artifact hashes do not cover generated markdown files")
    if HASH_MANIFEST in hashed:
        failures.append("hash manifest must not hash itself")

    index = contents.get("00_SANDBOX_VM_LIVE_POC_RUNTIME_TICKET_REVIEW_INDEX.md", "")
    prompt = contents.get("01_SANDBOX_VM_LIVE_POC_RUNTIME_TICKET_REVIEW_PROMPT.md", "")
    ticket = contents.get("02_ERG004_RUNTIME_TICKET.md", "")
    context = contents.get("03_ERG004_RUNTIME_CONTEXT.md", "")
    evidence = contents.get("05_ERG004_RUNTIME_TICKET_COMMAND_EVIDENCE.md", "")

    for phrase in [
        "Tool count remains `24`",
        "Current `ERG-004` status: `ready_for_runtime_ticket_draft`",
        "What This Bundle Does Not Prove",
    ]:
        if phrase not in index:
            failures.append(f"runtime-ticket index is missing phrase: {phrase}")
    for phrase in [
        "Finding namespace: `EXT-LIVE-TICKET-###`",
        "runtime implementation gate may be prepared later",
        "Do not approve runtime implementation",
        "Do not approve live VM/container inspection",
        "Do not approve local model invocation",
    ]:
        if phrase not in prompt:
            failures.append(f"runtime-ticket prompt is missing phrase: {phrase}")
    for phrase in [
        "sandbox-vm-live-poc-runtime-ticket.md",
        "ready_for_runtime_ticket_draft",
        "approve_draft_runtime_ticket",
        "descriptor_source: operator_supplied",
        "ithildin_lifecycle_control_performed: false",
    ]:
        if phrase not in ticket:
            failures.append(f"runtime ticket bundle is missing phrase: {phrase}")
    for phrase in [
        "sandbox-vm-live-poc-runtime-proposal.md",
        "sandbox-vm-live-poc-decision-record.md",
        "sandbox-vm-live-poc-implementation-plan.md",
        "ready_for_runtime_proposal_review",
    ]:
        if phrase not in context:
            failures.append(f"runtime context bundle is missing phrase: {phrase}")
    for phrase in [
        '"sandbox-vm-live-poc-runtime-ticket-check"',
        '"runtime_changes_allowed": false',
        '"runtime_implementation_allowed": false',
        '"live_vm_inspection_allowed": false',
        '"sandbox_orchestration_allowed": false',
        '"new_power_classes_allowed": false',
    ]:
        if phrase not in evidence:
            failures.append(f"runtime-ticket command evidence is missing phrase: {phrase}")

    combined = "\n".join(contents.values())
    for phrase in FORBIDDEN_APPROVAL_PHRASES:
        if phrase in combined:
            failures.append(f"runtime-ticket bundle contains forbidden phrase: {phrase}")

    if DOC_REL not in docs_site:
        failures.append("runtime-ticket review bundle doc is missing from docs site")
    if DOC_REL not in review_docs:
        failures.append("runtime-ticket review bundle doc is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing runtime-ticket review bundle")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if f"{CHECK_TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {CHECK_TARGET}")
    if CHECK_TARGET not in release_check_body:
        failures.append("runtime-ticket review bundle check missing from release-check")
    if f"$(MAKE) {TARGET}" not in review_candidate_body:
        failures.append("review-candidate does not generate runtime-ticket review bundle")
    if CHECK_TARGET not in release_guardrails:
        failures.append("release guardrails do not require runtime-ticket bundle check")
    if f"$(MAKE) {TARGET}" not in release_guardrails:
        failures.append("release guardrails do not require runtime-ticket bundle generation")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing runtime-ticket bundle command")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "output_dir": str(DEFAULT_OUTPUT_DIR),
        "artifact_count": len(expected),
        "tool_count": 24,
        "erg_004_status": "ready_for_runtime_ticket_draft",
        "finding_namespace": "EXT-LIVE-TICKET-###",
        "runtime_ticket_allowed": True,
        "runtime_changes_allowed": False,
        "runtime_implementation_allowed": False,
        "live_vm_inspection_allowed": False,
        "sandbox_orchestration_allowed": False,
        "local_model_invocation_allowed": False,
        "new_power_classes_allowed": False,
        "closes_erg_004": False,
    }


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM live POC runtime-ticket review bundle check",
        f"valid: {str(report['valid']).lower()}",
        f"output_dir: {report['output_dir']}",
        f"artifact_count: {report['artifact_count']}",
        f"tool_count: {report['tool_count']}",
        f"erg_004_status: {report['erg_004_status']}",
        f"finding_namespace: {report['finding_namespace']}",
        f"runtime_ticket_allowed: {str(report['runtime_ticket_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "runtime_implementation_allowed: "
        f"{str(report['runtime_implementation_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"closes_erg_004: {str(report['closes_erg_004']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _index(commit: str, dirty: bool) -> str:
    return f"""# ERG-004 Runtime Ticket Review Index

Reviewed commit: `{commit}`
Dirty tree while generated: `{str(dirty).lower()}`
Tool count remains `24`.
Current `ERG-004` status: `ready_for_runtime_ticket_draft`.

## Reading Order

1. `01_SANDBOX_VM_LIVE_POC_RUNTIME_TICKET_REVIEW_PROMPT.md`
2. `02_ERG004_RUNTIME_TICKET.md`
3. `03_ERG004_RUNTIME_CONTEXT.md`
4. `04_ERG004_TICKET_EVIDENCE_AND_NEGATIVE_PLAN.md`
5. `05_ERG004_RUNTIME_TICKET_COMMAND_EVIDENCE.md`
6. `{HASH_MANIFEST}`

## What This Bundle Does Not Prove

This packet does not approve runtime implementation, live VM/container inspection, lifecycle
management, sandbox orchestration, Mission Control runtime behavior, local model invocation,
trusted-host promotion, host writes, network expansion, API/MCP profile loading, new governed tool
powers, or public/security-product positioning.
"""


def _prompt(commit: str) -> str:
    return f"""# ERG-004 Runtime Ticket Review Prompt

You are reviewing Ithildin's `ERG-004` live sandbox/VM POC runtime-ticket draft only.

Reviewed commit: `{commit}`
Finding namespace: `EXT-LIVE-TICKET-###`

Please decide whether this draft ticket is coherent enough that a runtime implementation gate may be
prepared later. The runtime implementation gate may be prepared later only if it remains separately
reviewed and explicit. Do not approve runtime implementation from this packet.

Review:

- whether the ticket preserves descriptor-only, operator-managed VM evidence;
- whether the required fields are secret-free labels, hashes, IDs, and status metadata;
- whether negative fixtures cover lifecycle, live inspection, local model invocation, Mission
  Control runtime authority, trusted-host promotion, host writes, network expansion, API/MCP profile
  loading, and sensitive-content leakage;
- whether cleanup/failure transcript hashes and packet hashes are carried into acceptance criteria;
- whether the ticket clearly requires a later implementation gate and source review before runtime.

Do not approve runtime implementation. Do not approve live VM/container inspection.
Do not approve local model invocation. Do not approve VM lifecycle control, Mission Control runtime
behavior, host writes, network expansion, or new governed tool powers.

Use finding IDs `EXT-LIVE-TICKET-###` for actionable findings.
"""


def _docs_bundle(title: str, repo_root: Path, rel_paths: list[str]) -> str:
    sections = [f"# {title}"]
    for rel_path in rel_paths:
        sections.extend(
            [
                "",
                f"## {rel_path}",
                "",
                "```markdown",
                _read(repo_root / rel_path).strip(),
                "```",
            ]
        )
    return "\n".join(sections).rstrip() + "\n"


def _command_evidence(
    commit: str, dirty: bool, command_reports: list[dict[str, Any]]
) -> str:
    payload = {
        "commit": commit,
        "dirty": dirty,
        "tool_count": 24,
        "runtime_changes_allowed": False,
        "runtime_implementation_allowed": False,
        "live_vm_inspection_allowed": False,
        "sandbox_orchestration_allowed": False,
        "new_power_classes_allowed": False,
        "commands": command_reports,
    }
    return "# ERG-004 Runtime Ticket Command Evidence\n\n```json\n" + (
        json.dumps(payload, indent=2, sort_keys=True) + "\n```\n"
    )


def _negative_plan_summary() -> str:
    return """# Runtime Ticket Negative Plan Summary

The ticket must keep these cases fail-closed:

- attempted VM/container lifecycle management by Ithildin;
- attempted live VM/container inspection by Ithildin;
- attempted local model invocation by Ithildin;
- attempted Mission Control execution, approval, policy, or audit authority;
- attempted trusted-host promotion;
- attempted host write or artifact promotion;
- arbitrary network expansion;
- API/MCP profile loading;
- shell/Docker/Kubernetes/browser execution;
- cleanup failure;
- missing or mismatched failure transcript hash;
- raw secret, prompt, model response, file content, diff, transcript, dependency name, package
  script value, raw path, or directory listing leakage.
"""


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
        )
        reports.append(
            {
                "name": name,
                "command": command,
                "returncode": completed.returncode,
                "output": completed.stdout,
            }
        )
        if completed.returncode != 0:
            raise SandboxVmLivePocRuntimeTicketReviewBundleError(
                f"command failed for runtime-ticket review bundle: {name}"
            )
    return reports


def _write_hashes(output_dir: Path) -> None:
    artifacts = []
    for path in sorted(output_dir.iterdir()):
        if path.name == HASH_MANIFEST:
            continue
        data = path.read_bytes()
        artifacts.append(
            {
                "path": path.name,
                "sha256": "sha256:" + hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            }
        )
    _write(output_dir / HASH_MANIFEST, json.dumps({"artifacts": artifacts}, indent=2))


def _require_project_root(repo_root: Path) -> None:
    missing = [str(marker) for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        raise SandboxVmLivePocRuntimeTicketReviewBundleError(
            "not an Ithildin repo root; missing markers: " + ", ".join(missing)
        )


def _git(repo_root: Path, args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=True,
    )
    return completed.stdout.strip()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _write(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--skip-commands", action="store_true")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    if args.check:
        report = build_check_report(Path.cwd())
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print(render_check_report(report))
        return 0 if report["valid"] else 1

    output_dir = build_bundle(
        repo_root=Path.cwd(),
        output_dir=Path(args.output_dir),
        allow_dirty=args.allow_dirty,
        run_commands=not args.skip_commands,
    )
    print(f"Built sandbox/VM live POC runtime-ticket review bundle at {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Build the ERG-004 runtime implementation-gate readiness review bundle."""

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

DEFAULT_OUTPUT_DIR = Path(
    "var/review-packets/v3/sandbox-vm-live-poc-runtime-gate-readiness-review"
)
HASH_MANIFEST = "sandbox-vm-live-poc-runtime-gate-readiness-artifact-hashes.json"
DOC_REL = "docs/codex/sandbox-vm-live-poc-runtime-gate-readiness-review-bundle.md"
DOC_TITLE = "Sandbox/VM Live POC Runtime Gate Readiness Review Bundle"
TARGET = "sandbox-vm-live-poc-runtime-gate-readiness-review-bundle"
CHECK_TARGET = "sandbox-vm-live-poc-runtime-gate-readiness-review-bundle-check"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
ARTIFACTS = [
    "00_SANDBOX_VM_LIVE_POC_RUNTIME_GATE_READINESS_INDEX.md",
    "01_SANDBOX_VM_LIVE_POC_RUNTIME_GATE_READINESS_PROMPT.md",
    "02_ERG004_RUNTIME_IMPLEMENTATION_GATE.md",
    "03_ERG004_DESCRIPTOR_CONTRACT_AND_REVIEW.md",
    "04_ERG004_GATE_CONTEXT_AND_NEGATIVE_PLAN.md",
    "05_ERG004_RUNTIME_GATE_COMMAND_EVIDENCE.md",
]
COMMANDS = [
    (
        "sandbox-vm-live-poc-runtime-implementation-gate-check",
        ["make", "sandbox-vm-live-poc-runtime-implementation-gate-check"],
    ),
    (
        "sandbox-vm-live-poc-runtime-descriptor-contract-check",
        ["make", "sandbox-vm-live-poc-runtime-descriptor-contract-check"],
    ),
    (
        "sandbox-vm-live-poc-runtime-descriptor-contract-internal-review-check",
        ["make", "sandbox-vm-live-poc-runtime-descriptor-contract-internal-review-check"],
    ),
    (
        "sandbox-vm-live-poc-runtime-ticket-internal-review-check",
        ["make", "sandbox-vm-live-poc-runtime-ticket-internal-review-check"],
    ),
    (
        "sandbox-vm-live-poc-runtime-gate-readiness-response-dry-run",
        ["make", "sandbox-vm-live-poc-runtime-gate-readiness-response-dry-run"],
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
    "host writes are approved",
    "new governed tool powers are approved",
    "public security product approved",
]


class SandboxVmLivePocRuntimeGateReadinessBundleError(RuntimeError):
    """Raised when the runtime gate-readiness bundle cannot be built."""


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
        raise SandboxVmLivePocRuntimeGateReadinessBundleError(
            "working tree is dirty; commit before ERG-004 runtime gate-readiness handoff"
        )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    command_reports = _build_command_reports(repo_root, run_commands=run_commands)
    files = {
        "00_SANDBOX_VM_LIVE_POC_RUNTIME_GATE_READINESS_INDEX.md": _index(
            commit, dirty
        ),
        "01_SANDBOX_VM_LIVE_POC_RUNTIME_GATE_READINESS_PROMPT.md": _prompt(commit),
        "02_ERG004_RUNTIME_IMPLEMENTATION_GATE.md": _docs_bundle(
            "ERG-004 Runtime Implementation Gate",
            repo_root,
            ["docs/codex/sandbox-vm-live-poc-runtime-implementation-gate.md"],
        ),
        "03_ERG004_DESCRIPTOR_CONTRACT_AND_REVIEW.md": _docs_bundle(
            "ERG-004 Descriptor Contract And Internal Review",
            repo_root,
            [
                "docs/codex/sandbox-vm-live-poc-runtime-implementation-decision.md",
                "docs/codex/sandbox-vm-live-poc-runtime-descriptor-contract.md",
                "docs/codex/sandbox-vm-live-poc-runtime-negative-fixtures.md",
                "docs/codex/sandbox-vm-live-poc-runtime-descriptor-contract-internal-review.md",
            ],
        ),
        "04_ERG004_GATE_CONTEXT_AND_NEGATIVE_PLAN.md": _docs_bundle(
            "ERG-004 Gate Context And Negative Plan",
            repo_root,
            [
                "docs/codex/sandbox-vm-live-poc-runtime-ticket.md",
                "docs/codex/sandbox-vm-live-poc-runtime-ticket-internal-review.md",
                "docs/codex/sandbox-vm-live-poc-runtime-proposal.md",
                "docs/codex/sandbox-vm-live-poc-decision-record.md",
            ],
        )
        + "\n"
        + _negative_plan_summary(),
        "05_ERG004_RUNTIME_GATE_COMMAND_EVIDENCE.md": _command_evidence(
            commit, dirty, command_reports
        ),
    }
    for name, content in files.items():
        _write(output_dir / name, content)
    _write_hashes(output_dir)
    return output_dir


def build_check_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    current_commit = _git(repo_root, ["rev-parse", "HEAD"])
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
        output_dir = Path(tmp) / "runtime-gate-readiness-review"
        try:
            build_bundle(
                repo_root=repo_root,
                output_dir=output_dir,
                allow_dirty=True,
                run_commands=False,
            )
        except SandboxVmLivePocRuntimeGateReadinessBundleError as exc:
            failures.append(str(exc))
            artifact_names: set[str] = set()
            hashes: dict[str, Any] = {"artifacts": []}
            contents: dict[str, str] = {}
        else:
            artifact_names = {path.name for path in output_dir.iterdir()}
            hashes = json.loads((output_dir / HASH_MANIFEST).read_text(encoding="utf-8"))
            contents = {
                name: (output_dir / name).read_text(encoding="utf-8")
                for name in ARTIFACTS
            }

    expected = set(ARTIFACTS) | {HASH_MANIFEST}
    missing = expected - artifact_names
    if missing:
        failures.append(
            "runtime gate-readiness bundle missing artifacts: "
            + ", ".join(sorted(missing))
        )
    hashed = {entry.get("path") for entry in hashes.get("artifacts", [])}
    if set(ARTIFACTS) - hashed:
        failures.append("artifact hashes do not cover generated markdown files")
    if HASH_MANIFEST in hashed:
        failures.append("hash manifest must not hash itself")

    index = contents.get("00_SANDBOX_VM_LIVE_POC_RUNTIME_GATE_READINESS_INDEX.md", "")
    prompt = contents.get("01_SANDBOX_VM_LIVE_POC_RUNTIME_GATE_READINESS_PROMPT.md", "")
    gate = contents.get("02_ERG004_RUNTIME_IMPLEMENTATION_GATE.md", "")
    descriptor = contents.get("03_ERG004_DESCRIPTOR_CONTRACT_AND_REVIEW.md", "")
    context = contents.get("04_ERG004_GATE_CONTEXT_AND_NEGATIVE_PLAN.md", "")
    evidence = contents.get("05_ERG004_RUNTIME_GATE_COMMAND_EVIDENCE.md", "")

    for name, content in [
        ("index", index),
        ("prompt", prompt),
        ("command evidence", evidence),
    ]:
        if current_commit not in content:
            failures.append(
                f"runtime gate-readiness {name} does not reference current commit"
            )

    for phrase in [
        "Tool count remains `24`",
        "Current `ERG-004` status: `ready_for_runtime_implementation_gate_review`",
        "response dry run",
        "What This Bundle Does Not Prove",
    ]:
        if phrase not in index:
            failures.append(f"runtime gate-readiness index is missing phrase: {phrase}")
    for phrase in [
        "Finding namespace: `EXT-LIVE-GATE-###`",
        "descriptor-only runtime implementation sprint may be planned later",
        "Do not approve runtime implementation",
        "Do not approve live VM/container inspection",
        "local model invocation",
    ]:
        if phrase not in prompt:
            failures.append(f"runtime gate-readiness prompt is missing phrase: {phrase}")
    for phrase in [
        "sandbox-vm-live-poc-runtime-implementation-gate.md",
        "ready_for_runtime_implementation_gate_review",
        "descriptor/correlation slice",
        "Required Future Runtime Tests",
    ]:
        if phrase not in gate:
            failures.append(f"runtime implementation gate bundle is missing phrase: {phrase}")
    for phrase in [
        "sandbox-vm-live-poc-runtime-descriptor-contract.md",
        "sandbox-vm-live-poc-runtime-descriptor-contract-internal-review.md",
        "approve_internal_descriptor_contract_checkpoint",
        "Runtime implementation remains blocked",
    ]:
        if phrase not in descriptor:
            failures.append(f"descriptor contract/review bundle is missing phrase: {phrase}")
    for phrase in [
        "sandbox-vm-live-poc-runtime-ticket.md",
        "sandbox-vm-live-poc-runtime-ticket-internal-review.md",
        "approve_internal_runtime_ticket_review",
        "attempted live VM/container",
        "raw secret, prompt, model response",
    ]:
        if phrase not in context:
            failures.append(f"gate context bundle is missing phrase: {phrase}")
    for phrase in [
        '"sandbox-vm-live-poc-runtime-implementation-gate-check"',
        '"sandbox-vm-live-poc-runtime-descriptor-contract-check"',
        '"sandbox-vm-live-poc-runtime-descriptor-contract-internal-review-check"',
        '"sandbox-vm-live-poc-runtime-gate-readiness-response-dry-run"',
        '"runtime_implementation_allowed": false',
        '"live_vm_inspection_allowed": false',
        '"sandbox_orchestration_allowed": false',
        '"new_power_classes_allowed": false',
    ]:
        if phrase not in evidence:
            failures.append(f"runtime gate command evidence is missing phrase: {phrase}")

    combined = "\n".join(contents.values())
    for phrase in FORBIDDEN_APPROVAL_PHRASES:
        if phrase in combined:
            failures.append(f"runtime gate-readiness bundle contains forbidden phrase: {phrase}")

    if DOC_REL not in docs_site:
        failures.append("runtime gate-readiness bundle doc is missing from docs site")
    if DOC_REL not in review_docs:
        failures.append("runtime gate-readiness bundle doc is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing runtime gate-readiness bundle")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if f"{CHECK_TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {CHECK_TARGET}")
    if CHECK_TARGET not in release_check_body:
        failures.append("runtime gate-readiness bundle check missing from release-check")
    if f"$(MAKE) {TARGET}" not in review_candidate_body:
        failures.append("review-candidate does not generate runtime gate-readiness bundle")
    if CHECK_TARGET not in release_guardrails:
        failures.append("release guardrails do not require runtime gate-readiness check")
    if f"$(MAKE) {TARGET}" not in release_guardrails:
        failures.append("release guardrails do not require runtime gate-readiness generation")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing runtime gate-readiness bundle command")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "output_dir": str(DEFAULT_OUTPUT_DIR),
        "artifact_count": len(expected),
        "current_commit": current_commit,
        "tool_count": 24,
        "erg_004_status": "ready_for_runtime_implementation_gate_review",
        "finding_namespace": "EXT-LIVE-GATE-###",
        "runtime_gate_readiness_review_allowed": True,
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
        "Ithildin sandbox/VM live POC runtime gate-readiness review bundle check",
        f"valid: {str(report['valid']).lower()}",
        f"output_dir: {report['output_dir']}",
        f"artifact_count: {report['artifact_count']}",
        f"tool_count: {report['tool_count']}",
        f"erg_004_status: {report['erg_004_status']}",
        f"finding_namespace: {report['finding_namespace']}",
        "runtime_gate_readiness_review_allowed: "
        f"{str(report['runtime_gate_readiness_review_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "runtime_implementation_allowed: "
        f"{str(report['runtime_implementation_allowed']).lower()}",
        "live_vm_inspection_allowed: "
        f"{str(report['live_vm_inspection_allowed']).lower()}",
        "sandbox_orchestration_allowed: "
        f"{str(report['sandbox_orchestration_allowed']).lower()}",
        "local_model_invocation_allowed: "
        f"{str(report['local_model_invocation_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"closes_erg_004: {str(report['closes_erg_004']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _index(commit: str, dirty: bool) -> str:
    return f"""# Sandbox/VM Live POC Runtime Gate Readiness Review Index

Reviewed commit: `{commit}`

Dirty tree: `{str(dirty).lower()}`

Tool count remains `24`.

Current `ERG-004` status: `ready_for_runtime_implementation_gate_review`.

This packet packages the ERG-004 runtime implementation gate draft, descriptor/correlation
contract, internal xhigh descriptor-contract review, runtime-ticket context, response dry run, and
command evidence. It asks whether a later descriptor-only runtime implementation sprint may be
planned.

## Artifacts

- `01_SANDBOX_VM_LIVE_POC_RUNTIME_GATE_READINESS_PROMPT.md`
- `02_ERG004_RUNTIME_IMPLEMENTATION_GATE.md`
- `03_ERG004_DESCRIPTOR_CONTRACT_AND_REVIEW.md`
- `04_ERG004_GATE_CONTEXT_AND_NEGATIVE_PLAN.md`
- `05_ERG004_RUNTIME_GATE_COMMAND_EVIDENCE.md`
- `{HASH_MANIFEST}`

## What This Bundle Does Not Prove

This bundle does not approve runtime implementation, does not prove a VM/container is safe, does not
inspect live VM/container state, does not start or stop a VM/container, does not invoke a local
model, does not grant Mission Control runtime authority, does not load profiles through API/MCP, and
does not close `ERG-004`.
"""


def _prompt(commit: str) -> str:
    return f"""# ERG-004 Runtime Gate Readiness Review Prompt

You are reviewing Ithildin's `ERG-004` live sandbox/VM POC lane at the runtime gate-readiness stage.
Treat this as a packet review only unless you inspect the attached source/docs/evidence.

Reviewed commit: `{commit}`

Area: `sandbox-vm-live-poc-runtime-gate-readiness`

Finding namespace: `EXT-LIVE-GATE-###`

## Question

Can a descriptor-only runtime implementation sprint may be planned later for ERG-004, limited to
operator-supplied descriptor validation and correlation evidence?

## Review Focus

- Does the gate preserve operator-managed VM lifecycle and OS isolation?
- Does the descriptor contract stay closed, safe-label-only, hash/correlation oriented, and
  secret-free?
- Do the negative fixtures block lifecycle control, live inspection, local model invocation, Mission
  Control authority, host writes, trusted-host promotion, network expansion, and API/MCP profile
  loading?
- Does the packet make clear that source review is required before any live runtime readiness claim?

## Required Disposition

Answer whether the next sprint may plan a descriptor-only runtime implementation. If not, list the
exact blocker or missing evidence.

Use finding IDs in the `EXT-LIVE-GATE-###` namespace.

Do not approve runtime implementation. Do not approve live VM/container inspection. Do not approve
local model invocation. Do not approve Mission Control runtime authority. Do not approve host
writes, trusted-host promotion, profile loading, or new governed tool powers.
"""


def _docs_bundle(title: str, repo_root: Path, rel_paths: list[str]) -> str:
    parts = [f"# {title}\n"]
    for rel_path in rel_paths:
        path = repo_root / rel_path
        parts.append(f"\n## `{rel_path}`\n\n")
        parts.append(path.read_text(encoding="utf-8"))
        parts.append("\n")
    return "\n".join(parts)


def _negative_plan_summary() -> str:
    return """## Negative Review Expectations

The next implementation planning step must keep these negative cases explicit:

- attempted live VM/container inspection;
- attempted VM/container lifecycle management;
- attempted sandbox orchestration;
- attempted local model invocation;
- attempted Mission Control execution, approval, policy, or audit authority;
- attempted trusted-host promotion or host writes;
- network expansion or API/MCP profile loading;
- raw secret, prompt, model response, file content, diff, transcript, dependency name, package
  script value, raw path, or directory listing leakage.
"""


def _command_evidence(
    commit: str, dirty: bool, command_reports: list[dict[str, Any]]
) -> str:
    payload = {
        "commit": commit,
        "dirty": dirty,
        "commands": command_reports,
        "runtime_changes_allowed": False,
        "runtime_implementation_allowed": False,
        "live_vm_inspection_allowed": False,
        "vm_container_lifecycle_allowed": False,
        "sandbox_orchestration_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "trusted_host_promotion_allowed": False,
        "host_writes_allowed": False,
        "network_expansion_allowed": False,
        "api_mcp_profile_loading_allowed": False,
        "new_power_classes_allowed": False,
        "closes_erg_004": False,
    }
    return "# ERG-004 Runtime Gate Command Evidence\n\n```json\n" + json.dumps(
        payload, indent=2, sort_keys=True
    ) + "\n```\n"


def _build_command_reports(repo_root: Path, *, run_commands: bool) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for name, cmd in COMMANDS:
        if not run_commands:
            reports.append({"name": name, "command": cmd, "status": "not_run"})
            continue
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        reports.append(
            {
                "name": name,
                "command": cmd,
                "exit_code": result.returncode,
                "status": "passed" if result.returncode == 0 else "failed",
                "output_tail": "\n".join(result.stdout.splitlines()[-80:]),
            }
        )
        if result.returncode != 0:
            raise SandboxVmLivePocRuntimeGateReadinessBundleError(
                f"command failed for runtime gate-readiness bundle: {name}"
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
    _write(output_dir / HASH_MANIFEST, json.dumps({"artifacts": artifacts}, indent=2) + "\n")


def _write(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


def _require_project_root(repo_root: Path) -> None:
    missing = [str(marker) for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        raise SandboxVmLivePocRuntimeGateReadinessBundleError(
            "not an Ithildin repo root; missing project markers: " + ", ".join(missing)
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--skip-commands", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    if args.check:
        report = build_check_report(Path.cwd())
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print(render_check_report(report))
        return 0 if report["valid"] else 1

    try:
        output_dir = build_bundle(
            repo_root=Path.cwd(),
            output_dir=args.output_dir,
            allow_dirty=args.allow_dirty,
            run_commands=not args.skip_commands,
        )
    except SandboxVmLivePocRuntimeGateReadinessBundleError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Built ERG-004 runtime gate-readiness review bundle at {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

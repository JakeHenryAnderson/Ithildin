"""Build a reviewer-response kit for the blocked sandbox/VM live POC lane."""

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
    sandbox_vm_live_poc_decision_closure_check,
    sandbox_vm_live_poc_decision_record_skeleton_check,
    sandbox_vm_live_poc_external_response_intake_check,
    sandbox_vm_live_poc_prerequisite_disposition_dry_run,
    sandbox_vm_live_poc_response_dry_run,
)

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/sandbox-vm-live-poc-response-kit")
HASH_MANIFEST = "sandbox-vm-live-poc-response-kit-artifact-hashes.json"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
ARTIFACTS = [
    "00_SANDBOX_VM_LIVE_POC_RESPONSE_KIT_INDEX.md",
    "01_SANDBOX_VM_LIVE_POC_RESPONSE_INTAKE_GUIDE.md",
    "02_SANDBOX_VM_LIVE_POC_NORMALIZED_RESPONSE_EXAMPLES.md",
    "03_SANDBOX_VM_LIVE_POC_CLOSURE_TRIAGE_COMMANDS.md",
    "04_SANDBOX_VM_LIVE_POC_QUEUE_AND_BOUNDARY_STATUS.md",
    "05_SANDBOX_VM_LIVE_POC_RESPONSE_KIT_EVIDENCE.md",
]


class SandboxVmLivePocResponseKitError(RuntimeError):
    """Raised when the live POC response kit cannot be built."""


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
        output_dir = build_kit(
            repo_root=Path.cwd().resolve(),
            output_dir=args.output_dir,
            allow_dirty=args.allow_dirty,
            run_commands=not args.skip_commands,
        )
    except SandboxVmLivePocResponseKitError as exc:
        print(f"sandbox/VM live POC response kit failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built sandbox/VM live POC response kit at {output_dir}")
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
    decision_register = _read(repo_root / "docs/codex/post-rc-decision-register.md")
    preconditions = _read(repo_root / "docs/codex/sandbox-vm-live-poc-preconditions-map.md")
    preconditions_ready = _read(
        repo_root / "docs/codex/sandbox-vm-live-poc-preconditions-ready-check.md"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "sandbox-vm-live-poc-response-kit"
        try:
            build_kit(
                repo_root=repo_root,
                output_dir=output_dir,
                allow_dirty=True,
                run_commands=False,
            )
        except SandboxVmLivePocResponseKitError as exc:
            failures.append(str(exc))
            artifact_names: set[str] = set()
            hashes: dict[str, Any] = {"artifacts": []}
            artifact_hashes_match_files = False
            contents: dict[str, str] = {}
        else:
            artifact_names = {path.name for path in output_dir.iterdir()}
            hashes = json.loads((output_dir / HASH_MANIFEST).read_text(encoding="utf-8"))
            artifact_hashes_match_files = _artifact_hashes_match_files(
                output_dir=output_dir,
                hashes=hashes,
            )
            contents = {
                name: (output_dir / name).read_text(encoding="utf-8") for name in ARTIFACTS
            }

    expected = set(ARTIFACTS) | {HASH_MANIFEST}
    missing = expected - artifact_names
    if missing:
        failures.append("response kit missing artifacts: " + ", ".join(sorted(missing)))
    hashed = {entry["path"] for entry in hashes.get("artifacts", [])}
    if HASH_MANIFEST in hashed:
        failures.append("hash manifest must not hash itself")
    if set(ARTIFACTS) - hashed:
        failures.append("artifact hashes do not cover generated markdown files")
    if not artifact_hashes_match_files:
        failures.append("artifact hashes do not match generated markdown files")

    index = contents.get("00_SANDBOX_VM_LIVE_POC_RESPONSE_KIT_INDEX.md", "")
    guide = contents.get("01_SANDBOX_VM_LIVE_POC_RESPONSE_INTAKE_GUIDE.md", "")
    examples = contents.get("02_SANDBOX_VM_LIVE_POC_NORMALIZED_RESPONSE_EXAMPLES.md", "")
    commands = contents.get("03_SANDBOX_VM_LIVE_POC_CLOSURE_TRIAGE_COMMANDS.md", "")
    boundary = contents.get("04_SANDBOX_VM_LIVE_POC_QUEUE_AND_BOUNDARY_STATUS.md", "")
    evidence = contents.get("05_SANDBOX_VM_LIVE_POC_RESPONSE_KIT_EVIDENCE.md", "")

    for phrase in [
        "Tool count remains `24`",
        "What This Kit Does Not Prove",
        "does not close `ERG-004`",
        "does not approve live VM/container inspection",
        "does not approve implementation planning",
    ]:
        if phrase not in index:
            failures.append(f"response kit index is missing phrase: {phrase}")
    for phrase in [
        "Finding namespace: `EXT-LIVE-POC-###`",
        "var/review-runs/sandbox-vm-live-poc/normalized-response.json",
        "sandbox-vm-live-poc-external-response-intake.md",
        "Only a later committed decision-record update may move `ERG-004`",
    ]:
        if phrase not in guide:
            failures.append(f"response intake guide is missing phrase: {phrase}")
    for phrase in [
        '"response_type": "ithildin.external_review.normalized_response"',
        '"area": "sandbox-vm-live-poc"',
        '"source_access": "source-level"',
        '"source_access": "packet-only"',
        '"erg_003_favorable_disposition": true',
        '"decision_outcome": "approve_limited_operator_managed_poc_planning"',
        '"closes_external_review": false',
    ]:
        if phrase not in examples:
            failures.append(f"normalized response examples are missing phrase: {phrase}")
    for phrase in [
        "make sandbox-vm-live-poc-decision-closure-check",
        "make sandbox-vm-live-poc-decision-record-skeleton-check",
        "make sandbox-vm-live-poc-preconditions-ready-check",
        "make sandbox-vm-live-poc-response-dry-run",
        "make sandbox-vm-live-poc-prerequisite-disposition-dry-run",
        "make review-run-manifest-refresh",
        "make release-check",
        "make review-candidate",
    ]:
        if phrase not in commands:
            failures.append(f"closure/triage commands are missing phrase: {phrase}")
    for phrase in [
        "ERG-003",
        "ERG-004",
        "live VM/container inspection",
        "Mission Control runtime behavior",
        "local model invocation",
        "sandbox-vm-live-poc-preconditions-ready-check.md",
        "sandbox orchestration",
        "trusted-host promotion",
    ]:
        if phrase not in boundary:
            failures.append(f"boundary status is missing phrase: {phrase}")
    for phrase in [
        '"response_kit_boundary"',
        '"runtime_changes_allowed": false',
        '"implementation_planning_allowed": false',
        '"live_vm_inspection_allowed": false',
        '"sandbox_orchestration_allowed": false',
        '"local_model_invocation_allowed": false',
        '"preconditions_ready"',
        '"erg_004_closed": false',
        '"decision_record_recorded": false',
        '"prerequisite_disposition_dry_run"',
        '"erg_004_unblocked": false',
    ]:
        if phrase not in evidence:
            failures.append(f"response kit evidence is missing phrase: {phrase}")

    target = "sandbox-vm-live-poc-response-kit"
    check_target = f"{target}-check"
    for make_target in [f"{target}:", f"{check_target}:"]:
        if make_target not in makefile:
            failures.append(f"Make target is missing: {make_target.rstrip(':')}")
    release_check_additive = f"release-check: {check_target}"
    if check_target not in release_check_body and release_check_additive not in makefile:
        failures.append(f"{check_target} missing from release-check")
    if f"$(MAKE) {target}" not in review_candidate_body:
        failures.append(f"{target} missing from review-candidate")
    if check_target not in release_guardrails:
        failures.append(f"release guardrails do not require {check_target}")
    if f"$(MAKE) {target}" not in release_guardrails:
        failures.append(f"release guardrails do not require review-candidate {target}")
    doc_rel = "docs/codex/sandbox-vm-live-poc-response-kit.md"
    if doc_rel not in docs_site:
        failures.append("response kit doc is missing from docs-site inputs")
    if doc_rel not in review_docs:
        failures.append("response kit doc is missing from review docs")
    if "Sandbox/VM Live POC Response Kit" not in review_index:
        failures.append("review-docs index is missing live POC response kit entry")
    if f"make {target}" not in readme:
        failures.append("README is missing live POC response kit command")
    for text, source in [
        (runway, "enterprise runway"),
        (gap_matrix, "enterprise gap matrix"),
        (queue, "enterprise external-review queue"),
        (decision_register, "post-RC decision register"),
        (preconditions, "live POC preconditions map"),
        (preconditions_ready, "live POC preconditions ready check"),
    ]:
        if "sandbox-vm-live-poc-response-kit" not in text:
            failures.append(f"{source} is missing live POC response kit pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "output_dir": str(DEFAULT_OUTPUT_DIR),
        "artifact_count": len(expected),
        "artifact_hashes_match_files": artifact_hashes_match_files,
        "tool_count": 24,
        "erg_003_status": "closed_local_preview_static_preflight",
        "erg_003_disposition_recorded": True,
        "erg_004_status": "blocked",
        "recommended_next_review": "ERG-004 only after ERG-003 disposition",
        "runtime_changes_allowed": False,
        "implementation_planning_allowed": False,
        "live_vm_inspection_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "network_expansion_allowed": False,
        "api_mcp_profile_loading_allowed": False,
        "new_power_classes_allowed": False,
        "erg_004_closed": False,
        "decision_record_recorded": False,
    }


def build_kit(
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
        raise SandboxVmLivePocResponseKitError(
            "working tree is dirty; commit before live POC response-kit handoff"
        )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    command_reports = _build_command_reports(repo_root, run_commands=run_commands)
    files = {
        "00_SANDBOX_VM_LIVE_POC_RESPONSE_KIT_INDEX.md": _index(commit, dirty),
        "01_SANDBOX_VM_LIVE_POC_RESPONSE_INTAKE_GUIDE.md": _intake_guide(),
        "02_SANDBOX_VM_LIVE_POC_NORMALIZED_RESPONSE_EXAMPLES.md": _examples(),
        "03_SANDBOX_VM_LIVE_POC_CLOSURE_TRIAGE_COMMANDS.md": _commands(),
        "04_SANDBOX_VM_LIVE_POC_QUEUE_AND_BOUNDARY_STATUS.md": _docs_bundle(
            "Queue And Boundary Status",
            repo_root,
            [
                "docs/codex/enterprise-external-review-queue.md",
                "docs/codex/enterprise-readiness-gap-matrix.md",
                "docs/codex/sandbox-vm-live-poc-preconditions-map.md",
                "docs/codex/sandbox-vm-live-poc-preconditions-ready-check.md",
                "docs/codex/sandbox-vm-live-poc-decision-record-skeleton.md",
                "docs/codex/sandbox-vm-live-poc-prerequisite-disposition-dry-run.md",
                "docs/codex/post-rc-decision-register.md",
            ],
        ),
        "05_SANDBOX_VM_LIVE_POC_RESPONSE_KIT_EVIDENCE.md": _command_evidence(
            command_reports
        ),
    }
    for name, content in files.items():
        (output_dir / name).write_text(content, encoding="utf-8")
    _write_hashes(output_dir)
    return output_dir


def _index(commit: str, dirty: bool) -> str:
    boundary = (
        "This response kit does not prove external review happened, does not close `ERG-004`, "
        "does not close `ERG-003`, does not approve implementation planning, and does not "
        "approve live VM/container inspection, VM/container lifecycle management, sandbox "
        "orchestration, Mission Control runtime behavior, local model invocation, trusted-host "
        "promotion, network expansion, API/MCP profile loading, new governed tool powers, "
        "production identity, runtime Postgres, hosted telemetry, remote MCP, SIEM delivery, "
        "compliance automation, or public/security-product positioning."
    )
    return f"""# Sandbox/VM Live POC Response Kit

Status: response-intake kit for blocked `ERG-004` after external/source decision-packet review.

Reviewed commit for kit generation: `{commit}`
Dirty state when generated: `{str(dirty).lower()}`

Tool count remains `24`.

Current `ERG-003` status: `closed_local_preview_static_preflight`.

Current `ERG-004` status: `blocked`.

## Reading Order

1. `01_SANDBOX_VM_LIVE_POC_RESPONSE_INTAKE_GUIDE.md`
2. `02_SANDBOX_VM_LIVE_POC_NORMALIZED_RESPONSE_EXAMPLES.md`
3. `03_SANDBOX_VM_LIVE_POC_CLOSURE_TRIAGE_COMMANDS.md`
4. `04_SANDBOX_VM_LIVE_POC_QUEUE_AND_BOUNDARY_STATUS.md`
5. `05_SANDBOX_VM_LIVE_POC_RESPONSE_KIT_EVIDENCE.md`
6. `sandbox-vm-live-poc-response-kit-artifact-hashes.json`

## What This Kit Does Not Prove

{boundary}
"""


def _intake_guide() -> str:
    return """# Response Intake Guide

Finding namespace: `EXT-LIVE-POC-###`

Reviewed area for normalization: `sandbox-vm-live-poc`

Response target:

```text
var/review-runs/sandbox-vm-live-poc/normalized-response.json
```

Start from:

- `sandbox-vm-live-poc-external-response-intake.md`
- `sandbox-vm-live-poc-decision-closure-gate.md`
- `sandbox-vm-live-poc-response-dry-run.md`
- `sandbox-vm-live-poc-prerequisite-disposition-dry-run.md`
- `sandbox-vm-live-poc-decision-record-skeleton.md`

Only a later committed decision-record update may move `ERG-004`, and only after the closure gate
reports `closure_ready: true`. The normalized response must include favorable `ERG-003` disposition
evidence and may support implementation-planning-only discussion. It must not approve runtime
implementation, live VM/container inspection, local model invocation, sandbox orchestration,
Mission Control runtime behavior, trusted-host promotion, or API/MCP profile loading.
"""


def _examples() -> str:
    favorable = {
        "response_type": "ithildin.external_review.normalized_response",
        "area": "sandbox-vm-live-poc",
        "source_access": "source-level",
        "reviewed_packet_hash": "sha256:" + ("0" * 64),
        "can_close_source_rows": True,
        "mutates_findings": False,
        "closes_external_review": False,
        "erg_003_favorable_disposition": True,
        "decision_outcome": "approve_limited_operator_managed_poc_planning",
        "findings": [],
    }
    unfavorable = {
        "response_type": "ithildin.external_review.normalized_response",
        "area": "sandbox-vm-live-poc",
        "source_access": "packet-only",
        "reviewed_packet_hash": "sha256:" + ("0" * 64),
        "can_close_source_rows": False,
        "mutates_findings": False,
        "closes_external_review": False,
        "erg_003_favorable_disposition": False,
        "decision_outcome": "block_live_poc",
        "findings": [
            {
                "finding_id": "EXT-LIVE-POC-001",
                "severity": "high",
                "area": "sandbox-vm-live-poc",
                "affected_files_functions": "docs/codex/sandbox-vm-live-poc-decision-packet.md",
                "blocking_status": "blocking",
                "disposition": "open",
                "recommended_fix": "example unfavorable response",
            }
        ],
    }
    return (
        "# Normalized Response Examples\n\n"
        "These are shape examples only. Replace reviewer, packet, hash, and finding values with "
        "real evidence before using the response path.\n\n"
        "## Favorable Shape\n\n"
        "```json\n"
        f"{json.dumps(favorable, indent=2, sort_keys=True)}\n"
        "```\n\n"
        "## Unfavorable Shape\n\n"
        "```json\n"
        f"{json.dumps(unfavorable, indent=2, sort_keys=True)}\n"
        "```\n"
    )


def _commands() -> str:
    return """# Closure And Triage Commands

Run these commands after placing real normalized response evidence under the ignored response path:

```sh
make sandbox-vm-live-poc-decision-closure-check
make sandbox-vm-live-poc-decision-record-skeleton-check
make sandbox-vm-live-poc-preconditions-ready-check
make sandbox-vm-live-poc-response-dry-run
make sandbox-vm-live-poc-prerequisite-disposition-dry-run
make enterprise-external-review-queue-check
```

If and only if the closure gate reports `closure_ready: true`, perform a separate committed
decision-record update following `sandbox-vm-live-poc-decision-record-skeleton.md`, then run:

```sh
make review-run-manifest-refresh
make release-check
make review-candidate
```

If the response is absent, malformed, packet-only, docs-only, missing favorable `ERG-003`
disposition, critical/high, or attempts to close external review directly, keep `ERG-004` as
`blocked`.
"""


def _docs_bundle(title: str, repo_root: Path, rel_paths: list[str]) -> str:
    parts = [f"# {title}\n"]
    for rel in rel_paths:
        content = (repo_root / rel).read_text(encoding="utf-8")
        parts.append(f"\n## {rel}\n\n```markdown\n{content}\n```\n")
    return "".join(parts)


def _build_command_reports(repo_root: Path, *, run_commands: bool) -> dict[str, Any]:
    reports: dict[str, Any] = {
        "response_kit_boundary": {
            "runtime_changes_allowed": False,
            "implementation_planning_allowed": False,
            "live_vm_inspection_allowed": False,
            "mission_control_runtime_allowed": False,
            "local_model_invocation_allowed": False,
            "sandbox_orchestration_allowed": False,
            "trusted_host_promotion_allowed": False,
            "network_expansion_allowed": False,
            "api_mcp_profile_loading_allowed": False,
            "new_power_classes_allowed": False,
            "erg_004_closed": False,
            "decision_record_recorded": False,
        },
        "external_response_intake_check": (
            sandbox_vm_live_poc_external_response_intake_check.build_report(repo_root)
        ),
        "decision_closure_check": sandbox_vm_live_poc_decision_closure_check.build_report(
            repo_root
        ),
        "decision_record_skeleton_check": (
            sandbox_vm_live_poc_decision_record_skeleton_check.build_report(repo_root)
        ),
        "preconditions_ready": {
            "document": "docs/codex/sandbox-vm-live-poc-preconditions-ready-check.md",
            "command": "make sandbox-vm-live-poc-preconditions-ready-check",
            "ready_for_implementation_planning": False,
            "closes_erg_004": False,
        },
        "response_dry_run": sandbox_vm_live_poc_response_dry_run.run_dry_run(repo_root),
        "prerequisite_disposition_dry_run": (
            sandbox_vm_live_poc_prerequisite_disposition_dry_run.build_report(repo_root)
        ),
        "enterprise_external_review_queue_check": (
            enterprise_external_review_queue_check.build_report(repo_root)
        ),
    }
    reports["shell_commands"] = (
        _run_shell_commands(repo_root)
        if run_commands
        else [
            {
                "command": " ".join(command),
                "returncode": 0,
                "stdout_tail": "command execution skipped for fixture/test packet generation",
                "stderr_tail": "",
            }
            for command in _shell_commands()
        ]
    )
    return reports


def _command_evidence(reports: dict[str, Any]) -> str:
    payload = json.dumps(reports, indent=2, sort_keys=True)
    return f"# Response Kit Evidence\n\n```json\n{payload}\n```\n"


def _run_shell_commands(repo_root: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for command in _shell_commands():
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
            raise SandboxVmLivePocResponseKitError(
                f"command failed while building response kit: {' '.join(command)}"
            )
    return results


def _shell_commands() -> list[list[str]]:
    return [
        ["make", "sandbox-vm-live-poc-external-response-intake-check"],
        ["make", "sandbox-vm-live-poc-preconditions-ready-check"],
        ["make", "sandbox-vm-live-poc-decision-closure-check"],
        ["make", "sandbox-vm-live-poc-decision-record-skeleton-check"],
        ["make", "sandbox-vm-live-poc-response-dry-run"],
        ["make", "sandbox-vm-live-poc-prerequisite-disposition-dry-run"],
        ["make", "enterprise-external-review-queue-check"],
    ]


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


def _artifact_hashes_match_files(*, output_dir: Path, hashes: dict[str, Any]) -> bool:
    artifacts = hashes.get("artifacts")
    if not isinstance(artifacts, list):
        return False
    for entry in artifacts:
        if not isinstance(entry, dict):
            return False
        path = entry.get("path")
        sha256 = entry.get("sha256")
        byte_count = entry.get("bytes")
        if not isinstance(path, str):
            return False
        if not isinstance(sha256, str) or not sha256.startswith("sha256:"):
            return False
        if not isinstance(byte_count, int) or byte_count <= 0:
            return False
        artifact_path = output_dir / path
        if not artifact_path.exists() or not artifact_path.is_file():
            return False
        data = artifact_path.read_bytes()
        if sha256 != "sha256:" + hashlib.sha256(data).hexdigest():
            return False
        if byte_count != len(data):
            return False
    return True


def _require_project_root(repo_root: Path) -> None:
    missing = [str(marker) for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        raise SandboxVmLivePocResponseKitError(
            "not an Ithildin repo root; missing: " + ", ".join(missing)
        )


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM live POC response kit check",
        f"valid: {str(report['valid']).lower()}",
        f"output_dir: {report['output_dir']}",
        f"artifact_count: {report['artifact_count']}",
        f"artifact_hashes_match_files: {str(report['artifact_hashes_match_files']).lower()}",
        f"tool_count: {report['tool_count']}",
        f"erg_003_status: {report['erg_003_status']}",
        "erg_003_disposition_recorded: "
        f"{str(report['erg_003_disposition_recorded']).lower()}",
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
        f"network_expansion_allowed: {str(report['network_expansion_allowed']).lower()}",
        "api_mcp_profile_loading_allowed: "
        f"{str(report['api_mcp_profile_loading_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"erg_004_closed: {str(report['erg_004_closed']).lower()}",
        f"decision_record_recorded: {str(report['decision_record_recorded']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

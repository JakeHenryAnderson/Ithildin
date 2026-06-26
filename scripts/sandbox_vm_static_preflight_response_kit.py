"""Build a reviewer-response kit for ERG-003 static sandbox/VM preflight."""

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
    sandbox_vm_static_preflight_disposition_closure_check,
    sandbox_vm_static_preflight_external_response_intake_check,
    sandbox_vm_static_preflight_response_application_record_check,
    sandbox_vm_static_preflight_response_dry_run,
    sandbox_vm_static_preflight_triage_update_check,
)

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/sandbox-vm-static-preflight-response-kit")
HASH_MANIFEST = "sandbox-vm-static-preflight-response-kit-artifact-hashes.json"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
ARTIFACTS = [
    "00_SANDBOX_VM_STATIC_PREFLIGHT_RESPONSE_KIT_INDEX.md",
    "01_SANDBOX_VM_STATIC_PREFLIGHT_RESPONSE_INTAKE_GUIDE.md",
    "02_SANDBOX_VM_STATIC_PREFLIGHT_NORMALIZED_RESPONSE_EXAMPLES.md",
    "03_SANDBOX_VM_STATIC_PREFLIGHT_CLOSURE_TRIAGE_COMMANDS.md",
    "04_SANDBOX_VM_STATIC_PREFLIGHT_QUEUE_AND_BOUNDARY_STATUS.md",
    "05_SANDBOX_VM_STATIC_PREFLIGHT_RESPONSE_KIT_EVIDENCE.md",
]


class SandboxVmStaticPreflightResponseKitError(RuntimeError):
    """Raised when the response kit cannot be built."""


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
    except SandboxVmStaticPreflightResponseKitError as exc:
        print(f"sandbox/VM static preflight response kit failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built sandbox/VM static preflight response kit at {output_dir}")
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
    live_preconditions = _read(repo_root / "docs/codex/sandbox-vm-live-poc-preconditions-map.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "sandbox-vm-static-preflight-response-kit"
        try:
            build_kit(
                repo_root=repo_root,
                output_dir=output_dir,
                allow_dirty=True,
                run_commands=False,
            )
        except SandboxVmStaticPreflightResponseKitError as exc:
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
        failures.append("response kit missing artifacts: " + ", ".join(sorted(missing)))
    hashed = {entry["path"] for entry in hashes.get("artifacts", [])}
    if HASH_MANIFEST in hashed:
        failures.append("hash manifest must not hash itself")
    if set(ARTIFACTS) - hashed:
        failures.append("artifact hashes do not cover generated markdown files")

    index = contents.get("00_SANDBOX_VM_STATIC_PREFLIGHT_RESPONSE_KIT_INDEX.md", "")
    guide = contents.get("01_SANDBOX_VM_STATIC_PREFLIGHT_RESPONSE_INTAKE_GUIDE.md", "")
    examples = contents.get("02_SANDBOX_VM_STATIC_PREFLIGHT_NORMALIZED_RESPONSE_EXAMPLES.md", "")
    commands = contents.get("03_SANDBOX_VM_STATIC_PREFLIGHT_CLOSURE_TRIAGE_COMMANDS.md", "")
    boundary = contents.get("04_SANDBOX_VM_STATIC_PREFLIGHT_QUEUE_AND_BOUNDARY_STATUS.md", "")
    evidence = contents.get("05_SANDBOX_VM_STATIC_PREFLIGHT_RESPONSE_KIT_EVIDENCE.md", "")

    for phrase in [
        "Tool count remains `24`",
        "What This Kit Does Not Prove",
        "does not close `ERG-003`",
        "does not unblock `ERG-004`",
        "does not approve live VM/container inspection",
    ]:
        if phrase not in index:
            failures.append(f"response kit index is missing phrase: {phrase}")
    for phrase in [
        "Finding namespace: `EXT-SVP-###`",
        "var/review-runs/sandbox-vm-static-preflight/normalized-response.json",
        "sandbox-vm-static-preflight-external-response-intake.md",
        "Only a later committed triage update may move `ERG-003`",
    ]:
        if phrase not in guide:
            failures.append(f"response intake guide is missing phrase: {phrase}")
    for phrase in [
        '"response_type": "ithildin.external_review.normalized_response"',
        '"area": "sandbox-vm-static-preflight"',
        '"source_access": "source-level"',
        '"source_access": "packet-only"',
        '"closes_external_review": false',
    ]:
        if phrase not in examples:
            failures.append(f"normalized response examples are missing phrase: {phrase}")
    for phrase in [
        "make sandbox-vm-static-preflight-disposition-closure-check",
        "make sandbox-vm-static-preflight-disposition-record-skeleton-check",
        "make sandbox-vm-static-preflight-response-application-record-check",
        "make sandbox-vm-static-preflight-response-dry-run",
        "make sandbox-vm-static-preflight-triage-update-check",
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
        "local model invocation",
        "sandbox orchestration",
        "trusted-host promotion",
    ]:
        if phrase not in boundary:
            failures.append(f"boundary status is missing phrase: {phrase}")
    for phrase in [
        '"response_kit_boundary"',
        '"runtime_changes_allowed": false',
        '"live_vm_inspection_allowed": false',
        '"sandbox_orchestration_allowed": false',
        '"local_model_invocation_allowed": false',
        '"erg_004_unblocked": false',
        '"closes_erg_003": false',
        '"response_dry_run"',
        '"valid_response_accepts": true',
    ]:
        if phrase not in evidence:
            failures.append(f"response kit evidence is missing phrase: {phrase}")

    target = "sandbox-vm-static-preflight-response-kit"
    check_target = f"{target}-check"
    for make_target in [f"{target}:", f"{check_target}:"]:
        if make_target not in makefile:
            failures.append(f"Make target is missing: {make_target.rstrip(':')}")
    if check_target not in release_check_body:
        failures.append(f"{check_target} missing from release-check")
    if f"$(MAKE) {target}" not in review_candidate_body:
        failures.append(f"{target} missing from review-candidate")
    if check_target not in release_guardrails:
        failures.append(f"release guardrails do not require {check_target}")
    if f"$(MAKE) {target}" not in release_guardrails:
        failures.append(f"release guardrails do not require review-candidate {target}")
    doc_rel = "docs/codex/sandbox-vm-static-preflight-response-kit.md"
    if doc_rel not in docs_site:
        failures.append("response kit doc is missing from docs-site inputs")
    if doc_rel not in review_docs:
        failures.append("response kit doc is missing from review docs")
    if "Sandbox/VM Static Preflight Response Kit" not in review_index:
        failures.append("review-docs index is missing response kit entry")
    if f"make {target}" not in readme:
        failures.append("README is missing response kit command")
    for text, source in [
        (readme, "README"),
        (runway, "enterprise runway"),
        (gap_matrix, "enterprise gap matrix"),
        (queue, "enterprise external-review queue"),
        (decision_register, "post-RC decision register"),
        (live_preconditions, "live POC preconditions map"),
    ]:
        if "sandbox-vm-static-preflight-response-kit" not in text:
            failures.append(f"{source} is missing response kit pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "output_dir": str(DEFAULT_OUTPUT_DIR),
        "artifact_count": len(expected),
        "tool_count": 24,
        "erg_003_status": "external_review_required",
        "erg_004_status": "blocked",
        "recommended_next_review": "ERG-003",
        "runtime_changes_allowed": False,
        "live_vm_inspection_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "network_expansion_allowed": False,
        "api_mcp_profile_loading_allowed": False,
        "new_power_classes_allowed": False,
        "erg_004_unblocked": False,
        "closes_erg_003": False,
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
        raise SandboxVmStaticPreflightResponseKitError(
            "working tree is dirty; commit before response-kit handoff"
        )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    command_reports = _build_command_reports(repo_root, run_commands=run_commands)
    files = {
        "00_SANDBOX_VM_STATIC_PREFLIGHT_RESPONSE_KIT_INDEX.md": _index(commit, dirty),
        "01_SANDBOX_VM_STATIC_PREFLIGHT_RESPONSE_INTAKE_GUIDE.md": _intake_guide(),
        "02_SANDBOX_VM_STATIC_PREFLIGHT_NORMALIZED_RESPONSE_EXAMPLES.md": _examples(),
        "03_SANDBOX_VM_STATIC_PREFLIGHT_CLOSURE_TRIAGE_COMMANDS.md": _commands(),
        "04_SANDBOX_VM_STATIC_PREFLIGHT_QUEUE_AND_BOUNDARY_STATUS.md": _docs_bundle(
            "Queue And Boundary Status",
            repo_root,
            [
                "docs/codex/enterprise-external-review-queue.md",
                "docs/codex/enterprise-readiness-gap-matrix.md",
                "docs/codex/sandbox-vm-static-preflight-disposition-record-skeleton.md",
                "docs/codex/sandbox-vm-static-preflight-response-application-record.md",
                "docs/codex/sandbox-vm-live-poc-preconditions-map.md",
                "docs/codex/post-rc-decision-register.md",
            ],
        ),
        "05_SANDBOX_VM_STATIC_PREFLIGHT_RESPONSE_KIT_EVIDENCE.md": _command_evidence(
            command_reports
        ),
    }
    for name, content in files.items():
        (output_dir / name).write_text(content, encoding="utf-8")
    _write_hashes(output_dir)
    return output_dir


def _index(commit: str, dirty: bool) -> str:
    boundary = (
        "This response kit does not prove external review happened, does not close `ERG-003`, "
        "does not unblock `ERG-004`, and does not approve live VM/container inspection, "
        "VM/container lifecycle management, sandbox orchestration, Mission Control runtime "
        "behavior, local model invocation, trusted-host promotion, network expansion, API/MCP "
        "profile loading, new governed tool powers, production identity, runtime Postgres, "
        "hosted telemetry, remote MCP, SIEM delivery, compliance automation, or "
        "public/security-product positioning."
    )
    return f"""# Sandbox/VM Static Preflight Response Kit

Status: response-intake kit for `ERG-003` after external/source review.

Reviewed commit for kit generation: `{commit}`
Dirty state when generated: `{str(dirty).lower()}`

Tool count remains `24`.

Current `ERG-003` status: `external_review_required`.

Current `ERG-004` status: `blocked`.

## Reading Order

1. `01_SANDBOX_VM_STATIC_PREFLIGHT_RESPONSE_INTAKE_GUIDE.md`
2. `02_SANDBOX_VM_STATIC_PREFLIGHT_NORMALIZED_RESPONSE_EXAMPLES.md`
3. `03_SANDBOX_VM_STATIC_PREFLIGHT_CLOSURE_TRIAGE_COMMANDS.md`
4. `04_SANDBOX_VM_STATIC_PREFLIGHT_QUEUE_AND_BOUNDARY_STATUS.md`
5. `05_SANDBOX_VM_STATIC_PREFLIGHT_RESPONSE_KIT_EVIDENCE.md`
6. `sandbox-vm-static-preflight-response-kit-artifact-hashes.json`

## What This Kit Does Not Prove

{boundary}
"""


def _intake_guide() -> str:
    return """# Response Intake Guide

Finding namespace: `EXT-SVP-###`

Reviewed area for normalization: `sandbox-vm-static-preflight`

Response target:

```text
var/review-runs/sandbox-vm-static-preflight/normalized-response.json
```

Start from:

- `sandbox-vm-static-preflight-external-response-intake.md`
- `sandbox-vm-static-preflight-disposition-closure-gate.md`
- `sandbox-vm-static-preflight-response-application-record.md`
- `sandbox-vm-static-preflight-response-dry-run.md`
- `sandbox-vm-static-preflight-triage-update.md`

Only a later committed triage update may move `ERG-003`, and only after the closure gate reports
`closure_ready: true`. A response may support static preflight local-preview closure only. It must
not approve live VM/container control, local model invocation, sandbox orchestration, Mission
Control runtime behavior, trusted-host promotion, or API/MCP profile loading.
"""


def _examples() -> str:
    favorable = {
        "response_type": "ithildin.external_review.normalized_response",
        "area": "sandbox-vm-static-preflight",
        "source_access": "source-level",
        "reviewed_packet_hash": "sha256:" + ("0" * 64),
        "can_close_source_rows": True,
        "mutates_findings": False,
        "closes_external_review": False,
        "findings": [],
    }
    unfavorable = {
        "response_type": "ithildin.external_review.normalized_response",
        "area": "sandbox-vm-static-preflight",
        "source_access": "packet-only",
        "reviewed_packet_hash": "sha256:" + ("0" * 64),
        "can_close_source_rows": False,
        "mutates_findings": False,
        "closes_external_review": False,
        "findings": [
            {
                "finding_id": "EXT-SVP-001",
                "severity": "high",
                "area": "sandbox-vm-static-preflight",
                "affected_files_functions": "scripts/sandbox_vm_static_preflight.py",
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
make sandbox-vm-static-preflight-disposition-closure-check
make sandbox-vm-static-preflight-disposition-record-skeleton-check
make sandbox-vm-static-preflight-response-application-record-check
make sandbox-vm-static-preflight-response-dry-run
make sandbox-vm-static-preflight-triage-update-check
make enterprise-external-review-queue-check
```

If and only if the closure gate reports `closure_ready: true`, perform a separate committed triage
update following `sandbox-vm-static-preflight-triage-update.md`, then run:

```sh
make review-run-manifest-refresh
make release-check
make review-candidate
```

If the response is absent, malformed, packet-only, docs-only, critical/high, or attempts to close
external review directly, keep `ERG-003` as `external_review_required` and keep `ERG-004` blocked.
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
            "live_vm_inspection_allowed": False,
            "mission_control_runtime_allowed": False,
            "local_model_invocation_allowed": False,
            "sandbox_orchestration_allowed": False,
            "trusted_host_promotion_allowed": False,
            "network_expansion_allowed": False,
            "api_mcp_profile_loading_allowed": False,
            "new_power_classes_allowed": False,
            "erg_004_unblocked": False,
            "closes_erg_003": False,
        },
        "external_response_intake_check": (
            sandbox_vm_static_preflight_external_response_intake_check.build_report(repo_root)
        ),
        "disposition_closure_check": (
            sandbox_vm_static_preflight_disposition_closure_check.build_report(repo_root)
        ),
        "response_application_record_check": (
            sandbox_vm_static_preflight_response_application_record_check.build_report(repo_root)
        ),
        "response_dry_run": sandbox_vm_static_preflight_response_dry_run.run_dry_run(
            repo_root
        ),
        "triage_update_check": sandbox_vm_static_preflight_triage_update_check.build_report(
            repo_root
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
            raise SandboxVmStaticPreflightResponseKitError(
                f"command failed while building response kit: {' '.join(command)}"
            )
    return results


def _shell_commands() -> list[list[str]]:
    return [
        ["make", "sandbox-vm-static-preflight-external-response-intake-check"],
        ["make", "sandbox-vm-static-preflight-disposition-closure-check"],
        ["make", "sandbox-vm-static-preflight-response-application-record-check"],
        ["make", "sandbox-vm-static-preflight-response-dry-run"],
        ["make", "sandbox-vm-static-preflight-triage-update-check"],
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


def _require_project_root(repo_root: Path) -> None:
    missing = [str(marker) for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        raise SandboxVmStaticPreflightResponseKitError(
            "not an Ithildin repo root; missing: " + ", ".join(missing)
        )


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM static preflight response kit check",
        f"valid: {str(report['valid']).lower()}",
        f"output_dir: {report['output_dir']}",
        f"artifact_count: {report['artifact_count']}",
        f"tool_count: {report['tool_count']}",
        f"erg_003_status: {report['erg_003_status']}",
        f"erg_004_status: {report['erg_004_status']}",
        f"recommended_next_review: {report['recommended_next_review']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
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
        f"erg_004_unblocked: {str(report['erg_004_unblocked']).lower()}",
        f"closes_erg_003: {str(report['closes_erg_003']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

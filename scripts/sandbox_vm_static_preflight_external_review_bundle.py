"""Build a reviewer-friendly ERG-003 sandbox/VM static preflight launch bundle."""

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
    sandbox_vm_static_preflight_disposition_packet,
    sandbox_vm_static_preflight_disposition_plan_check,
    sandbox_vm_static_preflight_external_response_intake_check,
    sandbox_vm_static_preflight_response_dry_run,
    sandbox_vm_static_preflight_reviewer_reproduction_map_check,
    sandbox_vm_static_preflight_source_review_packet,
    sandbox_vm_static_preflight_triage_update_check,
)

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/sandbox-vm-static-preflight-external-review")
HASH_MANIFEST = "sandbox-vm-static-preflight-external-review-artifact-hashes.json"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
ARTIFACTS = [
    "00_SANDBOX_VM_STATIC_PREFLIGHT_EXTERNAL_REVIEW_INDEX.md",
    "01_SANDBOX_VM_STATIC_PREFLIGHT_EXTERNAL_REVIEW_PROMPT.md",
    "02_SANDBOX_VM_STATIC_PREFLIGHT_SOURCE_PACKET.md",
    "03_SANDBOX_VM_STATIC_PREFLIGHT_DISPOSITION_PACKET.md",
    "04_SANDBOX_VM_STATIC_PREFLIGHT_IMPLEMENTATION_CONTRACTS.md",
    "05_SANDBOX_VM_STATIC_PREFLIGHT_FIXTURES_NEGATIVES.md",
    "06_SANDBOX_VM_STATIC_PREFLIGHT_RESPONSE_CLOSURE_TRIAGE.md",
    "07_SANDBOX_VM_STATIC_PREFLIGHT_REPRODUCTION_QUEUE_STATUS.md",
    "08_SANDBOX_VM_STATIC_PREFLIGHT_COMMAND_EVIDENCE.md",
]


class SandboxVmStaticPreflightExternalReviewBundleError(RuntimeError):
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
    except SandboxVmStaticPreflightExternalReviewBundleError as exc:
        print(f"sandbox/VM static preflight external-review bundle failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built sandbox/VM static preflight external-review bundle at {output_dir}")
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
        output_dir = Path(tmp) / "sandbox-vm-static-preflight-external-review"
        try:
            build_bundle(
                repo_root=repo_root,
                output_dir=output_dir,
                allow_dirty=True,
                run_commands=False,
            )
        except SandboxVmStaticPreflightExternalReviewBundleError as exc:
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

    prompt = contents.get("01_SANDBOX_VM_STATIC_PREFLIGHT_EXTERNAL_REVIEW_PROMPT.md", "")
    index = contents.get("00_SANDBOX_VM_STATIC_PREFLIGHT_EXTERNAL_REVIEW_INDEX.md", "")
    evidence = contents.get("08_SANDBOX_VM_STATIC_PREFLIGHT_COMMAND_EVIDENCE.md", "")
    response = contents.get("06_SANDBOX_VM_STATIC_PREFLIGHT_RESPONSE_CLOSURE_TRIAGE.md", "")
    reproduction = contents.get("07_SANDBOX_VM_STATIC_PREFLIGHT_REPRODUCTION_QUEUE_STATUS.md", "")

    for phrase in [
        "Finding namespace: `EXT-SVP-###`",
        "Can `ERG-003` move from `external_review_required`",
        "Do not approve live VM/container inspection",
        "Do not approve local model invocation",
    ]:
        if phrase not in prompt:
            failures.append(f"external-review prompt is missing phrase: {phrase}")
    for phrase in [
        "Tool count remains `24`",
        "What This Bundle Does Not Prove",
        "does not close `ERG-003`",
        "approve live VM/container inspection",
    ]:
        if phrase not in index:
            failures.append(f"external-review index is missing phrase: {phrase}")
    for phrase in [
        "sandbox-vm-static-preflight-external-response-intake.md",
        "sandbox-vm-static-preflight-disposition-closure-gate.md",
        "sandbox-vm-static-preflight-disposition-record-skeleton.md",
        "sandbox-vm-static-preflight-response-dry-run.md",
        "sandbox-vm-static-preflight-triage-update.md",
    ]:
        if phrase not in response:
            failures.append(f"response/closure/triage bundle is missing phrase: {phrase}")
    for phrase in [
        "enterprise-external-review-queue.md",
        "Recommended next review",
        "sandbox-vm-static-preflight-reviewer-reproduction-map.md",
    ]:
        if phrase not in reproduction:
            failures.append(f"reproduction/queue bundle is missing phrase: {phrase}")
    for phrase in [
        '"runtime_changes_allowed": false',
        '"live_vm_inspection_allowed": false',
        '"mission_control_runtime_allowed": false',
        '"local_model_invocation_allowed": false',
        '"sandbox_orchestration_allowed": false',
        '"trusted_host_promotion_allowed": false',
        '"new_power_classes_allowed": false',
        '"closes_erg_003": false',
        '"response_dry_run"',
        '"valid_response_accepts": true',
    ]:
        if phrase not in evidence:
            failures.append(f"command evidence is missing phrase: {phrase}")

    target = "sandbox-vm-static-preflight-external-review-bundle"
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
    doc_rel = "docs/codex/sandbox-vm-static-preflight-external-review-bundle.md"
    if doc_rel not in docs_site:
        failures.append("external-review bundle doc is missing from docs-site inputs")
    if doc_rel not in review_docs:
        failures.append("external-review bundle doc is missing from review docs")
    if "Sandbox/VM Static Preflight External Review Bundle" not in review_index:
        failures.append("review-docs index is missing external-review bundle entry")
    if f"make {target}" not in readme:
        failures.append("README is missing external-review bundle command")
    for text, source in [
        (readme, "README"),
        (runway, "enterprise runway"),
        (gap_matrix, "enterprise gap matrix"),
        (queue, "enterprise external-review queue"),
    ]:
        if "sandbox-vm-static-preflight-external-review-bundle" not in text:
            failures.append(f"{source} is missing external-review bundle pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "output_dir": str(DEFAULT_OUTPUT_DIR),
        "artifact_count": len(expected),
        "tool_count": 24,
        "erg_003_status": "external_review_required",
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
        "public_security_product_positioning_allowed": False,
        "closes_erg_003": False,
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
        raise SandboxVmStaticPreflightExternalReviewBundleError(
            "working tree is dirty; commit before external-review bundle handoff"
        )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        source_dir = tmp_root / "source"
        disposition_dir = tmp_root / "disposition"
        sandbox_vm_static_preflight_source_review_packet.build_packet(
            repo_root=repo_root,
            output_dir=source_dir,
            allow_dirty=True,
            run_commands=run_commands,
        )
        sandbox_vm_static_preflight_disposition_packet.build_packet(
            repo_root=repo_root,
            output_dir=disposition_dir,
            allow_dirty=True,
            run_commands=run_commands,
        )
        command_reports = _build_command_reports(repo_root, run_commands=run_commands)

        files = {
            "00_SANDBOX_VM_STATIC_PREFLIGHT_EXTERNAL_REVIEW_INDEX.md": _index(commit, dirty),
            "01_SANDBOX_VM_STATIC_PREFLIGHT_EXTERNAL_REVIEW_PROMPT.md": _prompt(commit),
            "02_SANDBOX_VM_STATIC_PREFLIGHT_SOURCE_PACKET.md": _packet_bundle(
                "Source Review Packet Contents", source_dir
            ),
            "03_SANDBOX_VM_STATIC_PREFLIGHT_DISPOSITION_PACKET.md": _packet_bundle(
                "Disposition Packet Contents", disposition_dir
            ),
            "04_SANDBOX_VM_STATIC_PREFLIGHT_IMPLEMENTATION_CONTRACTS.md": _docs_bundle(
                "Implementation And Contracts",
                repo_root,
                [
                    "docs/codex/sandbox-vm-worker-boundary-charter.md",
                    "docs/codex/sandbox-vm-profile-contract.md",
                    "docs/codex/sandbox-vm-preflight-contract.md",
                    "docs/codex/sandbox-vm-static-profile-preflight-plan.md",
                    "docs/codex/sandbox-vm-static-preflight-implementation-decision.md",
                    "docs/codex/sandbox-vm-static-preflight-source-review.md",
                    "docs/codex/v3-sandbox-vm-static-preflight-internal-review.md",
                ],
            ),
            "05_SANDBOX_VM_STATIC_PREFLIGHT_FIXTURES_NEGATIVES.md": _docs_bundle(
                "Fixtures And Negative Evidence",
                repo_root,
                [
                    "docs/codex/sandbox-vm-static-profile-fixture-contract.md",
                    "docs/codex/fixtures/sandbox-vm-static-profile.local-preview.example.json",
                    "docs/codex/sandbox-vm-static-profile-negative-fixtures.md",
                    "docs/codex/findings/xh-sandbox-preflight-001-safe-label-suppression.md",
                ],
            ),
            "06_SANDBOX_VM_STATIC_PREFLIGHT_RESPONSE_CLOSURE_TRIAGE.md": _docs_bundle(
                "Response Intake, Closure Gate, And Triage",
                repo_root,
                [
                    "docs/codex/sandbox-vm-static-preflight-external-response-intake.md",
                    "docs/codex/sandbox-vm-static-preflight-disposition-closure-gate.md",
                    "docs/codex/sandbox-vm-static-preflight-disposition-record-skeleton.md",
                    "docs/codex/sandbox-vm-static-preflight-response-dry-run.md",
                    "docs/codex/sandbox-vm-static-preflight-triage-update.md",
                ],
            ),
            "07_SANDBOX_VM_STATIC_PREFLIGHT_REPRODUCTION_QUEUE_STATUS.md": _docs_bundle(
                "Reproduction And Queue Status",
                repo_root,
                [
                    "docs/codex/sandbox-vm-static-preflight-reviewer-reproduction-map.md",
                    "docs/codex/enterprise-external-review-queue.md",
                    "docs/codex/enterprise-readiness-gap-matrix.md",
                    "docs/codex/sandbox-vm-live-poc-preconditions-map.md",
                ],
            ),
            "08_SANDBOX_VM_STATIC_PREFLIGHT_COMMAND_EVIDENCE.md": _command_evidence(
                command_reports
            ),
        }

    for name, content in files.items():
        (output_dir / name).write_text(content, encoding="utf-8")
    _write_hashes(output_dir)
    return output_dir


def _index(commit: str, dirty: bool) -> str:
    return f"""# Sandbox/VM Static Preflight External Review Bundle

Status: reviewer launch bundle for `ERG-003`.

Reviewed commit: `{commit}`
Dirty state when generated: `{str(dirty).lower()}`

Tool count remains `24`.

Current selected capability: `not selected`.

Current `ERG-003` status before reviewer disposition: `external_review_required`.

Recommended next review: `ERG-003` static sandbox/VM preflight disposition.

## Reading Order

1. `01_SANDBOX_VM_STATIC_PREFLIGHT_EXTERNAL_REVIEW_PROMPT.md`
2. `02_SANDBOX_VM_STATIC_PREFLIGHT_SOURCE_PACKET.md`
3. `03_SANDBOX_VM_STATIC_PREFLIGHT_DISPOSITION_PACKET.md`
4. `04_SANDBOX_VM_STATIC_PREFLIGHT_IMPLEMENTATION_CONTRACTS.md`
5. `05_SANDBOX_VM_STATIC_PREFLIGHT_FIXTURES_NEGATIVES.md`
6. `06_SANDBOX_VM_STATIC_PREFLIGHT_RESPONSE_CLOSURE_TRIAGE.md`
7. `07_SANDBOX_VM_STATIC_PREFLIGHT_REPRODUCTION_QUEUE_STATUS.md`
8. `08_SANDBOX_VM_STATIC_PREFLIGHT_COMMAND_EVIDENCE.md`
9. `sandbox-vm-static-preflight-external-review-artifact-hashes.json`

## What This Bundle Does Not Prove

This bundle does not prove that external review has happened, does not close `ERG-003`, and does not
approve live VM/container inspection, VM/container lifecycle management, sandbox orchestration,
Mission Control runtime behavior, local model invocation, trusted-host promotion, network expansion,
API/MCP profile loading, new governed tool powers, production identity, runtime Postgres, hosted
telemetry, remote MCP, SIEM delivery, compliance automation, or public/security-product positioning.

This bundle does not approve live VM/container inspection.
"""


def _prompt(commit: str) -> str:
    return f"""# Sandbox/VM Static Preflight External Review Prompt

You are reviewing Ithildin as an external/source reviewer for `ERG-003` only: the CLI-only
sandbox/VM static profile preflight lane.

Reviewed commit: `{commit}`

Finding namespace: `EXT-SVP-###`

## Scope

Review the attached source-review packet, disposition packet, contracts, fixtures, negative
fixtures, reproduction map, closure/triage docs, and command evidence.

Please answer:

1. Did you inspect the static preflight source-review packet and the source/files it names?
2. Does the CLI-only fixture runner stay within the approved boundary?
3. Are the static profile fixture contract, negative fixtures, safe-label expectations, and
   safe-error expectations sufficient for local-preview planning evidence?
4. Does `XH-SANDBOX-PREFLIGHT-001` appear fixed for the local-preview fixture lane?
5. Are there any critical/high findings?
6. Does the response/closure/triage path correctly keep `ERG-003` open until a later committed
   triage update records real source-level evidence?
7. Can `ERG-003` move from `external_review_required` to
   `closed_local_preview_static_preflight` for the static preflight lane only?

Do not approve live VM/container inspection. Do not approve VM/container lifecycle management. Do
not approve sandbox orchestration. Do not approve local model invocation. Do not approve Mission
Control runtime behavior. Do not approve trusted-host promotion. Do not approve public/security
product positioning.

Use this finding namespace for actionable findings: `EXT-SVP-###`.

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
    source_packet_report = sandbox_vm_static_preflight_source_review_packet.build_check_report(
        repo_root
    )
    disposition_packet_report = (
        sandbox_vm_static_preflight_disposition_packet.build_check_report(repo_root)
    )
    disposition_plan_report = sandbox_vm_static_preflight_disposition_plan_check.build_report(
        repo_root
    )
    response_intake_report = (
        sandbox_vm_static_preflight_external_response_intake_check.build_report(repo_root)
    )
    closure_gate_report = sandbox_vm_static_preflight_disposition_closure_check.build_report(
        repo_root
    )
    reproduction_map_report = (
        sandbox_vm_static_preflight_reviewer_reproduction_map_check.build_report(repo_root)
    )
    enterprise_queue_report = enterprise_external_review_queue_check.build_report(repo_root)
    reports: dict[str, Any] = {
        "source_packet_check": source_packet_report,
        "disposition_packet_check": disposition_packet_report,
        "disposition_plan_check": disposition_plan_report,
        "external_response_intake_check": response_intake_report,
        "closure_gate_check": closure_gate_report,
        "response_dry_run": sandbox_vm_static_preflight_response_dry_run.run_dry_run(repo_root),
        "triage_update_check": sandbox_vm_static_preflight_triage_update_check.build_report(
            repo_root
        ),
        "reproduction_map_check": reproduction_map_report,
        "enterprise_external_review_queue_check": enterprise_queue_report,
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
        ["make", "sandbox-vm-static-preflight-source-review-packet-check"],
        ["make", "sandbox-vm-static-preflight-disposition-packet-check"],
        ["make", "sandbox-vm-static-preflight-disposition-closure-check"],
        ["make", "sandbox-vm-static-preflight-response-dry-run"],
        ["make", "sandbox-vm-static-preflight-triage-update-check"],
        ["make", "sandbox-vm-static-preflight-reviewer-reproduction-map-check"],
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
            raise SandboxVmStaticPreflightExternalReviewBundleError(
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
        raise SandboxVmStaticPreflightExternalReviewBundleError(
            "not an Ithildin repo root; missing: " + ", ".join(missing)
        )


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _fence_lang(path: Path) -> str:
    return "json" if path.suffix.lower() == ".json" else "markdown"


def render_check_report(report: dict[str, Any]) -> str:
    mission_control_allowed = str(report["mission_control_runtime_allowed"]).lower()
    local_model_allowed = str(report["local_model_invocation_allowed"]).lower()
    sandbox_orchestration_allowed = str(report["sandbox_orchestration_allowed"]).lower()
    trusted_host_allowed = str(report["trusted_host_promotion_allowed"]).lower()
    lines = [
        "Ithildin sandbox/VM static preflight external-review bundle check",
        f"valid: {str(report['valid']).lower()}",
        f"output_dir: {report['output_dir']}",
        f"artifact_count: {report['artifact_count']}",
        f"tool_count: {report['tool_count']}",
        f"erg_003_status: {report['erg_003_status']}",
        f"recommended_next_review: {report['recommended_next_review']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        f"mission_control_runtime_allowed: {mission_control_allowed}",
        f"local_model_invocation_allowed: {local_model_allowed}",
        f"sandbox_orchestration_allowed: {sandbox_orchestration_allowed}",
        f"trusted_host_promotion_allowed: {trusted_host_allowed}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"closes_erg_003: {str(report['closes_erg_003']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

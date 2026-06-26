"""Build a sandbox/VM static preflight external-disposition packet."""

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
    sandbox_vm_static_preflight_disposition_plan_check,
    sandbox_vm_static_preflight_external_response_intake_check,
    sandbox_vm_static_preflight_response_dry_run,
    sandbox_vm_static_preflight_source_review_packet,
)

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/sandbox-vm-static-preflight-disposition")
HASH_MANIFEST = "sandbox-vm-static-preflight-disposition-artifact-hashes.json"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
DISPOSITION_DOCS = [
    Path("docs/codex/sandbox-vm-static-preflight-disposition-plan.md"),
    Path("docs/codex/sandbox-vm-static-preflight-external-response-intake.md"),
    Path("docs/codex/sandbox-vm-static-preflight-response-dry-run.md"),
    Path("docs/codex/sandbox-vm-static-preflight-disposition-packet.md"),
]
SOURCE_REVIEW_DOCS = [
    Path("docs/codex/sandbox-vm-static-preflight-source-review.md"),
    Path("docs/codex/v3-sandbox-vm-static-preflight-internal-review.md"),
    Path("docs/codex/findings/xh-sandbox-preflight-001-safe-label-suppression.md"),
    Path("docs/codex/enterprise-readiness-gap-matrix.md"),
    Path("docs/codex/enterprise-readiness-runway.md"),
]
COMMANDS = [
    ["make", "sandbox-vm-static-preflight-source-review-packet-check"],
    ["make", "sandbox-vm-static-preflight-disposition-plan-check"],
    ["make", "sandbox-vm-static-preflight-external-response-intake-check"],
    ["make", "sandbox-vm-static-preflight-response-dry-run"],
    ["make", "external-findings-intake-dry-run"],
    ["make", "no-new-powers-guardrail"],
    ["make", "tool-surface-invariant-gate"],
]
FINDING_TABLE = "\n".join(
    [
        "| Finding ID | Severity | Area | Affected files/functions | "
        "Blocking status | Disposition | Recommended fix |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        "| EXT-SVP-### | critical/high/medium/low/informational | "
        "sandbox-vm-static-preflight | path/function | "
        "blocking/should-fix/later/advisory | open | fix summary |",
    ]
)


class SandboxVmStaticPreflightDispositionPacketError(RuntimeError):
    """Raised when the disposition packet cannot be built."""


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
        output_dir = build_packet(
            repo_root=Path.cwd().resolve(),
            output_dir=args.output_dir,
            allow_dirty=args.allow_dirty,
            run_commands=not args.skip_commands,
        )
    except SandboxVmStaticPreflightDispositionPacketError as exc:
        print(f"sandbox/VM static preflight disposition packet failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built sandbox/VM static preflight disposition packet at {output_dir}")
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
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "sandbox-vm-static-preflight-disposition"
        try:
            build_packet(
                repo_root=repo_root,
                output_dir=output_dir,
                allow_dirty=True,
                run_commands=False,
            )
        except SandboxVmStaticPreflightDispositionPacketError as exc:
            failures.append(str(exc))
            artifact_names: set[str] = set()
            hashes: dict[str, Any] = {"artifacts": []}
            prompt = ""
            index = ""
            evidence = ""
        else:
            artifact_names = {path.name for path in output_dir.iterdir()}
            hashes = json.loads((output_dir / HASH_MANIFEST).read_text(encoding="utf-8"))
            prompt = (
                output_dir / "01_SANDBOX_VM_STATIC_PREFLIGHT_DISPOSITION_PROMPT.md"
            ).read_text(encoding="utf-8")
            index = (
                output_dir / "00_SANDBOX_VM_STATIC_PREFLIGHT_DISPOSITION_INDEX.md"
            ).read_text(encoding="utf-8")
            evidence = (
                output_dir / "04_SANDBOX_VM_STATIC_PREFLIGHT_DISPOSITION_COMMAND_EVIDENCE.md"
            ).read_text(encoding="utf-8")

    expected = {
        "00_SANDBOX_VM_STATIC_PREFLIGHT_DISPOSITION_INDEX.md",
        "01_SANDBOX_VM_STATIC_PREFLIGHT_DISPOSITION_PROMPT.md",
        "02_SANDBOX_VM_STATIC_PREFLIGHT_DISPOSITION_AND_INTAKE.md",
        "03_SANDBOX_VM_STATIC_PREFLIGHT_SOURCE_REVIEW_POINTERS.md",
        "04_SANDBOX_VM_STATIC_PREFLIGHT_DISPOSITION_COMMAND_EVIDENCE.md",
        HASH_MANIFEST,
    }
    missing = expected - artifact_names
    if missing:
        failures.append("packet missing artifacts: " + ", ".join(sorted(missing)))
    hashed = {entry["path"] for entry in hashes.get("artifacts", [])}
    if HASH_MANIFEST in hashed:
        failures.append("hash manifest must not hash itself")
    if expected - {HASH_MANIFEST} - hashed:
        failures.append("artifact hashes do not cover generated markdown files")
    for phrase in [
        "Finding namespace: `EXT-SVP-###`",
        "closed_local_preview_static_preflight",
        "external_review_required",
        "Did the reviewer inspect the static preflight source-review packet",
        "Does the response dry run prove absent responses stay not-ready",
    ]:
        if phrase not in prompt:
            failures.append(f"packet prompt is missing phrase: {phrase}")
    for phrase in [
        "What This Packet Does Not Prove",
        "does not approve live VM/container inspection",
        "does not close `ERG-003`",
    ]:
        if phrase not in index:
            failures.append(f"packet index is missing phrase: {phrase}")
    for phrase in [
        '"runtime_changes_allowed": false',
        '"live_vm_inspection_allowed": false',
        '"mission_control_runtime_allowed": false',
        '"local_model_invocation_allowed": false',
        '"sandbox_orchestration_allowed": false',
        '"trusted_host_promotion_allowed": false',
        '"new_power_classes_allowed": false',
    ]:
        if phrase not in evidence:
            failures.append(f"command evidence is missing boundary flag: {phrase}")
    for phrase in [
        '"response_dry_run"',
        '"absent_response_not_ready": true',
        '"valid_response_accepts": true',
        '"packet_only_rejected": true',
        '"bad_hash_rejected": true',
        '"critical_high_finding_rejected": true',
        '"direct_external_closure_rejected": true',
    ]:
        if phrase not in evidence:
            failures.append(f"command evidence is missing response dry-run evidence: {phrase}")
    for target in [
        "sandbox-vm-static-preflight-disposition-packet:",
        "sandbox-vm-static-preflight-disposition-packet-check:",
    ]:
        if target not in makefile:
            failures.append(f"Make target is missing: {target.rstrip(':')}")
    if "sandbox-vm-static-preflight-disposition-packet-check" not in release_check_body:
        failures.append(
            "sandbox-vm-static-preflight-disposition-packet-check missing from release-check"
        )
    if "$(MAKE) sandbox-vm-static-preflight-disposition-packet" not in review_candidate_body:
        failures.append(
            "sandbox-vm-static-preflight-disposition-packet missing from review-candidate"
        )
    if "sandbox-vm-static-preflight-disposition-packet-check" not in release_guardrails:
        failures.append("release guardrails do not require disposition packet check")
    if "docs/codex/sandbox-vm-static-preflight-disposition-packet.md" not in docs_site:
        failures.append("disposition packet doc is missing from docs-site inputs")
    if "docs/codex/sandbox-vm-static-preflight-disposition-packet.md" not in review_docs:
        failures.append("disposition packet doc is missing from review docs")
    if "Sandbox/VM Static Preflight Disposition Packet" not in review_index:
        failures.append("review-docs index is missing disposition packet entry")
    if "make sandbox-vm-static-preflight-disposition-packet" not in readme:
        failures.append("README is missing disposition packet command")
    if "sandbox-vm-static-preflight-disposition-packet.md" not in readme:
        failures.append("README is missing disposition packet doc")
    if "sandbox-vm-static-preflight-disposition-packet.md" not in runway:
        failures.append("enterprise runway is missing disposition packet pointer")
    if "sandbox-vm-static-preflight-disposition-packet.md" not in gap_matrix:
        failures.append("enterprise gap matrix is missing disposition packet pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "output_dir": str(DEFAULT_OUTPUT_DIR),
        "artifact_count": len(expected),
        "tool_count": 24,
        "erg_003_status": "external_review_required",
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


def build_packet(
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
        raise SandboxVmStaticPreflightDispositionPacketError(
            "working tree is dirty; commit before disposition packet handoff"
        )

    source_packet = sandbox_vm_static_preflight_source_review_packet.build_check_report(repo_root)
    disposition = sandbox_vm_static_preflight_disposition_plan_check.build_report(repo_root)
    intake = sandbox_vm_static_preflight_external_response_intake_check.build_report(repo_root)
    response_dry_run = sandbox_vm_static_preflight_response_dry_run.run_dry_run(repo_root)
    failures = [
        *(f"source-review packet: {failure}" for failure in source_packet["failures"]),
        *(f"disposition plan: {failure}" for failure in disposition["failures"]),
        *(f"external response intake: {failure}" for failure in intake["failures"]),
    ]
    if not response_dry_run["valid"]:
        failures.append("response dry run: report is invalid")
    if failures:
        raise SandboxVmStaticPreflightDispositionPacketError("; ".join(failures))

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context = {
        "commit": commit,
        "dirty": dirty,
        "run_commands": run_commands,
        "source_packet": source_packet,
        "disposition": disposition,
        "intake": intake,
        "response_dry_run": response_dry_run,
    }
    files = {
        "00_SANDBOX_VM_STATIC_PREFLIGHT_DISPOSITION_INDEX.md": _index(context),
        "01_SANDBOX_VM_STATIC_PREFLIGHT_DISPOSITION_PROMPT.md": _prompt(context),
        "02_SANDBOX_VM_STATIC_PREFLIGHT_DISPOSITION_AND_INTAKE.md": _bundle_docs(
            repo_root, DISPOSITION_DOCS
        ),
        "03_SANDBOX_VM_STATIC_PREFLIGHT_SOURCE_REVIEW_POINTERS.md": _bundle_docs(
            repo_root, SOURCE_REVIEW_DOCS
        ),
        "04_SANDBOX_VM_STATIC_PREFLIGHT_DISPOSITION_COMMAND_EVIDENCE.md": _command_evidence(
            repo_root=repo_root,
            run_commands=run_commands,
            reports={
                "source_review_packet_check": source_packet,
                "disposition_plan_check": disposition,
                "external_response_intake_check": intake,
                "response_dry_run": response_dry_run,
            },
        ),
    }
    for relative, content in files.items():
        output_dir.joinpath(relative).write_text(content.rstrip() + "\n", encoding="utf-8")
    _write_json(output_dir / HASH_MANIFEST, {"artifacts": _hashes(output_dir)})
    return output_dir


def _index(context: dict[str, Any]) -> str:
    return f"""# Sandbox/VM Static Preflight Disposition Packet

This packet packages the `ERG-003` external/source-review disposition question set, response-intake
template, response dry-run evidence, source-review packet pointers, and command evidence. It is a
review handoff for deciding whether the CLI-only static preflight lane may be recorded as
`closed_local_preview_static_preflight`.

## Boundary

- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Command evidence executed: `{str(context["run_commands"]).lower()}`.
- Tool count remains `24`.
- Current `ERG-003` status remains `external_review_required`.
- This packet does not close `ERG-003`.
- This packet does not approve live VM/container inspection, sandbox orchestration, Mission Control
  runtime behavior, local model invocation, trusted-host promotion, network expansion, API/MCP
  profile loading, SIEM delivery, compliance automation, public/security-product positioning, or
  any new governed tool power.

## Artifacts

1. `00_SANDBOX_VM_STATIC_PREFLIGHT_DISPOSITION_INDEX.md`
2. `01_SANDBOX_VM_STATIC_PREFLIGHT_DISPOSITION_PROMPT.md`
3. `02_SANDBOX_VM_STATIC_PREFLIGHT_DISPOSITION_AND_INTAKE.md`
4. `03_SANDBOX_VM_STATIC_PREFLIGHT_SOURCE_REVIEW_POINTERS.md`
5. `04_SANDBOX_VM_STATIC_PREFLIGHT_DISPOSITION_COMMAND_EVIDENCE.md`
6. `sandbox-vm-static-preflight-disposition-artifact-hashes.json`

## What This Packet Does Not Prove

This packet does not prove external review has happened, does not prove `ERG-003` is closed, does
not approve live VM/container inspection, and does not approve runtime sandbox/VM work. A later
committed triage update must record the reviewer response, findings, verification commands, and any
matrix/status changes.
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# Sandbox/VM Static Preflight Disposition Review Prompt

You are reviewing Ithildin's CLI-only sandbox/VM static preflight lane for external/source
disposition.

Reviewed commit: `{context["commit"]}`
Area: `sandbox-vm-static-preflight`
Finding namespace: `EXT-SVP-###`

## Required Disposition

Please answer every question:

1. Did the reviewer inspect the static preflight source-review packet and the source files named in
   that packet?
2. Does the CLI-only fixture runner stay within the approved boundary?
3. Are the static profile fixture contract and negative fixtures sufficient for local-preview
   planning evidence?
4. Are safe-label and safe-error expectations strong enough for packet/display use?
5. Does `XH-SANDBOX-PREFLIGHT-001` appear fixed for the local-preview fixture lane?
6. Are there any critical/high findings?
7. Does the response dry run prove absent responses stay not-ready, source-level favorable
   responses are accepted for later triage, and packet-only, bad-hash, critical/high, and direct
   external-closure attempts are rejected?
8. If there are no critical/high findings, can `ERG-003` move from `external_review_required` to
   `closed_local_preview_static_preflight`?
9. Does the reviewer explicitly avoid approving live VM/container control, Mission Control runtime
   behavior, local model invocation, trusted-host promotion, or production/security-product claims?

Use this exact finding shape for actionable findings:

{FINDING_TABLE}

If there are no implementation findings, explicitly say `no findings` or `finding_count: 0`.

Do not approve live VM/container inspection, sandbox orchestration, Mission Control runtime
behavior, local model invocation, trusted-host promotion, network expansion, API/MCP profile
loading, SIEM delivery, compliance automation, public/security-product positioning, or new governed
tool powers.
"""


def _command_evidence(
    *,
    repo_root: Path,
    run_commands: bool,
    reports: dict[str, dict[str, Any]],
) -> str:
    lines = [
        "# Sandbox/VM Static Preflight Disposition Command Evidence",
        "",
        "## Boundary Flags",
        "",
        "```json",
        json.dumps(
            {
                "tool_count": 24,
                "erg_003_status": "external_review_required",
                "runtime_changes_allowed": False,
                "live_vm_inspection_allowed": False,
                "mission_control_runtime_allowed": False,
                "local_model_invocation_allowed": False,
                "sandbox_orchestration_allowed": False,
                "trusted_host_promotion_allowed": False,
                "network_expansion_allowed": False,
                "api_mcp_profile_loading_allowed": False,
                "new_power_classes_allowed": False,
                "closes_erg_003": False,
            },
            indent=2,
            sort_keys=True,
        ),
        "```",
        "",
        "## Embedded Check Reports",
        "",
        "```json",
        json.dumps(reports, indent=2, sort_keys=True),
        "```",
    ]
    if run_commands:
        lines.extend(["", "## Command Transcripts", ""])
        for command in COMMANDS:
            lines.append(f"### `{' '.join(command)}`")
            result = subprocess.run(
                command,
                cwd=repo_root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            lines.append("")
            lines.append("```text")
            lines.append((result.stdout or "").strip())
            lines.append("```")
            lines.append(f"exit_code: `{result.returncode}`")
            lines.append("")
            if result.returncode != 0:
                raise SandboxVmStaticPreflightDispositionPacketError(
                    f"command failed: {' '.join(command)}"
                )
    else:
        lines.extend(
            [
                "",
                "Command execution skipped for packet check mode.",
                "",
                "Expected full commands:",
                "",
                "```text",
                "\n".join(" ".join(command) for command in COMMANDS),
                "```",
            ]
        )
    return "\n".join(lines)


def _bundle_docs(repo_root: Path, docs: list[Path]) -> str:
    parts: list[str] = []
    for doc in docs:
        path = repo_root / doc
        if not path.exists():
            raise SandboxVmStaticPreflightDispositionPacketError(f"missing doc: {doc}")
        parts.append(f"## {doc}\n\n{path.read_text(encoding='utf-8').strip()}")
    return "\n\n".join(parts)


def _hashes(output_dir: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(output_dir.iterdir()):
        if path.name == HASH_MANIFEST or not path.is_file():
            continue
        data = path.read_bytes()
        entries.append(
            {
                "path": path.name,
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            }
        )
    return entries


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


def _require_project_root(repo_root: Path) -> None:
    missing = [str(marker) for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        raise SandboxVmStaticPreflightDispositionPacketError(
            "not an Ithildin project root; missing " + ", ".join(missing)
        )


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM static preflight disposition packet check",
        f"valid: {str(report['valid']).lower()}",
        f"output_dir: {report['output_dir']}",
        f"artifact_count: {report['artifact_count']}",
        f"tool_count: {report['tool_count']}",
        f"erg_003_status: {report['erg_003_status']}",
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
        f"closes_erg_003: {str(report['closes_erg_003']).lower()}",
    ]
    if report["failures"]:
        lines.append("")
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

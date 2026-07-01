"""Build a sandbox/VM live POC external-decision packet."""

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
    enterprise_sandbox_control_plane_readiness_check,
    sandbox_vm_live_poc_decision_intake_check,
    sandbox_vm_live_poc_evidence_contract_check,
    sandbox_vm_live_poc_prerequisite_disposition_dry_run,
    sandbox_vm_static_preflight_disposition_packet,
    sandbox_vm_static_preflight_disposition_plan_check,
    sandbox_vm_static_preflight_external_response_intake_check,
)

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/sandbox-vm-live-poc-decision")
HASH_MANIFEST = "sandbox-vm-live-poc-decision-artifact-hashes.json"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
DECISION_DOCS = [
    Path("docs/codex/sandbox-vm-live-poc-decision-packet.md"),
    Path("docs/codex/sandbox-vm-live-poc-decision-intake.md"),
    Path("docs/codex/sandbox-vm-live-poc-evidence-contract.md"),
    Path("docs/codex/sandbox-vm-live-poc-preconditions-ready-check.md"),
    Path("docs/codex/sandbox-vm-live-poc-external-response-intake.md"),
    Path("docs/codex/sandbox-vm-live-poc-prerequisite-disposition-dry-run.md"),
    Path("docs/codex/enterprise-sandbox-control-plane-readiness.md"),
]
REVIEW_POINTER_DOCS = [
    Path("docs/codex/sandbox-vm-static-preflight-disposition-packet.md"),
    Path("docs/codex/sandbox-vm-static-preflight-disposition-plan.md"),
    Path("docs/codex/sandbox-vm-static-preflight-external-response-intake.md"),
    Path("docs/codex/mission-control-display-disposition-packet.md"),
    Path("docs/codex/trusted-host-promotion-disposition-packet.md"),
    Path("docs/codex/post-rc-decision-register.md"),
    Path("docs/codex/enterprise-readiness-gap-matrix.md"),
    Path("docs/codex/enterprise-readiness-runway.md"),
]
COMMANDS = [
    ["make", "enterprise-sandbox-control-plane-readiness-check"],
    ["make", "sandbox-vm-live-poc-decision-intake-check"],
    ["make", "sandbox-vm-live-poc-evidence-contract-check"],
    ["make", "sandbox-vm-live-poc-preconditions-ready-check"],
    ["make", "sandbox-vm-live-poc-external-response-intake-check"],
    ["make", "sandbox-vm-live-poc-prerequisite-disposition-dry-run"],
    ["make", "sandbox-vm-static-preflight-disposition-packet-check"],
    ["make", "sandbox-vm-static-preflight-disposition-plan-check"],
    ["make", "sandbox-vm-static-preflight-external-response-intake-check"],
    ["make", "no-new-powers-guardrail"],
    ["make", "tool-surface-invariant-gate"],
]
FINDING_TABLE = "\n".join(
    [
        "| Finding ID | Severity | Area | Affected files/functions | "
        "Blocking status | Disposition | Recommended fix |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        "| EXT-LIVE-POC-### | critical/high/medium/low/informational | "
        "sandbox-vm-live-poc | path/function | "
        "blocking/should-fix/later/advisory | open | fix summary |",
    ]
)


class SandboxVmLivePocDecisionPacketError(RuntimeError):
    """Raised when the live POC decision packet cannot be built."""


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
    except SandboxVmLivePocDecisionPacketError as exc:
        print(f"sandbox/VM live POC decision packet failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built sandbox/VM live POC decision packet at {output_dir}")
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
    decision_register = _read(repo_root / "docs/codex/post-rc-decision-register.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "sandbox-vm-live-poc-decision"
        try:
            build_packet(
                repo_root=repo_root,
                output_dir=output_dir,
                allow_dirty=True,
                run_commands=False,
            )
        except SandboxVmLivePocDecisionPacketError as exc:
            failures.append(str(exc))
            artifact_names: set[str] = set()
            hashes: dict[str, Any] = {"artifacts": []}
            prompt = ""
            index = ""
            decision_docs = ""
            evidence = ""
        else:
            artifact_names = {path.name for path in output_dir.iterdir()}
            hashes = json.loads((output_dir / HASH_MANIFEST).read_text(encoding="utf-8"))
            prompt = (output_dir / "01_SANDBOX_VM_LIVE_POC_DECISION_PROMPT.md").read_text(
                encoding="utf-8"
            )
            index = (output_dir / "00_SANDBOX_VM_LIVE_POC_DECISION_INDEX.md").read_text(
                encoding="utf-8"
            )
            evidence = (
                output_dir / "04_SANDBOX_VM_LIVE_POC_DECISION_COMMAND_EVIDENCE.md"
            ).read_text(encoding="utf-8")
            decision_docs = (
                output_dir / "02_SANDBOX_VM_LIVE_POC_DECISION_AND_READINESS.md"
            ).read_text(encoding="utf-8")

    expected = {
        "00_SANDBOX_VM_LIVE_POC_DECISION_INDEX.md",
        "01_SANDBOX_VM_LIVE_POC_DECISION_PROMPT.md",
        "02_SANDBOX_VM_LIVE_POC_DECISION_AND_READINESS.md",
        "03_SANDBOX_VM_LIVE_POC_REVIEW_POINTERS.md",
        "04_SANDBOX_VM_LIVE_POC_DECISION_COMMAND_EVIDENCE.md",
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
        "Finding namespace: `EXT-LIVE-POC-###`",
        "continue_design_only",
        "approve_limited_operator_managed_poc_planning",
        "block_live_poc",
        "Does the reviewer agree `ERG-004` remains blocked",
        "sandbox-vm-live-poc-prerequisite-disposition-dry-run.md",
    ]:
        if phrase not in prompt:
            failures.append(f"packet prompt is missing phrase: {phrase}")
    for phrase in [
        "sandbox-vm-live-poc-preconditions-ready-check.md",
        "ready_for_implementation_planning: false",
    ]:
        if phrase not in decision_docs:
            failures.append(f"decision/readiness docs are missing phrase: {phrase}")
    for phrase in [
        "What This Packet Does Not Prove",
        "does not approve live VM/container inspection",
        "does not close `ERG-004`",
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
        '"preconditions_ready"',
        '"ready_for_implementation_planning": false',
        '"closes_erg_004": false',
        '"erg_004_unblocked": false',
        '"erg_003_disposition_recorded": true',
        '"temporary_fixtures_only": true',
    ]:
        if phrase not in evidence:
            failures.append(f"command evidence is missing boundary flag: {phrase}")
    for target in [
        "sandbox-vm-live-poc-decision-packet:",
        "sandbox-vm-live-poc-decision-packet-check:",
    ]:
        if target not in makefile:
            failures.append(f"Make target is missing: {target.rstrip(':')}")
    if "sandbox-vm-live-poc-decision-packet-check" not in release_check_body:
        failures.append("sandbox-vm-live-poc-decision-packet-check missing from release-check")
    if "$(MAKE) sandbox-vm-live-poc-decision-packet" not in review_candidate_body:
        failures.append("sandbox-vm-live-poc-decision-packet missing from review-candidate")
    if "sandbox-vm-live-poc-decision-packet-check" not in release_guardrails:
        failures.append("release guardrails do not require live POC decision packet check")
    if "docs/codex/sandbox-vm-live-poc-decision-packet.md" not in docs_site:
        failures.append("live POC decision packet doc is missing from docs-site inputs")
    if "docs/codex/sandbox-vm-live-poc-decision-packet.md" not in review_docs:
        failures.append("live POC decision packet doc is missing from review docs")
    if "Sandbox/VM Live POC Decision Packet" not in review_index:
        failures.append("review-docs index is missing live POC decision packet entry")
    if "make sandbox-vm-live-poc-decision-packet" not in readme:
        failures.append("README is missing live POC decision packet command")
    if "sandbox-vm-live-poc-decision-packet.md" not in runway:
        failures.append("enterprise runway is missing live POC decision packet pointer")
    if "sandbox-vm-live-poc-decision-packet.md" not in gap_matrix:
        failures.append("enterprise gap matrix is missing live POC decision packet pointer")
    if "sandbox-vm-live-poc-decision-packet.md" not in decision_register:
        failures.append("post-RC decision register is missing live POC decision packet pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "output_dir": str(DEFAULT_OUTPUT_DIR),
        "artifact_count": len(expected),
        "tool_count": 24,
        "erg_004_status": "blocked",
        "prd_id": "PRD-SANDBOX-LIVE-POC-001",
        "requires_erg_003_favorable_disposition": False,
        "erg_003_status": "closed_local_preview_static_preflight",
        "erg_003_disposition_recorded": True,
        "runtime_changes_allowed": False,
        "live_vm_inspection_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
        "closes_erg_004": False,
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
        raise SandboxVmLivePocDecisionPacketError(
            "working tree is dirty; commit before live POC decision packet handoff"
        )

    readiness = enterprise_sandbox_control_plane_readiness_check.build_report(repo_root)
    intake = sandbox_vm_live_poc_decision_intake_check.build_report(repo_root)
    evidence_contract = sandbox_vm_live_poc_evidence_contract_check.build_report(repo_root)
    preconditions_ready = {
        "schema_version": "1",
        "document": "docs/codex/sandbox-vm-live-poc-preconditions-ready-check.md",
        "command": "make sandbox-vm-live-poc-preconditions-ready-check",
        "ready_for_implementation_planning": False,
        "runtime_changes_allowed": False,
        "closes_erg_004": False,
    }
    static_disposition = sandbox_vm_static_preflight_disposition_packet.build_check_report(
        repo_root
    )
    static_plan = sandbox_vm_static_preflight_disposition_plan_check.build_report(repo_root)
    static_intake = sandbox_vm_static_preflight_external_response_intake_check.build_report(
        repo_root
    )
    prerequisite_disposition = (
        sandbox_vm_live_poc_prerequisite_disposition_dry_run.build_report(repo_root)
    )
    failures = [
        *(f"readiness: {failure}" for failure in readiness["failures"]),
        *(f"decision intake: {failure}" for failure in intake["failures"]),
        *(f"evidence contract: {failure}" for failure in evidence_contract["failures"]),
        *(f"static disposition: {failure}" for failure in static_disposition["failures"]),
        *(f"static plan: {failure}" for failure in static_plan["failures"]),
        *(f"static external intake: {failure}" for failure in static_intake["failures"]),
        *(
            f"prerequisite disposition: {failure}"
            for failure in prerequisite_disposition["failures"]
        ),
    ]
    if failures:
        raise SandboxVmLivePocDecisionPacketError("; ".join(failures))

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context = {
        "commit": commit,
        "dirty": dirty,
        "run_commands": run_commands,
        "readiness": readiness,
        "intake": intake,
        "evidence_contract": evidence_contract,
        "preconditions_ready": preconditions_ready,
        "static_disposition": static_disposition,
        "static_plan": static_plan,
        "static_intake": static_intake,
        "prerequisite_disposition": prerequisite_disposition,
    }
    files = {
        "00_SANDBOX_VM_LIVE_POC_DECISION_INDEX.md": _index(context),
        "01_SANDBOX_VM_LIVE_POC_DECISION_PROMPT.md": _prompt(context),
        "02_SANDBOX_VM_LIVE_POC_DECISION_AND_READINESS.md": _bundle_docs(
            repo_root, DECISION_DOCS
        ),
        "03_SANDBOX_VM_LIVE_POC_REVIEW_POINTERS.md": _bundle_docs(
            repo_root, REVIEW_POINTER_DOCS
        ),
        "04_SANDBOX_VM_LIVE_POC_DECISION_COMMAND_EVIDENCE.md": _command_evidence(
            repo_root=repo_root,
            run_commands=run_commands,
            reports={
                "enterprise_sandbox_control_plane_readiness": readiness,
                "decision_intake": intake,
                "evidence_contract": evidence_contract,
                "preconditions_ready": preconditions_ready,
                "static_preflight_disposition_packet": static_disposition,
                "static_preflight_disposition_plan": static_plan,
                "static_preflight_external_response_intake": static_intake,
                "live_poc_prerequisite_disposition_dry_run": prerequisite_disposition,
            },
        ),
    }
    for relative, content in files.items():
        output_dir.joinpath(relative).write_text(content.rstrip() + "\n", encoding="utf-8")
    _write_json(output_dir / HASH_MANIFEST, {"artifacts": _hashes(output_dir)})
    return output_dir


def _index(context: dict[str, Any]) -> str:
    return f"""# Sandbox/VM Live POC Decision Packet

This packet packages the `ERG-004` decision question set, evidence contract, enterprise
control-plane readiness map, prerequisite static-preflight disposition evidence, and command
evidence. It is a review handoff for deciding whether a later implementation-planning packet may be
prepared for an operator-managed live sandbox/VM worker POC.

## Boundary

- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Command evidence executed: `{str(context["run_commands"]).lower()}`.
- Tool count remains `24`.
- Current `ERG-004` status remains `blocked`.
- This packet does not close `ERG-004`.
- This packet does not approve live VM/container inspection, sandbox orchestration, Mission Control
  runtime behavior, local model invocation, trusted-host promotion, network expansion, API/MCP
  profile loading, SIEM delivery, compliance automation, public/security-product positioning, or
  any new governed tool power.

## Artifacts

1. `00_SANDBOX_VM_LIVE_POC_DECISION_INDEX.md`
2. `01_SANDBOX_VM_LIVE_POC_DECISION_PROMPT.md`
3. `02_SANDBOX_VM_LIVE_POC_DECISION_AND_READINESS.md`
4. `03_SANDBOX_VM_LIVE_POC_REVIEW_POINTERS.md`
5. `04_SANDBOX_VM_LIVE_POC_DECISION_COMMAND_EVIDENCE.md`
6. `sandbox-vm-live-poc-decision-artifact-hashes.json`

## What This Packet Does Not Prove

This packet does not prove external review has happened, does not prove `ERG-004` is closed, does
not approve live VM/container inspection, and does not approve runtime sandbox/VM work. A later
committed decision record must record the reviewer response, findings, verification commands, and
any matrix/status changes before implementation planning can begin.
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# Sandbox/VM Live POC Decision Review Prompt

You are reviewing Ithildin's blocked live sandbox/VM worker POC lane for external/source
disposition.

Reviewed commit: `{context["commit"]}`
Area: `sandbox-vm-live-poc`
Finding namespace: `EXT-LIVE-POC-###`

## Required Disposition

Please answer every question:

1. Did the reviewer inspect the live POC decision packet, evidence contract, readiness map, and
   prerequisite `ERG-003` static-preflight disposition evidence, including
   `sandbox-vm-live-poc-prerequisite-disposition-dry-run.md`?
2. Does the reviewer agree `ERG-004` remains blocked unless `ERG-003` receives favorable
   external/source disposition with no unresolved critical/high findings?
3. Are the operator-managed VM profile, network/mount/root contract, cleanup transcript, and failure
   transcript requirements sufficient before implementation planning?
4. Does the packet keep Mission Control display-only, with no execution, policy, approval, audit, or
   sandbox authority?
5. Does the packet keep local model invocation blocked until a later implementation plan explicitly
   scopes it?
6. Does the packet avoid approving trusted-host promotion, sandbox orchestration, shell, Docker
   socket, Kubernetes, browser automation, arbitrary HTTP, broad writes, SIEM delivery, compliance
   automation, and public/security-product positioning?
7. If there are no critical/high findings, may a later packet be prepared under
   `approve_limited_operator_managed_poc_planning`, or should the lane remain
   `continue_design_only`, `revise_before_decision`, or `block_live_poc`?

Use this exact finding shape for actionable findings:

{FINDING_TABLE}

If there are no implementation findings, explicitly say `no findings` or `finding_count: 0`.

Do not approve implementation, live VM/container inspection, sandbox orchestration, Mission Control
runtime behavior, local model invocation, trusted-host promotion, network expansion, API/MCP profile
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
        "# Sandbox/VM Live POC Decision Command Evidence",
        "",
        "## Boundary Flags",
        "",
        "```json",
        json.dumps(
            {
                "tool_count": 24,
                "erg_004_status": "blocked",
                "prd_id": "PRD-SANDBOX-LIVE-POC-001",
                "requires_erg_003_favorable_disposition": False,
                "erg_003_status": "closed_local_preview_static_preflight",
                "erg_003_disposition_recorded": True,
                "runtime_changes_allowed": False,
                "live_vm_inspection_allowed": False,
                "mission_control_runtime_allowed": False,
                "local_model_invocation_allowed": False,
                "sandbox_orchestration_allowed": False,
                "trusted_host_promotion_allowed": False,
                "siem_adapter_allowed": False,
                "network_expansion_allowed": False,
                "api_mcp_profile_loading_allowed": False,
                "new_power_classes_allowed": False,
                "closes_erg_004": False,
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
                raise SandboxVmLivePocDecisionPacketError(
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
            raise SandboxVmLivePocDecisionPacketError(f"missing doc: {doc}")
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
        raise SandboxVmLivePocDecisionPacketError(
            "not an Ithildin project root; missing " + ", ".join(missing)
        )


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM live POC decision packet check",
        f"valid: {str(report['valid']).lower()}",
        f"output_dir: {report['output_dir']}",
        f"artifact_count: {report['artifact_count']}",
        f"tool_count: {report['tool_count']}",
        f"erg_004_status: {report['erg_004_status']}",
        f"prd_id: {report['prd_id']}",
        f"erg_003_status: {report['erg_003_status']}",
        "erg_003_disposition_recorded: "
        f"{str(report['erg_003_disposition_recorded']).lower()}",
        "requires_erg_003_favorable_disposition: "
        f"{str(report['requires_erg_003_favorable_disposition']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
        f"closes_erg_004: {str(report['closes_erg_004']).lower()}",
    ]
    if report["failures"]:
        lines.append("")
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

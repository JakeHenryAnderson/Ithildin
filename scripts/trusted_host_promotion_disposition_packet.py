"""Build a trusted-host promotion external-disposition packet."""

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
    no_new_powers_guardrail,
    tool_surface_invariant_gate,
    trusted_host_promotion_decision_intake_check,
    trusted_host_promotion_implementation_plan_check,
    trusted_host_promotion_internal_review_check,
    trusted_host_promotion_negative_fixtures_check,
    trusted_host_promotion_source_review_packet,
    trusted_host_promotion_state_machine_check,
    trusted_host_promotion_zone_contract_check,
)

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/trusted-host-promotion-disposition")
HASH_MANIFEST = "trusted-host-promotion-disposition-artifact-hashes.json"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
DISPOSITION_DOCS = [
    Path("docs/codex/trusted-host-promotion-disposition-packet.md"),
    Path("docs/codex/trusted-host-promotion-decision-intake.md"),
]
SOURCE_REVIEW_DOCS = [
    Path("docs/codex/trusted-host-promotion-source-review.md"),
    Path("docs/codex/v3-trusted-host-promotion-internal-review.md"),
    Path("docs/codex/sandbox-promotion-evidence-contract.md"),
    Path("docs/codex/trusted-host-promotion-state-machine.md"),
    Path("docs/codex/trusted-host-promotion-negative-fixtures.md"),
    Path("docs/codex/trusted-host-promotion-zone-contract.md"),
    Path("docs/codex/trusted-host-promotion-implementation-plan.md"),
    Path("docs/codex/enterprise-readiness-gap-matrix.md"),
    Path("docs/codex/enterprise-readiness-runway.md"),
]
COMMANDS = [
    ["make", "trusted-host-promotion-source-review-packet-check"],
    ["make", "trusted-host-promotion-decision-intake-check"],
    ["make", "trusted-host-promotion-state-machine-check"],
    ["make", "trusted-host-promotion-negative-fixtures-check"],
    ["make", "trusted-host-promotion-zone-contract-check"],
    ["make", "trusted-host-promotion-implementation-plan-check"],
    ["make", "trusted-host-promotion-internal-review-check"],
    ["make", "no-new-powers-guardrail"],
    ["make", "tool-surface-invariant-gate"],
]
FINDING_TABLE = "\n".join(
    [
        "| Finding ID | Severity | Area | Affected files/functions | "
        "Blocking status | Disposition | Recommended fix |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        "| EXT-TRUSTED-HOST-### | critical/high/medium/low/informational | "
        "trusted-host-promotion | path/function | "
        "blocking/should-fix/later/advisory | open | fix summary |",
    ]
)


class TrustedHostPromotionDispositionPacketError(RuntimeError):
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
    except TrustedHostPromotionDispositionPacketError as exc:
        print(f"trusted-host promotion disposition packet failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built trusted-host promotion disposition packet at {output_dir}")
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
        output_dir = Path(tmp) / "trusted-host-promotion-disposition"
        try:
            build_packet(
                repo_root=repo_root,
                output_dir=output_dir,
                allow_dirty=True,
                run_commands=False,
            )
        except TrustedHostPromotionDispositionPacketError as exc:
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
                output_dir / "01_TRUSTED_HOST_PROMOTION_DISPOSITION_PROMPT.md"
            ).read_text(encoding="utf-8")
            index = (
                output_dir / "00_TRUSTED_HOST_PROMOTION_DISPOSITION_INDEX.md"
            ).read_text(encoding="utf-8")
            evidence = (
                output_dir / "04_TRUSTED_HOST_PROMOTION_DISPOSITION_COMMAND_EVIDENCE.md"
            ).read_text(encoding="utf-8")

    expected = {
        "00_TRUSTED_HOST_PROMOTION_DISPOSITION_INDEX.md",
        "01_TRUSTED_HOST_PROMOTION_DISPOSITION_PROMPT.md",
        "02_TRUSTED_HOST_PROMOTION_DISPOSITION_AND_INTAKE.md",
        "03_TRUSTED_HOST_PROMOTION_SOURCE_REVIEW_POINTERS.md",
        "04_TRUSTED_HOST_PROMOTION_DISPOSITION_COMMAND_EVIDENCE.md",
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
        "Finding namespace: `EXT-TRUSTED-HOST-###`",
        "continue_design_only",
        "revise_before_more_planning",
        "block_runtime_implementation",
        "may the lane continue design-only planning",
    ]:
        if phrase not in prompt:
            failures.append(f"packet prompt is missing phrase: {phrase}")
    for phrase in [
        "What This Packet Does Not Prove",
        "does not approve trusted-host promotion",
        "does not close `ERG-005`",
    ]:
        if phrase not in index:
            failures.append(f"packet index is missing phrase: {phrase}")
    for phrase in [
        '"runtime_changes_allowed": false',
        '"trusted_host_promotion_allowed": false',
        '"direct_host_writes_allowed": false',
        '"overwrite_delete_move_allowed": false',
        '"automatic_promotion_allowed": false',
        '"mission_control_runtime_allowed": false',
        '"local_model_invocation_allowed": false',
        '"sandbox_orchestration_allowed": false',
        '"siem_adapter_allowed": false',
        '"new_power_classes_allowed": false',
        '"closes_erg_005": false',
    ]:
        if phrase not in evidence:
            failures.append(f"command evidence is missing boundary flag: {phrase}")
    for target in [
        "trusted-host-promotion-disposition-packet:",
        "trusted-host-promotion-disposition-packet-check:",
    ]:
        if target not in makefile:
            failures.append(f"Make target is missing: {target.rstrip(':')}")
    if "trusted-host-promotion-disposition-packet-check" not in release_check_body:
        failures.append("trusted-host disposition packet check missing from release-check")
    if "$(MAKE) trusted-host-promotion-disposition-packet" not in review_candidate_body:
        failures.append("trusted-host disposition packet missing from review-candidate")
    if "trusted-host-promotion-disposition-packet-check" not in release_guardrails:
        failures.append("release guardrails do not require trusted-host disposition check")
    if "docs/codex/trusted-host-promotion-disposition-packet.md" not in docs_site:
        failures.append("trusted-host disposition doc is missing from docs-site inputs")
    if "docs/codex/trusted-host-promotion-disposition-packet.md" not in review_docs:
        failures.append("trusted-host disposition doc is missing from review docs")
    if "Trusted-Host Promotion Disposition Packet" not in review_index:
        failures.append("review-docs index is missing trusted-host disposition entry")
    if "make trusted-host-promotion-disposition-packet" not in readme:
        failures.append("README is missing trusted-host disposition command")
    if "trusted-host-promotion-disposition-packet.md" not in runway:
        failures.append("enterprise runway is missing trusted-host disposition pointer")
    if "trusted-host-promotion-disposition-packet.md" not in gap_matrix:
        failures.append("enterprise gap matrix is missing trusted-host disposition pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "output_dir": str(DEFAULT_OUTPUT_DIR),
        "artifact_count": len(expected),
        "tool_count": 24,
        "erg_005_status": "blocked",
        "prd_id": "PRD-TRUSTED-HOST-001",
        "runtime_changes_allowed": False,
        "trusted_host_promotion_allowed": False,
        "direct_host_writes_allowed": False,
        "overwrite_delete_move_allowed": False,
        "broad_archive_extraction_allowed": False,
        "automatic_promotion_allowed": False,
        "promotion_without_hash_binding_allowed": False,
        "promotion_without_approval_evidence_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
        "closes_erg_005": False,
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
        raise TrustedHostPromotionDispositionPacketError(
            "working tree is dirty; commit before disposition packet handoff"
        )

    source_packet = trusted_host_promotion_source_review_packet.build_check_report(repo_root)
    decision_intake = trusted_host_promotion_decision_intake_check.build_report(repo_root)
    state_machine = trusted_host_promotion_state_machine_check.build_report(repo_root)
    negative_fixtures = trusted_host_promotion_negative_fixtures_check.build_report(repo_root)
    zone_contract = trusted_host_promotion_zone_contract_check.build_report(repo_root)
    implementation_plan = trusted_host_promotion_implementation_plan_check.build_report(repo_root)
    internal_review = trusted_host_promotion_internal_review_check.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    reports = {
        "source_review_packet_check": source_packet,
        "decision_intake_check": decision_intake,
        "state_machine_check": state_machine,
        "negative_fixtures_check": negative_fixtures,
        "zone_contract_check": zone_contract,
        "implementation_plan_check": implementation_plan,
        "internal_review_check": internal_review,
        "no_new_powers": no_new_powers,
        "tool_surface": tool_surface,
    }
    failures = [
        f"{key}: {failure}"
        for key, report in reports.items()
        for failure in report.get("failures", [])
    ]
    if failures:
        raise TrustedHostPromotionDispositionPacketError("; ".join(failures))

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context = {
        "commit": commit,
        "dirty": dirty,
        "run_commands": run_commands,
        "reports": reports,
    }
    files = {
        "00_TRUSTED_HOST_PROMOTION_DISPOSITION_INDEX.md": _index(context),
        "01_TRUSTED_HOST_PROMOTION_DISPOSITION_PROMPT.md": _prompt(context),
        "02_TRUSTED_HOST_PROMOTION_DISPOSITION_AND_INTAKE.md": _bundle_docs(
            repo_root, DISPOSITION_DOCS
        ),
        "03_TRUSTED_HOST_PROMOTION_SOURCE_REVIEW_POINTERS.md": _bundle_docs(
            repo_root, SOURCE_REVIEW_DOCS
        ),
        "04_TRUSTED_HOST_PROMOTION_DISPOSITION_COMMAND_EVIDENCE.md": _command_evidence(
            repo_root=repo_root,
            run_commands=run_commands,
            reports=reports,
        ),
    }
    for relative, content in files.items():
        output_dir.joinpath(relative).write_text(content.rstrip() + "\n", encoding="utf-8")
    _write_json(output_dir / HASH_MANIFEST, {"artifacts": _hashes(output_dir)})
    return output_dir


def _index(context: dict[str, Any]) -> str:
    return f"""# Trusted-Host Promotion Disposition Packet

This packet packages the `ERG-005` external/source-review disposition question set, source-review
packet pointers, internal review evidence, and command evidence. It is a review handoff for deciding
whether trusted-host promotion may continue design-only planning.

## Boundary

- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Command evidence executed: `{str(context["run_commands"]).lower()}`.
- Tool count remains `24`.
- Current `ERG-005` status remains `blocked`.
- Post-RC decision ID: `PRD-TRUSTED-HOST-001`.
- This packet does not close `ERG-005`.
- This packet does not approve trusted-host promotion, direct host writes, overwrite/delete/move
  behavior, broad archive extraction, automatic promotion, Mission Control runtime behavior, local
  model invocation, sandbox orchestration, SIEM adapter behavior, compliance automation,
  public/security-product positioning, or any new governed tool power.

## Artifacts

1. `00_TRUSTED_HOST_PROMOTION_DISPOSITION_INDEX.md`
2. `01_TRUSTED_HOST_PROMOTION_DISPOSITION_PROMPT.md`
3. `02_TRUSTED_HOST_PROMOTION_DISPOSITION_AND_INTAKE.md`
4. `03_TRUSTED_HOST_PROMOTION_SOURCE_REVIEW_POINTERS.md`
5. `04_TRUSTED_HOST_PROMOTION_DISPOSITION_COMMAND_EVIDENCE.md`
6. `trusted-host-promotion-disposition-artifact-hashes.json`

## What This Packet Does Not Prove

This packet does not prove external review has happened, does not prove `ERG-005` is closed, does
not approve trusted-host promotion, and does not approve runtime host-write behavior. A later
post-RC decision record must record the reviewer response, findings, verification commands, and any
matrix/status changes before implementation planning can move.
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# Trusted-Host Promotion Disposition Review Prompt

You are reviewing Ithildin's trusted-host promotion planning lane for external/source disposition.

Reviewed commit: `{context["commit"]}`
Area: `trusted-host-promotion`
Finding namespace: `EXT-TRUSTED-HOST-###`

## Required Disposition

Please answer every question:

1. Did the reviewer inspect the trusted-host promotion source-review packet and the design/source
   artifacts named in that packet?
2. Are the source/staging/approved/evidence zone labels precise enough and non-authoritative?
3. Does the implementation-plan skeleton require exact artifact hash binding, approval binding,
   one-time scope evidence, conflict/replay/stale/path-escape denials, and policy/manifest evidence?
4. Are the negative fixture and state-machine expectations strong enough for a future
   implementation proposal to be considered?
5. Does the internal review appear sufficient for design-only continuation?
6. Are there any critical/high findings?
7. If there are no critical/high findings, may the lane continue design-only planning while
   `ERG-005` remains blocked from runtime implementation?
8. Does the reviewer explicitly avoid approving host promotion, direct host writes, Mission Control
   runtime behavior, local model invocation, sandbox orchestration, SIEM adapter behavior, or
   production/security-product claims?

Choose one disposition:

- `continue_design_only`: current evidence is coherent for further design and review packets.
- `revise_before_more_planning`: gaps or ambiguous claims must be fixed before more planning.
- `block_runtime_implementation`: a blocking risk prevents implementation planning until a new
  decision record resolves it.

Use this exact finding shape for actionable findings:

{FINDING_TABLE}

If there are no implementation findings, explicitly say `no findings` or `finding_count: 0`.

Do not approve runtime implementation, trusted-host promotion, direct host writes,
overwrite/delete/move, archive extraction, automatic promotion, Mission Control execution authority,
local model invocation, VM/container lifecycle control, sandbox orchestration, SIEM adapters,
production identity, runtime Postgres, hosted telemetry, remote MCP, shell/Docker/Kubernetes/browser
governed powers, arbitrary HTTP, broad filesystem writes, compliance automation, or
public/security-product positioning.
"""


def _command_evidence(
    *,
    repo_root: Path,
    run_commands: bool,
    reports: dict[str, dict[str, Any]],
) -> str:
    lines = [
        "# Trusted-Host Promotion Disposition Command Evidence",
        "",
        "## Boundary Flags",
        "",
        "```json",
        json.dumps(
            {
                "tool_count": 24,
                "erg_005_status": "blocked",
                "prd_id": "PRD-TRUSTED-HOST-001",
                "runtime_changes_allowed": False,
                "trusted_host_promotion_allowed": False,
                "direct_host_writes_allowed": False,
                "overwrite_delete_move_allowed": False,
                "broad_archive_extraction_allowed": False,
                "automatic_promotion_allowed": False,
                "promotion_without_hash_binding_allowed": False,
                "promotion_without_approval_evidence_allowed": False,
                "mission_control_runtime_allowed": False,
                "local_model_invocation_allowed": False,
                "sandbox_orchestration_allowed": False,
                "siem_adapter_allowed": False,
                "new_power_classes_allowed": False,
                "closes_erg_005": False,
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
                raise TrustedHostPromotionDispositionPacketError(
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
            raise TrustedHostPromotionDispositionPacketError(f"missing doc: {doc}")
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
        raise TrustedHostPromotionDispositionPacketError(
            "not an Ithildin project root; missing " + ", ".join(missing)
        )


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin trusted-host promotion disposition packet check",
        f"valid: {str(report['valid']).lower()}",
        f"output_dir: {report['output_dir']}",
        f"artifact_count: {report['artifact_count']}",
        f"tool_count: {report['tool_count']}",
        f"erg_005_status: {report['erg_005_status']}",
        f"prd_id: {report['prd_id']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "trusted_host_promotion_allowed: "
        f"{str(report['trusted_host_promotion_allowed']).lower()}",
        f"direct_host_writes_allowed: {str(report['direct_host_writes_allowed']).lower()}",
        "overwrite_delete_move_allowed: "
        f"{str(report['overwrite_delete_move_allowed']).lower()}",
        "broad_archive_extraction_allowed: "
        f"{str(report['broad_archive_extraction_allowed']).lower()}",
        f"automatic_promotion_allowed: {str(report['automatic_promotion_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"closes_erg_005: {str(report['closes_erg_005']).lower()}",
    ]
    if report["failures"]:
        lines.append("")
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

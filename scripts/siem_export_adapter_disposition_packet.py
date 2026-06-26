"""Build a SIEM export adapter architecture disposition packet."""

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
    accepted_risk_register,
    enterprise_readiness_gap_matrix_check,
    enterprise_readiness_runway_check,
    no_new_powers_guardrail,
    post_rc_decision_register_check,
    siem_evidence_design_check,
    siem_export_adapter_architecture_check,
    tool_surface_invariant_gate,
)

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/siem-export-adapter-disposition")
HASH_MANIFEST = "siem-export-adapter-disposition-artifact-hashes.json"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
DISPOSITION_DOCS = [
    Path("docs/codex/siem-export-adapter-disposition-packet.md"),
    Path("docs/codex/siem-export-adapter-architecture.md"),
    Path("docs/codex/siem-export-adapter-external-response-intake.md"),
]
REVIEW_POINTER_DOCS = [
    Path("docs/codex/siem-shaped-evidence-design.md"),
    Path("docs/codex/evidence-contracts.md"),
    Path("docs/codex/post-rc-decision-register.md"),
    Path("docs/codex/enterprise-readiness-gap-matrix.md"),
    Path("docs/codex/enterprise-readiness-runway.md"),
    Path("docs/codex/accepted-risk-register.md"),
]
COMMANDS = [
    ["make", "siem-export-adapter-architecture-check"],
    ["make", "siem-evidence-design-check"],
    ["make", "evidence-contracts-check"],
    ["make", "post-rc-decision-register-check"],
    ["make", "enterprise-readiness-gap-matrix-check"],
    ["make", "enterprise-readiness-runway-check"],
    ["make", "accepted-risk-register-check"],
    ["make", "no-new-powers-guardrail"],
    ["make", "tool-surface-invariant-gate"],
]
FINDING_TABLE = "\n".join(
    [
        "| Finding ID | Severity | Area | Affected files/functions | "
        "Blocking status | Disposition | Recommended fix |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        "| EXT-SIEM-ADAPTER-### | critical/high/medium/low/informational | "
        "siem-export-adapter | path/function | "
        "blocking/should-fix/later/advisory | open | fix summary |",
    ]
)


class SiemExportAdapterDispositionPacketError(RuntimeError):
    """Raised when the SIEM export adapter disposition packet cannot be built."""


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
    except SiemExportAdapterDispositionPacketError as exc:
        print(f"SIEM export adapter disposition packet failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built SIEM export adapter disposition packet at {output_dir}")
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
        output_dir = Path(tmp) / "siem-export-adapter-disposition"
        try:
            build_packet(
                repo_root=repo_root,
                output_dir=output_dir,
                allow_dirty=True,
                run_commands=False,
            )
        except SiemExportAdapterDispositionPacketError as exc:
            failures.append(str(exc))
            artifact_names: set[str] = set()
            hashes: dict[str, Any] = {"artifacts": []}
            prompt = ""
            index = ""
            evidence = ""
        else:
            artifact_names = {path.name for path in output_dir.iterdir()}
            hashes = json.loads((output_dir / HASH_MANIFEST).read_text(encoding="utf-8"))
            prompt = (output_dir / "01_SIEM_EXPORT_ADAPTER_DISPOSITION_PROMPT.md").read_text(
                encoding="utf-8"
            )
            index = (output_dir / "00_SIEM_EXPORT_ADAPTER_DISPOSITION_INDEX.md").read_text(
                encoding="utf-8"
            )
            evidence = (
                output_dir / "04_SIEM_EXPORT_ADAPTER_DISPOSITION_COMMAND_EVIDENCE.md"
            ).read_text(encoding="utf-8")

    expected = {
        "00_SIEM_EXPORT_ADAPTER_DISPOSITION_INDEX.md",
        "01_SIEM_EXPORT_ADAPTER_DISPOSITION_PROMPT.md",
        "02_SIEM_EXPORT_ADAPTER_DISPOSITION_AND_ARCHITECTURE.md",
        "03_SIEM_EXPORT_ADAPTER_REVIEW_POINTERS.md",
        "04_SIEM_EXPORT_ADAPTER_DISPOSITION_COMMAND_EVIDENCE.md",
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
        "Finding namespace: `EXT-SIEM-ADAPTER-###`",
        "continue_architecture_planning",
        "revise_before_more_planning",
        "block_runtime_implementation",
        "SIEM-shaped export adapter",
    ]:
        if phrase not in prompt:
            failures.append(f"packet prompt is missing phrase: {phrase}")
    for phrase in [
        "What This Packet Does Not Prove",
        "does not approve SIEM adapter runtime behavior",
        "does not close `ERG-008`",
    ]:
        if phrase not in index:
            failures.append(f"packet index is missing phrase: {phrase}")
    for phrase in [
        '"runtime_changes_allowed": false',
        '"siem_adapter_allowed": false',
        '"hosted_telemetry_allowed": false',
        '"remote_delivery_allowed": false',
        '"custody_grade_audit_allowed": false',
        '"external_notarization_allowed": false',
        '"immutable_storage_allowed": false',
        '"production_identity_allowed": false',
        '"runtime_postgres_allowed": false',
        '"compliance_claims_allowed": false',
        '"security_operations_control_plane_allowed": false',
        '"new_power_classes_allowed": false',
        '"closes_erg_008": false',
    ]:
        if phrase not in evidence:
            failures.append(f"command evidence is missing boundary flag: {phrase}")
    for target in [
        "siem-export-adapter-disposition-packet:",
        "siem-export-adapter-disposition-packet-check:",
    ]:
        if target not in makefile:
            failures.append(f"Make target is missing: {target.rstrip(':')}")
    if "siem-export-adapter-disposition-packet-check" not in release_check_body:
        failures.append("SIEM export adapter disposition check missing from release-check")
    if "$(MAKE) siem-export-adapter-disposition-packet" not in review_candidate_body:
        failures.append("SIEM export adapter disposition missing from review-candidate")
    if "siem-export-adapter-disposition-packet-check" not in release_guardrails:
        failures.append("release guardrails do not require SIEM disposition check")
    if "docs/codex/siem-export-adapter-disposition-packet.md" not in docs_site:
        failures.append("SIEM disposition doc missing from docs-site")
    if "docs/codex/siem-export-adapter-disposition-packet.md" not in review_docs:
        failures.append("SIEM disposition doc missing from review docs")
    if "SIEM Export Adapter Disposition Packet" not in review_index:
        failures.append("review-docs index missing SIEM disposition entry")
    if "make siem-export-adapter-disposition-packet" not in readme:
        failures.append("README is missing SIEM disposition command")
    for container_name, container_text in {
        "enterprise runway": runway,
        "enterprise gap matrix": gap_matrix,
        "post-RC decision register": decision_register,
    }.items():
        if "siem-export-adapter-disposition-packet.md" not in container_text:
            failures.append(f"{container_name} is missing SIEM disposition pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "output_dir": str(DEFAULT_OUTPUT_DIR),
        "artifact_count": len(expected),
        "tool_count": 24,
        "erg_008_status": "planning_only",
        "prd_id": "PRD-SIEM-EXPORT-001",
        "runtime_changes_allowed": False,
        "siem_adapter_allowed": False,
        "hosted_telemetry_allowed": False,
        "remote_delivery_allowed": False,
        "custody_grade_audit_allowed": False,
        "external_notarization_allowed": False,
        "immutable_storage_allowed": False,
        "production_identity_allowed": False,
        "runtime_postgres_allowed": False,
        "compliance_claims_allowed": False,
        "security_operations_control_plane_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
        "closes_erg_008": False,
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
        raise SiemExportAdapterDispositionPacketError(
            "working tree is dirty; commit before disposition packet handoff"
        )

    architecture = siem_export_adapter_architecture_check.build_report(repo_root)
    evidence_design = siem_evidence_design_check.build_report(repo_root)
    decision_register = post_rc_decision_register_check.build_report(repo_root)
    gap_matrix = enterprise_readiness_gap_matrix_check.build_report(repo_root)
    runway = enterprise_readiness_runway_check.build_report(repo_root)
    accepted_risks = accepted_risk_register.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    reports = {
        "architecture_check": architecture,
        "siem_evidence_design_check": evidence_design,
        "post_rc_decision_register_check": decision_register,
        "enterprise_gap_matrix_check": gap_matrix,
        "enterprise_runway_check": runway,
        "accepted_risk_register_check": accepted_risks,
        "no_new_powers": no_new_powers,
        "tool_surface": tool_surface,
    }
    failures = [
        f"{key}: {failure}"
        for key, report in reports.items()
        for failure in report.get("failures", [])
    ]
    if failures:
        raise SiemExportAdapterDispositionPacketError("; ".join(failures))

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context = {
        "commit": commit,
        "dirty": dirty,
        "run_commands": run_commands,
    }
    files = {
        "00_SIEM_EXPORT_ADAPTER_DISPOSITION_INDEX.md": _index(context),
        "01_SIEM_EXPORT_ADAPTER_DISPOSITION_PROMPT.md": _prompt(context),
        "02_SIEM_EXPORT_ADAPTER_DISPOSITION_AND_ARCHITECTURE.md": _bundle_docs(
            repo_root, DISPOSITION_DOCS
        ),
        "03_SIEM_EXPORT_ADAPTER_REVIEW_POINTERS.md": _bundle_docs(
            repo_root, REVIEW_POINTER_DOCS
        ),
        "04_SIEM_EXPORT_ADAPTER_DISPOSITION_COMMAND_EVIDENCE.md": _command_evidence(
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
    return f"""# SIEM Export Adapter Disposition Packet

This packet packages the `ERG-008` architecture-disposition question set, current SIEM-shaped
evidence design, adapter architecture evidence, decision-register pointers, and command evidence. It
is a review handoff for deciding whether the SIEM export adapter lane may continue architecture
planning.

## Boundary

- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Command evidence executed: `{str(context["run_commands"]).lower()}`.
- Tool count remains `24`.
- Current `ERG-008` status remains `planning_only`.
- Post-RC decision ID: `PRD-SIEM-EXPORT-001`.
- This packet does not close `ERG-008`.
- This packet does not approve SIEM adapter runtime behavior, hosted telemetry, remote delivery,
  custody-grade audit claims, external notarization, immutable storage, production identity, runtime
  Postgres, compliance automation, security-operations control-plane claims, or any new governed
  tool power.

## Artifacts

1. `00_SIEM_EXPORT_ADAPTER_DISPOSITION_INDEX.md`
2. `01_SIEM_EXPORT_ADAPTER_DISPOSITION_PROMPT.md`
3. `02_SIEM_EXPORT_ADAPTER_DISPOSITION_AND_ARCHITECTURE.md`
4. `03_SIEM_EXPORT_ADAPTER_REVIEW_POINTERS.md`
5. `04_SIEM_EXPORT_ADAPTER_DISPOSITION_COMMAND_EVIDENCE.md`
6. `siem-export-adapter-disposition-artifact-hashes.json`

## What This Packet Does Not Prove

This packet does not prove external architecture review has happened, does not prove `ERG-008` is
closed, and does not approve SIEM adapter runtime behavior. A later post-RC decision record must
record reviewer disposition, findings, verification commands, and any matrix/status changes before
implementation planning can move.
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# SIEM Export Adapter Disposition Review Prompt

You are reviewing Ithildin's SIEM-shaped export adapter architecture lane for external/source
disposition.

Reviewed commit: `{context["commit"]}`
Area: `siem-export-adapter`
Finding namespace: `EXT-SIEM-ADAPTER-###`

## Required Disposition

Please answer every question:

1. Did the reviewer inspect the SIEM export adapter architecture packet, SIEM-shaped evidence
   design, evidence contracts, and decision evidence named in this packet?
2. Are the event schema, category allowlist, required fields, compatibility policy, and redaction
   denylist precise enough for continued architecture planning?
3. Are the delivery profile, retry, dead-letter, backpressure, destination authentication, safe
   diagnostics, and no-export behavior complete enough for continued planning?
4. Is the local signing/verification story clear without implying custody, notarization, or stronger
   trust roots than local operator evidence?
5. Does the packet keep SIEM export delivery separate from current local-preview runtime behavior?
6. Are there any critical/high findings?
7. If there are no critical/high findings, may the lane continue architecture planning while
   `ERG-008` remains planning-only and runtime adapter implementation remains blocked?
8. Does the reviewer explicitly avoid approving SIEM adapter runtime behavior, hosted telemetry,
   remote delivery, custody-grade audit, compliance automation, or security-operations control-plane
   claims?

Choose one disposition:

- `continue_architecture_planning`: current evidence is coherent for further architecture planning
  and review packets.
- `revise_before_more_planning`: gaps or ambiguous claims must be fixed before more planning.
- `block_runtime_implementation`: a blocking risk prevents implementation planning until a new
  decision record resolves it.

Use this exact finding shape for actionable findings:

{FINDING_TABLE}

If there are no implementation findings, explicitly say `no findings` or `finding_count: 0`.

Do not approve runtime implementation, SIEM adapter behavior, hosted telemetry, remote delivery,
custody-grade audit, external notarization, immutable storage, production identity, runtime
Postgres, compliance automation, hosted control plane, remote MCP, sandbox orchestration,
trusted-host promotion, shell/Docker/Kubernetes/browser governed powers, arbitrary HTTP, broad
filesystem writes, or public/security-product positioning.
"""


def _command_evidence(
    *,
    repo_root: Path,
    run_commands: bool,
    reports: dict[str, dict[str, Any]],
) -> str:
    lines = [
        "# SIEM Export Adapter Disposition Command Evidence",
        "",
        "## Boundary Flags",
        "",
        "```json",
        json.dumps(
            {
                "tool_count": 24,
                "erg_008_status": "planning_only",
                "prd_id": "PRD-SIEM-EXPORT-001",
                "runtime_changes_allowed": False,
                "siem_adapter_allowed": False,
                "hosted_telemetry_allowed": False,
                "remote_delivery_allowed": False,
                "custody_grade_audit_allowed": False,
                "external_notarization_allowed": False,
                "immutable_storage_allowed": False,
                "production_identity_allowed": False,
                "runtime_postgres_allowed": False,
                "compliance_claims_allowed": False,
                "security_operations_control_plane_allowed": False,
                "new_power_classes_allowed": False,
                "closes_erg_008": False,
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
                raise SiemExportAdapterDispositionPacketError(
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
            raise SiemExportAdapterDispositionPacketError(f"missing doc: {doc}")
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
        raise SiemExportAdapterDispositionPacketError(
            "not an Ithildin project root; missing " + ", ".join(missing)
        )


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin SIEM export adapter disposition packet check",
        f"valid: {str(report['valid']).lower()}",
        f"output_dir: {report['output_dir']}",
        f"artifact_count: {report['artifact_count']}",
        f"tool_count: {report['tool_count']}",
        f"erg_008_status: {report['erg_008_status']}",
        f"prd_id: {report['prd_id']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"hosted_telemetry_allowed: {str(report['hosted_telemetry_allowed']).lower()}",
        f"remote_delivery_allowed: {str(report['remote_delivery_allowed']).lower()}",
        f"custody_grade_audit_allowed: {str(report['custody_grade_audit_allowed']).lower()}",
        f"external_notarization_allowed: {str(report['external_notarization_allowed']).lower()}",
        f"immutable_storage_allowed: {str(report['immutable_storage_allowed']).lower()}",
        f"production_identity_allowed: {str(report['production_identity_allowed']).lower()}",
        f"runtime_postgres_allowed: {str(report['runtime_postgres_allowed']).lower()}",
        f"compliance_claims_allowed: {str(report['compliance_claims_allowed']).lower()}",
        "security_operations_control_plane_allowed: "
        f"{str(report['security_operations_control_plane_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"closes_erg_008: {str(report['closes_erg_008']).lower()}",
    ]
    if report["failures"]:
        lines.append("")
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

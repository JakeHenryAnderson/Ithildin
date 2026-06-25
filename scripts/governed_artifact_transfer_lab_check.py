"""Validate governed artifact transfer lab docs, packet, and boundaries."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    governed_artifact_transfer_lab,
    no_new_powers_guardrail,
    review_docs,
    tool_surface_invariant_gate,
)

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/governed-artifact-transfer-lab.md"
REQUIRED_DOC_PHRASES = [
    "Stage 1 Part 1: Ithildin-Only Known Good",
    "Stage 1 Part 2: Mission Control Wrapper",
    "Stage 2A: Transfer Evidence Contract",
    "Stage 2B: Simulated Sandbox Working Copy",
    "Stage 2C: Real VM Readiness Plan",
    "make governed-artifact-transfer-lab",
    "make governed-artifact-transfer-lab-check",
    "make governed-artifact-transfer-stage2",
    "make governed-artifact-transfer-stage2-check",
    "mission_control_integration: `false`",
    "vm_or_sandbox: `false`",
    "mission_control_integration: `metadata_only`",
    "vm_or_sandbox: `simulated_directory_only`",
    "tool count remains `23`",
    "does not add governed tools",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report(ROOT)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])

    if not DOC.exists():
        failures.append("governed artifact transfer lab doc is missing")
    else:
        text = DOC.read_text(encoding="utf-8")
        for phrase in REQUIRED_DOC_PHRASES:
            if phrase not in text:
                failures.append(f"governed artifact transfer lab doc is missing phrase: {phrase}")
    rel_path = DOC.relative_to(repo_root).as_posix()
    if rel_path not in review_docs.REVIEW_DOCS:
        failures.append("governed artifact transfer lab doc is missing from review docs")
    if rel_path not in docs_site:
        failures.append("governed artifact transfer lab doc is missing from docs-site inputs")

    for target in [
        "governed-artifact-transfer-lab:",
        "governed-artifact-transfer-lab-check:",
        "governed-artifact-transfer-stage2:",
        "governed-artifact-transfer-stage2-check:",
    ]:
        if target not in makefile:
            failures.append(f"Make target is missing: {target.rstrip(':')}")
    if "governed-artifact-transfer-lab-check" not in release_check_body:
        failures.append("governed-artifact-transfer-lab-check is missing from release-check")
    if "governed-artifact-transfer-stage2-check" not in release_check_body:
        failures.append("governed-artifact-transfer-stage2-check is missing from release-check")
    for phrase in [
        "make governed-artifact-transfer-lab",
        "make governed-artifact-transfer-lab-check",
        "make governed-artifact-transfer-stage2",
        "make governed-artifact-transfer-stage2-check",
    ]:
        if phrase not in readme:
            failures.append(f"README is missing phrase: {phrase}")

    packet_report = _packet_report(repo_root)
    failures.extend(packet_report["failures"])

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "tool_count": tool_surface.get("tool_count"),
        "runtime_changes_allowed": False,
        "mission_control_integration": False,
        "vm_or_sandbox": False,
        "new_power_classes_allowed": False,
        "packet": packet_report,
    }


def _packet_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "lab"
        governed_artifact_transfer_lab.build_lab(
            repo_root=repo_root,
            output_dir=output_dir,
            allow_dirty=True,
        )
        manifest_path = output_dir / "evidence/manifest.json"
        stage2_manifest_path = output_dir / "evidence/stage2-simulated-sandbox-manifest.json"
        handoff_path = output_dir / "mission-control-handoff/mission-control-handoff.json"
        hash_path = output_dir / governed_artifact_transfer_lab.HASH_MANIFEST
        summary_path = output_dir / "staging/summary.md"
        for path in [
            manifest_path,
            stage2_manifest_path,
            handoff_path,
            hash_path,
            summary_path,
            output_dir / "STAGE_1_LAB_INDEX.md",
            output_dir / "STAGE_2_SIMULATED_SANDBOX_TRANSFER.md",
            output_dir / "STAGE_2_REAL_VM_READINESS_PLAN.md",
        ]:
            if not path.exists():
                failures.append(f"generated packet is missing {path.relative_to(output_dir)}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        stage2_manifest = json.loads(stage2_manifest_path.read_text(encoding="utf-8"))
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
        hashes = json.loads(hash_path.read_text(encoding="utf-8"))
        if manifest.get("tool_count") != 23:
            failures.append("generated manifest has unexpected tool_count")
        if manifest.get("mission_control_integration") is not False:
            failures.append("generated manifest must keep Mission Control disabled for Part 1")
        if manifest.get("vm_or_sandbox") is not False:
            failures.append("generated manifest must keep VM/sandbox disabled for Part 1")
        if manifest.get("governed_tool_calls_performed") is not False:
            failures.append("generated manifest must not claim live governed tool calls")
        if "no_new_governed_tools" not in manifest.get("boundaries", []):
            failures.append("generated manifest is missing no-new-governed-tools boundary")
        if handoff.get("mission_control_integration") != "metadata_only":
            failures.append("Mission Control handoff must remain metadata-only")
        if handoff.get("source_sha256") != manifest["source"]["sha256"]:
            failures.append("Mission Control handoff source hash does not match Stage 1")
        if handoff.get("output_sha256") != manifest["output"]["sha256"]:
            failures.append("Mission Control handoff output hash does not match Stage 1")
        if stage2_manifest.get("vm_or_sandbox") != "simulated_directory_only":
            failures.append("Stage 2 manifest must use simulated directory sandbox only")
        if stage2_manifest.get("real_vm_or_container_started") is not False:
            failures.append("Stage 2 manifest must not claim real VM/container startup")
        if stage2_manifest.get("sandbox_lifecycle_control") is not False:
            failures.append("Stage 2 manifest must not claim sandbox lifecycle control")
        checks = stage2_manifest.get("checks", {})
        for name in [
            "host_source_matches_sandbox_copy",
            "sandbox_output_matches_returned_staging",
            "stage1_source_matches_host_source",
            "stage1_output_matches_stage2_returned_output",
        ]:
            if checks.get(name) is not True:
                failures.append(f"Stage 2 check failed: {name}")
        if stage2_manifest.get("approval", {}).get("auto_promotion_performed") is not False:
            failures.append("Stage 2 manifest must not claim automatic promotion")
        artifact_paths = {entry["path"] for entry in hashes.get("artifacts", [])}
        for expected in [
            "STAGE_1_LAB_INDEX.md",
            "STAGE_1_LAB_TRANSCRIPT.md",
            "STAGE_1_PART_2_MISSION_CONTROL_NOTES.md",
            "STAGE_2_SIMULATED_SANDBOX_TRANSFER.md",
            "STAGE_2_REAL_VM_READINESS_PLAN.md",
            "staging/summary.md",
            "evidence/manifest.json",
            "evidence/stage2-simulated-sandbox-manifest.json",
            "mission-control-handoff/mission-control-handoff.json",
            "mission-control-handoff/MISSION_CONTROL_HANDOFF.md",
            "simulated-sandbox/host-source/article.txt",
            "simulated-sandbox/sandbox-working-copy/article.txt",
            "simulated-sandbox/sandbox-output/summary.md",
            "simulated-sandbox/host-staging/summary.md",
        ]:
            if expected not in artifact_paths:
                failures.append(f"artifact hashes are missing {expected}")
        summary_text = summary_path.read_text(encoding="utf-8")
        for forbidden in [
            "Mission Control mission ID:",
            "vm_or_sandbox: `true`",
            "shell output",
            "real_vm_or_container_started: true",
        ]:
            if forbidden in summary_text:
                failures.append(f"summary contains forbidden text: {forbidden}")
    return {"valid": not failures, "failures": failures}


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin governed artifact transfer lab check",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        "mission_control_integration: false",
        "vm_or_sandbox: false",
        "runtime_changes_allowed: false",
        "new_power_classes_allowed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

"""Validate the Hello World Mission Control handoff packet and wiring."""

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
    hello_world_mission_control_handoff,
    no_new_powers_guardrail,
    review_docs,
    tool_surface_invariant_gate,
)

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/hello-world-mission-control-handoff.md"
REQUIRED_DOC_PHRASES = [
    "make hello-world-mission-control-handoff",
    "make hello-world-mission-control-handoff-check",
    "metadata-only handoff",
    "Mission Control runtime behavior: `false`",
    "local LLM runtime behavior: `false`",
    "host promotion performed: `false`",
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
    makefile = repo_root.joinpath("Makefile").read_text(encoding="utf-8")
    readme = repo_root.joinpath("README.md").read_text(encoding="utf-8")
    docs_site = repo_root.joinpath("scripts/build_docs_site.py").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])

    if not DOC.exists():
        failures.append("Hello World Mission Control handoff doc is missing")
    else:
        text = DOC.read_text(encoding="utf-8")
        for phrase in REQUIRED_DOC_PHRASES:
            if phrase not in text:
                failures.append(f"Hello World Mission Control doc is missing phrase: {phrase}")
    rel_path = DOC.relative_to(repo_root).as_posix()
    if rel_path not in review_docs.REVIEW_DOCS:
        failures.append("Hello World Mission Control doc is missing from review docs")
    if rel_path not in docs_site:
        failures.append("Hello World Mission Control doc is missing from docs-site inputs")
    for target in [
        "hello-world-mission-control-handoff:",
        "hello-world-mission-control-handoff-check:",
    ]:
        if target not in makefile:
            failures.append(f"Make target is missing: {target.rstrip(':')}")
    if "hello-world-mission-control-handoff-check" not in release_check_body:
        failures.append("hello-world-mission-control-handoff-check is missing from release-check")
    if "$(MAKE) hello-world-mission-control-handoff" not in review_candidate_body:
        failures.append("hello-world-mission-control-handoff is missing from review-candidate")
    for phrase in [
        "make hello-world-mission-control-handoff",
        "make hello-world-mission-control-handoff-check",
    ]:
        if phrase not in readme:
            failures.append(f"README is missing phrase: {phrase}")

    packet_report = _packet_report()
    failures.extend(packet_report["failures"])
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "status": "metadata_only",
        "tool_count": tool_surface.get("tool_count"),
        "mission_control_runtime_behavior": False,
        "mission_control_authority": "display_and_operator_review_only",
        "local_llm_runtime_behavior": False,
        "real_vm_or_container_started": False,
        "host_promotion_performed": False,
        "packet": packet_report,
    }


def _packet_report() -> dict[str, Any]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "mission-control-handoff"
        hello_world_mission_control_handoff.build_handoff(output_dir)
        required = {
            hello_world_mission_control_handoff.INDEX_NAME,
            hello_world_mission_control_handoff.JSON_NAME,
            hello_world_mission_control_handoff.HASHES_NAME,
            hello_world_mission_control_handoff.OBSERVED_DIR_NAME,
        }
        if {path.name for path in output_dir.iterdir()} != required:
            failures.append("generated Mission Control handoff has unexpected top-level files")
        handoff = json.loads(
            output_dir.joinpath(hello_world_mission_control_handoff.JSON_NAME).read_text(
                encoding="utf-8"
            )
        )
        index = output_dir.joinpath(hello_world_mission_control_handoff.INDEX_NAME).read_text(
            encoding="utf-8"
        )
        hashes = json.loads(
            output_dir.joinpath(hello_world_mission_control_handoff.HASHES_NAME).read_text(
                encoding="utf-8"
            )
        )
        if handoff.get("status") != "metadata_only":
            failures.append("handoff status must be metadata_only")
        if handoff.get("tool_count") != 24:
            failures.append("handoff has unexpected tool count")
        if handoff.get("ithildin_remains_policy_authority") is not True:
            failures.append("handoff must keep Ithildin as policy authority")
        for key in [
            "mission_control_runtime_behavior",
            "local_llm_runtime_behavior",
            "real_vm_or_container_started",
            "sandbox_orchestration_performed",
            "shell_execution_performed",
            "host_promotion_performed",
        ]:
            if handoff.get(key) is not False:
                failures.append(f"handoff must report {key}: false")
        evidence = handoff["ithildin_evidence"]
        if evidence.get("request_status") != "approval_required":
            failures.append("handoff request status must be approval_required")
        if evidence.get("approval_status") != "executed":
            failures.append("handoff approval status must be executed")
        if evidence.get("execution_status") != "completed":
            failures.append("handoff execution status must be completed")
        if evidence.get("artifact_hash_matches_execution") is not True:
            failures.append("handoff artifact hash must match execution")
        if evidence.get("audit_valid") is not True:
            failures.append("handoff audit status must be valid")
        if handoff["mission"].get("promotion_status") != "not_promoted":
            failures.append("handoff must keep promotion status not_promoted")
        attachment_paths = {entry["path"] for entry in handoff.get("attachments", [])}
        for expected in [
            "observed-hello-world/HELLO_WORLD_SANDBOX_OBSERVED_DEMO.md",
            "observed-hello-world/hello-world-sandbox-observed-demo.json",
            "observed-hello-world/observed-governed-tool/SANDBOX_ARTIFACT_OBSERVED_DEMO.md",
        ]:
            if expected not in attachment_paths:
                failures.append(f"handoff attachments are missing {expected}")
        artifact_paths = {entry["path"] for entry in hashes.get("artifacts", [])}
        for expected in [
            hello_world_mission_control_handoff.INDEX_NAME,
            hello_world_mission_control_handoff.JSON_NAME,
            "observed-hello-world/HELLO_WORLD_SANDBOX_OBSERVED_DEMO.md",
            "observed-hello-world/hello-world-sandbox-observed-demo.json",
        ]:
            if expected not in artifact_paths:
                failures.append(f"artifact hashes are missing {expected}")
        for forbidden in [
            "content\":",
            "real VM or container started: `true`",
            "host promotion performed: `true`",
            "production-ready",
            "compliance-grade",
        ]:
            if forbidden in index:
                failures.append(f"handoff index contains forbidden content: {forbidden}")
    return {"valid": not failures, "failures": failures}


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Hello World Mission Control handoff check",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        "mission_control_runtime_behavior: false",
        "local_llm_runtime_behavior: false",
        "real_vm_or_container_started: false",
        "host_promotion_performed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

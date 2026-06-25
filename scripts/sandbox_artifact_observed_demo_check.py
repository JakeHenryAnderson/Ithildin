"""Validate the observed sandbox.artifact.write_text demo wiring and artifact shape."""

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
    no_new_powers_guardrail,
    review_docs,
    sandbox_artifact_observed_demo,
    tool_surface_invariant_gate,
)

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/sandbox-artifact-observed-demo.md"
REQUIRED_DOC_PHRASES = [
    "make sandbox-artifact-observed-demo",
    "make sandbox-artifact-observed-demo-check",
    "observed local fixture execution",
    "governed tool calls performed",
    "no host promotion",
    "local-preview only",
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
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])

    if not DOC.exists():
        failures.append("sandbox artifact observed demo doc is missing")
    else:
        text = DOC.read_text(encoding="utf-8")
        for phrase in REQUIRED_DOC_PHRASES:
            if phrase not in text:
                failures.append(f"sandbox artifact observed demo doc is missing phrase: {phrase}")
    rel_path = DOC.relative_to(repo_root).as_posix()
    if rel_path not in review_docs.REVIEW_DOCS:
        failures.append("sandbox artifact observed demo doc is missing from review docs")
    if rel_path not in docs_site:
        failures.append("sandbox artifact observed demo doc is missing from docs-site inputs")
    for target in [
        "sandbox-artifact-observed-demo:",
        "sandbox-artifact-observed-demo-check:",
    ]:
        if target not in makefile:
            failures.append(f"Make target is missing: {target.rstrip(':')}")
    if "sandbox-artifact-observed-demo-check" not in release_check_body:
        failures.append("sandbox-artifact-observed-demo-check is missing from release-check")
    if "$(MAKE) sandbox-artifact-observed-demo" not in review_candidate_body:
        failures.append("sandbox-artifact-observed-demo is missing from review-candidate")
    for phrase in [
        "make sandbox-artifact-observed-demo",
        "make sandbox-artifact-observed-demo-check",
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
        "governed_tool_calls_performed": True,
        "mission_control_runtime_behavior": False,
        "real_vm_or_container_started": False,
        "host_promotion_performed": False,
        "packet": packet_report,
    }


def _packet_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "sandbox-artifact-observed"
        sandbox_artifact_observed_demo.build_demo(output_dir)
        expected = {
            sandbox_artifact_observed_demo.TRANSCRIPT_NAME,
            sandbox_artifact_observed_demo.JSON_NAME,
            sandbox_artifact_observed_demo.HASHES_NAME,
        }
        if {path.name for path in output_dir.iterdir()} != expected:
            failures.append("generated observed demo packet has unexpected file set")
        payload = json.loads(
            output_dir.joinpath(sandbox_artifact_observed_demo.JSON_NAME).read_text(
                encoding="utf-8"
            )
        )
        transcript = output_dir.joinpath(sandbox_artifact_observed_demo.TRANSCRIPT_NAME).read_text(
            encoding="utf-8"
        )
        hashes = json.loads(
            output_dir.joinpath(sandbox_artifact_observed_demo.HASHES_NAME).read_text(
                encoding="utf-8"
            )
        )
        if payload.get("status") != "observed_local_fixture":
            failures.append("observed demo JSON has unexpected status")
        if payload.get("tool_name") != "sandbox.artifact.write_text":
            failures.append("observed demo JSON has unexpected tool name")
        if payload.get("tool_count") != 24:
            failures.append("observed demo JSON has unexpected tool count")
        if payload.get("governed_tool_calls_performed") is not True:
            failures.append("observed demo must report governed tool calls performed")
        for key in [
            "mission_control_runtime_behavior",
            "real_vm_or_container_started",
            "sandbox_orchestration_performed",
            "shell_execution_performed",
            "host_promotion_performed",
        ]:
            if payload.get(key) is not False:
                failures.append(f"observed demo must report {key}: false")
        if payload["request"].get("status") != "approval_required":
            failures.append("observed demo initial request did not require approval")
        if payload["execution"].get("status") != "completed":
            failures.append("observed demo execution did not complete")
        if payload["approval"].get("status") != "executed":
            failures.append("observed demo approval was not consumed exactly once")
        if payload["approval"].get("raw_content_stored_in_scope") is not False:
            failures.append("approval scope must not store raw content")
        if payload["artifact"].get("present") is not True:
            failures.append("observed demo artifact is not present")
        if payload["artifact"].get("content_matches_execution_hash") is not True:
            failures.append("observed demo artifact hash does not match execution hash")
        if payload["audit"]["verification"].get("valid") is not True:
            failures.append("observed demo audit chain did not verify")
        for forbidden in [
            sandbox_artifact_observed_demo.DEMO_CONTENT,
            "Hello World",
            "ithildin-sandbox-artifact-observed-",
            "content\":",
        ]:
            if forbidden in transcript:
                failures.append(f"transcript contains forbidden content: {forbidden}")
        artifact_paths = {entry["path"] for entry in hashes.get("artifacts", [])}
        for relative in [
            sandbox_artifact_observed_demo.TRANSCRIPT_NAME,
            sandbox_artifact_observed_demo.JSON_NAME,
        ]:
            if relative not in artifact_paths:
                failures.append(f"artifact hashes are missing {relative}")
    return {"valid": not failures, "failures": failures}


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox artifact observed demo check",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        "governed_tool_calls_performed: true",
        "mission_control_runtime_behavior: false",
        "real_vm_or_container_started: false",
        "host_promotion_performed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

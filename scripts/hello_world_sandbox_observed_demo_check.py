"""Validate the observed Hello World sandbox demo packet and wiring."""

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
    hello_world_sandbox_observed_demo,
    no_new_powers_guardrail,
    review_docs,
    tool_surface_invariant_gate,
)

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/hello-world-sandbox-observed-demo.md"
REQUIRED_DOC_PHRASES = [
    "make hello-world-sandbox-observed-demo",
    "make hello-world-sandbox-observed-demo-check",
    "observed local fixture execution",
    "governed tool calls performed",
    "Mission Control runtime behavior: `false`",
    "Local LLM runtime behavior: `false`",
    "Host promotion performed: `false`",
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
        failures.append("Hello World observed demo doc is missing")
    else:
        text = DOC.read_text(encoding="utf-8")
        for phrase in REQUIRED_DOC_PHRASES:
            if phrase not in text:
                failures.append(f"Hello World observed demo doc is missing phrase: {phrase}")
    rel_path = DOC.relative_to(repo_root).as_posix()
    if rel_path not in review_docs.REVIEW_DOCS:
        failures.append("Hello World observed demo doc is missing from review docs")
    if rel_path not in docs_site:
        failures.append("Hello World observed demo doc is missing from docs-site inputs")
    for target in [
        "hello-world-sandbox-observed-demo:",
        "hello-world-sandbox-observed-demo-check:",
    ]:
        if target not in makefile:
            failures.append(f"Make target is missing: {target.rstrip(':')}")
    if "hello-world-sandbox-observed-demo-check" not in release_check_body:
        failures.append("hello-world-sandbox-observed-demo-check is missing from release-check")
    if "$(MAKE) hello-world-sandbox-observed-demo" not in review_candidate_body:
        failures.append("hello-world-sandbox-observed-demo is missing from review-candidate")
    for phrase in [
        "make hello-world-sandbox-observed-demo",
        "make hello-world-sandbox-observed-demo-check",
    ]:
        if phrase not in readme:
            failures.append(f"README is missing phrase: {phrase}")

    packet_report = _packet_report()
    failures.extend(packet_report["failures"])
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "tool_count": tool_surface.get("tool_count"),
        "governed_tool_calls_performed": True,
        "mission_control_runtime_behavior": False,
        "local_llm_runtime_behavior": False,
        "real_vm_or_container_started": False,
        "host_promotion_performed": False,
        "packet": packet_report,
    }


def _packet_report() -> dict[str, Any]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "hello-observed"
        hello_world_sandbox_observed_demo.build_demo(output_dir)
        expected = {
            hello_world_sandbox_observed_demo.INDEX_NAME,
            hello_world_sandbox_observed_demo.JSON_NAME,
            hello_world_sandbox_observed_demo.HASHES_NAME,
            hello_world_sandbox_observed_demo.OBSERVED_DIR_NAME,
        }
        if {path.name for path in output_dir.iterdir()} != expected:
            failures.append("generated observed Hello World packet has unexpected top-level files")
        payload = json.loads(
            output_dir.joinpath(hello_world_sandbox_observed_demo.JSON_NAME).read_text(
                encoding="utf-8"
            )
        )
        index = output_dir.joinpath(hello_world_sandbox_observed_demo.INDEX_NAME).read_text(
            encoding="utf-8"
        )
        hashes = json.loads(
            output_dir.joinpath(hello_world_sandbox_observed_demo.HASHES_NAME).read_text(
                encoding="utf-8"
            )
        )
        observed_json = (
            output_dir
            / hello_world_sandbox_observed_demo.OBSERVED_DIR_NAME
            / "sandbox-artifact-observed-demo.json"
        )
        if not observed_json.exists():
            failures.append("observed governed tool JSON is missing")
        if payload.get("status") != "observed_hello_world_local_fixture":
            failures.append("observed Hello World JSON has unexpected status")
        if payload.get("tool_name") != "sandbox.artifact.write_text":
            failures.append("observed Hello World JSON has unexpected tool name")
        if payload.get("tool_count") != 24:
            failures.append("observed Hello World JSON has unexpected tool count")
        for key in [
            "governed_tool_calls_performed",
        ]:
            if payload.get(key) is not True:
                failures.append(f"observed Hello World JSON must report {key}: true")
        for key in [
            "mission_control_runtime_behavior",
            "local_llm_runtime_behavior",
            "real_vm_or_container_started",
            "sandbox_orchestration_performed",
            "shell_execution_performed",
            "host_promotion_performed",
        ]:
            if payload.get(key) is not False:
                failures.append(f"observed Hello World JSON must report {key}: false")
        if payload["governed_request"].get("status") != "approval_required":
            failures.append("observed Hello World request did not require approval")
        if payload["approval"].get("status") != "executed":
            failures.append("observed Hello World approval was not consumed")
        if payload["approval"].get("raw_content_stored_in_scope") is not False:
            failures.append("observed Hello World approval scope stored raw content")
        if payload["execution"].get("status") != "completed":
            failures.append("observed Hello World execution did not complete")
        if payload["artifact"].get("present") is not True:
            failures.append("observed Hello World artifact is not present")
        if payload["artifact"].get("hash_matches_execution") is not True:
            failures.append("observed Hello World artifact hash does not match execution")
        if payload["audit"].get("valid") is not True:
            failures.append("observed Hello World audit chain did not verify")
        for forbidden in [
            "content\":",
            "ithildin-sandbox-artifact-observed-",
            "real VM or container started: `true`",
            "host promotion performed: `true`",
        ]:
            if forbidden in index:
                failures.append(
                    f"observed Hello World index contains forbidden content: {forbidden}"
                )
        artifact_paths = {entry["path"] for entry in hashes.get("artifacts", [])}
        for relative in [
            hello_world_sandbox_observed_demo.INDEX_NAME,
            hello_world_sandbox_observed_demo.JSON_NAME,
            f"{hello_world_sandbox_observed_demo.OBSERVED_DIR_NAME}/SANDBOX_ARTIFACT_OBSERVED_DEMO.md",
            f"{hello_world_sandbox_observed_demo.OBSERVED_DIR_NAME}/sandbox-artifact-observed-demo.json",
        ]:
            if relative not in artifact_paths:
                failures.append(f"artifact hashes are missing {relative}")
    return {"valid": not failures, "failures": failures}


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Hello World observed sandbox demo check",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        "governed_tool_calls_performed: true",
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

"""Validate the evidence-only Hello World sandbox demo packet."""

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
    hello_world_sandbox_demo_packet,
    no_new_powers_guardrail,
    review_docs,
    tool_surface_invariant_gate,
)

ROOT = Path(__file__).resolve().parents[1]
ROADMAP_DOC = ROOT / "docs/codex/hello-world-sandbox-demo-roadmap.md"
REQUIRED_DOC_PHRASES = [
    "make hello-world-sandbox-demo-packet",
    "make hello-world-sandbox-demo-packet-check",
    "runtime write powers remain blocked",
    "tool count remains `23`",
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
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])

    if not ROADMAP_DOC.exists():
        failures.append("Hello World sandbox demo roadmap doc is missing")
    else:
        text = ROADMAP_DOC.read_text(encoding="utf-8")
        for phrase in REQUIRED_DOC_PHRASES:
            if phrase not in text:
                failures.append(f"Hello World roadmap is missing phrase: {phrase}")
    rel_path = ROADMAP_DOC.relative_to(repo_root).as_posix()
    if rel_path not in review_docs.REVIEW_DOCS:
        failures.append("Hello World roadmap is missing from review docs")
    if rel_path not in docs_site:
        failures.append("Hello World roadmap is missing from docs-site inputs")
    for target in [
        "hello-world-sandbox-demo-packet:",
        "hello-world-sandbox-demo-packet-check:",
    ]:
        if target not in makefile:
            failures.append(f"Make target is missing: {target.rstrip(':')}")
    if "hello-world-sandbox-demo-packet-check" not in release_check_body:
        failures.append("hello-world-sandbox-demo-packet-check is missing from release-check")
    for phrase in [
        "make hello-world-sandbox-demo-packet",
        "make hello-world-sandbox-demo-packet-check",
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
        "write_capability_implemented": False,
        "mission_control_runtime_behavior": False,
        "real_vm_or_container_started": False,
        "packet": packet_report,
    }


def _packet_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "hello-world-demo"
        hello_world_sandbox_demo_packet.build_packet(
            repo_root=repo_root,
            output_dir=output_dir,
            allow_dirty=True,
        )
        required_paths = [
            "HELLO_WORLD_SANDBOX_DEMO_INDEX.md",
            "mission-control/mission-control-intent.json",
            "mission-control/local-llm-plan.json",
            "mission-control/operator-approval-required.json",
            "evidence/demo-manifest.json",
            "evidence/promotion-evidence-draft.json",
            "simulated-sandbox/hello-demo/hello.txt",
            "host-staging/hello-demo/hello.txt",
            "approved-host/hello-demo/hello.txt",
            "artifact-hashes.json",
        ]
        for relative in required_paths:
            if not (output_dir / relative).exists():
                failures.append(f"generated packet is missing {relative}")
        manifest = json.loads((output_dir / "evidence/demo-manifest.json").read_text())
        promotion = json.loads((output_dir / "evidence/promotion-evidence-draft.json").read_text())
        hashes = json.loads((output_dir / "artifact-hashes.json").read_text())
        hello_text = (output_dir / "simulated-sandbox/hello-demo/hello.txt").read_text(
            encoding="utf-8"
        )
        if hello_text != hello_world_sandbox_demo_packet.HELLO_CONTENT:
            failures.append("hello fixture content does not match expected fixture")
        for key in [
            "runtime_write_capability_implemented",
            "governed_tool_calls_performed",
            "mission_control_runtime_behavior",
            "real_vm_or_container_started",
            "sandbox_orchestration_performed",
            "shell_execution_performed",
            "host_promotion_performed",
        ]:
            if manifest.get(key) is not False:
                failures.append(f"demo manifest must report {key}: false")
        if manifest.get("tool_count") != 23:
            failures.append("demo manifest has unexpected tool_count")
        checks = manifest.get("checks", {})
        for key in [
            "sandbox_to_staging_hash_match",
            "staging_to_approved_hash_match",
            "hello_world_content_fixture",
        ]:
            if checks.get(key) is not True:
                failures.append(f"demo manifest check failed: {key}")
        if promotion.get("auto_promotion_performed") is not False:
            failures.append("promotion evidence must not claim automatic promotion")
        if promotion.get("real_host_promotion_performed") is not False:
            failures.append("promotion evidence must not claim real host promotion")
        artifact_paths = {entry["path"] for entry in hashes.get("artifacts", [])}
        for relative in required_paths[:-1]:
            if relative not in artifact_paths:
                failures.append(f"artifact hashes are missing {relative}")
        index = (output_dir / "HELLO_WORLD_SANDBOX_DEMO_INDEX.md").read_text(
            encoding="utf-8"
        )
        for forbidden in [
            "runtime write capability implemented: `true`",
            "governed tool calls performed: `true`",
            "real VM or container started: `true`",
            "host promotion performed: `true`",
        ]:
            if forbidden in index:
                failures.append(f"index contains forbidden text: {forbidden}")
    return {"valid": not failures, "failures": failures}


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Hello World sandbox demo packet check",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        "runtime_changes_allowed: false",
        "write_capability_implemented: false",
        "mission_control_runtime_behavior: false",
        "real_vm_or_container_started: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

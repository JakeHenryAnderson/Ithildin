"""Validate Hello World sandbox demo roadmap and preimplementation boundaries."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import no_new_powers_guardrail, review_docs, tool_surface_invariant_gate

ROOT = Path(__file__).resolve().parents[1]
ROADMAP = ROOT / "docs/codex/hello-world-sandbox-demo-roadmap.md"
PROPOSAL = ROOT / "docs/codex/capability-proposals/sandbox-artifact-write-text.md"
PROMOTION_CONTRACT = ROOT / "docs/codex/sandbox-promotion-evidence-contract.md"

REQUIRED_ROADMAP_PHRASES = [
    "Status: roadmap and staged demo target.",
    "hello-demo",
    "hello.txt",
    "Hello World",
    "Mission Control intent",
    "local LLM plan",
    "operator approval",
    "Ithildin-mediated bounded sandbox artifact creation",
    "Phase 1: Mission Control Evidence Attachment",
    "Phase 2: Sandbox Profile Contract",
    "Phase 3: Local LLM Plan Dry Run",
    "Phase 4: Bounded Artifact Creation Capability",
    "Phase 5: Hello World Sandbox Run",
    "Phase 6: Host Promotion",
    "make governed-artifact-transfer-stage2",
    "sandbox.artifact.write_text",
    "bounded sandbox artifact write is implemented",
]
REQUIRED_PROPOSAL_PHRASES = [
    "Status: design-only proposal",
    "Implementation is blocked",
    "workspace_id",
    "sandbox_id",
    "relative_path",
    "content",
    "overwrite",
    "content_sha256",
    "sandbox_artifact",
    "approval binding",
    "Audit metadata must not include file contents",
    "Non-Goals",
]
REQUIRED_PROMOTION_PHRASES = [
    "Status: design-only evidence contract.",
    "promotion_id",
    "source_artifact_sha256",
    "host_staging_sha256",
    "approved_host_sha256",
    "approval_id",
    "auto_promotion_performed",
    "no file contents",
]
FORBIDDEN_PHRASES = [
    "production-ready",
    "compliance-grade",
    "tamper-proof",
    "secure sandbox",
    "safe arbitrary tool use",
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

    _check_doc(
        repo_root,
        ROADMAP,
        REQUIRED_ROADMAP_PHRASES,
        failures,
        docs_site=docs_site,
    )
    _check_doc(
        repo_root,
        PROPOSAL,
        REQUIRED_PROPOSAL_PHRASES,
        failures,
        docs_site=docs_site,
    )
    _check_doc(
        repo_root,
        PROMOTION_CONTRACT,
        REQUIRED_PROMOTION_PHRASES,
        failures,
        docs_site=docs_site,
    )

    if "hello-world-sandbox-demo-check:" not in makefile:
        failures.append("Make target is missing: hello-world-sandbox-demo-check")
    if "hello-world-sandbox-demo-check" not in release_check_body:
        failures.append("hello-world-sandbox-demo-check is missing from release-check")
    if "make hello-world-sandbox-demo-check" not in readme:
        failures.append("README is missing make hello-world-sandbox-demo-check")
    if "tool count remains `24`" not in readme:
        failures.append("README is missing current tool count reference")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "tool_count": tool_surface.get("tool_count"),
        "runtime_changes_allowed": True,
        "new_power_classes_allowed": False,
        "write_capability_implemented": True,
        "mission_control_runtime_behavior_allowed": False,
        "vm_orchestration_allowed": False,
    }


def _check_doc(
    repo_root: Path,
    path: Path,
    phrases: list[str],
    failures: list[str],
    *,
    docs_site: str,
) -> None:
    rel_path = path.relative_to(repo_root).as_posix()
    if not path.exists():
        failures.append(f"doc is missing: {rel_path}")
        return
    text = path.read_text(encoding="utf-8")
    lowered = text.lower()
    for phrase in phrases:
        if phrase not in text:
            failures.append(f"{rel_path} is missing phrase: {phrase}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase in lowered:
            failures.append(f"{rel_path} contains forbidden phrase: {phrase}")
    if rel_path not in review_docs.REVIEW_DOCS:
        failures.append(f"{rel_path} is missing from review docs")
    if rel_path not in docs_site:
        failures.append(f"{rel_path} is missing from docs-site inputs")


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Hello World sandbox demo check",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        "runtime_changes_allowed: true",
        "new_power_classes_allowed: false",
        "write_capability_implemented: true",
        "mission_control_runtime_behavior_allowed: false",
        "vm_orchestration_allowed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

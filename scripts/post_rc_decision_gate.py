"""Validate the post-RC decision gate and boundary wiring."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/post-rc-decision-gate.md"

REQUIRED_PHRASES = [
    "Status: process gate for post-v1.0 RC boundary decisions.",
    "Current governed tool count: `24`",
    "Current selected capability: `not selected`",
    "Capability expansion remains blocked.",
    "Mission Control runtime behavior remains blocked.",
    "Live sandbox/VM/container inspection remains blocked.",
    "Local model invocation remains blocked.",
    "Trusted-host promotion remains blocked.",
    "SIEM adapter work remains blocked.",
    "Compliance automation and public/security-product positioning remain blocked.",
    "Decision Record Required Fields",
    "Decision ID.",
    "Target lane.",
    "Current boundary being changed.",
    "Allowed scope.",
    "Explicitly forbidden scope.",
    "Required source-review or external-review evidence.",
    "Required implementation plan.",
    "Rollback and stop conditions.",
    "Required tests, gates, and packet artifacts.",
    "Accepted-risk impact.",
    "Tool count and manifest impact.",
    "Go/no-go outcome.",
    "Lanes Requiring This Gate",
    "New governed tool or capability implementation after the v1.0 RC freeze.",
    "Mission Control runtime importer",
    "Live sandbox/VM/container inspection.",
    "Local model invocation.",
    "Trusted-host promotion.",
    "SIEM adapters or hosted telemetry.",
    "Production identity.",
    "Runtime Postgres.",
    "Remote MCP or hosted MCP.",
    "Plugin SDK behavior.",
    "Compliance automation or public/security-product positioning.",
    "Broad filesystem, network, or write expansion.",
    "v1.0-rc-feature-freeze.md",
    "v1.0-rc-final-handoff.md",
    "v1.0-rc-post-review-triage.md",
    "enterprise-readiness-runway.md",
    "mission-control-display-integration-proposal.md",
    "sandbox-vm-static-preflight-source-review.md",
    "sandbox-promotion-evidence-contract.md",
    "make post-rc-decision-gate",
]

FORBIDDEN_PHRASES = [
    "capability expansion allowed now",
    "Mission Control may execute",
    "trusted-host promotion is implemented",
    "compliance automation approved",
    "public security product approved",
    "sandbox orchestration is implemented",
    "local model invocation is implemented",
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
    doc_rel = DOC.relative_to(ROOT).as_posix()
    doc_path = repo_root / doc_rel
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    text = ""
    if not doc_path.exists():
        failures.append("post-RC decision gate doc is missing")
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"post-RC decision gate doc is missing phrase: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(f"post-RC decision gate doc contains forbidden phrase: {phrase}")

    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("post-RC decision gate doc is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("post-RC decision gate doc is missing from docs-site inputs")
    if "post-rc-decision-gate:" not in makefile:
        failures.append("Make target is missing: post-rc-decision-gate")
    if "post-rc-decision-gate" not in release_check_body:
        failures.append("post-rc-decision-gate is missing from release-check")
    if "make post-rc-decision-gate" not in readme:
        failures.append("README is missing post-RC decision gate command")
    if "post-RC decision gate" not in readme:
        failures.append("README is missing post-RC decision gate reference")

    decision_fields = [
        "Decision ID.",
        "Date.",
        "Owner and reviewer.",
        "Target lane.",
        "Trigger and requested change.",
        "Current boundary being changed.",
        "Allowed scope.",
        "Explicitly forbidden scope.",
        "Go/no-go outcome.",
    ]
    missing_decision_fields = [field for field in decision_fields if field not in text]
    for field in missing_decision_fields:
        failures.append(f"post-RC decision gate doc is missing decision field: {field}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "decision_gate_doc": doc_rel,
        "tool_count": 24,
        "capability_expansion_allowed": False,
        "mission_control_runtime_allowed": False,
        "sandbox_orchestration_allowed": False,
        "local_model_invocation_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "production_identity_allowed": False,
        "compliance_claims_allowed": False,
        "runtime_changes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin post-RC decision gate check",
        f"valid: {str(report['valid']).lower()}",
        f"decision_gate_doc: {report['decision_gate_doc']}",
        f"tool_count: {report['tool_count']}",
        f"capability_expansion_allowed: {str(report['capability_expansion_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"production_identity_allowed: {str(report['production_identity_allowed']).lower()}",
        f"compliance_claims_allowed: {str(report['compliance_claims_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

"""Validate post-RC decision record examples and release wiring."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import post_rc_decision_gate, post_rc_decision_record_template_check, review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/post-rc-decision-record-examples.md"

REQUIRED_PHRASES = [
    "Status: example pack for post-v1.0 RC boundary decisions.",
    "Current governed tool count: `24`",
    "Current selected capability: `not selected`",
    "PRD-MC-DISPLAY-001",
    "Decision record status: `approved_for_planning`",
    "go for planning only; no-go for runtime behavior.",
    "Mission Control display importer continuation.",
    "Mission Control execution authority",
    "policy authority",
    "approval authority",
    "audit authority",
    "local-model runner behavior",
    "VM/container management",
    "sandbox orchestration",
    "trusted-host promotion",
    "PRD-SANDBOX-PREFLIGHT-001",
    "Decision record status: `no_go`",
    "live sandbox/VM preflight",
    "live VM/container inspection",
    "SSH",
    "shell",
    "Docker socket access",
    "Kubernetes tools",
    "runtime preflight runner behavior",
    "no-go for live runtime behavior.",
    "PRD-CAPABILITY-001",
    "new governed tool after the v1.0 RC freeze",
    "manifest addition",
    "executor code",
    "policy/rule semantics",
    "MCP/API behavior",
    "no-go for runtime implementation; go for design packet work only.",
    "Tool count impact: none",
    "Runtime surfaces touched: none.",
    "make post-rc-decision-record-examples-check",
    "make post-rc-decision-record-template-check",
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
    review_index = (repo_root / "docs/codex/review-docs-index.md").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    gate_report = post_rc_decision_gate.build_report(repo_root)
    template_report = post_rc_decision_record_template_check.build_report(repo_root)

    text = ""
    if not doc_path.exists():
        failures.append("post-RC decision record examples doc is missing")
    else:
        text = doc_path.read_text(encoding="utf-8")
        normalized_text = " ".join(text.split())
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in normalized_text:
                failures.append(f"post-RC decision record examples are missing phrase: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(
                    f"post-RC decision record examples contain forbidden phrase: {phrase}"
                )

    failures.extend(f"post-RC decision gate: {failure}" for failure in gate_report["failures"])
    failures.extend(
        f"post-RC decision record template: {failure}"
        for failure in template_report["failures"]
    )

    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("post-RC decision record examples are missing from review docs")
    if doc_rel not in docs_site:
        failures.append("post-RC decision record examples are missing from docs-site inputs")
    if "post-rc-decision-record-examples-check:" not in makefile:
        failures.append("Make target is missing: post-rc-decision-record-examples-check")
    if "post-rc-decision-record-examples-check" not in release_check_body:
        failures.append("post-rc-decision-record-examples-check is missing from release-check")
    if "make post-rc-decision-record-examples-check" not in readme:
        failures.append("README is missing post-RC decision record examples command")
    if "post-RC decision record examples" not in readme:
        failures.append("README is missing post-RC decision record examples reference")
    if "Post-RC Decision Record Examples" not in review_index:
        failures.append("review docs index is missing post-RC decision record examples")

    for example_id in ["PRD-MC-DISPLAY-001", "PRD-SANDBOX-PREFLIGHT-001", "PRD-CAPABILITY-001"]:
        if text.count(example_id) < 2:
            failures.append(f"post-RC decision record example is under-referenced: {example_id}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "decision_record_examples_doc": doc_rel,
        "tool_count": 24,
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "sandbox_orchestration_allowed": False,
        "local_model_invocation_allowed": False,
        "trusted_host_promotion_allowed": False,
        "new_capability_runtime_allowed": False,
        "compliance_claims_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin post-RC decision record examples check",
        f"valid: {str(report['valid']).lower()}",
        f"decision_record_examples_doc: {report['decision_record_examples_doc']}",
        f"tool_count: {report['tool_count']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"new_capability_runtime_allowed: {str(report['new_capability_runtime_allowed']).lower()}",
        f"compliance_claims_allowed: {str(report['compliance_claims_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

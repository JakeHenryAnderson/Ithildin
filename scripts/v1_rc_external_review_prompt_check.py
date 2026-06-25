"""Validate the v1.0 RC external review prompt and packet wiring."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs, v1_rc_feature_freeze_check, v1_rc_readiness_check

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/v1.0-rc-external-review-prompt.md"

REQUIRED_PHRASES = [
    "Status: v1.0 local-preview external handoff prompt.",
    "Use this prompt with GPT 5.5 Pro / Very High or a human expert reviewer",
    "v1.0 local-preview release-candidate packet review",
    "The governed tool count is 24.",
    "The latest implemented governed tool is sandbox.artifact.write_text.",
    "No next capability is selected.",
    "Capability expansion is feature-frozen for v1.0 RC.",
    "Public/security-product positioning remains blocked.",
    "Production/security/compliance positioning remains blocked.",
    "Internal AI/subagent review is supporting evidence only",
    "feature-freeze boundary is clear",
    "external/source-review pending rows",
    "accepted-deferred risks",
    "Blockers before v1.0 local-preview RC labeling.",
    "Do-not-add-yet list.",
    "distinguish packet/evidence confidence from implementation confidence",
    "Attachments To Send",
    "var/review-packets/v1.0/rc/",
    "05_V1_RC_FEATURE_FREEZE.md",
    "11_V1_RC_EXTERNAL_REVIEW_PROMPT.md",
    "12_V1_RC_FINAL_HANDOFF.md",
    "13_V1_RC_POST_REVIEW_TRIAGE.md",
    "14_V1_RC_ARTIFACTS.md",
    "15_V1_RC_COMMANDS.md",
    "v1-rc-artifact-hashes.json",
]

FORBIDDEN_PHRASES = [
    "production-ready",
    "compliance-grade audit",
    "tamper-proof audit",
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
    doc_rel = DOC.relative_to(ROOT).as_posix()
    doc_path = repo_root / doc_rel
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    readiness = v1_rc_readiness_check.build_report(repo_root)
    feature_freeze = v1_rc_feature_freeze_check.build_report(repo_root)
    for name, report in {
        "readiness": readiness,
        "feature_freeze": feature_freeze,
    }.items():
        failures.extend(f"{name}: {failure}" for failure in report.get("failures", []))

    text = ""
    if not doc_path.exists():
        failures.append("v1.0 RC external review prompt is missing")
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"v1.0 RC external review prompt is missing phrase: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase in lowered:
                failures.append(
                    f"v1.0 RC external review prompt contains forbidden phrase: {phrase}"
                )

    if readiness.get("tool_count") != 24:
        failures.append("external review prompt requires tool count 24")
    if readiness.get("latest_implemented_tool") != "sandbox.artifact.write_text":
        failures.append(
            "external review prompt requires sandbox.artifact.write_text as latest tool"
        )
    if readiness.get("selected_capability") != "not selected":
        failures.append("external review prompt requires no selected next capability")
    if readiness.get("capability_expansion_allowed") is not False:
        failures.append("external review prompt requires capability expansion blocked")
    if readiness.get("public_security_product_positioning_allowed") is not False:
        failures.append(
            "external review prompt requires public/security-product positioning blocked"
        )
    if feature_freeze.get("valid") is not True:
        failures.append("external review prompt requires valid feature-freeze gate")

    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("v1.0 RC external review prompt is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("v1.0 RC external review prompt is missing from docs-site inputs")
    if "v1-rc-external-review-prompt-check:" not in makefile:
        failures.append("Make target is missing: v1-rc-external-review-prompt-check")
    if "v1-rc-external-review-prompt-check" not in release_check_body:
        failures.append("v1-rc-external-review-prompt-check is missing from release-check")
    if doc_rel not in (repo_root / "scripts/v1_rc_packet.py").read_text(encoding="utf-8"):
        failures.append("v1.0 RC packet is missing the external review prompt")
    if "make v1-rc-external-review-prompt-check" not in readme:
        failures.append("README is missing v1.0 RC external review prompt command reference")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "prompt_doc": doc_rel,
        "tool_count": readiness.get("tool_count"),
        "latest_implemented_tool": readiness.get("latest_implemented_tool"),
        "selected_capability": readiness.get("selected_capability"),
        "capability_expansion_allowed": False,
        "public_security_product_positioning_allowed": False,
        "runtime_changes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v1.0 RC external review prompt check",
        f"valid: {str(report['valid']).lower()}",
        f"prompt_doc: {report['prompt_doc']}",
        f"tool_count: {report['tool_count']}",
        f"latest_implemented_tool: {report['latest_implemented_tool']}",
        f"selected_capability: {report['selected_capability']}",
        "capability_expansion_allowed: false",
        "public_security_product_positioning_allowed: false",
        "runtime_changes_allowed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

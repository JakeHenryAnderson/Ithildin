"""Validate the active enterprise review handoff docs stay in sync."""

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
DOC_REL = "docs/codex/enterprise-handoff-consistency.md"
DOC_TITLE = "Enterprise Handoff Consistency"
CURRENT_SEND_SET = ["ERG-003", "ERG-002"]
DUAL_INBOX_ROOT = "var/review-runs/enterprise-dual-response-inbox"
RAW_RESPONSE_PATHS = [
    f"{DUAL_INBOX_ROOT}/RAW_RESPONSE_ERG-003.md",
    f"{DUAL_INBOX_ROOT}/RAW_RESPONSE_ERG-002.md",
]
CURRENT_FLOW_COMMANDS = [
    "make enterprise-review-send-receipt-template",
    "make enterprise-dual-response-inbox",
    "make enterprise-response-waiting-room",
    "make enterprise-response-paste-preflight",
]

CURRENT_SEND_DOC_REQUIREMENTS: dict[str, list[str]] = {
    "docs/codex/enterprise-review-send-checklist.md": [
        *RAW_RESPONSE_PATHS,
        *CURRENT_FLOW_COMMANDS,
    ],
    "docs/codex/enterprise-review-send-quickstart.md": [
        DUAL_INBOX_ROOT,
        *RAW_RESPONSE_PATHS,
        *CURRENT_FLOW_COMMANDS,
    ],
    "docs/codex/enterprise-review-submission-prompt.md": [
        DUAL_INBOX_ROOT,
        "ENTERPRISE_DUAL_RESPONSE_CHEATSHEET.md",
        "make enterprise-response-paste-preflight",
    ],
    "docs/codex/enterprise-review-send-receipt-template.md": [
        *RAW_RESPONSE_PATHS,
        "make enterprise-dual-response-inbox",
    ],
    "docs/codex/enterprise-review-handoff-drill.md": [
        DUAL_INBOX_ROOT,
        *RAW_RESPONSE_PATHS,
        "make enterprise-response-paste-preflight",
    ],
    "docs/codex/enterprise-current-checkpoint.md": [
        DUAL_INBOX_ROOT,
        *CURRENT_FLOW_COMMANDS,
    ],
    "docs/codex/enterprise-north-star-roadmap.md": [
        DUAL_INBOX_ROOT,
        *CURRENT_FLOW_COMMANDS,
    ],
    "docs/codex/enterprise-dependency-ladder.md": [
        DUAL_INBOX_ROOT,
        *CURRENT_FLOW_COMMANDS,
    ],
    "docs/codex/enterprise-transition-map.md": [
        DUAL_INBOX_ROOT,
        "make enterprise-response-paste-preflight",
    ],
    "docs/codex/enterprise-operator-next-action.md": [
        *CURRENT_FLOW_COMMANDS,
    ],
}

FORBIDDEN_CURRENT_SEND_PHRASES = [
    "var/review-packets/v3/enterprise-dual-response-inbox",
    "var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-003.md",
    "var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-002.md",
]

BOUNDARY_FLAGS = {
    "records_external_review": False,
    "normalizes_responses": False,
    "writes_response_files": False,
    "closes_erg_003": False,
    "closes_erg_002": False,
    "runtime_changes_allowed": False,
    "mission_control_runtime_allowed": False,
    "live_vm_inspection_allowed": False,
    "sandbox_orchestration_allowed": False,
    "trusted_host_promotion_allowed": False,
    "siem_adapter_allowed": False,
    "compliance_automation_allowed": False,
    "public_security_product_positioning_allowed": False,
    "new_power_classes_allowed": False,
}


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

    docs_checked: list[str] = []
    for rel_path, required_phrases in CURRENT_SEND_DOC_REQUIREMENTS.items():
        text = _read(repo_root / rel_path)
        docs_checked.append(rel_path)
        if not text:
            failures.append(f"current handoff doc is missing or empty: {rel_path}")
            continue
        for phrase in required_phrases:
            if phrase not in text:
                failures.append(f"{rel_path} is missing current-flow phrase: {phrase}")
        for phrase in FORBIDDEN_CURRENT_SEND_PHRASES:
            if phrase in text:
                failures.append(f"{rel_path} contains stale handoff phrase: {phrase}")

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    consistency_doc = _read(repo_root / DOC_REL)
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition(
        "\n\n"
    )[0]

    wiring_checks = {
        "Make target": ("enterprise-handoff-consistency-check:", makefile),
        "Release check": (
            "enterprise-handoff-consistency-check",
            release_check_body + "\n" + makefile,
        ),
        "Review candidate": (
            "$(MAKE) enterprise-handoff-consistency-check",
            review_candidate_body,
        ),
        "README command": ("make enterprise-handoff-consistency-check", readme),
        "README doc": (DOC_REL, readme),
        "Docs site": (DOC_REL, docs_site),
        "Review docs": (DOC_REL, "\n".join(review_docs.REVIEW_DOCS)),
        "Review index": (DOC_TITLE, review_index),
        "Release guardrails": ("enterprise-handoff-consistency-check", release_guardrails),
    }
    for label, (needle, haystack) in wiring_checks.items():
        if needle not in haystack:
            failures.append(f"{label} is missing {needle}")

    for phrase in [
        "Status: checked read-only enterprise handoff consistency gate.",
        "make enterprise-handoff-consistency-check",
        DUAL_INBOX_ROOT,
        *CURRENT_FLOW_COMMANDS,
        *RAW_RESPONSE_PATHS,
        "does not record external review",
        "does not normalize responses",
        "does not close `ERG-003` or `ERG-002`",
    ]:
        if phrase not in consistency_doc:
            failures.append(f"enterprise handoff consistency doc is missing phrase: {phrase}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "docs_checked": docs_checked,
        "tool_count": 24,
        "selected_capability": "not selected",
        "current_send_set": CURRENT_SEND_SET,
        "dual_response_inbox_root": DUAL_INBOX_ROOT,
        "raw_response_paths": RAW_RESPONSE_PATHS,
        "required_current_flow_commands": CURRENT_FLOW_COMMANDS,
        **BOUNDARY_FLAGS,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise handoff consistency",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report['tool_count']}",
        f"selected_capability: {report['selected_capability']}",
        "current_send_set: " + ", ".join(report["current_send_set"]),
        f"dual_response_inbox_root: {report['dual_response_inbox_root']}",
        "docs_checked:",
        *[f"- {path}" for path in report["docs_checked"]],
        "required_current_flow_commands:",
        *[f"- {command}" for command in report["required_current_flow_commands"]],
    ]
    for key in BOUNDARY_FLAGS:
        lines.append(f"{key}: {str(report[key]).lower()}")
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())

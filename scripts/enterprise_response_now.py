"""Print the current enterprise response-intake instructions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import enterprise_response_waiting_room, review_docs  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-response-now.md"
DOC_TITLE = "Enterprise Response Now"

LANE_COMMANDS = {
    "ERG-003": {
        "name": "static sandbox/VM preflight",
        "normalizer": (
            "uv run python scripts/external_response_normalize.py "
            "--area sandbox-vm-static-preflight "
            "--raw-response var/review-runs/enterprise-dual-response-inbox/"
            "RAW_RESPONSE_ERG-003.md"
        ),
        "dry_run": "make sandbox-vm-static-preflight-response-dry-run",
        "closure_gate": "make sandbox-vm-static-preflight-disposition-closure-check",
    },
    "ERG-002": {
        "name": "Mission Control display/import planning",
        "normalizer": (
            "uv run python scripts/external_response_normalize.py "
            "--area mission-control-display "
            "--raw-response var/review-runs/enterprise-dual-response-inbox/"
            "RAW_RESPONSE_ERG-002.md"
        ),
        "dry_run": "make mission-control-display-response-dry-run",
        "closure_gate": "make mission-control-display-disposition-closure-check",
    },
}

BOUNDARY_FLAGS = {
    "normalizes_responses": False,
    "writes_response_files": False,
    "records_external_review": False,
    "mutates_findings": False,
    "closes_erg_003": False,
    "closes_erg_002": False,
    "runtime_changes_allowed": False,
    "mission_control_runtime_allowed": False,
    "live_vm_inspection_allowed": False,
    "local_model_invocation_allowed": False,
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
    waiting_room = enterprise_response_waiting_room.build_report(repo_root)
    failures = [f"waiting room: {failure}" for failure in waiting_room.get("failures", [])]
    response_rows = [_response_row(row) for row in waiting_room.get("rows", [])]
    candidate_rows = [row for row in response_rows if row["state"] == "candidate_response"]
    invalid_rows = [
        row for row in response_rows if row["state"] in {"invalid", "too_large", "missing"}
    ]

    if invalid_rows:
        next_action = "fix_response_inbox_state"
    elif candidate_rows:
        next_action = "run_lane_paste_preflight_then_normalizer_dry_run_and_closure_gate"
    else:
        next_action = "wait_for_external_response"

    _validate_wiring(repo_root, failures)

    return {
        "schema_version": "1",
        "valid": not failures and not invalid_rows,
        "failures": failures,
        "summary_doc": DOC_REL,
        "tool_count": 24,
        "recommended_gaps": ["ERG-003", "ERG-002"],
        "candidate_response_count": len(candidate_rows),
        "invalid_response_count": len(invalid_rows),
        "placeholder_count": waiting_room.get("placeholder_count", 0),
        "next_action": next_action,
        "lanes": response_rows,
        **BOUNDARY_FLAGS,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise response now",
        f"valid: {str(report['valid']).lower()}",
        f"summary_doc: {report['summary_doc']}",
        f"tool_count: {report['tool_count']}",
        "recommended_gaps: " + ", ".join(report["recommended_gaps"]),
        f"candidate_response_count: {report['candidate_response_count']}",
        f"invalid_response_count: {report['invalid_response_count']}",
        f"placeholder_count: {report['placeholder_count']}",
        f"next_action: {report['next_action']}",
        "lanes:",
    ]
    for lane in report["lanes"]:
        lines.extend(
            [
                f"- {lane['gap']}: {lane['name']}",
                f"  state: {lane['state']}",
                f"  raw_response_path: {lane['raw_response_path']}",
                f"  safe_reason: {lane['safe_reason']}",
                f"  paste_preflight: {lane['paste_preflight']}",
                f"  normalizer: {lane['normalizer']}",
                f"  dry_run: {lane['dry_run']}",
                f"  closure_gate: {lane['closure_gate']}",
            ]
        )
    lines.append("boundaries:")
    for key in BOUNDARY_FLAGS:
        lines.append(f"- {key}: {str(report[key]).lower()}")
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _response_row(waiting_row: dict[str, Any]) -> dict[str, Any]:
    gap = str(waiting_row.get("gap", ""))
    commands = LANE_COMMANDS.get(gap, {})
    return {
        "gap": gap,
        "name": commands.get("name", waiting_row.get("area", "unknown")),
        "state": waiting_row.get("state"),
        "raw_response_path": waiting_row.get("raw_response_path"),
        "finding_namespace": waiting_row.get("finding_namespace"),
        "safe_reason": waiting_row.get("safe_reason"),
        "paste_preflight": waiting_row.get("recommended_next"),
        "normalizer": commands.get("normalizer"),
        "dry_run": commands.get("dry_run"),
        "closure_gate": commands.get("closure_gate"),
        "content_excerpt_included": False,
        "normalizes_response": False,
        "writes_response_files": False,
        "records_external_review": False,
        "closes_external_review": False,
    }


def _validate_wiring(repo_root: Path, failures: list[str]) -> None:
    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    waiting_room_doc = _read(repo_root / "docs/codex/enterprise-response-waiting-room.md")
    paste_preflight_doc = _read(repo_root / "docs/codex/enterprise-response-paste-preflight.md")
    quickstart_doc = _read(repo_root / "docs/codex/enterprise-response-intake-quickstart.md")
    current_checkpoint = _read(repo_root / "docs/codex/enterprise-current-checkpoint.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    required_doc_phrases = [
        "Status: read-only current response-intake command summary.",
        "Current governed tool count: `24`.",
        "make enterprise-response-now",
        "make enterprise-response-waiting-room",
        "make enterprise-response-paste-preflight",
        "does not normalize responses",
        "does not write response files",
        "does not record external review",
        "does not close either lane",
        "does not approve runtime behavior",
    ]
    for phrase in required_doc_phrases:
        if phrase not in doc:
            failures.append(f"response-now doc is missing phrase: {phrase}")

    wiring_checks = {
        "Make target": "enterprise-response-now:" in makefile,
        "release-check": "enterprise-response-now" in release_check_body
        or "release-check: enterprise-response-now" in makefile,
        "review-candidate": "$(MAKE) enterprise-response-now" in review_candidate_body,
        "README command": "make enterprise-response-now" in readme,
        "README doc link": DOC_REL in readme,
        "docs site": DOC_REL in docs_site,
        "review docs": DOC_REL in review_docs.REVIEW_DOCS,
        "review index": DOC_TITLE in review_index,
        "release guardrails": "enterprise-response-now" in release_guardrails,
        "waiting room doc": "make enterprise-response-now" in waiting_room_doc,
        "paste preflight doc": "make enterprise-response-now" in paste_preflight_doc,
        "quickstart doc": "make enterprise-response-now" in quickstart_doc,
        "current checkpoint doc": "make enterprise-response-now" in current_checkpoint,
    }
    for label, ok in wiring_checks.items():
        if not ok:
            failures.append(f"response-now wiring missing: {label}")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


if __name__ == "__main__":
    raise SystemExit(main())

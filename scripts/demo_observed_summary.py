"""Generate a concise secret-free observed-demo summary."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

DEFAULT_RESULT = Path("var/review-packets/v3/operator-workbench/DEMO_FLOW_RESULT.md")
DEFAULT_RUN_EXPORT = Path("var/review-packets/v3/operator-workbench/RUN_EVIDENCE_EXPORT.json")
DEFAULT_OUTPUT = Path("var/review-packets/v3/operator-workbench/DEMO_OBSERVED_SUMMARY.md")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--run-export", type=Path, default=DEFAULT_RUN_EXPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = build_summary(result=args.result, run_export=args.run_export, output=args.output)
    print("Ithildin demo observed summary")
    print(f"status: {report['status']}")
    print(f"result_present: {str(report['result_present']).lower()}")
    print(f"run_export_present: {str(report['run_export_present']).lower()}")
    print(f"output: {args.output}")
    return 0


def build_summary(*, result: Path, run_export: Path, output: Path) -> dict[str, Any]:
    report = build_report(result=result, run_export=run_export)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_summary(report), encoding="utf-8")
    return report


def build_report(*, result: Path, run_export: Path) -> dict[str, Any]:
    fields = _result_fields(result)
    export = _run_export_summary(run_export)
    observed = bool(fields and fields.get("patch_apply_status") == "completed")
    return {
        "status": "observed" if observed else "not_observed",
        "result_present": result.exists(),
        "run_export_present": run_export.exists(),
        "proposal_id": fields.get("proposal_id"),
        "approval_id": fields.get("approval_id"),
        "candidate_run_ids": fields.get("candidate_run_ids"),
        "patch_apply_status": fields.get("patch_apply_status"),
        "audit_verification_valid": fields.get("audit_verification_valid"),
        "audit_event_count": fields.get("audit_event_count"),
        "audit_head_hash": fields.get("audit_head_hash"),
        "audit_export_event_count": fields.get("audit_export_event_count"),
        "audit_export_head_hash": fields.get("audit_export_head_hash"),
        "run_export_id": export.get("export_id"),
        "run_export_schema_version": export.get("schema_version"),
        "run_export_timeline_count": export.get("timeline_count"),
        "run_export_warning_count": export.get("warning_count"),
    }


def render_summary(report: dict[str, Any]) -> str:
    if report["status"] != "observed":
        return """# Demo Observed Summary

Status: `not_observed`

The mediated local demo has not been captured in `DEMO_FLOW_RESULT.md` yet. Run the intentional
operator flow, then regenerate the workbench packet:

1. `make demo-seed`
2. start the local API/UI stack
3. `make demo-flow`
4. export run evidence from the review console or API
5. `make demo-workbench`

This summary is read-only evidence packaging. It does not start services, call governed tools,
approve actions, repair state, add run controls, or manage sandboxes.
"""
    lines = [
        "# Demo Observed Summary",
        "",
        "Status: `observed`",
        "",
        "This summary is generated from the secret-free demo result and run evidence export.",
        "It is meant to be the quickest operator/reviewer entry point after a completed demo.",
        "",
        "## Observed Flow",
        "",
        f"- proposal_id: `{_value(report.get('proposal_id'))}`",
        f"- approval_id: `{_value(report.get('approval_id'))}`",
        f"- candidate_run_ids: `{_value(report.get('candidate_run_ids'))}`",
        f"- patch_apply_status: `{_value(report.get('patch_apply_status'))}`",
        f"- audit_verification_valid: `{_value(report.get('audit_verification_valid'))}`",
        f"- audit_event_count: `{_value(report.get('audit_event_count'))}`",
        f"- audit_head_hash: `{_value(report.get('audit_head_hash'))}`",
        f"- audit_export_event_count: `{_value(report.get('audit_export_event_count'))}`",
        f"- audit_export_head_hash: `{_value(report.get('audit_export_head_hash'))}`",
        "",
        "## Run Evidence Export",
        "",
        f"- present: `{str(report.get('run_export_present')).lower()}`",
        f"- export_id: `{_value(report.get('run_export_id'))}`",
        f"- schema_version: `{_value(report.get('run_export_schema_version'))}`",
        f"- timeline_count: `{_value(report.get('run_export_timeline_count'))}`",
        f"- warning_count: `{_value(report.get('run_export_warning_count'))}`",
        "",
        "## Reading Order",
        "",
        "1. `DEMO_OBSERVED_SUMMARY.md` for this compact result.",
        "2. `DEMO_FLOW_RESULT.md` for proposal, approval, audit, and run pointers.",
        "3. `RUN_EVIDENCE_EXPORT.json` for the selected run's safe evidence export.",
        "4. `WORKBENCH_DEMO_INDEX.md` for the full local operator workbench packet.",
        "5. `DEMO_RESET_GUIDE.md` before repeating or recovering a demo.",
        "",
        "## Boundary",
        "",
        "This summary does not include file contents, unified diffs, response bodies, prompts,",
        "secrets, raw sensitive paths, SIEM custody, compliance automation, OS isolation,",
        "production security proof, or activity outside Ithildin-mediated actions.",
        "",
    ]
    return "\n".join(lines)


def _result_fields(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    fields: dict[str, str] = {}
    pattern = re.compile(r"^- ([a-zA-Z0-9_]+): `([^`]*)`$")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            fields[match.group(1)] = match.group(2)
    return fields


def _run_export_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    summary = payload.get("summary") if isinstance(payload, dict) else {}
    timeline = payload.get("timeline") if isinstance(payload, dict) else []
    warnings = payload.get("warnings") if isinstance(payload, dict) else []
    return {
        "export_id": payload.get("export_id") if isinstance(payload, dict) else None,
        "schema_version": payload.get("schema_version") if isinstance(payload, dict) else None,
        "timeline_count": len(timeline) if isinstance(timeline, list) else None,
        "warning_count": (
            summary.get("warning_count")
            if isinstance(summary, dict) and summary.get("warning_count") is not None
            else len(warnings)
            if isinstance(warnings, list)
            else None
        ),
    }


def _value(value: Any) -> str:
    return str(value) if value not in {None, ""} else "unavailable"


if __name__ == "__main__":
    raise SystemExit(main())

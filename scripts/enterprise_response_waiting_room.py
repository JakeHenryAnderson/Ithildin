"""Summarize raw ERG response placeholders before normalization."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-response-waiting-room.md"
DOC_TITLE = "Enterprise Response Waiting Room"
MAX_RESPONSE_BYTES = 200_000

BOUNDARY_FLAGS = {
    "normalizes_responses": False,
    "writes_response_files": False,
    "records_external_review": False,
    "mutates_findings": False,
    "closes_erg_003": False,
    "closes_erg_002": False,
    "closes_erg_004": False,
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


@dataclass(frozen=True)
class LaneSpec:
    gap: str
    area: str
    raw_response_path: str
    finding_namespace: str
    paste_preflight_command: str


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
    rows = [_row(repo_root, spec) for spec in _lane_specs()]

    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    dual_inbox_doc = _read(repo_root / "docs/codex/enterprise-dual-response-inbox.md")
    paste_preflight_doc = _read(
        repo_root / "docs/codex/enterprise-response-paste-preflight.md"
    )
    quickstart_doc = _read(repo_root / "docs/codex/enterprise-response-intake-quickstart.md")
    current_checkpoint = _read(repo_root / "docs/codex/enterprise-current-checkpoint.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition(
        "\n\n"
    )[0]

    for phrase in [
        "Status: read-only raw-response waiting-room summary for active `ERG-004`.",
        "Current governed tool count: `24`.",
        "make enterprise-response-waiting-room",
        "RAW_RESPONSE_ERG-004-DESCRIPTOR-ONLY.md",
        "historical `ERG-003`/`ERG-002` fallback",
        "placeholder",
        "candidate_response",
        "make enterprise-response-paste-preflight",
        "does not normalize responses",
        "does not write response files",
        "does not record external review",
        "does not close any lane",
    ]:
        if phrase not in doc:
            failures.append(f"waiting-room doc is missing phrase: {phrase}")

    wiring_checks = {
        "Make target": "enterprise-response-waiting-room:" in makefile,
        "release-check": "enterprise-response-waiting-room" in release_check_body
        or "release-check: enterprise-response-waiting-room" in makefile,
        "review-candidate": "$(MAKE) enterprise-response-waiting-room"
        in review_candidate_body,
        "README command": "make enterprise-response-waiting-room" in readme,
        "README doc link": DOC_REL in readme,
        "docs site": DOC_REL in docs_site,
        "review docs": DOC_REL in review_docs.REVIEW_DOCS,
        "review index": DOC_TITLE in review_index,
        "release guardrails": "enterprise-response-waiting-room" in release_guardrails,
        "dual inbox doc": "make enterprise-response-waiting-room" in dual_inbox_doc,
        "paste preflight doc": "make enterprise-response-waiting-room"
        in paste_preflight_doc,
        "quickstart doc": "make enterprise-response-waiting-room" in quickstart_doc,
        "current checkpoint doc": "make enterprise-response-waiting-room"
        in current_checkpoint,
    }
    for label, ok in wiring_checks.items():
        if not ok:
            failures.append(f"waiting-room wiring missing: {label}")

    invalid_count = sum(1 for row in rows if row["state"] in {"invalid", "too_large"})
    candidate_count = sum(1 for row in rows if row["state"] == "candidate_response")
    placeholder_count = sum(1 for row in rows if row["state"] == "placeholder")
    missing_count = sum(1 for row in rows if row["state"] == "missing")

    if invalid_count:
        next_action = "fix_invalid_raw_response_files"
    elif candidate_count:
        next_action = "run_enterprise_response_paste_preflight"
    elif placeholder_count or missing_count:
        next_action = "wait_for_external_response"
    else:
        next_action = "inspect_response_waiting_room"

    return {
        "schema_version": "1",
        "valid": not failures and invalid_count == 0,
        "failures": failures,
        "summary_doc": DOC_REL,
        "tool_count": 24,
        "recommended_gaps": ["ERG-004"],
        "historical_fallback_gaps": ["ERG-003", "ERG-002"],
        "candidate_response_count": candidate_count,
        "placeholder_count": placeholder_count,
        "missing_count": missing_count,
        "invalid_count": invalid_count,
        "next_action": next_action,
        "rows": rows,
        **BOUNDARY_FLAGS,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise response waiting room",
        f"valid: {str(report['valid']).lower()}",
        f"summary_doc: {report['summary_doc']}",
        f"tool_count: {report['tool_count']}",
        "recommended_gaps: " + ", ".join(report["recommended_gaps"]),
        "historical_fallback_gaps: " + ", ".join(report["historical_fallback_gaps"]),
        f"candidate_response_count: {report['candidate_response_count']}",
        f"placeholder_count: {report['placeholder_count']}",
        f"missing_count: {report['missing_count']}",
        f"invalid_count: {report['invalid_count']}",
        f"next_action: {report['next_action']}",
    ]
    for key in BOUNDARY_FLAGS:
        lines.append(f"{key}: {str(report[key]).lower()}")
    lines.append("rows:")
    for row in report["rows"]:
        lines.append(
            "- {gap}: state={state} raw_response_path={path} size_bytes={size} "
            "recommended_next={next_step}".format(
                gap=row["gap"],
                state=row["state"],
                path=row["raw_response_path"],
                size=row["size_bytes"],
                next_step=row["recommended_next"],
            )
        )
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _row(repo_root: Path, spec: LaneSpec) -> dict[str, Any]:
    path = repo_root / spec.raw_response_path
    state = "missing"
    size: int | None = None
    recommended_next = "make enterprise-dual-response-inbox"
    safe_reason = "raw response placeholder is missing"

    if path.exists():
        if not path.is_file():
            state = "invalid"
            safe_reason = "raw response path is not a regular file"
            recommended_next = "replace raw response path with the generated placeholder file"
        else:
            size = path.stat().st_size
            if size > MAX_RESPONSE_BYTES:
                state = "too_large"
                safe_reason = f"raw response exceeds {MAX_RESPONSE_BYTES} bytes"
                recommended_next = "replace raw response with a size-bounded reviewer response"
            else:
                try:
                    text = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    state = "invalid"
                    safe_reason = "raw response is not valid UTF-8"
                    recommended_next = "replace raw response with UTF-8 reviewer text"
                else:
                    if _looks_like_placeholder(text):
                        state = "placeholder"
                        safe_reason = "raw response still appears to be the generated placeholder"
                        recommended_next = "wait_for_external_response"
                    elif text.strip():
                        state = "candidate_response"
                        safe_reason = (
                            "raw response appears populated; run paste preflight before "
                            "normalization"
                        )
                        recommended_next = spec.paste_preflight_command
                    else:
                        state = "missing"
                        safe_reason = "raw response file is empty"
                        recommended_next = "wait_for_external_response"

    return {
        "gap": spec.gap,
        "area": spec.area,
        "raw_response_path": spec.raw_response_path,
        "finding_namespace": spec.finding_namespace,
        "state": state,
        "size_bytes": size,
        "safe_reason": safe_reason,
        "recommended_next": recommended_next,
        "content_excerpt_included": False,
        "normalizes_response": False,
        "writes_response_files": False,
        "records_external_review": False,
        "closes_external_review": False,
    }


def _looks_like_placeholder(text: str) -> bool:
    lower = text.lower()
    markers = [
        "raw external review response placeholder",
        "paste the unmodified reviewer response",
        "expected finding namespace",
        "finding table shape",
        "leave this placeholder text intact",
    ]
    return any(marker in lower for marker in markers)


def _lane_specs() -> tuple[LaneSpec, ...]:
    return (
        LaneSpec(
            gap="ERG-004",
            area="sandbox-vm-live-poc-runtime-descriptor-only",
            raw_response_path=(
                "var/review-runs/"
                "sandbox-vm-live-poc-runtime-descriptor-only-response-inbox/"
                "RAW_RESPONSE_ERG-004-DESCRIPTOR-ONLY.md"
            ),
            finding_namespace="EXT-LIVE-DESC-###",
            paste_preflight_command=(
                "uv run python scripts/enterprise_response_paste_preflight.py "
                "--lane ERG-004 --raw-response "
                "var/review-runs/"
                "sandbox-vm-live-poc-runtime-descriptor-only-response-inbox/"
                "RAW_RESPONSE_ERG-004-DESCRIPTOR-ONLY.md"
            ),
        ),
    )


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


if __name__ == "__main__":
    raise SystemExit(main())

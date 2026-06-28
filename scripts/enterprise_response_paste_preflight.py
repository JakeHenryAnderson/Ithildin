"""Preflight pasted ERG-003/ERG-002 reviewer responses without normalizing them."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    enterprise_dual_response_readiness,
    enterprise_response_command_matrix,
    enterprise_response_intake_quickstart,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-response-paste-preflight.md"
DOC_TITLE = "Enterprise Response Paste Preflight"
MAX_RESPONSE_BYTES = 200_000
SUPPORTED_LANES = {"ERG-003", "ERG-002"}

BOUNDARY_FLAGS = {
    "normalizes_responses": False,
    "writes_response_files": False,
    "committed_findings_mutated": False,
    "external_review_recorded": False,
    "closes_enterprise_lanes": False,
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
    raw_response_path: str
    finding_namespace: str
    normalization_area: str
    normalizer_command: str
    dry_run_command: str
    closure_gate: str
    allowed_next_state: str


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--lane", choices=sorted(SUPPORTED_LANES))
    parser.add_argument("--raw-response", type=Path)
    args = parser.parse_args()

    if (args.lane is None) != (args.raw_response is None):
        parser.error("--lane and --raw-response must be supplied together")

    report = build_report(ROOT, lane=args.lane, raw_response=args.raw_response)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(
    repo_root: Path, *, lane: str | None = None, raw_response: Path | None = None
) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []

    readiness = enterprise_dual_response_readiness.build_report(repo_root)
    quickstart = enterprise_response_intake_quickstart.build_report(repo_root)
    command_matrix = enterprise_response_command_matrix.build_report(repo_root)

    for label, report in [
        ("enterprise-dual-response-readiness", readiness),
        ("enterprise-response-intake-quickstart", quickstart),
        ("enterprise-response-command-matrix", command_matrix),
    ]:
        if report.get("valid") is not True:
            failures.append(f"{label} is not valid")

    lane_specs = _lane_specs(command_matrix)
    if sorted(lane_specs) != sorted(SUPPORTED_LANES):
        failures.append("paste preflight expected only ERG-003 and ERG-002 lane specs")

    raw_report: dict[str, Any] | None = None
    if lane and raw_response:
        spec = lane_specs.get(lane)
        if spec is None:
            failures.append(f"unsupported lane for paste preflight: {lane}")
        else:
            raw_report = preflight_raw_response(repo_root, spec, raw_response)
            if raw_report["valid"] is not True:
                failures.extend(f"raw response: {failure}" for failure in raw_report["failures"])
            warnings.extend(raw_report["warnings"])
    else:
        warnings.append(
            "no raw response supplied; validating deterministic docs and command wiring only"
        )

    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    quickstart_doc = _read(repo_root / enterprise_response_intake_quickstart.DOC_REL)
    current_checkpoint = _read(repo_root / "docs/codex/enterprise-current-checkpoint.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    required_doc_phrases = [
        "Status: deterministic preflight for pasted `ERG-003` and `ERG-002` reviewer responses.",
        "Current governed tool count: `24`.",
        "make enterprise-response-paste-preflight",
        "--lane ERG-003",
        "--lane ERG-002",
        "--raw-response var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-003.md",
        "--raw-response var/review-runs/enterprise-response-inbox/RAW_RESPONSE_ERG-002.md",
        "does not normalize responses",
        "does not write response files",
        "does not record external review",
        "does not close either lane",
        "does not approve runtime behavior",
        "Expected finding namespace",
        "explicit no-findings statement",
        "make sandbox-vm-static-preflight-response-dry-run",
        "make mission-control-display-response-dry-run",
    ]
    for phrase in required_doc_phrases:
        if phrase not in doc:
            failures.append(f"paste preflight doc is missing phrase: {phrase}")

    wiring_checks = {
        "Make target": "enterprise-response-paste-preflight:" in makefile,
        "release-check": "enterprise-response-paste-preflight" in release_check_body
        or "release-check: enterprise-response-paste-preflight" in makefile,
        "review-candidate": "$(MAKE) enterprise-response-paste-preflight"
        in review_candidate_body,
        "README command": "make enterprise-response-paste-preflight" in readme,
        "README doc link": DOC_REL in readme,
        "docs site": DOC_REL in docs_site,
        "review docs": DOC_REL in review_docs.REVIEW_DOCS,
        "review index": DOC_TITLE in review_index,
        "release guardrails fragment": "enterprise-response-paste-preflight"
        in release_guardrails,
        "quickstart": "enterprise-response-paste-preflight" in quickstart_doc,
        "current checkpoint": "enterprise-response-paste-preflight" in current_checkpoint,
    }
    for label, ok in wiring_checks.items():
        if not ok:
            failures.append(f"paste preflight wiring missing: {label}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "warnings": warnings,
        "preflight_doc": DOC_REL,
        "tool_count": 24,
        "supported_lanes": sorted(SUPPORTED_LANES),
        "lane_supplied": lane,
        "raw_response_supplied": raw_response.as_posix() if raw_response else None,
        "raw_response_preflight": raw_report,
        "ready_for_normalization": raw_report is not None and raw_report["valid"] is True,
        "deterministic_docs_only": raw_report is None,
        **BOUNDARY_FLAGS,
    }


def preflight_raw_response(repo_root: Path, spec: LaneSpec, raw_response: Path) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []
    raw_path = raw_response if raw_response.is_absolute() else repo_root / raw_response

    expected_path = repo_root / spec.raw_response_path
    if raw_path.resolve(strict=False) != expected_path.resolve(strict=False):
        failures.append(
            "raw response path does not match the generated inbox path for "
            f"{spec.gap}: {spec.raw_response_path}"
        )
    if not raw_path.exists():
        failures.append("raw response file is missing")
        return _raw_report(spec, raw_path, None, failures, warnings)
    if not raw_path.is_file():
        failures.append("raw response path is not a regular file")
        return _raw_report(spec, raw_path, None, failures, warnings)

    size = raw_path.stat().st_size
    if size == 0:
        failures.append("raw response file is empty")
    if size > MAX_RESPONSE_BYTES:
        failures.append(f"raw response file exceeds {MAX_RESPONSE_BYTES} bytes")

    try:
        text = raw_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        failures.append("raw response file is not valid UTF-8")
        return _raw_report(spec, raw_path, size, failures, warnings)

    lower_text = text.lower()
    placeholder_markers = [
        "raw external review response placeholder",
        "paste the unmodified reviewer response",
        "critical/high/medium/low/informational",
    ]
    if any(marker in lower_text for marker in placeholder_markers):
        failures.append("raw response still appears to be the generated placeholder")

    no_findings_markers = [
        "no actionable findings",
        "no implementation findings",
        "no findings",
    ]
    has_namespace = spec.finding_namespace.replace("###", "") in text
    has_no_findings = any(marker in lower_text for marker in no_findings_markers)
    if not has_namespace and not has_no_findings:
        failures.append(
            "raw response must contain the expected finding namespace prefix "
            f"{spec.finding_namespace.replace('###', '')} or an explicit no-findings statement"
        )

    if spec.normalization_area not in text and not has_no_findings:
        warnings.append(
            "raw response does not mention the expected normalization area; "
            "normalizer may reject it"
        )
    if "```" in text:
        warnings.append("raw response contains fenced code; verify no copied secrets are included")

    return _raw_report(spec, raw_path, size, failures, warnings)


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise response paste preflight",
        f"valid: {str(report['valid']).lower()}",
        f"preflight_doc: {report['preflight_doc']}",
        f"tool_count: {report['tool_count']}",
        "supported_lanes: " + ", ".join(report["supported_lanes"]),
        f"deterministic_docs_only: {str(report['deterministic_docs_only']).lower()}",
        f"ready_for_normalization: {str(report['ready_for_normalization']).lower()}",
    ]
    if report["lane_supplied"]:
        lines.append(f"lane_supplied: {report['lane_supplied']}")
        lines.append(f"raw_response_supplied: {report['raw_response_supplied']}")
    for key in BOUNDARY_FLAGS:
        lines.append(f"{key}: {str(report[key]).lower()}")
    if report["raw_response_preflight"]:
        raw = report["raw_response_preflight"]
        lines.extend(
            [
                "raw_response_preflight:",
                f"- lane: {raw['lane']}",
                f"- raw_response_path: {raw['raw_response_path']}",
                f"- byte_count: {raw.get('byte_count')}",
                f"- valid: {str(raw['valid']).lower()}",
                f"- finding_namespace: {raw['finding_namespace']}",
            ]
        )
    if report["warnings"]:
        lines.append("warnings:")
        lines.extend(f"- {warning}" for warning in report["warnings"])
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _lane_specs(command_matrix: dict[str, Any]) -> dict[str, LaneSpec]:
    specs: dict[str, LaneSpec] = {}
    for row in command_matrix.get("command_rows", []):
        if row.get("gap") in SUPPORTED_LANES:
            specs[row["gap"]] = LaneSpec(
                gap=row["gap"],
                raw_response_path=row["raw_response_path"],
                finding_namespace=row["finding_namespace"],
                normalization_area=row["normalization_area"],
                normalizer_command=row["normalizer_command"],
                dry_run_command=row["dry_run_command"],
                closure_gate=row["closure_gate"],
                allowed_next_state=row["allowed_next_state"],
            )
    return specs


def _raw_report(
    spec: LaneSpec,
    raw_path: Path,
    byte_count: int | None,
    failures: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "warnings": warnings,
        "lane": spec.gap,
        "raw_response_path": raw_path.as_posix(),
        "byte_count": byte_count,
        "finding_namespace": spec.finding_namespace,
        "normalization_area": spec.normalization_area,
        "normalizer_command": spec.normalizer_command,
        "dry_run_command": spec.dry_run_command,
        "closure_gate": spec.closure_gate,
        "allowed_next_state": spec.allowed_next_state,
        "normalizes_responses": False,
        "writes_response_files": False,
        "external_review_recorded": False,
        "closes_enterprise_lanes": False,
    }


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


if __name__ == "__main__":
    raise SystemExit(main())

"""Validate v1.0 local-preview assurance closure wiring."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    accepted_risk_register,
    capability_decision_report,
    closure_matrix_evidence_sync,
    evidence_confusion_gate,
    external_review_closure_gate,
    review_docs,
    review_findings_collect,
    reviewer_findings,
    tool_surface_invariant_gate,
)

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/v1.0-assurance-closure.md"

REQUIRED_PHRASES = [
    "Status: v1.0 local-preview assurance closure map.",
    "Assurance Questions",
    "Current Assurance Ledger",
    "Closure State",
    "Required Commands",
    "Stop Conditions",
    "Non-Goals",
    "make release-guardrails",
    "make reviewer-findings-check",
    "make review-findings-summary",
    "make closure-matrix-evidence-sync",
    "make external-review-closure-gate",
    "make accepted-risk-register-check",
    "make capability-decision-report",
    "make evidence-confusion-gate",
    "make packet-redaction-scan",
    "External/source review is not complete",
    "Accepted-deferred risks are not closed risks",
    "does not mean production approval",
]

FORBIDDEN_PHRASES = [
    "external source review is complete",
    "external review complete",
    "capability expansion allowed",
    "ready for new tool powers",
    "production-ready",
    "compliance-grade",
    "tamper-proof",
    "secure sandbox",
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

    closure_report = external_review_closure_gate.build_report(repo_root)
    matrix_report = closure_matrix_evidence_sync.build_report(repo_root)
    accepted_risk_report = accepted_risk_register.build_report(repo_root)
    tool_surface_report = tool_surface_invariant_gate.build_report(repo_root)
    capability_report = capability_decision_report.build_report(repo_root)
    evidence_report = evidence_confusion_gate.build_report(repo_root)
    finding_records = reviewer_findings.validate_findings(
        findings_dir=repo_root / "docs/codex/findings",
        repo_root=repo_root,
    )
    finding_summary = review_findings_collect.collect_findings_summary(
        repo_root / "docs/codex/findings",
        repo_root,
    )

    for name, report in [
        ("external_review_closure", closure_report),
        ("closure_matrix", matrix_report),
        ("accepted_risk", accepted_risk_report),
        ("tool_surface", tool_surface_report),
        ("capability_decision", capability_report),
        ("evidence_confusion", evidence_report),
    ]:
        failures.extend(f"{name}: {failure}" for failure in report.get("failures", []))
        failures.extend(f"{name}: {failure}" for failure in report.get("hard_failures", []))

    if finding_summary["open_critical_high"] != 0:
        failures.append("review finding summary has open critical/high findings")
    if accepted_risk_report["undispositioned_external_review_ids"]:
        failures.append("accepted-risk register has undispositioned external-review risks")
    if closure_report["external_closure_complete"]:
        failures.append("assurance map expected external closure to remain incomplete")
    if not closure_report["pending_external_review_rows"]:
        failures.append("assurance map expected pending external-review rows to remain visible")
    if capability_report.get("capability_expansion_approved") is True:
        failures.append("capability expansion must remain blocked for v1.0 assurance closure")

    if not doc_path.exists():
        failures.append("v1.0 assurance closure doc is missing")
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"v1.0 assurance closure doc is missing phrase: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase in lowered:
                failures.append(f"v1.0 assurance closure doc contains forbidden phrase: {phrase}")

    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("v1.0 assurance closure doc is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("v1.0 assurance closure doc is missing from docs-site inputs")
    if "v1-assurance-closure-check:" not in makefile:
        failures.append("Make target is missing: v1-assurance-closure-check")
    if "v1-assurance-closure-check" not in release_check_body:
        failures.append("v1-assurance-closure-check is missing from release-check")
    if "v1.0 assurance closure" not in readme:
        failures.append("README is missing v1.0 assurance closure reference")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "closure_doc": doc_rel,
        "tool_count": tool_surface_report.get("tool_count"),
        "finding_count": len(finding_records),
        "open_critical_high_findings": finding_summary["open_critical_high"],
        "closure_matrix_rows": matrix_report["matrix_v3_row_count"],
        "pending_external_review_rows": len(closure_report["pending_external_review_rows"]),
        "externally_closed_rows": len(closure_report["externally_closed_rows"]),
        "accepted_risk_count": accepted_risk_report["risk_count"],
        "accepted_deferred_count": len(accepted_risk_report["accepted_deferred_ids"]),
        "external_closure_complete": closure_report["external_closure_complete"],
        "capability_expansion_allowed": False,
        "public_security_product_positioning_allowed": False,
        "runtime_changes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v1.0 assurance closure check",
        f"valid: {str(report['valid']).lower()}",
        f"closure_doc: {report['closure_doc']}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        f"finding_count: {report['finding_count']}",
        f"open_critical_high_findings: {report['open_critical_high_findings']}",
        f"closure_matrix_rows: {report['closure_matrix_rows']}",
        f"pending_external_review_rows: {report['pending_external_review_rows']}",
        f"externally_closed_rows: {report['externally_closed_rows']}",
        f"accepted_risk_count: {report['accepted_risk_count']}",
        f"accepted_deferred_count: {report['accepted_deferred_count']}",
        f"external_closure_complete: {str(report['external_closure_complete']).lower()}",
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

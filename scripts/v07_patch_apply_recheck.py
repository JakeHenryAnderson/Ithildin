"""Validate v0.7 patch-apply external recheck preparation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import reviewer_findings

ROOT = Path(__file__).resolve().parents[1]
RECHECK_DOC = "docs/codex/v0.7-patch-apply-recheck-request.md"
REQUIRED_FINDINGS = ("EXT-PA-001", "EXT-PA-002", "EXT-PA-003", "EXT-PA-004")
REQUIRED_COMMANDS = (
    "make v06-patch-apply-review-packet",
    (
        "uv run pytest tests/test_patch_proposals.py tests/test_approval_workflow.py "
        "tests/test_governed_tool_calls.py tests/test_security_regressions.py"
    ),
    "make reviewer-findings-check",
    "make review-findings-summary",
    "make external-review-closure-gate",
    "make release-check",
)


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
    findings = reviewer_findings.validate_findings(
        findings_dir=repo_root / "docs/codex/findings",
        repo_root=repo_root,
    )
    by_id = {record.finding_id: record for record in findings}

    for finding_id in REQUIRED_FINDINGS:
        record = by_id.get(finding_id)
        if record is None:
            failures.append(f"missing patch-apply external finding: {finding_id}")
            continue
        if record.fields["Disposition"] != "fixed":
            failures.append(f"{finding_id} must be fixed before recheck prep")
        if record.fields["Area"] != "patch-apply":
            failures.append(f"{finding_id} must remain in patch-apply area")
        if not record.fields["Verification notes"]:
            failures.append(f"{finding_id} is missing verification notes")

    matrix = (repo_root / "docs/codex/source-review-closure-matrix.md").read_text(
        encoding="utf-8"
    )
    if "Patch apply | v0.7 source-level recheck received" not in matrix:
        failures.append("source-review closure matrix missing patch-apply external review lineage")
    patch_row = _patch_apply_matrix_row(matrix)
    if "closed_local_preview" not in patch_row:
        failures.append("patch-apply closure matrix row must be closed_local_preview")

    recheck_path = repo_root / RECHECK_DOC
    if not recheck_path.exists():
        failures.append(f"missing patch-apply recheck request doc: {RECHECK_DOC}")
        recheck_text = ""
    else:
        recheck_text = recheck_path.read_text(encoding="utf-8")

    for finding_id in REQUIRED_FINDINGS:
        if finding_id not in recheck_text:
            failures.append(f"recheck request missing finding ID: {finding_id}")
    for command in REQUIRED_COMMANDS:
        if command not in recheck_text:
            failures.append(f"recheck request missing command: {command}")
    for phrase in (
        "External/source review closure: incomplete",
        "Capability expansion: no-go",
        "Public/security-product positioning: no-go",
        "No new governed tool powers",
    ):
        if phrase not in recheck_text:
            failures.append(f"recheck request missing boundary phrase: {phrase}")
    forbidden_lines = {
        "External/source review closure: complete",
        "Capability expansion: go",
        "Public/security-product positioning: go",
    }
    lines = {line.strip() for line in recheck_text.splitlines()}
    for line in forbidden_lines:
        if line in lines:
            failures.append(f"recheck request contains forbidden line: {line}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "required_findings": list(REQUIRED_FINDINGS),
        "fixed_findings": [
            finding_id
            for finding_id in REQUIRED_FINDINGS
            if finding_id in by_id and by_id[finding_id].fields["Disposition"] == "fixed"
        ],
        "closure_state": "closed_local_preview",
        "capability_expansion_allowed": False,
    }


def _patch_apply_matrix_row(matrix: str) -> str:
    for line in matrix.splitlines():
        if line.startswith("| Patch apply |"):
            return line
    return ""


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v0.7 patch-apply recheck prep check",
        f"valid: {str(report['valid']).lower()}",
        f"required_findings: {len(report['required_findings'])}",
        f"fixed_findings: {len(report['fixed_findings'])}",
        f"closure_state: {report['closure_state']}",
        "capability_expansion_allowed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

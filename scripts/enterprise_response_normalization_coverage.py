"""Check enterprise response lanes are supported by external response normalization."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import enterprise_response_status_board, external_response_normalize

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-response-normalization-coverage.md"
DOC_TITLE = "Enterprise Response Normalization Coverage"


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
    status_report = enterprise_response_status_board.build_report(repo_root)
    board_areas = [row["area"] for row in status_report["rows"]]
    namespace_map = external_response_normalize.AREA_NAMESPACES
    namespaces = {
        area: f"EXT-{namespace_map[area]}-###"
        for area in board_areas
        if area in namespace_map
    }
    missing_areas = [area for area in board_areas if area not in namespace_map]

    failures: list[str] = []
    if missing_areas:
        failures.append(
            "enterprise response status board areas missing from normalizer: "
            + ", ".join(missing_areas)
        )
    if namespaces.get("public-security-product-positioning") != "EXT-PUBLIC-POSITIONING-###":
        failures.append("public/security-product positioning namespace is not covered")

    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_docs = _read(repo_root / "scripts/review_docs.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    status_board_doc = _read(repo_root / "docs/codex/enterprise-response-status-board.md")
    dual_inbox_doc = _read(repo_root / "docs/codex/enterprise-dual-response-inbox.md")
    queue_doc = _read(repo_root / "docs/codex/enterprise-external-review-queue.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    for phrase in [
        "Status: coverage gate for enterprise response normalization lanes.",
        "make enterprise-response-normalization-coverage",
        "does not normalize responses",
        "does not mutate findings",
        "does not close enterprise lanes",
        "EXT-PUBLIC-POSITIONING-###",
    ]:
        if phrase not in doc:
            failures.append(f"coverage doc is missing phrase: {phrase}")
    if "enterprise-response-normalization-coverage:" not in makefile:
        failures.append("Make target is missing: enterprise-response-normalization-coverage")
    if (
        "enterprise-response-normalization-coverage" not in release_check_body
        and "release-check: enterprise-response-normalization-coverage" not in makefile
    ):
        failures.append("enterprise-response-normalization-coverage is missing from release-check")
    if "$(MAKE) enterprise-response-normalization-coverage" not in review_candidate_body:
        failures.append(
            "enterprise-response-normalization-coverage is missing from review-candidate"
        )
    if "make enterprise-response-normalization-coverage" not in readme:
        failures.append("README is missing enterprise response normalization coverage command")
    if DOC_REL not in docs_site:
        failures.append(
            "enterprise response normalization coverage is missing from docs-site inputs"
        )
    if DOC_REL not in review_docs:
        failures.append("enterprise response normalization coverage is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing enterprise response normalization coverage")
    if "enterprise-response-normalization-coverage" not in release_guardrails:
        failures.append(
            "release guardrails do not require enterprise response normalization coverage"
        )
    if "enterprise-response-normalization-coverage" not in status_board_doc:
        failures.append("enterprise response status board doc is missing coverage gate pointer")
    if "enterprise-response-normalization-coverage" not in dual_inbox_doc:
        failures.append("enterprise dual-response inbox doc is missing coverage gate pointer")
    if "enterprise-response-normalization-coverage" not in queue_doc:
        failures.append("enterprise external-review queue doc is missing coverage gate pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "coverage_doc": DOC_REL,
        "tool_count": 24,
        "selected_capability": "not selected",
        "lane_count": len(board_areas),
        "covered_area_count": len(namespaces),
        "missing_areas": missing_areas,
        "area_namespaces": namespaces,
        "normalizes_responses": False,
        "writes_response_files": False,
        "committed_findings_mutated": False,
        "external_review_recorded": False,
        "closes_enterprise_lanes": False,
        "runtime_changes_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise response normalization coverage",
        f"valid: {str(report['valid']).lower()}",
        f"coverage_doc: {report['coverage_doc']}",
        f"tool_count: {report['tool_count']}",
        f"selected_capability: {report['selected_capability']}",
        f"lane_count: {report['lane_count']}",
        f"covered_area_count: {report['covered_area_count']}",
        f"missing_areas: {', '.join(report['missing_areas']) or 'none'}",
        f"normalizes_responses: {str(report['normalizes_responses']).lower()}",
        f"writes_response_files: {str(report['writes_response_files']).lower()}",
        f"committed_findings_mutated: {str(report['committed_findings_mutated']).lower()}",
        f"external_review_recorded: {str(report['external_review_recorded']).lower()}",
        f"closes_enterprise_lanes: {str(report['closes_enterprise_lanes']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
        "areas:",
    ]
    for area, namespace in sorted(report["area_namespaces"].items()):
        lines.append(f"- {area}: {namespace}")
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


if __name__ == "__main__":
    raise SystemExit(main())

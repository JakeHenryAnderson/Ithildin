"""Validate v0.6 closure-readiness docs without closing external review."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import v06_lane_status

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DOCS = (
    "docs/codex/v0.6-critical-high-fix-freeze.md",
    "docs/codex/v0.6-medium-risk-disposition.md",
    "docs/codex/v0.6-external-review-outcome-summary.md",
    "docs/codex/source-review-closure-matrix-v4.md",
    "docs/codex/accepted-risk-register-v2.md",
    "docs/codex/accepted-risk-register-v2.json",
    "docs/codex/v0.6-post-review-packet.md",
)
FORBIDDEN_PHRASES = (
    "capability expansion allowed: true",
    "capability expansion: allowed",
    "external review complete",
    "external source review complete",
    "production ready",
    "new tool powers approved",
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
    lane_board = v06_lane_status.build_lane_status(repo_root)
    required_paths = [repo_root / doc for doc in REQUIRED_DOCS]
    for path in required_paths:
        if not path.exists():
            relative = path.relative_to(repo_root)
            failures.append(f"required closure-readiness doc missing: {relative}")

    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in required_paths if path.exists()
    ).lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in combined and f"not {phrase}" not in combined:
            failures.append(f"closure-readiness docs contain forbidden phrase: {phrase}")

    accepted_risk_v2 = _load_json(
        repo_root / "docs/codex/accepted-risk-register-v2.json",
        failures,
    )
    if accepted_risk_v2:
        if accepted_risk_v2.get("capability_expansion_allowed") is not False:
            failures.append("accepted-risk v2 must not approve capability expansion")
        if accepted_risk_v2.get("risk_count") != 10:
            failures.append("accepted-risk v2 must track the 10 accepted local-preview risks")
        if (
            accepted_risk_v2.get("closed_local_preview_risk_count", 0)
            + accepted_risk_v2.get("accepted_deferred_risk_count", 0)
            != 10
        ):
            failures.append("accepted-risk v2 must disposition all 10 accepted risks")

    if lane_board["summary"]["critical_high_open_count"] != 0:
        failures.append("lane-status board reports open critical/high findings")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "required_doc_count": len(REQUIRED_DOCS),
        "lane_count": lane_board["summary"]["lane_count"],
        "external_review_received": lane_board["summary"]["external_review_received"],
        "external_review_closed": lane_board["summary"]["external_review_closed"],
        "critical_high_open_count": lane_board["summary"]["critical_high_open_count"],
        "capability_expansion_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v0.6 closure-readiness check",
        f"valid: {str(report['valid']).lower()}",
        f"required_doc_count: {report['required_doc_count']}",
        f"lane_count: {report['lane_count']}",
        f"external_review_received: {report['external_review_received']}",
        f"external_review_closed: {report['external_review_closed']}",
        f"critical_high_open_count: {report['critical_high_open_count']}",
        "capability_expansion_allowed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _load_json(path: Path, failures: list[str]) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        failures.append(f"{path.name} is invalid JSON: {exc}")
        return {}
    if not isinstance(payload, dict):
        failures.append(f"{path.name} must contain a JSON object")
        return {}
    return payload


if __name__ == "__main__":
    raise SystemExit(main())

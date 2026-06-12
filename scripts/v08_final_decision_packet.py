"""Validate the v0.8 final product-risk decision packet."""

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
    no_new_powers_guardrail,
    v08_capability_design_gate,
    v08_public_preview_decision,
    v08_status_reconciliation,
)

ROOT = Path(__file__).resolve().parents[1]
PACKET_DOC = ROOT / "docs/codex/v0.8-final-decision-packet.md"
SUB_080_DOC = ROOT / "docs/codex/findings/sub-080-review-console-ui-test-harness.md"
REQUIRED_PHRASES = [
    "Local-preview implementation lanes",
    "closed/reference-only",
    "Accepted-risk rows",
    "dispositioned",
    "Continued local-preview development",
    "go",
    "Limited technical-preview sharing",
    "conditional_go",
    "Public/security-product positioning",
    "no_go",
    "Capability implementation",
    "no_go",
    "Capability design-only planning",
    "conditional_go",
    "`SUB-080` review-console interaction assurance",
    "fixed",
    "make v08-final-decision-packet",
    "make ui-test",
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
    packet_path = repo_root / PACKET_DOC.relative_to(ROOT)
    if not packet_path.exists():
        return _report(["v0.8 final decision packet is missing"], {})

    text = packet_path.read_text(encoding="utf-8")
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            failures.append(f"v0.8 final decision packet is missing phrase: {phrase}")

    sub_080_path = repo_root / SUB_080_DOC.relative_to(ROOT)
    if not sub_080_path.exists():
        failures.append("SUB-080 finding record is missing")
    else:
        sub_080_text = sub_080_path.read_text(encoding="utf-8")
        if "- Disposition: fixed" not in sub_080_text:
            failures.append("SUB-080 is not marked fixed")
        if "- Blocking status: later" in sub_080_text:
            failures.append("SUB-080 still has stale deferred blocking status")
        if "npm run test --prefix apps/ui" not in sub_080_text:
            failures.append("SUB-080 does not record UI test verification")

    status = v08_status_reconciliation.build_report(repo_root)
    public_preview = v08_public_preview_decision.build_report(repo_root)
    capability = v08_capability_design_gate.build_report(repo_root)
    accepted_risks = accepted_risk_register.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)

    for name, report in [
        ("status reconciliation", status),
        ("public-preview decision", public_preview),
        ("capability-design gate", capability),
        ("accepted-risk register", accepted_risks),
        ("no-new-powers guardrail", no_new_powers),
    ]:
        failures.extend(f"{name}: {failure}" for failure in report.get("failures", []))
        if not report.get("valid", False):
            failures.append(f"{name} is invalid")

    if status.get("product_decision_rows_pending") is not False:
        failures.append("status reconciliation still reports product decision rows pending")
    if public_preview.get("public_security_product_positioning") != "no_go":
        failures.append("public/security-product positioning is not no_go")
    if capability.get("capability_design_only") != "conditional_go":
        failures.append("capability design-only decision is not conditional_go")
    if capability.get("capability_implementation") != "no_go":
        failures.append("capability implementation is not no_go")
    if no_new_powers.get("tool_count") != 16:
        failures.append("tool count drifted from the approved 16-tool read-only metadata surface")

    return _report(
        failures,
        {
            "tool_count": no_new_powers.get("tool_count"),
            "closed_local_preview_risks": accepted_risks.get("closed_local_preview_ids", []),
            "accepted_deferred_risks": accepted_risks.get("accepted_deferred_ids", []),
        },
    )


def _report(failures: list[str], evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "local_preview_lanes": "closed_reference_only",
        "public_security_product_positioning": "no_go",
        "capability_implementation": "no_go",
        "capability_design_only": "conditional_go",
        "sub_080": "fixed",
        "evidence": evidence,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v0.8 final decision packet",
        f"valid: {str(report['valid']).lower()}",
        "local_preview_lanes: closed_reference_only",
        "public_security_product_positioning: no_go",
        "capability_implementation: no_go",
        "capability_design_only: conditional_go",
        "sub_080: fixed",
        f"tool_count: {report['evidence'].get('tool_count', 'unknown')}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

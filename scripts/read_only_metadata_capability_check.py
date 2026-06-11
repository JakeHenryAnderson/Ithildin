"""Validate shared read-only local metadata capability hardening docs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import no_new_powers_guardrail

ROOT = Path(__file__).resolve().parents[1]
DOC_REQUIREMENTS = {
    "docs/codex/read-only-local-metadata-contract.md": [
        "Status: capability-expansion preparation",
        "strict JSON Schema with `additionalProperties: false`",
        "avoid shell execution entirely",
        "avoid caller-controlled argv",
        "suppress remote/network behavior by construction",
        "policy-preview/runtime comparable",
        "audit-evidence producing",
        "Before implementation",
        "Before runtime implementation can be committed",
        "Non-Goals",
    ],
    "docs/codex/metadata-privacy-policy.md": [
        "Status: capability-expansion preparation",
        "Sensitive By Default",
        "Stable hashes are not anonymity guarantees",
        "response-local opaque IDs",
        "domain-separated keyed HMACs",
        "repository/workspace-scoped salted digests",
        "Repository-Controlled Text",
        "Audit Rule",
        "UI Rule",
    ],
    "docs/codex/read-only-metadata-capability-checklist.md": [
        "Status: reusable capability-prep checklist",
        "Proposal Gate",
        "Implementation-Planning Gate",
        "Implementation Gate",
        "Stop Conditions",
        "additionalProperties: false",
        "internal xhigh review",
        "implementation remains blocked",
    ],
    "docs/codex/read-only-capability-source-review-template.md": [
        "Status: reusable source-review bundle guidance",
        "Ten-Artifact Bundle Shape",
        "Required Source Bundle Sections",
        "Required Test Bundle Sections",
        "Required Contract Sections",
        "Prompt Requirements",
        "Evidence Requirements",
        "artifact-hashes.json",
    ],
    "docs/codex/v3-readiness-debt-register.md": [
        "Status: planning and hardening register",
        "Tool count is `14`",
        "project.manifest.summary",
        "make next-capability-readiness",
        "Public/security-product positioning remains blocked",
        "Broader capability expansion remains blocked",
        "Debt That Blocks Public/Security-Product Positioning",
        "Debt That Blocks New Powerful Tool Classes",
        "Debt That Should Be Paid Before More Read-Only Metadata Tools",
        "Do not expand into new powerful tool classes",
    ],
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
    checked_docs: list[str] = []
    for rel_path, phrases in DOC_REQUIREMENTS.items():
        path = repo_root / rel_path
        if not path.exists():
            failures.append(f"{rel_path} is missing")
            continue
        checked_docs.append(rel_path)
        text = path.read_text(encoding="utf-8")
        for phrase in phrases:
            if phrase not in text:
                failures.append(f"{rel_path} is missing phrase: {phrase}")

    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "checked_docs": checked_docs,
        "tool_count": no_new_powers.get("tool_count"),
        "new_power_classes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin read-only metadata capability check",
        f"valid: {str(report['valid']).lower()}",
        f"checked_docs: {len(report['checked_docs'])}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        "new_power_classes_allowed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

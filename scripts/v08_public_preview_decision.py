"""Validate the v0.8 public-preview claims decision."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DECISION_DOC = ROOT / "docs/codex/v0.8-public-preview-risk-review.md"
CLAIM_DOCS = [
    ROOT / "README.md",
    ROOT / "docs/codex/local-preview-release.md",
    ROOT / "docs/codex/operator-quickstart-v2.md",
    ROOT / "docs/codex/v0.8-public-preview-risk-review.md",
    ROOT / "docs/codex/v0.8-final-decision-packet.md",
]
REQUIRED_DECISIONS = {
    "continued local-preview development": "go",
    "limited technical-preview sharing": "conditional_go",
    "broad public/security-product positioning": "no_go",
    "production/security/compliance positioning": "no_go",
}
REQUIRED_WARNINGS = [
    "local preview only",
    "not a sandbox",
    "not production security",
    "not production identity",
    "not immutable",
    "not external notarization",
    "not hosted mcp",
    "redaction is best-effort",
    "no shell",
    "no new governed tool powers",
]
FORBIDDEN_PUBLIC_CLAIMS = [
    "production-ready",
    "secure sandbox",
    "security product",
    "production security software",
    "enterprise identity",
    "tamper-proof audit",
    "immutable audit",
    "compliance-grade",
    "compliance tool",
    "production control plane",
    "custody-grade",
    "notarized",
    "runtime postgres",
    "hosted telemetry",
    "remote mcp gateway",
    "safe arbitrary tool use",
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
    decision_path = repo_root / DECISION_DOC.relative_to(ROOT)
    if not decision_path.exists():
        return _report(["v0.8 public-preview risk review doc is missing"], [])

    decision_text = decision_path.read_text(encoding="utf-8").lower()
    for label, expected in REQUIRED_DECISIONS.items():
        if label not in decision_text or expected not in decision_text:
            failures.append(f"public-preview decision is missing {label}: {expected}")
    for warning in REQUIRED_WARNINGS:
        if warning not in decision_text:
            failures.append(f"public-preview decision is missing warning: {warning}")

    checked_docs: list[str] = []
    for doc in CLAIM_DOCS:
        path = repo_root / doc.relative_to(ROOT)
        checked_docs.append(path.relative_to(repo_root).as_posix())
        if not path.exists():
            failures.append(f"public-preview claim doc is missing: {checked_docs[-1]}")
            continue
        text = path.read_text(encoding="utf-8").lower()
        for phrase in FORBIDDEN_PUBLIC_CLAIMS:
            if phrase in text and _is_unqualified_claim(text, phrase):
                failures.append(f"{checked_docs[-1]} contains unqualified claim: {phrase}")

    return _report(failures, checked_docs)


def _is_unqualified_claim(text: str, phrase: str) -> bool:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if phrase not in line:
            continue
        context = " ".join(lines[max(0, index - 3) : index + 2])
        if any(
            marker in line
            or marker in context
            for marker in [
                "not ",
                "no ",
                "no_",
                "avoid ",
                "deliberately does not",
                "forbidden",
                "deferred",
                "deferred-power",
                "blocked",
                "unsupported",
                "remain",
            ]
        ):
            continue
        return True
    return False


def _report(failures: list[str], checked_docs: list[str]) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "checked_docs": checked_docs,
        "continued_local_preview_development": "go",
        "limited_technical_preview_sharing": "conditional_go",
        "public_security_product_positioning": "no_go",
        "production_security_compliance_positioning": "no_go",
        "capability_implementation": "no_go",
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v0.8 public-preview decision",
        f"valid: {str(report['valid']).lower()}",
        "continued_local_preview_development: go",
        "limited_technical_preview_sharing: conditional_go",
        "public_security_product_positioning: no_go",
        "production_security_compliance_positioning: no_go",
        "capability_implementation: no_go",
        f"checked_docs: {len(report['checked_docs'])}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

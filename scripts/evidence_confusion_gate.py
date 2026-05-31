"""Validate that signed-evidence docs do not overclaim trust semantics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_EVIDENCE_DOCS = {
    "docs/codex/signed-audit-exports.md": [
        "not external notarization",
        "runtime signing may still be unconfigured by default",
        "local fixture evidence only",
    ],
    "docs/codex/signed-manifest-locks.md": [
        "not external notarization",
        "Signed-lock enforcement is opt-in",
        "non-production signed-evidence demo",
    ],
    "docs/codex/evidence-contracts.md": [
        "not external notarization",
        "They do not provide hosted",
        "official supply-chain signing",
    ],
    "docs/codex/v0.2-review-packet.md": [
        "Optional locally signed Ed25519 evidence",
        "non-production locally signed evidence",
        "external custody",
    ],
    "docs/codex/reviewer-reproduction-map.md": [
        "runtime signing may be unconfigured",
        "signed-evidence demo is separate fixture evidence",
        "notarization, custody-grade evidence",
    ],
}

OVERCLAIM_PHRASES = [
    "tamper-proof",
    "immutable storage",
    "immutable evidence",
    "custody-grade",
    "external notarization",
    "hosted custody",
    "official supply-chain signing",
    "production key management",
]
WARNING_CONTEXT = [
    "not",
    "no ",
    "without",
    "deferred",
    "non-goal",
    "does not",
    "do not",
    "is not",
    "only",
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
    return 1 if report["failures"] else 0


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    checked_docs: list[str] = []
    overclaim_hits: list[dict[str, Any]] = []

    for doc_path, required_phrases in REQUIRED_EVIDENCE_DOCS.items():
        path = repo_root / doc_path
        if not path.exists():
            failures.append(f"missing evidence doc: {doc_path}")
            continue
        checked_docs.append(doc_path)
        text = path.read_text(encoding="utf-8")
        searchable_text = " ".join(text.split()).lower()
        for phrase in required_phrases:
            if phrase.lower() not in searchable_text:
                failures.append(f"{doc_path} is missing evidence-boundary phrase: {phrase}")
        overclaim_hits.extend(_overclaim_hits(doc_path, text))

    if overclaim_hits:
        failures.append("evidence docs contain overclaim phrases outside warning context")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "checked_docs": checked_docs,
        "overclaim_hits": overclaim_hits,
        "runtime_signing_required_by_default": False,
        "demo_evidence_is_non_production": True,
    }


def _overclaim_hits(doc_path: str, text: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        normalized = line.lower()
        for phrase in OVERCLAIM_PHRASES:
            if phrase in normalized and not any(
                context in normalized for context in WARNING_CONTEXT
            ):
                hits.append(
                    {
                        "path": doc_path,
                        "line": line_number,
                        "phrase": phrase,
                        "text": line.strip(),
                    }
                )
    return hits


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin evidence-confusion gate",
        f"valid: {str(report['valid']).lower()}",
        f"checked_docs: {len(report['checked_docs'])}",
        "runtime_signing_required_by_default: false",
        "demo_evidence_is_non_production: true",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

"""Validate the bounded Node configuration trust-rotation decision packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TARGET = "track-b-node-configuration-trust-rotation-decision-check"
DOCS = (
    "docs/codex/track-b-node-configuration-trust-rotation-capability-decision.md",
    "docs/codex/track-b-node-configuration-trust-rotation-architecture.md",
    "docs/codex/track-b-node-configuration-trust-rotation-implementation-plan.md",
)
REQUIRED_PHRASES = (
    "Current governed tool count: `24`.",
    "ITHILDIN-NODE-CONFIG-TRUST-V1",
    "staged_not_active",
    "BEGIN IMMEDIATE",
    "recovery-only",
    "does not rewrite or close",
    "process restart",
    "private key material is never accepted",
    "runner enforcement",
)
FORBIDDEN_APPROVALS = (
    "automatic rotation is approved",
    "bulk rotation is approved",
    "private-key upload is approved",
    "production pki is approved",
    "runner enforcement is approved",
)


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    texts: list[str] = []
    for relative in DOCS:
        path = repo_root / relative
        if not path.is_file():
            failures.append(f"missing trust-rotation document: {relative}")
            texts.append("")
        else:
            texts.append(path.read_text(encoding="utf-8"))
    combined = "\n".join(texts)
    lowered = combined.lower()
    for phrase in REQUIRED_PHRASES:
        if phrase not in combined:
            failures.append(f"trust-rotation packet is missing required phrase: {phrase}")
    for phrase in FORBIDDEN_APPROVALS:
        if phrase in lowered:
            failures.append(f"trust-rotation packet contains forbidden approval: {phrase}")

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_docs = _read(repo_root / "scripts/review_docs.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if f"release-check: {TARGET}" not in makefile:
        failures.append("trust-rotation decision check is missing from release-check")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing the trust-rotation decision check")
    for relative in DOCS:
        if relative not in readme:
            failures.append(f"README is missing: {relative}")
        if relative not in docs_site:
            failures.append(f"docs site is missing: {relative}")
        if relative not in review_docs:
            failures.append(f"review docs are missing: {relative}")
    if "Track B Node Configuration Trust Rotation" not in review_index:
        failures.append("review docs index is missing the trust-rotation section")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "documents": list(DOCS),
        "tool_count": 24,
        "signed_transition_allowed": True,
        "restart_based_activation_allowed": True,
        "automatic_rotation_allowed": False,
        "private_key_api_allowed": False,
        "runner_enforcement_claim_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Track B Node configuration trust-rotation decision check",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report['tool_count']}",
        f"signed_transition_allowed: {str(report['signed_transition_allowed']).lower()}",
        "restart_based_activation_allowed: "
        f"{str(report['restart_based_activation_allowed']).lower()}",
        f"automatic_rotation_allowed: {str(report['automatic_rotation_allowed']).lower()}",
        f"private_key_api_allowed: {str(report['private_key_api_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report(args.repo_root.resolve())
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_report(report))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

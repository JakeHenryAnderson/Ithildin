"""Validate the sandbox promotion evidence contract boundary and wiring."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import no_new_powers_guardrail, review_docs, tool_surface_invariant_gate

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/sandbox-promotion-evidence-contract.md"
REQUIRED_PHRASES = [
    "Status: design-only evidence contract.",
    "does not implement promotion",
    "promotion_id",
    "mission_id",
    "run_id",
    "workspace_id",
    "sandbox_id",
    "source_artifact_sha256",
    "host_staging_sha256",
    "approved_host_sha256",
    "approval_id",
    "operator_principal",
    "policy_hash",
    "manifest_hash",
    "auto_promotion_performed",
    "sandbox source hash equals host staging hash",
    "host staging hash equals approved host hash",
    "approval ID is present before trusted host placement",
    "promotion target is not hidden",
    "no file contents",
    "no raw host paths",
    "future explicitly approved promotion implementation",
]
FORBIDDEN_PHRASES = [
    "production-ready",
    "compliance-grade",
    "tamper-proof",
    "secure sandbox",
    "safe arbitrary tool use",
    "automatic host promotion is approved",
    "promotion is implemented",
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
    makefile = repo_root.joinpath("Makefile").read_text(encoding="utf-8")
    readme = repo_root.joinpath("README.md").read_text(encoding="utf-8")
    docs_site = repo_root.joinpath("scripts/build_docs_site.py").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])

    if not DOC.exists():
        failures.append("sandbox promotion evidence contract doc is missing")
    else:
        text = DOC.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"sandbox promotion contract is missing phrase: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase in lowered:
                failures.append(f"sandbox promotion contract contains forbidden phrase: {phrase}")
    rel_path = DOC.relative_to(repo_root).as_posix()
    if rel_path not in review_docs.REVIEW_DOCS:
        failures.append("sandbox promotion contract is missing from review docs")
    if rel_path not in docs_site:
        failures.append("sandbox promotion contract is missing from docs-site inputs")
    if "sandbox-promotion-evidence-contract-check:" not in makefile:
        failures.append("Make target is missing: sandbox-promotion-evidence-contract-check")
    if "sandbox-promotion-evidence-contract-check" not in release_check_body:
        failures.append("sandbox-promotion-evidence-contract-check is missing from release-check")
    if "make sandbox-promotion-evidence-contract-check" not in readme:
        failures.append("README is missing make sandbox-promotion-evidence-contract-check")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "tool_count": tool_surface.get("tool_count"),
        "scope": "design_only_evidence_contract",
        "runtime_changes_allowed": False,
        "host_promotion_implemented": False,
        "mission_control_runtime_behavior_allowed": False,
        "sandbox_orchestration_allowed": False,
        "new_power_classes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox promotion evidence contract check",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        "scope: design_only_evidence_contract",
        "runtime_changes_allowed: false",
        "host_promotion_implemented: false",
        "mission_control_runtime_behavior_allowed: false",
        "sandbox_orchestration_allowed: false",
        "new_power_classes_allowed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

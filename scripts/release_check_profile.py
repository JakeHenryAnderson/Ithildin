"""Summarize the static shape of the release-check Make target."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

CATEGORY_PREFIXES: tuple[tuple[str, str], ...] = (
    ("hermes-", "external_agent_poc"),
    ("enterprise-", "enterprise"),
    ("mission-control-", "mission_control"),
    ("sandbox-vm-", "sandbox_vm"),
    ("sandbox-artifact-", "sandbox_artifact"),
    ("trusted-host-", "trusted_host"),
    ("production-identity-", "production_identity_storage"),
    ("siem-", "siem"),
    ("compliance-", "compliance"),
    ("public-", "public_positioning"),
    ("post-erg005-", "status_efficiency"),
    ("post-rc-", "post_rc_decision"),
    ("project-", "project_metadata"),
    ("git-", "git_metadata"),
    ("agent-run-", "agent_run"),
    ("agent-workflow-", "agent_workflow"),
    ("low-implementer-", "agent_workflow"),
    ("governed-artifact-transfer-", "governed_artifact_transfer"),
    ("hello-world-", "governed_artifact_transfer"),
    ("v1-", "v1_rc"),
    ("v0", "versioned_review"),
    ("v3-", "v3_readiness"),
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
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    release_lines = _release_check_lines(makefile)
    targets = _release_check_targets(makefile)
    unique_targets = list(dict.fromkeys(targets))
    duplicates = sorted(
        target for target, count in Counter(targets).items() if count > 1
    )
    category_counts = Counter(_category(target) for target in unique_targets)
    grouped_targets = targets_by_category(unique_targets)
    other_targets = grouped_targets.get("other", [])
    categories = [
        {
            "category": category,
            "target_count": count,
            "targets": grouped_targets[category],
        }
        for category, count in sorted(category_counts.items())
    ]
    heaviest_categories = sorted(
        categories,
        key=lambda row: (-_target_count(row), str(row["category"])),
    )[:8]

    failures: list[str] = []
    if not targets:
        failures.append("release-check has no parsed prerequisites")
    if "release-context" not in unique_targets:
        failures.append("release-check profile expected release-context")
    if "test" not in unique_targets:
        failures.append("release-check profile expected full Python test target")
    if "ui-test" not in unique_targets:
        failures.append("release-check profile expected UI test target")
    if "docs-site" not in unique_targets:
        failures.append("release-check profile expected docs-site target")
    if duplicates:
        failures.append(
            "release-check has duplicate prerequisites: " + ", ".join(duplicates)
        )

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "release_check_line_count": len(release_lines),
        "target_count": len(targets),
        "unique_target_count": len(unique_targets),
        "duplicate_target_count": len(duplicates),
        "duplicate_targets": duplicates,
        "other_target_count": len(other_targets),
        "other_targets": other_targets,
        "categories": categories,
        "heaviest_categories": heaviest_categories,
        "contains_full_test": "test" in unique_targets,
        "contains_ui_build": _release_check_has_ui_build(makefile),
        "contains_docs_site": "docs-site" in unique_targets,
        "targets": unique_targets,
        "notes": [
            "This is a static Makefile profile; it does not execute release-check.",
            "Use validation-decision or smart-check for routine development.",
            "Use release-check for release proof, external handoff, or major checkpoint evidence.",
        ],
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin release-check profile",
        f"valid: {str(report['valid']).lower()}",
        f"release_check_line_count: {report['release_check_line_count']}",
        f"target_count: {report['target_count']}",
        f"unique_target_count: {report['unique_target_count']}",
        f"duplicate_target_count: {report['duplicate_target_count']}",
        f"other_target_count: {report['other_target_count']}",
        f"contains_full_test: {str(report['contains_full_test']).lower()}",
        f"contains_ui_build: {str(report['contains_ui_build']).lower()}",
        f"contains_docs_site: {str(report['contains_docs_site']).lower()}",
        "heaviest_categories:",
    ]
    lines.extend(
        f"- {row['category']}: {row['target_count']}"
        for row in report["heaviest_categories"]
    )
    if report["duplicate_targets"]:
        lines.append("duplicate_targets:")
        lines.extend(f"- {target}" for target in report["duplicate_targets"])
    if report["other_targets"]:
        lines.append("other_targets:")
        lines.extend(f"- {target}" for target in report["other_targets"])
    if report["notes"]:
        lines.append("notes:")
        lines.extend(f"- {note}" for note in report["notes"])
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _release_check_lines(makefile: str) -> list[str]:
    return [
        line
        for line in makefile.splitlines()
        if line.startswith("release-check:")
    ]


def _release_check_targets(makefile: str) -> list[str]:
    targets: list[str] = []
    for line in _release_check_lines(makefile):
        _, _, tail = line.partition(":")
        targets.extend(token for token in tail.split() if token)
    return targets


def _release_check_has_ui_build(makefile: str) -> bool:
    body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    return "npm run build --prefix apps/ui" in body


def _category(target: str) -> str:
    for prefix, category in CATEGORY_PREFIXES:
        if target.startswith(prefix):
            return category
    if target in {"test", "test-fast", "lint", "typecheck", "ui-test"}:
        return "test_lint_typecheck"
    if target in {"docs-site", "release-guardrails", "release-context"}:
        return "core_release"
    if target in {
        "filesystem-contract-check",
        "determinism-check",
        "adversarial-corpus-check",
        "resource-limit-check",
    }:
        return "hardening"
    if target in {
        "tool-surface-invariant-gate",
        "no-new-powers-guardrail",
        "read-only-metadata-capability-check",
        "read-only-capability-inventory-gate",
        "read-only-project-intelligence",
        "next-capability-readiness",
        "next-capability-candidate-evaluation-2-check",
        "capability-decision-report",
    }:
        return "capability_governance"
    if target in {
        "data-classification-design-check",
        "control-mapping-design-check",
        "incident-reconstruction-check",
        "observability-readiness",
        "control-mapping-readiness",
    }:
        return "observability_control"
    if target in {
        "accepted-risk-register-check",
        "external-findings-intake-dry-run",
    }:
        return "risk_findings"
    if target in {
        "technical-mvp-ticket-map",
        "technical-mvp-execution-board",
        "development-efficiency-status",
    }:
        return "status_efficiency"
    if "review" in target or "packet" in target:
        return "review_packet"
    if "evidence" in target or "audit" in target:
        return "evidence"
    if "policy" in target or "manifest" in target or "registry" in target:
        return "policy_registry_manifest"
    if "demo" in target or "workbench" in target or "operator" in target:
        return "demo_operator"
    return "other"


def targets_by_category(targets: list[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for target in targets:
        grouped.setdefault(_category(target), []).append(target)
    return dict(sorted(grouped.items()))


def _target_count(row: dict[str, object]) -> int:
    value = row["target_count"]
    if not isinstance(value, int):
        raise TypeError("target_count must be an int")
    return value


if __name__ == "__main__":
    raise SystemExit(main())

"""Recommend release-check slice categories for a changed file set."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import release_check_profile, validation_plan

ROOT = Path(__file__).resolve().parents[1]

PATH_CATEGORY_RULES: tuple[tuple[str, str], ...] = (
    ("docs/codex/enterprise-", "enterprise"),
    ("scripts/enterprise_", "enterprise"),
    ("docs/codex/mission-control-", "mission_control"),
    ("scripts/mission_control_", "mission_control"),
    ("docs/codex/sandbox-vm-", "sandbox_vm"),
    ("scripts/sandbox_vm_", "sandbox_vm"),
    ("docs/codex/trusted-host-", "trusted_host"),
    ("scripts/trusted_host_", "trusted_host"),
    ("docs/codex/production-identity-", "production_identity_storage"),
    ("scripts/production_identity_", "production_identity_storage"),
    ("docs/codex/siem-", "siem"),
    ("scripts/siem_", "siem"),
    ("docs/codex/compliance-", "compliance"),
    ("scripts/compliance_", "compliance"),
    ("docs/codex/public-security-product-", "public_positioning"),
    ("scripts/public_security_product_", "public_positioning"),
    ("docs/codex/project-", "project_metadata"),
    ("scripts/project_", "project_metadata"),
    ("docs/codex/git-", "git_metadata"),
    ("scripts/git_", "git_metadata"),
    ("docs/codex/agent-run-", "agent_run"),
    ("scripts/agent_run_", "agent_run"),
    ("docs/codex/v1-", "v1_rc"),
    ("scripts/v1_", "v1_rc"),
)

VALIDATION_CATEGORY_SLICES = {
    "manifest": ["policy_registry_manifest"],
    "policy_registry": ["policy_registry_manifest"],
    "review_packet": ["review_packet"],
    "runtime": ["test_lint_typecheck"],
    "ui": ["test_lint_typecheck"],
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", help="changed files to classify")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = build_report(ROOT, files=args.files)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(repo_root: Path, *, files: list[str] | None = None) -> dict[str, Any]:
    changed_files = files or validation_plan.changed_files(repo_root)
    plan = validation_plan.build_report(changed_files)
    profile = release_check_profile.build_report(repo_root)
    available_categories = {
        str(row["category"])
        for row in profile["categories"]
        if isinstance(row.get("category"), str)
    }
    slice_categories = _slice_categories(plan, available_categories)
    invalid_categories = sorted(set(slice_categories) - available_categories)
    failures: list[str] = []
    if profile["valid"] is not True:
        failures.append("release-check profile is not valid")
    if invalid_categories:
        failures.append(
            "impact planner selected unknown release-check categories: "
            + ", ".join(invalid_categories)
        )

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "files": plan["files"],
        "file_count": plan["file_count"],
        "validation_categories": plan["categories"],
        "development_commands": plan["development_commands"],
        "deferred_handoff_commands": plan["deferred_handoff_commands"],
        "release_or_handoff_required": bool(plan["deferred_handoff_commands"]),
        "slice_categories": slice_categories,
        "slice_commands": [
            f'make release-check-slice ARGS="--category {category}"'
            for category in slice_categories
        ],
        "notes": _notes(slice_categories),
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin release-check impact",
        f"valid: {str(report['valid']).lower()}",
        f"file_count: {report['file_count']}",
        "validation_categories: "
        + (", ".join(report["validation_categories"]) or "none"),
        f"release_or_handoff_required: {str(report['release_or_handoff_required']).lower()}",
        "development_commands:",
    ]
    lines.extend(f"- {command}" for command in report["development_commands"])
    if report["deferred_handoff_commands"]:
        lines.append("deferred_handoff_commands:")
        lines.extend(f"- {command}" for command in report["deferred_handoff_commands"])
    if report["slice_categories"]:
        lines.append("slice_categories:")
        lines.extend(f"- {category}" for category in report["slice_categories"])
        lines.append("slice_commands:")
        lines.extend(f"- {command}" for command in report["slice_commands"])
    else:
        lines.append("slice_categories: none")
    if report["notes"]:
        lines.append("notes:")
        lines.extend(f"- {note}" for note in report["notes"])
    if report["files"]:
        lines.append("files:")
        lines.extend(f"- {path}" for path in report["files"])
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _slice_categories(
    plan: dict[str, Any], available_categories: set[str]
) -> list[str]:
    categories: list[str] = []
    for path in plan["files"]:
        categories.extend(_path_categories(path))
    for validation_category in plan["categories"]:
        categories.extend(VALIDATION_CATEGORY_SLICES.get(validation_category, []))
    return [
        category
        for category in dict.fromkeys(categories)
        if category in available_categories
    ]


def _path_categories(path: str) -> list[str]:
    categories = [
        category
        for prefix, category in PATH_CATEGORY_RULES
        if path.startswith(prefix)
    ]
    if path in {"Makefile", "README.md", "AGENTS.md"}:
        categories.append("core_release")
    return categories


def _notes(slice_categories: list[str]) -> list[str]:
    notes = [
        "Release-check slices are focused development evidence, not release proof.",
        "Run full release-check before release, external handoff, or major checkpoint claims.",
    ]
    if not slice_categories:
        notes.append("No specific release-check slice category was inferred.")
    return notes


if __name__ == "__main__":
    raise SystemExit(main())

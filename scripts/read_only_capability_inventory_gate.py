"""Validate the approved read-only local metadata capability inventory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import no_new_powers_guardrail, review_docs, tool_surface_invariant_gate

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_DOC = ROOT / "docs/codex/read-only-capability-inventory.md"
APPROVED_CAPABILITIES = [
    {
        "tool_name": "git.show.commit_metadata",
        "manifest": "tool-manifests/git-show-commit-metadata.yaml",
        "proposal": "docs/codex/capability-proposals/git-show-commit-metadata.md",
        "implementation_plan": (
            "docs/codex/capability-implementation-plans/git-show-commit-metadata.md"
        ),
        "implementation": "docs/codex/v0.9-git-commit-metadata-implementation.md",
        "source_review": "docs/codex/v0.9-git-commit-metadata-source-review.md",
        "implementation_gate": "git-commit-metadata-implementation-gate",
        "source_review_bundle": "git-commit-metadata-source-review-bundle",
    },
    {
        "tool_name": "git.show.ref_summary",
        "manifest": "tool-manifests/git-show-ref-summary.yaml",
        "proposal": "docs/codex/capability-proposals/git-show-ref-summary.md",
        "implementation_plan": "docs/codex/capability-implementation-plans/git-show-ref-summary.md",
        "implementation": "docs/codex/v0.9-git-ref-summary-implementation.md",
        "source_review": "docs/codex/v0.9-git-ref-summary-source-review.md",
        "implementation_gate": "git-ref-summary-implementation-gate",
        "source_review_bundle": "git-ref-summary-source-review-bundle",
    },
    {
        "tool_name": "git.show.tag_metadata",
        "manifest": "tool-manifests/git-show-tag-metadata.yaml",
        "proposal": "docs/codex/capability-proposals/git-show-tag-metadata.md",
        "implementation_plan": (
            "docs/codex/capability-implementation-plans/git-show-tag-metadata.md"
        ),
        "implementation": "docs/codex/v0.9-git-tag-metadata-implementation.md",
        "source_review": "docs/codex/v0.9-git-tag-metadata-source-review.md",
        "implementation_gate": "git-tag-metadata-implementation-gate",
        "source_review_bundle": "git-tag-metadata-source-review-bundle",
    },
    {
        "tool_name": "project.manifest.summary",
        "manifest": "tool-manifests/project-manifest-summary.yaml",
        "proposal": "docs/codex/capability-proposals/project-manifest-summary.md",
        "implementation_plan": (
            "docs/codex/capability-implementation-plans/project-manifest-summary.md"
        ),
        "implementation": "docs/codex/v3-project-manifest-summary-implementation.md",
        "source_review": "docs/codex/v3-project-manifest-summary-source-review.md",
        "implementation_gate": "project-manifest-summary-implementation-gate",
        "source_review_bundle": "project-manifest-summary-source-review-bundle",
    },
    {
        "tool_name": "project.dependency.summary",
        "manifest": "tool-manifests/project-dependency-summary.yaml",
        "proposal": "docs/codex/capability-proposals/project-dependency-summary.md",
        "implementation_plan": (
            "docs/codex/capability-implementation-plans/project-dependency-summary.md"
        ),
        "implementation": "docs/codex/v3-project-dependency-summary-implementation.md",
        "source_review": "docs/codex/v3-project-dependency-summary-source-review.md",
        "implementation_gate": "project-dependency-summary-implementation-gate",
        "source_review_bundle": "project-dependency-summary-source-review-bundle",
    },
    {
        "tool_name": "project.structure.summary",
        "manifest": "tool-manifests/project-structure-summary.yaml",
        "proposal": "docs/codex/capability-proposals/project-structure-summary.md",
        "implementation_plan": (
            "docs/codex/capability-implementation-plans/project-structure-summary.md"
        ),
        "implementation": "docs/codex/v3-project-structure-summary-implementation.md",
        "source_review": "docs/codex/v3-project-structure-summary-source-review.md",
        "implementation_gate": "project-structure-summary-implementation-gate",
        "source_review_bundle": "project-structure-summary-source-review-bundle",
    },
    {
        "tool_name": "project.test.summary",
        "manifest": "tool-manifests/project-test-summary.yaml",
        "proposal": "docs/codex/capability-proposals/project-test-summary.md",
        "implementation_plan": (
            "docs/codex/capability-implementation-plans/project-test-summary.md"
        ),
        "implementation": "docs/codex/v3-project-test-summary-implementation.md",
        "source_review": "docs/codex/v3-project-test-summary-source-review.md",
        "implementation_gate": "project-test-summary-implementation-gate",
        "source_review_bundle": "project-test-summary-source-review-bundle",
    },
    {
        "tool_name": "project.docs.summary",
        "manifest": "tool-manifests/project-docs-summary.yaml",
        "proposal": "docs/codex/capability-proposals/project-docs-summary.md",
        "implementation_plan": "docs/codex/capability-implementation-plans/project-docs-summary.md",
        "implementation": "docs/codex/v3-project-docs-summary-implementation.md",
        "source_review": "docs/codex/v3-project-docs-summary-source-review.md",
        "implementation_gate": "project-docs-summary-implementation-gate",
        "source_review_bundle": "project-docs-summary-source-review-bundle",
    },
    {
        "tool_name": "project.language.summary",
        "manifest": "tool-manifests/project-language-summary.yaml",
        "proposal": "docs/codex/capability-proposals/project-language-summary.md",
        "implementation_plan": (
            "docs/codex/capability-implementation-plans/project-language-summary.md"
        ),
        "implementation": "docs/codex/v3-project-language-summary-implementation.md",
        "source_review": "docs/codex/v3-project-language-summary-source-review.md",
        "implementation_gate": "project-language-summary-implementation-gate",
        "source_review_bundle": "project-language-summary-source-review-bundle",
    },
    {
        "tool_name": "project.config.summary",
        "manifest": "tool-manifests/project-config-summary.yaml",
        "proposal": "docs/codex/capability-proposals/project-config-summary.md",
        "implementation_plan": (
            "docs/codex/capability-implementation-plans/project-config-summary.md"
        ),
        "implementation": "docs/codex/v3-project-config-summary-implementation.md",
        "source_review": "docs/codex/v3-project-config-summary-source-review.md",
        "implementation_gate": "project-config-summary-implementation-gate",
        "source_review_bundle": "project-config-summary-source-review-bundle",
    },
    {
        "tool_name": "project.ci.summary",
        "manifest": "tool-manifests/project-ci-summary.yaml",
        "proposal": "docs/codex/capability-proposals/project-ci-summary.md",
        "implementation_plan": "docs/codex/capability-implementation-plans/project-ci-summary.md",
        "implementation": "docs/codex/v3-project-ci-summary-implementation.md",
        "source_review": "docs/codex/v3-project-ci-summary-source-review.md",
        "implementation_gate": "project-ci-summary-implementation-gate",
        "source_review_bundle": "project-ci-summary-source-review-bundle",
    },
]
REQUIRED_INVENTORY_PHRASES = [
    "Status: approved read-only metadata inventory",
    "git.show.commit_metadata",
    "git.show.ref_summary",
    "git.show.tag_metadata",
    "project.dependency.summary",
    "project.manifest.summary",
    "project.structure.summary",
    "project.test.summary",
    "project.docs.summary",
    "project.language.summary",
    "project.config.summary",
    "project.ci.summary",
    "tool count `21`",
    "no shell",
    "no broad filesystem writes",
    "no arbitrary Git command execution",
    "no package-manager execution",
    "Broader capability expansion remains blocked",
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
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])

    inventory_doc = repo_root / INVENTORY_DOC.relative_to(ROOT)
    if not inventory_doc.exists():
        failures.append("read-only capability inventory doc is missing")
    else:
        text = inventory_doc.read_text(encoding="utf-8")
        for phrase in REQUIRED_INVENTORY_PHRASES:
            if phrase not in text:
                failures.append(f"inventory doc is missing phrase: {phrase}")

    implemented_git_show_tools = sorted(_implemented_read_only_metadata_tools(repo_root))
    approved_names = sorted(str(capability["tool_name"]) for capability in APPROVED_CAPABILITIES)
    if implemented_git_show_tools != approved_names:
        failures.append(
            "implemented read-only metadata inventory drifted: "
            f"expected {approved_names}, found {implemented_git_show_tools}"
        )

    capability_reports = []
    for capability in APPROVED_CAPABILITIES:
        failures.extend(
            _validate_capability(
                repo_root=repo_root,
                capability=capability,
                makefile=makefile,
                release_check_body=release_check_body,
                docs_site=docs_site,
            )
        )
        capability_reports.append(
            {
                "tool_name": capability["tool_name"],
                "manifest": capability["manifest"],
                "implementation_gate": capability["implementation_gate"],
                "source_review_bundle": capability["source_review_bundle"],
            }
        )

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "capability_count": len(APPROVED_CAPABILITIES),
        "capabilities": capability_reports,
        "tool_count": tool_surface.get("tool_count"),
        "new_power_classes_allowed": False,
    }


def _implemented_read_only_metadata_tools(repo_root: Path) -> list[str]:
    names: list[str] = []
    for manifest_path in sorted((repo_root / "tool-manifests").glob("*.yaml")):
        loaded = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            continue
        name = loaded.get("name")
        if isinstance(name, str) and (
            name.startswith("git.show.")
            or name
            in {
                "project.dependency.summary",
                "project.manifest.summary",
                "project.structure.summary",
                "project.test.summary",
                "project.docs.summary",
                "project.language.summary",
                "project.config.summary",
                "project.ci.summary",
            }
        ):
            names.append(name)
    return names


def _validate_capability(
    *,
    repo_root: Path,
    capability: dict[str, str],
    makefile: str,
    release_check_body: str,
    docs_site: str,
) -> list[str]:
    failures: list[str] = []
    tool_name = capability["tool_name"]
    manifest_path = repo_root / capability["manifest"]
    if not manifest_path.exists():
        failures.append(f"{tool_name}: manifest is missing")
    else:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            failures.append(f"{tool_name}: manifest is invalid")
        else:
            if manifest.get("name") != tool_name:
                failures.append(f"{tool_name}: manifest name drifted")
            if manifest.get("risk") != "read":
                failures.append(f"{tool_name}: manifest risk must stay read")
            expected_category = "project" if tool_name.startswith("project.") else "git"
            if manifest.get("category") != expected_category:
                failures.append(f"{tool_name}: manifest category must stay {expected_category}")
            if not bool((manifest.get("mcp") or {}).get("exposed")):
                failures.append(f"{tool_name}: manifest MCP exposure must be explicit")
            schema = manifest.get("input_schema")
            if not isinstance(schema, dict) or schema.get("additionalProperties") is not False:
                failures.append(f"{tool_name}: manifest must reject unknown top-level fields")

    for key in ("proposal", "implementation_plan", "implementation", "source_review"):
        rel_path = capability[key]
        path = repo_root / rel_path
        if not path.exists():
            failures.append(f"{tool_name}: {rel_path} is missing")
            continue
        if rel_path not in review_docs.REVIEW_DOCS:
            failures.append(f"{tool_name}: {rel_path} is missing from review docs")
        if rel_path not in docs_site:
            failures.append(f"{tool_name}: {rel_path} is missing from docs-site inputs")

    for key in ("implementation_gate", "source_review_bundle"):
        target = capability[key]
        if f"{target}:" not in makefile:
            failures.append(f"{tool_name}: Make target is missing: {target}")
    if capability["implementation_gate"] not in release_check_body:
        failures.append(f"{tool_name}: implementation gate is missing from release-check")
    return failures


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin read-only capability inventory gate",
        f"valid: {str(report['valid']).lower()}",
        f"capability_count: {report['capability_count']}",
        f"tool_count: {report.get('tool_count', 'unknown')}",
        "new_power_classes_allowed: false",
    ]
    for capability in report["capabilities"]:
        lines.append(f"- {capability['tool_name']}")
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

"""Fail if v0.5 review work expands Ithildin's governed tool powers."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.capability_expansion_gate import EXPECTED_DEFERRED_BOUNDARIES
from scripts.tool_surface_invariant_gate import EXPECTED_TOOL_NAMES, EXPECTED_TOOL_RISKS

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_CATEGORIES = {"filesystem", "git", "network", "project"}
ALLOWED_WRITE_TOOLS = {"fs.patch.apply", "fs.patch.propose"}
ALLOWED_NETWORK_TOOLS = {"http.fetch"}
ALLOWED_NEW_READ_TOOLS = {
    "git.show.commit_metadata",
    "git.show.ref_summary",
    "project.dependency.summary",
    "project.manifest.summary",
    "project.structure.summary",
    "project.test.summary",
    "project.docs.summary",
    "project.language.summary",
}
FORBIDDEN_TOOL_PREFIXES = (
    "shell.",
    "docker.",
    "k8s.",
    "kubernetes.",
    "browser.",
    "secret.",
    "secrets.",
)
FORBIDDEN_TOOL_NAME_PARTS = (
    ".exec",
    ".run",
    ".delete",
    ".move",
    ".chmod",
    ".archive",
    ".extract",
    ".upload",
    ".post",
)
FORBIDDEN_SCHEMA_FIELDS = {
    "body",
    "headers",
    "method",
    "cookie",
    "cookies",
    "command",
    "args",
    "argv",
    "script",
    "image",
    "container",
    "namespace",
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
    manifest = json.loads(
        (repo_root / "docs/codex/v0.5-milestone-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    manifest_paths = sorted((repo_root / "tool-manifests").glob("*.y*ml"))
    failures: list[str] = []
    reviewed_tools: list[dict[str, Any]] = []

    if manifest.get("deferred_boundaries") != EXPECTED_DEFERRED_BOUNDARIES:
        failures.append("v0.5 deferred-boundary list changed")
    if manifest.get("runtime_boundary") != "v0.1 local-preview":
        failures.append("runtime boundary changed")

    names: list[str] = []
    for path in manifest_paths:
        tool_manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(tool_manifest, dict):
            failures.append(f"{path.relative_to(repo_root).as_posix()} is not a YAML object")
            continue
        name = str(tool_manifest.get("name", ""))
        risk = str(tool_manifest.get("risk", ""))
        category = str(tool_manifest.get("category", ""))
        names.append(name)
        reviewed_tools.append(
            {
                "path": path.relative_to(repo_root).as_posix(),
                "name": name,
                "risk": risk,
                "category": category,
            }
        )
        failures.extend(_validate_manifest(tool_manifest, repo_root, path))

    if names != EXPECTED_TOOL_NAMES:
        failures.append("governed tool names changed outside the approved v0.9 read capability")
    if len(names) != len(EXPECTED_TOOL_NAMES):
        failures.append("governed tool count changed outside the approved v0.9 read capability")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "tool_count": len(names),
        "tool_names": names,
        "reviewed_tools": reviewed_tools,
        "deferred_boundaries_unchanged": (
            manifest.get("deferred_boundaries") == EXPECTED_DEFERRED_BOUNDARIES
        ),
        "approved_new_read_tools": sorted(ALLOWED_NEW_READ_TOOLS),
        "new_power_classes_allowed": False,
    }


def _validate_manifest(
    manifest: dict[str, Any],
    repo_root: Path,
    path: Path,
) -> list[str]:
    failures: list[str] = []
    rel_path = path.relative_to(repo_root).as_posix()
    name = str(manifest.get("name", ""))
    risk = str(manifest.get("risk", ""))
    category = str(manifest.get("category", ""))
    if any(name.startswith(prefix) for prefix in FORBIDDEN_TOOL_PREFIXES):
        failures.append(f"{name} uses forbidden tool prefix")
    if any(part in name for part in FORBIDDEN_TOOL_NAME_PARTS):
        failures.append(f"{name} uses forbidden broad-power name marker")
    if category not in ALLOWED_CATEGORIES:
        failures.append(f"{name} uses unapproved category {category!r}")
    expected_risk = EXPECTED_TOOL_RISKS.get(name)
    if expected_risk is None:
        failures.append(f"{rel_path} contains unexpected tool {name!r}")
    elif risk != expected_risk:
        failures.append(f"{name} risk changed from {expected_risk!r} to {risk!r}")
    if risk == "write" and name not in ALLOWED_WRITE_TOOLS:
        failures.append(f"{name} is an unapproved write tool")
    if risk == "network" and name not in ALLOWED_NETWORK_TOOLS:
        failures.append(f"{name} is an unapproved network tool")
    failures.extend(_validate_schema_fields(name, manifest))
    return failures


def _validate_schema_fields(name: str, manifest: dict[str, Any]) -> list[str]:
    schema = manifest.get("input_schema")
    if not isinstance(schema, dict):
        return [f"{name} has invalid input_schema"]
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return [f"{name} has invalid input_schema.properties"]
    forbidden = sorted(set(properties) & FORBIDDEN_SCHEMA_FIELDS)
    if forbidden:
        return [f"{name} exposes forbidden schema fields: {', '.join(forbidden)}"]
    if name == "http.fetch" and sorted(properties) != ["url"]:
        return ["http.fetch must stay URL-only"]
    if name == "git.show.ref_summary":
        failures = _validate_git_ref_summary_schema(properties)
        if failures:
            return failures
    if name == "project.manifest.summary":
        failures = _validate_project_manifest_summary_schema(properties)
        if failures:
            return failures
    if name == "project.dependency.summary":
        failures = _validate_project_dependency_summary_schema(properties)
        if failures:
            return failures
    if name == "project.test.summary":
        failures = _validate_project_test_summary_schema(properties)
        if failures:
            return failures
    if name == "project.docs.summary":
        failures = _validate_project_docs_summary_schema(properties)
        if failures:
            return failures
    if name == "project.language.summary":
        failures = _validate_project_language_summary_schema(properties)
        if failures:
            return failures
    return []


def _validate_git_ref_summary_schema(properties: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if sorted(properties) != ["limit", "selector", "workspace_id"]:
        failures.append("git.show.ref_summary must stay selector/limit/workspace-only")
        return failures
    selector = properties.get("selector")
    if not isinstance(selector, dict):
        return ["git.show.ref_summary selector schema is invalid"]
    if selector.get("additionalProperties") is not False:
        failures.append("git.show.ref_summary selector must reject unknown fields")
    if selector.get("required") != ["kind"]:
        failures.append("git.show.ref_summary selector required fields drifted")
    selector_properties = selector.get("properties")
    if not isinstance(selector_properties, dict):
        return failures + ["git.show.ref_summary selector properties are invalid"]
    kind = selector_properties.get("kind")
    if not isinstance(kind, dict) or sorted(kind.get("enum", [])) != [
        "all_local",
        "branch",
        "tag",
    ]:
        failures.append("git.show.ref_summary selector kind enum drifted")
    forbidden_nested = sorted(set(selector_properties) & FORBIDDEN_SCHEMA_FIELDS)
    if forbidden_nested:
        failures.append(
            "git.show.ref_summary exposes forbidden selector fields: "
            + ", ".join(forbidden_nested)
        )
    return failures


def _validate_project_manifest_summary_schema(properties: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if sorted(properties) != ["limit", "manifest_kinds", "root", "workspace_id"]:
        failures.append("project.manifest.summary must stay workspace/root/kinds/limit-only")
        return failures
    manifest_kinds = properties.get("manifest_kinds")
    if not isinstance(manifest_kinds, dict):
        return ["project.manifest.summary manifest_kinds schema is invalid"]
    items = manifest_kinds.get("items")
    if not isinstance(items, dict):
        return ["project.manifest.summary manifest_kinds items schema is invalid"]
    expected = [
        "Cargo.toml",
        "Gemfile",
        "build.gradle",
        "composer.json",
        "go.mod",
        "package.json",
        "pom.xml",
        "pyproject.toml",
        "requirements.txt",
    ]
    if sorted(items.get("enum", [])) != expected:
        failures.append("project.manifest.summary manifest kind allowlist drifted")
    limit = properties.get("limit")
    if not isinstance(limit, dict) or limit.get("maximum") != 20:
        failures.append("project.manifest.summary limit must stay bounded to 20")
    return failures


def _validate_project_dependency_summary_schema(properties: dict[str, Any]) -> list[str]:
    return [
        failure.replace("project.manifest.summary", "project.dependency.summary")
        for failure in _validate_project_manifest_summary_schema(properties)
    ]


def _validate_project_test_summary_schema(properties: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if sorted(properties) != ["include_categories", "limit", "max_depth", "root", "workspace_id"]:
        failures.append("project.test.summary must stay workspace/root/categories/depth/limit-only")
        return failures
    max_depth = properties.get("max_depth")
    if not isinstance(max_depth, dict) or max_depth.get("maximum") != 5:
        failures.append("project.test.summary max_depth must stay bounded to 5")
    limit = properties.get("limit")
    if not isinstance(limit, dict) or limit.get("maximum") != 300:
        failures.append("project.test.summary limit must stay bounded to 300")
    categories = properties.get("include_categories")
    if not isinstance(categories, dict):
        return failures + ["project.test.summary include_categories schema is invalid"]
    items = categories.get("items")
    expected = [
        "framework_hints",
        "language_family_counts",
        "skipped_counts",
        "test_location_counts",
    ]
    if not isinstance(items, dict) or sorted(items.get("enum", [])) != expected:
        failures.append("project.test.summary include_categories allowlist drifted")
    return failures


def _validate_project_docs_summary_schema(properties: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if sorted(properties) != ["include_categories", "limit", "max_depth", "root", "workspace_id"]:
        failures.append("project.docs.summary must stay workspace/root/categories/depth/limit-only")
        return failures
    max_depth = properties.get("max_depth")
    if not isinstance(max_depth, dict) or max_depth.get("maximum") != 5:
        failures.append("project.docs.summary max_depth must stay bounded to 5")
    limit = properties.get("limit")
    if not isinstance(limit, dict) or limit.get("maximum") != 300:
        failures.append("project.docs.summary limit must stay bounded to 300")
    categories = properties.get("include_categories")
    if not isinstance(categories, dict):
        return failures + ["project.docs.summary include_categories schema is invalid"]
    items = categories.get("items")
    expected = [
        "documentation_location_counts",
        "documentation_type_counts",
        "language_family_counts",
        "skipped_counts",
    ]
    if not isinstance(items, dict) or sorted(items.get("enum", [])) != expected:
        failures.append("project.docs.summary include_categories allowlist drifted")
    return failures


def _validate_project_language_summary_schema(properties: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if sorted(properties) != ["include_categories", "limit", "max_depth", "root", "workspace_id"]:
        failures.append(
            "project.language.summary must stay workspace/root/categories/depth/limit-only"
        )
        return failures
    max_depth = properties.get("max_depth")
    if not isinstance(max_depth, dict) or max_depth.get("maximum") != 5:
        failures.append("project.language.summary max_depth must stay bounded to 5")
    limit = properties.get("limit")
    if not isinstance(limit, dict) or limit.get("maximum") != 300:
        failures.append("project.language.summary limit must stay bounded to 300")
    categories = properties.get("include_categories")
    if not isinstance(categories, dict):
        return failures + ["project.language.summary include_categories schema is invalid"]
    items = categories.get("items")
    expected = [
        "extension_family_counts",
        "language_family_counts",
        "skipped_counts",
        "source_location_counts",
    ]
    if not isinstance(items, dict) or sorted(items.get("enum", [])) != expected:
        failures.append("project.language.summary include_categories allowlist drifted")
    return failures


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin no-new-powers guardrail v2",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report['tool_count']}",
        f"deferred_boundaries_unchanged: {str(report['deferred_boundaries_unchanged']).lower()}",
        "new_power_classes_allowed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

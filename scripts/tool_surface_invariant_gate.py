"""Validate that Ithildin's governed tool surface has not drifted."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TOOL_NAMES = [
    "fs.list",
    "fs.patch.apply",
    "fs.patch.propose",
    "fs.read",
    "fs.search",
    "fs.stat",
    "git.diff",
    "git.log",
    "git.show.commit_metadata",
    "git.show.ref_summary",
    "git.show.tag_metadata",
    "git.status",
    "http.fetch",
    "project.config.summary",
    "project.dependency.summary",
    "project.docs.summary",
    "project.language.summary",
    "project.manifest.summary",
    "project.structure.summary",
    "project.test.summary",
]
EXPECTED_TOOL_RISKS = {
    "fs.list": "read",
    "fs.patch.apply": "write",
    "fs.patch.propose": "write-proposal",
    "fs.read": "read",
    "fs.search": "read",
    "fs.stat": "read",
    "git.diff": "read",
    "git.log": "read",
    "git.show.commit_metadata": "read",
    "git.show.ref_summary": "read",
    "git.show.tag_metadata": "read",
    "git.status": "read",
    "http.fetch": "network",
    "project.config.summary": "read",
    "project.dependency.summary": "read",
    "project.docs.summary": "read",
    "project.language.summary": "read",
    "project.manifest.summary": "read",
    "project.structure.summary": "read",
    "project.test.summary": "read",
}
FORBIDDEN_MANIFEST_MARKERS = [
    "shell",
    "docker",
    "kubernetes",
    "browser",
    "delete",
    "chmod",
    "archive",
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
    lock = json.loads((repo_root / "tool-manifests.lock.json").read_text(encoding="utf-8"))
    lock_names = [record["name"] for record in lock["manifests"]]
    manifest_paths = sorted((repo_root / "tool-manifests").glob("*.y*ml"))
    lock_paths = sorted(record["path"] for record in lock["manifests"])
    actual_paths = sorted(path.relative_to(repo_root).as_posix() for path in manifest_paths)

    failures: list[str] = []
    if lock_names != EXPECTED_TOOL_NAMES:
        failures.append("tool-manifests.lock.json tool list drifted")
    if lock_paths != actual_paths:
        failures.append("tool-manifests.lock.json manifest paths drifted")
    if len(manifest_paths) != len(EXPECTED_TOOL_NAMES):
        failures.append("tool manifest file count drifted")

    manifest_summaries: list[dict[str, Any]] = []
    marker_hits: list[dict[str, str]] = []
    for path in manifest_paths:
        text = path.read_text(encoding="utf-8").lower()
        for marker in FORBIDDEN_MANIFEST_MARKERS:
            if marker in text:
                marker_hits.append(
                    {"path": path.relative_to(repo_root).as_posix(), "marker": marker}
                )
        manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            failures.append(f"{path.relative_to(repo_root).as_posix()} is not a YAML object")
            continue
        manifest_name = manifest.get("name")
        manifest_risk = manifest.get("risk")
        manifest_summaries.append(
            {
                "path": path.relative_to(repo_root).as_posix(),
                "name": manifest_name,
                "risk": manifest_risk,
                "category": manifest.get("category"),
                "mcp_exposed": bool((manifest.get("mcp") or {}).get("exposed")),
            }
        )
        expected_risk = EXPECTED_TOOL_RISKS.get(str(manifest_name))
        if expected_risk is None:
            failures.append(f"unexpected manifest tool name {manifest_name!r}")
        elif manifest_risk != expected_risk:
            failures.append(
                f"{manifest_name} risk drifted from {expected_risk!r} to {manifest_risk!r}"
            )
        if manifest_name == "http.fetch":
            failures.extend(_check_http_fetch_schema(manifest))
        if manifest_name == "git.show.commit_metadata":
            failures.extend(_check_git_commit_metadata_schema(manifest))
        if manifest_name == "git.show.ref_summary":
            failures.extend(_check_git_ref_summary_schema(manifest))
        if manifest_name == "git.show.tag_metadata":
            failures.extend(_check_git_tag_metadata_schema(manifest))
        if manifest_name == "project.manifest.summary":
            failures.extend(_check_project_manifest_summary_schema(manifest))
        if manifest_name == "project.dependency.summary":
            failures.extend(_check_project_dependency_summary_schema(manifest))
        if manifest_name == "project.structure.summary":
            failures.extend(_check_project_structure_summary_schema(manifest))
        if manifest_name == "project.test.summary":
            failures.extend(_check_project_test_summary_schema(manifest))
        if manifest_name == "project.language.summary":
            failures.extend(_check_project_language_summary_schema(manifest))
        if manifest_name == "project.config.summary":
            failures.extend(_check_project_config_summary_schema(manifest))
    if marker_hits:
        failures.append("manifest text references deferred or broad tool-power markers")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "tool_count": len(lock_names),
        "tool_names": lock_names,
        "manifest_file_count": len(manifest_paths),
        "manifest_summaries": manifest_summaries,
        "forbidden_marker_hits": marker_hits,
    }


def _check_http_fetch_schema(manifest: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    schema = manifest.get("input_schema")
    if not isinstance(schema, dict):
        return ["http.fetch input_schema is missing or invalid"]

    required = schema.get("required")
    properties = schema.get("properties")
    if required != ["url"]:
        failures.append("http.fetch required fields drifted")
    if not isinstance(properties, dict) or sorted(properties) != ["url"]:
        failures.append("http.fetch properties drifted beyond url")
    if schema.get("additionalProperties") is not False:
        failures.append("http.fetch must keep additionalProperties: false")

    forbidden_http_inputs = {"headers", "body", "method", "cookies", "cookie"}
    exposed = set(properties or {}) | set(required or [])
    drift = sorted(exposed & forbidden_http_inputs)
    if drift:
        failures.append(f"http.fetch exposes forbidden caller-controlled fields: {drift}")
    return failures


def _check_git_commit_metadata_schema(manifest: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    schema = manifest.get("input_schema")
    if not isinstance(schema, dict):
        return ["git.show.commit_metadata input_schema is missing or invalid"]
    if schema.get("additionalProperties") is not False:
        failures.append("git.show.commit_metadata must keep additionalProperties: false")
    required = schema.get("required")
    if required != ["ref"]:
        failures.append("git.show.commit_metadata required fields drifted")
    properties = schema.get("properties")
    allowed = ["include_body", "include_diffstat", "include_emails", "ref", "workspace_id"]
    if not isinstance(properties, dict) or sorted(properties) != allowed:
        failures.append("git.show.commit_metadata properties drifted")
        return failures
    ref_schema = properties.get("ref")
    if not isinstance(ref_schema, dict):
        return failures + ["git.show.commit_metadata ref schema is invalid"]
    if ref_schema.get("additionalProperties") is not False:
        failures.append("git.show.commit_metadata ref must keep additionalProperties: false")
    if ref_schema.get("required") != ["kind", "value"]:
        failures.append("git.show.commit_metadata ref required fields drifted")
    ref_properties = ref_schema.get("properties")
    if not isinstance(ref_properties, dict):
        failures.append("git.show.commit_metadata ref properties are invalid")
        return failures
    kind = ref_properties.get("kind")
    if not isinstance(kind, dict) or sorted(kind.get("enum", [])) != [
        "branch",
        "object_id",
        "tag",
    ]:
        failures.append("git.show.commit_metadata ref kind enum drifted")
    forbidden_inputs = {
        "argv",
        "args",
        "command",
        "format",
        "pathspec",
        "remote",
        "checkout",
        "diff",
        "headers",
        "body",
    }
    exposed = set(properties) | set(ref_properties)
    drift = sorted(exposed & forbidden_inputs)
    if drift:
        failures.append(
            "git.show.commit_metadata exposes forbidden caller-controlled fields: "
            + ", ".join(drift)
        )
    return failures


def _check_git_ref_summary_schema(manifest: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    schema = manifest.get("input_schema")
    if not isinstance(schema, dict):
        return ["git.show.ref_summary input_schema is missing or invalid"]
    if schema.get("additionalProperties") is not False:
        failures.append("git.show.ref_summary must keep additionalProperties: false")
    required = schema.get("required")
    if required != ["selector"]:
        failures.append("git.show.ref_summary required fields drifted")
    properties = schema.get("properties")
    allowed = ["limit", "selector", "workspace_id"]
    if not isinstance(properties, dict) or sorted(properties) != allowed:
        failures.append("git.show.ref_summary properties drifted")
        return failures
    selector_schema = properties.get("selector")
    if not isinstance(selector_schema, dict):
        return failures + ["git.show.ref_summary selector schema is invalid"]
    if selector_schema.get("additionalProperties") is not False:
        failures.append("git.show.ref_summary selector must keep additionalProperties: false")
    if selector_schema.get("required") != ["kind"]:
        failures.append("git.show.ref_summary selector required fields drifted")
    selector_properties = selector_schema.get("properties")
    if not isinstance(selector_properties, dict):
        failures.append("git.show.ref_summary selector properties are invalid")
        return failures
    kind = selector_properties.get("kind")
    if not isinstance(kind, dict) or sorted(kind.get("enum", [])) != [
        "all_local",
        "branch",
        "tag",
    ]:
        failures.append("git.show.ref_summary selector kind enum drifted")
    limit = properties.get("limit")
    if not isinstance(limit, dict) or limit.get("minimum") != 1 or limit.get("maximum") != 200:
        failures.append("git.show.ref_summary limit bounds drifted")
    forbidden_inputs = {
        "argv",
        "args",
        "command",
        "format",
        "pathspec",
        "remote",
        "checkout",
        "diff",
        "headers",
        "body",
        "include_names",
        "include_current_branch",
        "ref",
        "refspec",
    }
    exposed = set(properties) | set(selector_properties)
    drift = sorted(exposed & forbidden_inputs)
    if drift:
        failures.append(
            "git.show.ref_summary exposes forbidden caller-controlled fields: "
            + ", ".join(drift)
        )
    return failures


def _check_git_tag_metadata_schema(manifest: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    schema = manifest.get("input_schema")
    if not isinstance(schema, dict):
        return ["git.show.tag_metadata input_schema is missing or invalid"]
    if schema.get("additionalProperties") is not False:
        failures.append("git.show.tag_metadata must keep additionalProperties: false")
    required = schema.get("required")
    if required != ["selector"]:
        failures.append("git.show.tag_metadata required fields drifted")
    properties = schema.get("properties")
    allowed = ["limit", "selector", "workspace_id"]
    if not isinstance(properties, dict) or sorted(properties) != allowed:
        failures.append("git.show.tag_metadata properties drifted")
        return failures
    selector_schema = properties.get("selector")
    if not isinstance(selector_schema, dict):
        return failures + ["git.show.tag_metadata selector schema is invalid"]
    if selector_schema.get("additionalProperties") is not False:
        failures.append("git.show.tag_metadata selector must keep additionalProperties: false")
    if selector_schema.get("required") != ["kind"]:
        failures.append("git.show.tag_metadata selector required fields drifted")
    selector_properties = selector_schema.get("properties")
    if not isinstance(selector_properties, dict):
        failures.append("git.show.tag_metadata selector properties are invalid")
        return failures
    kind = selector_properties.get("kind")
    if not isinstance(kind, dict) or sorted(kind.get("enum", [])) != ["all_local_tags"]:
        failures.append("git.show.tag_metadata selector kind enum drifted")
    limit = properties.get("limit")
    if not isinstance(limit, dict) or limit.get("minimum") != 1 or limit.get("maximum") != 200:
        failures.append("git.show.tag_metadata limit bounds drifted")
    forbidden_inputs = {
        "argv",
        "args",
        "command",
        "format",
        "pathspec",
        "remote",
        "checkout",
        "diff",
        "headers",
        "body",
        "include_names",
        "include_messages",
        "include_signatures",
        "ref",
        "refspec",
    }
    exposed = set(properties) | set(selector_properties)
    drift = sorted(exposed & forbidden_inputs)
    if drift:
        failures.append(
            "git.show.tag_metadata exposes forbidden caller-controlled fields: "
            + ", ".join(drift)
        )
    return failures


def _check_project_manifest_summary_schema(manifest: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    schema = manifest.get("input_schema")
    if not isinstance(schema, dict):
        return ["project.manifest.summary input_schema is missing or invalid"]
    if schema.get("additionalProperties") is not False:
        failures.append("project.manifest.summary must keep additionalProperties: false")
    properties = schema.get("properties")
    if not isinstance(properties, dict) or sorted(properties) != [
        "limit",
        "manifest_kinds",
        "root",
        "workspace_id",
    ]:
        failures.append("project.manifest.summary properties drifted")
        return failures
    kinds = properties.get("manifest_kinds")
    if not isinstance(kinds, dict):
        failures.append("project.manifest.summary manifest_kinds schema is invalid")
    else:
        items = kinds.get("items")
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
        if not isinstance(items, dict) or sorted(items.get("enum", [])) != expected:
            failures.append("project.manifest.summary manifest kind allowlist drifted")
        if kinds.get("uniqueItems") is not True:
            failures.append("project.manifest.summary manifest_kinds must stay unique")
    limit = properties.get("limit")
    if not isinstance(limit, dict) or limit.get("minimum") != 1 or limit.get("maximum") != 20:
        failures.append("project.manifest.summary limit bounds drifted")
    forbidden_inputs = {
        "argv",
        "args",
        "command",
        "glob",
        "recursive",
        "registry_url",
        "include_file_contents",
        "include_dependency_names",
        "include_script_values",
        "headers",
        "body",
    }
    exposed = set(properties)
    drift = sorted(exposed & forbidden_inputs)
    if drift:
        failures.append(
            "project.manifest.summary exposes forbidden caller-controlled fields: "
            + ", ".join(drift)
        )
    return failures


def _check_project_dependency_summary_schema(manifest: dict[str, Any]) -> list[str]:
    failures = _check_project_manifest_summary_schema(manifest)
    return [
        failure.replace("project.manifest.summary", "project.dependency.summary")
        for failure in failures
    ]


def _check_project_structure_summary_schema(manifest: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    schema = manifest.get("input_schema")
    if not isinstance(schema, dict):
        return ["project.structure.summary input_schema is missing or invalid"]
    if schema.get("additionalProperties") is not False:
        failures.append("project.structure.summary must keep additionalProperties: false")
    properties = schema.get("properties")
    expected_properties = ["include_categories", "limit", "max_depth", "root", "workspace_id"]
    if not isinstance(properties, dict) or sorted(properties) != expected_properties:
        failures.append("project.structure.summary properties drifted")
        return failures
    max_depth = properties.get("max_depth")
    if (
        not isinstance(max_depth, dict)
        or max_depth.get("minimum") != 0
        or max_depth.get("maximum") != 4
    ):
        failures.append("project.structure.summary max_depth bounds drifted")
    limit = properties.get("limit")
    if not isinstance(limit, dict) or limit.get("minimum") != 1 or limit.get("maximum") != 250:
        failures.append("project.structure.summary limit bounds drifted")
    categories = properties.get("include_categories")
    expected_categories = ["directory_categories", "file_kinds", "skipped_counts"]
    if not isinstance(categories, dict):
        failures.append("project.structure.summary include_categories schema is invalid")
    else:
        items = categories.get("items")
        if not isinstance(items, dict) or sorted(items.get("enum", [])) != expected_categories:
            failures.append("project.structure.summary include_categories allowlist drifted")
        if categories.get("uniqueItems") is not True:
            failures.append("project.structure.summary include_categories must stay unique")
    forbidden_inputs = {
        "argv",
        "args",
        "command",
        "glob",
        "regex",
        "recursive",
        "registry_url",
        "include_file_contents",
        "include_file_names",
        "include_paths",
        "include_dependency_names",
        "include_package_names",
        "include_script_values",
        "headers",
        "body",
    }
    drift = sorted(set(properties) & forbidden_inputs)
    if drift:
        failures.append(
            "project.structure.summary exposes forbidden caller-controlled fields: "
            + ", ".join(drift)
        )
    return failures


def _check_project_test_summary_schema(manifest: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    schema = manifest.get("input_schema")
    if not isinstance(schema, dict):
        return ["project.test.summary input_schema is missing or invalid"]
    if schema.get("additionalProperties") is not False:
        failures.append("project.test.summary must keep additionalProperties: false")
    properties = schema.get("properties")
    expected_properties = ["include_categories", "limit", "max_depth", "root", "workspace_id"]
    if not isinstance(properties, dict) or sorted(properties) != expected_properties:
        failures.append("project.test.summary properties drifted")
        return failures
    max_depth = properties.get("max_depth")
    if (
        not isinstance(max_depth, dict)
        or max_depth.get("minimum") != 0
        or max_depth.get("maximum") != 5
    ):
        failures.append("project.test.summary max_depth bounds drifted")
    limit = properties.get("limit")
    if not isinstance(limit, dict) or limit.get("minimum") != 1 or limit.get("maximum") != 300:
        failures.append("project.test.summary limit bounds drifted")
    categories = properties.get("include_categories")
    expected_categories = [
        "framework_hints",
        "language_family_counts",
        "skipped_counts",
        "test_location_counts",
    ]
    if not isinstance(categories, dict):
        failures.append("project.test.summary include_categories schema is invalid")
    else:
        items = categories.get("items")
        if not isinstance(items, dict) or sorted(items.get("enum", [])) != expected_categories:
            failures.append("project.test.summary include_categories allowlist drifted")
        if categories.get("uniqueItems") is not True:
            failures.append("project.test.summary include_categories must stay unique")
    forbidden_inputs = {
        "argv",
        "args",
        "command",
        "glob",
        "regex",
        "recursive",
        "registry_url",
        "include_file_contents",
        "include_file_names",
        "include_paths",
        "include_test_names",
        "include_dependency_names",
        "include_package_names",
        "include_script_values",
        "include_coverage",
        "execute_tests",
        "headers",
        "body",
    }
    drift = sorted(set(properties) & forbidden_inputs)
    if drift:
        failures.append(
            "project.test.summary exposes forbidden caller-controlled fields: "
            + ", ".join(drift)
        )
    return failures


def _check_project_language_summary_schema(manifest: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    schema = manifest.get("input_schema")
    if not isinstance(schema, dict):
        return ["project.language.summary input_schema is missing or invalid"]
    if schema.get("additionalProperties") is not False:
        failures.append("project.language.summary must keep additionalProperties: false")
    properties = schema.get("properties")
    expected_properties = ["include_categories", "limit", "max_depth", "root", "workspace_id"]
    if not isinstance(properties, dict) or sorted(properties) != expected_properties:
        failures.append("project.language.summary properties drifted")
        return failures
    max_depth = properties.get("max_depth")
    if (
        not isinstance(max_depth, dict)
        or max_depth.get("minimum") != 0
        or max_depth.get("maximum") != 5
    ):
        failures.append("project.language.summary max_depth bounds drifted")
    limit = properties.get("limit")
    if not isinstance(limit, dict) or limit.get("minimum") != 1 or limit.get("maximum") != 300:
        failures.append("project.language.summary limit bounds drifted")
    categories = properties.get("include_categories")
    expected_categories = [
        "extension_family_counts",
        "language_family_counts",
        "skipped_counts",
        "source_location_counts",
    ]
    if not isinstance(categories, dict):
        failures.append("project.language.summary include_categories schema is invalid")
    else:
        items = categories.get("items")
        if not isinstance(items, dict) or sorted(items.get("enum", [])) != expected_categories:
            failures.append("project.language.summary include_categories allowlist drifted")
        if categories.get("uniqueItems") is not True:
            failures.append("project.language.summary include_categories must stay unique")
    forbidden_inputs = {
        "argv",
        "args",
        "command",
        "glob",
        "regex",
        "recursive",
        "registry_url",
        "include_file_contents",
        "include_file_names",
        "include_paths",
        "include_raw_extensions",
        "include_dependency_names",
        "include_package_names",
        "include_script_values",
        "include_coverage",
        "detect_languages",
        "execute_detector",
        "headers",
        "body",
    }
    drift = sorted(set(properties) & forbidden_inputs)
    if drift:
        failures.append(
            "project.language.summary exposes forbidden caller-controlled fields: "
            + ", ".join(drift)
        )
    return failures


def _check_project_config_summary_schema(manifest: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    schema = manifest.get("input_schema")
    if not isinstance(schema, dict):
        return ["project.config.summary input_schema is missing or invalid"]
    if schema.get("additionalProperties") is not False:
        failures.append("project.config.summary must keep additionalProperties: false")
    properties = schema.get("properties")
    expected_properties = ["include_categories", "limit", "max_depth", "root", "workspace_id"]
    if not isinstance(properties, dict) or sorted(properties) != expected_properties:
        failures.append("project.config.summary properties drifted")
        return failures
    max_depth = properties.get("max_depth")
    if (
        not isinstance(max_depth, dict)
        or max_depth.get("minimum") != 0
        or max_depth.get("maximum") != 5
    ):
        failures.append("project.config.summary max_depth bounds drifted")
    limit = properties.get("limit")
    if not isinstance(limit, dict) or limit.get("minimum") != 1 or limit.get("maximum") != 300:
        failures.append("project.config.summary limit bounds drifted")
    categories = properties.get("include_categories")
    expected_categories = [
        "config_category_counts",
        "config_location_counts",
        "skipped_counts",
    ]
    if not isinstance(categories, dict):
        failures.append("project.config.summary include_categories schema is invalid")
    else:
        items = categories.get("items")
        if not isinstance(items, dict) or sorted(items.get("enum", [])) != expected_categories:
            failures.append("project.config.summary include_categories allowlist drifted")
        if categories.get("uniqueItems") is not True:
            failures.append("project.config.summary include_categories must stay unique")
    forbidden_inputs = {
        "argv",
        "args",
        "command",
        "glob",
        "regex",
        "recursive",
        "registry_url",
        "include_file_contents",
        "include_file_names",
        "include_paths",
        "include_config_file_names",
        "include_config_contents",
        "include_config_values",
        "include_dependency_names",
        "include_package_names",
        "include_script_names",
        "include_script_values",
        "include_environment",
        "parse_config",
        "execute_parser",
        "headers",
        "body",
    }
    drift = sorted(set(properties) & forbidden_inputs)
    if drift:
        failures.append(
            "project.config.summary exposes forbidden caller-controlled fields: "
            + ", ".join(drift)
        )
    return failures


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin tool-surface invariant gate",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report['tool_count']}",
        f"manifest_file_count: {report['manifest_file_count']}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

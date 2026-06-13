"""Validate the approved git.show.tag_metadata implementation boundary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import no_new_powers_guardrail, tool_surface_invariant_gate

ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION_DOC = ROOT / "docs/codex/v0.9-git-tag-metadata-implementation.md"
MANIFEST_PATH = ROOT / "tool-manifests/git-show-tag-metadata.yaml"
READ_TOOLS_PATH = ROOT / "apps/api/src/ithildin_api/read_tools.py"
TOOL_CALLS_PATH = ROOT / "apps/api/src/ithildin_api/tool_calls.py"
REQUIRED_DOC_PHRASES = [
    "git.show.tag_metadata",
    "approved v0.9 implementation boundary",
    "read-only Git tag metadata",
    "no shell",
    "no caller-supplied Git format strings",
    "no raw tag names",
    "no stable tag-name hashes",
    "no tag messages",
    "no signatures",
    "no remotes",
    "no file contents",
    "fixed argv",
    "make git-tag-metadata-implementation-gate",
]
REQUIRED_READ_TOOLS_SNIPPETS = [
    "def tag_metadata(self, arguments: JsonObject) -> JsonObject:",
    "_validate_tag_metadata_arguments(arguments)",
    '"for-each-ref",',
    '"--sort=refname",',
    "--format=%(refname)%00%(objectname)%00%(objecttype)%00",
    "refs/tags",
    "_parse_tag_metadata_output(output.text)",
    '"tag_id": f"tag_{len(tags) + 1:04d}"',
    '"tag_type": tag_type',
    '"target_object_type": "commit"',
    '"tag_names_included": False',
    '"tag_messages_included": False',
    '"tag_signatures_included": False',
    '"stable_tag_hashes_included": False',
    '"tag_ids_are_response_local": True',
    "_validate_ref_summary_name(tag_name)",
    "seen_casefolded",
    "_ref_summary_resolved_commit(",
    "raise ReadToolError(\"git tag metadata exceeds configured read limit\")",
]
FORBIDDEN_READ_TOOLS_SNIPPETS = [
    "shell=True",
    "subprocess.run(",
    '"tag_name"',
    '"tag_names"',
    '"stable_tag_hash"',
    "sha256_digest(name)",
    "refs/remotes",
    "git show-ref",
]
REQUIRED_TOOL_CALLS_SNIPPETS = [
    "def _read_tool_execution_metadata(tool_name: str, content: JsonObject) -> JsonObject:",
    'if tool_name == "git.show.tag_metadata":',
    '"selector_kind"',
    '"tag_count"',
    '"total_tag_count"',
    '"skipped_non_commit_tag_count"',
    '"truncated"',
    '"tag_names_included"',
    '"tag_messages_included"',
    '"tag_signatures_included"',
    '"stable_tag_hashes_included"',
    '"tag_ids_are_response_local"',
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
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])

    doc_path = repo_root / IMPLEMENTATION_DOC.relative_to(ROOT)
    if not doc_path.exists():
        failures.append("v0.9 git tag metadata implementation doc is missing")
    else:
        lower = doc_path.read_text(encoding="utf-8").lower()
        for phrase in REQUIRED_DOC_PHRASES:
            if phrase.lower() not in lower:
                failures.append(f"implementation doc is missing phrase: {phrase}")

    manifest_path = repo_root / MANIFEST_PATH.relative_to(ROOT)
    if not manifest_path.exists():
        failures.append("git.show.tag_metadata manifest is missing")
        manifest: dict[str, Any] = {}
    else:
        loaded = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        manifest = loaded if isinstance(loaded, dict) else {}
    failures.extend(_validate_manifest(manifest))
    failures.extend(_validate_source_sentinels(repo_root))

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "tool_name": "git.show.tag_metadata",
        "implementation_status": "approved_limited_read_only",
        "tool_count": tool_surface.get("tool_count"),
        "new_power_classes_allowed": False,
        "deferred_boundaries_unchanged": no_new_powers.get("deferred_boundaries_unchanged"),
    }


def _validate_manifest(manifest: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if manifest.get("name") != "git.show.tag_metadata":
        failures.append("manifest name drifted")
    if manifest.get("risk") != "read":
        failures.append("manifest risk must stay read")
    if manifest.get("category") != "git":
        failures.append("manifest category must stay git")
    if not bool((manifest.get("mcp") or {}).get("exposed")):
        failures.append("manifest MCP exposure must be explicit")
    schema = manifest.get("input_schema")
    if not isinstance(schema, dict):
        failures.append("manifest input_schema is invalid")
        return failures
    if schema.get("type") != "object":
        failures.append("manifest input_schema type must stay object")
    if schema.get("additionalProperties") is not False:
        failures.append("manifest must reject additional properties")
    if schema.get("required") != ["selector"]:
        failures.append("manifest required fields drifted")
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        failures.append("manifest input_schema.properties is invalid")
        return failures
    if sorted(properties) != ["limit", "selector", "workspace_id"]:
        failures.append("manifest properties must stay selector, limit, and workspace_id only")
    selector = properties.get("selector")
    if not isinstance(selector, dict):
        failures.append("selector schema is invalid")
        return failures
    if selector.get("type") != "object":
        failures.append("selector schema type must stay object")
    if selector.get("additionalProperties") is not False:
        failures.append("selector must reject additional properties")
    if selector.get("required") != ["kind"]:
        failures.append("selector required fields drifted")
    selector_properties = selector.get("properties")
    if not isinstance(selector_properties, dict):
        failures.append("selector properties are invalid")
        return failures
    kind = selector_properties.get("kind")
    if not isinstance(kind, dict) or kind.get("type") != "string":
        failures.append("selector kind type must stay string")
    if not isinstance(kind, dict) or sorted(kind.get("enum", [])) != ["all_local_tags"]:
        failures.append("selector kind enum drifted")
    limit = properties.get("limit")
    if not isinstance(limit, dict) or limit.get("type") != "integer":
        failures.append("limit type must stay integer")
    if not isinstance(limit, dict) or limit.get("minimum") != 1 or limit.get("maximum") != 200:
        failures.append("limit bounds drifted")
    if not isinstance(limit, dict) or limit.get("default") != 100:
        failures.append("limit default drifted")
    workspace = properties.get("workspace_id")
    if not isinstance(workspace, dict) or workspace.get("type") != "string":
        failures.append("workspace_id type must stay string")
    if not isinstance(workspace, dict) or workspace.get("default") != "default":
        failures.append("workspace_id default drifted")
    exposed = set(properties) | set(selector_properties)
    forbidden = sorted(
        exposed
        & {
            "args",
            "argv",
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
    )
    if forbidden:
        failures.append(f"manifest exposes forbidden fields: {', '.join(forbidden)}")
    return failures


def _validate_source_sentinels(repo_root: Path) -> list[str]:
    failures: list[str] = []
    read_tools_path = repo_root / READ_TOOLS_PATH.relative_to(ROOT)
    tool_calls_path = repo_root / TOOL_CALLS_PATH.relative_to(ROOT)
    if not read_tools_path.exists():
        return ["read_tools.py is missing"]
    if not tool_calls_path.exists():
        return ["tool_calls.py is missing"]
    read_tools = read_tools_path.read_text(encoding="utf-8")
    tool_calls = tool_calls_path.read_text(encoding="utf-8")
    for snippet in REQUIRED_READ_TOOLS_SNIPPETS:
        if snippet not in read_tools:
            failures.append(f"read_tools.py is missing source sentinel: {snippet}")
    for snippet in FORBIDDEN_READ_TOOLS_SNIPPETS:
        if snippet in read_tools:
            failures.append(f"read_tools.py contains forbidden source sentinel: {snippet}")
    for snippet in REQUIRED_TOOL_CALLS_SNIPPETS:
        if snippet not in tool_calls:
            failures.append(f"tool_calls.py is missing source sentinel: {snippet}")
    return failures


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin git.show.tag_metadata implementation gate",
        f"valid: {str(report['valid']).lower()}",
        f"tool_name: {report['tool_name']}",
        f"implementation_status: {report['implementation_status']}",
        f"tool_count: {report['tool_count']}",
        "new_power_classes_allowed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

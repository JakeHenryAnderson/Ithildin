"""Validate the approved git.show.commit_metadata implementation boundary."""

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
IMPLEMENTATION_DOC = ROOT / "docs/codex/v0.9-git-commit-metadata-implementation.md"
MANIFEST_PATH = ROOT / "tool-manifests/git-show-commit-metadata.yaml"
REQUIRED_DOC_PHRASES = [
    "git.show.commit_metadata",
    "approved v0.9 implementation",
    "read-only Git metadata",
    "no shell",
    "no caller-supplied Git format strings",
    "no file contents",
    "no raw diffs",
    "fixed argv",
    "make git-commit-metadata-implementation-gate",
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
        failures.append("v0.9 git commit metadata implementation doc is missing")
    else:
        text = doc_path.read_text(encoding="utf-8")
        lower = text.lower()
        for phrase in REQUIRED_DOC_PHRASES:
            if phrase.lower() not in lower:
                failures.append(f"implementation doc is missing phrase: {phrase}")

    manifest_path = repo_root / MANIFEST_PATH.relative_to(ROOT)
    if not manifest_path.exists():
        failures.append("git.show.commit_metadata manifest is missing")
        manifest: dict[str, Any] = {}
    else:
        loaded = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        manifest = loaded if isinstance(loaded, dict) else {}
    failures.extend(_validate_manifest(manifest))

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "tool_name": "git.show.commit_metadata",
        "implementation_status": "approved_limited_read_only",
        "tool_count": tool_surface.get("tool_count"),
        "new_power_classes_allowed": False,
        "deferred_boundaries_unchanged": no_new_powers.get("deferred_boundaries_unchanged"),
    }


def _validate_manifest(manifest: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if manifest.get("name") != "git.show.commit_metadata":
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
    if schema.get("additionalProperties") is not False:
        failures.append("manifest must reject additional properties")
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        failures.append("manifest input_schema.properties is invalid")
        return failures
    forbidden = sorted(
        set(properties)
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
        }
    )
    if forbidden:
        failures.append(f"manifest exposes forbidden fields: {', '.join(forbidden)}")
    return failures


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin git.show.commit_metadata implementation gate",
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

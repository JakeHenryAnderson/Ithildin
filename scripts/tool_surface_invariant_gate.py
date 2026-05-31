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
    "git.status",
    "http.fetch",
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
    "git.status": "read",
    "http.fetch": "network",
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

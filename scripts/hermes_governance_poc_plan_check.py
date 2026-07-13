"""Validate the governed external-agent Hermes POC planning packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TARGET = "hermes-governance-poc-plan-check"
DOCS = (
    "docs/codex/governed-external-agent-hermes-poc-architecture.md",
    "docs/codex/governed-external-agent-hermes-poc-capability-proposal.md",
    "docs/codex/governed-external-agent-hermes-poc-implementation-plan.md",
    "docs/codex/governed-external-agent-hermes-poc-observed-results.md",
)
SOAK_FIXTURES = tuple(
    f"deploy/hermes-poc/workspace/soak/case-{index:03d}.md" for index in range(1, 26)
)
DEPLOYMENT_FILES = (
    "deploy/hermes-poc/Dockerfile",
    "deploy/hermes-poc/compose.yaml",
    "deploy/hermes-poc/config.yaml",
    "deploy/hermes-poc/workspaces.yaml",
    "deploy/hermes-poc/mission.md",
    "deploy/hermes-poc/workspace/inbox/case-001.md",
    "deploy/hermes-poc/workspace/inbox/case-002-adversarial.md",
    "deploy/hermes-poc/workspace/output/case-001-summary.md",
    "deploy/hermes-poc/README.md",
) + SOAK_FIXTURES
IMAGE_DIGEST = "sha256:6705aac1f41c5faca559858611ce696b760d858b73fa3b51be11599c73ba1ffc"
REQUIRED_PHRASES = (
    "Current governed tool count: `24`.",
    "agent:mcp-local",
    "mcp-stdio",
    IMAGE_DIGEST,
    "capability_expansion_allowed: false",
    "remote MCP",
    "Docker socket",
    "Track A",
    "Track B",
    "replay",
    "restart",
    "synthetic",
    "Command Center",
)
FORBIDDEN_PHRASES = (
    "runtime expansion is approved",
    "remote mcp is approved",
    "mission orchestration is approved",
    "production identity is approved",
    "agent fully non-bypassable: true",
)


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    texts: list[str] = []
    for relative in DOCS:
        path = repo_root / relative
        if not path.is_file():
            failures.append(f"missing POC planning document: {relative}")
            texts.append("")
        else:
            texts.append(path.read_text(encoding="utf-8"))

    deployment_texts: dict[str, str] = {}
    for relative in DEPLOYMENT_FILES:
        path = repo_root / relative
        if not path.is_file():
            failures.append(f"missing POC deployment file: {relative}")
            deployment_texts[relative] = ""
        else:
            deployment_texts[relative] = path.read_text(encoding="utf-8")

    combined = "\n".join(texts)
    lowered = combined.lower()
    for phrase in REQUIRED_PHRASES:
        if phrase not in combined:
            failures.append(f"POC packet is missing required phrase: {phrase}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase in lowered:
            failures.append(f"POC packet contains forbidden approval claim: {phrase}")

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_docs = _read(repo_root / "scripts/review_docs.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if f"release-check: {TARGET}" not in makefile:
        failures.append("POC plan check is missing from release-check")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing the POC plan check command")
    for relative in DOCS:
        if relative not in docs_site:
            failures.append(f"docs site is missing: {relative}")
        if relative not in review_docs:
            failures.append(f"review docs are missing: {relative}")
        if relative not in readme:
            failures.append(f"README is missing: {relative}")
    if "Governed External Agent POC" not in review_index:
        failures.append("review docs index is missing the governed external-agent POC section")

    dockerfile = deployment_texts["deploy/hermes-poc/Dockerfile"]
    compose = deployment_texts["deploy/hermes-poc/compose.yaml"]
    config = deployment_texts["deploy/hermes-poc/config.yaml"]
    mission = deployment_texts["deploy/hermes-poc/mission.md"]
    if f"nousresearch/hermes-agent@{IMAGE_DIGEST}" not in dockerfile:
        failures.append("Hermes POC Dockerfile is not pinned to the reviewed image digest")
    if "/var/run/docker.sock" in compose or "/var/run/docker.sock" in dockerfile:
        failures.append("Hermes POC must not mount the Docker socket")
    if "cap_drop:\n      - ALL" not in compose:
        failures.append("Hermes POC compose file must drop all Linux capabilities")
    if 'user: "10000:10000"' not in compose:
        failures.append("Hermes POC compose file must run as the image's unprivileged account")
    if "/opt/hermes/.venv/bin/hermes" not in compose:
        failures.append("Hermes POC compose file must bypass the root supervisor for one-shot runs")
    if "no-new-privileges:true" not in compose:
        failures.append("Hermes POC compose file must set no-new-privileges")
    if "provider: custom" not in config or "host.docker.internal:11434/v1" not in config:
        failures.append("Hermes POC must use the reviewed local Ollama configuration")
    if "platform_toolsets:\n  cli: []" not in config or "ithildin-local:" not in config:
        failures.append("Hermes POC must disable CLI toolsets and configure Ithildin MCP")
    if "default: gemma4:e4b" not in config or "mcp_discovery_timeout: 10" not in config:
        failures.append(
            "Hermes POC must pin the reviewed local model and bounded MCP discovery wait"
        )
    if "- chat" not in compose or "- --quiet" not in compose or "- --query" not in compose:
        failures.append("Hermes POC must use the verified single-query chat path")
    if "filesystem non-bypass" not in mission:
        failures.append("Hermes mission must state that Track A does not prove non-bypass")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "documents": list(DOCS),
        "deployment_files": list(DEPLOYMENT_FILES),
        "tool_count": 24,
        "image_digest": IMAGE_DIGEST,
        "track_a_compatibility_allowed": True,
        "track_b_runtime_expansion_allowed": False,
        "mission_orchestration_allowed": False,
        "remote_mcp_allowed": False,
        "dynamic_identity_allowed": False,
        "new_governed_tools_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Hermes governance POC plan check",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report['tool_count']}",
        f"image_digest: {report['image_digest']}",
        f"track_a_compatibility_allowed: {str(report['track_a_compatibility_allowed']).lower()}",
        "track_b_runtime_expansion_allowed: "
        f"{str(report['track_b_runtime_expansion_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report(args.repo_root.resolve())
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_report(report))
    return 0 if report["valid"] else 1


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


if __name__ == "__main__":
    raise SystemExit(main())

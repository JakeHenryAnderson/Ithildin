"""Validate public-preview documentation and deployment guardrails."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

WARNING_PHRASES = [
    "local-preview mediation layer",
    "not a sandbox",
    "trusted computing base",
    "tamper-evident local evidence",
    "Redaction is best-effort",
    "SQLite is the only v0.1 runtime storage backend",
]

FORBIDDEN_CLAIMS = [
    "secure sandbox",
    "prevents compromise",
    "production-ready",
    "enterprise identity",
    "tamper-proof audit",
    "immutable audit",
    "compliance-grade audit",
    "safe arbitrary tool use",
    "network sandbox",
    "remote MCP gateway",
]

FORBIDDEN_CLAIM_DOCS = [
    ROOT / "README.md",
    ROOT / "docs/codex",
    ROOT / "docs/obsidian",
    ROOT / "docs/research",
]

THREAT_MODEL_LINKED_DOCS = [
    ROOT / "README.md",
    ROOT / "docs/codex/local-preview-release.md",
    ROOT / "docs/codex/v0.1-local-preview-checklist.md",
    ROOT / "docs/codex/v0.1-public-preview-release-notes.md",
]


def main() -> None:
    failures: list[str] = []
    failures.extend(_check_warning_labels())
    failures.extend(_check_forbidden_claims())
    failures.extend(_check_threat_model_links())
    failures.extend(_check_compose_boundaries())

    if failures:
        for failure in failures:
            print(f"release guardrail failed: {failure}", file=sys.stderr)
        raise SystemExit(1)

    print("Release guardrails passed.")


def _check_warning_labels() -> list[str]:
    release_notes = (ROOT / "docs/codex/v0.1-public-preview-release-notes.md").read_text(
        encoding="utf-8"
    )
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    combined = f"{readme}\n{release_notes}"
    return [
        f"missing warning label: {phrase}"
        for phrase in WARNING_PHRASES
        if phrase not in combined
    ]


def _check_forbidden_claims() -> list[str]:
    failures: list[str] = []
    for path in _markdown_paths(FORBIDDEN_CLAIM_DOCS):
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            lowered_line = line.lower()
            for phrase in FORBIDDEN_CLAIMS:
                if phrase in lowered_line and not _is_allowed_claim_context(lines, index):
                    failures.append(
                        f"{path.relative_to(ROOT)}:{index + 1} uses forbidden claim {phrase!r}"
                    )
    return failures


def _markdown_paths(paths: list[Path]) -> list[Path]:
    result: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix == ".md":
            result.append(path)
        elif path.is_dir():
            result.extend(sorted(path.rglob("*.md")))
    return result


def _is_allowed_claim_context(lines: list[str], index: int) -> bool:
    start = max(0, index - 3)
    context = " ".join(lines[start : index + 2]).lower()
    allowed_markers = (
        "not ",
        "non-goal",
        "non-goals",
        "deferred",
        "avoid",
        "forbidden",
        "must not",
        "does not",
        "do-not-add",
        "warning",
        "review prompt",
        "reviewer focus",
        "should be avoided",
    )
    return any(marker in context for marker in allowed_markers)


def _check_threat_model_links() -> list[str]:
    failures: list[str] = []
    for path in THREAT_MODEL_LINKED_DOCS:
        text = path.read_text(encoding="utf-8")
        if "threat-model-and-non-goals.md" not in text:
            failures.append(f"{path.relative_to(ROOT)} does not link the threat model")
    return failures


def _check_compose_boundaries() -> list[str]:
    compose_path = ROOT / "deploy/docker-compose.yml"
    compose_text = compose_path.read_text(encoding="utf-8")
    compose = yaml.safe_load(compose_text)
    failures: list[str] = []
    if "docker.sock" in compose_text:
        failures.append("Compose must not mount the Docker socket")
    for service_name, service in compose.get("services", {}).items():
        for port in service.get("ports", []):
            if not str(port).startswith("127.0.0.1:"):
                failures.append(f"{service_name} exposes non-loopback port {port}")
        if service.get("privileged"):
            failures.append(f"{service_name} must not run privileged")
    return failures


if __name__ == "__main__":
    main()

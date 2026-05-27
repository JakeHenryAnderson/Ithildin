"""Validate public-preview documentation and deployment guardrails."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

WARNING_PHRASES = [
    "not production security software",
    "not a kernel sandbox",
    "not externally notarized or tamper-proof",
    "Local principals are attribution labels",
    "Redaction is best-effort",
    "SQLite is the only v0.1 runtime storage backend",
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

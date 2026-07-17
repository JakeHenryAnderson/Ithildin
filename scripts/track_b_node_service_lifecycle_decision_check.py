#!/usr/bin/env python3
"""Validate the bounded Node service lifecycle authorization artifacts."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = (
    ROOT / "docs/codex/track-b-node-service-lifecycle-capability-decision.md",
    ROOT / "docs/codex/track-b-node-service-lifecycle-architecture.md",
    ROOT / "docs/codex/track-b-node-service-lifecycle-implementation-plan.md",
)


def main() -> None:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in DOCS).lower()
    required = (
        "mode-0600",
        "stored_not_enforced",
        "bounded exponential retry",
        "graceful",
        "read-only root",
        "no docker socket",
        "stdin",
        "self-update",
        "runner lifecycle control",
        "production identity",
        "24",
        "new governed tool",
    )
    missing = [phrase for phrase in required if phrase not in combined]
    if missing:
        raise SystemExit(f"Node service lifecycle decision is incomplete: {missing}")
    print("Track B Node service lifecycle decision check passed")


if __name__ == "__main__":
    main()

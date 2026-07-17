#!/usr/bin/env python3
"""Validate the bounded Node release-artifact authorization artifacts."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = (
    ROOT / "docs/codex/track-b-node-release-artifact-capability-decision.md",
    ROOT / "docs/codex/track-b-node-release-artifact-architecture.md",
    ROOT / "docs/codex/track-b-node-release-artifact-implementation-plan.md",
)


def main() -> None:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in DOCS).lower()
    required = (
        "dedicated",
        "domain-separated",
        "dirty",
        "mode `0600`",
        "explicit operator-selected",
        "image id",
        "zero exposed ports",
        "self-update",
        "gateway enforcement",
        "official hosted supply-chain signing",
        "runner lifecycle control",
        "24",
        "new governed tool",
    )
    missing = [phrase for phrase in required if phrase not in combined]
    if missing:
        raise SystemExit(f"Node release-artifact decision is incomplete: {missing}")
    print("Track B Node release-artifact decision check passed")


if __name__ == "__main__":
    main()

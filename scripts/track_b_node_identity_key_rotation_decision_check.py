#!/usr/bin/env python3
"""Validate the bounded Node identity-key rotation authorization artifacts."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = (
    ROOT / "docs/codex/track-b-node-identity-key-rotation-capability-decision.md",
    ROOT / "docs/codex/track-b-node-identity-key-rotation-architecture.md",
    ROOT / "docs/codex/track-b-node-identity-key-rotation-implementation-plan.md",
)


def main() -> None:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in DOCS).lower()
    required = (
        "current-key authorization",
        "proof of possession",
        "mode-0600",
        "immediately loses all ordinary node request authority",
        "revoke and re-enroll",
        "24",
        "private-key upload",
        "administrator-forced key replacement",
        "retired-key fallback",
        "runner authority",
        "new governed tool",
    )
    missing = [phrase for phrase in required if phrase not in combined]
    if missing:
        raise SystemExit(f"Node identity-key rotation decision is incomplete: {missing}")
    print("Track B Node identity-key rotation decision check passed")


if __name__ == "__main__":
    main()

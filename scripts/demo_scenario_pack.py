"""Validate the documented demo scenario pack."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs/codex/demo-scenario-pack-v2.md"

REQUIRED_COMMANDS = [
    "make release-check",
    "make filesystem-contract-check",
    "make demo-seed",
    "make compose-up",
    "make compose-smoke",
    "make demo-flow",
    "make operator-sandbox-demo-readiness",
    "make operator-sandbox-demo-smoke",
    "make operator-sandbox-dashboard-checklist",
    "make operator-sandbox-demo-packet",
    "make agent-run-correlation-smoke",
    "make agent-run-correlation-packet",
    "make live-demo-preflight",
    "make live-demo-status",
    "make live-demo-smoke",
    "make live-demo-packet",
    "make negative-review-transcripts",
    "make signed-evidence-demo",
    "make signed-evidence-demo-verify",
    "make review-candidate",
]

REQUIRED_BOUNDARY_PHRASES = [
    "does not add new tool powers",
    "no Docker socket mount",
    "not production security software",
    "The wrong conclusion",
]


def main() -> int:
    failures = validate_scenario_pack()
    if failures:
        for failure in failures:
            print(f"demo scenario pack failure: {failure}", file=sys.stderr)
        return 1
    print("Demo scenario pack validation passed.")
    return 0


def validate_scenario_pack() -> list[str]:
    failures: list[str] = []
    if not DOC_PATH.exists():
        return [f"missing {DOC_PATH.relative_to(ROOT)}"]
    text = DOC_PATH.read_text(encoding="utf-8")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    targets = _make_targets(makefile)

    for command in REQUIRED_COMMANDS:
        if command not in text:
            failures.append(f"document missing command: {command}")
            continue
        target = command.removeprefix("make ").split()[0]
        if target not in targets:
            failures.append(f"document references missing Make target: {target}")

    for phrase in REQUIRED_BOUNDARY_PHRASES:
        if phrase not in text:
            failures.append(f"document missing boundary phrase: {phrase}")
    return failures


def _make_targets(makefile: str) -> set[str]:
    targets: set[str] = set()
    for line in makefile.splitlines():
        match = re.match(r"^([A-Za-z0-9_.-]+):(?:\s|$)", line)
        if match:
            targets.add(match.group(1))
    return targets


if __name__ == "__main__":
    raise SystemExit(main())

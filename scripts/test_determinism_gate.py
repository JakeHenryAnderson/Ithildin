"""Check test collection determinism and obvious local-state coupling patterns."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_TEST_PATTERNS = {
    "sleep_call": re.compile(r"\btime\.sleep\("),
    "unseeded_random": re.compile(r"\brandom\.(?:random|choice|choices|randint|shuffle)\("),
    "absolute_tmp_path": re.compile(r"Path\([\"']/tmp"),
}


class DeterminismGateError(RuntimeError):
    """Raised when the deterministic-test gate cannot complete."""


@dataclass(frozen=True)
class DeterminismFinding:
    path: str
    line: int
    reason: str


@dataclass(frozen=True)
class DeterminismGateResult:
    collection_stable: bool
    collected_summary: str
    findings: list[DeterminismFinding]

    def as_dict(self) -> dict[str, Any]:
        return {
            "collection_stable": self.collection_stable,
            "collected_summary": self.collected_summary,
            "findings": [finding.__dict__ for finding in self.findings],
            "ok": self.collection_stable and not self.findings,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()

    try:
        result = run_gate()
    except DeterminismGateError as exc:
        print(f"determinism gate failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    else:
        print(render_result(result))
    return 0 if result.collection_stable and not result.findings else 1


def run_gate() -> DeterminismGateResult:
    first = _pytest_collect()
    second = _pytest_collect()
    findings = _scan_test_patterns(ROOT / "tests")
    return DeterminismGateResult(
        collection_stable=first == second,
        collected_summary=first,
        findings=findings,
    )


def render_result(result: DeterminismGateResult) -> str:
    lines = [
        "# Ithildin Test Determinism Gate",
        "",
        f"collection_stable: `{str(result.collection_stable).lower()}`",
        f"findings: `{len(result.findings)}`",
        "",
        "## Collection Summary",
        "",
        "```text",
        result.collected_summary.rstrip(),
        "```",
        "",
    ]
    if result.findings:
        lines.extend(["## Findings", ""])
        lines.extend(
            f"- `{finding.path}:{finding.line}` {finding.reason}"
            for finding in result.findings
        )
        lines.append("")
    else:
        lines.append("Determinism gate passed.")
    return "\n".join(lines)


def _pytest_collect() -> str:
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise DeterminismGateError(completed.stderr.strip() or "pytest collection failed")
    return completed.stdout


def _scan_test_patterns(test_root: Path) -> list[DeterminismFinding]:
    findings: list[DeterminismFinding] = []
    for path in sorted(test_root.glob("test_*.py")):
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines, start=1):
            for reason, pattern in FORBIDDEN_TEST_PATTERNS.items():
                if pattern.search(line):
                    findings.append(
                        DeterminismFinding(
                            path=_display_path(path),
                            line=index,
                            reason=reason,
                        )
                    )
    return findings


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())

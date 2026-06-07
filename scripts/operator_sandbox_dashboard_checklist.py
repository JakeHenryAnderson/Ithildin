"""Generate a static dashboard checklist for the operator-managed sandbox demo."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_OUTPUT = Path(
    "var/review-packets/v3/operator-sandbox-demo/OPERATOR_SANDBOX_DASHBOARD_CHECKLIST.md"
)
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
UI_SOURCE = Path("apps/ui/src/App.tsx")
UI_TESTS = Path("apps/ui/src/App.test.tsx")
REQUIRED_UI_PHRASES = [
    "Agent Runs",
    "Export Run Evidence",
    "System Trust",
    "run-filter-bar",
    "timeline-view",
]
REQUIRED_TEST_PHRASES = [
    "filters agent runs with a bounded authenticated query",
    "renders trust warnings, approval evidence, and approve/deny actions",
    "Export Run Evidence",
]


class OperatorSandboxDashboardChecklistError(RuntimeError):
    """Raised when the dashboard checklist cannot be generated."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        path = build_checklist(repo_root=Path.cwd().resolve(), output=args.output)
    except OperatorSandboxDashboardChecklistError as exc:
        print(f"operator sandbox dashboard checklist failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built operator-managed sandbox dashboard checklist at {path}")
    return 0


def build_checklist(*, repo_root: Path, output: Path) -> Path:
    _require_project_root(repo_root)
    source = _read(repo_root / UI_SOURCE)
    tests = _read(repo_root / UI_TESTS)
    failures: list[str] = []
    for phrase in REQUIRED_UI_PHRASES:
        if phrase not in source:
            failures.append(f"UI source missing phrase: {phrase}")
    for phrase in REQUIRED_TEST_PHRASES:
        if phrase not in tests:
            failures.append(f"UI tests missing phrase: {phrase}")
    if failures:
        raise OperatorSandboxDashboardChecklistError("; ".join(failures))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_render(), encoding="utf-8")
    return output


def _render() -> str:
    return f"""# Operator-Managed Sandbox Dashboard Checklist

Status: generated static checklist. This artifact validates the demo-facing review-console surface
from committed UI source/tests; it does not use browser automation and does not add runtime
behavior.

Generated at: `{datetime.now(UTC).isoformat()}`.

## Panels To Inspect During Live Demo

- System Trust: local-preview warnings, tool count, manifest/policy/audit/storage/telemetry status.
- Agent Runs: principal/workspace/status/tool filters and summary chips.
- Selected run timeline: category/status grouping, warning chips, short IDs, and safe metadata.
- Export Run Evidence: read-only `/runs/{{run_id}}/evidence-export` download action.
- Approvals and diagnostics: approval binding evidence and patch diagnostics remain visible but do
  not create run controls or sandbox controls.

## Static Source/Test Evidence

- `apps/ui/src/App.tsx` contains the Agent Runs panel, System Trust panel, timeline view, bounded
  run filters, and Export Run Evidence action.
- `apps/ui/src/App.test.tsx` covers authenticated run filter requests, summary rendering, trust
  warning rendering, approval evidence display, approve/deny actions, and run evidence export.

## Non-Claims

- This checklist is not a screenshot, visual proof, browser smoke, production UX audit, SIEM
  custody review, or proof of sandboxing.
- Ithildin still does not add sandbox lifecycle control, shell/Docker/Kubernetes/browser tools,
  remote MCP hosting, production identity, runtime Postgres, hosted telemetry, arbitrary HTTP, broad
  filesystem writes, or new governed tool powers.
"""


def _read(path: Path) -> str:
    if not path.exists():
        raise OperatorSandboxDashboardChecklistError(f"missing required file: {path}")
    return path.read_text(encoding="utf-8")


def _require_project_root(repo_root: Path) -> None:
    missing = [marker.as_posix() for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        raise OperatorSandboxDashboardChecklistError(
            "must be run from the Ithildin repo root; missing markers: " + ", ".join(missing)
        )


if __name__ == "__main__":
    raise SystemExit(main())

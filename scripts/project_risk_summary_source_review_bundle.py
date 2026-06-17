"""Build a project.risk.summary source-review bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import project_risk_summary_review_handoff_check

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/project-risk-summary-source-review")
PROJECT_MARKERS = ("pyproject.toml", "Makefile", "tool-manifests.lock.json")
DOCS = {
    "02_PROJECT_RISK_SUMMARY_SELECTION.md": Path("docs/codex/v3-project-risk-summary-selection.md"),
    "03_PROJECT_RISK_SUMMARY_PROPOSAL.md": Path(
        "docs/codex/capability-proposals/project-risk-summary.md"
    ),
    "04_PROJECT_RISK_SUMMARY_IMPLEMENTATION_PLAN.md": Path(
        "docs/codex/capability-implementation-plans/project-risk-summary.md"
    ),
    "05_PROJECT_RISK_SUMMARY_IMPLEMENTATION_BOUNDARY.md": Path(
        "docs/codex/v3-project-risk-summary-implementation.md"
    ),
    "06_PROJECT_RISK_SUMMARY_FIXTURE_PLAN.md": Path(
        "docs/codex/project-risk-summary-fixture-plan.md"
    ),
    "07_PROJECT_RISK_SUMMARY_NEGATIVE_TRANSCRIPTS.md": Path(
        "docs/codex/project-risk-summary-negative-transcripts.md"
    ),
    "08_PROJECT_RISK_SUMMARY_SOURCE_REVIEW.md": Path(
        "docs/codex/v3-project-risk-summary-source-review.md"
    ),
}


class ProjectRiskSummarySourceReviewBundleError(RuntimeError):
    """Raised when the source-review bundle cannot be built."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()

    try:
        output_dir = build_bundle(
            repo_root=Path.cwd().resolve(),
            output_dir=args.output_dir,
            allow_dirty=args.allow_dirty,
        )
    except ProjectRiskSummarySourceReviewBundleError as exc:
        print(f"project.risk.summary source-review bundle failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built project.risk.summary source-review bundle at {output_dir}")
    return 0


def build_bundle(*, repo_root: Path, output_dir: Path, allow_dirty: bool = False) -> Path:
    _require_project_root(repo_root)
    commit = _git(repo_root, ["rev-parse", "HEAD"])
    dirty = bool(_git(repo_root, ["status", "--short"]))
    if dirty and not allow_dirty:
        raise ProjectRiskSummarySourceReviewBundleError(
            "working tree is dirty; commit before source-review handoff"
        )

    handoff = project_risk_summary_review_handoff_check.build_report(repo_root)
    if handoff["failures"]:
        raise ProjectRiskSummarySourceReviewBundleError("; ".join(handoff["failures"]))

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context = {"commit": commit, "dirty": dirty, "handoff": handoff}
    files = {
        "00_PROJECT_RISK_SUMMARY_SOURCE_REVIEW_INDEX.md": _index(context),
        "01_PROJECT_RISK_SUMMARY_SOURCE_REVIEW_PROMPT.md": _prompt(context),
        "09_PROJECT_RISK_SUMMARY_EVIDENCE.md": _evidence(context),
        "10_PROJECT_RISK_SUMMARY_INTAKE_COMMANDS.md": _intake(context),
    }
    for name, source in DOCS.items():
        files[name] = (repo_root / source).read_text(encoding="utf-8")
    for name, content in files.items():
        (output_dir / name).write_text(content.rstrip() + "\n", encoding="utf-8")
    _write_json(
        output_dir / "project-risk-summary-source-review-artifact-hashes.json",
        _hashes(output_dir),
    )
    return output_dir


def _require_project_root(repo_root: Path) -> None:
    missing = [marker for marker in PROJECT_MARKERS if not repo_root.joinpath(marker).exists()]
    if missing:
        raise ProjectRiskSummarySourceReviewBundleError(
            "must be run from the Ithildin repo root; missing markers: " + ", ".join(missing)
        )


def _index(context: dict[str, Any]) -> str:
    return f"""# project.risk.summary Source Review Bundle

This is the implemented source-review bundle for `project.risk.summary`. It prepares the review
lane for source-level disposition and does not claim external closure.

- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Tool count: `{context["handoff"]["tool_count"]}`.
- Runtime implemented: `{str(context["handoff"]["runtime_implemented"]).lower()}`.
- Future runtime implementation allowed:
  `{str(context["handoff"]["future_runtime_implementation_allowed"]).lower()}`.

## Attachments

1. `00_PROJECT_RISK_SUMMARY_SOURCE_REVIEW_INDEX.md`
2. `01_PROJECT_RISK_SUMMARY_SOURCE_REVIEW_PROMPT.md`
3. `02_PROJECT_RISK_SUMMARY_SELECTION.md`
4. `03_PROJECT_RISK_SUMMARY_PROPOSAL.md`
5. `04_PROJECT_RISK_SUMMARY_IMPLEMENTATION_PLAN.md`
6. `05_PROJECT_RISK_SUMMARY_IMPLEMENTATION_BOUNDARY.md`
7. `06_PROJECT_RISK_SUMMARY_FIXTURE_PLAN.md`
8. `07_PROJECT_RISK_SUMMARY_NEGATIVE_TRANSCRIPTS.md`
9. `08_PROJECT_RISK_SUMMARY_SOURCE_REVIEW.md`
10. `09_PROJECT_RISK_SUMMARY_EVIDENCE.md`
11. `10_PROJECT_RISK_SUMMARY_INTAKE_COMMANDS.md`
12. `project-risk-summary-source-review-artifact-hashes.json`
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# project.risk.summary Source Review Prompt

You are reviewing Ithildin's `project.risk.summary` lane as a source-review preparation packet.
Runtime implementation is present. Evaluate whether the manifest, executor, focused tests, policy
parity, audit metadata, fixture plan, negative transcript plan, and handoff evidence are sufficient
to close the lane for the v0.1 local-preview runtime boundary.

Reviewed commit: `{context["commit"]}`
Area: `project-risk-summary`
Finding namespace: `EXT-RISK-SUMMARY-###`

Please answer:

- whether the implementation preserves count-only risk posture metadata;
- whether the non-leak list is enforced by source and tests;
- whether any design item still drifts toward vulnerability scanning, scanner execution, dependency
  vulnerability analysis, compliance automation, or security assurance;
- what must be added before source-review closure.

Do not approve production security positioning, compliance claims, broad capability expansion, or
new governed tool powers.
"""


def _evidence(context: dict[str, Any]) -> str:
    return f"""# project.risk.summary Evidence

```json
{json.dumps(context["handoff"], indent=2, sort_keys=True)}
```
"""


def _intake(context: dict[str, Any]) -> str:
    return f"""# project.risk.summary Intake Commands

```sh
make project-risk-summary-proposal-check
make project-risk-summary-implementation-plan-check
make project-risk-summary-implementation-gate
make project-risk-summary-preimplementation-check
make project-risk-summary-review-handoff-check
make project-risk-summary-source-review-bundle
uv run pytest tests/test_read_tools.py tests/test_governed_tool_calls.py \\
  tests/test_mcp_adapter.py tests/test_policy_parity.py tests/test_tool_registry.py -q
make release-check
```

Current commit: `{context["commit"]}`.
"""


def _hashes(output_dir: Path) -> list[dict[str, Any]]:
    entries = []
    for path in sorted(output_dir.iterdir()):
        if path.name.endswith("artifact-hashes.json"):
            continue
        data = path.read_bytes()
        entries.append(
            {
                "path": path.name,
                "bytes": len(data),
                "sha256": "sha256:" + hashlib.sha256(data).hexdigest(),
            }
        )
    return entries


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


if __name__ == "__main__":
    raise SystemExit(main())

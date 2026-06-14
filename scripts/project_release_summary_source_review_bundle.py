"""Build a future project.release.summary source-review bundle placeholder."""

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

from scripts import (
    no_new_powers_guardrail,
    project_release_summary_implementation_gate,
    project_release_summary_preimplementation_check,
    project_release_summary_proposal_check,
    project_release_summary_review_handoff_check,
    tool_surface_invariant_gate,
)

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/project-release-summary-source-review")
DOCS = [
    (
        "02_PROJECT_RELEASE_SUMMARY_PROPOSAL.md",
        "docs/codex/capability-proposals/project-release-summary.md",
    ),
    (
        "03_PROJECT_RELEASE_SUMMARY_IMPLEMENTATION_PLAN.md",
        "docs/codex/capability-implementation-plans/project-release-summary.md",
    ),
    (
        "04_PROJECT_RELEASE_SUMMARY_IMPLEMENTATION_BOUNDARY.md",
        "docs/codex/v3-project-release-summary-implementation.md",
    ),
    (
        "05_PROJECT_RELEASE_SUMMARY_FIXTURE_PLAN.md",
        "docs/codex/project-release-summary-fixture-plan.md",
    ),
    (
        "06_PROJECT_RELEASE_SUMMARY_NEGATIVE_TRANSCRIPTS_PLAN.md",
        "docs/codex/project-release-summary-negative-transcripts.md",
    ),
    (
        "07_PROJECT_RELEASE_SUMMARY_REVIEW_HANDOFF.md",
        "docs/codex/v3-project-release-summary-source-review.md",
    ),
]


class ProjectReleaseSummarySourceReviewBundleError(RuntimeError):
    """Raised when the source-review bundle cannot be built."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--skip-commands", action="store_true")
    args = parser.parse_args()

    try:
        output_dir = build_bundle(
            repo_root=Path.cwd().resolve(),
            output_dir=args.output_dir,
            allow_dirty=args.allow_dirty,
            run_commands=not args.skip_commands,
        )
    except ProjectReleaseSummarySourceReviewBundleError as exc:
        print(f"project.release.summary source-review bundle failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built project.release.summary source-review bundle at {output_dir}")
    return 0


def build_bundle(
    *,
    repo_root: Path,
    output_dir: Path,
    allow_dirty: bool = False,
    run_commands: bool = True,
) -> Path:
    _require_project_root(repo_root)
    commit = _git(repo_root, ["rev-parse", "HEAD"])
    dirty = bool(_git(repo_root, ["status", "--short"]))
    if dirty and not allow_dirty:
        raise ProjectReleaseSummarySourceReviewBundleError(
            "working tree is dirty; commit before source-review handoff"
        )

    proposal = project_release_summary_proposal_check.build_report(repo_root)
    plan = project_release_summary_preimplementation_check.build_report(repo_root)
    implementation_gate = project_release_summary_implementation_gate.build_report(repo_root)
    review_handoff_check = project_release_summary_review_handoff_check.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)

    failures = [
        *(f"proposal check: {failure}" for failure in proposal["failures"]),
        *(f"preimplementation check: {failure}" for failure in plan["failures"]),
        *(f"implementation gate: {failure}" for failure in implementation_gate["failures"]),
        *(f"review handoff check: {failure}" for failure in review_handoff_check["failures"]),
        *(f"no-new-powers guardrail: {failure}" for failure in no_new_powers["failures"]),
        *(f"tool-surface: {failure}" for failure in tool_surface["failures"]),
    ]
    if failures:
        raise ProjectReleaseSummarySourceReviewBundleError("; ".join(failures))

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context = {
        "commit": commit,
        "dirty": dirty,
        "proposal": proposal,
        "preimplementation": plan,
        "implementation_gate": implementation_gate,
        "review_handoff_check": review_handoff_check,
        "no_new_powers": no_new_powers,
        "tool_surface": tool_surface,
    }
    files = {
        "00_PROJECT_RELEASE_SUMMARY_SOURCE_REVIEW_INDEX.md": _index(context),
        "01_PROJECT_RELEASE_SUMMARY_SOURCE_REVIEW_PROMPT.md": _prompt(context),
        "02_PROJECT_RELEASE_SUMMARY_PROPOSAL.md": _load_doc(repo_root, DOCS[0][1]),
        "03_PROJECT_RELEASE_SUMMARY_IMPLEMENTATION_PLAN.md": _load_doc(repo_root, DOCS[1][1]),
        "04_PROJECT_RELEASE_SUMMARY_IMPLEMENTATION_BOUNDARY.md": _load_doc(
            repo_root, DOCS[2][1]
        ),
        "05_PROJECT_RELEASE_SUMMARY_FIXTURE_PLAN.md": _load_doc(repo_root, DOCS[3][1]),
        "06_PROJECT_RELEASE_SUMMARY_NEGATIVE_TRANSCRIPTS_PLAN.md": _load_doc(
            repo_root, DOCS[4][1]
        ),
        "07_PROJECT_RELEASE_SUMMARY_REVIEW_HANDOFF.md": _load_doc(repo_root, DOCS[5][1]),
        "08_PROJECT_RELEASE_SUMMARY_GATE_EVIDENCE.json": json.dumps(
            {
                "proposal": proposal,
                "preimplementation": plan,
                "implementation_gate": implementation_gate,
                "review_handoff_check": review_handoff_check,
                "no_new_powers": no_new_powers,
                "tool_surface": tool_surface,
            },
            indent=2,
            sort_keys=True,
        ),
    }
    for name, content in files.items():
        (output_dir / name).write_text(content.rstrip() + "\n", encoding="utf-8")
    _write_json(
        output_dir / "project-release-summary-source-review-artifact-hashes.json",
        _hashes(output_dir),
    )
    return output_dir


def _require_project_root(repo_root: Path) -> None:
    missing = [
        marker for marker in ("pyproject.toml", "Makefile", "tool-manifests.lock.json")
        if not repo_root.joinpath(marker).exists()
    ]
    if missing:
        raise ProjectReleaseSummarySourceReviewBundleError(
            "must be run from the Ithildin repo root; missing markers: " + ", ".join(missing)
        )


def _index(context: dict[str, Any]) -> str:
    return f"""# project.release.summary Source Review Handoff

Status: implemented source-review handoff.

This packet prepares the implemented bounded read-only `project.release.summary` lane for focused
source review. It does not close the lane without reviewer disposition.

## Boundary

- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Capability: `project.release.summary`.
- Resource type: `project_release`.
- Tool count: `{context["tool_surface"]["tool_count"]}`.
- Runtime implementation: present.
- Finding namespace: `EXT-RELEASE-SUMMARY-###`.

## Attachments

1. `00_PROJECT_RELEASE_SUMMARY_SOURCE_REVIEW_INDEX.md`
2. `01_PROJECT_RELEASE_SUMMARY_SOURCE_REVIEW_PROMPT.md`
3. `02_PROJECT_RELEASE_SUMMARY_PROPOSAL.md`
4. `03_PROJECT_RELEASE_SUMMARY_IMPLEMENTATION_PLAN.md`
5. `04_PROJECT_RELEASE_SUMMARY_IMPLEMENTATION_BOUNDARY.md`
6. `05_PROJECT_RELEASE_SUMMARY_FIXTURE_PLAN.md`
7. `06_PROJECT_RELEASE_SUMMARY_NEGATIVE_TRANSCRIPTS_PLAN.md`
8. `07_PROJECT_RELEASE_SUMMARY_REVIEW_HANDOFF.md`
9. `08_PROJECT_RELEASE_SUMMARY_GATE_EVIDENCE.json`
10. `project-release-summary-source-review-artifact-hashes.json`

## Closure Note

The lane remains source-review pending until a focused reviewer reviews implementation source,
tests, policy parity, audit evidence, and no-new-powers evidence.
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# project.release.summary Source Review Prompt

This is the source-review handoff for the implemented bounded read-only `project.release.summary`
lane. Review the attached proposal, implementation plan, implementation boundary, fixture plan,
negative-transcript plan, review handoff doc, and gate evidence.

Reviewed commit: `{context["commit"]}`
Finding namespace: `EXT-RELEASE-SUMMARY-###`

Please confirm whether the implemented lane stays within the approved limited read-only boundary
and whether any `EXT-RELEASE-SUMMARY-###` findings block local-preview source-review disposition.
"""


def _load_doc(repo_root: Path, relative: str) -> str:
    path = repo_root / relative
    if not path.exists():
        raise ProjectReleaseSummarySourceReviewBundleError(f"missing document: {relative}")
    return path.read_text(encoding="utf-8")


def _hashes(output_dir: Path) -> list[dict[str, Any]]:
    entries = []
    for path in sorted(output_dir.iterdir()):
        if path.name == "project-release-summary-source-review-artifact-hashes.json":
            continue
        data = path.read_bytes()
        entries.append(
            {
                "path": path.name,
                "sha256": "sha256:" + hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            }
        )
    return entries


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git(repo_root: Path, args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())

"""Build the project.release.summary design-review packet."""

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
    next_capability_readiness,
    no_new_powers_guardrail,
    project_release_summary_implementation_gate,
    project_release_summary_implementation_plan_check,
    project_release_summary_preimplementation_check,
    project_release_summary_proposal_check,
    project_release_summary_review_handoff_check,
)

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/project-release-summary-design-review")
PROJECT_MARKERS = ("pyproject.toml", "Makefile", "tool-manifests.lock.json")
DOCS = {
    "02_NEXT_CAPABILITY_READINESS.md": Path("docs/codex/next-capability-readiness.md"),
    "03_V3_NEXT_CAPABILITY_CANDIDATE_EVALUATION_2.md": Path(
        "docs/codex/v3-next-capability-candidate-evaluation-2.md"
    ),
    "04_V3_PROJECT_RELEASE_SUMMARY_SELECTION.md": Path(
        "docs/codex/v3-project-release-summary-selection.md"
    ),
    "05_PROJECT_RELEASE_SUMMARY_PROPOSAL.md": Path(
        "docs/codex/capability-proposals/project-release-summary.md"
    ),
    "06_PROJECT_RELEASE_SUMMARY_IMPLEMENTATION_PLAN.md": Path(
        "docs/codex/capability-implementation-plans/project-release-summary.md"
    ),
    "07_PROJECT_RELEASE_SUMMARY_FIXTURE_PLAN.md": Path(
        "docs/codex/project-release-summary-fixture-plan.md"
    ),
    "09_PROJECT_RELEASE_SUMMARY_IMPLEMENTATION_DECISION.md": Path(
        "docs/codex/v3-project-release-summary-implementation.md"
    ),
    "11_PROJECT_RELEASE_SUMMARY_SOURCE_REVIEW_HANDOFF.md": Path(
        "docs/codex/v3-project-release-summary-source-review.md"
    ),
    "12_PROJECT_RELEASE_SUMMARY_NEGATIVE_TRANSCRIPTS_PLAN.md": Path(
        "docs/codex/project-release-summary-negative-transcripts.md"
    ),
}


class ProjectReleaseSummaryDesignReviewPacketError(RuntimeError):
    """Raised when the design-review packet cannot be built."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()

    try:
        output_dir = build_packet(
            repo_root=Path.cwd().resolve(),
            output_dir=args.output_dir,
            allow_dirty=args.allow_dirty,
        )
    except ProjectReleaseSummaryDesignReviewPacketError as exc:
        print(f"project.release.summary design-review packet failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built project.release.summary design-review packet at {output_dir}")
    return 0


def build_packet(*, repo_root: Path, output_dir: Path, allow_dirty: bool = False) -> Path:
    _require_project_root(repo_root)
    commit = _git(repo_root, ["rev-parse", "HEAD"])
    dirty = bool(_git(repo_root, ["status", "--short"]))
    if dirty and not allow_dirty:
        raise ProjectReleaseSummaryDesignReviewPacketError(
            "working tree is dirty; commit before design-review handoff"
        )

    proposal = project_release_summary_proposal_check.build_report(repo_root)
    plan = project_release_summary_implementation_plan_check.build_report(repo_root)
    preimplementation = project_release_summary_preimplementation_check.build_report(repo_root)
    implementation_gate = project_release_summary_implementation_gate.build_report(repo_root)
    review_handoff_check = project_release_summary_review_handoff_check.build_report(repo_root)
    readiness = next_capability_readiness.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures = [
        *(f"proposal check: {failure}" for failure in proposal["failures"]),
        *(f"implementation-plan check: {failure}" for failure in plan["failures"]),
        *(f"preimplementation check: {failure}" for failure in preimplementation["failures"]),
        *(f"implementation-gate: {failure}" for failure in implementation_gate["failures"]),
        *(f"review-handoff-check: {failure}" for failure in review_handoff_check["failures"]),
        *(f"next-capability readiness: {failure}" for failure in readiness["failures"]),
        *(f"no-new-powers guardrail: {failure}" for failure in no_new_powers["failures"]),
    ]
    if failures:
        raise ProjectReleaseSummaryDesignReviewPacketError("; ".join(failures))

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context = {
        "commit": commit,
        "dirty": dirty,
        "proposal": proposal,
        "plan": plan,
        "preimplementation": preimplementation,
        "implementation_gate": implementation_gate,
        "review_handoff_check": review_handoff_check,
        "readiness": readiness,
        "no_new_powers": no_new_powers,
    }
    files = {
        "00_PROJECT_RELEASE_SUMMARY_DESIGN_REVIEW_INDEX.md": _index(context),
        "01_PROJECT_RELEASE_SUMMARY_REVIEW_PROMPT.md": _prompt(context),
        "07_PROJECT_RELEASE_SUMMARY_FIXTURE_PLAN.md": (
            repo_root / DOCS["07_PROJECT_RELEASE_SUMMARY_FIXTURE_PLAN.md"]
        ).read_text(encoding="utf-8"),
        "08_PROJECT_RELEASE_SUMMARY_PREIMPLEMENTATION_CHECK.json": json.dumps(
            context["preimplementation"], indent=2, sort_keys=True
        ),
        "09_PROJECT_RELEASE_SUMMARY_IMPLEMENTATION_DECISION.md": (
            repo_root / DOCS["09_PROJECT_RELEASE_SUMMARY_IMPLEMENTATION_DECISION.md"]
        ).read_text(encoding="utf-8"),
        "10_PROJECT_RELEASE_SUMMARY_IMPLEMENTATION_GATE.json": json.dumps(
            context["implementation_gate"], indent=2, sort_keys=True
        ),
        "11_PROJECT_RELEASE_SUMMARY_SOURCE_REVIEW_HANDOFF.md": (
            repo_root / DOCS["11_PROJECT_RELEASE_SUMMARY_SOURCE_REVIEW_HANDOFF.md"]
        ).read_text(encoding="utf-8"),
        "12_PROJECT_RELEASE_SUMMARY_NEGATIVE_TRANSCRIPTS_PLAN.md": (
            repo_root / DOCS["12_PROJECT_RELEASE_SUMMARY_NEGATIVE_TRANSCRIPTS_PLAN.md"]
        ).read_text(encoding="utf-8"),
        "13_PROJECT_RELEASE_SUMMARY_REVIEW_HANDOFF_CHECK.json": json.dumps(
            context["review_handoff_check"], indent=2, sort_keys=True
        ),
        "14_PROJECT_RELEASE_SUMMARY_GATE_AND_RISK_EVIDENCE.md": _gate_evidence(context),
        "15_REVIEW_INTAKE_AND_NEXT_STEPS.md": _intake(context),
    }
    for name, source in DOCS.items():
        if name not in files:
            files[name] = (repo_root / source).read_text(encoding="utf-8")
    for name, content in files.items():
        (output_dir / name).write_text(content.rstrip() + "\n", encoding="utf-8")
    _write_json(
        output_dir / "project-release-summary-design-review-artifact-hashes.json",
        _hashes(output_dir),
    )
    return output_dir


def _require_project_root(repo_root: Path) -> None:
    missing = [marker for marker in PROJECT_MARKERS if not repo_root.joinpath(marker).exists()]
    if missing:
        raise ProjectReleaseSummaryDesignReviewPacketError(
            "must be run from the Ithildin repo root; missing markers: " + ", ".join(missing)
        )


def _index(context: dict[str, Any]) -> str:
    return f"""# project.release.summary Design Review Packet

This packet records the design-review lineage and source-review handoff for the implemented
bounded read-only local metadata capability. It does not approve additional implementation.
It now also includes the implemented source-review handoff doc,
`docs/codex/v3-project-release-summary-source-review.md`, the negative transcript plan,
`docs/codex/project-release-summary-negative-transcripts.md`, and review-handoff-check JSON
evidence for the same bounded lane.

## Boundary

- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Capability: `project.release.summary`.
- Scope: implemented bounded read-only source-review handoff.
- Implementation status: implemented bounded read-only.
- Tool count: `{context["no_new_powers"]["tool_count"]}`.
- New governed tool powers: no-go.

## Attachments

1. `00_PROJECT_RELEASE_SUMMARY_DESIGN_REVIEW_INDEX.md`
2. `01_PROJECT_RELEASE_SUMMARY_REVIEW_PROMPT.md`
3. `02_NEXT_CAPABILITY_READINESS.md`
4. `03_V3_NEXT_CAPABILITY_CANDIDATE_EVALUATION_2.md`
5. `04_V3_PROJECT_RELEASE_SUMMARY_SELECTION.md`
6. `05_PROJECT_RELEASE_SUMMARY_PROPOSAL.md`
7. `06_PROJECT_RELEASE_SUMMARY_IMPLEMENTATION_PLAN.md`
8. `07_PROJECT_RELEASE_SUMMARY_FIXTURE_PLAN.md`
9. `08_PROJECT_RELEASE_SUMMARY_PREIMPLEMENTATION_CHECK.json`
10. `09_PROJECT_RELEASE_SUMMARY_IMPLEMENTATION_DECISION.md`
11. `10_PROJECT_RELEASE_SUMMARY_IMPLEMENTATION_GATE.json`
12. `11_PROJECT_RELEASE_SUMMARY_SOURCE_REVIEW_HANDOFF.md`
13. `12_PROJECT_RELEASE_SUMMARY_NEGATIVE_TRANSCRIPTS_PLAN.md`
14. `13_PROJECT_RELEASE_SUMMARY_REVIEW_HANDOFF_CHECK.json`
15. `14_PROJECT_RELEASE_SUMMARY_GATE_AND_RISK_EVIDENCE.md`
16. `15_REVIEW_INTAKE_AND_NEXT_STEPS.md`
17. `project-release-summary-design-review-artifact-hashes.json`

## What This Packet Does Not Prove

This packet does not add or approve a manifest, executor, policy rule, MCP exposure, API behavior,
UI behavior, runtime behavior, release names, version strings, changelog contents, tag names,
branch names, raw paths, file contents, package names, dependency names, author or maintainer
names, command/script values, environment names or values, shell access, Git execution,
package-manager execution, CI execution, registry/network access, deployment-readiness claims,
legal claims, compliance claims, or future governed tool powers.
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# project.release.summary Review Prompt

This packet is for both internal and external source review of Ithildin's next design-only
read-only capability proposal. Treat this as review only. Do not approve implementation in this
review. At most, say whether a later implementation-boundary sprint may be considered. The packet
now also includes the implemented source-review handoff doc, negative-transcript plan, and
review-handoff-check evidence for the same bounded lane.

Reviewed commit: `{context["commit"]}`
Capability: `project.release.summary`
Finding namespace: `EXT-RELEASE-SUMMARY-###`

## Internal Review Prompt

Please review whether the selected candidate and its proposal remain design-only and avoid
manifest/executor/policy/MCP/runtime changes; whether count-only release posture metadata is useful
enough without release names, version strings, changelog contents, tag names, branch names, raw
paths, file contents, package names, dependency names, author or maintainer names, shell, Git,
package-manager, or CI execution; and whether the proposal, implementation plan, implementation
decision, and next-capability readiness evidence are consistent enough to justify a later
implementation-boundary sprint.

## External Review Prompt

Please review whether the attached candidate evaluation, selection, proposal, implementation plan,
implementation decision, and readiness evidence are sufficient for a later implementation-boundary
sprint to be considered. Do not approve implementation directly. Focus on whether the packet
preserves local-only count-only behavior, closed schema, policy/resource parity, audit safety, and
the deferred non-goals.

Required answer:

- Overall judgment.
- Blocking design findings, if any.
- Should-fix design findings, if any.
- Whether a later implementation-boundary sprint may be considered.
- What must remain deferred.

Use finding IDs `EXT-RELEASE-SUMMARY-###` for actionable findings.
"""


def _gate_evidence(context: dict[str, Any]) -> str:
    return f"""# project.release.summary Gate And Risk Evidence

## Proposal Check

```json
{json.dumps(context["proposal"], indent=2, sort_keys=True)}
```

## Implementation-Plan Check

```json
{json.dumps(context["plan"], indent=2, sort_keys=True)}
```

## Preimplementation Check

```json
{json.dumps(context["preimplementation"], indent=2, sort_keys=True)}
```

## Implementation Decision Evidence

```json
{json.dumps(context["implementation_gate"], indent=2, sort_keys=True)}
```

## Next-Capability Readiness

```json
{json.dumps(context["readiness"], indent=2, sort_keys=True)}
```

## No-New-Powers Guardrail

```json
{json.dumps(context["no_new_powers"], indent=2, sort_keys=True)}
```

## Review-Handoff Check Evidence

```json
{json.dumps(context["review_handoff_check"], indent=2, sort_keys=True)}
```
"""


def _intake(context: dict[str, Any]) -> str:
    return f"""# Review Intake And Next Steps

If review returns findings, normalize them with the existing finding-intake workflow and keep
implementation blocked until a later explicit decision.

Suggested command context:

- `make project-release-summary-proposal-check`
- `make project-release-summary-implementation-plan-check`
- `make project-release-summary-preimplementation-check`
- `make project-release-summary-implementation-gate`
- `make project-release-summary-review-handoff-check`
- `make project-release-summary-design-review-packet`
- `make project-release-summary-source-review-bundle`
- `make next-capability-readiness`
- `make release-check`

Current reviewed commit: `{context["commit"]}`.

If review finds no blocking design issues, the next sprint may draft an implementation decision.
It still must not add a manifest, executor, policy rule, MCP exposure, or runtime behavior unless
that later sprint explicitly records approval for this one bounded count-only capability.
"""


def _git(repo_root: Path, args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _hashes(output_dir: Path) -> list[dict[str, Any]]:
    entries = []
    for path in sorted(output_dir.iterdir()):
        if path.name == "project-release-summary-design-review-artifact-hashes.json":
            continue
        content = path.read_bytes()
        entries.append(
            {
                "path": path.name,
                "sha256": "sha256:" + hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
            }
        )
    return entries


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())

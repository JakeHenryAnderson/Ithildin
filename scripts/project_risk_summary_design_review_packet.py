"""Build the project.risk.summary design-review packet."""

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
    project_risk_summary_implementation_gate,
    project_risk_summary_implementation_plan_check,
    project_risk_summary_preimplementation_check,
    project_risk_summary_proposal_check,
    project_risk_summary_review_handoff_check,
)

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/project-risk-summary-design-review")
PROJECT_MARKERS = ("pyproject.toml", "Makefile", "tool-manifests.lock.json")
DOCS = {
    "02_NEXT_CAPABILITY_READINESS.md": Path("docs/codex/next-capability-readiness.md"),
    "03_PROJECT_RISK_SUMMARY_SELECTION.md": Path("docs/codex/v3-project-risk-summary-selection.md"),
    "04_PROJECT_RISK_SUMMARY_PROPOSAL.md": Path(
        "docs/codex/capability-proposals/project-risk-summary.md"
    ),
    "05_PROJECT_RISK_SUMMARY_IMPLEMENTATION_PLAN.md": Path(
        "docs/codex/capability-implementation-plans/project-risk-summary.md"
    ),
    "06_PROJECT_RISK_SUMMARY_IMPLEMENTATION_BOUNDARY.md": Path(
        "docs/codex/v3-project-risk-summary-implementation.md"
    ),
    "07_PROJECT_RISK_SUMMARY_FIXTURE_PLAN.md": Path(
        "docs/codex/project-risk-summary-fixture-plan.md"
    ),
    "08_PROJECT_RISK_SUMMARY_NEGATIVE_TRANSCRIPTS.md": Path(
        "docs/codex/project-risk-summary-negative-transcripts.md"
    ),
    "09_PROJECT_RISK_SUMMARY_SOURCE_REVIEW.md": Path(
        "docs/codex/v3-project-risk-summary-source-review.md"
    ),
}


class ProjectRiskSummaryDesignReviewPacketError(RuntimeError):
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
    except ProjectRiskSummaryDesignReviewPacketError as exc:
        print(f"project.risk.summary design-review packet failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built project.risk.summary design-review packet at {output_dir}")
    return 0


def build_packet(*, repo_root: Path, output_dir: Path, allow_dirty: bool = False) -> Path:
    _require_project_root(repo_root)
    commit = _git(repo_root, ["rev-parse", "HEAD"])
    dirty = bool(_git(repo_root, ["status", "--short"]))
    if dirty and not allow_dirty:
        raise ProjectRiskSummaryDesignReviewPacketError(
            "working tree is dirty; commit before design-review handoff"
        )

    proposal = project_risk_summary_proposal_check.build_report(repo_root)
    plan = project_risk_summary_implementation_plan_check.build_report(repo_root)
    implementation_gate = project_risk_summary_implementation_gate.build_report(repo_root)
    preimplementation = project_risk_summary_preimplementation_check.build_report(repo_root)
    review_handoff = project_risk_summary_review_handoff_check.build_report(repo_root)
    readiness = next_capability_readiness.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures = [
        *(f"proposal check: {failure}" for failure in proposal["failures"]),
        *(f"implementation-plan check: {failure}" for failure in plan["failures"]),
        *(f"implementation gate: {failure}" for failure in implementation_gate["failures"]),
        *(f"preimplementation check: {failure}" for failure in preimplementation["failures"]),
        *(f"review handoff check: {failure}" for failure in review_handoff["failures"]),
        *(f"next-capability readiness: {failure}" for failure in readiness["failures"]),
        *(f"no-new-powers guardrail: {failure}" for failure in no_new_powers["failures"]),
    ]
    if failures:
        raise ProjectRiskSummaryDesignReviewPacketError("; ".join(failures))

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context = {
        "commit": commit,
        "dirty": dirty,
        "proposal": proposal,
        "plan": plan,
        "implementation_gate": implementation_gate,
        "preimplementation": preimplementation,
        "review_handoff": review_handoff,
        "readiness": readiness,
        "no_new_powers": no_new_powers,
    }
    files = {
        "00_PROJECT_RISK_SUMMARY_DESIGN_REVIEW_INDEX.md": _index(context),
        "01_PROJECT_RISK_SUMMARY_DESIGN_REVIEW_PROMPT.md": _prompt(context),
        "10_GATE_AND_RISK_EVIDENCE.md": _gate_evidence(context),
        "11_REVIEW_INTAKE_AND_NEXT_STEPS.md": _intake(context),
    }
    for name, source in DOCS.items():
        files[name] = (repo_root / source).read_text(encoding="utf-8")
    for name, content in files.items():
        (output_dir / name).write_text(content.rstrip() + "\n", encoding="utf-8")
    _write_json(
        output_dir / "project-risk-summary-design-review-artifact-hashes.json",
        _hashes(output_dir),
    )
    return output_dir


def _require_project_root(repo_root: Path) -> None:
    missing = [marker for marker in PROJECT_MARKERS if not repo_root.joinpath(marker).exists()]
    if missing:
        raise ProjectRiskSummaryDesignReviewPacketError(
            "must be run from the Ithildin repo root; missing markers: " + ", ".join(missing)
        )


def _index(context: dict[str, Any]) -> str:
    return f"""# project.risk.summary Design Review Packet

This packet asks for design review of the next proposed read-only local metadata capability. It
does not approve implementation.

## Boundary

- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Capability: `project.risk.summary`.
- Scope: design-only proposal and implementation-planning packet.
- Implementation status: blocked.
- Tool count: `{context["no_new_powers"]["tool_count"]}`.
- New governed tool powers: no-go.

## Attachments

1. `00_PROJECT_RISK_SUMMARY_DESIGN_REVIEW_INDEX.md`
2. `01_PROJECT_RISK_SUMMARY_DESIGN_REVIEW_PROMPT.md`
3. `02_NEXT_CAPABILITY_READINESS.md`
4. `03_PROJECT_RISK_SUMMARY_SELECTION.md`
5. `04_PROJECT_RISK_SUMMARY_PROPOSAL.md`
6. `05_PROJECT_RISK_SUMMARY_IMPLEMENTATION_PLAN.md`
7. `06_PROJECT_RISK_SUMMARY_IMPLEMENTATION_BOUNDARY.md`
8. `07_PROJECT_RISK_SUMMARY_FIXTURE_PLAN.md`
9. `08_PROJECT_RISK_SUMMARY_NEGATIVE_TRANSCRIPTS.md`
10. `09_PROJECT_RISK_SUMMARY_SOURCE_REVIEW.md`
11. `10_GATE_AND_RISK_EVIDENCE.md`
12. `11_REVIEW_INTAKE_AND_NEXT_STEPS.md`
13. `project-risk-summary-design-review-artifact-hashes.json`

## What This Packet Does Not Prove

This packet does not add a manifest, executor, policy rule, MCP exposure, API behavior, UI behavior,
runtime behavior, filenames, raw paths, file contents, dependency names, package names, CVE IDs,
secret names/values, command/script values, scanner execution, vulnerability findings, network
access, compliance claims, security assurance, or future governed tool powers. It records only that
the implementation boundary may be considered in a later explicit runtime sprint.
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# project.risk.summary Design Review Prompt

You are reviewing Ithildin's next design-only read-only capability proposal. Treat this as design
review only. Do not approve implementation in this review. At most, say whether a separate
implementation decision sprint may be considered later.

Reviewed commit: `{context["commit"]}`
Capability: `project.risk.summary`
Finding namespace: `EXT-DESIGN-PRISK-###`

Please review:

- whether the proposal stays design-only and avoids manifest/executor/policy/MCP/runtime changes;
- whether count-only risk-signal posture metadata is useful enough without filenames, raw paths,
  file contents, dependency names, package names, CVE IDs, secret names/values, commands, scanner
  output, or vulnerability findings;
- whether scanner output, scanner execution, and vulnerability findings remain explicit non-goals;
- whether the future traversal and category allowlists preserve existing workspace and path safety;
- whether policy, audit, UI/review, negative transcript, resource-limit, accepted-risk, and
  no-new-powers evidence are sufficient for a future implementation go/no-go decision;
- whether this candidate should remain next, be narrowed further, or be replaced.

Required answer:

- Overall judgment.
- Blocking design findings, if any.
- Should-fix design findings, if any.
- Whether a separate implementation-decision sprint may be considered later.
- What must remain deferred.

Use finding IDs `EXT-DESIGN-PRISK-###` for actionable findings.
"""


def _gate_evidence(context: dict[str, Any]) -> str:
    return f"""# project.risk.summary Gate And Risk Evidence

## Proposal Check

```json
{json.dumps(context["proposal"], indent=2, sort_keys=True)}
```

## Implementation-Plan Check

```json
{json.dumps(context["plan"], indent=2, sort_keys=True)}
```

## Implementation Boundary Gate

```json
{json.dumps(context["implementation_gate"], indent=2, sort_keys=True)}
```

## Preimplementation Fixture Check

```json
{json.dumps(context["preimplementation"], indent=2, sort_keys=True)}
```

## Review Handoff Check

```json
{json.dumps(context["review_handoff"], indent=2, sort_keys=True)}
```

## Next-Capability Readiness

```json
{json.dumps(context["readiness"], indent=2, sort_keys=True)}
```

## No-New-Powers Guardrail

```json
{json.dumps(context["no_new_powers"], indent=2, sort_keys=True)}
```
"""


def _intake(context: dict[str, Any]) -> str:
    return f"""# Review Intake And Next Steps

If review returns findings, normalize them with the existing finding-intake workflow and keep
implementation blocked until a later explicit decision.

Suggested command context:

- `make project-risk-summary-proposal-check`
- `make project-risk-summary-implementation-plan-check`
- `make project-risk-summary-implementation-gate`
- `make project-risk-summary-preimplementation-check`
- `make project-risk-summary-review-handoff-check`
- `make project-risk-summary-design-review-packet`
- `make project-risk-summary-source-review-bundle`
- `make release-check`

Current reviewed commit: `{context["commit"]}`.

If review finds no blocking design issues, the next sprint may draft an implementation decision.
It still must not add a manifest, executor, policy rule, MCP exposure, or runtime behavior unless
that later sprint explicitly records approval for this one bounded count-only capability.
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

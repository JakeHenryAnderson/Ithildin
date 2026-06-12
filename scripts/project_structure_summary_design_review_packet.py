"""Build the project.structure.summary design-review packet."""

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
    project_structure_summary_proposal_check,
)

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/project-structure-summary-design-review")
PROJECT_MARKERS = ("pyproject.toml", "Makefile", "tool-manifests.lock.json")
DOCS = {
    "02_NEXT_CAPABILITY_READINESS.md": Path("docs/codex/next-capability-readiness.md"),
    "03_PROJECT_STRUCTURE_SUMMARY_SELECTION.md": Path(
        "docs/codex/v3-project-structure-summary-selection.md"
    ),
    "04_PROJECT_STRUCTURE_SUMMARY_PROPOSAL.md": Path(
        "docs/codex/capability-proposals/project-structure-summary.md"
    ),
    "05_READ_ONLY_LOCAL_METADATA_CONTRACT.md": Path(
        "docs/codex/read-only-local-metadata-contract.md"
    ),
}


class ProjectStructureSummaryDesignReviewPacketError(RuntimeError):
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
    except ProjectStructureSummaryDesignReviewPacketError as exc:
        print(f"project.structure.summary design-review packet failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built project.structure.summary design-review packet at {output_dir}")
    return 0


def build_packet(*, repo_root: Path, output_dir: Path, allow_dirty: bool = False) -> Path:
    _require_project_root(repo_root)
    commit = _git(repo_root, ["rev-parse", "HEAD"])
    dirty = bool(_git(repo_root, ["status", "--short"]))
    if dirty and not allow_dirty:
        raise ProjectStructureSummaryDesignReviewPacketError(
            "working tree is dirty; commit before design-review handoff"
        )

    proposal = project_structure_summary_proposal_check.build_report(repo_root)
    readiness = next_capability_readiness.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures = [
        *(f"proposal check: {failure}" for failure in proposal["failures"]),
        *(f"next-capability readiness: {failure}" for failure in readiness["failures"]),
        *(f"no-new-powers guardrail: {failure}" for failure in no_new_powers["failures"]),
    ]
    if failures:
        raise ProjectStructureSummaryDesignReviewPacketError("; ".join(failures))

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context = {
        "commit": commit,
        "dirty": dirty,
        "proposal": proposal,
        "readiness": readiness,
        "no_new_powers": no_new_powers,
    }
    files = {
        "00_PROJECT_STRUCTURE_SUMMARY_DESIGN_REVIEW_INDEX.md": _index(context),
        "01_PROJECT_STRUCTURE_SUMMARY_DESIGN_REVIEW_PROMPT.md": _prompt(context),
        "06_GATE_AND_RISK_EVIDENCE.md": _gate_evidence(context),
        "07_REVIEW_INTAKE_AND_NEXT_STEPS.md": _intake(context),
    }
    for name, source in DOCS.items():
        files[name] = (repo_root / source).read_text(encoding="utf-8")
    for name, content in files.items():
        (output_dir / name).write_text(content.rstrip() + "\n", encoding="utf-8")
    _write_json(
        output_dir / "project-structure-summary-design-review-artifact-hashes.json",
        _hashes(output_dir),
    )
    return output_dir


def _require_project_root(repo_root: Path) -> None:
    missing = [marker for marker in PROJECT_MARKERS if not repo_root.joinpath(marker).exists()]
    if missing:
        raise ProjectStructureSummaryDesignReviewPacketError(
            "must be run from the Ithildin repo root; missing markers: " + ", ".join(missing)
        )


def _index(context: dict[str, Any]) -> str:
    return f"""# project.structure.summary Design Review Packet

This packet asks for design review of the next proposed read-only local metadata capability. It
does not approve implementation.

## Boundary

- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Capability: `project.structure.summary`.
- Scope: design-only proposal.
- Implementation status: blocked.
- Tool count: `{context["no_new_powers"]["tool_count"]}`.
- New governed tool powers: no-go.

## Attachments

1. `00_PROJECT_STRUCTURE_SUMMARY_DESIGN_REVIEW_INDEX.md`
2. `01_PROJECT_STRUCTURE_SUMMARY_DESIGN_REVIEW_PROMPT.md`
3. `02_NEXT_CAPABILITY_READINESS.md`
4. `03_PROJECT_STRUCTURE_SUMMARY_SELECTION.md`
5. `04_PROJECT_STRUCTURE_SUMMARY_PROPOSAL.md`
6. `05_READ_ONLY_LOCAL_METADATA_CONTRACT.md`
7. `06_GATE_AND_RISK_EVIDENCE.md`
8. `07_REVIEW_INTAKE_AND_NEXT_STEPS.md`
9. `project-structure-summary-design-review-artifact-hashes.json`

## What This Packet Does Not Prove

This packet does not add or approve a manifest, executor, policy rule, MCP exposure, API behavior,
UI behavior, runtime behavior, recursive listing disclosure, file-content access, package-manager
execution, registry/network access, source-code analysis, compliance claims, or future governed
tool powers.
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# project.structure.summary Design Review Prompt

You are reviewing Ithildin's next design-only read-only capability proposal. Treat this as design
review only. Do not approve implementation in this review. At most, say whether a separate
implementation-planning sprint may be considered later.

Reviewed commit: `{context["commit"]}`
Capability: `project.structure.summary`
Finding namespace: `EXT-DESIGN-PSS-###`

Please review:

- whether the proposal stays design-only and avoids manifest/executor/policy/MCP/runtime changes;
- whether structural counts and allowlisted labels are useful enough without raw recursive listings,
  file contents, raw sensitive paths, package names, dependency names, or code search;
- whether the filesystem-derived parser contract preserves existing workspace, symlink, hardlink,
  hidden/sensitive path, and safe-error boundaries;
- whether policy, audit, UI/review, negative transcript, resource-limit, accepted-risk, and
  no-new-powers evidence are sufficient for a future implementation-planning decision;
- whether this candidate should remain next, be narrowed further, or be replaced.

Required answer:

- Overall judgment.
- Blocking design findings, if any.
- Should-fix design findings, if any.
- Whether a separate implementation-planning sprint may be considered later.
- What must remain deferred.

Use finding IDs `EXT-DESIGN-PSS-###` for actionable findings.
"""


def _gate_evidence(context: dict[str, Any]) -> str:
    return f"""# project.structure.summary Gate And Risk Evidence

## Proposal Check

```json
{json.dumps(context["proposal"], indent=2, sort_keys=True)}
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

- `make project-structure-summary-proposal-check`
- `make project-structure-summary-design-review-packet`
- `make release-check`

Current reviewed commit: `{context["commit"]}`.

If review finds no blocking design issues, the next sprint may draft an implementation-planning
packet. It still must not add a manifest, executor, policy rule, MCP exposure, or runtime behavior
unless that later sprint explicitly records approval for this one bounded structure-summary
capability.
"""


def _hashes(output_dir: Path) -> list[dict[str, Any]]:
    entries = []
    for path in sorted(output_dir.iterdir()):
        if path.name == "project-structure-summary-design-review-artifact-hashes.json":
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


def _git(repo_root: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())

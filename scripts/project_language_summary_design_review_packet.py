"""Build the project.language.summary design-review packet."""

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
    project_language_summary_implementation_plan_check,
    project_language_summary_proposal_check,
)

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/project-language-summary-design-review")
PROJECT_MARKERS = ("pyproject.toml", "Makefile", "tool-manifests.lock.json")
DOCS = {
    "02_NEXT_CAPABILITY_READINESS.md": Path("docs/codex/next-capability-readiness.md"),
    "03_PROJECT_LANGUAGE_SUMMARY_SELECTION.md": Path(
        "docs/codex/v3-project-language-summary-selection.md"
    ),
    "04_PROJECT_LANGUAGE_SUMMARY_PROPOSAL.md": Path(
        "docs/codex/capability-proposals/project-language-summary.md"
    ),
    "05_PROJECT_LANGUAGE_SUMMARY_IMPLEMENTATION_PLAN.md": Path(
        "docs/codex/capability-implementation-plans/project-language-summary.md"
    ),
    "06_READ_ONLY_LOCAL_METADATA_CONTRACT.md": Path(
        "docs/codex/read-only-local-metadata-contract.md"
    ),
    "07_METADATA_PRIVACY_POLICY.md": Path("docs/codex/metadata-privacy-policy.md"),
}


class ProjectLanguageSummaryDesignReviewPacketError(RuntimeError):
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
    except ProjectLanguageSummaryDesignReviewPacketError as exc:
        print(f"project.language.summary design-review packet failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built project.language.summary design-review packet at {output_dir}")
    return 0


def build_packet(*, repo_root: Path, output_dir: Path, allow_dirty: bool = False) -> Path:
    _require_project_root(repo_root)
    commit = _git(repo_root, ["rev-parse", "HEAD"])
    dirty = bool(_git(repo_root, ["status", "--short"]))
    if dirty and not allow_dirty:
        raise ProjectLanguageSummaryDesignReviewPacketError(
            "working tree is dirty; commit before design-review handoff"
        )

    proposal = project_language_summary_proposal_check.build_report(repo_root)
    plan = project_language_summary_implementation_plan_check.build_report(repo_root)
    readiness = next_capability_readiness.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures = [
        *(f"proposal check: {failure}" for failure in proposal["failures"]),
        *(f"implementation plan check: {failure}" for failure in plan["failures"]),
        *(f"next-capability readiness: {failure}" for failure in readiness["failures"]),
        *(f"no-new-powers guardrail: {failure}" for failure in no_new_powers["failures"]),
    ]
    if failures:
        raise ProjectLanguageSummaryDesignReviewPacketError("; ".join(failures))

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context = {
        "commit": commit,
        "dirty": dirty,
        "proposal": proposal,
        "plan": plan,
        "readiness": readiness,
        "no_new_powers": no_new_powers,
    }
    files = {
        "00_PROJECT_LANGUAGE_SUMMARY_DESIGN_REVIEW_INDEX.md": _index(context),
        "01_PROJECT_LANGUAGE_SUMMARY_DESIGN_REVIEW_PROMPT.md": _prompt(context),
        "08_GATE_AND_RISK_EVIDENCE.md": _gate_evidence(context),
        "09_REVIEW_INTAKE_AND_NEXT_STEPS.md": _intake(),
    }
    for name, source in DOCS.items():
        files[name] = (repo_root / source).read_text(encoding="utf-8")
    for name, content in files.items():
        (output_dir / name).write_text(content.rstrip() + "\n", encoding="utf-8")
    _write_json(
        output_dir / "project-language-summary-design-review-artifact-hashes.json",
        _hashes(output_dir),
    )
    return output_dir


def _require_project_root(repo_root: Path) -> None:
    missing = [marker for marker in PROJECT_MARKERS if not repo_root.joinpath(marker).exists()]
    if missing:
        raise ProjectLanguageSummaryDesignReviewPacketError(
            "must be run from the Ithildin repo root; missing markers: " + ", ".join(missing)
        )


def _index(context: dict[str, Any]) -> str:
    return f"""# project.language.summary Design Review Packet

This packet asks for design review of the next proposed read-only local metadata capability. It
does not approve implementation.

## Boundary

- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Capability: `project.language.summary`.
- Scope: design-only proposal.
- Implementation status: blocked.
- Tool count: `{context["no_new_powers"]["tool_count"]}`.
- New governed tool powers: no-go.

## Attachments

1. `00_PROJECT_LANGUAGE_SUMMARY_DESIGN_REVIEW_INDEX.md`
2. `01_PROJECT_LANGUAGE_SUMMARY_DESIGN_REVIEW_PROMPT.md`
3. `02_NEXT_CAPABILITY_READINESS.md`
4. `03_PROJECT_LANGUAGE_SUMMARY_SELECTION.md`
5. `04_PROJECT_LANGUAGE_SUMMARY_PROPOSAL.md`
6. `05_PROJECT_LANGUAGE_SUMMARY_IMPLEMENTATION_PLAN.md`
7. `06_READ_ONLY_LOCAL_METADATA_CONTRACT.md`
8. `07_METADATA_PRIVACY_POLICY.md`
9. `08_GATE_AND_RISK_EVIDENCE.md`
10. `09_REVIEW_INTAKE_AND_NEXT_STEPS.md`
11. `project-language-summary-design-review-artifact-hashes.json`

## What This Packet Does Not Prove

This packet does not add a manifest, executor, policy rule, MCP exposure, API behavior, UI
behavior, runtime behavior, language detector execution, language file names,
file-content access, package-manager execution, registry/network access, coverage claims, or broad
governed tool powers.
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# project.language.summary Design Review Prompt

You are reviewing Ithildin's next design-only read-only capability proposal. Treat this as design
review only. Do not approve implementation in this review. At most, say whether a separate
implementation-planning sprint may be considered later.

Reviewed commit: `{context["commit"]}`
Capability: `project.language.summary`
Finding namespace: `EXT-DESIGN-PLS-###`

Please review:

- whether the proposal stays design-only and avoids manifest/executor/policy/MCP/runtime changes;
- whether count-only language metadata and allowlisted labels are useful enough without
  language file names, raw paths, file contents, raw extensions, scripts, coverage,
  pass/fail state, or command output;
- whether the filesystem-derived parser contract preserves existing workspace, symlink, hardlink,
  hidden/sensitive path, and safe-error boundaries;
- whether the proposal defines enough policy, audit, UI/review, negative transcript,
  resource-limit, accepted-risk, and no-new-powers evidence for a later implementation plan;
- whether this candidate should remain next, be narrowed further, or be replaced.

Required answer:

- Overall judgment.
- Blocking design findings, if any.
- Should-fix design findings, if any.
- Whether a separate implementation-planning sprint may be considered later.
- What must remain deferred.

Use finding IDs `EXT-DESIGN-PLS-###` for actionable findings.
"""


def _gate_evidence(context: dict[str, Any]) -> str:
    return f"""# project.language.summary Gate And Risk Evidence

## Proposal Check

```json
{json.dumps(context["proposal"], indent=2, sort_keys=True)}
```

## Implementation Plan Check

```json
{json.dumps(context["plan"], indent=2, sort_keys=True)}
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


def _intake() -> str:
    return """# project.language.summary Intake And Next Steps

If design review records findings, intake them with finding IDs `EXT-DESIGN-PLS-###` before any
implementation-planning work. If there are no blocking design findings, the next sprint may draft
an implementation-planning packet only; it still must not add a manifest, executor, policy rule,
MCP exposure, API behavior, UI behavior, or runtime behavior without a separate implementation
decision.
"""


def _hashes(output_dir: Path) -> list[dict[str, Any]]:
    records = []
    for path in sorted(output_dir.iterdir()):
        if path.name.endswith("artifact-hashes.json"):
            continue
        data = path.read_bytes()
        records.append(
            {
                "path": path.name,
                "sha256": f"sha256:{hashlib.sha256(data).hexdigest()}",
                "bytes": len(data),
            }
        )
    return records


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git(repo_root: Path, args: list[str]) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if process.returncode != 0:
        raise ProjectLanguageSummaryDesignReviewPacketError(process.stderr.strip())
    return process.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())

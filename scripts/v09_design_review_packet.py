"""Build the v0.9 git.show.commit_metadata design-review packet."""

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
    accepted_risk_register,
    git_commit_metadata_proposal_check,
    no_new_powers_guardrail,
    v09_design_only_gate,
)

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v0.9/git-commit-metadata-design-review")
PROJECT_MARKERS = ("pyproject.toml", "Makefile", "tool-manifests.lock.json")
DOCS = {
    "02_V08_FINAL_DECISION_PACKET.md": Path("docs/codex/v0.8-final-decision-packet.md"),
    "03_V09_DESIGN_ONLY_CHARTER.md": Path("docs/codex/v0.9-design-only-boundary-charter.md"),
    "04_GIT_COMMIT_METADATA_PROPOSAL.md": Path(
        "docs/codex/capability-proposals/git-show-commit-metadata.md"
    ),
}


class DesignReviewPacketError(RuntimeError):
    """Raised when the v0.9 design-review packet cannot be built."""


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
    except DesignReviewPacketError as exc:
        print(f"v0.9 design-review packet failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built v0.9 design-review packet at {output_dir}")
    return 0


def build_packet(*, repo_root: Path, output_dir: Path, allow_dirty: bool = False) -> Path:
    _require_project_root(repo_root)
    commit = _git(repo_root, ["rev-parse", "HEAD"])
    dirty = bool(_git(repo_root, ["status", "--short"]))
    if dirty and not allow_dirty:
        raise DesignReviewPacketError(
            "working tree is dirty; commit before v0.9 design-review handoff"
        )

    design_gate = v09_design_only_gate.build_report(repo_root)
    proposal_check = git_commit_metadata_proposal_check.build_report(repo_root)
    risks = accepted_risk_register.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures = [
        *(f"v0.9 design-only gate: {failure}" for failure in design_gate["failures"]),
        *(f"proposal check: {failure}" for failure in proposal_check["failures"]),
        *(f"accepted-risk register: {failure}" for failure in risks["failures"]),
        *(f"no-new-powers guardrail: {failure}" for failure in no_new_powers["failures"]),
    ]
    if failures:
        raise DesignReviewPacketError("; ".join(failures))

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context = {
        "commit": commit,
        "dirty": dirty,
        "design_gate": design_gate,
        "proposal_check": proposal_check,
        "accepted_risks": risks,
        "no_new_powers": no_new_powers,
    }
    files = {
        "00_V09_DESIGN_REVIEW_INDEX.md": _index(context),
        "01_V09_DESIGN_REVIEW_PROMPT.md": _prompt(context),
        "05_GATE_AND_RISK_EVIDENCE.md": _gate_evidence(context),
        "06_REVIEW_INTAKE_AND_NEXT_STEPS.md": _intake(context),
    }
    for name, source in DOCS.items():
        files[name] = (repo_root / source).read_text(encoding="utf-8")
    for name, content in files.items():
        (output_dir / name).write_text(content.rstrip() + "\n", encoding="utf-8")
    _write_json(output_dir / "v09-design-review-artifact-hashes.json", _hashes(output_dir))
    return output_dir


def _require_project_root(repo_root: Path) -> None:
    missing = [marker for marker in PROJECT_MARKERS if not repo_root.joinpath(marker).exists()]
    if missing:
        raise DesignReviewPacketError(
            "must be run from the Ithildin repo root; missing markers: " + ", ".join(missing)
        )


def _index(context: dict[str, Any]) -> str:
    return f"""# v0.9 git.show.commit_metadata Design Review Packet

This packet asks GPT 5.5 Pro / human review to evaluate a design-only capability proposal. It does
not request implementation approval.

## Boundary

- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Capability: `git.show.commit_metadata`.
- Scope: design-only proposal.
- Implementation status: blocked.
- New governed tool powers: no-go.
- Tool count: `{context["no_new_powers"]["tool_count"]}`.

## Attachments

1. `00_V09_DESIGN_REVIEW_INDEX.md`
2. `01_V09_DESIGN_REVIEW_PROMPT.md`
3. `02_V08_FINAL_DECISION_PACKET.md`
4. `03_V09_DESIGN_ONLY_CHARTER.md`
5. `04_GIT_COMMIT_METADATA_PROPOSAL.md`
6. `05_GATE_AND_RISK_EVIDENCE.md`
7. `06_REVIEW_INTAKE_AND_NEXT_STEPS.md`
8. `v09-design-review-artifact-hashes.json`

## What This Packet Does Not Prove

This packet does not add or approve a tool manifest, executor, policy rule, MCP exposure, runtime
behavior, public/security-product positioning, production identity, remote MCP, shell/Docker/
Kubernetes/browser tooling, arbitrary HTTP, broad filesystem writes, or plugin SDK work.
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# v0.9 Design-Only Capability Review Prompt

You are reviewing Ithildin's first design-only capability proposal after the v0.8 final decision.
Treat this as design review only. Do not approve implementation in this review. At most, say
whether a separate implementation-planning sprint may be considered later.

Reviewed commit: `{context["commit"]}`
Capability: `git.show.commit_metadata`
Finding namespace: `EXT-DESIGN-GIT-###`

Please review:

- whether the proposal stays design-only and avoids manifest/executor/policy/MCP/runtime changes;
- whether `git.show.commit_metadata` is an appropriate first design-only candidate;
- whether the ref resolution policy is safe enough for later implementation planning;
- whether changed-file metadata parsing avoids file contents, raw diffs, raw stderr, credentials,
  and shell interpretation;
- whether bounded commit subject/body, author identity, committer identity, and email metadata
  create secret, privacy, or social-engineering risks that need stronger limits before planning;
- whether policy, audit, UI/review, negative transcript, resource-limit, accepted-risk, and
  no-new-powers evidence are sufficient for a future implementation go/no-go decision.

Required answer:

- Overall judgment.
- Blocking design findings, if any.
- Should-fix design findings, if any.
- Whether a separate implementation-planning sprint may be considered later.
- What must remain deferred.

Use finding IDs `EXT-DESIGN-GIT-###` for actionable findings.
"""


def _gate_evidence(context: dict[str, Any]) -> str:
    return f"""# v0.9 Gate And Risk Evidence

## v0.9 Design-Only Gate

```json
{json.dumps(context["design_gate"], indent=2, sort_keys=True)}
```

## Proposal Check

```json
{json.dumps(context["proposal_check"], indent=2, sort_keys=True)}
```

## No-New-Powers Guardrail

```json
{json.dumps(context["no_new_powers"], indent=2, sort_keys=True)}
```

## Accepted-Risk Register

```json
{json.dumps(context["accepted_risks"], indent=2, sort_keys=True)}
```
"""


def _intake(context: dict[str, Any]) -> str:
    return f"""# Review Intake And Next Steps

If GPT 5.5 Pro / human review returns findings, normalize them with the existing external-response
intake workflow and keep implementation blocked until a later explicit decision.

Suggested command context:

- `make v09-design-only-gate`
- `make git-commit-metadata-proposal-check`
- `make v09-design-review-packet`
- `make release-check`

Current reviewed commit: `{context["commit"]}`.

If review finds no blocking design issues, the next sprint may draft an implementation-planning
proposal. It still must not add a manifest, executor, policy rule, MCP exposure, or runtime behavior
until a separate implementation decision is approved.
"""


def _hashes(output_dir: Path) -> list[dict[str, Any]]:
    entries = []
    for path in sorted(output_dir.iterdir()):
        if path.name == "v09-design-review-artifact-hashes.json":
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

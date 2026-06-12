"""Build a focused operator workbench evidence packet."""

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
    demo_observed_summary,
    demo_readiness_summary,
    demo_reset_guide,
    demo_state_report,
    operator_demo_guide,
    operator_demo_walkthrough,
    workbench_demo_smoke,
)

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/operator-workbench")
HASH_MANIFEST = "operator-workbench-artifact-hashes.json"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
DOCS = [
    Path("docs/codex/operator-workbench-readiness.md"),
    Path("docs/codex/agent-run-model-contract.md"),
    Path("docs/codex/agent-run-evidence-contract.md"),
    Path("docs/codex/agent-run-evidence-export-implementation.md"),
    Path("docs/codex/operator-managed-sandbox-demo-guide.md"),
    Path("docs/codex/live-demo-runbook.md"),
    Path("docs/codex/incident-reconstruction-guide.md"),
]
COMMANDS = [
    ["make", "demo-operator-walkthrough"],
    ["make", "operator-demo-guide"],
    ["make", "demo-state-report"],
    ["make", "demo-reset-guide"],
    ["make", "demo-readiness-summary"],
    ["make", "workbench-readiness"],
    ["make", "demo-workbench-smoke"],
    ["make", "live-demo-preflight"],
    ["make", "live-demo-status"],
    ["make", "live-demo-smoke"],
    ["make", "live-demo-evidence-summary"],
    ["make", "operator-sandbox-demo-packet"],
    ["make", "agent-run-correlation-packet"],
    ["make", "no-new-powers-guardrail"],
    ["make", "tool-surface-invariant-gate"],
]
POINTERS = [
    Path("var/review-packets/v3/live-demo"),
    Path("var/review-packets/v3/operator-sandbox-demo"),
    Path("var/review-packets/v3/agent-run-correlation"),
    Path("var/review-packets/v0.2/signed-evidence-demo"),
    Path("var/review-packets/v0.2/negative-review-transcripts"),
    Path("var/review-packets/v0.2/GPT-5.5-Pro-consolidated"),
]


class WorkbenchEvidencePacketError(RuntimeError):
    """Raised when the operator workbench packet cannot be built."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--skip-commands", action="store_true")
    args = parser.parse_args()
    try:
        output_dir = build_packet(
            repo_root=Path.cwd().resolve(),
            output_dir=args.output_dir,
            allow_dirty=args.allow_dirty,
            run_commands=not args.skip_commands,
        )
    except WorkbenchEvidencePacketError as exc:
        print(f"operator workbench packet failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built operator workbench evidence packet at {output_dir}")
    return 0


def build_packet(
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
        raise WorkbenchEvidencePacketError(
            "working tree is dirty; commit before operator workbench handoff"
        )
    preserved_observed_artifacts = _preserve_observed_artifacts(output_dir)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    _restore_observed_artifacts(output_dir, preserved_observed_artifacts)
    workbench_demo_smoke.build_transcript(
        repo_root=repo_root,
        output=output_dir / "WORKBENCH_DEMO_SMOKE.md",
        run_commands=run_commands,
    )
    demo_readiness_summary.build_summary(
        repo_root=repo_root,
        output=output_dir / "DEMO_READINESS_SUMMARY.md",
        probe_endpoints=run_commands,
    )
    operator_demo_guide.build_guide(
        repo_root=repo_root,
        output=output_dir / "OPERATOR_DEMO_GUIDE.md",
        probe_endpoints=run_commands,
    )
    demo_state_report.build_report(
        repo_root=repo_root,
        output=output_dir / "DEMO_STATE_REPORT.md",
        probe_endpoints=run_commands,
    )
    demo_reset_guide.build_guide(
        repo_root=repo_root,
        output=output_dir / "DEMO_RESET_GUIDE.md",
    )
    demo_observed_summary.build_summary(
        result=output_dir / "DEMO_FLOW_RESULT.md",
        run_export=output_dir / "RUN_EVIDENCE_EXPORT.json",
        output=output_dir / "DEMO_OBSERVED_SUMMARY.md",
    )
    operator_demo_walkthrough.build_walkthrough(
        repo_root=repo_root,
        output=output_dir / "OPERATOR_DEMO_WALKTHROUGH.md",
    )

    context = {"commit": commit, "dirty": dirty, "run_commands": run_commands}
    files = {
        "00_OPERATOR_WORKBENCH_INDEX.md": _index(context),
        "01_OPERATOR_WORKBENCH_REVIEW_PROMPT.md": _prompt(context),
        "02_OPERATOR_WORKBENCH_DOCS.md": _bundle_docs(repo_root),
        "03_OPERATOR_WORKBENCH_COMMAND_EVIDENCE.md": _command_evidence(run_commands),
        "04_OPERATOR_WORKBENCH_ARTIFACT_POINTERS.md": _artifact_pointers(repo_root),
        "05_OPERATOR_WORKBENCH_SMOKE.md": _observed_smoke(output_dir),
        "06_DEMO_READINESS_SUMMARY.md": _observed_readiness(output_dir),
        "07_WORKBENCH_DEMO_STORY.md": _demo_story(context),
        "08_OPERATOR_DEMO_GUIDE.md": _observed_operator_guide(output_dir),
        "09_DEMO_STATE_REPORT.md": _observed_state_report(output_dir),
        "10_DEMO_RESET_GUIDE.md": _observed_reset_guide(output_dir),
        "11_DEMO_OBSERVED_SUMMARY.md": _observed_demo_summary(output_dir),
        "12_OPERATOR_DEMO_WALKTHROUGH.md": _observed_operator_walkthrough(output_dir),
        "WORKBENCH_DEMO_INDEX.md": _demo_index(output_dir, context),
    }
    for relative, content in files.items():
        (output_dir / relative).write_text(content.rstrip() + "\n", encoding="utf-8")
    _write_json(output_dir / HASH_MANIFEST, _hashes(output_dir))
    return output_dir


def _preserve_observed_artifacts(output_dir: Path) -> dict[str, str]:
    preserved: dict[str, str] = {}
    for name in ["DEMO_FLOW_RESULT.md", "RUN_EVIDENCE_EXPORT.json", "DEMO_OBSERVED_SUMMARY.md"]:
        path = output_dir / name
        if path.is_file():
            preserved[name] = path.read_text(encoding="utf-8")
    return preserved


def _restore_observed_artifacts(output_dir: Path, artifacts: dict[str, str]) -> None:
    for name, content in artifacts.items():
        (output_dir / name).write_text(content, encoding="utf-8")


def _index(context: dict[str, Any]) -> str:
    return f"""# Operator Workbench Evidence Packet

This packet packages the local-preview operator workbench story: System Trust, registered tools,
approval evidence, Agent Run operations, audit status, live-demo artifacts, operator-managed
sandbox/workspace posture, and read-only evidence export.

## Boundary

- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Command evidence executed: `{str(context["run_commands"]).lower()}`.
- tool count remains `18`.
- No run controls, sandbox orchestration, SIEM adapters, production identity, runtime Postgres,
  hosted telemetry, remote MCP, shell, Docker, Kubernetes, browser automation, arbitrary HTTP,
  broad filesystem writes, plugin SDK work, or new governed tool powers are added or approved.

## Artifacts

1. `00_OPERATOR_WORKBENCH_INDEX.md`
2. `01_OPERATOR_WORKBENCH_REVIEW_PROMPT.md`
3. `02_OPERATOR_WORKBENCH_DOCS.md`
4. `03_OPERATOR_WORKBENCH_COMMAND_EVIDENCE.md`
5. `04_OPERATOR_WORKBENCH_ARTIFACT_POINTERS.md`
6. `05_OPERATOR_WORKBENCH_SMOKE.md`
7. `06_DEMO_READINESS_SUMMARY.md`
8. `07_WORKBENCH_DEMO_STORY.md`
9. `08_OPERATOR_DEMO_GUIDE.md`
10. `09_DEMO_STATE_REPORT.md`
11. `10_DEMO_RESET_GUIDE.md`
12. `11_DEMO_OBSERVED_SUMMARY.md`
13. `12_OPERATOR_DEMO_WALKTHROUGH.md`
14. `WORKBENCH_DEMO_SMOKE.md`
15. `DEMO_READINESS_SUMMARY.md`
16. `OPERATOR_DEMO_GUIDE.md`
17. `DEMO_STATE_REPORT.md`
18. `DEMO_RESET_GUIDE.md`
19. `DEMO_OBSERVED_SUMMARY.md`
20. `OPERATOR_DEMO_WALKTHROUGH.md`
21. `WORKBENCH_DEMO_INDEX.md`
22. `operator-workbench-artifact-hashes.json`

## What This Packet Does Not Prove

This packet does not prove OS isolation, host compromise resistance, production deployment safety,
compliance automation, SIEM custody, production identity, remote MCP safety, external notarization,
or activity outside Ithildin-mediated actions.
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# Operator Workbench Evidence Review Prompt

You are reviewing Ithildin's operator workbench evidence packet. Treat this as a local-preview
operator-demo and evidence-surface review, not as production security approval.

Reviewed commit: `{context["commit"]}`
Area: `operator-workbench`
Finding namespace: `EXT-WORKBENCH-###`

## Scope

Please review whether the packet coherently shows how a local operator can:

- inspect trust posture and registered tool evidence;
- follow the Agent Runs `Demo Path`, filters, grouped timeline evidence, and summaries;
- inspect approval binding and audit status;
- export bounded read-only run evidence;
- inspect demo readiness status, missing/optional steps, and deferred boundaries;
- follow the happy path from preflight through cleanup without reading raw JSON first;
- inspect `DEMO_FLOW_RESULT.md` and `DEMO_RESET_GUIDE.md` after the optional mediated flow;
- connect live-demo, operator-managed sandbox, Agent Run correlation, signed fixture evidence, and
  negative transcript artifacts.

## Required Disposition

Say whether this is coherent enough for a local operator workbench demo. If not, name the missing
artifact, ambiguous claim, or required follow-up.

Do not approve new governed tool powers, run controls, sandbox orchestration, SIEM adapters,
production identity, remote MCP, hosted telemetry, shell/Docker/Kubernetes/browser tools, arbitrary
HTTP, broad writes, public/security-product positioning, or plugin SDK work.
"""


def _bundle_docs(repo_root: Path) -> str:
    parts = ["# Operator Workbench Document Bundle"]
    for path in DOCS:
        parts.extend(["", f"## {path.as_posix()}", "", "```md", _read(repo_root / path), "```"])
    return "\n".join(parts)


def _command_evidence(run_commands: bool) -> str:
    outputs = [_command_output(command, run_commands=run_commands) for command in COMMANDS]
    failures = [output for output in outputs if output["returncode"] != 0]
    if failures and run_commands:
        failed = ", ".join(" ".join(output["command"]) for output in failures)
        raise WorkbenchEvidencePacketError(f"evidence command failed: {failed}")
    lines = [
        "# Operator Workbench Command Evidence",
        "",
        "These commands are local readiness/evidence commands. They do not call governed tools,",
        "approve actions, repair diagnostics, or start services.",
    ]
    for output in outputs:
        lines.extend(
            [
                "",
                f"## {' '.join(output['command'])}",
                "",
                f"- exit code: `{output['returncode']}`",
                "",
                "```text",
                str(output["stdout"]).rstrip(),
                "```",
            ]
        )
        if output["stderr"]:
            lines.extend(["", "stderr:", "", "```text", str(output["stderr"]).rstrip(), "```"])
    return "\n".join(lines)


def _artifact_pointers(repo_root: Path) -> str:
    lines = ["# Operator Workbench Artifact Pointers", ""]
    for path in POINTERS:
        full_path = repo_root / path
        lines.append(f"- `{path.as_posix()}` exists=`{str(full_path.exists()).lower()}`")
    demo_result = Path("var/review-packets/v3/operator-workbench/DEMO_FLOW_RESULT.md")
    demo_observed = Path("var/review-packets/v3/operator-workbench/DEMO_OBSERVED_SUMMARY.md")
    run_export = Path("var/review-packets/v3/operator-workbench/RUN_EVIDENCE_EXPORT.json")
    demo_reset = Path("var/review-packets/v3/operator-workbench/DEMO_RESET_GUIDE.md")
    walkthrough = Path("var/review-packets/v3/operator-workbench/OPERATOR_DEMO_WALKTHROUGH.md")
    lines.extend(
        [
            f"- `{demo_result.as_posix()}` exists="
            f"`{str((repo_root / demo_result).exists()).lower()}`",
            f"- `{demo_observed.as_posix()}` exists="
            f"`{str((repo_root / demo_observed).exists()).lower()}`",
            f"- `{run_export.as_posix()}` exists="
            f"`{str((repo_root / run_export).exists()).lower()}`",
            f"- `{demo_reset.as_posix()}` exists="
            f"`{str((repo_root / demo_reset).exists()).lower()}`",
            f"- `{walkthrough.as_posix()}` exists="
            f"`{str((repo_root / walkthrough).exists()).lower()}`",
        ]
    )
    lines.extend(
        [
            "",
            "These artifacts are local evidence and reviewer convenience only. They are not",
            "notarization, SIEM custody, production compliance evidence, or proof of activity",
            "outside Ithildin-mediated actions.",
        ]
    )
    return "\n".join(lines)


def _observed_smoke(output_dir: Path) -> str:
    path = output_dir / "WORKBENCH_DEMO_SMOKE.md"
    if not path.exists():
        return "\n".join(
            [
                "# Workbench Demo Smoke Transcript",
                "",
                "Artifact not present. Run `make demo-workbench-smoke` before packet",
                "generation, or let `make workbench-evidence-packet` generate it.",
            ]
        )
    return "\n".join(
        [
            "# Workbench Demo Smoke Transcript",
            "",
            "```md",
            path.read_text(encoding="utf-8").rstrip(),
            "```",
        ]
    )


def _observed_readiness(output_dir: Path) -> str:
    path = output_dir / "DEMO_READINESS_SUMMARY.md"
    if not path.exists():
        return "\n".join(
            [
                "# Demo Readiness Summary",
                "",
                "Artifact not present. Run `make demo-readiness-summary` before packet",
                "generation, or let `make workbench-evidence-packet` generate it.",
            ]
        )
    return "\n".join(
        [
            "# Demo Readiness Summary",
            "",
            "```md",
            path.read_text(encoding="utf-8").rstrip(),
            "```",
        ]
    )


def _observed_operator_guide(output_dir: Path) -> str:
    path = output_dir / "OPERATOR_DEMO_GUIDE.md"
    if not path.exists():
        return "\n".join(
            [
                "# Operator Demo Guide",
                "",
                "Artifact not present. Run `make operator-demo-guide` before packet",
                "generation, or let `make workbench-evidence-packet` generate it.",
            ]
        )
    return "\n".join(
        [
            "# Operator Demo Guide",
            "",
            "```md",
            path.read_text(encoding="utf-8").rstrip(),
            "```",
        ]
    )


def _observed_state_report(output_dir: Path) -> str:
    path = output_dir / "DEMO_STATE_REPORT.md"
    if not path.exists():
        return "\n".join(
            [
                "# Demo State Report",
                "",
                "Artifact not present. Run `make demo-state-report` before packet",
                "generation, or let `make workbench-evidence-packet` generate it.",
            ]
        )
    return "\n".join(
        [
            "# Demo State Report",
            "",
            "```md",
            path.read_text(encoding="utf-8").rstrip(),
            "```",
        ]
    )


def _observed_reset_guide(output_dir: Path) -> str:
    path = output_dir / "DEMO_RESET_GUIDE.md"
    if not path.exists():
        return "\n".join(
            [
                "# Demo Reset Guide",
                "",
                "Artifact not present. Run `make demo-reset-guide` before packet",
                "generation, or let `make workbench-evidence-packet` generate it.",
            ]
        )
    return "\n".join(
        [
            "# Demo Reset Guide",
            "",
            "```md",
            path.read_text(encoding="utf-8").rstrip(),
            "```",
        ]
    )


def _observed_demo_summary(output_dir: Path) -> str:
    path = output_dir / "DEMO_OBSERVED_SUMMARY.md"
    if not path.exists():
        return "\n".join(
            [
                "# Demo Observed Summary",
                "",
                "Artifact not present. Run `make demo-observed-summary` after an",
                "intentional demo flow, or let `make workbench-evidence-packet` generate it.",
            ]
        )
    return "\n".join(
        [
            "# Demo Observed Summary",
            "",
            "```md",
            path.read_text(encoding="utf-8").rstrip(),
            "```",
        ]
    )


def _observed_operator_walkthrough(output_dir: Path) -> str:
    path = output_dir / "OPERATOR_DEMO_WALKTHROUGH.md"
    if not path.exists():
        return "\n".join(
            [
                "# Operator Demo Walkthrough",
                "",
                "Artifact not present. Run `make demo-operator-walkthrough` before packet",
                "generation, or let `make workbench-evidence-packet` generate it.",
            ]
        )
    return "\n".join(
        [
            "# Operator Demo Walkthrough",
            "",
            "```md",
            path.read_text(encoding="utf-8").rstrip(),
            "```",
        ]
    )


def _demo_story(context: dict[str, Any]) -> str:
    return f"""# Workbench Demo Happy Path Story

This story is generated by `make workbench-evidence-packet`. It is a reviewer/operator narrative
for the local demo; it does not start services, call governed tools, approve actions, mutate
workspaces, or manage sandbox lifecycle.

## Reviewed State

- commit: `{context["commit"]}`
- dirty: `{str(context["dirty"]).lower()}`
- command_evidence_executed: `{str(context["run_commands"]).lower()}`
- tool_count: `17`

## Happy Path Narrative

1. Run `make live-demo-preflight` and confirm loopback-only/local-preview posture.
2. Run `make demo-seed` if the ignored demo workspace needs sample files.
3. Run `make compose-up && make compose-smoke` for the optional local UI/API path.
4. Launch an MCP stdio client with `uv run python -m ithildin_mcp_server`.
5. Run `make demo-flow` to create a mediated local-preview run in the ignored demo workspace.
6. Inspect `DEMO_FLOW_RESULT.md` for proposal, approval, audit, and candidate run IDs.
7. Open `http://127.0.0.1:5173` and inspect System Trust, approvals, Agent Runs, and audit status.
8. Use Agent Runs `Demo Path`: filter runs, inspect grouped evidence, then Export Run Evidence.
9. Run `make demo-reset-guide` if the flow stops early or needs a clean repeat.
10. Run `make demo-workbench` to refresh packet evidence after the demo.
11. Run `make compose-down` if Compose was started.

## Evidence To Point At

- `DEMO_READINESS_SUMMARY.md` for ready/missing/optional/deferred status.
- `OPERATOR_DEMO_WALKTHROUGH.md` for the front-door expected screens, evidence files, and
  reset-safe human steps.
- `OPERATOR_DEMO_GUIDE.md` for the operator-facing preflight-to-cleanup walkthrough.
- `DEMO_STATE_REPORT.md` for current seed/reachability/artifact state and next commands.
- `DEMO_FLOW_RESULT.md` for proposal, approval, audit, candidate run ID, and cleanup evidence
  after `make demo-flow`.
- `DEMO_OBSERVED_SUMMARY.md` for the compact result, run evidence export pointer, and quickest
  post-demo reading order.
- `RUN_EVIDENCE_EXPORT.json` for the selected run's safe run evidence export when captured.
- `DEMO_RESET_GUIDE.md` for read-only reset/recovery guidance.
- `WORKBENCH_DEMO_SMOKE.md` for observed readiness commands and manual demo sequence.
- `02_OPERATOR_WORKBENCH_DOCS.md` for Agent Run and export contracts.
- `04_OPERATOR_WORKBENCH_ARTIFACT_POINTERS.md` for live-demo and correlation packet locations.

## Boundary

This story is not a runtime fixture loader and does not prove OS isolation, SIEM custody,
compliance automation, production security, external notarization, or activity outside
Ithildin-mediated actions.
"""


def _demo_index(output_dir: Path, context: dict[str, Any]) -> str:
    hashes = _hashes(output_dir)
    lines = [
        "# Workbench Demo Index",
        "",
        "This is the first file to open for the local operator workbench demo. It points to",
        "the generated packet artifacts and summarizes the intended reading order.",
        "",
        "## Status",
        "",
        f"- commit: `{context['commit']}`",
        f"- dirty: `{str(context['dirty']).lower()}`",
        f"- command_evidence_executed: `{str(context['run_commands']).lower()}`",
        "- tool_count: `17`",
        "",
        "## Newest Reading Order",
        "",
        "1. `WORKBENCH_DEMO_INDEX.md` for this newest reading order.",
        "2. `OPERATOR_DEMO_WALKTHROUGH.md` for expected screens, evidence files, and next",
        "   human steps.",
        "3. `DEMO_OBSERVED_SUMMARY.md` for the compact observed result when the demo has run.",
        "4. `DEMO_FLOW_RESULT.md` after `make demo-flow` for run/proposal/approval/audit pointers.",
        "5. `RUN_EVIDENCE_EXPORT.json` after Export Run Evidence for selected-run evidence.",
        "6. `OPERATOR_DEMO_GUIDE.md` for the preflight-to-cleanup walkthrough.",
        "7. `DEMO_STATE_REPORT.md` for current seed/reachability/artifact state.",
        "8. `DEMO_READINESS_SUMMARY.md` for ready/missing/optional/deferred status.",
        "9. `WORKBENCH_DEMO_SMOKE.md` for the operator flow transcript.",
        "10. `DEMO_RESET_GUIDE.md` for safe reset/recovery guidance.",
        "11. `00_OPERATOR_WORKBENCH_INDEX.md` for the workbench packet boundary.",
        "12. `var/review-packets/v3/live-demo/` for the live-demo packet.",
        "13. `02_OPERATOR_WORKBENCH_DOCS.md` for run evidence/export docs.",
        "",
        "## Supporting Artifacts",
        "",
        "- `07_WORKBENCH_DEMO_STORY.md` for the happy path narrative.",
        "- `11_DEMO_OBSERVED_SUMMARY.md` for the bundled observed-summary copy.",
        "- `12_OPERATOR_DEMO_WALKTHROUGH.md` for the bundled walkthrough copy.",
        "- `04_OPERATOR_WORKBENCH_ARTIFACT_POINTERS.md` for generated evidence paths.",
        "- `10_DEMO_RESET_GUIDE.md` for the bundled reset guide.",
        "",
        "## Artifact Hashes",
        "",
    ]
    for entry in hashes:
        lines.append(f"- `{entry['path']}`: `{entry['sha256']}` bytes=`{entry['bytes']}`")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This index does not prove OS isolation, SIEM custody, compliance automation,",
            "production security, or activity outside Ithildin-mediated actions.",
        ]
    )
    return "\n".join(lines)


def _require_project_root(repo_root: Path) -> None:
    missing = [path.as_posix() for path in PROJECT_MARKERS if not (repo_root / path).exists()]
    if missing:
        raise WorkbenchEvidencePacketError(
            f"must be run from Ithildin repo root; missing {', '.join(missing)}"
        )


def _read(path: Path) -> str:
    if not path.exists():
        raise WorkbenchEvidencePacketError(f"missing packet input: {path}")
    return path.read_text(encoding="utf-8").rstrip()


def _command_output(command: list[str], *, run_commands: bool) -> dict[str, Any]:
    if not run_commands:
        return {
            "command": command,
            "returncode": 0,
            "stdout": "command execution skipped for fixture/test packet generation",
            "stderr": "",
        }
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _git(repo_root: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _hashes(output_dir: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(output_dir.iterdir()):
        if path.name == HASH_MANIFEST or not path.is_file():
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

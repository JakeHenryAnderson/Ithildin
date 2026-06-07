"""Build a focused live-demo readiness review packet."""

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

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/live-demo")
HASH_MANIFEST = "live-demo-artifact-hashes.json"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
RUNBOOK_DOCS = [
    Path("docs/codex/live-demo-runbook.md"),
    Path("docs/codex/demo-scenario-pack-v2.md"),
    Path("docs/codex/reviewer-reproduction-map.md"),
]
EVIDENCE_DOCS = [
    Path("docs/codex/operator-managed-sandbox-demo-guide.md"),
    Path("docs/codex/sandbox-workspace-boundary-contract.md"),
    Path("docs/codex/agent-run-evidence-contract.md"),
    Path("docs/codex/agent-run-evidence-export-implementation.md"),
    Path("docs/codex/incident-reconstruction-guide.md"),
]
COMMANDS = [
    ["make", "live-demo-preflight"],
    ["make", "operator-sandbox-demo-packet"],
    ["make", "agent-run-correlation-packet"],
    ["make", "demo-scenario-pack"],
    ["make", "no-new-powers-guardrail"],
    ["make", "tool-surface-invariant-gate"],
]


class LiveDemoPacketError(RuntimeError):
    """Raised when the live-demo packet cannot be built."""


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
    except LiveDemoPacketError as exc:
        print(f"live demo packet failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built live-demo review packet at {output_dir}")
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
        raise LiveDemoPacketError("working tree is dirty; commit before live-demo handoff")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context = {"commit": commit, "dirty": dirty, "run_commands": run_commands}
    files = {
        "00_LIVE_DEMO_INDEX.md": _index(context),
        "01_LIVE_DEMO_REVIEW_PROMPT.md": _prompt(context),
        "02_LIVE_DEMO_RUNBOOK.md": _bundle_docs(
            repo_root, RUNBOOK_DOCS, "Live Demo Runbook Bundle"
        ),
        "03_LIVE_DEMO_EVIDENCE_CONTRACTS.md": _bundle_docs(
            repo_root, EVIDENCE_DOCS, "Live Demo Evidence Contract Bundle"
        ),
        "04_LIVE_DEMO_COMMAND_EVIDENCE.md": _command_evidence(run_commands=run_commands),
        "05_LIVE_DEMO_ARTIFACT_POINTERS.md": _artifact_pointers(),
    }
    for relative, content in files.items():
        (output_dir / relative).write_text(content.rstrip() + "\n", encoding="utf-8")
    _write_json(output_dir / HASH_MANIFEST, _hashes(output_dir))
    return output_dir


def _index(context: dict[str, Any]) -> str:
    return f"""# Live Demo Readiness Review Packet

This packet packages the local live-demo runbook, preflight output, operator-managed sandbox demo
packet pointers, Agent Run correlation packet pointers, and no-new-powers evidence. It is a
demo-readiness packet only.

## Boundary

- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Command evidence executed: `{str(context["run_commands"]).lower()}`.
- Tool count remains `13`.
- Ithildin does not start containers, mount Docker sockets, run shell commands through governed
  tools, manage Kubernetes, provide OS isolation, or claim production security.
- The live demo is an operator-managed local workbench showing mediated tool calls, approvals,
  audit evidence, Agent Run correlation, and locally signed fixture evidence.

## Artifacts

1. `00_LIVE_DEMO_INDEX.md`
2. `01_LIVE_DEMO_REVIEW_PROMPT.md`
3. `02_LIVE_DEMO_RUNBOOK.md`
4. `03_LIVE_DEMO_EVIDENCE_CONTRACTS.md`
5. `04_LIVE_DEMO_COMMAND_EVIDENCE.md`
6. `05_LIVE_DEMO_ARTIFACT_POINTERS.md`
7. `live-demo-artifact-hashes.json`

## What This Packet Does Not Prove

This packet does not prove sandboxing, host compromise resistance, SIEM custody, compliance
automation, production identity, remote MCP safety, runtime Postgres readiness, hosted telemetry
safety, or activity outside Ithildin-mediated actions.
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# Live Demo Readiness Review Prompt

You are reviewing Ithildin's local live-demo readiness packet. Treat this as a demo-readiness and
evidence-contract review, not as a production security review.

Reviewed commit: `{context["commit"]}`
Area: `live-demo-readiness`
Finding namespace: `EXT-LIVE-DEMO-###`

## Scope

Please review:

- whether the live-demo runbook has a coherent setup, demo, evidence, and cleanup sequence;
- whether preflight evidence covers loopback binding, no Docker socket mount, no-new-powers,
  tool-surface count, telemetry posture, HTTP allowlist posture, and demo inputs;
- whether the packet points clearly to operator-managed sandbox/workbench evidence, Agent Run
  correlation evidence, signed fixture evidence, negative transcripts, and review-candidate output;
- whether the wording avoids claims of sandbox lifecycle control, OS isolation, SIEM custody,
  compliance automation, production security, public/security-product approval, or new tool powers.

## Required Disposition

Say whether this packet is coherent enough for a local live demo handoff. If not, name the missing
artifact, ambiguous claim, or follow-up.

Do not approve new governed tool powers, sandbox orchestration, run controls, SIEM adapters,
production identity, runtime Postgres, remote MCP, hosted telemetry, shell/Docker/Kubernetes/browser
tools, arbitrary HTTP, broad writes, public/security-product positioning, or plugin SDK work.
"""


def _bundle_docs(repo_root: Path, paths: list[Path], title: str) -> str:
    parts = [f"# {title}"]
    for path in paths:
        parts.extend(
            [
                "",
                f"## {path.as_posix()}",
                "",
                "```md",
                _read(repo_root / path).rstrip(),
                "```",
            ]
        )
    return "\n".join(parts)


def _command_evidence(*, run_commands: bool) -> str:
    outputs = [_command_output(command, run_commands=run_commands) for command in COMMANDS]
    failures = [output for output in outputs if output["returncode"] != 0]
    if failures and run_commands:
        failed = ", ".join(" ".join(output["command"]) for output in failures)
        raise LiveDemoPacketError(f"evidence command failed: {failed}")
    lines = [
        "# Live Demo Command Evidence",
        "",
        "Commands are secret-free readiness gates. They do not call external models and do not",
        "change governed runtime behavior.",
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


def _artifact_pointers() -> str:
    return """# Live Demo Artifact Pointers

Generate these ignored artifacts during a full handoff:

- `var/review-packets/v3/operator-sandbox-demo/`
- `var/review-packets/v3/agent-run-correlation/`
- `var/review-packets/v0.2/signed-evidence-demo/`
- `var/review-packets/v0.2/negative-review-transcripts/`
- `var/review-packets/v0.2/GPT-5.5-Pro-consolidated/`

These artifacts are local evidence and reviewer convenience only. They are not notarization, SIEM
custody, production compliance evidence, or proof of activity outside Ithildin-mediated actions.
"""


def _require_project_root(repo_root: Path) -> None:
    missing = [path.as_posix() for path in PROJECT_MARKERS if not (repo_root / path).exists()]
    if missing:
        raise LiveDemoPacketError(
            f"must be run from Ithildin repo root; missing {', '.join(missing)}"
        )


def _read(path: Path) -> str:
    if not path.exists():
        raise LiveDemoPacketError(f"missing packet input: {path}")
    return path.read_text(encoding="utf-8")


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


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _hashes(output_dir: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(output_dir.iterdir()):
        if path.name == HASH_MANIFEST or not path.is_file():
            continue
        data = path.read_bytes()
        entries.append(
            {
                "path": path.name,
                "sha256": f"sha256:{hashlib.sha256(data).hexdigest()}",
                "bytes": len(data),
            }
        )
    return entries


if __name__ == "__main__":
    raise SystemExit(main())

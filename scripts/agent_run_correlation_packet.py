"""Build a focused Agent Run correlation review packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/agent-run-correlation")
HASH_MANIFEST = "agent-run-correlation-artifact-hashes.json"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
CONTRACT_DOCS = [
    Path("docs/codex/agent-run-model-contract.md"),
    Path("docs/codex/agent-run-evidence-contract.md"),
    Path("docs/codex/agent-run-evidence-export-implementation.md"),
    Path("docs/codex/agent-run-operations-readiness-gate.md"),
    Path("docs/codex/incident-reconstruction-guide.md"),
    Path("docs/codex/agent-run-observability-and-sandbox-roadmap.md"),
]
SOURCE_POINTERS = [
    Path("apps/api/src/ithildin_api/agent_runs.py"),
    Path("apps/api/src/ithildin_api/tool_calls.py"),
    Path("apps/api/src/ithildin_api/approvals.py"),
    Path("apps/api/src/ithildin_api/patches.py"),
    Path("apps/ui/src/App.tsx"),
    Path("apps/ui/src/App.test.tsx"),
]
EVIDENCE_COMMANDS = [
    ["make", "agent-run-correlation-smoke"],
    ["make", "agent-run-operations-readiness"],
    ["make", "agent-run-evidence-export-implementation-gate"],
    ["make", "incident-reconstruction-check"],
    ["make", "no-new-powers-guardrail"],
    ["make", "tool-surface-invariant-gate"],
]


class AgentRunCorrelationPacketError(RuntimeError):
    """Raised when the Agent Run correlation packet cannot be built."""


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
    except AgentRunCorrelationPacketError as exc:
        print(f"agent-run correlation packet failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built Agent Run correlation review packet at {output_dir}")
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
        raise AgentRunCorrelationPacketError(
            "working tree is dirty; commit before review-packet handoff"
        )
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context = {"commit": commit, "dirty": dirty, "run_commands": run_commands}
    evidence = _evidence(run_commands=run_commands)
    files = {
        "00_AGENT_RUN_CORRELATION_INDEX.md": _index(context),
        "01_AGENT_RUN_CORRELATION_PROMPT.md": _prompt(context),
        "02_AGENT_RUN_CORRELATION_CONTRACTS.md": _bundle_files(repo_root, CONTRACT_DOCS),
        "03_AGENT_RUN_CORRELATION_SOURCE_POINTERS.md": _source_pointers(repo_root),
        "04_AGENT_RUN_CORRELATION_SMOKE.md": _observed_smoke(output_dir),
        "05_AGENT_RUN_CORRELATION_COMMAND_EVIDENCE.md": evidence,
    }
    for relative, content in files.items():
        (output_dir / relative).write_text(content.rstrip() + "\n", encoding="utf-8")
    _write_json(output_dir / HASH_MANIFEST, _hashes(output_dir))
    return output_dir


def _index(context: dict[str, Any]) -> str:
    return f"""# Agent Run Correlation Review Packet

This packet shows how Ithildin's local-preview control-plane evidence can trace a mediated action
across Agent Run records, governed tool calls, policy decisions, approvals, audit events,
diagnostics, and read-only run evidence export. It is evidence packaging only.

## Boundary

- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Command evidence executed: `{str(context["run_commands"]).lower()}`.
- Tool count remains `13`.
- No manifests, executors, policy rules, API endpoints, MCP tools, run controls, sandbox controls,
  SIEM adapters, production identity, runtime Postgres, hosted telemetry, shell, Docker,
  Kubernetes, browser automation, arbitrary HTTP, broad filesystem writes, plugin SDK work, or new
  governed tool powers are added or approved by this packet.

## Artifacts

1. `00_AGENT_RUN_CORRELATION_INDEX.md`
2. `01_AGENT_RUN_CORRELATION_PROMPT.md`
3. `02_AGENT_RUN_CORRELATION_CONTRACTS.md`
4. `03_AGENT_RUN_CORRELATION_SOURCE_POINTERS.md`
5. `04_AGENT_RUN_CORRELATION_SMOKE.md`
6. `05_AGENT_RUN_CORRELATION_COMMAND_EVIDENCE.md`
7. `AGENT_RUN_CORRELATION_SMOKE.md`
8. `agent-run-correlation-artifact-hashes.json`
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# Agent Run Correlation Review Prompt

You are reviewing Ithildin's Agent Run correlation packet. Treat this as a local-preview evidence
review, not as proof of production security or activity outside Ithildin.

Reviewed commit: `{context["commit"]}`
Area: `agent-run-correlation`
Finding namespace: `EXT-RUN-CORR-###`

## Scope

Please review:

- whether the packet cleanly maps a mediated action across run record, tool-call metadata, policy
  evidence, approval evidence, audit event, diagnostics, and evidence export;
- whether the safe fields and exclusions align with the Agent Run evidence/export contracts;
- whether review-console operations evidence and incident reconstruction docs support the same
  correlation story;
- whether the packet avoids claims of SIEM custody, production compliance, sandboxing, run control,
  or proof of host activity outside Ithildin.

## Required Disposition

Say whether the Agent Run correlation story is coherent enough for local-preview operator demos. If
not, name the missing artifact, ambiguous claim, or required follow-up.

Do not approve new governed tool powers, run controls, sandbox orchestration, SIEM adapters,
production identity, remote MCP, hosted telemetry, shell/Docker/Kubernetes/browser tools, arbitrary
HTTP, broad writes, public/security-product positioning, or plugin SDK work.
"""


def _bundle_files(repo_root: Path, paths: list[Path]) -> str:
    parts: list[str] = ["# Agent Run Correlation Contract Bundle"]
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


def _source_pointers(repo_root: Path) -> str:
    parts = ["# Agent Run Correlation Source Pointers"]
    for path in SOURCE_POINTERS:
        content = _read(repo_root / path)
        parts.extend(
            [
                "",
                f"## {path.as_posix()}",
                "",
                "```text",
                content.rstrip(),
                "```",
            ]
        )
    return "\n".join(parts)


def _observed_smoke(output_dir: Path) -> str:
    path = output_dir / "AGENT_RUN_CORRELATION_SMOKE.md"
    if not path.exists():
        return "\n".join(
            [
                "# Agent Run Correlation Smoke",
                "",
                "## AGENT_RUN_CORRELATION_SMOKE.md",
                "",
                "Artifact not present. Run `make agent-run-correlation-smoke` before packet",
                "generation, or let `make agent-run-correlation-packet` generate it through",
                "command evidence.",
            ]
        )
    return "\n".join(
        [
            "# Agent Run Correlation Smoke",
            "",
            "```md",
            path.read_text(encoding="utf-8").rstrip(),
            "```",
        ]
    )


def _evidence(*, run_commands: bool) -> str:
    outputs = [_command_output(command, run_commands=run_commands) for command in EVIDENCE_COMMANDS]
    failures = [output for output in outputs if output["returncode"] != 0]
    if failures and run_commands:
        failed = ", ".join(" ".join(output["command"]) for output in failures)
        raise AgentRunCorrelationPacketError(f"evidence command failed: {failed}")
    lines = [
        "# Agent Run Correlation Command Evidence",
        "",
        "Commands are secret-free readiness gates. They do not call external models and do not",
        "change runtime behavior.",
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


def _command_output(command: list[str], *, run_commands: bool) -> dict[str, Any]:
    if not run_commands:
        return {
            "command": command,
            "returncode": 0,
            "stdout": "command execution skipped for fixture/test packet generation",
            "stderr": "",
        }
    result = subprocess.run(command, cwd=Path.cwd(), capture_output=True, text=True, check=False)
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _hashes(output_dir: Path) -> list[dict[str, Any]]:
    hashes: list[dict[str, Any]] = []
    for path in sorted(output_dir.iterdir()):
        if path.name == HASH_MANIFEST:
            continue
        content = path.read_bytes()
        hashes.append(
            {
                "path": path.name,
                "sha256": "sha256:" + hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
            }
        )
    return hashes


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read(path: Path) -> str:
    if not path.exists():
        raise AgentRunCorrelationPacketError(f"required packet input is missing: {path}")
    return path.read_text(encoding="utf-8")


def _git(repo_root: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AgentRunCorrelationPacketError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def _require_project_root(repo_root: Path) -> None:
    missing = [marker.as_posix() for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        raise AgentRunCorrelationPacketError(
            "must be run from the Ithildin repo root; missing markers: " + ", ".join(missing)
        )


if __name__ == "__main__":
    raise SystemExit(main())

"""Build a focused Agent Run timeline review packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/agent-run-timeline")
HASH_MANIFEST = "agent-run-timeline-artifact-hashes.json"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
SOURCE_FILES = [
    Path("apps/api/src/ithildin_api/agent_runs.py"),
    Path("apps/api/src/ithildin_api/app.py"),
    Path("apps/api/src/ithildin_api/tool_calls.py"),
    Path("apps/api/src/ithildin_api/approvals.py"),
    Path("apps/mcp-server/src/ithildin_mcp_server/server.py"),
    Path("apps/ui/src/App.tsx"),
    Path("apps/ui/src/App.test.tsx"),
]
TEST_FILES = [
    Path("tests/test_governed_tool_calls.py"),
    Path("tests/test_api_service.py"),
    Path("apps/ui/src/App.test.tsx"),
]
CONTRACT_DOCS = [
    Path("docs/codex/agent-run-model-contract.md"),
    Path("docs/codex/agent-run-evidence-contract.md"),
    Path("docs/codex/incident-reconstruction-guide.md"),
    Path("docs/codex/observability-readiness-gate.md"),
    Path("docs/codex/control-mapping-readiness-gate.md"),
    Path("docs/codex/agent-run-observability-and-sandbox-roadmap.md"),
]
EVIDENCE_COMMANDS = [
    ["make", "agent-run-evidence-contract-check"],
    ["uv", "run", "pytest", "tests/test_governed_tool_calls.py", "tests/test_api_service.py", "-q"],
    ["npm", "run", "test", "--prefix", "apps/ui"],
]


class AgentRunTimelinePacketError(RuntimeError):
    """Raised when the Agent Run timeline packet cannot be built."""


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
    except AgentRunTimelinePacketError as exc:
        print(f"agent-run timeline packet failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built Agent Run timeline review packet at {output_dir}")
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
        raise AgentRunTimelinePacketError(
            "working tree is dirty; commit before review-packet handoff"
        )
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context = {"commit": commit, "dirty": dirty, "run_commands": run_commands}
    files = {
        "00_AGENT_RUN_TIMELINE_INDEX.md": _index(context),
        "01_AGENT_RUN_TIMELINE_PROMPT.md": _prompt(context),
        "02_AGENT_RUN_SOURCE_BUNDLE.md": _bundle_files(repo_root, SOURCE_FILES),
        "03_AGENT_RUN_TESTS_BUNDLE.md": _bundle_files(repo_root, TEST_FILES),
        "04_AGENT_RUN_CONTRACTS_BUNDLE.md": _bundle_files(repo_root, CONTRACT_DOCS),
        "05_AGENT_RUN_COMMAND_EVIDENCE.md": _evidence(run_commands=run_commands),
    }
    for relative, content in files.items():
        (output_dir / relative).write_text(content.rstrip() + "\n", encoding="utf-8")
    _write_json(output_dir / HASH_MANIFEST, _hashes(output_dir))
    return output_dir


def _index(context: dict[str, Any]) -> str:
    return f"""# Agent Run Timeline Review Packet

This packet prepares Ithildin's Agent Run timeline surface for focused review. It includes the
read-only Agent Run store/API, governed-call correlation path, MCP startup wiring, review-console
panel, tests, contracts, and command evidence.

## Boundary

- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Command evidence executed: `{str(context["run_commands"]).lower()}`.
- tool count remains `16`.
- Agent Run timelines are read-only observability. They do not add pause, abort, kill, repair,
  replay, sandbox orchestration, SIEM adapters, production identity, or new governed tool powers.

## Artifacts

1. `00_AGENT_RUN_TIMELINE_INDEX.md`
2. `01_AGENT_RUN_TIMELINE_PROMPT.md`
3. `02_AGENT_RUN_SOURCE_BUNDLE.md`
4. `03_AGENT_RUN_TESTS_BUNDLE.md`
5. `04_AGENT_RUN_CONTRACTS_BUNDLE.md`
6. `05_AGENT_RUN_COMMAND_EVIDENCE.md`
7. `agent-run-timeline-artifact-hashes.json`
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# Agent Run Timeline Review Prompt

You are reviewing Ithildin's Agent Run timeline surface. Treat this as source/evidence review only
if you inspect the attached source bundle, focused tests, contracts, and command evidence.

Reviewed commit: `{context["commit"]}`
Area: `agent-run-timeline`
Finding namespace: `EXT-RUN-###`

## Scope

Please review:

- `AgentRunStore` persistence, run identity tuple, list/detail/timeline behavior, and safe decoding;
- `/runs` and `/runs/{{run_id}}` admin-only read-only API behavior;
- governed tool-call correlation metadata and `agent.session.started` audit event creation;
- MCP startup wiring that uses the same governed pipeline and run store;
- review-console Agent Runs panel, detail fetch, and safe timeline rendering;
- tests that cover run creation, audit metadata, API authorization, UI rendering, and no mutation;
- contract language that keeps Agent Runs as observability only.

## Required Disposition

Say whether the Agent Run timeline surface is coherent enough for local-preview observability. If
not, identify the missing source/test/evidence item or ambiguous product claim.

Do not approve run-control behavior, sandbox orchestration, process supervision, SIEM adapters,
production identity, remote MCP, hosted telemetry, shell/Docker/Kubernetes/browser tools, arbitrary
HTTP, broad writes, or new governed tool powers.
"""


def _bundle_files(repo_root: Path, paths: list[Path]) -> str:
    parts: list[str] = ["# Bundle"]
    for path in paths:
        parts.extend(
            [
                "",
                f"## {path.as_posix()}",
                "",
                "```text",
                _read(repo_root / path).rstrip(),
                "```",
            ]
        )
    return "\n".join(parts)


def _evidence(*, run_commands: bool) -> str:
    outputs = [_command_output(command, run_commands=run_commands) for command in EVIDENCE_COMMANDS]
    failures = [output for output in outputs if output["returncode"] != 0]
    if failures and run_commands:
        failed = ", ".join(" ".join(output["command"]) for output in failures)
        raise AgentRunTimelinePacketError(f"evidence command failed: {failed}")
    lines = [
        "# Agent Run Command Evidence",
        "",
        "Commands are focused, secret-free checks for the Agent Run timeline surface.",
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
        raise AgentRunTimelinePacketError(f"required packet input is missing: {path}")
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
        raise AgentRunTimelinePacketError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def _require_project_root(repo_root: Path) -> None:
    missing = [marker.as_posix() for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        raise AgentRunTimelinePacketError(
            "must be run from the Ithildin repo root; missing markers: " + ", ".join(missing)
        )


if __name__ == "__main__":
    raise SystemExit(main())

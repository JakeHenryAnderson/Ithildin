"""Build a focused Agent Run evidence export design review packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/agent-run-evidence")
HASH_MANIFEST = "agent-run-evidence-artifact-hashes.json"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
SOURCE_FILES = [
    Path("apps/api/src/ithildin_api/agent_runs.py"),
    Path("apps/api/src/ithildin_api/tool_calls.py"),
    Path("apps/api/src/ithildin_api/approvals.py"),
    Path("apps/api/src/ithildin_api/patches.py"),
    Path("packages/audit-core/src/ithildin_audit_core/signing.py"),
    Path("apps/ui/src/App.tsx"),
]
TEST_FILES = [
    Path("tests/test_governed_tool_calls.py"),
    Path("tests/test_api_service.py"),
    Path("tests/test_audit_writer.py"),
    Path("tests/test_signed_evidence_demo.py"),
    Path("apps/ui/src/App.test.tsx"),
]
CONTRACT_DOCS = [
    Path("docs/codex/agent-run-model-contract.md"),
    Path("docs/codex/agent-run-evidence-contract.md"),
    Path("docs/codex/agent-run-evidence-export-design.md"),
    Path("docs/codex/agent-run-evidence-export-implementation-plan.md"),
    Path("docs/codex/agent-run-evidence-export-implementation.md"),
    Path("docs/codex/agent-run-timeline-readiness-gate.md"),
    Path("docs/codex/incident-reconstruction-guide.md"),
    Path("docs/codex/dashboard-evidence-review-checklist.md"),
    Path("docs/codex/agent-run-operations-readiness-gate.md"),
    Path("docs/codex/siem-shaped-evidence-design.md"),
    Path("docs/codex/signed-audit-exports.md"),
]
EVIDENCE_COMMANDS = [
    ["make", "agent-run-evidence-contract-check"],
    ["make", "agent-run-evidence-export-check"],
    ["make", "agent-run-evidence-export-plan-check"],
    ["make", "agent-run-evidence-export-implementation-gate"],
    ["make", "agent-run-operations-readiness"],
    ["make", "incident-reconstruction-check"],
    ["make", "dashboard-evidence-checklist-check"],
    ["uv", "run", "pytest", "tests/test_governed_tool_calls.py", "tests/test_api_service.py", "-q"],
]


class AgentRunEvidencePacketError(RuntimeError):
    """Raised when the Agent Run evidence packet cannot be built."""


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
    except AgentRunEvidencePacketError as exc:
        print(f"agent-run evidence packet failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built Agent Run evidence review packet at {output_dir}")
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
        raise AgentRunEvidencePacketError(
            "working tree is dirty; commit before review-packet handoff"
        )
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context = {"commit": commit, "dirty": dirty, "run_commands": run_commands}
    files = {
        "00_AGENT_RUN_EVIDENCE_INDEX.md": _index(context),
        "01_AGENT_RUN_EVIDENCE_REVIEW_PROMPT.md": _prompt(context),
        "02_AGENT_RUN_EVIDENCE_SOURCE_BUNDLE.md": _bundle_files(repo_root, SOURCE_FILES),
        "03_AGENT_RUN_EVIDENCE_TESTS_BUNDLE.md": _bundle_files(repo_root, TEST_FILES),
        "04_AGENT_RUN_EVIDENCE_CONTRACTS_BUNDLE.md": _bundle_files(repo_root, CONTRACT_DOCS),
        "05_AGENT_RUN_EVIDENCE_COMMAND_EVIDENCE.md": _evidence(run_commands=run_commands),
    }
    for relative, content in files.items():
        (output_dir / relative).write_text(content.rstrip() + "\n", encoding="utf-8")
    _write_json(output_dir / HASH_MANIFEST, _hashes(output_dir))
    return output_dir


def _index(context: dict[str, Any]) -> str:
    return f"""# Agent Run Evidence Review Packet

This packet prepares Ithildin's Agent Run evidence and operations surface for focused review. It
includes the read-only run model, governed-call correlation path, approval and patch diagnostic
surfaces, signed audit export helper, bounded Agent Run evidence export endpoint, review-console
operations dashboard, tests, contracts, and command evidence.

## Boundary

- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Command evidence executed: `{str(context["run_commands"]).lower()}`.
- Tool count remains `13`.
- Agent Run evidence export and operations dashboard are bounded read-only local-preview surfaces.
  This packet does not add a SIEM adapter, sandbox control, production identity, run-control
  behavior, or new governed tool powers.

## Artifacts

1. `00_AGENT_RUN_EVIDENCE_INDEX.md`
2. `01_AGENT_RUN_EVIDENCE_REVIEW_PROMPT.md`
3. `02_AGENT_RUN_EVIDENCE_SOURCE_BUNDLE.md`
4. `03_AGENT_RUN_EVIDENCE_TESTS_BUNDLE.md`
5. `04_AGENT_RUN_EVIDENCE_CONTRACTS_BUNDLE.md`
6. `05_AGENT_RUN_EVIDENCE_COMMAND_EVIDENCE.md`
7. `agent-run-evidence-artifact-hashes.json`
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# Agent Run Evidence Review Prompt

You are reviewing Ithildin's Agent Run evidence and operations surface. Treat this as
source/evidence review only if you inspect the attached source bundle, focused tests, contracts, and
command evidence.

Reviewed commit: `{context["commit"]}`
Area: `agent-run-evidence`
Finding namespace: `EXT-RUN-EVID-###`

## Scope

Please review:

- the Agent Run record and timeline evidence fields;
- governed-call correlation metadata and safe audit relationship;
- approval and patch diagnostic evidence surfaces;
- signed audit export helper relationship and local-only trust boundary;
- dashboard filters, query summary evidence, timeline status/warning evidence, and incident
  reconstruction expectations;
- the export bundle fields, exclusions, hash fields, and warning states;
- tests and gates that keep the operations/export surface read-only and no-new-powers.

## Required Disposition

Say whether the Agent Run evidence export and read-only operations dashboard are coherent enough for
local-preview observability. If not, identify the missing source/test/evidence item or ambiguous
product claim.

Do not approve SIEM adapters, sandbox orchestration, process supervision, compliance automation,
production identity, remote MCP, hosted telemetry, shell/Docker/Kubernetes/browser tools, arbitrary
HTTP, broad writes, run controls, or new governed tool powers.
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
        raise AgentRunEvidencePacketError(f"evidence command failed: {failed}")
    lines = [
        "# Agent Run Evidence Command Evidence",
        "",
        "Commands are focused, secret-free checks for the Agent Run evidence export design.",
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
        raise AgentRunEvidencePacketError(f"required packet input is missing: {path}")
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
        raise AgentRunEvidencePacketError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def _require_project_root(repo_root: Path) -> None:
    missing = [marker.as_posix() for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        raise AgentRunEvidencePacketError(
            "must be run from the Ithildin repo root; missing markers: " + ", ".join(missing)
        )


if __name__ == "__main__":
    raise SystemExit(main())

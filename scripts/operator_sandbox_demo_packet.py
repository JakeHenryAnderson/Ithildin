"""Build a focused operator-managed sandbox/workbench demo review packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/operator-sandbox-demo")
HASH_MANIFEST = "operator-sandbox-demo-artifact-hashes.json"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
GUIDE_DOCS = [
    Path("docs/codex/operator-managed-sandbox-demo-guide.md"),
    Path("docs/codex/demo-scenario-pack-v2.md"),
    Path("docs/codex/reviewer-reproduction-map.md"),
]
CONTRACT_DOCS = [
    Path("docs/codex/sandbox-workspace-boundary-contract.md"),
    Path("docs/codex/agent-run-model-contract.md"),
    Path("docs/codex/agent-run-evidence-contract.md"),
    Path("docs/codex/agent-run-evidence-export-implementation.md"),
    Path("docs/codex/agent-run-operations-readiness-gate.md"),
    Path("docs/codex/agent-run-observability-and-sandbox-roadmap.md"),
    Path("docs/codex/incident-reconstruction-guide.md"),
]
DEMO_DOCS = [
    Path("docs/codex/mcp-client-examples.md"),
    Path("docs/codex/mcp-inspector-recipes.md"),
    Path("docs/codex/negative-review-recipes.md"),
]
EVIDENCE_COMMANDS = [
    ["make", "operator-sandbox-demo-smoke"],
    ["make", "operator-sandbox-dashboard-checklist"],
    ["make", "operator-sandbox-demo-readiness"],
    ["make", "agent-run-operations-readiness"],
    ["make", "demo-scenario-pack"],
    ["make", "no-new-powers-guardrail"],
    ["make", "tool-surface-invariant-gate"],
]


class OperatorSandboxDemoPacketError(RuntimeError):
    """Raised when the operator-managed sandbox demo packet cannot be built."""


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
    except OperatorSandboxDemoPacketError as exc:
        print(f"operator sandbox demo packet failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built operator-managed sandbox demo review packet at {output_dir}")
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
        raise OperatorSandboxDemoPacketError(
            "working tree is dirty; commit before review-packet handoff"
        )
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context = {"commit": commit, "dirty": dirty, "run_commands": run_commands}
    files = {
        "00_OPERATOR_SANDBOX_DEMO_INDEX.md": _index(context),
        "01_OPERATOR_SANDBOX_DEMO_PROMPT.md": _prompt(context),
        "02_OPERATOR_SANDBOX_DEMO_GUIDE.md": _bundle_docs(repo_root, GUIDE_DOCS),
        "03_SANDBOX_AND_AGENT_RUN_CONTRACTS.md": _bundle_docs(repo_root, CONTRACT_DOCS),
        "04_DEMO_COMMANDS_AND_SCENARIOS.md": _bundle_docs(repo_root, DEMO_DOCS),
        "05_OPERATOR_SANDBOX_DEMO_EVIDENCE.md": _evidence(run_commands=run_commands),
        "06_OPERATOR_SANDBOX_DEMO_OBSERVED_ARTIFACTS.md": _observed_artifacts(output_dir),
    }
    for relative, content in files.items():
        (output_dir / relative).write_text(content.rstrip() + "\n", encoding="utf-8")
    _write_json(output_dir / HASH_MANIFEST, _hashes(output_dir))
    return output_dir


def _index(context: dict[str, Any]) -> str:
    return f"""# Operator-Managed Sandbox Demo Review Packet

This packet packages Ithildin's operator-managed sandbox/workbench demo guide, Agent Run evidence
contracts, scenario recipes, and readiness command evidence. It is a review/demo-readiness packet
only.

## Boundary

- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Command evidence executed: `{str(context["run_commands"]).lower()}`.
- tool count remains `17`.
- Ithildin mediates registered tool calls against an operator-managed workspace or sandbox.
- This packet does not add runtime behavior, sandbox lifecycle control, sandbox orchestration, API
  endpoints, MCP tools, executors, tool manifests, policy rules, SIEM adapters, production identity,
  runtime Postgres, hosted telemetry, shell, Docker, Kubernetes, browser automation, arbitrary HTTP,
  broad filesystem writes, plugin SDK work, or new governed tool powers.

## Artifacts

1. `00_OPERATOR_SANDBOX_DEMO_INDEX.md`
2. `01_OPERATOR_SANDBOX_DEMO_PROMPT.md`
3. `02_OPERATOR_SANDBOX_DEMO_GUIDE.md`
4. `03_SANDBOX_AND_AGENT_RUN_CONTRACTS.md`
5. `04_DEMO_COMMANDS_AND_SCENARIOS.md`
6. `05_OPERATOR_SANDBOX_DEMO_EVIDENCE.md`
7. `06_OPERATOR_SANDBOX_DEMO_OBSERVED_ARTIFACTS.md`
8. `OPERATOR_SANDBOX_DEMO_SMOKE.md`
9. `OPERATOR_SANDBOX_DASHBOARD_CHECKLIST.md`
10. `operator-sandbox-demo-artifact-hashes.json`

## What This Packet Does Not Prove

This packet does not prove OS isolation, production deployment safety, SIEM-grade custody,
compliance automation, host compromise resistance, activity outside Ithildin-mediated actions, or
that Ithildin manages containers, VMs, Docker, Kubernetes, browsers, shells, or model lifecycle.
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# Operator-Managed Sandbox Demo Review Prompt

You are reviewing Ithildin's operator-managed sandbox/workbench demo packet. Treat this as a
demo-readiness and evidence-contract review, not as proof of sandboxing or production security.

Reviewed commit: `{context["commit"]}`
Area: `operator-sandbox-demo`
Finding namespace: `EXT-SANDBOX-DEMO-###`

## Scope

Please review:

- whether the demo guide clearly separates operator-managed workspace/sandbox setup from Ithildin
  mediation;
- whether Agent Run filters, timeline evidence, and evidence export provide a coherent local
  operator surface for mediated actions;
- whether the scenario pack, MCP recipes, negative recipes, signed-evidence demo references, and
  readiness commands are enough for a local workbench demonstration;
- whether all wording avoids claims of sandbox lifecycle control, OS isolation, production
  security, SIEM custody, compliance automation, or new tool powers.

## Required Disposition

Say whether this packet is coherent enough for an operator-managed sandbox/workbench local demo. If
not, name the missing artifact, ambiguous claim, or required follow-up.

Do not approve new governed tool powers, sandbox orchestration, container/VM lifecycle management,
Docker socket access, Kubernetes/browser/shell tools, arbitrary HTTP, broad filesystem writes,
production identity, runtime Postgres, hosted telemetry, SIEM adapters, compliance positioning,
remote MCP, public/security-product positioning, or plugin SDK work.
"""


def _bundle_docs(repo_root: Path, paths: list[Path]) -> str:
    parts: list[str] = ["# Bundle"]
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


def _evidence(*, run_commands: bool) -> str:
    outputs = [_command_output(command, run_commands=run_commands) for command in EVIDENCE_COMMANDS]
    failures = [output for output in outputs if output["returncode"] != 0]
    if failures and run_commands:
        failed = ", ".join(" ".join(output["command"]) for output in failures)
        raise OperatorSandboxDemoPacketError(f"evidence command failed: {failed}")
    lines = [
        "# Operator-Managed Sandbox Demo Command Evidence",
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


def _observed_artifacts(output_dir: Path) -> str:
    paths = [
        output_dir / "OPERATOR_SANDBOX_DEMO_SMOKE.md",
        output_dir / "OPERATOR_SANDBOX_DASHBOARD_CHECKLIST.md",
    ]
    parts = ["# Operator-Managed Sandbox Demo Observed Artifacts"]
    for path in paths:
        if path.exists():
            parts.extend(
                [
                    "",
                    f"## {path.name}",
                    "",
                    "```md",
                    path.read_text(encoding="utf-8").rstrip(),
                    "```",
                ]
            )
        else:
            parts.extend(
                [
                    "",
                    f"## {path.name}",
                    "",
                    "Artifact not present. Run `make operator-sandbox-demo-smoke` and",
                    "`make operator-sandbox-dashboard-checklist` before packet generation, or let",
                    "`make operator-sandbox-demo-packet` generate them through command evidence.",
                ]
            )
    return "\n".join(parts)


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
        raise OperatorSandboxDemoPacketError(f"required packet input is missing: {path}")
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
        raise OperatorSandboxDemoPacketError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def _require_project_root(repo_root: Path) -> None:
    missing = [marker.as_posix() for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        raise OperatorSandboxDemoPacketError(
            "must be run from the Ithildin repo root; missing markers: " + ", ".join(missing)
        )


if __name__ == "__main__":
    raise SystemExit(main())

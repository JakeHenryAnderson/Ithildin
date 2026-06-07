"""Generate a secret-free operator-managed sandbox demo smoke transcript."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT = Path(
    "var/review-packets/v3/operator-sandbox-demo/OPERATOR_SANDBOX_DEMO_SMOKE.md"
)
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
OBSERVED_COMMANDS = [
    ["make", "operator-sandbox-demo-readiness"],
    ["make", "demo-scenario-pack"],
    ["make", "no-new-powers-guardrail"],
    ["make", "tool-surface-invariant-gate"],
]
OPERATOR_MANAGED_COMMANDS = [
    "make demo-seed",
    "make compose-up",
    "make compose-smoke",
    "uv run python -m ithildin_mcp_server",
    "make demo-flow",
    "make negative-review-transcripts",
    "make signed-evidence-demo",
    "make signed-evidence-demo-verify",
]


class OperatorSandboxDemoSmokeError(RuntimeError):
    """Raised when the operator sandbox demo smoke transcript cannot be generated."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--skip-commands", action="store_true")
    args = parser.parse_args()

    try:
        path = build_transcript(
            repo_root=Path.cwd().resolve(),
            output=args.output,
            run_commands=not args.skip_commands,
        )
    except OperatorSandboxDemoSmokeError as exc:
        print(f"operator sandbox demo smoke failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built operator-managed sandbox demo smoke transcript at {path}")
    return 0


def build_transcript(*, repo_root: Path, output: Path, run_commands: bool = True) -> Path:
    _require_project_root(repo_root)
    commit = _git(repo_root, ["rev-parse", "HEAD"])
    dirty = bool(_git(repo_root, ["status", "--short"]))
    command_outputs = [
        _command_output(repo_root, command, run_commands=run_commands)
        for command in OBSERVED_COMMANDS
    ]
    failures = [entry for entry in command_outputs if entry["returncode"] != 0]
    if failures and run_commands:
        failed = ", ".join(" ".join(entry["command"]) for entry in failures)
        raise OperatorSandboxDemoSmokeError(f"smoke command failed: {failed}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        _render(
            commit=commit,
            dirty=dirty,
            run_commands=run_commands,
            command_outputs=command_outputs,
        ),
        encoding="utf-8",
    )
    return output


def _render(
    *,
    commit: str,
    dirty: bool,
    run_commands: bool,
    command_outputs: list[dict[str, Any]],
) -> str:
    lines = [
        "# Operator-Managed Sandbox Demo Smoke Transcript",
        "",
        "Status: generated local smoke transcript. This transcript is secret-free and does not",
        "start containers, VMs, Docker, Kubernetes, browsers, shells, hosted telemetry,",
        "remote MCP, or new governed tool powers.",
        "",
        "## Scope",
        "",
        f"- Generated at: `{datetime.now(UTC).isoformat()}`.",
        f"- Commit: `{commit}`.",
        f"- Dirty at generation: `{str(dirty).lower()}`.",
        f"- Observed readiness commands executed: `{str(run_commands).lower()}`.",
        "- Tool count remains `13`.",
        "- Ithildin mediates registered tools against an operator-managed workspace or sandbox.",
        "- The operator remains responsible for any container, VM, mount, isolation, and teardown.",
        "",
        "## Observed Readiness Commands",
    ]
    for entry in command_outputs:
        lines.extend(
            [
                "",
                f"### {' '.join(entry['command'])}",
                "",
                f"- exit code: `{entry['returncode']}`",
                "",
                "```text",
                str(entry["stdout"]).rstrip(),
                "```",
            ]
        )
        if entry["stderr"]:
            lines.extend(["", "stderr:", "", "```text", str(entry["stderr"]).rstrip(), "```"])
    lines.extend(
        [
            "",
            "## Operator-Managed Live Demo Sequence",
            "",
            "The following commands are intentionally listed as the live operator sequence",
            "rather than executed by this transcript generator. They may start local services",
            "or mutate only the ignored demo workspace when the operator chooses to run them.",
            "",
        ]
    )
    lines.extend(f"- `{command}`" for command in OPERATOR_MANAGED_COMMANDS)
    lines.extend(
        [
            "",
            "## Dashboard Evidence To Inspect",
            "",
            "- System Trust panel shows local-preview warnings and no new sandbox-control claim.",
            "- Agent Runs panel shows filters, summary chips, selected run timeline, and",
            "  warning chips.",
            "- Export Run Evidence remains a read-only download action.",
            "- Approval and patch diagnostics remain separate from run-control or sandbox",
            "  controls.",
            "",
            "## Right Conclusion",
            "",
            "The operator-managed sandbox/workbench demo path is reproducible as a local",
            "readiness story for Ithildin-mediated actions.",
            "",
            "## Wrong Conclusion",
            "",
            "This transcript does not prove OS isolation, production deployment safety, compliance",
            "automation, SIEM custody, or that Ithildin manages containers, VMs, shells, Docker,",
            "Kubernetes, browsers, models, or arbitrary host actions.",
            "",
        ]
    )
    return "\n".join(lines)


def _command_output(
    repo_root: Path,
    command: list[str],
    *,
    run_commands: bool,
) -> dict[str, Any]:
    if not run_commands:
        return {
            "command": command,
            "returncode": 0,
            "stdout": "command execution skipped for fixture/test transcript generation",
            "stderr": "",
        }
    result = subprocess.run(command, cwd=repo_root, capture_output=True, text=True, check=False)
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
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise OperatorSandboxDemoSmokeError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def _require_project_root(repo_root: Path) -> None:
    missing = [marker.as_posix() for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        raise OperatorSandboxDemoSmokeError(
            "must be run from the Ithildin repo root; missing markers: " + ", ".join(missing)
        )


if __name__ == "__main__":
    raise SystemExit(main())

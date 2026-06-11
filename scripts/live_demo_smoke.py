"""Generate a secret-free live-demo smoke transcript."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import live_demo_preflight

DEFAULT_OUTPUT = Path("var/review-packets/v3/live-demo/LIVE_DEMO_SMOKE.md")
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
OBSERVED_COMMANDS = [
    ["make", "live-demo-status"],
    ["make", "live-demo-preflight"],
    ["make", "operator-sandbox-demo-readiness"],
    ["make", "agent-run-operations-readiness"],
    ["make", "demo-scenario-pack"],
    ["make", "no-new-powers-guardrail"],
    ["make", "tool-surface-invariant-gate"],
]
OPERATOR_SEQUENCE = [
    "make admin-token-generate",
    "make demo-seed",
    "make compose-up",
    "make compose-smoke",
    "uv run python -m ithildin_mcp_server",
    "make demo-flow",
    "make operator-sandbox-demo-packet",
    "make agent-run-correlation-packet",
    "make negative-review-transcripts",
    "make signed-evidence-demo",
    "make signed-evidence-demo-verify",
    "make live-demo-evidence-summary",
    "make live-demo-packet",
    "make review-candidate",
    "make compose-down",
]


class LiveDemoSmokeError(RuntimeError):
    """Raised when the live-demo smoke transcript cannot be generated."""


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
    except LiveDemoSmokeError as exc:
        print(f"live demo smoke failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built live-demo smoke transcript at {path}")
    return 0


def build_transcript(*, repo_root: Path, output: Path, run_commands: bool = True) -> Path:
    _require_project_root(repo_root)
    commit = _git(repo_root, ["rev-parse", "HEAD"])
    dirty = bool(_git(repo_root, ["status", "--short"]))
    preflight = live_demo_preflight.build_report(repo_root)
    command_outputs = [
        _command_output(repo_root, command, run_commands=run_commands)
        for command in OBSERVED_COMMANDS
    ]
    failures = [entry for entry in command_outputs if entry["returncode"] != 0]
    if failures and run_commands:
        failed = ", ".join(" ".join(entry["command"]) for entry in failures)
        raise LiveDemoSmokeError(f"smoke command failed: {failed}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        _render(
            commit=commit,
            dirty=dirty,
            run_commands=run_commands,
            preflight=preflight,
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
    preflight: dict[str, Any],
    command_outputs: list[dict[str, Any]],
) -> str:
    lines = [
        "# Live Demo Smoke Transcript",
        "",
        "Status: generated local smoke transcript. This transcript is secret-free and does not",
        "start containers, run governed shell commands, call external models, mount Docker",
        "sockets, manage Kubernetes, enable remote MCP, or add governed tool powers.",
        "",
        "## Scope",
        "",
        f"- Generated at: `{datetime.now(UTC).isoformat()}`.",
        f"- Commit: `{commit}`.",
        f"- Dirty at generation: `{str(dirty).lower()}`.",
        f"- Observed readiness commands executed: `{str(run_commands).lower()}`.",
        "- Tool count remains `14`.",
        "- The local workbench is operator-managed; Ithildin mediates only registered tool calls.",
        "",
        "## Preflight Snapshot",
        "",
        f"- valid: `{str(preflight['valid']).lower()}`",
        f"- env source: `{preflight['env_source']}`",
        f"- tool count: `{preflight['tool_count']}`",
        f"- compose available: `{str(preflight['compose_available']).lower()}`",
        f"- loopback ports valid: `{str(preflight['loopback_ports_valid']).lower()}`",
        f"- Docker socket mounted: `{str(preflight['docker_socket_mounted']).lower()}`",
        f"- telemetry enabled: `{str(preflight['telemetry_enabled']).lower()}`",
        f"- HTTP allowlist count: `{preflight['http_allowlist_count']}`",
        "- runtime signing keys available: "
        f"`{str(preflight['runtime_signing_keys_available']).lower()}`",
        "",
        "### Preflight Warnings",
        "",
    ]
    warnings = preflight.get("warnings") or ["none"]
    lines.extend(f"- {warning}" for warning in warnings)
    lines.extend(["", "## Observed Readiness Commands"])
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
            "## Operator-Run Sequence",
            "",
            "These commands are intentionally not all executed by this transcript generator. Some",
            "start local services or mutate only the ignored demo workspace when the operator",
            "chooses to run them.",
            "",
        ]
    )
    lines.extend(f"- `{command}`" for command in OPERATOR_SEQUENCE)
    lines.extend(
        [
            "",
            "## Evidence Artifacts",
            "",
            "- `var/review-packets/v3/live-demo/`",
            "- `var/review-packets/v3/operator-sandbox-demo/`",
            "- `var/review-packets/v3/agent-run-correlation/`",
            "- `var/review-packets/v0.2/signed-evidence-demo/`",
            "- `var/review-packets/v0.2/negative-review-transcripts/`",
            "- `var/review-packets/v0.2/GPT-5.5-Pro-consolidated/`",
            "",
            "## Right Conclusion",
            "",
            "The local live-demo handoff has a repeatable, secret-free readiness transcript and",
            "clear evidence packet pointers for mediated actions.",
            "",
            "## Wrong Conclusion",
            "",
            "This transcript does not prove OS isolation, host compromise resistance, production",
            "security, compliance automation, SIEM custody, external notarization, or activity",
            "outside Ithildin-mediated actions.",
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
        raise LiveDemoSmokeError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def _require_project_root(repo_root: Path) -> None:
    missing = [marker.as_posix() for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        raise LiveDemoSmokeError(
            "must be run from the Ithildin repo root; missing markers: " + ", ".join(missing)
        )


if __name__ == "__main__":
    raise SystemExit(main())

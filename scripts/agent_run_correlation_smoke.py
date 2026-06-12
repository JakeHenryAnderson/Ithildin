"""Generate a secret-free Agent Run correlation smoke transcript."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT = Path("var/review-packets/v3/agent-run-correlation/AGENT_RUN_CORRELATION_SMOKE.md")
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
OBSERVED_COMMANDS = [
    ["make", "agent-run-operations-readiness"],
    ["make", "agent-run-evidence-export-implementation-gate"],
    ["make", "incident-reconstruction-check"],
    ["make", "no-new-powers-guardrail"],
    ["make", "tool-surface-invariant-gate"],
]
CORRELATION_FIELDS = [
    "run_id",
    "principal_id",
    "workspace_id",
    "tool_call_id",
    "request_id",
    "approval_id",
    "audit_event_id",
    "audit_event_hash",
    "policy_hash",
    "manifest_hash",
    "export_id",
    "evidence_hashes",
]


class AgentRunCorrelationSmokeError(RuntimeError):
    """Raised when the Agent Run correlation smoke transcript cannot be generated."""


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
    except AgentRunCorrelationSmokeError as exc:
        print(f"agent-run correlation smoke failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built Agent Run correlation smoke transcript at {path}")
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
        raise AgentRunCorrelationSmokeError(f"correlation smoke command failed: {failed}")
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
        "# Agent Run Correlation Smoke Transcript",
        "",
        "Status: generated local smoke transcript. It is secret-free and evidence-only;",
        "it does not create runs, approve actions, call governed tools, or add runtime behavior.",
        "",
        "## Scope",
        "",
        f"- Generated at: `{datetime.now(UTC).isoformat()}`.",
        f"- Commit: `{commit}`.",
        f"- Dirty at generation: `{str(dirty).lower()}`.",
        f"- Observed readiness commands executed: `{str(run_commands).lower()}`.",
        "- tool count remains `17`.",
        "- Correlation applies only to Ithildin-mediated actions.",
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
            "## Correlation Chain",
            "",
            "| Step | Evidence Pointer | Safe Metadata |",
            "| --- | --- | --- |",
            "| Run created | Agent Run record | run, principal, workspace, status |",
            "| Tool call started | Agent Run timeline + audit event | "
            "tool call, request, tool name |",
            "| Policy decision | audit/policy evidence | decision, rules, policy hash |",
            "| Approval required | approval record + timeline | "
            "approval, status, expiry, scope hash |",
            "| Approval consumed | approval record + audit event | "
            "one-time transition, safe reason |",
            "| Executor completed | Agent Run timeline + audit event | "
            "status, redaction, safe hashes |",
            "| Export generated | `GET /runs/{run_id}/evidence-export` | "
            "export and evidence hashes |",
            "| Signed audit export | local signed export bundle | "
            "key ID, digest, signature status |",
            "",
            "## Required Safe Fields",
            "",
        ]
    )
    lines.extend(f"- `{field}`" for field in CORRELATION_FIELDS)
    lines.extend(
        [
            "",
            "## Excluded From Correlation Evidence",
            "",
            "- prompts, model reasoning, raw tool arguments, file contents, diffs;",
            "- response bodies;",
            "- secrets, bearer tokens, cookies, private keys, local environment files;",
            "- package script values, dependency names, and raw sensitive paths.",
            "",
            "## Right Conclusion",
            "",
            "A reviewer can follow a mediated action across run records, timeline events,",
            "approvals, audit events, diagnostics, and read-only export without seeing secrets.",
            "",
            "## Wrong Conclusion",
            "",
            "This transcript does not prove production security, sandboxing, SIEM custody,",
            "compliance automation, external notarization, or non-mediated activity.",
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
        raise AgentRunCorrelationSmokeError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def _require_project_root(repo_root: Path) -> None:
    missing = [marker.as_posix() for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        raise AgentRunCorrelationSmokeError(
            "must be run from the Ithildin repo root; missing markers: " + ", ".join(missing)
        )


if __name__ == "__main__":
    raise SystemExit(main())

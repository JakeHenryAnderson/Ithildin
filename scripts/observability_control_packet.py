"""Build a focused observability/control mapping review packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/observability-control")
HASH_MANIFEST = "observability-control-artifact-hashes.json"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
CONTRACT_DOCS = [
    Path("docs/codex/agent-run-evidence-contract.md"),
    Path("docs/codex/sandbox-workspace-boundary-contract.md"),
    Path("docs/codex/siem-shaped-evidence-design.md"),
    Path("docs/codex/data-classification-design.md"),
    Path("docs/codex/control-mapping-design.md"),
    Path("docs/codex/incident-reconstruction-guide.md"),
    Path("docs/codex/observability-readiness-gate.md"),
    Path("docs/codex/agent-run-observability-and-sandbox-roadmap.md"),
]
EVIDENCE_COMMANDS = [
    ["make", "agent-run-evidence-contract-check"],
    ["make", "siem-evidence-design-check"],
    ["make", "data-classification-design-check"],
    ["make", "control-mapping-design-check"],
    ["make", "incident-reconstruction-check"],
    ["make", "observability-readiness"],
]


class ObservabilityControlPacketError(RuntimeError):
    """Raised when the observability/control packet cannot be built."""


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
    except ObservabilityControlPacketError as exc:
        print(f"observability/control packet failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built observability/control review packet at {output_dir}")
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
        raise ObservabilityControlPacketError(
            "working tree is dirty; commit before review-packet handoff"
        )
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context = {
        "commit": commit,
        "dirty": dirty,
        "run_commands": run_commands,
    }
    files = {
        "00_OBSERVABILITY_CONTROL_INDEX.md": _index(context),
        "01_OBSERVABILITY_CONTROL_PROMPT.md": _prompt(context),
        "02_OBSERVABILITY_CONTRACTS_BUNDLE.md": _bundle_docs(repo_root, CONTRACT_DOCS),
        "03_DATA_CLASSIFICATION_AND_CONTROL_MAPPING.md": _classification_and_mapping(repo_root),
        "04_INCIDENT_RECONSTRUCTION_GUIDE.md": _read(
            repo_root / "docs/codex/incident-reconstruction-guide.md"
        ),
        "05_OBSERVABILITY_COMMAND_EVIDENCE.md": _evidence(run_commands=run_commands),
    }
    for relative, content in files.items():
        (output_dir / relative).write_text(content.rstrip() + "\n", encoding="utf-8")
    _write_json(output_dir / HASH_MANIFEST, _hashes(output_dir))
    return output_dir


def _index(context: dict[str, Any]) -> str:
    return f"""# Observability Control Review Packet

This packet packages Ithildin's Agent Run, sandbox/workspace, SIEM-shaped evidence, data
classification, control mapping, and incident reconstruction design artifacts for review. It is a
review/design packet only and does not add runtime powers.

## Boundary

- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Command evidence executed: `{str(context["run_commands"]).lower()}`.
- tool count remains `20`.
- No new manifests, executors, policy rules, API endpoints, MCP tools, sandbox controls, SIEM
  adapters, production identity, runtime Postgres, hosted telemetry, shell, Docker, Kubernetes,
  browser automation, arbitrary HTTP, broad writes, or plugin SDK work are approved by this packet.

## Artifacts

1. `00_OBSERVABILITY_CONTROL_INDEX.md`
2. `01_OBSERVABILITY_CONTROL_PROMPT.md`
3. `02_OBSERVABILITY_CONTRACTS_BUNDLE.md`
4. `03_DATA_CLASSIFICATION_AND_CONTROL_MAPPING.md`
5. `04_INCIDENT_RECONSTRUCTION_GUIDE.md`
6. `05_OBSERVABILITY_COMMAND_EVIDENCE.md`
7. `observability-control-artifact-hashes.json`

## What This Packet Does Not Prove

This packet does not prove sandboxing, compliance automation, SIEM-grade custody, production
security control, immutable evidence, production identity, hosted trust, or activity outside
Ithildin-mediated actions.
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# Observability Control Design Review Prompt

You are reviewing Ithildin's observability/control mapping design packet. Treat this as a design and
evidence-contract review, not a source-level runtime review.

Reviewed commit: `{context["commit"]}`
Area: `observability-control`
Finding namespace: `EXT-OBS-###`

## Scope

Please review:

- Agent Run evidence contract and secret-free run correlation fields;
- operator-managed sandbox/workspace boundary contract and non-claims;
- SIEM-shaped evidence design and export non-goals;
- data classification proposal and future trusted local label boundaries;
- control mapping design and avoidance of HIPAA/GLBA/SOX/GDPR compliance claims;
- incident reconstruction guide for mediated actions only;
- command evidence and artifact hashes.

## Required Disposition

Say whether the packet is coherent enough for continued local-preview observability planning. If
not, name the missing artifact, ambiguous claim, or required follow-up.

Do not approve new governed tool powers, runtime sandbox control, SIEM adapters, production
identity, compliance positioning, public/security-product positioning, remote MCP, runtime Postgres,
hosted telemetry, shell/Docker/Kubernetes/browser tools, arbitrary HTTP, broad writes, or plugin SDK
work.
"""


def _bundle_docs(repo_root: Path, paths: list[Path]) -> str:
    parts: list[str] = ["# Observability Contract Bundle"]
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


def _classification_and_mapping(repo_root: Path) -> str:
    return "\n\n".join(
        [
            "# Data Classification and Control Mapping",
            "## docs/codex/data-classification-design.md",
            "```md\n"
            + _read(repo_root / "docs/codex/data-classification-design.md").rstrip()
            + "\n```",
            "## docs/codex/control-mapping-design.md",
            "```md\n"
            + _read(repo_root / "docs/codex/control-mapping-design.md").rstrip()
            + "\n```",
        ]
    )


def _evidence(*, run_commands: bool) -> str:
    command_outputs = [
        _command_output(command, run_commands=run_commands) for command in EVIDENCE_COMMANDS
    ]
    failures = [output for output in command_outputs if output["returncode"] != 0]
    if failures and run_commands:
        failed = ", ".join(" ".join(output["command"]) for output in failures)
        raise ObservabilityControlPacketError(f"evidence command failed: {failed}")
    lines = [
        "# Observability Command Evidence",
        "",
        "Commands are secret-free design/readiness gates. They do not call an external model and",
        "do not",
        "change runtime behavior.",
    ]
    for output in command_outputs:
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
        raise ObservabilityControlPacketError(f"required packet input is missing: {path}")
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
        raise ObservabilityControlPacketError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def _require_project_root(repo_root: Path) -> None:
    missing = [marker.as_posix() for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        raise ObservabilityControlPacketError(
            "must be run from the Ithildin repo root; missing markers: " + ", ".join(missing)
        )


if __name__ == "__main__":
    raise SystemExit(main())

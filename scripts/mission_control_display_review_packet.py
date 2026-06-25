"""Build a focused Mission Control display integration review packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/mission-control-display")
HASH_MANIFEST = "mission-control-display-artifact-hashes.json"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
CONTRACT_DOCS = [
    Path("docs/codex/mission-control-display-integration-proposal.md"),
    Path("docs/codex/mission-control-display-importer-plan.md"),
    Path("docs/codex/mission-control-side-handoff-plan.md"),
    Path("docs/codex/mission-control-handoff-schema-contract.md"),
    Path("docs/codex/mission-control-handoff-negative-fixtures.md"),
    Path("docs/codex/hello-world-mission-control-handoff.md"),
    Path("docs/codex/enterprise-readiness-runway.md"),
]
COMMANDS = [
    ["make", "mission-control-display-integration-proposal-check"],
    ["make", "mission-control-display-importer-plan-check"],
    ["make", "mission-control-side-handoff-plan-check"],
    ["make", "mission-control-handoff-schema-contract-check"],
    ["make", "mission-control-handoff-negative-fixtures-check"],
    ["make", "hello-world-mission-control-handoff-check"],
    ["make", "no-new-powers-guardrail"],
    ["make", "tool-surface-invariant-gate"],
]


class MissionControlDisplayReviewPacketError(RuntimeError):
    """Raised when the Mission Control display review packet cannot be built."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--skip-commands", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    try:
        if args.check:
            report = build_check_report(Path.cwd().resolve())
            print(render_check_report(report))
            return 0 if report["valid"] else 1
        output_dir = build_packet(
            repo_root=Path.cwd().resolve(),
            output_dir=args.output_dir,
            allow_dirty=args.allow_dirty,
            run_commands=not args.skip_commands,
        )
    except MissionControlDisplayReviewPacketError as exc:
        print(f"Mission Control display review packet failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built Mission Control display review packet at {output_dir}")
    return 0


def build_check_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "mission-control-display"
        try:
            build_packet(
                repo_root=repo_root,
                output_dir=output_dir,
                allow_dirty=True,
                run_commands=False,
            )
        except MissionControlDisplayReviewPacketError as exc:
            failures.append(str(exc))
            artifact_names: set[str] = set()
            hashes: dict[str, Any] = {"artifacts": []}
        else:
            artifact_names = {path.name for path in output_dir.iterdir()}
            hashes = json.loads((output_dir / HASH_MANIFEST).read_text(encoding="utf-8"))

    expected = {
        "00_MISSION_CONTROL_DISPLAY_INDEX.md",
        "01_MISSION_CONTROL_DISPLAY_REVIEW_PROMPT.md",
        "02_MISSION_CONTROL_DISPLAY_CONTRACTS.md",
        "03_MISSION_CONTROL_HANDOFF_SEED.md",
        "04_MISSION_CONTROL_NEGATIVE_FIXTURES.md",
        "05_MISSION_CONTROL_DISPLAY_COMMAND_EVIDENCE.md",
        HASH_MANIFEST,
    }
    missing = expected - artifact_names
    if missing:
        failures.append("packet missing artifacts: " + ", ".join(sorted(missing)))
    hashed = {entry["path"] for entry in hashes.get("artifacts", [])}
    if HASH_MANIFEST in hashed:
        failures.append("hash manifest must not hash itself")
    if expected - {HASH_MANIFEST} - hashed:
        failures.append("artifact hashes do not cover generated markdown files")
    for target in [
        "mission-control-display-review-packet:",
        "mission-control-display-review-packet-check:",
    ]:
        if target not in makefile:
            failures.append(f"Make target is missing: {target.rstrip(':')}")
    if "mission-control-display-review-packet-check" not in release_check_body:
        failures.append("mission-control-display-review-packet-check missing from release-check")
    if "$(MAKE) mission-control-display-review-packet" not in review_candidate_body:
        failures.append("mission-control-display-review-packet missing from review-candidate")
    if "make mission-control-display-review-packet" not in readme:
        failures.append("README is missing Mission Control display review packet command")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "output_dir": str(DEFAULT_OUTPUT_DIR),
        "artifact_count": len(expected),
        "tool_count": 24,
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "new_power_classes_allowed": False,
    }


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
        raise MissionControlDisplayReviewPacketError(
            "working tree is dirty; commit before review-packet handoff"
        )
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context = {"commit": commit, "dirty": dirty, "run_commands": run_commands}
    files = {
        "00_MISSION_CONTROL_DISPLAY_INDEX.md": _index(context),
        "01_MISSION_CONTROL_DISPLAY_REVIEW_PROMPT.md": _prompt(context),
        "02_MISSION_CONTROL_DISPLAY_CONTRACTS.md": _bundle_docs(repo_root, CONTRACT_DOCS),
        "03_MISSION_CONTROL_HANDOFF_SEED.md": _handoff_seed(run_commands=run_commands),
        "04_MISSION_CONTROL_NEGATIVE_FIXTURES.md": _negative_fixture_summary(repo_root),
        "05_MISSION_CONTROL_DISPLAY_COMMAND_EVIDENCE.md": _command_evidence(
            run_commands=run_commands
        ),
    }
    for relative, content in files.items():
        output_dir.joinpath(relative).write_text(content.rstrip() + "\n", encoding="utf-8")
    _write_json(output_dir / HASH_MANIFEST, {"artifacts": _hashes(output_dir)})
    return output_dir


def _index(context: dict[str, Any]) -> str:
    return f"""# Mission Control Display Review Packet

This packet packages Ithildin's current Mission Control display/import proposal, handoff schema
contract, Mission Control-side handoff plan, negative fixture plan, Hello World seed payload
evidence, and command evidence. It is a review/design handoff for display-only integration
planning.

## Boundary

- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Command evidence executed: `{str(context["run_commands"]).lower()}`.
- tool count remains `24`.
- Mission Control may be planned as an evidence viewer only.
- Ithildin remains the policy, approval, execution, and audit authority for Ithildin-mediated
  actions.
- This packet does not add runtime behavior, API callbacks, MCP transports, Mission Control
  execution behavior, local model invocation, VM/container lifecycle management, sandbox
  orchestration, trusted-host promotion, SIEM adapters, production identity, runtime Postgres,
  hosted telemetry, shell, Docker, Kubernetes, browser automation, arbitrary HTTP, broad
  filesystem writes, plugin SDK work, compliance automation, or new governed tool powers.

## Artifacts

1. `00_MISSION_CONTROL_DISPLAY_INDEX.md`
2. `01_MISSION_CONTROL_DISPLAY_REVIEW_PROMPT.md`
3. `02_MISSION_CONTROL_DISPLAY_CONTRACTS.md`
4. `03_MISSION_CONTROL_HANDOFF_SEED.md`
5. `04_MISSION_CONTROL_NEGATIVE_FIXTURES.md`
6. `05_MISSION_CONTROL_DISPLAY_COMMAND_EVIDENCE.md`
7. `mission-control-display-artifact-hashes.json`

## What This Packet Does Not Prove

This packet does not prove Mission Control implementation correctness, bidirectional integration,
live importer behavior, model execution, sandboxing, host promotion, SIEM custody, compliance
automation, production deployment safety, or activity outside Ithildin-mediated actions.
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# Mission Control Display Review Prompt

You are reviewing Ithildin's Mission Control display integration packet. Treat this as a
display/import contract review, not as runtime integration approval.

Reviewed commit: `{context["commit"]}`
Area: `mission-control-display`
Finding namespace: `EXT-MC-DISPLAY-###`

## Scope

Please review:

- whether the display proposal gives Mission Control enough safe fields to be useful as an evidence
  viewer;
- whether the Mission Control-side handoff plan is specific enough for a display-only importer
  implementation task without granting Mission Control authority;
- whether the handoff schema clearly keeps Ithildin as policy, approval, execution, and audit
  authority;
- whether the negative fixture plan covers malformed, stale, unsafe-path, authority-overclaiming,
  and content-leaking handoff payloads;
- whether the Hello World handoff seed is a coherent metadata-only sample for a future importer;
- whether the packet avoids claims of Mission Control execution authority, local model runtime,
  sandbox/VM control, host promotion, SIEM custody, compliance automation, production identity, or
  broader security-product readiness.

## Required Disposition

Say whether this packet is coherent enough for a future Mission Control-side display/import
implementation plan. If not, name the missing artifact, ambiguous claim, or required follow-up.

Do not approve new governed tool powers, Mission Control execution authority, API callbacks,
approval authority transfer, audit authority transfer, local model invocation, sandbox
orchestration, VM/container lifecycle management, host promotion, SIEM adapters, production
identity, runtime Postgres, hosted telemetry, shell/Docker/Kubernetes/browser tools, arbitrary
HTTP, broad writes, remote MCP, public/security-product positioning, or plugin SDK work.
"""


def _bundle_docs(repo_root: Path, paths: list[Path]) -> str:
    parts = ["# Mission Control Display Contract Bundle"]
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


def _handoff_seed(*, run_commands: bool) -> str:
    output = _command_output(
        ["make", "hello-world-mission-control-handoff"],
        run_commands=run_commands,
    )
    lines = [
        "# Mission Control Handoff Seed Evidence",
        "",
        "The seed command generates a metadata-only Mission Control handoff under",
        "`var/review-packets/v3/hello-world-mission-control-handoff/`.",
        "",
        f"- exit code: `{output['returncode']}`",
        "",
        "```text",
        str(output["stdout"]).rstrip(),
        "```",
    ]
    if output["stderr"]:
        lines.extend(["", "stderr:", "", "```text", str(output["stderr"]).rstrip(), "```"])
    if output["returncode"] != 0 and run_commands:
        raise MissionControlDisplayReviewPacketError("hello-world Mission Control handoff failed")
    return "\n".join(lines)


def _negative_fixture_summary(repo_root: Path) -> str:
    text = _read(repo_root / "docs/codex/mission-control-handoff-negative-fixtures.md")
    return "\n".join(
        [
            "# Mission Control Negative Fixture Summary",
            "",
            "This section embeds the current Ithildin-side negative fixture plan for any future",
            "Mission Control display/import implementation.",
            "",
            "```md",
            text.rstrip(),
            "```",
        ]
    )


def _command_evidence(*, run_commands: bool) -> str:
    outputs = [_command_output(command, run_commands=run_commands) for command in COMMANDS]
    failures = [output for output in outputs if output["returncode"] != 0]
    if failures and run_commands:
        failed = ", ".join(" ".join(output["command"]) for output in failures)
        raise MissionControlDisplayReviewPacketError(f"evidence command failed: {failed}")
    lines = [
        "# Mission Control Display Command Evidence",
        "",
        "Commands are secret-free readiness gates. They do not call Mission Control, do not call",
        "external models, and do not change runtime behavior.",
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
        raise MissionControlDisplayReviewPacketError(f"required packet input is missing: {path}")
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
        raise MissionControlDisplayReviewPacketError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def _require_project_root(repo_root: Path) -> None:
    missing = [marker.as_posix() for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        raise MissionControlDisplayReviewPacketError(
            "must be run from the Ithildin repo root; missing markers: " + ", ".join(missing)
        )


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Mission Control display review packet check",
        f"valid: {str(report['valid']).lower()}",
        f"output_dir: {report['output_dir']}",
        f"artifact_count: {report['artifact_count']}",
        f"tool_count: {report['tool_count']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

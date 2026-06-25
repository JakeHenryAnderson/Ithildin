"""Build a focused sandbox/VM proof-of-concept review packet."""

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

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/sandbox-vm-poc-review")
HASH_MANIFEST = "sandbox-vm-poc-review-artifact-hashes.json"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
BOUNDARY_DOCS = [
    Path("docs/codex/enterprise-readiness-runway.md"),
    Path("docs/codex/sandbox-vm-worker-boundary-charter.md"),
    Path("docs/codex/sandbox-vm-profile-contract.md"),
    Path("docs/codex/sandbox-vm-preflight-contract.md"),
    Path("docs/codex/sandbox-workspace-boundary-contract.md"),
]
DEMO_AND_HANDOFF_DOCS = [
    Path("docs/codex/hello-world-sandbox-demo-roadmap.md"),
    Path("docs/codex/hello-world-sandbox-observed-demo.md"),
    Path("docs/codex/hello-world-mission-control-handoff.md"),
    Path("docs/codex/mission-control-display-integration-proposal.md"),
    Path("docs/codex/mission-control-handoff-schema-contract.md"),
    Path("docs/codex/mission-control-handoff-negative-fixtures.md"),
]
ARTIFACT_AND_PROMOTION_DOCS = [
    Path("docs/codex/capability-proposals/sandbox-artifact-write-text.md"),
    Path("docs/codex/capability-implementation-plans/sandbox-artifact-write-text.md"),
    Path("docs/codex/sandbox-artifact-write-text-fixture-plan.md"),
    Path("docs/codex/sandbox-artifact-write-text-negative-transcripts.md"),
    Path("docs/codex/sandbox-artifact-write-text-source-review.md"),
    Path("docs/codex/sandbox-artifact-write-text-implementation-decision.md"),
    Path("docs/codex/v3-sandbox-artifact-write-text-internal-review.md"),
    Path("docs/codex/sandbox-promotion-evidence-contract.md"),
]
COMMANDS = [
    ["make", "sandbox-vm-worker-boundary-charter-check"],
    ["make", "sandbox-vm-profile-contract-check"],
    ["make", "sandbox-vm-preflight-contract-check"],
    ["make", "mission-control-display-review-packet-check"],
    ["make", "hello-world-sandbox-observed-demo-check"],
    ["make", "hello-world-mission-control-handoff-check"],
    ["make", "sandbox-promotion-evidence-contract-check"],
    ["make", "sandbox-artifact-write-text-implementation-gate"],
    ["make", "sandbox-artifact-write-text-negative-transcripts"],
    ["make", "no-new-powers-guardrail"],
    ["make", "tool-surface-invariant-gate"],
]


class SandboxVmPocReviewPacketError(RuntimeError):
    """Raised when the sandbox/VM POC review packet cannot be built."""


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
    except SandboxVmPocReviewPacketError as exc:
        print(f"sandbox/VM POC review packet failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built sandbox/VM proof-of-concept review packet at {output_dir}")
    return 0


def build_check_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    runway = _read(repo_root / "docs/codex/enterprise-readiness-runway.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "sandbox-vm-poc-review"
        try:
            build_packet(
                repo_root=repo_root,
                output_dir=output_dir,
                allow_dirty=True,
                run_commands=False,
            )
        except SandboxVmPocReviewPacketError as exc:
            failures.append(str(exc))
            artifact_names: set[str] = set()
            hashes: dict[str, Any] = {"artifacts": []}
        else:
            artifact_names = {path.name for path in output_dir.iterdir()}
            hashes = json.loads((output_dir / HASH_MANIFEST).read_text(encoding="utf-8"))

    expected = {
        "00_SANDBOX_VM_POC_REVIEW_INDEX.md",
        "01_SANDBOX_VM_POC_REVIEW_PROMPT.md",
        "02_SANDBOX_VM_BOUNDARY_CONTRACTS.md",
        "03_HELLO_WORLD_AND_MISSION_CONTROL_HANDOFF.md",
        "04_ARTIFACT_WRITE_AND_PROMOTION_CONTRACTS.md",
        "05_SANDBOX_VM_POC_COMMAND_EVIDENCE.md",
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
        "sandbox-vm-poc-review-packet:",
        "sandbox-vm-poc-review-packet-check:",
    ]:
        if target not in makefile:
            failures.append(f"Make target is missing: {target.rstrip(':')}")
    if "sandbox-vm-poc-review-packet-check" not in release_check_body:
        failures.append("sandbox-vm-poc-review-packet-check missing from release-check")
    if "$(MAKE) sandbox-vm-poc-review-packet" not in review_candidate_body:
        failures.append("sandbox-vm-poc-review-packet missing from review-candidate")
    if "make sandbox-vm-poc-review-packet" not in readme:
        failures.append("README is missing sandbox/VM POC review packet command")
    if "sandbox/VM proof-of-concept review packet" not in runway:
        failures.append("enterprise runway is missing sandbox/VM POC review packet pointer")

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
        raise SandboxVmPocReviewPacketError(
            "working tree is dirty; commit before review-packet handoff"
        )
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context = {"commit": commit, "dirty": dirty, "run_commands": run_commands}
    files = {
        "00_SANDBOX_VM_POC_REVIEW_INDEX.md": _index(context),
        "01_SANDBOX_VM_POC_REVIEW_PROMPT.md": _prompt(context),
        "02_SANDBOX_VM_BOUNDARY_CONTRACTS.md": _bundle_docs(repo_root, BOUNDARY_DOCS),
        "03_HELLO_WORLD_AND_MISSION_CONTROL_HANDOFF.md": _bundle_docs(
            repo_root, DEMO_AND_HANDOFF_DOCS
        ),
        "04_ARTIFACT_WRITE_AND_PROMOTION_CONTRACTS.md": _bundle_docs(
            repo_root, ARTIFACT_AND_PROMOTION_DOCS
        ),
        "05_SANDBOX_VM_POC_COMMAND_EVIDENCE.md": _command_evidence(
            run_commands=run_commands
        ),
    }
    for relative, content in files.items():
        output_dir.joinpath(relative).write_text(content.rstrip() + "\n", encoding="utf-8")
    _write_json(output_dir / HASH_MANIFEST, {"artifacts": _hashes(output_dir)})
    return output_dir


def _index(context: dict[str, Any]) -> str:
    return f"""# Sandbox/VM Proof-Of-Concept Review Packet

This packet packages the design-only sandbox/VM worker boundary, profile, preflight, Mission
Control display handoff, Hello World observed sandbox artifact evidence, artifact-write source
review handoff, promotion evidence contract, and command evidence needed before any real sandbox/VM
runtime integration is planned.

## Boundary

- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Command evidence executed: `{str(context["run_commands"]).lower()}`.
- tool count remains `24`.
- This is a pre-runtime proof-of-concept review packet, not a live sandbox/VM integration.
- Ithildin remains the governed mediation/evidence gateway.
- Mission Control remains a display/handoff surface only.
- The sandbox/VM layer remains operator-managed infrastructure.
- This packet does not add runtime behavior, API endpoints, MCP tools, executors, tool manifests,
  policy rules, local model invocation, Mission Control runtime behavior, sandbox orchestration, VM
  lifecycle control, Docker socket access, Kubernetes control, browser automation, shell execution,
  arbitrary HTTP, broad filesystem writes, trusted-host promotion, SIEM adapters, production
  identity, runtime Postgres, hosted telemetry, plugin SDK behavior, compliance automation, public
  security-product claims, or new governed tool powers.

## Artifacts

1. `00_SANDBOX_VM_POC_REVIEW_INDEX.md`
2. `01_SANDBOX_VM_POC_REVIEW_PROMPT.md`
3. `02_SANDBOX_VM_BOUNDARY_CONTRACTS.md`
4. `03_HELLO_WORLD_AND_MISSION_CONTROL_HANDOFF.md`
5. `04_ARTIFACT_WRITE_AND_PROMOTION_CONTRACTS.md`
6. `05_SANDBOX_VM_POC_COMMAND_EVIDENCE.md`
7. `sandbox-vm-poc-review-artifact-hashes.json`

## What This Packet Does Not Prove

This packet does not prove OS isolation, VM/container lifecycle safety, host compromise resistance,
Mission Control runtime correctness, local model plan quality, trusted-host promotion correctness,
SIEM custody, production deployment safety, compliance automation, or activity outside
Ithildin-mediated actions.
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# Sandbox/VM Proof-Of-Concept Review Prompt

You are reviewing Ithildin's sandbox/VM proof-of-concept review packet. Treat this as a
pre-runtime design/evidence handoff, not as source-review closure for sandbox orchestration or proof
of OS isolation.

Reviewed commit: `{context["commit"]}`
Area: `sandbox-vm-poc`
Finding namespace: `EXT-SANDBOX-VM-POC-###`

## Scope

Please review:

- whether the boundary charter, profile contract, and preflight contract are coherent enough before
  a future operator-managed sandbox/VM proof of concept;
- whether the supported platform, mount/root label, network posture, ingress/egress, cleanup,
  warning, and go/no-go fields are sufficient for a future preflight runner proposal;
- whether the Hello World observed sandbox artifact evidence and Mission Control handoff packet
  demonstrate the right separation between intent, mediation, evidence, and display;
- whether `sandbox.artifact.write_text` and promotion evidence remain separated from trusted-host
  promotion;
- whether command evidence and packet wording avoid claims of sandbox orchestration, OS isolation,
  local model authority, Mission Control execution authority, production security, SIEM custody,
  compliance automation, or new tool powers.

## Required Disposition

Say whether this packet is coherent enough to plan a later implementation proposal for a static,
operator-managed sandbox/VM profile fixture and preflight runner. If not, name the missing
artifact, ambiguous claim, or required follow-up.

Do not approve new governed tool powers, sandbox orchestration, VM/container lifecycle management,
Docker socket access, Kubernetes/browser/shell tools, arbitrary HTTP, broad filesystem writes,
trusted-host promotion, Mission Control execution authority, local model invocation, production
identity, runtime Postgres, hosted telemetry, SIEM adapters, compliance positioning, remote MCP,
public/security-product positioning, or plugin SDK work.
"""


def _bundle_docs(repo_root: Path, paths: list[Path]) -> str:
    parts = ["# Bundle"]
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
        raise SandboxVmPocReviewPacketError(f"evidence command failed: {failed}")
    lines = [
        "# Sandbox/VM Proof-Of-Concept Command Evidence",
        "",
        "Commands are secret-free readiness gates. They do not call external models, start",
        "containers or VMs, control Mission Control runtime behavior, or change governed tool",
        "powers.",
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
        raise SandboxVmPocReviewPacketError(f"required packet input is missing: {path}")
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
        raise SandboxVmPocReviewPacketError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def _require_project_root(repo_root: Path) -> None:
    missing = [marker.as_posix() for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        raise SandboxVmPocReviewPacketError(
            "must be run from the Ithildin repo root; missing markers: " + ", ".join(missing)
        )


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM proof-of-concept review packet check",
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

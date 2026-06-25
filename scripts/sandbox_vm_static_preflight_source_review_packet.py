"""Build a focused sandbox/VM static preflight source-review packet."""

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

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    no_new_powers_guardrail,
    sandbox_vm_poc_review_packet,
    sandbox_vm_static_preflight_implementation_gate,
    sandbox_vm_static_profile_fixture_contract_check,
    sandbox_vm_static_profile_negative_fixtures_check,
    sandbox_vm_static_profile_preflight_plan_check,
    tool_surface_invariant_gate,
)

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/sandbox-vm-static-preflight-source-review")
HASH_MANIFEST = "sandbox-vm-static-preflight-source-review-artifact-hashes.json"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
CONTRACT_DOCS = [
    Path("docs/codex/sandbox-vm-static-profile-preflight-plan.md"),
    Path("docs/codex/sandbox-vm-static-profile-fixture-contract.md"),
    Path("docs/codex/sandbox-vm-static-profile-negative-fixtures.md"),
    Path("docs/codex/sandbox-vm-static-preflight-implementation-decision.md"),
    Path("docs/codex/sandbox-vm-static-preflight-source-review.md"),
    Path("docs/codex/sandbox-vm-static-preflight-disposition-plan.md"),
    Path("docs/codex/sandbox-vm-static-preflight-external-response-intake.md"),
    Path("docs/codex/sandbox-vm-preflight-contract.md"),
    Path("docs/codex/sandbox-vm-profile-contract.md"),
    Path("docs/codex/sandbox-vm-worker-boundary-charter.md"),
    Path("docs/codex/enterprise-readiness-runway.md"),
]
FIXTURE_DOCS = [
    Path("docs/codex/fixtures/sandbox-vm-static-profile.local-preview.example.json"),
]
COMMANDS = [
    ["make", "sandbox-vm-static-profile-preflight-plan-check"],
    ["make", "sandbox-vm-static-profile-fixture-contract-check"],
    ["make", "sandbox-vm-static-profile-negative-fixtures-check"],
    ["make", "sandbox-vm-static-preflight"],
    ["make", "sandbox-vm-static-preflight-negative-transcripts"],
    ["make", "sandbox-vm-static-preflight-implementation-gate"],
    ["make", "sandbox-vm-poc-review-packet-check"],
    ["make", "no-new-powers-guardrail"],
    ["make", "tool-surface-invariant-gate"],
]


class SandboxVmStaticPreflightSourceReviewPacketError(RuntimeError):
    """Raised when the static preflight source-review packet cannot be built."""


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
    except SandboxVmStaticPreflightSourceReviewPacketError as exc:
        print(f"sandbox/VM static preflight source-review packet failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built sandbox/VM static preflight source-review packet at {output_dir}")
    return 0


def build_check_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    runway = _read(repo_root / "docs/codex/enterprise-readiness-runway.md")
    source_review_doc = _read(repo_root / "docs/codex/sandbox-vm-static-preflight-source-review.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "sandbox-vm-static-preflight-source-review"
        try:
            build_packet(
                repo_root=repo_root,
                output_dir=output_dir,
                allow_dirty=True,
                run_commands=False,
            )
        except SandboxVmStaticPreflightSourceReviewPacketError as exc:
            failures.append(str(exc))
            artifact_names: set[str] = set()
            hashes: dict[str, Any] = {"artifacts": []}
            prompt = ""
            index = ""
            validation = ""
        else:
            artifact_names = {path.name for path in output_dir.iterdir()}
            hashes = json.loads((output_dir / HASH_MANIFEST).read_text(encoding="utf-8"))
            prompt = (
                output_dir / "01_SANDBOX_VM_STATIC_PREFLIGHT_SOURCE_REVIEW_PROMPT.md"
            ).read_text(encoding="utf-8")
            index = (
                output_dir / "00_SANDBOX_VM_STATIC_PREFLIGHT_SOURCE_REVIEW_INDEX.md"
            ).read_text(encoding="utf-8")
            validation = (output_dir / "04_SANDBOX_VM_STATIC_PREFLIGHT_VALIDATION.md").read_text(
                encoding="utf-8"
            )

    expected = {
        "00_SANDBOX_VM_STATIC_PREFLIGHT_SOURCE_REVIEW_INDEX.md",
        "01_SANDBOX_VM_STATIC_PREFLIGHT_SOURCE_REVIEW_PROMPT.md",
        "02_SANDBOX_VM_STATIC_PREFLIGHT_CONTRACTS.md",
        "03_SANDBOX_VM_STATIC_PREFLIGHT_FIXTURES.md",
        "04_SANDBOX_VM_STATIC_PREFLIGHT_VALIDATION.md",
        "05_SANDBOX_VM_STATIC_PREFLIGHT_POC_EVIDENCE.md",
        "06_SANDBOX_VM_STATIC_PREFLIGHT_INTAKE_COMMANDS.md",
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
    if "Finding namespace: `EXT-SANDBOX-PREFLIGHT-###`" not in prompt:
        failures.append("packet prompt is missing EXT-SANDBOX-PREFLIGHT finding namespace")
    for phrase in [
        '"runtime_changes_allowed": false',
        '"mission_control_runtime_allowed": false',
        '"local_model_invocation_allowed": false',
        '"sandbox_orchestration_allowed": false',
        '"trusted_host_promotion_allowed": false',
        '"new_power_classes_allowed": false',
    ]:
        if phrase not in validation:
            failures.append(f"validation evidence is missing boundary flag: {phrase}")
    if "what this packet does not prove" not in index.lower():
        failures.append("packet index is missing what-this-packet-does-not-prove section")
    for target in [
        "sandbox-vm-static-preflight-source-review-packet:",
        "sandbox-vm-static-preflight-source-review-packet-check:",
    ]:
        if target not in makefile:
            failures.append(f"Make target is missing: {target.rstrip(':')}")
    if "sandbox-vm-static-preflight-source-review-packet-check" not in release_check_body:
        failures.append(
            "sandbox-vm-static-preflight-source-review-packet-check missing from release-check"
        )
    if "$(MAKE) sandbox-vm-static-preflight-source-review-packet" not in review_candidate_body:
        failures.append(
            "sandbox-vm-static-preflight-source-review-packet missing from review-candidate"
        )
    if "make sandbox-vm-static-preflight-source-review-packet" not in readme:
        failures.append("README is missing sandbox/VM static preflight source-review command")
    if "sandbox-vm-static-preflight-source-review.md" not in runway:
        failures.append("enterprise runway is missing static preflight source-review pointer")
    if "EXT-SANDBOX-PREFLIGHT-###" not in source_review_doc:
        failures.append("source-review handoff doc is missing finding namespace")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "output_dir": str(DEFAULT_OUTPUT_DIR),
        "artifact_count": len(expected),
        "tool_count": 24,
        "runtime_changes_allowed": False,
        "cli_only_fixture_preflight_runner_allowed": True,
        "cli_only_fixture_preflight_runner_implemented": True,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "network_expansion_allowed": False,
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
        raise SandboxVmStaticPreflightSourceReviewPacketError(
            "working tree is dirty; commit before source-review handoff"
        )

    preflight_plan = sandbox_vm_static_profile_preflight_plan_check.build_report(repo_root)
    fixture_contract = sandbox_vm_static_profile_fixture_contract_check.build_report(repo_root)
    negative_fixtures = sandbox_vm_static_profile_negative_fixtures_check.build_report(repo_root)
    implementation_gate = sandbox_vm_static_preflight_implementation_gate.build_report(repo_root)
    poc_packet = sandbox_vm_poc_review_packet.build_check_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    failures = [
        *(f"preflight plan: {failure}" for failure in preflight_plan["failures"]),
        *(f"fixture contract: {failure}" for failure in fixture_contract["failures"]),
        *(f"negative fixtures: {failure}" for failure in negative_fixtures["failures"]),
        *(f"implementation gate: {failure}" for failure in implementation_gate["failures"]),
        *(f"POC packet: {failure}" for failure in poc_packet["failures"]),
        *(f"no-new-powers: {failure}" for failure in no_new_powers["failures"]),
        *(f"tool-surface: {failure}" for failure in tool_surface["failures"]),
    ]
    if failures:
        raise SandboxVmStaticPreflightSourceReviewPacketError("; ".join(failures))

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context = {
        "commit": commit,
        "dirty": dirty,
        "run_commands": run_commands,
        "preflight_plan": preflight_plan,
        "fixture_contract": fixture_contract,
        "negative_fixtures": negative_fixtures,
        "implementation_gate": implementation_gate,
        "poc_packet": poc_packet,
        "no_new_powers": no_new_powers,
        "tool_surface": tool_surface,
    }
    files = {
        "00_SANDBOX_VM_STATIC_PREFLIGHT_SOURCE_REVIEW_INDEX.md": _index(context),
        "01_SANDBOX_VM_STATIC_PREFLIGHT_SOURCE_REVIEW_PROMPT.md": _prompt(context),
        "02_SANDBOX_VM_STATIC_PREFLIGHT_CONTRACTS.md": _bundle_docs(repo_root, CONTRACT_DOCS),
        "03_SANDBOX_VM_STATIC_PREFLIGHT_FIXTURES.md": _bundle_docs(repo_root, FIXTURE_DOCS),
        "04_SANDBOX_VM_STATIC_PREFLIGHT_VALIDATION.md": _validation_evidence(context),
        "05_SANDBOX_VM_STATIC_PREFLIGHT_POC_EVIDENCE.md": _poc_evidence(repo_root),
        "06_SANDBOX_VM_STATIC_PREFLIGHT_INTAKE_COMMANDS.md": _command_evidence(
            run_commands=run_commands
        ),
    }
    for relative, content in files.items():
        output_dir.joinpath(relative).write_text(content.rstrip() + "\n", encoding="utf-8")
    _write_json(output_dir / HASH_MANIFEST, {"artifacts": _hashes(output_dir)})
    return output_dir


def _index(context: dict[str, Any]) -> str:
    return f"""# Sandbox/VM Static Preflight Source Review Packet

This packet packages the source-review handoff for Ithildin's static sandbox/VM profile preflight
lane. It is a review packet for deciding whether a later implementation proposal for a read-only,
fixture-only preflight runner may be planned.

## Boundary

- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Command evidence executed: `{str(context["run_commands"]).lower()}`.
- tool count remains `{context["tool_surface"]["tool_count"]}`.
- CLI-only fixture preflight runner: present.
- Live sandbox/runtime control: absent.
- Finding namespace: `EXT-SANDBOX-PREFLIGHT-###`.
- This packet includes CLI-only static fixture preflight evidence. It does not add API endpoints,
  MCP tools, executors, tool manifests, policy rules, local model invocation, Mission Control
  runtime behavior, sandbox orchestration, VM lifecycle control, Docker socket access, Kubernetes
  control, browser automation, shell execution, arbitrary HTTP, broad filesystem writes,
  trusted-host promotion, SIEM adapters, production identity, runtime Postgres, hosted telemetry,
  plugin SDK behavior, compliance automation, public security-product claims, or new governed tool
  powers.

## Artifacts

1. `00_SANDBOX_VM_STATIC_PREFLIGHT_SOURCE_REVIEW_INDEX.md`
2. `01_SANDBOX_VM_STATIC_PREFLIGHT_SOURCE_REVIEW_PROMPT.md`
3. `02_SANDBOX_VM_STATIC_PREFLIGHT_CONTRACTS.md`
4. `03_SANDBOX_VM_STATIC_PREFLIGHT_FIXTURES.md`
5. `04_SANDBOX_VM_STATIC_PREFLIGHT_VALIDATION.md`
6. `05_SANDBOX_VM_STATIC_PREFLIGHT_POC_EVIDENCE.md`
7. `06_SANDBOX_VM_STATIC_PREFLIGHT_INTAKE_COMMANDS.md`
8. `sandbox-vm-static-preflight-source-review-artifact-hashes.json`

## What This Packet Does Not Prove

This packet does not prove OS isolation, live sandbox validation, VM/container lifecycle safety,
Mission Control runtime correctness, local model plan quality, trusted-host promotion correctness,
SIEM custody, production deployment safety, compliance automation, or activity outside
Ithildin-mediated actions.
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# Sandbox/VM Static Preflight Source Review Prompt

You are reviewing Ithildin's static sandbox/VM profile preflight lane. Treat this as a source-review
handoff for design, fixture, and CLI-only preflight evidence, not as approval of a live
VM/container integration.

Reviewed commit: `{context["commit"]}`
Area: `sandbox-vm-static-preflight`
Finding namespace: `EXT-SANDBOX-PREFLIGHT-###`

## Scope

Please review:

- whether the static profile preflight plan is precise enough to support a later implementation
  proposal for a read-only fixture-only preflight runner;
- whether the committed example fixture uses safe labels and false authority flags only;
- whether the negative fixture cases reject unsupported schemas, raw path-shaped labels, broad
  network posture, promotion claims, missing warnings, and false-authority overclaims;
- whether validation evidence is secret-free and confirms no-new-powers/tool-surface invariants;
- whether the packet wording avoids claims of OS isolation, sandbox orchestration, Mission Control
  execution authority, local model invocation, trusted-host promotion, production security, SIEM
  custody, compliance automation, or new governed tool powers.

## Required Disposition

Say whether this packet is coherent enough to plan a later implementation proposal for a read-only
static profile preflight runner that consumes committed/operator-supplied fixture metadata only.
If not, name the missing artifact, ambiguous claim, or required follow-up.

Do not approve new governed tool powers, sandbox orchestration, VM/container lifecycle management,
Docker socket access, Kubernetes/browser/shell tools, arbitrary HTTP, broad filesystem writes,
trusted-host promotion, Mission Control execution authority, local model invocation, production
identity, runtime Postgres, hosted telemetry, SIEM adapters, compliance positioning, remote MCP,
public/security-product positioning, or plugin SDK work.
"""


def _bundle_docs(repo_root: Path, paths: list[Path]) -> str:
    parts = ["# Bundle"]
    for path in paths:
        parts.extend(["", f"## {path.as_posix()}", "", _fenced(_read(repo_root / path), path)])
    return "\n".join(parts)


def _validation_evidence(context: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Sandbox/VM Static Preflight Validation Evidence",
            "",
            "The following evidence is generated from deterministic local checks. It is",
            "secret-free and does not start services, containers, VMs, local models,",
            "Mission Control, or governed tool",
            "calls.",
            "",
            "```json",
            json.dumps(
                {
                    "preflight_plan": context["preflight_plan"],
                    "fixture_contract": context["fixture_contract"],
                    "negative_fixtures": context["negative_fixtures"],
                    "implementation_gate": context["implementation_gate"],
                    "poc_packet": context["poc_packet"],
                    "no_new_powers": context["no_new_powers"],
                    "tool_surface": context["tool_surface"],
                    "runtime_changes_allowed": False,
                    "cli_only_fixture_preflight_runner_allowed": True,
                    "cli_only_fixture_preflight_runner_implemented": True,
                    "mission_control_runtime_allowed": False,
                    "local_model_invocation_allowed": False,
                    "sandbox_orchestration_allowed": False,
                    "trusted_host_promotion_allowed": False,
                    "new_power_classes_allowed": False,
                },
                indent=2,
                sort_keys=True,
            ),
            "```",
        ]
    )


def _poc_evidence(repo_root: Path) -> str:
    latest = repo_root / "var/review-packets/v3/sandbox-vm-poc-review"
    return f"""# Sandbox/VM Proof-Of-Concept Packet Pointer

The broader proof-of-concept packet is generated by:

```sh
make sandbox-vm-poc-review-packet
```

Default output path:

```text
{latest.as_posix()}
```

This static-preflight source-review packet does not rely on ignored local packet contents for
correctness. The source docs and deterministic check reports are bundled directly in this packet.
"""


def _command_evidence(*, run_commands: bool) -> str:
    outputs = [_command_output(command, run_commands=run_commands) for command in COMMANDS]
    failures = [output for output in outputs if output["returncode"] != 0]
    if failures and run_commands:
        failed = ", ".join(" ".join(output["command"]) for output in failures)
        raise SandboxVmStaticPreflightSourceReviewPacketError(f"evidence command failed: {failed}")
    lines = [
        "# Sandbox/VM Static Preflight Command Evidence",
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


def _fenced(content: str, path: Path) -> str:
    if path.suffix == ".json":
        language = "json"
    else:
        language = "md"
    return f"```{language}\n{content.rstrip()}\n```"


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
        raise SandboxVmStaticPreflightSourceReviewPacketError(
            f"required packet input is missing: {path}"
        )
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
        raise SandboxVmStaticPreflightSourceReviewPacketError(
            result.stderr.strip() or "git command failed"
        )
    return result.stdout.strip()


def _require_project_root(repo_root: Path) -> None:
    missing = [marker.as_posix() for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        raise SandboxVmStaticPreflightSourceReviewPacketError(
            "must be run from the Ithildin repo root; missing markers: " + ", ".join(missing)
        )


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM static preflight source-review packet check",
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
        f"network_expansion_allowed: {str(report['network_expansion_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

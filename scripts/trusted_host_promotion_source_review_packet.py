"""Build a focused trusted-host promotion source-review packet."""

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
    post_rc_decision_gate,
    post_rc_decision_register_check,
    review_docs,
    sandbox_promotion_evidence_contract_check,
    tool_surface_invariant_gate,
    trusted_host_promotion_decision_intake_check,
    trusted_host_promotion_implementation_plan_check,
    trusted_host_promotion_negative_fixtures_check,
    trusted_host_promotion_state_machine_check,
    trusted_host_promotion_zone_contract_check,
)

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/trusted-host-promotion-source-review")
HASH_MANIFEST = "trusted-host-promotion-source-review-artifact-hashes.json"
SOURCE_REVIEW_DOC = "docs/codex/trusted-host-promotion-source-review.md"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
CONTRACT_DOCS = [
    Path("docs/codex/sandbox-promotion-evidence-contract.md"),
    Path("docs/codex/trusted-host-promotion-decision-intake.md"),
    Path("docs/codex/trusted-host-promotion-state-machine.md"),
    Path("docs/codex/trusted-host-promotion-negative-fixtures.md"),
    Path("docs/codex/trusted-host-promotion-zone-contract.md"),
    Path("docs/codex/trusted-host-promotion-implementation-plan.md"),
    Path("docs/codex/trusted-host-promotion-source-review.md"),
    Path("docs/codex/post-rc-decision-gate.md"),
    Path("docs/codex/post-rc-decision-register.md"),
    Path("docs/codex/enterprise-readiness-runway.md"),
    Path("docs/codex/enterprise-readiness-gap-matrix.md"),
]
COMMANDS = [
    ["make", "sandbox-promotion-evidence-contract-check"],
    ["make", "trusted-host-promotion-decision-intake-check"],
    ["make", "trusted-host-promotion-state-machine-check"],
    ["make", "trusted-host-promotion-negative-fixtures-check"],
    ["make", "trusted-host-promotion-zone-contract-check"],
    ["make", "trusted-host-promotion-implementation-plan-check"],
    ["make", "post-rc-decision-gate"],
    ["make", "post-rc-decision-register-check"],
    ["make", "no-new-powers-guardrail"],
    ["make", "tool-surface-invariant-gate"],
]


class TrustedHostPromotionSourceReviewPacketError(RuntimeError):
    """Raised when the trusted-host promotion source-review packet cannot be built."""


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
    except TrustedHostPromotionSourceReviewPacketError as exc:
        print(f"trusted-host promotion source-review packet failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built trusted-host promotion source-review packet at {output_dir}")
    return 0


def build_check_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    runway = _read(repo_root / "docs/codex/enterprise-readiness-runway.md")
    gap_matrix = _read(repo_root / "docs/codex/enterprise-readiness-gap-matrix.md")
    decision_register = _read(repo_root / "docs/codex/post-rc-decision-register.md")
    source_review_doc = _read(repo_root / SOURCE_REVIEW_DOC)
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "trusted-host-promotion-source-review"
        try:
            build_packet(
                repo_root=repo_root,
                output_dir=output_dir,
                allow_dirty=True,
                run_commands=False,
            )
        except TrustedHostPromotionSourceReviewPacketError as exc:
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
                output_dir / "01_TRUSTED_HOST_PROMOTION_SOURCE_REVIEW_PROMPT.md"
            ).read_text(encoding="utf-8")
            index = (
                output_dir / "00_TRUSTED_HOST_PROMOTION_SOURCE_REVIEW_INDEX.md"
            ).read_text(encoding="utf-8")
            validation = (
                output_dir / "03_TRUSTED_HOST_PROMOTION_GATE_EVIDENCE.json"
            ).read_text(encoding="utf-8")

    expected = {
        "00_TRUSTED_HOST_PROMOTION_SOURCE_REVIEW_INDEX.md",
        "01_TRUSTED_HOST_PROMOTION_SOURCE_REVIEW_PROMPT.md",
        "02_TRUSTED_HOST_PROMOTION_CONTRACTS.md",
        "03_TRUSTED_HOST_PROMOTION_GATE_EVIDENCE.json",
        "04_TRUSTED_HOST_PROMOTION_COMMAND_EVIDENCE.md",
        "05_TRUSTED_HOST_PROMOTION_DECISION_CHECKLIST.md",
        "06_TRUSTED_HOST_PROMOTION_INTAKE_COMMANDS.md",
        HASH_MANIFEST,
    }
    missing = expected - artifact_names
    if missing:
        failures.append("packet missing artifacts: " + ", ".join(sorted(missing)))
    hashed = {entry["path"] for entry in hashes.get("artifacts", [])}
    if HASH_MANIFEST in hashed:
        failures.append("hash manifest must not hash itself")
    if expected - {HASH_MANIFEST} - hashed:
        failures.append("artifact hashes do not cover generated review files")
    if "Finding namespace: `EXT-TRUSTED-HOST-###`" not in prompt:
        failures.append("packet prompt is missing EXT-TRUSTED-HOST finding namespace")
    for phrase in [
        '"trusted_host_promotion_allowed": false',
        '"direct_host_writes_allowed": false',
        '"runtime_changes_allowed": false',
        '"mission_control_runtime_allowed": false',
        '"local_model_invocation_allowed": false',
        '"sandbox_orchestration_allowed": false',
        '"siem_adapter_allowed": false',
        '"new_power_classes_allowed": false',
    ]:
        if phrase not in validation:
            failures.append(f"validation evidence is missing boundary flag: {phrase}")
    if "What This Packet Does Not Prove" not in index:
        failures.append("packet index is missing what-this-packet-does-not-prove section")
    if "continue_design_only" not in prompt:
        failures.append("packet prompt is missing required disposition vocabulary")
    for target in [
        "trusted-host-promotion-source-review-packet:",
        "trusted-host-promotion-source-review-packet-check:",
    ]:
        if target not in makefile:
            failures.append(f"Make target is missing: {target.rstrip(':')}")
    if "trusted-host-promotion-source-review-packet-check" not in release_check_body:
        failures.append("trusted-host source-review packet check missing from release-check")
    if "$(MAKE) trusted-host-promotion-source-review-packet" not in review_candidate_body:
        failures.append("trusted-host source-review packet missing from review-candidate")
    if "make trusted-host-promotion-source-review-packet" not in readme:
        failures.append("README is missing trusted-host source-review packet command")
    if SOURCE_REVIEW_DOC not in review_docs.REVIEW_DOCS:
        failures.append("trusted-host source-review doc is missing from review-doc metadata")
    if SOURCE_REVIEW_DOC not in docs_site:
        failures.append("trusted-host source-review doc is missing from docs-site inputs")
    if "Trusted-Host Promotion Source Review" not in review_index:
        failures.append("review-doc index is missing trusted-host source-review doc")
    if "trusted-host-promotion-source-review.md" not in runway:
        failures.append("enterprise runway is missing trusted-host source-review pointer")
    if "trusted-host-promotion-source-review.md" not in gap_matrix:
        failures.append("enterprise gap matrix is missing trusted-host source-review pointer")
    if "trusted-host-promotion-source-review.md" not in decision_register:
        failures.append("post-RC decision register is missing trusted-host source-review pointer")
    if "EXT-TRUSTED-HOST-###" not in source_review_doc:
        failures.append("source-review handoff doc is missing finding namespace")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "output_dir": str(DEFAULT_OUTPUT_DIR),
        "artifact_count": len(expected),
        "tool_count": 24,
        "erg_005_status": "blocked",
        "prd_id": "PRD-TRUSTED-HOST-001",
        "finding_namespace": "EXT-TRUSTED-HOST-###",
        "runtime_changes_allowed": False,
        "trusted_host_promotion_allowed": False,
        "direct_host_writes_allowed": False,
        "overwrite_delete_move_allowed": False,
        "broad_archive_extraction_allowed": False,
        "automatic_promotion_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
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
        raise TrustedHostPromotionSourceReviewPacketError(
            "working tree is dirty; commit before source-review handoff"
        )

    context = _build_context(repo_root, commit=commit, dirty=dirty, run_commands=run_commands)
    failures = [
        failure
        for key in [
            "promotion_evidence_contract",
            "decision_intake",
            "state_machine",
            "negative_fixtures",
            "zone_contract",
            "implementation_plan",
            "post_rc_decision_gate",
            "post_rc_decision_register",
            "no_new_powers",
            "tool_surface",
        ]
        for failure in context[key]["failures"]
    ]
    if failures:
        raise TrustedHostPromotionSourceReviewPacketError("; ".join(failures))

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    files = {
        "00_TRUSTED_HOST_PROMOTION_SOURCE_REVIEW_INDEX.md": _index(context),
        "01_TRUSTED_HOST_PROMOTION_SOURCE_REVIEW_PROMPT.md": _prompt(context),
        "02_TRUSTED_HOST_PROMOTION_CONTRACTS.md": _bundle_docs(repo_root, CONTRACT_DOCS),
        "03_TRUSTED_HOST_PROMOTION_GATE_EVIDENCE.json": json.dumps(
            _gate_evidence(context),
            indent=2,
            sort_keys=True,
        ),
        "04_TRUSTED_HOST_PROMOTION_COMMAND_EVIDENCE.md": _command_evidence(
            run_commands=run_commands
        ),
        "05_TRUSTED_HOST_PROMOTION_DECISION_CHECKLIST.md": _decision_checklist(context),
        "06_TRUSTED_HOST_PROMOTION_INTAKE_COMMANDS.md": _intake_commands(context),
    }
    for relative, content in files.items():
        output_dir.joinpath(relative).write_text(content.rstrip() + "\n", encoding="utf-8")
    _write_json(output_dir / HASH_MANIFEST, {"artifacts": _hashes(output_dir)})
    return output_dir


def _build_context(
    repo_root: Path, *, commit: str, dirty: bool, run_commands: bool
) -> dict[str, Any]:
    return {
        "commit": commit,
        "dirty": dirty,
        "run_commands": run_commands,
        "promotion_evidence_contract": sandbox_promotion_evidence_contract_check.build_report(
            repo_root
        ),
        "decision_intake": trusted_host_promotion_decision_intake_check.build_report(
            repo_root
        ),
        "state_machine": trusted_host_promotion_state_machine_check.build_report(repo_root),
        "negative_fixtures": trusted_host_promotion_negative_fixtures_check.build_report(
            repo_root
        ),
        "zone_contract": trusted_host_promotion_zone_contract_check.build_report(repo_root),
        "implementation_plan": trusted_host_promotion_implementation_plan_check.build_report(
            repo_root
        ),
        "post_rc_decision_gate": post_rc_decision_gate.build_report(repo_root),
        "post_rc_decision_register": post_rc_decision_register_check.build_report(repo_root),
        "no_new_powers": no_new_powers_guardrail.build_report(repo_root),
        "tool_surface": tool_surface_invariant_gate.build_report(repo_root),
    }


def _index(context: dict[str, Any]) -> str:
    return f"""# Trusted-Host Promotion Source Review Packet

This packet packages Ithildin's trusted-host promotion planning lane for focused review. It is a
design/source-review packet for deciding whether the lane can continue toward a future
implementation decision. It is not an implementation approval.

## Boundary

- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Command evidence executed: `{str(context["run_commands"]).lower()}`.
- Tool count remains `{context["tool_surface"]["tool_count"]}`.
- ERG lane: `ERG-005`.
- Post-RC decision ID: `PRD-TRUSTED-HOST-001`.
- Finding namespace: `EXT-TRUSTED-HOST-###`.
- Current runtime state: `promotion_status: not_promoted` only.
- Trusted-host promotion: not implemented.
- Direct host writes: not implemented.

## Artifacts

1. `00_TRUSTED_HOST_PROMOTION_SOURCE_REVIEW_INDEX.md`
2. `01_TRUSTED_HOST_PROMOTION_SOURCE_REVIEW_PROMPT.md`
3. `02_TRUSTED_HOST_PROMOTION_CONTRACTS.md`
4. `03_TRUSTED_HOST_PROMOTION_GATE_EVIDENCE.json`
5. `04_TRUSTED_HOST_PROMOTION_COMMAND_EVIDENCE.md`
6. `05_TRUSTED_HOST_PROMOTION_DECISION_CHECKLIST.md`
7. `06_TRUSTED_HOST_PROMOTION_INTAKE_COMMANDS.md`
8. `trusted-host-promotion-source-review-artifact-hashes.json`

## What This Packet Does Not Prove

This packet does not prove runtime implementation safety, host promotion correctness, broad
filesystem write safety, OS isolation, sandbox orchestration, Mission Control runtime correctness,
local model behavior, SIEM custody, production deployment safety, compliance automation, or activity
outside Ithildin-mediated actions.
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# Trusted-Host Promotion Source Review Prompt

You are reviewing Ithildin's trusted-host promotion lane. Treat this as a source-review/design
handoff for the planning artifacts only, not as approval of a runtime host-promotion integration.

Reviewed commit: `{context["commit"]}`
Area: `trusted-host-promotion`
Finding namespace: `EXT-TRUSTED-HOST-###`

## Scope

Please review:

- whether the sandbox/staging/approved zone labels are precise and non-authoritative;
- whether the implementation-plan skeleton requires exact artifact hash binding, approval binding,
  one-time scope evidence, policy/manifest evidence, and source/staging/approved hash matching;
- whether the state machine blocks replay, stale evidence, invalid transitions, conflict cases, and
  recovery ambiguity before any host placement could be completed;
- whether the negative fixture families cover unsafe labels, path escape, overwrite/delete/move,
  automatic promotion, broad archive extraction, sensitive payloads, and product-boundary
  overclaims;
- whether the lane keeps Mission Control, local model invocation, VM/container lifecycle,
  sandbox orchestration, SIEM adapters, production identity, runtime Postgres, hosted telemetry,
  shell/Docker/Kubernetes/browser powers, arbitrary HTTP, broad filesystem writes, and compliance
  positioning out of scope;
- which source-review, transcript, decision-record, or gate evidence is still missing before a
  future implementation proposal may be considered.

## Required Disposition

Choose one disposition:

- `continue_design_only`: current evidence is coherent for further design and review packets.
- `revise_before_more_planning`: gaps or ambiguous claims must be fixed before more planning.
- `block_runtime_implementation`: a blocking risk prevents implementation planning until a new
  decision record resolves it.

Do not approve runtime implementation, host promotion, direct host writes, overwrite/delete/move,
archive extraction, automatic promotion, Mission Control execution authority, local model
invocation, VM/container lifecycle control, sandbox orchestration, SIEM adapters, production
identity, runtime Postgres, hosted telemetry, remote MCP, shell/Docker/Kubernetes/browser governed
powers, arbitrary HTTP, broad filesystem writes, compliance automation, or public/security-product
positioning.
"""


def _gate_evidence(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "promotion_evidence_contract": context["promotion_evidence_contract"],
        "decision_intake": context["decision_intake"],
        "state_machine": context["state_machine"],
        "negative_fixtures": context["negative_fixtures"],
        "zone_contract": context["zone_contract"],
        "implementation_plan": context["implementation_plan"],
        "post_rc_decision_gate": context["post_rc_decision_gate"],
        "post_rc_decision_register": context["post_rc_decision_register"],
        "no_new_powers": context["no_new_powers"],
        "tool_surface": context["tool_surface"],
        "runtime_changes_allowed": False,
        "trusted_host_promotion_allowed": False,
        "direct_host_writes_allowed": False,
        "overwrite_delete_move_allowed": False,
        "broad_archive_extraction_allowed": False,
        "automatic_promotion_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "siem_adapter_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
    }


def _decision_checklist(context: dict[str, Any]) -> str:
    return f"""# Trusted-Host Promotion Decision Checklist

Current disposition target: design/source-review only.

## Required Checks Before Any Future Runtime Proposal

- `make sandbox-promotion-evidence-contract-check`
- `make trusted-host-promotion-decision-intake-check`
- `make trusted-host-promotion-state-machine-check`
- `make trusted-host-promotion-negative-fixtures-check`
- `make trusted-host-promotion-zone-contract-check`
- `make trusted-host-promotion-implementation-plan-check`
- `make trusted-host-promotion-source-review-packet-check`
- `make post-rc-decision-gate`
- `make post-rc-decision-register-check`
- `make no-new-powers-guardrail`
- `make tool-surface-invariant-gate`

## Current Boundary Evidence

- Tool count: `{context["tool_surface"]["tool_count"]}`.
- Trusted-host promotion allowed: `false`.
- Direct host writes allowed: `false`.
- Runtime changes allowed: `false`.
- Current runtime/demo promotion state: `not_promoted`.

## Required Future Evidence

- favorable external/source-review disposition for `EXT-TRUSTED-HOST-###`;
- conflict/replay/stale/path-escape/sensitive-payload/product-overclaim transcripts for the exact
  future runtime surface;
- exact implementation decision record before any runtime path;
- release-check wiring for the exact future runtime checks;
- packet redaction scan with zero findings.
"""


def _intake_commands(context: dict[str, Any]) -> str:
    commands = "\n".join(f"- `{' '.join(command)}`" for command in COMMANDS)
    return f"""# Trusted-Host Promotion Intake Commands

Reviewed commit: `{context["commit"]}`

Run these commands from the Ithildin repo root:

{commands}

Generate this packet:

```sh
make trusted-host-promotion-source-review-packet
```

Validate this packet:

```sh
make trusted-host-promotion-source-review-packet-check
```
"""


def _command_evidence(*, run_commands: bool) -> str:
    outputs = [_command_output(command, run_commands=run_commands) for command in COMMANDS]
    failures = [output for output in outputs if output["returncode"] != 0]
    if failures and run_commands:
        failed = ", ".join(" ".join(output["command"]) for output in failures)
        raise TrustedHostPromotionSourceReviewPacketError(f"evidence command failed: {failed}")
    lines = [
        "# Trusted-Host Promotion Command Evidence",
        "",
        "These commands are deterministic local checks. They do not start services, inspect live",
        "VMs/containers, invoke local models, call Mission Control, perform host promotion, or run",
        "governed tool calls.",
    ]
    for output in outputs:
        lines.extend(
            [
                "",
                f"## `{' '.join(output['command'])}`",
                "",
                f"returncode: `{output['returncode']}`",
                "",
                "```text",
                output["stdout"].strip() or "(no stdout)",
                "```",
            ]
        )
        if output["stderr"]:
            lines.extend(["", "stderr:", "", "```text", output["stderr"].strip(), "```"])
    return "\n".join(lines)


def _bundle_docs(repo_root: Path, paths: list[Path]) -> str:
    parts = ["# Trusted-Host Promotion Contracts Bundle"]
    for path in paths:
        parts.extend(["", f"## {path.as_posix()}", "", _fenced(_read(repo_root / path), path)])
    return "\n".join(parts)


def _command_output(command: list[str], *, run_commands: bool) -> dict[str, Any]:
    if not run_commands:
        return {
            "command": command,
            "returncode": 0,
            "stdout": "(command execution skipped for packet check)",
            "stderr": "",
        }
    completed = subprocess.run(
        command,
        check=False,
        text=True,
        capture_output=True,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _hashes(output_dir: Path) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for path in sorted(output_dir.iterdir()):
        if path.name == HASH_MANIFEST:
            continue
        if not path.is_file():
            continue
        payload = path.read_bytes()
        artifacts.append(
            {
                "path": path.name,
                "bytes": len(payload),
                "sha256": "sha256:" + hashlib.sha256(payload).hexdigest(),
            }
        )
    return artifacts


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _fenced(text: str, path: Path) -> str:
    suffix = path.suffix.lower()
    lang = "json" if suffix == ".json" else "markdown"
    return f"```{lang}\n{text.rstrip()}\n```"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _git(repo_root: Path, args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def _require_project_root(repo_root: Path) -> None:
    missing = [path.as_posix() for path in PROJECT_MARKERS if not (repo_root / path).exists()]
    if missing:
        raise TrustedHostPromotionSourceReviewPacketError(
            "must be run from the Ithildin repo root; missing " + ", ".join(missing)
        )


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin trusted-host promotion source-review packet check",
        f"valid: {str(report['valid']).lower()}",
        f"output_dir: {report['output_dir']}",
        f"artifact_count: {report['artifact_count']}",
        f"tool_count: {report['tool_count']}",
        f"erg_005_status: {report['erg_005_status']}",
        f"prd_id: {report['prd_id']}",
        f"finding_namespace: {report['finding_namespace']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "trusted_host_promotion_allowed: "
        f"{str(report['trusted_host_promotion_allowed']).lower()}",
        f"direct_host_writes_allowed: {str(report['direct_host_writes_allowed']).lower()}",
        "overwrite_delete_move_allowed: "
        f"{str(report['overwrite_delete_move_allowed']).lower()}",
        "broad_archive_extraction_allowed: "
        f"{str(report['broad_archive_extraction_allowed']).lower()}",
        f"automatic_promotion_allowed: {str(report['automatic_promotion_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("")
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

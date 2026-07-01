"""Build the ERG-004 implementation-planning external-review bundle."""

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

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/sandbox-vm-live-poc-implementation-review")
HASH_MANIFEST = "sandbox-vm-live-poc-implementation-review-artifact-hashes.json"
DOC_REL = "docs/codex/sandbox-vm-live-poc-implementation-review-bundle.md"
DOC_TITLE = "Sandbox/VM Live POC Implementation Review Bundle"
TARGET = "sandbox-vm-live-poc-implementation-review-bundle"
CHECK_TARGET = "sandbox-vm-live-poc-implementation-review-bundle-check"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
ARTIFACTS = [
    "00_SANDBOX_VM_LIVE_POC_IMPLEMENTATION_REVIEW_INDEX.md",
    "01_SANDBOX_VM_LIVE_POC_IMPLEMENTATION_REVIEW_PROMPT.md",
    "02_ERG004_DECISION_AND_IMPLEMENTATION_PLAN.md",
    "03_ERG004_CONTRACTS_AND_PRECONDITIONS.md",
    "04_ERG004_STATIC_FIXTURE_AND_NEGATIVE_PLAN.md",
    "05_ERG004_COMMAND_EVIDENCE.md",
]
COMMANDS = [
    (
        "sandbox-vm-live-poc-decision-record-check",
        ["make", "sandbox-vm-live-poc-decision-record-check"],
    ),
    (
        "sandbox-vm-live-poc-implementation-plan-check",
        ["make", "sandbox-vm-live-poc-implementation-plan-check"],
    ),
    ("enterprise-active-route-clarity", ["make", "enterprise-active-route-clarity"]),
]
FORBIDDEN_APPROVAL_PHRASES = [
    "runtime implementation is approved",
    "live VM/container inspection is approved",
    "VM/container lifecycle management is approved",
    "sandbox orchestration is approved",
    "Mission Control runtime behavior is approved",
    "local model invocation is approved",
    "trusted-host promotion is approved",
    "new governed tool powers are approved",
    "public security product approved",
]


class SandboxVmLivePocImplementationReviewBundleError(RuntimeError):
    """Raised when the implementation-review bundle cannot be built."""


def build_bundle(
    *,
    repo_root: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    allow_dirty: bool = False,
    run_commands: bool = True,
) -> Path:
    _require_project_root(repo_root)
    commit = _git(repo_root, ["rev-parse", "HEAD"])
    dirty = bool(_git(repo_root, ["status", "--short"]))
    if dirty and not allow_dirty:
        raise SandboxVmLivePocImplementationReviewBundleError(
            "working tree is dirty; commit before ERG-004 implementation-review handoff"
        )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    command_reports = _build_command_reports(repo_root, run_commands=run_commands)
    files = {
        "00_SANDBOX_VM_LIVE_POC_IMPLEMENTATION_REVIEW_INDEX.md": _index(commit, dirty),
        "01_SANDBOX_VM_LIVE_POC_IMPLEMENTATION_REVIEW_PROMPT.md": _prompt(commit),
        "02_ERG004_DECISION_AND_IMPLEMENTATION_PLAN.md": _docs_bundle(
            "ERG-004 Decision And Implementation Plan",
            repo_root,
            [
                "docs/codex/sandbox-vm-live-poc-decision-record.md",
                "docs/codex/sandbox-vm-live-poc-implementation-plan.md",
                "docs/codex/enterprise-active-route-clarity.md",
            ],
        ),
        "03_ERG004_CONTRACTS_AND_PRECONDITIONS.md": _docs_bundle(
            "ERG-004 Contracts And Preconditions",
            repo_root,
            [
                "docs/codex/sandbox-vm-live-poc-evidence-contract.md",
                "docs/codex/sandbox-vm-live-poc-preconditions-map.md",
                "docs/codex/sandbox-vm-live-poc-preconditions-ready-check.md",
                "docs/codex/enterprise-sandbox-control-plane-readiness.md",
            ],
        ),
        "04_ERG004_STATIC_FIXTURE_AND_NEGATIVE_PLAN.md": _static_fixture_plan(),
        "05_ERG004_COMMAND_EVIDENCE.md": _command_evidence(commit, dirty, command_reports),
    }
    for name, content in files.items():
        _write(output_dir / name, content)
    _write_hashes(output_dir)
    return output_dir


def build_check_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_docs = _read(repo_root / "scripts/review_docs.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "implementation-review"
        try:
            build_bundle(
                repo_root=repo_root,
                output_dir=output_dir,
                allow_dirty=True,
                run_commands=False,
            )
        except SandboxVmLivePocImplementationReviewBundleError as exc:
            failures.append(str(exc))
            artifact_names: set[str] = set()
            hashes: dict[str, Any] = {"artifacts": []}
            contents: dict[str, str] = {}
        else:
            artifact_names = {path.name for path in output_dir.iterdir()}
            hashes = json.loads((output_dir / HASH_MANIFEST).read_text(encoding="utf-8"))
            contents = {
                name: (output_dir / name).read_text(encoding="utf-8") for name in ARTIFACTS
            }

    expected = set(ARTIFACTS) | {HASH_MANIFEST}
    missing = expected - artifact_names
    if missing:
        failures.append(
            "implementation-review bundle missing artifacts: " + ", ".join(sorted(missing))
        )
    hashed = {entry.get("path") for entry in hashes.get("artifacts", [])}
    if set(ARTIFACTS) - hashed:
        failures.append("artifact hashes do not cover generated markdown files")
    if HASH_MANIFEST in hashed:
        failures.append("hash manifest must not hash itself")

    index = contents.get("00_SANDBOX_VM_LIVE_POC_IMPLEMENTATION_REVIEW_INDEX.md", "")
    prompt = contents.get("01_SANDBOX_VM_LIVE_POC_IMPLEMENTATION_REVIEW_PROMPT.md", "")
    plan = contents.get("02_ERG004_DECISION_AND_IMPLEMENTATION_PLAN.md", "")
    contracts = contents.get("03_ERG004_CONTRACTS_AND_PRECONDITIONS.md", "")
    static_plan = contents.get("04_ERG004_STATIC_FIXTURE_AND_NEGATIVE_PLAN.md", "")
    evidence = contents.get("05_ERG004_COMMAND_EVIDENCE.md", "")

    for phrase in [
        "Tool count remains `24`",
        "Current `ERG-004` status: `ready_for_implementation_planning_only`",
        "VM-first and operator-managed",
        "What This Bundle Does Not Prove",
    ]:
        if phrase not in index:
            failures.append(f"implementation-review index is missing phrase: {phrase}")
    for phrase in [
        "Finding namespace: `EXT-LIVE-IMPL-###`",
        "planning artifacts complete enough",
        "Do not approve runtime implementation",
        "Do not approve live VM/container inspection",
        "Do not approve local model invocation",
    ]:
        if phrase not in prompt:
            failures.append(f"implementation-review prompt is missing phrase: {phrase}")
    for phrase in [
        "sandbox-vm-live-poc-decision-record.md",
        "sandbox-vm-live-poc-implementation-plan.md",
        "enterprise-active-route-clarity.md",
        "ready_for_implementation_planning_only",
    ]:
        if phrase not in plan:
            failures.append(f"implementation plan bundle is missing phrase: {phrase}")
    for phrase in [
        "sandbox-vm-live-poc-evidence-contract.md",
        "sandbox-vm-live-poc-preconditions-map.md",
        "sandbox-vm-live-poc-preconditions-ready-check.md",
        "enterprise-sandbox-control-plane-readiness.md",
    ]:
        if phrase not in contracts:
            failures.append(f"contracts bundle is missing phrase: {phrase}")
    for phrase in [
        "operator_intent_id",
        "vm_profile_hash",
        "mount_root_label",
        "network_posture_label",
        "cleanup_plan_hash",
        "failure_transcript_hash",
        "promotion_status: not_promoted",
        "Container profiles remain deferred",
    ]:
        if phrase not in static_plan:
            failures.append(f"static fixture plan is missing phrase: {phrase}")
    for phrase in [
        '"sandbox-vm-live-poc-decision-record-check"',
        '"sandbox-vm-live-poc-implementation-plan-check"',
        '"enterprise-active-route-clarity"',
        '"runtime_changes_allowed": false',
        '"runtime_implementation_allowed": false',
        '"live_vm_inspection_allowed": false',
        '"sandbox_orchestration_allowed": false',
        '"new_power_classes_allowed": false',
    ]:
        if phrase not in evidence:
            failures.append(f"command evidence is missing phrase: {phrase}")

    generated_text = "\n".join(contents.values())
    for phrase in FORBIDDEN_APPROVAL_PHRASES:
        if phrase.lower() in generated_text.lower():
            failures.append(f"implementation-review bundle contains forbidden phrase: {phrase}")

    for make_target in [f"{TARGET}:", f"{CHECK_TARGET}:"]:
        if make_target not in makefile:
            failures.append(f"Make target is missing: {make_target.rstrip(':')}")
    if CHECK_TARGET not in release_check_body and f"release-check: {CHECK_TARGET}" not in makefile:
        failures.append(f"{CHECK_TARGET} missing from release-check")
    if f"$(MAKE) {TARGET}" not in review_candidate_body:
        failures.append(f"{TARGET} missing from review-candidate")
    if CHECK_TARGET not in release_guardrails:
        failures.append(f"release guardrails do not require {CHECK_TARGET}")
    if f"$(MAKE) {TARGET}" not in release_guardrails:
        failures.append(f"release guardrails do not require review-candidate {TARGET}")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing implementation-review bundle command")
    if DOC_REL not in readme:
        failures.append("README is missing implementation-review bundle doc")
    if DOC_REL not in docs_site:
        failures.append("implementation-review bundle doc is missing from docs-site inputs")
    if DOC_REL not in review_docs:
        failures.append("implementation-review bundle doc is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing implementation-review bundle entry")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "output_dir": str(DEFAULT_OUTPUT_DIR),
        "artifact_count": len(expected),
        "tool_count": 24,
        "erg_004_status": "ready_for_implementation_planning_only",
        "finding_namespace": "EXT-LIVE-IMPL-###",
        "vm_first": True,
        "container_profiles_deferred": True,
        "implementation_planning_allowed": True,
        "runtime_changes_allowed": False,
        "runtime_implementation_allowed": False,
        "live_vm_inspection_allowed": False,
        "vm_container_lifecycle_allowed": False,
        "sandbox_orchestration_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "trusted_host_promotion_allowed": False,
        "api_mcp_profile_loading_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
        "external_review_required_before_runtime": True,
        "closes_erg_004": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM live POC implementation-review bundle",
        f"valid: {str(report['valid']).lower()}",
        f"output_dir: {report['output_dir']}",
        f"artifact_count: {report['artifact_count']}",
        f"tool_count: {report['tool_count']}",
        f"erg_004_status: {report['erg_004_status']}",
        f"finding_namespace: {report['finding_namespace']}",
        f"vm_first: {str(report['vm_first']).lower()}",
        f"container_profiles_deferred: {str(report['container_profiles_deferred']).lower()}",
        "implementation_planning_allowed: "
        f"{str(report['implementation_planning_allowed']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "runtime_implementation_allowed: "
        f"{str(report['runtime_implementation_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        "external_review_required_before_runtime: "
        f"{str(report['external_review_required_before_runtime']).lower()}",
        f"closes_erg_004: {str(report['closes_erg_004']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _index(commit: str, dirty: bool) -> str:
    return f"""# Sandbox/VM Live POC Implementation Review Bundle

Reviewed commit: `{commit}`

Dirty at generation: `{str(dirty).lower()}`

Tool count remains `24`.

Current `ERG-004` status: `ready_for_implementation_planning_only`.

This bundle packages the VM-first and operator-managed `ERG-004` implementation-planning lane for
external review. It asks whether the planning artifacts are complete enough to prepare a separate
future runtime implementation proposal.

## Artifacts

{_artifact_list()}

## What This Bundle Does Not Prove

This bundle does not prove external review happened, does not close `ERG-004`, and does not approve
runtime implementation, live VM/container inspection, VM/container lifecycle management, sandbox
orchestration, Mission Control runtime behavior, local model invocation, trusted-host promotion,
network expansion, API/MCP profile loading, SIEM adapter behavior, production identity, runtime
Postgres, hosted telemetry, remote MCP, compliance automation, shell/Docker/Kubernetes/browser
governed powers, arbitrary HTTP, broad filesystem writes, plugin SDK behavior, new governed tool
powers, or public/security-product positioning.
"""


def _prompt(commit: str) -> str:
    return f"""# Sandbox/VM Live POC Implementation Review Prompt

You are reviewing Ithildin as an external/source reviewer for the `ERG-004` live sandbox/VM worker
proof-of-concept implementation-planning lane only.

Reviewed commit: `{commit}`

Finding namespace: `EXT-LIVE-IMPL-###`

## Scope

Please inspect the attached decision record, implementation plan, active-route clarity note,
evidence contracts, precondition maps, static fixture plan, negative transcript plan, and command
evidence.

Please answer:

1. Are the planning artifacts complete enough to prepare a separate future runtime implementation
   proposal for an operator-managed VM proof of concept?
2. Are the VM-first, operator-managed boundaries clear enough?
3. Are container profiles clearly deferred?
4. Are the evidence fields, cleanup/failure transcript plans, and negative cases sufficient for
   later source review?
5. What findings, if any, must be fixed before runtime implementation may even be proposed?

Do not approve runtime implementation. Do not approve live VM/container inspection. Do not approve
VM/container lifecycle management. Do not approve local model invocation. Do not approve sandbox
orchestration. Do not approve Mission Control runtime behavior. Do not approve trusted-host
promotion. Do not approve network expansion, API/MCP profile loading, SIEM adapter behavior, new
governed tool powers, shell, Docker, Kubernetes, browser automation, arbitrary HTTP, broad writes,
production identity, runtime Postgres, hosted telemetry, remote MCP, compliance automation, or
public/security-product positioning.

Use this table shape for findings:

| Finding ID | Severity | Area | Affected files/functions |
| --- | --- | --- | --- |
| EXT-LIVE-IMPL-### | critical/high/medium/low/informational | sandbox-vm-live-poc | path/function |

| Blocking status | Disposition | Recommended fix |
| --- | --- | --- |
| blocking/should-fix/later/advisory | open | fix summary |
"""


def _static_fixture_plan() -> str:
    return """# ERG-004 Static Fixture And Negative Plan

This is planning evidence only. It does not define API, MCP, manifest, executor, or runtime input
behavior.

## Static Fixture Shape To Review Later

Future fixture-only planning may use secret-free fields:

- `operator_intent_id`
- `workspace_id`
- `run_id`
- `principal_id`
- `sandbox_profile_id`
- `sandbox_id`
- `vm_profile_label`
- `vm_profile_hash`
- `mount_root_label`
- `network_posture_label`
- `cleanup_plan_hash`
- `failure_transcript_hash`
- `mission_control_display_packet_hash`
- `model_client_label`
- `model_request_hash`
- `promotion_status: not_promoted`

No prompt text, model response, file content, diff, raw host path, raw VM path, raw VM transcript,
secret, dependency name, package script value, sandbox filesystem listing, or broad resource
enumeration may appear in the fixture.

Container profiles remain deferred. A container profile may be considered later as lower-assurance
developer evidence, but `ERG-004` implementation planning is VM-first and operator-managed.

## Negative Plans Required Before Runtime Proposal

The future runtime proposal must include negative transcripts or fixtures for:

- missing or stale `vm_profile_hash`;
- unsafe `mount_root_label`;
- unexpected `network_posture_label`;
- attempted VM/container lifecycle management by Ithildin;
- attempted live VM/container inspection;
- attempted local model invocation;
- attempted Mission Control execution or approval authority;
- attempted trusted-host promotion;
- attempted host write;
- broad write or arbitrary network expansion;
- cleanup failure;
- missing or mismatched `failure_transcript_hash`;
- packet hash mismatch;
- raw secret, prompt, model response, file content, diff, transcript, or path leakage.
"""


def _docs_bundle(title: str, repo_root: Path, docs: list[str]) -> str:
    lines = [f"# {title}", ""]
    for rel in docs:
        path = repo_root / rel
        if not path.exists():
            raise SandboxVmLivePocImplementationReviewBundleError(f"missing bundled doc: {rel}")
        lines.extend([f"## {rel}", "", path.read_text(encoding="utf-8"), ""])
    return "\n".join(lines)


def _command_evidence(
    commit: str, dirty: bool, command_reports: list[dict[str, Any]]
) -> str:
    payload = {
        "schema_version": "1",
        "commit": commit,
        "dirty": dirty,
        "tool_count": 24,
        "erg_004_status": "ready_for_implementation_planning_only",
        "commands": command_reports,
        "runtime_changes_allowed": False,
        "runtime_implementation_allowed": False,
        "live_vm_inspection_allowed": False,
        "vm_container_lifecycle_allowed": False,
        "sandbox_orchestration_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "trusted_host_promotion_allowed": False,
        "api_mcp_profile_loading_allowed": False,
        "new_power_classes_allowed": False,
        "public_security_product_positioning_allowed": False,
        "external_review_required_before_runtime": True,
        "closes_erg_004": False,
    }
    return "# ERG-004 Command Evidence\n\n```json\n" + json.dumps(
        payload, indent=2, sort_keys=True
    ) + "\n```\n"


def _build_command_reports(repo_root: Path, *, run_commands: bool) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for name, command in COMMANDS:
        if not run_commands:
            reports.append({"name": name, "command": command, "skipped": True})
            continue
        completed = subprocess.run(
            command,
            cwd=repo_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=180,
        )
        reports.append(
            {
                "name": name,
                "command": command,
                "returncode": completed.returncode,
                "output_tail": completed.stdout[-4000:],
                "skipped": False,
            }
        )
        if completed.returncode != 0:
            raise SandboxVmLivePocImplementationReviewBundleError(
                f"command failed for bundle evidence: {name}"
            )
    return reports


def _artifact_list() -> str:
    lines = []
    for index, name in enumerate(ARTIFACTS, start=1):
        lines.append(f"{index}. `{name}`")
    lines.append(f"{len(ARTIFACTS) + 1}. `{HASH_MANIFEST}`")
    return "\n".join(lines)


def _write_hashes(output_dir: Path) -> None:
    artifacts = []
    for name in ARTIFACTS:
        path = output_dir / name
        data = path.read_bytes()
        artifacts.append(
            {
                "path": name,
                "bytes": len(data),
                "sha256": "sha256:" + hashlib.sha256(data).hexdigest(),
            }
        )
    _write(
        output_dir / HASH_MANIFEST,
        json.dumps({"schema_version": "1", "artifacts": artifacts}, indent=2) + "\n",
    )


def _require_project_root(repo_root: Path) -> None:
    missing = [marker.as_posix() for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        raise SandboxVmLivePocImplementationReviewBundleError(
            "not an Ithildin project root; missing " + ", ".join(missing)
        )


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


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
            print(render_report(report))
            return 0 if report["valid"] else 1
        output_dir = build_bundle(
            repo_root=Path.cwd().resolve(),
            output_dir=args.output_dir,
            allow_dirty=args.allow_dirty,
            run_commands=not args.skip_commands,
        )
    except SandboxVmLivePocImplementationReviewBundleError as exc:
        print(f"sandbox/VM live POC implementation-review bundle failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built sandbox/VM live POC implementation-review bundle at {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

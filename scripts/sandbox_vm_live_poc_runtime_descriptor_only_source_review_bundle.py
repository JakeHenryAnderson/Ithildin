"""Build the ERG-004 descriptor-only implementation source-review bundle."""

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

from scripts import sandbox_vm_live_poc_runtime_descriptor_only_negative_transcripts

DEFAULT_OUTPUT_DIR = Path(
    "var/review-packets/v3/sandbox-vm-live-poc-runtime-descriptor-only-source-review"
)
HASH_MANIFEST = "sandbox-vm-live-poc-runtime-descriptor-only-source-artifact-hashes.json"
DOC_REL = "docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-source-review-bundle.md"
DOC_TITLE = "Sandbox/VM Live POC Runtime Descriptor-Only Source Review Bundle"
TARGET = "sandbox-vm-live-poc-runtime-descriptor-only-source-review-bundle"
CHECK_TARGET = "sandbox-vm-live-poc-runtime-descriptor-only-source-review-bundle-check"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
ARTIFACTS = [
    "00_SANDBOX_VM_LIVE_POC_DESCRIPTOR_ONLY_SOURCE_REVIEW_INDEX.md",
    "01_SANDBOX_VM_LIVE_POC_DESCRIPTOR_ONLY_SOURCE_REVIEW_PROMPT.md",
    "02_ERG004_DESCRIPTOR_ONLY_RUNTIME_SOURCE.md",
    "03_ERG004_DESCRIPTOR_ONLY_TESTS_AND_GATES.md",
    "04_ERG004_DESCRIPTOR_ONLY_CONTRACT_AND_BOUNDARY.md",
    "05_ERG004_DESCRIPTOR_ONLY_COMMAND_EVIDENCE.md",
    "06_ERG004_DESCRIPTOR_ONLY_NEGATIVE_TRANSCRIPTS.md",
]
COMMANDS = [
    (
        "sandbox-vm-live-poc-runtime-descriptor-only-implementation-check",
        ["make", "sandbox-vm-live-poc-runtime-descriptor-only-implementation-check"],
    ),
    (
        "focused-api-descriptor-tests",
        [
            "uv",
            "run",
            "pytest",
            "tests/test_api_service.py::test_sandbox_descriptor_endpoints_require_auth_and_store_safe_evidence",
            "tests/test_api_service.py::test_sandbox_descriptor_denies_unsafe_inputs_safely",
            "-q",
        ],
    ),
    (
        "descriptor-only-negative-transcripts",
        ["make", "sandbox-vm-live-poc-runtime-descriptor-only-negative-transcripts"],
    ),
    (
        "no-new-powers-guardrail",
        ["make", "no-new-powers-guardrail"],
    ),
    (
        "tool-surface-invariant-gate",
        ["make", "tool-surface-invariant-gate"],
    ),
]
FORBIDDEN_APPROVAL_PHRASES = [
    "ERG-004 is closed",
    "runtime implementation is externally approved",
    "approved live VM/container inspection",
    "approved VM/container lifecycle management",
    "approved sandbox orchestration",
    "approved Mission Control runtime authority",
    "approved local model invocation",
    "approved trusted-host promotion",
    "approved host writes",
    "approved new governed tool powers",
    "approved public security product positioning",
]


class DescriptorOnlySourceReviewBundleError(RuntimeError):
    """Raised when the descriptor-only source-review bundle cannot be built."""


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
        raise DescriptorOnlySourceReviewBundleError(
            "working tree is dirty; commit before ERG-004 descriptor-only source handoff"
        )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    command_reports = _build_command_reports(repo_root, run_commands=run_commands)
    files = {
        "00_SANDBOX_VM_LIVE_POC_DESCRIPTOR_ONLY_SOURCE_REVIEW_INDEX.md": _index(
            commit, dirty
        ),
        "01_SANDBOX_VM_LIVE_POC_DESCRIPTOR_ONLY_SOURCE_REVIEW_PROMPT.md": _prompt(
            commit
        ),
        "02_ERG004_DESCRIPTOR_ONLY_RUNTIME_SOURCE.md": _docs_bundle(
            "ERG-004 Descriptor-Only Runtime Source",
            repo_root,
            [
                "apps/api/src/ithildin_api/sandbox_descriptors.py",
                "apps/api/src/ithildin_api/app.py",
                "packages/schemas/src/ithildin_schemas/types.py",
            ],
        ),
        "03_ERG004_DESCRIPTOR_ONLY_TESTS_AND_GATES.md": _docs_bundle(
            "ERG-004 Descriptor-Only Tests And Gates",
            repo_root,
            [
                "tests/test_api_service.py",
                "scripts/sandbox_vm_live_poc_runtime_descriptor_only_implementation_check.py",
            ],
        ),
        "04_ERG004_DESCRIPTOR_ONLY_CONTRACT_AND_BOUNDARY.md": _docs_bundle(
            "ERG-004 Descriptor-Only Contract And Boundary",
            repo_root,
            [
                "docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-implementation.md",
                "docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-implementation-decision.md",
                "docs/codex/sandbox-vm-live-poc-runtime-descriptor-contract.md",
                "docs/codex/sandbox-vm-live-poc-runtime-negative-fixtures.md",
            ],
        ),
        "05_ERG004_DESCRIPTOR_ONLY_COMMAND_EVIDENCE.md": _command_evidence(
            commit, dirty, command_reports
        ),
        "06_ERG004_DESCRIPTOR_ONLY_NEGATIVE_TRANSCRIPTS.md": _negative_transcripts_bundle(),
    }
    for name, content in files.items():
        _write(output_dir / name, content)
    _write_hashes(output_dir)
    return output_dir


def build_check_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    current_commit = _git(repo_root, ["rev-parse", "HEAD"])
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_docs = _read(repo_root / "scripts/review_docs.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition(
        "\n\n"
    )[0]

    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "descriptor-only-source-review"
        try:
            build_bundle(
                repo_root=repo_root,
                output_dir=output_dir,
                allow_dirty=True,
                run_commands=False,
            )
        except DescriptorOnlySourceReviewBundleError as exc:
            failures.append(str(exc))
            artifact_names: set[str] = set()
            hashes: dict[str, Any] = {"artifacts": []}
            contents: dict[str, str] = {}
        else:
            artifact_names = {path.name for path in output_dir.iterdir()}
            hashes = json.loads((output_dir / HASH_MANIFEST).read_text(encoding="utf-8"))
            contents = {
                name: (output_dir / name).read_text(encoding="utf-8")
                for name in ARTIFACTS
            }

    expected = set(ARTIFACTS) | {HASH_MANIFEST}
    missing = expected - artifact_names
    if missing:
        failures.append(
            "descriptor-only source review bundle missing artifacts: "
            + ", ".join(sorted(missing))
        )
    hashed = {entry.get("path") for entry in hashes.get("artifacts", [])}
    if set(ARTIFACTS) - hashed:
        failures.append("artifact hashes do not cover generated markdown files")
    if HASH_MANIFEST in hashed:
        failures.append("hash manifest must not hash itself")

    index = contents.get(
        "00_SANDBOX_VM_LIVE_POC_DESCRIPTOR_ONLY_SOURCE_REVIEW_INDEX.md", ""
    )
    prompt = contents.get(
        "01_SANDBOX_VM_LIVE_POC_DESCRIPTOR_ONLY_SOURCE_REVIEW_PROMPT.md", ""
    )
    source = contents.get("02_ERG004_DESCRIPTOR_ONLY_RUNTIME_SOURCE.md", "")
    tests = contents.get("03_ERG004_DESCRIPTOR_ONLY_TESTS_AND_GATES.md", "")
    boundary = contents.get("04_ERG004_DESCRIPTOR_ONLY_CONTRACT_AND_BOUNDARY.md", "")
    evidence = contents.get("05_ERG004_DESCRIPTOR_ONLY_COMMAND_EVIDENCE.md", "")
    negative = contents.get("06_ERG004_DESCRIPTOR_ONLY_NEGATIVE_TRANSCRIPTS.md", "")

    for name, content in [
        ("index", index),
        ("prompt", prompt),
        ("command evidence", evidence),
    ]:
        if current_commit not in content:
            failures.append(f"descriptor-only source {name} does not reference current commit")

    for phrase in [
        "Tool count remains `24`",
        "Current `ERG-004` status: `descriptor_only_runtime_implemented_source_review_pending`",
        "What This Bundle Does Not Prove",
    ]:
        if phrase not in index:
            failures.append(f"descriptor-only source index is missing phrase: {phrase}")
    for phrase in [
        "Finding namespace: `EXT-LIVE-DESC-###`",
        "source-level review",
        "Do not close ERG-004 unless",
        "Do not approve live VM/container inspection",
    ]:
        if phrase not in prompt:
            failures.append(f"descriptor-only source prompt is missing phrase: {phrase}")
    for phrase in [
        "SandboxDescriptorPayload",
        "SandboxDescriptorStore",
        "sandbox.descriptor.submitted",
        "@api.post(\"/sandbox-descriptors\"",
        "@api.get(\"/sandbox-descriptors\"",
    ]:
        if phrase not in source:
            failures.append(f"descriptor-only source bundle is missing phrase: {phrase}")
    for phrase in [
        "test_sandbox_descriptor_endpoints_require_auth_and_store_safe_evidence",
        "test_sandbox_descriptor_denies_unsafe_inputs_safely",
        "runtime_descriptor_only_implemented",
    ]:
        if phrase not in tests:
            failures.append(f"descriptor-only tests bundle is missing phrase: {phrase}")
    for phrase in [
        "descriptor_source: operator_supplied",
        "operator-attested descriptor",
        "live VM/container inspection",
        "raw secrets, tokens, credentials",
    ]:
        if phrase not in boundary:
            failures.append(f"descriptor-only boundary bundle is missing phrase: {phrase}")
    for phrase in [
        '"sandbox-vm-live-poc-runtime-descriptor-only-implementation-check"',
        '"focused-api-descriptor-tests"',
        '"descriptor-only-negative-transcripts"',
        '"no-new-powers-guardrail"',
        '"tool-surface-invariant-gate"',
        '"live_vm_inspection_allowed": false',
        '"new_power_classes_allowed": false',
    ]:
        if phrase not in evidence:
            failures.append(f"descriptor-only source command evidence is missing phrase: {phrase}")
    for phrase in [
        "Sandbox/VM Live POC Descriptor-Only Negative Transcripts",
        "Unknown Field",
        "Lifecycle Control Claim",
        "Live Inspection Claim",
        "Raw Mount Path",
        "malformed_profile_hash",
        "does not close `ERG-004`",
    ]:
        if phrase not in negative:
            failures.append(
                "descriptor-only negative transcript bundle is missing phrase: "
                f"{phrase}"
            )

    combined = "\n".join(contents.values())
    for phrase in FORBIDDEN_APPROVAL_PHRASES:
        if phrase in combined:
            failures.append(f"descriptor-only source bundle contains forbidden phrase: {phrase}")

    if DOC_REL not in docs_site:
        failures.append("descriptor-only source review doc is missing from docs site")
    if DOC_REL not in review_docs:
        failures.append("descriptor-only source review doc is missing from review docs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing descriptor-only source review bundle")
    if f"{TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {TARGET}")
    if f"{CHECK_TARGET}:" not in makefile:
        failures.append(f"Make target is missing: {CHECK_TARGET}")
    if CHECK_TARGET not in release_check_body and f"release-check: {CHECK_TARGET}" not in makefile:
        failures.append("descriptor-only source review check missing from release-check")
    if f"$(MAKE) {TARGET}" not in review_candidate_body:
        failures.append("review-candidate does not generate descriptor-only source bundle")
    if CHECK_TARGET not in release_guardrails:
        failures.append("release guardrails do not require descriptor-only source check")
    if f"$(MAKE) {TARGET}" not in release_guardrails:
        failures.append("release guardrails do not require descriptor-only source generation")
    if f"make {TARGET}" not in readme:
        failures.append("README is missing descriptor-only source bundle command")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "output_dir": str(DEFAULT_OUTPUT_DIR),
        "artifact_count": len(expected),
        "current_commit": current_commit,
        "tool_count": 24,
        "erg_004_status": "descriptor_only_runtime_implemented_source_review_pending",
        "finding_namespace": "EXT-LIVE-DESC-###",
        "descriptor_only_source_review_ready": True,
        "runtime_changes_allowed": False,
        "live_vm_inspection_allowed": False,
        "sandbox_orchestration_allowed": False,
        "local_model_invocation_allowed": False,
        "new_power_classes_allowed": False,
        "closes_erg_004": False,
    }


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM live POC descriptor-only source review bundle check",
        f"valid: {str(report['valid']).lower()}",
        f"output_dir: {report['output_dir']}",
        f"artifact_count: {report['artifact_count']}",
        f"tool_count: {report['tool_count']}",
        f"erg_004_status: {report['erg_004_status']}",
        f"finding_namespace: {report['finding_namespace']}",
        "descriptor_only_source_review_ready: "
        f"{str(report['descriptor_only_source_review_ready']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "live_vm_inspection_allowed: "
        f"{str(report['live_vm_inspection_allowed']).lower()}",
        "sandbox_orchestration_allowed: "
        f"{str(report['sandbox_orchestration_allowed']).lower()}",
        "local_model_invocation_allowed: "
        f"{str(report['local_model_invocation_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"closes_erg_004: {str(report['closes_erg_004']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _index(commit: str, dirty: bool) -> str:
    return f"""# Sandbox/VM Live POC Descriptor-Only Source Review Index

Reviewed commit: `{commit}`

Dirty tree: `{str(dirty).lower()}`

Tool count remains `24`.

Current `ERG-004` status: `descriptor_only_runtime_implemented_source_review_pending`.

This packet packages the implemented descriptor-only runtime slice for source-level review:
operator-supplied descriptor validation, local descriptor records, admin-only read/write descriptor
APIs, system status evidence, and safe audit metadata.

## Artifacts

- `01_SANDBOX_VM_LIVE_POC_DESCRIPTOR_ONLY_SOURCE_REVIEW_PROMPT.md`
- `02_ERG004_DESCRIPTOR_ONLY_RUNTIME_SOURCE.md`
- `03_ERG004_DESCRIPTOR_ONLY_TESTS_AND_GATES.md`
- `04_ERG004_DESCRIPTOR_ONLY_CONTRACT_AND_BOUNDARY.md`
- `05_ERG004_DESCRIPTOR_ONLY_COMMAND_EVIDENCE.md`
- `06_ERG004_DESCRIPTOR_ONLY_NEGATIVE_TRANSCRIPTS.md`
- `{HASH_MANIFEST}`

## What This Bundle Does Not Prove

This bundle does not close ERG-004, does not prove external source-review disposition, does not
inspect or control a VM/container, does not invoke a local model, does not grant Mission Control
runtime authority, does not write or promote host artifacts, does not add MCP tools, and does not
approve new governed tool powers.
"""


def _prompt(commit: str) -> str:
    return f"""# ERG-004 Descriptor-Only Source Review Prompt

You are reviewing Ithildin's `ERG-004` descriptor-only runtime implementation. Treat this as
source-level review only if you inspect the attached source, tests, contract docs, and command
evidence.

Reviewed commit: `{commit}`

Area: `sandbox-vm-live-poc-runtime-descriptor-only-source`

Finding namespace: `EXT-LIVE-DESC-###`

## Review Focus

- `SandboxDescriptorPayload` closed schema validation and safe operator-attested field boundaries.
- `SandboxDescriptorStore` SQLite persistence, identifier handling, list/detail summaries, and safe
  metadata.
- Admin-only `POST /sandbox-descriptors`, `GET /sandbox-descriptors`, and
  `GET /sandbox-descriptors/{{descriptor_id}}` behavior.
- `/system/status` descriptor evidence and `sandbox.descriptor.submitted` audit metadata.
- Safe error behavior for invalid descriptors without echoing unsafe input.
- Negative boundaries: no live VM/container inspection, lifecycle control, sandbox orchestration,
  local model invocation, Mission Control runtime authority, trusted-host promotion, host writes,
  API/MCP profile loading, network expansion, or new governed tool powers.

## Required Disposition

Answer whether the descriptor-only runtime implementation is source-review ready for continued
local-preview development. Do not close ERG-004 unless you explicitly reviewed the source and find
no blocking implementation issue for this descriptor-only slice.

Use finding IDs in the `EXT-LIVE-DESC-###` namespace.

Do not approve live VM/container inspection. Do not approve VM/container lifecycle management.
Do not approve local model invocation. Do not approve Mission Control runtime authority.
Do not approve host writes, trusted-host promotion, profile loading, or new governed tool powers.
"""


def _docs_bundle(title: str, repo_root: Path, rel_paths: list[str]) -> str:
    parts = [f"# {title}\n"]
    for rel_path in rel_paths:
        path = repo_root / rel_path
        parts.append(f"\n## `{rel_path}`\n\n")
        parts.append(path.read_text(encoding="utf-8"))
        parts.append("\n")
    return "\n".join(parts)


def _command_evidence(
    commit: str, dirty: bool, command_reports: list[dict[str, Any]]
) -> str:
    payload = {
        "commit": commit,
        "dirty": dirty,
        "commands": command_reports,
        "runtime_changes_allowed": False,
        "live_vm_inspection_allowed": False,
        "vm_container_lifecycle_allowed": False,
        "sandbox_orchestration_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "trusted_host_promotion_allowed": False,
        "host_writes_allowed": False,
        "network_expansion_allowed": False,
        "api_mcp_profile_loading_allowed": False,
        "new_power_classes_allowed": False,
        "closes_erg_004": False,
    }
    return "# ERG-004 Descriptor-Only Source Review Command Evidence\n\n```json\n" + json.dumps(
        payload, indent=2, sort_keys=True
    ) + "\n```\n"


def _negative_transcripts_bundle() -> str:
    with tempfile.TemporaryDirectory() as tmp:
        transcript = (
            sandbox_vm_live_poc_runtime_descriptor_only_negative_transcripts.build_transcripts(
                Path(tmp)
            )
        )
        return transcript.read_text(encoding="utf-8")


def _build_command_reports(repo_root: Path, *, run_commands: bool) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for name, cmd in COMMANDS:
        if not run_commands:
            reports.append({"name": name, "command": cmd, "status": "not_run"})
            continue
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        reports.append(
            {
                "name": name,
                "command": cmd,
                "exit_code": result.returncode,
                "status": "passed" if result.returncode == 0 else "failed",
                "output_tail": "\n".join(result.stdout.splitlines()[-80:]),
            }
        )
        if result.returncode != 0:
            raise DescriptorOnlySourceReviewBundleError(
                f"command failed for descriptor-only source review bundle: {name}"
            )
    return reports


def _write_hashes(output_dir: Path) -> None:
    artifacts = []
    for path in sorted(output_dir.iterdir()):
        if path.name == HASH_MANIFEST:
            continue
        data = path.read_bytes()
        artifacts.append(
            {
                "path": path.name,
                "sha256": "sha256:" + hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            }
        )
    _write(output_dir / HASH_MANIFEST, json.dumps({"artifacts": artifacts}, indent=2) + "\n")


def _write(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


def _require_project_root(repo_root: Path) -> None:
    missing = [str(marker) for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        raise DescriptorOnlySourceReviewBundleError(
            "not an Ithildin repo root; missing project markers: " + ", ".join(missing)
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--skip-commands", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    if args.check:
        report = build_check_report(Path.cwd())
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print(render_check_report(report))
        return 0 if report["valid"] else 1

    try:
        output_dir = build_bundle(
            repo_root=Path.cwd(),
            output_dir=args.output_dir,
            allow_dirty=args.allow_dirty,
            run_commands=not args.skip_commands,
        )
    except DescriptorOnlySourceReviewBundleError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Built ERG-004 descriptor-only source review bundle at {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

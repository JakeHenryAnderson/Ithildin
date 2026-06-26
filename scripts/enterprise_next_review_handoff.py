"""Build the next enterprise-review handoff pointer."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-next-review-handoff.md"
DOC_NAME = "enterprise-next-review-handoff.md"
DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/enterprise-next-review-handoff")
MARKDOWN_NAME = "NEXT_ENTERPRISE_REVIEW_HANDOFF.md"
JSON_NAME = "next-enterprise-review-handoff.json"
HASH_NAME = "next-enterprise-review-handoff-artifact-hashes.json"
RECOMMENDED_GAP = "ERG-003"
RECOMMENDED_PACKET_DIR = Path("var/review-packets/v3/sandbox-vm-static-preflight-external-review")
REQUIRED_PACKET_FILES = [
    "00_SANDBOX_VM_STATIC_PREFLIGHT_EXTERNAL_REVIEW_INDEX.md",
    "01_SANDBOX_VM_STATIC_PREFLIGHT_EXTERNAL_REVIEW_PROMPT.md",
    "02_SANDBOX_VM_STATIC_PREFLIGHT_SOURCE_PACKET.md",
    "03_SANDBOX_VM_STATIC_PREFLIGHT_DISPOSITION_PACKET.md",
    "04_SANDBOX_VM_STATIC_PREFLIGHT_IMPLEMENTATION_CONTRACTS.md",
    "05_SANDBOX_VM_STATIC_PREFLIGHT_FIXTURES_NEGATIVES.md",
    "06_SANDBOX_VM_STATIC_PREFLIGHT_RESPONSE_CLOSURE_TRIAGE.md",
    "07_SANDBOX_VM_STATIC_PREFLIGHT_REPRODUCTION_QUEUE_STATUS.md",
    "08_SANDBOX_VM_STATIC_PREFLIGHT_COMMAND_EVIDENCE.md",
    "sandbox-vm-static-preflight-external-review-artifact-hashes.json",
]
BLOCKED_BOUNDARIES = [
    "runtime_changes_allowed",
    "live_vm_inspection_allowed",
    "mission_control_runtime_allowed",
    "local_model_invocation_allowed",
    "sandbox_orchestration_allowed",
    "trusted_host_promotion_allowed",
    "new_power_classes_allowed",
    "closes_erg_003",
]


class EnterpriseNextReviewHandoffError(RuntimeError):
    """Raised when the handoff cannot be built or validated."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.check:
        report = build_check_report(ROOT)
        print(render_check_report(report))
        return 0 if report["valid"] else 1

    try:
        output_dir = build_handoff(ROOT, args.output_dir)
    except EnterpriseNextReviewHandoffError as exc:
        print(f"enterprise next-review handoff failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built enterprise next-review handoff at {output_dir}")
    return 0


def build_handoff(repo_root: Path, output_dir: Path) -> Path:
    _validate_repo_root(repo_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    packet_dir = repo_root / RECOMMENDED_PACKET_DIR
    missing_packet_files = [
        name for name in REQUIRED_PACKET_FILES if not (packet_dir / name).exists()
    ]
    if missing_packet_files:
        raise EnterpriseNextReviewHandoffError(
            "ERG-003 packet is missing files: " + ", ".join(missing_packet_files)
        )
    packet_hash_manifest = _packet_hash_manifest(packet_dir)

    commit = _git(repo_root, ["rev-parse", "HEAD"])
    dirty = bool(_git(repo_root, ["status", "--short"]))
    payload = _handoff_payload(
        commit=commit,
        dirty=dirty,
        packet_hash_manifest=packet_hash_manifest,
    )
    markdown = _render_markdown(payload)

    markdown_path = output_dir / MARKDOWN_NAME
    json_path = output_dir / JSON_NAME
    hash_path = output_dir / HASH_NAME
    markdown_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    hashes = _artifact_hashes(output_dir, [MARKDOWN_NAME, JSON_NAME])
    hash_path.write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_dir


def build_check_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    try:
        output_dir = build_handoff(repo_root, DEFAULT_OUTPUT_DIR)
    except EnterpriseNextReviewHandoffError as exc:
        failures.append(str(exc))
        output_dir = DEFAULT_OUTPUT_DIR

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    queue = _read(repo_root / "docs/codex/enterprise-external-review-queue.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    handoff_doc = repo_root / DOC_REL
    if not handoff_doc.exists():
        failures.append("enterprise next-review handoff doc is missing")
        handoff_text = ""
    else:
        handoff_text = handoff_doc.read_text(encoding="utf-8")
    markdown_text = _read(output_dir / MARKDOWN_NAME)
    json_text = _read(output_dir / JSON_NAME)
    hash_text = _read(output_dir / HASH_NAME)
    try:
        hashes = json.loads(hash_text) if hash_text else {"artifacts": []}
    except json.JSONDecodeError:
        hashes = {"artifacts": []}
        failures.append("handoff hash manifest is not valid JSON")
    handoff_hashes_match_files = _artifact_hashes_match_files(
        output_dir=output_dir,
        hashes=hashes,
    )

    for phrase in [
        "Recommended next enterprise review: `ERG-003`",
        "sandbox-vm-static-preflight-external-review",
        "does not close `ERG-003`",
        "does not approve live VM/container inspection",
        "does not approve local model invocation",
        "make sandbox-vm-static-preflight-external-review-bundle",
        "make sandbox-vm-static-preflight-response-kit",
        "make sandbox-vm-static-preflight-response-application-record-check",
        "docs/codex/sandbox-vm-static-preflight-response-application-record.md",
        "artifact hash manifest",
    ]:
        if phrase not in handoff_text:
            failures.append(f"handoff doc is missing phrase: {phrase}")
    for phrase in [
        "Recommended next enterprise review: `ERG-003`",
        "Attach these files",
        "Response path after review",
        "What remains blocked",
        "EXT-SVP-###",
        "Response-application record",
        "Response-application check",
        "Attachment integrity check",
        "expected hashed files: `9`",
        "hash manifest matches files: `true`",
    ]:
        if phrase not in markdown_text:
            failures.append(f"generated handoff is missing phrase: {phrase}")
    for phrase in [
        '"recommended_gap": "ERG-003"',
        '"runtime_changes_allowed": false',
        '"live_vm_inspection_allowed": false',
        '"closes_erg_003": false',
        '"response_application_record"',
        '"packet_hash_manifest"',
        '"expected_hashed_file_count": 9',
        '"hash_manifest_matches_files": true',
    ]:
        if phrase not in json_text:
            failures.append(f"generated handoff JSON is missing phrase: {phrase}")
    for name in [MARKDOWN_NAME, JSON_NAME]:
        if name not in hash_text:
            failures.append(f"handoff hash manifest is missing artifact: {name}")
    if HASH_NAME in hash_text:
        failures.append("handoff hash manifest must not hash itself")
    if not handoff_hashes_match_files:
        failures.append("handoff artifact hashes do not match generated files")

    required_wiring = {
        "Make target": "enterprise-next-review-handoff:",
        "Check target": "enterprise-next-review-handoff-check:",
        "Release check": "enterprise-next-review-handoff-check",
        "Review candidate": "$(MAKE) enterprise-next-review-handoff",
        "README command": "make enterprise-next-review-handoff",
        "Queue pointer": "enterprise-next-review-handoff.md",
        "Docs site": DOC_REL,
        "Review docs": DOC_REL,
        "Review index": DOC_NAME,
        "Release guardrails": "enterprise-next-review-handoff-check",
    }
    if required_wiring["Make target"] not in makefile:
        failures.append("Make target is missing: enterprise-next-review-handoff")
    if required_wiring["Check target"] not in makefile:
        failures.append("Make target is missing: enterprise-next-review-handoff-check")
    if required_wiring["Release check"] not in release_check_body:
        failures.append("enterprise-next-review-handoff-check is missing from release-check")
    if required_wiring["Review candidate"] not in review_candidate_body:
        failures.append("enterprise-next-review-handoff is missing from review-candidate")
    if required_wiring["README command"] not in readme:
        failures.append("README is missing enterprise next-review handoff command")
    if required_wiring["Queue pointer"] not in queue:
        failures.append("enterprise queue is missing next-review handoff pointer")
    if required_wiring["Docs site"] not in docs_site:
        failures.append("enterprise next-review handoff is missing from docs site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("enterprise next-review handoff is missing from review docs")
    if required_wiring["Review index"] not in review_index:
        failures.append("review-docs index is missing enterprise next-review handoff")
    if required_wiring["Release guardrails"] not in release_guardrails:
        failures.append("release guardrails do not require enterprise next-review handoff")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "handoff_doc": DOC_REL,
        "output_dir": output_dir.as_posix(),
        "recommended_gap": RECOMMENDED_GAP,
        "tool_count": 24,
        "handoff_hashes_match_files": handoff_hashes_match_files,
        "runtime_changes_allowed": False,
        "live_vm_inspection_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "new_power_classes_allowed": False,
        "closes_erg_003": False,
    }


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise next-review handoff check",
        f"valid: {str(report['valid']).lower()}",
        f"handoff_doc: {report['handoff_doc']}",
        f"output_dir: {report['output_dir']}",
        f"recommended_gap: {report['recommended_gap']}",
        f"tool_count: {report['tool_count']}",
        f"handoff_hashes_match_files: {str(report['handoff_hashes_match_files']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"closes_erg_003: {str(report['closes_erg_003']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _validate_repo_root(repo_root: Path) -> None:
    missing = [
        marker
        for marker in ["pyproject.toml", "Makefile", "tool-manifests.lock.json"]
        if not (repo_root / marker).exists()
    ]
    if missing:
        raise EnterpriseNextReviewHandoffError(
            "must be run from the Ithildin repo root; missing " + ", ".join(missing)
        )


def _handoff_payload(
    *,
    commit: str,
    dirty: bool,
    packet_hash_manifest: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "handoff_type": "ithildin.enterprise_next_review",
        "recommended_gap": RECOMMENDED_GAP,
        "recommended_review": "sandbox-vm-static-preflight",
        "commit": commit,
        "dirty": dirty,
        "tool_count": 24,
        "selected_capability": "not selected",
        "attach_directory": RECOMMENDED_PACKET_DIR.as_posix(),
        "attach_files": REQUIRED_PACKET_FILES,
        "packet_hash_manifest": packet_hash_manifest,
        "finding_namespace": "EXT-SVP-###",
        "response_path": {
            "response_kit": "var/review-packets/v3/sandbox-vm-static-preflight-response-kit",
            "intake_doc": "docs/codex/sandbox-vm-static-preflight-external-response-intake.md",
            "closure_gate": "make sandbox-vm-static-preflight-disposition-closure-check",
            "dry_run": "make sandbox-vm-static-preflight-response-dry-run",
            "triage_update": "docs/codex/sandbox-vm-static-preflight-triage-update.md",
            "response_application_record": (
                "docs/codex/sandbox-vm-static-preflight-response-application-record.md"
            ),
            "response_application_check": (
                "make sandbox-vm-static-preflight-response-application-record-check"
            ),
        },
        "blocked_boundaries": {name: False for name in BLOCKED_BOUNDARIES},
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    attach_files = "\n".join(f"- `{name}`" for name in payload["attach_files"])
    blocked = "\n".join(f"- `{name}`: `false`" for name in BLOCKED_BOUNDARIES)
    packet_hash_manifest = payload["packet_hash_manifest"]
    return f"""# Enterprise Next Review Handoff

Recommended next enterprise review: `{payload['recommended_gap']}` static sandbox/VM preflight
disposition.

Reviewed commit for the handoff: `{payload['commit']}`

Dirty state when generated: `{str(payload['dirty']).lower()}`

Tool count remains `{payload['tool_count']}`.

Current selected capability: `{payload['selected_capability']}`.

## Attach These Files

Send the files from:

```text
{payload['attach_directory']}
```

Attach these files:

{attach_files}

## Attachment integrity check

Use `{packet_hash_manifest['path']}` to verify the nine review markdown files before review.

- expected hashed files: `{packet_hash_manifest['expected_hashed_file_count']}`
- hash manifest self-hashed: `{str(packet_hash_manifest['hash_manifest_self_hashed']).lower()}`
- hash manifest matches files: `{str(packet_hash_manifest['hash_manifest_matches_files']).lower()}`

## Reviewer Prompt

Use `01_SANDBOX_VM_STATIC_PREFLIGHT_EXTERNAL_REVIEW_PROMPT.md`.

Finding namespace: `{payload['finding_namespace']}`.

The reviewer should answer only whether `ERG-003` can move from
`external_review_required` to `closed_local_preview_static_preflight` for the CLI-only static
preflight fixture lane.

## Response path after review

- Response kit: `{payload['response_path']['response_kit']}`
- Intake doc: `{payload['response_path']['intake_doc']}`
- Closure gate: `{payload['response_path']['closure_gate']}`
- Dry run: `{payload['response_path']['dry_run']}`
- Triage update guide: `{payload['response_path']['triage_update']}`
- Response-application record: `{payload['response_path']['response_application_record']}`
- Response-application check: `{payload['response_path']['response_application_check']}`

## What remains blocked

This handoff does not close `ERG-003`, does not record external review, does not approve live
VM/container inspection, and does not approve local model invocation.

{blocked}

## Regeneration Commands

```sh
make sandbox-vm-static-preflight-external-review-bundle
make sandbox-vm-static-preflight-response-kit
make sandbox-vm-static-preflight-response-application-record-check
make enterprise-next-review-handoff
make enterprise-next-review-handoff-check
```
"""


def _packet_hash_manifest(packet_dir: Path) -> dict[str, Any]:
    hash_path = packet_dir / "sandbox-vm-static-preflight-external-review-artifact-hashes.json"
    if not hash_path.exists():
        raise EnterpriseNextReviewHandoffError("ERG-003 packet hash manifest is missing")
    try:
        manifest = json.loads(hash_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EnterpriseNextReviewHandoffError(
            "ERG-003 packet hash manifest is not valid JSON"
        ) from exc
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise EnterpriseNextReviewHandoffError(
            "ERG-003 packet hash manifest must contain an artifacts list"
        )
    hashed_paths: set[str] = set()
    for entry in artifacts:
        if not isinstance(entry, dict):
            raise EnterpriseNextReviewHandoffError(
                "ERG-003 packet hash manifest contains a non-object artifact"
            )
        path = entry.get("path")
        if not isinstance(path, str):
            raise EnterpriseNextReviewHandoffError(
                "ERG-003 packet hash manifest artifact is missing a path"
            )
        hashed_paths.add(path)
    expected_hashed = set(REQUIRED_PACKET_FILES) - {
        "sandbox-vm-static-preflight-external-review-artifact-hashes.json"
    }
    if hashed_paths != expected_hashed:
        missing = sorted(expected_hashed - hashed_paths)
        extra = sorted(hashed_paths - expected_hashed)
        detail = []
        if missing:
            detail.append("missing: " + ", ".join(missing))
        if extra:
            detail.append("extra: " + ", ".join(str(item) for item in extra))
        raise EnterpriseNextReviewHandoffError(
            "ERG-003 packet hash manifest mismatch; " + "; ".join(detail)
        )
    if "sandbox-vm-static-preflight-external-review-artifact-hashes.json" in hashed_paths:
        raise EnterpriseNextReviewHandoffError(
            "ERG-003 packet hash manifest must not hash itself"
        )
    for entry in artifacts:
        path = entry.get("path")
        sha256 = entry.get("sha256")
        byte_count = entry.get("bytes")
        if not isinstance(sha256, str) or not sha256.startswith("sha256:"):
            raise EnterpriseNextReviewHandoffError(
                f"ERG-003 packet hash manifest artifact has invalid sha256: {path}"
            )
        if not isinstance(byte_count, int) or byte_count <= 0:
            raise EnterpriseNextReviewHandoffError(
                f"ERG-003 packet hash manifest artifact has invalid byte count: {path}"
            )
        artifact_path = packet_dir / path
        if not artifact_path.exists():
            raise EnterpriseNextReviewHandoffError(
                f"ERG-003 packet hash manifest artifact file is missing: {path}"
            )
        artifact_bytes = artifact_path.read_bytes()
        actual_sha256 = "sha256:" + hashlib.sha256(artifact_bytes).hexdigest()
        if sha256 != actual_sha256:
            raise EnterpriseNextReviewHandoffError(
                f"ERG-003 packet hash manifest artifact digest mismatch: {path}"
            )
        if byte_count != len(artifact_bytes):
            raise EnterpriseNextReviewHandoffError(
                f"ERG-003 packet hash manifest artifact byte count mismatch: {path}"
            )
    return {
        "path": (RECOMMENDED_PACKET_DIR / hash_path.name).as_posix(),
        "expected_hashed_file_count": len(expected_hashed),
        "hash_manifest_self_hashed": (
            "sandbox-vm-static-preflight-external-review-artifact-hashes.json"
            in hashed_paths
        ),
        "hash_manifest_matches_files": True,
        "hashed_files": sorted(hashed_paths),
    }


def _artifact_hashes(output_dir: Path, names: list[str]) -> dict[str, Any]:
    artifacts = []
    for name in names:
        path = output_dir / name
        data = path.read_bytes()
        artifacts.append(
            {
                "path": name,
                "sha256": "sha256:" + hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            }
        )
    return {"schema_version": "1", "artifacts": artifacts}


def _artifact_hashes_match_files(*, output_dir: Path, hashes: dict[str, Any]) -> bool:
    artifacts = hashes.get("artifacts")
    if not isinstance(artifacts, list):
        return False
    expected = {MARKDOWN_NAME, JSON_NAME}
    seen: set[str] = set()
    for entry in artifacts:
        if not isinstance(entry, dict):
            return False
        path = entry.get("path")
        sha256 = entry.get("sha256")
        byte_count = entry.get("bytes")
        if not isinstance(path, str):
            return False
        if path == HASH_NAME:
            return False
        if not isinstance(sha256, str) or not sha256.startswith("sha256:"):
            return False
        if not isinstance(byte_count, int) or byte_count <= 0:
            return False
        artifact_path = output_dir / path
        if not artifact_path.exists() or not artifact_path.is_file():
            return False
        data = artifact_path.read_bytes()
        if sha256 != "sha256:" + hashlib.sha256(data).hexdigest():
            return False
        if byte_count != len(data):
            return False
        seen.add(path)
    return seen == expected


def _git(repo_root: Path, args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())

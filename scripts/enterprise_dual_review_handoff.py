"""Build the dual enterprise-review handoff pointer for the current send-ready lanes."""

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

from scripts import enterprise_review_send_readiness, review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-dual-review-handoff.md"
DOC_NAME = "enterprise-dual-review-handoff.md"
DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/enterprise-dual-review-handoff")
MARKDOWN_NAME = "ENTERPRISE_DUAL_REVIEW_HANDOFF.md"
JSON_NAME = "enterprise-dual-review-handoff.json"
HASH_NAME = "enterprise-dual-review-handoff-artifact-hashes.json"

RECOMMENDED_REVIEWS = [
    {
        "gap": "ERG-003",
        "name": "static sandbox/VM preflight",
        "packet_dir": Path("var/review-packets/v3/sandbox-vm-static-preflight-external-review"),
        "hash_manifest": "sandbox-vm-static-preflight-external-review-artifact-hashes.json",
        "prompt": "01_SANDBOX_VM_STATIC_PREFLIGHT_EXTERNAL_REVIEW_PROMPT.md",
        "finding_namespace": "EXT-SVP-###",
        "response_kit": "var/review-packets/v3/sandbox-vm-static-preflight-response-kit",
        "dry_run": "make sandbox-vm-static-preflight-response-dry-run",
        "closure_gate": "make sandbox-vm-static-preflight-disposition-closure-check",
        "intake_doc": "docs/codex/sandbox-vm-static-preflight-external-response-intake.md",
    },
    {
        "gap": "ERG-002",
        "name": "Mission Control display/import planning",
        "packet_dir": Path("var/review-packets/v3/mission-control-display-external-review"),
        "hash_manifest": "mission-control-display-external-review-artifact-hashes.json",
        "prompt": "01_MISSION_CONTROL_DISPLAY_EXTERNAL_REVIEW_PROMPT.md",
        "finding_namespace": "EXT-MC-DISPLAY-###",
        "response_kit": "var/review-packets/v3/mission-control-display-response-kit",
        "dry_run": "make mission-control-display-response-dry-run",
        "closure_gate": "make mission-control-display-disposition-closure-check",
        "intake_doc": "docs/codex/mission-control-display-external-response-intake.md",
    },
]

BLOCKED_BOUNDARIES = [
    "runtime_changes_allowed",
    "mission_control_runtime_allowed",
    "live_vm_inspection_allowed",
    "local_model_invocation_allowed",
    "sandbox_orchestration_allowed",
    "trusted_host_promotion_allowed",
    "siem_adapter_allowed",
    "compliance_automation_allowed",
    "public_security_product_positioning_allowed",
    "new_power_classes_allowed",
    "closes_erg_003",
    "closes_erg_002",
]


class EnterpriseDualReviewHandoffError(RuntimeError):
    """Raised when the dual handoff cannot be built or validated."""


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
    except EnterpriseDualReviewHandoffError as exc:
        print(f"enterprise dual-review handoff failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built enterprise dual-review handoff at {output_dir}")
    return 0


def build_handoff(repo_root: Path, output_dir: Path) -> Path:
    _validate_repo_root(repo_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    send_readiness = enterprise_review_send_readiness.build_report(repo_root)
    if send_readiness.get("valid") is not True:
        raise EnterpriseDualReviewHandoffError("enterprise send-readiness is not valid")
    if send_readiness.get("recommended_now") != ["ERG-003", "ERG-002"]:
        raise EnterpriseDualReviewHandoffError(
            "recommended send order must be ERG-003 then ERG-002"
        )

    packet_summaries = [_packet_summary(repo_root, review) for review in RECOMMENDED_REVIEWS]
    payload = _handoff_payload(
        commit=_git(repo_root, ["rev-parse", "HEAD"]),
        dirty=bool(_git(repo_root, ["status", "--short"])),
        packet_summaries=packet_summaries,
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
    except EnterpriseDualReviewHandoffError as exc:
        failures.append(str(exc))
        output_dir = DEFAULT_OUTPUT_DIR

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]
    queue = _read(repo_root / "docs/codex/enterprise-external-review-queue.md")
    send_readiness_doc = _read(repo_root / "docs/codex/enterprise-review-send-readiness.md")
    handoff_doc = _read(repo_root / DOC_REL)
    markdown_text = _read(output_dir / MARKDOWN_NAME)
    json_text = _read(output_dir / JSON_NAME)
    hash_text = _read(output_dir / HASH_NAME)

    try:
        hashes = json.loads(hash_text) if hash_text else {"artifacts": []}
    except json.JSONDecodeError:
        hashes = {"artifacts": []}
        failures.append("dual handoff hash manifest is not valid JSON")
    artifact_hashes_match_files = _artifact_hashes_match_files(output_dir=output_dir, hashes=hashes)

    for phrase in [
        "Status: operator handoff pointer for the two currently send-ready enterprise reviews.",
        "make enterprise-dual-review-handoff",
        "make enterprise-dual-review-handoff-check",
        "`ERG-003`",
        "`ERG-002`",
        "does not close either lane",
        "does not approve Mission Control runtime behavior",
        "does not approve live VM/container inspection",
    ]:
        if phrase not in handoff_doc:
            failures.append(f"dual handoff doc is missing phrase: {phrase}")
    for phrase in [
        "Recommended enterprise reviews: `ERG-003`, `ERG-002`",
        "Attach `ERG-003` packet",
        "Attach `ERG-002` packet",
        "Response paths after review",
        "What remains blocked",
        "EXT-SVP-###",
        "EXT-MC-DISPLAY-###",
        "hash manifest matches files: `true`",
    ]:
        if phrase not in markdown_text:
            failures.append(f"generated dual handoff is missing phrase: {phrase}")
    for phrase in [
        '"handoff_type": "ithildin.enterprise_dual_review"',
        '"recommended_gaps": [',
        '"ERG-003"',
        '"ERG-002"',
        '"runtime_changes_allowed": false',
        '"mission_control_runtime_allowed": false',
        '"live_vm_inspection_allowed": false',
        '"closes_erg_003": false',
        '"closes_erg_002": false',
        '"hash_manifest_matches_files": true',
    ]:
        if phrase not in json_text:
            failures.append(f"generated dual handoff JSON is missing phrase: {phrase}")
    for name in [MARKDOWN_NAME, JSON_NAME]:
        if name not in hash_text:
            failures.append(f"dual handoff hash manifest is missing artifact: {name}")
    if HASH_NAME in hash_text:
        failures.append("dual handoff hash manifest must not hash itself")
    if not artifact_hashes_match_files:
        failures.append("dual handoff artifact hashes do not match generated files")

    required_wiring = {
        "Make target": "enterprise-dual-review-handoff:",
        "Check target": "enterprise-dual-review-handoff-check:",
        "Release check": "enterprise-dual-review-handoff-check",
        "Review candidate": "$(MAKE) enterprise-dual-review-handoff",
        "README command": "make enterprise-dual-review-handoff",
        "Queue pointer": "enterprise-dual-review-handoff.md",
        "Docs site": DOC_REL,
        "Review docs": DOC_REL,
        "Review index": DOC_NAME,
        "Release guardrails": "enterprise-dual-review-handoff-check",
        "Send readiness pointer": "enterprise-dual-review-handoff.md",
    }
    if required_wiring["Make target"] not in makefile:
        failures.append("Make target is missing: enterprise-dual-review-handoff")
    if required_wiring["Check target"] not in makefile:
        failures.append("Make target is missing: enterprise-dual-review-handoff-check")
    if required_wiring["Release check"] not in release_check_body:
        failures.append("enterprise-dual-review-handoff-check is missing from release-check")
    if required_wiring["Review candidate"] not in review_candidate_body:
        failures.append("enterprise-dual-review-handoff is missing from review-candidate")
    if required_wiring["README command"] not in readme:
        failures.append("README is missing enterprise dual-review handoff command")
    if required_wiring["Queue pointer"] not in queue:
        failures.append("enterprise queue is missing dual-review handoff pointer")
    if required_wiring["Docs site"] not in docs_site:
        failures.append("enterprise dual-review handoff is missing from docs site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("enterprise dual-review handoff is missing from review docs")
    if required_wiring["Review index"] not in review_index:
        failures.append("review-docs index is missing enterprise dual-review handoff")
    if required_wiring["Release guardrails"] not in release_guardrails:
        failures.append("release guardrails do not require enterprise dual-review handoff")
    if required_wiring["Send readiness pointer"] not in send_readiness_doc:
        failures.append("send-readiness doc is missing dual-review handoff pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "handoff_doc": DOC_REL,
        "output_dir": output_dir.as_posix(),
        "recommended_gaps": ["ERG-003", "ERG-002"],
        "tool_count": 24,
        "artifact_hashes_match_files": artifact_hashes_match_files,
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "live_vm_inspection_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "compliance_automation_allowed": False,
        "public_security_product_positioning_allowed": False,
        "new_power_classes_allowed": False,
        "closes_erg_003": False,
        "closes_erg_002": False,
    }


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise dual-review handoff check",
        f"valid: {str(report['valid']).lower()}",
        f"handoff_doc: {report['handoff_doc']}",
        f"output_dir: {report['output_dir']}",
        "recommended_gaps: " + ", ".join(report["recommended_gaps"]),
        f"tool_count: {report['tool_count']}",
        f"artifact_hashes_match_files: {str(report['artifact_hashes_match_files']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"compliance_automation_allowed: {str(report['compliance_automation_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"closes_erg_003: {str(report['closes_erg_003']).lower()}",
        f"closes_erg_002: {str(report['closes_erg_002']).lower()}",
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
        raise EnterpriseDualReviewHandoffError(
            "must be run from the Ithildin repo root; missing " + ", ".join(missing)
        )


def _handoff_payload(
    *,
    commit: str,
    dirty: bool,
    packet_summaries: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "handoff_type": "ithildin.enterprise_dual_review",
        "recommended_gaps": ["ERG-003", "ERG-002"],
        "commit": commit,
        "dirty": dirty,
        "tool_count": 24,
        "selected_capability": "not selected",
        "packets": packet_summaries,
        "blocked_boundaries": {name: False for name in BLOCKED_BOUNDARIES},
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    packet_sections = []
    response_sections = []
    for packet in payload["packets"]:
        files = "\n".join(f"- `{name}`" for name in packet["attach_files"])
        packet_sections.append(
            f"""### Attach `{packet['gap']}` packet

Review: {packet['name']}.

Directory:

```text
{packet['packet_dir']}
```

Prompt: `{packet['prompt']}`

Finding namespace: `{packet['finding_namespace']}`

Attach these files:

{files}

Attachment integrity:

- hash manifest: `{packet['hash_manifest_path']}`
- expected hashed files: `{packet['expected_hashed_file_count']}`
- hash manifest self-hashed: `{str(packet['hash_manifest_self_hashed']).lower()}`
- hash manifest matches files: `{str(packet['hash_manifest_matches_files']).lower()}`
"""
        )
        response_sections.append(
            f"""### `{packet['gap']}` response path

- Response kit: `{packet['response_kit']}`
- Intake doc: `{packet['intake_doc']}`
- Dry run: `{packet['dry_run']}`
- Closure gate: `{packet['closure_gate']}`
"""
        )
    blocked = "\n".join(f"- `{name}`: `false`" for name in BLOCKED_BOUNDARIES)
    packet_markdown = "\n".join(packet_sections)
    response_markdown = "\n".join(response_sections)
    return f"""# Enterprise Dual Review Handoff

Recommended enterprise reviews: `ERG-003`, `ERG-002`.

Reviewed commit for the handoff: `{payload['commit']}`

Dirty state when generated: `{str(payload['dirty']).lower()}`

Tool count remains `{payload['tool_count']}`.

Current selected capability: `{payload['selected_capability']}`.

## Attachments

{packet_markdown}

## Response paths after review

{response_markdown}

## What remains blocked

This handoff does not close either lane, does not record external review, does not approve Mission
Control runtime behavior, and does not approve live VM/container inspection.

{blocked}

## Regeneration Commands

```sh
make sandbox-vm-static-preflight-external-review-bundle
make mission-control-display-external-review-bundle
make enterprise-review-send-readiness
make enterprise-dual-review-handoff
make enterprise-dual-review-handoff-check
```
"""


def _packet_summary(repo_root: Path, review: dict[str, Any]) -> dict[str, Any]:
    packet_dir = repo_root / review["packet_dir"]
    if not packet_dir.exists():
        raise EnterpriseDualReviewHandoffError(f"{review['gap']} packet directory is missing")
    manifest = _packet_hash_manifest(packet_dir, review["hash_manifest"])
    attach_files = sorted(path.name for path in packet_dir.iterdir() if path.is_file())
    return {
        "gap": review["gap"],
        "name": review["name"],
        "packet_dir": review["packet_dir"].as_posix(),
        "prompt": review["prompt"],
        "finding_namespace": review["finding_namespace"],
        "attach_files": attach_files,
        "hash_manifest_path": (review["packet_dir"] / review["hash_manifest"]).as_posix(),
        "expected_hashed_file_count": manifest["expected_hashed_file_count"],
        "hash_manifest_self_hashed": manifest["hash_manifest_self_hashed"],
        "hash_manifest_matches_files": manifest["hash_manifest_matches_files"],
        "hashed_files": manifest["hashed_files"],
        "response_kit": review["response_kit"],
        "dry_run": review["dry_run"],
        "closure_gate": review["closure_gate"],
        "intake_doc": review["intake_doc"],
    }


def _packet_hash_manifest(packet_dir: Path, hash_name: str) -> dict[str, Any]:
    hash_path = packet_dir / hash_name
    if not hash_path.exists():
        raise EnterpriseDualReviewHandoffError(f"packet hash manifest is missing: {hash_name}")
    try:
        manifest = json.loads(hash_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EnterpriseDualReviewHandoffError(
            f"packet hash manifest is not valid JSON: {hash_name}"
        ) from exc
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise EnterpriseDualReviewHandoffError(
            f"packet hash manifest must contain an artifacts list: {hash_name}"
        )
    hashed_paths: set[str] = set()
    for entry in artifacts:
        if not isinstance(entry, dict):
            raise EnterpriseDualReviewHandoffError(
                f"packet hash manifest contains a non-object artifact: {hash_name}"
            )
        path = entry.get("path")
        sha256 = entry.get("sha256")
        byte_count = entry.get("bytes")
        if not isinstance(path, str):
            raise EnterpriseDualReviewHandoffError(
                f"packet hash manifest artifact is missing a path: {hash_name}"
            )
        if path == hash_name:
            raise EnterpriseDualReviewHandoffError(
                f"packet hash manifest must not hash itself: {hash_name}"
            )
        if not isinstance(sha256, str) or not sha256.startswith("sha256:"):
            raise EnterpriseDualReviewHandoffError(
                f"packet hash manifest artifact has invalid sha256: {path}"
            )
        if not isinstance(byte_count, int) or byte_count <= 0:
            raise EnterpriseDualReviewHandoffError(
                f"packet hash manifest artifact has invalid byte count: {path}"
            )
        artifact_path = packet_dir / path
        if not artifact_path.exists() or not artifact_path.is_file():
            raise EnterpriseDualReviewHandoffError(
                f"packet hash manifest artifact file is missing: {path}"
            )
        data = artifact_path.read_bytes()
        if sha256 != "sha256:" + hashlib.sha256(data).hexdigest():
            raise EnterpriseDualReviewHandoffError(
                f"packet hash manifest artifact digest mismatch: {path}"
            )
        if byte_count != len(data):
            raise EnterpriseDualReviewHandoffError(
                f"packet hash manifest artifact byte count mismatch: {path}"
            )
        hashed_paths.add(path)
    expected_hashed = {
        path.name for path in packet_dir.iterdir() if path.is_file() and path.name != hash_name
    }
    if hashed_paths != expected_hashed:
        missing = sorted(expected_hashed - hashed_paths)
        extra = sorted(hashed_paths - expected_hashed)
        details = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append("extra: " + ", ".join(extra))
        raise EnterpriseDualReviewHandoffError(
            f"packet hash manifest mismatch for {hash_name}; " + "; ".join(details)
        )
    return {
        "expected_hashed_file_count": len(expected_hashed),
        "hash_manifest_self_hashed": hash_name in hashed_paths,
        "hash_manifest_matches_files": True,
        "hashed_files": sorted(hashed_paths),
    }


def _artifact_hashes(output_dir: Path, names: list[str]) -> dict[str, Any]:
    artifacts = []
    for name in names:
        data = (output_dir / name).read_bytes()
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
        if not isinstance(path, str) or path == HASH_NAME:
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

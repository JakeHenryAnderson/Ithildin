"""Build a send manifest for the current enterprise external-review packets."""

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

from scripts import (
    enterprise_dual_review_outbox,
    enterprise_response_status_board,
    enterprise_review_send_readiness,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-review-send-manifest.md"
DOC_NAME = "enterprise-review-send-manifest.md"
DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/enterprise-review-send-manifest")
MARKDOWN_NAME = "ENTERPRISE_REVIEW_SEND_MANIFEST.md"
JSON_NAME = "enterprise-review-send-manifest.json"
HASH_NAME = "enterprise-review-send-manifest-artifact-hashes.json"
RECOMMENDED_GAPS = ["ERG-003", "ERG-002"]
BOUNDARY_FLAGS = {
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
    "records_external_review": False,
    "normalizes_responses": False,
}


class EnterpriseReviewSendManifestError(RuntimeError):
    """Raised when the send manifest cannot be built or validated."""


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
        output_dir = build_manifest(ROOT, args.output_dir)
    except EnterpriseReviewSendManifestError as exc:
        print(f"enterprise review send manifest failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built enterprise review send manifest at {output_dir}")
    return 0


def build_manifest(repo_root: Path, output_dir: Path) -> Path:
    _validate_repo_root(repo_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    readiness = enterprise_review_send_readiness.build_report(repo_root)
    status = enterprise_response_status_board.build_report(repo_root)
    if readiness.get("valid") is not True:
        raise EnterpriseReviewSendManifestError("enterprise review send-readiness is not valid")
    if status.get("valid") is not True:
        raise EnterpriseReviewSendManifestError("enterprise response status board is not valid")

    outbox_dir = enterprise_dual_review_outbox.build_outbox(
        repo_root, enterprise_dual_review_outbox.DEFAULT_OUTPUT_DIR
    )
    outbox_payload = json.loads(
        (outbox_dir / enterprise_dual_review_outbox.JSON_NAME).read_text(encoding="utf-8")
    )
    outbox_hashes = json.loads(
        (outbox_dir / enterprise_dual_review_outbox.HASH_NAME).read_text(encoding="utf-8")
    )
    payload = _manifest_payload(
        repo_root=repo_root,
        readiness=readiness,
        status=status,
        outbox_dir=outbox_dir,
        outbox_payload=outbox_payload,
        outbox_hashes=outbox_hashes,
    )
    (output_dir / MARKDOWN_NAME).write_text(_render_markdown(payload), encoding="utf-8")
    (output_dir / JSON_NAME).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    hashes = _artifact_hashes(output_dir)
    (output_dir / HASH_NAME).write_text(
        json.dumps(hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output_dir


def build_check_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    try:
        output_dir = build_manifest(repo_root, DEFAULT_OUTPUT_DIR)
    except EnterpriseReviewSendManifestError as exc:
        failures.append(str(exc))
        output_dir = DEFAULT_OUTPUT_DIR

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    queue = _read(repo_root / "docs/codex/enterprise-external-review-queue.md")
    send_readiness = _read(repo_root / "docs/codex/enterprise-review-send-readiness.md")
    outbox_doc = _read(repo_root / "docs/codex/enterprise-dual-review-outbox.md")
    manifest_doc = _read(repo_root / DOC_REL)
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]
    markdown_text = _read(output_dir / MARKDOWN_NAME)
    json_text = _read(output_dir / JSON_NAME)
    hash_text = _read(output_dir / HASH_NAME)

    try:
        hash_manifest = json.loads(hash_text) if hash_text else {"artifacts": []}
    except json.JSONDecodeError:
        hash_manifest = {"artifacts": []}
        failures.append("enterprise review send manifest hashes are not valid JSON")

    for phrase in [
        "Status: generated send manifest for current enterprise external-review packets.",
        "make enterprise-review-send-manifest",
        "make enterprise-review-send-manifest-check",
        "`ERG-003`",
        "`ERG-002`",
        "does not record external review",
        "does not normalize responses",
        "does not close either lane",
    ]:
        if phrase not in manifest_doc:
            failures.append(f"enterprise review send manifest doc is missing phrase: {phrase}")
    for phrase in [
        "Enterprise Review Send Manifest",
        "Recommended send set",
        "ERG-003",
        "ERG-002",
        "Post-send response path",
        "Blocked boundaries",
        "records_external_review: `false`",
        "normalizes_responses: `false`",
    ]:
        if phrase not in markdown_text:
            failures.append(f"generated send manifest is missing phrase: {phrase}")
    for phrase in [
        '"manifest_type": "ithildin.enterprise_review_send_manifest"',
        '"recommended_gaps": [',
        '"ERG-003"',
        '"ERG-002"',
        '"records_external_review": false',
        '"normalizes_responses": false',
        '"closes_erg_003": false',
        '"closes_erg_002": false',
        '"outbox_hash_manifest"',
    ]:
        if phrase not in json_text:
            failures.append(f"generated send manifest JSON is missing phrase: {phrase}")

    expected_artifacts = {MARKDOWN_NAME, JSON_NAME}
    hashed_paths = {artifact.get("path") for artifact in hash_manifest.get("artifacts", [])}
    if not expected_artifacts.issubset(hashed_paths):
        failures.append("send manifest hash file is missing generated artifacts")
    if HASH_NAME in hashed_paths:
        failures.append("send manifest hash file must not hash itself")
    if not _artifact_hashes_match_files(output_dir, hash_manifest):
        failures.append("send manifest artifact hashes do not match files")

    required_wiring = {
        "Make target": "enterprise-review-send-manifest:",
        "Check target": "enterprise-review-send-manifest-check:",
        "Release check": "enterprise-review-send-manifest-check",
        "Review candidate": "$(MAKE) enterprise-review-send-manifest",
        "README command": "make enterprise-review-send-manifest",
        "Queue pointer": "enterprise-review-send-manifest.md",
        "Send readiness pointer": "enterprise-review-send-manifest",
        "Outbox pointer": "enterprise-review-send-manifest",
        "Docs site": DOC_REL,
        "Review docs": DOC_REL,
        "Review index": DOC_NAME,
        "Release guardrails": "enterprise-review-send-manifest-check",
    }
    if required_wiring["Make target"] not in makefile:
        failures.append("Make target is missing: enterprise-review-send-manifest")
    if required_wiring["Check target"] not in makefile:
        failures.append("Make target is missing: enterprise-review-send-manifest-check")
    if required_wiring["Release check"] not in release_check_body:
        failures.append("enterprise-review-send-manifest-check is missing from release-check")
    if required_wiring["Review candidate"] not in review_candidate_body:
        failures.append("enterprise-review-send-manifest is missing from review-candidate")
    if required_wiring["README command"] not in readme:
        failures.append("README is missing enterprise review send manifest command")
    if required_wiring["Queue pointer"] not in queue:
        failures.append("enterprise queue is missing review send manifest pointer")
    if required_wiring["Send readiness pointer"] not in send_readiness:
        failures.append("enterprise send-readiness doc is missing review send manifest pointer")
    if required_wiring["Outbox pointer"] not in outbox_doc:
        failures.append("enterprise dual-review outbox doc is missing review send manifest pointer")
    if required_wiring["Docs site"] not in docs_site:
        failures.append("enterprise review send manifest is missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("enterprise review send manifest is missing from review docs")
    if required_wiring["Review index"] not in review_index:
        failures.append("review-docs index is missing enterprise review send manifest")
    if required_wiring["Release guardrails"] not in release_guardrails:
        failures.append("release guardrails do not require enterprise review send manifest")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "manifest_doc": DOC_REL,
        "output_dir": output_dir.as_posix(),
        "recommended_gaps": RECOMMENDED_GAPS,
        "tool_count": 24,
        "artifact_hashes_match_files": _artifact_hashes_match_files(
            output_dir, hash_manifest
        ),
        **BOUNDARY_FLAGS,
    }


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise review send manifest check",
        f"valid: {str(report['valid']).lower()}",
        f"manifest_doc: {report['manifest_doc']}",
        f"output_dir: {report['output_dir']}",
        "recommended_gaps: " + ", ".join(report["recommended_gaps"]),
        f"tool_count: {report['tool_count']}",
        f"artifact_hashes_match_files: {str(report['artifact_hashes_match_files']).lower()}",
    ]
    lines.extend(f"{key}: {str(value).lower()}" for key, value in BOUNDARY_FLAGS.items())
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _manifest_payload(
    *,
    repo_root: Path,
    readiness: dict[str, Any],
    status: dict[str, Any],
    outbox_dir: Path,
    outbox_payload: dict[str, Any],
    outbox_hashes: dict[str, Any],
) -> dict[str, Any]:
    packets = []
    for packet in outbox_payload["packets"]:
        packets.append(
            {
                "gap": packet["gap"],
                "name": packet["name"],
                "finding_namespace": packet["finding_namespace"],
                "outbox_dir": packet["outbox_dir"],
                "prompt": f"{packet['outbox_dir']}/{packet['prompt']}",
                "copied_file_count": packet["copied_file_count"],
                "response_kit": packet["response_kit"],
                "intake_doc": packet["intake_doc"],
                "dry_run": packet["dry_run"],
                "closure_gate": packet["closure_gate"],
            }
        )
    return {
        "schema_version": "1",
        "manifest_type": "ithildin.enterprise_review_send_manifest",
        "commit": _git(repo_root, ["rev-parse", "HEAD"]),
        "dirty": bool(_git(repo_root, ["status", "--short"])),
        "tool_count": 24,
        "selected_capability": "not selected",
        "recommended_gaps": RECOMMENDED_GAPS,
        "packet_handoff_ready_count": readiness.get("packet_handoff_ready_count"),
        "response_present_count": status.get("response_present_count"),
        "closure_ready_count": status.get("closure_ready_count"),
        "outbox_dir": _repo_rel(repo_root, outbox_dir),
        "outbox_hash_manifest": {
            "path": _repo_rel(repo_root, outbox_dir / enterprise_dual_review_outbox.HASH_NAME),
            "artifact_count": outbox_hashes.get("artifact_count"),
            "sha256": hashlib.sha256(
                (outbox_dir / enterprise_dual_review_outbox.HASH_NAME).read_bytes()
            ).hexdigest(),
        },
        "send_set": packets,
        "post_send_commands": [
            "make enterprise-dual-response-inbox",
            "make enterprise-response-status-board",
            "make enterprise-response-intake-drill",
            "make sandbox-vm-static-preflight-response-dry-run",
            "make mission-control-display-response-dry-run",
        ],
        "blocked_boundaries": BOUNDARY_FLAGS,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    send_rows = "\n".join(
        (
            f"| `{packet['gap']}` | {packet['name']} | `{packet['prompt']}` | "
            f"`{packet['copied_file_count']}` | `{packet['finding_namespace']}` |"
        )
        for packet in payload["send_set"]
    )
    response_rows = "\n".join(
        (
            f"| `{packet['gap']}` | `{packet['response_kit']}` | `{packet['intake_doc']}` | "
            f"`{packet['dry_run']}` | `{packet['closure_gate']}` |"
        )
        for packet in payload["send_set"]
    )
    blocked = "\n".join(
        f"- {key}: `{str(value).lower()}`"
        for key, value in payload["blocked_boundaries"].items()
    )
    commands = "\n".join(payload["post_send_commands"])
    return f"""# Enterprise Review Send Manifest

Status: generated send manifest for current enterprise external-review packets.

Reviewed commit: `{payload['commit']}`

Dirty state when generated: `{str(payload['dirty']).lower()}`

Tool count remains `{payload['tool_count']}`.

Current selected capability: `{payload['selected_capability']}`.

## Recommended send set

| Gap | Review lane | Prompt | Attachment count | Finding namespace |
| --- | --- | --- | ---: | --- |
{send_rows}

Outbox root: `{payload['outbox_dir']}`

Outbox hash manifest: `{payload['outbox_hash_manifest']['path']}`

Outbox hash manifest artifact count: `{payload['outbox_hash_manifest']['artifact_count']}`

## Post-send response path

| Gap | Response kit | Intake doc | Dry run | Closure gate |
| --- | --- | --- | --- | --- |
{response_rows}

After sending the packets, use these commands while waiting for responses:

```sh
{commands}
```

## Blocked boundaries

{blocked}

This manifest does not record external review, does not normalize responses, and does not close
either lane. It only records the current send set and response path so the operator handoff can be
checked consistently.
"""


def _validate_repo_root(repo_root: Path) -> None:
    missing = [
        marker
        for marker in ["pyproject.toml", "Makefile", "tool-manifests.lock.json"]
        if not (repo_root / marker).exists()
    ]
    if missing:
        raise EnterpriseReviewSendManifestError(
            "must be run from the Ithildin repo root; missing " + ", ".join(missing)
        )


def _artifact_hashes(output_dir: Path) -> dict[str, Any]:
    artifacts = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name == HASH_NAME:
            continue
        rel = path.relative_to(output_dir).as_posix()
        data = path.read_bytes()
        artifacts.append(
            {
                "path": rel,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return {
        "schema_version": "1",
        "artifacts": artifacts,
        "artifact_count": len(artifacts),
        "hash_manifest_self_hashed": False,
    }


def _artifact_hashes_match_files(output_dir: Path, hashes: dict[str, Any]) -> bool:
    for artifact in hashes.get("artifacts", []):
        path = output_dir / artifact.get("path", "")
        if not path.is_file():
            return False
        data = path.read_bytes()
        if artifact.get("bytes") != len(data):
            return False
        if artifact.get("sha256") != hashlib.sha256(data).hexdigest():
            return False
    return True


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _repo_rel(repo_root: Path, path: Path) -> str:
    if not path.is_absolute():
        return path.as_posix()
    return path.relative_to(repo_root).as_posix()


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


if __name__ == "__main__":
    raise SystemExit(main())

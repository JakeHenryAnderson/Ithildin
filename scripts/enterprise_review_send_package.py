"""Build a compact operator package index for enterprise review sends."""

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
    enterprise_dual_response_inbox,
    enterprise_dual_review_outbox,
    enterprise_review_send_manifest,
    enterprise_review_send_quickstart,
    enterprise_review_send_receipt_template,
    enterprise_review_submission_prompt,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-review-send-package.md"
DOC_NAME = "enterprise-review-send-package.md"
DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/enterprise-review-send-package")
MARKDOWN_NAME = "ENTERPRISE_REVIEW_SEND_PACKAGE.md"
JSON_NAME = "enterprise-review-send-package.json"
HASH_NAME = "enterprise-review-send-package-artifact-hashes.json"
RECOMMENDED_GAPS = ["ERG-003", "ERG-002"]
BOUNDARY_FLAGS = {
    "records_external_review": False,
    "normalizes_responses": False,
    "writes_response_files": False,
    "closes_erg_003": False,
    "closes_erg_002": False,
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
}


class EnterpriseReviewSendPackageError(RuntimeError):
    """Raised when the send package cannot be built or validated."""


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
        output_dir = build_package(ROOT, args.output_dir)
    except EnterpriseReviewSendPackageError as exc:
        print(f"enterprise review send package failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built enterprise review send package at {output_dir}")
    return 0


def build_package(repo_root: Path, output_dir: Path) -> Path:
    _validate_repo_root(repo_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    outbox_dir = enterprise_dual_review_outbox.build_outbox(
        repo_root, enterprise_dual_review_outbox.DEFAULT_OUTPUT_DIR
    )
    manifest_dir = enterprise_review_send_manifest.build_manifest(
        repo_root, enterprise_review_send_manifest.DEFAULT_OUTPUT_DIR
    )
    quickstart_dir = enterprise_review_send_quickstart.build_quickstart(
        repo_root, enterprise_review_send_quickstart.DEFAULT_OUTPUT_DIR
    )
    submission_dir = enterprise_review_submission_prompt.build_prompt(
        repo_root, enterprise_review_submission_prompt.DEFAULT_OUTPUT_DIR
    )
    receipt_dir = enterprise_review_send_receipt_template.build_template(
        repo_root, enterprise_review_send_receipt_template.DEFAULT_OUTPUT_DIR
    )
    inbox_dir = enterprise_dual_response_inbox.build_inbox(
        repo_root, enterprise_dual_response_inbox.DEFAULT_OUTPUT_DIR
    )

    manifest_payload = _read_json(manifest_dir / enterprise_review_send_manifest.JSON_NAME)
    payload = _package_payload(
        repo_root=repo_root,
        outbox_dir=outbox_dir,
        manifest_dir=manifest_dir,
        quickstart_dir=quickstart_dir,
        submission_dir=submission_dir,
        receipt_dir=receipt_dir,
        inbox_dir=inbox_dir,
        manifest_payload=manifest_payload,
    )
    (output_dir / MARKDOWN_NAME).write_text(_render_markdown(payload), encoding="utf-8")
    (output_dir / JSON_NAME).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    hashes = _artifact_hashes(output_dir)
    (output_dir / HASH_NAME).write_text(
        json.dumps(hashes, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_dir


def build_check_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    try:
        output_dir = build_package(repo_root, DEFAULT_OUTPUT_DIR)
    except EnterpriseReviewSendPackageError as exc:
        failures.append(str(exc))
        output_dir = DEFAULT_OUTPUT_DIR

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    quickstart_doc = _read(repo_root / "docs/codex/enterprise-review-send-quickstart.md")
    manifest_doc = _read(repo_root / "docs/codex/enterprise-review-send-manifest.md")
    receipt_doc = _read(repo_root / "docs/codex/enterprise-review-send-receipt-template.md")
    package_doc = _read(repo_root / DOC_REL)
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition(
        "\n\n"
    )[0]
    refresh_body = makefile.partition("enterprise-review-send-refresh:")[2].partition(
        "\n\n"
    )[0]
    markdown_text = _read(output_dir / MARKDOWN_NAME)
    json_text = _read(output_dir / JSON_NAME)
    hash_text = _read(output_dir / HASH_NAME)

    try:
        hashes = json.loads(hash_text) if hash_text else {"artifacts": []}
    except json.JSONDecodeError:
        hashes = {"artifacts": []}
        failures.append("enterprise review send package hashes are not valid JSON")
    hashed_paths = {artifact.get("path") for artifact in hashes.get("artifacts", [])}

    _require_phrases(
        failures,
        "send package doc",
        package_doc,
        [
            "Status: generated operator package index for the current enterprise send set.",
            "make enterprise-review-send-package",
            "make enterprise-review-send-package-check",
            "`ERG-003`",
            "`ERG-002`",
            "does not record external review",
            "does not normalize responses",
            "does not close `ERG-003` or `ERG-002`",
        ],
    )
    _require_phrases(
        failures,
        "generated send package",
        markdown_text,
        [
            "Enterprise Review Send Package",
            "Lane attachment manifest",
            "ERG-003",
            "ERG-002",
            "ATTACHMENT_MANIFEST.md",
            "Submission prompt",
            "Send receipt template",
            "Dual response inbox",
            "records_external_review: `false`",
            "normalizes_responses: `false`",
            "closes_erg_003: `false`",
            "closes_erg_002: `false`",
        ],
    )
    _require_phrases(
        failures,
        "generated send package JSON",
        json_text,
        [
            '"package_type": "ithildin.enterprise_review_send_package"',
            '"ERG-003"',
            '"ERG-002"',
            '"attachment_manifest"',
            '"records_external_review": false',
            '"normalizes_responses": false',
            '"closes_erg_003": false',
            '"closes_erg_002": false',
        ],
    )
    if {MARKDOWN_NAME, JSON_NAME} - hashed_paths:
        failures.append("send package hash manifest is missing generated artifacts")
    if HASH_NAME in hashed_paths:
        failures.append("send package hash manifest must not hash itself")
    if not _artifact_hashes_match_files(output_dir, hashes):
        failures.append("send package artifact hashes do not match files")

    wiring_checks = {
        "Make target": ("enterprise-review-send-package:", makefile),
        "Check target": ("enterprise-review-send-package-check:", makefile),
        "Release check": ("enterprise-review-send-package-check", release_check_body),
        "Review candidate": ("$(MAKE) enterprise-review-send-package", review_candidate_body),
        "Send refresh": ("$(MAKE) enterprise-review-send-package", refresh_body),
        "README command": ("make enterprise-review-send-package", readme),
        "Docs site": (DOC_REL, docs_site),
        "Review docs": (DOC_REL, "\n".join(review_docs.REVIEW_DOCS)),
        "Review index": (DOC_NAME, review_index),
        "Release guardrails": ("enterprise-review-send-package-check", release_guardrails),
        "Quickstart pointer": ("enterprise-review-send-package", quickstart_doc),
        "Manifest pointer": ("enterprise-review-send-package", manifest_doc),
        "Receipt pointer": ("enterprise-review-send-package", receipt_doc),
    }
    for label, (needle, haystack) in wiring_checks.items():
        if needle not in haystack:
            failures.append(f"{label} is missing {needle}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "package_doc": DOC_REL,
        "output_dir": output_dir.as_posix(),
        "recommended_gaps": RECOMMENDED_GAPS,
        "tool_count": 24,
        "artifact_hashes_match_files": _artifact_hashes_match_files(output_dir, hashes),
        **BOUNDARY_FLAGS,
    }


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise review send package check",
        f"valid: {str(report['valid']).lower()}",
        f"package_doc: {report['package_doc']}",
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


def _package_payload(
    *,
    repo_root: Path,
    outbox_dir: Path,
    manifest_dir: Path,
    quickstart_dir: Path,
    submission_dir: Path,
    receipt_dir: Path,
    inbox_dir: Path,
    manifest_payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "package_type": "ithildin.enterprise_review_send_package",
        "commit": _git(repo_root, ["rev-parse", "HEAD"]),
        "dirty": bool(_git(repo_root, ["status", "--short"])),
        "tool_count": 24,
        "selected_capability": "not selected",
        "recommended_gaps": RECOMMENDED_GAPS,
        "send_artifacts": {
            "dual_review_outbox": _repo_rel(repo_root, outbox_dir),
            "send_manifest": _repo_rel(repo_root, manifest_dir),
            "send_quickstart": _repo_rel(repo_root, quickstart_dir),
            "submission_prompt": _repo_rel(repo_root, submission_dir),
            "send_receipt_template": _repo_rel(repo_root, receipt_dir),
            "dual_response_inbox": _repo_rel(repo_root, inbox_dir),
        },
        "send_set": [
            _send_lane(manifest_payload["outbox_dir"], packet)
            for packet in manifest_payload["send_set"]
        ],
        "blocked_boundaries": dict(BOUNDARY_FLAGS),
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    send_rows = "\n".join(
        (
            f"| `{packet['gap']}` | {packet['name']} | `{packet['prompt']}` | "
            f"`{packet['attachment_manifest']}` | `{packet['hash_manifest']}` | "
            f"`{packet['raw_response_path']}` |"
        )
        for packet in payload["send_set"]
    )
    artifact_rows = "\n".join(
        f"| {label} | `{path}` |"
        for label, path in _artifact_labels(payload["send_artifacts"]).items()
    )
    blocked = "\n".join(
        f"- {key}: `{str(value).lower()}`"
        for key, value in payload["blocked_boundaries"].items()
    )
    return f"""# Enterprise Review Send Package

Status: generated operator package index for the current enterprise send set.

Commit: `{payload['commit']}`

Dirty state when generated: `{str(payload['dirty']).lower()}`

Tool count: `{payload['tool_count']}`

Recommended send set: `ERG-003`, `ERG-002`

## Lane requests

| Gap | Review lane | Prompt | Lane attachment manifest | Lane hash manifest | Raw response path |
| --- | --- | --- | --- | --- | --- |
{send_rows}

## Operator artifacts

| Artifact | Path |
| --- | --- |
{artifact_rows}

## Boundary flags

{blocked}

This package does not record external review, does not normalize responses, does not write
response files, and does not close `ERG-003` or `ERG-002`. It is a generated index over the
current send artifacts so the operator can send the two review requests consistently.
"""


def _send_lane(outbox_root: str, packet: dict[str, Any]) -> dict[str, str]:
    gap = str(packet["gap"])
    lane_outbox = f"{outbox_root}/{packet['outbox_dir']}"
    return {
        "gap": gap,
        "name": str(packet["name"]),
        "finding_namespace": str(packet["finding_namespace"]),
        "outbox_dir": lane_outbox,
        "prompt": f"{outbox_root}/{packet['prompt']}",
        "attachment_manifest": f"{outbox_root}/{packet['attachment_manifest']}",
        "hash_manifest": _lane_hash_manifest(lane_outbox, gap),
        "raw_response_path": (
            "var/review-runs/enterprise-dual-response-inbox/"
            f"RAW_RESPONSE_{gap}.md"
        ),
    }


def _lane_hash_manifest(lane_outbox: str, gap: str) -> str:
    if gap == "ERG-003":
        return (
            f"{lane_outbox}/"
            "sandbox-vm-static-preflight-external-review-artifact-hashes.json"
        )
    if gap == "ERG-002":
        return (
            f"{lane_outbox}/"
            "mission-control-display-external-review-artifact-hashes.json"
        )
    return f"{lane_outbox}/unknown-artifact-hashes.json"


def _artifact_labels(artifacts: dict[str, str]) -> dict[str, str]:
    labels = {
        "dual_review_outbox": "Dual review outbox",
        "send_manifest": "Send manifest",
        "send_quickstart": "Send quickstart",
        "submission_prompt": "Submission prompt",
        "send_receipt_template": "Send receipt template",
        "dual_response_inbox": "Dual response inbox",
    }
    return {labels.get(key, key): value for key, value in artifacts.items()}


def _validate_repo_root(repo_root: Path) -> None:
    missing = [
        marker
        for marker in ["pyproject.toml", "Makefile", "tool-manifests.lock.json"]
        if not (repo_root / marker).exists()
    ]
    if missing:
        raise EnterpriseReviewSendPackageError(
            "must be run from the Ithildin repo root; missing " + ", ".join(missing)
        )


def _artifact_hashes(output_dir: Path) -> dict[str, Any]:
    artifacts = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name == HASH_NAME:
            continue
        data = path.read_bytes()
        artifacts.append(
            {
                "path": path.relative_to(output_dir).as_posix(),
                "bytes": len(data),
                "sha256": "sha256:" + hashlib.sha256(data).hexdigest(),
            }
        )
    return {"schema_version": "1", "artifacts": artifacts}


def _artifact_hashes_match_files(output_dir: Path, manifest: dict[str, Any]) -> bool:
    for artifact in manifest.get("artifacts", []):
        path = output_dir / artifact.get("path", "")
        if not path.is_file():
            return False
        data = path.read_bytes()
        if artifact.get("bytes") != len(data):
            return False
        if artifact.get("sha256") != "sha256:" + hashlib.sha256(data).hexdigest():
            return False
    return True


def _require_phrases(
    failures: list[str],
    label: str,
    text: str,
    phrases: list[str],
) -> None:
    for phrase in phrases:
        if phrase not in text:
            failures.append(f"{label} is missing phrase: {phrase}")


def _read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


def _repo_rel(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())

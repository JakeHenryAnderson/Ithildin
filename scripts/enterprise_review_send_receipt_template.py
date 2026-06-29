"""Build an operator receipt template for enterprise external-review sends."""

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

from scripts import enterprise_review_send_manifest, review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-review-send-receipt-template.md"
DOC_NAME = "enterprise-review-send-receipt-template.md"
DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/enterprise-review-send-receipt-template")
MARKDOWN_NAME = "ENTERPRISE_REVIEW_SEND_RECEIPT_TEMPLATE.md"
JSON_NAME = "enterprise-review-send-receipt-template.json"
HASH_NAME = "enterprise-review-send-receipt-template-artifact-hashes.json"
RAW_RESPONSE_INBOX_DIR = "var/review-runs/enterprise-dual-response-inbox"
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


class EnterpriseReviewSendReceiptTemplateError(RuntimeError):
    """Raised when the send receipt template cannot be built or validated."""


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
        output_dir = build_template(ROOT, args.output_dir)
    except EnterpriseReviewSendReceiptTemplateError as exc:
        print(f"enterprise review send receipt template failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built enterprise review send receipt template at {output_dir}")
    return 0


def build_template(repo_root: Path, output_dir: Path) -> Path:
    _validate_repo_root(repo_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_dir = enterprise_review_send_manifest.build_manifest(
        repo_root, enterprise_review_send_manifest.DEFAULT_OUTPUT_DIR
    )
    manifest_payload = json.loads(
        (manifest_dir / enterprise_review_send_manifest.JSON_NAME).read_text(
            encoding="utf-8"
        )
    )
    manifest_hashes = json.loads(
        (manifest_dir / enterprise_review_send_manifest.HASH_NAME).read_text(
            encoding="utf-8"
        )
    )
    payload = _template_payload(
        repo_root=repo_root,
        manifest_dir=manifest_dir,
        manifest_payload=manifest_payload,
        manifest_hashes=manifest_hashes,
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
        output_dir = build_template(repo_root, DEFAULT_OUTPUT_DIR)
    except EnterpriseReviewSendReceiptTemplateError as exc:
        failures.append(str(exc))
        output_dir = DEFAULT_OUTPUT_DIR

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    send_manifest_doc = _read(repo_root / "docs/codex/enterprise-review-send-manifest.md")
    submission_doc = _read(repo_root / "docs/codex/enterprise-review-submission-prompt.md")
    handoff_drill_doc = _read(repo_root / "docs/codex/enterprise-review-handoff-drill.md")
    receipt_doc = _read(repo_root / DOC_REL)
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]
    markdown_text = _read(output_dir / MARKDOWN_NAME)
    json_text = _read(output_dir / JSON_NAME)
    hash_text = _read(output_dir / HASH_NAME)

    try:
        hash_manifest = json.loads(hash_text) if hash_text else {"artifacts": []}
    except json.JSONDecodeError:
        hash_manifest = {"artifacts": []}
        failures.append("enterprise review send receipt template hashes are not valid JSON")

    for phrase in [
        "Status: generated operator template for recording external-review send receipts",
        "make enterprise-review-send-receipt-template",
        "make enterprise-review-send-receipt-template-check",
        "does not record external review by itself",
        "does not normalize responses",
        "does not write raw response files",
        "does not close `ERG-003` or `ERG-002`",
    ]:
        if phrase not in receipt_doc:
            failures.append(
                "enterprise review send receipt template doc is missing phrase: "
                f"{phrase}"
            )
    for phrase in [
        "Enterprise Review Send Receipt Template",
        "Receipt status",
        "sent: `false`",
        "Operator fill-in fields",
        "Packet hash evidence",
        f"{RAW_RESPONSE_INBOX_DIR}/RAW_RESPONSE_ERG-003.md",
        f"{RAW_RESPONSE_INBOX_DIR}/RAW_RESPONSE_ERG-002.md",
        "records_external_review: `false`",
        "writes_response_files: `false`",
        "closes_erg_003: `false`",
        "closes_erg_002: `false`",
    ]:
        if phrase not in markdown_text:
            failures.append(f"generated send receipt template is missing phrase: {phrase}")
    for phrase in [
        '"template_type": "ithildin.enterprise_review_send_receipt_template"',
        '"sent": false',
        '"ERG-003"',
        '"ERG-002"',
        f'"raw_response_path": "{RAW_RESPONSE_INBOX_DIR}/RAW_RESPONSE_ERG-003.md"',
        f'"raw_response_path": "{RAW_RESPONSE_INBOX_DIR}/RAW_RESPONSE_ERG-002.md"',
        '"records_external_review": false',
        '"normalizes_responses": false',
        '"writes_response_files": false',
        '"closes_erg_003": false',
        '"closes_erg_002": false',
    ]:
        if phrase not in json_text:
            failures.append(f"generated send receipt template JSON is missing phrase: {phrase}")

    expected_artifacts = {MARKDOWN_NAME, JSON_NAME}
    hashed_paths = {artifact.get("path") for artifact in hash_manifest.get("artifacts", [])}
    if not expected_artifacts.issubset(hashed_paths):
        failures.append("send receipt template hash file is missing generated artifacts")
    if HASH_NAME in hashed_paths:
        failures.append("send receipt template hash file must not hash itself")
    if not _artifact_hashes_match_files(output_dir, hash_manifest):
        failures.append("send receipt template artifact hashes do not match files")

    required_wiring = {
        "Make target": "enterprise-review-send-receipt-template:",
        "Check target": "enterprise-review-send-receipt-template-check:",
        "Release check": "enterprise-review-send-receipt-template-check",
        "Review candidate": "$(MAKE) enterprise-review-send-receipt-template",
        "README command": "make enterprise-review-send-receipt-template",
        "Docs site": DOC_REL,
        "Review docs": DOC_REL,
        "Review index": DOC_NAME,
        "Release guardrails": "enterprise-review-send-receipt-template-check",
        "Manifest pointer": "enterprise-review-send-receipt-template",
        "Submission pointer": "enterprise-review-send-receipt-template",
        "Handoff drill pointer": "enterprise-review-send-receipt-template",
    }
    if required_wiring["Make target"] not in makefile:
        failures.append("Make target is missing: enterprise-review-send-receipt-template")
    if required_wiring["Check target"] not in makefile:
        failures.append("Make target is missing: enterprise-review-send-receipt-template-check")
    if (
        required_wiring["Release check"] not in release_check_body
        and "release-check: enterprise-review-send-receipt-template-check" not in makefile
    ):
        failures.append(
            "enterprise-review-send-receipt-template-check is missing from release-check"
        )
    if required_wiring["Review candidate"] not in review_candidate_body:
        failures.append("enterprise-review-send-receipt-template is missing from review-candidate")
    if required_wiring["README command"] not in readme:
        failures.append("README is missing enterprise review send receipt template command")
    if required_wiring["Docs site"] not in docs_site:
        failures.append("enterprise review send receipt template is missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("enterprise review send receipt template is missing from review docs")
    if required_wiring["Review index"] not in review_index:
        failures.append("review-docs index is missing enterprise review send receipt template")
    if required_wiring["Release guardrails"] not in release_guardrails:
        failures.append("release guardrails do not require enterprise review send receipt template")
    if required_wiring["Manifest pointer"] not in send_manifest_doc:
        failures.append("send manifest doc is missing send receipt template pointer")
    if required_wiring["Submission pointer"] not in submission_doc:
        failures.append("submission prompt doc is missing send receipt template pointer")
    if required_wiring["Handoff drill pointer"] not in handoff_drill_doc:
        failures.append("handoff drill doc is missing send receipt template pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "template_doc": DOC_REL,
        "output_dir": output_dir.as_posix(),
        "recommended_gaps": RECOMMENDED_GAPS,
        "tool_count": 24,
        "artifact_hashes_match_files": _artifact_hashes_match_files(output_dir, hash_manifest),
        **BOUNDARY_FLAGS,
    }


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise review send receipt template check",
        f"valid: {str(report['valid']).lower()}",
        f"template_doc: {report['template_doc']}",
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


def _template_payload(
    *,
    repo_root: Path,
    manifest_dir: Path,
    manifest_payload: dict[str, Any],
    manifest_hashes: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "template_type": "ithildin.enterprise_review_send_receipt_template",
        "commit": _git(repo_root, ["rev-parse", "HEAD"]),
        "dirty": bool(_git(repo_root, ["status", "--short"])),
        "tool_count": 24,
        "selected_capability": "not selected",
        "sent": False,
        "operator_fill_in": {
            "sent_at": "",
            "channel": "",
            "reviewer_label": "",
            "thread_or_message_url": "",
            "operator_notes": "",
        },
        "send_manifest": {
            "path": _repo_rel(repo_root, manifest_dir / enterprise_review_send_manifest.JSON_NAME),
            "hash_manifest": _repo_rel(
                repo_root,
                manifest_dir / enterprise_review_send_manifest.HASH_NAME,
            ),
            "hash_manifest_sha256": hashlib.sha256(
                (manifest_dir / enterprise_review_send_manifest.HASH_NAME).read_bytes()
            ).hexdigest(),
            "artifact_count": manifest_hashes.get("artifact_count"),
        },
        "receipts": [
            {
                "gap": packet["gap"],
                "name": packet["name"],
                "finding_namespace": packet["finding_namespace"],
                "prompt": packet["prompt"],
                "outbox_dir": packet["outbox_dir"],
                "response_kit": packet["response_kit"],
                "raw_response_path": (
                    f"{RAW_RESPONSE_INBOX_DIR}/RAW_RESPONSE_{packet['gap']}.md"
                ),
                "sent": False,
                "sent_at": "",
                "channel": "",
                "reviewer_label": "",
                "thread_or_message_url": "",
                "message_id": "",
            }
            for packet in manifest_payload["send_set"]
        ],
        "blocked_boundaries": BOUNDARY_FLAGS,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    receipt_rows = "\n".join(
        (
            f"| `{receipt['gap']}` | {receipt['name']} | `{receipt['finding_namespace']}` | "
            f"`{receipt['prompt']}` | `{receipt['raw_response_path']}` |"
        )
        for receipt in payload["receipts"]
    )
    blocked = "\n".join(
        f"- {key}: `{str(value).lower()}`"
        for key, value in payload["blocked_boundaries"].items()
    )
    return f"""# Enterprise Review Send Receipt Template

Status: generated operator send receipt template for current enterprise external-review packets.

Reviewed commit: `{payload['commit']}`

Dirty state when generated: `{str(payload['dirty']).lower()}`

Tool count remains `{payload['tool_count']}`.

Current selected capability: `{payload['selected_capability']}`.

## Receipt status

sent: `{str(payload['sent']).lower()}`

This generated file is a template. It does not prove that the packets were sent.

## Packet hash evidence

Send manifest JSON: `{payload['send_manifest']['path']}`

Send manifest hash manifest: `{payload['send_manifest']['hash_manifest']}`

Send manifest hash manifest SHA-256: `{payload['send_manifest']['hash_manifest_sha256']}`

Send manifest artifact count: `{payload['send_manifest']['artifact_count']}`

## Review receipt rows

| Gap | Review lane | Finding namespace | Prompt | Raw response path |
| --- | --- | --- | --- | --- |
{receipt_rows}

## Operator fill-in fields

Copy this generated template before filling in local operator notes.

- sent_at:
- channel:
- reviewer_label:
- thread_or_message_url:
- message_id:
- operator_notes:

## Blocked boundaries

{blocked}

This template does not record external review, does not normalize responses, does not write raw
response files, and does not close either lane. It only gives the operator a hash-bound place to
record the human send step after it happens.
"""


def _validate_repo_root(repo_root: Path) -> None:
    missing = [
        marker
        for marker in ["pyproject.toml", "Makefile", "tool-manifests.lock.json"]
        if not (repo_root / marker).exists()
    ]
    if missing:
        raise EnterpriseReviewSendReceiptTemplateError(
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

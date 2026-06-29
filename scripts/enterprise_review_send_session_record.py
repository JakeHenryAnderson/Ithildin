"""Build a non-authoritative send-session record scaffold for enterprise reviews."""

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

from scripts import enterprise_review_send_package, review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-review-send-session-record.md"
DOC_NAME = "enterprise-review-send-session-record.md"
DEFAULT_OUTPUT_DIR = Path("var/review-runs/enterprise-review-send-session-record")
MARKDOWN_NAME = "ENTERPRISE_REVIEW_SEND_SESSION_RECORD.md"
JSON_NAME = "enterprise-review-send-session-record.json"
HASH_NAME = "enterprise-review-send-session-record-artifact-hashes.json"
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


class EnterpriseReviewSendSessionRecordError(RuntimeError):
    """Raised when the send-session record cannot be built or validated."""


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
        output_dir = build_record(ROOT, args.output_dir)
    except EnterpriseReviewSendSessionRecordError as exc:
        print(f"enterprise review send session record failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built enterprise review send session record at {output_dir}")
    return 0


def build_record(repo_root: Path, output_dir: Path) -> Path:
    _validate_repo_root(repo_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    package_dir = _ensure_package(repo_root)
    package_payload = _read_json(package_dir / enterprise_review_send_package.JSON_NAME)
    package_hashes = _read_json(package_dir / enterprise_review_send_package.HASH_NAME)
    payload = _record_payload(
        repo_root=repo_root,
        package_dir=package_dir,
        package_payload=package_payload,
        package_hashes=package_hashes,
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
        output_dir = build_record(repo_root, DEFAULT_OUTPUT_DIR)
    except EnterpriseReviewSendSessionRecordError as exc:
        failures.append(str(exc))
        output_dir = DEFAULT_OUTPUT_DIR

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    package_doc = _read(repo_root / "docs/codex/enterprise-review-send-package.md")
    preflight_doc = _read(repo_root / "docs/codex/enterprise-review-send-preflight.md")
    session_doc = _read(repo_root / DOC_REL)
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
        failures.append("enterprise review send session record hashes are not valid JSON")
    hashed_paths = {artifact.get("path") for artifact in hashes.get("artifacts", [])}

    _require_phrases(
        failures,
        "send session record doc",
        session_doc,
        [
            "Status: generated non-authoritative send-session record scaffold.",
            "make enterprise-review-send-session-record",
            "make enterprise-review-send-session-record-check",
            "sent: `false`",
            "does not record external review",
            "does not normalize responses",
            "does not write response files",
            "does not close `ERG-003` or `ERG-002`",
        ],
    )
    _require_phrases(
        failures,
        "generated send session record",
        markdown_text,
        [
            "Enterprise Review Send Session Record",
            "sent: `false`",
            "Operator fill-in fields",
            "Package hash evidence",
            "Lane response landing pads",
            "ERG-003",
            "ERG-002",
            "records_external_review: `false`",
            "normalizes_responses: `false`",
            "writes_response_files: `false`",
            "closes_erg_003: `false`",
            "closes_erg_002: `false`",
        ],
    )
    _require_phrases(
        failures,
        "generated send session record JSON",
        json_text,
        [
            '"record_type": "ithildin.enterprise_review_send_session_record"',
            '"sent": false',
            '"ERG-003"',
            '"ERG-002"',
            '"records_external_review": false',
            '"normalizes_responses": false',
            '"writes_response_files": false',
            '"closes_erg_003": false',
            '"closes_erg_002": false',
        ],
    )
    if {MARKDOWN_NAME, JSON_NAME} - hashed_paths:
        failures.append("send session record hash manifest is missing generated artifacts")
    if HASH_NAME in hashed_paths:
        failures.append("send session record hash manifest must not hash itself")
    if not _artifact_hashes_match_files(output_dir, hashes):
        failures.append("send session record artifact hashes do not match files")

    wiring_checks = {
        "Make target": ("enterprise-review-send-session-record:", makefile),
        "Check target": ("enterprise-review-send-session-record-check:", makefile),
        "Release check": ("enterprise-review-send-session-record-check", release_check_body),
        "Review candidate": (
            "$(MAKE) enterprise-review-send-session-record",
            review_candidate_body,
        ),
        "Send refresh": ("$(MAKE) enterprise-review-send-session-record", refresh_body),
        "README command": ("make enterprise-review-send-session-record", readme),
        "Docs site": (DOC_REL, docs_site),
        "Review docs": (DOC_REL, "\n".join(review_docs.REVIEW_DOCS)),
        "Review index": (DOC_NAME, review_index),
        "Release guardrails": (
            "enterprise-review-send-session-record-check",
            release_guardrails,
        ),
        "Package pointer": ("enterprise-review-send-session-record", package_doc),
        "Preflight pointer": ("enterprise-review-send-session-record", preflight_doc),
    }
    for label, (needle, haystack) in wiring_checks.items():
        if needle not in haystack:
            failures.append(f"{label} is missing enterprise review send session record wiring")

    return {
        "valid": not failures,
        "failures": failures,
        "doc": DOC_REL,
        "output_dir": str(DEFAULT_OUTPUT_DIR),
        "tool_count": 24,
        "selected_capability": "not selected",
        "recommended_gaps": RECOMMENDED_GAPS,
        "records_external_review": False,
        "normalizes_responses": False,
        "writes_response_files": False,
        "closes_erg_003": False,
        "closes_erg_002": False,
    }


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise review send session record check",
        f"valid: {str(report['valid']).lower()}",
        f"doc: {report['doc']}",
        f"output_dir: {report['output_dir']}",
        f"tool_count: {report['tool_count']}",
        f"selected_capability: {report['selected_capability']}",
        f"recommended_gaps: {', '.join(report['recommended_gaps'])}",
        f"records_external_review: {str(report['records_external_review']).lower()}",
        f"normalizes_responses: {str(report['normalizes_responses']).lower()}",
        f"writes_response_files: {str(report['writes_response_files']).lower()}",
        f"closes_erg_003: {str(report['closes_erg_003']).lower()}",
        f"closes_erg_002: {str(report['closes_erg_002']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _record_payload(
    *,
    repo_root: Path,
    package_dir: Path,
    package_payload: dict[str, Any],
    package_hashes: dict[str, Any],
) -> dict[str, Any]:
    commit = _git(["rev-parse", "HEAD"])
    dirty = bool(_git(["status", "--short"]))
    lanes = []
    for lane in package_payload["send_set"]:
        lanes.append(
            {
                "gap": lane["gap"],
                "review_lane": lane["name"],
                "prompt": lane["prompt"],
                "attachment_manifest": lane["attachment_manifest"],
                "hash_manifest": lane["hash_manifest"],
                "raw_response_path": lane["raw_response_path"],
                "operator_sent": False,
                "operator_thread_url_or_message_id": "<operator fill in after send>",
            }
        )
    return {
        "record_type": "ithildin.enterprise_review_send_session_record",
        "format_version": "1",
        "commit": commit,
        "dirty": dirty,
        "tool_count": 24,
        "selected_capability": "not selected",
        "sent": False,
        "operator_fill_in": {
            "send_timestamp": "<operator fill in>",
            "operator_label": "<operator fill in>",
            "reviewer_or_model_label": "<operator fill in>",
            "channel": "<operator fill in>",
            "notes": "<operator fill in>",
        },
        "package": {
            "path": str(package_dir),
            "markdown": str(package_dir / enterprise_review_send_package.MARKDOWN_NAME),
            "json": str(package_dir / enterprise_review_send_package.JSON_NAME),
            "hash_manifest": str(package_dir / enterprise_review_send_package.HASH_NAME),
            "artifact_count": len(package_hashes.get("artifacts", [])),
        },
        "package_hash_evidence": package_hashes,
        "lanes": lanes,
        "boundary_flags": BOUNDARY_FLAGS,
        "next_commands_after_responses_arrive": [
            "make enterprise-dual-response-inbox",
            "make enterprise-response-waiting-room",
            "make enterprise-response-paste-preflight",
            "make enterprise-response-intake-refresh",
        ],
    }


def _ensure_package(repo_root: Path) -> Path:
    package_dir = repo_root / enterprise_review_send_package.DEFAULT_OUTPUT_DIR
    required = [
        package_dir / enterprise_review_send_package.MARKDOWN_NAME,
        package_dir / enterprise_review_send_package.JSON_NAME,
        package_dir / enterprise_review_send_package.HASH_NAME,
    ]
    if all(path.exists() for path in required):
        return enterprise_review_send_package.DEFAULT_OUTPUT_DIR
    return enterprise_review_send_package.build_package(
        repo_root, enterprise_review_send_package.DEFAULT_OUTPUT_DIR
    )


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Enterprise Review Send Session Record",
        "",
        "Status: generated non-authoritative send-session record scaffold.",
        "",
        f"Commit: `{payload['commit']}`",
        "",
        f"Dirty state when generated: `{str(payload['dirty']).lower()}`",
        "",
        f"Tool count: `{payload['tool_count']}`",
        "",
        f"sent: `{str(payload['sent']).lower()}`",
        "",
        "This record scaffold does not prove that a review request was sent. It gives",
        "the operator a single local place to copy send details after the human send",
        "step while preserving the current package, lane, and response-path evidence.",
        "",
        "## Operator fill-in fields",
        "",
    ]
    for field, value in payload["operator_fill_in"].items():
        lines.append(f"- {field}: `{value}`")
    lines.extend(
        [
            "",
            "## Package hash evidence",
            "",
            f"- package path: `{payload['package']['path']}`",
            f"- package markdown: `{payload['package']['markdown']}`",
            f"- package JSON: `{payload['package']['json']}`",
            f"- package hash manifest: `{payload['package']['hash_manifest']}`",
            f"- package artifact count: `{payload['package']['artifact_count']}`",
            "",
            "## Lane response landing pads",
            "",
            "| Gap | Review lane | Prompt | Raw response path | Sent |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for lane in payload["lanes"]:
        lines.append(
            "| `{gap}` | {review_lane} | `{prompt}` | `{raw_response_path}` | `{sent}` |".format(
                gap=lane["gap"],
                review_lane=lane["review_lane"],
                prompt=lane["prompt"],
                raw_response_path=lane["raw_response_path"],
                sent=str(lane["operator_sent"]).lower(),
            )
        )
    lines.extend(
        [
            "",
            "## Boundary flags",
            "",
        ]
    )
    for key, value in payload["boundary_flags"].items():
        lines.append(f"- {key}: `{str(value).lower()}`")
    lines.extend(
        [
            "",
            "This session record does not record external review, does not normalize",
            "responses, does not write response files, does not close `ERG-003` or",
            "`ERG-002`, and does not approve runtime behavior. It is local operator",
            "evidence only.",
            "",
            "## After responses arrive",
            "",
        ]
    )
    lines.extend(f"1. `{command}`" for command in payload["next_commands_after_responses_arrive"])
    lines.append("")
    return "\n".join(lines)


def _validate_repo_root(repo_root: Path) -> None:
    missing = [
        marker
        for marker in [
            "pyproject.toml",
            "Makefile",
            "scripts/enterprise_review_send_package.py",
            DOC_REL,
        ]
        if not (repo_root / marker).exists()
    ]
    if missing:
        raise EnterpriseReviewSendSessionRecordError(
            "missing required project marker(s): " + ", ".join(missing)
        )


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EnterpriseReviewSendSessionRecordError(f"missing JSON artifact: {path}") from exc
    except json.JSONDecodeError as exc:
        raise EnterpriseReviewSendSessionRecordError(f"invalid JSON artifact: {path}") from exc
    if not isinstance(payload, dict):
        raise EnterpriseReviewSendSessionRecordError(f"JSON artifact is not an object: {path}")
    return payload


def _artifact_hashes(output_dir: Path) -> dict[str, Any]:
    artifacts = []
    for path in sorted(output_dir.iterdir()):
        if not path.is_file() or path.name == HASH_NAME:
            continue
        data = path.read_bytes()
        artifacts.append(
            {
                "path": path.name,
                "sha256": "sha256:" + hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            }
        )
    return {
        "hash_manifest_type": "ithildin.enterprise_review_send_session_record_hashes",
        "format_version": "1",
        "artifacts": artifacts,
    }


def _artifact_hashes_match_files(output_dir: Path, hashes: dict[str, Any]) -> bool:
    for artifact in hashes.get("artifacts", []):
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
    failures: list[str], label: str, text: str, phrases: list[str]
) -> None:
    for phrase in phrases:
        if phrase not in text:
            failures.append(f"{label} is missing phrase: {phrase}")


def _git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


if __name__ == "__main__":
    raise SystemExit(main())

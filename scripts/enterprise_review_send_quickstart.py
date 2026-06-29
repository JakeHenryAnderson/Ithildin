"""Build a compact operator quickstart for sending current enterprise reviews."""

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
    enterprise_review_send_manifest,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-review-send-quickstart.md"
DOC_NAME = "enterprise-review-send-quickstart.md"
DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/enterprise-review-send-quickstart")
MARKDOWN_NAME = "ENTERPRISE_REVIEW_SEND_QUICKSTART.md"
JSON_NAME = "enterprise-review-send-quickstart.json"
HASH_NAME = "enterprise-review-send-quickstart-artifact-hashes.json"
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


class EnterpriseReviewSendQuickstartError(RuntimeError):
    """Raised when the enterprise send quickstart cannot be built."""


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
        output_dir = build_quickstart(ROOT, args.output_dir)
    except EnterpriseReviewSendQuickstartError as exc:
        print(f"enterprise review send quickstart failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built enterprise review send quickstart at {output_dir}")
    return 0


def build_quickstart(repo_root: Path, output_dir: Path) -> Path:
    _validate_repo_root(repo_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    outbox_dir = enterprise_dual_review_outbox.build_outbox(
        repo_root,
        enterprise_dual_review_outbox.DEFAULT_OUTPUT_DIR,
    )
    manifest_dir = enterprise_review_send_manifest.build_manifest(
        repo_root,
        enterprise_review_send_manifest.DEFAULT_OUTPUT_DIR,
    )
    status = enterprise_response_status_board.build_report(repo_root)
    if status.get("valid") is not True:
        raise EnterpriseReviewSendQuickstartError(
            "enterprise response status board is not valid"
        )
    payload = _quickstart_payload(repo_root, outbox_dir, manifest_dir, status)
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
        output_dir = build_quickstart(repo_root, DEFAULT_OUTPUT_DIR)
    except EnterpriseReviewSendQuickstartError as exc:
        failures.append(str(exc))
        output_dir = DEFAULT_OUTPUT_DIR

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    operator_next_action = _read(repo_root / "docs/codex/enterprise-operator-next-action.md")
    send_checklist = _read(repo_root / "docs/codex/enterprise-review-send-checklist.md")
    submission_prompt = _read(repo_root / "docs/codex/enterprise-review-submission-prompt.md")
    quickstart_doc = _read(repo_root / DOC_REL)
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition(
        "\n\n"
    )[0]
    refresh_body = makefile.partition("enterprise-review-send-refresh:")[2].partition(
        "\n\n"
    )[0]
    generated_text = _read(output_dir / MARKDOWN_NAME)
    generated_json_text = _read(output_dir / JSON_NAME)
    hash_text = _read(output_dir / HASH_NAME)
    try:
        hashes = json.loads(hash_text) if hash_text else {"artifacts": []}
    except json.JSONDecodeError:
        hashes = {"artifacts": []}
        failures.append("enterprise review send quickstart hashes are not valid JSON")
    hashed_paths = {artifact.get("path") for artifact in hashes.get("artifacts", [])}

    _require_phrases(
        failures,
        "send quickstart doc",
        quickstart_doc,
        [
            "Status: generated operator quickstart for the current enterprise send set.",
            "make enterprise-review-send-quickstart",
            "make enterprise-review-send-quickstart-check",
            "`ERG-003`",
            "`ERG-002`",
            "does not record external review",
            "does not normalize responses",
            "does not close `ERG-003` or `ERG-002`",
        ],
    )
    _require_phrases(
        failures,
        "generated send quickstart",
        generated_text,
        [
            "Enterprise Review Send Quickstart",
            "Send these two review requests",
            "ERG-003",
            "ERG-002",
            "Attach every file from",
            "Prompt file",
            "Attachment manifest",
            "Hash manifest",
            "After responses arrive",
            "RAW_RESPONSE_ERG-003.md",
            "RAW_RESPONSE_ERG-002.md",
            "records_external_review: `false`",
            "normalizes_responses: `false`",
            "closes_erg_003: `false`",
            "closes_erg_002: `false`",
        ],
    )
    _require_phrases(
        failures,
        "generated send quickstart JSON",
        generated_json_text,
        [
            '"quickstart_type": "ithildin.enterprise_review_send_quickstart"',
            '"ERG-003"',
            '"ERG-002"',
            '"records_external_review": false',
            '"normalizes_responses": false',
            '"closes_erg_003": false',
            '"closes_erg_002": false',
        ],
    )
    if {MARKDOWN_NAME, JSON_NAME} - hashed_paths:
        failures.append("quickstart hash manifest is missing generated artifacts")
    if HASH_NAME in hashed_paths:
        failures.append("quickstart hash manifest must not hash itself")
    if not _artifact_hashes_match_files(output_dir, hashes):
        failures.append("quickstart artifact hashes do not match files")

    wiring_checks = {
        "Make target": ("enterprise-review-send-quickstart:", makefile),
        "Check target": ("enterprise-review-send-quickstart-check:", makefile),
        "Release check": ("enterprise-review-send-quickstart-check", release_check_body),
        "Review candidate": ("$(MAKE) enterprise-review-send-quickstart", review_candidate_body),
        "Send refresh": ("$(MAKE) enterprise-review-send-quickstart", refresh_body),
        "README command": ("make enterprise-review-send-quickstart", readme),
        "Docs site": (DOC_REL, docs_site),
        "Review docs": (DOC_REL, "\n".join(review_docs.REVIEW_DOCS)),
        "Review index": (DOC_NAME, review_index),
        "Release guardrails": ("enterprise-review-send-quickstart-check", release_guardrails),
        "Operator next action": ("enterprise-review-send-quickstart", operator_next_action),
        "Send checklist": ("enterprise-review-send-quickstart", send_checklist),
        "Submission prompt": ("enterprise-review-send-quickstart", submission_prompt),
    }
    for label, (needle, haystack) in wiring_checks.items():
        if needle not in haystack:
            failures.append(f"{label} is missing {needle}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "quickstart_doc": DOC_REL,
        "output_dir": output_dir.as_posix(),
        "recommended_gaps": RECOMMENDED_GAPS,
        "tool_count": 24,
        "artifact_hashes_match_files": _artifact_hashes_match_files(output_dir, hashes),
        **BOUNDARY_FLAGS,
    }


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise review send quickstart check",
        f"valid: {str(report['valid']).lower()}",
        f"quickstart_doc: {report['quickstart_doc']}",
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


def _quickstart_payload(
    repo_root: Path,
    outbox_dir: Path,
    manifest_dir: Path,
    status: dict[str, Any],
) -> dict[str, Any]:
    return {
        "quickstart_type": "ithildin.enterprise_review_send_quickstart",
        "schema_version": "1",
        "commit": _git(repo_root, ["rev-parse", "HEAD"]),
        "dirty": bool(_git(repo_root, ["status", "--short"])),
        "tool_count": 24,
        "selected_capability": "not selected",
        "recommended_gaps": RECOMMENDED_GAPS,
        "response_present_count": status.get("response_present_count"),
        "closure_ready_count": status.get("closure_ready_count"),
        "send_requests": [
            {
                "lane": "ERG-003",
                "title": "Sandbox/VM static preflight disposition",
                "attach_directory": (outbox_dir / "ERG-003").as_posix(),
                "prompt_file": "01_SANDBOX_VM_STATIC_PREFLIGHT_EXTERNAL_REVIEW_PROMPT.md",
                "attachment_manifest": "ATTACHMENT_MANIFEST.md",
                "hash_manifest": (
                    "sandbox-vm-static-preflight-external-review-artifact-hashes.json"
                ),
                "raw_response_path": (
                    "var/review-runs/enterprise-dual-response-inbox/"
                    "RAW_RESPONSE_ERG-003.md"
                ),
            },
            {
                "lane": "ERG-002",
                "title": "Mission Control display/import planning review",
                "attach_directory": (outbox_dir / "ERG-002").as_posix(),
                "prompt_file": "01_MISSION_CONTROL_DISPLAY_EXTERNAL_REVIEW_PROMPT.md",
                "attachment_manifest": "ATTACHMENT_MANIFEST.md",
                "hash_manifest": "mission-control-display-external-review-artifact-hashes.json",
                "raw_response_path": (
                    "var/review-runs/enterprise-dual-response-inbox/"
                    "RAW_RESPONSE_ERG-002.md"
                ),
            },
        ],
        "companion_artifacts": {
            "dual_review_outbox": outbox_dir.as_posix(),
            "send_manifest": manifest_dir.as_posix(),
            "submission_prompt": (
                "var/review-packets/v3/enterprise-review-submission-prompt"
            ),
            "send_receipt_template": (
                "var/review-packets/v3/enterprise-review-send-receipt-template"
            ),
            "dual_response_inbox": "var/review-runs/enterprise-dual-response-inbox",
        },
        "post_response_commands": [
            "make enterprise-review-send-receipt-template",
            "make enterprise-dual-response-inbox",
            "make enterprise-response-paste-preflight",
            "make enterprise-response-intake-refresh",
        ],
        "blocked_boundaries": dict(BOUNDARY_FLAGS),
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Enterprise Review Send Quickstart",
        "",
        "Status: generated operator quickstart for the current enterprise send set.",
        "",
        f"Commit: `{payload['commit']}`",
        f"Dirty state: `{str(payload['dirty']).lower()}`",
        f"Tool count: `{payload['tool_count']}`",
        "Recommended send set: `ERG-003`, `ERG-002`",
        "",
        "## Send these two review requests",
        "",
    ]
    for request in payload["send_requests"]:
        lines.extend(
            [
                f"### {request['lane']}: {request['title']}",
                "",
                f"- Attach every file from: `{request['attach_directory']}`",
                f"- Prompt file: `{request['prompt_file']}`",
                f"- Attachment manifest: `{request['attachment_manifest']}`",
                f"- Hash manifest: `{request['hash_manifest']}`",
                f"- Raw response placeholder: `{request['raw_response_path']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Companion operator artifacts",
            "",
        ]
    )
    for label, path in payload["companion_artifacts"].items():
        lines.append(f"- `{label}`: `{path}`")
    lines.extend(
        [
            "",
            "## After responses arrive",
            "",
        ]
    )
    lines.extend(f"1. `{command}`" for command in payload["post_response_commands"])
    lines.extend(
        [
            "",
            "## Boundary flags",
            "",
        ]
    )
    for key, value in payload["blocked_boundaries"].items():
        lines.append(f"- {key}: `{str(value).lower()}`")
    lines.extend(
        [
            "",
            "This quickstart does not record external review, does not normalize responses, "
            "does not write response files, and does not close `ERG-003` or `ERG-002`.",
            "",
        ]
    )
    return "\n".join(lines)


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


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


def _validate_repo_root(repo_root: Path) -> None:
    for marker in ["pyproject.toml", "Makefile", "tool-manifests.lock.json"]:
        if not (repo_root / marker).exists():
            raise EnterpriseReviewSendQuickstartError(
                f"repo root is missing required marker: {marker}"
            )


if __name__ == "__main__":
    raise SystemExit(main())

"""Build an operator drill for the enterprise review handoff loop."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    enterprise_dual_response_inbox,
    enterprise_dual_review_outbox,
    enterprise_response_intake_drill,
    enterprise_response_status_board,
    enterprise_review_send_manifest,
    enterprise_review_send_readiness,
    enterprise_review_send_receipt_template,
    enterprise_review_submission_prompt,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-review-handoff-drill.md"
DOC_NAME = "enterprise-review-handoff-drill.md"
DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/enterprise-review-handoff-drill")
MARKDOWN_NAME = "ENTERPRISE_REVIEW_HANDOFF_DRILL.md"
JSON_NAME = "enterprise-review-handoff-drill.json"
HASH_NAME = "enterprise-review-handoff-drill-artifact-hashes.json"
RECOMMENDED_GAPS = ["ERG-003", "ERG-002"]
ACTIVE_SEND_SET = ["ERG-006", "ERG-007"]
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
    "records_external_review": False,
    "normalizes_real_responses": False,
    "closes_enterprise_lanes": False,
}


class EnterpriseReviewHandoffDrillError(RuntimeError):
    """Raised when the handoff drill cannot be built or validated."""


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
        output_dir = build_drill(ROOT, args.output_dir)
    except EnterpriseReviewHandoffDrillError as exc:
        print(f"enterprise review handoff drill failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built enterprise review handoff drill at {output_dir}")
    return 0


def build_drill(repo_root: Path, output_dir: Path) -> Path:
    _validate_repo_root(repo_root)
    send_readiness = enterprise_review_send_readiness.build_report(repo_root)
    status_board = enterprise_response_status_board.build_report(repo_root)
    intake_drill = enterprise_response_intake_drill.build_report(repo_root)
    if send_readiness.get("valid") is not True:
        raise EnterpriseReviewHandoffDrillError("enterprise send-readiness is not valid")
    if status_board.get("valid") is not True:
        raise EnterpriseReviewHandoffDrillError("enterprise response status board is not valid")
    if intake_drill.get("valid") is not True:
        raise EnterpriseReviewHandoffDrillError("enterprise response intake drill is not valid")

    outbox_dir = enterprise_dual_review_outbox.build_outbox(
        repo_root, enterprise_dual_review_outbox.DEFAULT_OUTPUT_DIR
    )
    manifest_dir = enterprise_review_send_manifest.build_manifest(
        repo_root, enterprise_review_send_manifest.DEFAULT_OUTPUT_DIR
    )
    submission_prompt_dir = enterprise_review_submission_prompt.build_prompt(
        repo_root, enterprise_review_submission_prompt.DEFAULT_OUTPUT_DIR
    )
    receipt_template_dir = enterprise_review_send_receipt_template.build_template(
        repo_root, enterprise_review_send_receipt_template.DEFAULT_OUTPUT_DIR
    )
    inbox_dir = enterprise_dual_response_inbox.build_inbox(
        repo_root, enterprise_dual_response_inbox.DEFAULT_OUTPUT_DIR
    )
    outbox_payload = _read_json(outbox_dir / enterprise_dual_review_outbox.JSON_NAME)
    manifest_payload = _read_json(manifest_dir / enterprise_review_send_manifest.JSON_NAME)
    inbox_payload = _read_json(inbox_dir / enterprise_dual_response_inbox.JSON_NAME)

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    payload = _drill_payload(
        repo_root=repo_root,
        send_readiness=send_readiness,
        status_board=status_board,
        intake_drill=intake_drill,
        outbox_dir=outbox_dir,
        manifest_dir=manifest_dir,
        submission_prompt_dir=submission_prompt_dir,
        receipt_template_dir=receipt_template_dir,
        inbox_dir=inbox_dir,
        outbox_payload=outbox_payload,
        manifest_payload=manifest_payload,
        inbox_payload=inbox_payload,
    )
    (output_dir / MARKDOWN_NAME).write_text(_render_markdown(payload), encoding="utf-8")
    (output_dir / JSON_NAME).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / HASH_NAME).write_text(
        json.dumps(_artifact_hashes(output_dir), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_dir


def build_check_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    try:
        output_dir = build_drill(repo_root, DEFAULT_OUTPUT_DIR)
    except EnterpriseReviewHandoffDrillError as exc:
        failures.append(str(exc))
        output_dir = DEFAULT_OUTPUT_DIR

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    queue_doc = _read(repo_root / "docs/codex/enterprise-external-review-queue.md")
    send_manifest_doc = _read(repo_root / "docs/codex/enterprise-review-send-manifest.md")
    response_board_doc = _read(repo_root / "docs/codex/enterprise-response-status-board.md")
    drill_doc = _read(repo_root / DOC_REL)
    markdown_text = _read(output_dir / MARKDOWN_NAME)
    json_text = _read(output_dir / JSON_NAME)
    hash_text = _read(output_dir / HASH_NAME)
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    try:
        hash_manifest = json.loads(hash_text) if hash_text else {"artifacts": []}
    except json.JSONDecodeError:
        hash_manifest = {"artifacts": []}
        failures.append("enterprise review handoff drill hashes are not valid JSON")

    normalized_markdown_text = " ".join(markdown_text.split())
    for phrase in [
        "Status: generated operator drill for enterprise review send/receive readiness.",
        "make enterprise-review-handoff-drill",
        "make enterprise-review-handoff-drill-check",
        "`ERG-003`",
        "`ERG-002`",
        "does not record external review",
        "does not normalize real responses",
        "does not close any enterprise lane",
    ]:
        if phrase not in drill_doc:
            failures.append(f"enterprise review handoff drill doc missing phrase: {phrase}")
    for phrase in [
        "Enterprise Review Handoff Drill",
        "Historical Dual-Send Set",
        "Active enterprise route: preparation of the `PIS-002` entry decision record after the "
        "cleared `PIS-001` exact-candidate review; `ERG-006`/`ERG-007` remain planning-only scope.",
        "ERG-003",
        "ERG-002",
        "Operator sequence",
        "make enterprise-review-submission-prompt",
        "make enterprise-review-send-receipt-template",
        "make enterprise-review-send-receipt-validate RECEIPT=path/to/copied-receipt.json",
        "Response landing pads",
        "var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-003.md",
        "var/review-runs/enterprise-dual-response-inbox/RAW_RESPONSE_ERG-002.md",
        "make enterprise-response-paste-preflight",
        "records_external_review: `false`",
        "normalizes_real_responses: `false`",
        "closes_enterprise_lanes: `false`",
    ]:
        if " ".join(phrase.split()) not in normalized_markdown_text:
            failures.append(f"generated handoff drill is missing phrase: {phrase}")
    for phrase in [
        '"drill_type": "ithildin.enterprise_review_handoff_drill"',
        '"ERG-003"',
        '"ERG-002"',
        '"send_ready": true',
        '"intake_drill_valid": true',
        '"submission_prompt_dir":',
        '"receipt_template_dir":',
        '"response_inbox_dir": "var/review-runs/enterprise-dual-response-inbox"',
        '"make enterprise-response-paste-preflight"',
        '"records_external_review": false',
        '"normalizes_real_responses": false',
        '"closes_enterprise_lanes": false',
    ]:
        if phrase not in json_text:
            failures.append(f"generated handoff drill JSON is missing phrase: {phrase}")

    hashed_paths = {artifact.get("path") for artifact in hash_manifest.get("artifacts", [])}
    expected_hashes = {MARKDOWN_NAME, JSON_NAME}
    if not expected_hashes.issubset(hashed_paths):
        failures.append("handoff drill hash file is missing generated artifacts")
    if HASH_NAME in hashed_paths:
        failures.append("handoff drill hash file must not hash itself")
    if not _artifact_hashes_match_files(output_dir, hash_manifest):
        failures.append("handoff drill artifact hashes do not match files")

    if "enterprise-review-handoff-drill:" not in makefile:
        failures.append("Make target is missing: enterprise-review-handoff-drill")
    if "enterprise-review-handoff-drill-check:" not in makefile:
        failures.append("Make target is missing: enterprise-review-handoff-drill-check")
    if (
        "enterprise-review-handoff-drill-check" not in release_check_body
        and "release-check: enterprise-review-handoff-drill-check" not in makefile
    ):
        failures.append("enterprise-review-handoff-drill-check is missing from release-check")
    if "$(MAKE) enterprise-review-handoff-drill" not in review_candidate_body:
        failures.append("enterprise-review-handoff-drill is missing from review-candidate")
    if "make enterprise-review-handoff-drill" not in readme:
        failures.append("README is missing enterprise review handoff drill command")
    if DOC_REL not in docs_site:
        failures.append("enterprise review handoff drill doc is missing from docs site")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("enterprise review handoff drill doc is missing from review docs")
    if DOC_NAME not in review_index:
        failures.append("review-docs index is missing enterprise review handoff drill")
    if "enterprise-review-handoff-drill-check" not in release_guardrails:
        failures.append("release guardrails do not require enterprise review handoff drill")
    if "$(MAKE) enterprise-review-handoff-drill" not in release_guardrails:
        failures.append("release guardrails do not require handoff drill generation")
    if "enterprise-review-handoff-drill" not in queue_doc:
        failures.append("enterprise queue is missing handoff drill pointer")
    if "enterprise-review-handoff-drill" not in send_manifest_doc:
        failures.append("send manifest doc is missing handoff drill pointer")
    if "enterprise-review-handoff-drill" not in response_board_doc:
        failures.append("response status board doc is missing handoff drill pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "drill_doc": DOC_REL,
        "output_dir": output_dir.as_posix(),
        "recommended_gaps": RECOMMENDED_GAPS,
        "legacy_recommended_gaps": RECOMMENDED_GAPS,
        "active_send_set": ACTIVE_SEND_SET,
        "route_scope": "historical_dual_send_handoff_drill",
        "legacy_route_scope": "historical_dual_send_handoff_drill",
        "tool_count": 24,
        "artifact_hashes_match_files": _artifact_hashes_match_files(output_dir, hash_manifest),
        **BOUNDARY_FLAGS,
    }


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise review handoff drill check",
        f"valid: {str(report['valid']).lower()}",
        f"drill_doc: {report['drill_doc']}",
        f"output_dir: {report['output_dir']}",
        f"legacy_route_scope: {report['legacy_route_scope']}",
        "active_send_set: " + ", ".join(report["active_send_set"]),
        "legacy_recommended_gaps: " + ", ".join(report["legacy_recommended_gaps"]),
        f"tool_count: {report['tool_count']}",
        f"artifact_hashes_match_files: {str(report['artifact_hashes_match_files']).lower()}",
    ]
    lines.extend(f"{key}: {str(value).lower()}" for key, value in BOUNDARY_FLAGS.items())
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _drill_payload(
    *,
    repo_root: Path,
    send_readiness: dict[str, Any],
    status_board: dict[str, Any],
    intake_drill: dict[str, Any],
    outbox_dir: Path,
    manifest_dir: Path,
    submission_prompt_dir: Path,
    receipt_template_dir: Path,
    inbox_dir: Path,
    outbox_payload: dict[str, Any],
    manifest_payload: dict[str, Any],
    inbox_payload: dict[str, Any],
) -> dict[str, Any]:
    send_set = []
    inbox_by_gap = {lane["gap"]: lane for lane in inbox_payload["lanes"]}
    for packet in manifest_payload["send_set"]:
        inbox_lane = inbox_by_gap[packet["gap"]]
        raw_response_file = f"{_repo_rel(repo_root, inbox_dir)}/{inbox_lane['raw_response_file']}"
        send_set.append(
            {
                "gap": packet["gap"],
                "name": packet["name"],
                "finding_namespace": packet["finding_namespace"],
                "prompt": packet["prompt"],
                "attachment_count": packet["copied_file_count"],
                "outbox_dir": f"{manifest_payload['outbox_dir']}/{packet['outbox_dir']}",
                "raw_response_file": raw_response_file,
                "response_kit": packet["response_kit"],
                "intake_doc": packet["intake_doc"],
                "dry_run": packet["dry_run"],
                "closure_gate": packet["closure_gate"],
            }
        )
    return {
        "schema_version": "1",
        "drill_type": "ithildin.enterprise_review_handoff_drill",
        "commit": _git(repo_root, ["rev-parse", "HEAD"]),
        "dirty": bool(_git(repo_root, ["status", "--short"])),
        "tool_count": 24,
        "selected_capability": "not selected",
        "route_scope": "historical_dual_send_handoff_drill",
        "active_send_set": ACTIVE_SEND_SET,
        "recommended_gaps": RECOMMENDED_GAPS,
        "send_ready": send_readiness.get("valid") is True
        and send_readiness.get("recommended_now") == RECOMMENDED_GAPS,
        "response_present_count": status_board.get("response_present_count"),
        "closure_ready_count": status_board.get("closure_ready_count"),
        "intake_drill_valid": intake_drill.get("valid") is True,
        "intake_drill_dry_run_count": intake_drill.get("dry_run_count"),
        "outbox_dir": _repo_rel(repo_root, outbox_dir),
        "outbox_hash_manifest": _repo_rel(
            repo_root, outbox_dir / enterprise_dual_review_outbox.HASH_NAME
        ),
        "send_manifest_dir": _repo_rel(repo_root, manifest_dir),
        "submission_prompt_dir": _repo_rel(repo_root, submission_prompt_dir),
        "receipt_template_dir": _repo_rel(repo_root, receipt_template_dir),
        "response_inbox_dir": _repo_rel(repo_root, inbox_dir),
        "response_inbox_hash_manifest": _repo_rel(
            repo_root, inbox_dir / enterprise_dual_response_inbox.HASH_NAME
        ),
        "send_set": send_set,
        "operator_sequence": [
            "make enterprise-dual-review-outbox",
            "make enterprise-review-send-manifest",
            "make enterprise-review-submission-prompt",
            "make enterprise-review-send-receipt-template",
            "make enterprise-review-send-receipt-validate RECEIPT=path/to/copied-receipt.json",
            "send ERG-003 and ERG-002 attachment sets to reviewers",
            "make enterprise-dual-response-inbox",
            "paste raw responses into the lane raw-response files",
            "make enterprise-response-paste-preflight",
            "run the lane-specific response dry run",
            "run the lane-specific closure gate",
            "commit any later response-application record only after the closure gate is favorable",
        ],
        "blocked_boundaries": BOUNDARY_FLAGS,
        "outbox_artifact_count": outbox_payload.get("copied_packet_count")
        or len(outbox_payload.get("packets", [])),
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    send_rows = "\n".join(
        (
            f"| `{packet['gap']}` | {packet['name']} | `{packet['prompt']}` | "
            f"`{packet['attachment_count']}` | `{packet['finding_namespace']}` |"
        )
        for packet in payload["send_set"]
    )
    response_rows = "\n".join(
        (
            f"| `{packet['gap']}` | `{packet['raw_response_file']}` | "
            f"`{packet['response_kit']}` | `{packet['dry_run']}` | `{packet['closure_gate']}` |"
        )
        for packet in payload["send_set"]
    )
    sequence = "\n".join(
        f"{index}. {step}" for index, step in enumerate(payload["operator_sequence"], 1)
    )
    blocked = "\n".join(
        f"- {key}: `{str(value).lower()}`" for key, value in payload["blocked_boundaries"].items()
    )
    return f"""# Enterprise Review Handoff Drill

Status: generated operator drill for enterprise review send/receive readiness.

Reviewed commit: `{payload["commit"]}`

Dirty state when generated: `{str(payload["dirty"]).lower()}`

Tool count remains `24`.

Current selected capability: `not selected`.

Route scope: historical `ERG-003`/`ERG-002` dual-send handoff drill.

Active enterprise route: preparation of the `PIS-002` entry decision record after the cleared
`PIS-001` exact-candidate review; `ERG-006`/`ERG-007` remain planning-only scope.

This drill ties together the historical send-ready outbox, send manifest, submission prompt, send
receipt template, response inbox, response status board, and fixture-only intake drill. It does not
record external review, does not normalize real responses, and does not close any enterprise lane.

## Historical Dual-Send Set

| Gap | Review lane | Prompt | Attachment count | Finding namespace |
| --- | --- | --- | ---: | --- |
{send_rows}

Outbox root: `{payload["outbox_dir"]}`

Outbox hash manifest: `{payload["outbox_hash_manifest"]}`

Send manifest root: `{payload["send_manifest_dir"]}`

Submission prompt root: `{payload["submission_prompt_dir"]}`

Send receipt template root: `{payload["receipt_template_dir"]}`

## Operator sequence

{sequence}

## Response landing pads

| Gap | Raw response file | Response kit | Dry run | Closure gate |
| --- | --- | --- | --- | --- |
{response_rows}

Response inbox root: `{payload["response_inbox_dir"]}`

Response inbox hash manifest: `{payload["response_inbox_hash_manifest"]}`

## Current waiting state

- send_ready: `{str(payload["send_ready"]).lower()}`
- intake_drill_valid: `{str(payload["intake_drill_valid"]).lower()}`
- response_present_count: `{payload["response_present_count"]}`
- closure_ready_count: `{payload["closure_ready_count"]}`

## Blocked boundaries

{blocked}
"""


def _validate_repo_root(repo_root: Path) -> None:
    missing = [
        marker
        for marker in ["pyproject.toml", "Makefile", "tool-manifests.lock.json"]
        if not (repo_root / marker).exists()
    ]
    if missing:
        raise EnterpriseReviewHandoffDrillError(
            "must be run from the Ithildin repo root; missing " + ", ".join(missing)
        )


def _read_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


def _repo_rel(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


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


if __name__ == "__main__":
    raise SystemExit(main())

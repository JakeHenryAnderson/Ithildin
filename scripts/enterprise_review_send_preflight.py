"""Validate the final operator preflight for the current enterprise review send."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, TypedDict

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    enterprise_dual_response_readiness,
    enterprise_handoff_consistency_check,
    enterprise_operator_next_action,
    enterprise_response_status_board,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-review-send-preflight.md"
DOC_TITLE = "Enterprise Review Send Preflight"
CURRENT_SEND_SET = ["ERG-003", "ERG-002"]
EXPECTED_ACTION = "send_erg_003_and_erg_002"
BOUNDARY_FLAGS = {
    "records_external_review": False,
    "normalizes_responses": False,
    "writes_response_files": False,
    "closes_erg_003": False,
    "closes_erg_002": False,
    "runtime_changes_allowed": False,
    "mission_control_runtime_allowed": False,
    "live_vm_inspection_allowed": False,
    "sandbox_orchestration_allowed": False,
    "trusted_host_promotion_allowed": False,
    "siem_adapter_allowed": False,
    "compliance_automation_allowed": False,
    "public_security_product_positioning_allowed": False,
    "new_power_classes_allowed": False,
}

class ArtifactSpec(TypedDict):
    output_dir: str
    hash_file: str
    payload_file: str
    required_files: list[str]


EXPECTED_ARTIFACTS: dict[str, ArtifactSpec] = {
    "dual_review_outbox": {
        "output_dir": "var/review-packets/v3/enterprise-dual-review-outbox",
        "hash_file": "enterprise-dual-review-outbox-artifact-hashes.json",
        "payload_file": "enterprise-dual-review-outbox.json",
        "required_files": [
            "ENTERPRISE_DUAL_REVIEW_OUTBOX_INDEX.md",
            "enterprise-dual-review-outbox.json",
            "ERG-003/01_SANDBOX_VM_STATIC_PREFLIGHT_EXTERNAL_REVIEW_PROMPT.md",
            "ERG-002/01_MISSION_CONTROL_DISPLAY_EXTERNAL_REVIEW_PROMPT.md",
        ],
    },
    "send_manifest": {
        "output_dir": "var/review-packets/v3/enterprise-review-send-manifest",
        "hash_file": "enterprise-review-send-manifest-artifact-hashes.json",
        "payload_file": "enterprise-review-send-manifest.json",
        "required_files": [
            "ENTERPRISE_REVIEW_SEND_MANIFEST.md",
            "enterprise-review-send-manifest.json",
        ],
    },
    "send_quickstart": {
        "output_dir": "var/review-packets/v3/enterprise-review-send-quickstart",
        "hash_file": "enterprise-review-send-quickstart-artifact-hashes.json",
        "payload_file": "enterprise-review-send-quickstart.json",
        "required_files": [
            "ENTERPRISE_REVIEW_SEND_QUICKSTART.md",
            "enterprise-review-send-quickstart.json",
        ],
    },
    "submission_prompt": {
        "output_dir": "var/review-packets/v3/enterprise-review-submission-prompt",
        "hash_file": "enterprise-review-submission-prompt-artifact-hashes.json",
        "payload_file": "enterprise-review-submission-prompt.json",
        "required_files": [
            "ENTERPRISE_REVIEW_SUBMISSION_PROMPT.md",
            "enterprise-review-submission-prompt.json",
        ],
    },
    "send_receipt_template": {
        "output_dir": "var/review-packets/v3/enterprise-review-send-receipt-template",
        "hash_file": "enterprise-review-send-receipt-template-artifact-hashes.json",
        "payload_file": "enterprise-review-send-receipt-template.json",
        "required_files": [
            "ENTERPRISE_REVIEW_SEND_RECEIPT_TEMPLATE.md",
            "enterprise-review-send-receipt-template.json",
        ],
    },
    "send_package": {
        "output_dir": "var/review-packets/v3/enterprise-review-send-package",
        "hash_file": "enterprise-review-send-package-artifact-hashes.json",
        "payload_file": "enterprise-review-send-package.json",
        "required_files": [
            "ENTERPRISE_REVIEW_SEND_PACKAGE.md",
            "enterprise-review-send-package.json",
        ],
    },
    "send_session_record": {
        "output_dir": "var/review-runs/enterprise-review-send-session-record",
        "hash_file": "enterprise-review-send-session-record-artifact-hashes.json",
        "payload_file": "enterprise-review-send-session-record.json",
        "required_files": [
            "ENTERPRISE_REVIEW_SEND_SESSION_RECORD.md",
            "enterprise-review-send-session-record.json",
        ],
    },
    "dual_response_inbox": {
        "output_dir": "var/review-runs/enterprise-dual-response-inbox",
        "hash_file": "enterprise-dual-response-inbox-artifact-hashes.json",
        "payload_file": "enterprise-dual-response-inbox.json",
        "required_files": [
            "ENTERPRISE_DUAL_RESPONSE_INBOX.md",
            "ENTERPRISE_DUAL_RESPONSE_CHEATSHEET.md",
            "enterprise-dual-response-inbox.json",
            "RAW_RESPONSE_ERG-003.md",
            "RAW_RESPONSE_ERG-002.md",
        ],
    },
    "handoff_drill": {
        "output_dir": "var/review-packets/v3/enterprise-review-handoff-drill",
        "hash_file": "enterprise-review-handoff-drill-artifact-hashes.json",
        "payload_file": "enterprise-review-handoff-drill.json",
        "required_files": [
            "ENTERPRISE_REVIEW_HANDOFF_DRILL.md",
            "enterprise-review-handoff-drill.json",
        ],
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = build_report(ROOT)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    current_commit = _git(repo_root, ["rev-parse", "HEAD"])
    current_dirty = bool(_git(repo_root, ["status", "--short"]))

    operator_next = enterprise_operator_next_action.build_report(repo_root)
    response_status = enterprise_response_status_board.build_report(repo_root)
    dual_response = enterprise_dual_response_readiness.build_report(repo_root)
    handoff_consistency = enterprise_handoff_consistency_check.build_report(repo_root)

    state_reports = {
        "operator_next_action": operator_next,
        "dual_response_readiness": dual_response,
        "response_status_board": response_status,
        "handoff_consistency": handoff_consistency,
    }
    for name, report in state_reports.items():
        if report.get("valid") is not True:
            failures.append(f"{name} is not valid")
            failures.extend(f"{name}: {failure}" for failure in report.get("failures", []))

    if operator_next.get("next_action") != EXPECTED_ACTION:
        failures.append("operator next action is not the expected send flow")
    if operator_next.get("recommended_send_set") != CURRENT_SEND_SET:
        failures.append("operator next-action send set is not ERG-003 then ERG-002")
    if handoff_consistency.get("current_send_set") != CURRENT_SEND_SET:
        failures.append("handoff consistency current send set drifted")
    if response_status.get("response_present_count") != 0:
        failures.append("response evidence is present; use response-intake flow instead")
    if response_status.get("closure_ready_count") != 0:
        failures.append("closure-ready evidence is present; use lane closure flow instead")
    if dual_response.get("response_present_count") != 0:
        failures.append("dual-response readiness reports responses present")
    if dual_response.get("closure_ready_count") != 0:
        failures.append("dual-response readiness reports closure-ready evidence")

    artifact_reports = _artifact_reports(
        repo_root,
        current_commit=current_commit,
        current_dirty=current_dirty,
    )
    for name, artifact_report in artifact_reports.items():
        if not artifact_report["valid"]:
            failures.append(f"{name} generated artifacts are not ready")
            failures.extend(
                f"{name}: {failure}" for failure in artifact_report["failures"]
            )

    component_outputs = {
        name: artifact_report["output_dir"]
        for name, artifact_report in artifact_reports.items()
    }

    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition(
        "\n\n"
    )[0]

    for phrase in [
        "Status: checked final operator preflight for the current enterprise review send.",
        "make enterprise-review-send-preflight",
        "ERG-003",
        "ERG-002",
        "make enterprise-review-send-checklist",
        "make enterprise-review-send-quickstart",
        "make enterprise-review-submission-prompt",
        "make enterprise-review-send-receipt-template",
        "make enterprise-review-send-package",
        "make enterprise-review-send-session-record",
        "make enterprise-dual-response-inbox",
        "make enterprise-handoff-consistency-check",
        "does not record external review",
        "does not normalize responses",
        "does not close `ERG-003` or `ERG-002`",
    ]:
        if phrase not in doc:
            failures.append(f"enterprise review send preflight doc is missing phrase: {phrase}")

    wiring_checks = {
        "Make target": ("enterprise-review-send-preflight:", makefile),
        "Release check": ("enterprise-review-send-preflight", release_check_body + makefile),
        "Review candidate": ("$(MAKE) enterprise-review-send-preflight", review_candidate_body),
        "README command": ("make enterprise-review-send-preflight", readme),
        "README doc": (DOC_REL, readme),
        "Docs site": (DOC_REL, docs_site),
        "Review docs": (DOC_REL, "\n".join(review_docs.REVIEW_DOCS)),
        "Review index": (DOC_TITLE, review_index),
        "Release guardrails": ("enterprise-review-send-preflight", release_guardrails),
    }
    for label, (needle, haystack) in wiring_checks.items():
        if needle not in haystack:
            failures.append(f"{label} is missing {needle}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "preflight_doc": DOC_REL,
        "tool_count": 24,
        "selected_capability": "not selected",
        "current_send_set": CURRENT_SEND_SET,
        "expected_action": EXPECTED_ACTION,
        "current_commit": current_commit,
        "current_dirty": current_dirty,
        "response_present_count": response_status.get("response_present_count"),
        "closure_ready_count": response_status.get("closure_ready_count"),
        "component_validity": {
            **{name: report.get("valid") is True for name, report in state_reports.items()},
            **{name: report["valid"] for name, report in artifact_reports.items()},
        },
        "component_outputs": component_outputs,
        "artifact_hashes_match_files": all(
            report["artifact_hashes_match_files"] for report in artifact_reports.values()
        ),
        "artifact_commits_match_current": all(
            report["commit_matches_current"] for report in artifact_reports.values()
        ),
        "artifact_payloads_clean": all(
            report["payload_dirty"] is False for report in artifact_reports.values()
        ),
        **BOUNDARY_FLAGS,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise review send preflight",
        f"valid: {str(report['valid']).lower()}",
        f"preflight_doc: {report['preflight_doc']}",
        f"tool_count: {report['tool_count']}",
        f"selected_capability: {report['selected_capability']}",
        "current_send_set: " + ", ".join(report["current_send_set"]),
        f"expected_action: {report['expected_action']}",
        f"current_commit: {report['current_commit']}",
        f"current_dirty: {str(report['current_dirty']).lower()}",
        "artifact_hashes_match_files: "
        f"{str(report['artifact_hashes_match_files']).lower()}",
        "artifact_commits_match_current: "
        f"{str(report['artifact_commits_match_current']).lower()}",
        f"artifact_payloads_clean: {str(report['artifact_payloads_clean']).lower()}",
        f"response_present_count: {report['response_present_count']}",
        f"closure_ready_count: {report['closure_ready_count']}",
        "components:",
        *[
            f"- {name}: {str(valid).lower()}"
            for name, valid in report["component_validity"].items()
        ],
    ]
    for key in BOUNDARY_FLAGS:
        lines.append(f"{key}: {str(report[key]).lower()}")
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _artifact_reports(
    repo_root: Path,
    *,
    current_commit: str,
    current_dirty: bool,
) -> dict[str, dict[str, Any]]:
    return {
        name: _artifact_report(
            repo_root,
            name,
            spec,
            current_commit=current_commit,
            current_dirty=current_dirty,
        )
        for name, spec in EXPECTED_ARTIFACTS.items()
    }


def _artifact_report(
    repo_root: Path,
    name: str,
    spec: ArtifactSpec,
    *,
    current_commit: str,
    current_dirty: bool,
) -> dict[str, Any]:
    failures: list[str] = []
    output_dir = Path(spec["output_dir"])
    hash_file = spec["hash_file"]
    payload_file = spec["payload_file"]
    required_files = spec["required_files"]
    absolute_output_dir = repo_root / output_dir

    for rel_path in required_files:
        if not (absolute_output_dir / rel_path).exists():
            failures.append(f"missing generated file: {output_dir / rel_path}")

    hash_path = absolute_output_dir / hash_file
    hash_manifest: dict[str, Any] = {"artifacts": []}
    if not hash_path.exists():
        failures.append(f"missing artifact hash manifest: {output_dir / hash_file}")
    else:
        try:
            hash_manifest = json.loads(hash_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            failures.append(f"artifact hash manifest is invalid JSON: {output_dir / hash_file}")

    hashed_paths = {
        artifact.get("path")
        for artifact in hash_manifest.get("artifacts", [])
        if isinstance(artifact, dict)
    }
    missing_hash_entries = sorted(set(required_files) - hashed_paths)
    if missing_hash_entries:
        failures.append(
            "artifact hash manifest is missing entries: "
            + ", ".join(missing_hash_entries)
        )
    if hash_file in hashed_paths:
        failures.append("artifact hash manifest must not hash itself")

    artifact_hashes_match_files = _artifact_hashes_match_files(
        absolute_output_dir, hash_manifest
    )
    if not artifact_hashes_match_files:
        failures.append("artifact hashes do not match generated files")

    payload: dict[str, Any] = {}
    payload_path = absolute_output_dir / payload_file
    if not payload_path.exists():
        failures.append(f"missing payload file: {output_dir / payload_file}")
    else:
        try:
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            failures.append(f"payload file is invalid JSON: {output_dir / payload_file}")
    payload_commit = payload.get("commit")
    payload_dirty = payload.get("dirty")
    commit_matches_current = payload_commit == current_commit
    freshness_enforced = not current_dirty
    if freshness_enforced:
        if not commit_matches_current:
            failures.append(
                f"payload commit is stale for {output_dir / payload_file}: "
                f"{payload_commit!r} != {current_commit!r}"
            )
        if payload_dirty is not False:
            failures.append(
                f"payload was generated from a dirty tree for {output_dir / payload_file}"
            )

    return {
        "name": name,
        "valid": not failures,
        "failures": failures,
        "output_dir": output_dir.as_posix(),
        "hash_file": (output_dir / hash_file).as_posix(),
        "payload_file": (output_dir / payload_file).as_posix(),
        "required_files": required_files,
        "artifact_hashes_match_files": artifact_hashes_match_files,
        "payload_commit": payload_commit,
        "payload_dirty": payload_dirty,
        "commit_matches_current": commit_matches_current,
        "freshness_enforced": freshness_enforced,
    }


def _artifact_hashes_match_files(output_dir: Path, hash_manifest: dict[str, Any]) -> bool:
    artifacts = hash_manifest.get("artifacts")
    if not isinstance(artifacts, list):
        return False
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            return False
        rel_path = artifact.get("path")
        expected_sha = artifact.get("sha256")
        expected_bytes = artifact.get("bytes")
        if not isinstance(rel_path, str) or not isinstance(expected_sha, str):
            return False
        path = output_dir / rel_path
        if not path.exists():
            return False
        data = path.read_bytes()
        if _normalize_sha256(expected_sha) != _sha256(data):
            return False
        if isinstance(expected_bytes, int) and expected_bytes != len(data):
            return False
    return True


def _normalize_sha256(value: str) -> str:
    return value.removeprefix("sha256:")


def _sha256(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


if __name__ == "__main__":
    raise SystemExit(main())

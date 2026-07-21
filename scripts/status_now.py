"""Print the compact current development and handoff posture."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (  # noqa: E402
    artifact_freshness_check,
    enterprise_operator_next_action,
    validation_decision,
)

ROOT = Path(__file__).resolve().parents[1]
SEND_MANIFEST_JSON = Path(
    "var/review-packets/v3/enterprise-review-send-manifest/"
    "enterprise-review-send-manifest.json"
)
UPLOAD_STAGING_DIR = "var/review-packets/v3/enterprise-review-upload-staging"
DUAL_RESPONSE_INBOX_DIR = "var/review-runs/enterprise-dual-response-inbox"
SEND_RECEIPT_COPY = (
    "var/review-runs/enterprise-review-send-receipts/"
    "enterprise-review-send-receipt-copy.json"
)
ERG004_SOURCE_REVIEW_DIR = (
    "var/review-packets/v3/sandbox-vm-live-poc-runtime-descriptor-only-source-review"
)
ERG004_RESPONSE_INBOX_DIR = (
    "var/review-runs/sandbox-vm-live-poc-runtime-descriptor-only-response-inbox"
)
ERG004_RAW_RESPONSE = (
    "var/review-runs/sandbox-vm-live-poc-runtime-descriptor-only-response-inbox/"
    "RAW_RESPONSE_ERG-004-DESCRIPTOR-ONLY.md"
)
ENTERPRISE_SEND_NOW_DIR = "var/review-packets/v3/enterprise-send-now"
TRUSTED_HOST_EXTERNAL_REVIEW_DIR = (
    "var/review-packets/v3/trusted-host-promotion-external-review"
)
TRUSTED_HOST_RESPONSE_KIT_DIR = (
    "var/review-packets/v3/trusted-host-promotion-response-kit"
)
PIS_EXTERNAL_REVIEW_DIR = (
    "var/review-packets/v3/production-identity-storage-external-review"
)
PIS_RESPONSE_KIT_DIR = "var/review-packets/v3/production-identity-storage-response-kit"


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
    validation = validation_decision.build_report()
    freshness = artifact_freshness_check.build_report(repo_root)
    enterprise_next = enterprise_operator_next_action.build_report(repo_root)
    next_commands = _recommended_next_commands(validation, freshness, enterprise_next)
    return {
        "schema_version": "1",
        "valid": validation.get("valid") is True,
        "commit": freshness.get("commit"),
        "dirty": freshness.get("dirty"),
        "tool_count": freshness.get("tool_count"),
        "latest_implemented_tool": _latest_implemented_tool(repo_root),
        "selected_capability": _selected_capability(repo_root),
        "technical_mvp_state": freshness.get("technical_mvp_state"),
        "enterprise_next_action": enterprise_next.get("next_action"),
        "recommended_send_set": enterprise_next.get("recommended_send_set"),
        "response_present_count": enterprise_next.get("response_present_count"),
        "closure_ready_count": enterprise_next.get("closure_ready_count"),
        "validation_mode": validation.get("recommended_mode"),
        "validation_categories": validation.get("categories", []),
        "next_development_commands": validation.get("next_development_commands", []),
        "deferred_handoff_commands": validation.get("deferred_handoff_commands", []),
        "release_slice_commands": validation.get("release_slice_commands", []),
        "artifact_freshness_valid": freshness.get("valid"),
        "artifact_refresh_commands": freshness.get("refresh_commands", []),
        "recommended_next_commands": next_commands,
        "handoff_paths": _handoff_paths(repo_root, enterprise_next),
        "release_or_handoff_required": validation.get("release_or_handoff_required"),
        "runtime_changes_allowed": False,
        "new_power_classes_allowed": False,
        "sandbox_orchestration_allowed": False,
        "mission_control_execution_allowed": False,
        "public_security_product_positioning_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin status now",
        f"valid: {str(report['valid']).lower()}",
        f"commit: {report['commit']}",
        f"dirty: {str(report['dirty']).lower()}",
        f"tool_count: {report['tool_count']}",
        f"latest_implemented_tool: {report['latest_implemented_tool']}",
        f"selected_capability: {report['selected_capability']}",
        f"technical_mvp_state: {report['technical_mvp_state']}",
        f"enterprise_next_action: {report['enterprise_next_action']}",
        f"response_present_count: {report['response_present_count']}",
        f"closure_ready_count: {report['closure_ready_count']}",
        f"validation_mode: {report['validation_mode']}",
        "validation_categories: "
        + (", ".join(report["validation_categories"]) or "none"),
        f"artifact_freshness_valid: {str(report['artifact_freshness_valid']).lower()}",
        "recommended_next_commands:",
    ]
    lines.extend(f"- {command}" for command in report["recommended_next_commands"])
    if report["handoff_paths"]:
        lines.append("handoff_paths:")
        for label, path in report["handoff_paths"].items():
            lines.append(f"- {label}: {path}")
    if report["release_slice_commands"]:
        lines.append("release_slice_commands:")
        lines.extend(f"- {command}" for command in report["release_slice_commands"])
    lines.extend(
        [
            "boundaries:",
            "- status-only; does not start services or call governed tools",
            "- not release proof; use make release-check before checkpoint claims",
            "- not handoff proof; use make review-candidate before packet handoff",
        ]
    )
    return "\n".join(lines)


def _recommended_next_commands(
    validation: dict[str, Any],
    freshness: dict[str, Any],
    enterprise_next: dict[str, Any],
) -> list[str]:
    if validation.get("git_dirty"):
        return list(validation.get("next_development_commands", []))
    if not freshness.get("valid"):
        return list(freshness.get("refresh_commands", []))
    if enterprise_next.get("next_action") == "send_erg_003_and_erg_002":
        return [
            "make handoff-dry-run",
            "make enterprise-send-now",
            "make enterprise-review-send-receipt-copy after the human send step",
            "make enterprise-review-send-receipt-fill ARGS=\"...\" after the human send step",
            "make enterprise-review-send-receipt-validate RECEIPT=path/to/copied-receipt.json",
            "make enterprise-response-waiting-room after reviewer responses arrive",
            "make enterprise-response-now after reviewer responses arrive",
            "make enterprise-response-paste-preflight after reviewer responses arrive",
        ]
    if enterprise_next.get("next_action") == "prepare_erg004_runtime_ticket_review":
        return [
            "make sandbox-vm-live-poc-runtime-ticket-check",
            "make sandbox-vm-live-poc-runtime-ticket-review-bundle",
            "make sandbox-vm-live-poc-runtime-ticket-review-bundle-check",
        ]
    if enterprise_next.get("next_action") == "prepare_erg004_runtime_implementation_gate":
        return [
            "make sandbox-vm-live-poc-runtime-ticket-internal-review-check",
            "make sandbox-vm-live-poc-runtime-implementation-gate-check",
            "make sandbox-vm-live-poc-runtime-descriptor-contract-check",
            "make sandbox-vm-live-poc-runtime-descriptor-contract-internal-review-check",
            "make sandbox-vm-live-poc-runtime-gate-readiness-review-bundle-check",
            "make sandbox-vm-live-poc-runtime-gate-readiness-internal-review-check",
            "make sandbox-vm-live-poc-runtime-descriptor-only-plan-check",
            "make sandbox-vm-live-poc-runtime-descriptor-only-implementation-ticket-check",
            "make sandbox-vm-live-poc-runtime-descriptor-only-ticket-review-bundle-check",
            "make sandbox-vm-live-poc-runtime-gate-readiness-response-intake-check",
            "make sandbox-vm-live-poc-runtime-gate-readiness-response-dry-run",
            "make sandbox-vm-live-poc-runtime-gate-readiness-response-application-record-check",
            "make sandbox-vm-live-poc-runtime-gate-readiness-response-application-playbook-check",
            "make sandbox-vm-live-poc-runtime-gate-readiness-response-application-preflight-check",
            "make sandbox-vm-live-poc-runtime-gate-readiness-decision-record-skeleton-check",
        ]
    if enterprise_next.get("next_action") == "prepare_erg004_descriptor_only_runtime_planning":
        return [
            "make sandbox-vm-live-poc-runtime-gate-readiness-decision-record-check",
            "make sandbox-vm-live-poc-runtime-descriptor-only-plan-check",
            "make sandbox-vm-live-poc-runtime-descriptor-only-implementation-ticket-check",
            "make sandbox-vm-live-poc-runtime-descriptor-only-implementation-decision-check",
            "make sandbox-vm-live-poc-runtime-descriptor-only-implementation-check",
            "make sandbox-vm-live-poc-runtime-descriptor-only-internal-source-review-check",
            "make sandbox-vm-live-poc-runtime-descriptor-only-negative-transcripts",
            "make sandbox-vm-live-poc-runtime-descriptor-only-ticket-review-bundle-check",
            "make sandbox-vm-live-poc-runtime-descriptor-only-source-review-bundle-check",
            "make sandbox-vm-live-poc-runtime-descriptor-only-external-response-intake-check",
            "make sandbox-vm-live-poc-runtime-descriptor-only-response-inbox-check",
            "make sandbox-vm-live-poc-runtime-descriptor-only-send-receipt-check",
            "make sandbox-vm-live-poc-runtime-descriptor-only-response-dry-run",
            "make sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight-check",
            "make no-new-powers-guardrail",
            "make tool-surface-invariant-gate",
        ]
    if enterprise_next.get("next_action") == "prepare_erg005_trusted_host_promotion_review":
        return [
            "make trusted-host-promotion-decision-intake-check",
            "make trusted-host-promotion-state-machine-check",
            "make trusted-host-promotion-negative-fixtures-check",
            "make trusted-host-promotion-zone-contract-check",
            "make trusted-host-promotion-implementation-plan-check",
            "make trusted-host-promotion-source-review-packet-check",
            "make trusted-host-promotion-disposition-packet-check",
            "make trusted-host-promotion-external-review-bundle-check",
            "make trusted-host-promotion-response-kit-check",
            "make trusted-host-promotion-response-dry-run",
            "make trusted-host-promotion-internal-review-check",
            "make trusted-host-promotion-implementation-gate-decision-check",
            "make trusted-host-promotion-limited-runtime-plan-check",
            "make trusted-host-promotion-limited-runtime-ticket-check",
            "make trusted-host-promotion-runtime-implementation-decision-check",
            "make trusted-host-promotion-negative-transcripts",
            "make trusted-host-promotion-runtime-source-review-bundle-check",
            "make no-new-powers-guardrail",
            "make tool-surface-invariant-gate",
        ]
    if enterprise_next.get("next_action") == (
        "prepare_pis_002_entry_decision_record"
    ):
        return [
            "make production-identity-storage-pis-001-internal-review-check",
            "make production-identity-storage-pis-001-decision-check",
            "make production-identity-storage-pis-001-planning-gate-check",
            "make no-new-powers-guardrail",
            "make tool-surface-invariant-gate",
        ]
    return ["make dev-check"]


def _latest_implemented_tool(repo_root: Path) -> str:
    text = (repo_root / "var/review-packets/v1.0/rc/00_V1_RC_PACKET_INDEX.md").read_text(
        encoding="utf-8"
    )
    for line in text.splitlines():
        if line.startswith("- Latest implemented tool:"):
            parts = line.split("`")
            if len(parts) >= 2:
                return parts[1]
    return "unknown"


def _selected_capability(repo_root: Path) -> str:
    text = (repo_root / "docs/codex/next-capability-readiness.md").read_text(
        encoding="utf-8"
    )
    for line in text.splitlines():
        if line.startswith("- Selected candidate:"):
            return line.removeprefix("- Selected candidate:").strip(" .`")
    return "unknown"


def _send_manifest_count(repo_root: Path, key: str) -> int:
    path = repo_root / SEND_MANIFEST_JSON
    if not path.exists():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    value = data.get(key)
    return value if isinstance(value, int) else 0


def _handoff_paths(repo_root: Path, enterprise_next: dict[str, Any]) -> dict[str, str]:
    if enterprise_next.get("recommended_send_set") == ["ERG-004"]:
        return {
            "active_send_now": ENTERPRISE_SEND_NOW_DIR,
            "erg004_source_review_packet": ERG004_SOURCE_REVIEW_DIR,
            "erg004_response_inbox": ERG004_RESPONSE_INBOX_DIR,
            "erg004_raw_response": ERG004_RAW_RESPONSE,
        }
    if enterprise_next.get("recommended_send_set") == ["ERG-005"]:
        return {
            "active_send_now": ENTERPRISE_SEND_NOW_DIR,
            "trusted_host_external_review": TRUSTED_HOST_EXTERNAL_REVIEW_DIR,
            "trusted_host_response_kit": TRUSTED_HOST_RESPONSE_KIT_DIR,
        }
    if enterprise_next.get("recommended_send_set") == ["ERG-006", "ERG-007"]:
        return {
            "active_send_now": ENTERPRISE_SEND_NOW_DIR,
            "production_identity_storage_external_review": PIS_EXTERNAL_REVIEW_DIR,
            "production_identity_storage_response_kit": PIS_RESPONSE_KIT_DIR,
        }

    path = repo_root / SEND_MANIFEST_JSON
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    paths = {
        "dual_review_outbox": data.get("outbox_dir"),
        "submission_prompt": data.get("submission_prompt_dir"),
        "send_receipt_template": data.get("receipt_template_dir"),
        "send_receipt_copy": SEND_RECEIPT_COPY,
        "upload_staging": UPLOAD_STAGING_DIR,
        "dual_response_inbox": DUAL_RESPONSE_INBOX_DIR,
    }
    return {key: value for key, value in paths.items() if isinstance(value, str) and value}


if __name__ == "__main__":
    raise SystemExit(main())

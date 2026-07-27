"""Validate the bounded Enterprise E1 Command Center cockpit contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/codex/enterprise-e1-cockpit-contract.json"
EXPECTED_SURFACES = [
    "missions",
    "nodes",
    "versions",
    "configuration",
    "attention",
    "approvals",
    "evidence",
]
EXPECTED_TRUTH_SOURCES = ["gateway", "node_connectivity", "runner", "model_provider"]


def _read(root: Path, relative: str, failures: list[str]) -> str:
    try:
        return (root / relative).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        failures.append(f"cockpit source unavailable: {relative}")
        return ""


def build_report(root: Path) -> dict[str, Any]:
    failures: list[str] = []
    try:
        contract = json.loads(
            (root / CONTRACT.relative_to(ROOT)).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {"valid": False, "failures": [f"contract unavailable: {exc}"]}

    surfaces = contract.get("surfaces") if isinstance(contract, dict) else None
    surface_ids = (
        [surface.get("id") for surface in surfaces if isinstance(surface, dict)]
        if isinstance(surfaces, list)
        else []
    )
    if surface_ids != EXPECTED_SURFACES:
        failures.append("cockpit surfaces are not exact and ordered")
    if contract.get("tool_count") != 24:
        failures.append("cockpit contract does not preserve 24 tools")

    truth_sources = contract.get("truth_sources")
    if not isinstance(truth_sources, dict) or list(truth_sources) != EXPECTED_TRUTH_SOURCES:
        failures.append("cockpit truth sources are not exact and ordered")
        truth_sources = {}

    actions = contract.get("operator_actions")
    if not isinstance(actions, list) or not actions:
        failures.append("cockpit operator actions are unavailable")
        actions = []
    for action in actions:
        if (
            not isinstance(action, dict)
            or action.get("authority") != "existing_gateway_governed_workflow"
            or not str(action.get("path", "")).startswith("POST /")
        ):
            failures.append("cockpit action escapes an existing Gateway workflow")
            break

    accessibility = contract.get("accessibility")
    if not isinstance(accessibility, dict):
        failures.append("cockpit accessibility contract is unavailable")
        accessibility = {}
    for key in (
        "semantic_destination_regions",
        "keyboard_skip_to_attention",
        "focus_transfer_after_navigation",
        "state_not_conveyed_by_color_alone",
        "async_status_and_errors_announced",
    ):
        if accessibility.get(key) is not True:
            failures.append(f"cockpit accessibility binding is not closed: {key}")
    if any(
        accessibility.get(key) is not False
        for key in ("fresh_human_accessibility_uat_complete", "wcag_conformance_claimed")
    ):
        failures.append("cockpit accessibility evidence overclaims human acceptance")

    authority = contract.get("authority")
    if not isinstance(authority, dict):
        failures.append("cockpit authority is unavailable")
        authority = {}
    if authority.get("gateway_remains_authoritative") is not True or any(
        authority.get(key) is not False
        for key in (
            "command_center_execution_authority",
            "direct_runner_control",
            "direct_model_provider_control",
            "arbitrary_host_control",
            "new_governed_tool",
            "human_uat_complete",
        )
    ):
        failures.append("cockpit authority boundary changed")

    app = _read(root, "apps/ui/src/App.tsx", failures)
    app_test = _read(root, "apps/ui/src/App.test.tsx", failures)
    required_app_fragments = [
        'aria-label="Ithildin Nodes"',
        'aria-label="Loaded Node configuration cohorts"',
        'aria-label="Loaded Node software version cohorts"',
        'aria-label="Mission truth sources"',
        'source="Gateway authoritative"',
        'source="Runner reported through Node"',
        'label="Model provider"',
        'value="Unknown"',
        'role="alert"',
        'role="status"',
        'apiRequest<MissionOperatorSummary>("/missions"',
        '`/missions/${encodeURIComponent(mission.mission_id)}/cancel`',
        '"/nodes/enrollment-codes"',
        '`/nodes/${encodeURIComponent(node.node_id)}/configurations`',
        '`/nodes/${encodeURIComponent(node.node_id)}/configuration-trust-transitions`',
        '`/nodes/${encodeURIComponent(node.node_id)}/revoke`',
        '`/approvals/${approvalId}/${action}`',
    ]
    for fragment in required_app_fragments:
        if fragment not in app:
            failures.append(f"cockpit implementation binding missing: {fragment}")

    required_test_fragments = [
        "Skip to operator attention",
        (
            "presents mission admission and every authority source without runner "
            "or provider overclaim"
        ),
        "routes mission evidence exceptions into keyboard-accessible Attention remediation",
        "presents Gateway-derived Node identity without claiming runner health",
        "groups loaded enrolled Nodes into bounded configuration rollout cohorts",
        "groups loaded enrolled Nodes into bounded software version observation cohorts",
        "Request Gateway cancellation",
        "does not prove that a runner process stopped",
    ]
    for fragment in required_test_fragments:
        if fragment not in app_test:
            failures.append(f"cockpit UI evidence binding missing: {fragment}")

    lock = json.loads((root / "tool-manifests.lock.json").read_text(encoding="utf-8"))
    lock_tool_count = len(lock.get("manifests", []))
    if lock_tool_count != 24:
        failures.append("cockpit implementation does not preserve 24 tools")

    return {
        "valid": not failures,
        "failures": failures,
        "schema_version": contract.get("schema_version"),
        "tool_count": contract.get("tool_count"),
        "manifest_tool_count": lock_tool_count,
        "surfaces": surface_ids,
        "surface_count": len(surface_ids),
        "truth_sources": list(truth_sources),
        "action_count": len(actions),
        "gateway_authoritative": True,
        "command_center_execution_authority": False,
        "new_governed_tool": False,
        "human_uat_complete": False,
    }


def main() -> int:
    report = build_report(ROOT)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

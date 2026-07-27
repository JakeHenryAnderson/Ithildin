"""Validate the closed Enterprise E1 policy and Node-configuration state contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/codex/enterprise-e1-configuration-state-contract.json"
EXPECTED_STATES = [
    "desired",
    "acknowledged",
    "stored",
    "enforced",
    "stale",
    "rejected",
    "rollback",
]


def build_report(root: Path) -> dict[str, Any]:
    failures: list[str] = []
    try:
        contract = json.loads(
            (root / CONTRACT.relative_to(ROOT)).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {"valid": False, "failures": [f"contract unavailable: {exc}"]}
    states = contract.get("states") if isinstance(contract, dict) else None
    state_ids = (
        [state.get("id") for state in states if isinstance(state, dict)]
        if isinstance(states, list)
        else []
    )
    if state_ids != EXPECTED_STATES:
        failures.append("configuration states are not exact and ordered")
    if contract.get("tool_count") != 24:
        failures.append("configuration contract does not preserve 24 tools")
    authority = contract.get("authority")
    if not isinstance(authority, dict):
        failures.append("configuration authority is unavailable")
        authority = {}
    if authority.get("gateway_remains_authoritative") is not True or any(
        authority.get(key) is not False
        for key in (
            "node_self_configuration_allowed",
            "offline_governed_actions_allowed",
            "new_governed_tool",
            "arbitrary_host_control",
            "runner_enforcement_globally_proven",
            "human_uat_complete",
        )
    ):
        failures.append("configuration authority boundary changed")
    sources = {
        "node_configuration": (
            root / "apps/api/src/ithildin_api/node_configuration.py"
        ).read_text(encoding="utf-8"),
        "governed_access": (
            root / "apps/api/src/ithildin_api/node_governed_access.py"
        ).read_text(encoding="utf-8"),
        "api": (root / "apps/api/src/ithildin_api/app.py").read_text(encoding="utf-8"),
        "node": (root / "apps/node/src/ithildin_node/client.py").read_text(
            encoding="utf-8"
        ),
    }
    required_fragments = {
        "node_configuration": [
            'CONFIGURATION_ACK_STATUS = "stored_not_enforced"',
            "policy_digest",
            "manifest_lock_digest",
            "manual_rollback",
        ],
        "governed_access": [
            "Node desired configuration is not acknowledged",
            "Node desired policy is not current",
            "Node desired tool manifest is not current",
            "Node offline posture is not fail closed",
        ],
        "api": [
            '"/nodes/{node_id}/configurations"',
            '"/nodes/{node_id}/configurations/rollback"',
            '"/nodes/{node_id}/configuration/acknowledgments"',
        ],
        "node": [
            "verify_configuration_bundle",
            "stored configuration does not fail closed offline",
            "_write_private_json_atomic",
        ],
    }
    for source, fragments in required_fragments.items():
        for fragment in fragments:
            if fragment not in sources[source]:
                failures.append(f"configuration implementation binding missing: {fragment}")
    return {
        "valid": not failures,
        "failures": failures,
        "schema_version": contract.get("schema_version"),
        "tool_count": contract.get("tool_count"),
        "states": state_ids,
        "state_count": len(state_ids),
        "new_governed_tool": False,
        "gateway_authoritative": True,
        "human_uat_complete": False,
    }


def main() -> int:
    report = build_report(ROOT)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

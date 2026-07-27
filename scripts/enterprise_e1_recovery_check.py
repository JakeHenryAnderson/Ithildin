"""Validate the bounded Enterprise E1 upgrade and recovery contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def build_report(root: Path) -> dict[str, Any]:
    failures: list[str] = []
    required = {
        "operations": (
            "scripts/local_v1_operations_rehearsal.py",
            [
                "backup_manifest_matched",
                "failed_update_failed_closed",
                "restore_manifest_matched",
                "restored_stack_health_verified",
            ],
        ),
        "node_recovery": (
            "scripts/local_v1_failure_recovery_journey.py",
            [
                "Manual rollback creates a fresh signed generation",
                "Stored configuration remains stored_not_enforced",
            ],
        ),
        "migration_backup": (
            "apps/api/src/ithildin_api/database_migration_backup.py",
            [
                'TARGET_SCHEMA_VERSION = "4"',
                '"downgrade_posture": "restore_only"',
                "PRAGMA integrity_check",
            ],
        ),
        "contract": (
            "docs/codex/enterprise-e1-recovery-contract.md",
            [
                "revoke and re-enroll",
                "ambiguous",
                "make enterprise-e1-recovery-check",
            ],
        ),
    }
    for label, (relative, fragments) in required.items():
        path = root / relative
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            failures.append(f"{label} source unavailable")
            continue
        for fragment in fragments:
            if fragment not in text:
                failures.append(f"{label} binding missing: {fragment}")
    lock = json.loads((root / "tool-manifests.lock.json").read_text(encoding="utf-8"))
    tool_count = len(lock.get("manifests", []))
    if tool_count != 24:
        failures.append("recovery contract does not preserve 24 tools")
    return {
        "valid": not failures,
        "failures": failures,
        "tool_count": tool_count,
        "gateway_command_center_recovery": True,
        "optional_node_automatic_restore": False,
        "ambiguous_state_overwrite_allowed": False,
        "downgrade_posture": "restore_only",
        "new_governed_power": False,
        "human_uat_complete": False,
    }


def main() -> int:
    report = build_report(ROOT)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

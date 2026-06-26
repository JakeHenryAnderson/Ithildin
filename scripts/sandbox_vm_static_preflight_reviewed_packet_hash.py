"""Print the reviewed-packet hash for ERG-003 static preflight intake."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import sandbox_vm_static_preflight_disposition_closure_check as closure

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = build_report(ROOT)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif report["valid"]:
        print(report["reviewed_packet_hash"])
    else:
        print(render_report(report), file=sys.stderr)
    return 0 if report["valid"] else 1


def build_report(repo_root: Path) -> dict[str, Any]:
    path = repo_root / closure.REVIEW_PACKET_HASH_MANIFEST_REL
    failures: list[str] = []
    reviewed_packet_hash: str | None = None
    if not path.exists():
        failures.append(
            "ERG-003 external-review artifact-hash manifest is missing; "
            "run make sandbox-vm-static-preflight-external-review-bundle first"
        )
    else:
        reviewed_packet_hash = closure.current_reviewed_packet_hash(repo_root)

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "reviewed_packet_hash": reviewed_packet_hash,
        "hash_source": closure.REVIEW_PACKET_HASH_MANIFEST_REL,
        "tool_count": 24,
        "erg_003_status": "external_review_required",
        "runtime_changes_allowed": False,
        "live_vm_inspection_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "new_power_classes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM static preflight reviewed packet hash",
        f"valid: {str(report['valid']).lower()}",
        f"hash_source: {report['hash_source']}",
        f"reviewed_packet_hash: {report['reviewed_packet_hash']}",
        f"tool_count: {report['tool_count']}",
        f"erg_003_status: {report['erg_003_status']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

"""Validate the bounded Enterprise E1 operational-evidence export contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/codex/enterprise-e1-evidence-contract.json"
EXPECTED_SECTIONS = [
    "deployment",
    "configuration",
    "recovery",
    "missions",
    "fleet",
    "approvals",
    "audit",
]
EXPECTED_NONCLAIMS = [
    "SIEM custody",
    "hosted telemetry",
    "external notarization",
    "whole-host coverage",
    "compliance automation",
    "production identity",
    "enterprise production readiness",
    "human UAT completion",
]


def build_report(root: Path) -> dict[str, Any]:
    failures: list[str] = []
    try:
        contract = json.loads(
            (root / CONTRACT.relative_to(ROOT)).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {"valid": False, "failures": [f"contract unavailable: {exc}"]}
    sections = contract.get("required_sections") if isinstance(contract, dict) else None
    if sections != EXPECTED_SECTIONS:
        failures.append("evidence sections are not exact and ordered")
    if contract.get("nonclaims") != EXPECTED_NONCLAIMS:
        failures.append("evidence nonclaims are not exact and ordered")
    if contract.get("tool_count") != 24:
        failures.append("evidence contract does not preserve 24 tools")
    verification = contract.get("verification")
    if (
        not isinstance(verification, dict)
        or verification.get("local_content_integrity_only") is not True
        or verification.get("manifest_self_authentication_claimed") is not False
        or verification.get("external_notarization_claimed") is not False
    ):
        failures.append("evidence verification scope changed")
    authority = contract.get("authority")
    if not isinstance(authority, dict) or any(
        authority.get(key) is not False
        for key in (
            "export_is_authorization_input",
            "external_delivery_performed",
            "new_governed_tool",
            "arbitrary_host_control",
            "human_uat_complete",
        )
    ):
        failures.append("evidence authority boundary changed")

    sources = {
        "builder": (
            root / "scripts/enterprise_e1_operations_bundle.py"
        ).read_text(encoding="utf-8"),
        "tests": (
            root / "tests/test_enterprise_e1_operations_bundle.py"
        ).read_text(encoding="utf-8"),
        "docs": (
            root / "docs/codex/enterprise-e1-evidence-export.md"
        ).read_text(encoding="utf-8"),
    }
    required = {
        "builder": [
            "ZIP_STORED",
            "RedactionService",
            "scan_packet_paths",
            "content_root_sha256",
            "output target already exists",
        ],
        "tests": [
            "deterministic_redacted_and_offline_verifiable",
            "digest mismatch",
            "unmanifested_member",
        ],
        "docs": [
            "receiver-neutral",
            "SIEM custody",
            "whole-host",
            "make enterprise-e1-evidence-check",
        ],
    }
    for source, fragments in required.items():
        for fragment in fragments:
            if fragment not in sources[source]:
                failures.append(f"evidence implementation binding missing: {fragment}")
    lock = json.loads((root / "tool-manifests.lock.json").read_text(encoding="utf-8"))
    manifest_tool_count = len(lock.get("manifests", []))
    if manifest_tool_count != 24:
        failures.append("evidence implementation does not preserve 24 tools")
    return {
        "valid": not failures,
        "failures": failures,
        "schema_version": contract.get("schema_version"),
        "tool_count": contract.get("tool_count"),
        "manifest_tool_count": manifest_tool_count,
        "sections": sections,
        "section_count": len(sections) if isinstance(sections, list) else 0,
        "receiver_neutral": True,
        "local_content_integrity_only": True,
        "external_delivery_performed": False,
        "new_governed_tool": False,
        "human_uat_complete": False,
    }


def main() -> int:
    report = build_report(ROOT)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

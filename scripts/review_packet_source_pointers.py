"""Validate review-packet source pointers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/codex/review-packet-source-pointers.md"
REQUIRED_POINTERS = {
    "patch apply": [
        "apps/api/src/ithildin_api/patches.py",
        "apps/api/src/ithildin_api/tool_calls.py",
        "apps/api/src/ithildin_api/approvals.py",
    ],
    "filesystem": [
        "apps/api/src/ithildin_api/read_tools.py",
        "apps/api/src/ithildin_api/workspaces.py",
        "apps/api/src/ithildin_api/filesystem_contract.py",
    ],
    "http fetch": ["apps/api/src/ithildin_api/http_tools.py"],
    "signed evidence": [
        "packages/audit-core/src/ithildin_audit_core/signing.py",
        "apps/api/src/ithildin_api/manifest_lock.py",
    ],
    "policy parity": [
        "apps/api/src/ithildin_api/policy_preview.py",
        "apps/api/src/ithildin_api/tool_calls.py",
        "apps/api/src/ithildin_api/decision_evidence.py",
    ],
    "mcp ingress": ["apps/mcp-server/src/ithildin_mcp_server/server.py"],
    "review console": ["apps/ui/src/App.tsx"],
    "release automation": [
        "scripts/release_evidence.py",
        "scripts/external_review_dispatch_packets.py",
        "scripts/reviewer_artifact_manifest.py",
        "scripts/source_review_transcript_packet.py",
        "scripts/review_packet_source_pointers.py",
        "scripts/v06_lane_status.py",
    ],
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
    if not (repo_root / DOC.relative_to(ROOT)).exists():
        failures.append("review packet source pointers doc is missing")
        doc_text = ""
    else:
        doc_text = (repo_root / DOC.relative_to(ROOT)).read_text(encoding="utf-8")

    pointer_count = 0
    for area, paths in REQUIRED_POINTERS.items():
        if area not in doc_text.lower():
            failures.append(f"source pointer doc missing area: {area}")
        for path in paths:
            pointer_count += 1
            if not (repo_root / path).exists():
                failures.append(f"source pointer target missing: {path}")
            if path not in doc_text:
                failures.append(f"source pointer doc missing path: {path}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "area_count": len(REQUIRED_POINTERS),
        "pointer_count": pointer_count,
        "doc_path": DOC.relative_to(ROOT).as_posix(),
        "runtime_behavior_changed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin review packet source pointers",
        f"valid: {str(report['valid']).lower()}",
        f"area_count: {report['area_count']}",
        f"pointer_count: {report['pointer_count']}",
        "runtime_behavior_changed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

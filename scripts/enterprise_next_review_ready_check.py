"""Check that the recommended ERG-003 enterprise review handoff is ready to send."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    enterprise_next_review_handoff,
    sandbox_vm_static_preflight_disposition_closure_check,
    sandbox_vm_static_preflight_external_review_bundle,
    sandbox_vm_static_preflight_reviewed_packet_hash,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-next-review-ready-check.md"


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
    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_docs = _read(repo_root / "scripts/review_docs.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    bundle_report = sandbox_vm_static_preflight_external_review_bundle.build_check_report(
        repo_root
    )
    handoff_report = enterprise_next_review_handoff.build_check_report(repo_root)
    hash_report = sandbox_vm_static_preflight_reviewed_packet_hash.build_report(repo_root)
    closure_report = sandbox_vm_static_preflight_disposition_closure_check.build_report(
        repo_root
    )

    for label, report in [
        ("external-review bundle", bundle_report),
        ("enterprise next-review handoff", handoff_report),
        ("reviewed-packet hash helper", hash_report),
        ("disposition closure gate", closure_report),
    ]:
        if not report.get("valid"):
            failures.append(f"{label} is not valid")
            failures.extend(f"{label}: {failure}" for failure in report.get("failures", []))

    if closure_report.get("closure_ready") is True:
        failures.append("ERG-003 closure is already ready; use the triage-update path instead")
    if closure_report.get("normalized_response_present") is True:
        failures.append("normalized ERG-003 response already exists; review intake before sending")
    if hash_report.get("reviewed_packet_hash") != closure_report.get(
        "expected_reviewed_packet_hash"
    ):
        failures.append("reviewed-packet hash helper does not match closure gate expectation")

    for phrase in [
        "Recommended packet: `var/review-packets/v3/sandbox-vm-static-preflight-external-review/`",
        "make enterprise-next-review-ready-check",
        "make sandbox-vm-static-preflight-external-review-bundle",
        "make sandbox-vm-static-preflight-reviewed-packet-hash",
        "make enterprise-next-review-handoff",
        "does not close `ERG-003`",
        "does not approve live VM/container inspection",
        "does not approve local model invocation",
        "does not approve sandbox orchestration",
    ]:
        if phrase not in doc:
            failures.append(f"ready-check doc is missing phrase: {phrase}")

    wiring = {
        "Make target": "enterprise-next-review-ready-check:",
        "Release check": "enterprise-next-review-ready-check",
        "README command": "make enterprise-next-review-ready-check",
        "Docs site": DOC_REL,
        "Review docs": DOC_REL,
        "Review index": "Enterprise Next Review Ready Check",
        "Release guardrails": "enterprise-next-review-ready-check",
    }
    if wiring["Make target"] not in makefile:
        failures.append("Make target is missing: enterprise-next-review-ready-check")
    if wiring["Release check"] not in release_check_body:
        failures.append("enterprise-next-review-ready-check is missing from release-check")
    if wiring["README command"] not in readme:
        failures.append("README is missing enterprise next-review ready-check command")
    if wiring["Docs site"] not in docs_site:
        failures.append("enterprise next-review ready check is missing from docs site inputs")
    if wiring["Review docs"] not in review_docs:
        failures.append("enterprise next-review ready check is missing from review docs")
    if wiring["Review index"] not in review_index:
        failures.append("review-docs index is missing enterprise next-review ready check")
    if wiring["Release guardrails"] not in release_guardrails:
        failures.append("release guardrails do not require enterprise next-review ready check")

    ready_to_send = (
        not failures
        and bundle_report.get("valid") is True
        and handoff_report.get("valid") is True
        and hash_report.get("valid") is True
        and closure_report.get("valid") is True
        and closure_report.get("closure_ready") is False
        and closure_report.get("normalized_response_present") is False
    )

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "ready_to_send": ready_to_send,
        "recommended_gap": "ERG-003",
        "recommended_packet": (
            "var/review-packets/v3/sandbox-vm-static-preflight-external-review/"
        ),
        "reviewed_packet_hash": hash_report.get("reviewed_packet_hash"),
        "normalized_response_present": closure_report.get("normalized_response_present"),
        "closure_ready": closure_report.get("closure_ready"),
        "tool_count": 24,
        "runtime_changes_allowed": False,
        "live_vm_inspection_allowed": False,
        "mission_control_runtime_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "network_expansion_allowed": False,
        "api_mcp_profile_loading_allowed": False,
        "new_power_classes_allowed": False,
        "closes_erg_003": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise next-review ready check",
        f"valid: {str(report['valid']).lower()}",
        f"ready_to_send: {str(report['ready_to_send']).lower()}",
        f"recommended_gap: {report['recommended_gap']}",
        f"recommended_packet: {report['recommended_packet']}",
        f"reviewed_packet_hash: {report['reviewed_packet_hash']}",
        f"normalized_response_present: {str(report['normalized_response_present']).lower()}",
        f"closure_ready: {str(report['closure_ready']).lower()}",
        f"tool_count: {report['tool_count']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
        f"closes_erg_003: {str(report['closes_erg_003']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())

"""Validate the enterprise-readiness runway and its release-readiness wiring."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs

ROOT = Path(__file__).resolve().parents[1]
RUNWAY_DOC = ROOT / "docs/codex/enterprise-readiness-runway.md"

REQUIRED_PHRASES = [
    "Status: design-only runway beyond the v1.0 local-preview RC.",
    "Current governed tool count: `24`",
    "Current selected capability: `not selected`",
    "Mission Control remains the operator-facing mission/run dashboard.",
    "Ithildin remains the policy, approval, execution, redaction, and evidence gateway.",
    "Sandbox/VM workers remain isolated execution environments",
    "Phase E1: Local RC Freeze And Trusted User Trial",
    "Phase E2: Mission Control Display Integration",
    "Phase E3: Sandbox/VM Worker Proof Of Concept",
    "Phase E4: Trusted-Host Promotion Lane",
    "Phase E5: Production IAM And Storage Architecture",
    "Phase E6: Evidence Export And SIEM Adapter Lane",
    "Phase E7: Compliance Mapping Support",
    "Current Next Best Action",
    "Mission Control display proposal, handoff schema, negative fixtures",
    "focused display review",
    "packet now exist",
    "static preflight CLI fixture runner",
    "internal source-review pass also now exist",
    "current enterprise-path action is external/source review disposition",
    "separate post-RC decision",
    "live VM/container inspection",
    "Mission Control runtime importer",
    "sandbox/VM worker proof-of-concept boundary",
    "sandbox-vm-worker-boundary-charter.md",
    "make sandbox-vm-worker-boundary-charter-check",
    "sandbox-vm-profile-contract.md",
    "make sandbox-vm-profile-contract-check",
    "sandbox-vm-preflight-contract.md",
    "make sandbox-vm-preflight-contract-check",
    "sandbox/VM proof-of-concept review packet",
    "make sandbox-vm-poc-review-packet",
    "sandbox-vm-static-profile-preflight-plan.md",
    "make sandbox-vm-static-profile-preflight-plan-check",
    "sandbox-vm-static-profile-fixture-contract.md",
    "make sandbox-vm-static-profile-fixture-contract-check",
    "sandbox-vm-static-profile-negative-fixtures.md",
    "make sandbox-vm-static-profile-negative-fixtures-check",
    "sandbox-vm-static-preflight-implementation-decision.md",
    "make sandbox-vm-static-preflight-implementation-gate",
    "sandbox-vm-static-preflight-source-review.md",
    "make sandbox-vm-static-preflight-source-review-packet",
    "v3-sandbox-vm-static-preflight-internal-review.md",
    "static preflight lane remains local-preview fixture evidence only",
    "platform matrix",
    "mount/root posture",
    "network posture",
    "artifact ingress/egress",
    "failure/cleanup transcript",
    "promotion_status",
    "not_promoted",
    "Mission Control as the",
    "evidence viewer",
    "runtime sandbox control",
]

REQUIRED_BLOCKED_PHRASES = [
    "Mission Control execution authority",
    "Ithildin starting containers or VMs",
    "direct trusted-host writes",
    "production IAM",
    "runtime Postgres",
    "hosted telemetry by default",
    "claims of HIPAA, GLBA, SOX, GDPR",
]

FORBIDDEN_PHRASES = [
    "production-ready",
    "compliance-grade audit",
    "tamper-proof audit",
    "secure sandbox",
    "safe arbitrary tool use",
    "Mission Control may execute",
    "Ithildin starts containers",
    "trusted-host promotion is implemented",
    "before any real VM, local-model, importer, or preflight-runner runtime work begins",
]


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
    doc_rel = RUNWAY_DOC.relative_to(ROOT).as_posix()
    doc_path = repo_root / doc_rel
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    text = ""
    if not doc_path.exists():
        failures.append("enterprise-readiness runway doc is missing")
    else:
        text = doc_path.read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"enterprise-readiness runway is missing phrase: {phrase}")
        for phrase in REQUIRED_BLOCKED_PHRASES:
            if phrase not in text:
                failures.append(f"enterprise-readiness runway is missing blocked phrase: {phrase}")
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(f"enterprise-readiness runway contains forbidden phrase: {phrase}")

    if doc_rel not in review_docs.REVIEW_DOCS:
        failures.append("enterprise-readiness runway doc is missing from review docs")
    if doc_rel not in docs_site:
        failures.append("enterprise-readiness runway doc is missing from docs-site inputs")
    if "enterprise-readiness-runway-check:" not in makefile:
        failures.append("Make target is missing: enterprise-readiness-runway-check")
    if "enterprise-readiness-runway-check" not in release_check_body:
        failures.append("enterprise-readiness-runway-check is missing from release-check")
    if "enterprise readiness runway" not in readme.lower():
        failures.append("README is missing enterprise readiness runway reference")
    if "make sandbox-vm-poc-review-packet" not in readme:
        failures.append("README is missing sandbox/VM POC review packet command")
    if "make sandbox-vm-static-profile-preflight-plan-check" not in readme:
        failures.append("README is missing sandbox/VM static profile preflight plan command")
    if "make sandbox-vm-static-profile-fixture-contract-check" not in readme:
        failures.append("README is missing sandbox/VM static profile fixture contract command")
    if "make sandbox-vm-static-profile-negative-fixtures-check" not in readme:
        failures.append("README is missing sandbox/VM static profile negative fixture command")

    phases = [line for line in text.splitlines() if line.startswith("## Phase E")]
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "runway_doc": doc_rel,
        "phase_count": len(phases),
        "tool_count": 24,
        "selected_capability": "not selected",
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "production_identity_allowed": False,
        "compliance_claims_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise readiness runway check",
        f"valid: {str(report['valid']).lower()}",
        f"runway_doc: {report['runway_doc']}",
        f"phase_count: {report['phase_count']}",
        f"tool_count: {report['tool_count']}",
        f"selected_capability: {report['selected_capability']}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"production_identity_allowed: {str(report['production_identity_allowed']).lower()}",
        f"compliance_claims_allowed: {str(report['compliance_claims_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

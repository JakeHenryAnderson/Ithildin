"""Generate and validate optional observed v1.0 operator trial evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import demo_flow_result_check, review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs/codex/v1.0-operator-trial-observed.md"
DEFAULT_OUTPUT_DIR = ROOT / "var/review-packets/v1.0/operator-trial-observed"
DEMO_RESULT = ROOT / "var/review-packets/v3/operator-workbench/DEMO_FLOW_RESULT.md"
DEMO_RESULT_CHECK = ROOT / "var/review-packets/v3/demo-evidence/DEMO_FLOW_RESULT_CHECK.json"
REQUIRED_DOC_PHRASES = [
    "Status: optional observed local-preview operator trial evidence for the v1.0 RC path.",
    "make v1-operator-trial-observed",
    "make v1-operator-trial-observed-check",
    "var/review-packets/v1.0/operator-trial-observed/",
    "DEMO_FLOW_RESULT.md",
    "patch_apply_status: completed",
    "audit_verification_valid: true",
    "not_run",
    "This evidence only covers Ithildin-mediated demo activity.",
]
FORBIDDEN_RESULT_PHRASES = [
    "demo-secret-token",
    "TOKEN=",
    "PRIVATE KEY",
    "BEGIN OPENSSH",
    "BEGIN RSA",
    "diff --git",
    "\n@@ ",
    "\n--- ",
    "\n+++ ",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.check:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = build_observed_record(ROOT, Path(temp_dir) / "operator-trial-observed")
    else:
        report = build_observed_record(ROOT, args.output_dir)
    report["failures"].extend(_wiring_failures(ROOT))
    report["valid"] = not report["failures"]

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_observed_record(repo_root: Path, output_dir: Path) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    demo_check = demo_flow_result_check.build_report(DEMO_RESULT)
    parsed_result = _parse_demo_result(DEMO_RESULT) if DEMO_RESULT.exists() else {}
    result_present = bool(demo_check["result_present"])
    failures = _observed_failures(demo_check, parsed_result)
    report: dict[str, Any] = {
        "schema_version": "1",
        "valid": False,
        "generated_at": datetime.now(UTC).isoformat(),
        "repo_root": str(repo_root),
        "commit": _git(repo_root, ["rev-parse", "HEAD"]),
        "dirty": bool(_git(repo_root, ["status", "--short"])),
        "status": "observed" if result_present else "not_run",
        "result_present": result_present,
        "demo_result_path": DEMO_RESULT.relative_to(repo_root).as_posix(),
        "demo_result_check_path": DEMO_RESULT_CHECK.relative_to(repo_root).as_posix(),
        "demo_result_check": {
            "valid": demo_check["valid"],
            "status": demo_check["status"],
            "result_present": demo_check["result_present"],
            "failure_count": len(demo_check["failures"]),
        },
        "observed": _observed_summary(parsed_result),
        "artifact": _artifact_summary(DEMO_RESULT),
        "runtime_changes_allowed": False,
        "new_power_classes_allowed": False,
        "sandbox_orchestration_allowed": False,
        "siem_adapter_behavior_allowed": False,
        "production_identity_allowed": False,
        "public_security_product_positioning_allowed": False,
        "failures": failures,
    }
    report["valid"] = not report["failures"]
    (output_dir / "V1_OPERATOR_TRIAL_OBSERVED.md").write_text(
        render_observed_markdown(report), encoding="utf-8"
    )
    (output_dir / "v1-operator-trial-observed.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v1.0 observed operator trial evidence",
        f"valid: {str(report['valid']).lower()}",
        f"status: {report['status']}",
        f"commit: {report['commit']}",
        f"dirty: {str(report['dirty']).lower()}",
        f"result_present: {str(report['result_present']).lower()}",
        f"patch_apply_status: {report['observed'].get('patch_apply_status')}",
        f"audit_verification_valid: {report['observed'].get('audit_verification_valid')}",
        "runtime_changes_allowed: false",
        "new_power_classes_allowed: false",
        "sandbox_orchestration_allowed: false",
        "siem_adapter_behavior_allowed: false",
        "public_security_product_positioning_allowed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def render_observed_markdown(report: dict[str, Any]) -> str:
    observed = report["observed"]
    lines = [
        "# Ithildin v1.0 Observed Operator Trial Evidence",
        "",
        "Status: generated optional observed local-preview operator trial evidence.",
        "",
        "This generated artifact is secret-free. It does not start services, stop services, call",
        "governed tools, approve actions, mutate workspaces, manage sandbox lifecycle, create SIEM",
        "custody, certify compliance, or approve public/security-product positioning.",
        "",
        "## Current State",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- commit: `{report['commit']}`",
        f"- dirty: `{str(report['dirty']).lower()}`",
        f"- valid: `{str(report['valid']).lower()}`",
        f"- status: `{report['status']}`",
        f"- result_present: `{str(report['result_present']).lower()}`",
        f"- demo_result_path: `{report['demo_result_path']}`",
        "",
        "## Observed Demo Result",
        "",
        f"- scenario: `{observed.get('scenario', 'unavailable')}`",
        f"- demo_step: `{observed.get('demo_step', 'unavailable')}`",
        f"- proposal_id_present: `{str(bool(observed.get('proposal_id'))).lower()}`",
        f"- approval_id_present: `{str(bool(observed.get('approval_id'))).lower()}`",
        f"- patch_apply_status: `{observed.get('patch_apply_status', 'unavailable')}`",
        f"- candidate_run_ids_present: `{str(bool(observed.get('candidate_run_ids'))).lower()}`",
        f"- audit_verification_valid: `{observed.get('audit_verification_valid', 'unavailable')}`",
        f"- audit_event_count: `{observed.get('audit_event_count', 'unavailable')}`",
        f"- audit_head_hash_present: `{str(bool(observed.get('audit_head_hash'))).lower()}`",
        "- audit_export_head_hash_present: "
        f"`{str(bool(observed.get('audit_export_head_hash'))).lower()}`",
        "",
        "## Boundary",
        "",
        "This evidence only covers Ithildin-mediated demo activity. It does not prove OS",
        "isolation,",
        "host compromise resistance, VM/container security, SIEM custody, compliance automation,",
        "production security, external notarization, or activity outside Ithildin-mediated",
        "actions.",
        "",
    ]
    if report["failures"]:
        lines.extend(["## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
        lines.append("")
    return "\n".join(lines)


def _parse_demo_result(path: Path) -> dict[str, str]:
    parsed: dict[str, str] = {}
    if not path.exists():
        return parsed
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"- ([a-zA-Z0-9_]+): `([^`]*)`", line)
        if match:
            parsed[match.group(1)] = match.group(2)
    return parsed


def _observed_failures(demo_check: dict[str, Any], parsed: dict[str, str]) -> list[str]:
    failures = [f"demo-flow-result-check: {failure}" for failure in demo_check["failures"]]
    if not demo_check["result_present"]:
        return failures
    expected = {
        "scenario": "guided_local_demo",
        "demo_step": "mediated_patch_flow",
        "patch_apply_status": "completed",
        "audit_verification_valid": "true",
    }
    for key, value in expected.items():
        if parsed.get(key) != value:
            failures.append(f"demo result {key} is not {value}")
    for key, prefix in {
        "proposal_id": "patch_",
        "approval_id": "appr_",
        "audit_head_hash": "sha256:",
        "audit_export_head_hash": "sha256:",
    }.items():
        if not parsed.get(key, "").startswith(prefix):
            failures.append(f"demo result {key} is missing expected prefix {prefix}")
    if not parsed.get("candidate_run_ids", "").startswith("run_"):
        failures.append("demo result candidate_run_ids is missing a run_ identifier")
    if not parsed.get("audit_event_count", "").isdigit():
        failures.append("demo result audit_event_count is not numeric")
    if DEMO_RESULT.exists():
        text = DEMO_RESULT.read_text(encoding="utf-8")
        for phrase in FORBIDDEN_RESULT_PHRASES:
            if phrase in text:
                failures.append(f"demo result contains forbidden phrase: {phrase}")
    return failures


def _observed_summary(parsed: dict[str, str]) -> dict[str, str | None]:
    keys = [
        "scenario",
        "demo_step",
        "proposal_id",
        "approval_id",
        "patch_apply_status",
        "candidate_run_ids",
        "audit_verification_valid",
        "audit_event_count",
        "audit_head_hash",
        "audit_export_event_count",
        "audit_export_head_hash",
    ]
    return {key: parsed.get(key) for key in keys}


def _artifact_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "bytes": 0, "sha256": None}
    data = path.read_bytes()
    return {
        "exists": True,
        "bytes": len(data),
        "sha256": "sha256:" + hashlib.sha256(data).hexdigest(),
    }


def _wiring_failures(repo_root: Path) -> list[str]:
    failures: list[str] = []
    doc = DOC_PATH.read_text(encoding="utf-8") if DOC_PATH.exists() else ""
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    review_index = (repo_root / "docs/codex/review-docs-index.md").read_text(encoding="utf-8")
    release_check_body = makefile.partition("release-check:")[2]
    review_candidate_body = makefile.partition("review-candidate:")[2]
    if not DOC_PATH.exists():
        failures.append("observed operator trial doc is missing")
    for phrase in REQUIRED_DOC_PHRASES:
        if phrase not in doc:
            failures.append(f"observed operator trial doc is missing phrase: {phrase}")
    for target in ["v1-operator-trial-observed:", "v1-operator-trial-observed-check:"]:
        if target not in makefile:
            failures.append(f"Make target is missing: {target.rstrip(':')}")
    if "v1-operator-trial-observed-check" not in release_check_body:
        failures.append("v1-operator-trial-observed-check is missing from release-check")
    if "$(MAKE) v1-operator-trial-observed" not in review_candidate_body:
        failures.append("v1-operator-trial-observed is missing from review-candidate")
    for phrase in ["make v1-operator-trial-observed", "make v1-operator-trial-observed-check"]:
        if phrase not in readme:
            failures.append(f"README is missing phrase: {phrase}")
    rel_path = DOC_PATH.relative_to(repo_root).as_posix()
    if rel_path not in docs_site:
        failures.append("observed operator trial doc is missing from docs-site inputs")
    if rel_path not in review_docs.REVIEW_DOCS:
        failures.append("observed operator trial doc is missing from review docs")
    if "Ithildin v1.0 Observed Operator Trial Evidence" not in review_index:
        failures.append("review docs index is missing observed operator trial doc")
    return failures


def _git(repo_root: Path, args: list[str]) -> str:
    result = subprocess_run(["git", *args], repo_root)
    return result.strip()


def subprocess_run(command: list[str], cwd: Path) -> str:
    import subprocess

    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=True)
    return result.stdout


if __name__ == "__main__":
    raise SystemExit(main())

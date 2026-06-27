"""Create a local response inbox for all enterprise external-review lanes."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    enterprise_response_normalization_coverage,
    enterprise_response_status_board,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-response-inbox.md"
DOC_NAME = "enterprise-response-inbox.md"
DEFAULT_OUTPUT_DIR = Path("var/review-runs/enterprise-response-inbox")
INDEX_NAME = "ENTERPRISE_RESPONSE_INBOX.md"
JSON_NAME = "enterprise-response-inbox.json"
HASH_NAME = "enterprise-response-inbox-artifact-hashes.json"


class EnterpriseResponseInboxError(RuntimeError):
    """Raised when the all-lane response inbox cannot be built or validated."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.check:
        report = build_check_report(ROOT)
        print(render_check_report(report))
        return 0 if report["valid"] else 1

    try:
        output_dir = build_inbox(ROOT, args.output_dir)
    except EnterpriseResponseInboxError as exc:
        print(f"enterprise response inbox failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built enterprise response inbox at {output_dir}")
    return 0


def build_inbox(repo_root: Path, output_dir: Path) -> Path:
    _validate_repo_root(repo_root)
    status_report = enterprise_response_status_board.build_report(repo_root)
    coverage_report = enterprise_response_normalization_coverage.build_report(repo_root)
    if status_report.get("valid") is not True:
        raise EnterpriseResponseInboxError("enterprise response status board is not valid")
    if coverage_report.get("valid") is not True:
        raise EnterpriseResponseInboxError(
            "enterprise response normalization coverage is not valid"
        )
    if status_report.get("response_present_count") != 0:
        raise EnterpriseResponseInboxError(
            "normalized responses already exist; use lane-specific dry-run/closure gates"
        )
    if status_report.get("closure_ready_count") != 0:
        raise EnterpriseResponseInboxError(
            "a lane is closure-ready; do not generate a fresh all-lane inbox"
        )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    lanes = _lanes(repo_root)
    payload = _payload(repo_root, output_dir, lanes)
    (output_dir / INDEX_NAME).write_text(_render_index(payload), encoding="utf-8")
    (output_dir / JSON_NAME).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    for lane in lanes:
        (output_dir / lane["raw_response_file"]).write_text(
            _render_raw_placeholder(lane), encoding="utf-8"
        )
    hashes = _artifact_hashes(output_dir)
    (output_dir / HASH_NAME).write_text(
        json.dumps(hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output_dir


def build_check_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    try:
        output_dir = build_inbox(repo_root, DEFAULT_OUTPUT_DIR)
    except EnterpriseResponseInboxError as exc:
        failures.append(str(exc))
        output_dir = DEFAULT_OUTPUT_DIR

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    queue_doc = _read(repo_root / "docs/codex/enterprise-external-review-queue.md")
    status_board_doc = _read(repo_root / "docs/codex/enterprise-response-status-board.md")
    coverage_doc = _read(repo_root / "docs/codex/enterprise-response-normalization-coverage.md")
    dual_inbox_doc = _read(repo_root / "docs/codex/enterprise-dual-response-inbox.md")
    inbox_doc = _read(repo_root / DOC_REL)
    index_text = _read(output_dir / INDEX_NAME)
    json_text = _read(output_dir / JSON_NAME)
    hash_text = _read(output_dir / HASH_NAME)
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]

    try:
        payload = json.loads(json_text) if json_text else {}
    except json.JSONDecodeError:
        payload = {}
        failures.append("enterprise response inbox JSON is not valid JSON")
    try:
        hash_manifest = json.loads(hash_text) if hash_text else {"artifacts": []}
    except json.JSONDecodeError:
        hash_manifest = {"artifacts": []}
        failures.append("enterprise response inbox hash manifest is not valid JSON")

    artifact_hashes_match_files = _artifact_hashes_match_files(output_dir, hash_manifest)
    hashed_paths = {artifact.get("path") for artifact in hash_manifest.get("artifacts", [])}
    raw_files = {lane["raw_response_file"] for lane in payload.get("lanes", [])}

    for phrase in [
        "Status: generated response inbox for all enterprise external-review lanes.",
        "make enterprise-response-inbox",
        "make enterprise-response-inbox-check",
        "`ERG-003`",
        "`ERG-010`",
        "does not normalize responses",
        "does not mutate findings",
        "does not close any enterprise lane",
    ]:
        if phrase not in inbox_doc:
            failures.append(f"enterprise response inbox doc is missing phrase: {phrase}")
    for phrase in [
        "Enterprise Response Inbox",
        "RAW_RESPONSE_ERG-003.md",
        "RAW_RESPONSE_ERG-010.md",
        "EXT-PUBLIC-POSITIONING-###",
        "scripts/external_response_normalize.py",
        "make public-security-product-positioning-decision-closure-check",
        "runtime_changes_allowed: `false`",
        "closes_enterprise_lanes: `false`",
    ]:
        if phrase not in index_text:
            failures.append(f"generated enterprise response inbox is missing phrase: {phrase}")
    for phrase in [
        '"inbox_type": "ithildin.enterprise_response_inbox"',
        '"ERG-003"',
        '"ERG-010"',
        '"response_present_count": 0',
        '"closure_ready_count": 0',
        '"normalizes_responses": false',
        '"committed_findings_mutated": false',
        '"closes_enterprise_lanes": false',
    ]:
        if phrase not in json_text:
            failures.append(f"generated enterprise response inbox JSON is missing phrase: {phrase}")

    expected_paths = {INDEX_NAME, JSON_NAME, *raw_files}
    missing_hashes = sorted(expected_paths - hashed_paths)
    if missing_hashes:
        failures.append(
            "enterprise response inbox hash manifest is missing artifacts: "
            + ", ".join(missing_hashes)
        )
    if HASH_NAME in hashed_paths:
        failures.append("enterprise response inbox hash manifest must not hash itself")
    if not artifact_hashes_match_files:
        failures.append("enterprise response inbox artifact hashes do not match generated files")

    lanes = payload.get("lanes", [])
    if len(lanes) != 8:
        failures.append("enterprise response inbox must cover 8 lanes")
    if [lane.get("gap") for lane in lanes][:2] != ["ERG-003", "ERG-002"]:
        failures.append("enterprise response inbox must keep ERG-003 then ERG-002 first")
    for lane in lanes:
        if not str(lane.get("reviewed_packet_hash", "")).startswith("sha256:"):
            failures.append(f"{lane.get('gap', 'unknown')} reviewed packet hash is missing")
        if not str(lane.get("finding_namespace", "")).startswith("EXT-"):
            failures.append(f"{lane.get('gap', 'unknown')} finding namespace is missing")
        if lane.get("normalization_area") not in {
            "sandbox-vm-static-preflight",
            "mission-control-display",
            "trusted-host-promotion",
            "production-identity-storage",
            "siem-export-adapter",
            "compliance-mapping",
            "sandbox-vm-live-poc",
            "public-security-product-positioning",
        }:
            failures.append(f"{lane.get('gap', 'unknown')} normalization area is unexpected")

    if "enterprise-response-inbox:" not in makefile:
        failures.append("Make target is missing: enterprise-response-inbox")
    if "enterprise-response-inbox-check:" not in makefile:
        failures.append("Make target is missing: enterprise-response-inbox-check")
    if (
        "enterprise-response-inbox-check" not in release_check_body
        and "release-check: enterprise-response-inbox-check" not in makefile
    ):
        failures.append("enterprise-response-inbox-check is missing from release-check")
    if "$(MAKE) enterprise-response-inbox" not in review_candidate_body:
        failures.append("enterprise-response-inbox is missing from review-candidate")
    if "make enterprise-response-inbox" not in readme:
        failures.append("README is missing enterprise response inbox command")
    if DOC_REL not in docs_site:
        failures.append("enterprise response inbox is missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("enterprise response inbox is missing from review docs")
    if DOC_NAME not in review_index:
        failures.append("review-docs index is missing enterprise response inbox")
    if "enterprise-response-inbox-check" not in release_guardrails:
        failures.append("release guardrails do not require enterprise response inbox")
    if "enterprise-response-inbox" not in queue_doc:
        failures.append("enterprise queue is missing all-lane response inbox pointer")
    if "enterprise-response-inbox" not in status_board_doc:
        failures.append("enterprise response status board is missing all-lane inbox pointer")
    if "enterprise-response-inbox" not in coverage_doc:
        failures.append("enterprise response normalization coverage is missing inbox pointer")
    if "enterprise-response-inbox" not in dual_inbox_doc:
        failures.append("enterprise dual-response inbox is missing all-lane inbox pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "inbox_doc": DOC_REL,
        "output_dir": output_dir.as_posix(),
        "tool_count": 24,
        "lane_count": len(lanes),
        "response_present_count": payload.get("response_present_count", 0),
        "closure_ready_count": payload.get("closure_ready_count", 0),
        "artifact_hashes_match_files": artifact_hashes_match_files,
        "raw_response_placeholders": sorted(raw_files),
        "normalizes_responses": False,
        "writes_response_files": False,
        "committed_findings_mutated": False,
        "external_review_recorded": False,
        "closes_enterprise_lanes": False,
        "runtime_changes_allowed": False,
        "mission_control_runtime_allowed": False,
        "live_vm_inspection_allowed": False,
        "local_model_invocation_allowed": False,
        "sandbox_orchestration_allowed": False,
        "trusted_host_promotion_allowed": False,
        "siem_adapter_allowed": False,
        "compliance_automation_allowed": False,
        "public_security_product_positioning_allowed": False,
        "new_power_classes_allowed": False,
    }


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise response inbox check",
        f"valid: {str(report['valid']).lower()}",
        f"inbox_doc: {report['inbox_doc']}",
        f"output_dir: {report['output_dir']}",
        f"tool_count: {report['tool_count']}",
        f"lane_count: {report['lane_count']}",
        f"response_present_count: {report['response_present_count']}",
        f"closure_ready_count: {report['closure_ready_count']}",
        f"artifact_hashes_match_files: {str(report['artifact_hashes_match_files']).lower()}",
        f"normalizes_responses: {str(report['normalizes_responses']).lower()}",
        f"writes_response_files: {str(report['writes_response_files']).lower()}",
        f"committed_findings_mutated: {str(report['committed_findings_mutated']).lower()}",
        f"external_review_recorded: {str(report['external_review_recorded']).lower()}",
        f"closes_enterprise_lanes: {str(report['closes_enterprise_lanes']).lower()}",
        f"runtime_changes_allowed: {str(report['runtime_changes_allowed']).lower()}",
        "mission_control_runtime_allowed: "
        f"{str(report['mission_control_runtime_allowed']).lower()}",
        f"live_vm_inspection_allowed: {str(report['live_vm_inspection_allowed']).lower()}",
        f"local_model_invocation_allowed: {str(report['local_model_invocation_allowed']).lower()}",
        f"sandbox_orchestration_allowed: {str(report['sandbox_orchestration_allowed']).lower()}",
        f"trusted_host_promotion_allowed: {str(report['trusted_host_promotion_allowed']).lower()}",
        f"siem_adapter_allowed: {str(report['siem_adapter_allowed']).lower()}",
        f"compliance_automation_allowed: {str(report['compliance_automation_allowed']).lower()}",
        "public_security_product_positioning_allowed: "
        f"{str(report['public_security_product_positioning_allowed']).lower()}",
        f"new_power_classes_allowed: {str(report['new_power_classes_allowed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _lanes(repo_root: Path) -> list[dict[str, Any]]:
    # Keep this inventory independent from packet generation. The inbox is a lightweight
    # landing pad for review responses and should not rebuild lane packets as a side effect.
    path_by_gap = {
        "ERG-003": "var/review-packets/v3/sandbox-vm-static-preflight-external-review",
        "ERG-002": "var/review-packets/v3/mission-control-display-external-review",
        "ERG-005": "var/review-packets/v3/trusted-host-promotion-external-review",
        "ERG-006/ERG-007": "var/review-packets/v3/production-identity-storage-external-review",
        "ERG-008": "var/review-packets/v3/siem-export-adapter-external-review",
        "ERG-009": "var/review-packets/v3/compliance-mapping-external-review",
        "ERG-004": "var/review-packets/v3/sandbox-vm-live-poc-external-review",
        "ERG-010": "var/review-packets/v3/public-positioning-external-review",
    }
    descriptors = [
        _lane(
            gap="ERG-003",
            name="static sandbox/VM preflight",
            area="sandbox-vm-static-preflight",
            namespace="EXT-SVP-###",
            response_kit="var/review-packets/v3/sandbox-vm-static-preflight-response-kit",
            intake_doc="docs/codex/sandbox-vm-static-preflight-external-response-intake.md",
            dry_run="make sandbox-vm-static-preflight-response-dry-run",
            closure_gate="make sandbox-vm-static-preflight-disposition-closure-check",
            packet_path=path_by_gap["ERG-003"],
        ),
        _lane(
            gap="ERG-002",
            name="Mission Control display/import planning",
            area="mission-control-display",
            namespace="EXT-MC-DISPLAY-###",
            response_kit="var/review-packets/v3/mission-control-display-response-kit",
            intake_doc="docs/codex/mission-control-display-external-response-intake.md",
            dry_run="make mission-control-display-response-dry-run",
            closure_gate="make mission-control-display-disposition-closure-check",
            packet_path=path_by_gap["ERG-002"],
        ),
        _lane(
            gap="ERG-005",
            name="trusted-host promotion design review",
            area="trusted-host-promotion",
            namespace="EXT-TRUSTED-HOST-###",
            response_kit="var/review-packets/v3/trusted-host-promotion-response-kit",
            intake_doc="docs/codex/trusted-host-promotion-external-response-intake.md",
            dry_run="make trusted-host-promotion-response-dry-run",
            closure_gate="make trusted-host-promotion-disposition-closure-check",
            packet_path=path_by_gap["ERG-005"],
        ),
        _lane(
            gap="ERG-006-ERG-007",
            name="production identity and storage architecture",
            area="production-identity-storage",
            namespace="EXT-PROD-IAM-STORAGE-###",
            response_kit="var/review-packets/v3/production-identity-storage-response-kit",
            intake_doc="docs/codex/production-identity-storage-external-response-intake.md",
            dry_run="make production-identity-storage-response-dry-run",
            closure_gate="make production-identity-storage-disposition-closure-check",
            packet_path=path_by_gap["ERG-006/ERG-007"],
        ),
        _lane(
            gap="ERG-008",
            name="SIEM export adapter architecture",
            area="siem-export-adapter",
            namespace="EXT-SIEM-ADAPTER-###",
            response_kit="var/review-packets/v3/siem-export-adapter-response-kit",
            intake_doc="docs/codex/siem-export-adapter-external-response-intake.md",
            dry_run="make siem-export-adapter-response-dry-run",
            closure_gate="make siem-export-adapter-disposition-closure-check",
            packet_path=path_by_gap["ERG-008"],
        ),
        _lane(
            gap="ERG-009",
            name="compliance mapping support architecture",
            area="compliance-mapping",
            namespace="EXT-COMPLIANCE-MAPPING-###",
            response_kit="var/review-packets/v3/compliance-mapping-response-kit",
            intake_doc="docs/codex/compliance-mapping-external-response-intake.md",
            dry_run="make compliance-mapping-response-dry-run",
            closure_gate="make compliance-mapping-disposition-closure-check",
            packet_path=path_by_gap["ERG-009"],
        ),
        _lane(
            gap="ERG-004",
            name="live sandbox/VM worker POC decision",
            area="sandbox-vm-live-poc",
            namespace="EXT-LIVE-POC-###",
            response_kit="var/review-packets/v3/sandbox-vm-live-poc-response-kit",
            intake_doc="docs/codex/sandbox-vm-live-poc-external-response-intake.md",
            dry_run="make sandbox-vm-live-poc-response-dry-run",
            closure_gate="make sandbox-vm-live-poc-decision-closure-check",
            packet_path=path_by_gap["ERG-004"],
        ),
        _lane(
            gap="ERG-010",
            name="public/security-product positioning claim review",
            area="public-security-product-positioning",
            namespace="EXT-PUBLIC-POSITIONING-###",
            response_kit="var/review-packets/v3/public-security-product-positioning-response-kit",
            intake_doc="docs/codex/public-security-product-positioning-decision-intake.md",
            dry_run=None,
            closure_gate="make public-security-product-positioning-decision-closure-check",
            packet_path=path_by_gap["ERG-010"],
        ),
    ]
    for lane in descriptors:
        lane["reviewed_packet_hash"] = _packet_hash(repo_root, lane["reviewed_packet_path"])
    return descriptors


def _lane(
    *,
    gap: str,
    name: str,
    area: str,
    namespace: str,
    response_kit: str,
    intake_doc: str,
    dry_run: str | None,
    closure_gate: str,
    packet_path: str,
) -> dict[str, Any]:
    raw_name = "RAW_RESPONSE_" + gap.replace("/", "-").replace(" ", "-") + ".md"
    normalized_dir = area
    return {
        "gap": gap,
        "name": name,
        "normalization_area": area,
        "finding_namespace": namespace,
        "raw_response_file": raw_name,
        "reviewed_packet_hash": "",
        "reviewed_packet_path": packet_path,
        "normalized_response_path": f"var/review-runs/{normalized_dir}/normalized-response.json",
        "source_access": "source-level",
        "intake_doc": intake_doc,
        "dry_run": dry_run,
        "closure_gate": closure_gate,
        "response_kit": response_kit,
    }


def _payload(repo_root: Path, output_dir: Path, lanes: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "inbox_type": "ithildin.enterprise_response_inbox",
        "commit": _git(repo_root, ["rev-parse", "HEAD"]),
        "dirty": bool(_git(repo_root, ["status", "--short"])),
        "tool_count": 24,
        "selected_capability": "not selected",
        "output_dir": output_dir.as_posix(),
        "response_present_count": 0,
        "closure_ready_count": 0,
        "lanes": lanes,
        "blocked_boundaries": {
            "normalizes_responses": False,
            "writes_response_files": False,
            "committed_findings_mutated": False,
            "external_review_recorded": False,
            "closes_enterprise_lanes": False,
            "runtime_changes_allowed": False,
            "mission_control_runtime_allowed": False,
            "live_vm_inspection_allowed": False,
            "local_model_invocation_allowed": False,
            "sandbox_orchestration_allowed": False,
            "trusted_host_promotion_allowed": False,
            "siem_adapter_allowed": False,
            "compliance_automation_allowed": False,
            "public_security_product_positioning_allowed": False,
            "new_power_classes_allowed": False,
        },
    }


def _render_index(payload: dict[str, Any]) -> str:
    lane_sections = "\n".join(_render_lane_section(lane) for lane in payload["lanes"])
    blocked = "\n".join(
        f"- {name}: `{str(value).lower()}`"
        for name, value in payload["blocked_boundaries"].items()
    )
    return f"""# Enterprise Response Inbox

Generated response landing pad for all enterprise external-review lanes.

Reviewed commit for the inbox commands: `{payload['commit']}`

Dirty state when generated: `{str(payload['dirty']).lower()}`

Tool count remains `{payload['tool_count']}`.

Current selected capability: `{payload['selected_capability']}`.

This inbox creates raw-response placeholders and exact normalization commands for all enterprise
lanes. It does not normalize responses, write normalized response files, mutate committed findings,
record external review, close any enterprise lane, or approve runtime behavior.

## Use Order

1. Paste reviewer text into the matching raw-response placeholder.
2. Run that lane's `scripts/external_response_normalize.py` command.
3. Run the lane-specific dry-run command when one exists.
4. Run the lane-specific closure gate.
5. Commit a later triage/update record only if the closure gate proves the response is favorable.

{lane_sections}

## Boundary Flags

{blocked}

## Regeneration Commands

```sh
make enterprise-response-normalization-coverage
make enterprise-review-send-readiness
make enterprise-response-inbox
make enterprise-response-inbox-check
make enterprise-response-status-board
```
"""


def _render_lane_section(lane: dict[str, Any]) -> str:
    dry_run = (
        f"```sh\n{lane['dry_run']}\n```"
        if lane["dry_run"]
        else (
            "No separate dry-run target exists for this lane; use the closure gate after "
            "normalization."
        )
    )
    return f"""## {lane['gap']}: {lane['name']}

Raw-response placeholder: `{lane['raw_response_file']}`

Finding namespace: `{lane['finding_namespace']}`

Reviewed packet: `{lane['reviewed_packet_path']}`

Reviewed packet hash: `{lane['reviewed_packet_hash']}`

Response kit: `{lane['response_kit']}`

Intake doc: `{lane['intake_doc']}`

Normalize after pasting a real response:

```sh
uv run python scripts/external_response_normalize.py \\
  {DEFAULT_OUTPUT_DIR.as_posix()}/{lane['raw_response_file']} \\
  --reviewer "REVIEWER NAME" \\
  --reviewer-type "ai_external" \\
  --source-access {lane['source_access']} \\
  --reviewed-commit "{_shell_commit_placeholder()}" \\
  --reviewed-packet-hash "{lane['reviewed_packet_hash']}" \\
  --area {lane['normalization_area']} \\
  --output {lane['normalized_response_path']}
```

Dry run after normalization:

{dry_run}

Closure gate after dry run:

```sh
{lane['closure_gate']}
```
"""


def _render_raw_placeholder(lane: dict[str, Any]) -> str:
    finding_id = lane["finding_namespace"].replace("###", "001")
    table_header = (
        "| Finding ID | Severity | Area | Affected files/functions | "
        "Blocking status | Disposition | Recommended fix |"
    )
    table_row = (
        f"| {finding_id} | critical/high/medium/low/informational | "
        f"{lane['normalization_area']} | path/function | "
        "blocking/should-fix/later/advisory | open | fix summary |"
    )
    return f"""# Raw External Review Response Placeholder: {lane['gap']}

Paste the unmodified reviewer response for `{lane['gap']}` here, then run the normalization command
from `ENTERPRISE_RESPONSE_INBOX.md`.

Expected finding namespace: `{lane['finding_namespace']}`

If the reviewer reports no actionable findings, the response must explicitly say that no
implementation findings were found and must state whether the lane can close for the relevant
local-preview boundary. Do not edit this placeholder into a committed review record.

## Finding Table Shape

{table_header}
| --- | --- | --- | --- | --- | --- | --- |
{table_row}
"""


def _packet_hash(repo_root: Path, packet_path: str) -> str:
    packet_dir = repo_root / packet_path
    if not packet_dir.is_dir():
        raise EnterpriseResponseInboxError(f"review packet path is missing: {packet_path}")
    manifests = sorted(packet_dir.glob("*artifact-hashes.json"))
    if not manifests:
        manifests = sorted(packet_dir.glob("*hashes.json"))
    if not manifests:
        raise EnterpriseResponseInboxError(f"review packet hash manifest is missing: {packet_path}")
    return "sha256:" + hashlib.sha256(manifests[0].read_bytes()).hexdigest()


def _shell_commit_placeholder() -> str:
    return "$(git rev-parse HEAD)"


def _validate_repo_root(repo_root: Path) -> None:
    missing = [
        marker
        for marker in ["pyproject.toml", "Makefile", "tool-manifests.lock.json"]
        if not (repo_root / marker).exists()
    ]
    if missing:
        raise EnterpriseResponseInboxError(
            "must be run from the Ithildin repo root; missing " + ", ".join(missing)
        )


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


def _artifact_hashes(output_dir: Path) -> dict[str, Any]:
    artifacts = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name == HASH_NAME:
            continue
        rel = path.relative_to(output_dir).as_posix()
        data = path.read_bytes()
        artifacts.append(
            {
                "path": rel,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return {
        "schema_version": "1",
        "artifacts": artifacts,
        "artifact_count": len(artifacts),
        "hash_manifest_self_hashed": False,
    }


def _artifact_hashes_match_files(output_dir: Path, hashes: dict[str, Any]) -> bool:
    for artifact in hashes.get("artifacts", []):
        path = output_dir / artifact.get("path", "")
        if not path.is_file():
            return False
        data = path.read_bytes()
        if artifact.get("bytes") != len(data):
            return False
        if artifact.get("sha256") != hashlib.sha256(data).hexdigest():
            return False
    return True


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())

"""Create a local response inbox for the current dual enterprise-review handoff."""

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
    enterprise_dual_response_readiness,
    enterprise_dual_review_outbox,
    mission_control_display_external_review_bundle,
    review_docs,
    sandbox_vm_static_preflight_disposition_closure_check,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-dual-response-inbox.md"
DOC_NAME = "enterprise-dual-response-inbox.md"
DEFAULT_OUTPUT_DIR = Path("var/review-runs/enterprise-dual-response-inbox")
INDEX_NAME = "ENTERPRISE_DUAL_RESPONSE_INBOX.md"
JSON_NAME = "enterprise-dual-response-inbox.json"
HASH_NAME = "enterprise-dual-response-inbox-artifact-hashes.json"
ERG003_RAW = "RAW_RESPONSE_ERG-003.md"
ERG002_RAW = "RAW_RESPONSE_ERG-002.md"


class EnterpriseDualResponseInboxError(RuntimeError):
    """Raised when the response inbox cannot be built or validated."""


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
    except EnterpriseDualResponseInboxError as exc:
        print(f"enterprise dual-response inbox failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built enterprise dual-response inbox at {output_dir}")
    return 0


def build_inbox(repo_root: Path, output_dir: Path) -> Path:
    _validate_repo_root(repo_root)
    outbox_report = enterprise_dual_review_outbox.build_check_report(repo_root)
    readiness_report = enterprise_dual_response_readiness.build_report(repo_root)
    if outbox_report.get("valid") is not True:
        raise EnterpriseDualResponseInboxError("enterprise dual-review outbox is not valid")
    if readiness_report.get("valid") is not True:
        raise EnterpriseDualResponseInboxError("enterprise dual-response readiness is not valid")
    if readiness_report.get("response_present_count") != 0:
        raise EnterpriseDualResponseInboxError(
            "normalized responses already exist; use lane-specific dry-run/closure gates"
        )
    if readiness_report.get("closure_ready_count") != 0:
        raise EnterpriseDualResponseInboxError(
            "a lane is closure-ready; do not generate a fresh intake inbox"
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
    except EnterpriseDualResponseInboxError as exc:
        failures.append(str(exc))
        output_dir = DEFAULT_OUTPUT_DIR

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    dual_handoff_doc = _read(repo_root / "docs/codex/enterprise-dual-review-handoff.md")
    readiness_doc = _read(repo_root / "docs/codex/enterprise-dual-response-readiness.md")
    outbox_doc = _read(repo_root / "docs/codex/enterprise-dual-review-outbox.md")
    status_board_doc = _read(repo_root / "docs/codex/enterprise-response-status-board.md")
    queue_doc = _read(repo_root / "docs/codex/enterprise-external-review-queue.md")
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
        failures.append("dual response inbox JSON is not valid JSON")
    try:
        hash_manifest = json.loads(hash_text) if hash_text else {"artifacts": []}
    except json.JSONDecodeError:
        hash_manifest = {"artifacts": []}
        failures.append("dual response inbox hash manifest is not valid JSON")

    artifact_hashes_match_files = _artifact_hashes_match_files(output_dir, hash_manifest)
    hashed_paths = {artifact.get("path") for artifact in hash_manifest.get("artifacts", [])}

    for phrase in [
        "Status: generated response inbox for the current dual enterprise review handoff.",
        "make enterprise-dual-response-inbox",
        "make enterprise-dual-response-inbox-check",
        "`ERG-003`",
        "`ERG-002`",
        "does not normalize responses",
        "does not mutate findings",
        "does not close either lane",
    ]:
        if phrase not in inbox_doc:
            failures.append(f"dual response inbox doc is missing phrase: {phrase}")
    for phrase in [
        "Enterprise Dual Response Inbox",
        ERG003_RAW,
        ERG002_RAW,
        "EXT-SVP-###",
        "EXT-MC-DISPLAY-###",
        "scripts/external_response_normalize.py",
        "make sandbox-vm-static-preflight-response-dry-run",
        "make mission-control-display-response-dry-run",
        "runtime_changes_allowed: `false`",
        "closes_erg_003: `false`",
        "closes_erg_002: `false`",
    ]:
        if phrase not in index_text:
            failures.append(f"generated dual response inbox is missing phrase: {phrase}")
    for phrase in [
        '"inbox_type": "ithildin.enterprise_dual_response_inbox"',
        '"ERG-003"',
        '"ERG-002"',
        '"response_present_count": 0',
        '"closure_ready_count": 0',
        '"normalizes_responses": false',
        '"committed_findings_mutated": false',
        '"closes_erg_003": false',
        '"closes_erg_002": false',
    ]:
        if phrase not in json_text:
            failures.append(f"generated dual response inbox JSON is missing phrase: {phrase}")

    expected_paths = {INDEX_NAME, JSON_NAME, ERG003_RAW, ERG002_RAW}
    missing_hashes = sorted(expected_paths - hashed_paths)
    if missing_hashes:
        failures.append(
            "dual response inbox hash manifest is missing artifacts: "
            + ", ".join(missing_hashes)
        )
    if HASH_NAME in hashed_paths:
        failures.append("dual response inbox hash manifest must not hash itself")
    if not artifact_hashes_match_files:
        failures.append("dual response inbox artifact hashes do not match generated files")

    if payload.get("recommended_gaps") != ["ERG-003", "ERG-002"]:
        failures.append("dual response inbox recommended gaps are not ERG-003 then ERG-002")
    for lane in payload.get("lanes", []):
        if not str(lane.get("reviewed_packet_hash", "")).startswith("sha256:"):
            failures.append(f"{lane.get('gap', 'unknown')} reviewed packet hash is missing")
        if lane.get("normalization_area") not in {
            "sandbox-vm-static-preflight",
            "mission-control-display",
        }:
            failures.append(f"{lane.get('gap', 'unknown')} normalization area is unexpected")

    if "enterprise-dual-response-inbox:" not in makefile:
        failures.append("Make target is missing: enterprise-dual-response-inbox")
    if "enterprise-dual-response-inbox-check:" not in makefile:
        failures.append("Make target is missing: enterprise-dual-response-inbox-check")
    if "enterprise-dual-response-inbox-check" not in release_check_body:
        failures.append("enterprise-dual-response-inbox-check is missing from release-check")
    if "$(MAKE) enterprise-dual-response-inbox" not in review_candidate_body:
        failures.append("enterprise-dual-response-inbox is missing from review-candidate")
    if "make enterprise-dual-response-inbox" not in readme:
        failures.append("README is missing enterprise dual-response inbox command")
    if DOC_REL not in docs_site:
        failures.append("enterprise dual-response inbox is missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("enterprise dual-response inbox is missing from review docs")
    if DOC_NAME not in review_index:
        failures.append("review-docs index is missing enterprise dual-response inbox")
    if "enterprise-dual-response-inbox-check" not in release_guardrails:
        failures.append("release guardrails do not require enterprise dual-response inbox")
    if "enterprise-dual-response-inbox" not in dual_handoff_doc:
        failures.append("dual-review handoff doc is missing response inbox pointer")
    if "enterprise-dual-response-inbox" not in readiness_doc:
        failures.append("dual-response readiness doc is missing response inbox pointer")
    if "enterprise-dual-response-inbox" not in outbox_doc:
        failures.append("dual-review outbox doc is missing response inbox pointer")
    if "enterprise-dual-response-inbox" not in status_board_doc:
        failures.append("enterprise response status board is missing response inbox pointer")
    if "enterprise-dual-response-inbox" not in queue_doc:
        failures.append("enterprise queue is missing dual-response inbox pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "inbox_doc": DOC_REL,
        "output_dir": output_dir.as_posix(),
        "recommended_gaps": ["ERG-003", "ERG-002"],
        "tool_count": 24,
        "response_present_count": payload.get("response_present_count", 0),
        "closure_ready_count": payload.get("closure_ready_count", 0),
        "lane_count": len(payload.get("lanes", [])),
        "artifact_hashes_match_files": artifact_hashes_match_files,
        "raw_response_placeholders": [ERG003_RAW, ERG002_RAW],
        "normalizes_responses": False,
        "committed_findings_mutated": False,
        "external_review_recorded": False,
        "closes_erg_003": False,
        "closes_erg_002": False,
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
        "Ithildin enterprise dual-response inbox check",
        f"valid: {str(report['valid']).lower()}",
        f"inbox_doc: {report['inbox_doc']}",
        f"output_dir: {report['output_dir']}",
        "recommended_gaps: " + ", ".join(report["recommended_gaps"]),
        f"tool_count: {report['tool_count']}",
        f"lane_count: {report['lane_count']}",
        f"response_present_count: {report['response_present_count']}",
        f"closure_ready_count: {report['closure_ready_count']}",
        f"artifact_hashes_match_files: {str(report['artifact_hashes_match_files']).lower()}",
        f"normalizes_responses: {str(report['normalizes_responses']).lower()}",
        f"committed_findings_mutated: {str(report['committed_findings_mutated']).lower()}",
        f"external_review_recorded: {str(report['external_review_recorded']).lower()}",
        f"closes_erg_003: {str(report['closes_erg_003']).lower()}",
        f"closes_erg_002: {str(report['closes_erg_002']).lower()}",
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
    static_preflight = sandbox_vm_static_preflight_disposition_closure_check
    erg003_hash = static_preflight.current_reviewed_packet_hash(repo_root)
    erg002_manifest = (
        repo_root
        / mission_control_display_external_review_bundle.DEFAULT_OUTPUT_DIR
        / mission_control_display_external_review_bundle.HASH_MANIFEST
    )
    if not erg002_manifest.is_file():
        raise EnterpriseDualResponseInboxError(
            "ERG-002 external-review artifact hash manifest is missing"
        )
    erg002_hash = "sha256:" + hashlib.sha256(erg002_manifest.read_bytes()).hexdigest()
    return [
        {
            "gap": "ERG-003",
            "name": "static sandbox/VM preflight",
            "normalization_area": "sandbox-vm-static-preflight",
            "finding_namespace": "EXT-SVP-###",
            "raw_response_file": ERG003_RAW,
            "reviewed_packet_hash": erg003_hash,
            "normalized_response_path": (
                "var/review-runs/sandbox-vm-static-preflight/normalized-response.json"
            ),
            "source_access": "source-level",
            "intake_doc": "docs/codex/sandbox-vm-static-preflight-external-response-intake.md",
            "dry_run": "make sandbox-vm-static-preflight-response-dry-run",
            "closure_gate": "make sandbox-vm-static-preflight-disposition-closure-check",
            "response_kit": "var/review-packets/v3/sandbox-vm-static-preflight-response-kit",
        },
        {
            "gap": "ERG-002",
            "name": "Mission Control display/import planning",
            "normalization_area": "mission-control-display",
            "finding_namespace": "EXT-MC-DISPLAY-###",
            "raw_response_file": ERG002_RAW,
            "reviewed_packet_hash": erg002_hash,
            "normalized_response_path": (
                "var/review-runs/mission-control-display/normalized-response.json"
            ),
            "source_access": "source-level",
            "intake_doc": "docs/codex/mission-control-display-external-response-intake.md",
            "dry_run": "make mission-control-display-response-dry-run",
            "closure_gate": "make mission-control-display-disposition-closure-check",
            "response_kit": "var/review-packets/v3/mission-control-display-response-kit",
        },
    ]


def _payload(repo_root: Path, output_dir: Path, lanes: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "inbox_type": "ithildin.enterprise_dual_response_inbox",
        "commit": _git(repo_root, ["rev-parse", "HEAD"]),
        "dirty": bool(_git(repo_root, ["status", "--short"])),
        "tool_count": 24,
        "selected_capability": "not selected",
        "output_dir": output_dir.as_posix(),
        "recommended_gaps": ["ERG-003", "ERG-002"],
        "response_present_count": 0,
        "closure_ready_count": 0,
        "lanes": lanes,
        "blocked_boundaries": {
            "normalizes_responses": False,
            "committed_findings_mutated": False,
            "external_review_recorded": False,
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
            "closes_erg_003": False,
            "closes_erg_002": False,
        },
    }


def _render_index(payload: dict[str, Any]) -> str:
    lane_sections = "\n".join(_render_lane_section(lane) for lane in payload["lanes"])
    blocked = "\n".join(
        f"- {name}: `{str(value).lower()}`"
        for name, value in payload["blocked_boundaries"].items()
    )
    return f"""# Enterprise Dual Response Inbox

Generated response landing pad for the current `ERG-003` and `ERG-002` enterprise review handoff.

Reviewed commit for the inbox commands: `{payload['commit']}`

Dirty state when generated: `{str(payload['dirty']).lower()}`

Tool count remains `{payload['tool_count']}`.

Current selected capability: `{payload['selected_capability']}`.

This inbox creates raw-response placeholders and exact normalization commands. It does not
normalize responses, mutate committed findings, record external review, close either lane, or
approve runtime behavior.

## Use Order

1. Paste reviewer text into the matching raw-response placeholder.
2. Run that lane's `scripts/external_response_normalize.py` command.
3. Run the lane-specific dry-run command.
4. Run the lane-specific closure gate.
5. Commit a later triage/update record only if the closure gate proves the response is favorable.

{lane_sections}

## Boundary Flags

{blocked}

## Regeneration Commands

```sh
make enterprise-dual-review-outbox
make enterprise-dual-response-inbox
make enterprise-dual-response-inbox-check
make enterprise-dual-response-readiness
make enterprise-response-status-board
```
"""


def _render_lane_section(lane: dict[str, Any]) -> str:
    return f"""## {lane['gap']}: {lane['name']}

Raw-response placeholder: `{lane['raw_response_file']}`

Finding namespace: `{lane['finding_namespace']}`

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

```sh
{lane['dry_run']}
```

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
from `ENTERPRISE_DUAL_RESPONSE_INBOX.md`.

Expected finding namespace: `{lane['finding_namespace']}`

If the reviewer reports no actionable findings, the response must explicitly say that no
implementation findings were found and must state whether the lane can close for the relevant
local-preview boundary. Do not edit this placeholder into a committed review record.

## Finding Table Shape

{table_header}
| --- | --- | --- | --- | --- | --- | --- |
{table_row}
"""


def _shell_commit_placeholder() -> str:
    return "$(git rev-parse HEAD)"


def _validate_repo_root(repo_root: Path) -> None:
    missing = [
        marker
        for marker in ["pyproject.toml", "Makefile", "tool-manifests.lock.json"]
        if not (repo_root / marker).exists()
    ]
    if missing:
        raise EnterpriseDualResponseInboxError(
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

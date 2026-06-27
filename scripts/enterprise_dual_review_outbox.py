"""Build a send-ready outbox for the current dual enterprise review packets."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import enterprise_dual_review_handoff, review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-dual-review-outbox.md"
DOC_NAME = "enterprise-dual-review-outbox.md"
DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/enterprise-dual-review-outbox")
INDEX_NAME = "ENTERPRISE_DUAL_REVIEW_OUTBOX_INDEX.md"
JSON_NAME = "enterprise-dual-review-outbox.json"
HASH_NAME = "enterprise-dual-review-outbox-artifact-hashes.json"


class EnterpriseDualReviewOutboxError(RuntimeError):
    """Raised when the dual review outbox cannot be built or validated."""


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
        output_dir = build_outbox(ROOT, args.output_dir)
    except EnterpriseDualReviewOutboxError as exc:
        print(f"enterprise dual-review outbox failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built enterprise dual-review outbox at {output_dir}")
    return 0


def build_outbox(repo_root: Path, output_dir: Path) -> Path:
    _validate_repo_root(repo_root)
    handoff_dir = enterprise_dual_review_handoff.build_handoff(
        repo_root, enterprise_dual_review_handoff.DEFAULT_OUTPUT_DIR
    )
    handoff_payload = json.loads(
        (handoff_dir / enterprise_dual_review_handoff.JSON_NAME).read_text(encoding="utf-8")
    )
    packets = handoff_payload["packets"]

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    copied_packets = []
    for packet in packets:
        copied_packets.append(_copy_packet(repo_root, output_dir, packet))

    payload = _outbox_payload(
        commit=handoff_payload["commit"],
        dirty=handoff_payload["dirty"],
        copied_packets=copied_packets,
    )
    (output_dir / INDEX_NAME).write_text(_render_index(payload), encoding="utf-8")
    (output_dir / JSON_NAME).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    hashes = _artifact_hashes(output_dir)
    (output_dir / HASH_NAME).write_text(
        json.dumps(hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output_dir


def build_check_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    try:
        output_dir = build_outbox(repo_root, DEFAULT_OUTPUT_DIR)
    except EnterpriseDualReviewOutboxError as exc:
        failures.append(str(exc))
        output_dir = DEFAULT_OUTPUT_DIR

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    queue = _read(repo_root / "docs/codex/enterprise-external-review-queue.md")
    handoff_doc = _read(repo_root / "docs/codex/enterprise-dual-review-handoff.md")
    outbox_doc = _read(repo_root / DOC_REL)
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]
    index_text = _read(output_dir / INDEX_NAME)
    json_text = _read(output_dir / JSON_NAME)
    hash_text = _read(output_dir / HASH_NAME)

    try:
        hash_manifest = json.loads(hash_text) if hash_text else {"artifacts": []}
    except json.JSONDecodeError:
        hash_manifest = {"artifacts": []}
        failures.append("dual review outbox hash manifest is not valid JSON")
    artifact_hashes_match_files = _artifact_hashes_match_files(output_dir, hash_manifest)
    hashed_paths = {artifact.get("path") for artifact in hash_manifest.get("artifacts", [])}

    for phrase in [
        "Status: generated send-ready outbox for the current two enterprise reviews.",
        "make enterprise-dual-review-outbox",
        "make enterprise-dual-review-outbox-check",
        "`ERG-003`",
        "`ERG-002`",
        "does not record external review",
        "does not close either lane",
    ]:
        if phrase not in outbox_doc:
            failures.append(f"outbox doc is missing phrase: {phrase}")
    for phrase in [
        "Enterprise Dual Review Outbox",
        "Send-ready copy root",
        "ERG-003",
        "ERG-002",
        "runtime_changes_allowed: `false`",
        "closes_erg_003: `false`",
        "closes_erg_002: `false`",
    ]:
        if phrase not in index_text:
            failures.append(f"generated outbox index is missing phrase: {phrase}")
    for phrase in [
        '"outbox_type": "ithildin.enterprise_dual_review_outbox"',
        '"ERG-003"',
        '"ERG-002"',
        '"runtime_changes_allowed": false',
        '"closes_erg_003": false',
        '"closes_erg_002": false',
    ]:
        if phrase not in json_text:
            failures.append(f"generated outbox JSON is missing phrase: {phrase}")

    expected_paths = {
        INDEX_NAME,
        JSON_NAME,
        "ERG-003/00_SANDBOX_VM_STATIC_PREFLIGHT_EXTERNAL_REVIEW_INDEX.md",
        "ERG-003/01_SANDBOX_VM_STATIC_PREFLIGHT_EXTERNAL_REVIEW_PROMPT.md",
        "ERG-003/sandbox-vm-static-preflight-external-review-artifact-hashes.json",
        "ERG-002/00_MISSION_CONTROL_DISPLAY_EXTERNAL_REVIEW_INDEX.md",
        "ERG-002/01_MISSION_CONTROL_DISPLAY_EXTERNAL_REVIEW_PROMPT.md",
        "ERG-002/mission-control-display-external-review-artifact-hashes.json",
    }
    missing_hashes = sorted(expected_paths - hashed_paths)
    if missing_hashes:
        failures.append("outbox hash manifest is missing artifacts: " + ", ".join(missing_hashes))
    if HASH_NAME in hashed_paths:
        failures.append("outbox hash manifest must not hash itself")
    if not artifact_hashes_match_files:
        failures.append("outbox artifact hashes do not match generated files")

    required_wiring = {
        "Make target": "enterprise-dual-review-outbox:",
        "Check target": "enterprise-dual-review-outbox-check:",
        "Release check": "enterprise-dual-review-outbox-check",
        "Review candidate": "$(MAKE) enterprise-dual-review-outbox",
        "README command": "make enterprise-dual-review-outbox",
        "Queue pointer": "enterprise-dual-review-outbox.md",
        "Dual handoff pointer": "enterprise-dual-review-outbox",
        "Docs site": DOC_REL,
        "Review docs": DOC_REL,
        "Review index": DOC_NAME,
        "Release guardrails": "enterprise-dual-review-outbox-check",
    }
    if required_wiring["Make target"] not in makefile:
        failures.append("Make target is missing: enterprise-dual-review-outbox")
    if required_wiring["Check target"] not in makefile:
        failures.append("Make target is missing: enterprise-dual-review-outbox-check")
    if required_wiring["Release check"] not in release_check_body:
        failures.append("enterprise-dual-review-outbox-check is missing from release-check")
    if required_wiring["Review candidate"] not in review_candidate_body:
        failures.append("enterprise-dual-review-outbox is missing from review-candidate")
    if required_wiring["README command"] not in readme:
        failures.append("README is missing enterprise dual-review outbox command")
    if required_wiring["Queue pointer"] not in queue:
        failures.append("enterprise queue is missing dual-review outbox pointer")
    if required_wiring["Dual handoff pointer"] not in handoff_doc:
        failures.append("dual-review handoff doc is missing outbox pointer")
    if required_wiring["Docs site"] not in docs_site:
        failures.append("enterprise dual-review outbox is missing from docs site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("enterprise dual-review outbox is missing from review docs")
    if required_wiring["Review index"] not in review_index:
        failures.append("review-docs index is missing enterprise dual-review outbox")
    if required_wiring["Release guardrails"] not in release_guardrails:
        failures.append("release guardrails do not require enterprise dual-review outbox")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "outbox_doc": DOC_REL,
        "output_dir": output_dir.as_posix(),
        "recommended_gaps": ["ERG-003", "ERG-002"],
        "tool_count": 24,
        "copied_packet_count": 2,
        "artifact_hashes_match_files": artifact_hashes_match_files,
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
    }


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise dual-review outbox check",
        f"valid: {str(report['valid']).lower()}",
        f"outbox_doc: {report['outbox_doc']}",
        f"output_dir: {report['output_dir']}",
        "recommended_gaps: " + ", ".join(report["recommended_gaps"]),
        f"tool_count: {report['tool_count']}",
        f"copied_packet_count: {report['copied_packet_count']}",
        f"artifact_hashes_match_files: {str(report['artifact_hashes_match_files']).lower()}",
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
        f"closes_erg_003: {str(report['closes_erg_003']).lower()}",
        f"closes_erg_002: {str(report['closes_erg_002']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _copy_packet(repo_root: Path, output_dir: Path, packet: dict[str, Any]) -> dict[str, Any]:
    gap = packet["gap"]
    source_dir = repo_root / packet["packet_dir"]
    target_dir = output_dir / gap
    target_dir.mkdir(parents=True, exist_ok=True)
    copied_files = []
    for filename in packet["attach_files"]:
        source = source_dir / filename
        if not source.is_file():
            raise EnterpriseDualReviewOutboxError(f"{gap} attachment is missing: {filename}")
        target = target_dir / filename
        shutil.copy2(source, target)
        copied_files.append(filename)
    return {
        "gap": gap,
        "name": packet["name"],
        "source_packet_dir": packet["packet_dir"],
        "outbox_dir": target_dir.relative_to(output_dir).as_posix(),
        "finding_namespace": packet["finding_namespace"],
        "prompt": packet["prompt"],
        "copied_files": copied_files,
        "copied_file_count": len(copied_files),
        "response_kit": packet["response_kit"],
        "dry_run": packet["dry_run"],
        "closure_gate": packet["closure_gate"],
        "intake_doc": packet["intake_doc"],
    }


def _outbox_payload(
    *,
    commit: str,
    dirty: bool,
    copied_packets: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "outbox_type": "ithildin.enterprise_dual_review_outbox",
        "commit": commit,
        "dirty": dirty,
        "tool_count": 24,
        "selected_capability": "not selected",
        "recommended_gaps": ["ERG-003", "ERG-002"],
        "packets": copied_packets,
        "blocked_boundaries": {
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
    packet_sections = []
    for packet in payload["packets"]:
        files = "\n".join(f"- `{packet['outbox_dir']}/{name}`" for name in packet["copied_files"])
        packet_sections.append(
            f"""## {packet['gap']}: {packet['name']}

Finding namespace: `{packet['finding_namespace']}`

Prompt: `{packet['outbox_dir']}/{packet['prompt']}`

Copied files: `{packet['copied_file_count']}`

{files}

Response kit after review: `{packet['response_kit']}`

Dry run after response: `{packet['dry_run']}`

Closure gate after response: `{packet['closure_gate']}`
            """
        )
    packet_markdown = "\n".join(packet_sections)
    blocked = "\n".join(
        f"- {name}: `{str(value).lower()}`"
        for name, value in payload["blocked_boundaries"].items()
    )
    return f"""# Enterprise Dual Review Outbox

Send-ready copy root for `ERG-003` and `ERG-002` enterprise review packets.

Reviewed commit for the outbox: `{payload['commit']}`

Dirty state when generated: `{str(payload['dirty']).lower()}`

Tool count remains `{payload['tool_count']}`.

Current selected capability: `{payload['selected_capability']}`.

Attach each lane directory as its own review packet. The outbox copies the already generated
source packet files and their artifact hash manifests; it does not record reviewer feedback,
normalize responses, close lanes, or approve runtime behavior.

{packet_markdown}

## Boundary Flags

{blocked}

## Regeneration Commands

```sh
make enterprise-dual-review-handoff
make enterprise-dual-review-outbox
make enterprise-dual-review-outbox-check
make enterprise-dual-response-readiness
```
"""


def _validate_repo_root(repo_root: Path) -> None:
    missing = [
        marker
        for marker in ["pyproject.toml", "Makefile", "tool-manifests.lock.json"]
        if not (repo_root / marker).exists()
    ]
    if missing:
        raise EnterpriseDualReviewOutboxError(
            "must be run from the Ithildin repo root; missing " + ", ".join(missing)
        )


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

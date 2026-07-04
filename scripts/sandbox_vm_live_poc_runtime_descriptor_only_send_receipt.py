"""Build an operator send receipt template for the active ERG-004 review."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import enterprise_send_now, review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = (
    "docs/codex/"
    "sandbox-vm-live-poc-runtime-descriptor-only-send-receipt.md"
)
DOC_TITLE = "Sandbox/VM Live POC Runtime Descriptor-Only Send Receipt"
DEFAULT_OUTPUT_DIR = Path(
    "var/review-runs/"
    "sandbox-vm-live-poc-runtime-descriptor-only-send-receipt"
)
MARKDOWN_NAME = "ERG004_RUNTIME_DESCRIPTOR_ONLY_SEND_RECEIPT.md"
JSON_NAME = "erg004-runtime-descriptor-only-send-receipt.json"
HASH_NAME = "erg004-runtime-descriptor-only-send-receipt-artifact-hashes.json"
BOUNDARY_FLAGS = {
    "records_external_review": False,
    "normalizes_responses": False,
    "writes_response_files": False,
    "closes_erg_004": False,
    "runtime_changes_allowed": False,
    "mission_control_runtime_allowed": False,
    "live_vm_inspection_allowed": False,
    "sandbox_orchestration_allowed": False,
    "new_power_classes_allowed": False,
}
ALLOWED_SEND_NOW_FAILURES = {
    "handoff artifacts are stale; run make review-candidate",
}


class DescriptorOnlySendReceiptError(RuntimeError):
    """Raised when the ERG-004 send receipt cannot be built."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.check:
        report = build_check_report(ROOT, args.output_dir)
        print(render_check_report(report))
        return 0 if report["valid"] else 1

    try:
        output_dir = build_receipt(ROOT, args.output_dir)
    except DescriptorOnlySendReceiptError as exc:
        print(f"ERG-004 descriptor-only send receipt failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built ERG-004 descriptor-only send receipt at {output_dir}")
    return 0


def build_receipt(repo_root: Path, output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    _validate_repo_root(repo_root)
    output_path = output_dir if output_dir.is_absolute() else repo_root / output_dir
    output_path.mkdir(parents=True, exist_ok=True)

    send_now = enterprise_send_now.build_report(repo_root)
    _validate_send_now_route(send_now)

    payload = _payload(repo_root, send_now)
    (output_path / MARKDOWN_NAME).write_text(
        _render_markdown(payload),
        encoding="utf-8",
    )
    (output_path / JSON_NAME).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    hashes = _artifact_hashes(output_path)
    (output_path / HASH_NAME).write_text(
        json.dumps(hashes, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def _validate_send_now_route(send_now: dict[str, Any]) -> None:
    unexpected_failures = [
        failure
        for failure in send_now.get("failures", [])
        if failure not in ALLOWED_SEND_NOW_FAILURES
    ]
    if unexpected_failures:
        raise DescriptorOnlySendReceiptError(
            "enterprise-send-now has unexpected failures: "
            + "; ".join(unexpected_failures)
        )
    if send_now.get("recommended_gaps") != ["ERG-004"]:
        raise DescriptorOnlySendReceiptError("active send set is not ERG-004")
    if send_now.get("current_send_set") != ["ERG-004"]:
        raise DescriptorOnlySendReceiptError("current send set is not ERG-004")
    if len(send_now.get("lanes", [])) != 1:
        raise DescriptorOnlySendReceiptError("enterprise-send-now must expose one lane")
    if send_now.get("runtime_changes_allowed") is not False:
        raise DescriptorOnlySendReceiptError("enterprise-send-now allows runtime changes")
    if send_now.get("closes_erg_004") is not False:
        raise DescriptorOnlySendReceiptError("enterprise-send-now closes ERG-004")
    for flag, expected in BOUNDARY_FLAGS.items():
        if send_now.get(flag) is not expected:
            raise DescriptorOnlySendReceiptError(
                f"enterprise-send-now has unsafe boundary flag: {flag}"
            )


def build_check_report(repo_root: Path, output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    failures: list[str] = []
    try:
        output_path = build_receipt(repo_root, output_dir)
    except DescriptorOnlySendReceiptError as exc:
        failures.append(str(exc))
        output_path = output_dir if output_dir.is_absolute() else repo_root / output_dir

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    send_now_doc = _read(repo_root / "docs/codex/enterprise-current-checkpoint.md")
    response_inbox_doc = _read(
        repo_root
        / "docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-response-inbox.md"
    )
    receipt_doc = _read(repo_root / DOC_REL)
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition(
        "\n\n"
    )[0]
    markdown_text = _read(output_path / MARKDOWN_NAME)
    json_text = _read(output_path / JSON_NAME)
    hash_text = _read(output_path / HASH_NAME)

    try:
        hash_manifest = json.loads(hash_text) if hash_text else {"artifacts": []}
    except json.JSONDecodeError:
        hash_manifest = {"artifacts": []}
        failures.append("ERG-004 descriptor-only send receipt hashes are invalid JSON")

    _require_phrases(
        failures,
        "ERG-004 descriptor-only send receipt doc",
        receipt_doc,
        [
            "Status: generated operator send receipt template for the active ERG-004 "
            "descriptor-only review.",
            "make sandbox-vm-live-poc-runtime-descriptor-only-send-receipt",
            "make sandbox-vm-live-poc-runtime-descriptor-only-send-receipt-check",
            "does not record external review",
            "does not normalize responses",
            "does not write response files",
            "does not close `ERG-004`",
        ],
    )
    _require_phrases(
        failures,
        "generated ERG-004 descriptor-only send receipt",
        markdown_text,
        [
            "ERG-004 Runtime Descriptor-Only Send Receipt",
            "Receipt status",
            "sent: `false`",
            "Operator fill-in fields",
            "Packet hash evidence",
            "EXT-LIVE-DESC-###",
            "RAW_RESPONSE_ERG-004-DESCRIPTOR-ONLY.md",
            "records_external_review: `false`",
            "normalizes_responses: `false`",
            "writes_response_files: `false`",
            "closes_erg_004: `false`",
        ],
    )
    _require_phrases(
        failures,
        "generated ERG-004 descriptor-only send receipt JSON",
        json_text,
        [
            '"receipt_type": "ithildin.erg004_descriptor_only_send_receipt"',
            '"sent": false',
            '"gap": "ERG-004"',
            '"finding_namespace": "EXT-LIVE-DESC-###"',
            '"records_external_review": false',
            '"normalizes_responses": false',
            '"writes_response_files": false',
            '"closes_erg_004": false',
        ],
    )

    hashed_paths = {artifact.get("path") for artifact in hash_manifest.get("artifacts", [])}
    if {MARKDOWN_NAME, JSON_NAME} - hashed_paths:
        failures.append("ERG-004 send receipt hash manifest is missing generated artifacts")
    if HASH_NAME in hashed_paths:
        failures.append("ERG-004 send receipt hash manifest must not hash itself")
    if not _artifact_hashes_match_files(output_path, hash_manifest):
        failures.append("ERG-004 send receipt artifact hashes do not match files")

    wiring = {
        "Make target": ("sandbox-vm-live-poc-runtime-descriptor-only-send-receipt:", makefile),
        "Check target": (
            "sandbox-vm-live-poc-runtime-descriptor-only-send-receipt-check:",
            makefile,
        ),
        "Release check": (
            "sandbox-vm-live-poc-runtime-descriptor-only-send-receipt-check",
            release_check_body + "\n" + makefile,
        ),
        "Review candidate": (
            "$(MAKE) sandbox-vm-live-poc-runtime-descriptor-only-send-receipt",
            review_candidate_body,
        ),
        "README command": (
            "make sandbox-vm-live-poc-runtime-descriptor-only-send-receipt",
            readme,
        ),
        "README doc": (DOC_REL, readme),
        "Docs site": (DOC_REL, docs_site),
        "Review docs": (DOC_REL, "\n".join(review_docs.REVIEW_DOCS)),
        "Review index": (DOC_TITLE, review_index),
        "Release guardrails": (
            "sandbox-vm-live-poc-runtime-descriptor-only-send-receipt-check",
            release_guardrails,
        ),
        "Current checkpoint pointer": (
            "sandbox-vm-live-poc-runtime-descriptor-only-send-receipt",
            send_now_doc,
        ),
        "Response inbox pointer": (
            "sandbox-vm-live-poc-runtime-descriptor-only-send-receipt",
            response_inbox_doc,
        ),
    }
    for label, (needle, haystack) in wiring.items():
        if needle not in haystack:
            failures.append(f"{label} is missing ERG-004 send receipt wiring")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "receipt_doc": DOC_REL,
        "output_dir": _repo_rel(repo_root, output_path),
        "tool_count": 24,
        "selected_capability": "not selected",
        "recommended_gaps": ["ERG-004"],
        "artifact_hashes_match_files": _artifact_hashes_match_files(output_path, hash_manifest),
        **BOUNDARY_FLAGS,
    }


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin ERG-004 descriptor-only send receipt",
        f"valid: {str(report['valid']).lower()}",
        f"receipt_doc: {report['receipt_doc']}",
        f"output_dir: {report['output_dir']}",
        f"tool_count: {report['tool_count']}",
        "recommended_gaps: " + ", ".join(report["recommended_gaps"]),
        "artifact_hashes_match_files: "
        f"{str(report['artifact_hashes_match_files']).lower()}",
    ]
    lines.extend(f"{key}: {str(value).lower()}" for key, value in BOUNDARY_FLAGS.items())
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _payload(repo_root: Path, send_now: dict[str, Any]) -> dict[str, Any]:
    lane = send_now["lanes"][0]
    packet_dir = repo_root / lane["batches"][0]["path"]
    hash_path = (
        packet_dir
        / "sandbox-vm-live-poc-runtime-descriptor-only-source-artifact-hashes.json"
    )
    hash_bytes = hash_path.read_bytes()
    return {
        "schema_version": "1",
        "receipt_type": "ithildin.erg004_descriptor_only_send_receipt",
        "commit": _git(repo_root, ["rev-parse", "HEAD"]),
        "dirty": bool(_git(repo_root, ["status", "--short"])),
        "tool_count": 24,
        "selected_capability": "not selected",
        "sent": False,
        "operator_fill_in": {
            "sent_at": "",
            "channel": "",
            "reviewer_label": "",
            "thread_or_message_url": "",
            "message_id": "",
            "operator_notes": "",
        },
        "lane": {
            "gap": "ERG-004",
            "name": lane["name"],
            "finding_namespace": lane["finding_namespace"],
            "prompt": lane["prompt"],
            "source_review_packet": lane["batches"][0]["path"],
            "source_review_hash_manifest": _repo_rel(repo_root, hash_path),
            "source_review_hash_manifest_sha256": hashlib.sha256(hash_bytes).hexdigest(),
            "raw_response_path": lane["raw_response_path"],
            "dry_run_after_response": lane["dry_run"],
            "closure_gate_after_response": lane["closure_gate"],
        },
        "blocked_boundaries": BOUNDARY_FLAGS,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lane = payload["lane"]
    blocked = "\n".join(
        f"- {key}: `{str(value).lower()}`"
        for key, value in payload["blocked_boundaries"].items()
    )
    return f"""# ERG-004 Runtime Descriptor-Only Send Receipt

Status: generated operator send receipt template for the active ERG-004 descriptor-only review.

Reviewed commit: `{payload['commit']}`

Dirty state when generated: `{str(payload['dirty']).lower()}`

Tool count remains `{payload['tool_count']}`.

Current selected capability: `{payload['selected_capability']}`.

## Receipt status

sent: `{str(payload['sent']).lower()}`

This generated file is a template. It does not prove that the packet was sent or reviewed.

## Packet hash evidence

Source-review packet: `{lane['source_review_packet']}`

Prompt: `{lane['prompt']}`

Finding namespace: `{lane['finding_namespace']}`

Hash manifest: `{lane['source_review_hash_manifest']}`

Hash manifest SHA-256: `{lane['source_review_hash_manifest_sha256']}`

Raw response path: `{lane['raw_response_path']}`

## Operator fill-in fields

Copy this generated template before filling in local operator notes.

- sent_at:
- channel:
- reviewer_label:
- thread_or_message_url:
- message_id:
- operator_notes:

## After Response

Paste the real reviewer response only into:

```text
{lane['raw_response_path']}
```

Then run:

```sh
{lane['dry_run_after_response']}
{lane['closure_gate_after_response']}
```

## Blocked boundaries

{blocked}

This template does not record external review, does not normalize responses, does not write response
files, does not close `ERG-004`, and does not approve runtime implementation.
"""


def _require_phrases(
    failures: list[str],
    label: str,
    text: str,
    phrases: list[str],
) -> None:
    for phrase in phrases:
        if phrase not in text:
            failures.append(f"{label} is missing phrase: {phrase}")


def _validate_repo_root(repo_root: Path) -> None:
    missing = [
        marker
        for marker in ["pyproject.toml", "Makefile", "tool-manifests.lock.json"]
        if not (repo_root / marker).exists()
    ]
    if missing:
        raise DescriptorOnlySendReceiptError(
            "must be run from the Ithildin repo root; missing " + ", ".join(missing)
        )


def _artifact_hashes(output_dir: Path) -> dict[str, Any]:
    artifacts = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name == HASH_NAME:
            continue
        data = path.read_bytes()
        artifacts.append(
            {
                "path": path.relative_to(output_dir).as_posix(),
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


def _repo_rel(repo_root: Path, path: Path) -> str:
    if not path.is_absolute():
        return path.as_posix()
    return path.relative_to(repo_root).as_posix()


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


if __name__ == "__main__":
    raise SystemExit(main())

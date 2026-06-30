"""Stage enterprise review attachments into upload-friendly batch folders."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import enterprise_review_send_package, review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/enterprise-review-upload-staging.md"
DOC_NAME = "enterprise-review-upload-staging.md"
DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/enterprise-review-upload-staging")
MARKDOWN_NAME = "ENTERPRISE_REVIEW_UPLOAD_STAGING.md"
JSON_NAME = "enterprise-review-upload-staging.json"
HASH_NAME = "enterprise-review-upload-staging-artifact-hashes.json"
MAX_ATTACHMENTS_PER_BATCH = 10
RECOMMENDED_GAPS = ["ERG-003", "ERG-002"]
BOUNDARY_FLAGS = {
    "records_external_review": False,
    "normalizes_responses": False,
    "writes_response_files": False,
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


class EnterpriseReviewUploadStagingError(RuntimeError):
    """Raised when upload staging cannot be built or validated."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--prefer-existing-package",
        action="store_true",
        help=(
            "reuse the generated enterprise review send package when it matches "
            "the current commit/dirty state; rebuild it otherwise"
        ),
    )
    args = parser.parse_args()

    if args.check:
        report = build_check_report(
            ROOT,
            prefer_existing_package=args.prefer_existing_package,
        )
        print(render_check_report(report))
        return 0 if report["valid"] else 1

    try:
        output_dir = build_staging(
            ROOT,
            args.output_dir,
            prefer_existing_package=args.prefer_existing_package,
        )
    except EnterpriseReviewUploadStagingError as exc:
        print(f"enterprise review upload staging failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built enterprise review upload staging at {output_dir}")
    return 0


def build_staging(
    repo_root: Path,
    output_dir: Path,
    *,
    prefer_existing_package: bool = False,
) -> Path:
    _validate_repo_root(repo_root)
    package_dir = enterprise_review_send_package.DEFAULT_OUTPUT_DIR
    package_payload = None
    source_package_reused = False
    if prefer_existing_package:
        package_payload = _current_package_payload(repo_root, package_dir)
        source_package_reused = package_payload is not None
    if package_payload is None:
        package_dir = enterprise_review_send_package.build_package(repo_root, package_dir)
        package_payload = _read_json(package_dir / enterprise_review_send_package.JSON_NAME)

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    payload = _staging_payload(
        repo_root,
        output_dir,
        package_payload,
        source_package_reused=source_package_reused,
    )
    _copy_batches(repo_root, output_dir, payload)
    (output_dir / MARKDOWN_NAME).write_text(_render_markdown(payload), encoding="utf-8")
    (output_dir / JSON_NAME).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    hashes = _artifact_hashes(output_dir)
    (output_dir / HASH_NAME).write_text(
        json.dumps(hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output_dir


def build_check_report(
    repo_root: Path,
    *,
    prefer_existing_package: bool = False,
) -> dict[str, Any]:
    failures: list[str] = []
    try:
        output_dir = build_staging(
            repo_root,
            DEFAULT_OUTPUT_DIR,
            prefer_existing_package=prefer_existing_package,
        )
    except EnterpriseReviewUploadStagingError as exc:
        failures.append(str(exc))
        output_dir = DEFAULT_OUTPUT_DIR

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    quickstart_doc = _read(repo_root / "docs/codex/enterprise-review-send-quickstart.md")
    package_doc = _read(repo_root / "docs/codex/enterprise-review-send-package.md")
    staging_doc = _read(repo_root / DOC_REL)
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]
    refresh_body = makefile.partition("enterprise-review-send-refresh:")[2].partition("\n\n")[0]
    markdown_text = _read(output_dir / MARKDOWN_NAME)
    json_text = _read(output_dir / JSON_NAME)
    hash_text = _read(output_dir / HASH_NAME)

    try:
        payload = json.loads((output_dir / JSON_NAME).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        payload = {"lanes": []}
        failures.append("enterprise review upload staging JSON is missing or invalid")
    try:
        hashes = json.loads(hash_text) if hash_text else {"artifacts": []}
    except json.JSONDecodeError:
        hashes = {"artifacts": []}
        failures.append("enterprise review upload staging hashes are not valid JSON")

    _require_phrases(
        failures,
        "upload staging doc",
        staging_doc,
        [
            "Status: generated upload-staging batches for the current enterprise send set.",
            "make enterprise-review-upload-staging",
            "make enterprise-review-upload-staging-check",
            "`ERG-003`",
            "`ERG-002`",
            "does not record external review",
            "does not normalize responses",
            "does not close `ERG-003` or `ERG-002`",
        ],
    )
    _require_phrases(
        failures,
        "generated upload staging",
        markdown_text,
        [
            "Enterprise Review Upload Staging",
            "Upload batches",
            "ERG-003",
            "ERG-002",
            "batch-1",
            "batch-2",
            "records_external_review: `false`",
            "normalizes_responses: `false`",
            "closes_erg_003: `false`",
            "closes_erg_002: `false`",
        ],
    )
    _require_phrases(
        failures,
        "generated upload staging JSON",
        json_text,
        [
            '"staging_type": "ithildin.enterprise_review_upload_staging"',
            '"ERG-003"',
            '"ERG-002"',
            '"batch-1"',
            '"records_external_review": false',
            '"normalizes_responses": false',
            '"closes_erg_003": false',
            '"closes_erg_002": false',
        ],
    )

    hashed_paths = {artifact.get("path") for artifact in hashes.get("artifacts", [])}
    if {MARKDOWN_NAME, JSON_NAME} - hashed_paths:
        failures.append("upload staging hash manifest is missing generated artifacts")
    if HASH_NAME in hashed_paths:
        failures.append("upload staging hash manifest must not hash itself")
    if not _artifact_hashes_match_files(output_dir, hashes):
        failures.append("upload staging artifact hashes do not match files")
    _validate_payload_files(failures, output_dir, payload)

    wiring_checks = {
        "Make target": ("enterprise-review-upload-staging:", makefile),
        "Check target": ("enterprise-review-upload-staging-check:", makefile),
        "Release check": ("enterprise-review-upload-staging-check", release_check_body),
        "Review candidate": ("$(MAKE) enterprise-review-upload-staging", review_candidate_body),
        "Send refresh": ("$(MAKE) enterprise-review-upload-staging", refresh_body),
        "README command": ("make enterprise-review-upload-staging", readme),
        "Docs site": (DOC_REL, docs_site),
        "Review docs": (DOC_REL, "\n".join(review_docs.REVIEW_DOCS)),
        "Review index": (DOC_NAME, review_index),
        "Release guardrails": ("enterprise-review-upload-staging-check", release_guardrails),
        "Quickstart pointer": ("enterprise-review-upload-staging", quickstart_doc),
        "Package pointer": ("enterprise-review-upload-staging", package_doc),
    }
    for label, (needle, haystack) in wiring_checks.items():
        if needle not in haystack:
            failures.append(f"{label} is missing {needle}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "staging_doc": DOC_REL,
        "output_dir": output_dir.as_posix(),
        "recommended_gaps": RECOMMENDED_GAPS,
        "tool_count": 24,
        "batch_count": sum(len(lane.get("batches", [])) for lane in payload.get("lanes", [])),
        "source_package_reused": bool(payload.get("source_package_reused")),
        "artifact_hashes_match_files": _artifact_hashes_match_files(output_dir, hashes),
        **BOUNDARY_FLAGS,
    }


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin enterprise review upload staging check",
        f"valid: {str(report['valid']).lower()}",
        f"staging_doc: {report['staging_doc']}",
        f"output_dir: {report['output_dir']}",
        "recommended_gaps: " + ", ".join(report["recommended_gaps"]),
        f"tool_count: {report['tool_count']}",
        f"batch_count: {report['batch_count']}",
        f"source_package_reused: {str(report['source_package_reused']).lower()}",
        f"artifact_hashes_match_files: {str(report['artifact_hashes_match_files']).lower()}",
    ]
    lines.extend(f"{key}: {str(value).lower()}" for key, value in BOUNDARY_FLAGS.items())
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _staging_payload(
    repo_root: Path,
    output_dir: Path,
    package_payload: dict[str, Any],
    *,
    source_package_reused: bool,
) -> dict[str, Any]:
    lanes = []
    for lane in package_payload.get("send_set", []):
        attachment_manifest = repo_root / str(lane["attachment_manifest"])
        attachments = _parse_attachment_manifest(attachment_manifest)
        batches = []
        for index, batch_files in enumerate(_batch_files(attachments), start=1):
            batch_id = f"batch-{index}"
            batches.append(
                {
                    "batch_id": batch_id,
                    "path": _repo_rel(repo_root, output_dir / str(lane["gap"]) / batch_id),
                    "attachment_count": len(batch_files),
                    "attachments": [
                        {
                            "file": attachment["file"],
                            "bytes": attachment["bytes"],
                            "sha256": attachment["sha256"],
                        }
                        for attachment in batch_files
                    ],
                }
            )
        lanes.append(
            {
                "gap": lane["gap"],
                "name": lane["name"],
                "finding_namespace": lane["finding_namespace"],
                "source_outbox_dir": lane["outbox_dir"],
                "prompt": lane["prompt"],
                "attachment_manifest": lane["attachment_manifest"],
                "hash_manifest": lane["hash_manifest"],
                "raw_response_path": lane["raw_response_path"],
                "source_attachment_count": len(attachments),
                "batches": batches,
            }
        )
    return {
        "schema_version": "1",
        "staging_type": "ithildin.enterprise_review_upload_staging",
        "commit": _git(repo_root, ["rev-parse", "HEAD"]),
        "dirty": bool(_git(repo_root, ["status", "--short"])),
        "tool_count": 24,
        "selected_capability": "not selected",
        "recommended_gaps": RECOMMENDED_GAPS,
        "max_attachments_per_batch": MAX_ATTACHMENTS_PER_BATCH,
        "source_package": _repo_rel(
            repo_root,
            enterprise_review_send_package.DEFAULT_OUTPUT_DIR,
        ),
        "source_package_reused": source_package_reused,
        "lanes": lanes,
        "blocked_boundaries": dict(BOUNDARY_FLAGS),
    }


def _copy_batches(repo_root: Path, output_dir: Path, payload: dict[str, Any]) -> None:
    for lane in payload["lanes"]:
        source_dir = repo_root / lane["source_outbox_dir"]
        for batch in lane["batches"]:
            batch_dir = repo_root / batch["path"]
            batch_dir.mkdir(parents=True, exist_ok=True)
            for attachment in batch["attachments"]:
                source = source_dir / attachment["file"]
                destination = batch_dir / attachment["file"]
                if not source.is_file():
                    raise EnterpriseReviewUploadStagingError(
                        f"missing source attachment: {source}"
                    )
                shutil.copy2(source, destination)
                data = destination.read_bytes()
                if len(data) != int(attachment["bytes"]):
                    raise EnterpriseReviewUploadStagingError(
                        f"copied attachment byte count mismatch: {destination}"
                    )
                if "sha256:" + hashlib.sha256(data).hexdigest() != attachment["sha256"]:
                    raise EnterpriseReviewUploadStagingError(
                        f"copied attachment hash mismatch: {destination}"
                    )


def _render_markdown(payload: dict[str, Any]) -> str:
    lane_sections = "\n".join(_render_lane(lane) for lane in payload["lanes"])
    blocked = "\n".join(
        f"- {key}: `{str(value).lower()}`"
        for key, value in payload["blocked_boundaries"].items()
    )
    return f"""# Enterprise Review Upload Staging

Status: generated upload-staging batches for the current enterprise send set.

Commit: `{payload['commit']}`

Dirty state when generated: `{str(payload['dirty']).lower()}`

Tool count: `{payload['tool_count']}`

Recommended send set: `ERG-003`, `ERG-002`

Maximum attachments per batch: `{payload['max_attachments_per_batch']}`

Current send package reused: `{str(payload['source_package_reused']).lower()}`

## Upload batches

Use these batch folders when the review surface has a 10-attachment limit. Each batch contains only
the manifest-listed files to attach, not lane-local operator reference files such as
`ATTACHMENT_MANIFEST.md`.

{lane_sections}

## Boundary flags

{blocked}

This staging output does not record external review, does not normalize responses, does not write
response files, and does not close `ERG-003` or `ERG-002`. It only copies the already generated
manifest-listed attachments into upload-friendly batch folders.
"""


def _render_lane(lane: dict[str, Any]) -> str:
    batch_lines = []
    for batch in lane["batches"]:
        files = "\n".join(f"  - `{item['file']}`" for item in batch["attachments"])
        batch_lines.append(
            f"- `{batch['batch_id']}`: `{batch['path']}` "
            f"({batch['attachment_count']} attachment(s))\n{files}"
        )
    return (
        f"### {lane['gap']}: {lane['name']}\n\n"
        f"- Prompt: `{lane['prompt']}`\n"
        f"- Source outbox: `{lane['source_outbox_dir']}`\n"
        f"- Source attachment manifest: `{lane['attachment_manifest']}`\n"
        f"- Raw response placeholder: `{lane['raw_response_path']}`\n\n"
        + "\n\n".join(batch_lines)
    )


def _parse_attachment_manifest(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise EnterpriseReviewUploadStagingError(f"missing attachment manifest: {path}")
    rows: list[dict[str, Any]] = []
    pattern = re.compile(
        r"^\| `(?P<file>[^`]+)` \| `(?P<bytes>\d+)` "
        r"\| `(?P<sha>sha256:[0-9a-f]{64})` \|$"
    )
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line.strip())
        if match:
            rows.append(
                {
                    "file": match.group("file"),
                    "bytes": int(match.group("bytes")),
                    "sha256": match.group("sha"),
                }
            )
    if not rows:
        raise EnterpriseReviewUploadStagingError(
            f"attachment manifest has no parseable rows: {path}"
        )
    return rows


def _batch_files(files: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    if len(files) <= MAX_ATTACHMENTS_PER_BATCH:
        return [files]
    split = (len(files) + 1) // 2
    return [files[:split], files[split:]]


def _validate_payload_files(
    failures: list[str], output_dir: Path, payload: dict[str, Any]
) -> None:
    lane_by_gap = {lane.get("gap"): lane for lane in payload.get("lanes", [])}
    if sorted(lane_by_gap) != sorted(RECOMMENDED_GAPS):
        failures.append("upload staging payload does not include ERG-003 and ERG-002")
        return
    expected_batch_counts = {"ERG-003": [10], "ERG-002": [6, 5]}
    for gap, expected_counts in expected_batch_counts.items():
        lane = lane_by_gap[gap]
        actual_counts = [batch.get("attachment_count") for batch in lane.get("batches", [])]
        if actual_counts != expected_counts:
            failures.append(f"{gap} upload staging has unexpected batch counts: {actual_counts}")
        for batch in lane.get("batches", []):
            batch_path = Path(str(batch.get("path", "")))
            for attachment in batch.get("attachments", []):
                staged = batch_path / str(attachment.get("file", ""))
                if not staged.is_file():
                    failures.append(f"missing staged attachment: {staged}")
                    continue
                data = staged.read_bytes()
                if len(data) != int(attachment.get("bytes", -1)):
                    failures.append(f"staged attachment byte count mismatch: {staged}")
                if (
                    "sha256:" + hashlib.sha256(data).hexdigest()
                    != attachment.get("sha256")
                ):
                    failures.append(f"staged attachment hash mismatch: {staged}")
    if not (output_dir / "ERG-003" / "batch-1").is_dir():
        failures.append("ERG-003 batch-1 directory is missing")
    if not (output_dir / "ERG-002" / "batch-1").is_dir():
        failures.append("ERG-002 batch-1 directory is missing")
    if not (output_dir / "ERG-002" / "batch-2").is_dir():
        failures.append("ERG-002 batch-2 directory is missing")


def _current_package_payload(repo_root: Path, package_dir: Path) -> dict[str, Any] | None:
    package_path = package_dir / enterprise_review_send_package.JSON_NAME
    hashes_path = package_dir / enterprise_review_send_package.HASH_NAME
    if not package_path.is_file() or not hashes_path.is_file():
        return None
    try:
        payload = _read_json(package_path)
        hashes = _read_json(hashes_path)
    except (json.JSONDecodeError, OSError):
        return None
    if payload.get("package_type") != "ithildin.enterprise_review_send_package":
        return None
    if payload.get("commit") != _git(repo_root, ["rev-parse", "HEAD"]):
        return None
    if bool(payload.get("dirty")) != bool(_git(repo_root, ["status", "--short"])):
        return None
    if sorted(payload.get("recommended_gaps", [])) != sorted(RECOMMENDED_GAPS):
        return None
    if payload.get("blocked_boundaries") != BOUNDARY_FLAGS:
        return None
    if not _artifact_hashes_match_files(package_dir, hashes):
        return None
    return payload


def _validate_repo_root(repo_root: Path) -> None:
    missing = [
        marker
        for marker in ["pyproject.toml", "Makefile", "tool-manifests.lock.json"]
        if not (repo_root / marker).exists()
    ]
    if missing:
        raise EnterpriseReviewUploadStagingError(
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
                "sha256": "sha256:" + hashlib.sha256(data).hexdigest(),
            }
        )
    return {"schema_version": "1", "artifacts": artifacts}


def _artifact_hashes_match_files(output_dir: Path, manifest: dict[str, Any]) -> bool:
    for artifact in manifest.get("artifacts", []):
        path = output_dir / artifact.get("path", "")
        if not path.is_file():
            return False
        data = path.read_bytes()
        if artifact.get("bytes") != len(data):
            return False
        if artifact.get("sha256") != "sha256:" + hashlib.sha256(data).hexdigest():
            return False
    return True


def _require_phrases(
    failures: list[str],
    label: str,
    text: str,
    phrases: list[str],
) -> None:
    for phrase in phrases:
        if phrase not in text:
            failures.append(f"{label} is missing phrase: {phrase}")


def _read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


def _repo_rel(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())

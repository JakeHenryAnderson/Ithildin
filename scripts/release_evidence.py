"""Emit a local public-preview release evidence snapshot without secrets."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ithildin_api.config import Settings
from ithildin_api.filesystem_contract import collect_filesystem_contract_status
from ithildin_api.identity import PrincipalRegistry
from ithildin_api.manifest_lock import (
    ManifestLockRecord,
    manifest_lock_payload,
    manifest_lock_signature_status,
)
from ithildin_api.policy import load_policy_engine
from ithildin_api.registry import ToolRegistry
from ithildin_api.security_status import security_status
from ithildin_api.storage import storage_status
from ithildin_api.telemetry import configure_telemetry
from ithildin_api.workspaces import WorkspaceRegistry
from ithildin_audit_core import AuditWriter, audit_signing_status

from scripts.review_docs import collect_review_doc_metadata

PROJECT_MARKERS = (
    "pyproject.toml",
    "Makefile",
    "apps/api",
    "apps/mcp-server",
    "tool-manifests.lock.json",
)
RELEASE_EVIDENCE_SCHEMA_VERSION = "v0.3-prep-release-evidence-v1"
RELEASE_EVIDENCE_REQUIRED_TOP_LEVEL_KEYS = (
    "schema",
    "generated_at",
    "repo",
    "git",
    "release_check",
    "review_docs",
    "manifest_lock",
    "docs_site",
    "tools",
    "policy",
    "principals",
    "workspaces",
    "filesystem",
    "storage",
    "telemetry",
    "security",
    "audit",
    "audit_signing",
    "deferred_boundaries",
)
SECRET_MARKERS = (
    "BEGIN PRIVATE KEY",
    "ITHILDIN_ADMIN_TOKEN=",
    "dev-admin-token-change-me",
    "password=",
    "secret=",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-release",
        action="store_true",
        help="run make release-check before writing the snapshot",
    )
    parser.add_argument(
        "--release-check-transcript",
        type=Path,
        help="path to an attached release-check transcript",
    )
    parser.add_argument(
        "--release-check-observed-status",
        choices=("passed", "failed", "not_run"),
        help="observed release-check status when a transcript is attached",
    )
    parser.add_argument(
        "--release-check-commit",
        help="commit associated with the attached release-check transcript",
    )
    parser.add_argument(
        "--validate-file",
        type=Path,
        help="validate a previously generated release evidence JSON file and exit",
    )
    args = parser.parse_args()

    if args.validate_file is not None:
        try:
            payload = json.loads(args.validate_file.read_text(encoding="utf-8"))
            validate_release_evidence_snapshot(payload)
        except (OSError, json.JSONDecodeError, ReleaseEvidenceSchemaError) as exc:
            print(f"release evidence validation failed: {exc}", file=sys.stderr)
            return 1
        print("Release evidence schema validation passed.")
        return 0

    repo_root = Path.cwd().resolve()
    marker_status = _project_marker_status(repo_root)
    missing_markers = [
        marker for marker, present in marker_status.items() if not present
    ]
    if missing_markers:
        print(
            "release evidence must be run from the Ithildin repo root; "
            f"missing markers: {', '.join(missing_markers)}",
            file=sys.stderr,
        )
        return 1

    current_commit = _git(["rev-parse", "HEAD"])
    release_check = _release_check(
        args.check_release,
        transcript=args.release_check_transcript,
        observed_status=args.release_check_observed_status,
        observed_commit=args.release_check_commit,
        current_commit=current_commit,
    )
    settings = Settings(admin_token="ithildin_admin_release_evidence_placeholder_000000000000")
    registry = ToolRegistry.load(
        settings.manifest_dir,
        lock_path=settings.manifest_lock_path,
        require_lock=settings.require_manifest_lock,
    )
    principal_registry = PrincipalRegistry.load(
        settings.principal_registry_path,
        require_registry=settings.require_known_principals,
    )
    workspace_registry = WorkspaceRegistry.load(
        settings.workspace_registry_path,
        require_registry=settings.require_known_workspaces,
        fallback_root=settings.workspace_root,
        default_workspace_id=settings.default_workspace_id,
    )
    policy = load_policy_engine(settings)
    audit_writer = AuditWriter(settings.db_path, settings.audit_log_path)
    manifest_lock_current = _manifest_lock_is_current(
        manifest_dir=settings.manifest_dir,
        lock_path=settings.manifest_lock_path,
        registry=registry,
    )

    snapshot = {
        "schema": {
            "schema_version": RELEASE_EVIDENCE_SCHEMA_VERSION,
            "stable_top_level_keys": list(RELEASE_EVIDENCE_REQUIRED_TOP_LEVEL_KEYS),
            "secret_free": True,
        },
        "generated_at": datetime.now(UTC).isoformat(),
        "repo": {
            "repo_root": repo_root.as_posix(),
            "current_working_directory": Path.cwd().resolve().as_posix(),
            "project_markers": marker_status,
        },
        "git": {
            "commit": current_commit,
            "branch": _git(["branch", "--show-current"]),
            "dirty": bool(_git(["status", "--short"])),
        },
        "release_check": release_check,
        "review_docs": collect_review_doc_metadata(repo_root),
        "manifest_lock": {
            "path": settings.manifest_lock_path.as_posix(),
            "required": settings.require_manifest_lock,
            "current": manifest_lock_current,
            "signature": manifest_lock_signature_status(
                lock_path=settings.manifest_lock_path,
                signature_path=settings.manifest_lock_signature_path,
                public_key_path=settings.manifest_lock_signing_public_key_path,
                required=settings.require_signed_manifest_lock,
            ),
        },
        "docs_site": {"command": "make docs-site", "output_dir": "site"},
        "tools": {
            "count": len(registry.list_tools()),
            "names": [tool.manifest.name for tool in registry.list_tools()],
        },
        "policy": policy.status(),
        "principals": {
            **principal_registry.status(),
            "required": settings.require_known_principals,
        },
        "workspaces": workspace_registry.status(),
        "filesystem": collect_filesystem_contract_status(),
        "storage": storage_status(settings),
        "telemetry": configure_telemetry(settings).status(),
        "security": security_status(settings),
        "audit": _audit_snapshot(audit_writer),
        "audit_signing": audit_signing_status(
            settings.audit_signing_private_key_path,
            settings.audit_signing_public_key_path,
        ),
        "deferred_boundaries": [
            "production identity",
            "runtime Postgres",
            "hosted telemetry",
            "remote MCP hosting",
            "shell execution",
            "Docker socket access",
            "Kubernetes tools",
            "browser automation",
            "arbitrary HTTP methods, headers, or bodies",
            "broad filesystem writes",
            "plugin SDK and marketplace",
            "external audit anchoring and hosted supply-chain signing",
        ],
    }
    validate_release_evidence_snapshot(snapshot)
    json.dump(snapshot, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


class ReleaseEvidenceSchemaError(RuntimeError):
    """Raised when release evidence does not match the documented schema contract."""


def validate_release_evidence_snapshot(payload: object) -> None:
    if not isinstance(payload, dict):
        raise ReleaseEvidenceSchemaError("release evidence must be a JSON object")
    evidence = _json_object(payload)
    missing = [
        key for key in RELEASE_EVIDENCE_REQUIRED_TOP_LEVEL_KEYS if key not in evidence
    ]
    if missing:
        raise ReleaseEvidenceSchemaError(f"missing required top-level key: {missing[0]}")
    schema = _required_object(evidence, "schema")
    if schema.get("schema_version") != RELEASE_EVIDENCE_SCHEMA_VERSION:
        raise ReleaseEvidenceSchemaError("unsupported release evidence schema version")
    if schema.get("stable_top_level_keys") != list(
        RELEASE_EVIDENCE_REQUIRED_TOP_LEVEL_KEYS
    ):
        raise ReleaseEvidenceSchemaError("stable_top_level_keys does not match schema")
    if schema.get("secret_free") is not True:
        raise ReleaseEvidenceSchemaError("release evidence must declare secret_free=true")
    if not isinstance(evidence.get("generated_at"), str):
        raise ReleaseEvidenceSchemaError("generated_at must be a string")
    _required_object(evidence, "repo")
    release_check = _required_object(evidence, "release_check")
    for key in (
        "gate_executed_by_release_packet",
        "gate_status",
        "attached_transcript_exists",
        "attached_transcript_status",
        "attached_transcript_commit",
        "attached_transcript_path",
    ):
        if key not in release_check:
            raise ReleaseEvidenceSchemaError(f"release_check missing {key}")
    git = _required_object(evidence, "git")
    if not isinstance(git.get("dirty"), bool):
        raise ReleaseEvidenceSchemaError("git.dirty must be a boolean")
    tools = _required_object(evidence, "tools")
    if not isinstance(tools.get("count"), int) or not isinstance(tools.get("names"), list):
        raise ReleaseEvidenceSchemaError("tools must include count and names")
    filesystem = _required_object(evidence, "filesystem")
    support = filesystem.get("support")
    if not isinstance(support, dict):
        raise ReleaseEvidenceSchemaError("filesystem must include support evidence")
    if support.get("status") not in {"supported", "degraded", "unsupported"}:
        raise ReleaseEvidenceSchemaError("filesystem support status is invalid")
    if not isinstance(support.get("local_preview_security_supported"), bool):
        raise ReleaseEvidenceSchemaError(
            "filesystem support must include local_preview_security_supported"
        )
    probe = filesystem.get("probe")
    if not isinstance(probe, dict) or probe.get("touches_workspace") is not False:
        raise ReleaseEvidenceSchemaError("filesystem probe must not touch workspace files")
    review_docs = evidence.get("review_docs")
    if not isinstance(review_docs, list):
        raise ReleaseEvidenceSchemaError("review_docs must be a list")
    for item in review_docs:
        if not isinstance(item, dict):
            raise ReleaseEvidenceSchemaError("review_docs entries must be objects")
        metadata = _json_object(item)
        if not isinstance(metadata.get("path"), str):
            raise ReleaseEvidenceSchemaError("review_docs entries require path")
        if not str(metadata.get("sha256", "")).startswith("sha256:"):
            raise ReleaseEvidenceSchemaError("review_docs entries require sha256 digest")
        if not isinstance(metadata.get("bytes"), int):
            raise ReleaseEvidenceSchemaError("review_docs entries require byte count")
    text = json.dumps(evidence, sort_keys=True)
    for marker in SECRET_MARKERS:
        if marker.lower() in text.lower():
            raise ReleaseEvidenceSchemaError(f"secret-like marker present: {marker}")


def _project_marker_status(repo_root: Path) -> dict[str, bool]:
    return {marker: repo_root.joinpath(marker).exists() for marker in PROJECT_MARKERS}


def _release_check(
    enabled: bool,
    *,
    transcript: Path | None,
    observed_status: str | None,
    observed_commit: str | None,
    current_commit: str,
) -> dict[str, Any]:
    transcript_exists = transcript.exists() if transcript is not None else False
    transcript_path = transcript.as_posix() if transcript is not None else None
    if not enabled:
        status = observed_status or "not_run"
        return {
            "gate_executed_by_release_packet": False,
            "gate_status": "not_run",
            "attached_transcript_exists": transcript_exists,
            "attached_transcript_path": transcript_path,
            "attached_transcript_status": status,
            "attached_transcript_commit": observed_commit
            or (current_commit if transcript is not None else None),
        }
    completed = subprocess.run(
        ["make", "release-check"],
        check=False,
        capture_output=True,
        text=True,
    )
    status = "passed" if completed.returncode == 0 else "failed"
    return {
        "gate_executed_by_release_packet": True,
        "gate_status": status,
        "gate_returncode": completed.returncode,
        "attached_transcript_exists": transcript_exists,
        "attached_transcript_path": transcript_path,
        "attached_transcript_status": observed_status or status,
        "attached_transcript_commit": observed_commit or current_commit,
    }


def _manifest_lock_is_current(
    *,
    manifest_dir: Path,
    lock_path: Path,
    registry: ToolRegistry,
) -> bool:
    records = [
        ManifestLockRecord(
            path=tool.source_path,
            name=tool.manifest.name,
            version=tool.manifest.version,
            manifest_hash=tool.manifest_hash,
        )
        for tool in registry.list_tools()
    ]
    expected = manifest_lock_payload(
        manifest_dir=manifest_dir,
        lock_path=lock_path,
        records=records,
    )
    current = json.loads(lock_path.read_text(encoding="utf-8"))
    return bool(current == expected)


def _audit_snapshot(audit_writer: AuditWriter) -> dict[str, Any]:
    if not audit_writer.db_path.exists():
        return {
            "configured": True,
            "db_path": audit_writer.db_path.as_posix(),
            "log_path": audit_writer.jsonl_path.as_posix(),
            "verification": "not_initialized",
        }
    return {
        "configured": True,
        "db_path": audit_writer.db_path.as_posix(),
        "log_path": audit_writer.jsonl_path.as_posix(),
        "verification": audit_writer.verify_chain().as_dict(),
    }


def _json_object(value: dict[Any, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise ReleaseEvidenceSchemaError("release evidence keys must be strings")
        result[key] = item
    return result


def _required_object(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ReleaseEvidenceSchemaError(f"{key} must be an object")
    return _json_object(value)


def _git(args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())

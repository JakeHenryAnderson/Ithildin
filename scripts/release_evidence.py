"""Emit a local public-preview release evidence snapshot without secrets."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ithildin_api.config import Settings
from ithildin_api.identity import PrincipalRegistry
from ithildin_api.manifest_lock import ManifestLockRecord, manifest_lock_payload
from ithildin_api.policy import load_policy_engine
from ithildin_api.registry import ToolRegistry
from ithildin_api.security_status import security_status
from ithildin_api.storage import storage_status
from ithildin_api.telemetry import configure_telemetry
from ithildin_audit_core import AuditWriter


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-release",
        action="store_true",
        help="run make release-check before writing the snapshot",
    )
    args = parser.parse_args()

    release_check = _release_check(args.check_release)
    settings = Settings(admin_token="release-evidence-token")  # type: ignore[call-arg]
    registry = ToolRegistry.load(
        settings.manifest_dir,
        lock_path=settings.manifest_lock_path,
        require_lock=settings.require_manifest_lock,
    )
    principal_registry = PrincipalRegistry.load(
        settings.principal_registry_path,
        require_registry=settings.require_known_principals,
    )
    policy = load_policy_engine(settings)
    audit_writer = AuditWriter(settings.db_path, settings.audit_log_path)
    manifest_lock_current = _manifest_lock_is_current(
        manifest_dir=settings.manifest_dir,
        lock_path=settings.manifest_lock_path,
        registry=registry,
    )

    snapshot = {
        "generated_at": datetime.now(UTC).isoformat(),
        "git": {
            "commit": _git(["rev-parse", "HEAD"]),
            "branch": _git(["branch", "--show-current"]),
            "dirty": bool(_git(["status", "--short"])),
        },
        "release_check": release_check,
        "manifest_lock": {
            "path": settings.manifest_lock_path.as_posix(),
            "required": settings.require_manifest_lock,
            "current": manifest_lock_current,
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
        "storage": storage_status(settings),
        "telemetry": configure_telemetry(settings).status(),
        "security": security_status(settings),
        "audit": _audit_snapshot(audit_writer),
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
            "cryptographic signing or external notarization",
        ],
    }
    json.dump(snapshot, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


def _release_check(enabled: bool) -> dict[str, Any]:
    if not enabled:
        return {"executed": False, "status": "not_run"}
    completed = subprocess.run(
        ["make", "release-check"],
        check=False,
        capture_output=True,
        text=True,
    )
    return {
        "executed": True,
        "status": "passed" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
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
    return current == expected


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

"""Emit a secret-free v0.2 review release packet summary."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
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
from ithildin_api.workspaces import WorkspaceRegistry
from ithildin_audit_core import AuditWriter

REVIEW_DOCS = [
    "README.md",
    "docs/codex/v0.2-review-packet.md",
    "docs/codex/v0.2-planning-seed.md",
    "docs/codex/v0.1-security-test-matrix.md",
    "docs/codex/evidence-contracts.md",
    "docs/codex/threat-model-and-non-goals.md",
    "docs/codex/local-preview-release.md",
]

PROJECT_MARKERS = (
    "pyproject.toml",
    "Makefile",
    "apps/api",
    "apps/mcp-server",
    "tool-manifests.lock.json",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    marker_status = _project_marker_status(repo_root)
    missing_markers = [
        marker for marker, present in marker_status.items() if not present
    ]
    if missing_markers:
        print(
            "release packet must be run from the Ithildin repo root; "
            f"missing markers: {', '.join(missing_markers)}",
            file=sys.stderr,
        )
        return 1

    packet = build_packet(repo_root, marker_status)
    if args.json:
        json.dump(packet, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(render_markdown(packet))
    return 0


def build_packet(repo_root: Path, marker_status: dict[str, bool]) -> dict[str, Any]:
    settings = Settings(admin_token="ithildin_admin_release_packet_placeholder_000000000000")
    registry = ToolRegistry.load(
        settings.manifest_dir,
        lock_path=settings.manifest_lock_path,
        require_lock=settings.require_manifest_lock,
    )
    policy = load_policy_engine(settings)
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
    audit_writer = AuditWriter(settings.db_path, settings.audit_log_path)
    tools = registry.list_tools()

    return {
        "repo": {
            "repo_root": repo_root.as_posix(),
            "current_working_directory": Path.cwd().resolve().as_posix(),
            "project_markers": marker_status,
        },
        "git": {
            "commit": _git(["rev-parse", "HEAD"]),
            "branch": _git(["branch", "--show-current"]),
            "dirty": bool(_git(["status", "--short"])),
        },
        "release_check": {
            "command": "make release-check",
            "status": "not_run_by_release_packet",
        },
        "manifest_lock": {
            "path": settings.manifest_lock_path.as_posix(),
            "required": settings.require_manifest_lock,
            "current": _manifest_lock_is_current(
                manifest_dir=settings.manifest_dir,
                lock_path=settings.manifest_lock_path,
                registry=registry,
            ),
        },
        "tools": {
            "count": len(tools),
            "names": [tool.manifest.name for tool in tools],
        },
        "policy": policy.status(),
        "principals": {
            **principal_registry.status(),
            "required": settings.require_known_principals,
        },
        "workspaces": workspace_registry.status(),
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
            "external audit anchoring and hosted supply-chain signing",
        ],
        "review_docs": REVIEW_DOCS,
    }


def render_markdown(packet: dict[str, Any]) -> str:
    audit_verification = packet["audit"]["verification"]
    audit_valid = _audit_value(audit_verification, "valid")
    audit_head = _audit_value(audit_verification, "head_hash")
    audit_count = _audit_value(audit_verification, "event_count")
    principal_count = (
        f"{packet['principals']['enabled_count']}/{packet['principals']['count']}"
    )
    workspace_count = (
        f"{packet['workspaces']['enabled_count']}/{packet['workspaces']['count']}"
    )
    remote_mcp_enabled = str(
        packet["security"]["local_only"]["remote_mcp_enabled"]
    ).lower()
    wildcard_cors = str(packet["security"]["cors"]["wildcard_allowed"]).lower()

    lines = [
        "# Ithildin v0.2 Review Release Packet",
        "",
        "## Repository",
        "",
        f"- repo root: `{packet['repo']['repo_root']}`",
        f"- commit: `{packet['git']['commit']}`",
        f"- branch: `{packet['git']['branch']}`",
        f"- dirty: `{str(packet['git']['dirty']).lower()}`",
        "",
        "## Required Gate",
        "",
        "- run `make release-check` before attaching this packet to a review handoff;",
        f"- packet status: `{packet['release_check']['status']}`.",
        "",
        "## Trust Evidence",
        "",
        f"- manifest lock current: `{str(packet['manifest_lock']['current']).lower()}`",
        f"- policy engine: `{packet['policy']['engine']}`",
        f"- policy hash: `{packet['policy']['policy_hash']}`",
        f"- principals: `{principal_count}` enabled",
        f"- workspaces: `{workspace_count}` enabled",
        f"- audit valid: `{str(audit_valid).lower()}`",
        f"- audit events: `{audit_count}`",
        f"- audit head: `{audit_head}`",
        "",
        "## Tools",
        "",
        f"- count: `{packet['tools']['count']}`",
        *[f"- `{name}`" for name in packet["tools"]["names"]],
        "",
        "## Security Posture",
        "",
        f"- production ready: `{str(packet['security']['production_ready']).lower()}`",
        f"- remote MCP enabled: `{remote_mcp_enabled}`",
        f"- wildcard CORS: `{wildcard_cors}`",
        f"- storage backend: `{packet['storage']['runtime_backend']}`",
        f"- telemetry enabled: `{str(packet['telemetry']['enabled']).lower()}`",
        "",
        "## Deferred Boundaries",
        "",
        *[f"- {boundary}" for boundary in packet["deferred_boundaries"]],
        "",
        "## Review Documents",
        "",
        *[f"- [{doc}]({doc})" for doc in packet["review_docs"]],
        "",
    ]
    return "\n".join(lines)


def _project_marker_status(repo_root: Path) -> dict[str, bool]:
    return {marker: repo_root.joinpath(marker).exists() for marker in PROJECT_MARKERS}


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


def _audit_value(verification: object, key: str) -> object:
    if isinstance(verification, dict):
        return verification.get(key)
    return "not_initialized"


def _git(args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


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


if __name__ == "__main__":
    raise SystemExit(main())

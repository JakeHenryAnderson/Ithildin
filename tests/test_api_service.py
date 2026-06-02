from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from ithildin_api.app import create_app
from ithildin_api.approvals import ApprovalService, CreateApprovalInput
from ithildin_api.config import Settings
from ithildin_api.database import initialize_database
from ithildin_api.manifest_lock import (
    ManifestLockRecord,
    generate_manifest_lock_signing_keypair,
    write_manifest_lock,
    write_manifest_lock_signature,
)
from ithildin_api.patches import PatchApplyAttempt, PatchProposalService
from ithildin_api.registry import ToolRegistry
from ithildin_audit_core import AuditWriter, generate_audit_signing_keypair
from ithildin_policy_core import OpaBundleSource, opa_bundle_hash
from ithildin_schemas import AuditEventType, sha256_digest
from pydantic import ValidationError


def make_settings(
    tmp_path: Path,
    token: str = "test-admin-token",
    http_allowlist: str = "",
) -> Settings:
    manifest_dir = tmp_path / "tool-manifests"
    manifest_dir.mkdir()
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        """
version: test
rules:
  - id: allow_test_reads
    decision: allow
    reason: ok
    match:
      tool.risk: read
    obligations:
      audit_level: full
""",
        encoding="utf-8",
    )
    policy_tests_path = tmp_path / "policy-tests.yaml"
    policy_tests_path.write_text(
        """
version: test-fixtures-v1
cases:
  - id: read_case
    policy_input:
      principal: {id: "agent:test", roles: ["AgentDeveloper"]}
      tool: {name: fs.read, risk: read, version: "1.0.0"}
      resource: {type: file, path: README.md, in_scope: true}
      context: {session_id: policy-test}
    expect:
      decision: allow
      matched_rules: [allow_test_reads]
""",
        encoding="utf-8",
    )
    workspace_root = tmp_path / "workspace"
    workspace_registry_path = tmp_path / "workspaces.yaml"
    workspace_registry_path.write_text(
        f"""
version: test-workspaces-v1
default_workspace_id: default
workspaces:
  - id: default
    root: {workspace_root.as_posix()}
    display_name: Default workspace
    enabled: true
""",
        encoding="utf-8",
    )
    return Settings(
        admin_token=token,
        audit_log_path=tmp_path / "audit.jsonl",
        audit_signing_private_key_path=tmp_path / "keys" / "audit-private.pem",
        audit_signing_public_key_path=tmp_path / "keys" / "audit-public.pem",
        db_path=tmp_path / "ithildin.sqlite3",
        manifest_dir=manifest_dir,
        require_manifest_lock=False,
        manifest_lock_signing_private_key_path=tmp_path / "keys" / "manifest-private.pem",
        manifest_lock_signing_public_key_path=tmp_path / "keys" / "manifest-public.pem",
        manifest_lock_signature_path=tmp_path / "signatures" / "tool-manifests.lock.sig.json",
        policy_path=policy_path,
        policy_tests_path=policy_tests_path,
        workspace_root=workspace_root,
        workspace_registry_path=workspace_registry_path,
        http_allowlist=http_allowlist,
    )


def write_manifest(manifest_dir: Path, *, name: str, risk: str, required: list[str]) -> None:
    required_block = "\n".join(f"    - {field}" for field in required)
    manifest_dir.joinpath(f"{name.replace('.', '-')}.yaml").write_text(
        f"""
name: {name}
version: 1.0.0
title: {name}
risk: {risk}
category: filesystem
mcp:
  exposed: true
input_schema:
  type: object
  additionalProperties: false
  required:
{required_block}
  properties:
    path:
      type: string
    proposal_id:
      type: string
    url:
      type: string
""",
        encoding="utf-8",
    )


def write_policy(settings: Settings, rules_yaml: str) -> None:
    settings.policy_path.write_text(f"version: test\nrules:\n{rules_yaml}", encoding="utf-8")


def test_healthz_returns_service_health(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path))

    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ithildin-api"}


def test_missing_admin_token_fails_startup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ITHILDIN_ADMIN_TOKEN", raising=False)

    app = create_app()

    with pytest.raises(ValidationError):
        with TestClient(app):
            pass


def test_admin_status_requires_authentication(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path))

    with TestClient(app) as client:
        response = client.get("/admin/status")

    assert response.status_code == 401
    assert response.json()["detail"] == "missing bearer token"


def test_admin_status_rejects_wrong_bearer_token(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path, token="correct-token"))

    with TestClient(app) as client:
        response = client.get(
            "/admin/status",
            headers={"Authorization": "Bearer wrong-token"},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "invalid bearer token"
    assert "wrong-token" not in response.text


def test_admin_status_ignores_cookie_tokens(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path, token="correct-token"))

    with TestClient(app) as client:
        client.cookies.set("ithildin_admin_token", "correct-token")
        response = client.get("/admin/status")

    assert response.status_code == 401
    assert response.json()["detail"] == "missing bearer token"


def test_admin_status_accepts_correct_bearer_token(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path, token="correct-token"))

    with TestClient(app) as client:
        response = client.get(
            "/admin/status",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ithildin-api",
        "admin": "authenticated",
    }


def test_system_status_requires_auth_and_returns_trust_summary(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, token="correct-token", http_allowlist="https://example.com")
    write_manifest(settings.manifest_dir, name="fs.read", risk="read", required=["path"])
    app = create_app(settings)

    with TestClient(app) as client:
        unauthenticated = client.get("/system/status")
        response = client.get(
            "/system/status",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert unauthenticated.status_code == 401
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "ithildin-api"
    assert payload["tool_count"] == 1
    assert payload["manifest_lock"] == {
        "required": False,
        "path": settings.manifest_lock_path.as_posix(),
        "current": {
            "verified": False,
            "required": False,
            "error": None,
        },
        "signature": {
            "required": False,
            "signature_path": settings.manifest_lock_signature_path.as_posix(),
            "public_key_configured": False,
            "signature_configured": False,
            "verified": False,
            "key_id": None,
            "lock_sha256": None,
        },
        "signature_startup": {
            "required": False,
            "signature_path": settings.manifest_lock_signature_path.as_posix(),
            "public_key_configured": False,
            "signature_configured": False,
            "verified": False,
            "key_id": None,
            "lock_sha256": None,
        },
        "signature_drift": False,
    }
    assert payload["principals"]["required"] is True
    assert payload["principals"]["count"] >= 1
    assert payload["principals"]["enabled_count"] >= 1
    assert payload["workspaces"] == {
        "required": True,
        "path": settings.workspace_registry_path.as_posix(),
        "default_workspace_id": "default",
        "count": 1,
        "enabled_count": 1,
    }
    assert payload["filesystem"]["support"]["status"] in {
        "supported",
        "degraded",
        "unsupported",
    }
    assert payload["filesystem"]["probe"] == {
        "uses_temporary_directory": True,
        "touches_workspace": False,
    }
    assert payload["storage"]["runtime_backend"] == "sqlite"
    assert payload["storage"]["sqlite"]["runtime_enabled"] is True
    assert payload["storage"]["postgres"]["runtime_enabled"] is False
    assert payload["telemetry"] == {
        "enabled": False,
        "service_name": "ithildin-api",
        "console_export": False,
        "otlp_endpoint_configured": False,
        "exporters": [],
    }
    assert payload["security"]["production_ready"] is False
    assert payload["security"]["cors"]["wildcard_allowed"] is False
    assert payload["security"]["local_only"]["remote_mcp_enabled"] is False
    assert payload["security"]["admin_token"] == {
        "recommended_min_length": 32,
        "length_ok": False,
        "contains_whitespace": False,
        "weak": True,
    }
    assert payload["security"]["admin_api_auth"] == {
        "scheme": "bearer_token",
        "credential_source": "Authorization header",
        "cookie_auth_enabled": False,
        "server_sessions_enabled": False,
        "production_identity": False,
        "scope": "single local admin token",
    }
    assert payload["policy"]["engine"] == "yaml"
    assert payload["policy"]["policy_hash"].startswith("sha256:")
    assert payload["audit"] == {
        "valid": True,
        "event_count": 0,
        "head_hash": "sha256:" + ("0" * 64),
    }
    assert payload["redaction"] == {
        "baseline_enabled": True,
        "baseline_key_count": 10,
        "baseline_pattern_count": 7,
        "extra_key_count": 0,
        "extra_pattern_count": 0,
    }
    assert payload["limits"]["max_read_bytes"] == settings.max_read_bytes
    assert payload["limits"]["max_patch_bytes"] == settings.max_patch_bytes
    assert payload["limits"]["http_allowlist_configured"] is True


def test_principal_endpoints_require_auth_and_return_records(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path, token="correct-token"))

    with TestClient(app) as client:
        unauthenticated = client.get("/principals")
        response = client.get(
            "/principals",
            headers={"Authorization": "Bearer correct-token"},
        )
        detail_response = client.get(
            "/principals/agent:local-dev",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert unauthenticated.status_code == 401
    assert response.status_code == 200
    principals = response.json()["principals"]
    assert any(principal["id"] == "agent:local-dev" for principal in principals)
    assert detail_response.status_code == 200
    assert detail_response.json()["roles"] == ["AgentDeveloper"]


def test_unknown_principal_endpoint_returns_404(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path, token="correct-token"))

    with TestClient(app) as client:
        response = client.get(
            "/principals/agent:missing",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert response.status_code == 404
    assert "unknown principal" in response.json()["detail"]


def test_workspace_endpoint_requires_auth_and_returns_records(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path, token="correct-token"))

    with TestClient(app) as client:
        unauthenticated = client.get("/workspaces")
        response = client.get(
            "/workspaces",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert unauthenticated.status_code == 401
    assert response.status_code == 200
    assert response.json()["workspaces"] == [
        {
            "id": "default",
            "display_name": "Default workspace",
            "enabled": True,
            "metadata": {},
        }
    ]


def test_sample_admin_token_requires_explicit_demo_flag(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, token="dev-admin-token-change-me")
    app = create_app(settings)

    with pytest.raises(RuntimeError, match="sample admin token"):
        with TestClient(app):
            pass


def test_sample_admin_token_demo_flag_reports_warning(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, token="dev-admin-token-change-me")
    settings.allow_dev_admin_token = True
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.get(
            "/system/status",
            headers={"Authorization": "Bearer dev-admin-token-change-me"},
        )

    assert response.status_code == 200
    security = response.json()["security"]
    assert security["dev_admin_token"] == {
        "sample_token_active": True,
        "explicitly_allowed": True,
    }
    assert security["admin_token"] == {
        "recommended_min_length": 32,
        "length_ok": False,
        "contains_whitespace": False,
        "weak": False,
    }
    assert security["warnings"] == ["sample admin token is enabled for local demo use"]


def test_cors_origins_are_local_only(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path))

    cors = next(
        middleware
        for middleware in app.user_middleware
        if getattr(middleware.cls, "__name__", "") == "CORSMiddleware"
    )
    cors_kwargs = cast(dict[str, Any], cors.kwargs)
    allow_origins = cast(list[str], cors_kwargs["allow_origins"])

    assert "*" not in allow_origins
    assert all(
        origin.startswith(("http://127.0.0.1:", "http://localhost:"))
        for origin in allow_origins
    )
    assert cors_kwargs["allow_credentials"] is False


def test_postgres_storage_backend_fails_closed(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    settings.storage_backend = "postgres"
    settings.postgres_dsn = "postgresql://ithildin@example.invalid/ithildin"
    app = create_app(settings)

    with pytest.raises(RuntimeError, match="not runtime-enabled"):
        with TestClient(app):
            pass


def test_storage_status_reports_postgres_readiness_target(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.postgres_dsn = "postgresql://ithildin@example.invalid/ithildin"
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.get(
            "/system/status",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert response.status_code == 200
    storage = response.json()["storage"]
    assert storage["runtime_backend"] == "sqlite"
    assert storage["postgres"] == {
        "configured": True,
        "dsn_configured": True,
        "runtime_enabled": False,
        "readiness": "configured_not_runtime_enabled",
    }


def test_telemetry_status_reports_enabled_console_export(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.otel_enabled = True
    settings.otel_console_export = True
    settings.otel_service_name = "ithildin-test"
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.get(
            "/system/status",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert response.status_code == 200
    telemetry = response.json()["telemetry"]
    assert telemetry["enabled"] is True
    assert telemetry["service_name"] == "ithildin-test"
    assert telemetry["console_export"] is True
    assert telemetry["otlp_endpoint_configured"] is False
    assert telemetry["exporters"] == ["console"]


def test_app_startup_requires_principal_registry_when_configured(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    settings.principal_registry_path = tmp_path / "missing-principals.yaml"
    settings.require_known_principals = True
    app = create_app(settings)

    with pytest.raises(RuntimeError, match="principal registry not found"):
        with TestClient(app):
            pass


def test_app_startup_requires_workspace_registry_when_configured(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    settings.workspace_registry_path = tmp_path / "missing-workspaces.yaml"
    settings.require_known_workspaces = True
    app = create_app(settings)

    with pytest.raises(RuntimeError, match="workspace registry not found"):
        with TestClient(app):
            pass


def test_create_get_approve_and_deny_approval_endpoints(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path, token="correct-token"))

    with TestClient(app) as client:
        create_response = client.post(
            "/approvals",
            headers={"Authorization": "Bearer correct-token"},
            json={
                "principal": {"id": "agent:local-dev"},
                "tool_name": "fs.apply_patch",
                "resource": {"path": "/workspace/app.py"},
                "summary": "Modify app.py",
                "one_time_scope": {"tool_name": "fs.apply_patch"},
            },
        )
        created = create_response.json()
        get_response = client.get(
            f"/approvals/{created['approval_id']}",
            headers={"Authorization": "Bearer correct-token"},
        )
        approve_response = client.post(
            f"/approvals/{created['approval_id']}/approve",
            headers={"Authorization": "Bearer correct-token"},
            json={"decision": "approve", "decided_by": "user:alice"},
        )

        deny_create_response = client.post(
            "/approvals",
            headers={"Authorization": "Bearer correct-token"},
            json={
                "principal": {"id": "agent:local-dev"},
                "tool_name": "fs.apply_patch",
                "resource": {"path": "/workspace/other.py"},
                "summary": "Modify other.py",
                "one_time_scope": {"tool_name": "fs.apply_patch"},
            },
        )
        deny_created = deny_create_response.json()
        deny_response = client.post(
            f"/approvals/{deny_created['approval_id']}/deny",
            headers={"Authorization": "Bearer correct-token"},
            json={"decision": "deny", "decided_by": "user:alice", "reason": "not now"},
        )

    assert create_response.status_code == 200
    assert created["status"] == "pending"
    assert get_response.status_code == 200
    assert get_response.json()["approval_id"] == created["approval_id"]
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"
    assert deny_response.status_code == 200
    assert deny_response.json()["status"] == "denied"


def test_approval_mutation_routes_reject_body_decision_mismatch(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path, token="correct-token"))

    with TestClient(app) as client:
        create_response = client.post(
            "/approvals",
            headers={"Authorization": "Bearer correct-token"},
            json={
                "principal": {"id": "agent:local-dev"},
                "tool_name": "fs.apply_patch",
                "resource": {"path": "/workspace/app.py"},
                "summary": "Modify app.py",
                "one_time_scope": {"tool_name": "fs.apply_patch"},
            },
        )
        approval_id = create_response.json()["approval_id"]
        approve_mismatch = client.post(
            f"/approvals/{approval_id}/approve",
            headers={"Authorization": "Bearer correct-token"},
            json={"decision": "deny", "decided_by": "user:alice"},
        )
        deny_mismatch = client.post(
            f"/approvals/{approval_id}/deny",
            headers={"Authorization": "Bearer correct-token"},
            json={"decision": "approve", "decided_by": "user:alice"},
        )

    assert approve_mismatch.status_code == 400
    assert approve_mismatch.json()["detail"] == "decision must be approve"
    assert deny_mismatch.status_code == 400
    assert deny_mismatch.json()["detail"] == "decision must be deny"


def test_approval_list_requires_auth_and_supports_status_filter(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path, token="correct-token"))

    with TestClient(app) as client:
        unauthenticated = client.get("/approvals")
        first_response = client.post(
            "/approvals",
            headers={"Authorization": "Bearer correct-token"},
            json={
                "principal": {"id": "agent:local-dev"},
                "tool_name": "fs.patch.apply",
                "resource": {"path": "README.md"},
                "summary": "Apply README patch",
                "one_time_scope": {"tool_name": "fs.patch.apply"},
            },
        )
        second_response = client.post(
            "/approvals",
            headers={"Authorization": "Bearer correct-token"},
            json={
                "principal": {"id": "agent:local-dev"},
                "tool_name": "fs.patch.apply",
                "resource": {"path": "other.md"},
                "summary": "Apply other patch",
                "one_time_scope": {"tool_name": "fs.patch.apply"},
            },
        )
        client.post(
            f"/approvals/{first_response.json()['approval_id']}/approve",
            headers={"Authorization": "Bearer correct-token"},
            json={"decision": "approve", "decided_by": "user:alice"},
        )
        all_response = client.get(
            "/approvals",
            headers={"Authorization": "Bearer correct-token"},
        )
        pending_response = client.get(
            "/approvals?status=pending",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert unauthenticated.status_code == 401
    assert second_response.status_code == 200
    assert [approval["status"] for approval in all_response.json()["approvals"]] == [
        "approved",
        "pending",
    ]
    assert [approval["approval_id"] for approval in pending_response.json()["approvals"]] == [
        second_response.json()["approval_id"]
    ]


def test_tools_requires_authentication(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path))

    with TestClient(app) as client:
        response = client.get("/tools")

    assert response.status_code == 401


def test_tools_returns_empty_list_without_manifests(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path))

    with TestClient(app) as client:
        response = client.get(
            "/tools",
            headers={"Authorization": "Bearer test-admin-token"},
        )

    assert response.status_code == 200
    assert response.json() == {"tools": []}


def test_tools_returns_manifest_summaries(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    (settings.manifest_dir / "fs-read.yaml").write_text(
        """
name: fs.read
version: 1.0.0
title: Read file
risk: read
category: filesystem
mcp:
  exposed: true
input_schema:
  type: object
  required: ["path"]
  properties:
    path:
      type: string
""",
        encoding="utf-8",
    )
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.get(
            "/tools?principal=agent:local-dev",
            headers={"Authorization": "Bearer test-admin-token"},
        )

    assert response.status_code == 200
    assert response.json()["tools"] == [
        {
            "name": "fs.read",
            "version": "1.0.0",
            "title": "Read file",
            "risk": "read",
            "category": "filesystem",
            "manifest_hash": response.json()["tools"][0]["manifest_hash"],
            "mcp": {"exposed": True},
        }
    ]
    assert response.json()["tools"][0]["manifest_hash"].startswith("sha256:")


def test_tools_filters_by_trusted_principal_roles(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    write_manifest(settings.manifest_dir, name="fs.read", risk="read", required=["path"])
    write_manifest(settings.manifest_dir, name="http.fetch", risk="network", required=["url"])
    write_manifest(
        settings.manifest_dir,
        name="fs.patch.propose",
        risk="write-proposal",
        required=["path"],
    )
    write_manifest(settings.manifest_dir, name="fs.patch.apply", risk="write", required=["path"])
    app = create_app(settings)

    with TestClient(app) as client:
        all_tools = client.get(
            "/tools",
            headers={"Authorization": "Bearer test-admin-token"},
        )
        developer = client.get(
            "/tools?principal=agent:local-dev",
            headers={"Authorization": "Bearer test-admin-token"},
        )
        read_only = client.get(
            "/tools?principal=agent:readonly",
            headers={"Authorization": "Bearer test-admin-token"},
        )
        auditor = client.get(
            "/tools?principal=user:auditor",
            headers={"Authorization": "Bearer test-admin-token"},
        )
        missing = client.get(
            "/tools?principal=agent:missing",
            headers={"Authorization": "Bearer test-admin-token"},
        )

    assert [tool["name"] for tool in all_tools.json()["tools"]] == [
        "fs.patch.apply",
        "fs.patch.propose",
        "fs.read",
        "http.fetch",
    ]
    assert [tool["name"] for tool in developer.json()["tools"]] == [
        "fs.patch.apply",
        "fs.patch.propose",
        "fs.read",
        "http.fetch",
    ]
    assert [tool["name"] for tool in read_only.json()["tools"]] == ["fs.read"]
    assert [tool["name"] for tool in auditor.json()["tools"]] == ["fs.read"]
    assert missing.json() == {"tools": []}


def test_app_startup_enforces_manifest_lock_when_enabled(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    write_manifest(settings.manifest_dir, name="fs.read", risk="read", required=["path"])
    settings.require_manifest_lock = True
    settings.manifest_lock_path = tmp_path / "tool-manifests.lock.json"
    registry = ToolRegistry.load(settings.manifest_dir)
    write_manifest_lock(
        manifest_dir=settings.manifest_dir,
        lock_path=settings.manifest_lock_path,
        records=[
            ManifestLockRecord(
                path=tool.source_path,
                name=tool.manifest.name,
                version=tool.manifest.version,
                manifest_hash=tool.manifest_hash,
            )
            for tool in registry.list_tools()
        ],
    )
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.get(
            "/tools",
            headers={"Authorization": "Bearer test-admin-token"},
        )

    assert response.status_code == 200
    assert response.json()["tools"][0]["name"] == "fs.read"


def test_app_startup_allows_unsigned_manifest_lock_by_default(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    write_manifest(settings.manifest_dir, name="fs.read", risk="read", required=["path"])
    settings.require_manifest_lock = True
    settings.manifest_lock_path = tmp_path / "tool-manifests.lock.json"
    registry = ToolRegistry.load(settings.manifest_dir)
    write_manifest_lock(
        manifest_dir=settings.manifest_dir,
        lock_path=settings.manifest_lock_path,
        records=[
            ManifestLockRecord(
                path=tool.source_path,
                name=tool.manifest.name,
                version=tool.manifest.version,
                manifest_hash=tool.manifest_hash,
            )
            for tool in registry.list_tools()
        ],
    )

    with TestClient(create_app(settings)) as client:
        response = client.get(
            "/system/status",
            headers={"Authorization": "Bearer test-admin-token"},
        )

    assert response.status_code == 200
    assert response.json()["manifest_lock"]["signature"]["verified"] is False


def test_system_status_reports_current_manifest_lock_drift(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    manifest_path = settings.manifest_dir / "fs-read.yaml"
    write_manifest(settings.manifest_dir, name="fs.read", risk="read", required=["path"])
    settings.require_manifest_lock = True
    settings.manifest_lock_path = tmp_path / "tool-manifests.lock.json"
    registry = ToolRegistry.load(settings.manifest_dir)
    write_manifest_lock(
        manifest_dir=settings.manifest_dir,
        lock_path=settings.manifest_lock_path,
        records=[
            ManifestLockRecord(
                path=tool.source_path,
                name=tool.manifest.name,
                version=tool.manifest.version,
                manifest_hash=tool.manifest_hash,
            )
            for tool in registry.list_tools()
        ],
    )
    app = create_app(settings)

    with TestClient(app) as client:
        manifest_path.write_text(
            manifest_path.read_text(encoding="utf-8").replace("title: fs.read", "title: drift"),
            encoding="utf-8",
        )
        response = client.get(
            "/system/status",
            headers={"Authorization": "Bearer test-admin-token"},
        )

    assert response.status_code == 200
    current = response.json()["manifest_lock"]["current"]
    assert current["required"] is True
    assert current["verified"] is False
    assert "hash mismatch" in current["error"]


def test_app_startup_enforces_signed_manifest_lock_when_enabled(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    write_manifest(settings.manifest_dir, name="fs.read", risk="read", required=["path"])
    settings.require_manifest_lock = True
    settings.require_signed_manifest_lock = True
    settings.manifest_lock_path = tmp_path / "tool-manifests.lock.json"
    registry = ToolRegistry.load(settings.manifest_dir)
    write_manifest_lock(
        manifest_dir=settings.manifest_dir,
        lock_path=settings.manifest_lock_path,
        records=[
            ManifestLockRecord(
                path=tool.source_path,
                name=tool.manifest.name,
                version=tool.manifest.version,
                manifest_hash=tool.manifest_hash,
            )
            for tool in registry.list_tools()
        ],
    )
    generate_manifest_lock_signing_keypair(
        private_key_path=settings.manifest_lock_signing_private_key_path,
        public_key_path=settings.manifest_lock_signing_public_key_path,
    )
    write_manifest_lock_signature(
        lock_path=settings.manifest_lock_path,
        signature_path=settings.manifest_lock_signature_path,
        private_key_path=settings.manifest_lock_signing_private_key_path,
        public_key_path=settings.manifest_lock_signing_public_key_path,
    )

    with TestClient(create_app(settings)) as client:
        response = client.get(
            "/system/status",
            headers={"Authorization": "Bearer test-admin-token"},
        )

    assert response.status_code == 200
    assert response.json()["manifest_lock"]["signature"]["required"] is True
    assert response.json()["manifest_lock"]["signature"]["verified"] is True


def test_app_startup_fails_when_signed_manifest_lock_required_but_missing(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path)
    write_manifest(settings.manifest_dir, name="fs.read", risk="read", required=["path"])
    settings.require_manifest_lock = True
    settings.require_signed_manifest_lock = True
    settings.manifest_lock_path = tmp_path / "tool-manifests.lock.json"
    registry = ToolRegistry.load(settings.manifest_dir)
    write_manifest_lock(
        manifest_dir=settings.manifest_dir,
        lock_path=settings.manifest_lock_path,
        records=[
            ManifestLockRecord(
                path=tool.source_path,
                name=tool.manifest.name,
                version=tool.manifest.version,
                manifest_hash=tool.manifest_hash,
            )
            for tool in registry.list_tools()
        ],
    )
    app = create_app(settings)

    with pytest.raises(RuntimeError):
        with TestClient(app):
            pass


def test_app_startup_fails_for_tampered_manifest_lock(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    manifest_path = settings.manifest_dir / "fs-read.yaml"
    write_manifest(settings.manifest_dir, name="fs.read", risk="read", required=["path"])
    settings.require_manifest_lock = True
    settings.manifest_lock_path = tmp_path / "tool-manifests.lock.json"
    registry = ToolRegistry.load(settings.manifest_dir)
    write_manifest_lock(
        manifest_dir=settings.manifest_dir,
        lock_path=settings.manifest_lock_path,
        records=[
            ManifestLockRecord(
                path=tool.source_path,
                name=tool.manifest.name,
                version=tool.manifest.version,
                manifest_hash=tool.manifest_hash,
            )
            for tool in registry.list_tools()
        ],
    )
    manifest_path.write_text(
        manifest_path.read_text(encoding="utf-8").replace("fs.read", "fs.stat"),
        encoding="utf-8",
    )
    app = create_app(settings)

    with pytest.raises(RuntimeError):
        with TestClient(app):
            pass


def test_policy_preview_requires_authentication(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path))

    with TestClient(app) as client:
        response = client.post("/policy/preview", json={"tool_name": "fs.list", "arguments": {}})

    assert response.status_code == 401


def test_policy_status_requires_authentication_and_returns_evidence(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path))

    with TestClient(app) as client:
        unauthenticated = client.get("/policy/status")
        response = client.get(
            "/policy/status",
            headers={"Authorization": "Bearer test-admin-token"},
        )

    assert unauthenticated.status_code == 401
    assert response.status_code == 200
    assert response.json() == {
        "engine": "yaml",
        "document_version": "test",
        "policy_hash": response.json()["policy_hash"],
        "rule_count": 1,
    }
    assert response.json()["policy_hash"].startswith("sha256:")


def test_policy_status_reports_verified_opa_bundle_evidence(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    settings.policy_engine = "opa"
    settings.opa_url = "http://opa.example:8181"
    settings.opa_bundle_manifest_path = write_opa_bundle(tmp_path)
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.get(
            "/policy/status",
            headers={"Authorization": "Bearer test-admin-token"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["engine"] == "opa"
    assert payload["document_version"] == "opa-test-v1"
    assert payload["bundle_version"] == "opa-test-v1"
    assert payload["bundle_entrypoint"] == "ithildin/decision"
    assert payload["bundle_verified"] is True
    assert payload["policy_hash"] == payload["bundle_hash"]


def test_policy_impact_preview_requires_auth_and_reports_changes(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    write_manifest(settings.manifest_dir, name="fs.read", risk="read", required=["path"])
    app = create_app(settings)
    candidate_yaml = settings.policy_path.read_text(encoding="utf-8").replace(
        "decision: allow",
        "decision: deny",
        1,
    )

    with TestClient(app) as client:
        unauthorized = client.post(
            "/policy/impact-preview",
            json={"candidate_policy_yaml": candidate_yaml},
        )
        response = client.post(
            "/policy/impact-preview",
            headers={"Authorization": "Bearer correct-token"},
            json={"candidate_policy_yaml": candidate_yaml},
        )

    assert unauthorized.status_code == 401
    assert response.status_code == 200
    payload = response.json()
    assert payload["current"]["failed"] == 0
    assert payload["candidate"]["failed"] >= 1
    assert payload["changed_cases"]


def test_policy_impact_preview_rejects_invalid_candidate_yaml(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/policy/impact-preview",
            headers={"Authorization": "Bearer correct-token"},
            json={"candidate_policy_yaml": "version: ["},
        )

    assert response.status_code == 400
    assert "invalid YAML policy" in response.json()["detail"]


def test_policy_preview_allows_known_read_tool(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    settings.workspace_root.mkdir(parents=True)
    settings.workspace_root.joinpath("README.md").write_text("hello\n", encoding="utf-8")
    write_manifest(settings.manifest_dir, name="fs.read", risk="read", required=["path"])
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/policy/preview",
            headers={"Authorization": "Bearer test-admin-token"},
            json={"tool_name": "fs.read", "arguments": {"path": "README.md"}},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid_arguments"] is True
    assert payload["decision"] == "allow"
    assert payload["matched_rules"] == ["allow_test_reads"]
    assert payload["resource"] == {
        "type": "file",
        "in_scope": True,
        "risk": "read",
        "path": "README.md",
        "workspace_id": "default",
    }
    assert payload["policy_input"]["principal"] == {
        "id": "admin:local-ui",
        "type": "admin",
        "roles": ["Admin", "Approver", "Auditor"],
    }
    assert payload["manifest_hash"].startswith("sha256:")
    assert payload["policy_engine"] == "yaml"
    assert payload["policy_document_version"] == "test"
    assert payload["policy_hash"] == payload["policy_version"]
    assert payload["policy_hash"].startswith("sha256:")
    assert payload["decision_evidence"] == {
        "decision": "allow",
        "reason": "ok",
        "policy_engine": "yaml",
        "policy_hash": payload["policy_hash"],
        "policy_version": payload["policy_version"],
        "policy_document_version": "test",
        "matched_rules": ["allow_test_reads"],
        "obligation_keys": ["audit_level"],
        "tool_name": "fs.read",
        "tool_version": "1.0.0",
        "tool_risk": "read",
        "manifest_hash": payload["manifest_hash"],
        "resource_type": "file",
        "resource_in_scope": True,
        "principal_id": "admin:local-ui",
        "principal_roles": ["Admin", "Approver", "Auditor"],
        "session_id": "policy-preview",
    }


def test_policy_preview_requires_approval_for_write_tool(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    write_manifest(
        settings.manifest_dir,
        name="fs.patch.apply",
        risk="write",
        required=["proposal_id"],
    )
    write_policy(
        settings,
        """
  - id: require_write_approval
    decision: require_approval
    reason: writes require approval
    match:
      tool.risk: write
""",
    )
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/policy/preview",
            headers={"Authorization": "Bearer test-admin-token"},
            json={
                "tool_name": "fs.patch.apply",
                "arguments": {"proposal_id": "patch_1234"},
                "principal": {"id": "agent:test", "roles": ["Developer"]},
                "session_id": "preview-test",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid_arguments"] is True
    assert payload["decision"] == "require_approval"
    assert payload["reason"] == "writes require approval"
    assert payload["matched_rules"] == ["require_write_approval"]
    assert payload["policy_input"]["principal"] == {
        "id": "agent:test",
        "type": "agent",
        "roles": ["AgentDeveloper"],
    }
    assert payload["policy_input"]["context"] == {"session_id": "preview-test"}
    assert payload["decision_evidence"]["decision"] == "require_approval"
    assert payload["decision_evidence"]["session_id"] == "preview-test"
    assert payload["decision_evidence"]["principal_id"] == "agent:test"


def test_policy_preview_denies_out_of_scope_filesystem_path(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    settings.workspace_root.mkdir(parents=True)
    write_manifest(settings.manifest_dir, name="fs.read", risk="read", required=["path"])
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/policy/preview",
            headers={"Authorization": "Bearer test-admin-token"},
            json={"tool_name": "fs.read", "arguments": {"path": "../README.md"}},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid_arguments"] is True
    assert payload["decision"] == "deny"
    assert payload["resource"]["in_scope"] is False
    assert payload["resource"]["scope_error"] == "path traversal is outside the workspace scope"


def test_policy_preview_denies_unknown_principal_without_side_effects(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    write_manifest(settings.manifest_dir, name="fs.read", risk="read", required=["path"])
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/policy/preview",
            headers={"Authorization": "Bearer test-admin-token"},
            json={
                "tool_name": "fs.read",
                "arguments": {"path": "README.md"},
                "principal": {"id": "agent:missing", "roles": ["Admin"]},
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "deny"
    assert payload["valid_arguments"] is False
    assert "unknown principal" in payload["reason"]
    assert payload["policy_input"] is None
    assert _row_count(settings.db_path, "audit_events") == 0


def test_policy_preview_empty_principal_does_not_default_to_admin(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    write_manifest(settings.manifest_dir, name="fs.read", risk="read", required=["path"])
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/policy/preview",
            headers={"Authorization": "Bearer test-admin-token"},
            json={
                "tool_name": "fs.read",
                "arguments": {"path": "README.md"},
                "principal": {},
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "deny"
    assert payload["policy_evaluated"] is False
    assert payload["deny_source"] == "pre_policy"
    assert "principal id is required" in payload["reason"]
    assert payload["policy_input"] is None
    assert _row_count(settings.db_path, "audit_events") == 0


def test_policy_preview_denies_role_unauthorized_principal(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    write_manifest(settings.manifest_dir, name="http.fetch", risk="network", required=["url"])
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/policy/preview",
            headers={"Authorization": "Bearer test-admin-token"},
            json={
                "tool_name": "http.fetch",
                "arguments": {"url": "https://example.com/data"},
                "principal": {"id": "agent:readonly", "roles": ["Admin"]},
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "deny"
    assert payload["valid_arguments"] is False
    assert "not authorized" in payload["reason"]
    assert payload["policy_input"] is None
    assert _row_count(settings.db_path, "audit_events") == 0


def test_policy_preview_allows_allowlisted_http_fetch(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, http_allowlist="https://example.com")
    write_manifest(settings.manifest_dir, name="http.fetch", risk="network", required=["url"])
    write_policy(
        settings,
        """
  - id: allow_network
    decision: allow
    reason: network allowed
    match:
      tool.risk: network
      resource.in_scope: true
""",
    )
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/policy/preview",
            headers={"Authorization": "Bearer test-admin-token"},
            json={"tool_name": "http.fetch", "arguments": {"url": "https://example.com/data"}},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid_arguments"] is True
    assert payload["decision"] == "allow"
    assert payload["matched_rules"] == ["allow_network"]
    assert payload["resource"] == {
        "type": "network",
        "in_scope": True,
        "risk": "network",
        "url": "https://example.com/data",
        "scheme": "https",
        "host": "example.com",
    }
    assert _row_count(settings.db_path, "audit_events") == 0


def test_policy_preview_denies_unallowlisted_http_fetch_without_audit(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    write_manifest(settings.manifest_dir, name="http.fetch", risk="network", required=["url"])
    write_policy(
        settings,
        """
  - id: allow_network
    decision: allow
    reason: network allowed
    match:
      tool.risk: network
      resource.in_scope: true
""",
    )
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/policy/preview",
            headers={"Authorization": "Bearer test-admin-token"},
            json={"tool_name": "http.fetch", "arguments": {"url": "https://example.com/data"}},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid_arguments"] is True
    assert payload["decision"] == "deny"
    assert payload["resource"]["in_scope"] is False
    assert _row_count(settings.db_path, "audit_events") == 0


def test_policy_preview_malformed_http_resource_omits_raw_query_string(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, http_allowlist="https://example.com")
    write_manifest(settings.manifest_dir, name="http.fetch", risk="network", required=["url"])
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/policy/preview",
            headers={"Authorization": "Bearer test-admin-token"},
            json={
                "tool_name": "http.fetch",
                "arguments": {"url": " https://example.com/data?token=secret-value"},
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid_arguments"] is True
    assert payload["decision"] == "deny"
    assert "secret-value" not in json.dumps(payload)
    assert "url" not in payload["resource"]
    assert payload["resource"]["raw_url_hash"].startswith("sha256:")
    assert _row_count(settings.db_path, "audit_events") == 0


def test_policy_preview_invalid_http_arguments_use_generic_resource(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, http_allowlist="https://example.com")
    write_manifest(settings.manifest_dir, name="http.fetch", risk="network", required=["url"])
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/policy/preview",
            headers={"Authorization": "Bearer test-admin-token"},
            json={
                "tool_name": "http.fetch",
                "arguments": {
                    "url": "https://example.com/data",
                    "headers": {"authorization": "Bearer secret-value"},
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid_arguments"] is False
    assert payload["decision"] == "deny"
    assert payload["resource"] == {"type": "tool_call", "in_scope": False}
    assert "secret-value" not in json.dumps(payload)
    assert _row_count(settings.db_path, "audit_events") == 0


def test_policy_preview_invalid_arguments_do_not_echo_secret_values(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, http_allowlist="https://example.com")
    write_manifest(settings.manifest_dir, name="http.fetch", risk="network", required=["url"])
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/policy/preview",
            headers={"Authorization": "Bearer test-admin-token"},
            json={
                "tool_name": "http.fetch",
                "arguments": {
                    "url": {"token": "secret-value"},
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid_arguments"] is False
    assert payload["policy_evaluated"] is False
    assert payload["deny_source"] == "argument_validation"
    assert "JSON Schema validation failed" in payload["argument_error"]
    assert "secret-value" not in json.dumps(payload)
    assert _row_count(settings.db_path, "audit_events") == 0


def test_policy_preview_unknown_tool_is_safe_and_side_effect_free(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/policy/preview",
            headers={"Authorization": "Bearer test-admin-token"},
            json={"tool_name": "fs.missing", "arguments": {}},
        )

    assert response.status_code == 200
    assert response.json()["decision"] == "deny"
    assert response.json()["valid_arguments"] is False
    assert response.json()["reason"] == "unknown tool"
    assert _row_count(settings.db_path, "audit_events") == 0
    assert _row_count(settings.db_path, "approvals") == 0
    assert _row_count(settings.db_path, "patch_proposals") == 0


def test_policy_preview_invalid_arguments_do_not_evaluate_policy_or_write_audit(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path)
    write_manifest(settings.manifest_dir, name="fs.read", risk="read", required=["path"])
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/policy/preview",
            headers={"Authorization": "Bearer test-admin-token"},
            json={"tool_name": "fs.read", "arguments": {}},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid_arguments"] is False
    assert payload["argument_error"]
    assert payload["decision"] == "deny"
    assert payload["matched_rules"] == []
    assert payload["policy_input"] is None
    assert _row_count(settings.db_path, "audit_events") == 0
    assert _row_count(settings.db_path, "approvals") == 0
    assert _row_count(settings.db_path, "patch_proposals") == 0


def test_patch_proposal_endpoints_require_authentication(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path))

    with TestClient(app) as client:
        response = client.get("/patch-proposals")

    assert response.status_code == 401


def test_patch_proposal_endpoints_return_metadata(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("README.md").write_text("old\n", encoding="utf-8")
    app = create_app(settings)

    with TestClient(app) as client:
        patch_service = cast(PatchProposalService, app.state.patch_proposal_service)
        proposal = patch_service.create_proposal(
            request_id="req_1",
            principal={"id": "agent:test"},
            path="README.md",
            unified_diff="--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-old\n+new\n",
        )
        list_response = client.get(
            "/patch-proposals",
            headers={"Authorization": "Bearer correct-token"},
        )
        get_response = client.get(
            f"/patch-proposals/{proposal.proposal_id}",
            headers={"Authorization": "Bearer correct-token"},
        )
        missing_response = client.get(
            "/patch-proposals/patch_missing",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert list_response.status_code == 200
    assert "unified_diff" not in list_response.json()["patch_proposals"][0]
    assert list_response.json()["patch_proposals"][0]["proposal_id"] == proposal.proposal_id
    assert list_response.json()["patch_proposals"][0]["workspace_id"] == "default"
    assert list_response.json()["patch_proposals"][0]["review"]["stale"] is False
    assert get_response.status_code == 200
    assert get_response.json()["proposal_hash"] == proposal.proposal_hash
    assert get_response.json()["review"]["base_file_hash_matches"] is True
    assert get_response.json()["unified_diff"].startswith("--- a/README.md")
    assert missing_response.status_code == 404


def test_patch_apply_diagnostics_requires_auth_and_reports_clean_state(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path, token="correct-token"))

    with TestClient(app) as client:
        unauthenticated = client.get("/patch-apply-diagnostics")
        authenticated = client.get(
            "/patch-apply-diagnostics",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert unauthenticated.status_code == 401
    assert authenticated.status_code == 200
    payload = authenticated.json()
    assert payload["status"] == "clean"
    assert payload["attempts"] == []
    assert payload["stuck_approvals"] == []


def test_patch_apply_diagnostics_reports_recovery_required_without_sensitive_content(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("README.md").write_text("new\n", encoding="utf-8")
    app = create_app(settings)

    with TestClient(app) as client:
        patch_service = cast(PatchProposalService, app.state.patch_proposal_service)
        approval_service = cast(ApprovalService, app.state.approval_service)
        approval = approval_service.create_pending(
            CreateApprovalInput(
                principal={"id": "agent:test"},
                tool_name="fs.patch.apply",
                resource={"path": "README.md"},
                summary="Apply patch",
                one_time_scope={"proposal_id": "patch_1"},
            )
        )
        approval_service.approve(approval.approval_id, decided_by="admin:test")
        approval_service.begin_execution(approval.approval_id, approval.request_hash)
        now = datetime.now(UTC)
        patch_service.store.create_apply_attempt(
            PatchApplyAttempt(
                attempt_id="pa_test",
                approval_id=approval.approval_id,
                proposal_id="patch_1",
                request_id=approval.request_id,
                workspace_id="default",
                path="README.md",
                proposal_hash="sha256:" + ("1" * 64),
                base_file_hash=sha256_digest("old\n"),
                expected_post_apply_hash=sha256_digest("new\n"),
                status="recovery_required",
                failure_reason="simulated state completion failure",
                created_at=now,
                updated_at=now,
                metadata={"tool_name": "fs.patch.apply"},
            )
        )

        response = client.get(
            "/patch-apply-diagnostics",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert response.status_code == 200
    body = response.text
    payload = response.json()
    assert payload["status"] == "recovery_required"
    assert payload["attempts"][0]["attempt_id"] == "pa_test"
    assert payload["attempts"][0]["current_matches_expected_post_apply_hash"] is True
    assert payload["stuck_approvals"][0]["approval_id"] == approval.approval_id
    assert "new\n" not in body
    assert "--- a/README.md" not in body


def test_approval_review_endpoint_reports_binding_checks(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    write_manifest(
        settings.manifest_dir,
        name="fs.patch.apply",
        risk="write",
        required=["proposal_id"],
    )
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("README.md").write_text("old\n", encoding="utf-8")
    app = create_app(settings)

    with TestClient(app) as client:
        patch_service = cast(PatchProposalService, app.state.patch_proposal_service)
        approval_service = cast(ApprovalService, app.state.approval_service)
        registry = cast(ToolRegistry, app.state.registry)
        policy_evaluator = app.state.policy_evaluator
        proposal = patch_service.create_proposal(
            request_id="req_1",
            principal={"id": "agent:test"},
            path="README.md",
            unified_diff="--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-old\n+new\n",
        )
        tool = registry.get_tool("fs.patch.apply")
        expires_at = datetime.now(UTC) + timedelta(minutes=15)
        request_hash = sha256_digest({"request_id": "req_2"})
        scope = patch_service.approval_scope(
            proposal.proposal_id,
            manifest_hash=tool.manifest_hash,
            manifest_version=tool.manifest.version,
            tool_input_schema_hash=sha256_digest(tool.manifest.input_schema),
            policy_engine=policy_evaluator.engine_name,
            policy_hash=policy_evaluator.policy_hash,
            policy_version=policy_evaluator.policy_hash,
            policy_document_version=policy_evaluator.document_version,
            matched_rules=["allow_test_reads"],
            requesting_principal={"id": "agent:test"},
            request_hash=request_hash,
            expires_at=expires_at,
        )
        approval = approval_service.create_pending(
            CreateApprovalInput(
                request_id="req_2",
                request_hash=request_hash,
                principal={"id": "agent:test"},
                tool_name="fs.patch.apply",
                resource={"path": "README.md"},
                summary="Apply patch",
                one_time_scope=scope,
                expires_at=expires_at,
            )
        )
        response = client.get(
            "/approvals/review?status=pending",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert response.status_code == 200
    reviewed = response.json()["approvals"][0]
    assert reviewed["approval"]["approval_id"] == approval.approval_id
    assert reviewed["review"]["valid"] is True
    assert reviewed["review"]["checks"]["proposal_hash"] is True
    assert reviewed["review"]["proposal"]["base_file_hash_matches"] is True


def test_approval_review_endpoint_reports_runtime_binding_drift(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    write_manifest(
        settings.manifest_dir,
        name="fs.patch.apply",
        risk="write",
        required=["proposal_id"],
    )
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("README.md").write_text("old\n", encoding="utf-8")
    app = create_app(settings)

    with TestClient(app) as client:
        patch_service = cast(PatchProposalService, app.state.patch_proposal_service)
        approval_service = cast(ApprovalService, app.state.approval_service)
        registry = cast(ToolRegistry, app.state.registry)
        policy_evaluator = app.state.policy_evaluator
        proposal = patch_service.create_proposal(
            request_id="req_1",
            principal={"id": "agent:test"},
            path="README.md",
            unified_diff="--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-old\n+new\n",
        )
        tool = registry.get_tool("fs.patch.apply")
        expires_at = datetime.now(UTC) + timedelta(minutes=15)
        request_hash = sha256_digest({"request_id": "req_2"})
        scope = patch_service.approval_scope(
            proposal.proposal_id,
            manifest_hash=tool.manifest_hash,
            manifest_version=tool.manifest.version,
            tool_input_schema_hash=sha256_digest(tool.manifest.input_schema),
            policy_engine=policy_evaluator.engine_name,
            policy_hash=policy_evaluator.policy_hash,
            policy_version="policy-version-original",
            policy_document_version=policy_evaluator.document_version,
            matched_rules=["require_write_approval"],
            requesting_principal={"id": "agent:test"},
            request_hash=request_hash,
            expires_at=expires_at,
        )
        scope["policy_version"] = "policy-version-drifted"
        scope["matched_rules"] = ["wrong_rule"]
        scope["requesting_principal"] = {"id": "agent:other"}
        approval = approval_service.create_pending(
            CreateApprovalInput(
                request_id="req_2",
                request_hash=request_hash,
                principal={"id": "agent:test"},
                tool_name="fs.patch.apply",
                resource={"path": "README.md"},
                summary="Apply patch",
                one_time_scope=scope,
                expires_at=expires_at,
                metadata={
                    "policy_version": "policy-version-original",
                    "matched_rules": ["require_write_approval"],
                },
            )
        )
        response = client.get(
            "/approvals/review?status=pending",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert response.status_code == 200
    reviewed = response.json()["approvals"][0]
    assert reviewed["approval"]["approval_id"] == approval.approval_id
    assert reviewed["review"]["valid"] is False
    assert reviewed["review"]["checks"]["policy_version"] is False
    assert reviewed["review"]["checks"]["matched_rules"] is False
    assert reviewed["review"]["checks"]["requesting_principal"] is False


def test_approve_patch_apply_rejects_stale_binding_review(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    write_manifest(
        settings.manifest_dir,
        name="fs.patch.apply",
        risk="write",
        required=["proposal_id"],
    )
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("README.md").write_text("old\n", encoding="utf-8")
    app = create_app(settings)

    with TestClient(app) as client:
        patch_service = cast(PatchProposalService, app.state.patch_proposal_service)
        approval_service = cast(ApprovalService, app.state.approval_service)
        registry = cast(ToolRegistry, app.state.registry)
        policy_evaluator = app.state.policy_evaluator
        proposal = patch_service.create_proposal(
            request_id="req_1",
            principal={"id": "agent:test"},
            path="README.md",
            unified_diff="--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-old\n+new\n",
        )
        tool = registry.get_tool("fs.patch.apply")
        expires_at = datetime.now(UTC) + timedelta(minutes=15)
        request_hash = sha256_digest({"request_id": "req_2"})
        scope = patch_service.approval_scope(
            proposal.proposal_id,
            manifest_hash=tool.manifest_hash,
            manifest_version=tool.manifest.version,
            tool_input_schema_hash=sha256_digest(tool.manifest.input_schema),
            policy_engine=policy_evaluator.engine_name,
            policy_hash=policy_evaluator.policy_hash,
            policy_version=policy_evaluator.policy_hash,
            policy_document_version=policy_evaluator.document_version,
            matched_rules=["require_write_approval"],
            requesting_principal={"id": "agent:test"},
            request_hash=request_hash,
            expires_at=expires_at,
        )
        scope["proposal_hash"] = "sha256:" + ("0" * 64)
        approval = approval_service.create_pending(
            CreateApprovalInput(
                request_id="req_2",
                request_hash=request_hash,
                principal={"id": "agent:test"},
                tool_name="fs.patch.apply",
                resource={"path": "README.md"},
                summary="Apply patch",
                one_time_scope=scope,
                expires_at=expires_at,
                metadata={"matched_rules": ["require_write_approval"]},
            )
        )

        response = client.post(
            f"/approvals/{approval.approval_id}/approve",
            headers={"Authorization": "Bearer correct-token"},
            json={
                "decision": "approve",
                "decided_by": "admin:test",
            },
        )

    assert response.status_code == 409
    assert "binding review failed" in response.text
    assert approval_service.get(approval.approval_id).status.value == "pending"


def test_audit_events_endpoint_requires_auth_filters_and_bounds_results(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path, token="correct-token"))

    with TestClient(app) as client:
        audit_writer = cast(AuditWriter, app.state.audit_writer)
        audit_writer.write_event(
            event_id="evt_1",
            event_type=AuditEventType.POLICY_EVALUATED,
            request_id="req_1",
            principal={"id": "agent:local-dev"},
            tool_name="fs.read",
        )
        audit_writer.write_event(
            event_id="evt_2",
            event_type=AuditEventType.TOOL_EXECUTION_COMPLETED,
            request_id="req_2",
            principal={"id": "agent:local-dev"},
            tool_name="fs.read",
        )
        unauthenticated = client.get("/audit-events")
        limited_response = client.get(
            "/audit-events?limit=1",
            headers={"Authorization": "Bearer correct-token"},
        )
        filtered_response = client.get(
            "/audit-events?event_type=policy.evaluated&request_id=req_1",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert unauthenticated.status_code == 401
    assert [event["event_id"] for event in limited_response.json()["audit_events"]] == ["evt_2"]
    assert [event["event_id"] for event in filtered_response.json()["audit_events"]] == ["evt_1"]


def test_audit_verification_and_export_endpoints(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path, token="correct-token"))

    with TestClient(app) as client:
        audit_writer = cast(AuditWriter, app.state.audit_writer)
        audit_writer.write_event(
            event_id="evt_1",
            event_type=AuditEventType.POLICY_EVALUATED,
            request_id="req_1",
            principal={"id": "agent:local-dev"},
            tool_name="fs.read",
        )
        unauthenticated_verify = client.get("/audit-events/verify")
        verify_response = client.get(
            "/audit-events/verify",
            headers={"Authorization": "Bearer correct-token"},
        )
        export_response = client.get(
            "/audit-events/export",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert unauthenticated_verify.status_code == 401
    assert verify_response.status_code == 200
    assert verify_response.json()["valid"] is True
    assert verify_response.json()["event_count"] == 1
    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("application/x-ndjson")
    lines = export_response.text.splitlines()
    metadata = json.loads(lines[0])["metadata"]
    assert metadata["verification"]["valid"] is True
    assert metadata["event_count"] == 2
    assert metadata["diagnostics"]["lifecycle"]["status"] == "clean"
    assert json.loads(lines[1])["event_id"] == "evt_1"
    export_event = json.loads(lines[2])
    assert export_event["event_type"] == "audit.exported"
    assert export_event["metadata"]["export_format"] == "jsonl"


def test_audit_diagnostics_endpoint_requires_auth_and_reports_state(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path, token="correct-token"))

    with TestClient(app) as client:
        audit_writer = cast(AuditWriter, app.state.audit_writer)
        audit_writer.write_event(
            event_id="evt_1",
            event_type=AuditEventType.POLICY_EVALUATED,
            request_id="req_1",
            principal={"id": "agent:test"},
        )
        unauthenticated = client.get("/audit-events/diagnostics")
        response = client.get(
            "/audit-events/diagnostics",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert unauthenticated.status_code == 401
    assert response.status_code == 200
    payload = response.json()
    assert payload["category"] == "valid"
    assert payload["lifecycle"]["status"] == "clean"
    assert payload["lifecycle"]["retention_mutation_supported"] is False
    assert payload["verification"]["valid"] is True
    assert payload["verification"]["event_count"] == 1
    assert payload["signing"]["signed_export_available"] is False


def test_signed_audit_export_endpoint_requires_auth_and_keys(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    app = create_app(settings)

    with TestClient(app) as client:
        unauthenticated = client.get("/audit-events/export/signed")
        missing_keys = client.get(
            "/audit-events/export/signed",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert unauthenticated.status_code == 401
    assert missing_keys.status_code == 409
    assert "private key" in missing_keys.json()["detail"]
    assert _row_count(settings.db_path, "audit_events") == 0


def test_signed_audit_export_endpoint_returns_signed_bundle(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    generate_audit_signing_keypair(
        private_key_path=settings.audit_signing_private_key_path,
        public_key_path=settings.audit_signing_public_key_path,
    )
    app = create_app(settings)

    with TestClient(app) as client:
        audit_writer = cast(AuditWriter, app.state.audit_writer)
        event = audit_writer.write_event(
            event_id="evt_1",
            event_type=AuditEventType.POLICY_EVALUATED,
            request_id="req_1",
            principal={"id": "agent:local-dev"},
            tool_name="fs.read",
        )
        response = client.get(
            "/audit-events/export/signed",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert response.status_code == 200
    bundle = response.json()
    assert bundle["bundle_type"] == "ithildin.audit.signed_export"
    assert bundle["metadata"]["head_hash"] != event.event_hash
    assert bundle["metadata"]["event_count"] == 2
    assert bundle["metadata"]["diagnostics"]["lifecycle"]["status"] == "clean"
    assert bundle["events_sha256"].startswith("sha256:")
    assert bundle["signature"]["algorithm"] == "ed25519"
    assert bundle["signature"]["key_id"].startswith("sha256:")
    assert json.loads(bundle["events_jsonl"].splitlines()[0])["event_id"] == "evt_1"
    export_event = json.loads(bundle["events_jsonl"].splitlines()[1])
    assert export_event["event_type"] == "audit.exported"
    assert export_event["metadata"]["export_format"] == "signed_json"


def test_signed_audit_export_endpoint_rejects_unclean_lifecycle(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    generate_audit_signing_keypair(
        private_key_path=settings.audit_signing_private_key_path,
        public_key_path=settings.audit_signing_public_key_path,
    )
    app = create_app(settings)

    with TestClient(app) as client:
        audit_writer = cast(AuditWriter, app.state.audit_writer)
        audit_writer.write_event(
            event_id="evt_1",
            event_type=AuditEventType.POLICY_EVALUATED,
            request_id="req_1",
            principal={"id": "agent:local-dev"},
            tool_name="fs.read",
        )
        settings.audit_log_path.write_text("", encoding="utf-8")
        response = client.get(
            "/audit-events/export/signed",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert response.status_code == 409
    assert "audit lifecycle is not clean" in response.json()["detail"]
    payloads = AuditWriter(settings.db_path, settings.audit_log_path).list_events()
    assert all(payload["event_type"] != "audit.exported" for payload in payloads)


def test_audit_event_list_returns_structured_error_for_corrupt_payload(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    app = create_app(settings)

    with TestClient(app) as client:
        audit_writer = cast(AuditWriter, app.state.audit_writer)
        audit_writer.write_event(
            event_id="evt_1",
            event_type=AuditEventType.POLICY_EVALUATED,
            request_id="req_1",
            principal={"id": "agent:local-dev"},
        )
        with sqlite3.connect(settings.db_path) as connection:
            connection.execute(
                "UPDATE audit_events SET payload_json = ? WHERE event_id = ?",
                ("{", "evt_1"),
            )
            connection.commit()
        response = client.get(
            "/audit-events",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "failed to decode audit event payload"


def test_audit_export_reflects_failed_verification(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    app = create_app(settings)

    with TestClient(app) as client:
        audit_writer = cast(AuditWriter, app.state.audit_writer)
        audit_writer.write_event(
            event_id="evt_1",
            event_type=AuditEventType.POLICY_EVALUATED,
            request_id="req_1",
            principal={"id": "agent:local-dev"},
            tool_name="fs.read",
        )
        with sqlite3.connect(settings.db_path) as connection:
            payload_json = connection.execute(
                "SELECT payload_json FROM audit_events WHERE event_id = 'evt_1'"
            ).fetchone()[0]
            payload = json.loads(str(payload_json))
            payload["tool_name"] = "fs.changed"
            connection.execute(
                "UPDATE audit_events SET payload_json = ? WHERE event_id = 'evt_1'",
                (json.dumps(payload, sort_keys=True, separators=(",", ":")),),
            )
            connection.commit()
        export_response = client.get(
            "/audit-events/export",
            headers={"Authorization": "Bearer correct-token"},
        )

    metadata = json.loads(export_response.text.splitlines()[0])["metadata"]
    assert metadata["verification"]["valid"] is False
    assert metadata["verification"]["failure"]["reason"] == "event hash mismatch"


def test_app_startup_fails_for_invalid_manifest(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    (settings.manifest_dir / "invalid.yaml").write_text("name: fs.read\n", encoding="utf-8")
    app = create_app(settings)

    with pytest.raises(RuntimeError):
        with TestClient(app):
            pass


def test_app_startup_fails_for_invalid_policy(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    settings.policy_path.write_text("version: test\n", encoding="utf-8")
    app = create_app(settings)

    with pytest.raises(RuntimeError):
        with TestClient(app):
            pass


def test_database_initialization_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "ithildin.sqlite3"

    initialize_database(db_path)
    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            "SELECT key, value FROM app_metadata WHERE key = 'schema_version'"
        ).fetchall()

    assert rows == [("schema_version", "1")]


def _row_count(db_path: Path, table_name: str) -> int:
    with sqlite3.connect(db_path) as connection:
        return int(connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def write_opa_bundle(tmp_path: Path) -> Path:
    bundle_dir = tmp_path / "opa"
    bundle_dir.mkdir()
    source_path = bundle_dir / "ithildin.rego"
    source_path.write_text("package ithildin\n", encoding="utf-8")
    source_hash = "sha256:" + hashlib.sha256(source_path.read_bytes()).hexdigest()
    bundle_hash = opa_bundle_hash(
        bundle_version="opa-test-v1",
        entrypoint="ithildin/decision",
        sources=(OpaBundleSource(path="ithildin.rego", source_hash=source_hash),),
    )
    manifest_path = bundle_dir / "bundle.lock.json"
    manifest_path.write_text(
        json.dumps(
            {
                "bundle_manifest_version": 1,
                "bundle_version": "opa-test-v1",
                "entrypoint": "ithildin/decision",
                "bundle_hash": bundle_hash,
                "sources": [{"path": "ithildin.rego", "source_hash": source_hash}],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return manifest_path

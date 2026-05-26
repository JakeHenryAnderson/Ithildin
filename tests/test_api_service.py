from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient
from ithildin_api.app import create_app
from ithildin_api.config import Settings
from ithildin_api.database import initialize_database
from ithildin_api.patches import PatchProposalService
from ithildin_audit_core import AuditWriter
from ithildin_schemas import AuditEventType
from pydantic import ValidationError


def make_settings(tmp_path: Path, token: str = "test-admin-token") -> Settings:
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
    return Settings(
        admin_token=token,
        audit_log_path=tmp_path / "audit.jsonl",
        db_path=tmp_path / "ithildin.sqlite3",
        manifest_dir=manifest_dir,
        policy_path=policy_path,
        workspace_root=tmp_path / "workspace",
    )


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
    assert get_response.status_code == 200
    assert get_response.json()["proposal_hash"] == proposal.proposal_hash
    assert get_response.json()["unified_diff"].startswith("--- a/README.md")
    assert missing_response.status_code == 404


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

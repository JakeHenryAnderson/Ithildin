from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from ithildin_api.agent_runs import AgentRunStore
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
from ithildin_api.node_configuration import (
    NodeConfigurationConflictError,
    NodeConfigurationStore,
    generate_node_configuration_signing_keypair,
)
from ithildin_api.nodes import NodeHeartbeatPayload, canonical_signature_message
from ithildin_api.patches import PatchApplyAttempt, PatchProposalService
from ithildin_api.registry import ToolRegistry
from ithildin_audit_core import AuditWriter, generate_audit_signing_keypair
from ithildin_policy_core import OpaBundleSource, opa_bundle_hash
from ithildin_schemas import AuditEventType, JsonObject, sha256_digest
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
    manifest_lock_path = tmp_path / "tool-manifests.lock.json"
    if not manifest_lock_path.exists():
        manifest_lock_path.write_text(
            json.dumps(
                {
                    "lockfile_version": 1,
                    "manifest_dir": "tool-manifests",
                    "manifests": [],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    node_configuration_private_key = tmp_path / "keys" / "node-config-private.pem"
    node_configuration_public_key = tmp_path / "keys" / "node-config-public.pem"
    if not node_configuration_private_key.exists():
        generate_node_configuration_signing_keypair(
            node_configuration_private_key,
            node_configuration_public_key,
        )
    return Settings(
        admin_token=token,
        audit_log_path=tmp_path / "audit.jsonl",
        audit_signing_private_key_path=tmp_path / "keys" / "audit-private.pem",
        audit_signing_public_key_path=tmp_path / "keys" / "audit-public.pem",
        db_path=tmp_path / "ithildin.sqlite3",
        manifest_dir=manifest_dir,
        require_manifest_lock=False,
        manifest_lock_path=manifest_lock_path,
        manifest_lock_signing_private_key_path=tmp_path / "keys" / "manifest-private.pem",
        manifest_lock_signing_public_key_path=tmp_path / "keys" / "manifest-public.pem",
        manifest_lock_signature_path=tmp_path / "signatures" / "tool-manifests.lock.sig.json",
        node_configuration_signing_private_key_path=node_configuration_private_key,
        node_configuration_signing_public_key_path=node_configuration_public_key,
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


def sandbox_descriptor_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "workspace_id": "default",
        "principal_id": "agent:local-dev",
        "run_id": "run_11111111111111111111111111111111",
        "sandbox_id": "sandbox-demo",
        "sandbox_profile_id": "profile-demo",
        "vm_profile_hash": "sha256:" + ("1" * 64),
        "isolation_label": "operator-attested-vm",
        "network_posture_label": "host-only",
        "mount_root_label": "sandbox-workspace",
        "model_client_label": "local-llm",
        "descriptor_source": "operator_supplied",
        "vm_lifecycle_source": "operator_managed",
        "isolation_claim_source": "operator_attested",
        "network_posture_source": "operator_attested",
        "mount_posture_source": "operator_attested",
        "model_client_source": "operator_attested",
        "ithildin_live_inspection_performed": False,
        "ithildin_lifecycle_control_performed": False,
        "mission_control_runtime_authority_used": False,
        "trusted_host_promotion_performed": False,
        "approval_id": "ap_11111111111111111111111111111111",
        "audit_event_id": "evt_11111111111111111111111111111111",
        "signed_export_id": "sig_11111111111111111111111111111111",
        "failure_transcript_hash": "sha256:" + ("2" * 64),
        "packet_hash": "sha256:" + ("3" * 64),
        "operator_notes_label": "demo-notes",
    }
    payload.update(overrides)
    return payload


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
    assert payload["agent_runs"] == {
        "enabled": True,
        "count": 0,
        "status": "read_only_observability",
    }
    assert payload["sandbox_descriptors"] == {
        "enabled": True,
        "mode": "operator_attested_descriptor_only",
        "count": 0,
        "statuses": {},
        "runtime_controls": {
            "live_vm_inspection": False,
            "vm_container_lifecycle": False,
            "sandbox_orchestration": False,
            "mission_control_runtime_authority": False,
            "trusted_host_promotion": False,
            "host_writes": False,
            "network_expansion": False,
        },
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


def test_sandbox_descriptor_endpoints_require_auth_and_store_safe_evidence(
    tmp_path: Path,
) -> None:
    app = create_app(make_settings(tmp_path, token="correct-token"))

    with TestClient(app) as client:
        unauthenticated = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(),
        )
        created = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(),
            headers={"Authorization": "Bearer correct-token"},
        )
        descriptor_id = created.json()["descriptor_id"]
        listed = client.get(
            "/sandbox-descriptors",
            headers={"Authorization": "Bearer correct-token"},
        )
        detail = client.get(
            f"/sandbox-descriptors/{descriptor_id}",
            headers={"Authorization": "Bearer correct-token"},
        )
        status_response = client.get(
            "/system/status",
            headers={"Authorization": "Bearer correct-token"},
        )
        audit_response = client.get(
            "/audit-events?event_type=sandbox.descriptor.submitted",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert unauthenticated.status_code == 401
    assert created.status_code == 200
    created_payload = created.json()
    assert descriptor_id.startswith("sdesc_")
    assert created_payload["status"] == "accepted"
    assert created_payload["payload_hash"].startswith("sha256:")
    assert created_payload["descriptor_source"] == "operator_supplied"
    assert created_payload["vm_lifecycle_source"] == "operator_managed"
    assert created_payload["ithildin_live_inspection_performed"] is False
    assert created_payload["ithildin_lifecycle_control_performed"] is False
    assert created_payload["mission_control_runtime_authority_used"] is False
    assert created_payload["trusted_host_promotion_performed"] is False
    assert created_payload["correlation"] == {
        "approval_id": "ap_11111111111111111111111111111111",
        "audit_event_id": "evt_11111111111111111111111111111111",
        "signed_export_id": "sig_11111111111111111111111111111111",
    }
    assert created_payload["output_policy"]["operator_attested"] is True
    assert created_payload["output_policy"]["no_live_vm_inspection"] is True
    assert "raw_paths" in created_payload["output_policy"]["excluded_categories"]
    assert "safe_payload" in created_payload
    assert created_payload["safe_payload"]["mount_root_label"] == "sandbox-workspace"
    assert "secret.txt" not in created.text
    assert "command line" not in created.text
    assert "/Users/" not in created.text

    assert listed.status_code == 200
    listed_payload = listed.json()
    assert [item["descriptor_id"] for item in listed_payload["sandbox_descriptors"]] == [
        descriptor_id
    ]
    assert listed_payload["summary"]["count"] == 1
    assert listed_payload["summary"]["runtime_controls"] == {
        "live_vm_inspection": False,
        "vm_container_lifecycle": False,
        "sandbox_orchestration": False,
        "mission_control_runtime_authority": False,
        "trusted_host_promotion": False,
        "host_writes": False,
        "network_expansion": False,
    }
    assert detail.status_code == 200
    assert detail.json()["descriptor_id"] == descriptor_id
    assert status_response.status_code == 200
    assert status_response.json()["sandbox_descriptors"]["count"] == 1

    assert audit_response.status_code == 200
    audit_events = audit_response.json()["audit_events"]
    assert len(audit_events) == 1
    audit_metadata = audit_events[0]["metadata"]
    assert audit_metadata["descriptor_id"] == descriptor_id
    assert audit_metadata["descriptor_payload_hash"] == created_payload["payload_hash"]
    assert audit_metadata["descriptor_source"] == "operator_supplied"
    assert audit_metadata["ithildin_live_inspection_performed"] is False
    assert audit_metadata["trusted_host_promotion_performed"] is False
    assert "mount_root_label" not in audit_metadata
    assert "raw_paths" in audit_metadata["output_policy"]["excluded_categories"]


def test_sandbox_descriptor_denies_unsafe_inputs_safely(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path, token="correct-token"))

    with TestClient(app) as client:
        unknown_field = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(secret="/Users/jake/secret.txt"),
            headers={"Authorization": "Bearer correct-token"},
        )
        lifecycle_claim = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(ithildin_lifecycle_control_performed=True),
            headers={"Authorization": "Bearer correct-token"},
        )
        raw_path = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(mount_root_label="/Users/jake/workspace"),
            headers={"Authorization": "Bearer correct-token"},
        )
        bad_hash = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(vm_profile_hash="not-a-hash"),
            headers={"Authorization": "Bearer correct-token"},
        )
        bad_query = client.get(
            "/sandbox-descriptors?format=json",
            headers={"Authorization": "Bearer correct-token"},
        )
        bad_id = client.get(
            "/sandbox-descriptors/not-a-descriptor",
            headers={"Authorization": "Bearer correct-token"},
        )

    for response in [unknown_field, lifecycle_claim, raw_path, bad_hash]:
        assert response.status_code == 400
        assert response.json()["detail"] == "invalid sandbox descriptor"
        assert "/Users/jake" not in response.text
        assert "secret" not in response.text
        assert "not-a-hash" not in response.text
    assert bad_query.status_code == 400
    assert bad_query.json()["detail"] == "unsupported query parameter"
    assert bad_id.status_code == 400
    assert bad_id.json()["detail"] == "invalid sandbox descriptor id"


def test_trusted_host_promotion_stages_single_artifact_after_approval(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    settings.workspace_root.joinpath("summary.txt").write_text("Hello World\n", encoding="utf-8")
    app = create_app(settings)

    with TestClient(app) as client:
        descriptor = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(sandbox_id="sandbox-demo"),
            headers={"Authorization": "Bearer correct-token"},
        ).json()
        unauthenticated = client.post(
            "/trusted-host-promotions/proposals",
            json={
                "workspace_id": "default",
                "sandbox_descriptor_id": descriptor["descriptor_id"],
                "sandbox_id": "sandbox-demo",
                "source_artifact_path": "summary.txt",
                "host_staging_label": "host-staging://summary-output",
            },
        )
        proposal_response = client.post(
            "/trusted-host-promotions/proposals",
            json={
                "workspace_id": "default",
                "sandbox_descriptor_id": descriptor["descriptor_id"],
                "sandbox_id": "sandbox-demo",
                "source_artifact_path": "summary.txt",
                "host_staging_label": "host-staging://summary-output",
                "principal": {"id": "agent:local-dev", "roles": ["AgentDeveloper"]},
            },
            headers={"Authorization": "Bearer correct-token"},
        )
        proposal_payload = proposal_response.json()
        approval_id = proposal_payload["approval_id"]
        approve_response = client.post(
            f"/approvals/{approval_id}/approve",
            json={"decision": "approve", "decided_by": "admin:local"},
            headers={"Authorization": "Bearer correct-token"},
        )
        apply_response = client.post(
            f"/trusted-host-promotions/proposals/{proposal_payload['promotion_proposal_id']}/apply",
            json={"approval_id": approval_id},
            headers={"Authorization": "Bearer correct-token"},
        )
        replay_response = client.post(
            f"/trusted-host-promotions/proposals/{proposal_payload['promotion_proposal_id']}/apply",
            json={"approval_id": approval_id},
            headers={"Authorization": "Bearer correct-token"},
        )
        diagnostics_response = client.get(
            "/trusted-host-promotions/diagnostics",
            headers={"Authorization": "Bearer correct-token"},
        )
        list_response = client.get(
            "/trusted-host-promotions/proposals",
            headers={"Authorization": "Bearer correct-token"},
        )
        status_response = client.get(
            "/system/status",
            headers={"Authorization": "Bearer correct-token"},
        )
        audit_response = client.get(
            "/audit-events?tool_name=trusted_host.promotion.stage",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert unauthenticated.status_code == 401
    assert proposal_response.status_code == 200
    assert proposal_payload["promotion_proposal_id"].startswith("thp_")
    assert proposal_payload["status"] == "approval_required"
    assert proposal_payload["source_artifact_label"] == "sandbox://sandbox-demo/summary.txt"
    assert proposal_payload["host_staging_label"] == "host-staging://summary-output"
    assert proposal_payload["artifact_sha256"].startswith("sha256:")
    assert proposal_payload["artifact_size_bytes"] == len(b"Hello World\n")
    assert proposal_payload["output_policy"]["file_contents_included"] is False
    assert "Hello World" not in proposal_response.text
    assert settings.workspace_root.as_posix() not in proposal_response.text

    assert approve_response.status_code == 200
    assert apply_response.status_code == 200
    applied = apply_response.json()
    assert applied["status"] == "completed"
    assert applied["staged_sha256"] == proposal_payload["artifact_sha256"]
    assert applied["host_staging_label"] == "host-staging://summary-output"
    assert applied["output_policy"]["raw_host_paths_included"] is False
    assert "Hello World" not in apply_response.text
    assert settings.trusted_host_staging_root.as_posix() not in apply_response.text

    staged_files = list(settings.trusted_host_staging_root.rglob("*.artifact"))
    assert len(staged_files) == 1
    assert staged_files[0].read_text(encoding="utf-8") == "Hello World\n"

    assert replay_response.status_code == 409
    assert "approval is not approved" in replay_response.json()["detail"]
    assert diagnostics_response.status_code == 200
    assert diagnostics_response.json()["status"] == "clean"
    assert list_response.status_code == 200
    assert list_response.json()["promotion_proposals"][0]["status"] == "completed"
    assert status_response.status_code == 200
    assert status_response.json()["trusted_host_promotions"] == "clean"
    assert audit_response.status_code == 200
    audit_payload = audit_response.text
    assert "Hello World" not in audit_payload
    assert settings.trusted_host_staging_root.as_posix() not in audit_payload
    audit_events = audit_response.json()["audit_events"]
    event_types = {event["event_type"] for event in audit_events}
    assert "approval.created" in event_types
    assert "approval.approved" in event_types
    assert "tool.execution.started" in event_types
    assert "tool.execution.completed" in event_types
    completed_metadata = [
        event["metadata"]
        for event in audit_events
        if event["event_type"] == "tool.execution.completed"
    ][0]
    assert completed_metadata["staging_only"] is True
    assert completed_metadata["artifact_sha256"] == proposal_payload["artifact_sha256"]
    assert completed_metadata["staged_sha256"] == proposal_payload["artifact_sha256"]
    assert completed_metadata["output_policy"]["file_contents_included"] is False


def test_trusted_host_promotion_denies_stale_and_unsafe_inputs(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    artifact = settings.workspace_root / "summary.txt"
    artifact.write_text("original\n", encoding="utf-8")
    app = create_app(settings)

    with TestClient(app) as client:
        descriptor = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(sandbox_id="sandbox-demo"),
            headers={"Authorization": "Bearer correct-token"},
        ).json()
        hidden = client.post(
            "/trusted-host-promotions/proposals",
            json={
                "workspace_id": "default",
                "sandbox_descriptor_id": descriptor["descriptor_id"],
                "sandbox_id": "sandbox-demo",
                "source_artifact_path": ".env",
                "host_staging_label": "host-staging://summary-output",
            },
            headers={"Authorization": "Bearer correct-token"},
        )
        raw_path_label = client.post(
            "/trusted-host-promotions/proposals",
            json={
                "workspace_id": "default",
                "sandbox_descriptor_id": descriptor["descriptor_id"],
                "sandbox_id": "sandbox-demo",
                "source_artifact_path": "summary.txt",
                "host_staging_label": "host-staging://bad/path",
            },
            headers={"Authorization": "Bearer correct-token"},
        )
        proposal = client.post(
            "/trusted-host-promotions/proposals",
            json={
                "workspace_id": "default",
                "sandbox_descriptor_id": descriptor["descriptor_id"],
                "sandbox_id": "sandbox-demo",
                "source_artifact_path": "summary.txt",
                "host_staging_label": "host-staging://summary-output",
            },
            headers={"Authorization": "Bearer correct-token"},
        ).json()
        approval_id = proposal["approval_id"]
        approve = client.post(
            f"/approvals/{approval_id}/approve",
            json={"decision": "approve", "decided_by": "admin:local"},
            headers={"Authorization": "Bearer correct-token"},
        )
        unsupported_apply_field = client.post(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
            json={"approval_id": approval_id, "extra": True},
            headers={"Authorization": "Bearer correct-token"},
        )
        artifact.write_text("changed\n", encoding="utf-8")
        stale_apply = client.post(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
            json={"approval_id": approval_id},
            headers={"Authorization": "Bearer correct-token"},
        )
        diagnostics = client.get(
            "/trusted-host-promotions/diagnostics",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert hidden.status_code == 400
    assert hidden.json()["detail"] == "invalid trusted-host promotion proposal"
    assert raw_path_label.status_code == 400
    assert raw_path_label.json()["detail"] == "invalid trusted-host promotion proposal"
    assert approve.status_code == 200
    assert unsupported_apply_field.status_code == 400
    assert unsupported_apply_field.json()["detail"] == (
        "unsupported trusted-host promotion apply field"
    )
    assert stale_apply.status_code == 409
    assert stale_apply.json()["detail"] == "source artifact hash mismatch"
    assert "original" not in stale_apply.text
    assert "changed" not in stale_apply.text
    assert settings.trusted_host_staging_root.exists() is False
    assert diagnostics.status_code == 200
    assert diagnostics.json()["status"] == "clean"


def test_run_endpoints_require_auth_and_return_safe_timeline(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path, token="correct-token"))

    with TestClient(app) as client:
        run_store = cast(AgentRunStore, app.state.agent_run_store)
        audit_writer = cast(AuditWriter, app.state.audit_writer)
        run_context, created = run_store.ensure_for_tool_call(
            principal={"id": "agent:local-dev", "type": "agent", "roles": ["AgentDeveloper"]},
            session_id="sess_api_runs",
            workspace_id="default",
            request_id="req_test_runs",
            tool_name="fs.read",
            policy_hash="sha256:" + ("1" * 64),
            tool_manifest_hash="sha256:" + ("2" * 64),
        )
        assert created is True
        audit_writer.write_event(
            event_id="evt_test_runs",
            event_type=AuditEventType.POLICY_EVALUATED,
            request_id="req_test_runs",
            principal={"id": "agent:local-dev", "type": "agent", "roles": ["AgentDeveloper"]},
            tool_name="fs.read",
            metadata={**run_context.metadata(), "reason": "allowed"},
        )

        unauthenticated = client.get("/runs")
        list_response = client.get(
            "/runs",
            headers={"Authorization": "Bearer correct-token"},
        )
        detail_response = client.get(
            f"/runs/{run_context.run_id}",
            headers={"Authorization": "Bearer correct-token"},
        )
        missing_response = client.get(
            "/runs/run_missing",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert unauthenticated.status_code == 401
    assert list_response.status_code == 200
    runs = list_response.json()["runs"]
    summary = list_response.json()["summary"]
    assert len(runs) == 1
    assert runs[0]["run_id"] == run_context.run_id
    assert runs[0]["principal_id"] == "agent:local-dev"
    assert summary["returned"] == 1
    assert summary["filters"] == {}
    assert summary["principals"] == {"agent:local-dev": 1}
    assert summary["workspaces"] == {"default": 1}
    assert summary["statuses"] == {"active": 1}
    assert summary["tools"] == {"fs.read": 1}
    assert summary["latest_updated_at"] == runs[0]["updated_at"]
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["run"]["session_id"] == "sess_api_runs"
    assert detail["timeline"] == [
        {
            "event_id": "evt_test_runs",
            "timestamp": detail["timeline"][0]["timestamp"],
            "event_type": "policy.evaluated",
            "request_id": "req_test_runs",
            "tool_name": "fs.read",
            "decision": None,
            "event_hash": detail["timeline"][0]["event_hash"],
            "resource": None,
            "metadata": {
                "run_id": run_context.run_id,
                "session_id": "sess_api_runs",
                "workspace_id": "default",
                "principal_id": "agent:local-dev",
                "reason": "allowed",
            },
        }
    ]
    assert missing_response.status_code == 404


def test_run_list_filters_and_denies_bad_queries_safely(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path, token="correct-token"))

    with TestClient(app) as client:
        run_store = cast(AgentRunStore, app.state.agent_run_store)
        first, _created = run_store.ensure_for_tool_call(
            principal={"id": "agent:local-dev", "type": "agent", "roles": ["AgentDeveloper"]},
            session_id="sess_filter_one",
            workspace_id="default",
            request_id="req_filter_one",
            tool_name="fs.read",
            policy_hash="sha256:" + ("1" * 64),
            tool_manifest_hash="sha256:" + ("2" * 64),
        )
        second, _created = run_store.ensure_for_tool_call(
            principal={"id": "agent:readonly", "type": "agent", "roles": ["AgentReadOnly"]},
            session_id="sess_filter_two",
            workspace_id="network",
            request_id="req_filter_two",
            tool_name="http.fetch",
            policy_hash="sha256:" + ("3" * 64),
            tool_manifest_hash="sha256:" + ("4" * 64),
        )

        filtered = client.get(
            "/runs?principal_id=agent%3Alocal-dev&workspace_id=default&tool_name=fs.read",
            headers={"Authorization": "Bearer correct-token"},
        )
        limited = client.get(
            "/runs?limit=1",
            headers={"Authorization": "Bearer correct-token"},
        )
        unknown_query = client.get(
            "/runs?format=json",
            headers={"Authorization": "Bearer correct-token"},
        )
        bad_limit = client.get(
            "/runs?limit=201",
            headers={"Authorization": "Bearer correct-token"},
        )
        bad_filter = client.get(
            "/runs?workspace_id=" + ("a" * 129),
            headers={"Authorization": "Bearer correct-token"},
        )

    assert filtered.status_code == 200
    filtered_payload = filtered.json()
    assert [run["run_id"] for run in filtered_payload["runs"]] == [first.run_id]
    assert filtered_payload["summary"]["returned"] == 1
    assert filtered_payload["summary"]["filters"] == {
        "principal_id": "agent:local-dev",
        "workspace_id": "default",
        "tool_name": "fs.read",
    }
    assert filtered_payload["summary"]["tools"] == {"fs.read": 1}
    assert limited.status_code == 200
    assert len(limited.json()["runs"]) == 1
    assert limited.json()["runs"][0]["run_id"] in {first.run_id, second.run_id}
    assert limited.json()["summary"]["returned"] == 1
    assert unknown_query.status_code == 400
    assert unknown_query.json()["detail"] == "unsupported query parameter"
    assert bad_limit.status_code == 400
    assert bad_limit.json()["detail"] == "invalid limit"
    assert bad_filter.status_code == 400
    assert bad_filter.json()["detail"] == "invalid filter value"


def test_run_evidence_export_requires_auth_and_returns_secret_free_bundle(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path, token="correct-token"))

    with TestClient(app) as client:
        run_store = cast(AgentRunStore, app.state.agent_run_store)
        audit_writer = cast(AuditWriter, app.state.audit_writer)
        approval_service = cast(ApprovalService, app.state.approval_service)
        run_context, _created = run_store.ensure_for_tool_call(
            principal={"id": "agent:local-dev", "type": "agent", "roles": ["AgentDeveloper"]},
            session_id="sess_export_runs",
            workspace_id="default",
            request_id="req_export_runs",
            tool_name="fs.patch.apply",
            policy_hash="sha256:" + ("1" * 64),
            tool_manifest_hash="sha256:" + ("2" * 64),
        )
        approval = approval_service.create_pending(
            CreateApprovalInput(
                principal={"id": "agent:local-dev", "type": "agent", "roles": ["AgentDeveloper"]},
                tool_name="fs.patch.apply",
                resource={"type": "file", "workspace_id": "default", "path": "secret.txt"},
                summary="Apply patch containing secret text",
                one_time_scope={
                    "proposal_id": "patch_1",
                    "proposal_hash": "sha256:" + ("3" * 64),
                    "base_file_hash": "sha256:" + ("4" * 64),
                    "workspace_id": "default",
                    "path": "secret.txt",
                },
                request_id="req_export_runs",
                metadata={**run_context.metadata(), "proposal_hash": "sha256:" + ("3" * 64)},
            )
        )
        audit_writer.write_event(
            event_id="evt_export_runs",
            event_type=AuditEventType.TOOL_EXECUTION_COMPLETED,
            request_id="req_export_runs",
            principal={"id": "agent:local-dev", "type": "agent", "roles": ["AgentDeveloper"]},
            tool_name="fs.patch.apply",
            resource={"type": "file", "path": "secret.txt"},
            metadata={
                **run_context.metadata(),
                "approval_id": approval.approval_id,
                "proposal_id": "patch_1",
                "proposal_hash": "sha256:" + ("3" * 64),
                "path": "secret.txt",
                "diff": "--- a/secret.txt\n+++ b/secret.txt\n",
            },
        )

        unauthenticated = client.get(f"/runs/{run_context.run_id}/evidence-export")
        response = client.get(
            f"/runs/{run_context.run_id}/evidence-export",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert unauthenticated.status_code == 401
    assert response.status_code == 200
    body = response.text
    payload = response.json()
    assert payload["schema_version"] == "1"
    assert payload["export_id"].startswith("runev_")
    assert payload["run"]["run_id"] == run_context.run_id
    assert payload["run"]["manifest_lock_hash"] == "sha256:" + ("2" * 64)
    assert payload["summary"] == {
        "principal_id": "agent:local-dev",
        "workspace_id": "default",
        "session_id": "sess_export_runs",
        "status": "active",
        "tool_call_count": 1,
        "tools_used": ["fs.patch.apply"],
        "decision_counts": {},
        "approval_count": 1,
        "patch_diagnostic_count": 0,
        "audit_event_count": 2,
        "warning_count": 2,
        "latest_policy_hash": "sha256:" + ("1" * 64),
        "manifest_lock_hash": "sha256:" + ("2" * 64),
    }
    completed_events = [
        event for event in payload["timeline"] if event["category"] == "tool.execution.completed"
    ]
    assert completed_events[0]["approval_id"] == approval.approval_id
    assert "resource" not in completed_events[0]
    assert payload["approvals"][0]["approval_id"] == approval.approval_id
    assert payload["approvals"][0]["one_time_scope"]["path_hash"].startswith("sha256:")
    assert "path" not in payload["approvals"][0]["one_time_scope"]
    assert payload["signed_export_references"] == []
    assert payload["evidence_hashes"]["run_sha256"].startswith("sha256:")
    assert payload["redaction_summary"]["excluded_categories"]
    assert any(warning["type"] == "signed_evidence_unavailable" for warning in payload["warnings"])
    assert "secret.txt" not in body
    assert "--- a/secret.txt" not in body
    assert "Apply patch containing secret text" not in body


def test_run_evidence_export_denies_bad_inputs_safely(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path, token="correct-token"))

    with TestClient(app) as client:
        malformed = client.get(
            "/runs/not-a-run/evidence-export",
            headers={"Authorization": "Bearer correct-token"},
        )
        unknown = client.get(
            "/runs/run_11111111111111111111111111111111/evidence-export",
            headers={"Authorization": "Bearer correct-token"},
        )
        unknown_query = client.get(
            "/runs/run_11111111111111111111111111111111/evidence-export?format=json",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert malformed.status_code == 400
    assert malformed.json()["detail"] == "invalid run id"
    assert unknown.status_code == 404
    assert unknown_query.status_code == 400
    assert unknown_query.json()["detail"] == "unsupported query parameter"


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
                "tool_name": "fs.apply_patch",
                "resource": {"path": "README.md"},
                "summary": "Apply README patch",
                "one_time_scope": {"tool_name": "fs.apply_patch"},
            },
        )
        second_response = client.post(
            "/approvals",
            headers={"Authorization": "Bearer correct-token"},
            json={
                "principal": {"id": "agent:local-dev"},
                "tool_name": "fs.apply_patch",
                "resource": {"path": "other.md"},
                "summary": "Apply other patch",
                "one_time_scope": {"tool_name": "fs.apply_patch"},
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


def test_patch_apply_approval_requires_valid_binding_scope_before_approval(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    write_manifest(
        settings.manifest_dir,
        name="fs.patch.apply",
        risk="write",
        required=["proposal_id"],
    )
    app = create_app(settings)

    with TestClient(app) as client:
        create_response = client.post(
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
        approve_response = client.post(
            f"/approvals/{create_response.json()['approval_id']}/approve",
            headers={"Authorization": "Bearer correct-token"},
            json={"decision": "approve", "decided_by": "user:alice"},
        )

    assert create_response.status_code == 200
    assert approve_response.status_code == 409
    assert approve_response.json()["detail"] == "patch apply approval binding review failed"


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


def test_node_api_enrolls_authenticates_rejects_replay_and_revokes(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    admin_headers = {"Authorization": "Bearer test-admin-token"}
    private_key = Ed25519PrivateKey.generate()
    public_key = base64.b64encode(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    ).decode()
    with TestClient(create_app(settings)) as client:
        issued_response = client.post(
            "/nodes/enrollment-codes",
            headers=admin_headers,
            json={"workspace_id": "default", "display_name": "Hermes Node"},
        )
        assert issued_response.status_code == 200
        enrollment_code = issued_response.json()["enrollment_code"]
        enrollment = client.post(
            "/nodes/enroll",
            json={
                "enrollment_code": enrollment_code,
                "public_key": public_key,
                "protocol_version": "1",
                "node_version": "0.1.0",
                "runner_adapter": "hermes",
                "deployment_topology": "docker_sidecar",
            },
        )
        assert enrollment.status_code == 200
        assert enrollment.json()["evidence_status"] == "complete"
        node_id = enrollment.json()["node_id"]
        assert enrollment.json()["principal_id"] == f"agent:node.{node_id}"
        heartbeat = NodeHeartbeatPayload(
            protocol_version="1",
            node_version="0.1.0",
            runner_adapter="hermes",
            deployment_topology="docker_sidecar",
            configuration_digest="sha256:" + ("2" * 64),
            mission_id="mission-synthetic-001",
        )
        timestamp = str(int(datetime.now(UTC).timestamp()))
        nonce = "e" * 32
        message = canonical_signature_message(
            method="POST",
            path=f"/nodes/{node_id}/heartbeat",
            timestamp=timestamp,
            nonce=nonce,
            body_hash=sha256_digest(heartbeat.safe_payload()),
        )
        node_headers = {
            "X-Ithildin-Node": node_id,
            "X-Ithildin-Timestamp": timestamp,
            "X-Ithildin-Nonce": nonce,
            "X-Ithildin-Signature": base64.b64encode(private_key.sign(message)).decode(),
        }
        accepted = client.post(
            f"/nodes/{node_id}/heartbeat",
            headers=node_headers,
            json=heartbeat.model_dump(mode="json", exclude_none=True),
        )
        assert accepted.status_code == 200
        assert accepted.json()["evidence_status"] == "complete"
        assert accepted.json()["observed_state"] == "observed_connected"
        replay = client.post(
            f"/nodes/{node_id}/heartbeat",
            headers=node_headers,
            json=heartbeat.model_dump(mode="json", exclude_none=True),
        )
        assert replay.status_code == 401
        assert replay.json()["detail"] == "replayed Node nonce"
        inventory = client.get("/nodes", headers=admin_headers)
        assert inventory.status_code == 200
        assert inventory.json()["nodes"][0]["node_id"] == node_id
        assert inventory.json()["runner_health_known"] is False
        revoked = client.post(f"/nodes/{node_id}/revoke", headers=admin_headers)
        assert revoked.status_code == 200
        assert revoked.json()["status"] == "revoked"
        assert revoked.json()["evidence_status"] == "complete"
        post_revoke_headers = {**node_headers, "X-Ithildin-Nonce": "f" * 32}
        post_revoke = client.post(
            f"/nodes/{node_id}/heartbeat",
            headers=post_revoke_headers,
            json=heartbeat.model_dump(mode="json", exclude_none=True),
        )
        assert post_revoke.status_code == 401

    audit_text = settings.audit_log_path.read_text(encoding="utf-8")
    assert enrollment_code not in audit_text
    assert "node.enrollment_code.issued" in audit_text
    assert "node.enrolled" in audit_text
    assert "node.heartbeat.accepted" in audit_text
    assert "node.revoked" in audit_text


def test_node_signed_configuration_distribution_acknowledgment_and_drift_api(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    private_key = Ed25519PrivateKey.generate()
    public_key = base64.b64encode(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    ).decode()
    api = create_app(settings)
    with TestClient(api) as client:
        issued = client.post(
            "/nodes/enrollment-codes",
            headers=admin_headers,
            json={"workspace_id": "default", "display_name": "Configuration Node"},
        )
        enrollment = client.post(
            "/nodes/enroll",
            json={
                "enrollment_code": issued.json()["enrollment_code"],
                "public_key": public_key,
                "protocol_version": "1",
                "node_version": "0.1.0",
                "runner_adapter": "hermes",
                "deployment_topology": "docker_sidecar",
            },
        )
        assert enrollment.status_code == 200
        node_id = enrollment.json()["node_id"]
        assert enrollment.json()["configuration_trust"]["key_id"].startswith("sha256:")

        assigned = client.post(
            f"/nodes/{node_id}/configurations",
            headers=admin_headers,
            json={
                "minimum_node_version": "0.1.0",
                "heartbeat_interval_seconds": 30,
                "offline_posture": "deny_governed_actions",
                "evidence_buffer_max_events": 1000,
                "validity_seconds": 3600,
            },
        )
        assert assigned.status_code == 200
        assert assigned.json()["generation"] == 1
        request_payload: JsonObject = {"protocol_version": "1", "known_generation": 0}
        request_path = f"/nodes/{node_id}/configuration"
        request_headers = _signed_node_headers(
            private_key,
            node_id=node_id,
            path=request_path,
            payload=request_payload,
            nonce="7" * 32,
        )
        retrieved = client.post(request_path, headers=request_headers, json=request_payload)
        assert retrieved.status_code == 200
        assert retrieved.json()["node_id"] == node_id
        assert retrieved.json()["configuration"]["enforcement_status"] == "stored_not_enforced"
        replay = client.post(request_path, headers=request_headers, json=request_payload)
        assert replay.status_code == 401
        assert replay.json()["detail"] == "replayed Node nonce"

        acknowledgment_payload = {
            "protocol_version": "1",
            "generation": 1,
            "configuration_digest": retrieved.json()["configuration_digest"],
            "configuration_signing_key_id": retrieved.json()["signature"]["key_id"],
            "active_configuration_signing_key_id": retrieved.json()["signature"]["key_id"],
            "status": "stored_not_enforced",
        }
        acknowledgment_path = f"/nodes/{node_id}/configuration/acknowledgments"
        acknowledged = client.post(
            acknowledgment_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=acknowledgment_path,
                payload=acknowledgment_payload,
                nonce="8" * 32,
            ),
            json=acknowledgment_payload,
        )
        assert acknowledged.status_code == 200
        assert acknowledged.json()["configuration_state"] == "stored_current_not_enforced"
        assert acknowledged.json()["configuration_acknowledgment_status"] == "stored_not_enforced"

        second = client.post(
            f"/nodes/{node_id}/configurations",
            headers=admin_headers,
            json={"minimum_node_version": "0.2.0"},
        )
        assert second.status_code == 200
        assert second.json()["generation"] == 2
        inventory = client.get(f"/nodes/{node_id}", headers=admin_headers)
        assert inventory.json()["configuration_state"] == "configuration_drift"

        history = client.get(f"/nodes/{node_id}/configurations", headers=admin_headers)
        assert history.status_code == 200
        assert [item["generation"] for item in history.json()["configurations"]] == [2, 1]
        assert history.json()["configurations"][0]["is_desired"] is True
        assert history.json()["rollback_semantics"] == "fresh_signed_generation"
        rollback = client.post(
            f"/nodes/{node_id}/configurations/rollback",
            headers=admin_headers,
            json={"source_generation": 1, "expected_current_generation": 2},
        )
        assert rollback.status_code == 200
        assert rollback.json()["generation"] == 3
        assert rollback.json()["assignment_kind"] == "manual_rollback"
        assert rollback.json()["rollback_source_generation"] == 1
        concurrent_rollback = client.post(
            f"/nodes/{node_id}/configurations/rollback",
            headers=admin_headers,
            json={"source_generation": 1, "expected_current_generation": 2},
        )
        assert concurrent_rollback.status_code == 409
        assert concurrent_rollback.json()["detail"] == "desired configuration changed"

        stale_ack = client.post(
            acknowledgment_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=acknowledgment_path,
                payload=acknowledgment_payload,
                nonce="9" * 32,
            ),
            json=acknowledgment_payload,
        )
        assert stale_ack.status_code == 409
        assert stale_ack.json()["detail"] == "configuration acknowledgment is not current"

        class FailingAuditWriter:
            def write_event(self, **_: object) -> None:
                raise RuntimeError("simulated rollback audit failure")

        api.state.audit_writer = FailingAuditWriter()
        with pytest.raises(RuntimeError, match="simulated rollback audit failure"):
            client.post(
                f"/nodes/{node_id}/configurations/rollback",
                headers=admin_headers,
                json={"source_generation": 2, "expected_current_generation": 3},
            )
        configuration_store = NodeConfigurationStore(settings.db_path)
        failed_history = configuration_store.list(node_id)
        assert failed_history[0].generation == 4
        assert failed_history[0].evidence_status == "pending"
        with pytest.raises(NodeConfigurationConflictError, match="evidence is incomplete"):
            configuration_store.desired(node_id)

    audit_text = settings.audit_log_path.read_text(encoding="utf-8")
    assert "node.configuration.assigned" in audit_text
    assert "node.configuration.retrieved" in audit_text
    assert "node.configuration.acknowledged" in audit_text
    assert "node.configuration.rollback_assigned" in audit_text
    assert "stored_not_enforced" in audit_text


def test_node_configuration_trust_transition_api_is_targeted_signed_and_audited(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    node_private_key = Ed25519PrivateKey.generate()
    node_public_key = base64.b64encode(
        node_private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    ).decode()
    next_private_path = tmp_path / "keys" / "next-node-config-private.pem"
    next_public_path = tmp_path / "keys" / "next-node-config-public.pem"
    next_trust = generate_node_configuration_signing_keypair(
        next_private_path, next_public_path
    )
    api = create_app(settings)
    with TestClient(api) as client:
        issued = client.post(
            "/nodes/enrollment-codes",
            headers=admin_headers,
            json={"workspace_id": "default", "display_name": "Trust Rotation Node"},
        )
        enrollment = client.post(
            "/nodes/enroll",
            json={
                "enrollment_code": issued.json()["enrollment_code"],
                "public_key": node_public_key,
                "protocol_version": "1",
                "node_version": "0.1.0",
                "runner_adapter": "hermes",
                "deployment_topology": "docker_sidecar",
            },
        )
        node_id = enrollment.json()["node_id"]
        current_key_id = enrollment.json()["configuration_trust"]["key_id"]
        path = f"/nodes/{node_id}/configuration-trust-transitions"
        assigned = client.post(
            path,
            headers=admin_headers,
            json={
                "expected_current_key_id": current_key_id,
                "next_public_key": next_trust.public_key,
                "validity_seconds": 3600,
            },
        )
        assert assigned.status_code == 200
        assert assigned.json()["current_key_id"] == current_key_id
        assert assigned.json()["next_key_id"] == next_trust.key_id
        assert assigned.json()["activation_proven"] is False

        request_payload: JsonObject = {"protocol_version": "1"}
        request_path = f"/nodes/{node_id}/configuration-trust-transition"
        retrieved = client.post(
            request_path,
            headers=_signed_node_headers(
                node_private_key,
                node_id=node_id,
                path=request_path,
                payload=request_payload,
                nonce="a" * 32,
            ),
            json=request_payload,
        )
        assert retrieved.status_code == 200
        assert retrieved.json()["node_id"] == node_id
        assert retrieved.json()["signature"]["key_id"] == current_key_id
        assert retrieved.json()["transition"]["next_trust"]["key_id"] == next_trust.key_id

        acknowledgment_payload: JsonObject = {
            "protocol_version": "1",
            "transition_id": retrieved.json()["transition_id"],
            "transition_digest": retrieved.json()["transition_digest"],
            "status": "staged_not_active",
        }
        acknowledgment_path = (
            f"/nodes/{node_id}/configuration-trust-transition/acknowledgments"
        )
        acknowledged = client.post(
            acknowledgment_path,
            headers=_signed_node_headers(
                node_private_key,
                node_id=node_id,
                path=acknowledgment_path,
                payload=acknowledgment_payload,
                nonce="b" * 32,
            ),
            json=acknowledgment_payload,
        )
        assert acknowledged.status_code == 200
        assert acknowledged.json()["acknowledgment_status"] == "staged_not_active"
        assert acknowledged.json()["acknowledgment_evidence_status"] == "complete"

        history = client.get(path, headers=admin_headers)
        assert history.status_code == 200
        assert history.json()["count"] == 1
        assert history.json()["automatic"] is False
        inventory = client.get(f"/nodes/{node_id}", headers=admin_headers)
        transition = inventory.json()["configuration_trust_transition"]
        assert transition["next_key_id"] == next_trust.key_id
        assert transition["rotation_state"] == "staged_not_active"
        assert transition["activation_proven"] is False

    audit_text = settings.audit_log_path.read_text(encoding="utf-8")
    assert "node.configuration_trust_transition.assigned" in audit_text
    assert "node.configuration_trust_transition.retrieved" in audit_text
    assert "node.configuration_trust_transition.acknowledged" in audit_text
    assert next_trust.public_key not in audit_text


def _row_count(db_path: Path, table_name: str) -> int:
    with sqlite3.connect(db_path) as connection:
        return int(connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def _signed_node_headers(
    private_key: Ed25519PrivateKey,
    *,
    node_id: str,
    path: str,
    payload: JsonObject,
    nonce: str,
) -> dict[str, str]:
    timestamp = str(int(datetime.now(UTC).timestamp()))
    message = canonical_signature_message(
        method="POST",
        path=path,
        timestamp=timestamp,
        nonce=nonce,
        body_hash=sha256_digest(payload),
    )
    return {
        "X-Ithildin-Node": node_id,
        "X-Ithildin-Timestamp": timestamp,
        "X-Ithildin-Nonce": nonce,
        "X-Ithildin-Signature": base64.b64encode(private_key.sign(message)).decode(),
    }


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

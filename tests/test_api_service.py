from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import sqlite3
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event
from typing import Any, NoReturn, cast

import ithildin_api.mission_reports as mission_reports_module
import ithildin_api.registry as registry_module
import ithildin_api.trusted_host_promotions as trusted_host_promotions_module
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from ithildin_api.agent_runs import AgentRunError, AgentRunStore
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
from ithildin_api.mission_admission import MissionAdmissionService
from ithildin_api.mission_claims import MissionClaimError, MissionClaimService
from ithildin_api.mission_reports import MissionReportError, MissionReportService
from ithildin_api.missions import (
    MissionCancellationPayload,
    MissionControlPollPayload,
    MissionError,
    MissionRunnerReportPayload,
    MissionStore,
)
from ithildin_api.node_configuration import (
    NodeConfigurationConflictError,
    NodeConfigurationStore,
    generate_node_configuration_signing_keypair,
)
from ithildin_api.nodes import (
    NodeHeartbeatPayload,
    NodeIdentityRotationActivationPayload,
    NodeIdentityRotationRecord,
    NodeStore,
    canonical_identity_rotation_proof_message,
    canonical_signature_message,
    node_identity_key_id,
)
from ithildin_api.patches import PatchApplyAttempt, PatchProposalService
from ithildin_api.promotion_authority import (
    AdminPrincipalContext,
    PolicyAuthorityRecord,
    PromotionAuthoritySnapshot,
    RuntimeCandidateRecord,
)
from ithildin_api.registry import ToolRegistry
from ithildin_api.sandbox_descriptors import SandboxDescriptorStore
from ithildin_api.trusted_host_placement import TrustedHostPlacement
from ithildin_api.trusted_host_promotions import (
    TrustedHostPromotionError,
    TrustedHostPromotionService,
    TrustedHostPromotionStore,
)
from ithildin_api.trusted_host_registry import TRUSTED_HOST_REGISTRY_SCHEMA_DIGEST
from ithildin_audit_core import AuditWriteError, AuditWriter, generate_audit_signing_keypair
from ithildin_policy_core import OpaBundleSource, opa_bundle_hash
from ithildin_schemas import AuditEventType, JsonObject, PolicyDecision, PolicyInput, sha256_digest
from pydantic import ValidationError
from runtime_candidate_bootstrap import RuntimeCandidateVerifier

ADMIN_CONTEXT = AdminPrincipalContext(
    principal_id="admin:local-ui",
    principal_type="admin",
    roles=("Admin",),
    authentication_method="local_admin_bearer",
    identity_source="principal_registry",
    identity_generation="sha256:" + ("d" * 64),
)


def runtime_candidate_fixture() -> RuntimeCandidateRecord:
    core: JsonObject = {
        "source_commit": "1" * 40,
        "inventory_schema_version": "1",
        "reviewed_inventory_digest": "sha256:" + ("a" * 64),
        "dependency_lock_digest": "sha256:" + ("b" * 64),
        "release_artifact_digest": "sha256:" + ("c" * 64),
        "evidence_schema_version": "1",
    }
    return RuntimeCandidateRecord(
        posture="reviewed",
        candidate_id=sha256_digest(core),
        source_commit="1" * 40,
        inventory_schema_version="1",
        reviewed_inventory_digest="sha256:" + ("a" * 64),
        dependency_lock_digest="sha256:" + ("b" * 64),
        release_artifact_digest="sha256:" + ("c" * 64),
        review_packet_digest="sha256:" + ("d" * 64),
        evidence_schema_version="1",
        authorization_id="rca_test_fixture",
    )


def promotion_ready_app(
    settings: Settings,
    *,
    placement_ready: bool = False,
    test_fixture_ready: bool = True,
    manifest_lock_required: bool = True,
    principal_registry_required: bool = True,
    principal_registry_path: Path | None = None,
    workspace_registry_required: bool = True,
    workspace_registry_path: Path | None = None,
    runtime_candidate: RuntimeCandidateRecord | None = None,
    runtime_candidate_verifier: Callable[[], RuntimeCandidateRecord] | None = None,
    configure_runtime_candidate_verifier: bool = True,
) -> Any:
    settings.manifest_dir = Path("tool-manifests").resolve()
    settings.manifest_lock_path = Path("tool-manifests.lock.json").resolve()
    settings.require_manifest_lock = manifest_lock_required
    settings.trusted_host_registry_path = Path("trusted-hosts/local.yaml").resolve()
    settings.principal_registry_path = (
        principal_registry_path
        if principal_registry_path is not None
        else Path("principals/local.yaml").resolve()
    )
    settings.require_known_principals = principal_registry_required
    if workspace_registry_path is not None:
        settings.workspace_registry_path = workspace_registry_path
    settings.require_known_workspaces = workspace_registry_required
    settings.policy_path.write_text(
        """
version: promotion-test-v1
rules:
  - id: require_approval_for_trusted_host_promotion_stage
    decision: require_approval
    reason: Trusted-host staging requires one-time approval.
    match:
      tool.name: trusted_host.promotion.stage
      resource.in_scope: true
      principal.roles_contains: [Admin]
    obligations:
      approval_mode: one_time
      approval_required: true
      audit_level: full
      placement_mode: create_exclusive
      zone: host_staging
""",
        encoding="utf-8",
    )
    candidate = runtime_candidate or runtime_candidate_fixture()
    verifier = runtime_candidate_verifier
    if verifier is None and configure_runtime_candidate_verifier:
        def verify_fixture_candidate() -> RuntimeCandidateRecord:
            return candidate

        verifier = verify_fixture_candidate
    return create_app(
        settings,
        runtime_candidate=candidate,
        runtime_candidate_verifier=verifier,
        trusted_host_promotion_test_fixture_ready=test_fixture_ready,
        trusted_host_promotion_placement_test_fixture_ready=(
            test_fixture_ready and placement_ready
        ),
    )


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
    workspace_id:
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


def create_approved_promotion(
    client: TestClient,
    *,
    token: str = "correct-token",
    sandbox_id: str = "sandbox-demo",
) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"}
    descriptor = client.post(
        "/sandbox-descriptors",
        json=sandbox_descriptor_payload(sandbox_id=sandbox_id),
        headers=headers,
    )
    assert descriptor.status_code == 200
    proposal = client.post(
        "/trusted-host-promotions/proposals",
        json={
            "workspace_id": "default",
            "sandbox_descriptor_id": descriptor.json()["descriptor_id"],
            "sandbox_id": sandbox_id,
            "source_artifact_path": "summary.txt",
            "host_staging_label": "host-staging://artifact",
        },
        headers=headers,
    )
    assert proposal.status_code == 200
    proposal_payload = cast(dict[str, Any], proposal.json())
    approval = client.post(
        f"/approvals/{proposal_payload['approval_id']}/approve",
        json={"decision": "approve"},
        headers=headers,
    )
    assert approval.status_code == 200
    return proposal_payload


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


@pytest.mark.parametrize(
    "principal_fields",
    [
        "roles: [Admin]\n    enabled: false",
        "roles: [Auditor]\n    enabled: true",
    ],
)
def test_admin_token_fails_closed_without_enabled_registry_admin(
    tmp_path: Path,
    principal_fields: str,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    registry = tmp_path / "principals.yaml"
    registry.write_text(
        "principals:\n"
        "  - id: admin:local-ui\n"
        "    type: admin\n"
        "    display_name: Local Admin\n"
        f"    {principal_fields}\n",
        encoding="utf-8",
    )
    settings.principal_registry_path = registry

    with TestClient(create_app(settings)) as client:
        response = client.get(
            "/admin/status",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "admin principal is not authorized"


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
    assert payload["trusted_host_registry"] == {
        "schema_version": "2",
        "registry_schema_digest": TRUSTED_HOST_REGISTRY_SCHEMA_DIGEST,
        "generation": payload["trusted_host_registry"]["generation"],
        "count": 1,
        "enabled_count": 1,
        "raw_paths_included": False,
    }
    assert payload["runtime_candidate"] == {
        "posture": "unreviewed_local",
        "promotion_allowed": False,
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
        descriptor_store = app.state.sandbox_descriptor_store
        promotion_service = cast(
            TrustedHostPromotionService,
            app.state.trusted_host_promotion_service,
        )
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
    assert type(descriptor_store) is SandboxDescriptorStore
    assert promotion_service.descriptor_store is descriptor_store
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
    assert audit_events[0]["event_type"] == "sandbox.descriptor.submitted"
    audit_metadata = audit_events[0]["metadata"]
    assert set(audit_metadata) == {
        "descriptor_id",
        "descriptor_status",
        "descriptor_payload_hash",
        "descriptor_source",
        "vm_lifecycle_source",
        "isolation_claim_source",
        "network_posture_source",
        "mount_posture_source",
        "model_client_source",
        "workspace_id",
        "principal_id",
        "run_id",
        "sandbox_id",
        "sandbox_profile_id",
        "ithildin_live_inspection_performed",
        "ithildin_lifecycle_control_performed",
        "mission_control_runtime_authority_used",
        "trusted_host_promotion_performed",
        "output_policy",
    }
    assert audit_metadata["descriptor_id"] == descriptor_id
    assert audit_metadata["descriptor_payload_hash"] == created_payload["payload_hash"]
    assert audit_metadata["descriptor_source"] == "operator_supplied"
    assert audit_metadata["ithildin_live_inspection_performed"] is False
    assert audit_metadata["trusted_host_promotion_performed"] is False
    assert "mount_root_label" not in audit_metadata
    assert "raw_paths" in audit_metadata["output_policy"]["excluded_categories"]


def test_sandbox_descriptor_remains_committed_after_audit_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app(make_settings(tmp_path, token="correct-token"))

    with TestClient(app, raise_server_exceptions=False) as client:
        audit_writer = cast(AuditWriter, app.state.audit_writer)
        original_write_event = audit_writer.write_event

        def fail_descriptor_event(**kwargs: Any) -> Any:
            if kwargs.get("event_type") == AuditEventType.SANDBOX_DESCRIPTOR_SUBMITTED:
                raise RuntimeError("simulated descriptor audit failure")
            return original_write_event(**kwargs)

        monkeypatch.setattr(audit_writer, "write_event", fail_descriptor_event)
        failed = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(sandbox_id="sandbox-audit-residual"),
            headers={"Authorization": "Bearer correct-token"},
        )
        listed = client.get(
            "/sandbox-descriptors",
            headers={"Authorization": "Bearer correct-token"},
        )

    assert failed.status_code == 500
    assert failed.text == "Internal Server Error"
    assert listed.status_code == 200
    descriptors = listed.json()["sandbox_descriptors"]
    assert len(descriptors) == 1
    assert descriptors[0]["sandbox_id"] == "sandbox-audit-residual"


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


def test_trusted_host_promotion_binds_identity_but_keeps_placement_unavailable(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    settings.workspace_root.joinpath("summary.txt").write_text("Hello World\n", encoding="utf-8")
    app = promotion_ready_app(settings)

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
                "host_staging_label": "host-staging://artifact",
            },
        )
        proposal_response = client.post(
            "/trusted-host-promotions/proposals",
            json={
                "workspace_id": "default",
                "sandbox_descriptor_id": descriptor["descriptor_id"],
                "sandbox_id": "sandbox-demo",
                "source_artifact_path": "summary.txt",
                "host_staging_label": "host-staging://artifact",
            },
            headers={"Authorization": "Bearer correct-token"},
        )
        proposal_payload = proposal_response.json()
        approval_id = proposal_payload["approval_id"]
        approval_response = client.get(
            f"/approvals/{approval_id}",
            headers={"Authorization": "Bearer correct-token"},
        )
        pending_detail = client.get(
            f"/trusted-host-promotions/proposals/{proposal_payload['promotion_proposal_id']}",
            headers={"Authorization": "Bearer correct-token"},
        )
        pending_approval_reviews = client.get(
            "/approvals/review?status=pending",
            headers={"Authorization": "Bearer correct-token"},
        )
        approve_response = client.post(
            f"/approvals/{approval_id}/approve",
            json={"decision": "approve"},
            headers={"Authorization": "Bearer correct-token"},
        )
        decided_detail = client.get(
            f"/trusted-host-promotions/proposals/{proposal_payload['promotion_proposal_id']}",
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
    assert proposal_payload["source_artifact_reference_hash"] == sha256_digest(
        "sandbox://sandbox-demo/summary.txt"
    )
    assert "source_artifact_label" not in proposal_payload
    assert proposal_payload["host_staging_label"] == "host-staging://artifact"
    assert proposal_payload["artifact_sha256"].startswith("sha256:")
    assert proposal_payload["artifact_size_bytes"] == len(b"Hello World\n")
    authority = proposal_payload["authority_evidence"]
    assert authority["status"] == "bound"
    assert authority["requester"]["principal_id"] == "admin:local-ui"
    assert authority["trusted_host"]["descriptor_hash"].startswith("sha256:")
    assert authority["policy"]["policy_digest"].startswith("sha256:")
    assert authority["manifest"] == {
        "lock_version": "1",
        "lock_digest": authority["manifest"]["lock_digest"],
        "tool_count": 24,
    }
    assert authority["input_schema"]["schema_version"] == "2"
    assert authority["runtime_candidate"]["candidate_id"].startswith("sha256:")
    assert proposal_payload["output_policy"]["file_contents_included"] is False
    assert "Hello World" not in proposal_response.text
    assert settings.workspace_root.as_posix() not in proposal_response.text
    assert approval_response.status_code == 200
    approval_scope = approval_response.json()["one_time_scope"]
    assert approval_scope["source_artifact_reference_hash"] == sha256_digest(
        "sandbox://sandbox-demo/summary.txt"
    )
    assert "source_artifact_label" not in approval_scope
    assert approval_scope["authority_snapshot_hash"] == proposal_payload["authority_snapshot_hash"]
    assert approval_scope["policy_decision"] == "require_approval"
    assert approval_scope["policy_matched_rules"] == [
        "require_approval_for_trusted_host_promotion_stage"
    ]
    assert approval_scope["policy_obligations"] == {
        "approval_mode": "one_time",
        "approval_required": True,
        "audit_level": "full",
        "placement_mode": "create_exclusive",
        "zone": "host_staging",
    }
    assert approval_scope["manifest_tool_count"] == 24
    assert approval_scope["input_schema_version"] == "2"
    assert approval_scope["runtime_candidate_posture"] == "reviewed"
    assert approval_scope["required_approver_roles"] == ["Admin", "Approver"]
    assert pending_detail.json()["effective_status"] == "approval_required"
    assert pending_detail.json()["approval_evidence"]["approver_decision"] is None
    assert pending_approval_reviews.status_code == 200
    pending_review = pending_approval_reviews.json()["approvals"][0]
    assert pending_review["approval"]["approval_id"] == approval_id
    assert pending_review["review"]["valid"] is True
    assert pending_review["review"]["binding"]["source_artifact_reference_hash"] == sha256_digest(
        "sandbox://sandbox-demo/summary.txt"
    )
    assert "source_artifact_label" not in pending_approval_reviews.text

    assert approve_response.status_code == 200
    approved = approve_response.json()
    assert approved["deciding_principal_id"] == "admin:local-ui"
    assert approved["deciding_principal_generation"].startswith("sha256:")
    assert approved["decision_reason_hash"].startswith("sha256:")
    assert approved["decision_hash"].startswith("sha256:")
    assert (
        approved["decision_authority_snapshot_hash"]
        == (proposal_payload["authority_snapshot_hash"])
    )
    decision_evidence = decided_detail.json()["approval_evidence"]["approver_decision"]
    assert decided_detail.json()["effective_status"] == "approval_approved"
    assert decision_evidence["deciding_principal_id"] == "admin:local-ui"
    assert decision_evidence["decision_hash"] == approved["decision_hash"]
    assert apply_response.status_code == 409
    assert apply_response.json()["detail"] == (
        "trusted-host promotion placement is not production-ready"
    )
    assert replay_response.status_code == 409
    assert replay_response.json()["detail"] == apply_response.json()["detail"]
    assert not settings.trusted_host_staging_root.exists()
    assert diagnostics_response.status_code == 200
    assert diagnostics_response.json()["status"] == "clean"
    assert diagnostics_response.json()["availability"] == "staging_root_descriptor"
    assert list_response.status_code == 200
    listed = list_response.json()["promotion_proposals"][0]
    assert listed["status"] == "approval_required"
    assert listed["requester_principal_id"] == "admin:local-ui"
    assert (
        listed["approval_evidence"]["approver_decision"]["decision_hash"]
        == approved["decision_hash"]
    )
    assert status_response.status_code == 200
    assert status_response.json()["trusted_host_promotions"] == "clean"
    assert audit_response.status_code == 200
    audit_payload = audit_response.text
    assert "Hello World" not in audit_payload
    assert settings.trusted_host_staging_root.as_posix() not in audit_payload
    combined_safe_payload = "\n".join(
        [
            proposal_response.text,
            approval_response.text,
            pending_detail.text,
            decided_detail.text,
            diagnostics_response.text,
            list_response.text,
            audit_response.text,
        ]
    )
    assert "sandbox://sandbox-demo/summary.txt" not in combined_safe_payload
    assert "summary.txt" not in combined_safe_payload
    assert "Hello World" not in combined_safe_payload
    assert "Traceback" not in combined_safe_payload
    audit_events = audit_response.json()["audit_events"]
    event_types = {event["event_type"] for event in audit_events}
    assert "approval.created" in event_types
    assert "approval.approved" in event_types
    assert "tool.execution.started" not in event_types
    assert "tool.execution.completed" not in event_types


def test_trusted_host_promotion_internal_fixture_completes_after_audit_evidence(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text(
        "governed output\n",
        encoding="utf-8",
    )
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    settings.trusted_host_staging_root.mkdir()
    app = promotion_ready_app(settings, placement_ready=True)

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        proposal = create_approved_promotion(client)
        apply = client.post(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
            json={"approval_id": proposal["approval_id"]},
            headers=headers,
        )
        replay = client.post(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
            json={"approval_id": proposal["approval_id"]},
            headers=headers,
        )
        current = client.get(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}",
            headers=headers,
        )
        approval = client.get(f"/approvals/{proposal['approval_id']}", headers=headers)
        diagnostics = client.get("/trusted-host-promotions/diagnostics", headers=headers)
        audit = client.get(
            "/audit-events?tool_name=trusted_host.promotion.stage",
            headers=headers,
        )

    assert apply.status_code == 200
    assert apply.json()["completion_claimed"] is True
    assert apply.json()["proposal_status"] == "completed"
    assert apply.json()["completion_audit_event_id"].startswith("evt_")
    assert apply.json()["completion_audit_event_hash"].startswith("sha256:")
    attempt = apply.json()["promotion_attempt"]
    assert attempt["status"] == "completed"
    assert attempt["staged_sha256"] == proposal["artifact_sha256"]
    assert attempt["completion_evidence_status"] == "recorded"
    assert attempt["completion_audit_event_hash"] == apply.json()["completion_audit_event_hash"]
    assert replay.status_code == 409
    assert replay.json()["detail"] == "proposal_not_applicable"
    assert current.json()["status"] == "completed"
    assert approval.json()["status"] == "executed"
    assert diagnostics.json()["placement_available"] is False
    assert diagnostics.json()["status"] == "clean"
    event_types = {event["event_type"] for event in audit.json()["audit_events"]}
    assert "tool.execution.started" not in event_types
    assert "tool.execution.completed" in event_types
    destination_dir = (
        settings.trusted_host_staging_root / "default" / proposal["promotion_proposal_id"]
    )
    destinations = list(destination_dir.iterdir())
    assert len(destinations) == 1
    assert destinations[0].read_bytes() == b"governed output\n"
    response_text = apply.text + diagnostics.text + audit.text
    assert "governed output" not in response_text
    assert settings.trusted_host_staging_root.as_posix() not in response_text


def test_trusted_host_promotion_production_readiness_has_no_operator_bypass(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text(
        "production-ready fixture\n",
        encoding="utf-8",
    )
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    settings.trusted_host_staging_root.mkdir(mode=0o700)
    app = promotion_ready_app(settings, test_fixture_ready=False)

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        proposal = create_approved_promotion(client, sandbox_id="sandbox-production-ready")
        applied = client.post(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
            json={"approval_id": proposal["approval_id"]},
            headers=headers,
        )
        diagnostics = client.get("/trusted-host-promotions/diagnostics", headers=headers)

    assert applied.status_code == 200
    assert applied.json()["proposal_status"] == "completed"
    assert diagnostics.status_code == 200
    readiness = diagnostics.json()["production_readiness"]
    assert readiness["ready"] is True
    assert readiness["reason"] == "ready"
    assert all(readiness["components"].values())
    assert readiness["operator_override_available"] is False
    assert diagnostics.json()["placement_available"] is True


def test_trusted_host_promotion_production_readiness_requires_candidate_reverification(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text(
        "candidate-reverification fence\n",
        encoding="utf-8",
    )
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    settings.trusted_host_staging_root.mkdir(mode=0o700)
    app = promotion_ready_app(
        settings,
        test_fixture_ready=False,
        configure_runtime_candidate_verifier=False,
    )

    with TestClient(app) as client:
        diagnostics = client.get(
            "/trusted-host-promotions/diagnostics",
            headers={"Authorization": "Bearer correct-token"},
        )

    readiness = diagnostics.json()["production_readiness"]
    assert readiness["ready"] is False
    assert readiness["reason"] == "runtime_candidate_reverification"
    assert readiness["components"]["verified_runtime_candidate"] is True
    assert readiness["components"]["runtime_candidate_reverification"] is False
    assert readiness["operator_override_available"] is False


def test_trusted_host_promotion_missing_verifier_restart_terminally_stales_approved_proposal(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text(
        "restart verifier fence\n",
        encoding="utf-8",
    )
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    settings.trusted_host_staging_root.mkdir(mode=0o700)
    candidate = runtime_candidate_fixture()

    initial_app = promotion_ready_app(
        settings,
        test_fixture_ready=False,
        runtime_candidate=candidate,
    )
    with TestClient(initial_app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        proposal = create_approved_promotion(
            client,
            sandbox_id="sandbox-missing-verifier-restart",
        )

    unavailable_app = promotion_ready_app(
        settings,
        test_fixture_ready=False,
        runtime_candidate=candidate,
        configure_runtime_candidate_verifier=False,
    )
    with TestClient(unavailable_app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        unavailable_apply = client.post(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
            json={"approval_id": proposal["approval_id"]},
            headers=headers,
        )
        stale_proposal = client.get(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}",
            headers=headers,
        ).json()
        preserved_approval = client.get(
            f"/approvals/{proposal['approval_id']}",
            headers=headers,
        ).json()
        unavailable_diagnostics = client.get(
            "/trusted-host-promotions/diagnostics",
            headers=headers,
        ).json()

    restored_app = promotion_ready_app(
        settings,
        test_fixture_ready=False,
        runtime_candidate=candidate,
    )
    with TestClient(restored_app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        restored_apply = client.post(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
            json={"approval_id": proposal["approval_id"]},
            headers=headers,
        )
        still_stale_proposal = client.get(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}",
            headers=headers,
        ).json()
        still_preserved_approval = client.get(
            f"/approvals/{proposal['approval_id']}",
            headers=headers,
        ).json()
        restored_diagnostics = client.get(
            "/trusted-host-promotions/diagnostics",
            headers=headers,
        ).json()

    assert unavailable_apply.status_code == 409
    assert unavailable_apply.json()["detail"] == "trusted-host promotion authority is stale"
    assert stale_proposal["status"] == "authority_stale"
    assert preserved_approval["status"] == "approved"
    assert unavailable_diagnostics["attempts"] == []
    assert restored_apply.status_code == 409
    assert restored_apply.json()["detail"] == "proposal_not_applicable"
    assert still_stale_proposal["status"] == "authority_stale"
    assert still_preserved_approval["status"] == "approved"
    assert restored_diagnostics["attempts"] == []
    assert list(settings.trusted_host_staging_root.iterdir()) == []


def test_trusted_host_promotion_production_readiness_requires_enforced_manifest_lock(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text(
        "manifest-lock fence\n",
        encoding="utf-8",
    )
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    settings.trusted_host_staging_root.mkdir(mode=0o700)
    app = promotion_ready_app(
        settings,
        test_fixture_ready=False,
        manifest_lock_required=False,
    )

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        descriptor = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(sandbox_id="sandbox-unlocked-manifest"),
            headers=headers,
        ).json()
        proposal = client.post(
            "/trusted-host-promotions/proposals",
            json={
                "workspace_id": "default",
                "sandbox_descriptor_id": descriptor["descriptor_id"],
                "sandbox_id": "sandbox-unlocked-manifest",
                "source_artifact_path": "summary.txt",
                "host_staging_label": "host-staging://artifact",
            },
            headers=headers,
        )
        diagnostics = client.get("/trusted-host-promotions/diagnostics", headers=headers)

    assert proposal.status_code == 400
    assert proposal.json()["detail"] == "trusted_host_promotion_unavailable"
    readiness = diagnostics.json()["production_readiness"]
    assert readiness["ready"] is False
    assert readiness["reason"] == "manifest_lock"
    assert readiness["components"]["manifest_lock"] is False
    assert readiness["operator_override_available"] is False


def test_trusted_host_promotion_production_readiness_rejects_workspace_fallback(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text(
        "workspace-registry fence\n",
        encoding="utf-8",
    )
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    settings.trusted_host_staging_root.mkdir(mode=0o700)
    missing_registry = tmp_path / "missing-workspaces.yaml"
    app = promotion_ready_app(
        settings,
        test_fixture_ready=False,
        workspace_registry_required=False,
        workspace_registry_path=missing_registry,
    )

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        descriptor = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(sandbox_id="sandbox-workspace-fallback"),
            headers=headers,
        ).json()
        proposal = client.post(
            "/trusted-host-promotions/proposals",
            json={
                "workspace_id": "default",
                "sandbox_descriptor_id": descriptor["descriptor_id"],
                "sandbox_id": "sandbox-workspace-fallback",
                "source_artifact_path": "summary.txt",
                "host_staging_label": "host-staging://artifact",
            },
            headers=headers,
        )
        diagnostics = client.get("/trusted-host-promotions/diagnostics", headers=headers)

    assert proposal.status_code == 400
    assert proposal.json()["detail"] == "trusted_host_promotion_unavailable"
    readiness = diagnostics.json()["production_readiness"]
    assert readiness["ready"] is False
    assert readiness["reason"] == "workspace_registry"
    assert readiness["components"]["workspace_registry"] is False
    assert readiness["operator_override_available"] is False
    assert not missing_registry.exists()


def test_trusted_host_promotion_production_readiness_requires_principal_registry(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text(
        "principal-registry fence\n",
        encoding="utf-8",
    )
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    settings.trusted_host_staging_root.mkdir(mode=0o700)
    app = promotion_ready_app(
        settings,
        test_fixture_ready=False,
        principal_registry_required=False,
    )

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        descriptor = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(sandbox_id="sandbox-principal-unrequired"),
            headers=headers,
        ).json()
        proposal = client.post(
            "/trusted-host-promotions/proposals",
            json={
                "workspace_id": "default",
                "sandbox_descriptor_id": descriptor["descriptor_id"],
                "sandbox_id": "sandbox-principal-unrequired",
                "source_artifact_path": "summary.txt",
                "host_staging_label": "host-staging://artifact",
            },
            headers=headers,
        )
        diagnostics = client.get("/trusted-host-promotions/diagnostics", headers=headers)

    assert proposal.status_code == 400
    assert proposal.json()["detail"] == "trusted_host_promotion_unavailable"
    readiness = diagnostics.json()["production_readiness"]
    assert readiness["ready"] is False
    assert readiness["reason"] == "principal_registry"
    assert readiness["components"]["principal_registry"] is False
    assert readiness["operator_override_available"] is False


def test_trusted_host_promotion_production_readiness_requires_approver_role(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text(
        "approver-role readiness fence\n",
        encoding="utf-8",
    )
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    settings.trusted_host_staging_root.mkdir(mode=0o700)
    principal_registry = tmp_path / "principals-without-approver.yaml"
    principal_registry.write_text(
        "principals:\n"
        "  - id: admin:local-ui\n"
        "    type: admin\n"
        "    display_name: Local Admin Without Approver\n"
        "    roles: [Admin, Auditor]\n"
        "    enabled: true\n",
        encoding="utf-8",
    )
    app = promotion_ready_app(
        settings,
        test_fixture_ready=False,
        principal_registry_path=principal_registry,
    )

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        descriptor = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(sandbox_id="sandbox-missing-approver-readiness"),
            headers=headers,
        ).json()
        proposal = client.post(
            "/trusted-host-promotions/proposals",
            json={
                "workspace_id": "default",
                "sandbox_descriptor_id": descriptor["descriptor_id"],
                "sandbox_id": "sandbox-missing-approver-readiness",
                "source_artifact_path": "summary.txt",
                "host_staging_label": "host-staging://artifact",
            },
            headers=headers,
        )
        diagnostics = client.get("/trusted-host-promotions/diagnostics", headers=headers)

    assert proposal.status_code == 400
    assert proposal.json()["detail"] == "trusted_host_promotion_unavailable"
    readiness = diagnostics.json()["production_readiness"]
    assert readiness["ready"] is False
    assert readiness["reason"] == "principal_registry"
    assert readiness["components"]["principal_registry"] is False
    assert readiness["operator_override_available"] is False


def test_trusted_host_promotion_missing_approver_role_cannot_decide_or_place(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text(
        "must never be placed\n",
        encoding="utf-8",
    )
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    settings.trusted_host_staging_root.mkdir(mode=0o700)
    principal_registry = tmp_path / "principals-without-approver.yaml"
    principal_registry.write_text(
        "principals:\n"
        "  - id: admin:local-ui\n"
        "    type: admin\n"
        "    display_name: Local Admin Without Approver\n"
        "    roles: [Admin, Auditor]\n"
        "    enabled: true\n",
        encoding="utf-8",
    )
    app = promotion_ready_app(
        settings,
        placement_ready=True,
        principal_registry_path=principal_registry,
    )

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        descriptor = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(sandbox_id="sandbox-missing-approver"),
            headers=headers,
        ).json()
        proposal = client.post(
            "/trusted-host-promotions/proposals",
            json={
                "workspace_id": "default",
                "sandbox_descriptor_id": descriptor["descriptor_id"],
                "sandbox_id": "sandbox-missing-approver",
                "source_artifact_path": "summary.txt",
                "host_staging_label": "host-staging://artifact",
            },
            headers=headers,
        ).json()
        approval_path = f"/approvals/{proposal['approval_id']}"
        approve = client.post(
            f"{approval_path}/approve",
            json={"decision": "approve"},
            headers=headers,
        )
        deny = client.post(
            f"{approval_path}/deny",
            json={"decision": "deny"},
            headers=headers,
        )
        pending = client.get(approval_path, headers=headers)
        apply = client.post(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
            json={"approval_id": proposal["approval_id"]},
            headers=headers,
        )
        diagnostics = client.get("/trusted-host-promotions/diagnostics", headers=headers)

    for decision in (approve, deny):
        assert decision.status_code == 409
        assert decision.json()["detail"] == (
            "trusted-host promotion approval decision is not authorized"
        )
    assert pending.status_code == 200
    assert pending.json()["status"] == "pending"
    assert apply.status_code == 409
    assert apply.json()["detail"] == "trusted-host promotion authority is stale"
    assert diagnostics.json()["attempts"] == []
    assert list(settings.trusted_host_staging_root.iterdir()) == []


def test_trusted_host_promotion_apply_opens_source_exactly_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text("retained\n", encoding="utf-8")
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    settings.trusted_host_staging_root.mkdir(mode=0o700)
    app = promotion_ready_app(settings, placement_ready=True)

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        proposal = create_approved_promotion(client, sandbox_id="sandbox-source-once")
        service = cast(TrustedHostPromotionService, app.state.trusted_host_promotion_service)
        filesystem = service.read_executor.filesystems["default"]
        original_read = filesystem.read_file_bytes
        call_count = 0

        def counted_read(path: Path) -> bytes:
            nonlocal call_count
            call_count += 1
            return original_read(path)

        monkeypatch.setattr(filesystem, "read_file_bytes", counted_read)
        apply = client.post(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
            json={"approval_id": proposal["approval_id"]},
            headers=headers,
        )

    assert apply.status_code == 200
    assert call_count == 1
    destinations = list(
        (
            settings.trusted_host_staging_root / "default" / proposal["promotion_proposal_id"]
        ).iterdir()
    )
    assert len(destinations) == 1
    assert destinations[0].read_bytes() == b"retained\n"


def test_trusted_host_promotion_internal_fixture_concurrent_replay_reserves_once(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text("bounded\n", encoding="utf-8")
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    settings.trusted_host_staging_root.mkdir()
    app = promotion_ready_app(settings, placement_ready=True)

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        proposal = create_approved_promotion(client, sandbox_id="sandbox-concurrent")

        def apply_once() -> tuple[int, dict[str, Any]]:
            response = client.post(
                f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
                json={"approval_id": proposal["approval_id"]},
                headers=headers,
            )
            return response.status_code, cast(dict[str, Any], response.json())

        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(lambda _: apply_once(), range(2)))
        diagnostics = client.get("/trusted-host-promotions/diagnostics", headers=headers).json()

    assert sorted(status for status, _ in responses) == [200, 409]
    assert len(diagnostics["attempts"]) == 1
    destination_dir = (
        settings.trusted_host_staging_root / "default" / proposal["promotion_proposal_id"]
    )
    assert len(list(destination_dir.iterdir())) == 1


def test_concurrent_distinct_promotions_complete_on_one_valid_audit_chain(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text("bounded\n", encoding="utf-8")
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    settings.trusted_host_staging_root.mkdir()
    app = promotion_ready_app(settings, placement_ready=True)

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        proposals = [
            create_approved_promotion(client, sandbox_id=f"sandbox-concurrent-{index}")
            for index in range(2)
        ]

        def apply_once(proposal: dict[str, Any]) -> tuple[int, dict[str, Any]]:
            response = client.post(
                f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
                json={"approval_id": proposal["approval_id"]},
                headers=headers,
            )
            return response.status_code, cast(dict[str, Any], response.json())

        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(apply_once, proposals))
        diagnostics = client.get("/trusted-host-promotions/diagnostics", headers=headers).json()
        audit_writer = cast(AuditWriter, app.state.audit_writer)
        audit_verification = audit_writer.verify_chain()
        audit_diagnostics = audit_writer.diagnostics()

    assert [status for status, _ in responses] == [200, 200]
    assert all(payload["completion_claimed"] is True for _, payload in responses)
    assert len(diagnostics["attempts"]) == 2
    assert {attempt["status"] for attempt in diagnostics["attempts"]} == {"completed"}
    assert audit_verification.valid is True
    assert audit_diagnostics["sqlite_event_count"] == audit_diagnostics["jsonl_line_count"]
    assert audit_diagnostics["jsonl_head_hash"] == audit_verification.head_hash


@pytest.mark.parametrize("source_drift", ["bytes", "symlink", "hardlink", "directory"])
def test_trusted_host_promotion_source_drift_is_terminal_before_reservation(
    tmp_path: Path,
    source_drift: str,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    source = settings.workspace_root / "summary.txt"
    source.write_text("original\n", encoding="utf-8")
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    settings.trusted_host_staging_root.mkdir()
    app = promotion_ready_app(settings, placement_ready=True)

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        proposal = create_approved_promotion(client, sandbox_id=f"sandbox-{source_drift}")
        source.unlink()
        if source_drift == "bytes":
            source.write_text("changed\n", encoding="utf-8")
        elif source_drift == "symlink":
            outside = tmp_path / "outside.txt"
            outside.write_text("original\n", encoding="utf-8")
            source.symlink_to(outside)
        elif source_drift == "hardlink":
            outside = tmp_path / "outside.txt"
            outside.write_text("original\n", encoding="utf-8")
            os.link(outside, source)
        else:
            source.mkdir()
        apply = client.post(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
            json={"approval_id": proposal["approval_id"]},
            headers=headers,
        )
        current = client.get(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}",
            headers=headers,
        ).json()
        approval = client.get(f"/approvals/{proposal['approval_id']}", headers=headers).json()
        diagnostics = client.get("/trusted-host-promotions/diagnostics", headers=headers).json()

    assert apply.status_code == 409
    assert apply.json()["detail"] == "trusted-host promotion source is stale"
    assert current["status"] == "authority_stale"
    assert approval["status"] == "approved"
    assert diagnostics["attempts"] == []
    assert list(settings.trusted_host_staging_root.iterdir()) == []


def test_trusted_host_promotion_rejects_source_over_4096_bytes(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_bytes(b"a" * 4097)
    app = promotion_ready_app(settings, placement_ready=True)

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        descriptor = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(sandbox_id="sandbox-oversize"),
            headers=headers,
        ).json()
        proposal = client.post(
            "/trusted-host-promotions/proposals",
            json={
                "workspace_id": "default",
                "sandbox_descriptor_id": descriptor["descriptor_id"],
                "sandbox_id": "sandbox-oversize",
                "source_artifact_path": "summary.txt",
                "host_staging_label": "host-staging://artifact",
            },
            headers=headers,
        )
        proposals = client.get("/trusted-host-promotions/proposals", headers=headers).json()

    assert proposal.status_code == 400
    assert proposal.json()["detail"] == "source artifact exceeds promotion limit"
    assert proposals["promotion_proposals"] == []


def test_trusted_host_promotion_approval_decision_drift_is_terminal(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text("original\n", encoding="utf-8")
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    settings.trusted_host_staging_root.mkdir()
    app = promotion_ready_app(settings, placement_ready=True)

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        proposal = create_approved_promotion(client, sandbox_id="sandbox-decision-drift")
        with sqlite3.connect(settings.db_path) as connection:
            connection.execute(
                "UPDATE approvals SET decision_hash = ? WHERE approval_id = ?",
                ("sha256:" + ("e" * 64), proposal["approval_id"]),
            )
            connection.commit()
        apply = client.post(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
            json={"approval_id": proposal["approval_id"]},
            headers=headers,
        )
        current = client.get(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}",
            headers=headers,
        ).json()
        diagnostics = client.get("/trusted-host-promotions/diagnostics", headers=headers).json()

    assert apply.status_code == 409
    assert apply.json()["detail"] == "trusted-host promotion authority is stale"
    assert current["status"] == "authority_stale"
    assert diagnostics["status"] == "stale"
    assert diagnostics["conditions"] == ["stale"]
    assert diagnostics["recommendations"][0]["retry_available"] is False
    assert diagnostics["attempts"] == []
    assert list(settings.trusted_host_staging_root.iterdir()) == []


@pytest.mark.parametrize(
    "authority_component",
    [
        "principal",
        "workspace_record",
        "workspace_generation",
        "sandbox_payload",
        "sandbox_generation",
        "trusted_host_hash",
        "trusted_host_generation",
        "trusted_host_registry_schema",
        "policy_digest",
        "policy_version",
        "policy_document",
        "policy_rules",
        "policy_obligations",
        "manifest_digest",
        "manifest_version",
        "input_schema_digest",
        "input_schema_version",
        "runtime_candidate",
    ],
)
def test_trusted_host_promotion_every_authority_component_drift_is_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    authority_component: str,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text("original\n", encoding="utf-8")
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    settings.trusted_host_staging_root.mkdir(mode=0o700)
    app = promotion_ready_app(settings, placement_ready=True)

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        proposal = create_approved_promotion(client, sandbox_id=f"sandbox-{authority_component}")
        service = cast(TrustedHostPromotionService, app.state.trusted_host_promotion_service)
        stored = service.store.get_proposal(proposal["promotion_proposal_id"])
        assert stored.authority_snapshot_json is not None
        snapshot = PromotionAuthoritySnapshot.model_validate(stored.authority_snapshot_json)
        changed_hash = "sha256:" + ("f" * 64)

        if authority_component == "principal":
            changed_principal = snapshot.requesting_principal.model_copy(
                update={"identity_generation": changed_hash}
            )
            monkeypatch.setattr(
                service.principal_registry,
                "admin_context",
                lambda: changed_principal,
            )
        elif authority_component.startswith("workspace_"):
            workspace_record_hash = (
                changed_hash
                if authority_component == "workspace_record"
                else snapshot.workspace.workspace_record_hash
            )
            workspace_generation = (
                changed_hash
                if authority_component == "workspace_generation"
                else snapshot.workspace.workspace_registry_generation
            )
            monkeypatch.setattr(
                service.workspace_registry,
                "authority_record",
                lambda workspace_id=None: (
                    snapshot.workspace.workspace_id,
                    workspace_record_hash,
                    workspace_generation,
                ),
            )
        elif authority_component.startswith("sandbox_"):
            sandbox_update = {
                "descriptor_payload_hash": changed_hash
                if authority_component == "sandbox_payload"
                else snapshot.sandbox.descriptor_payload_hash,
                "descriptor_generation": changed_hash
                if authority_component == "sandbox_generation"
                else snapshot.sandbox.descriptor_generation,
            }
            changed_sandbox = snapshot.sandbox.model_copy(update=sandbox_update)
            monkeypatch.setattr(
                service.descriptor_store,
                "authority_record",
                lambda descriptor_id: changed_sandbox,
            )
        elif authority_component.startswith("trusted_host_"):
            host_field = {
                "trusted_host_hash": "descriptor_hash",
                "trusted_host_generation": "descriptor_generation",
                "trusted_host_registry_schema": "registry_schema_digest",
            }[authority_component]
            changed_host = snapshot.trusted_host.model_copy(update={host_field: changed_hash})
            monkeypatch.setattr(
                service.trusted_host_registry,
                "resolve",
                lambda **kwargs: changed_host,
            )
        elif authority_component.startswith("policy_"):
            original_policy_authority = service._policy_authority

            def changed_policy_authority(
                **kwargs: object,
            ) -> tuple[PolicyAuthorityRecord, JsonObject]:
                policy, obligations = original_policy_authority(**kwargs)  # type: ignore[arg-type]
                policy_update: dict[str, object] = {
                    "policy_digest": changed_hash
                    if authority_component == "policy_digest"
                    else policy.policy_digest,
                    "policy_version": "changed-policy-version"
                    if authority_component == "policy_version"
                    else policy.policy_version,
                    "document_version": "changed-document-version"
                    if authority_component == "policy_document"
                    else policy.document_version,
                    "matched_rules": ("changed_policy_rule",)
                    if authority_component == "policy_rules"
                    else policy.matched_rules,
                    "obligations_digest": changed_hash
                    if authority_component == "policy_obligations"
                    else policy.obligations_digest,
                }
                return policy.model_copy(update=policy_update), obligations

            monkeypatch.setattr(service, "_policy_authority", changed_policy_authority)
        elif authority_component.startswith("manifest_"):
            assert service._manifest_authority_record is not None
            service._manifest_authority_record = service._manifest_authority_record.model_copy(
                update={
                    "lock_digest": changed_hash
                    if authority_component == "manifest_digest"
                    else service._manifest_authority_record.lock_digest,
                    "lock_version": "changed-lock-version"
                    if authority_component == "manifest_version"
                    else service._manifest_authority_record.lock_version,
                }
            )
        elif authority_component.startswith("input_schema_"):
            service.input_schema_authority = service.input_schema_authority.model_copy(
                update={
                    "schema_digest": changed_hash
                    if authority_component == "input_schema_digest"
                    else service.input_schema_authority.schema_digest,
                    "schema_version": "3"
                    if authority_component == "input_schema_version"
                    else service.input_schema_authority.schema_version,
                }
            )
        else:
            assert service.runtime_candidate is not None
            service.runtime_candidate = service.runtime_candidate.model_copy(
                update={"review_packet_digest": changed_hash}
            )

        apply = client.post(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
            json={"approval_id": proposal["approval_id"]},
            headers=headers,
        )
        current = client.get(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}",
            headers=headers,
        ).json()
        approval = client.get(f"/approvals/{proposal['approval_id']}", headers=headers).json()
        diagnostics = client.get("/trusted-host-promotions/diagnostics", headers=headers).json()

    assert apply.status_code == 409
    assert apply.json()["detail"] == "trusted-host promotion authority is stale"
    assert current["status"] == "authority_stale"
    assert approval["status"] == "approved"
    assert diagnostics["attempts"] == []
    assert list(settings.trusted_host_staging_root.iterdir()) == []


def test_trusted_host_promotion_installed_file_drift_is_terminal_before_reservation(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text(
        "must never be placed after runtime drift\n",
        encoding="utf-8",
    )
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    settings.trusted_host_staging_root.mkdir(mode=0o700)
    package_root = tmp_path / "runtime-package"
    installed_file = package_root / "apps" / "runtime.py"
    installed_file.parent.mkdir(parents=True)
    installed_file.write_text("reviewed = True\n", encoding="utf-8")
    dependency_lock = package_root / "uv.lock"
    dependency_lock.write_text("lock\n", encoding="utf-8")

    def file_digest(path: Path) -> str:
        return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()

    files = [
        {"path": "apps/runtime.py", "sha256": file_digest(installed_file)},
        {"path": "uv.lock", "sha256": file_digest(dependency_lock)},
    ]
    reviewed_inventory_digest = sha256_digest(
        cast(JsonObject, {"schema_version": "1", "files": files})
    )
    candidate_core: JsonObject = {
        "source_commit": "1" * 40,
        "inventory_schema_version": "1",
        "reviewed_inventory_digest": reviewed_inventory_digest,
        "dependency_lock_digest": file_digest(dependency_lock),
        "release_artifact_digest": "sha256:" + ("c" * 64),
        "evidence_schema_version": "1",
    }
    candidate_id = sha256_digest(candidate_core)
    review_packet_digest = "sha256:" + ("d" * 64)
    inventory_path = package_root / "runtime-candidate-inventory.json"
    inventory_path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "source_commit": "1" * 40,
                "files": files,
                "dependency_lock_path": "uv.lock",
                "dependency_lock_digest": file_digest(dependency_lock),
                "release_artifact_digest": "sha256:" + ("c" * 64),
                "review_packet_digest": review_packet_digest,
                "evidence_schema_version": "1",
                "reviewed_inventory_digest": reviewed_inventory_digest,
                "candidate_id": candidate_id,
            }
        ),
        encoding="utf-8",
    )
    authorization_path = tmp_path / "runtime-authority" / "api-candidate.json"
    authorization_path.parent.mkdir()
    authorization: JsonObject = {
        "authorization_id": "rca_" + ("a" * 32),
        "candidate_id": candidate_id,
        "reviewed_commit": "1" * 40,
        "inventory_schema_version": "1",
        "reviewed_inventory_digest": reviewed_inventory_digest,
        "dependency_lock_digest": file_digest(dependency_lock),
        "release_artifact_digest": "sha256:" + ("c" * 64),
        "review_packet_digest": review_packet_digest,
        "evidence_schema_version": "1",
        "authorized_at": "2026-07-18T00:00:00+00:00",
    }
    authorization["record_hash"] = sha256_digest(authorization)
    authorization_path.write_text(json.dumps(authorization), encoding="utf-8")
    installed_file.chmod(0o444)
    dependency_lock.chmod(0o444)
    inventory_path.chmod(0o444)
    package_root.chmod(0o555)
    authorization_path.chmod(0o444)
    verifier = RuntimeCandidateVerifier(
        package_root=package_root,
        inventory_path=inventory_path,
        authorization_path=authorization_path,
        allow_test_paths=True,
    )
    candidate = RuntimeCandidateRecord.model_validate(verifier.verify())
    verification_count = 0

    def verify_installed_candidate() -> RuntimeCandidateRecord:
        nonlocal verification_count
        verification_count += 1
        return RuntimeCandidateRecord.model_validate(verifier.verify())

    app = promotion_ready_app(
        settings,
        placement_ready=True,
        runtime_candidate=candidate,
        runtime_candidate_verifier=verify_installed_candidate,
    )

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        proposal = create_approved_promotion(
            client,
            sandbox_id="sandbox-installed-runtime-drift",
        )
        installed_file.chmod(0o644)
        installed_file.write_text("reviewed = False\n", encoding="utf-8")
        installed_file.chmod(0o444)
        apply = client.post(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
            json={"approval_id": proposal["approval_id"]},
            headers=headers,
        )
        current = client.get(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}",
            headers=headers,
        ).json()
        approval = client.get(
            f"/approvals/{proposal['approval_id']}",
            headers=headers,
        ).json()
        diagnostics = client.get(
            "/trusted-host-promotions/diagnostics",
            headers=headers,
        ).json()

    assert verification_count == 2
    assert apply.status_code == 409
    assert apply.json()["detail"] == "trusted-host promotion authority is stale"
    assert current["status"] == "authority_stale"
    assert approval["status"] == "approved"
    assert diagnostics["attempts"] == []
    assert list(settings.trusted_host_staging_root.iterdir()) == []


def test_trusted_host_promotion_postwrite_root_drift_records_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text("original\n", encoding="utf-8")
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    retained_root = tmp_path / "retained-staging-root"
    settings.trusted_host_staging_root.mkdir()
    app = promotion_ready_app(settings, placement_ready=True)

    def replace_root() -> None:
        settings.trusted_host_staging_root.rename(retained_root)
        settings.trusted_host_staging_root.mkdir()

    monkeypatch.setattr(
        trusted_host_promotions_module,
        "TrustedHostPlacement",
        lambda root: TrustedHostPlacement(root, after_write_hook=replace_root),
    )
    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        proposal = create_approved_promotion(client, sandbox_id="sandbox-postwrite-drift")
        apply = client.post(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
            json={"approval_id": proposal["approval_id"]},
            headers=headers,
        )
        current = client.get(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}",
            headers=headers,
        ).json()
        approval = client.get(f"/approvals/{proposal['approval_id']}", headers=headers).json()
        diagnostics = client.get("/trusted-host-promotions/diagnostics", headers=headers).json()

    assert apply.status_code == 409
    assert apply.json()["detail"] == "staging_root_namespace_drift"
    assert current["status"] == "placement_evidence_recovery_required"
    assert approval["status"] == "failed"
    assert diagnostics["status"] == "recovery_required"
    assert len(diagnostics["attempts"]) == 1
    attempt = diagnostics["attempts"][0]
    assert attempt["status"] == "placement_evidence_recovery_required"
    assert attempt["failure_reason"] == "staging_root_namespace_drift"
    assert list(settings.trusted_host_staging_root.iterdir()) == []
    retained_files = list(retained_root.rglob("*.artifact"))
    assert len(retained_files) == 1
    assert retained_files[0].read_bytes() == b"original\n"
    response_text = apply.text + json.dumps(diagnostics)
    assert settings.trusted_host_staging_root.as_posix() not in response_text
    assert retained_root.as_posix() not in response_text
    assert "original" not in response_text


def test_trusted_host_promotion_success_evidence_failure_records_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text("original\n", encoding="utf-8")
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    settings.trusted_host_staging_root.mkdir(mode=0o700)
    app = promotion_ready_app(settings, placement_ready=True)

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        proposal = create_approved_promotion(client, sandbox_id="sandbox-evidence-failure")
        service = cast(TrustedHostPromotionService, app.state.trusted_host_promotion_service)

        def fail_success(*args: object, **kwargs: object) -> NoReturn:
            raise TrustedHostPromotionError("simulated success evidence failure")

        monkeypatch.setattr(service.store, "record_placement_success", fail_success)
        apply = client.post(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
            json={"approval_id": proposal["approval_id"]},
            headers=headers,
        )
        current = client.get(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}",
            headers=headers,
        ).json()
        approval = client.get(f"/approvals/{proposal['approval_id']}", headers=headers).json()
        diagnostics = client.get("/trusted-host-promotions/diagnostics", headers=headers).json()

    assert apply.status_code == 409
    assert apply.json()["detail"] == "placement_evidence_recovery_required"
    assert "simulated" not in apply.text
    assert current["status"] == "placement_evidence_recovery_required"
    assert approval["status"] == "failed"
    assert diagnostics["status"] == "recovery_required"
    assert diagnostics["attempts"][0]["status"] == ("placement_evidence_recovery_required")
    assert diagnostics["attempts"][0]["failure_reason"] == ("placement_evidence_update_failed")
    destinations = list(
        (
            settings.trusted_host_staging_root / "default" / proposal["promotion_proposal_id"]
        ).iterdir()
    )
    assert len(destinations) == 1
    assert destinations[0].read_bytes() == b"original\n"


def test_trusted_host_promotion_prewrite_root_drift_records_no_effect_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text("original\n", encoding="utf-8")
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    retained_root = tmp_path / "retained-staging-root"
    settings.trusted_host_staging_root.mkdir(mode=0o700)
    app = promotion_ready_app(settings, placement_ready=True)

    class ReplaceBeforePlacement:
        def __init__(self, root: Path) -> None:
            self._placement = TrustedHostPlacement(root)

        def __enter__(self) -> ReplaceBeforePlacement:
            return self

        def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
            self._placement.close()

        def place(self, *args: object, **kwargs: object) -> object:
            settings.trusted_host_staging_root.rename(retained_root)
            settings.trusted_host_staging_root.mkdir(mode=0o700)
            return self._placement.place(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(
        trusted_host_promotions_module,
        "TrustedHostPlacement",
        ReplaceBeforePlacement,
    )
    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        proposal = create_approved_promotion(client, sandbox_id="sandbox-prewrite-drift")
        apply = client.post(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
            json={"approval_id": proposal["approval_id"]},
            headers=headers,
        )
        current = client.get(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}",
            headers=headers,
        ).json()
        approval = client.get(f"/approvals/{proposal['approval_id']}", headers=headers).json()
        diagnostics = client.get("/trusted-host-promotions/diagnostics", headers=headers).json()

    assert apply.status_code == 409
    assert apply.json()["detail"] == "staging_root_namespace_drift"
    assert current["status"] == "failed"
    assert approval["status"] == "failed"
    assert diagnostics["status"] == "incomplete"
    assert len(diagnostics["attempts"]) == 1
    assert diagnostics["attempts"][0]["status"] == "failed"
    assert diagnostics["attempts"][0]["failure_reason"] == "staging_root_namespace_drift"
    assert list(settings.trusted_host_staging_root.iterdir()) == []
    assert list(retained_root.iterdir()) == []


def test_trusted_host_promotion_reservation_rolls_back_all_three_records(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text("original\n", encoding="utf-8")
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    settings.trusted_host_staging_root.mkdir()
    app = promotion_ready_app(settings, placement_ready=True)

    def fail_attempt_insert(*args: object, **kwargs: object) -> None:
        raise sqlite3.IntegrityError("simulated attempt insert failure")

    monkeypatch.setattr(
        TrustedHostPromotionStore,
        "_insert_attempt",
        staticmethod(fail_attempt_insert),
    )
    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        proposal = create_approved_promotion(client, sandbox_id="sandbox-reservation-rollback")
        apply = client.post(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
            json={"approval_id": proposal["approval_id"]},
            headers=headers,
        )
        current = client.get(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}",
            headers=headers,
        ).json()
        approval = client.get(f"/approvals/{proposal['approval_id']}", headers=headers).json()
        diagnostics = client.get("/trusted-host-promotions/diagnostics", headers=headers).json()

    assert apply.status_code == 409
    assert apply.json()["detail"] == "trusted-host execution reservation failed"
    assert current["status"] == "approval_required"
    assert approval["status"] == "approved"
    assert diagnostics["attempts"] == []
    assert list(settings.trusted_host_staging_root.iterdir()) == []
    assert "simulated" not in apply.text


def test_trusted_host_promotion_compare_and_set_drift_becomes_terminal_stale(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text("original\n", encoding="utf-8")
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    settings.trusted_host_staging_root.mkdir()
    app = promotion_ready_app(settings, placement_ready=True)
    original_placement = TrustedHostPlacement

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        proposal = create_approved_promotion(client, sandbox_id="sandbox-cas-drift")

        def mutate_before_reservation(root: Path) -> TrustedHostPlacement:
            with sqlite3.connect(settings.db_path) as connection:
                connection.execute(
                    """
                    UPDATE trusted_host_promotion_proposals
                    SET metadata_json = '{}'
                    WHERE proposal_id = ?
                    """,
                    (proposal["promotion_proposal_id"],),
                )
                connection.commit()
            return original_placement(root)

        monkeypatch.setattr(
            trusted_host_promotions_module,
            "TrustedHostPlacement",
            mutate_before_reservation,
        )
        apply = client.post(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
            json={"approval_id": proposal["approval_id"]},
            headers=headers,
        )
        current = client.get(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}",
            headers=headers,
        ).json()
        approval = client.get(f"/approvals/{proposal['approval_id']}", headers=headers).json()
        diagnostics = client.get("/trusted-host-promotions/diagnostics", headers=headers).json()

    assert apply.status_code == 409
    assert apply.json()["detail"] == "trusted-host promotion authority is stale"
    assert current["status"] == "authority_stale"
    assert approval["status"] == "approved"
    assert diagnostics["attempts"] == []
    assert list(settings.trusted_host_staging_root.iterdir()) == []


def test_trusted_host_promotion_destination_conflict_is_terminal_without_overwrite(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text("new bytes\n", encoding="utf-8")
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    settings.trusted_host_staging_root.mkdir()
    app = promotion_ready_app(settings, placement_ready=True)

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        proposal = create_approved_promotion(client, sandbox_id="sandbox-conflict")
        attempt_id = (
            "thpa_"
            + hashlib.sha256(proposal["promotion_proposal_id"].encode("utf-8")).hexdigest()[:32]
        )
        destination_dir = (
            settings.trusted_host_staging_root / "default" / proposal["promotion_proposal_id"]
        )
        destination_dir.mkdir(parents=True)
        destination = destination_dir / f"{attempt_id}-artifact.artifact"
        destination.write_bytes(b"existing bytes\n")
        apply = client.post(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
            json={"approval_id": proposal["approval_id"]},
            headers=headers,
        )
        current = client.get(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}",
            headers=headers,
        ).json()
        approval = client.get(f"/approvals/{proposal['approval_id']}", headers=headers).json()
        diagnostics = client.get("/trusted-host-promotions/diagnostics", headers=headers).json()

    assert apply.status_code == 409
    assert apply.json()["detail"] == "destination_conflict"
    assert destination.read_bytes() == b"existing bytes\n"
    assert current["status"] == "failed"
    assert approval["status"] == "failed"
    assert len(diagnostics["attempts"]) == 1
    assert diagnostics["attempts"][0]["status"] == "failed"
    assert diagnostics["attempts"][0]["failure_reason"] == "destination_conflict"
    assert "new bytes" not in apply.text + json.dumps(diagnostics)


@pytest.mark.parametrize(
    ("decision", "extra_obligation", "expected_detail"),
    [
        ("deny", "", "trusted-host promotion policy must require approval"),
        ("allow", "", "trusted-host promotion policy must require approval"),
        (
            "require_approval",
            "      unreviewed_obligation: true\n",
            "trusted-host promotion policy obligations are invalid",
        ),
    ],
)
def test_trusted_host_promotion_policy_fails_closed(
    tmp_path: Path,
    decision: str,
    extra_obligation: str,
    expected_detail: str,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text("bounded\n", encoding="utf-8")
    app = promotion_ready_app(settings)
    settings.policy_path.write_text(
        f"""
version: promotion-negative-v1
rules:
  - id: promotion_negative
    decision: {decision}
    reason: bounded test decision
    match:
      tool.name: trusted_host.promotion.stage
    obligations:
      approval_mode: one_time
      approval_required: true
      audit_level: full
      placement_mode: create_exclusive
      zone: host_staging
{extra_obligation}""",
        encoding="utf-8",
    )

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        descriptor = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(sandbox_id="sandbox-policy-negative"),
            headers=headers,
        ).json()
        response = client.post(
            "/trusted-host-promotions/proposals",
            json={
                "workspace_id": "default",
                "sandbox_descriptor_id": descriptor["descriptor_id"],
                "sandbox_id": "sandbox-policy-negative",
                "source_artifact_path": "summary.txt",
                "host_staging_label": "host-staging://artifact",
            },
            headers=headers,
        )
        proposals = client.get("/trusted-host-promotions/proposals", headers=headers).json()
        approvals = client.get("/approvals", headers=headers).json()

    assert response.status_code == 400
    assert response.json()["detail"] == expected_detail
    assert proposals["promotion_proposals"] == []
    assert approvals["approvals"] == []


@pytest.mark.parametrize(
    "matched_rules",
    [
        ["require_approval_for_trusted_host_promotion_stage"] * 2,
        ["z_rule", "a_rule"],
    ],
    ids=["duplicate", "unsorted"],
)
def test_trusted_host_promotion_rejects_noncanonical_policy_rule_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    matched_rules: list[str],
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text("bounded\n", encoding="utf-8")
    app = promotion_ready_app(settings)

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        service = cast(TrustedHostPromotionService, app.state.trusted_host_promotion_service)
        original_evaluate = service.policy_engine.evaluate

        def invalid_rule_evidence(policy_input: PolicyInput) -> PolicyDecision:
            decision = original_evaluate(policy_input)
            return decision.model_copy(update={"matched_rules": matched_rules})

        monkeypatch.setattr(service.policy_engine, "evaluate", invalid_rule_evidence)
        descriptor = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(sandbox_id="sandbox-policy-evidence"),
            headers=headers,
        ).json()
        response = client.post(
            "/trusted-host-promotions/proposals",
            json={
                "workspace_id": "default",
                "sandbox_descriptor_id": descriptor["descriptor_id"],
                "sandbox_id": "sandbox-policy-evidence",
                "source_artifact_path": "summary.txt",
                "host_staging_label": "host-staging://artifact",
            },
            headers=headers,
        )
        proposals = client.get("/trusted-host-promotions/proposals", headers=headers).json()

    assert response.status_code == 400
    assert response.json()["detail"] == ("trusted-host promotion policy rule evidence is invalid")
    assert proposals["promotion_proposals"] == []


def test_trusted_host_promotion_routes_reject_opa_without_calling_opa(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text("bounded\n", encoding="utf-8")
    app = promotion_ready_app(settings)
    settings.policy_engine = "opa"
    settings.opa_url = "http://opa.example:8181"
    settings.opa_bundle_manifest_path = write_opa_bundle(tmp_path)

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        descriptor = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(sandbox_id="sandbox-opa"),
            headers=headers,
        ).json()
        proposal = client.post(
            "/trusted-host-promotions/proposals",
            json={
                "workspace_id": "default",
                "sandbox_descriptor_id": descriptor["descriptor_id"],
                "sandbox_id": "sandbox-opa",
                "source_artifact_path": "summary.txt",
                "host_staging_label": "host-staging://artifact",
            },
            headers=headers,
        )
        apply = client.post(
            f"/trusted-host-promotions/proposals/thp_{'1' * 32}/apply",
            json={"approval_id": f"appr_{'2' * 32}"},
            headers=headers,
        )

    assert proposal.status_code == 400
    assert proposal.json()["detail"] == "unsupported_policy_engine_for_promotion"
    assert apply.status_code == 409
    assert apply.json()["detail"] == "unsupported_policy_engine_for_promotion"


def test_trusted_host_promotion_rejects_duplicate_manifest_evidence(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    app = promotion_ready_app(settings)
    settings.manifest_dir = tmp_path / "tool-manifests"
    shutil.copytree(Path("tool-manifests"), settings.manifest_dir, dirs_exist_ok=True)
    duplicate_lock = tmp_path / "duplicate-tool-manifests.lock.json"
    lock_text = Path("tool-manifests.lock.json").read_text(encoding="utf-8")
    duplicate_lock.write_text(
        lock_text.replace(
            '"lockfile_version": 1,',
            '"lockfile_version": 1,\n  "lockfile_version": 1,',
            1,
        ),
        encoding="utf-8",
    )
    settings.manifest_lock_path = duplicate_lock

    with pytest.raises(
        TrustedHostPromotionError,
        match="trusted-host promotion manifest authority is unavailable",
    ):
        with TestClient(app):
            pass


def test_trusted_host_promotion_authority_drift_is_terminal_without_placement(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text("bounded\n", encoding="utf-8")
    app = promotion_ready_app(settings)

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        descriptor = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(sandbox_id="sandbox-drift"),
            headers=headers,
        ).json()
        proposal = client.post(
            "/trusted-host-promotions/proposals",
            json={
                "workspace_id": "default",
                "sandbox_descriptor_id": descriptor["descriptor_id"],
                "sandbox_id": "sandbox-drift",
                "source_artifact_path": "summary.txt",
                "host_staging_label": "host-staging://artifact",
            },
            headers=headers,
        ).json()
        client.post(
            f"/approvals/{proposal['approval_id']}/approve",
            json={"decision": "approve"},
            headers=headers,
        )
        service = cast(TrustedHostPromotionService, app.state.trusted_host_promotion_service)
        assert service._manifest_authority_record is not None
        service._manifest_authority_record = service._manifest_authority_record.model_copy(
            update={"lock_digest": "sha256:" + ("f" * 64)}
        )
        apply = client.post(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
            json={"approval_id": proposal["approval_id"]},
            headers=headers,
        )
        current = client.get(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}",
            headers=headers,
        )

    assert apply.status_code == 409
    assert apply.json()["detail"] == "trusted-host promotion authority is stale"
    assert current.json()["status"] == "authority_stale"
    assert not settings.trusted_host_staging_root.exists()


def test_trusted_host_proposal_and_approval_insert_is_atomic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text("bounded\n", encoding="utf-8")
    app = promotion_ready_app(settings)

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        descriptor = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(sandbox_id="sandbox-atomic"),
            headers=headers,
        ).json()
        approval_service = cast(ApprovalService, app.state.approval_service)

        def fail_insert(*_args: Any, **_kwargs: Any) -> None:
            raise sqlite3.IntegrityError("simulated approval insert failure")

        monkeypatch.setattr(approval_service.store, "insert_on_connection", fail_insert)
        response = client.post(
            "/trusted-host-promotions/proposals",
            json={
                "workspace_id": "default",
                "sandbox_descriptor_id": descriptor["descriptor_id"],
                "sandbox_id": "sandbox-atomic",
                "source_artifact_path": "summary.txt",
                "host_staging_label": "host-staging://artifact",
            },
            headers=headers,
        )
        proposals = client.get("/trusted-host-promotions/proposals", headers=headers).json()
        approvals = client.get("/approvals", headers=headers).json()

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "trusted-host proposal approval evidence transaction failed"
    )
    assert proposals["promotion_proposals"] == []
    assert approvals["approvals"] == []


def test_trusted_host_approval_audit_failure_terminally_closes_pair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text("bounded\n", encoding="utf-8")
    app = promotion_ready_app(settings)

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        descriptor = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(sandbox_id="sandbox-audit-failure"),
            headers=headers,
        ).json()
        audit_writer = cast(AuditWriter, app.state.audit_writer)
        original_write_event = audit_writer.write_event

        def fail_created_event(**kwargs: Any) -> Any:
            if kwargs.get("event_type") == AuditEventType.APPROVAL_CREATED:
                raise RuntimeError("simulated approval-created audit failure")
            return original_write_event(**kwargs)

        monkeypatch.setattr(audit_writer, "write_event", fail_created_event)
        response = client.post(
            "/trusted-host-promotions/proposals",
            json={
                "workspace_id": "default",
                "sandbox_descriptor_id": descriptor["descriptor_id"],
                "sandbox_id": "sandbox-audit-failure",
                "source_artifact_path": "summary.txt",
                "host_staging_label": "host-staging://artifact",
            },
            headers=headers,
        )
        proposals = client.get("/trusted-host-promotions/proposals", headers=headers).json()
        approvals = client.get("/approvals", headers=headers).json()
        diagnostics = client.get(
            "/trusted-host-promotions/diagnostics",
            headers=headers,
        ).json()

    assert response.status_code == 400
    assert response.json()["detail"] == "approval_evidence_failed"
    assert proposals["promotion_proposals"][0]["status"] == "approval_evidence_failed"
    assert approvals["approvals"][0]["status"] == "superseded"
    assert diagnostics["status"] == "incomplete"
    assert diagnostics["conditions"] == ["incomplete"]
    assert diagnostics["recommendations"][0]["retry_available"] is False


@pytest.mark.parametrize("terminal_status", ["denied", "expired"])
def test_trusted_host_diagnostics_use_terminal_approval_outcome_as_gateway_truth(
    tmp_path: Path,
    terminal_status: str,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text("bounded\n", encoding="utf-8")
    app = promotion_ready_app(settings)

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        descriptor = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(sandbox_id=f"sandbox-{terminal_status}"),
            headers=headers,
        ).json()
        created = client.post(
            "/trusted-host-promotions/proposals",
            json={
                "workspace_id": "default",
                "sandbox_descriptor_id": descriptor["descriptor_id"],
                "sandbox_id": f"sandbox-{terminal_status}",
                "source_artifact_path": "summary.txt",
                "host_staging_label": "host-staging://artifact",
            },
            headers=headers,
        ).json()
        if terminal_status == "denied":
            decision = client.post(
                f"/approvals/{created['approval_id']}/deny",
                json={"decision": "deny"},
                headers=headers,
            )
            assert decision.status_code == 200
        else:
            with sqlite3.connect(settings.db_path) as connection:
                connection.execute(
                    "UPDATE approvals SET expires_at = ? WHERE approval_id = ?",
                    ("2000-01-01T00:00:00+00:00", created["approval_id"]),
                )
                connection.commit()
        proposal = client.get(
            f"/trusted-host-promotions/proposals/{created['promotion_proposal_id']}",
            headers=headers,
        )
        diagnostics = client.get("/trusted-host-promotions/diagnostics", headers=headers)

    assert proposal.status_code == 200
    review = proposal.json()
    assert review["status"] == "approval_required"
    assert review["effective_status"] == f"approval_{terminal_status}"
    assert review["approval_evidence_status"] == terminal_status
    assert review["approval_evidence"]["status"] == terminal_status
    if terminal_status == "denied":
        assert review["approval_evidence"]["approver_decision"]["decision_hash"].startswith(
            "sha256:"
        )
    else:
        assert review["approval_evidence"]["approver_decision"] is None
    payload = diagnostics.json()
    assert payload["status"] == "incomplete"
    assert payload["conditions"] == ["approval_terminal"]
    assert payload["recommendations"][0]["condition"] == "approval_terminal"
    assert payload["recommendations"][0]["retry_available"] is False
    assert payload["recommendations"][0]["automatic_repair_available"] is False
    assert "summary.txt" not in diagnostics.text


def test_trusted_host_diagnostics_report_legacy_proposals_without_raw_source_labels(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    raw_source_label = "department/records/summary.txt"
    source = settings.workspace_root / raw_source_label
    source.parent.mkdir(parents=True)
    source.write_text("bounded\n", encoding="utf-8")
    app = promotion_ready_app(settings)

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        descriptor = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(sandbox_id="sandbox-legacy-diagnostics"),
            headers=headers,
        ).json()
        created = client.post(
            "/trusted-host-promotions/proposals",
            json={
                "workspace_id": "default",
                "sandbox_descriptor_id": descriptor["descriptor_id"],
                "sandbox_id": "sandbox-legacy-diagnostics",
                "source_artifact_path": raw_source_label,
                "host_staging_label": "host-staging://artifact",
            },
            headers=headers,
        ).json()
        with sqlite3.connect(settings.db_path) as connection:
            connection.execute(
                """
                UPDATE trusted_host_promotion_proposals
                SET status = 'legacy_unbound', authority_schema_version = NULL,
                    authority_snapshot_json = NULL, authority_snapshot_hash = NULL,
                    requester_principal_id = NULL, requester_principal_generation = NULL,
                    executor_principal_id = NULL, executor_principal_generation = NULL
                WHERE proposal_id = ?
                """,
                (created["promotion_proposal_id"],),
            )
            connection.commit()
        diagnostics = client.get("/trusted-host-promotions/diagnostics", headers=headers)

    assert diagnostics.status_code == 200
    payload = diagnostics.json()
    assert payload["status"] == "legacy"
    assert payload["conditions"] == ["legacy"]
    assert payload["proposals"][0]["status"] == "legacy_unbound"
    assert payload["proposals"][0]["authority_evidence"]["status"] == "legacy_unbound"
    assert payload["recommendations"][0]["retry_available"] is False
    assert raw_source_label not in diagnostics.text


def test_trusted_host_diagnostics_never_hide_legacy_recovery_evidence(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text("bounded\n", encoding="utf-8")
    app = promotion_ready_app(settings)

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        descriptor = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(sandbox_id="sandbox-legacy-recovery"),
            headers=headers,
        ).json()
        created = client.post(
            "/trusted-host-promotions/proposals",
            json={
                "workspace_id": "default",
                "sandbox_descriptor_id": descriptor["descriptor_id"],
                "sandbox_id": "sandbox-legacy-recovery",
                "source_artifact_path": "summary.txt",
                "host_staging_label": "host-staging://artifact",
            },
            headers=headers,
        ).json()
        with sqlite3.connect(settings.db_path) as connection:
            connection.execute(
                """
                UPDATE trusted_host_promotion_proposals
                SET status = 'legacy_failed', authority_schema_version = NULL,
                    authority_snapshot_json = NULL, authority_snapshot_hash = NULL,
                    requester_principal_id = NULL, requester_principal_generation = NULL,
                    executor_principal_id = NULL, executor_principal_generation = NULL
                WHERE proposal_id = ?
                """,
                (created["promotion_proposal_id"],),
            )
            connection.execute(
                """
                INSERT INTO trusted_host_promotion_attempts (
                    attempt_id, approval_id, proposal_id, request_id, workspace_id,
                    host_staging_label, artifact_sha256, staged_sha256, status,
                    failure_reason, created_at, updated_at, metadata_json,
                    record_version, authority_snapshot_hash, executor_principal_id,
                    executor_principal_generation
                ) VALUES (?, ?, ?, ?, 'default', 'host-staging://artifact', ?, ?,
                    'legacy_recovery_required', 'legacy_recovery_evidence', ?, ?, '{}',
                    '1', NULL, NULL, NULL)
                """,
                (
                    "thpa_legacy_recovery",
                    created["approval_id"],
                    created["promotion_proposal_id"],
                    created["request_id"],
                    created["artifact_sha256"],
                    created["artifact_sha256"],
                    created["created_at"],
                    created["updated_at"],
                ),
            )
            connection.commit()
        diagnostics = client.get("/trusted-host-promotions/diagnostics", headers=headers)

    assert diagnostics.status_code == 200
    payload = diagnostics.json()
    assert payload["status"] == "recovery_required"
    assert payload["conditions"] == ["recovery_required", "legacy", "incomplete"]
    assert payload["proposals"][0]["status"] == "legacy_failed"
    assert payload["attempts"][0]["status"] == "legacy_recovery_required"
    assert payload["recommendations"][0]["condition"] == "recovery_required"
    assert all(
        recommendation["retry_available"] is False
        and recommendation["automatic_repair_available"] is False
        for recommendation in payload["recommendations"]
    )
    assert "summary.txt" not in diagnostics.text


@pytest.mark.parametrize(
    "malformed_snapshot",
    ["{}", "{", "[]", "private-authority-material"],
)
def test_trusted_host_diagnostics_fail_safe_for_malformed_authority_evidence(
    tmp_path: Path,
    malformed_snapshot: str,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text("bounded\n", encoding="utf-8")
    app = promotion_ready_app(settings)

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        descriptor = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(sandbox_id="sandbox-malformed-authority"),
            headers=headers,
        ).json()
        created = client.post(
            "/trusted-host-promotions/proposals",
            json={
                "workspace_id": "default",
                "sandbox_descriptor_id": descriptor["descriptor_id"],
                "sandbox_id": "sandbox-malformed-authority",
                "source_artifact_path": "summary.txt",
                "host_staging_label": "host-staging://artifact",
            },
            headers=headers,
        ).json()
        with sqlite3.connect(settings.db_path) as connection:
            connection.execute(
                """
                UPDATE trusted_host_promotion_proposals
                SET authority_snapshot_json = ?
                WHERE proposal_id = ?
                """,
                (malformed_snapshot, created["promotion_proposal_id"]),
            )
            connection.commit()
        diagnostics = client.get("/trusted-host-promotions/diagnostics", headers=headers)

    assert diagnostics.status_code == 200
    payload = diagnostics.json()
    assert payload["status"] == "stale"
    assert payload["conditions"] == ["stale"]
    assert payload["proposals"][0]["authority_evidence"]["status"] == "invalid"
    assert payload["recommendations"][0]["automatic_repair_available"] is False
    assert "Traceback" not in diagnostics.text
    assert "private-authority-material" not in diagnostics.text


def test_trusted_host_promotion_is_fail_closed_until_binding_is_complete(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    settings.workspace_root.joinpath("summary.txt").write_text("bounded\n", encoding="utf-8")

    with TestClient(create_app(settings)) as client:
        headers = {"Authorization": "Bearer correct-token"}
        descriptor = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(sandbox_id="sandbox-disabled"),
            headers=headers,
        ).json()
        response = client.post(
            "/trusted-host-promotions/proposals",
            json={
                "workspace_id": "default",
                "sandbox_descriptor_id": descriptor["descriptor_id"],
                "sandbox_id": "sandbox-disabled",
                "source_artifact_path": "summary.txt",
                "host_staging_label": "host-staging://artifact",
                "artifact_media_label": "text/plain",
                "operator_note_label": "reviewed-output",
            },
            headers=headers,
        )
        proposals = client.get("/trusted-host-promotions/proposals", headers=headers).json()
        approvals = client.get("/approvals", headers=headers).json()
        diagnostics = client.get("/trusted-host-promotions/diagnostics", headers=headers).json()
        audit_events = client.get("/audit-events", headers=headers).json()["audit_events"]

    assert response.status_code == 400
    assert response.json()["detail"] == "governance_binding_incomplete"
    assert proposals["promotion_proposals"] == []
    assert approvals["approvals"] == []
    assert diagnostics["availability"] == "governance_binding_incomplete"
    assert not any(
        event.get("tool_name") == "trusted_host.promotion.stage"
        and event.get("event_type") == "tool.execution.completed"
        for event in audit_events
    )
    assert not settings.trusted_host_staging_root.exists()


def test_legacy_caller_attribution_fields_are_rejected(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.workspace_root.joinpath("summary.txt").write_text("bounded\n", encoding="utf-8")
    app = promotion_ready_app(settings)

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        descriptor = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(sandbox_id="sandbox-legacy-input"),
            headers=headers,
        ).json()
        legacy_proposal = client.post(
            "/trusted-host-promotions/proposals",
            json={
                "workspace_id": "default",
                "sandbox_descriptor_id": descriptor["descriptor_id"],
                "sandbox_id": "sandbox-legacy-input",
                "source_artifact_path": "summary.txt",
                "host_staging_label": "host-staging://artifact",
                "principal": {"id": "caller:spoofed"},
            },
            headers=headers,
        )
        created = client.post(
            "/approvals",
            json={
                "principal": {"id": "agent:local-dev"},
                "tool_name": "fs.apply_patch",
                "resource": {"path": "README.md"},
                "summary": "Modify README",
                "one_time_scope": {"tool_name": "fs.apply_patch"},
            },
            headers=headers,
        ).json()
        legacy_decision = client.post(
            f"/approvals/{created['approval_id']}/approve",
            json={"decision": "approve", "decided_by": "caller:spoofed"},
            headers=headers,
        )
        current = client.get(
            f"/approvals/{created['approval_id']}",
            headers=headers,
        ).json()

    assert legacy_proposal.status_code == 400
    assert legacy_proposal.json()["detail"] == "invalid trusted-host promotion proposal"
    assert legacy_decision.status_code == 422
    assert current["status"] == "pending"
    assert current["deciding_principal_id"] is None


def test_trusted_host_promotion_denies_stale_and_unsafe_inputs(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    artifact = settings.workspace_root / "summary.txt"
    artifact.write_text("original\n", encoding="utf-8")
    app = promotion_ready_app(settings)

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
                "host_staging_label": "host-staging://artifact",
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
                "host_staging_label": "host-staging://artifact",
            },
            headers={"Authorization": "Bearer correct-token"},
        ).json()
        approval_id = proposal["approval_id"]
        approve = client.post(
            f"/approvals/{approval_id}/approve",
            json={"decision": "approve"},
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
    assert stale_apply.json()["detail"] == (
        "trusted-host promotion placement is not production-ready"
    )
    assert "original" not in stale_apply.text
    assert "changed" not in stale_apply.text
    assert settings.trusted_host_staging_root.exists() is False
    assert diagnostics.status_code == 200
    assert diagnostics.json()["status"] == "clean"
    assert diagnostics.json()["attempts"] == []


def test_trusted_host_promotion_rejects_unbound_approval_and_all_placement(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    (settings.workspace_root / "summary.txt").write_text("bounded output\n", encoding="utf-8")
    app = promotion_ready_app(settings)

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        descriptor = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(sandbox_id="sandbox-demo"),
            headers=headers,
        ).json()

        def create_proposal(host_staging_label: str) -> dict[str, Any]:
            response = client.post(
                "/trusted-host-promotions/proposals",
                json={
                    "workspace_id": "default",
                    "sandbox_descriptor_id": descriptor["descriptor_id"],
                    "sandbox_id": "sandbox-demo",
                    "source_artifact_path": "summary.txt",
                    "host_staging_label": host_staging_label,
                },
                headers=headers,
            )
            assert response.status_code == 200
            return cast(dict[str, Any], response.json())

        first = create_proposal("host-staging://artifact")
        second = create_proposal("host-staging://artifact")
        first_approval = client.get(
            f"/approvals/{first['approval_id']}",
            headers=headers,
        ).json()
        duplicate_approval_response = client.post(
            "/approvals",
            headers=headers,
            json={
                "principal": first_approval["principal"],
                "tool_name": first_approval["tool_name"],
                "resource": first_approval["resource"],
                "summary": first_approval["summary"],
                "one_time_scope": first_approval["one_time_scope"],
                "request_id": first_approval["request_id"],
                "request_hash": first_approval["request_hash"],
                "expires_at": first_approval["expires_at"],
                "metadata": first_approval["metadata"],
            },
        )
        for approval_id in [first["approval_id"], second["approval_id"]]:
            approve = client.post(
                f"/approvals/{approval_id}/approve",
                json={"decision": "approve"},
                headers=headers,
            )
            assert approve.status_code == 200
        mismatched = client.post(
            f"/trusted-host-promotions/proposals/{second['promotion_proposal_id']}/apply",
            json={"approval_id": first["approval_id"]},
            headers=headers,
        )
        first_apply = client.post(
            f"/trusted-host-promotions/proposals/{first['promotion_proposal_id']}/apply",
            json={"approval_id": first["approval_id"]},
            headers=headers,
        )
        second_apply = client.post(
            f"/trusted-host-promotions/proposals/{second['promotion_proposal_id']}/apply",
            json={"approval_id": second["approval_id"]},
            headers=headers,
        )
        diagnostics = client.get("/trusted-host-promotions/diagnostics", headers=headers)

    assert duplicate_approval_response.status_code == 400
    assert duplicate_approval_response.json()["detail"] == (
        "trusted-host approvals must originate from a bound proposal"
    )
    assert mismatched.status_code == 409
    assert mismatched.json()["detail"] == ("trusted-host promotion approval binding review failed")
    for response in [first_apply, second_apply]:
        assert response.status_code == 409
        assert response.json()["detail"] == (
            "trusted-host promotion placement is not production-ready"
        )
    assert not settings.trusted_host_staging_root.exists()
    assert diagnostics.status_code == 200
    assert diagnostics.json()["status"] == "clean"
    assert diagnostics.json()["attempts"] == []


def test_trusted_host_promotion_rejects_unsafe_source_object_types(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    source = settings.workspace_root / "summary.txt"
    source.write_text("bounded output\n", encoding="utf-8")
    (settings.workspace_root / "linked.txt").symlink_to(source)
    os.link(source, settings.workspace_root / "hardlinked.txt")
    (settings.workspace_root / "directory.txt").mkdir()
    app = promotion_ready_app(settings)

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        descriptor = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(sandbox_id="sandbox-demo"),
            headers=headers,
        ).json()

        responses = []
        for source_artifact_path in ["linked.txt", "hardlinked.txt", "directory.txt"]:
            responses.append(
                client.post(
                    "/trusted-host-promotions/proposals",
                    json={
                        "workspace_id": "default",
                        "sandbox_descriptor_id": descriptor["descriptor_id"],
                        "sandbox_id": "sandbox-demo",
                        "source_artifact_path": source_artifact_path,
                        "host_staging_label": "host-staging://artifact",
                    },
                    headers=headers,
                )
            )

    assert [response.status_code for response in responses] == [400, 400, 400]
    assert all(
        response.json()["detail"] == "source artifact cannot be safely read"
        for response in responses
    )
    assert all("bounded output" not in response.text for response in responses)


def test_trusted_host_promotion_concurrent_apply_remains_disabled(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    (settings.workspace_root / "summary.txt").write_text(
        "bounded output\n",
        encoding="utf-8",
    )
    app = promotion_ready_app(settings)

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        descriptor = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(sandbox_id="sandbox-demo"),
            headers=headers,
        ).json()
        proposal = client.post(
            "/trusted-host-promotions/proposals",
            json={
                "workspace_id": "default",
                "sandbox_descriptor_id": descriptor["descriptor_id"],
                "sandbox_id": "sandbox-demo",
                "source_artifact_path": "summary.txt",
                "host_staging_label": "host-staging://artifact",
            },
            headers=headers,
        ).json()
        approval_id = proposal["approval_id"]
        approve = client.post(
            f"/approvals/{approval_id}/approve",
            json={"decision": "approve"},
            headers=headers,
        )

        def apply_once() -> tuple[int, dict[str, Any]]:
            response = client.post(
                f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
                json={"approval_id": approval_id},
                headers=headers,
            )
            return response.status_code, cast(dict[str, Any], response.json())

        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(lambda _: apply_once(), range(2)))
        diagnostics = client.get("/trusted-host-promotions/diagnostics", headers=headers)

    assert approve.status_code == 200
    assert [status_code for status_code, _ in responses] == [409, 409]
    assert all(
        payload["detail"] == "trusted-host promotion placement is not production-ready"
        for _, payload in responses
    )
    assert not settings.trusted_host_staging_root.exists()
    assert diagnostics.status_code == 200
    assert diagnostics.json()["status"] == "clean"
    assert diagnostics.json()["attempts"] == []


def test_trusted_host_promotion_preserves_existing_destination(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    (settings.workspace_root / "summary.txt").write_text(
        "new output\n",
        encoding="utf-8",
    )
    app = promotion_ready_app(settings)

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        descriptor = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(sandbox_id="sandbox-demo"),
            headers=headers,
        ).json()
        proposal = client.post(
            "/trusted-host-promotions/proposals",
            json={
                "workspace_id": "default",
                "sandbox_descriptor_id": descriptor["descriptor_id"],
                "sandbox_id": "sandbox-demo",
                "source_artifact_path": "summary.txt",
                "host_staging_label": "host-staging://artifact",
            },
            headers=headers,
        ).json()
        approval_id = proposal["approval_id"]
        approve = client.post(
            f"/approvals/{approval_id}/approve",
            json={"decision": "approve"},
            headers=headers,
        )
        attempt_id = (
            "thpa_"
            + hashlib.sha256(proposal["promotion_proposal_id"].encode("utf-8")).hexdigest()[:32]
        )
        destination = (
            settings.trusted_host_staging_root
            / "default"
            / proposal["promotion_proposal_id"]
            / f"{attempt_id}-artifact.artifact"
        )
        destination.parent.mkdir(parents=True)
        destination.write_text("existing output\n", encoding="utf-8")
        apply_response = client.post(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
            json={"approval_id": approval_id},
            headers=headers,
        )
        diagnostics = client.get("/trusted-host-promotions/diagnostics", headers=headers)

    assert approve.status_code == 200
    assert apply_response.status_code == 409
    assert apply_response.json()["detail"] == (
        "trusted-host promotion placement is not production-ready"
    )
    assert destination.read_text(encoding="utf-8") == "existing output\n"
    assert diagnostics.status_code == 200
    assert diagnostics.json()["status"] == "clean"
    assert diagnostics.json()["attempts"] == []


def test_trusted_host_promotion_audit_failure_leaves_completion_pending(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = make_settings(tmp_path, token="correct-token")
    settings.workspace_root.mkdir()
    settings.trusted_host_staging_root = tmp_path / "trusted-host-staging"
    settings.trusted_host_staging_root.mkdir(mode=0o700)
    (settings.workspace_root / "summary.txt").write_text(
        "bounded output\n",
        encoding="utf-8",
    )
    app = promotion_ready_app(settings, placement_ready=True)

    with TestClient(app) as client:
        headers = {"Authorization": "Bearer correct-token"}
        descriptor = client.post(
            "/sandbox-descriptors",
            json=sandbox_descriptor_payload(sandbox_id="sandbox-demo"),
            headers=headers,
        ).json()
        proposal = client.post(
            "/trusted-host-promotions/proposals",
            json={
                "workspace_id": "default",
                "sandbox_descriptor_id": descriptor["descriptor_id"],
                "sandbox_id": "sandbox-demo",
                "source_artifact_path": "summary.txt",
                "host_staging_label": "host-staging://artifact",
            },
            headers=headers,
        ).json()
        approval_id = proposal["approval_id"]
        approve = client.post(
            f"/approvals/{approval_id}/approve",
            json={"decision": "approve"},
            headers=headers,
        )
        audit_writer = cast(AuditWriter, app.state.audit_writer)
        original_write_event = audit_writer.write_event

        def fail_completion_event(**kwargs: Any) -> Any:
            if kwargs.get("event_type") == AuditEventType.TOOL_EXECUTION_COMPLETED:
                raise RuntimeError("simulated promotion completion audit failure")
            return original_write_event(**kwargs)

        monkeypatch.setattr(audit_writer, "write_event", fail_completion_event)
        apply_response = client.post(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
            json={"approval_id": approval_id},
            headers=headers,
        )
        monkeypatch.setattr(audit_writer, "write_event", original_write_event)
        diagnostics = client.get("/trusted-host-promotions/diagnostics", headers=headers)
        proposal_response = client.get(
            f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}",
            headers=headers,
        )
        approval_response = client.get(f"/approvals/{approval_id}", headers=headers)
        audit_response = client.get(
            "/audit-events?tool_name=trusted_host.promotion.stage",
            headers=headers,
        )

    assert approve.status_code == 200
    assert apply_response.status_code == 409
    assert apply_response.json()["detail"] == "completion_evidence_incomplete"
    assert diagnostics.status_code == 200
    assert diagnostics.json()["status"] == "incomplete"
    assert diagnostics.json()["conditions"] == ["incomplete"]
    assert diagnostics.json()["attempts"][0]["status"] == "staged"
    assert diagnostics.json()["recommendations"][0]["retry_available"] is False
    assert proposal_response.status_code == 200
    assert proposal_response.json()["status"] == "completion_evidence_pending"
    assert approval_response.json()["status"] == "executed"
    assert "tool.execution.completed" not in {
        event["event_type"] for event in audit_response.json()["audit_events"]
    }
    destination_dir = (
        settings.trusted_host_staging_root / "default" / proposal["promotion_proposal_id"]
    )
    assert len(list(destination_dir.iterdir())) == 1


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


def test_agent_run_rejects_conflicting_authority_provenance(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    initialize_database(db_path)
    store = AgentRunStore(db_path)
    store.initialize()
    principal: JsonObject = {
        "id": "agent:node.node_authoritative",
        "type": "agent",
        "roles": ["AgentReadOnly"],
    }
    provenance: JsonObject = {
        "ingress_kind": "node_governed_access",
        "identity_source": "gateway_derived_node",
        "node_id": "node_authoritative",
        "offline_fallback_allowed": False,
        "runner_enforcement_proven": False,
    }

    _run, created = store.ensure_for_tool_call(
        principal=principal,
        session_id="node:node_authoritative:cfg:1:sha256:configuration:runner",
        workspace_id="default",
        request_id="req_first",
        tool_name="fs.read",
        policy_hash="sha256:" + ("1" * 64),
        tool_manifest_hash="sha256:" + ("2" * 64),
        run_metadata=provenance,
    )
    assert created is True

    with pytest.raises(AgentRunError, match="authority provenance conflicts"):
        store.ensure_for_tool_call(
            principal=principal,
            session_id="node:node_authoritative:cfg:1:sha256:configuration:runner",
            workspace_id="default",
            request_id="req_conflict",
            tool_name="fs.read",
            policy_hash="sha256:" + ("1" * 64),
            tool_manifest_hash="sha256:" + ("2" * 64),
            run_metadata={**provenance, "node_id": "node_conflicting"},
        )

    [persisted] = store.list_runs()
    assert persisted["last_request_id"] == "req_first"
    assert persisted["tool_call_count"] == 1
    persisted_metadata = persisted["metadata"]
    assert isinstance(persisted_metadata, dict)
    assert persisted_metadata["node_id"] == "node_authoritative"


def test_mission_agent_run_query_is_not_limited_to_latest_global_200(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "ithildin.sqlite3"
    initialize_database(db_path)
    store = AgentRunStore(db_path)
    store.initialize()
    mission_id = "mission_" + ("a" * 32)
    mission_run, _created = store.ensure_for_tool_call(
        principal={"id": "agent:mission-node", "type": "agent", "roles": []},
        session_id="mission-oldest",
        workspace_id="default",
        request_id="req_mission_oldest",
        tool_name="project.structure.summary",
        policy_hash=None,
        tool_manifest_hash=None,
        run_metadata={"mission_id": mission_id},
    )
    for index in range(205):
        store.ensure_for_tool_call(
            principal={"id": "agent:other", "type": "agent", "roles": []},
            session_id=f"unrelated-{index}",
            workspace_id="default",
            request_id=f"req_unrelated_{index}",
            tool_name="project.structure.summary",
            policy_hash=None,
            tool_manifest_hash=None,
        )

    assert [run["run_id"] for run in store.mission_candidates(mission_id)] == [mission_run.run_id]


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
        origin.startswith(("http://127.0.0.1:", "http://localhost:")) for origin in allow_origins
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
            json={"decision": "approve"},
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
            json={"decision": "deny", "reason": "not now"},
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
            json={"decision": "deny"},
        )
        deny_mismatch = client.post(
            f"/approvals/{approval_id}/deny",
            headers={"Authorization": "Bearer correct-token"},
            json={"decision": "approve"},
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
            json={"decision": "approve"},
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
            json={"decision": "approve"},
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
        approval_service.approve(approval.approval_id, context=ADMIN_CONTEXT)
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
    assert payload["lifecycle"]["sqlite_jsonl_payload_bytes_match"] is True
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


def test_audit_export_fails_closed_when_sqlite_payload_diverges_from_jsonl(
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

    assert export_response.status_code == 409
    assert export_response.json()["detail"] == "audit lifecycle recovery is required"


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
            """
            SELECT key, value FROM app_metadata
            WHERE key IN ('schema_version', 'minimum_writer_version')
            ORDER BY key
            """
        ).fetchall()

    assert rows == [("minimum_writer_version", "4"), ("schema_version", "4")]


@pytest.mark.parametrize(
    ("unavailable_prerequisite", "expected_detail"),
    [
        ("configuration_signer", "Node configuration signing trust root is unavailable"),
        ("manifest_lock", "manifest lock is unavailable for Node enrollment"),
    ],
)
def test_node_enrollment_code_issuance_fails_closed_before_secret_or_audit_success(
    tmp_path: Path,
    unavailable_prerequisite: str,
    expected_detail: str,
) -> None:
    settings = make_settings(tmp_path)
    api = create_app(settings)
    with TestClient(api) as client:
        if unavailable_prerequisite == "configuration_signer":
            api.state.node_configuration_signer = None
        else:
            settings.manifest_lock_path.unlink()

        response = client.post(
            "/nodes/enrollment-codes",
            headers={"Authorization": f"Bearer {settings.admin_token}"},
            json={"workspace_id": "default", "display_name": "Fail Closed Node"},
        )

    assert response.status_code == 503
    assert response.json() == {"detail": expected_detail}
    assert "enrollment_code" not in response.text
    with sqlite3.connect(settings.db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM node_enrollment_codes").fetchone() == (0,)
    audit_text = (
        settings.audit_log_path.read_text(encoding="utf-8")
        if settings.audit_log_path.exists()
        else ""
    )
    assert "node.enrollment_code.issued" not in audit_text


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
        assert accepted.json()["last_observed_node_version"] == "0.1.0"
        assert accepted.json()["version_posture"] == "unassigned"
        assert accepted.json()["maintenance_control_source"] == "operator_managed"
        assert accepted.json()["self_update_allowed"] is False
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
        assert inventory.json()["nodes"][0]["version_posture"] == "unassigned"
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


def test_node_identity_key_rotation_api_retires_old_key_and_reports_posture(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path)
    admin_headers = {"Authorization": "Bearer test-admin-token"}
    current_private = Ed25519PrivateKey.generate()
    current_public = base64.b64encode(current_private.public_key().public_bytes_raw()).decode()
    api = create_app(settings)
    with TestClient(api) as client:
        issued = client.post(
            "/nodes/enrollment-codes",
            headers=admin_headers,
            json={"workspace_id": "default", "display_name": "Rotating Node"},
        )
        enrollment = client.post(
            "/nodes/enroll",
            json={
                "enrollment_code": issued.json()["enrollment_code"],
                "public_key": current_public,
                "protocol_version": "1",
                "node_version": "0.1.0",
                "runner_adapter": "hermes",
                "deployment_topology": "docker_sidecar",
            },
        )
        assert enrollment.status_code == 200
        node_id = enrollment.json()["node_id"]
        challenge_path = f"/nodes/{node_id}/identity-key-rotation/challenges"
        challenge_payload: JsonObject = {"protocol_version": "1"}
        challenge = client.post(
            challenge_path,
            headers=_signed_node_headers(
                current_private,
                node_id=node_id,
                path=challenge_path,
                payload=challenge_payload,
                nonce="a1" * 16,
            ),
            json=challenge_payload,
        )
        assert challenge.status_code == 200
        challenge_document = challenge.json()
        assert challenge_document["evidence_status"] == "complete"
        next_private = Ed25519PrivateKey.generate()
        next_public = base64.b64encode(next_private.public_key().public_bytes_raw()).decode()
        next_key_id = node_identity_key_id(next_public)
        rotation = NodeIdentityRotationRecord(
            rotation_id=challenge_document["rotation_id"],
            node_id=node_id,
            principal_id=enrollment.json()["principal_id"],
            workspace_id="default",
            current_key_id=challenge_document["current_key_id"],
            challenge_digest=sha256_digest(challenge_document["challenge"]),
            created_at=challenge_document["created_at"],
            expires_at=challenge_document["expires_at"],
            status="pending",
            evidence_status="complete",
            next_key_id=None,
            activated_at=None,
        )
        proof = canonical_identity_rotation_proof_message(
            rotation=rotation, next_key_id=next_key_id
        )
        activation_path = f"/nodes/{node_id}/identity-key-rotation/activations"
        activation_payload: JsonObject = {
            "protocol_version": "1",
            "rotation_id": rotation.rotation_id,
            "challenge": challenge_document["challenge"],
            "next_public_key": next_public,
            "next_key_proof": base64.b64encode(next_private.sign(proof)).decode(),
        }
        activated = client.post(
            activation_path,
            headers=_signed_node_headers(
                current_private,
                node_id=node_id,
                path=activation_path,
                payload=activation_payload,
                nonce="a2" * 16,
            ),
            json=activation_payload,
        )
        assert activated.status_code == 200
        assert activated.json()["active_identity_key_id"] == next_key_id
        assert activated.json()["retired_key_request_authority"] is False

        status_path = f"/nodes/{node_id}/identity-key-rotation/status"
        status_payload: JsonObject = {
            "protocol_version": "1",
            "rotation_id": rotation.rotation_id,
        }
        old_key_status = client.post(
            status_path,
            headers=_signed_node_headers(
                current_private,
                node_id=node_id,
                path=status_path,
                payload=status_payload,
                nonce="a3" * 16,
            ),
            json=status_payload,
        )
        assert old_key_status.status_code == 401
        new_key_status = client.post(
            status_path,
            headers=_signed_node_headers(
                next_private,
                node_id=node_id,
                path=status_path,
                payload=status_payload,
                nonce="a4" * 16,
            ),
            json=status_payload,
        )
        assert new_key_status.status_code == 200
        detail = client.get(f"/nodes/{node_id}", headers=admin_headers)
        assert detail.json()["active_identity_key_id"] == next_key_id
        assert detail.json()["identity_key_rotation"]["status"] == "activated"

        second_challenge = client.post(
            challenge_path,
            headers=_signed_node_headers(
                next_private,
                node_id=node_id,
                path=challenge_path,
                payload=challenge_payload,
                nonce="a5" * 16,
            ),
            json=challenge_payload,
        ).json()
        third_private = Ed25519PrivateKey.generate()
        third_public = base64.b64encode(third_private.public_key().public_bytes_raw()).decode()
        second_rotation = NodeIdentityRotationRecord(
            rotation_id=second_challenge["rotation_id"],
            node_id=node_id,
            principal_id=enrollment.json()["principal_id"],
            workspace_id="default",
            current_key_id=next_key_id,
            challenge_digest=sha256_digest(second_challenge["challenge"]),
            created_at=second_challenge["created_at"],
            expires_at=second_challenge["expires_at"],
            status="pending",
            evidence_status="complete",
            next_key_id=None,
            activated_at=None,
        )
        third_key_id = node_identity_key_id(third_public)
        second_proof = canonical_identity_rotation_proof_message(
            rotation=second_rotation, next_key_id=third_key_id
        )
        second_activation_payload: JsonObject = {
            "protocol_version": "1",
            "rotation_id": second_rotation.rotation_id,
            "challenge": second_challenge["challenge"],
            "next_public_key": third_public,
            "next_key_proof": base64.b64encode(third_private.sign(second_proof)).decode(),
        }

        class FailingIdentityRotationAuditWriter:
            def write_event(self, **_: object) -> None:
                raise RuntimeError("simulated identity rotation audit failure")

        api.state.audit_writer = FailingIdentityRotationAuditWriter()
        with pytest.raises(RuntimeError, match="simulated identity rotation audit failure"):
            client.post(
                activation_path,
                headers=_signed_node_headers(
                    next_private,
                    node_id=node_id,
                    path=activation_path,
                    payload=second_activation_payload,
                    nonce="a6" * 16,
                ),
                json=second_activation_payload,
            )
        failed_store = NodeStore(settings.db_path)
        compensated_node = failed_store.get(node_id)
        assert compensated_node.evidence_status == "complete"
        assert node_identity_key_id(compensated_node.public_key) == next_key_id
        failed_rotation = failed_store.latest_identity_rotation(node_id)
        assert failed_rotation is not None
        assert failed_rotation.status == "audit_failed"
        assert failed_rotation.evidence_status == "complete"

    audit_text = settings.audit_log_path.read_text(encoding="utf-8")
    assert "node.identity_key_rotation.challenge_issued" in audit_text
    assert "node.identity_key.rotated" in audit_text
    assert challenge_document["challenge"] not in audit_text
    assert next_public not in audit_text


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
        assert inventory.json()["minimum_node_version"] == "0.2.0"
        assert inventory.json()["version_posture"] == "never_observed"

        heartbeat_payload: JsonObject = {
            "protocol_version": "1",
            "node_version": "0.1.0",
            "runner_adapter": "hermes",
            "deployment_topology": "docker_sidecar",
            "configuration_digest": retrieved.json()["configuration_digest"],
        }
        heartbeat_path = f"/nodes/{node_id}/heartbeat"
        heartbeat_response = client.post(
            heartbeat_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=heartbeat_path,
                payload=heartbeat_payload,
                nonce="c" * 32,
            ),
            json=heartbeat_payload,
        )
        assert heartbeat_response.status_code == 200
        assert heartbeat_response.json()["last_observed_node_version"] == "0.1.0"
        assert heartbeat_response.json()["minimum_node_version"] == "0.2.0"
        assert heartbeat_response.json()["version_posture"] == "below_minimum"

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


def test_node_governed_read_uses_derived_identity_workspace_and_durable_replay(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path)
    write_manifest(settings.manifest_dir, name="fs.read", risk="read", required=["path"])
    write_manifest(settings.manifest_dir, name="http.fetch", risk="network", required=["url"])
    settings.workspace_root.mkdir(parents=True)
    settings.workspace_root.joinpath("README.md").write_text(
        "governed Node read\n", encoding="utf-8"
    )
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    private_key = Ed25519PrivateKey.generate()
    public_key = base64.b64encode(private_key.public_key().public_bytes_raw()).decode()
    successful_payload: JsonObject
    successful_headers: dict[str, str]
    node_id: str

    with TestClient(create_app(settings)) as client:
        issued = client.post(
            "/nodes/enrollment-codes",
            headers=admin_headers,
            json={"workspace_id": "default", "display_name": "Governed Read Node"},
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
        assigned = client.post(
            f"/nodes/{node_id}/configurations",
            headers=admin_headers,
            json={"minimum_node_version": "0.1.0"},
        )
        assert assigned.status_code == 200
        configuration_request: JsonObject = {"protocol_version": "1", "known_generation": 0}
        configuration_path = f"/nodes/{node_id}/configuration"
        configuration = client.post(
            configuration_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=configuration_path,
                payload=configuration_request,
                nonce="d1" * 16,
            ),
            json=configuration_request,
        )
        assert configuration.status_code == 200
        bundle = configuration.json()
        acknowledgment: JsonObject = {
            "protocol_version": "1",
            "generation": bundle["generation"],
            "configuration_digest": bundle["configuration_digest"],
            "configuration_signing_key_id": bundle["signature"]["key_id"],
            "active_configuration_signing_key_id": bundle["signature"]["key_id"],
            "status": "stored_not_enforced",
        }
        acknowledgment_path = f"/nodes/{node_id}/configuration/acknowledgments"
        acknowledged = client.post(
            acknowledgment_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=acknowledgment_path,
                payload=acknowledgment,
                nonce="d2" * 16,
            ),
            json=acknowledgment,
        )
        assert acknowledged.status_code == 200
        heartbeat: JsonObject = {
            "protocol_version": "1",
            "node_version": "0.1.0",
            "runner_adapter": "hermes",
            "deployment_topology": "docker_sidecar",
            "configuration_digest": bundle["configuration_digest"],
        }
        heartbeat_path = f"/nodes/{node_id}/heartbeat"
        accepted = client.post(
            heartbeat_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=heartbeat_path,
                payload=heartbeat,
                nonce="d3" * 16,
            ),
            json=heartbeat,
        )
        assert accepted.status_code == 200

        inventory = client.get(f"/nodes/{node_id}", headers=admin_headers)
        assert inventory.status_code == 200
        governed_posture = inventory.json()["governed_access"]
        assert governed_posture["state"] == "ready_read_only"
        assert governed_posture["allowed_risks"] == ["read"]
        assert governed_posture["offline_fallback_allowed"] is False
        assert governed_posture["runner_enforcement_proven"] is False

        governed_path = f"/nodes/{node_id}/governed-tool-calls"
        successful_payload = {
            "protocol_version": "1",
            "configuration_generation": bundle["generation"],
            "configuration_digest": bundle["configuration_digest"],
            "node_version": "0.1.0",
            "session_id": "hermes-read-1",
            "tool_name": "fs.read",
            "arguments": {"path": "README.md"},
        }
        successful_headers = _signed_node_headers(
            private_key,
            node_id=node_id,
            path=governed_path,
            payload=successful_payload,
            nonce="d4" * 16,
        )
        governed = client.post(governed_path, headers=successful_headers, json=successful_payload)
        assert governed.status_code == 200
        assert governed.json()["status"] == "completed"
        assert governed.json()["identity_source"] == "gateway_derived_node"
        assert governed.json()["workspace_id"] == "default"
        assert governed.json()["content"]["content"] == "governed Node read\n"
        assert governed.json()["offline_fallback_used"] is False

        runs = client.get(
            "/runs",
            headers=admin_headers,
            params={"principal_id": f"agent:node.{node_id}"},
        )
        assert runs.status_code == 200
        [node_run] = runs.json()["runs"]
        assert node_run["metadata"] == {
            "authorization_profile": "agent:node-local-preview-readonly",
            "configuration_digest": bundle["configuration_digest"],
            "configuration_generation": bundle["generation"],
            "created_by": "governed_tool_call",
            "identity_source": "gateway_derived_node",
            "ingress_kind": "node_governed_access",
            "node_display_name": "Governed Read Node",
            "node_id": node_id,
            "offline_fallback_allowed": False,
            "runner_enforcement_proven": False,
        }
        run_evidence = client.get(
            f"/runs/{node_run['run_id']}/evidence-export",
            headers=admin_headers,
        )
        assert run_evidence.status_code == 200
        assert run_evidence.json()["run"]["origin"] == {
            key: node_run["metadata"][key]
            for key in (
                "authorization_profile",
                "configuration_digest",
                "configuration_generation",
                "identity_source",
                "ingress_kind",
                "node_display_name",
                "node_id",
                "offline_fallback_allowed",
                "runner_enforcement_proven",
            )
        }

        replay = client.post(governed_path, headers=successful_headers, json=successful_payload)
        assert replay.status_code == 401
        assert replay.json()["detail"] == "replayed Node nonce"

        cross_workspace: JsonObject = {
            **successful_payload,
            "arguments": {"path": "README.md", "workspace_id": "demo"},
        }
        cross_workspace_response = client.post(
            governed_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=governed_path,
                payload=cross_workspace,
                nonce="d5" * 16,
            ),
            json=cross_workspace,
        )
        assert cross_workspace_response.status_code == 200
        assert cross_workspace_response.json()["status"] == "denied"
        assert cross_workspace_response.json()["is_error"] is True

        network_request: JsonObject = {
            **successful_payload,
            "tool_name": "http.fetch",
            "arguments": {"url": "https://example.com"},
        }
        network_response = client.post(
            governed_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=governed_path,
                payload=network_request,
                nonce="d6" * 16,
            ),
            json=network_request,
        )
        assert network_response.status_code == 200
        assert network_response.json()["status"] == "denied"

    with TestClient(create_app(settings)) as restarted:
        replay_after_restart = restarted.post(
            f"/nodes/{node_id}/governed-tool-calls",
            headers=successful_headers,
            json=successful_payload,
        )
        assert replay_after_restart.status_code == 401
        assert replay_after_restart.json()["detail"] == "replayed Node nonce"
        verification = restarted.get("/audit-events/verify", headers=admin_headers)
        assert verification.status_code == 200
        assert verification.json()["valid"] is True

    audit_text = settings.audit_log_path.read_text(encoding="utf-8")
    assert f"agent:node.{node_id}" in audit_text
    assert "node:node_" in audit_text
    assert private_key.private_bytes_raw().hex() not in audit_text


def test_mission_admission_inventory_detail_and_queued_cancellation_api(
    tmp_path: Path,
) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    api = create_app(settings)
    with TestClient(api) as client:
        node_id = _ready_mission_node(client, settings, nonce_prefix="e")
        template_response = client.get("/mission-templates", headers=admin_headers)
        assert template_response.status_code == 200
        template_document = template_response.json()
        assert template_document["template_count"] == 1
        assert template_document["templates"][0]["payload_included"] is False
        assert "operations" not in template_response.text

        admission_payload = {
            "target_node_id": node_id,
            "mission_template_id": "synthetic_read_review_v1",
            "requested_timeout_seconds": 300,
            "client_request_id": "operator-mission-001",
        }
        unauthorized = client.post("/missions", json=admission_payload)
        assert unauthorized.status_code == 401
        assert client.get("/missions", headers=admin_headers).json()["count"] == 0
        duplicate = client.post(
            "/missions",
            headers={**admin_headers, "Content-Type": "application/json"},
            content=(
                f'{{"target_node_id":"{node_id}","target_node_id":"{node_id}",'
                '"mission_template_id":"synthetic_read_review_v1",'
                '"requested_timeout_seconds":300,"client_request_id":"duplicate"}'
            ),
        )
        assert duplicate.status_code == 400
        unknown_field = client.post(
            "/missions",
            headers=admin_headers,
            json={**admission_payload, "objective": "do something arbitrary"},
        )
        assert unknown_field.status_code == 400
        assert client.get("/missions", headers=admin_headers).json()["count"] == 0

        admitted = client.post("/missions", headers=admin_headers, json=admission_payload)
        assert admitted.status_code == 200
        admitted_document = admitted.json()
        assert admitted_document["lifecycle_state"] == "queued"
        assert admitted_document["lifecycle_revision"] == 1
        assert admitted_document["lifecycle_authority"] == "gateway"
        assert admitted_document["runner_state_authority"] == "runner_reported_only"
        assert admitted_document["model_provider_state_known"] is False
        assert "objective" not in admitted.text
        assert "operations" not in admitted.text
        mission_id = admitted_document["mission_id"]
        replay = client.post("/missions", headers=admin_headers, json=admission_payload)
        assert replay.status_code == 200
        assert replay.json()["mission_id"] == mission_id
        conflict = client.post(
            "/missions",
            headers=admin_headers,
            json={**admission_payload, "requested_timeout_seconds": 301},
        )
        assert conflict.status_code == 409

        inventory = client.get("/missions", headers=admin_headers)
        assert inventory.status_code == 200
        assert inventory.json()["count"] == 1
        assert inventory.json()["template_payloads_included"] is False
        detail = client.get(f"/missions/{mission_id}", headers=admin_headers)
        assert detail.status_code == 200
        detail_document = detail.json()
        assert {key: detail_document[key] for key in admitted_document} == admitted_document
        assert detail_document["delivery"] == {
            "authority": "gateway_node_claim",
            "state": "not_claimed",
            "claim": None,
        }
        assert detail_document["evidence"]["state"] == "complete"
        assert detail_document["runner_reports"] == {
            "authority": "runner_reported_through_authenticated_node",
            "latest": None,
            "receipts": [],
            "quarantined_count": 0,
            "report_conflict_count": 0,
        }
        assert detail_document["governed_agent_runs"]["count"] == 0
        assert detail_document["model_provider"] == {
            "state": "unknown",
            "authority": "external_runner_or_provider",
            "inference_known": False,
            "output_verified": False,
        }
        assert detail_document["attention_codes"] == []

        cancel_payload = {"client_request_id": "operator-cancel-001"}
        canceled = client.post(
            f"/missions/{mission_id}/cancel",
            headers=admin_headers,
            json=cancel_payload,
        )
        assert canceled.status_code == 200
        assert canceled.json()["lifecycle_state"] == "canceled"
        assert canceled.json()["cancellation_authority"] == "gateway_decision_only"
        assert canceled.json()["runner_stop_proven"] is False
        cancel_replay = client.post(
            f"/missions/{mission_id}/cancel",
            headers=admin_headers,
            json=cancel_payload,
        )
        assert cancel_replay.status_code == 200
        assert cancel_replay.json()["lifecycle_revision"] == 2
        with sqlite3.connect(settings.db_path) as connection:
            connection.execute(
                "UPDATE nodes SET status = 'revoked' WHERE node_id = ?",
                (node_id,),
            )
            connection.commit()
        replay_after_node_revocation = client.post(
            "/missions",
            headers=admin_headers,
            json=admission_payload,
        )
        assert replay_after_node_revocation.status_code == 200
        assert replay_after_node_revocation.json()["mission_id"] == mission_id
        assert replay_after_node_revocation.json()["lifecycle_state"] == "canceled"

    with TestClient(create_app(settings)) as restarted:
        restarted_inventory = restarted.get("/missions", headers=admin_headers)
        assert restarted_inventory.status_code == 200
        assert restarted_inventory.json()["count"] == 1
        restarted_detail = restarted.get(f"/missions/{mission_id}", headers=admin_headers)
        assert restarted_detail.status_code == 200
        assert restarted_detail.json()["lifecycle_state"] == "canceled"
        assert restarted_detail.json()["lifecycle_revision"] == 2

    with sqlite3.connect(settings.db_path) as connection:
        events = [
            json.loads(str(row[0]))
            for row in connection.execute(
                "SELECT payload_json FROM audit_events WHERE event_type IN (?, ?) ORDER BY rowid",
                (
                    AuditEventType.MISSION_ADMISSION_STAGED.value,
                    AuditEventType.MISSION_CANCELLATION_STAGED.value,
                ),
            )
        ]
        bindings = connection.execute(
            "SELECT owner_kind, owner_id, request_digest "
            "FROM mission_audit_evidence_bindings ORDER BY rowid"
        ).fetchall()
    assert [event["event_type"] for event in events] == [
        "mission.admission.staged",
        "mission.cancellation.staged",
    ]
    assert all(event["metadata"]["staged_proposal_only"] is True for event in events)
    assert all(event["metadata"]["evidence_status"] == "pending" for event in events)
    assert "operations" not in json.dumps(events)
    assert len(bindings) == 2
    assert all(binding[0] == "mission_transition" for binding in bindings)
    for event, binding in zip(events, bindings, strict=True):
        assert event["input_hash"] == binding[2]
        assert event["metadata"]["request_digest"] == binding[2]
        assert event["metadata"]["transition_id"] == binding[1]


def test_signed_node_claim_delivers_one_closed_envelope_and_denies_replay(
    tmp_path: Path,
) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    private_key = Ed25519PrivateKey.generate()
    claim_payload: JsonObject = {"protocol_version": "1"}
    api = create_app(settings)
    with TestClient(api) as client:
        node_id = _ready_mission_node(
            client,
            settings,
            nonce_prefix="7",
            node_private_key=private_key,
        )
        admitted = client.post(
            "/missions",
            headers=admin_headers,
            json={
                "target_node_id": node_id,
                "mission_template_id": "synthetic_read_review_v1",
                "requested_timeout_seconds": 300,
                "client_request_id": "claim-delivery-mission-001",
            },
        )
        assert admitted.status_code == 200
        mission_id = str(admitted.json()["mission_id"])
        claim_path = f"/nodes/{node_id}/mission-claims"
        unauthorized = client.post(claim_path, json=claim_payload)
        assert unauthorized.status_code == 401
        invalid = client.post(
            claim_path,
            headers={"X-Ithildin-Node": node_id},
            json={"protocol_version": "1", "mission_id": mission_id},
        )
        assert invalid.status_code == 400
        claim_headers = _signed_node_headers(
            private_key,
            node_id=node_id,
            path=claim_path,
            payload=claim_payload,
            nonce="74" * 16,
        )

        delivered = client.post(claim_path, headers=claim_headers, json=claim_payload)

        assert delivered.status_code == 200
        envelope = delivered.json()
        assert envelope["mission_id"] == mission_id
        assert envelope["gateway_lifecycle_state"] == "claimed"
        assert envelope["gateway_delivery_recorded"] is True
        assert envelope["claim_lifecycle_revision"] == 2
        assert envelope["runner_state_authority"] == "runner_reported_only"
        assert envelope["model_provider_state_known"] is False
        assert envelope["template_payload"]["operations"] == [
            {"sequence": 1, "tool_name": "project.structure.summary"},
            {"sequence": 2, "tool_name": "project.test.summary"},
        ]
        assert (
            sha256_digest(cast(JsonObject, envelope["template_payload"]))
            == (envelope["template_payload_digest"])
        )
        serialized = json.dumps(envelope, sort_keys=True)
        for forbidden in (
            "host_control",
            "runner_launch_allowed",
            "shell_allowed",
            "filesystem_write_allowed",
            "network_allowed",
            "objective",
            "executable",
            "command",
            "environment",
            "provider_secret",
        ):
            assert forbidden not in serialized
        detail = client.get(f"/missions/{mission_id}", headers=admin_headers)
        assert detail.json()["lifecycle_state"] == "claimed"
        assert detail.json()["lifecycle_revision"] == 2
        replay = client.post(claim_path, headers=claim_headers, json=claim_payload)
        assert replay.status_code == 401
        assert replay.json()["detail"] == "replayed Node nonce"

    with TestClient(create_app(settings)) as restarted:
        replay_after_restart = restarted.post(
            claim_path,
            headers=claim_headers,
            json=claim_payload,
        )
        assert replay_after_restart.status_code == 401
        assert replay_after_restart.json()["detail"] == "replayed Node nonce"

    with sqlite3.connect(settings.db_path) as connection:
        event = json.loads(
            str(
                connection.execute(
                    "SELECT payload_json FROM audit_events WHERE event_type = ?",
                    (AuditEventType.MISSION_CLAIM_STAGED.value,),
                ).fetchone()[0]
            )
        )
        binding = connection.execute(
            "SELECT owner_kind, owner_id, request_digest "
            "FROM mission_audit_evidence_bindings WHERE audit_event_id = ?",
            (event["event_id"],),
        ).fetchone()
    assert event["metadata"]["staged_proposal_only"] is True
    assert event["metadata"]["runner_started_proven"] is False
    assert event["input_hash"] == binding[2]
    assert event["metadata"]["request_digest"] == binding[2]
    assert binding[:2] == ("mission_transition", event["metadata"]["transition_id"])
    audit_text = settings.audit_log_path.read_text(encoding="utf-8")
    assert "project.structure.summary" not in audit_text
    assert "template_payload" not in audit_text


def test_signed_node_claim_is_single_winner_and_target_bound(tmp_path: Path) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    target_key = Ed25519PrivateKey.generate()
    other_key = Ed25519PrivateKey.generate()
    claim_payload: JsonObject = {"protocol_version": "1"}
    with TestClient(create_app(settings)) as client:
        target_node_id = _ready_mission_node(
            client,
            settings,
            nonce_prefix="8",
            node_private_key=target_key,
        )
        other_node_id = _ready_mission_node(
            client,
            settings,
            nonce_prefix="9",
            node_private_key=other_key,
        )
        admitted = client.post(
            "/missions",
            headers=admin_headers,
            json={
                "target_node_id": target_node_id,
                "mission_template_id": "synthetic_read_review_v1",
                "requested_timeout_seconds": 300,
                "client_request_id": "concurrent-claim-mission-001",
            },
        )
        assert admitted.status_code == 200
        other_path = f"/nodes/{other_node_id}/mission-claims"
        wrong_node = client.post(
            other_path,
            headers=_signed_node_headers(
                other_key,
                node_id=other_node_id,
                path=other_path,
                payload=claim_payload,
                nonce="94" * 16,
            ),
            json=claim_payload,
        )
        assert wrong_node.status_code == 404
        assert "template_payload" not in wrong_node.text

        claim_path = f"/nodes/{target_node_id}/mission-claims"
        headers = [
            _signed_node_headers(
                target_key,
                node_id=target_node_id,
                path=claim_path,
                payload=claim_payload,
                nonce=nonce,
            )
            for nonce in ("84" * 16, "85" * 16)
        ]

        def submit_claim(claim_headers: dict[str, str]) -> tuple[int, JsonObject]:
            response = client.post(claim_path, headers=claim_headers, json=claim_payload)
            return response.status_code, cast(JsonObject, response.json())

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(submit_claim, headers))

        assert [status_code for status_code, _ in outcomes].count(200) == 1
        assert all(status_code in {200, 404, 409} for status_code, _ in outcomes)
        [delivery] = [body for status_code, body in outcomes if status_code == 200]
        assert delivery["gateway_delivery_recorded"] is True
        with sqlite3.connect(settings.db_path) as connection:
            assert connection.execute("SELECT count(*) FROM mission_claims").fetchone() == (1,)
            assert connection.execute(
                "SELECT count(*) FROM mission_claims WHERE claim_status = 'delivered'"
            ).fetchone() == (1,)


def test_signed_node_claim_audit_failure_exposes_no_envelope(tmp_path: Path) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    private_key = Ed25519PrivateKey.generate()
    claim_payload: JsonObject = {"protocol_version": "1"}
    api = create_app(settings)
    with TestClient(api) as client:
        node_id = _ready_mission_node(
            client,
            settings,
            nonce_prefix="a",
            node_private_key=private_key,
        )
        admitted = client.post(
            "/missions",
            headers=admin_headers,
            json={
                "target_node_id": node_id,
                "mission_template_id": "synthetic_read_review_v1",
                "requested_timeout_seconds": 300,
                "client_request_id": "claim-audit-failure-001",
            },
        )
        assert admitted.status_code == 200

        class FailingAuditWriter:
            def write_event(self, **_: object) -> None:
                raise AuditWriteError("simulated claim audit failure")

        api.state.mission_claim_service.audit_writer = FailingAuditWriter()
        claim_path = f"/nodes/{node_id}/mission-claims"
        failed = client.post(
            claim_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=claim_path,
                payload=claim_payload,
                nonce="a4" * 16,
            ),
            json=claim_payload,
        )
        assert failed.status_code == 409
        assert failed.json()["detail"] == "mission claim audit evidence failed"
        assert "template_payload" not in failed.text

    with sqlite3.connect(settings.db_path) as connection:
        assert connection.execute(
            "SELECT lifecycle_state, lifecycle_revision FROM missions"
        ).fetchone() == ("queued", 1)
        assert connection.execute("SELECT claim_status FROM mission_claims").fetchone() == (
            "evidence_incomplete",
        )
        assert connection.execute(
            "SELECT evidence_status, failure_reason_code FROM mission_transition_attempts "
            "WHERE transition_kind = 'claim_pending_evidence'"
        ).fetchone() == ("evidence_incomplete", "audit_write_failed")


def test_signed_runner_reports_control_poll_and_cancellation_lifecycle(
    tmp_path: Path,
) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    private_key = Ed25519PrivateKey.generate()
    claim_payload: JsonObject = {"protocol_version": "1"}
    with TestClient(create_app(settings)) as client:
        node_id = _ready_mission_node(
            client,
            settings,
            nonce_prefix="5",
            node_private_key=private_key,
        )
        admitted = client.post(
            "/missions",
            headers=admin_headers,
            json={
                "target_node_id": node_id,
                "mission_template_id": "synthetic_read_review_v1",
                "requested_timeout_seconds": 300,
                "client_request_id": "runner-report-lifecycle-001",
            },
        ).json()
        mission_id = str(admitted["mission_id"])
        claim_path = f"/nodes/{node_id}/mission-claims"
        delivered = client.post(
            claim_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=claim_path,
                payload=claim_payload,
                nonce="54" * 16,
            ),
            json=claim_payload,
        ).json()
        claim_id = str(delivered["claim_id"])
        envelope_digest = str(delivered["envelope_digest"])

        control_path = f"/nodes/{node_id}/mission-control"
        control_payload: JsonObject = {
            "protocol_version": "1",
            "mission_id": mission_id,
            "claim_id": claim_id,
            "envelope_digest": envelope_digest,
            "observed_lifecycle_revision": 2,
        }
        control = client.post(
            control_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=control_path,
                payload=control_payload,
                nonce="55" * 16,
            ),
            json=control_payload,
        )
        assert control.status_code == 200
        assert control.json()["control_decision"] == "continue"
        assert control.json()["decision_revision"] == 2
        future_control_payload: JsonObject = {
            **control_payload,
            "observed_lifecycle_revision": 99,
        }
        future_control = client.post(
            control_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=control_path,
                payload=future_control_payload,
                nonce="5c" * 16,
            ),
            json=future_control_payload,
        )
        assert future_control.status_code == 409
        assert future_control.json()["detail"] == "mission control binding conflicts"

        report_path = f"/nodes/{node_id}/mission-reports"
        running_payload: JsonObject = {
            "mission_id": mission_id,
            "claim_id": claim_id,
            "envelope_digest": envelope_digest,
            "expected_lifecycle_revision": 2,
            "report_id": "mreport_" + ("5" * 32),
            "report_kind": "runner_running",
            "outcome_code": "started",
            "reason_code": None,
            "artifact_digest": None,
        }
        running_headers = _signed_node_headers(
            private_key,
            node_id=node_id,
            path=report_path,
            payload=running_payload,
            nonce="56" * 16,
        )
        running = client.post(
            report_path,
            headers=running_headers,
            json=running_payload,
        )
        assert running.status_code == 200
        assert running.json()["receipt"]["receipt_disposition"] == "lifecycle_advancing"
        assert running.json()["gateway_lifecycle_state"] == "runner_reported_running"
        assert running.json()["gateway_lifecycle_revision"] == 3
        assert running.json()["runner_behavior_proven"] is False
        replayed_nonce = client.post(
            report_path,
            headers=running_headers,
            json=running_payload,
        )
        assert replayed_nonce.status_code == 401
        assert replayed_nonce.json()["detail"] == "replayed mission report nonce"
        exact_replay = client.post(
            report_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=report_path,
                payload=running_payload,
                nonce="5a" * 16,
            ),
            json=running_payload,
        )
        assert exact_replay.status_code == 200
        assert exact_replay.json()["gateway_lifecycle_state"] == "runner_reported_running"
        drifted_payload: JsonObject = {
            **running_payload,
            "expected_lifecycle_revision": 3,
        }
        drifted_headers = _signed_node_headers(
            private_key,
            node_id=node_id,
            path=report_path,
            payload=drifted_payload,
            nonce="5b" * 16,
        )
        drifted = client.post(
            report_path,
            headers=drifted_headers,
            json=drifted_payload,
        )
        assert drifted.status_code == 409
        assert drifted.json()["detail"] == "mission report ID conflicts"
        drifted_nonce_replay = client.post(
            report_path,
            headers=drifted_headers,
            json=drifted_payload,
        )
        assert drifted_nonce_replay.status_code == 401
        assert drifted_nonce_replay.json()["detail"] == "replayed mission report nonce"

        node_record = client.get(f"/nodes/{node_id}", headers=admin_headers).json()
        governed_path = f"/nodes/{node_id}/governed-tool-calls"
        session_prefix = envelope_digest.removeprefix("sha256:")[:16]
        governed_payload: JsonObject = {
            "protocol_version": "1",
            "configuration_generation": node_record["desired_configuration_generation"],
            "configuration_digest": node_record["desired_configuration_digest"],
            "node_version": "0.1.0",
            "session_id": f"mission:{mission_id}:{claim_id}:{session_prefix}",
            "tool_name": "project.structure.summary",
            "arguments": {},
        }
        wrong_claim_payload: JsonObject = {
            **governed_payload,
            "session_id": (f"mission:{mission_id}:mclaim_{'f' * 32}:{session_prefix}"),
        }
        wrong_claim = client.post(
            governed_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=governed_path,
                payload=wrong_claim_payload,
                nonce="5f" * 16,
            ),
            json=wrong_claim_payload,
        )
        assert wrong_claim.status_code == 409
        wrong_envelope_payload: JsonObject = {
            **governed_payload,
            "session_id": f"mission:{mission_id}:{claim_id}:{'0' * 16}",
        }
        wrong_envelope = client.post(
            governed_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=governed_path,
                payload=wrong_envelope_payload,
                nonce="60" * 16,
            ),
            json=wrong_envelope_payload,
        )
        assert wrong_envelope.status_code == 409
        malformed_mission_payload: JsonObject = {
            **governed_payload,
            "session_id": f"mission:{mission_id}:{claim_id}:bad",
        }
        malformed_mission = client.post(
            governed_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=governed_path,
                payload=malformed_mission_payload,
                nonce="63" * 16,
            ),
            json=malformed_mission_payload,
        )
        assert malformed_mission.status_code == 409
        governed = client.post(
            governed_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=governed_path,
                payload=governed_payload,
                nonce="61" * 16,
            ),
            json=governed_payload,
        )
        assert governed.status_code == 200
        correlated = client.get(f"/missions/{mission_id}", headers=admin_headers).json()
        assert correlated["governed_agent_runs"]["count"] == 1
        assert correlated["governed_agent_runs"]["correlation_basis"] == (
            "gateway_validated_claim_session"
        )

        cancel = client.post(
            f"/missions/{mission_id}/cancel",
            headers=admin_headers,
            json={"client_request_id": "runner-report-cancel-001"},
        )
        assert cancel.status_code == 200
        assert cancel.json()["lifecycle_state"] == "cancel_requested"
        assert cancel.json()["lifecycle_revision"] == 4
        assert cancel.json()["runner_stop_proven"] is False
        denied_after_cancel = client.post(
            governed_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=governed_path,
                payload=governed_payload,
                nonce="62" * 16,
            ),
            json=governed_payload,
        )
        assert denied_after_cancel.status_code == 409

        cancel_control_payload: JsonObject = {
            **control_payload,
            "observed_lifecycle_revision": 3,
        }
        cancel_control = client.post(
            control_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=control_path,
                payload=cancel_control_payload,
                nonce="57" * 16,
            ),
            json=cancel_control_payload,
        )
        assert cancel_control.status_code == 200
        assert cancel_control.json()["control_decision"] == "cancel_requested"
        assert cancel_control.json()["decision_revision"] == 4

        observed_payload: JsonObject = {
            **running_payload,
            "expected_lifecycle_revision": 4,
            "report_id": "mreport_" + ("6" * 32),
            "report_kind": "cancel_observed",
            "outcome_code": "cancellation_observed",
        }
        observed = client.post(
            report_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=report_path,
                payload=observed_payload,
                nonce="58" * 16,
            ),
            json=observed_payload,
        )
        assert observed.status_code == 200
        assert observed.json()["receipt"]["receipt_disposition"] == "lifecycle_advancing"
        assert observed.json()["gateway_lifecycle_state"] == "cancel_requested"
        assert observed.json()["gateway_lifecycle_revision"] == 5

        duplicate_observed_payload: JsonObject = {
            **observed_payload,
            "report_id": "mreport_" + ("a" * 32),
        }
        duplicate_observed = client.post(
            report_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=report_path,
                payload=duplicate_observed_payload,
                nonce="5d" * 16,
            ),
            json=duplicate_observed_payload,
        )
        assert duplicate_observed.status_code == 200
        assert duplicate_observed.json()["receipt"]["receipt_disposition"] == "quarantined"
        assert duplicate_observed.json()["gateway_lifecycle_state"] == "cancel_requested"
        assert duplicate_observed.json()["gateway_lifecycle_revision"] == 5

        canceled_payload: JsonObject = {
            **running_payload,
            "expected_lifecycle_revision": 5,
            "report_id": "mreport_" + ("7" * 32),
            "report_kind": "runner_canceled",
            "outcome_code": "canceled",
        }
        canceled = client.post(
            report_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=report_path,
                payload=canceled_payload,
                nonce="59" * 16,
            ),
            json=canceled_payload,
        )
        assert canceled.status_code == 200
        assert canceled.json()["gateway_lifecycle_state"] == "runner_reported_canceled"
        assert canceled.json()["gateway_lifecycle_revision"] == 6
        terminal_control_payload: JsonObject = {
            **control_payload,
            "observed_lifecycle_revision": 6,
        }
        terminal_control = client.post(
            control_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=control_path,
                payload=terminal_control_payload,
                nonce="5e" * 16,
            ),
            json=terminal_control_payload,
        )
        assert terminal_control.status_code == 409
        assert terminal_control.json()["detail"] == "mission has no active control decision"
        cockpit = client.get(f"/missions/{mission_id}", headers=admin_headers)
        assert cockpit.status_code == 200
        cockpit_document = cockpit.json()
        assert cockpit_document["delivery"]["state"] == "claim_delivered"
        assert cockpit_document["runner_reports"]["latest"]["report_kind"] == ("runner_canceled")
        assert cockpit_document["runner_reports"]["quarantined_count"] == 1
        assert cockpit_document["runner_reports"]["report_conflict_count"] == 0
        assert cockpit_document["cancellation"] == {
            "authority": "gateway_decision_and_runner_reported_observation",
            "recorded": True,
            "observed_by_node": True,
            "runner_reported_canceled": True,
            "runner_process_stop_proven": False,
        }
        assert cockpit_document["attention_codes"] == ["quarantine"]

    with TestClient(create_app(settings)) as restarted:
        replay_after_restart = restarted.post(
            report_path,
            headers=running_headers,
            json=running_payload,
        )
        assert replay_after_restart.status_code == 401
        assert replay_after_restart.json()["detail"] == "replayed mission report nonce"

    with sqlite3.connect(settings.db_path) as connection:
        assert connection.execute(
            "SELECT count(*) FROM mission_report_receipts WHERE evidence_status = 'complete'"
        ).fetchone() == (4,)
        assert connection.execute(
            "SELECT count(*) FROM mission_transition_attempts "
            "WHERE transition_kind = 'report_pending_evidence' "
            "AND evidence_status = 'complete'"
        ).fetchone() == (2,)

    store = MissionStore(settings.db_path)
    cancellation = store.get_cancellation_transition(mission_id)
    assert cancellation is not None
    assert cancellation.audit_event_id is not None
    with sqlite3.connect(settings.db_path) as connection:
        original_owner_id = connection.execute(
            "SELECT owner_id FROM mission_audit_evidence_bindings WHERE audit_event_id = ?",
            (cancellation.audit_event_id,),
        ).fetchone()[0]
        connection.execute(
            "UPDATE mission_audit_evidence_bindings SET owner_id = ? WHERE audit_event_id = ?",
            ("mtransition_" + ("0" * 32), cancellation.audit_event_id),
        )
        connection.commit()
    with pytest.raises(MissionError, match="stored mission audit evidence binding"):
        store.get_cancellation_transition(mission_id)
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute(
            "UPDATE mission_audit_evidence_bindings SET owner_id = ? WHERE audit_event_id = ?",
            (original_owner_id, cancellation.audit_event_id),
        )
        connection.commit()
    assert store.get_cancellation_transition(mission_id) == cancellation


def test_revoked_node_report_is_quarantined_and_cannot_poll_control(
    tmp_path: Path,
) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    private_key = Ed25519PrivateKey.generate()
    claim_payload: JsonObject = {"protocol_version": "1"}
    with TestClient(create_app(settings)) as client:
        node_id = _ready_mission_node(
            client,
            settings,
            nonce_prefix="4",
            node_private_key=private_key,
        )
        mission = client.post(
            "/missions",
            headers=admin_headers,
            json={
                "target_node_id": node_id,
                "mission_template_id": "synthetic_read_review_v1",
                "requested_timeout_seconds": 300,
                "client_request_id": "revoked-report-quarantine-001",
            },
        ).json()
        mission_id = str(mission["mission_id"])
        claim_path = f"/nodes/{node_id}/mission-claims"
        claim = client.post(
            claim_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=claim_path,
                payload=claim_payload,
                nonce="44" * 16,
            ),
            json=claim_payload,
        ).json()
        revoked = client.post(f"/nodes/{node_id}/revoke", headers=admin_headers)
        assert revoked.status_code == 200
        report_path = f"/nodes/{node_id}/mission-reports"
        report_payload: JsonObject = {
            "mission_id": mission_id,
            "claim_id": claim["claim_id"],
            "envelope_digest": claim["envelope_digest"],
            "expected_lifecycle_revision": 2,
            "report_id": "mreport_" + ("4" * 32),
            "report_kind": "runner_running",
            "outcome_code": "started",
            "reason_code": None,
            "artifact_digest": None,
        }
        report = client.post(
            report_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=report_path,
                payload=report_payload,
                nonce="45" * 16,
            ),
            json=report_payload,
        )
        assert report.status_code == 200
        assert report.json()["receipt"]["receipt_disposition"] == "quarantined"
        assert report.json()["receipt"]["receipt_posture"]["proposed_advancement"] == {
            "node_status": "revoked",
            "node_evidence_status": "complete",
            "verified_node_identity_key_id": report.json()["receipt"][
                "verified_node_identity_key_id"
            ],
            "current_node_identity_key_id": report.json()["receipt"][
                "verified_node_identity_key_id"
            ],
            "state": "quarantined",
            "reason_code": "node_revoked",
        }
        assert report.json()["receipt"]["receipt_posture"]["quarantine_reason_code"] == (
            "node_revoked"
        )
        assert report.json()["gateway_lifecycle_state"] == "claimed"
        cockpit = client.get(f"/missions/{mission_id}", headers=admin_headers).json()
        assert cockpit["runner_reports"]["quarantined_count"] == 1
        assert cockpit["runner_reports"]["report_conflict_count"] == 0
        assert cockpit["attention_codes"] == ["quarantine"]
        control_path = f"/nodes/{node_id}/mission-control"
        control_payload: JsonObject = {
            "protocol_version": "1",
            "mission_id": mission_id,
            "claim_id": claim["claim_id"],
            "envelope_digest": claim["envelope_digest"],
            "observed_lifecycle_revision": 2,
        }
        denied_control = client.post(
            control_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=control_path,
                payload=control_payload,
                nonce="46" * 16,
            ),
            json=control_payload,
        )
        assert denied_control.status_code == 401
        assert denied_control.json()["detail"] == "Node is revoked"


def test_runner_report_identity_rotation_enforces_current_key_and_preserves_replay(
    tmp_path: Path,
) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    current_private_key = Ed25519PrivateKey.generate()
    claim_payload: JsonObject = {"protocol_version": "1"}
    with TestClient(create_app(settings)) as client:
        node_id = _ready_mission_node(
            client,
            settings,
            nonce_prefix="3",
            node_private_key=current_private_key,
        )
        mission = client.post(
            "/missions",
            headers=admin_headers,
            json={
                "target_node_id": node_id,
                "mission_template_id": "synthetic_read_review_v1",
                "requested_timeout_seconds": 300,
                "client_request_id": "runner-report-key-rotation-001",
            },
        ).json()
        mission_id = str(mission["mission_id"])
        claim_path = f"/nodes/{node_id}/mission-claims"
        claim = client.post(
            claim_path,
            headers=_signed_node_headers(
                current_private_key,
                node_id=node_id,
                path=claim_path,
                payload=claim_payload,
                nonce="34" * 16,
            ),
            json=claim_payload,
        ).json()
        report_path = f"/nodes/{node_id}/mission-reports"
        running_payload: JsonObject = {
            "mission_id": mission_id,
            "claim_id": claim["claim_id"],
            "envelope_digest": claim["envelope_digest"],
            "expected_lifecycle_revision": 2,
            "report_id": "mreport_" + ("3" * 32),
            "report_kind": "runner_running",
            "outcome_code": "started",
            "reason_code": None,
            "artifact_digest": None,
        }
        accepted = client.post(
            report_path,
            headers=_signed_node_headers(
                current_private_key,
                node_id=node_id,
                path=report_path,
                payload=running_payload,
                nonce="35" * 16,
            ),
            json=running_payload,
        )
        assert accepted.status_code == 200
        first_receipt = accepted.json()["receipt"]
        old_key_id = first_receipt["verified_node_identity_key_id"]

        next_private_key = _rotate_ready_node_identity_key(
            client,
            settings,
            node_id=node_id,
            current_private_key=current_private_key,
            nonce_prefix="b",
        )
        new_key_id = node_identity_key_id(
            base64.b64encode(next_private_key.public_key().public_bytes_raw()).decode()
        )
        assert new_key_id != old_key_id

        retired_key_payload: JsonObject = {
            **running_payload,
            "expected_lifecycle_revision": 3,
            "report_id": "mreport_" + ("b" * 32),
            "report_kind": "runner_succeeded",
            "outcome_code": "succeeded",
            "artifact_digest": "sha256:" + ("b" * 64),
        }
        retired_key_report = client.post(
            report_path,
            headers=_signed_node_headers(
                current_private_key,
                node_id=node_id,
                path=report_path,
                payload=retired_key_payload,
                nonce="36" * 16,
            ),
            json=retired_key_payload,
        )
        assert retired_key_report.status_code == 401

        replay_after_rotation = client.post(
            report_path,
            headers=_signed_node_headers(
                next_private_key,
                node_id=node_id,
                path=report_path,
                payload=running_payload,
                nonce="37" * 16,
            ),
            json=running_payload,
        )
        assert replay_after_rotation.status_code == 200
        assert replay_after_rotation.json()["receipt"] == first_receipt
        assert (
            replay_after_rotation.json()["receipt"]["verified_node_identity_key_id"] == old_key_id
        )

        current_key_report = client.post(
            report_path,
            headers=_signed_node_headers(
                next_private_key,
                node_id=node_id,
                path=report_path,
                payload=retired_key_payload,
                nonce="38" * 16,
            ),
            json=retired_key_payload,
        )
        assert current_key_report.status_code == 200
        assert current_key_report.json()["receipt"]["receipt_disposition"] == (
            "lifecycle_advancing"
        )
        assert current_key_report.json()["receipt"]["verified_node_identity_key_id"] == new_key_id
        assert current_key_report.json()["gateway_lifecycle_state"] == ("runner_reported_succeeded")
        assert current_key_report.json()["gateway_lifecycle_revision"] == 4


def test_mission_control_never_continues_at_claim_expiry(tmp_path: Path) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    private_key = Ed25519PrivateKey.generate()
    claim_payload: JsonObject = {"protocol_version": "1"}
    api = create_app(settings)
    with TestClient(api) as client:
        node_id = _ready_mission_node(
            client,
            settings,
            nonce_prefix="c",
            node_private_key=private_key,
        )
        mission_id = str(
            client.post(
                "/missions",
                headers=admin_headers,
                json={
                    "target_node_id": node_id,
                    "mission_template_id": "synthetic_read_review_v1",
                    "requested_timeout_seconds": 300,
                    "client_request_id": "expired-control-decision-001",
                },
            ).json()["mission_id"]
        )
        claim_path = f"/nodes/{node_id}/mission-claims"
        claim = client.post(
            claim_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=claim_path,
                payload=claim_payload,
                nonce="c4" * 16,
            ),
            json=claim_payload,
        ).json()
        stored_claim = MissionStore(settings.db_path).get_claim(mission_id)
        payload = MissionControlPollPayload(
            protocol_version="1",
            mission_id=mission_id,
            claim_id=claim["claim_id"],
            envelope_digest=claim["envelope_digest"],
            observed_lifecycle_revision=2,
        )
        with pytest.raises(MissionReportError, match="mission claim has expired"):
            cast(
                MissionReportService,
                api.state.mission_report_service,
            ).control_decision(
                payload,
                authenticated_node=NodeStore(settings.db_path).get(node_id),
                now=datetime.fromisoformat(stored_claim.expires_at),
            )


@pytest.mark.parametrize("completion_path", ("success", "cancellation"))
def test_started_mission_remains_controllable_after_claim_delivery_deadline(
    tmp_path: Path,
    completion_path: str,
) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    private_key = Ed25519PrivateKey.generate()
    claim_payload: JsonObject = {"protocol_version": "1"}
    api = create_app(settings)
    with TestClient(api) as client:
        node_id = _ready_mission_node(
            client,
            settings,
            nonce_prefix="9",
            node_private_key=private_key,
        )
        mission_id = str(
            client.post(
                "/missions",
                headers=admin_headers,
                json={
                    "target_node_id": node_id,
                    "mission_template_id": "synthetic_read_review_v1",
                    "requested_timeout_seconds": 60,
                    "client_request_id": f"post-expiry-{completion_path}-001",
                },
            ).json()["mission_id"]
        )
        claim_path = f"/nodes/{node_id}/mission-claims"
        claim_document = client.post(
            claim_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=claim_path,
                payload=claim_payload,
                nonce="94" * 16,
            ),
            json=claim_payload,
        ).json()

        store = MissionStore(settings.db_path)
        claim = store.get_claim(mission_id)
        expires_at = datetime.fromisoformat(claim.expires_at)
        before_expiry = expires_at - timedelta(seconds=1)
        after_expiry = expires_at + timedelta(seconds=1)
        node = NodeStore(settings.db_path).get(node_id)
        verified_key_id = node_identity_key_id(node.public_key)
        report_service = cast(MissionReportService, api.state.mission_report_service)

        def accept_at(
            report: MissionRunnerReportPayload,
            when: datetime,
        ) -> JsonObject:
            with sqlite3.connect(settings.db_path) as connection:
                connection.execute("PRAGMA foreign_keys = ON")
                connection.execute("BEGIN IMMEDIATE")
                staged = report_service.stage_authenticated_report(
                    connection,
                    report,
                    authenticated_node=node,
                    verified_node_identity_key_id=verified_key_id,
                    now=when,
                )
                connection.commit()
            return report_service.accept_report(
                report,
                authenticated_node=node,
                verified_node_identity_key_id=verified_key_id,
                staged=staged,
                now=when,
            )

        running_report = MissionRunnerReportPayload(
            mission_id=mission_id,
            claim_id=claim.claim_id,
            envelope_digest=claim.envelope_digest,
            expected_lifecycle_revision=2,
            report_id="mreport_" + ("9" * 32),
            report_kind="runner_running",
            outcome_code="started",
        )
        running = accept_at(running_report, before_expiry)
        assert running["gateway_lifecycle_state"] == "runner_reported_running"
        assert running["gateway_lifecycle_revision"] == 3

        control_payload = MissionControlPollPayload(
            protocol_version="1",
            mission_id=mission_id,
            claim_id=claim.claim_id,
            envelope_digest=claim.envelope_digest,
            observed_lifecycle_revision=3,
        )
        continued = report_service.control_decision(
            control_payload,
            authenticated_node=node,
            now=after_expiry,
        )
        assert continued["control_decision"] == "continue"
        assert continued["decision_revision"] == 3

        if completion_path == "success":
            success_report = MissionRunnerReportPayload(
                mission_id=mission_id,
                claim_id=claim.claim_id,
                envelope_digest=claim.envelope_digest,
                expected_lifecycle_revision=3,
                report_id="mreport_" + ("8" * 32),
                report_kind="runner_succeeded",
                outcome_code="succeeded",
                artifact_digest="sha256:" + ("8" * 64),
            )
            succeeded = accept_at(success_report, after_expiry)
            assert succeeded["gateway_lifecycle_state"] == "runner_reported_succeeded"
            assert succeeded["gateway_lifecycle_revision"] == 4
            return

        canceled = cast(
            MissionAdmissionService,
            api.state.mission_admission_service,
        ).cancel(
            mission_id,
            MissionCancellationPayload(client_request_id="post-expiry-cancellation-001"),
            requester=ADMIN_CONTEXT,
            now=after_expiry,
        )
        assert canceled["lifecycle_state"] == "cancel_requested"
        assert canceled["lifecycle_revision"] == 4
        cancel_decision = report_service.control_decision(
            control_payload,
            authenticated_node=node,
            now=after_expiry + timedelta(seconds=1),
        )
        assert cancel_decision["control_decision"] == "cancel_requested"
        assert cancel_decision["decision_revision"] == 4
        observed_report = MissionRunnerReportPayload(
            mission_id=mission_id,
            claim_id=claim.claim_id,
            envelope_digest=claim.envelope_digest,
            expected_lifecycle_revision=4,
            report_id="mreport_" + ("7" * 32),
            report_kind="cancel_observed",
            outcome_code="cancellation_observed",
        )
        observed = accept_at(observed_report, after_expiry + timedelta(seconds=2))
        assert observed["gateway_lifecycle_state"] == "cancel_requested"
        assert observed["gateway_lifecycle_revision"] == 5
        canceled_report = MissionRunnerReportPayload(
            mission_id=mission_id,
            claim_id=claim.claim_id,
            envelope_digest=claim.envelope_digest,
            expected_lifecycle_revision=5,
            report_id="mreport_" + ("6" * 32),
            report_kind="runner_canceled",
            outcome_code="canceled",
        )
        runner_canceled = accept_at(
            canceled_report,
            after_expiry + timedelta(seconds=3),
        )
        assert runner_canceled["gateway_lifecycle_state"] == "runner_reported_canceled"
        assert runner_canceled["gateway_lifecycle_revision"] == 6
        assert claim_document["claim_id"] == claim.claim_id


@pytest.mark.parametrize("authority_change", ("cancellation", "revocation"))
def test_control_post_audit_revalidation_denies_concurrent_authority_change(
    tmp_path: Path,
    authority_change: str,
) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    private_key = Ed25519PrivateKey.generate()
    claim_payload: JsonObject = {"protocol_version": "1"}
    api = create_app(settings)
    with TestClient(api) as client:
        node_id = _ready_mission_node(
            client,
            settings,
            nonce_prefix="7",
            node_private_key=private_key,
        )
        mission_id = str(
            client.post(
                "/missions",
                headers=admin_headers,
                json={
                    "target_node_id": node_id,
                    "mission_template_id": "synthetic_read_review_v1",
                    "requested_timeout_seconds": 300,
                    "client_request_id": f"control-race-{authority_change}-001",
                },
            ).json()["mission_id"]
        )
        claim_path = f"/nodes/{node_id}/mission-claims"
        claim = client.post(
            claim_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=claim_path,
                payload=claim_payload,
                nonce="74" * 16,
            ),
            json=claim_payload,
        ).json()
        real_audit_writer = api.state.mission_report_service.audit_writer

        class AuthorityChangingControlAuditWriter:
            def write_event(self, **kwargs: object) -> object:
                event = real_audit_writer.write_event(**kwargs)
                if kwargs.get("event_type") == AuditEventType.MISSION_CONTROL_POLLED:
                    if authority_change == "cancellation":
                        cast(
                            MissionAdmissionService,
                            api.state.mission_admission_service,
                        ).cancel(
                            mission_id,
                            MissionCancellationPayload(
                                client_request_id="control-race-cancellation-001"
                            ),
                            requester=ADMIN_CONTEXT,
                        )
                    else:
                        NodeStore(settings.db_path).revoke(node_id)
                return event

        api.state.mission_report_service.audit_writer = AuthorityChangingControlAuditWriter()
        control_path = f"/nodes/{node_id}/mission-control"
        control_payload: JsonObject = {
            "protocol_version": "1",
            "mission_id": mission_id,
            "claim_id": claim["claim_id"],
            "envelope_digest": claim["envelope_digest"],
            "observed_lifecycle_revision": 2,
        }
        denied = client.post(
            control_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=control_path,
                payload=control_payload,
                nonce="75" * 16,
            ),
            json=control_payload,
        )
        assert denied.status_code == 409
        assert denied.json()["detail"] == ("mission control authority changed before delivery")

        if authority_change == "cancellation":
            assert (
                MissionStore(settings.db_path).get(mission_id).safe_summary()["lifecycle_state"]
                == "cancel_requested"
            )
            return

        node = NodeStore(settings.db_path).get(node_id)
        assert (node.status, node.evidence_status) == ("revoked", "pending")
        report_path = f"/nodes/{node_id}/mission-reports"
        report_payload: JsonObject = {
            "mission_id": mission_id,
            "claim_id": claim["claim_id"],
            "envelope_digest": claim["envelope_digest"],
            "expected_lifecycle_revision": 2,
            "report_id": "mreport_" + ("5" * 32),
            "report_kind": "runner_running",
            "outcome_code": "started",
            "reason_code": None,
            "artifact_digest": None,
        }
        quarantined = client.post(
            report_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=report_path,
                payload=report_payload,
                nonce="76" * 16,
            ),
            json=report_payload,
        )
        assert quarantined.status_code == 200
        assert quarantined.json()["receipt"]["receipt_disposition"] == "quarantined"
        assert (
            quarantined.json()["receipt"]["receipt_posture"]["proposed_advancement"]["reason_code"]
            == "node_revoked"
        )
        assert quarantined.json()["gateway_lifecycle_state"] == "claimed"


def test_control_post_audit_revalidation_denies_claim_expiry_clock_race(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    private_key = Ed25519PrivateKey.generate()
    claim_payload: JsonObject = {"protocol_version": "1"}
    with TestClient(create_app(settings)) as client:
        node_id = _ready_mission_node(
            client,
            settings,
            nonce_prefix="6",
            node_private_key=private_key,
        )
        mission_id = str(
            client.post(
                "/missions",
                headers=admin_headers,
                json={
                    "target_node_id": node_id,
                    "mission_template_id": "synthetic_read_review_v1",
                    "requested_timeout_seconds": 60,
                    "client_request_id": "control-expiry-race-001",
                },
            ).json()["mission_id"]
        )
        claim_path = f"/nodes/{node_id}/mission-claims"
        claim = client.post(
            claim_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=claim_path,
                payload=claim_payload,
                nonce="64" * 16,
            ),
            json=claim_payload,
        ).json()
        expires_at = datetime.fromisoformat(
            MissionStore(settings.db_path).get_claim(mission_id).expires_at
        )
        observed_times = iter(
            (
                expires_at - timedelta(microseconds=1),
                expires_at + timedelta(microseconds=1),
            )
        )

        class AdvancingDateTime:
            @classmethod
            def now(cls, tz: object = None) -> datetime:
                del tz
                return next(observed_times)

            @classmethod
            def fromisoformat(cls, value: str) -> datetime:
                return datetime.fromisoformat(value)

        monkeypatch.setattr(mission_reports_module, "datetime", AdvancingDateTime)
        control_path = f"/nodes/{node_id}/mission-control"
        control_payload: JsonObject = {
            "protocol_version": "1",
            "mission_id": mission_id,
            "claim_id": claim["claim_id"],
            "envelope_digest": claim["envelope_digest"],
            "observed_lifecycle_revision": 2,
        }
        denied = client.post(
            control_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=control_path,
                payload=control_payload,
                nonce="65" * 16,
            ),
            json=control_payload,
        )
        assert denied.status_code == 409
        assert denied.json()["detail"] == ("mission control authority changed before delivery")


def test_pending_identity_rotation_current_key_report_is_quarantined(
    tmp_path: Path,
) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    private_key = Ed25519PrivateKey.generate()
    claim_payload: JsonObject = {"protocol_version": "1"}
    with TestClient(create_app(settings)) as client:
        node_id = _ready_mission_node(
            client,
            settings,
            nonce_prefix="4",
            node_private_key=private_key,
        )
        mission_id = str(
            client.post(
                "/missions",
                headers=admin_headers,
                json={
                    "target_node_id": node_id,
                    "mission_template_id": "synthetic_read_review_v1",
                    "requested_timeout_seconds": 300,
                    "client_request_id": "pending-rotation-report-001",
                },
            ).json()["mission_id"]
        )
        claim_path = f"/nodes/{node_id}/mission-claims"
        claim = client.post(
            claim_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=claim_path,
                payload=claim_payload,
                nonce="44" * 16,
            ),
            json=claim_payload,
        ).json()
        challenge_path = f"/nodes/{node_id}/identity-key-rotation/challenges"
        challenge_payload: JsonObject = {"protocol_version": "1"}
        challenge = client.post(
            challenge_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=challenge_path,
                payload=challenge_payload,
                nonce="45" * 16,
            ),
            json=challenge_payload,
        )
        assert challenge.status_code == 200
        assert challenge.json()["status"] == "pending"
        assert challenge.json()["evidence_status"] == "complete"

        report_path = f"/nodes/{node_id}/mission-reports"
        report_payload: JsonObject = {
            "mission_id": mission_id,
            "claim_id": claim["claim_id"],
            "envelope_digest": claim["envelope_digest"],
            "expected_lifecycle_revision": 2,
            "report_id": "mreport_" + ("4" * 32),
            "report_kind": "runner_running",
            "outcome_code": "started",
            "reason_code": None,
            "artifact_digest": None,
        }
        report = client.post(
            report_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=report_path,
                payload=report_payload,
                nonce="46" * 16,
            ),
            json=report_payload,
        )
        assert report.status_code == 200
        assert report.json()["receipt"]["receipt_disposition"] == "quarantined"
        assert (
            report.json()["receipt"]["receipt_posture"]["proposed_advancement"]["reason_code"]
            == "identity_rotation_pending"
        )
        assert report.json()["gateway_lifecycle_state"] == "claimed"
        control_path = f"/nodes/{node_id}/mission-control"
        control_payload: JsonObject = {
            "protocol_version": "1",
            "mission_id": mission_id,
            "claim_id": claim["claim_id"],
            "envelope_digest": claim["envelope_digest"],
            "observed_lifecycle_revision": 2,
        }
        control = client.post(
            control_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=control_path,
                payload=control_payload,
                nonce="47" * 16,
            ),
            json=control_payload,
        )
        assert control.status_code == 409
        assert control.json()["detail"] == ("mission control authority changed before delivery")


def test_identity_rotation_activation_pending_keys_cannot_report(
    tmp_path: Path,
) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    current_private_key = Ed25519PrivateKey.generate()
    claim_payload: JsonObject = {"protocol_version": "1"}
    with TestClient(create_app(settings)) as client:
        node_id = _ready_mission_node(
            client,
            settings,
            nonce_prefix="8",
            node_private_key=current_private_key,
        )
        mission_id = str(
            client.post(
                "/missions",
                headers=admin_headers,
                json={
                    "target_node_id": node_id,
                    "mission_template_id": "synthetic_read_review_v1",
                    "requested_timeout_seconds": 300,
                    "client_request_id": "activation-pending-report-001",
                },
            ).json()["mission_id"]
        )
        claim_path = f"/nodes/{node_id}/mission-claims"
        claim = client.post(
            claim_path,
            headers=_signed_node_headers(
                current_private_key,
                node_id=node_id,
                path=claim_path,
                payload=claim_payload,
                nonce="84" * 16,
            ),
            json=claim_payload,
        ).json()
        challenge_path = f"/nodes/{node_id}/identity-key-rotation/challenges"
        challenge_payload: JsonObject = {"protocol_version": "1"}
        challenge = client.post(
            challenge_path,
            headers=_signed_node_headers(
                current_private_key,
                node_id=node_id,
                path=challenge_path,
                payload=challenge_payload,
                nonce="85" * 16,
            ),
            json=challenge_payload,
        ).json()
        store = NodeStore(settings.db_path)
        rotation = store.get_identity_rotation(str(challenge["rotation_id"]))
        next_private_key = Ed25519PrivateKey.generate()
        next_public_key = base64.b64encode(
            next_private_key.public_key().public_bytes_raw()
        ).decode()
        next_key_id = node_identity_key_id(next_public_key)
        proof = canonical_identity_rotation_proof_message(
            rotation=rotation,
            next_key_id=next_key_id,
        )
        pending_node, pending_rotation = store.activate_identity_rotation(
            node_id,
            NodeIdentityRotationActivationPayload(
                protocol_version="1",
                rotation_id=rotation.rotation_id,
                challenge=str(challenge["challenge"]),
                next_public_key=next_public_key,
                next_key_proof=base64.b64encode(next_private_key.sign(proof)).decode(),
            ),
        )
        assert (pending_node.evidence_status, pending_rotation.status) == (
            "pending",
            "activated",
        )
        assert pending_rotation.evidence_status == "pending"

        report_path = f"/nodes/{node_id}/mission-reports"
        report_payload: JsonObject = {
            "mission_id": mission_id,
            "claim_id": claim["claim_id"],
            "envelope_digest": claim["envelope_digest"],
            "expected_lifecycle_revision": 2,
            "report_id": "mreport_" + ("8" * 32),
            "report_kind": "runner_running",
            "outcome_code": "started",
            "reason_code": None,
            "artifact_digest": None,
        }
        new_key_denied = client.post(
            report_path,
            headers=_signed_node_headers(
                next_private_key,
                node_id=node_id,
                path=report_path,
                payload=report_payload,
                nonce="86" * 16,
            ),
            json=report_payload,
        )
        assert new_key_denied.status_code == 401
        assert new_key_denied.json()["detail"] == (
            "Node identity-key activation evidence is incomplete"
        )
        old_key_denied = client.post(
            report_path,
            headers=_signed_node_headers(
                current_private_key,
                node_id=node_id,
                path=report_path,
                payload=report_payload,
                nonce="87" * 16,
            ),
            json=report_payload,
        )
        assert old_key_denied.status_code == 401
        with sqlite3.connect(settings.db_path) as connection:
            assert connection.execute(
                "SELECT count(*) FROM mission_report_receipts"
            ).fetchone() == (0,)


def test_heartbeat_audit_pending_current_key_report_is_quarantined(
    tmp_path: Path,
) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    private_key = Ed25519PrivateKey.generate()
    claim_payload: JsonObject = {"protocol_version": "1"}
    api = create_app(settings)
    with TestClient(api) as client:
        node_id = _ready_mission_node(
            client,
            settings,
            nonce_prefix="5",
            node_private_key=private_key,
        )
        mission_id = str(
            client.post(
                "/missions",
                headers=admin_headers,
                json={
                    "target_node_id": node_id,
                    "mission_template_id": "synthetic_read_review_v1",
                    "requested_timeout_seconds": 300,
                    "client_request_id": "heartbeat-pending-report-001",
                },
            ).json()["mission_id"]
        )
        claim_path = f"/nodes/{node_id}/mission-claims"
        claim = client.post(
            claim_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=claim_path,
                payload=claim_payload,
                nonce="54" * 16,
            ),
            json=claim_payload,
        ).json()
        node = NodeStore(settings.db_path).get(node_id)
        assert node.acknowledged_configuration_digest is not None
        heartbeat_payload: JsonObject = {
            "protocol_version": "1",
            "node_version": "0.1.0",
            "runner_adapter": "hermes",
            "deployment_topology": "docker_sidecar",
            "configuration_digest": node.acknowledged_configuration_digest,
        }
        real_audit_writer = api.state.audit_writer

        class FailingHeartbeatAuditWriter:
            def write_event(self, **kwargs: object) -> object:
                if kwargs.get("event_type") == AuditEventType.NODE_HEARTBEAT_ACCEPTED:
                    raise AuditWriteError("simulated heartbeat audit failure")
                return real_audit_writer.write_event(**kwargs)

        api.state.audit_writer = FailingHeartbeatAuditWriter()
        heartbeat_path = f"/nodes/{node_id}/heartbeat"
        with pytest.raises(AuditWriteError, match="simulated heartbeat audit failure"):
            client.post(
                heartbeat_path,
                headers=_signed_node_headers(
                    private_key,
                    node_id=node_id,
                    path=heartbeat_path,
                    payload=heartbeat_payload,
                    nonce="55" * 16,
                ),
                json=heartbeat_payload,
            )
        pending_node = NodeStore(settings.db_path).get(node_id)
        assert (pending_node.status, pending_node.evidence_status) == (
            "enrolled",
            "pending",
        )

        report_path = f"/nodes/{node_id}/mission-reports"
        report_payload: JsonObject = {
            "mission_id": mission_id,
            "claim_id": claim["claim_id"],
            "envelope_digest": claim["envelope_digest"],
            "expected_lifecycle_revision": 2,
            "report_id": "mreport_" + ("c" * 32),
            "report_kind": "runner_running",
            "outcome_code": "started",
            "reason_code": None,
            "artifact_digest": None,
        }
        report = client.post(
            report_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=report_path,
                payload=report_payload,
                nonce="56" * 16,
            ),
            json=report_payload,
        )
        assert report.status_code == 200
        assert report.json()["receipt"]["receipt_disposition"] == "quarantined"
        assert (
            report.json()["receipt"]["receipt_posture"]["proposed_advancement"]["reason_code"]
            == "posture_ineligible"
        )
        assert report.json()["gateway_lifecycle_state"] == "claimed"


@pytest.mark.parametrize(
    ("mutation_sql", "parameters"),
    (
        (
            "UPDATE nodes SET last_seen_at = ? WHERE node_id = ?",
            ("2020-01-01T00:00:00+00:00",),
        ),
        (
            "UPDATE nodes SET last_configuration_digest = ? WHERE node_id = ?",
            ("sha256:" + ("9" * 64),),
        ),
        ("UPDATE nodes SET last_node_version = '0.0.1' WHERE node_id = ?", ()),
        (
            "UPDATE nodes SET configuration_acknowledgment_status = NULL WHERE node_id = ?",
            (),
        ),
    ),
)
def test_ineligible_current_posture_runner_reports_are_quarantined(
    tmp_path: Path,
    mutation_sql: str,
    parameters: tuple[object, ...],
) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    private_key = Ed25519PrivateKey.generate()
    claim_payload: JsonObject = {"protocol_version": "1"}
    with TestClient(create_app(settings)) as client:
        node_id = _ready_mission_node(
            client,
            settings,
            nonce_prefix="d",
            node_private_key=private_key,
        )
        mission_id = str(
            client.post(
                "/missions",
                headers=admin_headers,
                json={
                    "target_node_id": node_id,
                    "mission_template_id": "synthetic_read_review_v1",
                    "requested_timeout_seconds": 300,
                    "client_request_id": "ineligible-report-quarantine-001",
                },
            ).json()["mission_id"]
        )
        claim_path = f"/nodes/{node_id}/mission-claims"
        claim = client.post(
            claim_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=claim_path,
                payload=claim_payload,
                nonce="d4" * 16,
            ),
            json=claim_payload,
        ).json()
        with sqlite3.connect(settings.db_path) as connection:
            connection.execute(mutation_sql, (*parameters, node_id))
            connection.commit()
        report_path = f"/nodes/{node_id}/mission-reports"
        report_payload: JsonObject = {
            "mission_id": mission_id,
            "claim_id": claim["claim_id"],
            "envelope_digest": claim["envelope_digest"],
            "expected_lifecycle_revision": 2,
            "report_id": "mreport_" + ("d" * 32),
            "report_kind": "runner_running",
            "outcome_code": "started",
            "reason_code": None,
            "artifact_digest": None,
        }
        report = client.post(
            report_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=report_path,
                payload=report_payload,
                nonce="d5" * 16,
            ),
            json=report_payload,
        )
        assert report.status_code == 200
        assert report.json()["receipt"]["receipt_disposition"] == "quarantined"
        assert (
            report.json()["receipt"]["receipt_posture"]["proposed_advancement"]["reason_code"]
            == "posture_ineligible"
        )
        assert report.json()["gateway_lifecycle_state"] == "claimed"
        assert report.json()["gateway_lifecycle_revision"] == 2


def test_runner_report_audit_failure_records_receipt_without_lifecycle_advance(
    tmp_path: Path,
) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    private_key = Ed25519PrivateKey.generate()
    claim_payload: JsonObject = {"protocol_version": "1"}
    api = create_app(settings)
    with TestClient(api) as client:
        node_id = _ready_mission_node(
            client,
            settings,
            nonce_prefix="3",
            node_private_key=private_key,
        )
        mission = client.post(
            "/missions",
            headers=admin_headers,
            json={
                "target_node_id": node_id,
                "mission_template_id": "synthetic_read_review_v1",
                "requested_timeout_seconds": 300,
                "client_request_id": "report-audit-failure-001",
            },
        ).json()
        mission_id = str(mission["mission_id"])
        claim_path = f"/nodes/{node_id}/mission-claims"
        claim = client.post(
            claim_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=claim_path,
                payload=claim_payload,
                nonce="34" * 16,
            ),
            json=claim_payload,
        ).json()

        class FailingReportAuditWriter:
            def write_event(self, **_: object) -> None:
                raise AuditWriteError("simulated report receipt audit failure")

        api.state.mission_report_service.audit_writer = FailingReportAuditWriter()
        report_path = f"/nodes/{node_id}/mission-reports"
        report_payload: JsonObject = {
            "mission_id": mission_id,
            "claim_id": claim["claim_id"],
            "envelope_digest": claim["envelope_digest"],
            "expected_lifecycle_revision": 2,
            "report_id": "mreport_" + ("3" * 32),
            "report_kind": "runner_running",
            "outcome_code": "started",
            "reason_code": None,
            "artifact_digest": None,
        }
        failed = client.post(
            report_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=report_path,
                payload=report_payload,
                nonce="35" * 16,
            ),
            json=report_payload,
        )
        assert failed.status_code == 409
        assert failed.json()["detail"] == "mission report receipt audit evidence failed"

    with TestClient(create_app(settings)) as recovered_client:
        blocked_cancel = recovered_client.post(
            f"/missions/{mission_id}/cancel",
            headers=admin_headers,
            json={"client_request_id": "report-recovery-cancel-001"},
        )
        assert blocked_cancel.status_code == 409
        assert blocked_cancel.json()["detail"] == (
            "mission report receipt requires evidence recovery"
        )
        later_report_payload: JsonObject = {
            **report_payload,
            "report_id": "mreport_" + ("c" * 32),
        }
        later_report = recovered_client.post(
            report_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=report_path,
                payload=later_report_payload,
                nonce="36" * 16,
            ),
            json=later_report_payload,
        )
        assert later_report.status_code == 200
        assert later_report.json()["receipt"]["receipt_disposition"] == "quarantined"
        assert later_report.json()["gateway_lifecycle_state"] == "claimed"
        assert later_report.json()["gateway_lifecycle_revision"] == 2

    with sqlite3.connect(settings.db_path) as connection:
        assert connection.execute(
            "SELECT lifecycle_state, lifecycle_revision FROM missions WHERE mission_id = ?",
            (mission_id,),
        ).fetchone() == ("claimed", 2)
        assert connection.execute(
            "SELECT receipt_disposition, evidence_status, failure_reason_code "
            "FROM mission_report_receipts WHERE report_id = ?",
            (report_payload["report_id"],),
        ).fetchone() == (
            "evidence_incomplete",
            "evidence_incomplete",
            "audit_write_failed",
        )
        assert connection.execute(
            "SELECT receipt_disposition, evidence_status FROM mission_report_receipts "
            "WHERE report_id = ?",
            (later_report_payload["report_id"],),
        ).fetchone() == ("quarantined", "complete")
        assert connection.execute(
            "SELECT count(*) FROM mission_transition_attempts "
            "WHERE transition_kind = 'report_pending_evidence'"
        ).fetchone() == (0,)


def test_runner_report_transition_audit_failure_preserves_completed_receipt(
    tmp_path: Path,
) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    private_key = Ed25519PrivateKey.generate()
    claim_payload: JsonObject = {"protocol_version": "1"}
    api = create_app(settings)
    with TestClient(api) as client:
        node_id = _ready_mission_node(
            client,
            settings,
            nonce_prefix="1",
            node_private_key=private_key,
        )
        mission_id = str(
            client.post(
                "/missions",
                headers=admin_headers,
                json={
                    "target_node_id": node_id,
                    "mission_template_id": "synthetic_read_review_v1",
                    "requested_timeout_seconds": 300,
                    "client_request_id": "report-transition-audit-failure-001",
                },
            ).json()["mission_id"]
        )
        claim_path = f"/nodes/{node_id}/mission-claims"
        claim = client.post(
            claim_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=claim_path,
                payload=claim_payload,
                nonce="14" * 16,
            ),
            json=claim_payload,
        ).json()
        real_audit_writer = api.state.mission_report_service.audit_writer

        class FailingTransitionAuditWriter:
            def write_event(self, **kwargs: object) -> object:
                if kwargs.get("event_type") == AuditEventType.MISSION_REPORT_TRANSITION_STAGED:
                    raise AuditWriteError("simulated report transition audit failure")
                return real_audit_writer.write_event(**kwargs)

        api.state.mission_report_service.audit_writer = FailingTransitionAuditWriter()
        report_path = f"/nodes/{node_id}/mission-reports"
        report_payload: JsonObject = {
            "mission_id": mission_id,
            "claim_id": claim["claim_id"],
            "envelope_digest": claim["envelope_digest"],
            "expected_lifecycle_revision": 2,
            "report_id": "mreport_" + ("1" * 32),
            "report_kind": "runner_running",
            "outcome_code": "started",
            "reason_code": None,
            "artifact_digest": None,
        }
        failed = client.post(
            report_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=report_path,
                payload=report_payload,
                nonce="15" * 16,
            ),
            json=report_payload,
        )
        assert failed.status_code == 409
        assert failed.json()["detail"] == "mission report transition audit evidence failed"

    with TestClient(create_app(settings)) as recovered_client:
        blocked_cancel = recovered_client.post(
            f"/missions/{mission_id}/cancel",
            headers=admin_headers,
            json={"client_request_id": "report-transition-recovery-cancel-001"},
        )
        assert blocked_cancel.status_code == 409
        assert blocked_cancel.json()["detail"] == ("mission transition requires evidence recovery")
        later_report_payload: JsonObject = {
            **report_payload,
            "report_id": "mreport_" + ("a" * 32),
        }
        later_report = recovered_client.post(
            report_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=report_path,
                payload=later_report_payload,
                nonce="16" * 16,
            ),
            json=later_report_payload,
        )
        assert later_report.status_code == 200
        assert later_report.json()["receipt"]["receipt_disposition"] == "quarantined"
        assert later_report.json()["gateway_lifecycle_state"] == "claimed"

    with sqlite3.connect(settings.db_path) as connection:
        assert connection.execute(
            "SELECT lifecycle_state, lifecycle_revision FROM missions WHERE mission_id = ?",
            (mission_id,),
        ).fetchone() == ("claimed", 2)
        assert connection.execute(
            "SELECT receipt_disposition, evidence_status FROM mission_report_receipts"
            " WHERE report_id = ?",
            (report_payload["report_id"],),
        ).fetchone() == ("lifecycle_advancing", "complete")
        assert connection.execute(
            "SELECT receipt_disposition, evidence_status FROM mission_report_receipts"
            " WHERE report_id = ?",
            (later_report_payload["report_id"],),
        ).fetchone() == ("quarantined", "complete")
        assert connection.execute(
            "SELECT evidence_status, failure_reason_code FROM mission_transition_attempts "
            "WHERE transition_kind = 'report_pending_evidence'"
        ).fetchone() == ("evidence_incomplete", "audit_write_failed")


def test_incomplete_cancel_observation_transition_quarantines_later_report(
    tmp_path: Path,
) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    private_key = Ed25519PrivateKey.generate()
    claim_payload: JsonObject = {"protocol_version": "1"}
    api = create_app(settings)
    with TestClient(api) as client:
        node_id = _ready_mission_node(
            client,
            settings,
            nonce_prefix="a",
            node_private_key=private_key,
        )
        mission_id = str(
            client.post(
                "/missions",
                headers=admin_headers,
                json={
                    "target_node_id": node_id,
                    "mission_template_id": "synthetic_read_review_v1",
                    "requested_timeout_seconds": 300,
                    "client_request_id": "cancel-observation-evidence-failure-001",
                },
            ).json()["mission_id"]
        )
        claim_path = f"/nodes/{node_id}/mission-claims"
        claim = client.post(
            claim_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=claim_path,
                payload=claim_payload,
                nonce="a4" * 16,
            ),
            json=claim_payload,
        ).json()
        report_path = f"/nodes/{node_id}/mission-reports"
        running_payload: JsonObject = {
            "mission_id": mission_id,
            "claim_id": claim["claim_id"],
            "envelope_digest": claim["envelope_digest"],
            "expected_lifecycle_revision": 2,
            "report_id": "mreport_" + ("1" * 32),
            "report_kind": "runner_running",
            "outcome_code": "started",
            "reason_code": None,
            "artifact_digest": None,
        }
        running = client.post(
            report_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=report_path,
                payload=running_payload,
                nonce="a5" * 16,
            ),
            json=running_payload,
        )
        assert running.json()["gateway_lifecycle_revision"] == 3
        canceled = client.post(
            f"/missions/{mission_id}/cancel",
            headers=admin_headers,
            json={"client_request_id": "cancel-observation-evidence-failure-001"},
        )
        assert canceled.json()["lifecycle_revision"] == 4
        real_audit_writer = api.state.mission_report_service.audit_writer

        class FailingObservationAuditWriter:
            def write_event(self, **kwargs: object) -> object:
                if kwargs.get("event_type") == AuditEventType.MISSION_CONTROL_OBSERVATION_STAGED:
                    raise AuditWriteError("simulated control observation audit failure")
                return real_audit_writer.write_event(**kwargs)

        api.state.mission_report_service.audit_writer = FailingObservationAuditWriter()
        observed_payload: JsonObject = {
            **running_payload,
            "expected_lifecycle_revision": 4,
            "report_id": "mreport_" + ("2" * 32),
            "report_kind": "cancel_observed",
            "outcome_code": "cancellation_observed",
        }
        failed_observation = client.post(
            report_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=report_path,
                payload=observed_payload,
                nonce="a6" * 16,
            ),
            json=observed_payload,
        )
        assert failed_observation.status_code == 409
        assert failed_observation.json()["detail"] == (
            "mission report transition audit evidence failed"
        )

    with TestClient(create_app(settings)) as recovered_client:
        later_payload: JsonObject = {
            **running_payload,
            "expected_lifecycle_revision": 4,
            "report_id": "mreport_" + ("3" * 32),
            "report_kind": "runner_canceled",
            "outcome_code": "canceled",
        }
        later = recovered_client.post(
            report_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=report_path,
                payload=later_payload,
                nonce="a7" * 16,
            ),
            json=later_payload,
        )
        assert later.status_code == 200
        assert later.json()["receipt"]["receipt_disposition"] == "quarantined"
        assert later.json()["gateway_lifecycle_state"] == "cancel_requested"
        assert later.json()["gateway_lifecycle_revision"] == 4

    with sqlite3.connect(settings.db_path) as connection:
        assert connection.execute(
            "SELECT evidence_status, failure_reason_code FROM mission_transition_attempts "
            "WHERE transition_kind = 'control_observation_pending_evidence'"
        ).fetchone() == ("evidence_incomplete", "audit_write_failed")
        assert connection.execute(
            "SELECT receipt_disposition, evidence_status FROM mission_report_receipts "
            "WHERE report_id = ?",
            (later_payload["report_id"],),
        ).fetchone() == ("quarantined", "complete")


def test_runner_report_revoked_after_transition_audit_does_not_advance(
    tmp_path: Path,
) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    private_key = Ed25519PrivateKey.generate()
    claim_payload: JsonObject = {"protocol_version": "1"}
    api = create_app(settings)
    with TestClient(api) as client:
        node_id = _ready_mission_node(
            client,
            settings,
            nonce_prefix="0",
            node_private_key=private_key,
        )
        mission_id = str(
            client.post(
                "/missions",
                headers=admin_headers,
                json={
                    "target_node_id": node_id,
                    "mission_template_id": "synthetic_read_review_v1",
                    "requested_timeout_seconds": 300,
                    "client_request_id": "report-final-authority-race-001",
                },
            ).json()["mission_id"]
        )
        claim_path = f"/nodes/{node_id}/mission-claims"
        claim = client.post(
            claim_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=claim_path,
                payload=claim_payload,
                nonce="04" * 16,
            ),
            json=claim_payload,
        ).json()
        real_audit_writer = api.state.mission_report_service.audit_writer

        class RevokingAfterTransitionAuditWriter:
            def write_event(self, **kwargs: object) -> object:
                event = real_audit_writer.write_event(**kwargs)
                if kwargs.get("event_type") == AuditEventType.MISSION_REPORT_TRANSITION_STAGED:
                    with sqlite3.connect(settings.db_path) as connection:
                        connection.execute(
                            "UPDATE nodes SET status = 'revoked' WHERE node_id = ?",
                            (node_id,),
                        )
                        connection.commit()
                return event

        api.state.mission_report_service.audit_writer = RevokingAfterTransitionAuditWriter()
        report_path = f"/nodes/{node_id}/mission-reports"
        report_payload: JsonObject = {
            "mission_id": mission_id,
            "claim_id": claim["claim_id"],
            "envelope_digest": claim["envelope_digest"],
            "expected_lifecycle_revision": 2,
            "report_id": "mreport_" + ("0" * 32),
            "report_kind": "runner_running",
            "outcome_code": "started",
            "reason_code": None,
            "artifact_digest": None,
        }
        failed = client.post(
            report_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=report_path,
                payload=report_payload,
                nonce="05" * 16,
            ),
            json=report_payload,
        )
        assert failed.status_code == 409
        assert failed.json()["detail"] == "mission report transition finalization failed"

    with sqlite3.connect(settings.db_path) as connection:
        assert connection.execute(
            "SELECT lifecycle_state, lifecycle_revision FROM missions WHERE mission_id = ?",
            (mission_id,),
        ).fetchone() == ("claimed", 2)
        assert connection.execute(
            "SELECT receipt_disposition, evidence_status FROM mission_report_receipts"
        ).fetchone() == ("lifecycle_advancing", "complete")
        assert connection.execute(
            "SELECT evidence_status, failure_reason_code FROM mission_transition_attempts "
            "WHERE transition_kind = 'report_pending_evidence'"
        ).fetchone() == ("evidence_incomplete", "finalization_failed")


def test_runner_report_revoked_after_receipt_audit_fails_receipt_closed(
    tmp_path: Path,
) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    private_key = Ed25519PrivateKey.generate()
    claim_payload: JsonObject = {"protocol_version": "1"}
    api = create_app(settings)
    with TestClient(api) as client:
        node_id = _ready_mission_node(
            client,
            settings,
            nonce_prefix="f",
            node_private_key=private_key,
        )
        mission_id = str(
            client.post(
                "/missions",
                headers=admin_headers,
                json={
                    "target_node_id": node_id,
                    "mission_template_id": "synthetic_read_review_v1",
                    "requested_timeout_seconds": 300,
                    "client_request_id": "report-receipt-authority-race-001",
                },
            ).json()["mission_id"]
        )
        claim_path = f"/nodes/{node_id}/mission-claims"
        claim = client.post(
            claim_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=claim_path,
                payload=claim_payload,
                nonce="f4" * 16,
            ),
            json=claim_payload,
        ).json()
        real_audit_writer = api.state.mission_report_service.audit_writer

        class RevokingAfterReceiptAuditWriter:
            def write_event(self, **kwargs: object) -> object:
                event = real_audit_writer.write_event(**kwargs)
                if kwargs.get("event_type") == AuditEventType.MISSION_REPORT_RECEIPT_STAGED:
                    with sqlite3.connect(settings.db_path) as connection:
                        connection.execute(
                            "UPDATE nodes SET status = 'revoked' WHERE node_id = ?",
                            (node_id,),
                        )
                        connection.commit()
                return event

        api.state.mission_report_service.audit_writer = RevokingAfterReceiptAuditWriter()
        report_path = f"/nodes/{node_id}/mission-reports"
        report_payload: JsonObject = {
            "mission_id": mission_id,
            "claim_id": claim["claim_id"],
            "envelope_digest": claim["envelope_digest"],
            "expected_lifecycle_revision": 2,
            "report_id": "mreport_" + ("f" * 32),
            "report_kind": "runner_running",
            "outcome_code": "started",
            "reason_code": None,
            "artifact_digest": None,
        }
        failed = client.post(
            report_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=report_path,
                payload=report_payload,
                nonce="f5" * 16,
            ),
            json=report_payload,
        )
        assert failed.status_code == 409
        assert failed.json()["detail"] == "mission report receipt finalization failed"

    with sqlite3.connect(settings.db_path) as connection:
        assert connection.execute(
            "SELECT lifecycle_state, lifecycle_revision FROM missions WHERE mission_id = ?",
            (mission_id,),
        ).fetchone() == ("claimed", 2)
        assert connection.execute(
            "SELECT receipt_disposition, evidence_status, failure_reason_code "
            "FROM mission_report_receipts"
        ).fetchone() == (
            "evidence_incomplete",
            "evidence_incomplete",
            "finalization_failed",
        )
        assert connection.execute(
            "SELECT count(*) FROM mission_transition_attempts "
            "WHERE transition_kind = 'report_pending_evidence'"
        ).fetchone() == (0,)


def test_completed_runner_report_receipt_tampering_fails_closed(tmp_path: Path) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    private_key = Ed25519PrivateKey.generate()
    claim_payload: JsonObject = {"protocol_version": "1"}
    report_id = "mreport_" + ("e" * 32)
    with TestClient(create_app(settings)) as client:
        node_id = _ready_mission_node(
            client,
            settings,
            nonce_prefix="e",
            node_private_key=private_key,
        )
        mission_id = str(
            client.post(
                "/missions",
                headers=admin_headers,
                json={
                    "target_node_id": node_id,
                    "mission_template_id": "synthetic_read_review_v1",
                    "requested_timeout_seconds": 300,
                    "client_request_id": "report-receipt-tamper-001",
                },
            ).json()["mission_id"]
        )
        claim_path = f"/nodes/{node_id}/mission-claims"
        claim = client.post(
            claim_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=claim_path,
                payload=claim_payload,
                nonce="e4" * 16,
            ),
            json=claim_payload,
        ).json()
        report_path = f"/nodes/{node_id}/mission-reports"
        report_payload: JsonObject = {
            "mission_id": mission_id,
            "claim_id": claim["claim_id"],
            "envelope_digest": claim["envelope_digest"],
            "expected_lifecycle_revision": 2,
            "report_id": report_id,
            "report_kind": "runner_running",
            "outcome_code": "started",
            "reason_code": None,
            "artifact_digest": None,
        }
        accepted = client.post(
            report_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=report_path,
                payload=report_payload,
                nonce="e5" * 16,
            ),
            json=report_payload,
        )
        assert accepted.status_code == 200

    store = MissionStore(settings.db_path)
    store.initialize()
    with sqlite3.connect(settings.db_path) as connection:
        original = connection.execute(
            "SELECT verified_node_identity_key_id, receipt_posture_json, "
            "receipt_disposition, audit_event_hash FROM mission_report_receipts "
            "WHERE report_id = ?",
            (report_id,),
        ).fetchone()
    posture = json.loads(str(original[1]))
    posture["proposed_advancement"]["reason_code"] = "authority_drift"
    mutations = (
        ("verified_node_identity_key_id", "sha256:" + ("0" * 64), original[0]),
        (
            "receipt_posture_json",
            json.dumps(posture, sort_keys=True, separators=(",", ":")),
            original[1],
        ),
        ("receipt_disposition", "quarantined", original[2]),
        ("audit_event_hash", "sha256:" + ("0" * 64), original[3]),
    )
    for column, tampered, restored in mutations:
        with sqlite3.connect(settings.db_path) as connection:
            connection.execute(
                f"UPDATE mission_report_receipts SET {column} = ? WHERE report_id = ?",
                (tampered, report_id),
            )
            connection.commit()
        with pytest.raises(MissionError, match="stored mission report"):
            store.get_report_receipt(report_id)
        with sqlite3.connect(settings.db_path) as connection:
            connection.execute(
                f"UPDATE mission_report_receipts SET {column} = ? WHERE report_id = ?",
                (restored, report_id),
            )
            connection.commit()
        assert store.get_report_receipt(report_id).report.report_id == report_id

    transition = store.get_report_transition(report_id)
    assert transition is not None
    assert transition.audit_event_id is not None
    with sqlite3.connect(settings.db_path) as connection:
        original_transition_hash = connection.execute(
            "SELECT audit_event_hash FROM mission_transition_attempts WHERE transition_id = ?",
            (transition.transition_id,),
        ).fetchone()[0]
        original_transition_event = connection.execute(
            "SELECT payload_json FROM audit_events WHERE event_id = ?",
            (transition.audit_event_id,),
        ).fetchone()[0]
        connection.execute(
            "UPDATE mission_transition_attempts SET audit_event_hash = ? WHERE transition_id = ?",
            ("sha256:" + ("0" * 64), transition.transition_id),
        )
        connection.commit()
    with pytest.raises(MissionError, match="stored mission audit evidence binding"):
        store.get_report_transition(report_id)
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute(
            "UPDATE mission_transition_attempts SET audit_event_hash = ? WHERE transition_id = ?",
            (original_transition_hash, transition.transition_id),
        )
        tampered_event = json.loads(str(original_transition_event))
        tampered_event["input_hash"] = "sha256:" + ("0" * 64)
        connection.execute(
            "UPDATE audit_events SET payload_json = ? WHERE event_id = ?",
            (
                json.dumps(tampered_event, sort_keys=True, separators=(",", ":")),
                transition.audit_event_id,
            ),
        )
        connection.commit()
    with pytest.raises(MissionError, match="transition audit event binding"):
        store.get_report_transition(report_id)
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute(
            "UPDATE audit_events SET payload_json = ? WHERE event_id = ?",
            (original_transition_event, transition.audit_event_id),
        )
        connection.commit()
    assert store.get_report_transition(report_id) == transition


def test_late_success_across_exact_cancellation_revision_advances_once(
    tmp_path: Path,
) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    private_key = Ed25519PrivateKey.generate()
    claim_payload: JsonObject = {"protocol_version": "1"}
    with TestClient(create_app(settings)) as client:
        node_id = _ready_mission_node(
            client,
            settings,
            nonce_prefix="2",
            node_private_key=private_key,
        )
        mission_id = str(
            client.post(
                "/missions",
                headers=admin_headers,
                json={
                    "target_node_id": node_id,
                    "mission_template_id": "synthetic_read_review_v1",
                    "requested_timeout_seconds": 300,
                    "client_request_id": "late-success-cancel-race-001",
                },
            ).json()["mission_id"]
        )
        claim_path = f"/nodes/{node_id}/mission-claims"
        claim = client.post(
            claim_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=claim_path,
                payload=claim_payload,
                nonce="24" * 16,
            ),
            json=claim_payload,
        ).json()
        report_path = f"/nodes/{node_id}/mission-reports"
        base_report: JsonObject = {
            "mission_id": mission_id,
            "claim_id": claim["claim_id"],
            "envelope_digest": claim["envelope_digest"],
            "expected_lifecycle_revision": 2,
            "report_id": "mreport_" + ("2" * 32),
            "report_kind": "runner_running",
            "outcome_code": "started",
            "reason_code": None,
            "artifact_digest": None,
        }
        running = client.post(
            report_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=report_path,
                payload=base_report,
                nonce="25" * 16,
            ),
            json=base_report,
        )
        assert running.json()["gateway_lifecycle_revision"] == 3
        canceled = client.post(
            f"/missions/{mission_id}/cancel",
            headers=admin_headers,
            json={"client_request_id": "late-success-cancel-001"},
        )
        assert canceled.json()["lifecycle_revision"] == 4
        success_payload: JsonObject = {
            **base_report,
            "expected_lifecycle_revision": 3,
            "report_id": "mreport_" + ("8" * 32),
            "report_kind": "runner_succeeded",
            "outcome_code": "succeeded",
            "artifact_digest": "sha256:" + ("8" * 64),
        }
        succeeded = client.post(
            report_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=report_path,
                payload=success_payload,
                nonce="26" * 16,
            ),
            json=success_payload,
        )
        assert succeeded.status_code == 200
        assert succeeded.json()["gateway_lifecycle_state"] == "runner_reported_succeeded"
        assert succeeded.json()["gateway_lifecycle_revision"] == 5
        contradictory_payload: JsonObject = {
            **base_report,
            "expected_lifecycle_revision": 4,
            "report_id": "mreport_" + ("9" * 32),
            "report_kind": "runner_failed",
            "outcome_code": "failed",
            "reason_code": "runner_error",
        }
        contradictory = client.post(
            report_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=report_path,
                payload=contradictory_payload,
                nonce="27" * 16,
            ),
            json=contradictory_payload,
        )
        assert contradictory.status_code == 200
        assert contradictory.json()["receipt"]["receipt_disposition"] == "quarantined"
        assert contradictory.json()["gateway_lifecycle_state"] == "runner_reported_succeeded"
        assert contradictory.json()["gateway_lifecycle_revision"] == 5
        cockpit = client.get(f"/missions/{mission_id}", headers=admin_headers).json()
        assert cockpit["runner_reports"]["quarantined_count"] == 1
        assert cockpit["runner_reports"]["report_conflict_count"] == 1
        assert cockpit["attention_codes"] == ["quarantine", "report_conflict"]


def test_concurrent_runner_report_and_cancellation_have_only_evidence_complete_outcomes(
    tmp_path: Path,
) -> None:
    def submit_report(
        client: TestClient,
        start: Event,
        private_key: Ed25519PrivateKey,
        node_id: str,
        report_path: str,
        report_payload: JsonObject,
    ) -> tuple[int, JsonObject]:
        start.wait(timeout=2)
        response = client.post(
            report_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=report_path,
                payload=report_payload,
                nonce="e5" * 16,
            ),
            json=report_payload,
        )
        return response.status_code, cast(JsonObject, response.json())

    def submit_cancel(
        client: TestClient,
        start: Event,
        mission_id: str,
        admin_headers: dict[str, str],
        iteration: int,
    ) -> tuple[int, JsonObject]:
        start.wait(timeout=2)
        response = client.post(
            f"/missions/{mission_id}/cancel",
            headers=admin_headers,
            json={"client_request_id": f"report-cancel-race-{iteration}"},
        )
        return response.status_code, cast(JsonObject, response.json())

    for iteration in range(6):
        iteration_path = tmp_path / str(iteration)
        iteration_path.mkdir()
        settings = _mission_ready_settings(iteration_path)
        admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
        private_key = Ed25519PrivateKey.generate()
        claim_payload: JsonObject = {"protocol_version": "1"}
        with TestClient(create_app(settings)) as client:
            node_id = _ready_mission_node(
                client,
                settings,
                nonce_prefix="e",
                node_private_key=private_key,
            )
            mission_id = str(
                client.post(
                    "/missions",
                    headers=admin_headers,
                    json={
                        "target_node_id": node_id,
                        "mission_template_id": "synthetic_read_review_v1",
                        "requested_timeout_seconds": 300,
                        "client_request_id": f"report-cancel-race-{iteration}",
                    },
                ).json()["mission_id"]
            )
            claim_path = f"/nodes/{node_id}/mission-claims"
            claim = client.post(
                claim_path,
                headers=_signed_node_headers(
                    private_key,
                    node_id=node_id,
                    path=claim_path,
                    payload=claim_payload,
                    nonce="e4" * 16,
                ),
                json=claim_payload,
            ).json()
            report_path = f"/nodes/{node_id}/mission-reports"
            report_payload: JsonObject = {
                "mission_id": mission_id,
                "claim_id": claim["claim_id"],
                "envelope_digest": claim["envelope_digest"],
                "expected_lifecycle_revision": 2,
                "report_id": "mreport_" + f"{iteration + 1:032x}",
                "report_kind": "runner_running",
                "outcome_code": "started",
                "reason_code": None,
                "artifact_digest": None,
            }
            start = Event()

            with ThreadPoolExecutor(max_workers=2) as executor:
                report_future = executor.submit(
                    submit_report,
                    client,
                    start,
                    private_key,
                    node_id,
                    report_path,
                    report_payload,
                )
                cancel_future = executor.submit(
                    submit_cancel,
                    client,
                    start,
                    mission_id,
                    admin_headers,
                    iteration,
                )
                start.set()
                report_status, report_body = report_future.result()
                cancel_status, cancel_body = cancel_future.result()

            assert report_status == 200, report_body
            assert cancel_status in {200, 409}, cancel_body
            if cancel_status == 409:
                assert cancel_body["detail"] in {
                    "mission report receipt requires evidence recovery",
                    "mission transition requires evidence recovery",
                }

        store = MissionStore(settings.db_path)
        receipt = store.get_report_receipt(str(report_payload["report_id"]))
        assert receipt.evidence_status == "complete"
        assert receipt.receipt_disposition in {"lifecycle_advancing", "quarantined"}
        mission = store.get(mission_id)
        assert (mission.lifecycle_state, mission.lifecycle_revision) in {
            ("runner_reported_running", 3),
            ("cancel_requested", 3),
            ("cancel_requested", 4),
        }
        with sqlite3.connect(settings.db_path) as connection:
            evidence_counts = connection.execute(
                "SELECT evidence_status, count(*) FROM mission_transition_attempts "
                "WHERE mission_id = ? GROUP BY evidence_status",
                (mission_id,),
            ).fetchall()
            transition_ids = [
                str(row[0])
                for row in connection.execute(
                    "SELECT transition_id FROM mission_transition_attempts WHERE mission_id = ?",
                    (mission_id,),
                ).fetchall()
            ]
        assert evidence_counts == [("complete", len(transition_ids))]
        for transition_id in transition_ids:
            assert store.get_transition(transition_id).evidence_status == "complete"


def test_signed_node_claim_revoked_after_audit_is_not_delivered(tmp_path: Path) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    private_key = Ed25519PrivateKey.generate()
    claim_payload: JsonObject = {"protocol_version": "1"}
    api = create_app(settings)
    with TestClient(api) as client:
        node_id = _ready_mission_node(
            client,
            settings,
            nonce_prefix="6",
            node_private_key=private_key,
        )
        admitted = client.post(
            "/missions",
            headers=admin_headers,
            json={
                "target_node_id": node_id,
                "mission_template_id": "synthetic_read_review_v1",
                "requested_timeout_seconds": 300,
                "client_request_id": "claim-final-authority-race-001",
            },
        )
        assert admitted.status_code == 200
        real_audit_writer = api.state.mission_claim_service.audit_writer

        class RevokingAfterAuditWriter:
            def write_event(self, **kwargs: object) -> object:
                event = real_audit_writer.write_event(**kwargs)
                with sqlite3.connect(settings.db_path) as connection:
                    connection.execute(
                        "UPDATE nodes SET status = 'revoked' WHERE node_id = ?",
                        (node_id,),
                    )
                    connection.commit()
                return event

        api.state.mission_claim_service.audit_writer = RevokingAfterAuditWriter()
        claim_path = f"/nodes/{node_id}/mission-claims"
        failed = client.post(
            claim_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=claim_path,
                payload=claim_payload,
                nonce="64" * 16,
            ),
            json=claim_payload,
        )

        assert failed.status_code == 409
        assert failed.json()["detail"] == "mission claim finalization failed"
        assert "template_payload" not in failed.text

    with sqlite3.connect(settings.db_path) as connection:
        assert connection.execute(
            "SELECT lifecycle_state, lifecycle_revision FROM missions"
        ).fetchone() == ("queued", 1)
        assert connection.execute("SELECT claim_status FROM mission_claims").fetchone() == (
            "evidence_incomplete",
        )
        transition = connection.execute(
            "SELECT transition_id, evidence_status, failure_reason_code "
            "FROM mission_transition_attempts "
            "WHERE transition_kind = 'claim_pending_evidence'"
        ).fetchone()
        assert transition[1:] == ("evidence_incomplete", "finalization_failed")
        assert connection.execute(
            "SELECT count(*) FROM mission_audit_evidence_bindings WHERE owner_id = ?",
            (transition[0],),
        ).fetchone() == (0,)


@pytest.mark.parametrize(
    ("mutation_sql", "parameters", "expected_status"),
    (
        (
            "UPDATE nodes SET last_seen_at = ? WHERE node_id = ?",
            ("2020-01-01T00:00:00+00:00",),
            409,
        ),
        ("UPDATE nodes SET status = 'revoked' WHERE node_id = ?", (), 401),
        (
            "UPDATE nodes SET last_configuration_digest = ? WHERE node_id = ?",
            ("sha256:" + ("9" * 64),),
            409,
        ),
        ("UPDATE nodes SET last_node_version = '0.0.1' WHERE node_id = ?", (), 409),
        (
            "UPDATE nodes SET configuration_acknowledgment_status = NULL WHERE node_id = ?",
            (),
            409,
        ),
    ),
)
def test_signed_node_claim_ineligible_postures_have_zero_claim_effects(
    tmp_path: Path,
    mutation_sql: str,
    parameters: tuple[object, ...],
    expected_status: int,
) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    private_key = Ed25519PrivateKey.generate()
    claim_payload: JsonObject = {"protocol_version": "1"}
    with TestClient(create_app(settings)) as client:
        node_id = _ready_mission_node(
            client,
            settings,
            nonce_prefix="b",
            node_private_key=private_key,
        )
        admitted = client.post(
            "/missions",
            headers=admin_headers,
            json={
                "target_node_id": node_id,
                "mission_template_id": "synthetic_read_review_v1",
                "requested_timeout_seconds": 300,
                "client_request_id": "ineligible-claim-mission-001",
            },
        )
        assert admitted.status_code == 200
        with sqlite3.connect(settings.db_path) as connection:
            connection.execute(mutation_sql, (*parameters, node_id))
            connection.commit()
        claim_path = f"/nodes/{node_id}/mission-claims"
        denied = client.post(
            claim_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=claim_path,
                payload=claim_payload,
                nonce="b4" * 16,
            ),
            json=claim_payload,
        )
        assert denied.status_code == expected_status
        assert "template_payload" not in denied.text

    with sqlite3.connect(settings.db_path) as connection:
        assert connection.execute("SELECT count(*) FROM mission_claims").fetchone() == (0,)
        assert connection.execute(
            "SELECT count(*) FROM mission_transition_attempts "
            "WHERE transition_kind = 'claim_pending_evidence'"
        ).fetchone() == (0,)


def test_mission_claim_expiry_reconciler_runs_without_request_traffic_and_restarts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _mission_ready_settings(tmp_path)
    observed = Event()
    original = MissionClaimService.reconcile_expired_claims

    def observe_reconciliation(
        self: MissionClaimService,
        *,
        now: datetime | None = None,
    ) -> int:
        observed.set()
        return original(self, now=now)

    monkeypatch.setattr(
        MissionClaimService,
        "reconcile_expired_claims",
        observe_reconciliation,
    )

    first_api = create_app(settings)
    with TestClient(first_api):
        assert observed.wait(timeout=2)
        first_task = first_api.state.mission_claim_reconciliation_task
        assert first_task.done() is False
    assert first_task.cancelled() is True

    observed.clear()
    restarted_api = create_app(settings)
    with TestClient(restarted_api):
        assert observed.wait(timeout=2)
        restarted_task = restarted_api.state.mission_claim_reconciliation_task
        assert restarted_task.done() is False
    assert restarted_task.cancelled() is True


def test_claim_expiry_reconciliation_enters_attention_without_requeue(
    tmp_path: Path,
) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    private_key = Ed25519PrivateKey.generate()
    claim_payload: JsonObject = {"protocol_version": "1"}
    api = create_app(settings)
    with TestClient(api) as client:
        node_id = _ready_mission_node(
            client,
            settings,
            nonce_prefix="c",
            node_private_key=private_key,
        )
        admitted = client.post(
            "/missions",
            headers=admin_headers,
            json={
                "target_node_id": node_id,
                "mission_template_id": "synthetic_read_review_v1",
                "requested_timeout_seconds": 60,
                "client_request_id": "claim-expiry-mission-001",
            },
        )
        assert admitted.status_code == 200
        second_admission = client.post(
            "/missions",
            headers=admin_headers,
            json={
                "target_node_id": node_id,
                "mission_template_id": "synthetic_read_review_v1",
                "requested_timeout_seconds": 60,
                "client_request_id": "claim-expiry-mission-002",
            },
        )
        assert second_admission.status_code == 200
        claim_path = f"/nodes/{node_id}/mission-claims"
        delivered = client.post(
            claim_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=claim_path,
                payload=claim_payload,
                nonce="c4" * 16,
            ),
            json=claim_payload,
        )
        assert delivered.status_code == 200
        mission_id = str(delivered.json()["mission_id"])
        expiry = datetime.fromisoformat(str(delivered.json()["claim_expires_at"]))

        reconciled = api.state.mission_claim_service.reconcile_expired_claims(
            now=expiry + timedelta(microseconds=1)
        )

        assert reconciled == 1
        detail = client.get(f"/missions/{mission_id}", headers=admin_headers)
        assert detail.status_code == 200
        assert detail.json()["lifecycle_state"] == "claim_expired_review_required"
        assert detail.json()["lifecycle_revision"] == 3
        assert (
            api.state.mission_claim_service.reconcile_expired_claims(now=expiry + timedelta(days=1))
            == 0
        )
        no_requeue = client.post(
            claim_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=claim_path,
                payload=claim_payload,
                nonce="c5" * 16,
            ),
            json=claim_payload,
        )
        assert no_requeue.status_code == 409
        assert no_requeue.json()["detail"] == "Node already has unresolved mission delivery"
        assert "template_payload" not in no_requeue.text

    with sqlite3.connect(settings.db_path) as connection:
        assert connection.execute("SELECT claim_status FROM mission_claims").fetchone() == (
            "expired_review_required",
        )
        assert connection.execute(
            "SELECT count(*) FROM mission_transition_attempts "
            "WHERE transition_kind = 'claim_expiry_pending_evidence' "
            "AND evidence_status = 'complete'"
        ).fetchone() == (1,)


def test_claim_expiry_audit_failure_preserves_claimed_state(tmp_path: Path) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    private_key = Ed25519PrivateKey.generate()
    claim_payload: JsonObject = {"protocol_version": "1"}
    api = create_app(settings)
    with TestClient(api) as client:
        node_id = _ready_mission_node(
            client,
            settings,
            nonce_prefix="d",
            node_private_key=private_key,
        )
        admitted = client.post(
            "/missions",
            headers=admin_headers,
            json={
                "target_node_id": node_id,
                "mission_template_id": "synthetic_read_review_v1",
                "requested_timeout_seconds": 60,
                "client_request_id": "claim-expiry-audit-failure-001",
            },
        )
        mission_id = str(admitted.json()["mission_id"])
        claim_path = f"/nodes/{node_id}/mission-claims"
        delivered = client.post(
            claim_path,
            headers=_signed_node_headers(
                private_key,
                node_id=node_id,
                path=claim_path,
                payload=claim_payload,
                nonce="d4" * 16,
            ),
            json=claim_payload,
        )
        expiry = datetime.fromisoformat(str(delivered.json()["claim_expires_at"]))

        class FailingAuditWriter:
            def write_event(self, **_: object) -> None:
                raise AuditWriteError("simulated claim expiry audit failure")

        api.state.mission_claim_service.audit_writer = FailingAuditWriter()
        with pytest.raises(MissionClaimError, match="expiry audit evidence failed"):
            api.state.mission_claim_service.reconcile_expired_claims(
                now=expiry + timedelta(microseconds=1)
            )

    with sqlite3.connect(settings.db_path) as connection:
        assert connection.execute(
            "SELECT lifecycle_state, lifecycle_revision FROM missions WHERE mission_id = ?",
            (mission_id,),
        ).fetchone() == ("claimed", 2)
        assert connection.execute(
            "SELECT claim_status FROM mission_claims WHERE mission_id = ?",
            (mission_id,),
        ).fetchone() == ("delivered",)
        assert connection.execute(
            "SELECT evidence_status, failure_reason_code FROM mission_transition_attempts "
            "WHERE transition_kind = 'claim_expiry_pending_evidence'"
        ).fetchone() == ("evidence_incomplete", "audit_write_failed")


@pytest.mark.parametrize(
    ("mutation_sql", "parameters"),
    (
        ("UPDATE nodes SET last_seen_at = ? WHERE node_id = ?", ("2020-01-01T00:00:00+00:00",)),
        ("UPDATE nodes SET status = 'revoked' WHERE node_id = ?", ()),
        (
            "UPDATE nodes SET last_configuration_digest = ? WHERE node_id = ?",
            ("sha256:" + ("9" * 64),),
        ),
        ("UPDATE nodes SET last_node_version = '0.0.1' WHERE node_id = ?", ()),
        ("UPDATE nodes SET evidence_status = 'pending' WHERE node_id = ?", ()),
        (
            "UPDATE nodes SET configuration_acknowledgment_status = NULL WHERE node_id = ?",
            (),
        ),
    ),
)
def test_mission_admission_denied_postures_have_zero_effects(
    tmp_path: Path,
    mutation_sql: str,
    parameters: tuple[object, ...],
) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    with TestClient(create_app(settings)) as client:
        node_id = _ready_mission_node(client, settings, nonce_prefix="f")
        with sqlite3.connect(settings.db_path) as connection:
            connection.execute(mutation_sql, (*parameters, node_id))
            connection.commit()
        denied = client.post(
            "/missions",
            headers=admin_headers,
            json={
                "target_node_id": node_id,
                "mission_template_id": "synthetic_read_review_v1",
                "requested_timeout_seconds": 300,
                "client_request_id": "denied-mission-001",
            },
        )
        assert denied.status_code == 409
        assert client.get("/missions", headers=admin_headers).json()["count"] == 0
    with sqlite3.connect(settings.db_path) as connection:
        assert connection.execute("SELECT count(*) FROM missions").fetchone() == (0,)
        assert connection.execute(
            "SELECT count(*) FROM mission_transition_attempts"
        ).fetchone() == (0,)


def test_mission_admission_audit_failure_remains_unadmitted_and_recovery_required(
    tmp_path: Path,
) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    api = create_app(settings)
    with TestClient(api) as client:
        node_id = _ready_mission_node(client, settings, nonce_prefix="a")

        class FailingAuditWriter:
            def write_event(self, **_: object) -> None:
                raise AuditWriteError("simulated mission audit failure")

        api.state.mission_admission_service.audit_writer = FailingAuditWriter()
        payload = {
            "target_node_id": node_id,
            "mission_template_id": "synthetic_read_review_v1",
            "requested_timeout_seconds": 300,
            "client_request_id": "audit-failure-mission-001",
        }
        failed = client.post("/missions", headers=admin_headers, json=payload)
        assert failed.status_code == 409
        assert failed.json()["detail"] == "mission transition audit evidence failed"
        assert client.get("/missions", headers=admin_headers).json()["count"] == 0
        retry = client.post("/missions", headers=admin_headers, json=payload)
        assert retry.status_code == 409
        assert retry.json()["detail"] == "mission admission requires evidence recovery"

    with sqlite3.connect(settings.db_path) as connection:
        assert connection.execute(
            "SELECT lifecycle_state, lifecycle_revision FROM missions"
        ).fetchone() == ("unadmitted", 0)
        assert connection.execute(
            "SELECT evidence_status, failure_reason_code FROM mission_transition_attempts"
        ).fetchone() == ("evidence_incomplete", "audit_write_failed")
        assert connection.execute(
            "SELECT count(*) FROM mission_audit_evidence_bindings"
        ).fetchone() == (0,)


def test_mission_admission_audit_failure_after_jsonl_append_rolls_back_audit_commit(
    tmp_path: Path,
) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    api = create_app(settings)
    with TestClient(api) as client:
        node_id = _ready_mission_node(client, settings, nonce_prefix="c")
        with sqlite3.connect(settings.db_path) as connection:
            audit_count_before = int(
                connection.execute("SELECT count(*) FROM audit_events").fetchone()[0]
            )
        jsonl_count_before = len(settings.audit_log_path.read_text(encoding="utf-8").splitlines())

        class FailAfterJsonlAppendAuditWriter(AuditWriter):
            def _persist_event(
                self,
                connection: sqlite3.Connection,
                event: Any,
            ) -> None:
                super()._persist_event(connection, event)
                raise sqlite3.OperationalError("simulated interruption after JSONL append")

        api.state.mission_admission_service.audit_writer = FailAfterJsonlAppendAuditWriter(
            settings.db_path,
            settings.audit_log_path,
        )
        failed = client.post(
            "/missions",
            headers=admin_headers,
            json={
                "target_node_id": node_id,
                "mission_template_id": "synthetic_read_review_v1",
                "requested_timeout_seconds": 300,
                "client_request_id": "after-jsonl-append-001",
            },
        )

        assert failed.status_code == 409
        assert failed.json()["detail"] == "mission transition audit evidence failed"
        assert len(settings.audit_log_path.read_text(encoding="utf-8").splitlines()) == (
            jsonl_count_before + 1
        )
        with pytest.raises(AuditWriteError, match="lifecycle recovery is required"):
            AuditWriter(settings.db_path, settings.audit_log_path).write_event(
                event_id="evt_" + ("9" * 32),
                event_type=AuditEventType.MISSION_ADMISSION_STAGED,
                request_id="after-jsonl-append-followup",
                principal={"id": "admin:local-ui", "roles": ["Admin"]},
            )
        assert len(settings.audit_log_path.read_text(encoding="utf-8").splitlines()) == (
            jsonl_count_before + 1
        )

    with sqlite3.connect(settings.db_path) as connection:
        assert connection.execute("SELECT count(*) FROM audit_events").fetchone() == (
            audit_count_before,
        )
        assert connection.execute(
            "SELECT lifecycle_state, lifecycle_revision FROM missions"
        ).fetchone() == ("unadmitted", 0)
        assert connection.execute(
            "SELECT evidence_status, failure_reason_code FROM mission_transition_attempts"
        ).fetchone() == ("evidence_incomplete", "audit_write_failed")


def test_mission_admission_audit_failure_after_audit_commit_remains_unadmitted(
    tmp_path: Path,
) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    api = create_app(settings)
    with TestClient(api) as client:
        node_id = _ready_mission_node(client, settings, nonce_prefix="d")
        real_audit_writer = api.state.mission_admission_service.audit_writer

        class FailAfterAuditCommitWriter:
            def write_event(self, **kwargs: object) -> None:
                real_audit_writer.write_event(**kwargs)
                raise AuditWriteError("simulated interruption after audit commit")

        api.state.mission_admission_service.audit_writer = FailAfterAuditCommitWriter()
        failed = client.post(
            "/missions",
            headers=admin_headers,
            json={
                "target_node_id": node_id,
                "mission_template_id": "synthetic_read_review_v1",
                "requested_timeout_seconds": 300,
                "client_request_id": "after-audit-commit-001",
            },
        )

        assert failed.status_code == 409
        assert failed.json()["detail"] == "mission transition audit evidence failed"

    with sqlite3.connect(settings.db_path) as connection:
        assert connection.execute(
            "SELECT lifecycle_state, lifecycle_revision FROM missions"
        ).fetchone() == ("unadmitted", 0)
        assert connection.execute(
            "SELECT evidence_status, failure_reason_code FROM mission_transition_attempts"
        ).fetchone() == ("evidence_incomplete", "audit_write_failed")
        assert connection.execute(
            "SELECT count(*) FROM audit_events WHERE event_type = 'mission.admission.staged'"
        ).fetchone() == (1,)
        assert connection.execute(
            "SELECT count(*) FROM mission_audit_evidence_bindings"
        ).fetchone() == (0,)


def test_mission_admission_requires_exact_startup_tool_authority(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    settings.require_manifest_lock = True
    settings.workspace_root.mkdir(parents=True, exist_ok=True)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    with TestClient(create_app(settings)) as client:
        node_id = _ready_mission_node(client, settings, nonce_prefix="b")
        denied = client.post(
            "/missions",
            headers=admin_headers,
            json={
                "target_node_id": node_id,
                "mission_template_id": "synthetic_read_review_v1",
                "requested_timeout_seconds": 300,
                "client_request_id": "missing-tool-authority-001",
            },
        )
        assert denied.status_code == 503
        assert denied.json()["detail"] == "mission tool authority is unavailable"
        assert client.get("/missions", headers=admin_headers).json()["count"] == 0


def test_mission_admission_manifest_lock_drift_has_zero_effects(tmp_path: Path) -> None:
    settings = _mission_ready_settings(tmp_path)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    with TestClient(create_app(settings)) as client:
        node_id = _ready_mission_node(client, settings, nonce_prefix="c")
        lock_document = json.loads(settings.manifest_lock_path.read_text(encoding="utf-8"))
        lock_document["authority_note"] = "post-startup-tamper"
        settings.manifest_lock_path.write_text(
            json.dumps(lock_document, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        denied = client.post(
            "/missions",
            headers=admin_headers,
            json={
                "target_node_id": node_id,
                "mission_template_id": "synthetic_read_review_v1",
                "requested_timeout_seconds": 300,
                "client_request_id": "manifest-drift-mission-001",
            },
        )
        assert denied.status_code == 503
        assert denied.json()["detail"] == "mission manifest authority is unavailable"
        assert client.get("/missions", headers=admin_headers).json()["count"] == 0

    with sqlite3.connect(settings.db_path) as connection:
        assert connection.execute("SELECT count(*) FROM missions").fetchone() == (0,)
        assert connection.execute(
            "SELECT count(*) FROM mission_transition_attempts"
        ).fetchone() == (0,)


def test_mission_admission_pins_the_lock_document_verified_with_the_registry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _mission_ready_settings(tmp_path)
    registry_module_any = cast(Any, registry_module)
    original_verify = registry_module_any.verify_manifest_lock

    def verify_then_replace_lock(
        *,
        manifest_dir: Path,
        lock_path: Path,
        records: list[ManifestLockRecord],
    ) -> str:
        verified_digest = cast(
            str,
            original_verify(
                manifest_dir=manifest_dir,
                lock_path=lock_path,
                records=records,
            ),
        )
        replacement = json.loads(lock_path.read_text(encoding="utf-8"))
        replacement["authority_note"] = "replacement-after-registry-verification"
        lock_path.write_text(
            json.dumps(replacement, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return verified_digest

    monkeypatch.setattr(registry_module_any, "verify_manifest_lock", verify_then_replace_lock)
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    with TestClient(create_app(settings)) as client:
        node_id = _ready_mission_node(client, settings, nonce_prefix="d")
        denied = client.post(
            "/missions",
            headers=admin_headers,
            json={
                "target_node_id": node_id,
                "mission_template_id": "synthetic_read_review_v1",
                "requested_timeout_seconds": 300,
                "client_request_id": "startup-lock-replacement-001",
            },
        )
        assert denied.status_code == 503
        assert denied.json()["detail"] == "mission manifest authority is unavailable"

    with sqlite3.connect(settings.db_path) as connection:
        assert connection.execute("SELECT count(*) FROM missions").fetchone() == (0,)
        assert connection.execute(
            "SELECT count(*) FROM mission_transition_attempts"
        ).fetchone() == (0,)


def _mission_ready_settings(tmp_path: Path) -> Settings:
    settings = make_settings(tmp_path)
    shutil.rmtree(settings.manifest_dir)
    shutil.copytree(Path("tool-manifests"), settings.manifest_dir)
    shutil.copyfile(Path("tool-manifests.lock.json"), settings.manifest_lock_path)
    settings.require_manifest_lock = True
    settings.workspace_root.mkdir(parents=True, exist_ok=True)
    return settings


def _ready_mission_node(
    client: TestClient,
    settings: Settings,
    *,
    nonce_prefix: str,
    node_private_key: Ed25519PrivateKey | None = None,
) -> str:
    admin_headers = {"Authorization": f"Bearer {settings.admin_token}"}
    private_key = node_private_key or Ed25519PrivateKey.generate()
    public_key = base64.b64encode(private_key.public_key().public_bytes_raw()).decode()
    issued = client.post(
        "/nodes/enrollment-codes",
        headers=admin_headers,
        json={"workspace_id": "default", "display_name": "Mission Node"},
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
    node_id = str(enrollment.json()["node_id"])
    assigned = client.post(
        f"/nodes/{node_id}/configurations",
        headers=admin_headers,
        json={"minimum_node_version": "0.1.0"},
    )
    assert assigned.status_code == 200
    configuration_request: JsonObject = {"protocol_version": "1", "known_generation": 0}
    configuration_path = f"/nodes/{node_id}/configuration"
    configuration = client.post(
        configuration_path,
        headers=_signed_node_headers(
            private_key,
            node_id=node_id,
            path=configuration_path,
            payload=configuration_request,
            nonce=nonce_prefix + ("1" * 31),
        ),
        json=configuration_request,
    )
    assert configuration.status_code == 200
    bundle = configuration.json()
    acknowledgment: JsonObject = {
        "protocol_version": "1",
        "generation": bundle["generation"],
        "configuration_digest": bundle["configuration_digest"],
        "configuration_signing_key_id": bundle["signature"]["key_id"],
        "active_configuration_signing_key_id": bundle["signature"]["key_id"],
        "status": "stored_not_enforced",
    }
    acknowledgment_path = f"/nodes/{node_id}/configuration/acknowledgments"
    acknowledged = client.post(
        acknowledgment_path,
        headers=_signed_node_headers(
            private_key,
            node_id=node_id,
            path=acknowledgment_path,
            payload=acknowledgment,
            nonce=nonce_prefix + ("2" * 31),
        ),
        json=acknowledgment,
    )
    assert acknowledged.status_code == 200
    heartbeat: JsonObject = {
        "protocol_version": "1",
        "node_version": "0.1.0",
        "runner_adapter": "hermes",
        "deployment_topology": "docker_sidecar",
        "configuration_digest": bundle["configuration_digest"],
    }
    heartbeat_path = f"/nodes/{node_id}/heartbeat"
    accepted = client.post(
        heartbeat_path,
        headers=_signed_node_headers(
            private_key,
            node_id=node_id,
            path=heartbeat_path,
            payload=heartbeat,
            nonce=nonce_prefix + ("3" * 31),
        ),
        json=heartbeat,
    )
    assert accepted.status_code == 200
    return node_id


def _rotate_ready_node_identity_key(
    client: TestClient,
    settings: Settings,
    *,
    node_id: str,
    current_private_key: Ed25519PrivateKey,
    nonce_prefix: str,
) -> Ed25519PrivateKey:
    node = NodeStore(settings.db_path).get(node_id)
    challenge_path = f"/nodes/{node_id}/identity-key-rotation/challenges"
    challenge_payload: JsonObject = {"protocol_version": "1"}
    challenge_response = client.post(
        challenge_path,
        headers=_signed_node_headers(
            current_private_key,
            node_id=node_id,
            path=challenge_path,
            payload=challenge_payload,
            nonce=nonce_prefix + ("1" * 31),
        ),
        json=challenge_payload,
    )
    assert challenge_response.status_code == 200
    challenge = challenge_response.json()
    next_private_key = Ed25519PrivateKey.generate()
    next_public_key = base64.b64encode(next_private_key.public_key().public_bytes_raw()).decode()
    next_key_id = node_identity_key_id(next_public_key)
    rotation = NodeIdentityRotationRecord(
        rotation_id=challenge["rotation_id"],
        node_id=node_id,
        principal_id=node.principal_id,
        workspace_id=node.workspace_id,
        current_key_id=challenge["current_key_id"],
        challenge_digest=sha256_digest(challenge["challenge"]),
        created_at=challenge["created_at"],
        expires_at=challenge["expires_at"],
        status="pending",
        evidence_status="complete",
        next_key_id=None,
        activated_at=None,
    )
    proof = canonical_identity_rotation_proof_message(
        rotation=rotation,
        next_key_id=next_key_id,
    )
    activation_path = f"/nodes/{node_id}/identity-key-rotation/activations"
    activation_payload: JsonObject = {
        "protocol_version": "1",
        "rotation_id": rotation.rotation_id,
        "challenge": challenge["challenge"],
        "next_public_key": next_public_key,
        "next_key_proof": base64.b64encode(next_private_key.sign(proof)).decode(),
    }
    activated = client.post(
        activation_path,
        headers=_signed_node_headers(
            current_private_key,
            node_id=node_id,
            path=activation_path,
            payload=activation_payload,
            nonce=nonce_prefix + ("2" * 31),
        ),
        json=activation_payload,
    )
    assert activated.status_code == 200
    assert activated.json()["active_identity_key_id"] == next_key_id
    return next_private_key


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
    next_trust = generate_node_configuration_signing_keypair(next_private_path, next_public_path)
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
        acknowledgment_path = f"/nodes/{node_id}/configuration-trust-transition/acknowledgments"
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

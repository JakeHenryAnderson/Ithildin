from __future__ import annotations

import pytest
from ithildin_api.promotion_authority import (
    AdminPrincipalContext,
    InputSchemaAuthorityRecord,
    ManifestAuthorityRecord,
    PolicyAuthorityRecord,
    PromotionAuthoritySnapshot,
    RuntimeCandidateRecord,
    SandboxAuthorityRecord,
    TrustedHostAuthorityRecord,
    WorkspaceAuthorityRecord,
)
from ithildin_schemas import JsonObject, sha256_digest
from pydantic import ValidationError

HASH_A = "sha256:" + ("a" * 64)
HASH_B = "sha256:" + ("b" * 64)


def _candidate() -> RuntimeCandidateRecord:
    core: JsonObject = {
        "source_commit": "1" * 40,
        "inventory_schema_version": "1",
        "reviewed_inventory_digest": HASH_A,
        "dependency_lock_digest": HASH_B,
        "release_artifact_digest": "sha256:" + ("c" * 64),
        "evidence_schema_version": "1",
    }
    return RuntimeCandidateRecord(
        posture="reviewed",
        candidate_id=sha256_digest(core),
        source_commit="1" * 40,
        inventory_schema_version="1",
        reviewed_inventory_digest=HASH_A,
        dependency_lock_digest=HASH_B,
        release_artifact_digest="sha256:" + ("c" * 64),
        evidence_schema_version="1",
        review_packet_digest="sha256:" + ("d" * 64),
        authorization_id="rca_test",
    )


def _snapshot() -> PromotionAuthoritySnapshot:
    return PromotionAuthoritySnapshot(
        requesting_principal=AdminPrincipalContext(
            principal_id="admin:local-ui",
            principal_type="admin",
            roles=("Admin", "Approver", "Auditor"),
            authentication_method="local_admin_bearer",
            identity_source="principal_registry",
            identity_generation=HASH_A,
        ),
        trusted_host=TrustedHostAuthorityRecord(
            descriptor_id="thd_test",
            descriptor_hash=HASH_A,
            descriptor_generation=HASH_B,
            registry_schema_digest=HASH_A,
            workspace_id="default",
            staging_label="host-staging://artifact",
        ),
        workspace=WorkspaceAuthorityRecord(
            workspace_id="default",
            workspace_record_hash=HASH_A,
            workspace_registry_generation=HASH_B,
        ),
        sandbox=SandboxAuthorityRecord(
            descriptor_id="sdesc_test",
            descriptor_payload_hash=HASH_A,
            descriptor_generation=HASH_B,
        ),
        policy=PolicyAuthorityRecord(
            engine="yaml",
            document_version="1",
            policy_version="1",
            policy_digest=HASH_A,
            decision="require_approval",
            matched_rules=("trusted-host-promotion",),
            obligations_digest=HASH_B,
        ),
        manifest=ManifestAuthorityRecord(
            lock_version="1",
            lock_digest=HASH_A,
            tool_count=24,
        ),
        input_schema=InputSchemaAuthorityRecord(
            schema_id="trusted-host-promotion-request",
            schema_version="2",
            schema_digest=HASH_B,
        ),
        runtime_candidate=_candidate(),
    )


def test_authority_snapshot_hash_is_deterministic_and_models_are_frozen() -> None:
    first = _snapshot()
    second = PromotionAuthoritySnapshot.model_validate(first.model_dump(mode="json"))

    assert first.snapshot_hash == second.snapshot_hash
    assert first.runtime_candidate.candidate_id_is_valid() is True
    with pytest.raises(ValidationError):
        first.manifest.tool_count = 23  # type: ignore[assignment]


def test_authority_models_reject_unknown_fields_and_wrong_tool_count() -> None:
    payload = _snapshot().model_dump(mode="json")
    payload["caller_principal"] = {"id": "admin:forged"}
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PromotionAuthoritySnapshot.model_validate(payload)

    with pytest.raises(ValidationError):
        ManifestAuthorityRecord.model_validate(
            {"lock_version": "1", "lock_digest": HASH_A, "tool_count": 25}
        )


def test_runtime_candidate_id_does_not_include_review_packet_digest() -> None:
    first = _candidate()
    changed = first.model_copy(update={"review_packet_digest": HASH_A})

    assert first.candidate_id == changed.candidate_id
    assert changed.candidate_id_is_valid() is True

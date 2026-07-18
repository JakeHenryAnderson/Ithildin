"""Immutable server-owned authority records for trusted-host promotion."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal, cast

from ithildin_schemas import JsonObject, sha256_digest
from ithildin_schemas.models import SHA256_PATTERN, StrictBaseModel
from pydantic import ConfigDict, Field


class FrozenAuthorityModel(StrictBaseModel):
    """Closed immutable base for authority evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> JsonObject:
        return cast(JsonObject, self.model_dump(mode="json"))

    def canonical_hash(self) -> str:
        return sha256_digest(self.canonical_payload())


class PromotionReadinessReason(StrEnum):
    READY = "ready"
    UNREVIEWED_LOCAL = "unreviewed_local"
    GOVERNANCE_BINDING_INCOMPLETE = "governance_binding_incomplete"
    CANDIDATE_AUTHORIZATION_UNAVAILABLE = "candidate_authorization_unavailable"
    CANDIDATE_VERIFICATION_FAILED = "candidate_verification_failed"


class AdminPrincipalContext(FrozenAuthorityModel):
    principal_id: Literal["admin:local-ui"]
    principal_type: Literal["admin"]
    roles: tuple[str, ...]
    authentication_method: Literal["local_admin_bearer"]
    identity_source: Literal["principal_registry"]
    identity_generation: str = Field(pattern=SHA256_PATTERN)


class WorkspaceAuthorityRecord(FrozenAuthorityModel):
    workspace_id: str = Field(min_length=1, max_length=128)
    workspace_record_hash: str = Field(pattern=SHA256_PATTERN)
    workspace_registry_generation: str = Field(pattern=SHA256_PATTERN)


class SandboxAuthorityRecord(FrozenAuthorityModel):
    descriptor_id: str = Field(min_length=1, max_length=128)
    descriptor_payload_hash: str = Field(pattern=SHA256_PATTERN)
    descriptor_generation: str = Field(pattern=SHA256_PATTERN)


class TrustedHostAuthorityRecord(FrozenAuthorityModel):
    descriptor_id: str = Field(min_length=1, max_length=128)
    descriptor_hash: str = Field(pattern=SHA256_PATTERN)
    descriptor_generation: str = Field(pattern=SHA256_PATTERN)
    registry_schema_digest: str = Field(pattern=SHA256_PATTERN)
    workspace_id: str = Field(min_length=1, max_length=128)
    staging_label: str = Field(min_length=1, max_length=128)


class PolicyAuthorityRecord(FrozenAuthorityModel):
    engine: Literal["yaml"]
    document_version: str = Field(min_length=1, max_length=128)
    policy_version: str = Field(min_length=1, max_length=128)
    policy_digest: str = Field(pattern=SHA256_PATTERN)
    decision: Literal["require_approval"]
    matched_rules: tuple[str, ...]
    obligations_digest: str = Field(pattern=SHA256_PATTERN)


class ManifestAuthorityRecord(FrozenAuthorityModel):
    lock_version: str = Field(min_length=1, max_length=128)
    lock_digest: str = Field(pattern=SHA256_PATTERN)
    tool_count: Literal[24]


class InputSchemaAuthorityRecord(FrozenAuthorityModel):
    schema_id: str = Field(min_length=1, max_length=128)
    schema_version: Literal["2"]
    schema_digest: str = Field(pattern=SHA256_PATTERN)


class RuntimeCandidateRecord(FrozenAuthorityModel):
    posture: Literal["reviewed"]
    candidate_id: str = Field(pattern=SHA256_PATTERN)
    source_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    inventory_schema_version: str = Field(min_length=1, max_length=64)
    reviewed_inventory_digest: str = Field(pattern=SHA256_PATTERN)
    dependency_lock_digest: str = Field(pattern=SHA256_PATTERN)
    release_artifact_digest: str = Field(pattern=SHA256_PATTERN)
    review_packet_digest: str = Field(pattern=SHA256_PATTERN)
    evidence_schema_version: str = Field(min_length=1, max_length=64)
    authorization_id: str = Field(min_length=1, max_length=128)

    def candidate_core(self) -> JsonObject:
        return {
            "source_commit": self.source_commit,
            "inventory_schema_version": self.inventory_schema_version,
            "reviewed_inventory_digest": self.reviewed_inventory_digest,
            "dependency_lock_digest": self.dependency_lock_digest,
            "release_artifact_digest": self.release_artifact_digest,
            "evidence_schema_version": self.evidence_schema_version,
        }

    def candidate_id_is_valid(self) -> bool:
        return self.candidate_id == sha256_digest(self.candidate_core())


class PromotionAuthoritySnapshot(FrozenAuthorityModel):
    snapshot_schema_version: Literal["1"] = "1"
    requesting_principal: AdminPrincipalContext
    trusted_host: TrustedHostAuthorityRecord
    workspace: WorkspaceAuthorityRecord
    sandbox: SandboxAuthorityRecord
    policy: PolicyAuthorityRecord
    manifest: ManifestAuthorityRecord
    input_schema: InputSchemaAuthorityRecord
    runtime_candidate: RuntimeCandidateRecord

    @property
    def snapshot_hash(self) -> str:
        return self.canonical_hash()

"""Staging-only trusted-host promotion evidence and placement."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import unicodedata
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast
from uuid import uuid4

from ithildin_policy_core import PolicyEngine
from ithildin_schemas import (
    ApprovalRequest,
    ApprovalStatus,
    JsonObject,
    JsonValue,
    PolicyDecisionValue,
    PolicyInput,
    canonical_json,
    sha256_digest,
)
from ithildin_schemas.models import StrictBaseModel
from pydantic import Field, ValidationError, field_validator

from ithildin_api.approvals import (
    ApprovalError,
    ApprovalService,
    ApprovalStore,
    CreateApprovalInput,
)
from ithildin_api.identity import PrincipalRegistry, PrincipalRegistryError
from ithildin_api.promotion_authority import (
    AdminPrincipalContext,
    InputSchemaAuthorityRecord,
    ManifestAuthorityRecord,
    PolicyAuthorityRecord,
    PromotionAuthoritySnapshot,
    PromotionReadinessReason,
    RuntimeCandidateRecord,
    WorkspaceAuthorityRecord,
)
from ithildin_api.read_tools import FilesystemReadTools, ReadToolError, ReadToolExecutor
from ithildin_api.registry import ToolRegistry
from ithildin_api.sandbox_descriptors import SandboxDescriptorError, SandboxDescriptorStore
from ithildin_api.trusted_host_placement import (
    TrustedHostPlacement,
    TrustedHostPlacementError,
    descriptor_relative_placement_supported,
)
from ithildin_api.trusted_host_promotion_v2_migration import initialize_or_migrate_database
from ithildin_api.trusted_host_registry import (
    TrustedHostDescriptorRegistry,
    TrustedHostRegistryError,
)
from ithildin_api.workspaces import WorkspaceRegistry, WorkspaceRegistryError

TRUSTED_HOST_PROMOTION_TOOL = "trusted_host.promotion.stage"
PROMOTION_INPUT_SCHEMA_ID = "ithildin.trusted_host_promotion_proposal"
PROMOTION_INPUT_SCHEMA_VERSION: Literal["2"] = "2"
PROMOTION_REQUIRED_APPROVER_ROLES = ("Admin", "Approver")
PROMOTION_OBLIGATIONS: JsonObject = {
    "approval_mode": "one_time",
    "approval_required": True,
    "audit_level": "full",
    "placement_mode": "create_exclusive",
    "zone": "host_staging",
}
MAX_PROMOTION_ARTIFACT_BYTES = 4096
LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@-]{0,127}$")
SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.@-]{0,127}$")


class TrustedHostPromotionError(RuntimeError):
    """Raised when trusted-host staging evidence is unsafe or invalid."""


class TrustedHostPromotionProposalInput(StrictBaseModel):
    workspace_id: str = Field(default="default", min_length=1, max_length=120)
    sandbox_descriptor_id: str = Field(min_length=1, max_length=120)
    sandbox_id: str = Field(min_length=1, max_length=120)
    source_artifact_path: str = Field(min_length=1, max_length=240)
    host_staging_label: str = Field(min_length=1, max_length=160)
    artifact_media_label: str = Field(default="text/plain", min_length=1, max_length=64)
    operator_note_label: str | None = Field(default=None, max_length=120)

    @field_validator(
        "workspace_id",
        "sandbox_descriptor_id",
        "sandbox_id",
        "artifact_media_label",
        "operator_note_label",
    )
    @classmethod
    def _safe_label(cls, value: str | None) -> str | None:
        if value is None:
            return None
        _reject_control_or_unnormalized(value, label="label")
        if not LABEL_RE.fullmatch(value) or "\\" in value or ".." in value:
            raise ValueError("unsafe label")
        return value

    @field_validator("source_artifact_path")
    @classmethod
    def _source_path_is_relative(cls, value: str) -> str:
        return _safe_relative_path(value, label="source_artifact_path")

    @field_validator("host_staging_label")
    @classmethod
    def _staging_label_is_safe(cls, value: str) -> str:
        _reject_control_or_unnormalized(value, label="host_staging_label")
        if not value.startswith("host-staging://"):
            raise ValueError("host staging label must use host-staging://")
        suffix = value.removeprefix("host-staging://")
        if not suffix or "/" in suffix or "\\" in suffix or ".." in suffix:
            raise ValueError("host staging label is unsafe")
        if suffix.startswith(".") or not SAFE_NAME_RE.fullmatch(suffix):
            raise ValueError("host staging label is unsafe")
        _ensure_not_sensitive_label(suffix)
        return value


@dataclass(frozen=True)
class TrustedHostPromotionProposal:
    proposal_id: str
    request_id: str
    status: str
    created_at: str
    updated_at: str
    workspace_id: str
    sandbox_descriptor_id: str
    sandbox_descriptor_hash: str
    sandbox_id: str
    source_artifact_label: str
    host_staging_label: str
    artifact_sha256: str
    artifact_size_bytes: int
    artifact_media_label: str
    proposal_hash: str
    metadata: JsonObject
    authority_schema_version: str | None = None
    authority_snapshot_json: JsonObject | None = None
    authority_snapshot_hash: str | None = None
    requester_principal_id: str | None = None
    requester_principal_generation: str | None = None
    executor_principal_id: str | None = None
    executor_principal_generation: str | None = None

    def scope_metadata(self) -> JsonObject:
        return {
            "promotion_proposal_id": self.proposal_id,
            "proposal_hash": self.proposal_hash,
            "workspace_id": self.workspace_id,
            "sandbox_descriptor_id": self.sandbox_descriptor_id,
            "sandbox_descriptor_hash": self.sandbox_descriptor_hash,
            "sandbox_id": self.sandbox_id,
            "source_artifact_label": self.source_artifact_label,
            "host_staging_label": self.host_staging_label,
            "artifact_sha256": self.artifact_sha256,
            "artifact_size_bytes": self.artifact_size_bytes,
            "artifact_media_label": self.artifact_media_label,
            "authority_snapshot_hash": self.authority_snapshot_hash,
        }

    def summary(self) -> JsonObject:
        return {
            "promotion_proposal_id": self.proposal_id,
            "request_id": self.request_id,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "authority_binding_status": (
                "version_2_bound" if self.authority_snapshot_hash is not None else "legacy_unbound"
            ),
            "authority_snapshot_hash": self.authority_snapshot_hash,
            "requester_principal_id": self.requester_principal_id,
            "requester_principal_generation": self.requester_principal_generation,
            "executor_principal_id": self.executor_principal_id,
            "executor_principal_generation": self.executor_principal_generation,
            **self.scope_metadata(),
            "output_policy": _output_policy(),
        }


@dataclass(frozen=True)
class TrustedHostPromotionAttempt:
    attempt_id: str
    approval_id: str
    proposal_id: str
    request_id: str
    workspace_id: str
    host_staging_label: str
    artifact_sha256: str
    staged_sha256: str | None
    status: str
    failure_reason: str | None
    created_at: str
    updated_at: str
    metadata: JsonObject
    record_version: str = "2"
    authority_snapshot_hash: str | None = None
    executor_principal_id: str | None = None
    executor_principal_generation: str | None = None

    def summary(self) -> JsonObject:
        return {
            "promotion_attempt_id": self.attempt_id,
            "approval_id": self.approval_id,
            "promotion_proposal_id": self.proposal_id,
            "request_id": self.request_id,
            "workspace_id": self.workspace_id,
            "host_staging_label": self.host_staging_label,
            "artifact_sha256": self.artifact_sha256,
            "staged_sha256": self.staged_sha256,
            "status": self.status,
            "failure_reason": self.failure_reason,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata_keys": cast(JsonValue, sorted(self.metadata.keys())),
            "record_version": self.record_version,
            "authority_snapshot_hash": self.authority_snapshot_hash,
            "executor_principal_id": self.executor_principal_id,
            "executor_principal_generation": self.executor_principal_generation,
            "output_policy": _output_policy(),
        }


class TrustedHostPromotionStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def initialize(self) -> None:
        initialize_or_migrate_database(self.db_path)

    def create_proposal(self, proposal: TrustedHostPromotionProposal) -> None:
        with sqlite3.connect(self.db_path) as connection:
            self._insert_proposal(connection, proposal)
            connection.commit()

    def create_proposal_with_approval(
        self,
        proposal: TrustedHostPromotionProposal,
        approval: ApprovalRequest,
        *,
        approval_store: ApprovalStore,
        promotion_authority_hash: str,
        promotion_request_hash: str,
    ) -> None:
        """Atomically persist a fully bound proposal and its one approval."""
        if approval_store.db_path != self.db_path:
            raise TrustedHostPromotionError(
                "trusted-host proposal and approval stores are not transactionally co-located"
            )
        connection = sqlite3.connect(self.db_path, isolation_level=None)
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._insert_proposal(connection, proposal)
            approval_store.insert_on_connection(
                connection,
                approval,
                promotion_authority_hash=promotion_authority_hash,
                promotion_request_hash=promotion_request_hash,
            )
            connection.execute("COMMIT")
        except (sqlite3.DatabaseError, RuntimeError) as exc:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise TrustedHostPromotionError(
                "trusted-host proposal approval evidence transaction failed"
            ) from exc
        finally:
            connection.close()

    def _insert_proposal(
        self,
        connection: sqlite3.Connection,
        proposal: TrustedHostPromotionProposal,
    ) -> None:
        connection.execute(
            """
            INSERT INTO trusted_host_promotion_proposals (
                proposal_id, request_id, status, created_at, updated_at,
                workspace_id, sandbox_descriptor_id, sandbox_descriptor_hash,
                sandbox_id, source_artifact_label, host_staging_label,
                artifact_sha256, artifact_size_bytes, artifact_media_label,
                proposal_hash, metadata_json, authority_schema_version,
                authority_snapshot_json, authority_snapshot_hash,
                requester_principal_id, requester_principal_generation,
                executor_principal_id, executor_principal_generation
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                proposal.proposal_id,
                proposal.request_id,
                _proposal_storage_status(proposal.status),
                proposal.created_at,
                proposal.updated_at,
                proposal.workspace_id,
                proposal.sandbox_descriptor_id,
                proposal.sandbox_descriptor_hash,
                proposal.sandbox_id,
                proposal.source_artifact_label,
                proposal.host_staging_label,
                proposal.artifact_sha256,
                proposal.artifact_size_bytes,
                proposal.artifact_media_label,
                proposal.proposal_hash,
                canonical_json(proposal.metadata),
                proposal.authority_schema_version,
                (
                    canonical_json(proposal.authority_snapshot_json)
                    if proposal.authority_snapshot_json is not None
                    else None
                ),
                proposal.authority_snapshot_hash,
                proposal.requester_principal_id,
                proposal.requester_principal_generation,
                proposal.executor_principal_id,
                proposal.executor_principal_generation,
            ),
        )

    def get_proposal(self, proposal_id: str) -> TrustedHostPromotionProposal:
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT proposal_id, request_id, status, created_at, updated_at,
                       workspace_id, sandbox_descriptor_id, sandbox_descriptor_hash,
                       sandbox_id, source_artifact_label, host_staging_label,
                       artifact_sha256, artifact_size_bytes, artifact_media_label,
                       proposal_hash, metadata_json, authority_schema_version,
                       authority_snapshot_json, authority_snapshot_hash,
                       requester_principal_id, requester_principal_generation,
                       executor_principal_id, executor_principal_generation
                FROM trusted_host_promotion_proposals
                WHERE proposal_id = ?
                """,
                (proposal_id,),
            ).fetchone()
        if row is None:
            raise TrustedHostPromotionError("trusted-host promotion proposal not found")
        return _proposal_from_row(row)

    def list_proposals(self) -> list[TrustedHostPromotionProposal]:
        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT proposal_id, request_id, status, created_at, updated_at,
                       workspace_id, sandbox_descriptor_id, sandbox_descriptor_hash,
                       sandbox_id, source_artifact_label, host_staging_label,
                       artifact_sha256, artifact_size_bytes, artifact_media_label,
                       proposal_hash, metadata_json, authority_schema_version,
                       authority_snapshot_json, authority_snapshot_hash,
                       requester_principal_id, requester_principal_generation,
                       executor_principal_id, executor_principal_generation
                FROM trusted_host_promotion_proposals
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [_proposal_from_row(row) for row in rows]

    def set_proposal_status(self, proposal_id: str, status: str) -> None:
        with sqlite3.connect(self.db_path) as connection:
            updated = connection.execute(
                """
                UPDATE trusted_host_promotion_proposals
                SET status = ?, updated_at = ?
                WHERE proposal_id = ?
                """,
                (_proposal_storage_status(status), datetime.now(UTC).isoformat(), proposal_id),
            ).rowcount
            connection.commit()
        if updated != 1:
            raise TrustedHostPromotionError("trusted-host promotion proposal not found")

    def bind_proposal_approval(self, proposal_id: str, approval_id: str) -> None:
        proposal = self.get_proposal(proposal_id)
        existing = proposal.metadata.get("approval_id")
        if existing is not None and existing != approval_id:
            raise TrustedHostPromotionError(
                "trusted-host promotion proposal approval binding conflict"
            )
        metadata = {**proposal.metadata, "approval_id": approval_id}
        with sqlite3.connect(self.db_path) as connection:
            updated = connection.execute(
                """
                UPDATE trusted_host_promotion_proposals
                SET metadata_json = ?, updated_at = ?
                WHERE proposal_id = ? AND status = 'v2_approval_required'
                """,
                (
                    canonical_json(metadata),
                    datetime.now(UTC).isoformat(),
                    proposal_id,
                ),
            ).rowcount
            connection.commit()
        if updated != 1:
            raise TrustedHostPromotionError(
                "trusted-host promotion proposal approval binding failed"
            )

    def create_attempt(self, attempt: TrustedHostPromotionAttempt) -> None:
        try:
            with sqlite3.connect(self.db_path) as connection:
                self._insert_attempt(connection, attempt)
                connection.commit()
        except sqlite3.IntegrityError as exc:
            raise TrustedHostPromotionError(
                "trusted-host promotion attempt already exists for approval or proposal"
            ) from exc

    def reserve_execution(
        self,
        attempt: TrustedHostPromotionAttempt,
        *,
        approval_store: ApprovalStore,
        approval: ApprovalRequest,
        proposal: TrustedHostPromotionProposal,
        promotion_request_hash: str,
    ) -> None:
        """Atomically reserve the approval, proposal, and single prepared attempt."""
        if approval_store.db_path != self.db_path:
            raise TrustedHostPromotionError(
                "trusted-host execution records are not transactionally co-located"
            )
        if (
            attempt.authority_snapshot_hash is None
            or attempt.executor_principal_id is None
            or attempt.executor_principal_generation is None
            or approval.decision_hash is None
        ):
            raise TrustedHostPromotionError("trusted-host execution evidence is incomplete")
        now = datetime.now(UTC).isoformat()
        connection = sqlite3.connect(self.db_path, isolation_level=None)
        try:
            connection.execute("BEGIN IMMEDIATE")
            approval_updated = connection.execute(
                """
                UPDATE approvals
                SET status = 'v2_executing', updated_at = ?,
                    executor_principal_id = ?, executor_principal_generation = ?
                WHERE approval_id = ?
                  AND approval_contract_version = '2'
                  AND status = 'v2_approved'
                  AND expires_at > ?
                  AND request_hash = ?
                  AND principal_json = ?
                  AND resource_json = ?
                  AND one_time_scope_json = ?
                  AND requester_principal_id = ?
                  AND requester_principal_generation = ?
                  AND promotion_authority_hash = ?
                  AND promotion_request_hash = ?
                  AND decided_at = ?
                  AND deciding_principal_id = ?
                  AND deciding_principal_generation = ?
                  AND decision_reason_hash = ?
                  AND decision_hash = ?
                  AND decision_authority_snapshot_hash = ?
                """,
                (
                    now,
                    attempt.executor_principal_id,
                    attempt.executor_principal_generation,
                    approval.approval_id,
                    now,
                    approval.request_hash,
                    canonical_json(approval.principal),
                    canonical_json(approval.resource),
                    canonical_json(approval.one_time_scope),
                    approval.requester_principal_id,
                    approval.requester_principal_generation,
                    attempt.authority_snapshot_hash,
                    promotion_request_hash,
                    approval.decided_at.isoformat() if approval.decided_at is not None else None,
                    approval.deciding_principal_id,
                    approval.deciding_principal_generation,
                    approval.decision_reason_hash,
                    approval.decision_hash,
                    attempt.authority_snapshot_hash,
                ),
            ).rowcount
            proposal_updated = connection.execute(
                """
                UPDATE trusted_host_promotion_proposals
                SET status = 'v2_executing', updated_at = ?,
                    executor_principal_id = ?, executor_principal_generation = ?
                WHERE proposal_id = ?
                  AND status = 'v2_approval_required'
                  AND authority_snapshot_hash = ?
                  AND proposal_hash = ?
                  AND request_id = ?
                  AND workspace_id = ?
                  AND sandbox_descriptor_id = ?
                  AND sandbox_descriptor_hash = ?
                  AND sandbox_id = ?
                  AND source_artifact_label = ?
                  AND host_staging_label = ?
                  AND artifact_sha256 = ?
                  AND artifact_size_bytes = ?
                  AND artifact_media_label = ?
                  AND metadata_json = ?
                  AND authority_snapshot_json = ?
                  AND requester_principal_id = ?
                  AND requester_principal_generation = ?
                  AND executor_principal_id IS NULL
                  AND executor_principal_generation IS NULL
                """,
                (
                    now,
                    attempt.executor_principal_id,
                    attempt.executor_principal_generation,
                    attempt.proposal_id,
                    attempt.authority_snapshot_hash,
                    proposal.proposal_hash,
                    proposal.request_id,
                    proposal.workspace_id,
                    proposal.sandbox_descriptor_id,
                    proposal.sandbox_descriptor_hash,
                    proposal.sandbox_id,
                    proposal.source_artifact_label,
                    proposal.host_staging_label,
                    proposal.artifact_sha256,
                    proposal.artifact_size_bytes,
                    proposal.artifact_media_label,
                    canonical_json(proposal.metadata),
                    canonical_json(proposal.authority_snapshot_json),
                    proposal.requester_principal_id,
                    proposal.requester_principal_generation,
                ),
            ).rowcount
            if approval_updated != 1 or proposal_updated != 1:
                raise TrustedHostPromotionError("proposal_not_applicable")
            self._insert_attempt(connection, attempt)
            connection.execute("COMMIT")
        except TrustedHostPromotionError:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        except sqlite3.DatabaseError as exc:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise TrustedHostPromotionError("trusted-host execution reservation failed") from exc
        finally:
            connection.close()

    def mark_authority_stale(self, proposal_id: str) -> bool:
        """Terminally stale only a proposal that has not been reserved."""
        with sqlite3.connect(self.db_path) as connection:
            updated = connection.execute(
                """
                UPDATE trusted_host_promotion_proposals
                SET status = 'v2_authority_stale', updated_at = ?
                WHERE proposal_id = ? AND status = 'v2_approval_required'
                """,
                (datetime.now(UTC).isoformat(), proposal_id),
            ).rowcount
            connection.commit()
        return updated == 1

    def record_placement_success(
        self,
        attempt_id: str,
        *,
        staged_sha256: str,
    ) -> TrustedHostPromotionAttempt:
        return self._record_placement_outcome(
            attempt_id,
            attempt_status="v2_staged",
            proposal_status="v2_completion_evidence_pending",
            approval_status="v2_executed",
            staged_sha256=staged_sha256,
            failure_reason=None,
        )

    def record_placement_failure(
        self,
        attempt_id: str,
        *,
        reason: str,
        recovery_required: bool,
    ) -> TrustedHostPromotionAttempt:
        return self._record_placement_outcome(
            attempt_id,
            attempt_status=(
                "v2_placement_evidence_recovery_required"
                if recovery_required
                else "v2_failed"
            ),
            proposal_status=(
                "v2_placement_evidence_recovery_required"
                if recovery_required
                else "v2_failed"
            ),
            approval_status="v2_failed",
            staged_sha256=None,
            failure_reason=reason,
        )

    def _record_placement_outcome(
        self,
        attempt_id: str,
        *,
        attempt_status: str,
        proposal_status: str,
        approval_status: str,
        staged_sha256: str | None,
        failure_reason: str | None,
    ) -> TrustedHostPromotionAttempt:
        now = datetime.now(UTC).isoformat()
        connection = sqlite3.connect(self.db_path, isolation_level=None)
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT approval_id, proposal_id
                FROM trusted_host_promotion_attempts
                WHERE attempt_id = ? AND status = 'v2_prepared'
                """,
                (attempt_id,),
            ).fetchone()
            if row is None:
                raise TrustedHostPromotionError("trusted-host attempt is not prepared")
            attempt_updated = connection.execute(
                """
                UPDATE trusted_host_promotion_attempts
                SET status = ?, staged_sha256 = ?, failure_reason = ?, updated_at = ?
                WHERE attempt_id = ? AND status = 'v2_prepared'
                """,
                (attempt_status, staged_sha256, failure_reason, now, attempt_id),
            ).rowcount
            proposal_updated = connection.execute(
                """
                UPDATE trusted_host_promotion_proposals
                SET status = ?, updated_at = ?
                WHERE proposal_id = ? AND status = 'v2_executing'
                """,
                (proposal_status, now, str(row[1])),
            ).rowcount
            approval_updated = connection.execute(
                """
                UPDATE approvals
                SET status = ?, updated_at = ?
                WHERE approval_id = ? AND status = 'v2_executing'
                """,
                (approval_status, now, str(row[0])),
            ).rowcount
            if attempt_updated != 1 or proposal_updated != 1 or approval_updated != 1:
                raise TrustedHostPromotionError("trusted-host placement evidence update failed")
            connection.execute("COMMIT")
        except TrustedHostPromotionError:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        except sqlite3.DatabaseError as exc:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise TrustedHostPromotionError(
                "trusted-host placement evidence update failed"
            ) from exc
        finally:
            connection.close()
        return self.get_attempt(attempt_id)

    @staticmethod
    def _insert_attempt(
        connection: sqlite3.Connection,
        attempt: TrustedHostPromotionAttempt,
    ) -> None:
        connection.execute(
            """
            INSERT INTO trusted_host_promotion_attempts (
                attempt_id, approval_id, proposal_id, request_id, workspace_id,
                host_staging_label, artifact_sha256, staged_sha256, status,
                failure_reason, created_at, updated_at, metadata_json,
                record_version, authority_snapshot_hash,
                executor_principal_id, executor_principal_generation
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attempt.attempt_id,
                attempt.approval_id,
                attempt.proposal_id,
                attempt.request_id,
                attempt.workspace_id,
                attempt.host_staging_label,
                attempt.artifact_sha256,
                attempt.staged_sha256,
                _attempt_storage_status(attempt.status),
                attempt.failure_reason,
                attempt.created_at,
                attempt.updated_at,
                canonical_json(attempt.metadata),
                attempt.record_version,
                attempt.authority_snapshot_hash,
                attempt.executor_principal_id,
                attempt.executor_principal_generation,
            ),
        )

    def get_attempt_for_proposal(
        self,
        proposal_id: str,
    ) -> TrustedHostPromotionAttempt | None:
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT attempt_id, approval_id, proposal_id, request_id, workspace_id,
                       host_staging_label, artifact_sha256, staged_sha256, status,
                       failure_reason, created_at, updated_at, metadata_json,
                       record_version, authority_snapshot_hash,
                       executor_principal_id, executor_principal_generation
                FROM trusted_host_promotion_attempts
                WHERE proposal_id = ?
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (proposal_id,),
            ).fetchone()
        return _attempt_from_row(row) if row is not None else None

    def set_attempt_status(
        self,
        attempt_id: str,
        status: str,
        *,
        staged_sha256: str | None = None,
        failure_reason: str | None = None,
    ) -> TrustedHostPromotionAttempt:
        with sqlite3.connect(self.db_path) as connection:
            updated = connection.execute(
                """
                UPDATE trusted_host_promotion_attempts
                SET status = ?,
                    staged_sha256 = COALESCE(?, staged_sha256),
                    failure_reason = COALESCE(?, failure_reason),
                    updated_at = ?
                WHERE attempt_id = ?
                """,
                (
                    _attempt_storage_status(status),
                    staged_sha256,
                    failure_reason,
                    datetime.now(UTC).isoformat(),
                    attempt_id,
                ),
            ).rowcount
            connection.commit()
        if updated != 1:
            raise TrustedHostPromotionError("trusted-host promotion attempt not found")
        return self.get_attempt(attempt_id)

    def get_attempt(self, attempt_id: str) -> TrustedHostPromotionAttempt:
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT attempt_id, approval_id, proposal_id, request_id, workspace_id,
                       host_staging_label, artifact_sha256, staged_sha256, status,
                       failure_reason, created_at, updated_at, metadata_json,
                       record_version, authority_snapshot_hash,
                       executor_principal_id, executor_principal_generation
                FROM trusted_host_promotion_attempts
                WHERE attempt_id = ?
                """,
                (attempt_id,),
            ).fetchone()
        if row is None:
            raise TrustedHostPromotionError("trusted-host promotion attempt not found")
        return _attempt_from_row(row)

    def list_attempts(self) -> list[TrustedHostPromotionAttempt]:
        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT attempt_id, approval_id, proposal_id, request_id, workspace_id,
                       host_staging_label, artifact_sha256, staged_sha256, status,
                       failure_reason, created_at, updated_at, metadata_json,
                       record_version, authority_snapshot_hash,
                       executor_principal_id, executor_principal_generation
                FROM trusted_host_promotion_attempts
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [_attempt_from_row(row) for row in rows]


class TrustedHostPromotionService:
    def __init__(
        self,
        *,
        store: TrustedHostPromotionStore,
        read_executor: ReadToolExecutor,
        descriptor_store: SandboxDescriptorStore,
        policy_engine: PolicyEngine,
        workspace_registry: WorkspaceRegistry,
        principal_registry: PrincipalRegistry,
        tool_registry: ToolRegistry,
        manifest_lock_path: Path,
        trusted_host_registry: TrustedHostDescriptorRegistry,
        runtime_candidate: RuntimeCandidateRecord | None,
        staging_root: Path,
        governance_binding_ready: bool = False,
        placement_test_fixture_ready: bool = False,
    ) -> None:
        self.store = store
        self.read_executor = read_executor
        self.descriptor_store = descriptor_store
        self.policy_engine = policy_engine
        self.workspace_registry = workspace_registry
        self.principal_registry = principal_registry
        self.tool_registry = tool_registry
        self.manifest_lock_path = manifest_lock_path
        self.trusted_host_registry = trusted_host_registry
        self.runtime_candidate = runtime_candidate
        self.staging_root = staging_root
        self.governance_binding_ready = governance_binding_ready
        self.placement_test_fixture_ready = placement_test_fixture_ready
        self.input_schema_authority = InputSchemaAuthorityRecord(
            schema_id=PROMOTION_INPUT_SCHEMA_ID,
            schema_version=PROMOTION_INPUT_SCHEMA_VERSION,
            schema_digest=sha256_digest(TrustedHostPromotionProposalInput.model_json_schema()),
        )
        self._manifest_authority_record: ManifestAuthorityRecord | None = None
        if governance_binding_ready:
            self._manifest_authority_record = self._manifest_authority()

    def create_proposal(
        self,
        payload: TrustedHostPromotionProposalInput,
        *,
        approval_service: ApprovalService,
        context: AdminPrincipalContext,
    ) -> JsonObject:
        self._require_governance_binding()
        context = self._current_requesting_principal(context)
        filesystem = self._filesystem(payload.workspace_id)
        source_path = _safe_relative_path(
            payload.source_artifact_path,
            label="source_artifact_path",
        )
        target = filesystem.workspace_root / source_path
        artifact_bytes = _read_source_artifact(filesystem, source_path)
        artifact_sha256 = _sha256_bytes(artifact_bytes)
        descriptor = self.descriptor_store.get(payload.sandbox_descriptor_id)
        safe_payload = descriptor.get("safe_payload")
        if not isinstance(safe_payload, dict):
            raise TrustedHostPromotionError("sandbox descriptor payload unavailable")
        if safe_payload.get("workspace_id") != payload.workspace_id:
            raise TrustedHostPromotionError("sandbox descriptor workspace mismatch")
        if safe_payload.get("sandbox_id") != payload.sandbox_id:
            raise TrustedHostPromotionError("sandbox descriptor sandbox mismatch")
        if safe_payload.get("trusted_host_promotion_performed") is not False:
            raise TrustedHostPromotionError("sandbox descriptor implies prior promotion")
        descriptor_hash = str(descriptor.get("payload_hash"))
        authority_snapshot, policy_obligations = self._authority_snapshot(
            payload=payload,
            context=context,
        )
        now = datetime.now(UTC).isoformat()
        proposal_id = f"thp_{uuid4().hex}"
        request_id = f"req_{uuid4().hex}"
        source_label = f"sandbox://{payload.sandbox_id}/{source_path}"
        metadata = cast(
            JsonObject,
            {
                "source_artifact_path_hash": sha256_digest(source_path),
                "operator_note_label": payload.operator_note_label,
                "target_leaf_hash": sha256_digest(target.name),
                "policy_obligations_digest": sha256_digest(policy_obligations),
                "required_approver_roles": list(PROMOTION_REQUIRED_APPROVER_ROLES),
                "output_policy": _output_policy(),
            },
        )
        authority_snapshot_json = authority_snapshot.canonical_payload()
        authority_snapshot_hash = authority_snapshot.snapshot_hash
        proposal_hash = sha256_digest(
            {
                "proposal_id": proposal_id,
                "request_id": request_id,
                "workspace_id": payload.workspace_id,
                "sandbox_descriptor_id": payload.sandbox_descriptor_id,
                "sandbox_descriptor_hash": descriptor_hash,
                "sandbox_id": payload.sandbox_id,
                "source_artifact_label": source_label,
                "host_staging_label": payload.host_staging_label,
                "artifact_sha256": artifact_sha256,
                "artifact_size_bytes": len(artifact_bytes),
                "artifact_media_label": payload.artifact_media_label,
                "metadata": metadata,
                "authority_snapshot_hash": authority_snapshot_hash,
            }
        )
        proposal = TrustedHostPromotionProposal(
            proposal_id=proposal_id,
            request_id=request_id,
            status="approval_required",
            created_at=now,
            updated_at=now,
            workspace_id=payload.workspace_id,
            sandbox_descriptor_id=payload.sandbox_descriptor_id,
            sandbox_descriptor_hash=descriptor_hash,
            sandbox_id=payload.sandbox_id,
            source_artifact_label=source_label,
            host_staging_label=payload.host_staging_label,
            artifact_sha256=artifact_sha256,
            artifact_size_bytes=len(artifact_bytes),
            artifact_media_label=payload.artifact_media_label,
            proposal_hash=proposal_hash,
            metadata=metadata,
            authority_schema_version="1",
            authority_snapshot_json=authority_snapshot_json,
            authority_snapshot_hash=authority_snapshot_hash,
            requester_principal_id=context.principal_id,
            requester_principal_generation=context.identity_generation,
        )
        scope = self._approval_scope(
            proposal=proposal,
            snapshot=authority_snapshot,
            policy_obligations=policy_obligations,
        )
        approval_input = CreateApprovalInput(
            request_id=request_id,
            principal=cast(
                JsonObject,
                {
                    "id": context.principal_id,
                    "type": context.principal_type,
                    "roles": list(context.roles),
                },
            ),
            tool_name=TRUSTED_HOST_PROMOTION_TOOL,
            resource={
                "type": "trusted_host_promotion",
                "workspace_id": payload.workspace_id,
                "source_artifact_label": source_label,
                "host_staging_label": payload.host_staging_label,
                "in_scope": True,
            },
            summary=f"Stage sandbox artifact to {payload.host_staging_label}",
            one_time_scope=scope,
            requester_context=context,
            promotion_authority_hash=authority_snapshot_hash,
            promotion_request_hash=sha256_digest(scope),
            metadata={
                "workspace_id": payload.workspace_id,
                "sandbox_id": payload.sandbox_id,
                "promotion_proposal_id": proposal_id,
                "proposal_hash": proposal_hash,
                "artifact_sha256": artifact_sha256,
                "artifact_size_bytes": len(artifact_bytes),
                "host_staging_label": payload.host_staging_label,
            },
        )
        approval = approval_service.prepare_pending(approval_input)
        proposal = replace(
            proposal,
            metadata={**proposal.metadata, "approval_id": approval.approval_id},
        )
        self.store.create_proposal_with_approval(
            proposal,
            approval,
            approval_store=approval_service.store,
            promotion_authority_hash=authority_snapshot_hash,
            promotion_request_hash=sha256_digest(scope),
        )
        try:
            approval_service.record_created(approval)
        except Exception as exc:
            self.store.set_proposal_status(proposal_id, "approval_evidence_failed")
            try:
                approval_service.store.compare_and_set_status(
                    approval.approval_id,
                    expected_status=approval.status,
                    next_status=ApprovalStatus.SUPERSEDED,
                )
            except ApprovalError:
                pass
            raise TrustedHostPromotionError("approval_evidence_failed") from exc
        return {
            **proposal.summary(),
            "approval_id": approval.approval_id,
            "approval_status": approval.status.value,
            "approval_expires_at": approval.expires_at.isoformat(),
        }

    def _authority_snapshot(
        self,
        *,
        payload: TrustedHostPromotionProposalInput,
        context: AdminPrincipalContext,
    ) -> tuple[PromotionAuthoritySnapshot, JsonObject]:
        try:
            workspace_id, workspace_hash, workspace_generation = (
                self.workspace_registry.authority_record(payload.workspace_id)
            )
            sandbox = self.descriptor_store.authority_record(payload.sandbox_descriptor_id)
            trusted_host = self.trusted_host_registry.resolve(
                workspace_id=payload.workspace_id,
                staging_label=payload.host_staging_label,
            )
        except (
            SandboxDescriptorError,
            WorkspaceRegistryError,
            TrustedHostRegistryError,
        ) as exc:
            raise TrustedHostPromotionError(
                "trusted-host promotion authority resolution failed"
            ) from exc
        workspace = WorkspaceAuthorityRecord(
            workspace_id=workspace_id,
            workspace_record_hash=workspace_hash,
            workspace_registry_generation=workspace_generation,
        )
        policy, obligations = self._policy_authority(
            payload=payload,
            context=context,
        )
        candidate = self.runtime_candidate
        if candidate is None:
            raise TrustedHostPromotionError(
                PromotionReadinessReason.CANDIDATE_AUTHORIZATION_UNAVAILABLE.value
            )
        if not candidate.candidate_id_is_valid():
            raise TrustedHostPromotionError(
                PromotionReadinessReason.CANDIDATE_VERIFICATION_FAILED.value
            )
        snapshot = PromotionAuthoritySnapshot(
            requesting_principal=context,
            trusted_host=trusted_host,
            workspace=workspace,
            sandbox=sandbox,
            policy=policy,
            manifest=self._manifest_authority(),
            input_schema=self.input_schema_authority,
            runtime_candidate=candidate,
        )
        return snapshot, obligations

    def _policy_authority(
        self,
        *,
        payload: TrustedHostPromotionProposalInput,
        context: AdminPrincipalContext,
    ) -> tuple[PolicyAuthorityRecord, JsonObject]:
        decision = self.policy_engine.evaluate(
            PolicyInput(
                principal={
                    "id": context.principal_id,
                    "type": context.principal_type,
                    "roles": list(context.roles),
                },
                tool={
                    "name": TRUSTED_HOST_PROMOTION_TOOL,
                    "risk": "write",
                    "version": "internal-v1",
                },
                resource={
                    "type": "trusted_host_promotion",
                    "workspace_id": payload.workspace_id,
                    "sandbox_descriptor_id": payload.sandbox_descriptor_id,
                    "sandbox_id": payload.sandbox_id,
                    "host_staging_label": payload.host_staging_label,
                    "artifact_media_label": payload.artifact_media_label,
                    "in_scope": True,
                },
                context={"authority_schema_version": "1"},
            )
        )
        if decision.decision is not PolicyDecisionValue.REQUIRE_APPROVAL:
            raise TrustedHostPromotionError("trusted-host promotion policy must require approval")
        if decision.policy_version != self.policy_engine.policy_hash:
            raise TrustedHostPromotionError("trusted-host promotion policy version mismatch")
        matched_rules = tuple(decision.matched_rules)
        if (
            not matched_rules
            or len(matched_rules) != len(set(matched_rules))
            or matched_rules != tuple(sorted(matched_rules))
            or any(not LABEL_RE.fullmatch(rule) for rule in matched_rules)
        ):
            raise TrustedHostPromotionError(
                "trusted-host promotion policy rule evidence is invalid"
            )
        obligations = decision.obligations
        if obligations != PROMOTION_OBLIGATIONS:
            raise TrustedHostPromotionError("trusted-host promotion policy obligations are invalid")
        return (
            PolicyAuthorityRecord(
                engine="yaml",
                document_version=self.policy_engine.document_version,
                policy_version=decision.policy_version,
                policy_digest=self.policy_engine.policy_hash,
                decision="require_approval",
                matched_rules=matched_rules,
                obligations_digest=sha256_digest(obligations),
            ),
            obligations,
        )

    def _manifest_authority(self) -> ManifestAuthorityRecord:
        if self._manifest_authority_record is not None:
            return self._manifest_authority_record
        try:
            raw_lock = json.loads(
                self.manifest_lock_path.read_text(encoding="utf-8"),
                object_pairs_hook=_json_object_without_duplicates,
            )
        except (OSError, ValueError) as exc:
            raise TrustedHostPromotionError(
                "trusted-host promotion manifest authority is unavailable"
            ) from exc
        if not isinstance(raw_lock, dict):
            raise TrustedHostPromotionError(
                "trusted-host promotion manifest authority is unavailable"
            )
        lock = cast(JsonObject, raw_lock)
        lock_version = lock.get("lockfile_version")
        if not isinstance(lock_version, (str, int)) or isinstance(lock_version, bool):
            raise TrustedHostPromotionError(
                "trusted-host promotion manifest authority is unavailable"
            )
        tool_count = len(self.tool_registry.list_tools())
        if tool_count != 24:
            raise TrustedHostPromotionError(
                "trusted-host promotion manifest tool count is invalid"
            )
        record = ManifestAuthorityRecord(
            lock_version=str(lock_version),
            lock_digest=sha256_digest(lock),
            tool_count=24,
        )
        self._manifest_authority_record = record
        return record

    def _current_requesting_principal(
        self,
        context: AdminPrincipalContext,
    ) -> AdminPrincipalContext:
        try:
            current = self.principal_registry.admin_context()
        except PrincipalRegistryError as exc:
            raise TrustedHostPromotionError(
                "trusted-host promotion principal authority is unavailable"
            ) from exc
        if current != context:
            raise TrustedHostPromotionError("trusted-host promotion principal authority mismatch")
        if len(current.roles) != len(set(current.roles)):
            raise TrustedHostPromotionError("trusted-host promotion principal roles are invalid")
        return current.model_copy(update={"roles": tuple(sorted(current.roles))})

    def _approval_scope(
        self,
        *,
        proposal: TrustedHostPromotionProposal,
        snapshot: PromotionAuthoritySnapshot,
        policy_obligations: JsonObject,
    ) -> JsonObject:
        base = cast(
            JsonObject,
            {
                "tool_name": TRUSTED_HOST_PROMOTION_TOOL,
                **proposal.scope_metadata(),
                "requesting_principal_id": snapshot.requesting_principal.principal_id,
                "requesting_principal_generation": (
                    snapshot.requesting_principal.identity_generation
                ),
                "trusted_host_descriptor_id": snapshot.trusted_host.descriptor_id,
                "trusted_host_descriptor_hash": snapshot.trusted_host.descriptor_hash,
                "trusted_host_descriptor_generation": (snapshot.trusted_host.descriptor_generation),
                "trusted_host_registry_schema_digest": (
                    snapshot.trusted_host.registry_schema_digest
                ),
                "workspace_record_hash": snapshot.workspace.workspace_record_hash,
                "workspace_registry_generation": (snapshot.workspace.workspace_registry_generation),
                "sandbox_descriptor_generation": snapshot.sandbox.descriptor_generation,
                "policy_engine": snapshot.policy.engine,
                "policy_document_version": snapshot.policy.document_version,
                "policy_version": snapshot.policy.policy_version,
                "policy_digest": snapshot.policy.policy_digest,
                "policy_decision": snapshot.policy.decision,
                "policy_matched_rules": list(snapshot.policy.matched_rules),
                "policy_obligations": policy_obligations,
                "policy_obligations_digest": snapshot.policy.obligations_digest,
                "manifest_lock_version": snapshot.manifest.lock_version,
                "manifest_lock_digest": snapshot.manifest.lock_digest,
                "manifest_tool_count": snapshot.manifest.tool_count,
                "input_schema_id": snapshot.input_schema.schema_id,
                "input_schema_version": snapshot.input_schema.schema_version,
                "input_schema_digest": snapshot.input_schema.schema_digest,
                "runtime_candidate_posture": snapshot.runtime_candidate.posture,
                "runtime_candidate_id": snapshot.runtime_candidate.candidate_id,
                "runtime_candidate_source_commit": snapshot.runtime_candidate.source_commit,
                "runtime_candidate_inventory_schema_version": (
                    snapshot.runtime_candidate.inventory_schema_version
                ),
                "runtime_candidate_inventory_digest": (
                    snapshot.runtime_candidate.reviewed_inventory_digest
                ),
                "runtime_candidate_dependency_lock_digest": (
                    snapshot.runtime_candidate.dependency_lock_digest
                ),
                "runtime_candidate_release_artifact_digest": (
                    snapshot.runtime_candidate.release_artifact_digest
                ),
                "runtime_candidate_review_packet_digest": (
                    snapshot.runtime_candidate.review_packet_digest
                ),
                "runtime_candidate_evidence_schema_version": (
                    snapshot.runtime_candidate.evidence_schema_version
                ),
                "runtime_candidate_authorization_id": (snapshot.runtime_candidate.authorization_id),
                "required_approver_roles": list(PROMOTION_REQUIRED_APPROVER_ROLES),
            },
        )
        return {**base, "request_hash": sha256_digest(base)}

    def approval_review(
        self,
        approval: ApprovalRequest,
        *,
        expected_proposal_id: str | None = None,
    ) -> JsonObject:
        reasons: list[str] = []
        scope = approval.one_time_scope
        proposal_id = _scope_string(scope, "promotion_proposal_id")
        try:
            proposal = self.store.get_proposal(proposal_id or "")
        except TrustedHostPromotionError:
            proposal = None
            reasons.append("promotion proposal unavailable")
        if approval.tool_name != TRUSTED_HOST_PROMOTION_TOOL:
            reasons.append("approval is not for trusted-host staging")
        if _scope_string(scope, "tool_name") != TRUSTED_HOST_PROMOTION_TOOL:
            reasons.append("approval scope tool mismatch")
        if expected_proposal_id is not None and proposal_id != expected_proposal_id:
            reasons.append("approval scope proposal mismatch")
        if proposal is not None:
            if proposal.status != "approval_required":
                reasons.append("promotion proposal is not approval required")
            if proposal.proposal_hash != sha256_digest(_proposal_hash_evidence(proposal)):
                reasons.append("promotion proposal hash mismatch")
            try:
                snapshot = PromotionAuthoritySnapshot.model_validate(
                    proposal.authority_snapshot_json
                )
            except ValidationError:
                snapshot = None
                reasons.append("promotion authority snapshot is invalid")
            if snapshot is not None:
                if proposal.authority_schema_version != snapshot.snapshot_schema_version:
                    reasons.append("promotion authority schema version mismatch")
                if snapshot.snapshot_hash != proposal.authority_snapshot_hash:
                    reasons.append("promotion authority snapshot hash mismatch")
                if (
                    snapshot.workspace.workspace_id != proposal.workspace_id
                    or snapshot.sandbox.descriptor_id != proposal.sandbox_descriptor_id
                    or snapshot.sandbox.descriptor_payload_hash
                    != proposal.sandbox_descriptor_hash
                    or snapshot.trusted_host.workspace_id != proposal.workspace_id
                    or snapshot.trusted_host.staging_label != proposal.host_staging_label
                ):
                    reasons.append("promotion authority component binding mismatch")
                if (
                    snapshot.policy.obligations_digest
                    != sha256_digest(PROMOTION_OBLIGATIONS)
                    or not snapshot.runtime_candidate.candidate_id_is_valid()
                    or not snapshot.policy.matched_rules
                    or snapshot.requesting_principal.roles
                    != tuple(sorted(set(snapshot.requesting_principal.roles)))
                    or snapshot.policy.matched_rules
                    != tuple(sorted(set(snapshot.policy.matched_rules)))
                ):
                    reasons.append("promotion authority evidence is invalid")
                if (
                    proposal.requester_principal_id
                    != snapshot.requesting_principal.principal_id
                    or proposal.requester_principal_generation
                    != snapshot.requesting_principal.identity_generation
                ):
                    reasons.append("promotion requester generation mismatch")
                expected_scope = self._approval_scope(
                    proposal=proposal,
                    snapshot=snapshot,
                    policy_obligations=PROMOTION_OBLIGATIONS,
                )
                if scope != expected_scope:
                    reasons.append("approval one-time scope mismatch")
                if approval.principal != {
                    "id": snapshot.requesting_principal.principal_id,
                    "type": snapshot.requesting_principal.principal_type,
                    "roles": list(snapshot.requesting_principal.roles),
                }:
                    reasons.append("approval principal authority mismatch")
                if (
                    approval.requester_principal_id != snapshot.requesting_principal.principal_id
                    or approval.requester_principal_generation
                    != snapshot.requesting_principal.identity_generation
                ):
                    reasons.append("approval requester generation mismatch")
            if approval.resource.get("workspace_id") != proposal.workspace_id:
                reasons.append("approval resource workspace mismatch")
            if approval.resource.get("host_staging_label") != proposal.host_staging_label:
                reasons.append("approval resource staging label mismatch")
            if approval.request_id != proposal.request_id:
                reasons.append("approval request mismatch")
            if proposal.metadata.get("approval_id") != approval.approval_id:
                reasons.append("proposal approval mismatch")
            expected_approval_request_hash = sha256_digest(
                {
                    "request_id": approval.request_id,
                    "principal": approval.principal,
                    "tool_name": approval.tool_name,
                    "resource": approval.resource,
                    "one_time_scope": approval.one_time_scope,
                }
            )
            if approval.request_hash != expected_approval_request_hash:
                reasons.append("approval request hash mismatch")
            if scope.get("required_approver_roles") != list(PROMOTION_REQUIRED_APPROVER_ROLES):
                reasons.append("approval required roles mismatch")
            if scope.get("policy_obligations") != PROMOTION_OBLIGATIONS:
                reasons.append("approval policy obligations mismatch")
        return {
            "valid": not reasons,
            "reasons": cast(JsonValue, reasons),
            "binding": {
                key: scope.get(key)
                for key in [
                    "promotion_proposal_id",
                    "proposal_hash",
                    "workspace_id",
                    "sandbox_descriptor_id",
                    "sandbox_descriptor_hash",
                    "sandbox_id",
                    "source_artifact_label",
                    "host_staging_label",
                    "artifact_sha256",
                    "artifact_size_bytes",
                    "artifact_media_label",
                    "authority_snapshot_hash",
                    "requesting_principal_id",
                    "requesting_principal_generation",
                    "trusted_host_descriptor_id",
                    "trusted_host_descriptor_hash",
                    "policy_engine",
                    "policy_document_version",
                    "policy_version",
                    "policy_digest",
                    "policy_decision",
                    "policy_matched_rules",
                    "policy_obligations",
                    "manifest_lock_version",
                    "manifest_lock_digest",
                    "manifest_tool_count",
                    "input_schema_id",
                    "input_schema_version",
                    "input_schema_digest",
                    "runtime_candidate_posture",
                    "runtime_candidate_id",
                    "runtime_candidate_source_commit",
                    "runtime_candidate_release_artifact_digest",
                    "runtime_candidate_review_packet_digest",
                    "required_approver_roles",
                ]
            },
            "output_policy": _output_policy(),
        }

    def apply_approved(
        self,
        *,
        proposal_id: str,
        approval_id: str,
        approval_service: ApprovalService,
        context: AdminPrincipalContext,
    ) -> JsonObject:
        self._require_governance_binding()
        proposal = self.store.get_proposal(proposal_id)
        if proposal.status != "approval_required":
            raise TrustedHostPromotionError("proposal_not_applicable")
        approval = approval_service.get(approval_id)
        review = self.approval_review(
            approval,
            expected_proposal_id=proposal.proposal_id,
        )
        if review["valid"] is not True:
            if proposal.metadata.get("approval_id") == approval.approval_id:
                self._terminally_stale(proposal.proposal_id)
            raise TrustedHostPromotionError("trusted-host promotion approval binding review failed")
        try:
            current_context = self._current_requesting_principal(context)
            current_snapshot, _ = self._authority_snapshot(
                payload=self._payload_from_proposal(proposal),
                context=current_context,
            )
            self._require_current_approval_decision(
                approval,
                context=current_context,
                authority_snapshot_hash=current_snapshot.snapshot_hash,
                approval_store=approval_service.store,
            )
        except TrustedHostPromotionError as exc:
            self._terminally_stale(proposal.proposal_id)
            raise TrustedHostPromotionError("trusted-host promotion authority is stale") from exc
        if (
            current_snapshot.snapshot_hash != proposal.authority_snapshot_hash
            or current_snapshot.canonical_payload() != proposal.authority_snapshot_json
        ):
            self._terminally_stale(proposal.proposal_id)
            raise TrustedHostPromotionError("trusted-host promotion authority is stale")
        if not self.placement_test_fixture_ready:
            raise TrustedHostPromotionError(
                "trusted-host promotion placement is not production-ready"
            )
        if not descriptor_relative_placement_supported():
            raise TrustedHostPromotionError("descriptor_relative_placement_unsupported")

        payload = self._payload_from_proposal(proposal)
        try:
            source_bytes = _read_source_artifact(
                self._filesystem(proposal.workspace_id),
                payload.source_artifact_path,
            )
        except TrustedHostPromotionError as exc:
            self._terminally_stale(proposal.proposal_id)
            raise TrustedHostPromotionError("trusted-host promotion source is stale") from exc
        if (
            len(source_bytes) != proposal.artifact_size_bytes
            or _sha256_bytes(source_bytes) != proposal.artifact_sha256
        ):
            self._terminally_stale(proposal.proposal_id)
            raise TrustedHostPromotionError("trusted-host promotion source is stale")

        attempt_id = _attempt_id_for_proposal(proposal.proposal_id)
        now = datetime.now(UTC).isoformat()
        attempt = TrustedHostPromotionAttempt(
            attempt_id=attempt_id,
            approval_id=approval.approval_id,
            proposal_id=proposal.proposal_id,
            request_id=proposal.request_id,
            workspace_id=proposal.workspace_id,
            host_staging_label=proposal.host_staging_label,
            artifact_sha256=proposal.artifact_sha256,
            staged_sha256=None,
            status="prepared",
            failure_reason=None,
            created_at=now,
            updated_at=now,
            metadata={
                "placement_mode": "create_exclusive",
                "zone": "host_staging",
                "source_buffer_sha256": proposal.artifact_sha256,
                "destination_leaf_hash": sha256_digest(
                    self._destination_leaf(proposal, attempt_id)
                ),
            },
            authority_snapshot_hash=current_snapshot.snapshot_hash,
            executor_principal_id=current_context.principal_id,
            executor_principal_generation=current_context.identity_generation,
        )
        promotion_request_hash = sha256_digest(approval.one_time_scope)
        try:
            with TrustedHostPlacement(self.staging_root) as placement:
                try:
                    self.store.reserve_execution(
                        attempt,
                        approval_store=approval_service.store,
                        approval=approval,
                        proposal=proposal,
                        promotion_request_hash=promotion_request_hash,
                    )
                except TrustedHostPromotionError as exc:
                    if str(exc) == "proposal_not_applicable":
                        current = self.store.get_proposal(proposal.proposal_id)
                        became_stale = (
                            current.status == "approval_required"
                            and self.store.mark_authority_stale(proposal.proposal_id)
                        )
                        if became_stale:
                            raise TrustedHostPromotionError(
                                "trusted-host promotion authority is stale"
                            ) from exc
                    raise
                try:
                    result = placement.place(
                        source_bytes,
                        workspace_id=proposal.workspace_id,
                        proposal_id=proposal.proposal_id,
                        destination_leaf=self._destination_leaf(proposal, attempt_id),
                    )
                except TrustedHostPlacementError as exc:
                    self.store.record_placement_failure(
                        attempt_id,
                        reason=exc.reason,
                        recovery_required=exc.effect_possible,
                    )
                    raise TrustedHostPromotionError(exc.reason) from exc
        except TrustedHostPlacementError as exc:
            raise TrustedHostPromotionError(exc.reason) from exc

        try:
            recorded = self.store.record_placement_success(
                attempt_id,
                staged_sha256=result.staged_sha256,
            )
        except TrustedHostPromotionError as exc:
            try:
                self.store.record_placement_failure(
                    attempt_id,
                    reason="placement_evidence_update_failed",
                    recovery_required=True,
                )
            except TrustedHostPromotionError:
                pass
            raise TrustedHostPromotionError(
                "placement_evidence_recovery_required"
            ) from exc
        return {
            "promotion_attempt": recorded.summary(),
            "proposal_status": "completion_evidence_pending",
            "completion_claimed": False,
            "output_policy": _output_policy(),
        }

    def _require_current_approval_decision(
        self,
        approval: ApprovalRequest,
        *,
        context: AdminPrincipalContext,
        authority_snapshot_hash: str,
        approval_store: ApprovalStore,
    ) -> None:
        if (
            approval.status is not ApprovalStatus.APPROVED
            or approval.decided_at is None
            or approval.deciding_principal_id != context.principal_id
            or approval.deciding_principal_generation != context.identity_generation
            or approval.decision_reason_hash is None
            or approval.decision_authority_snapshot_hash != authority_snapshot_hash
            or approval.decision_hash is None
        ):
            raise TrustedHostPromotionError("approval_decision_evidence_mismatch")
        expected_decision_hash = sha256_digest(
            {
                "approval_id": approval.approval_id,
                "approval_request_hash": approval.request_hash,
                "decision_status": ApprovalStatus.APPROVED.value,
                "decided_at": approval.decided_at.isoformat(),
                "deciding_principal_id": approval.deciding_principal_id,
                "deciding_principal_generation": approval.deciding_principal_generation,
                "decision_reason_hash": approval.decision_reason_hash,
                "decision_authority_snapshot_hash": authority_snapshot_hash,
            }
        )
        if approval.decision_hash != expected_decision_hash:
            raise TrustedHostPromotionError("approval_decision_evidence_mismatch")
        try:
            stored_authority_hash, stored_request_hash = (
                approval_store.promotion_binding_hashes(approval.approval_id)
            )
        except ApprovalError as exc:
            raise TrustedHostPromotionError("approval_decision_evidence_mismatch") from exc
        if (
            stored_authority_hash != authority_snapshot_hash
            or stored_request_hash != sha256_digest(approval.one_time_scope)
        ):
            raise TrustedHostPromotionError("approval_decision_evidence_mismatch")

    def _terminally_stale(self, proposal_id: str) -> None:
        if not self.store.mark_authority_stale(proposal_id):
            raise TrustedHostPromotionError("proposal_not_applicable")

    def complete_with_evidence(self, attempt_id: str) -> TrustedHostPromotionAttempt:
        self._require_governance_binding()
        raise TrustedHostPromotionError(
            "trusted-host promotion completion evidence is not production-ready"
        )

    def diagnostics(self, approval_service: ApprovalService) -> JsonObject:
        attempts = [attempt.summary() for attempt in self.store.list_attempts()]
        incomplete = [attempt for attempt in attempts if attempt["status"] != "completed"]
        stuck_approvals = [
            {
                "approval_id": approval.approval_id,
                "request_id": approval.request_id,
                "status": approval.status.value,
                "proposal_id": approval.one_time_scope.get("promotion_proposal_id"),
                "host_staging_label": approval.one_time_scope.get("host_staging_label"),
            }
            for approval in approval_service.list()
            if approval.tool_name == TRUSTED_HOST_PROMOTION_TOOL
            and approval.status.value == "executing"
        ]
        diagnostic_status = "clean"
        if any(
            attempt["status"] == "placement_evidence_recovery_required"
            for attempt in attempts
        ):
            diagnostic_status = "recovery_required"
        elif incomplete or stuck_approvals:
            diagnostic_status = "ambiguous"
        return {
            "status": diagnostic_status,
            "availability": self._availability_reason(),
            "placement_available": False,
            "attempts": cast(JsonValue, attempts),
            "stuck_approvals": cast(JsonValue, stuck_approvals),
            "recommendations": cast(
                JsonValue,
                [
                    {
                        "type": "manual_review",
                        "message": (
                            "Review proposal, approval, attempt, destination label, "
                            "and audit evidence; do not retry or repair automatically."
                        ),
                    }
                ],
            )
            if diagnostic_status != "clean"
            else cast(
                JsonValue,
                [{"type": "none", "message": "No incomplete trusted-host attempts detected."}],
            ),
            "output_policy": _output_policy(),
        }

    def _require_governance_binding(self) -> None:
        if self.policy_engine.engine_name != "yaml":
            raise TrustedHostPromotionError("unsupported_policy_engine_for_promotion")
        if not self.governance_binding_ready:
            raise TrustedHostPromotionError(
                PromotionReadinessReason.GOVERNANCE_BINDING_INCOMPLETE.value
            )
        if self.runtime_candidate is None:
            raise TrustedHostPromotionError(
                PromotionReadinessReason.CANDIDATE_AUTHORIZATION_UNAVAILABLE.value
            )

    def _availability_reason(self) -> str:
        if self.policy_engine.engine_name != "yaml":
            return "unsupported_policy_engine_for_promotion"
        if not self.governance_binding_ready:
            return PromotionReadinessReason.GOVERNANCE_BINDING_INCOMPLETE.value
        if self.runtime_candidate is None:
            return PromotionReadinessReason.CANDIDATE_AUTHORIZATION_UNAVAILABLE.value
        if not self.runtime_candidate.candidate_id_is_valid():
            return PromotionReadinessReason.CANDIDATE_VERIFICATION_FAILED.value
        return PromotionReadinessReason.READY.value

    def _payload_from_proposal(
        self,
        proposal: TrustedHostPromotionProposal,
    ) -> TrustedHostPromotionProposalInput:
        prefix = f"sandbox://{proposal.sandbox_id}/"
        if not proposal.source_artifact_label.startswith(prefix):
            raise TrustedHostPromotionError("trusted-host promotion source binding is invalid")
        operator_note = proposal.metadata.get("operator_note_label")
        if operator_note is not None and not isinstance(operator_note, str):
            raise TrustedHostPromotionError("trusted-host promotion note binding is invalid")
        try:
            return TrustedHostPromotionProposalInput(
                workspace_id=proposal.workspace_id,
                sandbox_descriptor_id=proposal.sandbox_descriptor_id,
                sandbox_id=proposal.sandbox_id,
                source_artifact_path=proposal.source_artifact_label.removeprefix(prefix),
                host_staging_label=proposal.host_staging_label,
                artifact_media_label=proposal.artifact_media_label,
                operator_note_label=operator_note,
            )
        except ValidationError as exc:
            raise TrustedHostPromotionError(
                "trusted-host promotion request binding is invalid"
            ) from exc

    def _filesystem(self, workspace_id: str) -> FilesystemReadTools:
        try:
            return self.read_executor.filesystems[workspace_id]
        except KeyError as exc:
            raise TrustedHostPromotionError("unknown workspace") from exc

    def _destination_leaf(self, proposal: TrustedHostPromotionProposal, attempt_id: str) -> str:
        label_leaf = proposal.host_staging_label.removeprefix("host-staging://")
        if not SAFE_NAME_RE.fullmatch(label_leaf):
            raise TrustedHostPromotionError("host staging label is unsafe")
        return f"{attempt_id}-{label_leaf}.artifact"


def _proposal_from_row(row: tuple[object, ...]) -> TrustedHostPromotionProposal:
    metadata = _json_object(str(row[15]), "promotion metadata")
    authority_snapshot_json = (
        _json_object(str(row[17]), "promotion authority snapshot") if row[17] is not None else None
    )
    return TrustedHostPromotionProposal(
        proposal_id=str(row[0]),
        request_id=str(row[1]),
        status=_proposal_display_status(str(row[2])),
        created_at=str(row[3]),
        updated_at=str(row[4]),
        workspace_id=str(row[5]),
        sandbox_descriptor_id=str(row[6]),
        sandbox_descriptor_hash=str(row[7]),
        sandbox_id=str(row[8]),
        source_artifact_label=str(row[9]),
        host_staging_label=str(row[10]),
        artifact_sha256=str(row[11]),
        artifact_size_bytes=int(str(row[12])),
        artifact_media_label=str(row[13]),
        proposal_hash=str(row[14]),
        metadata=metadata,
        authority_schema_version=_optional_string(row[16]),
        authority_snapshot_json=authority_snapshot_json,
        authority_snapshot_hash=_optional_string(row[18]),
        requester_principal_id=_optional_string(row[19]),
        requester_principal_generation=_optional_string(row[20]),
        executor_principal_id=_optional_string(row[21]),
        executor_principal_generation=_optional_string(row[22]),
    )


def _proposal_hash_evidence(proposal: TrustedHostPromotionProposal) -> JsonObject:
    metadata = {
        key: value for key, value in proposal.metadata.items() if key != "approval_id"
    }
    return {
        "proposal_id": proposal.proposal_id,
        "request_id": proposal.request_id,
        "workspace_id": proposal.workspace_id,
        "sandbox_descriptor_id": proposal.sandbox_descriptor_id,
        "sandbox_descriptor_hash": proposal.sandbox_descriptor_hash,
        "sandbox_id": proposal.sandbox_id,
        "source_artifact_label": proposal.source_artifact_label,
        "host_staging_label": proposal.host_staging_label,
        "artifact_sha256": proposal.artifact_sha256,
        "artifact_size_bytes": proposal.artifact_size_bytes,
        "artifact_media_label": proposal.artifact_media_label,
        "metadata": metadata,
        "authority_snapshot_hash": proposal.authority_snapshot_hash,
    }


def _attempt_from_row(row: tuple[object, ...]) -> TrustedHostPromotionAttempt:
    metadata = _json_object(str(row[12]), "promotion attempt metadata")
    staged_sha256 = row[7] if row[7] is not None else None
    failure_reason = row[9] if row[9] is not None else None
    return TrustedHostPromotionAttempt(
        attempt_id=str(row[0]),
        approval_id=str(row[1]),
        proposal_id=str(row[2]),
        request_id=str(row[3]),
        workspace_id=str(row[4]),
        host_staging_label=str(row[5]),
        artifact_sha256=str(row[6]),
        staged_sha256=str(staged_sha256) if staged_sha256 is not None else None,
        status=_attempt_display_status(str(row[8])),
        failure_reason=str(failure_reason) if failure_reason is not None else None,
        created_at=str(row[10]),
        updated_at=str(row[11]),
        metadata=metadata,
        record_version=str(row[13]),
        authority_snapshot_hash=_optional_string(row[14]),
        executor_principal_id=_optional_string(row[15]),
        executor_principal_generation=_optional_string(row[16]),
    )


def _proposal_storage_status(status: str) -> str:
    if status.startswith("legacy_"):
        raise TrustedHostPromotionError("legacy promotion proposal is immutable")
    if status.startswith("v2_"):
        return status
    return f"v2_{status}"


def _proposal_display_status(status: str) -> str:
    return status.removeprefix("v2_") if status.startswith("v2_") else status


def _attempt_storage_status(status: str) -> str:
    if status.startswith("legacy_"):
        raise TrustedHostPromotionError("legacy promotion attempt is immutable")
    if status.startswith("v2_"):
        return status
    if status == "recovery_required":
        return "v2_placement_evidence_recovery_required"
    return f"v2_{status}"


def _attempt_display_status(status: str) -> str:
    if status == "v2_placement_evidence_recovery_required":
        return "placement_evidence_recovery_required"
    return status.removeprefix("v2_") if status.startswith("v2_") else status


def _optional_string(value: object) -> str | None:
    return str(value) if value is not None else None


def _json_object(raw: str, label: str) -> JsonObject:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise TrustedHostPromotionError(f"failed to decode {label}") from exc
    if not isinstance(value, dict):
        raise TrustedHostPromotionError(f"failed to decode {label}")
    return cast(JsonObject, value)


def _json_object_without_duplicates(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _attempt_id_for_proposal(proposal_id: str) -> str:
    digest = hashlib.sha256(proposal_id.encode("utf-8")).hexdigest()
    return f"thpa_{digest[:32]}"


def _read_source_artifact(filesystem: FilesystemReadTools, relative_path: str) -> bytes:
    safe_path = _safe_relative_path(relative_path, label="source_artifact_path")
    target = filesystem.workspace_root / safe_path
    try:
        data = filesystem.read_file_bytes(target)
    except ReadToolError as exc:
        raise TrustedHostPromotionError("source artifact cannot be safely read") from exc
    if len(data) > MAX_PROMOTION_ARTIFACT_BYTES:
        raise TrustedHostPromotionError("source artifact exceeds promotion limit")
    if b"\x00" in data:
        raise TrustedHostPromotionError("source artifact is not supported text")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TrustedHostPromotionError("source artifact is not supported text") from exc
    if not unicodedata.is_normalized("NFC", text):
        raise TrustedHostPromotionError("source artifact is not Unicode-normalized")
    return data


def _safe_relative_path(value: str, *, label: str) -> str:
    _reject_control_or_unnormalized(value, label=label)
    lowered = value.lower()
    if any(token in lowered for token in ("%2e", "%2f", "%5c")):
        raise ValueError("encoded path tokens are not allowed")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("path escapes the sandbox scope")
    for part in path.parts:
        if part.startswith(".") or "/" in part or "\\" in part:
            raise ValueError("path is hidden or sensitive")
        _ensure_not_sensitive_label(part)
    return path.as_posix()


def _ensure_not_sensitive_label(value: str) -> None:
    lowered = value.lower()
    sensitive_exact = {".git", ".env", ".ssh", ".aws", "id_rsa", "id_ed25519"}
    sensitive_markers = ("secret", "token", "password", "credential", "private")
    if lowered in sensitive_exact or any(marker in lowered for marker in sensitive_markers):
        raise ValueError("label is hidden or sensitive")


def _reject_control_or_unnormalized(value: str, *, label: str) -> None:
    if any(
        ord(character) < 32
        or ord(character) == 127
        or unicodedata.category(character) in {"Cc", "Cf", "Cs"}
        for character in value
    ):
        raise ValueError(f"{label} contains control characters")
    if not unicodedata.is_normalized("NFC", value):
        raise ValueError(f"{label} is not Unicode-normalized")


def _scope_string(scope: JsonObject, key: str) -> str | None:
    value = scope.get(key)
    return value if isinstance(value, str) else None


def _output_policy() -> JsonObject:
    return {
        "staging_only": True,
        "file_contents_included": False,
        "raw_host_paths_included": False,
        "raw_source_paths_included": False,
        "diffs_included": False,
        "prompts_included": False,
        "model_outputs_included": False,
        "shell_output_included": False,
        "environment_values_included": False,
        "registry_urls_included": False,
        "dependency_names_included": False,
        "package_scripts_included": False,
        "secrets_included": False,
    }

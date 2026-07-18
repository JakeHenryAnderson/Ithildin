"""Staging-only trusted-host promotion evidence and placement."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import uuid4

from ithildin_schemas import ApprovalRequest, JsonObject, JsonValue, canonical_json, sha256_digest
from ithildin_schemas.models import StrictBaseModel
from pydantic import Field, field_validator

from ithildin_api.approvals import ApprovalError, ApprovalService, CreateApprovalInput
from ithildin_api.read_tools import FilesystemReadTools, ReadToolError, ReadToolExecutor
from ithildin_api.sandbox_descriptors import SandboxDescriptorStore

TRUSTED_HOST_PROMOTION_TOOL = "trusted_host.promotion.stage"
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
    principal: JsonObject = Field(
        default_factory=lambda: cast(JsonObject, {"id": "admin:local"})
    )

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
        }

    def summary(self) -> JsonObject:
        return {
            "promotion_proposal_id": self.proposal_id,
            "request_id": self.request_id,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
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
            "output_policy": _output_policy(),
        }


class TrustedHostPromotionStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS trusted_host_promotion_proposals (
                    proposal_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    sandbox_descriptor_id TEXT NOT NULL,
                    sandbox_descriptor_hash TEXT NOT NULL,
                    sandbox_id TEXT NOT NULL,
                    source_artifact_label TEXT NOT NULL,
                    host_staging_label TEXT NOT NULL,
                    artifact_sha256 TEXT NOT NULL,
                    artifact_size_bytes INTEGER NOT NULL,
                    artifact_media_label TEXT NOT NULL,
                    proposal_hash TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS trusted_host_promotion_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    approval_id TEXT NOT NULL UNIQUE,
                    proposal_id TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    host_staging_label TEXT NOT NULL,
                    artifact_sha256 TEXT NOT NULL,
                    staged_sha256 TEXT,
                    status TEXT NOT NULL,
                    failure_reason TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def create_proposal(self, proposal: TrustedHostPromotionProposal) -> None:
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO trusted_host_promotion_proposals (
                    proposal_id, request_id, status, created_at, updated_at,
                    workspace_id, sandbox_descriptor_id, sandbox_descriptor_hash,
                    sandbox_id, source_artifact_label, host_staging_label,
                    artifact_sha256, artifact_size_bytes, artifact_media_label,
                    proposal_hash, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal.proposal_id,
                    proposal.request_id,
                    proposal.status,
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
                ),
            )
            connection.commit()

    def get_proposal(self, proposal_id: str) -> TrustedHostPromotionProposal:
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT proposal_id, request_id, status, created_at, updated_at,
                       workspace_id, sandbox_descriptor_id, sandbox_descriptor_hash,
                       sandbox_id, source_artifact_label, host_staging_label,
                       artifact_sha256, artifact_size_bytes, artifact_media_label,
                       proposal_hash, metadata_json
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
                       proposal_hash, metadata_json
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
                (status, datetime.now(UTC).isoformat(), proposal_id),
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
                WHERE proposal_id = ? AND status = 'approval_required'
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
                connection.execute(
                    """
                    INSERT INTO trusted_host_promotion_attempts (
                        attempt_id, approval_id, proposal_id, request_id, workspace_id,
                        host_staging_label, artifact_sha256, staged_sha256, status,
                        failure_reason, created_at, updated_at, metadata_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        attempt.status,
                        attempt.failure_reason,
                        attempt.created_at,
                        attempt.updated_at,
                        canonical_json(attempt.metadata),
                    ),
                )
                connection.commit()
        except sqlite3.IntegrityError as exc:
            raise TrustedHostPromotionError(
                "trusted-host promotion attempt already exists for approval or proposal"
            ) from exc

    def get_attempt_for_proposal(
        self,
        proposal_id: str,
    ) -> TrustedHostPromotionAttempt | None:
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT attempt_id, approval_id, proposal_id, request_id, workspace_id,
                       host_staging_label, artifact_sha256, staged_sha256, status,
                       failure_reason, created_at, updated_at, metadata_json
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
                (status, staged_sha256, failure_reason, datetime.now(UTC).isoformat(), attempt_id),
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
                       failure_reason, created_at, updated_at, metadata_json
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
                       failure_reason, created_at, updated_at, metadata_json
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
        staging_root: Path,
    ) -> None:
        self.store = store
        self.read_executor = read_executor
        self.descriptor_store = descriptor_store
        self.staging_root = staging_root

    def create_proposal(
        self,
        payload: TrustedHostPromotionProposalInput,
        *,
        approval_service: ApprovalService,
    ) -> JsonObject:
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
                "output_policy": _output_policy(),
            },
        )
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
        )
        self.store.create_proposal(proposal)
        scope = {
            "tool_name": TRUSTED_HOST_PROMOTION_TOOL,
            **proposal.scope_metadata(),
            "request_hash": sha256_digest(proposal.scope_metadata()),
        }
        approval = approval_service.create_pending(
            CreateApprovalInput(
                request_id=request_id,
                principal=payload.principal,
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
        )
        self.store.bind_proposal_approval(proposal_id, approval.approval_id)
        return {
            **proposal.summary(),
            "approval_id": approval.approval_id,
            "approval_status": approval.status.value,
            "approval_expires_at": approval.expires_at.isoformat(),
        }

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
            for key, value in proposal.scope_metadata().items():
                if scope.get(key) != value:
                    reasons.append(f"{key} mismatch")
            if approval.resource.get("workspace_id") != proposal.workspace_id:
                reasons.append("approval resource workspace mismatch")
            if approval.resource.get("host_staging_label") != proposal.host_staging_label:
                reasons.append("approval resource staging label mismatch")
            if approval.request_id != proposal.request_id:
                reasons.append("approval request mismatch")
            if proposal.metadata.get("approval_id") != approval.approval_id:
                reasons.append("proposal approval mismatch")
            if scope.get("request_hash") != sha256_digest(proposal.scope_metadata()):
                reasons.append("approval scope request hash mismatch")
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
    ) -> JsonObject:
        proposal = self.store.get_proposal(proposal_id)
        approval = approval_service.get(approval_id)
        review = self.approval_review(
            approval,
            expected_proposal_id=proposal.proposal_id,
        )
        if review["valid"] is not True:
            raise TrustedHostPromotionError("trusted-host promotion approval binding review failed")
        if proposal.status != "approval_required":
            raise TrustedHostPromotionError("trusted-host promotion proposal is not applicable")
        if self.store.get_attempt_for_proposal(proposal.proposal_id) is not None:
            raise TrustedHostPromotionError(
                "trusted-host promotion proposal already has an attempt"
            )
        artifact_bytes = _read_source_artifact(
            self._filesystem(proposal.workspace_id),
            proposal.source_artifact_label.split("/", 3)[-1],
        )
        if _sha256_bytes(artifact_bytes) != proposal.artifact_sha256:
            raise TrustedHostPromotionError("source artifact hash mismatch")
        attempt_id = _attempt_id_for_proposal(proposal.proposal_id)
        now = datetime.now(UTC).isoformat()
        attempt = TrustedHostPromotionAttempt(
            attempt_id=attempt_id,
            approval_id=approval_id,
            proposal_id=proposal.proposal_id,
            request_id=approval.request_id,
            workspace_id=proposal.workspace_id,
            host_staging_label=proposal.host_staging_label,
            artifact_sha256=proposal.artifact_sha256,
            staged_sha256=None,
            status="prepared",
            failure_reason=None,
            created_at=now,
            updated_at=now,
            metadata={
                "proposal_hash": proposal.proposal_hash,
                "sandbox_descriptor_id": proposal.sandbox_descriptor_id,
                "sandbox_descriptor_hash": proposal.sandbox_descriptor_hash,
                "output_policy": _output_policy(),
            },
        )
        placed = False
        execution_begun = False
        attempt_created = False
        try:
            approval_service.begin_execution(approval_id, approval.request_hash)
            execution_begun = True
            self.store.create_attempt(attempt)
            attempt_created = True
            destination = self._destination_for(proposal, attempt_id)
            _copy_without_overwrite(artifact_bytes, destination)
            placed = True
            staged_sha256 = _sha256_bytes(destination.read_bytes())
            if staged_sha256 != proposal.artifact_sha256:
                raise TrustedHostPromotionError("staged artifact hash mismatch")
            self.store.set_attempt_status(
                attempt_id,
                "staged",
                staged_sha256=staged_sha256,
            )
            approval_service.complete_execution(approval_id, success=True)
            self.store.set_proposal_status(
                proposal.proposal_id,
                "completion_evidence_pending",
            )
            return {
                "status": "completion_evidence_pending",
                "promotion_attempt_id": attempt_id,
                "approval_id": approval_id,
                "promotion_proposal_id": proposal.proposal_id,
                "workspace_id": proposal.workspace_id,
                "host_staging_label": proposal.host_staging_label,
                "artifact_sha256": proposal.artifact_sha256,
                "staged_sha256": staged_sha256,
                "output_policy": _output_policy(),
            }
        except (OSError, ApprovalError, TrustedHostPromotionError) as exc:
            if not execution_begun:
                raise
            status = "recovery_required" if placed else "failed"
            if attempt_created:
                self.store.set_attempt_status(attempt_id, status, failure_reason=str(exc))
            if not placed:
                try:
                    approval_service.complete_execution(approval_id, success=False)
                except ApprovalError:
                    pass
                if attempt_created:
                    self.store.set_proposal_status(proposal.proposal_id, "failed")
            raise TrustedHostPromotionError("trusted-host promotion did not complete") from exc

    def complete_with_evidence(self, attempt_id: str) -> TrustedHostPromotionAttempt:
        attempt = self.store.get_attempt(attempt_id)
        if attempt.status != "staged" or attempt.staged_sha256 != attempt.artifact_sha256:
            raise TrustedHostPromotionError(
                "trusted-host promotion completion evidence is not finalizable"
            )
        completed = self.store.set_attempt_status(
            attempt_id,
            "completed",
            staged_sha256=attempt.staged_sha256,
        )
        self.store.set_proposal_status(attempt.proposal_id, "completed")
        return completed

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
        if any(attempt["status"] == "recovery_required" for attempt in attempts):
            diagnostic_status = "recovery_required"
        elif incomplete or stuck_approvals:
            diagnostic_status = "ambiguous"
        return {
            "status": diagnostic_status,
            "attempts": cast(JsonValue, attempts),
            "stuck_approvals": cast(JsonValue, stuck_approvals),
            "recommendations": cast(JsonValue, [
                {
                    "type": "manual_review",
                    "message": (
                        "Review proposal, approval, attempt, destination label, "
                        "and audit evidence; do not retry or repair automatically."
                    ),
                }
            ])
            if diagnostic_status != "clean"
            else cast(
                JsonValue,
                [{"type": "none", "message": "No incomplete trusted-host attempts detected."}],
            ),
            "output_policy": _output_policy(),
        }

    def _filesystem(self, workspace_id: str) -> FilesystemReadTools:
        try:
            return self.read_executor.filesystems[workspace_id]
        except KeyError as exc:
            raise TrustedHostPromotionError("unknown workspace") from exc

    def _destination_for(self, proposal: TrustedHostPromotionProposal, attempt_id: str) -> Path:
        label_leaf = proposal.host_staging_label.removeprefix("host-staging://")
        if not SAFE_NAME_RE.fullmatch(label_leaf):
            raise TrustedHostPromotionError("host staging label is unsafe")
        destination_dir = self.staging_root / proposal.workspace_id / proposal.proposal_id
        destination = destination_dir / f"{attempt_id}-{label_leaf}.artifact"
        _ensure_under_root(self.staging_root, destination)
        return destination


def _proposal_from_row(row: tuple[object, ...]) -> TrustedHostPromotionProposal:
    metadata = _json_object(str(row[15]), "promotion metadata")
    return TrustedHostPromotionProposal(
        proposal_id=str(row[0]),
        request_id=str(row[1]),
        status=str(row[2]),
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
    )


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
        status=str(row[8]),
        failure_reason=str(failure_reason) if failure_reason is not None else None,
        created_at=str(row[10]),
        updated_at=str(row[11]),
        metadata=metadata,
    )


def _json_object(raw: str, label: str) -> JsonObject:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise TrustedHostPromotionError(f"failed to decode {label}") from exc
    if not isinstance(value, dict):
        raise TrustedHostPromotionError(f"failed to decode {label}")
    return cast(JsonObject, value)


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


def _copy_without_overwrite(data: bytes, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    _ensure_under_root(destination.parent.parent.parent, destination)
    try:
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
    except FileExistsError as exc:
        raise TrustedHostPromotionError("host staging destination already exists") from exc
    except OSError as exc:
        raise TrustedHostPromotionError("host staging placement failed") from exc


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


def _ensure_under_root(root: Path, path: Path) -> None:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError as exc:
        raise TrustedHostPromotionError("host staging destination escapes staging root") from exc


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

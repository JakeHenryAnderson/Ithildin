"""Stored unified-diff patch proposals."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import stat
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import uuid4

from ithildin_schemas import ApprovalRequest, JsonObject, canonical_json, sha256_digest

from ithildin_api.approvals import ApprovalError, ApprovalService
from ithildin_api.read_tools import FilesystemReadTools, ReadToolError

PATCH_PROPOSE_TOOL = "fs.patch.propose"
PATCH_APPLY_TOOL = "fs.patch.apply"


class PatchProposalError(RuntimeError):
    """Raised when a patch proposal cannot be safely stored or applied."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class PatchProposal:
    proposal_id: str
    request_id: str
    principal: JsonObject
    workspace_id: str
    path: str
    unified_diff: str
    base_file_hash: str
    proposal_hash: str
    status: str
    created_at: datetime
    updated_at: datetime
    metadata: JsonObject

    def summary(self) -> JsonObject:
        return {
            "proposal_id": self.proposal_id,
            "request_id": self.request_id,
            "workspace_id": self.workspace_id,
            "path": self.path,
            "base_file_hash": self.base_file_hash,
            "proposal_hash": self.proposal_hash,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }

    def detail(self) -> JsonObject:
        result = self.summary()
        result["unified_diff"] = self.unified_diff
        return result

    def tool_result(self) -> JsonObject:
        result = self.summary()
        result["proposal_status"] = result.pop("status")
        return result


@dataclass(frozen=True)
class PatchApplyAttempt:
    attempt_id: str
    approval_id: str
    proposal_id: str
    request_id: str
    workspace_id: str
    path: str
    proposal_hash: str
    base_file_hash: str
    expected_post_apply_hash: str
    status: str
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime
    metadata: JsonObject

    def summary(self) -> JsonObject:
        return {
            "attempt_id": self.attempt_id,
            "approval_id": self.approval_id,
            "proposal_id": self.proposal_id,
            "request_id": self.request_id,
            "workspace_id": self.workspace_id,
            "path": self.path,
            "proposal_hash": self.proposal_hash,
            "base_file_hash": self.base_file_hash,
            "expected_post_apply_hash": self.expected_post_apply_hash,
            "status": self.status,
            "failure_reason": self.failure_reason,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


PatchApplyFaultHook = Callable[[str], None]
PatchApplyCompletionHook = Callable[[PatchProposal], None]


class PatchProposalStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS patch_proposals (
                    proposal_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    principal_json TEXT NOT NULL,
                    workspace_id TEXT NOT NULL DEFAULT 'default',
                    path TEXT NOT NULL,
                    unified_diff TEXT NOT NULL,
                    base_file_hash TEXT NOT NULL,
                    proposal_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(patch_proposals)").fetchall()
            }
            if "workspace_id" not in columns:
                connection.execute(
                    "ALTER TABLE patch_proposals "
                    "ADD COLUMN workspace_id TEXT NOT NULL DEFAULT 'default'"
                )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS patch_apply_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    approval_id TEXT NOT NULL UNIQUE,
                    proposal_id TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    path TEXT NOT NULL,
                    proposal_hash TEXT NOT NULL,
                    base_file_hash TEXT NOT NULL,
                    expected_post_apply_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    failure_reason TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def create(self, proposal: PatchProposal) -> PatchProposal:
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO patch_proposals (
                    proposal_id,
                    request_id,
                    principal_json,
                    workspace_id,
                    path,
                    unified_diff,
                    base_file_hash,
                    proposal_hash,
                    status,
                    created_at,
                    updated_at,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal.proposal_id,
                    proposal.request_id,
                    canonical_json(proposal.principal),
                    proposal.workspace_id,
                    proposal.path,
                    proposal.unified_diff,
                    proposal.base_file_hash,
                    proposal.proposal_hash,
                    proposal.status,
                    proposal.created_at.isoformat(),
                    proposal.updated_at.isoformat(),
                    canonical_json(proposal.metadata),
                ),
            )
            connection.commit()
        return proposal

    def list(self) -> list[PatchProposal]:
        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    proposal_id,
                    request_id,
                    principal_json,
                    workspace_id,
                    path,
                    unified_diff,
                    base_file_hash,
                    proposal_hash,
                    status,
                    created_at,
                    updated_at,
                    metadata_json
                FROM patch_proposals
                ORDER BY created_at ASC
                """
            ).fetchall()
        return [_proposal_from_row(row) for row in rows]

    def get(self, proposal_id: str) -> PatchProposal:
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT
                    proposal_id,
                    request_id,
                    principal_json,
                    workspace_id,
                    path,
                    unified_diff,
                    base_file_hash,
                    proposal_hash,
                    status,
                    created_at,
                    updated_at,
                    metadata_json
                FROM patch_proposals
                WHERE proposal_id = ?
                """,
                (proposal_id,),
            ).fetchone()
        if row is None:
            raise PatchProposalError(f"patch proposal not found: {proposal_id}")
        return _proposal_from_row(row)

    def set_status(self, proposal_id: str, status: str) -> PatchProposal:
        with sqlite3.connect(self.db_path) as connection:
            updated = connection.execute(
                """
                UPDATE patch_proposals
                SET status = ?,
                    updated_at = ?
                WHERE proposal_id = ?
                """,
                (status, datetime.now(UTC).isoformat(), proposal_id),
            ).rowcount
            connection.commit()
        if updated != 1:
            raise PatchProposalError(f"patch proposal not found: {proposal_id}")
        return self.get(proposal_id)

    def compare_and_set_status(
        self,
        proposal_id: str,
        *,
        expected_status: str,
        next_status: str,
    ) -> PatchProposal:
        with sqlite3.connect(self.db_path) as connection:
            updated = connection.execute(
                """
                UPDATE patch_proposals
                SET status = ?,
                    updated_at = ?
                WHERE proposal_id = ?
                  AND status = ?
                """,
                (next_status, datetime.now(UTC).isoformat(), proposal_id, expected_status),
            ).rowcount
            connection.commit()
        if updated != 1:
            current = self.get(proposal_id)
            raise PatchProposalError(
                f"patch proposal is not {expected_status}: {current.status}"
            )
        return self.get(proposal_id)

    def create_apply_attempt(self, attempt: PatchApplyAttempt) -> PatchApplyAttempt:
        try:
            with sqlite3.connect(self.db_path) as connection:
                connection.execute(
                    """
                    INSERT INTO patch_apply_attempts (
                        attempt_id,
                        approval_id,
                        proposal_id,
                        request_id,
                        workspace_id,
                        path,
                        proposal_hash,
                        base_file_hash,
                        expected_post_apply_hash,
                        status,
                        failure_reason,
                        created_at,
                        updated_at,
                        metadata_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        attempt.attempt_id,
                        attempt.approval_id,
                        attempt.proposal_id,
                        attempt.request_id,
                        attempt.workspace_id,
                        attempt.path,
                        attempt.proposal_hash,
                        attempt.base_file_hash,
                        attempt.expected_post_apply_hash,
                        attempt.status,
                        attempt.failure_reason,
                        attempt.created_at.isoformat(),
                        attempt.updated_at.isoformat(),
                        canonical_json(attempt.metadata),
                    ),
                )
                connection.commit()
        except sqlite3.IntegrityError as exc:
            raise PatchProposalError("patch apply attempt already exists for approval") from exc
        return attempt

    def list_apply_attempts(self) -> Sequence[PatchApplyAttempt]:
        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    attempt_id,
                    approval_id,
                    proposal_id,
                    request_id,
                    workspace_id,
                    path,
                    proposal_hash,
                    base_file_hash,
                    expected_post_apply_hash,
                    status,
                    failure_reason,
                    created_at,
                    updated_at,
                    metadata_json
                FROM patch_apply_attempts
                ORDER BY created_at ASC
                """
            ).fetchall()
        return [_apply_attempt_from_row(row) for row in rows]

    def set_apply_attempt_status(
        self,
        attempt_id: str,
        status: str,
        *,
        failure_reason: str | None = None,
    ) -> PatchApplyAttempt:
        with sqlite3.connect(self.db_path) as connection:
            current = connection.execute(
                "SELECT status FROM patch_apply_attempts WHERE attempt_id = ?",
                (attempt_id,),
            ).fetchone()
            if current is None:
                raise PatchProposalError(f"patch apply attempt not found: {attempt_id}")
            current_status = str(current[0])
            if not _apply_attempt_transition_allowed(current_status, status):
                raise PatchProposalError(
                    f"invalid patch apply attempt transition: {current_status} -> {status}"
                )
            updated = connection.execute(
                """
                UPDATE patch_apply_attempts
                SET status = ?,
                    failure_reason = COALESCE(?, failure_reason),
                    updated_at = ?
                WHERE attempt_id = ?
                """,
                (status, failure_reason, datetime.now(UTC).isoformat(), attempt_id),
            ).rowcount
            connection.commit()
        if updated != 1:
            raise PatchProposalError(f"patch apply attempt not found: {attempt_id}")
        return self.get_apply_attempt(attempt_id)

    def get_apply_attempt(self, attempt_id: str) -> PatchApplyAttempt:
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT
                    attempt_id,
                    approval_id,
                    proposal_id,
                    request_id,
                    workspace_id,
                    path,
                    proposal_hash,
                    base_file_hash,
                    expected_post_apply_hash,
                    status,
                    failure_reason,
                    created_at,
                    updated_at,
                    metadata_json
                FROM patch_apply_attempts
                WHERE attempt_id = ?
                """,
                (attempt_id,),
            ).fetchone()
        if row is None:
            raise PatchProposalError(f"patch apply attempt not found: {attempt_id}")
        return _apply_attempt_from_row(row)


class PatchProposalService:
    def __init__(
        self,
        store: PatchProposalStore,
        filesystem: FilesystemReadTools,
        max_patch_bytes: int,
        filesystems: dict[str, FilesystemReadTools] | None = None,
        default_workspace_id: str | None = None,
        apply_fault_hook: PatchApplyFaultHook | None = None,
    ) -> None:
        self.store = store
        self.filesystem = filesystem
        self.filesystems = filesystems or {filesystem.workspace_id: filesystem}
        self.default_workspace_id = default_workspace_id or filesystem.workspace_id
        self.max_patch_bytes = max_patch_bytes
        self.apply_fault_hook = apply_fault_hook

    def create_proposal(
        self,
        *,
        request_id: str,
        principal: JsonObject,
        path: str,
        unified_diff: str,
        workspace_id: str | None = None,
    ) -> PatchProposal:
        if _utf8_size(unified_diff, "patch") > self.max_patch_bytes:
            raise PatchProposalError("patch exceeds configured size limit")

        filesystem = self._filesystem(workspace_id)
        try:
            target = filesystem.resolve_existing_path(path)
        except ReadToolError as exc:
            raise PatchProposalError(exc.reason) from exc
        if not target.is_file():
            raise PatchProposalError("patch target is not a file")

        try:
            current_content = filesystem.read_text_file(target)
        except ReadToolError as exc:
            raise PatchProposalError(exc.reason) from exc

        normalized_path = filesystem.relative_path(target)
        normalized_diff = normalize_unified_diff(unified_diff)
        validate_unified_diff(
            target_path=normalized_path,
            current_content=current_content,
            unified_diff=normalized_diff,
        )
        base_file_hash = sha256_digest(current_content)
        proposal_hash = sha256_digest(
            {
                "workspace_id": filesystem.workspace_id,
                "path": normalized_path,
                "unified_diff": normalized_diff,
                "base_file_hash": base_file_hash,
            }
        )
        now = datetime.now(UTC)
        proposal = PatchProposal(
            proposal_id=_new_id("patch"),
            request_id=request_id,
            principal=principal,
            workspace_id=filesystem.workspace_id,
            path=normalized_path,
            unified_diff=normalized_diff,
            base_file_hash=base_file_hash,
            proposal_hash=proposal_hash,
            status="proposed",
            created_at=now,
            updated_at=now,
            metadata={"format": "unified_diff"},
        )
        return self.store.create(proposal)

    def list_proposals(self) -> list[PatchProposal]:
        return self.store.list()

    def get_proposal(self, proposal_id: str) -> PatchProposal:
        return self.store.get(proposal_id)

    def list_apply_attempts(self) -> Sequence[PatchApplyAttempt]:
        return self.store.list_apply_attempts()

    def proposal_review(self, proposal: PatchProposal) -> JsonObject:
        review: JsonObject = {
            "workspace_id": proposal.workspace_id,
            "target_path": proposal.path,
            "proposal_status": proposal.status,
            "current_base_file_hash": None,
            "base_file_hash_matches": False,
            "stale": True,
            "stale_reason": None,
        }
        try:
            filesystem = self._filesystem(proposal.workspace_id)
            target = filesystem.resolve_existing_path(proposal.path)
            current_content = filesystem.read_text_file(target)
            current_hash = sha256_digest(current_content)
        except (PatchProposalError, ReadToolError) as exc:
            review["stale_reason"] = str(exc)
            return review

        review["current_base_file_hash"] = current_hash
        review["base_file_hash_matches"] = current_hash == proposal.base_file_hash
        review["stale"] = proposal.status != "proposed" or current_hash != proposal.base_file_hash
        if proposal.status != "proposed":
            review["stale_reason"] = f"proposal is {proposal.status}"
        elif current_hash != proposal.base_file_hash:
            review["stale_reason"] = "target file changed since proposal"
        else:
            review["stale_reason"] = None
        return review

    def approval_review(
        self,
        approval: ApprovalRequest,
        *,
        expected_manifest_hash: str,
        expected_manifest_version: str,
        expected_tool_input_schema_hash: str,
        expected_policy_engine: str,
        expected_policy_hash: str,
        expected_policy_version: str,
        expected_policy_document_version: str,
        expected_matched_rules: list[str],
        expected_principal: JsonObject,
    ) -> JsonObject:
        checks: dict[str, bool] = {}
        reasons: list[str] = []
        proposal_review: JsonObject | None = None

        def check(name: str, passed: bool, reason: str) -> None:
            checks[name] = passed
            if not passed:
                reasons.append(reason)

        scope = approval.one_time_scope
        check(
            "tool_name",
            approval.tool_name == PATCH_APPLY_TOOL,
            "approval is not for patch apply",
        )
        check(
            "scope_tool_name",
            _optional_scope_string(scope, "tool_name") == PATCH_APPLY_TOOL,
            "scope tool mismatch",
        )
        check(
            "request_hash",
            _optional_scope_string(scope, "request_hash") == approval.request_hash,
            "request hash mismatch",
        )
        check(
            "expiry",
            _optional_scope_string(scope, "expires_at") == approval.expires_at.isoformat(),
            "expiry mismatch",
        )
        check(
            "manifest_hash",
            _optional_scope_string(scope, "manifest_hash") == expected_manifest_hash,
            "manifest hash mismatch",
        )
        check(
            "manifest_version",
            _optional_scope_string(scope, "manifest_version") == expected_manifest_version,
            "manifest version mismatch",
        )
        check(
            "tool_input_schema_hash",
            _optional_scope_string(scope, "tool_input_schema_hash")
            == expected_tool_input_schema_hash,
            "tool input schema mismatch",
        )
        check(
            "policy_engine",
            _optional_scope_string(scope, "policy_engine") == expected_policy_engine,
            "policy engine mismatch",
        )
        check(
            "policy_hash",
            _optional_scope_string(scope, "policy_hash") == expected_policy_hash,
            "policy hash mismatch",
        )
        check(
            "policy_version",
            _optional_scope_string(scope, "policy_version") == expected_policy_version,
            "policy version mismatch",
        )
        check(
            "policy_document_version",
            _optional_scope_string(scope, "policy_document_version")
            == expected_policy_document_version,
            "policy document version mismatch",
        )
        check(
            "matched_rules",
            _scope_string_list(scope, "matched_rules") == expected_matched_rules,
            "matched rules mismatch",
        )
        requesting_principal = _scope_object_or_none(scope, "requesting_principal")
        check(
            "requesting_principal",
            requesting_principal is not None
            and canonical_json(requesting_principal) == canonical_json(approval.principal)
            and canonical_json(requesting_principal) == canonical_json(expected_principal),
            "requesting principal mismatch",
        )

        proposal_id = _optional_scope_string(scope, "proposal_id")
        if proposal_id is None:
            check("proposal", False, "proposal id missing")
        else:
            try:
                proposal = self.get_proposal(proposal_id)
                proposal_review = self.proposal_review(proposal)
                check(
                    "proposal_hash",
                    proposal.proposal_hash == _optional_scope_string(scope, "proposal_hash"),
                    "proposal hash mismatch",
                )
                check(
                    "base_file_hash",
                    proposal.base_file_hash == _optional_scope_string(scope, "base_file_hash"),
                    "base file hash mismatch",
                )
                check(
                    "workspace_id",
                    proposal.workspace_id == _optional_scope_string(scope, "workspace_id"),
                    "workspace mismatch",
                )
                check(
                    "path",
                    proposal.path == _optional_scope_string(scope, "path"),
                    "path mismatch",
                )
                check(
                    "proposal_status",
                    proposal.status == "proposed",
                    f"proposal is {proposal.status}",
                )
                check(
                    "current_base",
                    proposal_review.get("base_file_hash_matches") is True,
                    str(proposal_review.get("stale_reason") or "base file hash mismatch"),
                )
            except PatchProposalError as exc:
                check("proposal", False, str(exc))

        executable = not reasons and approval.status.value in {"pending", "approved"}
        return cast(
            JsonObject,
            {
                "valid": executable,
                "checks": checks,
                "reasons": reasons,
                "proposal": proposal_review,
            },
        )

    def approval_scope(
        self,
        proposal_id: str,
        *,
        manifest_hash: str,
        manifest_version: str,
        tool_input_schema_hash: str,
        policy_engine: str,
        policy_hash: str,
        policy_version: str,
        policy_document_version: str,
        matched_rules: list[str],
        requesting_principal: JsonObject,
        request_hash: str,
        expires_at: datetime,
    ) -> JsonObject:
        proposal = self.get_proposal(proposal_id)
        if proposal.status != "proposed":
            raise PatchProposalError(f"patch proposal is not proposed: {proposal.status}")
        return cast(
            JsonObject,
            {
                "tool_name": PATCH_APPLY_TOOL,
                "proposal_id": proposal.proposal_id,
                "proposal_hash": proposal.proposal_hash,
                "base_file_hash": proposal.base_file_hash,
                "workspace_id": proposal.workspace_id,
                "path": proposal.path,
                "manifest_hash": manifest_hash,
                "manifest_version": manifest_version,
                "tool_input_schema_hash": tool_input_schema_hash,
                "policy_engine": policy_engine,
                "policy_hash": policy_hash,
                "policy_version": policy_version,
                "policy_document_version": policy_document_version,
                "matched_rules": matched_rules,
                "requesting_principal": requesting_principal,
                "request_hash": request_hash,
                "expires_at": expires_at.isoformat(),
            },
        )

    def patch_apply_diagnostics(self, approval_service: ApprovalService) -> JsonObject:
        attempts = [
            self._attempt_diagnostics(attempt)
            for attempt in self.store.list_apply_attempts()
            if attempt.status not in {"completed", "failed"}
        ]
        stuck_approvals: list[JsonObject] = []
        attempt_approval_ids = {
            str(attempt["approval_id"])
            for attempt in attempts
            if isinstance(attempt.get("approval_id"), str)
        }
        for approval in approval_service.list():
            if approval.tool_name != PATCH_APPLY_TOOL or approval.status.value != "executing":
                continue
            stuck_approvals.append(
                {
                    "approval_id": approval.approval_id,
                    "request_id": approval.request_id,
                    "tool_name": approval.tool_name,
                    "has_apply_attempt": approval.approval_id in attempt_approval_ids,
                    "proposal_id": _optional_scope_string(
                        approval.one_time_scope,
                        "proposal_id",
                    ),
                    "workspace_id": _optional_scope_string(
                        approval.one_time_scope,
                        "workspace_id",
                    ),
                    "path": _optional_scope_string(approval.one_time_scope, "path"),
                }
            )

        ambiguous = any(
            attempt.get("diagnostic_status") == "ambiguous" for attempt in attempts
        ) or any(not approval["has_apply_attempt"] for approval in stuck_approvals)
        recovery_required = any(
            attempt.get("diagnostic_status") == "recovery_required" for attempt in attempts
        )
        if ambiguous:
            status = "ambiguous"
        elif recovery_required:
            status = "recovery_required"
        else:
            status = "clean"

        recommendations: list[JsonObject] = []
        if recovery_required:
            recommendations.append(
                {
                    "type": "manual_review",
                    "message": (
                        "A patch apply appears to have replaced the target file but did not "
                        "complete all database/audit state transitions. Review the attempt "
                        "metadata and audit chain before deciding on manual cleanup."
                    ),
                }
            )
        if ambiguous:
            recommendations.append(
                {
                    "type": "external_review",
                    "message": (
                        "One or more patch apply states are ambiguous. Do not retry or repair "
                        "automatically; inspect the workspace, approval, proposal, and audit "
                        "evidence manually."
                    ),
                }
            )
        if status == "clean":
            recommendations.append(
                {"type": "none", "message": "No incomplete patch apply attempts were detected."}
            )

        return cast(
            JsonObject,
            {
                "status": status,
                "attempts": attempts,
                "stuck_approvals": stuck_approvals,
                "recommendations": recommendations,
            },
        )

    def apply_approved(
        self,
        *,
        approval_service: ApprovalService,
        approval_id: str,
        expected_manifest_hash: str,
        expected_manifest_version: str,
        expected_tool_input_schema_hash: str,
        expected_policy_engine: str,
        expected_policy_hash: str,
        expected_policy_version: str,
        expected_policy_document_version: str,
        expected_matched_rules: list[str],
        expected_principal: JsonObject,
        completion_hook: PatchApplyCompletionHook | None = None,
    ) -> PatchProposal:
        approval = approval_service.get(approval_id)
        proposal = self._proposal_for_approval(
            approval,
            expected_manifest_hash=expected_manifest_hash,
            expected_manifest_version=expected_manifest_version,
            expected_tool_input_schema_hash=expected_tool_input_schema_hash,
            expected_policy_engine=expected_policy_engine,
            expected_policy_hash=expected_policy_hash,
            expected_policy_version=expected_policy_version,
            expected_policy_document_version=expected_policy_document_version,
            expected_matched_rules=expected_matched_rules,
            expected_principal=expected_principal,
        )
        attempt: PatchApplyAttempt | None = None
        file_replaced = False
        applied: PatchProposal | None = None
        proposal_reserved = False
        try:
            self._inject_apply_fault("after_proposal_validation")
            approval_service.begin_execution(approval_id, approval.request_hash)
            self._inject_apply_fault("after_begin_execution")
            target, patched_content = self._prepare_apply(proposal)
            self._inject_apply_fault("after_prepare_apply")
            proposal = self.store.compare_and_set_status(
                proposal.proposal_id,
                expected_status="proposed",
                next_status="applying",
            )
            proposal_reserved = True
            self._inject_apply_fault("after_proposal_reserved")
            expected_post_apply_hash = sha256_digest(patched_content)
            now = datetime.now(UTC)
            attempt = self.store.create_apply_attempt(
                PatchApplyAttempt(
                    attempt_id=_new_id("pa"),
                    approval_id=approval.approval_id,
                    proposal_id=proposal.proposal_id,
                    request_id=approval.request_id,
                    workspace_id=proposal.workspace_id,
                    path=proposal.path,
                    proposal_hash=proposal.proposal_hash,
                    base_file_hash=proposal.base_file_hash,
                    expected_post_apply_hash=expected_post_apply_hash,
                    status="prepared",
                    failure_reason=None,
                    created_at=now,
                    updated_at=now,
                    metadata={"tool_name": PATCH_APPLY_TOOL},
                )
            )
            self._inject_apply_fault("after_create_apply_attempt")
            self._inject_apply_fault("before_atomic_replace")
            filesystem = self._filesystem(proposal.workspace_id)
            _atomic_write_text(
                filesystem.workspace_root,
                proposal.path,
                patched_content,
                expected_base_file_hash=proposal.base_file_hash,
                max_verify_bytes=filesystem.max_read_bytes,
            )
            file_replaced = True
            self._inject_apply_fault("after_atomic_replace")
            self.store.set_apply_attempt_status(attempt.attempt_id, "file_replaced")
            self._inject_apply_fault("after_file_replaced_status")
            self._inject_apply_fault("before_proposal_completion")
            applied = self.store.compare_and_set_status(
                proposal.proposal_id,
                expected_status="applying",
                next_status="applied",
            )
            self._inject_apply_fault("before_approval_completion")
            approval_service.complete_execution(approval_id, success=True)
            self._inject_apply_fault("after_approval_completion")
            if completion_hook is not None:
                try:
                    completion_hook(applied)
                except Exception as exc:
                    raise PatchProposalError("patch apply completion audit failed") from exc
            self._inject_apply_fault("after_completion_hook")
            self.store.set_apply_attempt_status(attempt.attempt_id, "completed")
            self._inject_apply_fault("after_apply_attempt_completion")
        except PatchProposalError as exc:
            self._record_apply_failure(
                approval_service,
                approval_id,
                attempt,
                proposal_id=proposal.proposal_id,
                proposal_reserved=proposal_reserved,
                file_replaced=file_replaced,
                reason=exc.reason,
            )
            raise
        except (OSError, ApprovalError, sqlite3.Error) as exc:
            reason = (
                "patch apply recovery diagnostics required"
                if file_replaced
                else "failed to apply patch safely"
            )
            self._record_apply_failure(
                approval_service,
                approval_id,
                attempt,
                proposal_id=proposal.proposal_id,
                proposal_reserved=proposal_reserved,
                file_replaced=file_replaced,
                reason=reason,
            )
            raise PatchProposalError(reason) from exc

        if applied is None:
            raise PatchProposalError("patch apply did not complete")
        return applied

    def _inject_apply_fault(self, phase: str) -> None:
        if self.apply_fault_hook is not None:
            self.apply_fault_hook(phase)

    def _proposal_for_approval(
        self,
        approval: ApprovalRequest,
        *,
        expected_manifest_hash: str,
        expected_manifest_version: str,
        expected_tool_input_schema_hash: str,
        expected_policy_engine: str,
        expected_policy_hash: str,
        expected_policy_version: str,
        expected_policy_document_version: str,
        expected_matched_rules: list[str],
        expected_principal: JsonObject,
    ) -> PatchProposal:
        if approval.tool_name != PATCH_APPLY_TOOL:
            raise PatchProposalError("approval is not for patch application")
        scope = approval.one_time_scope
        if _scope_string(scope, "tool_name") != PATCH_APPLY_TOOL:
            raise PatchProposalError("approval scope tool mismatch")
        if _scope_string(scope, "request_hash") != approval.request_hash:
            raise PatchProposalError("approval scope request hash mismatch")
        if _scope_string(scope, "expires_at") != approval.expires_at.isoformat():
            raise PatchProposalError("approval scope expiry mismatch")
        if _scope_string(scope, "manifest_hash") != expected_manifest_hash:
            raise PatchProposalError("approval scope manifest hash mismatch")
        if _scope_string(scope, "manifest_version") != expected_manifest_version:
            raise PatchProposalError("approval scope manifest version mismatch")
        if _scope_string(scope, "tool_input_schema_hash") != expected_tool_input_schema_hash:
            raise PatchProposalError("approval scope tool input schema mismatch")
        if _scope_string(scope, "policy_engine") != expected_policy_engine:
            raise PatchProposalError("approval scope policy engine mismatch")
        if _scope_string(scope, "policy_hash") != expected_policy_hash:
            raise PatchProposalError("approval scope policy hash mismatch")
        if _scope_string(scope, "policy_version") != expected_policy_version:
            raise PatchProposalError("approval scope policy version mismatch")
        if _scope_string(scope, "policy_document_version") != expected_policy_document_version:
            raise PatchProposalError("approval scope policy document version mismatch")
        if _scope_string_list(scope, "matched_rules") != expected_matched_rules:
            raise PatchProposalError("approval scope matched rules mismatch")
        requesting_principal = _scope_object(scope, "requesting_principal")
        if canonical_json(requesting_principal) != canonical_json(approval.principal):
            raise PatchProposalError("approval scope principal mismatch")
        if canonical_json(requesting_principal) != canonical_json(expected_principal):
            raise PatchProposalError("approval principal mismatch")
        proposal_id = _scope_string(scope, "proposal_id")
        proposal_hash = _scope_string(scope, "proposal_hash")
        base_file_hash = _scope_string(scope, "base_file_hash")
        path = _scope_string(scope, "path")
        workspace_id = _scope_string(scope, "workspace_id")
        proposal = self.get_proposal(proposal_id)
        if proposal.status != "proposed":
            raise PatchProposalError(f"patch proposal is not proposed: {proposal.status}")
        if proposal.proposal_hash != proposal_hash:
            raise PatchProposalError("patch proposal hash mismatch")
        if proposal.base_file_hash != base_file_hash:
            raise PatchProposalError("patch proposal base hash mismatch")
        if proposal.workspace_id != workspace_id:
            raise PatchProposalError("patch proposal workspace mismatch")
        if proposal.path != path:
            raise PatchProposalError("patch proposal path mismatch")
        return proposal

    def _prepare_apply(self, proposal: PatchProposal) -> tuple[Path, str]:
        filesystem = self._filesystem(proposal.workspace_id)
        try:
            target = filesystem.resolve_existing_path(proposal.path)
        except ReadToolError as exc:
            raise PatchProposalError(exc.reason) from exc
        if not target.is_file():
            raise PatchProposalError("patch target is not a file")
        try:
            current_content = filesystem.read_text_file(target)
        except ReadToolError as exc:
            raise PatchProposalError(exc.reason) from exc
        current_hash = sha256_digest(current_content)
        if current_hash != proposal.base_file_hash:
            raise PatchProposalError("patch target has changed since proposal")
        patched_content = apply_unified_diff(current_content, proposal.unified_diff)
        _ensure_safe_text_content(patched_content, "patched content")
        return target, patched_content

    def _record_apply_failure(
        self,
        approval_service: ApprovalService,
        approval_id: str,
        attempt: PatchApplyAttempt | None,
        *,
        proposal_id: str,
        proposal_reserved: bool,
        file_replaced: bool,
        reason: str,
    ) -> None:
        if attempt is not None:
            try:
                self.store.set_apply_attempt_status(
                    attempt.attempt_id,
                    "recovery_required" if file_replaced else "failed",
                    failure_reason=reason,
                )
            except (PatchProposalError, OSError, sqlite3.Error):
                pass
        if file_replaced:
            raise PatchProposalError("patch apply recovery diagnostics required")
        if proposal_reserved:
            try:
                self.store.compare_and_set_status(
                    proposal_id,
                    expected_status="applying",
                    next_status="proposed",
                )
            except (PatchProposalError, OSError, sqlite3.Error):
                pass
        try:
            approval_service.complete_execution(approval_id, success=False)
        except ApprovalError:
            pass

    def _attempt_diagnostics(self, attempt: PatchApplyAttempt) -> JsonObject:
        current_target_hash: str | None = None
        current_matches_expected = False
        current_matches_base = False
        diagnostic_status = "ambiguous"
        reason: str | None = None
        try:
            filesystem = self._filesystem(attempt.workspace_id)
            target = filesystem.resolve_existing_path(attempt.path)
            current_content = filesystem.read_text_file(target)
            current_target_hash = sha256_digest(current_content)
            current_matches_expected = (
                current_target_hash == attempt.expected_post_apply_hash
            )
            current_matches_base = current_target_hash == attempt.base_file_hash
        except (PatchProposalError, ReadToolError) as exc:
            reason = str(exc)

        if (
            attempt.status in {"prepared", "file_replaced", "recovery_required"}
            and current_matches_expected
        ):
            diagnostic_status = "recovery_required"
        elif attempt.status == "prepared" and current_matches_base:
            diagnostic_status = "ambiguous"
            reason = "apply was prepared but replacement completion is unknown"
        elif reason is None:
            reason = "target hash does not match expected apply or base state"

        result = attempt.summary()
        result.update(
            {
                "current_target_hash": current_target_hash,
                "current_matches_expected_post_apply_hash": current_matches_expected,
                "current_matches_base_file_hash": current_matches_base,
                "diagnostic_status": diagnostic_status,
                "diagnostic_reason": reason,
            }
        )
        return result

    def _filesystem(self, workspace_id: str | None) -> FilesystemReadTools:
        resolved_id = workspace_id or self.default_workspace_id
        try:
            return self.filesystems[resolved_id]
        except KeyError as exc:
            raise PatchProposalError(f"unknown workspace: {resolved_id}") from exc


def normalize_unified_diff(unified_diff: str) -> str:
    normalized = unified_diff.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.endswith("\n"):
        normalized += "\n"
    return normalized


def validate_unified_diff(
    *,
    target_path: str,
    current_content: str,
    unified_diff: str,
) -> None:
    lines = unified_diff.splitlines()
    _reject_unsupported_diff_features(lines)
    old_path, new_path, hunk_start = _single_file_headers(lines)
    if old_path == "/dev/null" or new_path == "/dev/null":
        raise PatchProposalError("patch must modify an existing file")
    if _clean_diff_path(old_path) != target_path or _clean_diff_path(new_path) != target_path:
        raise PatchProposalError("patch target does not match requested path")
    if hunk_start >= len(lines):
        raise PatchProposalError("patch must contain at least one hunk")
    _ensure_safe_text_content(apply_unified_diff(current_content, unified_diff), "patched content")


def apply_unified_diff(current_content: str, unified_diff: str) -> str:
    original_lines = current_content.splitlines()
    diff_lines = unified_diff.splitlines()
    _, _, index = _single_file_headers(diff_lines)
    output_lines: list[str] = []
    original_index = 0

    while index < len(diff_lines):
        hunk_match = _HUNK_RE.match(diff_lines[index])
        if hunk_match is None:
            raise PatchProposalError("patch contains malformed hunk")
        old_start = int(hunk_match.group("old_start")) - 1
        expected_old_count = _hunk_count(hunk_match.group("old_count"))
        expected_new_count = _hunk_count(hunk_match.group("new_count"))
        actual_old_count = 0
        actual_new_count = 0
        if old_start < original_index:
            raise PatchProposalError("patch hunks overlap or move backwards")
        output_lines.extend(original_lines[original_index:old_start])
        original_index = old_start
        index += 1

        while index < len(diff_lines) and not diff_lines[index].startswith("@@"):
            line = diff_lines[index]
            if line == r"\ No newline at end of file":
                index += 1
                continue
            if not line:
                raise PatchProposalError("patch contains malformed hunk line")
            prefix = line[0]
            value = line[1:]
            if prefix == " ":
                _require_original_line(original_lines, original_index, value)
                output_lines.append(value)
                original_index += 1
                actual_old_count += 1
                actual_new_count += 1
            elif prefix == "-":
                _require_original_line(original_lines, original_index, value)
                original_index += 1
                actual_old_count += 1
            elif prefix == "+":
                output_lines.append(value)
                actual_new_count += 1
            else:
                raise PatchProposalError("patch contains malformed hunk line")
            index += 1
        if actual_old_count != expected_old_count or actual_new_count != expected_new_count:
            raise PatchProposalError("patch hunk line count does not match header")

    output_lines.extend(original_lines[original_index:])
    trailing_newline = "\n" if current_content.endswith("\n") else ""
    return "\n".join(output_lines) + trailing_newline


def _proposal_from_row(row: tuple[object, ...]) -> PatchProposal:
    return PatchProposal(
        proposal_id=str(row[0]),
        request_id=str(row[1]),
        principal=json.loads(str(row[2])),
        workspace_id=str(row[3]),
        path=str(row[4]),
        unified_diff=str(row[5]),
        base_file_hash=str(row[6]),
        proposal_hash=str(row[7]),
        status=str(row[8]),
        created_at=datetime.fromisoformat(str(row[9])),
        updated_at=datetime.fromisoformat(str(row[10])),
        metadata=json.loads(str(row[11])),
    )


def _apply_attempt_from_row(row: tuple[object, ...]) -> PatchApplyAttempt:
    return PatchApplyAttempt(
        attempt_id=str(row[0]),
        approval_id=str(row[1]),
        proposal_id=str(row[2]),
        request_id=str(row[3]),
        workspace_id=str(row[4]),
        path=str(row[5]),
        proposal_hash=str(row[6]),
        base_file_hash=str(row[7]),
        expected_post_apply_hash=str(row[8]),
        status=str(row[9]),
        failure_reason=str(row[10]) if row[10] is not None else None,
        created_at=datetime.fromisoformat(str(row[11])),
        updated_at=datetime.fromisoformat(str(row[12])),
        metadata=json.loads(str(row[13])),
    )


def _apply_attempt_transition_allowed(current: str, target: str) -> bool:
    if current == target:
        return True
    allowed = {
        "prepared": {"file_replaced", "failed", "recovery_required"},
        "file_replaced": {"completed", "recovery_required"},
        "recovery_required": set(),
        "completed": set(),
        "failed": set(),
    }
    return target in allowed.get(current, set())


def _reject_unsupported_diff_features(lines: list[str]) -> None:
    unsupported_prefixes = (
        "Binary files ",
        "rename from ",
        "rename to ",
        "deleted file mode ",
        "new file mode ",
        "similarity index ",
    )
    for line in lines:
        if line.startswith(unsupported_prefixes):
            raise PatchProposalError("patch feature is not supported")


def _single_file_headers(lines: list[str]) -> tuple[str, str, int]:
    old_headers = [index for index, line in enumerate(lines) if line.startswith("--- ")]
    new_headers = [index for index, line in enumerate(lines) if line.startswith("+++ ")]
    if len(old_headers) != 1 or len(new_headers) != 1:
        raise PatchProposalError("patch must target exactly one file")
    old_index = old_headers[0]
    new_index = new_headers[0]
    if new_index != old_index + 1:
        raise PatchProposalError("patch has malformed file headers")
    return _header_path(lines[old_index]), _header_path(lines[new_index]), new_index + 1


def _header_path(line: str) -> str:
    return line[4:].split("\t", maxsplit=1)[0].split(" ", maxsplit=1)[0]


def _clean_diff_path(path: str) -> str:
    if path.startswith("a/") or path.startswith("b/"):
        return path[2:]
    return path


def _require_original_line(lines: list[str], index: int, expected: str) -> None:
    if index >= len(lines) or lines[index] != expected:
        raise PatchProposalError("patch hunk context does not match target file")


def _hunk_count(raw_count: str | None) -> int:
    return int(raw_count) if raw_count is not None else 1


def _scope_string(scope: JsonObject, key: str) -> str:
    value = scope.get(key)
    if not isinstance(value, str):
        raise PatchProposalError(f"approval scope missing {key}")
    return value


def _optional_scope_string(scope: JsonObject, key: str) -> str | None:
    value = scope.get(key)
    return value if isinstance(value, str) else None


def _scope_string_list(scope: JsonObject, key: str) -> list[str]:
    value = scope.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise PatchProposalError(f"approval scope missing {key}")
    return cast(list[str], value)


def _scope_object(scope: JsonObject, key: str) -> JsonObject:
    value = scope.get(key)
    if not isinstance(value, dict) or not all(isinstance(item, str) for item in value):
        raise PatchProposalError(f"approval scope missing {key}")
    return value


def _scope_object_or_none(scope: JsonObject, key: str) -> JsonObject | None:
    value = scope.get(key)
    if not isinstance(value, dict) or not all(isinstance(item, str) for item in value):
        return None
    return value


def _atomic_write_text(
    workspace_root: Path,
    relative_path: str,
    content: str,
    *,
    expected_base_file_hash: str | None = None,
    max_verify_bytes: int | None = None,
) -> None:
    _ensure_safe_text_content(content, "patched content")
    requested = _patch_relative_path(relative_path)
    parts = requested.parts
    if not parts:
        raise OSError("patch target path is invalid")

    root_fd = _open_verified_directory(workspace_root)
    parent_fd = os.dup(root_fd)
    temp_name: str | None = None
    try:
        for part in parts[:-1]:
            next_fd = _open_verified_directory_component(parent_fd, part)
            os.close(parent_fd)
            parent_fd = next_fd

        filename = parts[-1]
        target_fd = _open_verified_target(parent_fd, filename)
        try:
            target_stat = os.fstat(target_fd)
            if not stat.S_ISREG(target_stat.st_mode):
                raise OSError("patch target is not a safe regular file")
            if target_stat.st_nlink > 1:
                raise OSError("patch target is hardlinked")
            if expected_base_file_hash is not None:
                _verify_target_base_hash(
                    target_fd,
                    expected_base_file_hash=expected_base_file_hash,
                    max_verify_bytes=max_verify_bytes,
                )
            mode = stat.S_IMODE(target_stat.st_mode)
        finally:
            os.close(target_fd)

        temp_name = f".{filename}.ithildin-{uuid4().hex}.tmp"
        temp_fd = os.open(temp_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode, dir_fd=parent_fd)
        try:
            data = _safe_utf8_bytes(content, "patched content")
            view = memoryview(data)
            while view:
                written = os.write(temp_fd, view)
                if written <= 0:
                    raise OSError("patch temp write failed")
                view = view[written:]
            os.fsync(temp_fd)
        finally:
            os.close(temp_fd)
        os.replace(temp_name, filename, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        temp_name = None
        os.fsync(parent_fd)
    finally:
        if temp_name is not None:
            try:
                os.unlink(temp_name, dir_fd=parent_fd)
            except OSError:
                pass
        os.close(parent_fd)
        os.close(root_fd)


def _patch_relative_path(relative_path: str) -> Path:
    requested = Path(relative_path)
    if not relative_path or requested.is_absolute() or ".." in requested.parts:
        raise OSError("patch target path is outside the workspace")
    if len(requested.parts) == 0 or requested.parts[-1] in {"", "."}:
        raise OSError("patch target path is invalid")
    return requested


def _verify_target_base_hash(
    fd: int,
    *,
    expected_base_file_hash: str,
    max_verify_bytes: int | None,
) -> None:
    stat_result = os.fstat(fd)
    if max_verify_bytes is not None and stat_result.st_size > max_verify_bytes:
        raise OSError("patch target has changed since proposal")
    os.lseek(fd, 0, os.SEEK_SET)
    data = os.read(fd, (max_verify_bytes or stat_result.st_size) + 1)
    if max_verify_bytes is not None and len(data) > max_verify_bytes:
        raise OSError("patch target has changed since proposal")
    if b"\x00" in data:
        raise OSError("patch target has changed since proposal")
    try:
        current_content = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise OSError("patch target has changed since proposal") from exc
    if sha256_digest(current_content) != expected_base_file_hash:
        raise OSError("patch target has changed since proposal")
    os.lseek(fd, 0, os.SEEK_SET)


def _ensure_safe_text_content(content: str, label: str) -> None:
    _safe_utf8_bytes(content, label)
    if "\x00" in content:
        raise PatchProposalError(f"{label} appears to be binary")


def _utf8_size(content: str, label: str) -> int:
    return len(_safe_utf8_bytes(content, label))


def _safe_utf8_bytes(content: str, label: str) -> bytes:
    try:
        return content.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise PatchProposalError(f"{label} is not valid UTF-8 text") from exc


def _open_verified_directory(path: Path) -> int:
    flags = os.O_RDONLY | _o_directory()
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    try:
        stat_result = os.fstat(fd)
        if not stat.S_ISDIR(stat_result.st_mode):
            raise OSError("patch target parent is not a safe directory")
        return fd
    except Exception:
        os.close(fd)
        raise


def _open_verified_directory_component(parent_fd: int, name: str) -> int:
    flags = os.O_RDONLY | _o_directory()
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(name, flags, dir_fd=parent_fd)
    try:
        stat_result = os.fstat(fd)
        if not stat.S_ISDIR(stat_result.st_mode):
            raise OSError("patch target parent is not a safe directory")
        return fd
    except Exception:
        os.close(fd)
        raise


def _open_verified_target(parent_fd: int, name: str) -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return os.open(name, flags, dir_fd=parent_fd)


def _o_directory() -> int:
    return getattr(os, "O_DIRECTORY", 0)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


_HUNK_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@"
)

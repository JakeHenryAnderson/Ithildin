"""Stored unified-diff patch proposals."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import uuid4

from ithildin_schemas import ApprovalRequest, JsonObject, canonical_json, sha256_digest

from ithildin_api.approvals import ApprovalService
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


class PatchProposalService:
    def __init__(
        self,
        store: PatchProposalStore,
        filesystem: FilesystemReadTools,
        max_patch_bytes: int,
        filesystems: dict[str, FilesystemReadTools] | None = None,
        default_workspace_id: str | None = None,
    ) -> None:
        self.store = store
        self.filesystem = filesystem
        self.filesystems = filesystems or {filesystem.workspace_id: filesystem}
        self.default_workspace_id = default_workspace_id or filesystem.workspace_id
        self.max_patch_bytes = max_patch_bytes

    def create_proposal(
        self,
        *,
        request_id: str,
        principal: JsonObject,
        path: str,
        unified_diff: str,
        workspace_id: str | None = None,
    ) -> PatchProposal:
        if len(unified_diff.encode("utf-8")) > self.max_patch_bytes:
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
        expected_policy_document_version: str,
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
            "policy_document_version",
            _optional_scope_string(scope, "policy_document_version")
            == expected_policy_document_version,
            "policy document version mismatch",
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
        approval_service.begin_execution(approval_id, approval.request_hash)
        try:
            self._apply_proposal(proposal)
            applied = self.store.set_status(proposal.proposal_id, "applied")
        except PatchProposalError:
            approval_service.complete_execution(approval_id, success=False)
            raise
        except OSError as exc:
            approval_service.complete_execution(approval_id, success=False)
            raise PatchProposalError("failed to apply patch safely") from exc

        approval_service.complete_execution(approval_id, success=True)
        return applied

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

    def _apply_proposal(self, proposal: PatchProposal) -> None:
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
        _atomic_write_text(target, patched_content)

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
    apply_unified_diff(current_content, unified_diff)


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
            elif prefix == "-":
                _require_original_line(original_lines, original_index, value)
                original_index += 1
            elif prefix == "+":
                output_lines.append(value)
            else:
                raise PatchProposalError("patch contains malformed hunk line")
            index += 1

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


def _atomic_write_text(target: Path, content: str) -> None:
    mode = target.stat().st_mode
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=target.parent,
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.chmod(temp_path, mode)
        temp_path.replace(target)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


_HUNK_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@"
)

"""Stored unified-diff patch proposals."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from ithildin_schemas import JsonObject, canonical_json, sha256_digest

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
            "path": self.path,
            "base_file_hash": self.base_file_hash,
            "proposal_hash": self.proposal_hash,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }

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
            connection.commit()

    def create(self, proposal: PatchProposal) -> PatchProposal:
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO patch_proposals (
                    proposal_id,
                    request_id,
                    principal_json,
                    path,
                    unified_diff,
                    base_file_hash,
                    proposal_hash,
                    status,
                    created_at,
                    updated_at,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal.proposal_id,
                    proposal.request_id,
                    canonical_json(proposal.principal),
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


class PatchProposalService:
    def __init__(
        self,
        store: PatchProposalStore,
        filesystem: FilesystemReadTools,
        max_patch_bytes: int,
    ) -> None:
        self.store = store
        self.filesystem = filesystem
        self.max_patch_bytes = max_patch_bytes

    def create_proposal(
        self,
        *,
        request_id: str,
        principal: JsonObject,
        path: str,
        unified_diff: str,
    ) -> PatchProposal:
        if len(unified_diff.encode("utf-8")) > self.max_patch_bytes:
            raise PatchProposalError("patch exceeds configured size limit")

        try:
            target = self.filesystem.resolve_existing_path(path)
        except ReadToolError as exc:
            raise PatchProposalError(exc.reason) from exc
        if not target.is_file():
            raise PatchProposalError("patch target is not a file")

        try:
            current_content = target.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise PatchProposalError("patch target is not a UTF-8 text file") from exc

        normalized_path = self.filesystem.relative_path(target)
        normalized_diff = normalize_unified_diff(unified_diff)
        validate_unified_diff(
            target_path=normalized_path,
            current_content=current_content,
            unified_diff=normalized_diff,
        )
        base_file_hash = sha256_digest(current_content)
        proposal_hash = sha256_digest(
            {
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
        path=str(row[3]),
        unified_diff=str(row[4]),
        base_file_hash=str(row[5]),
        proposal_hash=str(row[6]),
        status=str(row[7]),
        created_at=datetime.fromisoformat(str(row[8])),
        updated_at=datetime.fromisoformat(str(row[9])),
        metadata=json.loads(str(row[10])),
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


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


_HUNK_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@"
)

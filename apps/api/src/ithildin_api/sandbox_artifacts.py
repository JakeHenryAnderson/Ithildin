"""Bounded sandbox artifact write executor."""

from __future__ import annotations

import os
import stat
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import cast
from uuid import uuid4

from ithildin_schemas import ApprovalRequest, JsonObject, canonical_json, sha256_digest

from ithildin_api.approvals import ApprovalError, ApprovalService
from ithildin_api.read_tools import FilesystemReadTools, ReadToolExecutor

SANDBOX_ARTIFACT_WRITE_TEXT_TOOL = "sandbox.artifact.write_text"
SANDBOX_ARTIFACT_CONTENT_MAX_BYTES = 4096
SANDBOX_ARTIFACT_CONTENT_MAX_LINES = 100
SANDBOX_ARTIFACT_PATH_MAX_BYTES = 240
SANDBOX_ARTIFACT_IDEMPOTENCY_KEY_MAX_BYTES = 120


class SandboxArtifactError(RuntimeError):
    """Raised when a sandbox artifact operation is unsafe or invalid."""


@dataclass(frozen=True)
class SandboxArtifactAction:
    workspace_id: str
    sandbox_id: str
    root: str
    relative_path: str
    artifact_path: str
    artifact_label: str
    content: str
    content_sha256: str
    content_bytes: int
    create_parent_directories: bool
    overwrite: bool
    idempotency_key: str

    def scope_metadata(self) -> JsonObject:
        return {
            "workspace_id": self.workspace_id,
            "sandbox_id": self.sandbox_id,
            "root": self.root,
            "relative_path": self.relative_path,
            "artifact_path": self.artifact_path,
            "artifact_label": self.artifact_label,
            "content_sha256": self.content_sha256,
            "content_bytes": self.content_bytes,
            "create_parent_directories": self.create_parent_directories,
            "overwrite": self.overwrite,
            "idempotency_key_hash": sha256_digest(self.idempotency_key),
        }


class SandboxArtifactWriteService:
    def __init__(
        self,
        *,
        filesystems: dict[str, FilesystemReadTools],
        default_workspace_id: str,
    ) -> None:
        self.filesystems = filesystems
        self.default_workspace_id = default_workspace_id

    @classmethod
    def from_read_executor(cls, read_executor: ReadToolExecutor) -> SandboxArtifactWriteService:
        return cls(
            filesystems=read_executor.filesystems,
            default_workspace_id=read_executor.default_workspace_id,
        )

    def resource_from_arguments(self, arguments: JsonObject) -> JsonObject:
        workspace_id = _workspace_id(arguments, self.default_workspace_id)
        resource: JsonObject = {
            "type": "sandbox_artifact",
            "workspace_id": workspace_id,
            "sandbox_id": _optional_string(arguments, "sandbox_id", default="unresolved"),
            "artifact_label": "unresolved",
            "in_scope": False,
        }
        try:
            action = self._action_from_arguments(arguments, require_content="content" in arguments)
        except SandboxArtifactError as exc:
            resource["scope_error"] = str(exc)
            return resource
        resource.update(
            {
                "sandbox_id": action.sandbox_id,
                "artifact_label": action.artifact_label,
                "content_sha256": action.content_sha256,
                "content_bytes": action.content_bytes,
                "create_parent_directories": action.create_parent_directories,
                "overwrite": action.overwrite,
                "in_scope": True,
            }
        )
        return resource

    def approval_scope(
        self,
        arguments: JsonObject,
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
        action = self._action_from_arguments(arguments, require_content=True)
        return cast(
            JsonObject,
            {
                "tool_name": SANDBOX_ARTIFACT_WRITE_TEXT_TOOL,
                **action.scope_metadata(),
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
        arguments: JsonObject,
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
        approval = approval_service.get(approval_id)
        action = self._action_from_arguments(arguments, require_content=True)
        _validate_approval_scope(
            approval=approval,
            action=action,
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
        file_written = False
        try:
            approval_service.begin_execution(approval_id, approval.request_hash)
            write_result = self._write_action(action)
            file_written = write_result["status"] in {"created", "overwritten"}
            approval_service.complete_execution(approval_id, success=True)
        except (ApprovalError, SandboxArtifactError):
            if not file_written:
                try:
                    approval_service.complete_execution(approval_id, success=False)
                except ApprovalError:
                    pass
            raise

        return {
            **write_result,
            "approval_id": approval_id,
            "workspace_id": action.workspace_id,
            "sandbox_id": action.sandbox_id,
            "artifact_label": action.artifact_label,
            "content_sha256": action.content_sha256,
            "content_bytes": action.content_bytes,
            "output_policy": _output_policy(),
        }

    def _action_from_arguments(
        self,
        arguments: JsonObject,
        *,
        require_content: bool,
    ) -> SandboxArtifactAction:
        workspace_id = _workspace_id(arguments, self.default_workspace_id)
        filesystem = self._filesystem(workspace_id)
        sandbox_id = _sandbox_id(arguments)
        root = _relative_path_arg(arguments, "root", default=".")
        relative_path = _relative_path_arg(arguments, "relative_path")
        content = _content(arguments, require=require_content)
        create_parent_directories = _bool_arg(arguments, "create_parent_directories", default=False)
        overwrite = _bool_arg(arguments, "overwrite", default=False)
        idempotency_key = _idempotency_key(arguments)
        content_bytes = len(content.encode("utf-8"))
        content_sha256 = sha256_digest(content)
        artifact_path = _joined_relative_artifact_path(root, relative_path)
        _validate_artifact_target(filesystem, artifact_path, create_parent_directories)
        artifact_label = f"sandbox://{sandbox_id}/{artifact_path}"
        return SandboxArtifactAction(
            workspace_id=workspace_id,
            sandbox_id=sandbox_id,
            root=root,
            relative_path=relative_path,
            artifact_path=artifact_path,
            artifact_label=artifact_label,
            content=content,
            content_sha256=content_sha256,
            content_bytes=content_bytes,
            create_parent_directories=create_parent_directories,
            overwrite=overwrite,
            idempotency_key=idempotency_key,
        )

    def _write_action(self, action: SandboxArtifactAction) -> JsonObject:
        filesystem = self._filesystem(action.workspace_id)
        target = filesystem.workspace_root / Path(action.artifact_path)
        parent = target.parent
        if not parent.exists():
            if not action.create_parent_directories:
                raise SandboxArtifactError("artifact parent directory does not exist")
            _mkdirs_under_workspace(filesystem, parent)
            parent_created = True
        else:
            parent_created = False
        _validate_artifact_target(
            filesystem,
            action.artifact_path,
            action.create_parent_directories,
        )
        if target.exists():
            _ensure_regular_single_link_file(target)
            existing = target.read_bytes()
            try:
                existing_text = existing.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise SandboxArtifactError("artifact path is not UTF-8 text") from exc
            if sha256_digest(existing_text) == action.content_sha256:
                return {"status": "already_exists", "parent_created": parent_created}
            if not action.overwrite:
                raise SandboxArtifactError("artifact already exists")
            status = "overwritten"
        else:
            status = "created"
        _atomic_write_text(target, action.content, overwrite=action.overwrite)
        return {"status": status, "parent_created": parent_created}

    def _filesystem(self, workspace_id: str) -> FilesystemReadTools:
        try:
            return self.filesystems[workspace_id]
        except KeyError as exc:
            raise SandboxArtifactError("unknown workspace") from exc


def sandbox_artifact_resource_from_arguments(
    arguments: JsonObject,
    read_tool_executor: ReadToolExecutor | None,
) -> JsonObject:
    if read_tool_executor is None:
        return {"type": "sandbox_artifact", "in_scope": False, "scope_error": "no workspace"}
    service = SandboxArtifactWriteService.from_read_executor(read_tool_executor)
    return service.resource_from_arguments(arguments)


def _validate_approval_scope(
    *,
    approval: ApprovalRequest,
    action: SandboxArtifactAction,
    expected_manifest_hash: str,
    expected_manifest_version: str,
    expected_tool_input_schema_hash: str,
    expected_policy_engine: str,
    expected_policy_hash: str,
    expected_policy_version: str,
    expected_policy_document_version: str,
    expected_matched_rules: list[str],
    expected_principal: JsonObject,
) -> None:
    scope = approval.one_time_scope
    checks = {
        "tool_name": approval.tool_name == SANDBOX_ARTIFACT_WRITE_TEXT_TOOL
        and _scope_string(scope, "tool_name") == SANDBOX_ARTIFACT_WRITE_TEXT_TOOL,
        "request_hash": _scope_string(scope, "request_hash") == approval.request_hash,
        "expiry": _scope_string(scope, "expires_at") == approval.expires_at.isoformat(),
        "manifest_hash": _scope_string(scope, "manifest_hash") == expected_manifest_hash,
        "manifest_version": _scope_string(scope, "manifest_version") == expected_manifest_version,
        "tool_input_schema_hash": _scope_string(scope, "tool_input_schema_hash")
        == expected_tool_input_schema_hash,
        "policy_engine": _scope_string(scope, "policy_engine") == expected_policy_engine,
        "policy_hash": _scope_string(scope, "policy_hash") == expected_policy_hash,
        "policy_version": _scope_string(scope, "policy_version") == expected_policy_version,
        "policy_document_version": _scope_string(scope, "policy_document_version")
        == expected_policy_document_version,
        "matched_rules": _scope_string_list(scope, "matched_rules") == expected_matched_rules,
        "requesting_principal": canonical_json(scope.get("requesting_principal"))
        == canonical_json(expected_principal),
    }
    for key, value in action.scope_metadata().items():
        checks[key] = scope.get(key) == value
    failed = sorted(key for key, passed in checks.items() if not passed)
    if failed:
        raise SandboxArtifactError("approval scope mismatch")


def _workspace_id(arguments: JsonObject, default: str) -> str:
    value = arguments.get("workspace_id", default)
    if not isinstance(value, str) or not value:
        raise SandboxArtifactError("workspace_id must be a non-empty string")
    if len(value.encode("utf-8")) > 120:
        raise SandboxArtifactError("workspace_id is too long")
    _reject_control_or_unnormalized(value, label="workspace_id")
    return value


def _sandbox_id(arguments: JsonObject) -> str:
    value = _optional_string(arguments, "sandbox_id", default="local-demo-sandbox")
    if not value or len(value.encode("utf-8")) > 120:
        raise SandboxArtifactError("sandbox_id is invalid")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.:-")
    if any(character not in allowed for character in value):
        raise SandboxArtifactError("sandbox_id is invalid")
    return value


def _relative_path_arg(arguments: JsonObject, key: str, *, default: str | None = None) -> str:
    raw = arguments.get(key, default)
    if not isinstance(raw, str) or not raw:
        raise SandboxArtifactError(f"{key} must be a non-empty relative path")
    if len(raw.encode("utf-8")) > SANDBOX_ARTIFACT_PATH_MAX_BYTES:
        raise SandboxArtifactError(f"{key} is too long")
    _reject_ambiguous_path_input(raw, label=key)
    path = Path(raw)
    if path.is_absolute() or ".." in path.parts:
        raise SandboxArtifactError("artifact path escapes the sandbox scope")
    _ensure_relative_parts_not_sensitive(path)
    return path.as_posix()


def _content(arguments: JsonObject, *, require: bool) -> str:
    raw = arguments.get("content")
    if raw is None and not require:
        return ""
    if not isinstance(raw, str):
        raise SandboxArtifactError("content must be UTF-8 text")
    encoded = raw.encode("utf-8")
    if len(encoded) > SANDBOX_ARTIFACT_CONTENT_MAX_BYTES:
        raise SandboxArtifactError("content exceeds sandbox artifact limit")
    if raw.count("\n") + 1 > SANDBOX_ARTIFACT_CONTENT_MAX_LINES:
        raise SandboxArtifactError("content exceeds sandbox artifact line limit")
    if "\x00" in raw:
        raise SandboxArtifactError("content must be text")
    if not unicodedata.is_normalized("NFC", raw):
        raise SandboxArtifactError("content is not Unicode-normalized")
    return raw


def _bool_arg(arguments: JsonObject, key: str, *, default: bool) -> bool:
    value = arguments.get(key, default)
    if not isinstance(value, bool):
        raise SandboxArtifactError(f"{key} must be boolean")
    return value


def _idempotency_key(arguments: JsonObject) -> str:
    value = _optional_string(arguments, "idempotency_key", default="")
    if len(value.encode("utf-8")) > SANDBOX_ARTIFACT_IDEMPOTENCY_KEY_MAX_BYTES:
        raise SandboxArtifactError("idempotency_key is too long")
    _reject_control_or_unnormalized(value, label="idempotency_key")
    return value


def _optional_string(arguments: JsonObject, key: str, *, default: str) -> str:
    value = arguments.get(key, default)
    if not isinstance(value, str):
        raise SandboxArtifactError(f"{key} must be a string")
    return value


def _joined_relative_artifact_path(root: str, relative_path: str) -> str:
    path = Path(root) / Path(relative_path)
    if path.is_absolute() or ".." in path.parts:
        raise SandboxArtifactError("artifact path escapes the sandbox scope")
    _ensure_relative_parts_not_sensitive(path)
    return path.as_posix()


def _validate_artifact_target(
    filesystem: FilesystemReadTools,
    artifact_path: str,
    create_parent_directories: bool,
) -> None:
    requested = Path(artifact_path)
    target = filesystem.workspace_root / requested
    _ensure_under_workspace(filesystem, target)
    _ensure_no_symlink_components(filesystem.workspace_root, requested, allow_missing=True)
    existing_parent = _nearest_existing_parent(filesystem.workspace_root, requested)
    if not existing_parent.is_dir():
        raise SandboxArtifactError("artifact parent is not a directory")
    _ensure_under_workspace(filesystem, existing_parent)
    if not target.parent.exists() and not create_parent_directories:
        raise SandboxArtifactError("artifact parent directory does not exist")
    if target.exists():
        _ensure_regular_single_link_file(target)


def _mkdirs_under_workspace(filesystem: FilesystemReadTools, parent: Path) -> None:
    _ensure_under_workspace(filesystem, parent)
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise SandboxArtifactError("artifact parent directory could not be created") from exc


def _atomic_write_text(target: Path, content: str, *, overwrite: bool) -> None:
    parent = target.parent
    temporary = parent / f".ithildin-{uuid4().hex}.tmp"
    data = content.encode("utf-8")
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
        if overwrite:
            if target.exists():
                _ensure_regular_single_link_file(target)
            os.replace(temporary, target)
        else:
            os.link(temporary, target)
            os.unlink(temporary)
    except FileExistsError as exc:
        raise SandboxArtifactError("artifact already exists") from exc
    except OSError as exc:
        raise SandboxArtifactError("artifact write failed") from exc
    finally:
        try:
            if temporary.exists():
                temporary.unlink()
        except OSError:
            pass


def _ensure_regular_single_link_file(path: Path) -> None:
    if path.is_symlink():
        raise SandboxArtifactError("artifact path is a symlink")
    try:
        stat_result = path.stat()
    except OSError as exc:
        raise SandboxArtifactError("artifact path cannot be inspected") from exc
    if not stat.S_ISREG(stat_result.st_mode):
        raise SandboxArtifactError("artifact path is not a file")
    if stat_result.st_nlink > 1:
        raise SandboxArtifactError("hardlinked files are not allowed")


def _ensure_under_workspace(filesystem: FilesystemReadTools, path: Path) -> None:
    try:
        path.resolve(strict=False).relative_to(filesystem.workspace_root)
    except ValueError as exc:
        raise SandboxArtifactError("artifact path escapes the workspace scope") from exc


def _nearest_existing_parent(root: Path, relative: Path) -> Path:
    current = root
    for part in relative.parts[:-1]:
        candidate = current / part
        if not candidate.exists():
            return current
        current = candidate
    return current


def _ensure_no_symlink_components(root: Path, relative: Path, *, allow_missing: bool) -> None:
    current = root
    for part in relative.parts:
        current = current / part
        if not current.exists():
            if allow_missing:
                continue
            raise SandboxArtifactError("artifact path does not exist")
        if current.is_symlink():
            raise SandboxArtifactError("artifact path is a symlink")


def _reject_ambiguous_path_input(value: str, *, label: str) -> None:
    _reject_control_or_unnormalized(value, label=label)
    lowered = value.lower()
    if any(token in lowered for token in ("%2e", "%2f", "%5c")):
        raise SandboxArtifactError("encoded path tokens are not allowed")


def _reject_control_or_unnormalized(value: str, *, label: str) -> None:
    if any(
        ord(character) < 32
        or ord(character) == 127
        or unicodedata.category(character) in {"Cc", "Cf", "Cs"}
        for character in value
    ):
        raise SandboxArtifactError(f"{label} contains control characters")
    if not unicodedata.is_normalized("NFC", value):
        raise SandboxArtifactError(f"{label} is not Unicode-normalized")


def _ensure_relative_parts_not_sensitive(relative: Path) -> None:
    sensitive_exact = {
        ".git",
        ".ssh",
        ".aws",
        ".env",
        "id_rsa",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
    }
    sensitive_markers = ("secret", "token", "password", "credential", "private")
    for part in relative.parts:
        lowered = part.lower()
        if (
            part.startswith(".")
            or lowered in sensitive_exact
            or any(marker in lowered for marker in sensitive_markers)
        ):
            raise SandboxArtifactError("artifact path is hidden or sensitive")


def _scope_string(scope: JsonObject, key: str) -> str | None:
    value = scope.get(key)
    return value if isinstance(value, str) else None


def _scope_string_list(scope: JsonObject, key: str) -> list[str]:
    value = scope.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _output_policy() -> JsonObject:
    return {
        "file_contents_included": False,
        "raw_host_paths_included": False,
        "shell_output_included": False,
        "sandbox_orchestration_performed": False,
        "host_promotion_performed": False,
    }

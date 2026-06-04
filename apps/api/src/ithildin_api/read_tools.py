"""Safe in-process read-only tool adapters."""

from __future__ import annotations

import os
import re
import shlex
import stat
import subprocess
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional, cast

from ithildin_schemas import JsonObject, JsonValue, sha256_digest

from ithildin_api.workspaces import WorkspaceRegistry

READ_TOOL_NAMES = frozenset(
    {
        "fs.list",
        "fs.stat",
        "fs.read",
        "fs.search",
        "git.status",
        "git.diff",
        "git.log",
        "git.show.commit_metadata",
    }
)

_GIT_COMMIT_METADATA_TOOL = "git.show.commit_metadata"
_HEX_OBJECT_RE = re.compile(r"^[0-9a-fA-F]{40}$|^[0-9a-fA-F]{64}$")
_SAFE_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
_EMAIL_LIKE_RE = re.compile(r"[\w.!#$%&'*+/=?^`{|}~-]+@[\w.-]+")
_COMMIT_METADATA_SUBJECT_LIMIT = 240
_COMMIT_METADATA_BODY_LIMIT = 2000
_COMMIT_METADATA_CHANGED_FILE_LIMIT = 100
_SENSITIVE_EXACT_PATH_PARTS = {
    ".env",
    "credentials.json",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
    "private-key.pem",
    "private_key.pem",
    "secret",
    "secrets",
}
_SENSITIVE_PATH_MARKERS = (
    "credential",
    "private-key",
    "private_key",
)


class ReadToolError(RuntimeError):
    """Raised when a read tool must fail without leaking sensitive data."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class GitOutput:
    text: str
    truncated: bool


@dataclass(frozen=True)
class ReadToolExecutor:
    filesystem: FilesystemReadTools
    git: GitReadTools
    filesystems: dict[str, FilesystemReadTools]
    git_tools: dict[str, GitReadTools]
    default_workspace_id: str

    @classmethod
    def from_settings(
        cls,
        *,
        workspace_root: Path,
        max_read_bytes: int,
        search_result_limit: int,
        git_log_limit: int,
        workspace_registry: WorkspaceRegistry | None = None,
    ) -> ReadToolExecutor:
        if workspace_registry is None:
            default_workspace_id = "default"
            filesystem = FilesystemReadTools(
                workspace_root=workspace_root,
                max_read_bytes=max_read_bytes,
                search_result_limit=search_result_limit,
                workspace_id=default_workspace_id,
            )
            git = GitReadTools(
                filesystem=filesystem,
                max_output_bytes=max_read_bytes,
                git_log_limit=git_log_limit,
            )
            return cls(
                filesystem=filesystem,
                git=git,
                filesystems={default_workspace_id: filesystem},
                git_tools={default_workspace_id: git},
                default_workspace_id=default_workspace_id,
            )

        filesystems: dict[str, FilesystemReadTools] = {}
        git_tools: dict[str, GitReadTools] = {}
        for workspace in workspace_registry.list_workspaces():
            if not workspace.enabled:
                continue
            _, root = workspace_registry.resolve_active(workspace.id)
            workspace_filesystem = FilesystemReadTools(
                workspace_root=root,
                max_read_bytes=max_read_bytes,
                search_result_limit=search_result_limit,
                workspace_id=workspace.id,
            )
            filesystems[workspace.id] = workspace_filesystem
            git_tools[workspace.id] = GitReadTools(
                filesystem=workspace_filesystem,
                max_output_bytes=max_read_bytes,
                git_log_limit=git_log_limit,
            )

        default_workspace_id = workspace_registry.default_workspace_id
        filesystem = filesystems[default_workspace_id]
        return cls(
            filesystem=filesystem,
            git=git_tools[default_workspace_id],
            filesystems=filesystems,
            git_tools=git_tools,
            default_workspace_id=default_workspace_id,
        )

    def supports(self, tool_name: str) -> bool:
        return tool_name in READ_TOOL_NAMES

    def resource_from_arguments(
        self,
        arguments: JsonObject,
        *,
        tool_name: str | None = None,
    ) -> JsonObject:
        if tool_name == _GIT_COMMIT_METADATA_TOOL:
            return self._commit_metadata_resource_from_arguments(arguments)

        path = _string_arg(arguments, "path", default=".")
        workspace_id = _workspace_id_arg(arguments, self.default_workspace_id)
        resource: JsonObject = {
            "type": "file",
            "path": path,
            "workspace_id": workspace_id,
            "in_scope": False,
        }
        try:
            filesystem = self._filesystem(workspace_id)
            target = filesystem.resolve_existing_path(path)
        except ReadToolError as exc:
            resource["scope_error"] = exc.reason
            return resource
        resource["path"] = filesystem.relative_path(target)
        resource["in_scope"] = True
        return resource

    def _commit_metadata_resource_from_arguments(self, arguments: JsonObject) -> JsonObject:
        workspace_id = _workspace_id_arg(arguments, self.default_workspace_id)
        resource: JsonObject = {
            "type": "git_commit",
            "workspace_id": workspace_id,
            "in_scope": False,
        }
        try:
            self._filesystem(workspace_id)
            git = self._git(workspace_id)
            repo = git._repo_path(".")
            git._ensure_repo_toplevel_in_workspace(repo)
            selector = _commit_ref_selector(arguments)
            _validate_commit_ref_selector(selector)
        except ReadToolError as exc:
            resource["scope_error"] = exc.reason
            return resource
        resource.update(
            {
                "ref_kind": selector["kind"],
                "ref_value_hash": sha256_digest(selector["value"]),
                "in_scope": True,
            }
        )
        return resource

    def execute(self, tool_name: str, arguments: JsonObject) -> JsonObject:
        workspace_id = _workspace_id_arg(arguments, self.default_workspace_id)
        filesystem = self._filesystem(workspace_id)
        git = self._git(workspace_id)
        if tool_name == "fs.list":
            return filesystem.list_path(_string_arg(arguments, "path", default="."))
        if tool_name == "fs.stat":
            return filesystem.stat_path(_string_arg(arguments, "path"))
        if tool_name == "fs.read":
            return filesystem.read_file(_string_arg(arguments, "path"))
        if tool_name == "fs.search":
            return filesystem.search(
                path=_string_arg(arguments, "path", default="."),
                query=_string_arg(arguments, "query"),
            )
        if tool_name == "git.status":
            return git.status(_string_arg(arguments, "path", default="."))
        if tool_name == "git.diff":
            return git.diff(_string_arg(arguments, "path", default="."))
        if tool_name == "git.log":
            return git.log(
                path=_string_arg(arguments, "path", default="."),
                limit=_int_arg(arguments, "limit", default=git.git_log_limit),
            )
        if tool_name == _GIT_COMMIT_METADATA_TOOL:
            return git.commit_metadata(arguments)
        raise ReadToolError("unsupported read tool")

    def _filesystem(self, workspace_id: str) -> FilesystemReadTools:
        try:
            return self.filesystems[workspace_id]
        except KeyError as exc:
            raise ReadToolError(f"unknown workspace: {workspace_id}") from exc

    def _git(self, workspace_id: str) -> GitReadTools:
        try:
            return self.git_tools[workspace_id]
        except KeyError as exc:
            raise ReadToolError(f"unknown workspace: {workspace_id}") from exc


class FilesystemReadTools:
    def __init__(
        self,
        workspace_root: Path,
        max_read_bytes: int,
        search_result_limit: int,
        workspace_id: str = "default",
    ) -> None:
        self.workspace_id = workspace_id
        self.workspace_root = workspace_root.resolve(strict=False)
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.max_read_bytes = max_read_bytes
        self.search_result_limit = search_result_limit

    def list_path(self, path: str = ".") -> JsonObject:
        target = self.resolve_existing_path(path)
        if not target.is_dir():
            raise ReadToolError("path is not a directory")

        entries: list[JsonValue] = []
        for child in sorted(target.iterdir(), key=lambda item: item.name):
            if child.is_symlink():
                continue
            try:
                allowed_child = self.resolve_existing_path(self.relative_path(child))
            except ReadToolError:
                continue
            entries.append(self._metadata(allowed_child))
        return {
            "workspace_id": self.workspace_id,
            "path": self.relative_path(target),
            "entries": entries,
        }

    def stat_path(self, path: str) -> JsonObject:
        return self._metadata(self.resolve_existing_path(path))

    def read_file(self, path: str) -> JsonObject:
        target = self.resolve_existing_path(path)
        content = self.read_text_file(target)
        return {
            "workspace_id": self.workspace_id,
            "path": self.relative_path(target),
            "content": content,
            "byte_count": len(content.encode("utf-8")),
        }

    def search(self, *, path: str, query: str) -> JsonObject:
        if not query:
            raise ReadToolError("query must not be empty")

        target = self.resolve_existing_path(path)
        candidates = [target] if target.is_file() else sorted(target.rglob("*"))
        matches: list[JsonValue] = []

        for candidate in candidates:
            if len(matches) >= self.search_result_limit:
                break
            if candidate.is_symlink():
                continue
            if not candidate.is_file():
                continue
            try:
                allowed_candidate = self.resolve_existing_path(self.relative_path(candidate))
            except ReadToolError:
                continue
            if allowed_candidate.stat().st_size > self.max_read_bytes:
                continue
            try:
                self._append_file_matches(allowed_candidate, query, matches)
            except ReadToolError:
                continue

        return {
            "workspace_id": self.workspace_id,
            "path": self.relative_path(target),
            "query": query,
            "matches": matches[: self.search_result_limit],
            "truncated": len(matches) >= self.search_result_limit,
        }

    def resolve_existing_path(self, path: str) -> Path:
        if not path:
            path = "."
        _reject_ambiguous_path_input(path)
        requested = Path(path)
        if requested.is_absolute():
            raise ReadToolError("absolute paths are outside the workspace scope")
        if ".." in requested.parts:
            raise ReadToolError("path traversal is outside the workspace scope")

        target = self.workspace_root.joinpath(requested)
        self._ensure_no_symlink_components(requested)
        try:
            resolved = target.resolve(strict=True)
        except OSError as exc:
            raise ReadToolError("path does not exist in the workspace") from exc

        self._ensure_under_workspace(resolved)
        self._ensure_not_sensitive(resolved)
        self._ensure_not_hardlinked_file(resolved)
        return resolved

    def read_text_file(self, path: Path) -> str:
        data = self.read_file_bytes(path)
        if b"\x00" in data:
            raise ReadToolError("file appears to be binary")
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ReadToolError("file is not valid UTF-8 text") from exc

    def read_file_bytes(self, path: Path) -> bytes:
        fd = self._open_no_follow_file(path)
        try:
            stat_result = os.fstat(fd)
            if not stat.S_ISREG(stat_result.st_mode):
                raise ReadToolError("path is not a file")
            if stat_result.st_nlink > 1:
                raise ReadToolError("hardlinked files are not allowed")
            if stat_result.st_size > self.max_read_bytes:
                raise ReadToolError("file exceeds configured read limit")
            data = os.read(fd, self.max_read_bytes + 1)
        finally:
            os.close(fd)
        if len(data) > self.max_read_bytes:
            raise ReadToolError("file exceeds configured read limit")
        return data

    def _open_no_follow_file(self, path: Path) -> int:
        try:
            relative = path.relative_to(self.workspace_root)
        except ValueError as exc:
            raise ReadToolError("path escapes the workspace scope") from exc
        if not relative.parts:
            raise ReadToolError("path is not a file")

        root_fd = _open_no_follow_directory(self.workspace_root)
        parent_fd = os.dup(root_fd)
        try:
            for part in relative.parts[:-1]:
                next_fd = _open_no_follow_directory_component(parent_fd, part)
                os.close(parent_fd)
                parent_fd = next_fd
            fd = _open_no_follow_file_component(parent_fd, relative.parts[-1])
            os.close(parent_fd)
            return fd
        except Exception:
            os.close(parent_fd)
            raise
        finally:
            os.close(root_fd)

    def relative_path(self, path: Path) -> str:
        try:
            relative = path.resolve(strict=True).relative_to(self.workspace_root)
        except ValueError as exc:
            raise ReadToolError("path escapes the workspace scope") from exc
        if not relative.parts:
            return "."
        return relative.as_posix()

    def _metadata(self, path: Path) -> JsonObject:
        stat_result = path.stat()
        return {
            "name": path.name,
            "path": self.relative_path(path),
            "type": _path_type(path),
            "size": stat_result.st_size,
            "modified_at": datetime.fromtimestamp(stat_result.st_mtime, UTC).isoformat(),
        }

    def _append_file_matches(
        self,
        path: Path,
        query: str,
        matches: list[JsonValue],
    ) -> None:
        content = self.read_text_file(path)
        for line_number, line in enumerate(content.splitlines(), start=1):
            if len(matches) >= self.search_result_limit:
                return
            if query in line:
                matches.append(
                    {
                        "path": self.relative_path(path),
                        "line_number": line_number,
                        "preview": line[:240],
                    }
                )

    def _ensure_under_workspace(self, path: Path) -> None:
        try:
            path.relative_to(self.workspace_root)
        except ValueError as exc:
            raise ReadToolError("path escapes the workspace scope") from exc

    def _ensure_not_sensitive(self, path: Path) -> None:
        relative = path.relative_to(self.workspace_root)
        _ensure_relative_parts_not_sensitive(relative)

    def _ensure_not_hardlinked_file(self, path: Path) -> None:
        try:
            stat_result = path.stat()
        except OSError as exc:
            raise ReadToolError("path does not exist in the workspace") from exc
        if stat.S_ISREG(stat_result.st_mode) and stat_result.st_nlink > 1:
            raise ReadToolError("hardlinked files are not allowed")

    def _ensure_no_symlink_components(self, requested: Path) -> None:
        current = self.workspace_root
        for part in requested.parts:
            if part in {"", "."}:
                continue
            current = current / part
            try:
                if current.is_symlink():
                    raise ReadToolError("path is a symlink")
            except OSError as exc:
                raise ReadToolError("path does not exist in the workspace") from exc


@dataclass(frozen=True)
class GitReadTools:
    filesystem: FilesystemReadTools
    max_output_bytes: int
    git_log_limit: int

    def status(self, path: str = ".") -> JsonObject:
        repo = self._repo_path(path)
        output = self._run_git(repo, ["status", "--short"])
        status_lines: list[JsonValue] = []
        status_lines.extend(output.text.splitlines())
        return {
            "workspace_id": self.filesystem.workspace_id,
            "path": self.filesystem.relative_path(repo),
            "status": status_lines,
            "truncated": output.truncated,
        }

    def diff(self, path: str = ".") -> JsonObject:
        repo = self._repo_path(path)
        output = self._run_git(repo, ["diff", "--no-ext-diff", "--"])
        _ensure_git_diff_output_safe(output.text)
        return {
            "workspace_id": self.filesystem.workspace_id,
            "path": self.filesystem.relative_path(repo),
            "diff": output.text,
            "truncated": output.truncated,
        }

    def log(self, *, path: str = ".", limit: int) -> JsonObject:
        repo = self._repo_path(path)
        bounded_limit = max(1, min(limit, self.git_log_limit))
        output = self._run_git(repo, ["log", "--oneline", "-n", str(bounded_limit)])
        return {
            "workspace_id": self.filesystem.workspace_id,
            "path": self.filesystem.relative_path(repo),
            "commits": _git_log_lines(output.text),
            "truncated": output.truncated,
        }

    def commit_metadata(self, arguments: JsonObject) -> JsonObject:
        selector = _commit_ref_selector(arguments)
        _validate_commit_ref_selector(selector)
        include_body = _bool_arg(arguments, "include_body", default=False)
        include_emails = _bool_arg(arguments, "include_emails", default=False)
        include_diffstat = _bool_arg(arguments, "include_diffstat", default=True)

        repo = self._repo_path(".")
        self._ensure_repo_toplevel_in_workspace(repo)
        resolved_commit = self._resolve_commit(repo, selector)
        metadata = self._commit_identity_metadata(repo, resolved_commit)
        changed_files = (
            self._commit_changed_files(repo, resolved_commit)
            if include_diffstat
            else _empty_changes()
        )

        author_email = str(metadata["author_email"])
        committer_email = str(metadata["committer_email"])
        author: JsonObject = {
            "name": metadata["author_name"],
            "email_included": include_emails,
            "email_hash": sha256_digest(author_email) if author_email else None,
        }
        committer: JsonObject = {
            "name": metadata["committer_name"],
            "email_included": include_emails,
            "email_hash": sha256_digest(committer_email) if committer_email else None,
        }
        if include_emails:
            author["email"] = "[REDACTED]"
            author["email_redacted"] = True
            committer["email"] = "[REDACTED]"
            committer["email_redacted"] = True

        body = str(metadata["body"])
        body_text, body_truncated = _bounded_text(
            _sanitize_git_metadata_text(body, multiline=True),
            _COMMIT_METADATA_BODY_LIMIT,
        )
        subject_text, subject_truncated = _bounded_text(
            _sanitize_git_metadata_text(str(metadata["subject"]), multiline=False),
            _COMMIT_METADATA_SUBJECT_LIMIT,
        )
        result: JsonObject = {
            "workspace_id": self.filesystem.workspace_id,
            "tool_name": _GIT_COMMIT_METADATA_TOOL,
            "requested_ref": {
                "kind": selector["kind"],
                "value_hash": sha256_digest(selector["value"]),
            },
            "resolved_commit_hash": resolved_commit,
            "parent_hashes": metadata["parent_hashes"],
            "author": author,
            "committer": committer,
            "author_timestamp": metadata["author_timestamp"],
            "committer_timestamp": metadata["committer_timestamp"],
            "subject": subject_text,
            "subject_truncated": subject_truncated,
            "body_included": include_body,
            "changed_files_included": include_diffstat,
            "changed_files": changed_files["files"],
            "changed_file_count": changed_files["count"],
            "changed_files_truncated": changed_files["truncated"],
            "sensitive_paths_redacted": changed_files["sensitive_paths_redacted"],
            "output_policy": {
                "file_contents_included": False,
                "raw_diff_included": False,
                "emails_included": include_emails,
                "email_values_redacted": include_emails,
                "metadata_is_untrusted": True,
            },
        }
        if include_body:
            result["body"] = body_text
            result["body_truncated"] = body_truncated
        return result

    def _repo_path(self, path: str) -> Path:
        repo = self.filesystem.resolve_existing_path(path)
        if not repo.is_dir():
            raise ReadToolError("git path is not a directory")
        self._run_git(repo, ["rev-parse", "--is-inside-work-tree"])
        return repo

    def _resolve_commit(self, repo: Path, selector: JsonObject) -> str:
        kind = str(selector["kind"])
        value = str(selector["value"])
        if kind == "object_id":
            commitish = value
        elif kind == "branch":
            commitish = f"refs/heads/{value}"
        elif kind == "tag":
            commitish = f"refs/tags/{value}"
        else:
            raise ReadToolError("unsupported ref selector")

        output = self._run_git(
            repo,
            ["rev-parse", "--verify", "--end-of-options", f"{commitish}^{{commit}}"],
        )
        resolved = output.text.strip()
        if not _HEX_OBJECT_RE.fullmatch(resolved):
            raise ReadToolError("commit metadata resolution failed safely")
        return resolved.lower()

    def _commit_identity_metadata(self, repo: Path, commit_hash: str) -> JsonObject:
        commit = self._commit_format_field(repo, commit_hash, "%H")
        parents = self._commit_format_field(repo, commit_hash, "%P")
        author_name = self._commit_format_field(repo, commit_hash, "%an")
        author_email = self._commit_format_field(repo, commit_hash, "%ae")
        author_ts = self._commit_format_field(repo, commit_hash, "%aI")
        committer_name = self._commit_format_field(repo, commit_hash, "%cn")
        committer_email = self._commit_format_field(repo, commit_hash, "%ce")
        committer_ts = self._commit_format_field(repo, commit_hash, "%cI")
        subject = self._commit_format_field(repo, commit_hash, "%s")
        body = self._commit_format_field(repo, commit_hash, "%b")
        if commit.strip().lower() != commit_hash:
            raise ReadToolError("git commit metadata mismatch")
        parent_hashes = [parent.lower() for parent in parents.split() if parent]
        if any(not _HEX_OBJECT_RE.fullmatch(parent) for parent in parent_hashes):
            raise ReadToolError("git commit parent metadata is invalid")
        _validate_git_iso_timestamp(author_ts)
        _validate_git_iso_timestamp(committer_ts)
        return {
            "parent_hashes": cast(list[JsonValue], parent_hashes),
            "author_name": _sanitize_git_identity_name(author_name.strip()),
            "author_email": author_email.strip(),
            "author_timestamp": author_ts.strip(),
            "committer_name": _sanitize_git_identity_name(committer_name.strip()),
            "committer_email": committer_email.strip(),
            "committer_timestamp": committer_ts.strip(),
            "subject": subject.strip(),
            "body": body.strip(),
        }

    def _commit_format_field(self, repo: Path, commit_hash: str, format_field: str) -> str:
        output = self._run_git(
            repo,
            ["show", "--no-patch", f"--format={format_field}", commit_hash],
        )
        if output.truncated:
            raise ReadToolError("git commit metadata exceeds configured read limit")
        return output.text.removesuffix("\n")

    def _commit_changed_files(self, repo: Path, commit_hash: str) -> JsonObject:
        output = self._run_git(
            repo,
            [
                "diff-tree",
                "--root",
                "--no-commit-id",
                "--name-status",
                "-z",
                "-r",
                "--no-renames",
                commit_hash,
            ],
        )
        files: list[JsonValue] = []
        sensitive_paths_redacted = 0
        records = _parse_git_name_status_records(output.text)
        for status_code, path in records:
            if len(files) >= _COMMIT_METADATA_CHANGED_FILE_LIMIT:
                break
            file_record: JsonObject = {"status": status_code}
            if _safe_commit_path(path):
                file_record["path"] = path
                file_record["path_redacted"] = False
            else:
                file_record["path"] = "<redacted>"
                file_record["path_redacted"] = True
                file_record["path_hash"] = sha256_digest(path)
                sensitive_paths_redacted += 1
            files.append(file_record)
        return {
            "files": files,
            "count": len(records),
            "truncated": output.truncated or len(records) > len(files),
            "sensitive_paths_redacted": sensitive_paths_redacted,
        }


    def _run_git(self, cwd: Path, args: list[str]) -> GitOutput:
        command = ["git", "-C", str(cwd), *args]
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ReadToolError("git command failed safely") from exc

        if completed.returncode != 0:
            raise ReadToolError("path is not a readable git repository")

        stdout = completed.stdout
        truncated = len(stdout) > self.max_output_bytes
        if truncated:
            text = stdout[: self.max_output_bytes].decode("utf-8", errors="replace")
        else:
            text = stdout.decode("utf-8", errors="replace")
        return GitOutput(text=text, truncated=truncated)

    def _ensure_repo_toplevel_in_workspace(self, repo: Path) -> None:
        output = self._run_git(repo, ["rev-parse", "--show-toplevel"])
        try:
            toplevel = Path(output.text.strip()).resolve(strict=True)
            toplevel.relative_to(self.filesystem.workspace_root)
        except (OSError, ValueError) as exc:
            raise ReadToolError("git repository escapes the workspace scope") from exc


def _string_arg(arguments: JsonObject, name: str, *, default: Optional[str] = None) -> str:
    value = arguments.get(name, default)
    if not isinstance(value, str):
        raise ReadToolError(f"{name} must be a string")
    return value


def _workspace_id_arg(arguments: JsonObject, default: str) -> str:
    value = arguments.get("workspace_id", default)
    if not isinstance(value, str) or not value:
        raise ReadToolError("workspace_id must be a non-empty string")
    return value


def _int_arg(arguments: JsonObject, name: str, *, default: int) -> int:
    value = arguments.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ReadToolError(f"{name} must be an integer")
    return value


def _bool_arg(arguments: JsonObject, name: str, *, default: bool) -> bool:
    value = arguments.get(name, default)
    if not isinstance(value, bool):
        raise ReadToolError(f"{name} must be a boolean")
    return value


def _commit_ref_selector(arguments: JsonObject) -> JsonObject:
    raw = arguments.get("ref")
    if not isinstance(raw, dict):
        raise ReadToolError("ref must be an object")
    kind = raw.get("kind")
    value = raw.get("value")
    if not isinstance(kind, str) or not isinstance(value, str):
        raise ReadToolError("ref kind and value must be strings")
    return {"kind": kind, "value": value}


def _validate_commit_ref_selector(selector: JsonObject) -> None:
    kind = str(selector["kind"])
    value = str(selector["value"])
    if kind not in {"object_id", "branch", "tag"}:
        raise ReadToolError("unsupported ref selector")
    if not value or len(value.encode("utf-8")) > 128:
        raise ReadToolError("ref value is outside allowed bounds")
    _reject_control_or_unnormalized_text(value, label="ref value")
    if value.startswith("-"):
        raise ReadToolError("ref value is not allowed")
    if kind == "object_id":
        if not _HEX_OBJECT_RE.fullmatch(value):
            raise ReadToolError("object_id ref must be a full commit hash")
        return
    if value.startswith(("refs/", "origin/")):
        raise ReadToolError("ref value must name a local branch or tag")
    if value.startswith("/") or value.endswith("/") or "//" in value:
        raise ReadToolError("ref value is not allowed")
    forbidden_tokens = ("..", "@{", "\\", "^", "~", ":", "?", "*", "[", " ")
    if any(token in value for token in forbidden_tokens):
        raise ReadToolError("ref value contains unsupported syntax")
    if not _SAFE_REF_RE.fullmatch(value):
        raise ReadToolError("ref value contains unsupported characters")


def _path_type(path: Path) -> str:
    if path.is_symlink():
        return "symlink"
    if path.is_dir():
        return "directory"
    if path.is_file():
        return "file"
    return "other"


def _reject_ambiguous_path_input(path: str) -> None:
    _reject_control_or_unnormalized_text(path, label="path")
    lowered = path.lower()
    if any(token in lowered for token in ("%2e", "%2f", "%5c")):
        raise ReadToolError("encoded path tokens are not allowed")


def _reject_control_or_unnormalized_text(value: str, *, label: str) -> None:
    if any(
        ord(character) < 32
        or ord(character) == 127
        or unicodedata.category(character) in {"Cc", "Cf", "Cs"}
        for character in value
    ):
        raise ReadToolError(f"{label} contains control characters")
    if not unicodedata.is_normalized("NFC", value):
        raise ReadToolError(f"{label} is not Unicode-normalized")


def _ensure_relative_parts_not_sensitive(relative: Path) -> None:
    for part in relative.parts:
        lowered = part.lower()
        if (
            part.startswith(".")
            or lowered in _SENSITIVE_EXACT_PATH_PARTS
            or any(marker in lowered for marker in _SENSITIVE_PATH_MARKERS)
        ):
            raise ReadToolError("path is hidden or sensitive")


def _ensure_git_diff_output_safe(diff_text: str) -> None:
    for raw_path in _git_diff_paths(diff_text):
        candidate = Path(raw_path)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ReadToolError("git diff includes an unsafe path")
        _ensure_relative_parts_not_sensitive(candidate)


def _git_diff_paths(diff_text: str) -> set[str]:
    paths: set[str] = set()
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            try:
                parts = shlex.split(line)
            except ValueError as exc:
                raise ReadToolError("git diff path metadata is invalid") from exc
            for token in parts[2:4]:
                path = _strip_git_path_prefix(token)
                if path is not None:
                    paths.add(path)
        elif line.startswith(("--- ", "+++ ")):
            token = line[4:].strip()
            if token == "/dev/null":
                continue
            path = _strip_git_path_prefix(token)
            if path is not None:
                paths.add(path)
    return paths


def _strip_git_path_prefix(token: str) -> str | None:
    if token.startswith(("a/", "b/")):
        return token[2:]
    if token in {"a", "b"}:
        return None
    return token


def _open_no_follow_directory(path: Path) -> int:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise ReadToolError("path is not a safe directory") from exc
    try:
        stat_result = os.fstat(fd)
        if not stat.S_ISDIR(stat_result.st_mode):
            raise ReadToolError("path is not a safe directory")
        return fd
    except Exception:
        os.close(fd)
        raise


def _open_no_follow_directory_component(parent_fd: int, name: str) -> int:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(name, flags, dir_fd=parent_fd)
    except OSError as exc:
        raise ReadToolError("path is not a safe directory") from exc
    try:
        stat_result = os.fstat(fd)
        if not stat.S_ISDIR(stat_result.st_mode):
            raise ReadToolError("path is not a safe directory")
        return fd
    except Exception:
        os.close(fd)
        raise


def _open_no_follow_file_component(parent_fd: int, name: str) -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        return os.open(name, flags, dir_fd=parent_fd)
    except OSError as exc:
        raise ReadToolError("path is not a safe regular file") from exc


def _git_log_lines(output: str) -> list[JsonValue]:
    commits: list[JsonValue] = []
    for line in output.splitlines():
        commit_hash, _, subject = line.partition(" ")
        commits.append({"commit": commit_hash, "subject": subject})
    return commits


def _bounded_text(value: str, limit: int) -> tuple[str, bool]:
    encoded = value.encode("utf-8")
    if len(encoded) <= limit:
        return value, False
    return encoded[:limit].decode("utf-8", errors="replace"), True


def _parse_git_name_status_records(output: str) -> list[tuple[str, str]]:
    tokens = [token for token in output.split("\x00") if token]
    records: list[tuple[str, str]] = []
    for index in range(0, len(tokens) - 1, 2):
        status_code = tokens[index]
        path = tokens[index + 1]
        if not status_code or not path:
            continue
        status = status_code[0]
        if status not in {"A", "C", "D", "M", "R", "T", "U", "X"}:
            status = "other"
        records.append((status, path))
    return records


def _safe_commit_path(path: str) -> bool:
    try:
        _reject_ambiguous_path_input(path)
        candidate = Path(path)
        if candidate.is_absolute() or ".." in candidate.parts:
            return False
        _ensure_relative_parts_not_sensitive(candidate)
    except ReadToolError:
        return False
    return True


def _empty_changes() -> JsonObject:
    return {
        "files": [],
        "count": 0,
        "truncated": False,
        "sensitive_paths_redacted": 0,
    }


def _sanitize_git_metadata_text(value: str, *, multiline: bool) -> str:
    normalized = unicodedata.normalize("NFC", value)
    safe_chars: list[str] = []
    for character in normalized:
        if multiline and character in {"\n", "\t"}:
            safe_chars.append(character)
            continue
        if (
            ord(character) < 32
            or ord(character) == 127
            or unicodedata.category(character) in {"Cc", "Cf", "Cs"}
        ):
            safe_chars.append("\uFFFD")
            continue
        safe_chars.append(character)
    return "".join(safe_chars)


def _sanitize_git_identity_name(value: str) -> str:
    sanitized = _sanitize_git_metadata_text(value, multiline=False)
    return _EMAIL_LIKE_RE.sub("[REDACTED_EMAIL]", sanitized)


def _validate_git_iso_timestamp(value: str) -> None:
    try:
        datetime.fromisoformat(value.strip())
    except ValueError as exc:
        raise ReadToolError("git commit timestamp metadata is invalid") from exc

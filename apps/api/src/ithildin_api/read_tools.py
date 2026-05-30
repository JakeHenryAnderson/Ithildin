"""Safe in-process read-only tool adapters."""

from __future__ import annotations

import os
import stat
import subprocess
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

from ithildin_schemas import JsonObject, JsonValue

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
    }
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
        if target.is_symlink():
            raise ReadToolError("path is a symlink")
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
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(path, flags)
        except OSError as exc:
            raise ReadToolError("path is not a safe regular file") from exc
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
        with path.open("r", encoding="utf-8", errors="replace") as candidate_file:
            for line_number, line in enumerate(candidate_file, start=1):
                if len(matches) >= self.search_result_limit:
                    return
                if query in line:
                    matches.append(
                        {
                            "path": self.relative_path(path),
                            "line_number": line_number,
                            "preview": line.rstrip("\n")[:240],
                        }
                    )

    def _ensure_under_workspace(self, path: Path) -> None:
        try:
            path.relative_to(self.workspace_root)
        except ValueError as exc:
            raise ReadToolError("path escapes the workspace scope") from exc

    def _ensure_not_sensitive(self, path: Path) -> None:
        relative = path.relative_to(self.workspace_root)
        for part in relative.parts:
            lowered = part.lower()
            if part.startswith(".") or lowered in {"secret", "secrets"} or lowered == ".env":
                raise ReadToolError("path is hidden or sensitive")

    def _ensure_not_hardlinked_file(self, path: Path) -> None:
        try:
            stat_result = path.stat()
        except OSError as exc:
            raise ReadToolError("path does not exist in the workspace") from exc
        if stat.S_ISREG(stat_result.st_mode) and stat_result.st_nlink > 1:
            raise ReadToolError("hardlinked files are not allowed")


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

    def _repo_path(self, path: str) -> Path:
        repo = self.filesystem.resolve_existing_path(path)
        if not repo.is_dir():
            raise ReadToolError("git path is not a directory")
        self._run_git(repo, ["rev-parse", "--is-inside-work-tree"])
        return repo

    def _run_git(self, cwd: Path, args: list[str]) -> GitOutput:
        command = ["git", "-C", str(cwd), *args]
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ReadToolError("git command failed safely") from exc

        if completed.returncode != 0:
            raise ReadToolError("path is not a readable git repository")

        encoded = completed.stdout.encode("utf-8")
        truncated = len(encoded) > self.max_output_bytes
        if truncated:
            text = encoded[: self.max_output_bytes].decode("utf-8", errors="replace")
        else:
            text = completed.stdout
        return GitOutput(text=text, truncated=truncated)


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


def _path_type(path: Path) -> str:
    if path.is_symlink():
        return "symlink"
    if path.is_dir():
        return "directory"
    if path.is_file():
        return "file"
    return "other"


def _reject_ambiguous_path_input(path: str) -> None:
    lowered = path.lower()
    if any(token in lowered for token in ("%2e", "%2f", "%5c")):
        raise ReadToolError("encoded path tokens are not allowed")
    if not unicodedata.is_normalized("NFC", path):
        raise ReadToolError("path is not Unicode-normalized")


def _git_log_lines(output: str) -> list[JsonValue]:
    commits: list[JsonValue] = []
    for line in output.splitlines():
        commit_hash, _, subject = line.partition(" ")
        commits.append({"commit": commit_hash, "subject": subject})
    return commits

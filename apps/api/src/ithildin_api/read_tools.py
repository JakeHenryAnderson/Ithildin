"""Safe in-process read-only tool adapters."""

from __future__ import annotations

import hashlib
import json
import os
import re
import selectors
import shlex
import stat
import subprocess
import time
import tomllib
import unicodedata
import xml.etree.ElementTree as ET
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
        "git.show.ref_summary",
        "project.dependency.summary",
        "project.manifest.summary",
    }
)

_GIT_COMMIT_METADATA_TOOL = "git.show.commit_metadata"
_GIT_REF_SUMMARY_TOOL = "git.show.ref_summary"
_PROJECT_DEPENDENCY_SUMMARY_TOOL = "project.dependency.summary"
_PROJECT_MANIFEST_SUMMARY_TOOL = "project.manifest.summary"
_HEX_OBJECT_RE = re.compile(r"^[0-9a-fA-F]{40}$|^[0-9a-fA-F]{64}$")
_SAFE_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
_EMAIL_LIKE_RE = re.compile(r"[\w.!#$%&'*+/=?^`{|}~-]+@[\w.-]+")
_COMMIT_METADATA_SUBJECT_LIMIT = 240
_COMMIT_METADATA_BODY_LIMIT = 2000
_COMMIT_METADATA_IDENTITY_LIMIT = 240
_COMMIT_METADATA_CHANGED_FILE_LIMIT = 100
_REF_SUMMARY_DEFAULT_LIMIT = 100
_REF_SUMMARY_MAX_LIMIT = 200
_REF_SUMMARY_NAME_BYTE_LIMIT = 240
_PROJECT_MANIFEST_DEFAULT_LIMIT = 20
_PROJECT_MANIFEST_MAX_LIMIT = 20
_PROJECT_MANIFEST_MAX_TOTAL_BYTES = 262144
_PROJECT_MANIFEST_ALLOWLIST = (
    "package.json",
    "pyproject.toml",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "requirements.txt",
    "Gemfile",
    "composer.json",
)
_PROJECT_MANIFEST_ECOSYSTEMS = {
    "package.json": "node",
    "pyproject.toml": "python",
    "go.mod": "go",
    "Cargo.toml": "rust",
    "pom.xml": "java",
    "build.gradle": "gradle",
    "requirements.txt": "python",
    "Gemfile": "ruby",
    "composer.json": "php",
}
_LOCKFILE_PRESENCE = {
    "package.json": ("package-lock.json", "pnpm-lock.yaml", "yarn.lock"),
    "pyproject.toml": ("poetry.lock", "uv.lock", "pdm.lock"),
    "go.mod": ("go.sum",),
    "Cargo.toml": ("Cargo.lock",),
    "pom.xml": (),
    "build.gradle": ("gradle.lockfile",),
    "requirements.txt": (),
    "Gemfile": ("Gemfile.lock",),
    "composer.json": ("composer.lock",),
}
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
        if tool_name == _GIT_REF_SUMMARY_TOOL:
            return self._ref_summary_resource_from_arguments(arguments)
        if tool_name in {
            _PROJECT_DEPENDENCY_SUMMARY_TOOL,
            _PROJECT_MANIFEST_SUMMARY_TOOL,
        }:
            return self._project_manifest_resource_from_arguments(arguments, tool_name=tool_name)

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

    def _ref_summary_resource_from_arguments(self, arguments: JsonObject) -> JsonObject:
        workspace_id = _workspace_id_arg(arguments, self.default_workspace_id)
        resource: JsonObject = {
            "type": "git_refs",
            "workspace_id": workspace_id,
            "in_scope": False,
        }
        try:
            self._filesystem(workspace_id)
            git = self._git(workspace_id)
            repo = git._repo_path(".")
            git._ensure_repo_toplevel_in_workspace(repo)
            selector_kind = _ref_summary_selector_kind(arguments)
            _ref_summary_limit(arguments)
        except ReadToolError as exc:
            resource["scope_error"] = exc.reason
            return resource
        resource.update(
            {
                "selector_kind": selector_kind,
                "in_scope": True,
            }
        )
        return resource

    def _project_manifest_resource_from_arguments(
        self, arguments: JsonObject, *, tool_name: str
    ) -> JsonObject:
        workspace_id = _workspace_id_arg(arguments, self.default_workspace_id)
        root = _project_manifest_root(arguments)
        resource_type = (
            "project_dependencies"
            if tool_name == _PROJECT_DEPENDENCY_SUMMARY_TOOL
            else "project_manifest"
        )
        resource: JsonObject = {
            "type": resource_type,
            "workspace_id": workspace_id,
            "root": root,
            "in_scope": False,
        }
        try:
            filesystem = self._filesystem(workspace_id)
            target = filesystem.resolve_existing_path(root)
            if not target.is_dir():
                raise ReadToolError("project manifest root is not a directory")
            _project_manifest_kinds(arguments)
            _project_manifest_limit(arguments)
        except ReadToolError as exc:
            resource["scope_error"] = exc.reason
            return resource
        resource.update(
            {
                "root": filesystem.relative_path(target),
                "manifest_kinds": cast(JsonValue, _project_manifest_kinds(arguments)),
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
        if tool_name == _GIT_REF_SUMMARY_TOOL:
            return git.ref_summary(arguments)
        if tool_name == _PROJECT_DEPENDENCY_SUMMARY_TOOL:
            return filesystem.project_dependency_summary(arguments)
        if tool_name == _PROJECT_MANIFEST_SUMMARY_TOOL:
            return filesystem.project_manifest_summary(arguments)
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

    def project_manifest_summary(self, arguments: JsonObject) -> JsonObject:
        _validate_project_manifest_summary_arguments(arguments)
        root_arg = _project_manifest_root(arguments)
        manifest_kinds = _project_manifest_kinds(arguments)
        limit = _project_manifest_limit(arguments)
        root_path = self.resolve_existing_path(root_arg)
        if not root_path.is_dir():
            raise ReadToolError("project manifest root is not a directory")

        root_relative = Path(self.relative_path(root_path))
        found: list[tuple[str, Path]] = []
        for kind in manifest_kinds:
            candidate = root_path / kind
            if not candidate.exists():
                continue
            relative = Path(kind) if self.relative_path(root_path) == "." else root_relative / kind
            found.append((kind, self.resolve_existing_path(relative.as_posix())))

        manifests: list[JsonValue] = []
        total_bytes = 0
        for kind, path in found[:limit]:
            data = self.read_file_bytes(path)
            total_bytes += len(data)
            if total_bytes > _PROJECT_MANIFEST_MAX_TOTAL_BYTES:
                raise ReadToolError("project manifest summary exceeds configured read limit")
            manifests.append(
                _project_manifest_record(
                    manifest_id=f"manifest_{len(manifests) + 1:04d}",
                    kind=kind,
                    data=data,
                    root_path=root_path,
                )
            )

        return {
            "workspace_id": self.workspace_id,
            "tool_name": _PROJECT_MANIFEST_SUMMARY_TOOL,
            "root": self.relative_path(root_path),
            "manifest_count": len(manifests),
            "truncated": len(found) > len(manifests),
            "manifests": manifests,
            "output_policy": {
                "file_contents_included": False,
                "dependency_names_included": False,
                "dependency_versions_included": False,
                "package_names_included": False,
                "package_script_names_included": False,
                "package_script_values_included": False,
                "registry_or_network_access_used": False,
                "package_manager_execution_used": False,
                "recursive_discovery_used": False,
                "metadata_is_untrusted": True,
            },
            "limits": {
                "manifest_limit": limit,
                "max_manifest_file_bytes": self.max_read_bytes,
                "max_total_parsed_bytes": _PROJECT_MANIFEST_MAX_TOTAL_BYTES,
            },
        }

    def project_dependency_summary(self, arguments: JsonObject) -> JsonObject:
        _validate_project_dependency_summary_arguments(arguments)
        manifest_summary = self.project_manifest_summary(arguments)
        manifests: list[JsonValue] = []
        section_totals: dict[str, int] = {}
        ecosystem_counts: dict[str, int] = {}
        kind_counts: dict[str, int] = {}
        total_direct_dependencies = 0
        for item in cast(list[JsonObject], manifest_summary.get("manifests", [])):
            dependency_counts = _safe_int_mapping(item.get("dependency_section_counts"))
            direct_dependency_count = sum(dependency_counts.values())
            total_direct_dependencies += direct_dependency_count
            for section, count in dependency_counts.items():
                section_totals[section] = section_totals.get(section, 0) + count
            kind = item.get("kind")
            ecosystem = item.get("ecosystem")
            if isinstance(kind, str):
                kind_counts[kind] = kind_counts.get(kind, 0) + 1
            if isinstance(ecosystem, str):
                ecosystem_counts[ecosystem] = ecosystem_counts.get(ecosystem, 0) + 1
            manifests.append(
                {
                    "manifest_id": item.get("manifest_id"),
                    "kind": kind,
                    "ecosystem": ecosystem,
                    "path_role": item.get("path_role"),
                    "dependency_section_counts": cast(JsonObject, dependency_counts),
                    "direct_dependency_count": direct_dependency_count,
                    "parse_status": item.get("parse_status"),
                    "parse_error_reason": item.get("parse_error_reason"),
                    "dependency_names_included": False,
                    "dependency_versions_included": False,
                    "package_names_included": False,
                    "package_script_names_included": False,
                    "package_script_values_included": False,
                    "file_contents_included": False,
                    "lockfile_contents_included": False,
                }
            )

        return {
            "workspace_id": self.workspace_id,
            "tool_name": _PROJECT_DEPENDENCY_SUMMARY_TOOL,
            "root": manifest_summary["root"],
            "manifest_count": manifest_summary["manifest_count"],
            "truncated": manifest_summary["truncated"],
            "total_direct_dependency_count": total_direct_dependencies,
            "dependency_section_totals": cast(JsonObject, section_totals),
            "ecosystem_counts": cast(JsonObject, ecosystem_counts),
            "manifest_kind_counts": cast(JsonObject, kind_counts),
            "manifests": manifests,
            "output_policy": {
                "file_contents_included": False,
                "dependency_names_included": False,
                "dependency_versions_included": False,
                "package_names_included": False,
                "package_script_names_included": False,
                "package_script_values_included": False,
                "lockfile_contents_included": False,
                "registry_or_network_access_used": False,
                "package_manager_execution_used": False,
                "recursive_discovery_used": False,
                "transitive_dependencies_resolved": False,
                "license_vulnerability_or_compliance_claims_included": False,
                "metadata_is_untrusted": True,
            },
            "limits": manifest_summary["limits"],
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

    def ref_summary(self, arguments: JsonObject) -> JsonObject:
        _validate_ref_summary_arguments(arguments)
        selector_kind = _ref_summary_selector_kind(arguments)
        limit = _ref_summary_limit(arguments)

        repo = self._repo_path(".")
        self._ensure_repo_toplevel_in_workspace(repo)
        prefixes = _ref_summary_prefixes(selector_kind)
        output = self._run_git(
            repo,
            [
                "for-each-ref",
                "--format=%(refname)%00%(objectname)%00%(objecttype)%00"
                "%(*objectname)%00%(*objecttype)%00%(HEAD)%00%(symref)",
                *prefixes,
            ],
        )
        if output.truncated:
            raise ReadToolError("git ref summary exceeds configured read limit")

        refs = _parse_ref_summary_output(output.text, selector_kind)
        selected_refs = refs[:limit]
        return {
            "workspace_id": self.filesystem.workspace_id,
            "tool_name": _GIT_REF_SUMMARY_TOOL,
            "selector": {"kind": selector_kind},
            "ref_count": len(selected_refs),
            "total_ref_count": len(refs),
            "truncated": len(refs) > limit,
            "refs": cast(list[JsonValue], selected_refs),
            "output_policy": {
                "file_contents_included": False,
                "raw_diff_included": False,
                "ref_names_included": False,
                "stable_ref_hashes_included": False,
                "ref_ids_are_response_local": True,
                "metadata_is_untrusted": True,
            },
        }

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
            "author_name": _bounded_text(
                _sanitize_git_identity_name(author_name.strip()),
                _COMMIT_METADATA_IDENTITY_LIMIT,
            )[0],
            "author_email": author_email.strip(),
            "author_timestamp": author_ts.strip(),
            "committer_name": _bounded_text(
                _sanitize_git_identity_name(committer_name.strip()),
                _COMMIT_METADATA_IDENTITY_LIMIT,
            )[0],
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
        timeout_seconds = 10.0
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            raise ReadToolError("git command failed safely") from exc

        stdout = bytearray()
        truncated = False
        deadline = time.monotonic() + timeout_seconds
        selector = selectors.DefaultSelector()
        try:
            if process.stdout is None:
                raise ReadToolError("git command failed safely")
            selector.register(process.stdout, selectors.EVENT_READ)
            fd = process.stdout.fileno()
            while True:
                if process.poll() is not None:
                    while len(stdout) <= self.max_output_bytes:
                        chunk = os.read(fd, min(65536, self.max_output_bytes + 1 - len(stdout)))
                        if not chunk:
                            break
                        stdout.extend(chunk)
                    truncated = len(stdout) > self.max_output_bytes
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(command, timeout_seconds)
                events = selector.select(timeout=min(0.1, remaining))
                if not events:
                    continue
                chunk = os.read(fd, min(65536, self.max_output_bytes + 1 - len(stdout)))
                if not chunk:
                    break
                stdout.extend(chunk)
                if len(stdout) > self.max_output_bytes:
                    truncated = True
                    process.kill()
                    break
            if truncated:
                process.kill()
            return_code = process.wait(timeout=max(0.0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired as exc:
            process.kill()
            process.wait()
            raise ReadToolError("git command failed safely") from exc
        finally:
            selector.close()
            if process.stdout is not None:
                process.stdout.close()

        if return_code != 0 and not truncated:
            raise ReadToolError("path is not a readable git repository")

        text = bytes(stdout[: self.max_output_bytes]).decode("utf-8", errors="replace")
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


def _validate_ref_summary_arguments(arguments: JsonObject) -> None:
    allowed = {"selector", "limit", "workspace_id"}
    unknown = sorted(set(arguments) - allowed)
    if unknown:
        raise ReadToolError("git ref summary received unsupported arguments")
    _ref_summary_selector_kind(arguments)
    _ref_summary_limit(arguments)


def _ref_summary_selector_kind(arguments: JsonObject) -> str:
    raw = arguments.get("selector")
    if not isinstance(raw, dict):
        raise ReadToolError("selector must be an object")
    unknown = sorted(set(raw) - {"kind"})
    if unknown:
        raise ReadToolError("git ref summary selector contains unsupported fields")
    kind = raw.get("kind")
    if not isinstance(kind, str):
        raise ReadToolError("selector kind must be a string")
    if kind not in {"all_local", "branch", "tag"}:
        raise ReadToolError("unsupported ref summary selector")
    return kind


def _ref_summary_limit(arguments: JsonObject) -> int:
    limit = _int_arg(arguments, "limit", default=_REF_SUMMARY_DEFAULT_LIMIT)
    if limit < 1 or limit > _REF_SUMMARY_MAX_LIMIT:
        raise ReadToolError("git ref summary limit is outside allowed bounds")
    return limit


def _ref_summary_prefixes(selector_kind: str) -> list[str]:
    if selector_kind == "branch":
        return ["refs/heads"]
    if selector_kind == "tag":
        return ["refs/tags"]
    return ["refs/heads", "refs/tags"]


def _parse_ref_summary_output(output: str, selector_kind: str) -> list[JsonObject]:
    refs: list[JsonObject] = []
    seen_casefolded: dict[tuple[str, str], str] = {}
    for line in output.splitlines():
        if not line:
            continue
        fields = line.split("\x00")
        if len(fields) != 7:
            raise ReadToolError("git ref summary metadata is invalid")
        refname, object_id, object_type, peeled_object, peeled_type, head_marker, symref = fields
        if symref:
            continue
        kind, name = _ref_summary_kind_and_name(refname, selector_kind)
        _validate_ref_summary_name(name)
        casefold_key = (kind, name.casefold())
        existing = seen_casefolded.get(casefold_key)
        if existing is not None and existing != name:
            raise ReadToolError("git ref summary contains ambiguous ref names")
        seen_casefolded[casefold_key] = name
        commit_hash = _ref_summary_resolved_commit(
            object_id=object_id,
            object_type=object_type,
            peeled_object=peeled_object,
            peeled_type=peeled_type,
        )
        if commit_hash is None:
            continue
        record: JsonObject = {
            "kind": kind,
            "ref_id": f"ref_{len(refs) + 1:04d}",
            "resolved_commit_hash": commit_hash,
        }
        if kind == "branch":
            record["is_current_branch"] = head_marker == "*"
        if kind == "tag":
            record["peeled_from_tag_object"] = object_type == "tag"
        refs.append(record)
    return refs


def _ref_summary_kind_and_name(refname: str, selector_kind: str) -> tuple[str, str]:
    if refname.startswith("refs/heads/"):
        if selector_kind == "tag":
            raise ReadToolError("git ref summary selector returned an unexpected branch")
        return "branch", refname.removeprefix("refs/heads/")
    if refname.startswith("refs/tags/"):
        if selector_kind == "branch":
            raise ReadToolError("git ref summary selector returned an unexpected tag")
        return "tag", refname.removeprefix("refs/tags/")
    raise ReadToolError("git ref summary returned an unsupported ref namespace")


def _validate_ref_summary_name(name: str) -> None:
    if not name or len(name.encode("utf-8")) > _REF_SUMMARY_NAME_BYTE_LIMIT:
        raise ReadToolError("git ref summary ref name is outside allowed bounds")
    _reject_control_or_unnormalized_text(name, label="ref name")
    if name.startswith("-") or name.startswith("/") or name.endswith("/") or "//" in name:
        raise ReadToolError("git ref summary ref name is not allowed")
    forbidden_tokens = ("..", "@{", "\\", "^", "~", ":", "?", "*", "[", " ")
    if any(token in name for token in forbidden_tokens):
        raise ReadToolError("git ref summary ref name contains unsupported syntax")
    parts = name.split("/")
    if any(not part or part.startswith(".") or part.endswith(".lock") for part in parts):
        raise ReadToolError("git ref summary ref name contains unsupported syntax")
    if not _SAFE_REF_RE.fullmatch(name):
        raise ReadToolError("git ref summary ref name contains unsupported characters")


def _ref_summary_resolved_commit(
    *,
    object_id: str,
    object_type: str,
    peeled_object: str,
    peeled_type: str,
) -> str | None:
    if object_type == "commit":
        candidate = object_id
    elif object_type == "tag" and peeled_type == "commit":
        candidate = peeled_object
    else:
        return None
    if not _HEX_OBJECT_RE.fullmatch(candidate):
        raise ReadToolError("git ref summary commit metadata is invalid")
    return candidate.lower()


def _validate_project_manifest_summary_arguments(arguments: JsonObject) -> None:
    allowed = {"workspace_id", "root", "manifest_kinds", "limit"}
    unknown = sorted(set(arguments) - allowed)
    if unknown:
        raise ReadToolError("project manifest summary received unsupported arguments")
    _project_manifest_root(arguments)
    _project_manifest_kinds(arguments)
    _project_manifest_limit(arguments)


def _validate_project_dependency_summary_arguments(arguments: JsonObject) -> None:
    allowed = {"workspace_id", "root", "manifest_kinds", "limit"}
    unknown = sorted(set(arguments) - allowed)
    if unknown:
        raise ReadToolError("project dependency summary received unsupported arguments")
    _project_manifest_root(arguments)
    _project_manifest_kinds(arguments)
    _project_manifest_limit(arguments)


def _project_manifest_root(arguments: JsonObject) -> str:
    root = _string_arg(arguments, "root", default=".")
    if not root:
        raise ReadToolError("project manifest root must be a non-empty string")
    return root


def _project_manifest_kinds(arguments: JsonObject) -> list[str]:
    raw = arguments.get("manifest_kinds")
    if raw is None:
        return list(_PROJECT_MANIFEST_ALLOWLIST)
    if not isinstance(raw, list):
        raise ReadToolError("manifest_kinds must be an array")
    kinds: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, str):
            raise ReadToolError("manifest_kinds entries must be strings")
        if item not in _PROJECT_MANIFEST_ALLOWLIST:
            raise ReadToolError("manifest kind is not allowlisted")
        if item in seen:
            raise ReadToolError("manifest_kinds entries must be unique")
        seen.add(item)
        kinds.append(item)
    if not kinds:
        raise ReadToolError("manifest_kinds must not be empty")
    return kinds


def _project_manifest_limit(arguments: JsonObject) -> int:
    limit = _int_arg(arguments, "limit", default=_PROJECT_MANIFEST_DEFAULT_LIMIT)
    if limit < 1 or limit > _PROJECT_MANIFEST_MAX_LIMIT:
        raise ReadToolError("project manifest summary limit is outside allowed bounds")
    return limit


def _project_manifest_record(
    *,
    manifest_id: str,
    kind: str,
    data: bytes,
    root_path: Path,
) -> JsonObject:
    if b"\x00" in data:
        raise ReadToolError("project manifest appears to be binary")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ReadToolError("project manifest is not valid UTF-8 text") from exc
    digest = f"sha256:{hashlib.sha256(data).hexdigest()}"
    parsed = _parse_project_manifest(kind, text)
    lockfile_presence: JsonObject = {}
    for lockfile in _LOCKFILE_PRESENCE.get(kind, ()):
        lockfile_presence[lockfile] = (root_path / lockfile).is_file()
    return {
        "manifest_id": manifest_id,
        "kind": kind,
        "ecosystem": _PROJECT_MANIFEST_ECOSYSTEMS[kind],
        "path_role": "root_manifest",
        "size_bytes": len(data),
        "sha256": digest,
        "dependency_section_counts": parsed["dependency_section_counts"],
        "script_count": parsed["script_count"],
        "lockfile_presence": lockfile_presence,
        "parse_status": parsed["parse_status"],
        "parse_error_reason": parsed.get("parse_error_reason"),
        "dependency_names_included": False,
        "script_values_included": False,
        "file_contents_included": False,
    }


def _safe_int_mapping(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    safe: dict[str, int] = {}
    for key, count in value.items():
        if isinstance(key, str) and isinstance(count, int) and not isinstance(count, bool):
            safe[key] = count
    return safe


def _parse_project_manifest(kind: str, text: str) -> JsonObject:
    try:
        if kind == "package.json":
            return _parse_package_json_manifest(text)
        if kind == "composer.json":
            return _parse_composer_json_manifest(text)
        if kind == "pyproject.toml":
            return _parse_pyproject_manifest(text)
        if kind == "Cargo.toml":
            return _parse_cargo_manifest(text)
        if kind == "go.mod":
            return _parse_go_mod_manifest(text)
        if kind == "pom.xml":
            return _parse_pom_manifest(text)
        if kind == "build.gradle":
            return _parse_gradle_manifest(text)
        if kind == "requirements.txt":
            return _parse_requirements_manifest(text)
        if kind == "Gemfile":
            return _parse_gemfile_manifest(text)
    except (ET.ParseError, json.JSONDecodeError, tomllib.TOMLDecodeError, ValueError):
        return {
            "dependency_section_counts": {},
            "script_count": 0,
            "parse_status": "parse_failed",
            "parse_error_reason": "manifest parse failed safely",
        }
    raise ReadToolError("unsupported project manifest kind")


def _parse_package_json_manifest(text: str) -> JsonObject:
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("package.json must be an object")
    dependency_sections: JsonObject = {
        section: _mapping_count(payload.get(section))
        for section in (
            "dependencies",
            "devDependencies",
            "peerDependencies",
            "optionalDependencies",
            "bundledDependencies",
        )
        if isinstance(payload.get(section), (dict, list))
    }
    return {
        "dependency_section_counts": dependency_sections,
        "script_count": _mapping_count(payload.get("scripts")),
        "parse_status": "parsed",
    }


def _parse_composer_json_manifest(text: str) -> JsonObject:
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("composer.json must be an object")
    return {
        "dependency_section_counts": {
            section: _mapping_count(payload.get(section))
            for section in ("require", "require-dev")
            if isinstance(payload.get(section), dict)
        },
        "script_count": _mapping_count(payload.get("scripts")),
        "parse_status": "parsed",
    }


def _parse_pyproject_manifest(text: str) -> JsonObject:
    payload = tomllib.loads(text)
    project = payload.get("project")
    tool = payload.get("tool")
    dependency_counts: JsonObject = {}
    if isinstance(project, dict):
        dependencies = project.get("dependencies")
        optional = project.get("optional-dependencies")
        if isinstance(dependencies, list):
            dependency_counts["project.dependencies"] = _string_list_count(dependencies)
        if isinstance(optional, dict):
            dependency_counts["project.optional-dependencies"] = sum(
                _string_list_count(value) for value in optional.values() if isinstance(value, list)
            )
    if isinstance(payload.get("dependency-groups"), dict):
        groups = payload["dependency-groups"]
        dependency_counts["dependency-groups"] = sum(
            _string_list_count(value) for value in groups.values() if isinstance(value, list)
        )
    script_count = 0
    if isinstance(project, dict):
        script_count += _mapping_count(project.get("scripts"))
        script_count += _mapping_count(project.get("gui-scripts"))
    if isinstance(tool, dict) and isinstance(tool.get("poetry"), dict):
        poetry = tool["poetry"]
        dependency_counts["tool.poetry.dependencies"] = _mapping_count(
            poetry.get("dependencies")
        )
        dependency_counts["tool.poetry.group-dependencies"] = _poetry_group_dependency_count(
            poetry.get("group")
        )
        script_count += _mapping_count(poetry.get("scripts"))
    return {
        "dependency_section_counts": dependency_counts,
        "script_count": script_count,
        "parse_status": "parsed",
    }


def _parse_cargo_manifest(text: str) -> JsonObject:
    payload = tomllib.loads(text)
    dependency_counts: JsonObject = {
        section: _mapping_count(payload.get(section))
        for section in ("dependencies", "dev-dependencies", "build-dependencies")
        if isinstance(payload.get(section), dict)
    }
    return {
        "dependency_section_counts": dependency_counts,
        "script_count": 1 if _cargo_has_build_script(payload) else 0,
        "parse_status": "parsed",
    }


def _parse_go_mod_manifest(text: str) -> JsonObject:
    count = 0
    in_require_block = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue
        if line == "require (":
            in_require_block = True
            continue
        if in_require_block and line == ")":
            in_require_block = False
            continue
        if in_require_block:
            count += 1
        elif line.startswith("require "):
            count += 1
    return {
        "dependency_section_counts": {"require": count} if count else {},
        "script_count": 0,
        "parse_status": "parsed",
    }


def _parse_pom_manifest(text: str) -> JsonObject:
    root = ET.fromstring(text)
    dependency_count = sum(
        1 for element in root.iter() if _xml_local_name(element.tag) == "dependency"
    )
    return {
        "dependency_section_counts": {"dependencies": dependency_count}
        if dependency_count
        else {},
        "script_count": 0,
        "parse_status": "parsed",
    }


def _parse_gradle_manifest(text: str) -> JsonObject:
    dependency_markers = (
        "implementation",
        "api",
        "compileOnly",
        "runtimeOnly",
        "testImplementation",
        "testRuntimeOnly",
    )
    count = 0
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("//", "#")):
            continue
        if any(
            line.startswith(marker + " ") or line.startswith(marker + "(")
            for marker in dependency_markers
        ):
            count += 1
    return {
        "dependency_section_counts": {"dependencies": count} if count else {},
        "script_count": 0,
        "parse_status": "parsed",
    }


def _parse_requirements_manifest(text: str) -> JsonObject:
    count = 0
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", "-")):
            continue
        count += 1
    return {
        "dependency_section_counts": {"requirements": count} if count else {},
        "script_count": 0,
        "parse_status": "parsed",
    }


def _parse_gemfile_manifest(text: str) -> JsonObject:
    count = sum(1 for line in text.splitlines() if line.strip().startswith("gem "))
    return {
        "dependency_section_counts": {"gem": count} if count else {},
        "script_count": 0,
        "parse_status": "parsed",
    }


def _mapping_count(value: object) -> int:
    return len(value) if isinstance(value, dict) else 0


def _string_list_count(value: list[object]) -> int:
    return sum(1 for item in value if isinstance(item, str))


def _poetry_group_dependency_count(value: object) -> int:
    if not isinstance(value, dict):
        return 0
    total = 0
    for group in value.values():
        if isinstance(group, dict):
            total += _mapping_count(group.get("dependencies"))
    return total


def _cargo_has_build_script(payload: dict[str, object]) -> bool:
    package = payload.get("package")
    return isinstance(package, dict) and isinstance(package.get("build"), str)


def _xml_local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


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

"""Produce one separately authorized, bounded Local-v1 O4 evidence journey.

The checked-in authorization is intentionally closed.  The default command therefore refuses
before runtime creation or any Docker, HTTP, provider, credential, Node, or Hermes action.  The
state machine and its external seams are implemented here so one future exact-reviewed candidate
can be authorized without accepting caller-supplied commands, paths, images, tools, or models.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import selectors
import signal
import socket
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, cast

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from ithildin_schemas import JsonObject, canonical_json, sha256_digest

from scripts import local_v1_constrained_mission_journey as assembler_module
from scripts import local_v1_lv1_003_o4_execution_authorization_check as authorization_gate

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_BASE = ROOT / "var/local-v1-lv1-003-o4-runtime"
RECEIPT_BASE = ROOT / "var/local-v1-lv1-003-o4-receipts"
BASE_COMPOSE = ROOT / "deploy/docker-compose.yml"
FIXED_OVERLAY = ROOT / "deploy/hermes-node-bridge/compose.yaml"
PROFILE = ROOT / "deploy/hermes-node-bridge/profile.json"
PROJECT_PREFIX = "ithildin-local-v1-o4-"
MODEL = "gemma4:e4b"
HOST_OLLAMA = "http://127.0.0.1:11434"
NODE_VERSION = "0.1.0"
WORKSPACE_ID = "demo"
LICENSE_INPUTS = ("pyproject.toml", "uv.lock")
MAX_LICENSE_BYTES = 1_048_576
MAX_SNAPSHOT_FILE_BYTES = 16 * 1_048_576
MAX_SNAPSHOT_BYTES = 64 * 1_048_576
NODE_TMPFS = ("/tmp:size=16m,mode=0700,uid=10002,gid=10002",)
MAX_RECOVERY_RECEIPT_BYTES = 4096
MAX_BASE_SERVICE_START_DIAGNOSTIC_BYTES = 1024
MAX_API_CONTAINER_DIAGNOSTIC_BYTES = 512
MAX_FIXED_NODE_START_DIAGNOSTIC_BYTES = 512
MAX_APPLICATION_STARTUP_STAGE_BYTES = 256
MAX_API_CONTAINER_REAP_ATTEMPTS = 3
API_CONTAINER_REAP_TIMEOUT_SECONDS = 0.25
BASE_SERVICE_START_DIAGNOSTIC_FORMAT = (
    "{{.Service}}\t{{.State}}\t{{.Health}}\t{{.ExitCode}}"
)
API_CONTAINER_STATE_FORMAT = (
    "{{.Id}}\t{{index .Config.Labels \"com.docker.compose.project\"}}\t"
    "{{index .Config.Labels \"com.docker.compose.service\"}}\t"
    "{{.State.Status}}\t{{.State.Running}}\t{{.State.ExitCode}}\t"
    "{{.State.OOMKilled}}\t{{.State.Dead}}\t{{ne .State.Error \"\"}}\t"
    "{{if .State.Health}}{{.State.Health.Status}}{{else}}absent{{end}}"
)
FIXED_NODE_CONTAINER_STATE_FORMAT = API_CONTAINER_STATE_FORMAT
APPLICATION_STARTUP_STATUS_DIRECTORY = "startup-status"
APPLICATION_STARTUP_STATUS_FILE = "api-startup-stage.json"
APPLICATION_STARTUP_STAGES = frozenset(
    {
        "launcher_entered",
        "runtime_candidate_verification_entered",
        "application_import_entered",
        "application_factory_entered",
        "server_run_entered",
        "lifespan_configuration_entered",
        "lifespan_persistence_entered",
        "lifespan_governance_entered",
        "lifespan_services_entered",
        "startup_ready",
        "shutdown_entered",
        "shutdown_complete",
    }
)
FIXED_BRIDGE_PHASE_BY_EXIT_CODE = {
    80: "fixed_bridge_entered",
    81: "preclaim_validation_entered",
    82: "mission_claim_entered",
    83: "session_validation_entered",
    84: "receipt_persistence_entered",
    85: "socket_parent_validation_entered",
    86: "socket_bind_entered",
    87: "socket_permissions_entered",
    88: "listener_accept_entered",
}
HERMES_TIMEOUT_SECONDS = 920.0
NODE_SYNCHRONIZATION_SECONDS = 90.0
REVOCATION_RECOVERY_RECEIPT = "node-revocation-recovery.json"
COMPOSE_PLUGIN_EXTRA_DIR = Path(
    "/Applications/Docker.app/Contents/Resources/cli-plugins"
)

_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_RUN_ID = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")
_PROJECT = re.compile(r"^ithildin-local-v1-o4-[0-9a-f]{8}$")
_NODE_ID = re.compile(r"^node_[0-9a-f]{32}$")
_MISSION_ID = re.compile(r"^mission_[0-9a-f]{32}$")
_CLAIM_ID = re.compile(r"^mclaim_[0-9a-f]{32}$")
_RUN_RECORD_ID = re.compile(r"^run_[0-9a-f]{32}$")
_REQUEST_ID = re.compile(r"^req_[0-9a-f]{32}$")
_EVENT_ID = re.compile(r"^evt_[0-9a-f]{32}$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_IMAGE_REFERENCE = re.compile(
    r"^ithildin/(?:api|ui|node|hermes-node-bridge)-o4:[0-9a-f]{8}$"
)
_COMPOSE_VERSION_LABEL = re.compile(r"^[0-9A-Za-z][0-9A-Za-z.+-]{0,31}$")
_ABSENT_IMAGE_ID_STDOUTS = frozenset({"", "\n"})
_CONTAINER_ID = re.compile(r"^[0-9a-f]{64}$")
_AMBIENT_AUTHORITY = re.compile(
    r"^(?:DOCKER_HOST|DOCKER_CONTEXT|DOCKER_CONFIG|COMPOSE_PROJECT_NAME|"
    r"HTTP_PROXY|HTTPS_PROXY|ALL_PROXY|NO_PROXY|AWS_.*|AZURE_.*|GOOGLE_.*|"
    r"GCP_.*|OPENAI_.*|ANTHROPIC_.*|GEMINI_.*|OLLAMA_.*|HERMES_.*|"
    r"REGISTRY_.*|DOCKER_AUTH_CONFIG)$",
    re.IGNORECASE,
)
_FORBIDDEN_OUTPUT = re.compile(
    r"(?:authorization|bearer|credential|private[_ -]?key|prompt|raw[_ -]?output|"
    r"secret|token)",
    re.IGNORECASE,
)
_SNAPSHOT_PREFIXES = (
    "apps/",
    "packages/",
    "policies/",
    "principals/",
    "scripts/",
    "tool-manifests/",
    "trusted-hosts/",
)
_SNAPSHOT_FILES = frozenset(
    {
        ".dockerignore",
        "README.md",
        "deploy/Dockerfile.api",
        "deploy/Dockerfile.node",
        "deploy/Dockerfile.ui",
        "deploy/docker-compose.yml",
        "deploy/hermes-node-bridge/Dockerfile",
        "deploy/hermes-node-bridge/compose.yaml",
        "deploy/hermes-node-bridge/config.yaml",
        "deploy/hermes-node-bridge/fixed-instruction.md",
        "deploy/hermes-node-bridge/profile.json",
        "deploy/nginx.conf",
        "pyproject.toml",
        "tool-manifests.lock.json",
        "uv.lock",
        "workspaces/local.yaml",
    }
)
_SNAPSHOT_REQUIRED = _SNAPSHOT_FILES | frozenset(
    {
        "apps/api/verified_launch.py",
        "apps/mcp-server/src/ithildin_mcp_server/node_bridge.py",
        "apps/node/src/ithildin_node/client.py",
        "apps/node/src/ithildin_node/fixed_runner_bridge.py",
        "apps/node/src/ithildin_node/service.py",
    }
)


class ProducerError(RuntimeError):
    """Stable, redacted producer failure."""

    def __init__(self, code: str) -> None:
        if not re.fullmatch(r"[a-z0-9_]{3,80}", code):
            raise ValueError("unsafe producer error code")
        super().__init__(code)
        self.code = code


class ProducerSignal(BaseException):
    """Internal controlled-interruption marker raised by installed signal handlers."""


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    classification: str = "completed"
    stderr: str = ""


@dataclass(frozen=True)
class HermesResult:
    classification: str
    exit_code: int | None


class Executor(Protocol):
    def bind_image_identity(self, image_id: str) -> None: ...

    def bind_container_identity(self, container_id: str) -> None: ...

    def discard_container_identity(self, container_id: str) -> None: ...

    def run(
        self,
        command: tuple[str, ...],
        *,
        input_text: str | None = None,
        timeout: float = 180.0,
    ) -> CommandResult: ...

    def run_hermes(
        self,
        command: tuple[str, ...],
        *,
        timeout: float,
    ) -> HermesResult: ...


class Api(Protocol):
    def get(self, path: str, *, admin: bool = True) -> JsonObject: ...

    def post(self, path: str, payload: JsonObject) -> JsonObject: ...


class Provider(Protocol):
    def exact_models(self) -> tuple[str, ...]: ...


class Gate(Protocol):
    def authorize(self, commit: str, tree: str) -> None: ...


class Anchor(Protocol):
    def validate(self) -> None: ...


class Assembler(Protocol):
    def assemble(
        self,
        build: JsonObject,
        journey: JsonObject,
        *,
        candidate_commit: str,
        candidate_tree: str,
        receipt_root: PrivateDirectory,
        snapshot: CandidateSnapshot,
    ) -> Path: ...


class RuntimeFactory(Protocol):
    def create(self, run_id: str) -> tuple[PrivateDirectory, PrivateDirectory]: ...


class ExecutorFactory(Protocol):
    def create(self, environment: dict[str, str]) -> Executor: ...


class ApiFactory(Protocol):
    def create(self, admin_token: str) -> Api: ...


@dataclass
class PrivateDirectory:
    """Owner-bound directory with descriptor-relative files and fail-closed removal."""

    base: Path
    name: str
    root_fd: int
    var_fd: int
    base_fd: int
    run_fd: int
    root_identity: tuple[int, int]
    var_identity: tuple[int, int]
    base_identity: tuple[int, int]
    run_identity: tuple[int, int]

    @property
    def path(self) -> Path:
        self.validate()
        return self.base / self.name

    @classmethod
    def create(cls, base: Path, name: str) -> PrivateDirectory:
        if base not in {RUNTIME_BASE, RECEIPT_BASE} or not _RUN_ID.fullmatch(name):
            raise ProducerError("runtime_path_not_confined")
        root_fd = -1
        var_fd = -1
        base_fd = -1
        run_fd = -1
        try:
            root_fd = os.open(ROOT, _directory_flags())
            root_stat = os.fstat(root_fd)
            if not _owned_nonwritable_directory(root_stat):
                raise ProducerError("repository_root_unsafe")
            var_fd = os.open("var", _directory_flags(), dir_fd=root_fd)
            var_stat = os.fstat(var_fd)
            if not _owned_nonwritable_directory(var_stat):
                raise ProducerError("repository_var_unsafe")
            try:
                os.mkdir(base.name, 0o700, dir_fd=var_fd)
            except FileExistsError:
                pass
            base_fd = os.open(base.name, _directory_flags(), dir_fd=var_fd)
            os.fchmod(base_fd, 0o700)
            base_stat = os.fstat(base_fd)
            if not _owner_directory(base_stat):
                raise ProducerError("runtime_base_unsafe")
            os.mkdir(name, 0o700, dir_fd=base_fd)
            run_fd = os.open(name, _directory_flags(), dir_fd=base_fd)
            os.fchmod(run_fd, 0o700)
            run_stat = os.fstat(run_fd)
            if not _owner_directory(run_stat):
                raise ProducerError("runtime_directory_unsafe")
            result = cls(
                base,
                name,
                root_fd,
                var_fd,
                base_fd,
                run_fd,
                (root_stat.st_dev, root_stat.st_ino),
                (var_stat.st_dev, var_stat.st_ino),
                (base_stat.st_dev, base_stat.st_ino),
                (run_stat.st_dev, run_stat.st_ino),
            )
            root_fd = -1
            var_fd = -1
            base_fd = -1
            run_fd = -1
            return result
        except (OSError, ProducerError) as exc:
            if isinstance(exc, ProducerError):
                raise
            raise ProducerError("runtime_directory_create_failed") from exc
        finally:
            if run_fd >= 0:
                os.close(run_fd)
            if base_fd >= 0:
                os.close(base_fd)
            if var_fd >= 0:
                os.close(var_fd)
            if root_fd >= 0:
                os.close(root_fd)

    def validate(self) -> None:
        try:
            root_held = os.fstat(self.root_fd)
            root_current = os.stat(ROOT, follow_symlinks=False)
            var_held = os.fstat(self.var_fd)
            var_current = os.stat("var", dir_fd=self.root_fd, follow_symlinks=False)
            base_held = os.fstat(self.base_fd)
            base_current = os.stat(
                self.base.name,
                dir_fd=self.var_fd,
                follow_symlinks=False,
            )
            run_held = os.fstat(self.run_fd)
            run_current = os.stat(
                self.name,
                dir_fd=self.base_fd,
                follow_symlinks=False,
            )
        except OSError as exc:
            raise ProducerError("runtime_anchor_changed") from exc
        if (
            (root_held.st_dev, root_held.st_ino) != self.root_identity
            or (root_current.st_dev, root_current.st_ino) != self.root_identity
            or (var_held.st_dev, var_held.st_ino) != self.var_identity
            or (var_current.st_dev, var_current.st_ino) != self.var_identity
            or (base_held.st_dev, base_held.st_ino) != self.base_identity
            or (base_current.st_dev, base_current.st_ino) != self.base_identity
            or (run_held.st_dev, run_held.st_ino) != self.run_identity
            or (run_current.st_dev, run_current.st_ino) != self.run_identity
            or not _owned_nonwritable_directory(root_held)
            or not _owned_nonwritable_directory(root_current)
            or not _owned_nonwritable_directory(var_held)
            or not _owned_nonwritable_directory(var_current)
            or not _owner_directory(base_held)
            or not _owner_directory(base_current)
            or not _owner_directory(run_held)
            or not _owner_directory(run_current)
        ):
            raise ProducerError("runtime_anchor_changed")

    def mkdir(self, relative: str) -> None:
        self.validate()
        parts = _relative_parts(relative)
        descriptor = os.dup(self.run_fd)
        try:
            for part in parts:
                try:
                    os.mkdir(part, 0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
                child = os.open(part, _directory_flags(), dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child
                os.fchmod(descriptor, 0o700)
        finally:
            os.close(descriptor)

    def write(self, relative: str, content: bytes, *, mode: int = 0o600) -> None:
        if mode not in {0o400, 0o500, 0o600, 0o700}:
            raise ProducerError("runtime_file_mode_invalid")
        self.validate()
        parent, name = self._parent(relative)
        descriptor = -1
        try:
            descriptor = os.open(
                name,
                _file_flags(os.O_WRONLY | os.O_CREAT | os.O_EXCL),
                mode,
                dir_fd=parent,
            )
            os.fchmod(descriptor, mode)
            view = memoryview(content)
            while view:
                view = view[os.write(descriptor, view) :]
            os.fsync(descriptor)
        except OSError as exc:
            raise ProducerError("runtime_file_write_failed") from exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            os.close(parent)
        self.validate()

    def read(self, relative: str, *, maximum: int = MAX_LICENSE_BYTES) -> bytes:
        self.validate()
        parent, name = self._parent(relative)
        descriptor = -1
        try:
            descriptor = os.open(name, _file_flags(os.O_RDONLY), dir_fd=parent)
            details = os.fstat(descriptor)
            if (
                not stat.S_ISREG(details.st_mode)
                or stat.S_IMODE(details.st_mode) not in {0o400, 0o500, 0o600, 0o700}
                or details.st_uid != os.geteuid()
                or details.st_gid != os.getegid()
            ):
                raise ProducerError("runtime_file_unsafe")
            content = os.read(descriptor, maximum + 1)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            os.close(parent)
        if len(content) > maximum:
            raise ProducerError("runtime_file_too_large")
        return content

    def read_exact_owner_file(
        self,
        directory: str,
        filename: str,
        *,
        maximum: int,
    ) -> bytes | None:
        self.validate()
        directory_fd = -1
        descriptor = -1
        try:
            directory_details = os.stat(
                directory,
                dir_fd=self.run_fd,
                follow_symlinks=False,
            )
            directory_fd = os.open(
                directory,
                _directory_flags(),
                dir_fd=self.run_fd,
            )
            held_directory = os.fstat(directory_fd)
            if (
                (directory_details.st_dev, directory_details.st_ino)
                != (held_directory.st_dev, held_directory.st_ino)
                or not _owner_directory(directory_details)
                or not _owner_directory(held_directory)
            ):
                raise ProducerError("runtime_file_unsafe")
            inventory = sorted(os.listdir(directory_fd))
            if not inventory:
                return None
            if inventory != [filename]:
                raise ProducerError("runtime_file_unsafe")
            lexical = os.stat(
                filename,
                dir_fd=directory_fd,
                follow_symlinks=False,
            )
            if (
                not stat.S_ISREG(lexical.st_mode)
                or stat.S_IMODE(lexical.st_mode) != 0o600
                or lexical.st_uid != os.geteuid()
                or lexical.st_gid != os.getegid()
                or lexical.st_size > maximum
            ):
                raise ProducerError("runtime_file_unsafe")
            descriptor = os.open(
                filename,
                _file_flags(os.O_RDONLY | os.O_NONBLOCK),
                dir_fd=directory_fd,
            )
            held = os.fstat(descriptor)
            if (
                (lexical.st_dev, lexical.st_ino) != (held.st_dev, held.st_ino)
                or not stat.S_ISREG(held.st_mode)
                or stat.S_IMODE(held.st_mode) != 0o600
                or held.st_uid != os.geteuid()
                or held.st_gid != os.getegid()
                or held.st_size > maximum
            ):
                raise ProducerError("runtime_file_unsafe")
            return _read_all(descriptor, maximum)
        except OSError as exc:
            raise ProducerError("runtime_file_unsafe") from exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            if directory_fd >= 0:
                os.close(directory_fd)
            self.validate()

    def file(self, relative: str) -> Path:
        _relative_parts(relative)
        self.validate()
        return self.path / relative

    def remove_tree(self, relative: str) -> bool:
        try:
            self.validate()
            parent, name = self._parent(relative)
            try:
                descriptor = os.open(name, _directory_flags(), dir_fd=parent)
                try:
                    _remove_contents(descriptor)
                finally:
                    os.close(descriptor)
                os.rmdir(name, dir_fd=parent)
            finally:
                os.close(parent)
            self.validate()
            return True
        except (OSError, ProducerError):
            return False

    def remove(self) -> bool:
        try:
            self.validate()
            _remove_contents(self.run_fd)
            self.validate()
            os.rmdir(self.name, dir_fd=self.base_fd)
            self.close()
            return True
        except (OSError, ProducerError):
            return False

    def close(self) -> None:
        if self.run_fd >= 0:
            os.close(self.run_fd)
            self.run_fd = -1
        if self.base_fd >= 0:
            os.close(self.base_fd)
            self.base_fd = -1
        if self.var_fd >= 0:
            os.close(self.var_fd)
            self.var_fd = -1
        if self.root_fd >= 0:
            os.close(self.root_fd)
            self.root_fd = -1

    def _parent(self, relative: str) -> tuple[int, str]:
        parts = _relative_parts(relative)
        descriptor = os.dup(self.run_fd)
        try:
            for part in parts[:-1]:
                child = os.open(part, _directory_flags(), dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child
            return descriptor, parts[-1]
        except BaseException:
            os.close(descriptor)
            raise


@dataclass
class CandidateSnapshot:
    """Descriptor-anchored, content-bound projection of exact Git candidate inputs."""

    root: PrivateDirectory
    candidate_commit: str
    candidate_tree: str
    manifest: dict[str, tuple[int, str]]
    directories: tuple[str, ...]
    snapshot_fd: int
    snapshot_identity: tuple[int, int]

    @property
    def path(self) -> Path:
        self.validate()
        return self.root.file("candidate")

    @classmethod
    def create(
        cls,
        root: PrivateDirectory,
        candidate_commit: str,
        candidate_tree: str,
    ) -> CandidateSnapshot:
        entries = _candidate_snapshot_entries(candidate_commit, candidate_tree)
        directories = sorted(
            {
                str(parent)
                for relative in entries
                for parent in Path(relative).parents
                if str(parent) != "."
            },
            key=lambda value: (len(Path(value).parts), value),
        )
        root.mkdir("candidate")
        for directory in directories:
            root.mkdir(f"candidate/{directory}")
        manifest: dict[str, tuple[int, str]] = {}
        for relative, (mode, content) in entries.items():
            private_mode = 0o500 if mode == 0o100755 else 0o400
            root.write(
                f"candidate/{relative}",
                content,
                mode=private_mode,
            )
            manifest[relative] = (
                private_mode,
                "sha256:" + hashlib.sha256(content).hexdigest(),
            )
        root.write(
            "candidate-manifest.json",
            (
                canonical_json(
                    {
                        "candidate_commit": candidate_commit,
                        "candidate_tree": candidate_tree,
                        "files": {
                            relative: {"mode": mode, "sha256": digest}
                            for relative, (mode, digest) in sorted(manifest.items())
                        },
                    }
                )
                + "\n"
            ).encode(),
        )
        snapshot_fd = os.open("candidate", _directory_flags(), dir_fd=root.run_fd)
        for directory in sorted(
            directories,
            key=lambda value: (len(Path(value).parts), value),
            reverse=True,
        ):
            descriptor = _open_relative_directory(snapshot_fd, directory)
            try:
                os.fchmod(descriptor, 0o500)
            finally:
                os.close(descriptor)
        os.fchmod(snapshot_fd, 0o500)
        details = os.fstat(snapshot_fd)
        result = cls(
            root,
            candidate_commit,
            candidate_tree,
            manifest,
            tuple(directories),
            snapshot_fd,
            (details.st_dev, details.st_ino),
        )
        try:
            result.validate()
        except BaseException:
            result.close()
            raise
        return result

    def validate(self) -> None:
        self.root.validate()
        try:
            held = os.fstat(self.snapshot_fd)
            current = os.stat(
                "candidate",
                dir_fd=self.root.run_fd,
                follow_symlinks=False,
            )
        except OSError as exc:
            raise ProducerError("candidate_snapshot_changed") from exc
        if (
            (held.st_dev, held.st_ino) != self.snapshot_identity
            or (current.st_dev, current.st_ino) != self.snapshot_identity
            or not _owner_snapshot_directory(held)
            or not _owner_snapshot_directory(current)
        ):
            raise ProducerError("candidate_snapshot_changed")
        actual_directories, actual_files = _enumerate_snapshot_tree(self.snapshot_fd)
        if (
            actual_directories != set(self.directories)
            or actual_files != set(self.manifest)
        ):
            raise ProducerError("candidate_snapshot_changed")
        for relative, (expected_mode, expected_digest) in self.manifest.items():
            descriptor = _open_relative_file(self.snapshot_fd, relative)
            try:
                details = os.fstat(descriptor)
                if (
                    not stat.S_ISREG(details.st_mode)
                    or stat.S_IMODE(details.st_mode) != expected_mode
                    or details.st_uid != os.geteuid()
                    or details.st_gid != os.getegid()
                    or details.st_size > MAX_SNAPSHOT_FILE_BYTES
                ):
                    raise ProducerError("candidate_snapshot_changed")
                content = _read_all(descriptor, MAX_SNAPSHOT_FILE_BYTES)
            finally:
                os.close(descriptor)
            if "sha256:" + hashlib.sha256(content).hexdigest() != expected_digest:
                raise ProducerError("candidate_snapshot_changed")

    def read(self, relative: str, *, maximum: int = MAX_LICENSE_BYTES) -> bytes:
        self.validate()
        descriptor = _open_relative_file(self.snapshot_fd, relative)
        try:
            content = _read_all(descriptor, maximum)
        finally:
            os.close(descriptor)
        return content

    def json_object(self, relative: str) -> JsonObject:
        try:
            raw = json.loads(self.read(relative).decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ProducerError("candidate_json_invalid") from exc
        if not isinstance(raw, dict):
            raise ProducerError("candidate_json_invalid")
        return cast(JsonObject, raw)

    def file_digest(self, relative: str) -> str:
        return "sha256:" + hashlib.sha256(
            self.read(relative, maximum=MAX_SNAPSHOT_FILE_BYTES)
        ).hexdigest()

    def source_digest(self, relatives: tuple[str, ...]) -> str:
        material: JsonObject = {
            relative: self.file_digest(relative) for relative in sorted(relatives)
        }
        return sha256_digest(material)

    def source_evidence(self) -> JsonObject:
        return {
            "profile": self.json_object("deploy/hermes-node-bridge/profile.json"),
            "bridge_source_digest": self.source_digest(
                tuple(
                    str(path.relative_to(ROOT))
                    for path in assembler_module.BRIDGE_SOURCE_PATHS
                )
            ),
            "node_source_digest": self.source_digest(
                tuple(
                    str(path.relative_to(ROOT))
                    for path in assembler_module.NODE_SOURCE_PATHS
                )
            ),
            "dependency_lock_digest": self.file_digest("uv.lock"),
            "hermes_config_digest": self.file_digest(
                "deploy/hermes-node-bridge/config.yaml"
            ),
        }

    def close(self) -> None:
        if self.snapshot_fd >= 0:
            os.close(self.snapshot_fd)
            self.snapshot_fd = -1


class DefaultRuntimeFactory:
    def create(self, run_id: str) -> tuple[PrivateDirectory, PrivateDirectory]:
        runtime = PrivateDirectory.create(RUNTIME_BASE, run_id)
        try:
            receipts = PrivateDirectory.create(RECEIPT_BASE, run_id)
        except BaseException:
            removed = runtime.remove()
            runtime.close()
            if not removed:
                raise ProducerError("recovery_required") from None
            raise
        return runtime, receipts


@dataclass(frozen=True)
class ComposePlan:
    run_id: str
    runtime: Path

    @property
    def candidate(self) -> Path:
        return RECEIPT_BASE / self.run_id / "candidate"

    @property
    def suffix(self) -> str:
        return self.run_id[-8:]

    @property
    def project(self) -> str:
        return PROJECT_PREFIX + self.suffix

    @property
    def images(self) -> tuple[str, str, str, str]:
        return tuple(
            f"ithildin/{name}-o4:{self.suffix}"
            for name in ("api", "ui", "node", "hermes-node-bridge")
        )  # type: ignore[return-value]

    def compose(self, *tail: str, fixed: bool = False) -> tuple[str, ...]:
        command = [
            "docker",
            "--config",
            str(self.runtime / "docker-config"),
            "compose",
            "--project-name",
            self.project,
            "--env-file",
            str(self.runtime / "compose.env"),
            "--file",
            str(self.candidate / BASE_COMPOSE.relative_to(ROOT)),
        ]
        if fixed:
            command.extend(
                ("--file", str(self.candidate / FIXED_OVERLAY.relative_to(ROOT)))
            )
        command.extend(("--file", str(self.runtime / "compose.override.yml"), *tail))
        return tuple(command)

    def daemon_version(self) -> tuple[str, ...]:
        return (
            "docker",
            "--config",
            str(self.runtime / "docker-config"),
            "version",
            "--format",
            "{{json .Server.Version}}",
        )

    def compose_version(self) -> tuple[str, ...]:
        return (
            "docker",
            "--config",
            str(self.runtime / "docker-config"),
            "compose",
            "version",
        )

    def resource_query(self, resource: str) -> tuple[str, ...]:
        noun = "ps" if resource == "container" else resource
        prefix = ("docker", "--config", str(self.runtime / "docker-config"), noun)
        project_filter = f"label=com.docker.compose.project={self.project}"
        if resource == "container":
            return (*prefix, "--all", "--quiet", "--filter", project_filter)
        return (*prefix, "ls", "--quiet", "--filter", project_filter)

    def image_query(self, reference: str) -> tuple[str, ...]:
        return (
            "docker", "--config", str(self.runtime / "docker-config"), "image", "ls",
            "--quiet", "--no-trunc", "--filter", f"reference={reference}",
        )

    def image_inspect(self, reference: str) -> tuple[str, ...]:
        return (
            "docker", "--config", str(self.runtime / "docker-config"), "image",
            "inspect", "--format", "{{json .}}", reference,
        )

    def image_remove(self, image_id: str) -> tuple[str, ...]:
        return (
            "docker", "--config", str(self.runtime / "docker-config"), "image",
            "rm", image_id,
        )

    def image_ancestor_containers(self, image_id: str) -> tuple[str, ...]:
        return (
            "docker",
            "--config",
            str(self.runtime / "docker-config"),
            "ps",
            "--all",
            "--quiet",
            "--filter",
            f"ancestor={image_id}",
        )

    def image_id_inspect(self, image_id: str) -> tuple[str, ...]:
        return (
            "docker",
            "--config",
            str(self.runtime / "docker-config"),
            "image",
            "inspect",
            "--format",
            "{{json .Id}}",
            image_id,
        )

    def base_service_start_diagnostic(self) -> tuple[str, ...]:
        return self.compose(
            "ps",
            "--all",
            "--format",
            BASE_SERVICE_START_DIAGNOSTIC_FORMAT,
            "ithildin-api",
            "ithildin-ui",
        )

    def api_container_id_query(self) -> tuple[str, ...]:
        return self.compose("ps", "--all", "--quiet", "ithildin-api")

    def api_container_state_inspect(
        self,
        container_id: str,
    ) -> tuple[str, ...]:
        return (
            "docker",
            "--config",
            str(self.runtime / "docker-config"),
            "container",
            "inspect",
            "--format",
            API_CONTAINER_STATE_FORMAT,
            container_id,
        )

    def fixed_node_container_id_query(self) -> tuple[str, ...]:
        return self.compose(
            "ps",
            "--all",
            "--quiet",
            "ithildin-node",
            fixed=True,
        )

    def fixed_node_container_state_inspect(
        self,
        container_id: str,
    ) -> tuple[str, ...]:
        return (
            "docker",
            "--config",
            str(self.runtime / "docker-config"),
            "container",
            "inspect",
            "--format",
            FIXED_NODE_CONTAINER_STATE_FORMAT,
            container_id,
        )


@dataclass(frozen=True)
class BoundImageIdentity:
    reference: str
    image_id: str
    project: str
    service: str
    compose_version: str
    platform: str
    layers: tuple[str, ...]


@dataclass(frozen=True)
class FixedNodeContainerState:
    status: str
    running: bool
    exit_class: str
    fixed_bridge_last_entered_phase: str
    oom_killed: bool
    dead: bool
    engine_error_present: bool
    health_status: str


@dataclass
class ProducerState:
    candidate_commit: str
    candidate_tree: str
    run_id: str
    plan: ComposePlan
    runtime: PrivateDirectory
    receipts: PrivateDirectory
    snapshot: CandidateSnapshot | None = None
    stages: list[int] = field(default_factory=list)
    node_id: str | None = None
    configuration_generation: int | None = None
    configuration_digest: str | None = None
    mission_id: str | None = None
    hermes_attempts: int = 0
    mutated: bool = False
    docker_preflight_complete: bool = False
    docker_mutation_started: bool = False
    docker_ownership_proven: bool = False
    enrollment_attempted: bool = False
    enrollment_outcome_ambiguous: bool = False
    node_enrolled: bool = False
    enrollment_revocation_confirmed: bool = False
    revocation_recovery_receipt_written: bool = False
    mission_admitted: bool = False
    cleanup_calls: int = 0
    cleanup_failures: list[str] = field(default_factory=list)
    recovery_required: bool = False
    clean_before_node_build: bool = False
    clean_after_node_build: bool = False
    clean_before_bridge_build: bool = False
    clean_after_bridge_build: bool = False
    base_build_completed: bool = False
    bridge_build_completed: bool = False
    base_service_start_diagnostic: JsonObject | None = None
    fixed_node_start_diagnostic: JsonObject | None = None
    fixed_node_start_diagnostic_calls: int = 0
    bound_images: dict[str, BoundImageIdentity] = field(default_factory=dict)
    inspected_images: dict[str, str] = field(default_factory=dict)
    image_platform: str | None = None
    image_inventory: JsonObject | None = None
    license_inventory: JsonObject | None = None
    image_inventory_digest: str | None = None
    license_inventory_digest: str | None = None
    gateway_journey: JsonObject | None = None

    def stage(self, number: int) -> None:
        if number != len(self.stages) + 1:
            raise ProducerError("stage_order_invalid")
        self.stages.append(number)


class ExactGate:
    def authorize(self, commit: str, tree: str) -> None:
        authorization_gate.assert_live_execution_authorized(
            ROOT,
            candidate_commit=commit,
            candidate_tree=tree,
        )


class DefaultExecutorFactory:
    def create(self, environment: dict[str, str]) -> Executor:
        return SubprocessExecutor(environment)


class DefaultApiFactory:
    def create(self, admin_token: str) -> Api:
        return LocalApi(admin_token)


class AnchoredExecutor:
    def __init__(
        self,
        delegate: Executor,
        anchors: tuple[Anchor, ...],
    ) -> None:
        self._delegate = delegate
        self._anchors = anchors

    def bind_image_identity(self, image_id: str) -> None:
        self._validate()
        try:
            self._delegate.bind_image_identity(image_id)
        finally:
            self._validate()

    def bind_container_identity(self, container_id: str) -> None:
        self._validate()
        try:
            self._delegate.bind_container_identity(container_id)
            self._validate()
        except BaseException:
            try:
                self._delegate.discard_container_identity(container_id)
            except BaseException as exc:
                raise ProducerError("container_identity_discard_failed") from exc
            raise

    def discard_container_identity(self, container_id: str) -> None:
        try:
            self._validate()
        except BaseException:
            try:
                self._delegate.discard_container_identity(container_id)
            except BaseException as exc:
                raise ProducerError("container_identity_discard_failed") from exc
            raise
        self._delegate.discard_container_identity(container_id)
        self._validate()

    def run(
        self,
        command: tuple[str, ...],
        *,
        input_text: str | None = None,
        timeout: float = 180.0,
    ) -> CommandResult:
        self._validate()
        try:
            return self._delegate.run(
                command,
                input_text=input_text,
                timeout=timeout,
            )
        finally:
            self._validate()

    def run_hermes(
        self,
        command: tuple[str, ...],
        *,
        timeout: float,
    ) -> HermesResult:
        self._validate()
        try:
            return self._delegate.run_hermes(command, timeout=timeout)
        finally:
            self._validate()

    def _validate(self) -> None:
        for anchor in self._anchors:
            anchor.validate()


class AnchoredApi:
    def __init__(
        self,
        delegate: Api,
        anchors: tuple[Anchor, ...],
    ) -> None:
        self._delegate = delegate
        self._anchors = anchors

    def get(self, path: str, *, admin: bool = True) -> JsonObject:
        self._validate()
        try:
            return self._delegate.get(path, admin=admin)
        finally:
            self._validate()

    def post(self, path: str, payload: JsonObject) -> JsonObject:
        self._validate()
        try:
            return self._delegate.post(path, payload)
        finally:
            self._validate()

    def _validate(self) -> None:
        for anchor in self._anchors:
            anchor.validate()


class AnchoredProvider:
    def __init__(
        self,
        delegate: Provider,
        anchors: tuple[Anchor, ...],
    ) -> None:
        self._delegate = delegate
        self._anchors = anchors

    def exact_models(self) -> tuple[str, ...]:
        for anchor in self._anchors:
            anchor.validate()
        try:
            return self._delegate.exact_models()
        finally:
            for anchor in self._anchors:
                anchor.validate()


class AnchoredAssembler:
    def __init__(
        self,
        delegate: Assembler,
        receipt_anchor: PrivateDirectory,
        snapshot_anchor: CandidateSnapshot,
    ) -> None:
        self._delegate = delegate
        self._receipt_anchor = receipt_anchor
        self._snapshot_anchor = snapshot_anchor

    def assemble(
        self,
        build: JsonObject,
        journey: JsonObject,
        *,
        candidate_commit: str,
        candidate_tree: str,
        receipt_root: PrivateDirectory,
        snapshot: CandidateSnapshot,
    ) -> Path:
        if snapshot is not self._snapshot_anchor:
            raise ProducerError("assembler_snapshot_anchor_invalid")
        if receipt_root is not self._receipt_anchor:
            raise ProducerError("assembler_receipt_anchor_invalid")
        receipt_root.validate()
        self._snapshot_anchor.validate()
        try:
            return self._delegate.assemble(
                build,
                journey,
                candidate_commit=candidate_commit,
                candidate_tree=candidate_tree,
                receipt_root=receipt_root,
                snapshot=snapshot,
            )
        finally:
            receipt_root.validate()
            self._snapshot_anchor.validate()


class SubprocessExecutor:
    """Closed subprocess adapter; Hermes streams are discarded at process creation."""

    def __init__(self, environment: dict[str, str]) -> None:
        self._environment = dict(environment)
        self._bound_image_ids: set[str] = set()
        self._bound_container_ids: set[str] = set()

    def bind_image_identity(self, image_id: str) -> None:
        if not _DIGEST.fullmatch(image_id):
            raise ProducerError("image_identity_binding_invalid")
        self._bound_image_ids.add(image_id)

    def bind_container_identity(self, container_id: str) -> None:
        if not _CONTAINER_ID.fullmatch(container_id):
            raise ProducerError("container_identity_binding_invalid")
        self._bound_container_ids.add(container_id)

    def discard_container_identity(self, container_id: str) -> None:
        if not _CONTAINER_ID.fullmatch(container_id):
            raise ProducerError("container_identity_binding_invalid")
        self._bound_container_ids.discard(container_id)

    def run(
        self,
        command: tuple[str, ...],
        *,
        input_text: str | None = None,
        timeout: float = 180.0,
    ) -> CommandResult:
        _validate_command(
            command,
            hermes=False,
            inspected_image_ids=frozenset(self._bound_image_ids),
            bound_container_ids=frozenset(self._bound_container_ids),
        )
        is_id_probe = (
            len(command) == 8
            and command[3:7]
            == ("image", "inspect", "--format", "{{json .Id}}")
            and _DIGEST.fullmatch(command[7]) is not None
        )
        config_runtime = Path(command[2]).parent
        command_plan = ComposePlan(config_runtime.name, config_runtime)
        is_base_start_diagnostic = (
            command == command_plan.base_service_start_diagnostic()
        )
        is_api_container_diagnostic = (
            command == command_plan.api_container_id_query()
            or command
            in {
                command_plan.api_container_state_inspect(container_id)
                for container_id in self._bound_container_ids
            }
        )
        is_fixed_node_container_diagnostic = (
            command == command_plan.fixed_node_container_id_query()
            or command
            in {
                command_plan.fixed_node_container_state_inspect(container_id)
                for container_id in self._bound_container_ids
            }
        )
        if is_api_container_diagnostic or is_fixed_node_container_diagnostic:
            return self._run_bounded_api_container_diagnostic(
                command,
                timeout=timeout,
            )
        try:
            input_bytes = (
                None
                if input_text is None
                else input_text.encode("utf-8", errors="strict")
            )
        except UnicodeError as exc:
            raise ProducerError("subprocess_input_rejected") from exc
        try:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                input=input_bytes,
                stdout=subprocess.PIPE,
                stderr=(
                    subprocess.PIPE
                    if is_id_probe or is_base_start_diagnostic
                    else subprocess.DEVNULL
                ),
                check=False,
                timeout=timeout,
                env=self._environment,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ProducerError("subprocess_unavailable") from exc
        if len(completed.stdout) > MAX_LICENSE_BYTES:
            raise ProducerError("subprocess_output_too_large")
        try:
            stdout = completed.stdout.decode("utf-8", errors="strict")
            stderr = (
                completed.stderr.decode("utf-8", errors="strict")
                if completed.stderr
                else ""
            )
        except UnicodeError as exc:
            raise ProducerError("subprocess_output_rejected") from exc
        classification = "completed"
        if is_id_probe and completed.returncode != 0:
            messages = {
                f"Error response from daemon: No such image: {command[7]}",
                f"Error: No such image: {command[7]}",
            }
            expected = messages | {message + "\n" for message in messages}
            classification = (
                "image_not_found"
                if completed.returncode == 1
                and stdout in _ABSENT_IMAGE_ID_STDOUTS
                and stderr in expected
                else "error"
            )
        return CommandResult(
            completed.returncode,
            stdout,
            classification,
            stderr if is_base_start_diagnostic else "",
        )

    def _run_bounded_api_container_diagnostic(
        self,
        command: tuple[str, ...],
        *,
        timeout: float,
    ) -> CommandResult:
        process: subprocess.Popen[bytes] | None = None
        selector = selectors.DefaultSelector()
        streams: dict[str, bytearray] = {
            "stdout": bytearray(),
            "stderr": bytearray(),
        }
        try:
            process = subprocess.Popen(
                command,
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self._environment,
            )
            if process.stdout is None or process.stderr is None:
                raise ProducerError("subprocess_unavailable")
            selector.register(process.stdout, selectors.EVENT_READ, "stdout")
            selector.register(process.stderr, selectors.EVENT_READ, "stderr")
            deadline = time.monotonic() + min(timeout, 10.0)
            total = 0
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    process.kill()
                    process.wait()
                    return CommandResult(1, "", "timeout")
                events = selector.select(remaining)
                if not events:
                    if process.poll() is None:
                        continue
                    break
                for key, _ in events:
                    maximum = (
                        MAX_API_CONTAINER_DIAGNOSTIC_BYTES + 1 - total
                    )
                    chunk = os.read(key.fd, max(1, maximum))
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    streams[cast(str, key.data)].extend(chunk)
                    total += len(chunk)
                    if total > MAX_API_CONTAINER_DIAGNOSTIC_BYTES:
                        process.kill()
                        process.wait()
                        return CommandResult(1, "", "output_rejected")
            returncode = process.wait(
                timeout=max(0.0, deadline - time.monotonic())
            )
            try:
                stdout = streams["stdout"].decode("utf-8", errors="strict")
                stderr = streams["stderr"].decode("utf-8", errors="strict")
            except UnicodeError:
                return CommandResult(1, "", "output_rejected")
            return CommandResult(returncode, stdout, "completed", stderr)
        except subprocess.TimeoutExpired:
            if process is not None:
                process.kill()
                process.wait()
            return CommandResult(1, "", "timeout")
        except OSError as exc:
            if process is not None and process.poll() is None:
                process.kill()
                process.wait()
            raise ProducerError("subprocess_unavailable") from exc
        finally:
            unwinding = sys.exc_info()[1] is not None
            process_reaped = True
            cleanup_interrupt: BaseException | None = None
            if process is not None:
                process_reaped, cleanup_interrupt = (
                    self._terminate_and_reap_active_process(process)
                )
            try:
                selector.close()
            except (KeyboardInterrupt, ProducerSignal) as exc:
                if cleanup_interrupt is None:
                    cleanup_interrupt = exc
            except (OSError, ValueError):
                pass
            if process is not None:
                if process.stdout is not None:
                    try:
                        process.stdout.close()
                    except (KeyboardInterrupt, ProducerSignal) as exc:
                        if cleanup_interrupt is None:
                            cleanup_interrupt = exc
                    except OSError:
                        pass
                if process.stderr is not None:
                    try:
                        process.stderr.close()
                    except (KeyboardInterrupt, ProducerSignal) as exc:
                        if cleanup_interrupt is None:
                            cleanup_interrupt = exc
                    except OSError:
                        pass
            if not unwinding and cleanup_interrupt is not None:
                raise cleanup_interrupt
            if not unwinding and not process_reaped:
                raise ProducerError("subprocess_cleanup_unconfirmed")

    @staticmethod
    def _terminate_and_reap_active_process(
        process: subprocess.Popen[bytes],
    ) -> tuple[bool, BaseException | None]:
        cleanup_interrupt: BaseException | None = None

        def remember_interrupt(exc: BaseException) -> None:
            nonlocal cleanup_interrupt
            if cleanup_interrupt is None:
                cleanup_interrupt = exc

        try:
            if process.poll() is not None:
                return True, cleanup_interrupt
        except (KeyboardInterrupt, ProducerSignal) as exc:
            remember_interrupt(exc)
        except OSError:
            pass
        for _ in range(MAX_API_CONTAINER_REAP_ATTEMPTS):
            try:
                process.kill()
            except (KeyboardInterrupt, ProducerSignal) as exc:
                remember_interrupt(exc)
            except OSError:
                pass
            try:
                process.wait(timeout=API_CONTAINER_REAP_TIMEOUT_SECONDS)
                return True, cleanup_interrupt
            except (KeyboardInterrupt, ProducerSignal) as exc:
                remember_interrupt(exc)
            except (OSError, subprocess.TimeoutExpired):
                pass
            try:
                if process.poll() is not None:
                    return True, cleanup_interrupt
            except (KeyboardInterrupt, ProducerSignal) as exc:
                remember_interrupt(exc)
            except OSError:
                pass
        return False, cleanup_interrupt

    def run_hermes(
        self,
        command: tuple[str, ...],
        *,
        timeout: float,
    ) -> HermesResult:
        _validate_command(command, hermes=True)
        try:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=timeout,
                env=self._environment,
            )
        except subprocess.TimeoutExpired:
            return HermesResult("timeout", None)
        except KeyboardInterrupt:
            return HermesResult("interruption", None)
        except OSError as exc:
            raise ProducerError("hermes_subprocess_unavailable") from exc
        return HermesResult("exit", completed.returncode)


class HostOllamaProvider:
    """Proxy-free host-only model inventory; container routing is never inferred."""

    def exact_models(self) -> tuple[str, ...]:
        request = urllib.request.Request(
            f"{HOST_OLLAMA}/api/tags",
            method="GET",
            headers={"Accept": "application/json"},
        )
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            _DenyRedirect(),
        )
        try:
            with opener.open(request, timeout=5.0) as response:
                content = response.read(MAX_LICENSE_BYTES + 1)
        except (OSError, urllib.error.URLError) as exc:
            raise ProducerError("host_provider_unreachable") from exc
        if len(content) > MAX_LICENSE_BYTES:
            raise ProducerError("host_provider_response_too_large")
        try:
            document = json.loads(content)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ProducerError("host_provider_inventory_invalid") from exc
        if not isinstance(document, dict) or set(document) != {"models"}:
            raise ProducerError("host_provider_inventory_invalid")
        models = document["models"]
        if not isinstance(models, list):
            raise ProducerError("host_provider_inventory_invalid")
        names: list[str] = []
        for entry in models:
            if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
                raise ProducerError("host_provider_inventory_invalid")
            names.append(cast(str, entry["name"]))
        return tuple(names)


class LocalApi:
    """Closed local API adapter with no redirects, proxies, or response text in errors."""

    def __init__(self, admin_token: str) -> None:
        self._admin_token = admin_token
        self._opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            _DenyRedirect(),
        )

    def get(self, path: str, *, admin: bool = True) -> JsonObject:
        return self._request("GET", path, None, admin=admin)

    def post(self, path: str, payload: JsonObject) -> JsonObject:
        _validate_api_operation("POST", path, payload, admin=True)
        return self._request("POST", path, payload, admin=True)

    def _request(
        self,
        method: str,
        path: str,
        payload: JsonObject | None,
        *,
        admin: bool,
    ) -> JsonObject:
        _validate_api_operation(method, path, payload, admin=admin)
        headers = {"Accept": "application/json"}
        if admin:
            headers["Authorization"] = f"Bearer {self._admin_token}"
        body = None if payload is None else canonical_json(payload).encode()
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            f"http://127.0.0.1:8000{path}",
            data=body,
            method=method,
            headers=headers,
        )
        try:
            with self._opener.open(request, timeout=5.0) as response:
                content = response.read(MAX_LICENSE_BYTES + 1)
        except (OSError, urllib.error.URLError) as exc:
            raise ProducerError("gateway_request_failed") from exc
        if len(content) > MAX_LICENSE_BYTES:
            raise ProducerError("gateway_response_too_large")
        try:
            document = json.loads(content)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ProducerError("gateway_response_invalid") from exc
        if not isinstance(document, dict):
            raise ProducerError("gateway_response_invalid")
        return cast(JsonObject, document)


class ClosedAssembler:
    def assemble(
        self,
        build: JsonObject,
        journey: JsonObject,
        *,
        candidate_commit: str,
        candidate_tree: str,
        receipt_root: PrivateDirectory,
        snapshot: CandidateSnapshot,
    ) -> Path:
        _validate_inventory_documents(build, receipt_root)
        receipt_root.write("build-receipt.json", canonical_json(build).encode())
        receipt_root.write("journey-receipt.json", canonical_json(journey).encode())
        source_evidence = snapshot.source_evidence()
        snapshot.validate()
        report = assembler_module.build_report(
            build,
            journey,
            expected_candidate=candidate_commit,
            expected_tree=candidate_tree,
            source_evidence=source_evidence,
        )
        checked = _check_report_documents(
            canonical_json(report),
            assembler_module.render_markdown(report),
            expected_candidate=candidate_commit,
            source_evidence=source_evidence,
        )
        snapshot.validate()
        if checked != report:
            raise ProducerError("assembler_checker_disagrees")
        receipt_root.write(
            "disposition.json",
            (
                canonical_json(
                    {
                        "status": "verified_staged_for_atomic_publication",
                        "candidate_commit": candidate_commit,
                        "candidate_tree": candidate_tree,
                        "run_id": report["run_id"],
                        "release_allowed": False,
                        "uat_complete": False,
                    }
                )
                + "\n"
            ).encode(),
        )
        return _publish_report_atomic(report, receipt_root)


def _check_report_documents(
    json_text: str,
    markdown_text: str,
    *,
    expected_candidate: str,
    source_evidence: JsonObject,
) -> JsonObject:
    try:
        raw = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ProducerError("assembler_checker_disagrees") from exc
    if not isinstance(raw, dict):
        raise ProducerError("assembler_checker_disagrees")
    report = cast(JsonObject, raw)
    assembler_module.validate_report(
        report,
        expected_candidate=expected_candidate,
        source_evidence=source_evidence,
    )
    if (
        json_text != canonical_json(report)
        or markdown_text != assembler_module.render_markdown(report)
    ):
        raise ProducerError("assembler_checker_disagrees")
    return report


def _publish_report_atomic(
    report: JsonObject,
    receipt_root: PrivateDirectory,
) -> Path:
    run_id = report.get("run_id")
    if not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id):
        raise ProducerError("report_run_id_invalid")
    base_name = assembler_module.REPORT_BASE.name
    temporary = f".{run_id}.staging-{secrets.token_hex(4)}"
    base_fd = -1
    staging_fd = -1
    renamed = False
    base_identity: tuple[int, int] | None = None
    try:
        try:
            os.mkdir(base_name, 0o700, dir_fd=receipt_root.var_fd)
        except FileExistsError:
            pass
        base_fd = os.open(base_name, _directory_flags(), dir_fd=receipt_root.var_fd)
        os.fchmod(base_fd, 0o700)
        base_details = os.fstat(base_fd)
        if not _owner_directory(base_details):
            raise ProducerError("report_base_unsafe")
        base_identity = (base_details.st_dev, base_details.st_ino)
        try:
            os.stat(run_id, dir_fd=base_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise ProducerError("report_run_already_exists")
        os.mkdir(temporary, 0o700, dir_fd=base_fd)
        staging_fd = os.open(temporary, _directory_flags(), dir_fd=base_fd)
        _write_private_at(
            staging_fd,
            assembler_module.REPORT_JSON,
            canonical_json(report).encode(),
        )
        _write_private_at(
            staging_fd,
            assembler_module.REPORT_MARKDOWN,
            assembler_module.render_markdown(report).encode(),
        )
        os.fsync(staging_fd)
        os.rename(temporary, run_id, src_dir_fd=base_fd, dst_dir_fd=base_fd)
        renamed = True
        published_details = os.fstat(staging_fd)
        named_details = os.stat(run_id, dir_fd=base_fd, follow_symlinks=False)
        if (
            not _owner_directory(published_details)
            or (named_details.st_dev, named_details.st_ino)
            != (published_details.st_dev, published_details.st_ino)
        ):
            raise ProducerError("report_publication_identity_invalid")
        os.fsync(base_fd)
        receipt_root.validate()
        current_base = os.stat(
            base_name,
            dir_fd=receipt_root.var_fd,
            follow_symlinks=False,
        )
        lexical_base = os.stat(
            assembler_module.REPORT_BASE,
            follow_symlinks=False,
        )
        lexical_run = os.stat(
            assembler_module.REPORT_BASE / run_id,
            follow_symlinks=False,
        )
        if (
            base_identity is None
            or (current_base.st_dev, current_base.st_ino) != base_identity
            or (lexical_base.st_dev, lexical_base.st_ino) != base_identity
            or (lexical_run.st_dev, lexical_run.st_ino)
            != (published_details.st_dev, published_details.st_ino)
        ):
            raise ProducerError("report_base_anchor_changed")
    except (OSError, ProducerError, KeyboardInterrupt, ProducerSignal) as exc:
        rollback_failed = False
        if staging_fd >= 0:
            if renamed:
                rollback_failed = not _rollback_published_report(
                    base_fd,
                    run_id,
                    staging_fd,
                )
            else:
                try:
                    _remove_contents(staging_fd)
                except OSError:
                    pass
        if base_fd >= 0:
            if not renamed:
                try:
                    os.rmdir(temporary, dir_fd=base_fd)
                except OSError:
                    pass
        if rollback_failed:
            raise ProducerError("report_publication_recovery_required") from None
        if isinstance(exc, ProducerError):
            raise
        if isinstance(exc, (KeyboardInterrupt, ProducerSignal)):
            raise
        raise ProducerError("report_atomic_publication_failed") from exc
    finally:
        if staging_fd >= 0:
            os.close(staging_fd)
        if base_fd >= 0:
            os.close(base_fd)
    return assembler_module.REPORT_BASE / run_id


def _rollback_published_report(
    base_fd: int,
    run_id: str,
    published_fd: int,
) -> bool:
    try:
        _remove_contents(published_fd)
        os.rmdir(run_id, dir_fd=base_fd)
    except (OSError, KeyboardInterrupt, ProducerSignal):
        quarantine = f".{run_id}.quarantined-{secrets.token_hex(4)}"
        try:
            os.rename(run_id, quarantine, src_dir_fd=base_fd, dst_dir_fd=base_fd)
        except (OSError, KeyboardInterrupt, ProducerSignal):
            return False
    try:
        os.fsync(base_fd)
    except (OSError, KeyboardInterrupt, ProducerSignal):
        return False
    return True


def _validate_inventory_documents(
    build: JsonObject,
    receipt_root: PrivateDirectory,
) -> None:
    image_document = _decode_canonical_private_json(
        receipt_root,
        "image-artifact-inventory.json",
    )
    license_document = _decode_canonical_private_json(
        receipt_root,
        "license-source-inventory.json",
    )
    if (
        sha256_digest(image_document)
        != build.get("image_artifact_inventory_digest")
        or sha256_digest(license_document)
        != build.get("license_source_inventory_digest")
    ):
        raise ProducerError("inventory_digest_binding_invalid")
    images = image_document.get("images")
    if not isinstance(images, list) or len(images) != 4:
        raise ProducerError("image_inventory_shape_invalid")
    platforms: set[str] = set()
    references: set[str] = set()
    image_names: set[str] = set()
    image_suffixes: set[str] = set()
    records: dict[str, JsonObject] = {}
    for raw in images:
        if (
            not isinstance(raw, dict)
            or set(raw)
            != {
                "reference",
                "image_id",
                "platform",
                "config_digest",
                "ordered_layer_digests",
            }
        ):
            raise ProducerError("image_inventory_shape_invalid")
        record = raw
        reference = record.get("reference")
        platform = record.get("platform")
        image_id = record.get("image_id")
        config_digest = record.get("config_digest")
        layers = record.get("ordered_layer_digests")
        if (
            not isinstance(reference, str)
            or not _IMAGE_REFERENCE.fullmatch(reference)
            or platform not in {"linux/amd64", "linux/arm64"}
            or not isinstance(image_id, str)
            or not _DIGEST.fullmatch(image_id)
            or config_digest != image_id
            or not isinstance(layers, list)
            or not layers
            or any(
                not isinstance(layer, str) or not _DIGEST.fullmatch(layer)
                for layer in layers
            )
        ):
            raise ProducerError("image_inventory_shape_invalid")
        image_name, image_suffix = reference.rsplit(":", 1)
        references.add(reference)
        image_names.add(image_name)
        image_suffixes.add(image_suffix)
        platforms.add(platform)
        records[reference] = record
    if (
        len(references) != 4
        or image_names
        != {
            "ithildin/api-o4",
            "ithildin/ui-o4",
            "ithildin/node-o4",
            "ithildin/hermes-node-bridge-o4",
        }
        or len(image_suffixes) != 1
        or len(platforms) != 1
    ):
        raise ProducerError("image_inventory_platform_invalid")
    platform = next(iter(platforms))
    bridge = next(
        (
            record
            for reference, record in records.items()
            if "/hermes-node-bridge-o4:" in reference
        ),
        None,
    )
    node = next(
        (
            record
            for reference, record in records.items()
            if "/node-o4:" in reference
        ),
        None,
    )
    if (
        bridge is None
        or node is None
        or build.get("platform") != platform
        or build.get("bridge_image_digest") != bridge.get("image_id")
        or build.get("node_image_digest") != node.get("image_id")
    ):
        raise ProducerError("image_inventory_receipt_binding_invalid")


def _decode_canonical_private_json(
    receipt_root: PrivateDirectory,
    relative: str,
) -> JsonObject:
    content = receipt_root.read(relative)
    try:
        raw = json.loads(content)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ProducerError("inventory_document_invalid") from exc
    if not isinstance(raw, dict):
        raise ProducerError("inventory_document_invalid")
    document = cast(JsonObject, raw)
    if content != canonical_json(document).encode():
        raise ProducerError("inventory_document_not_canonical")
    return document


class _DenyRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        del req, fp, code, msg, headers, newurl
        raise ProducerError("redirect_not_allowed")


def run_producer(
    *,
    gate: Gate,
    runtime_factory: RuntimeFactory,
    executor_factory: ExecutorFactory,
    api_factory: ApiFactory,
    provider: Provider,
    assembler: Assembler,
    candidate: tuple[str, str],
    environment: dict[str, str] | None = None,
    now: datetime | None = None,
) -> Path:
    """Run the exact state machine through injected, independently fakeable seams."""

    commit, tree = candidate
    if not _COMMIT.fullmatch(commit) or not _COMMIT.fullmatch(tree):
        raise ProducerError("candidate_identity_invalid")
    # The gate is deliberately first.  Refusal has no runtime/executor/API/provider calls.
    gate.authorize(commit, tree)
    _reject_ambient_authority(environment if environment is not None else dict(os.environ))

    observed = (now or datetime.now(UTC)).astimezone(UTC)
    run_id = observed.strftime("%Y%m%dT%H%M%SZ") + f"-{secrets.token_hex(4)}"
    runtime, receipts = runtime_factory.create(run_id)
    state: ProducerState | None = None
    enrollment_code: str | None = None
    report_root: Path | None = None
    primary_error: BaseException | None = None
    primary_failure_code: str | None = None
    executor: Executor | None = None
    api: Api | None = None
    snapshot: CandidateSnapshot | None = None
    try:
        plan = ComposePlan(run_id, runtime.path)
        state = ProducerState(commit, tree, run_id, plan, runtime, receipts)
        try:
            state.stage(1)
            state.stage(2)
            state.stage(3)
            admin_token = secrets.token_urlsafe(48)
            _observe_exact_source(state)
            snapshot = _create_candidate_snapshot(receipts, commit, tree)
            state.snapshot = snapshot
            _prepare_runtime(state, admin_token)
            isolated_environment = {
                "PATH": (environment if environment is not None else os.environ).get(
                    "PATH", "/usr/bin:/bin"
                ),
                "DOCKER_HOST": _prove_local_docker_socket(),
                "DOCKER_CONFIG": str(runtime.path / "docker-config"),
            }
            anchors: tuple[Anchor, ...] = (runtime, receipts, snapshot)
            executor = AnchoredExecutor(
                executor_factory.create(isolated_environment),
                anchors,
            )
            api = AnchoredApi(api_factory.create(admin_token), anchors)
            guarded_provider = AnchoredProvider(provider, anchors)
            state.stage(4)
            _preflight(state, executor, guarded_provider)
            state.docker_preflight_complete = True
            state.stage(5)
            _build_images(state, executor)
            state.stage(6)
            state.image_inventory = _image_inventory(state, executor)
            state.image_inventory_digest = sha256_digest(state.image_inventory)
            state.license_inventory = _license_source_inventory(state)
            state.license_inventory_digest = sha256_digest(state.license_inventory)
            state.stage(7)

            enrollment_code = _start_and_enroll(state, executor, api)
            state.stage(8)
            _prove_node_eligibility(state, api)
            state.stage(9)
            _admit_mission(state, api)
            state.stage(10)
            _require_success(
                executor.run(plan.compose("--profile", "node", "stop", "ithildin-node")),
                "ordinary_node_stop_failed",
            )
            state.stage(11)
            fixed_node_start = executor.run(
                plan.compose(
                    "--profile",
                    "node",
                    "up",
                    "--detach",
                    "--no-deps",
                    "--wait",
                    "ithildin-node",
                    fixed=True,
                )
            )
            if fixed_node_start.returncode != 0:
                try:
                    state.fixed_node_start_diagnostic = (
                        _collect_fixed_node_start_diagnostic(
                            state,
                            executor,
                            api,
                        )
                    )
                except BaseException:
                    state.fixed_node_start_diagnostic = (
                        _fixed_node_start_fallback(
                            collection_status="inconclusive",
                            collection_reason_code=(
                                "fixed_node_start_diagnostic_internal_failure"
                            ),
                        )
                    )
                raise ProducerError("fixed_node_start_failed")
            _require_success(fixed_node_start, "fixed_node_start_failed")
            state.stage(12)
            state.hermes_attempts += 1
            if state.hermes_attempts != 1:
                raise ProducerError("hermes_attempt_budget_exceeded")
            hermes = executor.run_hermes(
                plan.compose(
                    "--profile",
                    "hermes-node-bridge",
                    "run",
                    "--rm",
                    "-T",
                    "--no-deps",
                    "hermes",
                    fixed=True,
                ),
                timeout=HERMES_TIMEOUT_SECONDS,
            )
            if hermes.classification != "exit" or hermes.exit_code != 0:
                raise ProducerError(f"hermes_{hermes.classification}_failed")
            state.stage(13)
            state.gateway_journey = _gateway_journey(state, api)
            state.stage(14)
            _bind_node_receipt(state, executor)
            state.stage(15)
        except BaseException as exc:
            primary_error = exc
            primary_failure_code = _normalized_error(exc).code
        finally:
            if _cleanup_once(state, executor, api) is None:
                primary_error = ProducerError("recovery_required")

        if primary_error is not None:
            raise _normalized_error(primary_error)

        state.stage(16)
        _observe_exact_source(state)
        if state.gateway_journey is None or snapshot is None:
            raise ProducerError("gateway_journey_missing")
        if enrollment_code is not None:
            enrollment_code = None
        build = _build_receipt(state)
        receipts.write(
            "image-artifact-inventory.json",
            canonical_json(cast(JsonObject, state.image_inventory)).encode(),
        )
        receipts.write(
            "license-source-inventory.json",
            canonical_json(cast(JsonObject, state.license_inventory)).encode(),
        )
        report_root = AnchoredAssembler(assembler, receipts, snapshot).assemble(
            build,
            state.gateway_journey,
            candidate_commit=commit,
            candidate_tree=tree,
            receipt_root=receipts,
            snapshot=snapshot,
        )
        state.stage(17)
        return report_root
    except BaseException as exc:
        normalized = _normalized_error(exc)
        if (
            primary_failure_code is None
            and normalized.code != "recovery_required"
        ):
            primary_failure_code = normalized.code
        if state is None:
            if not runtime.remove():
                normalized = ProducerError("recovery_required")
        elif state.cleanup_calls == 0 and _cleanup_once(state, executor, api) is None:
            normalized = ProducerError("recovery_required")
        _write_failure_diagnostic(
            receipts,
            state=state,
            outward_failure_code=normalized.code,
            primary_failure_code=primary_failure_code,
        )
        _quarantine_receipts(receipts, normalized.code)
        raise normalized from None
    finally:
        if snapshot is not None:
            snapshot.close()
        runtime.close()
        receipts.close()


def _prepare_runtime(state: ProducerState, admin_token: str) -> None:
    if state.snapshot is None:
        raise ProducerError("candidate_snapshot_unavailable")
    for relative in (
        "docker-config",
        "var/db",
        "var/logs",
        "var/keys",
        "workspaces",
        "authority",
        "copied-receipt",
        "empty-scripts",
        APPLICATION_STARTUP_STATUS_DIRECTORY,
    ):
        state.runtime.mkdir(relative)
    docker_config: JsonObject = {"auths": {}, "credHelpers": {}}
    if _verified_compose_plugin_dir(COMPOSE_PLUGIN_EXTRA_DIR):
        docker_config["cliPluginsExtraDirs"] = [str(COMPOSE_PLUGIN_EXTRA_DIR)]
    state.runtime.write(
        "docker-config/config.json",
        (canonical_json(docker_config) + "\n").encode(),
    )
    state.runtime.write(
        "compose.env",
        (
            f"ITHILDIN_ADMIN_TOKEN={admin_token}\n"
            "ITHILDIN_ALLOW_DEV_ADMIN_TOKEN=false\n"
            "ITHILDIN_STORAGE_BACKEND=sqlite\n"
            "ITHILDIN_POSTGRES_DSN=\n"
            f"ITHILDIN_CONTAINER_UID={os.geteuid()}\n"
            f"ITHILDIN_CONTAINER_GID={os.getegid()}\n"
            "ITHILDIN_NODE_RUNNER_ADAPTER=hermes\n"
        ).encode(),
    )
    state.runtime.write("authority/api-candidate.json", b"{}\n")
    signer = Ed25519PrivateKey.generate()
    state.runtime.write(
        "var/keys/node-configuration-ed25519-private.pem",
        signer.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ),
    )
    state.runtime.write(
        "var/keys/node-configuration-ed25519-public.pem",
        signer.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ),
    )
    workspace_registry = state.snapshot.read("workspaces/local.yaml")
    if len(workspace_registry) > MAX_LICENSE_BYTES:
        raise ProducerError("workspace_registry_too_large")
    state.runtime.write("workspaces/local.yaml", workspace_registry)
    state.runtime.write(
        "compose.override.yml",
        _compose_override(state).encode(),
    )


def _verified_compose_plugin_dir(candidate: Path) -> bool:
    try:
        directory = candidate.lstat()
    except OSError:
        return False
    plugin = candidate / "docker-compose"
    try:
        executable = plugin.lstat()
    except OSError as exc:
        raise ProducerError("compose_plugin_directory_invalid") from exc
    if (
        candidate != COMPOSE_PLUGIN_EXTRA_DIR
        or candidate.is_symlink()
        or not stat.S_ISDIR(directory.st_mode)
        or directory.st_mode & 0o022
        or plugin.is_symlink()
        or not stat.S_ISREG(executable.st_mode)
        or executable.st_mode & 0o022
        or executable.st_mode & 0o111 == 0
        or not os.access(plugin, os.X_OK)
    ):
        raise ProducerError("compose_plugin_directory_invalid")
    return True


def _preflight(state: ProducerState, executor: Executor, provider: Provider) -> None:
    if state.snapshot is None:
        raise ProducerError("candidate_snapshot_unavailable")
    _require_ports_available((8000, 5173))
    state.snapshot.validate()
    _require_success(executor.run(state.plan.daemon_version()), "docker_daemon_unavailable")
    _require_success(executor.run(state.plan.compose_version()), "compose_plugin_unavailable")
    _require_success(
        executor.run(state.plan.compose("--profile", "node", "config", "--quiet")),
        "base_compose_invalid",
    )
    _require_success(
        executor.run(
            state.plan.compose(
                "--profile",
                "node",
                "--profile",
                "hermes-node-bridge",
                "config",
                "--quiet",
                fixed=True,
            )
        ),
        "fixed_compose_invalid",
    )
    _validate_merged_compose_config(
        executor.run(
            state.plan.compose(
                "--profile",
                "node",
                "config",
                "--no-interpolate",
                "--format",
                "json",
            )
        ),
        state,
        fixed=False,
    )
    _validate_merged_compose_config(
        executor.run(
            state.plan.compose(
                "--profile",
                "node",
                "--profile",
                "hermes-node-bridge",
                "config",
                "--no-interpolate",
                "--format",
                "json",
                fixed=True,
            )
        ),
        state,
        fixed=True,
    )
    for resource in ("container", "volume", "network"):
        result = executor.run(state.plan.resource_query(resource))
        _require_success(result, "project_resource_probe_failed")
        if result.stdout.strip():
            raise ProducerError("project_resource_preexists")
    for image in state.plan.images:
        result = executor.run(state.plan.image_query(image))
        _require_success(result, "image_absence_probe_failed")
        if result.stdout.strip():
            raise ProducerError("image_reference_preexists")
    models = provider.exact_models()
    if models.count(MODEL) != 1:
        raise ProducerError("host_provider_model_not_exact")


def _build_images(state: ProducerState, executor: Executor) -> None:
    _observe_exact_source(state)
    state.clean_before_node_build = True
    if not state.docker_preflight_complete:
        raise ProducerError("docker_preflight_incomplete")
    state.docker_mutation_started = True
    state.mutated = True
    _require_success(
        executor.run(
            state.plan.compose(
                "--profile",
                "node",
                "build",
                "ithildin-api",
                "ithildin-ui",
                "ithildin-node",
            ),
            timeout=900.0,
        ),
        "base_image_build_failed",
    )
    state.base_build_completed = True
    _bind_built_images(state, executor, state.plan.images[:3])
    _observe_exact_source(state)
    state.clean_after_node_build = True
    state.clean_before_bridge_build = True
    _require_success(
        executor.run(
            state.plan.compose(
                "--profile",
                "hermes-node-bridge",
                "build",
                "hermes",
                fixed=True,
            ),
            timeout=900.0,
        ),
        "bridge_image_build_failed",
    )
    state.bridge_build_completed = True
    _bind_built_images(state, executor, state.plan.images[3:])
    _observe_exact_source(state)
    state.clean_after_bridge_build = True


def _expected_image_service(state: ProducerState, reference: str) -> str:
    try:
        index = state.plan.images.index(reference)
    except ValueError as exc:
        raise ProducerError("image_reference_invalid") from exc
    return ("ithildin-api", "ithildin-ui", "ithildin-node", "hermes")[index]


def _inspect_exact_image_identity(
    state: ProducerState,
    executor: Executor,
    reference: str,
) -> BoundImageIdentity:
    result = executor.run(state.plan.image_inspect(reference))
    _require_success(result, "image_inspection_failed")
    try:
        raw = json.loads(result.stdout)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ProducerError("image_inspection_invalid") from exc
    if not isinstance(raw, dict):
        raise ProducerError("image_inspection_invalid")
    image_id = raw.get("Id")
    os_name = raw.get("Os")
    architecture = raw.get("Architecture")
    rootfs = raw.get("RootFS")
    layers = rootfs.get("Layers") if isinstance(rootfs, dict) else None
    config = raw.get("Config")
    labels = config.get("Labels") if isinstance(config, dict) else None
    compose_version = (
        labels.get("com.docker.compose.version")
        if isinstance(labels, dict)
        else None
    )
    expected_service = _expected_image_service(state, reference)
    platform = f"{os_name}/{architecture}"
    if (
        reference not in state.plan.images
        or raw.get("RepoTags") != [reference]
        or not isinstance(image_id, str)
        or not _DIGEST.fullmatch(image_id)
        or platform not in {"linux/amd64", "linux/arm64"}
        or not isinstance(layers, list)
        or not layers
        or any(
            not isinstance(value, str) or not _DIGEST.fullmatch(value)
            for value in layers
        )
        or not isinstance(labels, dict)
        or labels.get("com.docker.compose.project") != state.plan.project
        or labels.get("com.docker.compose.service") != expected_service
        or not isinstance(compose_version, str)
        or not _COMPOSE_VERSION_LABEL.fullmatch(compose_version)
    ):
        raise ProducerError("image_inspection_invalid")
    return BoundImageIdentity(
        reference=reference,
        image_id=image_id,
        project=state.plan.project,
        service=expected_service,
        compose_version=compose_version,
        platform=platform,
        layers=tuple(cast(list[str], layers)),
    )


def _bind_built_images(
    state: ProducerState,
    executor: Executor,
    references: tuple[str, ...],
) -> None:
    for reference in references:
        if reference in state.bound_images:
            raise ProducerError("image_identity_rebound")
        identity = _inspect_exact_image_identity(state, executor, reference)
        if identity.image_id in {
            bound.image_id for bound in state.bound_images.values()
        }:
            raise ProducerError("image_identity_duplicate")
        executor.bind_image_identity(identity.image_id)
        state.bound_images[reference] = identity
        state.inspected_images[reference] = identity.image_id
    if len({identity.platform for identity in state.bound_images.values()}) != 1:
        raise ProducerError("image_platform_mismatch")
    state.docker_ownership_proven = True


def _image_inventory(state: ProducerState, executor: Executor) -> JsonObject:
    inventory: list[JsonObject] = []
    platforms: set[str] = set()
    for reference in state.plan.images:
        observed = _inspect_exact_image_identity(state, executor, reference)
        bound = state.bound_images.get(reference)
        if bound is None or observed != bound:
            raise ProducerError("image_identity_drift")
        platforms.add(observed.platform)
        inventory.append(
            {
                "reference": reference,
                "image_id": observed.image_id,
                "platform": observed.platform,
                "config_digest": observed.image_id,
                "ordered_layer_digests": list(observed.layers),
            }
        )
    if len(platforms) != 1:
        raise ProducerError("image_platform_mismatch")
    state.image_platform = next(iter(platforms))
    state.docker_ownership_proven = True
    return {
        "schema_version": "1",
        "inventory_kind": "bounded_image_artifact_metadata_not_sbom",
        "images": cast(list[Any], inventory),
        "complete_sbom_claimed": False,
        "license_completeness_claimed": False,
        "compliance_claimed": False,
        "artifact_custody_claimed": False,
    }


def _license_source_inventory(state: ProducerState) -> JsonObject:
    if state.snapshot is None:
        raise ProducerError("candidate_snapshot_unavailable")
    tracked = sorted(state.snapshot.manifest)
    family = sorted(
        path
        for path in tracked
        if Path(path).name.startswith(("LICENSE", "NOTICE", "COPYING"))
    )
    inputs = sorted(path for path in tracked if path in LICENSE_INPUTS)
    if inputs != list(LICENSE_INPUTS) or family:
        raise ProducerError("license_source_inventory_drift")
    files: list[JsonObject] = []
    for relative in inputs:
        content = state.snapshot.read(relative)
        files.append(
            {
                "path": relative,
                "size_bytes": len(content),
                "sha256": "sha256:" + hashlib.sha256(content).hexdigest(),
            }
        )
    return {
        "schema_version": "1",
        "inventory_kind": "tracked_git_license_source_inventory",
        "candidate_commit": state.candidate_commit,
        "source": "private_exact_candidate_snapshot_no_follow_size_limited",
        "files": cast(list[Any], files),
        "license_family_files": [],
        "complete_sbom_claimed": False,
        "license_completeness_claimed": False,
        "compliance_claimed": False,
    }


def _base_service_start_diagnostic_fallback(
    *,
    output_rejected: bool,
) -> JsonObject:
    return {
        "collection_status": (
            "output_rejected" if output_rejected else "inconclusive"
        ),
        "reason_code": (
            "base_service_start_diagnostic_output_rejected"
            if output_rejected
            else "base_service_start_diagnostic_command_failed"
        ),
        "services": {
            "ithildin-api": "service_unobserved",
            "ithildin-ui": "service_unobserved",
        },
    }


def _validate_base_service_start_output_safety(
    result: CommandResult,
) -> None:
    try:
        combined = (result.stdout + result.stderr).encode(
            "utf-8",
            errors="strict",
        )
    except UnicodeError as exc:
        raise ProducerError("base_service_start_diagnostic_output_rejected") from exc
    if len(combined) > MAX_BASE_SERVICE_START_DIAGNOSTIC_BYTES:
        raise ProducerError("base_service_start_diagnostic_output_rejected")
    for text in (result.stdout, result.stderr):
        if any(
            (ord(character) < 32 and character not in {"\t", "\n"})
            or ord(character) == 127
            or ord(character) > 126
            for character in text
        ) or re.search(
            r"(?i)(?:authorization|bearer[ \t]|credential|enrollment[_ -]?code|"
            r"password|private[_ -]?key|prompt|raw[_ -]?output|secret|token)",
            text,
        ):
            raise ProducerError("base_service_start_diagnostic_output_rejected")


def _classify_base_service_start(
    state: str,
    health: str,
    exit_code: int,
) -> str:
    if state == "running":
        if exit_code != 0:
            raise ProducerError("base_service_start_diagnostic_output_rejected")
        classification = {
            "healthy": "service_running_healthy",
            "starting": "service_running_starting",
            "unhealthy": "service_running_unhealthy",
            "": "service_running_without_healthcheck",
        }.get(health)
        if classification is None:
            raise ProducerError("base_service_start_diagnostic_output_rejected")
        return classification
    if health:
        raise ProducerError("base_service_start_diagnostic_output_rejected")
    if state == "exited":
        return (
            "service_exited_zero"
            if exit_code == 0
            else "service_exited_nonzero"
        )
    if state == "dead":
        return (
            "service_dead_zero"
            if exit_code == 0
            else "service_dead_nonzero"
        )
    if state == "restarting":
        return (
            "service_restarting_zero"
            if exit_code == 0
            else "service_restarting_nonzero"
        )
    if exit_code != 0:
        raise ProducerError("base_service_start_diagnostic_output_rejected")
    classification = {
        "created": "service_created",
        "paused": "service_paused",
        "removing": "service_removing",
    }.get(state)
    if classification is None:
        raise ProducerError("base_service_start_diagnostic_output_rejected")
    return classification


def _parse_base_service_start_diagnostic(stdout: str) -> JsonObject:
    services: JsonObject = {
        "ithildin-api": "service_missing",
        "ithildin-ui": "service_missing",
    }
    observed: set[str] = set()
    lines = stdout.splitlines()
    if len(lines) > 2:
        raise ProducerError("base_service_start_diagnostic_output_rejected")
    for line in lines:
        fields = line.split("\t")
        if len(fields) != 4:
            raise ProducerError("base_service_start_diagnostic_output_rejected")
        service, state, health, raw_exit_code = fields
        if service not in services or service in observed:
            raise ProducerError("base_service_start_diagnostic_output_rejected")
        if not re.fullmatch(r"(?:0|[1-9][0-9]{0,2})", raw_exit_code):
            raise ProducerError("base_service_start_diagnostic_output_rejected")
        exit_code = int(raw_exit_code)
        if exit_code > 255:
            raise ProducerError("base_service_start_diagnostic_output_rejected")
        services[service] = _classify_base_service_start(
            state,
            health,
            exit_code,
        )
        observed.add(service)
    return services


def _collect_base_service_start_diagnostic(
    state: ProducerState,
    executor: Executor,
) -> JsonObject:
    try:
        result = executor.run(
            state.plan.base_service_start_diagnostic(),
            timeout=30.0,
        )
    except (Exception, KeyboardInterrupt, ProducerSignal):
        return _base_service_start_diagnostic_fallback(output_rejected=False)
    try:
        _validate_base_service_start_output_safety(result)
        if result.returncode != 0 or result.stderr:
            return _base_service_start_diagnostic_fallback(
                output_rejected=False
            )
        return {
            "collection_status": "complete",
            "reason_code": "base_service_start_state_collected",
            "services": _parse_base_service_start_diagnostic(result.stdout),
        }
    except (ProducerError, UnicodeError, ValueError):
        return _base_service_start_diagnostic_fallback(output_rejected=True)


def _api_container_state_fallback(
    *,
    collection_status: str,
    collection_reason_code: str,
) -> JsonObject:
    return {
        "collection_status": collection_status,
        "collection_reason_code": collection_reason_code,
        "cause_code": "api_exit_cause_inconclusive",
        "health_status": "absent",
    }


def _validate_api_container_diagnostic_safety(
    result: CommandResult,
) -> None:
    if result.classification == "output_rejected":
        raise ProducerError("api_container_state_output_rejected")
    try:
        combined = (result.stdout + result.stderr).encode(
            "utf-8",
            errors="strict",
        )
    except UnicodeError as exc:
        raise ProducerError("api_container_state_output_rejected") from exc
    if len(combined) > MAX_API_CONTAINER_DIAGNOSTIC_BYTES:
        raise ProducerError("api_container_state_output_rejected")
    for text in (result.stdout, result.stderr):
        if any(
            (ord(character) < 32 and character not in {"\t", "\n"})
            or ord(character) == 127
            or ord(character) > 126
            for character in text
        ) or re.search(
            r"(?i)(?:authorization|bearer[ \t]|credential|enrollment[_ -]?code|"
            r"password|private[_ -]?key|prompt|raw[_ -]?output|secret|token)",
            text,
        ):
            raise ProducerError("api_container_state_output_rejected")


def _parse_exact_api_container_id(stdout: str) -> tuple[str, str | None]:
    if stdout == "":
        return "missing", None
    candidate = stdout[:-1] if stdout.endswith("\n") else stdout
    if "\n" not in candidate and _CONTAINER_ID.fullmatch(candidate):
        return "bound", candidate
    lines = stdout.splitlines()
    if (
        len(lines) > 1
        and all(_CONTAINER_ID.fullmatch(line) is not None for line in lines)
    ):
        return "ambiguous", None
    raise ProducerError("api_container_state_output_rejected")


def _parse_bool(value: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    raise ProducerError("api_container_state_output_rejected")


def _parse_api_container_state(
    state: ProducerState,
    *,
    container_id: str,
    stdout: str,
) -> JsonObject:
    candidate = stdout[:-1] if stdout.endswith("\n") else stdout
    if "\n" in candidate:
        raise ProducerError("api_container_state_output_rejected")
    fields = candidate.split("\t")
    if len(fields) != 10:
        raise ProducerError("api_container_state_output_rejected")
    (
        observed_id,
        project,
        service,
        status,
        raw_running,
        raw_exit_code,
        raw_oom_killed,
        raw_dead,
        raw_error_present,
        health,
    ) = fields
    if (
        observed_id != container_id
        or project != state.plan.project
        or service != "ithildin-api"
        or status
        not in {
            "created",
            "running",
            "paused",
            "restarting",
            "removing",
            "exited",
            "dead",
        }
        or health not in {"absent", "starting", "healthy", "unhealthy"}
        or not re.fullmatch(r"(?:0|[1-9][0-9]{0,2})", raw_exit_code)
    ):
        raise ProducerError("api_container_state_output_rejected")
    exit_code = int(raw_exit_code)
    if exit_code > 255:
        raise ProducerError("api_container_state_output_rejected")
    running = _parse_bool(raw_running)
    oom_killed = _parse_bool(raw_oom_killed)
    dead = _parse_bool(raw_dead)
    error_present = _parse_bool(raw_error_present)
    inconsistent = (
        status != "exited"
        or running
        or dead
        or (exit_code == 0 and (oom_killed or error_present))
    )
    if inconsistent:
        cause_code = "api_state_inconsistent"
    elif exit_code == 0:
        cause_code = "api_unexpected_zero_exit"
    elif oom_killed:
        cause_code = "api_exit_oom_killed"
    elif error_present:
        cause_code = "api_container_runtime_error_present"
    else:
        cause_code = "api_application_exit_nonzero_no_engine_error"
    return {
        "collection_status": "complete",
        "collection_reason_code": "api_container_state_collected",
        "cause_code": cause_code,
        "health_status": health,
    }


def _collect_api_container_state_diagnostic(
    state: ProducerState,
    executor: Executor,
) -> JsonObject:
    try:
        query = executor.run(
            state.plan.api_container_id_query(),
            timeout=10.0,
        )
    except (Exception, KeyboardInterrupt, ProducerSignal):
        return _api_container_state_fallback(
            collection_status="inconclusive",
            collection_reason_code="api_container_state_command_failed",
        )
    try:
        _validate_api_container_diagnostic_safety(query)
        if (
            query.returncode != 0
            or query.stderr
            or query.classification != "completed"
        ):
            return _api_container_state_fallback(
                collection_status="inconclusive",
                collection_reason_code="api_container_state_command_failed",
            )
        identity_status, container_id = _parse_exact_api_container_id(
            query.stdout
        )
    except ProducerError:
        return _api_container_state_fallback(
            collection_status="output_rejected",
            collection_reason_code="api_container_state_output_rejected",
        )
    if identity_status == "missing":
        return _api_container_state_fallback(
            collection_status="inconclusive",
            collection_reason_code="api_container_id_missing",
        )
    if identity_status == "ambiguous" or container_id is None:
        return _api_container_state_fallback(
            collection_status="output_rejected",
            collection_reason_code="api_container_id_ambiguous",
        )
    try:
        executor.bind_container_identity(container_id)
        inspected = executor.run(
            state.plan.api_container_state_inspect(container_id),
            timeout=10.0,
        )
    except (Exception, KeyboardInterrupt, ProducerSignal):
        return _api_container_state_fallback(
            collection_status="inconclusive",
            collection_reason_code="api_container_state_command_failed",
        )
    try:
        _validate_api_container_diagnostic_safety(inspected)
        if (
            inspected.returncode != 0
            or inspected.stderr
            or inspected.classification != "completed"
        ):
            return _api_container_state_fallback(
                collection_status="inconclusive",
                collection_reason_code="api_container_state_command_failed",
            )
        return _parse_api_container_state(
            state,
            container_id=container_id,
            stdout=inspected.stdout,
        )
    except ProducerError:
        return _api_container_state_fallback(
            collection_status="output_rejected",
            collection_reason_code="api_container_state_output_rejected",
        )


def _fixed_node_start_fallback(
    *,
    collection_status: str,
    collection_reason_code: str,
) -> JsonObject:
    return {
        "collection_status": collection_status,
        "collection_reason_code": collection_reason_code,
        "classification": "fixed_node_start_inconclusive",
        "container_presence": "unknown",
        "container_lifecycle_state": "unknown",
        "container_running_state": "unknown",
        "container_exit_class": "unknown",
        "fixed_bridge_last_entered_phase": "unknown",
        "container_health_state": "unknown",
        "container_failure_signal": "unknown",
        "observation_semantics": "not_collected",
        "mission_lifecycle_state": "unknown",
        "delivery_state": "unknown",
        "evidence_state": "unknown",
    }


def _validate_fixed_node_diagnostic_safety(
    result: CommandResult,
) -> None:
    if result.classification == "output_rejected":
        raise ProducerError("fixed_node_start_diagnostic_output_rejected")
    try:
        combined = (result.stdout + result.stderr).encode(
            "utf-8",
            errors="strict",
        )
    except UnicodeError as exc:
        raise ProducerError("fixed_node_start_diagnostic_output_rejected") from exc
    if len(combined) > MAX_FIXED_NODE_START_DIAGNOSTIC_BYTES:
        raise ProducerError("fixed_node_start_diagnostic_output_rejected")
    for text in (result.stdout, result.stderr):
        if any(
            (ord(character) < 32 and character not in {"\t", "\n"})
            or ord(character) == 127
            or ord(character) > 126
            for character in text
        ) or re.search(
            r"(?i)(?:authorization|bearer[ \t]|credential|enrollment[_ -]?code|"
            r"password|private[_ -]?key|prompt|raw[_ -]?output|secret|token)",
            text,
        ):
            raise ProducerError("fixed_node_start_diagnostic_output_rejected")


def _parse_exact_fixed_node_container_id(
    stdout: str,
) -> tuple[str, str | None]:
    if stdout == "":
        return "missing", None
    candidate = stdout[:-1] if stdout.endswith("\n") else stdout
    if "\n" not in candidate and _CONTAINER_ID.fullmatch(candidate):
        return "bound", candidate
    lines = stdout.splitlines()
    if (
        len(lines) > 1
        and all(_CONTAINER_ID.fullmatch(line) is not None for line in lines)
    ):
        return "ambiguous", None
    raise ProducerError("fixed_node_start_diagnostic_output_rejected")


def _parse_fixed_node_container_state(
    state: ProducerState,
    *,
    container_id: str,
    stdout: str,
) -> FixedNodeContainerState:
    candidate = stdout[:-1] if stdout.endswith("\n") else stdout
    if "\n" in candidate:
        raise ProducerError("fixed_node_start_diagnostic_output_rejected")
    fields = candidate.split("\t")
    if len(fields) != 10:
        raise ProducerError("fixed_node_start_diagnostic_output_rejected")
    (
        observed_id,
        project,
        service,
        status,
        raw_running,
        raw_exit_code,
        raw_oom_killed,
        raw_dead,
        raw_error_present,
        health,
    ) = fields
    if (
        observed_id != container_id
        or project != state.plan.project
        or service != "ithildin-node"
        or status
        not in {
            "created",
            "running",
            "paused",
            "restarting",
            "removing",
            "exited",
            "dead",
        }
        or health not in {"absent", "starting", "healthy", "unhealthy"}
        or not re.fullmatch(r"(?:0|[1-9][0-9]{0,2})", raw_exit_code)
    ):
        raise ProducerError("fixed_node_start_diagnostic_output_rejected")
    exit_code = int(raw_exit_code)
    if exit_code > 255:
        raise ProducerError("fixed_node_start_diagnostic_output_rejected")
    try:
        running = _parse_bool(raw_running)
        oom_killed = _parse_bool(raw_oom_killed)
        dead = _parse_bool(raw_dead)
        engine_error_present = _parse_bool(raw_error_present)
    except ProducerError as exc:
        raise ProducerError("fixed_node_start_diagnostic_output_rejected") from exc
    return FixedNodeContainerState(
        status=status,
        running=running,
        exit_class="zero" if exit_code == 0 else "nonzero",
        fixed_bridge_last_entered_phase=FIXED_BRIDGE_PHASE_BY_EXIT_CODE.get(
            exit_code,
            "not_reported",
        ),
        oom_killed=oom_killed,
        dead=dead,
        engine_error_present=engine_error_present,
        health_status=health,
    )


def _fixed_node_mission_projection(
    state: ProducerState,
    detail: JsonObject,
) -> JsonObject:
    if state.mission_id is None or detail.get("mission_id") != state.mission_id:
        raise ProducerError("fixed_node_start_diagnostic_output_rejected")
    delivery = detail.get("delivery")
    evidence = detail.get("evidence")
    if not isinstance(delivery, dict) or not isinstance(evidence, dict):
        raise ProducerError("fixed_node_start_diagnostic_output_rejected")
    lifecycle_state = detail.get("lifecycle_state")
    delivery_state = delivery.get("state")
    evidence_state = evidence.get("state")
    if (
        lifecycle_state
        not in {
            "unadmitted",
            "queued",
            "claimed",
            "runner_reported_running",
            "runner_reported_succeeded",
            "runner_reported_failed",
            "cancel_requested",
            "runner_reported_canceled",
            "claim_expired_review_required",
            "canceled",
        }
        or delivery_state
        not in {
            "not_claimed",
            "claim_pending_evidence",
            "claim_delivered",
            "claim_evidence_incomplete",
            "claim_expired_review_required",
        }
        or evidence_state not in {"complete", "evidence_incomplete"}
    ):
        raise ProducerError("fixed_node_start_diagnostic_output_rejected")
    return {
        "mission_lifecycle_state": lifecycle_state,
        "delivery_state": delivery_state,
        "evidence_state": evidence_state,
    }


def _fixed_node_container_projection(
    container: FixedNodeContainerState | None,
    *,
    collected: bool,
) -> JsonObject:
    if not collected:
        return {
            "container_presence": "unknown",
            "container_lifecycle_state": "unknown",
            "container_running_state": "unknown",
            "container_exit_class": "unknown",
            "fixed_bridge_last_entered_phase": "unknown",
            "container_health_state": "unknown",
            "container_failure_signal": "unknown",
        }
    if container is None:
        return {
            "container_presence": "missing",
            "container_lifecycle_state": "not_applicable",
            "container_running_state": "not_applicable",
            "container_exit_class": "not_applicable",
            "fixed_bridge_last_entered_phase": "not_applicable",
            "container_health_state": "not_applicable",
            "container_failure_signal": "not_applicable",
        }
    failure_signals = (
        ("oom_killed", container.oom_killed),
        ("dead_flag", container.dead),
        ("engine_error_present", container.engine_error_present),
    )
    present_signals = [name for name, present in failure_signals if present]
    failure_signal = (
        "none"
        if not present_signals
        else present_signals[0]
        if len(present_signals) == 1
        else "multiple"
    )
    return {
        "container_presence": "present",
        "container_lifecycle_state": container.status,
        "container_running_state": (
            "running" if container.running else "not_running"
        ),
        "container_exit_class": container.exit_class,
        "fixed_bridge_last_entered_phase": (
            container.fixed_bridge_last_entered_phase
        ),
        "container_health_state": container.health_status,
        "container_failure_signal": failure_signal,
    }


def _classify_fixed_node_start(
    container: FixedNodeContainerState | None,
    mission: JsonObject,
) -> str:
    if container is None:
        return "fixed_node_container_missing"
    if container.status == "created":
        return "fixed_node_container_created"
    if (
        container.oom_killed
        or container.dead
        or container.engine_error_present
        or container.status in {"dead", "restarting", "removing"}
    ):
        return "fixed_node_container_runtime_error"
    lifecycle = mission["mission_lifecycle_state"]
    delivery = mission["delivery_state"]
    before_claim = lifecycle == "queued" and delivery == "not_claimed"
    after_claim = (
        lifecycle
        in {
            "claimed",
            "runner_reported_running",
            "runner_reported_succeeded",
            "runner_reported_failed",
            "cancel_requested",
            "runner_reported_canceled",
            "claim_expired_review_required",
            "canceled",
        }
        and delivery != "not_claimed"
    )
    if lifecycle != "queued" and delivery == "not_claimed":
        return "fixed_node_claim_state_inconsistent"
    if not before_claim and not after_claim:
        return "fixed_node_claim_state_inconsistent"
    if container.status == "exited":
        if container.running or container.dead or container.health_status != "absent":
            return "fixed_node_exited_observation_noncanonical"
        if container.exit_class == "zero":
            return (
                "fixed_node_exited_zero_no_queued_mission_or_"
                "claim_observation_inconsistent"
                if before_claim
                else "fixed_node_exited_zero_with_claim_observed"
            )
        return (
            "fixed_node_exited_nonzero_before_claim"
            if before_claim
            else "fixed_node_exited_nonzero_after_claim"
        )
    if container.status == "running":
        if not container.running or container.exit_class != "zero":
            return "fixed_node_running_observation_noncanonical"
        if container.health_status == "absent":
            return (
                "fixed_node_running_without_health_observation_"
                "after_wait_failure"
            )
        if container.health_status == "starting":
            return "fixed_node_running_health_starting_after_wait_failure"
        if container.health_status == "healthy":
            return "fixed_node_running_healthy_after_wait_failure"
        if container.health_status == "unhealthy":
            return "fixed_node_running_unhealthy_socket_health_contract"
        raise ProducerError("fixed_node_start_diagnostic_output_rejected")
    if container.status == "paused":
        return "fixed_node_paused_after_wait_failure"
    raise ProducerError("fixed_node_start_diagnostic_output_rejected")


def _collect_fixed_node_start_diagnostic(
    state: ProducerState,
    executor: Executor,
    api: Api,
) -> JsonObject:
    state.fixed_node_start_diagnostic_calls += 1
    if state.fixed_node_start_diagnostic_calls != 1:
        return _fixed_node_start_fallback(
            collection_status="output_rejected",
            collection_reason_code="fixed_node_start_diagnostic_repeated",
        )
    container: FixedNodeContainerState | None = None
    container_collection_status = "complete"
    container_collection_reason = "fixed_node_start_state_collected"
    identity_status = "unavailable"
    container_id: str | None = None
    try:
        query = executor.run(
            state.plan.fixed_node_container_id_query(),
            timeout=10.0,
        )
    except (KeyboardInterrupt, ProducerSignal):
        return _fixed_node_start_fallback(
            collection_status="inconclusive",
            collection_reason_code="fixed_node_start_diagnostic_interrupted",
        )
    except Exception:
        container_collection_status = "inconclusive"
        container_collection_reason = "fixed_node_start_diagnostic_command_failed"
    else:
        try:
            _validate_fixed_node_diagnostic_safety(query)
            if (
                query.returncode != 0
                or query.stderr
                or query.classification != "completed"
            ):
                container_collection_status = "inconclusive"
                container_collection_reason = (
                    "fixed_node_start_diagnostic_command_failed"
                )
            else:
                identity_status, container_id = (
                    _parse_exact_fixed_node_container_id(query.stdout)
                )
        except ProducerError:
            container_collection_status = "output_rejected"
            container_collection_reason = (
                "fixed_node_start_diagnostic_output_rejected"
            )
    if identity_status == "ambiguous":
        container_collection_status = "output_rejected"
        container_collection_reason = "fixed_node_container_id_ambiguous"
    if identity_status == "bound" and container_id is not None:
        try:
            executor.bind_container_identity(container_id)
            try:
                inspected = executor.run(
                    state.plan.fixed_node_container_state_inspect(container_id),
                    timeout=10.0,
                )
            finally:
                executor.discard_container_identity(container_id)
        except (KeyboardInterrupt, ProducerSignal):
            return _fixed_node_start_fallback(
                collection_status="inconclusive",
                collection_reason_code="fixed_node_start_diagnostic_interrupted",
            )
        except Exception:
            container_collection_status = "inconclusive"
            container_collection_reason = (
                "fixed_node_start_diagnostic_command_failed"
            )
        else:
            try:
                _validate_fixed_node_diagnostic_safety(inspected)
                if (
                    inspected.returncode != 0
                    or inspected.stderr
                    or inspected.classification != "completed"
                ):
                    container_collection_status = "inconclusive"
                    container_collection_reason = (
                        "fixed_node_start_diagnostic_command_failed"
                    )
                else:
                    container = _parse_fixed_node_container_state(
                        state,
                        container_id=container_id,
                        stdout=inspected.stdout,
                    )
            except ProducerError:
                container_collection_status = "output_rejected"
                container_collection_reason = (
                    "fixed_node_start_diagnostic_output_rejected"
                )
        container_id = None
    try:
        if state.mission_id is None:
            raise ProducerError("fixed_node_start_diagnostic_output_rejected")
        mission = _fixed_node_mission_projection(
            state,
            api.get(f"/missions/{state.mission_id}"),
        )
        classification = _classify_fixed_node_start(container, mission)
    except ProducerError:
        return _fixed_node_start_fallback(
            collection_status="output_rejected",
            collection_reason_code="fixed_node_start_diagnostic_output_rejected",
        )
    except (Exception, KeyboardInterrupt, ProducerSignal):
        return _fixed_node_start_fallback(
            collection_status="inconclusive",
            collection_reason_code="fixed_node_start_mission_query_failed",
        )
    container_projection = _fixed_node_container_projection(
        container,
        collected=container_collection_status == "complete",
    )
    if container_collection_status != "complete":
        return {
            "collection_status": container_collection_status,
            "collection_reason_code": container_collection_reason,
            "classification": "fixed_node_start_inconclusive",
            **container_projection,
            "observation_semantics": "sequential_container_then_mission",
            **mission,
        }
    return {
        "collection_status": "complete",
        "collection_reason_code": "fixed_node_start_state_collected",
        "classification": classification,
        **container_projection,
        "observation_semantics": "sequential_container_then_mission",
        **mission,
    }


def _application_startup_stage_fallback(
    *,
    collection_status: str,
    collection_reason_code: str,
) -> JsonObject:
    return {
        "collection_status": collection_status,
        "collection_reason_code": collection_reason_code,
        "last_emitted_stage": "unknown",
    }


def _closed_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON member")
        result[key] = value
    return result


def _collect_application_startup_stage_diagnostic(
    state: ProducerState,
) -> JsonObject:
    try:
        content = state.runtime.read_exact_owner_file(
            APPLICATION_STARTUP_STATUS_DIRECTORY,
            APPLICATION_STARTUP_STATUS_FILE,
            maximum=MAX_APPLICATION_STARTUP_STAGE_BYTES,
        )
        if content is None:
            return _application_startup_stage_fallback(
                collection_status="inconclusive",
                collection_reason_code="application_startup_stage_missing",
            )
        raw = json.loads(
            content.decode("utf-8", errors="strict"),
            object_pairs_hook=_closed_json_object,
        )
        if (
            not isinstance(raw, dict)
            or set(raw) != {"record_type", "schema_version", "stage"}
            or raw.get("record_type")
            != "ithildin_api_closed_startup_stage"
            or raw.get("schema_version") != "1"
            or not isinstance(raw.get("stage"), str)
            or raw["stage"] not in APPLICATION_STARTUP_STAGES
        ):
            raise ProducerError("application_startup_stage_invalid")
        normalized: JsonObject = {
            "record_type": "ithildin_api_closed_startup_stage",
            "schema_version": "1",
            "stage": cast(str, raw["stage"]),
        }
        if content != (canonical_json(normalized) + "\n").encode("utf-8"):
            raise ProducerError("application_startup_stage_invalid")
        return {
            "collection_status": "complete",
            "collection_reason_code": "application_startup_stage_collected",
            "last_emitted_stage": cast(str, raw["stage"]),
        }
    except (
        OSError,
        ProducerError,
        UnicodeError,
        ValueError,
        json.JSONDecodeError,
    ):
        return _application_startup_stage_fallback(
            collection_status="output_rejected",
            collection_reason_code=(
                "application_startup_stage_unsafe_or_incomplete"
            ),
        )


def _start_and_enroll(state: ProducerState, executor: Executor, api: Api) -> str:
    start = executor.run(
        state.plan.compose(
            "up",
            "--detach",
            "--wait",
            "ithildin-api",
            "ithildin-ui",
        )
    )
    if start.returncode != 0:
        state.base_service_start_diagnostic = (
            _collect_base_service_start_diagnostic(state, executor)
        )
        services = state.base_service_start_diagnostic.get("services")
        if (
            state.base_service_start_diagnostic.get("collection_status")
            == "complete"
            and isinstance(services, dict)
            and services.get("ithildin-api") == "service_exited_nonzero"
        ):
            api_container_diagnostic = (
                _collect_api_container_state_diagnostic(state, executor)
            )
            state.base_service_start_diagnostic[
                "api_container_state_diagnostic"
            ] = api_container_diagnostic
            if (
                api_container_diagnostic.get("collection_status") == "complete"
                and api_container_diagnostic.get("cause_code")
                == "api_application_exit_nonzero_no_engine_error"
            ):
                state.base_service_start_diagnostic[
                    "application_startup_stage_diagnostic"
                ] = _collect_application_startup_stage_diagnostic(state)
        raise ProducerError("base_services_start_failed")
    _require_success(start, "base_services_start_failed")
    health = api.get("/healthz", admin=False)
    if health != {"status": "ok", "service": "ithildin-api"}:
        raise ProducerError("gateway_health_invalid")
    status = api.get("/system/status")
    if status.get("status") != "ok" or status.get("tool_count") != 24:
        raise ProducerError("gateway_status_invalid")
    workspaces = api.get("/workspaces").get("workspaces")
    if (
        not isinstance(workspaces, list)
        or sum(
            isinstance(item, dict)
            and item.get("id") == WORKSPACE_ID
            and item.get("enabled") is True
            for item in workspaces
        )
        != 1
    ):
        raise ProducerError("workspace_projection_invalid")
    issued = api.post(
        "/nodes/enrollment-codes",
        {
            "workspace_id": WORKSPACE_ID,
            "display_name": f"Local v1 O4 Node {state.plan.suffix}",
        },
    )
    code = issued.get("enrollment_code")
    if (
        not isinstance(code, str)
        or not code
        or issued.get("secret_returned_once") is not True
        or issued.get("workspace_id") != WORKSPACE_ID
    ):
        raise ProducerError("enrollment_code_projection_invalid")
    state.recovery_required = True
    state.enrollment_attempted = True
    state.enrollment_outcome_ambiguous = True
    result = executor.run(
        state.plan.compose(
            "--profile",
            "node",
            "run",
            "--rm",
            "-T",
            "--no-deps",
            "ithildin-node",
            "enroll",
            "--api-url",
            "http://ithildin-api:8000",
            "--state",
            "/var/lib/ithildin-node/state.json",
            "--node-version",
            NODE_VERSION,
            "--runner-adapter",
            "hermes",
            "--deployment-topology",
            "docker_sidecar",
            "--enrollment-code-stdin",
        ),
        input_text=code + "\n",
    )
    _require_success(result, "enrollment_outcome_ambiguous")
    node_id = _parse_enrollment_projection(result.stdout)
    state.node_id = node_id
    state.node_enrolled = True
    state.enrollment_outcome_ambiguous = False
    assignment = api.post(
        f"/nodes/{node_id}/configurations",
        {
            "minimum_node_version": NODE_VERSION,
            "heartbeat_interval_seconds": 15,
            "offline_posture": "deny_governed_actions",
            "evidence_buffer_max_events": 1000,
            "validity_seconds": 3600,
        },
    )
    if (
        type(assignment.get("generation")) is not int
        or cast(int, assignment["generation"]) < 1
        or not isinstance(assignment.get("configuration_digest"), str)
        or not _DIGEST.fullmatch(cast(str, assignment["configuration_digest"]))
        or assignment.get("evidence_status") != "complete"
    ):
        raise ProducerError("configuration_assignment_invalid")
    state.configuration_generation = cast(int, assignment["generation"])
    state.configuration_digest = cast(str, assignment["configuration_digest"])
    _require_success(
        executor.run(
            state.plan.compose(
                "--profile",
                "node",
                "up",
                "--detach",
                "--no-deps",
                "ithildin-node",
            )
        ),
        "ordinary_node_start_failed",
    )
    state.recovery_required = False
    return code


def _parse_enrollment_projection(stdout: str) -> str:
    try:
        raw = json.loads(stdout, object_pairs_hook=_closed_json_object)
    except (UnicodeError, ValueError) as exc:
        raise ProducerError("enrollment_projection_invalid") from exc
    if (
        not isinstance(raw, dict)
        or set(raw) != {"node_id", "principal_id", "workspace_id"}
        or not all(isinstance(value, str) for value in raw.values())
    ):
        raise ProducerError("enrollment_projection_invalid")
    node_id = cast(str, raw["node_id"])
    normalized: JsonObject = {
        "node_id": node_id,
        "principal_id": cast(str, raw["principal_id"]),
        "workspace_id": cast(str, raw["workspace_id"]),
    }
    try:
        content = stdout.encode("utf-8", errors="strict")
        canonical = (canonical_json(normalized) + "\n").encode("utf-8")
    except UnicodeError as exc:
        raise ProducerError("enrollment_projection_invalid") from exc
    if (
        not _NODE_ID.fullmatch(node_id)
        or normalized["principal_id"] != f"agent:node.{node_id}"
        or normalized["workspace_id"] != WORKSPACE_ID
        or content != canonical
    ):
        raise ProducerError("enrollment_projection_invalid")
    return node_id


def _prove_node_eligibility(state: ProducerState, api: Api) -> None:
    if (
        state.node_id is None
        or state.configuration_generation is None
        or state.configuration_digest is None
    ):
        raise ProducerError("node_configuration_identity_missing")
    deadline = time.monotonic() + NODE_SYNCHRONIZATION_SECONDS
    while time.monotonic() < deadline:
        node = api.get(f"/nodes/{state.node_id}")
        if (
            node.get("node_id") == state.node_id
            and node.get("principal_id") == f"agent:node.{state.node_id}"
            and node.get("workspace_id") == WORKSPACE_ID
            and node.get("identity_source") == "gateway_derived"
            and node.get("evidence_status") == "complete"
            and node.get("desired_configuration_generation")
            == state.configuration_generation
            and node.get("desired_configuration_digest")
            == state.configuration_digest
            and node.get("acknowledged_configuration_generation")
            == state.configuration_generation
            and node.get("acknowledged_configuration_digest")
            == state.configuration_digest
            and node.get("last_configuration_digest")
            == state.configuration_digest
            and node.get("configuration_acknowledgment_status")
            == "stored_not_enforced"
            and node.get("configuration_state") == "stored_current_not_enforced"
            and node.get("observed_state") == "observed_connected"
            and node.get("connectivity_source") == "gateway_accepted_heartbeat"
            and node.get("runner_health_known") is False
            and node.get("model_health_known") is False
        ):
            return
        time.sleep(0.25)
    raise ProducerError("node_synchronization_timeout")


def _admit_mission(state: ProducerState, api: Api) -> None:
    if state.node_id is None:
        raise ProducerError("node_identity_missing")
    admitted = api.post(
        "/missions",
        {
            "target_node_id": state.node_id,
            "mission_template_id": "synthetic_read_review_v1",
            "requested_timeout_seconds": 300,
            "client_request_id": f"lv1-o4-{state.run_id}",
        },
    )
    mission_id = admitted.get("mission_id")
    if (
        not isinstance(mission_id, str)
        or not _MISSION_ID.fullmatch(mission_id)
        or admitted.get("target_node_id") != state.node_id
        or admitted.get("mission_template_id") != "synthetic_read_review_v1"
        or admitted.get("client_request_id") != f"lv1-o4-{state.run_id}"
    ):
        raise ProducerError("mission_admission_invalid")
    state.mission_id = mission_id
    state.mission_admitted = True


def _gateway_journey(state: ProducerState, api: Api) -> JsonObject:
    if state.mission_id is None:
        raise ProducerError("mission_identity_missing")
    detail = api.get(f"/missions/{state.mission_id}")
    if (
        detail.get("mission_id") != state.mission_id
        or detail.get("lifecycle_state") != "runner_reported_succeeded"
        or detail.get("target_node_id") != state.node_id
    ):
        raise ProducerError("gateway_mission_projection_invalid")
    delivery = detail.get("delivery")
    governed = detail.get("governed_agent_runs")
    if not isinstance(delivery, dict) or not isinstance(governed, dict):
        raise ProducerError("gateway_mission_projection_invalid")
    claim = delivery.get("claim")
    runs = governed.get("runs")
    if (
        not isinstance(claim, dict)
        or not isinstance(runs, list)
        or len(runs) != 1
        or governed.get("authority") != "gateway_agent_run_evidence"
        or governed.get("correlation_basis") != "gateway_validated_claim_session"
        or governed.get("rejected_correlation_count") != 0
    ):
        raise ProducerError("gateway_run_correlation_invalid")
    run_summary = runs[0]
    if not isinstance(run_summary, dict):
        raise ProducerError("gateway_run_correlation_invalid")
    run_id = run_summary.get("run_id")
    claim_id = claim.get("claim_id")
    envelope_digest = detail.get("envelope_digest")
    if (
        not isinstance(run_id, str)
        or not _RUN_RECORD_ID.fullmatch(run_id)
        or run_summary.get("status") != "active"
        or run_summary.get("tool_call_count") != 2
        or not isinstance(claim_id, str)
        or not _CLAIM_ID.fullmatch(claim_id)
        or not isinstance(envelope_digest, str)
        or not _DIGEST.fullmatch(envelope_digest)
    ):
        raise ProducerError("gateway_run_correlation_invalid")
    run_detail = api.get(f"/runs/{run_id}")
    run = run_detail.get("run")
    timeline = run_detail.get("timeline")
    if not isinstance(run, dict) or not isinstance(timeline, list):
        raise ProducerError("gateway_run_detail_invalid")
    session_id = (
        f"mission:{state.mission_id}:{claim_id}:"
        f"{envelope_digest.removeprefix('sha256:')[:16]}"
    )
    if (
        run.get("run_id") != run_id
        or run.get("session_id") != session_id
        or run.get("status") != "active"
        or run.get("tool_call_count") != 2
    ):
        raise ProducerError("gateway_run_detail_invalid")
    completed = [
        event for event in timeline
        if isinstance(event, dict) and event.get("event_type") == "tool.execution.completed"
    ]
    expected_tools = ("project.structure.summary", "project.test.summary")
    if len(completed) != 2:
        raise ProducerError("gateway_completed_event_count_invalid")
    bindings: list[JsonObject] = []
    for index, (event, expected_tool) in enumerate(
        zip(completed, expected_tools, strict=True),
        start=1,
    ):
        metadata = event.get("metadata")
        event_id = event.get("event_id")
        event_hash = event.get("event_hash")
        request_id = event.get("request_id")
        if (
            not isinstance(metadata, dict)
            or not isinstance(event_id, str)
            or not _EVENT_ID.fullmatch(event_id)
            or not isinstance(event_hash, str)
            or not _DIGEST.fullmatch(event_hash)
            or not isinstance(request_id, str)
            or not _REQUEST_ID.fullmatch(request_id)
            or event.get("tool_name") != expected_tool
            or metadata.get("run_id") != run_id
            or metadata.get("mission_id") != state.mission_id
            or metadata.get("mission_claim_id") != claim_id
            or metadata.get("mission_envelope_digest") != envelope_digest
        ):
            raise ProducerError("gateway_completed_event_binding_invalid")
        bindings.append(
            {
                "operation_index": index,
                "event_id": event_id,
                "event_hash": event_hash,
                "event_type": "tool.execution.completed",
                "tool_name": expected_tool,
                "request_id": request_id,
                "run_id": run_id,
                "session_id": session_id,
                "mission_id": state.mission_id,
                "claim_id": claim_id,
                "envelope_digest": envelope_digest,
                "authority": "gateway_agent_run_evidence",
                "correlation_basis": "gateway_validated_claim_session",
                "status": "completed",
            }
        )
    if state.snapshot is None:
        raise ProducerError("candidate_snapshot_unavailable")
    profile = state.snapshot.json_object("deploy/hermes-node-bridge/profile.json")
    return {
        "candidate_commit": state.candidate_commit,
        "candidate_tree": state.candidate_tree,
        "mission_id": state.mission_id,
        "claim_id": claim_id,
        "envelope_digest": envelope_digest,
        "profile_digest": sha256_digest(profile),
        "handoff_nonce_digest": "sha256:" + ("0" * 64),
        "authority": "gateway_agent_run_evidence",
        "correlation_basis": "gateway_validated_claim_session",
        "rejected_correlation_count": 0,
        "mission_session_id": session_id,
        "gateway_agent_runs": [
            {
                "run_id": run_id,
                "session_id": session_id,
                "mission_id": state.mission_id,
                "claim_id": claim_id,
                "envelope_digest": envelope_digest,
                "authority": "gateway_agent_run_evidence",
                "correlation_basis": "gateway_validated_claim_session",
                "tool_call_count": 2,
                "status": "active",
            }
        ],
        "gateway_operation_bindings": cast(list[Any], bindings),
        "gateway_lifecycle_state": "runner_reported_succeeded",
        "runner_state_authority": "runner_reported_only",
        "model_provider_state_known": False,
        "container_absent": False,
        "volumes_absent": False,
        "network_absent": False,
        "persistent_profile_volume_absent": False,
        "run_specific_images_absent": False,
        "runtime_plaintext_absent": False,
        "read_only_root": True,
        "logging_driver": "none",
        "tmpfs_limits": cast(JsonObject, cast(JsonObject, profile["limits"])["tmpfs"]),
    }


def _bind_node_receipt(state: ProducerState, executor: Executor) -> None:
    if state.gateway_journey is None:
        raise ProducerError("gateway_journey_missing")
    destination = state.runtime.file("copied-receipt/node-mission-receipt.json")
    _require_success(
        executor.run(
            state.plan.compose(
                "--profile",
                "node",
                "cp",
                "ithildin-node:/var/lib/ithildin-node/mission-receipt.json",
                str(destination),
                fixed=True,
            )
        ),
        "node_receipt_copy_failed",
    )
    content = state.runtime.read("copied-receipt/node-mission-receipt.json")
    try:
        receipt = json.loads(content)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ProducerError("node_receipt_invalid") from exc
    if not isinstance(receipt, dict):
        raise ProducerError("node_receipt_invalid")
    expected_keys = {
        "mission_id",
        "claim_id",
        "envelope_digest",
        "next_operation_index",
        "handoff_nonce_digest",
        "last_closed_status",
    }
    journey = state.gateway_journey
    nonce_digest = receipt.get("handoff_nonce_digest")
    if (
        set(receipt) != expected_keys
        or receipt.get("mission_id") != journey.get("mission_id")
        or receipt.get("claim_id") != journey.get("claim_id")
        or receipt.get("envelope_digest") != journey.get("envelope_digest")
        or not isinstance(nonce_digest, str)
        or not _DIGEST.fullmatch(nonce_digest)
        or receipt.get("next_operation_index") != 4
        or receipt.get("last_closed_status") != "runner_reported_succeeded"
    ):
        raise ProducerError("node_receipt_binding_invalid")
    journey["handoff_nonce_digest"] = nonce_digest


def _reconcile_bound_images_for_cleanup(
    state: ProducerState,
    executor: Executor,
) -> None:
    for reference in state.plan.images:
        bound = state.bound_images.get(reference)
        query = executor.run(state.plan.image_query(reference))
        _require_success(query, "image_cleanup_reference_probe_failed")
        if bound is None:
            if query.stdout.strip():
                raise ProducerError("unbound_image_reference_present")
            continue
        if query.stdout.split() != [bound.image_id]:
            raise ProducerError("bound_image_reference_drift")
        observed = _inspect_exact_image_identity(state, executor, reference)
        if observed != bound:
            raise ProducerError("bound_image_metadata_drift")
        ancestors = executor.run(
            state.plan.image_ancestor_containers(bound.image_id)
        )
        _require_success(ancestors, "image_ancestor_probe_failed")
        if ancestors.stdout.strip():
            raise ProducerError("image_ancestor_container_present")


def _cleanup_once(
    state: ProducerState,
    executor: Executor | None,
    api: Api | None,
) -> JsonObject | None:
    state.cleanup_calls += 1
    if state.cleanup_calls != 1:
        state.recovery_required = True
        return None
    cleanup: JsonObject = {
        "node_revoked": False,
        "container_absent": False,
        "volumes_absent": False,
        "network_absent": False,
        "persistent_profile_volume_absent": False,
        "run_specific_images_absent": False,
        "runtime_plaintext_absent": False,
    }
    failures: list[str] = []

    def attempt(name: str, action: Callable[[], None]) -> None:
        try:
            action()
        except (ProducerError, OSError, KeyboardInterrupt, ProducerSignal):
            failures.append(name)

    def remove_plaintext() -> None:
        if not state.runtime.remove():
            raise ProducerError("runtime_plaintext_removal_failed")
        cleanup["runtime_plaintext_absent"] = True

    def stop_fixed_node() -> None:
        if executor is None:
            raise ProducerError("fixed_node_stop_unavailable")
        _require_success(
            executor.run(
                state.plan.compose(
                    "--profile",
                    "node",
                    "stop",
                    "ithildin-node",
                    fixed=True,
                )
            ),
            "fixed_node_stop_failed",
        )

    if state.enrollment_outcome_ambiguous:
        if state.node_id is None or not _NODE_ID.fullmatch(state.node_id):
            failures.append("enrollment_outcome_ambiguous")
            state.cleanup_failures = failures
            state.recovery_required = True
            return None
        state.enrollment_outcome_ambiguous = False

    if not state.docker_mutation_started:
        if (
            state.mutated
            or state.docker_ownership_proven
            or state.enrollment_attempted
            or state.node_enrolled
            or state.enrollment_revocation_confirmed
            or state.node_id is not None
            or state.mission_admitted
            or state.mission_id is not None
        ):
            failures.append("preownership_milestone_contradiction")
        else:
            for field in (
                "node_revoked",
                "container_absent",
                "volumes_absent",
                "network_absent",
                "persistent_profile_volume_absent",
                "run_specific_images_absent",
            ):
                cleanup[field] = True
        attempt("runtime_plaintext_removal_failed", remove_plaintext)
        state.cleanup_failures = failures
        state.recovery_required = bool(failures)
        if state.recovery_required:
            return None
        return cleanup

    if state.node_id is not None:
        if api is None:
            failures.append("node_revocation_unavailable")
        else:

            def revoke() -> None:
                revoked = api.post(f"/nodes/{state.node_id}/revoke", {})
                if (
                    revoked.get("node_id") != state.node_id
                    or revoked.get("status") != "revoked"
                    or revoked.get("evidence_status") != "complete"
                ):
                    raise ProducerError("node_revocation_invalid")
                cleanup["node_revoked"] = True
                state.enrollment_revocation_confirmed = True

            attempt("node_revocation_failed", revoke)
    else:
        cleanup["node_revoked"] = True

    if state.node_id is not None and not state.enrollment_revocation_confirmed:
        attempt(
            "revocation_recovery_receipt_failed",
            lambda: _write_revocation_recovery_receipt(state),
        )
        attempt("fixed_node_stop_failed", stop_fixed_node)
        state.cleanup_failures = failures
        state.recovery_required = True
        return None

    if executor is None:
        if state.mutated:
            failures.append("runtime_resource_authority_unavailable")
        else:
            for field in (
                "container_absent",
                "volumes_absent",
                "network_absent",
                "persistent_profile_volume_absent",
                "run_specific_images_absent",
            ):
                cleanup[field] = True
    else:

        attempt("fixed_node_stop_failed", stop_fixed_node)

        def down_project() -> None:
            _require_success(
                executor.run(
                    state.plan.compose(
                        "--profile",
                        "node",
                        "--profile",
                        "hermes-node-bridge",
                        "down",
                        "--remove-orphans",
                        "--volumes",
                        fixed=True,
                    )
                ),
                "compose_cleanup_failed",
            )

        attempt("compose_cleanup_failed", down_project)

        for resource, field in (
            ("container", "container_absent"),
            ("volume", "volumes_absent"),
            ("network", "network_absent"),
        ):

            def prove_resource_absent(
                selected_resource: str = resource,
                selected_field: str = field,
            ) -> None:
                probe = executor.run(state.plan.resource_query(selected_resource))
                _require_success(probe, "cleanup_probe_failed")
                if probe.stdout.strip():
                    raise ProducerError("cleanup_residue_detected")
                cleanup[selected_field] = True

            attempt(f"{resource}_absence_proof_failed", prove_resource_absent)
        cleanup["persistent_profile_volume_absent"] = cleanup["volumes_absent"]

        images_reconciled = True
        try:
            _reconcile_bound_images_for_cleanup(state, executor)
        except (ProducerError, OSError, KeyboardInterrupt, ProducerSignal):
            failures.append("image_identity_reconciliation_failed")
            images_reconciled = False
        if images_reconciled:
            for reference in state.plan.images:
                bound = state.bound_images.get(reference)
                if bound is None:
                    continue

                def remove_image(
                    selected_image_id: str = bound.image_id,
                ) -> None:
                    _require_success(
                        executor.run(state.plan.image_remove(selected_image_id)),
                        "owned_image_removal_failed",
                    )

                attempt("owned_image_removal_failed", remove_image)

        image_proofs: list[bool] = []
        for reference in state.plan.images:

            def prove_image_absent(selected_reference: str = reference) -> None:
                probe = executor.run(state.plan.image_query(selected_reference))
                _require_success(probe, "owned_image_absence_probe_failed")
                if probe.stdout.strip():
                    raise ProducerError("owned_image_residue_detected")
                image_proofs.append(True)

            attempt("owned_image_absence_probe_failed", prove_image_absent)
        image_id_proofs: list[bool] = []
        for image_id in dict.fromkeys(
            identity.image_id for identity in state.bound_images.values()
        ):

            def prove_image_id_absent(
                selected_image_id: str = image_id,
            ) -> None:
                probe = executor.run(
                    state.plan.image_id_inspect(selected_image_id)
                )
                if (
                    probe.returncode == 1
                    and probe.stdout in _ABSENT_IMAGE_ID_STDOUTS
                    and probe.classification == "image_not_found"
                ):
                    image_id_proofs.append(True)
                    return
                if probe.returncode == 0 and probe.classification == "completed":
                    raise ProducerError("owned_image_id_residue_detected")
                raise ProducerError("owned_image_id_absence_probe_failed")

            try:
                prove_image_id_absent()
            except ProducerError as exc:
                failures.append(exc.code)
        cleanup["run_specific_images_absent"] = (
            len(image_proofs) == len(state.plan.images)
            and len(image_id_proofs) == len(state.bound_images)
        )

    attempt("runtime_plaintext_removal_failed", remove_plaintext)
    if state.gateway_journey is not None:
        for field in (
            "container_absent",
            "volumes_absent",
            "network_absent",
            "persistent_profile_volume_absent",
            "run_specific_images_absent",
            "runtime_plaintext_absent",
        ):
            state.gateway_journey[field] = cleanup[field]
    state.cleanup_failures = failures
    possible_live_resources = state.docker_mutation_started
    state.recovery_required = bool(failures) and (
        possible_live_resources or cleanup["runtime_plaintext_absent"] is not True
    )
    if state.recovery_required:
        return None
    return cleanup


def _write_revocation_recovery_receipt(state: ProducerState) -> None:
    if (
        state.node_id is None
        or not _NODE_ID.fullmatch(state.node_id)
        or state.enrollment_revocation_confirmed
    ):
        raise ProducerError("revocation_recovery_identity_invalid")
    document: JsonObject = {
        "schema_version": "1",
        "receipt_kind": "local_v1_o4_node_revocation_recovery",
        "run_id": state.run_id,
        "candidate_commit": state.candidate_commit,
        "candidate_tree": state.candidate_tree,
        "workspace_id": WORKSPACE_ID,
        "node_id": state.node_id,
        "compose_project": state.plan.project,
        "node_volume_name": f"{state.plan.project}_ithildin-node-state",
        "revocation_confirmed": False,
        "node_volume_retained": True,
        "anchored_runtime_retained": True,
        "reconciliation_required": True,
        "next_action": "confirm_node_revocation_before_destructive_cleanup",
        "release_allowed": False,
        "uat_complete": False,
    }
    content = (canonical_json(document) + "\n").encode()
    if len(content) > MAX_RECOVERY_RECEIPT_BYTES:
        raise ProducerError("revocation_recovery_receipt_too_large")
    state.receipts.write(REVOCATION_RECOVERY_RECEIPT, content)
    if state.receipts.read(
        REVOCATION_RECOVERY_RECEIPT,
        maximum=MAX_RECOVERY_RECEIPT_BYTES,
    ) != content:
        raise ProducerError("revocation_recovery_receipt_invalid")
    state.revocation_recovery_receipt_written = True


def _build_receipt(state: ProducerState) -> JsonObject:
    if (
        state.image_inventory is None
        or state.license_inventory is None
        or state.image_inventory_digest is None
        or state.license_inventory_digest is None
        or set(state.inspected_images) != set(state.plan.images)
        or state.snapshot is None
    ):
        raise ProducerError("build_inventory_incomplete")
    profile = state.snapshot.json_object("deploy/hermes-node-bridge/profile.json")
    hermes = cast(JsonObject, profile["hermes"])
    platforms = cast(JsonObject, hermes["platform_digests"])
    platform = _single_image_platform(state)
    bridge, node = state.plan.images[3], state.plan.images[2]
    return {
        "candidate_commit": state.candidate_commit,
        "candidate_tree": state.candidate_tree,
        "clean_before_bridge_build": state.clean_before_bridge_build,
        "clean_after_bridge_build": state.clean_after_bridge_build,
        "clean_before_node_build": state.clean_before_node_build,
        "clean_after_node_build": state.clean_after_node_build,
        "bridge_source_digest": state.snapshot.source_digest(
            tuple(
                str(path.relative_to(ROOT))
                for path in assembler_module.BRIDGE_SOURCE_PATHS
            )
        ),
        "node_source_digest": state.snapshot.source_digest(
            tuple(
                str(path.relative_to(ROOT))
                for path in assembler_module.NODE_SOURCE_PATHS
            )
        ),
        "dependency_lock_digest": state.snapshot.file_digest("uv.lock"),
        "hermes_oci_index_digest": hermes["oci_index_digest"],
        "hermes_platform_digest": platforms[platform],
        "profile_digest": sha256_digest(profile),
        "bridge_image_digest": state.inspected_images[bridge],
        "node_image_digest": state.inspected_images[node],
        "platform": platform,
        "image_artifact_inventory_digest": state.image_inventory_digest,
        "license_source_inventory_digest": state.license_inventory_digest,
    }


def _single_image_platform(state: ProducerState) -> str:
    if state.image_platform not in {"linux/amd64", "linux/arm64"}:
        raise ProducerError("image_platform_unavailable")
    return state.image_platform


def _compose_override(state: ProducerState) -> str:
    if state.snapshot is None:
        raise ProducerError("candidate_snapshot_unavailable")
    api_image, ui_image, node_image, hermes_image = state.plan.images
    root = state.runtime.path
    candidate = state.snapshot.path
    return f"""services:
  ithildin-api:
    image: {api_image}
    volumes:
      - type: bind
        source: {candidate / "tool-manifests.lock.json"}
        target: /app/tool-manifests.lock.json
        read_only: true
      - type: bind
        source: {candidate / "tool-manifests"}
        target: /app/tool-manifests
        read_only: true
      - type: bind
        source: {candidate / "policies"}
        target: /app/policies
        read_only: true
      - type: bind
        source: {candidate / "principals"}
        target: /app/principals
        read_only: true
      - type: bind
        source: {candidate / "trusted-hosts"}
        target: /app/trusted-hosts
        read_only: true
      - type: bind
        source: {root / "authority/api-candidate.json"}
        target: /run/ithildin-authority/api-candidate.json
        read_only: true
      - type: bind
        source: {root / "empty-scripts"}
        target: /app/scripts
        read_only: true
      - type: bind
        source: {root / "workspaces"}
        target: /app/workspaces
      - type: bind
        source: {root / "var"}
        target: /app/var
      - type: bind
        source: {root / APPLICATION_STARTUP_STATUS_DIRECTORY}
        target: /run/ithildin-startup
        read_only: false
  ithildin-ui:
    image: {ui_image}
  ithildin-node:
    image: {node_image}
  hermes:
    image: {hermes_image}
"""


def _validate_merged_compose_config(
    result: CommandResult,
    state: ProducerState,
    *,
    fixed: bool,
) -> None:
    if result.returncode != 0 or len(result.stdout.encode()) > MAX_LICENSE_BYTES:
        raise ProducerError("merged_compose_config_invalid")
    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ProducerError("merged_compose_config_invalid") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("services"), dict):
        raise ProducerError("merged_compose_config_invalid")
    services = cast(dict[str, Any], raw["services"])
    if state.snapshot is None:
        raise ProducerError("candidate_snapshot_unavailable")
    candidate = state.snapshot.path
    runtime = state.runtime.path
    expected_binds = {
        "/app/tool-manifests.lock.json": candidate / "tool-manifests.lock.json",
        "/app/tool-manifests": candidate / "tool-manifests",
        "/app/policies": candidate / "policies",
        "/app/principals": candidate / "principals",
        "/app/trusted-hosts": candidate / "trusted-hosts",
        "/run/ithildin-authority/api-candidate.json": (
            runtime / "authority/api-candidate.json"
        ),
        "/app/scripts": runtime / "empty-scripts",
        "/app/workspaces": runtime / "workspaces",
        "/app/var": runtime / "var",
        "/run/ithildin-startup": (
            runtime / APPLICATION_STARTUP_STATUS_DIRECTORY
        ),
    }
    observed_binds: dict[str, Path] = {}
    named_volume_targets: set[tuple[str, str]] = set()
    build_services = {"ithildin-api", "ithildin-ui", "ithildin-node"}
    if fixed:
        build_services.add("hermes")
    for service_name, service_raw in services.items():
        if not isinstance(service_name, str) or not isinstance(service_raw, dict):
            raise ProducerError("merged_compose_config_invalid")
        service = cast(dict[str, Any], service_raw)
        if (
            service_name == "ithildin-node"
            and service.get("tmpfs") != list(NODE_TMPFS)
        ):
            raise ProducerError("merged_compose_node_tmpfs_invalid")
        build = service.get("build")
        if service_name in build_services:
            if not isinstance(build, dict):
                raise ProducerError("merged_compose_build_path_invalid")
            context = build.get("context")
            dockerfile = build.get("dockerfile")
            if (
                not isinstance(context, str)
                or Path(context) != candidate
                or not isinstance(dockerfile, str)
            ):
                raise ProducerError("merged_compose_build_path_invalid")
            dockerfile_path = Path(dockerfile)
            if not dockerfile_path.is_absolute():
                dockerfile_path = candidate / dockerfile_path
            if not _path_within(dockerfile_path, candidate):
                raise ProducerError("merged_compose_build_path_invalid")
        volumes = service.get("volumes", [])
        if not isinstance(volumes, list):
            raise ProducerError("merged_compose_mount_invalid")
        for volume_raw in volumes:
            if not isinstance(volume_raw, dict):
                raise ProducerError("merged_compose_mount_invalid")
            volume = cast(dict[str, Any], volume_raw)
            volume_type = volume.get("type")
            source = volume.get("source")
            target = volume.get("target")
            if not isinstance(source, str) or not isinstance(target, str):
                raise ProducerError("merged_compose_mount_invalid")
            if volume_type == "bind":
                source_path = Path(source)
                expected = expected_binds.get(target)
                if (
                    service_name != "ithildin-api"
                    or expected is None
                    or source_path != expected
                    or not (
                        _path_within(source_path, runtime)
                        or _path_within(source_path, candidate)
                    )
                ):
                    raise ProducerError("merged_compose_host_path_invalid")
                if (
                    target == "/run/ithildin-startup"
                    and volume.get("read_only") is not False
                ):
                    raise ProducerError("merged_compose_mount_invalid")
                if target in observed_binds:
                    raise ProducerError("merged_compose_mount_invalid")
                observed_binds[target] = source_path
            elif volume_type == "volume":
                if source != "ithildin-node-state":
                    raise ProducerError("merged_compose_named_volume_invalid")
                named_volume_targets.add((service_name, target))
            else:
                raise ProducerError("merged_compose_mount_invalid")
    expected_named = {("ithildin-node", "/var/lib/ithildin-node")}
    if fixed:
        expected_named.add(("hermes", "/run/ithildin-node"))
    if observed_binds != expected_binds or named_volume_targets != expected_named:
        raise ProducerError("merged_compose_mount_set_invalid")


def _validate_command(
    command: tuple[str, ...],
    *,
    hermes: bool,
    inspected_image_ids: frozenset[str] = frozenset(),
    bound_container_ids: frozenset[str] = frozenset(),
) -> None:
    if len(command) < 3 or command[:2] != ("docker", "--config"):
        raise ProducerError("subprocess_command_not_allowed")
    config = Path(command[2])
    if (
        config.name != "docker-config"
        or config.parent.parent != RUNTIME_BASE
        or not _RUN_ID.fullmatch(config.parent.name)
    ):
        raise ProducerError("subprocess_command_not_allowed")
    plan = ComposePlan(config.parent.name, config.parent)
    allowed, hermes_command = _exact_command_vocabulary(
        plan,
        inspected_image_ids=inspected_image_ids,
        bound_container_ids=bound_container_ids,
    )
    if hermes:
        if command == hermes_command:
            return
        raise ProducerError("subprocess_command_not_allowed")
    if command not in allowed:
        raise ProducerError("subprocess_command_not_allowed")


def _exact_command_vocabulary(
    plan: ComposePlan,
    *,
    inspected_image_ids: frozenset[str],
    bound_container_ids: frozenset[str],
) -> tuple[set[tuple[str, ...]], tuple[str, ...]]:
    allowed = {
        plan.daemon_version(),
        plan.compose_version(),
        plan.compose("--profile", "node", "config", "--quiet"),
        plan.compose(
            "--profile",
            "node",
            "config",
            "--no-interpolate",
            "--format",
            "json",
        ),
        plan.compose(
            "--profile",
            "node",
            "--profile",
            "hermes-node-bridge",
            "config",
            "--quiet",
            fixed=True,
        ),
        plan.compose(
            "--profile",
            "node",
            "--profile",
            "hermes-node-bridge",
            "config",
            "--no-interpolate",
            "--format",
            "json",
            fixed=True,
        ),
        plan.compose(
            "--profile",
            "node",
            "build",
            "ithildin-api",
            "ithildin-ui",
            "ithildin-node",
        ),
        plan.compose(
            "--profile",
            "hermes-node-bridge",
            "build",
            "hermes",
            fixed=True,
        ),
        plan.compose("up", "--detach", "--wait", "ithildin-api", "ithildin-ui"),
        plan.base_service_start_diagnostic(),
        plan.api_container_id_query(),
        plan.fixed_node_container_id_query(),
        plan.compose(
            "--profile",
            "node",
            "run",
            "--rm",
            "-T",
            "--no-deps",
            "ithildin-node",
            "enroll",
            "--api-url",
            "http://ithildin-api:8000",
            "--state",
            "/var/lib/ithildin-node/state.json",
            "--node-version",
            NODE_VERSION,
            "--runner-adapter",
            "hermes",
            "--deployment-topology",
            "docker_sidecar",
            "--enrollment-code-stdin",
        ),
        plan.compose(
            "--profile",
            "node",
            "up",
            "--detach",
            "--no-deps",
            "ithildin-node",
        ),
        plan.compose("--profile", "node", "stop", "ithildin-node"),
        plan.compose(
            "--profile",
            "node",
            "up",
            "--detach",
            "--no-deps",
            "--wait",
            "ithildin-node",
            fixed=True,
        ),
        plan.compose(
            "--profile",
            "node",
            "cp",
            "ithildin-node:/var/lib/ithildin-node/mission-receipt.json",
            str(plan.runtime / "copied-receipt/node-mission-receipt.json"),
            fixed=True,
        ),
        plan.compose(
            "--profile",
            "node",
            "stop",
            "ithildin-node",
            fixed=True,
        ),
        plan.compose(
            "--profile",
            "node",
            "--profile",
            "hermes-node-bridge",
            "down",
            "--remove-orphans",
            "--volumes",
            fixed=True,
        ),
    }
    for resource in ("container", "volume", "network"):
        allowed.add(plan.resource_query(resource))
    for image in plan.images:
        allowed.add(plan.image_query(image))
        allowed.add(plan.image_inspect(image))
    for image_id in inspected_image_ids:
        if _DIGEST.fullmatch(image_id):
            allowed.add(plan.image_remove(image_id))
            allowed.add(plan.image_ancestor_containers(image_id))
            allowed.add(plan.image_id_inspect(image_id))
    for container_id in bound_container_ids:
        if _CONTAINER_ID.fullmatch(container_id):
            allowed.add(plan.api_container_state_inspect(container_id))
            allowed.add(plan.fixed_node_container_state_inspect(container_id))
    hermes_command = plan.compose(
        "--profile",
        "hermes-node-bridge",
        "run",
        "--rm",
        "-T",
        "--no-deps",
        "hermes",
        fixed=True,
    )
    return allowed, hermes_command


def _validate_api_operation(
    method: str,
    path: str,
    payload: JsonObject | None,
    *,
    admin: bool,
) -> None:
    if urllib.parse.urlsplit(path).scheme or not path.startswith("/"):
        raise ProducerError("api_operation_not_allowed")
    if method == "GET" and path == "/healthz" and not admin and payload is None:
        return
    if method == "GET" and path in {"/system/status", "/workspaces"} and admin:
        return
    if method == "GET" and admin and (
        re.fullmatch(r"/nodes/node_[0-9a-f]{32}", path)
        or re.fullmatch(r"/missions/mission_[0-9a-f]{32}", path)
        or re.fullmatch(r"/runs/run_[0-9a-f]{32}", path)
    ):
        return
    if method == "POST" and admin and path == "/nodes/enrollment-codes":
        if (
            payload is not None
            and set(payload) == {"workspace_id", "display_name"}
            and payload.get("workspace_id") == WORKSPACE_ID
            and isinstance(payload.get("display_name"), str)
            and re.fullmatch(
                r"Local v1 O4 Node [0-9a-f]{8}",
                cast(str, payload["display_name"]),
            )
        ):
            return
    if method == "POST" and admin and path == "/missions":
        if (
            payload is not None
            and set(payload)
            == {
                "target_node_id",
                "mission_template_id",
                "requested_timeout_seconds",
                "client_request_id",
            }
            and isinstance(payload.get("target_node_id"), str)
            and _NODE_ID.fullmatch(cast(str, payload["target_node_id"]))
            and payload.get("mission_template_id") == "synthetic_read_review_v1"
            and payload.get("requested_timeout_seconds") == 300
            and isinstance(payload.get("client_request_id"), str)
            and re.fullmatch(
                r"lv1-o4-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}",
                cast(str, payload["client_request_id"]),
            )
        ):
            return
    if method == "POST" and admin and re.fullmatch(
        r"/nodes/node_[0-9a-f]{32}/configurations", path
    ):
        if payload == {
            "minimum_node_version": NODE_VERSION,
            "heartbeat_interval_seconds": 15,
            "offline_posture": "deny_governed_actions",
            "evidence_buffer_max_events": 1000,
            "validity_seconds": 3600,
        }:
            return
    if method == "POST" and admin and re.fullmatch(
        r"/nodes/node_[0-9a-f]{32}/revoke", path
    ):
        if payload == {}:
            return
    raise ProducerError("api_operation_not_allowed")


def _reject_ambient_authority(environment: dict[str, str]) -> None:
    rejected = sorted(
        name
        for name, value in environment.items()
        if value and _AMBIENT_AUTHORITY.fullmatch(name)
    )
    if rejected:
        raise ProducerError("ambient_authority_present")


def _require_ports_available(ports: tuple[int, ...]) -> None:
    held: list[socket.socket] = []
    try:
        for port in ports:
            probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
            probe.bind(("127.0.0.1", port))
            held.append(probe)
    except OSError as exc:
        raise ProducerError("required_loopback_port_unavailable") from exc
    finally:
        for probe in held:
            probe.close()


def _prove_local_docker_socket(
    candidates: tuple[Path, ...] | None = None,
) -> str:
    effective = candidates or (
        Path("/var/run/docker.sock"),
        Path("/run/docker.sock"),
        Path.home() / ".docker/run/docker.sock",
    )
    sockets: dict[tuple[int, int], Path] = {}
    for candidate in effective:
        try:
            details = candidate.stat()
        except OSError:
            continue
        if stat.S_ISSOCK(details.st_mode):
            sockets.setdefault((details.st_dev, details.st_ino), candidate)
    if not sockets:
        raise ProducerError("local_docker_socket_unavailable")
    if len(sockets) != 1:
        raise ProducerError("local_docker_socket_ambiguous")
    return f"unix://{next(iter(sockets.values()))}"


def _require_success(result: CommandResult, code: str) -> None:
    if result.returncode != 0:
        raise ProducerError(code)
    if _FORBIDDEN_OUTPUT.search(result.stdout):
        raise ProducerError("subprocess_output_rejected")


def _create_candidate_snapshot(
    root: PrivateDirectory,
    candidate_commit: str,
    candidate_tree: str,
) -> CandidateSnapshot:
    return CandidateSnapshot.create(root, candidate_commit, candidate_tree)


def _candidate_snapshot_entries(
    candidate_commit: str,
    candidate_tree: str,
) -> dict[str, tuple[int, bytes]]:
    if (
        not _COMMIT.fullmatch(candidate_commit)
        or not _COMMIT.fullmatch(candidate_tree)
        or _git("rev-parse", f"{candidate_commit}^{{tree}}") != candidate_tree
    ):
        raise ProducerError("candidate_snapshot_identity_invalid")
    listing = _run_git_bytes(
        ("ls-tree", "-rz", "--full-tree", candidate_commit),
        maximum=MAX_SNAPSHOT_BYTES,
    )
    selected: dict[str, tuple[str, str]] = {}
    license_family: list[str] = []
    for record in listing.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            raw_mode, raw_type, raw_oid = metadata.decode("ascii").split(" ", 2)
            relative = raw_path.decode("utf-8")
        except (ValueError, UnicodeError) as exc:
            raise ProducerError("candidate_snapshot_listing_invalid") from exc
        _relative_parts(relative)
        if Path(relative).name.startswith(("LICENSE", "NOTICE", "COPYING")):
            license_family.append(relative)
        if relative not in _SNAPSHOT_FILES and not relative.startswith(
            _SNAPSHOT_PREFIXES
        ):
            continue
        if (
            raw_type != "blob"
            or raw_mode not in {"100644", "100755"}
            or not re.fullmatch(r"[0-9a-f]{40}", raw_oid)
        ):
            raise ProducerError("candidate_snapshot_entry_invalid")
        selected[relative] = (raw_mode, raw_oid)
    if not _SNAPSHOT_REQUIRED.issubset(selected) or license_family:
        raise ProducerError("candidate_snapshot_scope_drift")
    entries: dict[str, tuple[int, bytes]] = {}
    total = 0
    for relative, (raw_mode, raw_oid) in sorted(selected.items()):
        content = _run_git_bytes(
            ("cat-file", "blob", raw_oid),
            maximum=MAX_SNAPSHOT_FILE_BYTES,
        )
        git_material = f"blob {len(content)}\0".encode() + content
        if hashlib.sha1(git_material).hexdigest() != raw_oid:  # noqa: S324
            raise ProducerError("candidate_snapshot_blob_digest_invalid")
        total += len(content)
        if total > MAX_SNAPSHOT_BYTES:
            raise ProducerError("candidate_snapshot_too_large")
        entries[relative] = (
            0o100755 if raw_mode == "100755" else 0o100644,
            content,
        )
    return entries


def _git(*arguments: str) -> str:
    try:
        completed = subprocess.run(
            ("git", *arguments),
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise ProducerError("candidate_git_unavailable") from exc
    if completed.returncode != 0:
        raise ProducerError("candidate_git_unavailable")
    return completed.stdout.strip()


def _run_git_bytes(arguments: tuple[str, ...], *, maximum: int) -> bytes:
    try:
        completed = subprocess.run(
            ("git", *arguments),
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError as exc:
        raise ProducerError("candidate_git_unavailable") from exc
    if completed.returncode != 0 or len(completed.stdout) > maximum:
        raise ProducerError("candidate_git_object_unavailable")
    return completed.stdout


def _normalized_error(exc: BaseException) -> ProducerError:
    if isinstance(exc, ProducerError):
        return exc
    if isinstance(exc, (KeyboardInterrupt, ProducerSignal)):
        return ProducerError("interrupted")
    return ProducerError("unexpected_failure")


def _write_failure_diagnostic(
    receipts: PrivateDirectory,
    *,
    state: ProducerState | None,
    outward_failure_code: str,
    primary_failure_code: str | None,
) -> None:
    identities: list[JsonObject] = []
    cleanup_failures: list[str] = []
    if state is not None:
        cleanup_failures = list(dict.fromkeys(state.cleanup_failures))
        for reference in state.plan.images:
            identity = state.bound_images.get(reference)
            if identity is None:
                continue
            identities.append(
                {
                    "reference": identity.reference,
                    "image_id": identity.image_id,
                    "project": identity.project,
                    "service": identity.service,
                    "compose_version": identity.compose_version,
                    "platform": identity.platform,
                    "ordered_layer_digests": list(identity.layers),
                }
            )
    diagnostic: JsonObject = {
        "schema_version": "1",
        "record_type": "local_v1_lv1_003_o4_producer_failure_diagnostic",
        "outward_failure_code": outward_failure_code,
        "primary_failure_code": primary_failure_code,
        "cleanup_failure_codes": cast(list[Any], cleanup_failures),
        "recovery_required": outward_failure_code == "recovery_required",
        "highest_completed_stage": max(state.stages, default=0)
        if state is not None
        else 0,
        "base_build_completed": state.base_build_completed
        if state is not None
        else False,
        "bridge_build_completed": state.bridge_build_completed
        if state is not None
        else False,
        "bound_inspected_image_identities": cast(list[Any], identities),
    }
    if state is not None and state.base_service_start_diagnostic is not None:
        diagnostic["base_service_start_diagnostic"] = (
            state.base_service_start_diagnostic
        )
    if state is not None and state.fixed_node_start_diagnostic is not None:
        diagnostic["fixed_node_start_diagnostic"] = (
            state.fixed_node_start_diagnostic
        )
    try:
        receipts.write(
            "diagnostic.json",
            (canonical_json(diagnostic) + "\n").encode(),
        )
    except (OSError, ProducerError, KeyboardInterrupt, ProducerSignal):
        pass


def _quarantine_receipts(receipts: PrivateDirectory, code: str) -> None:
    relative = "disposition.json"
    try:
        receipts.read("disposition.json")
        relative = "failure-disposition.json"
    except (KeyError, OSError, ProducerError):
        pass
    try:
        receipts.write(
            relative,
            (
                canonical_json(
                    {
                        "status": "quarantined_not_published",
                        "failure_code": code,
                        "release_allowed": False,
                        "uat_complete": False,
                    }
                )
                + "\n"
            ).encode(),
        )
    except (OSError, ProducerError, KeyboardInterrupt, ProducerSignal):
        pass


def _path_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _open_relative_directory(parent: int, relative: str) -> int:
    descriptor = os.dup(parent)
    try:
        for part in _relative_parts(relative):
            child = os.open(part, _directory_flags(), dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _open_relative_file(parent: int, relative: str) -> int:
    parts = _relative_parts(relative)
    descriptor = os.dup(parent)
    try:
        for part in parts[:-1]:
            child = os.open(part, _directory_flags(), dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        result = os.open(parts[-1], _file_flags(os.O_RDONLY), dir_fd=descriptor)
    finally:
        os.close(descriptor)
    return result


def _read_all(descriptor: int, maximum: int) -> bytes:
    chunks: list[bytes] = []
    observed = 0
    while True:
        chunk = os.read(descriptor, min(65_536, maximum + 1 - observed))
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)
        observed += len(chunk)
        if observed > maximum:
            raise ProducerError("private_file_too_large")


def _write_private_at(parent: int, name: str, content: bytes) -> None:
    descriptor = -1
    try:
        descriptor = os.open(
            name,
            _file_flags(os.O_WRONLY | os.O_CREAT | os.O_EXCL),
            0o600,
            dir_fd=parent,
        )
        view = memoryview(content)
        while view:
            view = view[os.write(descriptor, view) :]
        os.fsync(descriptor)
    except OSError as exc:
        raise ProducerError("private_file_write_failed") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _observe_exact_source(state: ProducerState) -> None:
    if (
        _git("rev-parse", "HEAD") != state.candidate_commit
        or _git("rev-parse", "HEAD^{tree}") != state.candidate_tree
        or _git("status", "--porcelain=v1", "--untracked-files=all")
    ):
        raise ProducerError("source_candidate_changed")


def current_clean_candidate() -> tuple[str, str]:
    commit = _git("rev-parse", "HEAD")
    tree = _git("rev-parse", "HEAD^{tree}")
    if (
        not _COMMIT.fullmatch(commit)
        or not _COMMIT.fullmatch(tree)
        or _git("status", "--porcelain=v1", "--untracked-files=all")
    ):
        raise ProducerError("source_candidate_not_clean")
    return commit, tree


def _directory_flags() -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    return flags


def _file_flags(base: int) -> int:
    flags = base
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    return flags


def _owner_directory(details: os.stat_result) -> bool:
    return (
        stat.S_ISDIR(details.st_mode)
        and stat.S_IMODE(details.st_mode) == 0o700
        and details.st_uid == os.geteuid()
        and details.st_gid == os.getegid()
    )


def _owner_snapshot_directory(details: os.stat_result) -> bool:
    return (
        stat.S_ISDIR(details.st_mode)
        and stat.S_IMODE(details.st_mode) == 0o500
        and details.st_uid == os.geteuid()
        and details.st_gid == os.getegid()
    )


def _owned_nonwritable_directory(details: os.stat_result) -> bool:
    return (
        stat.S_ISDIR(details.st_mode)
        and details.st_mode & 0o022 == 0
        and details.st_uid == os.geteuid()
        and details.st_gid == os.getegid()
    )


def _enumerate_snapshot_tree(
    descriptor: int,
    prefix: str = "",
) -> tuple[set[str], set[str]]:
    directories: set[str] = set()
    files: set[str] = set()
    for name in sorted(os.listdir(descriptor)):
        if name in {"", ".", ".."} or "/" in name:
            raise ProducerError("candidate_snapshot_changed")
        relative = f"{prefix}/{name}" if prefix else name
        try:
            details = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
        except OSError as exc:
            raise ProducerError("candidate_snapshot_changed") from exc
        if stat.S_ISDIR(details.st_mode):
            if not _owner_snapshot_directory(details):
                raise ProducerError("candidate_snapshot_changed")
            directories.add(relative)
            child = os.open(name, _directory_flags(), dir_fd=descriptor)
            try:
                nested_directories, nested_files = _enumerate_snapshot_tree(
                    child,
                    relative,
                )
            finally:
                os.close(child)
            directories.update(nested_directories)
            files.update(nested_files)
        elif stat.S_ISREG(details.st_mode):
            if (
                stat.S_IMODE(details.st_mode) not in {0o400, 0o500}
                or details.st_uid != os.geteuid()
                or details.st_gid != os.getegid()
            ):
                raise ProducerError("candidate_snapshot_changed")
            files.add(relative)
        else:
            raise ProducerError("candidate_snapshot_changed")
    return directories, files


def _relative_parts(relative: str) -> tuple[str, ...]:
    path = Path(relative)
    if (
        not relative
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ProducerError("runtime_relative_path_invalid")
    return path.parts


def _remove_contents(descriptor: int) -> None:
    os.fchmod(descriptor, 0o700)
    for name in os.listdir(descriptor):
        details = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
        if stat.S_ISDIR(details.st_mode):
            child = os.open(name, _directory_flags(), dir_fd=descriptor)
            try:
                _remove_contents(child)
            finally:
                os.close(child)
            os.rmdir(name, dir_fd=descriptor)
        else:
            os.unlink(name, dir_fd=descriptor)


@contextmanager
def _controlled_signals() -> Iterator[None]:
    watched = tuple(
        value
        for value in (signal.SIGTERM, getattr(signal, "SIGHUP", None))
        if isinstance(value, signal.Signals)
    )
    previous = {value: signal.getsignal(value) for value in watched}

    def interrupt(signum: int, frame: Any) -> None:
        del frame
        raise ProducerSignal(signal.Signals(signum).name.lower())

    try:
        for value in watched:
            signal.signal(value, interrupt)
        yield
    finally:
        for value, handler in previous.items():
            signal.signal(value, handler)


def main() -> int:
    try:
        candidate = current_clean_candidate()
        with _controlled_signals():
            report_root = run_producer(
                gate=ExactGate(),
                runtime_factory=DefaultRuntimeFactory(),
                executor_factory=DefaultExecutorFactory(),
                api_factory=DefaultApiFactory(),
                provider=HostOllamaProvider(),
                assembler=ClosedAssembler(),
                candidate=candidate,
            )
    except (
        ProducerError,
        authorization_gate.O4ExecutionAuthorizationError,
        ProducerSignal,
    ) as exc:
        code = (
            exc.code
            if isinstance(exc, ProducerError)
            else "interrupted"
            if isinstance(exc, ProducerSignal)
            else str(exc)
        )
        print(f"LV1-003 O4 producer refused: {code}", file=sys.stderr)
        return 1
    print(f"LV1-003 O4 evidence assembled: {report_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

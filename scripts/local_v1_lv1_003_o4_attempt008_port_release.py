"""One-shot exact-project API/UI port release for retained O4 Attempt 008.

Importing this module performs no Docker, socket, or filesystem mutation.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import socket
import stat
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

from ithildin_schemas import JsonObject, JsonValue, canonical_json

ROOT = Path(__file__).resolve().parents[1]
RECOVERY_ID = "LV1-003-O4-ATTEMPT-008-PORT-RELEASE-002"
PREVIOUS_RECOVERY_ID = "LV1-003-O4-ATTEMPT-008-PORT-RELEASE-001"
PARENT_COMMIT = "1e57990b82d3c912bf158e0b06cbfb0ca417bb33"
PARENT_TREE = "b5fffdcc0b91f7d798763a0f1381fe78831ca22a"
RUN_ID = "20260726T001909Z-d801f37b"
PROJECT = "ithildin-local-v1-o4-d801f37b"
RUN_TARGET = "local-v1-lv1-003-o4-attempt008-port-release-run"
CHECK_TARGET = "local-v1-lv1-003-o4-attempt008-port-release-check"
MODULE_COMMAND = (
    "uv run python -m scripts.local_v1_lv1_003_o4_attempt008_port_release"
)
AUTHORIZATION_JSON = Path(
    "docs/codex/local-v1-lv1-003-o4-attempt008-port-release-authorization.json"
)
AUTHORIZATION_DOCUMENT = Path(
    "docs/codex/local-v1-lv1-003-o4-attempt008-port-release-authorization.md"
)
PORT_RELEASE_ATTEMPT_001_DISPOSITION_JSON = Path(
    "docs/codex/local-v1-lv1-003-o4-attempt008-port-release-attempt-001-disposition.json"
)
PORT_RELEASE_ATTEMPT_001_DISPOSITION_DOCUMENT = Path(
    "docs/codex/local-v1-lv1-003-o4-attempt008-port-release-attempt-001-disposition.md"
)
ATTEMPT_DISPOSITION_JSON = Path(
    "docs/codex/local-v1-lv1-003-o4-attempt-008-disposition.json"
)
ATTEMPT_DISPOSITION_DOCUMENT = Path(
    "docs/codex/local-v1-lv1-003-o4-attempt-008-disposition.md"
)
ATTEMPT_DISPOSITION_JSON_DIGEST = (
    "sha256:5ba9f74000174d7498feedc0c5f1d9acc8538ab5d34416d19650f8efc5bceb62"
)
ATTEMPT_DISPOSITION_DOCUMENT_DIGEST = (
    "sha256:6d993a2bfa41b649cb3eb78fe6b659edb8ec066dc8d5857a860627bdd21a5b7e"
)
RETAINED_ROOT = Path("var/local-v1-lv1-003-o4-receipts") / RUN_ID
PREVIOUS_RECEIPT_ROOT = (
    Path("var/local-v1-lv1-003-o4-reconciliation-receipts")
    / "attempt-008-port-release-001"
)
RECEIPT_ROOT = (
    Path("var/local-v1-lv1-003-o4-reconciliation-receipts")
    / "attempt-008-port-release-002"
)
CONSUMED_RECEIPT = "consumed.json"
DISPOSITION_RECEIPT = "disposition.json"
JOURNAL_DIRECTORY = "journal"
ATTEMPT_001_CONSUMED_SIZE = 913
ATTEMPT_001_CONSUMED_DIGEST = (
    "sha256:ba871180cad089f4a325060167ea5bf6fa800010a0f12562b63d00e32ea7de49"
)
ATTEMPT_001_JOURNAL_SIZE = 666
ATTEMPT_001_JOURNAL_DIGEST = (
    "sha256:a8f8bbbc670d68392d0376d14a1754a81d9d556fa155699a95006f3d368a1ec3"
)
ATTEMPT_001_DISPOSITION_SIZE = 1_172
ATTEMPT_001_DISPOSITION_DIGEST = (
    "sha256:e87493b5e5aa2ff596180371bdb6ebb68172790cf4f769176af269a47b3098b1"
)
MAX_DOCKER_OUTPUT_BYTES = 32_768
MAX_HASH_BYTES = 131_072
MAX_JOURNAL_ENTRIES = 16
GIT_EXECUTABLE = Path("/usr/bin/git")
DOCKER_ALIAS = Path("/usr/local/bin/docker")
DOCKER_EXECUTABLE = Path(
    "/Applications/Docker.app/Contents/Resources/bin/docker"
)
GIT_OWNER = (0, 0)
DOCKER_OWNER = (501, 80)
DOCKER_EXECUTABLE_SIZE = 41_043_648
DOCKER_EXECUTABLE_DIGEST = (
    "sha256:f3f8d9217542c530d26070b6a1f498452f717eb61d5839ef38f9a0f5d48c2b05"
)
MAX_EXECUTABLE_BYTES = 64 * 1024 * 1024
SEALED_TEMP_PARENT = Path("/private/tmp")
SEALED_EXECUTABLE_NAME = "docker"
DIRECTORY_OPEN_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_CLOEXEC", 0)
)
AUTHORITY_ENVIRONMENT_KEYS = {
    "COMPOSE_PROJECT_NAME",
    "DOCKER_AUTH_CONFIG",
    "DOCKER_CERT_PATH",
    "DOCKER_CONFIG",
    "DOCKER_CONTEXT",
    "DOCKER_HOST",
    "DOCKER_TLS_VERIFY",
}
PROVIDER_ENVIRONMENT_PREFIXES = (
    "ANTHROPIC_",
    "AWS_",
    "AZURE_",
    "GCP_",
    "GEMINI_",
    "GOOGLE_",
    "HERMES_",
    "OLLAMA_",
    "OPENAI_",
    "REGISTRY_",
)
SECRET_ENVIRONMENT_MARKERS = (
    "ACCESS_KEY",
    "API_KEY",
    "CREDENTIAL",
    "PASSWORD",
    "PRIVATE_KEY",
    "SECRET",
    "TOKEN",
)
INSPECT_FORMAT = (
    '{{json .Id}}\t{{json .Image}}\t'
    '{{json (index .Config.Labels "com.docker.compose.project")}}\t'
    '{{json (index .Config.Labels "com.docker.compose.service")}}\t'
    "{{json .State.Running}}\t{{json .State.Status}}\t"
    "{{json .NetworkSettings.Ports}}"
)
CANDIDATE_PATH_ALLOWLIST = [
    "README.md",
    PORT_RELEASE_ATTEMPT_001_DISPOSITION_JSON.as_posix(),
    PORT_RELEASE_ATTEMPT_001_DISPOSITION_DOCUMENT.as_posix(),
    AUTHORIZATION_JSON.as_posix(),
    AUTHORIZATION_DOCUMENT.as_posix(),
    "scripts/local_v1_lv1_003_o4_attempt008_port_release.py",
    "tests/test_local_v1_lv1_003_o4_attempt008_port_release.py",
]
TRUE_AUTHORITY = {
    "retained_receipt_validation",
    "exact_project_container_inspection",
    "exact_api_ui_stop",
    "point_in_time_port_release_observation",
    "private_receipt_write",
}
FALSE_AUTHORITY = {
    "container_deletion",
    "volume_deletion",
    "network_deletion",
    "image_deletion",
    "runtime_deletion",
    "evidence_deletion",
    "node_revocation",
    "node_stop",
    "hermes_stop",
    "compose_use",
    "project_down",
    "generic_process_discovery",
    "generic_process_control",
    "generic_docker_queries",
    "provider_access",
    "credential_access",
    "new_governed_tool",
    "new_governed_power",
    "release",
    "promotion",
    "uat",
}


@dataclass(frozen=True)
class ServiceContract:
    service: str
    image_id: str
    container_port: str | None = None
    host_port: str | None = None


SERVICES = {
    item.service: item
    for item in (
        ServiceContract(
            "ithildin-api",
            "sha256:20edad55b1bc2a67f6aa02c164122cdfc54ef139c4628e9ed9043936b9114242",
            "8000/tcp",
            "8000",
        ),
        ServiceContract(
            "ithildin-ui",
            "sha256:c3f77a6d09fad1df44dbd2506a2b92ba437bb3d2fead2d43040019b2ff69a27c",
            "8080/tcp",
            "5173",
        ),
        ServiceContract(
            "ithildin-node",
            "sha256:74dcb8a496ce2780b23ac7947aa821094fc80688a35a2c4318302e48809c3390",
        ),
        ServiceContract(
            "hermes",
            "sha256:3eb87a25a51b1182882588f5271705886e9fcf660742ba9006d26d91f6555c3e",
        ),
    )
}


class PortReleaseError(RuntimeError):
    """Stable, non-reflective recovery refusal."""

    def __init__(self, code: str) -> None:
        if re.fullmatch(r"[a-z0-9_]{3,80}", code) is None:
            raise ValueError("unsafe port-release error code")
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str


@dataclass(frozen=True)
class ContainerProjection:
    container_id: str
    image_id: str
    service: str
    running: bool
    status: str
    ports: JsonObject


@dataclass(frozen=True)
class ExecutableIdentity:
    path: str
    device: int
    inode: int
    size: int
    modified_ns: int
    changed_ns: int
    mode: int
    uid: int
    gid: int
    digest: str


class Executor(Protocol):
    def read(self, command: tuple[str, ...]) -> CommandResult: ...

    def stop(self, service: str, command: tuple[str, ...]) -> CommandResult: ...


class SealedExecutableHandle(Protocol):
    @property
    def path(self) -> str: ...

    def verify(self) -> None: ...


@dataclass(frozen=True)
class Plan:
    docker_executable: str

    def __post_init__(self) -> None:
        path = Path(self.docker_executable)
        if (
            not path.is_absolute()
            or path.name != SEALED_EXECUTABLE_NAME
            or path == DOCKER_EXECUTABLE
            or path == DOCKER_ALIAS
        ):
            raise PortReleaseError("sealed_docker_executable_not_allowed")

    def query(self) -> tuple[str, ...]:
        return (
            self.docker_executable,
            "ps",
            "--all",
            "--quiet",
            "--no-trunc",
            "--filter",
            f"label=com.docker.compose.project={PROJECT}",
        )

    def inspect(self, container_id: str) -> tuple[str, ...]:
        if re.fullmatch(r"[0-9a-f]{64}", container_id) is None:
            raise PortReleaseError("container_id_not_allowed")
        return (
            self.docker_executable,
            "container",
            "inspect",
            "--format",
            INSPECT_FORMAT,
            container_id,
        )

    def stop_command(self, service: str, container_id: str) -> tuple[str, ...]:
        if service not in {"ithildin-api", "ithildin-ui"}:
            raise PortReleaseError("container_stop_not_allowed")
        if re.fullmatch(r"[0-9a-f]{64}", container_id) is None:
            raise PortReleaseError("container_stop_not_allowed")
        return (
            self.docker_executable,
            "container",
            "stop",
            "--time",
            "10",
            container_id,
        )


class SubprocessExecutor:
    """Binary, output-bounded adapter for the sealed command vocabulary."""

    def __init__(
        self,
        environment: dict[str, str],
        plan: Plan,
        sealed_executable: SealedExecutableHandle,
    ) -> None:
        if "PATH" in environment:
            raise PortReleaseError("docker_environment_not_isolated")
        self._environment = dict(environment)
        self._plan = plan
        self._sealed_executable = sealed_executable
        if self._sealed_executable.path != plan.docker_executable:
            raise PortReleaseError("sealed_docker_executable_not_allowed")
        self._sealed_executable.verify()
        self._known_ids: set[str] = set()
        self._stop_ids: set[str] = set()
        self._stop_targets: dict[str, str] = {}

    def bind_ids(self, container_ids: set[str]) -> None:
        if self._known_ids or any(
            re.fullmatch(r"[0-9a-f]{64}", value) is None
            for value in container_ids
        ):
            raise PortReleaseError("container_id_binding_invalid")
        self._known_ids = set(container_ids)

    def bind_stop_targets(self, container_ids: dict[str, str]) -> None:
        if (
            self._stop_targets
            or set(container_ids) != {"ithildin-api", "ithildin-ui"}
            or len(set(container_ids.values())) != 2
            or not set(container_ids.values()) <= self._known_ids
        ):
            raise PortReleaseError("container_stop_binding_invalid")
        self._stop_targets = dict(container_ids)

    def read(self, command: tuple[str, ...]) -> CommandResult:
        allowed = {self._plan.query()} | {
            self._plan.inspect(value) for value in self._known_ids
        }
        if command not in allowed:
            raise PortReleaseError("docker_read_command_not_allowed")
        return self._run(command, mutation=False)

    def stop(self, service: str, command: tuple[str, ...]) -> CommandResult:
        container_id = self._stop_targets.get(service)
        if (
            container_id is None
            or command != self._plan.stop_command(service, container_id)
            or container_id in self._stop_ids
        ):
            raise PortReleaseError("docker_stop_command_not_allowed")
        self._stop_ids.add(container_id)
        return self._run(command, mutation=True)

    def _run(self, command: tuple[str, ...], *, mutation: bool) -> CommandResult:
        self._sealed_executable.verify()
        try:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                stdout=(subprocess.DEVNULL if mutation else subprocess.PIPE),
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=(30.0 if mutation else 20.0),
                env=self._environment,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PortReleaseError("docker_command_unavailable") from exc
        self._sealed_executable.verify()
        raw = b"" if mutation else completed.stdout
        if len(raw) > MAX_DOCKER_OUTPUT_BYTES:
            raise PortReleaseError("docker_output_rejected")
        try:
            output = raw.decode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise PortReleaseError("docker_output_rejected") from exc
        return CommandResult(completed.returncode, output)

    def verify_final_identity(self) -> None:
        self._sealed_executable.verify()


def _sha256_bytes(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _digest(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate member")
        result[key] = value
    return result


def _load_closed_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_closed_object,
        )
    except (OSError, UnicodeError, ValueError) as exc:
        raise PortReleaseError("authorization_invalid") from exc
    if not isinstance(value, dict):
        raise PortReleaseError("authorization_invalid")
    return cast(dict[str, Any], value)


def _executable_identity(
    path: Path,
    *,
    owner: tuple[int, int],
    error_code: str,
    expected_size: int | None = None,
    expected_digest: str | None = None,
) -> ExecutableIdentity:
    descriptor = -1
    try:
        before = path.lstat()
        descriptor = os.open(
            path,
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0),
        )
        opened = os.fstat(descriptor)
        if opened.st_size > MAX_EXECUTABLE_BYTES:
            raise PortReleaseError(error_code)
        hasher = hashlib.sha256()
        remaining = opened.st_size
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            hasher.update(chunk)
            remaining -= len(chunk)
        post_read = os.fstat(descriptor)
        after = path.lstat()
    except OSError as exc:
        raise PortReleaseError(error_code) from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if (
        not stat.S_ISREG(before.st_mode)
        or not stat.S_ISREG(opened.st_mode)
        or stat.S_IMODE(opened.st_mode) != 0o755
        or opened.st_uid != owner[0]
        or opened.st_gid != owner[1]
        or stat.S_IMODE(opened.st_mode) & 0o022
        or not _same_inode(before, opened)
        or not _same_inode(opened, post_read)
        or not _same_inode(post_read, after)
        or opened.st_size != post_read.st_size
        or post_read.st_size != after.st_size
        or opened.st_mtime_ns != post_read.st_mtime_ns
        or post_read.st_mtime_ns != after.st_mtime_ns
        or opened.st_ctime_ns != post_read.st_ctime_ns
        or post_read.st_ctime_ns != after.st_ctime_ns
        or remaining
        or (expected_size is not None and opened.st_size != expected_size)
        or (
            expected_digest is not None
            and "sha256:" + hasher.hexdigest() != expected_digest
        )
    ):
        raise PortReleaseError(error_code)
    return ExecutableIdentity(
        path.as_posix(),
        opened.st_dev,
        opened.st_ino,
        opened.st_size,
        opened.st_mtime_ns,
        opened.st_ctime_ns,
        stat.S_IMODE(opened.st_mode),
        opened.st_uid,
        opened.st_gid,
        "sha256:" + hasher.hexdigest(),
    )


def _validate_git_executable() -> ExecutableIdentity:
    return _executable_identity(
        GIT_EXECUTABLE,
        owner=GIT_OWNER,
        error_code="git_executable_invalid",
    )


def _validate_docker_executable() -> ExecutableIdentity:
    try:
        alias_before = DOCKER_ALIAS.lstat()
        target = os.readlink(DOCKER_ALIAS)
        alias_after = DOCKER_ALIAS.lstat()
    except OSError as exc:
        raise PortReleaseError("docker_executable_invalid") from exc
    if (
        not stat.S_ISLNK(alias_before.st_mode)
        or stat.S_IMODE(alias_before.st_mode) != 0o755
        or alias_before.st_uid != GIT_OWNER[0]
        or alias_before.st_gid != GIT_OWNER[1]
        or target != DOCKER_EXECUTABLE.as_posix()
        or not _same_inode(alias_before, alias_after)
        or alias_before.st_mtime_ns != alias_after.st_mtime_ns
        or alias_before.st_uid != alias_after.st_uid
        or alias_before.st_gid != alias_after.st_gid
        or stat.S_IMODE(alias_before.st_mode)
        != stat.S_IMODE(alias_after.st_mode)
    ):
        raise PortReleaseError("docker_executable_invalid")
    resolved_inventory = {DOCKER_EXECUTABLE.as_posix(), Path(target).as_posix()}
    if resolved_inventory != {DOCKER_EXECUTABLE.as_posix()}:
        raise PortReleaseError("docker_executable_ambiguous")
    identity = _executable_identity(
        DOCKER_EXECUTABLE,
        owner=DOCKER_OWNER,
        error_code="docker_executable_invalid",
        expected_size=DOCKER_EXECUTABLE_SIZE,
        expected_digest=DOCKER_EXECUTABLE_DIGEST,
    )
    try:
        alias_resolved = DOCKER_ALIAS.stat()
        direct_target = DOCKER_EXECUTABLE.lstat()
    except OSError as exc:
        raise PortReleaseError("docker_executable_invalid") from exc
    identities = {
        (alias_resolved.st_dev, alias_resolved.st_ino),
        (direct_target.st_dev, direct_target.st_ino),
        (identity.device, identity.inode),
    }
    if len(identities) != 1:
        raise PortReleaseError("docker_executable_ambiguous")
    try:
        alias_final = DOCKER_ALIAS.lstat()
        final_target = os.readlink(DOCKER_ALIAS)
    except OSError as exc:
        raise PortReleaseError("docker_executable_invalid") from exc
    if (
        not _same_inode(alias_after, alias_final)
        or final_target != DOCKER_EXECUTABLE.as_posix()
        or alias_after.st_mtime_ns != alias_final.st_mtime_ns
        or alias_after.st_uid != alias_final.st_uid
        or alias_after.st_gid != alias_final.st_gid
        or stat.S_IMODE(alias_after.st_mode)
        != stat.S_IMODE(alias_final.st_mode)
    ):
        raise PortReleaseError("docker_executable_changed")
    return identity


def _revalidate_executable(
    expected: ExecutableIdentity,
    validator: Callable[[], ExecutableIdentity],
    error_code: str,
) -> None:
    if validator() != expected:
        raise PortReleaseError(error_code)


def _revalidate_executable_metadata(
    expected: ExecutableIdentity,
    error_code: str,
) -> None:
    try:
        details = Path(expected.path).lstat()
        alias_before = DOCKER_ALIAS.lstat()
        alias_target = os.readlink(DOCKER_ALIAS)
        alias_after = DOCKER_ALIAS.lstat()
    except OSError as exc:
        raise PortReleaseError(error_code) from exc
    if (
        not stat.S_ISREG(details.st_mode)
        or details.st_dev != expected.device
        or details.st_ino != expected.inode
        or details.st_size != expected.size
        or details.st_mtime_ns != expected.modified_ns
        or details.st_ctime_ns != expected.changed_ns
        or stat.S_IMODE(details.st_mode) != expected.mode
        or details.st_uid != expected.uid
        or details.st_gid != expected.gid
        or stat.S_IMODE(details.st_mode) & 0o022
        or not stat.S_ISLNK(alias_before.st_mode)
        or stat.S_IMODE(alias_before.st_mode) != 0o755
        or alias_before.st_uid != GIT_OWNER[0]
        or alias_before.st_gid != GIT_OWNER[1]
        or not _same_inode(alias_before, alias_after)
        or alias_before.st_mtime_ns != alias_after.st_mtime_ns
        or alias_before.st_uid != alias_after.st_uid
        or alias_before.st_gid != alias_after.st_gid
        or stat.S_IMODE(alias_before.st_mode)
        != stat.S_IMODE(alias_after.st_mode)
        or alias_target != expected.path
    ):
        raise PortReleaseError(error_code)


def _same_file_metadata(
    first: os.stat_result,
    second: os.stat_result,
) -> bool:
    return (
        _same_inode(first, second)
        and first.st_size == second.st_size
        and first.st_mtime_ns == second.st_mtime_ns
        and first.st_ctime_ns == second.st_ctime_ns
        and first.st_uid == second.st_uid
        and first.st_gid == second.st_gid
        and stat.S_IMODE(first.st_mode) == stat.S_IMODE(second.st_mode)
    )


class SealedDockerExecutable:
    """Descriptor-anchored private copy of the reviewed Docker executable."""

    def __init__(
        self,
        *,
        parent_descriptor: int,
        parent_opened: os.stat_result,
        directory_name: str,
        directory_path: Path,
        directory_descriptor: int,
        directory_opened: os.stat_result,
        file_descriptor: int,
        file_opened: os.stat_result,
    ) -> None:
        self._parent_descriptor = parent_descriptor
        self._parent_opened = parent_opened
        self._directory_name = directory_name
        self._directory_path = directory_path
        self._directory_descriptor = directory_descriptor
        self._directory_opened = directory_opened
        self._file_descriptor = file_descriptor
        self._file_opened = file_opened
        self._closed = False

    @property
    def path(self) -> str:
        return (self._directory_path / SEALED_EXECUTABLE_NAME).as_posix()

    @staticmethod
    def _valid_temp_parent(details: os.stat_result) -> bool:
        mode = stat.S_IMODE(details.st_mode)
        private_owner = (
            details.st_uid == os.geteuid()
            and details.st_gid == os.getegid()
            and not mode & 0o022
        )
        fixed_sticky_root = (
            details.st_uid == 0
            and mode == 0o1777
        )
        return stat.S_ISDIR(details.st_mode) and (
            private_owner or fixed_sticky_root
        )

    @classmethod
    def create(cls) -> SealedDockerExecutable:
        source_identity = _validate_docker_executable()
        source_descriptor = -1
        parent_descriptor = -1
        directory_descriptor = -1
        write_descriptor = -1
        read_descriptor = -1
        directory_name = ""
        directory_path: Path | None = None
        try:
            source_before = DOCKER_EXECUTABLE.lstat()
            source_descriptor = os.open(
                DOCKER_EXECUTABLE,
                os.O_RDONLY
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_CLOEXEC", 0),
            )
            source_opened = os.fstat(source_descriptor)
            if (
                source_opened.st_dev != source_identity.device
                or source_opened.st_ino != source_identity.inode
                or not _same_file_metadata(source_before, source_opened)
            ):
                raise PortReleaseError("docker_source_changed")

            parent_before = SEALED_TEMP_PARENT.lstat()
            parent_descriptor = os.open(
                SEALED_TEMP_PARENT,
                DIRECTORY_OPEN_FLAGS,
            )
            parent_opened = os.fstat(parent_descriptor)
            parent_after = SEALED_TEMP_PARENT.lstat()
            if (
                not cls._valid_temp_parent(parent_opened)
                or not _same_inode(parent_before, parent_opened)
                or not _same_inode(parent_opened, parent_after)
            ):
                raise PortReleaseError("sealed_directory_invalid")

            for _attempt in range(8):
                directory_name = (
                    "ithildin-attempt008-sealed-"
                    + secrets.token_hex(16)
                )
                try:
                    os.mkdir(
                        directory_name,
                        0o700,
                        dir_fd=parent_descriptor,
                    )
                    os.fsync(parent_descriptor)
                    break
                except FileExistsError:
                    continue
            else:
                raise PortReleaseError("sealed_directory_unavailable")

            directory_path = SEALED_TEMP_PARENT / directory_name
            directory_before = os.stat(
                directory_name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
            directory_descriptor = os.open(
                directory_name,
                DIRECTORY_OPEN_FLAGS,
                dir_fd=parent_descriptor,
            )
            directory_opened = os.fstat(directory_descriptor)
            directory_after = directory_path.lstat()
            if (
                not stat.S_ISDIR(directory_opened.st_mode)
                or stat.S_IMODE(directory_opened.st_mode) != 0o700
                or directory_opened.st_uid != os.geteuid()
                or not _same_inode(directory_before, directory_opened)
                or not _same_inode(directory_opened, directory_after)
                or directory_before.st_gid != directory_opened.st_gid
                or directory_opened.st_gid != directory_after.st_gid
            ):
                raise PortReleaseError("sealed_directory_invalid")

            write_descriptor = os.open(
                SEALED_EXECUTABLE_NAME,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_CLOEXEC", 0),
                0o600,
                dir_fd=directory_descriptor,
            )
            source_hasher = hashlib.sha256()
            copied = 0
            while True:
                chunk = os.read(source_descriptor, 65_536)
                if not chunk:
                    break
                source_hasher.update(chunk)
                offset = 0
                while offset < len(chunk):
                    written = os.write(write_descriptor, chunk[offset:])
                    if written <= 0:
                        raise PortReleaseError("sealed_copy_failed")
                    offset += written
                copied += len(chunk)
                if copied > MAX_EXECUTABLE_BYTES:
                    raise PortReleaseError("sealed_copy_failed")
            source_post_descriptor = os.fstat(source_descriptor)
            source_post_path = DOCKER_EXECUTABLE.lstat()
            post_identity = _validate_docker_executable()
            copied_digest = "sha256:" + source_hasher.hexdigest()
            if (
                copied != DOCKER_EXECUTABLE_SIZE
                or copied_digest != DOCKER_EXECUTABLE_DIGEST
                or not _same_file_metadata(
                    source_before,
                    source_opened,
                )
                or not _same_file_metadata(
                    source_opened,
                    source_post_descriptor,
                )
                or not _same_file_metadata(
                    source_post_descriptor,
                    source_post_path,
                )
                or post_identity != source_identity
            ):
                raise PortReleaseError("docker_source_changed")

            os.fsync(write_descriptor)
            os.fchmod(write_descriptor, 0o500)
            os.fsync(write_descriptor)
            os.fsync(directory_descriptor)
            os.close(write_descriptor)
            write_descriptor = -1
            read_descriptor = os.open(
                SEALED_EXECUTABLE_NAME,
                os.O_RDONLY
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_CLOEXEC", 0),
                dir_fd=directory_descriptor,
            )
            file_opened = os.fstat(read_descriptor)
            directory_sealed = os.fstat(directory_descriptor)
            directory_sealed_from_parent = os.stat(
                directory_name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
            directory_sealed_path = directory_path.lstat()
            if (
                not stat.S_ISDIR(directory_sealed.st_mode)
                or stat.S_IMODE(directory_sealed.st_mode) != 0o700
                or directory_sealed.st_uid != os.geteuid()
                or not _same_file_metadata(
                    directory_sealed,
                    directory_sealed_from_parent,
                )
                or not _same_file_metadata(
                    directory_sealed_from_parent,
                    directory_sealed_path,
                )
            ):
                raise PortReleaseError("sealed_directory_invalid")
            instance = cls(
                parent_descriptor=parent_descriptor,
                parent_opened=parent_opened,
                directory_name=directory_name,
                directory_path=directory_path,
                directory_descriptor=directory_descriptor,
                directory_opened=directory_sealed,
                file_descriptor=read_descriptor,
                file_opened=file_opened,
            )
            instance.verify()
            source_descriptor_to_close = source_descriptor
            source_descriptor = -1
            os.close(source_descriptor_to_close)
            return instance
        except BaseException:
            if source_descriptor >= 0:
                os.close(source_descriptor)
            if write_descriptor >= 0:
                os.close(write_descriptor)
            if read_descriptor >= 0:
                os.close(read_descriptor)
            if directory_descriptor >= 0:
                try:
                    os.unlink(
                        SEALED_EXECUTABLE_NAME,
                        dir_fd=directory_descriptor,
                    )
                except OSError:
                    pass
                os.close(directory_descriptor)
            if parent_descriptor >= 0:
                if directory_name:
                    try:
                        os.rmdir(
                            directory_name,
                            dir_fd=parent_descriptor,
                        )
                        os.fsync(parent_descriptor)
                    except OSError:
                        pass
                os.close(parent_descriptor)
            raise

    def verify(self) -> None:
        if self._closed:
            raise PortReleaseError("sealed_executable_closed")
        try:
            parent_now = os.fstat(self._parent_descriptor)
            parent_path = SEALED_TEMP_PARENT.lstat()
            directory_from_parent = os.stat(
                self._directory_name,
                dir_fd=self._parent_descriptor,
                follow_symlinks=False,
            )
            directory_now = os.fstat(self._directory_descriptor)
            directory_path = self._directory_path.lstat()
            file_before = os.fstat(self._file_descriptor)
            file_from_directory = os.stat(
                SEALED_EXECUTABLE_NAME,
                dir_fd=self._directory_descriptor,
                follow_symlinks=False,
            )
            file_path = (self._directory_path / SEALED_EXECUTABLE_NAME).lstat()
            os.lseek(self._file_descriptor, 0, os.SEEK_SET)
            hasher = hashlib.sha256()
            remaining = DOCKER_EXECUTABLE_SIZE
            while remaining:
                chunk = os.read(
                    self._file_descriptor,
                    min(65_536, remaining),
                )
                if not chunk:
                    break
                hasher.update(chunk)
                remaining -= len(chunk)
            extra = os.read(self._file_descriptor, 1)
            os.lseek(self._file_descriptor, 0, os.SEEK_SET)
            file_after = os.fstat(self._file_descriptor)
        except OSError as exc:
            raise PortReleaseError("sealed_executable_changed") from exc
        if (
            not _same_inode(self._parent_opened, parent_now)
            or not _same_inode(parent_now, parent_path)
            or not self._valid_temp_parent(parent_now)
            or not _same_inode(
                self._directory_opened,
                directory_from_parent,
            )
            or not _same_file_metadata(
                self._directory_opened,
                directory_from_parent,
            )
            or not _same_file_metadata(
                directory_from_parent,
                directory_now,
            )
            or not _same_file_metadata(
                directory_now,
                directory_path,
            )
            or stat.S_IMODE(directory_now.st_mode) != 0o700
            or directory_now.st_uid != os.geteuid()
            or not _same_file_metadata(self._file_opened, file_before)
            or not _same_file_metadata(file_before, file_from_directory)
            or not _same_file_metadata(file_from_directory, file_path)
            or not _same_file_metadata(file_path, file_after)
            or not stat.S_ISREG(file_after.st_mode)
            or stat.S_IMODE(file_after.st_mode) != 0o500
            or file_after.st_uid != os.geteuid()
            or file_after.st_size != DOCKER_EXECUTABLE_SIZE
            or remaining
            or extra
            or "sha256:" + hasher.hexdigest()
            != DOCKER_EXECUTABLE_DIGEST
        ):
            raise PortReleaseError("sealed_executable_changed")

    def close(self) -> None:
        if self._closed:
            return
        failure: PortReleaseError | None = None
        try:
            self.verify()
        except PortReleaseError as exc:
            failure = exc
        try:
            os.unlink(
                SEALED_EXECUTABLE_NAME,
                dir_fd=self._directory_descriptor,
            )
            os.fsync(self._directory_descriptor)
        except OSError:
            failure = failure or PortReleaseError(
                "sealed_executable_cleanup_failed"
            )
        os.close(self._file_descriptor)
        os.close(self._directory_descriptor)
        try:
            os.rmdir(
                self._directory_name,
                dir_fd=self._parent_descriptor,
            )
            os.fsync(self._parent_descriptor)
        except OSError:
            failure = failure or PortReleaseError(
                "sealed_executable_cleanup_failed"
            )
        os.close(self._parent_descriptor)
        self._closed = True
        if failure is not None:
            raise failure

    def __enter__(self) -> SealedDockerExecutable:
        self.verify()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def _git(repo_root: Path, *arguments: str) -> str:
    executable = _validate_git_executable()
    try:
        result = subprocess.run(
            (executable.path, "-C", str(repo_root), *arguments),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=20.0,
            env={},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PortReleaseError("candidate_inspection_unavailable") from exc
    _revalidate_executable(
        executable,
        _validate_git_executable,
        "git_executable_changed",
    )
    if result.returncode != 0 or len(result.stdout) > MAX_DOCKER_OUTPUT_BYTES:
        raise PortReleaseError("candidate_inspection_invalid")
    try:
        return result.stdout.decode("utf-8", errors="strict").strip()
    except UnicodeError as exc:
        raise PortReleaseError("candidate_inspection_invalid") from exc


def candidate_identity(repo_root: Path) -> tuple[str, str]:
    if _git(repo_root, "status", "--porcelain", "--untracked-files=all"):
        raise PortReleaseError("candidate_not_clean")
    commit = _git(repo_root, "rev-parse", "HEAD")
    tree = _git(repo_root, "rev-parse", "HEAD^{tree}")
    parents = _git(repo_root, "rev-list", "--parents", "-n", "1", "HEAD").split()
    if parents != [commit, PARENT_COMMIT]:
        raise PortReleaseError("candidate_parent_invalid")
    if _git(repo_root, "rev-parse", f"{PARENT_COMMIT}^{{tree}}") != PARENT_TREE:
        raise PortReleaseError("candidate_parent_invalid")
    paths = _git(
        repo_root,
        "diff-tree",
        "--no-commit-id",
        "--name-only",
        "-r",
        PARENT_COMMIT,
        commit,
    ).splitlines()
    if sorted(paths) != CANDIDATE_PATH_ALLOWLIST:
        raise PortReleaseError("candidate_allowlist_invalid")
    return commit, tree


def validate_authorization(
    repo_root: Path,
    *,
    candidate_commit: str,
    candidate_tree: str,
) -> None:
    record = _load_closed_json(repo_root / AUTHORIZATION_JSON)
    expected = {
        "schema_version": "1",
        "record_type": "local_v1_lv1_003_o4_attempt008_port_release_authorization",
        "record_status": "AUTHORIZED_UNCONSUMED_EXACT_ONE_SHOT",
        "recovery_id": RECOVERY_ID,
        "parent_commit": PARENT_COMMIT,
        "parent_tree": PARENT_TREE,
        "candidate_binding": {
            "mode": "dynamic_clean_single_parent_immediate_child",
            "candidate_commit": None,
            "candidate_tree": None,
            "changed_paths_must_equal_allowlist": True,
            "persistent_cross_process_claim": False,
        },
        "candidate_path_allowlist": CANDIDATE_PATH_ALLOWLIST,
        "target": {
            "run_id": RUN_ID,
            "compose_project": PROJECT,
            "retained_receipt_root": RETAINED_ROOT.as_posix(),
            "private_receipt_root": RECEIPT_ROOT.as_posix(),
            "git_executable": GIT_EXECUTABLE.as_posix(),
            "docker_alias": DOCKER_ALIAS.as_posix(),
            "docker_resolved_executable": DOCKER_EXECUTABLE.as_posix(),
            "docker_executable_size": DOCKER_EXECUTABLE_SIZE,
            "docker_executable_digest": DOCKER_EXECUTABLE_DIGEST,
            "docker_reviewed_source_executed": False,
            "sealed_copy_descriptor_anchored": True,
            "sealed_copy_random_directory_bytes": 16,
            "sealed_copy_directory_mode": "0700",
            "sealed_copy_executable_mode": "0500",
            "sealed_copy_permission_boundary": (
                "stable_effective_uid_owner_and_mode"
            ),
            "sealed_copy_inherited_gid_permission_bearing": False,
            "sealed_copy_inherited_gid_recorded_and_revalidated": True,
            "sealed_copy_source_postmetadata_size_digest_revalidated": True,
            "sealed_copy_revalidated_before_after_each_command": True,
            "sealed_copy_cleanup_required": True,
            "sealed_copy_cleanup_failure_terminal": True,
            "docker_child_path_inherited": False,
            "service_image_ids": {
                service: contract.image_id
                for service, contract in SERVICES.items()
            },
            "api_port_binding": "127.0.0.1:8000->8000/tcp",
            "ui_port_binding": "127.0.0.1:5173->8080/tcp",
        },
        "attempt_budget": 1,
        "consumed": False,
        "retry_authorized": False,
        "previous_attempt_closure": {
            "recovery_id": PREVIOUS_RECOVERY_ID,
            "candidate_commit": PARENT_COMMIT,
            "candidate_tree": PARENT_TREE,
            "disposition_json": (
                PORT_RELEASE_ATTEMPT_001_DISPOSITION_JSON.as_posix()
            ),
            "disposition_document": (
                PORT_RELEASE_ATTEMPT_001_DISPOSITION_DOCUMENT.as_posix()
            ),
            "private_receipt_root": PREVIOUS_RECEIPT_ROOT.as_posix(),
            "receipt_bindings": [
                {
                    "path": (
                        PREVIOUS_RECEIPT_ROOT / CONSUMED_RECEIPT
                    ).as_posix(),
                    "size": ATTEMPT_001_CONSUMED_SIZE,
                    "sha256": ATTEMPT_001_CONSUMED_DIGEST,
                },
                {
                    "path": (
                        PREVIOUS_RECEIPT_ROOT
                        / JOURNAL_DIRECTORY
                        / "0001-disposition-intent.json"
                    ).as_posix(),
                    "size": ATTEMPT_001_JOURNAL_SIZE,
                    "sha256": ATTEMPT_001_JOURNAL_DIGEST,
                },
                {
                    "path": (
                        PREVIOUS_RECEIPT_ROOT / DISPOSITION_RECEIPT
                    ).as_posix(),
                    "size": ATTEMPT_001_DISPOSITION_SIZE,
                    "sha256": ATTEMPT_001_DISPOSITION_DIGEST,
                },
            ],
            "failure_code": "sealed_directory_invalid",
            "consumed": True,
            "attempt_budget": 0,
            "retry_authorized": False,
            "docker_command_executed": False,
            "successor_is_separate_authority": True,
            "successor_is_retry": False,
        },
        "receipt_contract": {
            "empty_or_missing_lane_consumption_status": "unconsumed",
            "valid_consumed_lane_consumption_status": "consumed",
            "nonempty_invalid_or_unknown_lane_consumption_status": (
                "presumed_consumed_unknown"
            ),
            "nonempty_invalid_or_unknown_lane_attempt_budget": 0,
            "nonempty_invalid_or_unknown_lane_execution_available": False,
            "leaf_identity_fields": [
                "device",
                "inode",
                "size",
                "mtime_ns",
                "ctime_ns",
                "uid",
                "gid",
                "mode",
            ],
        },
        "journal_contract": {
            "append_only_exclusive_leaves": True,
            "owner_only": True,
            "file_and_directory_fsync": True,
            "intent_result_ambiguity_preserved": True,
            "closed_payload_schemas": True,
            "unique_events_and_legal_transition_prefixes": True,
            "disposition_intent_is_final_journal_leaf": True,
            "disposition_equals_journal_derived_disposition": True,
            "preinspection_failure_requires_exact_default_outcome": True,
            "actions_preservation_and_ports_crosslinked": True,
            "maximum_entries": MAX_JOURNAL_ENTRIES,
        },
        "operator_command": f"make {RUN_TARGET}",
        "module_command": MODULE_COMMAND,
        "authority_true": sorted(TRUE_AUTHORITY),
        "authority_false": sorted(FALSE_AUTHORITY),
        "tool_count": 24,
        "release_allowed": False,
        "uat_complete": False,
    }
    if record != expected:
        raise PortReleaseError("authorization_invalid")
    document = (repo_root / AUTHORIZATION_DOCUMENT).read_text(encoding="utf-8")
    for phrase in (
        RECOVERY_ID,
        PARENT_COMMIT,
        PARENT_TREE,
        "exact seven-path allowlist",
        "budget is one and unconsumed",
        "persistent cross-process claim is false",
        PREVIOUS_RECOVERY_ID,
        "Attempt 002 is a separate authority, not a retry",
        "owner and mode are the permission boundary",
        "inherited gid is recorded and revalidated",
        "reviewed Docker source is never executed",
        "random private 0700 directory",
        "sealed 0500 copy",
        "Docker child PATH inheritance is false",
        DOCKER_EXECUTABLE_DIGEST,
        "append-only journal",
        "presumed_consumed_unknown",
        "final disposition-intent",
        "Static candidate validity is separate from execution availability",
        "Node and Hermes are never stop targets",
        "point-in-time port availability only",
        "tool count remains 24",
        f"make {RUN_TARGET}",
        f"make {CHECK_TARGET}",
    ):
        if phrase not in " ".join(document.split()):
            raise PortReleaseError("authorization_document_invalid")
    if not re.fullmatch(r"[0-9a-f]{40}", candidate_commit) or not re.fullmatch(
        r"[0-9a-f]{40}", candidate_tree
    ):
        raise PortReleaseError("candidate_identity_invalid")


def validate_tracked_disposition(repo_root: Path) -> None:
    for path, digest, size in (
        (
            ATTEMPT_DISPOSITION_JSON,
            ATTEMPT_DISPOSITION_JSON_DIGEST,
            4657,
        ),
        (
            ATTEMPT_DISPOSITION_DOCUMENT,
            ATTEMPT_DISPOSITION_DOCUMENT_DIGEST,
            3342,
        ),
    ):
        details = (repo_root / path).lstat()
        if (
            not stat.S_ISREG(details.st_mode)
            or stat.S_IMODE(details.st_mode) != 0o644
            or details.st_uid != os.geteuid()
            or details.st_gid != os.getegid()
            or details.st_size != size
            or _digest(repo_root / path) != digest
        ):
            raise PortReleaseError("tracked_disposition_invalid")
    record = _load_closed_json(repo_root / ATTEMPT_DISPOSITION_JSON)
    attempt_contract = record.get("attempt_contract")
    if (
        record.get("attempt_id") != "LV1-003-O4-ATTEMPT-008"
        or record.get("run_id") != RUN_ID
        or record.get("compose_project") != PROJECT
        or record.get("outward_failure_code") != "recovery_required"
        or not isinstance(attempt_contract, dict)
        or attempt_contract.get("recovery_required") is not True
    ):
        raise PortReleaseError("tracked_disposition_invalid")


def _attempt_001_port_release_disposition_record() -> JsonObject:
    return {
        "schema_version": "1",
        "record_type": (
            "local_v1_lv1_003_o4_attempt008_port_release_attempt_001_disposition"
        ),
        "record_status": "CONSUMED_FAILED_BEFORE_DOCKER_COMMAND",
        "attempt_id": "LV1-003-O4-ATTEMPT-008-PORT-RELEASE-ATTEMPT-001",
        "recovery_id": PREVIOUS_RECOVERY_ID,
        "candidate_commit": PARENT_COMMIT,
        "candidate_tree": PARENT_TREE,
        "run_id": RUN_ID,
        "compose_project": PROJECT,
        "failure": {
            "observed_code": "sealed_directory_invalid",
            "diagnosed_phase": "sealed_private_directory_validation",
            "diagnosed_cause": (
                "private_tmp_child_inherited_gid_differed_from_effective_gid"
            ),
        },
        "observed_receipt_outcome": {
            "before_projections": {},
            "after_projections": {},
            "actions": {
                "api": {"status": "not_attempted"},
                "ui": {"status": "not_attempted"},
            },
            "port_observations": [],
            "report": {
                "valid": True,
                "consumption_status": "consumed",
                "attempt_budget": 0,
                "execution_available": False,
            },
        },
        "derived_execution_nonclaims": {
            "basis": (
                "default_outcome_and_disposition_intent_only_journal"
            ),
            "docker_command_executed": False,
            "target_container_inspection_performed": False,
            "target_container_mutation_performed": False,
            "point_in_time_port_observation_performed": False,
        },
        "post_failure_observation": {
            "sealed_directory_leftover_observed": False,
            "evidence_source": "operator_post_failure_filesystem_observation",
        },
        "receipt_binding": {
            "root": PREVIOUS_RECEIPT_ROOT.as_posix(),
            "root_mode": "0700",
            "leaf_mode": "0600",
            "owner_only": True,
            "entries": [
                {
                    "path": (
                        PREVIOUS_RECEIPT_ROOT / CONSUMED_RECEIPT
                    ).as_posix(),
                    "size": ATTEMPT_001_CONSUMED_SIZE,
                    "sha256": ATTEMPT_001_CONSUMED_DIGEST,
                },
                {
                    "path": (
                        PREVIOUS_RECEIPT_ROOT
                        / JOURNAL_DIRECTORY
                        / "0001-disposition-intent.json"
                    ).as_posix(),
                    "size": ATTEMPT_001_JOURNAL_SIZE,
                    "sha256": ATTEMPT_001_JOURNAL_DIGEST,
                },
                {
                    "path": (
                        PREVIOUS_RECEIPT_ROOT / DISPOSITION_RECEIPT
                    ).as_posix(),
                    "size": ATTEMPT_001_DISPOSITION_SIZE,
                    "sha256": ATTEMPT_001_DISPOSITION_DIGEST,
                },
            ],
        },
        "attempt_budget": 0,
        "consumed": True,
        "retry_authorized": False,
        "successor_authorization": {
            "recovery_id": RECOVERY_ID,
            "separate_authority": True,
            "retry_of_attempt_001": False,
            "authority_derived_from_attempt_001_disposition": False,
        },
        "authority_granted_true": cast(
            list[JsonValue],
            sorted(TRUE_AUTHORITY),
        ),
        "authority_granted_false": cast(
            list[JsonValue],
            sorted(FALSE_AUTHORITY),
        ),
        "authority_exercised_true": [
            "private_receipt_write",
            "retained_receipt_validation",
        ],
        "authority_exercised_false": cast(
            list[JsonValue],
            sorted(
                (TRUE_AUTHORITY | FALSE_AUTHORITY)
                - {"private_receipt_write", "retained_receipt_validation"}
            ),
        ),
        "tool_count": 24,
        "release_allowed": False,
        "uat_complete": False,
    }


def validate_attempt_001_port_release_disposition(repo_root: Path) -> None:
    path = repo_root / PORT_RELEASE_ATTEMPT_001_DISPOSITION_JSON
    document_path = (
        repo_root / PORT_RELEASE_ATTEMPT_001_DISPOSITION_DOCUMENT
    )
    try:
        details = path.lstat()
        document_details = document_path.lstat()
        document = document_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise PortReleaseError("attempt_001_disposition_invalid") from exc
    if (
        not stat.S_ISREG(details.st_mode)
        or stat.S_IMODE(details.st_mode) != 0o644
        or details.st_uid != os.geteuid()
        or details.st_gid != os.getegid()
        or not stat.S_ISREG(document_details.st_mode)
        or stat.S_IMODE(document_details.st_mode) != 0o644
        or document_details.st_uid != os.geteuid()
        or document_details.st_gid != os.getegid()
        or _load_closed_json(path)
        != _attempt_001_port_release_disposition_record()
    ):
        raise PortReleaseError("attempt_001_disposition_invalid")
    normalized = " ".join(document.split())
    for phrase in (
        PREVIOUS_RECOVERY_ID,
        PARENT_COMMIT,
        PARENT_TREE,
        "sealed_directory_invalid",
        ATTEMPT_001_CONSUMED_DIGEST,
        ATTEMPT_001_JOURNAL_DIGEST,
        ATTEMPT_001_DISPOSITION_DIGEST,
        "no Docker command was executed",
        "not a retry",
        "budget is zero",
        "Release and UAT remain false",
    ):
        if phrase not in normalized:
            raise PortReleaseError("attempt_001_disposition_invalid")


def _validate_attempt_001_receipt_leaf(
    chain: _DirectoryChain,
    name: str,
    *,
    size: int,
    digest: str,
) -> None:
    content = _read_leaf(
        chain,
        name,
        expected_mode=0o600,
        maximum_size=MAX_HASH_BYTES,
        error_code="attempt_001_receipt_invalid",
    )
    if len(content) != size or _sha256_bytes(content) != digest:
        raise PortReleaseError("attempt_001_receipt_invalid")


def validate_attempt_001_port_release_receipts(repo_root: Path) -> None:
    root = _open_relative_chain(
        repo_root,
        PREVIOUS_RECEIPT_ROOT,
        create=False,
        error_code="attempt_001_receipt_invalid",
    )
    if root is None:
        raise PortReleaseError("attempt_001_receipt_invalid")
    with root:
        if root.entries() != [
            CONSUMED_RECEIPT,
            DISPOSITION_RECEIPT,
            JOURNAL_DIRECTORY,
        ]:
            raise PortReleaseError("attempt_001_receipt_invalid")
        _validate_attempt_001_receipt_leaf(
            root,
            CONSUMED_RECEIPT,
            size=ATTEMPT_001_CONSUMED_SIZE,
            digest=ATTEMPT_001_CONSUMED_DIGEST,
        )
        _validate_attempt_001_receipt_leaf(
            root,
            DISPOSITION_RECEIPT,
            size=ATTEMPT_001_DISPOSITION_SIZE,
            digest=ATTEMPT_001_DISPOSITION_DIGEST,
        )
    journal = _open_relative_chain(
        repo_root,
        PREVIOUS_RECEIPT_ROOT / JOURNAL_DIRECTORY,
        create=False,
        error_code="attempt_001_receipt_invalid",
    )
    if journal is None:
        raise PortReleaseError("attempt_001_receipt_invalid")
    with journal:
        if journal.entries() != ["0001-disposition-intent.json"]:
            raise PortReleaseError("attempt_001_receipt_invalid")
        _validate_attempt_001_receipt_leaf(
            journal,
            "0001-disposition-intent.json",
            size=ATTEMPT_001_JOURNAL_SIZE,
            digest=ATTEMPT_001_JOURNAL_DIGEST,
        )


def _same_inode(first: os.stat_result, second: os.stat_result) -> bool:
    return first.st_dev == second.st_dev and first.st_ino == second.st_ino


@dataclass
class _DirectoryNode:
    name: str | None
    descriptor: int
    opened: os.stat_result
    expected_mode: int | None


class _DirectoryChain:
    """An owner-bound directory chain anchored at one trusted repository fd."""

    def __init__(self, repo_root: Path, *, error_code: str) -> None:
        self._repo_root = repo_root
        self._error_code = error_code
        self._nodes: list[_DirectoryNode] = []
        descriptor = -1
        try:
            before = repo_root.lstat()
            descriptor = os.open(repo_root, DIRECTORY_OPEN_FLAGS)
            opened = os.fstat(descriptor)
            after = repo_root.lstat()
        except OSError as exc:
            if descriptor >= 0:
                os.close(descriptor)
            raise PortReleaseError(error_code) from exc
        if not self._valid_directory(opened, expected_mode=None) or not (
            _same_inode(before, opened) and _same_inode(opened, after)
        ):
            os.close(descriptor)
            raise PortReleaseError(error_code)
        self._nodes.append(_DirectoryNode(None, descriptor, opened, None))

    @staticmethod
    def _valid_directory(
        details: os.stat_result,
        *,
        expected_mode: int | None,
    ) -> bool:
        mode = stat.S_IMODE(details.st_mode)
        return (
            stat.S_ISDIR(details.st_mode)
            and details.st_uid == os.geteuid()
            and details.st_gid == os.getegid()
            and not mode & 0o022
            and (expected_mode is None or mode == expected_mode)
        )

    @property
    def descriptor(self) -> int:
        return self._nodes[-1].descriptor

    def open_child(
        self,
        name: str,
        *,
        expected_mode: int | None,
        create: bool,
    ) -> bool:
        if re.fullmatch(r"[A-Za-z0-9._-]+", name) is None:
            raise PortReleaseError(self._error_code)
        self.recheck()
        parent = self._nodes[-1]
        try:
            before = os.stat(
                name,
                dir_fd=parent.descriptor,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            if not create:
                return False
            if expected_mode is None:
                raise PortReleaseError(self._error_code) from None
            try:
                os.mkdir(name, expected_mode, dir_fd=parent.descriptor)
                os.fsync(parent.descriptor)
                before = os.stat(
                    name,
                    dir_fd=parent.descriptor,
                    follow_symlinks=False,
                )
            except FileExistsError:
                try:
                    before = os.stat(
                        name,
                        dir_fd=parent.descriptor,
                        follow_symlinks=False,
                    )
                except OSError as exc:
                    raise PortReleaseError(self._error_code) from exc
            except OSError as exc:
                raise PortReleaseError(self._error_code) from exc
        except OSError as exc:
            raise PortReleaseError(self._error_code) from exc
        descriptor = -1
        try:
            descriptor = os.open(
                name,
                DIRECTORY_OPEN_FLAGS,
                dir_fd=parent.descriptor,
            )
            opened = os.fstat(descriptor)
            after = os.stat(
                name,
                dir_fd=parent.descriptor,
                follow_symlinks=False,
            )
        except OSError as exc:
            if descriptor >= 0:
                os.close(descriptor)
            raise PortReleaseError(self._error_code) from exc
        if not self._valid_directory(opened, expected_mode=expected_mode) or not (
            _same_inode(before, opened) and _same_inode(opened, after)
        ):
            os.close(descriptor)
            raise PortReleaseError(self._error_code)
        self._nodes.append(
            _DirectoryNode(name, descriptor, opened, expected_mode)
        )
        self.recheck()
        return True

    def recheck(self) -> None:
        try:
            root_now = self._repo_root.lstat()
            if not _same_inode(self._nodes[0].opened, root_now):
                raise PortReleaseError(self._error_code)
            for index, node in enumerate(self._nodes):
                current = os.fstat(node.descriptor)
                if (
                    not _same_inode(node.opened, current)
                    or not self._valid_directory(
                        current,
                        expected_mode=node.expected_mode,
                    )
                ):
                    raise PortReleaseError(self._error_code)
                if index:
                    parent = self._nodes[index - 1]
                    relative = os.stat(
                        cast(str, node.name),
                        dir_fd=parent.descriptor,
                        follow_symlinks=False,
                    )
                    if not _same_inode(current, relative):
                        raise PortReleaseError(self._error_code)
        except OSError as exc:
            raise PortReleaseError(self._error_code) from exc

    def entries(self) -> list[str]:
        self.recheck()
        try:
            values = sorted(os.listdir(self.descriptor))
        except OSError as exc:
            raise PortReleaseError(self._error_code) from exc
        self.recheck()
        return values

    def close(self) -> None:
        while self._nodes:
            os.close(self._nodes.pop().descriptor)

    def __enter__(self) -> _DirectoryChain:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def _open_relative_chain(
    repo_root: Path,
    relative: Path,
    *,
    create: bool,
    error_code: str,
    final_mode: int | None = None,
) -> _DirectoryChain | None:
    chain = _DirectoryChain(repo_root, error_code=error_code)
    try:
        for index, component in enumerate(relative.parts):
            expected_mode = (
                final_mode
                if final_mode is not None and index == len(relative.parts) - 1
                else None
                if index == 0 and component == "var"
                else 0o700
            )
            if not chain.open_child(
                component,
                expected_mode=expected_mode,
                create=create and expected_mode is not None,
            ):
                chain.close()
                return None
        return chain
    except BaseException:
        chain.close()
        raise


def _read_leaf(
    chain: _DirectoryChain,
    name: str,
    *,
    expected_mode: int,
    maximum_size: int,
    error_code: str,
) -> bytes:
    if re.fullmatch(r"[A-Za-z0-9._-]+", name) is None:
        raise PortReleaseError(error_code)
    chain.recheck()
    descriptor = -1
    try:
        before = os.stat(
            name,
            dir_fd=chain.descriptor,
            follow_symlinks=False,
        )
        descriptor = os.open(
            name,
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0),
            dir_fd=chain.descriptor,
        )
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or not stat.S_ISREG(opened.st_mode)
            or stat.S_IMODE(before.st_mode) != expected_mode
            or stat.S_IMODE(opened.st_mode) != expected_mode
            or before.st_uid != os.geteuid()
            or before.st_gid != os.getegid()
            or opened.st_uid != os.geteuid()
            or opened.st_gid != os.getegid()
            or opened.st_size > maximum_size
            or not _same_file_metadata(before, opened)
        ):
            raise PortReleaseError(error_code)
        chunks: list[bytes] = []
        remaining = maximum_size + 1
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b"".join(chunks)
        after = os.fstat(descriptor)
        leaf_after = os.stat(
            name,
            dir_fd=chain.descriptor,
            follow_symlinks=False,
        )
        chain.recheck()
    except OSError as exc:
        raise PortReleaseError(error_code) from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if (
        len(content) > maximum_size
        or len(content) != opened.st_size
        or not _same_file_metadata(opened, after)
        or not _same_file_metadata(after, leaf_after)
        or not stat.S_ISREG(after.st_mode)
        or stat.S_IMODE(after.st_mode) != expected_mode
        or after.st_uid != os.geteuid()
        or after.st_gid != os.getegid()
    ):
        raise PortReleaseError(error_code)
    return content


def _read_json_leaf(
    chain: _DirectoryChain,
    name: str,
    *,
    error_code: str,
) -> dict[str, Any]:
    try:
        value = json.loads(
            _read_leaf(
                chain,
                name,
                expected_mode=0o600,
                maximum_size=MAX_HASH_BYTES,
                error_code=error_code,
            ).decode("utf-8", errors="strict"),
            object_pairs_hook=_closed_object,
        )
    except (UnicodeError, ValueError) as exc:
        raise PortReleaseError(error_code) from exc
    if not isinstance(value, dict):
        raise PortReleaseError(error_code)
    return cast(dict[str, Any], value)


def _write_json_leaf_exclusive(
    chain: _DirectoryChain,
    name: str,
    document: JsonObject,
    *,
    error_code: str,
) -> None:
    if re.fullmatch(r"[A-Za-z0-9._-]+", name) is None:
        raise PortReleaseError(error_code)
    content = (canonical_json(document) + "\n").encode()
    if len(content) > MAX_HASH_BYTES:
        raise PortReleaseError(error_code)
    chain.recheck()
    descriptor = -1
    try:
        descriptor = os.open(
            name,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0),
            0o600,
            dir_fd=chain.descriptor,
        )
        written = 0
        while written < len(content):
            count = os.write(descriptor, content[written:])
            if count <= 0:
                raise PortReleaseError(error_code)
            written += count
        os.fsync(descriptor)
        created = os.fstat(descriptor)
        os.fsync(chain.descriptor)
    except FileExistsError:
        raise
    except OSError as exc:
        raise PortReleaseError(error_code) from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    observed = _read_leaf(
        chain,
        name,
        expected_mode=0o600,
        maximum_size=MAX_HASH_BYTES,
        error_code=error_code,
    )
    if (
        observed != content
        or not stat.S_ISREG(created.st_mode)
        or stat.S_IMODE(created.st_mode) != 0o600
        or created.st_uid != os.geteuid()
        or created.st_gid != os.getegid()
        or created.st_size != len(content)
    ):
        raise PortReleaseError(error_code)


def _hash_exact_leaf(
    chain: _DirectoryChain,
    name: str,
    *,
    size: int,
    digest: str,
) -> None:
    content = _read_leaf(
        chain,
        name,
        expected_mode=0o600,
        maximum_size=MAX_HASH_BYTES,
        error_code="retained_receipt_invalid",
    )
    if len(content) != size or _sha256_bytes(content) != digest:
        raise PortReleaseError("retained_receipt_invalid")


def validate_retained_receipts(repo_root: Path) -> None:
    chain = _open_relative_chain(
        repo_root,
        RETAINED_ROOT,
        create=False,
        error_code="retained_receipt_invalid",
    )
    if chain is None:
        raise PortReleaseError("retained_receipt_invalid")
    candidate_chain = _open_relative_chain(
        repo_root,
        RETAINED_ROOT / "candidate",
        create=False,
        error_code="retained_receipt_invalid",
        final_mode=0o500,
    )
    if candidate_chain is None:
        chain.close()
        raise PortReleaseError("retained_receipt_invalid")
    with chain, candidate_chain:
        if chain.entries() != [
            "candidate",
            "candidate-manifest.json",
            "diagnostic.json",
            "disposition.json",
        ]:
            raise PortReleaseError("retained_receipt_invalid")
        candidate_chain.recheck()
        _hash_exact_leaf(
            chain,
            "disposition.json",
            size=119,
            digest="sha256:03bceb292828f68440c2183438f856edd4b291130d6f276b9418a3d2ad967992",
        )
        _hash_exact_leaf(
            chain,
            "diagnostic.json",
            size=7174,
            digest="sha256:cf303eb045cf522e62c5fa5b2f35fc54d5ecd5981e1c0c1428d4584d6a165b28",
        )
        _hash_exact_leaf(
            chain,
            "candidate-manifest.json",
            size=96772,
            digest="sha256:04d64359cbc275181d90b50cef3534c550a0d7e446ae12caee3f5fe7bcb19c54",
        )
        candidate_chain.recheck()


def _target_binding() -> JsonObject:
    return {
        "run_id": RUN_ID,
        "compose_project": PROJECT,
        "service_image_ids": {
            service: contract.image_id for service, contract in SERVICES.items()
        },
        "api_port_binding": "127.0.0.1:8000->8000/tcp",
        "ui_port_binding": "127.0.0.1:5173->8080/tcp",
    }


def _consumption_record(candidate_commit: str, candidate_tree: str) -> JsonObject:
    return {
        "schema_version": "1",
        "record_type": "attempt008_port_release_consumption",
        "recovery_id": RECOVERY_ID,
        "candidate": {
            "commit": candidate_commit,
            "tree": candidate_tree,
        },
        "target": _target_binding(),
        "status": "consumed_before_docker_access",
        "retry_authorized": False,
        "persistent_cross_process_claim": False,
    }


@dataclass(frozen=True)
class ReceiptLaneState:
    consumption_status: str
    valid: bool
    failure: str | None


def _valid_projection_document(
    value: object,
    *,
    expected_service: str,
    allow_cleared_ports: bool,
) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "container_id",
        "image_id",
        "service",
        "running",
        "status",
        "ports",
    }:
        return False
    running = value.get("running")
    ports = value.get("ports")
    contract = SERVICES.get(expected_service)
    if (
        contract is None
        or value.get("service") != expected_service
        or value.get("image_id") != contract.image_id
        or not isinstance(value.get("container_id"), str)
        or re.fullmatch(
            r"[0-9a-f]{64}",
            cast(str, value.get("container_id")),
        )
        is None
        or type(running) is not bool
        or value.get("status") not in {"running", "exited", "created", "dead"}
        or (running is True and value.get("status") != "running")
        or (running is False and value.get("status") == "running")
        or not isinstance(ports, dict)
    ):
        return False
    expected_ports: JsonObject = {}
    if contract.container_port is not None:
        expected_ports = {
            contract.container_port: [
                {
                    "HostIp": "127.0.0.1",
                    "HostPort": cast(str, contract.host_port),
                }
            ]
        }
    return ports == expected_ports or (
        allow_cleared_ports
        and expected_service in {"ithildin-api", "ithildin-ui"}
        and running is False
        and ports == {}
    )


def _valid_projection_map(
    value: object,
    *,
    allow_cleared_ports: bool,
    require_targets: bool,
) -> bool:
    if (
        not isinstance(value, dict)
        or len(value) > 4
        or set(value) - set(SERVICES)
        or (
            require_targets
            and not {"ithildin-api", "ithildin-ui"} <= set(value)
        )
    ):
        return False
    identifiers: set[str] = set()
    for service, projection in value.items():
        if not _valid_projection_document(
            projection,
            expected_service=service,
            allow_cleared_ports=allow_cleared_ports,
        ):
            return False
        identifier = cast(dict[str, Any], projection)["container_id"]
        if identifier in identifiers:
            return False
        identifiers.add(cast(str, identifier))
    return True


def _validate_outcome_document(value: object) -> None:
    if not isinstance(value, dict) or set(value) != {
        "before_projections",
        "after_projections",
        "actions",
        "preservation",
        "port_observations",
    }:
        raise PortReleaseError("receipt_lane_invalid")
    before = value.get("before_projections")
    after = value.get("after_projections")
    actions = value.get("actions")
    preservation = value.get("preservation")
    observations = value.get("port_observations")
    if (
        not _valid_projection_map(
            before,
            allow_cleared_ports=False,
            require_targets=bool(before),
        )
        or not _valid_projection_map(
            after,
            allow_cleared_ports=True,
            require_targets=bool(after),
        )
        or not isinstance(actions, dict)
        or set(actions) != {"api", "ui"}
        or not isinstance(preservation, dict)
        or set(preservation)
        != {
            "ithildin-node",
            "hermes",
            "volumes",
            "networks",
            "images",
            "retained_runtime_and_evidence",
        }
        or set(preservation.values())
        - {
            "not_targeted_by_recovery",
            "observed_unchanged",
            "observed_changed",
        }
        or not isinstance(observations, list)
        or len(observations) > 2
    ):
        raise PortReleaseError("receipt_lane_invalid")
    allowed_action_status = {
        "not_attempted",
        "intent_durable_result_unknown",
        "stop_command_failed",
        "stop_returned_post_observation_unavailable",
        "stop_returned_post_observation_invalid",
        "stop_not_observed",
        "stopped_observed",
        "already_stopped_no_stop_issued",
    }
    for key, service in (("api", "ithildin-api"), ("ui", "ithildin-ui")):
        action = actions.get(key)
        if not isinstance(action, dict):
            raise PortReleaseError("receipt_lane_invalid")
        if action == {"status": "not_attempted"}:
            continue
        if set(action) != {
            "service",
            "container_id",
            "image_id",
            "pre_running",
            "status",
            "stop_returncode",
            "post_observation",
        }:
            raise PortReleaseError("receipt_lane_invalid")
        post = action.get("post_observation")
        if (
            action.get("service") != service
            or action.get("image_id") != SERVICES[service].image_id
            or not isinstance(action.get("container_id"), str)
            or re.fullmatch(
                r"[0-9a-f]{64}",
                cast(str, action.get("container_id")),
            )
            is None
            or type(action.get("pre_running")) is not bool
            or action.get("status") not in allowed_action_status
            or (
                action.get("stop_returncode") is not None
                and type(action.get("stop_returncode")) is not int
            )
            or (
                post is not None
                and not _valid_projection_document(
                    post,
                    expected_service=service,
                    allow_cleared_ports=True,
                )
            )
        ):
            raise PortReleaseError("receipt_lane_invalid")
    observed_ports: set[int] = set()
    for observation in observations:
        if (
            not isinstance(observation, dict)
            or set(observation) != {"host", "port", "status"}
            or observation.get("host") != "127.0.0.1"
            or observation.get("port") not in {8000, 5173}
            or observation.get("port") in observed_ports
            or observation.get("status")
            not in {
                "individual_bind_succeeded_pending_complete_set",
                "individual_bind_succeeded_but_set_failed",
                "confirmed_simultaneously_bound_point_in_time",
            }
        ):
            raise PortReleaseError("receipt_lane_invalid")
        observed_ports.add(cast(int, observation["port"]))


def _validate_journal_payload(event: str, payload: object) -> None:
    if not isinstance(payload, dict):
        raise PortReleaseError("receipt_lane_invalid")
    if event in {"pre-inspection", "final-post-inspection"}:
        if (
            set(payload) != {"compose_project", "projections"}
            or payload.get("compose_project") != PROJECT
            or not _valid_projection_map(
                payload.get("projections"),
                allow_cleared_ports=event == "final-post-inspection",
                require_targets=True,
            )
        ):
            raise PortReleaseError("receipt_lane_invalid")
        return
    match = re.fullmatch(r"(api|ui)-stop-intent", event)
    if match:
        service = "ithildin-api" if match.group(1) == "api" else "ithildin-ui"
        if (
            set(payload)
            != {
                "service",
                "container_id",
                "image_id",
                "action",
                "result_at_record_time",
            }
            or payload.get("service") != service
            or payload.get("image_id") != SERVICES[service].image_id
            or not isinstance(payload.get("container_id"), str)
            or re.fullmatch(
                r"[0-9a-f]{64}",
                cast(str, payload.get("container_id")),
            )
            is None
            or payload.get("action") != "exact_container_stop_time_10"
            or payload.get("result_at_record_time") != "unknown"
        ):
            raise PortReleaseError("receipt_lane_invalid")
        return
    match = re.fullmatch(r"(api|ui)-(?:stop|no-stop)-result", event)
    if match:
        service = "ithildin-api" if match.group(1) == "api" else "ithildin-ui"
        post = payload.get("post_observation")
        status_value = payload.get("status")
        no_stop = "-no-stop-" in event
        if (
            set(payload)
            != {
                "service",
                "container_id",
                "status",
                "returncode",
                "post_observation",
            }
            or payload.get("service") != service
            or not isinstance(payload.get("container_id"), str)
            or re.fullmatch(
                r"[0-9a-f]{64}",
                cast(str, payload.get("container_id")),
            )
            is None
            or status_value
            not in {
                "stop_command_failed",
                "stop_returned_post_observation_unavailable",
                "stop_not_observed",
                "stopped_observed",
                "already_stopped_no_stop_issued",
            }
            or (
                payload.get("returncode") is not None
                and type(payload.get("returncode")) is not int
            )
            or (
                post is not None
                and not _valid_projection_document(
                    post,
                    expected_service=service,
                    allow_cleared_ports=True,
                )
            )
            or (
                no_stop
                and (
                    status_value != "already_stopped_no_stop_issued"
                    or payload.get("returncode") is not None
                    or post is None
                )
            )
            or (
                not no_stop
                and status_value == "already_stopped_no_stop_issued"
            )
            or (
                status_value
                in {"stopped_observed", "stop_not_observed"}
                and (
                    payload.get("returncode") != 0
                    or post is None
                )
            )
            or (
                status_value
                in {
                    "stop_command_failed",
                    "stop_returned_post_observation_unavailable",
                }
                and post is not None
            )
        ):
            raise PortReleaseError("receipt_lane_invalid")
        return
    port_match = re.fullmatch(r"port-(8000|5173)-bind-observation", event)
    if port_match:
        if payload != {
            "host": "127.0.0.1",
            "port": int(port_match.group(1)),
            "status": "individual_bind_succeeded_pending_complete_set",
        }:
            raise PortReleaseError("receipt_lane_invalid")
        return
    if event == "simultaneous-port-set-observation":
        if payload != {
            "host": "127.0.0.1",
            "ports": [8000, 5173],
            "status": "simultaneously_bound_point_in_time",
        }:
            raise PortReleaseError("receipt_lane_invalid")
        return
    if event == "simultaneous-port-set-failed":
        successful = payload.get("successful_ports")
        if (
            set(payload) != {"host", "successful_ports", "status"}
            or payload.get("host") != "127.0.0.1"
            or not isinstance(successful, list)
            or successful not in ([], [8000])
            or payload.get("status") != "complete_set_not_observed"
        ):
            raise PortReleaseError("receipt_lane_invalid")
        return
    if event == "disposition-intent":
        if (
            set(payload) != {"status", "failure_code", "outcome"}
            or payload.get("status") not in {"completed", "failed"}
        ):
            raise PortReleaseError("receipt_lane_invalid")
        _validate_outcome_document(payload.get("outcome"))
        _disposition(
            status=cast(str, payload["status"]),
            outcome=cast(JsonObject, payload["outcome"]),
            failure_code=cast(str | None, payload["failure_code"]),
        )
        return
    raise PortReleaseError("receipt_lane_invalid")


def _validate_journal_sequence(
    events: list[str],
    payloads: list[dict[str, Any]],
) -> None:
    if not events:
        return
    if events[0] == "disposition-intent":
        if (
            len(events) != 1
            or payloads[0].get("status") != "failed"
        ):
            raise PortReleaseError("receipt_lane_invalid")
        return
    if events[0] != "pre-inspection":
        raise PortReleaseError("receipt_lane_invalid")
    phase = "api"
    pending_target: str | None = None
    for index, event in enumerate(events[1:], start=1):
        if event == "disposition-intent":
            status_value = payloads[index]["status"]
            if status_value == "completed" and phase != "after-simultaneous":
                raise PortReleaseError("receipt_lane_invalid")
            if index != len(events) - 1:
                raise PortReleaseError("receipt_lane_invalid")
            phase = "done"
            continue
        if phase == "api":
            if event == "api-stop-intent":
                phase = "api-result"
                pending_target = "api"
            elif event == "api-no-stop-result":
                phase = "ui"
            else:
                raise PortReleaseError("receipt_lane_invalid")
        elif phase == "api-result":
            if event != "api-stop-result" or pending_target != "api":
                raise PortReleaseError("receipt_lane_invalid")
            phase = (
                "ui"
                if payloads[index]["status"] == "stopped_observed"
                else "failed-terminal"
            )
            pending_target = None
        elif phase == "ui":
            if event == "ui-stop-intent":
                phase = "ui-result"
                pending_target = "ui"
            elif event == "ui-no-stop-result":
                phase = "final"
            else:
                raise PortReleaseError("receipt_lane_invalid")
        elif phase == "ui-result":
            if event != "ui-stop-result" or pending_target != "ui":
                raise PortReleaseError("receipt_lane_invalid")
            phase = (
                "final"
                if payloads[index]["status"] == "stopped_observed"
                else "failed-terminal"
            )
            pending_target = None
        elif phase == "final":
            if event != "final-post-inspection":
                raise PortReleaseError("receipt_lane_invalid")
            phase = "port-8000"
        elif phase == "port-8000":
            if event == "port-8000-bind-observation":
                phase = "port-5173"
            elif event == "simultaneous-port-set-failed":
                phase = "failed-terminal"
            else:
                raise PortReleaseError("receipt_lane_invalid")
        elif phase == "port-5173":
            if event == "port-5173-bind-observation":
                phase = "simultaneous"
            elif event == "simultaneous-port-set-failed":
                phase = "failed-terminal"
            else:
                raise PortReleaseError("receipt_lane_invalid")
        elif phase == "simultaneous":
            if event == "simultaneous-port-set-observation":
                phase = "after-simultaneous"
            elif event == "simultaneous-port-set-failed":
                phase = "failed-terminal"
            else:
                raise PortReleaseError("receipt_lane_invalid")
        elif phase in {"failed-terminal", "after-simultaneous", "done"}:
            raise PortReleaseError("receipt_lane_invalid")


def _validate_journal(chain: _DirectoryChain) -> JsonObject | None:
    allowed_events = {
        "pre-inspection",
        "api-stop-intent",
        "api-stop-result",
        "api-no-stop-result",
        "ui-stop-intent",
        "ui-stop-result",
        "ui-no-stop-result",
        "final-post-inspection",
        "port-8000-bind-observation",
        "port-5173-bind-observation",
        "simultaneous-port-set-observation",
        "simultaneous-port-set-failed",
        "disposition-intent",
    }
    entries = chain.entries()
    if len(entries) > MAX_JOURNAL_ENTRIES:
        raise PortReleaseError("receipt_lane_invalid")
    observed_events: list[str] = []
    observed_payloads: list[dict[str, Any]] = []
    for sequence, name in enumerate(entries, start=1):
        if re.fullmatch(rf"{sequence:04d}-[a-z0-9-]+\.json", name) is None:
            raise PortReleaseError("receipt_lane_invalid")
        record = _read_json_leaf(chain, name, error_code="receipt_lane_invalid")
        event = record.get("event")
        if (
            record.get("schema_version") != "1"
            or record.get("record_type") != "attempt008_port_release_journal"
            or record.get("recovery_id") != RECOVERY_ID
            or record.get("sequence") != sequence
            or not isinstance(event, str)
            or event not in allowed_events
            or name != f"{sequence:04d}-{event}.json"
            or not isinstance(record.get("payload"), dict)
        ):
            raise PortReleaseError("receipt_lane_invalid")
        payload = cast(dict[str, Any], record["payload"])
        _validate_journal_payload(event, payload)
        observed_events.append(event)
        observed_payloads.append(payload)
    if len(set(observed_events)) != len(observed_events):
        raise PortReleaseError("receipt_lane_invalid")
    _validate_journal_sequence(observed_events, observed_payloads)
    if not observed_events or observed_events[-1] != "disposition-intent":
        return None
    intent_payload = observed_payloads[-1]
    status_value = cast(str, intent_payload["status"])
    if status_value == "completed":
        expected_suffix = [
            "final-post-inspection",
            "port-8000-bind-observation",
            "port-5173-bind-observation",
            "simultaneous-port-set-observation",
            "disposition-intent",
        ]
        if observed_events[-5:] != expected_suffix:
            raise PortReleaseError("receipt_lane_invalid")
        api_complete = (
            "api-no-stop-result" in observed_events
            or (
                "api-stop-intent" in observed_events
                and "api-stop-result" in observed_events
            )
        )
        ui_complete = (
            "ui-no-stop-result" in observed_events
            or (
                "ui-stop-intent" in observed_events
                and "ui-stop-result" in observed_events
            )
        )
        if not api_complete or not ui_complete:
            raise PortReleaseError("receipt_lane_invalid")
    outcome = cast(JsonObject, intent_payload["outcome"])
    if observed_events[0] == "disposition-intent":
        if outcome != _new_outcome():
            raise PortReleaseError("receipt_lane_invalid")
    else:
        if outcome["before_projections"] != observed_payloads[0]["projections"]:
            raise PortReleaseError("receipt_lane_invalid")
    if "final-post-inspection" in observed_events:
        final_index = observed_events.index("final-post-inspection")
        if (
            outcome["after_projections"]
            != observed_payloads[final_index]["projections"]
        ):
            raise PortReleaseError("receipt_lane_invalid")
    before_projections = cast(
        dict[str, dict[str, Any]],
        outcome["before_projections"],
    )
    after_projections = cast(
        dict[str, dict[str, Any]],
        outcome["after_projections"],
    )
    actions = cast(dict[str, Any], outcome["actions"])
    for target, service in (
        ("api", "ithildin-api"),
        ("ui", "ithildin-ui"),
    ):
        action = cast(dict[str, Any], actions[target])
        before_projection = before_projections.get(service)
        result_names = (
            f"{target}-stop-result",
            f"{target}-no-stop-result",
        )
        result_name = next(
            (name for name in result_names if name in observed_events),
            None,
        )
        intent_name = f"{target}-stop-intent"
        intent_payload_for_target = (
            observed_payloads[observed_events.index(intent_name)]
            if intent_name in observed_events
            else None
        )
        if action != {"status": "not_attempted"}:
            if (
                before_projection is None
                or action.get("service") != service
                or action.get("container_id")
                != before_projection.get("container_id")
                or action.get("image_id")
                != before_projection.get("image_id")
                or action.get("pre_running")
                != before_projection.get("running")
            ):
                raise PortReleaseError("receipt_lane_invalid")
        if intent_payload_for_target is not None and (
            action.get("service")
            != intent_payload_for_target["service"]
            or action.get("container_id")
            != intent_payload_for_target["container_id"]
            or action.get("image_id")
            != intent_payload_for_target["image_id"]
        ):
            raise PortReleaseError("receipt_lane_invalid")
        if result_name is not None:
            result_payload = observed_payloads[
                observed_events.index(result_name)
            ]
            result_status = result_payload["status"]
            result_post = result_payload["post_observation"]
            if (
                action.get("service") != result_payload["service"]
                or action.get("container_id")
                != result_payload["container_id"]
                or action.get("status") != result_payload["status"]
                or action.get("stop_returncode")
                != result_payload["returncode"]
                or action.get("post_observation")
                != result_payload["post_observation"]
                or (
                    result_name == f"{target}-no-stop-result"
                    and (
                        before_projection is None
                        or before_projection.get("running") is not False
                        or result_post != before_projection
                    )
                )
                or (
                    result_name == f"{target}-stop-result"
                    and (
                        before_projection is None
                        or before_projection.get("running") is not True
                    )
                )
                or (
                    result_status == "stopped_observed"
                    and (
                        not isinstance(result_post, dict)
                        or result_post.get("running") is not False
                    )
                )
                or (
                    result_status == "stop_not_observed"
                    and (
                        not isinstance(result_post, dict)
                        or result_post.get("running") is not True
                    )
                )
            ):
                raise PortReleaseError("receipt_lane_invalid")
        elif intent_name in observed_events:
            if (
                before_projection is None
                or before_projection.get("running") is not True
                or action.get("status") != "intent_durable_result_unknown"
            ):
                raise PortReleaseError("receipt_lane_invalid")
        elif action != {"status": "not_attempted"}:
            raise PortReleaseError("receipt_lane_invalid")
    preservation = cast(dict[str, str], outcome["preservation"])
    expected_preservation = {
        "volumes": "not_targeted_by_recovery",
        "networks": "not_targeted_by_recovery",
        "images": "not_targeted_by_recovery",
        "retained_runtime_and_evidence": "not_targeted_by_recovery",
    }
    for service in ("ithildin-node", "hermes"):
        expected_preservation[service] = (
            "not_targeted_by_recovery"
            if service not in before_projections
            else "observed_unchanged"
            if after_projections.get(service) == before_projections[service]
            else "observed_changed"
        )
    if preservation != expected_preservation:
        raise PortReleaseError("receipt_lane_invalid")
    expected_observations: list[JsonObject] = []
    for port in (8000, 5173):
        event = f"port-{port}-bind-observation"
        if event in observed_events:
            expected_observations.append(
                {
                    "host": "127.0.0.1",
                    "port": port,
                    "status": (
                        "confirmed_simultaneously_bound_point_in_time"
                        if "simultaneous-port-set-observation"
                        in observed_events
                        else "individual_bind_succeeded_but_set_failed"
                        if "simultaneous-port-set-failed" in observed_events
                        else "individual_bind_succeeded_pending_complete_set"
                    ),
                }
            )
    if "simultaneous-port-set-failed" in observed_events:
        failure_index = observed_events.index("simultaneous-port-set-failed")
        if observed_payloads[failure_index]["successful_ports"] != [
            item["port"] for item in expected_observations
        ]:
            raise PortReleaseError("receipt_lane_invalid")
    if outcome["port_observations"] != expected_observations:
        raise PortReleaseError("receipt_lane_invalid")
    return _disposition(
        status=status_value,
        outcome=outcome,
        failure_code=cast(str | None, intent_payload["failure_code"]),
    )


def _validate_disposition_record(record: dict[str, Any]) -> None:
    expected_keys = {
        "schema_version",
        "record_type",
        "recovery_id",
        "status",
        "outcome",
        "failure_code",
        "ports_point_in_time_available",
        "future_port_availability_claimed",
        "generic_port_owner_claimed",
        "full_project_cleanup_completed",
        "node_revocation_confirmed",
        "node_enrollment_ambiguous",
        "preservation",
        "retry_authorized",
        "release_allowed",
        "uat_complete",
    }
    outcome = record.get("outcome")
    preservation = record.get("preservation")
    allowed_preservation = {
        "not_targeted_by_recovery",
        "observed_unchanged",
        "observed_changed",
    }
    expected_preservation = {
        "ithildin-node",
        "hermes",
        "volumes",
        "networks",
        "images",
        "retained_runtime_and_evidence",
    }
    status_value = record.get("status")
    if (
        set(record) != expected_keys
        or record.get("schema_version") != "1"
        or record.get("record_type") != "attempt008_port_release_disposition"
        or record.get("recovery_id") != RECOVERY_ID
        or status_value not in {"completed", "failed"}
        or not isinstance(outcome, dict)
        or not isinstance(preservation, dict)
        or set(preservation) != expected_preservation
        or preservation != outcome.get("preservation")
        or set(preservation.values()) - allowed_preservation
        or (
            status_value == "completed"
            and record.get("failure_code") is not None
        )
        or (
            status_value == "failed"
            and (
                not isinstance(record.get("failure_code"), str)
                or re.fullmatch(
                    r"[a-z0-9_]{3,80}",
                    cast(str, record.get("failure_code")),
                )
                is None
            )
        )
        or record.get("future_port_availability_claimed") is not False
        or record.get("generic_port_owner_claimed") is not False
        or record.get("full_project_cleanup_completed") is not False
        or record.get("node_revocation_confirmed") is not False
        or record.get("node_enrollment_ambiguous") is not True
        or record.get("retry_authorized") is not False
        or record.get("release_allowed") is not False
        or record.get("uat_complete") is not False
    ):
        raise PortReleaseError("receipt_lane_invalid")
    _validate_outcome_document(outcome)
    derived = _disposition(
        status=cast(str, status_value),
        outcome=cast(JsonObject, outcome),
        failure_code=cast(str | None, record.get("failure_code")),
    )
    if record != derived:
        raise PortReleaseError("receipt_lane_invalid")


def inspect_receipt_lane(
    repo_root: Path,
    *,
    candidate_commit: str,
    candidate_tree: str,
) -> ReceiptLaneState:
    consumption_status = "presumed_consumed_unknown"
    disposition: dict[str, Any] | None = None
    try:
        chain = _open_relative_chain(
            repo_root,
            RECEIPT_ROOT,
            create=False,
            error_code="receipt_lane_invalid",
        )
        if chain is None:
            return ReceiptLaneState("unconsumed", True, None)
        with chain:
            entries = chain.entries()
            if not entries:
                return ReceiptLaneState("unconsumed", True, None)
            if CONSUMED_RECEIPT not in entries:
                return ReceiptLaneState(
                    "presumed_consumed_unknown",
                    False,
                    "receipt_lane_invalid",
                )
            consumed = _read_json_leaf(
                chain,
                CONSUMED_RECEIPT,
                error_code="receipt_lane_invalid",
            )
            if consumed != _consumption_record(candidate_commit, candidate_tree):
                return ReceiptLaneState(
                    "presumed_consumed_unknown",
                    False,
                    "receipt_lane_invalid",
                )
            consumption_status = "consumed"
            allowed = {CONSUMED_RECEIPT, JOURNAL_DIRECTORY, DISPOSITION_RECEIPT}
            if not set(entries) <= allowed:
                return ReceiptLaneState(
                    "consumed",
                    False,
                    "receipt_lane_invalid",
                )
            if DISPOSITION_RECEIPT in entries:
                disposition = _read_json_leaf(
                    chain,
                    DISPOSITION_RECEIPT,
                    error_code="receipt_lane_invalid",
                )
                _validate_disposition_record(disposition)
        journal = _open_relative_chain(
            repo_root,
            RECEIPT_ROOT / JOURNAL_DIRECTORY,
            create=False,
            error_code="receipt_lane_invalid",
        )
        expected_disposition: JsonObject | None = None
        if journal is not None:
            with journal:
                expected_disposition = _validate_journal(journal)
        if disposition is not None and (
            expected_disposition is None
            or disposition != expected_disposition
        ):
            raise PortReleaseError("receipt_lane_invalid")
        return ReceiptLaneState("consumed", True, None)
    except (OSError, PortReleaseError):
        return ReceiptLaneState(
            consumption_status,
            False,
            "receipt_lane_invalid",
        )


def build_report(repo_root: Path = ROOT) -> JsonObject:
    static_failures: list[str] = []
    execution_failures: list[str] = []
    commit = tree = ""
    try:
        commit, tree = candidate_identity(repo_root)
    except PortReleaseError as exc:
        static_failures.append(exc.code)
    if not static_failures:
        actions: tuple[Callable[[], object], ...] = (
            lambda: validate_authorization(
                repo_root,
                candidate_commit=commit,
                candidate_tree=tree,
            ),
            lambda: validate_tracked_disposition(repo_root),
            lambda: validate_attempt_001_port_release_disposition(
                repo_root
            ),
            lambda: validate_attempt_001_port_release_receipts(repo_root),
            lambda: validate_retained_receipts(repo_root),
            lambda: _validate_git_executable(),
            lambda: _validate_docker_executable(),
        )
        for action in actions:
            try:
                action()
            except (OSError, UnicodeError, PortReleaseError) as exc:
                static_failures.append(
                    exc.code
                    if isinstance(exc, PortReleaseError)
                    else "preflight_unavailable"
                )
    receipt_state = ReceiptLaneState(
        "presumed_consumed_unknown",
        False,
        "static_candidate_invalid",
    )
    if not static_failures:
        receipt_state = inspect_receipt_lane(
            repo_root,
            candidate_commit=commit,
            candidate_tree=tree,
        )
        if not receipt_state.valid:
            execution_failures.append(
                receipt_state.failure or "receipt_lane_invalid"
            )
        elif receipt_state.consumption_status == "consumed":
            execution_failures.append("attempt_budget_already_consumed")
        elif receipt_state.consumption_status != "unconsumed":
            execution_failures.append("attempt_consumption_unknown")
    static_valid = not static_failures
    execution_available = (
        static_valid
        and receipt_state.valid
        and receipt_state.consumption_status == "unconsumed"
    )
    all_failures = [*static_failures, *execution_failures]
    return {
        "valid": static_valid and receipt_state.valid,
        "static_candidate_valid": static_valid,
        "execution_available": execution_available,
        "recovery_id": RECOVERY_ID,
        "candidate_commit": commit,
        "candidate_tree": tree,
        "attempt_budget": (
            1
            if receipt_state.valid
            and receipt_state.consumption_status == "unconsumed"
            else 0
        ),
        "consumed": (
            True
            if receipt_state.consumption_status == "consumed"
            else False
            if receipt_state.consumption_status == "unconsumed"
            else None
        ),
        "consumption_status": receipt_state.consumption_status,
        "static_failures": cast(list[JsonValue], static_failures),
        "execution_failures": cast(list[JsonValue], execution_failures),
        "failures": cast(list[JsonValue], all_failures),
        "release_allowed": False,
        "uat_complete": False,
    }


def _parse_ids(output: str) -> list[str]:
    values = output.splitlines()
    if (
        not values
        or len(values) > 4
        or len(set(values)) != len(values)
        or any(re.fullmatch(r"[0-9a-f]{64}", value) is None for value in values)
    ):
        raise PortReleaseError("project_container_query_invalid")
    return sorted(values)


def _parse_projection(
    output: str,
    expected_id: str,
    *,
    allow_cleared_ports: bool = False,
) -> ContainerProjection:
    if len(output.encode("utf-8")) > 8192 or output.count("\n") > 1:
        raise PortReleaseError("container_projection_invalid")
    fields = output.removesuffix("\n").split("\t")
    if len(fields) != 7:
        raise PortReleaseError("container_projection_invalid")
    try:
        values = [json.loads(field, object_pairs_hook=_closed_object) for field in fields]
    except (ValueError, json.JSONDecodeError) as exc:
        raise PortReleaseError("container_projection_invalid") from exc
    container_id, image_id, project, service, running, status_value, ports = values
    if (
        container_id != expected_id
        or not isinstance(image_id, str)
        or project != PROJECT
        or not isinstance(service, str)
        or service not in SERVICES
        or type(running) is not bool
        or not isinstance(status_value, str)
        or status_value not in {"running", "exited", "created", "dead"}
        or (running is True and status_value != "running")
        or (running is False and status_value == "running")
        or not isinstance(ports, dict)
    ):
        raise PortReleaseError("container_projection_invalid")
    contract = SERVICES[service]
    expected_ports: JsonObject = {}
    if contract.container_port is not None:
        expected_ports = {
            contract.container_port: [
                {"HostIp": "127.0.0.1", "HostPort": cast(str, contract.host_port)}
            ]
        }
    ports_are_expected = ports == expected_ports
    ports_are_cleared_after_stop = (
        allow_cleared_ports
        and service in {"ithildin-api", "ithildin-ui"}
        and running is False
        and ports == {}
    )
    if image_id != contract.image_id or not (
        ports_are_expected or ports_are_cleared_after_stop
    ):
        raise PortReleaseError("container_projection_invalid")
    return ContainerProjection(
        expected_id,
        image_id,
        service,
        running,
        status_value,
        cast(JsonObject, ports),
    )


def _projection_record(projection: ContainerProjection) -> JsonObject:
    return {
        "container_id": projection.container_id,
        "image_id": projection.image_id,
        "service": projection.service,
        "running": projection.running,
        "status": projection.status,
        "ports": projection.ports,
    }


class JournalSink(Protocol):
    def record(self, event: str, payload: JsonObject) -> None: ...


def _new_outcome() -> JsonObject:
    return {
        "before_projections": {},
        "after_projections": {},
        "actions": {
            "api": {"status": "not_attempted"},
            "ui": {"status": "not_attempted"},
        },
        "preservation": {
            "ithildin-node": "not_targeted_by_recovery",
            "hermes": "not_targeted_by_recovery",
            "volumes": "not_targeted_by_recovery",
            "networks": "not_targeted_by_recovery",
            "images": "not_targeted_by_recovery",
            "retained_runtime_and_evidence": "not_targeted_by_recovery",
        },
        "port_observations": [],
    }


def _journal(
    sink: JournalSink | None,
    event: str,
    payload: JsonObject,
) -> None:
    if sink is not None:
        sink.record(event, payload)


def execute_port_release(
    executor: Executor,
    plan: Plan,
    *,
    progress: JsonObject | None = None,
    journal: JournalSink | None = None,
) -> JsonObject:
    outcomes = progress if progress is not None else _new_outcome()
    outcomes.clear()
    outcomes.update(_new_outcome())
    actions = cast(dict[str, Any], outcomes["actions"])
    preservation = cast(dict[str, Any], outcomes["preservation"])
    query = executor.read(plan.query())
    if query.returncode != 0:
        raise PortReleaseError("project_container_query_failed")
    container_ids = _parse_ids(query.stdout)
    if isinstance(executor, SubprocessExecutor):
        executor.bind_ids(set(container_ids))
    before: dict[str, ContainerProjection] = {}
    for container_id in container_ids:
        result = executor.read(plan.inspect(container_id))
        if result.returncode != 0:
            raise PortReleaseError("container_inspection_failed")
        projection = _parse_projection(result.stdout, container_id)
        if projection.service in before:
            raise PortReleaseError("duplicate_project_service")
        before[projection.service] = projection
    if set(before) - set(SERVICES) or not {"ithildin-api", "ithildin-ui"} <= set(before):
        raise PortReleaseError("project_container_set_invalid")
    before_record: JsonObject = {
        service: _projection_record(projection)
        for service, projection in sorted(before.items())
    }
    outcomes["before_projections"] = before_record
    _journal(
        journal,
        "pre-inspection",
        {
            "compose_project": PROJECT,
            "projections": before_record,
        },
    )
    if isinstance(executor, SubprocessExecutor):
        executor.bind_stop_targets(
            {
                "ithildin-api": before["ithildin-api"].container_id,
                "ithildin-ui": before["ithildin-ui"].container_id,
            }
        )
    for service in ("ithildin-api", "ithildin-ui"):
        outcome_key = "api" if service == "ithildin-api" else "ui"
        projection = before[service]
        action: JsonObject = {
            "service": service,
            "container_id": projection.container_id,
            "image_id": projection.image_id,
            "pre_running": projection.running,
            "status": "not_attempted",
            "stop_returncode": None,
            "post_observation": None,
        }
        actions[outcome_key] = action
        if projection.running:
            action["status"] = "intent_durable_result_unknown"
            _journal(
                journal,
                f"{outcome_key}-stop-intent",
                {
                    "service": service,
                    "container_id": projection.container_id,
                    "image_id": projection.image_id,
                    "action": "exact_container_stop_time_10",
                    "result_at_record_time": "unknown",
                },
            )
            stopped = executor.stop(
                service,
                plan.stop_command(service, projection.container_id),
            )
            action["stop_returncode"] = stopped.returncode
            if stopped.returncode != 0 or stopped.stdout:
                action["status"] = "stop_command_failed"
                _journal(
                    journal,
                    f"{outcome_key}-stop-result",
                    {
                        "service": service,
                        "container_id": projection.container_id,
                        "status": "stop_command_failed",
                        "returncode": stopped.returncode,
                        "post_observation": None,
                    },
                )
                raise PortReleaseError("container_stop_failed")
            immediate = executor.read(plan.inspect(projection.container_id))
            if immediate.returncode != 0:
                action["status"] = "stop_returned_post_observation_unavailable"
                _journal(
                    journal,
                    f"{outcome_key}-stop-result",
                    {
                        "service": service,
                        "container_id": projection.container_id,
                        "status": "stop_returned_post_observation_unavailable",
                        "returncode": stopped.returncode,
                        "post_observation": None,
                    },
                )
                raise PortReleaseError("container_postinspection_failed")
            observed = _parse_projection(
                immediate.stdout,
                projection.container_id,
                allow_cleared_ports=True,
            )
            if observed.service != service:
                action["status"] = "stop_returned_post_observation_invalid"
                raise PortReleaseError("container_postinspection_invalid")
            action["post_observation"] = _projection_record(observed)
            action["status"] = (
                "stop_not_observed" if observed.running else "stopped_observed"
            )
            _journal(
                journal,
                f"{outcome_key}-stop-result",
                {
                    "service": service,
                    "container_id": projection.container_id,
                    "status": cast(str, action["status"]),
                    "returncode": stopped.returncode,
                    "post_observation": _projection_record(observed),
                },
            )
            if observed.running:
                raise PortReleaseError("container_stop_not_observed")
        else:
            action["status"] = "already_stopped_no_stop_issued"
            action["post_observation"] = _projection_record(projection)
            _journal(
                journal,
                f"{outcome_key}-no-stop-result",
                {
                    "service": service,
                    "container_id": projection.container_id,
                    "status": "already_stopped_no_stop_issued",
                    "returncode": None,
                    "post_observation": _projection_record(projection),
                },
            )
    after: dict[str, ContainerProjection] = {}
    post_query = executor.read(plan.query())
    if post_query.returncode != 0:
        raise PortReleaseError("project_container_postquery_failed")
    post_container_ids = _parse_ids(post_query.stdout)
    if post_container_ids != container_ids:
        raise PortReleaseError("project_container_postset_changed")
    for container_id in post_container_ids:
        result = executor.read(plan.inspect(container_id))
        if result.returncode != 0:
            raise PortReleaseError("container_postinspection_failed")
        projection = _parse_projection(
            result.stdout,
            container_id,
            allow_cleared_ports=True,
        )
        if projection.service in after:
            raise PortReleaseError("container_postinspection_invalid")
        after[projection.service] = projection
    if set(after) != set(before):
        raise PortReleaseError("container_postinspection_invalid")
    after_record: JsonObject = {
        service: _projection_record(projection)
        for service, projection in sorted(after.items())
    }
    outcomes["after_projections"] = after_record
    _journal(
        journal,
        "final-post-inspection",
        {
            "compose_project": PROJECT,
            "projections": after_record,
        },
    )
    for service in ("ithildin-api", "ithildin-ui"):
        outcome_key = "api" if service == "ithildin-api" else "ui"
        if after[service].running:
            cast(dict[str, Any], actions[outcome_key])["status"] = (
                "stop_not_observed"
            )
            raise PortReleaseError("container_stop_not_observed")
    for service in ("ithildin-node", "hermes"):
        if service not in before:
            preservation[service] = "not_targeted_by_recovery"
        elif after.get(service) == before[service]:
            preservation[service] = "observed_unchanged"
        else:
            preservation[service] = "observed_changed"
            raise PortReleaseError("preserved_container_changed")
    if isinstance(executor, SubprocessExecutor):
        executor.verify_final_identity()
    return outcomes


def observe_ports_available(
    progress: JsonObject,
    *,
    journal: JournalSink | None = None,
) -> None:
    sockets: list[socket.socket] = []
    observations = cast(list[JsonValue], progress["port_observations"])
    try:
        for port in (8000, 5173):
            bound = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bound.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
            bound.bind(("127.0.0.1", port))
            sockets.append(bound)
            observation: JsonObject = {
                "host": "127.0.0.1",
                "port": port,
                "status": "individual_bind_succeeded_pending_complete_set",
            }
            _journal(
                journal,
                f"port-{port}-bind-observation",
                observation,
            )
            observations.append(observation)
        _journal(
            journal,
            "simultaneous-port-set-observation",
            {
                "host": "127.0.0.1",
                "ports": [8000, 5173],
                "status": "simultaneously_bound_point_in_time",
            },
        )
        for observed_item in observations:
            cast(dict[str, Any], observed_item)["status"] = (
                "confirmed_simultaneously_bound_point_in_time"
            )
    except OSError as exc:
        for observed_item in observations:
            cast(dict[str, Any], observed_item)["status"] = (
                "individual_bind_succeeded_but_set_failed"
            )
        _journal(
            journal,
            "simultaneous-port-set-failed",
            {
                "host": "127.0.0.1",
                "successful_ports": [
                    cast(dict[str, Any], item)["port"] for item in observations
                ],
                "status": "complete_set_not_observed",
            },
        )
        raise PortReleaseError("point_in_time_port_bind_failed") from exc
    finally:
        for bound in sockets:
            bound.close()


@dataclass(frozen=True)
class ReceiptSession:
    repo_root: Path

    def journal(self) -> DurableJournal:
        return DurableJournal(self.repo_root)

    def finalize(
        self,
        journal: DurableJournal,
        *,
        status: str,
        outcome: JsonObject,
        failure_code: str | None,
    ) -> None:
        document = _disposition(
            status=status,
            outcome=outcome,
            failure_code=failure_code,
        )
        journal.record(
            "disposition-intent",
            {
                "status": status,
                "failure_code": failure_code,
                "outcome": outcome,
            },
        )
        chain = _open_relative_chain(
            self.repo_root,
            RECEIPT_ROOT,
            create=False,
            error_code="receipt_write_failed",
        )
        if chain is None:
            raise PortReleaseError("receipt_write_failed")
        with chain:
            _write_json_leaf_exclusive(
                chain,
                DISPOSITION_RECEIPT,
                document,
                error_code="receipt_write_failed",
            )


class DurableJournal:
    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root
        self._sequence = 0
        self._events: list[str] = []
        self._payloads: list[dict[str, Any]] = []
        self._disposition_intent_recorded = False
        chain = _open_relative_chain(
            repo_root,
            RECEIPT_ROOT / JOURNAL_DIRECTORY,
            create=True,
            error_code="journal_write_failed",
        )
        if chain is None:
            raise PortReleaseError("journal_write_failed")
        with chain:
            if chain.entries():
                raise PortReleaseError("journal_not_empty")

    def record(self, event: str, payload: JsonObject) -> None:
        if re.fullmatch(r"[a-z0-9-]{3,64}", event) is None:
            raise PortReleaseError("journal_event_invalid")
        next_sequence = self._sequence + 1
        if self._disposition_intent_recorded:
            raise PortReleaseError("journal_already_finalized")
        if next_sequence > MAX_JOURNAL_ENTRIES:
            raise PortReleaseError("journal_entry_limit")
        _validate_journal_payload(event, payload)
        prospective_events = [*self._events, event]
        prospective_payloads = [*self._payloads, payload]
        _validate_journal_sequence(
            prospective_events,
            prospective_payloads,
        )
        chain = _open_relative_chain(
            self._repo_root,
            RECEIPT_ROOT / JOURNAL_DIRECTORY,
            create=False,
            error_code="journal_write_failed",
        )
        if chain is None:
            raise PortReleaseError("journal_write_failed")
        with chain:
            if len(chain.entries()) != self._sequence:
                raise PortReleaseError("journal_sequence_invalid")
            _write_json_leaf_exclusive(
                chain,
                f"{next_sequence:04d}-{event}.json",
                {
                    "schema_version": "1",
                    "record_type": "attempt008_port_release_journal",
                    "recovery_id": RECOVERY_ID,
                    "sequence": next_sequence,
                    "event": event,
                    "payload": payload,
                },
                error_code="journal_write_failed",
            )
        self._sequence = next_sequence
        self._events.append(event)
        self._payloads.append(payload)
        if event == "disposition-intent":
            self._disposition_intent_recorded = True

    @property
    def disposition_intent_recorded(self) -> bool:
        return self._disposition_intent_recorded


def consume_budget(
    repo_root: Path,
    *,
    candidate_commit: str,
    candidate_tree: str,
) -> ReceiptSession:
    chain = _open_relative_chain(
        repo_root,
        RECEIPT_ROOT,
        create=True,
        error_code="receipt_root_invalid",
    )
    if chain is None:
        raise PortReleaseError("receipt_root_invalid")
    with chain:
        entries = chain.entries()
        if entries:
            state = inspect_receipt_lane(
                repo_root,
                candidate_commit=candidate_commit,
                candidate_tree=candidate_tree,
            )
            if state.consumption_status == "consumed":
                raise PortReleaseError("attempt_budget_already_consumed")
            raise PortReleaseError("receipt_root_invalid")
        try:
            _write_json_leaf_exclusive(
                chain,
                CONSUMED_RECEIPT,
                _consumption_record(candidate_commit, candidate_tree),
                error_code="receipt_write_failed",
            )
        except FileExistsError as exc:
            raise PortReleaseError("attempt_budget_already_consumed") from exc
    state = inspect_receipt_lane(
        repo_root,
        candidate_commit=candidate_commit,
        candidate_tree=candidate_tree,
    )
    if not state.valid or state.consumption_status != "consumed":
        raise PortReleaseError("receipt_root_invalid")
    return ReceiptSession(repo_root)


def _disposition(
    *,
    status: str,
    outcome: JsonObject,
    failure_code: str | None,
) -> JsonObject:
    observations = outcome.get("port_observations")
    confirmed_ports: set[int] = set()
    if isinstance(observations, list):
        for item in observations:
            if (
                isinstance(item, dict)
                and item.get("host") == "127.0.0.1"
                and item.get("status")
                == "confirmed_simultaneously_bound_point_in_time"
                and type(item.get("port")) is int
            ):
                confirmed_ports.add(cast(int, item["port"]))
    if (
        status not in {"completed", "failed"}
        or (status == "completed" and confirmed_ports != {8000, 5173})
        or (status == "completed" and failure_code is not None)
        or (
            status == "failed"
            and (
                failure_code is None
                or re.fullmatch(r"[a-z0-9_]{3,80}", failure_code) is None
            )
        )
    ):
        raise PortReleaseError("disposition_invalid")
    return {
        "schema_version": "1",
        "record_type": "attempt008_port_release_disposition",
        "recovery_id": RECOVERY_ID,
        "status": status,
        "outcome": outcome,
        "failure_code": failure_code,
        "ports_point_in_time_available": confirmed_ports == {8000, 5173},
        "future_port_availability_claimed": False,
        "generic_port_owner_claimed": False,
        "full_project_cleanup_completed": False,
        "node_revocation_confirmed": False,
        "node_enrollment_ambiguous": True,
        "preservation": outcome["preservation"],
        "retry_authorized": False,
        "release_allowed": False,
        "uat_complete": False,
    }


def _local_docker_socket() -> str:
    candidates = (
        Path("/var/run/docker.sock"),
        Path("/run/docker.sock"),
        Path("/Users/jake/.docker/run/docker.sock"),
    )
    observed: dict[tuple[int, int], Path] = {}
    for candidate in candidates:
        try:
            details = candidate.stat()
        except OSError:
            continue
        if stat.S_ISSOCK(details.st_mode):
            observed.setdefault((details.st_dev, details.st_ino), candidate)
    if len(observed) != 1:
        raise PortReleaseError("local_docker_socket_not_exact")
    return f"unix://{next(iter(observed.values()))}"


def _empty_docker_config(root: Path) -> Path:
    root.mkdir(mode=0o700)
    content = b'{"auths":{},"credHelpers":{}}\n'
    directory = os.open(root, DIRECTORY_OPEN_FLAGS)
    descriptor = -1
    try:
        descriptor = os.open(
            "config.json",
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0),
            0o600,
            dir_fd=directory,
        )
        if os.write(descriptor, content) != len(content):
            raise PortReleaseError("docker_config_write_failed")
        os.fsync(descriptor)
        details = os.fstat(descriptor)
        os.fsync(directory)
        if (
            not stat.S_ISREG(details.st_mode)
            or stat.S_IMODE(details.st_mode) != 0o600
            or details.st_uid != os.geteuid()
            or details.st_gid != os.getegid()
            or details.st_size != len(content)
        ):
            raise PortReleaseError("docker_config_write_failed")
    except OSError as exc:
        raise PortReleaseError("docker_config_write_failed") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        os.close(directory)
    return root


def _reject_authority_environment(environment: Mapping[str, str]) -> None:
    for key in environment:
        normalized = key.upper()
        if (
            normalized in AUTHORITY_ENVIRONMENT_KEYS
            or normalized.startswith(PROVIDER_ENVIRONMENT_PREFIXES)
            or any(marker in normalized for marker in SECRET_ENVIRONMENT_MARKERS)
        ):
            raise PortReleaseError("ambient_authority_environment_rejected")


def run_live(environment: dict[str, str] | None = None) -> None:
    report = build_report(ROOT)
    if (
        report["static_candidate_valid"] is not True
        or report["execution_available"] is not True
    ):
        raise PortReleaseError("port_release_not_authorized")
    commit = cast(str, report["candidate_commit"])
    tree = cast(str, report["candidate_tree"])
    receipts = consume_budget(
        ROOT,
        candidate_commit=commit,
        candidate_tree=tree,
    )
    outcome = _new_outcome()
    journal = receipts.journal()
    try:
        source = os.environ if environment is None else environment
        _reject_authority_environment(source)
        docker_host = _local_docker_socket()
        with SealedDockerExecutable.create() as sealed:
            plan = Plan(sealed.path)
            with tempfile.TemporaryDirectory(
                prefix="ithildin-attempt008-port-release-"
            ) as temp:
                config = _empty_docker_config(Path(temp) / "docker-config")
                isolated = {
                    "DOCKER_HOST": docker_host,
                    "DOCKER_CONFIG": str(config),
                }
                outcome = execute_port_release(
                    SubprocessExecutor(isolated, plan, sealed),
                    plan,
                    progress=outcome,
                    journal=journal,
                )
        observe_ports_available(outcome, journal=journal)
        receipts.finalize(
            journal,
            status="completed",
            outcome=outcome,
            failure_code=None,
        )
    except BaseException as exc:
        failure = (
            exc.code
            if isinstance(exc, PortReleaseError)
            else "port_release_unexpected_failure"
        )
        if not journal.disposition_intent_recorded:
            try:
                receipts.finalize(
                    journal,
                    status="failed",
                    outcome=outcome,
                    failure_code=failure,
                )
            except (OSError, PortReleaseError):
                pass
        if isinstance(exc, PortReleaseError):
            raise
        raise PortReleaseError(failure) from None


def main(arguments: list[str] | None = None) -> int:
    effective = sys.argv[1:] if arguments is None else arguments
    if effective:
        print("attempt008_port_release_error: arguments_not_allowed")
        return 2
    try:
        run_live()
    except PortReleaseError as exc:
        print(f"attempt008_port_release_error: {exc.code}")
        return 1
    except KeyboardInterrupt:
        print("attempt008_port_release_error: interrupted")
        return 1
    except Exception:
        print("attempt008_port_release_error: unexpected_failure")
        return 1
    print("attempt008_port_release_status: completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

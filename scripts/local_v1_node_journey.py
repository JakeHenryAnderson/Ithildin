"""Run the bounded Local-v1 synthetic Node onboarding journey.

This is a deliberate live-local evidence command. It operates only against a uniquely named
Compose project and isolated ignored state. It does not exercise governed tools, missions,
runner execution, arbitrary host control, production identity, or PostgreSQL.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import socket
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, cast

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from ithildin_api.node_configuration import (
    CONFIGURATION_STATE_STORED_CURRENT_NOT_ENFORCED,
)
from ithildin_api.nodes import NODE_OBSERVED_STATE_CONNECTED
from ithildin_schemas import JsonObject, canonical_json

from scripts.local_v1_node_journey_evidence import (
    REPORT_JSON,
    REPORT_MARKDOWN,
    SCHEMA_VERSION,
    EvidenceValidationError,
    nonclaims_json_value,
    reject_secret_fields,
    render_markdown,
    scan_safe_text,
    validate_report,
)

ROOT = Path(__file__).resolve().parents[1]
REPORT_BASE = ROOT / "var/local-v1-node-journey"
RUNTIME_BASE = ROOT / "var/local-v1-node-journey-runtime"
COMPOSE_FILE = ROOT / "deploy/docker-compose.yml"
HOST_API_URL = "http://127.0.0.1:8000"
COMPOSE_PROJECT_PREFIX = "ithildin-local-v1-node-"
NODE_VERSION = "0.1.0"
WORKSPACE_ID = "demo"
POLL_SECONDS = 90.0

_SAFE_ID = re.compile(r"^[A-Za-z0-9_.:@-]{1,128}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_NODE_ID = re.compile(r"^node_[0-9a-f]{32}$")
_RUN_ID = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")


class JourneyError(RuntimeError):
    """A fail-closed journey error carrying only a safe stable code."""

    def __init__(self, code: str) -> None:
        if not re.fullmatch(r"[a-z0-9_]{3,80}", code):
            raise ValueError("unsafe journey error code")
        super().__init__(code)
        self.code = code


@dataclass
class AnchoredRunDirectory:
    """Descriptor-anchored run directory with no-follow creation and cleanup."""

    base_path: Path
    name: str
    base_descriptor: int
    run_descriptor: int
    base_device: int
    base_inode: int
    run_device: int
    run_inode: int

    @property
    def path(self) -> Path:
        return self.base_path / self.name

    @classmethod
    def create(cls, base_path: Path, name: str) -> AnchoredRunDirectory:
        if (
            not _RUN_ID.fullmatch(name)
            or base_path.parent != ROOT / "var"
            or base_path.name
            not in {"local-v1-node-journey", "local-v1-node-journey-runtime"}
        ):
            raise JourneyError("runtime_base_not_confined")
        var_descriptor = _open_directory(ROOT / "var")
        base_descriptor = -1
        run_descriptor = -1
        try:
            try:
                os.mkdir(base_path.name, 0o700, dir_fd=var_descriptor)
            except FileExistsError:
                pass
            base_descriptor = _open_directory_at(var_descriptor, base_path.name)
            try:
                os.mkdir(name, 0o700, dir_fd=base_descriptor)
            except FileExistsError as exc:
                raise JourneyError("run_directory_exists") from exc
            run_descriptor = _open_directory_at(base_descriptor, name)
            os.fchmod(run_descriptor, 0o700)
            base_status = os.fstat(base_descriptor)
            run_status = os.fstat(run_descriptor)
            anchored = cls(
                base_path=base_path,
                name=name,
                base_descriptor=base_descriptor,
                run_descriptor=run_descriptor,
                base_device=base_status.st_dev,
                base_inode=base_status.st_ino,
                run_device=run_status.st_dev,
                run_inode=run_status.st_ino,
            )
            base_descriptor = -1
            run_descriptor = -1
            anchored.validate()
            return anchored
        except OSError as exc:
            raise JourneyError("run_directory_create_failed") from exc
        finally:
            if run_descriptor >= 0:
                os.close(run_descriptor)
            if base_descriptor >= 0:
                os.close(base_descriptor)
            os.close(var_descriptor)

    def validate(self) -> None:
        if self.base_descriptor < 0 or self.run_descriptor < 0:
            raise JourneyError("run_directory_anchor_closed")
        try:
            base_current = os.lstat(self.base_path)
            base_held = os.fstat(self.base_descriptor)
            run_current = os.stat(
                self.name,
                dir_fd=self.base_descriptor,
                follow_symlinks=False,
            )
            run_held = os.fstat(self.run_descriptor)
        except OSError as exc:
            raise JourneyError("run_directory_identity_changed") from exc
        if (
            not stat.S_ISDIR(base_current.st_mode)
            or not stat.S_ISDIR(run_current.st_mode)
            or (base_current.st_dev, base_current.st_ino)
            != (self.base_device, self.base_inode)
            or (base_held.st_dev, base_held.st_ino)
            != (self.base_device, self.base_inode)
            or (run_current.st_dev, run_current.st_ino)
            != (self.run_device, self.run_inode)
            or (run_held.st_dev, run_held.st_ino)
            != (self.run_device, self.run_inode)
        ):
            raise JourneyError("run_directory_identity_changed")

    def mkdir(self, relative: str, *, mode: int = 0o700) -> None:
        self.validate()
        parts = _safe_relative_parts(relative)
        descriptor = os.dup(self.run_descriptor)
        try:
            for part in parts:
                try:
                    os.mkdir(part, mode, dir_fd=descriptor)
                except FileExistsError:
                    pass
                next_descriptor = _open_directory_at(descriptor, part)
                os.close(descriptor)
                descriptor = next_descriptor
                os.fchmod(descriptor, mode)
        except OSError as exc:
            raise JourneyError("runtime_directory_create_failed") from exc
        finally:
            os.close(descriptor)
        self.validate()

    def write_bytes(self, relative: str, content: bytes, *, mode: int) -> None:
        self.validate()
        parent_descriptor, name = self._open_parent(relative)
        descriptor = -1
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(name, flags, mode, dir_fd=parent_descriptor)
            os.fchmod(descriptor, mode)
            view = memoryview(content)
            while view:
                written = os.write(descriptor, view)
                view = view[written:]
            os.fsync(descriptor)
        except OSError as exc:
            raise JourneyError("runtime_file_create_failed") from exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            os.close(parent_descriptor)
        self.validate()

    def write_text(self, relative: str, content: str, *, mode: int) -> None:
        self.write_bytes(relative, content.encode("utf-8"), mode=mode)

    def file_path(self, relative: str) -> Path:
        _safe_relative_parts(relative)
        self.validate()
        return self.path / relative

    def file_mode(self, relative: str) -> int:
        self.validate()
        parent_descriptor, name = self._open_parent(relative)
        descriptor = -1
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(name, flags, dir_fd=parent_descriptor)
            details = os.fstat(descriptor)
            if not stat.S_ISREG(details.st_mode):
                raise JourneyError("runtime_file_not_regular")
            return stat.S_IMODE(details.st_mode)
        except OSError as exc:
            raise JourneyError("runtime_file_unavailable") from exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            os.close(parent_descriptor)

    def remove_tree(self) -> bool:
        """Delete only the inode-bound run contents and entry; retain on any uncertainty."""

        try:
            self.validate()
            _remove_directory_contents(self.run_descriptor)
            self.validate()
            os.rmdir(self.name, dir_fd=self.base_descriptor)
            self.close()
            return True
        except (JourneyError, OSError):
            return False

    def close(self) -> None:
        if self.run_descriptor >= 0:
            os.close(self.run_descriptor)
            self.run_descriptor = -1
        if self.base_descriptor >= 0:
            os.close(self.base_descriptor)
            self.base_descriptor = -1

    def _open_parent(self, relative: str) -> tuple[int, str]:
        parts = _safe_relative_parts(relative)
        descriptor = os.dup(self.run_descriptor)
        try:
            for part in parts[:-1]:
                next_descriptor = _open_directory_at(descriptor, part)
                os.close(descriptor)
                descriptor = next_descriptor
            return descriptor, parts[-1]
        except BaseException:
            os.close(descriptor)
            raise


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class JourneyRunResult:
    report_root: Path
    candidate_commit: str


class CommandExecutor(Protocol):
    def run(
        self,
        command: tuple[str, ...],
        *,
        input_text: str | None = None,
        timeout: float = 180.0,
    ) -> CommandResult: ...


class SubprocessExecutor:
    """Execute only the closed command vocabulary assembled by this module."""

    def __init__(self, environment: dict[str, str]) -> None:
        self._environment = dict(environment)

    def run(
        self,
        command: tuple[str, ...],
        *,
        input_text: str | None = None,
        timeout: float = 180.0,
    ) -> CommandResult:
        _validate_subprocess_command(command)
        try:
            result = subprocess.run(
                command,
                cwd=ROOT,
                input=input_text,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                env=self._environment,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise JourneyError("subprocess_unavailable") from exc
        return CommandResult(result.returncode, result.stdout, result.stderr)


class AnchoredExecutor:
    """Revalidate run-directory identity around every Docker CLI operation."""

    def __init__(
        self,
        delegate: CommandExecutor,
        anchors: tuple[AnchoredRunDirectory, ...],
    ) -> None:
        self._delegate = delegate
        self._anchors = anchors

    def run(
        self,
        command: tuple[str, ...],
        *,
        input_text: str | None = None,
        timeout: float = 180.0,
    ) -> CommandResult:
        for anchor in self._anchors:
            anchor.validate()
        result = self._delegate.run(command, input_text=input_text, timeout=timeout)
        for anchor in self._anchors:
            anchor.validate()
        return result


@dataclass(frozen=True)
class ComposePlan:
    project_name: str
    env_file: Path
    override_file: Path
    node_image: str

    @property
    def api_image(self) -> str:
        return f"{self.project_name}-ithildin-api"

    @property
    def ui_image(self) -> str:
        return f"{self.project_name}-ithildin-ui"

    @property
    def images(self) -> tuple[str, str, str]:
        return (self.api_image, self.ui_image, self.node_image)

    def command(self, *tail: str) -> tuple[str, ...]:
        return (
            "docker",
            "compose",
            "--project-name",
            self.project_name,
            "--env-file",
            str(self.env_file),
            "--file",
            str(COMPOSE_FILE),
            "--file",
            str(self.override_file),
            *tail,
        )

    def daemon_version(self) -> tuple[str, ...]:
        return ("docker", "version", "--format", "{{json .Server.Version}}")

    def config_check(self) -> tuple[str, ...]:
        return self.command("--profile", "node", "config", "--quiet")

    def project_containers(self) -> tuple[str, ...]:
        return (
            "docker",
            "ps",
            "--all",
            "--quiet",
            "--filter",
            f"label=com.docker.compose.project={self.project_name}",
        )

    def project_volumes(self) -> tuple[str, ...]:
        return (
            "docker",
            "volume",
            "ls",
            "--quiet",
            "--filter",
            f"label=com.docker.compose.project={self.project_name}",
        )

    def project_networks(self) -> tuple[str, ...]:
        return (
            "docker",
            "network",
            "ls",
            "--quiet",
            "--filter",
            f"label=com.docker.compose.project={self.project_name}",
        )

    def list_image(self, image: str) -> tuple[str, ...]:
        return (
            "docker",
            "image",
            "ls",
            "--quiet",
            "--no-trunc",
            "--filter",
            f"reference={image}",
        )

    def inspect_image(self, image: str) -> tuple[str, ...]:
        return ("docker", "image", "inspect", "--format", "{{.Id}}", image)

    def remove_image(self, image: str) -> tuple[str, ...]:
        return ("docker", "image", "rm", image)

    def start_stack(self) -> tuple[str, ...]:
        return self.command("up", "--build", "--detach", "ithildin-api", "ithildin-ui")

    def build_node(self) -> tuple[str, ...]:
        return self.command("--profile", "node", "build", "ithildin-node")

    def enroll_node(self) -> tuple[str, ...]:
        return self.command(
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
        )

    def start_node(self) -> tuple[str, ...]:
        return self.command(
            "--profile",
            "node",
            "up",
            "--detach",
            "--no-deps",
            "ithildin-node",
        )

    def stop_node(self) -> tuple[str, ...]:
        return self.command("--profile", "node", "stop", "ithildin-node")

    def revoked_heartbeat(self) -> tuple[str, ...]:
        return self.command(
            "--profile",
            "node",
            "run",
            "--rm",
            "-T",
            "--no-deps",
            "ithildin-node",
            "heartbeat",
            "--api-url",
            "http://ithildin-api:8000",
            "--state",
            "/var/lib/ithildin-node/state.json",
            "--configuration",
            "/var/lib/ithildin-node/configuration.json",
            "--node-version",
            NODE_VERSION,
            "--runner-adapter",
            "hermes",
            "--deployment-topology",
            "docker_sidecar",
        )

    def cleanup(self, *, remove_volumes: bool) -> tuple[str, ...]:
        tail = ["down", "--remove-orphans"]
        if remove_volumes:
            tail.append("--volumes")
        return self.command(*tail)


class LocalApi:
    """Closed local HTTP client that never exposes response bodies in errors."""

    def __init__(self, admin_token: str, *, timeout: float = 5.0) -> None:
        self._admin_token = admin_token
        self._timeout = timeout

    def get(self, path: str, *, admin: bool = True) -> JsonObject:
        return self._request("GET", path, None, admin=admin)

    def post(self, path: str, payload: JsonObject, *, admin: bool = True) -> JsonObject:
        _validate_http_payload(path, payload)
        return self._request("POST", path, payload, admin=admin)

    def _request(
        self,
        method: str,
        path: str,
        payload: JsonObject | None,
        *,
        admin: bool,
    ) -> JsonObject:
        _validate_http_operation(method, path, admin=admin)
        headers = {"Accept": "application/json"}
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = canonical_json(payload).encode()
        if admin:
            headers["Authorization"] = f"Bearer {self._admin_token}"
        request = urllib.request.Request(
            f"{HOST_API_URL}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                if response.status < 200 or response.status >= 300:
                    raise JourneyError("gateway_http_rejected")
                raw = response.read(262_145)
        except urllib.error.HTTPError as exc:
            raise JourneyError(f"gateway_http_{exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise JourneyError("gateway_unavailable") from exc
        if len(raw) > 262_144:
            raise JourneyError("gateway_response_too_large")
        try:
            document = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise JourneyError("gateway_response_invalid") from exc
        if not isinstance(document, dict):
            raise JourneyError("gateway_response_invalid")
        try:
            reject_secret_fields(
                document,
                allow_top_level_enrollment_code=path == "/nodes/enrollment-codes",
            )
        except EvidenceValidationError as exc:
            raise JourneyError("gateway_response_contains_secret_fields") from exc
        return cast(JsonObject, document)


class LocalUi:
    """Bounded health observation for the fixed local Command Center origin."""

    def __init__(self, *, timeout: float = 5.0) -> None:
        self._timeout = timeout

    def health(self) -> JsonObject:
        request = urllib.request.Request(
            "http://127.0.0.1:5173/",
            headers={"Accept": "text/html"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                content_type = response.headers.get_content_type()
                raw = response.read(262_145)
                status_code = response.status
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
            raise JourneyError("ui_unavailable") from exc
        if len(raw) > 262_144:
            raise JourneyError("ui_response_too_large")
        if status_code != 200 or content_type != "text/html":
            raise JourneyError("ui_health_invalid")
        try:
            text = raw.decode("utf-8")
        except UnicodeError as exc:
            raise JourneyError("ui_health_invalid") from exc
        if '<div id="root">' not in text:
            raise JourneyError("ui_shell_missing")
        return {
            "ui_http_status": 200,
            "ui_content_type": "text/html",
            "ui_shell_observed": True,
        }


@dataclass
class JourneyState:
    run_id: str
    candidate_commit: str
    source_clean_start: bool
    report_anchor: AnchoredRunDirectory
    runtime_anchor: AnchoredRunDirectory
    compose: ComposePlan
    started_at: str
    clock: Callable[[], datetime]
    stage: str = "preflight"
    stack_started: bool = False
    node_started: bool = False
    remote_enrollment_attempted: bool = False
    node_id: str | None = None
    node_revoked: bool = False
    recovery_required: bool = False
    node_image_build_attempted: bool = False
    node_image_built: bool = False
    candidate_commit_finish: str | None = None
    source_clean_finish: bool = False
    source_finish_observed: bool = False
    owned_image_references: set[str] = field(default_factory=set)
    created_images: dict[str, str] = field(default_factory=dict)
    image_reconciliation_ambiguous: bool = False
    safe_observations: JsonObject = field(default_factory=dict)

    @property
    def report_root(self) -> Path:
        return self.report_anchor.path

    @property
    def runtime_root(self) -> Path:
        return self.runtime_anchor.path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=POLL_SECONDS,
        help="bounded wait for API/UI health and Node acknowledgment",
    )
    args = parser.parse_args()
    if not 15.0 <= args.poll_seconds <= 300.0:
        parser.error("--poll-seconds must be between 15 and 300")
    try:
        result = run_live_journey(poll_seconds=args.poll_seconds)
    except JourneyError as exc:
        print(f"Local-v1 Node journey failed closed: {exc.code}", file=sys.stderr)
        return 1
    report_relative = result.report_root.relative_to(ROOT).as_posix()
    print(f"report_root={report_relative}")
    print(f"candidate_commit={result.candidate_commit}")
    print(
        "check_command=make local-v1-node-journey-check "
        f"LOCAL_V1_NODE_JOURNEY_REPORT={report_relative} "
        f"LOCAL_V1_NODE_JOURNEY_CANDIDATE={result.candidate_commit}"
    )
    return 0


def run_live_journey(
    *,
    poll_seconds: float = POLL_SECONDS,
    executor: CommandExecutor | None = None,
    api_factory: type[LocalApi] = LocalApi,
    ui_factory: type[LocalUi] = LocalUi,
    daemon_probe: Callable[[], str] | None = None,
    now: datetime | None = None,
) -> JourneyRunResult:
    effective_now = now or datetime.now(UTC)
    clock: Callable[[], datetime] = (
        (lambda: effective_now) if now is not None else (lambda: datetime.now(UTC))
    )
    candidate_commit = _git_observation(("rev-parse", "HEAD"))
    source_clean = _git_observation(
        ("status", "--porcelain=v1", "--untracked-files=normal")
    ) == ""
    if not _COMMIT.fullmatch(candidate_commit) or not source_clean:
        raise JourneyError("source_candidate_not_clean")
    _reject_ambient_docker_authority()
    docker_endpoint = (daemon_probe or _prove_local_docker_socket)()
    _require_ports_available((8000, 5173))

    run_id = _run_id(effective_now)
    report_anchor = AnchoredRunDirectory.create(REPORT_BASE, run_id)
    try:
        runtime_anchor = AnchoredRunDirectory.create(RUNTIME_BASE, run_id)
    except BaseException:
        report_anchor.remove_tree()
        report_anchor.close()
        raise

    env_file = runtime_anchor.file_path("compose.env")
    override_file = runtime_anchor.file_path("compose.override.yml")
    project_name = COMPOSE_PROJECT_PREFIX + run_id[-8:]
    node_image = f"ithildin/node-journey:{run_id[-8:]}"
    compose = ComposePlan(project_name, env_file, override_file, node_image)
    state = JourneyState(
        run_id=run_id,
        candidate_commit=candidate_commit,
        source_clean_start=source_clean,
        report_anchor=report_anchor,
        runtime_anchor=runtime_anchor,
        compose=compose,
        started_at=_timestamp(effective_now),
        clock=clock,
    )
    admin_token = secrets.token_urlsafe(48)
    enrollment_code: str | None = None
    api: LocalApi | None = None
    try:
        _prepare_isolated_runtime(state, admin_token)
        environment = _isolated_docker_environment(state, docker_endpoint)
        delegate = executor or SubprocessExecutor(environment)
        command_executor = AnchoredExecutor(
            delegate,
            (state.report_anchor, state.runtime_anchor),
        )
        _preflight(state, command_executor)
        api = api_factory(admin_token)
        ui = ui_factory()
        _start_normal_stack(
            state,
            command_executor,
            api,
            ui,
            poll_seconds=poll_seconds,
        )
        workspace = _select_workspace(api)
        state.safe_observations["workspace"] = workspace
        issued = api.post(
            "/nodes/enrollment-codes",
            {
                "workspace_id": workspace["workspace_id"],
                "display_name": f"Local v1 synthetic Node {run_id[-8:]}",
            },
        )
        enrollment_code = _parse_issued_enrollment_code(issued, run_id)
        state.safe_observations["code_handling"] = {
            "secret_returned_once": True,
            "transport": "compose_stdin_only",
            "recorded": False,
        }
        state.stage = "enrollment"
        state.remote_enrollment_attempted = True
        state.recovery_required = True
        enrollment = command_executor.run(
            compose.enroll_node(),
            input_text=enrollment_code + "\n",
            timeout=180.0,
        )
        _reject_secret_output(enrollment, (admin_token, enrollment_code))
        if enrollment.returncode != 0:
            state.recovery_required = True
            raise JourneyError("enrollment_outcome_ambiguous")
        enrollment_summary = _parse_safe_command_json(enrollment, "enrollment_output_invalid")
        node_id = _required_pattern(enrollment_summary, "node_id", _NODE_ID)
        principal_id = _required_safe_id(enrollment_summary, "principal_id")
        workspace_id = _required_safe_id(enrollment_summary, "workspace_id")
        if principal_id != f"agent:node.{node_id}" or workspace_id != workspace["workspace_id"]:
            state.recovery_required = True
            raise JourneyError("enrollment_identity_binding_invalid")
        state.node_id = node_id
        inventory = api.get(f"/nodes/{node_id}")
        _verify_gateway_identity(inventory, node_id, principal_id, workspace_id)
        state.recovery_required = False
        state.safe_observations["enrollment"] = {
            "node_id": node_id,
            "principal_id": principal_id,
            "workspace_id": workspace_id,
            "identity_source": "gateway_derived",
            "gateway_evidence_status": "complete",
        }

        state.stage = "configuration_assignment"
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
        generation = _required_int(assignment, "generation", minimum=1)
        configuration_digest = _required_pattern(
            assignment, "configuration_digest", _DIGEST
        )
        if assignment.get("evidence_status") != "complete":
            raise JourneyError("configuration_assignment_evidence_incomplete")
        state.safe_observations["configuration_assignment"] = {
            "generation": generation,
            "configuration_digest": configuration_digest,
            "evidence_status": "complete",
            "enforcement_status": "stored_not_enforced",
        }

        state.stage = "node_synchronization"
        state.node_started = True
        _require_success(command_executor.run(compose.start_node()), "node_service_start_failed")
        synchronized = _poll_node(
            api,
            node_id,
            generation=generation,
            configuration_digest=configuration_digest,
            poll_seconds=poll_seconds,
        )
        state.safe_observations["synchronization"] = synchronized
        _require_success(command_executor.run(compose.stop_node()), "node_service_stop_failed")
        state.node_started = False

        state.stage = "revocation"
        revoked = api.post(f"/nodes/{node_id}/revoke", {})
        if (
            revoked.get("status") != "revoked"
            or revoked.get("evidence_status") != "complete"
            or revoked.get("node_id") != node_id
        ):
            raise JourneyError("node_revocation_invalid")
        state.node_revoked = True
        rejected = command_executor.run(compose.revoked_heartbeat(), timeout=120.0)
        _reject_secret_output(rejected, (admin_token, enrollment_code))
        if (
            rejected.returncode == 0
            or "Gateway rejected Node request with HTTP 401" not in rejected.stderr
        ):
            raise JourneyError("revoked_request_rejection_not_proven")
        state.safe_observations["revocation"] = {
            "node_id": node_id,
            "status": "revoked",
            "gateway_evidence_status": "complete",
            "subsequent_signed_heartbeat_rejected": True,
            "rejection_output_recorded": False,
        }

        state.stage = "final_source_observation"
        final_commit = _git_observation(("rev-parse", "HEAD"))
        final_clean = _git_observation(
            ("status", "--porcelain=v1", "--untracked-files=normal")
        ) == ""
        state.candidate_commit_finish = final_commit
        state.source_clean_finish = final_clean
        state.source_finish_observed = True
        if final_commit != candidate_commit or not final_clean:
            raise JourneyError("source_candidate_changed_during_journey")
        state.stage = "complete"
        cleanup = _cleanup(state, command_executor, api=api)
        report = _report(state, result="passed", cleanup=cleanup)
        try:
            validate_report(
                report,
                directory_run_id=state.run_id,
                expected_candidate=state.candidate_commit,
                now=state.clock(),
            )
        except EvidenceValidationError as exc:
            raise JourneyError("internal_report_validation_failed") from exc
        _write_reports(
            state.report_anchor,
            report,
            secrets_to_reject=(admin_token, enrollment_code),
        )
        state.report_anchor.close()
        return JourneyRunResult(state.report_root, state.candidate_commit)
    except BaseException as raw_error:
        failure_code = (
            raw_error.code
            if isinstance(raw_error, JourneyError)
            else "interrupted"
            if isinstance(raw_error, KeyboardInterrupt)
            else "unexpected_failure"
        )
        possible_executor = locals().get("command_executor")
        if isinstance(possible_executor, AnchoredExecutor):
            cleanup_executor = possible_executor
        else:
            delegate = executor or _UnavailableExecutor()
            cleanup_executor = AnchoredExecutor(
                delegate,
                (state.report_anchor, state.runtime_anchor),
            )
        cleanup = _cleanup(state, cleanup_executor, api=api)
        report = _report(state, result="failed", cleanup=cleanup, failure_code=failure_code)
        try:
            _write_reports(
                state.report_anchor,
                report,
                secrets_to_reject=tuple(
                    secret for secret in (admin_token, enrollment_code) if secret is not None
                ),
            )
        except BaseException:
            pass
        state.report_anchor.close()
        state.runtime_anchor.close()
        raise JourneyError(failure_code) from None


def _prepare_isolated_runtime(state: JourneyState, admin_token: str) -> None:
    anchor = state.runtime_anchor
    for relative in (
        "var/db",
        "var/logs",
        "var/keys",
        "workspaces/demo",
        "authority",
        "docker-config",
    ):
        anchor.mkdir(relative)
    workspace_registry = (ROOT / "workspaces/local.yaml").read_bytes()
    if len(workspace_registry) > 65_536:
        raise JourneyError("workspace_registry_too_large")
    anchor.write_bytes("workspaces/local.yaml", workspace_registry, mode=0o600)
    private_key = Ed25519PrivateKey.generate()
    anchor.write_bytes(
        "var/keys/node-configuration-ed25519-private.pem",
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ),
        mode=0o600,
    )
    anchor.write_bytes(
        "var/keys/node-configuration-ed25519-public.pem",
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ),
        mode=0o644,
    )
    anchor.write_text("authority/api-candidate.json", "{}\n", mode=0o400)
    anchor.write_text(
        "compose.env",
        "\n".join(
            (
                f"ITHILDIN_ADMIN_TOKEN={admin_token}",
                "ITHILDIN_ALLOW_DEV_ADMIN_TOKEN=false",
                "ITHILDIN_STORAGE_BACKEND=sqlite",
                "ITHILDIN_POSTGRES_DSN=",
                f"ITHILDIN_CONTAINER_UID={os.getuid()}",
                f"ITHILDIN_CONTAINER_GID={os.getgid()}",
                "",
            )
        ),
        mode=0o600,
    )
    anchor.write_text(
        "compose.override.yml",
        _compose_override(state.runtime_root, state.compose.node_image),
        mode=0o600,
    )


def _isolated_docker_environment(
    state: JourneyState,
    docker_endpoint: str,
) -> dict[str, str]:
    state.runtime_anchor.validate()
    config_path = state.runtime_anchor.file_path("docker-config")
    if stat.S_IMODE(config_path.stat().st_mode) != 0o700 or any(config_path.iterdir()):
        raise JourneyError("docker_config_not_isolated")
    environment = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "DOCKER_HOST": docker_endpoint,
        "DOCKER_CONFIG": str(config_path),
    }
    if "TMPDIR" in os.environ:
        environment["TMPDIR"] = os.environ["TMPDIR"]
    return environment


def _preflight(state: JourneyState, executor: CommandExecutor) -> None:
    if not COMPOSE_FILE.is_file():
        raise JourneyError("compose_file_unavailable")
    for relative, expected_mode in (
        ("compose.env", 0o600),
        ("compose.override.yml", 0o600),
        ("var/keys/node-configuration-ed25519-private.pem", 0o600),
    ):
        if state.runtime_anchor.file_mode(relative) != expected_mode:
            raise JourneyError("runtime_file_permissions_invalid")
    _require_success(executor.run(state.compose.daemon_version()), "docker_daemon_unavailable")
    _require_success(executor.run(state.compose.config_check()), "compose_configuration_invalid")
    for command in (
        state.compose.project_containers(),
        state.compose.project_volumes(),
        state.compose.project_networks(),
    ):
        residue = executor.run(command)
        _require_success(residue, "compose_project_inspection_failed")
        if residue.stdout.strip():
            raise JourneyError("isolated_compose_project_not_empty")
    for image in state.compose.images:
        existing = executor.run(state.compose.list_image(image))
        _require_success(existing, "journey_image_inspection_failed")
        if existing.stdout.strip():
            raise JourneyError("journey_image_tag_not_empty")
    state.safe_observations["preflight"] = {
        "isolated_compose_project": True,
        "isolated_sqlite_state": True,
        "postgres_dsn_consumed": False,
        "configuration_signer_ready": True,
        "runtime_candidate_authority": False,
        "production_identity_authority": False,
        "docker_daemon": "allowlisted_local_unix_socket",
        "docker_credentials_inherited": False,
        "ports_available_before_mutation": True,
    }


def _start_normal_stack(
    state: JourneyState,
    executor: CommandExecutor,
    api: LocalApi,
    ui: LocalUi,
    *,
    poll_seconds: float,
) -> None:
    state.stage = "compose_stack_start"
    state.stack_started = True
    stack_images = {state.compose.api_image, state.compose.ui_image}
    state.owned_image_references.update(stack_images)
    stack_result: CommandResult | None = None
    try:
        stack_result = executor.run(state.compose.start_stack(), timeout=600.0)
    finally:
        current_images = _reconcile_owned_images(state, executor)
    if stack_result is None:
        raise JourneyError("compose_start_failed")
    _require_success(stack_result, "compose_start_failed")
    if (
        state.image_reconciliation_ambiguous
        or not stack_images.issubset(current_images)
    ):
        raise JourneyError("journey_image_identity_invalid")
    deadline = time.monotonic() + poll_seconds
    while time.monotonic() < deadline:
        try:
            health = api.get("/healthz", admin=False)
            status = api.get("/system/status")
            ui_health = ui.health()
            if (
                health == {"status": "ok", "service": "ithildin-api"}
                and status.get("status") == "ok"
                and ui_health
                == {
                    "ui_http_status": 200,
                    "ui_content_type": "text/html",
                    "ui_shell_observed": True,
                }
            ):
                break
        except JourneyError:
            time.sleep(0.25)
    else:
        raise JourneyError("compose_stack_health_timeout")
    if status.get("tool_count") != 24:
        raise JourneyError("governed_tool_count_changed")
    runtime_candidate = status.get("runtime_candidate")
    if (
        not isinstance(runtime_candidate, dict)
        or runtime_candidate.get("posture") != "unreviewed_local"
    ):
        raise JourneyError("runtime_candidate_authority_unexpected")
    storage = status.get("storage")
    if not isinstance(storage, dict) or storage.get("runtime_backend") != "sqlite":
        raise JourneyError("storage_backend_not_sqlite")
    postgres = storage.get("postgres")
    if not isinstance(postgres, dict) or postgres.get("configured") is not False:
        raise JourneyError("postgres_dsn_unexpected")
    state.node_image_build_attempted = True
    state.owned_image_references.add(state.compose.node_image)
    node_build_result: CommandResult | None = None
    try:
        node_build_result = executor.run(state.compose.build_node(), timeout=600.0)
    finally:
        current_images = _reconcile_owned_images(state, executor)
    if node_build_result is None:
        raise JourneyError("node_image_build_failed")
    _require_success(node_build_result, "node_image_build_failed")
    state.node_image_built = True
    if (
        state.image_reconciliation_ambiguous
        or state.compose.node_image not in current_images
    ):
        raise JourneyError("journey_image_identity_invalid")
    state.safe_observations["normal_stack"] = {
        "api_healthy": True,
        **ui_health,
        "tool_count": 24,
        "storage_backend": "sqlite",
        "runtime_candidate_posture": "unreviewed_local",
        "node_image_built": True,
    }


def _select_workspace(api: LocalApi) -> JsonObject:
    document = api.get("/workspaces")
    records = document.get("workspaces")
    if not isinstance(records, list):
        raise JourneyError("workspace_inventory_invalid")
    for raw in records:
        if not isinstance(raw, dict):
            continue
        if raw.get("id") == WORKSPACE_ID and raw.get("enabled") is True:
            return {
                "workspace_id": WORKSPACE_ID,
                "selected_from_active_gateway_inventory": True,
            }
    raise JourneyError("required_active_workspace_unavailable")


def _poll_node(
    api: LocalApi,
    node_id: str,
    *,
    generation: int,
    configuration_digest: str,
    poll_seconds: float,
) -> JsonObject:
    deadline = time.monotonic() + poll_seconds
    while time.monotonic() < deadline:
        document = api.get(f"/nodes/{node_id}")
        if (
            document.get("desired_configuration_generation") == generation
            and document.get("desired_configuration_digest") == configuration_digest
            and document.get("acknowledged_configuration_generation") == generation
            and document.get("acknowledged_configuration_digest") == configuration_digest
            and document.get("last_configuration_digest") == configuration_digest
            and document.get("configuration_acknowledgment_status") == "stored_not_enforced"
            and document.get("configuration_state")
            == CONFIGURATION_STATE_STORED_CURRENT_NOT_ENFORCED
            and document.get("observed_state") == NODE_OBSERVED_STATE_CONNECTED
            and document.get("connectivity_source") == "gateway_accepted_heartbeat"
            and document.get("runner_health_known") is False
            and document.get("model_health_known") is False
        ):
            return {
                "node_id": node_id,
                "desired_generation": generation,
                "acknowledged_generation": generation,
                "configuration_digest": configuration_digest,
                "configuration_acknowledgment_status": "stored_not_enforced",
                "configuration_state": CONFIGURATION_STATE_STORED_CURRENT_NOT_ENFORCED,
                "observed_state": NODE_OBSERVED_STATE_CONNECTED,
                "connectivity_source": "gateway_accepted_heartbeat",
                "runner_health_known": False,
                "model_health_known": False,
            }
        time.sleep(0.25)
    raise JourneyError("node_synchronization_timeout")


def _reconcile_owned_images(
    state: JourneyState,
    executor: CommandExecutor,
) -> dict[str, str]:
    current: dict[str, str] = {}
    for image in sorted(state.owned_image_references):
        try:
            listed = executor.run(state.compose.list_image(image))
            if listed.returncode != 0:
                state.image_reconciliation_ambiguous = True
                continue
            listed_id = listed.stdout.strip()
            if not listed_id:
                continue
            inspected = executor.run(state.compose.inspect_image(image))
            inspected_id = inspected.stdout.strip()
            if (
                inspected.returncode != 0
                or not re.fullmatch(r"sha256:[0-9a-f]{64}", listed_id)
                or inspected_id != listed_id
            ):
                state.image_reconciliation_ambiguous = True
                continue
            previous = state.created_images.get(image)
            if previous is not None and previous != listed_id:
                state.image_reconciliation_ambiguous = True
                continue
            state.created_images[image] = listed_id
            current[image] = listed_id
        except JourneyError:
            state.image_reconciliation_ambiguous = True
    return current


def _cleanup(
    state: JourneyState,
    executor: CommandExecutor,
    *,
    api: LocalApi | None,
) -> JsonObject:
    docker_mutation_attempted = state.stack_started or state.node_image_build_attempted
    if state.node_id is not None and not state.node_revoked and api is not None:
        try:
            revoked = api.post(f"/nodes/{state.node_id}/revoke", {})
            state.node_revoked = (
                revoked.get("status") == "revoked"
                and revoked.get("evidence_status") == "complete"
                and revoked.get("node_id") == state.node_id
            )
        except JourneyError:
            state.node_revoked = False
        if state.node_revoked:
            state.recovery_required = False
        else:
            state.recovery_required = True
    node_stop_succeeded = not state.node_started
    if state.node_started:
        try:
            stopped = executor.run(state.compose.stop_node())
            node_stop_succeeded = stopped.returncode == 0
        except JourneyError:
            node_stop_succeeded = False
        state.node_started = False
    can_remove_state = (
        not state.remote_enrollment_attempted
        or (state.node_revoked and not state.recovery_required)
    )
    compose_cleanup_succeeded = not state.stack_started
    if state.stack_started:
        try:
            down = executor.run(state.compose.cleanup(remove_volumes=can_remove_state))
            compose_cleanup_succeeded = down.returncode == 0
        except JourneyError:
            compose_cleanup_succeeded = False
        state.stack_started = False

    current_images = _reconcile_owned_images(state, executor)
    images_removed = not current_images and not state.image_reconciliation_ambiguous
    if current_images and can_remove_state and not state.image_reconciliation_ambiguous:
        images_removed = True
        try:
            for image, expected_id in current_images.items():
                inspected = executor.run(state.compose.inspect_image(image))
                if (
                    inspected.returncode != 0
                    or inspected.stdout.strip() != expected_id
                ):
                    images_removed = False
                    break
                removed = executor.run(state.compose.remove_image(image))
                absent = executor.run(state.compose.list_image(image))
                if (
                    removed.returncode != 0
                    or absent.returncode != 0
                    or absent.stdout.strip()
                ):
                    images_removed = False
                    break
        except JourneyError:
            images_removed = False
    elif current_images:
        images_removed = False
    if state.image_reconciliation_ambiguous:
        images_removed = False

    resources_absent = not docker_mutation_attempted
    if compose_cleanup_succeeded and docker_mutation_attempted:
        try:
            resource_results = [
                executor.run(state.compose.project_containers()),
                executor.run(state.compose.project_volumes()),
                executor.run(state.compose.project_networks()),
            ]
            resources_absent = all(
                item.returncode == 0 and not item.stdout.strip()
                for item in resource_results
            )
        except JourneyError:
            resources_absent = False
    volumes_removed = can_remove_state and compose_cleanup_succeeded and resources_absent
    runtime_state_removed = False
    if volumes_removed and images_removed:
        runtime_state_removed = state.runtime_anchor.remove_tree()
    outcome = (
        "completed"
        if can_remove_state
        and compose_cleanup_succeeded
        and resources_absent
        and images_removed
        and runtime_state_removed
        else "recovery_required"
        if state.recovery_required
        else "incomplete"
    )
    image_evidence: JsonObject = {}
    for label, image in (
        ("api", state.compose.api_image),
        ("ui", state.compose.ui_image),
        ("node", state.compose.node_image),
    ):
        image_evidence[label] = {
            "reference": image,
            "image_id": state.created_images.get(image),
        }
    return {
        "unique_project": state.compose.project_name,
        "images": image_evidence,
        "node_stop_succeeded": node_stop_succeeded,
        "revocation_succeeded": state.node_revoked,
        "compose_down_succeeded": compose_cleanup_succeeded,
        "images_removed": images_removed,
        "resources_absent": resources_absent,
        "volumes_removed": volumes_removed,
        "runtime_state_removed": runtime_state_removed,
        "runtime_state_retained": not runtime_state_removed,
        "recovery_required": state.recovery_required,
        "outcome": outcome,
    }


def _report(
    state: JourneyState,
    *,
    result: str,
    cleanup: JsonObject,
    failure_code: str | None = None,
) -> JsonObject:
    finished_at = _timestamp(state.clock())
    report: JsonObject = {
        "schema_version": SCHEMA_VERSION,
        "run_id": state.run_id,
        "result": result,
        "provenance": {
            "candidate_commit": state.candidate_commit,
            "candidate_tree_clean_observed": state.source_clean_start,
            "candidate_commit_at_finish_observed": state.candidate_commit_finish,
            "candidate_tree_clean_at_finish_observed": state.source_clean_finish,
            "candidate_finish_observation_completed": state.source_finish_observed,
            "started_at_utc": state.started_at,
            "finished_at_utc": finished_at,
            "execution_mode": "live_local_synthetic",
            "candidate_binding": "observation_not_authority",
        },
        "last_stage": state.stage,
        "observations": state.safe_observations,
        "cleanup": cleanup,
        "redaction_scan": {
            "status": "passed",
            "forbidden_value_matches": 0,
            "generic_secret_pattern_matches": 0,
            "raw_http_headers_recorded": False,
            "raw_http_bodies_recorded": False,
            "raw_subprocess_output_recorded": False,
        },
        "authority": {
            "runtime_authority": False,
            "release_authority": False,
            "promotion_authority": False,
            "production_identity_authority": False,
            "production_storage_authority": False,
            "uat_complete": False,
        },
        "nonclaims": nonclaims_json_value(),
    }
    if failure_code is not None:
        report["failure"] = {"code": failure_code, "details_recorded": False}
    return report


def _write_reports(
    report_anchor: AnchoredRunDirectory,
    report: JsonObject,
    *,
    secrets_to_reject: tuple[str, ...],
) -> None:
    json_text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    markdown_text = render_markdown(report)
    _scan_safe_texts((json_text, markdown_text), secrets_to_reject)
    report_anchor.write_text(REPORT_JSON, json_text, mode=0o600)
    report_anchor.write_text(REPORT_MARKDOWN, markdown_text, mode=0o600)


def _compose_override(runtime_root: Path, node_image: str) -> str:
    runtime_var = (runtime_root / "var").as_posix()
    runtime_workspaces = (runtime_root / "workspaces").as_posix()
    authority = (runtime_root / "authority/api-candidate.json").as_posix()
    return f"""services:
  ithildin-api:
    volumes:
      - type: bind
        source: {runtime_var}
        target: /app/var
      - type: bind
        source: {runtime_workspaces}
        target: /app/workspaces
      - type: bind
        source: {authority}
        target: /run/ithildin-authority/api-candidate.json
        read_only: true
  ithildin-node:
    image: {node_image}
"""


def _validate_subprocess_command(command: tuple[str, ...]) -> None:
    if command == ("docker", "version", "--format", "{{json .Server.Version}}"):
        return
    if len(command) == 6 and command[:2] == ("docker", "ps"):
        label = command[5] if command[2:5] == ("--all", "--quiet", "--filter") else ""
        if re.fullmatch(
            r"label=com\.docker\.compose\.project=ithildin-local-v1-node-[0-9a-f]{8}",
            label,
        ):
            return
    if len(command) == 6 and command[:4] in {
        ("docker", "volume", "ls", "--quiet"),
        ("docker", "network", "ls", "--quiet"),
    }:
        if command[4] == "--filter" and re.fullmatch(
            r"label=com\.docker\.compose\.project=ithildin-local-v1-node-[0-9a-f]{8}",
            command[5],
        ):
            return
    image_pattern = (
        r"(?:ithildin/node-journey:[0-9a-f]{8}|"
        r"ithildin-local-v1-node-[0-9a-f]{8}-ithildin-(?:api|ui))"
    )
    if (
        len(command) == 7
        and command[:6]
        == ("docker", "image", "ls", "--quiet", "--no-trunc", "--filter")
        and re.fullmatch(f"reference={image_pattern}", command[6])
    ):
        return
    if (
        len(command) == 6
        and command[:5]
        == ("docker", "image", "inspect", "--format", "{{.Id}}")
        and re.fullmatch(image_pattern, command[5])
    ):
        return
    if (
        len(command) == 4
        and command[:3] == ("docker", "image", "rm")
        and re.fullmatch(image_pattern, command[3])
    ):
        return
    if len(command) < 11 or command[:2] != ("docker", "compose"):
        raise JourneyError("subprocess_command_not_allowed")
    required_flags = ("--project-name", "--env-file", "--file", "--file")
    positions = (2, 4, 6, 8)
    if tuple(command[position] for position in positions) != required_flags:
        raise JourneyError("subprocess_command_not_allowed")
    project = command[3]
    if not project.startswith(COMPOSE_PROJECT_PREFIX) or not re.fullmatch(
        r"[a-z0-9-]{12,63}", project
    ):
        raise JourneyError("subprocess_command_not_allowed")
    env_path = Path(command[5])
    compose_path = Path(command[7])
    override_path = Path(command[9])
    if compose_path != COMPOSE_FILE:
        raise JourneyError("subprocess_command_not_allowed")
    run_root = env_path.parent
    if (
        env_path.name != "compose.env"
        or override_path != run_root / "compose.override.yml"
        or run_root.parent != RUNTIME_BASE
        or not _RUN_ID.fullmatch(run_root.name)
        or project != COMPOSE_PROJECT_PREFIX + run_root.name[-8:]
    ):
        raise JourneyError("subprocess_command_not_allowed")
    tail = command[10:]
    allowed_exact = {
        ("--profile", "node", "config", "--quiet"),
        ("up", "--build", "--detach", "ithildin-api", "ithildin-ui"),
        ("--profile", "node", "build", "ithildin-node"),
        ("--profile", "node", "up", "--detach", "--no-deps", "ithildin-node"),
        ("--profile", "node", "stop", "ithildin-node"),
        ("down", "--remove-orphans"),
        ("down", "--remove-orphans", "--volumes"),
    }
    if tail in allowed_exact:
        return
    dummy = ComposePlan("", Path(), Path(), "")
    if tail == dummy.enroll_node()[10:]:
        return
    if tail == dummy.revoked_heartbeat()[10:]:
        return
    raise JourneyError("subprocess_command_not_allowed")


def _validate_http_operation(method: str, path: str, *, admin: bool) -> None:
    if urllib.parse.urlsplit(path).scheme or not path.startswith("/"):
        raise JourneyError("http_operation_not_allowed")
    allowed: set[tuple[str, str, bool]] = {
        ("GET", "/healthz", False),
        ("GET", "/system/status", True),
        ("GET", "/workspaces", True),
        ("POST", "/nodes/enrollment-codes", True),
    }
    if (method, path, admin) in allowed:
        return
    if re.fullmatch(r"/nodes/node_[0-9a-f]{32}", path) and method == "GET" and admin:
        return
    if (
        re.fullmatch(r"/nodes/node_[0-9a-f]{32}/(?:configurations|revoke)", path)
        and method == "POST"
        and admin
    ):
        return
    raise JourneyError("http_operation_not_allowed")


def _validate_http_payload(path: str, payload: JsonObject) -> None:
    if path == "/nodes/enrollment-codes":
        display_name = payload.get("display_name")
        if (
            set(payload) != {"workspace_id", "display_name"}
            or payload.get("workspace_id") != WORKSPACE_ID
            or not isinstance(display_name, str)
            or not re.fullmatch(r"Local v1 synthetic Node [0-9a-f]{8}", display_name)
        ):
            raise JourneyError("http_payload_not_allowed")
        return
    if re.fullmatch(r"/nodes/node_[0-9a-f]{32}/configurations", path):
        if payload != {
            "minimum_node_version": NODE_VERSION,
            "heartbeat_interval_seconds": 15,
            "offline_posture": "deny_governed_actions",
            "evidence_buffer_max_events": 1000,
            "validity_seconds": 3600,
        }:
            raise JourneyError("http_payload_not_allowed")
        return
    if re.fullmatch(r"/nodes/node_[0-9a-f]{32}/revoke", path):
        if payload:
            raise JourneyError("http_payload_not_allowed")
        return
    raise JourneyError("http_payload_not_allowed")


def _reject_ambient_docker_authority() -> None:
    if os.environ.get("DOCKER_HOST", "").strip():
        raise JourneyError("ambient_docker_host_rejected")
    if os.environ.get("DOCKER_CONTEXT", "").strip():
        raise JourneyError("ambient_docker_context_rejected")


def _prove_local_docker_socket(candidates: tuple[Path, ...] | None = None) -> str:
    effective_candidates = candidates or (
        Path("/var/run/docker.sock"),
        Path("/run/docker.sock"),
        Path.home() / ".docker/run/docker.sock",
    )
    endpoints: dict[tuple[int, int], Path] = {}
    for candidate in effective_candidates:
        try:
            details = candidate.stat()
        except OSError:
            continue
        if not stat.S_ISSOCK(details.st_mode):
            continue
        endpoints.setdefault((details.st_dev, details.st_ino), candidate)
    if not endpoints:
        raise JourneyError("local_docker_socket_unavailable")
    if len(endpoints) != 1:
        raise JourneyError("local_docker_socket_ambiguous")
    selected = next(iter(endpoints.values()))
    return f"unix://{selected}"


def _require_ports_available(ports: tuple[int, ...]) -> None:
    sockets: list[socket.socket] = []
    try:
        for port in ports:
            probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sockets.append(probe)
            try:
                probe.bind(("127.0.0.1", port))
            except OSError as exc:
                raise JourneyError(f"local_port_{port}_unavailable") from exc
    finally:
        for probe in sockets:
            probe.close()


def _git_environment() -> dict[str, str]:
    allowed = ("PATH", "HOME", "TMPDIR", "XDG_CONFIG_HOME")
    return {key: os.environ[key] for key in allowed if key in os.environ}


def _git_observation(arguments: tuple[str, ...]) -> str:
    if arguments not in {
        ("rev-parse", "HEAD"),
        ("status", "--porcelain=v1", "--untracked-files=normal"),
    }:
        raise JourneyError("git_observation_not_allowed")
    try:
        result = subprocess.run(
            ("git", *arguments),
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
            env=_git_environment(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise JourneyError("git_observation_failed") from exc
    if result.returncode != 0:
        raise JourneyError("git_observation_failed")
    return result.stdout.strip()


def _verify_gateway_identity(
    document: JsonObject,
    node_id: str,
    principal_id: str,
    workspace_id: str,
) -> None:
    expected = {
        "node_id": node_id,
        "principal_id": principal_id,
        "workspace_id": workspace_id,
        "identity_source": "gateway_derived",
        "evidence_status": "complete",
        "runner_health_known": False,
        "model_health_known": False,
    }
    if any(document.get(key) != value for key, value in expected.items()):
        raise JourneyError("gateway_identity_binding_invalid")


def _parse_safe_command_json(result: CommandResult, error_code: str) -> JsonObject:
    try:
        document = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise JourneyError(error_code) from exc
    if not isinstance(document, dict):
        raise JourneyError(error_code)
    try:
        reject_secret_fields(document)
    except EvidenceValidationError as exc:
        raise JourneyError("unsafe_subprocess_output") from exc
    return cast(JsonObject, document)


def _reject_secret_output(result: CommandResult, secrets_to_reject: tuple[str, ...]) -> None:
    _scan_safe_texts((result.stdout, result.stderr), secrets_to_reject)


def _scan_safe_texts(texts: tuple[str, ...], secrets_to_reject: tuple[str, ...]) -> None:
    for text in texts:
        try:
            scan_safe_text(text, secrets_to_reject)
        except EvidenceValidationError as exc:
            raise JourneyError("secret_detected_in_output") from exc


def _parse_issued_enrollment_code(document: JsonObject, run_id: str) -> str:
    if set(document) != {
        "code_id",
        "enrollment_code",
        "workspace_id",
        "display_name",
        "created_at",
        "expires_at",
        "secret_returned_once",
    }:
        raise JourneyError("enrollment_code_response_not_closed")
    value = document.get("enrollment_code")
    if not isinstance(value, str) or not 32 <= len(value) <= 256 or value != value.strip():
        raise JourneyError("enrollment_code_invalid")
    if (
        document.get("secret_returned_once") is not True
        or document.get("workspace_id") != WORKSPACE_ID
        or document.get("display_name") != f"Local v1 synthetic Node {run_id[-8:]}"
        or not isinstance(document.get("code_id"), str)
        or not re.fullmatch(r"ncode_[0-9a-f]{32}", cast(str, document["code_id"]))
        or not isinstance(document.get("created_at"), str)
        or not isinstance(document.get("expires_at"), str)
    ):
        raise JourneyError("enrollment_code_response_invalid")
    return value


def _required_pattern(document: JsonObject, key: str, pattern: re.Pattern[str]) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise JourneyError(f"{key}_invalid")
    return value


def _required_safe_id(document: JsonObject, key: str) -> str:
    return _required_pattern(document, key, _SAFE_ID)


def _required_int(document: JsonObject, key: str, *, minimum: int) -> int:
    value = document.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise JourneyError(f"{key}_invalid")
    return value


def _require_success(result: CommandResult, code: str) -> None:
    if result.returncode != 0:
        raise JourneyError(code)


def _run_id(now: datetime) -> str:
    prefix = now.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    value = f"{prefix}-{secrets.token_hex(4)}"
    if not _RUN_ID.fullmatch(value):
        raise JourneyError("run_id_invalid")
    return value


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _safe_relative_parts(relative: str) -> tuple[str, ...]:
    path = Path(relative)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise JourneyError("runtime_relative_path_invalid")
    return path.parts


def _open_directory(path: Path) -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise JourneyError("runtime_directory_unavailable") from exc
    if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise JourneyError("runtime_directory_unavailable")
    return descriptor


def _open_directory_at(parent: int, name: str) -> int:
    if "/" in name or name in {"", ".", ".."}:
        raise JourneyError("runtime_relative_path_invalid")
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(name, flags, dir_fd=parent)
    except OSError as exc:
        raise JourneyError("runtime_directory_unavailable") from exc
    if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise JourneyError("runtime_directory_unavailable")
    return descriptor


def _remove_directory_contents(descriptor: int) -> None:
    for entry in list(os.scandir(descriptor)):
        name = entry.name
        details = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
        if stat.S_ISDIR(details.st_mode):
            child = _open_directory_at(descriptor, name)
            try:
                _remove_directory_contents(child)
            finally:
                os.close(child)
            os.rmdir(name, dir_fd=descriptor)
        else:
            os.unlink(name, dir_fd=descriptor)


class _UnavailableExecutor:
    def run(
        self,
        command: tuple[str, ...],
        *,
        input_text: str | None = None,
        timeout: float = 180.0,
    ) -> CommandResult:
        del command, input_text, timeout
        raise JourneyError("subprocess_unavailable")


if __name__ == "__main__":
    raise SystemExit(main())

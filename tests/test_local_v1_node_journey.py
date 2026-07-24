from __future__ import annotations

import copy
import io
import json
import os
import stat
import subprocess
import sys
import urllib.error
from datetime import UTC, datetime, timedelta
from email.message import Message
from pathlib import Path
from types import TracebackType

import pytest
from ithildin_api.node_configuration import (
    CONFIGURATION_STATE_STORED_CURRENT_NOT_ENFORCED,
    configuration_state,
)
from ithildin_api.nodes import NODE_OBSERVED_STATE_CONNECTED
from ithildin_schemas import JsonObject

from scripts import local_v1_node_journey as journey
from scripts import local_v1_node_journey_check as checker
from scripts import local_v1_node_journey_evidence as evidence

REPO_ROOT = Path(__file__).resolve().parents[1]
NODE_ID = "node_" + "1" * 32
PRINCIPAL_ID = f"agent:node.{NODE_ID}"
DIGEST = "sha256:" + "2" * 64
COMMIT = "3" * 40
CODE = "one-time-code-" + "4" * 40
API_IMAGE_ID = "sha256:" + "a" * 64
UI_IMAGE_ID = "sha256:" + "b" * 64
NODE_IMAGE_ID = "sha256:" + "c" * 64
NOW = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
RUN_ID = "20260723T120000Z-aaaaaaaa"


class FakeExecutor:
    def __init__(
        self,
        *,
        enroll_returncode: int = 0,
        enroll_stdout: str | None = None,
        enroll_stderr: str = "",
        residue: str = "",
        interrupt_tail: tuple[str, ...] | None = None,
        interrupt: BaseException | None = None,
        preexisting_images: dict[str, str] | None = None,
        inspection_failure: bool = False,
        up_returncode: int = 0,
        node_build_returncode: int = 0,
        diagnostic_returncode: int = 0,
        diagnostic_stdout: str = (
            "ithildin-api\trunning\thealthy\t0\n"
            "ithildin-ui\trunning\t\t0\n"
        ),
        diagnostic_stderr: str = "",
    ) -> None:
        self.commands: list[tuple[tuple[str, ...], str | None]] = []
        self.enroll_returncode = enroll_returncode
        self.enroll_stdout = enroll_stdout or json.dumps(
            {
                "node_id": NODE_ID,
                "principal_id": PRINCIPAL_ID,
                "workspace_id": "demo",
                "private_key_present": True,
            }
        )
        self.enroll_stderr = enroll_stderr
        self.residue = residue
        self.interrupt_tail = interrupt_tail
        self.interrupt = interrupt
        self.images = dict(preexisting_images or {})
        self.inspection_failure = inspection_failure
        self.up_returncode = up_returncode
        self.node_build_returncode = node_build_returncode
        self.diagnostic_returncode = diagnostic_returncode
        self.diagnostic_stdout = diagnostic_stdout
        self.diagnostic_stderr = diagnostic_stderr
        self.profile_volume_present = False

    def run(
        self,
        command: tuple[str, ...],
        *,
        input_text: str | None = None,
        timeout: float = 180.0,
    ) -> journey.CommandResult:
        del timeout
        self.commands.append((command, input_text))
        tail = command[10:] if len(command) > 10 else command
        if self.interrupt_tail is not None and tail == self.interrupt_tail:
            assert self.interrupt is not None
            raise self.interrupt
        if command == ("docker", "version", "--format", "{{json .Server.Version}}"):
            return journey.CommandResult(0, '"27.0.0"\n', "")
        if command[:3] == ("docker", "volume", "ls"):
            volume = "synthetic-node-state-volume\n" if self.profile_volume_present else ""
            return journey.CommandResult(0, self.residue or volume, "")
        if command[:2] == ("docker", "ps") or command[:3] == (
            "docker",
            "network",
            "ls",
        ):
            return journey.CommandResult(0, self.residue, "")
        if command[:3] == ("docker", "image", "ls"):
            reference = command[6].removeprefix("reference=")
            return journey.CommandResult(0, self.images.get(reference, ""), "")
        if command[:3] == ("docker", "image", "inspect"):
            reference = command[5]
            if self.inspection_failure:
                return journey.CommandResult(1, "", "synthetic inspection failure")
            image_id = self.images.get(reference)
            return journey.CommandResult(0 if image_id else 1, image_id or "", "")
        if command[:3] == ("docker", "image", "rm"):
            self.images.pop(command[3], None)
            return journey.CommandResult(0, "", "")
        if "enroll" in tail:
            self.profile_volume_present = True
            return journey.CommandResult(
                self.enroll_returncode,
                self.enroll_stdout,
                self.enroll_stderr,
            )
        if "heartbeat" in tail:
            return journey.CommandResult(
                2,
                "",
                "Gateway rejected Node request with HTTP 401",
            )
        if tail[:1] == ("up",) and "--build" in tail:
            project = command[3]
            self.images[f"{project}-ithildin-api"] = API_IMAGE_ID
            self.images[f"{project}-ithildin-ui"] = UI_IMAGE_ID
            return journey.CommandResult(self.up_returncode, "", "synthetic up result")
        if tail[:4] == ("ps", "--all", "--format", journey.STACK_DIAGNOSTIC_FORMAT):
            return journey.CommandResult(
                self.diagnostic_returncode,
                self.diagnostic_stdout,
                self.diagnostic_stderr,
            )
        if tail == ("--profile", "node", "build", "ithildin-node"):
            self.images[f"ithildin/node-journey:{command[3][-8:]}"] = NODE_IMAGE_ID
            return journey.CommandResult(
                self.node_build_returncode,
                "",
                "synthetic build result",
            )
        if tail[:4] == ("--profile", "node", "down", "--remove-orphans"):
            if "--volumes" in tail:
                self.profile_volume_present = False
            return journey.CommandResult(0, "", "")
        return journey.CommandResult(0, "", "")


class FakeApi:
    revoke_succeeds = True
    secret_returned_once = True
    inventory_evidence_status = "complete"
    assignment_evidence_status = "complete"
    system_status_document: JsonObject | None = None

    def __init__(self, admin_token: str) -> None:
        self.admin_token = admin_token
        self.revoked = False

    def get(self, path: str, *, admin: bool = True) -> JsonObject:
        del admin
        if path == "/healthz":
            return {"status": "ok", "service": "ithildin-api"}
        if path == "/system/status":
            if self.system_status_document is not None:
                return copy.deepcopy(self.system_status_document)
            return {
                "status": "ok",
                "tool_count": 24,
                "runtime_candidate": {
                    "posture": "unreviewed_local",
                    "promotion_allowed": False,
                },
                "storage": {
                    "runtime_backend": "sqlite",
                    "postgres": {"configured": False},
                },
            }
        if path == "/workspaces":
            return {
                "workspaces": [
                    {"id": "demo", "enabled": True, "display_name": "Demo workspace"}
                ]
            }
        if path == f"/nodes/{NODE_ID}":
            return {
                "node_id": NODE_ID,
                "principal_id": PRINCIPAL_ID,
                "workspace_id": "demo",
                "identity_source": "gateway_derived",
                "evidence_status": self.inventory_evidence_status,
                "desired_configuration_generation": 1,
                "desired_configuration_digest": DIGEST,
                "acknowledged_configuration_generation": 1,
                "acknowledged_configuration_digest": DIGEST,
                "last_configuration_digest": DIGEST,
                "configuration_acknowledgment_status": "stored_not_enforced",
                "configuration_state": CONFIGURATION_STATE_STORED_CURRENT_NOT_ENFORCED,
                "observed_state": NODE_OBSERVED_STATE_CONNECTED,
                "connectivity_source": "gateway_accepted_heartbeat",
                "runner_health_known": False,
                "model_health_known": False,
            }
        raise AssertionError(f"unexpected GET {path}")

    def post(
        self,
        path: str,
        payload: JsonObject,
        *,
        admin: bool = True,
    ) -> JsonObject:
        del payload, admin
        if path == "/nodes/enrollment-codes":
            return {
                "code_id": "ncode_" + "5" * 32,
                "enrollment_code": CODE,
                "workspace_id": "demo",
                "display_name": "Local v1 synthetic Node aaaaaaaa",
                "created_at": "2026-07-23T12:00:00Z",
                "expires_at": "2026-07-23T12:05:00Z",
                "secret_returned_once": self.secret_returned_once,
            }
        if path == f"/nodes/{NODE_ID}/configurations":
            return {
                "generation": 1,
                "configuration_digest": DIGEST,
                "evidence_status": self.assignment_evidence_status,
            }
        if path == f"/nodes/{NODE_ID}/revoke":
            if not self.revoke_succeeds:
                raise journey.JourneyError("gateway_http_503")
            self.revoked = True
            return {
                "node_id": NODE_ID,
                "status": "revoked",
                "evidence_status": "complete",
            }
        raise AssertionError(f"unexpected POST {path}")


class FakeUi:
    def health(self) -> JsonObject:
        return {
            "ui_http_status": 200,
            "ui_content_type": "text/html",
            "ui_shell_observed": True,
        }


@pytest.fixture
def isolated_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path]:
    (tmp_path / "var").mkdir()
    (tmp_path / "workspaces").mkdir()
    (tmp_path / "deploy").mkdir()
    (tmp_path / "workspaces/local.yaml").write_text(
        (REPO_ROOT / "workspaces/local.yaml").read_text()
    )
    (tmp_path / "deploy/docker-compose.yml").write_text("services: {}\n")
    compose_plugin_directory = tmp_path / "synthetic-compose-plugin-dir"
    compose_plugin_directory.mkdir(mode=0o700)
    compose_plugin = compose_plugin_directory / "docker-compose"
    compose_plugin.write_text("#!/bin/sh\nexit 0\n")
    compose_plugin.chmod(0o700)
    reports = tmp_path / "var/local-v1-node-journey"
    runtime = tmp_path / "var/local-v1-node-journey-runtime"
    monkeypatch.setattr(journey, "ROOT", tmp_path)
    monkeypatch.setattr(journey, "REPORT_BASE", reports)
    monkeypatch.setattr(journey, "RUNTIME_BASE", runtime)
    monkeypatch.setattr(journey, "COMPOSE_FILE", tmp_path / "deploy/docker-compose.yml")
    monkeypatch.setattr(
        journey,
        "COMPOSE_PLUGIN_EXTRA_DIR_CANDIDATES",
        (compose_plugin_directory,),
    )
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    monkeypatch.setattr(checker, "REPORT_BASE", reports)
    monkeypatch.setattr(
        journey,
        "_git_observation",
        lambda arguments: COMMIT if arguments == ("rev-parse", "HEAD") else "",
    )
    monkeypatch.setattr(journey, "_require_ports_available", lambda ports: None)
    monkeypatch.setattr(journey.secrets, "token_hex", lambda length: "a" * (length * 2))
    monkeypatch.setattr(journey.secrets, "token_urlsafe", lambda length: "A" * length)
    monkeypatch.delenv("DOCKER_HOST", raising=False)
    monkeypatch.delenv("DOCKER_CONTEXT", raising=False)
    return reports, runtime


def run_fake(
    *,
    executor: journey.CommandExecutor | None = None,
    api_factory: type[FakeApi] = FakeApi,
    ui_factory: type[FakeUi] = FakeUi,
) -> Path:
    return journey.run_live_journey(
        executor=executor or FakeExecutor(),
        api_factory=api_factory,  # type: ignore[arg-type]
        ui_factory=ui_factory,  # type: ignore[arg-type]
        daemon_probe=lambda: "unix:///var/run/docker.sock",
        now=NOW,
        poll_seconds=0.01,
    ).report_root


def load_run_report(report_root: Path) -> JsonObject:
    value = json.loads((report_root / journey.REPORT_JSON).read_text())
    assert isinstance(value, dict)
    return value


def production_node_inventory(*, assigned: bool) -> JsonObject:
    generation = 1 if assigned else None
    digest = DIGEST if assigned else None
    return {
        "node_id": NODE_ID,
        "principal_id": PRINCIPAL_ID,
        "workspace_id": "demo",
        "identity_source": "gateway_derived",
        "evidence_status": "complete",
        "desired_configuration_generation": generation,
        "desired_configuration_digest": digest,
        "acknowledged_configuration_generation": generation,
        "acknowledged_configuration_digest": digest,
        "last_configuration_digest": digest,
        "configuration_acknowledgment_status": (
            "stored_not_enforced" if assigned else None
        ),
        "configuration_state": (
            CONFIGURATION_STATE_STORED_CURRENT_NOT_ENFORCED
            if assigned
            else "unassigned"
        ),
        "observed_state": (
            NODE_OBSERVED_STATE_CONNECTED if assigned else "never_observed"
        ),
        "connectivity_source": "gateway_accepted_heartbeat",
        "runner_health_known": False,
        "model_health_known": False,
        "descriptor": {
            "runner_adapter": "hermes",
            "private_key_received": False,
        },
        "public_key": "ignored-public-key-material",
        "active_identity_key_id": "ignored-identity-key-id",
        "configuration_signing_key_id": "ignored-configuration-key-id",
        "identity_key_rotation": {
            "status": "none",
            "private_key_received": False,
        },
        "governed_access": {
            "state": "ready",
            "authorization_profile": "read_only_governed",
            "allowed_risks": ["read"],
            "offline_fallback_allowed": False,
        },
    }


def test_successful_fake_journey_writes_exact_checkable_redacted_evidence(
    isolated_roots: tuple[Path, Path],
) -> None:
    reports, runtime = isolated_roots
    executor = FakeExecutor()
    report_root = run_fake(executor=executor)

    report = checker.check_report(
        report_root,
        expected_candidate=COMMIT,
        now=NOW,
    )
    assert report["result"] == "passed"
    assert report["authority"]["uat_complete"] is False  # type: ignore[index]
    assert not (runtime / report_root.name).exists()
    enroll_calls = [call for call in executor.commands if "enroll" in call[0][10:]]
    assert len(enroll_calls) == 1
    command, input_text = enroll_calls[0]
    assert input_text == CODE + "\n"
    assert CODE not in command
    assert CODE not in (report_root / journey.REPORT_JSON).read_text()
    assert "A" * 48 not in (report_root / journey.REPORT_MARKDOWN).read_text()
    assert "failure" not in report
    assert not any(
        len(command) > 10 and command[10:11] == ("ps",)
        for command, _ in executor.commands
    )
    removed_images = {
        command[3]
        for command, _ in executor.commands
        if command[:3] == ("docker", "image", "rm")
    }
    assert removed_images == {
        "ithildin-local-v1-node-aaaaaaaa-ithildin-api",
        "ithildin-local-v1-node-aaaaaaaa-ithildin-ui",
        "ithildin/node-journey:aaaaaaaa",
    }
    assert executor.profile_volume_present is False
    cleanup_calls = [
        command[10:]
        for command, _ in executor.commands
        if command[10:13] == ("--profile", "node", "down")
    ]
    assert cleanup_calls == [
        ("--profile", "node", "down", "--remove-orphans", "--volumes")
    ]
    assert all("ithildin/node:local" not in command for command, _ in executor.commands)
    assert reports == report_root.parent


def test_enrollment_failure_retains_recovery_state_and_never_removes_volumes(
    isolated_roots: tuple[Path, Path],
) -> None:
    _, runtime = isolated_roots
    executor = FakeExecutor(enroll_returncode=2, enroll_stderr="Gateway unavailable")

    with pytest.raises(journey.JourneyError, match="enrollment_outcome_ambiguous"):
        run_fake(executor=executor)

    assert (runtime / RUN_ID).is_dir()
    report = load_run_report(journey.REPORT_BASE / RUN_ID)
    assert report["cleanup"]["recovery_required"] is True  # type: ignore[index]
    markdown = (journey.REPORT_BASE / RUN_ID / journey.REPORT_MARKDOWN).read_text()
    assert "Candidate commit at finish observed: `None`" in markdown
    assert "Candidate finish observation completed: `false`" in markdown
    down = [
        command
        for command, _ in executor.commands
        if command[10:13] == ("--profile", "node", "down")
    ]
    assert down
    assert all("--volumes" not in command for command in down)
    assert executor.profile_volume_present is True


def test_pre_docker_interrupt_removes_isolated_runtime_and_writes_safe_failure(
    isolated_roots: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, runtime = isolated_roots

    def interrupt(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise KeyboardInterrupt

    monkeypatch.setattr(journey, "_prepare_isolated_runtime", interrupt)
    with pytest.raises(journey.JourneyError, match="interrupted"):
        run_fake()
    assert not (runtime / RUN_ID).exists()
    report = load_run_report(journey.REPORT_BASE / RUN_ID)
    assert report["failure"] == {"code": "interrupted", "details_recorded": False}
    markdown = (journey.REPORT_BASE / RUN_ID / journey.REPORT_MARKDOWN).read_text()
    assert "Candidate commit at finish observed: `None`" in markdown
    assert "Candidate finish observation completed: `false`" in markdown


def test_interrupt_during_enrollment_preserves_possible_remote_contact(
    isolated_roots: tuple[Path, Path],
) -> None:
    _, runtime = isolated_roots
    executor = FakeExecutor(
        interrupt_tail=journey.ComposePlan(
            "unused", Path(), Path(), "unused"
        ).enroll_node()[10:],
        interrupt=KeyboardInterrupt(),
    )
    with pytest.raises(journey.JourneyError, match="interrupted"):
        run_fake(executor=executor)
    assert (runtime / RUN_ID).exists()
    report = load_run_report(journey.REPORT_BASE / RUN_ID)
    assert report["cleanup"]["recovery_required"] is True  # type: ignore[index]
    down = [
        command
        for command, _ in executor.commands
        if command[10:13] == ("--profile", "node", "down")
    ]
    assert down and all("--volumes" not in command for command in down)


def test_unexpected_failure_after_identity_revokes_and_cleans(
    isolated_roots: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, runtime = isolated_roots
    monkeypatch.setattr(
        journey,
        "_poll_node",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("hostile detail")),
    )
    with pytest.raises(journey.JourneyError, match="unexpected_failure"):
        run_fake()
    assert not (runtime / RUN_ID).exists()
    report = load_run_report(journey.REPORT_BASE / RUN_ID)
    assert report["failure"] == {
        "code": "unexpected_failure",
        "details_recorded": False,
    }
    assert report["cleanup"]["revocation_succeeded"] is True  # type: ignore[index]
    assert "hostile detail" not in json.dumps(report)


def test_stopped_compose_residue_is_rejected_before_mutation(
    isolated_roots: tuple[Path, Path],
) -> None:
    executor = FakeExecutor(residue="stopped-resource-id\n")
    with pytest.raises(journey.JourneyError, match="isolated_compose_project_not_empty"):
        run_fake(executor=executor)
    tails = [command[10:] for command, _ in executor.commands if len(command) > 10]
    assert not any(tail[:1] == ("up",) for tail in tails)


@pytest.mark.parametrize(
    "image",
    [
        "ithildin-local-v1-node-aaaaaaaa-ithildin-api",
        "ithildin-local-v1-node-aaaaaaaa-ithildin-ui",
        "ithildin/node-journey:aaaaaaaa",
    ],
)
def test_preexisting_exact_journey_image_tag_is_rejected_before_mutation(
    isolated_roots: tuple[Path, Path],
    image: str,
) -> None:
    executor = FakeExecutor(preexisting_images={image: API_IMAGE_ID})
    with pytest.raises(journey.JourneyError, match="journey_image_tag_not_empty"):
        run_fake(executor=executor)
    assert not any(
        command[10:11] == ("up",)
        for command, _ in executor.commands
        if len(command) > 10
    )


def test_image_inspection_failure_retains_run_resources(
    isolated_roots: tuple[Path, Path],
) -> None:
    _, runtime = isolated_roots
    executor = FakeExecutor(inspection_failure=True)
    with pytest.raises(journey.JourneyError, match="journey_image_identity_invalid"):
        run_fake(executor=executor)
    assert (runtime / RUN_ID).exists()
    report = load_run_report(journey.REPORT_BASE / RUN_ID)
    cleanup = report["cleanup"]
    assert isinstance(cleanup, dict)
    assert cleanup["images_removed"] is False
    assert cleanup["runtime_state_retained"] is True


@pytest.mark.parametrize(
    ("executor", "failure_code"),
    [
        (FakeExecutor(up_returncode=2), "compose_start_failed"),
        (FakeExecutor(node_build_returncode=2), "node_image_build_failed"),
    ],
)
def test_partial_build_failure_reconciles_and_removes_only_exact_run_images(
    isolated_roots: tuple[Path, Path],
    executor: FakeExecutor,
    failure_code: str,
) -> None:
    unrelated = "unrelated/product:test"
    unrelated_id = "sha256:" + "d" * 64
    executor.images[unrelated] = unrelated_id
    with pytest.raises(journey.JourneyError, match=failure_code):
        run_fake(executor=executor)
    assert executor.images == {unrelated: unrelated_id}
    report = load_run_report(journey.REPORT_BASE / RUN_ID)
    cleanup = report["cleanup"]
    assert isinstance(cleanup, dict)
    assert cleanup["images_removed"] is True
    assert cleanup["runtime_state_removed"] is True
    assert cleanup["runtime_state_retained"] is False
    assert cleanup["outcome"] == "completed"


def test_successful_cleanup_preserves_unrelated_image(
    isolated_roots: tuple[Path, Path],
) -> None:
    unrelated = "unrelated/product:test"
    executor = FakeExecutor(preexisting_images={unrelated: "sha256:" + "d" * 64})
    run_fake(executor=executor)
    assert executor.images == {unrelated: "sha256:" + "d" * 64}


def test_ambiguous_enrollment_retains_all_run_images(
    isolated_roots: tuple[Path, Path],
) -> None:
    executor = FakeExecutor(enroll_returncode=2)
    with pytest.raises(journey.JourneyError, match="enrollment_outcome_ambiguous"):
        run_fake(executor=executor)
    assert set(executor.images) == {
        "ithildin-local-v1-node-aaaaaaaa-ithildin-api",
        "ithildin-local-v1-node-aaaaaaaa-ithildin-ui",
        "ithildin/node-journey:aaaaaaaa",
    }
    assert not any(
        command[:3] == ("docker", "image", "rm")
        for command, _ in executor.commands
    )


@pytest.mark.parametrize(
    ("variable", "value", "code"),
    [
        ("DOCKER_HOST", "tcp://remote.example:2376", "ambient_docker_host_rejected"),
        ("DOCKER_HOST", "ssh://operator@remote", "ambient_docker_host_rejected"),
        ("DOCKER_CONTEXT", "production", "ambient_docker_context_rejected"),
    ],
)
def test_ambient_docker_authority_is_rejected_before_run_directory_creation(
    isolated_roots: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    variable: str,
    value: str,
    code: str,
) -> None:
    reports, runtime = isolated_roots
    monkeypatch.setenv(variable, value)
    with pytest.raises(journey.JourneyError, match=code):
        run_fake()
    assert not reports.exists()
    assert not runtime.exists()


def test_local_docker_socket_proof_accepts_one_and_rejects_missing_or_ambiguous(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = Path("/synthetic/first.sock")
    second = Path("/synthetic/second.sock")

    def fake_stat(path: Path) -> os.stat_result:
        if path == first:
            inode = 11
        elif path == second:
            inode = 12
        else:
            raise FileNotFoundError
        return os.stat_result((stat.S_IFSOCK | 0o600, inode, 7, 1, 0, 0, 0, 0, 0, 0))

    monkeypatch.setattr(Path, "stat", fake_stat)
    assert journey._prove_local_docker_socket((first,)) == f"unix://{first}"
    with pytest.raises(journey.JourneyError, match="unavailable"):
        journey._prove_local_docker_socket((Path("/synthetic/missing.sock"),))
    with pytest.raises(journey.JourneyError, match="ambiguous"):
        journey._prove_local_docker_socket((first, second))


def test_isolated_docker_environment_has_no_home_or_inherited_credentials(
    isolated_roots: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ambient_home = journey.ROOT / "ambient-home"
    (ambient_home / ".docker/contexts").mkdir(parents=True)
    (ambient_home / ".docker/config.json").write_text(
        '{"auths":{"registry.example":{"auth":"do-not-copy"}}}'
    )
    (ambient_home / ".docker/contexts/meta").write_text("do-not-copy")
    monkeypatch.setenv("HOME", str(ambient_home))
    monkeypatch.setenv("DOCKER_AUTH_CONFIG", '{"auths":{"registry.example":{}}}')
    report_anchor = journey.AnchoredRunDirectory.create(journey.REPORT_BASE, RUN_ID)
    runtime_anchor = journey.AnchoredRunDirectory.create(journey.RUNTIME_BASE, RUN_ID)
    try:
        runtime_anchor.mkdir("docker-config")
        state = _minimal_state(report_anchor, runtime_anchor)
        journey._write_isolated_docker_config(state)
        environment = journey._isolated_docker_environment(
            state,
            "unix:///var/run/docker.sock",
        )
        assert set(environment) <= {"PATH", "TMPDIR", "DOCKER_HOST", "DOCKER_CONFIG"}
        assert "HOME" not in environment
        assert "DOCKER_AUTH_CONFIG" not in environment
        config = Path(environment["DOCKER_CONFIG"])
        assert stat.S_IMODE(config.stat().st_mode) == 0o700
        assert {path.name for path in config.iterdir()} == {"config.json"}
        config_document = json.loads((config / "config.json").read_text())
        assert config_document == {
            "cliPluginsExtraDirs": [
                str(journey.ROOT / "synthetic-compose-plugin-dir")
            ]
        }
        assert stat.S_IMODE((config / "config.json").stat().st_mode) == 0o600
        assert "auths" not in config_document
        assert "credsStore" not in config_document
        assert "credHelpers" not in config_document
        assert not (config / "contexts").exists()
        assert "do-not-copy" not in str(list(config.rglob("*")))
        (config / "config.json").write_text(
            '{"auths":{"registry.example":{"auth":"hostile"}}}'
        )
        (config / "config.json").chmod(0o600)
        with pytest.raises(journey.JourneyError, match="docker_config_not_isolated"):
            journey._isolated_docker_environment(
                state,
                "unix:///var/run/docker.sock",
            )
    finally:
        runtime_anchor.remove_tree()
        report_anchor.remove_tree()


def test_compose_plugin_extra_dirs_are_closed_local_and_not_user_widened(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing"
    assert (
        journey._verified_compose_plugin_extra_dirs(
            (missing,),
            allowlist=frozenset({missing}),
        )
        == ()
    )

    valid = tmp_path / "valid"
    valid.mkdir(mode=0o700)
    valid_plugin = valid / "docker-compose"
    valid_plugin.write_text("#!/bin/sh\nexit 0\n")
    valid_plugin.chmod(0o700)
    assert journey._verified_compose_plugin_extra_dirs(
        (valid,),
        allowlist=frozenset({valid}),
    ) == (valid,)

    with pytest.raises(
        journey.JourneyError,
        match="compose_plugin_directory_not_allowlisted",
    ):
        journey._verified_compose_plugin_extra_dirs(
            (valid,),
            allowlist=frozenset(),
        )

    non_executable = tmp_path / "non-executable"
    non_executable.mkdir(mode=0o700)
    (non_executable / "docker-compose").write_text("not executable")
    with pytest.raises(journey.JourneyError, match="compose_plugin_directory_invalid"):
        journey._verified_compose_plugin_extra_dirs(
            (non_executable,),
            allowlist=frozenset({non_executable}),
        )

    widened = tmp_path / "widened"
    widened.mkdir(mode=0o777)
    widened.chmod(0o777)
    widened_plugin = widened / "docker-compose"
    widened_plugin.write_text("#!/bin/sh\nexit 0\n")
    widened_plugin.chmod(0o700)
    with pytest.raises(journey.JourneyError, match="compose_plugin_directory_invalid"):
        journey._verified_compose_plugin_extra_dirs(
            (widened,),
            allowlist=frozenset({widened}),
        )

    malicious_link = tmp_path / "linked-dir"
    malicious_link.symlink_to(valid, target_is_directory=True)
    with pytest.raises(journey.JourneyError, match="compose_plugin_directory_invalid"):
        journey._verified_compose_plugin_extra_dirs(
            (malicious_link,),
            allowlist=frozenset({malicious_link}),
        )


def test_compose_version_failure_has_stable_preflight_error(
    isolated_roots: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ComposeVersionFailExecutor(FakeExecutor):
        def run(
            self,
            command: tuple[str, ...],
            *,
            input_text: str | None = None,
            timeout: float = 180.0,
        ) -> journey.CommandResult:
            if command == ("docker", "compose", "version"):
                self.commands.append((command, input_text))
                return journey.CommandResult(1, "", "plugin unavailable")
            return super().run(command, input_text=input_text, timeout=timeout)

    executor = ComposeVersionFailExecutor()
    monkeypatch.setattr(journey, "COMPOSE_PLUGIN_EXTRA_DIR_CANDIDATES", ())
    with pytest.raises(journey.JourneyError, match="compose_plugin_execution_failed"):
        journey.run_live_journey(
            executor=executor,
            api_factory=FakeApi,  # type: ignore[arg-type]
            ui_factory=FakeUi,  # type: ignore[arg-type]
            daemon_probe=lambda: "unix:///var/run/docker.sock",
            now=NOW,
        )
    commands = [command for command, _ in executor.commands]
    assert ("docker", "compose", "version") in commands
    assert not any(len(command) > 10 for command in commands)


def test_port_probe_rejects_occupied_port(monkeypatch: pytest.MonkeyPatch) -> None:
    class OccupiedSocket:
        def bind(self, address: tuple[str, int]) -> None:
            raise OSError(f"occupied {address[1]}")

        def close(self) -> None:
            pass

    monkeypatch.setattr(journey.socket, "socket", lambda *args: OccupiedSocket())
    with pytest.raises(journey.JourneyError, match="local_port_8000_unavailable"):
        journey._require_ports_available((8000, 5173))


def test_second_run_directory_creation_failure_removes_first(
    isolated_roots: tuple[Path, Path],
) -> None:
    reports, runtime = isolated_roots
    runtime.mkdir()
    (runtime / RUN_ID).mkdir()
    with pytest.raises(journey.JourneyError, match="run_directory_exists"):
        run_fake()
    assert not (reports / RUN_ID).exists()


def test_anchor_detects_path_replacement_and_refuses_cleanup(
    isolated_roots: tuple[Path, Path],
) -> None:
    report_anchor = journey.AnchoredRunDirectory.create(journey.REPORT_BASE, RUN_ID)
    moved = report_anchor.path.with_name(RUN_ID + "-moved")
    report_anchor.path.rename(moved)
    report_anchor.path.mkdir()
    try:
        with pytest.raises(journey.JourneyError, match="identity_changed"):
            report_anchor.validate()
        assert report_anchor.remove_tree() is False
        assert report_anchor.path.is_dir()
    finally:
        report_anchor.close()


def test_anchored_executor_revalidates_after_command(
    isolated_roots: tuple[Path, Path],
) -> None:
    report_anchor = journey.AnchoredRunDirectory.create(journey.REPORT_BASE, RUN_ID)

    class SwapExecutor:
        def run(
            self,
            command: tuple[str, ...],
            *,
            input_text: str | None = None,
            timeout: float = 180.0,
        ) -> journey.CommandResult:
            del command, input_text, timeout
            report_anchor.path.rename(report_anchor.path.with_name(RUN_ID + "-moved"))
            report_anchor.path.mkdir()
            return journey.CommandResult(0, "", "")

    try:
        executor = journey.AnchoredExecutor(SwapExecutor(), (report_anchor,))
        with pytest.raises(journey.JourneyError, match="identity_changed"):
            executor.run(("docker", "version", "--format", "{{json .Server.Version}}"))
    finally:
        report_anchor.close()


def test_hostile_subprocess_and_http_material_is_never_exposed(
    isolated_roots: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executor = FakeExecutor(enroll_stdout=f'{{"message":"{CODE}"}}')
    with pytest.raises(journey.JourneyError, match="secret_detected_in_output"):
        run_fake(executor=executor)
    assert CODE not in (journey.REPORT_BASE / RUN_ID / journey.REPORT_JSON).read_text()

    secret_body = f'{{"enrollment_code":"{CODE}"}}'.encode()

    def reject(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise urllib.error.HTTPError(
            journey.HOST_API_URL + "/workspaces",
            503,
            "synthetic failure",
            {},
            io.BytesIO(secret_body),
        )

    monkeypatch.setattr(journey.urllib.request, "urlopen", reject)
    api = journey.LocalApi("admin-token-not-for-output")
    with pytest.raises(journey.JourneyError) as captured:
        api.get("/workspaces")
    assert captured.value.code == "gateway_http_503"
    assert CODE not in str(captured.value)


@pytest.mark.parametrize("field", ["private_key", "token", "signature"])
def test_local_api_recursively_rejects_secret_shaped_response_fields(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    class Response:
        status = 200
        headers = Message()

        def __enter__(self) -> Response:
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            traceback: TracebackType | None,
        ) -> None:
            del exc_type, exc, traceback

        def read(self, size: int) -> bytes:
            del size
            return json.dumps({"status": "ok", "nested": {field: "hostile"}}).encode()

    monkeypatch.setattr(journey.urllib.request, "urlopen", lambda *a, **k: Response())
    with pytest.raises(journey.JourneyError, match="gateway_response_contains_secret_fields"):
        journey.LocalApi("safe-but-private").get("/healthz", admin=False)


def test_system_status_uses_closed_projection_before_generic_secret_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    production_status: JsonObject = {
        "status": "ok",
        "tool_count": 24,
        "runtime_candidate": {
            "posture": "unreviewed_local",
            "promotion_allowed": False,
            "signature": "ignored-signature-value",
            "signing_key_id": "ignored-key-id",
        },
        "storage": {
            "runtime_backend": "sqlite",
            "postgres": {
                "configured": False,
                "dsn_source": "/run/ignored/postgres-dsn",
            },
            "database_path": "/app/var/db/ithildin.sqlite3",
        },
        "security": {
            "admin_token": {
                "configured": True,
                "source": "environment",
                "value_recorded": False,
            },
            "dev_admin_token": {
                "allowed": False,
                "signature": "ignored-security-signature",
            },
        },
        "paths": {
            "manifest_lock": "/app/tool-manifests.lock.json",
            "configuration_public_key": "/app/var/keys/public.pem",
        },
        "signatures": {
            "manifest_key_id": "ignored-manifest-key",
            "configuration_key_id": "ignored-configuration-key",
        },
    }

    class Response:
        status = 200
        headers = Message()

        def __enter__(self) -> Response:
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            traceback: TracebackType | None,
        ) -> None:
            del exc_type, exc, traceback

        def read(self, size: int) -> bytes:
            del size
            return json.dumps(production_status).encode()

    monkeypatch.setattr(journey.urllib.request, "urlopen", lambda *a, **k: Response())
    projected = journey.LocalApi("safe-private-admin").get("/system/status")
    assert projected == {
        "status": "ok",
        "tool_count": 24,
        "runtime_candidate": {"posture": "unreviewed_local"},
        "storage": {
            "runtime_backend": "sqlite",
            "postgres": {"configured": False},
        },
    }
    serialized = json.dumps(projected)
    for ignored in (
        "admin_token",
        "dev_admin_token",
        "ignored-signature-value",
        "ignored-key-id",
        "/app/var/db/ithildin.sqlite3",
    ):
        assert ignored not in serialized


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("status",), "bearer_secret_do_not_reflect"),
        (("tool_count",), "password_do_not_reflect"),
        (("runtime_candidate",), "private_key_do_not_reflect"),
        (("runtime_candidate", "posture"), "admin_token_do_not_reflect"),
        (("storage",), "credential_do_not_reflect"),
        (("storage", "runtime_backend"), "secret_backend_do_not_reflect"),
        (("storage", "postgres"), "enrollment_code_do_not_reflect"),
        (("storage", "postgres", "configured"), "token_do_not_reflect"),
        (("status",), 7),
        (("tool_count",), True),
        (("runtime_candidate",), []),
        (("runtime_candidate", "posture"), {}),
        (("storage",), []),
        (("storage", "runtime_backend"), []),
        (("storage", "postgres"), []),
        (("storage", "postgres", "configured"), 1),
    ],
)
def test_system_status_projection_rejects_hostile_required_fields_without_reflection(
    path: tuple[str, ...],
    value: object,
) -> None:
    document: JsonObject = {
        "status": "ok",
        "tool_count": 24,
        "runtime_candidate": {"posture": "unreviewed_local"},
        "storage": {
            "runtime_backend": "sqlite",
            "postgres": {"configured": False},
        },
    }
    target: object = document
    for part in path[:-1]:
        assert isinstance(target, dict)
        target = target[part]
    assert isinstance(target, dict)
    target[path[-1]] = value
    with pytest.raises(journey.JourneyError) as captured:
        journey._project_system_status(document)
    assert captured.value.code == "gateway_system_status_invalid"
    assert "do_not_reflect" not in str(captured.value).lower()


def test_system_status_projection_rejects_opaque_admin_secret_in_required_field() -> None:
    opaque_secret = "opaquesensitivevalue"
    document: JsonObject = {
        "status": opaque_secret,
        "tool_count": 24,
        "runtime_candidate": {"posture": "unreviewed_local"},
        "storage": {
            "runtime_backend": "sqlite",
            "postgres": {"configured": False},
        },
    }
    with pytest.raises(journey.JourneyError) as captured:
        journey._project_system_status(
            document,
            secrets_to_reject=(opaque_secret,),
        )
    assert captured.value.code == "gateway_system_status_invalid"
    assert opaque_secret not in str(captured.value)


def test_system_status_oversize_and_http_error_do_not_reflect_secret_material(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "SYSTEM_STATUS_SECRET_DO_NOT_REFLECT"

    class OversizedResponse:
        status = 200
        headers = Message()

        def __enter__(self) -> OversizedResponse:
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            traceback: TracebackType | None,
        ) -> None:
            del exc_type, exc, traceback

        def read(self, size: int) -> bytes:
            del size
            return (secret.encode() + b"x" * 262_145)

    monkeypatch.setattr(
        journey.urllib.request,
        "urlopen",
        lambda *a, **k: OversizedResponse(),
    )
    with pytest.raises(journey.JourneyError) as oversized:
        journey.LocalApi("safe-private-admin").get("/system/status")
    assert oversized.value.code == "gateway_response_too_large"
    assert secret not in str(oversized.value)

    def reject(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise urllib.error.HTTPError(
            journey.HOST_API_URL + "/system/status",
            503,
            secret,
            Message(),
            io.BytesIO(secret.encode()),
        )

    monkeypatch.setattr(journey.urllib.request, "urlopen", reject)
    with pytest.raises(journey.JourneyError) as rejected:
        journey.LocalApi("safe-private-admin").get("/system/status")
    assert rejected.value.code == "gateway_http_503"
    assert secret not in str(rejected.value)


def test_system_status_projection_failure_is_absent_from_reports_and_cli(
    isolated_roots: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    secret = "admin_token_do_not_reflect"

    class ProjectionFailureApi(FakeApi):
        def get(self, path: str, *, admin: bool = True) -> JsonObject:
            if path == "/system/status":
                return journey._project_system_status(
                    {
                        "status": "ok",
                        "tool_count": 24,
                        "runtime_candidate": {"posture": secret},
                        "storage": {
                            "runtime_backend": "sqlite",
                            "postgres": {"configured": False},
                        },
                    }
                )
            return super().get(path, admin=admin)

    with pytest.raises(journey.JourneyError) as failed:
        run_fake(api_factory=ProjectionFailureApi)
    assert failed.value.code == "compose_stack_health_timeout"
    report_root = journey.REPORT_BASE / RUN_ID
    emitted = (
        (report_root / journey.REPORT_JSON).read_text()
        + (report_root / journey.REPORT_MARKDOWN).read_text()
    )
    assert secret not in emitted
    assert "gateway_system_status_invalid" not in emitted

    def fail_cli(**kwargs: object) -> journey.JourneyRunResult:
        del kwargs
        raise journey.JourneyError("gateway_system_status_invalid")

    monkeypatch.setattr(journey, "run_live_journey", fail_cli)
    monkeypatch.setattr("sys.argv", ["local_v1_node_journey.py"])
    assert journey.main() == 1
    output = capsys.readouterr()
    assert secret not in output.out + output.err
    assert output.err.strip() == (
        "Local-v1 Node journey failed closed: gateway_system_status_invalid"
    )


@pytest.mark.parametrize("assigned", [False, True])
def test_node_inventory_uses_closed_projection_before_generic_secret_guard(
    monkeypatch: pytest.MonkeyPatch,
    assigned: bool,
) -> None:
    source = production_node_inventory(assigned=assigned)

    class Response:
        status = 200
        headers = Message()

        def __enter__(self) -> Response:
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            traceback: TracebackType | None,
        ) -> None:
            del exc_type, exc, traceback

        def read(self, size: int) -> bytes:
            del size
            return json.dumps(source).encode()

    monkeypatch.setattr(journey.urllib.request, "urlopen", lambda *a, **k: Response())
    projected = journey.LocalApi("safe-private-admin").get(f"/nodes/{NODE_ID}")
    assert set(projected) == {
        "node_id",
        "principal_id",
        "workspace_id",
        "identity_source",
        "evidence_status",
        "desired_configuration_generation",
        "desired_configuration_digest",
        "acknowledged_configuration_generation",
        "acknowledged_configuration_digest",
        "last_configuration_digest",
        "configuration_acknowledgment_status",
        "configuration_state",
        "observed_state",
        "connectivity_source",
        "runner_health_known",
        "model_health_known",
    }
    assert projected["node_id"] == NODE_ID
    assert projected["desired_configuration_generation"] == (1 if assigned else None)
    serialized = json.dumps(projected)
    for ignored in (
        "authorization_profile",
        "private_key_received",
        "ignored-public-key-material",
        "ignored-identity-key-id",
        "ignored-configuration-key-id",
        "governed_access",
    ):
        assert ignored not in serialized


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("node_id",), "node_" + "f" * 32),
        (("principal_id",), "agent:token.secret"),
        (("workspace_id",), "admin_token_workspace"),
        (("identity_source",), "private_key_source"),
        (("evidence_status",), "credential_pending"),
        (("desired_configuration_generation",), True),
        (("desired_configuration_generation",), 0),
        (("desired_configuration_digest",), "secret_digest"),
        (("acknowledged_configuration_generation",), "1"),
        (("acknowledged_configuration_digest",), "token_digest"),
        (("last_configuration_digest",), "not-a-digest"),
        (("configuration_acknowledgment_status",), "authorization_pending"),
        (("configuration_state",), "secret_state"),
        (("observed_state",), "password_state"),
        (("connectivity_source",), "bearer_source"),
        (("runner_health_known",), 0),
        (("model_health_known",), "false"),
    ],
)
def test_node_inventory_projection_rejects_hostile_required_fields(
    path: tuple[str, ...],
    value: object,
) -> None:
    document = production_node_inventory(assigned=True)
    target: object = document
    for part in path[:-1]:
        assert isinstance(target, dict)
        target = target[part]
    assert isinstance(target, dict)
    target[path[-1]] = value
    with pytest.raises(journey.JourneyError) as captured:
        journey._project_node_inventory(
            document,
            expected_node_id=NODE_ID,
        )
    assert captured.value.code == "gateway_node_inventory_invalid"
    assert str(value) not in str(captured.value)


def test_node_inventory_projection_rejects_missing_and_opaque_admin_secret() -> None:
    missing = production_node_inventory(assigned=False)
    del missing["desired_configuration_digest"]
    with pytest.raises(journey.JourneyError, match="gateway_node_inventory_invalid"):
        journey._project_node_inventory(missing, expected_node_id=NODE_ID)

    opaque_secret = "opaqueadminvalue"
    secret = production_node_inventory(assigned=False)
    secret["workspace_id"] = opaque_secret
    with pytest.raises(journey.JourneyError) as captured:
        journey._project_node_inventory(
            secret,
            expected_node_id=NODE_ID,
            secrets_to_reject=(opaque_secret,),
        )
    assert captured.value.code == "gateway_node_inventory_invalid"
    assert opaque_secret not in str(captured.value)

    digest_secret = DIGEST
    secret_digest = production_node_inventory(assigned=True)
    with pytest.raises(journey.JourneyError) as digest_captured:
        journey._project_node_inventory(
            secret_digest,
            expected_node_id=NODE_ID,
            secrets_to_reject=(digest_secret,),
        )
    assert digest_captured.value.code == "gateway_node_inventory_invalid"
    assert digest_secret not in str(digest_captured.value)


def test_projected_node_inventory_preserves_identity_binding_failure_code() -> None:
    source = production_node_inventory(assigned=False)
    source["principal_id"] = "agent:node.node_" + "2" * 32
    projected = journey._project_node_inventory(
        source,
        expected_node_id=NODE_ID,
    )
    with pytest.raises(journey.JourneyError) as captured:
        journey._verify_gateway_identity(
            projected,
            NODE_ID,
            PRINCIPAL_ID,
            "demo",
        )
    assert captured.value.code == "gateway_identity_binding_invalid"


def test_node_inventory_projection_failure_is_nonreflective_and_revoked(
    isolated_roots: tuple[Path, Path],
) -> None:
    secret = "authorization_profile_do_not_reflect"

    class ProjectionFailureApi(FakeApi):
        def get(self, path: str, *, admin: bool = True) -> JsonObject:
            if path == f"/nodes/{NODE_ID}":
                source = production_node_inventory(assigned=False)
                source["workspace_id"] = secret
                return journey._project_node_inventory(
                    source,
                    expected_node_id=NODE_ID,
                )
            return super().get(path, admin=admin)

    with pytest.raises(journey.JourneyError) as failed:
        run_fake(api_factory=ProjectionFailureApi)
    assert failed.value.code == "gateway_node_inventory_invalid"
    report_root = journey.REPORT_BASE / RUN_ID
    report = load_run_report(report_root)
    assert report["failure"] == {
        "code": "gateway_node_inventory_invalid",
        "details_recorded": False,
    }
    assert report["cleanup"]["revocation_succeeded"] is True  # type: ignore[index]
    assert report["cleanup"]["recovery_required"] is False  # type: ignore[index]
    emitted = (
        (report_root / journey.REPORT_JSON).read_text()
        + (report_root / journey.REPORT_MARKDOWN).read_text()
    )
    assert secret not in emitted


def test_projected_production_node_inventory_preserves_success_evidence_schema(
    isolated_roots: tuple[Path, Path],
) -> None:
    class ProjectingApi(FakeApi):
        def get(self, path: str, *, admin: bool = True) -> JsonObject:
            if path == f"/nodes/{NODE_ID}":
                return journey._project_node_inventory(
                    production_node_inventory(assigned=True),
                    expected_node_id=NODE_ID,
                )
            return super().get(path, admin=admin)

    report_root = run_fake(api_factory=ProjectingApi)
    report = checker.check_report(report_root, expected_candidate=COMMIT, now=NOW)
    assert report["result"] == "passed"
    assert "failure" not in report
    assert set(report) == {
        "schema_version",
        "run_id",
        "result",
        "provenance",
        "last_stage",
        "observations",
        "cleanup",
        "redaction_scan",
        "authority",
        "nonclaims",
    }


def test_local_ui_http_rejection_has_closed_probe_category(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise urllib.error.HTTPError(
            "http://127.0.0.1:5173/",
            503,
            "DO_NOT_REFLECT",
            Message(),
            None,
        )

    monkeypatch.setattr(journey.urllib.request, "urlopen", reject)
    with pytest.raises(journey.JourneyError) as captured:
        journey.LocalUi().health()
    assert captured.value.code == "ui_http_rejected"
    assert (
        journey._classify_probe_error(captured.value, ui=True)
        == "probe_rejected"
    )
    assert "DO_NOT_REFLECT" not in str(captured.value)


@pytest.mark.parametrize(
    ("api_type", "failure_code"),
    [
        (
            type("FalseOnceApi", (FakeApi,), {"secret_returned_once": False}),
            "enrollment_code_response_invalid",
        ),
        (
            type("PendingInventoryApi", (FakeApi,), {"inventory_evidence_status": "pending"}),
            "gateway_identity_binding_invalid",
        ),
        (
            type("PendingAssignmentApi", (FakeApi,), {"assignment_evidence_status": "pending"}),
            "configuration_assignment_evidence_incomplete",
        ),
    ],
)
def test_incomplete_gateway_truth_is_rejected(
    isolated_roots: tuple[Path, Path],
    api_type: type[FakeApi],
    failure_code: str,
) -> None:
    with pytest.raises(journey.JourneyError, match=failure_code):
        run_fake(api_factory=api_type)


def test_partial_ui_health_is_not_accepted(
    isolated_roots: tuple[Path, Path],
) -> None:
    class PartialUi(FakeUi):
        def health(self) -> JsonObject:
            return {
                "ui_http_status": 200,
                "ui_content_type": "text/plain",
                "ui_shell_observed": True,
            }

    with pytest.raises(journey.JourneyError, match="compose_stack_health_timeout"):
        run_fake(ui_factory=PartialUi)

    report = load_run_report(journey.REPORT_BASE / RUN_ID)
    assert report["failure"] == {
        "code": "compose_stack_health_timeout",
        "details_recorded": False,
        "diagnostic": {
            "collection_status": "complete",
            "collection_reason_code": "compose_stack_diagnostic_collected",
            "reason_code": "stack_ui_probe_not_ready",
            "probes": {
                "api_healthz": "probe_ready",
                "authenticated_system_status": "probe_ready",
                "ui": "probe_invalid",
            },
            "services": {
                "ithildin-api": "service_running_healthy",
                "ithildin-ui": "service_running_without_healthcheck",
            },
        },
    }
    markdown = (journey.REPORT_BASE / RUN_ID / journey.REPORT_MARKDOWN).read_text()
    assert "stack_ui_probe_not_ready" in markdown
    assert "compose_stack_diagnostic_collected" in markdown
    assert "service_running_healthy" in markdown
    assert "service_running_without_healthcheck" in markdown
    assert set(report["authority"].values()) == {False}  # type: ignore[union-attr]
    cleanup = report["cleanup"]
    assert isinstance(cleanup, dict)
    assert cleanup["outcome"] == "completed"
    assert cleanup["recovery_required"] is False
    assert cleanup["runtime_state_removed"] is True


def test_stack_probes_run_independently_in_one_cycle() -> None:
    calls: list[str] = []

    class IndependentApi:
        def get(self, path: str, *, admin: bool = True) -> JsonObject:
            calls.append(f"api:{path}:{admin}")
            if path == "/healthz":
                raise journey.JourneyError("gateway_unavailable")
            return FakeApi("synthetic").get(path, admin=admin)

    class IndependentUi:
        def health(self) -> JsonObject:
            calls.append("ui")
            return FakeUi().health()

    cycle = journey._probe_stack_cycle(  # type: ignore[arg-type]
        IndependentApi(),
        IndependentUi(),  # type: ignore[arg-type]
    )
    assert calls == [
        "api:/healthz:False",
        "api:/system/status:True",
        "ui",
    ]
    assert cycle.evidence() == {
        "api_healthz": "probe_unavailable",
        "authenticated_system_status": "probe_ready",
        "ui": "probe_ready",
    }
    assert cycle.ready is False
    assert (
        journey._classify_probe_error(
            journey.JourneyError("gateway_http_401"),
            ui=False,
        )
        == "probe_rejected"
    )
    assert (
        journey._classify_probe_error(
            journey.JourneyError("gateway_response_invalid"),
            ui=False,
        )
        == "probe_invalid"
    )


def test_probe_successes_in_different_cycles_do_not_establish_readiness() -> None:
    class FlappingApi(FakeApi):
        health_calls = 0

        def get(self, path: str, *, admin: bool = True) -> JsonObject:
            if path == "/healthz":
                self.health_calls += 1
                if self.health_calls == 2:
                    raise journey.JourneyError("gateway_unavailable")
            return super().get(path, admin=admin)

    class FlappingUi(FakeUi):
        calls = 0

        def health(self) -> JsonObject:
            self.calls += 1
            if self.calls == 1:
                raise journey.JourneyError("ui_unavailable")
            return super().health()

    api = FlappingApi("synthetic")
    ui = FlappingUi()
    first = journey._probe_stack_cycle(api, ui)
    second = journey._probe_stack_cycle(api, ui)

    assert first.evidence() == {
        "api_healthz": "probe_ready",
        "authenticated_system_status": "probe_ready",
        "ui": "probe_unavailable",
    }
    assert second.evidence() == {
        "api_healthz": "probe_unavailable",
        "authenticated_system_status": "probe_ready",
        "ui": "probe_ready",
    }
    assert first.ready is False
    assert second.ready is False


@pytest.mark.parametrize(
    ("status_document", "failure_code"),
    [
        (
            {
                "status": "ok",
                "tool_count": 25,
                "runtime_candidate": {"posture": "unreviewed_local"},
                "storage": {
                    "runtime_backend": "sqlite",
                    "postgres": {"configured": False},
                },
            },
            "governed_tool_count_changed",
        ),
        (
            {
                "status": "ok",
                "tool_count": 24,
                "runtime_candidate": {"posture": "released"},
                "storage": {
                    "runtime_backend": "sqlite",
                    "postgres": {"configured": False},
                },
            },
            "runtime_candidate_authority_unexpected",
        ),
        (
            {
                "status": "ok",
                "tool_count": 24,
                "runtime_candidate": {"posture": "unreviewed_local"},
                "storage": {
                    "runtime_backend": "postgres",
                    "postgres": {"configured": False},
                },
            },
            "storage_backend_not_sqlite",
        ),
        (
            {
                "status": "ok",
                "tool_count": 24,
                "runtime_candidate": {"posture": "unreviewed_local"},
                "storage": {
                    "runtime_backend": "sqlite",
                    "postgres": {"configured": True},
                },
            },
            "postgres_dsn_unexpected",
        ),
    ],
)
def test_ready_system_response_preserves_immediate_trust_failures(
    isolated_roots: tuple[Path, Path],
    status_document: JsonObject,
    failure_code: str,
) -> None:
    class UnavailableUi(FakeUi):
        calls = 0

        def health(self) -> JsonObject:
            type(self).calls += 1
            raise journey.JourneyError("ui_unavailable")

    api_type = type(
        "TrustMismatchApi",
        (FakeApi,),
        {"system_status_document": status_document},
    )
    executor = FakeExecutor()
    with pytest.raises(journey.JourneyError, match=failure_code):
        run_fake(
            executor=executor,
            api_factory=api_type,
            ui_factory=UnavailableUi,
        )
    report = load_run_report(journey.REPORT_BASE / RUN_ID)
    assert report["failure"] == {
        "code": failure_code,
        "details_recorded": False,
    }
    assert report["cleanup"]["outcome"] == "completed"  # type: ignore[index]
    assert report["cleanup"]["recovery_required"] is False  # type: ignore[index]
    assert report["cleanup"]["runtime_state_removed"] is True  # type: ignore[index]
    tails = [
        command[10:]
        for command, _ in executor.commands
        if len(command) > 10
    ]
    assert not any(tail[:1] == ("ps",) for tail in tails)
    assert not any("enroll" in tail for tail in tails)
    assert UnavailableUi.calls == 0


def test_stack_reason_inference_is_closed_and_does_not_guess_root_cause() -> None:
    services: JsonObject = {
        "ithildin-api": "service_running_healthy",
        "ithildin-ui": "service_running_without_healthcheck",
    }
    ui_failure = journey.StackProbeCycle(
        api_healthz="probe_ready",
        authenticated_system_status="probe_ready",
        ui="probe_unavailable",
        system_status=None,
        ui_health=None,
    )
    assert journey._infer_stack_reason(services, ui_failure) == (
        "stack_ui_probe_not_ready"
    )
    all_ready = journey.StackProbeCycle(
        api_healthz="probe_ready",
        authenticated_system_status="probe_ready",
        ui="probe_ready",
        system_status=None,
        ui_health=None,
    )
    assert (
        journey._infer_stack_reason(services, all_ready)
        == "stack_same_cycle_readiness_timeout"
    )
    services["ithildin-api"] = "service_exited_nonzero"
    assert (
        journey._infer_stack_reason(services, ui_failure)
        == "stack_multiple_readiness_failures"
    )


@pytest.mark.parametrize(
    ("state", "health", "exit_code", "expected"),
    [
        ("running", "healthy", 0, "service_running_healthy"),
        ("running", "starting", 0, "service_running_starting"),
        ("running", "unhealthy", 0, "service_running_unhealthy"),
        ("running", "", 0, "service_running_without_healthcheck"),
        ("exited", "", 0, "service_exited_zero"),
        ("exited", "", 23, "service_exited_nonzero"),
        ("created", "", 0, "service_created"),
        ("restarting", "", 0, "service_restarting_zero"),
        ("restarting", "", 137, "service_restarting_nonzero"),
        ("paused", "", 0, "service_paused"),
        ("dead", "", 0, "service_dead_zero"),
        ("dead", "", 137, "service_dead_nonzero"),
        ("removing", "", 0, "service_removing"),
    ],
)
def test_stack_diagnostic_classification_is_closed(
    state: str,
    health: str,
    exit_code: int,
    expected: str,
) -> None:
    assert journey._classify_stack_service(state, health, exit_code) == expected


@pytest.mark.parametrize(
    "hostile_output",
    [
        "malformed",
        "ithildin-api\trunning\thealthy\t0\nithildin-api\texited\t\t1\n",
        "unrelated-service\trunning\thealthy\t0\n",
        "ithildin-api\trunning\thealthy\t0\nithildin-ui\trunning\t\t0\nextra\tline\t\t0\n",
        "ithildin-api\trunning\thealthy\t0\x1b[31m\n",
        "ithildin-api\trunning\thealthy\t0\r\n",
        "authorization=DO_NOT_REFLECT",
        "ithildin-api\tunknown\t\t0\n",
        "ithildin-api\texited\thealthy\t1\n",
        "ithildin-api\trestarting\thealthy\t1\n",
        "ithildin-api\trunning\thealthy\t999\n",
        "x" * (journey.MAX_STACK_DIAGNOSTIC_BYTES + 1),
        "ithildin-api\trünning\thealthy\t0\n",
        "A" * 48,
        "ITHILDIN_ADMIN_TOKEN=DO_NOT_REFLECT",
        "-----BEGIN PRIVATE KEY-----",
        "Bearer DO_NOT_REFLECT",
        "/private/tmp/ithildin-host-material",
        "command=/bin/sh -c whoami",
        "mounts=/private/tmp:/data",
        "address=127.0.0.1:8000",
    ],
)
def test_hostile_stack_diagnostic_output_is_rejected_without_reflection(
    isolated_roots: tuple[Path, Path],
    hostile_output: str,
) -> None:
    class PartialUi(FakeUi):
        def health(self) -> JsonObject:
            raise journey.JourneyError("ui_unavailable")

    executor = FakeExecutor(diagnostic_stdout=hostile_output)
    with pytest.raises(journey.JourneyError, match="compose_stack_health_timeout"):
        run_fake(executor=executor, ui_factory=PartialUi)

    report_root = journey.REPORT_BASE / RUN_ID
    report = load_run_report(report_root)
    failure = report["failure"]
    assert isinstance(failure, dict)
    assert failure["diagnostic"] == {
        "collection_status": "output_rejected",
        "collection_reason_code": "compose_stack_diagnostic_output_rejected",
        "reason_code": "stack_diagnostic_output_rejected",
        "probes": {
            "api_healthz": "probe_ready",
            "authenticated_system_status": "probe_ready",
            "ui": "probe_unavailable",
        },
        "services": {
            "ithildin-api": "service_unobserved",
            "ithildin-ui": "service_unobserved",
        },
    }
    emitted = (
        (report_root / journey.REPORT_JSON).read_text()
        + (report_root / journey.REPORT_MARKDOWN).read_text()
    )
    assert hostile_output not in emitted
    diagnostic_commands = [
        command
        for command, _ in executor.commands
        if len(command) > 10 and command[10:11] == ("ps",)
    ]
    assert len(diagnostic_commands) == 1


def test_stack_diagnostic_command_failure_is_inconclusive_without_reflection(
    isolated_roots: tuple[Path, Path],
) -> None:
    class PartialUi(FakeUi):
        def health(self) -> JsonObject:
            raise journey.JourneyError("ui_unavailable")

    executor = FakeExecutor(
        diagnostic_returncode=2,
        diagnostic_stdout="",
        diagnostic_stderr="safe synthetic failure",
    )
    with pytest.raises(journey.JourneyError, match="compose_stack_health_timeout"):
        run_fake(executor=executor, ui_factory=PartialUi)
    report = load_run_report(journey.REPORT_BASE / RUN_ID)
    failure = report["failure"]
    assert isinstance(failure, dict)
    diagnostic = failure["diagnostic"]
    assert isinstance(diagnostic, dict)
    assert diagnostic["collection_status"] == "inconclusive"
    assert (
        diagnostic["collection_reason_code"]
        == "compose_stack_diagnostic_command_failed"
    )
    assert diagnostic["reason_code"] == "stack_diagnostic_inconclusive"
    assert set(diagnostic["services"].values()) == {"service_unobserved"}  # type: ignore[union-attr]
    assert "safe synthetic failure" not in json.dumps(report)
    cleanup = report["cleanup"]
    assert isinstance(cleanup, dict)
    assert cleanup["outcome"] == "completed"
    assert cleanup["recovery_required"] is False
    assert cleanup["runtime_state_removed"] is True


def test_stack_diagnostic_validator_rejects_contradictory_closed_fields() -> None:
    diagnostic: JsonObject = {
        "collection_status": "complete",
        "collection_reason_code": "compose_stack_diagnostic_collected",
        "reason_code": "stack_ui_probe_not_ready",
        "probes": {
            "api_healthz": "probe_ready",
            "authenticated_system_status": "probe_ready",
            "ui": "probe_invalid",
        },
        "services": {
            "ithildin-api": "service_running_healthy",
            "ithildin-ui": "service_running_without_healthcheck",
        },
    }
    evidence.validate_stack_diagnostic(diagnostic)
    hostile = copy.deepcopy(diagnostic)
    hostile["collection_status"] = "inconclusive"
    with pytest.raises(evidence.EvidenceValidationError, match="contradictory"):
        evidence.validate_stack_diagnostic(hostile)

    restarting = copy.deepcopy(diagnostic)
    assert isinstance(restarting["probes"], dict)
    assert isinstance(restarting["services"], dict)
    restarting["probes"]["ui"] = "probe_ready"
    restarting["services"]["ithildin-api"] = "service_restarting_nonzero"
    restarting["reason_code"] = "stack_api_service_not_ready"
    evidence.validate_stack_diagnostic(restarting)
    restarting["services"]["ithildin-api"] = "service_restarting"
    with pytest.raises(evidence.EvidenceValidationError, match="services are invalid"):
        evidence.validate_stack_diagnostic(restarting)


def test_checker_requires_exact_candidate_run_and_fresh_time(
    isolated_roots: tuple[Path, Path],
) -> None:
    report_root = run_fake()
    with pytest.raises(checker.EvidenceCheckError, match="exactly 40"):
        checker.check_report(report_root, expected_candidate="latest", now=NOW)
    with pytest.raises(evidence.EvidenceValidationError, match="expected candidate"):
        checker.check_report(report_root, expected_candidate="4" * 40, now=NOW)
    with pytest.raises(evidence.EvidenceValidationError, match="stale"):
        checker.check_report(
            report_root,
            expected_candidate=COMMIT,
            now=NOW + timedelta(hours=25),
        )
    with pytest.raises(evidence.EvidenceValidationError, match="future"):
        checker.check_report(
            report_root,
            expected_candidate=COMMIT,
            now=NOW - timedelta(minutes=3),
        )


def test_shared_validator_rejects_run_identity_drift(
    isolated_roots: tuple[Path, Path],
) -> None:
    report = load_run_report(run_fake())
    drifted = copy.deepcopy(report)
    provenance = drifted["provenance"]
    assert isinstance(provenance, dict)
    provenance["started_at_utc"] = "2026-07-23T12:00:01Z"
    with pytest.raises(evidence.EvidenceValidationError, match="run identity timestamp"):
        evidence.validate_report(
            drifted,
            directory_run_id=RUN_ID,
            expected_candidate=COMMIT,
            now=NOW,
        )


def test_shared_validator_closes_and_run_binds_cleanup_evidence(
    isolated_roots: tuple[Path, Path],
) -> None:
    report = load_run_report(run_fake())
    hostile_reports: list[JsonObject] = []

    extra = copy.deepcopy(report)
    assert isinstance(extra["cleanup"], dict)
    extra["cleanup"]["extra"] = True
    hostile_reports.append(extra)

    missing = copy.deepcopy(report)
    assert isinstance(missing["cleanup"], dict)
    del missing["cleanup"]["resources_absent"]
    hostile_reports.append(missing)

    mismatched = copy.deepcopy(report)
    assert isinstance(mismatched["cleanup"], dict)
    mismatched["cleanup"]["unique_project"] = "ithildin-local-v1-node-deadbeef"
    hostile_reports.append(mismatched)

    false_value = copy.deepcopy(report)
    assert isinstance(false_value["cleanup"], dict)
    false_value["cleanup"]["images_removed"] = False
    hostile_reports.append(false_value)

    retained = copy.deepcopy(report)
    assert isinstance(retained["cleanup"], dict)
    retained["cleanup"]["runtime_state_retained"] = True
    hostile_reports.append(retained)

    image_mismatch = copy.deepcopy(report)
    assert isinstance(image_mismatch["cleanup"], dict)
    images = image_mismatch["cleanup"]["images"]
    assert isinstance(images, dict) and isinstance(images["api"], dict)
    images["api"]["reference"] = "unrelated/product:test"
    hostile_reports.append(image_mismatch)

    for hostile in hostile_reports:
        with pytest.raises(evidence.EvidenceValidationError):
            evidence.validate_report(
                hostile,
                directory_run_id=RUN_ID,
                expected_candidate=COMMIT,
                now=NOW,
            )


def test_gateway_state_fake_is_bound_to_production_contract_constants() -> None:
    assert (
        configuration_state(
            node_status="enrolled",
            node_evidence_status="complete",
            desired_generation=1,
            desired_digest=DIGEST,
            acknowledged_generation=1,
            acknowledged_digest=DIGEST,
            acknowledgment_status="stored_not_enforced",
        )
        == CONFIGURATION_STATE_STORED_CURRENT_NOT_ENFORCED
    )
    record = FakeApi("synthetic").get(f"/nodes/{NODE_ID}")
    assert (
        record["configuration_state"]
        == CONFIGURATION_STATE_STORED_CURRENT_NOT_ENFORCED
    )
    assert record["observed_state"] == NODE_OBSERVED_STATE_CONNECTED


def test_failed_markdown_reports_actual_source_finish_observation(
    isolated_roots: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(journey.JourneyError):
        run_fake(executor=FakeExecutor(residue="stopped\n"))
    preflight = (journey.REPORT_BASE / RUN_ID / journey.REPORT_MARKDOWN).read_text()
    assert "Candidate commit at finish observed: `None`" in preflight
    assert "Candidate tree clean at finish observed: `false`" in preflight
    assert "Candidate finish observation completed: `false`" in preflight

    # Use fresh roots for a source-change report in the same test.
    report_anchor = journey.REPORT_BASE / RUN_ID
    runtime_anchor = journey.RUNTIME_BASE / RUN_ID
    for path in (report_anchor, runtime_anchor):
        if path.exists():
            for child in path.iterdir():
                if child.is_file():
                    child.unlink()
            path.rmdir()
    calls = 0

    def changed_source(arguments: tuple[str, ...]) -> str:
        nonlocal calls
        if arguments == ("rev-parse", "HEAD"):
            calls += 1
            return COMMIT if calls == 1 else "4" * 40
        return ""

    monkeypatch.setattr(journey, "_git_observation", changed_source)
    with pytest.raises(journey.JourneyError, match="source_candidate_changed_during_journey"):
        run_fake()
    changed = (journey.REPORT_BASE / RUN_ID / journey.REPORT_MARKDOWN).read_text()
    assert f"Candidate commit at finish observed: `{'4' * 40}`" in changed
    assert "Candidate tree clean at finish observed: `true`" in changed
    assert "Candidate finish observation completed: `true`" in changed


@pytest.mark.parametrize(
    ("hostile_key", "hostile_value"),
    [
        ("authorization", "DO_NOT_REFLECT_VALUE"),
        ("authorization_\u001bCONTROL", "CONTROL_VALUE_\u0007"),
    ],
)
def test_checker_cli_does_not_reflect_hostile_keys_or_values(
    isolated_roots: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    hostile_key: str,
    hostile_value: str,
) -> None:
    report_root = run_fake()
    path = report_root / journey.REPORT_JSON
    document = json.loads(path.read_text())
    document["observations"][hostile_key] = hostile_value
    path.write_text(json.dumps(document))
    path.chmod(0o600)
    monkeypatch.setattr(
        "sys.argv",
        [
            "local_v1_node_journey_check.py",
            "--report-root",
            str(report_root),
            "--expected-candidate",
            COMMIT,
        ],
    )
    assert checker.main() == 1
    stderr = capsys.readouterr().err
    assert hostile_key not in stderr
    assert hostile_value not in stderr
    assert "secret-shaped field is not allowed" in stderr


def test_main_uses_validated_run_result_candidate_without_reobserving_head(
    isolated_roots: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report_root = journey.REPORT_BASE / RUN_ID
    report_root.mkdir(parents=True)
    monkeypatch.setattr(
        journey,
        "run_live_journey",
        lambda **kwargs: journey.JourneyRunResult(report_root, COMMIT),
    )
    monkeypatch.setattr(
        journey,
        "_git_observation",
        lambda arguments: (_ for _ in ()).throw(AssertionError(arguments)),
    )
    monkeypatch.setattr("sys.argv", ["local_v1_node_journey.py"])
    assert journey.main() == 0
    output = capsys.readouterr().out
    assert f"candidate_commit={COMMIT}" in output
    assert f"LOCAL_V1_NODE_JOURNEY_CANDIDATE={COMMIT}" in output


def test_main_failure_is_safe_and_does_not_reobserve_head(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail(**kwargs: object) -> journey.JourneyRunResult:
        del kwargs
        raise journey.JourneyError("source_candidate_changed_during_journey")

    monkeypatch.setattr(journey, "run_live_journey", fail)
    monkeypatch.setattr(
        journey,
        "_git_observation",
        lambda arguments: (_ for _ in ()).throw(AssertionError(arguments)),
    )
    monkeypatch.setattr("sys.argv", ["local_v1_node_journey.py"])
    assert journey.main() == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err.strip() == (
        "Local-v1 Node journey failed closed: "
        "source_candidate_changed_during_journey"
    )


@pytest.mark.parametrize(
    "module",
    [
        "scripts.local_v1_node_journey",
        "scripts.local_v1_node_journey_check",
    ],
)
def test_real_module_entrypoints_resolve_before_execution(module: str) -> None:
    result = subprocess.run(
        (sys.executable, "-m", module, "--help"),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout
    assert "ModuleNotFoundError" not in result.stderr


def test_make_targets_use_module_entrypoints() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text()
    assert "python -m scripts.local_v1_node_journey\n" in makefile
    assert "python -m scripts.local_v1_node_journey_check \\" in makefile
    assert "python scripts/local_v1_node_journey.py" not in makefile
    assert "python scripts/local_v1_node_journey_check.py" not in makefile


def test_checker_rejects_secret_fields_permissions_and_markdown_drift(
    isolated_roots: tuple[Path, Path],
) -> None:
    report_root = run_fake()
    json_path = report_root / journey.REPORT_JSON
    markdown_path = report_root / journey.REPORT_MARKDOWN
    original_json = json_path.read_text()
    document = json.loads(original_json)
    document["observations"]["private_key"] = "not-safe"
    json_path.write_text(json.dumps(document))
    json_path.chmod(0o600)
    with pytest.raises((checker.EvidenceCheckError, evidence.EvidenceValidationError)):
        checker.check_report(report_root, expected_candidate=COMMIT, now=NOW)

    json_path.write_text(original_json)
    json_path.chmod(0o640)
    with pytest.raises(checker.EvidenceCheckError, match="owner-only"):
        checker.check_report(report_root, expected_candidate=COMMIT, now=NOW)
    json_path.chmod(0o600)
    markdown_path.write_text(markdown_path.read_text() + "\ndrift\n")
    markdown_path.chmod(0o600)
    with pytest.raises(checker.EvidenceCheckError, match="does not match"):
        checker.check_report(report_root, expected_candidate=COMMIT, now=NOW)


def test_compose_command_and_http_allowlists_are_closed(
    isolated_roots: tuple[Path, Path],
) -> None:
    _, runtime = isolated_roots
    run_root = runtime / RUN_ID
    plan = journey.ComposePlan(
        "ithildin-local-v1-node-aaaaaaaa",
        run_root / "compose.env",
        run_root / "compose.override.yml",
        "ithildin/node-journey:aaaaaaaa",
    )
    for command in (
        plan.daemon_version(),
        plan.compose_version(),
        plan.config_check(),
        plan.project_containers(),
        plan.project_volumes(),
        plan.project_networks(),
        plan.list_image(plan.api_image),
        plan.list_image(plan.ui_image),
        plan.list_image(plan.node_image),
        plan.inspect_image(plan.api_image),
        plan.inspect_image(plan.ui_image),
        plan.inspect_image(plan.node_image),
        plan.remove_image(plan.api_image),
        plan.remove_image(plan.ui_image),
        plan.remove_image(plan.node_image),
        plan.start_stack(),
        plan.stack_diagnostic(),
        plan.build_node(),
        plan.enroll_node(),
        plan.start_node(),
        plan.stop_node(),
        plan.revoked_heartbeat(),
        plan.cleanup(remove_volumes=False),
        plan.cleanup(remove_volumes=True),
    ):
        journey._validate_subprocess_command(command)
    with pytest.raises(journey.JourneyError, match="subprocess_command_not_allowed"):
        journey._validate_subprocess_command(plan.command("logs"))
    with pytest.raises(journey.JourneyError, match="subprocess_command_not_allowed"):
        journey._validate_subprocess_command(
            ("docker", "image", "rm", "ithildin/node:local")
        )
    with pytest.raises(journey.JourneyError, match="http_operation_not_allowed"):
        journey._validate_http_operation("GET", "/audit/events", admin=True)
    assert plan.stack_diagnostic()[10:] == (
        "ps",
        "--all",
        "--format",
        "{{.Service}}\t{{.State}}\t{{.Health}}\t{{.ExitCode}}",
        "ithildin-api",
        "ithildin-ui",
    )
    assert plan.cleanup(remove_volumes=False)[10:] == (
        "--profile",
        "node",
        "down",
        "--remove-orphans",
    )
    assert plan.cleanup(remove_volumes=True)[10:] == (
        "--profile",
        "node",
        "down",
        "--remove-orphans",
        "--volumes",
    )
    with pytest.raises(journey.JourneyError, match="subprocess_command_not_allowed"):
        journey._validate_subprocess_command(
            plan.command("--profile", "other", "down", "--volumes")
        )
    diagnostic_text = plan.stack_diagnostic()[13]
    for forbidden in (
        "json",
        "inspect",
        ".State.Error",
        "environment",
        "labels",
        "mounts",
        "ports",
        "command",
    ):
        assert forbidden not in diagnostic_text


def test_compose_override_isolates_runtime_and_run_specific_image(
    tmp_path: Path,
) -> None:
    text = journey._compose_override(
        tmp_path,
        "ithildin/node-journey:aaaaaaaa",
    )
    assert f"source: {(tmp_path / 'var').as_posix()}" in text
    assert f"source: {(tmp_path / 'workspaces').as_posix()}" in text
    assert "image: ithildin/node-journey:aaaaaaaa" in text
    assert "docker.sock" not in text
    assert "privileged" not in text


def test_var_is_wholly_excluded_from_effective_docker_context() -> None:
    dockerignore = (REPO_ROOT / ".dockerignore").read_text().splitlines()
    assert dockerignore.count("var/") == 1
    assert not any(line.startswith("!var") for line in dockerignore)
    for representative in (
        "var/keys/key.pem",
        "var/node-poc-x/state.json",
        "var/node-service-x/state.json",
        "var/review-packets/evidence.json",
        "var/local-v1-node-journey/run/report.json",
        "var/local-v1-node-journey-runtime/run/compose.env",
    ):
        assert representative.startswith("var/")


def test_report_nonclaims_keep_later_milestones_open() -> None:
    joined = "\n".join(evidence.NONCLAIMS)
    assert "No governed tool call or real agent mission" in joined
    assert "No restart, replay, partition" in joined
    assert "No production identity, PostgreSQL, release, promotion, or UAT" in joined


def _minimal_state(
    report_anchor: journey.AnchoredRunDirectory,
    runtime_anchor: journey.AnchoredRunDirectory,
) -> journey.JourneyState:
    return journey.JourneyState(
        run_id=RUN_ID,
        candidate_commit=COMMIT,
        source_clean_start=True,
        report_anchor=report_anchor,
        runtime_anchor=runtime_anchor,
        compose=journey.ComposePlan(
            "ithildin-local-v1-node-aaaaaaaa",
            runtime_anchor.path / "compose.env",
            runtime_anchor.path / "compose.override.yml",
            "ithildin/node-journey:aaaaaaaa",
        ),
        started_at="2026-07-23T12:00:00Z",
        clock=lambda: NOW,
    )

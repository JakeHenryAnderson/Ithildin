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
        if command[:2] == ("docker", "ps") or command[:3] in {
            ("docker", "volume", "ls"),
            ("docker", "network", "ls"),
        }:
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
        if tail == ("--profile", "node", "build", "ithildin-node"):
            self.images[f"ithildin/node-journey:{command[3][-8:]}"] = NODE_IMAGE_ID
            return journey.CommandResult(
                self.node_build_returncode,
                "",
                "synthetic build result",
            )
        return journey.CommandResult(0, "", "")


class FakeApi:
    revoke_succeeds = True
    secret_returned_once = True
    inventory_evidence_status = "complete"
    assignment_evidence_status = "complete"

    def __init__(self, admin_token: str) -> None:
        self.admin_token = admin_token
        self.revoked = False

    def get(self, path: str, *, admin: bool = True) -> JsonObject:
        del admin
        if path == "/healthz":
            return {"status": "ok", "service": "ithildin-api"}
        if path == "/system/status":
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
    reports = tmp_path / "var/local-v1-node-journey"
    runtime = tmp_path / "var/local-v1-node-journey-runtime"
    monkeypatch.setattr(journey, "ROOT", tmp_path)
    monkeypatch.setattr(journey, "REPORT_BASE", reports)
    monkeypatch.setattr(journey, "RUNTIME_BASE", runtime)
    monkeypatch.setattr(journey, "COMPOSE_FILE", tmp_path / "deploy/docker-compose.yml")
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
    down = [command for command, _ in executor.commands if command[10:11] == ("down",)]
    assert down
    assert all("--volumes" not in command for command in down)


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
    down = [command for command, _ in executor.commands if command[10:11] == ("down",)]
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
    monkeypatch.setenv("HOME", "/credential-bearing-home")
    monkeypatch.setenv("DOCKER_AUTH_CONFIG", '{"auths":{"registry.example":{}}}')
    report_anchor = journey.AnchoredRunDirectory.create(journey.REPORT_BASE, RUN_ID)
    runtime_anchor = journey.AnchoredRunDirectory.create(journey.RUNTIME_BASE, RUN_ID)
    try:
        runtime_anchor.mkdir("docker-config")
        state = _minimal_state(report_anchor, runtime_anchor)
        environment = journey._isolated_docker_environment(
            state,
            "unix:///var/run/docker.sock",
        )
        assert set(environment) <= {"PATH", "TMPDIR", "DOCKER_HOST", "DOCKER_CONFIG"}
        assert "HOME" not in environment
        assert "DOCKER_AUTH_CONFIG" not in environment
        config = Path(environment["DOCKER_CONFIG"])
        assert stat.S_IMODE(config.stat().st_mode) == 0o700
        assert not any(config.iterdir())
    finally:
        runtime_anchor.remove_tree()
        report_anchor.remove_tree()


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

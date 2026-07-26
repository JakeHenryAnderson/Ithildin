from __future__ import annotations

import hashlib
import json
import os
import socket
import stat
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
from ithildin_schemas import JsonObject, canonical_json

from scripts import local_v1_lv1_003_o4_attempt008_port_release as release

IDS = {
    "ithildin-api": "1" * 64,
    "ithildin-ui": "2" * 64,
    "ithildin-node": "3" * 64,
    "hermes": "4" * 64,
}
TEST_SEALED_DOCKER = "/private/tmp/ithildin-test-sealed/docker"


def _plan() -> release.Plan:
    return release.Plan(TEST_SEALED_DOCKER)


class FakeSealedExecutable:
    def __init__(self, path: str = TEST_SEALED_DOCKER) -> None:
        self.path = path
        self.verify_count = 0

    def verify(self) -> None:
        self.verify_count += 1


def _fake_identity(path: str | None = None) -> release.ExecutableIdentity:
    return release.ExecutableIdentity(
        path or release.DOCKER_EXECUTABLE.as_posix(),
        1,
        2,
        3,
        4,
        5,
        0o755,
        os.geteuid(),
        os.getegid(),
        "sha256:" + ("a" * 64),
    )


def _ports(service: str) -> JsonObject:
    contract = release.SERVICES[service]
    if contract.container_port is None:
        return {}
    return {
        contract.container_port: [
            {"HostIp": "127.0.0.1", "HostPort": contract.host_port}
        ]
    }


def _projection(
    service: str,
    *,
    container_id: str | None = None,
    image_id: str | None = None,
    project: str = release.PROJECT,
    running: bool = True,
    status_value: str | None = None,
    ports: JsonObject | None = None,
) -> str:
    values: list[object] = [
        container_id or IDS[service],
        image_id or release.SERVICES[service].image_id,
        project,
        service,
        running,
        status_value or ("running" if running else "exited"),
        _ports(service) if ports is None else ports,
    ]
    return "\t".join(json.dumps(value, separators=(",", ":")) for value in values) + "\n"


def _projection_document(
    service: str,
    *,
    running: bool = True,
    allow_cleared_ports: bool = False,
) -> JsonObject:
    return release._projection_record(  # noqa: SLF001
        release._parse_projection(  # noqa: SLF001
            _projection(
                service,
                running=running,
                ports={} if allow_cleared_ports else None,
            ),
            IDS[service],
            allow_cleared_ports=allow_cleared_ports,
        )
    )


class FakeExecutor:
    def __init__(
        self,
        *,
        services: tuple[str, ...] = (
            "ithildin-api",
            "ithildin-ui",
            "ithildin-node",
            "hermes",
        ),
        initially_stopped: frozenset[str] = frozenset(),
    ) -> None:
        self.services = services
        self.running = {
            service: service not in initially_stopped for service in services
        }
        self.commands: list[tuple[str, ...]] = []
        self.stop_failure_service: str | None = None
        self.still_running_after_stop = False
        self.clear_ports_after_stop = False
        self.overrides: dict[str, str] = {}
        self.post_overrides: dict[str, str] = {}
        self.stop_count = 0

    def read(self, command: tuple[str, ...]) -> release.CommandResult:
        self.commands.append(command)
        if command == _plan().query():
            return release.CommandResult(
                0,
                "".join(f"{IDS[service]}\n" for service in self.services),
            )
        container_id = command[-1]
        service = next(
            (name for name in self.services if IDS[name] == container_id),
            "",
        )
        if not service:
            return release.CommandResult(1, "")
        output = self.overrides.get(service)
        if self.stop_count and service in self.post_overrides:
            output = self.post_overrides[service]
        return release.CommandResult(
            0,
            output
            or _projection(
                service,
                running=self.running[service],
                ports=(
                    {}
                    if self.clear_ports_after_stop
                    and not self.running[service]
                    and service in {"ithildin-api", "ithildin-ui"}
                    else None
                ),
            ),
        )

    def stop(
        self,
        service: str,
        command: tuple[str, ...],
    ) -> release.CommandResult:
        self.commands.append(command)
        assert IDS[service] == command[-1]
        self.stop_count += 1
        if self.stop_failure_service == service:
            return release.CommandResult(1, "")
        if not self.still_running_after_stop:
            self.running[service] = False
        return release.CommandResult(0, "")


class RecordingJournal:
    def __init__(self, *, fail_event: str | None = None) -> None:
        self.events: list[tuple[str, JsonObject]] = []
        self.fail_event = fail_event

    def record(self, event: str, payload: JsonObject) -> None:
        self.events.append((event, payload))
        if event == self.fail_event:
            raise release.PortReleaseError("synthetic_journal_termination")


def test_full_success_records_exact_journey_and_never_stops_node_or_hermes() -> None:
    executor = FakeExecutor()
    journal = RecordingJournal()
    outcome = release.execute_port_release(
        executor,
        _plan(),
        journal=journal,
    )

    actions = outcome["actions"]
    assert isinstance(actions, dict)
    assert actions["api"]["status"] == "stopped_observed"
    assert actions["ui"]["status"] == "stopped_observed"
    assert outcome["preservation"]["ithildin-node"] == "observed_unchanged"
    assert outcome["preservation"]["hermes"] == "observed_unchanged"
    assert [
        event for event, _payload in journal.events
    ] == [
        "pre-inspection",
        "api-stop-intent",
        "api-stop-result",
        "ui-stop-intent",
        "ui-stop-result",
        "final-post-inspection",
    ]
    stop_commands = [
        command
        for command in executor.commands
        if command[1:3] == ("container", "stop")
    ]
    assert [command[-1] for command in stop_commands] == [
        IDS["ithildin-api"],
        IDS["ithildin-ui"],
    ]


def test_already_stopped_targets_are_observed_without_stop_intent() -> None:
    executor = FakeExecutor(
        initially_stopped=frozenset({"ithildin-api", "ithildin-ui"})
    )
    journal = RecordingJournal()
    outcome = release.execute_port_release(
        executor,
        _plan(),
        journal=journal,
    )

    assert outcome["actions"]["api"]["status"] == "already_stopped_no_stop_issued"
    assert outcome["actions"]["ui"]["status"] == "already_stopped_no_stop_issued"
    assert not any(command[1:3] == ("container", "stop") for command in executor.commands)
    assert not any(event.endswith("stop-intent") for event, _payload in journal.events)


@pytest.mark.parametrize(
    "output",
    [
        _projection("ithildin-api", project="other"),
        _projection("ithildin-api", image_id="sha256:" + ("f" * 64)),
        _projection("ithildin-api", ports={}),
        _projection(
            "ithildin-api",
            ports={"8000/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8000"}]},
        ),
        _projection("ithildin-api").replace("\t", " ", 1),
        _projection("ithildin-api", container_id="f" * 64),
        _projection("ithildin-api", running=True, status_value="exited"),
        _projection("ithildin-api", running=False, status_value="running"),
        "\xff",
    ],
)
def test_closed_projection_rejects_malformed_identity_labels_and_ports(
    output: str,
) -> None:
    with pytest.raises(release.PortReleaseError, match="container_projection_invalid"):
        release._parse_projection(output, IDS["ithildin-api"])  # noqa: SLF001


def test_duplicate_or_unknown_service_fails_before_mutation() -> None:
    executor = FakeExecutor(services=("ithildin-api", "ithildin-ui"))
    executor.overrides["ithildin-ui"] = _projection(
        "ithildin-api",
        container_id=IDS["ithildin-ui"],
    )
    with pytest.raises(release.PortReleaseError, match="duplicate_project_service"):
        release.execute_port_release(executor, _plan())
    assert not any(command[1:3] == ("container", "stop") for command in executor.commands)

    unknown = _projection("ithildin-api").replace(
        '"ithildin-api"',
        '"unknown-service"',
        1,
    )
    with pytest.raises(release.PortReleaseError, match="container_projection_invalid"):
        release._parse_projection(unknown, IDS["ithildin-api"])  # noqa: SLF001


@pytest.mark.parametrize(
    "output",
    [
        "",
        ("1" * 64) + "\n" + ("1" * 64) + "\n",
        "\n".join(str(index) * 64 for index in range(1, 6)) + "\n",
        "not-an-id\n",
    ],
)
def test_invalid_project_container_set_fails_before_mutation(output: str) -> None:
    class QueryExecutor(FakeExecutor):
        def read(self, command: tuple[str, ...]) -> release.CommandResult:
            self.commands.append(command)
            return release.CommandResult(0, output)

    executor = QueryExecutor()
    with pytest.raises(release.PortReleaseError, match="project_container_query_invalid"):
        release.execute_port_release(executor, _plan())
    assert len(executor.commands) == 1


def test_stop_failure_and_unobserved_stop_keep_truthful_action_state() -> None:
    failed = FakeExecutor(services=("ithildin-api", "ithildin-ui"))
    failed.stop_failure_service = "ithildin-api"
    progress: JsonObject = {}
    with pytest.raises(release.PortReleaseError, match="container_stop_failed"):
        release.execute_port_release(failed, _plan(), progress=progress)
    assert progress["actions"]["api"]["status"] == "stop_command_failed"
    assert progress["actions"]["ui"]["status"] == "not_attempted"

    running = FakeExecutor(services=("ithildin-api", "ithildin-ui"))
    running.still_running_after_stop = True
    progress = {}
    with pytest.raises(release.PortReleaseError, match="container_stop_not_observed"):
        release.execute_port_release(running, _plan(), progress=progress)
    assert progress["actions"]["api"]["status"] == "stop_not_observed"


def test_preservation_change_is_observed_and_never_claimed_preserved() -> None:
    executor = FakeExecutor()
    executor.post_overrides["ithildin-node"] = _projection(
        "ithildin-node",
        running=False,
    )
    progress: JsonObject = {}
    with pytest.raises(release.PortReleaseError, match="preserved_container_changed"):
        release.execute_port_release(executor, _plan(), progress=progress)
    assert progress["preservation"]["ithildin-node"] == "observed_changed"
    record = release._disposition(  # noqa: SLF001
        status="failed",
        outcome=progress,
        failure_code="preserved_container_changed",
    )
    assert record["preservation"]["ithildin-node"] == "observed_changed"


def test_final_project_query_must_match_complete_preinspection_set() -> None:
    class DriftingExecutor(FakeExecutor):
        def read(self, command: tuple[str, ...]) -> release.CommandResult:
            if command == _plan().query() and self.stop_count:
                self.commands.append(command)
                return release.CommandResult(
                    0,
                    "".join(
                        f"{IDS[service]}\n"
                        for service in self.services
                        if service != "hermes"
                    ),
                )
            return super().read(command)

    executor = DriftingExecutor()
    with pytest.raises(
        release.PortReleaseError,
        match="project_container_postset_changed",
    ):
        release.execute_port_release(executor, _plan())


def test_plan_uses_only_absolute_reviewed_docker_path_and_sealed_vocabulary() -> None:
    plan = _plan()
    assert plan.query() == (
        TEST_SEALED_DOCKER,
        "ps",
        "--all",
        "--quiet",
        "--no-trunc",
        "--filter",
        f"label=com.docker.compose.project={release.PROJECT}",
    )
    inspect = plan.inspect("a" * 64)
    assert inspect[0] == TEST_SEALED_DOCKER
    assert "Config.Env" not in release.INSPECT_FORMAT
    assert "Mounts" not in release.INSPECT_FORMAT
    assert "Args" not in release.INSPECT_FORMAT
    for service in ("ithildin-node", "hermes"):
        with pytest.raises(release.PortReleaseError, match="container_stop_not_allowed"):
            plan.stop_command(service, IDS[service])
    with pytest.raises(
        release.PortReleaseError,
        match="sealed_docker_executable_not_allowed",
    ):
        release.Plan(release.DOCKER_EXECUTABLE.as_posix())


def test_adapter_seals_each_stop_service_to_its_exact_container_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sealed = FakeSealedExecutable()
    plan = _plan()
    adapter = release.SubprocessExecutor({}, plan, sealed)
    adapter.bind_ids(set(IDS.values()))
    adapter.bind_stop_targets(
        {
            "ithildin-api": IDS["ithildin-api"],
            "ithildin-ui": IDS["ithildin-ui"],
        }
    )
    with pytest.raises(
        release.PortReleaseError,
        match="docker_stop_command_not_allowed",
    ):
        adapter.stop(
            "ithildin-api",
            plan.stop_command("ithildin-api", IDS["ithildin-ui"]),
        )


def test_post_stop_accepts_only_cleared_nonrunning_api_ui_ports() -> None:
    executor = FakeExecutor()
    executor.clear_ports_after_stop = True
    outcome = release.execute_port_release(executor, _plan())
    assert outcome["actions"]["api"]["status"] == "stopped_observed"
    with pytest.raises(release.PortReleaseError, match="container_projection_invalid"):
        release._parse_projection(  # noqa: SLF001
            _projection("ithildin-api", running=True, ports={}),
            IDS["ithildin-api"],
            allow_cleared_ports=True,
        )


def test_durable_intent_failure_stays_ambiguous_and_precedes_stop() -> None:
    journal = RecordingJournal(fail_event="api-stop-intent")
    executor = FakeExecutor(services=("ithildin-api", "ithildin-ui"))
    progress: JsonObject = {}
    with pytest.raises(
        release.PortReleaseError,
        match="synthetic_journal_termination",
    ):
        release.execute_port_release(
            executor,
            _plan(),
            progress=progress,
            journal=journal,
        )
    assert progress["actions"]["api"]["status"] == "intent_durable_result_unknown"
    assert [event for event, _payload in journal.events] == [
        "pre-inspection",
        "api-stop-intent",
    ]
    assert not any(command[1:3] == ("container", "stop") for command in executor.commands)


def _receipt_path(repo_root: Path, name: str) -> Path:
    return repo_root / release.RECEIPT_ROOT / name


def _make_retained_root(repo_root: Path) -> Path:
    (repo_root / "var").mkdir()
    base = repo_root / release.RETAINED_ROOT.parent
    base.mkdir(mode=0o700)
    root = repo_root / release.RETAINED_ROOT
    root.mkdir(mode=0o700)
    return root


def test_consumption_is_self_contained_owner_only_and_immutable(tmp_path: Path) -> None:
    (tmp_path / "var").mkdir()
    release.consume_budget(
        tmp_path,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    )
    receipt = _receipt_path(tmp_path, release.CONSUMED_RECEIPT)
    record = json.loads(receipt.read_text(encoding="utf-8"))
    assert record == release._consumption_record("a" * 40, "b" * 40)  # noqa: SLF001
    assert record["target"]["run_id"] == release.RUN_ID
    assert record["target"]["compose_project"] == release.PROJECT
    assert set(record["target"]["service_image_ids"]) == set(release.SERVICES)
    assert stat.S_IMODE(receipt.stat().st_mode) == 0o600
    original = receipt.read_bytes()
    with pytest.raises(
        release.PortReleaseError,
        match="attempt_budget_already_consumed",
    ):
        release.consume_budget(
            tmp_path,
            candidate_commit="a" * 40,
            candidate_tree="b" * 40,
        )
    assert receipt.read_bytes() == original


def test_concurrent_consumption_has_exactly_one_winner(tmp_path: Path) -> None:
    (tmp_path / "var").mkdir()

    def attempt() -> str:
        try:
            release.consume_budget(
                tmp_path,
                candidate_commit="a" * 40,
                candidate_tree="b" * 40,
            )
        except release.PortReleaseError as exc:
            return exc.code
        return "created"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = sorted(pool.map(lambda _index: attempt(), range(2)))
    assert outcomes == ["attempt_budget_already_consumed", "created"]


def test_journal_leaves_are_exclusive_ordered_and_file_directory_fsynced(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "var").mkdir()
    fsync_kinds: list[str] = []
    real_fsync = os.fsync

    def observed_fsync(descriptor: int) -> None:
        details = os.fstat(descriptor)
        fsync_kinds.append("directory" if stat.S_ISDIR(details.st_mode) else "file")
        real_fsync(descriptor)

    monkeypatch.setattr(release.os, "fsync", observed_fsync)
    session = release.consume_budget(
        tmp_path,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    )
    journal = session.journal()
    journal.record(
        "pre-inspection",
        {
            "compose_project": release.PROJECT,
            "projections": {
                service: _projection_document(service)
                for service in ("ithildin-api", "ithildin-ui")
            },
        },
    )
    journal.record(
        "api-stop-intent",
        {
            "service": "ithildin-api",
            "container_id": IDS["ithildin-api"],
            "image_id": release.SERVICES["ithildin-api"].image_id,
            "action": "exact_container_stop_time_10",
            "result_at_record_time": "unknown",
        },
    )
    names = sorted(
        item.name
        for item in _receipt_path(tmp_path, release.JOURNAL_DIRECTORY).iterdir()
    )
    assert names == [
        "0001-pre-inspection.json",
        "0002-api-stop-intent.json",
    ]
    assert {"file", "directory"} <= set(fsync_kinds)
    with pytest.raises(release.PortReleaseError, match="journal_not_empty"):
        session.journal()


def test_actual_journal_leaves_durable_unknown_result_after_stop_termination(
    tmp_path: Path,
) -> None:
    (tmp_path / "var").mkdir()
    session = release.consume_budget(
        tmp_path,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    )
    journal = session.journal()

    class TerminatingExecutor(FakeExecutor):
        def stop(
            self,
            service: str,
            command: tuple[str, ...],
        ) -> release.CommandResult:
            self.commands.append(command)
            raise release.PortReleaseError("synthetic_termination")

    progress: JsonObject = {}
    with pytest.raises(release.PortReleaseError, match="synthetic_termination"):
        release.execute_port_release(
            TerminatingExecutor(services=("ithildin-api", "ithildin-ui")),
            _plan(),
            progress=progress,
            journal=journal,
        )
    journal_root = _receipt_path(tmp_path, release.JOURNAL_DIRECTORY)
    names = sorted(item.name for item in journal_root.iterdir())
    assert names == [
        "0001-pre-inspection.json",
        "0002-api-stop-intent.json",
    ]
    intent = json.loads((journal_root / names[-1]).read_text(encoding="utf-8"))
    assert intent["payload"]["result_at_record_time"] == "unknown"
    assert progress["actions"]["api"]["status"] == "intent_durable_result_unknown"


def _write_receipt_document(path: Path, document: JsonObject) -> None:
    path.write_text(canonical_json(document) + "\n", encoding="utf-8")
    path.chmod(0o600)


def _completed_receipt_lane(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    finalize: bool = True,
) -> tuple[release.ReceiptSession, release.DurableJournal, JsonObject]:
    (tmp_path / "var").mkdir()
    session = release.consume_budget(
        tmp_path,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    )
    journal = session.journal()
    outcome = release.execute_port_release(
        FakeExecutor(),
        _plan(),
        journal=journal,
    )

    class SyntheticSocket:
        def setsockopt(self, *_args: object) -> None:
            return None

        def bind(self, _address: tuple[str, int]) -> None:
            return None

        def close(self) -> None:
            return None

    monkeypatch.setattr(socket, "socket", lambda *_args: SyntheticSocket())
    release.observe_ports_available(outcome, journal=journal)
    if finalize:
        session.finalize(
            journal,
            status="completed",
            outcome=outcome,
            failure_code=None,
        )
    return session, journal, outcome


def _rewrite_intent_and_disposition_outcome(
    repo_root: Path,
    mutate: Any,
) -> None:
    journal_root = _receipt_path(repo_root, release.JOURNAL_DIRECTORY)
    intent_path = sorted(journal_root.iterdir())[-1]
    intent = json.loads(intent_path.read_text(encoding="utf-8"))
    mutate(intent["payload"]["outcome"])
    _write_receipt_document(intent_path, intent)
    status_value = intent["payload"]["status"]
    failure_code = intent["payload"]["failure_code"]
    disposition = release._disposition(  # noqa: SLF001
        status=status_value,
        outcome=intent["payload"]["outcome"],
        failure_code=failure_code,
    )
    _write_receipt_document(
        _receipt_path(repo_root, release.DISPOSITION_RECEIPT),
        disposition,
    )


def test_completed_journal_and_disposition_are_exactly_closed_and_crosslinked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _completed_receipt_lane(tmp_path, monkeypatch)
    state = release.inspect_receipt_lane(
        tmp_path,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    )
    assert state == release.ReceiptLaneState("consumed", True, None)
    names = sorted(
        path.name
        for path in _receipt_path(
            tmp_path,
            release.JOURNAL_DIRECTORY,
        ).iterdir()
    )
    assert names == [
        "0001-pre-inspection.json",
        "0002-api-stop-intent.json",
        "0003-api-stop-result.json",
        "0004-ui-stop-intent.json",
        "0005-ui-stop-result.json",
        "0006-final-post-inspection.json",
        "0007-port-8000-bind-observation.json",
        "0008-port-5173-bind-observation.json",
        "0009-simultaneous-port-set-observation.json",
        "0010-disposition-intent.json",
    ]
    intent = json.loads(
        (
            _receipt_path(tmp_path, release.JOURNAL_DIRECTORY)
            / names[-1]
        ).read_text(encoding="utf-8")
    )
    disposition = json.loads(
        _receipt_path(
            tmp_path,
            release.DISPOSITION_RECEIPT,
        ).read_text(encoding="utf-8")
    )
    assert disposition == release._disposition(  # noqa: SLF001
        status=intent["payload"]["status"],
        outcome=intent["payload"]["outcome"],
        failure_code=intent["payload"]["failure_code"],
    )


def test_failed_preinspection_intent_requires_exact_default_outcome(
    tmp_path: Path,
) -> None:
    (tmp_path / "var").mkdir()
    session = release.consume_budget(
        tmp_path,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    )
    journal = session.journal()
    session.finalize(
        journal,
        status="failed",
        outcome=release._new_outcome(),  # noqa: SLF001
        failure_code="ambient_authority_environment_rejected",
    )
    state = release.inspect_receipt_lane(
        tmp_path,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    )
    assert state == release.ReceiptLaneState("consumed", True, None)
    names = [
        path.name
        for path in _receipt_path(
            tmp_path,
            release.JOURNAL_DIRECTORY,
        ).iterdir()
    ]
    assert names == ["0001-disposition-intent.json"]

    def mutate(outcome: JsonObject) -> None:
        outcome["preservation"]["volumes"] = "observed_changed"

    _rewrite_intent_and_disposition_outcome(tmp_path, mutate)
    invalid = release.inspect_receipt_lane(
        tmp_path,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    )
    assert invalid == release.ReceiptLaneState(
        "consumed",
        False,
        "receipt_lane_invalid",
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("container_id", "f" * 64),
        ("pre_running", False),
    ],
)
def test_nondefault_action_must_crosslink_to_before_intent_and_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: object,
) -> None:
    _completed_receipt_lane(tmp_path, monkeypatch)

    def mutate(outcome: JsonObject) -> None:
        outcome["actions"]["api"][field] = value

    _rewrite_intent_and_disposition_outcome(tmp_path, mutate)
    state = release.inspect_receipt_lane(
        tmp_path,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    )
    assert state.valid is False
    assert state.consumption_status == "consumed"


def test_unknown_stop_result_action_must_crosslink_to_durable_intent(
    tmp_path: Path,
) -> None:
    (tmp_path / "var").mkdir()
    session = release.consume_budget(
        tmp_path,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    )
    journal = session.journal()

    class TerminatingExecutor(FakeExecutor):
        def stop(
            self,
            service: str,
            command: tuple[str, ...],
        ) -> release.CommandResult:
            self.commands.append(command)
            raise release.PortReleaseError("synthetic_termination")

    outcome: JsonObject = {}
    with pytest.raises(release.PortReleaseError, match="synthetic_termination"):
        release.execute_port_release(
            TerminatingExecutor(
                services=("ithildin-api", "ithildin-ui"),
            ),
            _plan(),
            progress=outcome,
            journal=journal,
        )
    session.finalize(
        journal,
        status="failed",
        outcome=outcome,
        failure_code="synthetic_termination",
    )
    assert release.inspect_receipt_lane(
        tmp_path,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    ).valid

    def mutate(progress: JsonObject) -> None:
        progress["actions"]["api"]["container_id"] = "f" * 64

    _rewrite_intent_and_disposition_outcome(tmp_path, mutate)
    invalid = release.inspect_receipt_lane(
        tmp_path,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    )
    assert invalid.valid is False
    assert invalid.consumption_status == "consumed"


def test_stop_result_status_must_match_post_observation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _completed_receipt_lane(tmp_path, monkeypatch)
    journal_root = _receipt_path(tmp_path, release.JOURNAL_DIRECTORY)
    result_path = journal_root / "0003-api-stop-result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    post = result["payload"]["post_observation"]
    post["running"] = True
    post["status"] = "running"
    _write_receipt_document(result_path, result)

    def mutate(outcome: JsonObject) -> None:
        action_post = outcome["actions"]["api"]["post_observation"]
        action_post["running"] = True
        action_post["status"] = "running"

    _rewrite_intent_and_disposition_outcome(tmp_path, mutate)
    invalid = release.inspect_receipt_lane(
        tmp_path,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    )
    assert invalid == release.ReceiptLaneState(
        "consumed",
        False,
        "receipt_lane_invalid",
    )


def test_no_stop_result_requires_a_matching_stopped_preinspection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "var").mkdir()
    session = release.consume_budget(
        tmp_path,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    )
    journal = session.journal()
    outcome = release.execute_port_release(
        FakeExecutor(initially_stopped=frozenset({"ithildin-api"})),
        _plan(),
        journal=journal,
    )

    class SyntheticSocket:
        def setsockopt(self, *_args: object) -> None:
            return None

        def bind(self, _address: tuple[str, int]) -> None:
            return None

        def close(self) -> None:
            return None

    monkeypatch.setattr(socket, "socket", lambda *_args: SyntheticSocket())
    release.observe_ports_available(outcome, journal=journal)
    session.finalize(
        journal,
        status="completed",
        outcome=outcome,
        failure_code=None,
    )

    journal_root = _receipt_path(tmp_path, release.JOURNAL_DIRECTORY)
    pre_path = journal_root / "0001-pre-inspection.json"
    pre = json.loads(pre_path.read_text(encoding="utf-8"))
    pre_projection = pre["payload"]["projections"]["ithildin-api"]
    pre_projection["running"] = True
    pre_projection["status"] = "running"
    _write_receipt_document(pre_path, pre)

    def mutate(progress: JsonObject) -> None:
        before = progress["before_projections"]["ithildin-api"]
        before["running"] = True
        before["status"] = "running"
        progress["actions"]["api"]["pre_running"] = True

    _rewrite_intent_and_disposition_outcome(tmp_path, mutate)
    invalid = release.inspect_receipt_lane(
        tmp_path,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    )
    assert invalid == release.ReceiptLaneState(
        "consumed",
        False,
        "receipt_lane_invalid",
    )


@pytest.mark.parametrize("resource", ["ithildin-node", "volumes"])
def test_preservation_must_be_derived_or_fixed_not_targeted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    resource: str,
) -> None:
    _completed_receipt_lane(tmp_path, monkeypatch)

    def mutate(outcome: JsonObject) -> None:
        outcome["preservation"][resource] = "observed_changed"

    _rewrite_intent_and_disposition_outcome(tmp_path, mutate)
    state = release.inspect_receipt_lane(
        tmp_path,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    )
    assert state.valid is False
    assert state.consumption_status == "consumed"


def test_observed_container_disappearance_cannot_be_reported_not_targeted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _completed_receipt_lane(tmp_path, monkeypatch)
    journal_root = _receipt_path(tmp_path, release.JOURNAL_DIRECTORY)
    final_path = journal_root / "0006-final-post-inspection.json"
    final = json.loads(final_path.read_text(encoding="utf-8"))
    final["payload"]["projections"].pop("ithildin-node")
    _write_receipt_document(final_path, final)

    def mutate(outcome: JsonObject) -> None:
        outcome["after_projections"].pop("ithildin-node")
        outcome["preservation"]["ithildin-node"] = "not_targeted_by_recovery"

    _rewrite_intent_and_disposition_outcome(tmp_path, mutate)
    invalid = release.inspect_receipt_lane(
        tmp_path,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    )
    assert invalid == release.ReceiptLaneState(
        "consumed",
        False,
        "receipt_lane_invalid",
    )


def test_failed_port_observations_are_derived_from_failed_journal_events(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "var").mkdir()
    session = release.consume_budget(
        tmp_path,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    )
    journal = session.journal()
    outcome = release.execute_port_release(
        FakeExecutor(),
        _plan(),
        journal=journal,
    )

    class FailingSecondSocket:
        count = 0

        def setsockopt(self, *_args: object) -> None:
            return None

        def bind(self, _address: tuple[str, int]) -> None:
            type(self).count += 1
            if type(self).count == 2:
                raise OSError("synthetic")

        def close(self) -> None:
            return None

    monkeypatch.setattr(socket, "socket", lambda *_args: FailingSecondSocket())
    with pytest.raises(
        release.PortReleaseError,
        match="point_in_time_port_bind_failed",
    ):
        release.observe_ports_available(outcome, journal=journal)
    session.finalize(
        journal,
        status="failed",
        outcome=outcome,
        failure_code="point_in_time_port_bind_failed",
    )
    assert release.inspect_receipt_lane(
        tmp_path,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    ).valid

    def mutate(progress: JsonObject) -> None:
        progress["port_observations"][0]["status"] = (
            "individual_bind_succeeded_pending_complete_set"
        )

    _rewrite_intent_and_disposition_outcome(tmp_path, mutate)
    invalid = release.inspect_receipt_lane(
        tmp_path,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    )
    assert invalid.valid is False
    assert invalid.consumption_status == "consumed"


def test_disposition_leaf_must_equal_failed_journal_derived_disposition(
    tmp_path: Path,
) -> None:
    (tmp_path / "var").mkdir()
    session = release.consume_budget(
        tmp_path,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    )
    outcome = release._new_outcome()  # noqa: SLF001
    journal = session.journal()
    session.finalize(
        journal,
        status="failed",
        outcome=outcome,
        failure_code="synthetic_failure",
    )
    altered = release._disposition(  # noqa: SLF001
        status="failed",
        outcome=outcome,
        failure_code="different_failure",
    )
    _write_receipt_document(
        _receipt_path(tmp_path, release.DISPOSITION_RECEIPT),
        altered,
    )
    state = release.inspect_receipt_lane(
        tmp_path,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    )
    assert state.valid is False
    assert state.consumption_status == "consumed"


def test_disposition_leaf_must_equal_completed_journal_derived_disposition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _completed_receipt_lane(tmp_path, monkeypatch)
    disposition_path = _receipt_path(
        tmp_path,
        release.DISPOSITION_RECEIPT,
    )
    disposition = json.loads(disposition_path.read_text(encoding="utf-8"))
    disposition["outcome"]["actions"]["api"]["container_id"] = "f" * 64
    altered = release._disposition(  # noqa: SLF001
        status="completed",
        outcome=disposition["outcome"],
        failure_code=None,
    )
    _write_receipt_document(disposition_path, altered)
    state = release.inspect_receipt_lane(
        tmp_path,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    )
    assert state.valid is False
    assert state.consumption_status == "consumed"


def test_missing_disposition_after_durable_intent_remains_consumed_no_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _session, journal, outcome = _completed_receipt_lane(
        tmp_path,
        monkeypatch,
        finalize=False,
    )
    journal.record(
        "disposition-intent",
        {
            "status": "completed",
            "failure_code": None,
            "outcome": outcome,
        },
    )
    assert not _receipt_path(
        tmp_path,
        release.DISPOSITION_RECEIPT,
    ).exists()
    state = release.inspect_receipt_lane(
        tmp_path,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    )
    assert state == release.ReceiptLaneState("consumed", True, None)


def test_journal_writer_rejects_unknown_payload_and_illegal_transition(
    tmp_path: Path,
) -> None:
    (tmp_path / "var").mkdir()
    session = release.consume_budget(
        tmp_path,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    )
    journal = session.journal()
    with pytest.raises(release.PortReleaseError, match="receipt_lane_invalid"):
        journal.record("unknown-event", {})
    with pytest.raises(release.PortReleaseError, match="receipt_lane_invalid"):
        journal.record(
            "ui-no-stop-result",
            {
                "service": "ithildin-ui",
                "container_id": IDS["ithildin-ui"],
                "status": "already_stopped_no_stop_issued",
                "returncode": None,
                "post_observation": _projection_document("ithildin-ui"),
            },
        )


def test_descriptor_anchored_write_rejects_receipt_root_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "var").mkdir()
    chain = release._open_relative_chain(  # noqa: SLF001
        tmp_path,
        release.RECEIPT_ROOT,
        create=True,
        error_code="receipt_write_failed",
    )
    assert chain is not None
    root = tmp_path / release.RECEIPT_ROOT
    moved = root.with_name(root.name + "-moved")
    original_open = release.os.open
    replaced = False

    def racing_open(
        path: str | bytes | Path,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal replaced
        if path == "receipt.json" and dir_fd is not None and not replaced:
            root.rename(moved)
            root.mkdir(mode=0o700)
            replaced = True
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(release.os, "open", racing_open)
    try:
        with pytest.raises(release.PortReleaseError, match="receipt_write_failed"):
            release._write_json_leaf_exclusive(  # noqa: SLF001
                chain,
                "receipt.json",
                {"status": "first"},
                error_code="receipt_write_failed",
            )
    finally:
        chain.close()


def test_descriptor_anchored_read_rejects_leaf_replacement_after_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipts = tmp_path / "receipts"
    receipts.mkdir(mode=0o700)
    leaf = receipts / "receipt.json"
    leaf.write_text('{"first":true}\n', encoding="utf-8")
    leaf.chmod(0o600)
    chain = release._open_relative_chain(  # noqa: SLF001
        tmp_path,
        Path("receipts"),
        create=False,
        error_code="receipt_lane_invalid",
    )
    assert chain is not None
    original_read = release.os.read
    replaced = False

    def racing_read(descriptor: int, size: int) -> bytes:
        nonlocal replaced
        content = original_read(descriptor, size)
        if content and not replaced:
            leaf.unlink()
            leaf.write_text('{"second":true}\n', encoding="utf-8")
            leaf.chmod(0o600)
            replaced = True
        return content

    monkeypatch.setattr(release.os, "read", racing_read)
    with chain:
        with pytest.raises(release.PortReleaseError, match="receipt_lane_invalid"):
            release._read_leaf(  # noqa: SLF001
                chain,
                "receipt.json",
                expected_mode=0o600,
                maximum_size=1024,
                error_code="receipt_lane_invalid",
            )


def test_descriptor_anchored_read_rejects_same_inode_same_size_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipts = tmp_path / "receipts"
    receipts.mkdir(mode=0o700)
    leaf = receipts / "receipt.json"
    leaf.write_text('{"first":true}\n', encoding="utf-8")
    leaf.chmod(0o600)
    chain = release._open_relative_chain(  # noqa: SLF001
        tmp_path,
        Path("receipts"),
        create=False,
        error_code="receipt_lane_invalid",
    )
    assert chain is not None
    original_read = release.os.read
    mutated = False

    def racing_read(descriptor: int, size: int) -> bytes:
        nonlocal mutated
        content = original_read(descriptor, size)
        if content and not mutated:
            with leaf.open("r+b") as stream:
                stream.write(b'{"other":true}\n')
                stream.flush()
                os.fsync(stream.fileno())
            mutated = True
        return content

    monkeypatch.setattr(release.os, "read", racing_read)
    with chain:
        with pytest.raises(release.PortReleaseError, match="receipt_lane_invalid"):
            release._read_leaf(  # noqa: SLF001
                chain,
                "receipt.json",
                expected_mode=0o600,
                maximum_size=1024,
                error_code="receipt_lane_invalid",
            )


def test_private_receipt_ancestor_symlink_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "var").mkdir()
    target = tmp_path / "receipt-target"
    target.mkdir()
    (tmp_path / release.RECEIPT_ROOT.parent).symlink_to(target)
    with pytest.raises(release.PortReleaseError, match="receipt_root_invalid"):
        release.consume_budget(
            tmp_path,
            candidate_commit="a" * 40,
            candidate_tree="b" * 40,
        )


def _static_report_patches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        release,
        "candidate_identity",
        lambda _root: ("a" * 40, "b" * 40),
    )
    monkeypatch.setattr(release, "validate_authorization", lambda *_a, **_k: None)
    monkeypatch.setattr(release, "validate_tracked_disposition", lambda _root: None)
    monkeypatch.setattr(release, "validate_retained_receipts", lambda _root: None)
    monkeypatch.setattr(release, "_validate_git_executable", _fake_identity)
    monkeypatch.setattr(release, "_validate_docker_executable", _fake_identity)


def test_report_separates_static_validity_from_durable_execution_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "var").mkdir()
    _static_report_patches(monkeypatch)
    before = release.build_report(tmp_path)
    assert before["valid"] is True
    assert before["static_candidate_valid"] is True
    assert before["execution_available"] is True
    assert before["attempt_budget"] == 1
    assert before["consumed"] is False

    release.consume_budget(
        tmp_path,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    )
    after = release.build_report(tmp_path)
    assert after["valid"] is True
    assert after["static_candidate_valid"] is True
    assert after["execution_available"] is False
    assert after["attempt_budget"] == 0
    assert after["consumed"] is True


def test_corrupt_post_consumption_lane_is_nonvalid_and_never_reopens_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "var").mkdir()
    _static_report_patches(monkeypatch)
    release.consume_budget(
        tmp_path,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    )
    extra = _receipt_path(tmp_path, "unexpected.json")
    extra.write_text("{}\n", encoding="utf-8")
    extra.chmod(0o600)

    report = release.build_report(tmp_path)
    assert report["static_candidate_valid"] is True
    assert report["valid"] is False
    assert report["execution_available"] is False
    assert report["attempt_budget"] == 0
    assert report["consumed"] is True
    assert report["consumption_status"] == "consumed"
    assert report["execution_failures"] == ["receipt_lane_invalid"]


def test_nonempty_unknown_receipt_lane_presumes_consumption_and_budget_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "var").mkdir()
    _static_report_patches(monkeypatch)
    receipt_root = tmp_path / release.RECEIPT_ROOT
    receipt_root.mkdir(parents=True, mode=0o700)
    unknown = receipt_root / "unknown.json"
    unknown.write_text("{}\n", encoding="utf-8")
    unknown.chmod(0o600)

    report = release.build_report(tmp_path)
    assert report["static_candidate_valid"] is True
    assert report["valid"] is False
    assert report["execution_available"] is False
    assert report["attempt_budget"] == 0
    assert report["consumed"] is None
    assert report["consumption_status"] == "presumed_consumed_unknown"
    assert report["execution_failures"] == ["receipt_lane_invalid"]


def test_retained_validator_is_anchored_and_does_not_traverse_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _make_retained_root(tmp_path)
    candidate = root / "candidate"
    candidate.mkdir(mode=0o700)
    (candidate / "unread-symlink").symlink_to("/unavailable")
    candidate.chmod(0o500)
    for name in ("candidate-manifest.json", "diagnostic.json", "disposition.json"):
        path = root / name
        path.write_bytes(b"placeholder")
        path.chmod(0o600)
    observed: list[str] = []
    monkeypatch.setattr(
        release,
        "_hash_exact_leaf",
        lambda _chain, name, **_kwargs: observed.append(name),
    )
    try:
        release.validate_retained_receipts(tmp_path)
        assert sorted(observed) == [
            "candidate-manifest.json",
            "diagnostic.json",
            "disposition.json",
        ]
    finally:
        candidate.chmod(0o700)


@pytest.mark.parametrize("kind", ["root_mode", "candidate_symlink", "file_symlink"])
def test_retained_modes_and_symlinks_fail_closed(
    tmp_path: Path,
    kind: str,
) -> None:
    root = _make_retained_root(tmp_path)
    candidate = root / "candidate"
    if kind == "candidate_symlink":
        target = tmp_path / "candidate-target"
        target.mkdir()
        candidate.symlink_to(target)
    else:
        candidate.mkdir(mode=0o500)
    for name in ("candidate-manifest.json", "diagnostic.json", "disposition.json"):
        path = root / name
        if kind == "file_symlink" and name == "diagnostic.json":
            target = tmp_path / "diagnostic-target"
            target.write_bytes(b"x")
            path.symlink_to(target)
        else:
            path.write_bytes(b"x")
            path.chmod(0o600)
    if kind == "root_mode":
        root.chmod(0o755)
    with pytest.raises(release.PortReleaseError, match="retained_receipt_invalid"):
        release.validate_retained_receipts(tmp_path)
    if candidate.is_dir() and not candidate.is_symlink():
        candidate.chmod(0o700)


def test_hash_exact_leaf_validates_post_read_digest_mode_and_size(
    tmp_path: Path,
) -> None:
    receipts = tmp_path / "receipts"
    receipts.mkdir(mode=0o700)
    content = b"bounded-evidence"
    path = receipts / "receipt"
    path.write_bytes(content)
    path.chmod(0o600)
    chain = release._open_relative_chain(  # noqa: SLF001
        tmp_path,
        Path("receipts"),
        create=False,
        error_code="retained_receipt_invalid",
    )
    assert chain is not None
    with chain:
        release._hash_exact_leaf(  # noqa: SLF001
            chain,
            "receipt",
            size=len(content),
            digest="sha256:" + hashlib.sha256(content).hexdigest(),
        )
        with pytest.raises(release.PortReleaseError, match="retained_receipt_invalid"):
            release._hash_exact_leaf(  # noqa: SLF001
                chain,
                "receipt",
                size=len(content),
                digest="sha256:" + ("0" * 64),
            )


def _candidate_git(
    monkeypatch: pytest.MonkeyPatch,
    *,
    dirty: bool = False,
    parent: str = release.PARENT_COMMIT,
    paths: list[str] | None = None,
) -> None:
    commit = "a" * 40

    def fake_git(_root: Path, *arguments: str) -> str:
        if arguments[:2] == ("status", "--porcelain"):
            return "dirty" if dirty else ""
        if arguments == ("rev-parse", "HEAD"):
            return commit
        if arguments == ("rev-parse", "HEAD^{tree}"):
            return "b" * 40
        if arguments[:3] == ("rev-list", "--parents", "-n"):
            return f"{commit} {parent}"
        if arguments == ("rev-parse", f"{release.PARENT_COMMIT}^{{tree}}"):
            return release.PARENT_TREE
        if arguments[:3] == ("diff-tree", "--no-commit-id", "--name-only"):
            return "\n".join(paths or release.CANDIDATE_PATH_ALLOWLIST)
        raise AssertionError(arguments)

    monkeypatch.setattr(release, "_git", fake_git)


@pytest.mark.parametrize("case", ["dirty", "parent", "allowlist"])
def test_candidate_gate_rejects_dirty_wrong_parent_or_allowlist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    _candidate_git(
        monkeypatch,
        dirty=case == "dirty",
        parent=("c" * 40 if case == "parent" else release.PARENT_COMMIT),
        paths=(["README.md"] if case == "allowlist" else None),
    )
    with pytest.raises(release.PortReleaseError):
        release.candidate_identity(tmp_path)


def test_authorization_record_is_exact_json() -> None:
    json.loads(release.AUTHORIZATION_JSON.read_text(encoding="utf-8"))
    release.validate_authorization(
        release.ROOT,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    )


def test_executable_digest_mode_and_replacement_fail_closed(
    tmp_path: Path,
) -> None:
    executable = tmp_path / "docker"
    content = b"synthetic-reviewed-binary"
    executable.write_bytes(content)
    executable.chmod(0o755)
    identity = release._executable_identity(  # noqa: SLF001
        executable,
        owner=(os.geteuid(), os.getegid()),
        error_code="docker_executable_invalid",
        expected_size=len(content),
        expected_digest="sha256:" + hashlib.sha256(content).hexdigest(),
    )
    assert identity.digest == "sha256:" + hashlib.sha256(content).hexdigest()
    with pytest.raises(release.PortReleaseError, match="docker_executable_invalid"):
        release._executable_identity(  # noqa: SLF001
            executable,
            owner=(os.geteuid(), os.getegid()),
            error_code="docker_executable_invalid",
            expected_size=len(content),
            expected_digest="sha256:" + ("0" * 64),
        )
    executable.chmod(0o775)
    with pytest.raises(release.PortReleaseError, match="docker_executable_invalid"):
        release._executable_identity(  # noqa: SLF001
            executable,
            owner=(os.geteuid(), os.getegid()),
            error_code="docker_executable_invalid",
        )


def test_fixed_docker_alias_resolves_one_digest_bound_inode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "reviewed-docker"
    content = b"reviewed-docker-binary"
    target.write_bytes(content)
    target.chmod(0o755)
    alias = tmp_path / "docker"
    alias.symlink_to(target)
    owner = (os.geteuid(), os.getegid())
    monkeypatch.setattr(release, "DOCKER_ALIAS", alias)
    monkeypatch.setattr(release, "DOCKER_EXECUTABLE", target)
    monkeypatch.setattr(release, "GIT_OWNER", owner)
    monkeypatch.setattr(release, "DOCKER_OWNER", owner)
    monkeypatch.setattr(release, "DOCKER_EXECUTABLE_SIZE", len(content))
    monkeypatch.setattr(
        release,
        "DOCKER_EXECUTABLE_DIGEST",
        "sha256:" + hashlib.sha256(content).hexdigest(),
    )

    identity = release._validate_docker_executable()  # noqa: SLF001
    assert identity.path == target.as_posix()
    assert identity.digest == "sha256:" + hashlib.sha256(content).hexdigest()

    original = tmp_path / "reviewed-docker-original"
    target.rename(original)
    target.write_bytes(content)
    target.chmod(0o755)
    with pytest.raises(release.PortReleaseError, match="docker_executable_changed"):
        release._revalidate_executable_metadata(  # noqa: SLF001
            identity,
            "docker_executable_changed",
        )


def _patch_synthetic_docker_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    content: bytes = b"synthetic-reviewed-docker-binary",
) -> tuple[Path, Path, Path]:
    target = tmp_path / "reviewed-docker"
    target.write_bytes(content)
    target.chmod(0o755)
    alias = tmp_path / "docker-alias"
    alias.symlink_to(target)
    sealed_parent = tmp_path / "sealed-parent"
    sealed_parent.mkdir(mode=0o700)
    owner = (os.geteuid(), os.getegid())
    monkeypatch.setattr(release, "DOCKER_ALIAS", alias)
    monkeypatch.setattr(release, "DOCKER_EXECUTABLE", target)
    monkeypatch.setattr(release, "GIT_OWNER", owner)
    monkeypatch.setattr(release, "DOCKER_OWNER", owner)
    monkeypatch.setattr(release, "DOCKER_EXECUTABLE_SIZE", len(content))
    monkeypatch.setattr(
        release,
        "DOCKER_EXECUTABLE_DIGEST",
        "sha256:" + hashlib.sha256(content).hexdigest(),
    )
    monkeypatch.setattr(release, "SEALED_TEMP_PARENT", sealed_parent)
    return target, alias, sealed_parent


def test_reviewed_docker_is_copied_to_private_seal_and_only_seal_executes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, _alias, sealed_parent = _patch_synthetic_docker_source(
        tmp_path,
        monkeypatch,
    )
    observed: dict[str, Any] = {}

    def fake_run(
        command: tuple[str, ...],
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[bytes]:
        observed["command"] = command
        observed["environment"] = kwargs["env"]
        return subprocess.CompletedProcess(command, 0, b"ok\n", b"")

    monkeypatch.setattr(release.subprocess, "run", fake_run)
    with release.SealedDockerExecutable.create() as sealed:
        sealed_path = Path(sealed.path)
        sealed_directory = sealed_path.parent
        assert sealed_path != source
        assert sealed_path.read_bytes() == source.read_bytes()
        assert stat.S_IMODE(sealed_directory.stat().st_mode) == 0o700
        assert stat.S_IMODE(sealed_path.stat().st_mode) == 0o500
        plan = release.Plan(sealed.path)
        adapter = release.SubprocessExecutor(
            {
                "DOCKER_HOST": "unix:///synthetic.sock",
                "DOCKER_CONFIG": "/private/synthetic-config",
            },
            plan,
            sealed,
        )
        assert adapter.read(plan.query()).stdout == "ok\n"
        assert observed["command"][0] == sealed.path
        assert observed["command"][0] != source.as_posix()
        assert "PATH" not in observed["environment"]
    assert not sealed_directory.exists()
    assert list(sealed_parent.iterdir()) == []


def test_source_replacement_after_review_is_rejected_before_copy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, _alias, sealed_parent = _patch_synthetic_docker_source(
        tmp_path,
        monkeypatch,
    )
    original_validate = release._validate_docker_executable  # noqa: SLF001
    replaced = False

    def replacing_validate() -> release.ExecutableIdentity:
        nonlocal replaced
        identity = original_validate()
        if not replaced:
            original = source.with_name("reviewed-docker-original")
            source.rename(original)
            source.write_bytes(original.read_bytes())
            source.chmod(0o755)
            replaced = True
        return identity

    monkeypatch.setattr(
        release,
        "_validate_docker_executable",
        replacing_validate,
    )
    with pytest.raises(release.PortReleaseError, match="docker_source_changed"):
        release.SealedDockerExecutable.create()
    assert list(sealed_parent.iterdir()) == []


def test_source_replacement_during_sealed_copy_is_rejected_and_cleaned(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = b"x" * 70_000
    source, _alias, sealed_parent = _patch_synthetic_docker_source(
        tmp_path,
        monkeypatch,
        content=content,
    )
    original_write = release.os.write
    replaced = False

    def racing_write(descriptor: int, payload: bytes) -> int:
        nonlocal replaced
        written = original_write(descriptor, payload)
        if not replaced:
            original = source.with_name("reviewed-docker-original")
            source.rename(original)
            source.write_bytes(content)
            source.chmod(0o755)
            replaced = True
        return written

    monkeypatch.setattr(release.os, "write", racing_write)
    with pytest.raises(release.PortReleaseError, match="docker_source_changed"):
        release.SealedDockerExecutable.create()
    assert list(sealed_parent.iterdir()) == []


def test_sealed_command_revalidates_leaf_before_and_after_each_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _source, _alias, _sealed_parent = _patch_synthetic_docker_source(
        tmp_path,
        monkeypatch,
    )
    command_count = 0

    def fake_run(
        command: tuple[str, ...],
        **_kwargs: Any,
    ) -> subprocess.CompletedProcess[bytes]:
        nonlocal command_count
        command_count += 1
        Path(command[0]).chmod(0o700)
        return subprocess.CompletedProcess(command, 0, b"ok\n", b"")

    monkeypatch.setattr(release.subprocess, "run", fake_run)
    with pytest.raises(
        release.PortReleaseError,
        match="sealed_executable_changed",
    ):
        with release.SealedDockerExecutable.create() as sealed:
            plan = release.Plan(sealed.path)
            release.SubprocessExecutor({}, plan, sealed).read(plan.query())
    assert command_count == 1


@pytest.mark.parametrize("mutation", ["replacement", "content"])
def test_sealed_leaf_replacement_or_content_mutation_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    _source, _alias, sealed_parent = _patch_synthetic_docker_source(
        tmp_path,
        monkeypatch,
    )
    with pytest.raises(
        release.PortReleaseError,
        match="sealed_executable_changed",
    ):
        with release.SealedDockerExecutable.create() as sealed:
            sealed_path = Path(sealed.path)
            original = sealed_path.read_bytes()
            if mutation == "replacement":
                moved = sealed_path.with_name("docker-original")
                sealed_path.rename(moved)
                sealed_path.write_bytes(original)
                sealed_path.chmod(0o500)
                moved.unlink()
            else:
                sealed_path.chmod(0o700)
                sealed_path.write_bytes(b"z" * len(original))
                sealed_path.chmod(0o500)
            sealed.verify()
    assert list(sealed_parent.iterdir()) == []


def test_executable_post_open_error_closes_descriptor_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = tmp_path / "git"
    executable.write_bytes(b"binary")
    executable.chmod(0o755)
    original_fstat = release.os.fstat
    original_close = release.os.close
    opened_descriptor: int | None = None
    close_count = 0

    def failing_fstat(descriptor: int) -> os.stat_result:
        nonlocal opened_descriptor
        opened_descriptor = descriptor
        raise OSError("synthetic post-open failure")

    def observed_close(descriptor: int) -> None:
        nonlocal close_count
        if descriptor == opened_descriptor:
            close_count += 1
        original_close(descriptor)

    monkeypatch.setattr(release.os, "fstat", failing_fstat)
    monkeypatch.setattr(release.os, "close", observed_close)
    with pytest.raises(release.PortReleaseError, match="git_executable_invalid"):
        release._executable_identity(  # noqa: SLF001
            executable,
            owner=(os.geteuid(), os.getegid()),
            error_code="git_executable_invalid",
        )
    monkeypatch.setattr(release.os, "fstat", original_fstat)
    assert close_count == 1


def test_hostile_path_cannot_select_git_or_docker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = _fake_identity(release.GIT_EXECUTABLE.as_posix())
    observed: dict[str, Any] = {}

    def fake_run(
        command: tuple[str, ...],
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[bytes]:
        observed["command"] = command
        observed["environment"] = kwargs["env"]
        return subprocess.CompletedProcess(command, 0, b"ok\n", b"")

    monkeypatch.setattr(release, "_validate_git_executable", lambda: identity)
    monkeypatch.setattr(release.subprocess, "run", fake_run)
    assert release._git(Path("/repo"), "status") == "ok"  # noqa: SLF001
    assert observed["command"][0] == release.GIT_EXECUTABLE.as_posix()
    assert observed["environment"] == {}

    sealed = FakeSealedExecutable()
    with pytest.raises(
        release.PortReleaseError,
        match="docker_environment_not_isolated",
    ):
        release.SubprocessExecutor(
            {"PATH": "/tmp/hostile-shim"},
            _plan(),
            sealed,
        )


@pytest.mark.parametrize("payload", [b"\xffsecret-value", b"x" * 32_769])
def test_subprocess_output_is_bounded_utf8_and_nonreflective(
    monkeypatch: pytest.MonkeyPatch,
    payload: bytes,
) -> None:
    sealed = FakeSealedExecutable()

    def fake_run(
        command: tuple[str, ...],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(command, 0, payload, b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(release.PortReleaseError) as caught:
        release.SubprocessExecutor(
            {
                "DOCKER_HOST": "unix:///socket",
                "DOCKER_CONFIG": "/private/config",
            },
            _plan(),
            sealed,
        ).read(_plan().query())
    assert "secret-value" not in str(caught.value)
    assert "secret-value" not in repr(caught.value)


def test_ambient_environment_rejects_authority_keys_not_normal_keys() -> None:
    release._reject_authority_environment(  # noqa: SLF001
        {
            "HOME": "/synthetic/home",
            "LANG": "en_US.UTF-8",
            "PATH": "/tmp/hostile-shim",
            "TERM": "xterm-256color",
        }
    )
    for key in ("DOCKER_HOST", "OPENAI_API_KEY", "DEPLOY_TOKEN", "AWS_REGION"):
        with pytest.raises(
            release.PortReleaseError,
            match="ambient_authority_environment_rejected",
        ):
            release._reject_authority_environment({key: "unread"})  # noqa: SLF001


def test_port_observation_requires_complete_simultaneous_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class SyntheticSocket:
        count = 0

        def setsockopt(self, *_args: object) -> None:
            return None

        def bind(self, _address: tuple[str, int]) -> None:
            type(self).count += 1

        def close(self) -> None:
            return None

    monkeypatch.setattr(socket, "socket", lambda *_args: SyntheticSocket())
    progress = release._new_outcome()  # noqa: SLF001
    journal = RecordingJournal()
    release.observe_ports_available(progress, journal=journal)
    assert [
        item["status"] for item in progress["port_observations"]
    ] == [
        "confirmed_simultaneously_bound_point_in_time",
        "confirmed_simultaneously_bound_point_in_time",
    ]
    assert journal.events[-1][0] == "simultaneous-port-set-observation"


def test_second_port_failure_never_claims_simultaneous_availability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingSecondSocket:
        count = 0

        def setsockopt(self, *_args: object) -> None:
            return None

        def bind(self, _address: tuple[str, int]) -> None:
            type(self).count += 1
            if type(self).count == 2:
                raise OSError("synthetic")

        def close(self) -> None:
            return None

    monkeypatch.setattr(socket, "socket", lambda *_args: FailingSecondSocket())
    progress = release._new_outcome()  # noqa: SLF001
    journal = RecordingJournal()
    with pytest.raises(release.PortReleaseError, match="point_in_time_port_bind_failed"):
        release.observe_ports_available(progress, journal=journal)
    assert progress["port_observations"][0]["status"] == (
        "individual_bind_succeeded_but_set_failed"
    )
    assert not any(
        event == "simultaneous-port-set-observation"
        for event, _payload in journal.events
    )
    disposition = release._disposition(  # noqa: SLF001
        status="failed",
        outcome=progress,
        failure_code="point_in_time_port_bind_failed",
    )
    assert disposition["ports_point_in_time_available"] is False
    assert disposition["generic_port_owner_claimed"] is False
    assert disposition["future_port_availability_claimed"] is False


def test_disposition_keeps_nonclaims_and_targeting_semantics() -> None:
    outcome = release._new_outcome()  # noqa: SLF001
    record = release._disposition(  # noqa: SLF001
        status="failed",
        outcome=outcome,
        failure_code="synthetic_failure",
    )
    assert record["full_project_cleanup_completed"] is False
    assert record["node_revocation_confirmed"] is False
    assert record["node_enrollment_ambiguous"] is True
    assert record["preservation"]["volumes"] == "not_targeted_by_recovery"
    assert "volume_preserved" not in record
    assert record["release_allowed"] is False
    assert record["uat_complete"] is False


def test_failed_disposition_preserves_confirmed_point_in_time_port_truth() -> None:
    outcome = release._new_outcome()  # noqa: SLF001
    outcome["port_observations"] = [
        {
            "host": "127.0.0.1",
            "port": port,
            "status": "confirmed_simultaneously_bound_point_in_time",
        }
        for port in (8000, 5173)
    ]
    record = release._disposition(  # noqa: SLF001
        status="failed",
        outcome=outcome,
        failure_code="synthetic_failure_after_observation",
    )
    assert record["ports_point_in_time_available"] is True
    assert record["future_port_availability_claimed"] is False


def test_live_target_is_separate_and_not_aggregate_wired() -> None:
    makefile = (release.ROOT / "Makefile").read_text(encoding="utf-8")
    assert makefile.count(f"\n{release.RUN_TARGET}:") == 1
    assert makefile.count(f"\n{release.CHECK_TARGET}:") == 1
    for target in ("release-check", "local-v1-milestone-check", "progress-check"):
        body = makefile.split(f"\n{target}:", 1)[1].split("\n\n", 1)[0]
        assert release.RUN_TARGET not in body
    assert "var/local-v1-lv1-003-o4-reconciliation-receipts/*" in (
        release.ROOT / ".gitignore"
    ).read_text(encoding="utf-8")


def test_tool_surface_and_authority_remain_closed() -> None:
    record = json.loads(release.AUTHORIZATION_JSON.read_text(encoding="utf-8"))
    assert record["tool_count"] == 24
    assert set(record["authority_true"]) == release.TRUE_AUTHORITY
    assert set(record["authority_false"]) == release.FALSE_AUTHORITY
    assert record["release_allowed"] is False
    assert record["uat_complete"] is False
    assert "docker compose" not in canonical_json(record).lower()

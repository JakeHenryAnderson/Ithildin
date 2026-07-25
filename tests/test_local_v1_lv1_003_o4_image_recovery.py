from __future__ import annotations

import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from scripts import local_v1_lv1_003_o4_image_recovery as recovery


def _git(repo: Path, *arguments: str) -> str:
    result = subprocess.run(
        ("git", "-C", str(repo), *arguments),
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _exact_child(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "candidate"
    subprocess.run(
        ("git", "clone", "-q", str(Path.cwd()), str(repo)),
        check=True,
    )
    _git(repo, "checkout", "--detach", recovery.PARENT_COMMIT)
    for relative in recovery.CANDIDATE_PATH_ALLOWLIST:
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(Path(relative).read_bytes())
    _git(repo, "add", "--", *recovery.CANDIDATE_PATH_ALLOWLIST)
    _git(
        repo,
        "-c",
        "user.name=Ithildin Test",
        "-c",
        "user.email=ithildin-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "test: exact Attempt 003 image recovery child",
    )
    return (
        repo,
        _git(repo, "rev-parse", "HEAD"),
        _git(repo, "show", "-s", "--format=%T", "HEAD"),
    )


def _metadata(
    target: recovery.ImageTarget,
    *,
    extra_tag: bool = False,
    project: str = recovery.PROJECT,
    service: str | None = None,
    compose_version: str = recovery.COMPOSE_VERSION,
    operating_system: str = recovery.PLATFORM_OS,
    architecture: str = recovery.PLATFORM_ARCHITECTURE,
) -> str:
    tags = [target.reference]
    if extra_tag:
        tags.append("ithildin/forbidden:latest")
    return json.dumps(
        {
            "Id": target.image_id,
            "RepoTags": tags,
            "Os": operating_system,
            "Architecture": architecture,
            "Config": {
                "Labels": {
                    "com.docker.compose.project": project,
                    "com.docker.compose.service": service or target.service,
                    "com.docker.compose.version": compose_version,
                }
            },
        }
    )


class FakeExecutor:
    def __init__(
        self,
        plan: recovery.RecoveryPlan,
        *,
        drift: str | None = None,
        removal_returncode: int = 0,
        post_present: set[str] | None = None,
        removal_exception: BaseException | None = None,
    ) -> None:
        self.plan = plan
        self.drift = drift
        self.removal_returncode = removal_returncode
        self.post_present = set() if post_present is None else set(post_present)
        self.removal_exception = removal_exception
        self.removed = False
        self.reads: list[tuple[str, ...]] = []
        self.mutations: list[tuple[str, ...]] = []

    def read(self, command: tuple[str, ...]) -> recovery.CommandResult:
        assert command in self.plan.allowed_reads()
        self.reads.append(command)
        for resource in ("container", "volume", "network"):
            if command == self.plan.resource_query(resource):
                if self.drift == f"{resource}_present" and not self.removed:
                    return recovery.CommandResult(0, "unexpected\n")
                return recovery.CommandResult(0, "")
        if command == self.plan.image_query(recovery.HERMES_REFERENCE):
            if self.drift == "hermes_present" and not self.removed:
                return recovery.CommandResult(0, "sha256:" + "f" * 64 + "\n")
            return recovery.CommandResult(0, "")
        for target in recovery.IMAGE_TARGETS:
            if command == self.plan.image_query(target.reference):
                if not self.removed:
                    if self.drift == "reference_wrong_id":
                        return recovery.CommandResult(0, "sha256:" + "e" * 64 + "\n")
                    return recovery.CommandResult(0, target.image_id + "\n")
                if target.image_id in self.post_present:
                    return recovery.CommandResult(0, target.image_id + "\n")
                return recovery.CommandResult(0, "")
            if command == self.plan.image_inspect(target.image_id):
                if self.removed and target.image_id not in self.post_present:
                    return recovery.CommandResult(1, "")
                options: dict[str, object] = {}
                if self.drift == "extra_tag":
                    options["extra_tag"] = True
                elif self.drift == "project_label":
                    options["project"] = "other-project"
                elif self.drift == "service_label":
                    options["service"] = "other-service"
                elif self.drift == "compose_version":
                    options["compose_version"] = "0.0.0"
                elif self.drift == "operating_system":
                    options["operating_system"] = "windows"
                elif self.drift == "architecture":
                    options["architecture"] = "amd64"
                return recovery.CommandResult(0, _metadata(target, **options))
            if command == self.plan.ancestor_containers(target.image_id):
                if self.drift == "ancestor_container" and not self.removed:
                    return recovery.CommandResult(0, "container-id\n")
                return recovery.CommandResult(0, "")
        raise AssertionError(f"unexpected command: {command}")

    def remove(self, command: tuple[str, ...]) -> recovery.CommandResult:
        self.mutations.append(command)
        self.removed = True
        if self.removal_exception is not None:
            raise self.removal_exception
        return recovery.CommandResult(self.removal_returncode, "")


def test_exact_committed_child_derives_recovery_only_authority(
    tmp_path: Path,
) -> None:
    repo, commit, tree = _exact_child(tmp_path)

    report = recovery.build_report(repo)

    assert report["failures"] == []
    assert report["valid"] is True
    assert report["candidate_commit"] == commit
    assert report["candidate_tree"] == tree
    assert report["recovery_attempt_budget"] == 1
    assert report["retry_authorized"] is False
    assert report["recovery_inspection_authorized"] is True
    assert report["exact_image_removal_authorized"] is True
    assert set(report["o4_authority"]) == recovery.O4_AUTHORITY_FIELDS
    assert not any(report["o4_authority"].values())
    assert report["release_allowed"] is False
    assert report["uat_complete"] is False
    recovery.assert_recovery_authorized(repo)


def test_dirty_uncommitted_candidate_fails_closed() -> None:
    report = recovery.build_report(Path.cwd())

    assert report["valid"] is False
    assert report["recovery_attempt_budget"] == 0
    assert report["recovery_inspection_authorized"] is False
    assert report["exact_image_removal_authorized"] is False
    assert not any(report["o4_authority"].values())


def test_fixed_plan_constructs_one_non_force_full_id_removal(tmp_path: Path) -> None:
    plan = recovery.RecoveryPlan(tmp_path / "docker-config")
    command = plan.removal()

    assert command == (
        "docker",
        "--config",
        str(tmp_path / "docker-config"),
        "image",
        "rm",
        *(target.image_id for target in recovery.IMAGE_TARGETS),
    )
    assert "--force" not in command
    assert "-f" not in command
    assert "prune" not in command
    assert not any(target.reference in command for target in recovery.IMAGE_TARGETS)


def test_exact_recovery_prevalidates_removes_once_and_postverifies(
    tmp_path: Path,
) -> None:
    plan = recovery.RecoveryPlan(tmp_path / "docker-config")
    executor = FakeExecutor(plan)

    recovery.execute_recovery(executor, plan)

    assert executor.mutations == [plan.removal()]
    removal_index = len(
        [
            command
            for command in executor.reads
            if command in plan.allowed_reads()
        ]
    )
    assert removal_index == 23
    for target in recovery.IMAGE_TARGETS:
        assert executor.reads.count(plan.image_inspect(target.image_id)) == 2
        assert executor.reads.count(plan.image_query(target.reference)) == 2
        assert executor.reads.count(plan.ancestor_containers(target.image_id)) == 1
    assert executor.reads.count(plan.image_query(recovery.HERMES_REFERENCE)) == 2
    for resource in ("container", "volume", "network"):
        assert executor.reads.count(plan.resource_query(resource)) == 2


@pytest.mark.parametrize(
    "drift",
    [
        "container_present",
        "volume_present",
        "network_present",
        "hermes_present",
        "reference_wrong_id",
        "extra_tag",
        "project_label",
        "service_label",
        "compose_version",
        "operating_system",
        "architecture",
        "ancestor_container",
    ],
)
def test_hostile_precondition_drift_refuses_before_mutation(
    tmp_path: Path,
    drift: str,
) -> None:
    plan = recovery.RecoveryPlan(tmp_path / "docker-config")
    executor = FakeExecutor(plan, drift=drift)

    with pytest.raises(recovery.RecoveryError):
        recovery.execute_recovery(executor, plan)

    assert executor.mutations == []


def test_partial_removal_failure_runs_postverify_and_never_retries(
    tmp_path: Path,
) -> None:
    plan = recovery.RecoveryPlan(tmp_path / "docker-config")
    retained = recovery.IMAGE_TARGETS[-1].image_id
    executor = FakeExecutor(
        plan,
        removal_returncode=1,
        post_present={retained},
    )

    with pytest.raises(
        recovery.RecoveryError,
        match="image_recovery_remove_failed",
    ):
        recovery.execute_recovery(executor, plan)

    assert executor.mutations == [plan.removal()]
    assert plan.image_inspect(recovery.IMAGE_TARGETS[0].image_id) in executor.reads


@pytest.mark.parametrize(
    "removal_exception",
    [
        subprocess.TimeoutExpired(("docker", "image", "rm"), 1.0),
        OSError("simulated adapter failure"),
        RuntimeError("simulated ambiguous adapter crash"),
    ],
)
def test_ambiguous_removal_always_postverifies_and_never_retries(
    tmp_path: Path,
    removal_exception: BaseException,
) -> None:
    plan = recovery.RecoveryPlan(tmp_path / "docker-config")
    executor = FakeExecutor(plan, removal_exception=removal_exception)

    with pytest.raises(
        recovery.RecoveryError,
        match="image_recovery_remove_ambiguous",
    ):
        recovery.execute_recovery(executor, plan)

    assert executor.mutations == [plan.removal()]
    for target in recovery.IMAGE_TARGETS:
        assert executor.reads.count(plan.image_inspect(target.image_id)) == 2
        assert executor.reads.count(plan.image_query(target.reference)) == 2
    assert executor.reads.count(plan.image_query(recovery.HERMES_REFERENCE)) == 2


def test_successful_remove_with_failed_postcondition_is_not_success(
    tmp_path: Path,
) -> None:
    plan = recovery.RecoveryPlan(tmp_path / "docker-config")
    retained = recovery.IMAGE_TARGETS[0].image_id
    executor = FakeExecutor(plan, post_present={retained})

    with pytest.raises(
        recovery.RecoveryError,
        match="image_recovery_image_id_still_present",
    ):
        recovery.execute_recovery(executor, plan)

    assert executor.mutations == [plan.removal()]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value["candidate_binding"].__setitem__(  # type: ignore[union-attr]
            "candidate_commit", "a" * 40
        ),
        lambda value: value["candidate_path_allowlist"].pop(),  # type: ignore[union-attr]
        lambda value: value.__setitem__("recovery_attempt_budget", 2),
        lambda value: value.__setitem__("retry_authorized", True),
        lambda value: value["recovery_authority"].__setitem__(  # type: ignore[union-attr]
            "force_image_removal_authorized", True
        ),
        lambda value: value["recovery_authority"].__setitem__(  # type: ignore[union-attr]
            "durable_consumption_receipt_authorized", False
        ),
        lambda value: value["consumption_contract"].__setitem__(  # type: ignore[union-attr]
            "receipt_removal_authorized", True
        ),
        lambda value: value["o4_authority"].__setitem__(  # type: ignore[union-attr]
            "docker_lifecycle_authorized", True
        ),
        lambda value: value["recovery_target"]["images"][0].__setitem__(  # type: ignore[index,union-attr]
            "image_id", "sha256:" + "0" * 64
        ),
    ],
)
def test_authorization_rejects_scope_budget_or_authority_drift(
    mutate: object,
) -> None:
    authorization = json.loads(
        recovery.AUTHORIZATION_JSON.read_text(encoding="utf-8")
    )
    assert callable(mutate)
    mutate(authorization)
    failures: list[str] = []

    recovery._validate_authorization(  # noqa: SLF001
        Path.cwd(),
        authorization,
        failures,
    )

    assert failures


def _runtime_repository(tmp_path: Path) -> Path:
    repo = tmp_path / "runtime-repo"
    runtime = repo / recovery.RUNTIME_BASE
    runtime.mkdir(parents=True, mode=0o700)
    runtime.chmod(0o700)
    return repo


def test_consumption_receipt_is_exact_owner_only_and_durable(
    tmp_path: Path,
) -> None:
    repo = _runtime_repository(tmp_path)
    commit = "a" * 40
    tree = "b" * 40

    recovery.consume_recovery_budget(
        repo,
        candidate_commit=commit,
        candidate_tree=tree,
    )

    receipt = repo / recovery.RUNTIME_BASE / recovery.CONSUMPTION_RECEIPT
    details = receipt.stat()
    assert stat_mode(details.st_mode) == 0o600
    assert details.st_uid == os.geteuid()
    assert details.st_gid == os.getegid()
    assert receipt.read_bytes() == recovery._consumption_receipt_bytes(  # noqa: SLF001
        commit,
        tree,
    )
    with pytest.raises(
        recovery.RecoveryError,
        match="image_recovery_already_consumed",
    ):
        recovery.consume_recovery_budget(
            repo,
            candidate_commit=commit,
            candidate_tree=tree,
        )
    assert receipt.exists()


def stat_mode(mode: int) -> int:
    return mode & 0o7777


def test_concurrent_consumption_allows_exactly_one_creator(
    tmp_path: Path,
) -> None:
    repo = _runtime_repository(tmp_path)

    def consume() -> str:
        try:
            recovery.consume_recovery_budget(
                repo,
                candidate_commit="a" * 40,
                candidate_tree="b" * 40,
            )
        except recovery.RecoveryError as exc:
            return exc.code
        return "created"

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = (pool.submit(consume), pool.submit(consume))
        outcomes = sorted(future.result() for future in futures)

    assert outcomes == ["created", "image_recovery_already_consumed"]
    assert sorted((repo / recovery.RUNTIME_BASE).iterdir()) == [
        repo / recovery.RUNTIME_BASE / recovery.CONSUMPTION_RECEIPT
    ]


@pytest.mark.parametrize(
    "posture",
    [
        "runtime_symlink",
        "runtime_special",
        "runtime_wrong_mode",
        "wrong_owner",
        "var_symlink",
        "extra_entry",
        "existing_receipt_symlink",
        "existing_receipt_special",
    ],
)
def test_hostile_runtime_posture_refuses_consumption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    posture: str,
) -> None:
    repo = _runtime_repository(tmp_path)
    runtime = repo / recovery.RUNTIME_BASE
    if posture == "runtime_symlink":
        runtime.rmdir()
        external = tmp_path / "external-runtime"
        external.mkdir(mode=0o700)
        runtime.symlink_to(external, target_is_directory=True)
    elif posture == "runtime_special":
        runtime.rmdir()
        os.mkfifo(runtime, 0o700)
    elif posture == "runtime_wrong_mode":
        runtime.chmod(0o755)
    elif posture == "wrong_owner":
        original = recovery._owned_directory  # noqa: SLF001

        def reject_runtime(details: os.stat_result, mode: int | None) -> bool:
            return False if mode == 0o700 else original(details, mode)

        monkeypatch.setattr(recovery, "_owned_directory", reject_runtime)
    elif posture == "var_symlink":
        runtime.rmdir()
        (repo / "var").rmdir()
        external = tmp_path / "external-var"
        (external / recovery.RUNTIME_BASE.name).mkdir(parents=True, mode=0o700)
        (repo / "var").symlink_to(external, target_is_directory=True)
    elif posture == "extra_entry":
        (runtime / "unexpected").write_text("x\n", encoding="utf-8")
    elif posture == "existing_receipt_symlink":
        (runtime / recovery.CONSUMPTION_RECEIPT).symlink_to("/dev/null")
    else:
        os.mkfifo(runtime / recovery.CONSUMPTION_RECEIPT, 0o600)

    with pytest.raises(recovery.RecoveryError):
        recovery.consume_recovery_budget(
            repo,
            candidate_commit="a" * 40,
            candidate_tree="b" * 40,
        )


@pytest.mark.parametrize(
    "failure",
    [
        recovery.RecoveryError("simulated_preflight_failure"),
        subprocess.TimeoutExpired(("docker", "image", "inspect"), 1.0),
        RuntimeError("simulated crash"),
    ],
)
def test_receipt_remains_after_post_consumption_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: BaseException,
) -> None:
    repo, commit, tree = _exact_child(tmp_path)
    runtime = repo / recovery.RUNTIME_BASE
    runtime.mkdir(parents=True, mode=0o700)
    runtime.chmod(0o700)
    monkeypatch.setattr(recovery, "ROOT", repo)
    monkeypatch.setattr(
        recovery.producer,
        "_reject_ambient_authority",
        lambda _: None,
    )
    monkeypatch.setattr(
        recovery.producer,
        "_prove_local_docker_socket",
        lambda: "unix:///test/docker.sock",
    )

    def fail_execute(_: recovery.Executor, __: recovery.RecoveryPlan) -> None:
        raise failure

    monkeypatch.setattr(recovery, "execute_recovery", fail_execute)

    with pytest.raises(
        (recovery.RecoveryError, subprocess.TimeoutExpired, RuntimeError)
    ):
        recovery.run_live_recovery({"PATH": "/usr/bin:/bin"})

    receipt = runtime / recovery.CONSUMPTION_RECEIPT
    assert receipt.is_file()
    assert stat_mode(receipt.stat().st_mode) == 0o600
    receipt_record = json.loads(receipt.read_text(encoding="utf-8"))
    assert receipt_record["status"] == "consumed_before_docker_inspection"
    assert receipt_record["candidate_commit"] == commit
    assert receipt_record["candidate_tree"] == tree
    assert receipt_record["retry_authorized"] is False


def test_receipt_precedes_local_socket_inspection_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _, _ = _exact_child(tmp_path)
    runtime = repo / recovery.RUNTIME_BASE
    runtime.mkdir(parents=True, mode=0o700)
    runtime.chmod(0o700)
    monkeypatch.setattr(recovery, "ROOT", repo)
    monkeypatch.setattr(
        recovery.producer,
        "_reject_ambient_authority",
        lambda _: None,
    )

    def fail_socket() -> str:
        raise recovery.producer.ProducerError("local_docker_socket_unavailable")

    monkeypatch.setattr(recovery.producer, "_prove_local_docker_socket", fail_socket)

    with pytest.raises(
        recovery.RecoveryError,
        match="local_docker_socket_unavailable",
    ):
        recovery.run_live_recovery({"PATH": "/usr/bin:/bin"})

    assert (runtime / recovery.CONSUMPTION_RECEIPT).is_file()


def test_make_target_is_fixed_and_outside_aggregate_dependencies() -> None:
    failures: list[str] = []

    recovery._validate_makefile(Path.cwd(), failures)  # noqa: SLF001

    assert failures == []


def test_arguments_refuse_before_live_recovery(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    called = False

    def forbidden() -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(recovery, "run_live_recovery", forbidden)

    assert recovery.main(["unexpected"]) == 2
    assert called is False
    assert capsys.readouterr().out == "image_recovery_error: arguments_not_allowed\n"


@pytest.mark.parametrize("failure_point", ["temporary_directory", "docker_config"])
def test_tempfile_or_config_oserror_is_stable_and_receipt_remains(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure_point: str,
) -> None:
    repo, _, _ = _exact_child(tmp_path)
    runtime = repo / recovery.RUNTIME_BASE
    runtime.mkdir(parents=True, mode=0o700)
    runtime.chmod(0o700)
    monkeypatch.setattr(recovery, "ROOT", repo)
    monkeypatch.setattr(
        recovery.producer,
        "_reject_ambient_authority",
        lambda _: None,
    )
    monkeypatch.setattr(
        recovery.producer,
        "_prove_local_docker_socket",
        lambda: "unix:///test/docker.sock",
    )

    def unavailable(*_: object, **__: object) -> object:
        raise OSError("simulated local runtime failure")

    if failure_point == "temporary_directory":
        monkeypatch.setattr(recovery.tempfile, "TemporaryDirectory", unavailable)
    else:
        monkeypatch.setattr(recovery, "_write_empty_docker_config", unavailable)

    assert recovery.main([]) == 1
    assert capsys.readouterr().out == (
        "image_recovery_error: image_recovery_local_runtime_unavailable\n"
    )
    assert (runtime / recovery.CONSUMPTION_RECEIPT).is_file()


def test_unicode_failure_has_stable_main_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def unicode_failure() -> None:
        raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "simulated")

    monkeypatch.setattr(recovery, "run_live_recovery", unicode_failure)

    assert recovery.main([]) == 1
    assert capsys.readouterr().out == (
        "image_recovery_error: image_recovery_local_runtime_unavailable\n"
    )


def test_subprocess_adapter_rejects_second_or_broader_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = recovery.RecoveryPlan(tmp_path / "docker-config")
    calls: list[tuple[str, ...]] = []

    def fake_run(command: tuple[str, ...], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "")

    monkeypatch.setattr(recovery.subprocess, "run", fake_run)
    executor = recovery.SubprocessExecutor({}, plan)

    assert executor.remove(plan.removal()).returncode == 0
    with pytest.raises(
        recovery.RecoveryError,
        match="docker_mutation_command_not_allowed",
    ):
        executor.remove(plan.removal())
    with pytest.raises(
        recovery.RecoveryError,
        match="docker_mutation_command_not_allowed",
    ):
        executor.remove((*plan.prefix, "image", "prune"))
    assert calls == [plan.removal()]

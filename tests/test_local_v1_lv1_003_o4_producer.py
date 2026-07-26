from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest
from ithildin_schemas import JsonObject, canonical_json

from scripts import local_v1_constrained_mission_journey as journey
from scripts import local_v1_lv1_003_o4_producer as producer

COMMIT = "a" * 40
TREE = "b" * 40
NODE_ID = "node_" + "1" * 32
MISSION_ID = "mission_" + "2" * 32
CLAIM_ID = "mclaim_" + "3" * 32
RUN_RECORD_ID = "run_" + "4" * 32
ENVELOPE = "sha256:" + "5" * 64
SESSION_ID = f"mission:{MISSION_ID}:{CLAIM_ID}:{'5' * 16}"
DIGEST = "sha256:" + "6" * 64
VALID_ENROLLMENT_PROJECTION: JsonObject = {
    "node_id": NODE_ID,
    "principal_id": f"agent:node.{NODE_ID}",
    "workspace_id": producer.WORKSPACE_ID,
}
VALID_ENROLLMENT_STDOUT = (
    canonical_json(VALID_ENROLLMENT_PROJECTION) + "\n"
)


class FakePrivateDirectory:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.files: dict[str, bytes] = {}
        self.file_modes: dict[str, int] = {}
        self.removed = False
        self.closed = False
        self.validate_calls = 0

    def validate(self) -> None:
        self.validate_calls += 1

    def mkdir(self, relative: str) -> None:
        del relative

    def write(self, relative: str, content: bytes, *, mode: int = 0o600) -> None:
        assert mode in {0o400, 0o500, 0o600, 0o700}
        self.files[relative] = content
        self.file_modes[relative] = mode

    def read(self, relative: str, *, maximum: int = producer.MAX_LICENSE_BYTES) -> bytes:
        content = self.files[relative]
        assert len(content) <= maximum
        return content

    def file(self, relative: str) -> Path:
        return self.path / relative

    def read_exact_owner_file(
        self,
        directory: str,
        filename: str,
        *,
        maximum: int,
    ) -> bytes | None:
        relative = f"{directory}/{filename}"
        inventory = sorted(
            path
            for path in self.files
            if path.startswith(directory + "/")
        )
        if not inventory:
            return None
        if inventory != [relative]:
            raise producer.ProducerError("runtime_file_unsafe")
        content = self.files[relative]
        if self.file_modes.get(relative) != 0o600 or len(content) > maximum:
            raise producer.ProducerError("runtime_file_unsafe")
        return content

    def remove(self) -> bool:
        self.removed = True
        return True

    def remove_tree(self, relative: str) -> bool:
        prefix = relative + "/"
        self.files = {
            path: content
            for path, content in self.files.items()
            if path != relative and not path.startswith(prefix)
        }
        return True

    def close(self) -> None:
        self.closed = True


class FakeRuntimeFactory:
    def __init__(self, root: Path) -> None:
        self.calls = 0
        run_id = "20260724T180000Z-1234abcd"
        self.runtime = FakePrivateDirectory(root / "runtime-base" / run_id)
        self.receipts = FakePrivateDirectory(root / "receipt-base" / run_id)

    def create(
        self, run_id: str
    ) -> tuple[producer.PrivateDirectory, producer.PrivateDirectory]:
        assert run_id == "20260724T180000Z-1234abcd"
        self.calls += 1
        return cast(producer.PrivateDirectory, self.runtime), cast(
            producer.PrivateDirectory, self.receipts
        )


class FakeCandidateSnapshot:
    def __init__(self, root: FakePrivateDirectory) -> None:
        self.root = root
        self.path = root.path / "candidate"
        self.validate_calls = 0
        self.closed = False
        self.manifest = {
            "pyproject.toml": (0o400, DIGEST),
            "uv.lock": (0o400, DIGEST),
        }

    def validate(self) -> None:
        self.validate_calls += 1

    def read(self, relative: str, *, maximum: int = producer.MAX_LICENSE_BYTES) -> bytes:
        content = (producer.ROOT / relative).read_bytes()
        assert len(content) <= maximum
        return content

    def json_object(self, relative: str) -> JsonObject:
        raw = json.loads(self.read(relative))
        assert isinstance(raw, dict)
        return cast(JsonObject, raw)

    def file_digest(self, relative: str) -> str:
        return journey.file_digest(producer.ROOT / relative)

    def source_digest(self, relatives: tuple[str, ...]) -> str:
        return journey.source_digest(
            tuple(producer.ROOT / relative for relative in relatives)
        )

    def source_evidence(self) -> JsonObject:
        return journey.candidate_source_evidence(producer.ROOT)

    def close(self) -> None:
        self.closed = True


class AllowGate:
    def __init__(self, *, allow: bool = True) -> None:
        self.allow = allow
        self.calls: list[tuple[str, str]] = []

    def authorize(self, commit: str, tree: str) -> None:
        self.calls.append((commit, tree))
        if not self.allow:
            raise producer.ProducerError("gate_refused")


class FakeProvider:
    def __init__(self) -> None:
        self.calls = 0

    def exact_models(self) -> tuple[str, ...]:
        self.calls += 1
        return (producer.MODEL,)


def _merged_compose_document(
    plan: producer.ComposePlan,
    *,
    fixed: bool,
) -> JsonObject:
    candidate = plan.candidate
    runtime = plan.runtime
    api_volumes: list[JsonObject] = [
        {"type": "bind", "source": str(source), "target": target}
        for target, source in {
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
            "/run/ithildin-startup": runtime / "startup-status",
        }.items()
    ]
    api_volumes[-1]["read_only"] = False
    services: JsonObject = {
        "ithildin-api": {
            "build": {
                "context": str(candidate),
                "dockerfile": str(candidate / "deploy/Dockerfile.api"),
            },
            "volumes": api_volumes,
        },
        "ithildin-ui": {
            "build": {
                "context": str(candidate),
                "dockerfile": str(candidate / "deploy/Dockerfile.ui"),
            },
            "volumes": [],
        },
        "ithildin-node": {
            "build": {
                "context": str(candidate),
                "dockerfile": str(candidate / "deploy/Dockerfile.node"),
            },
            "tmpfs": list(producer.NODE_TMPFS),
            "volumes": [
                {
                    "type": "volume",
                    "source": "ithildin-node-state",
                    "target": "/var/lib/ithildin-node",
                }
            ],
        },
    }
    if fixed:
        services["hermes"] = {
            "build": {
                "context": str(candidate),
                "dockerfile": str(
                    candidate / "deploy/hermes-node-bridge/Dockerfile"
                ),
            },
            "volumes": [
                {
                    "type": "volume",
                    "source": "ithildin-node-state",
                    "target": "/run/ithildin-node",
                }
            ],
        }
    return {"services": services}


class FakeExecutor:
    def __init__(self, runtime: FakePrivateDirectory) -> None:
        self.runtime = runtime
        self.commands: list[tuple[str, ...]] = []
        self.inputs: list[str | None] = []
        self.timeouts: list[float] = []
        self.hermes_commands: list[tuple[str, ...]] = []
        self.hermes_timeouts: list[float] = []
        self.images: dict[str, str] = {}
        self.bound_image_ids: set[str] = set()
        self.bound_container_ids: set[str] = set()
        self.remaining_image_ids: set[str] = set()
        self.retain_ids_after_removal: set[str] = set()
        self.image_id_probe_modes: dict[str, str] = {}
        self.hermes_result = producer.HermesResult("exit", 0)
        self.image_architectures: dict[str, str] = {}
        self.image_extra_tags: set[str] = set()
        self.image_project_labels: dict[str, str] = {}
        self.image_service_labels: dict[str, str] = {}
        self.image_compose_versions: dict[str, str] = {}
        self.image_ancestor_containers: set[str] = set()
        self.build_failure: str | None = None
        self.base_failure_partial_reference = False
        self.cleanup_drift: str | None = None
        self.cleanup_phase = False
        self.removal_failures: set[str] = set()
        self.base_start_returncode = 0
        self.base_diagnostic_result = producer.CommandResult(
            0,
            (
                "ithildin-api\trunning\tstarting\t0\n"
                "ithildin-ui\texited\t\t1\n"
            ),
        )
        self.base_diagnostic_failure: str | None = None
        self.api_container_id = "a" * 64
        self.api_container_query_result: producer.CommandResult | None = None
        self.api_container_query_failure: str | None = None
        self.api_container_inspect_result: producer.CommandResult | None = None
        self.api_container_inspect_failure: str | None = None
        self.interrupt_on: str | None = None
        self.enrollment_failure: str | None = None
        self.enrollment_stdout: str | None = None

    def bind_image_identity(self, image_id: str) -> None:
        assert producer._DIGEST.fullmatch(image_id)  # noqa: SLF001
        self.bound_image_ids.add(image_id)

    def bind_container_identity(self, container_id: str) -> None:
        assert producer._CONTAINER_ID.fullmatch(container_id)  # noqa: SLF001
        self.bound_container_ids.add(container_id)

    def run(
        self,
        command: tuple[str, ...],
        *,
        input_text: str | None = None,
        timeout: float = 180.0,
    ) -> producer.CommandResult:
        self.timeouts.append(timeout)
        producer._validate_command(  # noqa: SLF001
            command,
            hermes=False,
            inspected_image_ids=frozenset(self.bound_image_ids),
            bound_container_ids=frozenset(self.bound_container_ids),
        )
        self.commands.append(command)
        self.inputs.append(input_text)
        if self.interrupt_on is not None and self.interrupt_on in command:
            raise producer.ProducerSignal("synthetic")
        plan = producer.ComposePlan(
            "20260724T180000Z-1234abcd", self.runtime.path
        )
        base_config = plan.compose(
            "--profile",
            "node",
            "config",
            "--no-interpolate",
            "--format",
            "json",
        )
        fixed_config = plan.compose(
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
        if command in {base_config, fixed_config}:
            return producer.CommandResult(
                0,
                json.dumps(
                    _merged_compose_document(
                        plan,
                        fixed=command == fixed_config,
                    )
                ),
            )
        if command in {plan.daemon_version(), plan.compose_version()}:
            return producer.CommandResult(0, "available")
        if command == plan.base_service_start_diagnostic():
            if self.base_diagnostic_failure == "error":
                raise producer.ProducerError("subprocess_unavailable")
            if self.base_diagnostic_failure == "interruption":
                raise producer.ProducerSignal("synthetic")
            return self.base_diagnostic_result
        if command == plan.api_container_id_query():
            if self.api_container_query_failure == "error":
                raise producer.ProducerError("subprocess_unavailable")
            if self.api_container_query_failure == "timeout":
                raise producer.ProducerError("subprocess_unavailable")
            if self.api_container_query_failure == "interruption":
                raise producer.ProducerSignal("synthetic")
            return self.api_container_query_result or producer.CommandResult(
                0,
                self.api_container_id + "\n",
            )
        for container_id in self.bound_container_ids:
            if command == plan.api_container_state_inspect(container_id):
                if self.api_container_inspect_failure == "error":
                    raise producer.ProducerError("subprocess_unavailable")
                if self.api_container_inspect_failure == "timeout":
                    raise producer.ProducerError("subprocess_unavailable")
                if self.api_container_inspect_failure == "interruption":
                    raise producer.ProducerSignal("synthetic")
                return (
                    self.api_container_inspect_result
                    or producer.CommandResult(
                        0,
                        "\t".join(
                            (
                                container_id,
                                plan.project,
                                "ithildin-api",
                                "exited",
                                "false",
                                "1",
                                "false",
                                "false",
                                "false",
                                "absent",
                            )
                        )
                        + "\n",
                    )
                )
        if command == plan.compose(
            "up",
            "--detach",
            "--wait",
            "ithildin-api",
            "ithildin-ui",
        ):
            return producer.CommandResult(self.base_start_returncode, "")
        for resource in ("container", "volume", "network"):
            if command == plan.resource_query(resource):
                return producer.CommandResult(0, "")
        for reference in plan.images:
            if command == plan.image_query(reference):
                if (
                    self.cleanup_phase
                    and self.cleanup_drift == "reference"
                    and reference == plan.images[0]
                ):
                    return producer.CommandResult(0, "sha256:" + "f" * 64)
                return producer.CommandResult(0, self.images.get(reference, ""))
            if command == plan.image_inspect(reference):
                image_id = "sha256:" + str(plan.images.index(reference) + 1) * 64
                self.images[reference] = image_id
                service = (
                    "ithildin-api",
                    "ithildin-ui",
                    "ithildin-node",
                    "hermes",
                )[plan.images.index(reference)]
                tags = [reference]
                if reference in self.image_extra_tags or (
                    self.cleanup_phase
                    and self.cleanup_drift == "extra_tag"
                    and reference == plan.images[0]
                ):
                    tags.append("ithildin/forbidden:latest")
                return producer.CommandResult(
                    0,
                    json.dumps(
                        {
                            "Id": image_id,
                            "RepoTags": tags,
                            "Os": "linux",
                            "Architecture": self.image_architectures.get(
                                reference,
                                (
                                    "amd64"
                                    if self.cleanup_phase
                                    and self.cleanup_drift == "platform"
                                    and reference == plan.images[0]
                                    else "arm64"
                                ),
                            ),
                            "RootFS": {"Layers": ["sha256:" + "9" * 64]},
                            "Config": {
                                "Labels": {
                                    "com.docker.compose.project": (
                                        self.image_project_labels.get(
                                            reference,
                                            (
                                                "other-project"
                                                if self.cleanup_phase
                                                and self.cleanup_drift == "label"
                                                and reference == plan.images[0]
                                                else plan.project
                                            ),
                                        )
                                    ),
                                    "com.docker.compose.service": (
                                        self.image_service_labels.get(
                                            reference, service
                                        )
                                    ),
                                    "com.docker.compose.version": (
                                        self.image_compose_versions.get(
                                            reference, "5.1.4"
                                        )
                                    ),
                                }
                            },
                        }
                    ),
                )
            image_id = self.images.get(reference)
            if (
                image_id is not None
                and command == plan.image_ancestor_containers(image_id)
            ):
                output = (
                    "container-id\n"
                    if reference in self.image_ancestor_containers
                    or (
                        self.cleanup_phase
                        and self.cleanup_drift == "container"
                        and reference == plan.images[0]
                    )
                    else ""
                )
                return producer.CommandResult(0, output)
        for image_id in self.bound_image_ids:
            if command == plan.image_id_inspect(image_id):
                mode = self.image_id_probe_modes.get(image_id)
                if mode == "error":
                    return producer.CommandResult(2, "", "error")
                if mode == "ambiguous":
                    return producer.CommandResult(1, "", "error")
                if mode == "single_newline":
                    return producer.CommandResult(
                        1,
                        "\n",
                        "image_not_found",
                    )
                hostile_stdout = {
                    "space": " ",
                    "tab": "\t",
                    "crlf": "\r\n",
                    "multiple_newlines": "\n\n",
                    "content": "present",
                }.get(mode)
                if hostile_stdout is not None:
                    return producer.CommandResult(
                        1,
                        hostile_stdout,
                        "image_not_found",
                    )
                if (
                    image_id in self.images.values()
                    or image_id in self.remaining_image_ids
                ):
                    return producer.CommandResult(
                        0,
                        json.dumps(image_id),
                    )
                return producer.CommandResult(1, "", "image_not_found")
        if len(command) == 6 and command[3:5] == ("image", "rm"):
            image_id = command[5]
            if image_id in self.removal_failures:
                return producer.CommandResult(1, "")
            self.images = {
                reference: current
                for reference, current in self.images.items()
                if current != image_id
            }
            if image_id in self.retain_ids_after_removal:
                self.remaining_image_ids.add(image_id)
            else:
                self.remaining_image_ids.discard(image_id)
            return producer.CommandResult(0, "")
        tail = command[max(i for i, value in enumerate(command) if value == "--file") + 2 :]
        if "build" in tail:
            if (
                self.build_failure == "base"
                and "ithildin-api" in tail
            ) or (
                self.build_failure == "bridge"
                and "hermes" in tail
            ):
                if (
                    self.build_failure == "base"
                    and self.base_failure_partial_reference
                ):
                    self.images[plan.images[0]] = "sha256:" + "1" * 64
                self.cleanup_phase = True
                return producer.CommandResult(1, "")
            return producer.CommandResult(0, "")
        if "enroll" in tail:
            if self.enrollment_failure == "nonzero":
                return producer.CommandResult(7, "")
            if self.enrollment_failure == "timeout":
                raise producer.ProducerError("subprocess_unavailable")
            if self.enrollment_failure == "malformed":
                return producer.CommandResult(0, "{")
            if self.enrollment_stdout is not None:
                return producer.CommandResult(0, self.enrollment_stdout)
            return producer.CommandResult(
                0,
                canonical_json(
                    {
                        "node_id": NODE_ID,
                        "principal_id": f"agent:node.{NODE_ID}",
                        "workspace_id": producer.WORKSPACE_ID,
                    }
                )
                + "\n",
            )
        if "cp" in tail:
            self.runtime.files["copied-receipt/node-mission-receipt.json"] = (
                json.dumps(
                    {
                        "mission_id": MISSION_ID,
                        "claim_id": CLAIM_ID,
                        "envelope_digest": ENVELOPE,
                        "next_operation_index": 4,
                        "handoff_nonce_digest": "sha256:" + "8" * 64,
                        "last_closed_status": "runner_reported_succeeded",
                    }
                ).encode()
            )
        return producer.CommandResult(0, "")

    def run_hermes(
        self,
        command: tuple[str, ...],
        *,
        timeout: float,
    ) -> producer.HermesResult:
        producer._validate_command(command, hermes=True)  # noqa: SLF001
        self.hermes_commands.append(command)
        self.hermes_timeouts.append(timeout)
        return self.hermes_result


class FakeExecutorFactory:
    def __init__(self, executor: FakeExecutor) -> None:
        self.executor = executor
        self.environments: list[dict[str, str]] = []

    def create(self, environment: dict[str, str]) -> producer.Executor:
        self.environments.append(environment)
        return self.executor


class FakeApi:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, JsonObject | None]] = []
        self.admission_count = 0
        self.node_overrides: JsonObject = {}
        self.revoke_failure: str | None = None

    def get(self, path: str, *, admin: bool = True) -> JsonObject:
        self.calls.append(("GET", path, None))
        if path == "/healthz":
            assert admin is False
            return {"status": "ok", "service": "ithildin-api"}
        if path == "/system/status":
            return {"status": "ok", "tool_count": 24}
        if path == "/workspaces":
            return {
                "workspaces": [
                    {"id": producer.WORKSPACE_ID, "enabled": True}
                ]
            }
        if path == f"/nodes/{NODE_ID}":
            document: JsonObject = {
                "node_id": NODE_ID,
                "principal_id": f"agent:node.{NODE_ID}",
                "workspace_id": producer.WORKSPACE_ID,
                "identity_source": "gateway_derived",
                "evidence_status": "complete",
                "observed_state": "observed_connected",
                "configuration_state": "stored_current_not_enforced",
                "desired_configuration_generation": 1,
                "desired_configuration_digest": DIGEST,
                "acknowledged_configuration_generation": 1,
                "acknowledged_configuration_digest": DIGEST,
                "last_configuration_digest": DIGEST,
                "configuration_acknowledgment_status": "stored_not_enforced",
                "runner_health_known": False,
                "model_health_known": False,
                "connectivity_source": "gateway_accepted_heartbeat",
            }
            document.update(self.node_overrides)
            return document
        if path == f"/missions/{MISSION_ID}":
            return {
                "mission_id": MISSION_ID,
                "target_node_id": NODE_ID,
                "lifecycle_state": "runner_reported_succeeded",
                "envelope_digest": ENVELOPE,
                "delivery": {"claim": {"claim_id": CLAIM_ID}},
                "governed_agent_runs": {
                    "authority": "gateway_agent_run_evidence",
                    "correlation_basis": "gateway_validated_claim_session",
                    "rejected_correlation_count": 0,
                    "runs": [
                        {
                            "run_id": RUN_RECORD_ID,
                            "status": "active",
                            "tool_call_count": 2,
                        }
                    ],
                },
            }
        if path == f"/runs/{RUN_RECORD_ID}":
            return {
                "run": {
                    "run_id": RUN_RECORD_ID,
                    "session_id": SESSION_ID,
                    "status": "active",
                    "tool_call_count": 2,
                },
                "timeline": [
                    _event(1, "project.structure.summary"),
                    _event(2, "project.test.summary"),
                ],
            }
        raise AssertionError(path)

    def post(self, path: str, payload: JsonObject) -> JsonObject:
        self.calls.append(("POST", path, payload))
        if path == "/nodes/enrollment-codes":
            return {
                "enrollment_code": "one-time-enrollment",
                "secret_returned_once": True,
                "workspace_id": producer.WORKSPACE_ID,
            }
        if path == f"/nodes/{NODE_ID}/configurations":
            return {
                "generation": 1,
                "configuration_digest": DIGEST,
                "evidence_status": "complete",
            }
        if path == "/missions":
            self.admission_count += 1
            return {
                "mission_id": MISSION_ID,
                "target_node_id": NODE_ID,
                "mission_template_id": "synthetic_read_review_v1",
                "client_request_id": payload["client_request_id"],
            }
        if path == f"/nodes/{NODE_ID}/revoke":
            if self.revoke_failure == "invalid":
                return {
                    "node_id": NODE_ID,
                    "status": "not-revoked",
                    "evidence_status": "incomplete",
                }
            if self.revoke_failure == "interrupted":
                raise producer.ProducerSignal("synthetic")
            return {
                "node_id": NODE_ID,
                "status": "revoked",
                "evidence_status": "complete",
            }
        raise AssertionError(path)


class FakeApiFactory:
    def __init__(self, api: FakeApi) -> None:
        self.api = api
        self.tokens: list[str] = []

    def create(self, admin_token: str) -> producer.Api:
        self.tokens.append(admin_token)
        return self.api


class FakeAssembler:
    def __init__(self) -> None:
        self.calls = 0
        self.build: JsonObject | None = None
        self.journey: JsonObject | None = None
        self.failure: producer.ProducerError | None = None

    def assemble(
        self,
        build: JsonObject,
        observed: JsonObject,
        *,
        candidate_commit: str,
        candidate_tree: str,
        receipt_root: producer.PrivateDirectory,
        snapshot: producer.CandidateSnapshot,
    ) -> Path:
        del receipt_root, snapshot
        self.calls += 1
        if self.failure is not None:
            raise self.failure
        self.build = build
        self.journey = observed
        report = journey.build_report(
            build,
            observed,
            expected_candidate=candidate_commit,
            expected_tree=candidate_tree,
            run_id="20260724T180000Z-1234abcd",
        )
        journey.validate_report(report, expected_candidate=candidate_commit)
        return Path("/synthetic/report")


def _event(index: int, tool: str) -> JsonObject:
    return {
        "event_id": "evt_" + str(index) * 32,
        "event_hash": "sha256:" + str(index + 1) * 64,
        "event_type": "tool.execution.completed",
        "request_id": "req_" + str(index) * 32,
        "tool_name": tool,
        "metadata": {
            "run_id": RUN_RECORD_ID,
            "mission_id": MISSION_ID,
            "mission_claim_id": CLAIM_ID,
            "mission_envelope_digest": ENVELOPE,
        },
    }


@pytest.fixture
def fake_stack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[
    FakeRuntimeFactory,
    FakeExecutorFactory,
    FakeApiFactory,
    FakeProvider,
    FakeAssembler,
]:
    runtime = FakeRuntimeFactory(tmp_path)
    executor = FakeExecutor(runtime.runtime)
    api = FakeApi()
    monkeypatch.setattr(producer, "_require_ports_available", lambda ports: None)
    monkeypatch.setattr(producer, "RUNTIME_BASE", runtime.runtime.path.parent)
    monkeypatch.setattr(producer, "RECEIPT_BASE", runtime.receipts.path.parent)
    monkeypatch.setattr(
        producer, "_prove_local_docker_socket", lambda candidates=None: "unix:///synthetic"
    )
    monkeypatch.setattr(
        producer,
        "_create_candidate_snapshot",
        lambda root, commit, tree: cast(
            producer.CandidateSnapshot,
            FakeCandidateSnapshot(cast(FakePrivateDirectory, root)),
        ),
    )
    monkeypatch.setattr(
        producer,
        "_license_source_inventory",
        lambda state: {
            "schema_version": "1",
            "inventory_kind": "tracked_git_license_source_inventory",
            "candidate_commit": state.candidate_commit,
            "source": "private_exact_candidate_snapshot_no_follow_size_limited",
            "files": [],
            "license_family_files": [],
            "complete_sbom_claimed": False,
            "license_completeness_claimed": False,
            "compliance_claimed": False,
        },
    )
    monkeypatch.setattr(producer, "_single_image_platform", lambda state: "linux/arm64")
    monkeypatch.setattr(producer, "_observe_exact_source", lambda state: None)
    monkeypatch.setattr(producer.secrets, "token_hex", lambda size: "1234abcd")
    return (
        runtime,
        FakeExecutorFactory(executor),
        FakeApiFactory(api),
        FakeProvider(),
        FakeAssembler(),
    )


def test_gate_refusal_makes_zero_runtime_executor_api_provider_or_assembler_calls(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
) -> None:
    runtime, executors, apis, provider, assembler = fake_stack
    gate = AllowGate(allow=False)

    with pytest.raises(producer.ProducerError, match="gate_refused"):
        producer.run_producer(
            gate=gate,
            runtime_factory=runtime,
            executor_factory=executors,
            api_factory=apis,
            provider=provider,
            assembler=assembler,
            candidate=(COMMIT, TREE),
            environment={},
            now=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
        )

    assert runtime.calls == 0
    assert executors.environments == []
    assert apis.tokens == []
    assert provider.calls == 0
    assert assembler.calls == 0


def test_fake_full_journey_is_one_admission_one_devnull_hermes_attempt_and_closed_evidence(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, executors, apis, provider, assembler = fake_stack
    observed: list[producer.ProducerState] = []
    original_cleanup = producer._cleanup_once  # noqa: SLF001

    def capture_cleanup(
        state: producer.ProducerState,
        executor: producer.Executor | None,
        api: producer.Api | None,
    ) -> JsonObject | None:
        observed.append(state)
        return original_cleanup(state, executor, api)

    monkeypatch.setattr(producer, "_cleanup_once", capture_cleanup)
    result = producer.run_producer(
        gate=AllowGate(),
        runtime_factory=runtime,
        executor_factory=executors,
        api_factory=apis,
        provider=provider,
        assembler=assembler,
        candidate=(COMMIT, TREE),
        environment={"PATH": "/usr/bin"},
        now=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
    )

    executor = executors.executor
    assert result == Path("/synthetic/report")
    assert len(executor.hermes_commands) == 1
    assert executor.hermes_timeouts == [producer.HERMES_TIMEOUT_SECONDS]
    assert apis.api.admission_count == 1
    assert assembler.calls == 1
    assert assembler.build is not None
    assert "sbom_digest" not in assembler.build
    assert "license_receipt_digest" not in assembler.build
    assert assembler.journey is not None
    assert assembler.journey["gateway_lifecycle_state"] == "runner_reported_succeeded"
    runs = assembler.journey["gateway_agent_runs"]
    assert isinstance(runs, list)
    assert runs[0]["status"] == "active"
    assert runtime.runtime.removed is True
    enroll_inputs = [
        value
        for command, value in zip(executor.commands, executor.inputs, strict=True)
        if "enroll" in command
    ]
    assert enroll_inputs == ["one-time-enrollment\n"]
    assert len(observed) == 1
    state = observed[0]
    assert state.enrollment_attempted is True
    assert state.enrollment_outcome_ambiguous is False
    assert state.node_enrolled is True
    assert state.enrollment_revocation_confirmed is True
    assert state.revocation_recovery_receipt_written is False
    assert state.cleanup_failures == []
    assert producer.REVOCATION_RECOVERY_RECEIPT not in runtime.receipts.files
    assert "diagnostic.json" not in runtime.receipts.files


@pytest.mark.parametrize("failure", ["nonzero", "timeout", "malformed"])
def test_ambiguous_enrollment_retains_recovery_material_without_false_revocation(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    runtime, executors, apis, provider, assembler = fake_stack
    executors.executor.enrollment_failure = failure
    observed: list[producer.ProducerState] = []
    original_cleanup = producer._cleanup_once  # noqa: SLF001

    def capture_cleanup(
        state: producer.ProducerState,
        executor: producer.Executor | None,
        api: producer.Api | None,
    ) -> JsonObject | None:
        observed.append(state)
        return original_cleanup(state, executor, api)

    monkeypatch.setattr(producer, "_cleanup_once", capture_cleanup)

    with pytest.raises(producer.ProducerError, match="recovery_required"):
        producer.run_producer(
            gate=AllowGate(),
            runtime_factory=runtime,
            executor_factory=executors,
            api_factory=apis,
            provider=provider,
            assembler=assembler,
            candidate=(COMMIT, TREE),
            environment={},
            now=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
        )

    assert len(observed) == 1
    state = observed[0]
    assert state.enrollment_attempted is True
    assert state.enrollment_outcome_ambiguous is True
    assert state.node_enrolled is False
    assert state.node_id is None
    assert state.enrollment_revocation_confirmed is False
    assert state.cleanup_failures == ["enrollment_outcome_ambiguous"]
    assert state.recovery_required is True
    enrollment_index = next(
        index
        for index, command in enumerate(executors.executor.commands)
        if "enroll" in command
    )
    assert executors.executor.commands[enrollment_index + 1 :] == []
    assert not any(
        method == "POST" and path.endswith("/revoke")
        for method, path, _ in apis.api.calls
    )
    assert runtime.runtime.removed is False
    assert runtime.runtime.closed is True
    assert runtime.receipts.closed is True
    assert "compose.env" in runtime.runtime.files
    assert "var/keys/node-configuration-ed25519-private.pem" in runtime.runtime.files
    assert assembler.calls == 0


@pytest.mark.parametrize(
    ("case", "stdout"),
    [
        (
            "extra",
            canonical_json(
                {**VALID_ENROLLMENT_PROJECTION, "unexpected": "value"}
            )
            + "\n",
        ),
        (
            "missing",
            canonical_json(
                {
                    "node_id": NODE_ID,
                    "principal_id": f"agent:node.{NODE_ID}",
                }
            )
            + "\n",
        ),
        (
            "duplicate",
            (
                f'{{"node_id":"{NODE_ID}","node_id":"{NODE_ID}",'
                f'"principal_id":"agent:node.{NODE_ID}",'
                f'"workspace_id":"{producer.WORKSPACE_ID}"}}\n'
            ),
        ),
        ("malformed", "{"),
        ("trailing", VALID_ENROLLMENT_STDOUT + "{}\n"),
        (
            "noncanonical",
            json.dumps(VALID_ENROLLMENT_PROJECTION, sort_keys=True) + "\n",
        ),
        ("missing_newline", VALID_ENROLLMENT_STDOUT.removesuffix("\n")),
        ("extra_newline", VALID_ENROLLMENT_STDOUT + "\n"),
        (
            "carriage_return_newline",
            VALID_ENROLLMENT_STDOUT.removesuffix("\n") + "\r\n",
        ),
        (
            "node_type",
            canonical_json(
                {**VALID_ENROLLMENT_PROJECTION, "node_id": True}
            )
            + "\n",
        ),
        (
            "principal_type",
            canonical_json(
                {**VALID_ENROLLMENT_PROJECTION, "principal_id": None}
            )
            + "\n",
        ),
        (
            "workspace_type",
            canonical_json(
                {**VALID_ENROLLMENT_PROJECTION, "workspace_id": 1}
            )
            + "\n",
        ),
        (
            "invalid_node_id",
            canonical_json(
                {
                    **VALID_ENROLLMENT_PROJECTION,
                    "node_id": "node_invalid",
                    "principal_id": "agent:node.node_invalid",
                }
            )
            + "\n",
        ),
        (
            "principal_mismatch",
            canonical_json(
                {
                    **VALID_ENROLLMENT_PROJECTION,
                    "principal_id": "agent:node.node_" + ("2" * 32),
                }
            )
            + "\n",
        ),
        (
            "workspace_mismatch",
            canonical_json(
                {**VALID_ENROLLMENT_PROJECTION, "workspace_id": "other"}
            )
            + "\n",
        ),
        (
            "forbidden_key",
            canonical_json(
                {**VALID_ENROLLMENT_PROJECTION, "token": "redacted"}
            )
            + "\n",
        ),
        (
            "forbidden_value",
            canonical_json(
                {
                    **VALID_ENROLLMENT_PROJECTION,
                    "workspace_id": "secret-workspace",
                }
            )
            + "\n",
        ),
    ],
)
def test_unsafe_enrollment_projection_preserves_ambiguous_recovery_boundary(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    stdout: str,
) -> None:
    del case
    runtime, executors, apis, provider, assembler = fake_stack
    executors.executor.enrollment_stdout = stdout
    observed: list[producer.ProducerState] = []
    original_cleanup = producer._cleanup_once  # noqa: SLF001

    def capture_cleanup(
        state: producer.ProducerState,
        executor: producer.Executor | None,
        api: producer.Api | None,
    ) -> JsonObject | None:
        observed.append(state)
        return original_cleanup(state, executor, api)

    monkeypatch.setattr(producer, "_cleanup_once", capture_cleanup)

    with pytest.raises(producer.ProducerError, match="recovery_required"):
        producer.run_producer(
            gate=AllowGate(),
            runtime_factory=runtime,
            executor_factory=executors,
            api_factory=apis,
            provider=provider,
            assembler=assembler,
            candidate=(COMMIT, TREE),
            environment={},
            now=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
        )

    assert len(observed) == 1
    state = observed[0]
    assert state.enrollment_attempted is True
    assert state.enrollment_outcome_ambiguous is True
    assert state.node_enrolled is False
    assert state.node_id is None
    assert state.enrollment_revocation_confirmed is False
    assert state.cleanup_failures == ["enrollment_outcome_ambiguous"]
    enrollment_index = next(
        index
        for index, command in enumerate(executors.executor.commands)
        if "enroll" in command
    )
    assert executors.executor.commands[enrollment_index + 1 :] == []
    assert not any(
        method == "POST" and path.endswith("/revoke")
        for method, path, _ in apis.api.calls
    )
    assert runtime.runtime.removed is False
    assert runtime.runtime.closed is True
    assert runtime.receipts.closed is True
    assert assembler.calls == 0


@pytest.mark.parametrize("revoke_failure", ["invalid", "interrupted"])
def test_full_journey_unconfirmed_revocation_quarantines_recovery_identity(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
    revoke_failure: str,
) -> None:
    runtime, executors, apis, provider, assembler = fake_stack
    apis.api.revoke_failure = revoke_failure

    with pytest.raises(producer.ProducerError, match="recovery_required"):
        producer.run_producer(
            gate=AllowGate(),
            runtime_factory=runtime,
            executor_factory=executors,
            api_factory=apis,
            provider=provider,
            assembler=assembler,
            candidate=(COMMIT, TREE),
            environment={},
            now=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
        )

    assert runtime.runtime.removed is False
    assert runtime.runtime.closed is True
    assert runtime.receipts.closed is True
    assert "compose.env" in runtime.runtime.files
    assert producer.REVOCATION_RECOVERY_RECEIPT in runtime.receipts.files
    recovery = json.loads(
        runtime.receipts.files[producer.REVOCATION_RECOVERY_RECEIPT]
    )
    assert recovery["node_id"] == NODE_ID
    assert recovery["revocation_confirmed"] is False
    assert recovery["node_volume_retained"] is True
    assert recovery["anchored_runtime_retained"] is True
    disposition = json.loads(runtime.receipts.files["disposition.json"])
    assert disposition == {
        "status": "quarantined_not_published",
        "failure_code": "recovery_required",
        "release_allowed": False,
        "uat_complete": False,
    }
    assert assembler.calls == 0
    assert not any("down" in command for command in executors.executor.commands)
    assert not any(
        command[3:5] == ("image", "rm")
        for command in executors.executor.commands
        if len(command) >= 5
    )
    assert executors.executor.commands[-1] == producer.ComposePlan(
        "20260724T180000Z-1234abcd",
        runtime.runtime.path,
    ).compose(
        "--profile",
        "node",
        "stop",
        "ithildin-node",
        fixed=True,
    )


def test_base_start_failure_collects_one_closed_diagnostic_and_preserves_primary(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
) -> None:
    runtime, executors, apis, provider, assembler = fake_stack
    executors.executor.base_start_returncode = 1
    plan = producer.ComposePlan(
        "20260724T180000Z-1234abcd",
        runtime.runtime.path,
    )

    with pytest.raises(
        producer.ProducerError,
        match="base_services_start_failed",
    ):
        producer.run_producer(
            gate=AllowGate(),
            runtime_factory=runtime,
            executor_factory=executors,
            api_factory=apis,
            provider=provider,
            assembler=assembler,
            candidate=(COMMIT, TREE),
            environment={},
            now=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
        )

    diagnostic = json.loads(runtime.receipts.files["diagnostic.json"])
    assert diagnostic["outward_failure_code"] == "base_services_start_failed"
    assert diagnostic["primary_failure_code"] == "base_services_start_failed"
    assert diagnostic["base_service_start_diagnostic"] == {
        "collection_status": "complete",
        "reason_code": "base_service_start_state_collected",
        "services": {
            "ithildin-api": "service_running_starting",
            "ithildin-ui": "service_exited_nonzero",
        },
    }
    assert (
        executors.executor.commands.count(
            plan.base_service_start_diagnostic()
        )
        == 1
    )
    diagnostic_index = executors.executor.commands.index(
        plan.base_service_start_diagnostic()
    )
    assert executors.executor.timeouts[diagnostic_index] == 30.0
    assert apis.api.calls == []
    assert sum(
        "down" in command for command in executors.executor.commands
    ) == 1


@pytest.mark.parametrize(
    ("case", "expected_status", "expected_reason", "expected_ui"),
    [
        (
            "malformed",
            "output_rejected",
            "base_service_start_diagnostic_output_rejected",
            "service_unobserved",
        ),
        (
            "secret",
            "output_rejected",
            "base_service_start_diagnostic_output_rejected",
            "service_unobserved",
        ),
        (
            "duplicate",
            "output_rejected",
            "base_service_start_diagnostic_output_rejected",
            "service_unobserved",
        ),
        (
            "oversize",
            "output_rejected",
            "base_service_start_diagnostic_output_rejected",
            "service_unobserved",
        ),
        (
            "control",
            "output_rejected",
            "base_service_start_diagnostic_output_rejected",
            "service_unobserved",
        ),
        (
            "missing",
            "complete",
            "base_service_start_state_collected",
            "service_missing",
        ),
        (
            "error",
            "inconclusive",
            "base_service_start_diagnostic_command_failed",
            "service_unobserved",
        ),
        (
            "interruption",
            "inconclusive",
            "base_service_start_diagnostic_command_failed",
            "service_unobserved",
        ),
    ],
)
def test_base_start_diagnostic_hostile_or_incomplete_input_is_closed(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
    case: str,
    expected_status: str,
    expected_reason: str,
    expected_ui: str,
) -> None:
    runtime, executors, apis, provider, assembler = fake_stack
    executors.executor.base_start_returncode = 1
    if case == "malformed":
        executors.executor.base_diagnostic_result = producer.CommandResult(
            0,
            "not-tabular\n",
        )
    elif case == "secret":
        executors.executor.base_diagnostic_result = producer.CommandResult(
            0,
            "ithildin-api\trunning\thealthy\t0\nBearer token-value\n",
        )
    elif case == "duplicate":
        executors.executor.base_diagnostic_result = producer.CommandResult(
            0,
            (
                "ithildin-api\trunning\thealthy\t0\n"
                "ithildin-api\texited\t\t1\n"
            ),
        )
    elif case == "oversize":
        executors.executor.base_diagnostic_result = producer.CommandResult(
            0,
            "x" * (producer.MAX_BASE_SERVICE_START_DIAGNOSTIC_BYTES + 1),
        )
    elif case == "control":
        executors.executor.base_diagnostic_result = producer.CommandResult(
            0,
            "ithildin-api\trunning\thealthy\t0\r\n",
        )
    elif case == "missing":
        executors.executor.base_diagnostic_result = producer.CommandResult(
            0,
            "ithildin-api\trunning\thealthy\t0\n",
        )
    elif case == "error":
        executors.executor.base_diagnostic_result = producer.CommandResult(
            2,
            "",
            "completed",
            "compose unavailable\n",
        )
    else:
        executors.executor.base_diagnostic_failure = "interruption"

    with pytest.raises(
        producer.ProducerError,
        match="base_services_start_failed",
    ):
        producer.run_producer(
            gate=AllowGate(),
            runtime_factory=runtime,
            executor_factory=executors,
            api_factory=apis,
            provider=provider,
            assembler=assembler,
            candidate=(COMMIT, TREE),
            environment={},
            now=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
        )

    encoded = runtime.receipts.files["diagnostic.json"].decode()
    diagnostic = json.loads(encoded)
    nested = diagnostic["base_service_start_diagnostic"]
    assert diagnostic["outward_failure_code"] == "base_services_start_failed"
    assert diagnostic["primary_failure_code"] == "base_services_start_failed"
    assert nested["collection_status"] == expected_status
    assert nested["reason_code"] == expected_reason
    assert nested["services"]["ithildin-ui"] == expected_ui
    assert "token-value" not in encoded
    assert apis.api.calls == []
    plan = producer.ComposePlan(
        "20260724T180000Z-1234abcd",
        runtime.runtime.path,
    )
    assert (
        executors.executor.commands.count(
            plan.base_service_start_diagnostic()
        )
        == 1
    )
    assert sum(
        "down" in command for command in executors.executor.commands
    ) == 1


def test_base_start_diagnostic_command_is_exactly_allowlisted() -> None:
    plan = producer.ComposePlan(
        "20260724T180000Z-1234abcd",
        producer.RUNTIME_BASE / "20260724T180000Z-1234abcd",
    )
    command = plan.base_service_start_diagnostic()
    producer._validate_command(command, hermes=False)  # noqa: SLF001
    mutations = (
        (*command, "unexpected-service"),
        tuple(value for value in command if value != "--all"),
        tuple(
            "changed-format"
            if value == producer.BASE_SERVICE_START_DIAGNOSTIC_FORMAT
            else value
            for value in command
        ),
    )
    for mutation in mutations:
        with pytest.raises(
            producer.ProducerError,
            match="subprocess_command_not_allowed",
        ):
            producer._validate_command(  # noqa: SLF001
                mutation,
                hermes=False,
            )


def _enable_api_exited_diagnostic(executor: FakeExecutor) -> None:
    executor.base_start_returncode = 1
    executor.base_diagnostic_result = producer.CommandResult(
        0,
        (
            "ithildin-api\texited\t\t1\n"
            "ithildin-ui\trunning\t\t0\n"
        ),
    )


def _startup_stage_record(stage: str) -> bytes:
    return (
        producer.canonical_json(
            {
                "record_type": "ithildin_api_closed_startup_stage",
                "schema_version": "1",
                "stage": stage,
            }
        )
        + "\n"
    ).encode()


def test_api_container_state_diagnostic_is_exact_closed_and_id_free(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
) -> None:
    runtime, executors, apis, provider, assembler = fake_stack
    executor = executors.executor
    _enable_api_exited_diagnostic(executor)
    plan = producer.ComposePlan(
        "20260724T180000Z-1234abcd",
        runtime.runtime.path,
    )

    with pytest.raises(
        producer.ProducerError,
        match="base_services_start_failed",
    ):
        producer.run_producer(
            gate=AllowGate(),
            runtime_factory=runtime,
            executor_factory=executors,
            api_factory=apis,
            provider=provider,
            assembler=assembler,
            candidate=(COMMIT, TREE),
            environment={},
            now=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
        )

    encoded = runtime.receipts.files["diagnostic.json"].decode()
    diagnostic = json.loads(encoded)
    nested = diagnostic["base_service_start_diagnostic"][
        "api_container_state_diagnostic"
    ]
    assert nested == {
        "collection_status": "complete",
        "collection_reason_code": "api_container_state_collected",
        "cause_code": "api_application_exit_nonzero_no_engine_error",
        "health_status": "absent",
    }
    assert diagnostic["base_service_start_diagnostic"][
        "application_startup_stage_diagnostic"
    ] == {
        "collection_status": "inconclusive",
        "collection_reason_code": "application_startup_stage_missing",
        "last_emitted_stage": "unknown",
    }
    assert executor.api_container_id not in encoded
    sequence = [
        plan.compose(
            "up",
            "--detach",
            "--wait",
            "ithildin-api",
            "ithildin-ui",
        ),
        plan.base_service_start_diagnostic(),
        plan.api_container_id_query(),
        plan.api_container_state_inspect(executor.api_container_id),
    ]
    indexes = [executor.commands.index(command) for command in sequence]
    assert indexes == sorted(indexes)
    assert all(executor.commands.count(command) == 1 for command in sequence)
    assert executor.timeouts[indexes[2:][0]] == 10.0
    assert executor.timeouts[indexes[3:][0]] == 10.0
    assert sum(
        "down" in command for command in executor.commands
    ) == 1
    assert diagnostic["primary_failure_code"] == "base_services_start_failed"
    assert diagnostic["outward_failure_code"] == "base_services_start_failed"


def test_application_startup_stage_is_normalized_only_for_exact_trigger(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
) -> None:
    runtime, executors, apis, provider, assembler = fake_stack
    executor = executors.executor
    _enable_api_exited_diagnostic(executor)
    runtime.runtime.write(
        "startup-status/api-startup-stage.json",
        _startup_stage_record("lifespan_governance_entered"),
    )

    with pytest.raises(
        producer.ProducerError,
        match="base_services_start_failed",
    ):
        producer.run_producer(
            gate=AllowGate(),
            runtime_factory=runtime,
            executor_factory=executors,
            api_factory=apis,
            provider=provider,
            assembler=assembler,
            candidate=(COMMIT, TREE),
            environment={},
            now=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
        )

    encoded = runtime.receipts.files["diagnostic.json"].decode()
    diagnostic = json.loads(encoded)
    assert diagnostic["base_service_start_diagnostic"][
        "application_startup_stage_diagnostic"
    ] == {
        "collection_status": "complete",
        "collection_reason_code": "application_startup_stage_collected",
        "last_emitted_stage": "lifespan_governance_entered",
    }
    assert "ithildin_api_closed_startup_stage" not in encoded
    assert "api-startup-stage.json" not in encoded
    assert diagnostic["primary_failure_code"] == "base_services_start_failed"
    assert diagnostic["outward_failure_code"] == "base_services_start_failed"
    assert sum("down" in command for command in executor.commands) == 1


@pytest.mark.parametrize(
    ("case", "expected_status"),
    [
        ("missing", "inconclusive"),
        ("malformed", "output_rejected"),
        ("duplicate", "output_rejected"),
        ("extra_key", "output_rejected"),
        ("oversize", "output_rejected"),
        ("utf8", "output_rejected"),
        ("enum", "output_rejected"),
        ("noncanonical", "output_rejected"),
        ("extra_file", "output_rejected"),
        ("temp_file", "output_rejected"),
        ("mode", "output_rejected"),
    ],
)
def test_application_startup_stage_parser_is_closed(
    tmp_path: Path,
    case: str,
    expected_status: str,
) -> None:
    run_id = "20260724T180000Z-1234abcd"
    runtime = FakePrivateDirectory(tmp_path / "runtime" / run_id)
    receipts = FakePrivateDirectory(tmp_path / "receipts" / run_id)
    state = producer.ProducerState(
        COMMIT,
        TREE,
        run_id,
        producer.ComposePlan(run_id, runtime.path),
        cast(producer.PrivateDirectory, runtime),
        cast(producer.PrivateDirectory, receipts),
    )
    relative = "startup-status/api-startup-stage.json"
    if case != "missing":
        content = _startup_stage_record("application_import_entered")
        if case == "malformed":
            content = b"{\n"
        elif case == "duplicate":
            content = (
                b'{"record_type":"ithildin_api_closed_startup_stage",'
                b'"schema_version":"1","stage":"application_import_entered",'
                b'"stage":"startup_ready"}\n'
            )
        elif case == "extra_key":
            content = content[:-2] + b',"extra":false}\n'
        elif case == "oversize":
            content = b"x" * (
                producer.MAX_APPLICATION_STARTUP_STAGE_BYTES + 1
            )
        elif case == "utf8":
            content = b"\xff"
        elif case == "enum":
            content = _startup_stage_record("not_a_stage")
        elif case == "noncanonical":
            content = json.dumps(
                {
                    "record_type": "ithildin_api_closed_startup_stage",
                    "schema_version": "1",
                    "stage": "application_import_entered",
                }
            ).encode()
        runtime.write(relative, content)
        if case == "extra_file":
            runtime.write("startup-status/extra", b"")
        elif case == "temp_file":
            runtime.write("startup-status/.api-startup-stage.tmp", b"")
        elif case == "mode":
            runtime.file_modes[relative] = 0o644

    result = producer._collect_application_startup_stage_diagnostic(  # noqa: SLF001
        state
    )

    assert result["collection_status"] == expected_status
    assert result["collection_reason_code"] == (
        "application_startup_stage_missing"
        if case == "missing"
        else "application_startup_stage_unsafe_or_incomplete"
    )
    assert result["last_emitted_stage"] == "unknown"


@pytest.mark.parametrize(
    ("case", "status", "reason"),
    [
        ("missing", "inconclusive", "api_container_id_missing"),
        (
            "lone_lf",
            "output_rejected",
            "api_container_state_output_rejected",
        ),
        (
            "multiple",
            "output_rejected",
            "api_container_id_ambiguous",
        ),
        (
            "short",
            "output_rejected",
            "api_container_state_output_rejected",
        ),
        (
            "extra_lf",
            "output_rejected",
            "api_container_state_output_rejected",
        ),
        (
            "crlf",
            "output_rejected",
            "api_container_state_output_rejected",
        ),
        (
            "stderr",
            "inconclusive",
            "api_container_state_command_failed",
        ),
        ("rc", "inconclusive", "api_container_state_command_failed"),
        ("timeout", "inconclusive", "api_container_state_command_failed"),
        (
            "oversize",
            "output_rejected",
            "api_container_state_output_rejected",
        ),
        (
            "nonascii",
            "output_rejected",
            "api_container_state_output_rejected",
        ),
        (
            "control",
            "output_rejected",
            "api_container_state_output_rejected",
        ),
        (
            "secret",
            "output_rejected",
            "api_container_state_output_rejected",
        ),
    ],
)
def test_api_container_id_query_hostile_results_are_closed(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
    case: str,
    status: str,
    reason: str,
) -> None:
    runtime, executors, apis, provider, assembler = fake_stack
    executor = executors.executor
    _enable_api_exited_diagnostic(executor)
    other = "b" * 64
    if case == "missing":
        executor.api_container_query_result = producer.CommandResult(0, "")
    elif case == "lone_lf":
        executor.api_container_query_result = producer.CommandResult(0, "\n")
    elif case == "multiple":
        executor.api_container_query_result = producer.CommandResult(
            0,
            executor.api_container_id + "\n" + other + "\n",
        )
    elif case == "short":
        executor.api_container_query_result = producer.CommandResult(
            0,
            "a" * 63,
        )
    elif case == "extra_lf":
        executor.api_container_query_result = producer.CommandResult(
            0,
            executor.api_container_id + "\n\n",
        )
    elif case == "crlf":
        executor.api_container_query_result = producer.CommandResult(
            0,
            executor.api_container_id + "\r\n",
        )
    elif case == "stderr":
        executor.api_container_query_result = producer.CommandResult(
            0,
            executor.api_container_id,
            "completed",
            "safe error\n",
        )
    elif case == "rc":
        executor.api_container_query_result = producer.CommandResult(2, "")
    elif case == "timeout":
        executor.api_container_query_failure = "timeout"
    elif case == "oversize":
        executor.api_container_query_result = producer.CommandResult(
            0,
            "x" * (producer.MAX_API_CONTAINER_DIAGNOSTIC_BYTES + 1),
        )
    elif case == "nonascii":
        executor.api_container_query_result = producer.CommandResult(0, "é")
    elif case == "control":
        executor.api_container_query_result = producer.CommandResult(0, "\x00")
    else:
        executor.api_container_query_result = producer.CommandResult(
            0,
            "Bearer token-value",
        )

    with pytest.raises(
        producer.ProducerError,
        match="base_services_start_failed",
    ):
        producer.run_producer(
            gate=AllowGate(),
            runtime_factory=runtime,
            executor_factory=executors,
            api_factory=apis,
            provider=provider,
            assembler=assembler,
            candidate=(COMMIT, TREE),
            environment={},
            now=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
        )

    encoded = runtime.receipts.files["diagnostic.json"].decode()
    base_diagnostic = json.loads(encoded)["base_service_start_diagnostic"]
    nested = base_diagnostic[
        "api_container_state_diagnostic"
    ]
    assert nested["collection_status"] == status
    assert nested["collection_reason_code"] == reason
    assert nested["cause_code"] == "api_exit_cause_inconclusive"
    assert nested["health_status"] == "absent"
    assert executor.bound_container_ids == set()
    assert not any(
        command[3:5] == ("container", "inspect")
        for command in executor.commands
        if len(command) >= 5
    )
    assert "token-value" not in encoded


@pytest.mark.parametrize(
    ("case", "status", "reason", "cause", "health"),
    [
        (
            "oom",
            "complete",
            "api_container_state_collected",
            "api_exit_oom_killed",
            "unhealthy",
        ),
        (
            "runtime_error",
            "complete",
            "api_container_state_collected",
            "api_container_runtime_error_present",
            "absent",
        ),
        (
            "zero_exit",
            "complete",
            "api_container_state_collected",
            "api_unexpected_zero_exit",
            "absent",
        ),
        (
            "zero_exit_oom",
            "complete",
            "api_container_state_collected",
            "api_state_inconsistent",
            "absent",
        ),
        (
            "zero_exit_runtime_error",
            "complete",
            "api_container_state_collected",
            "api_state_inconsistent",
            "absent",
        ),
        (
            "inconsistent",
            "complete",
            "api_container_state_collected",
            "api_state_inconsistent",
            "healthy",
        ),
        (
            "wrong_label",
            "output_rejected",
            "api_container_state_output_rejected",
            "api_exit_cause_inconclusive",
            "absent",
        ),
        (
            "unknown_enum",
            "output_rejected",
            "api_container_state_output_rejected",
            "api_exit_cause_inconclusive",
            "absent",
        ),
        (
            "stderr",
            "inconclusive",
            "api_container_state_command_failed",
            "api_exit_cause_inconclusive",
            "absent",
        ),
        (
            "timeout",
            "inconclusive",
            "api_container_state_command_failed",
            "api_exit_cause_inconclusive",
            "absent",
        ),
        (
            "oversize",
            "output_rejected",
            "api_container_state_output_rejected",
            "api_exit_cause_inconclusive",
            "absent",
        ),
        (
            "rc",
            "inconclusive",
            "api_container_state_command_failed",
            "api_exit_cause_inconclusive",
            "absent",
        ),
        (
            "nonascii",
            "output_rejected",
            "api_container_state_output_rejected",
            "api_exit_cause_inconclusive",
            "absent",
        ),
        (
            "control",
            "output_rejected",
            "api_container_state_output_rejected",
            "api_exit_cause_inconclusive",
            "absent",
        ),
        (
            "secret",
            "output_rejected",
            "api_container_state_output_rejected",
            "api_exit_cause_inconclusive",
            "absent",
        ),
    ],
)
def test_api_container_state_hostile_and_cause_classification_is_closed(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
    case: str,
    status: str,
    reason: str,
    cause: str,
    health: str,
) -> None:
    runtime, executors, apis, provider, assembler = fake_stack
    executor = executors.executor
    _enable_api_exited_diagnostic(executor)
    plan = producer.ComposePlan(
        "20260724T180000Z-1234abcd",
        runtime.runtime.path,
    )
    fields = [
        executor.api_container_id,
        plan.project,
        "ithildin-api",
        "exited",
        "false",
        "1",
        "false",
        "false",
        "false",
        "absent",
    ]
    if case == "oom":
        fields[6] = "true"
        fields[9] = "unhealthy"
    elif case == "runtime_error":
        fields[8] = "true"
    elif case == "zero_exit":
        fields[5] = "0"
    elif case == "zero_exit_oom":
        fields[5] = "0"
        fields[6] = "true"
    elif case == "zero_exit_runtime_error":
        fields[5] = "0"
        fields[8] = "true"
    elif case == "inconsistent":
        fields[3] = "running"
        fields[4] = "true"
        fields[9] = "healthy"
    elif case == "wrong_label":
        fields[1] = "other-project"
    elif case == "unknown_enum":
        fields[3] = "unknown"
    elif case == "stderr":
        executor.api_container_inspect_result = producer.CommandResult(
            0,
            "\t".join(fields),
            "completed",
            "safe error\n",
        )
    elif case == "timeout":
        executor.api_container_inspect_failure = "timeout"
    elif case == "oversize":
        executor.api_container_inspect_result = producer.CommandResult(
            0,
            "x" * (producer.MAX_API_CONTAINER_DIAGNOSTIC_BYTES + 1),
        )
    elif case == "rc":
        executor.api_container_inspect_result = producer.CommandResult(2, "")
    elif case == "nonascii":
        executor.api_container_inspect_result = producer.CommandResult(0, "é")
    elif case == "control":
        executor.api_container_inspect_result = producer.CommandResult(
            0,
            "\x00",
        )
    elif case == "secret":
        executor.api_container_inspect_result = producer.CommandResult(
            0,
            "Bearer token-value",
        )
    if (
        executor.api_container_inspect_result is None
        and executor.api_container_inspect_failure is None
    ):
        executor.api_container_inspect_result = producer.CommandResult(
            0,
            "\t".join(fields) + "\n",
        )

    with pytest.raises(
        producer.ProducerError,
        match="base_services_start_failed",
    ):
        producer.run_producer(
            gate=AllowGate(),
            runtime_factory=runtime,
            executor_factory=executors,
            api_factory=apis,
            provider=provider,
            assembler=assembler,
            candidate=(COMMIT, TREE),
            environment={},
            now=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
        )

    encoded = runtime.receipts.files["diagnostic.json"].decode()
    base_diagnostic = json.loads(encoded)["base_service_start_diagnostic"]
    nested = base_diagnostic[
        "api_container_state_diagnostic"
    ]
    assert nested == {
        "collection_status": status,
        "collection_reason_code": reason,
        "cause_code": cause,
        "health_status": health,
    }
    assert "application_startup_stage_diagnostic" not in base_diagnostic
    assert executor.api_container_id not in encoded
    assert "token-value" not in encoded
    assert sum(
        "down" in command for command in executor.commands
    ) == 1


def test_api_container_commands_require_exact_binding_and_scalar_template() -> None:
    plan = producer.ComposePlan(
        "20260724T180000Z-1234abcd",
        producer.RUNTIME_BASE / "20260724T180000Z-1234abcd",
    )
    container_id = "a" * 64
    producer._validate_command(  # noqa: SLF001
        plan.api_container_id_query(),
        hermes=False,
    )
    with pytest.raises(
        producer.ProducerError,
        match="subprocess_command_not_allowed",
    ):
        producer._validate_command(  # noqa: SLF001
            plan.api_container_state_inspect(container_id),
            hermes=False,
        )
    producer._validate_command(  # noqa: SLF001
        plan.api_container_state_inspect(container_id),
        hermes=False,
        bound_container_ids=frozenset({container_id}),
    )
    template = producer.API_CONTAINER_STATE_FORMAT
    assert '{{ne .State.Error ""}}' in template
    assert "{{.State.Error}}" not in template
    assert "Health.Log" not in template
    assert "{{json" not in template
    assert ".Config.Env" not in template
    assert ".Mounts" not in template
    for mutation in (
        (*plan.api_container_id_query(), "ithildin-ui"),
        (
            *plan.api_container_state_inspect(container_id)[:-2],
            "{{json .State}}",
            container_id,
        ),
    ):
        with pytest.raises(
            producer.ProducerError,
            match="subprocess_command_not_allowed",
        ):
            producer._validate_command(  # noqa: SLF001
                mutation,
                hermes=False,
                bound_container_ids=frozenset({container_id}),
            )


@pytest.mark.parametrize(
    ("stdout_bytes", "stderr_bytes", "classification"),
    [
        (256, 256, "completed"),
        (256, 257, "output_rejected"),
    ],
)
def test_api_container_diagnostic_subprocess_enforces_combined_stream_cap(
    stdout_bytes: int,
    stderr_bytes: int,
    classification: str,
) -> None:
    command = (
        sys.executable,
        "-c",
        (
            "import os;"
            f"os.write(1,b'x'*{stdout_bytes});"
            f"os.write(2,b'y'*{stderr_bytes})"
        ),
    )

    result = producer.SubprocessExecutor(
        dict(os.environ)
    )._run_bounded_api_container_diagnostic(  # noqa: SLF001
        command,
        timeout=10.0,
    )

    assert result.classification == classification
    if classification == "completed":
        assert len(result.stdout) + len(result.stderr) == 512
    else:
        assert result.stdout == ""
        assert result.stderr == ""


@pytest.mark.parametrize(
    ("seam", "interruption_type"),
    [
        ("selector", producer.ProducerSignal),
        ("read", KeyboardInterrupt),
        ("wait", producer.ProducerSignal),
    ],
)
def test_api_container_diagnostic_interruption_reaps_before_stream_close(
    monkeypatch: pytest.MonkeyPatch,
    seam: str,
    interruption_type: type[BaseException],
) -> None:
    interruption = interruption_type(f"synthetic_{seam}")

    class FakePipe:
        def __init__(self, owner: FakeProcess, descriptor: int) -> None:
            self.owner = owner
            self.descriptor = descriptor
            self.closed = False
            self.closed_after_reap = False

        def close(self) -> None:
            self.closed = True
            self.closed_after_reap = self.owner.reaped

    class FakeProcess:
        def __init__(self) -> None:
            self.killed = False
            self.reaped = False
            self.kill_calls = 0
            self.wait_calls = 0
            self.stdout = FakePipe(self, 1)
            self.stderr = FakePipe(self, 2)

        def poll(self) -> int | None:
            return -9 if self.reaped else None

        def kill(self) -> None:
            self.kill_calls += 1
            self.killed = True

        def wait(self, timeout: float | None = None) -> int:
            del timeout
            self.wait_calls += 1
            if seam == "wait" and self.wait_calls == 1:
                raise interruption
            self.reaped = True
            return -9 if self.killed else 0

    class FakeKey:
        def __init__(self, pipe: FakePipe, data: str) -> None:
            self.fd = pipe.descriptor
            self.fileobj = pipe
            self.data = data

    process = FakeProcess()

    class FakeSelector:
        def __init__(self) -> None:
            self.keys: dict[FakePipe, FakeKey] = {}
            self.closed = False
            self.closed_after_reap = False

        def register(
            self,
            pipe: FakePipe,
            event: int,
            data: str,
        ) -> None:
            del event
            self.keys[pipe] = FakeKey(pipe, data)

        def get_map(self) -> dict[FakePipe, FakeKey]:
            return self.keys

        def select(self, timeout: float) -> list[tuple[FakeKey, int]]:
            del timeout
            if seam == "selector":
                raise interruption
            return [(key, 1) for key in tuple(self.keys.values())]

        def unregister(self, pipe: FakePipe) -> None:
            del self.keys[pipe]

        def close(self) -> None:
            self.closed = True
            self.closed_after_reap = process.reaped

    selector = FakeSelector()

    def fake_popen(
        command: tuple[str, ...],
        **options: object,
    ) -> FakeProcess:
        del command, options
        return process

    def fake_read(descriptor: int, maximum: int) -> bytes:
        del descriptor, maximum
        if seam == "read":
            raise interruption
        return b""

    monkeypatch.setattr(producer.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(
        producer.selectors,
        "DefaultSelector",
        lambda: selector,
    )
    monkeypatch.setattr(producer.os, "read", fake_read)

    with pytest.raises(interruption_type) as caught:
        producer.SubprocessExecutor(
            dict(os.environ)
        )._run_bounded_api_container_diagnostic(  # noqa: SLF001
            ("synthetic",),
            timeout=10.0,
        )

    assert caught.value is interruption
    assert process.kill_calls == 1
    assert process.wait_calls == (2 if seam == "wait" else 1)
    assert process.killed is True
    assert process.reaped is True
    assert selector.closed is True
    assert selector.closed_after_reap is True
    assert process.stdout.closed is True
    assert process.stdout.closed_after_reap is True
    assert process.stderr.closed is True
    assert process.stderr.closed_after_reap is True


def test_api_container_diagnostic_repeated_wait_interrupt_is_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = producer.ProducerSignal("synthetic_selector")
    cleanup_interrupt = producer.ProducerSignal("synthetic_reap")

    class FakePipe:
        def __init__(self, descriptor: int) -> None:
            self.descriptor = descriptor
            self.closed = False

        def close(self) -> None:
            self.closed = True

    class FakeProcess:
        def __init__(self) -> None:
            self.stdout = FakePipe(1)
            self.stderr = FakePipe(2)
            self.kill_calls = 0
            self.wait_calls = 0

        def poll(self) -> None:
            return None

        def kill(self) -> None:
            self.kill_calls += 1

        def wait(self, timeout: float | None = None) -> int:
            assert timeout == producer.API_CONTAINER_REAP_TIMEOUT_SECONDS
            self.wait_calls += 1
            raise cleanup_interrupt

    class FakeKey:
        def __init__(self, pipe: FakePipe, data: str) -> None:
            self.fd = pipe.descriptor
            self.fileobj = pipe
            self.data = data

    process = FakeProcess()

    class FakeSelector:
        def __init__(self) -> None:
            self.keys: dict[FakePipe, FakeKey] = {}
            self.closed = False

        def register(
            self,
            pipe: FakePipe,
            event: int,
            data: str,
        ) -> None:
            del event
            self.keys[pipe] = FakeKey(pipe, data)

        def get_map(self) -> dict[FakePipe, FakeKey]:
            return self.keys

        def select(self, timeout: float) -> list[tuple[FakeKey, int]]:
            del timeout
            raise original

        def close(self) -> None:
            self.closed = True

    selector = FakeSelector()
    monkeypatch.setattr(
        producer.subprocess,
        "Popen",
        lambda *args, **kwargs: process,
    )
    monkeypatch.setattr(
        producer.selectors,
        "DefaultSelector",
        lambda: selector,
    )

    with pytest.raises(producer.ProducerSignal) as caught:
        producer.SubprocessExecutor(
            dict(os.environ)
        )._run_bounded_api_container_diagnostic(  # noqa: SLF001
            ("synthetic",),
            timeout=10.0,
        )

    assert caught.value is original
    assert process.kill_calls == producer.MAX_API_CONTAINER_REAP_ATTEMPTS
    assert process.wait_calls == producer.MAX_API_CONTAINER_REAP_ATTEMPTS
    assert selector.closed is True
    assert process.stdout.closed is True
    assert process.stderr.closed is True


def test_api_container_diagnostic_cleanup_interrupt_is_deferred(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cleanup_interrupt = KeyboardInterrupt("synthetic_cleanup")

    class FakePipe:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    class FakeProcess:
        def __init__(self) -> None:
            self.stdout = FakePipe()
            self.stderr = FakePipe()
            self.poll_calls = 0
            self.wait_calls = 0

        def poll(self) -> int | None:
            self.poll_calls += 1
            if self.poll_calls == 1:
                raise cleanup_interrupt
            return None

        def kill(self) -> None:
            return None

        def wait(self, timeout: float | None = None) -> int:
            self.wait_calls += 1
            if self.wait_calls == 1:
                assert timeout is not None
            else:
                assert timeout == producer.API_CONTAINER_REAP_TIMEOUT_SECONDS
            return 0

    process = FakeProcess()

    class FakeSelector:
        def __init__(self) -> None:
            self.closed = False

        def register(self, *args: object) -> None:
            return None

        def get_map(self) -> dict[object, object]:
            return {}

        def close(self) -> None:
            self.closed = True

    selector = FakeSelector()
    monkeypatch.setattr(
        producer.subprocess,
        "Popen",
        lambda *args, **kwargs: process,
    )
    monkeypatch.setattr(
        producer.selectors,
        "DefaultSelector",
        lambda: selector,
    )

    with pytest.raises(KeyboardInterrupt) as caught:
        producer.SubprocessExecutor(
            dict(os.environ)
        )._run_bounded_api_container_diagnostic(  # noqa: SLF001
            ("synthetic",),
            timeout=10.0,
        )

    assert caught.value is cleanup_interrupt
    assert process.wait_calls == 2
    assert selector.closed is True
    assert process.stdout.closed is True
    assert process.stderr.closed is True


@pytest.mark.parametrize("stage", ["query", "inspect"])
def test_api_container_diagnostic_interruption_is_closed_and_cleanup_once(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
    stage: str,
) -> None:
    runtime, executors, apis, provider, assembler = fake_stack
    executor = executors.executor
    _enable_api_exited_diagnostic(executor)
    if stage == "query":
        executor.api_container_query_failure = "interruption"
    else:
        executor.api_container_inspect_failure = "interruption"

    with pytest.raises(
        producer.ProducerError,
        match="base_services_start_failed",
    ):
        producer.run_producer(
            gate=AllowGate(),
            runtime_factory=runtime,
            executor_factory=executors,
            api_factory=apis,
            provider=provider,
            assembler=assembler,
            candidate=(COMMIT, TREE),
            environment={},
            now=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
        )

    diagnostic = json.loads(runtime.receipts.files["diagnostic.json"])
    nested = diagnostic["base_service_start_diagnostic"][
        "api_container_state_diagnostic"
    ]
    assert nested == {
        "collection_status": "inconclusive",
        "collection_reason_code": "api_container_state_command_failed",
        "cause_code": "api_exit_cause_inconclusive",
        "health_status": "absent",
    }
    assert diagnostic["primary_failure_code"] == "base_services_start_failed"
    assert diagnostic["outward_failure_code"] == "base_services_start_failed"
    assert sum("down" in command for command in executor.commands) == 1


def test_bridge_build_failure_cleans_exact_bound_base_images_and_preserves_primary(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
) -> None:
    runtime, executors, apis, provider, assembler = fake_stack
    executors.executor.build_failure = "bridge"

    with pytest.raises(
        producer.ProducerError,
        match="bridge_image_build_failed",
    ):
        producer.run_producer(
            gate=AllowGate(),
            runtime_factory=runtime,
            executor_factory=executors,
            api_factory=apis,
            provider=provider,
            assembler=assembler,
            candidate=(COMMIT, TREE),
            environment={},
            now=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
        )

    diagnostic = json.loads(runtime.receipts.files["diagnostic.json"])
    assert diagnostic == {
        "schema_version": "1",
        "record_type": "local_v1_lv1_003_o4_producer_failure_diagnostic",
        "outward_failure_code": "bridge_image_build_failed",
        "primary_failure_code": "bridge_image_build_failed",
        "cleanup_failure_codes": [],
        "recovery_required": False,
        "highest_completed_stage": 5,
        "base_build_completed": True,
        "bridge_build_completed": False,
        "bound_inspected_image_identities": [
            {
                "reference": reference,
                "image_id": "sha256:" + str(index) * 64,
                "project": producer.ComposePlan(
                    "20260724T180000Z-1234abcd",
                    runtime.runtime.path,
                ).project,
                "service": service,
                "compose_version": "5.1.4",
                "platform": "linux/arm64",
                "ordered_layer_digests": ["sha256:" + "9" * 64],
            }
            for index, (reference, service) in enumerate(
                zip(
                    producer.ComposePlan(
                        "20260724T180000Z-1234abcd",
                        runtime.runtime.path,
                    ).images[:3],
                    ("ithildin-api", "ithildin-ui", "ithildin-node"),
                    strict=True,
                ),
                start=1,
            )
        ],
    }
    removals = [
        command
        for command in executors.executor.commands
        if len(command) == 6 and command[3:5] == ("image", "rm")
    ]
    assert [command[-1] for command in removals] == [
        "sha256:" + str(index) * 64 for index in range(1, 4)
    ]
    assert not any(
        value in command
        for command in removals
        for value in ("--force", "-f", "prune")
    )
    disposition = json.loads(runtime.receipts.files["disposition.json"])
    assert disposition["failure_code"] == "bridge_image_build_failed"


def test_bridge_failure_cleanup_failure_is_recovery_with_separate_diagnostic(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
) -> None:
    runtime, executors, apis, provider, assembler = fake_stack
    executors.executor.build_failure = "bridge"
    executors.executor.removal_failures.add("sha256:" + "1" * 64)

    with pytest.raises(producer.ProducerError, match="recovery_required"):
        producer.run_producer(
            gate=AllowGate(),
            runtime_factory=runtime,
            executor_factory=executors,
            api_factory=apis,
            provider=provider,
            assembler=assembler,
            candidate=(COMMIT, TREE),
            environment={},
            now=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
        )

    diagnostic = json.loads(runtime.receipts.files["diagnostic.json"])
    assert diagnostic["outward_failure_code"] == "recovery_required"
    assert diagnostic["primary_failure_code"] == "bridge_image_build_failed"
    assert diagnostic["recovery_required"] is True
    assert diagnostic["cleanup_failure_codes"] == [
        "owned_image_removal_failed",
        "owned_image_absence_probe_failed",
        "owned_image_id_residue_detected",
    ]
    assert len(diagnostic["bound_inspected_image_identities"]) == 3
    assert executors.executor.images == {
        producer.ComposePlan(
            "20260724T180000Z-1234abcd",
            runtime.runtime.path,
        ).images[0]: "sha256:" + "1" * 64
    }
    assert sum(
        "down" in command for command in executors.executor.commands
    ) == 1
    disposition = json.loads(runtime.receipts.files["disposition.json"])
    assert disposition["failure_code"] == "recovery_required"


def test_all_run_tags_absent_but_bound_full_id_remains_is_recovery_required(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
) -> None:
    runtime, executors, apis, provider, assembler = fake_stack
    retained = "sha256:" + "1" * 64
    executors.executor.build_failure = "bridge"
    executors.executor.retain_ids_after_removal.add(retained)

    with pytest.raises(producer.ProducerError, match="recovery_required"):
        producer.run_producer(
            gate=AllowGate(),
            runtime_factory=runtime,
            executor_factory=executors,
            api_factory=apis,
            provider=provider,
            assembler=assembler,
            candidate=(COMMIT, TREE),
            environment={},
            now=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
        )

    assert executors.executor.images == {}
    assert executors.executor.remaining_image_ids == {retained}
    diagnostic = json.loads(runtime.receipts.files["diagnostic.json"])
    assert diagnostic["primary_failure_code"] == "bridge_image_build_failed"
    assert diagnostic["outward_failure_code"] == "recovery_required"
    assert diagnostic["cleanup_failure_codes"] == [
        "owned_image_id_residue_detected"
    ]


@pytest.mark.parametrize(
    "probe_mode",
    [
        "error",
        "ambiguous",
        "space",
        "tab",
        "crlf",
        "multiple_newlines",
        "content",
    ],
)
def test_bound_id_absence_probe_nonexact_outcome_fails_closed(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
    probe_mode: str,
) -> None:
    runtime, executors, apis, provider, assembler = fake_stack
    image_id = "sha256:" + "1" * 64
    executors.executor.build_failure = "bridge"
    executors.executor.image_id_probe_modes[image_id] = probe_mode

    with pytest.raises(producer.ProducerError, match="recovery_required"):
        producer.run_producer(
            gate=AllowGate(),
            runtime_factory=runtime,
            executor_factory=executors,
            api_factory=apis,
            provider=provider,
            assembler=assembler,
            candidate=(COMMIT, TREE),
            environment={},
            now=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
        )

    assert executors.executor.images == {}
    assert executors.executor.remaining_image_ids == set()
    diagnostic = json.loads(runtime.receipts.files["diagnostic.json"])
    assert diagnostic["cleanup_failure_codes"] == [
        "owned_image_id_absence_probe_failed"
    ]


def test_bound_id_absence_probe_accepts_one_newline_as_exact_absence(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
) -> None:
    runtime, executors, apis, provider, assembler = fake_stack
    image_id = "sha256:" + "1" * 64
    executors.executor.build_failure = "bridge"
    executors.executor.image_id_probe_modes[image_id] = "single_newline"

    with pytest.raises(
        producer.ProducerError,
        match="bridge_image_build_failed",
    ):
        producer.run_producer(
            gate=AllowGate(),
            runtime_factory=runtime,
            executor_factory=executors,
            api_factory=apis,
            provider=provider,
            assembler=assembler,
            candidate=(COMMIT, TREE),
            environment={},
            now=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
        )

    diagnostic = json.loads(runtime.receipts.files["diagnostic.json"])
    assert diagnostic["cleanup_failure_codes"] == []
    assert diagnostic["outward_failure_code"] == "bridge_image_build_failed"


@pytest.mark.parametrize(
    "drift",
    ["extra_tag", "label", "platform", "container", "reference"],
)
def test_cleanup_metadata_or_reference_drift_refuses_all_image_removal(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
    drift: str,
) -> None:
    runtime, executors, apis, provider, assembler = fake_stack
    executors.executor.build_failure = "bridge"
    executors.executor.cleanup_drift = drift

    with pytest.raises(producer.ProducerError, match="recovery_required"):
        producer.run_producer(
            gate=AllowGate(),
            runtime_factory=runtime,
            executor_factory=executors,
            api_factory=apis,
            provider=provider,
            assembler=assembler,
            candidate=(COMMIT, TREE),
            environment={},
            now=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
        )

    diagnostic = json.loads(runtime.receipts.files["diagnostic.json"])
    assert diagnostic["primary_failure_code"] == "bridge_image_build_failed"
    assert diagnostic["outward_failure_code"] == "recovery_required"
    assert "image_identity_reconciliation_failed" in diagnostic[
        "cleanup_failure_codes"
    ]
    assert not any(
        len(command) == 6 and command[3:5] == ("image", "rm")
        for command in executors.executor.commands
    )


def test_base_build_partial_reference_remains_ambiguous_and_fail_closed(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
) -> None:
    runtime, executors, apis, provider, assembler = fake_stack
    executors.executor.build_failure = "base"
    executors.executor.base_failure_partial_reference = True

    with pytest.raises(producer.ProducerError, match="recovery_required"):
        producer.run_producer(
            gate=AllowGate(),
            runtime_factory=runtime,
            executor_factory=executors,
            api_factory=apis,
            provider=provider,
            assembler=assembler,
            candidate=(COMMIT, TREE),
            environment={},
            now=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
        )

    diagnostic = json.loads(runtime.receipts.files["diagnostic.json"])
    assert diagnostic["primary_failure_code"] == "base_image_build_failed"
    assert diagnostic["outward_failure_code"] == "recovery_required"
    assert diagnostic["bound_inspected_image_identities"] == []
    assert "image_identity_reconciliation_failed" in diagnostic[
        "cleanup_failure_codes"
    ]
    assert not any(
        len(command) == 6 and command[3:5] == ("image", "rm")
        for command in executors.executor.commands
    )


def test_unexpected_failure_diagnostic_is_stable_and_never_reflects_raw_text(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, executors, apis, provider, assembler = fake_stack
    raw = "Bearer secret-value /private/host/path provider-model-output"

    def unexpected(
        state: producer.ProducerState,
        executor: producer.Executor,
    ) -> None:
        del state, executor
        raise RuntimeError(raw)

    monkeypatch.setattr(producer, "_build_images", unexpected)
    with pytest.raises(producer.ProducerError, match="unexpected_failure"):
        producer.run_producer(
            gate=AllowGate(),
            runtime_factory=runtime,
            executor_factory=executors,
            api_factory=apis,
            provider=provider,
            assembler=assembler,
            candidate=(COMMIT, TREE),
            environment={},
            now=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
        )

    encoded = runtime.receipts.files["diagnostic.json"].decode()
    diagnostic = json.loads(encoded)
    assert diagnostic["outward_failure_code"] == "unexpected_failure"
    assert diagnostic["primary_failure_code"] == "unexpected_failure"
    assert raw not in encoded
    assert "secret-value" not in encoded
    assert "/private/host/path" not in encoded
    assert "provider-model-output" not in encoded


def _o4_enrollment_command(plan: producer.ComposePlan) -> tuple[str, ...]:
    return plan.compose(
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
        producer.NODE_VERSION,
        "--runner-adapter",
        "hermes",
        "--deployment-topology",
        "docker_sidecar",
        "--enrollment-code-stdin",
    )


@pytest.mark.parametrize(
    ("line_ending", "accepted"),
    [(b"\n", True), (b"\r\n", False)],
)
def test_subprocess_adapter_preserves_enrollment_line_endings_for_closed_parser(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    line_ending: bytes,
    accepted: bool,
) -> None:
    run_id = "20260724T180000Z-1234abcd"
    runtime = tmp_path / run_id
    monkeypatch.setattr(producer, "RUNTIME_BASE", tmp_path)
    plan = producer.ComposePlan(run_id, runtime)
    command = _o4_enrollment_command(plan)
    raw_stdout = canonical_json(VALID_ENROLLMENT_PROJECTION).encode() + line_ending
    observed: dict[str, object] = {}

    def fake_run(
        invoked: tuple[str, ...],
        **options: object,
    ) -> subprocess.CompletedProcess[bytes]:
        observed.update(options)
        return subprocess.CompletedProcess(invoked, 0, raw_stdout, b"")

    monkeypatch.setattr(producer.subprocess, "run", fake_run)
    result = producer.SubprocessExecutor({}).run(
        command,
        input_text="one-time-enrollment\n",
    )

    assert observed["input"] == b"one-time-enrollment\n"
    assert "text" not in observed
    assert result.stdout.encode() == raw_stdout
    if accepted:
        assert producer._parse_enrollment_projection(result.stdout) == NODE_ID  # noqa: SLF001
    else:
        with pytest.raises(
            producer.ProducerError,
            match="enrollment_projection_invalid",
        ):
            producer._parse_enrollment_projection(result.stdout)  # noqa: SLF001


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_subprocess_adapter_rejects_invalid_utf8_without_reflection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stream: str,
) -> None:
    run_id = "20260724T180000Z-1234abcd"
    runtime = tmp_path / run_id
    monkeypatch.setattr(producer, "RUNTIME_BASE", tmp_path)
    plan = producer.ComposePlan(run_id, runtime)
    executor = producer.SubprocessExecutor({})
    raw_secret = b"\xffsecret-value"
    if stream == "stdout":
        command = _o4_enrollment_command(plan)
        stdout, stderr = raw_secret, b""
    else:
        image_id = "sha256:" + ("a" * 64)
        executor.bind_image_identity(image_id)
        command = plan.image_id_inspect(image_id)
        stdout, stderr = b"", raw_secret

    def fake_run(
        invoked: tuple[str, ...],
        **_: object,
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(invoked, 1, stdout, stderr)

    monkeypatch.setattr(producer.subprocess, "run", fake_run)
    with pytest.raises(
        producer.ProducerError,
        match="subprocess_output_rejected",
    ) as caught:
        executor.run(command)

    assert "secret-value" not in str(caught.value)
    assert "secret-value" not in repr(caught.value)


def test_raw_successful_inspect_does_not_authorize_unbound_id_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = "20260724T180000Z-1234abcd"
    runtime = tmp_path / run_id
    monkeypatch.setattr(producer, "RUNTIME_BASE", tmp_path)
    plan = producer.ComposePlan(run_id, runtime)
    image_id = "sha256:" + "a" * 64
    calls: list[tuple[str, ...]] = []

    def fake_run(
        command: tuple[str, ...],
        **_: object,
    ) -> subprocess.CompletedProcess[bytes]:
        calls.append(command)
        return subprocess.CompletedProcess(
            command,
            0,
            json.dumps({"Id": image_id}).encode(),
            b"",
        )

    monkeypatch.setattr(producer.subprocess, "run", fake_run)
    executor = producer.SubprocessExecutor({})

    result = executor.run(plan.image_inspect(plan.images[0]))
    assert result.returncode == 0
    for forbidden in (
        plan.image_remove(image_id),
        plan.image_id_inspect(image_id),
        plan.image_ancestor_containers(image_id),
    ):
        with pytest.raises(
            producer.ProducerError,
            match="subprocess_command_not_allowed",
        ):
            executor.run(forbidden)
    assert calls == [plan.image_inspect(plan.images[0])]


@pytest.mark.parametrize(
    ("returncode", "stdout", "stderr", "classification"),
    [
        (
            1,
            "",
            "Error response from daemon: No such image: {image_id}\n",
            "image_not_found",
        ),
        (
            1,
            "\n",
            "Error response from daemon: No such image: {image_id}",
            "image_not_found",
        ),
        (1, "", "Error response from daemon: permission denied\n", "error"),
        (
            2,
            "",
            "Error response from daemon: No such image: {image_id}\n",
            "error",
        ),
        (
            1,
            " ",
            "Error response from daemon: No such image: {image_id}\n",
            "error",
        ),
        (
            1,
            "\t",
            "Error response from daemon: No such image: {image_id}\n",
            "error",
        ),
        (
            1,
            "\r\n",
            "Error response from daemon: No such image: {image_id}\n",
            "error",
        ),
        (
            1,
            "\n\n",
            "Error response from daemon: No such image: {image_id}\n",
            "error",
        ),
        (
            1,
            "content",
            "Error response from daemon: No such image: {image_id}\n",
            "error",
        ),
    ],
)
def test_bound_id_probe_classifies_only_exact_not_found_as_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    stdout: str,
    stderr: str,
    classification: str,
) -> None:
    run_id = "20260724T180000Z-1234abcd"
    runtime = tmp_path / run_id
    monkeypatch.setattr(producer, "RUNTIME_BASE", tmp_path)
    plan = producer.ComposePlan(run_id, runtime)
    image_id = "sha256:" + "a" * 64
    executor = producer.SubprocessExecutor({})
    executor.bind_image_identity(image_id)

    def fake_run(
        command: tuple[str, ...],
        **_: object,
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(
            command,
            returncode,
            stdout.encode(),
            stderr.format(image_id=image_id).encode(),
        )

    monkeypatch.setattr(producer.subprocess, "run", fake_run)
    result = executor.run(plan.image_id_inspect(image_id))

    assert result.returncode == returncode
    assert result.stdout == stdout
    assert result.classification == classification


def test_subprocess_hermes_uses_devnull_for_both_streams(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    run_id = "20260724T180000Z-1234abcd"
    runtime = tmp_path / run_id
    monkeypatch.setattr(producer, "RUNTIME_BASE", tmp_path)
    plan = producer.ComposePlan(run_id, runtime)
    observed: dict[str, object] = {}

    def fake_run(command: tuple[str, ...], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        observed.update(kwargs)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(producer.subprocess, "run", fake_run)
    result = producer.SubprocessExecutor({}).run_hermes(
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
        timeout=producer.HERMES_TIMEOUT_SECONDS,
    )

    assert result == producer.HermesResult("exit", 0)
    assert observed["stdout"] is subprocess.DEVNULL
    assert observed["stderr"] is subprocess.DEVNULL
    assert observed["stdin"] is subprocess.DEVNULL
    assert not hasattr(result, "stdout")
    assert not hasattr(result, "stderr")


@pytest.mark.parametrize(
    "result",
    [
        producer.HermesResult("exit", 7),
        producer.HermesResult("timeout", None),
        producer.HermesResult("interruption", None),
    ],
)
def test_hermes_failure_timeout_or_interruption_consumes_only_attempt_and_never_assembles(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
    result: producer.HermesResult,
) -> None:
    runtime, executors, apis, provider, assembler = fake_stack
    executors.executor.hermes_result = result

    with pytest.raises(producer.ProducerError, match=f"hermes_{result.classification}_failed"):
        producer.run_producer(
            gate=AllowGate(),
            runtime_factory=runtime,
            executor_factory=executors,
            api_factory=apis,
            provider=provider,
            assembler=assembler,
            candidate=(COMMIT, TREE),
            environment={},
            now=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
        )

    assert len(executors.executor.hermes_commands) == 1
    assert assembler.calls == 0
    assert apis.api.admission_count == 1


def test_source_drift_fails_before_image_build_and_still_runs_cleanup_once(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, executors, apis, provider, assembler = fake_stack
    monkeypatch.setattr(
        producer,
        "_observe_exact_source",
        lambda state: (_ for _ in ()).throw(producer.ProducerError("source_candidate_changed")),
    )

    with pytest.raises(producer.ProducerError, match="source_candidate_changed"):
        producer.run_producer(
            gate=AllowGate(),
            runtime_factory=runtime,
            executor_factory=executors,
            api_factory=apis,
            provider=provider,
            assembler=assembler,
            candidate=(COMMIT, TREE),
            environment={},
            now=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
        )

    assert executors.executor.hermes_commands == []
    assert apis.api.admission_count == 0
    assert assembler.calls == 0


def test_hostile_subprocess_output_is_rejected_without_reflection() -> None:
    with pytest.raises(producer.ProducerError, match="subprocess_output_rejected") as caught:
        producer._require_success(  # noqa: SLF001
            producer.CommandResult(0, "Bearer secret-value"),
            "unused",
        )
    assert "secret-value" not in str(caught.value)


@pytest.mark.parametrize(
    "tail",
    [
        ("exec", "ithildin-api", "sh"),
        ("logs",),
        ("login",),
        ("pull",),
        ("push",),
        ("system", "prune"),
        ("run", "--rm", "hermes", "caller-argument"),
    ],
)
def test_static_command_validator_rejects_forbidden_or_caller_supplied_actions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tail: tuple[str, ...],
) -> None:
    run_id = "20260724T180000Z-1234abcd"
    monkeypatch.setattr(producer, "RUNTIME_BASE", tmp_path)
    plan = producer.ComposePlan(run_id, tmp_path / run_id)
    with pytest.raises(producer.ProducerError, match="subprocess_command_not_allowed"):
        producer._validate_command(  # noqa: SLF001
            plan.compose(*tail),
            hermes=False,
        )


def test_static_command_validator_rejects_uninspected_generic_image_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = "20260724T180000Z-1234abcd"
    monkeypatch.setattr(producer, "RUNTIME_BASE", tmp_path)
    plan = producer.ComposePlan(run_id, tmp_path / run_id)
    with pytest.raises(producer.ProducerError, match="subprocess_command_not_allowed"):
        producer._validate_command(  # noqa: SLF001
            plan.image_remove("sha256:" + "f" * 64),
            hermes=False,
            inspected_image_ids=frozenset(),
        )


@pytest.mark.parametrize("replacement", ["run", "base", "var_symlink"])
def test_private_directory_rejects_lexical_anchor_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement: str,
) -> None:
    root = tmp_path / "repo"
    var = root / "var"
    var.mkdir(parents=True)
    root.chmod(0o755)
    var.chmod(0o755)
    runtime_base = var / "runtime-base"
    receipt_base = var / "receipt-base"
    monkeypatch.setattr(producer, "ROOT", root)
    monkeypatch.setattr(producer, "RUNTIME_BASE", runtime_base)
    monkeypatch.setattr(producer, "RECEIPT_BASE", receipt_base)
    anchored = producer.PrivateDirectory.create(
        runtime_base,
        "20260724T180000Z-1234abcd",
    )
    try:
        if replacement == "run":
            os.rename(
                anchored.name,
                f"{anchored.name}.moved",
                src_dir_fd=anchored.base_fd,
                dst_dir_fd=anchored.base_fd,
            )
            os.mkdir(anchored.name, 0o700, dir_fd=anchored.base_fd)
        elif replacement == "base":
            os.rename(
                runtime_base.name,
                "runtime-base-moved",
                src_dir_fd=anchored.var_fd,
                dst_dir_fd=anchored.var_fd,
            )
            os.mkdir(runtime_base.name, 0o700, dir_fd=anchored.var_fd)
        else:
            os.rename(var, root / "var-moved")
            replacement_var = root / "replacement-var"
            replacement_var.mkdir()
            os.symlink(replacement_var, var)
        with pytest.raises(producer.ProducerError, match="runtime_anchor_changed"):
            anchored.validate()
    finally:
        anchored.close()


@pytest.mark.parametrize(
    "case",
    ["symlink", "fifo", "mode", "directory_mode", "owner"],
)
def test_application_startup_stage_rejects_unsafe_filesystem_objects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    root = tmp_path / "repo"
    var = root / "var"
    var.mkdir(parents=True)
    root.chmod(0o755)
    var.chmod(0o755)
    runtime_base = var / "runtime-base"
    receipt_base = var / "receipt-base"
    monkeypatch.setattr(producer, "ROOT", root)
    monkeypatch.setattr(producer, "RUNTIME_BASE", runtime_base)
    monkeypatch.setattr(producer, "RECEIPT_BASE", receipt_base)
    run_id = "20260724T180000Z-1234abcd"
    runtime = producer.PrivateDirectory.create(runtime_base, run_id)
    receipts = FakePrivateDirectory(tmp_path / "receipts" / run_id)
    runtime.mkdir("startup-status")
    state = producer.ProducerState(
        COMMIT,
        TREE,
        run_id,
        producer.ComposePlan(run_id, runtime.path),
        runtime,
        cast(producer.PrivateDirectory, receipts),
    )
    status_directory = runtime.file("startup-status")
    final = status_directory / producer.APPLICATION_STARTUP_STATUS_FILE
    try:
        if case == "symlink":
            final.symlink_to(status_directory / "missing")
        elif case == "fifo":
            os.mkfifo(final, 0o600)
        else:
            runtime.write(
                "startup-status/api-startup-stage.json",
                _startup_stage_record("startup_ready"),
            )
            if case == "mode":
                final.chmod(0o644)
            elif case == "directory_mode":
                status_directory.chmod(0o755)
        if case == "owner":
            current_uid = os.geteuid()
            with monkeypatch.context() as owner_context:
                owner_context.setattr(
                    producer.os,
                    "geteuid",
                    lambda: current_uid + 1,
                )
                result = (
                    producer._collect_application_startup_stage_diagnostic(  # noqa: SLF001
                        state
                    )
                )
        else:
            result = producer._collect_application_startup_stage_diagnostic(  # noqa: SLF001
                state
            )

        assert result == {
            "collection_status": "output_rejected",
            "collection_reason_code": (
                "application_startup_stage_unsafe_or_incomplete"
            ),
            "last_emitted_stage": "unknown",
        }
    finally:
        status_directory.chmod(0o700)
        assert runtime.remove() is True


def test_node_configuration_mismatch_times_out_before_admission(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, executors, apis, provider, assembler = fake_stack
    apis.api.node_overrides = {
        "acknowledged_configuration_digest": "sha256:" + "f" * 64
    }
    ticks = iter((0.0, 0.0, 1.0))
    monkeypatch.setattr(producer, "NODE_SYNCHRONIZATION_SECONDS", 0.5)
    monkeypatch.setattr(producer.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(producer.time, "sleep", lambda _: None)

    with pytest.raises(producer.ProducerError, match="node_synchronization_timeout"):
        producer.run_producer(
            gate=AllowGate(),
            runtime_factory=runtime,
            executor_factory=executors,
            api_factory=apis,
            provider=provider,
            assembler=assembler,
            candidate=(COMMIT, TREE),
            environment={},
            now=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
        )

    assert apis.api.admission_count == 0
    assert executors.executor.hermes_commands == []


@pytest.mark.parametrize(
    "mutation",
    [
        lambda command: (*command[:4], "--debug", *command[4:]),
        lambda command: (
            *command[:4],
            "--project-name",
            "ithildin-local-v1-o4-1234abcd",
            *command[4:],
        ),
        lambda command: (
            *command[:-1],
            "--file",
            "/tmp/hostile-compose.yml",
            command[-1],
        ),
    ],
)
def test_exact_command_vocabulary_rejects_duplicate_or_extra_global_structure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: object,
) -> None:
    run_id = "20260724T180000Z-1234abcd"
    monkeypatch.setattr(producer, "RUNTIME_BASE", tmp_path)
    plan = producer.ComposePlan(run_id, tmp_path / run_id)
    command = plan.compose("--profile", "node", "config", "--quiet")
    assert callable(mutation)
    with pytest.raises(producer.ProducerError, match="subprocess_command_not_allowed"):
        producer._validate_command(mutation(command), hermes=False)  # type: ignore[arg-type] # noqa: SLF001


def test_mixed_inspected_platforms_fail_before_admission(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
) -> None:
    runtime, executors, apis, provider, assembler = fake_stack
    plan = producer.ComposePlan(
        "20260724T180000Z-1234abcd",
        runtime.runtime.path,
    )
    executors.executor.image_architectures[plan.images[-1]] = "amd64"

    with pytest.raises(producer.ProducerError, match="image_platform_mismatch"):
        producer.run_producer(
            gate=AllowGate(),
            runtime_factory=runtime,
            executor_factory=executors,
            api_factory=apis,
            provider=provider,
            assembler=assembler,
            candidate=(COMMIT, TREE),
            environment={},
            now=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
        )

    assert apis.api.admission_count == 0


def test_assembler_rejects_mixed_inventory_platform(
    tmp_path: Path,
) -> None:
    receipt = FakePrivateDirectory(tmp_path)
    references = [
        f"ithildin/{name}-o4:1234abcd"
        for name in ("api", "ui", "node", "hermes-node-bridge")
    ]
    images: list[JsonObject] = [
        {
            "reference": reference,
            "image_id": "sha256:" + str(index) * 64,
            "platform": "linux/amd64" if index == 4 else "linux/arm64",
            "config_digest": "sha256:" + str(index) * 64,
            "ordered_layer_digests": ["sha256:" + "9" * 64],
        }
        for index, reference in enumerate(references, start=1)
    ]
    image_document: JsonObject = {"images": images}
    license_document: JsonObject = {"files": []}
    receipt.files["image-artifact-inventory.json"] = producer.canonical_json(
        image_document
    ).encode()
    receipt.files["license-source-inventory.json"] = producer.canonical_json(
        license_document
    ).encode()
    build: JsonObject = {
        "image_artifact_inventory_digest": producer.sha256_digest(image_document),
        "license_source_inventory_digest": producer.sha256_digest(license_document),
        "platform": "linux/arm64",
        "bridge_image_digest": images[-1]["image_id"],
        "node_image_digest": images[-2]["image_id"],
    }

    with pytest.raises(producer.ProducerError, match="image_inventory_platform_invalid"):
        producer._validate_inventory_documents(  # noqa: SLF001
            build,
            cast(producer.PrivateDirectory, receipt),
        )


def test_cleanup_interruption_marks_recovery_and_closes_descriptors(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
) -> None:
    runtime, executors, apis, provider, assembler = fake_stack
    executors.executor.interrupt_on = "down"

    with pytest.raises(producer.ProducerError, match="recovery_required"):
        producer.run_producer(
            gate=AllowGate(),
            runtime_factory=runtime,
            executor_factory=executors,
            api_factory=apis,
            provider=provider,
            assembler=assembler,
            candidate=(COMMIT, TREE),
            environment={},
            now=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
        )

    assert runtime.runtime.removed is True
    assert runtime.runtime.closed is True
    assert runtime.receipts.closed is True
    assert assembler.calls == 0


def test_assembler_failure_unconditionally_closes_both_roots(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
) -> None:
    runtime, executors, apis, provider, assembler = fake_stack
    assembler.failure = producer.ProducerError("synthetic_assembler_failure")

    with pytest.raises(producer.ProducerError, match="synthetic_assembler_failure"):
        producer.run_producer(
            gate=AllowGate(),
            runtime_factory=runtime,
            executor_factory=executors,
            api_factory=apis,
            provider=provider,
            assembler=assembler,
            candidate=(COMMIT, TREE),
            environment={},
            now=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
        )

    assert runtime.runtime.closed is True
    assert runtime.receipts.closed is True
    disposition = json.loads(runtime.receipts.files["disposition.json"])
    assert disposition["status"] == "quarantined_not_published"
    assert disposition["failure_code"] == "synthetic_assembler_failure"


@pytest.mark.parametrize(
    ("seam", "expected"),
    [
        ("state_construction_signal", "interrupted"),
        ("post_create_signal", "interrupted"),
        ("prepare", "synthetic_prepare_failure"),
        ("socket", "synthetic_socket_failure"),
        ("executor_factory", "synthetic_executor_factory_failure"),
        ("api_factory", "synthetic_api_factory_failure"),
    ],
)
def test_outer_cleanup_guard_removes_plaintext_for_every_early_failure_seam(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
    monkeypatch: pytest.MonkeyPatch,
    seam: str,
    expected: str,
) -> None:
    runtime, executors, apis, provider, assembler = fake_stack

    def fail(code: str) -> None:
        raise producer.ProducerError(code)

    if seam == "state_construction_signal":
        monkeypatch.setattr(
            producer,
            "ComposePlan",
            lambda run_id, runtime_path: (_ for _ in ()).throw(
                producer.ProducerSignal("synthetic")
            ),
        )
    elif seam == "post_create_signal":
        monkeypatch.setattr(
            producer,
            "_create_candidate_snapshot",
            lambda root, commit, tree: (_ for _ in ()).throw(
                producer.ProducerSignal("synthetic")
            ),
        )
    elif seam == "prepare":
        monkeypatch.setattr(
            producer,
            "_prepare_runtime",
            lambda state, token: fail("synthetic_prepare_failure"),
        )
    elif seam == "socket":
        monkeypatch.setattr(
            producer,
            "_prove_local_docker_socket",
            lambda candidates=None: fail("synthetic_socket_failure"),
        )
    elif seam == "executor_factory":
        monkeypatch.setattr(
            executors,
            "create",
            lambda environment: fail("synthetic_executor_factory_failure"),
        )
    else:
        monkeypatch.setattr(
            apis,
            "create",
            lambda token: fail("synthetic_api_factory_failure"),
        )

    with pytest.raises(producer.ProducerError, match=expected):
        producer.run_producer(
            gate=AllowGate(),
            runtime_factory=runtime,
            executor_factory=executors,
            api_factory=apis,
            provider=provider,
            assembler=assembler,
            candidate=(COMMIT, TREE),
            environment={},
            now=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
        )

    assert runtime.runtime.removed is True
    assert runtime.runtime.closed is True
    assert runtime.receipts.closed is True
    assert assembler.calls == 0
    assert executors.executor.commands == []
    assert executors.executor.hermes_commands == []
    assert apis.api.calls == []
    assert provider.calls == 0
    disposition = json.loads(runtime.receipts.files["disposition.json"])
    assert disposition["status"] == "quarantined_not_published"


@pytest.mark.parametrize(
    "revoke_failure",
    ["unavailable", "invalid", "interrupted", "validated_identity_flag_window"],
)
def test_unconfirmed_revocation_retains_identity_volume_and_runtime_for_recovery(
    tmp_path: Path,
    revoke_failure: str,
) -> None:
    run_id = "20260724T180000Z-1234abcd"
    runtime = FakePrivateDirectory(tmp_path / "runtime" / run_id)
    receipts = FakePrivateDirectory(tmp_path / "receipts" / run_id)
    plan = producer.ComposePlan(run_id, runtime.path)
    state = producer.ProducerState(
        COMMIT,
        TREE,
        run_id,
        plan,
        cast(producer.PrivateDirectory, runtime),
        cast(producer.PrivateDirectory, receipts),
    )
    state.node_id = NODE_ID
    state.mutated = True
    state.docker_preflight_complete = True
    state.docker_mutation_started = True
    state.docker_ownership_proven = True
    state.node_enrolled = True
    if revoke_failure == "validated_identity_flag_window":
        state.node_enrolled = False
        state.enrollment_outcome_ambiguous = True
    state.inspected_images = {
        reference: "sha256:" + str(index) * 64
        for index, reference in enumerate(plan.images, start=1)
    }
    state.gateway_journey = {}

    class RecoveryCleanupExecutor:
        def __init__(self) -> None:
            self.commands: list[tuple[str, ...]] = []

        def run(
            self,
            command: tuple[str, ...],
            *,
            input_text: str | None = None,
            timeout: float = 180.0,
        ) -> producer.CommandResult:
            del input_text, timeout
            self.commands.append(command)
            assert command == plan.compose(
                "--profile",
                "node",
                "stop",
                "ithildin-node",
                fixed=True,
            )
            return producer.CommandResult(0, "")

        def run_hermes(
            self,
            command: tuple[str, ...],
            *,
            timeout: float,
        ) -> producer.HermesResult:
            raise AssertionError((command, timeout))

    class UnconfirmedRevokeApi:
        def get(self, path: str, *, admin: bool = True) -> JsonObject:
            raise AssertionError((path, admin))

        def post(self, path: str, payload: JsonObject) -> JsonObject:
            assert path == f"/nodes/{NODE_ID}/revoke"
            assert payload == {}
            if revoke_failure == "interrupted":
                raise producer.ProducerSignal("synthetic")
            return {"node_id": NODE_ID, "status": "not-revoked"}

    executor = RecoveryCleanupExecutor()
    result = producer._cleanup_once(  # noqa: SLF001
        state,
        executor,
        None if revoke_failure == "unavailable" else UnconfirmedRevokeApi(),
    )

    assert result is None
    assert runtime.removed is False
    assert state.recovery_required is True
    assert state.enrollment_revocation_confirmed is False
    assert state.enrollment_outcome_ambiguous is False
    assert state.revocation_recovery_receipt_written is True
    assert state.cleanup_failures == [
        (
            "node_revocation_unavailable"
            if revoke_failure == "unavailable"
            else "node_revocation_failed"
        )
    ]
    assert executor.commands == [
        plan.compose(
            "--profile",
            "node",
            "stop",
            "ithildin-node",
            fixed=True,
        )
    ]
    assert runtime.files == {}
    assert state.inspected_images
    recovery_content = receipts.files[producer.REVOCATION_RECOVERY_RECEIPT]
    recovery = json.loads(recovery_content)
    assert recovery_content == (
        producer.canonical_json(cast(JsonObject, recovery)) + "\n"
    ).encode()
    assert recovery == {
        "schema_version": "1",
        "receipt_kind": "local_v1_o4_node_revocation_recovery",
        "run_id": run_id,
        "candidate_commit": COMMIT,
        "candidate_tree": TREE,
        "workspace_id": producer.WORKSPACE_ID,
        "node_id": NODE_ID,
        "compose_project": plan.project,
        "node_volume_name": f"{plan.project}_ithildin-node-state",
        "revocation_confirmed": False,
        "node_volume_retained": True,
        "anchored_runtime_retained": True,
        "reconciliation_required": True,
        "next_action": "confirm_node_revocation_before_destructive_cleanup",
        "release_allowed": False,
        "uat_complete": False,
    }
    lowered = recovery_content.lower()
    assert b"token" not in lowered
    assert b"private" not in lowered
    assert b"enrollment" not in lowered
    assert state.gateway_journey == {}


def test_merged_compose_config_rejects_any_surviving_repo_host_path(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
) -> None:
    runtime, _, _, _, _ = fake_stack
    run_id = "20260724T180000Z-1234abcd"
    plan = producer.ComposePlan(run_id, runtime.runtime.path)
    snapshot = FakeCandidateSnapshot(runtime.receipts)
    state = producer.ProducerState(
        COMMIT,
        TREE,
        run_id,
        plan,
        cast(producer.PrivateDirectory, runtime.runtime),
        cast(producer.PrivateDirectory, runtime.receipts),
        cast(producer.CandidateSnapshot, snapshot),
    )
    document = _merged_compose_document(plan, fixed=True)
    services = cast(JsonObject, document["services"])
    api = cast(JsonObject, services["ithildin-api"])
    volumes = cast(list[JsonObject], api["volumes"])
    volumes[0]["source"] = str(producer.ROOT / "tool-manifests.lock.json")

    with pytest.raises(producer.ProducerError, match="merged_compose_host_path_invalid"):
        producer._validate_merged_compose_config(  # noqa: SLF001
            producer.CommandResult(0, json.dumps(document)),
            state,
            fixed=True,
        )


@pytest.mark.parametrize(
    "mutation",
    ["read_only", "ui_mount", "duplicate"],
)
def test_merged_compose_config_requires_exact_api_only_startup_mount(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
    mutation: str,
) -> None:
    runtime, _, _, _, _ = fake_stack
    run_id = "20260724T180000Z-1234abcd"
    plan = producer.ComposePlan(run_id, runtime.runtime.path)
    state = producer.ProducerState(
        COMMIT,
        TREE,
        run_id,
        plan,
        cast(producer.PrivateDirectory, runtime.runtime),
        cast(producer.PrivateDirectory, runtime.receipts),
        cast(producer.CandidateSnapshot, FakeCandidateSnapshot(runtime.receipts)),
    )
    document = _merged_compose_document(plan, fixed=True)
    services = cast(JsonObject, document["services"])
    api = cast(JsonObject, services["ithildin-api"])
    volumes = cast(list[JsonObject], api["volumes"])
    startup_mount = next(
        volume
        for volume in volumes
        if volume["target"] == "/run/ithildin-startup"
    )
    if mutation == "read_only":
        startup_mount["read_only"] = True
    elif mutation == "ui_mount":
        volumes.remove(startup_mount)
        cast(list[JsonObject], cast(JsonObject, services["ithildin-ui"])["volumes"]).append(
            startup_mount
        )
    else:
        volumes.append(dict(startup_mount))

    with pytest.raises(producer.ProducerError):
        producer._validate_merged_compose_config(  # noqa: SLF001
            producer.CommandResult(0, json.dumps(document)),
            state,
            fixed=True,
        )


def test_merged_compose_config_requires_exactly_one_bounded_node_tmpfs(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
) -> None:
    runtime, _, _, _, _ = fake_stack
    run_id = "20260724T180000Z-1234abcd"
    plan = producer.ComposePlan(run_id, runtime.runtime.path)
    snapshot = FakeCandidateSnapshot(runtime.receipts)
    state = producer.ProducerState(
        COMMIT,
        TREE,
        run_id,
        plan,
        cast(producer.PrivateDirectory, runtime.runtime),
        cast(producer.PrivateDirectory, runtime.receipts),
        cast(producer.CandidateSnapshot, snapshot),
    )
    document = _merged_compose_document(plan, fixed=True)
    services = cast(JsonObject, document["services"])
    node = cast(JsonObject, services["ithildin-node"])
    node["tmpfs"] = [*producer.NODE_TMPFS, "/tmp"]

    with pytest.raises(
        producer.ProducerError,
        match="merged_compose_node_tmpfs_invalid",
    ):
        producer._validate_merged_compose_config(  # noqa: SLF001
            producer.CommandResult(0, json.dumps(document)),
            state,
            fixed=True,
        )


def test_snapshot_anchor_detects_candidate_replacement_during_external_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    var = root / "var"
    var.mkdir(parents=True)
    root.chmod(0o755)
    var.chmod(0o755)
    receipt_base = var / "receipts"
    runtime_base = var / "runtime"
    monkeypatch.setattr(producer, "ROOT", root)
    monkeypatch.setattr(producer, "RUNTIME_BASE", runtime_base)
    monkeypatch.setattr(producer, "RECEIPT_BASE", receipt_base)
    receipts = producer.PrivateDirectory.create(
        receipt_base,
        "20260724T180000Z-1234abcd",
    )
    receipts.mkdir("candidate")
    content = b"exact candidate\n"
    receipts.write("candidate/input.txt", content, mode=0o400)
    snapshot_fd = os.open(
        "candidate",
        producer._directory_flags(),  # noqa: SLF001
        dir_fd=receipts.run_fd,
    )
    os.fchmod(snapshot_fd, 0o500)
    details = os.fstat(snapshot_fd)
    snapshot = producer.CandidateSnapshot(
        receipts,
        COMMIT,
        TREE,
        {"input.txt": (0o400, "sha256:" + hashlib.sha256(content).hexdigest())},
        (),
        snapshot_fd,
        (details.st_dev, details.st_ino),
    )

    class ReplacingExecutor:
        def run(
            self,
            command: tuple[str, ...],
            *,
            input_text: str | None = None,
            timeout: float = 180.0,
        ) -> producer.CommandResult:
            del command, input_text, timeout
            os.rename(
                "candidate",
                "candidate-replaced",
                src_dir_fd=receipts.run_fd,
                dst_dir_fd=receipts.run_fd,
            )
            os.mkdir("candidate", 0o700, dir_fd=receipts.run_fd)
            return producer.CommandResult(0, "")

        def run_hermes(
            self,
            command: tuple[str, ...],
            *,
            timeout: float,
        ) -> producer.HermesResult:
            raise AssertionError((command, timeout))

    try:
        guarded = producer.AnchoredExecutor(ReplacingExecutor(), (snapshot,))
        with pytest.raises(producer.ProducerError, match="candidate_snapshot_changed"):
            guarded.run(("synthetic",))
    finally:
        snapshot.close()
        receipts.close()


@pytest.mark.parametrize("extra_kind", ["file", "directory", "symlink", "special"])
def test_snapshot_validation_rejects_every_unexpected_entry_kind(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    extra_kind: str,
) -> None:
    root = tmp_path / "repo"
    var = root / "var"
    var.mkdir(parents=True)
    root.chmod(0o755)
    var.chmod(0o755)
    receipt_base = var / "receipts"
    runtime_base = var / "runtime"
    monkeypatch.setattr(producer, "ROOT", root)
    monkeypatch.setattr(producer, "RUNTIME_BASE", runtime_base)
    monkeypatch.setattr(producer, "RECEIPT_BASE", receipt_base)
    receipts = producer.PrivateDirectory.create(
        receipt_base,
        "20260724T180000Z-1234abcd",
    )
    receipts.mkdir("candidate")
    content = b"exact candidate\n"
    receipts.write("candidate/input.txt", content, mode=0o400)
    snapshot_fd = os.open(
        "candidate",
        producer._directory_flags(),  # noqa: SLF001
        dir_fd=receipts.run_fd,
    )
    os.fchmod(snapshot_fd, 0o500)
    details = os.fstat(snapshot_fd)
    snapshot = producer.CandidateSnapshot(
        receipts,
        COMMIT,
        TREE,
        {"input.txt": (0o400, "sha256:" + hashlib.sha256(content).hexdigest())},
        (),
        snapshot_fd,
        (details.st_dev, details.st_ino),
    )
    os.fchmod(snapshot_fd, 0o700)
    if extra_kind == "file":
        descriptor = os.open(
            "extra",
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o400,
            dir_fd=snapshot_fd,
        )
        os.close(descriptor)
    elif extra_kind == "directory":
        os.mkdir("extra", 0o500, dir_fd=snapshot_fd)
    elif extra_kind == "symlink":
        os.symlink("input.txt", "extra", dir_fd=snapshot_fd)
    else:
        os.mkfifo("extra", 0o400, dir_fd=snapshot_fd)
    os.fchmod(snapshot_fd, 0o500)
    try:
        with pytest.raises(producer.ProducerError, match="candidate_snapshot_changed"):
            snapshot.validate()
    finally:
        snapshot.close()
        receipts.close()


def test_preflight_failure_makes_no_cleanup_docker_api_or_provider_calls(
    fake_stack: tuple[
        FakeRuntimeFactory,
        FakeExecutorFactory,
        FakeApiFactory,
        FakeProvider,
        FakeAssembler,
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, executors, apis, provider, assembler = fake_stack
    observed_command_count = 0

    def fail_preflight(
        state: producer.ProducerState,
        executor: producer.Executor,
        selected_provider: producer.Provider,
    ) -> None:
        nonlocal observed_command_count
        del selected_provider
        executor.run(state.plan.daemon_version())
        observed_command_count = len(executors.executor.commands)
        raise producer.ProducerError("synthetic_preflight_failure")

    monkeypatch.setattr(producer, "_preflight", fail_preflight)
    with pytest.raises(producer.ProducerError, match="synthetic_preflight_failure"):
        producer.run_producer(
            gate=AllowGate(),
            runtime_factory=runtime,
            executor_factory=executors,
            api_factory=apis,
            provider=provider,
            assembler=assembler,
            candidate=(COMMIT, TREE),
            environment={},
            now=datetime(2026, 7, 24, 18, 0, tzinfo=UTC),
        )

    assert observed_command_count == 1
    assert len(executors.executor.commands) == observed_command_count
    assert executors.executor.hermes_commands == []
    assert apis.api.calls == []
    assert provider.calls == 0
    assert runtime.runtime.removed is True


@pytest.mark.parametrize("failure_kind", ["write", "signal"])
def test_atomic_report_publication_never_leaves_success_directory_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_kind: str,
) -> None:
    root = tmp_path / "repo"
    var = root / "var"
    var.mkdir(parents=True)
    root.chmod(0o755)
    var.chmod(0o755)
    receipt_base = var / "receipts"
    runtime_base = var / "runtime"
    report_base = var / "reports"
    monkeypatch.setattr(producer, "ROOT", root)
    monkeypatch.setattr(producer, "RUNTIME_BASE", runtime_base)
    monkeypatch.setattr(producer, "RECEIPT_BASE", receipt_base)
    monkeypatch.setattr(producer.assembler_module, "REPORT_BASE", report_base)
    monkeypatch.setattr(
        producer.assembler_module,
        "render_markdown",
        lambda report: "verified report\n",
    )
    receipts = producer.PrivateDirectory.create(
        receipt_base,
        "20260724T180000Z-1234abcd",
    )
    original_write = producer._write_private_at  # noqa: SLF001
    calls = 0

    def fail_second_write(parent: int, name: str, content: bytes) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            if failure_kind == "signal":
                raise producer.ProducerSignal("synthetic")
            raise producer.ProducerError("synthetic_report_write_failure")
        original_write(parent, name, content)

    monkeypatch.setattr(producer, "_write_private_at", fail_second_write)
    report: JsonObject = {"run_id": "20260724T180000Z-87654321"}
    expected = (
        producer.ProducerSignal
        if failure_kind == "signal"
        else producer.ProducerError
    )
    try:
        with pytest.raises(expected):
            producer._publish_report_atomic(  # noqa: SLF001
                report,
                receipts,
            )
        assert not (report_base / "20260724T180000Z-87654321").exists()
        assert list(report_base.iterdir()) == []
    finally:
        receipts.close()


@pytest.mark.parametrize("failure_kind", ["fsync", "signal"])
def test_post_rename_failure_removes_exact_public_run_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_kind: str,
) -> None:
    root = tmp_path / "repo"
    var = root / "var"
    var.mkdir(parents=True)
    root.chmod(0o755)
    var.chmod(0o755)
    receipt_base = var / "receipts"
    runtime_base = var / "runtime"
    report_base = var / "reports"
    monkeypatch.setattr(producer, "ROOT", root)
    monkeypatch.setattr(producer, "RUNTIME_BASE", runtime_base)
    monkeypatch.setattr(producer, "RECEIPT_BASE", receipt_base)
    monkeypatch.setattr(producer.assembler_module, "REPORT_BASE", report_base)
    monkeypatch.setattr(
        producer.assembler_module,
        "render_markdown",
        lambda report: "verified report\n",
    )
    receipts = producer.PrivateDirectory.create(
        receipt_base,
        "20260724T180000Z-1234abcd",
    )
    original_fsync = producer.os.fsync
    calls = 0

    def fail_base_fsync(descriptor: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 4:
            if failure_kind == "signal":
                raise producer.ProducerSignal("synthetic")
            raise OSError("synthetic fsync failure")
        original_fsync(descriptor)

    monkeypatch.setattr(producer.os, "fsync", fail_base_fsync)
    report: JsonObject = {"run_id": "20260724T180000Z-87654321"}
    expected = (
        producer.ProducerSignal
        if failure_kind == "signal"
        else producer.ProducerError
    )
    try:
        with pytest.raises(expected):
            producer._publish_report_atomic(  # noqa: SLF001
                report,
                receipts,
            )
        assert report_base.exists()
        assert list(report_base.iterdir()) == []
    finally:
        receipts.close()


def test_post_rename_compound_remove_and_quarantine_failure_requires_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    var = root / "var"
    var.mkdir(parents=True)
    root.chmod(0o755)
    var.chmod(0o755)
    receipt_base = var / "receipts"
    report_base = var / "reports"
    monkeypatch.setattr(producer, "ROOT", root)
    monkeypatch.setattr(producer, "RUNTIME_BASE", var / "runtime")
    monkeypatch.setattr(producer, "RECEIPT_BASE", receipt_base)
    monkeypatch.setattr(producer.assembler_module, "REPORT_BASE", report_base)
    monkeypatch.setattr(
        producer.assembler_module,
        "render_markdown",
        lambda report: "verified report\n",
    )
    receipts = producer.PrivateDirectory.create(
        receipt_base,
        "20260724T180000Z-1234abcd",
    )
    original_rename = producer.os.rename

    def fail_quarantine_rename(
        source: str,
        destination: str,
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        if ".quarantined-" in destination:
            raise OSError("synthetic quarantine rename failure")
        original_rename(
            source,
            destination,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
        )

    monkeypatch.setattr(
        producer,
        "_remove_contents",
        lambda descriptor: (_ for _ in ()).throw(
            OSError("synthetic remove failure")
        ),
    )
    monkeypatch.setattr(producer.os, "rename", fail_quarantine_rename)
    monkeypatch.setattr(
        producer.PrivateDirectory,
        "validate",
        lambda self: (_ for _ in ()).throw(
            producer.ProducerError("synthetic_post_rename_failure")
        ),
    )
    run_id = "20260724T180000Z-87654321"
    try:
        with pytest.raises(
            producer.ProducerError,
            match="report_publication_recovery_required",
        ):
            producer._publish_report_atomic(  # noqa: SLF001
                {"run_id": run_id},
                receipts,
            )
        assert (report_base / run_id).is_dir()
    finally:
        receipts.close()


def test_post_rename_rollback_directory_fsync_failure_requires_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    var = root / "var"
    var.mkdir(parents=True)
    root.chmod(0o755)
    var.chmod(0o755)
    receipt_base = var / "receipts"
    report_base = var / "reports"
    monkeypatch.setattr(producer, "ROOT", root)
    monkeypatch.setattr(producer, "RUNTIME_BASE", var / "runtime")
    monkeypatch.setattr(producer, "RECEIPT_BASE", receipt_base)
    monkeypatch.setattr(producer.assembler_module, "REPORT_BASE", report_base)
    monkeypatch.setattr(
        producer.assembler_module,
        "render_markdown",
        lambda report: "verified report\n",
    )
    receipts = producer.PrivateDirectory.create(
        receipt_base,
        "20260724T180000Z-1234abcd",
    )
    original_fsync = producer.os.fsync
    calls = 0

    def fail_publication_and_rollback_fsync(descriptor: int) -> None:
        nonlocal calls
        calls += 1
        if calls >= 4:
            raise OSError("synthetic durable fsync failure")
        original_fsync(descriptor)

    monkeypatch.setattr(producer.os, "fsync", fail_publication_and_rollback_fsync)
    run_id = "20260724T180000Z-87654321"
    try:
        with pytest.raises(
            producer.ProducerError,
            match="report_publication_recovery_required",
        ):
            producer._publish_report_atomic(  # noqa: SLF001
                {"run_id": run_id},
                receipts,
            )
        assert not (report_base / run_id).exists()
    finally:
        receipts.close()


def test_report_base_swap_after_rename_rolls_back_through_held_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    var = root / "var"
    var.mkdir(parents=True)
    root.chmod(0o755)
    var.chmod(0o755)
    receipt_base = var / "receipts"
    runtime_base = var / "runtime"
    report_base = var / "reports"
    moved_base = var / "reports-moved"
    monkeypatch.setattr(producer, "ROOT", root)
    monkeypatch.setattr(producer, "RUNTIME_BASE", runtime_base)
    monkeypatch.setattr(producer, "RECEIPT_BASE", receipt_base)
    monkeypatch.setattr(producer.assembler_module, "REPORT_BASE", report_base)
    monkeypatch.setattr(
        producer.assembler_module,
        "render_markdown",
        lambda report: "verified report\n",
    )
    receipts = producer.PrivateDirectory.create(
        receipt_base,
        "20260724T180000Z-1234abcd",
    )
    original_rename = producer.os.rename
    swapped = False

    def swap_after_publish(
        source: str,
        destination: str,
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        nonlocal swapped
        original_rename(
            source,
            destination,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
        )
        if destination == "20260724T180000Z-87654321" and not swapped:
            swapped = True
            original_rename(report_base, moved_base)
            report_base.mkdir(mode=0o700)

    monkeypatch.setattr(producer.os, "rename", swap_after_publish)
    report: JsonObject = {"run_id": "20260724T180000Z-87654321"}
    try:
        with pytest.raises(producer.ProducerError):
            producer._publish_report_atomic(  # noqa: SLF001
                report,
                receipts,
            )
        assert swapped is True
        assert list(report_base.iterdir()) == []
        assert list(moved_base.iterdir()) == []
    finally:
        receipts.close()

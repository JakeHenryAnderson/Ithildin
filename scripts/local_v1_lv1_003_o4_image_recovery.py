"""Fixed, one-shot image recovery for the consumed LV1-003 O4 Attempt 003.

Importing this module performs no Docker or filesystem mutation.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

from scripts import local_v1_lv1_003_o4_producer as producer

ROOT = Path(__file__).resolve().parents[1]
AUTHORIZATION_JSON = Path(
    "docs/codex/local-v1-lv1-003-o4-image-recovery-authorization.json"
)
AUTHORIZATION_DOCUMENT = Path(
    "docs/codex/local-v1-lv1-003-o4-image-recovery-authorization.md"
)
ATTEMPT_003_CLOSURE_JSON = Path(
    "docs/codex/local-v1-lv1-003-o4-attempt-003-closure.json"
)
ATTEMPT_003_CLOSURE_DOCUMENT = Path(
    "docs/codex/local-v1-lv1-003-o4-attempt-003-closure.md"
)
RECOVERY_CLOSURE_JSON = Path(
    "docs/codex/local-v1-lv1-003-o4-image-recovery-closure.json"
)
RECOVERY_CLOSURE_DOCUMENT = Path(
    "docs/codex/local-v1-lv1-003-o4-image-recovery-closure.md"
)
AUTHORIZATION_JSON_DIGEST = (
    "sha256:103576d2db0b9fe177f935c8e075217c0786a93be34097eca66f906a11faa1aa"
)
AUTHORIZATION_DOCUMENT_DIGEST = (
    "sha256:7812616aff873ec22426eeb84759889827cbc3fadf98045fc5675b99a0432715"
)
ATTEMPT_003_CLOSURE_JSON_DIGEST = (
    "sha256:2dec56200e564decd398fd5c0e1539e60e1c87ebaf453c7093346ca61155db8a"
)
ATTEMPT_003_CLOSURE_DOCUMENT_DIGEST = (
    "sha256:b91cc06f5e88b35a4df18299405c60fa3868303d40c17d900ee101720feffe56"
)
RECOVERY_CLOSURE_JSON_DIGEST = (
    "sha256:88a47a8ee15dab08dc508487758564a448cfe4cc9d65c0adce39a2da1fdd8450"
)
RECOVERY_CLOSURE_DOCUMENT_DIGEST = (
    "sha256:69071ab5b0a0c00390726c639d633c0a83e1c93b9fb0c9f91fc835429180a930"
)
AUTHORIZATION_ORIGIN_COMMIT = "e703237fb22355c1ebc5aee509b6301970812dc3"
AUTHORIZATION_ORIGIN_TREE = "2fd7bdd86b2e2d37ecf7d1b9607c988fef6b5446"
PARENT_COMMIT = "2051a136e13bacbee4e3fcec332fc4ef78698e73"
PARENT_TREE = "e0cb7285e720c38a1e071536d7bd25e2bc7caa4e"
RUN_ID = "20260725T125344Z-6460809b"
PROJECT = "ithildin-local-v1-o4-6460809b"
HERMES_REFERENCE = "ithildin/hermes-node-bridge-o4:6460809b"
COMPOSE_VERSION = "5.1.4"
PLATFORM_OS = "linux"
PLATFORM_ARCHITECTURE = "arm64"
RUN_TARGET = "local-v1-lv1-003-o4-image-recovery-run"
MODULE_COMMAND = "uv run python -m scripts.local_v1_lv1_003_o4_image_recovery"
RECOVERY_ID = "LV1-003-O4-ATTEMPT-003-IMAGE-RECOVERY-001"
RUNTIME_BASE = Path("var/local-v1-lv1-003-o4-runtime")
CONSUMPTION_RECEIPT = "attempt-003-image-recovery-001-consumed.json"
CONSUMPTION_RECEIPT_SIZE = 336
CONSUMPTION_RECEIPT_DIGEST = (
    "sha256:df7ce1a69c5fc3b27011f788f846bb5b385ed6f3d348ceb6c78d12de9366ca3c"
)
MAX_READ_OUTPUT_BYTES = 1_048_576

CANDIDATE_PATH_ALLOWLIST = [
    AUTHORIZATION_JSON.as_posix(),
    AUTHORIZATION_DOCUMENT.as_posix(),
    RECOVERY_CLOSURE_JSON.as_posix(),
    RECOVERY_CLOSURE_DOCUMENT.as_posix(),
    "scripts/local_v1_lv1_003_o4_image_recovery.py",
    "tests/test_local_v1_lv1_003_o4_image_recovery.py",
]
O4_AUTHORITY_FIELDS = {
    "producer_code_authorized",
    "docker_lifecycle_authorized",
    "live_hermes_execution_authorized",
    "model_provider_access_authorized",
    "o4_evidence_execution_authorized",
    "credential_custody_authorized",
    "runner_lifecycle_authority",
    "arbitrary_host_control_authorized",
    "generic_process_control_authorized",
    "shell_execution_authorized",
    "docker_socket_authorized",
    "network_non_bypass_claimed",
    "filesystem_non_bypass_claimed",
    "new_governed_power_authorized",
    "new_governed_tool",
    "release_allowed",
    "promotion_allowed",
    "production_authorized",
    "uat_complete",
}
RECOVERY_AUTHORITY = {
    "durable_consumption_receipt_authorized": False,
    "recovery_inspection_authorized": False,
    "exact_image_removal_authorized": False,
    "force_image_removal_authorized": False,
    "image_prune_authorized": False,
    "tag_based_image_removal_authorized": False,
    "project_container_mutation_authorized": False,
    "project_volume_mutation_authorized": False,
    "project_network_mutation_authorized": False,
    "arbitrary_docker_command_authorized": False,
}


@dataclass(frozen=True)
class ImageTarget:
    service: str
    reference: str
    image_id: str


IMAGE_TARGETS = (
    ImageTarget(
        "ithildin-api",
        "ithildin/api-o4:6460809b",
        "sha256:19dc658884e9298b7966e5fb10c80874afaa33956e565b55dd0a30e8a02bd5d6",
    ),
    ImageTarget(
        "ithildin-ui",
        "ithildin/ui-o4:6460809b",
        "sha256:4b530eb0fc350c433089d88ddd75d03042e633a5b23a0fdeaaeb77c58f75b6b7",
    ),
    ImageTarget(
        "ithildin-node",
        "ithildin/node-o4:6460809b",
        "sha256:0d85000f6172508554524f276d4051170e53a6c3fc79cbc5dc1b0c051b682c81",
    ),
)


class RecoveryError(RuntimeError):
    """Stable, secret-free recovery refusal."""

    def __init__(self, code: str) -> None:
        if re.fullmatch(r"[a-z0-9_]{3,80}", code) is None:
            raise ValueError("unsafe recovery error code")
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str


class Executor(Protocol):
    def read(self, command: tuple[str, ...]) -> CommandResult: ...

    def remove(self, command: tuple[str, ...]) -> CommandResult: ...


@dataclass(frozen=True)
class RecoveryPlan:
    docker_config: Path

    @property
    def prefix(self) -> tuple[str, ...]:
        return ("docker", "--config", str(self.docker_config))

    def resource_query(self, resource: str) -> tuple[str, ...]:
        if resource not in {"container", "volume", "network"}:
            raise RecoveryError("resource_query_not_allowed")
        noun = "ps" if resource == "container" else resource
        command = [*self.prefix, noun]
        if resource == "container":
            command.extend(("--all", "--quiet"))
        else:
            command.extend(("ls", "--quiet"))
        command.extend(
            ("--filter", f"label=com.docker.compose.project={PROJECT}")
        )
        return tuple(command)

    def image_query(self, reference: str) -> tuple[str, ...]:
        if reference not in {
            HERMES_REFERENCE,
            *(target.reference for target in IMAGE_TARGETS),
        }:
            raise RecoveryError("image_query_not_allowed")
        return (
            *self.prefix,
            "image",
            "ls",
            "--quiet",
            "--no-trunc",
            "--filter",
            f"reference={reference}",
        )

    def image_inspect(self, image_id: str) -> tuple[str, ...]:
        if image_id not in {target.image_id for target in IMAGE_TARGETS}:
            raise RecoveryError("image_inspect_not_allowed")
        return (
            *self.prefix,
            "image",
            "inspect",
            "--format",
            "{{json .}}",
            image_id,
        )

    def ancestor_containers(self, image_id: str) -> tuple[str, ...]:
        if image_id not in {target.image_id for target in IMAGE_TARGETS}:
            raise RecoveryError("ancestor_query_not_allowed")
        return (
            *self.prefix,
            "ps",
            "--all",
            "--quiet",
            "--filter",
            f"ancestor={image_id}",
        )

    def removal(self) -> tuple[str, ...]:
        return (
            *self.prefix,
            "image",
            "rm",
            *(target.image_id for target in IMAGE_TARGETS),
        )

    def allowed_reads(self) -> frozenset[tuple[str, ...]]:
        commands = {
            *(self.resource_query(resource) for resource in ("container", "volume", "network")),
            self.image_query(HERMES_REFERENCE),
        }
        for target in IMAGE_TARGETS:
            commands.add(self.image_query(target.reference))
            commands.add(self.image_inspect(target.image_id))
            commands.add(self.ancestor_containers(target.image_id))
        return frozenset(commands)


class SubprocessExecutor:
    """Closed Docker adapter for the exact recovery command set."""

    def __init__(self, environment: dict[str, str], plan: RecoveryPlan) -> None:
        self._environment = dict(environment)
        self._plan = plan
        self._mutation_calls = 0

    def read(self, command: tuple[str, ...]) -> CommandResult:
        if command not in self._plan.allowed_reads():
            raise RecoveryError("docker_read_command_not_allowed")
        try:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                check=False,
                timeout=60.0,
                env=self._environment,
            )
        except (OSError, UnicodeError, subprocess.TimeoutExpired) as exc:
            raise RecoveryError("docker_read_unavailable") from exc
        if len(completed.stdout.encode("utf-8")) > MAX_READ_OUTPUT_BYTES:
            raise RecoveryError("docker_read_output_too_large")
        return CommandResult(completed.returncode, completed.stdout)

    def remove(self, command: tuple[str, ...]) -> CommandResult:
        if command != self._plan.removal() or self._mutation_calls != 0:
            raise RecoveryError("docker_mutation_command_not_allowed")
        self._mutation_calls += 1
        try:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=120.0,
                env=self._environment,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RecoveryError("docker_remove_unavailable") from exc
        return CommandResult(completed.returncode, "")


def _digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json_record(
    repo_root: Path,
    path: Path,
    label: str,
    failures: list[str],
) -> dict[str, Any]:
    try:
        raw = json.loads((repo_root / path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        failures.append(f"image recovery {label} is unavailable or invalid")
        return {}
    if not isinstance(raw, dict):
        failures.append(f"image recovery {label} is not an object")
        return {}
    return cast(dict[str, Any], raw)


def _validate_authorization(
    repo_root: Path,
    authorization: dict[str, Any],
    failures: list[str],
) -> None:
    for path, digest, label in (
        (AUTHORIZATION_JSON, AUTHORIZATION_JSON_DIGEST, "authorization JSON"),
        (
            AUTHORIZATION_DOCUMENT,
            AUTHORIZATION_DOCUMENT_DIGEST,
            "authorization document",
        ),
        (
            ATTEMPT_003_CLOSURE_JSON,
            ATTEMPT_003_CLOSURE_JSON_DIGEST,
            "Attempt 003 closure JSON",
        ),
        (
            ATTEMPT_003_CLOSURE_DOCUMENT,
            ATTEMPT_003_CLOSURE_DOCUMENT_DIGEST,
            "Attempt 003 closure document",
        ),
        (
            RECOVERY_CLOSURE_JSON,
            RECOVERY_CLOSURE_JSON_DIGEST,
            "closure JSON",
        ),
        (
            RECOVERY_CLOSURE_DOCUMENT,
            RECOVERY_CLOSURE_DOCUMENT_DIGEST,
            "closure document",
        ),
    ):
        try:
            observed = _digest(repo_root / path)
        except OSError:
            failures.append(f"image recovery {label} is unavailable")
            continue
        if observed != digest:
            failures.append(f"image recovery {label} digest is not exact")
    expected_scalars = {
        "schema_version": "1",
        "record_type": "local_v1_lv1_003_o4_image_recovery_authorization",
        "record_status": "ATTEMPT_003_IMAGE_RECOVERY_CLOSED_NO_AUTHORITY",
        "ticket_id": "LV1-003",
        "outcome_id": "O4",
        "recovery_id": RECOVERY_ID,
        "authorization_origin_parent_commit": AUTHORIZATION_ORIGIN_COMMIT,
        "authorization_origin_parent_tree": AUTHORIZATION_ORIGIN_TREE,
        "recovery_candidate_commit": PARENT_COMMIT,
        "recovery_candidate_tree": PARENT_TREE,
        "attempt_003_closure_json": ATTEMPT_003_CLOSURE_JSON.as_posix(),
        "attempt_003_closure_json_sha256": ATTEMPT_003_CLOSURE_JSON_DIGEST,
        "attempt_003_closure_document": ATTEMPT_003_CLOSURE_DOCUMENT.as_posix(),
        "attempt_003_closure_document_sha256": (
            ATTEMPT_003_CLOSURE_DOCUMENT_DIGEST
        ),
        "recovery_closure_json": RECOVERY_CLOSURE_JSON.as_posix(),
        "recovery_closure_json_sha256": RECOVERY_CLOSURE_JSON_DIGEST,
        "recovery_closure_document": RECOVERY_CLOSURE_DOCUMENT.as_posix(),
        "recovery_closure_document_sha256": RECOVERY_CLOSURE_DOCUMENT_DIGEST,
        "operator_command": f"make {RUN_TARGET}",
        "module_command": MODULE_COMMAND,
        "recovery_attempt_budget": 0,
        "retry_authorized": False,
    }
    for key, expected in expected_scalars.items():
        if authorization.get(key) != expected:
            failures.append(f"image recovery authorization {key} is not exact")
    binding = authorization.get("candidate_binding")
    if binding != {
        "mode": "dynamic_clean_single_parent_immediate_child",
        "candidate_parent_commit": PARENT_COMMIT,
        "candidate_parent_tree": PARENT_TREE,
        "candidate_commit": None,
        "candidate_tree": None,
        "changed_paths_must_equal_allowlist": True,
        "future_self_reference_claimed": False,
    }:
        failures.append("image recovery candidate binding is not exact")
    if authorization.get("candidate_path_allowlist") != CANDIDATE_PATH_ALLOWLIST:
        failures.append("image recovery candidate path allowlist is not exact")
    if authorization.get("recovery_authority") != RECOVERY_AUTHORITY:
        failures.append("image recovery authority is not exact")
    if authorization.get("recovery_outcome") != {
        "exit_code": 0,
        "stable_output": "image_recovery_status: completed",
        "exact_image_removal_succeeded": True,
        "o4_execution_succeeded": False,
        "successful_o4_evidence_created": False,
    }:
        failures.append("image recovery outcome is not exact")
    if authorization.get("durable_consumption_receipt") != {
        "path": (RUNTIME_BASE / CONSUMPTION_RECEIPT).as_posix(),
        "runtime_base_mode": "0700",
        "runtime_base_entries": [CONSUMPTION_RECEIPT],
        "receipt_mode": "0600",
        "receipt_size_bytes": CONSUMPTION_RECEIPT_SIZE,
        "receipt_sha256": CONSUMPTION_RECEIPT_DIGEST,
        "receipt_candidate_commit": PARENT_COMMIT,
        "receipt_candidate_tree": PARENT_TREE,
        "receipt_status": "consumed_before_docker_inspection",
        "receipt_retry_authorized": False,
        "receipt_retained": True,
        "receipt_removal_authorized": False,
    }:
        failures.append("image recovery durable receipt record is not exact")
    if authorization.get("point_in_time_post_recovery_observation") != {
        "three_exact_image_ids_absent": True,
        "four_exact_image_references_absent": True,
        "exact_project_label_container_count": 0,
        "exact_project_label_volume_count": 0,
        "exact_project_label_network_count": 0,
        "ongoing_live_truth_claimed": False,
        "general_docker_absence_claimed": False,
        "docker_non_bypass_claimed": False,
    }:
        failures.append("image recovery point-in-time observation is not exact")
    o4_authority = authorization.get("o4_authority")
    if (
        not isinstance(o4_authority, dict)
        or set(o4_authority) != O4_AUTHORITY_FIELDS
        or any(value is not False for value in o4_authority.values())
    ):
        failures.append("image recovery must keep all 19 O4 authority fields false")
    document = repo_root / AUTHORIZATION_DOCUMENT
    try:
        normalized = " ".join(document.read_text(encoding="utf-8").split())
    except (OSError, UnicodeError):
        failures.append("image recovery authorization document is unavailable")
        return
    for phrase in (
        "Status: `ATTEMPT_003_IMAGE_RECOVERY_CLOSED_NO_AUTHORITY`",
        "not Attempt 004",
        PARENT_COMMIT,
        PARENT_TREE,
        AUTHORIZATION_ORIGIN_COMMIT,
        AUTHORIZATION_ORIGIN_TREE,
        ATTEMPT_003_CLOSURE_JSON_DIGEST,
        ATTEMPT_003_CLOSURE_DOCUMENT_DIGEST,
        RECOVERY_CLOSURE_JSON_DIGEST,
        RECOVERY_CLOSURE_DOCUMENT_DIGEST,
        "exact six-path closure allowlist",
        f"make {RUN_TARGET}",
        MODULE_COMMAND,
        CONSUMPTION_RECEIPT_DIGEST,
        "The recovery budget is zero, retry is false, and every recovery authority is false",
        "All 19 O4 authority fields remain false",
        CONSUMPTION_RECEIPT,
        "consumed_before_docker_inspection",
        "Receipt deletion or mutation is not authorized",
        "point-in-time postconditions only",
        "refuse before receipt mutation, Docker inspection, or Docker mutation",
    ):
        if phrase not in normalized:
            failures.append(
                f"image recovery authorization document is missing phrase: {phrase}"
            )


def _validate_recovery_closure(
    repo_root: Path,
    closure: dict[str, Any],
    failures: list[str],
) -> None:
    expected_scalars = {
        "schema_version": "1",
        "record_type": "local_v1_lv1_003_o4_image_recovery_closure",
        "record_status": "RECOVERY_COMPLETED_EXACT_IMAGE_REMOVAL_CLOSED",
        "ticket_id": "LV1-003",
        "outcome_id": "O4",
        "recovery_id": RECOVERY_ID,
        "recovery_candidate_commit": PARENT_COMMIT,
        "recovery_candidate_tree": PARENT_TREE,
        "operator_command": f"make {RUN_TARGET}",
        "module_command": MODULE_COMMAND,
        "exit_code": 0,
        "stable_output": "image_recovery_status: completed",
        "recovery_attempt_budget": 0,
        "retry_authorized": False,
    }
    for key, expected in expected_scalars.items():
        if closure.get(key) != expected:
            failures.append(f"image recovery closure {key} is not exact")
    if closure.get("tracked_closure_scope") != CANDIDATE_PATH_ALLOWLIST:
        failures.append("image recovery closure scope is not exact")
    if closure.get("recovery_authority") != RECOVERY_AUTHORITY:
        failures.append("image recovery closure authority is not exact")
    o4_authority = closure.get("o4_authority")
    if (
        not isinstance(o4_authority, dict)
        or set(o4_authority) != O4_AUTHORITY_FIELDS
        or any(value is not False for value in o4_authority.values())
    ):
        failures.append("image recovery closure must keep all 19 O4 fields false")
    binding = closure.get("candidate_binding")
    if binding != {
        "mode": "dynamic_clean_single_parent_immediate_child",
        "candidate_parent_commit": PARENT_COMMIT,
        "candidate_parent_tree": PARENT_TREE,
        "candidate_commit": None,
        "candidate_tree": None,
        "future_self_reference_claimed": False,
    }:
        failures.append("image recovery closure candidate binding is not exact")
    receipt = closure.get("durable_consumption_receipt")
    if (
        not isinstance(receipt, dict)
        or receipt.get("path") != (RUNTIME_BASE / CONSUMPTION_RECEIPT).as_posix()
        or receipt.get("runtime_base_mode") != "0700"
        or receipt.get("runtime_base_entries") != [CONSUMPTION_RECEIPT]
        or receipt.get("receipt_mode") != "0600"
        or receipt.get("receipt_size_bytes") != CONSUMPTION_RECEIPT_SIZE
        or receipt.get("receipt_sha256") != CONSUMPTION_RECEIPT_DIGEST
        or receipt.get("receipt_candidate_commit") != PARENT_COMMIT
        or receipt.get("receipt_candidate_tree") != PARENT_TREE
        or receipt.get("receipt_status") != "consumed_before_docker_inspection"
        or receipt.get("receipt_retry_authorized") is not False
        or receipt.get("receipt_retained") is not True
        or receipt.get("receipt_removal_authorized") is not False
    ):
        failures.append("image recovery closure durable receipt is not exact")
    observation = closure.get("point_in_time_post_recovery_observation")
    if (
        not isinstance(observation, dict)
        or observation.get("image_ids_absent")
        != [target.image_id for target in IMAGE_TARGETS]
        or observation.get("image_references_absent")
        != [*(target.reference for target in IMAGE_TARGETS), HERMES_REFERENCE]
        or observation.get("compose_project") != PROJECT
        or observation.get("exact_project_label_containers") != 0
        or observation.get("exact_project_label_volumes") != 0
        or observation.get("exact_project_label_networks") != 0
        or observation.get("ongoing_live_truth_claimed") is not False
        or observation.get("general_docker_absence_claimed") is not False
        or observation.get("docker_non_bypass_claimed") is not False
    ):
        failures.append("image recovery closure point-in-time observation is not exact")
    try:
        normalized = " ".join(
            (repo_root / RECOVERY_CLOSURE_DOCUMENT)
            .read_text(encoding="utf-8")
            .split()
        )
    except (OSError, UnicodeError):
        failures.append("image recovery closure document is unavailable")
        return
    for phrase in (
        "Status: `RECOVERY_COMPLETED_EXACT_IMAGE_REMOVAL_CLOSED`",
        PARENT_COMMIT,
        PARENT_TREE,
        "image_recovery_status: completed",
        CONSUMPTION_RECEIPT,
        CONSUMPTION_RECEIPT_DIGEST,
        "point-in-time postconditions",
        "not ongoing live truth",
        "whose committed diff is exactly:",
        "The recovery budget is zero",
        "all 19 O4 authority fields remain false",
        "governed tool count remains 24",
    ):
        if phrase not in normalized:
            failures.append(
                f"image recovery closure document is missing phrase: {phrase}"
            )


def _git(repo_root: Path, arguments: tuple[str, ...], failures: list[str]) -> str:
    try:
        result = subprocess.run(
            ("git", "-C", str(repo_root), *arguments),
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        failures.append("image recovery git inspection is unavailable")
        return ""
    if result.returncode != 0:
        failures.append("image recovery git inspection failed")
        return ""
    return result.stdout.strip()


def _target_body(makefile: str, target: str) -> str:
    lines = makefile.splitlines()
    for index, line in enumerate(lines):
        if line == f"{target}:":
            body: list[str] = []
            for candidate in lines[index + 1 :]:
                if candidate and not candidate.startswith(("\t", " ")):
                    break
                body.append(candidate)
            return "\n".join(body).strip()
    return ""


def _validate_makefile(repo_root: Path, failures: list[str]) -> None:
    try:
        makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        failures.append("image recovery Makefile is unavailable")
        return
    if sum(line == f"{RUN_TARGET}:" for line in makefile.splitlines()) != 1:
        failures.append("image recovery Make target is not unique")
    if _target_body(makefile, RUN_TARGET) != MODULE_COMMAND:
        failures.append("image recovery Make target body is not exact")
    occurrences = sum(RUN_TARGET in line for line in makefile.splitlines())
    if occurrences != 2:
        failures.append("image recovery Make target occurrence count is not exact")
    for forbidden_parent in (
        "release-check",
        "local-v1-milestone-check",
        "local-v1-lv1-003-o4-producer-static-check",
        "local-v1-lv1-003-o4-execution-authorization-check",
    ):
        if RUN_TARGET in _target_body(makefile, forbidden_parent):
            failures.append(
                f"image recovery target is wired into forbidden target: {forbidden_parent}"
            )


def build_report(repo_root: Path = ROOT) -> dict[str, Any]:
    failures: list[str] = []
    authorization = _load_json_record(
        repo_root,
        AUTHORIZATION_JSON,
        "authorization JSON",
        failures,
    )
    closure = _load_json_record(
        repo_root,
        RECOVERY_CLOSURE_JSON,
        "closure JSON",
        failures,
    )
    _validate_authorization(repo_root, authorization, failures)
    _validate_recovery_closure(repo_root, closure, failures)
    _validate_makefile(repo_root, failures)
    _validate_consumption_receipt(repo_root, failures)
    head = _git(repo_root, ("rev-parse", "HEAD"), failures)
    tree = _git(repo_root, ("show", "-s", "--format=%T", "HEAD"), failures)
    parents = _git(repo_root, ("show", "-s", "--format=%P", "HEAD"), failures).split()
    if parents != [PARENT_COMMIT]:
        failures.append(
            "image recovery checkout is not a single immediate child of the parent"
        )
    parent_tree = _git(
        repo_root,
        ("show", "-s", "--format=%T", PARENT_COMMIT),
        failures,
    )
    if parent_tree != PARENT_TREE:
        failures.append("image recovery parent tree is not exact")
    status = _git(
        repo_root,
        ("status", "--porcelain=v1", "--untracked-files=all"),
        failures,
    )
    if status:
        failures.append("image recovery checkout is not clean")
    changed = _git(
        repo_root,
        ("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"),
        failures,
    ).splitlines()
    if changed != CANDIDATE_PATH_ALLOWLIST:
        failures.append("image recovery changed paths are not the exact allowlist")
    valid = not failures
    return {
        "schema_version": "1",
        "valid": valid,
        "failures": failures,
        "record_status": authorization.get("record_status"),
        "candidate_commit": head if valid else None,
        "candidate_tree": tree if valid else None,
        "recovery_attempt_budget": 0,
        "retry_authorized": False,
        "recovery_inspection_authorized": False,
        "exact_image_removal_authorized": False,
        "o4_authority": {field: False for field in sorted(O4_AUTHORITY_FIELDS)},
        "release_allowed": False,
        "uat_complete": False,
    }


def assert_recovery_authorized(repo_root: Path = ROOT) -> None:
    report = build_report(repo_root)
    if (
        report["valid"] is not True
        or report["recovery_attempt_budget"] != 1
        or report["recovery_inspection_authorized"] is not True
        or report["exact_image_removal_authorized"] is not True
    ):
        raise RecoveryError("image_recovery_not_authorized")


def _directory_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )


def _same_inode(first: os.stat_result, second: os.stat_result) -> bool:
    return first.st_dev == second.st_dev and first.st_ino == second.st_ino


def _owned_directory(details: os.stat_result, mode: int | None) -> bool:
    return (
        stat.S_ISDIR(details.st_mode)
        and details.st_uid == os.geteuid()
        and details.st_gid == os.getegid()
        and (mode is None or stat.S_IMODE(details.st_mode) == mode)
    )


def _open_owned_directory_at(
    parent: int,
    name: str,
    *,
    mode: int | None,
) -> int:
    descriptor = -1
    try:
        before = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if not _owned_directory(before, mode):
            raise RecoveryError("image_recovery_runtime_posture_invalid")
        descriptor = os.open(name, _directory_flags(), dir_fd=parent)
        opened = os.fstat(descriptor)
        if not _same_inode(before, opened) or not _owned_directory(opened, mode):
            raise RecoveryError("image_recovery_runtime_posture_invalid")
        return descriptor
    except RecoveryError:
        if descriptor >= 0:
            os.close(descriptor)
        raise
    except OSError as exc:
        if descriptor >= 0:
            os.close(descriptor)
        raise RecoveryError("image_recovery_runtime_unavailable") from exc


def _open_runtime_base(repo_root: Path) -> tuple[int, int, int]:
    repository = var = runtime = -1
    try:
        before = os.stat(repo_root, follow_symlinks=False)
        if not _owned_directory(before, None):
            raise RecoveryError("image_recovery_repository_posture_invalid")
        repository = os.open(repo_root, _directory_flags())
        opened = os.fstat(repository)
        if not _same_inode(before, opened) or not _owned_directory(opened, None):
            raise RecoveryError("image_recovery_repository_posture_invalid")
        var = _open_owned_directory_at(repository, "var", mode=None)
        runtime = _open_owned_directory_at(
            var,
            RUNTIME_BASE.name,
            mode=0o700,
        )
        return repository, var, runtime
    except BaseException:
        for descriptor in (runtime, var, repository):
            if descriptor >= 0:
                os.close(descriptor)
        raise


def _consumption_receipt_bytes(candidate_commit: str, candidate_tree: str) -> bytes:
    if (
        re.fullmatch(r"[0-9a-f]{40}", candidate_commit) is None
        or re.fullmatch(r"[0-9a-f]{40}", candidate_tree) is None
    ):
        raise RecoveryError("image_recovery_candidate_identity_invalid")
    return (
        json.dumps(
            {
                "schema_version": "1",
                "record_type": "local_v1_lv1_003_o4_image_recovery_consumption",
                "recovery_id": RECOVERY_ID,
                "candidate_commit": candidate_commit,
                "candidate_tree": candidate_tree,
                "status": "consumed_before_docker_inspection",
                "retry_authorized": False,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _validate_consumption_receipt(
    repo_root: Path,
    failures: list[str],
) -> None:
    repository = var = runtime = receipt = -1
    try:
        repository, var, runtime = _open_runtime_base(repo_root)
        if sorted(os.listdir(runtime)) != [CONSUMPTION_RECEIPT]:
            failures.append("image recovery retained receipt is not the sole entry")
            return
        before = os.stat(
            CONSUMPTION_RECEIPT,
            dir_fd=runtime,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != 0o600
            or before.st_uid != os.geteuid()
            or before.st_gid != os.getegid()
            or before.st_size != CONSUMPTION_RECEIPT_SIZE
        ):
            failures.append("image recovery retained receipt posture is not exact")
            return
        flags = (
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        receipt = os.open(CONSUMPTION_RECEIPT, flags, dir_fd=runtime)
        opened = os.fstat(receipt)
        if (
            not _same_inode(before, opened)
            or not stat.S_ISREG(opened.st_mode)
            or stat.S_IMODE(opened.st_mode) != 0o600
            or opened.st_uid != os.geteuid()
            or opened.st_gid != os.getegid()
            or opened.st_size != CONSUMPTION_RECEIPT_SIZE
        ):
            failures.append("image recovery retained receipt identity is not exact")
            return
        payload = b""
        while len(payload) <= CONSUMPTION_RECEIPT_SIZE:
            chunk = os.read(receipt, CONSUMPTION_RECEIPT_SIZE + 1 - len(payload))
            if not chunk:
                break
            payload += chunk
        after = os.fstat(receipt)
        expected = _consumption_receipt_bytes(PARENT_COMMIT, PARENT_TREE)
        if (
            not _same_inode(opened, after)
            or after.st_size != CONSUMPTION_RECEIPT_SIZE
            or len(payload) != CONSUMPTION_RECEIPT_SIZE
            or payload != expected
            or "sha256:" + hashlib.sha256(payload).hexdigest()
            != CONSUMPTION_RECEIPT_DIGEST
        ):
            failures.append("image recovery retained receipt content is not exact")
    except RecoveryError:
        failures.append("image recovery retained receipt runtime posture is not exact")
    except (OSError, UnicodeError):
        failures.append("image recovery retained receipt is unavailable")
    finally:
        for descriptor in (receipt, runtime, var, repository):
            if descriptor >= 0:
                os.close(descriptor)


def consume_recovery_budget(
    repo_root: Path,
    *,
    candidate_commit: str,
    candidate_tree: str,
) -> None:
    repository = var = runtime = receipt = -1
    created = False
    try:
        repository, var, runtime = _open_runtime_base(repo_root)
        try:
            entries = os.listdir(runtime)
        except OSError as exc:
            raise RecoveryError("image_recovery_runtime_unavailable") from exc
        if entries:
            raise RecoveryError("image_recovery_already_consumed")
        flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        try:
            receipt = os.open(CONSUMPTION_RECEIPT, flags, 0o600, dir_fd=runtime)
            created = True
        except FileExistsError as exc:
            raise RecoveryError("image_recovery_already_consumed") from exc
        except OSError as exc:
            raise RecoveryError("image_recovery_consumption_unavailable") from exc
        payload = _consumption_receipt_bytes(candidate_commit, candidate_tree)
        written = 0
        while written < len(payload):
            count = os.write(receipt, payload[written:])
            if count <= 0:
                raise RecoveryError("image_recovery_consumption_unavailable")
            written += count
        os.fsync(receipt)
        details = os.fstat(receipt)
        if (
            not stat.S_ISREG(details.st_mode)
            or stat.S_IMODE(details.st_mode) != 0o600
            or details.st_uid != os.geteuid()
            or details.st_gid != os.getegid()
            or details.st_size != len(payload)
        ):
            raise RecoveryError("image_recovery_consumption_invalid")
        os.close(receipt)
        receipt = -1
        os.fsync(runtime)
        if sorted(os.listdir(runtime)) != [CONSUMPTION_RECEIPT]:
            raise RecoveryError("image_recovery_consumption_invalid")
    except RecoveryError:
        raise
    except (OSError, UnicodeError) as exc:
        code = (
            "image_recovery_consumption_unavailable"
            if created
            else "image_recovery_runtime_unavailable"
        )
        raise RecoveryError(code) from exc
    finally:
        for descriptor in (receipt, runtime, var, repository):
            if descriptor >= 0:
                os.close(descriptor)


def _require_empty_success(result: CommandResult, code: str) -> None:
    if result.returncode != 0 or result.stdout.strip():
        raise RecoveryError(code)


def _parse_image(result: CommandResult, target: ImageTarget) -> None:
    if result.returncode != 0:
        raise RecoveryError("image_recovery_inspect_failed")
    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RecoveryError("image_recovery_inspect_invalid") from exc
    if not isinstance(raw, dict):
        raise RecoveryError("image_recovery_inspect_invalid")
    labels = raw.get("Config", {}).get("Labels") if isinstance(raw.get("Config"), dict) else None
    expected_labels = {
        "com.docker.compose.project": PROJECT,
        "com.docker.compose.service": target.service,
        "com.docker.compose.version": COMPOSE_VERSION,
    }
    if (
        raw.get("Id") != target.image_id
        or raw.get("RepoTags") != [target.reference]
        or raw.get("Os") != PLATFORM_OS
        or raw.get("Architecture") != PLATFORM_ARCHITECTURE
        or not isinstance(labels, dict)
        or any(labels.get(key) != value for key, value in expected_labels.items())
    ):
        raise RecoveryError("image_recovery_metadata_drift")


def _verify_project_and_hermes_absent(
    executor: Executor,
    plan: RecoveryPlan,
) -> None:
    for resource in ("container", "volume", "network"):
        _require_empty_success(
            executor.read(plan.resource_query(resource)),
            "image_recovery_project_residue",
        )
    _require_empty_success(
        executor.read(plan.image_query(HERMES_REFERENCE)),
        "image_recovery_hermes_present",
    )


def _prevalidate(executor: Executor, plan: RecoveryPlan) -> None:
    _verify_project_and_hermes_absent(executor, plan)
    for target in IMAGE_TARGETS:
        query = executor.read(plan.image_query(target.reference))
        if query.returncode != 0 or query.stdout.split() != [target.image_id]:
            raise RecoveryError("image_recovery_reference_drift")
        _parse_image(executor.read(plan.image_inspect(target.image_id)), target)
        _require_empty_success(
            executor.read(plan.ancestor_containers(target.image_id)),
            "image_recovery_container_reference_present",
        )


def _postverify(executor: Executor, plan: RecoveryPlan) -> None:
    for target in IMAGE_TARGETS:
        inspected = executor.read(plan.image_inspect(target.image_id))
        if inspected.returncode == 0 or inspected.stdout.strip():
            raise RecoveryError("image_recovery_image_id_still_present")
        _require_empty_success(
            executor.read(plan.image_query(target.reference)),
            "image_recovery_reference_still_present",
        )
    _verify_project_and_hermes_absent(executor, plan)


def execute_recovery(executor: Executor, plan: RecoveryPlan) -> None:
    _prevalidate(executor, plan)
    removal: CommandResult | None = None
    removal_error: BaseException | None = None
    try:
        removal = executor.remove(plan.removal())
    except BaseException as exc:
        removal_error = exc
    post_error: BaseException | None = None
    try:
        _postverify(executor, plan)
    except BaseException as exc:
        post_error = exc
    if removal_error is not None:
        raise RecoveryError("image_recovery_remove_ambiguous") from removal_error
    if removal is None or removal.returncode != 0 or removal.stdout:
        raise RecoveryError("image_recovery_remove_failed")
    if post_error is not None:
        if isinstance(post_error, RecoveryError):
            raise post_error
        raise RecoveryError("image_recovery_postverify_unavailable") from post_error


def _write_empty_docker_config(root: Path) -> Path:
    descriptor = -1
    try:
        root.chmod(0o700)
        config = root / "docker-config"
        config.mkdir(mode=0o700)
        payload = config / "config.json"
        descriptor = os.open(
            payload,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0),
            0o600,
        )
        content = b'{"auths":{},"credHelpers":{}}\n'
        written = 0
        while written < len(content):
            count = os.write(descriptor, content[written:])
            if count <= 0:
                raise RecoveryError("image_recovery_docker_config_unavailable")
            written += count
        os.fsync(descriptor)
        details = os.fstat(descriptor)
        if (
            not stat.S_ISREG(details.st_mode)
            or stat.S_IMODE(details.st_mode) != 0o600
            or details.st_uid != os.geteuid()
            or details.st_gid != os.getegid()
        ):
            raise RecoveryError("image_recovery_docker_config_invalid")
        return config
    except RecoveryError:
        raise
    except (OSError, UnicodeError) as exc:
        raise RecoveryError("image_recovery_docker_config_unavailable") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def run_live_recovery(environment: dict[str, str] | None = None) -> None:
    report = build_report(ROOT)
    if (
        report["valid"] is not True
        or not isinstance(report["candidate_commit"], str)
        or not isinstance(report["candidate_tree"], str)
        or report["recovery_attempt_budget"] != 1
        or report["recovery_inspection_authorized"] is not True
        or report["exact_image_removal_authorized"] is not True
    ):
        raise RecoveryError("image_recovery_not_authorized")
    consume_recovery_budget(
        ROOT,
        candidate_commit=report["candidate_commit"],
        candidate_tree=report["candidate_tree"],
    )
    source_environment = dict(os.environ if environment is None else environment)
    try:
        producer._reject_ambient_authority(source_environment)  # noqa: SLF001
        docker_host = producer._prove_local_docker_socket()  # noqa: SLF001
    except producer.ProducerError as exc:
        raise RecoveryError(exc.code) from exc
    try:
        with tempfile.TemporaryDirectory(
            prefix="ithildin-o4-image-recovery-"
        ) as temporary:
            config = _write_empty_docker_config(Path(temporary))
            plan = RecoveryPlan(config)
            isolated_environment = {
                "PATH": source_environment.get("PATH", "/usr/bin:/bin"),
                "DOCKER_HOST": docker_host,
                "DOCKER_CONFIG": str(config),
            }
            execute_recovery(SubprocessExecutor(isolated_environment, plan), plan)
    except RecoveryError:
        raise
    except (OSError, UnicodeError, subprocess.SubprocessError) as exc:
        raise RecoveryError("image_recovery_local_runtime_unavailable") from exc


def render_report(report: dict[str, Any]) -> str:
    return "\n".join(
        (
            "LV1-003 O4 image recovery authorization",
            f"valid: {str(report['valid']).lower()}",
            f"record_status: {report['record_status']}",
            f"recovery_attempt_budget: {report['recovery_attempt_budget']}",
            f"retry_authorized: {str(report['retry_authorized']).lower()}",
            "recovery_inspection_authorized: "
            f"{str(report['recovery_inspection_authorized']).lower()}",
            "exact_image_removal_authorized: "
            f"{str(report['exact_image_removal_authorized']).lower()}",
            f"release_allowed: {str(report['release_allowed']).lower()}",
            f"uat_complete: {str(report['uat_complete']).lower()}",
            *(f"failure: {failure}" for failure in report["failures"]),
        )
    )


def main(arguments: list[str] | None = None) -> int:
    effective = sys.argv[1:] if arguments is None else arguments
    if effective:
        print("image_recovery_error: arguments_not_allowed")
        return 2
    try:
        run_live_recovery()
    except RecoveryError as exc:
        print(f"image_recovery_error: {exc.code}")
        return 1
    except (OSError, UnicodeError, subprocess.SubprocessError):
        print("image_recovery_error: image_recovery_local_runtime_unavailable")
        return 1
    except KeyboardInterrupt:
        print("image_recovery_error: image_recovery_interrupted")
        return 1
    except Exception:
        print("image_recovery_error: image_recovery_unexpected_failure")
        return 1
    print("image_recovery_status: completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

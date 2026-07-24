"""Closed evidence contract shared by the Local-v1 Node journey and its checker."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from ithildin_api.node_configuration import (
    CONFIGURATION_STATE_STORED_CURRENT_NOT_ENFORCED,
)
from ithildin_api.nodes import NODE_OBSERVED_STATE_CONNECTED
from ithildin_schemas import JsonObject, JsonValue

SCHEMA_VERSION = "ithildin.local-v1-node-journey.evidence.v1"
REPORT_JSON = "local-v1-node-journey.json"
REPORT_MARKDOWN = "local-v1-node-journey.md"
MAX_JOURNEY_DURATION = timedelta(minutes=20)
MAX_EVIDENCE_AGE = timedelta(hours=24)
MAX_FUTURE_SKEW = timedelta(minutes=2)

NONCLAIMS = [
    "No governed tool call or real agent mission was exercised.",
    "No runner or model-provider health was established.",
    "Stored configuration was acknowledged as stored_not_enforced, not enforced.",
    "No restart, replay, partition, stale-configuration, or rollback behavior was exercised.",
    "No production identity, PostgreSQL, release, promotion, or UAT authority was established.",
    "Candidate commit and cleanliness are observations, not authorization or approval.",
]

_RUN_ID = re.compile(r"^([0-9]{8}T[0-9]{6}Z)-[0-9a-f]{8}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_NODE_ID = re.compile(r"^node_[0-9a-f]{32}$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_SECRET_KEY = re.compile(
    r"(?:^|_)(?:admin_token|api_key|authorization|credential|enrollment_code|"
    r"password|private_key|secret|signature|token)(?:$|_)",
    re.IGNORECASE,
)
_SECRET_TEXT = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?im)^ITHILDIN_ADMIN_TOKEN=(?!\[redacted\])\S+"),
    re.compile(r'"enrollment_code"\s*:\s*"(?!\[redacted\])'),
    re.compile(r'"private_key"\s*:\s*"(?!\[redacted\])'),
    re.compile(r"dev-admin-token-change-me"),
)


class EvidenceValidationError(RuntimeError):
    """Raised when a report is unsafe, incomplete, contradictory, or stale."""


def reject_secret_fields(
    value: Any,
    *,
    allow_top_level_enrollment_code: bool = False,
    _depth: int = 0,
) -> None:
    """Reject secret-shaped keys recursively before values can reach evidence."""

    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise EvidenceValidationError("response contains a non-string key")
            allowed_code = (
                allow_top_level_enrollment_code
                and _depth == 0
                and key == "enrollment_code"
            )
            safe_posture = key in {
                "private_key_present",
                "secret_returned_once",
                "raw_http_headers_recorded",
                "raw_http_bodies_recorded",
                "raw_subprocess_output_recorded",
                "generic_secret_pattern_matches",
            }
            if _SECRET_KEY.search(key) and not allowed_code and not safe_posture:
                raise EvidenceValidationError("secret-shaped field is not allowed")
            reject_secret_fields(
                child,
                allow_top_level_enrollment_code=False,
                _depth=_depth + 1,
            )
    elif isinstance(value, list):
        for child in value:
            reject_secret_fields(
                child,
                allow_top_level_enrollment_code=False,
                _depth=_depth + 1,
            )


def scan_safe_text(text: str, secrets_to_reject: tuple[str, ...] = ()) -> None:
    if any(secret and secret in text for secret in secrets_to_reject):
        raise EvidenceValidationError("secret value detected in output")
    if any(pattern.search(text) for pattern in _SECRET_TEXT):
        raise EvidenceValidationError("secret-shaped material detected in output")


def validate_report(
    report: JsonObject,
    *,
    directory_run_id: str,
    expected_candidate: str,
    now: datetime | None = None,
) -> None:
    required = {
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
    if set(report) != required:
        raise EvidenceValidationError("report fields are not closed")
    if report.get("schema_version") != SCHEMA_VERSION:
        raise EvidenceValidationError("schema version is invalid")
    if report.get("run_id") != directory_run_id or not _RUN_ID.fullmatch(directory_run_id):
        raise EvidenceValidationError("run identity is invalid")
    if not _COMMIT.fullmatch(expected_candidate):
        raise EvidenceValidationError("expected candidate is invalid")
    if report.get("result") != "passed" or report.get("last_stage") != "complete":
        raise EvidenceValidationError("journey result is not a completed pass")
    if report.get("nonclaims") != NONCLAIMS:
        raise EvidenceValidationError("explicit nonclaims are incomplete")
    reject_secret_fields(report)

    provenance = _object(report, "provenance")
    if set(provenance) != {
        "candidate_commit",
        "candidate_tree_clean_observed",
        "candidate_commit_at_finish_observed",
        "candidate_tree_clean_at_finish_observed",
        "candidate_finish_observation_completed",
        "started_at_utc",
        "finished_at_utc",
        "execution_mode",
        "candidate_binding",
    }:
        raise EvidenceValidationError("provenance fields are not closed")
    candidate = _string(provenance, "candidate_commit")
    if candidate != expected_candidate:
        raise EvidenceValidationError("report does not match the expected candidate")
    if provenance.get("candidate_tree_clean_observed") is not True:
        raise EvidenceValidationError("clean candidate was not observed")
    if provenance.get("candidate_commit_at_finish_observed") != candidate or (
        provenance.get("candidate_tree_clean_at_finish_observed") is not True
        or provenance.get("candidate_finish_observation_completed") is not True
    ):
        raise EvidenceValidationError("candidate finish observation is incomplete")
    if provenance.get("execution_mode") != "live_local_synthetic":
        raise EvidenceValidationError("execution mode is invalid")
    if provenance.get("candidate_binding") != "observation_not_authority":
        raise EvidenceValidationError("candidate binding overclaims authority")
    started = _timestamp(provenance, "started_at_utc")
    finished = _timestamp(provenance, "finished_at_utc")
    run_started = datetime.strptime(
        cast(re.Match[str], _RUN_ID.fullmatch(directory_run_id)).group(1),
        "%Y%m%dT%H%M%SZ",
    ).replace(tzinfo=UTC)
    effective_now = (now or datetime.now(UTC)).astimezone(UTC)
    if started.replace(microsecond=0) != run_started:
        raise EvidenceValidationError("run identity timestamp does not match provenance")
    if finished < started or finished - started > MAX_JOURNEY_DURATION:
        raise EvidenceValidationError("journey timestamps are contradictory or stale")
    if started > effective_now + MAX_FUTURE_SKEW or finished > effective_now + MAX_FUTURE_SKEW:
        raise EvidenceValidationError("journey timestamp is in the future")
    if effective_now - finished > MAX_EVIDENCE_AGE:
        raise EvidenceValidationError("journey evidence is stale")

    observations = _object(report, "observations")
    if set(observations) != {
        "preflight",
        "normal_stack",
        "workspace",
        "code_handling",
        "enrollment",
        "configuration_assignment",
        "synchronization",
        "revocation",
    }:
        raise EvidenceValidationError("required observations are incomplete")
    if _object(observations, "preflight") != {
        "isolated_compose_project": True,
        "isolated_sqlite_state": True,
        "postgres_dsn_consumed": False,
        "configuration_signer_ready": True,
        "runtime_candidate_authority": False,
        "production_identity_authority": False,
        "docker_daemon": "allowlisted_local_unix_socket",
        "docker_credentials_inherited": False,
        "ports_available_before_mutation": True,
    }:
        raise EvidenceValidationError("preflight observation is invalid")
    if _object(observations, "normal_stack") != {
        "api_healthy": True,
        "ui_http_status": 200,
        "ui_content_type": "text/html",
        "ui_shell_observed": True,
        "tool_count": 24,
        "storage_backend": "sqlite",
        "runtime_candidate_posture": "unreviewed_local",
        "node_image_built": True,
    }:
        raise EvidenceValidationError("normal stack observation is invalid")
    if _object(observations, "workspace") != {
        "workspace_id": "demo",
        "selected_from_active_gateway_inventory": True,
    }:
        raise EvidenceValidationError("workspace observation is invalid")
    if _object(observations, "code_handling") != {
        "secret_returned_once": True,
        "transport": "compose_stdin_only",
        "recorded": False,
    }:
        raise EvidenceValidationError("one-time-code handling observation is invalid")

    enrollment = _object(observations, "enrollment")
    node_id = _string(enrollment, "node_id")
    principal_id = _string(enrollment, "principal_id")
    if not _NODE_ID.fullmatch(node_id) or principal_id != f"agent:node.{node_id}":
        raise EvidenceValidationError("Gateway-derived Node identity binding is invalid")
    if enrollment != {
        "node_id": node_id,
        "principal_id": principal_id,
        "workspace_id": "demo",
        "identity_source": "gateway_derived",
        "gateway_evidence_status": "complete",
    }:
        raise EvidenceValidationError("enrollment observation is invalid")

    assignment = _object(observations, "configuration_assignment")
    generation = assignment.get("generation")
    digest = assignment.get("configuration_digest")
    if not isinstance(generation, int) or isinstance(generation, bool) or generation < 1:
        raise EvidenceValidationError("configuration generation is invalid")
    if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
        raise EvidenceValidationError("configuration digest is invalid")
    if assignment != {
        "generation": generation,
        "configuration_digest": digest,
        "evidence_status": "complete",
        "enforcement_status": "stored_not_enforced",
    }:
        raise EvidenceValidationError("configuration assignment is invalid")
    if _object(observations, "synchronization") != {
        "node_id": node_id,
        "desired_generation": generation,
        "acknowledged_generation": generation,
        "configuration_digest": digest,
        "configuration_acknowledgment_status": "stored_not_enforced",
        "configuration_state": CONFIGURATION_STATE_STORED_CURRENT_NOT_ENFORCED,
        "observed_state": NODE_OBSERVED_STATE_CONNECTED,
        "connectivity_source": "gateway_accepted_heartbeat",
        "runner_health_known": False,
        "model_health_known": False,
    }:
        raise EvidenceValidationError("Node synchronization observation is invalid")
    if _object(observations, "revocation") != {
        "node_id": node_id,
        "status": "revoked",
        "gateway_evidence_status": "complete",
        "subsequent_signed_heartbeat_rejected": True,
        "rejection_output_recorded": False,
    }:
        raise EvidenceValidationError("revocation observation is invalid")
    cleanup = _object(report, "cleanup")
    if set(cleanup) != {
        "unique_project",
        "images",
        "node_stop_succeeded",
        "revocation_succeeded",
        "compose_down_succeeded",
        "images_removed",
        "resources_absent",
        "volumes_removed",
        "runtime_state_removed",
        "runtime_state_retained",
        "recovery_required",
        "outcome",
    }:
        raise EvidenceValidationError("cleanup fields are not closed")
    for key in (
        "node_stop_succeeded",
        "revocation_succeeded",
        "compose_down_succeeded",
        "images_removed",
        "resources_absent",
        "volumes_removed",
        "runtime_state_removed",
    ):
        if cleanup.get(key) is not True:
            raise EvidenceValidationError("cleanup observation is incomplete")
    if (
        cleanup.get("runtime_state_retained") is not False
        or cleanup.get("outcome") != "completed"
        or cleanup.get("recovery_required") is not False
    ):
        raise EvidenceValidationError("cleanup did not complete without recovery")
    suffix = directory_run_id[-8:]
    project = f"ithildin-local-v1-node-{suffix}"
    if cleanup.get("unique_project") != project:
        raise EvidenceValidationError("cleanup project identity is invalid")
    images = _object(cleanup, "images")
    expected_references = {
        "api": f"{project}-ithildin-api",
        "ui": f"{project}-ithildin-ui",
        "node": f"ithildin/node-journey:{suffix}",
    }
    if set(images) != set(expected_references):
        raise EvidenceValidationError("cleanup image fields are not closed")
    for label, reference in expected_references.items():
        image = _object(images, label)
        if set(image) != {"reference", "image_id"} or image.get("reference") != reference:
            raise EvidenceValidationError("cleanup image reference is invalid")
        image_id = image.get("image_id")
        if not isinstance(image_id, str) or not _DIGEST.fullmatch(image_id):
            raise EvidenceValidationError("cleanup image identity is invalid")

    if _object(report, "redaction_scan") != {
        "status": "passed",
        "forbidden_value_matches": 0,
        "generic_secret_pattern_matches": 0,
        "raw_http_headers_recorded": False,
        "raw_http_bodies_recorded": False,
        "raw_subprocess_output_recorded": False,
    }:
        raise EvidenceValidationError("redaction scan record is invalid")
    if _object(report, "authority") != {
        "runtime_authority": False,
        "release_authority": False,
        "promotion_authority": False,
        "production_identity_authority": False,
        "production_storage_authority": False,
        "uat_complete": False,
    }:
        raise EvidenceValidationError("authority fields are not all false")


def render_markdown(report: JsonObject) -> str:
    provenance = _object(report, "provenance")
    cleanup = _object(report, "cleanup")
    lines = [
        "# Ithildin Local v1.0 Synthetic Node Journey",
        "",
        f"- Result: `{report['result']}`",
        f"- Run: `{report['run_id']}`",
        f"- Candidate commit observed: `{provenance['candidate_commit']}`",
        (
            "- Candidate tree clean observed: "
            f"`{str(provenance['candidate_tree_clean_observed']).lower()}`"
        ),
        (
            "- Candidate commit at finish observed: "
            f"`{provenance['candidate_commit_at_finish_observed']}`"
        ),
        (
            "- Candidate tree clean at finish observed: "
            f"`{str(provenance['candidate_tree_clean_at_finish_observed']).lower()}`"
        ),
        (
            "- Candidate finish observation completed: "
            f"`{str(provenance['candidate_finish_observation_completed']).lower()}`"
        ),
        f"- Started: `{provenance['started_at_utc']}`",
        f"- Finished: `{provenance['finished_at_utc']}`",
        f"- Candidate binding: `{provenance['candidate_binding']}`",
        f"- Last stage: `{report['last_stage']}`",
    ]
    if report.get("result") == "passed":
        observations = _object(report, "observations")
        enrollment = _object(observations, "enrollment")
        assignment = _object(observations, "configuration_assignment")
        lines.extend(
            [
                f"- Gateway-derived Node: `{enrollment['node_id']}`",
                f"- Gateway-derived principal: `{enrollment['principal_id']}`",
                f"- Configuration generation: `{assignment['generation']}`",
                f"- Configuration digest: `{assignment['configuration_digest']}`",
                "- Configuration truth: `stored_not_enforced`",
                "- UI shell observed at fixed local origin: `true`",
            ]
        )
    else:
        failure = _object(report, "failure")
        lines.append(f"- Failure code: `{failure['code']}`")
    lines.extend(
        [
            "",
            "## Cleanup",
            "",
            f"- Unique project: `{cleanup['unique_project']}`",
            f"- Outcome: `{cleanup['outcome']}`",
            (
                "- Runtime, release, promotion, production identity/storage, "
                "and UAT authority: `false`"
            ),
            "",
            "## Explicit nonclaims",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in NONCLAIMS)
    lines.extend(
        [
            "",
            "The redaction scan passed before these files were written. No raw HTTP headers,",
            (
                "HTTP bodies, subprocess output, enrollment code, admin token, or private key "
                "is recorded."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def nonclaims_json_value() -> list[JsonValue]:
    return cast(list[JsonValue], NONCLAIMS)


def _object(document: JsonObject, key: str) -> JsonObject:
    value = document.get(key)
    if not isinstance(value, dict):
        raise EvidenceValidationError(f"report field is not an object: {key}")
    return value


def _string(document: JsonObject, key: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value:
        raise EvidenceValidationError(f"report field is not a string: {key}")
    return value


def _timestamp(document: JsonObject, key: str) -> datetime:
    value = _string(document, key)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceValidationError(f"timestamp is invalid: {key}") from exc
    if parsed.tzinfo is None:
        raise EvidenceValidationError(f"timestamp is not timezone-aware: {key}")
    return parsed.astimezone(UTC)

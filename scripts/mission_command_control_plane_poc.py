"""Run the bounded MCC-006 Mission Command POC against a real local Gateway."""

from __future__ import annotations

import argparse
import base64
import http.client
import json
import os
import secrets
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from types import FrameType
from typing import Any, cast

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from ithildin_api.node_configuration import generate_node_configuration_signing_keypair
from ithildin_api.nodes import canonical_signature_message
from ithildin_audit_core import generate_audit_signing_keypair
from ithildin_node.client import (
    NodeClient,
    NodeClientError,
    NodeState,
    StoredNodeConfiguration,
)
from ithildin_schemas import JsonObject, canonical_json, sha256_digest

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_ROOT = ROOT / "var/mission-command-control-plane-poc-20260719"
HOST = "127.0.0.1"
PORT = 8021
API_URL = f"http://{HOST}:{PORT}"
ADMIN_TOKEN = secrets.token_urlsafe(32)
RUNNER_OUTPUT_SENTINEL = "MCC006-RUNNER-OUTPUT-MUST-NOT-BE-PERSISTED"


class _DenyRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        return None


LOOPBACK_OPENER = urllib.request.build_opener(
    urllib.request.ProxyHandler({}),
    _DenyRedirectHandler(),
)

ADVERSARIAL_TESTS = (
    "tests/test_api_service.py::test_signed_node_claim_is_single_winner_and_target_bound",
    "tests/test_api_service.py::test_ineligible_current_posture_runner_reports_are_quarantined",
    "tests/test_api_service.py::test_runner_report_identity_rotation_enforces_current_key_and_preserves_replay",
    "tests/test_api_service.py::test_revoked_node_report_is_quarantined_and_cannot_poll_control",
    "tests/test_api_service.py::test_late_success_across_exact_cancellation_revision_advances_once",
    "tests/test_api_service.py::test_signed_node_claim_audit_failure_exposes_no_envelope",
    "tests/test_api_service.py::test_runner_report_audit_failure_records_receipt_without_lifecycle_advance",
    "tests/test_api_service.py::test_runner_report_transition_audit_failure_preserves_completed_receipt",
    "tests/test_api_service.py::test_signed_node_claim_revoked_after_audit_is_not_delivered",
    "tests/test_api_service.py::test_completed_runner_report_receipt_tampering_fails_closed",
    "tests/test_api_service.py::test_mission_admission_audit_failure_remains_unadmitted_and_recovery_required",
    "tests/test_api_service.py::test_mission_admission_audit_failure_after_jsonl_append_rolls_back_audit_commit",
    "tests/test_api_service.py::test_mission_admission_audit_failure_after_audit_commit_remains_unadmitted",
    "tests/test_missions.py::test_evidence_interruption_preserves_prior_lifecycle_and_blocks_finalize",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", type=Path, default=DEFAULT_EVIDENCE_ROOT)
    parser.add_argument(
        "--replace",
        action="store_true",
        help="replace only the selected generated POC evidence root",
    )
    args = parser.parse_args()
    evidence_root = args.evidence_root.resolve()
    _require_clean_candidate()
    _prepare_root(evidence_root, replace=args.replace)
    _generate_keys(evidence_root)
    metadata = _candidate_metadata()
    _write(evidence_root / "evidence/candidate.json", metadata)

    gateway: subprocess.Popen[str] | None = None
    try:
        gateway = _start_gateway(evidence_root, phase="before-restart")
        state, configuration = _prepare_node(evidence_root)
        mission = _exercise_primary_mission(evidence_root, state, configuration)
        _stop_gateway(gateway)
        gateway = None
        _exercise_partition(evidence_root, state, configuration, mission)
        gateway = _start_gateway(evidence_root, phase="after-restart")
        _exercise_restart_and_success(evidence_root, state, configuration, mission)
        _exercise_cancellation_race(evidence_root, state, configuration)
        _exercise_revoked_late_report(evidence_root, state, configuration)
        _write(
            evidence_root / "evidence/audit-verification.json",
            _admin_request("/audit-events/verify"),
        )
        _write(
            evidence_root / "evidence/final-mission-inventory.json",
            _admin_request("/missions?limit=50"),
        )
    finally:
        if gateway is not None:
            _stop_gateway(gateway)

    _run_adversarial_tests(evidence_root)
    print(f"Built MCC-006 Mission Command POC evidence at {evidence_root}")
    return 0


def _require_clean_candidate() -> None:
    top_level = Path(_git_output(ROOT, "rev-parse", "--show-toplevel")).resolve()
    if top_level != ROOT:
        raise SystemExit("MCC-006 POC repository identity is not the expected checkout")
    status = _git_output(ROOT, "status", "--short")
    if status.strip():
        raise SystemExit("MCC-006 POC requires a clean exact candidate")


def _prepare_root(root: Path, *, replace: bool) -> None:
    if root.exists():
        if not replace:
            raise SystemExit(f"evidence root already exists: {root}")
        if ROOT / "var" not in root.parents:
            raise SystemExit("refusing to replace evidence outside the repository var directory")
        shutil.rmtree(root)
    for child in ("client", "db", "evidence", "keys", "logs"):
        (root / child).mkdir(parents=True, exist_ok=True)


def _candidate_metadata() -> JsonObject:
    commit = _git_output(ROOT, "rev-parse", "HEAD")
    return {
        "schema_version": "1",
        "ticket": "MCC-006",
        "git_commit": commit,
        "source_tree_clean": True,
        "generated_at": datetime.now(UTC).isoformat(),
        "claim_level": "mission_control_plane_candidate_ready_for_external_review",
        "runner_launch_claimed": False,
        "production_deployment_authorized": False,
        "uat_acceptance_recorded": False,
        "tool_count": 24,
    }


def _generate_keys(root: Path) -> None:
    generate_audit_signing_keypair(
        private_key_path=root / "keys/audit-private.pem",
        public_key_path=root / "keys/audit-public.pem",
    )
    generate_node_configuration_signing_keypair(
        root / "keys/configuration-private.pem",
        root / "keys/configuration-public.pem",
    )


def _start_gateway(root: Path, *, phase: str) -> subprocess.Popen[str]:
    environment = _isolated_environment(root)
    log_path = root / f"logs/gateway-{phase}.log"
    process: subprocess.Popen[str] | None = None
    try:
        with _defer_termination_signals():
            with log_path.open("w", encoding="utf-8") as log_handle:
                process = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        "ithildin_api.app:app",
                        "--host",
                        HOST,
                        "--port",
                        str(PORT),
                    ],
                    cwd=root,
                    env=environment,
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"Gateway failed to start; inspect {log_path}")
            try:
                with LOOPBACK_OPENER.open(f"{API_URL}/healthz", timeout=1):
                    return process
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.2)
        raise RuntimeError("Gateway did not become healthy")
    except BaseException:
        if process is not None:
            _stop_gateway(process)
        raise


def _stop_gateway(process: subprocess.Popen[str]) -> None:
    with _defer_termination_signals():
        if process.poll() is not None:
            process.wait(timeout=0)
            return
        try:
            process.terminate()
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            process.wait(timeout=5)


def _prepare_node(root: Path) -> tuple[NodeState, StoredNodeConfiguration]:
    issued = _admin_request(
        "/nodes/enrollment-codes",
        {
            "workspace_id": "default",
            "display_name": "MCC-006 synthetic Mission Node",
        },
    )
    client = _node_client()
    state = client.enroll(
        enrollment_code=_required(issued, "enrollment_code"),
        node_version="0.1.0",
        runner_adapter="synthetic_external_runner",
        deployment_topology="local_process",
    )
    state.write_new(root / "client/state.json")
    _write(root / "evidence/enrollment-safe.json", state.safe_summary())
    assignment = _admin_request(
        f"/nodes/{state.node_id}/configurations",
        {
            "minimum_node_version": "0.1.0",
            "heartbeat_interval_seconds": 30,
            "offline_posture": "deny_governed_actions",
            "evidence_buffer_max_events": 1000,
        },
    )
    configuration = client.pull_configuration(state, known_generation=0)
    configuration.write_atomic(root / "client/current-configuration.json")
    acknowledgment = client.acknowledge_configuration(state, configuration)
    heartbeat = client.heartbeat(
        state,
        node_version="0.1.0",
        runner_adapter="synthetic_external_runner",
        deployment_topology="local_process",
        configuration_digest=configuration.configuration_digest,
    )
    _write(
        root / "evidence/node-ready.json",
        {
            "node_id": state.node_id,
            "principal_id": state.principal_id,
            "workspace_id": state.workspace_id,
            "configuration_generation": assignment.get("generation"),
            "configuration_digest": assignment.get("configuration_digest"),
            "acknowledgment_status": acknowledgment.get("configuration_acknowledgment_status"),
            "heartbeat_observed_state": heartbeat.get("observed_state"),
        },
    )
    return state, configuration


def _exercise_primary_mission(
    root: Path,
    state: NodeState,
    configuration: StoredNodeConfiguration,
) -> JsonObject:
    admission: JsonObject = {
        "target_node_id": state.node_id,
        "mission_template_id": "synthetic_read_review_v1",
        "requested_timeout_seconds": 300,
        "client_request_id": "mcc006-primary-response-loss",
    }
    lost_status = _post_and_discard_response("/missions", admission)
    if lost_status != 200:
        raise RuntimeError(f"response-loss admission failed with HTTP {lost_status}")
    replay = _wait_for_admission_replay(admission)
    mission_id = _required(replay, "mission_id")
    _write(
        root / "evidence/admission-response-loss-and-replay.json",
        {
            "response_status_observed": lost_status,
            "response_body_observed": False,
            "replay_mission_id": mission_id,
            "replay_lifecycle_state": replay.get("lifecycle_state"),
            "replay_lifecycle_revision": replay.get("lifecycle_revision"),
        },
    )
    drifted = {**admission, "requested_timeout_seconds": 301}
    drift_status, drift_body = _request_outcome("/missions", drifted, admin=True)
    _write(
        root / "evidence/admission-drifted-replay-denial.json",
        {"status_code": drift_status, "detail": drift_body.get("detail")},
    )

    claim_path = f"/nodes/{state.node_id}/mission-claims"
    claim_payload: JsonObject = {"protocol_version": "1"}
    claim = _signed_request(state, claim_path, claim_payload, nonce="c0" * 16)
    claim_id = _required(claim, "claim_id")
    envelope_digest = _required(claim, "envelope_digest")
    _write(root / "evidence/primary-claim-safe.json", _claim_summary(claim))

    report_path = f"/nodes/{state.node_id}/mission-reports"
    running_report: JsonObject = {
        "mission_id": mission_id,
        "claim_id": claim_id,
        "envelope_digest": envelope_digest,
        "expected_lifecycle_revision": 2,
        "report_id": "mreport_" + ("c" * 32),
        "report_kind": "runner_running",
        "outcome_code": "started",
        "reason_code": None,
        "artifact_digest": None,
    }
    running = _signed_request(state, report_path, running_report, nonce="c1" * 16)
    _write(root / "evidence/primary-running-report.json", running)
    session_prefix = envelope_digest.removeprefix("sha256:")[:16]
    governed = _node_client().governed_tool_call(
        state,
        configuration,
        node_version="0.1.0",
        session_id=f"mission:{mission_id}:{claim_id}:{session_prefix}",
        tool_name="project.structure.summary",
        arguments={},
        nonce="c2" * 16,
    )
    _write(root / "evidence/primary-governed-run.json", _governed_summary(governed))
    detail = _admin_request(f"/missions/{mission_id}")
    _write(root / "evidence/primary-before-restart.json", _mission_projection(detail))
    return {
        "admission": admission,
        "mission_id": mission_id,
        "claim_id": claim_id,
        "envelope_digest": envelope_digest,
        "running_report": running_report,
        "report_path": report_path,
    }


def _exercise_partition(
    root: Path,
    state: NodeState,
    configuration: StoredNodeConfiguration,
    mission: JsonObject,
) -> None:
    try:
        _node_client(timeout_seconds=0.25).governed_tool_call(
            state,
            configuration,
            node_version="0.1.0",
            session_id=(
                f"mission:{mission['mission_id']}:{mission['claim_id']}:"
                f"{str(mission['envelope_digest']).removeprefix('sha256:')[:16]}"
            ),
            tool_name="project.test.summary",
            arguments={},
            nonce="c3" * 16,
        )
    except NodeClientError as exc:
        outcome: JsonObject = {
            "status": "failed_closed",
            "error_category": str(exc),
            "local_execution_used": False,
            "buffered_or_queued": False,
            "automatic_retry_used": False,
        }
    else:
        outcome = {"status": "unexpectedly_accepted"}
    _write(root / "evidence/partition-denial.json", outcome)


def _exercise_restart_and_success(
    root: Path,
    state: NodeState,
    configuration: StoredNodeConfiguration,
    mission: JsonObject,
) -> None:
    _refresh_heartbeat(state, configuration)
    claim_status, claim_replay = _signed_request_outcome(
        state,
        f"/nodes/{state.node_id}/mission-claims",
        {"protocol_version": "1"},
        nonce="c0" * 16,
    )
    _write(
        root / "evidence/claim-nonce-replay-after-restart.json",
        {"status_code": claim_status, "detail": claim_replay.get("detail")},
    )
    report_status, report_replay = _signed_request_outcome(
        state,
        str(mission["report_path"]),
        cast(JsonObject, mission["running_report"]),
        nonce="c4" * 16,
    )
    _write(
        root / "evidence/report-id-replay-after-restart.json",
        {
            "status_code": report_status,
            **_receipt_summary(report_replay),
        },
    )
    admission_replay = _admin_request("/missions", cast(JsonObject, mission["admission"]))
    _write(
        root / "evidence/admission-replay-after-restart.json",
        {
            "mission_id": admission_replay.get("mission_id"),
            "lifecycle_state": admission_replay.get("lifecycle_state"),
            "lifecycle_revision": admission_replay.get("lifecycle_revision"),
        },
    )
    artifact_digest = sha256_digest({"runner_output": RUNNER_OUTPUT_SENTINEL})
    succeeded_report: JsonObject = {
        "mission_id": mission["mission_id"],
        "claim_id": mission["claim_id"],
        "envelope_digest": mission["envelope_digest"],
        "expected_lifecycle_revision": 3,
        "report_id": "mreport_" + ("d" * 32),
        "report_kind": "runner_succeeded",
        "outcome_code": "succeeded",
        "reason_code": None,
        "artifact_digest": artifact_digest,
    }
    succeeded = _signed_request(
        state,
        str(mission["report_path"]),
        succeeded_report,
        nonce="c5" * 16,
    )
    _write(root / "evidence/primary-succeeded-report.json", succeeded)
    detail = _admin_request(f"/missions/{mission['mission_id']}")
    _write(root / "evidence/primary-final.json", _mission_projection(detail))


def _exercise_cancellation_race(
    root: Path,
    state: NodeState,
    configuration: StoredNodeConfiguration,
) -> None:
    _refresh_heartbeat(state, configuration)
    admitted = _admin_request(
        "/missions",
        {
            "target_node_id": state.node_id,
            "mission_template_id": "synthetic_read_review_v1",
            "requested_timeout_seconds": 300,
            "client_request_id": "mcc006-cancellation-race",
        },
    )
    mission_id = _required(admitted, "mission_id")
    claim = _signed_request(
        state,
        f"/nodes/{state.node_id}/mission-claims",
        {"protocol_version": "1"},
        nonce="d0" * 16,
    )
    claim_id = _required(claim, "claim_id")
    envelope_digest = _required(claim, "envelope_digest")
    report_path = f"/nodes/{state.node_id}/mission-reports"
    running: JsonObject = {
        "mission_id": mission_id,
        "claim_id": claim_id,
        "envelope_digest": envelope_digest,
        "expected_lifecycle_revision": 2,
        "report_id": "mreport_" + ("e" * 32),
        "report_kind": "runner_running",
        "outcome_code": "started",
        "reason_code": None,
        "artifact_digest": None,
    }
    _signed_request(state, report_path, running, nonce="d1" * 16)
    canceled = _admin_request(
        f"/missions/{mission_id}/cancel",
        {"client_request_id": "mcc006-cancel-decision"},
    )
    late_success: JsonObject = {
        "mission_id": mission_id,
        "claim_id": claim_id,
        "envelope_digest": envelope_digest,
        "expected_lifecycle_revision": 3,
        "report_id": "mreport_" + ("f" * 32),
        "report_kind": "runner_succeeded",
        "outcome_code": "succeeded",
        "reason_code": None,
        "artifact_digest": sha256_digest({"artifact": "late-success"}),
    }
    late = _signed_request(state, report_path, late_success, nonce="d2" * 16)
    detail = _admin_request(f"/missions/{mission_id}")
    _write(
        root / "evidence/cancellation-race.json",
        {
            "mission_id": mission_id,
            "cancel_lifecycle_state": canceled.get("lifecycle_state"),
            "cancel_revision": canceled.get("lifecycle_revision"),
            "runner_stop_proven": canceled.get("runner_stop_proven"),
            "late_report_disposition": late.get("receipt_disposition"),
            "final_projection": _mission_projection(detail),
        },
    )


def _exercise_revoked_late_report(
    root: Path,
    state: NodeState,
    configuration: StoredNodeConfiguration,
) -> None:
    _refresh_heartbeat(state, configuration)
    admitted = _admin_request(
        "/missions",
        {
            "target_node_id": state.node_id,
            "mission_template_id": "synthetic_read_review_v1",
            "requested_timeout_seconds": 300,
            "client_request_id": "mcc006-revoked-late-report",
        },
    )
    mission_id = _required(admitted, "mission_id")
    claim = _signed_request(
        state,
        f"/nodes/{state.node_id}/mission-claims",
        {"protocol_version": "1"},
        nonce="e0" * 16,
    )
    claim_id = _required(claim, "claim_id")
    envelope_digest = _required(claim, "envelope_digest")
    report_path = f"/nodes/{state.node_id}/mission-reports"
    running: JsonObject = {
        "mission_id": mission_id,
        "claim_id": claim_id,
        "envelope_digest": envelope_digest,
        "expected_lifecycle_revision": 2,
        "report_id": "mreport_" + ("a" * 32),
        "report_kind": "runner_running",
        "outcome_code": "started",
        "reason_code": None,
        "artifact_digest": None,
    }
    _signed_request(state, report_path, running, nonce="e1" * 16)
    revoked = _admin_request(f"/nodes/{state.node_id}/revoke", {})
    late: JsonObject = {
        "mission_id": mission_id,
        "claim_id": claim_id,
        "envelope_digest": envelope_digest,
        "expected_lifecycle_revision": 3,
        "report_id": "mreport_" + ("b" * 32),
        "report_kind": "runner_succeeded",
        "outcome_code": "succeeded",
        "reason_code": None,
        "artifact_digest": sha256_digest({"artifact": "revoked-late-report"}),
    }
    quarantined = _signed_request(state, report_path, late, nonce="e2" * 16)
    receipt = _receipt_summary(quarantined)
    detail = _admin_request(f"/missions/{mission_id}")
    _write(
        root / "evidence/revoked-late-report.json",
        {
            "mission_id": mission_id,
            "node_status": revoked.get("status"),
            "receipt_disposition": receipt.get("receipt_disposition"),
            "quarantine_reason_code": receipt.get("quarantine_reason_code"),
            "final_projection": _mission_projection(detail),
        },
    )


def _refresh_heartbeat(
    state: NodeState,
    configuration: StoredNodeConfiguration,
) -> None:
    heartbeat = _node_client().heartbeat(
        state,
        node_version="0.1.0",
        runner_adapter="synthetic_external_runner",
        deployment_topology="local_process",
        configuration_digest=configuration.configuration_digest,
    )
    if heartbeat.get("observed_state") != "observed_connected":
        raise RuntimeError("MCC-006 Node heartbeat did not restore connected posture")


def _run_adversarial_tests(root: Path) -> None:
    command = [sys.executable, "-m", "pytest", "-vv", "--tb=short", *ADVERSARIAL_TESTS]
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=_isolated_environment(root),
        capture_output=True,
        text=True,
        check=False,
    )
    transcript = "$ " + " ".join(command) + "\n" + result.stdout + result.stderr
    (root / "evidence/focused-adversarial-tests.txt").write_text(
        transcript,
        encoding="utf-8",
    )
    _write(
        root / "evidence/focused-adversarial-tests.json",
        {
            "returncode": result.returncode,
            "selected_tests": list(ADVERSARIAL_TESTS),
            "all_selected_tests_passed": result.returncode == 0,
        },
    )
    if result.returncode != 0:
        raise RuntimeError("MCC-006 focused adversarial tests failed")


def _post_and_discard_response(path: str, payload: JsonObject) -> int:
    connection = http.client.HTTPConnection(HOST, PORT, timeout=10)
    connection.request(
        "POST",
        path,
        body=canonical_json(payload).encode(),
        headers={
            "Authorization": f"Bearer {ADMIN_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    response = connection.getresponse()
    status = response.status
    connection.close()
    return status


def _wait_for_admission_replay(payload: JsonObject) -> JsonObject:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        status, document = _request_outcome("/missions", payload, admin=True)
        if status == 200:
            return document
        time.sleep(0.1)
    raise RuntimeError("admission did not become replayable after response loss")


def _admin_request(path: str, payload: JsonObject | None = None) -> JsonObject:
    status, document = _request_outcome(path, payload, admin=True)
    if status < 200 or status >= 300:
        raise RuntimeError(f"Gateway request {path} failed with HTTP {status}: {document}")
    return document


def _signed_request(
    state: NodeState,
    path: str,
    payload: JsonObject,
    *,
    nonce: str,
) -> JsonObject:
    status, document = _signed_request_outcome(state, path, payload, nonce=nonce)
    if status < 200 or status >= 300:
        raise RuntimeError(f"signed Gateway request {path} failed with HTTP {status}: {document}")
    return document


def _signed_request_outcome(
    state: NodeState,
    path: str,
    payload: JsonObject,
    *,
    nonce: str,
) -> tuple[int, JsonObject]:
    timestamp = str(int(datetime.now(UTC).timestamp()))
    message = canonical_signature_message(
        method="POST",
        path=path,
        timestamp=timestamp,
        nonce=nonce,
        body_hash=sha256_digest(payload),
    )
    private_key = Ed25519PrivateKey.from_private_bytes(
        base64.b64decode(state.private_key, validate=True)
    )
    return _request_outcome(
        path,
        payload,
        headers={
            "X-Ithildin-Node": state.node_id,
            "X-Ithildin-Timestamp": timestamp,
            "X-Ithildin-Nonce": nonce,
            "X-Ithildin-Signature": base64.b64encode(private_key.sign(message)).decode(),
        },
    )


def _request_outcome(
    path: str,
    payload: JsonObject | None,
    *,
    admin: bool = False,
    headers: dict[str, str] | None = None,
) -> tuple[int, JsonObject]:
    request_headers = dict(headers or {})
    if admin:
        request_headers["Authorization"] = f"Bearer {ADMIN_TOKEN}"
    data = None
    method = "GET"
    if payload is not None:
        request_headers["Content-Type"] = "application/json"
        data = canonical_json(payload).encode()
        method = "POST"
    request = urllib.request.Request(
        f"{API_URL}{path}",
        data=data,
        headers=request_headers,
        method=method,
    )
    try:
        with LOOPBACK_OPENER.open(request, timeout=10) as response:
            return response.status, _parse_json(response.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, _parse_json(exc.read().decode())


def _node_client(*, timeout_seconds: float = 10.0) -> NodeClient:
    return _LoopbackNodeClient(API_URL, timeout_seconds=timeout_seconds)


class _LoopbackNodeClient(NodeClient):
    def _post(
        self,
        path: str,
        payload: JsonObject,
        *,
        headers: dict[str, str] | None = None,
    ) -> JsonObject:
        request = urllib.request.Request(
            f"{self.api_url}{path}",
            data=canonical_json(payload).encode(),
            headers={"Content-Type": "application/json", **(headers or {})},
            method="POST",
        )
        try:
            with LOOPBACK_OPENER.open(request, timeout=self.timeout_seconds) as response:
                document = json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            raise NodeClientError(
                f"Gateway rejected Node request with HTTP {exc.code}"
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise NodeClientError("Gateway is unavailable") from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise NodeClientError("Gateway returned an invalid response") from exc
        if not isinstance(document, dict):
            raise NodeClientError("Gateway returned an invalid response")
        return cast(JsonObject, document)


def _local_git_environment() -> dict[str, str]:
    return {
        "PATH": os.defpath,
        "LANG": "C",
        "LC_ALL": "C",
        "GIT_ALLOW_PROTOCOL": "file",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
    }


def _git_output(repo_root: Path, *arguments: str) -> str:
    git_executable = shutil.which("git", path=os.defpath)
    if git_executable is None:
        raise RuntimeError("system Git executable is unavailable")
    return subprocess.run(
        [
            git_executable,
            "--no-optional-locks",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.untrackedCache=false",
            "-c",
            f"core.hooksPath={os.devnull}",
            "-C",
            str(repo_root),
            *arguments,
        ],
        cwd=repo_root,
        env=_local_git_environment(),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


@contextmanager
def _defer_termination_signals() -> Iterator[None]:
    received: list[tuple[int, Any]] = []
    previous_handlers: dict[int, Any] = {}

    def record(signum: int, frame: FrameType | None) -> None:
        received.append((signum, frame))

    for configured_signal in (signal.SIGINT, signal.SIGTERM):
        previous = signal.getsignal(configured_signal)
        if previous == signal.SIG_IGN:
            continue
        previous_handlers[configured_signal] = previous
        signal.signal(configured_signal, record)
    try:
        yield
    finally:
        for restored_signum, previous in previous_handlers.items():
            signal.signal(restored_signum, previous)
    if not received:
        return
    received_signum, frame = received[0]
    previous = previous_handlers[received_signum]
    if callable(previous):
        previous(received_signum, frame)
        return
    if received_signum == signal.SIGINT:
        raise KeyboardInterrupt
    raise SystemExit(128 + received_signum)


def _isolated_environment(root: Path) -> dict[str, str]:
    return {
        "PATH": os.defpath,
        "NO_PROXY": "*",
        "no_proxy": "*",
        "PYTHONHASHSEED": "0",
        "PYTHONNOUSERSITE": "1",
        "ITHILDIN_ADMIN_TOKEN": ADMIN_TOKEN,
        "ITHILDIN_ALLOW_DEV_ADMIN_TOKEN": "false",
        "ITHILDIN_AUDIT_LOG_PATH": str(root / "logs/audit.jsonl"),
        "ITHILDIN_AUDIT_SIGNING_PRIVATE_KEY_PATH": str(root / "keys/audit-private.pem"),
        "ITHILDIN_AUDIT_SIGNING_PUBLIC_KEY_PATH": str(root / "keys/audit-public.pem"),
        "ITHILDIN_DB_PATH": str(root / "db/ithildin.sqlite3"),
        "ITHILDIN_STORAGE_BACKEND": "sqlite",
        "ITHILDIN_POSTGRES_DSN": "",
        "ITHILDIN_MANIFEST_DIR": str(ROOT / "tool-manifests"),
        "ITHILDIN_MANIFEST_LOCK_PATH": str(ROOT / "tool-manifests.lock.json"),
        "ITHILDIN_REQUIRE_MANIFEST_LOCK": "true",
        "ITHILDIN_MANIFEST_LOCK_SIGNING_PRIVATE_KEY_PATH": str(
            root / "keys/unused-manifest-lock-private.pem"
        ),
        "ITHILDIN_MANIFEST_LOCK_SIGNING_PUBLIC_KEY_PATH": str(
            root / "keys/unused-manifest-lock-public.pem"
        ),
        "ITHILDIN_MANIFEST_LOCK_SIGNATURE_PATH": str(
            root / "keys/unused-manifest-lock-signature.json"
        ),
        "ITHILDIN_REQUIRE_SIGNED_MANIFEST_LOCK": "false",
        "ITHILDIN_PRINCIPAL_REGISTRY_PATH": str(ROOT / "principals/local.yaml"),
        "ITHILDIN_REQUIRE_KNOWN_PRINCIPALS": "true",
        "ITHILDIN_POLICY_PATH": str(ROOT / "policies/default.yaml"),
        "ITHILDIN_POLICY_TESTS_PATH": str(ROOT / "policies/tests/default.yaml"),
        "ITHILDIN_POLICY_ENGINE": "yaml",
        "ITHILDIN_OPA_URL": "",
        "ITHILDIN_OPA_DECISION_PATH": "/v1/data/ithildin/decision",
        "ITHILDIN_OPA_BUNDLE_MANIFEST_PATH": str(ROOT / "policies/opa/bundle.lock.json"),
        "ITHILDIN_APPROVAL_EXPIRY_SECONDS": "900",
        "ITHILDIN_NODE_ENROLLMENT_EXPIRY_SECONDS": "600",
        "ITHILDIN_NODE_MAX_CLOCK_SKEW_SECONDS": "120",
        "ITHILDIN_NODE_STALE_AFTER_SECONDS": "5",
        "ITHILDIN_NODE_CONFIGURATION_SIGNING_PRIVATE_KEY_PATH": str(
            root / "keys/configuration-private.pem"
        ),
        "ITHILDIN_NODE_CONFIGURATION_SIGNING_PUBLIC_KEY_PATH": str(
            root / "keys/configuration-public.pem"
        ),
        "ITHILDIN_WORKSPACE_ROOT": str(ROOT / "workspaces"),
        "ITHILDIN_WORKSPACE_REGISTRY_PATH": str(ROOT / "workspaces/local.yaml"),
        "ITHILDIN_REQUIRE_KNOWN_WORKSPACES": "true",
        "ITHILDIN_DEFAULT_WORKSPACE_ID": "default",
        "ITHILDIN_TRUSTED_HOST_STAGING_ROOT": str(root / "trusted-host-staging"),
        "ITHILDIN_TRUSTED_HOST_REGISTRY_PATH": str(ROOT / "trusted-hosts/local.yaml"),
        "ITHILDIN_RUNTIME_CANDIDATE_AUTHORIZATION_PATH": str(
            root / "disabled-runtime-candidate-authorization.json"
        ),
        "ITHILDIN_MAX_READ_BYTES": "131072",
        "ITHILDIN_MAX_PATCH_BYTES": "131072",
        "ITHILDIN_HTTP_ALLOWLIST": "",
        "ITHILDIN_HTTP_TIMEOUT_SECONDS": "10",
        "ITHILDIN_HTTP_MAX_RESPONSE_BYTES": "131072",
        "ITHILDIN_HTTP_MAX_REDIRECTS": "3",
        "ITHILDIN_REDACTION_EXTRA_KEYS": "",
        "ITHILDIN_REDACTION_EXTRA_PATTERNS": "",
        "ITHILDIN_SEARCH_RESULT_LIMIT": "100",
        "ITHILDIN_GIT_LOG_LIMIT": "20",
        "ITHILDIN_OTEL_ENABLED": "false",
        "ITHILDIN_OTEL_SERVICE_NAME": "ithildin-mcc006-poc",
        "ITHILDIN_OTEL_CONSOLE_EXPORT": "false",
        "ITHILDIN_OTEL_OTLP_ENDPOINT": "",
        "ITHILDIN_LOG_LEVEL": "INFO",
    }


def _claim_summary(claim: JsonObject) -> JsonObject:
    return {
        "mission_id": claim.get("mission_id"),
        "claim_id": claim.get("claim_id"),
        "envelope_digest": claim.get("envelope_digest"),
        "claim_lifecycle_revision": claim.get("claim_lifecycle_revision"),
        "gateway_lifecycle_state": claim.get("gateway_lifecycle_state"),
        "gateway_delivery_recorded": claim.get("gateway_delivery_recorded"),
        "runner_state_authority": claim.get("runner_state_authority"),
        "model_provider_state_known": claim.get("model_provider_state_known"),
        "template_payload_included_in_saved_evidence": False,
    }


def _governed_summary(result: JsonObject) -> JsonObject:
    return {
        "status": result.get("status"),
        "request_id": result.get("request_id"),
        "tool_name": result.get("tool_name"),
        "is_error": result.get("is_error"),
        "identity_source": result.get("identity_source"),
        "workspace_id": result.get("workspace_id"),
        "configuration_generation": result.get("configuration_generation"),
        "configuration_digest": result.get("configuration_digest"),
        "offline_fallback_used": result.get("offline_fallback_used"),
        "tool_output_included_in_saved_evidence": False,
    }


def _receipt_summary(result: JsonObject) -> JsonObject:
    receipt = cast(JsonObject, result.get("receipt", {}))
    posture = cast(JsonObject, receipt.get("receipt_posture", {}))
    return {
        "report_id": receipt.get("report_id"),
        "receipt_disposition": receipt.get("receipt_disposition"),
        "evidence_status": receipt.get("evidence_status"),
        "quarantine_reason_code": posture.get("quarantine_reason_code"),
    }


def _mission_projection(detail: JsonObject) -> JsonObject:
    runner_reports = cast(JsonObject, detail.get("runner_reports", {}))
    governed_runs = cast(JsonObject, detail.get("governed_agent_runs", {}))
    cancellation = cast(JsonObject, detail.get("cancellation", {}))
    model_provider = cast(JsonObject, detail.get("model_provider", {}))
    delivery = cast(JsonObject, detail.get("delivery", {}))
    evidence = cast(JsonObject, detail.get("evidence", {}))
    return {
        "mission_id": detail.get("mission_id"),
        "lifecycle_state": detail.get("lifecycle_state"),
        "lifecycle_revision": detail.get("lifecycle_revision"),
        "gateway_state_authority": detail.get("gateway_state_authority"),
        "delivery_state": delivery.get("state"),
        "delivery_authority": delivery.get("authority"),
        "evidence_state": evidence.get("state"),
        "runner_latest": runner_reports.get("latest"),
        "runner_quarantined_count": runner_reports.get("quarantined_count"),
        "runner_report_conflict_count": runner_reports.get("report_conflict_count"),
        "governed_agent_run_count": governed_runs.get("count"),
        "governed_agent_run_correlation_basis": governed_runs.get("correlation_basis"),
        "cancellation_recorded": cancellation.get("recorded"),
        "cancellation_observed_by_node": cancellation.get("observed_by_node"),
        "runner_reported_canceled": cancellation.get("runner_reported_canceled"),
        "runner_process_stop_proven": cancellation.get("runner_process_stop_proven"),
        "attention_codes": detail.get("attention_codes"),
        "model_provider_state": model_provider.get("state"),
        "model_inference_known": model_provider.get("inference_known"),
        "model_output_verified": model_provider.get("output_verified"),
    }


def _parse_json(value: str) -> JsonObject:
    document: Any = json.loads(value)
    if not isinstance(document, dict):
        raise RuntimeError("POC response is not an object")
    return cast(JsonObject, document)


def _required(document: JsonObject, key: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"POC response is missing {key}")
    return value


def _write(path: Path, document: JsonObject) -> None:
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())

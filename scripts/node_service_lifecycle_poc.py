"""Run the bounded Ithildin Node service lifecycle POC with real containers."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, cast

from ithildin_api.node_configuration import generate_node_configuration_signing_keypair
from ithildin_audit_core import generate_audit_signing_keypair
from ithildin_schemas import JsonObject

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_ROOT = ROOT / "var/node-service-lifecycle-poc-20260716"
IMAGE = "ithildin/node:local"
VOLUME = "ithildin-node-lifecycle-poc-20260716"
SERVICE_CONTAINER = "ithildin-node-lifecycle-poc-service"
HOST_API_URL = "http://127.0.0.1:8016"
CONTAINER_API_URL = "http://host.docker.internal:8016"
ADMIN_TOKEN = secrets.token_urlsafe(32)


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
    if evidence_root.exists():
        if not args.replace:
            raise SystemExit(f"evidence root already exists: {evidence_root}")
        if (
            evidence_root != DEFAULT_EVIDENCE_ROOT.resolve()
            and ROOT / "var" not in evidence_root.parents
        ):
            raise SystemExit("refusing to replace evidence outside the repository var directory")
        shutil.rmtree(evidence_root)
    for child in ("db", "logs", "keys", "evidence"):
        (evidence_root / child).mkdir(parents=True, exist_ok=True)
    _generate_keys(evidence_root)
    _docker(["volume", "rm", "-f", VOLUME], check=False)
    _docker(["volume", "create", VOLUME])
    gateway: subprocess.Popen[str] | None = None
    try:
        gateway = _start_gateway(evidence_root, phase="before-restart")
        issued = _request(
            "/nodes/enrollment-codes",
            {
                "workspace_id": "default",
                "display_name": "Hermes Node service lifecycle POC",
            },
        )
        enrollment_code = _required(issued, "enrollment_code")
        enrollment = _container(
            [
                "enroll",
                "--api-url",
                CONTAINER_API_URL,
                "--state",
                "/var/lib/ithildin-node/state.json",
                "--node-version",
                "0.1.0",
                "--runner-adapter",
                "hermes",
                "--deployment-topology",
                "docker_sidecar",
                "--enrollment-code-stdin",
            ],
            input_text=enrollment_code + "\n",
        )
        enrollment_document = _parse_json(enrollment.stdout)
        _write(evidence_root / "evidence/enrollment-safe.json", enrollment_document)
        node_id = _required(enrollment_document, "node_id")
        assignment = _request(
            f"/nodes/{node_id}/configurations",
            {
                "minimum_node_version": "0.2.0",
                "heartbeat_interval_seconds": 15,
                "offline_posture": "deny_governed_actions",
                "evidence_buffer_max_events": 1000,
                "validity_seconds": 86400,
            },
        )
        _write(evidence_root / "evidence/assignment.json", assignment)
        initial = _service_cycle("0.1.0")
        _write(evidence_root / "evidence/initial-cycle.json", _parse_json(initial.stdout))
        _write(evidence_root / "evidence/initial-inventory.json", _inventory(node_id))
        _docker(["rm", "-f", SERVICE_CONTAINER], check=False)
        _docker(
            [
                "run",
                "--detach",
                "--name",
                SERVICE_CONTAINER,
                *_container_security_options(),
                IMAGE,
                "run",
                "--state",
                "/var/lib/ithildin-node/state.json",
                "--configuration",
                "/var/lib/ithildin-node/configuration.json",
                "--node-version",
                "0.1.0",
                "--runner-adapter",
                "hermes",
                "--deployment-topology",
                "docker_sidecar",
            ]
        )
        _wait_for_container_log(SERVICE_CONTAINER)
        duplicate = _service_cycle("0.1.0", check=False)
        _write(
            evidence_root / "evidence/concurrent-service-denial.json",
            {
                "exit_code": duplicate.returncode,
                "identity_already_in_use": "Node service identity is already in use"
                in duplicate.stderr,
            },
        )
        _docker(["stop", "--time", "5", SERVICE_CONTAINER])
        service_logs = _docker(["logs", SERVICE_CONTAINER]).stdout.splitlines()
        _write(
            evidence_root / "evidence/graceful-service-stop.json",
            {
                "events": [_parse_json(line) for line in service_logs if line.strip()],
                "stopped": any('"status": "stopped"' in line for line in service_logs),
            },
        )
        _docker(["rm", SERVICE_CONTAINER])
        image_config = _parse_json(
            _docker(["image", "inspect", IMAGE, "--format", "{{json .Config}}"]).stdout
        )
        _write(evidence_root / "evidence/image-config.json", image_config)
        state_mode = _docker(
            [
                "run",
                "--rm",
                "--read-only",
                "--volume",
                f"{VOLUME}:/var/lib/ithildin-node",
                "--entrypoint",
                "stat",
                IMAGE,
                "-c",
                "%a",
                "/var/lib/ithildin-node/state.json",
                "/var/lib/ithildin-node/configuration.json",
                "/var/lib/ithildin-node/.service.lock",
            ]
        ).stdout.splitlines()
        _write(
            evidence_root / "evidence/private-file-modes.json",
            {
                "state": state_mode[0],
                "configuration": state_mode[1],
                "service_lease": state_mode[2],
            },
        )
        _stop_gateway(gateway)
        gateway = None
        partition = _service_cycle("0.1.0", check=False)
        _write(
            evidence_root / "evidence/partition-cycle.json",
            {"exit_code": partition.returncode, **_parse_json(partition.stdout)},
        )
        gateway = _start_gateway(evidence_root, phase="after-restart")
        _write(evidence_root / "evidence/restart-inventory.json", _inventory(node_id))
        upgraded = _service_cycle("0.2.0")
        _write(evidence_root / "evidence/operator-upgrade-cycle.json", _parse_json(upgraded.stdout))
        _write(evidence_root / "evidence/operator-upgrade-inventory.json", _inventory(node_id))
        rolled_back = _service_cycle("0.1.0")
        _write(
            evidence_root / "evidence/operator-rollback-cycle.json",
            _parse_json(rolled_back.stdout),
        )
        _write(evidence_root / "evidence/operator-rollback-inventory.json", _inventory(node_id))
        final_status = _container(
            ["status", "--state", "/var/lib/ithildin-node/state.json"]
        )
        _write(evidence_root / "evidence/final-node-status.json", _parse_json(final_status.stdout))
        _write(evidence_root / "evidence/revocation.json", _request(f"/nodes/{node_id}/revoke", {}))
        revoked = _service_cycle("0.3.0", check=False)
        _write(
            evidence_root / "evidence/post-revocation-cycle.json",
            {"exit_code": revoked.returncode, **_parse_json(revoked.stdout)},
        )
    finally:
        if gateway is not None:
            _stop_gateway(gateway)
        _docker(["rm", "-f", SERVICE_CONTAINER], check=False)
        _docker(["volume", "rm", "-f", VOLUME], check=False)
    print(f"Built Node service lifecycle POC evidence at {evidence_root}")
    return 0


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
    environment = {
        **os.environ,
        "ITHILDIN_ADMIN_TOKEN": ADMIN_TOKEN,
        "ITHILDIN_ALLOW_DEV_ADMIN_TOKEN": "false",
        "ITHILDIN_DB_PATH": str(root / "db/ithildin.sqlite3"),
        "ITHILDIN_AUDIT_LOG_PATH": str(root / "logs/audit.jsonl"),
        "ITHILDIN_AUDIT_SIGNING_PRIVATE_KEY_PATH": str(root / "keys/audit-private.pem"),
        "ITHILDIN_AUDIT_SIGNING_PUBLIC_KEY_PATH": str(root / "keys/audit-public.pem"),
        "ITHILDIN_NODE_CONFIGURATION_SIGNING_PRIVATE_KEY_PATH": str(
            root / "keys/configuration-private.pem"
        ),
        "ITHILDIN_NODE_CONFIGURATION_SIGNING_PUBLIC_KEY_PATH": str(
            root / "keys/configuration-public.pem"
        ),
        "ITHILDIN_OTEL_ENABLED": "false",
    }
    log_path = root / f"logs/gateway-{phase}.log"
    log_handle = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [
            "uv",
            "run",
            "uvicorn",
            "ithildin_api.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8016",
        ],
        cwd=ROOT,
        env=environment,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    log_handle.close()
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Gateway failed to start; inspect {log_path}")
        try:
            with urllib.request.urlopen(f"{HOST_API_URL}/healthz", timeout=1):
                return process
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.2)
    process.terminate()
    raise RuntimeError("Gateway did not become healthy")


def _stop_gateway(process: subprocess.Popen[str]) -> None:
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _service_cycle(version: str, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return _container(
        [
            "run",
            "--state",
            "/var/lib/ithildin-node/state.json",
            "--configuration",
            "/var/lib/ithildin-node/configuration.json",
            "--node-version",
            version,
            "--runner-adapter",
            "hermes",
            "--deployment-topology",
            "docker_sidecar",
            "--max-cycles",
            "1",
            "--retry-initial-seconds",
            "1",
            "--retry-max-seconds",
            "1",
        ],
        check=check,
    )


def _container(
    arguments: list[str], *, input_text: str | None = None, check: bool = True
) -> subprocess.CompletedProcess[str]:
    interactive = ["--interactive"] if input_text is not None else []
    return _docker(
        [
            "run",
            "--rm",
            *interactive,
            *_container_security_options(),
            IMAGE,
            *arguments,
        ],
        input_text=input_text,
        check=check,
    )


def _container_security_options() -> list[str]:
    return [
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--pids-limit",
        "64",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=16m",
        "--add-host",
        "host.docker.internal:host-gateway",
        "--volume",
        f"{VOLUME}:/var/lib/ithildin-node",
    ]


def _wait_for_container_log(name: str) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        result = _docker(["logs", name], check=False)
        if '"status": "synchronized"' in result.stdout:
            return
        time.sleep(0.2)
    raise RuntimeError("Node service container did not complete its first synchronization")


def _docker(
    arguments: list[str], *, input_text: str | None = None, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", *arguments],
        cwd=ROOT,
        input=input_text,
        capture_output=True,
        text=True,
        check=check,
    )


def _request(path: str, payload: JsonObject | None = None) -> JsonObject:
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    data = None
    method = "GET"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        method = "POST"
    request = urllib.request.Request(
        f"{HOST_API_URL}{path}", data=data, headers=headers, method=method
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return _parse_json(response.read().decode())


def _inventory(node_id: str) -> JsonObject:
    return _request(f"/nodes/{node_id}")


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

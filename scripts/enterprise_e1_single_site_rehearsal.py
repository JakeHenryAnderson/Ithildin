"""Run and record an isolated Enterprise E1 single-site deployment rehearsal."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import enterprise_e1_single_site

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_BASE = ROOT / "var/enterprise-e1-single-site"
COMPOSE_PATH = ROOT / "deploy/single-site/compose.yaml"
REPORT_NAME = "enterprise-e1-single-site-rehearsal.json"
RUN_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{16}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
COMMAND_TIMEOUT_SECONDS = 1200


class RehearsalError(RuntimeError):
    """A closed, secret-free deployment-rehearsal failure."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--api-port", type=int, default=18081)
    parser.add_argument("--ui-port", type=int, default=15174)
    args = parser.parse_args()
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + f"-{secrets.token_hex(8)}"
    run_root = confined_run_root(EVIDENCE_BASE / run_id)
    try:
        report = run_rehearsal(
            run_root,
            run_id=run_id,
            api_port=args.api_port,
            ui_port=args.ui_port,
        )
    except (OSError, RehearsalError, enterprise_e1_single_site.SingleSiteError) as exc:
        try:
            shutil.rmtree(run_root)
        except FileNotFoundError:
            pass
        except OSError:
            print(
                f"Enterprise E1 partial rehearsal cleanup required: {run_root}",
                file=sys.stderr,
            )
        print(f"Enterprise E1 single-site rehearsal refused: {exc}", file=sys.stderr)
        return 1
    print(f"Enterprise E1 single-site rehearsal passed: {report['result']}")
    print(f"Safe evidence: {run_root.relative_to(ROOT) / REPORT_NAME}")
    return 0


def confined_run_root(selected: Path) -> Path:
    base = Path(os.path.abspath(EVIDENCE_BASE))
    root = Path(os.path.abspath(selected))
    if root.parent != base or RUN_ID_RE.fullmatch(root.name) is None:
        raise RehearsalError("evidence_root_outside_confined_base")
    return root


def run_rehearsal(
    run_root: Path,
    *,
    run_id: str,
    api_port: int,
    ui_port: int,
) -> dict[str, Any]:
    _require_clean_candidate()
    _require_free_port(api_port)
    _require_free_port(ui_port)
    if api_port == ui_port:
        raise RehearsalError("ports_must_differ")
    _run(["docker", "compose", "version"], failure="compose_cli_unavailable")
    daemon = _run(
        ["docker", "info", "--format", "{{json .ServerVersion}}"],
        failure="docker_daemon_unavailable",
    ).stdout.strip()

    commit = _git("rev-parse", "HEAD")
    tree = _git("rev-parse", "HEAD^{tree}")
    if COMMIT_RE.fullmatch(commit) is None or COMMIT_RE.fullmatch(tree) is None:
        raise RehearsalError("candidate_identity_invalid")

    run_root.mkdir(parents=True, mode=0o700)
    os.chmod(run_root, 0o700)
    suffix = run_id.rsplit("-", 1)[1]
    site_id = f"e1-{suffix[:12]}"
    version = f"1.0.0-e1.{suffix}"
    project = f"ithildin-e1-{site_id}"
    api_image = f"ithildin/api:{version}"
    ui_image = f"ithildin/ui:{version}"
    runtime_directory = tempfile.TemporaryDirectory(prefix=f"ithildin-e1-{suffix}-")
    runtime_root = Path(runtime_directory.name)
    data_root = runtime_root / "state"
    inventory_path = runtime_root / "unreviewed-runtime-candidate.json"
    authority_path = runtime_root / "unavailable-runtime-authority.json"
    env_path = runtime_root / "rehearsal.env"
    token = secrets.token_urlsafe(32)
    cleanup_failures: list[str] = []

    try:
        _write_mode(inventory_path, b"{}\n", 0o400)
        _write_mode(authority_path, b"{}\n", 0o400)
        environment = {
            "ITHILDIN_E1_SITE_ID": site_id,
            "ITHILDIN_E1_VERSION": version,
            "ITHILDIN_E1_SOURCE_REVISION": commit,
            "ITHILDIN_E1_API_PORT": str(api_port),
            "ITHILDIN_E1_UI_PORT": str(ui_port),
            "ITHILDIN_E1_DATA_ROOT": str(data_root),
            "ITHILDIN_E1_RUNTIME_INVENTORY_PATH": str(inventory_path),
            "ITHILDIN_E1_RUNTIME_AUTHORITY_PATH": str(authority_path),
            "ITHILDIN_E1_EXPECTED_RUNTIME_POSTURE": "unreviewed_local",
            "ITHILDIN_ADMIN_TOKEN": token,
            "ITHILDIN_CONTAINER_UID": str(os.getuid()),
            "ITHILDIN_CONTAINER_GID": str(os.getgid()),
        }
        _write_mode(
            env_path,
            (
                "\n".join(f"{key}={value}" for key, value in environment.items()) + "\n"
            ).encode(),
            0o600,
        )
        config = enterprise_e1_single_site.validate_environment(environment, ROOT)
        enterprise_e1_single_site.bootstrap_state(config)
        shutil.copyfile(ROOT / "workspaces/local.yaml", data_root / "workspaces/local.yaml")
        os.chmod(data_root / "workspaces/local.yaml", 0o400)
    except Exception:
        runtime_directory.cleanup()
        raise

    observations: dict[str, Any] = {}
    image_labels: dict[str, dict[str, str]] = {}
    try:
        _compose(project, env_path, "up", "-d", "--build", "--wait")
        observations.update(enterprise_e1_single_site.probe_health(config))
        image_labels = {
            "api": _image_labels(api_image, version=version, revision=commit),
            "ui": _image_labels(ui_image, version=version, revision=commit),
        }
        _compose(project, env_path, "down")
        if _compose(project, env_path, "ps", "--all", "-q").stdout.strip():
            raise RehearsalError("exact_project_shutdown_incomplete")
        observations["state_after_shutdown"] = _state_observation(data_root)
        observations["exact_project_shutdown_complete"] = True
    finally:
        if _compose(project, env_path, "down", check=False).returncode != 0:
            cleanup_failures.append("compose_cleanup_failed")
        for image in (api_image, ui_image):
            if _run(["docker", "image", "rm", image], check=False).returncode != 0:
                cleanup_failures.append("image_cleanup_failed")
        token = ""
        runtime_directory.cleanup()

    if cleanup_failures:
        raise RehearsalError(sorted(set(cleanup_failures))[0])
    report = {
        "schema_version": "ithildin.enterprise-e1-single-site-rehearsal.v1",
        "result": "passed",
        "run_id": run_id,
        "candidate": {
            "source_commit": commit,
            "tree": tree,
            "version": version,
            "runtime_candidate_posture": "unreviewed_local",
            "reviewed_runtime_candidate": False,
        },
        "topology": {
            "services": ["ithildin-api", "ithildin-ui"],
            "loopback_only": True,
            "storage_backend": "sqlite",
            "optional_node_included": False,
            "docker_socket_mounted": False,
            "runtime_postgres_allowed": False,
        },
        "observations": observations,
        "image_labels": image_labels,
        "daemon_version_observed": json.loads(daemon),
        "authority": {
            "docker_lifecycle_invoked_by_operator": True,
            "docker_lifecycle_authority_granted_to_ithildin": False,
            "new_governed_power_authorized": False,
            "production_authorized": False,
            "promotion_allowed": False,
            "release_allowed": False,
            "human_uat_complete": False,
        },
        "cleanup": {
            "synthetic_state_retained": False,
            "safe_report_retained": True,
            "unique_images_removed": True,
            "exact_project_removed": True,
        },
        "nonclaims": [
            "The exact Git and OCI image identity is deployment-candidate provenance, "
            "not reviewed-runtime-candidate authorization.",
            "The rehearsal intentionally observed unreviewed_local runtime posture.",
            "The rehearsal used isolated synthetic state and did not touch ambient user data.",
            "Passing evidence is not release acceptance, production readiness, promotion, "
            "or human UAT.",
        ],
    }
    validate_report(report)
    _write_mode(
        run_root / REPORT_NAME,
        (json.dumps(report, indent=2, sort_keys=True) + "\n").encode(),
        0o600,
    )
    return report


def validate_report(report: dict[str, Any]) -> None:
    candidate = report.get("candidate")
    topology = report.get("topology")
    observations = report.get("observations")
    authority = report.get("authority")
    cleanup = report.get("cleanup")
    if report.get("result") != "passed" or not isinstance(candidate, dict):
        raise RehearsalError("report_result_invalid")
    if candidate.get("reviewed_runtime_candidate") is not False:
        raise RehearsalError("report_runtime_review_claim_invalid")
    if candidate.get("runtime_candidate_posture") != "unreviewed_local":
        raise RehearsalError("report_runtime_posture_invalid")
    if not isinstance(topology, dict) or topology.get("services") != [
        "ithildin-api",
        "ithildin-ui",
    ]:
        raise RehearsalError("report_topology_invalid")
    expected_observations = {
        "gateway_http_ready": True,
        "command_center_http_reachable": True,
        "authenticated_tool_count": 24,
        "storage_backend": "sqlite",
        "runtime_candidate_posture": "unreviewed_local",
        "exact_project_shutdown_complete": True,
    }
    if not isinstance(observations, dict) or any(
        observations.get(key) != value for key, value in expected_observations.items()
    ):
        raise RehearsalError("report_observations_invalid")
    if not isinstance(authority, dict) or any(
        authority.get(key) is not False
        for key in (
            "docker_lifecycle_authority_granted_to_ithildin",
            "new_governed_power_authorized",
            "production_authorized",
            "promotion_allowed",
            "release_allowed",
            "human_uat_complete",
        )
    ):
        raise RehearsalError("report_authority_invalid")
    if not isinstance(cleanup, dict) or cleanup.get("exact_project_removed") is not True:
        raise RehearsalError("report_cleanup_invalid")


def _state_observation(root: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        details = path.lstat()
        if stat.S_ISLNK(details.st_mode):
            raise RehearsalError("state_contains_symlink")
        if stat.S_ISREG(details.st_mode):
            records.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "size": details.st_size,
                    "sha256": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
    if not records:
        raise RehearsalError("state_after_shutdown_empty")
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    return {
        "regular_file_count": len(records),
        "manifest_digest": "sha256:" + hashlib.sha256(encoded).hexdigest(),
        "database_present": any(
            record["path"] == "gateway/db/ithildin.sqlite3" for record in records
        ),
        "audit_log_present": any(
            record["path"] == "gateway/logs/audit.jsonl" for record in records
        ),
    }


def _image_labels(image: str, *, version: str, revision: str) -> dict[str, str]:
    raw = _run(
        ["docker", "image", "inspect", image, "--format", "{{json .Config.Labels}}"],
        failure="image_inspect_failed",
    ).stdout
    try:
        labels = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RehearsalError("image_labels_invalid") from exc
    if not isinstance(labels, dict):
        raise RehearsalError("image_labels_invalid")
    expected = {
        "org.opencontainers.image.version": version,
        "org.opencontainers.image.revision": revision,
    }
    if any(labels.get(key) != value for key, value in expected.items()):
        raise RehearsalError("image_identity_mismatch")
    return expected


def _require_clean_candidate() -> None:
    if _git("status", "--porcelain"):
        raise RehearsalError("source_checkout_not_clean")


def _require_free_port(port: int) -> None:
    if port < 1024 or port > 65535:
        raise RehearsalError("port_outside_supported_range")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
        try:
            candidate.bind(("127.0.0.1", port))
        except OSError as exc:
            raise RehearsalError("loopback_port_unavailable") from exc


def _write_mode(path: Path, payload: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        os.write(descriptor, payload)
        os.fsync(descriptor)
        os.fchmod(descriptor, mode)
    finally:
        os.close(descriptor)


def _compose(
    project: str,
    env_path: Path,
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return _run(
        [
            "docker",
            "compose",
            "--project-name",
            project,
            "--env-file",
            str(env_path),
            "--file",
            str(COMPOSE_PATH),
            *args,
        ],
        failure="compose_command_failed",
        check=check,
    )


def _run(
    command: list[str],
    *,
    failure: str = "command_failed",
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RehearsalError(failure) from exc
    if check and result.returncode != 0:
        raise RehearsalError(failure)
    return result


def _git(*args: str) -> str:
    return _run(["git", *args], failure="git_candidate_state_unavailable").stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())

"""Exercise the isolated Local-v1 install, backup, failed-update, restore, and cleanup path."""

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
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_BASE = ROOT / "var/local-v1-operations"
RUN_ID = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
REPORT_NAME = "local-v1-operations.json"
COMMAND_TIMEOUT_SECONDS = 900
PROBE_TIMEOUT_SECONDS = 90

AUTHORITY = {
    "arbitrary_host_control_authorized": False,
    "docker_socket_mounted": False,
    "new_governed_power_authorized": False,
    "new_governed_tool": False,
    "production_authorized": False,
    "promotion_allowed": False,
    "release_allowed": False,
    "uat_complete": False,
}


class OperationsError(RuntimeError):
    """A closed, secret-free operations-rehearsal failure."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--api-port", type=int, default=18080)
    parser.add_argument("--ui-port", type=int, default=15173)
    args = parser.parse_args()

    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + f"-{secrets.token_hex(4)}"
    run_root = confined_run_root(EVIDENCE_BASE / run_id)
    try:
        report = run_rehearsal(
            run_root,
            run_id=run_id,
            api_port=args.api_port,
            ui_port=args.ui_port,
        )
    except (OSError, OperationsError, ValueError) as exc:
        print(f"Local-v1 operations rehearsal refused: {exc}", file=sys.stderr)
        return 1

    print(f"Local-v1 operations rehearsal passed: {report['result']}")
    print(f"Safe evidence: {run_root.relative_to(ROOT) / REPORT_NAME}")
    return 0


def confined_run_root(selected: Path) -> Path:
    base = Path(os.path.abspath(EVIDENCE_BASE))
    root = Path(os.path.abspath(selected))
    if root.parent != base or not RUN_ID.fullmatch(root.name):
        raise ValueError("operations evidence root is outside the confined base")
    _reject_symlink_components(base)
    _reject_symlink_components(root)
    return root


def run_rehearsal(
    run_root: Path,
    *,
    run_id: str,
    api_port: int,
    ui_port: int,
) -> dict[str, Any]:
    if run_root.name != run_id:
        raise ValueError("operations run identity does not match the selected root")
    _require_clean_candidate()
    _require_port(api_port)
    _require_port(ui_port)
    if api_port == ui_port:
        raise ValueError("API and UI ports must differ")
    _require_free_port(api_port)
    _require_free_port(ui_port)
    if shutil.which("docker") is None:
        raise OperationsError("docker_cli_unavailable")
    _run_command(["docker", "compose", "version"], failure="compose_cli_unavailable")
    _run_command(
        ["docker", "info", "--format", "{{json .ServerVersion}}"],
        failure="docker_daemon_unavailable",
    )

    commit = _git("rev-parse", "HEAD")
    tree = _git("rev-parse", "HEAD^{tree}")
    parent = _git("rev-parse", "HEAD^")
    if not all(COMMIT.fullmatch(value) for value in (commit, tree, parent)):
        raise OperationsError("candidate_identity_invalid")

    run_root.mkdir(parents=True, mode=0o700)
    os.chmod(run_root, 0o700)
    project = f"ithildin-lv1-ops-{run_id.rsplit('-', 1)[1]}"
    api_image = f"ithildin/api:lv1-ops-{run_id.rsplit('-', 1)[1]}"
    ui_image = f"ithildin/ui:lv1-ops-{run_id.rsplit('-', 1)[1]}"
    token = secrets.token_urlsafe(32)
    compose_paths: list[Path] = []
    cleanup_failures: list[str] = []
    current_state = run_root / "current-state"
    current_workspaces = run_root / "current-workspaces"
    backup_root = run_root / "backup"
    restored_state = run_root / "restored-state"
    restored_workspaces = run_root / "restored-workspaces"

    try:
        _prepare_state(current_state, current_workspaces)
        current_compose = run_root / "compose-current.json"
        _write_private_json(
            current_compose,
            compose_document(
                state_root=current_state,
                workspace_root=current_workspaces,
                api_port=api_port,
                ui_port=ui_port,
                api_image=api_image,
                ui_image=ui_image,
                token=token,
            ),
        )
        compose_paths.append(current_compose)
        _compose(project, current_compose, "up", "--build", "-d")
        _verify_stack(api_port=api_port, ui_port=ui_port, token=token)
        _compose(project, current_compose, "stop")

        source_manifest = snapshot_manifest(
            {"state": current_state, "workspaces": current_workspaces}
        )
        _copy_regular_tree(current_state, backup_root / "state")
        _copy_regular_tree(current_workspaces, backup_root / "workspaces")
        backup_manifest = snapshot_manifest(
            {"state": backup_root / "state", "workspaces": backup_root / "workspaces"}
        )
        if source_manifest != backup_manifest:
            raise OperationsError("backup_manifest_mismatch")

        failed_compose = run_root / "compose-failed-update.json"
        failed_document = compose_document(
            state_root=current_state,
            workspace_root=current_workspaces,
            api_port=api_port,
            ui_port=ui_port,
            api_image=api_image,
            ui_image=ui_image,
            token=token,
        )
        failed_document["services"]["ithildin-api"]["command"] = [
            "python",
            "-c",
            "raise SystemExit(23)",
        ]
        _write_private_json(failed_compose, failed_document)
        compose_paths.append(failed_compose)
        failed_update = _compose(
            project,
            failed_compose,
            "up",
            "-d",
            "--force-recreate",
            check=False,
        )
        if failed_update.returncode == 0 and _url_ready(
            f"http://127.0.0.1:{api_port}/healthz",
            headers={},
            timeout_seconds=5,
        ):
            raise OperationsError("failed_update_did_not_fail_closed")
        _compose(project, failed_compose, "down", "--remove-orphans", check=False)

        _copy_regular_tree(backup_root / "state", restored_state)
        _copy_regular_tree(backup_root / "workspaces", restored_workspaces)
        restored_manifest = snapshot_manifest(
            {"state": restored_state, "workspaces": restored_workspaces}
        )
        if restored_manifest != backup_manifest:
            raise OperationsError("restore_manifest_mismatch")

        restored_compose = run_root / "compose-restored.json"
        _write_private_json(
            restored_compose,
            compose_document(
                state_root=restored_state,
                workspace_root=restored_workspaces,
                api_port=api_port,
                ui_port=ui_port,
                api_image=api_image,
                ui_image=ui_image,
                token=token,
            ),
        )
        compose_paths.append(restored_compose)
        _compose(project, restored_compose, "up", "-d")
        _verify_stack(api_port=api_port, ui_port=ui_port, token=token)
        _compose(project, restored_compose, "down", "--remove-orphans")
    finally:
        for compose_path in reversed(compose_paths):
            result = _compose(
                project,
                compose_path,
                "down",
                "--remove-orphans",
                check=False,
            )
            if result.returncode != 0:
                cleanup_failures.append("compose_cleanup_failed")
        if not _remove_images(api_image, ui_image):
            cleanup_failures.append("image_cleanup_failed")
        for compose_path in compose_paths:
            compose_path.unlink(missing_ok=True)
        token = ""

    if cleanup_failures:
        raise OperationsError(sorted(set(cleanup_failures))[0])

    retained_manifest_digest = _digest_json(backup_manifest)
    for private_path in (
        current_state,
        current_workspaces,
        backup_root,
        restored_state,
        restored_workspaces,
    ):
        shutil.rmtree(private_path)
    report = {
        "schema_version": "ithildin.local-v1-operations.v1",
        "result": "passed",
        "candidate": {"commit": commit, "tree": tree, "parent": parent},
        "observations": {
            "fresh_state_initialized": True,
            "gateway_health_verified": True,
            "command_center_http_verified": True,
            "authenticated_tool_count": 24,
            "clean_stop_before_backup": True,
            "backup_manifest_matched": True,
            "failed_update_failed_closed": True,
            "restore_manifest_matched": True,
            "restored_files_owner_only": True,
            "restored_stack_health_verified": True,
            "exact_project_cleanup_complete": True,
            "unique_images_removed": True,
        },
        "backup": {
            "private_artifacts_retained": False,
            "manifest_digest": retained_manifest_digest,
            "scope": ["gateway_state", "configured_workspaces"],
        },
        "topology": {
            "loopback_only": True,
            "docker_socket_mounted": False,
            "optional_node_included": False,
            "model_provider_included": False,
        },
        "authority": AUTHORITY,
        "tool_count": 24,
        "nonclaims": [
            "The rehearsal uses synthetic isolated state and does not touch ambient local data.",
            "Restore evidence is not disaster recovery, production durability, or custody proof.",
            "The failed update is a fixed service-start failure, not every future upgrade failure.",
            "Optional Node state requires its separate revoke or re-enroll procedure.",
            "Passing evidence is not release acceptance or human UAT.",
        ],
    }
    _write_private_json(run_root / REPORT_NAME, report)
    return report


def compose_document(
    *,
    state_root: Path,
    workspace_root: Path,
    api_port: int,
    ui_port: int,
    api_image: str,
    ui_image: str,
    token: str,
) -> dict[str, Any]:
    uid = os.getuid()
    gid = os.getgid()
    return {
        "services": {
            "ithildin-api": {
                "build": {"context": str(ROOT), "dockerfile": "deploy/Dockerfile.api"},
                "image": api_image,
                "user": f"{uid}:{gid}",
                "environment": {
                    "ITHILDIN_ADMIN_TOKEN": token,
                    "ITHILDIN_ALLOW_DEV_ADMIN_TOKEN": "false",
                    "ITHILDIN_STORAGE_BACKEND": "sqlite",
                    "ITHILDIN_POSTGRES_DSN": "",
                    "ITHILDIN_DB_PATH": "/app/var/db/ithildin.sqlite3",
                    "ITHILDIN_AUDIT_LOG_PATH": "/app/var/logs/audit.jsonl",
                    "ITHILDIN_MANIFEST_DIR": "/app/tool-manifests",
                    "ITHILDIN_MANIFEST_LOCK_PATH": "/app/tool-manifests.lock.json",
                    "ITHILDIN_REQUIRE_MANIFEST_LOCK": "true",
                    "ITHILDIN_POLICY_PATH": "/app/policies/default.yaml",
                    "ITHILDIN_PRINCIPAL_REGISTRY_PATH": "/app/principals/local.yaml",
                    "ITHILDIN_WORKSPACE_ROOT": "/app/workspaces",
                    "ITHILDIN_WORKSPACE_REGISTRY_PATH": "/app/workspaces/local.yaml",
                    "ITHILDIN_TRUSTED_HOST_REGISTRY_PATH": "/app/trusted-hosts/local.yaml",
                    "ITHILDIN_RUNTIME_CANDIDATE_AUTHORIZATION_PATH": (
                        "/run/ithildin-authority/api-candidate.json"
                    ),
                    "ITHILDIN_OTEL_ENABLED": "false",
                    "ITHILDIN_HTTP_ALLOWLIST": "",
                },
                "ports": [f"127.0.0.1:{api_port}:8000"],
                "volumes": [
                    f"{ROOT / 'tool-manifests.lock.json'}:/app/tool-manifests.lock.json:ro",
                    f"{ROOT / 'tool-manifests'}:/app/tool-manifests:ro",
                    f"{ROOT / 'policies'}:/app/policies:ro",
                    f"{ROOT / 'principals'}:/app/principals:ro",
                    f"{ROOT / 'trusted-hosts'}:/app/trusted-hosts:ro",
                    f"{ROOT / 'scripts'}:/app/scripts:ro",
                    f"{workspace_root}:/app/workspaces",
                    f"{state_root}:/app/var",
                    (
                        f"{state_root / 'authority/api-candidate.json'}:"
                        "/run/ithildin-authority/api-candidate.json:ro"
                    ),
                ],
                "read_only": True,
                "tmpfs": ["/tmp"],
                "cap_drop": ["ALL"],
                "security_opt": ["no-new-privileges:true"],
                "pids_limit": 256,
                "healthcheck": {
                    "test": [
                        "CMD",
                        "python",
                        "-c",
                        (
                            "import urllib.request; "
                            "urllib.request.urlopen("
                            "'http://127.0.0.1:8000/healthz', timeout=2).read()"
                        ),
                    ],
                    "interval": "2s",
                    "timeout": "2s",
                    "retries": 20,
                    "start_period": "3s",
                },
            },
            "ithildin-ui": {
                "build": {
                    "context": str(ROOT),
                    "dockerfile": "deploy/Dockerfile.ui",
                    "args": {
                        "VITE_ITHILDIN_API_BASE_URL": (
                            f"http://127.0.0.1:{api_port}"
                        )
                    },
                },
                "image": ui_image,
                "ports": [f"127.0.0.1:{ui_port}:8080"],
                "read_only": True,
                "tmpfs": ["/tmp", "/var/cache/nginx", "/var/run"],
                "cap_drop": ["ALL"],
                "security_opt": ["no-new-privileges:true"],
                "pids_limit": 128,
                "depends_on": {
                    "ithildin-api": {"condition": "service_healthy"}
                },
            },
        }
    }


def snapshot_manifest(roots: dict[str, Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for label, root in sorted(roots.items()):
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root).as_posix()
            entry = os.lstat(path)
            if stat.S_ISLNK(entry.st_mode):
                raise OperationsError("snapshot_contains_symlink")
            if stat.S_ISDIR(entry.st_mode):
                continue
            if not stat.S_ISREG(entry.st_mode):
                raise OperationsError("snapshot_contains_non_regular_entry")
            records.append(
                {
                    "root": label,
                    "path": relative,
                    "size": entry.st_size,
                    "sha256": _sha256_file(path),
                }
            )
    return records


def _prepare_state(state_root: Path, workspace_root: Path) -> None:
    for path in (
        state_root / "db",
        state_root / "logs",
        state_root / "keys",
        state_root / "authority",
        workspace_root,
    ):
        path.mkdir(parents=True, mode=0o700)
    shutil.copy2(ROOT / "workspaces/local.yaml", workspace_root / "local.yaml")
    shutil.copytree(
        ROOT / "deploy/demo/workspace",
        workspace_root / "demo",
        copy_function=shutil.copy2,
    )
    _write_private_json(state_root / "authority/api-candidate.json", {})


def _copy_regular_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        raise OperationsError("copy_destination_exists")
    destination.mkdir(parents=True, mode=0o700)
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        entry = os.lstat(path)
        if stat.S_ISLNK(entry.st_mode):
            raise OperationsError("copy_source_contains_symlink")
        target = destination / relative
        if stat.S_ISDIR(entry.st_mode):
            target.mkdir(mode=0o700)
        elif stat.S_ISREG(entry.st_mode):
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target, follow_symlinks=False)
            os.chmod(target, 0o600)
        else:
            raise OperationsError("copy_source_contains_non_regular_entry")


def _verify_stack(*, api_port: int, ui_port: int, token: str) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    if not _url_ready(
        f"http://127.0.0.1:{api_port}/healthz",
        headers={},
        timeout_seconds=PROBE_TIMEOUT_SECONDS,
    ):
        raise OperationsError("gateway_health_not_ready")
    tools = _read_json(f"http://127.0.0.1:{api_port}/tools", headers=headers)
    if not isinstance(tools.get("tools"), list) or len(tools["tools"]) != 24:
        raise OperationsError("authenticated_tool_count_invalid")
    if not _url_ready(
        f"http://127.0.0.1:{ui_port}/",
        headers={},
        timeout_seconds=PROBE_TIMEOUT_SECONDS,
    ):
        raise OperationsError("command_center_not_ready")


def _url_ready(
    url: str,
    *,
    headers: dict[str, str],
    timeout_seconds: int,
) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=2) as response:
                if response.status == 200:
                    response.read(4096)
                    return True
        except (OSError, urllib.error.URLError):
            time.sleep(0.5)
    return False


def _read_json(url: str, *, headers: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            value = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise OperationsError("authenticated_probe_failed") from exc
    if not isinstance(value, dict):
        raise OperationsError("authenticated_probe_invalid")
    return value


def _compose(
    project: str,
    compose_path: Path,
    *arguments: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return _run_command(
        [
            "docker",
            "compose",
            "--project-name",
            project,
            "--file",
            str(compose_path),
            *arguments,
        ],
        failure="compose_command_failed",
        check=check,
    )


def _run_command(
    command: list[str],
    *,
    failure: str,
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
        raise OperationsError(failure) from exc
    if check and result.returncode != 0:
        raise OperationsError(failure)
    return result


def _remove_images(*images: str) -> bool:
    complete = True
    for image in images:
        exists = _run_command(
            ["docker", "image", "inspect", image],
            failure="image_inspection_failed",
            check=False,
        ).returncode == 0
        if not exists:
            continue
        removed = _run_command(
            ["docker", "image", "rm", image],
            failure="image_cleanup_failed",
            check=False,
        )
        remains = _run_command(
            ["docker", "image", "inspect", image],
            failure="image_inspection_failed",
            check=False,
        ).returncode == 0
        complete = complete and removed.returncode == 0 and not remains
    return complete


def _require_clean_candidate() -> None:
    if _git("status", "--porcelain=v1", "--untracked-files=all"):
        raise OperationsError("candidate_worktree_not_clean")


def _git(*arguments: str) -> str:
    result = _run_command(["git", *arguments], failure="candidate_git_query_failed")
    return result.stdout.strip()


def _require_port(port: int) -> None:
    if port < 1024 or port > 65535:
        raise ValueError("operations ports must be between 1024 and 65535")


def _require_free_port(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as exc:
            raise OperationsError("required_loopback_port_unavailable") from exc


def _reject_symlink_components(path: Path) -> None:
    try:
        relative = path.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError("operations evidence root is outside the repository") from exc
    for candidate in (ROOT, *(ROOT / parent for parent in relative.parents[::-1]), path):
        try:
            entry = os.lstat(candidate)
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(entry.st_mode):
            raise ValueError("operations evidence path contains a symlink")
        if not stat.S_ISDIR(entry.st_mode):
            raise ValueError("operations evidence path has a non-directory component")


def _write_private_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(131072), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _digest_json(value: Any) -> str:
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return f"sha256:{hashlib.sha256(serialized).hexdigest()}"


if __name__ == "__main__":
    raise SystemExit(main())

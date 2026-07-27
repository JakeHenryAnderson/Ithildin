"""Bootstrap, validate, or probe the bounded Enterprise E1 single-site deployment."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
ENV_KEYS = {
    "ITHILDIN_E1_SITE_ID",
    "ITHILDIN_E1_VERSION",
    "ITHILDIN_E1_SOURCE_REVISION",
    "ITHILDIN_E1_API_PORT",
    "ITHILDIN_E1_UI_PORT",
    "ITHILDIN_E1_DATA_ROOT",
    "ITHILDIN_E1_RUNTIME_INVENTORY_PATH",
    "ITHILDIN_E1_RUNTIME_AUTHORITY_PATH",
    "ITHILDIN_ADMIN_TOKEN",
    "ITHILDIN_CONTAINER_UID",
    "ITHILDIN_CONTAINER_GID",
}
SITE_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,31}$")
VERSION_RE = re.compile(
    r"^(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?$"
)
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
PLACEHOLDER_FRAGMENTS = ("replace-with", "/replace/", "change-me")
DEV_ADMIN_TOKEN = "dev-admin-token-change-me"
STATE_DIRECTORIES = (
    Path("gateway"),
    Path("gateway/db"),
    Path("gateway/keys"),
    Path("gateway/logs"),
    Path("gateway/signatures"),
    Path("workspaces"),
)


class SingleSiteError(RuntimeError):
    """Raised when the single-site deployment cannot proceed safely."""


@dataclass(frozen=True)
class SingleSiteConfig:
    site_id: str
    version: str
    source_revision: str
    api_port: int
    ui_port: int
    data_root: Path
    runtime_inventory_path: Path
    runtime_authority_path: Path
    container_uid: int
    container_gid: int

    def safe_summary(self) -> dict[str, Any]:
        return {
            "schema_version": "1",
            "site_id": self.site_id,
            "version": self.version,
            "source_revision": self.source_revision,
            "api_origin": f"http://127.0.0.1:{self.api_port}",
            "ui_origin": f"http://127.0.0.1:{self.ui_port}",
            "data_root": str(self.data_root),
            "runtime_inventory_path": str(self.runtime_inventory_path),
            "runtime_authority_path": str(self.runtime_authority_path),
            "container_uid": self.container_uid,
            "container_gid": self.container_gid,
            "admin_token_configured": True,
            "storage_backend": "sqlite",
            "tool_count_expected": 24,
            "optional_node_in_m1": False,
            "docker_authority_granted": False,
            "runtime_postgres_allowed": False,
            "production_identity_allowed": False,
            "human_uat_complete": False,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("bootstrap", "check", "probe", "shutdown-check"))
    parser.add_argument("--env-file", required=True, type=Path)
    args = parser.parse_args()
    try:
        environment = load_env_file(args.env_file)
        config = validate_environment(
            environment,
            ROOT,
            require_current_source=args.action in {"bootstrap", "check"},
        )
        if args.action == "bootstrap":
            bootstrap_state(config)
        else:
            validate_state(config)
        report = config.safe_summary()
        report["action"] = args.action
        report["state_valid"] = True
        if args.action == "probe":
            report["health"] = probe_health(config)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except SingleSiteError as exc:
        print(f"Enterprise E1 single-site {args.action} failed: {exc}", file=sys.stderr)
        return 2


def parse_env_text(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not key or key.strip() != key:
            raise SingleSiteError(f"environment line {line_number} is invalid")
        if key in values:
            raise SingleSiteError(f"environment contains duplicate key: {key}")
        values[key] = value
    if set(values) != ENV_KEYS:
        missing = sorted(ENV_KEYS - set(values))
        unexpected = sorted(set(values) - ENV_KEYS)
        raise SingleSiteError(
            f"environment keys are not closed; missing={missing}, unexpected={unexpected}"
        )
    return values


def load_env_file(path: Path) -> dict[str, str]:
    if not path.is_absolute():
        raise SingleSiteError("environment path must be absolute")
    try:
        status = path.lstat()
    except OSError as exc:
        raise SingleSiteError("environment file is unavailable") from exc
    if not stat.S_ISREG(status.st_mode):
        raise SingleSiteError("environment path must be a regular file")
    if stat.S_IMODE(status.st_mode) != 0o600:
        raise SingleSiteError("environment file mode must be 0600")
    if status.st_uid != os.getuid():
        raise SingleSiteError("environment file must be owned by the current operator")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise SingleSiteError("environment file cannot be read as UTF-8") from exc
    return parse_env_text(text)


def validate_environment(
    environment: dict[str, str],
    repo_root: Path,
    *,
    require_current_source: bool = True,
) -> SingleSiteConfig:
    site_id = environment["ITHILDIN_E1_SITE_ID"]
    version = environment["ITHILDIN_E1_VERSION"]
    source_revision = environment["ITHILDIN_E1_SOURCE_REVISION"]
    if SITE_RE.fullmatch(site_id) is None:
        raise SingleSiteError("site id must be a bounded lowercase slug")
    if VERSION_RE.fullmatch(version) is None:
        raise SingleSiteError("deployment version must be semantic and explicit")
    if COMMIT_RE.fullmatch(source_revision) is None:
        raise SingleSiteError("source revision must be one lowercase 40-hex commit")
    if require_current_source:
        current_revision = _git_one(repo_root, "rev-parse", "HEAD")
        if source_revision != current_revision:
            raise SingleSiteError("source revision does not match the checked-out candidate")
        if _git_one(repo_root, "status", "--porcelain"):
            raise SingleSiteError("source checkout must be clean before deployment")

    api_port = _bounded_integer(environment["ITHILDIN_E1_API_PORT"], "API port", 1024, 65535)
    ui_port = _bounded_integer(environment["ITHILDIN_E1_UI_PORT"], "UI port", 1024, 65535)
    if api_port == ui_port:
        raise SingleSiteError("API and UI ports must be distinct")
    container_uid = _bounded_integer(
        environment["ITHILDIN_CONTAINER_UID"], "container UID", 1, 2**31 - 1
    )
    container_gid = _bounded_integer(
        environment["ITHILDIN_CONTAINER_GID"], "container GID", 1, 2**31 - 1
    )
    if container_uid != os.getuid() or container_gid != os.getgid():
        raise SingleSiteError("container UID/GID must match the current state owner")

    data_root = _absolute_path(environment["ITHILDIN_E1_DATA_ROOT"], "data root")
    inventory_path = _absolute_path(
        environment["ITHILDIN_E1_RUNTIME_INVENTORY_PATH"],
        "runtime inventory path",
    )
    authority_path = _absolute_path(
        environment["ITHILDIN_E1_RUNTIME_AUTHORITY_PATH"],
        "runtime authority path",
    )
    resolved_repo = repo_root.resolve(strict=True)
    resolved_data = data_root.resolve(strict=False)
    if _is_relative_to(resolved_data, resolved_repo):
        raise SingleSiteError("data root must remain outside the source checkout")
    if resolved_data in {Path("/"), Path.home().resolve()} or len(resolved_data.parts) < 4:
        raise SingleSiteError("data root is too broad")
    for label, path in (
        ("runtime inventory", inventory_path),
        ("runtime authority record", authority_path),
    ):
        if _is_relative_to(path.resolve(strict=False), resolved_repo):
            raise SingleSiteError(f"{label} must remain outside the source checkout")
    _validate_evidence_file(
        inventory_path,
        label="runtime inventory",
        allowed_modes={0o600, 0o644},
    )
    _validate_evidence_file(
        authority_path,
        label="runtime authority record",
        allowed_modes={0o600},
    )

    token = environment["ITHILDIN_ADMIN_TOKEN"]
    if (
        len(token) < 32
        or token == DEV_ADMIN_TOKEN
        or any(fragment in token.lower() for fragment in PLACEHOLDER_FRAGMENTS)
        or token.strip() != token
        or any(ord(character) < 33 or ord(character) > 126 for character in token)
    ):
        raise SingleSiteError("admin token is placeholder, weak, or unsafe")
    return SingleSiteConfig(
        site_id=site_id,
        version=version,
        source_revision=source_revision,
        api_port=api_port,
        ui_port=ui_port,
        data_root=data_root,
        runtime_inventory_path=inventory_path,
        runtime_authority_path=authority_path,
        container_uid=container_uid,
        container_gid=container_gid,
    )


def bootstrap_state(config: SingleSiteConfig) -> None:
    _ensure_private_directory(config.data_root, create=True)
    for relative in STATE_DIRECTORIES:
        _ensure_private_directory(config.data_root / relative, create=True)
    validate_state(config)


def validate_state(config: SingleSiteConfig) -> None:
    _ensure_private_directory(config.data_root, create=False)
    for relative in STATE_DIRECTORIES:
        _ensure_private_directory(config.data_root / relative, create=False)
    _validate_evidence_file(
        config.runtime_inventory_path,
        label="runtime inventory",
        allowed_modes={0o600, 0o644},
    )
    _validate_evidence_file(
        config.runtime_authority_path,
        label="runtime authority record",
        allowed_modes={0o600},
    )


def probe_health(config: SingleSiteConfig) -> dict[str, Any]:
    api_url = f"http://127.0.0.1:{config.api_port}/healthz"
    ui_url = f"http://127.0.0.1:{config.ui_port}/"
    api_payload = _bounded_get(api_url, 4096)
    try:
        api_document = json.loads(api_payload)
    except json.JSONDecodeError as exc:
        raise SingleSiteError("Gateway health response is not valid JSON") from exc
    if api_document != {"status": "ok", "service": "ithildin-api"}:
        raise SingleSiteError("Gateway health response is not the expected bounded document")
    ui_payload = _bounded_get(ui_url, 65536)
    if b"<html" not in ui_payload.lower():
        raise SingleSiteError("Command Center response is not an HTML document")
    return {
        "gateway_http_ready": True,
        "command_center_http_reachable": True,
        "node_connectivity": "not_part_of_e1_m1",
        "runner_state": "unknown",
        "model_provider_state": "unknown",
    }


def _bounded_get(url: str, maximum_bytes: int) -> bytes:
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            if response.status != 200:
                raise SingleSiteError("bounded loopback health probe returned non-200")
            payload = cast(bytes, response.read(maximum_bytes + 1))
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise SingleSiteError("bounded loopback health probe failed") from exc
    if len(payload) > maximum_bytes:
        raise SingleSiteError("bounded loopback health response is too large")
    return payload


def _ensure_private_directory(path: Path, *, create: bool) -> None:
    try:
        status = path.lstat()
    except FileNotFoundError:
        if not create:
            raise SingleSiteError(f"required state directory is missing: {path.name}") from None
        try:
            path.mkdir(mode=0o700)
            status = path.lstat()
        except OSError as exc:
            raise SingleSiteError(f"state directory cannot be created: {path.name}") from exc
    except OSError as exc:
        raise SingleSiteError(f"state directory cannot be inspected: {path.name}") from exc
    if not stat.S_ISDIR(status.st_mode):
        raise SingleSiteError(f"state path is not a directory: {path.name}")
    if stat.S_IMODE(status.st_mode) != 0o700:
        raise SingleSiteError(f"state directory mode must be 0700: {path.name}")
    if status.st_uid != os.getuid() or status.st_gid != os.getgid():
        raise SingleSiteError(f"state directory ownership mismatch: {path.name}")


def _validate_evidence_file(
    path: Path,
    *,
    label: str,
    allowed_modes: set[int],
) -> None:
    try:
        status = path.lstat()
    except OSError as exc:
        raise SingleSiteError(f"{label} is unavailable") from exc
    if not stat.S_ISREG(status.st_mode):
        raise SingleSiteError(f"{label} must be a regular file")
    if stat.S_IMODE(status.st_mode) not in allowed_modes:
        rendered_modes = "/".join(f"{mode:04o}" for mode in sorted(allowed_modes))
        raise SingleSiteError(f"{label} mode must be {rendered_modes}")
    if status.st_uid != os.getuid():
        raise SingleSiteError(f"{label} must be operator-owned")
    if status.st_size == 0 or status.st_size > 65536:
        raise SingleSiteError(f"{label} size is invalid")


def _bounded_integer(value: str, label: str, minimum: int, maximum: int) -> int:
    if not value.isascii() or not value.isdecimal():
        raise SingleSiteError(f"{label} must be a decimal integer")
    number = int(value)
    if number < minimum or number > maximum:
        raise SingleSiteError(f"{label} is outside the supported range")
    return number


def _absolute_path(value: str, label: str) -> Path:
    path = Path(value)
    placeholder_present = any(
        fragment in value.lower() for fragment in PLACEHOLDER_FRAGMENTS
    )
    if not path.is_absolute() or placeholder_present:
        raise SingleSiteError(f"{label} must be an explicit absolute path")
    return path


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _git_one(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


if __name__ == "__main__":
    raise SystemExit(main())

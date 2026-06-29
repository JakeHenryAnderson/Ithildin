"""Report bounded local environment diagnostics for the optional live demo."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/live-demo-environment-diagnostics.md"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
COMMAND_TIMEOUT_SECONDS = 8


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = build_report(ROOT)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    failures: list[str] = []
    missing = [marker.as_posix() for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        failures.append("must be run from Ithildin repo root; missing " + ", ".join(missing))

    docker_path = shutil.which("docker")
    compose_version = _run([docker_path, "compose", "version"]) if docker_path else _missing()
    docker_info = _run([docker_path, "info", "--format", "json"]) if docker_path else _missing()
    host = _host_report()
    rosetta = _rosetta_report(host)
    compose_demo_ready = bool(
        docker_path
        and compose_version["status"] == "ok"
        and docker_info["status"] == "ok"
    )

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "diagnostics_doc": DOC_REL,
        "generated_at": datetime.now(UTC).isoformat(),
        "repo_root": str(repo_root),
        "host": host,
        "docker": {
            "cli_path": docker_path,
            "cli_available": docker_path is not None,
            "compose_version": compose_version,
            "daemon_info": docker_info,
        },
        "rosetta": rosetta,
        "compose_demo_ready": compose_demo_ready,
        "safe_next_actions": _safe_next_actions(
            docker_path=docker_path,
            compose_version=compose_version,
            docker_info=docker_info,
            compose_demo_ready=compose_demo_ready,
            rosetta=rosetta,
        ),
        "does_not_do": [
            "start Docker Desktop",
            "start containers",
            "stop containers",
            "pull images",
            "build images",
            "call governed tools",
            "read secrets",
            "change Rosetta or Docker settings",
        ],
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin live-demo environment diagnostics",
        f"valid: {str(report['valid']).lower()}",
        f"diagnostics_doc: {report['diagnostics_doc']}",
        f"platform: {report['host']['platform']}",
        f"machine: {report['host']['machine']}",
        f"python_version: {report['host']['python_version']}",
        f"docker_cli_available: {str(report['docker']['cli_available']).lower()}",
        f"docker_cli_path: {report['docker']['cli_path'] or 'not_found'}",
        f"docker_compose_status: {report['docker']['compose_version']['status']}",
        f"docker_daemon_status: {report['docker']['daemon_info']['status']}",
        f"rosetta_check_status: {report['rosetta']['status']}",
        f"compose_demo_ready: {str(report['compose_demo_ready']).lower()}",
        "safe_next_actions:",
        *[f"- {action}" for action in report["safe_next_actions"]],
        "does_not_do:",
        *[f"- {item}" for item in report["does_not_do"]],
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _host_report() -> dict[str, str]:
    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
    }


def _rosetta_report(host: dict[str, str]) -> dict[str, Any]:
    if host["system"] != "Darwin":
        return {
            "status": "not_applicable",
            "safe_error": None,
            "hint": "Rosetta is macOS-specific.",
        }
    if host["machine"] != "arm64":
        return {
            "status": "not_required",
            "safe_error": None,
            "hint": "Host is not Apple Silicon arm64.",
        }
    result = _run(["/usr/sbin/pkgutil", "--pkg-info", "com.apple.pkg.RosettaUpdateAuto"])
    if result["status"] == "ok":
        status = "installed"
        hint = "Rosetta package receipt is present."
    elif result["status"] == "timeout":
        status = "unknown_timeout"
        hint = "Rosetta package receipt check timed out."
    else:
        status = "not_confirmed"
        hint = (
            "Rosetta package receipt was not confirmed; update macOS/Rosetta "
            "if Docker requires it."
        )
    return {"status": status, "safe_error": result["safe_error"], "hint": hint}


def _run(command: list[str | None]) -> dict[str, Any]:
    safe_command = [part for part in command if part]
    if not safe_command:
        return _missing()
    try:
        completed = subprocess.run(
            safe_command,
            check=False,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "returncode": 124, "safe_error": "command timed out"}
    except OSError as exc:
        return {"status": "error", "returncode": None, "safe_error": type(exc).__name__}
    status = "ok" if completed.returncode == 0 else "error"
    safe_error = None
    if completed.returncode != 0:
        safe_error = (completed.stderr or completed.stdout).strip()[:200] or "command failed"
    return {"status": status, "returncode": completed.returncode, "safe_error": safe_error}


def _missing() -> dict[str, Any]:
    return {"status": "missing", "returncode": None, "safe_error": "docker CLI not found"}


def _safe_next_actions(
    *,
    docker_path: str | None,
    compose_version: dict[str, Any],
    docker_info: dict[str, Any],
    compose_demo_ready: bool,
    rosetta: dict[str, Any],
) -> list[str]:
    if compose_demo_ready:
        return [
            "run make live-demo-preflight",
            "run make demo-seed",
            "run make compose-up && make compose-smoke",
        ]
    actions = ["use non-Compose evidence commands until the optional local stack is healthy"]
    if not docker_path:
        actions.append("install or repair Docker Desktop before running Compose demo commands")
    elif compose_version["status"] != "ok":
        actions.append("repair Docker Compose CLI integration")
    elif docker_info["status"] == "timeout":
        actions.append("restart/update Docker Desktop; docker info timed out")
    elif docker_info["status"] != "ok":
        actions.append("start or repair the Docker Desktop daemon")
    if rosetta["status"] in {"not_confirmed", "unknown_timeout"}:
        actions.append("update macOS/Rosetta if Docker Desktop requests it")
    return actions


if __name__ == "__main__":
    raise SystemExit(main())

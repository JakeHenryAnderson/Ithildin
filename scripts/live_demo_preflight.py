"""Run a secret-free live-demo preflight for the local-preview workbench."""

from __future__ import annotations

import argparse
import json
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import no_new_powers_guardrail, tool_surface_invariant_gate

ROOT = Path(__file__).resolve().parents[1]
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]
REQUIRED_MAKE_TARGETS = [
    "demo-seed",
    "compose-up",
    "compose-smoke",
    "demo-flow",
    "live-demo-status",
    "live-demo-smoke",
    "live-demo-evidence-summary",
    "live-demo-packet",
    "operator-sandbox-demo-packet",
    "agent-run-correlation-packet",
    "signed-evidence-demo",
    "negative-review-transcripts",
    "review-candidate",
]
SAMPLE_ADMIN_TOKEN = "dev-admin-token-change-me"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    report = build_report(ROOT)
    if args.json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_human(report)
    return 0 if report["valid"] else 1


def build_report(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    failures: list[str] = []
    warnings: list[str] = []
    _check_project_root(repo_root, failures)

    env_path = repo_root / ".env"
    env_source = ".env" if env_path.exists() else ".env.example"
    env = _read_env(repo_root / env_source, failures)
    admin_token_configured = bool(env.get("ITHILDIN_ADMIN_TOKEN"))
    sample_token_active = env.get("ITHILDIN_ADMIN_TOKEN") == SAMPLE_ADMIN_TOKEN
    dev_token_allowed = _truthy(env.get("ITHILDIN_ALLOW_DEV_ADMIN_TOKEN"))
    if not admin_token_configured:
        failures.append(f"{env_source} does not configure ITHILDIN_ADMIN_TOKEN")
    if sample_token_active and not dev_token_allowed:
        failures.append("sample admin token is active without ITHILDIN_ALLOW_DEV_ADMIN_TOKEN=true")
    if sample_token_active and dev_token_allowed:
        warnings.append("sample admin token is active for local demo; replace it before sharing")

    compose = (repo_root / "deploy/docker-compose.yml").read_text(encoding="utf-8")
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    targets = _make_targets(makefile)
    missing_targets = sorted(set(REQUIRED_MAKE_TARGETS) - targets)
    if missing_targets:
        failures.append(f"missing Make targets: {', '.join(missing_targets)}")

    loopback_ports_valid = all(
        marker in compose
        for marker in ['"127.0.0.1:8000:8000"', '"127.0.0.1:5173:8080"']
    )
    if not loopback_ports_valid:
        failures.append("Compose API/UI ports are not loopback-bound")
    docker_socket_mounted = "/var/run/docker.sock" in compose
    if docker_socket_mounted:
        failures.append("Compose mounts the Docker socket")
    compose_read_only = compose.count("read_only: true") >= 2
    if not compose_read_only:
        failures.append("Compose services are not read-only")
    no_new_privileges = compose.count("no-new-privileges:true") >= 2
    if not no_new_privileges:
        failures.append("Compose services are missing no-new-privileges")
    cap_drop_all = compose.count("cap_drop:") >= 2 and compose.count("- ALL") >= 2
    if not cap_drop_all:
        failures.append("Compose services do not drop all capabilities")

    for required_path in [
        "deploy/demo/workspace",
        "workspaces/local.yaml",
        "principals/local.yaml",
        "tool-manifests.lock.json",
    ]:
        if not (repo_root / required_path).exists():
            failures.append(f"missing live-demo input: {required_path}")

    storage_backend = env.get("ITHILDIN_STORAGE_BACKEND", "sqlite")
    if storage_backend != "sqlite":
        failures.append(f"live demo expects sqlite storage, got {storage_backend!r}")
    telemetry_enabled = _truthy(env.get("ITHILDIN_OTEL_ENABLED"))
    if telemetry_enabled:
        failures.append("live demo expects telemetry disabled by default")
    http_allowlist_count = _count_csv(env.get("ITHILDIN_HTTP_ALLOWLIST", ""))

    compose_available = _compose_available()
    if not compose_available:
        warnings.append("Docker Compose was not detected; compose demo commands may be skipped")
    signing_keys_available = all(
        (repo_root / path).exists()
        for path in [
            "var/keys/audit-ed25519-private.pem",
            "var/keys/audit-ed25519-public.pem",
        ]
    )
    if not signing_keys_available:
        warnings.append("runtime audit signing keys are absent; use fixture signed-evidence demo")

    tool_count = _tool_count(repo_root, failures)
    no_new_power_failures = no_new_powers_guardrail.build_report(repo_root)["failures"]
    tool_surface_report = tool_surface_invariant_gate.build_report(repo_root)
    if no_new_power_failures:
        failures.extend(f"no-new-powers: {failure}" for failure in no_new_power_failures)
    if not tool_surface_report["valid"]:
        failures.append("tool-surface invariant gate failed")

    return {
        "valid": not failures,
        "repo_root": str(repo_root),
        "platform": platform.platform(),
        "env_source": env_source,
        "admin_token_configured": admin_token_configured,
        "sample_admin_token_active": sample_token_active,
        "dev_admin_token_allowed": dev_token_allowed,
        "storage_backend": storage_backend,
        "telemetry_enabled": telemetry_enabled,
        "http_allowlist_count": http_allowlist_count,
        "tool_count": tool_count,
        "expected_tool_count": 23,
        "tool_surface_valid": bool(tool_surface_report["valid"]),
        "new_power_classes_allowed": bool(no_new_power_failures),
        "compose_available": compose_available,
        "loopback_ports_valid": loopback_ports_valid,
        "docker_socket_mounted": docker_socket_mounted,
        "compose_read_only": compose_read_only,
        "compose_no_new_privileges": no_new_privileges,
        "compose_cap_drop_all": cap_drop_all,
        "runtime_signing_keys_available": signing_keys_available,
        "warnings": warnings,
        "failures": failures,
        "recommendations": _recommendations(warnings, failures),
    }


def _check_project_root(repo_root: Path, failures: list[str]) -> None:
    missing = [path.as_posix() for path in PROJECT_MARKERS if not (repo_root / path).exists()]
    if missing:
        failures.append(f"must be run from Ithildin repo root; missing {', '.join(missing)}")


def _read_env(path: Path, failures: list[str]) -> dict[str, str]:
    if not path.exists():
        failures.append(f"missing env file: {path.name}")
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _make_targets(makefile: str) -> set[str]:
    targets: set[str] = set()
    for line in makefile.splitlines():
        match = re.match(r"^([A-Za-z0-9_.-]+):(?:\s|$)", line)
        if match:
            targets.add(match.group(1))
    return targets


def _compose_available() -> bool:
    docker = shutil.which("docker")
    if not docker:
        return False
    result = subprocess.run(
        [docker, "compose", "version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.returncode == 0


def _tool_count(repo_root: Path, failures: list[str]) -> int:
    try:
        lock = json.loads((repo_root / "tool-manifests.lock.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        failures.append(f"cannot read tool-manifests.lock.json: {exc}")
        return 0
    manifests = lock.get("manifests")
    if not isinstance(manifests, list):
        failures.append("tool-manifests.lock.json has no manifest list")
        return 0
    return len(manifests)


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _count_csv(value: str) -> int:
    return len([part for part in value.split(",") if part.strip()])


def _recommendations(warnings: list[str], failures: list[str]) -> list[str]:
    if failures:
        return ["fix failed preflight checks before running the live demo"]
    recommendations = [
        "run make demo-seed before compose or demo-flow commands",
        "run make compose-down after the demo",
        "use make signed-evidence-demo for non-production signing evidence",
    ]
    if warnings:
        recommendations.append("review warnings before sharing the demo with a reviewer")
    return recommendations


def _print_human(report: dict[str, Any]) -> None:
    print("Ithildin live-demo preflight")
    print(f"status: {'pass' if report['valid'] else 'fail'}")
    print(f"repo_root: {report['repo_root']}")
    print(f"env_source: {report['env_source']}")
    print(f"tool_count: {report['tool_count']} / expected {report['expected_tool_count']}")
    print(f"compose_available: {str(report['compose_available']).lower()}")
    print(f"loopback_ports_valid: {str(report['loopback_ports_valid']).lower()}")
    print(f"docker_socket_mounted: {str(report['docker_socket_mounted']).lower()}")
    print(f"telemetry_enabled: {str(report['telemetry_enabled']).lower()}")
    print(f"http_allowlist_count: {report['http_allowlist_count']}")
    if report["warnings"]:
        print("\nwarnings:")
        for warning in report["warnings"]:
            print(f"- {warning}")
    if report["failures"]:
        print("\nfailures:")
        for failure in report["failures"]:
            print(f"- {failure}")
    print("\nrecommendations:")
    for recommendation in report["recommendations"]:
        print(f"- {recommendation}")


if __name__ == "__main__":
    raise SystemExit(main())

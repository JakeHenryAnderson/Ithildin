"""Validate the static Enterprise E1 single-site deployment foundation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import enterprise_e1_single_site

ROOT = Path(__file__).resolve().parents[1]
COMPOSE_REL = Path("deploy/single-site/compose.yaml")
ENV_REL = Path("deploy/single-site/env.example")
DOC_REL = Path("deploy/single-site/README.md")


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
    failures: list[str] = []
    compose_text = _read(repo_root / COMPOSE_REL, failures)
    env_text = _read(repo_root / ENV_REL, failures)
    doc = _read(repo_root / DOC_REL, failures)
    makefile = _read(repo_root / "Makefile", failures)
    api_dockerfile = _read(repo_root / "deploy/Dockerfile.api", failures)
    ui_dockerfile = _read(repo_root / "deploy/Dockerfile.ui", failures)
    try:
        compose = yaml.safe_load(compose_text)
    except yaml.YAMLError as exc:
        failures.append(f"E1 single-site Compose is invalid YAML: {exc}")
        compose = {}
    try:
        sample = enterprise_e1_single_site.parse_env_text(env_text)
    except enterprise_e1_single_site.SingleSiteError as exc:
        failures.append(f"E1 single-site sample environment is invalid: {exc}")
        sample = {}

    services = compose.get("services") if isinstance(compose, dict) else None
    expected_services = {"ithildin-api", "ithildin-ui"}
    if not isinstance(services, dict) or set(services) != expected_services:
        failures.append("E1 single-site service inventory is not exact")
        services = {}
    for service_name in expected_services:
        service = services.get(service_name)
        if not isinstance(service, dict):
            failures.append(f"E1 single-site service is missing: {service_name}")
            continue
        if service.get("read_only") is not True:
            failures.append(f"E1 single-site service is not read-only: {service_name}")
        if service.get("cap_drop") != ["ALL"]:
            failures.append(
                f"E1 single-site service does not drop all capabilities: {service_name}"
            )
        if service.get("security_opt") != ["no-new-privileges:true"]:
            failures.append(
                f"E1 single-site service lacks no-new-privileges: {service_name}"
            )
        ports = service.get("ports")
        if not isinstance(ports, list) or not all(
            isinstance(port, str) and port.startswith("127.0.0.1:") for port in ports
        ):
            failures.append(f"E1 single-site service port is not loopback-only: {service_name}")
    api = services.get("ithildin-api")
    api_environment = api.get("environment") if isinstance(api, dict) else None
    if not isinstance(api_environment, dict):
        failures.append("E1 single-site API environment is unavailable")
        api_environment = {}
    expected_fixed_environment = {
        "ITHILDIN_ALLOW_DEV_ADMIN_TOKEN": "false",
        "ITHILDIN_STORAGE_BACKEND": "sqlite",
        "ITHILDIN_POSTGRES_DSN": "",
        "ITHILDIN_HTTP_ALLOWLIST": "",
        "ITHILDIN_OTEL_ENABLED": "false",
        "ITHILDIN_OTEL_CONSOLE_EXPORT": "false",
        "ITHILDIN_OTEL_OTLP_ENDPOINT": "",
        "ITHILDIN_RUNTIME_CANDIDATE_INVENTORY_PATH": (
            "/app/runtime-candidate-inventory.json"
        ),
        "ITHILDIN_RUNTIME_CANDIDATE_AUTHORIZATION_PATH": (
            "/run/ithildin-authority/api-candidate.json"
        ),
    }
    for key, value in expected_fixed_environment.items():
        if api_environment.get(key) != value:
            failures.append(f"E1 single-site API boundary changed: {key}")
    serialized_compose = json.dumps(compose, sort_keys=True)
    for forbidden in (
        "/var/run/docker.sock",
        "network_mode",
        "privileged",
        "postgres:",
        "kubernetes",
    ):
        if forbidden in serialized_compose.lower():
            failures.append(f"E1 single-site Compose contains forbidden authority: {forbidden}")
    if set(sample) != enterprise_e1_single_site.ENV_KEYS:
        failures.append("E1 single-site sample environment keys are not exact")
    for command in (
        "enterprise-e1-single-site-bootstrap",
        "enterprise-e1-single-site-config",
        "enterprise-e1-single-site-up",
        "enterprise-e1-single-site-health",
        "enterprise-e1-single-site-down",
        "enterprise-e1-single-site-deployment-check",
    ):
        if f"{command}:" not in makefile or f"make {command}" not in doc:
            failures.append(f"E1 single-site command is not fully wired: {command}")
    for phrase in (
        "not production identity",
        "runtime PostgreSQL",
        "optional Ithildin Node is intentionally not part",
        "does not receive Docker lifecycle authority",
        "model-provider state",
        "Do not delete or overwrite state when ownership or candidate identity is ambiguous",
    ):
        if phrase not in doc:
            failures.append(f"E1 single-site documentation is missing boundary text: {phrase}")
    for dockerfile_name, dockerfile in (
        ("API", api_dockerfile),
        ("UI", ui_dockerfile),
    ):
        if "org.opencontainers.image.version" not in dockerfile:
            failures.append(f"E1 {dockerfile_name} image lacks a version label")
        if "org.opencontainers.image.revision" not in dockerfile:
            failures.append(f"E1 {dockerfile_name} image lacks a source-revision label")
    tool_count = _tool_count(repo_root / "tool-manifests.lock.json")
    if tool_count != 24:
        failures.append("E1 single-site deployment tool count is not 24")
    return {
        "valid": not failures,
        "failures": failures,
        "schema_version": "1",
        "services": sorted(services),
        "service_count": len(services),
        "tool_count": tool_count,
        "loopback_only": not any("loopback-only" in failure for failure in failures),
        "storage_backend": api_environment.get("ITHILDIN_STORAGE_BACKEND", "invalid"),
        "runtime_postgres_allowed": False,
        "docker_authority_granted": False,
        "optional_node_in_m1": False,
        "human_uat_complete": False,
    }


def _read(path: Path, failures: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        failures.append(f"cannot read {path}: {exc}")
        return ""


def _tool_count(path: Path) -> int:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        manifests = document.get("manifests")
    except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
        return -1
    return len(manifests) if isinstance(manifests, list) else -1


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Enterprise E1 single-site deployment check",
        f"valid: {str(report['valid']).lower()}",
        f"services: {', '.join(report['services'])}",
        f"service_count: {report['service_count']}",
        f"tool_count: {report['tool_count']}",
        f"loopback_only: {str(report['loopback_only']).lower()}",
        f"storage_backend: {report['storage_backend']}",
        f"runtime_postgres_allowed: {str(report['runtime_postgres_allowed']).lower()}",
        f"docker_authority_granted: {str(report['docker_authority_granted']).lower()}",
        f"optional_node_in_m1: {str(report['optional_node_in_m1']).lower()}",
        f"human_uat_complete: {str(report['human_uat_complete']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

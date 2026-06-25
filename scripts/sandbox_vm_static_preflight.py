"""Run a read-only static sandbox/VM profile preflight over a fixture JSON file."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import sandbox_vm_static_profile_fixture_contract_check as fixture_contract

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "docs/codex/fixtures/sandbox-vm-static-profile.local-preview.example.json"
MAX_FIXTURE_BYTES = 65536
SAFE_REASON_PATTERN = re.compile(r"^[a-z0-9_]+$")
SENSITIVE_PATTERNS = [
    re.compile(r"/Users/"),
    re.compile(r"/var/"),
    re.compile(r"/tmp/"),
    re.compile(r"~[/\\]"),
    re.compile(r"\b[A-Za-z]:\\\\"),
    re.compile(r"docker\.sock"),
    re.compile(r"kubeconfig", re.IGNORECASE),
    re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
    re.compile(r"(?i)\b(secret|token|password|api_key)\s*[:=]\s*[^,\s]+"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", nargs="?", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report(args.fixture)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(fixture_path: Path) -> dict[str, Any]:
    payload, load_reasons = _load_fixture(fixture_path)
    validation_reasons = _validate_payload(payload) if payload is not None else []
    safe_reasons = sorted(set(load_reasons + validation_reasons))
    for reason in safe_reasons:
        if not SAFE_REASON_PATTERN.match(reason):
            safe_reasons.append("unsafe_reason_label")
            break
    decision = _decision(payload, safe_reasons)
    output_policy = {
        "raw_paths_included": False,
        "file_contents_included": False,
        "model_prompts_included": False,
        "model_outputs_included": False,
        "shell_output_included": False,
        "network_endpoints_included": False,
        "secret_values_included": False,
        "sandbox_runtime_inspected": False,
        "mission_control_runtime_called": False,
        "local_model_invoked": False,
        "trusted_host_promotion_performed": False,
    }
    return {
        "schema_version": "1",
        "valid": not safe_reasons,
        "fixture_loaded": payload is not None,
        "profile_id": _safe_value(payload, "profile_label"),
        "workspace_id": _safe_value(payload, "workspace_id"),
        "sandbox_id": _safe_value(payload, "sandbox_id"),
        "support_status": _safe_value(payload, "support_status"),
        "platform_label": _nested_safe_value(payload, ("platform", "os_label")),
        "mount_label_count": _safe_count(payload, ("mounts",)),
        "network_posture": _nested_safe_value(payload, ("network", "posture")),
        "ingress_egress_status": _nested_safe_value(payload, ("ingress_egress", "status")),
        "cleanup_status": _nested_safe_value(payload, ("cleanup", "status")),
        "warning_labels": _safe_string_list(payload, "warnings"),
        "false_authority_flags": _false_authority_flags(payload),
        "promotion_status": _nested_safe_value(payload, ("decision", "promotion_status")),
        "decision": decision,
        "safe_reasons": safe_reasons,
        "output_policy": output_policy,
    }


def _load_fixture(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        stat = path.stat()
    except OSError:
        return None, ["fixture_unreadable"]
    if stat.st_size > MAX_FIXTURE_BYTES:
        return None, ["fixture_too_large"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return None, ["unsupported_encoding"]
    except json.JSONDecodeError:
        return None, ["malformed_json"]
    if not isinstance(data, dict):
        return None, ["not_object"]
    return data, []


def _validate_payload(payload: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    contract_failures = fixture_contract._validate_fixture(dict(payload))  # noqa: SLF001
    reasons.extend(_to_reason_label(reason) for reason in contract_failures)
    if _contains_sensitive_shape(payload):
        reasons.append("sensitive_payload_shape")
    network = payload.get("network")
    if isinstance(network, Mapping) and network.get("broad_network_access") is not False:
        reasons.append("broad_network_overclaim")
    return sorted(set(reasons))


def _decision(payload: Mapping[str, Any] | None, safe_reasons: list[str]) -> str:
    if safe_reasons:
        return "no_go"
    if payload is None:
        return "no_go"
    if payload.get("support_status") == "unsupported":
        return "no_go"
    return "review_required"


def _to_reason_label(reason: str) -> str:
    lowered = reason.lower()
    if "schema_version" in lowered:
        return "unsupported_schema"
    if "unknown keys" in lowered:
        return "closed_schema_violation"
    if "warning" in lowered:
        return "missing_warning_state"
    if "supported_local_preview" in lowered:
        return "support_overclaim"
    if "promotion_status" in lowered:
        return "promotion_overclaim"
    if "decision" in lowered:
        return "readiness_overclaim"
    if "flag must be false" in lowered:
        return "authority_overclaim"
    if "network" in lowered:
        return "unsupported_network_posture"
    return "invalid_static_profile"


def _contains_sensitive_shape(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            _sensitive_key(str(key)) or _contains_sensitive_shape(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_sensitive_shape(child) for child in value)
    if isinstance(value, str):
        return any(pattern.search(value) for pattern in SENSITIVE_PATTERNS)
    return False


def _sensitive_key(key: str) -> bool:
    return key.lower() in {
        "secret",
        "secrets",
        "token",
        "tokens",
        "password",
        "api_key",
        "private_key",
        "raw_prompt",
        "file_contents",
    }


def _safe_value(payload: Mapping[str, Any] | None, key: str) -> str | None:
    if payload is None:
        return None
    value = payload.get(key)
    return value if isinstance(value, str) and _safe_labelish(value) else None


def _nested_safe_value(payload: Mapping[str, Any] | None, path: tuple[str, ...]) -> str | None:
    current: Any = payload
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, str) and _safe_labelish(current) else None


def _safe_string_list(payload: Mapping[str, Any] | None, key: str) -> list[str]:
    if payload is None:
        return []
    value = payload.get(key)
    if not isinstance(value, list):
        return []
    return sorted(
        item for item in value if isinstance(item, str) and _safe_labelish(item)
    )


def _false_authority_flags(payload: Mapping[str, Any] | None) -> dict[str, bool]:
    if payload is None:
        return {}
    decision = payload.get("decision")
    if not isinstance(decision, Mapping):
        return {}
    flags = decision.get("false_authority_flags")
    if not isinstance(flags, Mapping):
        return {}
    return {
        key: value
        for key, value in sorted(flags.items())
        if isinstance(key, str)
        and key in fixture_contract.FALSE_AUTHORITY_FLAGS
        and isinstance(value, bool)
    }


def _safe_count(payload: Mapping[str, Any] | None, path: tuple[str, ...]) -> int:
    current: Any = payload
    for key in path:
        if not isinstance(current, Mapping):
            return 0
        current = current.get(key)
    if not isinstance(current, Mapping):
        return 0
    return sum(1 for value in current.values() if isinstance(value, str) and _safe_labelish(value))


def _safe_labelish(value: str) -> bool:
    if any(pattern.search(value) for pattern in SENSITIVE_PATTERNS):
        return False
    if value.startswith(("/", "~")) or "\\" in value:
        return False
    if "://" in value:
        return bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,31}://[A-Za-z0-9_.-]{1,64}", value))
    return bool(re.fullmatch(r"[A-Za-z0-9_.-]{1,96}", value))


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin sandbox/VM static preflight",
        f"valid: {str(report['valid']).lower()}",
        f"decision: {report['decision']}",
        f"profile_id: {report['profile_id']}",
        f"workspace_id: {report['workspace_id']}",
        f"sandbox_id: {report['sandbox_id']}",
        f"support_status: {report['support_status']}",
        f"platform_label: {report['platform_label']}",
        f"network_posture: {report['network_posture']}",
        f"promotion_status: {report['promotion_status']}",
        "safe_reasons: "
        + (", ".join(report["safe_reasons"]) if report["safe_reasons"] else "none"),
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

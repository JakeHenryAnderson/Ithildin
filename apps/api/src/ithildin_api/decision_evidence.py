"""Shared construction of safe policy decision evidence."""

from __future__ import annotations

from typing import cast

from ithildin_schemas import JsonObject, PolicyDecision, PolicyInput


def policy_decision_evidence(
    *,
    policy_engine: str,
    policy_hash: str,
    policy_document_version: str,
    policy_input: PolicyInput,
    policy_decision: PolicyDecision,
) -> JsonObject:
    policy_input_data = policy_input.model_dump(mode="json")
    tool = _json_object(policy_input_data.get("tool"))
    resource = _json_object(policy_input_data.get("resource"))
    principal = _json_object(policy_input_data.get("principal"))
    context = _json_object(policy_input_data.get("context"))
    obligations = policy_decision.obligations
    obligation_keys = sorted(obligations.keys())
    principal_roles = principal.get("roles")

    return cast(JsonObject, {
        "decision": policy_decision.decision.value,
        "reason": policy_decision.reason,
        "policy_engine": policy_engine,
        "policy_hash": policy_hash,
        "policy_version": policy_decision.policy_version,
        "policy_document_version": policy_document_version,
        "matched_rules": list(policy_decision.matched_rules),
        "obligation_keys": obligation_keys,
        "tool_name": _optional_string(tool.get("name")),
        "tool_version": _optional_string(tool.get("version")),
        "tool_risk": _optional_string(tool.get("risk")),
        "manifest_hash": _optional_string(tool.get("manifest_hash")),
        "resource_type": _optional_string(resource.get("type")),
        "resource_in_scope": _optional_bool(resource.get("in_scope")),
        "principal_id": _optional_string(principal.get("id")),
        "principal_roles": principal_roles if _string_list(principal_roles) else [],
        "session_id": _optional_string(context.get("session_id")),
    })


def _json_object(value: object) -> JsonObject:
    return value if isinstance(value, dict) else {}


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _optional_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _string_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)

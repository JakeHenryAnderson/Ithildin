"""Read-only policy preview service."""

from __future__ import annotations

from ithildin_policy_core import PolicyEngine
from ithildin_schemas import JsonObject, JsonValue, PolicyDecisionValue, PolicyInput
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate as validate_json_schema

from ithildin_api.http_tools import HttpAllowlist
from ithildin_api.identity import (
    PrincipalRegistry,
    PrincipalRegistryError,
    can_access_risk,
    principal_denial_metadata,
    resolve_trusted_principal,
)
from ithildin_api.registry import ToolRegistry, UnknownToolDenied
from ithildin_api.resources import resource_from_arguments

DEFAULT_PREVIEW_PRINCIPAL: JsonObject = {"id": "admin:local-ui", "roles": ["Admin"]}
DEFAULT_PREVIEW_SESSION_ID = "policy-preview"


class PolicyPreviewService:
    def __init__(
        self,
        registry: ToolRegistry,
        policy_evaluator: PolicyEngine,
        http_allowlist: HttpAllowlist | None = None,
        principal_registry: PrincipalRegistry | None = None,
    ) -> None:
        self.registry = registry
        self.policy_evaluator = policy_evaluator
        self.http_allowlist = http_allowlist or HttpAllowlist(())
        self.principal_registry = principal_registry

    def preview(
        self,
        *,
        tool_name: str,
        arguments: JsonObject,
        principal: JsonObject | None = None,
        session_id: str = DEFAULT_PREVIEW_SESSION_ID,
    ) -> JsonObject:
        preview_principal = principal or DEFAULT_PREVIEW_PRINCIPAL

        try:
            registered_tool = self.registry.get_tool(tool_name)
        except UnknownToolDenied as exc:
            return {
                **self._policy_evidence(),
                "tool_name": tool_name,
                "manifest_hash": None,
                "manifest_risk": None,
                "manifest_version": None,
                "valid_arguments": False,
                "argument_error": exc.reason,
                "policy_input": None,
                "resource": {"type": "tool_call", "in_scope": False},
                "decision": PolicyDecisionValue.DENY.value,
                "reason": exc.reason,
                "policy_version": self.policy_evaluator.policy_hash,
                "matched_rules": [],
                "obligations": {"audit_level": "full"},
            }

        manifest = registered_tool.manifest
        if self.principal_registry is not None:
            try:
                principal_record = resolve_trusted_principal(
                    self.principal_registry,
                    preview_principal,
                )
            except PrincipalRegistryError as exc:
                return self._deny_preview(
                    tool_name=manifest.name,
                    manifest_hash=registered_tool.manifest_hash,
                    manifest_risk=manifest.risk.value,
                    manifest_version=manifest.version,
                    reason=str(exc),
                    resource={"type": "tool_call", "in_scope": False},
                    metadata=principal_denial_metadata(str(exc)),
            )
            preview_principal = principal_record.trusted_principal()
            if not can_access_risk(principal_record, manifest.risk):
                reason = (
                    f"principal {principal_record.id} is not authorized "
                    f"for {manifest.risk.value} tools"
                )
                return self._deny_preview(
                    tool_name=manifest.name,
                    manifest_hash=registered_tool.manifest_hash,
                    manifest_risk=manifest.risk.value,
                    manifest_version=manifest.version,
                    reason=reason,
                    resource={"type": "tool_call", "in_scope": False},
                    metadata=principal_denial_metadata(reason),
                )

        resource = resource_from_arguments(
            arguments,
            manifest.risk,
            http_allowlist=self.http_allowlist,
        )

        try:
            validate_json_schema(instance=arguments, schema=manifest.input_schema)
        except JsonSchemaValidationError as exc:
            return {
                **self._policy_evidence(),
                "tool_name": manifest.name,
                "manifest_hash": registered_tool.manifest_hash,
                "manifest_risk": manifest.risk.value,
                "manifest_version": manifest.version,
                "valid_arguments": False,
                "argument_error": exc.message,
                "policy_input": None,
                "resource": resource,
                "decision": PolicyDecisionValue.DENY.value,
                "reason": "invalid tool arguments",
                "policy_version": self.policy_evaluator.policy_hash,
                "matched_rules": [],
                "obligations": {"audit_level": "full"},
            }

        policy_input = PolicyInput(
            principal=preview_principal,
            tool={
                "name": manifest.name,
                "risk": manifest.risk.value,
                "version": manifest.version,
                "manifest_hash": registered_tool.manifest_hash,
            },
            resource=resource,
            context={"session_id": session_id},
        )
        policy_decision = self.policy_evaluator.evaluate(policy_input)
        matched_rules: list[JsonValue] = [rule_id for rule_id in policy_decision.matched_rules]

        return {
            **self._policy_evidence(),
            "tool_name": manifest.name,
            "manifest_hash": registered_tool.manifest_hash,
            "manifest_risk": manifest.risk.value,
            "manifest_version": manifest.version,
            "valid_arguments": True,
            "argument_error": None,
            "policy_input": policy_input.model_dump(mode="json"),
            "resource": resource,
            "decision": policy_decision.decision.value,
            "reason": policy_decision.reason,
            "policy_version": policy_decision.policy_version,
            "matched_rules": matched_rules,
            "obligations": policy_decision.obligations,
        }

    def _policy_evidence(self) -> JsonObject:
        return {
            "policy_engine": self.policy_evaluator.engine_name,
            "policy_document_version": self.policy_evaluator.document_version,
            "policy_hash": self.policy_evaluator.policy_hash,
        }

    def _deny_preview(
        self,
        *,
        tool_name: str,
        manifest_hash: str | None,
        manifest_risk: str | None,
        manifest_version: str | None,
        reason: str,
        resource: JsonObject,
        metadata: JsonObject | None = None,
    ) -> JsonObject:
        return {
            **self._policy_evidence(),
            "tool_name": tool_name,
            "manifest_hash": manifest_hash,
            "manifest_risk": manifest_risk,
            "manifest_version": manifest_version,
            "valid_arguments": False,
            "argument_error": reason,
            "policy_input": None,
            "resource": resource,
            "decision": PolicyDecisionValue.DENY.value,
            "reason": reason,
            "policy_version": self.policy_evaluator.policy_hash,
            "matched_rules": [],
            "obligations": {"audit_level": "full", **(metadata or {})},
        }

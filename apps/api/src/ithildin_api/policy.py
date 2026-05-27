"""Policy engine selection for API and MCP runtimes."""

from __future__ import annotations

from ithildin_policy_core import (
    OpaPolicyEvaluator,
    PolicyEngine,
    PolicyError,
    PolicyEvaluator,
    verify_opa_bundle_manifest,
)

from ithildin_api.config import Settings


def load_policy_engine(settings: Settings) -> PolicyEngine:
    engine = settings.policy_engine.strip().lower()
    if engine == "yaml":
        return PolicyEvaluator.load(settings.policy_path)
    if engine == "opa":
        if not settings.opa_url:
            raise PolicyError("ITHILDIN_OPA_URL is required when ITHILDIN_POLICY_ENGINE=opa")
        bundle_evidence = verify_opa_bundle_manifest(settings.opa_bundle_manifest_path)
        return OpaPolicyEvaluator(
            base_url=settings.opa_url,
            decision_path=settings.opa_decision_path,
            bundle_evidence=bundle_evidence,
        )
    raise PolicyError(f"unsupported policy engine: {settings.policy_engine}")

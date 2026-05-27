"""Policy evaluation package for Ithildin."""

from ithildin_policy_core.evaluator import PolicyDocument, PolicyError, PolicyEvaluator, PolicyRule
from ithildin_policy_core.opa import OpaPolicyEvaluator
from ithildin_policy_core.opa_bundle import (
    OpaBundleError,
    OpaBundleEvidence,
    OpaBundleSource,
    opa_bundle_hash,
    verify_opa_bundle_manifest,
)
from ithildin_policy_core.types import PolicyEngine

__all__ = [
    "OpaBundleError",
    "OpaBundleEvidence",
    "OpaBundleSource",
    "OpaPolicyEvaluator",
    "PolicyDocument",
    "PolicyEngine",
    "PolicyError",
    "PolicyEvaluator",
    "PolicyRule",
    "__version__",
    "opa_bundle_hash",
    "verify_opa_bundle_manifest",
]

__version__ = "0.1.0"

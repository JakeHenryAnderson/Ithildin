"""Policy evaluation package for Ithildin."""

from ithildin_policy_core.evaluator import PolicyDocument, PolicyError, PolicyEvaluator, PolicyRule
from ithildin_policy_core.opa import OpaPolicyEvaluator
from ithildin_policy_core.types import PolicyEngine

__all__ = [
    "OpaPolicyEvaluator",
    "PolicyDocument",
    "PolicyEngine",
    "PolicyError",
    "PolicyEvaluator",
    "PolicyRule",
    "__version__",
]

__version__ = "0.1.0"

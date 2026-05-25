"""Shared schema package for Ithildin."""

from ithildin_schemas.hashing import canonical_json, sha256_digest
from ithildin_schemas.models import (
    ApprovalDecision,
    ApprovalRequest,
    AuditEvent,
    PolicyDecision,
    PolicyInput,
    ToolCallRequest,
    ToolCallResult,
    ToolManifest,
)
from ithildin_schemas.types import (
    ApprovalDecisionValue,
    ApprovalStatus,
    AuditEventType,
    JsonObject,
    JsonValue,
    PolicyDecisionValue,
    ToolRisk,
)

__all__ = [
    "ApprovalDecision",
    "ApprovalDecisionValue",
    "ApprovalRequest",
    "ApprovalStatus",
    "AuditEvent",
    "AuditEventType",
    "JsonObject",
    "JsonValue",
    "PolicyDecision",
    "PolicyDecisionValue",
    "PolicyInput",
    "ToolCallRequest",
    "ToolCallResult",
    "ToolManifest",
    "ToolRisk",
    "__version__",
    "canonical_json",
    "sha256_digest",
]

__version__ = "0.1.0"

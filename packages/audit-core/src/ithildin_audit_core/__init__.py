"""Audit package for Ithildin."""

from ithildin_audit_core.signing import (
    AuditSignatureVerificationResult,
    AuditSigningError,
    audit_public_key_id,
    audit_signing_status,
    generate_audit_signing_keypair,
    signed_audit_export_bundle,
    verify_exported_events_jsonl,
    verify_signed_audit_export_bundle,
)
from ithildin_audit_core.writer import (
    AuditVerificationFailure,
    AuditVerificationResult,
    AuditWriteError,
    AuditWriter,
)

__all__ = [
    "AuditSignatureVerificationResult",
    "AuditSigningError",
    "AuditVerificationFailure",
    "AuditVerificationResult",
    "AuditWriteError",
    "AuditWriter",
    "audit_public_key_id",
    "audit_signing_status",
    "generate_audit_signing_keypair",
    "signed_audit_export_bundle",
    "verify_exported_events_jsonl",
    "verify_signed_audit_export_bundle",
    "__version__",
]

__version__ = "0.1.0"

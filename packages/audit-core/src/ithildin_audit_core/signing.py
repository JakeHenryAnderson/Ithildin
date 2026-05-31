"""Local Ed25519 signing for audit export bundles."""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional, cast

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from ithildin_schemas import AuditEvent, JsonObject, JsonValue, canonical_json, sha256_digest
from pydantic import ValidationError

from ithildin_audit_core.writer import (
    GENESIS_HASH,
    AuditVerificationFailure,
    AuditVerificationResult,
)

SIGNED_AUDIT_EXPORT_BUNDLE_TYPE = "ithildin.audit.signed_export"
SIGNED_AUDIT_EXPORT_FORMAT_VERSION = "1"
SIGNATURE_ALGORITHM = "ed25519"


class AuditSigningError(RuntimeError):
    """Raised when audit export signing or verification fails."""


@dataclass(frozen=True)
class AuditSignatureVerificationResult:
    valid: bool
    key_id: Optional[str]
    events_sha256: Optional[str]
    audit_verification: AuditVerificationResult
    failure: Optional[str] = None

    def as_dict(self) -> JsonObject:
        return {
            "valid": self.valid,
            "key_id": self.key_id,
            "events_sha256": self.events_sha256,
            "audit_verification": self.audit_verification.as_dict(),
            "failure": self.failure,
        }


def generate_audit_signing_keypair(
    *,
    private_key_path: Path,
    public_key_path: Path,
    overwrite: bool = False,
) -> str:
    """Generate a local Ed25519 keypair and return the public key id."""
    if not overwrite and (private_key_path.exists() or public_key_path.exists()):
        raise AuditSigningError("audit signing key already exists")

    private_key_path.parent.mkdir(parents=True, exist_ok=True)
    public_key_path.parent.mkdir(parents=True, exist_ok=True)
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    private_key_path.write_bytes(private_bytes)
    private_key_path.chmod(0o600)
    public_key_path.write_bytes(public_bytes)
    public_key_path.chmod(0o644)
    return audit_public_key_id(public_key)


def signed_audit_export_bundle(
    *,
    jsonl_bundle: str,
    private_key_path: Path,
    public_key_path: Path,
) -> JsonObject:
    """Return a signed JSON export bundle derived from an existing JSONL export."""
    private_key = _load_private_key(private_key_path)
    configured_public_key = _load_public_key(public_key_path)
    derived_public_key = private_key.public_key()
    if _public_key_raw(configured_public_key) != _public_key_raw(derived_public_key):
        raise AuditSigningError("audit signing public key does not match private key")

    metadata, events_jsonl = _split_jsonl_export(jsonl_bundle)
    events_sha256 = _sha256_text(events_jsonl)
    public_key_b64 = _public_key_b64(derived_public_key)
    key_id = audit_public_key_id(derived_public_key)
    signature_metadata: JsonObject = {
        "algorithm": SIGNATURE_ALGORITHM,
        "key_id": key_id,
        "public_key": public_key_b64,
        "created_at": datetime.now(UTC).isoformat(),
    }
    payload = _signature_payload(
        metadata=metadata,
        events_sha256=events_sha256,
        signature_metadata=signature_metadata,
    )
    signature = private_key.sign(canonical_json(cast(JsonValue, payload)).encode("utf-8"))

    return {
        "bundle_type": SIGNED_AUDIT_EXPORT_BUNDLE_TYPE,
        "format_version": SIGNED_AUDIT_EXPORT_FORMAT_VERSION,
        "metadata": metadata,
        "events_jsonl": events_jsonl,
        "events_sha256": events_sha256,
        "signature": {
            **signature_metadata,
            "signature": base64.b64encode(signature).decode("ascii"),
        },
    }


def verify_signed_audit_export_bundle(
    bundle: JsonObject,
    *,
    public_key_path: Optional[Path] = None,
) -> AuditSignatureVerificationResult:
    """Verify a signed audit export bundle and its embedded event chain."""
    try:
        _require_string(bundle.get("bundle_type"), "bundle_type", SIGNED_AUDIT_EXPORT_BUNDLE_TYPE)
        _require_string(
            bundle.get("format_version"),
            "format_version",
            SIGNED_AUDIT_EXPORT_FORMAT_VERSION,
        )
        metadata = _require_object(bundle.get("metadata"), "metadata")
        events_jsonl = _require_any_string(bundle.get("events_jsonl"), "events_jsonl")
        events_sha256 = _require_prefixed_hash(bundle.get("events_sha256"), "events_sha256")
        signature = _require_object(bundle.get("signature"), "signature")
        algorithm = _require_string(signature.get("algorithm"), "signature.algorithm")
        if algorithm != SIGNATURE_ALGORITHM:
            raise AuditSigningError("unsupported signature algorithm")
        public_key_b64 = _require_any_string(signature.get("public_key"), "signature.public_key")
        key_id = _require_prefixed_hash(signature.get("key_id"), "signature.key_id")
        signature_b64 = _require_any_string(signature.get("signature"), "signature.signature")

        recomputed_events_sha256 = _sha256_text(events_jsonl)
        if recomputed_events_sha256 != events_sha256:
            raise AuditSigningError("events digest mismatch")

        embedded_public_key = _public_key_from_b64(public_key_b64)
        if audit_public_key_id(embedded_public_key) != key_id:
            raise AuditSigningError("signature key id mismatch")
        if public_key_path is None:
            raise AuditSigningError("trusted public key is required")
        trusted_public_key = _load_public_key(public_key_path)
        if _public_key_raw(trusted_public_key) != _public_key_raw(embedded_public_key):
            raise AuditSigningError("signed bundle public key does not match trusted key")

        signature_metadata: JsonObject = {
            "algorithm": algorithm,
            "key_id": key_id,
            "public_key": public_key_b64,
            "created_at": _require_any_string(signature.get("created_at"), "signature.created_at"),
        }
        payload = _signature_payload(
            metadata=metadata,
            events_sha256=events_sha256,
            signature_metadata=signature_metadata,
        )
        signature_bytes = base64.b64decode(signature_b64, validate=True)
        embedded_public_key.verify(
            signature_bytes,
            canonical_json(cast(JsonValue, payload)).encode("utf-8"),
        )
        audit_verification = verify_exported_events_jsonl(events_jsonl)
        if not audit_verification.valid:
            raise AuditSigningError("audit verification failed")
        if not _metadata_matches_verification(metadata, audit_verification):
            raise AuditSigningError("metadata verification does not match exported events")
    except (AuditSigningError, InvalidSignature, ValueError) as exc:
        exported_events = _optional_string(bundle.get("events_jsonl")) or ""
        failure = "signature verification failed" if isinstance(exc, InvalidSignature) else str(exc)
        return AuditSignatureVerificationResult(
            valid=False,
            key_id=_optional_hash_from_bundle(bundle),
            events_sha256=_optional_string(bundle.get("events_sha256")),
            audit_verification=verify_exported_events_jsonl(exported_events),
            failure=failure,
        )

    return AuditSignatureVerificationResult(
        valid=True,
        key_id=key_id,
        events_sha256=events_sha256,
        audit_verification=audit_verification,
    )


def audit_signing_status(private_key_path: Path, public_key_path: Path) -> JsonObject:
    """Return secret-free local audit signing status."""
    private_configured = private_key_path.exists()
    public_configured = public_key_path.exists()
    status: JsonObject = {
        "algorithm": SIGNATURE_ALGORITHM,
        "private_key_configured": private_configured,
        "public_key_configured": public_configured,
        "signed_export_available": False,
        "key_id": None,
    }
    if not private_configured or not public_configured:
        return status

    try:
        private_key = _load_private_key(private_key_path)
        public_key = _load_public_key(public_key_path)
        if _public_key_raw(private_key.public_key()) != _public_key_raw(public_key):
            status["error"] = "configured keys do not match"
            return status
        status["signed_export_available"] = True
        status["key_id"] = audit_public_key_id(public_key)
    except AuditSigningError as exc:
        status["error"] = str(exc)
    return status


def audit_public_key_id(public_key: Ed25519PublicKey) -> str:
    return sha256_digest(
        {
            "algorithm": SIGNATURE_ALGORITHM,
            "public_key": _public_key_b64(public_key),
        }
    )


def verify_exported_events_jsonl(events_jsonl: str) -> AuditVerificationResult:
    lines = [line for line in events_jsonl.splitlines() if line.strip()]
    if not lines:
        return AuditVerificationResult(
            valid=True,
            event_count=0,
            first_timestamp=None,
            last_timestamp=None,
            head_hash=GENESIS_HASH,
        )

    previous_hash = GENESIS_HASH
    first_timestamp: Optional[str] = None
    last_timestamp: Optional[str] = None
    head_hash = GENESIS_HASH
    parsed_rows: list[tuple[object]] = [(line,) for line in lines]
    seen_event_ids: set[str] = set()

    for row_number, line in enumerate(lines, start=1):
        try:
            payload = cast(JsonObject, json.loads(line))
        except json.JSONDecodeError:
            return _failed_jsonl_verification(
                rows=parsed_rows,
                row_number=row_number,
                head_hash=head_hash,
                reason="invalid audit payload JSON",
            )
        if not isinstance(payload, dict):
            return _failed_jsonl_verification(
                rows=parsed_rows,
                row_number=row_number,
                head_hash=head_hash,
                reason="invalid audit event schema",
            )
        raw_event_id = payload.get("event_id")
        event_id = raw_event_id if isinstance(raw_event_id, str) else None
        try:
            event = AuditEvent.model_validate(payload)
        except ValidationError:
            return _failed_jsonl_verification(
                rows=parsed_rows,
                row_number=row_number,
                head_hash=head_hash,
                reason="invalid audit event schema",
                event_id=event_id,
            )
        if event.event_id in seen_event_ids:
            return _failed_jsonl_verification(
                rows=parsed_rows,
                row_number=row_number,
                head_hash=head_hash,
                reason="duplicate audit event id",
                event_id=event.event_id,
            )
        seen_event_ids.add(event.event_id)
        if event.prev_event_hash != previous_hash:
            return _failed_jsonl_verification(
                rows=parsed_rows,
                row_number=row_number,
                head_hash=head_hash,
                reason="previous event hash mismatch",
                event_id=event.event_id,
            )
        expected_hash = _event_hash_from_event(event)
        if event.event_hash != expected_hash:
            return _failed_jsonl_verification(
                rows=parsed_rows,
                row_number=row_number,
                head_hash=head_hash,
                reason="event hash mismatch",
                event_id=event.event_id,
            )
        if first_timestamp is None:
            first_timestamp = event.timestamp.isoformat()
        last_timestamp = event.timestamp.isoformat()
        previous_hash = event.event_hash
        head_hash = event.event_hash

    return AuditVerificationResult(
        valid=True,
        event_count=len(lines),
        first_timestamp=first_timestamp,
        last_timestamp=last_timestamp,
        head_hash=head_hash,
    )


def _load_private_key(path: Path) -> Ed25519PrivateKey:
    try:
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    except (OSError, ValueError) as exc:
        raise AuditSigningError("audit signing private key is missing or invalid") from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise AuditSigningError("audit signing private key must be Ed25519")
    return key


def _load_public_key(path: Path) -> Ed25519PublicKey:
    try:
        key = serialization.load_pem_public_key(path.read_bytes())
    except (OSError, ValueError) as exc:
        raise AuditSigningError("audit signing public key is missing or invalid") from exc
    if not isinstance(key, Ed25519PublicKey):
        raise AuditSigningError("audit signing public key must be Ed25519")
    return key


def _split_jsonl_export(jsonl_bundle: str) -> tuple[JsonObject, str]:
    lines = jsonl_bundle.splitlines()
    if not lines:
        raise AuditSigningError("audit export bundle is empty")
    try:
        metadata_wrapper = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        raise AuditSigningError("audit export metadata is invalid JSON") from exc
    metadata = _require_object(metadata_wrapper.get("metadata"), "metadata")
    events_jsonl = "\n".join(lines[1:])
    if events_jsonl:
        events_jsonl += "\n"
    return metadata, events_jsonl


def _signature_payload(
    *,
    metadata: JsonObject,
    events_sha256: str,
    signature_metadata: JsonObject,
) -> JsonObject:
    return {
        "bundle_type": SIGNED_AUDIT_EXPORT_BUNDLE_TYPE,
        "format_version": SIGNED_AUDIT_EXPORT_FORMAT_VERSION,
        "metadata": metadata,
        "events_sha256": events_sha256,
        "signature": signature_metadata,
    }


def _metadata_matches_verification(
    metadata: JsonObject,
    verification: AuditVerificationResult,
) -> bool:
    verification_metadata = metadata.get("verification")
    if not isinstance(verification_metadata, dict):
        return False
    return (
        metadata.get("event_count") == verification.event_count
        and metadata.get("head_hash") == verification.head_hash
        and verification_metadata == verification.as_dict()
    )


def _event_hash_from_event(event: AuditEvent) -> str:
    event_data = {
        "event_id": event.event_id,
        "timestamp": event.timestamp.isoformat(),
        "event_type": event.event_type.value,
        "request_id": event.request_id,
        "principal": event.principal,
        "tool_name": event.tool_name,
        "resource": event.resource,
        "decision": event.decision.value if event.decision is not None else None,
        "policy_version": event.policy_version,
        "matched_rules": event.matched_rules,
        "input_hash": event.input_hash,
        "redactions": event.redactions,
        "metadata": event.metadata,
        "prev_event_hash": event.prev_event_hash,
    }
    return sha256_digest(cast(JsonValue, event_data))


def _failed_jsonl_verification(
    *,
    rows: list[tuple[object]],
    row_number: int,
    head_hash: str,
    reason: str,
    event_id: Optional[str] = None,
) -> AuditVerificationResult:
    timestamps = []
    for row in rows:
        try:
            payload = json.loads(str(row[0]))
        except json.JSONDecodeError:
            continue
        timestamp = payload.get("timestamp") if isinstance(payload, dict) else None
        if isinstance(timestamp, str):
            timestamps.append(timestamp)
    return AuditVerificationResult(
        valid=False,
        event_count=len(rows),
        first_timestamp=timestamps[0] if timestamps else None,
        last_timestamp=timestamps[-1] if timestamps else None,
        head_hash=head_hash,
        failure=AuditVerificationFailure(
            row_number=row_number,
            event_id=event_id,
            reason=reason,
        ),
    )


def _public_key_raw(public_key: Ed25519PublicKey) -> bytes:
    return public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def _public_key_b64(public_key: Ed25519PublicKey) -> str:
    return base64.b64encode(_public_key_raw(public_key)).decode("ascii")


def _public_key_from_b64(value: str) -> Ed25519PublicKey:
    try:
        return Ed25519PublicKey.from_public_bytes(base64.b64decode(value, validate=True))
    except ValueError as exc:
        raise AuditSigningError("signature public key is invalid") from exc


def _sha256_text(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def _require_object(value: object, field: str) -> JsonObject:
    if not isinstance(value, dict):
        raise AuditSigningError(f"{field} must be an object")
    return cast(JsonObject, value)


def _require_string(value: object, field: str, expected: Optional[str] = None) -> str:
    if not isinstance(value, str) or not value:
        raise AuditSigningError(f"{field} must be a string")
    if expected is not None and value != expected:
        raise AuditSigningError(f"{field} has unsupported value")
    return value


def _require_any_string(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise AuditSigningError(f"{field} must be a string")
    return value


def _require_prefixed_hash(value: object, field: str) -> str:
    string_value = _require_string(value, field)
    if not string_value.startswith("sha256:") or len(string_value) != 71:
        raise AuditSigningError(f"{field} must be a sha256 digest")
    return string_value


def _optional_string(value: object) -> Optional[str]:
    return value if isinstance(value, str) else None


def _optional_hash_from_bundle(bundle: JsonObject) -> Optional[str]:
    signature = bundle.get("signature")
    if not isinstance(signature, dict):
        return None
    key_id = signature.get("key_id")
    return key_id if isinstance(key_id, str) else None

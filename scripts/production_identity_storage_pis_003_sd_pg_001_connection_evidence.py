"""Test-only PIS-003 connection-evidence harness.

The implementation is intentionally non-executable until a later exact-candidate
review and environment-specific execution gate change ``EXECUTION_AUTHORITY_ACTIVE``.
Importing this module does not import Psycopg, read connection environment variables,
construct an engine, or open a socket.
"""

from __future__ import annotations

import argparse
import base64
import ctypes
import hashlib
import hmac
import importlib
import importlib.metadata
import ipaddress
import json
import os
import platform
import re
import sqlite3
import subprocess
import sys
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any, NoReturn, cast

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from ithildin_api.storage_import import (
    DescriptorImportReceipt,
    PreconnectionRollbackReceipt,
    StorageImportError,
    import_validated_descriptor_snapshot,
    validate_descriptor_snapshot,
)
from ithildin_api.storage_schema import sandbox_descriptors
from ithildin_schemas import JsonObject
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import Connection
from sqlalchemy.pool import NullPool

ROOT = Path(__file__).resolve().parents[1]
RUN_LABEL = "isolated_nonproduction_connection_evidence_only"
EXECUTION_AUTHORITY_ACTIVE = False
EXECUTION_AUTHORITY_REASON = (
    "exact harness review and environment-specific execution gate are required"
)
DSN_ENV = "ITHILDIN_PIS3_TEST_DSN"
BINDING_KEY_ENV = "ITHILDIN_PIS3_TARGET_BINDING_KEY"
PSYCOPG_IMPL_ENV = "PSYCOPG_IMPL"
RECEIPT_DOMAIN = b"ITHILDIN-PIS3-CONNECTION-RECEIPT-V1\n"
BINDING_DOMAIN = b"ITHILDIN-PIS3-DSN-BINDING-V1\n"
REQUIRED_RECEIPT_TYPES = {
    "preconnection_rollback_receipt",
    "target_owner_quarantine_receipt",
    "target_discard_receipt",
}
PREFLIGHT_RECEIPT_TYPES = REQUIRED_RECEIPT_TYPES - {"target_discard_receipt"}
FAILURE_CATEGORIES = {
    "preflight_invalid",
    "receipt_authenticity_failed",
    "dsn_binding_failed",
    "native_library_identity_mismatch",
    "connection_attempt_budget_exhausted",
    "tls_verification_failed",
    "authentication_or_authorization_failed",
    "target_unavailable",
    "target_not_empty",
    "migration_failed",
    "semantic_verification_failed",
    "transaction_state_lost",
    "ambiguous_commit",
}
FAILURE_STAGES = {
    "authority_gate",
    "manifest",
    "external_receipts",
    "synthetic_source",
    "environment",
    "dsn_binding",
    "driver_identity",
    "connection",
    "migration",
    "import",
    "rollback",
    "post_rollback",
    "discard",
    "secret_scan",
}
SAFE_LABEL = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")
ISSUER_ID = re.compile(r"^[a-z][a-z0-9._-]{2,63}$")
RUN_ID = re.compile(r"^pis3run_[0-9a-f]{32}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
HMAC_DIGEST = re.compile(r"^hmac-sha256:[0-9a-f]{64}$")
UTC_TEXT = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\+00:00$")
HOSTNAME = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(?:\."
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*$"
)
AMBIENT_LIBPQ = re.compile(r"^PG[A-Z0-9_]+$")
SAFE_RAW_COMPONENT = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
QUERY_ORDER = (
    "application_name",
    "connect_timeout",
    "sslmode",
    "sslrootcert",
)
FAILURE_MAP: tuple[tuple[str, str], ...] = (
    ("certificate verify failed", "tls_verification_failed"),
    ("ssl", "tls_verification_failed"),
    ("authentication", "authentication_or_authorization_failed"),
    ("authorization", "authentication_or_authorization_failed"),
    ("permission", "authentication_or_authorization_failed"),
    ("timeout", "target_unavailable"),
    ("unavailable", "target_unavailable"),
    ("refused", "target_unavailable"),
)


class ConnectionEvidenceError(RuntimeError):
    """A closed, secret-safe harness failure."""

    def __init__(self, category: str, stage: str) -> None:
        if category not in FAILURE_CATEGORIES or stage not in FAILURE_STAGES:
            raise ValueError("failure category and stage must be closed values")
        self.category = category
        self.stage = stage
        super().__init__(f"PIS-003 connection evidence failed: {category} at {stage}")

    def evidence(self) -> JsonObject:
        return {
            "schema_version": "1",
            "run_label": RUN_LABEL,
            "failure_category": self.category,
            "failure_stage": self.stage,
            "raw_exception_included": False,
            "credentials_included": False,
            "dsn_included": False,
        }


@dataclass(frozen=True)
class TrustRecord:
    issuer_id: str
    public_key: Ed25519PublicKey
    public_key_fingerprint: str
    allowed_receipt_types: frozenset[str]
    valid_from: datetime
    valid_until: datetime


@dataclass(frozen=True)
class VerifiedReceipt:
    receipt_type: str
    issuer_id: str
    run_id: str
    target_label: str
    reviewed_candidate_commit: str
    source_digest: str
    issued_at: datetime
    expires_at: datetime
    assertion: Mapping[str, object]
    file_sha256: str


@dataclass(frozen=True)
class ParsedDsn:
    scheme: str
    hostname_ascii_lower: str
    port: int
    database_utf8: str
    user_utf8: str
    password_utf8: str
    sslmode: str
    sslrootcert_realpath: str
    application_name: str
    connect_timeout_seconds: int

    def binding_payload(
        self,
        *,
        run_id: str,
        target_label: str,
        reviewed_candidate_commit: str,
        sslrootcert_sha256: str,
    ) -> JsonObject:
        return {
            "application_name": self.application_name,
            "connect_timeout_seconds": self.connect_timeout_seconds,
            "database_utf8": self.database_utf8,
            "hostname_ascii_lower": self.hostname_ascii_lower,
            "password_utf8": self.password_utf8,
            "port": self.port,
            "reviewed_candidate_commit": reviewed_candidate_commit,
            "run_id": run_id,
            "schema_version": "1",
            "scheme": self.scheme,
            "sslmode": self.sslmode,
            "sslrootcert_realpath": self.sslrootcert_realpath,
            "sslrootcert_sha256": sslrootcert_sha256,
            "target_label": target_label,
            "user_utf8": self.user_utf8,
        }


@dataclass(frozen=True)
class FrozenSnapshot:
    path: Path
    file_digest: str
    records_digest: str
    rows: tuple[Mapping[str, object], ...]


@dataclass(frozen=True)
class ValidatedPreflight:
    manifest: Mapping[str, object]
    run_id: str
    target_label: str
    reviewed_candidate_commit: str
    source: FrozenSnapshot
    rollback_receipt: VerifiedReceipt
    target_owner_receipt: VerifiedReceipt
    trust_records: Mapping[str, TrustRecord]
    output_root: Path
    manifest_digest: str


@dataclass(frozen=True)
class ConnectionRunResult:
    run_id: str
    target_label: str
    reviewed_candidate_commit: str
    source_digest: str
    import_receipt: DescriptorImportReceipt
    transaction_rolled_back: bool
    post_rollback_rows_absent: bool
    connection_attempt_count: int
    target_discard_receipt_pending: bool = True

    def evidence(self) -> JsonObject:
        return {
            "schema_version": "1",
            "run_label": RUN_LABEL,
            "run_id": self.run_id,
            "target_label": self.target_label,
            "reviewed_candidate_commit": self.reviewed_candidate_commit,
            "source_digest": self.source_digest,
            "import_receipt_digest": self.import_receipt.digest(),
            "record_count": self.import_receipt.record_count,
            "descriptor_ids": list(self.import_receipt.descriptor_ids),
            "transaction_rolled_back": self.transaction_rolled_back,
            "post_rollback_rows_absent": self.post_rollback_rows_absent,
            "connection_attempt_count": self.connection_attempt_count,
            "database_commit_performed": False,
            "target_activated": False,
            "target_discard_receipt_pending": self.target_discard_receipt_pending,
            "credentials_included": False,
            "dsn_included": False,
        }


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def load_strict_canonical_json(path: Path) -> Mapping[str, object]:
    try:
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            raise ValueError("UTF-8 BOM is forbidden")
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_closed_object,
            parse_constant=_reject_nonfinite,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        raise ConnectionEvidenceError("preflight_invalid", "manifest") from None
    if not isinstance(value, dict) or canonical_json_bytes(value) != raw:
        raise ConnectionEvidenceError("preflight_invalid", "manifest")
    return cast(Mapping[str, object], value)


def validate_execution_preflight(
    manifest_path: Path,
    *,
    expected_reviewed_commit: str,
    repo_root: Path = ROOT,
    now: datetime | None = None,
) -> ValidatedPreflight:
    """Validate every non-secret prerequisite without loading a driver or DSN."""

    checked_now = _require_utc(now or datetime.now(UTC), "manifest")
    manifest_path = manifest_path.resolve(strict=True)
    manifest = load_strict_canonical_json(manifest_path)
    expected_keys = {
        "schema_version",
        "run_label",
        "run_id",
        "target_label",
        "reviewed_candidate_commit",
        "issued_at",
        "expires_at",
        "output_root",
        "source",
        "implementation_artifact_hashes",
        "trust_records",
        "preconnection_receipts",
        "python_dependencies",
        "native_dependencies",
        "tls_root",
        "sbom_and_licenses",
        "dsn_posture",
        "connection_attempt_budget",
        "negative_scenario",
        "secret_scan_marker_commitment",
    }
    _require_exact_keys(manifest, expected_keys, "manifest")
    if manifest.get("schema_version") != "1" or manifest.get("run_label") != RUN_LABEL:
        _fail("preflight_invalid", "manifest")
    run_id = _require_pattern(manifest.get("run_id"), RUN_ID, "manifest")
    target_label = _require_pattern(manifest.get("target_label"), SAFE_LABEL, "manifest")
    reviewed_commit = _require_pattern(
        manifest.get("reviewed_candidate_commit"), COMMIT, "manifest"
    )
    if reviewed_commit != expected_reviewed_commit:
        _fail("preflight_invalid", "manifest")
    issued_at = _parse_utc_text(manifest.get("issued_at"), "manifest")
    expires_at = _parse_utc_text(manifest.get("expires_at"), "manifest")
    if not (issued_at < expires_at <= issued_at + timedelta(minutes=15)):
        _fail("preflight_invalid", "manifest")
    if not (issued_at <= checked_now <= expires_at):
        _fail("preflight_invalid", "manifest")

    output_root = _absolute_path(manifest.get("output_root"), "manifest")
    repo_resolved = repo_root.resolve()
    if _inside(output_root, repo_resolved):
        _fail("preflight_invalid", "manifest")

    source = _mapping(manifest.get("source"), "manifest")
    _require_exact_keys(source, {"path", "file_sha256", "records_digest"}, "manifest")
    source_path = _absolute_path(source.get("path"), "manifest")
    source_file_digest = _require_pattern(source.get("file_sha256"), DIGEST, "manifest")
    source_records_digest = _require_pattern(source.get("records_digest"), DIGEST, "manifest")
    frozen = read_frozen_snapshot(
        source_path,
        expected_file_digest=source_file_digest,
        expected_records_digest=source_records_digest,
    )

    _validate_artifact_hashes(
        _mapping(manifest.get("implementation_artifact_hashes"), "manifest"),
        repo_resolved,
    )
    _validate_dependency_receipts(manifest, repo_resolved, output_root)
    trust_records = _load_trust_records(
        manifest.get("trust_records"),
        repo_root=repo_resolved,
        output_root=output_root,
        now=checked_now,
    )
    receipts = _mapping(manifest.get("preconnection_receipts"), "manifest")
    _require_exact_keys(receipts, PREFLIGHT_RECEIPT_TYPES, "external_receipts")
    verified = {
        receipt_type: verify_external_receipt(
            _external_file_reference(
                receipts.get(receipt_type),
                repo_root=repo_resolved,
                output_root=output_root,
            ),
            trust_records=trust_records,
            verification_time=checked_now,
        )
        for receipt_type in PREFLIGHT_RECEIPT_TYPES
    }
    for receipt in verified.values():
        if (
            receipt.run_id != run_id
            or receipt.target_label != target_label
            or receipt.reviewed_candidate_commit != reviewed_commit
            or receipt.source_digest != source_file_digest
        ):
            _fail("receipt_authenticity_failed", "external_receipts")
    owner = verified["target_owner_quarantine_receipt"]
    expected_budget = 1 if manifest.get("negative_scenario") is not None else 2
    if manifest.get("connection_attempt_budget") != expected_budget:
        _fail("preflight_invalid", "manifest")
    if owner.assertion.get("connection_attempt_budget") != expected_budget:
        _fail("receipt_authenticity_failed", "external_receipts")
    if manifest.get("negative_scenario") is not None:
        _require_pattern(manifest.get("negative_scenario"), SAFE_LABEL, "manifest")
    _validate_dsn_posture(_mapping(manifest.get("dsn_posture"), "manifest"))
    _require_pattern(manifest.get("secret_scan_marker_commitment"), DIGEST, "manifest")
    return ValidatedPreflight(
        manifest=manifest,
        run_id=run_id,
        target_label=target_label,
        reviewed_candidate_commit=reviewed_commit,
        source=frozen,
        rollback_receipt=verified["preconnection_rollback_receipt"],
        target_owner_receipt=owner,
        trust_records=trust_records,
        output_root=output_root,
        manifest_digest=_sha256_file(manifest_path),
    )


def read_frozen_snapshot(
    path: Path,
    *,
    expected_file_digest: str,
    expected_records_digest: str,
) -> FrozenSnapshot:
    """Read one immutable SQLite snapshot and prove its digest stayed unchanged."""

    resolved = path.resolve(strict=True)
    try:
        if resolved.stat().st_mode & 0o222:
            _fail("preflight_invalid", "synthetic_source")
    except OSError:
        _fail("preflight_invalid", "synthetic_source")
    before = _sha256_file(resolved)
    if before != expected_file_digest:
        _fail("preflight_invalid", "synthetic_source")
    uri = f"file:{resolved.as_posix()}?mode=ro&immutable=1"
    try:
        with sqlite3.connect(uri, uri=True) as connection:
            connection.execute("PRAGMA query_only = ON")
            query_only = connection.execute("PRAGMA query_only").fetchone()
            if query_only != (1,):
                _fail("preflight_invalid", "synthetic_source")
            raw_rows = connection.execute(
                """
                SELECT descriptor_id, status, created_at, updated_at,
                       payload_hash, payload_json
                FROM sandbox_descriptors
                ORDER BY descriptor_id
                """
            ).fetchall()
    except (sqlite3.Error, OSError):
        raise ConnectionEvidenceError("preflight_invalid", "synthetic_source") from None
    rows = tuple(
        {
            "descriptor_id": _exact_string(row[0], "synthetic_source"),
            "status": _exact_string(row[1], "synthetic_source"),
            "created_at": _exact_string(row[2], "synthetic_source"),
            "updated_at": _exact_string(row[3], "synthetic_source"),
            "payload_hash": _exact_string(row[4], "synthetic_source"),
            "payload_json": _exact_string(row[5], "synthetic_source"),
        }
        for row in raw_rows
    )
    try:
        snapshot = validate_descriptor_snapshot(rows)
    except Exception:
        raise ConnectionEvidenceError("preflight_invalid", "synthetic_source") from None
    after = _sha256_file(resolved)
    if before != after or snapshot.records_digest != expected_records_digest:
        _fail("preflight_invalid", "synthetic_source")
    return FrozenSnapshot(
        path=resolved,
        file_digest=before,
        records_digest=snapshot.records_digest,
        rows=rows,
    )


def parse_canonical_dsn(value: str, *, approved_tls_root: Path) -> ParsedDsn:
    """Parse the closed canonical DSN grammar without invoking Psycopg or libpq."""

    try:
        value.encode("ascii", errors="strict")
    except UnicodeError:
        _fail("dsn_binding_failed", "dsn_binding")
    prefix = "postgresql+psycopg://"
    if not value.startswith(prefix) or "#" in value:
        _fail("dsn_binding_failed", "dsn_binding")
    body = value[len(prefix) :]
    if body.count("@") != 1 or "?" not in body:
        _fail("dsn_binding_failed", "dsn_binding")
    userinfo, host_path_query = body.split("@", 1)
    if userinfo.count(":") != 1:
        _fail("dsn_binding_failed", "dsn_binding")
    raw_user, raw_password = userinfo.split(":", 1)
    user = _decode_canonical_component(raw_user, min_bytes=1, max_bytes=63)
    password = _decode_canonical_component(raw_password, min_bytes=1, max_bytes=1024)
    if "\x00" in password:
        _fail("dsn_binding_failed", "dsn_binding")
    authority_path, raw_query = host_path_query.split("?", 1)
    if authority_path.count("/") != 1 or authority_path.count(":") != 1:
        _fail("dsn_binding_failed", "dsn_binding")
    authority, raw_database = authority_path.split("/", 1)
    hostname, raw_port = authority.split(":", 1)
    if not HOSTNAME.fullmatch(hostname) or hostname != hostname.lower() or hostname.endswith("."):
        _fail("dsn_binding_failed", "dsn_binding")
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        _fail("dsn_binding_failed", "dsn_binding")
    if not raw_port.isdecimal() or raw_port.startswith("0"):
        _fail("dsn_binding_failed", "dsn_binding")
    port = int(raw_port)
    if not 1 <= port <= 65535:
        _fail("dsn_binding_failed", "dsn_binding")
    database = _decode_canonical_component(raw_database, min_bytes=1, max_bytes=63)
    if "/" in database or any(ord(char) < 32 for char in database):
        _fail("dsn_binding_failed", "dsn_binding")
    pairs = raw_query.split("&")
    if len(pairs) != 4:
        _fail("dsn_binding_failed", "dsn_binding")
    query: dict[str, str] = {}
    seen_order: list[str] = []
    for pair in pairs:
        if pair.count("=") != 1:
            _fail("dsn_binding_failed", "dsn_binding")
        raw_key, raw_value = pair.split("=", 1)
        if not raw_key or not raw_value or not raw_key.isascii():
            _fail("dsn_binding_failed", "dsn_binding")
        if raw_key in query:
            _fail("dsn_binding_failed", "dsn_binding")
        query[raw_key] = _decode_canonical_component(raw_value, min_bytes=1, max_bytes=1024)
        seen_order.append(raw_key)
    if tuple(seen_order) != QUERY_ORDER:
        _fail("dsn_binding_failed", "dsn_binding")
    approved_root = approved_tls_root.resolve(strict=True)
    if query != {
        "application_name": "ithildin-pis3-evidence",
        "connect_timeout": "5",
        "sslmode": "verify-full",
        "sslrootcert": str(approved_root),
    }:
        _fail("dsn_binding_failed", "dsn_binding")
    return ParsedDsn(
        scheme="postgresql+psycopg",
        hostname_ascii_lower=hostname,
        port=port,
        database_utf8=database,
        user_utf8=user,
        password_utf8=password,
        sslmode="verify-full",
        sslrootcert_realpath=str(approved_root),
        application_name="ithildin-pis3-evidence",
        connect_timeout_seconds=5,
    )


def validate_dsn_target_binding(
    dsn: str,
    binding_key: str,
    *,
    approved_tls_root: Path,
    sslrootcert_sha256: str,
    run_id: str,
    target_label: str,
    reviewed_candidate_commit: str,
    expected_commitment: str,
) -> None:
    parsed = parse_canonical_dsn(dsn, approved_tls_root=approved_tls_root)
    key = bytearray(_decode_base64url(binding_key, 32, "dsn_binding"))
    try:
        payload = parsed.binding_payload(
            run_id=_require_pattern(run_id, RUN_ID, "dsn_binding"),
            target_label=_require_pattern(target_label, SAFE_LABEL, "dsn_binding"),
            reviewed_candidate_commit=_require_pattern(
                reviewed_candidate_commit, COMMIT, "dsn_binding"
            ),
            sslrootcert_sha256=_require_pattern(sslrootcert_sha256, DIGEST, "dsn_binding"),
        )
        actual = (
            "hmac-sha256:"
            + hmac.new(
                bytes(key), BINDING_DOMAIN + canonical_json_bytes(payload), hashlib.sha256
            ).hexdigest()
        )
        if not HMAC_DIGEST.fullmatch(expected_commitment) or not hmac.compare_digest(
            actual, expected_commitment
        ):
            _fail("dsn_binding_failed", "dsn_binding")
    finally:
        for index in range(len(key)):
            key[index] = 0


def reject_ambient_libpq_environment(environment: Mapping[str, str]) -> None:
    if any(AMBIENT_LIBPQ.fullmatch(key) for key in environment):
        _fail("preflight_invalid", "environment")


def verify_external_receipt(
    reference: tuple[Path, str],
    *,
    trust_records: Mapping[str, TrustRecord],
    verification_time: datetime,
) -> VerifiedReceipt:
    path, expected_digest = reference
    envelope = load_strict_canonical_json(path)
    _require_exact_keys(envelope, {"payload", "signature"}, "external_receipts")
    payload = _mapping(envelope.get("payload"), "external_receipts")
    signature = _mapping(envelope.get("signature"), "external_receipts")
    _require_exact_keys(
        signature,
        {"algorithm", "key_id", "signature_base64url"},
        "external_receipts",
    )
    if signature.get("algorithm") != "Ed25519":
        _fail("receipt_authenticity_failed", "external_receipts")
    issuer_id = _require_pattern(payload.get("issuer_id"), ISSUER_ID, "external_receipts")
    trust = trust_records.get(issuer_id)
    if trust is None or signature.get("key_id") != trust.public_key_fingerprint:
        _fail("receipt_authenticity_failed", "external_receipts")
    signature_bytes = _decode_base64url(
        signature.get("signature_base64url"), 64, "external_receipts"
    )
    try:
        trust.public_key.verify(
            signature_bytes,
            RECEIPT_DOMAIN + canonical_json_bytes(payload),
        )
    except InvalidSignature:
        raise ConnectionEvidenceError("receipt_authenticity_failed", "external_receipts") from None
    expected_payload_keys = {
        "schema_version",
        "receipt_type",
        "issuer_id",
        "issued_at",
        "expires_at",
        "provenance",
        "run_id",
        "target_label",
        "reviewed_candidate_commit",
        "source_digest",
        "assertion",
    }
    _require_exact_keys(payload, expected_payload_keys, "external_receipts")
    if payload.get("schema_version") != "1":
        _fail("receipt_authenticity_failed", "external_receipts")
    receipt_type = _exact_string(payload.get("receipt_type"), "external_receipts")
    if (
        receipt_type not in REQUIRED_RECEIPT_TYPES
        or receipt_type not in trust.allowed_receipt_types
    ):
        _fail("receipt_authenticity_failed", "external_receipts")
    expected_provenance = (
        "external_target_discard_owner_attestation"
        if receipt_type == "target_discard_receipt"
        else "external_target_owner_attestation"
    )
    if payload.get("provenance") != expected_provenance:
        _fail("receipt_authenticity_failed", "external_receipts")
    issued_at = _parse_utc_text(payload.get("issued_at"), "external_receipts")
    expires_at = _parse_utc_text(payload.get("expires_at"), "external_receipts")
    if not (issued_at < expires_at <= issued_at + timedelta(minutes=15)):
        _fail("receipt_authenticity_failed", "external_receipts")
    if not (
        trust.valid_from <= issued_at
        and expires_at <= trust.valid_until
        and issued_at <= verification_time <= expires_at
    ):
        _fail("receipt_authenticity_failed", "external_receipts")
    assertion = _mapping(payload.get("assertion"), "external_receipts")
    if len(canonical_json_bytes(assertion)) > 4096:
        _fail("receipt_authenticity_failed", "external_receipts")
    _validate_receipt_assertion(receipt_type, assertion)
    actual_digest = _sha256_file(path)
    if actual_digest != expected_digest:
        _fail("receipt_authenticity_failed", "external_receipts")
    return VerifiedReceipt(
        receipt_type=receipt_type,
        issuer_id=issuer_id,
        run_id=_require_pattern(payload.get("run_id"), RUN_ID, "external_receipts"),
        target_label=_require_pattern(payload.get("target_label"), SAFE_LABEL, "external_receipts"),
        reviewed_candidate_commit=_require_pattern(
            payload.get("reviewed_candidate_commit"), COMMIT, "external_receipts"
        ),
        source_digest=_require_pattern(payload.get("source_digest"), DIGEST, "external_receipts"),
        issued_at=issued_at,
        expires_at=expires_at,
        assertion=assertion,
        file_sha256=actual_digest,
    )


def execute_connection_evidence(
    manifest_path: Path,
    *,
    expected_reviewed_commit: str,
    environment: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> ConnectionRunResult:
    """Execute the future harness only after the later authority gate is active."""

    if not EXECUTION_AUTHORITY_ACTIVE:
        raise ConnectionEvidenceError("preflight_invalid", "authority_gate")
    checked_now = _require_utc(now or datetime.now(UTC), "manifest")
    preflight = validate_execution_preflight(
        manifest_path,
        expected_reviewed_commit=expected_reviewed_commit,
        now=checked_now,
    )
    env = dict(os.environ if environment is None else environment)
    reject_ambient_libpq_environment(env)
    if env.get(PSYCOPG_IMPL_ENV) != "python":
        _fail("preflight_invalid", "environment")
    dsn = env.get(DSN_ENV)
    binding_key = env.get(BINDING_KEY_ENV)
    if not dsn or not binding_key:
        _fail("preflight_invalid", "environment")
    tls_root = _mapping(preflight.manifest.get("tls_root"), "manifest")
    tls_root_path = _absolute_path(tls_root.get("path"), "manifest")
    tls_root_digest = _require_pattern(tls_root.get("sha256"), DIGEST, "manifest")
    commitment = _exact_string(
        preflight.target_owner_receipt.assertion.get("target_binding_hmac_sha256_commitment"),
        "external_receipts",
    )
    validate_dsn_target_binding(
        dsn,
        binding_key,
        approved_tls_root=tls_root_path,
        sslrootcert_sha256=tls_root_digest,
        run_id=preflight.run_id,
        target_label=preflight.target_label,
        reviewed_candidate_commit=preflight.reviewed_candidate_commit,
        expected_commitment=commitment,
    )
    del binding_key
    driver = _load_plain_psycopg_driver()
    _validate_loaded_native_identity(driver, preflight.manifest)
    engine = create_engine(dsn, poolclass=NullPool)
    del dsn
    attempts = 0
    import_receipt: DescriptorImportReceipt | None = None
    try:
        attempts += 1
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                try:
                    _run_online_alembic(connection)
                except Exception:
                    raise ConnectionEvidenceError("migration_failed", "migration") from None
                snapshot = validate_descriptor_snapshot(preflight.source.rows)
                rollback = PreconnectionRollbackReceipt(
                    candidate_commit=preflight.reviewed_candidate_commit,
                    target_label=preflight.target_label,
                )
                context = __import_context(rollback)
                try:
                    import_receipt = import_validated_descriptor_snapshot(
                        connection,
                        snapshot,
                        context,
                        rollback,
                        verified_at=checked_now,
                    )
                except StorageImportError as exc:
                    raise ConnectionEvidenceError(
                        _safe_import_failure_category(exc), "import"
                    ) from None
            except ConnectionEvidenceError:
                raise
            finally:
                if transaction.is_active:
                    transaction.rollback()
        attempts += 1
        with engine.connect() as verification_connection:
            post_rollback_absent = _post_rollback_rows_absent(verification_connection)
    except ConnectionEvidenceError:
        raise
    except Exception as exc:
        category = _safe_connection_failure_category(exc)
        raise ConnectionEvidenceError(category, "connection") from None
    finally:
        engine.dispose()
    if _sha256_file(preflight.source.path) != preflight.source.file_digest:
        _fail("preflight_invalid", "synthetic_source")
    if attempts != 2 or not post_rollback_absent or import_receipt is None:
        _fail("transaction_state_lost", "post_rollback")
    return ConnectionRunResult(
        run_id=preflight.run_id,
        target_label=preflight.target_label,
        reviewed_candidate_commit=preflight.reviewed_candidate_commit,
        source_digest=preflight.source.file_digest,
        import_receipt=import_receipt,
        transaction_rolled_back=True,
        post_rollback_rows_absent=True,
        connection_attempt_count=attempts,
    )


def finalize_discard_receipt(
    preflight: ValidatedPreflight,
    reference: tuple[Path, str],
    *,
    last_connection_closed_at: datetime,
    verification_time: datetime,
) -> VerifiedReceipt:
    receipt = verify_external_receipt(
        reference,
        trust_records=preflight.trust_records,
        verification_time=verification_time,
    )
    owner_assertion = preflight.target_owner_receipt.assertion
    if (
        receipt.receipt_type != "target_discard_receipt"
        or receipt.issuer_id != owner_assertion.get("discard_owner_id")
        or receipt.run_id != preflight.run_id
        or receipt.target_label != preflight.target_label
        or receipt.reviewed_candidate_commit != preflight.reviewed_candidate_commit
        or receipt.source_digest != preflight.source.file_digest
    ):
        _fail("receipt_authenticity_failed", "discard")
    closed_at = _parse_utc_text(receipt.assertion.get("last_connection_closed_at"), "discard")
    discarded_at = _parse_utc_text(receipt.assertion.get("target_discarded_at"), "discard")
    if closed_at != _require_utc(last_connection_closed_at, "discard"):
        _fail("receipt_authenticity_failed", "discard")
    if not closed_at < discarded_at <= receipt.issued_at:
        _fail("receipt_authenticity_failed", "discard")
    return receipt


def scan_output_tree_for_secrets(
    output_root: Path,
    *,
    secret_markers: Sequence[bytes],
) -> None:
    forbidden_patterns = (
        re.compile(rb"postgres(?:ql)?(?:\+psycopg)?://", re.IGNORECASE),
        re.compile(rb"(?:password|passwd|pwd)\s*[:=]", re.IGNORECASE),
        re.compile(rb"ITHILDIN_PIS3_(?:TEST_DSN|TARGET_BINDING_KEY)"),
    )
    root = output_root.resolve(strict=True)
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        try:
            data = path.read_bytes()
        except OSError:
            _fail("preflight_invalid", "secret_scan")
        if any(marker and marker in data for marker in secret_markers):
            _fail("preflight_invalid", "secret_scan")
        if any(pattern.search(data) for pattern in forbidden_patterns):
            _fail("preflight_invalid", "secret_scan")


def _load_plain_psycopg_driver() -> ModuleType:
    try:
        driver = importlib.import_module("psycopg")
        pq = importlib.import_module("psycopg.pq")
    except Exception:
        raise ConnectionEvidenceError(
            "native_library_identity_mismatch", "driver_identity"
        ) from None
    if getattr(pq, "__impl__", None) != "python":
        _fail("native_library_identity_mismatch", "driver_identity")
    return driver


def _validate_loaded_native_identity(
    driver: ModuleType,
    manifest: Mapping[str, object],
) -> None:
    """Bind the loaded pure-Python driver, libpq, and TLS library to preflight."""

    del driver
    try:
        pq = importlib.import_module("psycopg.pq")
        pq_ctypes = importlib.import_module("psycopg.pq._pq_ctypes")
        libpq_path = Path(cast(str, pq_ctypes.libname)).resolve(strict=True)
        libpq_version = str(cast(Any, pq.version)())
    except Exception:
        raise ConnectionEvidenceError(
            "native_library_identity_mismatch", "driver_identity"
        ) from None
    native = _mapping(manifest.get("native_dependencies"), "manifest")
    libpq = _mapping(native.get("libpq"), "manifest")
    tls = _mapping(native.get("tls_backend"), "manifest")
    _match_loaded_identity(
        libpq,
        loaded_path=libpq_path,
        loaded_version=libpq_version,
    )
    tls_path = _absolute_path(tls.get("loaded_library_realpath"), "manifest")
    if not _library_dependency_is_bound(libpq_path, tls_path):
        _fail("native_library_identity_mismatch", "driver_identity")
    _match_loaded_identity(
        tls,
        loaded_path=tls_path,
        loaded_version=_openssl_library_version(tls_path),
    )


def _match_loaded_identity(
    expected: Mapping[str, object],
    *,
    loaded_path: Path,
    loaded_version: str,
) -> None:
    expected_path = _absolute_path(expected.get("loaded_library_realpath"), "manifest")
    expected_digest = _require_pattern(expected.get("library_sha256"), DIGEST, "manifest")
    if (
        loaded_path != expected_path
        or _sha256_file(loaded_path) != expected_digest
        or expected.get("version") != loaded_version
        or expected.get("architecture") != platform.machine()
    ):
        _fail("native_library_identity_mismatch", "driver_identity")


def _library_dependency_is_bound(library: Path, dependency: Path) -> bool:
    command_line = (
        ["otool", "-L", str(library)] if sys.platform == "darwin" else ["ldd", str(library)]
    )
    try:
        result = subprocess.run(
            command_line,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    if result.returncode != 0:
        return False
    return str(dependency) in result.stdout or dependency.name in result.stdout


def _openssl_library_version(path: Path) -> str:
    try:
        library = ctypes.CDLL(str(path))
        version_function = library.OpenSSL_version
        version_function.argtypes = [ctypes.c_int]
        version_function.restype = ctypes.c_char_p
        raw = version_function(0)
        if not isinstance(raw, bytes):
            _fail("native_library_identity_mismatch", "driver_identity")
        return raw.decode("ascii", errors="strict")
    except (OSError, AttributeError, UnicodeError):
        raise ConnectionEvidenceError(
            "native_library_identity_mismatch", "driver_identity"
        ) from None


def _run_online_alembic(connection: Connection) -> None:
    config = Config(str(ROOT / "db/alembic/alembic.ini"))
    if ScriptDirectory.from_config(config).get_heads() != ["0001_sandbox_descriptors"]:
        _fail("migration_failed", "migration")
    config.attributes["connection"] = connection
    command.upgrade(config, "head")


def _post_rollback_rows_absent(connection: Connection) -> bool:
    relation = connection.execute(select(func.to_regclass("sandbox_descriptors"))).scalar_one()
    if relation is None:
        return True
    count = connection.execute(select(func.count()).select_from(sandbox_descriptors)).scalar_one()
    return type(count) is int and count == 0


def __import_context(rollback: PreconnectionRollbackReceipt) -> Any:
    from ithildin_api.storage_import import DescriptorImportContext

    return DescriptorImportContext.bind(rollback)


def _load_trust_records(
    value: object,
    *,
    repo_root: Path,
    output_root: Path,
    now: datetime,
) -> Mapping[str, TrustRecord]:
    if not isinstance(value, list) or not 1 <= len(value) <= 3:
        _fail("preflight_invalid", "external_receipts")
    records: dict[str, TrustRecord] = {}
    for item in value:
        path, expected_digest = _external_file_reference(
            item, repo_root=repo_root, output_root=output_root
        )
        if _sha256_file(path) != expected_digest:
            _fail("receipt_authenticity_failed", "external_receipts")
        document = load_strict_canonical_json(path)
        _require_exact_keys(
            document,
            {
                "issuer_id",
                "ed25519_public_key",
                "public_key_fingerprint",
                "allowed_receipt_types",
                "valid_from",
                "valid_until",
            },
            "external_receipts",
        )
        issuer_id = _require_pattern(document.get("issuer_id"), ISSUER_ID, "external_receipts")
        raw_key = _decode_base64url(document.get("ed25519_public_key"), 32, "external_receipts")
        fingerprint = "sha256:" + hashlib.sha256(raw_key).hexdigest()
        if document.get("public_key_fingerprint") != fingerprint:
            _fail("receipt_authenticity_failed", "external_receipts")
        allowed_raw = document.get("allowed_receipt_types")
        if (
            not isinstance(allowed_raw, list)
            or not allowed_raw
            or any(type(item) is not str for item in allowed_raw)
        ):
            _fail("receipt_authenticity_failed", "external_receipts")
        allowed = frozenset(cast(list[str], allowed_raw))
        if len(allowed) != len(allowed_raw) or not allowed <= REQUIRED_RECEIPT_TYPES:
            _fail("receipt_authenticity_failed", "external_receipts")
        valid_from = _parse_utc_text(document.get("valid_from"), "external_receipts")
        valid_until = _parse_utc_text(document.get("valid_until"), "external_receipts")
        if not valid_from < valid_until or not valid_from <= now <= valid_until:
            _fail("receipt_authenticity_failed", "external_receipts")
        if issuer_id in records:
            _fail("receipt_authenticity_failed", "external_receipts")
        records[issuer_id] = TrustRecord(
            issuer_id=issuer_id,
            public_key=Ed25519PublicKey.from_public_bytes(raw_key),
            public_key_fingerprint=fingerprint,
            allowed_receipt_types=allowed,
            valid_from=valid_from,
            valid_until=valid_until,
        )
    return records


def _validate_receipt_assertion(receipt_type: str, assertion: Mapping[str, object]) -> None:
    if receipt_type == "preconnection_rollback_receipt":
        expected = {
            "activation_allowed": False,
            "bound_before_connection": True,
            "rollback_disposition": (
                "revert_exact_candidate_and_discard_isolated_target_before_activation"
            ),
            "source_unchanged": True,
        }
        if assertion != expected or any(
            type(assertion[key]) is not bool
            for key in ("activation_allowed", "bound_before_connection", "source_unchanged")
        ):
            _fail("receipt_authenticity_failed", "external_receipts")
        return
    if receipt_type == "target_owner_quarantine_receipt":
        _require_exact_keys(
            assertion,
            {
                "connection_attempt_budget",
                "dedicated_nonproduction_purpose",
                "discard_owner_id",
                "target_binding_hmac_sha256_commitment",
                "target_empty",
                "target_quarantined",
            },
            "external_receipts",
        )
        budget = assertion.get("connection_attempt_budget")
        if type(budget) is not int or budget not in {1, 2}:
            _fail("receipt_authenticity_failed", "external_receipts")
        if (
            assertion.get("dedicated_nonproduction_purpose") != "pis3_connection_evidence_only"
            or assertion.get("target_empty") is not True
            or assertion.get("target_quarantined") is not True
        ):
            _fail("receipt_authenticity_failed", "external_receipts")
        _require_pattern(assertion.get("discard_owner_id"), ISSUER_ID, "external_receipts")
        _require_pattern(
            assertion.get("target_binding_hmac_sha256_commitment"),
            HMAC_DIGEST,
            "external_receipts",
        )
        return
    _require_exact_keys(
        assertion,
        {
            "activation_never_occurred",
            "last_connection_closed_at",
            "target_discarded",
            "target_discarded_at",
        },
        "external_receipts",
    )
    if (
        assertion.get("activation_never_occurred") is not True
        or assertion.get("target_discarded") is not True
    ):
        _fail("receipt_authenticity_failed", "external_receipts")
    _parse_utc_text(assertion.get("last_connection_closed_at"), "external_receipts")
    _parse_utc_text(assertion.get("target_discarded_at"), "external_receipts")


def _validate_artifact_hashes(value: Mapping[str, object], repo_root: Path) -> None:
    required = {
        "db/alembic/env.py",
        "db/alembic/versions/0001_sandbox_descriptors.py",
        "apps/api/src/ithildin_api/storage_import.py",
        "apps/api/src/ithildin_api/storage_schema.py",
        "scripts/production_identity_storage_pis_003_sd_pg_001_connection_evidence.py",
        "pyproject.toml",
        "uv.lock",
        "tool-manifests.lock.json",
    }
    if set(value) != required:
        _fail("preflight_invalid", "manifest")
    for relative, digest in value.items():
        expected = _require_pattern(digest, DIGEST, "manifest")
        if _sha256_file(repo_root / relative) != expected:
            _fail("preflight_invalid", "manifest")


def _validate_dependency_receipts(
    manifest: Mapping[str, object], repo_root: Path, output_root: Path
) -> None:
    python_dependencies = _mapping(manifest.get("python_dependencies"), "manifest")
    _require_exact_keys(
        python_dependencies,
        {"python", "sqlalchemy", "alembic", "psycopg", "psycopg_impl"},
        "manifest",
    )
    if python_dependencies.get("psycopg_impl") != "python":
        _fail("preflight_invalid", "manifest")
    expected_versions = {
        "python": platform.python_version(),
        "sqlalchemy": _distribution_version("SQLAlchemy"),
        "alembic": _distribution_version("alembic"),
        "psycopg": _distribution_version("psycopg"),
    }
    for key, expected_version in expected_versions.items():
        if python_dependencies.get(key) != expected_version:
            _fail("preflight_invalid", "manifest")
    for forbidden in ("psycopg-c", "psycopg-binary", "psycopg-pool", "asyncpg"):
        try:
            importlib.metadata.version(forbidden)
        except importlib.metadata.PackageNotFoundError:
            continue
        _fail("preflight_invalid", "manifest")
    native = _mapping(manifest.get("native_dependencies"), "manifest")
    _require_exact_keys(native, {"libpq", "tls_backend"}, "manifest")
    identity_keys = {
        "distribution_source",
        "package_receipt",
        "version",
        "patch_provenance",
        "architecture",
        "loaded_library_realpath",
        "library_sha256",
        "license",
    }
    for identity in native.values():
        item = _mapping(identity, "manifest")
        _require_exact_keys(item, identity_keys, "manifest")
        library_path = _absolute_path(item.get("loaded_library_realpath"), "manifest")
        library_digest = _require_pattern(item.get("library_sha256"), DIGEST, "manifest")
        if _sha256_file(library_path) != library_digest:
            _fail("preflight_invalid", "manifest")
        if any(not isinstance(item.get(key), str) or not item.get(key) for key in identity_keys):
            _fail("preflight_invalid", "manifest")
    tls_root = _mapping(manifest.get("tls_root"), "manifest")
    _require_exact_keys(tls_root, {"path", "sha256"}, "manifest")
    tls_path = _absolute_path(tls_root.get("path"), "manifest")
    if _sha256_file(tls_path) != _require_pattern(tls_root.get("sha256"), DIGEST, "manifest"):
        _fail("preflight_invalid", "manifest")
    sbom = _mapping(manifest.get("sbom_and_licenses"), "manifest")
    _require_exact_keys(sbom, {"path", "sha256"}, "manifest")
    sbom_path, sbom_digest = _external_file_reference(
        sbom, repo_root=repo_root, output_root=output_root
    )
    if _sha256_file(sbom_path) != sbom_digest:
        _fail("preflight_invalid", "manifest")


def _validate_dsn_posture(value: Mapping[str, object]) -> None:
    expected = {
        "scheme": "postgresql+psycopg",
        "single_host": True,
        "explicit_port": True,
        "explicit_database_user_password": True,
        "sslmode": "verify-full",
        "application_name": "ithildin-pis3-evidence",
        "connect_timeout_seconds": 5,
        "ambient_libpq_allowlist": [],
        "dsn_or_credentials_persisted": False,
    }
    if value != expected or type(value.get("connect_timeout_seconds")) is not int:
        _fail("preflight_invalid", "manifest")


def _external_file_reference(
    value: object, *, repo_root: Path, output_root: Path
) -> tuple[Path, str]:
    item = _mapping(value, "external_receipts")
    _require_exact_keys(item, {"path", "sha256"}, "external_receipts")
    path = _absolute_path(item.get("path"), "external_receipts")
    if _inside(path, repo_root) or _inside(path, output_root):
        _fail("receipt_authenticity_failed", "external_receipts")
    try:
        if path.stat().st_mode & 0o222:
            _fail("receipt_authenticity_failed", "external_receipts")
    except OSError:
        _fail("receipt_authenticity_failed", "external_receipts")
    return path, _require_pattern(item.get("sha256"), DIGEST, "external_receipts")


def _decode_canonical_component(raw: str, *, min_bytes: int, max_bytes: int) -> str:
    if not raw:
        _fail("dsn_binding_failed", "dsn_binding")
    output = bytearray()
    index = 0
    while index < len(raw):
        character = raw[index]
        if character in SAFE_RAW_COMPONENT:
            output.extend(character.encode("ascii"))
            index += 1
            continue
        if character != "%" or index + 2 >= len(raw):
            _fail("dsn_binding_failed", "dsn_binding")
        encoded = raw[index + 1 : index + 3]
        if not re.fullmatch(r"[0-9A-F]{2}", encoded):
            _fail("dsn_binding_failed", "dsn_binding")
        byte = int(encoded, 16)
        if chr(byte) in SAFE_RAW_COMPONENT:
            _fail("dsn_binding_failed", "dsn_binding")
        output.append(byte)
        index += 3
    if not min_bytes <= len(output) <= max_bytes:
        _fail("dsn_binding_failed", "dsn_binding")
    try:
        decoded = output.decode("utf-8", errors="strict")
    except UnicodeError:
        _fail("dsn_binding_failed", "dsn_binding")
    if unicodedata.normalize("NFC", decoded) != decoded:
        _fail("dsn_binding_failed", "dsn_binding")
    if _encode_component(decoded) != raw:
        _fail("dsn_binding_failed", "dsn_binding")
    return decoded


def _encode_component(value: str) -> str:
    pieces: list[str] = []
    for byte in value.encode("utf-8"):
        character = chr(byte)
        pieces.append(character if character in SAFE_RAW_COMPONENT else f"%{byte:02X}")
    return "".join(pieces)


def _decode_base64url(value: object, expected_bytes: int, stage: str) -> bytes:
    text = _exact_string(value, stage)
    if "=" in text or not re.fullmatch(r"[A-Za-z0-9_-]+", text):
        _fail(
            "receipt_authenticity_failed" if stage == "external_receipts" else "dsn_binding_failed",
            stage,
        )
    try:
        decoded = base64.urlsafe_b64decode(text + ("=" * (-len(text) % 4)))
    except (ValueError, TypeError):
        _fail(
            "receipt_authenticity_failed" if stage == "external_receipts" else "dsn_binding_failed",
            stage,
        )
    if (
        len(decoded) != expected_bytes
        or base64.urlsafe_b64encode(decoded).rstrip(b"=").decode() != text
    ):
        _fail(
            "receipt_authenticity_failed" if stage == "external_receipts" else "dsn_binding_failed",
            stage,
        )
    return decoded


def _safe_connection_failure_category(exc: BaseException) -> str:
    try:
        text = str(exc).lower()
    except Exception:
        return "target_unavailable"
    for marker, category in FAILURE_MAP:
        if marker in text:
            return category
    return "target_unavailable"


def _safe_import_failure_category(exc: StorageImportError) -> str:
    try:
        text = str(exc).lower()
    except Exception:
        return "semantic_verification_failed"
    if "target must be empty" in text:
        return "target_not_empty"
    if "outer transaction" in text or "autocommit" in text:
        return "transaction_state_lost"
    return "semantic_verification_failed"


def _distribution_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        _fail("preflight_invalid", "manifest")


def _sha256_file(path: Path) -> str:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    except OSError:
        _fail("preflight_invalid", "manifest")
    return "sha256:" + digest.hexdigest()


def _parse_utc_text(value: object, stage: str) -> datetime:
    text = _exact_string(value, stage)
    if not UTC_TEXT.fullmatch(text):
        _fail(
            "receipt_authenticity_failed"
            if stage in {"external_receipts", "discard"}
            else "preflight_invalid",
            stage,
        )
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        _fail("receipt_authenticity_failed", stage)
    return _require_utc(parsed, stage)


def _require_utc(value: datetime, stage: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        _fail("preflight_invalid", stage)
    return value.astimezone(UTC)


def _require_exact_keys(value: Mapping[str, object], keys: set[str], stage: str) -> None:
    if set(value) != keys:
        _fail(
            "receipt_authenticity_failed"
            if stage in {"external_receipts", "discard"}
            else "preflight_invalid",
            stage,
        )


def _require_pattern(value: object, pattern: re.Pattern[str], stage: str) -> str:
    text = _exact_string(value, stage)
    if not pattern.fullmatch(text):
        _fail(
            "receipt_authenticity_failed"
            if stage in {"external_receipts", "discard"}
            else ("dsn_binding_failed" if stage == "dsn_binding" else "preflight_invalid"),
            stage,
        )
    return text


def _exact_string(value: object, stage: str) -> str:
    if type(value) is not str:
        _fail(
            "receipt_authenticity_failed"
            if stage in {"external_receipts", "discard"}
            else ("dsn_binding_failed" if stage == "dsn_binding" else "preflight_invalid"),
            stage,
        )
    return value


def _mapping(value: object, stage: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        _fail(
            "receipt_authenticity_failed"
            if stage in {"external_receipts", "discard"}
            else "preflight_invalid",
            stage,
        )
    if any(type(key) is not str for key in value):
        _fail("preflight_invalid", stage)
    return cast(Mapping[str, object], value)


def _absolute_path(value: object, stage: str) -> Path:
    text = _exact_string(value, stage)
    if any(ord(character) < 32 for character in text):
        _fail("preflight_invalid", stage)
    path = Path(text)
    if not path.is_absolute():
        _fail("preflight_invalid", stage)
    try:
        return path.resolve(strict=True)
    except OSError:
        _fail("preflight_invalid", stage)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _closed_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON member")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> NoReturn:
    raise ValueError(f"non-finite JSON constant is forbidden: {value}")


def _fail(category: str, stage: str) -> NoReturn:
    raise ConnectionEvidenceError(category, stage)


def _render_check() -> JsonObject:
    return {
        "schema_version": "1",
        "valid": True,
        "run_label": RUN_LABEL,
        "execution_authority_active": EXECUTION_AUTHORITY_ACTIVE,
        "execution_authority_reason": EXECUTION_AUTHORITY_REASON,
        "psycopg_imported": "psycopg" in sys.modules,
        "dsn_environment_read": False,
        "binding_key_environment_read": False,
        "engine_constructed": False,
        "database_connection_attempted": False,
        "migration_executed": False,
        "runtime_postgres_allowed": False,
        "production_identity_allowed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.check:
        parser.error("only --check is available before the execution authority gate")
    print(json.dumps(_render_check(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import ast
import base64
import hashlib
import hmac
import importlib.metadata
import io
import json
import platform
import sqlite3
import sys
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from typing import Any, cast

import pytest

pytest.importorskip("sqlalchemy", reason="PIS-003 checks require the non-default pis3 group")

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from ithildin_api import storage_import, storage_schema
from ithildin_api.storage_import import (
    DescriptorImportContext,
    DescriptorImportReceipt,
    PreconnectionRollbackReceipt,
    StorageImportError,
    import_validated_descriptor_snapshot,
    validate_descriptor_snapshot,
)
from ithildin_schemas import canonical_json, sha256_digest
from sqlalchemy import CheckConstraint, DateTime, String
from sqlalchemy.engine import Connection
from sqlalchemy.pool import NullPool

from scripts import (
    production_identity_storage_pis_003_sd_pg_001_connection_evidence as connection_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "a" * 40
SECRET_MARKERS = (b"synthetic-secret-marker",)


class ConnectionEvidenceGateRequired(RuntimeError):
    """The test-only connection contract cannot execute under the offline gate."""


class _RunnerTransaction:
    def __init__(self, connection: _RunnerConnection, *, rollback_error: bool = False) -> None:
        self.connection = connection
        self.is_active = True
        self.rollback_error = rollback_error
        self.rollback_count = 0

    def rollback(self) -> None:
        self.rollback_count += 1
        if self.rollback_error:
            raise RuntimeError("rollback exposed synthetic-secret-marker")
        self.is_active = False
        self.connection.current_transaction = None


class _RunnerConnection:
    def __init__(self, *, rollback_error: bool = False) -> None:
        self.rollback_error = rollback_error
        self.current_transaction: _RunnerTransaction | None = None
        self.last_transaction: _RunnerTransaction | None = None
        self.nested = False
        self.autocommit = False

    def __enter__(self) -> _RunnerConnection:
        return self

    def __exit__(self, *args: object) -> None:
        del args

    def begin(self) -> _RunnerTransaction:
        transaction = _RunnerTransaction(self, rollback_error=self.rollback_error)
        self.current_transaction = transaction
        self.last_transaction = transaction
        return transaction

    def get_transaction(self) -> _RunnerTransaction | None:
        return self.current_transaction

    def in_transaction(self) -> bool:
        return self.current_transaction is not None

    def in_nested_transaction(self) -> bool:
        return self.nested

    def _is_autocommit_isolation(self) -> bool:
        return self.autocommit


class _RunnerEngine:
    def __init__(
        self,
        *,
        connection: _RunnerConnection | None = None,
        connect_error: Exception | None = None,
        dispose_error: bool = False,
    ) -> None:
        self.connection = connection or _RunnerConnection()
        self.connect_error = connect_error
        self.dispose_error = dispose_error
        self.connect_count = 0
        self.dispose_count = 0

    def connect(self) -> _RunnerConnection:
        self.connect_count += 1
        if self.connect_error is not None:
            raise self.connect_error
        return self.connection

    def dispose(self) -> None:
        self.dispose_count += 1
        if self.dispose_error:
            raise RuntimeError("dispose exposed synthetic-secret-marker")


def _deferred_isolated_harness_contract(
    *,
    external_dsn: str,
    rollback_receipt: PreconnectionRollbackReceipt,
    pool_class: type[NullPool] = NullPool,
) -> None:
    """Declare future ownership without consuming the DSN or constructing an engine."""

    raise ConnectionEvidenceGateRequired(
        "separate connection-evidence authority is required before harness execution"
    )


class _FakeResult:
    def __init__(
        self, *, scalar: object = None, rows: list[dict[str, object]] | None = None
    ) -> None:
        self._scalar = scalar
        self._rows = rows

    def scalar_one(self) -> object:
        return self._scalar

    def mappings(self) -> _FakeResult:
        return self

    def all(self) -> list[dict[str, object]]:
        return list(self._rows or [])


class _FakeConnection:
    def __init__(
        self,
        target_rows: list[dict[str, object]],
        *,
        existing: int = 0,
        in_transaction: bool = True,
        nested: bool = False,
        dialect: str = "postgresql",
        autocommit: object = False,
        lose_transaction_after_readback: bool = False,
    ) -> None:
        self.target_rows = target_rows
        self.existing = existing
        self.outer_transaction = in_transaction
        self.nested_transaction = nested
        self.dialect = SimpleNamespace(name=dialect)
        self.autocommit = autocommit
        self.lose_transaction_after_readback = lose_transaction_after_readback
        self.executions: list[tuple[object, object]] = []

    def _is_autocommit_isolation(self) -> bool:
        if type(self.autocommit) is not bool:
            raise AttributeError("autocommit state is unavailable")
        return self.autocommit

    def in_transaction(self) -> bool:
        return self.outer_transaction

    def in_nested_transaction(self) -> bool:
        return self.nested_transaction

    def execute(self, statement: object, parameters: object = None) -> _FakeResult:
        self.executions.append((statement, parameters))
        if len(self.executions) == 1:
            return _FakeResult(scalar=self.existing)
        if len(self.executions) == 2 and parameters is not None:
            return _FakeResult()
        if self.lose_transaction_after_readback:
            self.outer_transaction = False
        return _FakeResult(rows=self.target_rows)


def _payload(workspace_id: str = "default") -> dict[str, object]:
    return {
        "workspace_id": workspace_id,
        "principal_id": "agent:pis3-test",
        "run_id": "run_11111111111111111111111111111111",
        "sandbox_id": "sandbox-pis3",
        "sandbox_profile_id": "profile-pis3",
        "vm_profile_hash": "sha256:" + ("1" * 64),
        "isolation_label": "operator-attested-vm",
        "network_posture_label": "host-only",
        "mount_root_label": "sandbox-workspace",
        "model_client_label": "local-llm",
        "descriptor_source": "operator_supplied",
        "vm_lifecycle_source": "operator_managed",
        "isolation_claim_source": "operator_attested",
        "network_posture_source": "operator_attested",
        "mount_posture_source": "operator_attested",
        "model_client_source": "operator_attested",
        "ithildin_live_inspection_performed": False,
        "ithildin_lifecycle_control_performed": False,
        "mission_control_runtime_authority_used": False,
        "trusted_host_promotion_performed": False,
    }


def _source_row(
    *,
    suffix: str = "1",
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    value = payload or _payload()
    return {
        "descriptor_id": "sdesc_" + (suffix * 32),
        "status": "accepted",
        "created_at": "2026-07-20T12:00:00+00:00",
        "updated_at": "2026-07-20T12:05:00+00:00",
        "payload_hash": sha256_digest(cast(Any, value)),
        "payload_json": canonical_json(cast(Any, value)),
    }


def _target_row(source: Mapping[str, object]) -> dict[str, object]:
    return {
        "descriptor_id": source["descriptor_id"],
        "status": source["status"],
        "created_at": datetime.fromisoformat(cast(str, source["created_at"])),
        "updated_at": datetime.fromisoformat(cast(str, source["updated_at"])),
        "payload_hash": source["payload_hash"],
        "payload_json": json.loads(cast(str, source["payload_json"])),
    }


def _connection(fake: _FakeConnection) -> Connection:
    return cast(Connection, cast(object, fake))


def _context() -> tuple[DescriptorImportContext, PreconnectionRollbackReceipt]:
    rollback = PreconnectionRollbackReceipt(
        candidate_commit=COMMIT,
        target_label="external-quarantined-target",
    )
    return DescriptorImportContext.bind(rollback), rollback


def _alembic_config() -> tuple[Config, io.StringIO]:
    output = io.StringIO()
    config = Config(
        str(ROOT / "db/alembic/alembic.ini"),
        stdout=io.StringIO(),
        output_buffer=output,
    )
    return config, output


def _write_canonical(path: Path, value: object, *, read_only: bool = True) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(connection_evidence.canonical_json_bytes(value))
    if read_only:
        path.chmod(0o444)
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _signed_receipt(
    path: Path,
    *,
    private_key: Ed25519PrivateKey,
    fingerprint: str,
    payload: dict[str, object],
) -> str:
    signature = private_key.sign(
        connection_evidence.RECEIPT_DOMAIN + connection_evidence.canonical_json_bytes(payload)
    )
    return _write_canonical(
        path,
        {
            "payload": payload,
            "signature": {
                "algorithm": "Ed25519",
                "key_id": fingerprint,
                "signature_base64url": _base64url(signature),
            },
        },
    )


def _frozen_sqlite_source(path: Path) -> tuple[str, str]:
    row = _source_row()
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE sandbox_descriptors (
                descriptor_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO sandbox_descriptors (
                descriptor_id, status, created_at, updated_at, payload_hash, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            tuple(
                row[key]
                for key in (
                    "descriptor_id",
                    "status",
                    "created_at",
                    "updated_at",
                    "payload_hash",
                    "payload_json",
                )
            ),
        )
        connection.commit()
    path.chmod(0o444)
    file_digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    records_digest = validate_descriptor_snapshot([row]).records_digest
    return file_digest, records_digest


def _connection_preflight_fixture(
    tmp_path: Path,
) -> tuple[Path, datetime, dict[str, object], str, str, Path, str]:
    now = datetime(2026, 7, 21, 12, 5, tzinfo=UTC)
    issued = "2026-07-21T12:00:00+00:00"
    expires = "2026-07-21T12:10:00+00:00"
    run_id = "pis3run_" + ("1" * 32)
    target_label = "pis3-isolated-target"
    reviewed_commit = "a" * 40
    external = tmp_path / "external"
    output_root = tmp_path / "output"
    output_root.mkdir()
    source_path = tmp_path / "source.sqlite3"
    source_digest, records_digest = _frozen_sqlite_source(source_path)
    tls_root = tmp_path / "tls-root.pem"
    tls_root.write_text("synthetic test root\n", encoding="utf-8")
    tls_root.chmod(0o444)
    tls_digest = "sha256:" + hashlib.sha256(tls_root.read_bytes()).hexdigest()
    binding_key_bytes = b"\x11" * 32
    binding_key = _base64url(binding_key_bytes)
    encoded_tls_root = connection_evidence._encode_component(str(tls_root.resolve()))
    dsn = (
        "postgresql+psycopg://pis3-user:pis3-password@db.example.test:5432/"
        "pis3_evidence?application_name=ithildin-pis3-evidence&connect_timeout=5&"
        f"sslmode=verify-full&sslrootcert={encoded_tls_root}"
    )
    parsed = connection_evidence.parse_canonical_dsn(dsn, approved_tls_root=tls_root)
    binding_payload = parsed.binding_payload(
        run_id=run_id,
        target_label=target_label,
        reviewed_candidate_commit=reviewed_commit,
        sslrootcert_sha256=tls_digest,
    )
    commitment = (
        "hmac-sha256:"
        + hmac.new(
            binding_key_bytes,
            connection_evidence.BINDING_DOMAIN
            + connection_evidence.canonical_json_bytes(binding_payload),
            hashlib.sha256,
        ).hexdigest()
    )

    private_key = Ed25519PrivateKey.generate()
    public_raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    fingerprint = "sha256:" + hashlib.sha256(public_raw).hexdigest()
    issuer_id = "pis3.target.owner"
    trust_path = external / "trust.json"
    trust_digest = _write_canonical(
        trust_path,
        {
            "issuer_id": issuer_id,
            "ed25519_public_key": _base64url(public_raw),
            "public_key_fingerprint": fingerprint,
            "allowed_receipt_types": sorted(connection_evidence.REQUIRED_RECEIPT_TYPES),
            "valid_from": "2026-07-21T11:55:00+00:00",
            "valid_until": "2026-07-21T12:20:00+00:00",
        },
    )
    shared = {
        "schema_version": "1",
        "issuer_id": issuer_id,
        "issued_at": issued,
        "expires_at": expires,
        "run_id": run_id,
        "target_label": target_label,
        "reviewed_candidate_commit": reviewed_commit,
        "source_digest": source_digest,
    }
    rollback_path = external / "rollback.json"
    rollback_digest = _signed_receipt(
        rollback_path,
        private_key=private_key,
        fingerprint=fingerprint,
        payload={
            **shared,
            "receipt_type": "preconnection_rollback_receipt",
            "provenance": "external_target_owner_attestation",
            "assertion": {
                "activation_allowed": False,
                "bound_before_connection": True,
                "rollback_disposition": (
                    "revert_exact_candidate_and_discard_isolated_target_before_activation"
                ),
                "source_unchanged": True,
            },
        },
    )
    owner_path = external / "owner.json"
    owner_digest = _signed_receipt(
        owner_path,
        private_key=private_key,
        fingerprint=fingerprint,
        payload={
            **shared,
            "receipt_type": "target_owner_quarantine_receipt",
            "provenance": "external_target_owner_attestation",
            "assertion": {
                "connection_attempt_budget": 2,
                "dedicated_nonproduction_purpose": "pis3_connection_evidence_only",
                "discard_owner_id": issuer_id,
                "target_binding_hmac_sha256_commitment": commitment,
                "target_empty": True,
                "target_quarantined": True,
            },
        },
    )
    sbom_path = external / "sbom.json"
    sbom_digest = _write_canonical(
        sbom_path,
        {"schema_version": "1", "packages": [], "licenses": []},
    )
    identity = {
        "distribution_source": "synthetic-test-receipt",
        "package_receipt": "sha256:" + ("2" * 64),
        "version": "test-only",
        "patch_provenance": "synthetic-test-only",
        "architecture": "test",
        "loaded_library_realpath": str(tls_root.resolve()),
        "library_sha256": tls_digest,
        "license": "test-only",
    }
    artifact_paths = {
        "db/alembic/env.py",
        "db/alembic/versions/0001_sandbox_descriptors.py",
        "apps/api/src/ithildin_api/storage_import.py",
        "apps/api/src/ithildin_api/storage_schema.py",
        "scripts/production_identity_storage_pis_003_sd_pg_001_connection_evidence.py",
        "pyproject.toml",
        "uv.lock",
        "tool-manifests.lock.json",
    }
    manifest = {
        "schema_version": "1",
        "run_label": connection_evidence.RUN_LABEL,
        "run_id": run_id,
        "target_label": target_label,
        "reviewed_candidate_commit": reviewed_commit,
        "issued_at": issued,
        "expires_at": expires,
        "output_root": str(output_root.resolve()),
        "source": {
            "path": str(source_path.resolve()),
            "file_sha256": source_digest,
            "records_digest": records_digest,
        },
        "implementation_artifact_hashes": {
            path: "sha256:" + hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in sorted(artifact_paths)
        },
        "trust_records": [{"path": str(trust_path), "sha256": trust_digest}],
        "preconnection_receipts": {
            "preconnection_rollback_receipt": {
                "path": str(rollback_path),
                "sha256": rollback_digest,
            },
            "target_owner_quarantine_receipt": {
                "path": str(owner_path),
                "sha256": owner_digest,
            },
        },
        "python_dependencies": {
            "python": platform.python_version(),
            "sqlalchemy": importlib.metadata.version("SQLAlchemy"),
            "alembic": importlib.metadata.version("alembic"),
            "psycopg": importlib.metadata.version("psycopg"),
            "psycopg_impl": "python",
        },
        "native_dependencies": {"libpq": identity, "tls_backend": identity},
        "tls_root": {"path": str(tls_root.resolve()), "sha256": tls_digest},
        "sbom_and_licenses": {"path": str(sbom_path), "sha256": sbom_digest},
        "dsn_posture": {
            "scheme": "postgresql+psycopg",
            "single_host": True,
            "explicit_port": True,
            "explicit_database_user_password": True,
            "sslmode": "verify-full",
            "application_name": "ithildin-pis3-evidence",
            "connect_timeout_seconds": 5,
            "ambient_libpq_allowlist": [],
            "dsn_or_credentials_persisted": False,
        },
        "connection_attempt_budget": 2,
        "negative_scenario": None,
        "secret_scan_marker_commitment": connection_evidence.secret_marker_commitment(
            SECRET_MARKERS
        ),
    }
    manifest_path = tmp_path / "execution-manifest.json"
    _write_canonical(manifest_path, manifest, read_only=False)
    return manifest_path, now, manifest, dsn, binding_key, tls_root, commitment


def test_schema_metadata_is_one_closed_descriptor_aggregate() -> None:
    table = storage_schema.sandbox_descriptors
    assert list(storage_schema.metadata.tables) == ["sandbox_descriptors"]
    assert list(table.c.keys()) == [
        "descriptor_id",
        "status",
        "created_at",
        "updated_at",
        "payload_hash",
        "payload_json",
    ]
    assert isinstance(table.c.descriptor_id.type, String)
    assert table.c.descriptor_id.type.length == 38
    assert isinstance(table.c.status.type, String)
    assert table.c.status.type.length == 8
    assert cast(DateTime, table.c.created_at.type).timezone is True
    assert cast(DateTime, table.c.updated_at.type).timezone is True
    assert isinstance(table.c.payload_hash.type, String)
    assert table.c.payload_hash.type.length == 71
    assert table.c.payload_json.type.__class__.__name__ == "JSONB"
    assert table.primary_key.columns.keys() == ["descriptor_id"]
    constraints = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert constraints == {
        "ck_sandbox_descriptors_descriptor_id": "descriptor_id ~ '^sdesc_[0-9a-f]{32}$'",
        "ck_sandbox_descriptors_status_accepted": "status = 'accepted'",
        "ck_sandbox_descriptors_payload_hash": "payload_hash ~ '^sha256:[0-9a-f]{64}$'",
        "ck_sandbox_descriptors_payload_object": "jsonb_typeof(payload_json) = 'object'",
        "ck_sandbox_descriptors_timestamp_order": "updated_at >= created_at",
    }
    assert [index.name for index in table.indexes] == ["idx_sandbox_descriptors_created_at"]
    index = next(iter(table.indexes))
    assert [column.name for column in index.columns] == ["created_at"]
    assert index.unique is False


def test_direct_postgresql_ddl_is_deterministic_and_connection_free() -> None:
    first = storage_schema.render_postgresql_schema_sql()
    assert first == storage_schema.render_postgresql_schema_sql()
    for fragment in (
        "CREATE TABLE sandbox_descriptors",
        "VARCHAR(38)",
        "TIMESTAMP WITH TIME ZONE",
        "payload_json JSONB NOT NULL",
        "ck_sandbox_descriptors_status_accepted",
        "idx_sandbox_descriptors_created_at",
    ):
        assert fragment in first
    for forbidden in ("postgresql://", "password", "CREATE EXTENSION", "CREATE TYPE"):
        assert forbidden not in first


def test_alembic_has_one_head_and_renders_deterministic_offline_sql() -> None:
    config, first_output = _alembic_config()
    assert ScriptDirectory.from_config(config).get_heads() == ["0001_sandbox_descriptors"]
    command.upgrade(config, "head", sql=True)
    second_config, second_output = _alembic_config()
    command.upgrade(second_config, "head", sql=True)

    assert first_output.getvalue() == second_output.getvalue()
    sql = first_output.getvalue()
    assert "CREATE TABLE sandbox_descriptors" in sql
    assert "payload_json JSONB NOT NULL" in sql
    assert "CREATE INDEX idx_sandbox_descriptors_created_at" in sql
    ini = (ROOT / "db/alembic/alembic.ini").read_text(encoding="utf-8")
    assert "sqlalchemy.url" not in ini
    assert "postgresql://" not in ini


def test_snapshot_validation_is_order_independent_and_canonical() -> None:
    second = _source_row(suffix="2", payload=_payload("second"))
    first = _source_row(suffix="1", payload=_payload("first"))
    ascending = validate_descriptor_snapshot([first, second])
    descending = validate_descriptor_snapshot([second, first])
    assert ascending == descending
    assert ascending.descriptor_ids == (
        cast(str, first["descriptor_id"]),
        cast(str, second["descriptor_id"]),
    )
    assert ascending.records_digest.startswith("sha256:")


def test_importer_round_trip_is_stable_and_receipt_is_secret_free() -> None:
    second = _source_row(suffix="2", payload=_payload("second"))
    first = _source_row(suffix="1", payload=_payload("first"))
    snapshot = validate_descriptor_snapshot([second, first])
    fake = _FakeConnection([_target_row(first), _target_row(second)])
    context, rollback = _context()

    receipt = import_validated_descriptor_snapshot(
        _connection(fake),
        snapshot,
        context,
        rollback,
        verified_at=datetime(2026, 7, 20, 13, tzinfo=UTC),
    )

    assert isinstance(receipt, DescriptorImportReceipt)
    assert receipt.record_count == 2
    assert receipt.descriptor_ids == snapshot.descriptor_ids
    assert receipt.source_records_digest == snapshot.records_digest
    assert receipt.target_records_digest == snapshot.records_digest
    assert receipt.verified_at == "2026-07-20T13:00:00+00:00"
    assert receipt.transaction_owner == "caller"
    assert receipt.transaction_state == "outer_transaction_open"
    assert receipt.target_state == "quarantined_discard_required"
    assert receipt.database_commit_performed is False
    assert receipt.digest().startswith("sha256:")
    document = receipt.document()
    assert document["dsn_included"] is False
    assert document["credentials_included"] is False
    assert document["activation_allowed"] is False
    assert "payload_json" not in document
    assert len(fake.executions) == 3


@pytest.mark.parametrize(
    ("field", "value", "failure"),
    [
        ("status", "pending", "status"),
        ("created_at", "2026-07-20T12:00:00", "timezone-aware"),
        ("created_at", "2026-07-20T13:00:00+01:00", "must be UTC"),
        ("created_at", "2026-07-20T12:00:00Z", "not canonical UTC text"),
        ("payload_hash", "sha256:" + ("0" * 64), "does not match"),
        ("payload_json", "{", "malformed or duplicated"),
        ("payload_json", '{"a":1,"a":2}', "malformed or duplicated"),
        ("payload_json", "[]", "must be an object"),
        ("payload_json", '{"number":NaN}', "malformed or duplicated"),
        ("payload_json", '{"workspace_id":"default"}', "descriptor contract"),
    ],
)
def test_source_validation_rejects_unsafe_rows(
    field: str,
    value: object,
    failure: str,
) -> None:
    row = _source_row()
    row[field] = value
    with pytest.raises(StorageImportError, match=failure):
        validate_descriptor_snapshot([row])


def test_source_validation_rejects_noncanonical_unknown_and_duplicate_rows() -> None:
    missing = _source_row()
    del missing["status"]
    with pytest.raises(StorageImportError, match="fields are not exact"):
        validate_descriptor_snapshot([missing])

    extra = _source_row()
    extra["dsn"] = "must-not-exist"
    with pytest.raises(StorageImportError, match="fields are not exact"):
        validate_descriptor_snapshot([extra])

    unknown_payload = _payload()
    unknown_payload["unknown"] = True
    with pytest.raises(StorageImportError, match="descriptor contract"):
        validate_descriptor_snapshot([_source_row(payload=unknown_payload)])

    row = _source_row()
    row["payload_json"] = json.dumps(json.loads(cast(str, row["payload_json"])), indent=2)
    with pytest.raises(StorageImportError, match="not canonical Ithildin JSON"):
        validate_descriptor_snapshot([row])

    row = _source_row()
    with pytest.raises(StorageImportError, match="duplicate descriptor_id"):
        validate_descriptor_snapshot([row, deepcopy(row)])


@pytest.mark.parametrize(
    (
        "existing",
        "outer",
        "nested",
        "dialect",
        "autocommit",
        "failure",
        "expected_calls",
    ),
    [
        (1, True, False, "postgresql", False, "target must be empty", 1),
        (0, False, False, "postgresql", False, "outer transaction is required", 0),
        (0, True, True, "postgresql", False, "outer transaction is required", 0),
        (0, True, False, "sqlite", False, "PostgreSQL dialect", 0),
        (0, True, False, "postgresql", True, "autocommit isolation", 0),
        (0, True, False, "postgresql", None, "state is unavailable", 0),
    ],
)
def test_importer_requires_empty_postgres_target_and_outer_transaction(
    existing: int,
    outer: bool,
    nested: bool,
    dialect: str,
    autocommit: object,
    failure: str,
    expected_calls: int,
) -> None:
    row = _source_row()
    snapshot = validate_descriptor_snapshot([row])
    fake = _FakeConnection(
        [_target_row(row)],
        existing=existing,
        in_transaction=outer,
        nested=nested,
        dialect=dialect,
        autocommit=autocommit,
    )
    context, rollback = _context()
    with pytest.raises(StorageImportError, match=failure):
        import_validated_descriptor_snapshot(
            _connection(fake),
            snapshot,
            context,
            rollback,
            verified_at=datetime(2026, 7, 20, tzinfo=UTC),
        )
    assert len(fake.executions) == expected_calls


def test_importer_rechecks_outer_transaction_before_issuing_receipt() -> None:
    row = _source_row()
    fake = _FakeConnection(
        [_target_row(row)],
        lose_transaction_after_readback=True,
    )
    context, rollback = _context()

    with pytest.raises(StorageImportError, match="outer transaction is required"):
        import_validated_descriptor_snapshot(
            _connection(fake),
            validate_descriptor_snapshot([row]),
            context,
            rollback,
            verified_at=datetime(2026, 7, 20, tzinfo=UTC),
        )
    assert len(fake.executions) == 3


def test_importer_rejects_target_mismatch_without_repair_or_transaction_control() -> None:
    source = _source_row(suffix="1")
    other = _source_row(suffix="2", payload=_payload("different"))
    fake = _FakeConnection([_target_row(other)])
    context, rollback = _context()
    with pytest.raises(StorageImportError, match="semantic verification failed"):
        import_validated_descriptor_snapshot(
            _connection(fake),
            validate_descriptor_snapshot([source]),
            context,
            rollback,
            verified_at=datetime(2026, 7, 20, tzinfo=UTC),
        )
    assert len(fake.executions) == 3


def test_importer_rejects_unbound_context_and_tampered_snapshot_before_connection() -> None:
    row = _source_row()
    snapshot = validate_descriptor_snapshot([row])
    fake = _FakeConnection([_target_row(row)])
    context, rollback = _context()

    with pytest.raises(StorageImportError, match="does not match the rollback receipt"):
        import_validated_descriptor_snapshot(
            _connection(fake),
            snapshot,
            replace(context, rollback_receipt_digest="sha256:" + ("0" * 64)),
            rollback,
            verified_at=datetime(2026, 7, 20, tzinfo=UTC),
        )
    assert fake.executions == []

    with pytest.raises(StorageImportError, match="snapshot integrity is invalid"):
        import_validated_descriptor_snapshot(
            _connection(fake),
            replace(snapshot, records_digest="sha256:" + ("0" * 64)),
            context,
            rollback,
            verified_at=datetime(2026, 7, 20, tzinfo=UTC),
        )
    assert fake.executions == []


def test_rollback_receipt_is_bound_secret_free_and_digest_stable() -> None:
    receipt = PreconnectionRollbackReceipt(
        candidate_commit=COMMIT,
        target_label="external-quarantined-target",
    )
    receipt.validate()
    assert receipt.digest() == sha256_digest(receipt.document())
    assert receipt.bound_before_connection is True
    assert receipt.source_sqlite_modified is False
    assert receipt.activation_allowed is False
    assert receipt.credentials_included is False

    with pytest.raises(StorageImportError, match="target label is invalid"):
        PreconnectionRollbackReceipt(
            candidate_commit=COMMIT,
            target_label="postgresql://credential-bearing-target",
        ).validate()


def test_connection_harness_contract_refuses_execution_and_driver_is_not_loaded() -> None:
    module_source = Path(storage_import.__file__).read_text(encoding="utf-8")
    tree = ast.parse(module_source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert not any(name == "psycopg" or name.startswith("psycopg.") for name in imports)
    assert not any("sqlalchemy.orm" in name or "sqlalchemy.ext.asyncio" in name for name in imports)
    assert "psycopg" not in sys.modules

    importer = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "import_validated_descriptor_snapshot"
    )
    importer_attributes = {
        node.attr for node in ast.walk(importer) if isinstance(node, ast.Attribute)
    }
    assert (
        not {
            "begin",
            "begin_nested",
            "commit",
            "rollback",
            "connect",
            "dispose",
        }
        & importer_attributes
    )
    assert "create_engine" not in module_source

    test_source = Path(__file__).read_text(encoding="utf-8")
    test_tree = ast.parse(test_source)
    harness_node = next(
        node
        for node in test_tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_deferred_isolated_harness_contract"
    )
    harness_source = ast.get_source_segment(test_source, harness_node)
    assert harness_source is not None
    assert _deferred_isolated_harness_contract.__kwdefaults__ == {"pool_class": NullPool}
    assert "create_engine" not in harness_source

    assert connection_evidence.EXECUTION_AUTHORITY_ACTIVE is False
    assert "psycopg" not in sys.modules
    check = connection_evidence._render_check()
    assert check["valid"] is True
    assert check["execution_authority_active"] is False
    assert check["psycopg_imported"] is False
    assert check["dsn_environment_read"] is False
    assert check["engine_constructed"] is False


def test_connection_harness_refuses_before_manifest_or_environment_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("preflight must not run before the authority gate")

    monkeypatch.setattr(connection_evidence, "validate_execution_preflight", unexpected)
    with pytest.raises(
        connection_evidence.ConnectionEvidenceError,
        match="preflight_invalid at authority_gate",
    ) as captured:
        connection_evidence.execute_connection_evidence(
            Path("must-not-be-read.json"),
            expected_reviewed_commit="a" * 40,
            environment={
                connection_evidence.DSN_ENV: "must-not-be-read",
                connection_evidence.BINDING_KEY_ENV: "must-not-be-read",
            },
        )
    assert captured.value.evidence()["raw_exception_included"] is False
    assert "must-not-be-read" not in str(captured.value)
    assert "psycopg" not in sys.modules


def test_connection_preflight_validates_closed_receipts_and_frozen_source(
    tmp_path: Path,
) -> None:
    manifest_path, now, manifest, _, _, _, _ = _connection_preflight_fixture(tmp_path)
    reviewed_commit = cast(str, manifest["reviewed_candidate_commit"])

    preflight = connection_evidence.validate_execution_preflight(
        manifest_path,
        expected_reviewed_commit=reviewed_commit,
        now=now,
    )

    assert preflight.run_id == manifest["run_id"]
    assert preflight.target_label == manifest["target_label"]
    assert preflight.reviewed_candidate_commit == reviewed_commit
    assert (
        preflight.source.file_digest
        == cast(Mapping[str, object], manifest["source"])["file_sha256"]
    )
    assert (
        preflight.source.records_digest
        == cast(Mapping[str, object], manifest["source"])["records_digest"]
    )
    assert preflight.rollback_receipt.receipt_type == "preconnection_rollback_receipt"
    assert preflight.target_owner_receipt.assertion["target_empty"] is True
    assert preflight.manifest_digest.startswith("sha256:")
    assert "psycopg" not in sys.modules


@pytest.mark.parametrize(
    "mutation",
    [
        "candidate",
        "source_digest",
        "attempt_budget",
        "artifact_hash",
        "ambient_allowlist",
        "extra_key",
    ],
)
def test_connection_preflight_fails_closed_on_manifest_drift(
    tmp_path: Path,
    mutation: str,
) -> None:
    manifest_path, now, manifest, _, _, _, _ = _connection_preflight_fixture(tmp_path)
    changed = deepcopy(manifest)
    if mutation == "candidate":
        changed["reviewed_candidate_commit"] = "b" * 40
    elif mutation == "source_digest":
        cast(dict[str, object], changed["source"])["file_sha256"] = "sha256:" + ("0" * 64)
    elif mutation == "attempt_budget":
        changed["connection_attempt_budget"] = 1
    elif mutation == "artifact_hash":
        artifacts = cast(dict[str, object], changed["implementation_artifact_hashes"])
        artifacts["db/alembic/env.py"] = "sha256:" + ("0" * 64)
    elif mutation == "ambient_allowlist":
        cast(dict[str, object], changed["dsn_posture"])["ambient_libpq_allowlist"] = ["PGUSER"]
    else:
        changed["unexpected"] = True
    _write_canonical(manifest_path, changed, read_only=False)

    with pytest.raises(connection_evidence.ConnectionEvidenceError) as captured:
        connection_evidence.validate_execution_preflight(
            manifest_path,
            expected_reviewed_commit="a" * 40,
            now=now,
        )
    assert captured.value.category in {
        "preflight_invalid",
        "receipt_authenticity_failed",
    }
    assert "psycopg" not in sys.modules


def test_connection_dsn_binding_is_canonical_and_constant_time_checked(
    tmp_path: Path,
) -> None:
    _, _, manifest, dsn, binding_key, tls_root, commitment = _connection_preflight_fixture(tmp_path)
    source = cast(Mapping[str, object], manifest["source"])
    tls = cast(Mapping[str, object], manifest["tls_root"])
    connection_evidence.validate_dsn_target_binding(
        dsn,
        binding_key,
        approved_tls_root=tls_root,
        sslrootcert_sha256=cast(str, tls["sha256"]),
        run_id=cast(str, manifest["run_id"]),
        target_label=cast(str, manifest["target_label"]),
        reviewed_candidate_commit=cast(str, manifest["reviewed_candidate_commit"]),
        expected_commitment=commitment,
    )
    assert cast(str, source["file_sha256"]).startswith("sha256:")

    with pytest.raises(connection_evidence.ConnectionEvidenceError, match="dsn_binding_failed"):
        connection_evidence.validate_dsn_target_binding(
            dsn,
            binding_key,
            approved_tls_root=tls_root,
            sslrootcert_sha256=cast(str, tls["sha256"]),
            run_id=cast(str, manifest["run_id"]),
            target_label=cast(str, manifest["target_label"]),
            reviewed_candidate_commit=cast(str, manifest["reviewed_candidate_commit"]),
            expected_commitment="hmac-sha256:" + ("0" * 64),
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "postgresql+psycopg://pis3-user:pis3-password@DB.example.test:5432/db",
        "postgresql+psycopg://pis3-user:pis3-password@127.0.0.1:5432/db",
        "postgresql+psycopg://pis3-user:pis3-password@db.example.test:05432/db",
        "postgresql+psycopg://pis3-user:pis3-password@db.example.test:5432/a%2fb",
    ],
)
def test_connection_dsn_parser_rejects_noncanonical_authority_and_path(
    tmp_path: Path,
    mutation: str,
) -> None:
    tls_root = tmp_path / "root.pem"
    tls_root.write_text("test\n", encoding="utf-8")
    query = (
        "?application_name=ithildin-pis3-evidence&connect_timeout=5&sslmode=verify-full&"
        f"sslrootcert={connection_evidence._encode_component(str(tls_root.resolve()))}"
    )
    with pytest.raises(connection_evidence.ConnectionEvidenceError):
        connection_evidence.parse_canonical_dsn(mutation + query, approved_tls_root=tls_root)


@pytest.mark.parametrize(
    "component",
    ["pis3%0Auser", "pis3%0Duser", "pis3%7Fuser", "pis3%C2%80user"],
)
@pytest.mark.parametrize("location", ["user", "database"])
def test_connection_dsn_parser_rejects_control_characters(
    tmp_path: Path,
    component: str,
    location: str,
) -> None:
    tls_root = tmp_path / "root.pem"
    tls_root.write_text("test\n", encoding="utf-8")
    user = component if location == "user" else "pis3-user"
    database = component if location == "database" else "pis3_evidence"
    dsn = (
        f"postgresql+psycopg://{user}:pis3-password@db.example.test:5432/{database}"
        "?application_name=ithildin-pis3-evidence&connect_timeout=5&sslmode=verify-full&"
        f"sslrootcert={connection_evidence._encode_component(str(tls_root.resolve()))}"
    )

    with pytest.raises(connection_evidence.ConnectionEvidenceError) as captured:
        connection_evidence.parse_canonical_dsn(dsn, approved_tls_root=tls_root)

    assert captured.value.category == "dsn_binding_failed"


def test_connection_dsn_parser_accepts_canonical_nfc_non_ascii_components(
    tmp_path: Path,
) -> None:
    tls_root = tmp_path / "root.pem"
    tls_root.write_text("test\n", encoding="utf-8")
    dsn = (
        "postgresql+psycopg://pis3-%C3%A9:pis3-password@db.example.test:5432/"
        "evidence-%C3%A9?application_name=ithildin-pis3-evidence&connect_timeout=5&"
        "sslmode=verify-full&"
        f"sslrootcert={connection_evidence._encode_component(str(tls_root.resolve()))}"
    )

    parsed = connection_evidence.parse_canonical_dsn(dsn, approved_tls_root=tls_root)

    assert parsed.user_utf8 == "pis3-é"
    assert parsed.database_utf8 == "evidence-é"


def test_connection_preflight_rejects_every_ambient_libpq_key() -> None:
    for key in (
        "PGHOST",
        "PGPASSWORD",
        "PGSERVICEFILE",
        "PGSSLNEGOTIATION",
        "PGFUTUREUNKNOWN",
    ):
        with pytest.raises(
            connection_evidence.ConnectionEvidenceError,
            match="preflight_invalid at environment",
        ):
            connection_evidence.reject_ambient_libpq_environment({key: "redacted"})
    connection_evidence.reject_ambient_libpq_environment(
        {connection_evidence.DSN_ENV: "not-read-by-this-function"}
    )


@pytest.mark.parametrize("expected", sorted(connection_evidence.NETWORK_NEGATIVE_SCENARIOS))
def test_connection_network_negative_attempt_is_exactly_one_and_category_bound(
    expected: str,
) -> None:
    message = {
        "tls_verification_failed": "certificate verify failed",
        "authentication_or_authorization_failed": "authentication failed",
        "target_unavailable": "connection refused",
    }[expected]
    engine = _RunnerEngine(connect_error=RuntimeError(message))

    with pytest.raises(connection_evidence.ConnectionEvidenceError) as captured:
        connection_evidence._run_network_negative_attempt(engine, expected)

    assert captured.value.category == expected
    assert captured.value.stage == "connection"
    assert engine.connect_count == 1


def test_connection_network_negative_unexpected_success_never_crosses_attempt_budget() -> None:
    engine = _RunnerEngine()

    with pytest.raises(connection_evidence.ConnectionEvidenceError) as captured:
        connection_evidence._run_network_negative_attempt(engine, "tls_verification_failed")

    assert captured.value.category == "connection_attempt_budget_exhausted"
    assert engine.connect_count == 1


def test_connection_runner_pops_binding_secrets_before_driver_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path, now, manifest, dsn, binding_key, _, _ = _connection_preflight_fixture(tmp_path)
    preflight = connection_evidence.validate_execution_preflight(
        manifest_path,
        expected_reviewed_commit=cast(str, manifest["reviewed_candidate_commit"]),
        now=now,
    )
    environment = {
        connection_evidence.PSYCOPG_IMPL_ENV: "python",
        connection_evidence.DSN_ENV: dsn,
        connection_evidence.BINDING_KEY_ENV: binding_key,
    }

    def driver_boundary() -> None:
        assert connection_evidence.DSN_ENV not in environment
        assert connection_evidence.BINDING_KEY_ENV not in environment
        raise connection_evidence.ConnectionEvidenceError(
            "native_library_identity_mismatch", "driver_identity"
        )

    monkeypatch.setattr(connection_evidence, "_load_plain_psycopg_driver", driver_boundary)
    with pytest.raises(connection_evidence.ConnectionEvidenceError) as captured:
        connection_evidence._execute_validated_preflight(
            preflight,
            checked_now=now,
            environment=environment,
        )

    assert captured.value.category == "native_library_identity_mismatch"
    assert connection_evidence.DSN_ENV not in environment
    assert connection_evidence.BINDING_KEY_ENV not in environment


def test_connection_runner_removes_secrets_even_when_binding_fails(
    tmp_path: Path,
) -> None:
    manifest_path, now, manifest, dsn, _, _, _ = _connection_preflight_fixture(tmp_path)
    preflight = connection_evidence.validate_execution_preflight(
        manifest_path,
        expected_reviewed_commit=cast(str, manifest["reviewed_candidate_commit"]),
        now=now,
    )
    environment = {
        connection_evidence.PSYCOPG_IMPL_ENV: "python",
        connection_evidence.DSN_ENV: dsn,
        connection_evidence.BINDING_KEY_ENV: _base64url(b"\x22" * 32),
    }

    with pytest.raises(connection_evidence.ConnectionEvidenceError) as captured:
        connection_evidence._execute_validated_preflight(
            preflight,
            checked_now=now,
            environment=environment,
        )

    assert captured.value.category == "dsn_binding_failed"
    assert connection_evidence.DSN_ENV not in environment
    assert connection_evidence.BINDING_KEY_ENV not in environment


def test_connection_runner_rejects_immutable_environment_mapping(
    tmp_path: Path,
) -> None:
    manifest_path, now, manifest, dsn, binding_key, _, _ = _connection_preflight_fixture(tmp_path)
    preflight = connection_evidence.validate_execution_preflight(
        manifest_path,
        expected_reviewed_commit=cast(str, manifest["reviewed_candidate_commit"]),
        now=now,
    )
    environment = MappingProxyType(
        {
            connection_evidence.PSYCOPG_IMPL_ENV: "python",
            connection_evidence.DSN_ENV: dsn,
            connection_evidence.BINDING_KEY_ENV: binding_key,
        }
    )

    with pytest.raises(connection_evidence.ConnectionEvidenceError) as captured:
        connection_evidence._execute_validated_preflight(
            preflight,
            checked_now=now,
            environment=cast(Any, environment),
        )

    assert captured.value.category == "preflight_invalid"
    assert captured.value.stage == "environment"


def test_connection_attempt_rolls_back_the_exact_original_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path, now, manifest, _, _, _, _ = _connection_preflight_fixture(tmp_path)
    preflight = connection_evidence.validate_execution_preflight(
        manifest_path,
        expected_reviewed_commit=cast(str, manifest["reviewed_candidate_commit"]),
        now=now,
    )
    connection = _RunnerConnection()
    engine = _RunnerEngine(connection=connection)
    receipt = cast(DescriptorImportReceipt, object())
    monkeypatch.setattr(connection_evidence, "_run_online_alembic", lambda _connection: None)
    monkeypatch.setattr(
        connection_evidence,
        "import_validated_descriptor_snapshot",
        lambda *args, **kwargs: receipt,
    )

    observed = connection_evidence._run_migration_import_attempt(engine, preflight, now)

    assert observed is receipt
    assert engine.connect_count == 1
    assert connection.current_transaction is None
    assert connection.last_transaction is not None
    assert connection.last_transaction.rollback_count == 1


def test_connection_attempt_rejects_transaction_identity_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path, now, manifest, _, _, _, _ = _connection_preflight_fixture(tmp_path)
    preflight = connection_evidence.validate_execution_preflight(
        manifest_path,
        expected_reviewed_commit=cast(str, manifest["reviewed_candidate_commit"]),
        now=now,
    )
    connection = _RunnerConnection()
    engine = _RunnerEngine(connection=connection)
    import_called = False

    def replace_transaction(_connection: object) -> None:
        original = connection.current_transaction
        assert original is not None
        original.is_active = False
        connection.current_transaction = _RunnerTransaction(connection)

    def unexpected_import(*args: object, **kwargs: object) -> None:
        nonlocal import_called
        del args, kwargs
        import_called = True

    monkeypatch.setattr(connection_evidence, "_run_online_alembic", replace_transaction)
    monkeypatch.setattr(
        connection_evidence,
        "import_validated_descriptor_snapshot",
        unexpected_import,
    )

    with pytest.raises(connection_evidence.ConnectionEvidenceError) as captured:
        connection_evidence._run_migration_import_attempt(engine, preflight, now)

    assert captured.value.category == "transaction_state_lost"
    assert import_called is False


def test_connection_attempt_redacts_rollback_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path, now, manifest, _, _, _, _ = _connection_preflight_fixture(tmp_path)
    preflight = connection_evidence.validate_execution_preflight(
        manifest_path,
        expected_reviewed_commit=cast(str, manifest["reviewed_candidate_commit"]),
        now=now,
    )
    engine = _RunnerEngine(connection=_RunnerConnection(rollback_error=True))
    monkeypatch.setattr(connection_evidence, "_run_online_alembic", lambda _connection: None)
    monkeypatch.setattr(
        connection_evidence,
        "import_validated_descriptor_snapshot",
        lambda *args, **kwargs: cast(DescriptorImportReceipt, object()),
    )

    with pytest.raises(connection_evidence.ConnectionEvidenceError) as captured:
        connection_evidence._run_migration_import_attempt(engine, preflight, now)

    assert captured.value.category == "transaction_state_lost"
    assert captured.value.stage == "rollback"
    assert "synthetic-secret-marker" not in str(captured.value)
    assert captured.value.__cause__ is None


def test_connection_public_boundary_redacts_engine_and_cleanup_exceptions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path, now, manifest, dsn, binding_key, _, _ = _connection_preflight_fixture(tmp_path)
    environment = {
        connection_evidence.PSYCOPG_IMPL_ENV: "python",
        connection_evidence.DSN_ENV: dsn,
        connection_evidence.BINDING_KEY_ENV: binding_key,
    }
    monkeypatch.setattr(connection_evidence, "EXECUTION_AUTHORITY_ACTIVE", True)
    monkeypatch.setattr(connection_evidence, "_load_plain_psycopg_driver", lambda: object())
    monkeypatch.setattr(connection_evidence, "_validate_loaded_native_identity", lambda *args: None)
    monkeypatch.setattr(
        connection_evidence,
        "create_engine",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("synthetic-secret-marker password=exposed")
        ),
    )

    with pytest.raises(connection_evidence.ConnectionEvidenceError) as captured:
        connection_evidence.execute_connection_evidence(
            manifest_path,
            expected_reviewed_commit=cast(str, manifest["reviewed_candidate_commit"]),
            environment=environment,
            now=now,
        )

    assert captured.value.category == "target_unavailable"
    assert "synthetic-secret-marker" not in str(captured.value)
    assert captured.value.__cause__ is None


def test_connection_negative_failure_survives_dispose_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path, now, manifest, dsn, binding_key, _, _ = _connection_preflight_fixture(tmp_path)
    preflight = replace(
        connection_evidence.validate_execution_preflight(
            manifest_path,
            expected_reviewed_commit=cast(str, manifest["reviewed_candidate_commit"]),
            now=now,
        ),
        negative_scenario="tls_verification_failed",
    )
    environment = {
        connection_evidence.PSYCOPG_IMPL_ENV: "python",
        connection_evidence.DSN_ENV: dsn,
        connection_evidence.BINDING_KEY_ENV: binding_key,
    }
    engine = _RunnerEngine(
        connect_error=RuntimeError("certificate verify failed"),
        dispose_error=True,
    )
    monkeypatch.setattr(connection_evidence, "_load_plain_psycopg_driver", lambda: object())
    monkeypatch.setattr(connection_evidence, "_validate_loaded_native_identity", lambda *args: None)
    monkeypatch.setattr(connection_evidence, "create_engine", lambda *args, **kwargs: engine)

    with pytest.raises(connection_evidence.ConnectionEvidenceError) as captured:
        connection_evidence._execute_validated_preflight(
            preflight,
            checked_now=now,
            environment=environment,
        )

    assert captured.value.category == "tls_verification_failed"
    assert engine.connect_count == 1
    assert engine.dispose_count == 1
    assert "synthetic-secret-marker" not in str(captured.value)


@pytest.mark.parametrize(
    ("declared", "expected"),
    [
        ("migration_failed", "migration_failed"),
        ("semantic_verification_failed", "connection_attempt_budget_exhausted"),
    ],
)
def test_connection_connected_negative_is_one_attempt_and_exactly_category_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    declared: str,
    expected: str,
) -> None:
    manifest_path, now, manifest, dsn, binding_key, _, _ = _connection_preflight_fixture(tmp_path)
    preflight = replace(
        connection_evidence.validate_execution_preflight(
            manifest_path,
            expected_reviewed_commit=cast(str, manifest["reviewed_candidate_commit"]),
            now=now,
        ),
        negative_scenario=declared,
    )
    environment = {
        connection_evidence.PSYCOPG_IMPL_ENV: "python",
        connection_evidence.DSN_ENV: dsn,
        connection_evidence.BINDING_KEY_ENV: binding_key,
    }
    engine = _RunnerEngine()
    monkeypatch.setattr(connection_evidence, "_load_plain_psycopg_driver", lambda: object())
    monkeypatch.setattr(connection_evidence, "_validate_loaded_native_identity", lambda *args: None)
    monkeypatch.setattr(connection_evidence, "create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        connection_evidence,
        "_run_online_alembic",
        lambda _connection: (_ for _ in ()).throw(RuntimeError("migration failed")),
    )

    with pytest.raises(connection_evidence.ConnectionEvidenceError) as captured:
        connection_evidence._execute_validated_preflight(
            preflight,
            checked_now=now,
            environment=environment,
        )

    assert captured.value.category == expected
    assert engine.connect_count == 1
    assert engine.dispose_count == 1


@pytest.mark.parametrize(
    ("negative_scenario", "attempt_kind", "observed_category", "observed_stage"),
    [
        ("tls_verification_failed", "network", "tls_verification_failed", "connection"),
        (
            "semantic_verification_failed",
            "connected",
            "semantic_verification_failed",
            "import",
        ),
        (None, "connected", "migration_failed", "migration"),
    ],
)
def test_connection_source_integrity_overrides_every_engine_run_outcome(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    negative_scenario: str | None,
    attempt_kind: str,
    observed_category: str,
    observed_stage: str,
) -> None:
    manifest_path, now, manifest, dsn, binding_key, _, _ = _connection_preflight_fixture(tmp_path)
    preflight = replace(
        connection_evidence.validate_execution_preflight(
            manifest_path,
            expected_reviewed_commit=cast(str, manifest["reviewed_candidate_commit"]),
            now=now,
        ),
        negative_scenario=negative_scenario,
    )
    environment = {
        connection_evidence.PSYCOPG_IMPL_ENV: "python",
        connection_evidence.DSN_ENV: dsn,
        connection_evidence.BINDING_KEY_ENV: binding_key,
    }

    def mutate_source_and_fail(*args: object) -> None:
        del args
        preflight.source.path.chmod(0o644)
        preflight.source.path.write_bytes(b"mutated synthetic source")
        raise connection_evidence.ConnectionEvidenceError(
            observed_category,
            observed_stage,
        )

    monkeypatch.setattr(connection_evidence, "_load_plain_psycopg_driver", lambda: object())
    monkeypatch.setattr(connection_evidence, "_validate_loaded_native_identity", lambda *args: None)
    monkeypatch.setattr(
        connection_evidence,
        "create_engine",
        lambda *args, **kwargs: _RunnerEngine(),
    )
    helper = (
        "_run_network_negative_attempt"
        if attempt_kind == "network"
        else "_run_migration_import_attempt"
    )
    monkeypatch.setattr(connection_evidence, helper, mutate_source_and_fail)

    with pytest.raises(connection_evidence.ConnectionEvidenceError) as captured:
        connection_evidence._execute_validated_preflight(
            preflight,
            checked_now=now,
            environment=environment,
        )

    assert captured.value.category == "preflight_invalid"
    assert captured.value.stage == "synthetic_source"


def test_connection_source_integrity_overrides_cleanup_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path, now, manifest, dsn, binding_key, _, _ = _connection_preflight_fixture(tmp_path)
    preflight = connection_evidence.validate_execution_preflight(
        manifest_path,
        expected_reviewed_commit=cast(str, manifest["reviewed_candidate_commit"]),
        now=now,
    )

    class SourceMutatingEngine(_RunnerEngine):
        def dispose(self) -> None:
            preflight.source.path.chmod(0o644)
            preflight.source.path.write_bytes(b"mutated during cleanup")
            raise RuntimeError("cleanup exposed synthetic-secret-marker")

    engine = SourceMutatingEngine()
    environment = {
        connection_evidence.PSYCOPG_IMPL_ENV: "python",
        connection_evidence.DSN_ENV: dsn,
        connection_evidence.BINDING_KEY_ENV: binding_key,
    }
    monkeypatch.setattr(connection_evidence, "_load_plain_psycopg_driver", lambda: object())
    monkeypatch.setattr(connection_evidence, "_validate_loaded_native_identity", lambda *args: None)
    monkeypatch.setattr(connection_evidence, "create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        connection_evidence,
        "_run_migration_import_attempt",
        lambda *args: cast(DescriptorImportReceipt, object()),
    )
    monkeypatch.setattr(connection_evidence, "_post_rollback_rows_absent", lambda *args: True)

    with pytest.raises(connection_evidence.ConnectionEvidenceError) as captured:
        connection_evidence._execute_validated_preflight(
            preflight,
            checked_now=now,
            environment=environment,
        )

    assert captured.value.category == "preflight_invalid"
    assert captured.value.stage == "synthetic_source"
    assert "synthetic-secret-marker" not in str(captured.value)


def test_connection_output_scan_rejects_markers_and_connection_strings(
    tmp_path: Path,
) -> None:
    output = tmp_path / "output"
    output.mkdir()
    safe = output / "evidence.json"
    safe.write_text('{"status":"safe"}', encoding="utf-8")
    connection_evidence.scan_output_tree_for_secrets(
        output,
        secret_markers=SECRET_MARKERS,
        expected_commitment=connection_evidence.secret_marker_commitment(SECRET_MARKERS),
    )

    safe.write_text("postgresql://redacted", encoding="utf-8")
    with pytest.raises(
        connection_evidence.ConnectionEvidenceError,
        match="preflight_invalid at secret_scan",
    ):
        connection_evidence.scan_output_tree_for_secrets(
            output,
            secret_markers=SECRET_MARKERS,
            expected_commitment=connection_evidence.secret_marker_commitment(SECRET_MARKERS),
        )


def test_connection_output_scan_binds_markers_and_rejects_symlinks(
    tmp_path: Path,
) -> None:
    output = tmp_path / "output"
    output.mkdir()
    safe = output / "evidence.json"
    safe.write_text('{"status":"safe"}', encoding="utf-8")
    expected = connection_evidence.secret_marker_commitment(SECRET_MARKERS)

    with pytest.raises(connection_evidence.ConnectionEvidenceError):
        connection_evidence.scan_output_tree_for_secrets(
            output,
            secret_markers=(b"substituted-secret-marker",),
            expected_commitment=expected,
        )
    with pytest.raises(connection_evidence.ConnectionEvidenceError):
        connection_evidence.secret_marker_commitment(())
    with pytest.raises(connection_evidence.ConnectionEvidenceError):
        connection_evidence.secret_marker_commitment((SECRET_MARKERS[0], SECRET_MARKERS[0]))

    (output / "linked-evidence").symlink_to(safe)
    with pytest.raises(
        connection_evidence.ConnectionEvidenceError,
        match="preflight_invalid at secret_scan",
    ):
        connection_evidence.scan_output_tree_for_secrets(
            output,
            secret_markers=SECRET_MARKERS,
            expected_commitment=expected,
        )


def test_connection_output_scan_rejects_nested_markers_and_nonregular_files(
    tmp_path: Path,
) -> None:
    output = tmp_path / "output"
    nested = output / "nested"
    nested.mkdir(parents=True)
    expected = connection_evidence.secret_marker_commitment(SECRET_MARKERS)
    artifact = nested / "evidence.json"
    artifact.write_bytes(b'{"status":"safe","marker":"' + SECRET_MARKERS[0] + b'"}')

    with pytest.raises(connection_evidence.ConnectionEvidenceError):
        connection_evidence.scan_output_tree_for_secrets(
            output,
            secret_markers=SECRET_MARKERS,
            expected_commitment=expected,
        )

    artifact.unlink()
    fifo = nested / "evidence.fifo"
    try:
        import os

        os.mkfifo(fifo)
    except (AttributeError, OSError):
        pytest.skip("FIFO creation is unavailable on this platform")
    with pytest.raises(connection_evidence.ConnectionEvidenceError):
        connection_evidence.scan_output_tree_for_secrets(
            output,
            secret_markers=SECRET_MARKERS,
            expected_commitment=expected,
        )


def test_connection_native_tls_identity_rejects_same_basename_different_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_dir = tmp_path / "expected"
    actual_dir = tmp_path / "actual"
    expected_dir.mkdir()
    actual_dir.mkdir()
    libpq = tmp_path / "libpq.test"
    expected_tls = expected_dir / "libssl.test"
    actual_tls = actual_dir / "libssl.test"
    for path, content in (
        (libpq, b"libpq"),
        (expected_tls, b"expected tls"),
        (actual_tls, b"actual tls"),
    ):
        path.write_bytes(content)
    native = {
        "libpq": {
            "loaded_library_realpath": str(libpq.resolve()),
            "library_sha256": "sha256:" + hashlib.sha256(libpq.read_bytes()).hexdigest(),
            "version": "libpq-test",
            "architecture": platform.machine(),
        },
        "tls_backend": {
            "loaded_library_realpath": str(expected_tls.resolve()),
            "library_sha256": (
                "sha256:" + hashlib.sha256(expected_tls.read_bytes()).hexdigest()
            ),
            "version": "tls-test",
            "architecture": platform.machine(),
        },
    }
    modules = {
        "psycopg.pq": SimpleNamespace(version=lambda: "libpq-test"),
        "psycopg.pq._pq_ctypes": SimpleNamespace(libname=str(libpq)),
    }
    symbol_lookups: list[tuple[Path, str]] = []

    def loaded_symbol_owner(path: Path, symbol: str) -> Path:
        symbol_lookups.append((path, symbol))
        if symbol == "PQlibVersion":
            return libpq.resolve()
        if symbol == "SSL_CTX_new":
            return actual_tls.resolve()
        raise AssertionError(f"unexpected native symbol lookup: {symbol}")

    monkeypatch.setattr(importlib, "import_module", lambda name: modules[name])
    monkeypatch.setattr(
        connection_evidence,
        "_loaded_symbol_library_path",
        loaded_symbol_owner,
    )

    with pytest.raises(connection_evidence.ConnectionEvidenceError) as captured:
        connection_evidence._validate_loaded_native_identity(
            cast(Any, object()),
            {"native_dependencies": native},
        )

    assert captured.value.category == "native_library_identity_mismatch"
    assert symbol_lookups == [
        (libpq.resolve(), "PQlibVersion"),
        (libpq.resolve(), "SSL_CTX_new"),
    ]
    source = Path(connection_evidence.__file__).read_text(encoding="utf-8")
    assert "dependency.name in" not in source
    assert 'subprocess.run(["otool"' not in source
    assert '_loaded_symbol_library_path(libpq_path, "OpenSSL_version")' not in source


@pytest.mark.parametrize(
    ("failure_stage", "expected_stage"),
    [("external_receipts", "external_receipts"), ("discard", "discard")],
)
def test_connection_malformed_receipt_json_uses_contextual_failure_stage(
    tmp_path: Path,
    failure_stage: str,
    expected_stage: str,
) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_text('{"payload":', encoding="utf-8")

    with pytest.raises(connection_evidence.ConnectionEvidenceError) as captured:
        connection_evidence.verify_external_receipt(
            (malformed, "sha256:" + ("0" * 64)),
            trust_records={},
            verification_time=datetime(2026, 7, 21, 12, 7, tzinfo=UTC),
            failure_stage=failure_stage,
        )

    assert captured.value.category == "receipt_authenticity_failed"
    assert captured.value.stage == expected_stage


def test_connection_malformed_trust_json_uses_external_receipt_failure_stage(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    output_root = tmp_path / "output"
    external_root = tmp_path / "external"
    repo_root.mkdir()
    output_root.mkdir()
    external_root.mkdir()
    malformed = external_root / "trust.json"
    malformed.write_text('{"issuer_id":', encoding="utf-8")
    malformed.chmod(0o444)
    reference = {
        "path": str(malformed.resolve()),
        "sha256": "sha256:" + hashlib.sha256(malformed.read_bytes()).hexdigest(),
    }

    with pytest.raises(connection_evidence.ConnectionEvidenceError) as captured:
        connection_evidence._load_trust_records(
            [reference],
            repo_root=repo_root,
            output_root=output_root,
            now=datetime(2026, 7, 21, 12, 7, tzinfo=UTC),
        )

    assert captured.value.category == "receipt_authenticity_failed"
    assert captured.value.stage == "external_receipts"


def test_connection_missing_manifest_uses_closed_manifest_failure(
    tmp_path: Path,
) -> None:
    with pytest.raises(connection_evidence.ConnectionEvidenceError) as captured:
        connection_evidence.validate_execution_preflight(
            tmp_path / "missing.json",
            expected_reviewed_commit="a" * 40,
        )

    assert captured.value.category == "preflight_invalid"
    assert captured.value.stage == "manifest"
    assert captured.value.__cause__ is None


def test_connection_discard_finalizer_binds_named_discard_owner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path, now, manifest, _, _, _, _ = _connection_preflight_fixture(tmp_path)
    preflight = connection_evidence.validate_execution_preflight(
        manifest_path,
        expected_reviewed_commit=cast(str, manifest["reviewed_candidate_commit"]),
        now=now,
    )
    last_closed = datetime(2026, 7, 21, 12, 6, tzinfo=UTC)
    assertion = {
        "activation_never_occurred": True,
        "last_connection_closed_at": "2026-07-21T12:06:00+00:00",
        "target_discarded": True,
        "target_discarded_at": "2026-07-21T12:06:30+00:00",
    }

    def receipt(issuer_id: str) -> connection_evidence.VerifiedReceipt:
        return connection_evidence.VerifiedReceipt(
            receipt_type="target_discard_receipt",
            issuer_id=issuer_id,
            run_id=preflight.run_id,
            target_label=preflight.target_label,
            reviewed_candidate_commit=preflight.reviewed_candidate_commit,
            source_digest=preflight.source.file_digest,
            issued_at=datetime(2026, 7, 21, 12, 7, tzinfo=UTC),
            expires_at=datetime(2026, 7, 21, 12, 10, tzinfo=UTC),
            assertion=assertion,
            file_sha256="sha256:" + ("4" * 64),
        )

    monkeypatch.setattr(
        connection_evidence,
        "verify_external_receipt",
        lambda *args, **kwargs: receipt("otherwise.trusted.issuer"),
    )
    with pytest.raises(
        connection_evidence.ConnectionEvidenceError,
        match="receipt_authenticity_failed at discard",
    ):
        connection_evidence.finalize_discard_receipt(
            preflight,
            (tmp_path / "unused", "sha256:" + ("4" * 64)),
            last_connection_closed_at=last_closed,
            verification_time=datetime(2026, 7, 21, 12, 7, tzinfo=UTC),
            secret_markers=SECRET_MARKERS,
        )

    named_owner = cast(str, preflight.target_owner_receipt.assertion["discard_owner_id"])
    monkeypatch.setattr(
        connection_evidence,
        "verify_external_receipt",
        lambda *args, **kwargs: receipt(named_owner),
    )
    verified = connection_evidence.finalize_discard_receipt(
        preflight,
        (tmp_path / "unused", "sha256:" + ("4" * 64)),
        last_connection_closed_at=last_closed,
        verification_time=datetime(2026, 7, 21, 12, 7, tzinfo=UTC),
        secret_markers=SECRET_MARKERS,
    )
    assert verified.issuer_id == named_owner

    preflight.source.path.chmod(0o644)
    preflight.source.path.write_bytes(b"mutated after last connection")
    with pytest.raises(connection_evidence.ConnectionEvidenceError) as captured:
        connection_evidence.finalize_discard_receipt(
            preflight,
            (tmp_path / "unused", "sha256:" + ("4" * 64)),
            last_connection_closed_at=last_closed,
            verification_time=datetime(2026, 7, 21, 12, 7, tzinfo=UTC),
            secret_markers=SECRET_MARKERS,
        )
    assert captured.value.category == "preflight_invalid"
    assert captured.value.stage == "synthetic_source"


def test_offline_modules_are_not_imported_by_runtime_or_startup() -> None:
    protected = [
        ROOT / "apps/api/src/ithildin_api/app.py",
        ROOT / "apps/api/src/ithildin_api/config.py",
        ROOT / "apps/api/src/ithildin_api/sandbox_descriptors.py",
        ROOT / "apps/api/src/ithildin_api/storage.py",
    ]
    for path in protected:
        source = path.read_text(encoding="utf-8")
        assert "storage_schema" not in source
        assert "storage_import" not in source
    env_source = (ROOT / "db/alembic/env.py").read_text(encoding="utf-8")
    assert "create_engine" not in env_source
    assert "engine_from_config" not in env_source
    assert "psycopg" not in env_source
    assert 'config.attributes.get("connection")' in env_source
    assert "caller-owned non-nested transaction" in env_source
    lock = json.loads((ROOT / "tool-manifests.lock.json").read_text(encoding="utf-8"))
    assert len(lock["manifests"]) == 24

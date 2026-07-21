from __future__ import annotations

import ast
import io
import json
import sys
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

pytest.importorskip("sqlalchemy", reason="PIS-003 checks require the non-default pis3 group")

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
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

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "a" * 40


class ConnectionEvidenceGateRequired(RuntimeError):
    """The test-only connection contract cannot execute under the offline gate."""


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
    ) -> None:
        self.target_rows = target_rows
        self.existing = existing
        self.outer_transaction = in_transaction
        self.nested_transaction = nested
        self.dialect = SimpleNamespace(name=dialect)
        self.executions: list[tuple[object, object]] = []

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
    ("existing", "outer", "nested", "dialect", "failure", "expected_calls"),
    [
        (1, True, False, "postgresql", "target must be empty", 1),
        (0, False, False, "postgresql", "outer transaction is required", 0),
        (0, True, True, "postgresql", "outer transaction is required", 0),
        (0, True, False, "sqlite", "PostgreSQL dialect", 0),
    ],
)
def test_importer_requires_empty_postgres_target_and_outer_transaction(
    existing: int,
    outer: bool,
    nested: bool,
    dialect: str,
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
    assert "connection-evidence gate is required" in env_source
    lock = json.loads((ROOT / "tool-manifests.lock.json").read_text(encoding="utf-8"))
    assert len(lock["manifests"]) == 24

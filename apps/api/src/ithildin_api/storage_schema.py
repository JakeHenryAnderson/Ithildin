"""Offline-only PostgreSQL schema metadata for the PIS-003 descriptor candidate."""

from __future__ import annotations

from sqlalchemy import CheckConstraint, Column, DateTime, Index, MetaData, String, Table
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

SCHEMA_EPOCH = "pis_003_sd_pg_001"
STATUS_ACCEPTED = "accepted"

metadata = MetaData()

sandbox_descriptors = Table(
    "sandbox_descriptors",
    metadata,
    Column("descriptor_id", String(38), primary_key=True, nullable=False),
    Column("status", String(8), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("payload_hash", String(71), nullable=False),
    Column("payload_json", postgresql.JSONB, nullable=False),
    CheckConstraint(
        "descriptor_id ~ '^sdesc_[0-9a-f]{32}$'",
        name="ck_sandbox_descriptors_descriptor_id",
    ),
    CheckConstraint(
        "status = 'accepted'",
        name="ck_sandbox_descriptors_status_accepted",
    ),
    CheckConstraint(
        "payload_hash ~ '^sha256:[0-9a-f]{64}$'",
        name="ck_sandbox_descriptors_payload_hash",
    ),
    CheckConstraint(
        "jsonb_typeof(payload_json) = 'object'",
        name="ck_sandbox_descriptors_payload_object",
    ),
    CheckConstraint(
        "updated_at >= created_at",
        name="ck_sandbox_descriptors_timestamp_order",
    ),
)

created_at_index = Index(
    "idx_sandbox_descriptors_created_at",
    sandbox_descriptors.c.created_at,
)


def render_postgresql_schema_sql() -> str:
    """Render deterministic PostgreSQL DDL without a URL, driver, or connection."""

    dialect = postgresql.dialect()  # type: ignore[no-untyped-call]
    statements = [
        str(CreateTable(sandbox_descriptors).compile(dialect=dialect)).strip(),
        str(CreateIndex(created_at_index).compile(dialect=dialect)).strip(),
    ]
    return ";\n\n".join(statement.rstrip(";") for statement in statements) + ";\n"

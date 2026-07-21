"""Create the isolated sandbox descriptor candidate schema.

Revision ID: 0001_sandbox_descriptors
Revises: None
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_sandbox_descriptors"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sandbox_descriptors",
        sa.Column("descriptor_id", sa.String(length=38), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_hash", sa.String(length=71), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint(
            "descriptor_id ~ '^sdesc_[0-9a-f]{32}$'",
            name="ck_sandbox_descriptors_descriptor_id",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(payload_json) = 'object'",
            name="ck_sandbox_descriptors_payload_object",
        ),
        sa.CheckConstraint(
            "payload_hash ~ '^sha256:[0-9a-f]{64}$'",
            name="ck_sandbox_descriptors_payload_hash",
        ),
        sa.CheckConstraint(
            "status = 'accepted'",
            name="ck_sandbox_descriptors_status_accepted",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_sandbox_descriptors_timestamp_order",
        ),
        sa.PrimaryKeyConstraint("descriptor_id"),
    )
    op.create_index(
        "idx_sandbox_descriptors_created_at",
        "sandbox_descriptors",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    raise RuntimeError("downgrade is not authorized; discard the isolated target")

"""Offline-first Alembic environment for the isolated PIS-003 candidate."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from ithildin_api.storage_schema import metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = metadata


def run_migrations_offline() -> None:
    """Render PostgreSQL SQL without a URL, driver, or connection."""

    context.configure(
        dialect_name="postgresql",
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        transaction_per_migration=False,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Fail closed until a separate connection-evidence gate changes this artifact."""

    raise RuntimeError("PIS-003 connection-evidence gate is required for online migration")


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

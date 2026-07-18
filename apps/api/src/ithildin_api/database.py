"""Coordinated SQLite initialization for the Ithildin API service."""

from __future__ import annotations

from pathlib import Path

from ithildin_api.trusted_host_promotion_v2_migration import (
    DATABASE_SCHEMA_VERSION,
    initialize_or_migrate_database,
)

SCHEMA_VERSION = DATABASE_SCHEMA_VERSION


def initialize_database(db_path: Path) -> None:
    initialize_or_migrate_database(db_path)

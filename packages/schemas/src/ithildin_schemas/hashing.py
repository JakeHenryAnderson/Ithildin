"""Deterministic JSON serialization and digest helpers."""

from __future__ import annotations

import hashlib
import json

from ithildin_schemas.types import JsonValue


def canonical_json(value: JsonValue) -> str:
    """Serialize a JSON-compatible value with deterministic key ordering."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_digest(value: JsonValue) -> str:
    """Return a prefixed SHA-256 digest for a JSON-compatible value."""
    digest = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"

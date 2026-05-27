"""Verification for local OPA bundle/source evidence."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ithildin_schemas import JsonObject, JsonValue, sha256_digest

BUNDLE_MANIFEST_VERSION = 1
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class OpaBundleError(RuntimeError):
    """Raised when OPA bundle/source evidence cannot be verified."""


@dataclass(frozen=True)
class OpaBundleSource:
    path: str
    source_hash: str

    def as_dict(self) -> JsonObject:
        return {"path": self.path, "source_hash": self.source_hash}


@dataclass(frozen=True)
class OpaBundleEvidence:
    bundle_version: str
    entrypoint: str
    bundle_hash: str
    sources: tuple[OpaBundleSource, ...]
    manifest_path: Path

    def as_status(self) -> JsonObject:
        source_hashes: list[JsonValue] = [source.as_dict() for source in self.sources]
        return {
            "bundle_version": self.bundle_version,
            "bundle_entrypoint": self.entrypoint,
            "bundle_hash": self.bundle_hash,
            "bundle_verified": True,
            "bundle_sources": source_hashes,
        }


def verify_opa_bundle_manifest(manifest_path: Path) -> OpaBundleEvidence:
    payload = _read_manifest(manifest_path)
    bundle_version = _string(payload, "bundle_version")
    entrypoint = _string(payload, "entrypoint")
    locked_bundle_hash = _string(payload, "bundle_hash")
    if not SHA256_RE.match(locked_bundle_hash):
        raise OpaBundleError("OPA bundle manifest has invalid bundle hash")

    raw_sources = payload.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise OpaBundleError("OPA bundle manifest must contain sources")

    sources: list[OpaBundleSource] = []
    manifest_root = manifest_path.parent.resolve(strict=False)
    for raw_source in raw_sources:
        if not isinstance(raw_source, dict):
            raise OpaBundleError("OPA bundle source must be an object")
        source = _json_object(raw_source)
        source_path = _string(source, "path")
        expected_hash = _string(source, "source_hash")
        if not SHA256_RE.match(expected_hash):
            raise OpaBundleError(f"OPA bundle source has invalid hash: {source_path}")
        resolved_source = _safe_source_path(manifest_root=manifest_root, raw_path=source_path)
        actual_hash = _file_sha256(resolved_source)
        if actual_hash != expected_hash:
            raise OpaBundleError(f"OPA bundle source hash mismatch: {source_path}")
        sources.append(OpaBundleSource(path=source_path, source_hash=actual_hash))

    computed_bundle_hash = opa_bundle_hash(
        bundle_version=bundle_version,
        entrypoint=entrypoint,
        sources=tuple(sources),
    )
    if computed_bundle_hash != locked_bundle_hash:
        raise OpaBundleError("OPA bundle hash mismatch")

    return OpaBundleEvidence(
        bundle_version=bundle_version,
        entrypoint=entrypoint,
        bundle_hash=computed_bundle_hash,
        sources=tuple(sources),
        manifest_path=manifest_path,
    )


def opa_bundle_hash(
    *,
    bundle_version: str,
    entrypoint: str,
    sources: tuple[OpaBundleSource, ...],
) -> str:
    return sha256_digest(
        {
            "bundle_version": bundle_version,
            "entrypoint": entrypoint,
            "sources": [source.as_dict() for source in sorted(sources, key=lambda item: item.path)],
        }
    )


def _read_manifest(manifest_path: Path) -> JsonObject:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise OpaBundleError(f"OPA bundle manifest not found: {manifest_path}") from exc
    except json.JSONDecodeError as exc:
        raise OpaBundleError(f"OPA bundle manifest is invalid JSON: {manifest_path}") from exc
    if not isinstance(payload, dict):
        raise OpaBundleError("OPA bundle manifest must be a JSON object")
    manifest = _json_object(payload)
    if manifest.get("bundle_manifest_version") != BUNDLE_MANIFEST_VERSION:
        raise OpaBundleError("unsupported OPA bundle manifest version")
    return manifest


def _json_object(value: dict[Any, Any]) -> JsonObject:
    result: JsonObject = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise OpaBundleError("OPA bundle manifest keys must be strings")
        result[key] = item
    return result


def _string(value: JsonObject, key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise OpaBundleError(f"OPA bundle manifest missing {key}")
    return item


def _safe_source_path(*, manifest_root: Path, raw_path: str) -> Path:
    requested = Path(raw_path)
    if requested.is_absolute() or ".." in requested.parts:
        raise OpaBundleError("OPA bundle source paths must stay under the bundle directory")
    resolved = manifest_root.joinpath(requested).resolve(strict=False)
    try:
        resolved.relative_to(manifest_root)
    except ValueError as exc:
        raise OpaBundleError("OPA bundle source path escapes the bundle directory") from exc
    return resolved


def _file_sha256(path: Path) -> str:
    try:
        data = path.read_bytes()
    except FileNotFoundError as exc:
        raise OpaBundleError(f"OPA bundle source not found: {path.name}") from exc
    return "sha256:" + hashlib.sha256(data).hexdigest()

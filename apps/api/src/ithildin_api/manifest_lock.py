"""Deterministic lockfile support for trusted tool manifests."""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from ithildin_schemas import JsonObject, JsonValue, canonical_json, sha256_digest

LOCKFILE_VERSION = 1
SIGNATURE_ALGORITHM = "ed25519"
SIGNATURE_FORMAT_VERSION = "1"
SIGNATURE_TYPE = "ithildin.manifest_lock.signature"
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class ManifestLockError(RuntimeError):
    """Raised when manifest lock verification fails closed."""


class ManifestLockSignatureError(ManifestLockError):
    """Raised when manifest lock signature verification fails closed."""


@dataclass(frozen=True)
class ManifestLockRecord:
    path: Path
    name: str
    version: str
    manifest_hash: str


@dataclass(frozen=True)
class ManifestLockSignatureVerificationResult:
    valid: bool
    lock_sha256: Optional[str]
    key_id: Optional[str]
    failure: Optional[str] = None

    def as_dict(self) -> JsonObject:
        return {
            "valid": self.valid,
            "lock_sha256": self.lock_sha256,
            "key_id": self.key_id,
            "failure": self.failure,
        }


def write_manifest_lock(
    *,
    manifest_dir: Path,
    lock_path: Path,
    records: list[ManifestLockRecord],
) -> None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    payload = manifest_lock_payload(
        manifest_dir=manifest_dir,
        lock_path=lock_path,
        records=records,
    )
    lock_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def manifest_lock_payload(
    *,
    manifest_dir: Path,
    lock_path: Path,
    records: list[ManifestLockRecord],
) -> JsonObject:
    lock_root = lock_path.parent.resolve(strict=False)
    entries: list[JsonValue] = []
    for record in sorted(records, key=lambda item: _relative_lock_path(lock_root, item.path)):
        entries.append(
            {
                "path": _relative_lock_path(lock_root, record.path),
                "name": record.name,
                "version": record.version,
                "manifest_hash": record.manifest_hash,
            }
        )
    return {
        "lockfile_version": LOCKFILE_VERSION,
        "manifest_dir": _relative_lock_path(lock_root, manifest_dir),
        "manifests": entries,
    }


def generate_manifest_lock_signing_keypair(
    *,
    private_key_path: Path,
    public_key_path: Path,
    overwrite: bool = False,
) -> str:
    """Generate a local Ed25519 manifest-lock signing keypair."""
    if not overwrite and (private_key_path.exists() or public_key_path.exists()):
        raise ManifestLockSignatureError("manifest lock signing key already exists")

    private_key_path.parent.mkdir(parents=True, exist_ok=True)
    public_key_path.parent.mkdir(parents=True, exist_ok=True)
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    private_key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    private_key_path.chmod(0o600)
    public_key_path.write_bytes(
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    public_key_path.chmod(0o644)
    return manifest_lock_public_key_id(public_key)


def write_manifest_lock_signature(
    *,
    lock_path: Path,
    signature_path: Path,
    private_key_path: Path,
    public_key_path: Path,
) -> JsonObject:
    """Write a signature bundle for the current manifest lock."""
    signature_path.parent.mkdir(parents=True, exist_ok=True)
    bundle = manifest_lock_signature_bundle(
        lock_path=lock_path,
        private_key_path=private_key_path,
        public_key_path=public_key_path,
    )
    signature_path.write_text(
        json.dumps(bundle, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return bundle


def manifest_lock_signature_bundle(
    *,
    lock_path: Path,
    private_key_path: Path,
    public_key_path: Path,
) -> JsonObject:
    """Return a signed JSON bundle for a manifest lock."""
    private_key = _load_private_key(private_key_path)
    configured_public_key = _load_public_key(public_key_path)
    derived_public_key = private_key.public_key()
    if _public_key_raw(configured_public_key) != _public_key_raw(derived_public_key):
        raise ManifestLockSignatureError("manifest lock signing keys do not match")

    lock_sha256 = sha256_digest(_read_lock(lock_path))
    public_key_b64 = _public_key_b64(derived_public_key)
    key_id = manifest_lock_public_key_id(derived_public_key)
    signature_metadata: JsonObject = {
        "algorithm": SIGNATURE_ALGORITHM,
        "key_id": key_id,
        "public_key": public_key_b64,
        "created_at": datetime.now(UTC).isoformat(),
    }
    payload = _signature_payload(
        lock_path=lock_path,
        lock_sha256=lock_sha256,
        signature_metadata=signature_metadata,
    )
    signature = private_key.sign(canonical_json(payload).encode("utf-8"))
    return {
        "signature_type": SIGNATURE_TYPE,
        "format_version": SIGNATURE_FORMAT_VERSION,
        "lock_path": lock_path.as_posix(),
        "lock_sha256": lock_sha256,
        "signature": {
            **signature_metadata,
            "signature": base64.b64encode(signature).decode("ascii"),
        },
    }


def verify_manifest_lock_signature(
    *,
    lock_path: Path,
    signature_path: Path,
    public_key_path: Optional[Path] = None,
) -> ManifestLockSignatureVerificationResult:
    """Verify a signed manifest lock bundle."""
    try:
        bundle = _read_signature(signature_path)
        _require_string(bundle.get("signature_type"), "signature_type", SIGNATURE_TYPE)
        _require_string(bundle.get("format_version"), "format_version", SIGNATURE_FORMAT_VERSION)
        signed_lock_path = _require_string(bundle.get("lock_path"), "lock_path")
        if signed_lock_path != lock_path.as_posix():
            raise ManifestLockSignatureError(
                "manifest lock signature targets a different lock path"
            )
        lock_sha256 = _require_hash(bundle.get("lock_sha256"), "lock_sha256")
        signature = _object(bundle.get("signature"), "signature")
        algorithm = _require_string(signature.get("algorithm"), "signature.algorithm")
        if algorithm != SIGNATURE_ALGORITHM:
            raise ManifestLockSignatureError("unsupported manifest lock signature algorithm")
        public_key_b64 = _require_string(signature.get("public_key"), "signature.public_key")
        key_id = _require_hash(signature.get("key_id"), "signature.key_id")
        signature_b64 = _require_string(signature.get("signature"), "signature.signature")

        if sha256_digest(_read_lock(lock_path)) != lock_sha256:
            raise ManifestLockSignatureError("manifest lock signature digest mismatch")

        embedded_public_key = _public_key_from_b64(public_key_b64)
        if manifest_lock_public_key_id(embedded_public_key) != key_id:
            raise ManifestLockSignatureError("manifest lock signature key id mismatch")
        if public_key_path is not None:
            trusted_public_key = _load_public_key(public_key_path)
            if _public_key_raw(trusted_public_key) != _public_key_raw(embedded_public_key):
                raise ManifestLockSignatureError("manifest lock signature public key mismatch")

        signature_metadata: JsonObject = {
            "algorithm": algorithm,
            "key_id": key_id,
            "public_key": public_key_b64,
            "created_at": _require_string(signature.get("created_at"), "signature.created_at"),
        }
        payload = _signature_payload(
            lock_path=lock_path,
            lock_sha256=lock_sha256,
            signature_metadata=signature_metadata,
        )
        embedded_public_key.verify(
            base64.b64decode(signature_b64, validate=True),
            canonical_json(payload).encode("utf-8"),
        )
    except (ManifestLockSignatureError, InvalidSignature, ValueError) as exc:
        return ManifestLockSignatureVerificationResult(
            valid=False,
            lock_sha256=_optional_lock_sha(signature_path),
            key_id=_optional_key_id(signature_path),
            failure=(
                "manifest lock signature verification failed"
                if isinstance(exc, InvalidSignature)
                else str(exc)
            ),
        )

    return ManifestLockSignatureVerificationResult(
        valid=True,
        lock_sha256=lock_sha256,
        key_id=key_id,
    )


def require_manifest_lock_signature(
    *,
    lock_path: Path,
    signature_path: Path,
    public_key_path: Path,
) -> None:
    result = verify_manifest_lock_signature(
        lock_path=lock_path,
        signature_path=signature_path,
        public_key_path=public_key_path,
    )
    if not result.valid:
        raise ManifestLockSignatureError(result.failure or "invalid manifest lock signature")


def manifest_lock_signature_status(
    *,
    lock_path: Path,
    signature_path: Path,
    public_key_path: Path,
    required: bool,
) -> JsonObject:
    """Return secret-free manifest lock signature status."""
    status: JsonObject = {
        "required": required,
        "signature_path": signature_path.as_posix(),
        "public_key_configured": public_key_path.exists(),
        "signature_configured": signature_path.exists(),
        "verified": False,
        "key_id": None,
    }
    if not public_key_path.exists() or not signature_path.exists():
        return status

    result = verify_manifest_lock_signature(
        lock_path=lock_path,
        signature_path=signature_path,
        public_key_path=public_key_path,
    )
    status["verified"] = result.valid
    status["key_id"] = result.key_id
    if result.failure is not None:
        status["error"] = result.failure
    return status


def manifest_lock_public_key_id(public_key: Ed25519PublicKey) -> str:
    return sha256_digest(
        {
            "algorithm": SIGNATURE_ALGORITHM,
            "public_key": _public_key_b64(public_key),
        }
    )


def verify_manifest_lock(
    *,
    manifest_dir: Path,
    lock_path: Path,
    records: list[ManifestLockRecord],
) -> None:
    lock = _read_lock(lock_path)
    lock_root = lock_path.parent.resolve(strict=False)
    expected_manifest_dir = _safe_relative_path(
        raw_path=_string(lock, "manifest_dir"),
        lock_root=lock_root,
    )
    if expected_manifest_dir.resolve(strict=False) != manifest_dir.resolve(strict=False):
        raise ManifestLockError("manifest lock targets a different manifest directory")

    manifest_entries = lock.get("manifests")
    if not isinstance(manifest_entries, list):
        raise ManifestLockError("manifest lock must contain a manifests list")

    locked_by_path: dict[Path, JsonObject] = {}
    locked_names: set[str] = set()
    for item in manifest_entries:
        if not isinstance(item, dict):
            raise ManifestLockError("manifest lock entry must be an object")
        entry = _json_object(item)
        entry_path = _safe_relative_path(raw_path=_string(entry, "path"), lock_root=lock_root)
        if entry_path in locked_by_path:
            raise ManifestLockError(f"duplicate manifest lock path: {_string(entry, 'path')}")
        entry_name = _string(entry, "name")
        if entry_name in locked_names:
            raise ManifestLockError(f"duplicate manifest lock name: {entry_name}")
        locked_by_path[entry_path] = entry
        locked_names.add(entry_name)

    records_by_path = {record.path.resolve(strict=True): record for record in records}
    missing_entries = sorted(
        _relative_lock_path(lock_root, record.path)
        for record in records
        if record.path.resolve(strict=True) not in locked_by_path
    )
    if missing_entries:
        raise ManifestLockError(f"manifest missing from lock: {missing_entries[0]}")

    stale_entries = sorted(
        _relative_lock_path(lock_root, locked_path)
        for locked_path in locked_by_path
        if locked_path.resolve(strict=False) not in records_by_path
    )
    if stale_entries:
        raise ManifestLockError(f"stale manifest lock entry: {stale_entries[0]}")

    for record_path, record in records_by_path.items():
        entry = locked_by_path[record_path]
        if _string(entry, "name") != record.name:
            raise ManifestLockError(f"manifest lock name mismatch: {record.name}")
        if _string(entry, "version") != record.version:
            raise ManifestLockError(f"manifest lock version mismatch: {record.name}")
        locked_hash = _string(entry, "manifest_hash")
        if not SHA256_RE.match(locked_hash):
            raise ManifestLockError(f"invalid manifest hash in lock: {record.name}")
        if locked_hash != record.manifest_hash:
            raise ManifestLockError(f"manifest hash mismatch: {record.name}")


def _read_lock(lock_path: Path) -> JsonObject:
    try:
        payload = json.loads(lock_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ManifestLockError(f"manifest lock not found: {lock_path}") from exc
    except json.JSONDecodeError as exc:
        raise ManifestLockError(f"manifest lock is invalid JSON: {lock_path}") from exc
    if not isinstance(payload, dict):
        raise ManifestLockError("manifest lock must be a JSON object")
    lock = _json_object(payload)
    if lock.get("lockfile_version") != LOCKFILE_VERSION:
        raise ManifestLockError("unsupported manifest lock version")
    return lock


def _read_signature(signature_path: Path) -> JsonObject:
    try:
        payload = json.loads(signature_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ManifestLockSignatureError(
            f"manifest lock signature not found: {signature_path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ManifestLockSignatureError(
            f"manifest lock signature is invalid JSON: {signature_path}"
        ) from exc
    return _object(payload, "manifest lock signature")


def _json_object(value: dict[Any, Any]) -> JsonObject:
    result: JsonObject = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise ManifestLockError("manifest lock keys must be strings")
        result[key] = item
    return result


def _string(value: JsonObject, key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise ManifestLockError(f"manifest lock missing {key}")
    return item


def _object(value: object, field: str) -> JsonObject:
    if not isinstance(value, dict):
        raise ManifestLockSignatureError(f"{field} must be an object")
    return _json_object(value)


def _require_string(value: object, field: str, expected: Optional[str] = None) -> str:
    if not isinstance(value, str) or not value:
        raise ManifestLockSignatureError(f"{field} must be a string")
    if expected is not None and value != expected:
        raise ManifestLockSignatureError(f"{field} has unsupported value")
    return value


def _require_hash(value: object, field: str) -> str:
    string_value = _require_string(value, field)
    if not SHA256_RE.match(string_value):
        raise ManifestLockSignatureError(f"{field} must be a sha256 digest")
    return string_value


def _signature_payload(
    *,
    lock_path: Path,
    lock_sha256: str,
    signature_metadata: JsonObject,
) -> JsonObject:
    return {
        "signature_type": SIGNATURE_TYPE,
        "format_version": SIGNATURE_FORMAT_VERSION,
        "lock_path": lock_path.as_posix(),
        "lock_sha256": lock_sha256,
        "signature": signature_metadata,
    }


def _load_private_key(path: Path) -> Ed25519PrivateKey:
    try:
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    except (OSError, ValueError) as exc:
        raise ManifestLockSignatureError(
            "manifest lock signing private key is missing or invalid"
        ) from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise ManifestLockSignatureError("manifest lock signing private key must be Ed25519")
    return key


def _load_public_key(path: Path) -> Ed25519PublicKey:
    try:
        key = serialization.load_pem_public_key(path.read_bytes())
    except (OSError, ValueError) as exc:
        raise ManifestLockSignatureError(
            "manifest lock signing public key is missing or invalid"
        ) from exc
    if not isinstance(key, Ed25519PublicKey):
        raise ManifestLockSignatureError("manifest lock signing public key must be Ed25519")
    return key


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
        raise ManifestLockSignatureError("manifest lock signature public key is invalid") from exc


def _optional_lock_sha(signature_path: Path) -> Optional[str]:
    try:
        value = _read_signature(signature_path).get("lock_sha256")
    except ManifestLockSignatureError:
        return None
    return value if isinstance(value, str) else None


def _optional_key_id(signature_path: Path) -> Optional[str]:
    try:
        signature = _read_signature(signature_path).get("signature")
    except ManifestLockSignatureError:
        return None
    if not isinstance(signature, dict):
        return None
    key_id = signature.get("key_id")
    return key_id if isinstance(key_id, str) else None


def _safe_relative_path(*, raw_path: str, lock_root: Path) -> Path:
    requested = Path(raw_path)
    if requested.is_absolute() or ".." in requested.parts:
        raise ManifestLockError("manifest lock paths must stay under the lock root")
    return lock_root.joinpath(requested).resolve(strict=False)


def _relative_lock_path(lock_root: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(lock_root).as_posix()
    except ValueError as exc:
        raise ManifestLockError("manifest lock paths must stay under the lock root") from exc

"""Verify the non-production signed-evidence demo artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, cast

from ithildin_api.manifest_lock import verify_manifest_lock_signature
from ithildin_audit_core import verify_signed_audit_export_bundle
from ithildin_schemas import JsonObject

DEFAULT_DEMO_ROOT = Path("var/review-packets/v0.2/signed-evidence-demo")


class SignedEvidenceDemoVerificationError(RuntimeError):
    """Raised when the signed-evidence demo cannot be verified."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo-root", type=Path, default=DEFAULT_DEMO_ROOT)
    args = parser.parse_args()

    try:
        result = verify_demo(args.demo_root)
    except (OSError, json.JSONDecodeError, SignedEvidenceDemoVerificationError) as exc:
        print(f"signed evidence demo verification failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def verify_demo(demo_root: Path) -> JsonObject:
    summary_path = demo_root / "summary.json"
    summary = cast(JsonObject, json.loads(summary_path.read_text(encoding="utf-8")))
    if summary.get("demo_type") != "ithildin.locally_signed_evidence_demo":
        raise SignedEvidenceDemoVerificationError("unexpected demo_type")
    if summary.get("non_production") is not True:
        raise SignedEvidenceDemoVerificationError("demo must be marked non_production")

    _verify_artifacts(demo_root, cast(JsonObject, summary.get("artifacts", {})))

    audit = cast(JsonObject, summary["audit"])
    manifest_lock = cast(JsonObject, summary["manifest_lock"])
    signed_bundle_path = Path(str(audit["signed_bundle_path"]))
    tampered_bundle_path = Path(str(audit["tampered_bundle_path"]))
    audit_public_key = demo_root / "keys/audit-demo-ed25519-public.pem"
    manifest_public_key = demo_root / "keys/manifest-lock-demo-ed25519-public.pem"
    manifest_signature_path = Path(str(manifest_lock["signature_path"]))
    manifest_lock_path = Path(str(manifest_lock.get("lock_path", "tool-manifests.lock.json")))

    signed_bundle = _read_json_object(signed_bundle_path)
    tampered_bundle = _read_json_object(tampered_bundle_path)
    signed_result = verify_signed_audit_export_bundle(
        signed_bundle,
        public_key_path=audit_public_key,
    )
    tampered_result = verify_signed_audit_export_bundle(
        tampered_bundle,
        public_key_path=audit_public_key,
    )
    manifest_result = verify_manifest_lock_signature(
        lock_path=manifest_lock_path,
        signature_path=manifest_signature_path,
        public_key_path=manifest_public_key,
    )

    if not signed_result.valid:
        raise SignedEvidenceDemoVerificationError("signed audit demo bundle did not verify")
    if tampered_result.valid:
        raise SignedEvidenceDemoVerificationError(
            "tampered audit demo bundle unexpectedly verified"
        )
    if not manifest_result.valid:
        raise SignedEvidenceDemoVerificationError("manifest lock demo signature did not verify")

    return cast(
        JsonObject,
        {
            "demo_root": demo_root.as_posix(),
            "non_production": True,
            "audit": {
                "verified": signed_result.valid,
                "key_id": signed_result.key_id,
                "tampered_verified": tampered_result.valid,
                "tampered_failure": tampered_result.failure,
            },
            "manifest_lock": {
                "verified": manifest_result.valid,
                "key_id": manifest_result.key_id,
            },
        },
    )


def _verify_artifacts(demo_root: Path, artifacts: JsonObject) -> None:
    if not artifacts:
        raise SignedEvidenceDemoVerificationError("summary artifact hashes are missing")
    demo_root_resolved = demo_root.resolve(strict=True)
    for name, value in artifacts.items():
        if not isinstance(value, dict):
            raise SignedEvidenceDemoVerificationError(
                f"artifact metadata must be an object: {name}"
            )
        raw_path = value.get("path")
        expected_sha256 = value.get("sha256")
        expected_bytes = value.get("bytes")
        if not isinstance(raw_path, str) or not isinstance(expected_sha256, str):
            raise SignedEvidenceDemoVerificationError(f"artifact metadata is incomplete: {name}")
        if not isinstance(expected_bytes, int):
            raise SignedEvidenceDemoVerificationError(f"artifact byte count is missing: {name}")
        artifact_path = Path(raw_path)
        if not artifact_path.is_absolute():
            artifact_path = Path.cwd() / artifact_path
        artifact_path = artifact_path.resolve(strict=True)
        try:
            artifact_path.relative_to(demo_root_resolved)
        except ValueError as exc:
            raise SignedEvidenceDemoVerificationError(
                f"artifact path escapes demo root: {name}"
            ) from exc
        actual_bytes = artifact_path.stat().st_size
        if actual_bytes != expected_bytes:
            raise SignedEvidenceDemoVerificationError(f"artifact byte count mismatch: {name}")
        actual_sha256 = "sha256:" + hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        if actual_sha256 != expected_sha256:
            raise SignedEvidenceDemoVerificationError(f"artifact digest mismatch: {name}")


def _read_json_object(path: Path) -> JsonObject:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SignedEvidenceDemoVerificationError(f"expected JSON object: {path}")
    return cast(dict[str, Any], value)


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import cast

import pytest
from ithildin_api.manifest_lock import verify_manifest_lock_signature
from ithildin_audit_core import verify_signed_audit_export_bundle
from ithildin_schemas import JsonObject

from scripts.signed_evidence_demo import build_demo
from scripts.signed_evidence_demo_verify import (
    SignedEvidenceDemoVerificationError,
    verify_demo,
)


def test_signed_evidence_demo_generates_and_verifies(tmp_path: Path) -> None:
    lock_path = Path("tool-manifests.lock.json")

    summary = build_demo(output_dir=tmp_path / "demo", lock_path=lock_path)

    audit = cast(JsonObject, summary["audit"])
    manifest_lock = cast(JsonObject, summary["manifest_lock"])
    assert audit["verified"] is True
    assert audit["tampered_verified"] is False
    assert manifest_lock["verified"] is True
    assert Path(str(audit["signed_bundle_path"])).exists()
    assert Path(str(audit["tampered_bundle_path"])).exists()
    assert Path(str(manifest_lock["signature_path"])).exists()
    assert (tmp_path / "demo/SIGNED_EVIDENCE_DEMO.md").exists()
    artifacts = cast(JsonObject, summary["artifacts"])
    for artifact_name in [
        "signed_audit_export_demo_bundle",
        "tampered_audit_export_demo_bundle",
        "manifest_lock_signature_demo_bundle",
        "signed_evidence_demo_summary",
    ]:
        artifact = cast(JsonObject, artifacts[artifact_name])
        artifact_path = Path(str(artifact["path"]))
        assert artifact_path.exists()
        assert artifact["sha256"] == _sha256_file(artifact_path)
        assert isinstance(artifact["bytes"], int)

    signed_bundle = cast(
        JsonObject,
        json.loads(Path(str(audit["signed_bundle_path"])).read_text(encoding="utf-8")),
    )
    audit_public_key = tmp_path / "demo/keys/audit-demo-ed25519-public.pem"
    assert verify_signed_audit_export_bundle(
        signed_bundle,
        public_key_path=audit_public_key,
    ).valid
    assert verify_manifest_lock_signature(
        lock_path=lock_path,
        signature_path=Path(str(manifest_lock["signature_path"])),
        public_key_path=tmp_path / "demo/keys/manifest-lock-demo-ed25519-public.pem",
    ).valid


def test_signed_evidence_demo_keeps_key_material_in_ignored_demo_path(tmp_path: Path) -> None:
    lock_path = Path("tool-manifests.lock.json")

    summary = build_demo(output_dir=tmp_path / "var/review-packets/v0.2/demo", lock_path=lock_path)

    output_dir = Path(str(summary["output_dir"]))
    private_keys = sorted(output_dir.rglob("*private.pem"))
    assert private_keys
    assert all("var/review-packets/v0.2" in path.as_posix() for path in private_keys)


def test_signed_evidence_demo_standalone_verifier(tmp_path: Path) -> None:
    lock_path = Path("tool-manifests.lock.json")
    build_demo(output_dir=tmp_path / "demo", lock_path=lock_path)

    result = verify_demo(tmp_path / "demo")
    audit = cast(JsonObject, result["audit"])
    manifest_lock = cast(JsonObject, result["manifest_lock"])

    assert audit["verified"] is True
    assert audit["tampered_verified"] is False
    assert manifest_lock["verified"] is True


def test_signed_evidence_demo_verifier_uses_recorded_lock_path(tmp_path: Path) -> None:
    lock_path = tmp_path / "custom-tool-manifests.lock.json"
    lock_path.write_text(Path("tool-manifests.lock.json").read_text(encoding="utf-8"))
    build_demo(output_dir=tmp_path / "demo", lock_path=lock_path)

    result = verify_demo(tmp_path / "demo")
    manifest_lock = cast(JsonObject, result["manifest_lock"])

    assert manifest_lock["verified"] is True


def test_signed_evidence_demo_verifier_rejects_summary_confusion(tmp_path: Path) -> None:
    lock_path = Path("tool-manifests.lock.json")
    build_demo(output_dir=tmp_path / "demo", lock_path=lock_path)
    summary_path = tmp_path / "demo/summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["non_production"] = False
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    with pytest.raises(SignedEvidenceDemoVerificationError, match="non_production"):
        verify_demo(tmp_path / "demo")


def test_signed_evidence_demo_verifier_rejects_artifact_digest_mismatch(
    tmp_path: Path,
) -> None:
    lock_path = Path("tool-manifests.lock.json")
    build_demo(output_dir=tmp_path / "demo", lock_path=lock_path)
    summary_path = tmp_path / "demo/summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["artifacts"]["signed_audit_export_demo_bundle"]["sha256"] = (
        "sha256:" + ("f" * 64)
    )
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    with pytest.raises(SignedEvidenceDemoVerificationError, match="digest mismatch"):
        verify_demo(tmp_path / "demo")


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()

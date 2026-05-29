"""Generate non-production locally signed evidence demo artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from ithildin_api.manifest_lock import (
    generate_manifest_lock_signing_keypair,
    verify_manifest_lock_signature,
    write_manifest_lock_signature,
)
from ithildin_audit_core import (
    AuditWriter,
    generate_audit_signing_keypair,
    signed_audit_export_bundle,
    verify_signed_audit_export_bundle,
)
from ithildin_schemas import AuditEventType, JsonObject, PolicyDecisionValue

DEMO_ROOT = Path("var/review-packets/v0.2/signed-evidence-demo")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEMO_ROOT)
    parser.add_argument("--lock-path", type=Path, default=Path("tool-manifests.lock.json"))
    args = parser.parse_args()

    result = build_demo(output_dir=args.output_dir, lock_path=args.lock_path)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def build_demo(*, output_dir: Path, lock_path: Path) -> JsonObject:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    audit_private_key = output_dir / "keys/audit-demo-ed25519-private.pem"
    audit_public_key = output_dir / "keys/audit-demo-ed25519-public.pem"
    manifest_private_key = output_dir / "keys/manifest-lock-demo-ed25519-private.pem"
    manifest_public_key = output_dir / "keys/manifest-lock-demo-ed25519-public.pem"

    audit_key_id = generate_audit_signing_keypair(
        private_key_path=audit_private_key,
        public_key_path=audit_public_key,
    )
    manifest_key_id = generate_manifest_lock_signing_keypair(
        private_key_path=manifest_private_key,
        public_key_path=manifest_public_key,
    )

    writer = AuditWriter(
        db_path=output_dir / "audit/demo-audit.sqlite3",
        jsonl_path=output_dir / "audit/demo-audit.jsonl",
    )
    writer.initialize()
    writer.write_event(
        event_id="evt_demo_signed_evidence_001",
        event_type=AuditEventType.POLICY_EVALUATED,
        request_id="req_demo_signed_evidence_001",
        principal={"id": "demo:reviewer", "roles": ["Auditor"]},
        timestamp=datetime(2026, 5, 29, 0, 0, 0, tzinfo=UTC),
        tool_name="fs.read",
        resource={"type": "workspace_path", "path": "README.md", "in_scope": True},
        decision=PolicyDecisionValue.ALLOW,
        policy_version="demo-policy-v1",
        matched_rules=["demo_allow_read"],
        input_hash="sha256:" + ("1" * 64),
        metadata={"demo": True, "non_production": True},
    )
    audit_jsonl = writer.export_jsonl_bundle()
    signed_audit_bundle = signed_audit_export_bundle(
        jsonl_bundle=audit_jsonl,
        private_key_path=audit_private_key,
        public_key_path=audit_public_key,
    )
    signed_audit_path = output_dir / "audit/signed-audit-export-demo.json"
    _write_json(signed_audit_path, signed_audit_bundle)
    audit_verification = verify_signed_audit_export_bundle(
        signed_audit_bundle,
        public_key_path=audit_public_key,
    )

    tampered_bundle = cast(JsonObject, json.loads(json.dumps(signed_audit_bundle)))
    tampered_bundle["events_sha256"] = "sha256:" + ("2" * 64)
    tampered_path = output_dir / "audit/signed-audit-export-demo-tampered.json"
    _write_json(tampered_path, tampered_bundle)
    tampered_verification = verify_signed_audit_export_bundle(
        tampered_bundle,
        public_key_path=audit_public_key,
    )

    manifest_signature_path = output_dir / "manifest-lock/tool-manifests.lock.sig.demo.json"
    write_manifest_lock_signature(
        lock_path=lock_path,
        signature_path=manifest_signature_path,
        private_key_path=manifest_private_key,
        public_key_path=manifest_public_key,
    )
    manifest_verification = verify_manifest_lock_signature(
        lock_path=lock_path,
        signature_path=manifest_signature_path,
        public_key_path=manifest_public_key,
    )

    summary_path = output_dir / "SIGNED_EVIDENCE_DEMO.md"
    summary = cast(
        JsonObject,
        {
        "demo_type": "ithildin.locally_signed_evidence_demo",
        "non_production": True,
        "output_dir": output_dir.as_posix(),
        "audit": {
            "key_id": audit_key_id,
            "signed_bundle_path": signed_audit_path.as_posix(),
            "verified": audit_verification.valid,
            "tampered_bundle_path": tampered_path.as_posix(),
            "tampered_verified": tampered_verification.valid,
        },
        "manifest_lock": {
            "key_id": manifest_key_id,
            "signature_path": manifest_signature_path.as_posix(),
            "verified": manifest_verification.valid,
        },
        "artifacts": {
            "signed_audit_export_demo_bundle": _artifact_metadata(signed_audit_path),
            "tampered_audit_export_demo_bundle": _artifact_metadata(tampered_path),
            "manifest_lock_signature_demo_bundle": _artifact_metadata(
                manifest_signature_path
            ),
        },
        },
    )
    _write_json(output_dir / "summary.json", summary)
    _write_markdown_summary(summary_path, summary)
    artifacts = cast(JsonObject, summary["artifacts"])
    artifacts["signed_evidence_demo_summary"] = _artifact_metadata(summary_path)
    _write_json(output_dir / "summary.json", summary)
    return summary


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _artifact_metadata(path: Path) -> JsonObject:
    content = path.read_bytes()
    return {
        "path": path.as_posix(),
        "sha256": "sha256:" + hashlib.sha256(content).hexdigest(),
        "bytes": len(content),
    }


def _write_markdown_summary(path: Path, summary: JsonObject) -> None:
    audit = cast(JsonObject, summary["audit"])
    manifest_lock = cast(JsonObject, summary["manifest_lock"])
    artifacts = cast(JsonObject, summary["artifacts"])
    signed_audit = cast(JsonObject, artifacts["signed_audit_export_demo_bundle"])
    tampered_audit = cast(JsonObject, artifacts["tampered_audit_export_demo_bundle"])
    manifest_signature = cast(
        JsonObject,
        artifacts["manifest_lock_signature_demo_bundle"],
    )
    path.write_text(
        f"""# Signed Evidence Demo

This directory contains non-production local fixture evidence for reviewer inspection. The keys were
generated only for this ignored demo directory and are not runtime trust roots, hosted trust roots,
or official release signing keys.

## Audit Export

- key ID: `{audit["key_id"]}`
- signed bundle: `{audit["signed_bundle_path"]}`
- signed bundle SHA-256: `{signed_audit["sha256"]}`
- verification valid: `{str(audit["verified"]).lower()}`
- tampered bundle: `{audit["tampered_bundle_path"]}`
- tampered bundle SHA-256: `{tampered_audit["sha256"]}`
- tampered verification valid: `{str(audit["tampered_verified"]).lower()}`

## Manifest Lock

- key ID: `{manifest_lock["key_id"]}`
- signature bundle: `{manifest_lock["signature_path"]}`
- signature bundle SHA-256: `{manifest_signature["sha256"]}`
- verification valid: `{str(manifest_lock["verified"]).lower()}`

## Artifact Hashes

`summary.json` includes SHA-256 digests for this markdown summary, the signed audit export demo
bundle, the tampered audit export demo bundle, and the manifest-lock signature demo bundle.

## Warning

This demonstrates locally signed evidence only. It does not provide external notarization, hosted
custody, official supply-chain signing, production key management, or immutable storage.
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())

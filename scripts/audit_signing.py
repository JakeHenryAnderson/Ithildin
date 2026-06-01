"""Manage local audit export signing keys and verify signed audit exports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

from ithildin_api.config import Settings
from ithildin_audit_core import (
    AuditSigningError,
    generate_audit_signing_keypair,
    verify_signed_audit_export_bundle,
)
from ithildin_schemas import JsonObject


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    keygen = subparsers.add_parser("keygen", help="create a local Ed25519 audit signing keypair")
    keygen.add_argument("--private-key", type=Path)
    keygen.add_argument("--public-key", type=Path)
    keygen.add_argument("--force", action="store_true", help="overwrite existing key files")

    verify = subparsers.add_parser("verify", help="verify a signed audit export JSON bundle")
    verify.add_argument("file", type=Path)
    verify.add_argument("--public-key", type=Path, required=True, help="trusted public key PEM")

    args = parser.parse_args()
    settings = Settings(admin_token="audit-signing-cli")

    try:
        if args.command == "keygen":
            private_key_path = args.private_key or settings.audit_signing_private_key_path
            public_key_path = args.public_key or settings.audit_signing_public_key_path
            key_id = generate_audit_signing_keypair(
                private_key_path=private_key_path,
                public_key_path=public_key_path,
                overwrite=args.force,
            )
            print(
                json.dumps(
                    {
                        "status": "created",
                        "algorithm": "ed25519",
                        "key_id": key_id,
                        "private_key_path": private_key_path.as_posix(),
                        "public_key_path": public_key_path.as_posix(),
                    },
                    sort_keys=True,
                    indent=2,
                )
            )
            return

        if args.command == "verify":
            raw_bundle = json.loads(args.file.read_text(encoding="utf-8"))
            if not isinstance(raw_bundle, dict):
                raise AuditSigningError("bundle must be an object")
            bundle = cast(JsonObject, raw_bundle)
            result = verify_signed_audit_export_bundle(
                bundle,
                public_key_path=args.public_key,
            )
            print(json.dumps(result.as_dict(), sort_keys=True, indent=2))
            if not result.valid:
                raise SystemExit(1)
            return
    except (AuditSigningError, OSError, json.JSONDecodeError) as exc:
        print(f"audit signing error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    _unreachable(args)


def _unreachable(value: Any) -> None:
    raise RuntimeError(f"unsupported command: {value}")


if __name__ == "__main__":
    main()

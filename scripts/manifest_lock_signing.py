"""Manage local manifest lock signing keys and signatures."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

from ithildin_api.config import Settings
from ithildin_api.manifest_lock import (
    ManifestLockSignatureError,
    generate_manifest_lock_signing_keypair,
    verify_manifest_lock_signature,
    write_manifest_lock_signature,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    keygen = subparsers.add_parser("keygen", help="create a manifest-lock signing keypair")
    keygen.add_argument("--private-key", type=Path)
    keygen.add_argument("--public-key", type=Path)
    keygen.add_argument("--force", action="store_true", help="overwrite existing key files")

    sign = subparsers.add_parser("sign", help="sign the current manifest lock")
    sign.add_argument("--lock-path", type=Path)
    sign.add_argument("--signature-path", type=Path)
    sign.add_argument("--private-key", type=Path)
    sign.add_argument("--public-key", type=Path)

    verify = subparsers.add_parser("verify", help="verify the manifest lock signature")
    verify.add_argument("--lock-path", type=Path)
    verify.add_argument("--signature-path", type=Path)
    verify.add_argument("--public-key", type=Path)

    args = parser.parse_args()
    settings = Settings(admin_token="manifest-lock-signing-cli")

    private_key_path = (
        getattr(args, "private_key", None) or settings.manifest_lock_signing_private_key_path
    )
    public_key_path = (
        getattr(args, "public_key", None) or settings.manifest_lock_signing_public_key_path
    )
    lock_path = getattr(args, "lock_path", None) or settings.manifest_lock_path
    signature_path = getattr(args, "signature_path", None) or settings.manifest_lock_signature_path

    try:
        if args.command == "keygen":
            key_id = generate_manifest_lock_signing_keypair(
                private_key_path=private_key_path,
                public_key_path=public_key_path,
                overwrite=args.force,
            )
            _print_json(
                {
                    "status": "created",
                    "algorithm": "ed25519",
                    "key_id": key_id,
                    "private_key_path": private_key_path.as_posix(),
                    "public_key_path": public_key_path.as_posix(),
                }
            )
            return 0
        if args.command == "sign":
            bundle = cast(
                dict[str, Any],
                write_manifest_lock_signature(
                    lock_path=lock_path,
                    signature_path=signature_path,
                    private_key_path=private_key_path,
                    public_key_path=public_key_path,
                ),
            )
            _print_json(
                {
                    "status": "signed",
                    "signature_path": signature_path.as_posix(),
                    "lock_sha256": bundle["lock_sha256"],
                    "key_id": bundle["signature"]["key_id"],
                }
            )
            return 0
        if args.command == "verify":
            result = verify_manifest_lock_signature(
                lock_path=lock_path,
                signature_path=signature_path,
                public_key_path=public_key_path,
            )
            _print_json(result.as_dict())
            return 0 if result.valid else 1
    except (ManifestLockSignatureError, OSError) as exc:
        print(f"manifest lock signing error: {exc}", file=sys.stderr)
        return 1

    raise RuntimeError(f"unsupported command: {args.command}")


def _print_json(value: object) -> None:
    print(json.dumps(value, sort_keys=True, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())

"""Create and verify local signed Ithildin Node release-artifact manifests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ithildin_node.release_artifact import (
    NodeReleaseArtifactError,
    generate_node_release_signing_keypair,
    sign_node_release_artifact,
    verify_node_release_artifact,
)
from ithildin_schemas import JsonObject

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRIVATE_KEY = ROOT / "var/keys/node-release-artifact-private.pem"
DEFAULT_PUBLIC_KEY = ROOT / "var/keys/node-release-artifact-public.pem"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    keygen = subparsers.add_parser("keygen")
    keygen.add_argument("--private-key", type=Path, default=DEFAULT_PRIVATE_KEY)
    keygen.add_argument("--public-key", type=Path, default=DEFAULT_PUBLIC_KEY)
    sign = subparsers.add_parser("sign")
    sign.add_argument("--image", required=True)
    sign.add_argument("--node-version", required=True)
    sign.add_argument("--output", type=Path, required=True)
    sign.add_argument("--private-key", type=Path, default=DEFAULT_PRIVATE_KEY)
    sign.add_argument("--public-key", type=Path, default=DEFAULT_PUBLIC_KEY)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--bundle", type=Path, required=True)
    verify.add_argument("--image", required=True)
    verify.add_argument("--public-key", type=Path, default=DEFAULT_PUBLIC_KEY)
    args = parser.parse_args()
    result: JsonObject
    try:
        if args.command == "keygen":
            key_id = generate_node_release_signing_keypair(
                args.private_key,
                args.public_key,
            )
            result = {
                "valid": True,
                "configured": True,
                "key_id": key_id,
                "private_key_mode": "0600",
                "public_key_mode": "0644",
                "local_operator_evidence_only": True,
            }
        elif args.command == "sign":
            bundle = sign_node_release_artifact(
                image_reference=args.image,
                node_version=args.node_version,
                source_root=ROOT,
                dockerfile_path=ROOT / "deploy/Dockerfile.node",
                lockfile_path=ROOT / "uv.lock",
                private_key_path=args.private_key,
                public_key_path=args.public_key,
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(bundle, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            artifact = bundle["artifact"]
            signature = bundle["signature"]
            if not isinstance(artifact, dict) or not isinstance(signature, dict):
                raise NodeReleaseArtifactError("generated Node release bundle is invalid")
            result = {
                "valid": True,
                "image_id": artifact.get("image_id"),
                "node_version": artifact.get("node_version"),
                "source_commit": artifact.get("source_commit"),
                "key_id": signature.get("key_id"),
                "local_operator_evidence_only": True,
                "gateway_enforcement": False,
                "self_update_authority": False,
            }
        else:
            bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
            verification = verify_node_release_artifact(
                bundle,
                public_key_path=args.public_key,
                expected_image_reference=args.image,
            )
            result = verification.safe_summary()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["valid"] else 1
    except (NodeReleaseArtifactError, OSError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {
                    "valid": False,
                    "failure": str(exc),
                    "local_operator_evidence_only": True,
                    "gateway_enforcement": False,
                    "self_update_authority": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

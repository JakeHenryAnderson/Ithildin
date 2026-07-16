"""Manage the local Ithildin Node configuration-signing trust root."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ithildin_api.config import Settings
from ithildin_api.node_configuration import (
    NodeConfigurationSigner,
    NodeConfigurationSigningError,
    generate_node_configuration_signing_keypair,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("keygen", "status"))
    parser.add_argument("--private-key", type=Path)
    parser.add_argument("--public-key", type=Path)
    args = parser.parse_args()
    settings = Settings(admin_token="node-configuration-cli")
    private_path, public_path = _paths(settings, args.private_key, args.public_key)
    try:
        if args.command == "keygen":
            trust = generate_node_configuration_signing_keypair(private_path, public_path)
            result = {
                "valid": True,
                "configured": True,
                "key_id": trust.key_id,
                "private_key_mode": "0600",
                "public_key_mode": "0644",
            }
        else:
            if not private_path.exists() and not public_path.exists():
                result = {"valid": True, "configured": False, "key_id": None}
            else:
                signer = NodeConfigurationSigner.load(private_path, public_path)
                result = {
                    "valid": True,
                    "configured": True,
                    "key_id": signer.trust.key_id,
                }
    except NodeConfigurationSigningError as exc:
        result = {"valid": False, "configured": False, "failure": str(exc)}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


def _paths(
    settings: Settings, private_key: Path | None, public_key: Path | None
) -> tuple[Path, Path]:
    return (
        private_key or settings.node_configuration_signing_private_key_path,
        public_key or settings.node_configuration_signing_public_key_path,
    )


if __name__ == "__main__":
    raise SystemExit(main())

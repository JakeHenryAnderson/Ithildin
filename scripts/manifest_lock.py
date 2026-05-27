#!/usr/bin/env python
"""Generate or check the trusted tool manifest lockfile."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ithildin_api.manifest_lock import (
    ManifestLockRecord,
    manifest_lock_payload,
    write_manifest_lock,
)
from ithildin_api.registry import ToolRegistry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-dir", type=Path, default=Path("tool-manifests"))
    parser.add_argument("--lock-path", type=Path, default=Path("tool-manifests.lock.json"))
    parser.add_argument("--check", action="store_true", help="verify the lockfile is current")
    args = parser.parse_args()

    registry = ToolRegistry.load(args.manifest_dir)
    records = [
        ManifestLockRecord(
            path=tool.source_path,
            name=tool.manifest.name,
            version=tool.manifest.version,
            manifest_hash=tool.manifest_hash,
        )
        for tool in registry.list_tools()
    ]

    if args.check:
        expected = manifest_lock_payload(
            manifest_dir=args.manifest_dir,
            lock_path=args.lock_path,
            records=records,
        )
        current_text = args.lock_path.read_text(encoding="utf-8")
        import json

        current = json.loads(current_text)
        if current != expected:
            print("tool manifest lock is out of date", file=sys.stderr)
            return 1
        return 0

    write_manifest_lock(
        manifest_dir=args.manifest_dir,
        lock_path=args.lock_path,
        records=records,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Print read-only diagnostics for Ithildin's local audit evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ithildin_api.config import Settings
from ithildin_audit_core import AuditWriter, audit_signing_status


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", type=Path)
    parser.add_argument("--log-path", type=Path)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument(
        "--fail-on-invalid",
        action="store_true",
        help="exit nonzero when audit verification is invalid",
    )
    args = parser.parse_args()

    settings = Settings(admin_token="audit-diagnostics-cli")
    writer = AuditWriter(
        args.db_path or settings.db_path,
        args.log_path or settings.audit_log_path,
    )
    diagnostics = {
        **writer.diagnostics(),
        "signing": audit_signing_status(
            settings.audit_signing_private_key_path,
            settings.audit_signing_public_key_path,
        ),
    }

    if args.json:
        json.dump(diagnostics, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        _print_human(diagnostics)

    verification = diagnostics["verification"]
    if (
        args.fail_on_invalid
        and isinstance(verification, dict)
        and verification.get("valid") is False
    ):
        return 2
    return 0


def _print_human(diagnostics: dict[str, Any]) -> None:
    verification = diagnostics["verification"]
    if not isinstance(verification, dict):
        print("Audit diagnostics unavailable.")
        return

    print(f"Audit DB: {diagnostics['db_path']}")
    print(f"Audit JSONL: {diagnostics['log_path']}")
    print(f"Category: {diagnostics['category']}")
    lifecycle = diagnostics.get("lifecycle")
    if isinstance(lifecycle, dict):
        print(f"Lifecycle: {lifecycle.get('status')}")
        print(f"Retention mode: {lifecycle.get('retention_mode')}")
    print(f"Valid: {verification.get('valid')}")
    print(f"Events: {verification.get('event_count')}")
    print(f"SQLite events: {diagnostics.get('sqlite_event_count')}")
    print(f"JSONL lines: {diagnostics.get('jsonl_line_count')}")
    print(f"Head hash: {verification.get('head_hash')}")
    print(f"JSONL head hash: {diagnostics.get('jsonl_head_hash')}")
    failure = verification.get("failure")
    if isinstance(failure, dict) and failure:
        print(
            "First failure: "
            f"row={failure.get('row_number')} "
            f"event={failure.get('event_id')} "
            f"reason={failure.get('reason')}"
        )


if __name__ == "__main__":
    raise SystemExit(main())

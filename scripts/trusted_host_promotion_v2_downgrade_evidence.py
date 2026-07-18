#!/usr/bin/env python3
"""Prove the authorized v1 writer cannot mutate a migrated v2 database."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sqlite3
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType, SimpleNamespace

from ithildin_api.database import initialize_database
from ithildin_schemas import ApprovalRequest, ApprovalStatus

BASELINE_COMMIT = "250e6d8947972de28de134b72e0561bf39c62f5f"
BASELINE_FILES = {
    "apps/api/src/ithildin_api/approvals.py": (
        "214bd207ac5208ecbfd6fbd5ba5ec024485edc11f88e133a5e5e699821dfec48"
    ),
    "apps/api/src/ithildin_api/trusted_host_promotions.py": (
        "5361ac1ec20098bff482def23cbd26e3d86e5201a6f64cc03a031853b1df5eeb"
    ),
}


def main() -> int:
    baseline_sources = _baseline_sources()
    source_hashes_valid = _verify_baseline_sources(baseline_sources)
    with tempfile.TemporaryDirectory(prefix="ithildin-tgb002-") as temporary:
        root = Path(temporary)
        db_path = root / "ithildin.sqlite3"
        staging_root = root / "trusted-host-staging"
        baseline_approvals, baseline_promotions = _load_baseline_modules(
            root,
            baseline_sources,
        )
        _create_v1_fixture(db_path)
        initialize_database(db_path)
        _insert_v2_rows(db_path)
        cases = _run_old_writer_cases(
            db_path,
            staging_root=staging_root,
            baseline_approvals=baseline_approvals,
            baseline_promotions=baseline_promotions,
        )
        statuses = _promotion_statuses(db_path)
        no_placement_effect = not staging_root.exists()

    valid = source_hashes_valid and all(cases.values()) and no_placement_effect
    print("Ithildin trusted-host promotion v2 downgrade evidence")
    print(f"valid: {str(valid).lower()}")
    print(f"baseline_commit: {BASELINE_COMMIT}")
    print(f"source_hashes_valid: {str(source_hashes_valid).lower()}")
    print(f"no_placement_effect: {str(no_placement_effect).lower()}")
    print("proposal_statuses:")
    for proposal_id, status in sorted(statuses.items()):
        print(f"- {proposal_id}: {status}")
    print("cases:")
    for name, passed in cases.items():
        print(f"- {name}: {str(passed).lower()}")
    return 0 if valid else 1


def _baseline_sources() -> dict[str, bytes]:
    return {
        path: subprocess.run(
            ["git", "show", f"{BASELINE_COMMIT}:{path}"],
            check=True,
            capture_output=True,
        ).stdout
        for path in BASELINE_FILES
    }


def _verify_baseline_sources(sources: Mapping[str, bytes]) -> bool:
    for path, expected in BASELINE_FILES.items():
        source = sources[path]
        if hashlib.sha256(source).hexdigest() != expected:
            return False
    return True


def _load_baseline_modules(
    root: Path,
    sources: Mapping[str, bytes],
) -> tuple[ModuleType, ModuleType]:
    module_root = root / "frozen-v1-writer"
    module_root.mkdir()
    loaded: list[ModuleType] = []
    for name, path in (
        ("ithildin_frozen_v1_approvals", "apps/api/src/ithildin_api/approvals.py"),
        (
            "ithildin_frozen_v1_trusted_host_promotions",
            "apps/api/src/ithildin_api/trusted_host_promotions.py",
        ),
    ):
        module_path = module_root / f"{name}.py"
        module_path.write_bytes(sources[path])
        spec = importlib.util.spec_from_file_location(name, module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load frozen writer module: {name}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        finally:
            sys.modules.pop(name, None)
        loaded.append(module)
    return loaded[0], loaded[1]


def _run_old_writer_cases(
    db_path: Path,
    *,
    staging_root: Path,
    baseline_approvals: ModuleType,
    baseline_promotions: ModuleType,
) -> dict[str, bool]:
    cases: dict[str, bool] = {}
    old_approval_store = baseline_approvals.ApprovalStore(db_path)
    old_promotion_store = baseline_promotions.TrustedHostPromotionStore(db_path)
    cases["legacy_proposal_insert_rejected"] = _database_rejected(
        lambda: old_promotion_store.create_proposal(
            baseline_promotions.TrustedHostPromotionProposal(
                proposal_id="old_thp",
                request_id="old_req",
                status="approval_required",
                created_at="2026-01-01T00:00:00+00:00",
                updated_at="2026-01-01T00:00:00+00:00",
                workspace_id="default",
                sandbox_descriptor_id="sdesc_old",
                sandbox_descriptor_hash="sha256:" + ("2" * 64),
                sandbox_id="sandbox-old",
                source_artifact_label="sandbox://sandbox-old/a.txt",
                host_staging_label="host-staging://old",
                artifact_sha256="sha256:" + ("3" * 64),
                artifact_size_bytes=1,
                artifact_media_label="text/plain",
                proposal_hash="sha256:" + ("4" * 64),
                metadata={},
            )
        )
    )
    cases["legacy_approval_insert_rejected"] = _database_rejected(
        lambda: old_approval_store.create(_v2_approval_for_old_insert())
    )
    cases["legacy_attempt_insert_rejected"] = _database_rejected(
        lambda: old_promotion_store.create_attempt(
            baseline_promotions.TrustedHostPromotionAttempt(
                attempt_id="old_thpa",
                approval_id="old_appr",
                proposal_id="old_thp",
                request_id="old_req",
                workspace_id="default",
                host_staging_label="host-staging://old",
                artifact_sha256="sha256:" + ("3" * 64),
                staged_sha256=None,
                status="prepared",
                failure_reason=None,
                created_at="2026-01-01T00:00:00+00:00",
                updated_at="2026-01-01T00:00:00+00:00",
                metadata={},
            )
        ),
        translated_error=baseline_promotions.TrustedHostPromotionError,
    )
    cases["legacy_approve_migrated_row_rejected"] = _database_rejected(
        lambda: old_approval_store.set_status(
            "appr_v1",
            ApprovalStatus.APPROVED,
            decided_by="old-writer",
        )
    )
    cases["legacy_deny_v2_row_rejected"] = _database_rejected(
        lambda: old_approval_store.set_status(
            "appr_v2",
            ApprovalStatus.DENIED,
            decided_by="old-writer",
        )
    )
    old_promotion_service = baseline_promotions.TrustedHostPromotionService(
        store=old_promotion_store,
        read_executor=None,
        descriptor_store=None,
        staging_root=staging_root,
    )
    old_promotion_service.approval_review = lambda *args, **kwargs: {"valid": True}
    fake_approval_service = SimpleNamespace(
        get=lambda _approval_id: SimpleNamespace(request_hash="sha256:" + ("5" * 64))
    )
    cases["legacy_apply_migrated_row_stops_before_placement"] = _old_apply_rejected(
        old_promotion_service,
        proposal_id="thp_v1",
        approval_id="appr_v1",
        approval_service=fake_approval_service,
        error_type=baseline_promotions.TrustedHostPromotionError,
    )
    cases["legacy_apply_v2_row_stops_before_placement"] = _old_apply_rejected(
        old_promotion_service,
        proposal_id="thp_v2",
        approval_id="appr_v2",
        approval_service=fake_approval_service,
        error_type=baseline_promotions.TrustedHostPromotionError,
    )
    return cases


def _v2_approval_for_old_insert() -> ApprovalRequest:
    return ApprovalRequest(
        approval_id="old_appr",
        request_id="old_req",
        request_hash="sha256:" + ("1" * 64),
        principal={"id": "agent:old"},
        tool_name="fs.patch.apply",
        resource={},
        status=ApprovalStatus.PENDING,
        summary="old writer insert",
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
        one_time_scope={},
        approval_contract_version="2",
        requester_principal_id="agent:old",
        requester_principal_generation="sha256:" + ("2" * 64),
    )


def _old_apply_rejected(
    service: object,
    *,
    proposal_id: str,
    approval_id: str,
    approval_service: object,
    error_type: type[Exception],
) -> bool:
    try:
        service.apply_approved(  # type: ignore[attr-defined]
            proposal_id=proposal_id,
            approval_id=approval_id,
            approval_service=approval_service,
        )
    except error_type as exc:
        return "proposal is not applicable" in str(exc)
    return False


def _database_rejected(
    operation: Callable[[], object],
    *,
    translated_error: type[Exception] | None = None,
) -> bool:
    try:
        operation()
    except sqlite3.DatabaseError:
        return True
    except Exception as exc:
        if translated_error is not None and isinstance(exc, translated_error):
            return isinstance(exc.__cause__, sqlite3.DatabaseError)
        raise
    return False


def _create_v1_fixture(db_path: Path) -> None:
    with sqlite3.connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE app_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            INSERT INTO app_metadata VALUES ('schema_version', '1');
            CREATE TABLE approvals (
                approval_id TEXT PRIMARY KEY, request_id TEXT NOT NULL,
                request_hash TEXT NOT NULL, principal_json TEXT NOT NULL,
                tool_name TEXT NOT NULL, resource_json TEXT NOT NULL,
                status TEXT NOT NULL, summary TEXT NOT NULL, expires_at TEXT NOT NULL,
                one_time_scope_json TEXT NOT NULL, metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                decided_by TEXT, decision_reason TEXT
            );
            CREATE TABLE trusted_host_promotion_proposals (
                proposal_id TEXT PRIMARY KEY, request_id TEXT NOT NULL,
                status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                workspace_id TEXT NOT NULL, sandbox_descriptor_id TEXT NOT NULL,
                sandbox_descriptor_hash TEXT NOT NULL, sandbox_id TEXT NOT NULL,
                source_artifact_label TEXT NOT NULL, host_staging_label TEXT NOT NULL,
                artifact_sha256 TEXT NOT NULL, artifact_size_bytes INTEGER NOT NULL,
                artifact_media_label TEXT NOT NULL, proposal_hash TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            );
            CREATE TABLE trusted_host_promotion_attempts (
                attempt_id TEXT PRIMARY KEY, approval_id TEXT NOT NULL UNIQUE,
                proposal_id TEXT NOT NULL, request_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL, host_staging_label TEXT NOT NULL,
                artifact_sha256 TEXT NOT NULL, staged_sha256 TEXT, status TEXT NOT NULL,
                failure_reason TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            );
            """
        )
        connection.execute(
            "INSERT INTO approvals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "appr_v1",
                "req_v1",
                "sha256:" + ("a" * 64),
                json.dumps({"id": "agent:v1"}),
                "trusted_host.promotion.stage",
                "{}",
                "pending",
                "legacy approval",
                "2030-01-01T00:00:00+00:00",
                "{}",
                "{}",
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
                "caller:v1",
                "legacy reason",
            ),
        )
        connection.execute(
            "INSERT INTO trusted_host_promotion_proposals VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "thp_v1",
                "req_v1",
                "approval_required",
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
                "default",
                "sdesc_v1",
                "sha256:" + ("b" * 64),
                "sandbox-v1",
                "sandbox://sandbox-v1/a.txt",
                "host-staging://a",
                "sha256:" + ("c" * 64),
                1,
                "text/plain",
                "sha256:" + ("d" * 64),
                "{}",
            ),
        )
        connection.execute(
            "INSERT INTO trusted_host_promotion_attempts VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "thpa_v1",
                "appr_v1",
                "thp_v1",
                "req_v1",
                "default",
                "host-staging://a",
                "sha256:" + ("c" * 64),
                None,
                "prepared",
                None,
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
                "{}",
            ),
        )
        connection.commit()


def _insert_v2_rows(db_path: Path) -> None:
    authority_hash = "sha256:" + ("8" * 64)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO approvals (
                approval_id, request_id, request_hash, principal_json, tool_name,
                resource_json, status, summary, expires_at, one_time_scope_json,
                metadata_json, created_at, updated_at, approval_contract_version,
                requester_principal_id, requester_principal_generation,
                promotion_authority_hash, promotion_request_hash
            ) VALUES ('appr_v2', 'req_v2', ?, '{"id":"admin:local-ui"}',
                'trusted_host.promotion.stage', '{}', 'v2_pending', 'v2',
                '2030-01-01T00:00:00+00:00', '{}', '{}',
                '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00',
                '2', 'admin:local-ui', ?, ?, ?)
            """,
            (
                "sha256:" + ("5" * 64),
                "sha256:" + ("6" * 64),
                authority_hash,
                "sha256:" + ("7" * 64),
            ),
        )
        connection.execute(
            """
            INSERT INTO trusted_host_promotion_proposals (
                proposal_id, request_id, status, created_at, updated_at, workspace_id,
                sandbox_descriptor_id, sandbox_descriptor_hash, sandbox_id,
                source_artifact_label, host_staging_label, artifact_sha256,
                artifact_size_bytes, artifact_media_label, proposal_hash, metadata_json,
                authority_schema_version, authority_snapshot_json,
                authority_snapshot_hash, requester_principal_id,
                requester_principal_generation
            ) VALUES ('thp_v2', 'req_v2', 'v2_approval_required',
                '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00',
                'default', 'sdesc_v2', ?, 'sandbox-v2', 'sandbox://sandbox-v2/a.txt',
                'host-staging://a', ?, 1, 'text/plain', ?, '{}', '1', '{}', ?,
                'admin:local-ui', ?)
            """,
            (
                "sha256:" + ("9" * 64),
                "sha256:" + ("a" * 64),
                "sha256:" + ("b" * 64),
                authority_hash,
                "sha256:" + ("6" * 64),
            ),
        )
        connection.commit()


def _promotion_statuses(db_path: Path) -> dict[str, str]:
    with sqlite3.connect(db_path) as connection:
        return _promotion_statuses_from_connection(connection)


def _promotion_statuses_from_connection(
    connection: sqlite3.Connection,
) -> dict[str, str]:
    return {
        str(proposal_id): str(status)
        for proposal_id, status in connection.execute(
            "SELECT proposal_id, status FROM trusted_host_promotion_proposals"
        )
    }


if __name__ == "__main__":
    raise SystemExit(main())

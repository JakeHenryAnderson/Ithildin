from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import cast

import pytest
from ithildin_api.sandbox_descriptors import (
    SandboxDescriptorError,
    SandboxDescriptorPayload,
    SandboxDescriptorRepository,
    SandboxDescriptorStore,
    safe_audit_metadata,
)
from ithildin_schemas import canonical_json, sha256_digest


def descriptor_payload(**overrides: object) -> SandboxDescriptorPayload:
    payload: dict[str, object] = {
        "workspace_id": "default",
        "principal_id": "agent:repository-test",
        "run_id": "run_11111111111111111111111111111111",
        "sandbox_id": "sandbox-repository",
        "sandbox_profile_id": "profile-repository",
        "vm_profile_hash": "sha256:" + ("1" * 64),
        "isolation_label": "operator-attested-vm",
        "network_posture_label": "host-only",
        "mount_root_label": "sandbox-workspace",
        "model_client_label": "local-llm",
        "descriptor_source": "operator_supplied",
        "vm_lifecycle_source": "operator_managed",
        "isolation_claim_source": "operator_attested",
        "network_posture_source": "operator_attested",
        "mount_posture_source": "operator_attested",
        "model_client_source": "operator_attested",
        "ithildin_live_inspection_performed": False,
        "ithildin_lifecycle_control_performed": False,
        "mission_control_runtime_authority_used": False,
        "trusted_host_promotion_performed": False,
        "approval_id": "ap_11111111111111111111111111111111",
        "audit_event_id": "evt_11111111111111111111111111111111",
        "signed_export_id": "sig_11111111111111111111111111111111",
        "failure_transcript_hash": "sha256:" + ("2" * 64),
        "packet_hash": "sha256:" + ("3" * 64),
        "operator_notes_label": "repository-test",
    }
    payload.update(overrides)
    return SandboxDescriptorPayload.model_validate(payload)


def repository(db_path: Path) -> SandboxDescriptorRepository:
    implementation = SandboxDescriptorStore(db_path)
    implementation.initialize()
    return implementation


def test_sqlite_repository_preserves_record_bytes_hash_and_authority(tmp_path: Path) -> None:
    db_path = tmp_path / "ithildin.db"
    repo = repository(db_path)
    payload = descriptor_payload()

    record = repo.create(payload)
    detail = repo.get(record.descriptor_id)
    authority = repo.authority_record(record.descriptor_id)

    with sqlite3.connect(db_path) as connection:
        persisted = connection.execute(
            """
            SELECT status, created_at, updated_at, payload_hash, payload_json
            FROM sandbox_descriptors
            WHERE descriptor_id = ?
            """,
            (record.descriptor_id,),
        ).fetchone()

    assert persisted is not None
    assert persisted[0] == "accepted"
    assert persisted[1] == record.created_at
    assert persisted[2] == record.updated_at
    assert persisted[3] == sha256_digest(payload.safe_payload())
    assert persisted[4] == canonical_json(payload.safe_payload())
    assert json.loads(str(persisted[4])) == payload.safe_payload()
    assert detail == record.detail()
    assert repo.list(limit=0) == [record.summary()]
    assert repo.status()["count"] == 1
    assert authority.descriptor_id == record.descriptor_id
    assert authority.descriptor_payload_hash == record.payload_hash
    assert authority.descriptor_generation == sha256_digest(
        {
            "descriptor_id": record.descriptor_id,
            "payload_hash": record.payload_hash,
            "created_at": record.created_at,
        }
    )


def test_sqlite_repository_reads_and_extends_an_entry_baseline_database(tmp_path: Path) -> None:
    db_path = tmp_path / "entry-baseline.db"
    payload = descriptor_payload(sandbox_id="sandbox-before-interface")
    safe_payload = payload.safe_payload()
    created_at = "2026-07-20T12:00:00+00:00"
    descriptor_id = "sdesc_" + ("a" * 32)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE sandbox_descriptors (
                descriptor_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX idx_sandbox_descriptors_created_at
            ON sandbox_descriptors(created_at)
            """
        )
        connection.execute(
            """
            INSERT INTO sandbox_descriptors (
                descriptor_id, status, created_at, updated_at, payload_hash, payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                descriptor_id,
                "accepted",
                created_at,
                created_at,
                sha256_digest(safe_payload),
                canonical_json(safe_payload),
            ),
        )
        connection.commit()
        schema_before = connection.execute(
            """
            SELECT type, name, sql
            FROM sqlite_master
            WHERE tbl_name = 'sandbox_descriptors'
            ORDER BY type, name
            """
        ).fetchall()

    repo = repository(db_path)
    existing = repo.get(descriptor_id)
    added = repo.create(descriptor_payload(sandbox_id="sandbox-after-interface"))

    with sqlite3.connect(db_path) as connection:
        schema_after = connection.execute(
            """
            SELECT type, name, sql
            FROM sqlite_master
            WHERE tbl_name = 'sandbox_descriptors'
            ORDER BY type, name
            """
        ).fetchall()

    assert existing["safe_payload"] == safe_payload
    assert repo.get(added.descriptor_id)["sandbox_id"] == "sandbox-after-interface"
    assert schema_after == schema_before
    assert repo.list(limit=1) == [added.summary()]
    assert {item["descriptor_id"] for item in repo.list(limit=200)} == {
        descriptor_id,
        added.descriptor_id,
    }
    with pytest.raises(SandboxDescriptorError, match="sandbox descriptor not found"):
        repo.get("sdesc_" + ("f" * 32))


def test_repository_audit_metadata_is_minimized_and_exact(tmp_path: Path) -> None:
    repo = repository(tmp_path / "ithildin.db")
    record = repo.create(descriptor_payload())

    metadata = safe_audit_metadata(record)

    assert set(metadata) == {
        "descriptor_id",
        "descriptor_status",
        "descriptor_payload_hash",
        "descriptor_source",
        "vm_lifecycle_source",
        "isolation_claim_source",
        "network_posture_source",
        "mount_posture_source",
        "model_client_source",
        "workspace_id",
        "principal_id",
        "run_id",
        "sandbox_id",
        "sandbox_profile_id",
        "ithildin_live_inspection_performed",
        "ithildin_lifecycle_control_performed",
        "mission_control_runtime_authority_used",
        "trusted_host_promotion_performed",
        "output_policy",
    }
    assert "mount_root_label" not in metadata
    assert "failure_transcript_hash" not in metadata
    assert "packet_hash" not in metadata
    output_policy = cast(dict[str, object], metadata["output_policy"])
    excluded_categories = cast(list[object], output_policy["excluded_categories"])
    assert "raw_paths" in excluded_categories

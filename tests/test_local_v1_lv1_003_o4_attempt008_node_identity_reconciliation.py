from __future__ import annotations

import json
import os
import sqlite3
import stat
from pathlib import Path
from typing import Any

import pytest

from scripts import (
    local_v1_lv1_003_o4_attempt008_node_identity_reconciliation as reconciliation,
)

NODE_ID = "node_" + "a" * 32
TIMESTAMP = "2026-07-26T00:20:00+00:00"


def _database(*, status: str = "enrolled", revoked_at: str | None = None) -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE app_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT INTO app_metadata VALUES
            ('schema_version', '4'),
            ('minimum_writer_version', '4');
        CREATE TABLE node_enrollment_codes (
            code_id TEXT,
            code_hash TEXT,
            workspace_id TEXT,
            display_name TEXT,
            created_at TEXT,
            expires_at TEXT,
            consumed_at TEXT,
            consumed_node_id TEXT,
            evidence_status TEXT
        );
        CREATE TABLE nodes (
            node_id TEXT,
            principal_id TEXT,
            workspace_id TEXT,
            display_name TEXT,
            status TEXT,
            evidence_status TEXT,
            public_key TEXT,
            descriptor_hash TEXT,
            descriptor_json TEXT,
            enrolled_at TEXT,
            updated_at TEXT,
            last_seen_at TEXT,
            revoked_at TEXT,
            last_heartbeat_hash TEXT,
            last_node_version TEXT,
            last_configuration_digest TEXT,
            last_mission_id TEXT,
            desired_configuration_generation INTEGER,
            desired_configuration_digest TEXT,
            acknowledged_configuration_generation INTEGER,
            acknowledged_configuration_digest TEXT,
            acknowledged_configuration_signing_key_id TEXT,
            acknowledged_active_configuration_signing_key_id TEXT,
            configuration_acknowledged_at TEXT,
            configuration_acknowledgment_status TEXT
        );
        """
    )
    for table, columns in reconciliation._EXPECTED_TABLE_COLUMNS.items():  # noqa: SLF001
        if table in {"app_metadata", "node_enrollment_codes", "nodes"}:
            continue
        definitions = ", ".join(f"{column} TEXT" for column in columns)
        connection.execute(f"CREATE TABLE {table} ({definitions})")  # noqa: S608
    connection.execute(
        "INSERT INTO node_enrollment_codes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "ncode_fixture",
            "SECRET-ENROLLMENT-CODE-HASH",
            reconciliation.WORKSPACE_ID,
            reconciliation.DISPLAY_NAME,
            TIMESTAMP,
            TIMESTAMP,
            TIMESTAMP,
            NODE_ID,
            "complete",
        ),
    )
    updated_at = revoked_at if status == "revoked" else TIMESTAMP
    connection.execute(
        "INSERT INTO nodes VALUES ("
        + ",".join("?" for _ in range(25))
        + ")",
        (
            NODE_ID,
            f"agent:node.{NODE_ID}",
            reconciliation.WORKSPACE_ID,
            reconciliation.DISPLAY_NAME,
            status,
            "complete",
            "SECRET-PUBLIC-KEY",
            reconciliation.EXPECTED_DESCRIPTOR_DIGEST,
            "SECRET-DESCRIPTOR-JSON",
            TIMESTAMP,
            updated_at,
            None,
            revoked_at,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ),
    )
    connection.commit()
    return connection


def _snapshot(**kwargs: Any) -> bytes:
    connection = _database(**kwargs)
    try:
        return connection.serialize()
    finally:
        connection.close()


def _assert_unresolved(snapshot: bytes | bytearray) -> None:
    with pytest.raises(
        reconciliation.ReconciliationError,
        match="identity_unresolved_reconciliation_required",
    ):
        reconciliation.project_identity(snapshot)


def _write_runtime_database(repo_root: Path, snapshot: bytes) -> Path:
    current = repo_root
    repo_root.mkdir(exist_ok=True)
    os.chmod(repo_root, 0o700)
    for component in reconciliation.RUNTIME_COMPONENTS:
        current = current / component
        current.mkdir(mode=0o700)
    database = current / reconciliation.DATABASE_NAME
    database.write_bytes(snapshot)
    database.chmod(0o600)
    return database


def test_expected_authorization_is_closed_and_six_path() -> None:
    record = reconciliation._expected_authorization()  # noqa: SLF001
    assert record["candidate_path_allowlist"] == reconciliation.CANDIDATE_PATH_ALLOWLIST
    assert len(reconciliation.CANDIDATE_PATH_ALLOWLIST) == 6
    assert record["attempt_budget"] == 1
    assert record["consumed"] is False
    assert record["retry_authorized"] is False
    assert record["successor_o4_authorized"] is False
    assert record["tool_count"] == 24
    assert record["release_allowed"] is False
    assert record["uat_complete"] is False
    assert "docker_access" in record["authority_false"]
    assert "ambient_credential_access" in record["authority_false"]


def test_active_identity_projects_only_bounded_private_fields() -> None:
    projected = reconciliation.project_identity(_snapshot())
    assert projected["classification"] == "identity_bound_active_quarantine_required"
    assert projected["node_id"] == NODE_ID
    assert projected["principal_id"] == f"agent:node.{NODE_ID}"
    assert projected["quarantine_confirmed"] is False
    assert projected["revocation_authorized"] is False
    assert projected["successor_o4_authorized"] is False
    assert projected["release_allowed"] is False
    text = reconciliation.canonical_json(projected)
    assert "SECRET-" not in text
    assert "code_hash" not in text
    assert "public_key" not in text
    assert "descriptor_json" not in text


def test_revoked_identity_projects_without_new_authority() -> None:
    revoked_at = "2026-07-26T00:30:00+00:00"
    projected = reconciliation.project_identity(
        _snapshot(status="revoked", revoked_at=revoked_at)
    )
    assert projected["classification"] == "identity_bound_revoked"
    assert projected["revoked_at"] == revoked_at
    assert projected["cleanup_authorized"] is False
    assert projected["successor_o4_authorized"] is False


def test_revocation_order_compares_timezone_aware_instants() -> None:
    equivalent_offset = "2026-07-25T19:20:00-05:00"
    projected = reconciliation.project_identity(
        _snapshot(status="revoked", revoked_at=equivalent_offset)
    )
    assert projected["classification"] == "identity_bound_revoked"

    _assert_unresolved(
        _snapshot(status="revoked", revoked_at="2026-07-25T19:19:59-05:00")
    )


@pytest.mark.parametrize(
    ("statement", "parameters"),
    [
        (
            "UPDATE node_enrollment_codes SET workspace_id = ?",
            ("other",),
        ),
        (
            "UPDATE node_enrollment_codes SET display_name = ?",
            ("Other Node",),
        ),
        (
            "UPDATE node_enrollment_codes SET evidence_status = ?",
            ("pending",),
        ),
        (
            "UPDATE node_enrollment_codes SET consumed_at = NULL",
            (),
        ),
        (
            "UPDATE node_enrollment_codes SET consumed_node_id = ?",
            ("node_" + "b" * 32,),
        ),
        (
            "UPDATE nodes SET principal_id = ?",
            ("agent:node.wrong",),
        ),
        (
            "UPDATE nodes SET workspace_id = ?",
            ("other",),
        ),
        (
            "UPDATE nodes SET display_name = ?",
            ("Other Node",),
        ),
        (
            "UPDATE nodes SET evidence_status = ?",
            ("pending",),
        ),
        (
            "UPDATE nodes SET descriptor_hash = ?",
            ("sha256:" + "0" * 64,),
        ),
        (
            "UPDATE nodes SET enrolled_at = ?",
            ("2026-07-26T00:20:01+00:00",),
        ),
        (
            "UPDATE nodes SET last_seen_at = ?",
            (TIMESTAMP,),
        ),
        (
            "UPDATE nodes SET desired_configuration_generation = 1",
            (),
        ),
        (
            "UPDATE nodes SET last_mission_id = ?",
            ("mission_" + "a" * 32,),
        ),
    ],
)
def test_identity_mismatches_fail_closed(
    statement: str, parameters: tuple[object, ...]
) -> None:
    connection = _database()
    connection.execute(statement, parameters)
    connection.commit()
    snapshot = connection.serialize()
    connection.close()
    _assert_unresolved(snapshot)


def test_zero_or_multiple_identity_rows_fail_closed() -> None:
    connection = _database()
    connection.execute("DELETE FROM nodes")
    connection.commit()
    _assert_unresolved(connection.serialize())
    connection.close()

    connection = _database()
    connection.execute(
        "INSERT INTO node_enrollment_codes SELECT * FROM node_enrollment_codes"
    )
    connection.commit()
    _assert_unresolved(connection.serialize())
    connection.close()


@pytest.mark.parametrize(
    ("table", "column"),
    [
        ("node_nonces", "node_id"),
        ("node_identity_key_rotations", "node_id"),
        ("node_configurations", "node_id"),
        ("node_configuration_trust_transitions", "node_id"),
        ("missions", "target_node_id"),
        ("mission_audit_evidence_bindings", "owner_id"),
        ("mission_transition_attempts", "mission_id"),
        ("mission_claims", "node_id"),
        ("mission_report_receipts", "node_id"),
        ("mission_report_nonces", "node_id"),
    ],
)
def test_any_attempt_node_activity_fails_closed(table: str, column: str) -> None:
    connection = _database()
    columns = [
        str(row[1])
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    ]
    values: list[object] = []
    for name in columns:
        if name == column:
            values.append(NODE_ID)
        elif "nonce" in name:
            values.append("a" * 32)
        elif "rotation_id" in name:
            values.append("nkr_" + "a" * 32)
        else:
            values.append("{}")
    connection.execute(
        f"INSERT INTO {table} VALUES ({','.join('?' for _ in values)})",
        values,
    )
    connection.commit()
    _assert_unresolved(connection.serialize())
    connection.close()


def test_schema_metadata_and_corruption_fail_closed() -> None:
    connection = _database()
    connection.execute(
        "UPDATE app_metadata SET value = '5' WHERE key = 'schema_version'"
    )
    connection.commit()
    _assert_unresolved(connection.serialize())
    connection.close()
    _assert_unresolved(b"not a sqlite database")


def test_added_removed_and_reordered_schema_columns_fail_closed() -> None:
    connection = _database()
    connection.execute("ALTER TABLE nodes ADD COLUMN unexpected TEXT")
    connection.commit()
    _assert_unresolved(connection.serialize())
    connection.close()

    connection = _database()
    connection.execute("ALTER TABLE nodes DROP COLUMN last_seen_at")
    connection.commit()
    _assert_unresolved(connection.serialize())
    connection.close()

    connection = _database()
    connection.execute("ALTER TABLE nodes RENAME TO nodes_original")
    reordered = list(
        reconciliation._EXPECTED_TABLE_COLUMNS["nodes"]  # noqa: SLF001
    )
    first = reordered.index("last_seen_at")
    second = reordered.index("revoked_at")
    reordered[first], reordered[second] = reordered[second], reordered[first]
    definitions = ", ".join(f"{column} TEXT" for column in reordered)
    connection.execute(f"CREATE TABLE nodes ({definitions})")  # noqa: S608
    columns = ", ".join(reordered)
    connection.execute(  # noqa: S608
        f"INSERT INTO nodes ({columns}) SELECT {columns} FROM nodes_original"
    )
    connection.execute("DROP TABLE nodes_original")
    connection.commit()
    _assert_unresolved(connection.serialize())
    connection.close()

    connection = _database()
    connection.execute("DROP TABLE node_nonces")
    connection.execute(
        "CREATE VIEW node_nonces AS "
        "SELECT NULL AS node_id, NULL AS nonce, NULL AS accepted_at WHERE 0"
    )
    connection.commit()
    _assert_unresolved(connection.serialize())
    connection.close()


def test_authorizer_denies_secret_columns_writes_and_unrelated_tables() -> None:
    connection = _database()
    snapshot = connection.serialize()
    connection.close()
    projected = sqlite3.connect(":memory:")
    projected.deserialize(snapshot)
    projected.set_authorizer(reconciliation._projection_authorizer)  # noqa: SLF001
    for statement in (
        "SELECT code_hash FROM node_enrollment_codes",
        "SELECT public_key FROM nodes",
        "SELECT descriptor_json FROM nodes",
        "UPDATE nodes SET status = 'revoked'",
        "PRAGMA writable_schema = ON",
        "SELECT name FROM sqlite_master",
    ):
        with pytest.raises(sqlite3.DatabaseError):
            projected.execute(statement).fetchall()
    projected.close()


def test_descriptor_snapshot_is_stable_and_sidecar_free(tmp_path: Path) -> None:
    database = _write_runtime_database(tmp_path, _snapshot())
    before = database.read_bytes()
    observed = reconciliation._read_database_snapshot(tmp_path)  # noqa: SLF001
    assert bytes(observed) == before
    assert database.read_bytes() == before

    sidecar = database.with_name(database.name + "-wal")
    sidecar.write_bytes(b"forbidden")
    with pytest.raises(
        reconciliation.ReconciliationError,
        match="identity_unresolved_reconciliation_required",
    ):
        reconciliation._read_database_snapshot(tmp_path)  # noqa: SLF001


def test_descriptor_snapshot_rejects_symlink_and_hardlink(tmp_path: Path) -> None:
    database = _write_runtime_database(tmp_path / "symlink", _snapshot())
    real = database.with_name("real.sqlite3")
    database.rename(real)
    database.symlink_to(real.name)
    with pytest.raises(reconciliation.ReconciliationError):
        reconciliation._read_database_snapshot(tmp_path / "symlink")  # noqa: SLF001

    database = _write_runtime_database(tmp_path / "hardlink", _snapshot())
    os.link(database, database.with_name("second-link.sqlite3"))
    with pytest.raises(reconciliation.ReconciliationError):
        reconciliation._read_database_snapshot(tmp_path / "hardlink")  # noqa: SLF001


def test_descriptor_snapshot_rejects_fifo_leaf_without_blocking(
    tmp_path: Path,
) -> None:
    assert reconciliation._OPEN_FILE_FLAGS & os.O_NONBLOCK  # noqa: SLF001
    current = tmp_path
    tmp_path.mkdir(exist_ok=True)
    os.chmod(tmp_path, 0o700)
    for component in reconciliation.RUNTIME_COMPONENTS:
        current = current / component
        current.mkdir(mode=0o700)
    os.mkfifo(current / reconciliation.DATABASE_NAME, 0o600)
    with pytest.raises(
        reconciliation.ReconciliationError,
        match="identity_unresolved_reconciliation_required",
    ):
        reconciliation._read_database_snapshot(tmp_path)  # noqa: SLF001


def test_descriptor_snapshot_rejects_lexical_leaf_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = _write_runtime_database(tmp_path, _snapshot())
    real_read = os.read
    swapped = False

    def swapping_read(descriptor: int, size: int) -> bytes:
        nonlocal swapped
        block = real_read(descriptor, size)
        if block and not swapped:
            swapped = True
            displaced = database.with_name("displaced.sqlite3")
            database.rename(displaced)
            database.write_bytes(_snapshot())
            database.chmod(0o600)
        return block

    monkeypatch.setattr(reconciliation.os, "read", swapping_read)
    with pytest.raises(
        reconciliation.ReconciliationError,
        match="identity_unresolved_reconciliation_required",
    ):
        reconciliation._read_database_snapshot(tmp_path)  # noqa: SLF001


def test_consume_budget_is_owner_only_and_one_shot(tmp_path: Path) -> None:
    os.chmod(tmp_path, 0o700)
    receipt_fd, held = reconciliation.consume_budget(
        tmp_path,
        candidate_commit="a" * 40,
        candidate_tree="b" * 40,
    )
    try:
        root = (
            tmp_path
            / "var/local-v1-lv1-003-o4-reconciliation-receipts"
            / reconciliation.RECEIPT_DIRECTORY
        )
        consumed = root / reconciliation.CONSUMED_RECEIPT
        assert stat.S_IMODE(root.stat().st_mode) == 0o700
        assert stat.S_IMODE(consumed.stat().st_mode) == 0o600
        record = json.loads(consumed.read_text(encoding="utf-8"))
        assert record["consumed_before_database_open"] is True
        assert record["attempt_budget"] == 0
        assert record["retry_authorized"] is False
        assert receipt_fd >= 0
    finally:
        for descriptor in reversed(held):
            os.close(descriptor)
    with pytest.raises(
        reconciliation.ReconciliationError,
        match="attempt_budget_already_consumed",
    ):
        reconciliation.consume_budget(
            tmp_path,
            candidate_commit="a" * 40,
            candidate_tree="b" * 40,
        )


def test_run_live_refuses_before_consumption_or_database_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        reconciliation,
        "build_report",
        lambda _root: {
            "static_candidate_valid": False,
            "execution_available": False,
        },
    )
    monkeypatch.setattr(
        reconciliation,
        "consume_budget",
        lambda *_args, **_kwargs: pytest.fail("consumption reached"),
    )
    monkeypatch.setattr(
        reconciliation,
        "_read_database_snapshot",
        lambda _root: pytest.fail("database reached"),
    )
    with pytest.raises(
        reconciliation.ReconciliationError,
        match="identity_reconciliation_not_authorized",
    ):
        reconciliation.run_live(tmp_path)


def test_run_live_writes_private_result_and_returns_secret_free_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    os.chmod(tmp_path, 0o700)
    monkeypatch.setattr(
        reconciliation,
        "build_report",
        lambda _root: {
            "static_candidate_valid": True,
            "execution_available": True,
            "candidate_commit": "a" * 40,
            "candidate_tree": "b" * 40,
        },
    )
    monkeypatch.setattr(
        reconciliation,
        "_read_database_snapshot",
        lambda _root: bytearray(_snapshot()),
    )
    public = reconciliation.run_live(tmp_path)
    assert public["classification"] == "identity_bound_active_quarantine_required"
    assert "node_id" not in public
    assert NODE_ID not in reconciliation.canonical_json(public)
    result_path = (
        tmp_path
        / "var/local-v1-lv1-003-o4-reconciliation-receipts"
        / reconciliation.RECEIPT_DIRECTORY
        / reconciliation.RESULT_RECEIPT
    )
    assert stat.S_IMODE(result_path.stat().st_mode) == 0o600
    private = json.loads(result_path.read_text(encoding="utf-8"))
    assert private["node_id"] == NODE_ID
    assert private["successor_o4_authorized"] is False


def test_public_main_never_prints_raw_node_id(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        reconciliation,
        "run_live",
        lambda: {
            "classification": "identity_bound_active_quarantine_required",
        },
    )
    assert reconciliation.main([]) == 0
    output = capsys.readouterr().out
    assert "identity_bound_active_quarantine_required" in output
    assert NODE_ID not in output


def test_source_has_no_broad_access_or_mutation_vocabulary() -> None:
    source = (reconciliation.ROOT / reconciliation.SCRIPT_PATH).read_text(
        encoding="utf-8"
    )
    for forbidden in (
        "os.listdir",
        "os.scandir",
        ".iterdir(",
        "docker ",
        "docker\"",
        "requests.",
        "urllib.",
        "socket.",
        "subprocess.Popen",
        "UPDATE nodes",
        "DELETE FROM",
        "compose.env",
    ):
        assert forbidden not in source

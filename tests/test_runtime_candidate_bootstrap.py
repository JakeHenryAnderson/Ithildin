from __future__ import annotations

import hashlib
import json
import sys
import types
from datetime import UTC, datetime
from pathlib import Path

import pytest
from runtime_candidate_bootstrap import (
    RuntimeCandidateVerificationError,
    verify_runtime_candidate,
)

from scripts.runtime_candidate_authorization_record import (
    AuthorizationRecordError,
    build_authorization_record,
    write_authorization_record,
)


def test_runtime_candidate_verifies_detached_closed_evidence(tmp_path: Path) -> None:
    root, inventory_path, authorization_path = _candidate_fixture(tmp_path)

    verified = verify_runtime_candidate(
        package_root=root,
        inventory_path=inventory_path,
        authorization_path=authorization_path,
        allow_test_paths=True,
    )

    assert verified["posture"] == "reviewed"
    assert verified["candidate_id"].startswith("sha256:")
    assert verified["authorization_id"].startswith("rca_")


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("file", "file digest mismatch"),
        ("authorization", "record hash mismatch"),
        ("writable", "authorization is writable"),
    ],
)
def test_runtime_candidate_rejects_drift_and_writable_authority(
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    root, inventory_path, authorization_path = _candidate_fixture(tmp_path)
    if mutation == "file":
        runtime_file = root / "apps" / "runtime.py"
        runtime_file.chmod(0o644)
        runtime_file.write_text("changed\n", encoding="utf-8")
        runtime_file.chmod(0o444)
    elif mutation == "authorization":
        payload = json.loads(authorization_path.read_text(encoding="utf-8"))
        payload["reviewed_commit"] = "2" * 40
        authorization_path.chmod(0o600)
        authorization_path.write_text(json.dumps(payload), encoding="utf-8")
        authorization_path.chmod(0o444)
    else:
        authorization_path.chmod(0o644)

    with pytest.raises(RuntimeCandidateVerificationError, match=message):
        verify_runtime_candidate(
            package_root=root,
            inventory_path=inventory_path,
            authorization_path=authorization_path,
            allow_test_paths=True,
        )


def test_authorization_record_requires_matching_packet_and_create_exclusive_output(
    tmp_path: Path,
) -> None:
    root, inventory_path, _ = _candidate_fixture(tmp_path, create_authorization=False)
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    packet = tmp_path / "review-packet.json"
    packet.write_text(json.dumps({"candidate_id": inventory["candidate_id"]}), encoding="utf-8")
    inventory["review_packet_digest"] = _file_digest(packet)
    inventory_path.chmod(0o644)
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")

    record = build_authorization_record(
        candidate_manifest_path=inventory_path,
        review_packet_path=packet,
        repo_root=root,
        require_clean_git=False,
        authorized_at=datetime(2026, 7, 18, tzinfo=UTC),
    )
    output = tmp_path / "runtime-authority" / "api-candidate.json"
    write_authorization_record(output, record)

    assert output.stat().st_mode & 0o222 == 0
    with pytest.raises(AuthorizationRecordError, match="already exists"):
        write_authorization_record(output, record)


def test_verified_launcher_verifies_before_importing_app(monkeypatch: pytest.MonkeyPatch) -> None:
    import verified_launch as launcher

    sys.modules.pop("ithildin_api.app", None)
    observed: list[str] = []

    def verify() -> dict[str, str]:
        assert "ithildin_api.app" not in sys.modules
        observed.append("verified")
        fake_app = types.ModuleType("ithildin_api.app")
        fake_app.create_app = lambda **_kwargs: "app"  # type: ignore[attr-defined]
        sys.modules["ithildin_api.app"] = fake_app
        return _verified_payload()

    fake_authority = types.ModuleType("ithildin_api.promotion_authority")

    class Candidate:
        @classmethod
        def model_validate(cls, _payload: object) -> object:
            observed.append("candidate")
            return object()

    fake_authority.RuntimeCandidateRecord = Candidate  # type: ignore[attr-defined]
    fake_uvicorn = types.ModuleType("uvicorn")
    fake_uvicorn.run = lambda *_args, **_kwargs: observed.append("run")  # type: ignore[attr-defined]
    monkeypatch.setattr(launcher, "verify_from_environment", verify)
    monkeypatch.setitem(sys.modules, "ithildin_api.promotion_authority", fake_authority)
    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)

    assert launcher.main() == 0
    assert observed == ["verified", "candidate", "run"]


def _candidate_fixture(
    tmp_path: Path,
    *,
    create_authorization: bool = True,
) -> tuple[Path, Path, Path]:
    root = tmp_path / "package"
    (root / "apps").mkdir(parents=True)
    runtime_file = root / "apps" / "runtime.py"
    runtime_file.write_text("safe = True\n", encoding="utf-8")
    lock = root / "uv.lock"
    lock.write_text("lock\n", encoding="utf-8")
    files = [
        {"path": "apps/runtime.py", "sha256": _file_digest(runtime_file)},
        {"path": "uv.lock", "sha256": _file_digest(lock)},
    ]
    inventory_core = {"schema_version": "1", "files": files}
    reviewed_inventory_digest = _json_digest(inventory_core)
    packet_digest = "sha256:" + ("d" * 64)
    candidate_core = {
        "source_commit": "1" * 40,
        "inventory_schema_version": "1",
        "reviewed_inventory_digest": reviewed_inventory_digest,
        "dependency_lock_digest": _file_digest(lock),
        "release_artifact_digest": "sha256:" + ("c" * 64),
        "evidence_schema_version": "1",
    }
    candidate_id = _json_digest(candidate_core)
    inventory = {
        "schema_version": "1",
        "source_commit": "1" * 40,
        "files": files,
        "dependency_lock_path": "uv.lock",
        "dependency_lock_digest": _file_digest(lock),
        "release_artifact_digest": "sha256:" + ("c" * 64),
        "review_packet_digest": packet_digest,
        "evidence_schema_version": "1",
        "reviewed_inventory_digest": reviewed_inventory_digest,
        "candidate_id": candidate_id,
    }
    inventory_path = root / "runtime-candidate-inventory.json"
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
    runtime_file.chmod(0o444)
    lock.chmod(0o444)
    inventory_path.chmod(0o444)
    root.chmod(0o555)
    authorization_path = tmp_path / "runtime-authority" / "api-candidate.json"
    if create_authorization:
        authorization_path.parent.mkdir()
        record = {
            "authorization_id": "rca_" + ("a" * 32),
            "candidate_id": candidate_id,
            "reviewed_commit": "1" * 40,
            "inventory_schema_version": "1",
            "reviewed_inventory_digest": reviewed_inventory_digest,
            "dependency_lock_digest": _file_digest(lock),
            "release_artifact_digest": "sha256:" + ("c" * 64),
            "review_packet_digest": packet_digest,
            "evidence_schema_version": "1",
            "authorized_at": "2026-07-18T00:00:00+00:00",
        }
        record["record_hash"] = _json_digest(record)
        authorization_path.write_text(json.dumps(record), encoding="utf-8")
        authorization_path.chmod(0o444)
    return root, inventory_path, authorization_path


def _verified_payload() -> dict[str, str]:
    return {
        "posture": "reviewed",
        "candidate_id": "sha256:" + ("a" * 64),
        "source_commit": "1" * 40,
        "inventory_schema_version": "1",
        "reviewed_inventory_digest": "sha256:" + ("b" * 64),
        "dependency_lock_digest": "sha256:" + ("c" * 64),
        "release_artifact_digest": "sha256:" + ("d" * 64),
        "review_packet_digest": "sha256:" + ("e" * 64),
        "evidence_schema_version": "1",
        "authorization_id": "rca_test",
    }


def _file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _json_digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()

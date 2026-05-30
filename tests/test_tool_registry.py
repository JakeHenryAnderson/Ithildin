from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from ithildin_api.manifest_lock import (
    ManifestLockError,
    ManifestLockRecord,
    generate_manifest_lock_signing_keypair,
    manifest_lock_signature_status,
    verify_manifest_lock_signature,
    write_manifest_lock,
    write_manifest_lock_signature,
)
from ithildin_api.registry import (
    DuplicateToolManifest,
    InvalidToolManifest,
    ToolRegistry,
    UnknownToolDenied,
)


def write_manifest(path: Path, name: str = "fs.read") -> None:
    path.write_text(
        f"""
name: {name}
version: 1.0.0
title: Read file
risk: read
category: filesystem
mcp:
  exposed: true
input_schema:
  type: object
  required: ["path"]
  properties:
    path:
      type: string
""",
        encoding="utf-8",
    )


def test_empty_manifest_directory_loads_empty_registry(tmp_path: Path) -> None:
    registry = ToolRegistry.load(tmp_path)

    assert registry.list_tools() == []


def test_valid_yaml_manifest_loads_tool(tmp_path: Path) -> None:
    write_manifest(tmp_path / "fs-read.yaml")

    registry = ToolRegistry.load(tmp_path)
    tools = registry.list_tools()

    assert len(tools) == 1
    assert tools[0].manifest.name == "fs.read"
    assert tools[0].manifest.version == "1.0.0"
    assert tools[0].manifest_hash.startswith("sha256:")


def test_manifest_hash_is_stable(tmp_path: Path) -> None:
    write_manifest(tmp_path / "fs-read.yaml")

    first_registry = ToolRegistry.load(tmp_path)
    second_registry = ToolRegistry.load(tmp_path)

    assert first_registry.get_tool("fs.read").manifest_hash == second_registry.get_tool(
        "fs.read"
    ).manifest_hash


def test_invalid_yaml_fails_closed(tmp_path: Path) -> None:
    (tmp_path / "broken.yaml").write_text("name: [", encoding="utf-8")

    with pytest.raises(InvalidToolManifest):
        ToolRegistry.load(tmp_path)


def test_invalid_manifest_schema_fails_closed(tmp_path: Path) -> None:
    (tmp_path / "invalid.yaml").write_text("name: fs.read\n", encoding="utf-8")

    with pytest.raises(InvalidToolManifest):
        ToolRegistry.load(tmp_path)


def test_duplicate_tool_names_fail_closed(tmp_path: Path) -> None:
    write_manifest(tmp_path / "one.yaml", name="fs.read")
    write_manifest(tmp_path / "two.yml", name="fs.read")

    with pytest.raises(DuplicateToolManifest):
        ToolRegistry.load(tmp_path)


def test_non_manifest_files_are_ignored(tmp_path: Path) -> None:
    (tmp_path / ".gitkeep").write_text("", encoding="utf-8")

    registry = ToolRegistry.load(tmp_path)

    assert registry.list_tools() == []


def test_unknown_tool_lookup_has_audit_ready_denial_metadata(tmp_path: Path) -> None:
    registry = ToolRegistry.load(tmp_path)

    with pytest.raises(UnknownToolDenied) as exc_info:
        registry.get_tool("fs.missing")

    assert exc_info.value.audit_metadata == {
        "event_type": "tool.call.denied",
        "tool_name": "fs.missing",
        "decision": "deny",
        "reason": "unknown tool",
    }


def test_committed_read_tool_manifests_load() -> None:
    registry = ToolRegistry.load(
        Path("tool-manifests"),
        lock_path=Path("tool-manifests.lock.json"),
        require_lock=True,
    )

    assert [tool.manifest.name for tool in registry.list_tools()] == [
        "fs.list",
        "fs.patch.apply",
        "fs.patch.propose",
        "fs.read",
        "fs.search",
        "fs.stat",
        "git.diff",
        "git.log",
        "git.status",
        "http.fetch",
    ]


def test_manifest_lock_generation_is_deterministic(tmp_path: Path) -> None:
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    write_manifest(manifest_dir / "fs-read.yaml")
    lock_path = tmp_path / "tool-manifests.lock.json"
    registry = ToolRegistry.load(manifest_dir)
    records = _lock_records(registry)

    write_manifest_lock(manifest_dir=manifest_dir, lock_path=lock_path, records=records)
    first = lock_path.read_text(encoding="utf-8")
    write_manifest_lock(manifest_dir=manifest_dir, lock_path=lock_path, records=records)
    second = lock_path.read_text(encoding="utf-8")

    assert first == second
    assert '"manifest_hash": "sha256:' in first


def test_valid_manifest_lock_allows_registry_load(tmp_path: Path) -> None:
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    write_manifest(manifest_dir / "fs-read.yaml")
    lock_path = tmp_path / "tool-manifests.lock.json"
    registry = ToolRegistry.load(manifest_dir)
    write_manifest_lock(
        manifest_dir=manifest_dir,
        lock_path=lock_path,
        records=_lock_records(registry),
    )

    locked_registry = ToolRegistry.load(manifest_dir, lock_path=lock_path, require_lock=True)

    assert [tool.manifest.name for tool in locked_registry.list_tools()] == ["fs.read"]


def test_manifest_lock_signature_generation_and_verification(tmp_path: Path) -> None:
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    write_manifest(manifest_dir / "fs-read.yaml")
    lock_path = tmp_path / "tool-manifests.lock.json"
    registry = ToolRegistry.load(manifest_dir)
    write_manifest_lock(
        manifest_dir=manifest_dir,
        lock_path=lock_path,
        records=_lock_records(registry),
    )
    private_key_path = tmp_path / "keys" / "private.pem"
    public_key_path = tmp_path / "keys" / "public.pem"
    signature_path = tmp_path / "signatures" / "tool-manifests.lock.sig.json"

    key_id = generate_manifest_lock_signing_keypair(
        private_key_path=private_key_path,
        public_key_path=public_key_path,
    )
    bundle = cast(
        dict[str, Any],
        write_manifest_lock_signature(
            lock_path=lock_path,
            signature_path=signature_path,
            private_key_path=private_key_path,
            public_key_path=public_key_path,
        ),
    )
    result = verify_manifest_lock_signature(
        lock_path=lock_path,
        signature_path=signature_path,
        public_key_path=public_key_path,
    )

    assert bundle["signature_type"] == "ithildin.manifest_lock.signature"
    assert bundle["format_version"] == "1"
    assert bundle["lock_sha256"].startswith("sha256:")
    assert bundle["signature"]["algorithm"] == "ed25519"
    assert bundle["signature"]["key_id"] == key_id
    assert result.valid is True
    assert result.key_id == key_id


def test_signed_manifest_lock_allows_registry_load(tmp_path: Path) -> None:
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    write_manifest(manifest_dir / "fs-read.yaml")
    lock_path = tmp_path / "tool-manifests.lock.json"
    registry = ToolRegistry.load(manifest_dir)
    write_manifest_lock(
        manifest_dir=manifest_dir,
        lock_path=lock_path,
        records=_lock_records(registry),
    )
    private_key_path = tmp_path / "private.pem"
    public_key_path = tmp_path / "public.pem"
    signature_path = tmp_path / "tool-manifests.lock.sig.json"
    generate_manifest_lock_signing_keypair(
        private_key_path=private_key_path,
        public_key_path=public_key_path,
    )
    write_manifest_lock_signature(
        lock_path=lock_path,
        signature_path=signature_path,
        private_key_path=private_key_path,
        public_key_path=public_key_path,
    )

    locked_registry = ToolRegistry.load(
        manifest_dir,
        lock_path=lock_path,
        require_lock=True,
        signature_path=signature_path,
        signature_public_key_path=public_key_path,
        require_signed_lock=True,
    )

    assert [tool.manifest.name for tool in locked_registry.list_tools()] == ["fs.read"]


@pytest.mark.parametrize(
    "tamper",
    ["lock", "signature", "public_key", "key_id", "wrong_public_key_file", "missing_signature"],
)
def test_manifest_lock_signature_tampering_fails_closed(tmp_path: Path, tamper: str) -> None:
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    write_manifest(manifest_dir / "fs-read.yaml")
    lock_path = tmp_path / "tool-manifests.lock.json"
    registry = ToolRegistry.load(manifest_dir)
    write_manifest_lock(
        manifest_dir=manifest_dir,
        lock_path=lock_path,
        records=_lock_records(registry),
    )
    private_key_path = tmp_path / "private.pem"
    public_key_path = tmp_path / "public.pem"
    signature_path = tmp_path / "tool-manifests.lock.sig.json"
    generate_manifest_lock_signing_keypair(
        private_key_path=private_key_path,
        public_key_path=public_key_path,
    )
    write_manifest_lock_signature(
        lock_path=lock_path,
        signature_path=signature_path,
        private_key_path=private_key_path,
        public_key_path=public_key_path,
    )
    if tamper == "lock":
        write_manifest(manifest_dir / "fs-stat.yaml", name="fs.stat")
        write_manifest_lock(
            manifest_dir=manifest_dir,
            lock_path=lock_path,
            records=_lock_records(ToolRegistry.load(manifest_dir)),
        )
    elif tamper == "wrong_public_key_file":
        generate_manifest_lock_signing_keypair(
            private_key_path=tmp_path / "wrong-private.pem",
            public_key_path=public_key_path,
            overwrite=True,
        )
    elif tamper == "missing_signature":
        signature_path.unlink()
    else:
        payload = cast(dict[str, Any], json.loads(signature_path.read_text(encoding="utf-8")))
        if tamper == "signature":
            payload["signature"]["signature"] = "AA" + payload["signature"]["signature"][2:]
        elif tamper == "public_key":
            payload["signature"]["public_key"] = "AA" + payload["signature"]["public_key"][2:]
        else:
            payload["signature"]["key_id"] = "sha256:" + ("b" * 64)
        signature_path.write_text(
            json.dumps(payload, sort_keys=True),
            encoding="utf-8",
        )

    result = verify_manifest_lock_signature(
        lock_path=lock_path,
        signature_path=signature_path,
        public_key_path=public_key_path,
    )

    assert result.valid is False
    with pytest.raises(ManifestLockError):
        ToolRegistry.load(
            manifest_dir,
            lock_path=lock_path,
            require_lock=True,
            signature_path=signature_path,
            signature_public_key_path=public_key_path,
            require_signed_lock=True,
        )


def test_manifest_lock_signature_cannot_be_replayed_for_different_lock_path(
    tmp_path: Path,
) -> None:
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    write_manifest(manifest_dir / "fs-read.yaml")
    lock_path = tmp_path / "tool-manifests.lock.json"
    replay_lock_path = tmp_path / "copy" / "tool-manifests.lock.json"
    replay_lock_path.parent.mkdir()
    registry = ToolRegistry.load(manifest_dir)
    write_manifest_lock(
        manifest_dir=manifest_dir,
        lock_path=lock_path,
        records=_lock_records(registry),
    )
    replay_lock_path.write_text(lock_path.read_text(encoding="utf-8"), encoding="utf-8")
    private_key_path = tmp_path / "private.pem"
    public_key_path = tmp_path / "public.pem"
    signature_path = tmp_path / "tool-manifests.lock.sig.json"
    generate_manifest_lock_signing_keypair(
        private_key_path=private_key_path,
        public_key_path=public_key_path,
    )
    write_manifest_lock_signature(
        lock_path=lock_path,
        signature_path=signature_path,
        private_key_path=private_key_path,
        public_key_path=public_key_path,
    )

    result = verify_manifest_lock_signature(
        lock_path=replay_lock_path,
        signature_path=signature_path,
        public_key_path=public_key_path,
    )

    assert result.valid is False
    assert result.failure == "manifest lock signature targets a different lock path"


def test_manifest_lock_signature_status_reports_optional_and_verified(tmp_path: Path) -> None:
    lock_path = tmp_path / "tool-manifests.lock.json"
    write_manifest_lock(
        manifest_dir=tmp_path / "missing-manifests",
        lock_path=lock_path,
        records=[],
    )
    signature_path = tmp_path / "missing-signature.json"
    public_key_path = tmp_path / "missing-public.pem"

    status = manifest_lock_signature_status(
        lock_path=lock_path,
        signature_path=signature_path,
        public_key_path=public_key_path,
        required=False,
    )

    assert status == {
        "required": False,
        "signature_path": signature_path.as_posix(),
        "public_key_configured": False,
        "signature_configured": False,
        "verified": False,
        "key_id": None,
    }


def test_missing_manifest_lock_fails_closed(tmp_path: Path) -> None:
    write_manifest(tmp_path / "fs-read.yaml")

    with pytest.raises(ManifestLockError, match="not found"):
        ToolRegistry.load(
            tmp_path,
            lock_path=tmp_path / "missing.lock.json",
            require_lock=True,
        )


def test_manifest_missing_from_lock_fails_closed(tmp_path: Path) -> None:
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    write_manifest(manifest_dir / "fs-read.yaml")
    lock_path = tmp_path / "tool-manifests.lock.json"
    registry = ToolRegistry.load(manifest_dir)
    write_manifest_lock(
        manifest_dir=manifest_dir,
        lock_path=lock_path,
        records=_lock_records(registry),
    )
    write_manifest(manifest_dir / "fs-stat.yaml", name="fs.stat")

    with pytest.raises(ManifestLockError, match="missing from lock"):
        ToolRegistry.load(manifest_dir, lock_path=lock_path, require_lock=True)


def test_stale_manifest_lock_entry_fails_closed(tmp_path: Path) -> None:
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    manifest_path = manifest_dir / "fs-read.yaml"
    write_manifest(manifest_path)
    lock_path = tmp_path / "tool-manifests.lock.json"
    registry = ToolRegistry.load(manifest_dir)
    write_manifest_lock(
        manifest_dir=manifest_dir,
        lock_path=lock_path,
        records=_lock_records(registry),
    )
    manifest_path.unlink()

    with pytest.raises(ManifestLockError, match="stale"):
        ToolRegistry.load(manifest_dir, lock_path=lock_path, require_lock=True)


def test_manifest_lock_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    manifest_path = manifest_dir / "fs-read.yaml"
    write_manifest(manifest_path)
    lock_path = tmp_path / "tool-manifests.lock.json"
    registry = ToolRegistry.load(manifest_dir)
    write_manifest_lock(
        manifest_dir=manifest_dir,
        lock_path=lock_path,
        records=_lock_records(registry),
    )
    manifest_path.write_text(
        manifest_path.read_text(encoding="utf-8").replace("Read file", "Tampered read file"),
        encoding="utf-8",
    )

    with pytest.raises(ManifestLockError, match="hash mismatch"):
        ToolRegistry.load(manifest_dir, lock_path=lock_path, require_lock=True)


def _lock_records(registry: ToolRegistry) -> list[ManifestLockRecord]:
    return [
        ManifestLockRecord(
            path=tool.source_path,
            name=tool.manifest.name,
            version=tool.manifest.version,
            manifest_hash=tool.manifest_hash,
        )
        for tool in registry.list_tools()
    ]

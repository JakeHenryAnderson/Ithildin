from __future__ import annotations

import copy
import os
import stat
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from ithildin_node import release_artifact as release_module
from ithildin_node.release_artifact import (
    NodeReleaseArtifactError,
    generate_node_release_signing_keypair,
    sign_node_release_artifact,
    verify_node_release_artifact,
)
from ithildin_schemas import JsonObject


def test_signed_node_release_artifact_binds_clean_source_and_local_image(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, commit = _source_checkout(tmp_path)
    private_key = tmp_path / "keys/private.pem"
    public_key = tmp_path / "keys/public.pem"
    key_id = generate_node_release_signing_keypair(private_key, public_key)
    inspection = _inspection(commit)
    monkeypatch.setattr(release_module, "inspect_node_image", lambda _image: inspection)

    bundle = sign_node_release_artifact(
        image_reference="ithildin/node:0.1.0",
        node_version="0.1.0",
        source_root=source,
        dockerfile_path=source / "deploy/Dockerfile.node",
        lockfile_path=source / "uv.lock",
        private_key_path=private_key,
        public_key_path=public_key,
        now=datetime(2026, 7, 16, 12, 0, tzinfo=UTC),
    )
    result = verify_node_release_artifact(
        bundle,
        public_key_path=public_key,
        expected_image_reference="ithildin/node:0.1.0",
    )

    assert result.valid is True
    assert result.key_id == key_id
    assert result.image_id == "sha256:" + ("a" * 64)
    assert result.source_commit == commit
    assert result.safe_summary()["gateway_enforcement"] is False
    assert result.safe_summary()["self_update_authority"] is False
    assert stat.S_IMODE(private_key.stat().st_mode) == 0o600
    assert stat.S_IMODE(public_key.stat().st_mode) == 0o644


def test_node_release_artifact_rejects_tamper_wrong_selection_and_wrong_local_image(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, commit = _source_checkout(tmp_path)
    private_key = tmp_path / "keys/private.pem"
    public_key = tmp_path / "keys/public.pem"
    generate_node_release_signing_keypair(private_key, public_key)
    inspection = _inspection(commit)
    monkeypatch.setattr(release_module, "inspect_node_image", lambda _image: inspection)
    bundle = sign_node_release_artifact(
        image_reference="ithildin/node:0.1.0",
        node_version="0.1.0",
        source_root=source,
        dockerfile_path=source / "deploy/Dockerfile.node",
        lockfile_path=source / "uv.lock",
        private_key_path=private_key,
        public_key_path=public_key,
    )
    tampered = copy.deepcopy(bundle)
    artifact = tampered["artifact"]
    assert isinstance(artifact, dict)
    artifact["node_version"] = "0.1.1"

    assert verify_node_release_artifact(
        tampered,
        public_key_path=public_key,
        expected_image_reference="ithildin/node:0.1.0",
    ).valid is False
    wrong_selection = verify_node_release_artifact(
        bundle,
        public_key_path=public_key,
        expected_image_reference="ithildin/node:0.2.0",
    )
    assert wrong_selection.valid is False
    assert wrong_selection.failure == "signed Node image reference does not match selection"
    wrong_inspection = copy.deepcopy(inspection)
    wrong_inspection["Id"] = "sha256:" + ("b" * 64)
    monkeypatch.setattr(release_module, "inspect_node_image", lambda _image: wrong_inspection)
    wrong_local = verify_node_release_artifact(
        bundle,
        public_key_path=public_key,
        expected_image_reference="ithildin/node:0.1.0",
    )
    assert wrong_local.valid is False
    assert wrong_local.failure == "local Node image ID does not match signed artifact"


def test_node_release_signing_rejects_dirty_source_and_unsafe_private_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, commit = _source_checkout(tmp_path)
    private_key = tmp_path / "keys/private.pem"
    public_key = tmp_path / "keys/public.pem"
    generate_node_release_signing_keypair(private_key, public_key)
    monkeypatch.setattr(release_module, "inspect_node_image", lambda _image: _inspection(commit))
    (source / "dirty.txt").write_text("dirty\n", encoding="utf-8")

    with pytest.raises(NodeReleaseArtifactError, match="must be clean"):
        sign_node_release_artifact(
            image_reference="ithildin/node:0.1.0",
            node_version="0.1.0",
            source_root=source,
            dockerfile_path=source / "deploy/Dockerfile.node",
            lockfile_path=source / "uv.lock",
            private_key_path=private_key,
            public_key_path=public_key,
        )
    (source / "dirty.txt").unlink()
    os.chmod(private_key, 0o644)
    with pytest.raises(NodeReleaseArtifactError, match="permissions must be 0600"):
        sign_node_release_artifact(
            image_reference="ithildin/node:0.1.0",
            node_version="0.1.0",
            source_root=source,
            dockerfile_path=source / "deploy/Dockerfile.node",
            lockfile_path=source / "uv.lock",
            private_key_path=private_key,
            public_key_path=public_key,
        )
    os.chmod(private_key, 0o600)
    linked_private = tmp_path / "keys/linked-private.pem"
    linked_private.symlink_to(private_key)
    with pytest.raises(NodeReleaseArtifactError, match="regular file"):
        sign_node_release_artifact(
            image_reference="ithildin/node:0.1.0",
            node_version="0.1.0",
            source_root=source,
            dockerfile_path=source / "deploy/Dockerfile.node",
            lockfile_path=source / "uv.lock",
            private_key_path=linked_private,
            public_key_path=public_key,
        )


def test_node_release_artifact_rejects_untrusted_key_and_unsafe_image_shape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, commit = _source_checkout(tmp_path)
    private_key = tmp_path / "keys/private.pem"
    public_key = tmp_path / "keys/public.pem"
    other_private = tmp_path / "other/private.pem"
    other_public = tmp_path / "other/public.pem"
    generate_node_release_signing_keypair(private_key, public_key)
    generate_node_release_signing_keypair(other_private, other_public)
    inspection = _inspection(commit)
    monkeypatch.setattr(release_module, "inspect_node_image", lambda _image: inspection)
    bundle = sign_node_release_artifact(
        image_reference="ithildin/node:0.1.0",
        node_version="0.1.0",
        source_root=source,
        dockerfile_path=source / "deploy/Dockerfile.node",
        lockfile_path=source / "uv.lock",
        private_key_path=private_key,
        public_key_path=public_key,
    )

    untrusted = verify_node_release_artifact(
        bundle,
        public_key_path=other_public,
        expected_image_reference="ithildin/node:0.1.0",
    )
    assert untrusted.valid is False
    assert untrusted.failure == "Node release signature public key mismatch"

    unsafe_shapes: list[dict[str, object]] = []
    root_image = copy.deepcopy(inspection)
    assert isinstance(root_image["Config"], dict)
    root_image["Config"]["User"] = "0:0"
    unsafe_shapes.append(root_image)
    listening_image = copy.deepcopy(inspection)
    assert isinstance(listening_image["Config"], dict)
    listening_image["Config"]["ExposedPorts"] = {"9000/tcp": {}}
    unsafe_shapes.append(listening_image)
    wrong_entrypoint = copy.deepcopy(inspection)
    assert isinstance(wrong_entrypoint["Config"], dict)
    wrong_entrypoint["Config"]["Entrypoint"] = ["/bin/sh"]
    unsafe_shapes.append(wrong_entrypoint)
    for unsafe in unsafe_shapes:
        monkeypatch.setattr(
            release_module,
            "inspect_node_image",
            lambda _image, value=unsafe: value,
        )
        with pytest.raises(NodeReleaseArtifactError, match="violates"):
            sign_node_release_artifact(
                image_reference="ithildin/node:0.1.0",
                node_version="0.1.0",
                source_root=source,
                dockerfile_path=source / "deploy/Dockerfile.node",
                lockfile_path=source / "uv.lock",
                private_key_path=private_key,
                public_key_path=public_key,
            )
def _source_checkout(tmp_path: Path) -> tuple[Path, str]:
    source = tmp_path / "source"
    (source / "deploy").mkdir(parents=True)
    (source / "deploy/Dockerfile.node").write_text("FROM scratch\n", encoding="utf-8")
    (source / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    _git(source, "init")
    _git(source, "config", "user.email", "test@example.invalid")
    _git(source, "config", "user.name", "Ithildin Test")
    _git(source, "add", ".")
    _git(source, "commit", "-m", "fixture")
    return source, _git(source, "rev-parse", "HEAD").stdout.strip()


def _git(source: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=source,
        capture_output=True,
        text=True,
        check=True,
    )


def _inspection(commit: str) -> dict[str, object]:
    config: JsonObject = {
        "User": "10002:10002",
        "Entrypoint": ["python", "-m", "ithildin_node"],
        "ExposedPorts": None,
        "Labels": {
            "org.opencontainers.image.version": "0.1.0",
            "org.opencontainers.image.revision": commit,
        },
    }
    return {
        "Id": "sha256:" + ("a" * 64),
        "RepoDigests": [],
        "Os": "linux",
        "Architecture": "arm64",
        "Config": config,
    }

"""Exercise signed Ithildin Node OCI artifact selection and rollback evidence."""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import stat
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from ithildin_node.release_artifact import (
    NodeReleaseArtifactError,
    generate_node_release_signing_keypair,
    sign_node_release_artifact,
    verify_node_release_artifact,
)
from ithildin_schemas import JsonObject

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_ROOT = ROOT / "var/node-release-artifact-poc-20260716"
CURRENT_VERSION = "0.1.0"
ROLLBACK_VERSION = "0.0.9"
CURRENT_IMAGE = f"ithildin/node:{CURRENT_VERSION}"
ROLLBACK_IMAGE = f"ithildin/node:{ROLLBACK_VERSION}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", type=Path, default=DEFAULT_EVIDENCE_ROOT)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    root = args.evidence_root.resolve()
    _prepare_root(root, replace=args.replace)
    commit = _clean_commit(ROOT)
    private_key = root / "keys/private.pem"
    public_key = root / "keys/public.pem"
    other_private_key = root / "keys/other-private.pem"
    other_public_key = root / "keys/other-public.pem"
    key_id = generate_node_release_signing_keypair(private_key, public_key)
    generate_node_release_signing_keypair(other_private_key, other_public_key)
    _build_image(CURRENT_IMAGE, CURRENT_VERSION, commit)
    _build_image(ROLLBACK_IMAGE, ROLLBACK_VERSION, commit)
    now = datetime.now(UTC)
    current_bundle = _sign(
        CURRENT_IMAGE,
        CURRENT_VERSION,
        private_key,
        public_key,
        now,
    )
    rollback_bundle = _sign(
        ROLLBACK_IMAGE,
        ROLLBACK_VERSION,
        private_key,
        public_key,
        now,
    )
    _write(root / "evidence/current-bundle.json", current_bundle)
    _write(root / "evidence/rollback-bundle.json", rollback_bundle)
    _write(
        root / "evidence/current-verification.json",
        verify_node_release_artifact(
            current_bundle,
            public_key_path=public_key,
            expected_image_reference=CURRENT_IMAGE,
        ).safe_summary(),
    )
    _write(
        root / "evidence/rollback-verification.json",
        verify_node_release_artifact(
            rollback_bundle,
            public_key_path=public_key,
            expected_image_reference=ROLLBACK_IMAGE,
        ).safe_summary(),
    )
    tampered = copy.deepcopy(current_bundle)
    artifact = tampered.get("artifact")
    if not isinstance(artifact, dict):
        raise RuntimeError("generated current artifact is invalid")
    artifact["dockerfile_sha256"] = "sha256:" + ("0" * 64)
    _write(
        root / "evidence/tamper-verification.json",
        verify_node_release_artifact(
            tampered,
            public_key_path=public_key,
            expected_image_reference=CURRENT_IMAGE,
        ).safe_summary(),
    )
    _write(
        root / "evidence/wrong-selection-verification.json",
        verify_node_release_artifact(
            current_bundle,
            public_key_path=public_key,
            expected_image_reference=ROLLBACK_IMAGE,
        ).safe_summary(),
    )
    _write(
        root / "evidence/untrusted-key-verification.json",
        verify_node_release_artifact(
            current_bundle,
            public_key_path=other_public_key,
            expected_image_reference=CURRENT_IMAGE,
        ).safe_summary(),
    )
    current_artifact = cast(dict[str, object], current_bundle["artifact"])
    current_image_id = str(current_artifact["image_id"])
    try:
        _docker("tag", ROLLBACK_IMAGE, CURRENT_IMAGE)
        _write(
            root / "evidence/substituted-image-verification.json",
            verify_node_release_artifact(
                current_bundle,
                public_key_path=public_key,
                expected_image_reference=CURRENT_IMAGE,
            ).safe_summary(),
        )
    finally:
        _docker("tag", current_image_id, CURRENT_IMAGE)
    _write(
        root / "evidence/dirty-source-result.json",
        _dirty_source_result(private_key, public_key),
    )
    _write(
        root / "evidence/key-posture.json",
        {
            "key_id": key_id,
            "private_key_mode": f"{stat.S_IMODE(private_key.stat().st_mode):04o}",
            "public_key_mode": f"{stat.S_IMODE(public_key.stat().st_mode):04o}",
            "dedicated_release_artifact_key": True,
        },
    )
    print(f"Built Node release-artifact POC evidence at {root}")
    return 0


def _prepare_root(root: Path, *, replace: bool) -> None:
    if root.exists():
        if not replace:
            raise SystemExit(f"evidence root already exists: {root}")
        if root != DEFAULT_EVIDENCE_ROOT.resolve() and ROOT / "var" not in root.parents:
            raise SystemExit("refusing to replace evidence outside repository var")
        shutil.rmtree(root)
    (root / "keys").mkdir(parents=True)
    (root / "evidence").mkdir()


def _clean_commit(root: Path) -> str:
    status = _git(root, "status", "--porcelain=v1", "--untracked-files=normal").stdout.strip()
    if status:
        raise SystemExit("Node release-artifact POC requires a clean checkout")
    return _git(root, "rev-parse", "HEAD").stdout.strip()


def _build_image(image: str, version: str, commit: str) -> None:
    subprocess.run(
        [
            "docker",
            "build",
            "-f",
            "deploy/Dockerfile.node",
            "--build-arg",
            f"ITHILDIN_NODE_VERSION={version}",
            "--build-arg",
            f"ITHILDIN_SOURCE_REVISION={commit}",
            "-t",
            image,
            ".",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )


def _sign(
    image: str,
    version: str,
    private_key: Path,
    public_key: Path,
    now: datetime,
) -> JsonObject:
    return sign_node_release_artifact(
        image_reference=image,
        node_version=version,
        source_root=ROOT,
        dockerfile_path=ROOT / "deploy/Dockerfile.node",
        lockfile_path=ROOT / "uv.lock",
        private_key_path=private_key,
        public_key_path=public_key,
        now=now,
    )


def _dirty_source_result(private_key: Path, public_key: Path) -> JsonObject:
    with tempfile.TemporaryDirectory(prefix="ithildin-node-release-dirty-") as temporary:
        clone = Path(temporary) / "source"
        subprocess.run(
            ["git", "clone", "--quiet", "--no-hardlinks", str(ROOT), str(clone)],
            capture_output=True,
            text=True,
            check=True,
        )
        (clone / "dirty-source-marker.txt").write_text("dirty\n", encoding="utf-8")
        try:
            sign_node_release_artifact(
                image_reference=CURRENT_IMAGE,
                node_version=CURRENT_VERSION,
                source_root=clone,
                dockerfile_path=clone / "deploy/Dockerfile.node",
                lockfile_path=clone / "uv.lock",
                private_key_path=private_key,
                public_key_path=public_key,
            )
        except NodeReleaseArtifactError as exc:
            return {
                "valid": False,
                "dirty_source_denied": str(exc)
                == "Node release source checkout must be clean",
                "failure": str(exc),
                "gateway_enforcement": False,
                "self_update_authority": False,
            }
    return {"valid": True, "dirty_source_denied": False}


def _git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )


def _docker(*arguments: str) -> None:
    subprocess.run(
        ["docker", *arguments],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )


def _write(path: Path, document: JsonObject) -> None:
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())

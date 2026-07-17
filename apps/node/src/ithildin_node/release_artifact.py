"""Local operator signing and verification for Ithildin Node OCI artifacts."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import stat
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from ithildin_schemas import JsonObject, canonical_json, sha256_digest
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

BUNDLE_TYPE: Literal["ithildin.node_release_artifact"] = "ithildin.node_release_artifact"
FORMAT_VERSION: Literal["1"] = "1"
SIGNATURE_TYPE: Literal["ithildin.node_release_artifact.signature"] = (
    "ithildin.node_release_artifact.signature"
)
SIGNATURE_ALGORITHM: Literal["ed25519"] = "ed25519"
SIGNATURE_DOMAIN = b"ITHILDIN-NODE-RELEASE-ARTIFACT-V1\n"
IMAGE_REFERENCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/@:-]{0,254}$")
VERSION_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


class NodeReleaseArtifactError(RuntimeError):
    """Raised when Node release artifact signing or verification fails closed."""


class NodeReleasePlatform(BaseModel):
    model_config = ConfigDict(extra="forbid")

    os: Literal["linux"]
    architecture: str = Field(min_length=1, max_length=32, pattern=r"^[a-z0-9_]+$")


class NodeReleaseRuntime(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user: Literal["10002:10002"]
    entrypoint: list[str]
    exposed_ports: list[str]

    @model_validator(mode="after")
    def validate_closed_runtime(self) -> NodeReleaseRuntime:
        if self.entrypoint != ["python", "-m", "ithildin_node"]:
            raise ValueError("Node release artifact entrypoint is not approved")
        if self.exposed_ports:
            raise ValueError("Node release artifact must expose no ports")
        return self


class NodeReleaseArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_kind: Literal["oci_image"]
    image_reference: str = Field(min_length=1, max_length=255)
    image_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    repo_digests: list[str]
    node_version: str
    source_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    source_dirty: Literal[False]
    dockerfile_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    lockfile_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    created_at: datetime
    platform: NodeReleasePlatform
    runtime: NodeReleaseRuntime

    @field_validator("image_reference")
    @classmethod
    def validate_image_reference(cls, value: str) -> str:
        if IMAGE_REFERENCE_RE.fullmatch(value) is None:
            raise ValueError("Node release image reference is invalid")
        return value

    @field_validator("node_version")
    @classmethod
    def validate_node_version(cls, value: str) -> str:
        if VERSION_RE.fullmatch(value) is None:
            raise ValueError("Node release version is invalid")
        return value

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Node release creation time must be timezone-aware")
        return value


class NodeReleaseSignature(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signature_type: Literal["ithildin.node_release_artifact.signature"]
    algorithm: Literal["ed25519"]
    key_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    public_key: str = Field(min_length=44, max_length=44)
    signature: str = Field(min_length=88, max_length=88)


class NodeReleaseArtifactBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bundle_type: Literal["ithildin.node_release_artifact"]
    format_version: Literal["1"]
    artifact: NodeReleaseArtifact
    signature: NodeReleaseSignature


@dataclass(frozen=True)
class NodeReleaseVerificationResult:
    valid: bool
    key_id: str | None
    image_id: str | None
    node_version: str | None
    source_commit: str | None
    failure: str | None = None

    def safe_summary(self) -> JsonObject:
        return {
            "valid": self.valid,
            "key_id": self.key_id,
            "image_id": self.image_id,
            "node_version": self.node_version,
            "source_commit": self.source_commit,
            "local_operator_evidence_only": True,
            "gateway_enforcement": False,
            "self_update_authority": False,
            "failure": self.failure,
        }


def generate_node_release_signing_keypair(
    private_key_path: Path, public_key_path: Path, *, overwrite: bool = False
) -> str:
    if not overwrite and (private_key_path.exists() or public_key_path.exists()):
        raise NodeReleaseArtifactError("Node release signing key already exists")
    private_key_path.parent.mkdir(parents=True, exist_ok=True)
    public_key_path.parent.mkdir(parents=True, exist_ok=True)
    private_key = Ed25519PrivateKey.generate()
    private_key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    private_key_path.chmod(0o600)
    public_key_path.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    public_key_path.chmod(0o644)
    return node_release_public_key_id(private_key.public_key())


def sign_node_release_artifact(
    *,
    image_reference: str,
    node_version: str,
    source_root: Path,
    dockerfile_path: Path,
    lockfile_path: Path,
    private_key_path: Path,
    public_key_path: Path,
    now: datetime | None = None,
) -> JsonObject:
    source_commit = _clean_source_commit(source_root)
    private_key = _load_private_key(private_key_path)
    trusted_public_key = _load_public_key(public_key_path)
    if _public_key_raw(private_key.public_key()) != _public_key_raw(trusted_public_key):
        raise NodeReleaseArtifactError("Node release signing keys do not match")
    inspected = inspect_node_image(image_reference)
    labels = _string_object(inspected.get("Config"), "image Config").get("Labels")
    label_values = _string_object(labels, "image labels")
    if label_values.get("org.opencontainers.image.version") != node_version:
        raise NodeReleaseArtifactError("Node image version label does not match requested version")
    if label_values.get("org.opencontainers.image.revision") != source_commit:
        raise NodeReleaseArtifactError("Node image source revision does not match clean checkout")
    try:
        artifact = NodeReleaseArtifact(
            artifact_kind="oci_image",
            image_reference=image_reference,
            image_id=_required_string(inspected, "Id"),
            repo_digests=_string_list(inspected.get("RepoDigests")),
            node_version=node_version,
            source_commit=source_commit,
            source_dirty=False,
            dockerfile_sha256=_file_sha256(dockerfile_path),
            lockfile_sha256=_file_sha256(lockfile_path),
            created_at=now or datetime.now(UTC),
            platform=NodeReleasePlatform(
                os=cast(Literal["linux"], _required_string(inspected, "Os")),
                architecture=_required_string(inspected, "Architecture"),
            ),
            runtime=_runtime_from_inspection(inspected),
        )
    except ValidationError as exc:
        raise NodeReleaseArtifactError(
            "Node image inspection violates the release artifact contract"
        ) from exc
    public_key_b64 = base64.b64encode(_public_key_raw(trusted_public_key)).decode("ascii")
    key_id = node_release_public_key_id(trusted_public_key)
    metadata: JsonObject = {
        "signature_type": SIGNATURE_TYPE,
        "algorithm": SIGNATURE_ALGORITHM,
        "key_id": key_id,
        "public_key": public_key_b64,
    }
    artifact_document = cast(JsonObject, artifact.model_dump(mode="json"))
    signature = private_key.sign(_signature_message(artifact_document, metadata))
    bundle = NodeReleaseArtifactBundle(
        bundle_type=BUNDLE_TYPE,
        format_version=FORMAT_VERSION,
        artifact=artifact,
        signature=NodeReleaseSignature(
            signature_type=SIGNATURE_TYPE,
            algorithm=SIGNATURE_ALGORITHM,
            key_id=key_id,
            public_key=public_key_b64,
            signature=base64.b64encode(signature).decode("ascii"),
        ),
    )
    return cast(JsonObject, bundle.model_dump(mode="json"))


def verify_node_release_artifact(
    bundle: object,
    *,
    public_key_path: Path,
    expected_image_reference: str,
) -> NodeReleaseVerificationResult:
    artifact: NodeReleaseArtifact | None = None
    try:
        parsed = NodeReleaseArtifactBundle.model_validate(bundle)
        artifact = parsed.artifact
        if artifact.image_reference != expected_image_reference:
            raise NodeReleaseArtifactError("signed Node image reference does not match selection")
        embedded_key = _public_key_from_b64(parsed.signature.public_key)
        trusted_key = _load_public_key(public_key_path)
        if _public_key_raw(embedded_key) != _public_key_raw(trusted_key):
            raise NodeReleaseArtifactError("Node release signature public key mismatch")
        if node_release_public_key_id(embedded_key) != parsed.signature.key_id:
            raise NodeReleaseArtifactError("Node release signature key id mismatch")
        artifact_document = cast(JsonObject, artifact.model_dump(mode="json"))
        metadata: JsonObject = {
            "signature_type": parsed.signature.signature_type,
            "algorithm": parsed.signature.algorithm,
            "key_id": parsed.signature.key_id,
            "public_key": parsed.signature.public_key,
        }
        embedded_key.verify(
            base64.b64decode(parsed.signature.signature, validate=True),
            _signature_message(artifact_document, metadata),
        )
        inspected = inspect_node_image(expected_image_reference)
        _verify_inspected_image(artifact, inspected)
    except (
        NodeReleaseArtifactError,
        ValidationError,
        InvalidSignature,
        ValueError,
        binascii.Error,
    ) as exc:
        return NodeReleaseVerificationResult(
            valid=False,
            key_id=None,
            image_id=artifact.image_id if artifact is not None else None,
            node_version=artifact.node_version if artifact is not None else None,
            source_commit=artifact.source_commit if artifact is not None else None,
            failure=(
                "Node release artifact signature verification failed"
                if isinstance(exc, InvalidSignature)
                else str(exc)
            ),
        )
    return NodeReleaseVerificationResult(
        valid=True,
        key_id=parsed.signature.key_id,
        image_id=artifact.image_id,
        node_version=artifact.node_version,
        source_commit=artifact.source_commit,
    )


def inspect_node_image(image_reference: str) -> dict[str, Any]:
    if IMAGE_REFERENCE_RE.fullmatch(image_reference) is None:
        raise NodeReleaseArtifactError("Node release image reference is invalid")
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", image_reference],
            capture_output=True,
            text=True,
            check=True,
        )
        document = json.loads(result.stdout)
    except FileNotFoundError as exc:
        raise NodeReleaseArtifactError("Docker CLI is unavailable") from exc
    except subprocess.CalledProcessError as exc:
        raise NodeReleaseArtifactError("selected Node image is unavailable") from exc
    except json.JSONDecodeError as exc:
        raise NodeReleaseArtifactError("Docker returned invalid image inspection data") from exc
    if not isinstance(document, list) or len(document) != 1 or not isinstance(document[0], dict):
        raise NodeReleaseArtifactError("Docker returned invalid image inspection data")
    return cast(dict[str, Any], document[0])


def node_release_public_key_id(public_key: Ed25519PublicKey) -> str:
    return sha256_digest(
        {
            "algorithm": SIGNATURE_ALGORITHM,
            "public_key": base64.b64encode(_public_key_raw(public_key)).decode("ascii"),
            "usage": SIGNATURE_TYPE,
        }
    )


def _verify_inspected_image(artifact: NodeReleaseArtifact, inspected: dict[str, Any]) -> None:
    if _required_string(inspected, "Id") != artifact.image_id:
        raise NodeReleaseArtifactError("local Node image ID does not match signed artifact")
    if _required_string(inspected, "Os") != artifact.platform.os:
        raise NodeReleaseArtifactError("local Node image OS does not match signed artifact")
    if _required_string(inspected, "Architecture") != artifact.platform.architecture:
        raise NodeReleaseArtifactError(
            "local Node image architecture does not match signed artifact"
        )
    if _runtime_from_inspection(inspected) != artifact.runtime:
        raise NodeReleaseArtifactError("local Node image runtime does not match signed artifact")
    labels = _string_object(
        _string_object(inspected.get("Config"), "image Config").get("Labels"),
        "image labels",
    )
    if labels.get("org.opencontainers.image.version") != artifact.node_version:
        raise NodeReleaseArtifactError(
            "local Node image version label does not match signed artifact"
        )
    if labels.get("org.opencontainers.image.revision") != artifact.source_commit:
        raise NodeReleaseArtifactError(
            "local Node image source revision does not match signed artifact"
        )


def _runtime_from_inspection(inspected: dict[str, Any]) -> NodeReleaseRuntime:
    config = _string_object(inspected.get("Config"), "image Config")
    exposed = config.get("ExposedPorts")
    exposed_ports = sorted(exposed) if isinstance(exposed, dict) else []
    return NodeReleaseRuntime(
        user=cast(Literal["10002:10002"], _required_string(config, "User")),
        entrypoint=_string_list(config.get("Entrypoint")),
        exposed_ports=exposed_ports,
    )


def _clean_source_commit(source_root: Path) -> str:
    try:
        status_result = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=normal"],
            cwd=source_root,
            capture_output=True,
            text=True,
            check=True,
        )
        if status_result.stdout.strip():
            raise NodeReleaseArtifactError("Node release source checkout must be clean")
        commit_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=source_root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise NodeReleaseArtifactError("Node release source checkout is unavailable") from exc
    commit = commit_result.stdout.strip()
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise NodeReleaseArtifactError("Node release source commit is invalid")
    return commit


def _signature_message(artifact: JsonObject, metadata: JsonObject) -> bytes:
    payload: JsonObject = {
        "bundle_type": BUNDLE_TYPE,
        "format_version": FORMAT_VERSION,
        "artifact": artifact,
        "signature": metadata,
    }
    return SIGNATURE_DOMAIN + canonical_json(payload).encode("utf-8")


def _file_sha256(path: Path) -> str:
    if not path.is_file():
        raise NodeReleaseArtifactError("Node release source input is unavailable")
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _load_private_key(path: Path) -> Ed25519PrivateKey:
    _require_private_file(path)
    try:
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    except (OSError, ValueError, TypeError) as exc:
        raise NodeReleaseArtifactError("Node release private key is invalid") from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise NodeReleaseArtifactError("Node release private key must be Ed25519")
    return key


def _load_public_key(path: Path) -> Ed25519PublicKey:
    try:
        key = serialization.load_pem_public_key(path.read_bytes())
    except (OSError, ValueError, TypeError) as exc:
        raise NodeReleaseArtifactError("Node release public key is invalid") from exc
    if not isinstance(key, Ed25519PublicKey):
        raise NodeReleaseArtifactError("Node release public key must be Ed25519")
    return key


def _require_private_file(path: Path) -> None:
    try:
        file_status = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise NodeReleaseArtifactError("Node release private key is unavailable") from exc
    if not stat.S_ISREG(file_status.st_mode) or path.is_symlink():
        raise NodeReleaseArtifactError("Node release private key must be a regular file")
    if stat.S_IMODE(file_status.st_mode) & 0o077:
        raise NodeReleaseArtifactError("Node release private key permissions must be 0600")


def _public_key_from_b64(value: str) -> Ed25519PublicKey:
    try:
        decoded = base64.b64decode(value, validate=True)
        if len(decoded) != 32:
            raise ValueError
        return Ed25519PublicKey.from_public_bytes(decoded)
    except (binascii.Error, ValueError) as exc:
        raise NodeReleaseArtifactError("Node release embedded public key is invalid") from exc


def _public_key_raw(public_key: Ed25519PublicKey) -> bytes:
    return public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def _required_string(document: dict[str, Any], key: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value:
        raise NodeReleaseArtifactError(f"Node image inspection is missing {key}")
    return value


def _string_object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise NodeReleaseArtifactError(f"{label} is invalid")
    return cast(dict[str, Any], value)


def _string_list(value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise NodeReleaseArtifactError("Node image inspection list is invalid")
    return cast(list[str], value)

"""Minimal local-preview Ithildin Node enrollment and heartbeat client."""

from __future__ import annotations

import base64
import binascii
import json
import os
import re
import secrets
import stat
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from ithildin_api.node_configuration import (
    CONFIGURATION_ACK_STATUS,
    NodeConfigurationTrust,
    NodeConfigurationVerificationError,
    NodeDesiredConfigurationPayload,
    verify_configuration_bundle,
)
from ithildin_api.node_configuration_trust import (
    TRUST_TRANSITION_ACK_STATUS,
    NodeConfigurationTrustTransitionVerificationError,
    transition_next_trust,
    verify_configuration_trust_transition,
)
from ithildin_api.node_versions import parse_node_version
from ithildin_api.nodes import (
    NODE_PROTOCOL_VERSION,
    NodeIdentityRotationRecord,
    canonical_identity_rotation_proof_message,
    canonical_signature_message,
    node_identity_key_id,
)
from ithildin_schemas import JsonObject, canonical_json, sha256_digest

_LOCAL_PREVIEW_HOSTS = {
    "127.0.0.1",
    "::1",
    "localhost",
    "host.docker.internal",
    "ithildin-api",
}


class NodeClientError(RuntimeError):
    """Raised when the local-preview Node client cannot proceed safely."""


@dataclass(frozen=True)
class NodeState:
    api_url: str
    node_id: str
    principal_id: str
    workspace_id: str
    private_key: str
    public_key: str
    enrolled_at: str
    gateway_configuration_key_id: str
    gateway_configuration_public_key: str
    gateway_manifest_lock_digest: str
    pending_configuration_key_id: str | None = None
    pending_configuration_public_key: str | None = None
    pending_trust_transition_id: str | None = None
    pending_trust_transition_digest: str | None = None
    pending_trust_expires_at: str | None = None
    previous_configuration_key_id: str | None = None
    previous_configuration_public_key: str | None = None
    previous_trust_expires_at: str | None = None
    pending_identity_private_key: str | None = None
    pending_identity_public_key: str | None = None
    pending_identity_rotation_id: str | None = None
    pending_identity_current_key_id: str | None = None
    pending_identity_challenge: str | None = None
    pending_identity_challenge_digest: str | None = None
    pending_identity_expires_at: str | None = None

    def safe_summary(self) -> JsonObject:
        return {
            "api_url": self.api_url,
            "node_id": self.node_id,
            "principal_id": self.principal_id,
            "workspace_id": self.workspace_id,
            "enrolled_at": self.enrolled_at,
            "private_key_present": True,
            "configuration_trust_key_id": self.gateway_configuration_key_id,
            "manifest_lock_digest": self.gateway_manifest_lock_digest,
            "pending_configuration_key_id": self.pending_configuration_key_id,
            "pending_trust_transition_id": self.pending_trust_transition_id,
            "pending_trust_expires_at": self.pending_trust_expires_at,
            "previous_configuration_key_id": self.previous_configuration_key_id,
            "previous_trust_expires_at": self.previous_trust_expires_at,
            "active_identity_key_id": node_identity_key_id(self.public_key),
            "pending_identity_key_id": (
                node_identity_key_id(self.pending_identity_public_key)
                if self.pending_identity_public_key is not None
                else None
            ),
            "pending_identity_rotation_id": self.pending_identity_rotation_id,
            "pending_identity_expires_at": self.pending_identity_expires_at,
        }

    def pending_identity_rotation_expired(self, *, now: datetime | None = None) -> bool:
        if self.pending_identity_expires_at is None:
            return False
        return (now or datetime.now(UTC)) >= _parse_aware_datetime(
            self.pending_identity_expires_at,
            "pending identity-key rotation expiry",
        )

    def _document(self) -> JsonObject:
        return {
            **self.safe_summary(),
            "private_key": self.private_key,
            "public_key": self.public_key,
            "gateway_configuration_key_id": self.gateway_configuration_key_id,
            "gateway_configuration_public_key": self.gateway_configuration_public_key,
            "gateway_manifest_lock_digest": self.gateway_manifest_lock_digest,
            "pending_configuration_public_key": self.pending_configuration_public_key,
            "pending_trust_transition_digest": self.pending_trust_transition_digest,
            "previous_configuration_public_key": self.previous_configuration_public_key,
            "pending_identity_private_key": self.pending_identity_private_key,
            "pending_identity_public_key": self.pending_identity_public_key,
            "pending_identity_current_key_id": self.pending_identity_current_key_id,
            "pending_identity_challenge": self.pending_identity_challenge,
            "pending_identity_challenge_digest": self.pending_identity_challenge_digest,
        }

    def write_new(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = canonical_json(self._document()).encode()
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            file_descriptor = os.open(path, flags, 0o600)
        except FileExistsError as exc:
            raise NodeClientError("Node state already exists") from exc
        try:
            with os.fdopen(file_descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            # Leave a mode-0600 partial file for explicit operator recovery. Unlinking a pathname
            # after opening it would risk removing a replacement created by another actor.
            raise

    def write_atomic(self, path: Path) -> None:
        _write_private_json_atomic(path, self._document(), label="Node state")

    @classmethod
    def load(cls, path: Path) -> NodeState:
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            file_descriptor = os.open(path, flags)
        except OSError as exc:
            raise NodeClientError("Node state is unavailable") from exc
        try:
            file_status = os.fstat(file_descriptor)
            if not stat.S_ISREG(file_status.st_mode):
                raise NodeClientError("Node state must be a regular file")
            if stat.S_IMODE(file_status.st_mode) & 0o077:
                raise NodeClientError("Node state permissions must be 0600")
            with os.fdopen(file_descriptor, "r", encoding="utf-8") as handle:
                file_descriptor = -1
                document = json.load(handle)
            state = cls(
                api_url=str(document["api_url"]),
                node_id=str(document["node_id"]),
                principal_id=str(document["principal_id"]),
                workspace_id=str(document["workspace_id"]),
                private_key=str(document["private_key"]),
                public_key=str(document["public_key"]),
                enrolled_at=str(document["enrolled_at"]),
                gateway_configuration_key_id=str(document["gateway_configuration_key_id"]),
                gateway_configuration_public_key=str(
                    document["gateway_configuration_public_key"]
                ),
                gateway_manifest_lock_digest=str(document["gateway_manifest_lock_digest"]),
                pending_configuration_key_id=_optional_string(
                    document, "pending_configuration_key_id"
                ),
                pending_configuration_public_key=_optional_string(
                    document, "pending_configuration_public_key"
                ),
                pending_trust_transition_id=_optional_string(
                    document, "pending_trust_transition_id"
                ),
                pending_trust_transition_digest=_optional_string(
                    document, "pending_trust_transition_digest"
                ),
                pending_trust_expires_at=_optional_string(
                    document, "pending_trust_expires_at"
                ),
                previous_configuration_key_id=_optional_string(
                    document, "previous_configuration_key_id"
                ),
                previous_configuration_public_key=_optional_string(
                    document, "previous_configuration_public_key"
                ),
                previous_trust_expires_at=_optional_string(
                    document, "previous_trust_expires_at"
                ),
                pending_identity_private_key=_optional_string(
                    document, "pending_identity_private_key"
                ),
                pending_identity_public_key=_optional_string(
                    document, "pending_identity_public_key"
                ),
                pending_identity_rotation_id=_optional_string(
                    document, "pending_identity_rotation_id"
                ),
                pending_identity_current_key_id=_optional_string(
                    document, "pending_identity_current_key_id"
                ),
                pending_identity_challenge=_optional_string(
                    document, "pending_identity_challenge"
                ),
                pending_identity_challenge_digest=_optional_string(
                    document, "pending_identity_challenge_digest"
                ),
                pending_identity_expires_at=_optional_string(
                    document, "pending_identity_expires_at"
                ),
            )
        except NodeClientError:
            raise
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise NodeClientError("Node state is invalid") from exc
        finally:
            if file_descriptor >= 0:
                os.close(file_descriptor)
        _validate_api_url(state.api_url)
        if state.principal_id != f"agent:node.{state.node_id}":
            raise NodeClientError("Node state identity binding is invalid")
        _validate_identity_keypair(
            state.private_key, state.public_key, label="active Node identity"
        )
        _configuration_trust(state)
        _validate_optional_trust_state(state)
        _validate_optional_identity_rotation_state(state)
        return state


@dataclass(frozen=True)
class StoredNodeConfiguration:
    bundle: JsonObject

    @property
    def generation(self) -> int:
        value = self.bundle.get("generation")
        if not isinstance(value, int) or isinstance(value, bool):
            raise NodeClientError("stored configuration generation is invalid")
        return value

    @property
    def configuration_digest(self) -> str:
        return _required_string(self.bundle, "configuration_digest")

    @property
    def signing_key_id(self) -> str:
        signature = self.bundle.get("signature")
        if not isinstance(signature, dict):
            raise NodeClientError("stored configuration signature is invalid")
        return _required_string(signature, "key_id")

    def safe_summary(self) -> JsonObject:
        return {
            "configuration_id": _required_string(self.bundle, "configuration_id"),
            "generation": self.generation,
            "configuration_digest": self.configuration_digest,
            "expires_at": _required_string(self.bundle, "expires_at"),
            "status": CONFIGURATION_ACK_STATUS,
            "enforcement_proven": False,
        }

    def write_atomic(self, path: Path) -> None:
        _write_private_json_atomic(path, self.bundle, label="verified Node configuration")

    @classmethod
    def load(cls, path: Path) -> StoredNodeConfiguration:
        document = _read_private_json(path, label="Node configuration")
        return cls(bundle=document)


@dataclass(frozen=True)
class NodeConfigurationPullResult:
    configuration: StoredNodeConfiguration
    state: NodeState
    trust_promoted: bool
    verification_trust: str


@dataclass(frozen=True)
class NodeConfigurationTrustStageResult:
    state: NodeState
    bundle: JsonObject


class NodeClient:
    def __init__(self, api_url: str, *, timeout_seconds: float = 10.0) -> None:
        self.api_url = _validate_api_url(api_url)
        self.timeout_seconds = timeout_seconds

    def enroll(
        self,
        *,
        enrollment_code: str,
        node_version: str,
        runner_adapter: str,
        deployment_topology: str,
    ) -> NodeState:
        private_key = Ed25519PrivateKey.generate()
        private_key_text = base64.b64encode(
            private_key.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption(),
            )
        ).decode()
        public_key_text = base64.b64encode(
            private_key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        ).decode()
        response = self._post(
            "/nodes/enroll",
            {
                "enrollment_code": enrollment_code,
                "public_key": public_key_text,
                "protocol_version": NODE_PROTOCOL_VERSION,
                "node_version": node_version,
                "runner_adapter": runner_adapter,
                "deployment_topology": deployment_topology,
            },
        )
        trust = response.get("configuration_trust")
        if not isinstance(trust, dict):
            raise NodeClientError("Gateway enrollment response is incomplete")
        return NodeState(
            api_url=self.api_url,
            node_id=_required_string(response, "node_id"),
            principal_id=_required_string(response, "principal_id"),
            workspace_id=_required_string(response, "workspace_id"),
            private_key=private_key_text,
            public_key=public_key_text,
            enrolled_at=_required_string(response, "enrolled_at"),
            gateway_configuration_key_id=_required_string(trust, "key_id"),
            gateway_configuration_public_key=_required_string(
                trust, "public_key"
            ),
            gateway_manifest_lock_digest=_required_string(
                response, "manifest_lock_digest"
            ),
        )

    def heartbeat(
        self,
        state: NodeState,
        *,
        node_version: str,
        runner_adapter: str,
        deployment_topology: str,
        configuration_digest: str,
        mission_id: str | None = None,
        now: datetime | None = None,
        nonce: str | None = None,
    ) -> JsonObject:
        payload: JsonObject = {
            "protocol_version": NODE_PROTOCOL_VERSION,
            "node_version": node_version,
            "runner_adapter": runner_adapter,
            "deployment_topology": deployment_topology,
            "configuration_digest": configuration_digest,
        }
        if mission_id is not None:
            payload["mission_id"] = mission_id
        return self._signed_post(
            state,
            f"/nodes/{state.node_id}/heartbeat",
            payload,
            now=now,
            nonce=nonce,
        )

    def stage_identity_key_rotation(
        self,
        state: NodeState,
        *,
        now: datetime | None = None,
        nonce: str | None = None,
    ) -> NodeState:
        if state.pending_identity_rotation_id is not None:
            raise NodeClientError("Node already has a pending identity-key rotation")
        return self._stage_identity_key_rotation(state, now=now, nonce=nonce)

    def replace_expired_identity_key_rotation(
        self,
        state: NodeState,
        *,
        now: datetime | None = None,
        nonce: str | None = None,
    ) -> NodeState:
        effective_now = now or datetime.now(UTC)
        if not state.pending_identity_rotation_expired(now=effective_now):
            raise NodeClientError("Node pending identity-key rotation is not expired")
        # The Gateway issues a replacement only after authenticating this request with the still
        # active K1. That proof makes it safe to replace the expired local pending K2.
        return self._stage_identity_key_rotation(state, now=effective_now, nonce=nonce)

    def _stage_identity_key_rotation(
        self,
        state: NodeState,
        *,
        now: datetime | None,
        nonce: str | None,
    ) -> NodeState:
        response = self._signed_post(
            state,
            f"/nodes/{state.node_id}/identity-key-rotation/challenges",
            {"protocol_version": NODE_PROTOCOL_VERSION},
            now=now,
            nonce=nonce,
        )
        private_key = Ed25519PrivateKey.generate()
        private_key_text, public_key_text = _identity_keypair_text(private_key)
        current_key_id = _required_string(response, "current_key_id")
        if current_key_id != node_identity_key_id(state.public_key):
            raise NodeClientError("Gateway identity-key rotation current key mismatch")
        challenge = _required_string(response, "challenge")
        challenge_digest = sha256_digest(challenge)
        staged = replace(
            state,
            pending_identity_private_key=private_key_text,
            pending_identity_public_key=public_key_text,
            pending_identity_rotation_id=_required_string(response, "rotation_id"),
            pending_identity_current_key_id=current_key_id,
            pending_identity_challenge=challenge,
            pending_identity_challenge_digest=challenge_digest,
            pending_identity_expires_at=_required_string(response, "expires_at"),
        )
        _validate_optional_identity_rotation_state(staged)
        return staged

    def activate_identity_key_rotation(
        self,
        state: NodeState,
        *,
        now: datetime | None = None,
        nonce: str | None = None,
    ) -> NodeState:
        rotation = _pending_identity_rotation_record(state)
        next_public_key = cast(str, state.pending_identity_public_key)
        next_private_key = cast(str, state.pending_identity_private_key)
        next_key_id = node_identity_key_id(next_public_key)
        proof = canonical_identity_rotation_proof_message(
            rotation=rotation,
            next_key_id=next_key_id,
        )
        payload: JsonObject = {
            "protocol_version": NODE_PROTOCOL_VERSION,
            "rotation_id": rotation.rotation_id,
            "challenge": cast(str, state.pending_identity_challenge),
            "next_public_key": next_public_key,
            "next_key_proof": base64.b64encode(_private_key(next_private_key).sign(proof)).decode(),
        }
        response = self._signed_post(
            state,
            f"/nodes/{state.node_id}/identity-key-rotation/activations",
            payload,
            now=now,
            nonce=nonce,
        )
        _validate_identity_rotation_activation_response(response, rotation, next_key_id)
        return _promote_pending_identity_key(state)

    def recover_identity_key_rotation(
        self,
        state: NodeState,
        *,
        now: datetime | None = None,
        nonce: str | None = None,
    ) -> NodeState:
        rotation = _pending_identity_rotation_record(state)
        next_public_key = cast(str, state.pending_identity_public_key)
        next_private_key = cast(str, state.pending_identity_private_key)
        next_key_id = node_identity_key_id(next_public_key)
        response = self._signed_post_with_private_key(
            state,
            f"/nodes/{state.node_id}/identity-key-rotation/status",
            {
                "protocol_version": NODE_PROTOCOL_VERSION,
                "rotation_id": rotation.rotation_id,
            },
            private_key=next_private_key,
            now=now,
            nonce=nonce,
        )
        _validate_identity_rotation_activation_response(response, rotation, next_key_id)
        return _promote_pending_identity_key(state)

    def pull_configuration(
        self,
        state: NodeState,
        *,
        known_generation: int | None = None,
        now: datetime | None = None,
        nonce: str | None = None,
    ) -> StoredNodeConfiguration:
        result = self.pull_configuration_with_state(
            state,
            known_generation=known_generation,
            now=now,
            nonce=nonce,
        )
        if result.trust_promoted:
            raise NodeClientError(
                "configuration trust promotion requires atomic Node state persistence"
            )
        return result.configuration

    def pull_configuration_with_state(
        self,
        state: NodeState,
        *,
        known_generation: int | None = None,
        now: datetime | None = None,
        nonce: str | None = None,
    ) -> NodeConfigurationPullResult:
        payload: JsonObject = {"protocol_version": NODE_PROTOCOL_VERSION}
        if known_generation is not None:
            payload["known_generation"] = known_generation
        bundle = self._signed_post(
            state,
            f"/nodes/{state.node_id}/configuration",
            payload,
            now=now,
            nonce=nonce,
        )
        signing_key_id = _bundle_signing_key_id(bundle)
        trust, source = _configuration_verification_trust(state, signing_key_id, now=now)
        try:
            verified = verify_configuration_bundle(
                bundle,
                trust=trust,
                node_id=state.node_id,
                principal_id=state.principal_id,
                workspace_id=state.workspace_id,
                minimum_generation=known_generation or 0,
                expected_manifest_lock_digest=state.gateway_manifest_lock_digest,
                now=now,
            )
        except NodeConfigurationVerificationError as exc:
            raise NodeClientError(str(exc)) from exc
        configuration = StoredNodeConfiguration(bundle=verified)
        next_state = state
        promoted = source == "pending"
        if promoted:
            next_state = replace(
                state,
                gateway_configuration_key_id=trust.key_id,
                gateway_configuration_public_key=trust.public_key,
                pending_configuration_key_id=None,
                pending_configuration_public_key=None,
                pending_trust_transition_id=None,
                pending_trust_transition_digest=None,
                pending_trust_expires_at=None,
                previous_configuration_key_id=state.gateway_configuration_key_id,
                previous_configuration_public_key=state.gateway_configuration_public_key,
                previous_trust_expires_at=state.pending_trust_expires_at,
            )
        return NodeConfigurationPullResult(
            configuration=configuration,
            state=next_state,
            trust_promoted=promoted,
            verification_trust=source,
        )

    def stage_configuration_trust(
        self,
        state: NodeState,
        *,
        now: datetime | None = None,
        nonce: str | None = None,
    ) -> NodeConfigurationTrustStageResult:
        payload: JsonObject = {"protocol_version": NODE_PROTOCOL_VERSION}
        if state.pending_trust_transition_id is not None:
            payload["known_transition_id"] = state.pending_trust_transition_id
        bundle = self._signed_post(
            state,
            f"/nodes/{state.node_id}/configuration-trust-transition",
            payload,
            now=now,
            nonce=nonce,
        )
        try:
            verified = verify_configuration_trust_transition(
                bundle,
                current_trust=_configuration_trust(state),
                node_id=state.node_id,
                principal_id=state.principal_id,
                workspace_id=state.workspace_id,
                now=now,
            )
            next_trust = transition_next_trust(verified)
        except NodeConfigurationTrustTransitionVerificationError as exc:
            raise NodeClientError(str(exc)) from exc
        staged = replace(
            state,
            pending_configuration_key_id=next_trust.key_id,
            pending_configuration_public_key=next_trust.public_key,
            pending_trust_transition_id=_required_string(verified, "transition_id"),
            pending_trust_transition_digest=_required_string(
                verified, "transition_digest"
            ),
            pending_trust_expires_at=_required_string(verified, "expires_at"),
        )
        return NodeConfigurationTrustStageResult(state=staged, bundle=verified)

    def acknowledge_configuration_trust(
        self,
        state: NodeState,
        *,
        now: datetime | None = None,
        nonce: str | None = None,
    ) -> JsonObject:
        if (
            state.pending_trust_transition_id is None
            or state.pending_trust_transition_digest is None
        ):
            raise NodeClientError("Node has no staged configuration trust transition")
        return self._signed_post(
            state,
            f"/nodes/{state.node_id}/configuration-trust-transition/acknowledgments",
            {
                "protocol_version": NODE_PROTOCOL_VERSION,
                "transition_id": state.pending_trust_transition_id,
                "transition_digest": state.pending_trust_transition_digest,
                "status": TRUST_TRANSITION_ACK_STATUS,
            },
            now=now,
            nonce=nonce,
        )

    def acknowledge_configuration(
        self,
        state: NodeState,
        configuration: StoredNodeConfiguration,
        *,
        now: datetime | None = None,
        nonce: str | None = None,
    ) -> JsonObject:
        return self._signed_post(
            state,
            f"/nodes/{state.node_id}/configuration/acknowledgments",
            {
                "protocol_version": NODE_PROTOCOL_VERSION,
                "generation": configuration.generation,
                "configuration_digest": configuration.configuration_digest,
                "configuration_signing_key_id": configuration.signing_key_id,
                "active_configuration_signing_key_id": (
                    state.gateway_configuration_key_id
                ),
                "status": CONFIGURATION_ACK_STATUS,
            },
            now=now,
            nonce=nonce,
        )

    def governed_tool_call(
        self,
        state: NodeState,
        configuration: StoredNodeConfiguration,
        *,
        node_version: str,
        session_id: str,
        tool_name: str,
        arguments: JsonObject,
        now: datetime | None = None,
        nonce: str | None = None,
    ) -> JsonObject:
        """Submit one signed governed read request with no retry or local fallback."""

        effective_now = now or datetime.now(UTC)
        signing_key_id = configuration.signing_key_id
        trust, _source = _configuration_verification_trust(
            state, signing_key_id, now=effective_now
        )
        try:
            verified = verify_configuration_bundle(
                configuration.bundle,
                trust=trust,
                node_id=state.node_id,
                principal_id=state.principal_id,
                workspace_id=state.workspace_id,
                minimum_generation=configuration.generation,
                expected_manifest_lock_digest=state.gateway_manifest_lock_digest,
                now=effective_now,
            )
            closed = NodeDesiredConfigurationPayload.model_validate(
                verified.get("configuration")
            )
        except (NodeConfigurationVerificationError, ValueError) as exc:
            raise NodeClientError("stored configuration is not valid for governed access") from exc
        if closed.offline_posture != "deny_governed_actions":
            raise NodeClientError("stored configuration does not fail closed offline")
        if parse_node_version(node_version) < parse_node_version(closed.minimum_node_version):
            raise NodeClientError("Node version does not meet the stored minimum")
        requested_workspace = arguments.get("workspace_id")
        if requested_workspace is not None and requested_workspace != state.workspace_id:
            raise NodeClientError("governed request workspace differs from Node enrollment")
        bound_arguments = {**arguments, "workspace_id": state.workspace_id}
        return self._signed_post(
            state,
            f"/nodes/{state.node_id}/governed-tool-calls",
            {
                "protocol_version": NODE_PROTOCOL_VERSION,
                "configuration_generation": configuration.generation,
                "configuration_digest": configuration.configuration_digest,
                "node_version": node_version,
                "session_id": session_id,
                "tool_name": tool_name,
                "arguments": bound_arguments,
            },
            now=effective_now,
            nonce=nonce,
        )

    def _signed_post(
        self,
        state: NodeState,
        path: str,
        payload: JsonObject,
        *,
        now: datetime | None = None,
        nonce: str | None = None,
    ) -> JsonObject:
        return self._signed_post_with_private_key(
            state,
            path,
            payload,
            private_key=state.private_key,
            now=now,
            nonce=nonce,
        )

    def _signed_post_with_private_key(
        self,
        state: NodeState,
        path: str,
        payload: JsonObject,
        *,
        private_key: str,
        now: datetime | None = None,
        nonce: str | None = None,
    ) -> JsonObject:
        if state.api_url != self.api_url:
            raise NodeClientError("Node state API binding mismatch")
        timestamp = str(int((now or datetime.now(UTC)).timestamp()))
        effective_nonce = nonce or secrets.token_hex(16)
        message = canonical_signature_message(
            method="POST",
            path=path,
            timestamp=timestamp,
            nonce=effective_nonce,
            body_hash=sha256_digest(payload),
        )
        signature = base64.b64encode(_private_key(private_key).sign(message)).decode()
        return self._post(
            path,
            payload,
            headers={
                "X-Ithildin-Node": state.node_id,
                "X-Ithildin-Timestamp": timestamp,
                "X-Ithildin-Nonce": effective_nonce,
                "X-Ithildin-Signature": signature,
            },
        )

    def _post(
        self,
        path: str,
        payload: JsonObject,
        *,
        headers: dict[str, str] | None = None,
    ) -> JsonObject:
        request = urllib.request.Request(
            f"{self.api_url}{path}",
            data=canonical_json(payload).encode(),
            headers={"Content-Type": "application/json", **(headers or {})},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                document = json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            raise NodeClientError(f"Gateway rejected Node request with HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise NodeClientError("Gateway is unavailable") from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise NodeClientError("Gateway returned an invalid response") from exc
        if not isinstance(document, dict):
            raise NodeClientError("Gateway returned an invalid response")
        return cast(JsonObject, document)


def _validate_api_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value.rstrip("/"))
    if parsed.scheme != "http" or parsed.hostname not in _LOCAL_PREVIEW_HOSTS:
        raise NodeClientError("Node API URL must use an approved local-preview HTTP host")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise NodeClientError("Node API URL contains unsupported components")
    if parsed.path not in {"", "/"}:
        raise NodeClientError("Node API URL must not include a path")
    return value.rstrip("/")


def _private_key(value: str) -> Ed25519PrivateKey:
    try:
        decoded = base64.b64decode(value, validate=True)
        if len(decoded) != 32:
            raise ValueError
        return Ed25519PrivateKey.from_private_bytes(decoded)
    except (binascii.Error, ValueError, TypeError) as exc:
        raise NodeClientError("Node private key is invalid") from exc


def _identity_keypair_text(private_key: Ed25519PrivateKey) -> tuple[str, str]:
    private_key_text = base64.b64encode(
        private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
    ).decode()
    public_key_text = base64.b64encode(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    ).decode()
    return private_key_text, public_key_text


def _validate_identity_keypair(private_key_text: str, public_key_text: str, *, label: str) -> None:
    private_key = _private_key(private_key_text)
    expected = base64.b64encode(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    ).decode()
    if expected != public_key_text:
        raise NodeClientError(f"{label} keypair is invalid")
    try:
        node_identity_key_id(public_key_text)
    except ValueError as exc:
        raise NodeClientError(f"{label} public key is invalid") from exc


def _configuration_trust(state: NodeState) -> NodeConfigurationTrust:
    return _trust(
        state.gateway_configuration_key_id,
        state.gateway_configuration_public_key,
    )


def _trust(key_id: str, public_key_text: str) -> NodeConfigurationTrust:
    try:
        public_key = base64.b64decode(public_key_text, validate=True)
        if len(public_key) != 32:
            raise ValueError
        Ed25519PublicKey.from_public_bytes(public_key)
    except (binascii.Error, ValueError) as exc:
        raise NodeClientError("Gateway configuration trust is invalid") from exc
    if sha256_digest(public_key_text) != key_id:
        raise NodeClientError("Gateway configuration trust key ID is invalid")
    return NodeConfigurationTrust(key_id=key_id, public_key=public_key_text)


def _validate_optional_trust_state(state: NodeState) -> None:
    pending = (
        state.pending_configuration_key_id,
        state.pending_configuration_public_key,
        state.pending_trust_transition_id,
        state.pending_trust_transition_digest,
        state.pending_trust_expires_at,
    )
    if any(value is not None for value in pending):
        if any(value is None for value in pending):
            raise NodeClientError("Node pending configuration trust state is incomplete")
        _trust(cast(str, pending[0]), cast(str, pending[1]))
        if pending[0] == state.gateway_configuration_key_id:
            raise NodeClientError("Node pending configuration trust matches active trust")
        if not re.fullmatch(r"nct_[0-9a-f]{32}", cast(str, pending[2])):
            raise NodeClientError("Node pending trust transition ID is invalid")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", cast(str, pending[3])):
            raise NodeClientError("Node pending trust transition digest is invalid")
        _parse_aware_datetime(cast(str, pending[4]), "pending trust expiry")
    previous = (
        state.previous_configuration_key_id,
        state.previous_configuration_public_key,
        state.previous_trust_expires_at,
    )
    if any(value is not None for value in previous):
        if any(value is None for value in previous):
            raise NodeClientError("Node previous configuration trust state is incomplete")
        _trust(cast(str, previous[0]), cast(str, previous[1]))
        if previous[0] == state.gateway_configuration_key_id:
            raise NodeClientError("Node previous configuration trust matches active trust")
        _parse_aware_datetime(cast(str, previous[2]), "previous trust expiry")


def _validate_optional_identity_rotation_state(state: NodeState) -> None:
    pending = (
        state.pending_identity_private_key,
        state.pending_identity_public_key,
        state.pending_identity_rotation_id,
        state.pending_identity_current_key_id,
        state.pending_identity_challenge,
        state.pending_identity_challenge_digest,
        state.pending_identity_expires_at,
    )
    if not any(value is not None for value in pending):
        return
    if any(value is None for value in pending):
        raise NodeClientError("Node pending identity-key rotation state is incomplete")
    private_key, public_key, rotation_id, current_key_id, challenge, digest, expires_at = cast(
        tuple[str, str, str, str, str, str, str], pending
    )
    _validate_identity_keypair(private_key, public_key, label="pending Node identity")
    if not re.fullmatch(r"nkr_[0-9a-f]{32}", rotation_id):
        raise NodeClientError("Node pending identity-key rotation ID is invalid")
    if current_key_id != node_identity_key_id(state.public_key):
        raise NodeClientError("Node pending identity current key binding is invalid")
    if node_identity_key_id(public_key) == current_key_id:
        raise NodeClientError("Node pending identity key matches active key")
    if sha256_digest(challenge) != digest:
        raise NodeClientError("Node pending identity challenge digest is invalid")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise NodeClientError("Node pending identity challenge digest is invalid")
    _parse_aware_datetime(expires_at, "pending identity-key rotation expiry")


def _pending_identity_rotation_record(state: NodeState) -> NodeIdentityRotationRecord:
    _validate_optional_identity_rotation_state(state)
    if state.pending_identity_rotation_id is None:
        raise NodeClientError("Node has no pending identity-key rotation")
    return NodeIdentityRotationRecord(
        rotation_id=state.pending_identity_rotation_id,
        node_id=state.node_id,
        principal_id=state.principal_id,
        workspace_id=state.workspace_id,
        current_key_id=cast(str, state.pending_identity_current_key_id),
        challenge_digest=cast(str, state.pending_identity_challenge_digest),
        created_at=state.enrolled_at,
        expires_at=cast(str, state.pending_identity_expires_at),
        status="pending",
        evidence_status="complete",
        next_key_id=None,
        activated_at=None,
    )


def _validate_identity_rotation_activation_response(
    response: JsonObject,
    rotation: NodeIdentityRotationRecord,
    next_key_id: str,
) -> None:
    if (
        _required_string(response, "rotation_id") != rotation.rotation_id
        or _required_string(response, "node_id") != rotation.node_id
        or _required_string(response, "principal_id") != rotation.principal_id
        or _required_string(response, "workspace_id") != rotation.workspace_id
        or _required_string(response, "current_key_id") != rotation.current_key_id
        or _required_string(response, "expires_at") != rotation.expires_at
        or _required_string(response, "status") != "activated"
        or _required_string(response, "evidence_status") != "complete"
        or _required_string(response, "active_identity_key_id") != next_key_id
        or _required_string(response, "next_key_id") != next_key_id
    ):
        raise NodeClientError("Gateway identity-key rotation response is invalid")


def _promote_pending_identity_key(state: NodeState) -> NodeState:
    _validate_optional_identity_rotation_state(state)
    if state.pending_identity_private_key is None or state.pending_identity_public_key is None:
        raise NodeClientError("Node has no pending identity-key rotation")
    return replace(
        state,
        private_key=state.pending_identity_private_key,
        public_key=state.pending_identity_public_key,
        pending_identity_private_key=None,
        pending_identity_public_key=None,
        pending_identity_rotation_id=None,
        pending_identity_current_key_id=None,
        pending_identity_challenge=None,
        pending_identity_challenge_digest=None,
        pending_identity_expires_at=None,
    )


def _bundle_signing_key_id(bundle: JsonObject) -> str:
    signature = bundle.get("signature")
    if not isinstance(signature, dict):
        raise NodeClientError("configuration signature is invalid")
    return _required_string(signature, "key_id")


def _configuration_verification_trust(
    state: NodeState,
    signing_key_id: str,
    *,
    now: datetime | None,
) -> tuple[NodeConfigurationTrust, str]:
    effective_now = now or datetime.now(UTC)
    if signing_key_id == state.gateway_configuration_key_id:
        return _configuration_trust(state), "active"
    if signing_key_id == state.pending_configuration_key_id:
        if state.pending_configuration_public_key is None or state.pending_trust_expires_at is None:
            raise NodeClientError("Node pending configuration trust state is incomplete")
        if effective_now >= _parse_aware_datetime(
            state.pending_trust_expires_at, "pending trust expiry"
        ):
            raise NodeClientError("pending configuration trust expired")
        return _trust(signing_key_id, state.pending_configuration_public_key), "pending"
    if signing_key_id == state.previous_configuration_key_id:
        if (
            state.previous_configuration_public_key is None
            or state.previous_trust_expires_at is None
        ):
            raise NodeClientError("Node previous configuration trust state is incomplete")
        if effective_now >= _parse_aware_datetime(
            state.previous_trust_expires_at, "previous trust expiry"
        ):
            raise NodeClientError("previous configuration trust expired")
        return _trust(signing_key_id, state.previous_configuration_public_key), "previous"
    raise NodeClientError("configuration signing key is not trusted")


def _parse_aware_datetime(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise NodeClientError(f"{label} is invalid") from exc
    if parsed.tzinfo is None:
        raise NodeClientError(f"{label} must include timezone")
    return parsed.astimezone(UTC)


def _write_private_json_atomic(path: Path, document: JsonObject, *, label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(16)}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(temporary, flags, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(canonical_json(document).encode())
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise NodeClientError(f"failed to store {label}") from exc


def _read_private_json(path: Path, *, label: str) -> JsonObject:
    flags = os.O_RDONLY | (os.O_NOFOLLOW if hasattr(os, "O_NOFOLLOW") else 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise NodeClientError(f"{label} is unavailable") from exc
    try:
        status = os.fstat(descriptor)
        if not stat.S_ISREG(status.st_mode):
            raise NodeClientError(f"{label} must be a regular file")
        if stat.S_IMODE(status.st_mode) & 0o077:
            raise NodeClientError(f"{label} permissions must be 0600")
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            descriptor = -1
            document = json.load(handle)
    except NodeClientError:
        raise
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise NodeClientError(f"{label} is invalid") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if not isinstance(document, dict):
        raise NodeClientError(f"{label} is invalid")
    return cast(JsonObject, document)


def _required_string(document: JsonObject, key: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value:
        raise NodeClientError("Gateway enrollment response is incomplete")
    return value


def _optional_string(document: object, key: str) -> str | None:
    if not isinstance(document, dict):
        raise NodeClientError("Node state is invalid")
    value = document.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise NodeClientError("Node state is invalid")
    return value

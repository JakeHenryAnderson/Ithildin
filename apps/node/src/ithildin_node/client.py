"""Minimal local-preview Ithildin Node enrollment and heartbeat client."""

from __future__ import annotations

import base64
import binascii
import json
import os
import secrets
import stat
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from ithildin_api.nodes import NODE_PROTOCOL_VERSION, canonical_signature_message
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

    def safe_summary(self) -> JsonObject:
        return {
            "api_url": self.api_url,
            "node_id": self.node_id,
            "principal_id": self.principal_id,
            "workspace_id": self.workspace_id,
            "enrolled_at": self.enrolled_at,
            "private_key_present": True,
        }

    def _document(self) -> JsonObject:
        return {
            **self.safe_summary(),
            "private_key": self.private_key,
            "public_key": self.public_key,
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
        _private_key(state.private_key)
        return state


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
        return NodeState(
            api_url=self.api_url,
            node_id=_required_string(response, "node_id"),
            principal_id=_required_string(response, "principal_id"),
            workspace_id=_required_string(response, "workspace_id"),
            private_key=private_key_text,
            public_key=public_key_text,
            enrolled_at=_required_string(response, "enrolled_at"),
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
        if state.api_url != self.api_url:
            raise NodeClientError("Node state API binding mismatch")
        timestamp = str(int((now or datetime.now(UTC)).timestamp()))
        effective_nonce = nonce or secrets.token_hex(16)
        payload: JsonObject = {
            "protocol_version": NODE_PROTOCOL_VERSION,
            "node_version": node_version,
            "runner_adapter": runner_adapter,
            "deployment_topology": deployment_topology,
            "configuration_digest": configuration_digest,
        }
        if mission_id is not None:
            payload["mission_id"] = mission_id
        path = f"/nodes/{state.node_id}/heartbeat"
        message = canonical_signature_message(
            method="POST",
            path=path,
            timestamp=timestamp,
            nonce=effective_nonce,
            body_hash=sha256_digest(payload),
        )
        signature = base64.b64encode(_private_key(state.private_key).sign(message)).decode()
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


def _required_string(document: JsonObject, key: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value:
        raise NodeClientError("Gateway enrollment response is incomplete")
    return value

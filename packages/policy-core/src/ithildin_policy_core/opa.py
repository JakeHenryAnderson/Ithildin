"""Optional OPA sidecar policy evaluator."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol, cast
from urllib.error import URLError
from urllib.parse import urljoin
from urllib.request import Request, build_opener

from ithildin_schemas import (
    JsonObject,
    PolicyDecision,
    PolicyDecisionValue,
    PolicyInput,
    sha256_digest,
)
from pydantic import ValidationError

from ithildin_policy_core.opa_bundle import OpaBundleEvidence


class OpaOpener(Protocol):
    def open(self, fullurl: Request, timeout: float = ...) -> Any:
        """Open a request and return a response-like object."""


class OpaResponse(Protocol):
    def read(self) -> bytes:
        """Read the response body."""


@dataclass(frozen=True)
class OpaPolicyEvaluator:
    base_url: str
    decision_path: str
    timeout_seconds: float = 2.0
    opener: OpaOpener | None = None
    bundle_evidence: OpaBundleEvidence | None = None

    engine_name = "opa"

    def __post_init__(self) -> None:
        if not self.base_url:
            raise ValueError("OPA base URL must not be empty")
        if not self.decision_path.startswith("/"):
            raise ValueError("OPA decision path must start with /")

    @property
    def policy_hash(self) -> str:
        if self.bundle_evidence is not None:
            return self.bundle_evidence.bundle_hash
        return sha256_digest(
            {
                "engine": self.engine_name,
                "base_url": self.base_url.rstrip("/"),
                "decision_path": self.decision_path,
            }
        )

    @property
    def document_version(self) -> str:
        if self.bundle_evidence is not None:
            return self.bundle_evidence.bundle_version
        return self.decision_path

    @property
    def rule_count(self) -> int:
        return 0

    def status(self) -> JsonObject:
        status: JsonObject = {
            "engine": self.engine_name,
            "document_version": self.document_version,
            "policy_hash": self.policy_hash,
            "rule_count": self.rule_count,
            "decision_url": _decision_url(self.base_url, self.decision_path),
        }
        if self.bundle_evidence is not None:
            status.update(self.bundle_evidence.as_status())
        else:
            status["bundle_verified"] = False
        return status

    def evaluate(self, policy_input: PolicyInput) -> PolicyDecision:
        try:
            result = self._query(policy_input)
            return self._decision_from_result(result)
        except (OSError, TimeoutError, URLError, ValueError, ValidationError, json.JSONDecodeError):
            return self._fail_closed_decision()

    def _query(self, policy_input: PolicyInput) -> JsonObject:
        body = json.dumps({"input": policy_input.model_dump(mode="json")}).encode("utf-8")
        request = Request(
            _decision_url(self.base_url, self.decision_path),
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        opener = self.opener or build_opener()
        response = cast(OpaResponse, opener.open(request, timeout=self.timeout_seconds))
        payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("OPA response must be a JSON object")
        result = payload.get("result")
        if not isinstance(result, dict):
            raise ValueError("OPA response result must be a JSON object")
        return cast(JsonObject, result)

    def _decision_from_result(self, result: JsonObject) -> PolicyDecision:
        return PolicyDecision.model_validate(
            {
                "decision": result.get("decision"),
                "reason": result.get("reason", "OPA policy decision"),
                "policy_version": result.get("policy_version", self.policy_hash),
                "matched_rules": result.get("matched_rules", []),
                "obligations": result.get("obligations", {"audit_level": "full"}),
            }
        )

    def _fail_closed_decision(self) -> PolicyDecision:
        return PolicyDecision(
            decision=PolicyDecisionValue.DENY,
            reason="OPA policy evaluation failed closed",
            policy_version=self.policy_hash,
            matched_rules=[],
            obligations={"audit_level": "full", "fail_closed": True},
        )


def _decision_url(base_url: str, decision_path: str) -> str:
    return urljoin(base_url.rstrip("/") + "/", decision_path.lstrip("/"))

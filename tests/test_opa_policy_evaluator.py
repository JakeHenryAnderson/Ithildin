from __future__ import annotations

import json
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request

import pytest
from ithildin_api.config import Settings
from ithildin_api.policy import load_policy_engine
from ithildin_policy_core import OpaPolicyEvaluator, PolicyError
from ithildin_schemas import PolicyDecisionValue, PolicyInput


class FakeOpaResponse:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class FakeOpaOpener:
    def __init__(self, response: object | None = None) -> None:
        self.response = response or FakeOpaResponse(
            {
                "result": {
                    "decision": "allow",
                    "reason": "OPA allowed",
                    "matched_rules": ["opa_allow_read"],
                    "obligations": {"audit_level": "full"},
                }
            }
        )
        self.requests: list[Request] = []

    def open(self, fullurl: Request, timeout: float = 0) -> object:
        self.requests.append(fullurl)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_opa_policy_evaluator_parses_allow_decision() -> None:
    opener = FakeOpaOpener()
    evaluator = OpaPolicyEvaluator(
        base_url="http://opa.example:8181",
        decision_path="/v1/data/ithildin/decision",
        opener=opener,
    )

    decision = evaluator.evaluate(policy_input("fs.read", "read"))

    assert decision.decision == PolicyDecisionValue.ALLOW
    assert decision.reason == "OPA allowed"
    assert decision.policy_version == evaluator.policy_hash
    assert decision.matched_rules == ["opa_allow_read"]
    assert decision.obligations == {"audit_level": "full"}
    request = opener.requests[0]
    assert request.full_url == "http://opa.example:8181/v1/data/ithildin/decision"
    assert request.get_method() == "POST"
    request_data = request.data
    assert isinstance(request_data, bytes)
    assert json.loads(request_data.decode("utf-8"))["input"]["tool"]["name"] == "fs.read"


def test_opa_policy_evaluator_parses_require_approval_decision() -> None:
    opener = FakeOpaOpener(
        FakeOpaResponse(
            {
                "result": {
                    "decision": "require_approval",
                    "reason": "OPA requires approval",
                    "policy_version": "sha256:" + ("1" * 64),
                    "matched_rules": ["opa_write"],
                    "obligations": {"approval_required": True},
                }
            }
        )
    )
    evaluator = OpaPolicyEvaluator(
        base_url="http://opa.example:8181",
        decision_path="/v1/data/ithildin/decision",
        opener=opener,
    )

    decision = evaluator.evaluate(policy_input("fs.patch.apply", "write"))

    assert decision.decision == PolicyDecisionValue.REQUIRE_APPROVAL
    assert decision.reason == "OPA requires approval"
    assert decision.policy_version == "sha256:" + ("1" * 64)
    assert decision.matched_rules == ["opa_write"]


@pytest.mark.parametrize(
    "response",
    [
        URLError("offline"),
        FakeOpaResponse({"result": {"decision": "bogus"}}),
        FakeOpaResponse({"not_result": {}}),
    ],
)
def test_opa_policy_evaluator_fails_closed(response: object) -> None:
    evaluator = OpaPolicyEvaluator(
        base_url="http://opa.example:8181",
        decision_path="/v1/data/ithildin/decision",
        opener=FakeOpaOpener(response),
    )

    decision = evaluator.evaluate(policy_input("fs.read", "read"))

    assert decision.decision == PolicyDecisionValue.DENY
    assert decision.reason == "OPA policy evaluation failed closed"
    assert decision.matched_rules == []
    assert decision.obligations == {"audit_level": "full", "fail_closed": True}


def test_opa_policy_status_reports_engine_metadata() -> None:
    evaluator = OpaPolicyEvaluator(
        base_url="http://opa.example:8181",
        decision_path="/v1/data/ithildin/decision",
    )

    status = evaluator.status()

    assert status["engine"] == "opa"
    assert status["document_version"] == "/v1/data/ithildin/decision"
    assert status["policy_hash"] == evaluator.policy_hash
    assert status["rule_count"] == 0
    assert status["decision_url"] == "http://opa.example:8181/v1/data/ithildin/decision"


def test_policy_engine_loader_selects_opa_and_requires_url(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, policy_engine="opa", opa_url="http://opa.example:8181")
    evaluator = load_policy_engine(settings)

    assert evaluator.status()["engine"] == "opa"

    missing_url = make_settings(tmp_path, policy_engine="opa", opa_url="")
    with pytest.raises(PolicyError, match="ITHILDIN_OPA_URL"):
        load_policy_engine(missing_url)


def policy_input(tool_name: str, tool_risk: str) -> PolicyInput:
    return PolicyInput(
        principal={"id": "agent:test"},
        tool={"name": tool_name, "risk": tool_risk, "version": "1.0.0"},
        resource={"type": "file", "in_scope": True},
        context={"session_id": "sess_1"},
    )


def make_settings(
    tmp_path: Path,
    *,
    policy_engine: str = "yaml",
    opa_url: str = "",
) -> Settings:
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir(exist_ok=True)
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text("version: test\nrules: []\n", encoding="utf-8")
    return Settings(
        admin_token="test-admin-token",
        db_path=tmp_path / "ithildin.sqlite3",
        audit_log_path=tmp_path / "audit.jsonl",
        manifest_dir=manifest_dir,
        require_manifest_lock=False,
        policy_path=policy_path,
        policy_engine=policy_engine,
        opa_url=opa_url,
    )

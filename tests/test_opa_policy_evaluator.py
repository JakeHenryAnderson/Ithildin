from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request

import pytest
from ithildin_api.config import Settings
from ithildin_api.policy import load_policy_engine
from ithildin_policy_core import (
    OpaBundleError,
    OpaBundleEvidence,
    OpaBundleSource,
    OpaPolicyEvaluator,
    PolicyError,
    opa_bundle_hash,
    verify_opa_bundle_manifest,
)
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


def test_opa_policy_evaluator_uses_bundle_hash_when_result_has_no_policy_version(
    tmp_path: Path,
) -> None:
    bundle_evidence = write_opa_bundle(tmp_path)
    evaluator = OpaPolicyEvaluator(
        base_url="http://opa.example:8181",
        decision_path="/v1/data/ithildin/decision",
        opener=FakeOpaOpener(),
        bundle_evidence=bundle_evidence,
    )

    decision = evaluator.evaluate(policy_input("fs.read", "read"))

    assert decision.decision == PolicyDecisionValue.ALLOW
    assert decision.policy_version == bundle_evidence.bundle_hash
    assert evaluator.policy_hash == bundle_evidence.bundle_hash


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
    assert status["bundle_verified"] is False


def test_opa_policy_status_reports_verified_bundle_evidence(tmp_path: Path) -> None:
    bundle_evidence = write_opa_bundle(tmp_path)
    evaluator = OpaPolicyEvaluator(
        base_url="http://opa.example:8181",
        decision_path="/v1/data/ithildin/decision",
        bundle_evidence=bundle_evidence,
    )

    status = evaluator.status()

    assert status["engine"] == "opa"
    assert status["document_version"] == "opa-test-v1"
    assert status["policy_hash"] == bundle_evidence.bundle_hash
    assert status["bundle_version"] == "opa-test-v1"
    assert status["bundle_entrypoint"] == "ithildin/decision"
    assert status["bundle_hash"] == bundle_evidence.bundle_hash
    assert status["bundle_verified"] is True
    assert status["bundle_sources"] == [
        {"path": "ithildin.rego", "source_hash": bundle_evidence.sources[0].source_hash}
    ]


def test_policy_engine_loader_selects_opa_and_requires_url(tmp_path: Path) -> None:
    bundle_evidence = write_opa_bundle(tmp_path)
    settings = make_settings(
        tmp_path,
        policy_engine="opa",
        opa_url="http://opa.example:8181",
        opa_bundle_manifest_path=bundle_evidence.manifest_path,
    )
    evaluator = load_policy_engine(settings)

    assert evaluator.status()["engine"] == "opa"
    assert evaluator.status()["bundle_verified"] is True

    missing_url = make_settings(
        tmp_path,
        policy_engine="opa",
        opa_url="",
        opa_bundle_manifest_path=bundle_evidence.manifest_path,
    )
    with pytest.raises(PolicyError, match="ITHILDIN_OPA_URL"):
        load_policy_engine(missing_url)


def test_policy_engine_loader_requires_verified_opa_bundle(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, policy_engine="opa", opa_url="http://opa.example:8181")

    with pytest.raises(OpaBundleError, match="not found"):
        load_policy_engine(settings)


def test_opa_bundle_manifest_rejects_tampered_source(tmp_path: Path) -> None:
    evidence = write_opa_bundle(tmp_path)
    evidence.manifest_path.with_name("ithildin.rego").write_text(
        "package changed\n",
        encoding="utf-8",
    )

    with pytest.raises(OpaBundleError, match="source hash mismatch"):
        verify_opa_bundle_manifest(evidence.manifest_path)


def test_opa_bundle_manifest_rejects_missing_source(tmp_path: Path) -> None:
    evidence = write_opa_bundle(tmp_path)
    evidence.manifest_path.with_name("ithildin.rego").unlink()

    with pytest.raises(OpaBundleError, match="source not found"):
        verify_opa_bundle_manifest(evidence.manifest_path)


def test_opa_bundle_manifest_rejects_path_escape(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "opa"
    bundle_dir.mkdir()
    source_hash = "sha256:" + ("1" * 64)
    bundle_dir.joinpath("bundle.lock.json").write_text(
        json.dumps(
            {
                "bundle_manifest_version": 1,
                "bundle_version": "opa-test-v1",
                "entrypoint": "ithildin/decision",
                "bundle_hash": opa_bundle_hash(
                    bundle_version="opa-test-v1",
                    entrypoint="ithildin/decision",
                    sources=(OpaBundleSource(path="../escape.rego", source_hash=source_hash),),
                ),
                "sources": [{"path": "../escape.rego", "source_hash": source_hash}],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(OpaBundleError, match="stay under"):
        verify_opa_bundle_manifest(bundle_dir / "bundle.lock.json")


def test_opa_bundle_manifest_rejects_malformed_metadata(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "opa"
    bundle_dir.mkdir()
    bundle_dir.joinpath("bundle.lock.json").write_text(
        json.dumps({"bundle_manifest_version": 1}),
        encoding="utf-8",
    )

    with pytest.raises(OpaBundleError, match="missing bundle_version"):
        verify_opa_bundle_manifest(bundle_dir / "bundle.lock.json")


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
    opa_bundle_manifest_path: Path | None = None,
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
        opa_bundle_manifest_path=(
            opa_bundle_manifest_path or tmp_path / "opa" / "bundle.lock.json"
        ),
    )


def write_opa_bundle(tmp_path: Path) -> OpaBundleEvidence:
    bundle_dir = tmp_path / "opa"
    bundle_dir.mkdir(exist_ok=True)
    source_path = bundle_dir / "ithildin.rego"
    source_path.write_text(
        """
package ithildin

default decision := {"decision": "deny"}
""".lstrip(),
        encoding="utf-8",
    )
    source_hash = "sha256:" + hashlib.sha256(source_path.read_bytes()).hexdigest()
    bundle_hash = opa_bundle_hash(
        bundle_version="opa-test-v1",
        entrypoint="ithildin/decision",
        sources=(OpaBundleSource(path="ithildin.rego", source_hash=source_hash),),
    )
    manifest_path = bundle_dir / "bundle.lock.json"
    manifest_path.write_text(
        json.dumps(
            {
                "bundle_manifest_version": 1,
                "bundle_version": "opa-test-v1",
                "entrypoint": "ithildin/decision",
                "bundle_hash": bundle_hash,
                "sources": [{"path": "ithildin.rego", "source_hash": source_hash}],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return verify_opa_bundle_manifest(manifest_path)

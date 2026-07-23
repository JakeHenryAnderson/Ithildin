import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any, cast

import pytest
from ithildin_api.config import Settings
from ithildin_audit_core import AuditWriter
from ithildin_schemas import AuditEventType

from scripts import mission_command_control_plane_poc as poc
from scripts import mission_command_control_plane_poc_evidence_check as evidence_check


def test_poc_environment_is_allowlisted_and_proxy_free(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.invalid")
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.invalid")
    monkeypatch.setenv("ALL_PROXY", "socks5://proxy.invalid")
    monkeypatch.setenv("PATH", "/ambient/bin")
    monkeypatch.setenv("UV_INDEX_URL", "https://ambient.invalid/simple")
    monkeypatch.setenv("PIP_INDEX_URL", "https://ambient.invalid/simple")
    monkeypatch.setenv("ITHILDIN_POSTGRES_DSN", "postgresql://ambient.invalid")
    monkeypatch.setenv("ITHILDIN_OPA_URL", "https://ambient.invalid")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "ambient-secret")

    environment = poc._isolated_environment(tmp_path)

    assert environment["ITHILDIN_STORAGE_BACKEND"] == "sqlite"
    assert environment["ITHILDIN_POSTGRES_DSN"] == ""
    assert environment["ITHILDIN_POLICY_ENGINE"] == "yaml"
    assert environment["ITHILDIN_OPA_URL"] == ""
    assert environment["ITHILDIN_HTTP_ALLOWLIST"] == ""
    assert environment["ITHILDIN_OTEL_ENABLED"] == "false"
    assert environment["NO_PROXY"] == "*"
    assert environment["no_proxy"] == "*"
    assert environment["PATH"] == os.defpath
    assert environment["PYTHONNOUSERSITE"] == "1"
    assert "HTTP_PROXY" not in environment
    assert "HTTPS_PROXY" not in environment
    assert "ALL_PROXY" not in environment
    assert "UV_INDEX_URL" not in environment
    assert "PIP_INDEX_URL" not in environment
    assert "AWS_SECRET_ACCESS_KEY" not in environment
    assert {
        f"ITHILDIN_{field_name.upper()}" for field_name in Settings.model_fields
    } == {key for key in environment if key.startswith("ITHILDIN_")}
    assert all(
        key.startswith("ITHILDIN_")
        or key
        in {"PATH", "NO_PROXY", "no_proxy", "PYTHONHASHSEED", "PYTHONNOUSERSITE"}
        for key in environment
    )
    assert not any(
        isinstance(handler, urllib.request.ProxyHandler)
        for handler in cast(Any, poc.LOOPBACK_OPENER).handlers
    )


def test_gateway_startup_timeout_reaps_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "logs").mkdir()

    class FakeProcess:
        terminated = False
        waited = False

        def poll(self) -> None:
            return None

        def terminate(self) -> None:
            self.terminated = True

        def wait(self, timeout: float | None = None) -> int:
            self.waited = True
            return 0

        def kill(self) -> None:
            raise AssertionError("graceful termination should not require kill")

    process = FakeProcess()
    monotonic_values = iter([0.0, 21.0])
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(time, "monotonic", lambda: next(monotonic_values))

    with pytest.raises(RuntimeError, match="did not become healthy"):
        poc._start_gateway(tmp_path, phase="timeout-test")

    assert process.terminated is True
    assert process.waited is True


def test_stopped_gateway_is_reaped() -> None:
    class FinishedProcess:
        waited = False

        def poll(self) -> int:
            return 1

        def wait(self, timeout: float | None = None) -> int:
            self.waited = True
            return 1

        def terminate(self) -> None:
            raise AssertionError("finished process must not be terminated again")

        def kill(self) -> None:
            raise AssertionError("finished process must not be killed")

    process = FinishedProcess()

    poc._stop_gateway(process)  # type: ignore[arg-type]

    assert process.waited is True


def test_missing_live_evidence_is_not_a_candidate(tmp_path: Path) -> None:
    report = evidence_check.build_report(Path("."), tmp_path / "missing")

    assert report["valid"] is False
    assert report["claim_level"] == "mission_control_plane_candidate_ready_for_external_review"
    assert report["tool_count"] == 24
    assert "runner_launch" in report["non_claims"]
    assert "uat_acceptance" in report["non_claims"]
    assert any("missing MCC-006 evidence" in failure for failure in report["failures"])


def test_redaction_scan_rejects_forbidden_nested_keys() -> None:
    assert evidence_check._object_keys_absent(
        {"safe": [{"digest": "sha256:ok"}]},
        {"runner_output", "template_payload"},
    )
    assert not evidence_check._object_keys_absent(
        {"safe": [{"template_payload": "not permitted"}]},
        {"runner_output", "template_payload"},
    )


def test_focused_transcript_requires_every_named_passing_test() -> None:
    transcript = "\n".join(f"{name} PASSED [1%]" for name in poc.ADVERSARIAL_TESTS)
    document = {
        "returncode": 0,
        "all_selected_tests_passed": True,
        "selected_tests": list(poc.ADVERSARIAL_TESTS),
    }

    assert evidence_check._focused_transcript_valid(transcript, document)
    assert not evidence_check._focused_transcript_valid(
        transcript.replace(" PASSED ", " FAILED ", 1),
        document,
    )


@pytest.mark.parametrize("drift", ["content_edit_same_head", "missing_terminal_newline"])
def test_exact_sqlite_jsonl_comparison_rejects_noncanonical_mirror(
    tmp_path: Path,
    drift: str,
) -> None:
    database = tmp_path / "audit.sqlite3"
    audit = tmp_path / "audit.jsonl"
    writer = AuditWriter(database, audit)
    writer.initialize()
    writer.write_event(
        event_id="evt_1",
        event_type=AuditEventType.POLICY_EVALUATED,
        request_id="req_1",
        principal={"id": "agent:test"},
    )

    assert evidence_check._sqlite_jsonl_payloads_match(database, audit)
    if drift == "content_edit_same_head":
        payload = json.loads(audit.read_text(encoding="utf-8"))
        payload["principal"]["id"] = "agent:edited"
        audit.write_text(
            json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    else:
        audit.write_bytes(audit.read_bytes().removesuffix(b"\n"))
    assert not evidence_check._sqlite_jsonl_payloads_match(database, audit)


def test_live_report_receipt_summary_uses_api_response_envelope() -> None:
    summary = poc._receipt_summary(
        {
            "gateway_lifecycle_state": "runner_reported_running",
            "receipt": {
                "report_id": "mreport_" + ("a" * 32),
                "receipt_disposition": "quarantined",
                "evidence_status": "complete",
                "receipt_posture": {"quarantine_reason_code": "node_revoked"},
            },
        }
    )

    assert summary == {
        "report_id": "mreport_" + ("a" * 32),
        "receipt_disposition": "quarantined",
        "evidence_status": "complete",
        "quarantine_reason_code": "node_revoked",
    }


def test_poc_contract_and_candidate_gate_are_wired() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    gitignore = Path(".gitignore").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    index = Path("docs/codex/review-docs-index.md").read_text(encoding="utf-8")
    contract = Path(
        "docs/codex/mission-command-control-plane-poc-evidence-contract.md"
    ).read_text(encoding="utf-8")

    assert "mission-command-control-plane-poc:" in makefile
    assert "mission-command-control-plane-poc-check:" in makefile
    poc_target = makefile.partition("mission-command-control-plane-poc:")[2].partition(
        "\n\n"
    )[0]
    assert "uv run --offline python scripts/mission_command_control_plane_poc.py" in poc_target
    review_candidate = makefile.partition("review-candidate:")[2].partition("\n\n")[0]
    assert "$(MAKE) mission-command-control-plane-poc-check" in review_candidate
    assert "var/mission-command-control-plane-poc-*/" in gitignore
    poc_source = Path("scripts/mission_command_control_plane_poc.py").read_text(encoding="utf-8")
    assert 'deployment_topology="local_process"' in poc_source
    assert "local_sidecar" not in poc_source
    assert "**os.environ" not in poc_source
    assert "urllib.request.urlopen" not in poc_source
    assert "ProxyHandler({})" in poc_source
    assert '"uvicorn"' in poc_source
    assert '"pytest"' in poc_source
    assert "sys.executable" in poc_source
    assert "mission-command-control-plane-poc-evidence-contract.md" in readme
    assert "mission-command-control-plane-poc-evidence-contract.md" in index
    assert "mission_control_plane_candidate_ready_for_external_review" in contract
    assert "Current governed tool count: `24`." in contract
    assert "Ambient Environment And Transport Isolation" in contract

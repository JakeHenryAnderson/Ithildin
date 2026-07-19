import json
from pathlib import Path

import pytest
from ithildin_audit_core import AuditWriter
from ithildin_schemas import AuditEventType

from scripts import mission_command_control_plane_poc as poc
from scripts import mission_command_control_plane_poc_evidence_check as evidence_check


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
    review_candidate = makefile.partition("review-candidate:")[2].partition("\n\n")[0]
    assert "$(MAKE) mission-command-control-plane-poc-check" in review_candidate
    assert "var/mission-command-control-plane-poc-*/" in gitignore
    poc_source = Path("scripts/mission_command_control_plane_poc.py").read_text(encoding="utf-8")
    assert 'deployment_topology="local_process"' in poc_source
    assert "local_sidecar" not in poc_source
    assert "mission-command-control-plane-poc-evidence-contract.md" in readme
    assert "mission-command-control-plane-poc-evidence-contract.md" in index
    assert "mission_control_plane_candidate_ready_for_external_review" in contract
    assert "Current governed tool count: `24`." in contract

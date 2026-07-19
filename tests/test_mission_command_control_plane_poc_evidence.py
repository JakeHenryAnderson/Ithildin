import sqlite3
from pathlib import Path

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


def test_exact_sqlite_jsonl_comparison_rejects_edited_mirror(tmp_path: Path) -> None:
    database = tmp_path / "audit.sqlite3"
    audit = tmp_path / "audit.jsonl"
    payload = '{"event_hash":"sha256:committed"}'
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE audit_events (payload_json TEXT NOT NULL)")
        connection.execute("INSERT INTO audit_events (payload_json) VALUES (?)", (payload,))
        connection.commit()
    audit.write_text(payload + "\n", encoding="utf-8")

    assert evidence_check._sqlite_jsonl_payloads_match(database, audit)
    audit.write_text('{"event_hash":"sha256:edited"}\n', encoding="utf-8")
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
    assert "review-candidate: mission-command-control-plane-poc-check" in makefile
    assert "var/mission-command-control-plane-poc-*/" in gitignore
    poc_source = Path("scripts/mission_command_control_plane_poc.py").read_text(encoding="utf-8")
    assert 'deployment_topology="local_process"' in poc_source
    assert "local_sidecar" not in poc_source
    assert "mission-command-control-plane-poc-evidence-contract.md" in readme
    assert "mission-command-control-plane-poc-evidence-contract.md" in index
    assert "mission_control_plane_candidate_ready_for_external_review" in contract
    assert "Current governed tool count: `24`." in contract

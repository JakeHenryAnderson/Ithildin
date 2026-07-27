from __future__ import annotations

from scripts import enterprise_e1_evidence_check


def test_enterprise_e1_evidence_contract_is_receiver_neutral_and_bounded() -> None:
    report = enterprise_e1_evidence_check.build_report(
        enterprise_e1_evidence_check.ROOT
    )

    assert report["valid"] is True, report["failures"]
    assert report["tool_count"] == 24
    assert report["manifest_tool_count"] == 24
    assert report["sections"] == enterprise_e1_evidence_check.EXPECTED_SECTIONS
    assert report["section_count"] == 7
    assert report["receiver_neutral"] is True
    assert report["local_content_integrity_only"] is True
    assert report["external_delivery_performed"] is False
    assert report["new_governed_tool"] is False
    assert report["human_uat_complete"] is False

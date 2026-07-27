from __future__ import annotations

from scripts import enterprise_e1_cockpit_check


def test_enterprise_e1_cockpit_contract_is_accessible_and_bounded() -> None:
    report = enterprise_e1_cockpit_check.build_report(
        enterprise_e1_cockpit_check.ROOT
    )

    assert report["valid"] is True, report["failures"]
    assert report["tool_count"] == 24
    assert report["manifest_tool_count"] == 24
    assert report["surfaces"] == enterprise_e1_cockpit_check.EXPECTED_SURFACES
    assert report["surface_count"] == 7
    assert report["truth_sources"] == (
        enterprise_e1_cockpit_check.EXPECTED_TRUTH_SOURCES
    )
    assert report["action_count"] == 7
    assert report["gateway_authoritative"] is True
    assert report["command_center_execution_authority"] is False
    assert report["new_governed_tool"] is False
    assert report["human_uat_complete"] is False

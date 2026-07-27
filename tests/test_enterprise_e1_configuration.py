from __future__ import annotations

from scripts import enterprise_e1_configuration_check


def test_enterprise_e1_configuration_contract_is_closed_and_bounded() -> None:
    report = enterprise_e1_configuration_check.build_report(
        enterprise_e1_configuration_check.ROOT
    )

    assert report["valid"] is True, report["failures"]
    assert report["tool_count"] == 24
    assert report["states"] == enterprise_e1_configuration_check.EXPECTED_STATES
    assert report["state_count"] == 7
    assert report["trust_rotation_state_count"] == 5
    assert report["new_governed_tool"] is False
    assert report["gateway_authoritative"] is True
    assert report["human_uat_complete"] is False

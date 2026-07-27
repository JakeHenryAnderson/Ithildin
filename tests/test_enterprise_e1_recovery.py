from scripts import enterprise_e1_recovery_check


def test_enterprise_e1_recovery_contract_is_bounded() -> None:
    report = enterprise_e1_recovery_check.build_report(
        enterprise_e1_recovery_check.ROOT
    )

    assert report["valid"] is True, report["failures"]
    assert report["tool_count"] == 24
    assert report["downgrade_posture"] == "restore_only"
    assert report["optional_node_automatic_restore"] is False
    assert report["ambiguous_state_overwrite_allowed"] is False
    assert report["new_governed_power"] is False
    assert report["human_uat_complete"] is False

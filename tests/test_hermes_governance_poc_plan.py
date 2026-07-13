from pathlib import Path

from scripts import hermes_governance_poc_plan_check


def test_hermes_governance_poc_plan_is_valid() -> None:
    report = hermes_governance_poc_plan_check.build_report(Path("."))

    assert report["valid"], report["failures"]
    assert report["tool_count"] == 24
    assert report["track_a_compatibility_allowed"] is True
    assert report["track_b_runtime_expansion_allowed"] is False
    assert report["mission_orchestration_allowed"] is False
    assert report["remote_mcp_allowed"] is False
    assert report["new_governed_tools_allowed"] is False

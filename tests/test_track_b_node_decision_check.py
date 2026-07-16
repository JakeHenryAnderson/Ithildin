from pathlib import Path

from scripts import track_b_node_decision_check


def test_track_b_node_decision_is_narrow_and_valid() -> None:
    report = track_b_node_decision_check.build_report(Path("."))

    assert report["valid"], report["failures"]
    assert report["tool_count"] == 24
    assert report["limited_enrollment_identity_slice_allowed"] is True
    assert report["node_tool_execution_allowed"] is False
    assert report["remote_mcp_allowed"] is False
    assert report["runner_lifecycle_allowed"] is False
    assert report["production_identity_allowed"] is False
    assert report["historical_external_review_mutated"] is False

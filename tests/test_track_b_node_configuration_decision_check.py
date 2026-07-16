from __future__ import annotations

from pathlib import Path

from scripts.track_b_node_configuration_decision_check import build_report


def test_track_b_node_configuration_decision_packet_is_bounded() -> None:
    report = build_report(Path.cwd())

    assert report["valid"] is True, report["failures"]
    assert report["tool_count"] == 24
    assert report["signed_configuration_distribution_allowed"] is True
    assert report["stored_configuration_enforcement_claim_allowed"] is False
    assert report["node_tool_execution_allowed"] is False
    assert report["remote_mcp_allowed"] is False

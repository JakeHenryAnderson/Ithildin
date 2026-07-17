from __future__ import annotations

from pathlib import Path

from scripts.track_b_node_governed_access_decision_check import build_report


def test_track_b_node_governed_access_decision_packet_is_bounded() -> None:
    report = build_report(Path.cwd())

    assert report["valid"] is True, report["failures"]
    assert report["tool_count"] == 24
    assert report["node_read_only_governed_access_allowed"] is True
    assert report["node_write_access_allowed"] is False
    assert report["node_network_access_allowed"] is False
    assert report["offline_execution_allowed"] is False
    assert report["runner_control_allowed"] is False
    assert report["remote_mcp_allowed"] is False
    assert report["observed_evidence_check_available"] is True

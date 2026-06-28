from __future__ import annotations

import pytest

SLOW_PACKET_NAME_MARKERS = (
    "bundle",
    "packet",
    "outbox",
    "handoff",
    "external_review",
    "external_response",
    "response_kit",
    "response_dry_run",
    "observed_demo",
    "sandbox_vm",
    "mission_control",
    "north_star",
    "review_candidate",
    "manifest",
    "readiness",
    "checkpoint",
    "status_board",
    "progress_model",
    "dependency_ladder",
    "transition_map",
    "command_matrix",
    "drill",
)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark recursive generated-artifact tests so fast dev gates can skip them."""
    for item in items:
        if not item.nodeid.startswith("tests/test_release_readiness.py::"):
            continue
        name = item.name.lower()
        if any(marker in name for marker in SLOW_PACKET_NAME_MARKERS):
            item.add_marker(pytest.mark.slow_packet)

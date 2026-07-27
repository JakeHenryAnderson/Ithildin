from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from scripts import enterprise_e1_single_site_rehearsal


def _report() -> dict[str, object]:
    return {
        "result": "passed",
        "candidate": {
            "runtime_candidate_posture": "unreviewed_local",
            "reviewed_runtime_candidate": False,
        },
        "topology": {"services": ["ithildin-api", "ithildin-ui"]},
        "observations": {
            "gateway_http_ready": True,
            "command_center_http_reachable": True,
            "authenticated_tool_count": 24,
            "storage_backend": "sqlite",
            "runtime_candidate_posture": "unreviewed_local",
            "exact_project_shutdown_complete": True,
        },
        "authority": {
            "docker_lifecycle_authority_granted_to_ithildin": False,
            "new_governed_power_authorized": False,
            "production_authorized": False,
            "promotion_allowed": False,
            "release_allowed": False,
            "human_uat_complete": False,
        },
        "cleanup": {"exact_project_removed": True},
    }


def test_rehearsal_report_preserves_boundary() -> None:
    enterprise_e1_single_site_rehearsal.validate_report(_report())


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("candidate", "reviewed_runtime_candidate"), True),
        (("observations", "authenticated_tool_count"), 25),
        (("authority", "production_authorized"), True),
        (("cleanup", "exact_project_removed"), False),
    ],
)
def test_rehearsal_report_rejects_false_claims(
    path: tuple[str, str],
    value: object,
) -> None:
    report = deepcopy(_report())
    section = report[path[0]]
    assert isinstance(section, dict)
    section[path[1]] = value

    with pytest.raises(enterprise_e1_single_site_rehearsal.RehearsalError):
        enterprise_e1_single_site_rehearsal.validate_report(report)


def test_rehearsal_root_is_confined() -> None:
    base = enterprise_e1_single_site_rehearsal.EVIDENCE_BASE
    valid = base / "20260727T120000Z-0123456789abcdef"
    assert enterprise_e1_single_site_rehearsal.confined_run_root(valid) == valid
    with pytest.raises(enterprise_e1_single_site_rehearsal.RehearsalError):
        enterprise_e1_single_site_rehearsal.confined_run_root(
            Path("/tmp/20260727T120000Z-0123456789abcdef")
        )

from __future__ import annotations

import pytest
from ithildin_api.node_versions import node_version_posture, parse_node_version


@pytest.mark.parametrize(
    ("value", "parsed"),
    [("0.0.0", (0, 0, 0)), ("1.2.3", (1, 2, 3)), ("4294967295.0.1", (4294967295, 0, 1))],
)
def test_parse_node_version_accepts_closed_grammar(
    value: str, parsed: tuple[int, int, int]
) -> None:
    assert parse_node_version(value) == parsed


@pytest.mark.parametrize(
    "value",
    ["1", "1.2", "1.2.3.4", "01.2.3", "1.02.3", "1.2.03", "1.2.3-rc1", "v1.2.3", "4294967296.0.0"],
)
def test_parse_node_version_rejects_ambiguous_or_unbounded_versions(value: str) -> None:
    with pytest.raises(ValueError):
        parse_node_version(value)


@pytest.mark.parametrize(
    ("observed", "minimum", "expected"),
    [
        ("1.2.2", "1.2.3", "below_minimum"),
        ("1.2.3", "1.2.3", "meets_minimum"),
        ("2.0.0", "1.9.9", "meets_minimum"),
    ],
)
def test_node_version_posture_compares_integer_tuples(
    observed: str, minimum: str, expected: str
) -> None:
    assert (
        node_version_posture(
            node_status="enrolled",
            node_evidence_status="complete",
            desired_assigned=True,
            desired_evidence_complete=True,
            observed_version=observed,
            minimum_version=minimum,
        )
        == expected
    )


def test_node_version_posture_prioritizes_revocation_and_incomplete_evidence() -> None:
    assert (
        node_version_posture(
            node_status="revoked",
            node_evidence_status="pending",
            desired_assigned=True,
            desired_evidence_complete=False,
            observed_version="1.0.0",
            minimum_version="1.0.0",
        )
        == "revoked"
    )
    assert (
        node_version_posture(
            node_status="enrolled",
            node_evidence_status="pending",
            desired_assigned=False,
            desired_evidence_complete=False,
            observed_version=None,
            minimum_version=None,
        )
        == "evidence_incomplete"
    )

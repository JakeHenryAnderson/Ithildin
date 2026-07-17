"""Closed Node software-version validation and posture derivation."""

from __future__ import annotations

import re
from typing import Literal

NodeVersionPosture = Literal[
    "unassigned",
    "never_observed",
    "meets_minimum",
    "below_minimum",
    "evidence_incomplete",
    "revoked",
]

_VERSION_PATTERN = re.compile(r"^(0|[1-9][0-9]{0,9})\.(0|[1-9][0-9]{0,9})\.(0|[1-9][0-9]{0,9})$")
_MAX_COMPONENT = 4_294_967_295


def parse_node_version(value: str) -> tuple[int, int, int]:
    match = _VERSION_PATTERN.fullmatch(value)
    if match is None:
        raise ValueError("Node version must use MAJOR.MINOR.PATCH")
    major, minor, patch = (int(component) for component in match.groups())
    parsed = (major, minor, patch)
    if any(component > _MAX_COMPONENT for component in parsed):
        raise ValueError("Node version component is too large")
    return parsed


def validate_node_version(value: str) -> str:
    parse_node_version(value)
    return value


def node_version_posture(
    *,
    node_status: str,
    node_evidence_status: str,
    desired_assigned: bool,
    desired_evidence_complete: bool,
    observed_version: str | None,
    minimum_version: str | None,
) -> NodeVersionPosture:
    if node_status == "revoked":
        return "revoked"
    if node_evidence_status != "complete":
        return "evidence_incomplete"
    if not desired_assigned:
        return "unassigned"
    if not desired_evidence_complete or minimum_version is None:
        return "evidence_incomplete"
    try:
        minimum = parse_node_version(minimum_version)
    except ValueError:
        return "evidence_incomplete"
    if observed_version is None:
        return "never_observed"
    try:
        observed = parse_node_version(observed_version)
    except ValueError:
        return "evidence_incomplete"
    return "below_minimum" if observed < minimum else "meets_minimum"

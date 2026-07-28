"""Build and verify a deterministic, test-only Enterprise E2 scale fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path, PureWindowsPath
from typing import Any

E1_CANDIDATE = "02e39d57a6d38a14d959bb88a32da79fe34e4e13"
SCHEMA_VERSION = "ithildin.enterprise-e2.scale-fixture.v1"
FIXTURE_ID = "single_org_medium_synthetic"
FIXED_GENERATED_AT = "2026-07-28T00:00:00Z"
CONFIGURATION_STATES = (
    "desired",
    "acknowledged",
    "stored",
    "enforced",
    "stale",
    "rejected",
    "rollback",
)
EXPECTED_COUNTS = {
    "workspaces": 8,
    "missions": 96,
    "nodes": 64,
    "configuration_cohorts": 8,
    "version_cohorts": 4,
    "approvals": 48,
    "evidence": 144,
    "attention": 24,
}
AUTHORITY = {
    "runtime_import_allowed": False,
    "runtime_identity_allowed": False,
    "production_identity_allowed": False,
    "enterprise_rbac_allowed": False,
    "remote_admin_allowed": False,
    "new_governed_tool_allowed": False,
    "performance_certification_allowed": False,
    "supported_scale_claim_allowed": False,
    "human_uat_complete": False,
}
NONCLAIMS = (
    "production identity",
    "enterprise RBAC",
    "remote administration",
    "runtime PostgreSQL",
    "supported scale",
    "performance certification",
    "human UAT completion",
    "production readiness",
)
FORBIDDEN_KEYS = {
    "access_token",
    "authorization",
    "client_secret",
    "cookie",
    "dsn",
    "email",
    "password",
    "private_key",
    "refresh_token",
    "secret",
    "token",
}
TOP_LEVEL_KEYS = {
    "schema_version",
    "fixture_id",
    "generated_at",
    "status",
    "e1_candidate_commit",
    "tool_count",
    "organization_scope",
    "counts",
    "workspaces",
    "missions",
    "nodes",
    "configuration_cohorts",
    "version_cohorts",
    "approvals",
    "evidence",
    "attention",
    "authority",
    "nonclaims",
}
COLLECTION_KEYS = {
    "workspaces": {"workspace_id", "status", "authority_source"},
    "missions": {
        "mission_id",
        "workspace_id",
        "gateway_state",
        "runner_reported_state",
        "model_provider_state",
        "attention_required",
    },
    "nodes": {
        "node_id",
        "workspace_id",
        "connectivity_state",
        "runner_health_state",
        "configuration_state",
        "software_version",
    },
    "configuration_cohorts": {
        "cohort_id",
        "workspace_id",
        "state",
        "node_count",
        "authority_source",
    },
    "version_cohorts": {
        "cohort_id",
        "software_version",
        "node_count",
        "observation_source",
    },
    "approvals": {
        "approval_id",
        "mission_id",
        "workspace_id",
        "decision_state",
        "application_state",
        "authority_source",
    },
    "evidence": {
        "evidence_id",
        "mission_id",
        "source",
        "authoritative",
        "digest",
    },
    "attention": {
        "attention_id",
        "subject_type",
        "subject_id",
        "severity",
        "authority_source",
    },
}


class ScaleFixtureError(RuntimeError):
    """Raised when a scale fixture cannot be built or verified safely."""


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
    ).encode("utf-8")


def build_fixture() -> dict[str, Any]:
    workspaces = [
        {
            "workspace_id": f"workspace_{index:02d}",
            "status": "active",
            "authority_source": "gateway",
        }
        for index in range(EXPECTED_COUNTS["workspaces"])
    ]
    workspace_ids = [item["workspace_id"] for item in workspaces]
    workspace_configuration_states = {
        workspace_id: CONFIGURATION_STATES[index % len(CONFIGURATION_STATES)]
        for index, workspace_id in enumerate(workspace_ids)
    }
    gateway_states = ("queued", "admitted", "running", "completed", "denied")
    runner_states = ("not_reported", "accepted", "running", "completed")
    missions = [
        {
            "mission_id": f"mission_{index:03d}",
            "workspace_id": workspace_ids[index % len(workspace_ids)],
            "gateway_state": gateway_states[index % len(gateway_states)],
            "runner_reported_state": runner_states[index % len(runner_states)],
            "model_provider_state": "unknown",
            "attention_required": index % 8 == 0,
        }
        for index in range(EXPECTED_COUNTS["missions"])
    ]
    connectivity_states = ("connected", "stale", "unreachable", "revoked")
    nodes = [
        {
            "node_id": f"node_{index:03d}",
            "workspace_id": workspace_ids[index % len(workspace_ids)],
            "connectivity_state": connectivity_states[index % len(connectivity_states)],
            "runner_health_state": "unknown",
            "configuration_state": workspace_configuration_states[
                workspace_ids[index % len(workspace_ids)]
            ],
            "software_version": f"1.{index % 4}.0-e1",
        }
        for index in range(EXPECTED_COUNTS["nodes"])
    ]
    configuration_cohorts = [
        {
            "cohort_id": f"configuration_cohort_{index:02d}",
            "workspace_id": workspace_ids[index],
            "state": workspace_configuration_states[workspace_ids[index]],
            "node_count": sum(
                node["workspace_id"] == workspace_ids[index]
                for node in nodes
            ),
            "authority_source": "gateway",
        }
        for index in range(EXPECTED_COUNTS["configuration_cohorts"])
    ]
    version_cohorts = [
        {
            "cohort_id": f"version_cohort_{index:02d}",
            "software_version": f"1.{index}.0-e1",
            "node_count": sum(
                node["software_version"] == f"1.{index}.0-e1" for node in nodes
            ),
            "observation_source": "gateway_node_inventory",
        }
        for index in range(EXPECTED_COUNTS["version_cohorts"])
    ]
    approval_states = ("pending", "approved", "denied", "expired")
    application_states = ("not_started", "applied", "not_applicable", "not_started")
    approvals = [
        {
            "approval_id": f"approval_{index:03d}",
            "mission_id": missions[index * 2]["mission_id"],
            "workspace_id": missions[index * 2]["workspace_id"],
            "decision_state": approval_states[index % len(approval_states)],
            "application_state": application_states[index % len(application_states)],
            "authority_source": "gateway",
        }
        for index in range(EXPECTED_COUNTS["approvals"])
    ]
    evidence_sources = ("gateway", "gateway", "runner")
    evidence = []
    for index in range(EXPECTED_COUNTS["evidence"]):
        source = evidence_sources[index % len(evidence_sources)]
        evidence.append(
            {
                "evidence_id": f"evidence_{index:03d}",
                "mission_id": missions[index % len(missions)]["mission_id"],
                "source": source,
                "authoritative": source == "gateway",
                "digest": "sha256:"
                + hashlib.sha256(f"evidence_{index:03d}".encode()).hexdigest(),
            }
        )
    subject_types = ("mission", "node", "approval")
    subject_collections: dict[str, list[dict[str, Any]]] = {
        "mission": missions,
        "node": nodes,
        "approval": approvals,
    }
    subject_keys = {
        "mission": "mission_id",
        "node": "node_id",
        "approval": "approval_id",
    }
    attention = []
    for index in range(EXPECTED_COUNTS["attention"]):
        subject_type = subject_types[index % len(subject_types)]
        subjects = subject_collections[subject_type]
        attention.append(
            {
                "attention_id": f"attention_{index:03d}",
                "subject_type": subject_type,
                "subject_id": subjects[index % len(subjects)][subject_keys[subject_type]],
                "severity": ("low", "medium", "high")[index % 3],
                "authority_source": "gateway",
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "fixture_id": FIXTURE_ID,
        "generated_at": FIXED_GENERATED_AT,
        "status": "synthetic_test_only_not_runtime_importable",
        "e1_candidate_commit": E1_CANDIDATE,
        "tool_count": 24,
        "organization_scope": "single_organization_synthetic_only",
        "counts": dict(EXPECTED_COUNTS),
        "workspaces": workspaces,
        "missions": missions,
        "nodes": nodes,
        "configuration_cohorts": configuration_cohorts,
        "version_cohorts": version_cohorts,
        "approvals": approvals,
        "evidence": evidence,
        "attention": attention,
        "authority": dict(AUTHORITY),
        "nonclaims": list(NONCLAIMS),
    }


def validate_fixture(payload: object) -> list[str]:
    failures: list[str] = []
    if not isinstance(payload, dict):
        return ["fixture must be an object"]
    if set(payload) != TOP_LEVEL_KEYS:
        failures.append("fixture top-level keys are not closed")
    expected_scalars = {
        "schema_version": SCHEMA_VERSION,
        "fixture_id": FIXTURE_ID,
        "generated_at": FIXED_GENERATED_AT,
        "status": "synthetic_test_only_not_runtime_importable",
        "e1_candidate_commit": E1_CANDIDATE,
        "tool_count": 24,
        "organization_scope": "single_organization_synthetic_only",
    }
    for key, expected in expected_scalars.items():
        if payload.get(key) != expected:
            failures.append(f"fixture scalar is invalid: {key}")
    if payload.get("counts") != EXPECTED_COUNTS:
        failures.append("fixture counts are not exact")
    if payload.get("authority") != AUTHORITY:
        failures.append("fixture authority boundary is not exact")
    if payload.get("nonclaims") != list(NONCLAIMS):
        failures.append("fixture nonclaims are not exact and ordered")

    collections: dict[str, list[dict[str, Any]]] = {}
    for key, expected_count in EXPECTED_COUNTS.items():
        value = payload.get(key)
        if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
            failures.append(f"fixture collection is invalid: {key}")
            collections[key] = []
        else:
            collections[key] = value
            if len(value) != expected_count:
                failures.append(f"fixture collection count is invalid: {key}")
            if any(set(item) != COLLECTION_KEYS[key] for item in value):
                failures.append(f"fixture collection keys are not closed: {key}")

    workspace_ids = _unique_ids(collections["workspaces"], "workspace_id", failures)
    mission_ids = _unique_ids(collections["missions"], "mission_id", failures)
    node_ids = _unique_ids(collections["nodes"], "node_id", failures)
    approval_ids = _unique_ids(collections["approvals"], "approval_id", failures)
    _unique_ids(collections["configuration_cohorts"], "cohort_id", failures)
    _unique_ids(collections["version_cohorts"], "cohort_id", failures)
    _unique_ids(collections["evidence"], "evidence_id", failures)
    _unique_ids(collections["attention"], "attention_id", failures)

    for mission in collections["missions"]:
        if mission.get("workspace_id") not in workspace_ids:
            failures.append("mission references an unknown workspace")
        if mission.get("model_provider_state") != "unknown":
            failures.append("mission fixture overclaims model-provider state")
    for node in collections["nodes"]:
        if node.get("workspace_id") not in workspace_ids:
            failures.append("Node references an unknown workspace")
        if node.get("runner_health_state") != "unknown":
            failures.append("Node fixture overclaims runner health")
    observed_states = {
        str(item.get("state")) for item in collections["configuration_cohorts"]
    }
    if observed_states != set(CONFIGURATION_STATES):
        failures.append("configuration state semantics are incomplete")
    nodes_by_workspace: dict[str, list[dict[str, Any]]] = {
        workspace_id: [] for workspace_id in workspace_ids
    }
    for node in collections["nodes"]:
        workspace_id = node.get("workspace_id")
        if isinstance(workspace_id, str) and workspace_id in nodes_by_workspace:
            nodes_by_workspace[workspace_id].append(node)
    for cohort in collections["configuration_cohorts"]:
        workspace_id = cohort.get("workspace_id")
        state = cohort.get("state")
        cohort_nodes = (
            nodes_by_workspace.get(workspace_id, [])
            if isinstance(workspace_id, str)
            else []
        )
        if (
            workspace_id not in workspace_ids
            or cohort.get("node_count") != len(cohort_nodes)
            or any(node.get("configuration_state") != state for node in cohort_nodes)
        ):
            failures.append("configuration cohort membership is inconsistent")
    mission_by_id = {
        str(item.get("mission_id")): item for item in collections["missions"]
    }
    for approval in collections["approvals"]:
        linked_mission = mission_by_id.get(str(approval.get("mission_id")))
        if linked_mission is None or approval.get("workspace_id") != linked_mission.get(
            "workspace_id"
        ):
            failures.append("approval mission/workspace correlation is invalid")
    for item in collections["evidence"]:
        if item.get("mission_id") not in mission_ids:
            failures.append("evidence references an unknown mission")
        source = item.get("source")
        if item.get("authoritative") is not (source == "gateway"):
            failures.append("evidence source authority is ambiguous")
        digest = item.get("digest")
        if (
            not isinstance(digest, str)
            or not digest.startswith("sha256:")
            or len(digest) != 71
        ):
            failures.append("evidence digest is invalid")
    subjects = {
        "mission": mission_ids,
        "node": node_ids,
        "approval": approval_ids,
    }
    for item in collections["attention"]:
        subject_type = item.get("subject_type")
        if not isinstance(subject_type, str) or subject_type not in subjects:
            failures.append("Attention subject type is invalid")
        elif item.get("subject_id") not in subjects[subject_type]:
            failures.append("Attention item references an unknown subject")

    _scan_sensitive(payload, failures)
    return failures


def build_report(payload: object | None = None) -> dict[str, Any]:
    fixture = build_fixture() if payload is None else payload
    failures = validate_fixture(fixture)
    return {
        "valid": not failures,
        "failures": failures,
        "schema_version": (
            fixture.get("schema_version") if isinstance(fixture, dict) else None
        ),
        "fixture_id": fixture.get("fixture_id") if isinstance(fixture, dict) else None,
        "tool_count": fixture.get("tool_count") if isinstance(fixture, dict) else None,
        "counts": fixture.get("counts") if isinstance(fixture, dict) else None,
        "canonical_sha256": hashlib.sha256(canonical_bytes(fixture)).hexdigest(),
        "runtime_import_allowed": False,
        "production_identity_allowed": False,
        "supported_scale_claim_allowed": False,
        "human_uat_complete": False,
    }


def _unique_ids(
    items: list[dict[str, Any]],
    key: str,
    failures: list[str],
) -> set[str]:
    identifiers = [item.get(key) for item in items]
    if any(not isinstance(identifier, str) or not identifier for identifier in identifiers):
        failures.append(f"fixture identifiers are invalid: {key}")
        return set()
    string_ids = [str(identifier) for identifier in identifiers]
    if len(set(string_ids)) != len(string_ids):
        failures.append(f"fixture identifiers are not unique: {key}")
    return set(string_ids)


def _scan_sensitive(value: object, failures: list[str], *, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key.casefold() in FORBIDDEN_KEYS:
                failures.append(f"fixture contains forbidden key at {path}.{key}")
            _scan_sensitive(item, failures, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _scan_sensitive(item, failures, path=f"{path}[{index}]")
    elif isinstance(value, str):
        if Path(value).is_absolute() or PureWindowsPath(value).is_absolute():
            failures.append(f"fixture contains an absolute path at {path}")
        if "://" in value:
            failures.append(f"fixture contains a network endpoint at {path}")


def _closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_fixture(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_closed_object)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ScaleFixtureError(f"fixture cannot be loaded: {exc}") from exc


def write_fixture(path: Path) -> None:
    if not path.is_absolute():
        raise ScaleFixtureError("fixture output path must be absolute")
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise ScaleFixtureError(
            "fixture output parent must be an existing non-symlink directory"
        )
    try:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(canonical_bytes(build_fixture()).decode("utf-8"))
    except (OSError, UnicodeError) as exc:
        raise ScaleFixtureError(f"fixture cannot be published exclusively: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check")
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--output", required=True, type=Path)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--fixture", required=True, type=Path)
    args = parser.parse_args()

    try:
        if args.command == "build":
            write_fixture(args.output)
            report = build_report(load_fixture(args.output))
        elif args.command == "verify":
            report = build_report(load_fixture(args.fixture))
        else:
            report = build_report()
    except ScaleFixtureError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

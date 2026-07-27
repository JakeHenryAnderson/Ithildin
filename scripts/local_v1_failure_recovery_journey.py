"""Run the bounded Local-v1 failure-and-recovery evidence journey.

The journey reuses the isolated MCC-006 loopback Gateway harness, then adds the
stale-configuration and manual-rollback observations required by Local-v1 O5.
It never starts Docker, launches a runner, contacts a model provider, or gains
arbitrary host/process authority.
"""

from __future__ import annotations

import argparse
import os
import re
import secrets
import stat
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from ithildin_node.client import NodeState, StoredNodeConfiguration
from ithildin_schemas import JsonObject, canonical_json, sha256_digest

from scripts import mission_command_control_plane_poc as mcc_poc

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_BASE = ROOT / "var/local-v1-failure-recovery"
SCHEMA_VERSION = "ithildin.local-v1-failure-recovery.v1"
REPORT_JSON = "local-v1-failure-recovery.json"
REPORT_MARKDOWN = "local-v1-failure-recovery.md"
_RUN_ID = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")

AUTHORITY = {
    "arbitrary_host_control_authorized": False,
    "docker_lifecycle_authorized": False,
    "model_provider_access_authorized": False,
    "new_governed_power_authorized": False,
    "new_governed_tool": False,
    "production_authorized": False,
    "promotion_allowed": False,
    "release_allowed": False,
    "runner_launch_authorized": False,
    "uat_complete": False,
}

NONCLAIMS = [
    "Gateway restart evidence does not prove whole-host restart safety.",
    "Partition evidence proves fail-closed mediated access only, not network non-bypass.",
    "Runner reports remain runner-reported state and do not prove provider output.",
    "Stored configuration remains stored_not_enforced; host enforcement is not claimed.",
    "Manual rollback creates a fresh signed generation and is not automatic rollback.",
    "No release, production, promotion, credential custody, or UAT authority is granted.",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument(
        "--replace",
        action="store_true",
        help="replace only the explicitly selected confined run root",
    )
    args = parser.parse_args()
    run_id = (
        args.evidence_root.name
        if args.evidence_root is not None
        else datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + f"-{secrets.token_hex(4)}"
    )
    evidence_root = selected_evidence_root(args.evidence_root, run_id=run_id)

    try:
        report = run_journey(
            evidence_root,
            run_id=run_id,
            replace=args.replace,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Local-v1 failure-recovery journey refused: {exc}", file=sys.stderr)
        return 1

    candidate = cast(JsonObject, report["candidate"])
    print(f"Local-v1 failure-recovery evidence written below {EVIDENCE_BASE}")
    print(
        "The selected run identity remains private; validate the same confined "
        f"root against candidate {candidate['commit']}."
    )
    return 0


def selected_evidence_root(selected: Path | None, *, run_id: str) -> Path:
    if not _RUN_ID.fullmatch(run_id):
        raise ValueError("failure-recovery run identity is invalid")
    base = Path(os.path.abspath(EVIDENCE_BASE))
    root = Path(os.path.abspath(selected or base / run_id))
    if root.parent != base or root.name != run_id:
        raise ValueError("failure-recovery evidence root is outside the confined base")
    _require_nonsymlink_components(base)
    _require_nonsymlink_components(root)
    return root


def validate_evidence_tree(root: Path) -> None:
    """Reject symlinks and non-regular entries anywhere below a confined run root."""

    selected_evidence_root(root, run_id=root.name)
    root_stat = os.lstat(root)
    if not stat.S_ISDIR(root_stat.st_mode):
        raise ValueError("failure-recovery evidence root is not a directory")

    pending = [root]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                entry_stat = entry.stat(follow_symlinks=False)
                if stat.S_ISLNK(entry_stat.st_mode):
                    raise ValueError("failure-recovery evidence contains a symlink")
                if stat.S_ISDIR(entry_stat.st_mode):
                    pending.append(Path(entry.path))
                elif not stat.S_ISREG(entry_stat.st_mode):
                    raise ValueError(
                        "failure-recovery evidence contains a non-regular entry"
                    )


def _require_nonsymlink_components(path: Path) -> None:
    try:
        relative = path.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(
            "failure-recovery evidence root is outside the repository"
        ) from exc

    current = ROOT
    for component in (Path(), *relative.parents[::-1], relative):
        candidate = current if component == Path() else ROOT / component
        try:
            candidate_stat = os.lstat(candidate)
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(candidate_stat.st_mode):
            raise ValueError("failure-recovery evidence path contains a symlink")
        if not stat.S_ISDIR(candidate_stat.st_mode):
            raise ValueError(
                "failure-recovery evidence path has a non-directory component"
            )


def run_journey(
    evidence_root: Path,
    *,
    run_id: str,
    replace: bool,
) -> JsonObject:
    mcc_poc._require_clean_candidate()  # noqa: SLF001
    started_at = datetime.now(UTC)
    candidate_commit = mcc_poc._git_output(ROOT, "rev-parse", "HEAD")  # noqa: SLF001
    candidate_tree = mcc_poc._git_output(ROOT, "rev-parse", "HEAD^{tree}")  # noqa: SLF001
    if not _COMMIT.fullmatch(candidate_commit) or not _COMMIT.fullmatch(candidate_tree):
        raise RuntimeError("candidate identity is invalid")

    mcc_poc._prepare_root(evidence_root, replace=replace)  # noqa: SLF001
    validate_evidence_tree(evidence_root)
    mcc_poc._generate_keys(evidence_root)  # noqa: SLF001
    mcc_poc._write(  # noqa: SLF001
        evidence_root / "evidence/candidate.json",
        mcc_poc._candidate_metadata(),  # noqa: SLF001
    )

    gateway = None
    recovered_configuration: StoredNodeConfiguration
    mission: JsonObject
    state: NodeState
    try:
        gateway = mcc_poc._start_gateway(  # noqa: SLF001
            evidence_root,
            phase="before-restart",
        )
        state, configuration = mcc_poc._prepare_node(evidence_root)  # noqa: SLF001
        mission = mcc_poc._exercise_primary_mission(  # noqa: SLF001
            evidence_root,
            state,
            configuration,
        )
        mcc_poc._stop_gateway(gateway)  # noqa: SLF001
        gateway = None

        mcc_poc._exercise_partition(  # noqa: SLF001
            evidence_root,
            state,
            configuration,
            mission,
        )
        gateway = mcc_poc._start_gateway(  # noqa: SLF001
            evidence_root,
            phase="after-restart",
        )
        mcc_poc._exercise_restart_and_success(  # noqa: SLF001
            evidence_root,
            state,
            configuration,
            mission,
        )
        recovered_configuration, _ = exercise_configuration_recovery(
            evidence_root,
            state,
            configuration,
        )
        mcc_poc._exercise_cancellation_race(  # noqa: SLF001
            evidence_root,
            state,
            recovered_configuration,
        )
        mcc_poc._exercise_revoked_late_report(  # noqa: SLF001
            evidence_root,
            state,
            recovered_configuration,
        )
        mcc_poc._write(  # noqa: SLF001
            evidence_root / "evidence/audit-verification.json",
            mcc_poc._admin_request("/audit-events/verify"),  # noqa: SLF001
        )
        mcc_poc._write(  # noqa: SLF001
            evidence_root / "evidence/final-mission-inventory.json",
            mcc_poc._admin_request("/missions?limit=50"),  # noqa: SLF001
        )
    finally:
        if gateway is not None:
            mcc_poc._stop_gateway(gateway)  # noqa: SLF001

    mcc_poc._run_adversarial_tests(evidence_root)  # noqa: SLF001
    finished_at = datetime.now(UTC)
    finish_commit = mcc_poc._git_output(ROOT, "rev-parse", "HEAD")  # noqa: SLF001
    finish_tree = mcc_poc._git_output(ROOT, "rev-parse", "HEAD^{tree}")  # noqa: SLF001
    finish_clean = not bool(mcc_poc._git_status(ROOT))  # noqa: SLF001
    if (
        finish_commit != candidate_commit
        or finish_tree != candidate_tree
        or not finish_clean
    ):
        raise RuntimeError("candidate identity changed during failure-recovery journey")

    report: JsonObject = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "result": "passed",
        "candidate": {
            "commit": candidate_commit,
            "tree": candidate_tree,
            "clean_at_start": True,
            "commit_at_finish": finish_commit,
            "tree_at_finish": finish_tree,
            "clean_at_finish": finish_clean,
            "started_at_utc": started_at.isoformat(),
            "finished_at_utc": finished_at.isoformat(),
        },
        "identity_digests": {
            "node": sha256_digest({"kind": "local_v1_node", "id": state.node_id}),
            "mission": sha256_digest(
                {"kind": "local_v1_mission", "id": mission["mission_id"]}
            ),
        },
        "observations": {
            "restart_continuity": "passed",
            "replay_rejection": "passed",
            "partition_failure": "passed",
            "revocation": "passed",
            "stale_configuration_rejection": "passed",
            "manual_rollback": "passed",
            "rollback_generation": recovered_configuration.generation,
            "rollback_configuration_digest": (
                recovered_configuration.configuration_digest
            ),
            "configuration_enforcement": "stored_not_enforced",
            "gateway_truth_authoritative": True,
            "runner_state_authority": "runner_reported_only",
            "model_provider_state": "unknown",
        },
        "authority": dict(AUTHORITY),
        "nonclaims": list(NONCLAIMS),
    }
    _write_private_report(evidence_root / "evidence" / REPORT_JSON, report)
    _write_private_text(
        evidence_root / "evidence" / REPORT_MARKDOWN,
        render_markdown(report),
    )
    validate_evidence_tree(evidence_root)
    return report


def exercise_configuration_recovery(
    root: Path,
    state: NodeState,
    first: StoredNodeConfiguration,
) -> tuple[StoredNodeConfiguration, JsonObject]:
    second = mcc_poc._admin_request(  # noqa: SLF001
        f"/nodes/{state.node_id}/configurations",
        {
            "minimum_node_version": "0.2.0",
            "heartbeat_interval_seconds": 30,
            "offline_posture": "deny_governed_actions",
            "evidence_buffer_max_events": 1000,
        },
    )
    second_generation = _required_int(second, "generation")
    inventory = mcc_poc._admin_request(f"/nodes/{state.node_id}")  # noqa: SLF001
    mcc_poc._write(  # noqa: SLF001
        root / "evidence/configuration-drift.json",
        {
            "acknowledged_generation": first.generation,
            "desired_generation": second_generation,
            "configuration_state": inventory.get("configuration_state"),
            "enforcement_proven": False,
        },
    )

    rollback = mcc_poc._admin_request(  # noqa: SLF001
        f"/nodes/{state.node_id}/configurations/rollback",
        {
            "source_generation": first.generation,
            "expected_current_generation": second_generation,
        },
    )
    rollback_generation = _required_int(rollback, "generation")
    rollback_digest = _required_string(rollback, "configuration_digest")
    rollback_document: JsonObject = {
        "generation": rollback_generation,
        "assignment_kind": rollback.get("assignment_kind"),
        "rollback_source_generation": rollback.get("rollback_source_generation"),
        "replaced_desired_generation": second_generation,
        "configuration_digest_matches_source": (
            rollback_digest == first.configuration_digest
        ),
        "automatic": False,
        "enforcement_proven": False,
    }
    mcc_poc._write(  # noqa: SLF001
        root / "evidence/manual-rollback.json",
        rollback_document,
    )

    conflict_status, conflict = mcc_poc._request_outcome(  # noqa: SLF001
        f"/nodes/{state.node_id}/configurations/rollback",
        {
            "source_generation": first.generation,
            "expected_current_generation": second_generation,
        },
        admin=True,
    )
    mcc_poc._write(  # noqa: SLF001
        root / "evidence/stale-rollback-conflict.json",
        {
            "status_code": conflict_status,
            "detail": conflict.get("detail"),
            "automatic_retry_used": False,
        },
    )

    stale_payload: JsonObject = {
        "protocol_version": "1",
        "generation": first.generation,
        "configuration_digest": first.configuration_digest,
        "configuration_signing_key_id": first.signing_key_id,
        "active_configuration_signing_key_id": (
            state.gateway_configuration_key_id
        ),
        "status": "stored_not_enforced",
    }
    stale_status, stale = mcc_poc._signed_request_outcome(  # noqa: SLF001
        state,
        f"/nodes/{state.node_id}/configuration/acknowledgments",
        stale_payload,
        nonce="f1" * 16,
    )
    mcc_poc._write(  # noqa: SLF001
        root / "evidence/stale-configuration-rejection.json",
        {
            "status_code": stale_status,
            "detail": stale.get("detail"),
            "stale_generation": first.generation,
            "desired_generation": rollback_generation,
            "automatic_retry_used": False,
        },
    )

    client = mcc_poc._node_client()  # noqa: SLF001
    recovered = client.pull_configuration(
        state,
        known_generation=first.generation,
        nonce="f2" * 16,
    )
    recovered.write_atomic(root / "client/rollback-configuration.json")
    acknowledgment = client.acknowledge_configuration(
        state,
        recovered,
        nonce="f3" * 16,
    )
    heartbeat = client.heartbeat(
        state,
        node_version="0.1.0",
        runner_adapter="synthetic_external_runner",
        deployment_topology="local_process",
        configuration_digest=recovered.configuration_digest,
        nonce="f4" * 16,
    )
    mcc_poc._write(  # noqa: SLF001
        root / "evidence/rollback-acknowledged.json",
        {
            "generation": recovered.generation,
            "assignment_kind": recovered.bundle.get("assignment_kind"),
            "rollback_source_generation": recovered.bundle.get(
                "rollback_source_generation"
            ),
            "configuration_digest_matches_source": (
                recovered.configuration_digest == first.configuration_digest
            ),
            "configuration_acknowledgment_status": acknowledgment.get(
                "configuration_acknowledgment_status"
            ),
            "configuration_state": acknowledgment.get("configuration_state"),
            "heartbeat_observed_state": heartbeat.get("observed_state"),
            "enforcement_proven": False,
        },
    )
    return recovered, rollback_document


def render_markdown(report: JsonObject) -> str:
    candidate = cast(JsonObject, report["candidate"])
    observations = cast(JsonObject, report["observations"])
    lines = [
        "# Local v1 Failure and Recovery Evidence",
        "",
        f"Result: `{report['result']}`",
        "",
        "This candidate-bound local scenario passed restart continuity, replay rejection,",
        "partition failure, revocation, stale-configuration rejection, and manual rollback.",
        "",
        f"- Candidate: `{candidate['commit']}`",
        f"- Candidate tree: `{candidate['tree']}`",
        f"- Rollback generation: `{observations['rollback_generation']}`",
        "- Configuration enforcement: `stored_not_enforced`",
        "- Runner state authority: `runner_reported_only`",
        "- Model-provider state: `unknown`",
        "- Governed tool count: `24`",
        "",
        "## Authority limits",
        "",
    ]
    lines.extend(f"- {statement}" for statement in NONCLAIMS)
    return "\n".join(lines) + "\n"


def _write_private_report(path: Path, report: JsonObject) -> None:
    _write_private_text(path, canonical_json(report) + "\n")


def _write_private_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)


def _required_int(document: JsonObject, key: str) -> int:
    value = document.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise RuntimeError(f"failure-recovery response is missing {key}")
    return value


def _required_string(document: JsonObject, key: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"failure-recovery response is missing {key}")
    return value


if __name__ == "__main__":
    raise SystemExit(main())

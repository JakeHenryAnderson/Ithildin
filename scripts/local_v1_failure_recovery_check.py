"""Validate candidate-bound Local-v1 failure-and-recovery evidence."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

from scripts import mission_command_control_plane_poc_evidence_check as mcc_check
from scripts.local_v1_failure_recovery_journey import (
    AUTHORITY,
    NONCLAIMS,
    REPORT_JSON,
    REPORT_MARKDOWN,
    ROOT,
    SCHEMA_VERSION,
    selected_evidence_root,
    validate_evidence_tree,
)

_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_RAW_IDENTITY = re.compile(r"\b(?:node|mission|mclaim|run)_[0-9a-f]{32}\b")
MAX_EVIDENCE_AGE = timedelta(hours=24)
MAX_FUTURE_SKEW = timedelta(minutes=2)


def build_report(
    repo_root: Path,
    evidence_root: Path,
    *,
    expected_candidate: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    failures: list[str] = []
    if not _COMMIT.fullmatch(expected_candidate):
        failures.append("expected candidate is invalid")
    confined = False
    try:
        root = selected_evidence_root(evidence_root, run_id=evidence_root.name)
        validate_evidence_tree(root)
        confined = True
    except (OSError, ValueError) as exc:
        failures.append(str(exc))
        root = evidence_root

    base = (
        mcc_check.build_report(repo_root, root)
        if confined
        else {"valid": False, "tool_count": None}
    )
    if base.get("valid") is not True:
        failures.append("base Mission Command recovery evidence is invalid")

    paths = {
        "report": Path("evidence") / REPORT_JSON,
        "markdown": Path("evidence") / REPORT_MARKDOWN,
        "drift": Path("evidence/configuration-drift.json"),
        "rollback": Path("evidence/manual-rollback.json"),
        "stale_rollback": Path("evidence/stale-rollback-conflict.json"),
        "stale_configuration": Path("evidence/stale-configuration-rejection.json"),
        "rollback_acknowledged": Path("evidence/rollback-acknowledged.json"),
        "rollback_configuration": Path("client/rollback-configuration.json"),
    }
    if confined:
        failures.extend(
            f"missing Local-v1 recovery evidence: {name}"
            for name, path in paths.items()
            if not _is_regular_nofollow(root, path)
        )

    checks: dict[str, bool] = {
        "tool_count_unchanged": base.get("tool_count") == 24,
        "base_mission_recovery_valid": base.get("valid") is True,
    }
    safe_summary: dict[str, Any] = {}
    if confined and not any(failure.startswith("missing ") for failure in failures):
        try:
            report, _ = _json(root, paths["report"])
            drift, _ = _json(root, paths["drift"])
            rollback, _ = _json(root, paths["rollback"])
            stale_rollback, _ = _json(root, paths["stale_rollback"])
            stale_configuration, _ = _json(root, paths["stale_configuration"])
            rollback_acknowledged, _ = _json(root, paths["rollback_acknowledged"])
            markdown, _ = _read_text_nofollow(root, paths["markdown"])
            _, rollback_configuration_mode = _read_text_nofollow(
                root,
                paths["rollback_configuration"],
            )
            current_commit = _git(repo_root, "rev-parse", "HEAD")
            current_tree = _git(repo_root, "rev-parse", "HEAD^{tree}")
            current_clean = not bool(_git_status(repo_root))
            checks.update(
                validate_documents(
                    report=report,
                    drift=drift,
                    rollback=rollback,
                    stale_rollback=stale_rollback,
                    stale_configuration=stale_configuration,
                    rollback_acknowledged=rollback_acknowledged,
                    markdown=markdown,
                    expected_candidate=expected_candidate,
                    current_commit=current_commit,
                    current_tree=current_tree,
                    current_clean=current_clean,
                    rollback_configuration_mode=rollback_configuration_mode,
                    now=now,
                )
            )
            candidate = cast(dict[str, Any], report.get("candidate", {}))
            observations = cast(dict[str, Any], report.get("observations", {}))
            safe_summary = {
                "candidate_commit": candidate.get("commit"),
                "candidate_tree": candidate.get("tree"),
                "restart_continuity": observations.get("restart_continuity"),
                "replay_rejection": observations.get("replay_rejection"),
                "partition_failure": observations.get("partition_failure"),
                "revocation": observations.get("revocation"),
                "stale_configuration_rejection": observations.get(
                    "stale_configuration_rejection"
                ),
                "manual_rollback": observations.get("manual_rollback"),
                "configuration_enforcement": observations.get(
                    "configuration_enforcement"
                ),
                "runner_state_authority": observations.get(
                    "runner_state_authority"
                ),
                "model_provider_state": observations.get("model_provider_state"),
            }
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            failures.append(f"Local-v1 recovery evidence is unreadable: {exc}")

    failures.extend(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "claim_level": "local_v1_failure_recovery_candidate_evidence",
        "tool_count": base.get("tool_count"),
        "checks": checks,
        "safe_summary": safe_summary,
        "authority": dict(AUTHORITY),
        "nonclaims": list(NONCLAIMS),
    }


def validate_documents(
    *,
    report: dict[str, Any],
    drift: dict[str, Any],
    rollback: dict[str, Any],
    stale_rollback: dict[str, Any],
    stale_configuration: dict[str, Any],
    rollback_acknowledged: dict[str, Any],
    markdown: str,
    expected_candidate: str,
    current_commit: str,
    current_tree: str,
    current_clean: bool,
    rollback_configuration_mode: int,
    now: datetime | None = None,
) -> dict[str, bool]:
    candidate = cast(dict[str, Any], report.get("candidate", {}))
    identities = cast(dict[str, Any], report.get("identity_digests", {}))
    observations = cast(dict[str, Any], report.get("observations", {}))
    authority = cast(dict[str, Any], report.get("authority", {}))
    started = _timestamp(candidate.get("started_at_utc"))
    finished = _timestamp(candidate.get("finished_at_utc"))
    effective_now = (now or datetime.now(UTC)).astimezone(UTC)
    report_text = json.dumps(report, sort_keys=True) + "\n" + markdown
    rollback_generation = rollback.get("generation")
    return {
        "report_shape_closed": set(report)
        == {
            "schema_version",
            "run_id",
            "result",
            "candidate",
            "identity_digests",
            "observations",
            "authority",
            "nonclaims",
        },
        "report_schema_and_result_valid": report.get("schema_version") == SCHEMA_VERSION
        and report.get("result") == "passed",
        "candidate_bound_to_current_clean_tree": candidate
        == {
            "commit": expected_candidate,
            "tree": current_tree,
            "clean_at_start": True,
            "commit_at_finish": expected_candidate,
            "tree_at_finish": current_tree,
            "clean_at_finish": True,
            "started_at_utc": candidate.get("started_at_utc"),
            "finished_at_utc": candidate.get("finished_at_utc"),
        }
        and current_commit == expected_candidate
        and current_clean,
        "evidence_fresh_and_ordered": started is not None
        and finished is not None
        and started <= finished
        and finished - started <= timedelta(minutes=20)
        and finished <= effective_now + MAX_FUTURE_SKEW
        and effective_now - finished <= MAX_EVIDENCE_AGE,
        "identity_evidence_is_digest_only": set(identities) == {"node", "mission"}
        and all(_DIGEST.fullmatch(str(value)) for value in identities.values())
        and _RAW_IDENTITY.search(report_text) is None,
        "restart_replay_partition_revocation_bound": all(
            observations.get(name) == "passed"
            for name in (
                "restart_continuity",
                "replay_rejection",
                "partition_failure",
                "revocation",
            )
        ),
        "configuration_drift_observed": drift
        == {
            "acknowledged_generation": 1,
            "desired_generation": 2,
            "configuration_state": "configuration_drift",
            "enforcement_proven": False,
        },
        "manual_rollback_is_fresh_signed_generation": rollback
        == {
            "generation": 3,
            "assignment_kind": "manual_rollback",
            "rollback_source_generation": 1,
            "replaced_desired_generation": 2,
            "configuration_digest_matches_source": True,
            "automatic": False,
            "enforcement_proven": False,
        }
        and rollback_generation == observations.get("rollback_generation"),
        "stale_rollback_conflict_rejected": stale_rollback
        == {
            "status_code": 409,
            "detail": "desired configuration changed",
            "automatic_retry_used": False,
        },
        "stale_configuration_acknowledgment_rejected": stale_configuration
        == {
            "status_code": 409,
            "detail": "configuration acknowledgment is not current",
            "stale_generation": 1,
            "desired_generation": 3,
            "automatic_retry_used": False,
        },
        "rollback_acknowledged_as_stored_not_enforced": rollback_acknowledged
        == {
            "generation": 3,
            "assignment_kind": "manual_rollback",
            "rollback_source_generation": 1,
            "configuration_digest_matches_source": True,
            "configuration_acknowledgment_status": "stored_not_enforced",
            "configuration_state": "stored_current_not_enforced",
            "heartbeat_observed_state": "observed_connected",
            "enforcement_proven": False,
        }
        and observations.get("stale_configuration_rejection") == "passed"
        and observations.get("manual_rollback") == "passed"
        and observations.get("configuration_enforcement") == "stored_not_enforced",
        "truth_sources_remain_separate": observations.get(
            "gateway_truth_authoritative"
        )
        is True
        and observations.get("runner_state_authority") == "runner_reported_only"
        and observations.get("model_provider_state") == "unknown",
        "all_authority_remains_false": authority == AUTHORITY
        and all(value is False for value in authority.values()),
        "nonclaims_exact": report.get("nonclaims") == NONCLAIMS,
        "private_rollback_configuration_mode_0600": (
            rollback_configuration_mode == 0o600
        ),
        "operator_markdown_matches_safe_report": (
            markdown == _expected_markdown(report)
        ),
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Local-v1 failure-recovery evidence check",
        f"valid: {str(report['valid']).lower()}",
        f"claim_level: {report['claim_level']}",
        f"tool_count: {report['tool_count']}",
    ]
    lines.extend(
        f"{name}: {str(value).lower()}"
        for name, value in cast(dict[str, bool], report["checks"]).items()
    )
    lines.extend(
        f"{name}: {value}"
        for name, value in cast(dict[str, Any], report["safe_summary"]).items()
    )
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _expected_markdown(report: dict[str, Any]) -> str:
    candidate = cast(dict[str, Any], report.get("candidate", {}))
    observations = cast(dict[str, Any], report.get("observations", {}))
    lines = [
        "# Local v1 Failure and Recovery Evidence",
        "",
        f"Result: `{report.get('result')}`",
        "",
        "This candidate-bound local scenario passed restart continuity, replay rejection,",
        "partition failure, revocation, stale-configuration rejection, and manual rollback.",
        "",
        f"- Candidate: `{candidate.get('commit')}`",
        f"- Candidate tree: `{candidate.get('tree')}`",
        f"- Rollback generation: `{observations.get('rollback_generation')}`",
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


def _is_regular_nofollow(root: Path, relative: Path) -> bool:
    try:
        _read_text_nofollow(root, relative)
    except (OSError, UnicodeError, ValueError):
        return False
    return True


def _read_text_nofollow(root: Path, relative: Path) -> tuple[str, int]:
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError("invalid confined evidence path")
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory_flag = getattr(os, "O_DIRECTORY", 0)
    descriptors: list[int] = []
    try:
        current = os.open(root, os.O_RDONLY | nofollow | directory_flag)
        descriptors.append(current)
        for component in relative.parts[:-1]:
            current = os.open(
                component,
                os.O_RDONLY | nofollow | directory_flag,
                dir_fd=current,
            )
            descriptors.append(current)
        file_descriptor = os.open(
            relative.parts[-1],
            os.O_RDONLY | nofollow,
            dir_fd=current,
        )
        descriptors.append(file_descriptor)
        file_stat = os.fstat(file_descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise ValueError("confined evidence entry is not a regular file")
        with os.fdopen(os.dup(file_descriptor), encoding="utf-8") as stream:
            return stream.read(), stat.S_IMODE(file_stat.st_mode)
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _json(root: Path, relative: Path) -> tuple[dict[str, Any], int]:
    text, mode = _read_text_nofollow(root, relative)
    document = json.loads(text)
    if not isinstance(document, dict):
        raise ValueError(f"expected object in {relative.name}")
    return cast(dict[str, Any], document), mode


def _timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


def _git(repo_root: Path, *arguments: str) -> str:
    return mcc_check._git(repo_root, *arguments)  # noqa: SLF001


def _git_status(repo_root: Path) -> str:
    from scripts import mission_command_control_plane_poc as mcc_poc

    return mcc_poc._git_status(repo_root)  # noqa: SLF001


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--expected-candidate", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report(
        ROOT,
        args.evidence_root,
        expected_candidate=args.expected_candidate,
    )
    print(
        json.dumps(report, indent=2, sort_keys=True)
        if args.json
        else render_report(report)
    )
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

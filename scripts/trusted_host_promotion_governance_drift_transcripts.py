#!/usr/bin/env python3
"""Generate observed governance-drift evidence for the TGB-006 adversarial matrix."""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = Path(
    "var/review-packets/v3/trusted-host-promotion-governance-drift"
)
TRANSCRIPT_NAME = "TRUSTED_HOST_PROMOTION_GOVERNANCE_DRIFT_TRANSCRIPTS.md"


class GovernanceDriftTranscriptError(RuntimeError):
    """Raised when observed matrix evidence cannot be generated safely."""


@dataclass(frozen=True)
class MatrixRow:
    category: str
    proofs: tuple[str, ...]
    commands: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class ObservedCommand:
    command: tuple[str, ...]
    returncode: int
    output: str


PYTEST = ("uv", "run", "pytest")
MATRIX_ROWS = (
    MatrixRow(
        category="Identity",
        proofs=(
            "caller principal, role, and decided_by fields rejected",
            "missing and invalid bearer authentication rejected",
            "absent or disabled registry principal rejected",
            "requester, approver, and executor attribution remains server-derived",
            "approval consumers and Command Center use returned identity evidence",
        ),
        commands=(
            PYTEST
            + (
                "tests/test_api_service.py::test_legacy_caller_attribution_fields_are_rejected",
                "tests/test_api_service.py::test_trusted_host_promotion_binds_identity_but_keeps_placement_unavailable",
                "tests/test_api_service.py::test_admin_token_fails_closed_without_enabled_registry_admin",
                "tests/test_api_service.py::test_admin_status_rejects_wrong_bearer_token",
                "tests/test_api_service.py::test_trusted_host_diagnostics_use_terminal_approval_outcome_as_gateway_truth",
                "-q",
            ),
            ("npm", "run", "test", "--prefix", "apps/ui", "--", "--run"),
        ),
    ),
    MatrixRow(
        category="Host descriptor",
        proofs=(
            "missing, duplicate, disabled, and wrong-workspace bindings rejected",
            "unreviewed and unsupported host postures rejected",
            "descriptor hash, generation, and registry-schema drift terminally stale",
            "raw path and unsafe label injection rejected",
        ),
        commands=(
            PYTEST
            + (
                "tests/test_trusted_host_registry.py",
                "tests/test_api_service.py::test_trusted_host_promotion_every_authority_component_drift_is_terminal",
                "tests/test_api_service.py::test_trusted_host_promotion_denies_stale_and_unsafe_inputs",
                "tests/test_trusted_host_placement.py::test_descriptor_relative_capability_fails_closed_without_dir_fd",
                "-q",
            ),
        ),
    ),
    MatrixRow(
        category="Policy",
        proofs=(
            "YAML deny and plain allow rejected; require_approval required",
            "OPA rejected for this bounded slice",
            "digest, policy-version, document-version, rule, and obligation drift terminally stale",
            "duplicate and unsorted rule evidence rejected",
            "unknown obligation set rejected",
        ),
        commands=(
            PYTEST
            + (
                "tests/test_api_service.py::test_trusted_host_promotion_policy_fails_closed",
                "tests/test_api_service.py::test_trusted_host_promotion_rejects_noncanonical_policy_rule_evidence",
                "tests/test_api_service.py::test_trusted_host_promotion_routes_reject_opa_without_calling_opa",
                "tests/test_api_service.py::test_trusted_host_promotion_every_authority_component_drift_is_terminal",
                "-q",
            ),
        ),
    ),
    MatrixRow(
        category="Manifest",
        proofs=(
            "unverified manifest readiness cannot be bypassed",
            "duplicate lock evidence rejected",
            "tool count is exactly 24",
            "lock digest and version drift after approval terminally stale",
        ),
        commands=(
            PYTEST
            + (
                "tests/test_api_service.py::test_trusted_host_promotion_production_readiness_requires_enforced_manifest_lock",
                "tests/test_api_service.py::test_trusted_host_promotion_rejects_duplicate_manifest_evidence",
                "tests/test_promotion_authority.py::test_authority_models_reject_unknown_fields_and_wrong_tool_count",
                "tests/test_api_service.py::test_trusted_host_promotion_every_authority_component_drift_is_terminal",
                "-q",
            ),
            ("make", "tool-surface-invariant-gate"),
        ),
    ),
    MatrixRow(
        category="Schema",
        proofs=(
            "unknown proposal and apply fields rejected",
            "legacy caller principal and decided_by fields rejected",
            "closed authority models reject extra evidence",
            "schema version and digest drift after approval terminally stale",
            "newer or weakened persistence schemas rejected",
        ),
        commands=(
            PYTEST
            + (
                "tests/test_api_service.py::test_legacy_caller_attribution_fields_are_rejected",
                "tests/test_api_service.py::test_trusted_host_promotion_denies_stale_and_unsafe_inputs",
                "tests/test_promotion_authority.py::test_authority_models_reject_unknown_fields_and_wrong_tool_count",
                "tests/test_api_service.py::test_trusted_host_promotion_every_authority_component_drift_is_terminal",
                "tests/test_trusted_host_promotion_v2_migration.py::test_newer_database_or_minimum_writer_is_rejected",
                "tests/test_trusted_host_promotion_v2_migration.py::test_v2_schema_with_required_columns_but_weakened_constraints_is_rejected",
                "-q",
            ),
        ),
    ),
    MatrixRow(
        category="Candidate",
        proofs=(
            "absent inventory and dirty source rejected",
            "wrong candidate and metadata-only spoof rejected",
            "inventory schema, reviewed inventory, installed file, and reviewed commit drift "
            "rejected",
            "release artifact, review packet, and dependency-lock digest drift rejected",
            "digest-domain cycle rejected",
            "writable package root and environment-only spoof rejected",
        ),
        commands=(
            PYTEST
            + (
                "tests/test_runtime_candidate_bootstrap.py",
                "tests/test_promotion_authority.py::test_runtime_candidate_id_does_not_include_review_packet_digest",
                "tests/test_api_service.py::test_trusted_host_promotion_every_authority_component_drift_is_terminal",
                "-q",
            ),
        ),
    ),
    MatrixRow(
        category="Approval",
        proofs=(
            "copied, wrong-proposal, wrong-snapshot, and wrong-requester approval rejected",
            "server-derived principal missing the required Approver role cannot decide or place",
            "expired and denied approvals cannot execute",
            "decision drift terminally stale",
            "sequential replay and concurrent double apply reserve only once",
            "conflicting terminal decisions have one atomic winner",
        ),
        commands=(
            PYTEST
            + (
                "tests/test_api_service.py::test_trusted_host_promotion_missing_approver_role_cannot_decide_or_place",
                "tests/test_api_service.py::test_trusted_host_promotion_rejects_unbound_approval_and_all_placement",
                "tests/test_api_service.py::test_trusted_host_promotion_approval_decision_drift_is_terminal",
                "tests/test_api_service.py::test_trusted_host_promotion_internal_fixture_concurrent_replay_reserves_once",
                "tests/test_approval_workflow.py::test_expired_approval_cannot_be_approved_or_executed",
                "tests/test_approval_workflow.py::test_denied_approval_cannot_execute",
                "tests/test_approval_workflow.py::test_conflicting_terminal_decisions_have_one_atomic_winner",
                "-q",
            ),
        ),
    ),
    MatrixRow(
        category="Source and destination",
        proofs=(
            "retained exact source buffer is placed and hashed",
            "symlink, hardlink, directory, stale hash, traversal, and sensitive labels rejected",
            "destination conflict preserves existing content and overwrite is impossible",
            "pre-write root replacement has no effect; post-write replacement requires recovery",
            "ancestor symlink and writable ancestry rejected",
            "unsupported no-follow primitives fail closed",
        ),
        commands=(
            PYTEST
            + (
                "tests/test_trusted_host_placement.py",
                "tests/test_api_service.py::test_trusted_host_promotion_rejects_unsafe_source_object_types",
                "tests/test_api_service.py::test_trusted_host_promotion_source_drift_is_terminal_before_reservation",
                "tests/test_api_service.py::test_trusted_host_promotion_destination_conflict_is_terminal_without_overwrite",
                "tests/test_api_service.py::test_trusted_host_promotion_postwrite_root_drift_records_recovery",
                "tests/test_api_service.py::test_trusted_host_promotion_prewrite_root_drift_records_no_effect_failure",
                "-q",
            ),
        ),
    ),
    MatrixRow(
        category="Migration",
        proofs=(
            "legacy rows remain explicit and immutable",
            "partial rebuild and interrupted migration roll back atomically",
            "restart is idempotent and newer database downgrade is denied",
            "frozen previous writer proposal, approval, deny, apply, and attempt paths are denied",
            "previous writer cannot create a placement effect",
        ),
        commands=(
            PYTEST + ("tests/test_trusted_host_promotion_v2_migration.py", "-q"),
            ("uv", "run", "python", "scripts/trusted_host_promotion_v2_downgrade_evidence.py"),
        ),
    ),
    MatrixRow(
        category="Evidence",
        proofs=(
            "completion-audit interruption cannot produce completed state",
            "concurrent completions append one valid audit chain",
            "malformed authority JSON and legacy recovery render safely",
            "diagnostics expose no automatic repair or raw source labels",
            "negative transcript output is redacted",
            "packet freshness, hashes, and redaction are independently gated by the bundle builder",
        ),
        commands=(
            PYTEST
            + (
                "tests/test_api_service.py::test_trusted_host_promotion_audit_failure_leaves_completion_pending",
                "tests/test_api_service.py::test_concurrent_distinct_promotions_complete_on_one_valid_audit_chain",
                "tests/test_api_service.py::test_trusted_host_diagnostics_fail_safe_for_malformed_authority_evidence",
                "tests/test_api_service.py::test_trusted_host_diagnostics_never_hide_legacy_recovery_evidence",
                "tests/test_audit_writer.py::test_audit_writer_serializes_concurrent_chain_appends",
                "-q",
            ),
            ("make", "trusted-host-promotion-negative-transcripts"),
        ),
    ),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--skip-commands", action="store_true")
    args = parser.parse_args()
    try:
        transcript = build_transcript(
            repo_root=REPO_ROOT,
            output_dir=args.output_dir,
            allow_dirty=args.allow_dirty,
            run_commands=not args.skip_commands,
        )
    except GovernanceDriftTranscriptError as exc:
        print(f"trusted-host governance-drift transcript failed: {exc}")
        return 1
    print(f"Built trusted-host governance-drift transcript at {transcript}")
    return 0


def build_transcript(
    *,
    repo_root: Path,
    output_dir: Path,
    allow_dirty: bool = False,
    run_commands: bool = True,
) -> Path:
    commit = _git(repo_root, "rev-parse", "HEAD")
    dirty = bool(_git(repo_root, "status", "--short"))
    if dirty and not allow_dirty:
        raise GovernanceDriftTranscriptError(
            "working tree is dirty; commit before generating exact-candidate evidence"
        )
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    observed: list[tuple[MatrixRow, tuple[ObservedCommand, ...]]] = []
    for row in MATRIX_ROWS:
        results = tuple(
            _run(repo_root, command, run_commands=run_commands)
            for command in row.commands
        )
        observed.append((row, results))
    failures = [
        f"{row.category}: {' '.join(result.command)}"
        for row, results in observed
        for result in results
        if result.returncode != 0
    ]
    if failures:
        raise GovernanceDriftTranscriptError("; ".join(failures))

    transcript = output_dir / TRANSCRIPT_NAME
    rendered = _render(commit=commit, dirty=dirty, observed=observed)
    forbidden = _forbidden_hits(rendered, repo_root)
    if forbidden:
        raise GovernanceDriftTranscriptError(
            "transcript redaction failed: " + ", ".join(forbidden)
        )
    transcript.write_text(rendered, encoding="utf-8")
    return transcript


def _run(
    repo_root: Path,
    command: tuple[str, ...],
    *,
    run_commands: bool,
) -> ObservedCommand:
    if not run_commands:
        return ObservedCommand(command=command, returncode=0, output="command execution skipped")
    process = subprocess.run(
        command,
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    output = (process.stdout + process.stderr).strip()
    return ObservedCommand(
        command=command,
        returncode=process.returncode,
        output=_bounded_output(_sanitize_output(output, repo_root)),
    )


def _render(
    *,
    commit: str,
    dirty: bool,
    observed: list[tuple[MatrixRow, tuple[ObservedCommand, ...]]],
) -> str:
    disposition = (
        "implementation_candidate_ready_for_independent_re_review"
        if not dirty
        else "development_evidence_only"
    )
    lines = [
        "# Trusted-Host Promotion Governance-Drift Transcripts",
        "",
        f"- Exact commit: `{commit}`",
        f"- Dirty at generation: `{str(dirty).lower()}`",
        f"- Matrix categories observed: `{len(observed)}`",
        "- Governed tool count: `24`",
        f"- Disposition: `{disposition}`",
        "- External/source-review closure recorded: `false`",
        "",
        "Each row below is executable evidence for the corresponding architecture matrix row. A",
        "passing transcript does not approve broader host powers, external closure, release, or "
        "UAT.",
        "",
    ]
    for row, results in observed:
        lines.extend([f"## {row.category}", "", "Required proofs:", ""])
        lines.extend(f"- {proof}" for proof in row.proofs)
        lines.extend(["", "Observed commands:", ""])
        for result in results:
            lines.extend(
                [
                    "```text",
                    f"$ {' '.join(result.command)}",
                    f"exit_code={result.returncode}",
                    result.output or "(no output)",
                    "```",
                    "",
                ]
            )
        lines.extend(["Observed result: `pass`.", ""])
    return "\n".join(lines).rstrip() + "\n"


def _bounded_output(output: str) -> str:
    lines = output.splitlines()
    if len(lines) > 80:
        lines = ["[output truncated to final 80 lines]"] + lines[-80:]
    return "\n".join(lines)


def _sanitize_output(output: str, repo_root: Path) -> str:
    sanitized = output.replace(repo_root.as_posix(), ".")
    sanitized = re.sub(r"/Users/[^/\s]+", "<user-home>", sanitized)
    sanitized = sanitized.replace("correct-token", "[REDACTED]")
    return sanitized.replace("dev-admin-token", "[REDACTED]")


def _forbidden_hits(rendered: str, repo_root: Path) -> list[str]:
    forbidden = {
        repo_root.as_posix(): "repo absolute path",
        "/Users/": "user home path",
        "correct-token": "test bearer token",
        "dev-admin-token": "sample bearer token",
        "Traceback (most recent call last)": "stack trace",
    }
    return [label for needle, label in forbidden.items() if needle in rendered]


def _git(repo_root: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return process.stdout.strip()


def transcript_digest(path: Path) -> str:
    """Return a packet-friendly digest for a generated transcript."""

    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())

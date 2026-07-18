"""Build the trusted-host promotion runtime source-review bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (  # noqa: E402
    no_new_powers_guardrail,
    tool_surface_invariant_gate,
    trusted_host_promotion_runtime_implementation_decision_check,
)

DEFAULT_OUTPUT_DIR = Path(
    "var/review-packets/v3/trusted-host-promotion-runtime-source-review"
)
HASH_MANIFEST = "trusted-host-promotion-runtime-source-review-artifact-hashes.json"
FINDING_NAMESPACE = "EXT-TRUSTED-HOST-RUNTIME-###"
RUNTIME_CANDIDATE_REVIEW_PACKET = (
    "11_TRUSTED_HOST_PROMOTION_RUNTIME_CANDIDATE_REVIEW_PACKET.json"
)
RUNTIME_CANDIDATE_DIGEST_EVIDENCE = (
    "12_TRUSTED_HOST_PROMOTION_RUNTIME_CANDIDATE_DIGEST_EVIDENCE.json"
)

SOURCE_FILES = [
    "apps/api/runtime_candidate_bootstrap.py",
    "apps/api/verified_launch.py",
    "apps/api/src/ithildin_api/trusted_host_promotions.py",
    "apps/api/src/ithildin_api/trusted_host_placement.py",
    "apps/api/src/ithildin_api/filesystem_contract.py",
    "apps/api/src/ithildin_api/app.py",
    "apps/api/src/ithildin_api/auth.py",
    "apps/api/src/ithildin_api/config.py",
    "apps/api/src/ithildin_api/identity.py",
    "apps/api/src/ithildin_api/promotion_authority.py",
    "apps/api/src/ithildin_api/approvals.py",
    "apps/api/src/ithildin_api/database.py",
    "apps/api/src/ithildin_api/trusted_host_promotion_v2_migration.py",
    "apps/api/src/ithildin_api/read_tools.py",
    "apps/api/src/ithildin_api/sandbox_descriptors.py",
    "apps/api/src/ithildin_api/trusted_host_registry.py",
    "apps/api/src/ithildin_api/workspaces.py",
    "apps/ui/src/App.tsx",
    "apps/ui/src/styles.css",
    "packages/audit-core/src/ithildin_audit_core/writer.py",
    "packages/schemas/src/ithildin_schemas/models.py",
    "packages/schemas/src/ithildin_schemas/types.py",
    "scripts/runtime_candidate_authorization_record.py",
    "scripts/trusted_host_promotion_negative_transcripts.py",
    "scripts/trusted_host_promotion_governance_drift_transcripts.py",
    "scripts/trusted_host_promotion_v2_downgrade_evidence.py",
    "schemas/runtime-candidate-authorization.schema.json",
    "trusted-hosts/local.yaml",
]
TEST_FILES = [
    "apps/ui/src/App.test.tsx",
    "tests/test_audit_writer.py",
    "tests/test_api_service.py",
    "tests/test_approval_workflow.py",
    "tests/test_core_schemas.py",
    "tests/test_governed_tool_calls.py",
    "tests/test_identity.py",
    "tests/test_promotion_authority.py",
    "tests/test_release_readiness.py",
    "tests/test_runtime_candidate_bootstrap.py",
    "tests/test_trusted_host_registry.py",
    "tests/test_trusted_host_promotion_v2_migration.py",
    "tests/test_trusted_host_placement.py",
    "tests/test_filesystem_contract_check.py",
    "tests/test_workspaces.py",
]
CONTRACT_DOCS = [
    "docs/codex/trusted-host-promotion-runtime-implementation-decision.md",
    "docs/codex/trusted-host-promotion-runtime-implementation.md",
    "docs/codex/v3-trusted-host-promotion-runtime-internal-review.md",
    "docs/codex/v3-trusted-host-promotion-governance-binding-internal-review.md",
    "docs/codex/v3-trusted-host-promotion-runtime-review-closure.md",
    "docs/codex/v3-trusted-host-promotion-runtime-local-disposition.md",
    "docs/codex/trusted-host-promotion-runtime-source-review.md",
    "docs/codex/trusted-host-promotion-limited-runtime-ticket.md",
    "docs/codex/trusted-host-promotion-limited-runtime-plan.md",
    "docs/codex/trusted-host-promotion-zone-contract.md",
    "docs/codex/trusted-host-promotion-negative-fixtures.md",
    "docs/codex/sandbox-promotion-evidence-contract.md",
    "docs/codex/findings/ext-trusted-host-runtime-001-proposal-approval-binding.md",
    "docs/codex/findings/ext-trusted-host-runtime-002-governance-bindings.md",
    "docs/codex/findings/ext-trusted-host-runtime-003-source-object-race.md",
    "docs/codex/findings/ext-trusted-host-runtime-004-completion-audit-state.md",
    "docs/codex/findings/ext-trusted-host-runtime-005-packet-freshness.md",
    "docs/codex/findings/ext-trusted-host-runtime-006-adversarial-coverage.md",
    "docs/codex/findings/ext-trusted-host-runtime-007-gate-evidence-serialization.md",
    "docs/codex/findings/ext-trusted-host-runtime-008-interrupted-packet-generation.md",
    "docs/codex/findings/ext-trusted-host-runtime-009-approver-role-enforcement.md",
    "docs/codex/findings/ext-trusted-host-runtime-010-packet-candidate-equivalence.md",
]
FOCUSED_TEST_COMMAND = [
    "uv",
    "run",
    "pytest",
    "tests/test_api_service.py::test_trusted_host_promotion_binds_identity_but_keeps_placement_unavailable",
    "tests/test_api_service.py::test_trusted_host_promotion_production_readiness_requires_approver_role",
    "tests/test_api_service.py::test_trusted_host_promotion_missing_approver_role_cannot_decide_or_place",
    "tests/test_api_service.py::test_trusted_host_promotion_denies_stale_and_unsafe_inputs",
    "tests/test_api_service.py::test_trusted_host_promotion_rejects_unbound_approval_and_all_placement",
    "tests/test_api_service.py::test_trusted_host_promotion_rejects_unsafe_source_object_types",
    "tests/test_api_service.py::test_trusted_host_promotion_concurrent_apply_remains_disabled",
    "tests/test_api_service.py::test_trusted_host_promotion_preserves_existing_destination",
    "tests/test_api_service.py::test_trusted_host_promotion_audit_failure_leaves_completion_pending",
    "tests/test_api_service.py::test_trusted_host_promotion_is_fail_closed_until_binding_is_complete",
    "tests/test_api_service.py::test_trusted_host_promotion_internal_fixture_completes_after_audit_evidence",
    "tests/test_api_service.py::test_trusted_host_promotion_apply_opens_source_exactly_once",
    "tests/test_api_service.py::test_trusted_host_promotion_internal_fixture_concurrent_replay_reserves_once",
    "tests/test_api_service.py::test_trusted_host_promotion_source_drift_is_terminal_before_reservation",
    "tests/test_api_service.py::test_trusted_host_promotion_every_authority_component_drift_is_terminal",
    "tests/test_api_service.py::test_trusted_host_promotion_approval_decision_drift_is_terminal",
    "tests/test_api_service.py::test_trusted_host_promotion_postwrite_root_drift_records_recovery",
    "tests/test_api_service.py::test_trusted_host_promotion_success_evidence_failure_records_recovery",
    "tests/test_api_service.py::test_trusted_host_promotion_prewrite_root_drift_records_no_effect_failure",
    "tests/test_api_service.py::test_trusted_host_promotion_reservation_rolls_back_all_three_records",
    "tests/test_api_service.py::test_trusted_host_promotion_compare_and_set_drift_becomes_terminal_stale",
    "tests/test_api_service.py::test_trusted_host_promotion_destination_conflict_is_terminal_without_overwrite",
    "tests/test_trusted_host_placement.py",
    "tests/test_promotion_authority.py",
    "tests/test_runtime_candidate_bootstrap.py",
    "tests/test_trusted_host_registry.py",
    "tests/test_trusted_host_promotion_v2_migration.py",
    "-q",
]


class TrustedHostPromotionRuntimeSourceReviewBundleError(RuntimeError):
    """Raised when the runtime source-review bundle cannot be built."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--skip-commands", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    try:
        if args.check:
            report = build_check_report(Path.cwd())
            print(_json(report))
            return 0 if report["valid"] else 1
        output_dir = build_bundle(
            repo_root=Path.cwd().resolve(),
            output_dir=args.output_dir,
            allow_dirty=args.allow_dirty,
            run_commands=not args.skip_commands,
        )
    except TrustedHostPromotionRuntimeSourceReviewBundleError as exc:
        print(
            f"trusted-host promotion runtime source-review bundle failed: {exc}",
            file=sys.stderr,
        )
        return 1
    print(f"Built trusted-host promotion runtime source-review bundle at {output_dir}")
    return 0


def build_check_report(
    repo_root: Path,
    *,
    validate_existing_packet: bool = True,
) -> dict[str, Any]:
    failures: list[str] = []
    _collect_missing(repo_root, SOURCE_FILES, "source", failures)
    _collect_missing(repo_root, TEST_FILES, "test", failures)
    _collect_missing(repo_root, CONTRACT_DOCS, "contract", failures)

    decision = trusted_host_promotion_runtime_implementation_decision_check.build_report(
        repo_root
    )
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    for label, report in [
        ("runtime implementation decision", decision),
        ("tool surface", tool_surface),
        ("no-new-powers", no_new_powers),
    ]:
        failures.extend(f"{label}: {failure}" for failure in report["failures"])

    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    review_docs = (repo_root / "scripts/review_docs.py").read_text(encoding="utf-8")
    release_guardrails = (repo_root / "scripts/release_guardrails.py").read_text(
        encoding="utf-8"
    )
    review_index = (repo_root / "docs/codex/review-docs-index.md").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    checks = [
        ("Make bundle target", "trusted-host-promotion-runtime-source-review-bundle:", makefile),
        (
            "Make check target",
            "trusted-host-promotion-runtime-source-review-bundle-check:",
            makefile,
        ),
        (
            "release-check target",
            "trusted-host-promotion-runtime-source-review-bundle-check",
            release_check_body,
        ),
        (
            "README command",
            "make trusted-host-promotion-runtime-source-review-bundle",
            readme,
        ),
        (
            "docs site runtime review doc",
            "docs/codex/trusted-host-promotion-runtime-source-review.md",
            docs_site,
        ),
        (
            "review docs runtime review doc",
            "docs/codex/trusted-host-promotion-runtime-source-review.md",
            review_docs,
        ),
        (
            "docs site internal review doc",
            "docs/codex/v3-trusted-host-promotion-runtime-internal-review.md",
            docs_site,
        ),
        (
            "docs site closure review doc",
            "docs/codex/v3-trusted-host-promotion-runtime-review-closure.md",
            docs_site,
        ),
        (
            "docs site local disposition doc",
            "docs/codex/v3-trusted-host-promotion-runtime-local-disposition.md",
            docs_site,
        ),
        (
            "review docs internal review doc",
            "docs/codex/v3-trusted-host-promotion-runtime-internal-review.md",
            review_docs,
        ),
        (
            "docs site governance-binding internal review doc",
            "docs/codex/v3-trusted-host-promotion-governance-binding-internal-review.md",
            docs_site,
        ),
        (
            "review docs governance-binding internal review doc",
            "docs/codex/v3-trusted-host-promotion-governance-binding-internal-review.md",
            review_docs,
        ),
        (
            "review docs closure review doc",
            "docs/codex/v3-trusted-host-promotion-runtime-review-closure.md",
            review_docs,
        ),
        (
            "review docs local disposition doc",
            "docs/codex/v3-trusted-host-promotion-runtime-local-disposition.md",
            review_docs,
        ),
        (
            "review index runtime review",
            "Trusted-Host Promotion Runtime Source Review",
            review_index,
        ),
        (
            "review index internal runtime review",
            "Trusted-Host Promotion Runtime Internal Review",
            review_index,
        ),
        (
            "review index governance-binding internal review",
            "Trusted-Host Promotion Governance-Binding Internal Review",
            review_index,
        ),
        (
            "review index runtime closure",
            "Trusted-Host Promotion Runtime Review Closure",
            review_index,
        ),
        (
            "review index local disposition",
            "Trusted-Host Promotion Runtime Local Disposition",
            review_index,
        ),
        (
            "release guardrail target",
            "trusted-host-promotion-runtime-source-review-bundle-check",
            release_guardrails,
        ),
    ]
    for label, needle, haystack in checks:
        if needle not in haystack:
            failures.append(f"{label} missing: {needle}")

    runtime_review = (
        repo_root / "docs/codex/trusted-host-promotion-runtime-source-review.md"
    ).read_text(encoding="utf-8")
    internal_review = (
        repo_root / "docs/codex/v3-trusted-host-promotion-runtime-internal-review.md"
    ).read_text(encoding="utf-8")
    governance_internal_review = repo_root.joinpath(
        "docs/codex/v3-trusted-host-promotion-governance-binding-internal-review.md"
    ).read_text(encoding="utf-8")
    closure_review = (
        repo_root / "docs/codex/v3-trusted-host-promotion-runtime-review-closure.md"
    ).read_text(encoding="utf-8")
    local_disposition = (
        repo_root / "docs/codex/v3-trusted-host-promotion-runtime-local-disposition.md"
    ).read_text(encoding="utf-8")
    for text_label, text in [
        ("runtime review", runtime_review),
        ("internal review", internal_review),
        ("governance-binding internal review", governance_internal_review),
        ("closure review", closure_review),
        ("local disposition", local_disposition),
    ]:
        if FINDING_NAMESPACE not in text:
            failures.append(f"{text_label} missing finding namespace {FINDING_NAMESPACE}")
    if "No critical or high implementation findings" not in internal_review:
        failures.append("internal review does not record no critical/high findings")
    if (
        "Status: `implementation_candidate_ready_for_independent_re_review`."
        not in governance_internal_review
    ):
        failures.append(
            "governance-binding internal review does not record the bounded disposition"
        )
    if "external_review_complete: false" not in governance_internal_review:
        failures.append(
            "governance-binding internal review does not preserve external review boundary"
        )
    if "Disposition: `local_reviewed_external_pending`" not in closure_review:
        failures.append("closure review does not record local_reviewed_external_pending")
    if "Disposition: `external_review_received_remediation_pending`" not in local_disposition:
        failures.append(
            "local disposition does not record external_review_received_remediation_pending"
        )
    if tool_surface.get("tool_count") != 24:
        failures.append(f"tool count changed: {tool_surface.get('tool_count')!r}")
    if decision.get("runtime_implementation_allowed_next") is not True:
        failures.append("runtime decision no longer allows the staging-only slice")

    packet_evidence = _existing_packet_evidence(repo_root)
    if validate_existing_packet and packet_evidence["present"]:
        if not packet_evidence["commit_matches_head"]:
            failures.append(
                "existing runtime source-review packet is not bound to current HEAD"
            )
        if not packet_evidence["generated_from_clean_tree"]:
            failures.append(
                "existing runtime source-review packet was generated from a dirty tree"
            )
        if not packet_evidence["artifact_hashes_match_files"]:
            failures.append(
                "existing runtime source-review packet artifact hashes do not match files"
            )
        if not packet_evidence["bundled_files_match_head"]:
            failures.append(
                "existing runtime source-review packet bundles do not match current HEAD"
            )
        if not packet_evidence["redaction_scan_valid"]:
            failures.append(
                "existing runtime source-review packet redaction scan is missing or invalid"
            )
        if not packet_evidence["candidate_digest_evidence_valid"]:
            failures.append(
                "existing runtime source-review packet candidate digest evidence is invalid"
            )
        if not packet_evidence["candidate_index_evidence_matches"]:
            failures.append(
                "existing runtime source-review packet index does not match candidate evidence"
            )
        embedded_packet_evidence = _embedded_packet_evidence(
            repo_root / DEFAULT_OUTPUT_DIR
        )
        if embedded_packet_evidence != packet_evidence:
            failures.append(
                "existing runtime source-review packet embedded gate evidence "
                "does not match live packet evidence"
            )

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "finding_namespace": FINDING_NAMESPACE,
        "output_dir": DEFAULT_OUTPUT_DIR.as_posix(),
        "tool_count": tool_surface.get("tool_count"),
        "runtime_slice": "staging_only_single_artifact",
        "source_review_status": "ready_for_external_source_review",
        "existing_packet": packet_evidence,
        "broad_host_promotion_allowed": False,
        "new_governed_tool_allowed": False,
    }


def build_bundle(
    *,
    repo_root: Path,
    output_dir: Path,
    allow_dirty: bool = False,
    run_commands: bool = True,
) -> Path:
    _require_project_root(repo_root)
    check = build_check_report(repo_root, validate_existing_packet=False)
    if check["failures"]:
        raise TrustedHostPromotionRuntimeSourceReviewBundleError(
            "; ".join(check["failures"])
        )
    commit = _git(repo_root, ["rev-parse", "HEAD"])
    dirty = bool(_git(repo_root, ["status", "--short"]))
    if dirty and not allow_dirty:
        raise TrustedHostPromotionRuntimeSourceReviewBundleError(
            "working tree is dirty; commit before source-review handoff"
        )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    check = {
        **check,
        "existing_packet": {
            "present": True,
            "commit": commit,
            "commit_matches_head": True,
            "generated_from_clean_tree": not dirty,
            "artifact_hashes_match_files": False,
            "bundled_files_match_head": False,
            "redaction_scan_valid": False,
            "candidate_digest_evidence_valid": False,
            "candidate_index_evidence_matches": False,
        },
    }

    context = {
        "commit": commit,
        "dirty": dirty,
        "check": check,
    }
    candidate_evidence = _candidate_digest_evidence(repo_root, commit=commit, dirty=dirty)
    context["candidate_evidence"] = candidate_evidence
    files = {
        "00_TRUSTED_HOST_PROMOTION_RUNTIME_SOURCE_REVIEW_INDEX.md": _index(context),
        "01_TRUSTED_HOST_PROMOTION_RUNTIME_SOURCE_REVIEW_PROMPT.md": _prompt(context),
        "02_TRUSTED_HOST_PROMOTION_RUNTIME_SOURCE_BUNDLE.md": _bundle_files(
            repo_root, SOURCE_FILES
        ),
        "03_TRUSTED_HOST_PROMOTION_RUNTIME_TESTS_BUNDLE.md": _bundle_files(
            repo_root, TEST_FILES
        ),
        "04_TRUSTED_HOST_PROMOTION_RUNTIME_CONTRACTS_BUNDLE.md": _bundle_files(
            repo_root, CONTRACT_DOCS
        ),
        "05_TRUSTED_HOST_PROMOTION_RUNTIME_GATE_EVIDENCE.json": _json(check),
        "08_TRUSTED_HOST_PROMOTION_RUNTIME_INTAKE_COMMANDS.md": _intake_commands(),
    }
    for name, content in files.items():
        (output_dir / name).write_text(_packet_text(content), encoding="utf-8")
    _write_json(
        output_dir / RUNTIME_CANDIDATE_REVIEW_PACKET,
        candidate_evidence["candidate_review_packet"],
    )
    _write_json(
        output_dir / RUNTIME_CANDIDATE_DIGEST_EVIDENCE,
        {
            key: value
            for key, value in candidate_evidence.items()
            if key != "candidate_review_packet"
        },
    )

    decision_output = _command_output(
        ["make", "trusted-host-promotion-runtime-implementation-decision-check"],
        repo_root=repo_root,
        run_commands=run_commands,
    )
    negative_output = _command_output(
        ["make", "trusted-host-promotion-negative-transcripts"],
        repo_root=repo_root,
        run_commands=run_commands,
    )
    governance_drift_output = _command_output(
        ["make", "trusted-host-promotion-governance-drift-transcripts"],
        repo_root=repo_root,
        run_commands=run_commands,
    )
    no_new_powers_output = _command_output(
        ["make", "no-new-powers-guardrail"],
        repo_root=repo_root,
        run_commands=run_commands,
    )
    tool_surface_output = _command_output(
        ["make", "tool-surface-invariant-gate"],
        repo_root=repo_root,
        run_commands=run_commands,
    )
    (output_dir / "06_TRUSTED_HOST_PROMOTION_RUNTIME_EVIDENCE.md").write_text(
        _packet_text(
            _evidence(
                decision_output,
                negative_output,
                governance_drift_output,
                no_new_powers_output,
                tool_surface_output,
            )
        ),
        encoding="utf-8",
    )
    _write_command_output(
        output_dir / "07_TRUSTED_HOST_PROMOTION_RUNTIME_FOCUSED_TESTS.txt",
        _command_output(
            FOCUSED_TEST_COMMAND,
            repo_root=repo_root,
            run_commands=run_commands,
        ),
    )
    governance_transcript = (
        repo_root
        / "var/review-packets/v3/trusted-host-promotion-governance-drift/"
        "TRUSTED_HOST_PROMOTION_GOVERNANCE_DRIFT_TRANSCRIPTS.md"
    )
    governance_packet_path = (
        output_dir / "09_TRUSTED_HOST_PROMOTION_GOVERNANCE_DRIFT_TRANSCRIPTS.md"
    )
    if run_commands:
        if not governance_transcript.is_file():
            raise TrustedHostPromotionRuntimeSourceReviewBundleError(
                "governance-drift transcript command did not produce its artifact"
            )
        governance_packet_path.write_text(
            governance_transcript.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    else:
        governance_packet_path.write_text(
            "# Trusted-Host Promotion Governance-Drift Transcripts\n\n"
            "Command execution skipped for packet-shape validation.\n",
            encoding="utf-8",
        )
    redaction_report = _packet_redaction_report(output_dir, repo_root=repo_root)
    _write_json(
        output_dir / "10_TRUSTED_HOST_PROMOTION_RUNTIME_REDACTION_SCAN.json",
        redaction_report,
    )
    if not redaction_report["valid"]:
        raise TrustedHostPromotionRuntimeSourceReviewBundleError(
            "generated packet failed bounded evidence redaction scan"
        )
    _write_json(output_dir / HASH_MANIFEST, _hashes(output_dir))
    packet_evidence = _existing_packet_evidence(repo_root, output_dir)
    check["existing_packet"] = packet_evidence
    _write_json(
        output_dir / "05_TRUSTED_HOST_PROMOTION_RUNTIME_GATE_EVIDENCE.json",
        check,
    )
    _write_json(output_dir / HASH_MANIFEST, _hashes(output_dir))
    final_evidence = _existing_packet_evidence(repo_root, output_dir)
    if (
        not final_evidence["commit_matches_head"]
        or not final_evidence["artifact_hashes_match_files"]
        or not final_evidence["bundled_files_match_head"]
        or not final_evidence["redaction_scan_valid"]
        or (not allow_dirty and not final_evidence["candidate_digest_evidence_valid"])
        or (not allow_dirty and not final_evidence["candidate_index_evidence_matches"])
        or (not allow_dirty and not final_evidence["generated_from_clean_tree"])
    ):
        raise TrustedHostPromotionRuntimeSourceReviewBundleError(
            "generated packet failed exact-candidate self-validation"
        )
    return output_dir


def _index(context: dict[str, Any]) -> str:
    candidate = context["candidate_evidence"]
    return f"""# Trusted-Host Promotion Runtime Source Review Handoff

This packet prepares the implemented staging-only `ERG-005` runtime slice for source review.

## Boundary

- Lane: trusted-host promotion runtime.
- Finding namespace: `{FINDING_NAMESPACE}`.
- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Tool count: `{context["check"]["tool_count"]}`.
- Runtime slice: one stored sandbox/workspace artifact -> one approved local host-staging placement.
- Runtime candidate ID: `{candidate["candidate_id"]}`.
- Candidate inventory digest: `{candidate["reviewed_inventory_digest"]}`.
- Dependency-lock digest: `{candidate["dependency_lock_digest"]}`.
- Immutable release-artifact digest: `{candidate["release_artifact_digest"]}`.
- Detached candidate review-packet digest: `{candidate["review_packet_digest"]}`.
- MCP/tool manifest exposure: not added.
- Approved-output publishing: not implemented.
- Arbitrary host paths or broad host writes: not implemented.

## Send These Files

1. `00_TRUSTED_HOST_PROMOTION_RUNTIME_SOURCE_REVIEW_INDEX.md`
2. `01_TRUSTED_HOST_PROMOTION_RUNTIME_SOURCE_REVIEW_PROMPT.md`
3. `02_TRUSTED_HOST_PROMOTION_RUNTIME_SOURCE_BUNDLE.md`
4. `03_TRUSTED_HOST_PROMOTION_RUNTIME_TESTS_BUNDLE.md`
5. `04_TRUSTED_HOST_PROMOTION_RUNTIME_CONTRACTS_BUNDLE.md`
6. `05_TRUSTED_HOST_PROMOTION_RUNTIME_GATE_EVIDENCE.json`
7. `06_TRUSTED_HOST_PROMOTION_RUNTIME_EVIDENCE.md`
8. `07_TRUSTED_HOST_PROMOTION_RUNTIME_FOCUSED_TESTS.txt`
9. `08_TRUSTED_HOST_PROMOTION_RUNTIME_INTAKE_COMMANDS.md`
10. `09_TRUSTED_HOST_PROMOTION_GOVERNANCE_DRIFT_TRANSCRIPTS.md`
11. `10_TRUSTED_HOST_PROMOTION_RUNTIME_REDACTION_SCAN.json`
12. `{RUNTIME_CANDIDATE_REVIEW_PACKET}`
13. `{RUNTIME_CANDIDATE_DIGEST_EVIDENCE}`
14. `{HASH_MANIFEST}`

## What This Does Not Approve

This packet does not approve broad trusted-host promotion, arbitrary host paths,
overwrite/delete/move behavior, approved-output publishing, Mission Control runtime authority,
sandbox orchestration, SIEM adapter behavior, compliance automation, production identity, runtime
Postgres, hosted telemetry, remote MCP, shell, Docker, Kubernetes, browser automation, arbitrary
HTTP, plugin SDK behavior, or public/security-product positioning.
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# Trusted-Host Promotion Runtime Source Review Prompt

You are reviewing Ithildin as a source reviewer for the implemented staging-only trusted-host
promotion runtime slice. Treat this as source-level review if and only if you inspect the attached
source bundle, focused tests, contract docs, gate evidence, and command evidence.

Reviewed commit: `{context["commit"]}`
Area: `trusted-host-promotion-runtime`
Finding namespace: `{FINDING_NAMESPACE}`

Please answer whether this lane can be locally dispositioned for the v0.1 local-preview runtime
boundary. If it cannot, explain exactly which implementation issue or evidence gap blocks closure.

Review that:

- all runtime routes are admin-protected;
- requester, approver, and executor identities are server-derived and generation-bound;
- no MCP tool, tool manifest, or governed tool power was added;
- proposals and apply payloads are closed and bounded;
- every principal, workspace, sandbox, host, policy, manifest, schema, candidate, and approval
  component is revalidated immediately before one atomic reservation;
- migrations are one-transaction, downgrade-safe, idempotent, and preserve legacy rows without
  synthesizing authority;
- the exact runtime candidate is bound to a clean commit, closed file inventory, dependency lock,
  immutable Git-archive release domain, and detached review packet;
- source artifacts are relative, workspace-confined, UTF-8 text, size-limited, and re-hashed before
  staging;
- hidden/sensitive paths, `.git`, symlinks, hardlinks, traversal, stale hashes, replayed approvals,
  and extra apply fields fail safely;
- approval consumption is one-time and evidence-bound;
- completion is recorded only after append-only audit evidence succeeds, while interrupted and
  post-write recovery states remain terminal and non-retryable;
- host staging accepts only safe `host-staging://<label>` labels, not raw host paths;
- placement uses create-exclusive behavior and does not overwrite;
- API responses, audit events, diagnostics, and transcripts do not expose file contents, diffs,
  prompts, secrets, raw sensitive paths, or raw host paths.

Use finding IDs in the `EXT-TRUSTED-HOST-RUNTIME-###` namespace. For each actionable finding,
include severity, area, affected files/functions, blocking status, disposition, and recommended
fix.

Do not approve broad host writes, approved-output publishing, Mission Control runtime authority,
sandbox orchestration, SIEM custody, compliance automation, production positioning, public/security
product claims, or new governed tool powers.
"""


def _evidence(
    decision_output: str,
    negative_output: str,
    governance_drift_output: str,
    no_new_powers_output: str,
    tool_surface_output: str,
) -> str:
    return f"""# Trusted-Host Promotion Runtime Evidence

## Runtime Implementation Decision

```text
{decision_output}
```

## Observed Negative Transcripts

```text
{negative_output}
```

## Observed Governance-Drift Matrix

```text
{governance_drift_output}
```

## No-New-Powers Guardrail

```text
{no_new_powers_output}
```

## Tool Surface Invariant

```text
{tool_surface_output}
```
"""


def _intake_commands() -> str:
    return """# Trusted-Host Promotion Runtime Intake Commands

```bash
make trusted-host-promotion-runtime-implementation-decision-check
make trusted-host-promotion-negative-transcripts
make trusted-host-promotion-governance-drift-transcripts
make no-new-powers-guardrail
make tool-surface-invariant-gate
uv run pytest \\
  tests/test_api_service.py::test_trusted_host_promotion_stages_single_artifact_after_approval \\
  tests/test_api_service.py::test_trusted_host_promotion_denies_stale_and_unsafe_inputs \\
  -q
```
"""


def _bundle_files(repo_root: Path, paths: list[str]) -> str:
    chunks: list[str] = []
    for relative in paths:
        path = repo_root / relative
        if not path.exists():
            raise TrustedHostPromotionRuntimeSourceReviewBundleError(
                f"missing bundle file: {relative}"
            )
        chunks.append(f"## {relative}\n\n```text\n{path.read_text(encoding='utf-8')}\n```")
    return "\n\n".join(chunks)


def _collect_missing(
    repo_root: Path, paths: list[str], label: str, failures: list[str]
) -> None:
    for relative in paths:
        if not (repo_root / relative).exists():
            failures.append(f"missing {label}: {relative}")


def _command_output(
    command: list[str],
    *,
    repo_root: Path,
    run_commands: bool,
) -> str:
    if not run_commands:
        return f"skipped command: {' '.join(command)}"
    process = subprocess.run(
        command,
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    output = (process.stdout + process.stderr).strip()
    if process.returncode != 0:
        raise TrustedHostPromotionRuntimeSourceReviewBundleError(
            f"evidence command failed ({process.returncode}): {' '.join(command)}"
        )
    return f"$ {' '.join(command)}\nexit_code={process.returncode}\n{output}"


def _write_command_output(path: Path, output: str) -> None:
    path.write_text(output + "\n", encoding="utf-8")


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(_json(payload) + "\n", encoding="utf-8")


def _json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _candidate_digest_evidence(
    repo_root: Path,
    *,
    commit: str,
    dirty: bool,
) -> dict[str, Any]:
    candidate_paths = _runtime_candidate_paths(repo_root)
    files = [
        {
            "path": relative,
            "sha256": _file_digest(repo_root / relative),
        }
        for relative in candidate_paths
    ]
    inventory_schema_version = "1"
    reviewed_inventory_digest = _sha256_json(
        {"schema_version": inventory_schema_version, "files": files}
    )
    dependency_lock_digest = _file_digest(repo_root / "uv.lock")
    release_artifact_digest = _git_archive_digest(repo_root, commit)
    evidence_schema_version = "1"
    candidate_core = {
        "source_commit": commit,
        "inventory_schema_version": inventory_schema_version,
        "reviewed_inventory_digest": reviewed_inventory_digest,
        "dependency_lock_digest": dependency_lock_digest,
        "release_artifact_digest": release_artifact_digest,
        "evidence_schema_version": evidence_schema_version,
    }
    candidate_id = _sha256_json(candidate_core)
    candidate_review_packet = {
        "schema_version": "1",
        "candidate_id": candidate_id,
        "source_commit": commit,
        "finding_namespace": FINDING_NAMESPACE,
        "review_scope": "trusted_host_promotion_runtime_staging_only",
        "external_review_complete": False,
    }
    review_packet_digest = _sha256_bytes(
        (_json(candidate_review_packet) + "\n").encode("utf-8")
    )
    return {
        "schema_version": "1",
        "source_commit": commit,
        "source_dirty": dirty,
        "candidate_id": candidate_id,
        "inventory_schema_version": inventory_schema_version,
        "inventory_file_count": len(files),
        "inventory_files": files,
        "reviewed_inventory_digest": reviewed_inventory_digest,
        "dependency_lock_path": "uv.lock",
        "dependency_lock_digest": dependency_lock_digest,
        "release_artifact_domain": "git_archive_exact_commit",
        "release_artifact_digest": release_artifact_digest,
        "review_packet_path": RUNTIME_CANDIDATE_REVIEW_PACKET,
        "review_packet_digest": review_packet_digest,
        "evidence_schema_version": evidence_schema_version,
        "digest_domains_acyclic": True,
        "candidate_review_packet": candidate_review_packet,
        "authorization_record_created": False,
        "external_review_complete": False,
    }


def _runtime_candidate_paths(repo_root: Path) -> list[str]:
    process = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if process.returncode != 0:
        raise TrustedHostPromotionRuntimeSourceReviewBundleError(
            "runtime candidate inventory is unavailable"
        )
    exact = {
        "deploy/Dockerfile.api",
        "pyproject.toml",
        "tool-manifests.lock.json",
        "uv.lock",
    }
    prefixes = (
        "apps/api/",
        "migrations/",
        "packages/",
        "policies/",
        "principals/",
        "schemas/",
        "tool-manifests/",
        "trusted-hosts/",
        "workspaces/",
    )
    candidates = sorted(
        relative
        for relative in process.stdout.splitlines()
        if relative in exact or relative.startswith(prefixes)
    )
    if not candidates or "uv.lock" not in candidates:
        raise TrustedHostPromotionRuntimeSourceReviewBundleError(
            "runtime candidate inventory is incomplete"
        )
    missing = [relative for relative in candidates if not (repo_root / relative).is_file()]
    if missing:
        raise TrustedHostPromotionRuntimeSourceReviewBundleError(
            "runtime candidate inventory contains unavailable files"
        )
    return candidates


def _packet_redaction_report(output_dir: Path, *, repo_root: Path) -> dict[str, Any]:
    scanned_names = [
        "00_TRUSTED_HOST_PROMOTION_RUNTIME_SOURCE_REVIEW_INDEX.md",
        "01_TRUSTED_HOST_PROMOTION_RUNTIME_SOURCE_REVIEW_PROMPT.md",
        "05_TRUSTED_HOST_PROMOTION_RUNTIME_GATE_EVIDENCE.json",
        "06_TRUSTED_HOST_PROMOTION_RUNTIME_EVIDENCE.md",
        "07_TRUSTED_HOST_PROMOTION_RUNTIME_FOCUSED_TESTS.txt",
        "08_TRUSTED_HOST_PROMOTION_RUNTIME_INTAKE_COMMANDS.md",
        "09_TRUSTED_HOST_PROMOTION_GOVERNANCE_DRIFT_TRANSCRIPTS.md",
        RUNTIME_CANDIDATE_REVIEW_PACKET,
        RUNTIME_CANDIDATE_DIGEST_EVIDENCE,
    ]
    patterns = [
        ("repo_absolute_path", re.escape(repo_root.as_posix())),
        ("user_home_path", r"/Users/"),
        ("test_bearer_token", r"correct-token"),
        ("sample_bearer_token", r"dev-admin-token"),
        ("stack_trace", r"Traceback \(most recent call last\)"),
        ("authorization_header", r"(?i)authorization:\s*bearer\s+\S+"),
    ]
    findings: list[dict[str, str]] = []
    for name in scanned_names:
        path = output_dir / name
        text = path.read_text(encoding="utf-8")
        for finding_type, pattern in patterns:
            if re.search(pattern, text):
                findings.append({"path": name, "finding_type": finding_type})
    return {
        "schema_version": "1",
        "valid": not findings,
        "scanned_files": scanned_names,
        "scanned_file_count": len(scanned_names),
        "finding_count": len(findings),
        "findings": findings,
        "source_test_contract_bundles_excluded": True,
        "exclusion_reason": (
            "bundled reviewed source contains deliberate security-test literals; "
            "generated handoff and evidence surfaces are scanned"
        ),
    }


def _file_digest(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _sha256_json(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return _sha256_bytes(encoded)


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _git_archive_digest(repo_root: Path, commit: str) -> str:
    process = subprocess.run(
        ["git", "archive", "--format=tar", commit],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if process.returncode != 0:
        raise TrustedHostPromotionRuntimeSourceReviewBundleError(
            "immutable release artifact domain is unavailable"
        )
    return _sha256_bytes(process.stdout)


def _candidate_digest_evidence_valid(repo_root: Path, output_dir: Path) -> bool:
    evidence_path = output_dir / RUNTIME_CANDIDATE_DIGEST_EVIDENCE
    review_packet_path = output_dir / RUNTIME_CANDIDATE_REVIEW_PACKET
    try:
        evidence = _load_json_without_duplicates(evidence_path)
        review_packet = _load_json_without_duplicates(review_packet_path)
    except (OSError, ValueError):
        return False
    if not isinstance(evidence, dict) or not isinstance(review_packet, dict):
        return False
    if set(evidence) != {
        "schema_version",
        "source_commit",
        "source_dirty",
        "candidate_id",
        "inventory_schema_version",
        "inventory_file_count",
        "inventory_files",
        "reviewed_inventory_digest",
        "dependency_lock_path",
        "dependency_lock_digest",
        "release_artifact_domain",
        "release_artifact_digest",
        "review_packet_path",
        "review_packet_digest",
        "evidence_schema_version",
        "digest_domains_acyclic",
        "authorization_record_created",
        "external_review_complete",
    }:
        return False
    commit = evidence.get("source_commit")
    files = evidence.get("inventory_files")
    if not isinstance(commit, str) or not isinstance(files, list):
        return False
    if evidence.get("source_dirty") is not False:
        return False
    if (
        evidence.get("schema_version") != "1"
        or evidence.get("inventory_schema_version") != "1"
        or evidence.get("dependency_lock_path") != "uv.lock"
        or evidence.get("release_artifact_domain") != "git_archive_exact_commit"
        or evidence.get("review_packet_path") != RUNTIME_CANDIDATE_REVIEW_PACKET
        or evidence.get("evidence_schema_version") != "1"
    ):
        return False
    if _git(repo_root, ["rev-parse", "HEAD"]) != commit:
        return False
    if _git(repo_root, ["status", "--short"]):
        return False
    if evidence.get("review_packet_digest") != _file_digest(review_packet_path):
        return False
    if evidence.get("dependency_lock_digest") != _file_digest(repo_root / "uv.lock"):
        return False
    if evidence.get("release_artifact_digest") != _git_archive_digest(repo_root, commit):
        return False
    normalized_files: list[dict[str, str]] = []
    previous = ""
    for record in files:
        if not isinstance(record, dict) or set(record) != {"path", "sha256"}:
            return False
        relative = record.get("path")
        digest = record.get("sha256")
        if not isinstance(relative, str) or relative <= previous:
            return False
        path = repo_root / relative
        if not path.is_file() or digest != _file_digest(path):
            return False
        previous = relative
        normalized_files.append({"path": relative, "sha256": digest})
    expected_paths = _runtime_candidate_paths(repo_root)
    if [record["path"] for record in normalized_files] != expected_paths:
        return False
    if evidence.get("inventory_file_count") != len(expected_paths):
        return False
    inventory_schema_version = evidence.get("inventory_schema_version")
    reviewed_inventory_digest = _sha256_json(
        {"schema_version": inventory_schema_version, "files": normalized_files}
    )
    if evidence.get("reviewed_inventory_digest") != reviewed_inventory_digest:
        return False
    candidate_core = {
        "source_commit": commit,
        "inventory_schema_version": inventory_schema_version,
        "reviewed_inventory_digest": reviewed_inventory_digest,
        "dependency_lock_digest": evidence.get("dependency_lock_digest"),
        "release_artifact_digest": evidence.get("release_artifact_digest"),
        "evidence_schema_version": evidence.get("evidence_schema_version"),
    }
    candidate_id = _sha256_json(candidate_core)
    expected_review_packet = {
        "schema_version": "1",
        "candidate_id": candidate_id,
        "source_commit": commit,
        "finding_namespace": FINDING_NAMESPACE,
        "review_scope": "trusted_host_promotion_runtime_staging_only",
        "external_review_complete": False,
    }
    return (
        evidence.get("candidate_id") == candidate_id
        and review_packet == expected_review_packet
        and evidence.get("digest_domains_acyclic") is True
        and evidence.get("authorization_record_created") is False
        and evidence.get("external_review_complete") is False
    )


def _bundled_files_match_head(repo_root: Path, output_dir: Path) -> bool:
    bundles = {
        "02_TRUSTED_HOST_PROMOTION_RUNTIME_SOURCE_BUNDLE.md": SOURCE_FILES,
        "03_TRUSTED_HOST_PROMOTION_RUNTIME_TESTS_BUNDLE.md": TEST_FILES,
        "04_TRUSTED_HOST_PROMOTION_RUNTIME_CONTRACTS_BUNDLE.md": CONTRACT_DOCS,
    }
    try:
        return all(
            output_dir.joinpath(name).read_text(encoding="utf-8")
            == _packet_text(_bundle_files(repo_root, paths))
            for name, paths in bundles.items()
        )
    except (OSError, UnicodeError, TrustedHostPromotionRuntimeSourceReviewBundleError):
        return False


def _candidate_index_evidence_matches(output_dir: Path) -> bool:
    evidence_path = output_dir / RUNTIME_CANDIDATE_DIGEST_EVIDENCE
    index_path = output_dir / "00_TRUSTED_HOST_PROMOTION_RUNTIME_SOURCE_REVIEW_INDEX.md"
    try:
        evidence = _load_json_without_duplicates(evidence_path)
        index = index_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError):
        return False
    if not isinstance(evidence, dict):
        return False
    labels = {
        "Reviewed commit": "source_commit",
        "Runtime candidate ID": "candidate_id",
        "Candidate inventory digest": "reviewed_inventory_digest",
        "Dependency-lock digest": "dependency_lock_digest",
        "Immutable release-artifact digest": "release_artifact_digest",
        "Detached candidate review-packet digest": "review_packet_digest",
    }
    lines = index.splitlines()
    for label, key in labels.items():
        value = evidence.get(key)
        if not isinstance(value, str):
            return False
        expected = f"- {label}: `{value}`."
        matching = [line for line in lines if line.startswith(f"- {label}:")]
        if matching != [expected]:
            return False
    return True


def _hashes(output_dir: Path) -> list[dict[str, Any]]:
    records = []
    for path in sorted(output_dir.iterdir()):
        if path.name == HASH_MANIFEST:
            continue
        data = path.read_bytes()
        records.append(
            {
                "path": path.name,
                "sha256": f"sha256:{hashlib.sha256(data).hexdigest()}",
                "bytes": len(data),
            }
        )
    return records


def _existing_packet_evidence(
    repo_root: Path,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    output_dir = output_dir or repo_root / DEFAULT_OUTPUT_DIR
    if not output_dir.is_dir():
        return {
            "present": False,
            "commit": None,
            "commit_matches_head": None,
            "generated_from_clean_tree": None,
            "artifact_hashes_match_files": None,
            "bundled_files_match_head": None,
            "redaction_scan_valid": None,
            "candidate_digest_evidence_valid": None,
            "candidate_index_evidence_matches": None,
        }

    head = _git(repo_root, ["rev-parse", "HEAD"])
    index_path = output_dir / "00_TRUSTED_HOST_PROMOTION_RUNTIME_SOURCE_REVIEW_INDEX.md"
    prompt_path = output_dir / "01_TRUSTED_HOST_PROMOTION_RUNTIME_SOURCE_REVIEW_PROMPT.md"
    manifest_path = output_dir / HASH_MANIFEST
    index = index_path.read_text(encoding="utf-8") if index_path.is_file() else ""
    prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.is_file() else ""
    packet_commit = _extract_packet_commit(index)
    prompt_commit = _extract_packet_commit(prompt)

    hashes_match = False
    try:
        recorded_hashes = _load_json_without_duplicates(manifest_path)
    except (OSError, ValueError):
        recorded_hashes = None
    if isinstance(recorded_hashes, list):
        hashes_match = recorded_hashes == _hashes(output_dir)
    redaction_scan_valid = False
    redaction_path = (
        output_dir / "10_TRUSTED_HOST_PROMOTION_RUNTIME_REDACTION_SCAN.json"
    )
    try:
        redaction_payload = _load_json_without_duplicates(redaction_path)
    except (OSError, ValueError):
        redaction_payload = None
    if isinstance(redaction_payload, dict):
        redaction_scan_valid = (
            redaction_payload == _packet_redaction_report(output_dir, repo_root=repo_root)
            and redaction_payload.get("valid") is True
        )
    candidate_digest_evidence_valid = _candidate_digest_evidence_valid(
        repo_root,
        output_dir,
    )
    bundled_files_match_head = _bundled_files_match_head(repo_root, output_dir)
    candidate_index_evidence_matches = _candidate_index_evidence_matches(output_dir)

    return {
        "present": True,
        "commit": packet_commit,
        "commit_matches_head": packet_commit == head and prompt_commit == head,
        "generated_from_clean_tree": "Dirty at generation: `false`." in index,
        "artifact_hashes_match_files": hashes_match,
        "bundled_files_match_head": bundled_files_match_head,
        "redaction_scan_valid": redaction_scan_valid,
        "candidate_digest_evidence_valid": candidate_digest_evidence_valid,
        "candidate_index_evidence_matches": candidate_index_evidence_matches,
    }


def _embedded_packet_evidence(output_dir: Path) -> dict[str, Any] | None:
    gate_evidence_path = (
        output_dir / "05_TRUSTED_HOST_PROMOTION_RUNTIME_GATE_EVIDENCE.json"
    )
    try:
        gate_evidence = _load_json_without_duplicates(gate_evidence_path)
    except (OSError, ValueError):
        return None
    if not isinstance(gate_evidence, dict):
        return None
    packet_evidence = gate_evidence.get("existing_packet")
    return packet_evidence if isinstance(packet_evidence, dict) else None


def _extract_packet_commit(text: str) -> str | None:
    marker = "Reviewed commit: `"
    if text.count(marker) != 1:
        return None
    return text.partition(marker)[2].partition("`")[0] or None


def _packet_text(text: str) -> str:
    return text.strip() + "\n"


def _load_json_without_duplicates(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_json_object_without_duplicates,
    )


def _json_object_without_duplicates(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _require_project_root(repo_root: Path) -> None:
    for marker in ("pyproject.toml", "Makefile", "tool-manifests.lock.json"):
        if not (repo_root / marker).exists():
            raise TrustedHostPromotionRuntimeSourceReviewBundleError(
                "not an Ithildin repository root"
            )


def _git(repo_root: Path, args: list[str]) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if process.returncode != 0:
        raise TrustedHostPromotionRuntimeSourceReviewBundleError(process.stderr.strip())
    return process.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, cast

import pytest

from scripts import (
    accepted_risk_register,
    capability_decision_report,
    capability_expansion_gate,
    closure_matrix_evidence_sync,
    consolidate_review_packet,
    evidence_confusion_gate,
    evidence_contracts_check,
    external_findings_intake_dry_run,
    external_response_normalize,
    external_response_template_check,
    external_review_closure_gate,
    external_review_dispatch_packets,
    internal_review_packet,
    no_new_powers_guardrail,
    packet_redaction_scan,
    patch_apply_external_review_packet,
    release_evidence,
    release_guardrails,
    release_packet,
    review_docs,
    review_findings_collect,
    review_packet_bundle,
    review_packet_diff,
    review_packet_source_pointers,
    review_run_manifest,
    reviewer_artifact_manifest,
    reviewer_findings,
    source_review_transcript_packet,
    test_determinism_gate,
    tool_surface_invariant_gate,
    v04_review_packet,
    v05_boundary_decision_draft_check,
    v05_handoff_packet_check,
    v05_threat_model_delta_check,
    v06_closure_readiness,
    v06_final_handoff,
    v06_lane_status,
    v07_closure_prep,
    v07_patch_apply_recheck,
)


def test_release_evidence_fails_outside_repo_markers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["release_evidence.py"])

    result = release_evidence.main()

    assert result == 1
    assert "must be run from the Ithildin repo root" in capsys.readouterr().err


def test_release_guardrails_catches_forbidden_claims(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    docs.joinpath("unsafe.md").write_text(
        "Ithildin is production-ready enterprise identity.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(release_guardrails, "ROOT", tmp_path)
    monkeypatch.setattr(release_guardrails, "FORBIDDEN_CLAIM_DOCS", [docs])

    failures = release_guardrails._check_forbidden_claims()

    assert any("production-ready" in failure for failure in failures)
    assert any("enterprise identity" in failure for failure in failures)


def test_release_packet_fails_outside_repo_markers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["release_packet.py"])

    result = release_packet.main()

    assert result == 1
    assert "must be run from the Ithildin repo root" in capsys.readouterr().err


def test_release_packet_json_is_secret_free(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["release_packet.py", "--json"])

    result = release_packet.main()

    assert result == 0
    output = capsys.readouterr().out
    assert "dev-admin-token-change-me" not in output
    assert "release_packet_placeholder" not in output
    assert "ITHILDIN_ADMIN_TOKEN" not in output
    assert "tool-manifests.lock.json" in output
    assert "http.fetch" in output
    assert "production identity" in output
    assert "review_doc_hashes" in output


def test_release_packet_review_docs_exist() -> None:
    missing = [doc for doc in review_docs.REVIEW_DOCS if not Path(doc).exists()]

    assert missing == []


def test_v03_milestone_manifest_is_linked_and_complete() -> None:
    manifest_doc = Path("docs/codex/v0.3-milestone-manifest.md").read_text(encoding="utf-8")
    manifest = json.loads(
        Path("docs/codex/v0.3-milestone-manifest.json").read_text(encoding="utf-8")
    )
    readme = Path("README.md").read_text(encoding="utf-8")
    planning_seed = Path("docs/codex/v0.2-planning-seed.md").read_text(encoding="utf-8")

    task_ids = [milestone["id"] for milestone in manifest["milestones"]]
    assert task_ids == [f"{index:03d}" for index in range(85, 113)]
    assert manifest["runtime_boundary"] == "v0.1 local-preview"
    assert "shell execution" in manifest["deferred_boundaries"]
    assert "trust-boundary regression" in manifest["stop_conditions"]
    assert "external source-review closure" in manifest["subagent_policy"]["not_authorized_for"]
    assert "v0.3-milestone-manifest.json" in manifest_doc
    assert "v0.3-milestone-manifest.md" in readme
    assert "v0.3-milestone-manifest.md" in planning_seed
    assert "docs/codex/v0.3-milestone-manifest.md" in review_docs.REVIEW_DOCS


def test_v04_milestone_manifest_is_linked_and_scopes_remaining_plan() -> None:
    manifest_doc = Path("docs/codex/v0.4-milestone-manifest.md").read_text(encoding="utf-8")
    manifest = json.loads(
        Path("docs/codex/v0.4-milestone-manifest.json").read_text(encoding="utf-8")
    )
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    review_packet = Path("docs/codex/v0.3-review-packet.md").read_text(encoding="utf-8")

    task_ids = [milestone["id"] for milestone in manifest["milestones"]]
    assert task_ids == [f"{index:03d}" for index in range(113, 152)]
    assert manifest["completed_range"] == "113-151"
    assert manifest["planned_range"] == "none"
    assert manifest["gating_overlay_version"] == "1"
    assert manifest["runtime_boundary"] == "v0.1 local-preview"
    assert "shell execution" in manifest["deferred_boundaries"]
    assert "new powerful tool class" in manifest["external_review_required_before"]
    assert "Capability Expansion Gate" in {gate["name"] for gate in manifest["named_gates"]}
    assert manifest["waves"][1]["tasks"] == [
        "123",
        "124",
        "125",
        "126",
        "127",
        "128",
    ]
    assert "Tasks 123-151" in manifest_doc
    assert "ready for external/source review" in manifest_doc
    assert "v0.4-gating-overlay.md" in manifest_doc
    assert "v0.4-milestone-manifest.json" in manifest_doc
    assert "Tasks 113-151 are" in readme
    assert "123 - v0.4 gating overlay | Done" in backlog
    assert "124 - Release evidence schema gate v2 | Done" in backlog
    assert "125 - Review packet diff gate v2 | Done" in backlog
    assert "126 - Release guardrail expansion v2 | Done" in backlog
    assert "127 - Secrets hygiene and packet redaction scanner | Done" in backlog
    assert "128 - Test isolation and determinism gate | Done" in backlog
    assert "129 - Signed-evidence verifier hardening | Done" in backlog
    assert "130 - Audit integrity adversarial suite v2 | Done" in backlog
    assert "131 - Evidence contract versioning v2 | Done" in backlog
    assert "132 - Local audit retention and export lifecycle diagnostics | Done" in backlog
    assert "133 - Policy preview/runtime parity harness v2 | Done" in backlog
    assert "134 - OPA boundary decision | Done" in backlog
    assert "135 - Registry fail-closed exhaustive suite | Done" in backlog
    assert "136 - Manifest-change review workflow | Done" in backlog
    assert "v0.4-milestone-manifest.md" in review_packet
    assert "v0.4-gating-overlay.md" in review_packet
    assert "docs/codex/v0.4-milestone-manifest.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/v0.4-gating-overlay.md" in review_docs.REVIEW_DOCS


def test_v04_planned_milestones_have_blocker_metadata() -> None:
    manifest = json.loads(
        Path("docs/codex/v0.4-milestone-manifest.json").read_text(encoding="utf-8")
    )
    required_keys = {
        "blocks_capability_expansion",
        "blocks_broader_distribution",
        "blocks_external_handoff",
        "requires_external_review_before_closure",
        "required_commands",
        "risk_surface",
        "deferred_boundary_must_remain_unchanged",
    }
    valid_blocker_values = {"yes", "no", "conditional"}
    planned = [
        milestone for milestone in manifest["milestones"] if 123 <= int(milestone["id"]) <= 151
    ]

    assert len(planned) == 29
    for milestone in planned:
        assert required_keys <= set(milestone)
        assert milestone["blocks_capability_expansion"] in valid_blocker_values
        assert milestone["blocks_broader_distribution"] in valid_blocker_values
        assert milestone["blocks_external_handoff"] in valid_blocker_values
        assert isinstance(milestone["requires_external_review_before_closure"], bool)
        assert isinstance(milestone["required_commands"], list)
        assert milestone["required_commands"]
        assert isinstance(milestone["risk_surface"], list)
        assert milestone["risk_surface"]
        assert milestone["deferred_boundary_must_remain_unchanged"] is True


def test_v04_gating_overlay_documents_required_stop_gates() -> None:
    overlay = Path("docs/codex/v0.4-gating-overlay.md").read_text(encoding="utf-8")

    for required in [
        "Capability Expansion Gate",
        "Tool-Surface Invariant Gate",
        "Evidence-Confusion Gate",
        "UI/Admin No-Mutation Gate",
        "External-Review Closure Gate",
        "make review-packet-diff-gate OLD=<prior checkpoint> NEW=<current checkpoint>",
        "tool count remains 10",
        "Task 151 creates a review packet. It does not unlock v0.5",
    ]:
        assert required in overlay


def test_negative_review_recipes_reference_existing_tools_and_commands() -> None:
    recipes = Path("docs/codex/negative-review-recipes.md").read_text(encoding="utf-8")
    manifest_names = {
        line.removeprefix("name: ").strip()
        for path in Path("tool-manifests").glob("*.yaml")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("name: ")
    }
    for tool_name in [
        "fs.read",
        "fs.list",
        "fs.patch.propose",
        "fs.patch.apply",
        "http.fetch",
    ]:
        assert tool_name in manifest_names
        assert tool_name in recipes
    for command in ["make demo-seed", "make mcp-inspector-recipes"]:
        assert command in recipes


def test_reviewer_reproduction_map_references_implemented_targets() -> None:
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    for target in [
        "release-check",
        "release-evidence",
        "release-packet",
        "review-candidate",
        "internal-review-packet",
        "evidence-contracts-check",
        "adversarial-corpus-check",
        "resource-limit-check",
        "signed-evidence-demo",
        "signed-evidence-demo-verify",
        "filesystem-contract-check",
        "reviewer-findings-check",
        "v06-review-dispatch-packets",
        "review-packet-bundle",
        "review-packet-consolidated",
        "review-packet-diff",
        "docs-site",
    ]:
        assert f"make {target}" in reproduction_map
        assert f"{target}:" in makefile
    assert "artifact-hashes.json" in reproduction_map
    assert "consolidated-attachment-hashes.json" in reproduction_map
    assert "review-doc-hashes.json" in reproduction_map


def test_review_candidate_target_sequences_handoff_commands() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    target = re.search(r"^review-candidate:\n(?P<body>(?:\t.*\n)+)", makefile, re.MULTILINE)

    assert target is not None
    body = target.group("body")
    expected_commands = [
        "$(MAKE) release-check",
        "$(MAKE) filesystem-contract-check",
        "$(MAKE) signed-evidence-demo",
        "$(MAKE) signed-evidence-demo-verify",
        "$(MAKE) negative-review-transcripts",
        "$(MAKE) v06-review-dispatch-packets",
        "$(MAKE) review-packet-bundle",
        "$(MAKE) review-packet-consolidated",
        "$(MAKE) packet-redaction-scan",
        "$(MAKE) docs-site",
    ]
    positions = [body.index(command) for command in expected_commands]
    assert positions == sorted(positions)
    assert "Review candidate ready: var/review-packets/v0.2/GPT-5.5-Pro-consolidated" in body


def test_consolidated_review_packet_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path
    bundle_dir = repo_root / "var/review-packets/v0.2/ithildin-v0.2-review-packet-abc123"
    bundle_dir.mkdir(parents=True)
    for path in [
        "INDEX.md",
        "release-check.txt",
        "filesystem-contract-check.txt",
        "release-evidence.json",
        "release-packet.md",
        "release-packet.json",
        "review-doc-hashes.json",
        "packet-redaction-scan.txt",
        "artifact-hashes.json",
        "git-summary.txt",
    ]:
        bundle_dir.joinpath(path).write_text(f"# {path}\n", encoding="utf-8")
    for path in [
        "README.md",
        "docs/codex/v0.6-gpt-55-pro-handoff-prompt.md",
        "docs/codex/v0.6-closure-handoff.md",
        "docs/codex/v0.6-boundary-charter.md",
        "docs/codex/v0.6-internal-review-execution-wave-2.md",
        "docs/codex/v0.6-milestone-manifest.md",
        "docs/codex/v0.3-external-review-prompt.md",
        "docs/codex/v0.5-external-review-prompt.md",
        "docs/codex/v0.3-review-packet.md",
        "docs/codex/v0.3-boundary-decision.md",
        "docs/codex/v0.2-external-review-prompt.md",
        "docs/codex/reviewer-reproduction-map.md",
        "docs/codex/v0.5-review-candidate-command.md",
        "docs/codex/v0.5-roadmap-from-v0.4-review.md",
        "docs/codex/v0.5-milestone-manifest.md",
        "docs/codex/v0.5-threat-model-delta.md",
        "docs/codex/v0.2-review-packet.md",
        "docs/codex/v0.2-review-response-and-rc-cleanup.md",
        "docs/codex/v0.2-planning-seed.md",
        "docs/codex/v0.1-security-test-matrix.md",
        "docs/codex/filesystem-executor-contract.md",
        "docs/codex/evidence-contracts.md",
        "docs/codex/threat-model-and-non-goals.md",
        "docs/codex/negative-review-recipes.md",
        "docs/codex/source-review-closure-matrix.md",
        "docs/codex/accepted-risk-register.md",
        "docs/codex/capability-decision-report.md",
        "docs/codex/no-new-powers-guardrail.md",
        "docs/codex/source-review-runbook-v2.md",
        "docs/codex/source-review-transcript-packet.md",
        "docs/codex/reviewer-artifact-manifest-v2.md",
        "docs/codex/external-review-response-intake-template-v2.md",
        "docs/codex/review-packet-source-pointers.md",
        "docs/codex/internal-source-review-pass-1.md",
        "docs/codex/internal-ai-review-workflow.md",
        "docs/codex/autonomous-sprint-guardrails.md",
        "docs/codex/reviewer-finding-template.md",
        "docs/codex/signed-audit-exports.md",
        "docs/codex/signed-manifest-locks.md",
        "docs/codex/local-preview-release.md",
        "docs/codex/mcp-client-examples.md",
        "docs/codex/mcp-inspector-recipes.md",
        "docs/research/source-verification.md",
    ]:
        source = repo_root / path
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(f"# {source.stem}\n", encoding="utf-8")
    demo_summary = (
        repo_root / "var/review-packets/v0.2/signed-evidence-demo/SIGNED_EVIDENCE_DEMO.md"
    )
    demo_summary.parent.mkdir(parents=True)
    demo_summary.write_text("# demo\n", encoding="utf-8")
    negative_transcripts = (
        repo_root
        / "var/review-packets/v0.2/negative-review-transcripts/NEGATIVE_REVIEW_TRANSCRIPTS.md"
    )
    negative_transcripts.parent.mkdir(parents=True)
    negative_transcripts.write_text("# negative transcripts\n", encoding="utf-8")
    monkeypatch.chdir(repo_root)

    output_dir = consolidate_review_packet.build_consolidated_packet(
        repo_root=repo_root,
        bundle_dir=bundle_dir,
        output_dir=repo_root / "var/review-packets/v0.2/GPT-5.5-Pro-consolidated",
    )

    for filename in consolidate_review_packet.ATTACHMENT_FILES:
        assert output_dir.joinpath(filename).exists()
    hashes = json.loads(
        output_dir.joinpath("consolidated-attachment-hashes.json").read_text(encoding="utf-8")
    )
    hash_paths = {entry["path"] for entry in hashes}
    assert hash_paths == set(consolidate_review_packet.ATTACHMENT_FILES)
    assert all(str(entry["sha256"]).startswith("sha256:") for entry in hashes)
    assert "Negative Review Transcripts" in output_dir.joinpath(
        "04_REPRODUCTION_SECURITY_AND_NEGATIVE_RECIPES.md"
    ).read_text(encoding="utf-8")
    assert "v0.6 Review-Closure Packet" in output_dir.joinpath("00_ATTACHMENT_INDEX.md").read_text(
        encoding="utf-8"
    )
    assert "v0.6 GPT 5.5 Pro Handoff Prompt" in output_dir.joinpath(
        "01_START_HERE_AND_REVIEW_PROMPT.md"
    ).read_text(encoding="utf-8")
    assert "v0.6 Closure Handoff" in output_dir.joinpath(
        "02_REVIEW_PACKET_AND_RESPONSE.md"
    ).read_text(encoding="utf-8")
    assert "v0.5 Roadmap From v0.4 Review" in output_dir.joinpath(
        "02_REVIEW_PACKET_AND_RESPONSE.md"
    ).read_text(encoding="utf-8")
    assert "Review Packet Source Pointers" in output_dir.joinpath(
        "04_REPRODUCTION_SECURITY_AND_NEGATIVE_RECIPES.md"
    ).read_text(encoding="utf-8")
    all_output_paths = [path.as_posix() for path in output_dir.rglob("*")]
    assert not any("/.env" in path for path in all_output_paths)
    assert not any("/var/keys/" in path for path in all_output_paths)
    assert not any(path.endswith(".sqlite3") for path in all_output_paths)


def test_security_matrix_splits_link_race_coverage() -> None:
    matrix = Path("docs/codex/v0.1-security-test-matrix.md").read_text(encoding="utf-8")

    assert "Hardlink ambiguity and deeper TOCTOU cases" not in matrix
    assert "Hardlink and symlink cases" in matrix
    assert "Broader TOCTOU/race proofs" in matrix
    assert "Covered after v0.2" not in matrix
    assert "Covered by v0.2 tests; pending external review" in matrix
    assert "Platform filesystem support profile" in matrix
    assert "Documented by Task 080; pending external/source review" in matrix
    assert "filesystem-executor-contract.md" in matrix


def test_source_review_closure_matrix_covers_required_areas() -> None:
    matrix_path = Path("docs/codex/source-review-closure-matrix.md")
    matrix = matrix_path.read_text(encoding="utf-8")
    review_packet = Path("docs/codex/v0.2-review-packet.md").read_text(encoding="utf-8")
    prompt = Path("docs/codex/v0.2-external-review-prompt.md").read_text(encoding="utf-8")

    for area in [
        "fs.read",
        "fs.patch.propose",
        "fs.patch.apply",
        "http.fetch",
        "Audit export/signing",
        "Manifest-lock verification",
        "Policy preview/impact",
        "MCP ingress",
        "Review-console approval flow",
    ]:
        assert area in matrix
    for column in [
        "Reviewer",
        "Date",
        "Findings count",
        "Blocking findings",
        "Disposition",
        "Closure notes",
    ]:
        assert column in matrix
    assert "source-review-closure-matrix.md" in review_packet
    assert "source-review-closure-matrix.md" in prompt


def test_source_review_closure_matrix_v2_separates_review_layers() -> None:
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")

    for column in [
        "Internal review",
        "Subagent review",
        "External review",
        "Finding records",
        "Blocking status",
        "Closure evidence",
    ]:
        assert column in matrix
    assert "v0.3-milestone-manifest.md" in matrix
    assert "Pending Wave 2" in matrix
    assert "Wave 3 subagent review complete" in matrix
    assert "Pending Wave 4" in matrix
    assert "cannot mark an external/source-review row closed" in matrix
    assert "No blocking finding open" in matrix


def test_internal_source_review_pass_is_linked_and_validated() -> None:
    review_path = Path("docs/codex/internal-source-review-pass-1.md")
    review = review_path.read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    review_packet = Path("docs/codex/v0.2-review-packet.md").read_text(encoding="utf-8")
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(encoding="utf-8")

    for area in [
        "`fs.patch.apply` Approval Binding And Atomic Apply",
        "Filesystem Read/Path Handling And Race-Sensitive Behavior",
        "`http.fetch` SSRF/Redirect/DNS/IP Behavior",
        "Signed Audit Export Verification And Manifest-Lock Signature Verification",
        "Policy Preview/Runtime Parity",
        "MCP Ingress Thinness",
        "Review-Console Approval Evidence Flow",
    ]:
        assert area in review
    for finding_id in ["ISR-001", "ISR-002"]:
        assert finding_id in review
    assert set(re.findall(r"\bISR-\d{3}\b", review)) == {"ISR-001", "ISR-002"}
    assert "Codex internal source review pass 1" in matrix
    assert "internal reviewed; pending external review" in matrix
    assert "Addressed by Task 080; pending external review" in review
    assert "filesystem-executor-contract.md" in review
    assert "internal-source-review-pass-1.md" in review_packet
    assert "internal-source-review-pass-1.md" in reproduction_map


def test_filesystem_executor_contract_is_linked_and_validated() -> None:
    contract = Path("docs/codex/filesystem-executor-contract.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    review_packet = Path("docs/codex/v0.2-review-packet.md").read_text(encoding="utf-8")
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(encoding="utf-8")
    local_preview = Path("docs/codex/local-preview-release.md").read_text(encoding="utf-8")

    for required in [
        "macOS",
        "Linux",
        "Windows and WSL are not security-supported",
        "make filesystem-contract-check",
        "O_NOFOLLOW",
        "not a sandbox contract",
    ]:
        assert required in contract
    for linked in [readme, review_packet, reproduction_map, local_preview]:
        assert "filesystem-executor-contract.md" in linked


def test_patch_apply_state_machine_contract_is_linked_and_validated() -> None:
    contract = Path("docs/codex/patch-apply-state-machine.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")

    for required in [
        "approved",
        "executing",
        "executed",
        "prepared",
        "file_replaced",
        "completed",
        "failed",
        "recovery_required",
        "one attempt per approval ID",
        "does not add repair",
    ]:
        assert required in contract
    assert "patch-apply-state-machine.md" in readme
    assert "docs/codex/patch-apply-state-machine.md" in review_docs.REVIEW_DOCS
    assert "Task 089 state-machine contract" in matrix


def test_http_executor_contract_is_linked_and_validated() -> None:
    contract = Path("docs/codex/http-executor-contract.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")

    for required in [
        "HTTP Fetch Executor Contract v2",
        "GET only",
        "exact allowlist",
        "no caller-supplied headers",
        "Parse-Normalize-Allowlist-Resolve-Pin-Open Order",
        "whitespace/control characters",
        "percent-encoded host",
        "malformed ports",
        "IDNA",
        "resolves the destination twice",
        "Redirects repeat",
        "connect to one of the validated IPs",
        "tests/fixtures/http_canonicalization_corpus.json",
        "Audit Fields",
        "proxy",
        "response bodies",
        "not a network sandbox",
    ]:
        assert required in contract
    assert "http-executor-contract.md" in readme
    assert "docs/codex/http-executor-contract.md" in review_docs.REVIEW_DOCS
    assert "Task 093 HTTP executor contract" in matrix
    assert "Tasks 121-122 corpus and contract v2" in matrix


def test_executor_contract_set_indexes_review_surfaces() -> None:
    contract = Path("docs/codex/executor-contract-set.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    review_packet = Path("docs/codex/v0.2-review-packet.md").read_text(encoding="utf-8")
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")

    for required in [
        "Filesystem read",
        "Git read",
        "Patch proposal",
        "Patch apply",
        "HTTP fetch",
        "Audit export/signing",
        "Manifest lock verification",
        "Policy preview/parity",
        "MCP ingress",
        "Review console evidence",
        "git status --porcelain=v1",
        "no executor introduces shell execution",
    ]:
        assert required in contract
    assert "executor-contract-set.md" in readme
    assert "executor-contract-set.md" in review_packet
    assert "executor-contract-set.md" in reproduction_map
    assert "104 - Executor contract set | Done" in backlog
    assert "Task 104 adds" in matrix
    assert "docs/codex/executor-contract-set.md" in review_docs.REVIEW_DOCS


def test_manifest_validation_suite_is_documented() -> None:
    doc = Path("docs/codex/manifest-validation-suite.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    review_packet = Path("docs/codex/v0.2-review-packet.md").read_text(encoding="utf-8")
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")

    for required in [
        "invalid YAML",
        "non-string manifest keys",
        "invalid risk enum values",
        "duplicate lock paths",
        "path escape",
        "signature configuration is incomplete",
    ]:
        assert required in doc
    assert "manifest-validation-suite.md" in readme
    assert "manifest-validation-suite.md" in review_packet
    assert "manifest-validation-suite.md" in reproduction_map
    assert "105 - Tool manifest negative validation suite | Done" in backlog
    assert "Task 105 adds" in matrix
    assert "docs/codex/manifest-validation-suite.md" in review_docs.REVIEW_DOCS


def test_registry_fail_closed_suite_is_documented() -> None:
    doc = Path("docs/codex/registry-fail-closed-suite.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    review_packet = Path("docs/codex/v0.2-review-packet.md").read_text(encoding="utf-8")
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")

    for required in [
        "invalid YAML",
        "principal ID/type mismatch",
        "disabled principals",
        "malformed workspace IDs",
        "traversal roots",
        "disabled named workspace",
    ]:
        assert required in doc
    assert "registry-fail-closed-suite.md" in readme
    assert "registry-fail-closed-suite.md" in review_packet
    assert "registry-fail-closed-suite.md" in reproduction_map
    assert "106 - Principal/workspace registry fail-closed suite | Done" in backlog
    assert "Task 106 adds" in matrix
    assert "docs/codex/registry-fail-closed-suite.md" in review_docs.REVIEW_DOCS


def test_audit_integrity_adversarial_suite_is_documented() -> None:
    doc = Path("docs/codex/audit-integrity-adversarial-suite.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    review_packet = Path("docs/codex/v0.2-review-packet.md").read_text(encoding="utf-8")
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")

    for required in [
        "invalid payload JSON rows",
        "missing middle rows",
        "duplicate event lines",
        "malformed signature fields",
        "not immutable storage",
    ]:
        assert required in doc
    assert "audit-integrity-adversarial-suite.md" in readme
    assert "audit-integrity-adversarial-suite.md" in review_packet
    assert "audit-integrity-adversarial-suite.md" in reproduction_map
    assert "107 - Audit integrity adversarial suite | Done" in backlog
    assert "Task 107 adds" in matrix
    assert "docs/codex/audit-integrity-adversarial-suite.md" in review_docs.REVIEW_DOCS


def test_release_guardrail_expansion_is_documented_and_wired() -> None:
    doc = Path("docs/codex/release-guardrail-expansion.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    review_packet = Path("docs/codex/v0.2-review-packet.md").read_text(encoding="utf-8")
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")

    for required in [
        "required review/docs-site documents",
        "release-check",
        "review-candidate",
        "deferred shell, Docker, Kubernetes, or browser tool",
        "Tasks 101-112 are marked done",
        "Task 126 extends",
        "Tasks 113-151 done",
    ]:
        assert required in doc
    assert release_guardrails._check_review_docs_present() == []
    assert release_guardrails._check_release_targets() == []
    assert release_guardrails._check_deferred_tool_powers_absent_from_manifests() == []
    assert release_guardrails._check_v03_wave5_status() == []
    assert release_guardrails._check_v04_horizontal_gate_status() == []
    assert "release-guardrail-expansion.md" in readme
    assert "release-guardrail-expansion.md" in review_packet
    assert "release-guardrail-expansion.md" in reproduction_map
    assert "108 - Release guardrail expansion | Done" in backlog
    assert "126 - Release guardrail expansion v2 | Done" in backlog
    assert "Task 108 adds" in matrix
    assert "docs/codex/release-guardrail-expansion.md" in review_docs.REVIEW_DOCS


def test_evidence_contracts_define_versioning_policy() -> None:
    contracts = Path("docs/codex/evidence-contracts.md").read_text(encoding="utf-8")
    contract_index = json.loads(
        Path("docs/codex/evidence-contracts-v2.json").read_text(encoding="utf-8")
    )
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")

    for required in [
        "Contract Versioning",
        "v0.4-local-preview-evidence-contract-v2",
        "evidence-contracts-v2.json",
        'format_version: "1"',
        'version: "1"',
        "Stable v0.4 evidence fields",
        "Preview-only evidence fields",
        "requires a trusted local public key file",
        "new format version",
    ]:
        assert required in contracts
    assert contract_index["contract_version"] == "v0.4-local-preview-evidence-contract-v2"
    assert {contract["id"] for contract in contract_index["contracts"]} >= {
        "audit_event",
        "audit_jsonl_export",
        "signed_audit_export",
        "signed_manifest_lock",
        "release_evidence",
        "policy_decision_evidence",
        "approval_binding_evidence",
    }
    assert "Task 095 evidence-contract versioning" in matrix
    assert "SUB-001" in matrix
    assert "docs/codex/evidence-contracts-v2.json" in review_docs.REVIEW_DOCS
    assert evidence_contracts_check.validate_contract_index()["contract_version"] == (
        "v0.4-local-preview-evidence-contract-v2"
    )


def test_policy_parity_harness_is_documented_and_gated() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    doc = Path("docs/codex/policy-parity-harness.md").read_text(encoding="utf-8")

    assert "policy-parity:" in makefile
    assert "policy-parity" in makefile.partition("release-check:")[2]
    assert "make policy-parity" in readme
    assert "make policy-parity" in doc
    assert "policies/tests/parity.yaml" in doc
    assert "096 - Policy preview/runtime parity harness | Done" in backlog
    assert "Task 096 preview/runtime parity fixtures" in matrix
    assert "docs/codex/policy-parity-harness.md" in review_docs.REVIEW_DOCS


def test_opa_parity_decision_keeps_yaml_canonical_for_gates() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    release = Path("docs/codex/local-preview-release.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    doc = Path("docs/codex/opa-parity-decision.md").read_text(encoding="utf-8")

    for required in [
        "YAML remains the canonical local-preview policy engine",
        "OPA remains an optional sidecar/evidence prototype",
        "make policy-test",
        "make policy-parity",
        "not a semantic parity claim",
        "v0.4 Boundary Decision",
        "YAML remains the only canonical policy engine for release gates",
        "controlled OPA fixture/parity runner",
    ]:
        assert required in doc
    assert "opa-parity-decision.md" in readme
    assert "OPA Parity Decision" in release
    assert "097 - OPA parity decision point | Done" in backlog
    assert "134 - OPA boundary decision | Done" in backlog
    assert "Task 097 keeps YAML canonical" in matrix
    assert "docs/codex/opa-parity-decision.md" in review_docs.REVIEW_DOCS


def test_mcp_ingress_bypass_audit_is_documented() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    doc = Path("docs/codex/mcp-ingress-bypass-audit.md").read_text(encoding="utf-8")

    for required in [
        "Task 137 expands",
        "fixed local MCP principal",
        "fixed local MCP session",
        "MCP callers cannot spoof an admin principal",
        "MCP callers cannot provide their own session or request ID",
        "Unknown tools called through MCP are denied",
        "deny_source: mcp_exposure",
        "policy.evaluated",
        "remote MCP remains deferred",
    ]:
        assert required in doc
    assert "mcp-ingress-bypass-audit.md" in readme
    assert "098 - MCP ingress bypass audit | Done" in backlog
    assert "137 - MCP ingress bypass audit v2 | Done" in backlog
    assert "Task 098 tests fixed-principal audit evidence" in matrix
    assert "SUB-074" in matrix
    assert "docs/codex/mcp-ingress-bypass-audit.md" in review_docs.REVIEW_DOCS


def test_local_auth_boundary_is_documented() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    doc = Path("docs/codex/local-auth-boundary.md").read_text(encoding="utf-8")

    for required in [
        "Authorization: Bearer <token>",
        "server session state: disabled",
        "cookie authentication: disabled",
        "production identity: not implemented",
        "cookies do not authenticate admin endpoints",
    ]:
        assert required in doc
    assert "local-auth-boundary.md" in readme
    assert "138 - Local auth/session hardening within current boundary | Done" in backlog
    assert "Task 138 local bearer-token/session boundary documented and tested" in matrix
    assert "docs/codex/local-auth-boundary.md" in review_docs.REVIEW_DOCS


def test_review_console_assurance_is_documented() -> None:
    app = Path("apps/ui/src/App.tsx").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    doc = Path("docs/codex/review-console-assurance.md").read_text(encoding="utf-8")

    for required in [
        "approval scope hash",
        "Task 139 adds",
        "Task 140 tightens",
        "patch artifact",
        "tool manifest",
        "policy decision",
        "principal and scope",
        "policy reason",
        "/patch-apply-diagnostics",
        "warning banners",
        "rejected admin token shows a locked dashboard state",
        "failed export responses are parsed",
        "does not add repair",
        "review_summary",
    ]:
        assert required in doc
    for ui_marker in [
        "PatchApplyDiagnostics",
        "/patch-apply-diagnostics",
        "Patch Apply Diagnostics",
        "copyApprovalEvidence",
        "review_summary",
        "approval_scope_hash",
        "Patch Artifact",
        "Tool Manifest",
        "Policy Decision",
        "Principal and Scope",
        "apiErrorFromResponse",
        "Dashboard data is locked",
        "Console data is unavailable",
    ]:
        assert ui_marker in app
    assert "review-console-assurance.md" in readme
    assert "099 - Review-console approval evidence clarity | Done" in backlog
    assert "100 - Review-console failure-state and trust-status UX | Done" in backlog
    assert "139 - Review-console approval UX v3 | Done" in backlog
    assert "140 - Review-console failure and unauthorized states | Done" in backlog
    assert "Tasks 099-100 expose copyable approval binding evidence" in matrix
    assert "SUB-075" in matrix
    assert "docs/codex/review-console-assurance.md" in review_docs.REVIEW_DOCS


def test_negative_transcript_expansion_is_documented() -> None:
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    recipes = Path("docs/codex/negative-review-recipes.md").read_text(encoding="utf-8")

    for required in [
        "Hidden Sensitive Path Denial",
        "HTTP Credential URL Denial",
        "Manifest Lock Tamper Denial",
        "Policy Parity Mismatch Detection",
        "Patch Apply Ambiguous Diagnostics",
        "Signed Audit Export Tamper Denial",
    ]:
        assert required in recipes
    assert "101 - Negative transcript expansion | Done" in backlog
    assert "141 - Negative transcript expansion v2 | Done" in backlog
    assert "Task 101 expands observed transcripts" in matrix
    assert "Task 141 expanded observed denial transcripts" in matrix


def test_adversarial_corpus_framework_is_documented() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    doc = Path("docs/codex/adversarial-corpus-framework.md").read_text(encoding="utf-8")
    manifest = Path("tests/fixtures/adversarial_corpus_manifest.json").read_text(encoding="utf-8")

    for required in [
        "make adversarial-corpus-check",
        "http-canonicalization-v2",
        "filesystem-race-v2",
        "audit-integrity-v2",
        "negative-review-transcripts-v2",
        "not a fuzzing engine",
    ]:
        assert required in doc
    assert "adversarial-corpus-framework.md" in readme
    assert "142 - Adversarial corpus framework | Done" in backlog
    assert "Task 142 manifest-backed corpus index added" in matrix
    assert "docs/codex/adversarial-corpus-framework.md" in review_docs.REVIEW_DOCS
    assert "tests/fixtures/http_canonicalization_corpus.json" in manifest


def test_resource_limit_sanity_is_documented() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    doc = Path("docs/codex/resource-limit-sanity.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")

    for required in [
        "make resource-limit-check",
        "read byte limit",
        "patch byte limit",
        "HTTP response byte limit",
        "not production capacity planning",
    ]:
        assert required in doc
    assert "resource-limit-sanity.md" in readme
    assert "143 - Performance and resource-limit sanity | Done" in backlog
    assert "Task 143 local-preview resource-limit sanity gate added" in matrix
    assert "resource-limit-check:" in makefile
    assert (
        "adversarial-corpus-check resource-limit-check demo-scenario-pack "
        "evidence-contracts-check" in makefile
    )
    assert "docs/codex/resource-limit-sanity.md" in review_docs.REVIEW_DOCS


def test_ci_platform_plan_is_documented_without_broad_claims() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    doc = Path("docs/codex/ci-platform-plan.md").read_text(encoding="utf-8")

    for required in [
        "macOS and Linux local filesystems",
        "Windows and WSL remain unsupported/untested",
        "make release-check",
        "make filesystem-contract-check",
        "CI passing would mean",
        "not prove production security",
    ]:
        assert required in doc
    assert "ci-platform-plan.md" in readme
    assert "144 - CI and platform planning without broad claims | Done" in backlog
    assert "Task 144 CI/platform plan added without broad claims" in matrix
    assert "docs/codex/ci-platform-plan.md" in review_docs.REVIEW_DOCS


def test_redaction_evidence_boundary_is_documented() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    doc = Path("docs/codex/redaction-evidence-boundary.md").read_text(encoding="utf-8")
    evidence = Path("docs/codex/evidence-contracts.md").read_text(encoding="utf-8")

    for required in [
        "best-effort leak reduction",
        "not a security boundary",
        "make packet-redaction-scan",
        "redaction_applied",
        "redaction_count",
        "redaction_paths",
    ]:
        assert required in doc
    assert "redaction-evidence-boundary.md" in readme
    assert "redaction-evidence-boundary.md" in evidence
    assert "145 - Redaction evidence and leak-boundary clarity | Done" in backlog
    assert "Task 145 redaction evidence boundary clarified" in matrix
    assert "docs/codex/redaction-evidence-boundary.md" in review_docs.REVIEW_DOCS


def test_demo_scenario_pack_is_documented_and_wired() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    doc = Path("docs/codex/demo-scenario-pack-v2.md").read_text(encoding="utf-8")
    local_preview = Path("docs/codex/local-preview-release.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    for required in [
        "make demo-flow",
        "make negative-review-transcripts",
        "make signed-evidence-demo",
        "make review-candidate",
        "does not add new tool powers",
        "not production security software",
    ]:
        assert required in doc
    assert "demo-scenario-pack:" in makefile
    assert "demo-scenario-pack" in release_guardrails.REQUIRED_RELEASE_CHECK_FRAGMENTS
    assert "make demo-scenario-pack" in readme
    assert "demo-scenario-pack-v2.md" in local_preview
    assert "146 - Demo scenario pack v2 | Done" in backlog
    assert "Task 146 scenario pack maps" in matrix
    assert "docs/codex/demo-scenario-pack-v2.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/demo-scenario-pack-v2.md" in docs_site


def test_review_docs_index_is_documented_and_wired() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    doc = Path("docs/codex/review-docs-index.md").read_text(encoding="utf-8")
    local_preview = Path("docs/codex/local-preview-release.md").read_text(encoding="utf-8")
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    for required in [
        "Start Here",
        "Threat and Boundary",
        "Evidence and Gates",
        "Review Closure",
        "Reproduction and Packet Handoff",
        "v0.6 Preflight Transition Note",
        "Do not infer production readiness",
    ]:
        assert required in doc
    assert "review-docs-index.md" in readme
    assert "review-docs-index.md" in local_preview
    assert "review-docs-index.md" in reproduction_map
    assert "147 - Documentation information architecture cleanup | Done" in backlog
    assert "Task 147 review docs index added" in matrix
    assert "docs/codex/review-docs-index.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/review-docs-index.md" in docs_site


def test_v04_threat_model_refresh_is_documented_and_wired() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    doc = Path("docs/codex/v0.4-threat-model-refresh.md").read_text(encoding="utf-8")
    threat_model = Path("docs/codex/threat-model-and-non-goals.md").read_text(encoding="utf-8")
    obsidian = Path("docs/obsidian/04-threat-model.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    for required in [
        "Accepted Local-Preview Risks",
        "compromised local host",
        "not external notarization",
        "Windows or WSL",
        "Stop Conditions",
        "capability expansion",
    ]:
        assert required in doc
    assert "v0.4-threat-model-refresh.md" in readme
    assert "v0.4-threat-model-refresh.md" in threat_model
    assert "v0.4 Local-Preview Refresh" in obsidian
    assert "148 - v0.4 threat model refresh | Done" in backlog
    assert "Task 148 local-preview accepted risks refreshed" in matrix
    assert "docs/codex/v0.4-threat-model-refresh.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/v0.4-threat-model-refresh.md" in docs_site


def test_v04_review_packet_generator_is_documented_and_secret_free(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    doc = Path("docs/codex/v0.4-review-packet-generator.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["v04_review_packet.py", "--json"])
    result = v04_review_packet.main()
    output = capsys.readouterr().out
    payload = json.loads(output)

    assert result == 0
    assert payload["packet_version"] == "v0.4-review-candidate"
    assert payload["v04_milestone"]["completed_range"] == "113-151"
    assert "dev-admin-token-change-me" not in output
    assert "make v04-review-packet" in readme
    assert "v04-review-packet:" in makefile
    assert "v0.4-review-packet-generator.md" in doc
    assert "149 - v0.4 review packet generator | Done" in backlog
    assert "Task 149 packet generator added" in matrix
    assert "docs/codex/v0.4-review-packet-generator.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/v0.4-review-packet-generator.md" in docs_site


def test_external_review_intake_v2_is_documented_and_wired() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    doc = Path("docs/codex/external-review-intake-v2.md").read_text(encoding="utf-8")
    original = Path("docs/codex/external-review-intake-and-closure.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    for required in [
        "make reviewer-findings-check",
        "make review-findings-summary",
        "EXT-###",
        "Internal AI/subagent review cannot close external rows",
        "boundary decision",
    ]:
        assert required in doc
    assert "external-review-intake-v2.md" in readme
    assert "external-review-intake-v2.md" in original
    assert "150 - External review intake and closure workflow v2 | Done" in backlog
    assert "Task 150 intake workflow updated" in matrix
    assert "docs/codex/external-review-intake-v2.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/external-review-intake-v2.md" in docs_site


def test_v04_external_packet_and_capability_seed_are_documented() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    packet = Path("docs/codex/v0.4-review-packet.md").read_text(encoding="utf-8")
    prompt = Path("docs/codex/v0.4-external-review-prompt.md").read_text(encoding="utf-8")
    seed = Path("docs/codex/v0.4-capability-decision-seed.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    for required in [
        "make release-check",
        "make v04-review-packet",
        "make review-candidate",
        "does not unlock new tool powers",
    ]:
        assert required in packet
    assert "Do not treat v0.4 as production security software" in prompt
    assert "No new powerful tool class is approved" in seed
    assert "v0.4-review-packet.md" in readme
    assert "151 - v0.4 external review packet and capability decision seed | Done" in backlog
    assert "Task 151 external packet and capability seed added" in matrix
    for doc in [
        "docs/codex/v0.4-review-packet.md",
        "docs/codex/v0.4-external-review-prompt.md",
        "docs/codex/v0.4-capability-decision-seed.md",
    ]:
        assert doc in review_docs.REVIEW_DOCS
        assert doc in docs_site


def test_v05_roadmap_from_review_is_documented_and_scoped() -> None:
    manifest_doc = Path("docs/codex/v0.5-milestone-manifest.md").read_text(encoding="utf-8")
    manifest = json.loads(
        Path("docs/codex/v0.5-milestone-manifest.json").read_text(encoding="utf-8")
    )
    roadmap = Path("docs/codex/v0.5-roadmap-from-v0.4-review.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    task_ids = [milestone["id"] for milestone in manifest["milestones"]]
    assert task_ids == [f"{index:03d}" for index in range(152, 181)]
    assert manifest["completed_range"] == "152-180"
    assert manifest["planned_range"] == "none"
    assert manifest["runtime_boundary"] == "v0.1 local-preview"
    assert "shell execution" in manifest["deferred_boundaries"]
    assert "No task in this manifest may add new governed tool powers" in manifest_doc
    assert "Tasks 152-180" in roadmap
    assert "Task 151 as a review packet only" in roadmap
    assert "v0.5-milestone-manifest.md" in readme
    assert "152 - v0.5 roadmap from v0.4 review | Done" in backlog
    assert "Task 152 records GPT 5.5 Pro v0.4 feedback" in matrix
    for doc in [
        "docs/codex/v0.5-roadmap-from-v0.4-review.md",
        "docs/codex/v0.5-milestone-manifest.md",
        "docs/codex/v0.5-milestone-manifest.json",
    ]:
        assert doc in review_docs.REVIEW_DOCS
    assert "docs/codex/v0.5-roadmap-from-v0.4-review.md" in docs_site
    assert "docs/codex/v0.5-milestone-manifest.md" in docs_site


def test_capability_expansion_gate_reports_blocked_without_tool_drift() -> None:
    report = capability_expansion_gate.build_report(Path.cwd())
    doc = Path("docs/codex/capability-expansion-gate.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    assert report["hard_failures"] == []
    assert report["capability_expansion_allowed"] is False
    assert report["decision"] == "blocked"
    assert report["tool_count"] == 10
    assert "external_pending" in " ".join(report["blockers"])
    assert "make capability-expansion-gate" in readme
    assert "blocked result is healthy" in doc
    assert "153 - Capability expansion gate v2 | Done" in backlog
    assert "Task 153 adds an explicit blocked/allowed" in matrix
    assert "docs/codex/capability-expansion-gate.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/capability-expansion-gate.md" in docs_site


def test_tool_surface_invariant_gate_is_wired_and_valid() -> None:
    report = tool_surface_invariant_gate.build_report(Path.cwd())
    doc = Path("docs/codex/tool-surface-invariant-gate.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    assert report["valid"] is True
    assert report["failures"] == []
    assert report["tool_count"] == 10
    assert report["manifest_file_count"] == 10
    assert report["tool_names"] == tool_surface_invariant_gate.EXPECTED_TOOL_NAMES
    assert report["forbidden_marker_hits"] == []
    assert any(
        summary["name"] == "http.fetch" and summary["risk"] == "network"
        for summary in report["manifest_summaries"]
    )
    assert "make tool-surface-invariant-gate" in readme
    assert "single caller-controlled `url` field" in doc
    assert "154 - Tool-surface invariant gate v2 | Done" in backlog
    assert "Task 154 verifies the current ten-tool" in matrix
    assert "tool-surface-invariant-gate" in makefile.partition("release-check:")[2]
    assert "docs/codex/tool-surface-invariant-gate.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/tool-surface-invariant-gate.md" in docs_site


def test_evidence_confusion_gate_is_wired_and_valid() -> None:
    report = evidence_confusion_gate.build_report(Path.cwd())
    doc = Path("docs/codex/evidence-confusion-gate.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    assert report["valid"] is True
    assert report["failures"] == []
    assert report["overclaim_hits"] == []
    assert report["runtime_signing_required_by_default"] is False
    assert report["demo_evidence_is_non_production"] is True
    assert "make evidence-confusion-gate" in readme
    assert "not external notarization" in doc
    assert "155 - Evidence-confusion gate v2 | Done" in backlog
    assert "Task 155 verifies local signing evidence" in matrix
    assert "evidence-confusion-gate" in makefile.partition("release-check:")[2]
    assert "evidence-confusion-gate" in release_guardrails.REQUIRED_RELEASE_CHECK_FRAGMENTS
    assert "docs/codex/evidence-confusion-gate.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/evidence-confusion-gate.md" in docs_site


def test_external_review_closure_gate_is_wired_and_blocked_honestly() -> None:
    report = external_review_closure_gate.build_report(Path.cwd())
    doc = Path("docs/codex/external-review-closure-gate.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    assert report["valid"] is True
    assert report["hard_failures"] == []
    assert report["external_closure_complete"] is False
    assert report["pending_external_review_rows"]
    assert "external review rows still pending" in " ".join(report["blockers"])
    assert "make external-review-closure-gate" in readme
    assert "external_closure_complete" in doc
    assert "156 - External-review closure gate v2 | Done" in backlog
    assert "Task 156 verifies source-review closure" in matrix
    assert "external-review-closure-gate" in makefile.partition("release-check:")[2]
    assert "external-review-closure-gate" in release_guardrails.REQUIRED_RELEASE_CHECK_FRAGMENTS
    assert "docs/codex/external-review-closure-gate.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/external-review-closure-gate.md" in docs_site


def test_source_review_runbook_v2_is_documented() -> None:
    runbook = Path("docs/codex/source-review-runbook-v2.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    for required in [
        "make release-check",
        "make review-candidate",
        "make internal-review-packet",
        "make capability-expansion-gate",
        "make tool-surface-invariant-gate",
        "make evidence-confusion-gate",
        "make external-review-closure-gate",
        "Critical/high open findings stop autonomous implementation",
        "External rows may not be closed by internal review",
        "http-executor-contract.md",
    ]:
        assert required in runbook
    assert "http-fetch-executor-contract.md" not in runbook
    assert "source-review-runbook-v2.md" in readme
    assert "157 - Source review runbook v2 | Done" in backlog
    assert "Task 157 documents the repeatable source-review workflow" in matrix
    assert "docs/codex/source-review-runbook-v2.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/source-review-runbook-v2.md" in docs_site


def test_source_file_inspection_packet_maps_review_surfaces() -> None:
    packet = Path("docs/codex/source-file-inspection-packet.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    for required in [
        "Patch apply",
        "Filesystem reads",
        "HTTP fetch",
        "Signed audit export",
        "Manifest-lock signatures",
        "Policy preview/runtime parity",
        "MCP ingress",
        "Review console evidence",
        "Release/evidence automation",
        "PatchProposalService.apply_approved",
        "HttpFetchExecutor.fetch",
        "IthildinMcpAdapter.call_tool",
    ]:
        assert required in packet
    for path in [
        "apps/api/src/ithildin_api/patches.py",
        "apps/api/src/ithildin_api/read_tools.py",
        "apps/api/src/ithildin_api/http_tools.py",
        "apps/mcp-server/src/ithildin_mcp_server/server.py",
        "apps/ui/src/App.tsx",
    ]:
        assert path in packet
        assert Path(path).exists()
    assert "source-file-inspection-packet.md" in readme
    assert "158 - Source file inspection packet | Done" in backlog
    assert "Task 158 maps high-risk source files/functions" in matrix
    assert "docs/codex/source-file-inspection-packet.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/source-file-inspection-packet.md" in docs_site


def test_patch_apply_source_review_checklist_is_documented() -> None:
    checklist = Path("docs/codex/patch-apply-source-review-checklist.md").read_text(
        encoding="utf-8"
    )
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    for required in [
        "PatchProposalService.apply_approved",
        "ApprovalService.begin_execution",
        "GovernedToolCallService._execute_approved_patch",
        "stored-proposal-only",
        "Failure after replacement records",
        "uv run pytest tests/test_governed_tool_calls.py",
        "make release-check",
        "No shell/broad-write behavior",
    ]:
        if required == "No shell/broad-write behavior":
            assert "shell execution" in checklist and "broad writes" in checklist
        else:
            assert required in checklist
    assert "patch-apply-source-review-checklist.md" in readme
    assert "159 - Patch apply source review checklist | Done" in backlog
    assert "Task 159 adds a source checklist" in matrix
    assert "docs/codex/patch-apply-source-review-checklist.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/patch-apply-source-review-checklist.md" in docs_site


def test_filesystem_source_review_checklist_is_documented() -> None:
    checklist = Path("docs/codex/filesystem-source-review-checklist.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    for required in [
        "FilesystemReadTools.resolve_existing_path",
        "FilesystemReadTools._ensure_under_workspace",
        "FilesystemReadTools._ensure_not_sensitive",
        "FilesystemReadTools._ensure_not_hardlinked_file",
        "_reject_ambiguous_path_input",
        "PatchProposalService.create_proposal",
        "make filesystem-contract-check",
        "Windows/WSL remain unsupported/untested",
    ]:
        assert required in checklist
    assert "filesystem-source-review-checklist.md" in readme
    assert "160 - Filesystem source review checklist | Done" in backlog
    assert "Task 160 adds a source checklist" in matrix
    assert "docs/codex/filesystem-source-review-checklist.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/filesystem-source-review-checklist.md" in docs_site


def test_http_fetch_source_review_checklist_is_documented() -> None:
    checklist = Path("docs/codex/http-fetch-source-review-checklist.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    for required in [
        "HttpFetchExecutor.fetch",
        "_ensure_allowed_destination",
        "_validated_resolution",
        "parse_http_url",
        "_is_blocked_ip",
        "tests/fixtures/http_canonicalization_corpus.json",
        "Proxy environment variables are not inherited",
        "GET-only boundary",
    ]:
        assert required in checklist
    assert "http-fetch-source-review-checklist.md" in readme
    assert "161 - HTTP fetch source review checklist | Done" in backlog
    assert "Task 161 adds a source checklist" in matrix
    assert "docs/codex/http-fetch-source-review-checklist.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/http-fetch-source-review-checklist.md" in docs_site


def test_signed_evidence_source_review_checklist_is_documented() -> None:
    checklist = Path("docs/codex/signed-evidence-source-review-checklist.md").read_text(
        encoding="utf-8"
    )
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    for required in [
        "signed_audit_export_bundle",
        "verify_signed_audit_export_bundle",
        "verify_manifest_lock_signature",
        "signed_evidence_demo.py",
        "make signed-evidence-demo-verify",
        "make evidence-confusion-gate",
        "not external notarization",
        "official supply-chain signing",
    ]:
        assert required in checklist
    assert "signed-evidence-source-review-checklist.md" in readme
    assert "162 - Signed evidence source review checklist | Done" in backlog
    assert "Task 162 adds a source checklist" in matrix
    assert "docs/codex/signed-evidence-source-review-checklist.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/signed-evidence-source-review-checklist.md" in docs_site


def test_policy_parity_source_review_checklist_is_documented() -> None:
    checklist = Path("docs/codex/policy-parity-source-review-checklist.md").read_text(
        encoding="utf-8"
    )
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    for required in [
        "PolicyPreviewService.preview",
        "GovernedToolCallService.call_tool",
        "decision_evidence.py",
        "scripts/policy_parity.py",
        "make policy-test",
        "make policy-parity",
        "side-effect-free",
        "YAML remains canonical",
    ]:
        assert required in checklist
    assert "policy-parity-source-review-checklist.md" in readme
    assert "163 - Policy parity source review checklist | Done" in backlog
    assert "Task 163 adds a source checklist" in matrix
    assert "docs/codex/policy-parity-source-review-checklist.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/policy-parity-source-review-checklist.md" in docs_site


def test_mcp_ingress_source_review_checklist_is_documented() -> None:
    checklist = Path("docs/codex/mcp-ingress-source-review-checklist.md").read_text(
        encoding="utf-8"
    )
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    for required in [
        "IthildinMcpAdapter.list_tools",
        "IthildinMcpAdapter.call_tool",
        "GovernedToolCallService.call_tool",
        "stdio-only local ingress",
        "Caller-supplied principal/session spoofing",
        "tests/test_mcp_adapter.py",
        "tests/test_mcp_integration_flow.py",
    ]:
        assert required in checklist
    assert "mcp-ingress-source-review-checklist.md" in readme
    assert "164 - MCP ingress source review checklist | Done" in backlog
    assert "Task 164 adds a source checklist" in matrix
    assert "docs/codex/mcp-ingress-source-review-checklist.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/mcp-ingress-source-review-checklist.md" in docs_site


def test_review_console_source_review_checklist_is_documented() -> None:
    checklist = Path("docs/codex/review-console-source-review-checklist.md").read_text(
        encoding="utf-8"
    )
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    for required in [
        "apps/ui/src/App.tsx",
        "approval binding evidence display",
        'decided_by: "admin:local-ui"',
        "The UI does not add direct tool execution",
        "derived review verdict/checks/reasons",
        "npm run typecheck --prefix apps/ui",
        "npm run build --prefix apps/ui",
        "not custody or notarization",
    ]:
        assert required in checklist
    assert "review-console-source-review-checklist.md" in readme
    assert "165 - Review console source review checklist | Done" in backlog
    assert "Task 165 adds a source checklist" in matrix
    assert "docs/codex/review-console-source-review-checklist.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/review-console-source-review-checklist.md" in docs_site


def test_external_findings_intake_dry_run_is_wired() -> None:
    report = external_findings_intake_dry_run.run_dry_run()
    doc = Path("docs/codex/external-findings-intake-dry-run.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    assert report["valid"] is True
    assert report["validated_fixture_id"] == "EXT-900"
    assert report["open_high_fixture_rejected"] is True
    assert report["committed_findings_mutated"] is False
    assert "make external-findings-intake-dry-run" in readme
    assert "temporary `EXT-###` finding fixtures" in doc
    assert "166 - External findings intake dry run | Done" in backlog
    assert "Task 166 validates EXT finding intake rails" in matrix
    assert "external-findings-intake-dry-run" in makefile.partition("release-check:")[2]
    assert "external-findings-intake-dry-run" in release_guardrails.REQUIRED_RELEASE_CHECK_FRAGMENTS
    assert "docs/codex/external-findings-intake-dry-run.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/external-findings-intake-dry-run.md" in docs_site


def test_closure_matrix_evidence_sync_is_wired() -> None:
    report = closure_matrix_evidence_sync.build_report(Path.cwd())
    doc = Path("docs/codex/closure-matrix-evidence-sync.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    assert report["valid"] is True
    assert report["failures"] == []
    assert report["missing_done_task_refs"] == []
    assert "167" in report["done_task_ids"]
    assert "make closure-matrix-evidence-sync" in readme
    assert "every completed v0.5 task" in doc
    assert "167 - Closure matrix evidence sync | Done" in backlog
    assert "Task 167 verifies done v0.5 tasks" in matrix
    assert "closure-matrix-evidence-sync" in makefile.partition("release-check:")[2]
    assert "closure-matrix-evidence-sync" in release_guardrails.REQUIRED_RELEASE_CHECK_FRAGMENTS
    assert "docs/codex/closure-matrix-evidence-sync.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/closure-matrix-evidence-sync.md" in docs_site


def test_closure_matrix_evidence_sync_rejects_fixed_rows_with_pending_commit(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs/codex"
    docs_dir.mkdir(parents=True)
    docs_dir.joinpath("v0.5-milestone-manifest.json").write_text(
        json.dumps({"milestones": []}),
        encoding="utf-8",
    )
    docs_dir.joinpath("source-review-closure-matrix.md").write_text(
        "\n".join(
            [
                "# Matrix",
                "",
                "## v3 Closure State",
                "",
                "| Area | Internal status | External status | Highest open severity | "
                "Fixed commit | Verification command | Accepted/deferred risk link | "
                "Closure state |",
                "| --- | --- | --- | --- | --- | --- | --- | --- |",
                "| HTTP fetch | findings fixed internally | pending external review | none | "
                "pending | `make release-check` | none | external_pending |",
                "",
            ]
        ),
        encoding="utf-8",
    )

    report = closure_matrix_evidence_sync.build_report(tmp_path)

    assert report["valid"] is False
    assert "HTTP fetch records fixed internal findings with pending commit" in report["failures"]


def test_accepted_risk_register_is_wired_and_scoped() -> None:
    report = accepted_risk_register.build_report(Path.cwd())
    doc = Path("docs/codex/accepted-risk-register.md").read_text(encoding="utf-8")
    register = json.loads(
        Path("docs/codex/accepted-risk-register.json").read_text(encoding="utf-8")
    )
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    assert report["valid"] is True
    assert report["failures"] == []
    assert report["risk_count"] == 10
    assert report["capability_expansion_approved"] is False
    assert report["external_source_review_closed"] is False
    assert {risk["id"] for risk in register["risks"]} == {
        f"AR-{index:03d}" for index in range(1, 11)
    }
    assert all(
        risk["external_review_required_before_closure"] is True for risk in register["risks"]
    )
    assert "does not approve capability expansion" in doc
    assert "not production authorization" in doc
    assert "make accepted-risk-register-check" in readme
    assert "168 - Accepted risk register | Done" in backlog
    assert "Task 168 records accepted local-preview risks" in matrix
    assert "accepted-risk-register-check" in makefile.partition("release-check:")[2]
    assert "accepted-risk-register-check" in release_guardrails.REQUIRED_RELEASE_CHECK_FRAGMENTS
    assert "docs/codex/accepted-risk-register.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/accepted-risk-register.json" in review_docs.REVIEW_DOCS
    assert "docs/codex/accepted-risk-register.md" in docs_site


def test_capability_decision_report_is_wired_and_blocked() -> None:
    report = capability_decision_report.build_report(Path.cwd())
    doc = Path("docs/codex/capability-decision-report.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    assert report["valid"] is True
    assert report["decision"] == "blocked"
    assert report["capability_expansion_allowed"] is False
    assert report["tool_count"] == 10
    assert report["completed_range"] == "152-180"
    assert report["planned_range"] == "none"
    assert report["open_accepted_risks"] == 10
    assert report["external_closure_complete"] is False
    assert "does not approve new governed tool powers" in doc
    assert "make capability-decision-report" in readme
    assert "169 - Capability decision report generator | Done" in backlog
    assert "Task 169 summarizes capability go/no-go evidence" in matrix
    assert "capability-decision-report" in makefile.partition("release-check:")[2]
    assert "capability-decision-report" in release_guardrails.REQUIRED_RELEASE_CHECK_FRAGMENTS
    assert "docs/codex/capability-decision-report.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/capability-decision-report.md" in docs_site


def test_no_new_powers_guardrail_is_wired_and_preserves_boundary() -> None:
    report = no_new_powers_guardrail.build_report(Path.cwd())
    doc = Path("docs/codex/no-new-powers-guardrail.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    assert report["valid"] is True
    assert report["failures"] == []
    assert report["tool_count"] == 10
    assert report["new_power_classes_allowed"] is False
    assert report["deferred_boundaries_unchanged"] is True
    assert report["tool_names"] == [
        "fs.list",
        "fs.patch.apply",
        "fs.patch.propose",
        "fs.read",
        "fs.search",
        "fs.stat",
        "git.diff",
        "git.log",
        "git.status",
        "http.fetch",
    ]
    assert "does not approve new powers" in doc
    assert "make no-new-powers-guardrail" in readme
    assert "170 - No-new-powers release guardrail v2 | Done" in backlog
    assert "Task 170 validates manifests and boundaries" in matrix
    assert "no-new-powers-guardrail" in makefile.partition("release-check:")[2]
    assert "no-new-powers-guardrail" in release_guardrails.REQUIRED_RELEASE_CHECK_FRAGMENTS
    assert "docs/codex/no-new-powers-guardrail.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/no-new-powers-guardrail.md" in docs_site


def test_source_review_transcript_packet_is_wired() -> None:
    report = source_review_transcript_packet.build_report(Path.cwd())
    doc = Path("docs/codex/source-review-transcript-packet.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    assert report["valid"] is True
    assert report["failures"] == []
    assert report["doc_count"] == len(source_review_transcript_packet.REQUIRED_PACKET_DOCS)
    assert report["external_review_closed"] is False
    assert report["runtime_behavior_changed"] is False
    assert all(str(item["sha256"]).startswith("sha256:") for item in report["docs"])
    assert "does not close external review" in doc
    assert "make source-review-transcript-packet" in readme
    assert "171 - Source review transcript packet | Done" in backlog
    assert "Task 171 generates transcript skeletons" in matrix
    assert "source-review-transcript-packet:" in makefile
    assert "docs/codex/source-review-transcript-packet.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/source-review-transcript-packet.md" in docs_site


def test_reviewer_artifact_manifest_is_wired() -> None:
    report = reviewer_artifact_manifest.build_manifest(Path.cwd())
    doc = Path("docs/codex/reviewer-artifact-manifest-v2.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    assert report["valid"] is True
    assert report["failures"] == []
    assert report["runtime_boundary"] == "v0.1 local-preview"
    assert report["committed_review_doc_count"] == len(review_docs.REVIEW_DOCS)
    assert "make review-candidate" not in report["does_not_prove"]
    assert "external/source review closure" in report["does_not_prove"]
    assert "make reviewer-artifact-manifest" in readme
    assert "172 - Reviewer artifact manifest v2 | Done" in backlog
    assert "Task 172 generates a v0.5 artifact inventory" in matrix
    assert "reviewer-artifact-manifest:" in makefile
    assert "does not close external/source review" in doc
    assert "docs/codex/reviewer-artifact-manifest-v2.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/reviewer-artifact-manifest-v2.md" in docs_site


def test_external_response_template_v2_is_wired() -> None:
    report = external_response_template_check.build_report(Path.cwd())
    doc = Path("docs/codex/external-review-response-intake-template-v2.md").read_text(
        encoding="utf-8"
    )
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    assert report["valid"] is True
    assert report["failures"] == []
    assert report["mutates_findings"] is False
    assert report["closes_external_review"] is False
    assert "Finding Extraction Table" in doc
    assert "EXT-###" in doc
    assert "make external-response-template-check" in readme
    assert "173 - External review response intake template v2 | Done" in backlog
    assert "Task 173 adds a v2 template" in matrix
    assert "external-response-template-check:" in makefile
    assert "docs/codex/external-review-response-intake-template-v2.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/external-review-response-intake-template-v2.md" in docs_site


def test_review_packet_source_pointers_are_wired() -> None:
    report = review_packet_source_pointers.build_report(Path.cwd())
    doc = Path("docs/codex/review-packet-source-pointers.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    assert report["valid"] is True
    assert report["failures"] == []
    assert report["area_count"] == 7
    assert report["pointer_count"] >= 12
    assert report["runtime_behavior_changed"] is False
    assert "apps/api/src/ithildin_api/patches.py" in doc
    assert "apps/api/src/ithildin_api/http_tools.py" in doc
    assert "make review-packet-source-pointers" in readme
    assert "174 - Review packet source pointers | Done" in backlog
    assert "Task 174 maps review packet claims" in matrix
    assert "review-packet-source-pointers:" in makefile
    assert "docs/codex/review-packet-source-pointers.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/review-packet-source-pointers.md" in docs_site


def test_v05_threat_model_delta_is_wired_and_scoped() -> None:
    report = v05_threat_model_delta_check.build_report(Path.cwd())
    doc = Path("docs/codex/v0.5-threat-model-delta.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    assert report["valid"] is True
    assert report["failures"] == []
    assert report["runtime_boundary_changed"] is False
    assert report["new_powers_added"] is False
    assert report["external_review_closed"] is False
    assert "No new governed tool powers" in doc
    assert "v0.5-threat-model-delta.md" in readme
    assert "175 - v0.5 threat model delta | Done" in backlog
    assert "Task 175 records what changed" in matrix
    assert "v05-threat-model-delta-check" in makefile.partition("release-check:")[2]
    assert "v05-threat-model-delta-check" in release_guardrails.REQUIRED_RELEASE_CHECK_FRAGMENTS
    assert "docs/codex/v0.5-threat-model-delta.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/v0.5-threat-model-delta.md" in docs_site


def test_v05_review_candidate_command_is_wired() -> None:
    doc = Path("docs/codex/v0.5-review-candidate-command.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")
    target = re.search(r"^v05-review-candidate:\n(?P<body>(?:\t.*\n)+)", makefile, re.MULTILINE)

    assert target is not None
    body = target.group("body")
    expected_commands = [
        "$(MAKE) review-candidate",
        "$(MAKE) v05-threat-model-delta-check",
        "$(MAKE) review-packet-source-pointers",
        "$(MAKE) external-response-template-check",
        "$(MAKE) source-review-transcript-packet",
        "$(MAKE) reviewer-artifact-manifest",
    ]
    positions = [body.index(command) for command in expected_commands]
    assert positions == sorted(positions)
    assert "does not approve capability expansion" in doc
    assert "make v05-review-candidate" in readme
    assert "176 - v0.5 review candidate command | Done" in backlog
    assert "Task 176 adds a one-command" in matrix
    assert "docs/codex/v0.5-review-candidate-command.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/v0.5-review-candidate-command.md" in docs_site


def test_v05_consolidated_packet_update_is_wired() -> None:
    doc = Path("docs/codex/v0.5-consolidated-packet-update.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")
    consolidated = Path("scripts/consolidate_review_packet.py").read_text(encoding="utf-8")

    assert "v0.6 Review-Closure Packet" in consolidated
    assert "v0.5 Roadmap From v0.4 Review" in consolidated
    assert "Review Packet Source Pointers" in consolidated
    assert "does not close external review" in doc
    assert "v0.5-milestone-manifest.md" in readme
    assert "177 - v0.5 consolidated packet update | Done" in backlog
    assert "Task 177 adds v0.5 review-closure artifacts" in matrix
    assert "docs/codex/v0.5-consolidated-packet-update.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/v0.5-consolidated-packet-update.md" in docs_site


def test_v06_closure_handoff_docs_are_wired() -> None:
    handoff = Path("docs/codex/v0.6-closure-handoff.md").read_text(encoding="utf-8")
    prompt = Path("docs/codex/v0.6-gpt-55-pro-handoff-prompt.md").read_text(
        encoding="utf-8"
    )
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    manifest = Path("docs/codex/v0.6-milestone-manifest.md").read_text(
        encoding="utf-8"
    )
    review_index = Path("docs/codex/review-docs-index.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")
    consolidated = Path("scripts/consolidate_review_packet.py").read_text(
        encoding="utf-8"
    )

    assert "SUB-001" in handoff
    assert "SUB-077" in handoff
    assert "v0.6 external/source-review handoff" in prompt
    assert "v0.6-closure-handoff.md" in readme
    assert "v0.6-gpt-55-pro-handoff-prompt.md" in readme
    assert "Internally remediated" in backlog
    assert "Internal proxy findings SUB-040 through SUB-047 fixed internally" in manifest
    assert "Internal proxy findings SUB-048 through SUB-063 fixed internally" in manifest
    assert "Internal proxy findings SUB-064 through SUB-073 fixed internally" in manifest
    assert "Internal proxy finding SUB-074 fixed internally" in manifest
    assert "Internal proxy finding SUB-075 fixed internally" in manifest
    assert "Internal proxy findings SUB-076 through SUB-077 fixed internally" in manifest
    assert "v0.6 Closure Handoff" in review_index
    assert "docs/codex/v0.6-closure-handoff.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/v0.6-gpt-55-pro-handoff-prompt.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/v0.6-closure-handoff.md" in docs_site
    assert "v0.6 GPT 5.5 Pro Handoff Prompt" in consolidated


def test_v05_external_review_prompt_is_wired() -> None:
    prompt = Path("docs/codex/v0.5-external-review-prompt.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")
    consolidated = Path("scripts/consolidate_review_packet.py").read_text(encoding="utf-8")

    for required in [
        "Overall judgment",
        "Capability expansion go/no-go opinion",
        "Do-not-add-yet list",
        "distinguish packet/documentation risk from implementation risk",
    ]:
        assert required in prompt
    assert "v0.5-external-review-prompt.md" in readme or "v0.5-milestone-manifest.md" in readme
    assert "178 - v0.5 external review prompt | Done" in backlog
    assert "Task 178 adds the v0.5 external review prompt" in matrix
    assert "docs/codex/v0.5-external-review-prompt.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/v0.5-external-review-prompt.md" in docs_site
    assert "v0.5 External Review Prompt" in consolidated


def test_v05_boundary_decision_draft_is_wired_and_blocked() -> None:
    report = v05_boundary_decision_draft_check.build_report(Path.cwd())
    doc = Path("docs/codex/v0.5-boundary-decision-draft.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    assert report["valid"] is True
    assert report["failures"] == []
    assert report["external_handoff_go"] is True
    assert report["capability_expansion_go"] is False
    assert report["broader_distribution_go"] is False
    assert "Decision draft: no-go for capability expansion" in doc
    assert "v0.5-milestone-manifest.md" in readme
    assert "179 - v0.5 boundary decision draft | Done" in backlog
    assert "Task 179 records go for external handoff" in matrix
    assert "v05-boundary-decision-draft-check" in makefile.partition("release-check:")[2]
    assert (
        "v05-boundary-decision-draft-check" in release_guardrails.REQUIRED_RELEASE_CHECK_FRAGMENTS
    )
    assert "docs/codex/v0.5-boundary-decision-draft.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/v0.5-boundary-decision-draft.md" in docs_site


def test_v05_handoff_packet_is_wired_and_blocked() -> None:
    report = v05_handoff_packet_check.build_report(Path.cwd())
    doc = Path("docs/codex/v0.5-handoff-packet.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    assert report["valid"] is True
    assert report["failures"] == []
    assert report["external_handoff_go"] is True
    assert report["capability_expansion_go"] is False
    assert report["broader_distribution_go"] is False
    assert report["tasks_complete"] is True
    assert "Tasks 152-180 are complete" in doc
    assert "make v05-review-candidate" in doc
    assert "v0.5-handoff-packet.md" in readme
    assert "180 - v0.5 handoff packet and go/no-go seed | Done" in backlog
    assert "Task 180 records go/no-go seed" in matrix
    assert "v05-handoff-packet-check" in makefile.partition("release-check:")[2]
    assert "v05-handoff-packet-check" in release_guardrails.REQUIRED_RELEASE_CHECK_FRAGMENTS
    assert "docs/codex/v0.5-handoff-packet.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/v0.5-handoff-packet.md" in docs_site


def test_v06_preflight_transition_note_is_wired() -> None:
    doc = Path("docs/codex/v0.6-preflight-transition.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    index = Path("docs/codex/review-docs-index.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    for required in [
        "2b6911715bffe0e2f967a25a70c742dc0ee5346d",
        "Go for v0.6 Wave 1 external-review setup and dispatch work",
        "No-go for capability expansion",
        "Task 181 should turn this transition note into a formal v0.6 boundary charter",
    ]:
        assert required in doc
    assert "v0.6-preflight-transition.md" in readme
    assert "v0.6-preflight-transition.md" in index
    assert "docs/codex/v0.6-preflight-transition.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/v0.6-preflight-transition.md" in docs_site


def test_v06_boundary_charter_and_manifest_are_wired() -> None:
    charter = Path("docs/codex/v0.6-boundary-charter.md").read_text(encoding="utf-8")
    manifest_doc = Path("docs/codex/v0.6-milestone-manifest.md").read_text(encoding="utf-8")
    manifest = json.loads(
        Path("docs/codex/v0.6-milestone-manifest.json").read_text(encoding="utf-8")
    )
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    index = Path("docs/codex/review-docs-index.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    task_ids = [milestone["id"] for milestone in manifest["milestones"]]
    assert task_ids == [f"{index:03d}" for index in range(181, 216)]
    assert manifest["runtime_boundary"] == "v0.1 local-preview"
    assert manifest["completed_range"] == "181-184 plus internal remediation through SUB-077"
    assert manifest["planned_range"] == "external review and post-review closure remain pending"
    assert manifest["capability_expansion_allowed"] is False
    assert manifest["broader_distribution_allowed"] is False
    for required in [
        "v0.6 is an external/source-review execution and closure wave",
        "No v0.6 task may add or approve",
        "external handoff: go",
        "capability expansion: no-go",
        "broader public/security-product positioning: no-go",
        "critical/high external finding appears",
    ]:
        assert required in charter
    assert "No task in this manifest may add new governed tool powers" in manifest_doc
    assert "181 - v0.6 boundary charter and freeze | Done" in backlog
    assert "Task 181 freezes v0.6" in matrix
    assert "v0.6-boundary-charter.md" in readme
    assert "v0.6-milestone-manifest.md" in readme
    assert "v0.6 Boundary Charter" in index
    for doc in [
        "docs/codex/v0.6-boundary-charter.md",
        "docs/codex/v0.6-milestone-manifest.md",
        "docs/codex/v0.6-milestone-manifest.json",
    ]:
        assert doc in review_docs.REVIEW_DOCS
    assert "docs/codex/v0.6-boundary-charter.md" in docs_site
    assert "docs/codex/v0.6-milestone-manifest.md" in docs_site


def test_v06_external_review_assignment_matrix_is_wired() -> None:
    doc = Path("docs/codex/v0.6-external-review-assignment-matrix.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    index = Path("docs/codex/review-docs-index.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    for required in [
        "This matrix turns the external-pending rows",
        "Patch apply",
        "Filesystem/platform",
        "HTTP fetch",
        "Audit/signed evidence",
        "Policy/registry",
        "MCP ingress",
        "Review console/admin boundary",
        "Release automation",
        "packet-only review may comment",
        "`source-level` or `packet-and-source` review may support implementation-row closure",
        "`docs-only` review may support wording/navigation rows only",
        "does not close any row",
    ]:
        assert required in doc
    assert doc.count("| not started |") >= 52
    assert "v0.6-external-review-assignment-matrix.md" in readme
    assert "182 - External reviewer assignment matrix | Done" in backlog
    assert "Task 182 maps external-pending rows" in matrix
    assert "v0.6 External Review Assignment Matrix" in index
    assert "docs/codex/v0.6-external-review-assignment-matrix.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/v0.6-external-review-assignment-matrix.md" in docs_site


def test_v06_external_review_dispatch_packets_are_wired(tmp_path: Path) -> None:
    summary = external_review_dispatch_packets.build_dispatch_packets(
        Path.cwd(),
        tmp_path / "dispatch",
    )
    doc = Path("docs/codex/v0.6-external-review-dispatch-packets.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    index = Path("docs/codex/review-docs-index.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    assert summary["packet_count"] == 8
    paths = {artifact["path"] for artifact in summary["packets"]}
    for expected in [
        "INDEX.md",
        "patch-apply.md",
        "filesystem.md",
        "http-fetch.md",
        "signed-evidence.md",
        "policy-registry.md",
        "mcp-ingress.md",
        "review-console.md",
        "release-automation.md",
    ]:
        assert expected in paths
    assert all(str(artifact["sha256"]).startswith("sha256:") for artifact in summary["packets"])
    manifest = json.loads(Path(summary["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["packet_type"] == "ithildin.v0.6.external_review_dispatch_packets"
    assert "production readiness" in manifest["does_not_prove"]
    assert all(
        str(artifact.get("payload_sha256", "sha256:")).startswith("sha256:")
        for artifact in manifest["packets"]
        if artifact["path"] != "INDEX.md"
    )
    dispatch_root = Path(summary["output_root"])
    for packet in manifest["packets"]:
        if packet["path"] == "INDEX.md":
            continue
        packet_text = dispatch_root.joinpath(packet["path"]).read_text(encoding="utf-8")
        assert "Dispatch packet payload SHA-256" in packet_text
        assert "The whole-file artifact SHA-256 is recorded" in packet_text
        assert "Required minimum commands:" in packet_text
        assert "- `make release-check`" in packet_text
        assert "## Source Access Closure Rule" in packet_text
    index_text = dispatch_root.joinpath("INDEX.md").read_text(encoding="utf-8")
    assert (
        "historical note: some generated bundle paths still contain v0.2/v0.5 names" in index_text
    )
    http_packet = dispatch_root.joinpath("http-fetch.md").read_text(encoding="utf-8")
    for finding_id in [
        "SUB-001",
        "SUB-007",
        "SUB-008",
        "SUB-009",
        "SUB-040",
        "SUB-041",
        "SUB-042",
        "SUB-043",
        "SUB-044",
        "SUB-045",
        "SUB-046",
        "SUB-047",
    ]:
        assert finding_id in http_packet
    signed_packet = dispatch_root.joinpath("signed-evidence.md").read_text(encoding="utf-8")
    for finding_id in [
        "SUB-010",
        "SUB-011",
        "SUB-012",
        "SUB-013",
        "SUB-014",
        "SUB-048",
        "SUB-049",
        "SUB-050",
        "SUB-051",
        "SUB-052",
        "SUB-053",
        "SUB-054",
        "SUB-055",
        "SUB-056",
        "SUB-057",
        "SUB-058",
        "SUB-059",
        "SUB-060",
        "SUB-061",
    ]:
        assert finding_id in signed_packet
    release_packet_text = dispatch_root.joinpath("release-automation.md").read_text(
        encoding="utf-8"
    )
    for required in [
        "make release-evidence",
        "make release-evidence-validate",
        "make release-evidence-gate",
        "make packet-redaction-scan",
        "scripts/release_evidence.py",
        "scripts/review_packet_bundle.py",
        "scripts/consolidate_review_packet.py",
        "scripts/review_packet_diff.py",
        "scripts/packet_redaction_scan.py",
        "scripts/external_response_normalize.py",
        "scripts/capability_decision_report.py",
        "tests/test_release_readiness.py",
        "docs/codex/release-evidence-schema.md",
        "docs/codex/review-packet-diff.md",
        "docs/codex/packet-redaction-scanner.md",
        "docs/codex/v0.6-external-response-normalization.md",
        "SUB-022",
        "SUB-023",
        "SUB-024",
        "SUB-025",
        "SUB-026",
        "SUB-054",
        "SUB-060",
        "SUB-061",
        "SUB-062",
        "SUB-063",
        "SUB-076",
        "SUB-077",
        "make review-candidate",
    ]:
        assert required in release_packet_text
    policy_packet = dispatch_root.joinpath("policy-registry.md").read_text(encoding="utf-8")
    for finding_id in [
        "SUB-015",
        "SUB-016",
        "SUB-017",
        "SUB-064",
        "SUB-065",
        "SUB-066",
        "SUB-067",
        "SUB-068",
        "SUB-069",
        "SUB-070",
        "SUB-071",
        "SUB-072",
        "SUB-073",
    ]:
        assert finding_id in policy_packet
    for required in [
        "apps/api/src/ithildin_api/tool_calls.py",
        "apps/api/src/ithildin_api/schema_validation.py",
        "apps/api/src/ithildin_api/yaml_utils.py",
        "tests/test_policy_parity.py",
        "tests/test_workspaces.py",
        "make policy-test",
        "make policy-parity",
        "tests/test_policy_parity.py tests/test_policy_test_harness.py",
    ]:
        assert required in policy_packet
    mcp_packet = dispatch_root.joinpath("mcp-ingress.md").read_text(encoding="utf-8")
    for finding_id in ["SUB-018", "SUB-074"]:
        assert finding_id in mcp_packet
    for required in [
        "apps/mcp-server/src/ithildin_mcp_server/server.py",
        "apps/api/src/ithildin_api/tool_calls.py",
        "tests/test_mcp_adapter.py",
        "tests/test_mcp_integration_flow.py",
        "tests/test_governed_tool_calls.py",
        (
            "uv run pytest tests/test_mcp_adapter.py tests/test_mcp_integration_flow.py "
            "tests/test_governed_tool_calls.py -q"
        ),
    ]:
        assert required in mcp_packet
    review_console_packet = dispatch_root.joinpath("review-console.md").read_text(
        encoding="utf-8"
    )
    for finding_id in ["SUB-019", "SUB-020", "SUB-021", "SUB-075"]:
        assert finding_id in review_console_packet
    for required in [
        "apps/ui/src/App.tsx",
        "apps/api/src/ithildin_api/app.py",
        "apps/api/src/ithildin_api/patches.py",
        "tests/test_api_service.py",
        "tests/test_release_readiness.py",
        "npm run build --prefix apps/ui",
        "test_approval_review_endpoint_reports_binding_checks",
        "test_approval_mutation_routes_reject_body_decision_mismatch",
    ]:
        assert required in review_console_packet
    for required in [
        "make v06-review-dispatch-packets",
        "dispatch-packet-hashes.json",
        "does not close external review rows",
        "EXT-###",
        "source-access closure rule",
        "Every focused packet ends its expected-command list with `make release-check`",
    ]:
        assert required in doc
    assert "make v06-review-dispatch-packets" in readme
    assert "v06-review-dispatch-packets:" in makefile
    assert "183 - External review packet dispatch set | Done" in backlog
    assert "Task 183 generates focused packet slices" in matrix
    assert "v0.6 External Review Dispatch Packets" in index
    assert "docs/codex/v0.6-external-review-dispatch-packets.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/v0.6-external-review-dispatch-packets.md" in docs_site


def test_v06_patch_apply_external_review_packet_is_wired(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path
    for marker in [
        "pyproject.toml",
        "Makefile",
        "apps/api",
        "apps/mcp-server",
        "tool-manifests.lock.json",
    ]:
        path = repo_root / marker
        if "." in Path(marker).name:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("marker\n", encoding="utf-8")
        else:
            path.mkdir(parents=True, exist_ok=True)
    for relative in (
        patch_apply_external_review_packet.SOURCE_FILES
        + patch_apply_external_review_packet.TEST_FILES
        + patch_apply_external_review_packet.CONTRACT_DOCS
    ):
        path = repo_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {relative.name}\n", encoding="utf-8")

    def fake_build_dispatch_packets(repo_root: Path, output_root: Path) -> dict[str, object]:
        output_root.mkdir(parents=True)
        output_root.joinpath("patch-apply.md").write_text("# Patch Apply\n", encoding="utf-8")
        manifest: dict[str, object] = {
            "packets": [
                {
                    "path": "patch-apply.md",
                    "sha256": "sha256:" + ("1" * 64),
                    "payload_sha256": "sha256:" + ("2" * 64),
                    "bytes": 14,
                }
            ]
        }
        output_root.joinpath("dispatch-packet-hashes.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )
        return manifest

    monkeypatch.setattr(
        patch_apply_external_review_packet,
        "_build_dispatch_packets",
        fake_build_dispatch_packets,
    )
    monkeypatch.setattr(
        patch_apply_external_review_packet,
        "_git",
        lambda repo_root, args: "abcdef1234567890"
        if args == ["rev-parse", "HEAD"]
        else "",
    )

    output_dir = patch_apply_external_review_packet.build_packet(
        repo_root=repo_root,
        output_dir=repo_root / "var/review-packets/v0.6/patch-apply-external-review",
    )

    assert output_dir.joinpath("00_PATCH_APPLY_EXTERNAL_REVIEW_INDEX.md").exists()
    assert output_dir.joinpath("01_PATCH_APPLY_EXTERNAL_REVIEW_PROMPT.md").exists()
    assert output_dir.joinpath("03_PATCH_APPLY_SOURCE_BUNDLE.md").exists()
    assert output_dir.joinpath("patch-apply-review-artifact-hashes.json").exists()
    index = output_dir.joinpath("00_PATCH_APPLY_EXTERNAL_REVIEW_INDEX.md").read_text(
        encoding="utf-8"
    )
    assert "supersedes the earlier generic v0.6 dispatch entry" in index
    assert "intentionally excludes itself" in index
    prompt = output_dir.joinpath("01_PATCH_APPLY_EXTERNAL_REVIEW_PROMPT.md").read_text(
        encoding="utf-8"
    )
    assert "EXT-PA-###" in prompt
    assert "sha256:" + ("1" * 64) in prompt
    intake = output_dir.joinpath("06_PATCH_APPLY_INTAKE_COMMANDS.md").read_text(
        encoding="utf-8"
    )
    assert "--area \"patch-apply\"" in intake
    assert "normalized-response.json" in intake
    assert "make reviewer-findings-check" in intake
    assert "make review-findings-summary" in intake
    assert "make external-review-closure-gate" in intake
    assert "make release-check" in intake
    hashes = json.loads(
        output_dir.joinpath("patch-apply-review-artifact-hashes.json").read_text(
            encoding="utf-8"
        )
    )
    assert {entry["path"] for entry in hashes} == {
        "00_PATCH_APPLY_EXTERNAL_REVIEW_INDEX.md",
        "01_PATCH_APPLY_EXTERNAL_REVIEW_PROMPT.md",
        "02_PATCH_APPLY_DISPATCH_PACKET.md",
        "03_PATCH_APPLY_SOURCE_BUNDLE.md",
        "04_PATCH_APPLY_TESTS_BUNDLE.md",
        "05_PATCH_APPLY_CONTRACTS_BUNDLE.md",
        "06_PATCH_APPLY_INTAKE_COMMANDS.md",
    }
    assert "patch-apply-review-artifact-hashes.json" not in {
        entry["path"] for entry in hashes
    }

    doc = Path("docs/codex/v0.6-patch-apply-external-review-execution.md").read_text(
        encoding="utf-8"
    )
    readme = Path("README.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    manifest = Path("docs/codex/v0.6-milestone-manifest.md").read_text(
        encoding="utf-8"
    )
    index = Path("docs/codex/review-docs-index.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")
    assert "make v06-patch-apply-review-packet" in doc
    assert "EXT-PA-###" in doc
    assert "make v06-patch-apply-review-packet" in readme
    assert "v06-patch-apply-review-packet:" in makefile
    assert "185 - Patch apply external review execution packet" in backlog
    assert "Source review received; EXT-PA findings remediated" in manifest
    assert "v0.6 Patch Apply External Review Execution" in index
    assert (
        "docs/codex/v0.6-patch-apply-external-review-execution.md"
        in review_docs.REVIEW_DOCS
    )
    assert "docs/codex/v0.6-patch-apply-external-review-execution.md" in docs_site

    dispatch_area = next(
        area
        for area in external_review_dispatch_packets.DISPATCH_AREAS
        if area.slug == "patch-apply"
    )
    assert any(
        "tests/test_security_regressions.py" in command
        for command in dispatch_area.commands
    )
    assert dispatch_area.finding_namespace == "EXT-PA-###"


def test_v06_external_response_normalization_is_wired() -> None:
    finding_header = (
        "| Finding ID | Severity | Area | Affected files/functions | "
        "Blocking status | Disposition | Recommended fix |"
    )
    finding_row = (
        "| EXT-001 | medium | http-fetch | apps/api/src/ithildin_api/http_tools.py | "
        "should-fix | open | add reviewer-requested regression |"
    )
    raw_response = "\n".join(
        [
            "# Review",
            "",
            finding_header,
            "| --- | --- | --- | --- | --- | --- | --- |",
            finding_row,
        ]
    )
    normalized = external_response_normalize.normalize_response(
        raw_response,
        reviewer="GPT 5.5 Pro",
        reviewer_type="external-model",
        source_access="source-level",
        reviewed_commit="abcdef1234567890",
        reviewed_packet_hash="sha256:" + "0" * 64,
        area="http-fetch",
    )
    doc = Path("docs/codex/v0.6-external-response-normalization.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")
    index = Path("docs/codex/review-docs-index.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    assert normalized["finding_count"] == 1
    assert normalized["findings"][0]["finding_id"] == "EXT-001"
    assert normalized["can_close_source_rows"] is True
    assert normalized["mutates_findings"] is False
    assert normalized["closes_external_review"] is False
    for required in [
        "source-level",
        "reviewed packet hash",
        "mutates_findings: false",
        "closes_external_review: false",
        "Secret-like markers are rejected",
    ]:
        assert required in doc
    assert "make external-response-normalize FILE=..." in readme
    assert "external-response-normalize:" in makefile
    assert "184 - External response normalization | Done" in backlog
    assert "Task 184 normalizes raw external responses" in matrix
    assert "v0.6 External Response Normalization" in index
    assert "docs/codex/v0.6-external-response-normalization.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/v0.6-external-response-normalization.md" in docs_site


def test_v06_lane_status_board_is_generated_and_wired() -> None:
    board = v06_lane_status.build_lane_status(Path.cwd())
    doc = Path("docs/codex/v0.6-lane-status-board.md").read_text(encoding="utf-8")
    payload = json.loads(
        Path("docs/codex/v0.6-lane-status-board.json").read_text(encoding="utf-8")
    )
    readme = Path("README.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    manifest = Path("docs/codex/v0.6-milestone-manifest.md").read_text(
        encoding="utf-8"
    )
    index = Path("docs/codex/review-docs-index.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    assert json.loads(json.dumps(board)) == payload
    assert board["summary"]["lane_count"] == 8
    assert board["summary"]["external_review_received"] == 1
    assert board["summary"]["external_review_closed"] == 0
    assert board["summary"]["critical_high_open_count"] == 0
    patch_lane = next(lane for lane in board["lanes"] if lane["slug"] == "patch-apply")
    assert patch_lane["external_review_received"] is True
    assert patch_lane["ext_findings_count"] == 4
    assert patch_lane["reviewer_recheck_required"] is True
    assert patch_lane["closure_state"] == "external_pending"
    assert "does not close external/source review" in doc
    assert "Patch Apply | yes | 4 | 0 | yes | external_pending" in doc
    assert "make v06-lane-status" in readme
    assert "v06-lane-status:" in makefile
    assert "v06-lane-status" in makefile.partition("release-check:")[2]
    assert "193 - External finding triage wave | Done" in backlog
    assert "lane-status board added" in manifest
    assert "v0.6 Lane Status Board" in index
    assert "docs/codex/v0.6-lane-status-board.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/v0.6-lane-status-board.json" in review_docs.REVIEW_DOCS
    assert "docs/codex/v0.6-lane-status-board.md" in docs_site
    v06_lane_status.check_outputs(
        board,
        output_doc=Path("docs/codex/v0.6-lane-status-board.md"),
        output_json=Path("docs/codex/v0.6-lane-status-board.json"),
    )


def test_v06_closure_readiness_bundle_is_wired() -> None:
    report = v06_closure_readiness.build_report(Path.cwd())
    readme = Path("README.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    manifest = Path("docs/codex/v0.6-milestone-manifest.md").read_text(
        encoding="utf-8"
    )
    manifest_json = json.loads(
        Path("docs/codex/v0.6-milestone-manifest.json").read_text(encoding="utf-8")
    )
    index = Path("docs/codex/review-docs-index.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    assert report["valid"] is True
    assert report["external_review_received"] == 1
    assert report["external_review_closed"] == 0
    assert report["critical_high_open_count"] == 0
    assert "make v06-closure-readiness" in readme
    assert "v06-closure-readiness:" in makefile
    assert "v06-closure-readiness" in makefile.partition("release-check:")[2]
    assert "v06-closure-readiness" in release_guardrails.REQUIRED_RELEASE_CHECK_FRAGMENTS
    assert "194-199 - v0.6 closure-readiness bundle | Done" in backlog
    assert "194 | Critical/high fix freeze | Done" in manifest
    assert "199 | v0.6 post-review packet | Done" in manifest
    assert manifest_json["milestones"][13]["status"].startswith("Done")
    for doc in [
        "docs/codex/v0.6-critical-high-fix-freeze.md",
        "docs/codex/v0.6-medium-risk-disposition.md",
        "docs/codex/v0.6-external-review-outcome-summary.md",
        "docs/codex/source-review-closure-matrix-v4.md",
        "docs/codex/accepted-risk-register-v2.md",
        "docs/codex/accepted-risk-register-v2.json",
        "docs/codex/v0.6-post-review-packet.md",
    ]:
        assert doc in review_docs.REVIEW_DOCS
        if doc.endswith(".md"):
            assert doc in docs_site
    for title in [
        "v0.6 Critical/High Fix Freeze",
        "v0.6 Medium-Risk Disposition",
        "v0.6 External Review Outcome Summary",
        "Source Review Closure Matrix v4",
        "Accepted Risk Register v2",
        "v0.6 Post-Review Packet",
    ]:
        assert title in index


def test_v06_final_handoff_docs_are_wired() -> None:
    report = v06_final_handoff.build_report(Path.cwd())
    readme = Path("README.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    manifest = Path("docs/codex/v0.6-milestone-manifest.md").read_text(
        encoding="utf-8"
    )
    manifest_json = json.loads(
        Path("docs/codex/v0.6-milestone-manifest.json").read_text(encoding="utf-8")
    )
    index = Path("docs/codex/review-docs-index.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")

    assert report["valid"] is True
    assert report["external_review_received"] == 1
    assert report["external_review_closed"] == 0
    assert report["capability_expansion_allowed"] is False
    assert "make v06-final-handoff" in readme
    assert "v06-final-handoff:" in makefile
    assert "v06-final-handoff" in makefile.partition("release-check:")[2]
    assert "v06-final-handoff" in release_guardrails.REQUIRED_RELEASE_CHECK_FRAGMENTS
    assert "200-215 - v0.6 final no-go handoff | Done" in backlog
    assert "211 | v0.6 final go/no-go packet | Done" in manifest
    assert "215 | v0.6 handoff to user | Done" in manifest
    assert manifest_json["milestones"][-1]["status"].startswith("Done")
    for doc in [
        "docs/codex/v0.6-public-preview-readiness-decision.md",
        "docs/codex/v0.6-capability-decision-v2.md",
        "docs/codex/operator-quickstart-v2.md",
        "docs/codex/diagnostics-bundle-v2.md",
        "docs/codex/external-review-recheck-loop.md",
        "docs/codex/release-candidate-naming-cleanup.md",
        "docs/codex/v0.6-public-preview-packet.md",
        "docs/codex/v0.7-design-only-capability-rubric.md",
        "docs/codex/candidate-capability-triage.md",
        "docs/codex/security-claims-freeze.md",
        "docs/codex/v0.6-final-go-no-go-packet.md",
        "docs/codex/v0.7-boundary-decision-seed.md",
        "docs/codex/v0.6-retrospective.md",
        "docs/codex/review-artifact-minimization-pass.md",
        "docs/codex/v0.6-handoff-to-user.md",
    ]:
        assert doc in review_docs.REVIEW_DOCS
        assert doc in docs_site
    for title in [
        "v0.6 Public-Preview Readiness Decision",
        "v0.6 Capability Decision v2",
        "Operator Quickstart v2",
        "Diagnostics Bundle v2",
        "External Review Recheck Loop",
        "Release Candidate Naming Cleanup",
        "v0.6 Final Go/No-Go Packet",
        "v0.6 Handoff To User",
    ]:
        assert title in index


def test_v07_external_review_closure_prep_is_wired() -> None:
    report = v07_closure_prep.build_report(Path.cwd())
    readme = Path("README.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    index = Path("docs/codex/review-docs-index.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")
    partition = Path("docs/codex/v0.7-external-review-row-partition.md").read_text(
        encoding="utf-8"
    )

    assert report["valid"] is True
    assert report["pending_external_review_rows"] == 55
    assert report["externally_closed_rows"] == 0
    assert report["capability_expansion_allowed"] is False
    assert "make v07-closure-prep" in readme
    assert "v07-closure-prep:" in makefile
    assert "v07-closure-prep" in makefile.partition("release-check:")[2]
    assert "v07-closure-prep" in release_guardrails.REQUIRED_RELEASE_CHECK_FRAGMENTS
    assert "216 - v0.7 closure charter and freeze | Done" in backlog
    assert "217 - v0.6 final packet sanity review | Done" in backlog
    assert "218 - External-review row partition | Done" in backlog
    for doc in [
        "docs/codex/v0.7-external-review-closure-charter.md",
        "docs/codex/v0.6-final-packet-sanity-review.md",
        "docs/codex/v0.7-external-review-row-partition.md",
    ]:
        assert doc in review_docs.REVIEW_DOCS
        assert doc in docs_site
    for title in [
        "v0.7 External Review Closure Charter",
        "v0.6 Final Packet Sanity Review",
        "v0.7 External Review Row Partition",
    ]:
        assert title in index
    for batch in [
        "Patch apply recheck",
        "Filesystem/platform",
        "HTTP fetch",
        "Signed evidence/audit",
        "Policy/registry",
        "MCP ingress",
        "Review console/admin",
        "Release/evidence automation",
        "Docs/claims/public-preview wording",
    ]:
        assert batch in partition


def test_v07_patch_apply_recheck_prep_is_wired() -> None:
    report = v07_patch_apply_recheck.build_report(Path.cwd())
    readme = Path("README.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    index = Path("docs/codex/review-docs-index.md").read_text(encoding="utf-8")
    docs_site = Path("scripts/build_docs_site.py").read_text(encoding="utf-8")
    recheck_doc = Path("docs/codex/v0.7-patch-apply-recheck-request.md").read_text(
        encoding="utf-8"
    )
    packet_script = Path("scripts/patch_apply_external_review_packet.py").read_text(
        encoding="utf-8"
    )

    assert report["valid"] is True
    assert report["fixed_findings"] == [
        "EXT-PA-001",
        "EXT-PA-002",
        "EXT-PA-003",
        "EXT-PA-004",
    ]
    assert report["closure_state"] == "external_pending"
    assert "make v07-patch-apply-recheck-prep" in readme
    assert "v07-patch-apply-recheck-prep:" in makefile
    assert "v07-patch-apply-recheck-prep" in makefile.partition("release-check:")[2]
    assert (
        "v07-patch-apply-recheck-prep"
        in release_guardrails.REQUIRED_RELEASE_CHECK_FRAGMENTS
    )
    assert "219 - Patch-apply recheck closure prep | Done" in backlog
    assert "docs/codex/v0.7-patch-apply-recheck-request.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/v0.7-patch-apply-recheck-request.md" in docs_site
    assert "v0.7 Patch Apply Recheck Request" in index
    assert "EXT-PA-001" in recheck_doc
    assert "EXT-PA-004" in recheck_doc
    assert "docs/codex/v0.7-patch-apply-recheck-request.md" in packet_script
    assert "EXT-PA-001" in packet_script


def test_external_response_normalization_rejects_ambiguous_source_review() -> None:
    finding_header = (
        "| Finding ID | Severity | Area | Affected files/functions | "
        "Blocking status | Disposition | Recommended fix |"
    )
    raw_response = "\n".join(
        [
            "# Review",
            "",
            finding_header,
            "| --- | --- | --- | --- | --- | --- | --- |",
            "| EXT-002 | high | filesystem | unknown | blocking | open | inspect path handling |",
        ]
    )
    with pytest.raises(external_response_normalize.ExternalResponseNormalizationError):
        external_response_normalize.normalize_response(
            raw_response,
            reviewer="GPT 5.5 Pro",
            reviewer_type="external-model",
            source_access="source-level",
            reviewed_commit="abcdef1234567890",
            reviewed_packet_hash="sha256:" + "0" * 64,
            area="filesystem",
        )


def test_external_response_normalization_accepts_lane_specific_ids() -> None:
    raw_response = "\n".join(
        [
            "# Patch Review",
            "",
            "| Finding ID | Severity | Area | Affected files/functions | "
            "Blocking status | Disposition | Recommended fix |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            "| EXT-PA-001 | medium | patch-apply | apps/api/src/ithildin_api/patches.py | "
            "should-fix | open | tighten transition tests |",
        ]
    )

    normalized = external_response_normalize.normalize_response(
        raw_response,
        reviewer="GPT 5.5 Pro",
        reviewer_type="external-model",
        source_access="source-level",
        reviewed_commit="abcdef1234567890",
        reviewed_packet_hash="sha256:" + "0" * 64,
        area="patch-apply",
    )

    assert normalized["findings"][0]["finding_id"] == "EXT-PA-001"

    tab_response = "\n".join(
        [
            "# Patch Review",
            "",
            "Finding ID\tSeverity\tArea\tAffected files/functions\t"
            "Blocking status\tDisposition\tRecommended fix",
            "EXT-PA-002\tmedium\tpatch-apply\tapps/api/src/ithildin_api/patches.py\t"
            "should-fix\topen\tadd proposal reservation",
            "EXT-PA-004\tlow/informational\tpatch-apply\tapps/api/src/ithildin_api/patches.py\t"
            "later/advisory\topen\tdocument or enforce hunk counts",
        ]
    )
    tab_normalized = external_response_normalize.normalize_response(
        tab_response,
        reviewer="GPT 5.5 Pro",
        reviewer_type="external-model",
        source_access="source-level",
        reviewed_commit="abcdef1234567890",
        reviewed_packet_hash="sha256:" + "0" * 64,
        area="patch-apply",
    )
    assert tab_normalized["findings"][0]["finding_id"] == "EXT-PA-002"
    assert tab_normalized["findings"][1]["severity"] == "low"
    assert tab_normalized["findings"][1]["blocking_status"] == "later"


def test_external_response_normalization_binds_area_and_namespace() -> None:
    raw_response = "\n".join(
        [
            "# Patch Review",
            "",
            "| Finding ID | Severity | Area | Affected files/functions | "
            "Blocking status | Disposition | Recommended fix |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            "| EXT-HTTP-001 | medium | http-fetch | apps/api/src/ithildin_api/http_tools.py | "
            "should-fix | open | inspect redirect behavior |",
        ]
    )

    with pytest.raises(
        external_response_normalize.ExternalResponseNormalizationError,
        match="namespace does not match",
    ):
        external_response_normalize.normalize_response(
            raw_response,
            reviewer="GPT 5.5 Pro",
            reviewer_type="external-model",
            source_access="source-level",
            reviewed_commit="abcdef1234567890",
            reviewed_packet_hash="sha256:" + "0" * 64,
            area="patch-apply",
        )


def test_external_response_normalization_requires_findings_or_explicit_none() -> None:
    with pytest.raises(
        external_response_normalize.ExternalResponseNormalizationError,
        match="finding table or explicitly state no findings",
    ):
        external_response_normalize.normalize_response(
            "# Review\n\nLooks good from the packet.",
            reviewer="GPT 5.5 Pro",
            reviewer_type="external-model",
            source_access="source-level",
            reviewed_commit="abcdef1234567890",
            reviewed_packet_hash="sha256:" + "0" * 64,
            area="patch-apply",
        )

    normalized = external_response_normalize.normalize_response(
        "# Review\n\nNo findings.",
        reviewer="GPT 5.5 Pro",
        reviewer_type="external-model",
        source_access="source-level",
        reviewed_commit="abcdef1234567890",
        reviewed_packet_hash="sha256:" + "0" * 64,
        area="patch-apply",
    )

    assert normalized["finding_count"] == 0


def test_external_response_normalization_rejects_malformed_packet_hash() -> None:
    with pytest.raises(
        external_response_normalize.ExternalResponseNormalizationError,
        match="64 lowercase hex",
    ):
        external_response_normalize.normalize_response(
            "# Review\n\nNo findings.",
            reviewer="GPT 5.5 Pro",
            reviewer_type="external-model",
            source_access="source-level",
            reviewed_commit="abcdef1234567890",
            reviewed_packet_hash="sha256:not-a-real-digest",
            area="patch-apply",
        )


def test_reviewer_finding_template_has_required_fields() -> None:
    template = Path("docs/codex/reviewer-finding-template.md").read_text(encoding="utf-8")
    prompt = Path("docs/codex/v0.2-external-review-prompt.md").read_text(encoding="utf-8")
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(encoding="utf-8")

    for field in [
        "Finding ID",
        "Severity",
        "Affected files/functions",
        "Claim being tested",
        "Observed behavior",
        "Recommended fix",
        "Blocking status",
        "Disposition",
        "Verification notes",
        "Overall judgment",
        "Brutal short version",
    ]:
        assert field in template
    assert "reviewer-finding-template.md" in prompt
    assert "reviewer-finding-template.md" in reproduction_map


def test_reviewer_finding_intake_validates_records(tmp_path: Path) -> None:
    findings_dir = tmp_path / "findings"
    findings_dir.mkdir()
    findings_dir.joinpath("isr-003.md").write_text(
        """# ISR-003 Example

- Finding ID: ISR-003
- Severity: medium
- Area: patch apply
- Affected files/functions: apps/api/src/ithildin_api/patches.py
- Claim being tested: one-time approval cannot replay
- Observed behavior: replay is rejected
- Risk: regression would permit duplicate writes
- Recommended fix: keep replay tests
- Blocking status: should-fix
- Disposition: open
- Verification notes: fixture finding
""",
        encoding="utf-8",
    )

    records = reviewer_findings.validate_findings(
        findings_dir=findings_dir,
        repo_root=tmp_path,
    )

    assert [record.finding_id for record in records] == ["ISR-003"]
    assert records[0].fields["Severity"] == "medium"

    findings_dir.joinpath("ext-pa-001.md").write_text(
        """# EXT-PA-001 Example

- Finding ID: EXT-PA-001
- Severity: medium
- Area: patch apply
- Affected files/functions: apps/api/src/ithildin_api/patches.py
- Claim being tested: external patch finding namespaces validate
- Observed behavior: fixture
- Risk: fixture risk
- Recommended fix: fixture fix
- Blocking status: should-fix
- Disposition: fixed
- Verification notes: fixture verification
""",
        encoding="utf-8",
    )
    records = reviewer_findings.validate_findings(
        findings_dir=findings_dir,
        repo_root=tmp_path,
    )
    assert {record.finding_id for record in records} == {"ISR-003", "EXT-PA-001"}


def test_reviewer_finding_intake_rejects_invalid_records(tmp_path: Path) -> None:
    findings_dir = tmp_path / "findings"
    findings_dir.mkdir()
    findings_dir.joinpath("bad.md").write_text(
        """# Bad

- Finding ID: BAD-1
- Severity: urgent
""",
        encoding="utf-8",
    )

    with pytest.raises(reviewer_findings.FindingValidationError):
        reviewer_findings.validate_findings(
            findings_dir=findings_dir,
            repo_root=tmp_path,
        )


def test_reviewer_finding_intake_rejects_duplicates(tmp_path: Path) -> None:
    findings_dir = tmp_path / "findings"
    findings_dir.mkdir()
    body = """# Duplicate

- Finding ID: EXT-001
- Severity: low
- Area: review packet
- Affected files/functions: docs/codex/v0.2-review-packet.md
- Claim being tested: finding IDs are unique
- Observed behavior: duplicate fixture
- Risk: closure ambiguity
- Recommended fix: assign unique ID
- Blocking status: later
- Disposition: open
- Verification notes: fixture finding
"""
    findings_dir.joinpath("one.md").write_text(body, encoding="utf-8")
    findings_dir.joinpath("two.md").write_text(body, encoding="utf-8")

    with pytest.raises(reviewer_findings.FindingValidationError, match="duplicate"):
        reviewer_findings.validate_findings(
            findings_dir=findings_dir,
            repo_root=tmp_path,
        )


def test_reviewer_finding_intake_rejects_open_high_findings(tmp_path: Path) -> None:
    findings_dir = tmp_path / "findings"
    findings_dir.mkdir()
    findings_dir.joinpath("high.md").write_text(
        """# High

- Finding ID: EXT-002
- Severity: high
- Area: patch apply
- Affected files/functions: apps/api/src/ithildin_api/patches.py
- Claim being tested: crash states are diagnosed
- Observed behavior: fixture
- Risk: fixture risk
- Recommended fix: fixture fix
- Blocking status: should-fix
- Disposition: open
- Verification notes: fixture finding
""",
        encoding="utf-8",
    )

    with pytest.raises(reviewer_findings.FindingValidationError, match="open high"):
        reviewer_findings.validate_findings(
            findings_dir=findings_dir,
            repo_root=tmp_path,
        )


def test_reviewer_finding_summary_handles_paths_outside_repo(tmp_path: Path) -> None:
    outside_root = tmp_path / "outside"
    findings_dir = outside_root / "findings"
    findings_dir.mkdir(parents=True)
    findings_dir.joinpath("low.md").write_text(
        """# Low

- Finding ID: SUB-001
- Severity: low
- Area: release packet
- Affected files/functions: docs/codex/v0.2-review-packet.md
- Claim being tested: summaries are printable
- Observed behavior: fixture
- Risk: fixture risk
- Recommended fix: fixture fix
- Blocking status: later
- Disposition: open
- Verification notes: fixture finding
""",
        encoding="utf-8",
    )

    records = reviewer_findings.validate_findings(
        findings_dir=findings_dir,
        repo_root=Path("/not/the/root"),
    )

    assert records[0].summary(Path("/not/the/root"))["path"].endswith("low.md")


def test_reviewer_finding_intake_doc_and_release_check_are_wired() -> None:
    intake = Path("docs/codex/reviewer-finding-intake.md").read_text(encoding="utf-8")
    makefile = Path("Makefile").read_text(encoding="utf-8")
    review_packet = Path("docs/codex/v0.2-review-packet.md").read_text(encoding="utf-8")
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(encoding="utf-8")

    assert "make reviewer-findings-check" in intake
    assert "reviewer-findings-check:" in makefile
    assert (
        "release-check: release-context manifest-lock-check release-guardrails "
        "release-evidence-gate reviewer-findings-check review-findings-summary "
        "review-run-manifest-check filesystem-contract-check"
    ) in makefile
    assert "open critical/high findings" in intake
    assert "reviewer-finding-intake.md" in review_packet
    assert "reviewer-finding-intake.md" in reproduction_map
    assert "docs/codex/reviewer-finding-intake.md" in review_docs.REVIEW_DOCS


def test_review_run_manifest_validator_accepts_valid_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = tmp_path / "prompt.md"
    output = tmp_path / "output.md"
    prompt.write_text("prompt\n", encoding="utf-8")
    output.write_text("output\n", encoding="utf-8")
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    commit = "abc1234"
    runs_dir.joinpath("review-run-fixture.json").write_text(
        json.dumps(
            {
                "review_id": "review-1",
                "prompt_file": "prompt.md",
                "reviewer_type": "internal_ai",
                "reviewer_name": "fixture",
                "date": "2026-05-31",
                "commit": commit,
                "dirty": False,
                "files_inspected": ["apps/api/src/ithildin_api/http_tools.py"],
                "tests_run": ["uv run pytest tests/test_http_tools.py"],
                "output_file": "output.md",
                "finding_count": 2,
                "severity_counts": {
                    "critical": 0,
                    "high": 0,
                    "medium": 2,
                    "low": 0,
                    "informational": 0,
                },
                "closure_matrix_rows_touched": ["http.fetch"],
                "findings": [
                    {
                        "finding_id": "V03-INT-HTTP-001",
                        "severity": "medium",
                        "kind": "implementation",
                        "files_functions": ["http_tools.py:HttpFetchExecutor.fetch"],
                        "disposition": "open",
                    },
                    {
                        "finding_id": "EXT-PA-001",
                        "severity": "medium",
                        "kind": "implementation",
                        "files_functions": ["patches.py:PatchProposalService.apply_approved"],
                        "disposition": "open",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        review_run_manifest,
        "_git",
        lambda repo_root, args: commit if args == ["rev-parse", "HEAD"] else "",
    )

    summaries = review_run_manifest.validate_review_runs(runs_dir, tmp_path)

    assert summaries[0]["review_id"] == "review-1"
    assert summaries[0]["finding_count"] == 2


def test_review_run_manifest_validator_rejects_missing_and_mismatched_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    runs_dir.joinpath("review-run-bad.json").write_text(
        json.dumps(
            {
                "review_id": "review-1",
                "prompt_file": "missing.md",
                "reviewer_type": "internal_ai",
                "reviewer_name": "fixture",
                "date": "2026-05-31",
                "commit": "abc1234",
                "dirty": True,
                "files_inspected": [],
                "tests_run": [],
                "output_file": "missing-output.md",
                "finding_count": 0,
                "severity_counts": {
                    "critical": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                    "informational": 0,
                },
                "closure_matrix_rows_touched": [],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        review_run_manifest,
        "_git",
        lambda repo_root, args: "abc1234" if args == ["rev-parse", "HEAD"] else "",
    )

    with pytest.raises(review_run_manifest.ReviewRunManifestError, match="dirty state"):
        review_run_manifest.validate_review_runs(runs_dir, tmp_path)


def test_review_run_manifest_doc_and_release_check_are_wired() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    schema = Path("docs/codex/review-run-manifest-schema.md").read_text(encoding="utf-8")

    assert "review-run-manifest-check:" in makefile
    assert "review-run-manifest-check" in makefile.partition("release-check:")[2]
    assert "make review-run-manifest-check" in readme
    assert "V03-INT-PATCH-001" in schema
    assert "docs/codex/review-run-manifest-schema.md" in review_docs.REVIEW_DOCS


def test_review_findings_summary_collects_structured_records() -> None:
    summary = review_findings_collect.collect_findings_summary(
        Path("docs/codex/findings"),
        Path.cwd(),
    )

    assert summary["total"] >= 1
    assert summary["open_critical_high"] == 0
    assert any(finding["finding_id"] == "SUB-001" for finding in summary["findings"])


def test_review_findings_summary_doc_and_release_check_are_wired() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    summary = Path("docs/codex/v0.3-review-findings-summary.md").read_text(encoding="utf-8")

    assert "review-findings-summary:" in makefile
    assert "review-findings-summary" in makefile.partition("release-check:")[2]
    assert "make review-findings-summary" in readme
    assert "SUB-001" in summary
    assert "docs/codex/v0.3-review-findings-summary.md" in review_docs.REVIEW_DOCS


def test_source_review_closure_matrix_v3_is_guarded() -> None:
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")

    assert "## v3 Closure State" in matrix
    for state in [
        "not_started",
        "internal_reviewed",
        "external_pending",
        "external_reviewed",
        "blocked",
        "fixed_pending_verify",
        "closed_local_preview",
        "accepted_deferred",
    ]:
        assert state in matrix
    assert "Patch apply" in matrix
    assert "Review console evidence" in matrix
    assert release_guardrails._check_closure_matrix_v3() == []


def test_release_check_enforces_filesystem_contract_check() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")

    assert (
        "release-check: release-context manifest-lock-check release-guardrails "
        "release-evidence-gate reviewer-findings-check review-findings-summary "
        "review-run-manifest-check filesystem-contract-check"
    ) in makefile
    assert "Task 091 release-check filesystem-contract-check gate" in matrix


def test_internal_ai_review_workflow_and_packet_are_validated(tmp_path: Path) -> None:
    workflow = Path("docs/codex/internal-ai-review-workflow.md").read_text(encoding="utf-8")
    prompt = Path("docs/codex/v0.2-review-packet.md").read_text(encoding="utf-8")
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(encoding="utf-8")

    for required in [
        "not an independent external audit",
        "make internal-review-packet",
        "Patch apply approval binding",
        "HTTP fetch SSRF",
        "Manifest, principal, and workspace registry fail-closed behavior",
        "Release evidence automation and guardrails",
        "reviewer-finding-template.md",
        "source-review-closure-matrix.md",
    ]:
        assert required in workflow
    assert "internal-ai-review-workflow.md" in prompt
    assert "internal-ai-review-workflow.md" in reproduction_map

    output_dir = internal_review_packet.build_internal_review_packet(tmp_path / "packet")
    expected_prompts = {
        "patch-apply.md",
        "filesystem.md",
        "http-fetch.md",
        "signed-evidence.md",
        "policy-parity.md",
        "registry-fail-closed.md",
        "evidence-automation.md",
        "mcp-ingress.md",
        "review-console.md",
    }
    assert {path.name for path in output_dir.glob("*.md")} == {
        *expected_prompts,
        "INTERNAL_REVIEW_INDEX.md",
    }
    prompt_text = output_dir.joinpath("patch-apply.md").read_text(encoding="utf-8")
    assert "docs/codex/reviewer-finding-template.md" in prompt_text
    assert "apps/api/src/ithildin_api/patches.py" in prompt_text
    assert "Do not propose new powerful tool classes" in prompt_text
    index_text = output_dir.joinpath("INTERNAL_REVIEW_INDEX.md").read_text(encoding="utf-8")
    assert "Internal AI Review Packet v2" in index_text
    assert "v0.3-prep evidence automation" in index_text


def test_internal_review_packet_v2_is_documented() -> None:
    doc = Path("docs/codex/internal-review-packet-v2.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    review_packet = Path("docs/codex/v0.2-review-packet.md").read_text(encoding="utf-8")
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")

    for required in [
        "var/review-packets/v0.3/internal-ai-review-packet/",
        "signed evidence and audit integrity",
        "manifest, principal, and workspace fail-closed registries",
        "release evidence automation and guardrails",
        "not independent external validation",
    ]:
        assert required in doc
    assert "v2 local prompts" in readme
    assert "internal-review-packet-v2.md" in review_packet
    assert "internal-review-packet-v2.md" in reproduction_map
    assert "109 - Internal AI review packet v2 | Done" in backlog
    assert "Task 109 updates" in matrix
    assert "docs/codex/internal-review-packet-v2.md" in review_docs.REVIEW_DOCS


def test_v03_external_review_packet_is_documented() -> None:
    packet = Path("docs/codex/v0.3-review-packet.md").read_text(encoding="utf-8")
    prompt = Path("docs/codex/v0.3-external-review-prompt.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")

    for required in [
        "v0.3-prep external/source-review packet",
        "make review-candidate",
        "What This Packet Does Not Prove",
        "Do Not Add Yet",
    ]:
        assert required in packet
    for required in [
        "v0.3-prep source",
        "SUB-001",
        "Release automation",
        "Do-not-add-yet list",
    ]:
        assert required in prompt
    assert "v0.3-review-packet.md" in readme
    assert "v0.3-external-review-prompt.md" in readme
    assert "v0.3-review-packet.md" in reproduction_map
    assert "v0.3-external-review-prompt.md" in reproduction_map
    assert "110 - External review packet v3 | Done" in backlog
    assert "Task 110 adds" in matrix
    assert "docs/codex/v0.3-review-packet.md" in review_docs.REVIEW_DOCS
    assert "docs/codex/v0.3-external-review-prompt.md" in review_docs.REVIEW_DOCS


def test_external_review_intake_and_closure_is_documented() -> None:
    doc = Path("docs/codex/external-review-intake-and-closure.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    packet = Path("docs/codex/v0.3-review-packet.md").read_text(encoding="utf-8")
    prompt = Path("docs/codex/v0.3-external-review-prompt.md").read_text(encoding="utf-8")
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")

    for required in [
        "EXT-###",
        "make reviewer-findings-check",
        "Critical/high open findings stop autonomous implementation",
        "pending external review",
    ]:
        assert required in doc
    for linked in [readme, packet, prompt, reproduction_map]:
        assert "external-review-intake-and-closure.md" in linked
    assert "111 - External review intake and closure | Done" in backlog
    assert "Task 111 adds" in matrix
    assert "docs/codex/external-review-intake-and-closure.md" in review_docs.REVIEW_DOCS


def test_v03_boundary_decision_is_documented() -> None:
    decision = Path("docs/codex/v0.3-boundary-decision.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    packet = Path("docs/codex/v0.3-review-packet.md").read_text(encoding="utf-8")
    prompt = Path("docs/codex/v0.3-external-review-prompt.md").read_text(encoding="utf-8")
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")

    for required in [
        "ready for external/source review handoff",
        "not a decision to broaden tool powers",
        "Required Before Any Boundary Expansion",
        "not a sandbox",
    ]:
        assert required in decision
    for linked in [readme, packet, prompt, reproduction_map]:
        assert "v0.3-boundary-decision.md" in linked
    assert "112 - v0.3 boundary decision memo | Done" in backlog
    assert "Task 112 adds" in matrix
    assert "docs/codex/v0.3-boundary-decision.md" in review_docs.REVIEW_DOCS


def test_autonomous_sprint_guardrails_are_linked_and_validated() -> None:
    guardrails = Path("docs/codex/autonomous-sprint-guardrails.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    review_packet = Path("docs/codex/v0.2-review-packet.md").read_text(encoding="utf-8")
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(encoding="utf-8")

    for required in [
        "one formal goal at a time",
        "same blocking failure repeats three times",
        "trust-boundary regression",
        "Wall-Hit Status Format",
        "current commit and dirty state",
        "External review is also required after every 3-5 autonomous hardening sprints",
        "make review-candidate",
        "make internal-review-packet",
    ]:
        assert required in guardrails
    for linked in [readme, review_packet, reproduction_map]:
        assert "autonomous-sprint-guardrails.md" in linked


def test_review_doc_metadata_is_deterministic(tmp_path: Path) -> None:
    doc = tmp_path / "README.md"
    doc.write_text("hello\n", encoding="utf-8")

    first = review_docs.collect_review_doc_metadata(tmp_path, ["README.md"])
    second = review_docs.collect_review_doc_metadata(tmp_path, ["README.md"])

    assert first == second
    assert first == [
        {
            "path": "README.md",
            "sha256": "sha256:5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03",
            "bytes": 6,
        }
    ]


def test_review_doc_metadata_fails_for_missing_doc(tmp_path: Path) -> None:
    with pytest.raises(review_docs.ReviewDocError, match="review document is missing"):
        review_docs.collect_review_doc_metadata(tmp_path, ["missing.md"])


def test_review_packet_bundle_fails_outside_repo_markers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["review_packet_bundle.py"])

    result = review_packet_bundle.main()

    assert result == 1
    assert "must be run from the Ithildin repo root" in capsys.readouterr().err


def test_review_packet_bundle_rejects_dirty_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_project_markers(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        review_packet_bundle,
        "_git",
        lambda args: " M README.md" if args == ["status", "--short"] else "abc123",
    )

    with pytest.raises(review_packet_bundle.BundleError, match="working tree is dirty"):
        review_packet_bundle.build_bundle(
            repo_root=tmp_path,
            output_root=tmp_path / "var/review-packets/v0.2",
            allow_dirty=False,
            run_release_check=False,
        )


def test_review_packet_bundle_layout_and_exclusions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_project_markers(tmp_path)
    docs = ["README.md", "docs/codex/v0.2-review-packet.md"]
    for doc in docs:
        path = tmp_path / doc
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {path.stem}\n", encoding="utf-8")
    demo_summary = tmp_path / "var/review-packets/v0.2/signed-evidence-demo/SIGNED_EVIDENCE_DEMO.md"
    demo_summary.parent.mkdir(parents=True)
    demo_summary.write_text("# Signed Evidence Demo\n", encoding="utf-8")
    negative_transcripts = (
        tmp_path
        / "var/review-packets/v0.2/negative-review-transcripts/NEGATIVE_REVIEW_TRANSCRIPTS.md"
    )
    negative_transcripts.parent.mkdir(parents=True)
    negative_transcripts.write_text("# Negative Review Transcripts\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(review_packet_bundle, "REVIEW_DOCS", docs)
    monkeypatch.setattr(review_packet_bundle, "BUNDLE_DOCS", docs)

    def fake_git(args: list[str]) -> str:
        if args == ["status", "--short"]:
            return ""
        if args == ["rev-parse", "HEAD"]:
            return "abcdef1234567890"
        if args == ["branch", "--show-current"]:
            return "main"
        if args == ["log", "-12", "--oneline"]:
            return "abcdef1 test commit"
        raise AssertionError(args)

    def fake_capture(command: list[str]) -> review_packet_bundle.CommandOutput:
        if "scripts/release_evidence.py" in command:
            stdout = '{"secret_free": true}\n'
        elif "scripts/release_packet.py" in command and "--json" in command:
            stdout = '{"packet": "ok"}\n'
        else:
            stdout = "ok\n"
        return review_packet_bundle.CommandOutput(
            command=command,
            returncode=0,
            stdout=stdout,
            stderr="",
        )

    monkeypatch.setattr(review_packet_bundle, "_git", fake_git)
    monkeypatch.setattr(review_packet_bundle, "_run_capture", fake_capture)

    result = review_packet_bundle.build_bundle(
        repo_root=tmp_path,
        output_root=tmp_path / "var/review-packets/v0.2",
        allow_dirty=False,
        run_release_check=True,
    )

    assert result.path.joinpath("INDEX.md").exists()
    assert result.path.joinpath("release-check.txt").exists()
    assert result.path.joinpath("filesystem-contract-check.txt").exists()
    assert result.path.joinpath("release-evidence.json").exists()
    assert result.path.joinpath("release-evidence.json.transcript.txt").exists()
    assert result.path.joinpath("release-packet.md").exists()
    assert result.path.joinpath("release-packet.json").exists()
    assert result.path.joinpath("release-packet.json.transcript.txt").exists()
    assert result.path.joinpath("review-doc-hashes.json").exists()
    assert result.path.joinpath("artifact-hashes.json").exists()
    assert result.path.joinpath("git-summary.txt").exists()
    assert result.path.joinpath("docs/README.md").exists()
    assert result.path.joinpath("docs/docs/codex/v0.2-review-packet.md").exists()
    assert result.path.joinpath("signed-evidence-demo/SIGNED_EVIDENCE_DEMO.md").exists()
    assert result.path.joinpath("signed-evidence-demo/signed-evidence-demo-verify.json").exists()
    assert result.path.joinpath(
        "signed-evidence-demo/signed-evidence-demo-verify.json.transcript.txt"
    ).exists()
    assert result.path.joinpath(
        "negative-review-transcripts/NEGATIVE_REVIEW_TRANSCRIPTS.md"
    ).exists()
    artifact_hashes = json.loads(
        result.path.joinpath("artifact-hashes.json").read_text(encoding="utf-8")
    )
    artifact_paths = {artifact["path"] for artifact in artifact_hashes}
    assert "INDEX.md" in artifact_paths
    assert "release-check.txt" in artifact_paths
    assert "filesystem-contract-check.txt" in artifact_paths
    assert "release-evidence.json" in artifact_paths
    assert "release-evidence.json.transcript.txt" in artifact_paths
    assert "release-packet.md" in artifact_paths
    assert "release-packet.json" in artifact_paths
    assert "release-packet.json.transcript.txt" in artifact_paths
    assert "review-doc-hashes.json" in artifact_paths
    assert "docs/README.md" in artifact_paths
    assert "signed-evidence-demo/SIGNED_EVIDENCE_DEMO.md" in artifact_paths
    assert "signed-evidence-demo/signed-evidence-demo-verify.json" in artifact_paths
    assert "signed-evidence-demo/signed-evidence-demo-verify.json.transcript.txt" in artifact_paths
    assert "negative-review-transcripts/NEGATIVE_REVIEW_TRANSCRIPTS.md" in artifact_paths
    bundle_paths = [path.as_posix() for path in result.path.rglob("*")]
    assert not any("/.env" in path for path in bundle_paths)
    assert not any("/var/keys/" in path for path in bundle_paths)
    assert "review-doc-hashes.json" in result.path.joinpath("INDEX.md").read_text(encoding="utf-8")
    assert "artifact-hashes.json" in result.path.joinpath("INDEX.md").read_text(encoding="utf-8")
    assert "filesystem-contract-check.txt" in result.path.joinpath("INDEX.md").read_text(
        encoding="utf-8"
    )


def test_review_packet_diff_compares_artifact_hashes(tmp_path: Path) -> None:
    old_packet = tmp_path / "old"
    new_packet = tmp_path / "new"
    old_packet.mkdir()
    new_packet.mkdir()
    old_packet.joinpath("artifact-hashes.json").write_text(
        json.dumps(
            [
                {"path": "INDEX.md", "sha256": "sha256:" + ("1" * 64), "bytes": 10},
                {"path": "old-only.txt", "sha256": "sha256:" + ("2" * 64), "bytes": 20},
                {"path": "changed.txt", "sha256": "sha256:" + ("3" * 64), "bytes": 30},
            ]
        ),
        encoding="utf-8",
    )
    new_packet.joinpath("artifact-hashes.json").write_text(
        json.dumps(
            [
                {"path": "INDEX.md", "sha256": "sha256:" + ("1" * 64), "bytes": 10},
                {"path": "new-only.txt", "sha256": "sha256:" + ("4" * 64), "bytes": 40},
                {"path": "changed.txt", "sha256": "sha256:" + ("5" * 64), "bytes": 50},
            ]
        ),
        encoding="utf-8",
    )

    diff = review_packet_diff.compare_packets(old_packet, new_packet)

    assert [artifact.path for artifact in diff.added] == ["new-only.txt"]
    assert [artifact.path for artifact in diff.removed] == ["old-only.txt"]
    assert [entry["old"].path for entry in diff.changed] == ["changed.txt"]
    assert diff.unchanged_count == 1
    rendered = review_packet_diff.render_diff(diff)
    assert "added: `1`" in rendered
    assert "changed: `1`" in rendered


def test_review_packet_diff_rejects_unsafe_artifact_paths(tmp_path: Path) -> None:
    old_packet = tmp_path / "old"
    new_packet = tmp_path / "new"
    old_packet.mkdir()
    new_packet.mkdir()
    for packet in [old_packet, new_packet]:
        packet.joinpath("artifact-hashes.json").write_text(
            json.dumps(
                [
                    {
                        "path": "../escape.txt",
                        "sha256": "sha256:" + ("1" * 64),
                        "bytes": 10,
                    }
                ]
            ),
            encoding="utf-8",
        )

    with pytest.raises(review_packet_diff.ReviewPacketDiffError, match="unsafe"):
        review_packet_diff.compare_packets(old_packet, new_packet)


def test_review_packet_diff_gate_rejects_removed_artifacts(tmp_path: Path) -> None:
    old_packet = tmp_path / "old"
    new_packet = tmp_path / "new"
    old_packet.mkdir()
    new_packet.mkdir()
    _write_packet_artifacts(
        old_packet,
        {"INDEX.md": "# packet\n", "removed.txt": "removed\n"},
    )
    _write_packet_artifacts(new_packet, {"INDEX.md": "# packet\n"})

    diff = review_packet_diff.compare_packets(old_packet, new_packet, require_hashes=True)

    with pytest.raises(review_packet_diff.ReviewPacketDiffError, match="removed"):
        review_packet_diff.validate_packet_diff_gate(diff)


def test_review_packet_diff_gate_requires_artifact_hashes(tmp_path: Path) -> None:
    old_packet = tmp_path / "old"
    new_packet = tmp_path / "new"
    old_packet.mkdir()
    new_packet.mkdir()
    old_packet.joinpath("INDEX.md").write_text("# old\n", encoding="utf-8")
    new_packet.joinpath("INDEX.md").write_text("# new\n", encoding="utf-8")

    with pytest.raises(review_packet_diff.ReviewPacketDiffError, match="missing"):
        review_packet_diff.compare_packets(old_packet, new_packet, require_hashes=True)


def test_review_packet_diff_gate_recomputes_hashes_and_detects_unlisted(
    tmp_path: Path,
) -> None:
    packet = tmp_path / "packet"
    packet.mkdir()
    _write_packet_artifacts(packet, {"INDEX.md": "# packet\n"})
    packet.joinpath("INDEX.md").write_text("# tampered\n", encoding="utf-8")

    with pytest.raises(review_packet_diff.ReviewPacketDiffError, match="hash mismatch"):
        review_packet_diff.collect_packet_artifacts(packet, require_hashes=True)

    _write_packet_artifacts(packet, {"INDEX.md": "# packet\n"})
    packet.joinpath("unlisted.txt").write_text("surprise\n", encoding="utf-8")

    with pytest.raises(review_packet_diff.ReviewPacketDiffError, match="unlisted"):
        review_packet_diff.collect_packet_artifacts(packet, require_hashes=True)

    benign_packet = tmp_path / "benign-packet"
    benign_packet.mkdir()
    _write_packet_artifacts(benign_packet, {"README.md": "`ITHILDIN_ADMIN_TOKEN=...`\n"})
    review_packet_diff.collect_packet_artifacts(benign_packet, require_hashes=True)

    leak_packet = tmp_path / "leak-packet"
    leak_packet.mkdir()
    _write_packet_artifacts(leak_packet, {"leak.md": "ITHILDIN_ADMIN_TOKEN=real-token\n"})
    with pytest.raises(review_packet_diff.ReviewPacketDiffError, match="secret-like"):
        review_packet_diff.collect_packet_artifacts(leak_packet, require_hashes=True)


def test_review_packet_diff_rejects_malformed_sha256(tmp_path: Path) -> None:
    packet = tmp_path / "packet"
    packet.mkdir()
    packet.joinpath("artifact-hashes.json").write_text(
        json.dumps([{"path": "INDEX.md", "sha256": "sha256:not-a-digest", "bytes": 1}]),
        encoding="utf-8",
    )

    with pytest.raises(review_packet_diff.ReviewPacketDiffError, match="sha256"):
        review_packet_diff.collect_packet_artifacts(packet)


def _write_packet_artifacts(packet: Path, files: dict[str, str]) -> None:
    artifacts = []
    for relative, content in files.items():
        path = packet / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        encoded = content.encode("utf-8")
        artifacts.append(
            {
                "path": relative,
                "sha256": "sha256:" + hashlib.sha256(encoded).hexdigest(),
                "bytes": len(encoded),
            }
        )
    packet.joinpath("artifact-hashes.json").write_text(
        json.dumps(artifacts),
        encoding="utf-8",
    )


def test_review_packet_diff_doc_and_target_are_wired() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    doc = Path("docs/codex/review-packet-diff.md").read_text(encoding="utf-8")
    review_packet = Path("docs/codex/v0.2-review-packet.md").read_text(encoding="utf-8")
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")

    assert "review-packet-diff:" in makefile
    assert "review-packet-diff-gate:" in makefile
    assert "make review-packet-diff OLD=... NEW=..." in readme
    assert "make review-packet-diff-gate OLD=... NEW=..." in readme
    assert "artifact-hashes.json" in doc
    assert "make review-packet-diff-gate OLD=old-packet NEW=new-packet" in doc
    assert "make review-packet-diff OLD=old-packet NEW=new-packet" in review_packet
    assert "make review-packet-diff-gate OLD=old-packet NEW=new-packet" in review_packet
    assert "make review-packet-diff OLD=old-packet NEW=new-packet" in reproduction_map
    assert "make review-packet-diff-gate OLD=old-packet NEW=new-packet" in reproduction_map
    assert "103 - Review packet diff command | Done" in backlog
    assert "125 - Review packet diff gate v2 | Done" in backlog
    assert "docs/codex/review-packet-diff.md" in review_docs.REVIEW_DOCS


def test_packet_redaction_scan_passes_clean_packet(tmp_path: Path) -> None:
    packet = tmp_path / "packet"
    packet.mkdir()
    packet.joinpath("INDEX.md").write_text("# clean\n", encoding="utf-8")
    packet.joinpath("release-evidence.json").write_text(
        '{"schema":{"secret_free":true}}\n',
        encoding="utf-8",
    )

    result = packet_redaction_scan.scan_packet_paths([packet])

    assert result.scanned_files == 2
    assert result.findings == []
    assert "Packet redaction scan passed." in packet_redaction_scan.render_scan_result(result)


@pytest.mark.parametrize(
    ("filename", "content", "reason"),
    [
        ("private.pem", "not actually read\n", "forbidden runtime file"),
        ("INDEX.md", "-----BEGIN PRIVATE KEY-----\nabc\n", "private_key"),
        ("INDEX.md", "ITHILDIN_ADMIN_TOKEN=ithildin_admin_real_token\n", "admin_token"),
        ("INDEX.md", "dev-admin-token-change-me\n", "sample_admin_token"),
    ],
)
def test_packet_redaction_scan_rejects_secret_material(
    tmp_path: Path, filename: str, content: str, reason: str
) -> None:
    packet = tmp_path / "packet"
    packet.mkdir()
    packet.joinpath(filename).write_text(content, encoding="utf-8")

    result = packet_redaction_scan.scan_packet_paths([packet])

    assert result.findings
    assert any(reason in finding.reason for finding in result.findings)


def test_packet_redaction_scan_doc_target_and_bundle_are_wired() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    doc = Path("docs/codex/packet-redaction-scanner.md").read_text(encoding="utf-8")
    review_packet = Path("docs/codex/v0.2-review-packet.md").read_text(encoding="utf-8")
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(encoding="utf-8")
    bundle_script = Path("scripts/review_packet_bundle.py").read_text(encoding="utf-8")
    consolidated_script = Path("scripts/consolidate_review_packet.py").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")

    assert "packet-redaction-scan:" in makefile
    assert "$(MAKE) packet-redaction-scan" in makefile
    assert "make packet-redaction-scan" in readme
    assert "make packet-redaction-scan" in doc
    assert "make packet-redaction-scan" in review_packet
    assert "packet-redaction-scan.txt" in reproduction_map
    assert "packet-redaction-scan.txt" in bundle_script
    assert "Packet Redaction Scan" in consolidated_script
    assert "127 - Secrets hygiene and packet redaction scanner | Done" in backlog
    assert "docs/codex/packet-redaction-scanner.md" in review_docs.REVIEW_DOCS


def test_determinism_gate_detects_forbidden_patterns(tmp_path: Path) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    sleep_call = "time." + "sleep(1)"
    random_call = "random." + "random()"
    tests_dir.joinpath("test_bad.py").write_text(
        f"import time\nimport random\ndef test_bad():\n    {sleep_call}\n    {random_call}\n",
        encoding="utf-8",
    )

    findings = test_determinism_gate._scan_test_patterns(tests_dir)

    assert {finding.reason for finding in findings} == {"sleep_call", "unseeded_random"}


def test_determinism_gate_doc_and_target_are_wired() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    doc = Path("docs/codex/test-determinism-gate.md").read_text(encoding="utf-8")
    review_packet = Path("docs/codex/v0.2-review-packet.md").read_text(encoding="utf-8")
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")

    assert "determinism-check:" in makefile
    assert "release-check: release-context manifest-lock-check release-guardrails" in makefile
    assert (
        "determinism-check adversarial-corpus-check resource-limit-check "
        "demo-scenario-pack evidence-contracts-check policy-test" in makefile
    )
    assert "make determinism-check" in readme
    assert "make determinism-check" in doc
    assert "make determinism-check" in review_packet
    assert "make determinism-check" in reproduction_map
    assert "128 - Test isolation and determinism gate | Done" in backlog
    assert "docs/codex/test-determinism-gate.md" in review_docs.REVIEW_DOCS


def test_release_evidence_records_attached_release_check_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    transcript = tmp_path / "release-check.txt"
    transcript.write_text("returncode=0\npassed\n", encoding="utf-8")
    current_commit = release_evidence._git(["rev-parse", "HEAD"])
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "release_evidence.py",
            "--release-check-transcript",
            transcript.as_posix(),
            "--release-check-observed-status",
            "passed",
            "--release-check-commit",
            current_commit,
        ],
    )

    result = release_evidence.main()

    assert result == 0
    output = capsys.readouterr().out
    assert '"gate_executed_by_release_packet": false' in output
    assert '"gate_status": "not_run"' in output
    assert '"attached_transcript_exists": true' in output
    assert '"attached_transcript_status": "passed"' in output
    assert f'"attached_transcript_commit": "{current_commit}"' in output
    assert '"schema_version": "v0.3-prep-release-evidence-v1"' in output


def test_release_evidence_schema_validator_accepts_minimal_snapshot() -> None:
    payload = _minimal_release_evidence_payload()

    release_evidence.validate_release_evidence_snapshot(payload)


def test_release_evidence_rejects_passing_transcript_without_returncode_zero(
    tmp_path: Path,
) -> None:
    payload = _minimal_release_evidence_payload()
    transcript = tmp_path / "release-check.txt"
    transcript.write_text("passed\n", encoding="utf-8")
    payload["release_check"] = {
        "gate_executed_by_release_packet": False,
        "gate_status": "not_run",
        "attached_transcript_exists": True,
        "attached_transcript_status": "passed",
        "attached_transcript_commit": "abc123",
        "attached_transcript_path": transcript.as_posix(),
    }

    with pytest.raises(
        release_evidence.ReleaseEvidenceSchemaError,
        match="release-check transcript did not pass",
    ):
        release_evidence.validate_release_evidence_snapshot(payload)


def test_release_evidence_rejects_required_unverified_signed_manifest_lock() -> None:
    payload = _minimal_release_evidence_payload()
    manifest_lock = cast(dict[str, Any], payload["manifest_lock"])
    signature = cast(dict[str, Any], manifest_lock["signature"])
    signature["required"] = True
    signature["verified"] = False

    with pytest.raises(
        release_evidence.ReleaseEvidenceSchemaError,
        match="required signed manifest lock is not verified",
    ):
        release_evidence.validate_release_evidence_snapshot(payload)


def test_release_evidence_schema_validator_rejects_missing_key() -> None:
    payload = _minimal_release_evidence_payload()
    del payload["tools"]

    with pytest.raises(
        release_evidence.ReleaseEvidenceSchemaError,
        match="missing required top-level key: tools",
    ):
        release_evidence.validate_release_evidence_snapshot(payload)


def test_release_evidence_schema_validator_rejects_secret_marker() -> None:
    payload = _minimal_release_evidence_payload()
    payload["deferred_boundaries"] = ["contains dev-admin-token-change-me marker"]

    with pytest.raises(
        release_evidence.ReleaseEvidenceSchemaError,
        match="secret-like marker",
    ):
        release_evidence.validate_release_evidence_snapshot(payload)


def test_release_evidence_validate_file_cli(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    evidence_path = tmp_path / "release-evidence.json"
    evidence_path.write_text(
        json.dumps(_minimal_release_evidence_payload()),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["release_evidence.py", "--validate-file", evidence_path.as_posix()],
    )

    result = release_evidence.main()

    assert result == 0
    assert "Release evidence schema validation passed." in capsys.readouterr().out


def test_release_evidence_schema_doc_and_target_are_wired() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    doc = Path("docs/codex/release-evidence-schema.md").read_text(encoding="utf-8")
    review_packet = Path("docs/codex/v0.2-review-packet.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(encoding="utf-8")

    assert "release-evidence-validate:" in makefile
    assert "release-evidence-gate:" in makefile
    assert (
        "release-check: release-context manifest-lock-check release-guardrails "
        "release-evidence-gate"
    ) in makefile
    assert "make release-evidence-gate" in readme
    assert "make release-evidence-validate FILE=..." in readme
    assert "v0.3-prep-release-evidence-v1" in doc
    assert "Task 124 promotes this validation" in doc
    assert "make release-evidence-validate FILE=release-evidence.json" in review_packet
    assert "Task 102 adds" in matrix
    assert "docs/codex/release-evidence-schema.md" in review_docs.REVIEW_DOCS


def _minimal_release_evidence_payload() -> dict[str, object]:
    return {
        "schema": {
            "schema_version": release_evidence.RELEASE_EVIDENCE_SCHEMA_VERSION,
            "stable_top_level_keys": list(
                release_evidence.RELEASE_EVIDENCE_REQUIRED_TOP_LEVEL_KEYS
            ),
            "secret_free": True,
        },
        "generated_at": "2026-05-30T00:00:00+00:00",
        "repo": {
            "repo_root": "/tmp/ithildin",
            "current_working_directory": "/tmp/ithildin",
            "project_markers": {},
        },
        "git": {"commit": "abc123", "branch": "main", "dirty": False},
        "release_check": {
            "gate_executed_by_release_packet": False,
            "gate_status": "not_run",
            "attached_transcript_exists": False,
            "attached_transcript_status": "not_run",
            "attached_transcript_commit": None,
            "attached_transcript_path": None,
        },
        "review_docs": [
            {
                "path": "README.md",
                "sha256": "sha256:" + ("0" * 64),
                "bytes": 1,
            }
        ],
        "manifest_lock": {
            "path": "tool-manifests.lock.json",
            "required": True,
            "current": True,
            "signature": {
                "required": False,
                "verified": False,
                "key_id": None,
                "lock_sha256": None,
            },
        },
        "docs_site": {},
        "tools": {"count": 0, "names": []},
        "policy": {},
        "principals": {},
        "workspaces": {},
        "filesystem": {
            "platform": {
                "system": "Darwin",
                "profile": "macos",
                "release": "23.0.0",
                "machine": "arm64",
            },
            "python": {"version": "3.12.13"},
            "capabilities": {
                "o_no_follow_available": True,
                "symlink_supported": True,
                "hardlink_supported": True,
                "case_sensitive": False,
            },
            "support": {
                "status": "supported",
                "local_preview_security_supported": True,
            },
            "probe": {
                "uses_temporary_directory": True,
                "touches_workspace": False,
            },
        },
        "storage": {},
        "telemetry": {},
        "security": {},
        "audit": {},
        "audit_signing": {},
        "deferred_boundaries": [],
    }


def test_release_evidence_schema_validator_requires_filesystem_capabilities() -> None:
    payload = _minimal_release_evidence_payload()
    filesystem = payload["filesystem"]
    assert isinstance(filesystem, dict)
    del filesystem["capabilities"]

    with pytest.raises(
        release_evidence.ReleaseEvidenceSchemaError,
        match="capability evidence",
    ):
        release_evidence.validate_release_evidence_snapshot(payload)


def test_release_evidence_schema_validator_requires_o_no_follow_evidence() -> None:
    payload = _minimal_release_evidence_payload()
    filesystem = payload["filesystem"]
    assert isinstance(filesystem, dict)
    capabilities = filesystem["capabilities"]
    assert isinstance(capabilities, dict)
    del capabilities["o_no_follow_available"]

    with pytest.raises(
        release_evidence.ReleaseEvidenceSchemaError,
        match="o_no_follow_available",
    ):
        release_evidence.validate_release_evidence_snapshot(payload)


def _write_project_markers(root: Path) -> None:
    directory_markers = {"apps/api", "apps/mcp-server"}
    for marker in review_packet_bundle.PROJECT_MARKERS:
        path = root / marker
        if marker in directory_markers:
            path.mkdir(parents=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("", encoding="utf-8")

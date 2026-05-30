from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

from scripts import (
    consolidate_review_packet,
    internal_review_packet,
    release_evidence,
    release_guardrails,
    release_packet,
    review_docs,
    review_packet_bundle,
    review_packet_diff,
    reviewer_findings,
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
    manifest_doc = Path("docs/codex/v0.3-milestone-manifest.md").read_text(
        encoding="utf-8"
    )
    manifest = json.loads(
        Path("docs/codex/v0.3-milestone-manifest.json").read_text(encoding="utf-8")
    )
    readme = Path("README.md").read_text(encoding="utf-8")
    planning_seed = Path("docs/codex/v0.2-planning-seed.md").read_text(
        encoding="utf-8"
    )

    task_ids = [milestone["id"] for milestone in manifest["milestones"]]
    assert task_ids == [f"{index:03d}" for index in range(85, 113)]
    assert manifest["runtime_boundary"] == "v0.1 local-preview"
    assert "shell execution" in manifest["deferred_boundaries"]
    assert "trust-boundary regression" in manifest["stop_conditions"]
    assert (
        "external source-review closure"
        in manifest["subagent_policy"]["not_authorized_for"]
    )
    assert "v0.3-milestone-manifest.json" in manifest_doc
    assert "v0.3-milestone-manifest.md" in readme
    assert "v0.3-milestone-manifest.md" in planning_seed
    assert "docs/codex/v0.3-milestone-manifest.md" in review_docs.REVIEW_DOCS


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
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(
        encoding="utf-8"
    )
    makefile = Path("Makefile").read_text(encoding="utf-8")
    for target in [
        "release-check",
        "release-evidence",
        "release-packet",
        "review-candidate",
        "internal-review-packet",
        "signed-evidence-demo",
        "filesystem-contract-check",
        "reviewer-findings-check",
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
        "$(MAKE) negative-review-transcripts",
        "$(MAKE) review-packet-bundle",
        "$(MAKE) review-packet-consolidated",
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
        "artifact-hashes.json",
        "git-summary.txt",
    ]:
        bundle_dir.joinpath(path).write_text(f"# {path}\n", encoding="utf-8")
    for path in [
        "README.md",
        "docs/codex/v0.2-external-review-prompt.md",
        "docs/codex/reviewer-reproduction-map.md",
        "docs/codex/v0.2-review-packet.md",
        "docs/codex/v0.2-review-response-and-rc-cleanup.md",
        "docs/codex/v0.2-planning-seed.md",
        "docs/codex/v0.1-security-test-matrix.md",
        "docs/codex/filesystem-executor-contract.md",
        "docs/codex/evidence-contracts.md",
        "docs/codex/threat-model-and-non-goals.md",
        "docs/codex/negative-review-recipes.md",
        "docs/codex/source-review-closure-matrix.md",
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
        repo_root
        / "var/review-packets/v0.2/signed-evidence-demo/SIGNED_EVIDENCE_DEMO.md"
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
        output_dir.joinpath("consolidated-attachment-hashes.json").read_text(
            encoding="utf-8"
        )
    )
    hash_paths = {entry["path"] for entry in hashes}
    assert hash_paths == set(consolidate_review_packet.ATTACHMENT_FILES)
    assert all(str(entry["sha256"]).startswith("sha256:") for entry in hashes)
    assert "Negative Review Transcripts" in output_dir.joinpath(
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
    prompt = Path("docs/codex/v0.2-external-review-prompt.md").read_text(
        encoding="utf-8"
    )

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
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(
        encoding="utf-8"
    )

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
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(
        encoding="utf-8"
    )

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
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(
        encoding="utf-8"
    )
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
    contract = Path("docs/codex/patch-apply-state-machine.md").read_text(
        encoding="utf-8"
    )
    readme = Path("README.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(
        encoding="utf-8"
    )

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
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(
        encoding="utf-8"
    )

    for required in [
        "GET only",
        "exact allowlist",
        "no caller-supplied headers",
        "malformed ports",
        "IDNA",
        "resolves the destination twice",
        "Redirects repeat",
        "connect to one of the validated IPs",
        "proxy",
        "response bodies",
        "not a network sandbox",
    ]:
        assert required in contract
    assert "http-executor-contract.md" in readme
    assert "docs/codex/http-executor-contract.md" in review_docs.REVIEW_DOCS
    assert "Task 093 HTTP executor contract" in matrix


def test_executor_contract_set_indexes_review_surfaces() -> None:
    contract = Path("docs/codex/executor-contract-set.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    review_packet = Path("docs/codex/v0.2-review-packet.md").read_text(
        encoding="utf-8"
    )
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(
        encoding="utf-8"
    )
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(
        encoding="utf-8"
    )

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
    review_packet = Path("docs/codex/v0.2-review-packet.md").read_text(
        encoding="utf-8"
    )
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(
        encoding="utf-8"
    )
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(
        encoding="utf-8"
    )

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


def test_evidence_contracts_define_versioning_policy() -> None:
    contracts = Path("docs/codex/evidence-contracts.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(
        encoding="utf-8"
    )

    for required in [
        "Contract Versioning",
        'format_version: "1"',
        'version: "1"',
        "Stable v0.3-prep evidence fields",
        "Preview-only evidence fields",
        "requires a trusted local public key file",
        "new format version",
    ]:
        assert required in contracts
    assert "Task 095 evidence-contract versioning" in matrix
    assert "SUB-001" in matrix


def test_policy_parity_harness_is_documented_and_gated() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(
        encoding="utf-8"
    )
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
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(
        encoding="utf-8"
    )
    doc = Path("docs/codex/opa-parity-decision.md").read_text(encoding="utf-8")

    for required in [
        "YAML remains the canonical local-preview policy engine",
        "OPA remains an optional sidecar/evidence prototype",
        "make policy-test",
        "make policy-parity",
        "not a semantic parity claim",
    ]:
        assert required in doc
    assert "opa-parity-decision.md" in readme
    assert "OPA Parity Decision" in release
    assert "097 - OPA parity decision point | Done" in backlog
    assert "Task 097 keeps YAML canonical" in matrix
    assert "docs/codex/opa-parity-decision.md" in review_docs.REVIEW_DOCS


def test_mcp_ingress_bypass_audit_is_documented() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(
        encoding="utf-8"
    )
    doc = Path("docs/codex/mcp-ingress-bypass-audit.md").read_text(encoding="utf-8")

    for required in [
        "fixed local MCP principal",
        "MCP callers cannot spoof an admin principal",
        "Unknown tools called through MCP are denied",
        "policy.evaluated",
        "remote MCP remains deferred",
    ]:
        assert required in doc
    assert "mcp-ingress-bypass-audit.md" in readme
    assert "098 - MCP ingress bypass audit | Done" in backlog
    assert "Task 098 tests fixed-principal audit evidence" in matrix
    assert "docs/codex/mcp-ingress-bypass-audit.md" in review_docs.REVIEW_DOCS


def test_review_console_assurance_is_documented() -> None:
    app = Path("apps/ui/src/App.tsx").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(
        encoding="utf-8"
    )
    doc = Path("docs/codex/review-console-assurance.md").read_text(encoding="utf-8")

    for required in [
        "approval scope hash",
        "policy reason",
        "/patch-apply-diagnostics",
        "warning banners",
        "does not add repair",
    ]:
        assert required in doc
    for ui_marker in [
        "PatchApplyDiagnostics",
        "/patch-apply-diagnostics",
        "Patch Apply Diagnostics",
        "copyApprovalEvidence",
        "approval_scope_hash",
    ]:
        assert ui_marker in app
    assert "review-console-assurance.md" in readme
    assert "099 - Review-console approval evidence clarity | Done" in backlog
    assert "100 - Review-console failure-state and trust-status UX | Done" in backlog
    assert "Tasks 099-100 expose copyable approval binding evidence" in matrix
    assert "docs/codex/review-console-assurance.md" in review_docs.REVIEW_DOCS


def test_negative_transcript_expansion_is_documented() -> None:
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(
        encoding="utf-8"
    )
    recipes = Path("docs/codex/negative-review-recipes.md").read_text(encoding="utf-8")

    for required in [
        "Manifest Lock Tamper Denial",
        "Policy Parity Mismatch Detection",
        "Patch Apply Ambiguous Diagnostics",
    ]:
        assert required in recipes
    assert "101 - Negative transcript expansion | Done" in backlog
    assert "Task 101 expands observed transcripts" in matrix


def test_reviewer_finding_template_has_required_fields() -> None:
    template = Path("docs/codex/reviewer-finding-template.md").read_text(
        encoding="utf-8"
    )
    prompt = Path("docs/codex/v0.2-external-review-prompt.md").read_text(
        encoding="utf-8"
    )
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(
        encoding="utf-8"
    )

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
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(
        encoding="utf-8"
    )

    assert "make reviewer-findings-check" in intake
    assert "reviewer-findings-check:" in makefile
    assert (
        "release-check: release-context manifest-lock-check release-guardrails "
        "reviewer-findings-check filesystem-contract-check"
    ) in makefile
    assert "open critical/high findings" in intake
    assert "reviewer-finding-intake.md" in review_packet
    assert "reviewer-finding-intake.md" in reproduction_map
    assert "docs/codex/reviewer-finding-intake.md" in review_docs.REVIEW_DOCS


def test_release_check_enforces_filesystem_contract_check() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(
        encoding="utf-8"
    )

    assert (
        "release-check: release-context manifest-lock-check release-guardrails "
        "reviewer-findings-check filesystem-contract-check"
    ) in makefile
    assert "Task 091 release-check filesystem-contract-check gate" in matrix


def test_internal_ai_review_workflow_and_packet_are_validated(tmp_path: Path) -> None:
    workflow = Path("docs/codex/internal-ai-review-workflow.md").read_text(encoding="utf-8")
    prompt = Path("docs/codex/v0.2-review-packet.md").read_text(encoding="utf-8")
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(
        encoding="utf-8"
    )

    for required in [
        "not an independent external audit",
        "make internal-review-packet",
        "Patch apply approval binding",
        "HTTP fetch SSRF",
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


def test_autonomous_sprint_guardrails_are_linked_and_validated() -> None:
    guardrails = Path("docs/codex/autonomous-sprint-guardrails.md").read_text(
        encoding="utf-8"
    )
    readme = Path("README.md").read_text(encoding="utf-8")
    review_packet = Path("docs/codex/v0.2-review-packet.md").read_text(encoding="utf-8")
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(
        encoding="utf-8"
    )

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
    demo_summary = (
        tmp_path
        / "var/review-packets/v0.2/signed-evidence-demo/SIGNED_EVIDENCE_DEMO.md"
    )
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
        return review_packet_bundle.CommandOutput(
            command=command,
            returncode=0,
            stdout='{"secret_free": true}\n' if "release_evidence.py" in command else "ok\n",
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
    assert result.path.joinpath("release-packet.md").exists()
    assert result.path.joinpath("release-packet.json").exists()
    assert result.path.joinpath("review-doc-hashes.json").exists()
    assert result.path.joinpath("artifact-hashes.json").exists()
    assert result.path.joinpath("git-summary.txt").exists()
    assert result.path.joinpath("docs/README.md").exists()
    assert result.path.joinpath("docs/docs/codex/v0.2-review-packet.md").exists()
    assert result.path.joinpath("signed-evidence-demo/SIGNED_EVIDENCE_DEMO.md").exists()
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
    assert "release-packet.md" in artifact_paths
    assert "release-packet.json" in artifact_paths
    assert "review-doc-hashes.json" in artifact_paths
    assert "docs/README.md" in artifact_paths
    assert "signed-evidence-demo/SIGNED_EVIDENCE_DEMO.md" in artifact_paths
    assert "negative-review-transcripts/NEGATIVE_REVIEW_TRANSCRIPTS.md" in artifact_paths
    bundle_paths = [path.as_posix() for path in result.path.rglob("*")]
    assert not any("/.env" in path for path in bundle_paths)
    assert not any("/var/keys/" in path for path in bundle_paths)
    assert "review-doc-hashes.json" in result.path.joinpath("INDEX.md").read_text(
        encoding="utf-8"
    )
    assert "artifact-hashes.json" in result.path.joinpath("INDEX.md").read_text(
        encoding="utf-8"
    )
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


def test_review_packet_diff_doc_and_target_are_wired() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    doc = Path("docs/codex/review-packet-diff.md").read_text(encoding="utf-8")
    review_packet = Path("docs/codex/v0.2-review-packet.md").read_text(
        encoding="utf-8"
    )
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(
        encoding="utf-8"
    )
    backlog = Path("docs/codex/implementation-backlog.md").read_text(encoding="utf-8")

    assert "review-packet-diff:" in makefile
    assert "make review-packet-diff OLD=... NEW=..." in readme
    assert "artifact-hashes.json" in doc
    assert "make review-packet-diff OLD=old-packet NEW=new-packet" in review_packet
    assert "make review-packet-diff OLD=old-packet NEW=new-packet" in reproduction_map
    assert "103 - Review packet diff command | Done" in backlog
    assert "docs/codex/review-packet-diff.md" in review_docs.REVIEW_DOCS


def test_release_evidence_records_attached_release_check_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    transcript = tmp_path / "release-check.txt"
    transcript.write_text("passed\n", encoding="utf-8")
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
            "abc123",
        ],
    )

    result = release_evidence.main()

    assert result == 0
    output = capsys.readouterr().out
    assert '"gate_executed_by_release_packet": false' in output
    assert '"gate_status": "not_run"' in output
    assert '"attached_transcript_exists": true' in output
    assert '"attached_transcript_status": "passed"' in output
    assert '"attached_transcript_commit": "abc123"' in output
    assert '"schema_version": "v0.3-prep-release-evidence-v1"' in output


def test_release_evidence_schema_validator_accepts_minimal_snapshot() -> None:
    payload = _minimal_release_evidence_payload()

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
    review_packet = Path("docs/codex/v0.2-review-packet.md").read_text(
        encoding="utf-8"
    )
    matrix = Path("docs/codex/source-review-closure-matrix.md").read_text(
        encoding="utf-8"
    )

    assert "release-evidence-validate:" in makefile
    assert "make release-evidence-validate FILE=..." in readme
    assert "v0.3-prep-release-evidence-v1" in doc
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
            "attached_transcript_exists": True,
            "attached_transcript_status": "passed",
            "attached_transcript_commit": "abc123",
            "attached_transcript_path": "release-check.txt",
        },
        "review_docs": [
            {
                "path": "README.md",
                "sha256": "sha256:" + ("0" * 64),
                "bytes": 1,
            }
        ],
        "manifest_lock": {},
        "docs_site": {},
        "tools": {"count": 0, "names": []},
        "policy": {},
        "principals": {},
        "workspaces": {},
        "storage": {},
        "telemetry": {},
        "security": {},
        "audit": {},
        "audit_signing": {},
        "deferred_boundaries": [],
    }


def _write_project_markers(root: Path) -> None:
    directory_markers = {"apps/api", "apps/mcp-server"}
    for marker in review_packet_bundle.PROJECT_MARKERS:
        path = root / marker
        if marker in directory_markers:
            path.mkdir(parents=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("", encoding="utf-8")

from __future__ import annotations

from pathlib import Path

from scripts.build_docs_site import DEFAULT_DOCS, build_site, markdown_to_html


def test_markdown_to_html_renders_basic_blocks() -> None:
    html = markdown_to_html(
        """# Title

Short `code` paragraph.

- One
- Two

```sh
make test
```
"""
    )

    assert "<h1>Title</h1>" in html
    assert "<code>code</code>" in html
    assert "<li>One</li>" in html
    assert "make test" in html


def test_build_site_creates_index_and_pages(tmp_path: Path) -> None:
    doc = tmp_path / "README.md"
    doc.write_text("# Demo Docs\n\nHello.\n", encoding="utf-8")
    output_dir = tmp_path / "site"

    pages = build_site(output_dir, [doc])

    assert pages[0].title == "Demo Docs"
    assert (output_dir / "index.html").exists()
    assert (output_dir / pages[0].output_name).read_text(encoding="utf-8").startswith("<!doctype")
    assert "Demo Docs" in (output_dir / "index.html").read_text(encoding="utf-8")


def test_default_docs_include_v02_review_packet() -> None:
    assert "docs/codex/v0.2-review-packet.md" in DEFAULT_DOCS
    assert "docs/codex/v0.2-review-response-and-rc-cleanup.md" in DEFAULT_DOCS
    assert "docs/codex/v0.2-external-review-prompt.md" in DEFAULT_DOCS
    assert "docs/codex/v0.3-review-packet.md" in DEFAULT_DOCS
    assert "docs/codex/v0.3-external-review-prompt.md" in DEFAULT_DOCS
    assert "docs/codex/external-review-intake-and-closure.md" in DEFAULT_DOCS
    assert "docs/codex/v0.3-boundary-decision.md" in DEFAULT_DOCS
    assert "docs/codex/v0.3-milestone-manifest.md" in DEFAULT_DOCS
    assert "docs/codex/v0.4-milestone-manifest.md" in DEFAULT_DOCS
    assert "docs/codex/v0.4-gating-overlay.md" in DEFAULT_DOCS
    assert "docs/codex/patch-apply-state-machine.md" in DEFAULT_DOCS
    assert "docs/codex/executor-contract-set.md" in DEFAULT_DOCS
    assert "docs/codex/http-executor-contract.md" in DEFAULT_DOCS
    assert "docs/codex/negative-review-recipes.md" in DEFAULT_DOCS
    assert "docs/codex/release-evidence-schema.md" in DEFAULT_DOCS
    assert "docs/codex/review-packet-diff.md" in DEFAULT_DOCS
    assert "docs/codex/packet-redaction-scanner.md" in DEFAULT_DOCS
    assert "docs/codex/test-determinism-gate.md" in DEFAULT_DOCS
    assert "docs/codex/registry-fail-closed-suite.md" in DEFAULT_DOCS
    assert "docs/codex/release-guardrail-expansion.md" in DEFAULT_DOCS
    assert "docs/codex/v0.8-roadmap-prompt.md" in DEFAULT_DOCS
    assert "docs/codex/v0.9-lane-closure-summary.md" in DEFAULT_DOCS
    assert "docs/codex/v0.9-next-read-only-capability-seed.md" in DEFAULT_DOCS
    assert "docs/codex/agent-run-observability-and-sandbox-roadmap.md" in DEFAULT_DOCS
    assert "docs/codex/agent-run-model-contract.md" in DEFAULT_DOCS
    assert "docs/codex/agent-run-evidence-contract.md" in DEFAULT_DOCS
    assert "docs/codex/agent-run-evidence-export-design.md" in DEFAULT_DOCS
    assert "docs/codex/agent-run-evidence-export-implementation-plan.md" in DEFAULT_DOCS
    assert "docs/codex/agent-run-evidence-export-implementation.md" in DEFAULT_DOCS
    assert "docs/codex/agent-run-timeline-readiness-gate.md" in DEFAULT_DOCS
    assert "docs/codex/agent-run-evidence-readiness-gate.md" in DEFAULT_DOCS
    assert "docs/codex/agent-run-operations-readiness-gate.md" in DEFAULT_DOCS
    assert "docs/codex/operator-workbench-readiness.md" in DEFAULT_DOCS
    assert "docs/codex/operator-demo-walkthrough.md" in DEFAULT_DOCS
    assert "docs/codex/operator-action-states-design.md" in DEFAULT_DOCS
    assert "docs/codex/dashboard-evidence-review-checklist.md" in DEFAULT_DOCS
    assert "docs/codex/sandbox-workspace-boundary-contract.md" in DEFAULT_DOCS
    assert "docs/codex/siem-shaped-evidence-design.md" in DEFAULT_DOCS
    assert "docs/codex/data-classification-design.md" in DEFAULT_DOCS
    assert "docs/codex/control-mapping-design.md" in DEFAULT_DOCS
    assert "docs/codex/incident-reconstruction-guide.md" in DEFAULT_DOCS
    assert "docs/codex/compliance-mapping-architecture.md" in DEFAULT_DOCS
    assert "docs/codex/observability-readiness-gate.md" in DEFAULT_DOCS
    assert "docs/codex/control-mapping-readiness-gate.md" in DEFAULT_DOCS
    assert "docs/codex/capability-proposals/git-show-ref-summary.md" in DEFAULT_DOCS
    assert "docs/codex/capability-implementation-plans/git-show-ref-summary.md" in DEFAULT_DOCS
    assert "docs/codex/capability-proposals/git-show-tag-metadata.md" in DEFAULT_DOCS
    assert "docs/codex/capability-implementation-plans/git-show-tag-metadata.md" in DEFAULT_DOCS
    assert "docs/codex/v0.9-git-tag-metadata-implementation.md" in DEFAULT_DOCS
    assert "docs/codex/v0.9-git-tag-metadata-source-review.md" in DEFAULT_DOCS
    assert "docs/codex/v0.9-git-tag-metadata-internal-review.md" in DEFAULT_DOCS
    assert "docs/codex/v0.9-git-ref-summary-proposal-review.md" in DEFAULT_DOCS
    assert "docs/codex/read-only-local-metadata-contract.md" in DEFAULT_DOCS
    assert "docs/codex/metadata-privacy-policy.md" in DEFAULT_DOCS
    assert "docs/codex/v3-next-capability-candidate-evaluation-2.md" in DEFAULT_DOCS
    assert "docs/codex/project-release-summary-fixture-plan.md" in DEFAULT_DOCS
    assert "docs/codex/project-release-summary-negative-transcripts.md" in DEFAULT_DOCS
    assert "docs/codex/v3-project-release-summary-implementation.md" in DEFAULT_DOCS
    assert "docs/codex/project-release-summary-implementation-transition.md" in DEFAULT_DOCS
    assert "docs/codex/v3-project-release-summary-source-review.md" in DEFAULT_DOCS
    assert "docs/codex/v3-project-ci-summary-selection.md" in DEFAULT_DOCS
    assert "docs/codex/capability-proposals/project-ci-summary.md" in DEFAULT_DOCS
    assert "docs/codex/capability-implementation-plans/project-ci-summary.md" in DEFAULT_DOCS
    assert "docs/codex/v3-project-risk-summary-selection.md" in DEFAULT_DOCS
    assert "docs/codex/capability-proposals/project-risk-summary.md" in DEFAULT_DOCS
    assert "docs/codex/capability-implementation-plans/project-risk-summary.md" in DEFAULT_DOCS
    assert "docs/codex/v3-project-risk-summary-implementation.md" in DEFAULT_DOCS
    assert "docs/codex/project-risk-summary-fixture-plan.md" in DEFAULT_DOCS
    assert "docs/codex/project-risk-summary-negative-transcripts.md" in DEFAULT_DOCS
    assert "docs/codex/v3-project-risk-summary-source-review.md" in DEFAULT_DOCS
    assert "docs/codex/read-only-metadata-capability-checklist.md" in DEFAULT_DOCS
    assert "docs/codex/read-only-capability-source-review-template.md" in DEFAULT_DOCS
    assert "docs/codex/v1.0-rc-roadmap.md" in DEFAULT_DOCS
    assert "docs/codex/v1.0-rc-status.md" in DEFAULT_DOCS
    assert "docs/codex/v1.0-rc-feature-freeze.md" in DEFAULT_DOCS
    assert "docs/codex/v1.0-rc-external-review-prompt.md" in DEFAULT_DOCS
    assert "docs/codex/v1.0-rc-final-handoff.md" in DEFAULT_DOCS
    assert "docs/codex/v1.0-rc-post-review-triage.md" in DEFAULT_DOCS
    assert "docs/codex/v1.0-operator-quickstart.md" in DEFAULT_DOCS
    assert "docs/codex/v1.0-workbench-evidence-closure.md" in DEFAULT_DOCS
    assert "docs/codex/v1.0-assurance-closure.md" in DEFAULT_DOCS
    assert "docs/codex/v1.0-rc-readiness-gate.md" in DEFAULT_DOCS
    assert "docs/codex/enterprise-readiness-runway.md" in DEFAULT_DOCS
    assert "docs/codex/enterprise-readiness-gap-matrix.md" in DEFAULT_DOCS
    assert "docs/codex/post-rc-decision-gate.md" in DEFAULT_DOCS
    assert "docs/codex/post-rc-decision-record-template.md" in DEFAULT_DOCS
    assert "docs/codex/post-rc-decision-record-examples.md" in DEFAULT_DOCS
    assert "docs/codex/post-rc-decision-register.md" in DEFAULT_DOCS
    assert "docs/codex/production-identity-storage-architecture.md" in DEFAULT_DOCS
    assert "docs/codex/siem-export-adapter-architecture.md" in DEFAULT_DOCS
    assert "docs/codex/compliance-mapping-architecture.md" in DEFAULT_DOCS
    assert "docs/codex/mission-control-display-integration-proposal.md" in DEFAULT_DOCS
    assert "docs/codex/mission-control-display-importer-plan.md" in DEFAULT_DOCS
    assert "docs/codex/mission-control-display-disposition-packet.md" in DEFAULT_DOCS
    assert "docs/codex/mission-control-side-handoff-plan.md" in DEFAULT_DOCS
    assert "docs/codex/mission-control-integration-implementation-ticket.md" in DEFAULT_DOCS
    assert "docs/codex/mission-control-handoff-schema-contract.md" in DEFAULT_DOCS
    assert "docs/codex/mission-control-handoff-negative-fixtures.md" in DEFAULT_DOCS
    assert "docs/codex/sandbox-vm-worker-boundary-charter.md" in DEFAULT_DOCS
    assert "docs/codex/sandbox-vm-profile-contract.md" in DEFAULT_DOCS
    assert "docs/codex/sandbox-vm-preflight-contract.md" in DEFAULT_DOCS
    assert "docs/codex/sandbox-vm-static-profile-preflight-plan.md" in DEFAULT_DOCS
    assert "docs/codex/sandbox-vm-static-profile-fixture-contract.md" in DEFAULT_DOCS
    assert (
        "docs/codex/fixtures/sandbox-vm-static-profile.local-preview.example.json"
        in DEFAULT_DOCS
    )
    assert "docs/codex/sandbox-vm-static-profile-negative-fixtures.md" in DEFAULT_DOCS
    assert "docs/codex/sandbox-vm-static-preflight-implementation-decision.md" in DEFAULT_DOCS
    assert "docs/codex/sandbox-vm-static-preflight-source-review.md" in DEFAULT_DOCS
    assert "docs/codex/sandbox-vm-static-preflight-disposition-plan.md" in DEFAULT_DOCS
    assert "docs/codex/sandbox-vm-static-preflight-disposition-packet.md" in DEFAULT_DOCS
    assert "docs/codex/sandbox-vm-static-preflight-external-response-intake.md" in DEFAULT_DOCS
    assert "docs/codex/sandbox-vm-live-poc-decision-intake.md" in DEFAULT_DOCS
    assert "docs/codex/sandbox-vm-live-poc-evidence-contract.md" in DEFAULT_DOCS
    assert "docs/codex/v3-sandbox-vm-static-preflight-internal-review.md" in DEFAULT_DOCS
    assert "docs/codex/governed-artifact-transfer-lab.md" in DEFAULT_DOCS
    assert "docs/codex/hello-world-sandbox-demo-roadmap.md" in DEFAULT_DOCS
    assert "docs/codex/capability-proposals/sandbox-artifact-write-text.md" in DEFAULT_DOCS
    assert (
        "docs/codex/capability-implementation-plans/sandbox-artifact-write-text.md"
        in DEFAULT_DOCS
    )
    assert "docs/codex/sandbox-artifact-write-text-fixture-plan.md" in DEFAULT_DOCS
    assert "docs/codex/sandbox-artifact-write-text-negative-transcripts.md" in DEFAULT_DOCS
    assert "docs/codex/sandbox-artifact-observed-demo.md" in DEFAULT_DOCS
    assert "docs/codex/sandbox-artifact-write-text-source-review.md" in DEFAULT_DOCS
    assert "docs/codex/sandbox-artifact-write-text-implementation-decision.md" in DEFAULT_DOCS
    assert "docs/codex/sandbox-promotion-evidence-contract.md" in DEFAULT_DOCS
    assert "docs/codex/trusted-host-promotion-decision-intake.md" in DEFAULT_DOCS
    assert "docs/codex/trusted-host-promotion-state-machine.md" in DEFAULT_DOCS
    assert "docs/codex/trusted-host-promotion-negative-fixtures.md" in DEFAULT_DOCS
    assert "docs/codex/trusted-host-promotion-zone-contract.md" in DEFAULT_DOCS
    assert "docs/codex/trusted-host-promotion-implementation-plan.md" in DEFAULT_DOCS
    assert "docs/codex/trusted-host-promotion-source-review.md" in DEFAULT_DOCS
    assert "docs/codex/trusted-host-promotion-disposition-packet.md" in DEFAULT_DOCS
    assert "docs/codex/v3-trusted-host-promotion-internal-review.md" in DEFAULT_DOCS
    assert "docs/codex/v3-readiness-debt-register.md" in DEFAULT_DOCS
    assert "docs/codex/local-prompt-triage.md" in DEFAULT_DOCS
    assert "docs/codex/reviewer-reproduction-map.md" in DEFAULT_DOCS
    assert "docs/codex/source-review-closure-matrix.md" in DEFAULT_DOCS
    assert "docs/codex/internal-source-review-pass-1.md" in DEFAULT_DOCS
    assert "docs/codex/internal-review-packet-v2.md" in DEFAULT_DOCS
    assert "docs/codex/internal-ai-review-workflow.md" in DEFAULT_DOCS
    assert "docs/codex/autonomous-sprint-guardrails.md" in DEFAULT_DOCS
    assert "AGENTS.md" in DEFAULT_DOCS
    assert "docs/codex/agent-workflow-instruction-layer.md" in DEFAULT_DOCS
    assert "docs/codex/low-implementer-delegation-pilot.md" in DEFAULT_DOCS
    assert "docs/codex/reviewer-finding-template.md" in DEFAULT_DOCS
    assert "docs/codex/reviewer-finding-intake.md" in DEFAULT_DOCS
    assert "docs/codex/filesystem-executor-contract.md" in DEFAULT_DOCS
    assert "docs/codex/policy-parity-harness.md" in DEFAULT_DOCS
    assert "docs/codex/audit-integrity-adversarial-suite.md" in DEFAULT_DOCS
    assert "docs/codex/adversarial-corpus-framework.md" in DEFAULT_DOCS
    assert "docs/codex/resource-limit-sanity.md" in DEFAULT_DOCS
    assert "docs/codex/ci-platform-plan.md" in DEFAULT_DOCS
    assert "docs/codex/manifest-validation-suite.md" in DEFAULT_DOCS
    assert "docs/codex/opa-parity-decision.md" in DEFAULT_DOCS
    assert "docs/codex/mcp-ingress-bypass-audit.md" in DEFAULT_DOCS
    assert "docs/codex/local-auth-boundary.md" in DEFAULT_DOCS
    assert "docs/codex/review-console-assurance.md" in DEFAULT_DOCS

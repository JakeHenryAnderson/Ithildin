"""Build a small static documentation site from selected Markdown docs."""

from __future__ import annotations

import argparse
import html
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DOCS = [
    "AGENTS.md",
    "README.md",
    "docs/codex/v0.2-review-response-and-rc-cleanup.md",
    "docs/codex/v0.2-review-packet.md",
    "docs/codex/v0.2-external-review-prompt.md",
    "docs/codex/v0.3-review-packet.md",
    "docs/codex/v0.3-external-review-prompt.md",
    "docs/codex/external-review-intake-and-closure.md",
    "docs/codex/external-review-intake-v2.md",
    "docs/codex/external-review-response-intake-template-v2.md",
    "docs/codex/v0.3-boundary-decision.md",
    "docs/codex/v0.4-boundary-charter.md",
    "docs/codex/review-docs-index.md",
    "docs/codex/review-run-manifest-schema.md",
    "docs/codex/v0.3-review-findings-summary.md",
    "docs/codex/v0.3-milestone-manifest.md",
    "docs/codex/v0.4-milestone-manifest.md",
    "docs/codex/v0.4-gating-overlay.md",
    "docs/codex/patch-apply-state-machine.md",
    "docs/codex/executor-contract-set.md",
    "docs/codex/http-executor-contract.md",
    "docs/codex/v0.1-review-packet.md",
    "docs/codex/v0.1-external-review-prompt.md",
    "docs/codex/v0.1-release-evidence.md",
    "docs/codex/local-preview-release.md",
    "docs/codex/threat-model-and-non-goals.md",
    "docs/codex/v0.4-threat-model-refresh.md",
    "docs/codex/v0.4-review-packet-generator.md",
    "docs/codex/v0.4-review-packet.md",
    "docs/codex/v0.4-external-review-prompt.md",
    "docs/codex/v0.4-capability-decision-seed.md",
    "docs/codex/v0.5-roadmap-from-v0.4-review.md",
    "docs/codex/v0.5-milestone-manifest.md",
    "docs/codex/v0.5-threat-model-delta.md",
    "docs/codex/v0.5-review-candidate-command.md",
    "docs/codex/v0.5-consolidated-packet-update.md",
    "docs/codex/v0.5-external-review-prompt.md",
    "docs/codex/v0.5-boundary-decision-draft.md",
    "docs/codex/v0.5-handoff-packet.md",
    "docs/codex/v0.6-preflight-transition.md",
    "docs/codex/v0.6-boundary-charter.md",
    "docs/codex/v0.6-milestone-manifest.md",
    "docs/codex/v0.6-external-review-assignment-matrix.md",
    "docs/codex/v0.6-external-review-dispatch-packets.md",
    "docs/codex/v0.6-external-response-normalization.md",
    "docs/codex/v0.6-patch-apply-external-review-execution.md",
    "docs/codex/v0.6-lane-status-board.md",
    "docs/codex/v0.6-critical-high-fix-freeze.md",
    "docs/codex/v0.6-medium-risk-disposition.md",
    "docs/codex/v0.6-external-review-outcome-summary.md",
    "docs/codex/source-review-closure-matrix-v4.md",
    "docs/codex/accepted-risk-register-v2.md",
    "docs/codex/v0.6-post-review-packet.md",
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
    "docs/codex/v0.7-external-review-closure-charter.md",
    "docs/codex/v0.6-final-packet-sanity-review.md",
    "docs/codex/v0.7-external-review-row-partition.md",
    "docs/codex/v0.7-patch-apply-recheck-request.md",
    "docs/codex/v0.7-patch-apply-recheck-outcome.md",
    "docs/codex/v0.7-filesystem-platform-source-review.md",
    "docs/codex/v0.7-http-fetch-source-review.md",
    "docs/codex/v0.7-signed-evidence-source-review.md",
    "docs/codex/v0.7-mcp-ingress-source-review.md",
    "docs/codex/v0.8-roadmap-prompt.md",
    "docs/codex/v0.8-status-source-of-truth.md",
    "docs/codex/v0.8-accepted-risk-disposition.md",
    "docs/codex/v0.8-public-preview-risk-review.md",
    "docs/codex/v0.8-capability-design-decision.md",
    "docs/codex/v0.8-final-decision-packet.md",
    "docs/codex/v0.9-design-only-boundary-charter.md",
    "docs/codex/capability-proposals/git-show-commit-metadata.md",
    "docs/codex/capability-proposals/git-show-ref-summary.md",
    "docs/codex/capability-proposals/git-show-tag-metadata.md",
    "docs/codex/capability-proposals/project-manifest-summary.md",
    "docs/codex/capability-implementation-plans/project-manifest-summary.md",
    "docs/codex/v3-project-manifest-summary-implementation.md",
    "docs/codex/v3-project-manifest-summary-source-review.md",
    "docs/codex/v3-project-dependency-summary-implementation.md",
    "docs/codex/v3-project-dependency-summary-source-review.md",
    "docs/codex/agent-run-observability-and-sandbox-roadmap.md",
    "docs/codex/agent-run-model-contract.md",
    "docs/codex/agent-run-evidence-contract.md",
    "docs/codex/agent-run-evidence-export-design.md",
    "docs/codex/agent-run-evidence-export-implementation-plan.md",
    "docs/codex/agent-run-evidence-export-implementation.md",
    "docs/codex/agent-run-timeline-readiness-gate.md",
    "docs/codex/agent-run-evidence-readiness-gate.md",
    "docs/codex/agent-run-operations-readiness-gate.md",
    "docs/codex/operator-workbench-readiness.md",
    "docs/codex/operator-demo-walkthrough.md",
    "docs/codex/guided-demo-readiness.md",
    "docs/codex/demo-flow-readiness.md",
    "docs/codex/demo-evidence-closure.md",
    "docs/codex/operator-action-states-design.md",
    "docs/codex/dashboard-evidence-review-checklist.md",
    "docs/codex/sandbox-workspace-boundary-contract.md",
    "docs/codex/operator-managed-sandbox-demo-guide.md",
    "docs/codex/siem-shaped-evidence-design.md",
    "docs/codex/data-classification-design.md",
    "docs/codex/control-mapping-design.md",
    "docs/codex/incident-reconstruction-guide.md",
    "docs/codex/siem-export-adapter-architecture.md",
    "docs/codex/compliance-mapping-architecture.md",
    "docs/codex/compliance-mapping-disposition-packet.md",
    "docs/codex/compliance-mapping-external-response-intake.md",
    "docs/codex/mission-control-display-external-response-intake.md",
    "docs/codex/mission-control-display-disposition-closure-gate.md",
    "docs/codex/mission-control-display-response-dry-run.md",
    "docs/codex/observability-readiness-gate.md",
    "docs/codex/control-mapping-readiness-gate.md",
    "docs/codex/capability-implementation-plans/git-show-ref-summary.md",
    "docs/codex/capability-implementation-plans/git-show-tag-metadata.md",
    "docs/codex/capability-implementation-plans/git-show-commit-metadata.md",
    "docs/codex/v0.9-git-commit-metadata-implementation.md",
    "docs/codex/v0.9-git-commit-metadata-source-review.md",
    "docs/codex/v0.9-git-ref-summary-implementation.md",
    "docs/codex/v0.9-git-ref-summary-source-review.md",
    "docs/codex/v0.9-git-tag-metadata-implementation.md",
    "docs/codex/v0.9-git-tag-metadata-source-review.md",
    "docs/codex/v0.9-git-tag-metadata-internal-review.md",
    "docs/codex/v0.9-git-tag-metadata-selection.md",
    "docs/codex/v0.9-lane-closure-summary.md",
    "docs/codex/v0.9-next-read-only-capability-seed.md",
    "docs/codex/v0.9-git-ref-summary-proposal-review.md",
    "docs/codex/read-only-local-metadata-contract.md",
    "docs/codex/read-only-capability-inventory.md",
    "docs/codex/read-only-project-intelligence.md",
    "docs/codex/next-capability-readiness.md",
    "docs/codex/v3-next-capability-candidate-evaluation.md",
    "docs/codex/v3-next-capability-candidate-evaluation-2.md",
    "docs/codex/v3-project-release-summary-selection.md",
    "docs/codex/v3-project-dependency-summary-selection.md",
    "docs/codex/capability-proposals/project-dependency-summary.md",
    "docs/codex/capability-implementation-plans/project-dependency-summary.md",
    "docs/codex/v3-project-structure-summary-selection.md",
    "docs/codex/capability-proposals/project-structure-summary.md",
    "docs/codex/capability-implementation-plans/project-structure-summary.md",
    "docs/codex/v3-project-structure-summary-implementation.md",
    "docs/codex/v3-project-structure-summary-source-review.md",
    "docs/codex/v3-project-structure-summary-internal-review.md",
    "docs/codex/v3-project-test-summary-selection.md",
    "docs/codex/capability-proposals/project-test-summary.md",
    "docs/codex/capability-implementation-plans/project-test-summary.md",
    "docs/codex/v3-project-test-summary-implementation.md",
    "docs/codex/v3-project-test-summary-source-review.md",
    "docs/codex/v3-project-docs-summary-selection.md",
    "docs/codex/capability-proposals/project-docs-summary.md",
    "docs/codex/capability-implementation-plans/project-docs-summary.md",
    "docs/codex/v3-project-docs-summary-implementation.md",
    "docs/codex/v3-project-docs-summary-source-review.md",
    "docs/codex/v3-project-language-summary-selection.md",
    "docs/codex/capability-proposals/project-language-summary.md",
    "docs/codex/capability-implementation-plans/project-language-summary.md",
    "docs/codex/v3-project-language-summary-implementation.md",
    "docs/codex/v3-project-language-summary-source-review.md",
    "docs/codex/v3-project-config-summary-selection.md",
    "docs/codex/capability-proposals/project-config-summary.md",
    "docs/codex/capability-implementation-plans/project-config-summary.md",
    "docs/codex/v3-project-config-summary-implementation.md",
    "docs/codex/v3-project-config-summary-source-review.md",
    "docs/codex/v3-project-ci-summary-selection.md",
    "docs/codex/capability-proposals/project-ci-summary.md",
    "docs/codex/capability-implementation-plans/project-ci-summary.md",
    "docs/codex/v3-project-ci-summary-implementation.md",
    "docs/codex/v3-project-ci-summary-source-review.md",
    "docs/codex/capability-proposals/project-release-summary.md",
    "docs/codex/capability-implementation-plans/project-release-summary.md",
    "docs/codex/project-release-summary-fixture-plan.md",
    "docs/codex/project-release-summary-negative-transcripts.md",
    "docs/codex/v3-project-release-summary-implementation.md",
    "docs/codex/project-release-summary-implementation-transition.md",
    "docs/codex/v3-project-release-summary-source-review.md",
    "docs/codex/v3-project-release-summary-internal-review.md",
    "docs/codex/v3-project-risk-summary-selection.md",
    "docs/codex/capability-proposals/project-risk-summary.md",
    "docs/codex/capability-implementation-plans/project-risk-summary.md",
    "docs/codex/v3-project-risk-summary-implementation.md",
    "docs/codex/project-risk-summary-fixture-plan.md",
    "docs/codex/project-risk-summary-negative-transcripts.md",
    "docs/codex/v3-project-risk-summary-source-review.md",
    "docs/codex/metadata-privacy-policy.md",
    "docs/codex/read-only-metadata-capability-checklist.md",
    "docs/codex/read-only-capability-source-review-template.md",
    "docs/codex/v1.0-rc-roadmap.md",
    "docs/codex/v1.0-rc-status.md",
    "docs/codex/v1.0-rc-feature-freeze.md",
    "docs/codex/v1.0-rc-external-review-prompt.md",
    "docs/codex/v1.0-rc-final-handoff.md",
    "docs/codex/v1.0-rc-post-review-triage.md",
    "docs/codex/v1.0-operator-quickstart.md",
    "docs/codex/v1.0-workbench-evidence-closure.md",
    "docs/codex/v1.0-assurance-closure.md",
    "docs/codex/v1.0-rc-readiness-gate.md",
    "docs/codex/enterprise-readiness-runway.md",
    "docs/codex/enterprise-readiness-gap-matrix.md",
    "docs/codex/enterprise-external-review-queue.md",
    "docs/codex/enterprise-sandbox-control-plane-readiness.md",
    "docs/codex/post-rc-decision-gate.md",
    "docs/codex/post-rc-decision-record-template.md",
    "docs/codex/post-rc-decision-record-examples.md",
    "docs/codex/post-rc-decision-register.md",
    "docs/codex/public-security-product-positioning-decision-intake.md",
    "docs/codex/public-security-product-positioning-decision-closure-gate.md",
    "docs/codex/docs-claims-public-preview-disposition-closure-gate.md",
    "docs/codex/production-identity-storage-architecture.md",
    "docs/codex/production-identity-storage-disposition-packet.md",
    "docs/codex/production-identity-storage-disposition-closure-gate.md",
    "docs/codex/production-identity-storage-response-dry-run.md",
    "docs/codex/production-identity-storage-external-response-intake.md",
    "docs/codex/siem-export-adapter-architecture.md",
    "docs/codex/siem-export-adapter-disposition-packet.md",
    "docs/codex/siem-export-adapter-disposition-closure-gate.md",
    "docs/codex/siem-export-adapter-response-dry-run.md",
    "docs/codex/siem-export-adapter-external-response-intake.md",
    "docs/codex/compliance-mapping-architecture.md",
    "docs/codex/compliance-mapping-disposition-packet.md",
    "docs/codex/compliance-mapping-disposition-closure-gate.md",
    "docs/codex/compliance-mapping-response-dry-run.md",
    "docs/codex/compliance-mapping-external-response-intake.md",
    "docs/codex/mission-control-display-integration-proposal.md",
    "docs/codex/mission-control-display-importer-plan.md",
    "docs/codex/mission-control-display-decision-intake.md",
    "docs/codex/mission-control-display-disposition-packet.md",
    "docs/codex/mission-control-display-external-response-intake.md",
    "docs/codex/mission-control-display-disposition-closure-gate.md",
    "docs/codex/mission-control-display-response-dry-run.md",
    "docs/codex/mission-control-integration-readiness-packet.md",
    "docs/codex/mission-control-side-handoff-plan.md",
    "docs/codex/mission-control-integration-implementation-ticket.md",
    "docs/codex/mission-control-handoff-schema-contract.md",
    "docs/codex/mission-control-handoff-negative-fixtures.md",
    "docs/codex/sandbox-vm-worker-boundary-charter.md",
    "docs/codex/sandbox-vm-profile-contract.md",
    "docs/codex/sandbox-vm-preflight-contract.md",
    "docs/codex/sandbox-vm-static-profile-preflight-plan.md",
    "docs/codex/sandbox-vm-static-profile-fixture-contract.md",
    "docs/codex/fixtures/sandbox-vm-static-profile.local-preview.example.json",
    "docs/codex/sandbox-vm-static-profile-negative-fixtures.md",
    "docs/codex/sandbox-vm-static-preflight-implementation-decision.md",
    "docs/codex/sandbox-vm-static-preflight-source-review.md",
    "docs/codex/sandbox-vm-static-preflight-external-review-bundle.md",
    "docs/codex/sandbox-vm-static-preflight-disposition-plan.md",
    "docs/codex/sandbox-vm-static-preflight-disposition-closure-gate.md",
    "docs/codex/sandbox-vm-static-preflight-disposition-packet.md",
    "docs/codex/sandbox-vm-static-preflight-external-response-intake.md",
    "docs/codex/sandbox-vm-static-preflight-response-dry-run.md",
    "docs/codex/sandbox-vm-static-preflight-triage-update.md",
    "docs/codex/sandbox-vm-static-preflight-reviewer-reproduction-map.md",
    "docs/codex/sandbox-vm-live-poc-decision-intake.md",
    "docs/codex/sandbox-vm-live-poc-evidence-contract.md",
    "docs/codex/sandbox-vm-live-poc-preconditions-map.md",
    "docs/codex/sandbox-vm-live-poc-external-response-intake.md",
    "docs/codex/sandbox-vm-live-poc-decision-closure-gate.md",
    "docs/codex/sandbox-vm-live-poc-response-dry-run.md",
    "docs/codex/sandbox-vm-live-poc-decision-packet.md",
    "docs/codex/v3-sandbox-vm-static-preflight-internal-review.md",
    "docs/codex/governed-artifact-transfer-lab.md",
    "docs/codex/hello-world-sandbox-demo-roadmap.md",
    "docs/codex/hello-world-sandbox-observed-demo.md",
    "docs/codex/hello-world-mission-control-handoff.md",
    "docs/codex/capability-proposals/sandbox-artifact-write-text.md",
    "docs/codex/capability-implementation-plans/sandbox-artifact-write-text.md",
    "docs/codex/sandbox-artifact-write-text-fixture-plan.md",
    "docs/codex/sandbox-artifact-write-text-negative-transcripts.md",
    "docs/codex/sandbox-artifact-observed-demo.md",
    "docs/codex/sandbox-artifact-write-text-source-review.md",
    "docs/codex/sandbox-artifact-write-text-implementation-decision.md",
    "docs/codex/v3-sandbox-artifact-write-text-internal-review.md",
    "docs/codex/sandbox-promotion-evidence-contract.md",
    "docs/codex/trusted-host-promotion-decision-intake.md",
    "docs/codex/trusted-host-promotion-state-machine.md",
    "docs/codex/trusted-host-promotion-negative-fixtures.md",
    "docs/codex/trusted-host-promotion-zone-contract.md",
    "docs/codex/trusted-host-promotion-implementation-plan.md",
    "docs/codex/trusted-host-promotion-source-review.md",
    "docs/codex/trusted-host-promotion-disposition-packet.md",
    "docs/codex/trusted-host-promotion-disposition-closure-gate.md",
    "docs/codex/trusted-host-promotion-external-response-intake.md",
    "docs/codex/trusted-host-promotion-response-dry-run.md",
    "docs/codex/v3-trusted-host-promotion-internal-review.md",
    "docs/codex/v3-readiness-debt-register.md",
    "docs/codex/v0.6-internal-subagent-review-wave.md",
    "docs/codex/v0.6-internal-review-execution-wave-2.md",
    "docs/codex/v0.6-internal-proxy-review-operating-model.md",
    "docs/codex/v0.6-closure-handoff.md",
    "docs/codex/v0.6-gpt-55-pro-handoff-prompt.md",
    "docs/codex/local-prompt-triage.md",
    "docs/codex/capability-expansion-gate.md",
    "docs/codex/tool-surface-invariant-gate.md",
    "docs/codex/no-new-powers-guardrail.md",
    "docs/codex/evidence-confusion-gate.md",
    "docs/codex/external-review-closure-gate.md",
    "docs/codex/source-review-runbook-v2.md",
    "docs/codex/source-review-transcript-packet.md",
    "docs/codex/reviewer-artifact-manifest-v2.md",
    "docs/codex/source-file-inspection-packet.md",
    "docs/codex/review-packet-source-pointers.md",
    "docs/codex/patch-apply-source-review-checklist.md",
    "docs/codex/filesystem-source-review-checklist.md",
    "docs/codex/http-fetch-source-review-checklist.md",
    "docs/codex/signed-evidence-source-review-checklist.md",
    "docs/codex/policy-parity-source-review-checklist.md",
    "docs/codex/mcp-ingress-source-review-checklist.md",
    "docs/codex/review-console-source-review-checklist.md",
    "docs/codex/external-findings-intake-dry-run.md",
    "docs/codex/closure-matrix-evidence-sync.md",
    "docs/codex/accepted-risk-register.md",
    "docs/codex/capability-decision-report.md",
    "docs/codex/mcp-client-examples.md",
    "docs/codex/mcp-inspector-recipes.md",
    "docs/codex/evidence-contracts.md",
    "docs/codex/audit-integrity-adversarial-suite.md",
    "docs/codex/adversarial-corpus-framework.md",
    "docs/codex/resource-limit-sanity.md",
    "docs/codex/ci-platform-plan.md",
    "docs/codex/demo-scenario-pack-v2.md",
    "docs/codex/live-demo-runbook.md",
    "docs/codex/manifest-validation-suite.md",
    "docs/codex/policy-parity-harness.md",
    "docs/codex/opa-parity-decision.md",
    "docs/codex/mcp-ingress-bypass-audit.md",
    "docs/codex/local-auth-boundary.md",
    "docs/codex/review-console-assurance.md",
    "docs/codex/filesystem-executor-contract.md",
    "docs/codex/negative-review-recipes.md",
    "docs/codex/release-evidence-schema.md",
    "docs/codex/review-packet-diff.md",
    "docs/codex/packet-redaction-scanner.md",
    "docs/codex/test-determinism-gate.md",
    "docs/codex/registry-fail-closed-suite.md",
    "docs/codex/release-guardrail-expansion.md",
    "docs/codex/reviewer-reproduction-map.md",
    "docs/codex/source-review-closure-matrix.md",
    "docs/codex/internal-source-review-pass-1.md",
    "docs/codex/internal-review-packet-v2.md",
    "docs/codex/internal-ai-review-workflow.md",
    "docs/codex/autonomous-sprint-guardrails.md",
    "docs/codex/agent-workflow-instruction-layer.md",
    "docs/codex/low-implementer-delegation-pilot.md",
    "docs/codex/low-implementer-ticket-catalog.md",
    "docs/codex/low-implementer-trial-log.md",
    "docs/codex/low-implementer-delegation-scorecard.md",
    "docs/codex/reviewer-finding-template.md",
    "docs/codex/reviewer-finding-intake.md",
    "docs/codex/signed-audit-exports.md",
    "docs/codex/signed-manifest-locks.md",
    "docs/codex/v0.1-public-preview-release-notes.md",
    "docs/codex/local-model-demo.md",
    "docs/codex/v0.1-local-preview-checklist.md",
    "docs/codex/v0.1-security-test-matrix.md",
    "docs/codex/implementation-backlog.md",
    "docs/codex/v0.2-planning-seed.md",
    "docs/obsidian/03-security-model.md",
    "docs/obsidian/04-threat-model.md",
    "docs/obsidian/11-roadmap.md",
    "docs/research/source-verification.md",
]


@dataclass(frozen=True)
class DocPage:
    source: Path
    title: str
    output_name: str


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="site")
    args = parser.parse_args()

    build_site(Path(args.output_dir), [Path(doc) for doc in DEFAULT_DOCS])


def build_site(output_dir: Path, docs: list[Path]) -> list[DocPage]:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    pages = [_page_for_doc(doc) for doc in docs]
    for page in pages:
        markdown = _strip_front_matter(page.source.read_text(encoding="utf-8"))
        html_body = markdown_to_html(markdown)
        (output_dir / page.output_name).write_text(
            _html_document(page.title, html_body),
            encoding="utf-8",
        )

    index_items = "\n".join(
        f'<li><a href="{html.escape(page.output_name)}">{html.escape(page.title)}</a></li>'
        for page in pages
    )
    (output_dir / "index.html").write_text(
        _html_document("Ithildin Docs", f"<h1>Ithildin Docs</h1>\n<ul>\n{index_items}\n</ul>"),
        encoding="utf-8",
    )
    print(f"Built docs site at {output_dir}")
    return pages


def markdown_to_html(markdown: str) -> str:
    blocks: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    in_code = False
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            blocks.append(f"<p>{' '.join(paragraph)}</p>")
            paragraph.clear()

    def flush_list() -> None:
        if list_items:
            blocks.append("<ul>\n" + "\n".join(list_items) + "\n</ul>")
            list_items.clear()

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if line.startswith("```"):
            if in_code:
                blocks.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
                code_lines.clear()
                in_code = False
            else:
                flush_paragraph()
                flush_list()
                in_code = True
            continue
        if in_code:
            code_lines.append(raw_line)
            continue
        if not line:
            flush_paragraph()
            flush_list()
            continue
        heading = re.match(r"^(#{1,4})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            flush_list()
            level = len(heading.group(1))
            blocks.append(f"<h{level}>{_inline_markdown(heading.group(2))}</h{level}>")
            continue
        if line.startswith("- "):
            flush_paragraph()
            list_items.append(f"<li>{_inline_markdown(line[2:])}</li>")
            continue
        numbered = re.match(r"^\d+\.\s+(.+)$", line)
        if numbered:
            flush_paragraph()
            list_items.append(f"<li>{_inline_markdown(numbered.group(1))}</li>")
            continue
        paragraph.append(_inline_markdown(line))

    flush_paragraph()
    flush_list()
    if code_lines:
        blocks.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
    return "\n".join(blocks)


def _page_for_doc(path: Path) -> DocPage:
    text = _strip_front_matter(path.read_text(encoding="utf-8"))
    title = path.stem
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    output_name = re.sub(r"[^A-Za-z0-9]+", "-", path.as_posix()).strip("-").lower() + ".html"
    return DocPage(source=path, title=title, output_name=output_name)


def _strip_front_matter(markdown: str) -> str:
    if not markdown.startswith("---\n"):
        return markdown
    end = markdown.find("\n---\n", 4)
    if end == -1:
        return markdown
    return markdown[end + 5 :]


def _inline_markdown(value: str) -> str:
    escaped = html.escape(value)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)


def _html_document(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.55; margin: 0; color: #18202b; background: #f7f8fa; }}
    main {{ max-width: 880px; margin: 0 auto; padding: 40px 20px 64px;
      background: #fff; min-height: 100vh; }}
    a {{ color: #0f5d8f; }}
    code, pre {{ background: #eef2f5; border-radius: 4px; }}
    code {{ padding: 0 4px; }}
    pre {{ overflow-x: auto; padding: 14px; }}
    h1, h2, h3, h4 {{ line-height: 1.2; }}
  </style>
</head>
<body>
<main>
{body}
</main>
</body>
</html>
"""


if __name__ == "__main__":
    main()

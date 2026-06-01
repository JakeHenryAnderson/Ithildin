"""Shared review-document metadata for release evidence and review bundles."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TypedDict

REVIEW_DOCS = [
    "README.md",
    "docs/codex/v0.2-review-response-and-rc-cleanup.md",
    "docs/codex/v0.2-review-packet.md",
    "docs/codex/v0.2-external-review-prompt.md",
    "docs/codex/v0.2-planning-seed.md",
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
    "docs/codex/v0.1-security-test-matrix.md",
    "docs/codex/filesystem-executor-contract.md",
    "docs/codex/evidence-contracts.md",
    "docs/codex/evidence-contracts-v2.json",
    "docs/codex/redaction-evidence-boundary.md",
    "docs/codex/audit-integrity-adversarial-suite.md",
    "docs/codex/adversarial-corpus-framework.md",
    "docs/codex/resource-limit-sanity.md",
    "docs/codex/ci-platform-plan.md",
    "docs/codex/demo-scenario-pack-v2.md",
    "docs/codex/audit-export-lifecycle-diagnostics.md",
    "docs/codex/manifest-validation-suite.md",
    "docs/codex/manifest-change-review-workflow.md",
    "docs/codex/policy-parity-harness.md",
    "docs/codex/opa-parity-decision.md",
    "docs/codex/mcp-ingress-bypass-audit.md",
    "docs/codex/local-auth-boundary.md",
    "docs/codex/review-console-assurance.md",
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
    "docs/codex/reviewer-finding-template.md",
    "docs/codex/reviewer-finding-intake.md",
    "docs/codex/threat-model-and-non-goals.md",
    "docs/codex/v0.4-threat-model-refresh.md",
    "docs/codex/v0.4-review-packet-generator.md",
    "docs/codex/v0.4-review-packet.md",
    "docs/codex/v0.4-external-review-prompt.md",
    "docs/codex/v0.4-capability-decision-seed.md",
    "docs/codex/v0.5-roadmap-from-v0.4-review.md",
    "docs/codex/v0.5-milestone-manifest.md",
    "docs/codex/v0.5-milestone-manifest.json",
    "docs/codex/v0.5-threat-model-delta.md",
    "docs/codex/v0.5-review-candidate-command.md",
    "docs/codex/v0.5-consolidated-packet-update.md",
    "docs/codex/v0.5-external-review-prompt.md",
    "docs/codex/v0.5-boundary-decision-draft.md",
    "docs/codex/v0.5-handoff-packet.md",
    "docs/codex/v0.6-preflight-transition.md",
    "docs/codex/v0.6-boundary-charter.md",
    "docs/codex/v0.6-milestone-manifest.md",
    "docs/codex/v0.6-milestone-manifest.json",
    "docs/codex/v0.6-external-review-assignment-matrix.md",
    "docs/codex/v0.6-external-review-dispatch-packets.md",
    "docs/codex/v0.6-external-response-normalization.md",
    "docs/codex/v0.6-patch-apply-external-review-execution.md",
    "docs/codex/v0.6-lane-status-board.md",
    "docs/codex/v0.6-lane-status-board.json",
    "docs/codex/v0.6-critical-high-fix-freeze.md",
    "docs/codex/v0.6-medium-risk-disposition.md",
    "docs/codex/v0.6-external-review-outcome-summary.md",
    "docs/codex/source-review-closure-matrix-v4.md",
    "docs/codex/accepted-risk-register-v2.md",
    "docs/codex/accepted-risk-register-v2.json",
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
    "docs/codex/v0.6-internal-subagent-review-wave.md",
    "docs/codex/v0.6-internal-review-execution-wave-2.md",
    "docs/codex/v0.6-internal-proxy-review-operating-model.md",
    "docs/codex/v0.6-closure-handoff.md",
    "docs/codex/v0.6-gpt-55-pro-handoff-prompt.md",
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
    "docs/codex/accepted-risk-register.json",
    "docs/codex/capability-decision-report.md",
    "docs/codex/local-preview-release.md",
]


class ReviewDocMetadata(TypedDict):
    path: str
    sha256: str
    bytes: int


class ReviewDocError(RuntimeError):
    """Raised when a required review document is unavailable."""


def collect_review_doc_metadata(
    repo_root: Path,
    docs: list[str] | None = None,
) -> list[ReviewDocMetadata]:
    metadata: list[ReviewDocMetadata] = []
    for doc in docs or REVIEW_DOCS:
        path = repo_root / doc
        if not path.exists():
            raise ReviewDocError(f"review document is missing: {doc}")
        content = path.read_bytes()
        metadata.append(
            {
                "path": doc,
                "sha256": "sha256:" + hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
            }
        )
    return metadata

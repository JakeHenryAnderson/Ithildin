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
    "docs/codex/v0.3-boundary-decision.md",
    "docs/codex/v0.4-boundary-charter.md",
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
    "docs/codex/audit-integrity-adversarial-suite.md",
    "docs/codex/adversarial-corpus-framework.md",
    "docs/codex/resource-limit-sanity.md",
    "docs/codex/ci-platform-plan.md",
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

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
    assert "docs/codex/capability-proposals/git-show-ref-summary.md" in DEFAULT_DOCS
    assert "docs/codex/v0.9-git-ref-summary-proposal-review.md" in DEFAULT_DOCS
    assert "docs/codex/reviewer-reproduction-map.md" in DEFAULT_DOCS
    assert "docs/codex/source-review-closure-matrix.md" in DEFAULT_DOCS
    assert "docs/codex/internal-source-review-pass-1.md" in DEFAULT_DOCS
    assert "docs/codex/internal-review-packet-v2.md" in DEFAULT_DOCS
    assert "docs/codex/internal-ai-review-workflow.md" in DEFAULT_DOCS
    assert "docs/codex/autonomous-sprint-guardrails.md" in DEFAULT_DOCS
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

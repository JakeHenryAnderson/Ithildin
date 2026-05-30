"""Build a small static documentation site from selected Markdown docs."""

from __future__ import annotations

import argparse
import html
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DOCS = [
    "README.md",
    "docs/codex/v0.2-review-response-and-rc-cleanup.md",
    "docs/codex/v0.2-review-packet.md",
    "docs/codex/v0.2-external-review-prompt.md",
    "docs/codex/v0.3-review-packet.md",
    "docs/codex/v0.3-external-review-prompt.md",
    "docs/codex/v0.3-milestone-manifest.md",
    "docs/codex/patch-apply-state-machine.md",
    "docs/codex/executor-contract-set.md",
    "docs/codex/http-executor-contract.md",
    "docs/codex/v0.1-review-packet.md",
    "docs/codex/v0.1-external-review-prompt.md",
    "docs/codex/v0.1-release-evidence.md",
    "docs/codex/local-preview-release.md",
    "docs/codex/threat-model-and-non-goals.md",
    "docs/codex/mcp-client-examples.md",
    "docs/codex/mcp-inspector-recipes.md",
    "docs/codex/evidence-contracts.md",
    "docs/codex/audit-integrity-adversarial-suite.md",
    "docs/codex/manifest-validation-suite.md",
    "docs/codex/policy-parity-harness.md",
    "docs/codex/opa-parity-decision.md",
    "docs/codex/mcp-ingress-bypass-audit.md",
    "docs/codex/review-console-assurance.md",
    "docs/codex/filesystem-executor-contract.md",
    "docs/codex/negative-review-recipes.md",
    "docs/codex/release-evidence-schema.md",
    "docs/codex/review-packet-diff.md",
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

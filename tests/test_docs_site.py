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

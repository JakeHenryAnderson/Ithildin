from __future__ import annotations

from pathlib import Path

from scripts.negative_review_transcripts import build_transcripts


def test_negative_review_transcripts_cover_denial_scenarios(tmp_path: Path) -> None:
    transcript_path = build_transcripts(tmp_path / "negative-review-transcripts")
    transcript = transcript_path.read_text(encoding="utf-8")

    for heading in [
        "Path Traversal Denial",
        "Symlink Escape Denial",
        "Stale-Base Patch Apply Denial",
        "HTTP Private Redirect Denial",
        "Unknown Principal Denial",
        "Disabled Principal Denial",
        "Replayed Approval Denial",
        "Manifest Lock Tamper Denial",
        "Policy Parity Mismatch Detection",
        "Patch Apply Ambiguous Diagnostics",
    ]:
        assert heading in transcript
    assert transcript.count("observed status: `denied`") == 10


def test_negative_review_transcripts_are_secret_free(tmp_path: Path) -> None:
    transcript_path = build_transcripts(tmp_path / "negative-review-transcripts")
    transcript = transcript_path.read_text(encoding="utf-8")

    forbidden_fragments = [
        "do-not-leak",
        "BEGIN PRIVATE KEY",
        "TOKEN=",
        "secret",
        "--- a/README.md",
        "+new",
        "169.254.169.254",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in transcript

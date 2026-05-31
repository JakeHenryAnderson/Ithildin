from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.adversarial_corpus_check import AdversarialCorpusError, validate_manifest


def test_committed_adversarial_corpus_manifest_passes() -> None:
    summary = validate_manifest()

    assert summary.version == "1"
    assert summary.count == 4
    assert summary.implemented == 4
    assert summary.ids == (
        "http-canonicalization-v2",
        "filesystem-race-v2",
        "audit-integrity-v2",
        "negative-review-transcripts-v2",
    )


def test_adversarial_corpus_manifest_rejects_duplicate_ids(tmp_path: Path) -> None:
    manifest = tmp_path / "corpus.json"
    manifest.write_text(
        json.dumps(
            {
                "version": "1",
                "corpora": [
                    _entry("duplicate", "README.md"),
                    _entry("duplicate", "README.md"),
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(AdversarialCorpusError, match="duplicate corpus id"):
        validate_manifest(manifest)


def test_adversarial_corpus_manifest_rejects_missing_artifacts(tmp_path: Path) -> None:
    manifest = tmp_path / "corpus.json"
    manifest.write_text(
        json.dumps({"version": "1", "corpora": [_entry("missing", "missing.md")]}),
        encoding="utf-8",
    )

    with pytest.raises(AdversarialCorpusError, match="corpus artifact is missing"):
        validate_manifest(manifest)


def test_adversarial_corpus_manifest_rejects_bad_categories(tmp_path: Path) -> None:
    manifest = tmp_path / "corpus.json"
    entry = _entry("bad-categories", "README.md")
    entry["categories"] = ["path", "path"]
    manifest.write_text(
        json.dumps({"version": "1", "corpora": [entry]}),
        encoding="utf-8",
    )

    with pytest.raises(AdversarialCorpusError, match="duplicate categories"):
        validate_manifest(manifest)


def _entry(corpus_id: str, artifact: str) -> dict[str, object]:
    return {
        "id": corpus_id,
        "area": "fixture",
        "artifact": artifact,
        "command": "make test",
        "status": "implemented",
        "categories": ["fixture"],
    }

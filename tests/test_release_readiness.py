from __future__ import annotations

import sys
from pathlib import Path

import pytest

from scripts import release_evidence, release_guardrails, release_packet


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


def test_release_packet_review_docs_exist() -> None:
    missing = [doc for doc in release_packet.REVIEW_DOCS if not Path(doc).exists()]

    assert missing == []

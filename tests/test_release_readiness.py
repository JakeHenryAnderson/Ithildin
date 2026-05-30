from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from scripts import (
    consolidate_review_packet,
    release_evidence,
    release_guardrails,
    release_packet,
    review_docs,
    review_packet_bundle,
)


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
    assert "review_doc_hashes" in output


def test_release_packet_review_docs_exist() -> None:
    missing = [doc for doc in review_docs.REVIEW_DOCS if not Path(doc).exists()]

    assert missing == []


def test_negative_review_recipes_reference_existing_tools_and_commands() -> None:
    recipes = Path("docs/codex/negative-review-recipes.md").read_text(encoding="utf-8")
    manifest_names = {
        line.removeprefix("name: ").strip()
        for path in Path("tool-manifests").glob("*.yaml")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("name: ")
    }
    for tool_name in [
        "fs.read",
        "fs.list",
        "fs.patch.propose",
        "fs.patch.apply",
        "http.fetch",
    ]:
        assert tool_name in manifest_names
        assert tool_name in recipes
    for command in ["make demo-seed", "make mcp-inspector-recipes"]:
        assert command in recipes


def test_reviewer_reproduction_map_references_implemented_targets() -> None:
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(
        encoding="utf-8"
    )
    makefile = Path("Makefile").read_text(encoding="utf-8")
    for target in [
        "release-check",
        "release-evidence",
        "release-packet",
        "signed-evidence-demo",
        "review-packet-bundle",
        "review-packet-consolidated",
        "docs-site",
    ]:
        assert f"make {target}" in reproduction_map
        assert f"{target}:" in makefile
    assert "artifact-hashes.json" in reproduction_map
    assert "consolidated-attachment-hashes.json" in reproduction_map
    assert "review-doc-hashes.json" in reproduction_map


def test_consolidated_review_packet_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path
    bundle_dir = repo_root / "var/review-packets/v0.2/ithildin-v0.2-review-packet-abc123"
    bundle_dir.mkdir(parents=True)
    for path in [
        "INDEX.md",
        "release-check.txt",
        "release-evidence.json",
        "release-packet.md",
        "release-packet.json",
        "review-doc-hashes.json",
        "artifact-hashes.json",
        "git-summary.txt",
    ]:
        bundle_dir.joinpath(path).write_text(f"# {path}\n", encoding="utf-8")
    for path in [
        "README.md",
        "docs/codex/v0.2-external-review-prompt.md",
        "docs/codex/reviewer-reproduction-map.md",
        "docs/codex/v0.2-review-packet.md",
        "docs/codex/v0.2-review-response-and-rc-cleanup.md",
        "docs/codex/v0.2-planning-seed.md",
        "docs/codex/v0.1-security-test-matrix.md",
        "docs/codex/evidence-contracts.md",
        "docs/codex/threat-model-and-non-goals.md",
        "docs/codex/negative-review-recipes.md",
        "docs/codex/source-review-closure-matrix.md",
        "docs/codex/reviewer-finding-template.md",
        "docs/codex/signed-audit-exports.md",
        "docs/codex/signed-manifest-locks.md",
        "docs/codex/local-preview-release.md",
        "docs/codex/mcp-client-examples.md",
        "docs/codex/mcp-inspector-recipes.md",
        "docs/research/source-verification.md",
    ]:
        source = repo_root / path
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(f"# {source.stem}\n", encoding="utf-8")
    demo_summary = (
        repo_root
        / "var/review-packets/v0.2/signed-evidence-demo/SIGNED_EVIDENCE_DEMO.md"
    )
    demo_summary.parent.mkdir(parents=True)
    demo_summary.write_text("# demo\n", encoding="utf-8")
    negative_transcripts = (
        repo_root
        / "var/review-packets/v0.2/negative-review-transcripts/NEGATIVE_REVIEW_TRANSCRIPTS.md"
    )
    negative_transcripts.parent.mkdir(parents=True)
    negative_transcripts.write_text("# negative transcripts\n", encoding="utf-8")
    monkeypatch.chdir(repo_root)

    output_dir = consolidate_review_packet.build_consolidated_packet(
        repo_root=repo_root,
        bundle_dir=bundle_dir,
        output_dir=repo_root / "var/review-packets/v0.2/GPT-5.5-Pro-consolidated",
    )

    for filename in consolidate_review_packet.ATTACHMENT_FILES:
        assert output_dir.joinpath(filename).exists()
    hashes = json.loads(
        output_dir.joinpath("consolidated-attachment-hashes.json").read_text(
            encoding="utf-8"
        )
    )
    hash_paths = {entry["path"] for entry in hashes}
    assert hash_paths == set(consolidate_review_packet.ATTACHMENT_FILES)
    assert all(str(entry["sha256"]).startswith("sha256:") for entry in hashes)
    assert "Negative Review Transcripts" in output_dir.joinpath(
        "04_REPRODUCTION_SECURITY_AND_NEGATIVE_RECIPES.md"
    ).read_text(encoding="utf-8")
    all_output_paths = [path.as_posix() for path in output_dir.rglob("*")]
    assert not any("/.env" in path for path in all_output_paths)
    assert not any("/var/keys/" in path for path in all_output_paths)
    assert not any(path.endswith(".sqlite3") for path in all_output_paths)


def test_security_matrix_splits_link_race_coverage() -> None:
    matrix = Path("docs/codex/v0.1-security-test-matrix.md").read_text(encoding="utf-8")

    assert "Hardlink ambiguity and deeper TOCTOU cases" not in matrix
    assert "Hardlink and symlink cases" in matrix
    assert "Broader TOCTOU/race proofs" in matrix
    assert "Covered after v0.2" not in matrix
    assert "Covered by v0.2 tests; pending external review" in matrix


def test_source_review_closure_matrix_covers_required_areas() -> None:
    matrix_path = Path("docs/codex/source-review-closure-matrix.md")
    matrix = matrix_path.read_text(encoding="utf-8")
    review_packet = Path("docs/codex/v0.2-review-packet.md").read_text(encoding="utf-8")
    prompt = Path("docs/codex/v0.2-external-review-prompt.md").read_text(
        encoding="utf-8"
    )

    for area in [
        "fs.read",
        "fs.patch.propose",
        "fs.patch.apply",
        "http.fetch",
        "Audit export/signing",
        "Manifest-lock verification",
        "Policy preview/impact",
        "MCP ingress",
        "Review-console approval flow",
    ]:
        assert area in matrix
    for column in [
        "Reviewer",
        "Date",
        "Findings count",
        "Blocking findings",
        "Disposition",
        "Closure notes",
    ]:
        assert column in matrix
    assert "source-review-closure-matrix.md" in review_packet
    assert "source-review-closure-matrix.md" in prompt


def test_reviewer_finding_template_has_required_fields() -> None:
    template = Path("docs/codex/reviewer-finding-template.md").read_text(
        encoding="utf-8"
    )
    prompt = Path("docs/codex/v0.2-external-review-prompt.md").read_text(
        encoding="utf-8"
    )
    reproduction_map = Path("docs/codex/reviewer-reproduction-map.md").read_text(
        encoding="utf-8"
    )

    for field in [
        "Finding ID",
        "Severity",
        "Affected files/functions",
        "Claim being tested",
        "Observed behavior",
        "Recommended fix",
        "Blocking status",
        "Disposition",
        "Verification notes",
        "Overall judgment",
        "Brutal short version",
    ]:
        assert field in template
    assert "reviewer-finding-template.md" in prompt
    assert "reviewer-finding-template.md" in reproduction_map


def test_review_doc_metadata_is_deterministic(tmp_path: Path) -> None:
    doc = tmp_path / "README.md"
    doc.write_text("hello\n", encoding="utf-8")

    first = review_docs.collect_review_doc_metadata(tmp_path, ["README.md"])
    second = review_docs.collect_review_doc_metadata(tmp_path, ["README.md"])

    assert first == second
    assert first == [
        {
            "path": "README.md",
            "sha256": "sha256:5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03",
            "bytes": 6,
        }
    ]


def test_review_doc_metadata_fails_for_missing_doc(tmp_path: Path) -> None:
    with pytest.raises(review_docs.ReviewDocError, match="review document is missing"):
        review_docs.collect_review_doc_metadata(tmp_path, ["missing.md"])


def test_review_packet_bundle_fails_outside_repo_markers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["review_packet_bundle.py"])

    result = review_packet_bundle.main()

    assert result == 1
    assert "must be run from the Ithildin repo root" in capsys.readouterr().err


def test_review_packet_bundle_rejects_dirty_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_project_markers(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        review_packet_bundle,
        "_git",
        lambda args: " M README.md" if args == ["status", "--short"] else "abc123",
    )

    with pytest.raises(review_packet_bundle.BundleError, match="working tree is dirty"):
        review_packet_bundle.build_bundle(
            repo_root=tmp_path,
            output_root=tmp_path / "var/review-packets/v0.2",
            allow_dirty=False,
            run_release_check=False,
        )


def test_review_packet_bundle_layout_and_exclusions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_project_markers(tmp_path)
    docs = ["README.md", "docs/codex/v0.2-review-packet.md"]
    for doc in docs:
        path = tmp_path / doc
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {path.stem}\n", encoding="utf-8")
    demo_summary = (
        tmp_path
        / "var/review-packets/v0.2/signed-evidence-demo/SIGNED_EVIDENCE_DEMO.md"
    )
    demo_summary.parent.mkdir(parents=True)
    demo_summary.write_text("# Signed Evidence Demo\n", encoding="utf-8")
    negative_transcripts = (
        tmp_path
        / "var/review-packets/v0.2/negative-review-transcripts/NEGATIVE_REVIEW_TRANSCRIPTS.md"
    )
    negative_transcripts.parent.mkdir(parents=True)
    negative_transcripts.write_text("# Negative Review Transcripts\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(review_packet_bundle, "REVIEW_DOCS", docs)
    monkeypatch.setattr(review_packet_bundle, "BUNDLE_DOCS", docs)

    def fake_git(args: list[str]) -> str:
        if args == ["status", "--short"]:
            return ""
        if args == ["rev-parse", "HEAD"]:
            return "abcdef1234567890"
        if args == ["branch", "--show-current"]:
            return "main"
        if args == ["log", "-12", "--oneline"]:
            return "abcdef1 test commit"
        raise AssertionError(args)

    def fake_capture(command: list[str]) -> review_packet_bundle.CommandOutput:
        return review_packet_bundle.CommandOutput(
            command=command,
            returncode=0,
            stdout='{"secret_free": true}\n' if "release_evidence.py" in command else "ok\n",
            stderr="",
        )

    monkeypatch.setattr(review_packet_bundle, "_git", fake_git)
    monkeypatch.setattr(review_packet_bundle, "_run_capture", fake_capture)

    result = review_packet_bundle.build_bundle(
        repo_root=tmp_path,
        output_root=tmp_path / "var/review-packets/v0.2",
        allow_dirty=False,
        run_release_check=True,
    )

    assert result.path.joinpath("INDEX.md").exists()
    assert result.path.joinpath("release-check.txt").exists()
    assert result.path.joinpath("release-evidence.json").exists()
    assert result.path.joinpath("release-packet.md").exists()
    assert result.path.joinpath("release-packet.json").exists()
    assert result.path.joinpath("review-doc-hashes.json").exists()
    assert result.path.joinpath("artifact-hashes.json").exists()
    assert result.path.joinpath("git-summary.txt").exists()
    assert result.path.joinpath("docs/README.md").exists()
    assert result.path.joinpath("docs/docs/codex/v0.2-review-packet.md").exists()
    assert result.path.joinpath("signed-evidence-demo/SIGNED_EVIDENCE_DEMO.md").exists()
    assert result.path.joinpath(
        "negative-review-transcripts/NEGATIVE_REVIEW_TRANSCRIPTS.md"
    ).exists()
    artifact_hashes = json.loads(
        result.path.joinpath("artifact-hashes.json").read_text(encoding="utf-8")
    )
    artifact_paths = {artifact["path"] for artifact in artifact_hashes}
    assert "INDEX.md" in artifact_paths
    assert "release-check.txt" in artifact_paths
    assert "release-evidence.json" in artifact_paths
    assert "release-packet.md" in artifact_paths
    assert "release-packet.json" in artifact_paths
    assert "review-doc-hashes.json" in artifact_paths
    assert "docs/README.md" in artifact_paths
    assert "signed-evidence-demo/SIGNED_EVIDENCE_DEMO.md" in artifact_paths
    assert "negative-review-transcripts/NEGATIVE_REVIEW_TRANSCRIPTS.md" in artifact_paths
    bundle_paths = [path.as_posix() for path in result.path.rglob("*")]
    assert not any("/.env" in path for path in bundle_paths)
    assert not any("/var/keys/" in path for path in bundle_paths)
    assert "review-doc-hashes.json" in result.path.joinpath("INDEX.md").read_text(
        encoding="utf-8"
    )
    assert "artifact-hashes.json" in result.path.joinpath("INDEX.md").read_text(
        encoding="utf-8"
    )


def test_release_evidence_records_attached_release_check_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    transcript = tmp_path / "release-check.txt"
    transcript.write_text("passed\n", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "release_evidence.py",
            "--release-check-transcript",
            transcript.as_posix(),
            "--release-check-observed-status",
            "passed",
            "--release-check-commit",
            "abc123",
        ],
    )

    result = release_evidence.main()

    assert result == 0
    output = capsys.readouterr().out
    assert '"gate_executed_by_release_packet": false' in output
    assert '"gate_status": "not_run"' in output
    assert '"attached_transcript_exists": true' in output
    assert '"attached_transcript_status": "passed"' in output
    assert '"attached_transcript_commit": "abc123"' in output


def _write_project_markers(root: Path) -> None:
    directory_markers = {"apps/api", "apps/mcp-server"}
    for marker in review_packet_bundle.PROJECT_MARKERS:
        path = root / marker
        if marker in directory_markers:
            path.mkdir(parents=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("", encoding="utf-8")

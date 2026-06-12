from __future__ import annotations

import json
from pathlib import Path

from scripts import manifest_change_review


def test_manifest_change_review_passes_without_manifest_changes() -> None:
    result = manifest_change_review.evaluate_manifest_change_review(
        changed_files=[],
        tool_names=["fs.read"],
    )

    assert result.passed is True
    assert result.tool_count == 1


def test_manifest_change_review_requires_lock_for_manifest_changes() -> None:
    result = manifest_change_review.evaluate_manifest_change_review(
        changed_files=["tool-manifests/fs-read.yaml"],
        tool_names=["fs.read"],
    )

    assert result.passed is False
    assert result.failures == [
        "tool manifest changes require tool-manifests.lock.json changes"
    ]


def test_manifest_change_review_requires_manifest_for_lock_changes() -> None:
    result = manifest_change_review.evaluate_manifest_change_review(
        changed_files=["tool-manifests.lock.json"],
        tool_names=["fs.read"],
    )

    assert result.passed is False
    assert result.failures == [
        "manifest lock changes require an accompanying manifest change"
    ]


def test_manifest_change_review_rejects_non_yaml_manifest_dir_changes() -> None:
    result = manifest_change_review.evaluate_manifest_change_review(
        changed_files=["tool-manifests/README.md", "tool-manifests.lock.json"],
        tool_names=["fs.read"],
    )

    assert result.passed is False
    assert "tool-manifests changes must be YAML manifests only" in result.failures


def test_manifest_change_review_json_shape_for_current_repo() -> None:
    result = manifest_change_review.run_review(Path("."))
    payload = result.as_dict()
    tool_names = payload.get("tool_names")

    assert result.passed is True
    assert payload["tool_count"] == 16
    assert isinstance(tool_names, list)
    assert "git.show.commit_metadata" in tool_names
    assert "http.fetch" in tool_names
    assert "project.structure.summary" in tool_names
    assert "project.test.summary" in tool_names
    json.dumps(payload)

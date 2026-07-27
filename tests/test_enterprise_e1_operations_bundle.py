from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import enterprise_e1_operations_bundle as bundle

FIXTURE = bundle.ROOT / "tests/fixtures/enterprise-e1-operations-input.json"


def _input(tmp_path: Path) -> Path:
    target = tmp_path / "input.json"
    target.write_bytes(FIXTURE.read_bytes())
    return target


def test_bundle_is_deterministic_redacted_and_offline_verifiable(
    tmp_path: Path,
) -> None:
    first = bundle.build_bundle(
        root=bundle.ROOT,
        input_path=_input(tmp_path),
        output_dir=tmp_path / "first",
    )
    second = bundle.build_bundle(
        root=bundle.ROOT,
        input_path=_input(tmp_path),
        output_dir=tmp_path / "second",
    )

    assert first["archive_sha256"] == second["archive_sha256"]
    assert (tmp_path / "first.zip").read_bytes() == (tmp_path / "second.zip").read_bytes()
    rendered = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((tmp_path / "first").rglob("*"))
        if path.is_file()
    )
    assert "must-not-leak" not in rendered
    assert "/must/not/leak" not in rendered
    assert "[REDACTED]" in rendered
    directory_report = bundle.verify_bundle(root=bundle.ROOT, bundle=tmp_path / "first")
    archive_report = bundle.verify_bundle(
        root=bundle.ROOT, bundle=tmp_path / "first.zip"
    )
    assert directory_report == archive_report
    assert archive_report["tool_count"] == 24
    assert archive_report["section_count"] == 7
    assert archive_report["local_content_integrity_only"] is True
    assert archive_report["external_notarization_claimed"] is False
    assert archive_report["human_uat_complete"] is False


def test_bundle_rejects_missing_section_and_existing_output(tmp_path: Path) -> None:
    value = json.loads(FIXTURE.read_text(encoding="utf-8"))
    del value["sections"]["audit"]
    input_path = tmp_path / "invalid.json"
    input_path.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(bundle.OperationsBundleError, match="sections are not exact"):
        bundle.build_bundle(
            root=bundle.ROOT,
            input_path=input_path,
            output_dir=tmp_path / "missing",
        )

    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(bundle.OperationsBundleError, match="already exists"):
        bundle.build_bundle(
            root=bundle.ROOT,
            input_path=_input(tmp_path),
            output_dir=output,
        )


def test_bundle_verifier_rejects_mutation_and_unmanifested_member(
    tmp_path: Path,
) -> None:
    output = tmp_path / "bundle"
    bundle.build_bundle(
        root=bundle.ROOT,
        input_path=_input(tmp_path),
        output_dir=output,
    )
    deployment = output / "sections/deployment.json"
    original_deployment = deployment.read_bytes()
    deployment.write_text('{"status":"changed"}\n', encoding="utf-8")
    with pytest.raises(bundle.OperationsBundleError, match="digest mismatch"):
        bundle.verify_bundle(root=bundle.ROOT, bundle=output)

    deployment.write_bytes(original_deployment)
    (output / "unexpected.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(bundle.OperationsBundleError, match="unmanifested"):
        bundle.verify_bundle(root=bundle.ROOT, bundle=output)

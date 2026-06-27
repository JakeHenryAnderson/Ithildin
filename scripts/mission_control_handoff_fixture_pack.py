"""Generate Mission Control handoff importer fixtures."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    hello_world_mission_control_handoff,
    mission_control_handoff_negative_fixtures_check,
    review_docs,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/mission-control-handoff-fixture-pack.md"
DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/mission-control-handoff-fixtures")
INDEX_NAME = "MISSION_CONTROL_HANDOFF_FIXTURE_PACK.md"
SUMMARY_NAME = "fixture-summary.json"
VALID_NAME = "valid/mission-control-handoff-valid.json"
HASH_NAME = "mission-control-handoff-fixture-artifact-hashes.json"

BOUNDARY_FLAGS = {
    "runtime_changes_allowed": False,
    "mission_control_runtime_allowed": False,
    "mission_control_execution_allowed": False,
    "mission_control_policy_authority_allowed": False,
    "mission_control_approval_authority_allowed": False,
    "mission_control_audit_authority_allowed": False,
    "local_model_invocation_allowed": False,
    "sandbox_orchestration_allowed": False,
    "trusted_host_promotion_allowed": False,
    "new_power_classes_allowed": False,
}


class MissionControlHandoffFixturePackError(RuntimeError):
    """Raised when the fixture pack cannot be generated or validated."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.check:
        report = build_check_report(ROOT)
        print(render_check_report(report))
        return 0 if report["valid"] else 1

    try:
        output_dir = build_fixture_pack(ROOT, args.output_dir)
    except MissionControlHandoffFixturePackError as exc:
        print(f"Mission Control handoff fixture pack failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built Mission Control handoff fixture pack at {output_dir}")
    return 0


def build_fixture_pack(repo_root: Path, output_dir: Path) -> Path:
    _validate_repo_root(repo_root)
    seed = _build_seed_payload()
    seed_reasons = mission_control_handoff_negative_fixtures_check._validate_for_display_import(
        seed
    )
    if seed_reasons:
        raise MissionControlHandoffFixturePackError(
            "positive seed payload failed fixture validation: " + ", ".join(seed_reasons)
        )

    cases = _negative_case_payloads(seed)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    output_dir.joinpath("valid").mkdir()
    output_dir.joinpath("negatives").mkdir()

    _write_json(output_dir / VALID_NAME, seed)
    negative_entries = []
    for case in cases:
        rel_path = Path("negatives") / f"{case['id']}-{case['label']}.json"
        _write_json(output_dir / rel_path, case["payload"])
        negative_entries.append(
            {
                "id": case["id"],
                "label": case["label"],
                "path": rel_path.as_posix(),
                "expected_accept": False,
                "expected_reasons": case["reasons"],
            }
        )

    summary = {
        "schema_version": "1",
        "fixture_pack_type": "ithildin.mission_control_handoff.fixture_pack",
        "status": "display_import_test_fixtures",
        "tool_count": 24,
        "valid_payload": {
            "path": VALID_NAME,
            "expected_accept": True,
            "expected_reasons": [],
        },
        "negative_case_count": len(negative_entries),
        "negative_cases": negative_entries,
        "safe_error_reason_labels_only": True,
        "forbidden_runtime_authority": BOUNDARY_FLAGS,
    }
    _write_json(output_dir / SUMMARY_NAME, summary)
    output_dir.joinpath(INDEX_NAME).write_text(_render_index(summary), encoding="utf-8")
    _write_json(output_dir / HASH_NAME, _artifact_hashes(output_dir))
    return output_dir


def build_check_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    try:
        output_dir = build_fixture_pack(repo_root, DEFAULT_OUTPUT_DIR)
    except MissionControlHandoffFixturePackError as exc:
        failures.append(str(exc))
        output_dir = DEFAULT_OUTPUT_DIR

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    v1_packet = _read(repo_root / "scripts/v1_rc_packet.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    schema_contract = _read(repo_root / "docs/codex/mission-control-handoff-schema-contract.md")
    negative_doc = _read(repo_root / "docs/codex/mission-control-handoff-negative-fixtures.md")
    implementation_ticket = _read(
        repo_root / "docs/codex/mission-control-integration-implementation-ticket.md"
    )
    doc = _read(repo_root / DOC_REL)
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    review_candidate_body = makefile.partition("review-candidate:")[2].partition("\n\n")[0]
    summary_text = _read(output_dir / SUMMARY_NAME)
    index_text = _read(output_dir / INDEX_NAME)
    hash_text = _read(output_dir / HASH_NAME)

    try:
        summary = json.loads(summary_text) if summary_text else {}
    except json.JSONDecodeError:
        summary = {}
        failures.append("Mission Control handoff fixture summary is not valid JSON")
    try:
        hash_manifest = json.loads(hash_text) if hash_text else {"artifacts": []}
    except json.JSONDecodeError:
        hash_manifest = {"artifacts": []}
        failures.append("Mission Control handoff fixture hashes are not valid JSON")

    for phrase in [
        "Status: generated fixture pack for Mission Control display/import tests.",
        "make mission-control-handoff-fixture-pack",
        "make mission-control-handoff-fixture-pack-check",
        "display/import fixtures only",
        "does not add Mission Control runtime behavior",
        "does not approve callbacks into Ithildin",
        "MC-HANDOFF-NEG-001",
        "MC-HANDOFF-NEG-014",
    ]:
        if phrase not in doc:
            failures.append(f"fixture pack doc is missing phrase: {phrase}")
    for phrase in [
        "Mission Control Handoff Fixture Pack",
        "Valid Fixture",
        "Negative Fixtures",
        "MC-HANDOFF-NEG-001",
        "MC-HANDOFF-NEG-014",
        "runtime_changes_allowed: `false`",
        "mission_control_runtime_allowed: `false`",
    ]:
        if phrase not in index_text:
            failures.append(f"generated fixture index is missing phrase: {phrase}")

    if summary.get("fixture_pack_type") != "ithildin.mission_control_handoff.fixture_pack":
        failures.append("fixture summary has the wrong type")
    if summary.get("tool_count") != 24:
        failures.append("fixture summary tool_count must remain 24")
    if summary.get("negative_case_count") != 14:
        failures.append("fixture summary must include 14 negative cases")
    if summary.get("safe_error_reason_labels_only") is not True:
        failures.append("fixture summary must require safe reason labels")
    boundaries = summary.get("forbidden_runtime_authority")
    if not isinstance(boundaries, dict):
        failures.append("fixture summary is missing forbidden runtime authority flags")
    else:
        for key in BOUNDARY_FLAGS:
            if boundaries.get(key) is not False:
                failures.append(f"fixture boundary flag must be false: {key}")

    hashed_paths = {artifact.get("path") for artifact in hash_manifest.get("artifacts", [])}
    if not {INDEX_NAME, SUMMARY_NAME, VALID_NAME}.issubset(hashed_paths):
        failures.append("fixture hash manifest is missing required top-level artifacts")
    negative_hashes = [path for path in hashed_paths if str(path).startswith("negatives/")]
    if len(negative_hashes) != 14:
        failures.append("fixture hash manifest must include 14 negative fixture files")
    if HASH_NAME in hashed_paths:
        failures.append("fixture hash manifest must not hash itself")
    if not _artifact_hashes_match_files(output_dir, hash_manifest):
        failures.append("fixture artifact hashes do not match files")

    if "mission-control-handoff-fixture-pack:" not in makefile:
        failures.append("Make target is missing: mission-control-handoff-fixture-pack")
    if "mission-control-handoff-fixture-pack-check:" not in makefile:
        failures.append("Make target is missing: mission-control-handoff-fixture-pack-check")
    if "mission-control-handoff-fixture-pack-check" not in release_check_body:
        failures.append("fixture pack check is missing from release-check")
    if "$(MAKE) mission-control-handoff-fixture-pack" not in review_candidate_body:
        failures.append("fixture pack generation is missing from review-candidate")
    if "make mission-control-handoff-fixture-pack" not in readme:
        failures.append("README is missing fixture pack command")
    if DOC_REL not in docs_site:
        failures.append("fixture pack doc is missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("fixture pack doc is missing from review docs")
    if DOC_REL not in v1_packet:
        failures.append("fixture pack doc is missing from v1 RC packet")
    if "Mission Control Handoff Fixture Pack" not in review_index:
        failures.append("review-docs index is missing fixture pack doc")
    if "mission-control-handoff-fixture-pack-check" not in release_guardrails:
        failures.append("release guardrails do not require fixture pack check")
    if "mission-control-handoff-fixture-pack" not in schema_contract:
        failures.append("schema contract is missing fixture pack pointer")
    if "mission-control-handoff-fixture-pack" not in negative_doc:
        failures.append("negative fixture doc is missing fixture pack pointer")
    if "mission-control-handoff-fixture-pack" not in implementation_ticket:
        failures.append("implementation ticket is missing fixture pack pointer")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "fixture_pack_doc": DOC_REL,
        "output_dir": output_dir.as_posix(),
        "negative_case_count": summary.get("negative_case_count"),
        "negative_fixture_files": len(negative_hashes),
        "tool_count": 24,
        "artifact_hashes_match_files": _artifact_hashes_match_files(
            output_dir, hash_manifest
        ),
        **BOUNDARY_FLAGS,
    }


def _build_seed_payload() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "mission-control-handoff"
        hello_world_mission_control_handoff.build_handoff(output_dir)
        return cast(
            dict[str, Any],
            json.loads(
                output_dir.joinpath(hello_world_mission_control_handoff.JSON_NAME).read_text(
                    encoding="utf-8"
                )
            ),
        )


def _negative_case_payloads(seed: dict[str, Any]) -> list[dict[str, Any]]:
    case_results = mission_control_handoff_negative_fixtures_check._run_negative_cases(seed)
    cases = []
    case_definitions = _case_definitions()
    for result in case_results:
        payload = copy.deepcopy(seed)
        case_definitions[result["id"]](payload)
        reasons = mission_control_handoff_negative_fixtures_check._validate_for_display_import(
            payload
        )
        if not reasons:
            raise MissionControlHandoffFixturePackError(
                f"negative fixture would be accepted: {result['id']}"
            )
        if sorted(result["reasons"]) != reasons:
            raise MissionControlHandoffFixturePackError(
                f"negative fixture reason drift for {result['id']}"
            )
        cases.append(
            {
                "id": result["id"],
                "label": result["label"],
                "reasons": reasons,
                "payload": payload,
            }
        )
    return cases


def _case_definitions() -> dict[str, mission_control_handoff_negative_fixtures_check.Mutator]:
    return {
        "MC-HANDOFF-NEG-001": mission_control_handoff_negative_fixtures_check._pop_key(
            "schema_version"
        ),
        "MC-HANDOFF-NEG-002": mission_control_handoff_negative_fixtures_check._set(
            "schema_version", "999"
        ),
        "MC-HANDOFF-NEG-003": mission_control_handoff_negative_fixtures_check._set(
            "status", "live_integration"
        ),
        "MC-HANDOFF-NEG-004": mission_control_handoff_negative_fixtures_check._set(
            "mission_control_runtime_behavior", True
        ),
        "MC-HANDOFF-NEG-005": mission_control_handoff_negative_fixtures_check._set(
            "host_promotion_performed", True
        ),
        "MC-HANDOFF-NEG-006": mission_control_handoff_negative_fixtures_check._set(
            "ithildin_remains_policy_authority", False
        ),
        "MC-HANDOFF-NEG-007": mission_control_handoff_negative_fixtures_check._set_attachment_path(
            "/tmp/secret"
        ),
        "MC-HANDOFF-NEG-008": mission_control_handoff_negative_fixtures_check._set_attachment_path(
            "../secret"
        ),
        "MC-HANDOFF-NEG-009": mission_control_handoff_negative_fixtures_check._pop_key(
            "display_contract"
        ),
        "MC-HANDOFF-NEG-010": mission_control_handoff_negative_fixtures_check._remove_hide_field(
            "tokens"
        ),
        "MC-HANDOFF-NEG-011": mission_control_handoff_negative_fixtures_check._remove_warning_chip(
            "host_promotion_not_performed"
        ),
        "MC-HANDOFF-NEG-012": mission_control_handoff_negative_fixtures_check._set(
            "mission_control_authority", "executor_authority"
        ),
        "MC-HANDOFF-NEG-013": mission_control_handoff_negative_fixtures_check._inject(
            "file_contents", "hello"
        ),
        "MC-HANDOFF-NEG-014": mission_control_handoff_negative_fixtures_check._inject(
            "raw_prompt", "summarize this"
        ),
    }


def _render_index(summary: dict[str, Any]) -> str:
    negative_rows = "\n".join(
        "| `{id}` | `{label}` | `{path}` | `{reasons}` |".format(
            id=case["id"],
            label=case["label"],
            path=case["path"],
            reasons=", ".join(case["expected_reasons"]),
        )
        for case in summary["negative_cases"]
    )
    boundaries = "\n".join(
        f"- {key}: `{str(value).lower()}`"
        for key, value in summary["forbidden_runtime_authority"].items()
    )
    return f"""# Mission Control Handoff Fixture Pack

Status: generated display/import fixtures for Mission Control tests.

This packet contains one valid metadata-only Mission Control handoff payload and fourteen negative
payloads derived from the same seed. It is for importer tests only; it does not call Mission
Control, call Ithildin APIs, create approvals, start a VM/container, invoke a local model, or
promote artifacts to the host.

## Valid Fixture

- path: `{summary["valid_payload"]["path"]}`
- expected_accept: `true`

## Negative Fixtures

| Fixture ID | Label | Path | Expected reason labels |
| --- | --- | --- | --- |
{negative_rows}

## Boundary Flags

{boundaries}

## Consumer Expectations

Mission Control may use these fixtures to test display/import validation. It should accept the
valid fixture as metadata-only evidence and reject the negative fixtures with safe reason labels
only. It must not display raw prompts, file contents, raw host paths, environment values, tokens,
private keys, response bodies, dependency names, package script values, or sandbox internals.
"""


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Mission Control handoff fixture pack check",
        f"valid: {str(report['valid']).lower()}",
        f"fixture_pack_doc: {report['fixture_pack_doc']}",
        f"output_dir: {report['output_dir']}",
        f"negative_case_count: {report['negative_case_count']}",
        f"negative_fixture_files: {report['negative_fixture_files']}",
        f"tool_count: {report['tool_count']}",
        f"artifact_hashes_match_files: {str(report['artifact_hashes_match_files']).lower()}",
    ]
    lines.extend(f"{key}: {str(value).lower()}" for key, value in BOUNDARY_FLAGS.items())
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _validate_repo_root(repo_root: Path) -> None:
    missing = [
        marker
        for marker in ["pyproject.toml", "Makefile", "tool-manifests.lock.json"]
        if not (repo_root / marker).exists()
    ]
    if missing:
        raise MissionControlHandoffFixturePackError(
            "must be run from the Ithildin repo root; missing " + ", ".join(missing)
        )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _artifact_hashes(output_dir: Path) -> dict[str, Any]:
    artifacts = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name == HASH_NAME:
            continue
        data = path.read_bytes()
        artifacts.append(
            {
                "path": path.relative_to(output_dir).as_posix(),
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return {
        "schema_version": "1",
        "artifacts": artifacts,
        "artifact_count": len(artifacts),
        "hash_manifest_self_hashed": False,
    }


def _artifact_hashes_match_files(output_dir: Path, hashes: dict[str, Any]) -> bool:
    for artifact in hashes.get("artifacts", []):
        path = output_dir / artifact.get("path", "")
        if not path.is_file():
            return False
        data = path.read_bytes()
        if artifact.get("bytes") != len(data):
            return False
        if artifact.get("sha256") != hashlib.sha256(data).hexdigest():
            return False
    return True


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())

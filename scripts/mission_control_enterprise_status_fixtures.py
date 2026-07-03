"""Generate Mission Control enterprise status importer fixtures."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import enterprise_status_export, review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/mission-control-enterprise-status-fixtures.md"
DOC_TITLE = "Mission Control Enterprise Status Fixtures"
DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/mission-control-enterprise-status-fixtures")
INDEX_NAME = "MISSION_CONTROL_ENTERPRISE_STATUS_FIXTURES.md"
SUMMARY_NAME = "fixture-summary.json"
VALID_NAME = "valid/enterprise-status-valid.json"
HASH_NAME = "mission-control-enterprise-status-fixture-artifact-hashes.json"

BOUNDARY_FLAGS = {
    "runtime_changes_allowed": False,
    "mission_control_runtime_allowed": False,
    "mission_control_execution_allowed": False,
    "mission_control_policy_authority_allowed": False,
    "mission_control_approval_authority_allowed": False,
    "mission_control_audit_authority_allowed": False,
    "polling_or_mutating_ithildin_apis_allowed": False,
    "local_model_invocation_allowed": False,
    "live_vm_inspection_allowed": False,
    "sandbox_orchestration_allowed": False,
    "trusted_host_promotion_allowed": False,
    "siem_adapter_allowed": False,
    "compliance_automation_allowed": False,
    "public_security_product_positioning_allowed": False,
    "new_power_classes_allowed": False,
}

FORBIDDEN_PAYLOAD_KEYS = {
    "file_contents",
    "raw_prompt",
    "raw_model_prompt",
    "chain_of_thought",
    "private_key",
    "private_keys",
    "token",
    "tokens",
    "environment_values",
    "response_body",
}

ALLOWED_ACTION_COMMANDS = {
    "make release-check",
    "make review-candidate",
    "make enterprise-review-send-refresh",
    "make handoff-dry-run",
    "make enterprise-send-quick-check",
    "make enterprise-send-now",
    "make enterprise-response-intake-refresh",
    "make sandbox-vm-live-poc-runtime-ticket-check",
    "make sandbox-vm-live-poc-runtime-ticket-review-bundle",
    "make sandbox-vm-live-poc-runtime-ticket-review-bundle-check",
    "make sandbox-vm-live-poc-runtime-ticket-internal-review-check",
    "make sandbox-vm-live-poc-runtime-implementation-gate-check",
    "make sandbox-vm-live-poc-runtime-descriptor-contract-check",
    "make sandbox-vm-live-poc-runtime-descriptor-contract-internal-review-check",
    "make sandbox-vm-live-poc-runtime-gate-readiness-review-bundle-check",
    "make sandbox-vm-live-poc-runtime-gate-readiness-internal-review-check",
    "make sandbox-vm-live-poc-runtime-gate-readiness-decision-record-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-plan-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-implementation-ticket-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-implementation-decision-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-implementation-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-internal-source-review-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-ticket-review-bundle-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-source-review-bundle-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-external-response-intake-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-response-inbox-check",
    "make sandbox-vm-live-poc-runtime-descriptor-only-response-dry-run",
    "make sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight-check",
    "make sandbox-vm-live-poc-runtime-gate-readiness-response-intake-check",
    "make sandbox-vm-live-poc-runtime-gate-readiness-response-dry-run",
    "make sandbox-vm-live-poc-runtime-gate-readiness-response-application-record-check",
    "make sandbox-vm-live-poc-runtime-gate-readiness-response-application-playbook-check",
    "make sandbox-vm-live-poc-runtime-gate-readiness-response-application-preflight-check",
    "make sandbox-vm-live-poc-runtime-gate-readiness-decision-record-skeleton-check",
    "make sandbox-vm-live-poc-prerequisite-disposition-dry-run",
    "make sandbox-vm-live-poc-decision-packet-check",
    "make no-new-powers-guardrail",
    "make tool-surface-invariant-gate",
}

SAFE_HANDOFF_ARTIFACT_PATH_PREFIXES = (
    "docs/codex/",
    "var/review-packets/v3/",
    "var/review-runs/",
)

Mutator = Callable[[dict[str, Any]], None]


class MissionControlEnterpriseStatusFixtureError(RuntimeError):
    """Raised when the enterprise status fixture pack cannot be generated."""


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
    except MissionControlEnterpriseStatusFixtureError as exc:
        print(f"Mission Control enterprise status fixture pack failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built Mission Control enterprise status fixtures at {output_dir}")
    return 0


def build_fixture_pack(repo_root: Path, output_dir: Path) -> Path:
    _validate_repo_root(repo_root)
    seed = _build_seed_payload(repo_root)
    seed_reasons = _validate_for_display_import(seed)
    if seed_reasons:
        raise MissionControlEnterpriseStatusFixtureError(
            "positive enterprise status payload failed validation: "
            + ", ".join(seed_reasons)
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
        "fixture_pack_type": "ithildin.mission_control_enterprise_status.fixture_pack",
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
    except MissionControlEnterpriseStatusFixtureError as exc:
        failures.append(str(exc))
        output_dir = DEFAULT_OUTPUT_DIR

    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    v1_packet = _read(repo_root / "scripts/v1_rc_packet.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    contract_doc = _read(
        repo_root / "docs/codex/mission-control-enterprise-status-import-contract.md"
    )
    export_doc = _read(repo_root / enterprise_status_export.DOC_REL)
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
        failures.append("enterprise status fixture summary is not valid JSON")
    try:
        hash_manifest = json.loads(hash_text) if hash_text else {"artifacts": []}
    except json.JSONDecodeError:
        hash_manifest = {"artifacts": []}
        failures.append("enterprise status fixture hashes are not valid JSON")

    for phrase in [
        "Status: generated fixture pack for Mission Control enterprise status "
        "display/import tests.",
        "make mission-control-enterprise-status-fixtures",
        "make mission-control-enterprise-status-fixtures-check",
        "make mission-control-enterprise-status-import-check",
        "display/import fixtures only",
        "does not add Mission Control runtime behavior",
        "does not approve callbacks into Ithildin",
        "MC-STATUS-NEG-001",
        "MC-STATUS-NEG-011",
    ]:
        if phrase not in doc:
            failures.append(f"enterprise status fixture doc is missing phrase: {phrase}")
    for phrase in [
        "Mission Control Enterprise Status Fixtures",
        "Valid Fixture",
        "Negative Fixtures",
        "MC-STATUS-NEG-001",
        "MC-STATUS-NEG-011",
        "MC-STATUS-NEG-012",
        "unsupported_action_command",
        "unsafe_handoff_artifact",
        "runtime_changes_allowed: `false`",
        "mission_control_runtime_allowed: `false`",
    ]:
        if phrase not in index_text:
            failures.append(
                f"generated enterprise status fixture index is missing phrase: {phrase}"
            )

    if summary.get("fixture_pack_type") != (
        "ithildin.mission_control_enterprise_status.fixture_pack"
    ):
        failures.append("enterprise status fixture summary has the wrong type")
    if summary.get("tool_count") != 24:
        failures.append("enterprise status fixture summary tool_count must remain 24")
    if summary.get("negative_case_count") != 12:
        failures.append("enterprise status fixture summary must include 12 negative cases")
    if summary.get("safe_error_reason_labels_only") is not True:
        failures.append("enterprise status fixture summary must require safe reason labels")
    boundaries = summary.get("forbidden_runtime_authority")
    if not isinstance(boundaries, dict):
        failures.append("enterprise status fixture summary is missing forbidden authority flags")
    else:
        for key in BOUNDARY_FLAGS:
            if boundaries.get(key) is not False:
                failures.append(f"enterprise status fixture boundary flag must be false: {key}")

    hashed_paths = {artifact.get("path") for artifact in hash_manifest.get("artifacts", [])}
    if not {INDEX_NAME, SUMMARY_NAME, VALID_NAME}.issubset(hashed_paths):
        failures.append("enterprise status fixture hash manifest is missing required artifacts")
    negative_hashes = [path for path in hashed_paths if str(path).startswith("negatives/")]
    if len(negative_hashes) != 12:
        failures.append("enterprise status fixture hash manifest must include 12 negative files")
    if HASH_NAME in hashed_paths:
        failures.append("enterprise status fixture hash manifest must not hash itself")
    if not _artifact_hashes_match_files(output_dir, hash_manifest):
        failures.append("enterprise status fixture artifact hashes do not match files")

    if "mission-control-enterprise-status-fixtures:" not in makefile:
        failures.append("Make target is missing: mission-control-enterprise-status-fixtures")
    if "mission-control-enterprise-status-fixtures-check:" not in makefile:
        failures.append("Make target is missing: mission-control-enterprise-status-fixtures-check")
    if (
        "mission-control-enterprise-status-fixtures-check" not in release_check_body
        and "release-check: mission-control-enterprise-status-fixtures-check" not in makefile
    ):
        failures.append("enterprise status fixture check is missing from release-check")
    if "$(MAKE) mission-control-enterprise-status-fixtures" not in review_candidate_body:
        failures.append("enterprise status fixture generation is missing from review-candidate")
    if "make mission-control-enterprise-status-fixtures" not in readme:
        failures.append("README is missing enterprise status fixture command")
    if DOC_REL not in docs_site:
        failures.append("enterprise status fixture doc is missing from docs-site inputs")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("enterprise status fixture doc is missing from review docs")
    if DOC_REL not in v1_packet:
        failures.append("enterprise status fixture doc is missing from v1 RC packet")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing enterprise status fixture doc")
    if "mission-control-enterprise-status-fixtures-check" not in release_guardrails:
        failures.append("release guardrails do not require enterprise status fixture check")
    if "mission-control-enterprise-status-fixtures" not in contract_doc:
        failures.append("enterprise status import contract is missing fixture pointer")
    if "mission-control-enterprise-status-fixtures" not in export_doc:
        failures.append("enterprise status export doc is missing fixture pointer")

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


def _build_seed_payload(repo_root: Path) -> dict[str, Any]:
    return enterprise_status_export.build_report(repo_root)


def _negative_case_payloads(seed: dict[str, Any]) -> list[dict[str, Any]]:
    cases = []
    for case_id, label, mutator in _case_definitions():
        payload = copy.deepcopy(seed)
        mutator(payload)
        reasons = _validate_for_display_import(payload)
        if not reasons:
            raise MissionControlEnterpriseStatusFixtureError(
                f"negative fixture would be accepted: {case_id}"
            )
        cases.append(
            {
                "id": case_id,
                "label": label,
                "reasons": reasons,
                "payload": payload,
            }
        )
    return cases


def _case_definitions() -> list[tuple[str, str, Mutator]]:
    return [
        ("MC-STATUS-NEG-001", "missing_schema_version", _pop_key("schema_version")),
        ("MC-STATUS-NEG-002", "unsupported_schema_version", _set("schema_version", "999")),
        ("MC-STATUS-NEG-003", "wrong_artifact_type", _set("artifact_type", "unknown")),
        ("MC-STATUS-NEG-004", "non_display_status", _set("status", "runtime_status")),
        (
            "MC-STATUS-NEG-005",
            "mission_control_runtime_true",
            _set("mission_control_runtime_allowed", True),
        ),
        (
            "MC-STATUS-NEG-006",
            "sandbox_orchestration_true",
            _set("sandbox_orchestration_allowed", True),
        ),
        (
            "MC-STATUS-NEG-007",
            "new_power_classes_true",
            _set("new_power_classes_allowed", True),
        ),
        (
            "MC-STATUS-NEG-008",
            "closure_without_response",
            _set_multiple({"closure_ready_count": 1, "response_present_count": 0}),
        ),
        ("MC-STATUS-NEG-009", "raw_prompt", _inject("raw_prompt", "summarize this")),
        ("MC-STATUS-NEG-010", "raw_file_contents", _inject("file_contents", "secret")),
        (
            "MC-STATUS-NEG-011",
            "unsafe_action_command",
            _set("action_commands", ["make enterprise-review-send-refresh", "rm -rf /"]),
        ),
        (
            "MC-STATUS-NEG-012",
            "unsafe_handoff_artifact",
            _set(
                "handoff_artifacts",
                [
                    {
                        "label": "unsafe",
                        "path": "/tmp/unsafe-host-path",
                        "description": "absolute host path must not be display-imported",
                    }
                ],
            ),
        ),
    ]


def _validate_for_display_import(payload: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if payload.get("schema_version") != "1":
        reasons.append("unsupported_schema_version")
    if payload.get("artifact_type") != "ithildin.enterprise_status_export":
        reasons.append("unsupported_artifact_type")
    if payload.get("status") != "display_only":
        reasons.append("status_must_be_display_only")
    if payload.get("tool_count") != 24:
        reasons.append("unexpected_tool_count")

    for key in [
        "runtime_changes_allowed",
        "mission_control_runtime_allowed",
        "live_vm_inspection_allowed",
        "sandbox_orchestration_allowed",
        "trusted_host_promotion_allowed",
        "siem_adapter_allowed",
        "compliance_automation_allowed",
        "public_security_product_positioning_allowed",
        "new_power_classes_allowed",
    ]:
        if payload.get(key) is not False:
            reasons.append(f"{key}_must_be_false")

    if payload.get("closure_ready_count") not in {0, None} and payload.get(
        "response_present_count"
    ) == 0:
        reasons.append("closure_claim_requires_normalized_response")
    action_commands = payload.get("action_commands")
    if not isinstance(action_commands, list) or not action_commands:
        reasons.append("action_commands_must_be_safe_list")
    elif any(command not in ALLOWED_ACTION_COMMANDS for command in action_commands):
        reasons.append("unsupported_action_command")
    handoff_artifacts = payload.get("handoff_artifacts")
    if not isinstance(handoff_artifacts, list) or not handoff_artifacts:
        reasons.append("handoff_artifacts_must_be_safe_list")
    else:
        for artifact in handoff_artifacts:
            if not _safe_handoff_artifact(artifact):
                reasons.append("unsafe_handoff_artifact")
                break
    if _contains_forbidden_key(payload):
        reasons.append("forbidden_payload_field")
    return sorted(set(reasons))


def _safe_handoff_artifact(artifact: Any) -> bool:
    if not isinstance(artifact, Mapping):
        return False
    label = artifact.get("label")
    path = artifact.get("path")
    description = artifact.get("description")
    if not isinstance(label, str) or not label:
        return False
    if not isinstance(path, str) or not path:
        return False
    if not isinstance(description, str) or not description:
        return False
    if path.startswith("/") or ".." in Path(path).parts:
        return False
    return path.startswith(SAFE_HANDOFF_ARTIFACT_PATH_PREFIXES)


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
    return f"""# Mission Control Enterprise Status Fixtures

Status: generated display/import fixtures for Mission Control enterprise status tests.

This packet contains one valid display-only enterprise status export payload and twelve negative
payloads derived from the same seed. It is for importer tests only; it does not call Mission
Control, call Ithildin APIs, create approvals, start a VM/container, invoke a local model, close
enterprise lanes, or grant runtime authority.

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

Mission Control may use these fixtures to test display/import validation. It should accept the valid
fixture as non-authoritative display status and reject the negative fixtures with safe reason labels
only. It must not display raw prompts, file contents, raw host paths, environment values, tokens,
private keys, response bodies, dependency names, package script values, arbitrary JSON subtrees, or
sandbox internals.
"""


def render_check_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Mission Control enterprise status fixture pack check",
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
        raise MissionControlEnterpriseStatusFixtureError(
            "must be run from the Ithildin repo root; missing " + ", ".join(missing)
        )


def _set(key: str, value: Any) -> Mutator:
    def mutate(payload: dict[str, Any]) -> None:
        payload[key] = value

    return mutate


def _set_multiple(values: dict[str, Any]) -> Mutator:
    def mutate(payload: dict[str, Any]) -> None:
        payload.update(values)

    return mutate


def _pop_key(key: str) -> Mutator:
    def mutate(payload: dict[str, Any]) -> None:
        payload.pop(key)

    return mutate


def _inject(key: str, value: Any) -> Mutator:
    def mutate(payload: dict[str, Any]) -> None:
        payload.setdefault("unsafe_debug", {})[key] = value

    return mutate


def _contains_forbidden_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if isinstance(key, str) and key in FORBIDDEN_PAYLOAD_KEYS:
                return True
            if _contains_forbidden_key(child):
                return True
    elif isinstance(value, list):
        return any(_contains_forbidden_key(item) for item in value)
    return False


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _artifact_hashes(output_dir: Path) -> dict[str, Any]:
    artifacts = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name == HASH_NAME:
            continue
        rel = path.relative_to(output_dir).as_posix()
        data = path.read_bytes()
        artifacts.append(
            {
                "path": rel,
                "bytes": len(data),
                "sha256": "sha256:" + hashlib.sha256(data).hexdigest(),
            }
        )
    return {
        "schema_version": "1",
        "artifact_type": "ithildin.mission_control_enterprise_status.fixture_hashes",
        "hash_manifest_self_hashed": False,
        "artifacts": artifacts,
    }


def _artifact_hashes_match_files(output_dir: Path, manifest: dict[str, Any]) -> bool:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        return False
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            return False
        rel = artifact.get("path")
        expected_hash = artifact.get("sha256")
        expected_bytes = artifact.get("bytes")
        if not isinstance(rel, str) or not isinstance(expected_hash, str):
            return False
        path = output_dir / rel
        if not path.exists() or not path.is_file():
            return False
        data = path.read_bytes()
        if expected_bytes != len(data):
            return False
        if expected_hash != "sha256:" + hashlib.sha256(data).hexdigest():
            return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())

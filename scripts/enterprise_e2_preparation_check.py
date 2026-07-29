"""Validate the bounded Enterprise E2 production-identity preparation lane."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import enterprise_e2_scale_fixture

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("docs/codex/enterprise-e2-preparation-contract.json")
DOC_REL = Path("docs/codex/enterprise-e2-production-identity-preparation.md")
SCALE_DOC_REL = Path("docs/codex/enterprise-e2-scale-fixture.md")
BASE_COMMIT = "9df7a04cec197fd4953de692793a32e69c107b49"
E1_CANDIDATE = "02e39d57a6d38a14d959bb88a32da79fe34e4e13"
E1_CANDIDATE_TREE = "9850b6cbd40742d67388527de802961ddef306bd"
PREPARATION_BRANCH = "codex/enterprise-e2-production-identity-prep"
PIS004A_BRANCH = "codex/enterprise-e2-pis004a-review-repair"
PIS004A_SOURCE_COMMIT = "e86f5a19e4e067d73141246f78304597e6cc28a0"
PIS004A_SOURCE_TREE = "6dbbcf0bef3320dfdfa4142f2d30b798b01511d0"
PIS_WAIT_ACTION = (
    "await_external_operator_target_and_signed_receipt_inputs_before_separate_"
    "collection_action_authority"
)
NEXT_ACTION = (
    "continue_e1_human_uat_and_existing_pis_external_input_wait_before_separate_e2_entry_decision"
)
WORK_PACKAGE_IDS = tuple(f"E2-ID-00{index}" for index in range(1, 6))
EXPECTED_AUTHORITY = {
    "runtime_behavior_changes_allowed": False,
    "public_api_changes_allowed": False,
    "schema_or_migration_changes_allowed": False,
    "dependency_changes_allowed": False,
    "production_identity_allowed": False,
    "enterprise_rbac_allowed": False,
    "remote_admin_allowed": False,
    "runtime_postgres_allowed": False,
    "external_identity_connection_allowed": False,
    "credential_or_signing_key_custody_allowed": False,
    "new_governed_tool_allowed": False,
    "release_allowed": False,
    "production_promotion_allowed": False,
    "e1_human_uat_complete": False,
    "e2_human_uat_complete": False,
}
EXPECTED_NONCLAIMS = [
    "production identity",
    "enterprise RBAC",
    "remote administration",
    "runtime PostgreSQL",
    "supported scale",
    "performance certification",
    "human UAT completion",
    "enterprise production readiness",
    "Local v1 release acceptance",
]
PROTECTED_E1_HASHES = {
    "docs/codex/enterprise-e1-completion-contract.json": (
        "cfcf463cf294b6db2e8bb70c2e7e5d6f9dad4bb740a5c290947403f8a49e256a"
    ),
    "docs/codex/enterprise-e1-candidate-gate.md": (
        "35e8a4102606ee6a87e2815c14147931b17a2510618b0205c8c484d1391973e0"
    ),
    "docs/codex/enterprise-e1-independent-review.md": (
        "6ec9e9ec18643ba7565a0583267a5684cfa519c08b57a76fc095ded0eab82319"
    ),
    "docs/codex/enterprise-e1-human-uat-packet.md": (
        "c98975a6b21146d2913325625a2d2d805bee0951cf201f440b5f5a97fc42dd14"
    ),
}
ALLOWED_CHANGED_PATHS = {
    "Makefile",
    "README.md",
    "docs/codex/enterprise-e2-preparation-contract.json",
    "docs/codex/enterprise-e2-production-identity-preparation.md",
    "docs/codex/enterprise-e2-scale-fixture.md",
    "docs/codex/review-docs-index.md",
    "scripts/build_docs_site.py",
    "scripts/enterprise_e2_preparation_check.py",
    "scripts/enterprise_e2_scale_fixture.py",
    "scripts/review_docs.py",
    "tests/test_enterprise_e2_preparation.py",
    "tests/test_enterprise_e2_scale_fixture.py",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report(ROOT)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(root: Path) -> dict[str, Any]:
    failures: list[str] = []
    contract = load_contract(root / CONTRACT_REL, failures)
    failures.extend(validate_contract(contract))
    _validate_repository(root, contract, failures)
    scale = contract.get("scale_fixture")
    return {
        "valid": not failures,
        "failures": failures,
        "track_id": contract.get("track_id"),
        "status": contract.get("status"),
        "base_commit": BASE_COMMIT,
        "e1_candidate_commit": E1_CANDIDATE,
        "tool_count": contract.get("tool_count"),
        "work_package_ids": _work_package_ids(contract),
        "scale_counts": scale.get("counts") if isinstance(scale, dict) else None,
        "pis_next_action": PIS_WAIT_ACTION,
        "next_action": contract.get("next_action"),
        "runtime_behavior_changes_allowed": False,
        "production_identity_allowed": False,
        "runtime_postgres_allowed": False,
        "e1_human_uat_complete": False,
    }


def load_contract(path: Path, failures: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_closed_object)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        failures.append(f"E2 preparation contract cannot be loaded: {exc}")
        return {}
    if not isinstance(value, dict):
        failures.append("E2 preparation contract must be an object")
        return {}
    return value


def validate_contract(contract: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    expected_top = {
        "schema_version",
        "track_id",
        "title",
        "status",
        "base",
        "tool_count",
        "standing_authority",
        "identity_reconciliation",
        "scale_fixture",
        "authority",
        "nonclaims",
        "next_action",
    }
    if set(contract) != expected_top:
        failures.append("E2 preparation contract top-level keys are not closed")
    if (
        contract.get("schema_version") != "1"
        or contract.get("track_id") != "E2-PREP"
        or contract.get("status") != "preparation_complete_implementation_not_authorized"
    ):
        failures.append("E2 preparation contract identity is invalid")
    if contract.get("tool_count") != 24:
        failures.append("E2 preparation contract does not preserve 24 tools")
    if contract.get("base") != {
        "e1_handoff_commit": BASE_COMMIT,
        "e1_candidate_commit": E1_CANDIDATE,
        "e1_candidate_tree": E1_CANDIDATE_TREE,
        "e1_next_action": "stop_for_human_uat",
        "e1_human_uat_complete": False,
    }:
        failures.append("E2 preparation base does not preserve the exact E1 handoff")
    if contract.get("standing_authority") != {
        "identity_storage_architecture": ("docs/codex/production-identity-storage-architecture.md"),
        "identity_threat_model": (
            "docs/codex/production-identity-storage-pis-001-threat-model-and-dependency-decision.md"
        ),
        "current_pis_authority": (
            "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
            "environment-evidence-collection-authority.json"
        ),
        "pis_next_action": PIS_WAIT_ACTION,
        "external_target_selection_proposal_permission": True,
        "external_environment_receipt_collection_proposal_permission": True,
        "operational_collection_action_effective": False,
    }:
        failures.append("E2 preparation does not preserve current PIS authority")
    identity = contract.get("identity_reconciliation")
    if not isinstance(identity, dict) or set(identity) != {
        "standing_architecture_reused",
        "competing_identity_architecture_created",
        "future_entry_gate",
        "provider_selected",
        "dependency_selected_or_added",
        "live_identity_endpoint_selected",
        "work_packages",
    }:
        failures.append("E2 identity reconciliation keys are not closed")
        identity = {}
    if (
        identity.get("standing_architecture_reused") is not True
        or identity.get("competing_identity_architecture_created") is not False
        or identity.get("future_entry_gate") != "PIS-004"
        or any(
            identity.get(key) is not False
            for key in (
                "provider_selected",
                "dependency_selected_or_added",
                "live_identity_endpoint_selected",
            )
        )
    ):
        failures.append("E2 identity reconciliation expands authority or duplicates architecture")
    packages = identity.get("work_packages")
    package_list: list[dict[str, Any]] = (
        [item for item in packages if isinstance(item, dict)] if isinstance(packages, list) else []
    )
    package_ids = [item.get("id") for item in package_list]
    if package_ids != list(WORK_PACKAGE_IDS):
        failures.append("E2 identity work packages are not exact and ordered")
    elif any(
        set(item)
        != {
            "id",
            "title",
            "status",
            "implementation_gate_required",
        }
        or item.get("status") != "proposal_only"
        or item.get("implementation_gate_required") is not True
        for item in package_list
    ):
        failures.append("E2 identity work packages are not proposal-only gated records")
    scale = contract.get("scale_fixture")
    expected_fixture_digest = hashlib.sha256(
        enterprise_e2_scale_fixture.canonical_bytes(enterprise_e2_scale_fixture.build_fixture())
    ).hexdigest()
    if not isinstance(scale, dict) or scale != {
        "schema_version": enterprise_e2_scale_fixture.SCHEMA_VERSION,
        "fixture_id": enterprise_e2_scale_fixture.FIXTURE_ID,
        "canonical_sha256": expected_fixture_digest,
        "single_organization_only": True,
        "counts": enterprise_e2_scale_fixture.EXPECTED_COUNTS,
        "runtime_import_allowed": False,
        "supported_scale_claim_allowed": False,
        "performance_certification_allowed": False,
    }:
        failures.append("E2 scale fixture contract is not exact and bounded")
    if contract.get("authority") != EXPECTED_AUTHORITY:
        failures.append("E2 preparation grants forbidden implementation authority")
    if contract.get("nonclaims") != EXPECTED_NONCLAIMS:
        failures.append("E2 preparation nonclaims are not exact and ordered")
    if contract.get("next_action") != NEXT_ACTION:
        failures.append("E2 preparation next action is not exact")
    return failures


def _validate_repository(
    root: Path,
    contract: dict[str, Any],
    failures: list[str],
) -> None:
    if not _git_ok(root, "cat-file", "-e", f"{BASE_COMMIT}^{{commit}}"):
        failures.append("E2 base commit is unavailable")
    elif not _git_ok(root, "merge-base", "--is-ancestor", BASE_COMMIT, "HEAD"):
        failures.append("E2 base commit is not an ancestor of HEAD")
    current_branch = _git_one(root, "branch", "--show-current")
    if current_branch not in {PREPARATION_BRANCH, PIS004A_BRANCH}:
        failures.append("E2 preparation is not on its isolated branch")
    elif current_branch == PIS004A_BRANCH and (
        not _git_ok(root, "merge-base", "--is-ancestor", PIS004A_SOURCE_COMMIT, "HEAD")
        or _git_one(root, "rev-parse", f"{PIS004A_SOURCE_COMMIT}^{{tree}}") != PIS004A_SOURCE_TREE
    ):
        failures.append("E2 preparation descendant does not preserve its exact source")

    for relative, expected_hash in PROTECTED_E1_HASHES.items():
        path = root / relative
        try:
            observed_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            observed_hash = ""
        if observed_hash != expected_hash:
            failures.append(f"E2 preparation changed protected E1 evidence: {relative}")

    e1 = _load_json(root / "docs/codex/enterprise-e1-completion-contract.json", failures)
    qualification = e1.get("qualification") if isinstance(e1, dict) else None
    if not isinstance(qualification, dict) or qualification != {
        "candidate_commit": E1_CANDIDATE,
        "candidate_gate_complete": True,
        "independent_review_complete": True,
        "human_uat_packet_ready": True,
        "human_uat_complete": False,
    }:
        failures.append("E2 preparation does not preserve E1 qualification state")
    if e1.get("next_action") != "stop_for_human_uat":
        failures.append("E2 preparation changed the E1 human-UAT stop line")

    authority_path = (
        root / "docs/codex/production-identity-storage-pis-003-sd-pg-001-"
        "environment-evidence-collection-authority.json"
    )
    pis = _load_json(authority_path, failures)
    pis_authority = pis.get("authority") if isinstance(pis, dict) else None
    if (
        pis.get("next_required_action") != PIS_WAIT_ACTION
        or not isinstance(pis_authority, dict)
        or pis_authority.get("external_target_selection_allowed") is not True
        or pis_authority.get("external_environment_receipt_collection_allowed") is not True
        or pis_authority.get("operational_collection_action_effective") is not False
        or pis_authority.get("production_identity_allowed") is not False
        or pis_authority.get("runtime_postgres_allowed") is not False
        or pis_authority.get("database_connections_allowed") is not False
    ):
        failures.append("E2 preparation does not preserve the current PIS wait and ceiling")

    lock = _load_json(root / "tool-manifests.lock.json", failures)
    manifests = lock.get("manifests") if isinstance(lock, dict) else None
    if not isinstance(manifests, list) or len(manifests) != 24:
        failures.append("E2 preparation does not preserve the 24-tool manifest lock")

    doc = _read(root / DOC_REL, failures)
    scale_doc = _read(root / SCALE_DOC_REL, failures)
    readme = _read(root / "README.md", failures)
    makefile = _read(root / "Makefile", failures)
    review_docs = _read(root / "scripts/review_docs.py", failures)
    docs_site = _read(root / "scripts/build_docs_site.py", failures)
    review_index = _read(root / "docs/codex/review-docs-index.md", failures)
    for phrase in (
        "Status: preparation complete; implementation not authorized.",
        "future identity entry gate remains `PIS-004`",
        PIS_WAIT_ACTION,
        NEXT_ACTION,
        "governed tool count remains exactly `24`",
    ):
        if phrase not in doc:
            failures.append(f"E2 preparation document is missing phrase: {phrase}")
    for phrase in (
        "deterministic test-only fixture generator",
        "not a supported-scale or performance claim",
        "make enterprise-e2-scale-fixture-check",
    ):
        if phrase not in scale_doc:
            failures.append(f"E2 scale fixture document is missing phrase: {phrase}")
    doc_name = DOC_REL.as_posix()
    for source_name, source, expected_reference in (
        ("README", readme, doc_name),
        ("review docs", review_docs, doc_name),
        ("docs site", docs_site, doc_name),
        ("review index", review_index, DOC_REL.name),
    ):
        if expected_reference not in source:
            failures.append(f"E2 preparation document is missing from {source_name}")
    for target in (
        "enterprise-e2-preparation-check:",
        "enterprise-e2-scale-fixture-check:",
    ):
        if target not in makefile:
            failures.append(f"Makefile is missing E2 target: {target}")

    if current_branch == PREPARATION_BRANCH:
        unexpected = sorted(_changed_paths(root) - ALLOWED_CHANGED_PATHS)
        if unexpected:
            failures.append(
                "E2 preparation changed paths outside its lane: " + ", ".join(unexpected)
            )
    elif (
        current_branch == PIS004A_BRANCH
        and not (
            root
            / "docs/codex/"
            "production-identity-storage-pis-004a-entry-and-implementation-contract.json"
        ).is_file()
    ):
        failures.append("E2 preparation descendant is missing its separate entry decision")
    if contract.get("authority") != EXPECTED_AUTHORITY:
        failures.append("E2 repository validation observed an expanded authority contract")


def _work_package_ids(contract: dict[str, Any]) -> list[object]:
    identity = contract.get("identity_reconciliation")
    packages = identity.get("work_packages") if isinstance(identity, dict) else None
    if not isinstance(packages, list):
        return []
    return [item.get("id") for item in packages if isinstance(item, dict)]


def _changed_paths(root: Path) -> set[str]:
    paths: set[str] = set()
    for args in (
        ("diff", "--name-only", f"{BASE_COMMIT}..HEAD"),
        ("diff", "--name-only"),
        ("diff", "--cached", "--name-only"),
        ("ls-files", "--others", "--exclude-standard"),
    ):
        output = _git_output(root, *args)
        paths.update(line for line in output.splitlines() if line)
    return paths


def _load_json(path: Path, failures: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_closed_object)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        failures.append(f"required JSON cannot be loaded: {path.name}: {exc}")
        return {}
    if not isinstance(value, dict):
        failures.append(f"required JSON is not an object: {path.name}")
        return {}
    return value


def _read(path: Path, failures: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        failures.append(f"required text cannot be loaded: {path.name}: {exc}")
        return ""


def _closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _git_ok(root: Path, *args: str) -> bool:
    return (
        subprocess.run(
            ["git", *args],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        ).returncode
        == 0
    )


def _git_one(root: Path, *args: str) -> str:
    return _git_output(root, *args).strip()


def _git_output(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout if result.returncode == 0 else ""


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin Enterprise E2 preparation check",
        f"valid: {str(report['valid']).lower()}",
        f"track_id: {report['track_id']}",
        f"status: {report['status']}",
        f"base_commit: {report['base_commit']}",
        f"e1_candidate_commit: {report['e1_candidate_commit']}",
        f"tool_count: {report['tool_count']}",
        f"work_package_ids: {', '.join(str(value) for value in report['work_package_ids'])}",
        f"scale_counts: {json.dumps(report['scale_counts'], sort_keys=True)}",
        f"pis_next_action: {report['pis_next_action']}",
        f"next_action: {report['next_action']}",
        "runtime_behavior_changes_allowed: false",
        "production_identity_allowed: false",
        "runtime_postgres_allowed: false",
        "e1_human_uat_complete: false",
    ]
    lines.extend(f"failure: {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

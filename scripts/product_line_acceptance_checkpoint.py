"""Validate the scoped Ithildin product-line acceptance checkpoint."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECORD_REL = Path("docs/codex/product-line-acceptance-checkpoint.json")
DOC_REL = Path("docs/codex/product-line-acceptance-checkpoint.md")
LOCAL_DISPOSITION_REL = Path("docs/codex/local-v1-release-disposition.json")
E1_CONTRACT_REL = Path("docs/codex/enterprise-e1-completion-contract.json")
LOCAL_CANDIDATE = "ab4162d8f4b6d3f45a68f33316f4b765a45765db"
LOCAL_TREE = "25be9f049ca3ff3ccf6721100944e36baa0c3b05"
E1_CANDIDATE = "02e39d57a6d38a14d959bb88a32da79fe34e4e13"
E1_TREE = "9850b6cbd40742d67388527de802961ddef306bd"
PIS_005A_CANDIDATE = "fce0a3668db5150cf0aa75de1fd914b296a2e099"
PIS_WAIT = (
    "await_external_operator_target_and_signed_receipt_inputs_before_separate_"
    "collection_action_authority"
)

EXPECTED_RECORD: dict[str, Any] = {
    "schema_version": "1",
    "record_type": "ithildin_product_line_acceptance_checkpoint",
    "record_status": "accepted_for_scoped_development_continuation",
    "recorded_on": "2026-07-30",
    "source_authority": {
        "kind": "human_product_authority",
        "accepted_direction": (
            "personal_technical_preview_and_bounded_enterprise_e1_single_site_pilot"
        ),
        "acceptance_effect": "scoped_development_continuation_only",
    },
    "product_lines": {
        "personal": {
            "candidate_commit": LOCAL_CANDIDATE,
            "candidate_tree": LOCAL_TREE,
            "acceptance_scope": "personal_technical_preview",
            "development_continuation_accepted": True,
            "human_uat": {
                "prescribed": True,
                "executed": False,
                "passed": False,
                "waived_only_for": (
                    "continued_product_development_and_scoped_personal_"
                    "technical_preview_acceptance"
                ),
            },
        },
        "enterprise_e1": {
            "candidate_commit": E1_CANDIDATE,
            "candidate_tree": E1_TREE,
            "acceptance_scope": "bounded_enterprise_e1_single_site_pilot",
            "development_continuation_accepted": True,
            "human_uat": {
                "prescribed": True,
                "executed": False,
                "passed": False,
                "waived_only_for": (
                    "continued_product_development_and_bounded_enterprise_e1_"
                    "single_site_pilot_acceptance"
                ),
            },
        },
    },
    "preserved_boundaries": {
        "governed_tool_count": 24,
        "runtime_authority": "Gateway",
        "pis_external_input_wait": {
            "next_action": PIS_WAIT,
            "external_inputs_present": False,
            "collection_action_authority": False,
        },
        "frozen_candidates_modified": False,
        "frozen_candidates_reinterpreted": False,
        "pis_005a_rejected_candidate": {
            "commit": PIS_005A_CANDIDATE,
            "tree": "331adb70f2c2c24def540c3576fc6876e33c478c",
            "status": "candidate_independent_review_pending",
            "review_findings": {
                "critical": 0,
                "high": 1,
                "medium": 1,
                "low": 3,
            },
            "modified": False,
            "reinterpreted": False,
        },
    },
    "authority_nonclaims": {
        "human_uat_passed": False,
        "local_v1_release_accepted": False,
        "release_authority": False,
        "production_readiness": False,
        "production_promotion": False,
        "public_security_product_readiness": False,
        "external_system_authority": False,
        "enterprise_production_ready": False,
    },
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


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    record = _load_json(repo_root / RECORD_REL, failures)
    local_disposition = _load_json(repo_root / LOCAL_DISPOSITION_REL, failures)
    e1_contract = _load_json(repo_root / E1_CONTRACT_REL, failures)
    failures.extend(validate_record(record))
    failures.extend(validate_source_contracts(local_disposition, e1_contract))
    git_report = validate_git_bindings(repo_root)
    failures.extend(git_report["failures"])
    failures.extend(validate_navigation(repo_root))
    product_lines = record.get("product_lines", {}) if isinstance(record, dict) else {}
    boundaries = (
        record.get("preserved_boundaries", {}) if isinstance(record, dict) else {}
    )
    return {
        "valid": not failures,
        "record_status": record.get("record_status") if isinstance(record, dict) else None,
        "personal_candidate": _nested(product_lines, "personal", "candidate_commit"),
        "personal_tree": _nested(product_lines, "personal", "candidate_tree"),
        "enterprise_e1_candidate": _nested(
            product_lines, "enterprise_e1", "candidate_commit"
        ),
        "enterprise_e1_tree": _nested(
            product_lines, "enterprise_e1", "candidate_tree"
        ),
        "enterprise_e1_descends_from_local": git_report["e1_descends_from_local"],
        "governed_tool_count": boundaries.get("governed_tool_count"),
        "human_uat_executed": False,
        "failures": failures,
    }


def validate_record(record: dict[str, Any]) -> list[str]:
    if record != EXPECTED_RECORD:
        return ["product-line acceptance checkpoint keys or values are not exact"]
    return []


def validate_source_contracts(
    local_disposition: dict[str, Any],
    e1_contract: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    if _nested(local_disposition, "candidate", "frozen_commit") != LOCAL_CANDIDATE:
        failures.append("Local-v1 frozen candidate does not match the checkpoint")
    if _nested(local_disposition, "human_uat", "completed") is not False:
        failures.append("Local-v1 human UAT must remain incomplete")
    if _nested(local_disposition, "human_acceptance", "accepted") is not False:
        failures.append("Local-v1 release acceptance must remain false")
    local_authority = local_disposition.get("authority")
    if not isinstance(local_authority, dict) or any(
        local_authority.get(key) is not False
        for key in ("release_allowed", "promotion_allowed", "production_allowed")
    ):
        failures.append("Local-v1 release, promotion, and production authority must remain false")

    if _nested(e1_contract, "qualification", "candidate_commit") != E1_CANDIDATE:
        failures.append("E1 frozen candidate does not match the checkpoint")
    if _nested(e1_contract, "qualification", "human_uat_complete") is not False:
        failures.append("E1 human_uat_complete must remain false")
    e1_authority = e1_contract.get("authority")
    if not isinstance(e1_authority, dict) or any(
        e1_authority.get(key) is not False
        for key in (
            "enterprise_production_ready",
            "local_v1_release_accepted",
            "production_promotion_allowed",
            "public_security_product_claims_allowed",
        )
    ):
        failures.append(
            "E1 release, promotion, production, and public-claim fields must remain false"
        )
    if e1_contract.get("tool_count") != 24:
        failures.append("E1 governed tool count must remain exactly 24")
    if e1_contract.get("pis_wait") != {
        "next_action": PIS_WAIT,
        "external_inputs_present": False,
        "collection_action_authority": False,
    }:
        failures.append("E1 PIS external-input wait is not exact")
    return failures


def validate_git_bindings(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    local_tree = _git_one(repo_root, "rev-parse", f"{LOCAL_CANDIDATE}^{{tree}}")
    e1_tree = _git_one(repo_root, "rev-parse", f"{E1_CANDIDATE}^{{tree}}")
    if local_tree != LOCAL_TREE:
        failures.append("Local-v1 candidate does not resolve to the recorded tree")
    if e1_tree != E1_TREE:
        failures.append("E1 candidate does not resolve to the recorded tree")
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", LOCAL_CANDIDATE, E1_CANDIDATE],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    e1_descends_from_local = ancestry.returncode == 0
    if not e1_descends_from_local:
        failures.append("E1 candidate does not descend from the frozen Local-v1 candidate")
    return {
        "local_tree": local_tree,
        "e1_tree": e1_tree,
        "e1_descends_from_local": e1_descends_from_local,
        "failures": failures,
    }


def validate_navigation(repo_root: Path) -> list[str]:
    failures: list[str] = []
    expected_paths = (DOC_REL.as_posix(), RECORD_REL.as_posix())
    files = {
        "README.md": _read_text(repo_root / "README.md", failures),
        "scripts/build_docs_site.py": _read_text(
            repo_root / "scripts/build_docs_site.py", failures
        ),
        "scripts/review_docs.py": _read_text(repo_root / "scripts/review_docs.py", failures),
        "docs/codex/review-docs-index.md": _read_text(
            repo_root / "docs/codex/review-docs-index.md", failures
        ),
    }
    for path in expected_paths:
        for source, text in files.items():
            if path not in text and Path(path).name not in text:
                failures.append(f"{source} does not route {path}")
    makefile = _read_text(repo_root / "Makefile", failures)
    if "product-line-acceptance-checkpoint:" not in makefile:
        failures.append("Makefile does not define product-line-acceptance-checkpoint")
    doc = _read_text(repo_root / DOC_REL, failures)
    for required in (
        LOCAL_CANDIDATE,
        LOCAL_TREE,
        E1_CANDIDATE,
        E1_TREE,
        PIS_005A_CANDIDATE,
        PIS_WAIT,
        "Prescribed human UAT was not executed.",
        "does not claim `human_uat_passed`",
    ):
        if required not in doc:
            failures.append(f"checkpoint prose is missing required text: {required}")
    return failures


def _load_json(path: Path, failures: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        failures.append(f"cannot parse {path}: {exc}")
        return {}
    if not isinstance(payload, dict):
        failures.append(f"{path} must contain a JSON object")
        return {}
    return payload


def _read_text(path: Path, failures: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        failures.append(f"cannot read {path}: {exc}")
        return ""


def _git_one(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _nested(payload: object, *keys: str) -> object:
    current = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin product-line acceptance checkpoint",
        f"valid: {str(report['valid']).lower()}",
        f"record_status: {report['record_status']}",
        f"personal_candidate: {report['personal_candidate']}",
        f"personal_tree: {report['personal_tree']}",
        f"enterprise_e1_candidate: {report['enterprise_e1_candidate']}",
        f"enterprise_e1_tree: {report['enterprise_e1_tree']}",
        (
            "enterprise_e1_descends_from_local: "
            f"{str(report['enterprise_e1_descends_from_local']).lower()}"
        ),
        f"governed_tool_count: {report['governed_tool_count']}",
        f"human_uat_executed: {str(report['human_uat_executed']).lower()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

"""Validate the static synthetic compliance-mapping template corpus."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import sys
import unicodedata
from collections.abc import Mapping
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/compliance-mapping-template-compatibility-fixtures.md"
DOC_TITLE = "Compliance Mapping Template Compatibility Fixtures"
ARCHITECTURE_REL = "docs/codex/compliance-mapping-architecture.md"
FIXTURE_DIR_REL = "tests/fixtures/compliance_mapping"
CORPUS_REL = f"{FIXTURE_DIR_REL}/compatibility-corpus.json"
BASE_TEMPLATE_REL = f"{FIXTURE_DIR_REL}/valid-template-v1.json"
CORPUS_SHA256 = "46a8ff8292fa0ba7cabacc53675db57da1da3d616cb74e9606b418ccfadb20ca"
BASE_TEMPLATE_SHA256 = (
    "8ad83afb9626fb99c93a69e32b1d2542a334b42cc0c2c73728255b80cef20c1a"
)

TEMPLATE_KEYS = {
    "schema",
    "template_id",
    "framework",
    "operator_responsibility",
    "legal_review",
    "rows",
    "authority",
}
FRAMEWORK_KEYS = {"family", "version", "status"}
OPERATOR_RESPONSIBILITY_KEYS = {
    "operator_must_validate_applicability",
    "operator_must_review_legal_obligations",
    "operator_decides_evidence_sufficiency",
}
LEGAL_REVIEW_KEYS = {"required_before_external_claim", "legal_advice_provided"}
ROW_KEYS = {
    "mapping_id",
    "control_reference",
    "control_objective",
    "evidence_source",
    "safe_evidence_fields",
    "operator_input",
    "evidence_supports",
    "evidence_does_not_prove",
    "freshness",
    "review_cadence",
    "applicability",
    "accepted_risk_refs",
    "verification",
    "confidence",
    "review_console_expectation",
}
APPLICABILITY_KEYS = {"status", "reason_code"}
VERIFICATION_KEYS = {"command", "packet_pointer"}

AUTHORITY_FLAGS = {
    "automated_certification_allowed": False,
    "compliance_claims_allowed": False,
    "compliance_mapping_runtime_allowed": False,
    "custody_grade_audit_allowed": False,
    "legal_advice_allowed": False,
    "new_power_classes_allowed": False,
    "production_identity_allowed": False,
    "release_allowed": False,
    "runtime_changes_allowed": False,
    "uat_allowed": False,
}

CONTROL_OBJECTIVES = {
    "least_privilege",
    "approval_required_writes",
    "restricted_network_destinations",
    "sensitive_resource_labeling",
    "evidence_export",
    "denied_destructive_actions",
    "incident_reconstruction",
}
EVIDENCE_FIELDS = {
    "policy_decision_evidence": {"decision", "policy_id", "reason_code", "tool_id"},
    "approval_lifecycle_evidence": {"approval_id", "state", "tool_id"},
    "denied_action_evidence": {"reason_code", "risk_class", "tool_id"},
    "review_packet_hashes": {"artifact_id", "sha256"},
    "none": set(),
}
EVIDENCE_SUPPORT_BY_SOURCE = {
    "policy_decision_evidence": "mediated_policy_decision_recorded",
    "approval_lifecycle_evidence": "mediated_approval_lifecycle_recorded",
    "denied_action_evidence": "mediated_denial_recorded",
    "review_packet_hashes": "review_packet_digest_recorded",
    "none": "no_supporting_statement",
}
OPERATOR_INPUTS = {"confirm_scope_and_evidence_sufficiency", "none"}
EVIDENCE_SUPPORT_STATEMENTS = {
    "mediated_policy_decision_recorded",
    "mediated_approval_lifecycle_recorded",
    "mediated_denial_recorded",
    "review_packet_digest_recorded",
    "no_supporting_statement",
}
REQUIRED_LIMITATIONS = {
    "activity_outside_ithildin",
    "human_identity",
    "organizational_control_conformance",
}
APPLICABILITY_REASON_CODES = {
    "supported": {"evidence_source_available"},
    "unsupported": {"evidence_source_not_available"},
    "not_applicable": {"objective_not_selected"},
}
CONFIDENCE_BY_STATUS = {
    "supported": "design_example_only",
    "unsupported": "unsupported",
    "not_applicable": "not_applicable",
}
CONSOLE_BY_STATUS = {
    "supported": "show_evidence_and_gaps",
    "unsupported": "show_unsupported_reason",
    "not_applicable": "show_not_applicable_reason",
}
VERIFICATION_REFERENCES = {
    (
        "make control-mapping-design-check",
        "docs/codex/control-mapping-design.md",
    ),
    (
        "make incident-reconstruction-check",
        "docs/codex/incident-reconstruction-guide.md",
    ),
}
ACCEPTED_RISK_REFS = {f"AR-{number:03d}" for number in range(1, 11)}

EXPECTED_CASES = [
    {
        "id": "CMT-COMP-001",
        "label": "valid_v1",
        "mutation": "none",
        "expected_accept": True,
        "expected_reasons": [],
    },
    {
        "id": "CMT-COMP-002",
        "label": "valid_supported_only",
        "mutation": "supported_only",
        "expected_accept": True,
        "expected_reasons": [],
    },
    {
        "id": "CMT-COMP-003",
        "label": "valid_unsupported_and_not_applicable",
        "mutation": "unsupported_and_not_applicable",
        "expected_accept": True,
        "expected_reasons": [],
    },
    {
        "id": "CMT-COMP-004",
        "label": "duplicate_json_member",
        "mutation": "duplicate_json_member",
        "expected_accept": False,
        "expected_reasons": ["duplicate_json_member"],
    },
    {
        "id": "CMT-COMP-005",
        "label": "unknown_template_field",
        "mutation": "unknown_template_field",
        "expected_accept": False,
        "expected_reasons": ["unknown_template_field"],
    },
    {
        "id": "CMT-COMP-006",
        "label": "unsupported_template_schema",
        "mutation": "unsupported_template_schema",
        "expected_accept": False,
        "expected_reasons": ["unsupported_template_schema"],
    },
    {
        "id": "CMT-COMP-007",
        "label": "real_framework_not_allowed",
        "mutation": "real_framework_not_allowed",
        "expected_accept": False,
        "expected_reasons": ["real_framework_not_allowed"],
    },
    {
        "id": "CMT-COMP-008",
        "label": "legal_review_boundary_weakened",
        "mutation": "legal_review_boundary_weakened",
        "expected_accept": False,
        "expected_reasons": ["legal_review_boundary_weakened"],
    },
    {
        "id": "CMT-COMP-009",
        "label": "authority_expansion",
        "mutation": "authority_expansion",
        "expected_accept": False,
        "expected_reasons": ["authority_expansion"],
    },
    {
        "id": "CMT-COMP-010",
        "label": "forbidden_evidence_field",
        "mutation": "forbidden_evidence_field",
        "expected_accept": False,
        "expected_reasons": ["forbidden_evidence_field"],
    },
    {
        "id": "CMT-COMP-011",
        "label": "unknown_evidence_field",
        "mutation": "unknown_evidence_field",
        "expected_accept": False,
        "expected_reasons": ["unknown_evidence_field"],
    },
    {
        "id": "CMT-COMP-012",
        "label": "missing_evidence_limitation",
        "mutation": "missing_evidence_limitation",
        "expected_accept": False,
        "expected_reasons": ["missing_evidence_limitation"],
    },
    {
        "id": "CMT-COMP-013",
        "label": "applicability_confidence_mismatch",
        "mutation": "applicability_confidence_mismatch",
        "expected_accept": False,
        "expected_reasons": ["applicability_confidence_mismatch"],
    },
    {
        "id": "CMT-COMP-014",
        "label": "unsafe_verification_reference",
        "mutation": "unsafe_verification_reference",
        "expected_accept": False,
        "expected_reasons": ["unsafe_verification_reference"],
    },
    {
        "id": "CMT-COMP-015",
        "label": "invalid_accepted_risk_reference",
        "mutation": "invalid_accepted_risk_reference",
        "expected_accept": False,
        "expected_reasons": ["invalid_accepted_risk_reference"],
    },
    {
        "id": "CMT-COMP-016",
        "label": "duplicate_mapping_id",
        "mutation": "duplicate_mapping_id",
        "expected_accept": False,
        "expected_reasons": ["duplicate_mapping_id"],
    },
    {
        "id": "CMT-COMP-017",
        "label": "duplicate_control_reference",
        "mutation": "duplicate_control_reference",
        "expected_accept": False,
        "expected_reasons": ["duplicate_control_reference"],
    },
    {
        "id": "CMT-COMP-018",
        "label": "prohibited_claim_text",
        "mutation": "prohibited_claim_text",
        "expected_accept": False,
        "expected_reasons": [
            "prohibited_claim_text",
            "unsupported_evidence_support_statement",
        ],
    },
    {
        "id": "CMT-COMP-019",
        "label": "overflowing_json_number",
        "mutation": "overflowing_json_number",
        "expected_accept": False,
        "expected_reasons": ["non_finite_number"],
    },
    {
        "id": "CMT-COMP-020",
        "label": "invalid_unicode",
        "mutation": "invalid_unicode",
        "expected_accept": False,
        "expected_reasons": ["invalid_unicode"],
    },
    {
        "id": "CMT-COMP-021",
        "label": "unknown_row_field",
        "mutation": "unknown_row_field",
        "expected_accept": False,
        "expected_reasons": ["unknown_row_field"],
    },
    {
        "id": "CMT-COMP-022",
        "label": "arbitrary_limitation_value",
        "mutation": "arbitrary_limitation_value",
        "expected_accept": False,
        "expected_reasons": ["invalid_evidence_limitation"],
    },
    {
        "id": "CMT-COMP-023",
        "label": "evidence_source_support_mismatch",
        "mutation": "evidence_source_support_mismatch",
        "expected_accept": False,
        "expected_reasons": ["evidence_source_support_mismatch"],
    },
    {
        "id": "CMT-COMP-024",
        "label": "verification_reference_mismatch",
        "mutation": "verification_reference_mismatch",
        "expected_accept": False,
        "expected_reasons": ["unsafe_verification_reference"],
    },
]

REQUIRED_DOC_PHRASES = [
    "Status: static planning-only compatibility corpus for `CMT-001` and `ERG-009`.",
    "Current governed tool count: `24`.",
    "make compliance-mapping-template-compatibility-check",
    "valid-template-v1.json",
    "compatibility-corpus.json",
    "materialized in memory",
    "never written",
    "synthetic, non-regulatory",
    "CMT-COMP-001",
    "CMT-COMP-024",
    "reports only the safe reason label",
    "does not close `ERG-009`",
    "does not authorize new power classes",
]

_MAPPING_ID = re.compile(r"CM-SYN-[0-9]{3}")
_CONTROL_REFERENCE = re.compile(r"SYNTHETIC-CONTROL-[0-9]{3}")
_TEMPLATE_ID = re.compile(r"cmt_[a-z0-9_]{3,63}")
_PROHIBITED_CLAIM = re.compile(
    r"\b(?:hipaa|glba|sox|gdpr|nist|cis|soc\s*2|compliant|certified|certification)\b",
    re.IGNORECASE,
)
_SENSITIVE_KEY_PARTS = {
    "token",
    "cookie",
    "secret",
    "password",
    "passwd",
    "credential",
    "prompt",
}


class DuplicateJsonMember(ValueError):
    """Raised when a fixture contains an ambiguous JSON object."""


class NonFiniteJsonNumber(ValueError):
    """Raised when a fixture contains NaN or an infinity."""


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
    doc = _read(repo_root / DOC_REL)
    architecture = _read(repo_root / ARCHITECTURE_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    normalized_doc = " ".join(doc.split())
    for phrase in REQUIRED_DOC_PHRASES:
        if phrase not in normalized_doc:
            failures.append(f"template compatibility doc is missing phrase: {phrase}")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("template compatibility doc is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("template compatibility doc is missing from docs-site inputs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing template compatibility doc")
    if DOC_REL not in readme:
        failures.append("README is missing template compatibility doc")
    if "make compliance-mapping-template-compatibility-check" not in readme:
        failures.append("README is missing template compatibility command")
    if "compliance-mapping-template-compatibility-check:" not in makefile:
        failures.append("Make target is missing: compliance-mapping-template-compatibility-check")
    if (
        "compliance-mapping-template-compatibility-check" not in release_check_body
        and "release-check: compliance-mapping-template-compatibility-check" not in makefile
    ):
        failures.append("template compatibility check is missing from release-check")
    if "compliance-mapping-template-compatibility-check" not in release_guardrails:
        failures.append("release guardrails do not require template compatibility check")
    if Path(DOC_REL).name not in architecture or "CMT-001" not in architecture:
        failures.append("compliance architecture is missing template compatibility pointer")

    fixture_dir = repo_root / FIXTURE_DIR_REL
    corpus_path = repo_root / CORPUS_REL
    base_path = repo_root / BASE_TEMPLATE_REL
    for path, label in [
        (fixture_dir, "fixture directory"),
        (corpus_path, "corpus"),
        (base_path, "base template"),
    ]:
        if not path.exists():
            failures.append(f"{label} is missing")
        elif path.is_symlink():
            failures.append(f"{label} must not be a symlink")
    if fixture_dir.is_dir():
        actual_files = sorted(
            path.relative_to(repo_root).as_posix()
            for path in fixture_dir.iterdir()
            if path.is_file()
        )
        if actual_files != sorted([CORPUS_REL, BASE_TEMPLATE_REL]):
            failures.append("template fixture file inventory drifted")

    corpus = _load_json_object(corpus_path, failures, "template compatibility corpus")
    corpus_sha256 = _file_sha256(corpus_path)
    base_template_sha256 = _file_sha256(base_path)
    if corpus_sha256 != CORPUS_SHA256:
        failures.append("template compatibility corpus exact-byte digest drifted")
    if base_template_sha256 != BASE_TEMPLATE_SHA256:
        failures.append("canonical template exact-byte digest drifted")
    if set(corpus) != {
        "schema_version",
        "corpus_type",
        "status",
        "tool_count",
        "base_template",
        "cases",
    }:
        failures.append("template compatibility corpus top-level schema drifted")
    if corpus.get("schema_version") != "1":
        failures.append("template compatibility corpus schema version drifted")
    if (
        corpus.get("corpus_type")
        != "ithildin.compliance_mapping_template.compatibility_fixtures"
    ):
        failures.append("template compatibility corpus type drifted")
    if corpus.get("status") != "static_planning_only":
        failures.append("template compatibility corpus status drifted")
    if corpus.get("tool_count") != 24:
        failures.append("template compatibility corpus tool count drifted")
    if corpus.get("base_template") != BASE_TEMPLATE_REL:
        failures.append("template compatibility base path drifted")
    if corpus.get("cases") != EXPECTED_CASES:
        failures.append("template compatibility case inventory or expectations drifted")

    tool_count = _tool_count(repo_root, failures)
    base_raw = _read(base_path)
    try:
        base_document = _parse_json_object(base_raw)
    except (json.JSONDecodeError, DuplicateJsonMember, NonFiniteJsonNumber, ValueError):
        base_document = {}
        failures.append("canonical template is invalid JSON")
    base_snapshot = _dump_json(base_document)

    case_results: list[dict[str, Any]] = []
    for case in EXPECTED_CASES:
        try:
            materialized = _materialize_case(
                base_raw,
                base_document,
                str(case["mutation"]),
            )
            reasons = validate_template_text(materialized)
        except (KeyError, TypeError, ValueError) as exc:
            reasons = ["fixture_materialization_failed"]
            failures.append(
                f"template case {case['id']} materialization failed: {type(exc).__name__}"
            )
        accepted = not reasons
        if (
            accepted is not case["expected_accept"]
            or reasons != case["expected_reasons"]
        ):
            failures.append(
                f"template case {case['id']} expected {case['expected_reasons']!r} "
                f"but observed {reasons!r}"
            )
        case_results.append(
            {"id": case["id"], "accepted": accepted, "reasons": reasons}
        )
    if _dump_json(base_document) != base_snapshot:
        failures.append("case materialization mutated the canonical template")

    if any(value is not False for value in AUTHORITY_FLAGS.values()):
        failures.append("template checker authority map must remain fail-closed")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "fixture_doc": DOC_REL,
        "corpus": CORPUS_REL,
        "corpus_sha256": corpus_sha256,
        "base_template": BASE_TEMPLATE_REL,
        "base_template_sha256": base_template_sha256,
        "case_count": len(EXPECTED_CASES),
        "accepted_case_count": sum(result["accepted"] for result in case_results),
        "rejected_case_count": sum(not result["accepted"] for result in case_results),
        "case_results": case_results,
        "safe_reason_labels_only": True,
        "tool_count": tool_count,
        **AUTHORITY_FLAGS,
    }


def render_report(report: Mapping[str, Any]) -> str:
    lines = [
        "Ithildin compliance mapping template compatibility check",
        f"valid: {str(report['valid']).lower()}",
        f"fixture_doc: {report['fixture_doc']}",
        f"corpus: {report['corpus']}",
        f"corpus_sha256: {report['corpus_sha256']}",
        f"base_template: {report['base_template']}",
        f"base_template_sha256: {report['base_template_sha256']}",
        f"case_count: {report['case_count']}",
        f"accepted_case_count: {report['accepted_case_count']}",
        f"rejected_case_count: {report['rejected_case_count']}",
        f"safe_reason_labels_only: {str(report['safe_reason_labels_only']).lower()}",
        f"tool_count: {report['tool_count']}",
    ]
    lines.extend(
        f"{key}: {str(report[key]).lower()}" for key in AUTHORITY_FLAGS
    )
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def validate_template_text(raw: str) -> list[str]:
    try:
        document = _parse_json_object(raw)
    except DuplicateJsonMember:
        return ["duplicate_json_member"]
    except NonFiniteJsonNumber:
        return ["non_finite_number"]
    except (json.JSONDecodeError, ValueError):
        return ["invalid_json"]
    if _contains_invalid_unicode(document):
        return ["invalid_unicode"]

    reasons: set[str] = set()
    if set(document) - TEMPLATE_KEYS:
        reasons.add("unknown_template_field")
    if TEMPLATE_KEYS - set(document):
        reasons.add("missing_template_field")
    if document.get("schema") != "ithildin.control_mapping_template.v1":
        reasons.add("unsupported_template_schema")
    if not _TEMPLATE_ID.fullmatch(str(document.get("template_id", ""))):
        reasons.add("invalid_template_id")
    _validate_framework(document.get("framework"), reasons)
    _validate_operator_responsibility(
        document.get("operator_responsibility"),
        reasons,
    )
    _validate_legal_review(document.get("legal_review"), reasons)
    _validate_authority(document.get("authority"), reasons)
    _validate_rows(document.get("rows"), reasons)
    if _contains_prohibited_claim(document):
        reasons.add("prohibited_claim_text")
    return sorted(reasons)


def _validate_framework(value: Any, reasons: set[str]) -> None:
    if not isinstance(value, dict) or set(value) != FRAMEWORK_KEYS:
        reasons.add("invalid_framework_shape")
        return
    if value != {
        "family": "ithildin.synthetic.control_objectives",
        "version": "1",
        "status": "synthetic_non_regulatory",
    }:
        reasons.add("real_framework_not_allowed")


def _validate_operator_responsibility(value: Any, reasons: set[str]) -> None:
    expected = {
        "operator_must_validate_applicability": True,
        "operator_must_review_legal_obligations": True,
        "operator_decides_evidence_sufficiency": True,
    }
    if not isinstance(value, dict) or set(value) != OPERATOR_RESPONSIBILITY_KEYS:
        reasons.add("invalid_operator_responsibility")
    elif value != expected:
        reasons.add("operator_responsibility_weakened")


def _validate_legal_review(value: Any, reasons: set[str]) -> None:
    if not isinstance(value, dict) or set(value) != LEGAL_REVIEW_KEYS:
        reasons.add("invalid_legal_review_shape")
    elif value != {
        "required_before_external_claim": True,
        "legal_advice_provided": False,
    }:
        reasons.add("legal_review_boundary_weakened")


def _validate_authority(value: Any, reasons: set[str]) -> None:
    if not isinstance(value, dict) or set(value) != set(AUTHORITY_FLAGS):
        reasons.add("invalid_authority_shape")
    elif value != AUTHORITY_FLAGS:
        reasons.add("authority_expansion")


def _validate_rows(value: Any, reasons: set[str]) -> None:
    if not isinstance(value, list) or not value:
        reasons.add("invalid_rows")
        return
    mapping_ids: list[str] = []
    control_refs: list[str] = []
    for row in value:
        if not isinstance(row, dict):
            reasons.add("invalid_row_shape")
            continue
        unknown = set(row) - ROW_KEYS
        missing = ROW_KEYS - set(row)
        if unknown:
            reasons.add("unknown_row_field")
        if "evidence_does_not_prove" in missing:
            reasons.add("missing_evidence_limitation")
            missing.remove("evidence_does_not_prove")
        if missing:
            reasons.add("missing_row_field")
        if unknown or missing:
            continue
        mapping_id = row.get("mapping_id")
        control_reference = row.get("control_reference")
        if not isinstance(mapping_id, str) or not _MAPPING_ID.fullmatch(mapping_id):
            reasons.add("invalid_mapping_id")
        else:
            mapping_ids.append(mapping_id)
        if (
            not isinstance(control_reference, str)
            or not _CONTROL_REFERENCE.fullmatch(control_reference)
        ):
            reasons.add("invalid_control_reference")
        else:
            control_refs.append(control_reference)
        _validate_row_values(row, reasons)
    if len(mapping_ids) != len(set(mapping_ids)):
        reasons.add("duplicate_mapping_id")
    if len(control_refs) != len(set(control_refs)):
        reasons.add("duplicate_control_reference")


def _validate_row_values(row: Mapping[str, Any], reasons: set[str]) -> None:
    objective = row.get("control_objective")
    source = row.get("evidence_source")
    fields = row.get("safe_evidence_fields")
    if objective not in CONTROL_OBJECTIVES:
        reasons.add("unknown_control_objective")
    if source not in EVIDENCE_FIELDS:
        reasons.add("unknown_evidence_source")
    if not isinstance(fields, list) or any(not isinstance(item, str) for item in fields):
        reasons.add("invalid_evidence_fields")
    elif _contains_forbidden_key(fields):
        reasons.add("forbidden_evidence_field")
    elif isinstance(source, str) and source in EVIDENCE_FIELDS:
        if len(fields) != len(set(fields)) or not set(fields).issubset(
            EVIDENCE_FIELDS[source]
        ):
            reasons.add("unknown_evidence_field")
    if row.get("operator_input") not in OPERATOR_INPUTS:
        reasons.add("invalid_operator_input")
    if row.get("evidence_supports") not in EVIDENCE_SUPPORT_STATEMENTS:
        reasons.add("unsupported_evidence_support_statement")
    elif (
        isinstance(source, str)
        and source in EVIDENCE_SUPPORT_BY_SOURCE
        and row.get("evidence_supports") != EVIDENCE_SUPPORT_BY_SOURCE[source]
    ):
        reasons.add("evidence_source_support_mismatch")
    limitations = row.get("evidence_does_not_prove")
    if not isinstance(limitations, list) or any(
        not isinstance(item, str) for item in limitations
    ):
        reasons.add("missing_evidence_limitation")
    elif not REQUIRED_LIMITATIONS.issubset(set(limitations)):
        reasons.add("missing_evidence_limitation")
    elif set(limitations) != REQUIRED_LIMITATIONS or len(limitations) != len(
        REQUIRED_LIMITATIONS
    ):
        reasons.add("invalid_evidence_limitation")
    if row.get("freshness") != "at_review_time":
        reasons.add("invalid_freshness")
    if row.get("review_cadence") != "each_mapping_review":
        reasons.add("invalid_review_cadence")
    _validate_applicability(row, reasons)
    risks = row.get("accepted_risk_refs")
    if (
        not isinstance(risks, list)
        or any(not isinstance(item, str) for item in risks)
        or not set(risks).issubset(ACCEPTED_RISK_REFS)
        or len(risks) != len(set(risks))
    ):
        reasons.add("invalid_accepted_risk_reference")
    verification = row.get("verification")
    if (
        not isinstance(verification, dict)
        or set(verification) != VERIFICATION_KEYS
        or (
            verification.get("command"),
            verification.get("packet_pointer"),
        )
        not in VERIFICATION_REFERENCES
    ):
        reasons.add("unsafe_verification_reference")


def _validate_applicability(row: Mapping[str, Any], reasons: set[str]) -> None:
    applicability = row.get("applicability")
    if not isinstance(applicability, dict) or set(applicability) != APPLICABILITY_KEYS:
        reasons.add("invalid_applicability")
        return
    status = applicability.get("status")
    reason_code = applicability.get("reason_code")
    if status not in APPLICABILITY_REASON_CODES:
        reasons.add("invalid_applicability")
        return
    if reason_code not in APPLICABILITY_REASON_CODES[str(status)]:
        reasons.add("invalid_applicability_reason")
    if (
        row.get("confidence") != CONFIDENCE_BY_STATUS[str(status)]
        or row.get("review_console_expectation") != CONSOLE_BY_STATUS[str(status)]
    ):
        reasons.add("applicability_confidence_mismatch")
    source = row.get("evidence_source")
    supports = row.get("evidence_supports")
    operator_input = row.get("operator_input")
    if status == "supported":
        if source == "none" or supports == "no_supporting_statement":
            reasons.add("invalid_supported_row")
    elif (
        source != "none"
        or supports != "no_supporting_statement"
        or operator_input != "none"
    ):
        reasons.add("invalid_non_supported_row")


def _materialize_case(
    base_raw: str,
    base_document: Mapping[str, Any],
    mutation: str,
) -> str:
    if mutation == "duplicate_json_member":
        return base_raw.replace(
            '"schema": "ithildin.control_mapping_template.v1",',
            '"schema": "ithildin.control_mapping_template.v1",\n'
            '  "schema": "ithildin.control_mapping_template.v1",',
            1,
        )
    document = copy.deepcopy(dict(base_document))
    rows = document["rows"]
    if mutation == "none":
        pass
    elif mutation == "supported_only":
        document["rows"] = [rows[0]]
    elif mutation == "unsupported_and_not_applicable":
        document["rows"] = rows[1:]
    elif mutation == "unknown_template_field":
        document["metadata"] = {}
    elif mutation == "unsupported_template_schema":
        document["schema"] = "ithildin.control_mapping_template.v2"
    elif mutation == "real_framework_not_allowed":
        document["framework"]["family"] = "external.real.framework"
    elif mutation == "legal_review_boundary_weakened":
        document["legal_review"]["required_before_external_claim"] = False
    elif mutation == "authority_expansion":
        document["authority"]["compliance_mapping_runtime_allowed"] = True
    elif mutation == "forbidden_evidence_field":
        rows[0]["safe_evidence_fields"].append("access_token")
    elif mutation == "unknown_evidence_field":
        rows[0]["safe_evidence_fields"].append("unregistered_label")
    elif mutation == "missing_evidence_limitation":
        del rows[0]["evidence_does_not_prove"]
    elif mutation == "applicability_confidence_mismatch":
        rows[0]["confidence"] = "unsupported"
    elif mutation == "unsafe_verification_reference":
        rows[0]["verification"]["command"] = "sh arbitrary-command"
    elif mutation == "invalid_accepted_risk_reference":
        rows[0]["accepted_risk_refs"] = ["AR-999"]
    elif mutation == "duplicate_mapping_id":
        rows[1]["mapping_id"] = rows[0]["mapping_id"]
    elif mutation == "duplicate_control_reference":
        rows[1]["control_reference"] = rows[0]["control_reference"]
    elif mutation == "prohibited_claim_text":
        rows[0]["evidence_supports"] = "Ｈ.Ｉ.Ｐ.Ａ.Ａ satisfied"
    elif mutation == "overflowing_json_number":
        return _dump_json(document).replace('"version": "1"', '"version": 1e999', 1)
    elif mutation == "invalid_unicode":
        document["template_id"] = "\ud800"
    elif mutation == "unknown_row_field":
        rows[0]["details"] = {}
    elif mutation == "arbitrary_limitation_value":
        rows[0]["evidence_does_not_prove"].append("access_token")
    elif mutation == "evidence_source_support_mismatch":
        rows[0]["evidence_source"] = "denied_action_evidence"
        rows[0]["safe_evidence_fields"] = ["reason_code", "risk_class", "tool_id"]
    elif mutation == "verification_reference_mismatch":
        rows[0]["verification"] = {
            "command": "make incident-reconstruction-check",
            "packet_pointer": "docs/codex/control-mapping-design.md",
        }
    else:
        raise ValueError(f"unknown template mutation: {mutation}")
    return _dump_json(document)


def _parse_json_object(raw: str) -> dict[str, Any]:
    value = json.loads(
        raw,
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=_reject_non_finite,
        parse_float=_parse_finite_float,
    )
    if not isinstance(value, dict):
        raise ValueError("JSON document must be an object")
    return value


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        if key in document:
            raise DuplicateJsonMember(key)
        document[key] = value
    return document


def _reject_non_finite(value: str) -> None:
    raise NonFiniteJsonNumber(value)


def _parse_finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise NonFiniteJsonNumber("non_finite_number")
    return parsed


def _contains_invalid_unicode(value: Any) -> bool:
    if isinstance(value, str):
        try:
            value.encode("utf-8", errors="strict")
        except UnicodeEncodeError:
            return True
    elif isinstance(value, dict):
        return any(
            _contains_invalid_unicode(key) or _contains_invalid_unicode(item)
            for key, item in value.items()
        )
    elif isinstance(value, list):
        return any(_contains_invalid_unicode(item) for item in value)
    return False


def _contains_forbidden_key(values: list[str]) -> bool:
    for value in values:
        parts = [part for part in re.split(r"[^a-z0-9]+", value.lower()) if part]
        compact = "".join(parts)
        if any(part in _SENSITIVE_KEY_PARTS for part in parts):
            return True
        if compact.endswith(
            ("accesstoken", "authtoken", "privatekey", "connectionstring")
        ):
            return True
    return False


def _contains_prohibited_claim(value: Any) -> bool:
    if isinstance(value, str):
        normalized = unicodedata.normalize("NFKC", value).casefold()
        spaced = re.sub(r"[^a-z0-9]+", " ", normalized)
        compact = re.sub(r"[^a-z0-9]+", "", normalized)
        return bool(_PROHIBITED_CLAIM.search(spaced)) or any(
            claim in compact
            for claim in (
                "hipaa",
                "glba",
                "sox",
                "gdpr",
                "nist",
                "soc2",
                "compliant",
                "certified",
                "certification",
            )
        )
    if isinstance(value, dict):
        return any(_contains_prohibited_claim(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_prohibited_claim(item) for item in value)
    return False


def _dump_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def _load_json_object(
    path: Path,
    failures: list[str],
    label: str,
) -> dict[str, Any]:
    try:
        return _parse_json_object(path.read_text(encoding="utf-8"))
    except (
        OSError,
        json.JSONDecodeError,
        DuplicateJsonMember,
        NonFiniteJsonNumber,
        ValueError,
    ):
        failures.append(f"{label} is unavailable or ambiguous")
        return {}


def _tool_count(repo_root: Path, failures: list[str]) -> int:
    manifests = sorted((repo_root / "tool-manifests").glob("*.yaml"))
    lock = _load_json_object(
        repo_root / "tool-manifests.lock.json",
        failures,
        "tool manifest lock",
    )
    lock_manifests = lock.get("manifests")
    if not isinstance(lock_manifests, list):
        failures.append("tool manifest lock has no manifest list")
        return -1
    if len(manifests) != 24 or len(lock_manifests) != 24:
        failures.append(
            "governed tool surface changed: "
            f"{len(manifests)} manifests, {len(lock_manifests)} lock entries"
        )
    return len(manifests)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _file_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())

"""Validate the static SIEM export adapter compatibility corpus."""

from __future__ import annotations

import argparse
import base64
import binascii
import copy
import hashlib
import json
import math
import re
import sys
from collections import Counter
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = "docs/codex/siem-export-adapter-compatibility-fixtures.md"
DOC_TITLE = "SIEM Export Adapter Compatibility Fixtures"
ARCHITECTURE_REL = "docs/codex/siem-export-adapter-architecture.md"
FIXTURE_DIR_REL = "tests/fixtures/siem_export_adapter"
CORPUS_REL = f"{FIXTURE_DIR_REL}/compatibility-corpus.json"
BASE_BUNDLE_REL = f"{FIXTURE_DIR_REL}/valid-bundle-v1.json"
CORPUS_SHA256 = "39a31416c80f727f1b049216ecbe6b6517bd6d0ab18ece596f74b065626d222c"
BASE_BUNDLE_SHA256 = (
    "ea2c0fa28afaa4e0aefbd343383bf15121f1638f9dd505fe6ee94a294a5601c5"
)

BUNDLE_KEYS = {"manifest", "events_ndjson", "signature"}
MANIFEST_KEYS = {
    "schema",
    "profile",
    "deployment_epoch",
    "range",
    "source_export_sha256",
    "event_count",
    "omission_count",
    "omission_categories",
    "omissions",
    "events_sha256",
    "event_schema",
    "mapper_version",
    "redaction_policy_version",
    "activation_segments",
    "created_at",
    "signing_key_id",
    "signing_key_epoch",
}
RANGE_KEYS = {
    "first_sequence",
    "last_sequence",
    "prior_source_hash",
    "head_source_hash",
}
ACTIVATION_KEYS = {"mapper", "redaction"}
ACTIVATION_SEGMENT_KEYS = {"version", "first_sequence", "last_sequence"}
OMISSION_KEYS = {"source_sequence", "source_event_hash", "category"}
OMISSION_CATEGORIES = {"not_exportable"}
EVENT_KEYS = {
    "schema",
    "event_id",
    "category",
    "action",
    "outcome",
    "severity",
    "occurred_at",
    "recorded_at",
    "deployment_epoch",
    "source_sequence",
    "source_event_hash",
    "correlation",
    "redaction",
    "attributes",
}
EVENT_REQUIRED_KEYS = EVENT_KEYS - {"attributes"}
CORRELATION_KEYS = {
    "principal_id",
    "request_id",
    "run_id",
    "mission_id",
    "workspace_id",
    "node_id",
    "tool_id",
    "policy_id",
    "approval_id",
    "artifact_id",
}
REDACTION_KEYS = {
    "mapper_version",
    "policy_version",
    "omitted_field_count",
    "categories",
}
SIGNATURE_KEYS = {
    "schema",
    "algorithm",
    "key_id",
    "key_epoch",
    "manifest_sha256",
    "signature_b64",
}
OUTCOMES = {
    "success",
    "denied",
    "failed",
    "pending",
    "recovery_required",
    "informational",
}
SEVERITIES = {"info", "low", "medium", "high", "critical"}
CATEGORY_ATTRIBUTES = {
    "audit_verification": {"verification_scope", "chain_valid"},
    "policy_decision": {"decision", "reason_code"},
    "run_lifecycle": {"state"},
    "tool_lifecycle": {"tool_name", "state"},
    "approval_lifecycle": {"state"},
    "executor_result": {"result_code"},
    "signed_export": {"export_profile"},
    "redaction_summary": {"category_count"},
    "diagnostics": {"diagnostic_code"},
    "sandbox_workspace_posture": {"posture"},
}
ATTRIBUTE_SAFE_LABEL = re.compile(r"[a-z][a-z0-9_.-]{1,63}")
TOOL_NAME = re.compile(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+")
FORBIDDEN_EVENT_KEYS = {
    "prompt",
    "raw_prompt",
    "chain_of_thought",
    "model_input",
    "model_output",
    "tool_arguments",
    "tool_results",
    "file_contents",
    "diff",
    "response_body",
    "raw_path",
    "dependency_name",
    "package_script",
    "environment_values",
    "token",
    "cookie",
    "connection_string",
    "private_key",
    "raw_idp_claims",
    "email",
    "username",
    "display_name",
    "database_rows",
    "sandbox_internals",
}

AUTHORITY_FLAGS = {
    "runtime_changes_allowed": False,
    "siem_adapter_allowed": False,
    "hosted_telemetry_allowed": False,
    "remote_delivery_allowed": False,
    "signing_key_access_allowed": False,
    "destination_credentials_allowed": False,
    "persistent_cursor_allowed": False,
    "queue_or_dead_letter_storage_allowed": False,
    "custody_grade_audit_claims_allowed": False,
    "compliance_claims_allowed": False,
    "security_operations_control_plane_allowed": False,
    "closes_erg_008": False,
    "new_power_classes_allowed": False,
}

EXPECTED_CASES = [
    {
        "id": "SEA-COMP-001",
        "label": "valid_v1",
        "mutation": "none",
        "expected_accept": True,
        "expected_reasons": [],
    },
    {
        "id": "SEA-COMP-002",
        "label": "duplicate_json_member",
        "mutation": "duplicate_json_member",
        "expected_accept": False,
        "expected_reasons": ["duplicate_json_member"],
    },
    {
        "id": "SEA-COMP-003",
        "label": "unknown_bundle_field",
        "mutation": "unknown_bundle_field",
        "expected_accept": False,
        "expected_reasons": ["unknown_bundle_field"],
    },
    {
        "id": "SEA-COMP-004",
        "label": "unsupported_manifest_schema",
        "mutation": "unsupported_manifest_schema",
        "expected_accept": False,
        "expected_reasons": ["unsupported_manifest_schema"],
    },
    {
        "id": "SEA-COMP-005",
        "label": "unsafe_event_field",
        "mutation": "unsafe_event_field",
        "expected_accept": False,
        "expected_reasons": ["forbidden_event_field"],
    },
    {
        "id": "SEA-COMP-006",
        "label": "cross_activation_range",
        "mutation": "cross_activation_range",
        "expected_accept": False,
        "expected_reasons": ["cross_activation_range"],
    },
    {
        "id": "SEA-COMP-007",
        "label": "missing_signature",
        "mutation": "missing_signature",
        "expected_accept": False,
        "expected_reasons": ["partial_bundle"],
    },
    {
        "id": "SEA-COMP-008",
        "label": "signature_reference_mismatch",
        "mutation": "signature_reference_mismatch",
        "expected_accept": False,
        "expected_reasons": ["signature_manifest_digest_mismatch"],
    },
    {
        "id": "SEA-COMP-009",
        "label": "unsupported_event_schema",
        "mutation": "unsupported_event_schema",
        "expected_accept": False,
        "expected_reasons": ["unsupported_event_schema"],
    },
    {
        "id": "SEA-COMP-010",
        "label": "events_digest_mismatch",
        "mutation": "events_digest_mismatch",
        "expected_accept": False,
        "expected_reasons": ["events_digest_mismatch"],
    },
    {
        "id": "SEA-COMP-011",
        "label": "source_sequence_gap",
        "mutation": "source_sequence_gap",
        "expected_accept": False,
        "expected_reasons": ["non_contiguous_source_sequence"],
    },
    {
        "id": "SEA-COMP-012",
        "label": "non_finite_number",
        "mutation": "non_finite_number",
        "expected_accept": False,
        "expected_reasons": ["non_finite_number"],
    },
    {
        "id": "SEA-COMP-013",
        "label": "unknown_event_attribute",
        "mutation": "unknown_event_attribute",
        "expected_accept": False,
        "expected_reasons": ["unknown_event_attribute"],
    },
    {
        "id": "SEA-COMP-014",
        "label": "nested_sensitive_attribute",
        "mutation": "nested_sensitive_attribute",
        "expected_accept": False,
        "expected_reasons": ["forbidden_event_field", "invalid_event_attribute"],
    },
    {
        "id": "SEA-COMP-015",
        "label": "omission_count_mismatch",
        "mutation": "omission_count_mismatch",
        "expected_accept": False,
        "expected_reasons": ["omission_count_mismatch", "source_range_count_mismatch"],
    },
    {
        "id": "SEA-COMP-016",
        "label": "range_head_hash_mismatch",
        "mutation": "range_head_hash_mismatch",
        "expected_accept": False,
        "expected_reasons": ["range_head_hash_mismatch"],
    },
    {
        "id": "SEA-COMP-017",
        "label": "duplicate_event_identity",
        "mutation": "duplicate_event_identity",
        "expected_accept": False,
        "expected_reasons": ["duplicate_event_identity"],
    },
    {
        "id": "SEA-COMP-018",
        "label": "invalid_calendar_timestamp",
        "mutation": "invalid_calendar_timestamp",
        "expected_accept": False,
        "expected_reasons": ["invalid_event_shape"],
    },
    {
        "id": "SEA-COMP-019",
        "label": "optional_attributes_absent",
        "mutation": "optional_attributes_absent",
        "expected_accept": True,
        "expected_reasons": [],
    },
    {
        "id": "SEA-COMP-020",
        "label": "overflowing_json_number",
        "mutation": "overflowing_json_number",
        "expected_accept": False,
        "expected_reasons": ["non_finite_number"],
    },
    {
        "id": "SEA-COMP-021",
        "label": "valid_omission_receipt",
        "mutation": "valid_omission_receipt",
        "expected_accept": True,
        "expected_reasons": [],
    },
]

REQUIRED_DOC_PHRASES = [
    "Status: static planning-only compatibility corpus for `SEA-001` and `ERG-008`.",
    "Current governed tool count: `24`.",
    "make siem-export-adapter-compatibility-check",
    "valid-bundle-v1.json",
    "compatibility-corpus.json",
    "materialized in memory",
    "never written",
    "does not claim that the fixture carries a valid Ed25519 signature",
    "SEA-COMP-001",
    "SEA-COMP-021",
    "duplicate_json_member",
    "cross_activation_range",
    "signature_manifest_digest_mismatch",
    "non_finite_number",
    "unknown_event_attribute",
    "nested_sensitive_attribute",
    "omission_count_mismatch",
    "range_head_hash_mismatch",
    "duplicate_event_identity",
    "invalid_calendar_timestamp",
    "optional_attributes_absent",
    "overflowing_json_number",
    "valid_omission_receipt",
    "reports only the safe reason label",
    "does not change `PRD-SIEM-EXPORT-001` from `no_go`",
    "does not close `ERG-008`",
    "runtime changes allowed;",
    "new power classes allowed.",
]

_HEX64 = re.compile(r"[0-9a-f]{64}")
_SAFE_ID = re.compile(r"[a-z][a-z0-9_]{2,63}")
_SAFE_CORRELATION_ID = re.compile(r"[a-z][a-z0-9_.:-]{2,127}")
_VERSION = re.compile(r"[a-z][a-z0-9_-]{0,31}-[1-9][0-9]{0,5}")
_TIMESTAMP = re.compile(
    r"20[0-9]{2}-(0[1-9]|1[0-2])-([0-2][0-9]|3[01])T"
    r"([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]Z"
)


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
            failures.append(f"compatibility fixture doc is missing phrase: {phrase}")

    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("compatibility fixture doc is missing from review docs")
    if DOC_REL not in docs_site:
        failures.append("compatibility fixture doc is missing from docs-site inputs")
    if DOC_TITLE not in review_index:
        failures.append("review-docs index is missing compatibility fixture doc")
    if DOC_REL not in readme:
        failures.append("README is missing compatibility fixture doc")
    if "make siem-export-adapter-compatibility-check" not in readme:
        failures.append("README is missing compatibility fixture command")
    if "siem-export-adapter-compatibility-check:" not in makefile:
        failures.append("Make target is missing: siem-export-adapter-compatibility-check")
    if (
        "siem-export-adapter-compatibility-check" not in release_check_body
        and "release-check: siem-export-adapter-compatibility-check" not in makefile
    ):
        failures.append("compatibility fixture check is missing from release-check")
    if "siem-export-adapter-compatibility-check" not in release_guardrails:
        failures.append("release guardrails do not require compatibility fixture check")
    if (
        Path(DOC_REL).name not in architecture
        or "SEA-001 Offline Compatibility Corpus" not in architecture
    ):
        failures.append("SIEM adapter architecture is missing compatibility corpus pointer")

    fixture_dir = repo_root / FIXTURE_DIR_REL
    corpus_path = repo_root / CORPUS_REL
    base_path = repo_root / BASE_BUNDLE_REL
    for path, label in [
        (fixture_dir, "fixture directory"),
        (corpus_path, "corpus"),
        (base_path, "base bundle"),
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
        expected_files = sorted([CORPUS_REL, BASE_BUNDLE_REL])
        if actual_files != expected_files:
            failures.append(
                "compatibility fixture file inventory drifted: "
                + ", ".join(actual_files)
            )

    corpus = _load_json_object(corpus_path, failures, "compatibility corpus")
    corpus_sha256 = _file_sha256(corpus_path)
    base_bundle_sha256 = _file_sha256(base_path)
    if corpus_sha256 != CORPUS_SHA256:
        failures.append("compatibility corpus exact-byte digest drifted")
    if base_bundle_sha256 != BASE_BUNDLE_SHA256:
        failures.append("canonical compatibility bundle exact-byte digest drifted")
    expected_corpus_keys = {
        "schema_version",
        "corpus_type",
        "status",
        "tool_count",
        "base_bundle",
        "cases",
    }
    if set(corpus) != expected_corpus_keys:
        failures.append("compatibility corpus does not use the closed top-level schema")
    if corpus.get("schema_version") != "1":
        failures.append("compatibility corpus schema_version must be 1")
    if (
        corpus.get("corpus_type")
        != "ithildin.siem_export_adapter.compatibility_fixtures"
    ):
        failures.append("compatibility corpus type drifted")
    if corpus.get("status") != "static_planning_only":
        failures.append("compatibility corpus status must remain static_planning_only")
    if corpus.get("tool_count") != 24:
        failures.append("compatibility corpus tool count must remain 24")
    if corpus.get("base_bundle") != BASE_BUNDLE_REL:
        failures.append("compatibility corpus base bundle path drifted")
    if corpus.get("cases") != EXPECTED_CASES:
        failures.append("compatibility corpus case inventory or expectations drifted")

    tool_count = _tool_count(repo_root, failures)
    base_raw = _read(base_path)
    try:
        base_document = _parse_json_object(base_raw)
    except (json.JSONDecodeError, DuplicateJsonMember, NonFiniteJsonNumber, ValueError):
        base_document = {}
        failures.append("canonical compatibility bundle is invalid JSON")

    case_results: list[dict[str, Any]] = []
    for case in EXPECTED_CASES:
        try:
            materialized = _materialize_case(
                base_raw,
                base_document,
                str(case["mutation"]),
            )
            reasons = validate_bundle_text(materialized)
        except (KeyError, TypeError, ValueError) as exc:
            reasons = ["fixture_materialization_failed"]
            failures.append(
                f"compatibility case {case['id']} could not be materialized: "
                f"{type(exc).__name__}"
            )
        expected_reasons = case["expected_reasons"]
        accepted = not reasons
        if accepted is not case["expected_accept"] or reasons != expected_reasons:
            failures.append(
                f"compatibility case {case['id']} expected "
                f"{expected_reasons!r} but observed {reasons!r}"
            )
        case_results.append(
            {
                "id": case["id"],
                "accepted": accepted,
                "reasons": reasons,
            }
        )

    if case_results and case_results[0]["reasons"]:
        failures.append("canonical compatibility bundle was not accepted")
    if any(value is not False for value in AUTHORITY_FLAGS.values()):
        failures.append("compatibility checker authority map must remain fail-closed")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "fixture_doc": DOC_REL,
        "corpus": CORPUS_REL,
        "corpus_sha256": corpus_sha256,
        "base_bundle": BASE_BUNDLE_REL,
        "base_bundle_sha256": base_bundle_sha256,
        "case_count": len(EXPECTED_CASES),
        "accepted_case_count": sum(result["accepted"] for result in case_results),
        "rejected_case_count": sum(not result["accepted"] for result in case_results),
        "case_results": case_results,
        "safe_reason_labels_only": True,
        "tool_count": tool_count,
        **AUTHORITY_FLAGS,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin SIEM export adapter compatibility check",
        f"valid: {str(report['valid']).lower()}",
        f"fixture_doc: {report['fixture_doc']}",
        f"corpus: {report['corpus']}",
        f"corpus_sha256: {report['corpus_sha256']}",
        f"base_bundle: {report['base_bundle']}",
        f"base_bundle_sha256: {report['base_bundle_sha256']}",
        f"case_count: {report['case_count']}",
        f"accepted_case_count: {report['accepted_case_count']}",
        f"rejected_case_count: {report['rejected_case_count']}",
        f"safe_reason_labels_only: {str(report['safe_reason_labels_only']).lower()}",
        f"tool_count: {report['tool_count']}",
    ]
    lines.extend(
        f"{key}: {str(value).lower()}" for key, value in AUTHORITY_FLAGS.items()
    )
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def validate_bundle_text(raw: str) -> list[str]:
    try:
        document = _parse_json_object(raw)
    except DuplicateJsonMember:
        return ["duplicate_json_member"]
    except NonFiniteJsonNumber:
        return ["non_finite_number"]
    except (json.JSONDecodeError, ValueError):
        return ["invalid_bundle_json"]
    return _validate_bundle(document)


def _validate_bundle(document: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    keys = set(document)
    if keys - BUNDLE_KEYS:
        reasons.append("unknown_bundle_field")
    if BUNDLE_KEYS - keys:
        reasons.append("partial_bundle")

    manifest = document.get("manifest")
    events_ndjson = document.get("events_ndjson")
    signature = document.get("signature")
    if not isinstance(manifest, dict):
        reasons.append("invalid_manifest_shape")
        manifest = {}
    if not isinstance(events_ndjson, str):
        reasons.append("invalid_events_shape")
        events_ndjson = ""
    if not isinstance(signature, dict):
        if "signature" in document:
            reasons.append("invalid_signature_shape")
        signature = {}

    if set(manifest) - MANIFEST_KEYS:
        reasons.append("unknown_manifest_field")
    if MANIFEST_KEYS - set(manifest):
        reasons.append("invalid_manifest_shape")
    if manifest.get("schema") != "ithildin.security_export_manifest.v1":
        reasons.append("unsupported_manifest_schema")
    if manifest.get("profile") != "operator_retrieved_offline_signed_bundle":
        reasons.append("invalid_manifest_shape")
    if not _safe_identifier(manifest.get("deployment_epoch"), "dep_"):
        reasons.append("invalid_manifest_shape")
    if not _safe_identifier(manifest.get("signing_key_id"), "key_"):
        reasons.append("invalid_manifest_shape")
    if not _exact_positive_int(manifest.get("signing_key_epoch")):
        reasons.append("invalid_manifest_shape")
    if not _valid_timestamp(manifest.get("created_at")):
        reasons.append("invalid_manifest_shape")
    for key in ["source_export_sha256", "events_sha256"]:
        if not _HEX64.fullmatch(str(manifest.get(key, ""))):
            reasons.append("invalid_manifest_shape")
    if not _VERSION.fullmatch(str(manifest.get("mapper_version", ""))):
        reasons.append("invalid_manifest_shape")
    if not _VERSION.fullmatch(str(manifest.get("redaction_policy_version", ""))):
        reasons.append("invalid_manifest_shape")
    if not _exact_nonnegative_int(manifest.get("event_count")):
        reasons.append("invalid_manifest_shape")
    if not _exact_nonnegative_int(manifest.get("omission_count")):
        reasons.append("invalid_manifest_shape")

    source_range = manifest.get("range")
    if not isinstance(source_range, dict) or set(source_range) != RANGE_KEYS:
        reasons.append("invalid_manifest_shape")
        source_range = {}
    first_sequence = source_range.get("first_sequence")
    last_sequence = source_range.get("last_sequence")
    if not _exact_positive_int(first_sequence) or not _exact_positive_int(last_sequence):
        reasons.append("invalid_manifest_shape")
    for key in ["prior_source_hash", "head_source_hash"]:
        if not _HEX64.fullmatch(str(source_range.get(key, ""))):
            reasons.append("invalid_manifest_shape")

    omission_count = manifest.get("omission_count")
    omission_categories = manifest.get("omission_categories")
    omissions = manifest.get("omissions")
    if not isinstance(omission_categories, dict) or any(
        not isinstance(key, str)
        or key not in OMISSION_CATEGORIES
        or not _exact_positive_int(value)
        for key, value in omission_categories.items()
    ):
        reasons.append("invalid_manifest_shape")
        omission_categories = {}
    if not isinstance(omissions, list):
        reasons.append("invalid_manifest_shape")
        omissions = []

    omission_sequences: list[int] = []
    omission_hashes: dict[int, str] = {}
    actual_omission_categories: Counter[str] = Counter()
    for omission in omissions:
        if not isinstance(omission, dict) or set(omission) != OMISSION_KEYS:
            reasons.append("invalid_manifest_shape")
            continue
        sequence = omission.get("source_sequence")
        event_hash = omission.get("source_event_hash")
        category = omission.get("category")
        if (
            not _exact_positive_int(sequence)
            or not isinstance(event_hash, str)
            or not _HEX64.fullmatch(event_hash)
            or not isinstance(category, str)
            or category not in OMISSION_CATEGORIES
        ):
            reasons.append("invalid_manifest_shape")
            continue
        assert type(sequence) is int
        omission_sequences.append(sequence)
        omission_hashes[sequence] = event_hash
        actual_omission_categories[category] += 1
    if (
        omission_sequences != sorted(omission_sequences)
        or len(omission_sequences) != len(set(omission_sequences))
    ):
        reasons.append("invalid_omission_sequence")
    if (
        type(omission_count) is int
        and omission_count >= 0
        and (
            omission_count != len(omissions)
            or omission_count != sum(omission_categories.values())
            or dict(actual_omission_categories) != omission_categories
        )
    ):
        reasons.append("omission_count_mismatch")

    activation = manifest.get("activation_segments")
    if not isinstance(activation, dict) or set(activation) != ACTIVATION_KEYS:
        reasons.append("invalid_manifest_shape")
        activation = {}
    for label, expected_version_key in [
        ("mapper", "mapper_version"),
        ("redaction", "redaction_policy_version"),
    ]:
        segment = activation.get(label)
        if not isinstance(segment, dict) or set(segment) != ACTIVATION_SEGMENT_KEYS:
            reasons.append("invalid_manifest_shape")
            continue
        segment_first = segment.get("first_sequence")
        segment_last = segment.get("last_sequence")
        if (
            not _exact_positive_int(segment_first)
            or not _exact_positive_int(segment_last)
            or segment.get("version") != manifest.get(expected_version_key)
        ):
            reasons.append("invalid_manifest_shape")
            continue
        if (
            type(first_sequence) is int
            and first_sequence > 0
            and type(last_sequence) is int
            and last_sequence > 0
            and type(segment_first) is int
            and segment_first > 0
            and type(segment_last) is int
            and segment_last > 0
            and (
                segment_first > first_sequence
                or segment_last < last_sequence
                or segment_first > segment_last
            )
        ):
            reasons.append("cross_activation_range")

    events, event_parse_reasons = _parse_events(events_ndjson)
    reasons.extend(event_parse_reasons)
    event_parse_failed = bool(event_parse_reasons)
    if hashlib.sha256(events_ndjson.encode("utf-8")).hexdigest() != manifest.get(
        "events_sha256"
    ):
        reasons.append("events_digest_mismatch")
    if manifest.get("event_schema") != "ithildin.security_event.v1":
        reasons.append("unsupported_event_schema")
    if not event_parse_failed and manifest.get("event_count") != len(events):
        reasons.append("event_count_mismatch")

    sequences: list[int] = []
    event_hashes: dict[int, str] = {}
    event_identities: list[tuple[str, str]] = []
    for event in events:
        reasons.extend(_validate_event(event, manifest))
        sequence = event.get("source_sequence")
        if type(sequence) is int and sequence > 0:
            sequences.append(sequence)
            source_event_hash = event.get("source_event_hash")
            if _HEX64.fullmatch(str(source_event_hash or "")):
                event_hashes[sequence] = str(source_event_hash)
        deployment_epoch = event.get("deployment_epoch")
        event_id = event.get("event_id")
        if isinstance(deployment_epoch, str) and isinstance(event_id, str):
            event_identities.append((deployment_epoch, event_id))
    if len(event_identities) != len(set(event_identities)):
        reasons.append("duplicate_event_identity")
    if sequences != sorted(sequences) or len(sequences) != len(set(sequences)):
        reasons.append("non_contiguous_source_sequence")
    if (
        not event_parse_failed
        and type(first_sequence) is int
        and first_sequence > 0
        and type(last_sequence) is int
        and last_sequence > 0
    ):
        range_size = last_sequence - first_sequence + 1
        all_sequences = sequences + omission_sequences
        if (
            first_sequence > last_sequence
            or type(manifest.get("event_count")) is not int
            or type(omission_count) is not int
            or range_size
            != int(manifest.get("event_count", -1)) + int(omission_count or 0)
        ):
            reasons.append("source_range_count_mismatch")
        range_coverage_invalid = (
            len(all_sequences) != len(set(all_sequences))
            or any(
                sequence < first_sequence or sequence > last_sequence
                for sequence in all_sequences
            )
            or len(all_sequences) != range_size
        )
        if range_coverage_invalid:
            reasons.append("non_contiguous_source_sequence")
        head_hash = event_hashes.get(last_sequence) or omission_hashes.get(last_sequence)
        if not range_coverage_invalid and head_hash != source_range.get("head_source_hash"):
            reasons.append("range_head_hash_mismatch")

    if signature:
        if set(signature) - SIGNATURE_KEYS:
            reasons.append("unknown_signature_field")
        if SIGNATURE_KEYS - set(signature):
            reasons.append("invalid_signature_shape")
        if signature.get("schema") != "ithildin.security_export_signature.v1":
            reasons.append("unsupported_signature_schema")
        if signature.get("algorithm") != "ed25519":
            reasons.append("invalid_signature_shape")
        if signature.get("key_id") != manifest.get("signing_key_id"):
            reasons.append("invalid_signature_shape")
        if signature.get("key_epoch") != manifest.get("signing_key_epoch"):
            reasons.append("invalid_signature_shape")
        expected_manifest_sha = hashlib.sha256(
            _canonical_json(manifest).encode("utf-8")
        ).hexdigest()
        if signature.get("manifest_sha256") != expected_manifest_sha:
            reasons.append("signature_manifest_digest_mismatch")
        if not _valid_signature_shape(signature.get("signature_b64")):
            reasons.append("invalid_signature_shape")

    return sorted(set(reasons))


def _parse_events(raw: str) -> tuple[list[dict[str, Any]], list[str]]:
    if not raw.endswith("\n") or "\r" in raw:
        return [], ["invalid_events_shape"]
    lines = raw.splitlines()
    if not lines or any(not line for line in lines):
        return [], ["invalid_events_shape"]
    events: list[dict[str, Any]] = []
    reasons: list[str] = []
    for line in lines:
        try:
            event = _parse_json_object(line)
        except DuplicateJsonMember:
            reasons.append("duplicate_json_member")
            continue
        except NonFiniteJsonNumber:
            reasons.append("non_finite_number")
            continue
        except (json.JSONDecodeError, ValueError):
            reasons.append("invalid_event_json")
            continue
        if _canonical_json(event) != line:
            reasons.append("non_canonical_event_json")
        events.append(event)
    return events, reasons


def _validate_event(event: dict[str, Any], manifest: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    forbidden = _forbidden_keys(event)
    if forbidden:
        reasons.append("forbidden_event_field")
    unexpected_event_keys = set(event) - EVENT_KEYS - FORBIDDEN_EVENT_KEYS
    if unexpected_event_keys:
        reasons.append("unknown_event_field")
    if EVENT_REQUIRED_KEYS - set(event):
        reasons.append("invalid_event_shape")
    if event.get("schema") != "ithildin.security_event.v1":
        reasons.append("unsupported_event_schema")
    if not _safe_identifier(event.get("event_id"), "evt_"):
        reasons.append("invalid_event_shape")
    category = event.get("category")
    if category not in CATEGORY_ATTRIBUTES:
        reasons.append("invalid_event_shape")
    if not isinstance(event.get("action"), str) or not re.fullmatch(
        r"[a-z][a-z0-9_.]{2,63}",
        str(event.get("action", "")),
    ):
        reasons.append("invalid_event_shape")
    if event.get("outcome") not in OUTCOMES:
        reasons.append("invalid_event_shape")
    if event.get("severity") not in SEVERITIES:
        reasons.append("invalid_event_shape")
    occurred_at = _parse_timestamp(event.get("occurred_at"))
    recorded_at = _parse_timestamp(event.get("recorded_at"))
    if occurred_at is None or recorded_at is None:
        reasons.append("invalid_event_shape")
    elif recorded_at < occurred_at:
        reasons.append("invalid_event_shape")
    if event.get("deployment_epoch") != manifest.get("deployment_epoch"):
        reasons.append("deployment_epoch_mismatch")
    if not _exact_positive_int(event.get("source_sequence")):
        reasons.append("invalid_event_shape")
    if not _HEX64.fullmatch(str(event.get("source_event_hash", ""))):
        reasons.append("invalid_event_shape")

    correlation = event.get("correlation")
    if not isinstance(correlation, dict) or set(correlation) - CORRELATION_KEYS:
        reasons.append("invalid_event_shape")
    elif any(
        not _safe_correlation_identifier(value, _correlation_prefix(key))
        for key, value in correlation.items()
    ):
        reasons.append("invalid_event_shape")

    redaction = event.get("redaction")
    if not isinstance(redaction, dict) or set(redaction) != REDACTION_KEYS:
        reasons.append("invalid_event_shape")
    else:
        if redaction.get("mapper_version") != manifest.get("mapper_version"):
            reasons.append("mapper_version_mismatch")
        if redaction.get("policy_version") != manifest.get(
            "redaction_policy_version"
        ):
            reasons.append("redaction_policy_version_mismatch")
        if not _exact_nonnegative_int(redaction.get("omitted_field_count")):
            reasons.append("invalid_event_shape")
        categories = redaction.get("categories")
        if not isinstance(categories, list) or any(
            not isinstance(value, str)
            or not re.fullmatch(r"[a-z][a-z0-9_]{1,31}", value)
            for value in categories
        ):
            reasons.append("invalid_event_shape")

    attributes = event.get("attributes")
    if "attributes" not in event:
        return reasons
    if not isinstance(attributes, dict):
        reasons.append("invalid_event_shape")
    elif isinstance(category, str) and category in CATEGORY_ATTRIBUTES:
        unknown_attributes = (
            set(attributes)
            - CATEGORY_ATTRIBUTES[category]
            - FORBIDDEN_EVENT_KEYS
        )
        if unknown_attributes:
            reasons.append("unknown_event_attribute")
        if (
            not unknown_attributes
            and not (set(attributes) & FORBIDDEN_EVENT_KEYS)
        ):
            reasons.extend(_validate_category_attributes(category, attributes))
    return reasons


def _validate_category_attributes(
    category: str,
    attributes: Mapping[str, Any],
) -> list[str]:
    if set(attributes) != CATEGORY_ATTRIBUTES[category]:
        return ["invalid_event_attribute"]
    if category == "audit_verification":
        if attributes.get("verification_scope") not in {
            "requested_range",
            "full_chain",
        } or not isinstance(attributes.get("chain_valid"), bool):
            return ["invalid_event_attribute"]
        return []
    if category == "policy_decision":
        decision = attributes.get("decision")
        return (
            []
            if isinstance(decision, str)
            and decision in {"allow", "deny", "require_approval"}
            and _safe_label(attributes.get("reason_code"))
            else ["invalid_event_attribute"]
        )
    if category in {
        "run_lifecycle",
        "approval_lifecycle",
        "sandbox_workspace_posture",
    }:
        key = "posture" if category == "sandbox_workspace_posture" else "state"
        return [] if _safe_label(attributes.get(key)) else ["invalid_event_attribute"]
    if category == "tool_lifecycle":
        return (
            []
            if isinstance(attributes.get("tool_name"), str)
            and TOOL_NAME.fullmatch(str(attributes["tool_name"]))
            and _safe_label(attributes.get("state"))
            else ["invalid_event_attribute"]
        )
    if category in {"executor_result", "diagnostics"}:
        key = "result_code" if category == "executor_result" else "diagnostic_code"
        return [] if _safe_label(attributes.get(key)) else ["invalid_event_attribute"]
    if category == "signed_export":
        return (
            []
            if attributes.get("export_profile")
            == "operator_retrieved_offline_signed_bundle"
            else ["invalid_event_attribute"]
        )
    if category == "redaction_summary":
        return (
            []
            if _exact_nonnegative_int(attributes.get("category_count"))
            else ["invalid_event_attribute"]
        )
    return ["invalid_event_attribute"]


def _materialize_case(
    base_raw: str,
    base_document: dict[str, Any],
    mutation: str,
) -> str:
    if mutation == "none":
        return base_raw
    if mutation == "duplicate_json_member":
        stripped = base_raw.rstrip()
        if not stripped.endswith("}"):
            raise ValueError("base bundle is not an object")
        return stripped[:-1] + ', "manifest": {} }\n'

    document = copy.deepcopy(base_document)
    if mutation == "unknown_bundle_field":
        document["delivery_target"] = "forbidden"
    elif mutation == "unsupported_manifest_schema":
        document["manifest"]["schema"] = "ithildin.security_export_manifest.v2"
        _rebind_signature(document)
    elif mutation == "unsafe_event_field":
        events = _fixture_events(document)
        events[0]["attributes"]["raw_prompt"] = "must-not-echo"
        _replace_events_and_rebind(document, events)
    elif mutation == "cross_activation_range":
        document["manifest"]["activation_segments"]["mapper"]["last_sequence"] = 40
        _rebind_signature(document)
    elif mutation == "missing_signature":
        document.pop("signature")
    elif mutation == "signature_reference_mismatch":
        document["signature"]["manifest_sha256"] = "0" * 64
    elif mutation == "unsupported_event_schema":
        events = _fixture_events(document)
        events[0]["schema"] = "ithildin.security_event.v2"
        document["manifest"]["event_schema"] = "ithildin.security_event.v2"
        _replace_events_and_rebind(document, events)
    elif mutation == "events_digest_mismatch":
        document["manifest"]["events_sha256"] = "0" * 64
        _rebind_signature(document)
    elif mutation == "source_sequence_gap":
        events = _fixture_events(document)
        events[0]["source_sequence"] = 43
        _replace_events_and_rebind(document, events)
    elif mutation == "non_finite_number":
        events_raw = str(document["events_ndjson"]).replace(
            '"source_sequence":41',
            '"source_sequence":NaN',
        )
        document["events_ndjson"] = events_raw
        document["manifest"]["events_sha256"] = hashlib.sha256(
            events_raw.encode("utf-8")
        ).hexdigest()
        _rebind_signature(document)
    elif mutation == "unknown_event_attribute":
        events = _fixture_events(document)
        events[0]["attributes"]["unregistered_detail"] = "blocked"
        _replace_events_and_rebind(document, events)
    elif mutation == "nested_sensitive_attribute":
        events = _fixture_events(document)
        events[0]["category"] = "policy_decision"
        events[0]["attributes"] = {
            "decision": {"access_token": "must-not-echo"},
            "reason_code": "policy_match",
        }
        _replace_events_and_rebind(document, events)
    elif mutation == "omission_count_mismatch":
        document["manifest"]["omission_count"] = 1
        _rebind_signature(document)
    elif mutation == "range_head_hash_mismatch":
        document["manifest"]["range"]["head_source_hash"] = "f" * 64
        _rebind_signature(document)
    elif mutation == "duplicate_event_identity":
        events = _fixture_events(document)
        duplicate = copy.deepcopy(events[0])
        duplicate["source_sequence"] = 42
        duplicate["source_event_hash"] = "2" * 64
        events.append(duplicate)
        document["manifest"]["event_count"] = 2
        document["manifest"]["range"]["last_sequence"] = 42
        document["manifest"]["range"]["head_source_hash"] = "2" * 64
        _replace_events_and_rebind(document, events)
    elif mutation == "invalid_calendar_timestamp":
        events = _fixture_events(document)
        events[0]["occurred_at"] = "2026-02-31T12:00:00Z"
        _replace_events_and_rebind(document, events)
    elif mutation == "optional_attributes_absent":
        events = _fixture_events(document)
        events[0].pop("attributes")
        _replace_events_and_rebind(document, events)
    elif mutation == "overflowing_json_number":
        events_raw = str(document["events_ndjson"]).replace(
            '"source_sequence":41',
            '"source_sequence":1e1000000',
        )
        document["events_ndjson"] = events_raw
        document["manifest"]["events_sha256"] = hashlib.sha256(
            events_raw.encode("utf-8")
        ).hexdigest()
        _rebind_signature(document)
    elif mutation == "valid_omission_receipt":
        events = _fixture_events(document)
        last_event = copy.deepcopy(events[0])
        last_event["event_id"] = "evt_2222222222222222"
        last_event["source_sequence"] = 43
        last_event["source_event_hash"] = "3" * 64
        last_event["occurred_at"] = "2026-07-23T12:00:02Z"
        last_event["recorded_at"] = "2026-07-23T12:00:02Z"
        events.append(last_event)
        document["manifest"]["event_count"] = 2
        document["manifest"]["omission_count"] = 1
        document["manifest"]["omission_categories"] = {"not_exportable": 1}
        document["manifest"]["omissions"] = [
            {
                "category": "not_exportable",
                "source_event_hash": "2" * 64,
                "source_sequence": 42,
            }
        ]
        document["manifest"]["range"]["last_sequence"] = 43
        document["manifest"]["range"]["head_source_hash"] = "3" * 64
        _replace_events_and_rebind(document, events)
    else:
        raise ValueError(f"unknown compatibility mutation: {mutation}")
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def _fixture_events(document: Mapping[str, Any]) -> list[dict[str, Any]]:
    events, reasons = _parse_events(str(document["events_ndjson"]))
    if reasons:
        raise ValueError("base fixture event stream is invalid")
    return events


def _replace_events_and_rebind(
    document: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    events_raw = "".join(_canonical_json(event) + "\n" for event in events)
    document["events_ndjson"] = events_raw
    document["manifest"]["events_sha256"] = hashlib.sha256(
        events_raw.encode("utf-8")
    ).hexdigest()
    _rebind_signature(document)


def _rebind_signature(document: dict[str, Any]) -> None:
    document["signature"]["manifest_sha256"] = hashlib.sha256(
        _canonical_json(document["manifest"]).encode("utf-8")
    ).hexdigest()


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


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _forbidden_keys(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if _forbidden_key(key):
                found.add(key.lower())
            found.update(_forbidden_keys(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_forbidden_keys(item))
    return found


def _forbidden_key(value: str) -> bool:
    lowered = value.lower()
    if lowered in FORBIDDEN_EVENT_KEYS:
        return True
    parts = [part for part in re.split(r"[^a-z0-9]+", lowered) if part]
    sensitive_parts = {
        "token",
        "cookie",
        "secret",
        "password",
        "passwd",
        "credential",
    }
    if any(part in sensitive_parts for part in parts):
        return True
    compact = "".join(parts)
    return compact.endswith(
        (
            "accesstoken",
            "authtoken",
            "refreshtoken",
            "sessiontoken",
            "privatekey",
            "sessionkey",
            "connectionstring",
        )
    )


def _valid_signature_shape(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        return False
    return len(decoded) == 64


def _safe_identifier(value: Any, prefix: str) -> bool:
    return (
        isinstance(value, str)
        and value.startswith(prefix)
        and bool(_SAFE_ID.fullmatch(value))
    )


def _safe_correlation_identifier(value: Any, prefix: str) -> bool:
    return (
        isinstance(value, str)
        and value.startswith(prefix)
        and bool(_SAFE_CORRELATION_ID.fullmatch(value))
    )


def _safe_label(value: Any) -> bool:
    return isinstance(value, str) and bool(ATTRIBUTE_SAFE_LABEL.fullmatch(value))


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not _TIMESTAMP.fullmatch(value):
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None
    return parsed if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value else None


def _valid_timestamp(value: Any) -> bool:
    return _parse_timestamp(value) is not None


def _correlation_prefix(key: str) -> str:
    return {
        "principal_id": "agent:",
        "request_id": "req_",
        "run_id": "run_",
        "mission_id": "mis_",
        "workspace_id": "ws_",
        "node_id": "node_",
        "tool_id": "tool_",
        "policy_id": "pol_",
        "approval_id": "apr_",
        "artifact_id": "art_",
    }[key]


def _exact_positive_int(value: Any) -> bool:
    return type(value) is int and value > 0


def _exact_nonnegative_int(value: Any) -> bool:
    return type(value) is int and value >= 0


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

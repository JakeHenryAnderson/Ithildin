"""Normalize an external review response into structured finding drafts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

VALID_SOURCE_ACCESS = {"source-level", "packet-and-source", "packet-only", "docs-only"}
VALID_SEVERITIES = {"critical", "high", "medium", "low", "informational"}
VALID_BLOCKING_STATUSES = {"blocking", "should-fix", "later", "accepted risk", "advisory"}
VALID_DISPOSITIONS = {"open", "fixed", "deferred", "rejected", "accepted-deferred"}
FINDING_PATTERN = re.compile(
    r"^EXT-((PA|FS|HTTP|SE|PR|MCP|UI|REL)-(\d{3}|###)|(\d{3}|###))$"
)
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{7,40}$")
SECRET_MARKERS = (
    "BEGIN PRIVATE KEY",
    "ITHILDIN_ADMIN_TOKEN=",
    "dev-admin-token-change-me",
    "password=",
    "secret=",
)


class ExternalResponseNormalizationError(RuntimeError):
    """Raised when a raw external response is not intake-ready."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="raw markdown external review response")
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--reviewer-type", required=True)
    parser.add_argument("--source-access", required=True, choices=sorted(VALID_SOURCE_ACCESS))
    parser.add_argument("--reviewed-commit", required=True)
    parser.add_argument("--reviewed-packet-hash", required=True)
    parser.add_argument("--area", required=True)
    parser.add_argument("--output", help="write normalized JSON to this path")
    args = parser.parse_args()

    try:
        result = normalize_response(
            Path(args.input).read_text(encoding="utf-8"),
            reviewer=args.reviewer,
            reviewer_type=args.reviewer_type,
            source_access=args.source_access,
            reviewed_commit=args.reviewed_commit,
            reviewed_packet_hash=args.reviewed_packet_hash,
            area=args.area,
        )
    except ExternalResponseNormalizationError as exc:
        print(f"external response normalization failed: {exc}", file=sys.stderr)
        return 1

    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 0


def normalize_response(
    text: str,
    *,
    reviewer: str,
    reviewer_type: str,
    source_access: str,
    reviewed_commit: str,
    reviewed_packet_hash: str,
    area: str,
) -> dict[str, Any]:
    _reject_secret_markers(text)
    if not reviewer.strip():
        raise ExternalResponseNormalizationError("reviewer is required")
    if not reviewer_type.strip():
        raise ExternalResponseNormalizationError("reviewer type is required")
    if source_access not in VALID_SOURCE_ACCESS:
        raise ExternalResponseNormalizationError(f"invalid source access level: {source_access}")
    if not COMMIT_PATTERN.match(reviewed_commit):
        raise ExternalResponseNormalizationError("reviewed commit must be a git commit hash")
    if not reviewed_packet_hash.startswith("sha256:"):
        raise ExternalResponseNormalizationError("reviewed packet hash must start with sha256:")
    if not area.strip():
        raise ExternalResponseNormalizationError("reviewed area is required")

    findings = _extract_findings(text, source_access=source_access)
    return {
        "schema_version": "1",
        "response_type": "ithildin.external_review.normalized_response",
        "reviewer": reviewer,
        "reviewer_type": reviewer_type,
        "source_access": source_access,
        "reviewed_commit": reviewed_commit,
        "reviewed_packet_hash": reviewed_packet_hash,
        "area": area,
        "finding_count": len(findings),
        "findings": findings,
        "can_close_source_rows": source_access in {"source-level", "packet-and-source"},
        "mutates_findings": False,
        "closes_external_review": False,
    }


def _extract_findings(text: str, *, source_access: str) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    header: list[str] | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not (line.startswith("|") and line.endswith("|")):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if all(set(cell) <= {"-", ":"} for cell in cells):
            continue
        normalized = [_normalize_header(cell) for cell in cells]
        if "finding id" in normalized and "severity" in normalized:
            header = normalized
            continue
        if header is None:
            continue
        row = dict(zip(header, cells, strict=False))
        if not row.get("finding id", "").startswith("EXT-"):
            continue
        findings.append(_validate_finding_row(row, source_access=source_access))
    return findings


def _validate_finding_row(row: dict[str, str], *, source_access: str) -> dict[str, str]:
    required = [
        "finding id",
        "severity",
        "area",
        "affected files/functions",
        "blocking status",
        "disposition",
        "recommended fix",
    ]
    missing = [field for field in required if not row.get(field)]
    if missing:
        raise ExternalResponseNormalizationError(f"finding row missing fields: {missing}")
    finding_id = row["finding id"]
    if not FINDING_PATTERN.match(finding_id):
        raise ExternalResponseNormalizationError(f"invalid finding ID: {finding_id}")
    severity = row["severity"].lower()
    if severity not in VALID_SEVERITIES:
        raise ExternalResponseNormalizationError(f"{finding_id} invalid severity: {severity}")
    blocking_status = row["blocking status"].lower()
    if blocking_status not in VALID_BLOCKING_STATUSES:
        raise ExternalResponseNormalizationError(
            f"{finding_id} invalid blocking status: {blocking_status}"
        )
    disposition = row["disposition"].lower()
    if disposition not in VALID_DISPOSITIONS:
        raise ExternalResponseNormalizationError(
            f"{finding_id} invalid disposition: {disposition}"
        )
    affected = row["affected files/functions"]
    if source_access in {"source-level", "packet-and-source"} and affected.lower() in {
        "n/a",
        "none",
        "unknown",
        "packet-only limitation",
    }:
        raise ExternalResponseNormalizationError(
            f"{finding_id} needs affected files/functions for {source_access}"
        )
    return {
        "finding_id": finding_id,
        "severity": severity,
        "area": row["area"],
        "affected_files_functions": affected,
        "blocking_status": blocking_status,
        "disposition": disposition,
        "recommended_fix": row["recommended fix"],
    }


def _normalize_header(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _reject_secret_markers(text: str) -> None:
    lowered = text.lower()
    for marker in SECRET_MARKERS:
        if marker.lower() in lowered:
            raise ExternalResponseNormalizationError(
                f"external response contains secret-like marker: {marker}"
            )


if __name__ == "__main__":
    raise SystemExit(main())

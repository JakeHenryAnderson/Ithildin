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
AREA_NAMESPACES = {
    "patch-apply": "PA",
    "filesystem": "FS",
    "http-fetch": "HTTP",
    "signed-evidence": "SE",
    "policy-registry": "PR",
    "mcp-ingress": "MCP",
    "review-console": "UI",
    "release-automation": "REL",
    "sandbox-vm-static-preflight": "SVP",
    "sandbox-vm-live-poc": "LIVE-POC",
    "sandbox-vm-live-poc-runtime-gate-readiness": "LIVE-GATE",
    "sandbox-vm-live-poc-runtime-descriptor-only": "LIVE-DESC",
    "trusted-host-promotion": "TRUSTED-HOST",
    "production-identity-storage": "PROD-IAM-STORAGE",
    "siem-export-adapter": "SIEM-ADAPTER",
    "compliance-mapping": "COMPLIANCE-MAPPING",
    "mission-control-display": "MC-DISPLAY",
    "public-security-product-positioning": "PUBLIC-POSITIONING",
}
FINDING_PATTERN = re.compile(
    r"^EXT-(([A-Z]+(?:-[A-Z]+)*)-(\d{3}|###)|(\d{3}|###))$"
)
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{7,40}$")
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
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
    if not SHA256_PATTERN.match(reviewed_packet_hash):
        raise ExternalResponseNormalizationError(
            "reviewed packet hash must be sha256:<64 lowercase hex chars>"
        )
    area = area.strip()
    if not area:
        raise ExternalResponseNormalizationError("reviewed area is required")
    if area not in AREA_NAMESPACES:
        raise ExternalResponseNormalizationError(f"unknown reviewed area: {area}")

    findings = _extract_findings(text, source_access=source_access, area=area)
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


def _extract_findings(text: str, *, source_access: str, area: str) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    header: list[str] | None = None
    saw_finding_table = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        cells = _table_cells(line)
        if cells is None:
            continue
        if all(set(cell) <= {"-", ":"} for cell in cells):
            continue
        normalized = [_normalize_header(cell) for cell in cells]
        if "finding id" in normalized and "severity" in normalized:
            header = normalized
            saw_finding_table = True
            continue
        if header is None:
            continue
        if len(cells) != len(header):
            header = None
            continue
        row = dict(zip(header, cells, strict=False))
        if not row.get("finding id", "").startswith("EXT-"):
            continue
        findings.append(_validate_finding_row(row, source_access=source_access, area=area))
    if not findings and not _has_explicit_no_findings_statement(text):
        if saw_finding_table:
            raise ExternalResponseNormalizationError(
                "finding table contained no valid EXT findings; explicitly state no findings"
            )
        raise ExternalResponseNormalizationError(
            "response must contain a finding table or explicitly state no findings"
        )
    return findings


def _table_cells(line: str) -> list[str] | None:
    if line.startswith("|") and line.endswith("|"):
        return [cell.strip() for cell in line.strip("|").split("|")]
    if "\t" in line:
        return [cell.strip() for cell in line.split("\t")]
    return None


def _validate_finding_row(
    row: dict[str, str], *, source_access: str, area: str
) -> dict[str, str]:
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
    expected_namespace = AREA_NAMESPACES[area]
    namespace_match = re.match(r"^EXT-([A-Z]+(?:-[A-Z]+)*)-", finding_id)
    if namespace_match and namespace_match.group(1) != expected_namespace:
        raise ExternalResponseNormalizationError(
            f"{finding_id} namespace does not match reviewed area: {area}"
        )
    row_area = _normalize_area(row["area"])
    if row_area != area:
        raise ExternalResponseNormalizationError(
            f"{finding_id} area {row_area!r} does not match reviewed area: {area}"
        )
    severity = _normalize_severity(row["severity"])
    if severity not in VALID_SEVERITIES:
        raise ExternalResponseNormalizationError(f"{finding_id} invalid severity: {severity}")
    blocking_status = _normalize_blocking_status(row["blocking status"])
    if blocking_status not in VALID_BLOCKING_STATUSES:
        raise ExternalResponseNormalizationError(
            f"{finding_id} invalid blocking status: {blocking_status}"
        )
    disposition = _normalize_disposition(row["disposition"])
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
        "area": row_area,
        "affected_files_functions": affected,
        "blocking_status": blocking_status,
        "disposition": disposition,
        "recommended_fix": row["recommended fix"],
    }


def _normalize_header(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _normalize_area(value: str) -> str:
    return re.sub(r"\s+", "-", value.strip().lower())


def _has_explicit_no_findings_statement(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    return any(
        marker in normalized
        for marker in (
            "no findings",
            "there are no findings",
            "no actionable findings",
            "finding_count: 0",
            "finding count: 0",
        )
    )


def _normalize_severity(value: str) -> str:
    normalized = value.strip().lower()
    if normalized == "low/informational":
        return "low"
    if "/" in normalized:
        normalized = normalized.split("/", maxsplit=1)[0].strip()
    return normalized


def _normalize_blocking_status(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in VALID_BLOCKING_STATUSES:
        return normalized
    if "blocking" in normalized:
        return "blocking"
    if "should-fix" in normalized or "should fix" in normalized:
        return "should-fix"
    if "accepted" in normalized:
        return "accepted risk"
    if "later" in normalized or "advisory" in normalized:
        return "later"
    return normalized


def _normalize_disposition(value: str) -> str:
    normalized = value.strip().lower()
    if normalized == "accepted-deferred":
        return "deferred"
    return normalized


def _reject_secret_markers(text: str) -> None:
    lowered = text.lower()
    for marker in SECRET_MARKERS:
        if marker.lower() in lowered:
            raise ExternalResponseNormalizationError(
                f"external response contains secret-like marker: {marker}"
            )


if __name__ == "__main__":
    raise SystemExit(main())

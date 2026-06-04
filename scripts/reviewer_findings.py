"""Validate structured reviewer finding records."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FINDINGS_DIR = ROOT / "docs/codex/findings"

REQUIRED_FIELDS = [
    "Finding ID",
    "Severity",
    "Area",
    "Affected files/functions",
    "Claim being tested",
    "Observed behavior",
    "Risk",
    "Recommended fix",
    "Blocking status",
    "Disposition",
    "Verification notes",
]
VALID_SEVERITIES = {"critical", "high", "medium", "low", "informational"}
VALID_BLOCKING_STATUSES = {"blocking", "should-fix", "later", "accepted risk"}
VALID_DISPOSITIONS = {"open", "fixed", "deferred", "rejected"}
FINDING_ID_PATTERN = re.compile(
    r"^((ISR|EXT|SUB|AI)-\d{3}|EXT-(PA|FS|HTTP|SE|PR|MCP|UI|REL)-\d{3}|"
    r"SUB-GITMETA-\d{3}|V03-(INT|EXT|DOCS)-[A-Z0-9]+-\d{3})$"
)
FIELD_PATTERN = re.compile(r"^-\s+(?P<field>[^:]+):\s*(?P<value>.*)$")
SECRET_MARKERS = (
    "BEGIN PRIVATE KEY",
    "ITHILDIN_ADMIN_TOKEN=",
    "dev-admin-token-change-me",
    "password=",
    "secret=",
)


class FindingSummary(TypedDict):
    path: str
    finding_id: str
    severity: str
    blocking_status: str
    disposition: str


@dataclass(frozen=True)
class FindingRecord:
    path: Path
    fields: dict[str, str]

    @property
    def finding_id(self) -> str:
        return self.fields["Finding ID"]

    def summary(self, root: Path) -> FindingSummary:
        return {
            "path": _display_path(self.path, root),
            "finding_id": self.finding_id,
            "severity": self.fields["Severity"],
            "blocking_status": self.fields["Blocking status"],
            "disposition": self.fields["Disposition"],
        }


class FindingValidationError(RuntimeError):
    """Raised when reviewer finding records are invalid."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--findings-dir", default=str(DEFAULT_FINDINGS_DIR))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    findings_dir = Path(args.findings_dir)
    try:
        records = validate_findings(findings_dir=findings_dir, repo_root=ROOT)
    except FindingValidationError as exc:
        print(f"reviewer finding validation failed: {exc}", file=sys.stderr)
        return 1

    summaries = [record.summary(ROOT) for record in records]
    if args.json:
        print(json.dumps({"count": len(summaries), "findings": summaries}, indent=2))
    else:
        print(f"Reviewer finding validation passed: {len(summaries)} finding(s).")
        for summary in summaries:
            print(
                f"- {summary['finding_id']} {summary['severity']} "
                f"{summary['blocking_status']} {summary['disposition']} "
                f"({summary['path']})"
            )
    return 0


def validate_findings(findings_dir: Path, repo_root: Path) -> list[FindingRecord]:
    if not findings_dir.exists():
        return []
    if not findings_dir.is_dir():
        raise FindingValidationError(f"findings path is not a directory: {findings_dir}")

    records: list[FindingRecord] = []
    seen_ids: set[str] = set()
    for path in sorted(findings_dir.glob("*.md")):
        if path.name.startswith("."):
            continue
        record = _parse_record(path)
        _validate_record(record, repo_root)
        if record.finding_id in seen_ids:
            raise FindingValidationError(f"duplicate finding ID: {record.finding_id}")
        seen_ids.add(record.finding_id)
        records.append(record)
    return records


def _parse_record(path: Path) -> FindingRecord:
    text = path.read_text(encoding="utf-8")
    for marker in SECRET_MARKERS:
        if marker.lower() in text.lower():
            raise FindingValidationError(f"{path} contains secret-like marker: {marker}")

    fields: dict[str, str] = {}
    for line in text.splitlines():
        match = FIELD_PATTERN.match(line.strip())
        if match:
            fields[match.group("field").strip()] = match.group("value").strip()
    return FindingRecord(path=path, fields=fields)


def _validate_record(record: FindingRecord, repo_root: Path) -> None:
    missing = [field for field in REQUIRED_FIELDS if not record.fields.get(field)]
    if missing:
        raise FindingValidationError(f"{_display_path(record.path, repo_root)} missing {missing}")

    if not FINDING_ID_PATTERN.match(record.fields["Finding ID"]):
        raise FindingValidationError(
            f"{_display_path(record.path, repo_root)} has invalid Finding ID"
        )
    severity = record.fields["Severity"].lower()
    if severity not in VALID_SEVERITIES:
        raise FindingValidationError(
            f"{record.finding_id} has invalid severity: {record.fields['Severity']}"
        )
    blocking_status = record.fields["Blocking status"].lower()
    if blocking_status not in VALID_BLOCKING_STATUSES:
        raise FindingValidationError(
            f"{record.finding_id} has invalid blocking status: "
            f"{record.fields['Blocking status']}"
        )
    disposition = record.fields["Disposition"].lower()
    if disposition not in VALID_DISPOSITIONS:
        raise FindingValidationError(
            f"{record.finding_id} has invalid disposition: {record.fields['Disposition']}"
        )
    if severity in {"critical", "high"} and disposition == "open":
        raise FindingValidationError(
            f"{record.finding_id} is an open {severity} finding; stop and resolve, "
            "defer, reject, or accept the risk before release gates pass"
        )
    if blocking_status == "blocking" and disposition == "open":
        raise FindingValidationError(
            f"{record.finding_id} is an open blocking finding; release gates cannot pass"
        )
    record.fields["Severity"] = severity
    record.fields["Blocking status"] = blocking_status
    record.fields["Disposition"] = disposition


def _display_path(path: Path, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())

"""Validate ERG-004 descriptor-only response-application playbook wiring."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import review_docs
from scripts import (
    sandbox_vm_live_poc_runtime_descriptor_only_response_application_record_check as record,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_REL = (
    "docs/codex/"
    "sandbox-vm-live-poc-runtime-descriptor-only-response-application-playbook.md"
)
DOC_NAME = (
    "sandbox-vm-live-poc-runtime-descriptor-only-response-application-playbook.md"
)

REQUIRED_PHRASES = [
    "Status: manager-owned playbook for applying a real `ERG-004` descriptor-only response.",
    "Current governed tool count: `24`.",
    "Current selected capability: `not selected`.",
    "descriptor_only_runtime_implemented_source_review_pending",
    "make sandbox-vm-live-poc-runtime-descriptor-only-response-application-playbook-check",
    "var/review-runs/sandbox-vm-live-poc-runtime-descriptor-only/normalized-response.json",
    "ithildin.external_review.normalized_response",
    "sandbox-vm-live-poc-runtime-descriptor-only",
    "EXT-LIVE-DESC-###",
    "source-level` or `packet-and-source`",
    "can_close_source_rows: true",
    "mutates_findings: false",
    "closes_external_review: false",
    "approve_descriptor_only_local_preview_disposition",
    "make sandbox-vm-live-poc-runtime-descriptor-only-response-application-preflight-check",
    (
        "ERG-004 descriptor-only: source_review_pending -> "
        "descriptor_only_local_preview_disposition_ready"
    ),
]

REQUIRED_ALLOWED_FILES = [
    "docs/codex/source-review-closure-matrix.md",
    "docs/codex/enterprise-readiness-gap-matrix.md",
    "docs/codex/enterprise-external-review-queue.md",
    "docs/codex/post-rc-decision-register.md",
    "docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-response-application-record.md",
    "docs/codex/findings/ext-live-desc-*.md",
]

REQUIRED_BLOCKED_BOUNDARIES = [
    "runtime implementation",
    "live VM/container inspection",
    "VM/container lifecycle management",
    "sandbox orchestration",
    "Mission Control runtime behavior",
    "local model invocation",
    "trusted-host promotion",
    "host writes",
    "network expansion",
    "API/MCP profile loading",
    "new governed tool powers",
    "public/security-product positioning",
]

FORBIDDEN_PHRASES = [
    "runtime implementation is approved",
    "live VM/container inspection is approved",
    "sandbox orchestration is approved",
    "ERG-004 is closed",
    "public security product approved",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report(ROOT)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(record.render_report(report))
    return 0 if report["valid"] else 1


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    doc = _read(repo_root / DOC_REL)
    makefile = _read(repo_root / "Makefile")
    readme = _read(repo_root / "README.md")
    docs_site = _read(repo_root / "scripts/build_docs_site.py")
    release_guardrails = _read(repo_root / "scripts/release_guardrails.py")
    review_index = _read(repo_root / "docs/codex/review-docs-index.md")
    record_doc = _read(
        repo_root
        / "docs/codex/sandbox-vm-live-poc-runtime-descriptor-only-response-application-record.md"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    record_report = record.build_report(repo_root)

    if not doc:
        failures.append("descriptor-only response application playbook doc is missing")
    else:
        normalized = " ".join(doc.split())
        lowered = doc.lower()
        for phrase in REQUIRED_PHRASES:
            if phrase not in normalized:
                failures.append(f"response application playbook is missing phrase: {phrase}")
        for allowed_file in REQUIRED_ALLOWED_FILES:
            if allowed_file not in doc:
                failures.append(
                    f"response application playbook is missing allowed file: {allowed_file}"
                )
        for boundary in REQUIRED_BLOCKED_BOUNDARIES:
            if boundary not in doc:
                failures.append(
                    f"response application playbook is missing blocked boundary: {boundary}"
                )
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(f"response application playbook contains: {phrase}")

    if record_report.get("valid") is not True:
        failures.append("response application record is not valid")
        failures.extend(f"record: {failure}" for failure in record_report.get("failures", []))

    target = "sandbox-vm-live-poc-runtime-descriptor-only-response-application-playbook-check"
    if f"{target}:" not in makefile:
        failures.append(f"Make target is missing: {target}")
    if target not in release_check_body and f"release-check: {target}" not in makefile:
        failures.append("response application playbook check missing from release-check")
    if target not in release_guardrails:
        failures.append("release guardrails do not require response application playbook")
    if f"make {target}" not in readme:
        failures.append("README is missing response application playbook command")
    if DOC_REL not in readme:
        failures.append("README is missing response application playbook doc")
    if DOC_REL not in docs_site:
        failures.append("response application playbook is missing from docs site")
    if DOC_REL not in review_docs.REVIEW_DOCS:
        failures.append("response application playbook is missing from review docs")
    if (
        "Sandbox/VM Live POC Runtime Descriptor-Only Response Application Playbook"
        not in review_index
    ):
        failures.append("review-docs index is missing response application playbook")
    if DOC_NAME not in record_doc:
        failures.append("response application record is missing playbook pointer")

    return record._report(not failures, failures, "response_application_playbook_doc")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())

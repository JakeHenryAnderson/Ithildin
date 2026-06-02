"""Generate a local source-review transcript packet skeleton."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "var/review-packets/v0.5/source-review-transcripts"
REQUIRED_PACKET_DOCS = [
    "docs/codex/source-review-runbook-v2.md",
    "docs/codex/source-file-inspection-packet.md",
    "docs/codex/patch-apply-source-review-checklist.md",
    "docs/codex/filesystem-source-review-checklist.md",
    "docs/codex/http-fetch-source-review-checklist.md",
    "docs/codex/signed-evidence-source-review-checklist.md",
    "docs/codex/policy-parity-source-review-checklist.md",
    "docs/codex/mcp-ingress-source-review-checklist.md",
    "docs/codex/review-console-source-review-checklist.md",
    "docs/codex/reviewer-finding-template.md",
    "docs/codex/source-review-closure-matrix.md",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    report = build_report(ROOT, output_dir=Path(args.output_dir))
    if not args.check and report["valid"]:
        write_packet(report, Path(args.output_dir))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(repo_root: Path, *, output_dir: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    docs: list[dict[str, Any]] = []
    failures: list[str] = []
    for doc in REQUIRED_PACKET_DOCS:
        path = repo_root / doc
        if not path.exists():
            failures.append(f"missing transcript packet input: {doc}")
            continue
        content = path.read_bytes()
        docs.append(
            {
                "path": doc,
                "sha256": "sha256:" + hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
            }
        )

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "output_dir": output_dir.as_posix(),
        "output_file": (output_dir / "SOURCE_REVIEW_TRANSCRIPT_PACKET.md").as_posix(),
        "doc_count": len(docs),
        "docs": docs,
        "external_review_closed": False,
        "runtime_behavior_changed": False,
    }


def write_packet(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    packet_path = output_dir / "SOURCE_REVIEW_TRANSCRIPT_PACKET.md"
    packet_path.write_text(_packet_markdown(report), encoding="utf-8")
    (output_dir / "source-review-transcript-doc-hashes.json").write_text(
        json.dumps(report["docs"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _packet_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Source Review Transcript Packet",
        "",
        "This generated packet is a transcript skeleton for external/source reviewers. It does not",
        "close external review, approve capability expansion, or change runtime behavior.",
        "",
        "## Reviewer Instructions",
        "",
        "1. Inspect the source files named in the source-file inspection packet.",
        "2. Use the subsystem checklist for each reviewed area.",
        "3. Record findings with the reviewer finding template.",
        "4. Update the source-review closure matrix only after findings are triaged.",
        "",
        "## Required Input Documents",
        "",
    ]
    for doc in report["docs"]:
        lines.append(f"- `{doc['path']}` ({doc['sha256']}, {doc['bytes']} bytes)")
    lines.extend(
        [
            "",
            "## Transcript Sections",
            "",
            "### Patch Apply",
            "",
            "- Reviewer:",
            "- Date:",
            "- Files/functions inspected:",
            "- Findings:",
            "",
            "### Filesystem",
            "",
            "- Reviewer:",
            "- Date:",
            "- Files/functions inspected:",
            "- Findings:",
            "",
            "### HTTP Fetch",
            "",
            "- Reviewer:",
            "- Date:",
            "- Files/functions inspected:",
            "- Findings:",
            "",
            "### Signed Evidence, Policy, MCP, And Review Console",
            "",
            "- Reviewer:",
            "- Date:",
            "- Files/functions inspected:",
            "- Findings:",
            "",
            "### Release Automation",
            "",
            "- Reviewer:",
            "- Date:",
            "- Files/functions inspected:",
            "- Required evidence inputs: release evidence, redaction scan, artifact hashes, "
            "external response normalization, closure/capability gates, dispatch packets.",
            "- Findings:",
            "",
        ]
    )
    return "\n".join(lines)


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin source-review transcript packet",
        f"valid: {str(report['valid']).lower()}",
        f"doc_count: {report['doc_count']}",
        f"output_file: {report['output_file']}",
        "external_review_closed: false",
        "runtime_behavior_changed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

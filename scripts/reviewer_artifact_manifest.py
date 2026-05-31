"""Generate the reviewer artifact manifest v2."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.review_docs import collect_review_doc_metadata

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "var/review-packets/v0.5/reviewer-artifact-manifest-v2.json"
REQUIRED_COMMANDS = [
    "make release-check",
    "make filesystem-contract-check",
    "make signed-evidence-demo",
    "make signed-evidence-demo-verify",
    "make negative-review-transcripts",
    "make source-review-transcript-packet",
    "make review-packet-bundle",
    "make review-packet-consolidated",
    "make packet-redaction-scan",
    "make docs-site",
]
GENERATED_ARTIFACTS = [
    "var/review-packets/v0.2/latest bundle INDEX.md",
    "var/review-packets/v0.2/latest bundle artifact-hashes.json",
    "var/review-packets/v0.2/GPT-5.5-Pro-consolidated/00_ATTACHMENT_INDEX.md",
    "var/review-packets/v0.2/GPT-5.5-Pro-consolidated/consolidated-attachment-hashes.json",
    "var/review-packets/v0.2/signed-evidence-demo/SIGNED_EVIDENCE_DEMO.md",
    "var/review-packets/v0.2/negative-review-transcripts/NEGATIVE_REVIEW_TRANSCRIPTS.md",
    "var/review-packets/v0.5/source-review-transcripts/SOURCE_REVIEW_TRANSCRIPT_PACKET.md",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    report = build_manifest(ROOT)
    if not args.check and report["valid"]:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report, Path(args.output)))
    return 0 if report["valid"] else 1


def build_manifest(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    missing_commands = [
        command
        for command in REQUIRED_COMMANDS
        if f"{command.removeprefix('make ')}:" not in makefile
    ]
    if missing_commands:
        failures.append(f"missing Make targets: {', '.join(missing_commands)}")

    review_docs = collect_review_doc_metadata(repo_root)
    return {
        "schema_version": "2",
        "valid": not failures,
        "failures": failures,
        "review_candidate_label": (
            "v0.5 review-closure candidate for deciding whether capability expansion "
            "is safe to plan"
        ),
        "runtime_boundary": "v0.1 local-preview",
        "committed_review_doc_count": len(review_docs),
        "committed_review_docs": review_docs,
        "required_commands": REQUIRED_COMMANDS,
        "generated_artifacts": GENERATED_ARTIFACTS,
        "does_not_prove": [
            "external/source review closure",
            "capability expansion approval",
            "production identity",
            "runtime Postgres",
            "remote MCP hosting",
            "new governed tool powers",
        ],
    }


def render_report(report: dict[str, Any], output: Path) -> str:
    lines = [
        "Ithildin reviewer artifact manifest v2",
        f"valid: {str(report['valid']).lower()}",
        f"committed_review_doc_count: {report['committed_review_doc_count']}",
        f"required_command_count: {len(report['required_commands'])}",
        f"generated_artifact_count: {len(report['generated_artifacts'])}",
        f"output: {output.as_posix()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

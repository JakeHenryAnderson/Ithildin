"""Build a 10-attachment-friendly consolidated review packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

DEFAULT_BUNDLE_ROOT = Path("var/review-packets/v0.2")
DEFAULT_OUTPUT_DIR = DEFAULT_BUNDLE_ROOT / "GPT-5.5-Pro-consolidated"
SIGNED_EVIDENCE_DEMO_SUMMARY = (
    DEFAULT_BUNDLE_ROOT / "signed-evidence-demo/SIGNED_EVIDENCE_DEMO.md"
)
NEGATIVE_TRANSCRIPTS_SUMMARY = (
    DEFAULT_BUNDLE_ROOT / "negative-review-transcripts/NEGATIVE_REVIEW_TRANSCRIPTS.md"
)

ATTACHMENT_FILES = [
    "00_ATTACHMENT_INDEX.md",
    "01_START_HERE_AND_REVIEW_PROMPT.md",
    "02_REVIEW_PACKET_AND_RESPONSE.md",
    "03_RELEASE_EVIDENCE_AND_COMMAND_OUTPUTS.md",
    "04_REPRODUCTION_SECURITY_AND_NEGATIVE_RECIPES.md",
    "05_SIGNED_EVIDENCE_DEMO_AND_GUIDES.md",
    "06_OPERATOR_AND_MCP_GUIDES.md",
    "07_PROJECT_README.md",
]

CURRENT_STATUS_BANNER = (
    "**Current status:** v0.6/v0.7 external-review closure work for the v0.1 "
    "local-preview runtime boundary; some generated paths retain historical v0.2 names.\n\n"
)


class ConsolidationError(RuntimeError):
    """Raised when the consolidated review packet cannot be generated."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bundle-dir",
        type=Path,
        help="review bundle directory to consolidate; defaults to latest generated bundle",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="output directory for consolidated attachments",
    )
    args = parser.parse_args()

    try:
        result = build_consolidated_packet(
            repo_root=Path.cwd().resolve(),
            bundle_dir=args.bundle_dir,
            output_dir=args.output_dir,
        )
    except ConsolidationError as exc:
        print(f"review packet consolidation failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built consolidated review packet at {result}")
    return 0


def build_consolidated_packet(
    *,
    repo_root: Path,
    bundle_dir: Path | None,
    output_dir: Path,
) -> Path:
    selected_bundle = bundle_dir or _latest_bundle(repo_root / DEFAULT_BUNDLE_ROOT)
    if not selected_bundle.exists():
        raise ConsolidationError(f"review bundle does not exist: {selected_bundle}")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    attachments = _attachment_contents(repo_root, selected_bundle)
    for filename, content in attachments.items():
        output_dir.joinpath(filename).write_text(content.rstrip() + "\n", encoding="utf-8")

    hashes = _attachment_hashes(output_dir)
    _write_json(output_dir / "consolidated-attachment-hashes.json", hashes)
    return output_dir


def _latest_bundle(bundle_root: Path) -> Path:
    bundles = sorted(
        bundle_root.glob("ithildin-v0.2-review-packet-*"),
        key=lambda path: path.stat().st_mtime,
    )
    if not bundles:
        raise ConsolidationError(f"no review bundles found under {bundle_root}")
    return bundles[-1]


def _attachment_contents(repo_root: Path, bundle_dir: Path) -> dict[str, str]:
    short_commit = bundle_dir.name.removeprefix("ithildin-v0.2-review-packet-")
    negative_transcripts = repo_root / NEGATIVE_TRANSCRIPTS_SUMMARY
    attachments = {
        "01_START_HERE_AND_REVIEW_PROMPT.md": CURRENT_STATUS_BANNER
        + _section(
            "v0.6 GPT 5.5 Pro Handoff Prompt",
            repo_root / "docs/codex/v0.6-gpt-55-pro-handoff-prompt.md",
            repo_root,
        )
        + _section(
            "v0.6 Closure Handoff",
            repo_root / "docs/codex/v0.6-closure-handoff.md",
            repo_root,
        )
        + _section(
            "v0.6 Boundary Charter",
            repo_root / "docs/codex/v0.6-boundary-charter.md",
            repo_root,
        )
        + _section(
            "v0.5 External Review Prompt",
            repo_root / "docs/codex/v0.5-external-review-prompt.md",
            repo_root,
        )
        + _section(
            "v0.3 External Review Prompt",
            repo_root / "docs/codex/v0.3-external-review-prompt.md",
            repo_root,
        )
        + _section(
            "v0.2 External Review Prompt",
            repo_root / "docs/codex/v0.2-external-review-prompt.md",
            repo_root,
        )
        + _section(
            "Reviewer Reproduction Map",
            repo_root / "docs/codex/reviewer-reproduction-map.md",
            repo_root,
        )
        + _section(
            "v0.5 Review Candidate Command",
            repo_root / "docs/codex/v0.5-review-candidate-command.md",
            repo_root,
        ),
        "02_REVIEW_PACKET_AND_RESPONSE.md": _section(
            "v0.6 Closure Handoff",
            repo_root / "docs/codex/v0.6-closure-handoff.md",
            repo_root,
        )
        + _section(
            "v0.6 Internal Review Execution Wave 2",
            repo_root / "docs/codex/v0.6-internal-review-execution-wave-2.md",
            repo_root,
        )
        + _section(
            "v0.6 Milestone Manifest",
            repo_root / "docs/codex/v0.6-milestone-manifest.md",
            repo_root,
        )
        + _section(
            "v0.5 Roadmap From v0.4 Review",
            repo_root / "docs/codex/v0.5-roadmap-from-v0.4-review.md",
            repo_root,
        )
        + _section(
            "v0.5 Milestone Manifest",
            repo_root / "docs/codex/v0.5-milestone-manifest.md",
            repo_root,
        )
        + _section(
            "v0.5 Threat Model Delta",
            repo_root / "docs/codex/v0.5-threat-model-delta.md",
            repo_root,
        )
        + _section(
            "v0.3 Review Packet",
            repo_root / "docs/codex/v0.3-review-packet.md",
            repo_root,
        )
        + _section(
            "v0.3 Boundary Decision",
            repo_root / "docs/codex/v0.3-boundary-decision.md",
            repo_root,
        )
        + _section(
            "v0.2 Review Packet",
            repo_root / "docs/codex/v0.2-review-packet.md",
            repo_root,
        )
        + _section(
            "v0.2 Review Response and RC Cleanup",
            repo_root / "docs/codex/v0.2-review-response-and-rc-cleanup.md",
            repo_root,
        )
        + _section(
            "v0.2 Planning Seed",
            repo_root / "docs/codex/v0.2-planning-seed.md",
            repo_root,
        ),
        "03_RELEASE_EVIDENCE_AND_COMMAND_OUTPUTS.md": _section(
            "Bundle Index",
            bundle_dir / "INDEX.md",
            repo_root,
        )
        + _section("Release Check Transcript", bundle_dir / "release-check.txt", repo_root)
        + _section(
            "Filesystem Contract Check",
            bundle_dir / "filesystem-contract-check.txt",
            repo_root,
        )
        + _section("Release Evidence JSON", bundle_dir / "release-evidence.json", repo_root)
        + _section("Release Packet Markdown", bundle_dir / "release-packet.md", repo_root)
        + _section("Release Packet JSON", bundle_dir / "release-packet.json", repo_root)
        + _section("Review Doc Hashes", bundle_dir / "review-doc-hashes.json", repo_root)
        + _section(
            "Packet Redaction Scan",
            bundle_dir / "packet-redaction-scan.txt",
            repo_root,
        )
        + _section("Artifact Hashes", bundle_dir / "artifact-hashes.json", repo_root)
        + _section("Git Summary", bundle_dir / "git-summary.txt", repo_root),
        "04_REPRODUCTION_SECURITY_AND_NEGATIVE_RECIPES.md": _section(
            "Reviewer Reproduction Map",
            repo_root / "docs/codex/reviewer-reproduction-map.md",
            repo_root,
        )
        + _section(
            "Local Preview Security Test Matrix",
            repo_root / "docs/codex/v0.1-security-test-matrix.md",
            repo_root,
        )
        + _section("Evidence Contracts", repo_root / "docs/codex/evidence-contracts.md", repo_root)
        + _section(
            "Filesystem Executor Contract",
            repo_root / "docs/codex/filesystem-executor-contract.md",
            repo_root,
        )
        + _section(
            "Threat Model and Non-Goals",
            repo_root / "docs/codex/threat-model-and-non-goals.md",
            repo_root,
        )
        + _section(
            "Negative Review Recipes",
            repo_root / "docs/codex/negative-review-recipes.md",
            repo_root,
        )
        + _section(
            "Source Review Closure Matrix",
            repo_root / "docs/codex/source-review-closure-matrix.md",
            repo_root,
        )
        + _section(
            "Accepted Risk Register",
            repo_root / "docs/codex/accepted-risk-register.md",
            repo_root,
        )
        + _section(
            "Capability Decision Report",
            repo_root / "docs/codex/capability-decision-report.md",
            repo_root,
        )
        + _section(
            "No-New-Powers Guardrail",
            repo_root / "docs/codex/no-new-powers-guardrail.md",
            repo_root,
        )
        + _section(
            "Source Review Runbook v2",
            repo_root / "docs/codex/source-review-runbook-v2.md",
            repo_root,
        )
        + _section(
            "Source Review Transcript Packet",
            repo_root / "docs/codex/source-review-transcript-packet.md",
            repo_root,
        )
        + _section(
            "Reviewer Artifact Manifest v2",
            repo_root / "docs/codex/reviewer-artifact-manifest-v2.md",
            repo_root,
        )
        + _section(
            "External Review Response Intake Template v2",
            repo_root / "docs/codex/external-review-response-intake-template-v2.md",
            repo_root,
        )
        + _section(
            "Review Packet Source Pointers",
            repo_root / "docs/codex/review-packet-source-pointers.md",
            repo_root,
        )
        + _section(
            "Internal Source Review Pass 1",
            repo_root / "docs/codex/internal-source-review-pass-1.md",
            repo_root,
        )
        + _section(
            "Internal AI Review Workflow",
            repo_root / "docs/codex/internal-ai-review-workflow.md",
            repo_root,
        )
        + _section(
            "Autonomous Sprint Guardrails",
            repo_root / "docs/codex/autonomous-sprint-guardrails.md",
            repo_root,
        )
        + _section(
            "Reviewer Finding Template",
            repo_root / "docs/codex/reviewer-finding-template.md",
            repo_root,
        )
        + _optional_section("Negative Review Transcripts", negative_transcripts, repo_root),
        "05_SIGNED_EVIDENCE_DEMO_AND_GUIDES.md": _section(
            "Signed Evidence Demo Summary",
            repo_root / SIGNED_EVIDENCE_DEMO_SUMMARY,
            repo_root,
        )
        + _section(
            "Signed Audit Exports",
            repo_root / "docs/codex/signed-audit-exports.md",
            repo_root,
        )
        + _section(
            "Signed Manifest Locks",
            repo_root / "docs/codex/signed-manifest-locks.md",
            repo_root,
        ),
        "06_OPERATOR_AND_MCP_GUIDES.md": _section(
            "Local Preview Release Guide",
            repo_root / "docs/codex/local-preview-release.md",
            repo_root,
        )
        + _section(
            "MCP Client Examples",
            repo_root / "docs/codex/mcp-client-examples.md",
            repo_root,
        )
        + _section(
            "MCP Inspector Recipes",
            repo_root / "docs/codex/mcp-inspector-recipes.md",
            repo_root,
        )
        + _section(
            "Source Verification Notes",
            repo_root / "docs/research/source-verification.md",
            repo_root,
        ),
        "07_PROJECT_README.md": _section("README", repo_root / "README.md", repo_root),
    }
    index = f"""# Ithildin v0.6 Review-Closure Packet: Consolidated Attachments

{CURRENT_STATUS_BANNER.rstrip()}

This folder is the 10-attachment-friendly packet for GPT 5.5 Pro / Very High or a human expert
reviewer. It consolidates the review bundle generated from commit `{short_commit}`.

In practice, v0.6 is an external/source-review execution and closure wave over the same narrow v0.1
local-preview runtime boundary. The generated bundle path still uses the historical `v0.2`
directory because the packet tooling predates later review waves.

Send these files in order:

{chr(10).join(f"- `{name}`" for name in ATTACHMENT_FILES if name != "00_ATTACHMENT_INDEX.md")}

Also include `consolidated-attachment-hashes.json` when possible. It contains SHA-256 hashes for
all eight markdown attachments, including this index.

The source review bundle is `{_display_path(bundle_dir, repo_root)}`. Runtime audit signing and
manifest-lock signing may be unconfigured; the signed-evidence demo is separate non-production
fixture evidence only.

## What This Packet Does Not Prove

This packet proves release evidence and test status for the referenced commit. It does not prove
source correctness, OS isolation, external custody, production identity, runtime compromise
resistance, or production-security readiness.
"""
    return {"00_ATTACHMENT_INDEX.md": index, **attachments}


def _section(title: str, path: Path, repo_root: Path) -> str:
    if not path.exists():
        raise ConsolidationError(f"required consolidated packet source is missing: {path}")
    return (
        "\n\n---\n\n"
        f"# {title}\n\n"
        f"_Source: `{_display_path(path, repo_root)}`_\n\n"
        f"{path.read_text(encoding='utf-8').rstrip()}\n"
    )


def _optional_section(title: str, path: Path, repo_root: Path) -> str:
    if not path.exists():
        return ""
    return _section(title, path, repo_root)


def _display_path(path: Path, repo_root: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _attachment_hashes(output_dir: Path) -> list[dict[str, Any]]:
    metadata: list[dict[str, Any]] = []
    for filename in ATTACHMENT_FILES:
        path = output_dir / filename
        if not path.exists():
            raise ConsolidationError(f"consolidated attachment is missing: {filename}")
        content = path.read_bytes()
        metadata.append(
            {
                "path": filename,
                "sha256": "sha256:" + hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
            }
        )
    return metadata


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())

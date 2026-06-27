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
    "make v06-review-dispatch-packets",
    "make v1-rc-packet",
    "make enterprise-next-review-handoff",
    "make enterprise-review-send-readiness",
    "make enterprise-dual-review-handoff",
    "make enterprise-dual-response-readiness",
    "make enterprise-response-status-board",
    "make sandbox-vm-static-preflight-external-review-bundle",
    "make sandbox-vm-static-preflight-response-kit",
    "make review-packet-bundle",
    "make review-packet-consolidated",
    "make packet-redaction-scan",
    "make docs-site",
]
BASE_GENERATED_ARTIFACTS = [
    "var/review-packets/v0.2/GPT-5.5-Pro-consolidated/00_ATTACHMENT_INDEX.md",
    "var/review-packets/v0.2/GPT-5.5-Pro-consolidated/consolidated-attachment-hashes.json",
    "var/review-packets/v0.2/signed-evidence-demo/SIGNED_EVIDENCE_DEMO.md",
    "var/review-packets/v0.2/negative-review-transcripts/NEGATIVE_REVIEW_TRANSCRIPTS.md",
    "var/review-packets/v0.5/source-review-transcripts/SOURCE_REVIEW_TRANSCRIPT_PACKET.md",
    "var/review-packets/v0.6/dispatch/dispatch-packet-hashes.json",
    "var/review-packets/v0.6/dispatch/release-automation.md",
    "var/review-packets/v1.0/rc/00_V1_RC_PACKET_INDEX.md",
    "var/review-packets/v1.0/rc/07B_ENTERPRISE_DUAL_REVIEW_HANDOFF.md",
    "var/review-packets/v1.0/rc/07C_ENTERPRISE_RESPONSE_STATUS_BOARD.md",
    "var/review-packets/v1.0/rc/v1-rc-artifact-hashes.json",
    "var/review-packets/v3/enterprise-next-review-handoff/NEXT_ENTERPRISE_REVIEW_HANDOFF.md",
    "var/review-packets/v3/enterprise-next-review-handoff/next-enterprise-review-handoff-artifact-hashes.json",
    "var/review-packets/v3/enterprise-dual-review-handoff/ENTERPRISE_DUAL_REVIEW_HANDOFF.md",
    "var/review-packets/v3/enterprise-dual-review-handoff/enterprise-dual-review-handoff-artifact-hashes.json",
    "var/review-packets/v3/sandbox-vm-static-preflight-external-review/00_SANDBOX_VM_STATIC_PREFLIGHT_EXTERNAL_REVIEW_INDEX.md",
    "var/review-packets/v3/sandbox-vm-static-preflight-external-review/sandbox-vm-static-preflight-external-review-artifact-hashes.json",
    "var/review-packets/v3/sandbox-vm-static-preflight-response-kit/00_SANDBOX_VM_STATIC_PREFLIGHT_RESPONSE_KIT_INDEX.md",
    "var/review-packets/v3/sandbox-vm-static-preflight-response-kit/sandbox-vm-static-preflight-response-kit-artifact-hashes.json",
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
    generated_artifacts = _generated_artifacts(repo_root)
    missing_generated_artifacts = [
        artifact for artifact in generated_artifacts if not (repo_root / artifact).exists()
    ]
    if missing_generated_artifacts:
        failures.append(
            "missing generated artifacts: " + ", ".join(sorted(missing_generated_artifacts))
        )
    return {
        "schema_version": "2",
        "valid": not failures,
        "failures": failures,
        "review_candidate_label": (
            "v1.0 local-preview RC plus enterprise review handoff inventory"
        ),
        "runtime_boundary": "v0.1 local-preview",
        "committed_review_doc_count": len(review_docs),
        "committed_review_docs": review_docs,
        "required_commands": REQUIRED_COMMANDS,
        "generated_artifacts": generated_artifacts,
        "missing_generated_artifacts": missing_generated_artifacts,
        "does_not_prove": [
            "external/source review closure",
            "capability expansion approval",
            "production identity",
            "runtime Postgres",
            "remote MCP hosting",
            "new governed tool powers",
        ],
    }


def _generated_artifacts(repo_root: Path) -> list[str]:
    artifacts = list(BASE_GENERATED_ARTIFACTS)
    latest_packet = _latest_v02_review_packet(repo_root)
    if latest_packet is not None:
        rel = latest_packet.relative_to(repo_root).as_posix()
        artifacts.extend(
            [
                f"{rel}/INDEX.md",
                f"{rel}/artifact-hashes.json",
                f"{rel}/release-check.txt",
                f"{rel}/packet-redaction-scan.txt",
            ]
        )
    return artifacts


def _latest_v02_review_packet(repo_root: Path) -> Path | None:
    root = repo_root / "var/review-packets/v0.2"
    if not root.exists():
        return None
    candidates = [
        path for path in root.glob("ithildin-v0.2-review-packet-*") if path.is_dir()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def render_report(report: dict[str, Any], output: Path) -> str:
    lines = [
        "Ithildin reviewer artifact manifest v2",
        f"valid: {str(report['valid']).lower()}",
        f"committed_review_doc_count: {report['committed_review_doc_count']}",
        f"required_command_count: {len(report['required_commands'])}",
        f"generated_artifact_count: {len(report['generated_artifacts'])}",
        f"missing_generated_artifact_count: {len(report['missing_generated_artifacts'])}",
        f"output: {output.as_posix()}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

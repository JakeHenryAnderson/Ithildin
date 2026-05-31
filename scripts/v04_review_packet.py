"""Emit a secret-free v0.4 review-candidate packet summary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import release_packet

PACKET_VERSION = "v0.4-review-candidate"
PACKET_LABEL = "v0.4 review candidate for the v0.1 local-preview runtime boundary"
MILESTONE_PATH = Path("docs/codex/v0.4-milestone-manifest.json")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    marker_status = release_packet._project_marker_status(repo_root)
    missing_markers = [
        marker for marker, present in marker_status.items() if not present
    ]
    if missing_markers:
        print(
            "v0.4 review packet must be run from the Ithildin repo root; "
            f"missing markers: {', '.join(missing_markers)}",
            file=sys.stderr,
        )
        return 1

    packet = build_v04_packet(repo_root, marker_status)
    if args.json:
        json.dump(packet, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(render_markdown(packet))
    return 0


def build_v04_packet(repo_root: Path, marker_status: dict[str, bool]) -> dict[str, Any]:
    packet = release_packet.build_packet(repo_root, marker_status)
    milestone = json.loads((repo_root / MILESTONE_PATH).read_text(encoding="utf-8"))
    packet["packet_version"] = PACKET_VERSION
    packet["review_candidate_label"] = PACKET_LABEL
    packet["v04_milestone"] = {
        "completed_range": milestone["completed_range"],
        "planned_range": milestone["planned_range"],
        "runtime_boundary": milestone["runtime_boundary"],
        "gating_overlay_version": milestone["gating_overlay_version"],
    }
    packet["v04_review_documents"] = [
        "docs/codex/v0.4-boundary-charter.md",
        "docs/codex/v0.4-milestone-manifest.md",
        "docs/codex/v0.4-gating-overlay.md",
        "docs/codex/v0.4-threat-model-refresh.md",
        "docs/codex/review-docs-index.md",
        "docs/codex/source-review-closure-matrix.md",
    ]
    return packet


def render_markdown(packet: dict[str, Any]) -> str:
    lines = [
        "# Ithildin v0.4 Review Candidate Packet",
        "",
        f"- packet version: `{packet['packet_version']}`",
        f"- label: {packet['review_candidate_label']}",
        f"- repo root: `{packet['repo']['repo_root']}`",
        f"- commit: `{packet['git']['commit']}`",
        f"- dirty: `{str(packet['git']['dirty']).lower()}`",
        f"- completed v0.4 tasks: `{packet['v04_milestone']['completed_range']}`",
        f"- planned v0.4 tasks: `{packet['v04_milestone']['planned_range']}`",
        f"- runtime boundary: `{packet['v04_milestone']['runtime_boundary']}`",
        "",
        "## Required Local Gate",
        "",
        "- run `make release-check` and `make review-candidate` before external handoff;",
        "- run `make review-packet-diff-gate OLD=<prior> NEW=<current>` at each wave boundary;",
        "- this packet is handoff evidence, not external review closure.",
        "",
        "## Current Evidence Snapshot",
        "",
        f"- tools: `{packet['tools']['count']}`",
        f"- manifest lock current: `{str(packet['manifest_lock']['current']).lower()}`",
        f"- policy engine: `{packet['policy']['engine']}`",
        f"- policy hash: `{packet['policy']['policy_hash']}`",
        f"- storage backend: `{packet['storage']['runtime_backend']}`",
        f"- telemetry enabled: `{str(packet['telemetry']['enabled']).lower()}`",
        f"- production ready: `{str(packet['security']['production_ready']).lower()}`",
        "",
        "## v0.4 Review Documents",
        "",
        *[f"- [{doc}]({doc})" for doc in packet["v04_review_documents"]],
        "",
        "## Deferred Boundaries",
        "",
        *[f"- {boundary}" for boundary in packet["deferred_boundaries"]],
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

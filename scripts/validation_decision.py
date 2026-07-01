"""Summarize the current validation decision for developer/operator use."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import release_check_impact, validation_plan  # noqa: E402

GATE_GUIDANCE = {
    "make dev-check": {
        "tier": "dirty_file_aware_default",
        "use_for": "normal development loop when release or handoff evidence is not being claimed",
        "release_proof": False,
    },
    "make quick-check": {
        "tier": "fast",
        "use_for": "small docs/process/script wiring changes",
        "release_proof": False,
    },
    "make docs-check": {
        "tier": "docs_fast",
        "use_for": "pure docs/README/AGENTS edits with no code, scripts, config, or tests changed",
        "release_proof": False,
    },
    "make readiness-check": {
        "tier": "medium",
        "use_for": "docs-site, review-doc, Make target, and release-readiness wiring changes",
        "release_proof": False,
    },
    "make runtime-check": {
        "tier": "focused_runtime",
        "use_for": "backend/API/governed-tool/security/policy runtime iteration",
        "release_proof": False,
    },
    "make test-fast": {
        "tier": "broad_python_non_packet",
        "use_for": "broad Python confidence without generated-packet test paths",
        "release_proof": False,
    },
    "make capability-check": {
        "tier": "bounded_capability_development",
        "use_for": (
            "read-only capability implementation before full release or "
            "source-review handoff proof"
        ),
        "release_proof": False,
    },
    "make evidence-check": {
        "tier": "evidence_review_state",
        "use_for": (
            "release evidence, findings, review-run manifest, packet recursion, "
            "and docs wiring changes"
        ),
        "release_proof": False,
    },
    "make release-check": {
        "tier": "full_release",
        "use_for": (
            "meaningful checkpoint, release proof, source-review handoff, and runtime changes "
            "before handoff"
        ),
        "release_proof": True,
    },
    "make review-candidate": {
        "tier": "full_handoff",
        "use_for": "reviewer/operator packet generation",
        "release_proof": True,
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", help="changed files to classify")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()

    report = build_report(args.files)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(files: list[str] | None = None) -> dict[str, Any]:
    changed_files = files or validation_plan.changed_files(ROOT)
    plan = validation_plan.build_report(changed_files)
    impact = release_check_impact.build_report(ROOT, files=changed_files)
    dirty = bool(changed_files)
    next_commands = plan["recommended_commands"]
    deferred = plan["deferred_handoff_commands"]
    return {
        "schema_version": "1",
        "valid": impact["valid"],
        "failures": impact["failures"],
        "repo_root": str(ROOT),
        "git_commit": _git(["rev-parse", "HEAD"]),
        "git_dirty": dirty,
        "file_count": plan["file_count"],
        "categories": plan["categories"],
        "next_development_commands": next_commands,
        "deferred_handoff_commands": deferred,
        "release_slice_categories": impact["slice_categories"],
        "release_slice_commands": impact["slice_commands"],
        "release_or_handoff_required": bool(deferred),
        "recommended_mode": _recommended_mode(plan),
        "gate_guidance": {
            command: GATE_GUIDANCE[command]
            for command in next_commands + deferred
            if command in GATE_GUIDANCE
        },
        "notes": _notes(plan),
        "files": plan["files"],
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin validation decision",
        f"valid: {str(report['valid']).lower()}",
        f"git_commit: {report['git_commit']}",
        f"git_dirty: {str(report['git_dirty']).lower()}",
        f"file_count: {report['file_count']}",
        "categories: " + (", ".join(report["categories"]) or "none"),
        f"recommended_mode: {report['recommended_mode']}",
        f"release_or_handoff_required: {str(report['release_or_handoff_required']).lower()}",
        "next_development_commands:",
    ]
    lines.extend(f"- {command}" for command in report["next_development_commands"])
    if report["deferred_handoff_commands"]:
        lines.append("deferred_handoff_commands:")
        lines.extend(f"- {command}" for command in report["deferred_handoff_commands"])
    if report["release_slice_categories"]:
        lines.append("release_slice_categories:")
        lines.extend(f"- {category}" for category in report["release_slice_categories"])
    if report["release_slice_commands"]:
        lines.append("release_slice_commands:")
        lines.extend(f"- {command}" for command in report["release_slice_commands"])
    lines.append("notes:")
    lines.extend(f"- {note}" for note in report["notes"])
    if report["files"]:
        lines.append("files:")
        lines.extend(f"- {path}" for path in report["files"])
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _recommended_mode(plan: dict[str, Any]) -> str:
    if plan["deferred_handoff_commands"]:
        return "develop_then_handoff_gate"
    if plan["categories"]:
        return "development_gate_only"
    return "clean_tree_quick_gate"


def _notes(plan: dict[str, Any]) -> list[str]:
    notes = list(plan["notes"])
    if plan["deferred_handoff_commands"]:
        notes.append(
            "Run development commands first; run deferred handoff commands before external "
            "review, release proof, or major checkpoint claims."
        )
    else:
        notes.append("No slow release/review gate is recommended for the current dirty-file set.")
    notes.append("Release-check slice suggestions are focused development evidence only.")
    return notes


def _git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


if __name__ == "__main__":
    raise SystemExit(main())

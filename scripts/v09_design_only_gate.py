"""Validate that v0.9 work stays design-only."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import no_new_powers_guardrail, v08_capability_design_gate

ROOT = Path(__file__).resolve().parents[1]
CHARTER_DOC = ROOT / "docs/codex/v0.9-design-only-boundary-charter.md"
V09_BASELINE_COMMIT = "de32893"
FORBIDDEN_SURFACE_PREFIXES = (
    "apps/api/",
    "apps/mcp-server/",
    "ithildin_api/",
    "ithildin_mcp_server/",
    "policies/",
    "tool-manifests/",
)
FORBIDDEN_SURFACE_FILES = {"tool-manifests.lock.json"}
REQUIRED_PHRASES = [
    "v0.9 starts design-only capability planning",
    "must not implement new runtime behavior",
    "tool manifests",
    "executor code",
    "API or MCP runtime behavior",
    "policy rules or approval behavior",
    "git.show.commit_metadata",
    "proposal only",
    "make v09-design-only-gate",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = build_report(ROOT)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    charter_path = repo_root / CHARTER_DOC.relative_to(ROOT)
    if not charter_path.exists():
        return _report(["v0.9 design-only boundary charter is missing"], {})

    charter = charter_path.read_text(encoding="utf-8")
    for phrase in REQUIRED_PHRASES:
        if phrase not in charter:
            failures.append(f"v0.9 charter is missing phrase: {phrase}")

    v08_gate = v08_capability_design_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    failures.extend(f"v0.8 gate: {failure}" for failure in v08_gate["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])
    failures.extend(_forbidden_design_only_surface_changes(repo_root))

    return _report(
        failures,
        {
            "v09_baseline_commit": V09_BASELINE_COMMIT,
            "design_only_baseline_commit": V09_BASELINE_COMMIT,
            "baseline_purpose": (
                "commit before v0.9 design-only planning began; reviewed packet commits are "
                "expected to be later clean commits"
            ),
            "tool_count": no_new_powers.get("tool_count"),
            "capability_design_only": v08_gate.get("capability_design_only"),
            "capability_implementation": v08_gate.get("capability_implementation"),
        },
    )


def _forbidden_design_only_surface_changes(repo_root: Path) -> list[str]:
    if not (repo_root / ".git").exists():
        return []
    baseline_check = subprocess.run(
        ["git", "rev-parse", "--verify", f"{V09_BASELINE_COMMIT}^{{commit}}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if baseline_check.returncode != 0:
        return [f"could not verify v0.9 design-only baseline commit: {V09_BASELINE_COMMIT}"]
    committed = subprocess.run(
        ["git", "diff", "--name-only", V09_BASELINE_COMMIT, "HEAD"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if committed.returncode != 0:
        return ["could not inspect committed v0.9 design-only diff"]
    working = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if working.returncode != 0:
        return ["could not inspect working-tree v0.9 design-only diff"]
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if untracked.returncode != 0:
        return ["could not inspect untracked v0.9 design-only files"]

    changed = sorted(
        {
            line.strip()
            for output in (committed.stdout, working.stdout, untracked.stdout)
            for line in output.splitlines()
            if line.strip()
        }
    )
    forbidden = [
        path
        for path in changed
        if path in FORBIDDEN_SURFACE_FILES or path.startswith(FORBIDDEN_SURFACE_PREFIXES)
    ]
    return [
        "v0.9 design-only work changed runtime/tool surfaces since baseline "
        f"{V09_BASELINE_COMMIT}: "
        + ", ".join(forbidden)
    ] if forbidden else []


def _report(failures: list[str], evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "v09_scope": "design_only",
        "capability_implementation": "no_go",
        "new_governed_tool_powers": "no_go",
        "evidence": evidence,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin v0.9 design-only gate",
        f"valid: {str(report['valid']).lower()}",
        "v09_scope: design_only",
        "capability_implementation: no_go",
        "new_governed_tool_powers: no_go",
        f"v09_baseline_commit: {report['evidence'].get('v09_baseline_commit', 'unknown')}",
        "baseline_purpose: design-only diff comparison, not the reviewed packet commit",
        f"tool_count: {report['evidence'].get('tool_count', 'unknown')}",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

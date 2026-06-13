"""Generate and validate a narrow Low Codex implementer delegation packet."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = Path("var/agent-delegation/low-implementer-packet")
PILOT_DOC = Path("docs/codex/low-implementer-delegation-pilot.md")
PACKET_FILES = ("LOW_IMPLEMENTER_TASK.md", "MANAGER_REVIEW_CHECKLIST.md", "packet-summary.json")

REQUIRED_DOC_PHRASES = [
    "Low Codex implementer",
    "Gemma/local-model output is optional advisory input only",
    "Low Codex implementers are the preferred mechanical delegation path",
    "productivity experiment, not permission to delegate safety judgment",
    "They must not edit manifests, executors, policy semantics, approval logic, audit logic",
    "does not call a local model",
    "make low-implementer-delegation-packet",
    "make low-implementer-delegation-check",
]

REQUIRED_PACKET_PHRASES = [
    "Task: mechanical documentation command-list scan",
    "Allowed files",
    "Forbidden files",
    "Do not edit runtime source",
    "Return only",
    "Main manager review required",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    if not args.check:
        build_packet(ROOT, args.output_dir)
    report = build_report(ROOT, args.output_dir)
    if args.json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_packet(repo_root: Path, output_dir: Path) -> Path:
    path = repo_root / output_dir
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True).strip()
    dirty = bool(
        subprocess.check_output(["git", "status", "--short"], cwd=repo_root, text=True).strip()
    )
    path.joinpath("LOW_IMPLEMENTER_TASK.md").write_text(
        _task_prompt(commit, dirty),
        encoding="utf-8",
    )
    path.joinpath("MANAGER_REVIEW_CHECKLIST.md").write_text(
        _manager_checklist(),
        encoding="utf-8",
    )
    path.joinpath("packet-summary.json").write_text(
        json.dumps(
            {
                "schema_version": "1",
                "packet_type": "ithildin.low_implementer_delegation_pilot",
                "commit": commit,
                "dirty": dirty,
                "runtime_changes_allowed": False,
                "new_tool_powers_allowed": False,
                "model_call_performed": False,
                "tool_count": 19,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def build_report(repo_root: Path, output_dir: Path) -> dict[str, Any]:
    failures: list[str] = []
    pilot_doc = _read_required(repo_root / PILOT_DOC, failures)
    agents = _read_required(repo_root / "AGENTS.md", failures)
    readme = _read_required(repo_root / "README.md", failures)
    makefile = _read_required(repo_root / "Makefile", failures)
    review_docs = _read_required(repo_root / "scripts/review_docs.py", failures)
    docs_site = _read_required(repo_root / "scripts/build_docs_site.py", failures)
    packet_dir = repo_root / output_dir

    failures.extend(_missing_phrases(PILOT_DOC.as_posix(), pilot_doc, REQUIRED_DOC_PHRASES))
    if "Low Codex implementers are the preferred mechanical delegation path" not in agents:
        failures.append("AGENTS.md no longer defines Low Codex as preferred mechanical path")
    if "Gemma/local-model output is advisory only" not in agents:
        failures.append("AGENTS.md no longer keeps Gemma/local-model output advisory")
    if "low-implementer-delegation-packet:" not in makefile:
        failures.append("Makefile is missing low-implementer-delegation-packet target")
    if "low-implementer-delegation-check:" not in makefile:
        failures.append("Makefile is missing low-implementer-delegation-check target")
    if "make low-implementer-delegation-packet" not in readme:
        failures.append("README.md does not document low-implementer-delegation-packet")
    if PILOT_DOC.as_posix() not in review_docs:
        failures.append("pilot doc is missing from review docs")
    if PILOT_DOC.as_posix() not in docs_site:
        failures.append("pilot doc is missing from docs-site inputs")

    missing_packet_files = [name for name in PACKET_FILES if not packet_dir.joinpath(name).exists()]
    if missing_packet_files:
        failures.append(f"delegation packet missing files: {', '.join(missing_packet_files)}")
    else:
        task = packet_dir.joinpath("LOW_IMPLEMENTER_TASK.md").read_text(encoding="utf-8")
        failures.extend(
            _missing_phrases(
                f"{output_dir.as_posix()}/LOW_IMPLEMENTER_TASK.md",
                task,
                REQUIRED_PACKET_PHRASES,
            )
        )
        summary = json.loads(packet_dir.joinpath("packet-summary.json").read_text(encoding="utf-8"))
        if summary.get("runtime_changes_allowed") is not False:
            failures.append("packet summary must keep runtime_changes_allowed=false")
        if summary.get("new_tool_powers_allowed") is not False:
            failures.append("packet summary must keep new_tool_powers_allowed=false")
        if summary.get("model_call_performed") is not False:
            failures.append("packet summary must record model_call_performed=false")
        if summary.get("tool_count") != 18:
            failures.append("packet summary tool_count drifted from 19")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "pilot_doc": PILOT_DOC.as_posix(),
        "output_dir": output_dir.as_posix(),
        "tool_count": 19,
        "runtime_changes_allowed": False,
        "new_tool_powers_allowed": False,
        "model_call_performed": False,
        "low_codex_preferred_mechanical_path": True,
        "gemma_output_advisory_only": True,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin low-implementer delegation pilot",
        f"valid: {str(report['valid']).lower()}",
        f"pilot_doc: {report['pilot_doc']}",
        f"output_dir: {report['output_dir']}",
        f"tool_count: {report['tool_count']}",
        "runtime_changes_allowed: false",
        "new_tool_powers_allowed: false",
        "model_call_performed: false",
        "low_codex_preferred_mechanical_path: true",
        "gemma_output_advisory_only: true",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _task_prompt(commit: str, dirty: bool) -> str:
    return f"""# Low Implementer Task

Task: mechanical documentation command-list scan.

You are acting as a Low Codex implementer for Ithildin. Main manager review required.

Gemma/local-model suggestions are optional advisory input only and are not the default path for this
task.

Reviewed commit: `{commit}`
Dirty tree at packet generation: `{str(dirty).lower()}`

## Allowed files

- `README.md`
- `docs/codex/reviewer-reproduction-map.md`
- `docs/codex/review-docs-index.md`

## Forbidden files

- Do not edit runtime source.
- Do not edit `tool-manifests/`, `policies/`, approval code, audit code, executor code, MCP/API
  behavior, storage/auth code, or UI runtime behavior.
- Do not add new claims about sandboxing, compliance, production security, public-preview readiness,
  or new governed tool powers.

## Assignment

Inspect the allowed files for stale command-list references, missing links to existing docs, or
obvious inconsistent wording. Return candidate mechanical updates only.

## Return only

- Short summary.
- File/section references.
- Candidate exact text changes.
- Any uncertainty.

Do not apply changes unless the main manager explicitly asks.
"""


def _manager_checklist() -> str:
    return """# Manager Review Checklist

- Confirm the low implementer stayed within allowed files.
- Confirm suggestions are mechanical and do not change safety/product claims.
- Confirm no runtime, manifest, policy, approval, audit, MCP/API, storage/auth, or UI runtime
  behavior is changed.
- Apply only the useful parts manually or via reviewed patch.
- Run `make low-implementer-delegation-check`.
- Run focused docs/release tests before committing.
"""


def _read_required(path: Path, failures: list[str]) -> str:
    if not path.exists():
        failures.append(f"{path.relative_to(ROOT).as_posix()} is missing")
        return ""
    return path.read_text(encoding="utf-8")


def _missing_phrases(path: str, text: str, phrases: list[str]) -> list[str]:
    return [f"{path} missing required phrase: {phrase}" for phrase in phrases if phrase not in text]


if __name__ == "__main__":
    raise SystemExit(main())

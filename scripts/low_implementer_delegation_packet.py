"""Generate and validate a narrow Low Codex implementer delegation packet."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = Path("var/agent-delegation/low-implementer-packet")
PILOT_DOC = Path("docs/codex/low-implementer-delegation-pilot.md")
CATALOG_DOC = Path("docs/codex/low-implementer-ticket-catalog.md")
TRIAL_LOG_DOC = Path("docs/codex/low-implementer-trial-log.md")
SCORECARD_DOC = Path("docs/codex/low-implementer-delegation-scorecard.md")
DEFAULT_TICKET = "docs-link-scan"
PACKET_FILES = (
    "LOW_IMPLEMENTER_TASK.md",
    "MANAGER_REVIEW_CHECKLIST.md",
    "MANAGER_SCORECARD.md",
    "packet-summary.json",
)

TICKET_TYPES: dict[str, dict[str, object]] = {
    "docs-link-scan": {
        "title": "mechanical documentation link/reference scan",
        "allowed_files": [
            "README.md",
            "docs/codex/reviewer-reproduction-map.md",
            "docs/codex/review-docs-index.md",
        ],
        "focused_check": "make low-implementer-delegation-check",
        "assignment": (
            "Inspect the allowed files for stale command-list references, missing links "
            "to existing docs, or obvious inconsistent wording. Return candidate "
            "mechanical updates only."
        ),
    },
    "stale-wording-scan": {
        "title": "stale tool-count/current-candidate wording scan",
        "allowed_files": [
            "README.md",
            "docs/codex/v3-readiness-debt-register.md",
            "docs/codex/next-capability-readiness.md",
            "docs/codex/read-only-project-intelligence.md",
        ],
        "focused_check": "uv run pytest tests/test_release_readiness.py tests/test_docs_site.py -q",
        "assignment": (
            "Inspect the allowed files for stale tool counts, stale next-candidate wording, or "
            "phrasing that conflicts with the current read-only capability inventory. Return "
            "candidate mechanical updates only."
        ),
    },
    "make-target-wiring": {
        "title": "Make target/docs wiring check",
        "allowed_files": [
            "README.md",
            "Makefile",
            "tests/test_release_readiness.py",
        ],
        "focused_check": (
            "uv run pytest "
            "tests/test_release_readiness.py::test_low_implementer_delegation_pilot_is_wired -q"
        ),
        "assignment": (
            "Inspect command documentation and release-readiness assertions for existing "
            "Make target wiring drift. Return candidate mechanical updates only."
        ),
    },
    "packet-inventory": {
        "title": "generated packet inventory check",
        "allowed_files": [
            "README.md",
            "docs/codex/reviewer-reproduction-map.md",
            "docs/codex/review-docs-index.md",
        ],
        "focused_check": "make low-implementer-delegation-check",
        "assignment": (
            "Inspect generated-packet references in the allowed files for missing or "
            "stale artifact inventory wording. Return candidate mechanical updates only."
        ),
    },
}

REQUIRED_DOC_PHRASES = [
    "Low Codex implementer",
    "Gemma/local-model output is optional advisory input only",
    "mechanical delegation path",
    "gpt-5.4-mini",
    "used one at a time and report-first",
    "Direct file edits by Low Codex implementers remain disabled",
    "productivity experiment, not permission to delegate safety judgment",
    "They must not edit manifests, executors, policy semantics, approval logic, audit logic",
    "does not call a local model",
    "make low-implementer-delegation-packet",
    "make low-implementer-delegation-check",
]

REQUIRED_CATALOG_PHRASES = [
    "Low-Implementer Ticket Catalog",
    "gpt-5.4-mini",
    "Use one Low Codex implementer at a time by default",
    "suggestions only",
    "several clean read-only trials",
    "docs-link-scan",
    "stale-wording-scan",
    "make-target-wiring",
    "packet-inventory",
    "Repetitive release-readiness assertion suggestions",
    "not permission to edit runtime behavior",
    "manager scorecard",
]

REQUIRED_TRIAL_LOG_PHRASES = [
    "Low-Implementer Trial Log",
    "gpt-5.4-mini",
    "report-first",
    "one at a time",
    "Trial 1: docs-link-scan",
    "Trial 2: stale-wording-scan",
    "Trial 3: make-target-wiring",
    "Trial 4: packet-inventory",
    "accepted suggestions",
    "rejected suggestions",
    "boundary drift observed",
    "manager cleanup required",
    "recommendation",
]

REQUIRED_SCORECARD_PHRASES = [
    "Low-Implementer Delegation Scorecard",
    "total trials",
    "accepted suggestions",
    "rejected suggestions",
    "boundary drift count",
    "cleanup trend",
    "current recommendation",
    "direct low-worker patching remains disabled",
]

REQUIRED_PACKET_PHRASES = [
    "Task:",
    "Ticket type:",
    "Allowed files",
    "Forbidden files",
    "Do not edit runtime source",
    "Focused check",
    "Return only",
    "Main manager review required",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--ticket", choices=sorted(TICKET_TYPES), default=DEFAULT_TICKET)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    if not args.check:
        build_packet(ROOT, args.output_dir, ticket=args.ticket)
    report = build_report(ROOT, args.output_dir)
    if args.json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_report(report))
    return 0 if report["valid"] else 1


def build_packet(repo_root: Path, output_dir: Path, ticket: str = DEFAULT_TICKET) -> Path:
    if ticket not in TICKET_TYPES:
        raise ValueError(f"unknown low-implementer ticket: {ticket}")
    path = repo_root / output_dir
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True).strip()
    dirty = bool(
        subprocess.check_output(["git", "status", "--short"], cwd=repo_root, text=True).strip()
    )
    path.joinpath("LOW_IMPLEMENTER_TASK.md").write_text(
        _task_prompt(commit, dirty, ticket),
        encoding="utf-8",
    )
    path.joinpath("MANAGER_REVIEW_CHECKLIST.md").write_text(
        _manager_checklist(),
        encoding="utf-8",
    )
    path.joinpath("MANAGER_SCORECARD.md").write_text(
        _manager_scorecard(ticket),
        encoding="utf-8",
    )
    path.joinpath("packet-summary.json").write_text(
        json.dumps(
            {
                "schema_version": "1",
                "packet_type": "ithildin.low_implementer_delegation_pilot",
                "ticket": ticket,
                "commit": commit,
                "dirty": dirty,
                "runtime_changes_allowed": False,
                "new_tool_powers_allowed": False,
                "model_call_performed": False,
                "tool_count": 20,
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
    catalog_doc = _read_required(repo_root / CATALOG_DOC, failures)
    trial_log_doc = _read_required(repo_root / TRIAL_LOG_DOC, failures)
    scorecard_doc = _read_required(repo_root / SCORECARD_DOC, failures)
    agents = _read_required(repo_root / "AGENTS.md", failures)
    readme = _read_required(repo_root / "README.md", failures)
    makefile = _read_required(repo_root / "Makefile", failures)
    review_docs = _read_required(repo_root / "scripts/review_docs.py", failures)
    docs_site = _read_required(repo_root / "scripts/build_docs_site.py", failures)
    packet_dir = repo_root / output_dir

    failures.extend(_missing_phrases(PILOT_DOC.as_posix(), pilot_doc, REQUIRED_DOC_PHRASES))
    failures.extend(_missing_phrases(CATALOG_DOC.as_posix(), catalog_doc, REQUIRED_CATALOG_PHRASES))
    failures.extend(
        _missing_phrases(TRIAL_LOG_DOC.as_posix(), trial_log_doc, REQUIRED_TRIAL_LOG_PHRASES)
    )
    failures.extend(
        _missing_phrases(SCORECARD_DOC.as_posix(), scorecard_doc, REQUIRED_SCORECARD_PHRASES)
    )
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
    if CATALOG_DOC.as_posix() not in review_docs:
        failures.append("ticket catalog doc is missing from review docs")
    if TRIAL_LOG_DOC.as_posix() not in review_docs:
        failures.append("trial log doc is missing from review docs")
    if SCORECARD_DOC.as_posix() not in review_docs:
        failures.append("delegation scorecard doc is missing from review docs")
    if PILOT_DOC.as_posix() not in docs_site:
        failures.append("pilot doc is missing from docs-site inputs")
    if CATALOG_DOC.as_posix() not in docs_site:
        failures.append("ticket catalog doc is missing from docs-site inputs")
    if TRIAL_LOG_DOC.as_posix() not in docs_site:
        failures.append("trial log doc is missing from docs-site inputs")
    if SCORECARD_DOC.as_posix() not in docs_site:
        failures.append("delegation scorecard doc is missing from docs-site inputs")

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
        scorecard = packet_dir.joinpath("MANAGER_SCORECARD.md").read_text(encoding="utf-8")
        failures.extend(
            _missing_phrases(
                f"{output_dir.as_posix()}/MANAGER_SCORECARD.md",
                scorecard,
                [
                    "useful_suggestions_count",
                    "rejected_suggestions_count",
                    "boundary_drift_observed",
                    "manager_cleanup_required",
                    "delegate_again",
                ],
            )
        )
        summary = json.loads(packet_dir.joinpath("packet-summary.json").read_text(encoding="utf-8"))
        if summary.get("ticket") not in TICKET_TYPES:
            failures.append("packet summary ticket is missing or unknown")
        if summary.get("runtime_changes_allowed") is not False:
            failures.append("packet summary must keep runtime_changes_allowed=false")
        if summary.get("new_tool_powers_allowed") is not False:
            failures.append("packet summary must keep new_tool_powers_allowed=false")
        if summary.get("model_call_performed") is not False:
            failures.append("packet summary must record model_call_performed=false")
        if summary.get("tool_count") != 20:
            failures.append("packet summary tool_count drifted from 20")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "pilot_doc": PILOT_DOC.as_posix(),
        "catalog_doc": CATALOG_DOC.as_posix(),
        "trial_log_doc": TRIAL_LOG_DOC.as_posix(),
        "scorecard_doc": SCORECARD_DOC.as_posix(),
        "output_dir": output_dir.as_posix(),
        "ticket_types": sorted(TICKET_TYPES),
        "tool_count": 20,
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
        f"catalog_doc: {report['catalog_doc']}",
        f"trial_log_doc: {report['trial_log_doc']}",
        f"scorecard_doc: {report['scorecard_doc']}",
        f"output_dir: {report['output_dir']}",
        "ticket_types: " + ", ".join(report["ticket_types"]),
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


def _task_prompt(commit: str, dirty: bool, ticket: str) -> str:
    ticket_config = TICKET_TYPES[ticket]
    title = str(ticket_config["title"])
    allowed_file_paths = cast(list[str], ticket_config["allowed_files"])
    allowed_files = "\n".join(f"- `{path}`" for path in allowed_file_paths)
    assignment = str(ticket_config["assignment"])
    focused_check = str(ticket_config["focused_check"])
    return f"""# Low Implementer Task

Task: {title}.

Ticket type: `{ticket}`

You are acting as a Low Codex implementer for Ithildin. Main manager review required.

Gemma/local-model suggestions are optional advisory input only and are not the default path for this
task.

Reviewed commit: `{commit}`
Dirty tree at packet generation: `{str(dirty).lower()}`

## Allowed files

{allowed_files}

## Forbidden files

- Do not edit runtime source.
- Do not edit `tool-manifests/`, `policies/`, approval code, audit code, executor code, MCP/API
  behavior, storage/auth code, or UI runtime behavior.
- Do not add new claims about sandboxing, compliance, production security, public-preview readiness,
  or new governed tool powers.

## Assignment

{assignment}

## Focused check

`{focused_check}`

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


def _manager_scorecard(ticket: str) -> str:
    return f"""# Manager Scorecard

Ticket type: `{ticket}`

Record this after reviewing low-implementer output. This scorecard is a productivity note, not
release evidence and not a safety approval.

```yaml
useful_suggestions_count:
rejected_suggestions_count:
boundary_drift_observed: false
manager_cleanup_required: none
delegate_again: undecided
notes:
```

Reject the output if it changes safety/product claims, broadens scope, touches forbidden files, or
tries to decide whether a capability is safe.
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

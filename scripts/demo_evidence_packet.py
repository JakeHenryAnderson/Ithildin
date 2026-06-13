"""Build a focused local demo evidence closure packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    demo_flow_result_check,
    demo_observed_summary,
    demo_readiness_summary,
    demo_reset_guide,
    demo_state_report,
)

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/demo-evidence")
HASH_MANIFEST = "demo-evidence-artifact-hashes.json"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]


class DemoEvidencePacketError(RuntimeError):
    """Raised when the demo evidence packet cannot be built."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--skip-probes", action="store_true")
    args = parser.parse_args()
    try:
        output_dir = build_packet(
            repo_root=Path.cwd().resolve(),
            output_dir=args.output_dir,
            allow_dirty=args.allow_dirty,
            probe_endpoints=not args.skip_probes,
        )
    except DemoEvidencePacketError as exc:
        print(f"demo evidence packet failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built demo evidence packet at {output_dir}")
    return 0


def build_packet(
    *,
    repo_root: Path,
    output_dir: Path,
    allow_dirty: bool = False,
    probe_endpoints: bool = True,
) -> Path:
    _require_project_root(repo_root)
    commit = _git(repo_root, ["rev-parse", "HEAD"])
    dirty = bool(_git(repo_root, ["status", "--short"]))
    if dirty and not allow_dirty:
        raise DemoEvidencePacketError("working tree is dirty; commit before demo evidence handoff")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    readiness = demo_readiness_summary.build_summary(
        repo_root=repo_root,
        output=output_dir / "DEMO_READINESS_SUMMARY.md",
        probe_endpoints=probe_endpoints,
    )
    state = demo_state_report.build_report(
        repo_root=repo_root,
        output=output_dir / "DEMO_STATE_REPORT.md",
        probe_endpoints=probe_endpoints,
    )
    reset = demo_reset_guide.build_guide(
        repo_root=repo_root,
        output=output_dir / "DEMO_RESET_GUIDE.md",
    )
    result_check = demo_flow_result_check.build_report(
        repo_root / demo_flow_result_check.DEFAULT_RESULT
    )
    _write_json(output_dir / "DEMO_FLOW_RESULT_CHECK.json", result_check)
    observed = demo_observed_summary.build_summary(
        result=repo_root / demo_observed_summary.DEFAULT_RESULT,
        run_export=repo_root / demo_observed_summary.DEFAULT_RUN_EXPORT,
        output=output_dir / "DEMO_OBSERVED_SUMMARY.md",
    )

    context = {
        "commit": commit,
        "dirty": dirty,
        "readiness": readiness,
        "state": state,
        "reset": reset,
        "result_check": result_check,
        "observed": observed,
        "probe_endpoints": probe_endpoints,
    }
    files = {
        "00_DEMO_EVIDENCE_INDEX.md": _index(context),
        "01_DEMO_EVIDENCE_REVIEW_PROMPT.md": _prompt(context),
        "02_DEMO_COMMAND_SEQUENCE.md": _commands(),
        "03_DEMO_RESULT_CHECK.md": _result_check_markdown(result_check),
        "04_DEMO_ARTIFACT_POINTERS.md": _artifact_pointers(repo_root),
    }
    for relative, content in files.items():
        (output_dir / relative).write_text(content.rstrip() + "\n", encoding="utf-8")
    _write_json(output_dir / HASH_MANIFEST, _hashes(output_dir))
    return output_dir


def _index(context: dict[str, Any]) -> str:
    result_check = context["result_check"]
    return f"""# Demo Evidence Closure Packet

This packet closes the loop between the local workbench demo commands and the evidence an operator
or reviewer should inspect after the optional mediated flow.

## Status

- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Endpoint probes executed: `{str(context["probe_endpoints"]).lower()}`.
- tool count remains `20`.
- Demo flow result status: `{result_check["status"]}`.
- Demo flow result present: `{str(result_check["result_present"]).lower()}`.

## Artifacts

1. `00_DEMO_EVIDENCE_INDEX.md`
2. `01_DEMO_EVIDENCE_REVIEW_PROMPT.md`
3. `02_DEMO_COMMAND_SEQUENCE.md`
4. `03_DEMO_RESULT_CHECK.md`
5. `04_DEMO_ARTIFACT_POINTERS.md`
6. `DEMO_READINESS_SUMMARY.md`
7. `DEMO_STATE_REPORT.md`
8. `DEMO_RESET_GUIDE.md`
9. `DEMO_FLOW_RESULT_CHECK.json`
10. `DEMO_OBSERVED_SUMMARY.md`
11. `demo-evidence-artifact-hashes.json`

## Boundary

This packet does not start services, call governed tools, approve actions, repair diagnostics,
delete evidence, orchestrate sandboxes, export to SIEM, add run controls, or add governed tool
powers. It is local demo evidence packaging only.
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# Demo Evidence Closure Review Prompt

You are reviewing Ithildin's local demo evidence closure packet. Treat this as an operator/reviewer
handoff packet, not production security approval.

Reviewed commit: `{context["commit"]}`
Area: `demo-evidence`
Finding namespace: `EXT-DEMO-###`

Please review whether the packet makes it clear how to:

- run the local demo sequence;
- inspect ready/missing/optional/deferred status;
- inspect `DEMO_FLOW_RESULT.md` when the optional mediated flow has run;
- recover safely when the flow is incomplete;
- refresh workbench packets after a demo;
- avoid overclaiming sandboxing, SIEM custody, compliance automation, or production security.

Do not approve new governed tool powers, run controls, sandbox orchestration, SIEM adapters,
production identity, remote MCP, hosted telemetry, shell/Docker/Kubernetes/browser tools, arbitrary
HTTP, broad writes, public/security-product positioning, or plugin SDK work.
"""


def _commands() -> str:
    return """# Demo Command Sequence

1. `make live-demo-preflight`
2. `make demo-seed`
3. `make compose-up && make compose-smoke`
4. `uv run python -m ithildin_mcp_server`
5. `make demo-flow`
6. Inspect `var/review-packets/v3/operator-workbench/DEMO_FLOW_RESULT.md`
7. Open `http://127.0.0.1:5173`
8. Select the demo run and use `Export Run Evidence`
9. `make demo-flow-result-check`
10. `make demo-reset-guide`
11. `make demo-workbench`
12. `make compose-down`

Steps 3-8 require an intentional local demo run. The packet generator itself does not perform them.
"""


def _result_check_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Demo Flow Result Check",
        "",
        f"- valid: `{str(report['valid']).lower()}`",
        f"- status: `{report['status']}`",
        f"- result_present: `{str(report['result_present']).lower()}`",
        f"- path: `{report['path']}`",
        "",
        "## Failures",
        "",
    ]
    lines.extend(f"- {failure}" for failure in report["failures"] or ["none"])
    lines.extend(
        [
            "",
            "A `not_run` status is acceptable for normal release gates because `make demo-flow`",
            "requires an intentional local API/UI demo stack. If the result is present, this",
            "check validates required safe fields and rejects obvious secret or diff content.",
        ]
    )
    return "\n".join(lines)


def _artifact_pointers(repo_root: Path) -> str:
    paths = [
        Path("var/review-packets/v3/operator-workbench/DEMO_FLOW_RESULT.md"),
        Path("var/review-packets/v3/operator-workbench/DEMO_OBSERVED_SUMMARY.md"),
        Path("var/review-packets/v3/operator-workbench/RUN_EVIDENCE_EXPORT.json"),
        Path("var/review-packets/v3/operator-workbench/DEMO_RESET_GUIDE.md"),
        Path("var/review-packets/v3/operator-workbench/WORKBENCH_DEMO_INDEX.md"),
        Path("var/review-packets/v3/live-demo"),
        Path("var/review-packets/v3/operator-sandbox-demo"),
        Path("var/review-packets/v3/agent-run-correlation"),
    ]
    lines = ["# Demo Artifact Pointers", ""]
    for path in paths:
        lines.append(f"- `{path.as_posix()}` exists=`{str((repo_root / path).exists()).lower()}`")
    return "\n".join(lines)


def _require_project_root(repo_root: Path) -> None:
    missing = [marker.as_posix() for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        raise DemoEvidencePacketError(
            "must be run from Ithildin repo root; missing " + ", ".join(missing)
        )


def _git(repo_root: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _hashes(output_dir: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(output_dir.iterdir()):
        if path.name == HASH_MANIFEST or not path.is_file():
            continue
        data = path.read_bytes()
        entries.append(
            {
                "path": path.name,
                "bytes": len(data),
                "sha256": "sha256:" + hashlib.sha256(data).hexdigest(),
            }
        )
    return entries


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())

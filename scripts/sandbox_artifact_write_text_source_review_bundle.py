"""Build a focused sandbox.artifact.write_text source-review bundle."""

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
    no_new_powers_guardrail,
    sandbox_artifact_write_text_implementation_gate,
    sandbox_artifact_write_text_preimplementation_check,
    tool_surface_invariant_gate,
)

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/sandbox-artifact-write-text-source-review")
SOURCE_FILES = [
    "apps/api/src/ithildin_api/sandbox_artifacts.py",
    "apps/api/src/ithildin_api/tool_calls.py",
    "apps/api/src/ithildin_api/resources.py",
    "apps/api/src/ithildin_api/policy_parity.py",
    "apps/mcp-server/src/ithildin_mcp_server/server.py",
    "tool-manifests/sandbox-artifact-write-text.yaml",
    "tool-manifests.lock.json",
    "policies/tests/parity.yaml",
]
TEST_FILES = [
    "tests/test_governed_tool_calls.py",
    "tests/test_mcp_adapter.py",
    "tests/test_policy_parity.py",
    "tests/test_tool_registry.py",
    "tests/test_manifest_change_review.py",
    "tests/test_release_readiness.py",
]
CONTRACT_DOCS = [
    "docs/codex/capability-proposals/sandbox-artifact-write-text.md",
    "docs/codex/capability-implementation-plans/sandbox-artifact-write-text.md",
    "docs/codex/sandbox-artifact-write-text-fixture-plan.md",
    "docs/codex/sandbox-artifact-write-text-negative-transcripts.md",
    "docs/codex/sandbox-artifact-write-text-source-review.md",
    "docs/codex/sandbox-artifact-write-text-implementation-decision.md",
    "docs/codex/sandbox-promotion-evidence-contract.md",
    "docs/codex/no-new-powers-guardrail.md",
    "docs/codex/tool-surface-invariant-gate.md",
]
FOCUSED_TEST_COMMAND = [
    "uv",
    "run",
    "pytest",
    "tests/test_governed_tool_calls.py",
    "tests/test_mcp_adapter.py",
    "tests/test_policy_parity.py",
    "tests/test_tool_registry.py",
    "tests/test_manifest_change_review.py",
    "-q",
]


class SandboxArtifactWriteTextSourceReviewBundleError(RuntimeError):
    """Raised when the source-review bundle cannot be built."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--skip-commands", action="store_true")
    args = parser.parse_args()
    try:
        output_dir = build_bundle(
            repo_root=Path.cwd().resolve(),
            output_dir=args.output_dir,
            allow_dirty=args.allow_dirty,
            run_commands=not args.skip_commands,
        )
    except SandboxArtifactWriteTextSourceReviewBundleError as exc:
        print(f"sandbox.artifact.write_text source-review bundle failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built sandbox.artifact.write_text source-review bundle at {output_dir}")
    return 0


def build_bundle(
    *,
    repo_root: Path,
    output_dir: Path,
    allow_dirty: bool = False,
    run_commands: bool = True,
) -> Path:
    _require_project_root(repo_root)
    commit = _git(repo_root, ["rev-parse", "HEAD"])
    dirty = bool(_git(repo_root, ["status", "--short"]))
    if dirty and not allow_dirty:
        raise SandboxArtifactWriteTextSourceReviewBundleError(
            "working tree is dirty; commit before source-review handoff"
        )
    implementation_gate = sandbox_artifact_write_text_implementation_gate.build_report(repo_root)
    historical_plan = sandbox_artifact_write_text_preimplementation_check.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    failures = [
        *(f"implementation gate: {failure}" for failure in implementation_gate["failures"]),
        *(f"historical preimplementation: {failure}" for failure in historical_plan["failures"]),
        *(f"no-new-powers guardrail: {failure}" for failure in no_new_powers["failures"]),
        *(f"tool-surface: {failure}" for failure in tool_surface["failures"]),
    ]
    if failures:
        raise SandboxArtifactWriteTextSourceReviewBundleError("; ".join(failures))

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    context = {
        "commit": commit,
        "dirty": dirty,
        "implementation_gate": implementation_gate,
        "historical_plan": historical_plan,
        "no_new_powers": no_new_powers,
        "tool_surface": tool_surface,
    }
    files = {
        "00_SANDBOX_ARTIFACT_WRITE_TEXT_SOURCE_REVIEW_INDEX.md": _index(context),
        "01_SANDBOX_ARTIFACT_WRITE_TEXT_SOURCE_REVIEW_PROMPT.md": _prompt(context),
        "02_SANDBOX_ARTIFACT_WRITE_TEXT_SOURCE_BUNDLE.md": _bundle_files(
            repo_root, SOURCE_FILES
        ),
        "03_SANDBOX_ARTIFACT_WRITE_TEXT_TESTS_BUNDLE.md": _bundle_files(repo_root, TEST_FILES),
        "04_SANDBOX_ARTIFACT_WRITE_TEXT_CONTRACTS_BUNDLE.md": _bundle_files(
            repo_root, CONTRACT_DOCS
        ),
        "05_SANDBOX_ARTIFACT_WRITE_TEXT_GATE_EVIDENCE.json": json.dumps(
            {
                "implementation_gate": implementation_gate,
                "historical_preimplementation": historical_plan,
                "no_new_powers": no_new_powers,
                "tool_surface": tool_surface,
            },
            indent=2,
            sort_keys=True,
        ),
        "08_SANDBOX_ARTIFACT_WRITE_TEXT_INTAKE_COMMANDS.md": _intake_commands(context),
    }
    for name, content in files.items():
        (output_dir / name).write_text(content.rstrip() + "\n", encoding="utf-8")

    gate_output = _command_output(
        ["make", "sandbox-artifact-write-text-implementation-gate"],
        run_commands=run_commands,
    )
    parity_output = _command_output(["make", "policy-parity"], run_commands=run_commands)
    negative_output = _command_output(
        ["make", "sandbox-artifact-write-text-negative-transcripts"],
        run_commands=run_commands,
    )
    (output_dir / "06_SANDBOX_ARTIFACT_WRITE_TEXT_EVIDENCE.md").write_text(
        _packet_text(_evidence(gate_output, parity_output, negative_output)),
        encoding="utf-8",
    )
    _write_command_output(
        output_dir / "07_SANDBOX_ARTIFACT_WRITE_TEXT_FOCUSED_TESTS.txt",
        _command_output(FOCUSED_TEST_COMMAND, run_commands=run_commands),
    )
    _write_json(
        output_dir / "sandbox-artifact-write-text-source-review-artifact-hashes.json",
        _hashes(output_dir),
    )
    return output_dir


def _index(context: dict[str, Any]) -> str:
    return f"""# sandbox.artifact.write_text Source Review Handoff

This packet prepares the implemented bounded local-preview `sandbox.artifact.write_text` lane for
focused source review. It packages the executor, governed dispatch path, MCP wiring, manifest,
policy-parity fixture, tests, contract docs, negative transcript evidence, and gate evidence.

## Boundary

- Lane: `sandbox.artifact.write_text`.
- Finding namespace: `EXT-SANDBOX-WRITE-###`.
- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Tool count: `{context["tool_surface"]["tool_count"]}`.
- Runtime implementation: bounded approval-gated local-preview text artifact writes.
- Host promotion: not implemented.
- Sandbox/VM lifecycle control: not implemented.

## Send These Files

1. `00_SANDBOX_ARTIFACT_WRITE_TEXT_SOURCE_REVIEW_INDEX.md`
2. `01_SANDBOX_ARTIFACT_WRITE_TEXT_SOURCE_REVIEW_PROMPT.md`
3. `02_SANDBOX_ARTIFACT_WRITE_TEXT_SOURCE_BUNDLE.md`
4. `03_SANDBOX_ARTIFACT_WRITE_TEXT_TESTS_BUNDLE.md`
5. `04_SANDBOX_ARTIFACT_WRITE_TEXT_CONTRACTS_BUNDLE.md`
6. `05_SANDBOX_ARTIFACT_WRITE_TEXT_GATE_EVIDENCE.json`
7. `06_SANDBOX_ARTIFACT_WRITE_TEXT_EVIDENCE.md`
8. `07_SANDBOX_ARTIFACT_WRITE_TEXT_FOCUSED_TESTS.txt`
9. `08_SANDBOX_ARTIFACT_WRITE_TEXT_INTAKE_COMMANDS.md`
10. `sandbox-artifact-write-text-source-review-artifact-hashes.json`

## What This Does Not Prove

This packet does not approve broad filesystem writes, host promotion, automatic repair, sandbox
orchestration, VM/container lifecycle control, shell execution, public/security-product
positioning, compliance automation, or production safety.
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# sandbox.artifact.write_text Source Review Prompt

You are reviewing Ithildin as a source reviewer for the `sandbox.artifact.write_text` lane only.
Treat this as source-level review if and only if you inspect the attached source bundle, focused
tests, policy parity fixture, contract docs, negative transcript evidence, and gate evidence.

Reviewed commit: `{context["commit"]}`
Area: `sandbox-artifact-write-text`
Finding namespace: `EXT-SANDBOX-WRITE-###`

Command evidence includes `make sandbox-artifact-write-text-negative-transcripts`,
`make sandbox-artifact-write-text-implementation-gate`, focused tests, and policy parity.

## Scope

Please review:

- manifest/schema shape: write risk, sandbox category, MCP exposure, closed input schema, content
  limits, path/root fields, and approval-id execution flow;
- approval binding: approval scope stores content hash/action metadata, not artifact content, and
  execution must resubmit matching content with the approved one-time scope;
- executor path handling: workspace confinement, relative paths only, traversal/encoded/control
  denial, hidden/sensitive/`.git` denial, symlink/hardlink denial, UTF-8 text only, size/line
  limits, parent directory behavior, overwrite behavior, and safe errors;
- write behavior: same-directory temp file, exclusive-create/link semantics for no-overwrite,
  replace semantics for explicit overwrite, replay denial, and no broad write/delete/move behavior;
- output and audit safety: no file contents, raw host paths, prompts, secrets, environment values,
  shell output, VM logs, sandbox internals, or Mission Control private state;
- policy preview/runtime parity for `sandbox_artifact`;
- MCP exposure through the governed path only;
- separation from Mission Control, host promotion, sandbox orchestration, and VM/container
  lifecycle.

## Required Disposition

Please answer whether this lane can proceed as a bounded local-preview implementation pending
external/source-review disposition. If it cannot, list each blocking implementation, test, or
evidence gap.

Use finding IDs `EXT-SANDBOX-WRITE-###`. Do not approve broad filesystem writes, host promotion,
sandbox orchestration, shell/Docker/Kubernetes/browser powers, public/security-product
positioning, compliance automation, or future governed tool powers.
"""


def _evidence(gate_output: str, parity_output: str, negative_output: str) -> str:
    return f"""# sandbox.artifact.write_text Evidence

## Implementation Gate

```text
{gate_output.rstrip()}
```

## Policy Parity

```text
{parity_output.rstrip()}
```

## Negative Transcripts

```text
{negative_output.rstrip()}
```
"""


def _intake_commands(context: dict[str, Any]) -> str:
    return f"""# sandbox.artifact.write_text Intake Commands

Reviewed commit:

```sh
git checkout {context["commit"]}
```

Focused validation:

```sh
make sandbox-artifact-write-text-implementation-gate
make sandbox-artifact-write-text-negative-transcripts
make policy-parity
uv run pytest tests/test_governed_tool_calls.py tests/test_mcp_adapter.py \\
  tests/test_policy_parity.py tests/test_tool_registry.py tests/test_manifest_change_review.py -q
```

Broader validation:

```sh
make release-check
```
"""


def _bundle_files(repo_root: Path, files: list[str]) -> str:
    sections: list[str] = []
    for relative in files:
        path = repo_root / relative
        if not path.exists():
            raise SandboxArtifactWriteTextSourceReviewBundleError(f"missing file: {relative}")
        sections.extend(
            [
                f"## {relative}",
                "",
                "```" + _fence_language(path),
                path.read_text(encoding="utf-8").rstrip(),
                "```",
                "",
            ]
        )
    return "\n".join(sections).rstrip()


def _packet_text(content: str) -> str:
    return content.rstrip() + "\n"


def _write_command_output(path: Path, output: str) -> None:
    path.write_text(output.rstrip() + "\n", encoding="utf-8")


def _command_output(command: list[str], *, run_commands: bool) -> str:
    if not run_commands:
        return "$ " + " ".join(command) + "\n<command execution skipped>"
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    output = "\n".join(
        [
            "$ " + " ".join(command),
            f"returncode={completed.returncode}",
            completed.stdout.rstrip(),
            completed.stderr.rstrip(),
        ]
    ).rstrip()
    if completed.returncode != 0:
        raise SandboxArtifactWriteTextSourceReviewBundleError(
            "source-review evidence command failed:\n" + output
        )
    return output


def _hashes(output_dir: Path) -> list[dict[str, Any]]:
    entries = []
    for path in sorted(output_dir.iterdir()):
        if path.name == "sandbox-artifact-write-text-source-review-artifact-hashes.json":
            continue
        data = path.read_bytes()
        entries.append(
            {
                "path": path.name,
                "sha256": "sha256:" + hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            }
        )
    return entries


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _require_project_root(repo_root: Path) -> None:
    missing = [
        marker
        for marker in ("pyproject.toml", "Makefile", "tool-manifests.lock.json")
        if not repo_root.joinpath(marker).exists()
    ]
    if missing:
        raise SandboxArtifactWriteTextSourceReviewBundleError(
            "must be run from the Ithildin repo root; missing markers: " + ", ".join(missing)
        )


def _git(repo_root: Path, args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _fence_language(path: Path) -> str:
    if path.suffix == ".py":
        return "python"
    if path.suffix in {".yaml", ".yml"}:
        return "yaml"
    if path.suffix == ".json":
        return "json"
    if path.suffix == ".md":
        return "markdown"
    return "text"


if __name__ == "__main__":
    raise SystemExit(main())

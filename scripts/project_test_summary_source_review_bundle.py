"""Build a focused project.test.summary source-review bundle."""

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

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/project-test-summary-source-review")
SOURCE_FILES = [
    Path("apps/api/src/ithildin_api/read_tools.py"),
    Path("apps/api/src/ithildin_api/tool_calls.py"),
    Path("apps/api/src/ithildin_api/policy_preview.py"),
    Path("apps/api/src/ithildin_api/policy_parity.py"),
    Path("apps/mcp-server/src/ithildin_mcp_server/server.py"),
    Path("tool-manifests/project-test-summary.yaml"),
    Path("tool-manifests.lock.json"),
]
TEST_FILES = [
    Path("policies/tests/parity.yaml"),
    Path("tests/test_read_tools.py"),
    Path("tests/test_governed_tool_calls.py"),
    Path("tests/test_mcp_adapter.py"),
    Path("tests/test_policy_parity.py"),
    Path("tests/test_tool_registry.py"),
    Path("tests/test_release_readiness.py"),
]
CONTRACT_DOCS = [
    Path("docs/codex/v3-project-test-summary-implementation.md"),
    Path("docs/codex/capability-implementation-plans/project-test-summary.md"),
    Path("docs/codex/capability-proposals/project-test-summary.md"),
    Path("docs/codex/read-only-local-metadata-contract.md"),
    Path("docs/codex/metadata-privacy-policy.md"),
    Path("docs/codex/read-only-capability-inventory.md"),
    Path("docs/codex/no-new-powers-guardrail.md"),
    Path("docs/codex/source-review-closure-matrix.md"),
]
FOCUSED_TEST_COMMAND = [
    "uv",
    "run",
    "pytest",
    "tests/test_read_tools.py",
    "tests/test_governed_tool_calls.py",
    "tests/test_mcp_adapter.py",
    "tests/test_policy_parity.py",
    "tests/test_tool_registry.py",
    "-q",
]
IMPLEMENTATION_GATE_COMMAND = ["make", "project-test-summary-implementation-gate"]
POLICY_PARITY_COMMAND = ["make", "policy-parity"]


class ProjectTestSummarySourceReviewBundleError(RuntimeError):
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
    except ProjectTestSummarySourceReviewBundleError as exc:
        print(f"project.test.summary source-review bundle failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built project.test.summary source-review bundle at {output_dir}")
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
        raise ProjectTestSummarySourceReviewBundleError(
            "working tree is dirty; commit before source-review handoff"
        )
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context = {"commit": commit, "dirty": dirty}
    implementation_packet = _packet_text(_implementation_packet(context))
    context["implementation_packet_sha256"] = _content_sha256(implementation_packet)
    files = {
        "00_PROJECT_TEST_SUMMARY_SOURCE_REVIEW_INDEX.md": _index(context),
        "01_PROJECT_TEST_SUMMARY_SOURCE_REVIEW_PROMPT.md": _prompt(context),
        "02_PROJECT_TEST_SUMMARY_IMPLEMENTATION_PACKET.md": implementation_packet,
        "03_PROJECT_TEST_SUMMARY_SOURCE_BUNDLE.md": _bundle_sources(repo_root, SOURCE_FILES),
        "04_PROJECT_TEST_SUMMARY_TESTS_BUNDLE.md": _bundle_sources(repo_root, TEST_FILES),
        "05_PROJECT_TEST_SUMMARY_CONTRACTS_BUNDLE.md": _bundle_sources(
            repo_root, CONTRACT_DOCS
        ),
        "08_PROJECT_TEST_SUMMARY_INTAKE_COMMANDS.md": _intake_commands(),
    }
    for relative, content in files.items():
        (output_dir / relative).write_text(_packet_text(content), encoding="utf-8")
    gate_output = _command_output(IMPLEMENTATION_GATE_COMMAND, run_commands=run_commands)
    parity_output = _command_output(POLICY_PARITY_COMMAND, run_commands=run_commands)
    (output_dir / "06_PROJECT_TEST_SUMMARY_EVIDENCE.md").write_text(
        _packet_text(_evidence(gate_output, parity_output)),
        encoding="utf-8",
    )
    _write_command_output(
        output_dir / "07_PROJECT_TEST_SUMMARY_FOCUSED_TESTS.txt",
        _command_output(FOCUSED_TEST_COMMAND, run_commands=run_commands),
    )
    _write_json(
        output_dir / "project-test-summary-source-review-artifact-hashes.json",
        _hashes(output_dir),
    )
    return output_dir


def _index(context: dict[str, Any]) -> str:
    return f"""# project.test.summary Source Review Handoff

This packet prepares the `project.test.summary` lane for source-level review. It attaches the
manifest, implementation path, focused tests, policy-parity fixture, implementation record,
no-new-powers evidence, and command evidence needed to decide whether this bounded read-only
capability can close for the v0.1 local-preview runtime boundary.

- Lane: `project.test.summary`.
- Finding namespace: `EXT-PTS-###`.
- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Implementation packet SHA-256: `{context["implementation_packet_sha256"]}`.

## Send These Files

1. `00_PROJECT_TEST_SUMMARY_SOURCE_REVIEW_INDEX.md`
2. `01_PROJECT_TEST_SUMMARY_SOURCE_REVIEW_PROMPT.md`
3. `02_PROJECT_TEST_SUMMARY_IMPLEMENTATION_PACKET.md`
4. `03_PROJECT_TEST_SUMMARY_SOURCE_BUNDLE.md`
5. `04_PROJECT_TEST_SUMMARY_TESTS_BUNDLE.md`
6. `05_PROJECT_TEST_SUMMARY_CONTRACTS_BUNDLE.md`
7. `06_PROJECT_TEST_SUMMARY_EVIDENCE.md`
8. `07_PROJECT_TEST_SUMMARY_FOCUSED_TESTS.txt`
9. `08_PROJECT_TEST_SUMMARY_INTAKE_COMMANDS.md`
10. `project-test-summary-source-review-artifact-hashes.json`

This packet does not approve raw recursive listings, raw paths, test file names, test case names,
file contents, coverage data, command output, dependency names, package names, package-manager
execution, test execution, network access, broad filesystem access, or public/security-product
positioning.
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# project.test.summary Source Review Prompt

You are reviewing Ithildin as a source reviewer for the `project.test.summary` lane only.
Treat this as source-level review if and only if you inspect the attached source bundle, focused
tests, parity fixture, contract docs, implementation packet, and command evidence.

Reviewed commit: `{context["commit"]}`
Reviewed implementation packet hash: `{context["implementation_packet_sha256"]}`
Area: `project-test-summary`
Finding namespace: `EXT-PTS-###`

Please answer whether this lane can close for the v0.1 local-preview runtime boundary. Review that
the tool is count-only, workspace-confined, read-only, policy/audit/MCP mediated, uses resource
type `project_tests`, and is free of test file names, raw sensitive paths, file contents,
test case names, coverage data, command output, package-manager execution, test execution,
registry/network access, shell, and broad filesystem powers.
"""


def _implementation_packet(context: dict[str, Any]) -> str:
    return f"""# project.test.summary Implementation Packet

- Tool: `project.test.summary`
- Commit: `{context["commit"]}`
- Dirty: `{str(context["dirty"]).lower()}`
- Risk/category: `read` / `project`
- Resource type: `project_tests`
- Boundary: test-layout counts and allowlisted labels only.
"""


def _evidence(gate_output: str, parity_output: str) -> str:
    return f"""# project.test.summary Evidence

## Implementation Gate

```text
{gate_output}
```

## Policy Parity

```text
{parity_output}
```
"""


def _intake_commands() -> str:
    return """# project.test.summary Intake Commands

```bash
make project-test-summary-implementation-gate
make policy-parity
uv run pytest tests/test_read_tools.py tests/test_governed_tool_calls.py \\
  tests/test_mcp_adapter.py tests/test_policy_parity.py tests/test_tool_registry.py -q
```
"""


def _bundle_sources(repo_root: Path, paths: list[Path]) -> str:
    chunks: list[str] = []
    for relative in paths:
        path = repo_root / relative
        if not path.exists():
            raise ProjectTestSummarySourceReviewBundleError(f"missing source: {relative}")
        content = path.read_text(encoding="utf-8")
        chunks.append(f"## {relative.as_posix()}\n\n```text\n{content}\n```")
    return "\n\n".join(chunks)


def _command_output(command: list[str], *, run_commands: bool) -> str:
    if not run_commands:
        return f"skipped command: {' '.join(command)}"
    process = subprocess.run(command, text=True, capture_output=True, check=False)
    output = (process.stdout + process.stderr).strip()
    return f"$ {' '.join(command)}\nexit_code={process.returncode}\n{output}"


def _write_command_output(path: Path, output: str) -> None:
    path.write_text(output + "\n", encoding="utf-8")


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _hashes(output_dir: Path) -> list[dict[str, Any]]:
    records = []
    for path in sorted(output_dir.iterdir()):
        if path.name.endswith("artifact-hashes.json"):
            continue
        data = path.read_bytes()
        records.append(
            {
                "path": path.name,
                "sha256": f"sha256:{hashlib.sha256(data).hexdigest()}",
                "bytes": len(data),
            }
        )
    return records


def _content_sha256(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


def _packet_text(text: str) -> str:
    return text.strip() + "\n"


def _require_project_root(repo_root: Path) -> None:
    for marker in ("pyproject.toml", "Makefile", "tool-manifests.lock.json"):
        if not (repo_root / marker).exists():
            raise ProjectTestSummarySourceReviewBundleError("not an Ithildin repository root")


def _git(repo_root: Path, args: list[str]) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if process.returncode != 0:
        raise ProjectTestSummarySourceReviewBundleError(process.stderr.strip())
    return process.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())

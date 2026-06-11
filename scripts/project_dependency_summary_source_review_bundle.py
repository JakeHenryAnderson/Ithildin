"""Build a focused project.dependency.summary source-review bundle."""

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

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v0.9/project-dependency-summary-source-review")

SOURCE_FILES = [
    Path("apps/api/src/ithildin_api/read_tools.py"),
    Path("apps/api/src/ithildin_api/resources.py"),
    Path("apps/api/src/ithildin_api/policy_preview.py"),
    Path("apps/api/src/ithildin_api/tool_calls.py"),
    Path("apps/api/src/ithildin_api/schema_validation.py"),
    Path("apps/api/src/ithildin_api/policy_parity.py"),
    Path("apps/mcp-server/src/ithildin_mcp_server/server.py"),
    Path("tool-manifests/project-dependency-summary.yaml"),
    Path("tool-manifests.lock.json"),
]

TEST_FILES = [
    Path("policies/tests/parity.yaml"),
    Path("tests/test_read_tools.py"),
    Path("tests/test_governed_tool_calls.py"),
    Path("tests/test_mcp_adapter.py"),
    Path("tests/test_policy_parity.py"),
    Path("tests/test_tool_registry.py"),
    Path("tests/test_manifest_change_review.py"),
    Path("tests/test_release_readiness.py"),
]

CONTRACT_DOCS = [
    Path("docs/codex/v3-project-dependency-summary-implementation.md"),
    Path("docs/codex/capability-implementation-plans/project-dependency-summary.md"),
    Path("docs/codex/capability-proposals/project-dependency-summary.md"),
    Path("docs/codex/read-only-local-metadata-contract.md"),
    Path("docs/codex/metadata-privacy-policy.md"),
    Path("docs/codex/read-only-metadata-capability-checklist.md"),
    Path("docs/codex/tool-surface-invariant-gate.md"),
    Path("docs/codex/no-new-powers-guardrail.md"),
    Path("docs/codex/capability-expansion-gate.md"),
    Path("docs/codex/read-only-capability-inventory.md"),
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
    "tests/test_manifest_change_review.py",
    "-q",
]
IMPLEMENTATION_GATE_COMMAND = ["make", "project-dependency-summary-implementation-gate"]
POLICY_PARITY_COMMAND = ["make", "policy-parity"]


class ProjectDependencySummarySourceReviewBundleError(RuntimeError):
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
    except ProjectDependencySummarySourceReviewBundleError as exc:
        print(f"project.dependency.summary source-review bundle failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built project.dependency.summary source-review bundle at {output_dir}")
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
        raise ProjectDependencySummarySourceReviewBundleError(
            "working tree is dirty; commit before source-review handoff"
        )
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    implementation_packet = _packet_text(_implementation_packet(commit, dirty, run_commands))
    packet_hash = _content_sha256(implementation_packet)
    context = {
        "commit": commit,
        "dirty": dirty,
        "implementation_packet_sha256": packet_hash,
    }
    files = {
        "00_PROJECT_DEPENDENCY_SUMMARY_SOURCE_REVIEW_INDEX.md": _index(context),
        "01_PROJECT_DEPENDENCY_SUMMARY_SOURCE_REVIEW_PROMPT.md": _prompt(context),
        "02_PROJECT_DEPENDENCY_SUMMARY_IMPLEMENTATION_PACKET.md": implementation_packet,
        "03_PROJECT_DEPENDENCY_SUMMARY_SOURCE_BUNDLE.md": _bundle_sources(repo_root, SOURCE_FILES),
        "04_PROJECT_DEPENDENCY_SUMMARY_TESTS_BUNDLE.md": _bundle_sources(repo_root, TEST_FILES),
        "05_PROJECT_DEPENDENCY_SUMMARY_CONTRACTS_BUNDLE.md": _bundle_sources(
            repo_root, CONTRACT_DOCS
        ),
        "08_PROJECT_DEPENDENCY_SUMMARY_INTAKE_COMMANDS.md": _intake_commands(context),
    }
    for relative, content in files.items():
        (output_dir / relative).write_text(_packet_text(content), encoding="utf-8")

    gate_output = _command_output(IMPLEMENTATION_GATE_COMMAND, run_commands=run_commands)
    parity_output = _command_output(POLICY_PARITY_COMMAND, run_commands=run_commands)
    (output_dir / "06_PROJECT_DEPENDENCY_SUMMARY_EVIDENCE.md").write_text(
        _packet_text(_evidence(gate_output, parity_output)),
        encoding="utf-8",
    )
    _write_command_output(
        output_dir / "07_PROJECT_DEPENDENCY_SUMMARY_FOCUSED_TESTS.txt",
        _command_output(FOCUSED_TEST_COMMAND, run_commands=run_commands),
    )
    _write_json(
        output_dir / "project-dependency-summary-source-review-artifact-hashes.json",
        _hashes(output_dir),
    )
    return output_dir


def _index(context: dict[str, Any]) -> str:
    return f"""# project.dependency.summary Source Review Handoff

This packet prepares the `project.dependency.summary` lane for source-level review. It attaches the
manifest, implementation path, focused tests, policy-parity fixture, implementation record,
no-new-powers evidence, and command evidence needed to decide whether this bounded read-only
capability can close for the v0.1 local-preview runtime boundary.

## Boundary

- Lane: `project.dependency.summary`.
- Finding namespace: `EXT-PMS-###`.
- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Implementation packet SHA-256: `{context["implementation_packet_sha256"]}`.

## Send These Files

1. `00_PROJECT_DEPENDENCY_SUMMARY_SOURCE_REVIEW_INDEX.md`
2. `01_PROJECT_DEPENDENCY_SUMMARY_SOURCE_REVIEW_PROMPT.md`
3. `02_PROJECT_DEPENDENCY_SUMMARY_IMPLEMENTATION_PACKET.md`
4. `03_PROJECT_DEPENDENCY_SUMMARY_SOURCE_BUNDLE.md`
5. `04_PROJECT_DEPENDENCY_SUMMARY_TESTS_BUNDLE.md`
6. `05_PROJECT_DEPENDENCY_SUMMARY_CONTRACTS_BUNDLE.md`
7. `06_PROJECT_DEPENDENCY_SUMMARY_EVIDENCE.md`
8. `07_PROJECT_DEPENDENCY_SUMMARY_FOCUSED_TESTS.txt`
9. `08_PROJECT_DEPENDENCY_SUMMARY_INTAKE_COMMANDS.md`
10. `project-dependency-summary-source-review-artifact-hashes.json`

## What This Does Not Prove

This packet does not approve package-manager execution, registry/network access, recursive project
discovery, arbitrary manifest filenames, dependency-name disclosure, package-script disclosure,
broad filesystem access, or public/security-product positioning.
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# project.dependency.summary Source Review Prompt

You are reviewing Ithildin as a source reviewer for the `project.dependency.summary` lane only.
Treat this as source-level review if and only if you inspect the attached source bundle, focused
tests, parity fixture, contract docs, implementation packet, and command evidence.

Reviewed commit: `{context["commit"]}`
Reviewed implementation packet hash: `{context["implementation_packet_sha256"]}`
Area: `project-dependency-summary`
Finding namespace: `EXT-PDS-###`

## Scope

Please review:

- manifest/schema shape: read risk, project category, MCP exposure, `workspace_id`, `root`,
  `manifest_kinds`, `limit`, `additionalProperties: false`, no package-manager execution, and no
  caller-controlled parser, network, registry, or recursive-discovery fields;
- workspace safety: `root` and manifest files must resolve through existing workspace/path-safety
  rules, with symlink, hardlink, hidden/sensitive, traversal, binary, encoding, and size-limit
  denials preserved;
- manifest allowlist behavior for package.json, pyproject.toml, go.mod, Cargo.toml, pom.xml,
  build.gradle, requirements.txt, Gemfile, and composer.json only;
- parser/output safety: count-only metadata, file digests, byte sizes, parser status, response-local
  manifest IDs, lockfile-presence booleans, and no file contents, dependency names, version
  constraints, package names, package script names/values, registry URLs, repository URLs, or
  package-manager stdout/stderr;
- policy preview/runtime parity for the syntactic `project_dependencies` resource;
- MCP exposure and role visibility through the existing governed pipeline;
- audit evidence containing only safe dependency count, truncation, parser status, manifest kind,
  and output-policy booleans;
- no-new-powers and tool-surface gates staying limited to this bounded read-only addition.

## Required Disposition

Please answer whether the `project.dependency.summary` lane can close for the v0.1 local-preview
runtime boundary. If it cannot close, explain exactly which source/test/evidence item is missing or
which implementation issue blocks closure.

Use this exact finding table shape for actionable findings:

| Finding ID | Severity | Area | Affected files/functions |
| --- | --- | --- | --- |
| EXT-PDS-### | critical/high/medium/low/informational | project dependency | path/function |

Also include blocking status, disposition, and recommended fix for every actionable finding.

Do not approve package-manager execution, registry/network access, recursive discovery, arbitrary
manifest filenames, dependency-name disclosure, package-script disclosure, broad filesystem access,
public/security-product positioning, or future governed tool powers.
"""


def _implementation_packet(commit: str, dirty: bool, run_commands: bool) -> str:
    report = _command_output(
        [
            "uv",
            "run",
            "python",
            "scripts/project_dependency_summary_implementation_gate.py",
            "--json",
        ],
        run_commands=run_commands,
    )
    return "\n".join(
        [
            "# project.dependency.summary Implementation Packet",
            "",
            f"- Reviewed commit: `{commit}`",
            f"- Dirty at generation: `{str(dirty).lower()}`",
            "- Tool: `project.dependency.summary`",
            "- Status: approved v3 implementation for one bounded read-only project dependency",
            "  metadata tool.",
            "- Boundary: no shell, no package-manager execution, no registry/network access, no",
            "  recursive discovery, no arbitrary manifest filenames, no file contents, no",
            "  dependency names or versions, and no package script names or values.",
            "",
            "## Implementation Gate JSON",
            "",
            "```json",
            report.strip(),
            "```",
        ]
    )


def _evidence(gate_output: str, parity_output: str) -> str:
    return "\n".join(
        [
            "# project.dependency.summary Evidence",
            "",
            "## Implementation Gate",
            "",
            "```text",
            gate_output.strip(),
            "```",
            "",
            "## Policy Parity",
            "",
            "```text",
            parity_output.strip(),
            "```",
        ]
    )


def _intake_commands(context: dict[str, Any]) -> str:
    return f"""# project.dependency.summary Intake Commands

If a reviewer returns findings, normalize them with:

```bash
uv run python scripts/external_response_normalize.py \\
  var/review-runs/v0.9/project-dependency-summary/raw-response.md \\
  --reviewer "Reviewer Name" \\
  --reviewer-type "external-model" \\
  --source-access "source-level" \\
  --reviewed-commit "{context["commit"]}" \\
  --reviewed-packet-hash "{context["implementation_packet_sha256"]}" \\
  --area "project-dependency-summary" \\
  --output var/review-runs/v0.9/project-dependency-summary/normalized-response.json
```

Use finding IDs in the `EXT-PMS-###` namespace.

Focused commands:

```sh
uv run pytest \\
  tests/test_read_tools.py \\
  tests/test_governed_tool_calls.py \\
  tests/test_mcp_adapter.py \\
  tests/test_policy_parity.py \\
  tests/test_tool_registry.py \\
  tests/test_manifest_change_review.py \\
  -q
make project-dependency-summary-implementation-gate
make policy-parity
make tool-surface-invariant-gate
make no-new-powers-guardrail
```
"""


def _bundle_sources(repo_root: Path, paths: list[Path]) -> str:
    sections: list[str] = []
    for path in paths:
        source_path = repo_root / path
        if not source_path.exists():
            raise ProjectDependencySummarySourceReviewBundleError(f"missing bundle input: {path}")
        sections.extend(
            [
                f"# {path.as_posix()}",
                "",
                "```text",
                source_path.read_text(encoding="utf-8"),
                "```",
                "",
            ]
        )
    return "\n".join(sections)


def _command_output(command: list[str], *, run_commands: bool) -> str:
    if not run_commands:
        return f"$ {' '.join(command)}\n<command execution skipped for fixture bundle>"
    completed = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = completed.stdout.strip()
    status = f"$ {' '.join(command)}\nexit_code: {completed.returncode}"
    if output:
        status = f"{status}\n{output}"
    if completed.returncode != 0:
        raise ProjectDependencySummarySourceReviewBundleError(
            f"command failed while building bundle: {' '.join(command)}"
        )
    return status


def _write_command_output(path: Path, output: str) -> None:
    path.write_text(output if output.endswith("\n") else f"{output}\n", encoding="utf-8")


def _hashes(output_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    hash_manifest = "project-dependency-summary-source-review-artifact-hashes.json"
    for path in sorted(output_dir.iterdir()):
        if not path.is_file() or path.name == hash_manifest:
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


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(f"{json.dumps(payload, indent=2, sort_keys=True)}\n", encoding="utf-8")


def _packet_text(content: str) -> str:
    return content if content.endswith("\n") else f"{content}\n"


def _content_sha256(content: str) -> str:
    return f"sha256:{hashlib.sha256(_packet_text(content).encode('utf-8')).hexdigest()}"


def _git(repo_root: Path, args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=True,
    )
    return completed.stdout.strip()


def _require_project_root(repo_root: Path) -> None:
    markers = [
        repo_root / "pyproject.toml",
        repo_root / "Makefile",
        repo_root / "apps/api",
        repo_root / "apps/mcp-server",
        repo_root / "tool-manifests.lock.json",
    ]
    if not all(marker.exists() for marker in markers):
        raise ProjectDependencySummarySourceReviewBundleError(
            "must be run from the Ithildin repo root"
        )


if __name__ == "__main__":
    raise SystemExit(main())

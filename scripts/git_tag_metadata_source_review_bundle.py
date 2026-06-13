"""Build a focused git.show.tag_metadata source-review bundle."""

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

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v0.9/git-tag-metadata-source-review")

SOURCE_FILES = [
    Path("apps/api/src/ithildin_api/read_tools.py"),
    Path("apps/api/src/ithildin_api/resources.py"),
    Path("apps/api/src/ithildin_api/policy_preview.py"),
    Path("apps/api/src/ithildin_api/tool_calls.py"),
    Path("apps/api/src/ithildin_api/schema_validation.py"),
    Path("apps/api/src/ithildin_api/policy_parity.py"),
    Path("apps/mcp-server/src/ithildin_mcp_server/server.py"),
    Path("tool-manifests/git-show-tag-metadata.yaml"),
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
    Path("docs/codex/v0.9-git-tag-metadata-implementation.md"),
    Path("docs/codex/v0.9-git-tag-metadata-internal-review.md"),
    Path("docs/codex/capability-implementation-plans/git-show-tag-metadata.md"),
    Path("docs/codex/capability-proposals/git-show-tag-metadata.md"),
    Path("docs/codex/read-only-local-metadata-contract.md"),
    Path("docs/codex/metadata-privacy-policy.md"),
    Path("docs/codex/read-only-metadata-capability-checklist.md"),
    Path("docs/codex/tool-surface-invariant-gate.md"),
    Path("docs/codex/no-new-powers-guardrail.md"),
    Path("docs/codex/capability-expansion-gate.md"),
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
IMPLEMENTATION_GATE_COMMAND = ["make", "git-tag-metadata-implementation-gate"]
POLICY_PARITY_COMMAND = ["make", "policy-parity"]


class GitTagMetadataSourceReviewBundleError(RuntimeError):
    """Raised when the git tag metadata source-review bundle cannot be built."""


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
    except GitTagMetadataSourceReviewBundleError as exc:
        print(f"git.show.tag_metadata source-review bundle failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built git.show.tag_metadata source-review bundle at {output_dir}")
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
        raise GitTagMetadataSourceReviewBundleError(
            "working tree is dirty; commit before source-review handoff"
        )
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    implementation_packet = _packet_text(_implementation_packet(commit, dirty, run_commands))
    implementation_packet_hash = _content_sha256(implementation_packet)
    context = {
        "commit": commit,
        "dirty": dirty,
        "implementation_packet_sha256": implementation_packet_hash,
    }
    files = {
        "00_GIT_TAG_METADATA_SOURCE_REVIEW_INDEX.md": _index(context),
        "01_GIT_TAG_METADATA_SOURCE_REVIEW_PROMPT.md": _prompt(context),
        "02_GIT_TAG_METADATA_IMPLEMENTATION_PACKET.md": implementation_packet,
        "03_GIT_TAG_METADATA_SOURCE_BUNDLE.md": _bundle_sources(repo_root, SOURCE_FILES),
        "04_GIT_TAG_METADATA_TESTS_BUNDLE.md": _bundle_sources(repo_root, TEST_FILES),
        "05_GIT_TAG_METADATA_CONTRACTS_BUNDLE.md": _bundle_sources(repo_root, CONTRACT_DOCS),
        "08_GIT_TAG_METADATA_INTAKE_COMMANDS.md": _intake_commands(context),
    }
    for relative, content in files.items():
        (output_dir / relative).write_text(_packet_text(content), encoding="utf-8")

    gate_output = _command_output(IMPLEMENTATION_GATE_COMMAND, run_commands=run_commands)
    parity_output = _command_output(POLICY_PARITY_COMMAND, run_commands=run_commands)
    (output_dir / "06_GIT_TAG_METADATA_EVIDENCE.md").write_text(
        _packet_text(_evidence(gate_output, parity_output)),
        encoding="utf-8",
    )
    _write_command_output(
        output_dir / "07_GIT_TAG_METADATA_FOCUSED_TESTS.txt",
        _command_output(FOCUSED_TEST_COMMAND, run_commands=run_commands),
    )
    _write_json(
        output_dir / "git-tag-metadata-source-review-artifact-hashes.json",
        _hashes(output_dir),
    )
    return output_dir


def _index(context: dict[str, Any]) -> str:
    return f"""# git.show.tag_metadata Source Review Handoff

This packet prepares the `git.show.tag_metadata` lane for source-level review. It attaches the
manifest, implementation path, focused tests, policy-parity fixture, implementation record,
no-new-powers evidence, and command evidence needed to decide whether this bounded read-only
capability can close for the v0.1 local-preview runtime boundary.

## Boundary

- Lane: `git.show.tag_metadata`.
- Finding namespace: `EXT-GITTAG-###`.
- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Implementation packet SHA-256: `{context["implementation_packet_sha256"]}`.

## Send These Files

1. `00_GIT_TAG_METADATA_SOURCE_REVIEW_INDEX.md`
2. `01_GIT_TAG_METADATA_SOURCE_REVIEW_PROMPT.md`
3. `02_GIT_TAG_METADATA_IMPLEMENTATION_PACKET.md`
4. `03_GIT_TAG_METADATA_SOURCE_BUNDLE.md`
5. `04_GIT_TAG_METADATA_TESTS_BUNDLE.md`
6. `05_GIT_TAG_METADATA_CONTRACTS_BUNDLE.md`
7. `06_GIT_TAG_METADATA_EVIDENCE.md`
8. `07_GIT_TAG_METADATA_FOCUSED_TESTS.txt`
9. `08_GIT_TAG_METADATA_INTAKE_COMMANDS.md`
10. `git-tag-metadata-source-review-artifact-hashes.json`

## What This Does Not Prove

This packet does not approve broader capability expansion, arbitrary Git command execution, shell
access, branch/tag mutation, remote fetch, raw tag-name exposure, stable tag-name hashes, raw diffs,
file contents, broad filesystem access, or public/security-product positioning.
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# git.show.tag_metadata Source Review Prompt

You are reviewing Ithildin as a source reviewer for the `git.show.tag_metadata` lane only. Treat
this as source-level review if and only if you inspect the attached source bundle, focused tests,
parity fixture, contract docs, implementation packet, and command evidence.

Reviewed commit: `{context["commit"]}`
Reviewed implementation packet hash: `{context["implementation_packet_sha256"]}`
Area: `git-tag-metadata`
Finding namespace: `EXT-GITTAG-###`

## Scope

Please review:

- manifest/schema shape: read risk, Git category, MCP exposure, `selector.kind` enum, `limit`
  bounds, `additionalProperties: false`, and no caller-controlled argv, format strings, tag names,
  refspecs, remotes, pathspecs, diffs, headers, or bodies;
- fixed Git argv behavior for local tags only, with no shell, checkout, mutation, remote fetch,
  reflog access, or raw stderr leakage;
- workspace safety: repository toplevel must be inside the configured workspace for preview and
  runtime;
- output safety: no raw tag names, no stable tag-name hashes, no tag messages, no signatures,
  response-local `tag_id` handles only, resolved commit hashes, tag type/peeling evidence,
  count/truncation/skipped evidence, and untrusted metadata labeling;
- denial/safe failure cases for unsupported selectors, unknown fields, non-commit tag targets,
  casefold-conflicting tag names, control/non-NFC names, parent-repository escape, oversized output,
  and malformed Git metadata;
- policy preview/runtime parity for the syntactic `git_tags` resource;
- MCP exposure and role visibility through the existing governed pipeline;
- audit evidence containing only safe selector/count/output-policy metadata;
- no-new-powers and tool-surface gates staying limited to this bounded read-only addition.

## Required Disposition

Please answer whether the `git.show.tag_metadata` lane can close for the v0.1 local-preview runtime
boundary. If it cannot close, explain exactly which source/test/evidence item is missing or which
implementation issue blocks closure.

Use this exact finding table shape for actionable findings:

| Finding ID | Severity | Area | Affected files/functions |
| --- | --- | --- | --- |
| EXT-GITTAG-### | critical/high/medium/low/informational | git-tag-metadata | path/function |

Also include blocking status, disposition, and recommended fix for every actionable finding.

Do not approve arbitrary Git execution, raw tag names, stable tag-name hashes, raw diffs, file
contents, checkout, branch/tag mutation, remote fetch, public/security-product positioning, or
future governed tool powers.
"""


def _implementation_packet(commit: str, dirty: bool, run_commands: bool) -> str:
    report = _command_output(
        ["uv", "run", "python", "scripts/git_tag_metadata_implementation_gate.py", "--json"],
        run_commands=run_commands,
    )
    return "\n".join(
        [
            "# git.show.tag_metadata Implementation Packet",
            "",
            f"- Reviewed commit: `{commit}`",
            f"- Dirty at generation: `{str(dirty).lower()}`",
            "- Tool: `git.show.tag_metadata`",
            "- Status: approved v0.9 implementation for one bounded read-only Git tag metadata",
            "  tool.",
            "- Boundary: no shell, no caller-controlled Git argv/format/pathspec/refspec, no raw",
            "  tag names, no stable tag-name hashes, no remote refs, no file contents, no raw",
            "  diffs, no branch/tag mutation, and no broader capability approval.",
            "",
            "## Implementation Gate JSON",
            "",
            "```json",
            str(report["stdout"]).rstrip(),
            "```",
            "",
            "## Internal Checkpoint Note",
            "",
            "`git.show.tag_metadata` is ready for focused source-review handoff. The",
            "implementation gate validates safe audit metadata, nested schema checks in the",
            "no-new-powers guardrail, and documentation that `tag_id` values are response-local",
            "display handles rather than privacy-preserving randomness.",
        ]
    )


def _evidence(gate_output: dict[str, str | int], parity_output: dict[str, str | int]) -> str:
    return "\n".join(
        [
            "# git.show.tag_metadata Evidence",
            "",
            "## Implementation Gate",
            "",
            "Command: `make git-tag-metadata-implementation-gate`",
            f"Return code: `{gate_output['returncode']}`",
            "",
            "```text",
            str(gate_output["stdout"]).rstrip(),
            "```",
            "",
            "```text",
            str(gate_output["stderr"]).rstrip(),
            "```",
            "",
            "## Policy Parity",
            "",
            "Command: `make policy-parity`",
            f"Return code: `{parity_output['returncode']}`",
            "",
            "```text",
            str(parity_output["stdout"]).rstrip(),
            "```",
            "",
            "```text",
            str(parity_output["stderr"]).rstrip(),
            "```",
        ]
    )


def _intake_commands(context: dict[str, Any]) -> str:
    return f"""# git.show.tag_metadata Intake Commands

If a reviewer returns findings, normalize them with:

```bash
uv run python scripts/external_response_normalize.py \\
  var/review-runs/v0.9/git-tag-metadata/raw-response.md \\
  --reviewer "Reviewer Name" \\
  --reviewer-type "external-model" \\
  --source-access "source-level" \\
  --reviewed-commit "{context["commit"]}" \\
  --reviewed-packet-hash "{context["implementation_packet_sha256"]}" \\
  --area "git-tag-metadata" \\
  --output var/review-runs/v0.9/git-tag-metadata/normalized-response.json
```

Use finding IDs in the `EXT-GITTAG-###` namespace.
"""


def _bundle_sources(repo_root: Path, paths: list[Path]) -> str:
    sections: list[str] = []
    for path in paths:
        full_path = repo_root / path
        if not full_path.exists():
            raise GitTagMetadataSourceReviewBundleError(f"missing review file: {path}")
        sections.extend(
            [
                f"# {path.as_posix()}",
                "",
                "```text",
                full_path.read_text(encoding="utf-8").rstrip(),
                "```",
                "",
            ]
        )
    return "\n".join(sections)


def _command_output(command: list[str], *, run_commands: bool) -> dict[str, str | int]:
    if not run_commands:
        return {"returncode": 0, "stdout": f"SKIPPED: {' '.join(command)}", "stderr": ""}
    process = subprocess.run(command, capture_output=True, text=True, check=False)
    if process.returncode != 0:
        raise GitTagMetadataSourceReviewBundleError(
            "review evidence command failed: "
            f"{' '.join(command)} returned {process.returncode}\n"
            f"stdout:\n{process.stdout.rstrip()}\n"
            f"stderr:\n{process.stderr.rstrip()}"
        )
    return {
        "returncode": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr,
    }


def _write_command_output(path: Path, output: dict[str, str | int]) -> None:
    path.write_text(
        "\n".join(
            [
                f"returncode={output['returncode']}",
                "",
                "# stdout",
                str(output["stdout"]).rstrip(),
                "",
                "# stderr",
                str(output["stderr"]).rstrip(),
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _hashes(output_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(output_dir.iterdir(), key=lambda item: item.name):
        if path.name.endswith("artifact-hashes.json"):
            continue
        content = path.read_bytes()
        records.append(
            {
                "path": path.name,
                "sha256": "sha256:" + hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
            }
        )
    return records


def _packet_text(content: str) -> str:
    return content.rstrip() + "\n"


def _content_sha256(content: str) -> str:
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _require_project_root(repo_root: Path) -> None:
    required = [
        repo_root / "pyproject.toml",
        repo_root / "Makefile",
        repo_root / "tool-manifests.lock.json",
        repo_root / "apps/api",
        repo_root / "apps/mcp-server",
    ]
    if not all(path.exists() for path in required):
        raise GitTagMetadataSourceReviewBundleError("must be run from the Ithildin repo root")


if __name__ == "__main__":
    raise SystemExit(main())

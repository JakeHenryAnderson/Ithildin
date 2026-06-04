"""Build a focused git.show.commit_metadata external source-review bundle."""

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

try:
    from scripts import external_review_dispatch_packets
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    import external_review_dispatch_packets  # type: ignore[import-not-found,no-redef]

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v0.9/git-commit-metadata-source-review")

SOURCE_FILES = [
    Path("apps/api/src/ithildin_api/read_tools.py"),
    Path("apps/api/src/ithildin_api/resources.py"),
    Path("apps/api/src/ithildin_api/policy_preview.py"),
    Path("apps/api/src/ithildin_api/tool_calls.py"),
    Path("apps/api/src/ithildin_api/schema_validation.py"),
    Path("apps/api/src/ithildin_api/policy_parity.py"),
    Path("apps/mcp-server/src/ithildin_mcp_server/server.py"),
    Path("tool-manifests/git-show-commit-metadata.yaml"),
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
    Path("docs/codex/v0.9-git-commit-metadata-implementation.md"),
    Path("docs/codex/capability-implementation-plans/git-show-commit-metadata.md"),
    Path("docs/codex/capability-proposals/git-show-commit-metadata.md"),
    Path("docs/codex/v0.9-design-only-boundary-charter.md"),
    Path("docs/codex/v0.8-final-decision-packet.md"),
    Path("docs/codex/tool-surface-invariant-gate.md"),
    Path("docs/codex/no-new-powers-guardrail.md"),
    Path("docs/codex/capability-expansion-gate.md"),
    Path("docs/codex/source-review-closure-matrix.md"),
    Path("docs/codex/source-review-runbook-v2.md"),
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

IMPLEMENTATION_GATE_COMMAND = ["make", "git-commit-metadata-implementation-gate"]
POLICY_PARITY_COMMAND = ["make", "policy-parity"]


class GitCommitMetadataSourceReviewBundleError(RuntimeError):
    """Raised when the git commit metadata source-review bundle cannot be built."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument(
        "--skip-commands",
        action="store_true",
        help="skip command execution; intended only for tests",
    )
    args = parser.parse_args()

    try:
        output_dir = build_bundle(
            repo_root=Path.cwd().resolve(),
            output_dir=args.output_dir,
            allow_dirty=args.allow_dirty,
            run_commands=not args.skip_commands,
        )
    except GitCommitMetadataSourceReviewBundleError as exc:
        print(f"git.show.commit_metadata source-review bundle failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built git.show.commit_metadata source-review bundle at {output_dir}")
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
        raise GitCommitMetadataSourceReviewBundleError(
            "working tree is dirty; commit before source-review handoff"
        )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    implementation_packet = _packet_text(
        _implementation_packet(
            repo_root, commit, dirty, run_commands=run_commands
        )
    )
    implementation_packet_sha256 = _content_sha256(implementation_packet)
    context: dict[str, Any] = {
        "commit": commit,
        "dirty": dirty,
        "implementation_packet_sha256": implementation_packet_sha256,
    }

    files: dict[str, str] = {
        "00_GIT_COMMIT_METADATA_SOURCE_REVIEW_INDEX.md": _index(context),
        "01_GIT_COMMIT_METADATA_SOURCE_REVIEW_PROMPT.md": _prompt(context),
        "02_GIT_COMMIT_METADATA_IMPLEMENTATION_PACKET.md": implementation_packet,
        "03_GIT_COMMIT_METADATA_SOURCE_BUNDLE.md": _bundle_sources(repo_root, SOURCE_FILES),
        "04_GIT_COMMIT_METADATA_TESTS_BUNDLE.md": _bundle_sources(repo_root, TEST_FILES),
        "05_GIT_COMMIT_METADATA_CONTRACTS_BUNDLE.md": _bundle_sources(
            repo_root, CONTRACT_DOCS
        ),
        "08_GIT_COMMIT_METADATA_INTAKE_COMMANDS.md": _intake_commands(context),
    }
    for relative, content in files.items():
        (output_dir / relative).write_text(_packet_text(content), encoding="utf-8")

    gate_output = _command_output(IMPLEMENTATION_GATE_COMMAND, run_commands=run_commands)
    parity_output = _command_output(POLICY_PARITY_COMMAND, run_commands=run_commands)
    (output_dir / "06_GIT_COMMIT_METADATA_EVIDENCE.md").write_text(
        _packet_text(_evidence(gate_output, parity_output)),
        encoding="utf-8",
    )
    _write_command_output(
        output_dir / "07_GIT_COMMIT_METADATA_FOCUSED_TESTS.txt",
        _command_output(FOCUSED_TEST_COMMAND, run_commands=run_commands),
    )
    _write_json(
        output_dir / "git-commit-metadata-source-review-artifact-hashes.json",
        _hashes(output_dir),
    )
    return output_dir


def _packet_text(content: str) -> str:
    return content.rstrip() + "\n"


def _content_sha256(content: str) -> str:
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()


def _index(context: dict[str, Any]) -> str:
    return f"""# git.show.commit_metadata Source Review Handoff

This packet prepares the `git.show.commit_metadata` lane for source-level external review. It
attaches the manifest, implementation path, focused tests, policy-parity fixture, implementation
record, no-new-powers evidence, and command evidence needed to decide whether this one bounded
read-only capability can close for the v0.1 local-preview runtime boundary.

## Boundary

- Current review status: v0.9 approved implementation of one read-only Git metadata tool after the
  v0.8 product-risk decision.
- Lane: `git.show.commit_metadata`.
- Finding namespace: `EXT-GITMETA-###`.
- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Implementation packet SHA-256: `{context["implementation_packet_sha256"]}`.

## Send These Files

1. `00_GIT_COMMIT_METADATA_SOURCE_REVIEW_INDEX.md`
2. `01_GIT_COMMIT_METADATA_SOURCE_REVIEW_PROMPT.md`
3. `02_GIT_COMMIT_METADATA_IMPLEMENTATION_PACKET.md`
4. `03_GIT_COMMIT_METADATA_SOURCE_BUNDLE.md`
5. `04_GIT_COMMIT_METADATA_TESTS_BUNDLE.md`
6. `05_GIT_COMMIT_METADATA_CONTRACTS_BUNDLE.md`
7. `06_GIT_COMMIT_METADATA_EVIDENCE.md`
8. `07_GIT_COMMIT_METADATA_FOCUSED_TESTS.txt`
9. `08_GIT_COMMIT_METADATA_INTAKE_COMMANDS.md`
10. `git-commit-metadata-source-review-artifact-hashes.json`

## What This Does Not Prove

This packet does not approve any future capability expansion, public/security-product positioning,
production security, arbitrary Git command execution, shell access, branch mutation, remote fetch,
raw diff/file-content exposure, or broad filesystem access. It provides source/test evidence for an
external reviewer to decide whether this single read-only Git metadata tool can close for the
local-preview boundary.
"""


def _prompt(context: dict[str, Any]) -> str:
    finding_table = "\n".join(
        [
            "| Finding ID | Severity | Area | Affected files/functions | "
            "Blocking status | Disposition | Recommended fix |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            "| EXT-GITMETA-### | critical/high/medium/low/informational | git metadata | "
            "path/function | blocking/should-fix/later/advisory | open | fix summary |",
        ]
    )
    return f"""# git.show.commit_metadata Source Review Prompt

You are reviewing Ithildin as an external source reviewer for the `git.show.commit_metadata` lane
only. Treat this as source-level review if and only if you inspect the attached source bundle,
focused tests, parity fixture, contract docs, implementation packet, and command evidence.

Reviewed commit: `{context["commit"]}`
Reviewed implementation packet hash: `{context["implementation_packet_sha256"]}`
Area: `git-commit-metadata`
Finding namespace: `EXT-GITMETA-###`

## Scope

Please review:

- manifest/schema shape, including structured `ref` input, `additionalProperties: false`, read risk,
  and absence of caller-controlled argv, format strings, pathspecs, diff flags, checkout, remotes,
  headers, or bodies;
- ref validation for full object IDs, local branches, and local tags, including denial of
  option-like refs, revision operators, remote refs, path traversal, whitespace/control characters,
  and ambiguous syntax;
- fixed Git argv behavior and subprocess handling, including no shell, no checkout, no mutation, no
  remote fetch, safe decoding, and no raw stderr leakage;
- output safety: bounded subject/body, untrusted metadata labeling, control/format-character
  sanitization, email redaction plus hashes, changed-file metadata limits, hidden/sensitive path
  redaction, and no raw diffs/file/blob contents;
- policy preview/runtime parity for the syntactic `git_commit` resource and the governed-call audit
  path for success, denial, and safe failure;
- MCP exposure and role visibility staying routed through the existing registry/governed pipeline;
- no-new-powers and tool-surface gates continuing to allow only this bounded read-only Git metadata
  addition.

## Required Disposition

Please answer whether the `git.show.commit_metadata` lane can be externally closed for the v0.1
local-preview runtime boundary. If it cannot close, explain exactly which source/test/evidence item
is missing or which implementation issue blocks closure.

Use this exact finding table shape for actionable findings:

{finding_table}

If there are no implementation findings, explicitly say so and state whether the lane can close for
local-preview `git.show.commit_metadata`. Do not approve arbitrary Git execution, raw diffs, file
contents, checkout, branch mutation, remote fetch, public/security-product positioning, or future
governed tool powers.
"""


def _implementation_packet(
    repo_root: Path, commit: str, dirty: bool, *, run_commands: bool
) -> str:
    report = _command_output(
        ["uv", "run", "python", "scripts/git_commit_metadata_implementation_gate.py", "--json"],
        run_commands=run_commands,
    )
    return "\n".join(
        [
            "# git.show.commit_metadata Implementation Packet",
            "",
            f"- Reviewed commit: `{commit}`",
            f"- Dirty at generation: `{str(dirty).lower()}`",
            "- Tool: `git.show.commit_metadata`",
            "- Status: approved v0.9 implementation for one bounded read-only Git metadata tool.",
            "- Boundary: no shell, no caller-controlled Git argv/format/pathspecs, no checkout, no",
            "  branch mutation, no remote fetch, no raw diffs, no file contents, no broad",
            "  filesystem access, and no future tool-power approval.",
            "",
            "## Implementation Gate JSON",
            "",
            "```json",
            str(report["stdout"]).rstrip(),
            "```",
            "",
            "## Implementation Record",
            "",
            _read(repo_root / "docs/codex/v0.9-git-commit-metadata-implementation.md").rstrip(),
            "",
            "## Internal Checkpoint Note",
            "",
            "A high-intelligence internal checkpoint review found no critical/high blocker and",
            "raised medium/low concerns about NUL-delimited changed-file parsing, raw email",
            "output, untrusted metadata labeling, and subprocess output handling. Those were",
            "remediated before this source-review handoff. External review should still inspect",
            "those areas directly.",
        ]
    )


def _intake_commands(context: dict[str, Any]) -> str:
    return f"""# git.show.commit_metadata External Review Intake Commands

Store the raw external review response at:

```text
var/review-runs/v0.9/git-commit-metadata/raw-response.md
```

Normalize it with:

```bash
uv run python scripts/external_response_normalize.py \\
  var/review-runs/v0.9/git-commit-metadata/raw-response.md \\
  --reviewer "GPT 5.5 Pro" \\
  --reviewer-type "external-model" \\
  --source-access "source-level" \\
  --reviewed-commit "{context["commit"]}" \\
  --reviewed-packet-hash "{context["implementation_packet_sha256"]}" \\
  --area "git-commit-metadata" \\
  --output var/review-runs/v0.9/git-commit-metadata/normalized-response.json
```

The normalizer accepts `EXT-GITMETA-###` finding IDs for this lane. Normalized output does not
mutate finding records and does not close external review rows.

After normalization and any finding-record updates, run:

```bash
make reviewer-findings-check
make review-findings-summary
make external-review-closure-gate
make release-check
```

If critical/high findings are present, stop unrelated capability work and create structured finding
records before remediation.
"""


def _require_project_root(repo_root: Path) -> None:
    for marker in external_review_dispatch_packets.PROJECT_MARKERS:
        if not (repo_root / marker).exists():
            raise GitCommitMetadataSourceReviewBundleError(f"missing project marker: {marker}")


def _bundle_sources(repo_root: Path, paths: list[Path]) -> str:
    sections: list[str] = []
    for relative in paths:
        path = repo_root / relative
        if not path.exists():
            raise GitCommitMetadataSourceReviewBundleError(
                f"required source is missing: {relative}"
            )
        suffix = path.suffix.lstrip(".") or "text"
        sections.append(
            "\n".join(
                [
                    f"# {relative.as_posix()}",
                    "",
                    f"```{suffix}",
                    path.read_text(encoding="utf-8").rstrip(),
                    "```",
                    "",
                ]
            )
        )
    return "\n---\n\n".join(sections)


def _command_output(command: list[str], *, run_commands: bool) -> dict[str, Any]:
    if not run_commands:
        return {
            "command": command,
            "returncode": 0,
            "stdout": "skipped by test harness\n",
            "stderr": "",
        }
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise GitCommitMetadataSourceReviewBundleError(f"{' '.join(command)} failed")
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _write_command_output(path: Path, output: dict[str, Any]) -> None:
    path.write_text(
        "\n".join(
            [
                f"$ {' '.join(output['command'])}",
                f"returncode={output['returncode']}",
                "",
                "## stdout",
                str(output["stdout"]).rstrip(),
                "",
                "## stderr",
                str(output["stderr"]).rstrip(),
                "",
            ]
        ),
        encoding="utf-8",
    )


def _evidence(gate_output: dict[str, Any], parity_output: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# git.show.commit_metadata Evidence",
            "",
            "## Boundary Summary",
            "",
            "- `git.show.commit_metadata` is a bounded read-only Git metadata tool.",
            "- The manifest accepts structured ref selectors and rejects caller-controlled argv,",
            "  format strings, pathspecs, checkout, remotes, headers, bodies, and raw diff flags.",
            "- Runtime review should verify fixed Git argv, safe ref validation, bounded metadata,",
            "  email redaction, untrusted metadata labeling, hidden/sensitive path redaction,",
            "  and no file/blob content exposure.",
            "- Policy preview/runtime parity uses a syntactic `git_commit` resource and writes no",
            "  preview audit events.",
            "- Capability expansion remains limited to this one read-risk Git metadata addition.",
            "",
            "## make git-commit-metadata-implementation-gate",
            "",
            f"$ {' '.join(gate_output['command'])}",
            f"returncode={gate_output['returncode']}",
            "",
            "### stdout",
            str(gate_output["stdout"]).rstrip(),
            "",
            "### stderr",
            str(gate_output["stderr"]).rstrip(),
            "",
            "## make policy-parity",
            "",
            f"$ {' '.join(parity_output['command'])}",
            f"returncode={parity_output['returncode']}",
            "",
            "### stdout",
            str(parity_output["stdout"]).rstrip(),
            "",
            "### stderr",
            str(parity_output["stderr"]).rstrip(),
            "",
        ]
    )


def _hashes(output_dir: Path) -> list[dict[str, Any]]:
    hashes: list[dict[str, Any]] = []
    for path in sorted(output_dir.glob("*")):
        if path.name == "git-commit-metadata-source-review-artifact-hashes.json":
            continue
        content = path.read_bytes()
        hashes.append(
            {
                "path": path.name,
                "sha256": "sha256:" + hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
            }
        )
    return hashes


def _read(path: Path) -> str:
    if not path.exists():
        raise GitCommitMetadataSourceReviewBundleError(f"required packet source is missing: {path}")
    return path.read_text(encoding="utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


if __name__ == "__main__":
    raise SystemExit(main())

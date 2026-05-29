"""Build an ignored v0.2 external-review handoff bundle."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

PROJECT_MARKERS = (
    "pyproject.toml",
    "Makefile",
    "apps/api",
    "apps/mcp-server",
    "tool-manifests.lock.json",
)

REVIEW_DOCS = [
    "README.md",
    "docs/codex/v0.2-review-response-and-rc-cleanup.md",
    "docs/codex/v0.2-review-packet.md",
    "docs/codex/v0.2-external-review-prompt.md",
    "docs/codex/v0.2-planning-seed.md",
    "docs/codex/v0.1-security-test-matrix.md",
    "docs/codex/evidence-contracts.md",
    "docs/codex/threat-model-and-non-goals.md",
    "docs/codex/local-preview-release.md",
    "docs/codex/mcp-client-examples.md",
    "docs/codex/mcp-inspector-recipes.md",
    "docs/codex/signed-audit-exports.md",
    "docs/codex/signed-manifest-locks.md",
    "docs/research/source-verification.md",
]


class BundleError(RuntimeError):
    """Raised for release-bundle failures that should be shown to the operator."""


@dataclass(frozen=True)
class CommandOutput:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class BundleResult:
    path: Path
    commit: str
    release_check_status: str


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        default="var/review-packets/v0.2",
        help="directory under which the bundle directory will be created",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="allow draft bundle generation from a dirty working tree",
    )
    args = parser.parse_args()

    try:
        result = build_bundle(
            repo_root=Path.cwd().resolve(),
            output_root=Path(args.output_root),
            allow_dirty=args.allow_dirty,
            run_release_check=True,
        )
    except BundleError as exc:
        print(f"review packet bundle failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built review packet bundle at {result.path}")
    print(f"commit={result.commit}")
    print(f"release_check={result.release_check_status}")
    return 0


def build_bundle(
    *,
    repo_root: Path,
    output_root: Path,
    allow_dirty: bool,
    run_release_check: bool,
) -> BundleResult:
    marker_status = _project_marker_status(repo_root)
    missing_markers = [
        marker for marker, present in marker_status.items() if not present
    ]
    if missing_markers:
        raise BundleError(
            "must be run from the Ithildin repo root; "
            f"missing markers: {', '.join(missing_markers)}"
        )

    dirty_status = _git(["status", "--short"])
    if dirty_status and not allow_dirty:
        raise BundleError("working tree is dirty; commit changes or use --allow-dirty for drafts")

    commit = _git(["rev-parse", "HEAD"])
    short_commit = commit[:12]
    bundle_dir = output_root / f"ithildin-v0.2-review-packet-{short_commit}"
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True)

    if run_release_check:
        release_check = _run_capture(["make", "release-check"])
    else:
        release_check = CommandOutput(
            command=["make", "release-check"],
            returncode=0,
            stdout="skipped by test harness\n",
            stderr="",
        )
    _write_command_output(bundle_dir / "release-check.txt", release_check)
    if release_check.returncode != 0:
        raise BundleError("make release-check failed; see release-check.txt")

    _write_command_output(
        bundle_dir / "release-evidence.json",
        _required_command(["uv", "run", "python", "scripts/release_evidence.py"]),
    )
    _write_command_output(
        bundle_dir / "release-packet.md",
        _required_command(["uv", "run", "python", "scripts/release_packet.py"]),
    )
    _write_command_output(
        bundle_dir / "release-packet.json",
        _required_command(["uv", "run", "python", "scripts/release_packet.py", "--json"]),
    )
    _write_git_summary(bundle_dir / "git-summary.txt", repo_root, commit, dirty_status)
    _copy_review_docs(repo_root, bundle_dir)
    _write_index(bundle_dir, commit, marker_status, allow_dirty)

    return BundleResult(
        path=bundle_dir,
        commit=commit,
        release_check_status="passed",
    )


def _project_marker_status(repo_root: Path) -> dict[str, bool]:
    return {marker: repo_root.joinpath(marker).exists() for marker in PROJECT_MARKERS}


def _required_command(command: list[str]) -> CommandOutput:
    output = _run_capture(command)
    if output.returncode != 0:
        raise BundleError(f"{' '.join(command)} failed")
    return output


def _run_capture(command: list[str]) -> CommandOutput:
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    return CommandOutput(
        command=command,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _write_command_output(path: Path, output: CommandOutput) -> None:
    path.write_text(
        "\n".join(
            [
                f"$ {' '.join(output.command)}",
                f"returncode={output.returncode}",
                "",
                "## stdout",
                output.stdout.rstrip(),
                "",
                "## stderr",
                output.stderr.rstrip(),
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_git_summary(
    path: Path,
    repo_root: Path,
    commit: str,
    dirty_status: str,
) -> None:
    branch = _git(["branch", "--show-current"])
    log = _git(["log", "-12", "--oneline"])
    path.write_text(
        "\n".join(
            [
                f"repo_root={repo_root.as_posix()}",
                f"commit={commit}",
                f"branch={branch}",
                f"dirty={str(bool(dirty_status)).lower()}",
                "",
                "recent_commits:",
                log,
                "",
            ]
        ),
        encoding="utf-8",
    )


def _copy_review_docs(repo_root: Path, bundle_dir: Path) -> None:
    for doc in REVIEW_DOCS:
        source = repo_root / doc
        if not source.exists():
            raise BundleError(f"review document is missing: {doc}")
        destination = bundle_dir / "docs" / doc
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _write_index(
    bundle_dir: Path,
    commit: str,
    marker_status: dict[str, bool],
    allow_dirty: bool,
) -> None:
    docs_list = "\n".join(f"- `docs/{doc}`" for doc in REVIEW_DOCS)
    markers = "\n".join(
        f"- `{marker}`: `{str(present).lower()}`"
        for marker, present in marker_status.items()
    )
    bundle_dir.joinpath("INDEX.md").write_text(
        f"""# Ithildin v0.2 Review Bundle

Generated at: `{datetime.now(UTC).isoformat()}`

Commit: `{commit}`

Draft dirty-tree mode: `{str(allow_dirty).lower()}`

## What To Send

Send this bundle to GPT 5.5 Pro / Very High or a human expert reviewer. Start with:

- `docs/docs/codex/v0.2-review-response-and-rc-cleanup.md`
- `docs/docs/codex/v0.2-review-packet.md`
- `docs/docs/codex/v0.2-external-review-prompt.md`
- `release-check.txt`
- `release-evidence.json`
- `release-packet.md`
- `release-packet.json`
- `git-summary.txt`

## Included Review Documents

{docs_list}

## Project Markers

{markers}

## Exclusions

This bundle intentionally excludes `.env`, private keys, local signatures, node modules, UI build
output, SQLite databases, audit JSONL state, and other runtime files. Evidence files are generated
through secret-free release scripts.
""",
        encoding="utf-8",
    )


def _git(args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())

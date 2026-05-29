"""Build an ignored v0.2 external-review handoff bundle."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.review_docs import REVIEW_DOCS, ReviewDocMetadata, collect_review_doc_metadata

BUNDLE_DOCS = [
    *REVIEW_DOCS,
    "docs/codex/mcp-client-examples.md",
    "docs/codex/mcp-inspector-recipes.md",
    "docs/codex/signed-audit-exports.md",
    "docs/codex/signed-manifest-locks.md",
    "docs/research/source-verification.md",
]

PROJECT_MARKERS = (
    "pyproject.toml",
    "Makefile",
    "apps/api",
    "apps/mcp-server",
    "tool-manifests.lock.json",
)

SIGNED_EVIDENCE_DEMO_SUMMARY = Path(
    "var/review-packets/v0.2/signed-evidence-demo/SIGNED_EVIDENCE_DEMO.md"
)

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

    review_doc_hashes = collect_review_doc_metadata(repo_root, REVIEW_DOCS)
    _write_json(bundle_dir / "review-doc-hashes.json", review_doc_hashes)
    _write_command_output(
        bundle_dir / "release-evidence.json",
        _required_command(
            [
                "uv",
                "run",
                "python",
                "scripts/release_evidence.py",
                "--release-check-transcript",
                (bundle_dir / "release-check.txt").as_posix(),
                "--release-check-observed-status",
                "passed",
                "--release-check-commit",
                commit,
            ]
        ),
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
    signed_demo_included = _copy_signed_evidence_demo_summary(repo_root, bundle_dir)
    _write_index(
        bundle_dir,
        commit,
        marker_status,
        allow_dirty,
        review_doc_hashes,
        signed_demo_included,
    )
    artifact_hashes = _collect_artifact_hashes(
        bundle_dir=bundle_dir,
        review_docs=BUNDLE_DOCS,
        signed_demo_included=signed_demo_included,
    )
    _write_json(bundle_dir / "artifact-hashes.json", artifact_hashes)

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


def _write_json(path: Path, value: Any) -> None:
    import json

    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
    for doc in BUNDLE_DOCS:
        source = repo_root / doc
        if not source.exists():
            raise BundleError(f"review document is missing: {doc}")
        destination = bundle_dir / "docs" / doc
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _copy_signed_evidence_demo_summary(repo_root: Path, bundle_dir: Path) -> bool:
    source = repo_root / SIGNED_EVIDENCE_DEMO_SUMMARY
    if not source.exists():
        return False
    destination = bundle_dir / "signed-evidence-demo" / "SIGNED_EVIDENCE_DEMO.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return True


def _collect_artifact_hashes(
    *,
    bundle_dir: Path,
    review_docs: list[str],
    signed_demo_included: bool,
) -> list[dict[str, Any]]:
    paths = [
        Path("INDEX.md"),
        Path("release-check.txt"),
        Path("release-evidence.json"),
        Path("release-packet.md"),
        Path("release-packet.json"),
        Path("review-doc-hashes.json"),
        Path("git-summary.txt"),
    ]
    paths.extend(Path("docs") / doc for doc in review_docs)
    if signed_demo_included:
        paths.append(Path("signed-evidence-demo/SIGNED_EVIDENCE_DEMO.md"))

    artifacts: list[dict[str, Any]] = []
    for relative_path in paths:
        artifact_path = bundle_dir / relative_path
        if not artifact_path.exists():
            raise BundleError(f"bundle artifact is missing: {relative_path.as_posix()}")
        content = artifact_path.read_bytes()
        artifacts.append(
            {
                "path": relative_path.as_posix(),
                "sha256": "sha256:" + hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
            }
        )
    return artifacts


def _write_index(
    bundle_dir: Path,
    commit: str,
    marker_status: dict[str, bool],
    allow_dirty: bool,
    review_doc_hashes: list[ReviewDocMetadata],
    signed_demo_included: bool,
) -> None:
    docs_list = "\n".join(f"- `docs/{doc}`" for doc in BUNDLE_DOCS)
    doc_hashes = "\n".join(
        f"- `{doc['path']}` `{doc['sha256']}` `{doc['bytes']} bytes`"
        for doc in review_doc_hashes
    )
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
- `review-doc-hashes.json`
- `artifact-hashes.json`
- `signed-evidence-demo/SIGNED_EVIDENCE_DEMO.md` if `make signed-evidence-demo` was run first
- `git-summary.txt`

## Included Review Documents

{docs_list}

## Review Document Hashes

{doc_hashes}

## Locally Signed Evidence Demo

included: `{str(signed_demo_included).lower()}`

Runtime audit signing and manifest-lock signing may be unconfigured by default. Run
`make signed-evidence-demo` before `make review-packet-bundle` to include the separate
non-production fixture summary. That demo proves the local signing and verification flow only; it is
not external notarization, hosted custody, or official supply-chain signing.

## Bundle Artifact Hashes

See `artifact-hashes.json` for SHA-256 digests of the generated bundle outputs, copied review
documents, and copied signed-evidence demo summary when present.

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

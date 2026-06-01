"""Build a focused filesystem/platform external source-review bundle."""

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

from ithildin_api.filesystem_contract import collect_filesystem_contract_status

try:
    from scripts import external_review_dispatch_packets
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    import external_review_dispatch_packets  # type: ignore[import-not-found,no-redef]

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v0.7/filesystem-source-review")
DISPATCH_ROOT = Path("var/review-packets/v0.6/dispatch")

SOURCE_FILES = [
    Path("apps/api/src/ithildin_api/read_tools.py"),
    Path("apps/api/src/ithildin_api/workspaces.py"),
    Path("apps/api/src/ithildin_api/filesystem_contract.py"),
    Path("apps/api/src/ithildin_api/patches.py"),
    Path("apps/api/src/ithildin_api/app.py"),
    Path("apps/api/src/ithildin_api/security_status.py"),
    Path("scripts/filesystem_contract_check.py"),
]

TEST_FILES = [
    Path("tests/test_read_tools.py"),
    Path("tests/test_patch_proposals.py"),
    Path("tests/test_security_regressions.py"),
    Path("tests/test_workspaces.py"),
    Path("tests/test_filesystem_contract_check.py"),
    Path("tests/test_api_service.py"),
]

CONTRACT_DOCS = [
    Path("docs/codex/filesystem-executor-contract.md"),
    Path("docs/codex/filesystem-source-review-checklist.md"),
    Path("docs/codex/v0.7-filesystem-platform-source-review.md"),
    Path("docs/codex/source-review-closure-matrix.md"),
    Path("docs/codex/v0.6-lane-status-board.md"),
]

FOCUSED_TEST_COMMAND = [
    "uv",
    "run",
    "pytest",
    "tests/test_read_tools.py",
    "tests/test_patch_proposals.py",
    "tests/test_security_regressions.py",
    "tests/test_workspaces.py",
    "tests/test_filesystem_contract_check.py",
    "-q",
]


class FilesystemSourceReviewBundleError(RuntimeError):
    """Raised when the filesystem source-review bundle cannot be built."""


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
    except FilesystemSourceReviewBundleError as exc:
        print(f"filesystem source-review bundle failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built filesystem source-review bundle at {output_dir}")
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
        raise FilesystemSourceReviewBundleError(
            "working tree is dirty; commit before source-review handoff"
        )

    _build_dispatch_packets(repo_root, repo_root / DISPATCH_ROOT)
    dispatch_manifest_path = repo_root / DISPATCH_ROOT / "dispatch-packet-hashes.json"
    dispatch_manifest = json.loads(dispatch_manifest_path.read_text(encoding="utf-8"))
    filesystem_packet = _packet_metadata(dispatch_manifest)

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context: dict[str, Any] = {
        "commit": commit,
        "dirty": dirty,
        "dispatch_manifest_path": DISPATCH_ROOT / "dispatch-packet-hashes.json",
        "filesystem_packet_path": DISPATCH_ROOT / filesystem_packet["path"],
        "filesystem_packet_sha256": filesystem_packet["sha256"],
        "filesystem_packet_payload_sha256": filesystem_packet["payload_sha256"],
    }

    files: dict[str, str] = {
        "00_FILESYSTEM_SOURCE_REVIEW_INDEX.md": _index(context),
        "01_FILESYSTEM_SOURCE_REVIEW_PROMPT.md": _prompt(context),
        "02_FILESYSTEM_DISPATCH_PACKET.md": _read(
            repo_root / context["filesystem_packet_path"]
        ),
        "03_FILESYSTEM_SOURCE_BUNDLE.md": _bundle_sources(repo_root, SOURCE_FILES),
        "04_FILESYSTEM_TESTS_BUNDLE.md": _bundle_sources(repo_root, TEST_FILES),
        "05_FILESYSTEM_CONTRACTS_BUNDLE.md": _bundle_sources(repo_root, CONTRACT_DOCS),
        "08_FILESYSTEM_INTAKE_COMMANDS.md": _intake_commands(context),
    }
    for relative, content in files.items():
        (output_dir / relative).write_text(content.rstrip() + "\n", encoding="utf-8")

    contract_check = _command_output(
        ["make", "filesystem-contract-check"], run_commands=run_commands
    )
    status_evidence = {
        "evidence_type": "ithildin.filesystem_status_evidence",
        "system_status_path": "/system/status.filesystem",
        "source_files": [
            "apps/api/src/ithildin_api/app.py",
            "apps/api/src/ithildin_api/filesystem_contract.py",
        ],
        "filesystem": collect_filesystem_contract_status(),
    }
    (output_dir / "06_FILESYSTEM_EVIDENCE.md").write_text(
        _filesystem_evidence(contract_check, status_evidence).rstrip() + "\n",
        encoding="utf-8",
    )
    _write_command_output(
        output_dir / "07_FILESYSTEM_FOCUSED_TESTS.txt",
        _command_output(FOCUSED_TEST_COMMAND, run_commands=run_commands),
    )
    _write_json(output_dir / "filesystem-source-review-artifact-hashes.json", _hashes(output_dir))
    return output_dir


def _index(context: dict[str, Any]) -> str:
    return f"""# Filesystem and Platform Source Review Handoff

This packet directly answers `EXT-FS-001`: the previous consolidated packet was ready for
filesystem/platform source review but did not attach the implementation and focused tests required
for external source-level closure.

## Boundary

- Current review status: v0.6/v0.7 external-review closure work for the v0.1 local-preview runtime
  boundary.
- Lane: filesystem/platform.
- Finding namespace: `EXT-FS-###`.
- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Dispatch packet path: `{context["filesystem_packet_path"]}`.
- Dispatch packet whole-file SHA-256: `{context["filesystem_packet_sha256"]}`.
- Dispatch packet payload SHA-256: `{context["filesystem_packet_payload_sha256"]}`.

## Send These Files

1. `00_FILESYSTEM_SOURCE_REVIEW_INDEX.md`
2. `01_FILESYSTEM_SOURCE_REVIEW_PROMPT.md`
3. `02_FILESYSTEM_DISPATCH_PACKET.md`
4. `03_FILESYSTEM_SOURCE_BUNDLE.md`
5. `04_FILESYSTEM_TESTS_BUNDLE.md`
6. `05_FILESYSTEM_CONTRACTS_BUNDLE.md`
7. `06_FILESYSTEM_EVIDENCE.md`
8. `07_FILESYSTEM_FOCUSED_TESTS.txt`
9. `08_FILESYSTEM_INTAKE_COMMANDS.md`
10. `filesystem-source-review-artifact-hashes.json`

## What This Does Not Prove

This packet does not close external review rows, approve public/security-product positioning,
approve capability expansion, or prove production security. It provides the source/test evidence
needed for an external reviewer to decide whether the filesystem/platform lane can be closed for
the v0.1 local-preview boundary.
"""


def _prompt(context: dict[str, Any]) -> str:
    finding_table = "\n".join(
        [
            "| Finding ID | Severity | Area | Affected files/functions | "
            "Blocking status | Disposition | Recommended fix |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            "| EXT-FS-### | critical/high/medium/low/informational | filesystem/platform | "
            "path/function | blocking/should-fix/later/advisory | open | fix summary |",
        ]
    )
    return f"""# Filesystem and Platform Source Review Prompt

You are reviewing Ithildin as an external source reviewer for the filesystem/platform lane only.
Treat this as source-level review if and only if you inspect the attached source bundle, focused
tests, contract docs, and command evidence.

Reviewed commit: `{context["commit"]}`
Reviewed dispatch packet hash: `{context["filesystem_packet_sha256"]}`
Reviewed dispatch payload hash: `{context["filesystem_packet_payload_sha256"]}`
Area: `filesystem`
Finding namespace: `EXT-FS-###`

## Scope

Please review:

- workspace confinement and workspace registry behavior;
- path normalization and relative-path-only assumptions;
- hidden/sensitive path denial, `.git` denial, symlink denial, and hardlink denial;
- read/propose/apply race assumptions and same-directory atomic replace behavior;
- Unicode/control-character, case-sensitivity, binary/encoding, and size-limit behavior;
- macOS/Linux support claims and Windows/WSL unsupported posture;
- `/system/status` filesystem-support evidence and `make filesystem-contract-check`.

## Required Disposition

Please answer whether the filesystem/platform lane can be externally closed for the v0.1
local-preview runtime boundary. If it cannot close, explain exactly which source/test/evidence item
is missing or which implementation issue blocks closure.

Use this exact finding table shape for actionable findings:

{finding_table}

If there are no implementation findings, explicitly say so and state whether `EXT-FS-001` is closed
as a process/evidence issue by this source bundle. Do not approve capability expansion, public
security-product positioning, Windows/WSL security claims, remote filesystem claims, or any new
governed tool powers.
"""


def _intake_commands(context: dict[str, Any]) -> str:
    return f"""# Filesystem External Review Intake Commands

Store the raw external review response at:

```text
var/review-runs/v0.7/filesystem/raw-response.md
```

Normalize it with:

```bash
uv run python scripts/external_response_normalize.py \\
  var/review-runs/v0.7/filesystem/raw-response.md \\
  --reviewer "GPT 5.5 Pro" \\
  --reviewer-type "external-model" \\
  --source-access "source-level" \\
  --reviewed-commit "{context["commit"]}" \\
  --reviewed-packet-hash "{context["filesystem_packet_sha256"]}" \\
  --area "filesystem" \\
  --output var/review-runs/v0.7/filesystem/normalized-response.json
```

The normalizer accepts `EXT-FS-###` finding IDs for this lane. Normalized output does not mutate
finding records and does not close external review rows.

After normalization and any finding-record updates, run:

```bash
make reviewer-findings-check
make review-findings-summary
make external-review-closure-gate
make v06-lane-status
make release-check
```

If critical/high findings are present, stop unrelated work and create structured finding records
before remediation.
"""


def _require_project_root(repo_root: Path) -> None:
    for marker in external_review_dispatch_packets.PROJECT_MARKERS:
        if not (repo_root / marker).exists():
            raise FilesystemSourceReviewBundleError(f"missing project marker: {marker}")


def _build_dispatch_packets(repo_root: Path, output_root: Path) -> dict[str, Any]:
    return external_review_dispatch_packets.build_dispatch_packets(repo_root, output_root)


def _packet_metadata(dispatch_manifest: dict[str, Any]) -> dict[str, Any]:
    for packet in dispatch_manifest.get("packets", []):
        if packet.get("path") == "filesystem.md":
            return dict(packet)
    raise FilesystemSourceReviewBundleError("filesystem dispatch packet metadata is missing")


def _bundle_sources(repo_root: Path, paths: list[Path]) -> str:
    sections: list[str] = []
    for relative in paths:
        path = repo_root / relative
        if not path.exists():
            raise FilesystemSourceReviewBundleError(f"required source is missing: {relative}")
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
        raise FilesystemSourceReviewBundleError(f"{' '.join(command)} failed")
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


def _filesystem_evidence(command_output: dict[str, Any], status_evidence: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Filesystem Evidence",
            "",
            "## make filesystem-contract-check",
            "",
            f"$ {' '.join(command_output['command'])}",
            f"returncode={command_output['returncode']}",
            "",
            "### stdout",
            str(command_output["stdout"]).rstrip(),
            "",
            "### stderr",
            str(command_output["stderr"]).rstrip(),
            "",
            "## /system/status.filesystem Evidence",
            "",
            "The API `/system/status` route embeds this filesystem capability evidence under the",
            "`filesystem` key. This bundle includes the direct collector output so review does not",
            "require starting a local API server.",
            "",
            "```json",
            json.dumps(status_evidence, indent=2, sort_keys=True),
            "```",
            "",
        ]
    )


def _hashes(output_dir: Path) -> list[dict[str, Any]]:
    hashes: list[dict[str, Any]] = []
    for path in sorted(output_dir.glob("*")):
        if path.name == "filesystem-source-review-artifact-hashes.json":
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
        raise FilesystemSourceReviewBundleError(f"required packet source is missing: {path}")
    return path.read_text(encoding="utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


if __name__ == "__main__":
    raise SystemExit(main())

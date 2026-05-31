"""Build a focused patch-apply external/source-review handoff packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

try:
    from scripts import external_review_dispatch_packets
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    import external_review_dispatch_packets  # type: ignore[import-not-found,no-redef]

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v0.6/patch-apply-external-review")
DISPATCH_ROOT = Path("var/review-packets/v0.6/dispatch")

SOURCE_FILES = [
    Path("apps/api/src/ithildin_api/patches.py"),
    Path("apps/api/src/ithildin_api/approvals.py"),
    Path("apps/api/src/ithildin_api/tool_calls.py"),
]
TEST_FILES = [
    Path("tests/test_patch_proposals.py"),
    Path("tests/test_approval_workflow.py"),
    Path("tests/test_governed_tool_calls.py"),
    Path("tests/test_security_regressions.py"),
]
CONTRACT_DOCS = [
    Path("docs/codex/patch-apply-source-review-checklist.md"),
    Path("docs/codex/patch-apply-state-machine.md"),
    Path("docs/codex/filesystem-executor-contract.md"),
    Path("docs/codex/source-file-inspection-packet.md"),
    Path("docs/codex/v0.6-closure-handoff.md"),
]


class PatchApplyReviewPacketError(RuntimeError):
    """Raised when the patch-apply external-review packet cannot be built."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()

    try:
        output_dir = build_packet(
            repo_root=Path.cwd().resolve(),
            output_dir=args.output_dir,
            allow_dirty=args.allow_dirty,
        )
    except PatchApplyReviewPacketError as exc:
        print(f"patch-apply external review packet failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built patch apply external review packet at {output_dir}")
    return 0


def build_packet(*, repo_root: Path, output_dir: Path, allow_dirty: bool = False) -> Path:
    _require_project_root(repo_root)
    commit = _git(repo_root, ["rev-parse", "HEAD"])
    dirty = bool(_git(repo_root, ["status", "--short"]))
    if dirty and not allow_dirty:
        raise PatchApplyReviewPacketError("working tree is dirty; commit before handoff")

    _build_dispatch_packets(repo_root, repo_root / DISPATCH_ROOT)
    dispatch_manifest_path = repo_root / DISPATCH_ROOT / "dispatch-packet-hashes.json"
    dispatch_manifest = json.loads(dispatch_manifest_path.read_text(encoding="utf-8"))
    patch_packet = _packet_metadata(dispatch_manifest)

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context = {
        "commit": commit,
        "dirty": dirty,
        "dispatch_manifest_path": DISPATCH_ROOT / "dispatch-packet-hashes.json",
        "patch_packet_path": DISPATCH_ROOT / patch_packet["path"],
        "patch_packet_sha256": patch_packet["sha256"],
        "patch_packet_payload_sha256": patch_packet["payload_sha256"],
    }
    files: dict[str, str] = {
        "00_PATCH_APPLY_EXTERNAL_REVIEW_INDEX.md": _index(context),
        "01_PATCH_APPLY_EXTERNAL_REVIEW_PROMPT.md": _prompt(context),
        "02_PATCH_APPLY_DISPATCH_PACKET.md": _read(repo_root / context["patch_packet_path"]),
        "03_PATCH_APPLY_SOURCE_BUNDLE.md": _bundle_sources(repo_root, SOURCE_FILES),
        "04_PATCH_APPLY_TESTS_BUNDLE.md": _bundle_sources(repo_root, TEST_FILES),
        "05_PATCH_APPLY_CONTRACTS_BUNDLE.md": _bundle_sources(repo_root, CONTRACT_DOCS),
        "06_PATCH_APPLY_INTAKE_COMMANDS.md": _intake_commands(context),
    }
    for relative, content in files.items():
        (output_dir / relative).write_text(content.rstrip() + "\n", encoding="utf-8")
    _write_json(output_dir / "patch-apply-review-artifact-hashes.json", _hashes(output_dir))
    return output_dir


def _require_project_root(repo_root: Path) -> None:
    for marker in external_review_dispatch_packets.PROJECT_MARKERS:
        if not (repo_root / marker).exists():
            raise PatchApplyReviewPacketError(f"missing project marker: {marker}")


def _build_dispatch_packets(repo_root: Path, output_root: Path) -> dict[str, Any]:
    return external_review_dispatch_packets.build_dispatch_packets(repo_root, output_root)


def _packet_metadata(dispatch_manifest: dict[str, Any]) -> dict[str, Any]:
    for packet in dispatch_manifest.get("packets", []):
        if packet.get("path") == "patch-apply.md":
            return cast(dict[str, Any], packet)
    raise PatchApplyReviewPacketError("patch-apply dispatch packet metadata is missing")


def _index(context: dict[str, Any]) -> str:
    return f"""# Patch Apply External Review Handoff

This packet is the first v0.6 external/source-review execution lane. It is scoped to
`fs.patch.apply`, Ithildin's only local-preview write path.

## Boundary

- Current review status: v0.6 external/source-review handoff for the v0.1 local-preview runtime
  boundary.
- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Dispatch packet path: `{context["patch_packet_path"]}`.
- Dispatch packet whole-file SHA-256: `{context["patch_packet_sha256"]}`.
- Dispatch packet payload SHA-256: `{context["patch_packet_payload_sha256"]}`.

## Send These Files

1. `00_PATCH_APPLY_EXTERNAL_REVIEW_INDEX.md`
2. `01_PATCH_APPLY_EXTERNAL_REVIEW_PROMPT.md`
3. `02_PATCH_APPLY_DISPATCH_PACKET.md`
4. `03_PATCH_APPLY_SOURCE_BUNDLE.md`
5. `04_PATCH_APPLY_TESTS_BUNDLE.md`
6. `05_PATCH_APPLY_CONTRACTS_BUNDLE.md`
7. `06_PATCH_APPLY_INTAKE_COMMANDS.md`
8. `patch-apply-review-artifact-hashes.json`

## What This Does Not Prove

This packet does not close external review rows, create EXT findings, approve public preview,
approve capability expansion, or prove production readiness. It prepares the source-level review
input for an external reviewer.
"""


def _prompt(context: dict[str, Any]) -> str:
    finding_table = "\n".join(
        [
            "| Finding ID | Severity | Area | Affected files/functions | "
            "Blocking status | Disposition | Recommended fix |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            "| EXT-PA-### | critical/high/medium/low/informational | patch-apply | "
            "path/function | blocking/should-fix/later/advisory | open | fix summary |",
        ]
    )
    return f"""# Patch Apply Source Review Prompt

You are reviewing Ithildin as an external source reviewer for the patch-apply lane only. Treat this
as source-level review if and only if you inspect the attached source bundle and tests.

Reviewed commit: `{context["commit"]}`
Reviewed dispatch packet hash: `{context["patch_packet_sha256"]}`
Reviewed dispatch payload hash: `{context["patch_packet_payload_sha256"]}`
Area: `patch-apply`
Finding namespace: `EXT-PA-###`

## Scope

Review the stored-proposal-only `fs.patch.apply` flow:

- proposal binding and proposal hash checks;
- approval scope, request hash, expiry, and one-time execution;
- policy/manifest/schema/principal drift checks;
- stale-base rejection before file replacement;
- same-directory temporary replacement behavior;
- failure evidence before replacement, after replacement, and before completion;
- replay denial and stuck/incomplete apply diagnostics;
- safe audit metadata with no file contents, diff contents, tokens, private keys, or secrets.

## Required Response

Please answer with:

- overall judgment;
- blockers before external patch-apply closure;
- blockers before broader public/security-product positioning;
- should-fix items;
- residual risks or accepted-deferred candidates;
- finding table.

Use this exact finding table shape for actionable findings:

{finding_table}

If there are no findings, explicitly say so. Do not mark external review rows closed yourself; the
project will normalize and ingest your response separately.

## Stop Conditions

Call out any critical/high implementation finding clearly. Capability expansion and public/security
positioning remain blocked regardless of this review outcome.
"""


def _intake_commands(context: dict[str, Any]) -> str:
    return f"""# Patch Apply External Review Intake Commands

Store the raw external review response at:

```text
var/review-runs/v0.6/patch-apply/raw-response.md
```

Normalize it with:

```bash
uv run python scripts/external_response_normalize.py \\
  var/review-runs/v0.6/patch-apply/raw-response.md \\
  --reviewer "GPT 5.5 Pro" \\
  --reviewer-type "external-model" \\
  --source-access "source-level" \\
  --reviewed-commit "{context["commit"]}" \\
  --reviewed-packet-hash "{context["patch_packet_sha256"]}" \\
  --area "patch-apply" \\
  --output var/review-runs/v0.6/patch-apply/normalized-response.json
```

The normalizer accepts `EXT-PA-###` finding IDs for this lane. Normalized output does not mutate
finding records and does not close external review rows.

If critical/high findings are present, stop unrelated work and create structured finding records
before remediation.
"""


def _bundle_sources(repo_root: Path, paths: list[Path]) -> str:
    sections: list[str] = []
    for relative in paths:
        path = repo_root / relative
        if not path.exists():
            raise PatchApplyReviewPacketError(f"required source is missing: {relative}")
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


def _hashes(output_dir: Path) -> list[dict[str, Any]]:
    hashes: list[dict[str, Any]] = []
    for path in sorted(output_dir.glob("*")):
        if path.name == "patch-apply-review-artifact-hashes.json":
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
        raise PatchApplyReviewPacketError(f"required packet source is missing: {path}")
    return path.read_text(encoding="utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


if __name__ == "__main__":
    raise SystemExit(main())

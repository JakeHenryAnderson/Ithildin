"""Build a focused review-console/admin external source-review bundle."""

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

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v0.7/review-console-source-review")
DISPATCH_ROOT = Path("var/review-packets/v0.6/dispatch")

SOURCE_FILES = [
    Path("apps/ui/src/App.tsx"),
    Path("apps/ui/src/styles.css"),
    Path("apps/ui/package.json"),
    Path("apps/api/src/ithildin_api/app.py"),
    Path("apps/api/src/ithildin_api/auth.py"),
    Path("apps/api/src/ithildin_api/approvals.py"),
    Path("apps/api/src/ithildin_api/patches.py"),
    Path("apps/api/src/ithildin_api/security_status.py"),
    Path("apps/api/src/ithildin_api/config.py"),
    Path("apps/api/src/ithildin_api/redaction.py"),
]

TEST_FILES = [
    Path("tests/test_api_service.py"),
    Path("tests/test_release_readiness.py"),
    Path("tests/test_governed_tool_calls.py"),
]

CONTRACT_DOCS = [
    Path("docs/codex/review-console-source-review-checklist.md"),
    Path("docs/codex/review-console-assurance.md"),
    Path("docs/codex/local-auth-boundary.md"),
    Path("docs/codex/release-evidence-schema.md"),
    Path("docs/codex/source-review-closure-matrix.md"),
    Path("docs/codex/v0.6-lane-status-board.md"),
    Path("docs/codex/v0.7-external-review-row-partition.md"),
    Path("docs/codex/v0.6-internal-proxy-review-operating-model.md"),
    Path("docs/codex/findings/sub-019-approval-review-binding-drift.md"),
    Path("docs/codex/findings/sub-020-review-console-trust-posture.md"),
    Path("docs/codex/findings/sub-021-approval-route-decision-mismatch.md"),
    Path("docs/codex/findings/sub-075-review-console-copy-evidence-parity.md"),
    Path("docs/codex/findings/sub-078-approval-review-drift.md"),
    Path("docs/codex/findings/sub-079-patch-diagnostics-detail.md"),
    Path("docs/codex/findings/sub-080-review-console-ui-test-harness.md"),
    Path("docs/codex/findings/sub-084-patch-apply-missing-scope-approval.md"),
]

FOCUSED_TEST_COMMAND = [
    "uv",
    "run",
    "pytest",
    "tests/test_api_service.py",
    "tests/test_release_readiness.py",
    "-q",
]

EVIDENCE_COMMANDS = [
    ["npm", "run", "typecheck", "--prefix", "apps/ui"],
    ["npm", "run", "build", "--prefix", "apps/ui"],
    ["make", "reviewer-findings-check"],
]


class ReviewConsoleSourceReviewBundleError(RuntimeError):
    """Raised when the Review console source-review bundle cannot be built."""


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
    except ReviewConsoleSourceReviewBundleError as exc:
        print(f"Review console source-review bundle failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built Review console source-review bundle at {output_dir}")
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
        raise ReviewConsoleSourceReviewBundleError(
            "working tree is dirty; commit before source-review handoff"
        )

    _build_dispatch_packets(repo_root, repo_root / DISPATCH_ROOT)
    dispatch_manifest_path = repo_root / DISPATCH_ROOT / "dispatch-packet-hashes.json"
    dispatch_manifest = json.loads(dispatch_manifest_path.read_text(encoding="utf-8"))
    review_console_packet = _packet_metadata(dispatch_manifest)

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context: dict[str, Any] = {
        "commit": commit,
        "dirty": dirty,
        "dispatch_manifest_path": DISPATCH_ROOT / "dispatch-packet-hashes.json",
        "review_console_packet_path": DISPATCH_ROOT / review_console_packet["path"],
        "review_console_packet_sha256": review_console_packet["sha256"],
        "review_console_packet_payload_sha256": review_console_packet["payload_sha256"],
    }

    files: dict[str, str] = {
        "00_REVIEW_CONSOLE_SOURCE_REVIEW_INDEX.md": _index(context),
        "01_REVIEW_CONSOLE_SOURCE_REVIEW_PROMPT.md": _prompt(context),
        "02_REVIEW_CONSOLE_DISPATCH_PACKET.md": _read(
            repo_root / context["review_console_packet_path"]
        ),
        "03_REVIEW_CONSOLE_SOURCE_BUNDLE.md": _bundle_sources(repo_root, SOURCE_FILES),
        "04_REVIEW_CONSOLE_TESTS_BUNDLE.md": _bundle_sources(repo_root, TEST_FILES),
        "05_REVIEW_CONSOLE_CONTRACTS_BUNDLE.md": _bundle_sources(repo_root, CONTRACT_DOCS),
        "08_REVIEW_CONSOLE_INTAKE_COMMANDS.md": _intake_commands(context),
    }
    for relative, content in files.items():
        (output_dir / relative).write_text(content.rstrip() + "\n", encoding="utf-8")

    evidence_outputs = [
        _command_output(command, run_commands=run_commands) for command in EVIDENCE_COMMANDS
    ]
    (output_dir / "06_REVIEW_CONSOLE_EVIDENCE.md").write_text(
        _mcp_evidence(evidence_outputs).rstrip() + "\n",
        encoding="utf-8",
    )
    _write_command_output(
        output_dir / "07_REVIEW_CONSOLE_FOCUSED_TESTS.txt",
        _command_output(FOCUSED_TEST_COMMAND, run_commands=run_commands),
    )
    _write_json(
        output_dir / "review-console-source-review-artifact-hashes.json",
        _hashes(output_dir),
    )
    return output_dir


def _index(context: dict[str, Any]) -> str:
    return f"""# Review Console Source Review Handoff

This packet prepares the review-console/admin lane for source-level external review. It attaches the
React console, local admin API routes, approval review and mutation paths, patch-apply diagnostics,
trust/status surfaces, focused API/release-readiness tests, review-console assurance docs, prior
internal findings, and command evidence needed to decide whether the lane can close for the v0.1
local-preview boundary.

## Boundary

- Current review status: v0.8 roadmap/product-risk consultation after v0.6/v0.7 focused
  source-review lane closure for the v0.1 local-preview runtime boundary.
- Lane: Review console.
- Finding namespace: `EXT-UI-###`.
- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Dispatch packet path: `{context["review_console_packet_path"]}`.
- Dispatch packet whole-file SHA-256: `{context["review_console_packet_sha256"]}`.
- Dispatch packet payload SHA-256: `{context["review_console_packet_payload_sha256"]}`.

## Send These Files

1. `00_REVIEW_CONSOLE_SOURCE_REVIEW_INDEX.md`
2. `01_REVIEW_CONSOLE_SOURCE_REVIEW_PROMPT.md`
3. `02_REVIEW_CONSOLE_DISPATCH_PACKET.md`
4. `03_REVIEW_CONSOLE_SOURCE_BUNDLE.md`
5. `04_REVIEW_CONSOLE_TESTS_BUNDLE.md`
6. `05_REVIEW_CONSOLE_CONTRACTS_BUNDLE.md`
7. `06_REVIEW_CONSOLE_EVIDENCE.md`
8. `07_REVIEW_CONSOLE_FOCUSED_TESTS.txt`
9. `08_REVIEW_CONSOLE_INTAKE_COMMANDS.md`
10. `review-console-source-review-artifact-hashes.json`

## What This Does Not Prove

This packet does not close external review rows, approve public/security-product positioning,
approve capability expansion, prove production authentication, or make the local admin console a
multi-user identity system. It provides the source/test evidence needed for an external reviewer to
decide whether the review-console evidence, local admin auth, and review-console source-review
checklist rows can close for the v0.1 local-preview boundary.
"""


def _prompt(context: dict[str, Any]) -> str:
    finding_table = "\n".join(
        [
            "| Finding ID | Severity | Area | Affected files/functions | "
            "Blocking status | Disposition | Recommended fix |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            "| EXT-UI-### | critical/high/medium/low/informational | Review console | "
            "path/function | blocking/should-fix/later/advisory | open | fix summary |",
        ]
    )
    return f"""# Review Console Source Review Prompt

You are reviewing Ithildin as an external source reviewer for the review-console/admin lane only.
Treat this as source-level review if and only if you inspect the attached React source, local admin
API source, approval/patch-diagnostics source, focused tests, contract docs, prior internal
findings, and command evidence.

Reviewed commit: `{context["commit"]}`
Reviewed dispatch packet hash: `{context["review_console_packet_sha256"]}`
Reviewed dispatch payload hash: `{context["review_console_packet_payload_sha256"]}`
Area: `review-console`
Finding namespace: `EXT-UI-###`

## Scope

Please review:

- local bearer-token admin authentication remains local-preview only and does not claim production
  identity, RBAC, sessions, OIDC, SAML, SCIM, or multi-user custody;
- the review console sends the admin bearer token only to configured local API origins and does not
  create a new tool execution path outside existing API routes;
- approval lists use `/approvals/review` evidence, display binding checks, expose copyable safe
  approval evidence, and prevent stale approvals at the API before marking stored-proposal patch
  apply approvals approved;
- approve/deny controls send the expected route decision and `decided_by` value without changing
  approval semantics or adding execution controls;
- patch proposal detail and diagnostics expose only admin-protected diffs or safe recovery metadata,
  with no file contents/diff contents in diagnostic tables;
- system trust, audit verification/export, tools, policy preview, and policy impact panels render
  safe status/evidence without mutating policy, audit, registry, or tool state;
- loading, locked, unauthorized, warning, failure, and empty states preserve the local-preview
  boundary and do not overstate production/security-product readiness.

## Required Disposition

Please answer whether the review-console evidence, local admin auth, and review-console
source-review checklist rows can be externally closed for the v0.1 local-preview runtime boundary.
If they cannot close, explain exactly which source/test/evidence item is missing or which
implementation issue blocks closure.

Use this exact finding table shape for actionable findings:

{finding_table}

If there are no implementation findings, explicitly say so and state whether the lane can close for
local-preview review-console/admin behavior. Do not approve production identity, enterprise RBAC,
remote MCP hosting, public/security-product positioning, capability expansion, or new governed tool
powers.
"""


def _intake_commands(context: dict[str, Any]) -> str:
    return f"""# Review Console External Review Intake Commands

Store the raw external review response at:

```text
var/review-runs/v0.7/review-console/raw-response.md
```

Normalize it with:

```bash
uv run python scripts/external_response_normalize.py \\
  var/review-runs/v0.7/review-console/raw-response.md \\
  --reviewer "GPT 5.5 Pro" \\
  --reviewer-type "external-model" \\
  --source-access "source-level" \\
  --reviewed-commit "{context["commit"]}" \\
  --reviewed-packet-hash "{context["review_console_packet_sha256"]}" \\
  --area "review-console" \\
  --output var/review-runs/v0.7/review-console/normalized-response.json
```

The normalizer accepts `EXT-UI-###` finding IDs for this lane. Normalized output does not mutate
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
            raise ReviewConsoleSourceReviewBundleError(f"missing project marker: {marker}")


def _build_dispatch_packets(repo_root: Path, output_root: Path) -> dict[str, Any]:
    return external_review_dispatch_packets.build_dispatch_packets(repo_root, output_root)


def _packet_metadata(dispatch_manifest: dict[str, Any]) -> dict[str, Any]:
    for packet in dispatch_manifest.get("packets", []):
        if packet.get("path") == "review-console.md":
            return dict(packet)
    raise ReviewConsoleSourceReviewBundleError("Review console dispatch packet metadata is missing")


def _bundle_sources(repo_root: Path, paths: list[Path]) -> str:
    sections: list[str] = []
    for relative in paths:
        path = repo_root / relative
        if not path.exists():
            raise ReviewConsoleSourceReviewBundleError(f"required source is missing: {relative}")
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
        raise ReviewConsoleSourceReviewBundleError(f"{' '.join(command)} failed")
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


def _mcp_evidence(outputs: list[dict[str, Any]]) -> str:
    sections = [
        "# Review Console Evidence",
        "",
        "## Boundary Summary",
        "",
        "- The review console remains a local admin evidence and approval surface.",
        "- It does not implement production identity, sessions, OIDC/SAML/SCIM, or new tool",
        "  powers.",
        "- Patch apply approval-time binding review is enforced server-side for stored proposals.",
        "- Patch apply diagnostics remain read-only and content-free.",
        "- UI validation is TypeScript/build plus backend/release-readiness tests; a dedicated",
        "  frontend interaction harness is a low deferred assurance item.",
        "",
    ]
    for output in outputs:
        sections.extend(
            [
                f"## {' '.join(output['command'])}",
                "",
                f"$ {' '.join(output['command'])}",
                f"returncode={output['returncode']}",
                "",
                "### stdout",
                str(output["stdout"]).rstrip(),
                "",
                "### stderr",
                str(output["stderr"]).rstrip(),
                "",
            ]
        )
    return "\n".join(sections)


def _hashes(output_dir: Path) -> list[dict[str, Any]]:
    hashes: list[dict[str, Any]] = []
    for path in sorted(output_dir.glob("*")):
        if path.name == "review-console-source-review-artifact-hashes.json":
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
        raise ReviewConsoleSourceReviewBundleError(
            f"required packet source is missing: {path}"
        )
    return path.read_text(encoding="utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


if __name__ == "__main__":
    raise SystemExit(main())

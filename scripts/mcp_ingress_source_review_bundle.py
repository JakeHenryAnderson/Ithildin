"""Build a focused MCP ingress external source-review bundle."""

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

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v0.7/mcp-ingress-source-review")
DISPATCH_ROOT = Path("var/review-packets/v0.6/dispatch")

SOURCE_FILES = [
    Path("apps/mcp-server/src/ithildin_mcp_server/server.py"),
    Path("apps/mcp-server/src/ithildin_mcp_server/__main__.py"),
    Path("apps/api/src/ithildin_api/tool_calls.py"),
    Path("apps/api/src/ithildin_api/identity.py"),
    Path("apps/api/src/ithildin_api/registry.py"),
    Path("apps/api/src/ithildin_api/resources.py"),
    Path("apps/api/src/ithildin_api/schema_validation.py"),
    Path("apps/api/src/ithildin_api/policy_preview.py"),
    Path("apps/api/src/ithildin_api/redaction.py"),
    Path("apps/api/src/ithildin_api/config.py"),
    Path("apps/api/src/ithildin_api/app.py"),
]

TEST_FILES = [
    Path("tests/test_mcp_adapter.py"),
    Path("tests/test_mcp_integration_flow.py"),
    Path("tests/test_governed_tool_calls.py"),
    Path("tests/test_api_service.py"),
    Path("tests/test_policy_parity.py"),
    Path("tests/test_tool_registry.py"),
    Path("tests/test_identity.py"),
    Path("tests/test_mcp_inspector_recipes.py"),
]

CONTRACT_DOCS = [
    Path("docs/codex/mcp-ingress-source-review-checklist.md"),
    Path("docs/codex/mcp-ingress-bypass-audit.md"),
    Path("docs/codex/mcp-client-examples.md"),
    Path("docs/codex/mcp-inspector-recipes.md"),
    Path("docs/codex/executor-contract-set.md"),
    Path("docs/codex/source-review-closure-matrix.md"),
    Path("docs/codex/v0.6-lane-status-board.md"),
    Path("docs/codex/v0.7-external-review-row-partition.md"),
    Path("docs/codex/v0.6-internal-subagent-review-wave.md"),
    Path("docs/codex/v0.6-internal-review-execution-wave-2.md"),
    Path("docs/codex/findings/sub-018-mcp-exposure-gate.md"),
    Path("docs/codex/findings/sub-074-mcp-unexposed-denial-audit.md"),
]

FOCUSED_TEST_COMMAND = [
    "uv",
    "run",
    "pytest",
    "tests/test_mcp_adapter.py",
    "tests/test_mcp_integration_flow.py",
    "tests/test_governed_tool_calls.py",
    "-q",
]

EVIDENCE_COMMANDS = [
    ["make", "no-new-powers-guardrail"],
    ["make", "mcp-inspector-recipes"],
]


class McpIngressSourceReviewBundleError(RuntimeError):
    """Raised when the MCP ingress source-review bundle cannot be built."""


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
    except McpIngressSourceReviewBundleError as exc:
        print(f"MCP ingress source-review bundle failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built MCP ingress source-review bundle at {output_dir}")
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
        raise McpIngressSourceReviewBundleError(
            "working tree is dirty; commit before source-review handoff"
        )

    _build_dispatch_packets(repo_root, repo_root / DISPATCH_ROOT)
    dispatch_manifest_path = repo_root / DISPATCH_ROOT / "dispatch-packet-hashes.json"
    dispatch_manifest = json.loads(dispatch_manifest_path.read_text(encoding="utf-8"))
    mcp_packet = _packet_metadata(dispatch_manifest)

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context: dict[str, Any] = {
        "commit": commit,
        "dirty": dirty,
        "dispatch_manifest_path": DISPATCH_ROOT / "dispatch-packet-hashes.json",
        "mcp_packet_path": DISPATCH_ROOT / mcp_packet["path"],
        "mcp_packet_sha256": mcp_packet["sha256"],
        "mcp_packet_payload_sha256": mcp_packet["payload_sha256"],
    }

    files: dict[str, str] = {
        "00_MCP_INGRESS_SOURCE_REVIEW_INDEX.md": _index(context),
        "01_MCP_INGRESS_SOURCE_REVIEW_PROMPT.md": _prompt(context),
        "02_MCP_INGRESS_DISPATCH_PACKET.md": _read(repo_root / context["mcp_packet_path"]),
        "03_MCP_INGRESS_SOURCE_BUNDLE.md": _bundle_sources(repo_root, SOURCE_FILES),
        "04_MCP_INGRESS_TESTS_BUNDLE.md": _bundle_sources(repo_root, TEST_FILES),
        "05_MCP_INGRESS_CONTRACTS_BUNDLE.md": _bundle_sources(repo_root, CONTRACT_DOCS),
        "08_MCP_INGRESS_INTAKE_COMMANDS.md": _intake_commands(context),
    }
    for relative, content in files.items():
        (output_dir / relative).write_text(content.rstrip() + "\n", encoding="utf-8")

    evidence_outputs = [
        _command_output(command, run_commands=run_commands) for command in EVIDENCE_COMMANDS
    ]
    (output_dir / "06_MCP_INGRESS_EVIDENCE.md").write_text(
        _mcp_evidence(evidence_outputs).rstrip() + "\n",
        encoding="utf-8",
    )
    _write_command_output(
        output_dir / "07_MCP_INGRESS_FOCUSED_TESTS.txt",
        _command_output(FOCUSED_TEST_COMMAND, run_commands=run_commands),
    )
    _write_json(
        output_dir / "mcp-ingress-source-review-artifact-hashes.json",
        _hashes(output_dir),
    )
    return output_dir


def _index(context: dict[str, Any]) -> str:
    return f"""# MCP Ingress Source Review Handoff

This packet prepares the stdio MCP ingress lane for source-level external review. It attaches the
MCP adapter, shared governed-call path, trusted identity/registry helpers, focused MCP and governed
pipeline tests, MCP ingress contract docs, prior internal findings, and command evidence needed to
decide whether the lane can close for the v0.1 local-preview boundary.

## Boundary

- Current review status: v0.8 roadmap/product-risk consultation after v0.6/v0.7 focused
  source-review lane closure for the v0.1 local-preview runtime boundary.
- Lane: MCP ingress.
- Finding namespace: `EXT-MCP-###`.
- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Dispatch packet path: `{context["mcp_packet_path"]}`.
- Dispatch packet whole-file SHA-256: `{context["mcp_packet_sha256"]}`.
- Dispatch packet payload SHA-256: `{context["mcp_packet_payload_sha256"]}`.

## Send These Files

1. `00_MCP_INGRESS_SOURCE_REVIEW_INDEX.md`
2. `01_MCP_INGRESS_SOURCE_REVIEW_PROMPT.md`
3. `02_MCP_INGRESS_DISPATCH_PACKET.md`
4. `03_MCP_INGRESS_SOURCE_BUNDLE.md`
5. `04_MCP_INGRESS_TESTS_BUNDLE.md`
6. `05_MCP_INGRESS_CONTRACTS_BUNDLE.md`
7. `06_MCP_INGRESS_EVIDENCE.md`
8. `07_MCP_INGRESS_FOCUSED_TESTS.txt`
9. `08_MCP_INGRESS_INTAKE_COMMANDS.md`
10. `mcp-ingress-source-review-artifact-hashes.json`

## What This Does Not Prove

This packet does not close external review rows, approve public/security-product positioning,
approve capability expansion, approve remote MCP hosting, or prove production authorization. It
provides the source/test evidence needed for an external reviewer to decide whether the MCP ingress
and MCP ingress source-review checklist rows can close for the v0.1 local-preview boundary.
"""


def _prompt(context: dict[str, Any]) -> str:
    finding_table = "\n".join(
        [
            "| Finding ID | Severity | Area | Affected files/functions | "
            "Blocking status | Disposition | Recommended fix |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            "| EXT-MCP-### | critical/high/medium/low/informational | MCP ingress | "
            "path/function | blocking/should-fix/later/advisory | open | fix summary |",
        ]
    )
    return f"""# MCP Ingress Source Review Prompt

You are reviewing Ithildin as an external source reviewer for the MCP ingress lane only. Treat this
as source-level review if and only if you inspect the attached MCP adapter source, shared governed
pipeline source, focused MCP tests, contract docs, prior internal findings, and command evidence.

Reviewed commit: `{context["commit"]}`
Reviewed dispatch packet hash: `{context["mcp_packet_sha256"]}`
Reviewed dispatch payload hash: `{context["mcp_packet_payload_sha256"]}`
Area: `mcp-ingress`
Finding namespace: `EXT-MCP-###`

## Scope

Please review:

- stdio MCP remains local ingress only; remote/network MCP hosting remains deferred;
- `tools/list` is filtered by trusted registry metadata, `mcp.exposed`, and the configured local MCP
  principal rather than caller-supplied roles;
- `tools/call` uses the fixed local MCP principal/session and routes to `GovernedToolCallService`
  for registry lookup, schema validation, trusted principal resolution, resource construction,
  policy, approvals, execution, redaction, and audit;
- registered tools that are not exposed over MCP are denied before execution through the shared
  pre-policy denial audit helper with safe `mcp_exposure` metadata;
- unknown tools, disabled/unknown principals, invalid arguments, policy denials, and
  approval-required write calls produce safe MCP responses and audit evidence where appropriate;
- the adapter does not implement independent policy logic, executor logic, approval state
  transitions, identity upgrades, audit rewriting, or redaction bypasses;
- MCP startup enforces manifest lock, signed-lock requirements when configured, principal registry,
  workspace registry, storage validation, and local security settings consistently with API startup.

## Required Disposition

Please answer whether the MCP ingress and MCP ingress source-review checklist rows can be externally
closed for the v0.1 local-preview runtime boundary. If they cannot close, explain exactly which
source/test/evidence item is missing or which implementation issue blocks closure.

Use this exact finding table shape for actionable findings:

{finding_table}

If there are no implementation findings, explicitly say so and state whether the lane can close for
local-preview MCP ingress. Do not approve remote MCP hosting, OAuth/OIDC, HTTP MCP transport,
session-based authorization, public/security-product positioning, capability expansion, or new
governed tool powers.
"""


def _intake_commands(context: dict[str, Any]) -> str:
    return f"""# MCP Ingress External Review Intake Commands

Store the raw external review response at:

```text
var/review-runs/v0.7/mcp-ingress/raw-response.md
```

Normalize it with:

```bash
uv run python scripts/external_response_normalize.py \\
  var/review-runs/v0.7/mcp-ingress/raw-response.md \\
  --reviewer "GPT 5.5 Pro" \\
  --reviewer-type "external-model" \\
  --source-access "source-level" \\
  --reviewed-commit "{context["commit"]}" \\
  --reviewed-packet-hash "{context["mcp_packet_sha256"]}" \\
  --area "mcp-ingress" \\
  --output var/review-runs/v0.7/mcp-ingress/normalized-response.json
```

The normalizer accepts `EXT-MCP-###` finding IDs for this lane. Normalized output does not mutate
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
            raise McpIngressSourceReviewBundleError(f"missing project marker: {marker}")


def _build_dispatch_packets(repo_root: Path, output_root: Path) -> dict[str, Any]:
    return external_review_dispatch_packets.build_dispatch_packets(repo_root, output_root)


def _packet_metadata(dispatch_manifest: dict[str, Any]) -> dict[str, Any]:
    for packet in dispatch_manifest.get("packets", []):
        if packet.get("path") == "mcp-ingress.md":
            return dict(packet)
    raise McpIngressSourceReviewBundleError("MCP ingress dispatch packet metadata is missing")


def _bundle_sources(repo_root: Path, paths: list[Path]) -> str:
    sections: list[str] = []
    for relative in paths:
        path = repo_root / relative
        if not path.exists():
            raise McpIngressSourceReviewBundleError(f"required source is missing: {relative}")
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
        raise McpIngressSourceReviewBundleError(f"{' '.join(command)} failed")
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
        "# MCP Ingress Evidence",
        "",
        "## Boundary Summary",
        "",
        "- MCP remains stdio-only local ingress; remote/network MCP hosting remains deferred.",
        "- The adapter uses the fixed local MCP principal `agent:mcp-local` and fixed session",
        "  `mcp-stdio` rather than caller-supplied principal/session metadata.",
        "- `tools/list` filters by trusted registry visibility and `mcp.exposed` metadata.",
        "- `tools/call` routes through the shared governed pipeline or shared pre-policy denial",
        "  evidence helper for unexposed registered tools.",
        "- This packet does not add remote MCP, OAuth/OIDC, session authorization, or new tool",
        "  powers.",
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
        if path.name == "mcp-ingress-source-review-artifact-hashes.json":
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
        raise McpIngressSourceReviewBundleError(
            f"required packet source is missing: {path}"
        )
    return path.read_text(encoding="utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


if __name__ == "__main__":
    raise SystemExit(main())

"""Build a focused HTTP fetch external source-review bundle."""

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

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v0.7/http-fetch-source-review")
DISPATCH_ROOT = Path("var/review-packets/v0.6/dispatch")

SOURCE_FILES = [
    Path("apps/api/src/ithildin_api/http_tools.py"),
    Path("apps/api/src/ithildin_api/resources.py"),
    Path("apps/api/src/ithildin_api/policy_preview.py"),
    Path("apps/api/src/ithildin_api/tool_calls.py"),
    Path("apps/api/src/ithildin_api/schema_validation.py"),
    Path("apps/api/src/ithildin_api/config.py"),
    Path("apps/api/src/ithildin_api/app.py"),
    Path("apps/api/src/ithildin_api/policy_parity.py"),
    Path("apps/mcp-server/src/ithildin_mcp_server/server.py"),
    Path("tool-manifests/http-fetch.yaml"),
]

TEST_FILES = [
    Path("tests/fixtures/http_canonicalization_corpus.json"),
    Path("tests/test_http_tools.py"),
    Path("tests/test_governed_tool_calls.py"),
    Path("tests/test_policy_parity.py"),
    Path("tests/test_mcp_adapter.py"),
    Path("tests/test_mcp_integration_flow.py"),
    Path("tests/test_security_regressions.py"),
    Path("tests/test_api_service.py"),
]

CONTRACT_DOCS = [
    Path("docs/codex/http-executor-contract.md"),
    Path("docs/codex/http-fetch-source-review-checklist.md"),
    Path("docs/codex/source-review-closure-matrix.md"),
    Path("docs/codex/v0.6-lane-status-board.md"),
    Path("docs/codex/v0.7-external-review-row-partition.md"),
    Path("docs/codex/v0.6-internal-subagent-review-wave.md"),
    Path("docs/codex/v0.6-internal-review-execution-wave-2.md"),
    Path("docs/codex/findings/sub-001-http-fetch-dns-pinning.md"),
    Path("docs/codex/findings/sub-007-http-response-processing-safe-errors.md"),
    Path("docs/codex/findings/sub-008-http-explicit-port-normalization.md"),
    Path("docs/codex/findings/sub-009-http-audit-query-redaction.md"),
    Path("docs/codex/findings/sub-040-http-malformed-url-resource-redaction.md"),
    Path("docs/codex/findings/sub-041-http-preview-schema-resource-order.md"),
    Path("docs/codex/findings/sub-042-http-raw-unicode-url-safe-error.md"),
    Path("docs/codex/findings/sub-043-http-json-parser-safe-errors.md"),
    Path("docs/codex/findings/sub-044-http-dispatch-finding-coverage.md"),
    Path("docs/codex/findings/sub-045-http-closure-traceability.md"),
    Path("docs/codex/findings/sub-046-http-lane-result-summary.md"),
    Path("docs/codex/findings/sub-047-http-contract-link-drift.md"),
]

FOCUSED_TEST_COMMAND = [
    "uv",
    "run",
    "pytest",
    "tests/test_http_tools.py",
    "tests/test_governed_tool_calls.py",
    "tests/test_policy_parity.py",
    "tests/test_mcp_adapter.py",
    "tests/test_mcp_integration_flow.py",
    "-q",
]

POLICY_PARITY_COMMAND = ["make", "policy-parity"]


class HttpFetchSourceReviewBundleError(RuntimeError):
    """Raised when the HTTP fetch source-review bundle cannot be built."""


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
    except HttpFetchSourceReviewBundleError as exc:
        print(f"HTTP fetch source-review bundle failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built HTTP fetch source-review bundle at {output_dir}")
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
        raise HttpFetchSourceReviewBundleError(
            "working tree is dirty; commit before source-review handoff"
        )

    _build_dispatch_packets(repo_root, repo_root / DISPATCH_ROOT)
    dispatch_manifest_path = repo_root / DISPATCH_ROOT / "dispatch-packet-hashes.json"
    dispatch_manifest = json.loads(dispatch_manifest_path.read_text(encoding="utf-8"))
    http_packet = _packet_metadata(dispatch_manifest)

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context: dict[str, Any] = {
        "commit": commit,
        "dirty": dirty,
        "dispatch_manifest_path": DISPATCH_ROOT / "dispatch-packet-hashes.json",
        "http_packet_path": DISPATCH_ROOT / http_packet["path"],
        "http_packet_sha256": http_packet["sha256"],
        "http_packet_payload_sha256": http_packet["payload_sha256"],
    }

    files: dict[str, str] = {
        "00_HTTP_FETCH_SOURCE_REVIEW_INDEX.md": _index(context),
        "01_HTTP_FETCH_SOURCE_REVIEW_PROMPT.md": _prompt(context),
        "02_HTTP_FETCH_DISPATCH_PACKET.md": _read(repo_root / context["http_packet_path"]),
        "03_HTTP_FETCH_SOURCE_BUNDLE.md": _bundle_sources(repo_root, SOURCE_FILES),
        "04_HTTP_FETCH_TESTS_BUNDLE.md": _bundle_sources(repo_root, TEST_FILES),
        "05_HTTP_FETCH_CONTRACTS_BUNDLE.md": _bundle_sources(repo_root, CONTRACT_DOCS),
        "08_HTTP_FETCH_INTAKE_COMMANDS.md": _intake_commands(context),
    }
    for relative, content in files.items():
        (output_dir / relative).write_text(content.rstrip() + "\n", encoding="utf-8")

    parity_output = _command_output(POLICY_PARITY_COMMAND, run_commands=run_commands)
    (output_dir / "06_HTTP_FETCH_EVIDENCE.md").write_text(
        _http_evidence(parity_output).rstrip() + "\n",
        encoding="utf-8",
    )
    _write_command_output(
        output_dir / "07_HTTP_FETCH_FOCUSED_TESTS.txt",
        _command_output(FOCUSED_TEST_COMMAND, run_commands=run_commands),
    )
    _write_json(output_dir / "http-fetch-source-review-artifact-hashes.json", _hashes(output_dir))
    return output_dir


def _index(context: dict[str, Any]) -> str:
    return f"""# HTTP Fetch Source Review Handoff

This packet prepares the `http.fetch` lane for source-level external review. It attaches the
implementation path, focused tests, HTTP executor contract, canonicalization corpus, prior internal
finding history, and command evidence needed to decide whether the lane can close for the v0.1
local-preview boundary.

## Boundary

- Current review status: v0.6/v0.7 external-review closure work for the v0.1 local-preview runtime
  boundary.
- Lane: HTTP fetch.
- Finding namespace: `EXT-HTTP-###`.
- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Dispatch packet path: `{context["http_packet_path"]}`.
- Dispatch packet whole-file SHA-256: `{context["http_packet_sha256"]}`.
- Dispatch packet payload SHA-256: `{context["http_packet_payload_sha256"]}`.

## Send These Files

1. `00_HTTP_FETCH_SOURCE_REVIEW_INDEX.md`
2. `01_HTTP_FETCH_SOURCE_REVIEW_PROMPT.md`
3. `02_HTTP_FETCH_DISPATCH_PACKET.md`
4. `03_HTTP_FETCH_SOURCE_BUNDLE.md`
5. `04_HTTP_FETCH_TESTS_BUNDLE.md`
6. `05_HTTP_FETCH_CONTRACTS_BUNDLE.md`
7. `06_HTTP_FETCH_EVIDENCE.md`
8. `07_HTTP_FETCH_FOCUSED_TESTS.txt`
9. `08_HTTP_FETCH_INTAKE_COMMANDS.md`
10. `http-fetch-source-review-artifact-hashes.json`

## What This Does Not Prove

This packet does not close external review rows, approve public/security-product positioning,
approve capability expansion, or prove production security. It provides the source/test evidence
needed for an external reviewer to decide whether the HTTP fetch lane can be closed for the v0.1
local-preview boundary.
"""


def _prompt(context: dict[str, Any]) -> str:
    finding_table = "\n".join(
        [
            "| Finding ID | Severity | Area | Affected files/functions | "
            "Blocking status | Disposition | Recommended fix |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            "| EXT-HTTP-### | critical/high/medium/low/informational | HTTP fetch | "
            "path/function | blocking/should-fix/later/advisory | open | fix summary |",
        ]
    )
    return f"""# HTTP Fetch Source Review Prompt

You are reviewing Ithildin as an external source reviewer for the `http.fetch` lane only. Treat
this as source-level review if and only if you inspect the attached source bundle, focused tests,
canonicalization corpus, contract docs, prior internal findings, and command evidence.

Reviewed commit: `{context["commit"]}`
Reviewed dispatch packet hash: `{context["http_packet_sha256"]}`
Reviewed dispatch payload hash: `{context["http_packet_payload_sha256"]}`
Area: `http-fetch`
Finding namespace: `EXT-HTTP-###`

## Scope

Please review:

- URL parsing, normalization, control-character denial, credential denial, fragment denial, and
  malformed host/port handling;
- exact allowlist semantics across scheme, normalized host, IDNA/punycode, trailing dots, and
  default/explicit ports;
- DNS/IP validation, DNS-change denial, pinned transport handoff, and proxy environment suppression;
- redirect revalidation for allowlist, DNS, and blocked IP ranges on every hop;
- timeout, redirect-limit, content-length, body-size, JSON/text processing, and safe-error behavior;
- audit resource redaction and policy preview/runtime parity for valid and invalid `http.fetch`
  arguments;
- MCP and governed-call integration staying thin and routed through the shared pipeline.

## Required Disposition

Please answer whether the HTTP fetch lane can be externally closed for the v0.1 local-preview
runtime boundary. If it cannot close, explain exactly which source/test/evidence item is missing or
which implementation issue blocks closure.

Use this exact finding table shape for actionable findings:

{finding_table}

If there are no implementation findings, explicitly say so and state whether the lane can close for
local-preview `http.fetch`. Do not approve arbitrary HTTP methods, caller-supplied headers, request
bodies, cookies, broad network access, proxy configuration, browser automation, public
security-product positioning, or new governed tool powers.
"""


def _intake_commands(context: dict[str, Any]) -> str:
    return f"""# HTTP Fetch External Review Intake Commands

Store the raw external review response at:

```text
var/review-runs/v0.7/http-fetch/raw-response.md
```

Normalize it with:

```bash
uv run python scripts/external_response_normalize.py \\
  var/review-runs/v0.7/http-fetch/raw-response.md \\
  --reviewer "GPT 5.5 Pro" \\
  --reviewer-type "external-model" \\
  --source-access "source-level" \\
  --reviewed-commit "{context["commit"]}" \\
  --reviewed-packet-hash "{context["http_packet_sha256"]}" \\
  --area "http-fetch" \\
  --output var/review-runs/v0.7/http-fetch/normalized-response.json
```

The normalizer accepts `EXT-HTTP-###` finding IDs for this lane. Normalized output does not mutate
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
            raise HttpFetchSourceReviewBundleError(f"missing project marker: {marker}")


def _build_dispatch_packets(repo_root: Path, output_root: Path) -> dict[str, Any]:
    return external_review_dispatch_packets.build_dispatch_packets(repo_root, output_root)


def _packet_metadata(dispatch_manifest: dict[str, Any]) -> dict[str, Any]:
    for packet in dispatch_manifest.get("packets", []):
        if packet.get("path") == "http-fetch.md":
            return dict(packet)
    raise HttpFetchSourceReviewBundleError("HTTP fetch dispatch packet metadata is missing")


def _bundle_sources(repo_root: Path, paths: list[Path]) -> str:
    sections: list[str] = []
    for relative in paths:
        path = repo_root / relative
        if not path.exists():
            raise HttpFetchSourceReviewBundleError(f"required source is missing: {relative}")
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
        raise HttpFetchSourceReviewBundleError(f"{' '.join(command)} failed")
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


def _http_evidence(parity_output: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# HTTP Fetch Evidence",
            "",
            "## Boundary Summary",
            "",
            "- `http.fetch` is GET-only and URL-only.",
            "- The manifest rejects caller-supplied headers, methods, request bodies, cookies,",
            "  timeout overrides, and proxy configuration.",
            "- Runtime review should verify exact allowlist matching, DNS/IP validation, pinned",
            "  transport handoff, redirect revalidation, proxy suppression, and safe errors.",
            "- Policy preview should stay side-effect-free and match runtime resource semantics",
            "  for valid arguments while avoiding raw secret leakage for malformed URLs.",
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
        if path.name == "http-fetch-source-review-artifact-hashes.json":
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
        raise HttpFetchSourceReviewBundleError(f"required packet source is missing: {path}")
    return path.read_text(encoding="utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


if __name__ == "__main__":
    raise SystemExit(main())

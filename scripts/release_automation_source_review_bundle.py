"""Build a focused release-automation external source-review bundle."""

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

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v0.7/release-automation-source-review")
DISPATCH_ROOT = Path("var/review-packets/v0.6/dispatch")

SOURCE_FILES = [
    Path("Makefile"),
    Path("scripts/release_evidence.py"),
    Path("scripts/release_guardrails.py"),
    Path("scripts/review_packet_bundle.py"),
    Path("scripts/consolidate_review_packet.py"),
    Path("scripts/review_packet_diff.py"),
    Path("scripts/packet_redaction_scan.py"),
    Path("scripts/external_review_dispatch_packets.py"),
    Path("scripts/external_response_normalize.py"),
    Path("scripts/reviewer_artifact_manifest.py"),
    Path("scripts/source_review_transcript_packet.py"),
    Path("scripts/review_packet_source_pointers.py"),
    Path("scripts/external_review_closure_gate.py"),
    Path("scripts/capability_decision_report.py"),
    Path("scripts/no_new_powers_guardrail.py"),
    Path("scripts/v06_lane_status.py"),
]

TEST_FILES = [
    Path("tests/test_release_readiness.py"),
    Path("tests/test_docs_site.py"),
    Path("tests/test_adversarial_corpus.py"),
    Path("tests/test_resource_limit_check.py"),
]

CONTRACT_DOCS = [
    Path("docs/codex/release-evidence-schema.md"),
    Path("docs/codex/release-guardrail-expansion.md"),
    Path("docs/codex/packet-redaction-scanner.md"),
    Path("docs/codex/reviewer-artifact-manifest-v2.md"),
    Path("docs/codex/source-review-transcript-packet.md"),
    Path("docs/codex/review-packet-source-pointers.md"),
    Path("docs/codex/v0.6-external-review-dispatch-packets.md"),
    Path("docs/codex/v0.6-external-response-normalization.md"),
    Path("docs/codex/capability-expansion-gate.md"),
    Path("docs/codex/no-new-powers-guardrail.md"),
    Path("docs/codex/source-review-closure-matrix.md"),
    Path("docs/codex/v0.6-lane-status-board.md"),
    Path("docs/codex/v0.7-external-review-row-partition.md"),
    Path("docs/codex/v0.6-internal-proxy-review-operating-model.md"),
    Path("docs/codex/findings/sub-022-review-packet-artifact-hash-gate.md"),
    Path("docs/codex/findings/sub-023-review-bundle-json-transcripts.md"),
    Path("docs/codex/findings/sub-024-release-evidence-transcript-binding.md"),
    Path("docs/codex/findings/sub-025-review-finding-namespace-alignment.md"),
    Path("docs/codex/findings/sub-026-finding-summary-check-mode.md"),
    Path("docs/codex/findings/sub-054-release-evidence-signed-lock-required.md"),
    Path("docs/codex/findings/sub-060-review-artifact-staleness.md"),
    Path("docs/codex/findings/sub-061-signed-demo-verification-transcript.md"),
    Path("docs/codex/findings/sub-062-release-dispatch-evidence-commands.md"),
    Path("docs/codex/findings/sub-063-release-transcript-returncode.md"),
    Path("docs/codex/findings/sub-076-release-automation-dispatch-focus.md"),
    Path("docs/codex/findings/sub-077-review-candidate-dispatch-freshness.md"),
    Path("docs/codex/findings/sub-081-review-artifact-dispatch-inventory.md"),
    Path("docs/codex/findings/sub-082-dispatch-pointer-validation.md"),
    Path("docs/codex/findings/sub-083-release-automation-transcript-section.md"),
    Path("docs/codex/findings/sub-085-release-automation-source-inventory.md"),
    Path("docs/codex/findings/sub-086-release-transcript-doc-freshness.md"),
]

FOCUSED_TEST_COMMAND = [
    "uv",
    "run",
    "pytest",
    "tests/test_release_readiness.py",
    "-q",
]

EVIDENCE_COMMANDS = [
    ["make", "release-evidence"],
    ["make", "release-evidence-gate"],
    ["make", "packet-redaction-scan"],
    ["make", "reviewer-artifact-manifest"],
    ["make", "source-review-transcript-packet"],
    ["make", "v06-review-dispatch-packets"],
    ["make", "no-new-powers-guardrail"],
]


class ReleaseAutomationSourceReviewBundleError(RuntimeError):
    """Raised when the Release automation source-review bundle cannot be built."""


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
    except ReleaseAutomationSourceReviewBundleError as exc:
        print(f"Release automation source-review bundle failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built Release automation source-review bundle at {output_dir}")
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
        raise ReleaseAutomationSourceReviewBundleError(
            "working tree is dirty; commit before source-review handoff"
        )

    _build_dispatch_packets(repo_root, repo_root / DISPATCH_ROOT)
    dispatch_manifest_path = repo_root / DISPATCH_ROOT / "dispatch-packet-hashes.json"
    dispatch_manifest = json.loads(dispatch_manifest_path.read_text(encoding="utf-8"))
    release_automation_packet = _packet_metadata(dispatch_manifest)

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context: dict[str, Any] = {
        "commit": commit,
        "dirty": dirty,
        "dispatch_manifest_path": DISPATCH_ROOT / "dispatch-packet-hashes.json",
        "release_automation_packet_path": DISPATCH_ROOT / release_automation_packet["path"],
        "release_automation_packet_sha256": release_automation_packet["sha256"],
        "release_automation_packet_payload_sha256": release_automation_packet["payload_sha256"],
    }

    files: dict[str, str] = {
        "00_RELEASE_AUTOMATION_SOURCE_REVIEW_INDEX.md": _index(context),
        "01_RELEASE_AUTOMATION_SOURCE_REVIEW_PROMPT.md": _prompt(context),
        "02_RELEASE_AUTOMATION_DISPATCH_PACKET.md": _read(
            repo_root / context["release_automation_packet_path"]
        ),
        "03_RELEASE_AUTOMATION_SOURCE_BUNDLE.md": _bundle_sources(repo_root, SOURCE_FILES),
        "04_RELEASE_AUTOMATION_TESTS_BUNDLE.md": _bundle_sources(repo_root, TEST_FILES),
        "05_RELEASE_AUTOMATION_CONTRACTS_BUNDLE.md": _bundle_sources(repo_root, CONTRACT_DOCS),
        "08_RELEASE_AUTOMATION_INTAKE_COMMANDS.md": _intake_commands(context),
    }
    for relative, content in files.items():
        (output_dir / relative).write_text(content.rstrip() + "\n", encoding="utf-8")

    evidence_outputs = [
        _command_output(command, run_commands=run_commands) for command in EVIDENCE_COMMANDS
    ]
    (output_dir / "06_RELEASE_AUTOMATION_EVIDENCE.md").write_text(
        _mcp_evidence(evidence_outputs).rstrip() + "\n",
        encoding="utf-8",
    )
    _write_command_output(
        output_dir / "07_RELEASE_AUTOMATION_FOCUSED_TESTS.txt",
        _command_output(FOCUSED_TEST_COMMAND, run_commands=run_commands),
    )
    _write_json(
        output_dir / "release-automation-source-review-artifact-hashes.json",
        _hashes(output_dir),
    )
    return output_dir


def _index(context: dict[str, Any]) -> str:
    return f"""# Release Automation Source Review Handoff

This packet prepares the release/evidence automation lane for source-level external review. It
attaches release evidence generation, guardrails, redaction scan, packet/bundle generation,
dispatch-packet generation, response normalization, closure/capability gates, focused
release-readiness tests, prior internal findings, and command evidence needed to decide whether the
lane can close for the v0.1 local-preview boundary.

## Boundary

- Current review status: v0.8 roadmap/product-risk consultation after v0.6/v0.7 focused
  source-review lane closure for the v0.1 local-preview runtime boundary.
- Lane: Release automation.
- Finding namespace: `EXT-REL-###`.
- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Dispatch packet path: `{context["release_automation_packet_path"]}`.
- Dispatch packet whole-file SHA-256: `{context["release_automation_packet_sha256"]}`.
- Dispatch packet payload SHA-256: `{context["release_automation_packet_payload_sha256"]}`.

## Send These Files

1. `00_RELEASE_AUTOMATION_SOURCE_REVIEW_INDEX.md`
2. `01_RELEASE_AUTOMATION_SOURCE_REVIEW_PROMPT.md`
3. `02_RELEASE_AUTOMATION_DISPATCH_PACKET.md`
4. `03_RELEASE_AUTOMATION_SOURCE_BUNDLE.md`
5. `04_RELEASE_AUTOMATION_TESTS_BUNDLE.md`
6. `05_RELEASE_AUTOMATION_CONTRACTS_BUNDLE.md`
7. `06_RELEASE_AUTOMATION_EVIDENCE.md`
8. `07_RELEASE_AUTOMATION_FOCUSED_TESTS.txt`
9. `08_RELEASE_AUTOMATION_INTAKE_COMMANDS.md`
10. `release-automation-source-review-artifact-hashes.json`

## What This Does Not Prove

This packet does not close external review rows, approve public/security-product positioning,
approve capability expansion, prove production readiness, or make generated packets independent
external audits. It provides the source/test evidence needed for an external reviewer to decide
whether release/evidence automation rows can close for the v0.1 local-preview boundary.
"""


def _prompt(context: dict[str, Any]) -> str:
    finding_table = "\n".join(
        [
            "| Finding ID | Severity | Area | Affected files/functions | "
            "Blocking status | Disposition | Recommended fix |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            "| EXT-REL-### | critical/high/medium/low/informational | Release automation | "
            "path/function | blocking/should-fix/later/advisory | open | fix summary |",
        ]
    )
    return f"""# Release Automation Source Review Prompt

You are reviewing Ithildin as an external source reviewer for the release/evidence automation lane
only. Treat this as source-level review if and only if you inspect the attached release automation
source, focused release-readiness tests, contract docs, prior internal findings, and command
evidence.

Reviewed commit: `{context["commit"]}`
Reviewed dispatch packet hash: `{context["release_automation_packet_sha256"]}`
Reviewed dispatch payload hash: `{context["release_automation_packet_payload_sha256"]}`
Area: `release-automation`
Finding namespace: `EXT-REL-###`

## Scope

Please review:

- `make release-check` and `make review-candidate` run the promised gate sequence without
  overstating external closure or capability-expansion readiness;
- release evidence is schema-validated, secret-free, tied to repo root/commit/dirty state, and
  honest about runtime signing/configuration status;
- review bundle, consolidated packet, dispatch packets, artifact hashes, review-doc hashes, and
  transcript packets are deterministic enough for handoff and fail closed on missing inputs;
- redaction scans, no-new-powers guardrails, tool-surface invariant gates, closure gates, accepted
  risk checks, and capability-decision reports preserve the blocked capability-expansion state;
- external response normalization validates area/namespace binding and does not mutate findings or
  close rows by itself;
- generated packets explain what they do not prove: production readiness, independent source
  review, capability expansion approval, notarization, custody, hosted trust, or new tool powers;
- ignored generated artifacts do not include `.env`, private keys, runtime DBs, audit JSONL,
  `node_modules`, UI build output, or other local runtime secrets.

## Required Disposition

Please answer whether the release evidence, external-review dispatch packets, reviewer artifact
manifest, source-review transcript packet, response normalization, redaction/guardrail, and
capability/closure gate rows can be externally closed for the v0.1 local-preview runtime boundary.
If they cannot close, explain exactly which source/test/evidence item is missing or which
implementation issue blocks closure.

Use this exact finding table shape for actionable findings:

{finding_table}

If there are no implementation findings, explicitly say so and state whether the lane can close for
local-preview release/evidence automation. Do not approve public/security-product positioning,
capability expansion, production readiness, external notarization, hosted custody, or new governed
tool powers.
"""


def _intake_commands(context: dict[str, Any]) -> str:
    return f"""# Release Automation External Review Intake Commands

Store the raw external review response at:

```text
var/review-runs/v0.7/release-automation/raw-response.md
```

Normalize it with:

```bash
uv run python scripts/external_response_normalize.py \\
  var/review-runs/v0.7/release-automation/raw-response.md \\
  --reviewer "GPT 5.5 Pro" \\
  --reviewer-type "external-model" \\
  --source-access "source-level" \\
  --reviewed-commit "{context["commit"]}" \\
  --reviewed-packet-hash "{context["release_automation_packet_sha256"]}" \\
  --area "release-automation" \\
  --output var/review-runs/v0.7/release-automation/normalized-response.json
```

The normalizer accepts `EXT-REL-###` finding IDs for this lane. Normalized output does not mutate
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
            raise ReleaseAutomationSourceReviewBundleError(f"missing project marker: {marker}")


def _build_dispatch_packets(repo_root: Path, output_root: Path) -> dict[str, Any]:
    return external_review_dispatch_packets.build_dispatch_packets(repo_root, output_root)


def _packet_metadata(dispatch_manifest: dict[str, Any]) -> dict[str, Any]:
    for packet in dispatch_manifest.get("packets", []):
        if packet.get("path") == "release-automation.md":
            return dict(packet)
    raise ReleaseAutomationSourceReviewBundleError(
        "Release automation dispatch packet metadata is missing"
    )


def _bundle_sources(repo_root: Path, paths: list[Path]) -> str:
    sections: list[str] = []
    for relative in paths:
        path = repo_root / relative
        if not path.exists():
            raise ReleaseAutomationSourceReviewBundleError(
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
        raise ReleaseAutomationSourceReviewBundleError(f"{' '.join(command)} failed")
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
        "# Release Automation Evidence",
        "",
        "## Boundary Summary",
        "",
        "- Release automation remains evidence generation, guardrails, and handoff packaging only.",
        "- It does not close external review rows, approve capability expansion, or add tool",
        "  powers.",
        "- Generated packets are handoff artifacts, not independent audits or notarized evidence.",
        "- Capability expansion remains blocked until closure gates and accepted-risk status allow",
        "  it.",
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
        if path.name == "release-automation-source-review-artifact-hashes.json":
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
        raise ReleaseAutomationSourceReviewBundleError(
            f"required packet source is missing: {path}"
        )
    return path.read_text(encoding="utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


if __name__ == "__main__":
    raise SystemExit(main())

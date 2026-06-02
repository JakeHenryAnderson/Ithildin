"""Build a focused audit and signed-evidence external source-review bundle."""

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

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v0.7/signed-evidence-source-review")
DISPATCH_ROOT = Path("var/review-packets/v0.6/dispatch")

SOURCE_FILES = [
    Path("packages/audit-core/src/ithildin_audit_core/__init__.py"),
    Path("packages/audit-core/src/ithildin_audit_core/signing.py"),
    Path("packages/audit-core/src/ithildin_audit_core/writer.py"),
    Path("apps/api/src/ithildin_api/app.py"),
    Path("apps/api/src/ithildin_api/config.py"),
    Path("apps/api/src/ithildin_api/manifest_lock.py"),
    Path("scripts/audit_signing.py"),
    Path("scripts/manifest_lock_signing.py"),
    Path("scripts/signed_evidence_demo.py"),
    Path("scripts/signed_evidence_demo_verify.py"),
    Path("scripts/evidence_confusion_gate.py"),
    Path("scripts/release_evidence.py"),
]

TEST_FILES = [
    Path("tests/test_audit_writer.py"),
    Path("tests/test_audit_diagnostics.py"),
    Path("tests/test_signed_evidence_demo.py"),
    Path("tests/test_tool_registry.py"),
    Path("tests/test_api_service.py"),
    Path("tests/test_mcp_adapter.py"),
]

CONTRACT_DOCS = [
    Path("docs/codex/signed-evidence-source-review-checklist.md"),
    Path("docs/codex/signed-audit-exports.md"),
    Path("docs/codex/signed-manifest-locks.md"),
    Path("docs/codex/audit-integrity-adversarial-suite.md"),
    Path("docs/codex/evidence-contracts.md"),
    Path("docs/codex/evidence-contracts-v2.json"),
    Path("docs/codex/source-review-closure-matrix.md"),
    Path("docs/codex/v0.6-lane-status-board.md"),
    Path("docs/codex/v0.7-external-review-row-partition.md"),
    Path("docs/codex/v0.6-internal-review-execution-wave-2.md"),
    Path("docs/codex/findings/sub-010-signed-export-lifecycle-drift.md"),
    Path("docs/codex/findings/sub-011-signed-export-embedded-verification.md"),
    Path("docs/codex/findings/sub-012-audit-non-object-payload.md"),
    Path("docs/codex/findings/sub-013-audit-export-events.md"),
    Path("docs/codex/findings/sub-014-signed-demo-artifact-hashes.md"),
    Path("docs/codex/findings/sub-048-signed-export-failure-evidence.md"),
    Path("docs/codex/findings/sub-049-signed-export-metadata-validation.md"),
    Path("docs/codex/findings/sub-050-signed-export-trusted-key-docs.md"),
    Path("docs/codex/findings/sub-051-signed-export-non-object-bundle.md"),
    Path("docs/codex/findings/sub-052-audit-list-corrupt-payload.md"),
    Path("docs/codex/findings/sub-053-manifest-signature-lock-read-status.md"),
    Path("docs/codex/findings/sub-054-release-evidence-signed-lock-required.md"),
    Path("docs/codex/findings/sub-055-system-status-signature-startup-evidence.md"),
    Path("docs/codex/findings/sub-056-manifest-signature-untrusted-key-id.md"),
    Path("docs/codex/findings/sub-057-signed-demo-custom-lock-path.md"),
    Path("docs/codex/findings/sub-058-signed-evidence-closure-traceability.md"),
    Path("docs/codex/findings/sub-059-signed-evidence-dispatch-pointers.md"),
    Path("docs/codex/findings/sub-060-review-artifact-staleness.md"),
    Path("docs/codex/findings/sub-061-signed-demo-verification-transcript.md"),
]

FOCUSED_TEST_COMMAND = [
    "uv",
    "run",
    "pytest",
    "tests/test_audit_writer.py",
    "tests/test_audit_diagnostics.py",
    "tests/test_signed_evidence_demo.py",
    "tests/test_tool_registry.py",
    "tests/test_api_service.py",
    "tests/test_mcp_adapter.py",
    "-q",
]

EVIDENCE_COMMANDS = [
    ["make", "signed-evidence-demo"],
    ["make", "signed-evidence-demo-verify"],
    ["make", "evidence-confusion-gate"],
]


class SignedEvidenceSourceReviewBundleError(RuntimeError):
    """Raised when the signed-evidence source-review bundle cannot be built."""


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
    except SignedEvidenceSourceReviewBundleError as exc:
        print(f"signed evidence source-review bundle failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built signed evidence source-review bundle at {output_dir}")
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
        raise SignedEvidenceSourceReviewBundleError(
            "working tree is dirty; commit before source-review handoff"
        )

    _build_dispatch_packets(repo_root, repo_root / DISPATCH_ROOT)
    dispatch_manifest_path = repo_root / DISPATCH_ROOT / "dispatch-packet-hashes.json"
    dispatch_manifest = json.loads(dispatch_manifest_path.read_text(encoding="utf-8"))
    signed_packet = _packet_metadata(dispatch_manifest)

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context: dict[str, Any] = {
        "commit": commit,
        "dirty": dirty,
        "dispatch_manifest_path": DISPATCH_ROOT / "dispatch-packet-hashes.json",
        "signed_packet_path": DISPATCH_ROOT / signed_packet["path"],
        "signed_packet_sha256": signed_packet["sha256"],
        "signed_packet_payload_sha256": signed_packet["payload_sha256"],
    }

    files: dict[str, str] = {
        "00_SIGNED_EVIDENCE_SOURCE_REVIEW_INDEX.md": _index(context),
        "01_SIGNED_EVIDENCE_SOURCE_REVIEW_PROMPT.md": _prompt(context),
        "02_SIGNED_EVIDENCE_DISPATCH_PACKET.md": _read(
            repo_root / context["signed_packet_path"]
        ),
        "03_SIGNED_EVIDENCE_SOURCE_BUNDLE.md": _bundle_sources(repo_root, SOURCE_FILES),
        "04_SIGNED_EVIDENCE_TESTS_BUNDLE.md": _bundle_sources(repo_root, TEST_FILES),
        "05_SIGNED_EVIDENCE_CONTRACTS_BUNDLE.md": _bundle_sources(repo_root, CONTRACT_DOCS),
        "08_SIGNED_EVIDENCE_INTAKE_COMMANDS.md": _intake_commands(context),
    }
    for relative, content in files.items():
        (output_dir / relative).write_text(content.rstrip() + "\n", encoding="utf-8")

    evidence_outputs = [
        _command_output(command, run_commands=run_commands) for command in EVIDENCE_COMMANDS
    ]
    (output_dir / "06_SIGNED_EVIDENCE_EVIDENCE.md").write_text(
        _signed_evidence(evidence_outputs).rstrip() + "\n",
        encoding="utf-8",
    )
    _write_command_output(
        output_dir / "07_SIGNED_EVIDENCE_FOCUSED_TESTS.txt",
        _command_output(FOCUSED_TEST_COMMAND, run_commands=run_commands),
    )
    _write_json(
        output_dir / "signed-evidence-source-review-artifact-hashes.json",
        _hashes(output_dir),
    )
    return output_dir


def _index(context: dict[str, Any]) -> str:
    return f"""# Signed Evidence and Audit Source Review Handoff

This packet prepares the signed evidence, audit integrity, and manifest-lock verification lanes for
source-level external review. It attaches audit signing/export code, audit writer verification,
manifest-lock signature code, API wiring, CLI/demo scripts, focused tests, contract docs, prior
internal finding history, and command evidence.

## Boundary

- Current review status: v0.6/v0.7 external-review closure work for the v0.1 local-preview runtime
  boundary.
- Lane: signed evidence and audit.
- Finding namespace: `EXT-SE-###`.
- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Dispatch packet path: `{context["signed_packet_path"]}`.
- Dispatch packet whole-file SHA-256: `{context["signed_packet_sha256"]}`.
- Dispatch packet payload SHA-256: `{context["signed_packet_payload_sha256"]}`.

## Send These Files

1. `00_SIGNED_EVIDENCE_SOURCE_REVIEW_INDEX.md`
2. `01_SIGNED_EVIDENCE_SOURCE_REVIEW_PROMPT.md`
3. `02_SIGNED_EVIDENCE_DISPATCH_PACKET.md`
4. `03_SIGNED_EVIDENCE_SOURCE_BUNDLE.md`
5. `04_SIGNED_EVIDENCE_TESTS_BUNDLE.md`
6. `05_SIGNED_EVIDENCE_CONTRACTS_BUNDLE.md`
7. `06_SIGNED_EVIDENCE_EVIDENCE.md`
8. `07_SIGNED_EVIDENCE_FOCUSED_TESTS.txt`
9. `08_SIGNED_EVIDENCE_INTAKE_COMMANDS.md`
10. `signed-evidence-source-review-artifact-hashes.json`

## What This Does Not Prove

This packet does not close external review rows, approve public/security-product positioning,
approve capability expansion, or prove production security. It provides the source/test evidence
needed for an external reviewer to decide whether the signed evidence, audit integrity, and
manifest-lock verification lanes can be closed for the v0.1 local-preview boundary.
"""


def _prompt(context: dict[str, Any]) -> str:
    finding_table = "\n".join(
        [
            "| Finding ID | Severity | Area | Affected files/functions | "
            "Blocking status | Disposition | Recommended fix |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            "| EXT-SE-### | critical/high/medium/low/informational | signed evidence/audit | "
            "path/function | blocking/should-fix/later/advisory | open | fix summary |",
        ]
    )
    return f"""# Signed Evidence and Audit Source Review Prompt

You are reviewing Ithildin as an external source reviewer for the signed evidence and audit lanes
only. Treat this as source-level review if and only if you inspect the attached source bundle,
focused tests, contract docs, prior internal findings, demo evidence, and command transcripts.

Reviewed commit: `{context["commit"]}`
Reviewed dispatch packet hash: `{context["signed_packet_sha256"]}`
Reviewed dispatch payload hash: `{context["signed_packet_payload_sha256"]}`
Area: `signed-evidence`
Finding namespace: `EXT-SE-###`

## Scope

Please review:

- audit JSONL/hash-chain verification and export behavior;
- signed audit export payload construction, digest binding, key ID handling, public key trust, and
  offline verification;
- manifest-lock signature payload construction, lock digest binding, key ID/public key validation,
  startup enforcement, status reporting, and MCP/API enforcement;
- signed-evidence demo generation and verification using ignored non-production fixture keys;
- release/system status distinction between runtime signing status and demo signing evidence;
- audit export events, lifecycle diagnostics, corrupt payload handling, and safe errors;
- wording boundaries that keep local signatures separate from external notarization, hosted
  custody, immutable storage, official release signing, or production key management.

## Required Disposition

Please answer whether the signed evidence, audit integrity, and manifest-lock verification lanes can
be externally closed for the v0.1 local-preview runtime boundary. If they cannot close, explain
exactly which source/test/evidence item is missing or which implementation issue blocks closure.

Use this exact finding table shape for actionable findings:

{finding_table}

If there are no implementation findings, explicitly say so and state whether the lanes can close
for local-preview signed evidence and audit. Do not approve external notarization, hosted custody,
immutable evidence, official supply-chain signing, production key management, per-event signatures,
public/security-product positioning, or new governed tool powers.
"""


def _intake_commands(context: dict[str, Any]) -> str:
    return f"""# Signed Evidence External Review Intake Commands

Store the raw external review response at:

```text
var/review-runs/v0.7/signed-evidence/raw-response.md
```

Normalize it with:

```bash
uv run python scripts/external_response_normalize.py \\
  var/review-runs/v0.7/signed-evidence/raw-response.md \\
  --reviewer "GPT 5.5 Pro" \\
  --reviewer-type "external-model" \\
  --source-access "source-level" \\
  --reviewed-commit "{context["commit"]}" \\
  --reviewed-packet-hash "{context["signed_packet_sha256"]}" \\
  --area "signed-evidence" \\
  --output var/review-runs/v0.7/signed-evidence/normalized-response.json
```

The normalizer accepts `EXT-SE-###` finding IDs for this lane. Normalized output does not mutate
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
            raise SignedEvidenceSourceReviewBundleError(f"missing project marker: {marker}")


def _build_dispatch_packets(repo_root: Path, output_root: Path) -> dict[str, Any]:
    return external_review_dispatch_packets.build_dispatch_packets(repo_root, output_root)


def _packet_metadata(dispatch_manifest: dict[str, Any]) -> dict[str, Any]:
    for packet in dispatch_manifest.get("packets", []):
        if packet.get("path") == "signed-evidence.md":
            return dict(packet)
    raise SignedEvidenceSourceReviewBundleError(
        "signed evidence dispatch packet metadata is missing"
    )


def _bundle_sources(repo_root: Path, paths: list[Path]) -> str:
    sections: list[str] = []
    for relative in paths:
        path = repo_root / relative
        if not path.exists():
            raise SignedEvidenceSourceReviewBundleError(
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
        raise SignedEvidenceSourceReviewBundleError(f"{' '.join(command)} failed")
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


def _signed_evidence(outputs: list[dict[str, Any]]) -> str:
    sections = [
        "# Signed Evidence and Audit Evidence",
        "",
        "## Boundary Summary",
        "",
        "- Runtime audit signing and signed-manifest-lock enforcement are explicit local",
        "  configuration; trust roots are not silently generated.",
        "- The signed-evidence demo uses ignored non-production fixture keys and is separate from",
        "  runtime signing configuration.",
        "- Signed exports are local authenticity/integrity evidence, not external notarization,",
        "  hosted custody, immutable storage, official release signing, or production key",
        "  management.",
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
        if path.name == "signed-evidence-source-review-artifact-hashes.json":
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
        raise SignedEvidenceSourceReviewBundleError(
            f"required packet source is missing: {path}"
        )
    return path.read_text(encoding="utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


if __name__ == "__main__":
    raise SystemExit(main())

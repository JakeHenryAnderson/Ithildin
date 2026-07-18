"""Build the trusted-host promotion runtime source-review bundle."""

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

from scripts import (  # noqa: E402
    no_new_powers_guardrail,
    tool_surface_invariant_gate,
    trusted_host_promotion_runtime_implementation_decision_check,
)

DEFAULT_OUTPUT_DIR = Path(
    "var/review-packets/v3/trusted-host-promotion-runtime-source-review"
)
HASH_MANIFEST = "trusted-host-promotion-runtime-source-review-artifact-hashes.json"
FINDING_NAMESPACE = "EXT-TRUSTED-HOST-RUNTIME-###"

SOURCE_FILES = [
    "apps/api/src/ithildin_api/trusted_host_promotions.py",
    "apps/api/src/ithildin_api/app.py",
    "apps/api/src/ithildin_api/config.py",
    "apps/api/src/ithildin_api/approvals.py",
    "apps/api/src/ithildin_api/read_tools.py",
    "apps/api/src/ithildin_api/sandbox_descriptors.py",
]
TEST_FILES = [
    "tests/test_api_service.py",
    "tests/test_release_readiness.py",
]
CONTRACT_DOCS = [
    "docs/codex/trusted-host-promotion-runtime-implementation-decision.md",
    "docs/codex/trusted-host-promotion-runtime-implementation.md",
    "docs/codex/v3-trusted-host-promotion-runtime-internal-review.md",
    "docs/codex/v3-trusted-host-promotion-runtime-review-closure.md",
    "docs/codex/v3-trusted-host-promotion-runtime-local-disposition.md",
    "docs/codex/trusted-host-promotion-runtime-source-review.md",
    "docs/codex/trusted-host-promotion-limited-runtime-ticket.md",
    "docs/codex/trusted-host-promotion-limited-runtime-plan.md",
    "docs/codex/trusted-host-promotion-zone-contract.md",
    "docs/codex/trusted-host-promotion-negative-fixtures.md",
    "docs/codex/sandbox-promotion-evidence-contract.md",
    "docs/codex/findings/ext-trusted-host-runtime-001-proposal-approval-binding.md",
    "docs/codex/findings/ext-trusted-host-runtime-002-governance-bindings.md",
    "docs/codex/findings/ext-trusted-host-runtime-003-source-object-race.md",
    "docs/codex/findings/ext-trusted-host-runtime-004-completion-audit-state.md",
    "docs/codex/findings/ext-trusted-host-runtime-005-packet-freshness.md",
    "docs/codex/findings/ext-trusted-host-runtime-006-adversarial-coverage.md",
]
FOCUSED_TEST_COMMAND = [
    "uv",
    "run",
    "pytest",
    "tests/test_api_service.py::test_trusted_host_promotion_stages_single_artifact_after_approval",
    "tests/test_api_service.py::test_trusted_host_promotion_denies_stale_and_unsafe_inputs",
    "tests/test_api_service.py::test_trusted_host_promotion_binds_route_proposal_and_allows_one_attempt",
    "tests/test_api_service.py::test_trusted_host_promotion_rejects_unsafe_source_object_types",
    "tests/test_api_service.py::test_trusted_host_promotion_concurrent_apply_stages_once",
    "tests/test_api_service.py::test_trusted_host_promotion_preserves_existing_destination",
    "tests/test_api_service.py::test_trusted_host_promotion_audit_failure_remains_incomplete",
    "-q",
]


class TrustedHostPromotionRuntimeSourceReviewBundleError(RuntimeError):
    """Raised when the runtime source-review bundle cannot be built."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--skip-commands", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    try:
        if args.check:
            report = build_check_report(Path.cwd())
            print(_json(report))
            return 0 if report["valid"] else 1
        output_dir = build_bundle(
            repo_root=Path.cwd().resolve(),
            output_dir=args.output_dir,
            allow_dirty=args.allow_dirty,
            run_commands=not args.skip_commands,
        )
    except TrustedHostPromotionRuntimeSourceReviewBundleError as exc:
        print(
            f"trusted-host promotion runtime source-review bundle failed: {exc}",
            file=sys.stderr,
        )
        return 1
    print(f"Built trusted-host promotion runtime source-review bundle at {output_dir}")
    return 0


def build_check_report(
    repo_root: Path,
    *,
    validate_existing_packet: bool = True,
) -> dict[str, Any]:
    failures: list[str] = []
    _collect_missing(repo_root, SOURCE_FILES, "source", failures)
    _collect_missing(repo_root, TEST_FILES, "test", failures)
    _collect_missing(repo_root, CONTRACT_DOCS, "contract", failures)

    decision = trusted_host_promotion_runtime_implementation_decision_check.build_report(
        repo_root
    )
    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    for label, report in [
        ("runtime implementation decision", decision),
        ("tool surface", tool_surface),
        ("no-new-powers", no_new_powers),
    ]:
        failures.extend(f"{label}: {failure}" for failure in report["failures"])

    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    docs_site = (repo_root / "scripts/build_docs_site.py").read_text(encoding="utf-8")
    review_docs = (repo_root / "scripts/review_docs.py").read_text(encoding="utf-8")
    release_guardrails = (repo_root / "scripts/release_guardrails.py").read_text(
        encoding="utf-8"
    )
    review_index = (repo_root / "docs/codex/review-docs-index.md").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]

    checks = [
        ("Make bundle target", "trusted-host-promotion-runtime-source-review-bundle:", makefile),
        (
            "Make check target",
            "trusted-host-promotion-runtime-source-review-bundle-check:",
            makefile,
        ),
        (
            "release-check target",
            "trusted-host-promotion-runtime-source-review-bundle-check",
            release_check_body,
        ),
        (
            "README command",
            "make trusted-host-promotion-runtime-source-review-bundle",
            readme,
        ),
        (
            "docs site runtime review doc",
            "docs/codex/trusted-host-promotion-runtime-source-review.md",
            docs_site,
        ),
        (
            "review docs runtime review doc",
            "docs/codex/trusted-host-promotion-runtime-source-review.md",
            review_docs,
        ),
        (
            "docs site internal review doc",
            "docs/codex/v3-trusted-host-promotion-runtime-internal-review.md",
            docs_site,
        ),
        (
            "docs site closure review doc",
            "docs/codex/v3-trusted-host-promotion-runtime-review-closure.md",
            docs_site,
        ),
        (
            "docs site local disposition doc",
            "docs/codex/v3-trusted-host-promotion-runtime-local-disposition.md",
            docs_site,
        ),
        (
            "review docs internal review doc",
            "docs/codex/v3-trusted-host-promotion-runtime-internal-review.md",
            review_docs,
        ),
        (
            "review docs closure review doc",
            "docs/codex/v3-trusted-host-promotion-runtime-review-closure.md",
            review_docs,
        ),
        (
            "review docs local disposition doc",
            "docs/codex/v3-trusted-host-promotion-runtime-local-disposition.md",
            review_docs,
        ),
        (
            "review index runtime review",
            "Trusted-Host Promotion Runtime Source Review",
            review_index,
        ),
        (
            "review index internal runtime review",
            "Trusted-Host Promotion Runtime Internal Review",
            review_index,
        ),
        (
            "review index runtime closure",
            "Trusted-Host Promotion Runtime Review Closure",
            review_index,
        ),
        (
            "review index local disposition",
            "Trusted-Host Promotion Runtime Local Disposition",
            review_index,
        ),
        (
            "release guardrail target",
            "trusted-host-promotion-runtime-source-review-bundle-check",
            release_guardrails,
        ),
    ]
    for label, needle, haystack in checks:
        if needle not in haystack:
            failures.append(f"{label} missing: {needle}")

    runtime_review = (
        repo_root / "docs/codex/trusted-host-promotion-runtime-source-review.md"
    ).read_text(encoding="utf-8")
    internal_review = (
        repo_root / "docs/codex/v3-trusted-host-promotion-runtime-internal-review.md"
    ).read_text(encoding="utf-8")
    closure_review = (
        repo_root / "docs/codex/v3-trusted-host-promotion-runtime-review-closure.md"
    ).read_text(encoding="utf-8")
    local_disposition = (
        repo_root / "docs/codex/v3-trusted-host-promotion-runtime-local-disposition.md"
    ).read_text(encoding="utf-8")
    for text_label, text in [
        ("runtime review", runtime_review),
        ("internal review", internal_review),
        ("closure review", closure_review),
        ("local disposition", local_disposition),
    ]:
        if FINDING_NAMESPACE not in text:
            failures.append(f"{text_label} missing finding namespace {FINDING_NAMESPACE}")
    if "No critical or high implementation findings" not in internal_review:
        failures.append("internal review does not record no critical/high findings")
    if "Disposition: `local_reviewed_external_pending`" not in closure_review:
        failures.append("closure review does not record local_reviewed_external_pending")
    if "Disposition: `external_review_received_remediation_pending`" not in local_disposition:
        failures.append(
            "local disposition does not record external_review_received_remediation_pending"
        )
    if tool_surface.get("tool_count") != 24:
        failures.append(f"tool count changed: {tool_surface.get('tool_count')!r}")
    if decision.get("runtime_implementation_allowed_next") is not True:
        failures.append("runtime decision no longer allows the staging-only slice")

    packet_evidence = _existing_packet_evidence(repo_root)
    if validate_existing_packet and packet_evidence["present"]:
        if not packet_evidence["commit_matches_head"]:
            failures.append(
                "existing runtime source-review packet is not bound to current HEAD"
            )
        if not packet_evidence["generated_from_clean_tree"]:
            failures.append(
                "existing runtime source-review packet was generated from a dirty tree"
            )
        if not packet_evidence["artifact_hashes_match_files"]:
            failures.append(
                "existing runtime source-review packet artifact hashes do not match files"
            )

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "finding_namespace": FINDING_NAMESPACE,
        "output_dir": DEFAULT_OUTPUT_DIR.as_posix(),
        "tool_count": tool_surface.get("tool_count"),
        "runtime_slice": "staging_only_single_artifact",
        "source_review_status": "ready_for_external_source_review",
        "existing_packet": packet_evidence,
        "broad_host_promotion_allowed": False,
        "new_governed_tool_allowed": False,
    }


def build_bundle(
    *,
    repo_root: Path,
    output_dir: Path,
    allow_dirty: bool = False,
    run_commands: bool = True,
) -> Path:
    _require_project_root(repo_root)
    check = build_check_report(repo_root, validate_existing_packet=False)
    if check["failures"]:
        raise TrustedHostPromotionRuntimeSourceReviewBundleError(
            "; ".join(check["failures"])
        )
    commit = _git(repo_root, ["rev-parse", "HEAD"])
    dirty = bool(_git(repo_root, ["status", "--short"]))
    if dirty and not allow_dirty:
        raise TrustedHostPromotionRuntimeSourceReviewBundleError(
            "working tree is dirty; commit before source-review handoff"
        )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context = {
        "commit": commit,
        "dirty": dirty,
        "check": check,
    }
    files = {
        "00_TRUSTED_HOST_PROMOTION_RUNTIME_SOURCE_REVIEW_INDEX.md": _index(context),
        "01_TRUSTED_HOST_PROMOTION_RUNTIME_SOURCE_REVIEW_PROMPT.md": _prompt(context),
        "02_TRUSTED_HOST_PROMOTION_RUNTIME_SOURCE_BUNDLE.md": _bundle_files(
            repo_root, SOURCE_FILES
        ),
        "03_TRUSTED_HOST_PROMOTION_RUNTIME_TESTS_BUNDLE.md": _bundle_files(
            repo_root, TEST_FILES
        ),
        "04_TRUSTED_HOST_PROMOTION_RUNTIME_CONTRACTS_BUNDLE.md": _bundle_files(
            repo_root, CONTRACT_DOCS
        ),
        "05_TRUSTED_HOST_PROMOTION_RUNTIME_GATE_EVIDENCE.json": _json(check),
        "08_TRUSTED_HOST_PROMOTION_RUNTIME_INTAKE_COMMANDS.md": _intake_commands(),
    }
    for name, content in files.items():
        (output_dir / name).write_text(_packet_text(content), encoding="utf-8")

    decision_output = _command_output(
        ["make", "trusted-host-promotion-runtime-implementation-decision-check"],
        run_commands=run_commands,
    )
    negative_output = _command_output(
        ["make", "trusted-host-promotion-negative-transcripts"],
        run_commands=run_commands,
    )
    no_new_powers_output = _command_output(
        ["make", "no-new-powers-guardrail"],
        run_commands=run_commands,
    )
    tool_surface_output = _command_output(
        ["make", "tool-surface-invariant-gate"],
        run_commands=run_commands,
    )
    (output_dir / "06_TRUSTED_HOST_PROMOTION_RUNTIME_EVIDENCE.md").write_text(
        _packet_text(
            _evidence(
                decision_output,
                negative_output,
                no_new_powers_output,
                tool_surface_output,
            )
        ),
        encoding="utf-8",
    )
    _write_command_output(
        output_dir / "07_TRUSTED_HOST_PROMOTION_RUNTIME_FOCUSED_TESTS.txt",
        _command_output(FOCUSED_TEST_COMMAND, run_commands=run_commands),
    )
    _write_json(output_dir / HASH_MANIFEST, _hashes(output_dir))
    return output_dir


def _index(context: dict[str, Any]) -> str:
    return f"""# Trusted-Host Promotion Runtime Source Review Handoff

This packet prepares the implemented staging-only `ERG-005` runtime slice for source review.

## Boundary

- Lane: trusted-host promotion runtime.
- Finding namespace: `{FINDING_NAMESPACE}`.
- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Tool count: `{context["check"]["tool_count"]}`.
- Runtime slice: one stored sandbox/workspace artifact -> one approved local host-staging placement.
- MCP/tool manifest exposure: not added.
- Approved-output publishing: not implemented.
- Arbitrary host paths or broad host writes: not implemented.

## Send These Files

1. `00_TRUSTED_HOST_PROMOTION_RUNTIME_SOURCE_REVIEW_INDEX.md`
2. `01_TRUSTED_HOST_PROMOTION_RUNTIME_SOURCE_REVIEW_PROMPT.md`
3. `02_TRUSTED_HOST_PROMOTION_RUNTIME_SOURCE_BUNDLE.md`
4. `03_TRUSTED_HOST_PROMOTION_RUNTIME_TESTS_BUNDLE.md`
5. `04_TRUSTED_HOST_PROMOTION_RUNTIME_CONTRACTS_BUNDLE.md`
6. `05_TRUSTED_HOST_PROMOTION_RUNTIME_GATE_EVIDENCE.json`
7. `06_TRUSTED_HOST_PROMOTION_RUNTIME_EVIDENCE.md`
8. `07_TRUSTED_HOST_PROMOTION_RUNTIME_FOCUSED_TESTS.txt`
9. `08_TRUSTED_HOST_PROMOTION_RUNTIME_INTAKE_COMMANDS.md`
10. `{HASH_MANIFEST}`

## What This Does Not Approve

This packet does not approve broad trusted-host promotion, arbitrary host paths,
overwrite/delete/move behavior, approved-output publishing, Mission Control runtime authority,
sandbox orchestration, SIEM adapter behavior, compliance automation, production identity, runtime
Postgres, hosted telemetry, remote MCP, shell, Docker, Kubernetes, browser automation, arbitrary
HTTP, plugin SDK behavior, or public/security-product positioning.
"""


def _prompt(context: dict[str, Any]) -> str:
    return f"""# Trusted-Host Promotion Runtime Source Review Prompt

You are reviewing Ithildin as a source reviewer for the implemented staging-only trusted-host
promotion runtime slice. Treat this as source-level review if and only if you inspect the attached
source bundle, focused tests, contract docs, gate evidence, and command evidence.

Reviewed commit: `{context["commit"]}`
Area: `trusted-host-promotion-runtime`
Finding namespace: `{FINDING_NAMESPACE}`

Please answer whether this lane can be locally dispositioned for the v0.1 local-preview runtime
boundary. If it cannot, explain exactly which implementation issue or evidence gap blocks closure.

Review that:

- all runtime routes are admin-protected;
- no MCP tool, tool manifest, or governed tool power was added;
- proposals and apply payloads are closed and bounded;
- source artifacts are relative, workspace-confined, UTF-8 text, size-limited, and re-hashed before
  staging;
- hidden/sensitive paths, `.git`, symlinks, hardlinks, traversal, stale hashes, replayed approvals,
  and extra apply fields fail safely;
- approval consumption is one-time and evidence-bound;
- host staging accepts only safe `host-staging://<label>` labels, not raw host paths;
- placement uses create-exclusive behavior and does not overwrite;
- API responses, audit events, diagnostics, and transcripts do not expose file contents, diffs,
  prompts, secrets, raw sensitive paths, or raw host paths.

Use finding IDs in the `EXT-TRUSTED-HOST-RUNTIME-###` namespace. For each actionable finding,
include severity, area, affected files/functions, blocking status, disposition, and recommended
fix.

Do not approve broad host writes, approved-output publishing, Mission Control runtime authority,
sandbox orchestration, SIEM custody, compliance automation, production positioning, public/security
product claims, or new governed tool powers.
"""


def _evidence(
    decision_output: str,
    negative_output: str,
    no_new_powers_output: str,
    tool_surface_output: str,
) -> str:
    return f"""# Trusted-Host Promotion Runtime Evidence

## Runtime Implementation Decision

```text
{decision_output}
```

## Observed Negative Transcripts

```text
{negative_output}
```

## No-New-Powers Guardrail

```text
{no_new_powers_output}
```

## Tool Surface Invariant

```text
{tool_surface_output}
```
"""


def _intake_commands() -> str:
    return """# Trusted-Host Promotion Runtime Intake Commands

```bash
make trusted-host-promotion-runtime-implementation-decision-check
make trusted-host-promotion-negative-transcripts
make no-new-powers-guardrail
make tool-surface-invariant-gate
uv run pytest \\
  tests/test_api_service.py::test_trusted_host_promotion_stages_single_artifact_after_approval \\
  tests/test_api_service.py::test_trusted_host_promotion_denies_stale_and_unsafe_inputs \\
  -q
```
"""


def _bundle_files(repo_root: Path, paths: list[str]) -> str:
    chunks: list[str] = []
    for relative in paths:
        path = repo_root / relative
        if not path.exists():
            raise TrustedHostPromotionRuntimeSourceReviewBundleError(
                f"missing bundle file: {relative}"
            )
        chunks.append(f"## {relative}\n\n```text\n{path.read_text(encoding='utf-8')}\n```")
    return "\n\n".join(chunks)


def _collect_missing(
    repo_root: Path, paths: list[str], label: str, failures: list[str]
) -> None:
    for relative in paths:
        if not (repo_root / relative).exists():
            failures.append(f"missing {label}: {relative}")


def _command_output(command: list[str], *, run_commands: bool) -> str:
    if not run_commands:
        return f"skipped command: {' '.join(command)}"
    process = subprocess.run(command, text=True, capture_output=True, check=False)
    output = (process.stdout + process.stderr).strip()
    return f"$ {' '.join(command)}\nexit_code={process.returncode}\n{output}"


def _write_command_output(path: Path, output: str) -> None:
    path.write_text(output + "\n", encoding="utf-8")


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(_json(payload) + "\n", encoding="utf-8")


def _json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _hashes(output_dir: Path) -> list[dict[str, Any]]:
    records = []
    for path in sorted(output_dir.iterdir()):
        if path.name == HASH_MANIFEST:
            continue
        data = path.read_bytes()
        records.append(
            {
                "path": path.name,
                "sha256": f"sha256:{hashlib.sha256(data).hexdigest()}",
                "bytes": len(data),
            }
        )
    return records


def _existing_packet_evidence(
    repo_root: Path,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    output_dir = output_dir or repo_root / DEFAULT_OUTPUT_DIR
    if not output_dir.is_dir():
        return {
            "present": False,
            "commit": None,
            "commit_matches_head": None,
            "generated_from_clean_tree": None,
            "artifact_hashes_match_files": None,
        }

    head = _git(repo_root, ["rev-parse", "HEAD"])
    index_path = output_dir / "00_TRUSTED_HOST_PROMOTION_RUNTIME_SOURCE_REVIEW_INDEX.md"
    prompt_path = output_dir / "01_TRUSTED_HOST_PROMOTION_RUNTIME_SOURCE_REVIEW_PROMPT.md"
    manifest_path = output_dir / HASH_MANIFEST
    index = index_path.read_text(encoding="utf-8") if index_path.is_file() else ""
    prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.is_file() else ""
    packet_commit = _extract_packet_commit(index)
    prompt_commit = _extract_packet_commit(prompt)

    hashes_match = False
    try:
        recorded_hashes = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        recorded_hashes = None
    if isinstance(recorded_hashes, list):
        hashes_match = recorded_hashes == _hashes(output_dir)

    return {
        "present": True,
        "commit": packet_commit,
        "commit_matches_head": packet_commit == head and prompt_commit == head,
        "generated_from_clean_tree": "Dirty at generation: `false`." in index,
        "artifact_hashes_match_files": hashes_match,
    }


def _extract_packet_commit(text: str) -> str | None:
    marker = "Reviewed commit: `"
    if marker not in text:
        return None
    return text.partition(marker)[2].partition("`")[0] or None


def _packet_text(text: str) -> str:
    return text.strip() + "\n"


def _require_project_root(repo_root: Path) -> None:
    for marker in ("pyproject.toml", "Makefile", "tool-manifests.lock.json"):
        if not (repo_root / marker).exists():
            raise TrustedHostPromotionRuntimeSourceReviewBundleError(
                "not an Ithildin repository root"
            )


def _git(repo_root: Path, args: list[str]) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if process.returncode != 0:
        raise TrustedHostPromotionRuntimeSourceReviewBundleError(process.stderr.strip())
    return process.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())

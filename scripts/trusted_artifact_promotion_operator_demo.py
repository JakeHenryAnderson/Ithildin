"""Generate and validate the ERG-005 trusted artifact promotion operator demo packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (  # noqa: E402
    no_new_powers_guardrail,
    review_docs,
    tool_surface_invariant_gate,
    trusted_host_promotion_runtime_source_review_bundle,
)

DEFAULT_OUTPUT_DIR = Path(
    "var/review-packets/v3/trusted-artifact-promotion-operator-demo"
)
HASH_MANIFEST = "trusted-artifact-promotion-operator-demo-artifact-hashes.json"
DOC = Path("docs/codex/trusted-artifact-promotion-operator-demo.md")
REQUIRED_PACKET_FILES = {
    "00_TRUSTED_ARTIFACT_PROMOTION_OPERATOR_DEMO_INDEX.md",
    "01_GUIDED_OPERATOR_FLOW.md",
    "02_COMMAND_CENTER_FRAMING.md",
    "03_DEMO_SCENARIO.md",
    "04_EVIDENCE_MAP.md",
    "05_LIVE_WALKTHROUGH_PREP.md",
    "06_BOUNDARY_FLAGS.md",
    HASH_MANIFEST,
}
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]


class TrustedArtifactPromotionOperatorDemoError(RuntimeError):
    """Raised when the operator demo packet cannot be generated or validated."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    try:
        if args.check:
            report = build_check_report(Path.cwd().resolve())
            if args.json_output:
                print(json.dumps(report, indent=2, sort_keys=True))
            else:
                print(render_report(report))
            return 0 if report["valid"] else 1
        output_dir = build_packet(
            repo_root=Path.cwd().resolve(),
            output_dir=args.output_dir,
            allow_dirty=args.allow_dirty,
        )
    except TrustedArtifactPromotionOperatorDemoError as exc:
        print(f"trusted artifact promotion operator demo failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built trusted artifact promotion operator demo at {output_dir}")
    return 0


def build_packet(*, repo_root: Path, output_dir: Path, allow_dirty: bool = False) -> Path:
    _require_project_root(repo_root)
    commit = _git(repo_root, ["rev-parse", "HEAD"])
    dirty = bool(_git(repo_root, ["status", "--short"]))
    if dirty and not allow_dirty:
        raise TrustedArtifactPromotionOperatorDemoError(
            "working tree is dirty; commit or pass --allow-dirty before building the demo packet"
        )
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context = {
        "commit": commit,
        "dirty": dirty,
        "tool_count": 24,
        "packet_path": output_dir.as_posix(),
        "runtime_slice": "ERG-005 staging-only single-artifact promotion",
        "source_review_packet": (
            "var/review-packets/v3/trusted-host-promotion-runtime-source-review"
        ),
        "observed_sandbox_packet": "var/review-packets/v3/sandbox-artifact-observed-demo",
        "negative_transcripts": (
            "var/review-packets/v3/trusted-host-promotion-negative-transcripts"
        ),
    }
    files = {
        "00_TRUSTED_ARTIFACT_PROMOTION_OPERATOR_DEMO_INDEX.md": _index(context),
        "01_GUIDED_OPERATOR_FLOW.md": _guided_flow(context),
        "02_COMMAND_CENTER_FRAMING.md": _command_center_framing(context),
        "03_DEMO_SCENARIO.md": _demo_scenario(context),
        "04_EVIDENCE_MAP.md": _evidence_map(context),
        "05_LIVE_WALKTHROUGH_PREP.md": _walkthrough_prep(context),
        "06_BOUNDARY_FLAGS.md": _boundary_flags(context),
    }
    for name, text in files.items():
        output_dir.joinpath(name).write_text(text.rstrip() + "\n", encoding="utf-8")
    output_dir.joinpath(HASH_MANIFEST).write_text(
        json.dumps(_hashes(output_dir), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_dir


def build_check_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    _require_project_root(repo_root)
    makefile = repo_root.joinpath("Makefile").read_text(encoding="utf-8")
    readme = repo_root.joinpath("README.md").read_text(encoding="utf-8")
    docs_site = repo_root.joinpath("scripts/build_docs_site.py").read_text(encoding="utf-8")
    review_index = repo_root.joinpath("docs/codex/review-docs-index.md").read_text(
        encoding="utf-8"
    )
    release_guardrails = repo_root.joinpath("scripts/release_guardrails.py").read_text(
        encoding="utf-8"
    )
    release_check_body = makefile.partition("release-check:")[2].partition("\n\n")[0]
    doc_rel = DOC.as_posix()

    tool_surface = tool_surface_invariant_gate.build_report(repo_root)
    no_new_powers = no_new_powers_guardrail.build_report(repo_root)
    runtime_bundle = trusted_host_promotion_runtime_source_review_bundle.build_check_report(
        repo_root
    )
    failures.extend(f"tool-surface: {failure}" for failure in tool_surface["failures"])
    failures.extend(f"no-new-powers: {failure}" for failure in no_new_powers["failures"])
    failures.extend(
        f"runtime-source-review: {failure}" for failure in runtime_bundle["failures"]
    )

    if not repo_root.joinpath(DOC).exists():
        failures.append("trusted artifact promotion operator demo doc is missing")
    else:
        doc_text = repo_root.joinpath(DOC).read_text(encoding="utf-8")
        for phrase in [
            "sandbox/workspace-side artifact",
            "Ithildin Command Center is the operator display and review surface",
            "one create-exclusive staging placement",
            "make trusted-artifact-promotion-operator-demo",
            "Tool count remains `24`",
            "does not add governed tools",
        ]:
            if phrase not in doc_text:
                failures.append(f"demo doc missing phrase: {phrase}")

    checks = [
        ("Make packet target", "trusted-artifact-promotion-operator-demo:", makefile),
        (
            "Make check target",
            "trusted-artifact-promotion-operator-demo-check:",
            makefile,
        ),
        (
            "release-check target",
            "trusted-artifact-promotion-operator-demo-check",
            release_check_body,
        ),
        (
            "release guardrail fragment",
            "trusted-artifact-promotion-operator-demo-check",
            release_guardrails,
        ),
        ("README packet command", "make trusted-artifact-promotion-operator-demo", readme),
        (
            "README check command",
            "make trusted-artifact-promotion-operator-demo-check",
            readme,
        ),
        ("docs-site doc", doc_rel, docs_site),
        ("review docs doc", doc_rel, "\n".join(review_docs.REVIEW_DOCS)),
        (
            "review index",
            "Trusted Artifact Promotion Operator Demo",
            review_index,
        ),
    ]
    for label, needle, haystack in checks:
        if needle not in haystack:
            failures.append(f"{label} missing: {needle}")

    packet_report = _packet_report(repo_root)
    failures.extend(packet_report["failures"])

    if tool_surface.get("tool_count") != 24:
        failures.append(f"tool count changed: {tool_surface.get('tool_count')!r}")

    return {
        "schema_version": "1",
        "valid": not failures,
        "failures": failures,
        "tool_count": tool_surface.get("tool_count"),
        "packet": packet_report,
        "output_dir": DEFAULT_OUTPUT_DIR.as_posix(),
        "runtime_changes_allowed": False,
        "command_center_runtime_authority_allowed": False,
        "broad_host_promotion_allowed": False,
        "new_power_classes_allowed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "Ithildin trusted artifact promotion operator demo check",
        f"valid: {str(report['valid']).lower()}",
        f"tool_count: {report.get('tool_count')}",
        f"output_dir: {report['output_dir']}",
        "runtime_changes_allowed: false",
        "command_center_runtime_authority_allowed: false",
        "broad_host_promotion_allowed: false",
        "new_power_classes_allowed: false",
    ]
    if report["failures"]:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines)


def _packet_report(repo_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "trusted-artifact-promotion-operator-demo"
        build_packet(repo_root=repo_root, output_dir=output_dir, allow_dirty=True)
        names = {path.name for path in output_dir.iterdir()}
        if names != REQUIRED_PACKET_FILES:
            failures.append(f"packet files mismatch: {sorted(names)}")
        hashes = json.loads(output_dir.joinpath(HASH_MANIFEST).read_text(encoding="utf-8"))
        hashed_paths = {record["path"] for record in hashes}
        expected_hashed = REQUIRED_PACKET_FILES - {HASH_MANIFEST}
        if hashed_paths != expected_hashed:
            failures.append(f"hash manifest paths mismatch: {sorted(hashed_paths)}")
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in output_dir.glob("*.md")
        )
        normalized_combined = " ".join(combined.split())
        for phrase in [
            "sandbox/workspace-produced artifact",
            "approval-bound promotion proposal",
            "create-exclusive placement",
            "Ithildin Command Center",
            "not the promotion engine",
            "make trusted-host-promotion-runtime-source-review-bundle",
            "stop and ask Codex to guide the walkthrough",
        ]:
            if phrase not in normalized_combined:
                failures.append(f"packet missing phrase: {phrase}")
        for forbidden in [
            "public/security-product approval",
            "Command Center enforcement authority: true",
            "broad host writes allowed",
            "sandbox orchestration allowed",
            "trusted_host_promotion_allowed: true",
        ]:
            if forbidden in combined:
                failures.append(f"packet contains forbidden phrase: {forbidden}")
    return {"valid": not failures, "failures": failures}


def _index(context: dict[str, Any]) -> str:
    return f"""# Trusted Artifact Promotion Operator Demo

This packet is the front-door runway for a live/manual walkthrough of the bounded `ERG-005`
trusted artifact promotion slice. It is generated without starting services, calling governed
tools, approving proposals, or staging host files.

## Status

- commit: `{context["commit"]}`
- dirty: `{str(context["dirty"]).lower()}`
- tool_count: `{context["tool_count"]}`
- runtime_slice: `{context["runtime_slice"]}`
- packet_path: `{context["packet_path"]}`

## Reading Order

1. `00_TRUSTED_ARTIFACT_PROMOTION_OPERATOR_DEMO_INDEX.md`
2. `01_GUIDED_OPERATOR_FLOW.md`
3. `02_COMMAND_CENTER_FRAMING.md`
4. `03_DEMO_SCENARIO.md`
5. `04_EVIDENCE_MAP.md`
6. `05_LIVE_WALKTHROUGH_PREP.md`
7. `06_BOUNDARY_FLAGS.md`
8. `{HASH_MANIFEST}`

## Stop Point

After this packet is generated and checked, stop and ask Codex to guide the walkthrough. The
walkthrough should be observed with the operator present rather than silently promoted by an
unattended automation.
"""


def _guided_flow(context: dict[str, Any]) -> str:
    return """# Guided Operator Flow

The operator story is:

1. Confirm a sandbox/workspace-produced artifact exists in safe evidence.
2. Inspect safe metadata: artifact label, source zone label, byte count, SHA-256 digest, and
   output-policy flags.
3. Confirm the promotion proposal binds one artifact digest, one approval, one configured staging
   destination label, and create-exclusive placement.
4. Approve only after the digest, source label, and destination label match operator intent.
5. Verify Ithildin stages exactly the approved bytes and records matching audit/proposal/approval
   evidence.
6. Export or inspect evidence showing the digest-bound transfer and any denial cases.

The flow is intentionally one artifact at a time. It is not a general file manager, host sync tool,
approved-output publisher, or broad trusted-host write path.
"""


def _command_center_framing(context: dict[str, Any]) -> str:
    return """# Command Center Framing

Ithildin Command Center is the operator-facing display and review surface for this demo. It may
show status, warnings, artifact metadata, approval binding, staging result evidence, and next
operator actions.

It is not the promotion engine. It does not bypass policy, create approvals by itself, stage host
files by itself, become a second audit authority, or turn Mission Control/Command Center artifacts
into runtime authority. Ithildin remains the governed gateway and source of truth.

Expected UI-facing language should prefer:

- `review artifact metadata`
- `verify digest binding`
- `approve one staging placement`
- `inspect staging evidence`
- `export local evidence`

Avoid language that implies sandbox orchestration, automatic host publishing, production custody,
compliance automation, public security-product approval, or host-wide protection.
"""


def _demo_scenario(context: dict[str, Any]) -> str:
    return """# Demo Scenario

Use the smallest useful artifact-promotion story:

- source: observed sandbox/workspace artifact evidence;
- artifact label: `hello-world-summary.txt` or equivalent fixture label;
- digest: SHA-256 computed before proposal;
- approval-bound promotion proposal: one artifact digest, one destination label, and one approval;
- proposal: one artifact, one destination label, one approval requirement;
- execution: one create-exclusive staged file under configured trusted-host staging root;
- verification: staged bytes hash to the approved digest;
- export: safe evidence packet, audit metadata, proposal/approval status, and negative transcripts.

Useful preparation commands:

```sh
make sandbox-artifact-observed-demo
make trusted-host-promotion-negative-transcripts
make trusted-host-promotion-runtime-source-review-bundle
make trusted-artifact-promotion-operator-demo
make trusted-artifact-promotion-operator-demo-check
```

This packet does not itself run a live promotion. It prepares the operator runway so the live/manual
step can be guided and observed.
"""


def _evidence_map(context: dict[str, Any]) -> str:
    return f"""# Evidence Map

Expected evidence surfaces:

- observed sandbox artifact packet: `{context["observed_sandbox_packet"]}`
- trusted-host runtime source-review packet: `{context["source_review_packet"]}`
- ERG-005 negative transcripts: `{context["negative_transcripts"]}`
- runtime implementation decision:
  `docs/codex/trusted-host-promotion-runtime-implementation-decision.md`
- runtime implementation contract: `docs/codex/trusted-host-promotion-runtime-implementation.md`
- runtime internal review: `docs/codex/v3-trusted-host-promotion-runtime-internal-review.md`
- runtime local disposition: `docs/codex/v3-trusted-host-promotion-runtime-local-disposition.md`

Evidence should prove:

- proposal and approval are bound to the artifact digest;
- staged output hash matches the approved digest;
- replay, stale, traversal, overwrite, unapproved, and wrong-digest cases are denied;
- audit metadata uses IDs, hashes, labels, counts, and status only;
- file contents, prompts, secrets, raw sensitive paths, and broad host state are not exposed.
"""


def _walkthrough_prep(context: dict[str, Any]) -> str:
    return """# Live Walkthrough Prep

Before the live/manual walkthrough:

1. Run `make trusted-artifact-promotion-operator-demo-check`.
2. Run `make sandbox-artifact-observed-demo-check`.
3. Run `make trusted-host-promotion-runtime-source-review-bundle-check`.
4. Confirm `git status --short` is clean except ignored generated packet artifacts.
5. Open this packet and keep the boundary flags visible.

Operator inspection checklist:

- artifact label is visible as safe metadata;
- source zone/workspace label is visible;
- SHA-256 digest is visible before approval;
- destination label is visible and is not a broad host folder;
- one-time approval binding is visible;
- proposal/request/approval IDs are visible as IDs, not raw contents;
- staged artifact digest can be compared with the approved digest;
- denial evidence exists for replay, stale, traversal, overwrite, unapproved, and wrong-digest
  cases.

During the walkthrough:

- do not approve a proposal unless the expected artifact digest and destination label are visible;
- do not use broad host folders as staging destinations;
- do not treat Command Center display as an enforcement decision;
- stop if the UI/API evidence differs from the packet expectations;
- stop and ask Codex to guide the walkthrough if any evidence surface is missing or ambiguous.

After the walkthrough:

- capture the staged artifact digest;
- compare it with the approved digest;
- export or record audit/proposal/approval evidence;
- run the relevant focused check before claiming the demo succeeded.

What this walkthrough can prove:

- Ithildin can present and verify a digest-bound, approval-bound, create-exclusive staging story for
  one artifact;
- Command Center can be framed as display/review only;
- the operator can follow the evidence trail without raw file contents or broad host state.

What this walkthrough does not prove:

- broad trusted-host promotion;
- production custody, SIEM retention, compliance automation, or public/security-product readiness;
- sandbox/VM orchestration;
- host-wide protection from activity outside Ithildin;
- Command Center enforcement authority.
"""


def _boundary_flags(context: dict[str, Any]) -> str:
    return """# Boundary Flags

- runtime_changes_allowed: `false` for this packet generator
- command_center_runtime_authority_allowed: `false`
- sandbox_orchestration_allowed: `false`
- broad_host_promotion_allowed: `false`
- trusted_host_promotion_allowed: `false` for any broad/general promotion claim
- staging_only_single_artifact_slice_available: `true`
- create_exclusive_only: `true`
- one_artifact_per_approval: `true`
- shell_execution_allowed: `false`
- docker_socket_access_allowed: `false`
- kubernetes_tools_allowed: `false`
- browser_automation_tools_allowed: `false`
- arbitrary_http_allowed: `false`
- production_identity_allowed: `false`
- runtime_postgres_allowed: `false`
- hosted_telemetry_allowed: `false`
- remote_mcp_allowed: `false`
- siem_adapter_allowed: `false`
- compliance_automation_allowed: `false`
- public_security_product_positioning_allowed: `false`
- new_power_classes_allowed: `false`

The only positive runtime claim is that the already implemented ERG-005 staging-only slice can be
used for one approved create-exclusive local staging placement when its existing API, policy,
approval, and audit checks pass.
"""


def _hashes(output_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(output_dir.iterdir()):
        if path.name == HASH_MANIFEST or not path.is_file():
            continue
        records.append(
            {
                "path": path.name,
                "bytes": path.stat().st_size,
                "sha256": f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}",
            }
        )
    return records


def _git(repo_root: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def _require_project_root(repo_root: Path) -> None:
    missing = [
        marker.as_posix()
        for marker in PROJECT_MARKERS
        if not repo_root.joinpath(marker).exists()
    ]
    if missing:
        raise TrustedArtifactPromotionOperatorDemoError(
            f"not an Ithildin repository root; missing {', '.join(missing)}"
        )


if __name__ == "__main__":
    raise SystemExit(main())

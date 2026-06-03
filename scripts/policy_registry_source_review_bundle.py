"""Build a focused policy/registry external source-review bundle."""

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

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v0.7/policy-registry-source-review")
DISPATCH_ROOT = Path("var/review-packets/v0.6/dispatch")

SOURCE_FILES = [
    Path("packages/policy-core/src/ithildin_policy_core/evaluator.py"),
    Path("packages/policy-core/src/ithildin_policy_core/types.py"),
    Path("packages/policy-core/src/ithildin_policy_core/opa.py"),
    Path("packages/policy-core/src/ithildin_policy_core/opa_bundle.py"),
    Path("apps/api/src/ithildin_api/policy.py"),
    Path("apps/api/src/ithildin_api/policy_preview.py"),
    Path("apps/api/src/ithildin_api/policy_parity.py"),
    Path("apps/api/src/ithildin_api/policy_impact.py"),
    Path("apps/api/src/ithildin_api/tool_calls.py"),
    Path("apps/api/src/ithildin_api/resources.py"),
    Path("apps/api/src/ithildin_api/decision_evidence.py"),
    Path("apps/api/src/ithildin_api/schema_validation.py"),
    Path("apps/api/src/ithildin_api/yaml_utils.py"),
    Path("apps/api/src/ithildin_api/registry.py"),
    Path("apps/api/src/ithildin_api/manifest_lock.py"),
    Path("apps/api/src/ithildin_api/identity.py"),
    Path("apps/api/src/ithildin_api/workspaces.py"),
    Path("apps/api/src/ithildin_api/app.py"),
    Path("scripts/policy_test.py"),
    Path("scripts/policy_parity.py"),
    Path("scripts/manifest_lock.py"),
    Path("scripts/manifest_change_review.py"),
    Path("policies/default.yaml"),
    Path("policies/tests/default.yaml"),
    Path("policies/tests/parity.yaml"),
    Path("principals/local.yaml"),
    Path("workspaces/local.yaml"),
]

TEST_FILES = [
    Path("tests/test_policy_parity.py"),
    Path("tests/test_policy_test_harness.py"),
    Path("tests/test_policy_impact.py"),
    Path("tests/test_policy_evaluator.py"),
    Path("tests/test_opa_policy_evaluator.py"),
    Path("tests/test_tool_registry.py"),
    Path("tests/test_identity.py"),
    Path("tests/test_workspaces.py"),
    Path("tests/test_api_service.py"),
    Path("tests/test_governed_tool_calls.py"),
    Path("tests/test_manifest_change_review.py"),
]

CONTRACT_DOCS = [
    Path("docs/codex/policy-parity-source-review-checklist.md"),
    Path("docs/codex/policy-parity-harness.md"),
    Path("docs/codex/registry-fail-closed-suite.md"),
    Path("docs/codex/opa-parity-decision.md"),
    Path("docs/codex/manifest-validation-suite.md"),
    Path("docs/codex/manifest-change-review-workflow.md"),
    Path("docs/codex/source-review-closure-matrix.md"),
    Path("docs/codex/v0.6-lane-status-board.md"),
    Path("docs/codex/v0.7-external-review-row-partition.md"),
    Path("docs/codex/v0.6-internal-subagent-review-wave.md"),
    Path("docs/codex/v0.6-internal-review-execution-wave-2.md"),
    Path("docs/codex/v0.6-internal-proxy-review-operating-model.md"),
    Path("docs/codex/findings/sub-015-filesystem-resource-scope.md"),
    Path("docs/codex/findings/sub-016-manifest-input-schema-validation.md"),
    Path("docs/codex/findings/sub-017-policy-parity-resource-scope.md"),
    Path("docs/codex/findings/sub-064-empty-preview-principal.md"),
    Path("docs/codex/findings/sub-065-patch-apply-parity-service.md"),
    Path("docs/codex/findings/sub-066-validation-error-value-leak.md"),
    Path("docs/codex/findings/sub-067-pre-policy-denial-evidence.md"),
    Path("docs/codex/findings/sub-068-workspace-registry-strict-fail-open.md"),
    Path("docs/codex/findings/sub-069-manifest-drift-status.md"),
    Path("docs/codex/findings/sub-070-duplicate-yaml-keys.md"),
    Path("docs/codex/findings/sub-071-policy-registry-closure-traceability.md"),
    Path("docs/codex/findings/sub-072-policy-registry-dispatch-coverage.md"),
    Path("docs/codex/findings/sub-073-policy-registry-lane-result.md"),
]

FOCUSED_TEST_COMMAND = [
    "uv",
    "run",
    "pytest",
    "tests/test_policy_parity.py",
    "tests/test_policy_test_harness.py",
    "tests/test_policy_impact.py",
    "tests/test_policy_evaluator.py",
    "tests/test_opa_policy_evaluator.py",
    "tests/test_tool_registry.py",
    "tests/test_identity.py",
    "tests/test_workspaces.py",
    "tests/test_api_service.py",
    "tests/test_governed_tool_calls.py",
    "-q",
]

EVIDENCE_COMMANDS = [
    ["make", "policy-test"],
    ["make", "policy-parity"],
    ["make", "manifest-lock-check"],
    ["make", "manifest-change-review"],
]


class PolicyRegistrySourceReviewBundleError(RuntimeError):
    """Raised when the policy/registry source-review bundle cannot be built."""


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
    except PolicyRegistrySourceReviewBundleError as exc:
        print(f"policy/registry source-review bundle failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built policy/registry source-review bundle at {output_dir}")
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
        raise PolicyRegistrySourceReviewBundleError(
            "working tree is dirty; commit before source-review handoff"
        )

    _build_dispatch_packets(repo_root, repo_root / DISPATCH_ROOT)
    dispatch_manifest_path = repo_root / DISPATCH_ROOT / "dispatch-packet-hashes.json"
    dispatch_manifest = json.loads(dispatch_manifest_path.read_text(encoding="utf-8"))
    policy_packet = _packet_metadata(dispatch_manifest)

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    context: dict[str, Any] = {
        "commit": commit,
        "dirty": dirty,
        "dispatch_manifest_path": DISPATCH_ROOT / "dispatch-packet-hashes.json",
        "policy_packet_path": DISPATCH_ROOT / policy_packet["path"],
        "policy_packet_sha256": policy_packet["sha256"],
        "policy_packet_payload_sha256": policy_packet["payload_sha256"],
    }

    files: dict[str, str] = {
        "00_POLICY_REGISTRY_SOURCE_REVIEW_INDEX.md": _index(context),
        "01_POLICY_REGISTRY_SOURCE_REVIEW_PROMPT.md": _prompt(context),
        "02_POLICY_REGISTRY_DISPATCH_PACKET.md": _read(
            repo_root / context["policy_packet_path"]
        ),
        "03_POLICY_REGISTRY_SOURCE_BUNDLE.md": _bundle_sources(repo_root, SOURCE_FILES),
        "04_POLICY_REGISTRY_TESTS_BUNDLE.md": _bundle_sources(repo_root, TEST_FILES),
        "05_POLICY_REGISTRY_CONTRACTS_BUNDLE.md": _bundle_sources(repo_root, CONTRACT_DOCS),
        "08_POLICY_REGISTRY_INTAKE_COMMANDS.md": _intake_commands(context),
    }
    for relative, content in files.items():
        (output_dir / relative).write_text(content.rstrip() + "\n", encoding="utf-8")

    evidence_outputs = [
        _command_output(command, run_commands=run_commands) for command in EVIDENCE_COMMANDS
    ]
    (output_dir / "06_POLICY_REGISTRY_EVIDENCE.md").write_text(
        _policy_registry_evidence(evidence_outputs).rstrip() + "\n",
        encoding="utf-8",
    )
    _write_command_output(
        output_dir / "07_POLICY_REGISTRY_FOCUSED_TESTS.txt",
        _command_output(FOCUSED_TEST_COMMAND, run_commands=run_commands),
    )
    _write_json(
        output_dir / "policy-registry-source-review-artifact-hashes.json",
        _hashes(output_dir),
    )
    return output_dir


def _index(context: dict[str, Any]) -> str:
    return f"""# Policy and Registry Source Review Handoff

This packet prepares the policy parity and registry fail-closed lanes for source-level external
review. It attaches policy-core evaluator code, API preview/runtime paths, resource construction,
decision evidence, manifest/principal/workspace registry loading, duplicate-key rejection,
manifest-lock evidence, focused tests, policy fixtures, prior internal finding history, and command
evidence.

## Boundary

- Current review status: v0.8 roadmap/product-risk consultation after v0.6/v0.7 focused
  source-review lane closure for the v0.1 local-preview runtime boundary.
- Lane: policy and registry.
- Finding namespace: `EXT-PR-###`.
- Reviewed commit: `{context["commit"]}`.
- Dirty at generation: `{str(context["dirty"]).lower()}`.
- Dispatch packet path: `{context["policy_packet_path"]}`.
- Dispatch packet whole-file SHA-256: `{context["policy_packet_sha256"]}`.
- Dispatch packet payload SHA-256: `{context["policy_packet_payload_sha256"]}`.

## Send These Files

1. `00_POLICY_REGISTRY_SOURCE_REVIEW_INDEX.md`
2. `01_POLICY_REGISTRY_SOURCE_REVIEW_PROMPT.md`
3. `02_POLICY_REGISTRY_DISPATCH_PACKET.md`
4. `03_POLICY_REGISTRY_SOURCE_BUNDLE.md`
5. `04_POLICY_REGISTRY_TESTS_BUNDLE.md`
6. `05_POLICY_REGISTRY_CONTRACTS_BUNDLE.md`
7. `06_POLICY_REGISTRY_EVIDENCE.md`
8. `07_POLICY_REGISTRY_FOCUSED_TESTS.txt`
9. `08_POLICY_REGISTRY_INTAKE_COMMANDS.md`
10. `policy-registry-source-review-artifact-hashes.json`

## What This Does Not Prove

This packet does not close external review rows, approve public/security-product positioning,
approve capability expansion, or prove production authorization. It provides the source/test
evidence needed for an external reviewer to decide whether the policy parity, registry fail-closed,
and policy source-review checklist rows can close for the v0.1 local-preview boundary.
"""


def _prompt(context: dict[str, Any]) -> str:
    finding_table = "\n".join(
        [
            "| Finding ID | Severity | Area | Affected files/functions | "
            "Blocking status | Disposition | Recommended fix |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            "| EXT-PR-### | critical/high/medium/low/informational | policy-registry | "
            "path/function | blocking/should-fix/later/advisory | open | fix summary |",
        ]
    )
    return f"""# Policy and Registry Source Review Prompt

You are reviewing Ithildin as an external source reviewer for the policy/registry lane only. Treat
this as source-level review if and only if you inspect the attached source bundle, focused tests,
policy fixtures, contract docs, prior internal findings, and command evidence.

Reviewed commit: `{context["commit"]}`
Reviewed dispatch packet hash: `{context["policy_packet_sha256"]}`
Reviewed dispatch payload hash: `{context["policy_packet_payload_sha256"]}`
Area: `policy-registry`
Finding namespace: `EXT-PR-###`

## Scope

Please review:

- default YAML policy evaluation, deny-default semantics, matched-rule evidence, obligations, and
  dangerous/destructive denial behavior;
- policy preview/runtime parity for principal/resource normalization, trusted principal handling,
  schema validation failures, and pre-policy denial evidence;
- local principal registry loading, disabled/unknown principal denial, role handling, and avoidance
  of caller-supplied role spoofing;
- workspace registry loading, strict missing-registry behavior, disabled workspace denial, root
  confinement, default workspace handling, and path escape prevention at the registry layer;
- tool manifest registry loading, duplicate name rejection, manifest-lock enforcement/status, and
  manifest drift evidence;
- duplicate-YAML-key rejection across policy fixtures, manifests, principal registries, and
  workspace registries;
- OPA/YAML boundary clarity: YAML remains canonical for local-preview gates while OPA remains
  optional verified sidecar evidence unless fixture parity support is explicitly configured later.

## Required Disposition

Please answer whether the policy parity, registry fail-closed, and policy source-review checklist
rows can be externally closed for the v0.1 local-preview runtime boundary. If they cannot close,
explain exactly which source/test/evidence item is missing or which implementation issue blocks
closure.

Use this exact finding table shape for actionable findings:

{finding_table}

If there are no implementation findings, explicitly say so and state whether the lane can close for
local-preview policy/registry behavior. Do not approve production identity, enterprise RBAC, OPA as
canonical runtime policy, remote MCP, public/security-product positioning, capability expansion, or
new governed tool powers.
"""


def _intake_commands(context: dict[str, Any]) -> str:
    return f"""# Policy and Registry External Review Intake Commands

Store the raw external review response at:

```text
var/review-runs/v0.7/policy-registry/raw-response.md
```

Normalize it with:

```bash
uv run python scripts/external_response_normalize.py \\
  var/review-runs/v0.7/policy-registry/raw-response.md \\
  --reviewer "GPT 5.5 Pro" \\
  --reviewer-type "external-model" \\
  --source-access "source-level" \\
  --reviewed-commit "{context["commit"]}" \\
  --reviewed-packet-hash "{context["policy_packet_sha256"]}" \\
  --area "policy-registry" \\
  --output var/review-runs/v0.7/policy-registry/normalized-response.json
```

The normalizer accepts `EXT-PR-###` finding IDs for this lane. Normalized output does not mutate
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
            raise PolicyRegistrySourceReviewBundleError(f"missing project marker: {marker}")


def _build_dispatch_packets(repo_root: Path, output_root: Path) -> dict[str, Any]:
    return external_review_dispatch_packets.build_dispatch_packets(repo_root, output_root)


def _packet_metadata(dispatch_manifest: dict[str, Any]) -> dict[str, Any]:
    for packet in dispatch_manifest.get("packets", []):
        if packet.get("path") == "policy-registry.md":
            return dict(packet)
    raise PolicyRegistrySourceReviewBundleError(
        "policy/registry dispatch packet metadata is missing"
    )


def _bundle_sources(repo_root: Path, paths: list[Path]) -> str:
    sections: list[str] = []
    for relative in paths:
        path = repo_root / relative
        if not path.exists():
            raise PolicyRegistrySourceReviewBundleError(
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
        raise PolicyRegistrySourceReviewBundleError(f"{' '.join(command)} failed")
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


def _policy_registry_evidence(outputs: list[dict[str, Any]]) -> str:
    sections = [
        "# Policy and Registry Evidence",
        "",
        "## Boundary Summary",
        "",
        "- YAML policy remains canonical for local-preview release gates.",
        "- OPA remains optional verified sidecar evidence unless a later fixture runner makes it",
        "  equivalent for policy parity checks.",
        "- Local principals are trusted local attribution labels, not production identity.",
        "- Principal/workspace/manifest registries are trusted local configuration and must fail",
        "  closed on malformed, duplicate, disabled, missing, or drifted evidence.",
        "- This packet does not add policy rules, registry mutation APIs, or new tool powers.",
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
        if path.name == "policy-registry-source-review-artifact-hashes.json":
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
        raise PolicyRegistrySourceReviewBundleError(
            f"required packet source is missing: {path}"
        )
    return path.read_text(encoding="utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


if __name__ == "__main__":
    raise SystemExit(main())

"""Generate an evidence-only Hello World sandbox demo packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/hello-world-sandbox-demo")
HELLO_CONTENT = "Hello World\n"
PROJECT_MARKERS = [
    Path("pyproject.toml"),
    Path("Makefile"),
    Path("apps/api"),
    Path("apps/mcp-server"),
    Path("tool-manifests.lock.json"),
]


class HelloWorldSandboxDemoPacketError(RuntimeError):
    """Raised when the Hello World sandbox demo packet cannot be generated."""


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
    except HelloWorldSandboxDemoPacketError as exc:
        print(f"Hello World sandbox demo packet failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built Hello World sandbox demo packet at {output_dir}")
    return 0


def build_packet(*, repo_root: Path, output_dir: Path, allow_dirty: bool = False) -> Path:
    _require_project_root(repo_root)
    commit = _git(repo_root, ["rev-parse", "HEAD"])
    dirty = bool(_git(repo_root, ["status", "--short"]))
    if dirty and not allow_dirty:
        raise HelloWorldSandboxDemoPacketError(
            "working tree is dirty; commit before generating the Hello World sandbox demo packet"
        )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    evidence_dir = output_dir / "evidence"
    mission_dir = output_dir / "mission-control"
    sandbox_dir = output_dir / "simulated-sandbox/hello-demo"
    staging_dir = output_dir / "host-staging/hello-demo"
    approved_dir = output_dir / "approved-host/hello-demo"
    for directory in [evidence_dir, mission_dir, sandbox_dir, staging_dir, approved_dir]:
        directory.mkdir(parents=True)

    sandbox_artifact = sandbox_dir / "hello.txt"
    staging_artifact = staging_dir / "hello.txt"
    approved_artifact = approved_dir / "hello.txt"
    sandbox_artifact.write_text(HELLO_CONTENT, encoding="utf-8")
    shutil.copyfile(sandbox_artifact, staging_artifact)
    shutil.copyfile(staging_artifact, approved_artifact)

    content_sha256 = _sha256(sandbox_artifact)
    mission = {
        "schema_version": "1",
        "mission_id": "mc-hello-world-demo",
        "operator_intent": "create hello-demo/hello.txt containing Hello World",
        "mission_control_runtime_behavior": False,
        "mission_control_authority": "metadata_only",
        "tool_count": 23,
    }
    plan = {
        "schema_version": "1",
        "run_id": "run_hello_world_demo",
        "model_client_label": "local-llm-plan-dry-run",
        "plan_status": "simulated_plan_only",
        "actions": [
            {
                "action": "write_text_file",
                "artifact_label": "sandbox://hello-demo/hello.txt",
                "content_sha256": content_sha256,
                "requires_approval": True,
            }
        ],
        "raw_model_prompt_recorded": False,
        "chain_of_thought_recorded": False,
    }
    approval = {
        "schema_version": "1",
        "approval_status": "simulated_required_not_executed",
        "approval_id": "approval_hello_world_demo_placeholder",
        "approval_binding_required": [
            "workspace_id",
            "sandbox_id",
            "artifact_label",
            "content_sha256",
            "policy_hash",
            "manifest_hash",
            "principal_id",
            "request_hash",
            "expiry",
        ],
        "approval_consumed": False,
    }
    promotion = {
        "schema_version": "1",
        "promotion_id": "promotion_hello_world_demo_simulated",
        "mission_id": mission["mission_id"],
        "run_id": plan["run_id"],
        "workspace_id": "demo",
        "sandbox_id": "operator-managed-demo-sandbox",
        "source_artifact_label": "sandbox://hello-demo/hello.txt",
        "source_artifact_sha256": content_sha256,
        "host_staging_label": "host-staging://hello-demo/hello.txt",
        "host_staging_sha256": _sha256(staging_artifact),
        "approved_host_label": "approved://hello-demo/hello.txt",
        "approved_host_sha256": _sha256(approved_artifact),
        "approval_id": approval["approval_id"],
        "auto_promotion_performed": False,
        "real_host_promotion_performed": False,
    }
    manifest = {
        "schema_version": "1",
        "packet": "hello-world-sandbox-demo",
        "status": "evidence_only_simulation",
        "commit": commit,
        "dirty": dirty,
        "tool_count": 23,
        "runtime_write_capability_implemented": False,
        "governed_tool_calls_performed": False,
        "mission_control_runtime_behavior": False,
        "real_vm_or_container_started": False,
        "sandbox_orchestration_performed": False,
        "shell_execution_performed": False,
        "host_promotion_performed": False,
        "artifact_content_sha256": content_sha256,
        "checks": {
            "sandbox_to_staging_hash_match": content_sha256 == _sha256(staging_artifact),
            "staging_to_approved_hash_match": _sha256(staging_artifact)
            == _sha256(approved_artifact),
            "hello_world_content_fixture": sandbox_artifact.read_text(encoding="utf-8")
            == HELLO_CONTENT,
        },
    }
    _write_json(mission_dir / "mission-control-intent.json", mission)
    _write_json(mission_dir / "local-llm-plan.json", plan)
    _write_json(mission_dir / "operator-approval-required.json", approval)
    _write_json(evidence_dir / "promotion-evidence-draft.json", promotion)
    _write_json(evidence_dir / "demo-manifest.json", manifest)
    (output_dir / "HELLO_WORLD_SANDBOX_DEMO_INDEX.md").write_text(
        _index(manifest, mission, plan, promotion).rstrip() + "\n",
        encoding="utf-8",
    )
    _write_json(output_dir / "artifact-hashes.json", _hashes(output_dir))
    return output_dir


def _index(
    manifest: dict[str, Any],
    mission: dict[str, Any],
    plan: dict[str, Any],
    promotion: dict[str, Any],
) -> str:
    return f"""# Hello World Sandbox Demo Packet

Status: evidence-only simulation.

This packet demonstrates the target evidence shape for the future Mission Control plus local LLM
plus Ithildin Hello World sandbox demo. It does not perform a governed tool call, start a VM,
orchestrate a sandbox, execute shell, add a runtime write capability, or promote an artifact to a
trusted host location.

## Demo Story

1. Mission Control records an operator intent.
2. A local LLM plan is represented as metadata only.
3. Operator approval is required but not consumed.
4. A deterministic simulated sandbox artifact is written inside this ignored packet directory.
5. Sandbox, host-staging, and approved-host labels have matching SHA-256 hashes.

## Evidence

- Commit: `{manifest["commit"]}`
- Dirty at generation: `{str(manifest["dirty"]).lower()}`
- Tool count: `{manifest["tool_count"]}`
- Mission ID: `{mission["mission_id"]}`
- Run ID: `{plan["run_id"]}`
- Approval ID: `{promotion["approval_id"]}`
- Artifact SHA-256: `{manifest["artifact_content_sha256"]}`
- Runtime write capability implemented: `false`
- Governed tool calls performed: `false`
- Mission Control runtime behavior: `false`
- Real VM or container started: `false`
- Host promotion performed: `false`

## Reading Order

1. `mission-control/mission-control-intent.json`
2. `mission-control/local-llm-plan.json`
3. `mission-control/operator-approval-required.json`
4. `evidence/demo-manifest.json`
5. `evidence/promotion-evidence-draft.json`
6. `artifact-hashes.json`
"""


def _hashes(output_dir: Path) -> dict[str, Any]:
    artifacts: list[dict[str, Any]] = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name == "artifact-hashes.json":
            continue
        artifacts.append(
            {
                "path": path.relative_to(output_dir).as_posix(),
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
        )
    return {
        "schema_version": "1",
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _git(repo_root: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def _require_project_root(repo_root: Path) -> None:
    missing = [str(marker) for marker in PROJECT_MARKERS if not (repo_root / marker).exists()]
    if missing:
        raise HelloWorldSandboxDemoPacketError(
            "must be run from the Ithildin repo root; missing " + ", ".join(missing)
        )


if __name__ == "__main__":
    raise SystemExit(main())

"""Generate observed trusted-host promotion negative transcripts."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ithildin_api.app import create_app
from ithildin_api.config import Settings

DEFAULT_OUTPUT_DIR = Path("var/review-packets/v3/trusted-host-promotion-negative")
TRANSCRIPT_NAME = "TRUSTED_HOST_PROMOTION_NEGATIVE_TRANSCRIPTS.md"


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    setup: str
    expected: str
    observed_status: int
    observed_reason: str
    evidence_pointer: str


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    transcript = build_transcripts(args.output_dir)
    print(f"Built trusted-host promotion negative transcripts at {transcript}")
    return 0


def build_transcripts(output_dir: Path) -> Path:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="ithildin-trusted-host-negative-") as temp_dir:
        root = Path(temp_dir)
        results = [
            _unauthenticated(root / "unauthenticated"),
            _hidden_source(root / "hidden-source"),
            _symlink_source(root / "symlink-source"),
            _hardlink_source(root / "hardlink-source"),
            _unsafe_staging_label(root / "unsafe-label"),
            _stale_artifact_hash(root / "stale-artifact"),
            _mismatched_proposal_approval(root / "mismatched-binding"),
            _replayed_approval(root / "replayed-approval"),
            _existing_destination(root / "existing-destination"),
            _unsupported_apply_field(root / "unsupported-apply-field"),
        ]
    transcript = output_dir / TRANSCRIPT_NAME
    transcript.write_text(_render(results), encoding="utf-8")
    return transcript


def _unauthenticated(root: Path) -> ScenarioResult:
    client, _settings, descriptor_id = _client(root)
    response = client.post(
        "/trusted-host-promotions/proposals",
        json=_proposal_payload(descriptor_id),
    )
    return _scenario(
        "Unauthenticated Proposal Denial",
        "POST /trusted-host-promotions/proposals without bearer token",
        "401 before any proposal, approval, or staging action",
        response.status_code,
        _reason(response.json()),
        "admin dependency rejected the request",
    )


def _hidden_source(root: Path) -> ScenarioResult:
    client, _settings, descriptor_id = _client(root)
    response = client.post(
        "/trusted-host-promotions/proposals",
        json={**_proposal_payload(descriptor_id), "source_artifact_path": ".env"},
        headers=_headers(),
    )
    return _scenario(
        "Hidden Source Denial",
        'proposal source_artifact_path=".env"',
        "400 without proposal, approval, or staging action",
        response.status_code,
        _reason(response.json()),
        "closed proposal schema rejected hidden/sensitive source",
    )


def _unsafe_staging_label(root: Path) -> ScenarioResult:
    client, _settings, descriptor_id = _client(root)
    response = client.post(
        "/trusted-host-promotions/proposals",
        json={**_proposal_payload(descriptor_id), "host_staging_label": "host-staging://bad/path"},
        headers=_headers(),
    )
    return _scenario(
        "Unsafe Staging Label Denial",
        'proposal host_staging_label="host-staging://bad/path"',
        "400 without raw host path resolution",
        response.status_code,
        _reason(response.json()),
        "host-staging labels allow one safe label segment only",
    )


def _symlink_source(root: Path) -> ScenarioResult:
    client, settings, descriptor_id = _client(root)
    settings.workspace_root.joinpath("linked.txt").symlink_to(
        settings.workspace_root / "summary.txt"
    )
    response = client.post(
        "/trusted-host-promotions/proposals",
        json={**_proposal_payload(descriptor_id), "source_artifact_path": "linked.txt"},
        headers=_headers(),
    )
    return _scenario(
        "Symlink Source Denial",
        'proposal source_artifact_path="linked.txt" points to a symlink',
        "400 without following the source object",
        response.status_code,
        _reason(response.json()),
        "descriptor-bound no-follow source read rejected the symlink",
    )


def _hardlink_source(root: Path) -> ScenarioResult:
    client, settings, descriptor_id = _client(root)
    os.link(
        settings.workspace_root / "summary.txt",
        settings.workspace_root / "hardlinked.txt",
    )
    response = client.post(
        "/trusted-host-promotions/proposals",
        json={**_proposal_payload(descriptor_id), "source_artifact_path": "hardlinked.txt"},
        headers=_headers(),
    )
    return _scenario(
        "Hardlink Source Denial",
        'proposal source_artifact_path="hardlinked.txt" has multiple links',
        "400 without accepting an ambiguous source object",
        response.status_code,
        _reason(response.json()),
        "opened source descriptor failed the single-link check",
    )


def _stale_artifact_hash(root: Path) -> ScenarioResult:
    client, settings, descriptor_id = _client(root)
    proposal = client.post(
        "/trusted-host-promotions/proposals",
        json=_proposal_payload(descriptor_id),
        headers=_headers(),
    ).json()
    approval_id = proposal["approval_id"]
    client.post(
        f"/approvals/{approval_id}/approve",
        json={"decision": "approve", "decided_by": "admin:local"},
        headers=_headers(),
    )
    settings.workspace_root.joinpath("summary.txt").write_text("changed\n", encoding="utf-8")
    response = client.post(
        f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
        json={"approval_id": approval_id},
        headers=_headers(),
    )
    return _scenario(
        "Stale Artifact Hash Denial",
        "source artifact changed after approval",
        "409 before staging placement",
        response.status_code,
        _reason(response.json()),
        "source artifact hash mismatch",
    )


def _mismatched_proposal_approval(root: Path) -> ScenarioResult:
    client, _settings, descriptor_id = _client(root)
    first = client.post(
        "/trusted-host-promotions/proposals",
        json=_proposal_payload(descriptor_id),
        headers=_headers(),
    ).json()
    second = client.post(
        "/trusted-host-promotions/proposals",
        json={
            **_proposal_payload(descriptor_id),
            "host_staging_label": "host-staging://second-output",
        },
        headers=_headers(),
    ).json()
    client.post(
        f"/approvals/{first['approval_id']}/approve",
        json={"decision": "approve", "decided_by": "admin:local"},
        headers=_headers(),
    )
    response = client.post(
        f"/trusted-host-promotions/proposals/{second['promotion_proposal_id']}/apply",
        json={"approval_id": first["approval_id"]},
        headers=_headers(),
    )
    return _scenario(
        "Mismatched Proposal Approval Denial",
        "apply route proposal differs from the approval-bound proposal",
        "409 before approval consumption or staging placement",
        response.status_code,
        _reason(response.json()),
        "route, proposal, scope, request, and approval binding review failed closed",
    )


def _replayed_approval(root: Path) -> ScenarioResult:
    client, _settings, descriptor_id = _client(root)
    proposal = client.post(
        "/trusted-host-promotions/proposals",
        json=_proposal_payload(descriptor_id),
        headers=_headers(),
    ).json()
    approval_id = proposal["approval_id"]
    client.post(
        f"/approvals/{approval_id}/approve",
        json={"decision": "approve", "decided_by": "admin:local"},
        headers=_headers(),
    )
    client.post(
        f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
        json={"approval_id": approval_id},
        headers=_headers(),
    )
    response = client.post(
        f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
        json={"approval_id": approval_id},
        headers=_headers(),
    )
    return _scenario(
        "Replayed Approval Denial",
        "second apply call reuses executed approval",
        "409 and no second staged artifact",
        response.status_code,
        _reason(response.json()),
        "approval compare-and-set rejected replay",
    )


def _existing_destination(root: Path) -> ScenarioResult:
    client, settings, descriptor_id = _client(root)
    proposal = client.post(
        "/trusted-host-promotions/proposals",
        json=_proposal_payload(descriptor_id),
        headers=_headers(),
    ).json()
    approval_id = proposal["approval_id"]
    client.post(
        f"/approvals/{approval_id}/approve",
        json={"decision": "approve", "decided_by": "admin:local"},
        headers=_headers(),
    )
    attempt_id = "thpa_" + hashlib.sha256(
        proposal["promotion_proposal_id"].encode("utf-8")
    ).hexdigest()[:32]
    destination = (
        settings.trusted_host_staging_root
        / "default"
        / proposal["promotion_proposal_id"]
        / f"{attempt_id}-summary-output.artifact"
    )
    destination.parent.mkdir(parents=True)
    destination.write_text("existing output\n", encoding="utf-8")
    response = client.post(
        f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
        json={"approval_id": approval_id},
        headers=_headers(),
    )
    preserved = destination.read_text(encoding="utf-8") == "existing output\n"
    return _scenario(
        "Existing Destination Denial",
        "deterministic final staging leaf already exists",
        "409 without overwriting the existing destination",
        response.status_code,
        _reason(response.json()),
        f"create-exclusive placement preserved existing destination: {str(preserved).lower()}",
    )


def _unsupported_apply_field(root: Path) -> ScenarioResult:
    client, _settings, descriptor_id = _client(root)
    proposal = client.post(
        "/trusted-host-promotions/proposals",
        json=_proposal_payload(descriptor_id),
        headers=_headers(),
    ).json()
    response = client.post(
        f"/trusted-host-promotions/proposals/{proposal['promotion_proposal_id']}/apply",
        json={"approval_id": proposal["approval_id"], "extra": True},
        headers=_headers(),
    )
    return _scenario(
        "Unsupported Apply Field Denial",
        "apply payload includes extra field",
        "400 closed input shape",
        response.status_code,
        _reason(response.json()),
        "apply endpoint accepts only approval_id",
    )


def _client(root: Path) -> tuple[TestClient, Settings, str]:
    settings = _settings(root)
    settings.workspace_root.mkdir(parents=True)
    settings.workspace_root.joinpath("summary.txt").write_text("original\n", encoding="utf-8")
    client = TestClient(create_app(settings))
    client.__enter__()
    response = client.post(
        "/sandbox-descriptors",
        json=_descriptor_payload(),
        headers=_headers(),
    )
    return client, settings, str(response.json()["descriptor_id"])


def _settings(root: Path) -> Settings:
    manifest_dir = root / "tool-manifests"
    manifest_dir.mkdir(parents=True)
    policy_path = root / "policy.yaml"
    policy_path.write_text("version: test\nrules: []\n", encoding="utf-8")
    policy_tests_path = root / "policy-tests.yaml"
    policy_tests_path.write_text("version: test\ncases: []\n", encoding="utf-8")
    workspace_root = root / "workspace"
    workspace_registry = root / "workspaces.yaml"
    workspace_registry.write_text(
        f"""
version: test
default_workspace_id: default
workspaces:
  - id: default
    root: {workspace_root.as_posix()}
    display_name: Default
    enabled: true
""",
        encoding="utf-8",
    )
    return Settings(
        admin_token="correct-token",
        audit_log_path=root / "audit.jsonl",
        db_path=root / "ithildin.sqlite3",
        manifest_dir=manifest_dir,
        require_manifest_lock=False,
        policy_path=policy_path,
        policy_tests_path=policy_tests_path,
        workspace_root=workspace_root,
        workspace_registry_path=workspace_registry,
        trusted_host_staging_root=root / "trusted-host-staging",
    )


def _descriptor_payload() -> dict[str, Any]:
    return {
        "workspace_id": "default",
        "principal_id": "agent:local-dev",
        "sandbox_id": "sandbox-demo",
        "sandbox_profile_id": "profile-demo",
        "vm_profile_hash": "sha256:" + ("1" * 64),
        "isolation_label": "operator-attested-vm",
        "network_posture_label": "host-only",
        "mount_root_label": "sandbox-workspace",
        "model_client_label": "local-llm",
        "descriptor_source": "operator_supplied",
        "vm_lifecycle_source": "operator_managed",
        "isolation_claim_source": "operator_attested",
        "network_posture_source": "operator_attested",
        "mount_posture_source": "operator_attested",
        "model_client_source": "operator_attested",
        "ithildin_live_inspection_performed": False,
        "ithildin_lifecycle_control_performed": False,
        "mission_control_runtime_authority_used": False,
        "trusted_host_promotion_performed": False,
    }


def _proposal_payload(descriptor_id: str) -> dict[str, Any]:
    return {
        "workspace_id": "default",
        "sandbox_descriptor_id": descriptor_id,
        "sandbox_id": "sandbox-demo",
        "source_artifact_path": "summary.txt",
        "host_staging_label": "host-staging://summary-output",
    }


def _headers() -> dict[str, str]:
    return {"Authorization": "Bearer correct-token"}


def _reason(payload: Any) -> str:
    if isinstance(payload, dict) and isinstance(payload.get("detail"), str):
        return str(payload["detail"])
    return "safe error"


def _scenario(
    name: str,
    setup: str,
    expected: str,
    status: int,
    reason: str,
    evidence: str,
) -> ScenarioResult:
    return ScenarioResult(
        name=name,
        setup=setup,
        expected=expected,
        observed_status=status,
        observed_reason=reason,
        evidence_pointer=evidence,
    )


def _render(results: list[ScenarioResult]) -> str:
    rows = "\n".join(
        (
            f"| {result.name} | {result.setup} | {result.expected} | "
            f"{result.observed_status} | {result.observed_reason} | "
            f"{result.evidence_pointer} |"
        )
        for result in results
    )
    return f"""# Trusted-Host Promotion Negative Transcripts

Status: observed local fixture denials for the staging-only `ERG-005` runtime slice.

These transcripts are generated from temporary local API fixtures. They do not use real secrets,
real customer files, raw host paths, shell execution, Mission Control runtime authority, sandbox
orchestration, local model invocation, SIEM adapters, or compliance automation.

| Scenario | Setup | Expected | Observed status | Observed safe reason | Evidence pointer |
| --- | --- | --- | --- | --- | --- |
{rows}
"""


if __name__ == "__main__":
    raise SystemExit(main())

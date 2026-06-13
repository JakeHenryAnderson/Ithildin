from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import NoReturn, cast
from urllib.request import Request

import pytest
from ithildin_api.agent_runs import AgentRunStore
from ithildin_api.approvals import ApprovalService, ApprovalStore, CreateApprovalInput
from ithildin_api.http_tools import HTTP_FETCH_TOOL, HttpAllowlist, HttpFetchExecutor
from ithildin_api.identity import PrincipalRegistry
from ithildin_api.patches import (
    PatchApplyAttempt,
    PatchApplyFaultHook,
    PatchProposalError,
    PatchProposalService,
    PatchProposalStore,
)
from ithildin_api.read_tools import ReadToolExecutor
from ithildin_api.registry import ToolRegistry
from ithildin_api.tool_calls import GovernedToolCallService
from ithildin_audit_core import AuditWriter
from ithildin_policy_core import PolicyEvaluator
from ithildin_schemas import AuditEventType, JsonObject, canonical_json, sha256_digest


class FakeHttpResponse:
    def __init__(
        self,
        *,
        body: bytes = b"hello network",
        content_type: str = "text/plain; charset=utf-8",
    ) -> None:
        self.body = body
        self.code = 200
        self.headers = {"Content-Type": content_type}

    def read(self, size: int) -> bytes:
        return self.body[:size]

    def getcode(self) -> int:
        return self.code


class FakeHttpOpener:
    def __init__(self, response: FakeHttpResponse | None = None) -> None:
        self.requests: list[Request] = []
        self.response = response or FakeHttpResponse()

    def open(self, fullurl: Request, timeout: float = 0) -> FakeHttpResponse:
        self.requests.append(fullurl)
        return self.response

    def open_pinned(
        self,
        fullurl: Request,
        *,
        parsed_url: object,
        resolved_ips: object,
        timeout: float = 0,
    ) -> FakeHttpResponse:
        return self.open(fullurl, timeout=timeout)


def write_policy(path: Path) -> None:
    path.write_text(
        """
version: test
rules:
  - id: deny_shell
    decision: deny
    reason: shell denied
    match:
      tool.name_prefix: shell.
    obligations:
      audit_level: full
  - id: require_write_approval
    decision: require_approval
    reason: writes require approval
    match:
      tool.risk: write
    obligations:
      audit_level: full
  - id: allow_write_proposals
    decision: allow
    reason: proposals allowed
    match:
      tool.risk: write-proposal
      resource.in_scope: true
    obligations:
      audit_level: full
  - id: allow_reads
    decision: allow
    reason: reads allowed
    match:
      tool.risk: read
      resource.in_scope: true
    obligations:
      audit_level: full
  - id: allow_network
    decision: allow
    reason: network allowed
    match:
      tool.risk: network
      resource.in_scope: true
    obligations:
      audit_level: full
""",
        encoding="utf-8",
    )


def write_manifest(manifest_dir: Path, name: str, risk: str, required: str = "path") -> None:
    manifest_dir.mkdir(exist_ok=True)
    manifest_dir.joinpath(f"{name.replace('.', '-')}.yaml").write_text(
        f"""
name: {name}
version: 1.0.0
title: {name}
risk: {risk}
category: test
mcp:
  exposed: true
input_schema:
  type: object
  additionalProperties: false
  required: ["{required}"]
  properties:
    {required}:
      type: string
""",
        encoding="utf-8",
    )


def write_patch_propose_manifest(manifest_dir: Path) -> None:
    manifest_dir.mkdir(exist_ok=True)
    manifest_dir.joinpath("fs-patch-propose.yaml").write_text(
        """
name: fs.patch.propose
version: 1.0.0
title: Propose patch
risk: write-proposal
category: test
mcp:
  exposed: true
input_schema:
  type: object
  additionalProperties: false
  required: ["path", "unified_diff"]
  properties:
    path:
      type: string
    unified_diff:
      type: string
""",
        encoding="utf-8",
    )


def write_patch_apply_manifest(manifest_dir: Path) -> None:
    manifest_dir.mkdir(exist_ok=True)
    manifest_dir.joinpath("fs-patch-apply.yaml").write_text(
        """
name: fs.patch.apply
version: 1.0.0
title: Apply patch
risk: write
category: test
mcp:
  exposed: true
input_schema:
  type: object
  additionalProperties: false
  properties:
    proposal_id:
      type: string
    approval_id:
      type: string
  oneOf:
    - required: ["proposal_id"]
    - required: ["approval_id"]
""",
        encoding="utf-8",
    )


def write_http_fetch_manifest(manifest_dir: Path) -> None:
    manifest_dir.mkdir(exist_ok=True)
    manifest_dir.joinpath("http-fetch.yaml").write_text(
        """
name: http.fetch
version: 1.0.0
title: Fetch URL
risk: network
category: network
mcp:
  exposed: true
input_schema:
  type: object
  additionalProperties: false
  required: ["url"]
  properties:
    url:
      type: string
""",
        encoding="utf-8",
    )


def write_git_commit_metadata_manifest(manifest_dir: Path) -> None:
    manifest_dir.mkdir(exist_ok=True)
    manifest_dir.joinpath("git-show-commit-metadata.yaml").write_text(
        """
name: git.show.commit_metadata
version: 1.0.0
title: Show commit metadata
risk: read
category: git
mcp:
  exposed: true
input_schema:
  type: object
  additionalProperties: false
  required: ["ref"]
  properties:
    ref:
      type: object
      additionalProperties: false
      required: ["kind", "value"]
      properties:
        kind:
          type: string
          enum: [object_id, branch, tag]
        value:
          type: string
    include_body:
      type: boolean
    include_emails:
      type: boolean
    include_diffstat:
      type: boolean
""",
        encoding="utf-8",
    )


def write_git_ref_summary_manifest(manifest_dir: Path) -> None:
    manifest_dir.mkdir(exist_ok=True)
    manifest_dir.joinpath("git-show-ref-summary.yaml").write_text(
        """
name: git.show.ref_summary
version: 1.0.0
title: Show ref summary
risk: read
category: git
mcp:
  exposed: true
input_schema:
  type: object
  additionalProperties: false
  required: ["selector"]
  properties:
    selector:
      type: object
      additionalProperties: false
      required: ["kind"]
      properties:
        kind:
          type: string
          enum: [all_local, branch, tag]
    limit:
      type: integer
      minimum: 1
      maximum: 200
""",
        encoding="utf-8",
    )


def write_git_tag_metadata_manifest(manifest_dir: Path) -> None:
    manifest_dir.mkdir(exist_ok=True)
    manifest_dir.joinpath("git-show-tag-metadata.yaml").write_text(
        """
name: git.show.tag_metadata
version: 1.0.0
title: Show tag metadata
risk: read
category: git
mcp:
  exposed: true
input_schema:
  type: object
  additionalProperties: false
  required: ["selector"]
  properties:
    selector:
      type: object
      additionalProperties: false
      required: ["kind"]
      properties:
        kind:
          type: string
          enum: [all_local_tags]
    limit:
      type: integer
      minimum: 1
      maximum: 200
""",
        encoding="utf-8",
    )


def write_project_manifest_summary_manifest(manifest_dir: Path) -> None:
    manifest_dir.mkdir(exist_ok=True)
    manifest_dir.joinpath("project-manifest-summary.yaml").write_text(
        """
name: project.manifest.summary
version: 1.0.0
title: Summarize project manifests
risk: read
category: project
mcp:
  exposed: true
input_schema:
  type: object
  additionalProperties: false
  properties:
    root:
      type: string
    manifest_kinds:
      type: array
      items:
        type: string
    limit:
      type: integer
    workspace_id:
      type: string
""",
        encoding="utf-8",
    )


def write_project_dependency_summary_manifest(manifest_dir: Path) -> None:
    manifest_dir.mkdir(exist_ok=True)
    manifest_dir.joinpath("project-dependency-summary.yaml").write_text(
        """
name: project.dependency.summary
version: 1.0.0
title: Summarize project dependencies
risk: read
category: project
mcp:
  exposed: true
input_schema:
  type: object
  additionalProperties: false
  properties:
    root:
      type: string
    manifest_kinds:
      type: array
      items:
        type: string
    limit:
      type: integer
    workspace_id:
      type: string
""",
        encoding="utf-8",
    )


def write_project_structure_summary_manifest(manifest_dir: Path) -> None:
    manifest_dir.mkdir(exist_ok=True)
    manifest_dir.joinpath("project-structure-summary.yaml").write_text(
        """
name: project.structure.summary
version: 1.0.0
title: Summarize project structure
risk: read
category: project
mcp:
  exposed: true
input_schema:
  type: object
  additionalProperties: false
  properties:
    root:
      type: string
    max_depth:
      type: integer
      minimum: 0
      maximum: 4
    limit:
      type: integer
      minimum: 1
      maximum: 250
    include_categories:
      type: array
      items:
        type: string
        enum: [directory_categories, file_kinds, skipped_counts]
    workspace_id:
      type: string
""",
        encoding="utf-8",
    )


def write_project_test_summary_manifest(manifest_dir: Path) -> None:
    manifest_dir.mkdir(exist_ok=True)
    manifest_dir.joinpath("project-test-summary.yaml").write_text(
        """
name: project.test.summary
version: 1.0.0
title: Summarize project tests
risk: read
category: project
mcp:
  exposed: true
input_schema:
  type: object
  additionalProperties: false
  properties:
    root:
      type: string
    max_depth:
      type: integer
      minimum: 0
      maximum: 5
    limit:
      type: integer
      minimum: 1
      maximum: 300
    include_categories:
      type: array
      items:
        type: string
        enum: [framework_hints, test_location_counts, language_family_counts, skipped_counts]
    workspace_id:
      type: string
""",
        encoding="utf-8",
    )


def write_project_docs_summary_manifest(manifest_dir: Path) -> None:
    manifest_dir.mkdir(exist_ok=True)
    manifest_dir.joinpath("project-docs-summary.yaml").write_text(
        """
name: project.docs.summary
version: 1.0.0
title: Summarize project documentation
risk: read
category: project
mcp:
  exposed: true
input_schema:
  type: object
  additionalProperties: false
  properties:
    root:
      type: string
    max_depth:
      type: integer
      minimum: 0
      maximum: 5
    limit:
      type: integer
      minimum: 1
      maximum: 300
    include_categories:
      type: array
      items:
        type: string
        enum:
          - documentation_type_counts
          - documentation_location_counts
          - language_family_counts
          - skipped_counts
    workspace_id:
      type: string
""",
        encoding="utf-8",
    )


def write_project_language_summary_manifest(manifest_dir: Path) -> None:
    manifest_dir.mkdir(exist_ok=True)
    manifest_dir.joinpath("project-language-summary.yaml").write_text(
        """
name: project.language.summary
version: 1.0.0
title: Summarize project languages
risk: read
category: project
mcp:
  exposed: true
input_schema:
  type: object
  additionalProperties: false
  properties:
    root:
      type: string
    max_depth:
      type: integer
      minimum: 0
      maximum: 5
    limit:
      type: integer
      minimum: 1
      maximum: 300
    include_categories:
      type: array
      items:
        type: string
        enum:
          - language_family_counts
          - extension_family_counts
          - source_location_counts
          - skipped_counts
    workspace_id:
      type: string
""",
        encoding="utf-8",
    )


def write_project_config_summary_manifest(manifest_dir: Path) -> None:
    manifest_dir.mkdir(exist_ok=True)
    manifest_dir.joinpath("project-config-summary.yaml").write_text(
        """
name: project.config.summary
version: 1.0.0
title: Summarize project configuration posture
risk: read
category: project
mcp:
  exposed: true
input_schema:
  type: object
  additionalProperties: false
  properties:
    root:
      type: string
    max_depth:
      type: integer
      minimum: 0
      maximum: 5
    limit:
      type: integer
      minimum: 1
      maximum: 300
    include_categories:
      type: array
      items:
        type: string
        enum:
          - config_category_counts
          - config_location_counts
          - skipped_counts
    workspace_id:
      type: string
""",
        encoding="utf-8",
    )


def write_project_ci_summary_manifest(manifest_dir: Path) -> None:
    manifest_dir.mkdir(exist_ok=True)
    manifest_dir.joinpath("project-ci-summary.yaml").write_text(
        """
name: project.ci.summary
version: 1.0.0
title: Summarize project CI posture
risk: read
category: project
mcp:
  exposed: true
input_schema:
  type: object
  additionalProperties: false
  properties:
    root:
      type: string
    max_depth:
      type: integer
      minimum: 0
      maximum: 5
    limit:
      type: integer
      minimum: 1
      maximum: 300
    include_categories:
      type: array
      items:
        type: string
        enum:
          - provider_counts
          - trigger_category_counts
          - job_category_counts
          - location_bucket_counts
          - skipped_counts
    workspace_id:
      type: string
""",
        encoding="utf-8",
    )


def make_service(tmp_path: Path) -> GovernedToolCallService:
    manifest_dir = tmp_path / "manifests"
    write_manifest(manifest_dir, "fs.read", "read")
    write_manifest(manifest_dir, "fs.apply_patch", "write")
    write_manifest(manifest_dir, "shell.run", "write", required="command")
    policy_path = tmp_path / "policy.yaml"
    write_policy(policy_path)
    db_path = tmp_path / "ithildin.sqlite3"
    audit_writer = AuditWriter(db_path, tmp_path / "audit.jsonl")
    audit_writer.initialize()
    approval_store = ApprovalStore(db_path)
    approval_store.initialize()
    approval_service = ApprovalService(approval_store, audit_writer, timedelta(minutes=15))
    return GovernedToolCallService(
        ToolRegistry.load(manifest_dir),
        PolicyEvaluator.load(policy_path),
        approval_service,
        audit_writer,
    )


def make_identity_service(tmp_path: Path) -> GovernedToolCallService:
    manifest_dir = tmp_path / "manifests"
    write_manifest(manifest_dir, "fs.read", "read")
    write_manifest(manifest_dir, "http.fetch", "network", required="url")
    policy_path = tmp_path / "policy.yaml"
    write_policy(policy_path)
    db_path = tmp_path / "ithildin.sqlite3"
    audit_writer = AuditWriter(db_path, tmp_path / "audit.jsonl")
    audit_writer.initialize()
    approval_store = ApprovalStore(db_path)
    approval_store.initialize()
    approval_service = ApprovalService(approval_store, audit_writer, timedelta(minutes=15))
    return GovernedToolCallService(
        ToolRegistry.load(manifest_dir),
        PolicyEvaluator.load(policy_path),
        approval_service,
        audit_writer,
        principal_registry=PrincipalRegistry.load(Path("principals/local.yaml")),
    )


def make_read_service(
    tmp_path: Path,
    *,
    content: str = "hello governed reads\n",
    policy_yaml: str | None = None,
    track_runs: bool = False,
) -> GovernedToolCallService:
    manifest_dir = tmp_path / "manifests"
    write_manifest(manifest_dir, "fs.read", "read")
    write_manifest(manifest_dir, "git.status", "read", required="path")
    policy_path = tmp_path / "policy.yaml"
    if policy_yaml is None:
        write_policy(policy_path)
    else:
        policy_path.write_text(policy_yaml, encoding="utf-8")
    db_path = tmp_path / "ithildin.sqlite3"
    audit_writer = AuditWriter(db_path, tmp_path / "audit.jsonl")
    audit_writer.initialize()
    approval_store = ApprovalStore(db_path)
    approval_store.initialize()
    approval_service = ApprovalService(approval_store, audit_writer, timedelta(minutes=15))
    agent_run_store = AgentRunStore(db_path) if track_runs else None
    if agent_run_store is not None:
        agent_run_store.initialize()
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    workspace_root.joinpath("README.md").write_text(content, encoding="utf-8")
    return GovernedToolCallService(
        ToolRegistry.load(manifest_dir),
        PolicyEvaluator.load(policy_path),
        approval_service,
        audit_writer,
        ReadToolExecutor.from_settings(
            workspace_root=workspace_root,
            max_read_bytes=1024,
            search_result_limit=10,
            git_log_limit=10,
        ),
        agent_run_store=agent_run_store,
    )


def make_git_commit_metadata_service(tmp_path: Path) -> tuple[GovernedToolCallService, str]:
    manifest_dir = tmp_path / "manifests"
    write_git_commit_metadata_manifest(manifest_dir)
    policy_path = tmp_path / "policy.yaml"
    write_policy(policy_path)
    db_path = tmp_path / "ithildin.sqlite3"
    audit_writer = AuditWriter(db_path, tmp_path / "audit.jsonl")
    audit_writer.initialize()
    approval_store = ApprovalStore(db_path)
    approval_store.initialize()
    approval_service = ApprovalService(approval_store, audit_writer, timedelta(minutes=15))
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    run_git(workspace_root, ["init"])
    run_git(workspace_root, ["config", "user.email", "test@example.com"])
    run_git(workspace_root, ["config", "user.name", "Test User"])
    workspace_root.joinpath("README.md").write_text("hello\n", encoding="utf-8")
    run_git(workspace_root, ["add", "README.md"])
    run_git(workspace_root, ["commit", "-m", "initial"])
    commit_hash = git_output(workspace_root, ["rev-parse", "HEAD"])
    return (
        GovernedToolCallService(
            ToolRegistry.load(manifest_dir),
            PolicyEvaluator.load(policy_path),
            approval_service,
            audit_writer,
            ReadToolExecutor.from_settings(
                workspace_root=workspace_root,
                max_read_bytes=4096,
                search_result_limit=10,
                git_log_limit=10,
            ),
        ),
        commit_hash,
    )


def make_git_ref_summary_service(tmp_path: Path) -> tuple[GovernedToolCallService, str]:
    manifest_dir = tmp_path / "manifests"
    write_git_ref_summary_manifest(manifest_dir)
    policy_path = tmp_path / "policy.yaml"
    write_policy(policy_path)
    db_path = tmp_path / "ithildin.sqlite3"
    audit_writer = AuditWriter(db_path, tmp_path / "audit.jsonl")
    audit_writer.initialize()
    approval_store = ApprovalStore(db_path)
    approval_store.initialize()
    approval_service = ApprovalService(approval_store, audit_writer, timedelta(minutes=15))
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    run_git(workspace_root, ["init"])
    run_git(workspace_root, ["config", "user.email", "test@example.com"])
    run_git(workspace_root, ["config", "user.name", "Test User"])
    workspace_root.joinpath("README.md").write_text("hello\n", encoding="utf-8")
    run_git(workspace_root, ["add", "README.md"])
    run_git(workspace_root, ["commit", "-m", "initial"])
    run_git(workspace_root, ["branch", "safe/topic"])
    commit_hash = git_output(workspace_root, ["rev-parse", "HEAD"])
    return (
        GovernedToolCallService(
            ToolRegistry.load(manifest_dir),
            PolicyEvaluator.load(policy_path),
            approval_service,
            audit_writer,
            ReadToolExecutor.from_settings(
                workspace_root=workspace_root,
                max_read_bytes=4096,
                search_result_limit=10,
                git_log_limit=10,
            ),
        ),
        commit_hash,
    )


def make_git_tag_metadata_service(tmp_path: Path) -> tuple[GovernedToolCallService, str]:
    manifest_dir = tmp_path / "manifests"
    write_git_tag_metadata_manifest(manifest_dir)
    policy_path = tmp_path / "policy.yaml"
    write_policy(policy_path)
    db_path = tmp_path / "ithildin.sqlite3"
    audit_writer = AuditWriter(db_path, tmp_path / "audit.jsonl")
    audit_writer.initialize()
    approval_store = ApprovalStore(db_path)
    approval_store.initialize()
    approval_service = ApprovalService(approval_store, audit_writer, timedelta(minutes=15))
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    run_git(workspace_root, ["init"])
    run_git(workspace_root, ["config", "user.email", "test@example.com"])
    run_git(workspace_root, ["config", "user.name", "Test User"])
    workspace_root.joinpath("README.md").write_text("hello\n", encoding="utf-8")
    run_git(workspace_root, ["add", "README.md"])
    run_git(workspace_root, ["commit", "-m", "initial"])
    commit_hash = git_output(workspace_root, ["rev-parse", "HEAD"])
    run_git(workspace_root, ["tag", "v-secret-customer-release", commit_hash])
    return (
        GovernedToolCallService(
            ToolRegistry.load(manifest_dir),
            PolicyEvaluator.load(policy_path),
            approval_service,
            audit_writer,
            ReadToolExecutor.from_settings(
                workspace_root=workspace_root,
                max_read_bytes=4096,
                search_result_limit=10,
                git_log_limit=10,
            ),
        ),
        commit_hash,
    )


def make_project_manifest_summary_service(tmp_path: Path) -> GovernedToolCallService:
    manifest_dir = tmp_path / "manifests"
    write_project_manifest_summary_manifest(manifest_dir)
    policy_path = tmp_path / "policy.yaml"
    write_policy(policy_path)
    db_path = tmp_path / "ithildin.sqlite3"
    audit_writer = AuditWriter(db_path, tmp_path / "audit.jsonl")
    audit_writer.initialize()
    approval_store = ApprovalStore(db_path)
    approval_store.initialize()
    approval_service = ApprovalService(approval_store, audit_writer, timedelta(minutes=15))
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    workspace_root.joinpath("package.json").write_text(
        json.dumps(
            {
                "scripts": {"deploy": "TOKEN=secret npm publish"},
                "dependencies": {"internal-package": "1.0.0"},
            }
        ),
        encoding="utf-8",
    )
    return GovernedToolCallService(
        ToolRegistry.load(manifest_dir),
        PolicyEvaluator.load(policy_path),
        approval_service,
        audit_writer,
        ReadToolExecutor.from_settings(
            workspace_root=workspace_root,
            max_read_bytes=4096,
            search_result_limit=10,
            git_log_limit=10,
        ),
    )


def make_project_dependency_summary_service(tmp_path: Path) -> GovernedToolCallService:
    manifest_dir = tmp_path / "manifests"
    write_project_dependency_summary_manifest(manifest_dir)
    policy_path = tmp_path / "policy.yaml"
    write_policy(policy_path)
    db_path = tmp_path / "ithildin.sqlite3"
    audit_writer = AuditWriter(db_path, tmp_path / "audit.jsonl")
    audit_writer.initialize()
    approval_store = ApprovalStore(db_path)
    approval_store.initialize()
    approval_service = ApprovalService(approval_store, audit_writer, timedelta(minutes=15))
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    workspace_root.joinpath("package.json").write_text(
        json.dumps(
            {
                "name": "private-service",
                "scripts": {"deploy": "TOKEN=secret npm publish"},
                "dependencies": {"internal-package": "1.0.0"},
                "devDependencies": {"test-helper": "2.0.0"},
            }
        ),
        encoding="utf-8",
    )
    return GovernedToolCallService(
        ToolRegistry.load(manifest_dir),
        PolicyEvaluator.load(policy_path),
        approval_service,
        audit_writer,
        ReadToolExecutor.from_settings(
            workspace_root=workspace_root,
            max_read_bytes=4096,
            search_result_limit=10,
            git_log_limit=10,
        ),
    )


def make_project_structure_summary_service(tmp_path: Path) -> GovernedToolCallService:
    manifest_dir = tmp_path / "manifests"
    write_project_structure_summary_manifest(manifest_dir)
    policy_path = tmp_path / "policy.yaml"
    write_policy(policy_path)
    db_path = tmp_path / "ithildin.sqlite3"
    audit_writer = AuditWriter(db_path, tmp_path / "audit.jsonl")
    audit_writer.initialize()
    approval_store = ApprovalStore(db_path)
    approval_store.initialize()
    approval_service = ApprovalService(approval_store, audit_writer, timedelta(minutes=15))
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    workspace_root.joinpath("src").mkdir()
    workspace_root.joinpath("src", "private_feature.py").write_text(
        "TOKEN = 'secret'\n", encoding="utf-8"
    )
    workspace_root.joinpath("docs").mkdir()
    workspace_root.joinpath("docs", "Private Roadmap.md").write_text(
        "private\n", encoding="utf-8"
    )
    workspace_root.joinpath(".env").write_text("TOKEN=secret", encoding="utf-8")
    return GovernedToolCallService(
        ToolRegistry.load(manifest_dir),
        PolicyEvaluator.load(policy_path),
        approval_service,
        audit_writer,
        ReadToolExecutor.from_settings(
            workspace_root=workspace_root,
            max_read_bytes=4096,
            search_result_limit=10,
            git_log_limit=10,
        ),
    )


def make_project_test_summary_service(tmp_path: Path) -> GovernedToolCallService:
    manifest_dir = tmp_path / "manifests"
    write_project_test_summary_manifest(manifest_dir)
    policy_path = tmp_path / "policy.yaml"
    write_policy(policy_path)
    db_path = tmp_path / "ithildin.sqlite3"
    audit_writer = AuditWriter(db_path, tmp_path / "audit.jsonl")
    audit_writer.initialize()
    approval_store = ApprovalStore(db_path)
    approval_store.initialize()
    approval_service = ApprovalService(approval_store, audit_writer, timedelta(minutes=15))
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    workspace_root.joinpath("tests").mkdir()
    workspace_root.joinpath("tests", "test_private_feature.py").write_text(
        "TOKEN = 'secret'\n", encoding="utf-8"
    )
    workspace_root.joinpath("src").mkdir()
    workspace_root.joinpath("src", "feature.test.ts").write_text(
        "TOKEN=secret\n", encoding="utf-8"
    )
    return GovernedToolCallService(
        ToolRegistry.load(manifest_dir),
        PolicyEvaluator.load(policy_path),
        approval_service,
        audit_writer,
        ReadToolExecutor.from_settings(
            workspace_root=workspace_root,
            max_read_bytes=4096,
            search_result_limit=10,
            git_log_limit=10,
        ),
    )


def make_project_docs_summary_service(tmp_path: Path) -> GovernedToolCallService:
    manifest_dir = tmp_path / "manifests"
    write_project_docs_summary_manifest(manifest_dir)
    policy_path = tmp_path / "policy.yaml"
    write_policy(policy_path)
    db_path = tmp_path / "ithildin.sqlite3"
    audit_writer = AuditWriter(db_path, tmp_path / "audit.jsonl")
    audit_writer.initialize()
    approval_store = ApprovalStore(db_path)
    approval_store.initialize()
    approval_service = ApprovalService(approval_store, audit_writer, timedelta(minutes=15))
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    workspace_root.joinpath("README.md").write_text("# Secret Project\n", encoding="utf-8")
    workspace_root.joinpath("docs").mkdir()
    workspace_root.joinpath("docs", "api.md").write_text("TOKEN=secret\n", encoding="utf-8")
    workspace_root.joinpath("src").mkdir()
    workspace_root.joinpath("src", "usage.md").write_text("TOKEN=secret\n", encoding="utf-8")
    return GovernedToolCallService(
        ToolRegistry.load(manifest_dir),
        PolicyEvaluator.load(policy_path),
        approval_service,
        audit_writer,
        ReadToolExecutor.from_settings(
            workspace_root=workspace_root,
            max_read_bytes=4096,
            search_result_limit=10,
            git_log_limit=10,
        ),
    )


def make_project_language_summary_service(tmp_path: Path) -> GovernedToolCallService:
    manifest_dir = tmp_path / "manifests"
    write_project_language_summary_manifest(manifest_dir)
    policy_path = tmp_path / "policy.yaml"
    write_policy(policy_path)
    db_path = tmp_path / "ithildin.sqlite3"
    audit_writer = AuditWriter(db_path, tmp_path / "audit.jsonl")
    audit_writer.initialize()
    approval_store = ApprovalStore(db_path)
    approval_store.initialize()
    approval_service = ApprovalService(approval_store, audit_writer, timedelta(minutes=15))
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    workspace_root.joinpath("main.py").write_text("TOKEN='secret'\n", encoding="utf-8")
    workspace_root.joinpath("src").mkdir()
    workspace_root.joinpath("src", "app.ts").write_text("TOKEN=secret\n", encoding="utf-8")
    workspace_root.joinpath("docs").mkdir()
    workspace_root.joinpath("docs", "guide.md").write_text("TOKEN=secret\n", encoding="utf-8")
    return GovernedToolCallService(
        ToolRegistry.load(manifest_dir),
        PolicyEvaluator.load(policy_path),
        approval_service,
        audit_writer,
        ReadToolExecutor.from_settings(
            workspace_root=workspace_root,
            max_read_bytes=4096,
            search_result_limit=10,
            git_log_limit=10,
        ),
    )


def make_project_config_summary_service(tmp_path: Path) -> GovernedToolCallService:
    manifest_dir = tmp_path / "manifests"
    write_project_config_summary_manifest(manifest_dir)
    policy_path = tmp_path / "policy.yaml"
    write_policy(policy_path)
    db_path = tmp_path / "ithildin.sqlite3"
    audit_writer = AuditWriter(db_path, tmp_path / "audit.jsonl")
    audit_writer.initialize()
    approval_store = ApprovalStore(db_path)
    approval_store.initialize()
    approval_service = ApprovalService(approval_store, audit_writer, timedelta(minutes=15))
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    workspace_root.joinpath("pyproject.toml").write_text(
        "[project]\nname='secret-package'\n",
        encoding="utf-8",
    )
    workspace_root.joinpath("config").mkdir()
    workspace_root.joinpath("config", "app.yaml").write_text(
        "token: secret\n",
        encoding="utf-8",
    )
    workspace_root.joinpath("src").mkdir()
    workspace_root.joinpath("src", "settings.ini").write_text(
        "password=secret\n",
        encoding="utf-8",
    )
    return GovernedToolCallService(
        ToolRegistry.load(manifest_dir),
        PolicyEvaluator.load(policy_path),
        approval_service,
        audit_writer,
        ReadToolExecutor.from_settings(
            workspace_root=workspace_root,
            max_read_bytes=4096,
            search_result_limit=10,
            git_log_limit=10,
        ),
    )


def make_project_ci_summary_service(tmp_path: Path) -> GovernedToolCallService:
    manifest_dir = tmp_path / "manifests"
    write_project_ci_summary_manifest(manifest_dir)
    policy_path = tmp_path / "policy.yaml"
    write_policy(policy_path)
    db_path = tmp_path / "ithildin.sqlite3"
    audit_writer = AuditWriter(db_path, tmp_path / "audit.jsonl")
    audit_writer.initialize()
    approval_store = ApprovalStore(db_path)
    approval_store.initialize()
    approval_service = ApprovalService(approval_store, audit_writer, timedelta(minutes=15))
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    workspace_root.joinpath(".github", "workflows").mkdir(parents=True)
    workspace_root.joinpath(".github", "workflows", "private-ci.yml").write_text(
        """
name: Secret Release
on:
  push:
  pull_request:
jobs:
  private-test:
    runs-on: ubuntu-latest
    steps:
      - run: pytest --token secret
      - run: ruff check .
""",
        encoding="utf-8",
    )
    return GovernedToolCallService(
        ToolRegistry.load(manifest_dir),
        PolicyEvaluator.load(policy_path),
        approval_service,
        audit_writer,
        ReadToolExecutor.from_settings(
            workspace_root=workspace_root,
            max_read_bytes=4096,
            search_result_limit=10,
            git_log_limit=10,
        ),
    )


def make_http_service(
    tmp_path: Path,
    *,
    allowlist: str = "https://example.com",
    opener: FakeHttpOpener | None = None,
) -> GovernedToolCallService:
    manifest_dir = tmp_path / "manifests"
    write_http_fetch_manifest(manifest_dir)
    policy_path = tmp_path / "policy.yaml"
    write_policy(policy_path)
    db_path = tmp_path / "ithildin.sqlite3"
    audit_writer = AuditWriter(db_path, tmp_path / "audit.jsonl")
    audit_writer.initialize()
    approval_store = ApprovalStore(db_path)
    approval_store.initialize()
    approval_service = ApprovalService(approval_store, audit_writer, timedelta(minutes=15))
    http_opener = opener or FakeHttpOpener()
    http_executor = HttpFetchExecutor(
        allowlist=HttpAllowlist.from_csv(allowlist),
        timeout_seconds=1,
        max_response_bytes=1024,
        max_redirects=3,
        resolver=lambda host, port: ["93.184.216.34"],
        opener=http_opener,
    )
    return GovernedToolCallService(
        ToolRegistry.load(manifest_dir),
        PolicyEvaluator.load(policy_path),
        approval_service,
        audit_writer,
        http_fetch_executor=http_executor,
    )


@dataclass(frozen=True)
class PatchHarness:
    service: GovernedToolCallService
    approval_service: ApprovalService
    patch_service: PatchProposalService
    db_path: Path
    workspace_root: Path


def make_patch_harness(
    tmp_path: Path,
    *,
    apply_fault_hook: PatchApplyFaultHook | None = None,
) -> PatchHarness:
    manifest_dir = tmp_path / "manifests"
    write_patch_propose_manifest(manifest_dir)
    write_patch_apply_manifest(manifest_dir)
    policy_path = tmp_path / "policy.yaml"
    write_policy(policy_path)
    db_path = tmp_path / "ithildin.sqlite3"
    audit_writer = AuditWriter(db_path, tmp_path / "audit.jsonl")
    audit_writer.initialize()
    approval_store = ApprovalStore(db_path)
    approval_store.initialize()
    approval_service = ApprovalService(approval_store, audit_writer, timedelta(minutes=15))
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    workspace_root.joinpath("README.md").write_text("old\n", encoding="utf-8")
    read_executor = ReadToolExecutor.from_settings(
        workspace_root=workspace_root,
        max_read_bytes=1024,
        search_result_limit=10,
        git_log_limit=10,
    )
    patch_store = PatchProposalStore(db_path)
    patch_store.initialize()
    patch_service = PatchProposalService(
        patch_store,
        read_executor.filesystem,
        max_patch_bytes=1024,
        apply_fault_hook=apply_fault_hook,
    )
    service = GovernedToolCallService(
        ToolRegistry.load(manifest_dir),
        PolicyEvaluator.load(policy_path),
        approval_service,
        audit_writer,
        read_executor,
        patch_service,
    )
    return PatchHarness(service, approval_service, patch_service, db_path, workspace_root)


def make_patch_service(tmp_path: Path) -> GovernedToolCallService:
    return make_patch_harness(tmp_path).service


def principal() -> JsonObject:
    return {"id": "agent:local-dev", "roles": ["AgentDeveloper"]}


def audit_payloads(tmp_path: Path) -> list[JsonObject]:
    return [
        json.loads(line)
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]


def run_git(repo: Path, args: list[str]) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


def git_output(repo: Path, args: list[str]) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_unknown_tool_is_denied_and_audited(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    result = service.call_tool(
        tool_name="fs.missing",
        arguments={"path": "README.md"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert result.is_error is True
    assert audit_payloads(tmp_path)[0]["decision"] == "deny"


def test_invalid_arguments_are_denied_before_policy(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    result = service.call_tool(
        tool_name="fs.read",
        arguments={"not_path": "README.md"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert result.content == {"reason": "invalid tool arguments"}
    metadata = cast(JsonObject, audit_payloads(tmp_path)[0]["metadata"])
    assert metadata["reason"] == "invalid tool arguments"


def test_invalid_argument_audit_metadata_does_not_echo_secret_values(
    tmp_path: Path,
) -> None:
    service = make_service(tmp_path)

    result = service.call_tool(
        tool_name="fs.read",
        arguments={"path": {"token": "secret-value"}},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    payload_text = json.dumps(audit_payloads(tmp_path))
    assert "secret-value" not in payload_text
    assert "JSON Schema validation failed" in payload_text


def test_unknown_principal_is_denied_and_audited_before_policy(tmp_path: Path) -> None:
    service = make_identity_service(tmp_path)

    result = service.call_tool(
        tool_name="fs.read",
        arguments={"path": "README.md"},
        principal={"id": "agent:missing", "roles": ["Admin"]},
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert result.is_error is True
    assert "unknown principal" in str(result.content["reason"])
    payload = audit_payloads(tmp_path)[0]
    metadata = cast(JsonObject, payload["metadata"])
    assert payload["principal"] == {"id": "agent:missing", "roles": ["Admin"]}
    assert payload["decision"] == "deny"
    assert metadata["identity_source"] == "principal_registry"


def test_role_unauthorized_principal_is_denied_before_execution(tmp_path: Path) -> None:
    service = make_identity_service(tmp_path)

    result = service.call_tool(
        tool_name="http.fetch",
        arguments={"url": "https://example.com/data"},
        principal={"id": "agent:readonly", "roles": ["Admin"]},
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert result.is_error is True
    assert "not authorized" in str(result.content["reason"])
    payload = audit_payloads(tmp_path)[0]
    metadata = cast(JsonObject, payload["metadata"])
    assert payload["principal"] == {
        "id": "agent:readonly",
        "type": "agent",
        "roles": ["AgentReadOnly"],
    }
    assert payload["decision"] == "deny"
    assert metadata["tool_risk"] == "network"


def test_read_allow_returns_governance_only_success(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    result = service.call_tool(
        tool_name="fs.read",
        arguments={"path": "README.md"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "allowed"
    message = result.content["message"]
    assert isinstance(message, str)
    assert "execution is not implemented" in message
    assert audit_payloads(tmp_path)[0]["decision"] == "allow"


def test_read_tool_executes_after_policy_allow_and_is_audited(tmp_path: Path) -> None:
    service = make_read_service(tmp_path)

    result = service.call_tool(
        tool_name="fs.read",
        arguments={"path": "README.md"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "completed"
    assert result.content["content"] == "hello governed reads\n"
    payloads = audit_payloads(tmp_path)
    assert [payload["event_type"] for payload in payloads] == [
        "policy.evaluated",
        "tool.execution.started",
        "tool.execution.completed",
    ]
    policy_metadata = cast(JsonObject, payloads[0]["metadata"])
    assert policy_metadata["policy_engine"] == "yaml"
    assert policy_metadata["policy_document_version"] == "test"
    assert policy_metadata["policy_hash"] == payloads[0]["policy_version"]
    assert policy_metadata["policy_version"] == payloads[0]["policy_version"]
    assert policy_metadata["decision"] == "allow"
    assert policy_metadata["reason"] == "reads allowed"
    manifest_hash = policy_metadata["manifest_hash"]
    assert isinstance(manifest_hash, str)
    assert manifest_hash.startswith("sha256:")
    assert policy_metadata["tool_name"] == "fs.read"
    assert policy_metadata["tool_version"] == "1.0.0"
    assert policy_metadata["tool_risk"] == "read"
    assert policy_metadata["resource_type"] == "file"
    assert policy_metadata["resource_in_scope"] is True
    assert policy_metadata["principal_id"] == "agent:local-dev"
    assert policy_metadata["principal_roles"] == ["AgentDeveloper"]
    assert policy_metadata["session_id"] == "sess_1"
    assert policy_metadata["obligation_keys"] == ["audit_level"]
    metadata = cast(JsonObject, payloads[-1]["metadata"])
    assert metadata["redaction_applied"] is True
    assert metadata["redaction_count"] == 0


def test_agent_run_store_correlates_governed_tool_call_audit_events(tmp_path: Path) -> None:
    service = make_read_service(tmp_path, track_runs=True)

    result = service.call_tool(
        tool_name="fs.read",
        arguments={"path": "README.md"},
        principal=principal(),
        session_id="sess_runs",
    )

    assert result.status == "completed"
    run_store = AgentRunStore(tmp_path / "ithildin.sqlite3")
    runs = run_store.list_runs()
    assert len(runs) == 1
    run = runs[0]
    assert run["principal_id"] == "agent:local-dev"
    assert run["workspace_id"] == "default"
    assert run["session_id"] == "sess_runs"
    assert run["tool_call_count"] == 1
    assert run["last_tool_name"] == "fs.read"
    run_id = cast(str, run["run_id"])

    detail = run_store.detail(run_id)
    timeline = cast(list[JsonObject], detail["timeline"])
    assert [event["event_type"] for event in timeline] == [
        "agent.session.started",
        "policy.evaluated",
        "tool.execution.started",
        "tool.execution.completed",
    ]
    for event in timeline:
        metadata = cast(JsonObject, event["metadata"])
        assert metadata["run_id"] == run_id
        assert metadata["session_id"] == "sess_runs"
    timeline_text = json.dumps(timeline)
    assert "hello governed reads" not in timeline_text


def test_git_commit_metadata_tool_executes_after_policy_allow_and_is_audited(
    tmp_path: Path,
) -> None:
    service, commit_hash = make_git_commit_metadata_service(tmp_path)

    result = service.call_tool(
        tool_name="git.show.commit_metadata",
        arguments={"ref": {"kind": "object_id", "value": commit_hash}},
        principal=principal(),
        session_id="sess_git_commit",
    )

    assert result.status == "completed"
    assert result.content["resolved_commit_hash"] == commit_hash
    assert result.content["subject"] == "initial"
    output_policy = cast(JsonObject, result.content["output_policy"])
    assert output_policy["raw_diff_included"] is False
    payloads = audit_payloads(tmp_path)
    assert [payload["event_type"] for payload in payloads] == [
        "policy.evaluated",
        "tool.execution.started",
        "tool.execution.completed",
    ]
    policy_metadata = cast(JsonObject, payloads[0]["metadata"])
    assert policy_metadata["resource_type"] == "git_commit"
    assert policy_metadata["resource_in_scope"] is True
    execution_resource = cast(JsonObject, payloads[1]["resource"])
    assert execution_resource["type"] == "git_commit"
    assert execution_resource["ref_kind"] == "object_id"
    assert "value" not in execution_resource


def test_git_commit_metadata_unresolved_commit_fails_without_content_leak(
    tmp_path: Path,
) -> None:
    service, _commit_hash = make_git_commit_metadata_service(tmp_path)

    result = service.call_tool(
        tool_name="git.show.commit_metadata",
        arguments={"ref": {"kind": "object_id", "value": "0" * 40}},
        principal=principal(),
        session_id="sess_git_commit_missing",
    )

    assert result.status == "denied"
    assert result.is_error is True
    assert result.content == {"reason": "path is not a readable git repository"}
    payloads = audit_payloads(tmp_path)
    assert payloads[2]["event_type"] == AuditEventType.TOOL_EXECUTION_FAILED.value
    resources = [payload["resource"] for payload in payloads]
    assert "0000000000000000000000000000000000000000" not in json.dumps(resources)


def test_git_ref_summary_tool_executes_after_policy_allow_and_is_audited(
    tmp_path: Path,
) -> None:
    service, commit_hash = make_git_ref_summary_service(tmp_path)

    result = service.call_tool(
        tool_name="git.show.ref_summary",
        arguments={"selector": {"kind": "branch"}, "limit": 10},
        principal=principal(),
        session_id="sess_git_refs",
    )

    assert result.status == "completed"
    refs = cast(list[JsonObject], result.content["refs"])
    assert refs
    assert all(ref["kind"] == "branch" for ref in refs)
    assert all(ref["resolved_commit_hash"] == commit_hash for ref in refs)
    assert "safe/topic" not in json.dumps(result.content)
    assert "refs/heads" not in json.dumps(result.content)
    payloads = audit_payloads(tmp_path)
    assert [payload["event_type"] for payload in payloads] == [
        "policy.evaluated",
        "tool.execution.started",
        "tool.execution.completed",
    ]
    policy_metadata = cast(JsonObject, payloads[0]["metadata"])
    assert policy_metadata["resource_type"] == "git_refs"
    assert policy_metadata["resource_in_scope"] is True
    execution_resource = cast(JsonObject, payloads[1]["resource"])
    assert execution_resource["type"] == "git_refs"
    assert execution_resource["selector_kind"] == "branch"
    completed_metadata = cast(JsonObject, payloads[2]["metadata"])
    assert completed_metadata["selector_kind"] == "branch"
    assert completed_metadata["ref_names_included"] is False
    assert completed_metadata["stable_ref_hashes_included"] is False
    assert completed_metadata["ref_ids_are_response_local"] is True
    completed_ref_count = completed_metadata["ref_count"]
    assert isinstance(completed_ref_count, int)
    assert completed_ref_count >= 1
    assert "safe/topic" not in json.dumps(completed_metadata)


def test_git_tag_metadata_tool_executes_after_policy_allow_and_is_audited(
    tmp_path: Path,
) -> None:
    service, commit_hash = make_git_tag_metadata_service(tmp_path)

    result = service.call_tool(
        tool_name="git.show.tag_metadata",
        arguments={"selector": {"kind": "all_local_tags"}, "limit": 10},
        principal=principal(),
        session_id="sess_git_tags",
    )

    assert result.status == "completed"
    assert result.content["tool_name"] == "git.show.tag_metadata"
    tags = cast(list[JsonObject], result.content["tags"])
    assert tags
    assert tags[0]["tag_id"] == "tag_0001"
    assert tags[0]["resolved_commit_hash"] == commit_hash
    output_policy = cast(JsonObject, result.content["output_policy"])
    assert output_policy["tag_names_included"] is False
    assert "v-secret-customer-release" not in json.dumps(result.content)
    assert "refs/tags" not in json.dumps(result.content)
    payloads = audit_payloads(tmp_path)
    assert [payload["event_type"] for payload in payloads] == [
        "policy.evaluated",
        "tool.execution.started",
        "tool.execution.completed",
    ]
    policy_metadata = cast(JsonObject, payloads[0]["metadata"])
    assert policy_metadata["resource_type"] == "git_tags"
    assert policy_metadata["resource_in_scope"] is True
    execution_resource = cast(JsonObject, payloads[1]["resource"])
    assert execution_resource["type"] == "git_tags"
    assert execution_resource["selector_kind"] == "all_local_tags"
    completed_metadata = cast(JsonObject, payloads[2]["metadata"])
    assert completed_metadata["selector_kind"] == "all_local_tags"
    assert completed_metadata["tag_count"] == 1
    assert completed_metadata["total_tag_count"] == 1
    assert completed_metadata["tag_names_included"] is False
    assert completed_metadata["tag_messages_included"] is False
    assert completed_metadata["tag_signatures_included"] is False
    assert completed_metadata["stable_tag_hashes_included"] is False
    assert completed_metadata["tag_ids_are_response_local"] is True
    assert "v-secret-customer-release" not in json.dumps(completed_metadata)


def test_project_manifest_summary_tool_executes_after_policy_allow_and_is_audited(
    tmp_path: Path,
) -> None:
    service = make_project_manifest_summary_service(tmp_path)

    result = service.call_tool(
        tool_name="project.manifest.summary",
        arguments={"manifest_kinds": ["package.json"], "limit": 5},
        principal=principal(),
        session_id="sess_project_manifest",
    )

    assert result.status == "completed"
    assert result.content["manifest_count"] == 1
    output_policy = cast(JsonObject, result.content["output_policy"])
    assert output_policy["dependency_names_included"] is False
    assert output_policy["package_script_values_included"] is False
    assert output_policy["registry_or_network_access_used"] is False
    assert "internal-package" not in json.dumps(result.content)
    assert "TOKEN=secret" not in json.dumps(result.content)
    payloads = audit_payloads(tmp_path)
    assert [payload["event_type"] for payload in payloads] == [
        "policy.evaluated",
        "tool.execution.started",
        "tool.execution.completed",
    ]
    policy_metadata = cast(JsonObject, payloads[0]["metadata"])
    assert policy_metadata["resource_type"] == "project_manifest"
    assert policy_metadata["resource_in_scope"] is True
    execution_resource = cast(JsonObject, payloads[1]["resource"])
    assert execution_resource["type"] == "project_manifest"
    completed_metadata = cast(JsonObject, payloads[2]["metadata"])
    assert completed_metadata["manifest_count"] == 1
    assert completed_metadata["manifest_kinds"] == ["package.json"]
    assert completed_metadata["file_contents_included"] is False
    assert completed_metadata["dependency_names_included"] is False
    assert completed_metadata["package_script_values_included"] is False
    assert completed_metadata["package_manager_execution_used"] is False


def test_project_dependency_summary_tool_executes_after_policy_allow_and_is_audited(
    tmp_path: Path,
) -> None:
    service = make_project_dependency_summary_service(tmp_path)

    result = service.call_tool(
        tool_name="project.dependency.summary",
        arguments={"manifest_kinds": ["package.json"], "limit": 5},
        principal=principal(),
        session_id="sess_project_dependency",
    )

    assert result.status == "completed"
    assert result.content["manifest_count"] == 1
    assert result.content["total_direct_dependency_count"] == 2
    output_policy = cast(JsonObject, result.content["output_policy"])
    assert output_policy["dependency_names_included"] is False
    assert output_policy["dependency_versions_included"] is False
    assert output_policy["package_script_names_included"] is False
    assert output_policy["lockfile_contents_included"] is False
    assert output_policy["registry_or_network_access_used"] is False
    assert "internal-package" not in json.dumps(result.content)
    assert "test-helper" not in json.dumps(result.content)
    assert "TOKEN=secret" not in json.dumps(result.content)
    payloads = audit_payloads(tmp_path)
    assert [payload["event_type"] for payload in payloads] == [
        "policy.evaluated",
        "tool.execution.started",
        "tool.execution.completed",
    ]
    policy_metadata = cast(JsonObject, payloads[0]["metadata"])
    assert policy_metadata["resource_type"] == "project_dependencies"
    assert policy_metadata["resource_in_scope"] is True
    execution_resource = cast(JsonObject, payloads[1]["resource"])
    assert execution_resource["type"] == "project_dependencies"
    completed_metadata = cast(JsonObject, payloads[2]["metadata"])
    assert completed_metadata["manifest_count"] == 1
    assert completed_metadata["total_direct_dependency_count"] == 2
    assert completed_metadata["manifest_kinds"] == ["package.json"]


def test_project_structure_summary_tool_executes_after_policy_allow_and_is_audited(
    tmp_path: Path,
) -> None:
    service = make_project_structure_summary_service(tmp_path)

    result = service.call_tool(
        tool_name="project.structure.summary",
        arguments={"root": ".", "max_depth": 2, "limit": 25},
        principal=principal(),
        session_id="sess_project_structure",
    )

    assert result.status == "completed"
    assert result.content["tool_name"] == "project.structure.summary"
    assert cast(JsonObject, result.content["summary"])["visible_directory_count"] == 2
    output_policy = cast(JsonObject, result.content["output_policy"])
    assert output_policy["file_contents_included"] is False
    assert output_policy["raw_file_names_included"] is False
    assert output_policy["raw_recursive_listing_included"] is False
    assert output_policy["package_manager_execution_used"] is False
    assert "private_feature" not in json.dumps(result.content)
    assert "Private Roadmap" not in json.dumps(result.content)
    assert "TOKEN=secret" not in json.dumps(result.content)
    payloads = audit_payloads(tmp_path)
    assert [payload["event_type"] for payload in payloads] == [
        "policy.evaluated",
        "tool.execution.started",
        "tool.execution.completed",
    ]
    policy_metadata = cast(JsonObject, payloads[0]["metadata"])
    assert policy_metadata["resource_type"] == "project_structure"
    assert policy_metadata["resource_in_scope"] is True
    execution_resource = cast(JsonObject, payloads[1]["resource"])
    assert execution_resource["type"] == "project_structure"
    completed_metadata = cast(JsonObject, payloads[2]["metadata"])
    assert completed_metadata["visible_directory_count"] == 2
    assert completed_metadata["visible_file_count"] == 2
    assert completed_metadata["directory_categories_keys"] == [
        "build_output",
        "config",
        "docs",
        "generated",
        "source",
        "tests",
        "unknown",
        "vendor",
    ]
    assert completed_metadata["file_contents_included"] is False
    assert completed_metadata["raw_file_names_included"] is False
    assert completed_metadata["raw_recursive_listing_included"] is False
    assert completed_metadata["raw_sensitive_paths_included"] is False
    assert completed_metadata["package_manager_execution_used"] is False


def test_project_test_summary_tool_executes_after_policy_allow_and_is_audited(
    tmp_path: Path,
) -> None:
    service = make_project_test_summary_service(tmp_path)

    result = service.call_tool(
        tool_name="project.test.summary",
        arguments={"root": ".", "max_depth": 3, "limit": 30},
        principal=principal(),
        session_id="sess_project_test",
    )

    assert result.status == "completed"
    assert result.content["tool_name"] == "project.test.summary"
    assert cast(JsonObject, result.content["summary"])["visible_test_directory_count"] == 1
    assert cast(JsonObject, result.content["summary"])["visible_test_file_count"] == 2
    output_policy = cast(JsonObject, result.content["output_policy"])
    assert output_policy["file_contents_included"] is False
    assert output_policy["test_file_names_included"] is False
    assert output_policy["raw_paths_included"] is False
    assert output_policy["test_execution_used"] is False
    assert "test_private_feature" not in json.dumps(result.content)
    assert "feature.test" not in json.dumps(result.content)
    assert "TOKEN=secret" not in json.dumps(result.content)
    payloads = audit_payloads(tmp_path)
    assert [payload["event_type"] for payload in payloads] == [
        "policy.evaluated",
        "tool.execution.started",
        "tool.execution.completed",
    ]
    policy_metadata = cast(JsonObject, payloads[0]["metadata"])
    assert policy_metadata["resource_type"] == "project_tests"
    assert policy_metadata["resource_in_scope"] is True
    execution_resource = cast(JsonObject, payloads[1]["resource"])
    assert execution_resource["type"] == "project_tests"
    completed_metadata = cast(JsonObject, payloads[2]["metadata"])
    assert completed_metadata["visible_test_directory_count"] == 1
    assert completed_metadata["visible_test_file_count"] == 2
    assert completed_metadata["framework_hints_keys"] == [
        "go_test_hint",
        "java_test_hint",
        "javascript_test_hint",
        "python_pytest_hint",
        "python_unittest_hint",
        "rust_test_hint",
        "typescript_test_hint",
        "unknown_test_hint",
    ]
    assert completed_metadata["file_contents_included"] is False
    assert completed_metadata["test_file_names_included"] is False
    assert completed_metadata["raw_paths_included"] is False
    assert completed_metadata["test_execution_used"] is False


def test_project_docs_summary_tool_executes_after_policy_allow_and_is_audited(
    tmp_path: Path,
) -> None:
    service = make_project_docs_summary_service(tmp_path)

    result = service.call_tool(
        tool_name="project.docs.summary",
        arguments={"root": ".", "max_depth": 3, "limit": 30},
        principal=principal(),
        session_id="sess_project_docs",
    )

    assert result.status == "completed"
    assert result.content["tool_name"] == "project.docs.summary"
    assert (
        cast(JsonObject, result.content["summary"])["visible_documentation_directory_count"] == 1
    )
    assert cast(JsonObject, result.content["summary"])["visible_documentation_file_count"] == 3
    output_policy = cast(JsonObject, result.content["output_policy"])
    assert output_policy["file_contents_included"] is False
    assert output_policy["documentation_file_names_included"] is False
    assert output_policy["documentation_headings_included"] is False
    assert output_policy["raw_paths_included"] is False
    assert output_policy["documentation_build_execution_used"] is False
    assert "README" not in json.dumps(result.content)
    assert "api.md" not in json.dumps(result.content)
    assert "Secret Project" not in json.dumps(result.content)
    assert "TOKEN=secret" not in json.dumps(result.content)
    payloads = audit_payloads(tmp_path)
    assert [payload["event_type"] for payload in payloads] == [
        "policy.evaluated",
        "tool.execution.started",
        "tool.execution.completed",
    ]
    policy_metadata = cast(JsonObject, payloads[0]["metadata"])
    assert policy_metadata["resource_type"] == "project_docs"
    assert policy_metadata["resource_in_scope"] is True
    execution_resource = cast(JsonObject, payloads[1]["resource"])
    assert execution_resource["type"] == "project_docs"
    completed_metadata = cast(JsonObject, payloads[2]["metadata"])
    assert completed_metadata["visible_documentation_directory_count"] == 1
    assert completed_metadata["visible_documentation_file_count"] == 3
    assert completed_metadata["documentation_type_counts_keys"] == [
        "api_docs",
        "changelog_docs",
        "contributing_docs",
        "how_to_docs",
        "license_docs",
        "readme_docs",
        "reference_docs",
        "tutorial_docs",
        "unknown_docs",
    ]
    assert completed_metadata["file_contents_included"] is False
    assert completed_metadata["documentation_file_names_included"] is False
    assert completed_metadata["documentation_headings_included"] is False
    assert completed_metadata["raw_paths_included"] is False
    assert completed_metadata["documentation_build_execution_used"] is False


def test_project_language_summary_tool_executes_after_policy_allow_and_is_audited(
    tmp_path: Path,
) -> None:
    service = make_project_language_summary_service(tmp_path)

    result = service.call_tool(
        tool_name="project.language.summary",
        arguments={"root": ".", "max_depth": 3, "limit": 30},
        principal=principal(),
        session_id="sess_project_language",
    )

    assert result.status == "completed"
    assert result.content["tool_name"] == "project.language.summary"
    assert cast(JsonObject, result.content["summary"])["visible_source_directory_count"] == 2
    assert cast(JsonObject, result.content["summary"])["visible_source_like_file_count"] == 3
    output_policy = cast(JsonObject, result.content["output_policy"])
    assert output_policy["file_contents_included"] is False
    assert output_policy["language_file_names_included"] is False
    assert output_policy["raw_extensions_included"] is False
    assert output_policy["raw_paths_included"] is False
    assert output_policy["language_detector_execution_used"] is False
    assert "main.py" not in json.dumps(result.content)
    assert "app.ts" not in json.dumps(result.content)
    assert ".py" not in json.dumps(result.content)
    assert "TOKEN=secret" not in json.dumps(result.content)
    payloads = audit_payloads(tmp_path)
    assert [payload["event_type"] for payload in payloads] == [
        "policy.evaluated",
        "tool.execution.started",
        "tool.execution.completed",
    ]
    policy_metadata = cast(JsonObject, payloads[0]["metadata"])
    assert policy_metadata["resource_type"] == "project_language"
    assert policy_metadata["resource_in_scope"] is True
    execution_resource = cast(JsonObject, payloads[1]["resource"])
    assert execution_resource["type"] == "project_language"
    completed_metadata = cast(JsonObject, payloads[2]["metadata"])
    assert completed_metadata["visible_source_directory_count"] == 2
    assert completed_metadata["visible_source_like_file_count"] == 3
    assert completed_metadata["language_family_counts_keys"] == [
        "c_cpp",
        "configuration",
        "documentation",
        "go",
        "java",
        "javascript",
        "markup",
        "python",
        "rust",
        "shell",
        "typescript",
        "unknown",
    ]
    assert completed_metadata["extension_family_counts_keys"] == [
        "build_metadata",
        "configuration",
        "data",
        "documentation",
        "markup",
        "source_code",
        "unknown",
    ]
    assert completed_metadata["file_contents_included"] is False
    assert completed_metadata["language_file_names_included"] is False
    assert completed_metadata["raw_extensions_included"] is False
    assert completed_metadata["raw_paths_included"] is False
    assert completed_metadata["language_detector_execution_used"] is False


def test_project_config_summary_tool_executes_after_policy_allow_and_is_audited(
    tmp_path: Path,
) -> None:
    service = make_project_config_summary_service(tmp_path)

    result = service.call_tool(
        tool_name="project.config.summary",
        arguments={"root": ".", "max_depth": 3, "limit": 30},
        principal=principal(),
        session_id="sess_project_config",
    )

    assert result.status == "completed"
    assert result.content["tool_name"] == "project.config.summary"
    assert cast(JsonObject, result.content["summary"])["visible_config_directory_count"] == 1
    assert cast(JsonObject, result.content["summary"])["visible_config_like_file_count"] == 3
    output_policy = cast(JsonObject, result.content["output_policy"])
    assert output_policy["file_contents_included"] is False
    assert output_policy["config_file_names_included"] is False
    assert output_policy["config_contents_included"] is False
    assert output_policy["config_values_included"] is False
    assert output_policy["raw_paths_included"] is False
    assert output_policy["environment_names_or_values_included"] is False
    assert output_policy["config_parser_execution_used"] is False
    dumped = json.dumps(result.content)
    assert "pyproject" not in dumped
    assert "app.yaml" not in dumped
    assert "settings.ini" not in dumped
    assert "Secret Release" not in dumped
    assert "--token secret" not in dumped
    assert "password" not in dumped
    payloads = audit_payloads(tmp_path)
    assert [payload["event_type"] for payload in payloads] == [
        "policy.evaluated",
        "tool.execution.started",
        "tool.execution.completed",
    ]
    policy_metadata = cast(JsonObject, payloads[0]["metadata"])
    assert policy_metadata["resource_type"] == "project_config"
    assert policy_metadata["resource_in_scope"] is True
    execution_resource = cast(JsonObject, payloads[1]["resource"])
    assert execution_resource["type"] == "project_config"
    completed_metadata = cast(JsonObject, payloads[2]["metadata"])
    assert completed_metadata["visible_config_directory_count"] == 1
    assert completed_metadata["visible_config_like_file_count"] == 3
    assert completed_metadata["config_category_counts_keys"] == [
        "build_config",
        "ci_workflow_config",
        "container_deployment_config",
        "editor_tooling_config",
        "lint_format_config",
        "runtime_app_config",
        "test_config",
        "unknown_config",
    ]
    assert completed_metadata["config_location_counts_keys"] == [
        "ci_directory",
        "config_directory",
        "root_level",
        "source_adjacent_config",
        "tooling_directory",
        "unknown_location",
    ]
    assert completed_metadata["file_contents_included"] is False
    assert completed_metadata["config_file_names_included"] is False
    assert completed_metadata["config_contents_included"] is False
    assert completed_metadata["config_values_included"] is False


def test_project_ci_summary_tool_executes_after_policy_allow_and_is_audited(
    tmp_path: Path,
) -> None:
    service = make_project_ci_summary_service(tmp_path)

    result = service.call_tool(
        tool_name="project.ci.summary",
        arguments={"root": ".", "max_depth": 4, "limit": 30},
        principal=principal(),
        session_id="sess_project_ci",
    )

    assert result.status == "completed"
    assert result.content["tool_name"] == "project.ci.summary"
    summary = cast(JsonObject, result.content["summary"])
    assert summary["visible_ci_config_count"] == 1
    assert cast(JsonObject, result.content["provider_counts"])["github_actions"] == 1
    assert cast(JsonObject, result.content["trigger_category_counts"])["push"] == 1
    assert cast(JsonObject, result.content["job_category_counts"])["test"] == 1
    output_policy = cast(JsonObject, result.content["output_policy"])
    assert output_policy["file_contents_included"] is False
    assert output_policy["workflow_names_included"] is False
    assert output_policy["raw_paths_included"] is False
    assert output_policy["command_values_included"] is False
    assert output_policy["script_values_included"] is False
    assert output_policy["ci_execution_used"] is False
    dumped = json.dumps(result.content)
    assert "private-ci" not in dumped
    assert "Secret Release" not in dumped
    assert "pytest" not in dumped
    assert "ruff" not in dumped
    assert "--token secret" not in dumped
    payloads = audit_payloads(tmp_path)
    assert [payload["event_type"] for payload in payloads] == [
        "policy.evaluated",
        "tool.execution.started",
        "tool.execution.completed",
    ]
    policy_metadata = cast(JsonObject, payloads[0]["metadata"])
    assert policy_metadata["resource_type"] == "project_ci"
    assert policy_metadata["resource_in_scope"] is True
    execution_resource = cast(JsonObject, payloads[1]["resource"])
    assert execution_resource["type"] == "project_ci"
    completed_metadata = cast(JsonObject, payloads[2]["metadata"])
    assert completed_metadata["visible_ci_config_count"] == 1
    assert completed_metadata["provider_counts_keys"] == [
        "azure_pipelines",
        "buildkite",
        "circleci",
        "github_actions",
        "gitlab_ci",
        "jenkins",
        "travis",
        "unknown_ci",
    ]
    assert completed_metadata["trigger_category_counts_keys"] == [
        "manual",
        "pull_request",
        "push",
        "release",
        "schedule",
        "tag",
        "unknown_trigger",
    ]
    assert completed_metadata["job_category_counts_keys"] == [
        "build",
        "deploy_label",
        "lint",
        "release_label",
        "security_scan_label",
        "test",
        "unknown_job",
    ]
    assert completed_metadata["file_contents_included"] is False
    assert completed_metadata["raw_paths_included"] is False
    assert completed_metadata["environment_names_or_values_included"] is False
    assert completed_metadata["registry_or_network_access_used"] is False
    assert completed_metadata["package_manager_execution_used"] is False


def test_read_tool_output_is_redacted_and_audit_summary_is_recorded(tmp_path: Path) -> None:
    service = make_read_service(tmp_path, content="TOKEN=secret-value\nvisible\n")

    result = service.call_tool(
        tool_name="fs.read",
        arguments={"path": "README.md"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "completed"
    assert result.content["content"] == "TOKEN=[REDACTED]\nvisible\n"
    payloads = audit_payloads(tmp_path)
    metadata = cast(JsonObject, payloads[-1]["metadata"])
    assert metadata["redaction_count"] == 1
    assert metadata["redaction_paths"] == ["$.content"]


def test_policy_obligation_redact_fields_extends_output_redaction(tmp_path: Path) -> None:
    policy_yaml = """
version: test
rules:
  - id: allow_reads
    decision: allow
    reason: reads allowed
    match:
      tool.risk: read
      resource.in_scope: true
    obligations:
      audit_level: full
      redact_fields:
        - content
"""
    service = make_read_service(tmp_path, content="ordinary content\n", policy_yaml=policy_yaml)

    result = service.call_tool(
        tool_name="fs.read",
        arguments={"path": "README.md"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "completed"
    assert result.content["content"] == "[REDACTED]"
    metadata = cast(JsonObject, audit_payloads(tmp_path)[-1]["metadata"])
    assert metadata["redaction_paths"] == ["$.content"]


def test_denied_read_attempt_is_audited_before_execution(tmp_path: Path) -> None:
    service = make_read_service(tmp_path)

    result = service.call_tool(
        tool_name="fs.read",
        arguments={"path": "../README.md"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert result.is_error is True
    payloads = audit_payloads(tmp_path)
    assert [payload["event_type"] for payload in payloads] == ["policy.evaluated"]
    assert payloads[0]["decision"] == "deny"
    metadata = cast(JsonObject, payloads[0]["metadata"])
    assert metadata["reason"] == "path traversal is outside the workspace scope"


def test_http_fetch_executes_after_policy_allow_and_is_audited(tmp_path: Path) -> None:
    opener = FakeHttpOpener()
    service = make_http_service(tmp_path, opener=opener)

    result = service.call_tool(
        tool_name=HTTP_FETCH_TOOL,
        arguments={"url": "https://example.com/data"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "completed"
    assert result.content["body_text"] == "hello network"
    assert opener.requests[0].full_url == "https://example.com/data"
    payloads = audit_payloads(tmp_path)
    assert [payload["event_type"] for payload in payloads] == [
        "policy.evaluated",
        "tool.execution.started",
        "tool.execution.completed",
    ]


def test_http_fetch_output_is_redacted_before_return(tmp_path: Path) -> None:
    opener = FakeHttpOpener(
        FakeHttpResponse(
            body=b'{"token":"secret-token","message":"Bearer abcdefghijklmnopqrstuvwxyz"}',
            content_type="application/json; charset=utf-8",
        )
    )
    service = make_http_service(tmp_path, opener=opener)

    result = service.call_tool(
        tool_name=HTTP_FETCH_TOOL,
        arguments={"url": "https://example.com/data"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "completed"
    assert "secret-token" not in str(result.content)
    assert "abcdefghijklmnopqrstuvwxyz" not in str(result.content)
    body_json = cast(JsonObject, result.content["body_json"])
    assert body_json["token"] == "[REDACTED]"
    metadata = cast(JsonObject, audit_payloads(tmp_path)[-1]["metadata"])
    assert metadata["redaction_count"] == 3
    assert metadata["redaction_paths"] == [
        "$.body_text",
        "$.body_json.token",
        "$.body_json.message",
    ]


def test_unallowlisted_http_fetch_is_denied_by_policy_and_audited(tmp_path: Path) -> None:
    opener = FakeHttpOpener()
    service = make_http_service(tmp_path, allowlist="", opener=opener)

    result = service.call_tool(
        tool_name=HTTP_FETCH_TOOL,
        arguments={"url": "https://example.com/data"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert result.is_error is True
    assert opener.requests == []
    payloads = audit_payloads(tmp_path)
    assert [payload["event_type"] for payload in payloads] == ["policy.evaluated"]
    assert payloads[0]["decision"] == "deny"


def test_arbitrary_git_flags_are_rejected_by_manifest_schema(tmp_path: Path) -> None:
    service = make_read_service(tmp_path)

    result = service.call_tool(
        tool_name="git.status",
        arguments={"path": ".", "flag": "--help"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert result.content == {"reason": "invalid tool arguments"}
    assert [payload["event_type"] for payload in audit_payloads(tmp_path)] == ["policy.evaluated"]


def test_patch_proposal_runs_through_policy_and_audit(tmp_path: Path) -> None:
    service = make_patch_service(tmp_path)
    unified_diff = "--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-old\n+new\n"

    result = service.call_tool(
        tool_name="fs.patch.propose",
        arguments={"path": "README.md", "unified_diff": unified_diff},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "completed"
    assert result.content["proposal_id"]
    assert result.content["path"] == "README.md"
    payloads = audit_payloads(tmp_path)
    assert [payload["event_type"] for payload in payloads] == [
        "policy.evaluated",
        "tool.execution.started",
        "tool.execution.completed",
    ]


def test_invalid_patch_proposal_path_is_audited_before_execution(tmp_path: Path) -> None:
    service = make_patch_service(tmp_path)

    result = service.call_tool(
        tool_name="fs.patch.propose",
        arguments={"path": "../README.md", "unified_diff": "not a diff"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert result.is_error is True
    payloads = audit_payloads(tmp_path)
    assert [payload["event_type"] for payload in payloads] == ["policy.evaluated"]
    assert payloads[0]["decision"] == "deny"
    metadata = cast(JsonObject, payloads[0]["metadata"])
    assert metadata["reason"] == "path traversal is outside the workspace scope"


def test_patch_apply_with_proposal_id_returns_approval_required(tmp_path: Path) -> None:
    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"proposal_id": proposal["proposal_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "approval_required"
    assert result.content["approval_id"]
    assert result.content["proposal_id"] == proposal["proposal_id"]
    assert result.content["proposal_hash"] == proposal["proposal_hash"]
    assert result.content["path"] == "README.md"


def test_patch_apply_approval_scope_binds_evidence(tmp_path: Path) -> None:
    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"proposal_id": proposal["proposal_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    approval = harness.approval_service.get(str(result.content["approval_id"]))
    scope = approval.one_time_scope
    assert scope["tool_name"] == "fs.patch.apply"
    assert scope["proposal_id"] == proposal["proposal_id"]
    assert scope["proposal_hash"] == proposal["proposal_hash"]
    assert scope["base_file_hash"] == proposal["base_file_hash"]
    assert scope["manifest_hash"]
    assert scope["manifest_version"] == "1.0.0"
    tool_input_schema_hash = scope["tool_input_schema_hash"]
    assert isinstance(tool_input_schema_hash, str)
    assert tool_input_schema_hash.startswith("sha256:")
    assert scope["policy_engine"] == "yaml"
    assert scope["policy_hash"] == scope["policy_version"]
    assert scope["matched_rules"] == ["require_write_approval"]
    assert scope["requesting_principal"] == principal()
    assert scope["request_hash"] == approval.request_hash
    assert scope["expires_at"] == approval.expires_at.isoformat()
    assert approval.metadata["approval_scope_hash"] == sha256_digest(scope)


def test_approved_patch_apply_writes_file_and_replay_is_rejected(tmp_path: Path) -> None:
    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )
    replay = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "completed"
    assert harness.workspace_root.joinpath("README.md").read_text(encoding="utf-8") == "new\n"
    attempts = harness.patch_service.list_apply_attempts()
    assert len(attempts) == 1
    assert attempts[0].attempt_id.startswith("pa_")
    assert attempts[0].approval_id == approval["approval_id"]
    assert attempts[0].proposal_id == proposal["proposal_id"]
    assert attempts[0].status == "completed"
    assert attempts[0].base_file_hash == proposal["base_file_hash"]
    assert attempts[0].expected_post_apply_hash == sha256_digest("new\n")
    assert replay.status == "denied"
    assert "not proposed" in str(replay.content["reason"])
    payloads = audit_payloads(tmp_path)
    event_types = [payload["event_type"] for payload in payloads]
    assert "tool.execution.completed" in event_types
    assert event_types[-1] == "tool.execution.failed"


def test_patch_apply_rejects_proposal_hash_mismatch(tmp_path: Path) -> None:
    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")
    with sqlite3.connect(harness.db_path) as connection:
        connection.execute(
            "UPDATE patch_proposals SET proposal_hash = ? WHERE proposal_id = ?",
            ("sha256:" + ("1" * 64), proposal["proposal_id"]),
        )
        connection.commit()

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert "hash mismatch" in str(result.content["reason"])
    assert harness.workspace_root.joinpath("README.md").read_text(encoding="utf-8") == "old\n"


def test_patch_apply_rejects_manifest_scope_mismatch(tmp_path: Path) -> None:
    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    approval_record = harness.approval_service.get(str(approval["approval_id"]))
    scope = dict(approval_record.one_time_scope)
    scope["manifest_hash"] = "sha256:" + ("2" * 64)
    with sqlite3.connect(harness.db_path) as connection:
        connection.execute(
            "UPDATE approvals SET one_time_scope_json = ? WHERE approval_id = ?",
            (canonical_json(scope), approval["approval_id"]),
        )
        connection.commit()
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert "manifest hash mismatch" in str(result.content["reason"])
    assert harness.workspace_root.joinpath("README.md").read_text(encoding="utf-8") == "old\n"


@pytest.mark.parametrize(
    ("scope_key", "replacement", "expected_reason"),
    [
        ("policy_hash", "sha256:" + ("3" * 64), "policy hash mismatch"),
        ("policy_version", "sha256:" + ("4" * 64), "policy version mismatch"),
        ("policy_document_version", "drifted-policy", "policy document version mismatch"),
        ("matched_rules", ["different_rule"], "matched rules mismatch"),
        ("manifest_version", "9.9.9", "manifest version mismatch"),
        ("tool_input_schema_hash", "sha256:" + ("5" * 64), "tool input schema mismatch"),
    ],
)
def test_patch_apply_rejects_approval_scope_drift(
    tmp_path: Path,
    scope_key: str,
    replacement: object,
    expected_reason: str,
) -> None:
    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    _mutate_approval_scope(harness.db_path, str(approval["approval_id"]), scope_key, replacement)
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert expected_reason in str(result.content["reason"])
    assert harness.workspace_root.joinpath("README.md").read_text(encoding="utf-8") == "old\n"
    failed_event = audit_payloads(tmp_path)[-1]
    assert failed_event["event_type"] == "tool.execution.failed"
    failed_metadata = cast(JsonObject, failed_event["metadata"])
    assert failed_metadata["approval_binding_verified"] is False
    assert expected_reason in str(failed_metadata["reason"])


def test_patch_apply_rejects_wrong_requesting_principal(tmp_path: Path) -> None:
    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal={"id": "agent:other", "roles": ["AgentDeveloper"]},
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert "principal mismatch" in str(result.content["reason"])
    assert harness.workspace_root.joinpath("README.md").read_text(encoding="utf-8") == "old\n"


def test_patch_apply_rejects_stale_base_without_partial_write(tmp_path: Path) -> None:
    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")
    harness.workspace_root.joinpath("README.md").write_text("changed elsewhere\n", encoding="utf-8")

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert "changed since proposal" in str(result.content["reason"])
    assert (
        harness.workspace_root.joinpath("README.md").read_text(encoding="utf-8")
        == "changed elsewhere\n"
    )


def test_patch_apply_failure_before_replace_records_failed_attempt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ithildin_api.patches as patches

    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")

    def fail_before_replace(
        workspace_root: Path,
        relative_path: str,
        content: str,
        **_: object,
    ) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(patches, "_atomic_write_text", fail_before_replace)

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    attempts = harness.patch_service.list_apply_attempts()
    assert result.status == "denied"
    assert "failed to apply patch safely" in str(result.content["reason"])
    assert harness.workspace_root.joinpath("README.md").read_text(encoding="utf-8") == "old\n"
    assert attempts[0].status == "failed"
    assert attempts[0].failure_reason == "failed to apply patch safely"
    assert harness.approval_service.get(str(approval["approval_id"])).status.value == "failed"


def test_patch_apply_rechecks_base_immediately_before_replace(tmp_path: Path) -> None:
    phases: list[str] = []

    def fault(phase: str) -> None:
        phases.append(phase)
        if phase == "before_atomic_replace":
            (harness.workspace_root / "README.md").write_text(
                "concurrent change\n",
                encoding="utf-8",
            )

    harness = make_patch_harness(tmp_path, apply_fault_hook=fault)
    proposal = propose_patch(harness.service)
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert "failed to apply patch safely" in str(result.content["reason"])
    assert "before_atomic_replace" in phases
    assert (
        harness.workspace_root.joinpath("README.md").read_text(encoding="utf-8")
        == "concurrent change\n"
    )
    assert harness.patch_service.list_apply_attempts()[0].status == "failed"
    assert harness.approval_service.get(str(approval["approval_id"])).status.value == "failed"


def test_patch_apply_attempt_creation_failure_leaves_file_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")

    def fail_create_attempt(attempt: object) -> NoReturn:
        raise sqlite3.Error("simulated attempt insert failure")

    monkeypatch.setattr(harness.patch_service.store, "create_apply_attempt", fail_create_attempt)

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert "failed to apply patch safely" in str(result.content["reason"])
    assert harness.workspace_root.joinpath("README.md").read_text(encoding="utf-8") == "old\n"
    assert harness.patch_service.list_apply_attempts() == []
    assert harness.approval_service.get(str(approval["approval_id"])).status.value == "failed"


def test_patch_apply_fault_after_begin_execution_marks_failed_without_write(
    tmp_path: Path,
) -> None:
    phases: list[str] = []

    def fault(phase: str) -> None:
        phases.append(phase)
        if phase == "after_begin_execution":
            raise OSError("simulated post-begin failure")

    harness = make_patch_harness(tmp_path, apply_fault_hook=fault)
    proposal = propose_patch(harness.service)
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert "failed to apply patch safely" in str(result.content["reason"])
    assert phases == ["after_proposal_validation", "after_begin_execution"]
    assert harness.workspace_root.joinpath("README.md").read_text(encoding="utf-8") == "old\n"
    assert harness.patch_service.list_apply_attempts() == []
    assert harness.approval_service.get(str(approval["approval_id"])).status.value == "failed"


def test_patch_apply_failure_after_replace_records_recovery_required(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")
    original_compare_and_set_status = harness.patch_service.store.compare_and_set_status

    def fail_after_replace(
        proposal_id: str,
        *,
        expected_status: str,
        next_status: str,
    ) -> object:
        if expected_status == "applying" and next_status == "applied":
            raise PatchProposalError("simulated database failure after replace")
        return original_compare_and_set_status(
            proposal_id,
            expected_status=expected_status,
            next_status=next_status,
        )

    monkeypatch.setattr(
        harness.patch_service.store,
        "compare_and_set_status",
        fail_after_replace,
    )

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )
    monkeypatch.setattr(
        harness.patch_service.store,
        "compare_and_set_status",
        original_compare_and_set_status,
    )

    attempts = harness.patch_service.list_apply_attempts()
    diagnostics = harness.patch_service.patch_apply_diagnostics(harness.approval_service)
    diagnostic_attempts = cast(list[JsonObject], diagnostics["attempts"])
    stuck_approvals = cast(list[JsonObject], diagnostics["stuck_approvals"])

    assert result.status == "denied"
    assert "recovery diagnostics required" in str(result.content["reason"])
    assert harness.workspace_root.joinpath("README.md").read_text(encoding="utf-8") == "new\n"
    assert harness.approval_service.get(str(approval["approval_id"])).status.value == "executing"
    assert attempts[0].status == "recovery_required"
    assert attempts[0].failure_reason == "simulated database failure after replace"
    assert diagnostics["status"] == "recovery_required"
    assert diagnostic_attempts[0]["current_matches_expected_post_apply_hash"] is True
    assert diagnostic_attempts[0]["diagnostic_status"] == "recovery_required"
    assert stuck_approvals[0]["approval_id"] == approval["approval_id"]


def test_patch_apply_completed_audit_failure_is_diagnosable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")
    original_audit_execution = harness.service._audit_execution

    def fail_completed_audit(**kwargs: object) -> None:
        if kwargs["event_type"] == AuditEventType.TOOL_EXECUTION_COMPLETED:
            raise RuntimeError("simulated completion audit failure")
        original_audit_execution(**kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(harness.service, "_audit_execution", fail_completed_audit)

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    attempts = harness.patch_service.list_apply_attempts()
    diagnostics = harness.patch_service.patch_apply_diagnostics(harness.approval_service)
    diagnostic_attempts = cast(list[JsonObject], diagnostics["attempts"])
    payloads = audit_payloads(tmp_path)
    event_types = [payload["event_type"] for payload in payloads]
    patch_apply_completed_events: list[JsonObject] = []
    for payload in payloads:
        metadata = payload.get("metadata")
        if (
            payload["event_type"] == "tool.execution.completed"
            and isinstance(metadata, dict)
            and metadata.get("executor") == "patch_apply"
        ):
            patch_apply_completed_events.append(payload)

    assert result.status == "denied"
    assert "recovery diagnostics required" in str(result.content["reason"])
    assert harness.workspace_root.joinpath("README.md").read_text(encoding="utf-8") == "new\n"
    assert harness.approval_service.get(str(approval["approval_id"])).status.value == "executed"
    assert attempts[0].status == "recovery_required"
    assert attempts[0].failure_reason == "patch apply completion audit failed"
    assert diagnostics["status"] == "recovery_required"
    assert diagnostic_attempts[0]["current_matches_expected_post_apply_hash"] is True
    assert patch_apply_completed_events == []
    assert event_types[-1] == "tool.execution.failed"


def test_patch_apply_fault_after_atomic_replace_requires_recovery(
    tmp_path: Path,
) -> None:
    phases: list[str] = []

    def fault(phase: str) -> None:
        phases.append(phase)
        if phase == "after_atomic_replace":
            raise OSError("simulated crash after replace")

    harness = make_patch_harness(tmp_path, apply_fault_hook=fault)
    proposal = propose_patch(harness.service)
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    attempts = harness.patch_service.list_apply_attempts()
    diagnostics = harness.patch_service.patch_apply_diagnostics(harness.approval_service)

    assert result.status == "denied"
    assert "recovery diagnostics required" in str(result.content["reason"])
    assert "after_atomic_replace" in phases
    assert harness.workspace_root.joinpath("README.md").read_text(encoding="utf-8") == "new\n"
    assert attempts[0].status == "recovery_required"
    assert diagnostics["status"] == "recovery_required"
    assert harness.approval_service.get(str(approval["approval_id"])).status.value == "executing"


def test_two_approved_apply_calls_for_same_proposal_mutate_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    barrier = threading.Barrier(2)
    phases: list[str] = []

    def fault(phase: str) -> None:
        if phase == "after_prepare_apply":
            phases.append(phase)
            barrier.wait(timeout=5)

    harness = make_patch_harness(tmp_path, apply_fault_hook=fault)
    proposal = propose_patch(harness.service)
    first_approval = request_patch_apply_approval(
        harness.service,
        cast(str, proposal["proposal_id"]),
    )
    second_approval = request_patch_apply_approval(
        harness.service,
        cast(str, proposal["proposal_id"]),
    )
    harness.approval_service.approve(str(first_approval["approval_id"]), decided_by="user:alice")
    harness.approval_service.approve(str(second_approval["approval_id"]), decided_by="user:alice")
    import ithildin_api.patches as patches

    original_atomic_write = patches._atomic_write_text
    writes: list[str] = []

    def counted_atomic_write(
        workspace_root: Path,
        relative_path: str,
        content: str,
        *,
        expected_base_file_hash: str | None = None,
        max_verify_bytes: int | None = None,
    ) -> None:
        writes.append(relative_path)
        original_atomic_write(
            workspace_root,
            relative_path,
            content,
            expected_base_file_hash=expected_base_file_hash,
            max_verify_bytes=max_verify_bytes,
        )

    monkeypatch.setattr(patches, "_atomic_write_text", counted_atomic_write)

    def apply(approval_id: str) -> str:
        return harness.service.call_tool(
            tool_name="fs.patch.apply",
            arguments={"approval_id": approval_id},
            principal=principal(),
            session_id="sess_1",
        ).status

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(apply, cast(str, first_approval["approval_id"]))
        second_future = executor.submit(apply, cast(str, second_approval["approval_id"]))
        statuses = sorted(
            [
                first_future.result(timeout=10),
                second_future.result(timeout=10),
            ]
        )

    assert statuses == ["completed", "denied"]
    assert phases == ["after_prepare_apply", "after_prepare_apply"]
    assert writes == ["README.md"]
    assert harness.workspace_root.joinpath("README.md").read_text(encoding="utf-8") == "new\n"
    assert (
        harness.patch_service.get_proposal(cast(str, proposal["proposal_id"])).status
        == "applied"
    )


def test_patch_apply_attempt_state_machine_allows_documented_transitions(
    tmp_path: Path,
) -> None:
    harness = make_patch_harness(tmp_path)
    now = datetime.now(UTC)
    attempt = PatchApplyAttempt(
        attempt_id="pa_valid",
        approval_id="appr_valid",
        proposal_id="patch_valid",
        request_id="req_valid",
        workspace_id="default",
        path="README.md",
        proposal_hash="sha256:" + ("1" * 64),
        base_file_hash="sha256:" + ("2" * 64),
        expected_post_apply_hash="sha256:" + ("3" * 64),
        status="prepared",
        failure_reason=None,
        created_at=now,
        updated_at=now,
        metadata={"tool_name": "fs.patch.apply"},
    )

    harness.patch_service.store.create_apply_attempt(attempt)
    harness.patch_service.store.set_apply_attempt_status("pa_valid", "file_replaced")
    completed = harness.patch_service.store.set_apply_attempt_status("pa_valid", "completed")

    assert completed.status == "completed"


def test_patch_apply_attempt_state_machine_rejects_invalid_transitions(
    tmp_path: Path,
) -> None:
    harness = make_patch_harness(tmp_path)
    now = datetime.now(UTC)
    attempt = PatchApplyAttempt(
        attempt_id="pa_invalid",
        approval_id="appr_invalid",
        proposal_id="patch_invalid",
        request_id="req_invalid",
        workspace_id="default",
        path="README.md",
        proposal_hash="sha256:" + ("1" * 64),
        base_file_hash="sha256:" + ("2" * 64),
        expected_post_apply_hash="sha256:" + ("3" * 64),
        status="prepared",
        failure_reason=None,
        created_at=now,
        updated_at=now,
        metadata={"tool_name": "fs.patch.apply"},
    )

    harness.patch_service.store.create_apply_attempt(attempt)

    with pytest.raises(PatchProposalError, match="invalid patch apply attempt transition"):
        harness.patch_service.store.set_apply_attempt_status("pa_invalid", "completed")
    failed = harness.patch_service.store.set_apply_attempt_status("pa_invalid", "failed")
    with pytest.raises(PatchProposalError, match="invalid patch apply attempt transition"):
        harness.patch_service.store.set_apply_attempt_status("pa_invalid", "recovery_required")

    assert failed.status == "failed"


def test_patch_apply_file_replaced_status_failure_is_diagnosable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")
    original_set_apply_attempt_status = harness.patch_service.store.set_apply_attempt_status

    def fail_file_replaced(
        attempt_id: str,
        status: str,
        failure_reason: str | None = None,
    ) -> NoReturn:
        if status == "file_replaced":
            raise sqlite3.Error("simulated file_replaced update failure")
        raise sqlite3.Error("simulated recovery update failure")

    monkeypatch.setattr(
        harness.patch_service.store,
        "set_apply_attempt_status",
        fail_file_replaced,
    )

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )
    monkeypatch.setattr(
        harness.patch_service.store,
        "set_apply_attempt_status",
        original_set_apply_attempt_status,
    )

    attempts = harness.patch_service.list_apply_attempts()
    diagnostics = harness.patch_service.patch_apply_diagnostics(harness.approval_service)
    diagnostic_attempts = cast(list[JsonObject], diagnostics["attempts"])

    assert result.status == "denied"
    assert "recovery diagnostics required" in str(result.content["reason"])
    assert harness.workspace_root.joinpath("README.md").read_text(encoding="utf-8") == "new\n"
    assert harness.approval_service.get(str(approval["approval_id"])).status.value == "executing"
    assert attempts[0].status == "prepared"
    assert diagnostics["status"] == "recovery_required"
    assert diagnostic_attempts[0]["current_matches_expected_post_apply_hash"] is True
    assert diagnostic_attempts[0]["diagnostic_status"] == "recovery_required"


def test_patch_apply_diagnostics_reports_executing_approval_without_attempt_as_ambiguous(
    tmp_path: Path,
) -> None:
    harness = make_patch_harness(tmp_path)
    approval = harness.approval_service.create_pending(
        CreateApprovalInput(
            principal=principal(),
            tool_name="fs.patch.apply",
            resource={"path": "README.md"},
            summary="Apply patch",
            one_time_scope={"proposal_id": "patch_missing"},
        )
    )
    harness.approval_service.approve(approval.approval_id, decided_by="user:alice")
    harness.approval_service.begin_execution(approval.approval_id, approval.request_hash)

    diagnostics = harness.patch_service.patch_apply_diagnostics(harness.approval_service)
    stuck_approvals = cast(list[JsonObject], diagnostics["stuck_approvals"])

    assert diagnostics["status"] == "ambiguous"
    assert diagnostics["attempts"] == []
    assert stuck_approvals[0]["approval_id"] == approval.approval_id
    assert stuck_approvals[0]["has_apply_attempt"] is False


def test_patch_apply_rejects_hardlinked_target_without_partial_write(tmp_path: Path) -> None:
    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")
    try:
        os.link(harness.workspace_root / "README.md", harness.workspace_root / "README-copy.md")
    except OSError as exc:
        pytest.skip(f"hardlinks unavailable: {exc}")

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert "hardlinked" in str(result.content["reason"])
    assert harness.workspace_root.joinpath("README.md").read_text(encoding="utf-8") == "old\n"


def test_patch_apply_denies_symlink_swap_during_apply_preparation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if not hasattr(os, "O_NOFOLLOW"):
        pytest.skip("O_NOFOLLOW unavailable on this platform")
    harness = make_patch_harness(tmp_path)
    proposal = propose_patch(harness.service)
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    original_resolver = harness.patch_service.filesystem.resolve_existing_path
    did_swap = False

    def swap_to_symlink(path: str) -> Path:
        nonlocal did_swap
        resolved = original_resolver(path)
        if path == "README.md" and not did_swap:
            did_swap = True
            resolved.unlink()
            resolved.symlink_to(outside)
        return resolved

    monkeypatch.setattr(harness.patch_service.filesystem, "resolve_existing_path", swap_to_symlink)

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert "safe regular file" in str(result.content["reason"])
    assert outside.read_text(encoding="utf-8") == "outside\n"
    assert harness.approval_service.get(str(approval["approval_id"])).status.value == "failed"


def test_patch_apply_denies_parent_directory_symlink_swap_before_replace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = make_patch_harness(tmp_path)
    nested = harness.workspace_root / "docs"
    nested.mkdir()
    nested.joinpath("README.md").write_text("old\n", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    proposal_result = harness.service.call_tool(
        tool_name="fs.patch.propose",
        arguments={
            "path": "docs/README.md",
            "unified_diff": "--- a/docs/README.md\n+++ b/docs/README.md\n@@ -1 +1 @@\n-old\n+new\n",
        },
        principal=principal(),
        session_id="sess_1",
    )
    assert proposal_result.status == "completed"
    proposal = proposal_result.content
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")

    import ithildin_api.patches as patches_module

    original_atomic_write = patches_module._atomic_write_text

    def swap_parent_to_symlink(
        workspace_root: Path,
        relative_path: str,
        content: str,
        *,
        expected_base_file_hash: str | None = None,
        max_verify_bytes: int | None = None,
    ) -> None:
        target = workspace_root / relative_path
        if target.parent.name == "docs":
            target.parent.rename(workspace_root / "docs-original")
            target.parent.symlink_to(outside)
        original_atomic_write(
            workspace_root,
            relative_path,
            content,
            expected_base_file_hash=expected_base_file_hash,
            max_verify_bytes=max_verify_bytes,
        )

    monkeypatch.setattr(patches_module, "_atomic_write_text", swap_parent_to_symlink)

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert "failed to apply patch safely" in str(result.content["reason"])
    assert outside.joinpath("README.md").exists() is False
    assert (harness.workspace_root / "docs-original/README.md").read_text(
        encoding="utf-8"
    ) == "old\n"


def test_patch_apply_denies_ancestor_directory_symlink_swap_before_replace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = make_patch_harness(tmp_path)
    nested = harness.workspace_root / "docs" / "nested"
    nested.mkdir(parents=True)
    nested.joinpath("README.md").write_text("old\n", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    proposal_result = harness.service.call_tool(
        tool_name="fs.patch.propose",
        arguments={
            "path": "docs/nested/README.md",
            "unified_diff": (
                "--- a/docs/nested/README.md\n"
                "+++ b/docs/nested/README.md\n"
                "@@ -1 +1 @@\n"
                "-old\n"
                "+new\n"
            ),
        },
        principal=principal(),
        session_id="sess_1",
    )
    assert proposal_result.status == "completed"
    proposal = proposal_result.content
    approval = request_patch_apply_approval(harness.service, cast(str, proposal["proposal_id"]))
    harness.approval_service.approve(str(approval["approval_id"]), decided_by="user:alice")

    import ithildin_api.patches as patches_module

    original_atomic_write = patches_module._atomic_write_text

    def swap_ancestor_to_symlink(
        workspace_root: Path,
        relative_path: str,
        content: str,
        *,
        expected_base_file_hash: str | None = None,
        max_verify_bytes: int | None = None,
    ) -> None:
        docs = workspace_root / "docs"
        docs.rename(workspace_root / "docs-original")
        docs.symlink_to(outside)
        original_atomic_write(
            workspace_root,
            relative_path,
            content,
            expected_base_file_hash=expected_base_file_hash,
            max_verify_bytes=max_verify_bytes,
        )

    monkeypatch.setattr(patches_module, "_atomic_write_text", swap_ancestor_to_symlink)

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"approval_id": approval["approval_id"]},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert "failed to apply patch safely" in str(result.content["reason"])
    assert outside.joinpath("nested/README.md").exists() is False
    assert (harness.workspace_root / "docs-original/nested/README.md").read_text(
        encoding="utf-8"
    ) == "old\n"


def test_http_fetch_audit_resource_redacts_query_string(tmp_path: Path) -> None:
    opener = FakeHttpOpener()
    service = make_http_service(tmp_path, opener=opener)

    result = service.call_tool(
        tool_name=HTTP_FETCH_TOOL,
        arguments={"url": "https://example.com/data?token=secret-value"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "completed"
    payloads = audit_payloads(tmp_path)
    audit_text = json.dumps(payloads)
    assert "secret-value" not in audit_text
    for payload in payloads:
        resource = payload.get("resource")
        if isinstance(resource, dict) and resource.get("type") == "network":
            assert resource["url"] == "https://example.com/data"


def test_malformed_http_fetch_audit_resource_omits_raw_query_string(tmp_path: Path) -> None:
    opener = FakeHttpOpener()
    service = make_http_service(tmp_path, opener=opener)

    result = service.call_tool(
        tool_name=HTTP_FETCH_TOOL,
        arguments={"url": " https://example.com/data?token=secret-value"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert opener.requests == []
    payloads = audit_payloads(tmp_path)
    audit_text = json.dumps(payloads)
    assert "secret-value" not in audit_text
    for payload in payloads:
        resource = payload.get("resource")
        if isinstance(resource, dict) and resource.get("type") == "network":
            assert "url" not in resource
            assert str(resource["raw_url_hash"]).startswith("sha256:")


def test_direct_patch_payload_cannot_be_applied(tmp_path: Path) -> None:
    harness = make_patch_harness(tmp_path)

    result = harness.service.call_tool(
        tool_name="fs.patch.apply",
        arguments={
            "proposal_id": "patch_123",
            "unified_diff": "--- a/README.md\n+++ b/README.md\n",
        },
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    assert result.content == {"reason": "invalid tool arguments"}


def test_write_call_creates_approval_required_response(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    result = service.call_tool(
        tool_name="fs.apply_patch",
        arguments={"path": "app.py"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "approval_required"
    approval_id = result.content["approval_id"]
    assert isinstance(approval_id, str)
    assert approval_id.startswith("appr_")
    payloads = audit_payloads(tmp_path)
    assert [payload["event_type"] for payload in payloads] == [
        "policy.evaluated",
        "approval.created",
    ]


def test_denied_policy_decision_is_audited(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    result = service.call_tool(
        tool_name="shell.run",
        arguments={"command": "echo nope"},
        principal=principal(),
        session_id="sess_1",
    )

    assert result.status == "denied"
    metadata = cast(JsonObject, audit_payloads(tmp_path)[0]["metadata"])
    assert metadata["reason"] == "shell denied"


def propose_patch(service: GovernedToolCallService) -> JsonObject:
    result = service.call_tool(
        tool_name="fs.patch.propose",
        arguments={
            "path": "README.md",
            "unified_diff": "--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-old\n+new\n",
        },
        principal=principal(),
        session_id="sess_1",
    )
    assert result.status == "completed"
    return result.content


def request_patch_apply_approval(
    service: GovernedToolCallService,
    proposal_id: str,
) -> JsonObject:
    result = service.call_tool(
        tool_name="fs.patch.apply",
        arguments={"proposal_id": proposal_id},
        principal=principal(),
        session_id="sess_1",
    )
    assert result.status == "approval_required"
    return result.content


def _mutate_approval_scope(
    db_path: Path,
    approval_id: str,
    key: str,
    replacement: object,
) -> None:
    with sqlite3.connect(db_path) as connection:
        raw_scope = connection.execute(
            "SELECT one_time_scope_json FROM approvals WHERE approval_id = ?",
            (approval_id,),
        ).fetchone()[0]
        scope = json.loads(str(raw_scope))
        scope[key] = replacement
        connection.execute(
            "UPDATE approvals SET one_time_scope_json = ? WHERE approval_id = ?",
            (canonical_json(scope), approval_id),
        )
        connection.commit()

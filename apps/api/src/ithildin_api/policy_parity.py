"""Policy preview/runtime parity harness."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any, cast
from urllib.request import Request

import yaml
from ithildin_audit_core import AuditWriter
from ithildin_policy_core import PolicyEvaluator
from ithildin_schemas import AuditEventType, JsonObject, PolicyDecisionValue
from ithildin_schemas.models import StrictBaseModel
from pydantic import Field, ValidationError

from ithildin_api.approvals import ApprovalService, ApprovalStore
from ithildin_api.http_tools import HttpAllowlist, HttpFetchExecutor, ParsedHttpUrl
from ithildin_api.identity import PrincipalRegistry
from ithildin_api.patches import PatchProposalService, PatchProposalStore
from ithildin_api.policy_preview import PolicyPreviewService
from ithildin_api.read_tools import ReadToolExecutor
from ithildin_api.registry import ToolRegistry
from ithildin_api.tool_calls import GovernedToolCallService
from ithildin_api.yaml_utils import safe_load_no_duplicate_keys

DEFAULT_POLICY_PARITY_TESTS_PATH = Path("policies/tests/parity.yaml")
PARITY_EVIDENCE_KEYS = (
    "decision",
    "reason",
    "policy_engine",
    "policy_hash",
    "policy_version",
    "policy_document_version",
    "matched_rules",
    "obligation_keys",
    "tool_name",
    "tool_version",
    "tool_risk",
    "manifest_hash",
    "resource_type",
    "resource_in_scope",
    "principal_id",
    "principal_roles",
    "session_id",
)


class PolicyParityError(RuntimeError):
    """Raised when policy parity fixtures cannot be loaded or evaluated."""


class PolicyParityCase(StrictBaseModel):
    id: str
    description: str | None = None
    tool_name: str
    arguments: JsonObject = Field(default_factory=dict)
    principal: JsonObject
    session_id: str
    expect_decision: PolicyDecisionValue | None = None
    expect_policy_evidence: bool = True
    expect_valid_arguments: bool | None = None
    expect_runtime_status: str | None = None
    expect_resource_type: str | None = None
    expect_resource_in_scope: bool | None = None


class PolicyParityDocument(StrictBaseModel):
    version: str
    cases: list[PolicyParityCase]


@dataclass(frozen=True)
class PolicyParityCaseResult:
    id: str
    passed: bool
    failures: list[str]
    preview_decision: str | None
    runtime_decision: str | None
    request_id: str | None

    def as_dict(self) -> JsonObject:
        return cast(
            JsonObject,
            {
                "id": self.id,
                "passed": self.passed,
                "failures": self.failures,
                "preview_decision": self.preview_decision,
                "runtime_decision": self.runtime_decision,
                "request_id": self.request_id,
            },
        )


@dataclass(frozen=True)
class PolicyParityRun:
    version: str
    tests_path: Path
    cases: list[PolicyParityCaseResult]

    @property
    def passed(self) -> int:
        return sum(1 for result in self.cases if result.passed)

    @property
    def failed(self) -> int:
        return len(self.cases) - self.passed

    def as_dict(self) -> JsonObject:
        return {
            "version": self.version,
            "tests_path": self.tests_path.as_posix(),
            "passed": self.passed,
            "failed": self.failed,
            "cases": [result.as_dict() for result in self.cases],
        }


def run_policy_parity(
    *,
    repo_root: Path,
    work_dir: Path,
    tests_path: Path = DEFAULT_POLICY_PARITY_TESTS_PATH,
    http_allowlist: str = "https://example.com",
) -> PolicyParityRun:
    document = load_policy_parity_tests(repo_root / tests_path)
    harness = _PolicyParityHarness(
        repo_root=repo_root,
        work_dir=work_dir,
        http_allowlist=http_allowlist,
    )
    return PolicyParityRun(
        version=document.version,
        tests_path=tests_path,
        cases=[harness.run_case(case) for case in document.cases],
    )


def load_policy_parity_tests(tests_path: Path) -> PolicyParityDocument:
    try:
        raw_tests = safe_load_no_duplicate_keys(tests_path)
    except FileNotFoundError as exc:
        raise PolicyParityError(f"policy parity tests file not found: {tests_path}") from exc
    except yaml.YAMLError as exc:
        raise PolicyParityError(f"invalid policy parity YAML: {tests_path}") from exc

    if not isinstance(raw_tests, dict):
        raise PolicyParityError(f"policy parity tests must be a mapping: {tests_path}")
    try:
        document = PolicyParityDocument.model_validate(_json_object(raw_tests))
    except ValidationError as exc:
        raise PolicyParityError(f"invalid policy parity fixture schema: {tests_path}") from exc

    seen: set[str] = set()
    for case in document.cases:
        if case.id in seen:
            raise PolicyParityError(f"duplicate policy parity case id: {case.id}")
        seen.add(case.id)
    return document


class _PolicyParityHarness:
    def __init__(self, *, repo_root: Path, work_dir: Path, http_allowlist: str) -> None:
        work_dir.mkdir(parents=True, exist_ok=True)
        registry = ToolRegistry.load(repo_root / "tool-manifests")
        policy_evaluator = PolicyEvaluator.load(repo_root / "policies/default.yaml")
        principal_registry = PrincipalRegistry.load(repo_root / "principals/local.yaml")
        audit_writer = AuditWriter(
            db_path=work_dir / "policy-parity.sqlite3",
            jsonl_path=work_dir / "policy-parity-audit.jsonl",
        )
        audit_writer.initialize()
        approval_store = ApprovalStore(work_dir / "policy-parity.sqlite3")
        approval_store.initialize()
        approval_service = ApprovalService(
            approval_store,
            audit_writer,
            default_expiry=timedelta(minutes=15),
        )
        http_fetch_executor = HttpFetchExecutor(
            allowlist=HttpAllowlist.from_csv(http_allowlist),
            timeout_seconds=1.0,
            max_response_bytes=1024,
            max_redirects=1,
            resolver=lambda host, port: ["93.184.216.34"],
            opener=_FixtureHttpOpener(),
        )
        workspace_root = work_dir / "workspace"
        workspace_root.mkdir(parents=True, exist_ok=True)
        workspace_root.joinpath("README.md").write_text(
            "policy parity fixture\n",
            encoding="utf-8",
        )
        read_tool_executor = ReadToolExecutor.from_settings(
            workspace_root=workspace_root,
            max_read_bytes=1024,
            search_result_limit=10,
            git_log_limit=5,
        )
        patch_store = PatchProposalStore(work_dir / "policy-parity.sqlite3")
        patch_store.initialize()
        patch_service = PatchProposalService(
            patch_store,
            read_tool_executor.filesystem,
            max_patch_bytes=2048,
            filesystems=read_tool_executor.filesystems,
            default_workspace_id=read_tool_executor.default_workspace_id,
        )
        self.patch_apply_proposal_id = patch_service.create_proposal(
            request_id="req_policy_parity_seed",
            principal={"id": "agent:mcp-local", "roles": ["AgentDeveloper"]},
            path="README.md",
            unified_diff=(
                "--- a/README.md\n"
                "+++ b/README.md\n"
                "@@ -1 +1 @@\n"
                "-policy parity fixture\n"
                "+policy parity fixture updated\n"
            ),
        ).proposal_id

        self.audit_writer = audit_writer
        self.preview_service = PolicyPreviewService(
            registry=registry,
            policy_evaluator=policy_evaluator,
            http_allowlist=http_fetch_executor.allowlist,
            principal_registry=principal_registry,
            read_tool_executor=read_tool_executor,
        )
        self.tool_call_service = GovernedToolCallService(
            registry=registry,
            policy_evaluator=policy_evaluator,
            approval_service=approval_service,
            audit_writer=audit_writer,
            http_fetch_executor=http_fetch_executor,
            read_tool_executor=read_tool_executor,
            patch_proposal_service=patch_service,
            principal_registry=principal_registry,
        )

    def run_case(self, case: PolicyParityCase) -> PolicyParityCaseResult:
        failures: list[str] = []
        arguments = self._case_arguments(case)
        preview = self.preview_service.preview(
            tool_name=case.tool_name,
            arguments=arguments,
            principal=case.principal,
            session_id=case.session_id,
        )
        runtime = self.tool_call_service.call_tool(
            tool_name=case.tool_name,
            arguments=arguments,
            principal=case.principal,
            session_id=case.session_id,
        )
        policy_event = self._policy_event(runtime.request_id)
        runtime_decision = _optional_string(policy_event.get("decision"))
        preview_decision = _optional_string(preview.get("decision"))

        if preview_decision != runtime_decision:
            failures.append(
                f"decision mismatch: preview={preview_decision}, runtime={runtime_decision}"
            )
        if case.expect_decision is not None and preview_decision != case.expect_decision.value:
            failures.append(
                f"expected {case.expect_decision.value}, got preview={preview_decision}"
            )
        if (
            case.expect_valid_arguments is not None
            and preview.get("valid_arguments") is not case.expect_valid_arguments
        ):
            failures.append(
                "valid_arguments mismatch: "
                f"expected={case.expect_valid_arguments}, "
                f"preview={preview.get('valid_arguments')!r}"
            )
        if case.expect_runtime_status is not None and runtime.status != case.expect_runtime_status:
            failures.append(
                f"runtime status mismatch: expected={case.expect_runtime_status}, "
                f"runtime={runtime.status}"
            )
        preview_resource = _json_object_or_none(preview.get("resource"))
        if case.expect_resource_type is not None:
            observed_type = preview_resource.get("type") if preview_resource is not None else None
            if observed_type != case.expect_resource_type:
                failures.append(
                    f"resource type mismatch: expected={case.expect_resource_type}, "
                    f"preview={observed_type!r}"
                )
        if case.expect_resource_in_scope is not None:
            observed_scope = (
                preview_resource.get("in_scope") if preview_resource is not None else None
            )
            if observed_scope is not case.expect_resource_in_scope:
                failures.append(
                    "resource in_scope mismatch: "
                    f"expected={case.expect_resource_in_scope}, preview={observed_scope!r}"
                )

        preview_evidence = _json_object_or_none(preview.get("decision_evidence"))
        runtime_evidence = _json_object_or_none(policy_event.get("metadata"))
        if case.expect_policy_evidence:
            if preview_evidence is None:
                failures.append("preview did not include decision_evidence")
            if runtime_evidence is None:
                failures.append("runtime audit event did not include decision evidence metadata")
        elif preview_evidence is not None:
            failures.append("preview unexpectedly included decision_evidence")

        if (
            case.expect_policy_evidence
            and preview_evidence is not None
            and runtime_evidence is not None
        ):
            for key in PARITY_EVIDENCE_KEYS:
                if preview_evidence.get(key) != runtime_evidence.get(key):
                    failures.append(
                        "evidence mismatch for "
                        f"{key}: preview={preview_evidence.get(key)!r}, "
                        f"runtime={runtime_evidence.get(key)!r}"
                    )

        return PolicyParityCaseResult(
            id=case.id,
            passed=not failures,
            failures=failures,
            preview_decision=preview_decision,
            runtime_decision=runtime_decision,
            request_id=runtime.request_id,
        )

    def _case_arguments(self, case: PolicyParityCase) -> JsonObject:
        arguments = dict(case.arguments)
        if (
            case.tool_name == "fs.patch.apply"
            and arguments.get("proposal_id") == "patch_abc"
        ):
            arguments["proposal_id"] = self.patch_apply_proposal_id
        return arguments

    def _policy_event(self, request_id: str) -> JsonObject:
        events = self.audit_writer.list_events(
            limit=10,
            event_type=AuditEventType.POLICY_EVALUATED.value,
            request_id=request_id,
        )
        if len(events) != 1:
            raise PolicyParityError(
                f"expected exactly one policy.evaluated event for {request_id}, got {len(events)}"
            )
        return events[0]


class _FixtureHttpResponse:
    code = 200
    headers = {"Content-Type": "text/plain; charset=utf-8"}

    def read(self, size: int) -> bytes:
        return b"policy parity fixture"[:size]

    def getcode(self) -> int:
        return self.code


class _FixtureHttpOpener:
    def open_pinned(
        self,
        fullurl: Request,
        *,
        parsed_url: ParsedHttpUrl,
        resolved_ips: Sequence[str],
        timeout: float,
    ) -> _FixtureHttpResponse:
        return _FixtureHttpResponse()

    def open(self, fullurl: Request, timeout: float = 0) -> _FixtureHttpResponse:
        return _FixtureHttpResponse()


def _json_object(value: dict[Any, Any]) -> JsonObject:
    result: JsonObject = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise PolicyParityError("policy parity keys must be strings")
        result[key] = item
    return result


def _json_object_or_none(value: object) -> JsonObject | None:
    return cast(JsonObject, value) if isinstance(value, dict) else None


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None

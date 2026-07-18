"""Run the local Ithildin demo flow against a running Compose stack."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ithildin_mcp_server.server import create_adapter

JsonObject = dict[str, Any]

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_TOKEN = "dev-admin-token-change-me"
DEFAULT_RESULT_OUTPUT = Path("var/review-packets/v3/operator-workbench/DEMO_FLOW_RESULT.md")
DEMO_PATH = "demo/README.md"
REDACTION_CHECK_PATH = "demo/redaction-check.txt"
REDACTION_SECRET = "demo-secret-token"
DEMO_SCENARIO = "guided_local_demo"
DEMO_STEP = "mediated_patch_flow"
PATCH_FIND = "This workspace is intentionally small and safe to mutate during local demos."
PATCH_REPLACE = (
    "This workspace is intentionally small, visible, and safe to mutate during local demos."
)


class DemoFlowError(RuntimeError):
    """Raised when the demo flow cannot finish safely."""


@dataclass(frozen=True)
class DemoGovernedFlowResult:
    proposal_id: str
    approval_id: str
    patched_path: str


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=_default_env_file())
    parser.add_argument("--api-base-url", default=DEFAULT_API_BASE_URL)
    parser.add_argument("--result-output", type=Path, default=DEFAULT_RESULT_OUTPUT)
    args = parser.parse_args()

    env = _load_env_file(Path(args.env_file))
    _apply_env_defaults(env)
    token = env.get("ITHILDIN_ADMIN_TOKEN") or os.environ.get("ITHILDIN_ADMIN_TOKEN", DEFAULT_TOKEN)
    api = ApiClient(args.api_base_url, token)

    print("Checking API health...")
    health = api.get("/healthz")
    _expect(health.get("status") == "ok", "API health check failed")

    print("Checking registered tools...")
    tools = api.get("/tools")
    tool_names = [tool["name"] for tool in tools.get("tools", [])]
    _expect("fs.list" in tool_names, "fs.list is not registered")
    _expect("fs.patch.apply" in tool_names, "fs.patch.apply is not registered")
    _expect("http.fetch" in tool_names, "http.fetch is not registered")

    print("Previewing policy...")
    preview = api.post("/policy/preview", {"tool_name": "fs.list", "arguments": {}})
    _expect(preview.get("decision") == "allow", "fs.list preview was not allowed")
    http_preview = api.post(
        "/policy/preview",
        {"tool_name": "http.fetch", "arguments": {"url": "https://example.com/"}},
    )
    _expect(http_preview.get("valid_arguments") is True, "http.fetch preview arguments invalid")
    _expect(
        http_preview.get("decision") in {"allow", "deny"},
        "http.fetch preview did not produce a safe policy decision",
    )
    http_resource = http_preview.get("resource")
    _expect(
        isinstance(http_resource, dict) and http_resource.get("type") == "network",
        "http.fetch preview did not produce a network resource",
    )

    print("Checking approvals list...")
    approvals = api.get("/approvals?status=pending")
    _expect("approvals" in approvals, "approvals endpoint did not return approvals")

    print("Calling governed tools through the MCP adapter...")
    flow_result = asyncio.run(_run_governed_tool_flow(api))

    print("Verifying audit chain...")
    verification = api.get("/audit-events/verify")
    _expect(verification.get("valid") is True, "audit chain verification failed")
    _expect(int(verification.get("event_count", 0)) > 0, "demo flow did not write audit events")

    print("Checking audit export...")
    export_text = api.get_text("/audit-events/export")
    first_line = export_text.splitlines()[0]
    metadata = json.loads(first_line)["metadata"]
    _expect(metadata["verification"]["valid"] is True, "audit export verification failed")

    candidate_runs = _candidate_demo_runs(api)
    _write_result_summary(
        output=args.result_output,
        flow_result=flow_result,
        audit_verification=verification,
        export_metadata=metadata,
        candidate_runs=candidate_runs,
    )

    print("Demo flow passed.")
    print(f"Wrote demo flow result summary: {args.result_output}")


async def _run_governed_tool_flow(api: ApiClient) -> DemoGovernedFlowResult:
    adapter = create_adapter()

    read_result = await adapter.call_tool("fs.read", {"path": DEMO_PATH})
    _expect(not read_result.isError, "fs.read returned an error")
    read_content = _structured_content(read_result.structuredContent, "fs.read")
    _expect(read_content.get("status") == "completed", "fs.read did not complete")

    workspace_root = Path(os.environ.get("ITHILDIN_WORKSPACE_ROOT", "workspaces"))
    redaction_file = workspace_root / REDACTION_CHECK_PATH
    redaction_file.write_text(f"TOKEN={REDACTION_SECRET}\nvisible\n", encoding="utf-8")
    redaction_result = await adapter.call_tool("fs.read", {"path": REDACTION_CHECK_PATH})
    _expect(not redaction_result.isError, "redaction fs.read returned an error")
    redaction_content = _structured_content(redaction_result.structuredContent, "redaction fs.read")
    rendered_redaction = json.dumps(redaction_content, sort_keys=True)
    _expect(REDACTION_SECRET not in rendered_redaction, "structured content leaked demo secret")
    _expect("[REDACTED]" in rendered_redaction, "structured content did not show redaction")
    _expect(REDACTION_SECRET not in _text_content(redaction_result), "MCP text leaked demo secret")

    demo_file = workspace_root / DEMO_PATH
    current_text = demo_file.read_text(encoding="utf-8")
    _expect(PATCH_FIND in current_text, "demo workspace is not in its expected seeded state")
    patched_text = current_text.replace(PATCH_FIND, PATCH_REPLACE, 1)
    unified_diff = _unified_diff(DEMO_PATH, current_text, patched_text)

    propose_result = await adapter.call_tool(
        "fs.patch.propose",
        {"path": DEMO_PATH, "unified_diff": unified_diff},
    )
    _expect(not propose_result.isError, "fs.patch.propose returned an error")
    propose_content = _structured_content(propose_result.structuredContent, "fs.patch.propose")
    proposal_id = str(propose_content.get("proposal_id", ""))
    _expect(proposal_id.startswith("patch_"), "patch proposal was not created")

    approval_request = await adapter.call_tool("fs.patch.apply", {"proposal_id": proposal_id})
    _expect(not approval_request.isError, "fs.patch.apply proposal request returned an error")
    approval_content = _structured_content(approval_request.structuredContent, "fs.patch.apply")
    approval_id = str(approval_content.get("approval_id", ""))
    _expect(approval_id.startswith("appr_"), "approval was not created")

    approved = api.post(
        f"/approvals/{approval_id}/approve",
        {
            "decision": "approve",
            "reason": "local deployment demo",
        },
    )
    _expect(approved.get("status") == "approved", "approval was not approved")

    apply_result = await adapter.call_tool("fs.patch.apply", {"approval_id": approval_id})
    _expect(not apply_result.isError, "approved patch apply returned an error")
    apply_content = _structured_content(apply_result.structuredContent, "approved fs.patch.apply")
    _expect(apply_content.get("status") == "completed", "patch did not apply")
    _expect(PATCH_REPLACE in demo_file.read_text(encoding="utf-8"), "patch output was not written")
    return DemoGovernedFlowResult(
        proposal_id=proposal_id,
        approval_id=approval_id,
        patched_path=DEMO_PATH,
    )


def _candidate_demo_runs(api: ApiClient) -> list[JsonObject]:
    try:
        payload = api.get("/runs?limit=5&session_id=mcp-stdio")
    except DemoFlowError:
        return []
    runs = payload.get("runs")
    if not isinstance(runs, list):
        return []
    return [run for run in runs if isinstance(run, dict)]


def _write_result_summary(
    *,
    output: Path,
    flow_result: DemoGovernedFlowResult,
    audit_verification: JsonObject,
    export_metadata: JsonObject,
    candidate_runs: list[JsonObject],
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(UTC).isoformat()
    candidate_run_ids = [
        str(run["run_id"])
        for run in candidate_runs
        if isinstance(run.get("run_id"), str)
    ]
    candidate_run_summary = ", ".join(candidate_run_ids) if candidate_run_ids else "unavailable"
    lines = [
        "# Demo Flow Result",
        "",
        "Generated by `make demo-flow`. This secret-free result summary records the",
        "observed local demo flow outputs without file contents, unified diffs, response",
        "bodies, secrets, or raw sensitive paths.",
        "",
        "## Demo Labels",
        "",
        f"- scenario: `{DEMO_SCENARIO}`",
        f"- demo_step: `{DEMO_STEP}`",
        "- operator_note: `local operator workbench demo`",
        "",
        "## Result",
        "",
        f"- generated_at: `{generated_at}`",
        f"- proposal_id: `{flow_result.proposal_id}`",
        f"- approval_id: `{flow_result.approval_id}`",
        f"- patched_file_path: `{flow_result.patched_path}`",
        "- patch_apply_status: `completed`",
        f"- candidate_run_ids: `{candidate_run_summary}`",
        f"- audit_verification_valid: `{str(audit_verification.get('valid')).lower()}`",
        f"- audit_event_count: `{audit_verification.get('event_count')}`",
        f"- audit_head_hash: `{audit_verification.get('head_hash')}`",
        f"- audit_export_event_count: `{export_metadata.get('event_count')}`",
        f"- audit_export_head_hash: `{export_metadata.get('head_hash')}`",
        "",
        "## Evidence Pointers",
        "",
        "- JSONL audit export: `GET /audit-events/export`",
        "- Run evidence export: review console `Export Run Evidence` for the selected run",
        "- Workbench packet: `var/review-packets/v3/operator-workbench/`",
        "- Demo reset guide: `var/review-packets/v3/operator-workbench/DEMO_RESET_GUIDE.md`",
        "",
        "## Cleanup And Reset",
        "",
        "1. Run `make compose-down` if the local stack was started.",
        "2. Run `make demo-seed` before the next demo to restore the ignored demo workspace.",
        "3. Run `make demo-reset-guide` for non-mutating reset and recovery guidance.",
        "4. Run `make demo-workbench` to refresh evidence packets after a completed demo.",
        "",
        "## Boundary",
        "",
        "This result does not prove OS isolation, SIEM custody, compliance automation,",
        "production security, host compromise resistance, external notarization, or",
        "activity outside Ithildin-mediated actions.",
        "",
    ]
    output.write_text("\n".join(lines), encoding="utf-8")


def _structured_content(value: JsonObject | None, tool_name: str) -> JsonObject:
    _expect(value is not None, f"{tool_name} did not return structured content")
    assert value is not None
    return value


def _text_content(result: object) -> str:
    content = getattr(result, "content", [])
    if not content:
        return ""
    first = content[0]
    text = getattr(first, "text", "")
    return str(text)


def _unified_diff(path: str, before: str, after: str) -> str:
    import difflib

    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )


class ApiClient:
    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    def get(self, path: str) -> JsonObject:
        return cast(JsonObject, json.loads(self.get_text(path)))

    def get_text(self, path: str) -> str:
        request = Request(
            f"{self.base_url}{path}",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        return _read_response(request)

    def post(self, path: str, payload: JsonObject) -> JsonObject:
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        return cast(JsonObject, json.loads(_read_response(request)))


def _read_response(request: Request) -> str:
    try:
        with urlopen(request, timeout=10) as response:
            return cast(str, response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise DemoFlowError(f"{request.full_url} returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise DemoFlowError(f"{request.full_url} is unavailable: {exc.reason}") from exc


def _default_env_file() -> str:
    return ".env" if Path(".env").exists() else ".env.example"


def _load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _apply_env_defaults(values: Mapping[str, str]) -> None:
    defaults = {
        "ITHILDIN_ADMIN_TOKEN": DEFAULT_TOKEN,
        "ITHILDIN_DB_PATH": "var/db/ithildin.sqlite3",
        "ITHILDIN_AUDIT_LOG_PATH": "var/logs/audit.jsonl",
        "ITHILDIN_MANIFEST_DIR": "tool-manifests",
        "ITHILDIN_POLICY_PATH": "policies/default.yaml",
        "ITHILDIN_WORKSPACE_ROOT": "workspaces",
    }
    for key, value in {**defaults, **values}.items():
        os.environ.setdefault(key, value)


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise DemoFlowError(message)


if __name__ == "__main__":
    main()

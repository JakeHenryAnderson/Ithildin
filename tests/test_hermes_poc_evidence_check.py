from collections.abc import Mapping

from scripts.hermes_poc_evidence_check import evaluate_runtime_evidence


def test_runtime_evidence_requires_bound_execution_and_replay_denial() -> None:
    approval_id = "appr_123"
    principal = {"principal_id": "agent:mcp-local", "session_id": "mcp-stdio"}
    events = [
        _event("policy.evaluated", "fs.list", decision="allow", metadata=principal),
        _event("tool.execution.completed", "fs.list", metadata=principal),
        _event("policy.evaluated", "fs.read", decision="allow", metadata=principal),
        _event("tool.execution.completed", "fs.read", metadata=principal),
        _event(
            "policy.evaluated",
            "fs.read",
            decision="deny",
            metadata={**principal, "reason": "path traversal is outside the workspace scope"},
        ),
        _event(
            "policy.evaluated",
            "http.fetch",
            decision="deny",
            request_id="req_http",
            metadata=principal,
        ),
        _event(
            "policy.evaluated",
            "sandbox.artifact.write_text",
            decision="require_approval",
            metadata=principal,
        ),
        _event(
            "approval.created",
            "sandbox.artifact.write_text",
            metadata={**principal, "approval_id": approval_id},
        ),
        _event(
            "tool.execution.completed",
            "sandbox.artifact.write_text",
            metadata={
                **principal,
                "approval_id": approval_id,
                "approval_binding_verified": True,
                "artifact_label": "sandbox://local-demo-sandbox/output/case-001-artifact.txt",
                "content_sha256": (
                    "sha256:240eb53bd727b66255a6f71156a9a577"
                    "fd9b16c6a94d9fc0688a0c209aabde6d"
                ),
            },
        ),
        _event(
            "tool.execution.failed",
            "sandbox.artifact.write_text",
            metadata={**principal, "reason": "approval is not approved: executed"},
        ),
    ]
    events.extend(
        {
            **_event("tool.execution.completed", "fs.read", metadata=principal),
            "resource": {"path": f"soak/case-{index:03d}.md"},
        }
        for index in range(1, 26)
    )

    report = evaluate_runtime_evidence(
        events,
        approval_statuses={approval_id: "executed"},
        artifact_content="Synthetic operator summary: the out-of-scope access attempt was denied.",
    )

    assert all(value for value in report.values() if isinstance(value, bool))
    assert report["approval_ids"] == [approval_id]
    assert report["soak_unique_read_count"] == 25


def _event(
    event_type: str,
    tool_name: str,
    *,
    decision: str | None = None,
    request_id: str = "req_default",
    metadata: Mapping[str, object],
) -> dict[str, object]:
    return {
        "event_type": event_type,
        "tool_name": tool_name,
        "decision": decision,
        "request_id": request_id,
        "metadata": dict(metadata),
    }

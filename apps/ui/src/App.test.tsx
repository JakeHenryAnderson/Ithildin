import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

const API_BASE = "http://127.0.0.1:8000";

function systemStatus(overrides = {}) {
  return {
    status: "ok",
    service: "ithildin-api",
    tool_count: 1,
    manifest_lock: {
      required: true,
      path: "tool-manifests.lock.json",
      signature: {
        required: false,
        signature_path: "var/signatures/tool-manifests.lock.sig.json",
        public_key_configured: false,
        signature_configured: false,
        verified: false,
        key_id: null,
      },
    },
    policy: {
      engine: "yaml",
      document_version: "default-v1",
      policy_hash: "sha256:policyhash",
      rule_count: 6,
    },
    audit: {
      valid: true,
      event_count: 2,
      head_hash: "sha256:audithead",
    },
    agent_runs: {
      enabled: true,
      count: 1,
      status: "read_only_observability",
    },
    principals: { required: true, path: "principals/local.yaml", count: 2, enabled_count: 2 },
    workspaces: {
      required: true,
      path: "workspaces/local.yaml",
      default_workspace_id: "demo",
      count: 1,
      enabled_count: 1,
    },
    storage: {
      runtime_backend: "sqlite",
      runtime_enabled: true,
      postgres: { configured: false, runtime_enabled: false, readiness: "not_configured" },
    },
    telemetry: { enabled: false, service_name: "ithildin-api", exporters: [] },
    audit_signing: {
      algorithm: "ed25519",
      private_key_configured: true,
      public_key_configured: true,
      signed_export_available: true,
      key_id: "sha256:auditkey",
    },
    filesystem: {
      platform: { system: "Darwin", profile: "macos", release: "x", machine: "arm64" },
      python: { version: "3.12" },
      capabilities: {
        o_no_follow_available: true,
        symlink_supported: true,
        hardlink_supported: true,
        case_sensitive: false,
      },
      support: {
        status: "supported",
        local_preview_security_supported: true,
        reason: "supported",
      },
      probe: { uses_temporary_directory: true, touches_workspace: false },
    },
    redaction: {
      baseline_enabled: true,
      baseline_key_count: 1,
      baseline_pattern_count: 1,
      extra_key_count: 0,
      extra_pattern_count: 0,
    },
    security: {
      preview_label: "v0.1 local-preview",
      production_ready: false,
      dev_admin_token: { sample_token_active: false, explicitly_allowed: false },
      admin_token: {
        recommended_min_length: 32,
        length_ok: true,
        contains_whitespace: false,
        weak: false,
      },
      local_only: {
        api_host_publish: "127.0.0.1:8000",
        ui_host_publish: "127.0.0.1:5173",
        remote_mcp_enabled: false,
      },
      cors: {
        allow_credentials: false,
        allow_origins: ["http://127.0.0.1:5173"],
        wildcard_allowed: false,
      },
      warnings: [],
    },
    limits: {
      approval_expiry_seconds: 900,
      max_read_bytes: 131072,
      max_patch_bytes: 131072,
      search_result_limit: 50,
      git_log_limit: 20,
      http_allowlist_configured: false,
      http_timeout_seconds: 10,
      http_max_response_bytes: 131072,
      http_max_redirects: 3,
    },
    ...overrides,
  };
}

const approvalReview = {
  approval: {
    approval_id: "appr_123456789",
    request_id: "req_123456789",
    request_hash: "sha256:requesthash",
    principal: { id: "agent:mcp-local" },
    tool_name: "fs.patch.apply",
    resource: { path: "demo.txt" },
    status: "pending",
    summary: "Apply demo patch",
    expires_at: "2026-06-03T12:00:00Z",
    one_time_scope: {
      proposal_id: "patch_123456789",
      proposal_hash: "sha256:proposalhash",
      base_file_hash: "sha256:basehash",
      path: "demo.txt",
      workspace_id: "demo",
      tool_name: "fs.patch.apply",
      manifest_hash: "sha256:manifesthash",
      manifest_version: "1",
      tool_input_schema_hash: "sha256:schemahash",
      policy_engine: "yaml",
      policy_hash: "sha256:policyhash",
      policy_version: "default-v1",
      policy_document_version: "default-v1",
      matched_rules: ["require_approval_for_write"],
      requesting_principal: { id: "agent:mcp-local" },
      request_hash: "sha256:requesthash",
      expires_at: "2026-06-03T12:00:00Z",
    },
    metadata: {
      policy_reason: "write tools require approval",
      approval_scope_hash: "sha256:scopehash",
    },
  },
  review: {
    valid: true,
    checks: { proposal_hash: true, manifest_hash: true },
    reasons: [],
    proposal: { proposal_id: "patch_123456789" },
  },
};

function jsonResponse(payload: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
    ...init,
  });
}

function installFetchMock(status = systemStatus()) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const path = url.replace(API_BASE, "");
    if (path === "/system/status") return jsonResponse(status);
    if (path === "/tools") {
      return jsonResponse({
        tools: [
          {
            name: "fs.read",
            version: "1",
            title: "Read file",
            risk: "read",
            category: "filesystem",
            manifest_hash: "sha256:toolhash",
            mcp: { exposed: true },
          },
        ],
      });
    }
    if (path === "/approvals/review?status=pending") {
      return jsonResponse({ approvals: [approvalReview] });
    }
    if (path === "/patch-proposals") {
      return jsonResponse({
        patch_proposals: [
          {
            proposal_id: "patch_123456789",
            request_id: "req_123456789",
            workspace_id: "demo",
            path: "demo.txt",
            base_file_hash: "sha256:basehash",
            proposal_hash: "sha256:proposalhash",
            status: "proposed",
            created_at: "2026-06-03T12:00:00Z",
            updated_at: "2026-06-03T12:00:00Z",
            metadata: {},
          },
        ],
      });
    }
    if (path === "/patch-proposals/patch_123456789") {
      return jsonResponse({
        proposal_id: "patch_123456789",
        request_id: "req_123456789",
        workspace_id: "demo",
        path: "demo.txt",
        base_file_hash: "sha256:basehash",
        proposal_hash: "sha256:proposalhash",
        status: "proposed",
        created_at: "2026-06-03T12:00:00Z",
        updated_at: "2026-06-03T12:00:00Z",
        metadata: {},
        unified_diff: "--- a/demo.txt\n+++ b/demo.txt\n@@\n-old\n+new\n",
        review: { valid: true, checks: { base_file_hash: true }, reasons: [] },
      });
    }
    if (path === "/patch-apply-diagnostics") {
      return jsonResponse({ status: "clean", attempts: [], stuck_approvals: [], recommendations: [] });
    }
    if (path === "/runs?limit=25" || path.startsWith("/runs?limit=25&")) {
      return jsonResponse({
        runs: [
          {
            run_id: "run_123456789",
            principal_id: "agent:mcp-local",
            principal_type: "agent",
            principal_roles: ["AgentDeveloper"],
            workspace_id: "demo",
            session_id: "mcp-stdio",
            status: "active",
            tool_call_count: 2,
            created_at: "2026-06-03T12:00:00Z",
            updated_at: "2026-06-03T12:01:00Z",
            last_request_id: "req_123456789",
            policy_hash: "sha256:policyhash",
            last_tool_name: "fs.read",
            last_tool_manifest_hash: "sha256:toolhash",
            metadata: {},
          },
        ],
        summary: {
          returned: 1,
          filters: path.includes("principal_id")
            ? { principal_id: "agent:mcp-local", workspace_id: "demo", tool_name: "fs.read" }
            : {},
          workspaces: { demo: 1 },
          principals: { "agent:mcp-local": 1 },
          statuses: { active: 1 },
          tools: { "fs.read": 1 },
          latest_updated_at: "2026-06-03T12:01:00Z",
        },
      });
    }
    if (path === "/runs/run_123456789") {
      return jsonResponse({
        run: {
          run_id: "run_123456789",
          principal_id: "agent:mcp-local",
          principal_type: "agent",
          principal_roles: ["AgentDeveloper"],
          workspace_id: "demo",
          session_id: "mcp-stdio",
          status: "active",
          tool_call_count: 2,
          created_at: "2026-06-03T12:00:00Z",
          updated_at: "2026-06-03T12:01:00Z",
          last_request_id: "req_123456789",
          policy_hash: "sha256:policyhash",
          last_tool_name: "fs.read",
          last_tool_manifest_hash: "sha256:toolhash",
          metadata: {},
        },
        timeline: [
          {
            event_id: "evt_run_1",
            timestamp: "2026-06-03T12:00:00Z",
            event_type: "policy.evaluated",
            request_id: "req_123456789",
            tool_name: "fs.read",
            decision: "allow",
            event_hash: "sha256:runeventhash",
            resource: { path: "README.md" },
            metadata: { run_id: "run_123456789" },
          },
        ],
      });
    }
    if (path === "/runs/run_123456789/evidence-export") {
      return jsonResponse({
        schema_version: "1",
        export_id: "runev_123456789",
        exported_at: "2026-06-03T12:02:00Z",
        run: { run_id: "run_123456789" },
        summary: {
          principal_id: "agent:mcp-local",
          workspace_id: "demo",
          session_id: "mcp-stdio",
          status: "active",
          tool_call_count: 2,
          tools_used: ["fs.read"],
          decision_counts: { allow: 1 },
          approval_count: 0,
          patch_diagnostic_count: 0,
          audit_event_count: 1,
          warning_count: 1,
          latest_policy_hash: "sha256:policyhash",
          manifest_lock_hash: "sha256:toolhash",
        },
        timeline: [],
        approvals: [],
        patch_diagnostics: [],
        signed_export_references: [],
        evidence_hashes: { run_sha256: "sha256:runhash" },
        redaction_summary: { excluded_categories: ["prompts"] },
        warnings: [{ type: "signed_evidence_unavailable" }],
      });
    }
    if (path === "/audit-events?limit=100") {
      return jsonResponse({
        audit_events: [
          {
            event_id: "evt_123",
            timestamp: "2026-06-03T12:00:00Z",
            event_type: "tool.execution.completed",
            request_id: "req_123456789",
            tool_name: "fs.read",
            decision: "allow",
            event_hash: "sha256:eventhash",
            metadata: { redaction_count: 0 },
          },
        ],
      });
    }
    if (path === "/audit-events/verify") {
      return jsonResponse({
        valid: true,
        event_count: 1,
        first_timestamp: "2026-06-03T12:00:00Z",
        last_timestamp: "2026-06-03T12:00:00Z",
        head_hash: "sha256:audithead",
        failure: null,
      });
    }
    if (path === "/policy/preview") {
      return jsonResponse({
        tool_name: "fs.read",
        manifest_hash: "sha256:toolhash",
        manifest_risk: "read",
        manifest_version: "1",
        valid_arguments: true,
        argument_error: null,
        policy_input: {},
        resource: { path: "demo.txt" },
        decision: "allow",
        reason: "read allowed",
        policy_version: "default-v1",
        matched_rules: ["allow_read"],
        obligations: {},
      });
    }
    if (path === "/approvals/appr_123456789/approve" && init?.method === "POST") {
      return jsonResponse(approvalReview.approval);
    }
    if (path === "/approvals/appr_123456789/deny" && init?.method === "POST") {
      return jsonResponse(approvalReview.approval);
    }
    if (path === "/audit-events/export" || path === "/audit-events/export/signed") {
      return new Response("export", { status: 200 });
    }
    return jsonResponse({ detail: `Unhandled ${path}` }, { status: 404, statusText: "Not Found" });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function saveToken(user = userEvent.setup()) {
  render(<App />);
  await user.type(screen.getByLabelText("Admin token"), "local-token");
  await user.click(screen.getByRole("button", { name: /save/i }));
  await screen.findByText("System Trust");
  return user;
}

describe("Review console interactions", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.stubGlobal("URL", {
      createObjectURL: vi.fn(() => "blob:ithildin"),
      revokeObjectURL: vi.fn(),
    });
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: vi.fn() },
    });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    sessionStorage.clear();
  });

  it("stores the admin token and sends bearer auth for dashboard requests", async () => {
    const fetchMock = installFetchMock();
    await saveToken();

    expect(sessionStorage.getItem("ithildin.adminToken")).toBe("local-token");
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        `${API_BASE}/system/status`,
        expect.objectContaining({
          headers: expect.objectContaining({ Authorization: "Bearer local-token" }),
        }),
      );
    });
  });

  it("renders trust warnings, approval evidence, and approve/deny actions", async () => {
    const fetchMock = installFetchMock(
      systemStatus({
        security: {
          ...systemStatus().security,
          dev_admin_token: { sample_token_active: true, explicitly_allowed: true },
          admin_token: {
            ...systemStatus().security.admin_token,
            weak: true,
          },
        },
      }),
    );
    const user = await saveToken();

    expect(await screen.findByText(/sample admin token is active/)).toBeInTheDocument();
    expect(screen.getByText("Agent Runs")).toBeInTheDocument();
    expect(screen.getAllByText("agent:mcp-local").length).toBeGreaterThan(0);
    expect(screen.getByText("1 runs")).toBeInTheDocument();
    expect(screen.getByText("demo (1)")).toBeInTheDocument();
    expect(screen.getByText("Run Evidence")).toBeInTheDocument();
    expect(screen.getByText("2 tool calls")).toBeInTheDocument();
    expect(screen.getByText("1 audit events")).toBeInTheDocument();
    expect(screen.getByText("policy.evaluated")).toBeInTheDocument();
    expect(screen.getAllByText("allow").length).toBeGreaterThan(0);
    await user.click(screen.getByRole("button", { name: /Export Run Evidence/i }));
    expect(screen.getByText("Apply demo patch")).toBeInTheDocument();
    expect(screen.getByText("Binding Evidence")).toBeInTheDocument();
    expect(screen.getByText("Patch Artifact")).toBeInTheDocument();
    expect(screen.getByText("Policy Decision")).toBeInTheDocument();
    expect(screen.getByText("basehash")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Deny reason for appr_123456789"), "not today");
    await user.click(screen.getByRole("button", { name: /^Deny$/i }));
    await user.click(screen.getByRole("button", { name: /^Approve$/i }));

    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/runs/run_123456789/evidence-export`,
      expect.objectContaining({
        headers: { Authorization: "Bearer local-token" },
      }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/approvals/appr_123456789/deny`,
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/approvals/appr_123456789/approve`,
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("filters agent runs with a bounded authenticated query", async () => {
    const fetchMock = installFetchMock();
    const user = await saveToken();
    const runSection = screen.getByText("Agent Runs").closest("section")!;

    await user.type(within(runSection).getByLabelText("Principal"), "agent:mcp-local");
    await user.type(within(runSection).getByLabelText("Workspace"), "demo");
    await user.type(within(runSection).getByLabelText("Tool"), "fs.read");
    await user.click(within(runSection).getByRole("button", { name: /^Apply$/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        `${API_BASE}/runs?limit=25&principal_id=agent%3Amcp-local&workspace_id=demo&tool_name=fs.read`,
        expect.objectContaining({
          headers: expect.objectContaining({ Authorization: "Bearer local-token" }),
        }),
      );
    });
    expect(screen.getByText(/principal_id=agent:mcp-local/)).toBeInTheDocument();
  });

  it("handles signed export and invalid policy-preview JSON", async () => {
    const user = await saveToken();

    await user.click(screen.getByRole("button", { name: /Export Signed/i }));
    expect(fetch).toHaveBeenCalledWith(
      `${API_BASE}/audit-events/export/signed`,
      expect.objectContaining({
        headers: { Authorization: "Bearer local-token" },
      }),
    );

    const argumentsEditor = within(screen.getByText("Policy Preview").closest("section")!).getByText(
      "Arguments",
    ).parentElement!.querySelector("textarea")!;
    fireEvent.change(argumentsEditor, { target: { value: "[not-object]" } });
    await user.click(screen.getByRole("button", { name: /^Preview$/i }));

    expect(await screen.findByText(/Unexpected token/)).toBeInTheDocument();
  });
});

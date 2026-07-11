import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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

function deferredResponse() {
  let resolve!: (response: Response) => void;
  const promise = new Promise<Response>((next) => {
    resolve = next;
  });
  return { promise, resolve };
}

type FetchMockOptions = {
  approvalStatus?: "executed" | "pending";
  auditExportFailure?: boolean;
  decision?: "deny" | "require_approval";
  emptyRuns?: boolean;
  emptyTimeline?: boolean;
  invalidBinding?: boolean;
  noApprovals?: boolean;
  proposalStatus?: "applied" | "proposed";
};

function installFetchMock(status = systemStatus(), options: FetchMockOptions = {}) {
  const approvalForScenario = {
    ...approvalReview,
    approval: {
      ...approvalReview.approval,
      status: options.approvalStatus ?? approvalReview.approval.status,
    },
    review: {
      ...approvalReview.review,
      valid:
        options.proposalStatus === "applied" || options.invalidBinding
          ? false
          : approvalReview.review.valid,
    },
  };
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
          {
            name: "fs.patch.apply",
            version: "1",
            title: "Apply patch proposal",
            risk: "write",
            category: "filesystem",
            manifest_hash: "sha256:manifesthash",
            mcp: { exposed: true },
          },
        ],
      });
    }
    if (path === "/approvals/review?status=pending") {
      return jsonResponse({ approvals: options.noApprovals ? [] : [approvalForScenario] });
    }
    if (path === "/approvals") {
      return jsonResponse({
        approvals: options.noApprovals ? [] : [approvalForScenario.approval],
      });
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
            status: options.proposalStatus ?? "proposed",
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
        status: options.proposalStatus ?? "proposed",
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
      if (options.emptyRuns) {
        return jsonResponse({
          runs: [],
          summary: {
            returned: 0,
            filters: {},
            workspaces: {},
            principals: {},
            statuses: {},
            tools: {},
            latest_updated_at: null,
          },
        });
      }
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
            metadata: { scenario: "guided_local_demo", demo_step: "mediated_patch_flow" },
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
          metadata: { scenario: "guided_local_demo", demo_step: "mediated_patch_flow" },
        },
        timeline: options.emptyTimeline
          ? []
          : [
              {
                event_id: "evt_run_1",
                timestamp: "2026-06-03T12:00:00Z",
                event_type: "policy.evaluated",
                request_id: "req_read_123456789",
                tool_name: "fs.read",
                decision: "allow",
                event_hash: "sha256:runeventhash",
                resource: { path: "README.md" },
                metadata: { run_id: "run_123456789" },
              },
              {
                event_id: "evt_run_2",
                timestamp: "2026-06-03T12:01:00Z",
                event_type: "policy.evaluated",
                request_id: "req_123456789",
                tool_name: "fs.patch.apply",
                decision: options.decision ?? "require_approval",
                event_hash: "sha256:approvaleventhash",
                resource: { path: "demo.txt" },
                metadata: {
                  run_id: "run_123456789",
                  policy_reason:
                    options.decision === "deny"
                      ? "request is outside the permitted write policy"
                      : "write tools require approval",
                  matched_rules: [
                    options.decision === "deny"
                      ? "deny_unapproved_write_path"
                      : "require_approval_for_write",
                  ],
                },
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
            metadata: { redaction_count: 0, run_id: "run_123456789" },
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
      if (options.auditExportFailure) {
        return jsonResponse(
          { detail: "signed export unavailable" },
          { status: 409, statusText: "Conflict" },
        );
      }
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
  await screen.findByText("Authenticated local preview");
  return user;
}

describe("Review console interactions", () => {
  beforeEach(() => {
    sessionStorage.clear();
    Object.defineProperty(Element.prototype, "scrollIntoView", {
      configurable: true,
      value: vi.fn(),
    });
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

  it("orients a first-time operator and opens authoritative attention in Workbench", async () => {
    installFetchMock();
    const user = userEvent.setup();
    render(<App />);

    expect(
      screen.getByRole("heading", { name: "Ithildin Command Center" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Gateway remains the enforcement and audit authority/i),
    ).toBeInTheDocument();
    await user.tab();
    const skipLink = screen.getByRole("link", { name: "Skip to operator attention" });
    expect(skipLink).toHaveFocus();
    await user.click(skipLink);
    expect(document.getElementById("attention")).toHaveFocus();

    const navigation = screen.getByRole("navigation", {
      name: "Command Center sections",
    });
    for (const label of [
      "Attention",
      "Missions / Agent Runs",
      "Artifacts",
      "Approvals",
      "Evidence",
      "Administration",
      "Help",
    ]) {
      expect(within(navigation).getByRole("link", { name: label })).toBeInTheDocument();
    }
    expect(within(navigation).getByText("Sign-in required")).toBeInTheDocument();
    expect(
      screen.getByText(/Sign in with the local admin token to load operator attention records/i),
    ).toBeInTheDocument();

    await user.type(screen.getByLabelText("Admin token"), "local-token");
    await user.click(screen.getByRole("button", { name: /save/i }));

    const attention = await screen.findByRole("region", { name: "Attention" });
    expect(within(navigation).getByText("Authenticated local preview")).toBeInTheDocument();
    expect(within(attention).getByText("Guided local demo mission")).toBeInTheDocument();
    expect(within(attention).getByText("Apply demo patch")).toBeInTheDocument();
    expect(within(attention).getByText("Review decision")).toBeInTheDocument();
    expect(within(attention).getByText("demo")).toBeInTheDocument();
    expect(within(attention).getByText("agent:mcp-local")).toBeInTheDocument();
    expect(within(attention).getByText("write tools require approval")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Routine operations" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.queryByText("System Trust")).not.toBeInTheDocument();
    expect(screen.queryByText("Observed investigation filters")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Policy administration" }));
    expect(screen.getByText("Local System Posture")).toBeInTheDocument();
    expect(screen.getByText("Request Decision Preflight")).toBeInTheDocument();
    expect(screen.queryByText("Recent Audit Events")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Technical review" }));
    expect(screen.getByText("Audit Integrity")).toBeInTheDocument();
    expect(screen.getByText("Recent Audit Events")).toBeInTheDocument();
    expect(screen.queryByText("Request Decision Preflight")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Routine operations" }));

    await user.click(within(navigation).getByRole("link", { name: "Administration" }));
    await waitFor(() => {
      expect(document.getElementById("administration")).toHaveFocus();
    });
    expect(screen.getByText("Request Decision Preflight")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Routine operations" }));

    await user.click(
      within(attention).getByRole("button", { name: "Open mission Workbench" }),
    );
    await waitFor(() => {
      expect(document.getElementById("missions")).toHaveFocus();
    });
    expect(document.getElementById("missions")).not.toBeNull();
  });

  it("shows locked and empty Agent Run states without run controls", async () => {
    const user = userEvent.setup();
    const fetchMock = installFetchMock(systemStatus(), { emptyRuns: true });
    render(<App />);

    expect(screen.getAllByText("Locked.").length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: /abort/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /pause/i })).not.toBeInTheDocument();

    await user.type(screen.getByLabelText("Admin token"), "local-token");
    await user.click(screen.getByRole("button", { name: /save/i }));
    await screen.findByText(/No recorded agent runs. Run make demo-seed/);
    expect(screen.getByText(/Export appears after selecting a run/)).toBeInTheDocument();
    expect(screen.getByText("0 runs")).toBeInTheDocument();
    expect(screen.getByText("no statuses")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/runs?limit=25`,
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer local-token" }),
      }),
    );
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
    expect(screen.getByText("Demo Path")).toBeInTheDocument();
    expect(screen.getByText("Preflight")).toBeInTheDocument();
    expect(screen.getByText("Seed/run")).toBeInTheDocument();
    expect(screen.getByText("Cleanup")).toBeInTheDocument();
    expect(screen.getAllByText("agent:mcp-local").length).toBeGreaterThan(0);
    expect(screen.getByText("1 runs")).toBeInTheDocument();
    expect(screen.getByText("demo (1)")).toBeInTheDocument();
    expect(screen.getByText("Run Evidence")).toBeInTheDocument();
    expect(await screen.findByLabelText("Run evidence closeout")).toBeInTheDocument();
    expect(screen.getByText("Evidence closeout")).toBeInTheDocument();
    expect(screen.getByText("1 bundle warnings")).toBeInTheDocument();
    expect(
      screen.getByText("Verified for 1 currently loaded local audit events"),
    ).toBeInTheDocument();
    expect(screen.getByText("Run snapshot has no signed evidence reference")).toBeInTheDocument();
    expect(screen.getByText("Not exported in this browser session")).toBeInTheDocument();
    expect(screen.getByText(/Not host-compromise resistance/)).toBeInTheDocument();
    expect(screen.getAllByText("demo").length).toBeGreaterThan(0);
    expect(document.querySelector(".demo-label")).not.toBeNull();
    expect(screen.getByText("Evidence Types")).toBeInTheDocument();
    expect(screen.getByText("policy (2)")).toBeInTheDocument();
    expect(screen.getByText("Statuses")).toBeInTheDocument();
    expect(screen.getByText("Decisions")).toBeInTheDocument();
    expect(screen.getByText("Correlation")).toBeInTheDocument();
    expect(screen.getByText("Observed Reconstruction")).toBeInTheDocument();
    expect(screen.getByText("Tool Call")).toBeInTheDocument();
    expect(screen.getAllByText("Policy Decision").length).toBeGreaterThan(0);
    expect(screen.getByText("Audit/Export")).toBeInTheDocument();
    expect(screen.getByText("2 requests")).toBeInTheDocument();
    expect(screen.getByText("2 tool calls")).toBeInTheDocument();
    expect(screen.getByText("2 audit events")).toBeInTheDocument();
    expect(screen.getAllByText("policy.evaluated")).toHaveLength(2);
    expect(screen.getAllByText("allow").length).toBeGreaterThan(0);
    expect(screen.getByText("Governed request decision")).toBeInTheDocument();
    expect(screen.getByText("Approval required.")).toBeInTheDocument();
    expect(screen.getAllByText("write tools require approval").length).toBeGreaterThan(0);
    expect(
      screen.getByText("Review the matching pending approval and its exact one-time scope."),
    ).toBeInTheDocument();
    expect(screen.getByText(/Registration identifies the reviewed tool definition/)).toBeInTheDocument();
    const approvalArticle = screen.getByRole("article", {
      name: "Approval appr_123456789 for Apply demo patch",
    });
    expect(approvalArticle).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Open matching pending approval" }));
    await waitFor(() => expect(approvalArticle).toHaveFocus());
    const artifactRow = screen.getByRole("button", { name: /Artifact: demo\.txt/i });
    expect(within(artifactRow).getByLabelText("Artifact: demo.txt")).toHaveAttribute(
      "data-label",
      "Artifact",
    );
    expect(within(artifactRow).getByLabelText(/Requester:/)).toHaveAttribute(
      "data-label",
      "Requester",
    );
    await user.click(screen.getByRole("button", { name: /Export Run Evidence/i }));
    expect(await screen.findByText("Download initiated")).toBeInTheDocument();
    expect(screen.getByText(/save location, custody, receipt/)).toBeInTheDocument();
    expect(screen.getAllByText("Apply demo patch").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("Binding Evidence")).toBeInTheDocument();
    expect(screen.getByText("Patch Artifact")).toBeInTheDocument();
    expect(screen.getAllByText("Policy Decision").length).toBeGreaterThan(0);
    expect(screen.getAllByText("basehash").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Artifact proposal filters")).toBeInTheDocument();
    expect(screen.getByText("demo workspace")).toBeInTheDocument();
    expect(screen.getByLabelText("Selected artifact lifecycle")).toBeInTheDocument();
    expect(screen.getByText("Proposed change")).toBeInTheDocument();
    expect(screen.getByText("1 · Proposal")).toBeInTheDocument();
    expect(screen.getByText("2 · Approval")).toBeInTheDocument();
    expect(screen.getByText("3 · Application")).toBeInTheDocument();
    expect(screen.getByText("4 · Operator review")).toBeInTheDocument();
    expect(screen.getByText(/does not mean approved, applied, reviewed/)).toBeInTheDocument();

    await user.type(screen.getByLabelText("Deny reason for appr_123456789"), "not today");
    await user.click(screen.getByRole("button", { name: /^Deny$/i }));

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
    expect(fetchMock).not.toHaveBeenCalledWith(
      `${API_BASE}/approvals/appr_123456789/approve`,
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("shows a safe selected-run state when no correlated timeline exists", async () => {
    installFetchMock(systemStatus(), { emptyTimeline: true });
    await saveToken();

    expect(screen.getByText("Run Evidence")).toBeInTheDocument();
    expect(screen.getByText("0 audit events")).toBeInTheDocument();
    expect(
      screen.getByText(/Export Run Evidence still returns the safe run summary/i),
    ).toBeInTheDocument();
    expect(screen.queryByText("Evidence Types")).not.toBeInTheDocument();
  });

  it("distinguishes a recorded denial from an approval requirement", async () => {
    installFetchMock(systemStatus(), { decision: "deny", noApprovals: true });
    await saveToken();

    expect(screen.getByText("Denied.")).toBeInTheDocument();
    expect(
      screen.getByText("Gateway blocked the governed request. No governed execution should follow this decision."),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "No approval action is available for this denied request. Investigate or change the request through an authorized workflow.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText("Approval required.")).not.toBeInTheDocument();
  });

  it("keeps applied artifact state separate from operator review and promotion", async () => {
    installFetchMock(systemStatus(), {
      approvalStatus: "executed",
      proposalStatus: "applied",
    });
    const user = await saveToken();

    expect(screen.getByText("Applied change ready for operator review")).toBeInTheDocument();
    expect(screen.getByText("recorded applied")).toBeInTheDocument();
    expect(screen.getAllByText("not recorded").length).toBeGreaterThan(0);
    expect(
      screen.getByText(/does not mean reviewed, promoted, published, release-ready/),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Open matching pending approval" })).not.toBeInTheDocument();

    await user.type(screen.getByLabelText("Search artifacts"), "missing-artifact");
    expect(screen.getByText("No proposals match the current artifact filters.")).toBeInTheDocument();
    expect(screen.getByLabelText("Selected artifact lifecycle")).toBeInTheDocument();
  });

  it("keeps approval lifecycle separate from invalid binding evidence", async () => {
    installFetchMock(systemStatus(), { invalidBinding: true });
    await saveToken();

    expect(screen.getAllByText("pending").length).toBeGreaterThan(0);
    expect(screen.getAllByText("stale binding").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /^Approve$/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /^Deny$/i })).toBeDisabled();
  });

  it("filters agent runs with a bounded authenticated query", async () => {
    const fetchMock = installFetchMock();
    const user = await saveToken();
    await user.click(screen.getByRole("button", { name: "Investigation" }));
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
    expect(
      screen.getByRole("button", { name: "Identity: agent:mcp-local ×" }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Identity: agent:mcp-local ×" }));
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        `${API_BASE}/runs?limit=25&workspace_id=demo&tool_name=fs.read`,
        expect.anything(),
      );
    });
    expect(within(runSection).getByLabelText("Principal")).toHaveValue("");
    expect(screen.getByLabelText("Bounded investigation summary")).toBeInTheDocument();
    expect(screen.getByText("1 of 1 loaded runs shown")).toBeInTheDocument();

    fetchMock.mockClear();
    await user.type(within(runSection).getByLabelText("Status"), "active");
    await user.click(screen.getByRole("button", { name: "Refresh" }));
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        `${API_BASE}/runs?limit=25&workspace_id=demo&tool_name=fs.read`,
        expect.anything(),
      );
    });
    expect(fetchMock).not.toHaveBeenCalledWith(
      expect.stringContaining("status=active"),
      expect.anything(),
    );

    await user.selectOptions(within(runSection).getByLabelText("Observed decision"), "allow");
    expect(
      screen.getByRole("button", { name: "Observed decision: allow ×" }),
    ).toBeInTheDocument();

    await user.selectOptions(
      within(runSection).getByLabelText("Observed attention"),
      "attention",
    );
    expect(
      screen.getByText(/No loaded runs match the current bounded investigation filters/),
    ).toBeInTheDocument();
    expect(screen.getByText("0 of 1 loaded runs shown")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Clear all" }));
    expect(await screen.findByText("1 of 1 loaded runs shown")).toBeInTheDocument();
    expect(screen.queryByLabelText("Active run filters")).not.toBeInTheDocument();
  });

  it("handles signed export and invalid policy-preview JSON", async () => {
    const user = await saveToken();

    await user.click(screen.getByRole("button", { name: "Technical review" }));
    await user.click(screen.getByRole("button", { name: /Export Signed/i }));
    expect(fetch).toHaveBeenCalledWith(
      `${API_BASE}/audit-events/export/signed`,
      expect.objectContaining({
        headers: { Authorization: "Bearer local-token" },
      }),
    );

    await user.click(screen.getByRole("button", { name: "Policy administration" }));
    const argumentsEditor = within(
      screen.getByText("Request Decision Preflight").closest("section")!,
    )
      .getByText("Request details (JSON)")
      .parentElement!.querySelector("textarea")!;
    fireEvent.change(argumentsEditor, { target: { value: "[not-object]" } });
    await user.click(screen.getByRole("button", { name: /^Test decision$/i }));

    expect(await screen.findByText(/Unexpected token/)).toBeInTheDocument();
  });

  it("keeps export failure distinct from evidence and signing availability", async () => {
    installFetchMock(systemStatus(), { auditExportFailure: true });
    const user = await saveToken();

    await user.click(screen.getByRole("button", { name: "Technical review" }));
    await user.click(screen.getByRole("button", { name: /Export Signed/i }));

    expect(await screen.findByText(/Signed audit export: failed/)).toBeInTheDocument();
    expect(screen.getByText("Not exported in this browser session")).toBeInTheDocument();
    expect(screen.getAllByText("signed export unavailable").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Apply demo patch").length).toBeGreaterThan(0);
    expect(screen.getByText("Run snapshot has no signed evidence reference")).toBeInTheDocument();
  });

  it("does not restore a delayed policy preview after the authentication context changes", async () => {
    const fetchMock = installFetchMock();
    const initialImplementation = fetchMock.getMockImplementation()!;
    const delayed = deferredResponse();
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/policy/preview")) {
        return delayed.promise;
      }
      return initialImplementation(input, init);
    });
    const user = await saveToken();
    await user.click(screen.getByRole("button", { name: "Policy administration" }));
    await user.click(screen.getByRole("button", { name: /^Test decision$/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/policy/preview`,
      expect.anything(),
    ));

    const tokenInput = screen.getByLabelText("Admin token");
    await user.clear(tokenInput);
    await user.click(screen.getByRole("button", { name: /save/i }));
    await act(async () => {
      delayed.resolve(jsonResponse({
        tool_name: "fs.read",
        manifest_hash: "sha256:toolhash",
        manifest_risk: "read",
        manifest_version: "1",
        valid_arguments: true,
        argument_error: null,
        policy_input: {},
        resource: { path: "demo.txt" },
        decision: "allow",
        reason: "delayed result must not reappear",
        policy_version: "default-v1",
        matched_rules: ["allow_read"],
        obligations: {},
      }));
      await delayed.promise;
    });

    expect(screen.getByText("Admin token required.")).toBeInTheDocument();
    expect(screen.queryByText("delayed result must not reappear")).not.toBeInTheDocument();
  });

  it("does not restore delayed policy-impact results after the authentication context changes", async () => {
    const fetchMock = installFetchMock();
    const initialImplementation = fetchMock.getMockImplementation()!;
    const delayed = deferredResponse();
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/policy/impact-preview")) {
        return delayed.promise;
      }
      return initialImplementation(input, init);
    });
    const user = await saveToken();
    await user.click(screen.getByRole("button", { name: "Policy administration" }));
    await user.click(screen.getByRole("button", { name: /^Compare$/i }));
    const tokenInput = screen.getByLabelText("Admin token");
    await user.clear(tokenInput);
    await user.click(screen.getByRole("button", { name: /save/i }));
    await act(async () => {
      delayed.resolve(jsonResponse({
        current: { passed: 1, failed: 0, case_count: 1 },
        candidate: { policy_hash: "sha256:delayed", passed: 1, failed: 0, case_count: 1 },
        changed_cases: [{ id: "delayed-case", changes: ["decision"], current: {}, candidate: {} }],
      }));
      await delayed.promise;
    });

    expect(screen.getByText("Admin token required.")).toBeInTheDocument();
    expect(screen.queryByText("delayed-case")).not.toBeInTheDocument();
  });

  it("does not download a delayed run export after signing out", async () => {
    const fetchMock = installFetchMock();
    const initialImplementation = fetchMock.getMockImplementation()!;
    const delayed = deferredResponse();
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/runs/run_123456789/evidence-export")) {
        return delayed.promise;
      }
      return initialImplementation(input, init);
    });
    const user = await saveToken();
    await user.click(screen.getByRole("button", { name: /Export Run Evidence/i }));
    const tokenInput = screen.getByLabelText("Admin token");
    await user.clear(tokenInput);
    await user.click(screen.getByRole("button", { name: /save/i }));
    await act(async () => {
      delayed.resolve(jsonResponse({ schema_version: "1" }));
      await delayed.promise;
    });

    expect(HTMLAnchorElement.prototype.click).not.toHaveBeenCalled();
    expect(screen.queryByText("Download initiated")).not.toBeInTheDocument();
  });

  it("attributes run export failures to the selected run", async () => {
    const fetchMock = installFetchMock();
    const initialImplementation = fetchMock.getMockImplementation()!;
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/runs/run_123456789/evidence-export")) {
        return jsonResponse(
          { detail: "evidence unavailable" },
          { status: 503, statusText: "Unavailable" },
        );
      }
      return initialImplementation(input, init);
    });
    const user = await saveToken();

    await user.click(screen.getByRole("button", { name: /Export Run Evidence/i }));
    expect(
      (await screen.findAllByText(/Run run_123456789 export failed: evidence unavailable/)).length,
    ).toBeGreaterThan(0);
  });

  it("uses API history order for the latest non-pending proposal lifecycle", async () => {
    const fetchMock = installFetchMock();
    const initialImplementation = fetchMock.getMockImplementation()!;
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input).replace(API_BASE, "");
      if (path === "/approvals/review?status=pending") {
        return jsonResponse({ approvals: [] });
      }
      if (path === "/approvals") {
        return jsonResponse({ approvals: [
          {
            ...approvalReview.approval,
            status: "denied",
            updated_at: "2026-06-03T12:05:00Z",
            expires_at: "2026-06-03T12:06:00Z",
          },
          {
            ...approvalReview.approval,
            approval_id: "appr_older123",
            status: "executed",
            updated_at: "2026-06-03T12:04:00Z",
            expires_at: "2026-06-04T12:00:00Z",
          },
        ] });
      }
      return initialImplementation(input, init);
    });
    await saveToken();

    expect(screen.getAllByText("No approval action remains. Revise the change through an authorized workflow if needed.")).toHaveLength(2);
    expect(screen.getAllByText("denied").length).toBeGreaterThan(0);
  });

  it("uses recorded recovery evidence time in operator attention", async () => {
    const fetchMock = installFetchMock();
    const initialImplementation = fetchMock.getMockImplementation()!;
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input).replace(API_BASE, "");
      if (path === "/approvals/review?status=pending" || path === "/approvals") {
        return jsonResponse({ approvals: [] });
      }
      if (path === "/patch-proposals") {
        return jsonResponse({ patch_proposals: [] });
      }
      if (path === "/patch-apply-diagnostics") {
        return jsonResponse({
          status: "recovery_required",
          attempts: [{ updated_at: "2026-06-03T12:05:00Z" }],
          stuck_approvals: [],
          recommendations: [],
        });
      }
      return initialImplementation(input, init);
    });
    await saveToken();

    const attention = screen.getByRole("region", { name: "Attention" });
    expect(within(attention).getByText("Patch recovery review required")).toBeInTheDocument();
    expect(within(attention).getByText(/6\/3\/26/)).toBeInTheDocument();
  });

  it("fails closed when a replacement token is rejected", async () => {
    const fetchMock = installFetchMock();
    const user = await saveToken();

    fetchMock.mockImplementation(async () =>
      jsonResponse({ detail: "Admin token rejected." }, { status: 401 }),
    );
    const tokenInput = screen.getByLabelText("Admin token");
    await user.clear(tokenInput);
    await user.type(tokenInput, "rejected-token");
    await user.click(screen.getByRole("button", { name: /save/i }));

    expect(await screen.findByText("Dashboard data is locked until a valid local admin token is saved.")).toBeInTheDocument();
    expect(screen.queryByText("Authenticated local preview")).not.toBeInTheDocument();
    expect(screen.queryByText("Apply demo patch")).not.toBeInTheDocument();
    expect(screen.getByText("Pending approval data is unavailable.")).toBeInTheDocument();
  });

  it("does not retain authority records after a partial refresh failure", async () => {
    const fetchMock = installFetchMock();
    const user = await saveToken();
    const initialImplementation = fetchMock.getMockImplementation()!;
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/tools")) {
        return jsonResponse({ detail: "tool inventory unavailable" }, { status: 503 });
      }
      return initialImplementation(input, init);
    });

    await user.click(screen.getByRole("button", { name: "Refresh" }));

    expect(await screen.findByText("tool inventory unavailable")).toBeInTheDocument();
    expect(screen.queryByText("Apply demo patch")).not.toBeInTheDocument();
    expect(screen.getByText("Operator attention records are unavailable. No empty-state conclusion is available.")).toBeInTheDocument();

    fetchMock.mockImplementation(initialImplementation);
    await user.click(screen.getByRole("button", { name: "Refresh" }));
    expect(await screen.findByText("Authenticated local preview")).toBeInTheDocument();
    expect(screen.getAllByText("Apply demo patch").length).toBeGreaterThan(0);
  });

  it("ignores an out-of-order proposal detail response after selection changes", async () => {
    const fetchMock = installFetchMock();
    const initialImplementation = fetchMock.getMockImplementation()!;
    const delayed = deferredResponse();
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input).replace(API_BASE, "");
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
              updated_at: "2026-06-03T12:02:00Z",
              metadata: {},
            },
            {
              proposal_id: "patch_987654321",
              request_id: "req_987654321",
              workspace_id: "demo",
              path: "other.txt",
              base_file_hash: "sha256:otherbase",
              proposal_hash: "sha256:otherproposal",
              status: "proposed",
              created_at: "2026-06-03T12:00:00Z",
              updated_at: "2026-06-03T12:01:00Z",
              metadata: {},
            },
          ],
        });
      }
      if (path === "/patch-proposals/patch_987654321") {
        return delayed.promise;
      }
      return initialImplementation(input, init);
    });
    const user = await saveToken();

    await user.click(screen.getByRole("button", { name: /other\.txt/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/patch-proposals/patch_987654321`,
      expect.anything(),
    ));
    await user.click(screen.getByRole("button", { name: /demo\.txt/i }));
    delayed.resolve(jsonResponse({
      proposal_id: "patch_987654321",
      request_id: "req_987654321",
      workspace_id: "demo",
      path: "other.txt",
      base_file_hash: "sha256:otherbase",
      proposal_hash: "sha256:otherproposal",
      status: "proposed",
      created_at: "2026-06-03T12:00:00Z",
      updated_at: "2026-06-03T12:01:00Z",
      metadata: {},
    }));

    const detail = screen.getByRole("region", { name: "Selected artifact detail" });
    expect(await within(detail).findByRole("heading", { name: "demo.txt" })).toBeInTheDocument();
  });

  it("keeps delayed run detail and evidence bound to the current run", async () => {
    const fetchMock = installFetchMock();
    const initialImplementation = fetchMock.getMockImplementation()!;
    const delayedDetail = deferredResponse();
    const delayedEvidence = deferredResponse();
    const secondRun = {
      run_id: "run_987654321",
      principal_id: "agent:other",
      principal_type: "agent",
      principal_roles: ["AgentDeveloper"],
      workspace_id: "other",
      session_id: "mcp-stdio",
      status: "active",
      tool_call_count: 1,
      created_at: "2026-06-03T11:00:00Z",
      updated_at: "2026-06-03T11:01:00Z",
      last_request_id: "req_987654321",
      policy_hash: "sha256:otherpolicy",
      last_tool_name: "fs.read",
      last_tool_manifest_hash: "sha256:othertool",
      metadata: {},
    };
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input).replace(API_BASE, "");
      if (path.startsWith("/runs?")) {
        return jsonResponse({
          runs: [
            {
              ...secondRun,
              run_id: "run_123456789",
              principal_id: "agent:mcp-local",
              workspace_id: "demo",
              updated_at: "2026-06-03T12:01:00Z",
              last_request_id: "req_123456789",
              metadata: { scenario: "guided_local_demo" },
            },
            secondRun,
          ],
          summary: {
            returned: 2,
            filters: {},
            workspaces: { demo: 1, other: 1 },
            principals: { "agent:mcp-local": 1, "agent:other": 1 },
            statuses: { active: 2 },
            tools: { "fs.read": 2 },
            latest_updated_at: "2026-06-03T12:01:00Z",
          },
        });
      }
      if (path === "/runs/run_987654321") return delayedDetail.promise;
      if (path === "/runs/run_987654321/evidence-export") return delayedEvidence.promise;
      return initialImplementation(input, init);
    });
    const user = await saveToken();
    const runSection = screen.getByText("Agent Runs").closest("section")!;

    await user.click(within(runSection).getByRole("button", { name: /agent:other/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/runs/run_987654321`,
      expect.anything(),
    ));
    await user.click(within(runSection).getByRole("button", { name: /agent:mcp-local/i }));
    delayedDetail.resolve(jsonResponse({ run: secondRun, timeline: [] }));
    delayedEvidence.resolve(jsonResponse({
      schema_version: "1",
      export_id: "runev_987654321",
      exported_at: "2026-06-03T11:02:00Z",
      run: { run_id: "run_987654321" },
      summary: {
        principal_id: "agent:other",
        workspace_id: "other",
        session_id: "mcp-stdio",
        status: "active",
        tool_call_count: 1,
        tools_used: ["fs.read"],
        decision_counts: {},
        approval_count: 0,
        patch_diagnostic_count: 0,
        audit_event_count: 0,
        warning_count: 0,
        latest_policy_hash: null,
        manifest_lock_hash: null,
      },
      timeline: [], approvals: [], patch_diagnostics: [], signed_export_references: [],
      evidence_hashes: {}, redaction_summary: { excluded_categories: [] }, warnings: [],
    }));

    const detail = screen.getByRole("region", { name: "Selected run detail" });
    expect(await within(detail).findByRole("heading", { name: "agent:mcp-local" })).toBeInTheDocument();
    expect(within(detail).queryByRole("heading", { name: "agent:other" })).not.toBeInTheDocument();
  });

  it("suppresses an opposite approval action while a decision is in flight", async () => {
    const fetchMock = installFetchMock();
    const initialImplementation = fetchMock.getMockImplementation()!;
    const delayed = deferredResponse();
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/approvals/appr_123456789/deny")) {
        return delayed.promise;
      }
      return initialImplementation(input, init);
    });
    const user = await saveToken();
    const deny = screen.getByRole("button", { name: /^Deny$/i });
    const approve = screen.getByRole("button", { name: /^Approve$/i });

    await user.click(deny);
    expect(deny).toBeDisabled();
    expect(approve).toBeDisabled();
    fireEvent.click(approve);
    expect(fetchMock).not.toHaveBeenCalledWith(
      `${API_BASE}/approvals/appr_123456789/approve`,
      expect.objectContaining({ method: "POST" }),
    );
    delayed.resolve(jsonResponse(approvalReview.approval));
  });

  it("does not restore delayed detail after signing out", async () => {
    const fetchMock = installFetchMock();
    const initialImplementation = fetchMock.getMockImplementation()!;
    const delayed = deferredResponse();
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/patch-proposals/patch_123456789")) {
        return delayed.promise;
      }
      return initialImplementation(input, init);
    });
    const user = await saveToken();
    const tokenInput = screen.getByLabelText("Admin token");

    await user.clear(tokenInput);
    await user.click(screen.getByRole("button", { name: /save/i }));
    delayed.resolve(jsonResponse({
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
    }));

    expect(await screen.findByText("Admin token required.")).toBeInTheDocument();
    const detail = screen.getByRole("region", { name: "Selected artifact detail" });
    expect(within(detail).getByText("Locked.")).toBeInTheDocument();
    expect(within(detail).queryByRole("heading", { name: "demo.txt" })).not.toBeInTheDocument();
  });
});

import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App, verifyEvidenceSectionDigests } from "./App";

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
  additionalNodes?: Record<string, unknown>[];
  nodeOverrides?: Record<string, unknown>;
  nodeRevokeFailure?: boolean;
  nodeRun?: boolean;
  nodeRunOriginMismatch?: boolean;
  runEvidenceRevisionMismatch?: boolean;
  nodeStatus?: "enrolled" | "revoked";
  proposalStatus?: "applied" | "proposed";
  runEvidenceFailure?: boolean;
  runEvidenceHashMismatch?: boolean;
};

type TestJsonValue = string | number | boolean | null | TestJsonValue[] | TestJsonObject;
type TestJsonObject = { [key: string]: TestJsonValue };

function testCanonicalJson(value: TestJsonValue): string {
  if (Array.isArray(value)) return `[${value.map(testCanonicalJson).join(",")}]`;
  if (value !== null && typeof value === "object") {
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${testCanonicalJson(value[key])}`)
      .join(",")}}`;
  }
  return JSON.stringify(value);
}

async function testSha256(value: TestJsonValue) {
  const digest = await globalThis.crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(testCanonicalJson(value)),
  );
  return `sha256:${Array.from(
    new Uint8Array(digest),
    (byte) => byte.toString(16).padStart(2, "0"),
  ).join("")}`;
}

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
  const runPrincipalId = options.nodeRun
    ? "agent:node.node_11111111111111111111111111111111"
    : "agent:mcp-local";
  const runSessionId = options.nodeRun
    ? "node:node_11111111111111111111111111111111:cfg:1:sha256:desiredconfiguration:hermes-read"
    : "mcp-stdio";
  const runRoles = options.nodeRun ? ["AgentReadOnly"] : ["AgentDeveloper"];
  const runMetadata = options.nodeRun
    ? {
        authorization_profile: "agent:node-local-preview-readonly",
        configuration_digest: "sha256:desiredconfiguration",
        configuration_generation: 1,
        created_by: "governed_tool_call",
        identity_source: "gateway_derived_node",
        ingress_kind: "node_governed_access",
        node_display_name: "Hermes Node",
        node_id: "node_11111111111111111111111111111111",
        offline_fallback_allowed: false,
        runner_enforcement_proven: false,
      }
    : { scenario: "guided_local_demo", demo_step: "mediated_patch_flow" };
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
    if (
      path === "/nodes/node_11111111111111111111111111111111/configurations"
      && init?.method === "POST"
    ) {
      return jsonResponse({
        configuration_id: "ncfg_22222222222222222222222222222222",
        generation: 2,
        configuration_digest: "sha256:newconfiguration",
        issued_at: "2026-07-16T12:02:00Z",
        expires_at: "2026-07-16T13:02:00Z",
        evidence_status: "complete",
        assignment_kind: "direct",
        rollback_source_generation: null,
      });
    }
    if (
      path === "/nodes/node_11111111111111111111111111111111/configuration-trust-transitions"
      && init?.method === "POST"
    ) {
      return jsonResponse({
        transition_id: "nct_44444444444444444444444444444444",
        transition_digest: "sha256:newtrusttransition",
        current_key_id: "sha256:configsigner",
        next_key_id: "sha256:operatornextsigner",
        issued_at: "2026-07-16T12:03:00Z",
        expires_at: "2026-07-17T12:03:00Z",
        evidence_status: "complete",
        acknowledgment_status: null,
        acknowledgment_evidence_status: null,
        acknowledged_at: null,
        gateway_key_id: "sha256:configsigner",
        node_acknowledged_key_id: "sha256:configsigner",
        rotation_state: "awaiting_node_stage",
        activation_proven: false,
        enforcement_proven: false,
      });
    }
    if (
      path === "/nodes/node_11111111111111111111111111111111/revoke"
      && init?.method === "POST"
    ) {
      if (options.nodeRevokeFailure) {
        return jsonResponse(
          { detail: "Node evidence is incomplete" },
          { status: 409, statusText: "Conflict" },
        );
      }
      return jsonResponse({
        node_id: "node_11111111111111111111111111111111",
        status: "revoked",
        evidence_status: "complete",
        revoked_at: "2026-07-16T12:10:00Z",
      });
    }
    if (path === "/nodes/node_11111111111111111111111111111111/configurations?limit=50") {
      return jsonResponse({
        node_id: "node_11111111111111111111111111111111",
        count: 1,
        rollback_semantics: "fresh_signed_generation",
        enforcement_proven: false,
        configurations: [
          {
            configuration_id: "ncfg_11111111111111111111111111111111",
            generation: 1,
            configuration_digest: "sha256:desiredconfiguration",
            issued_at: "2026-07-16T12:00:00Z",
            expires_at: "2026-07-16T13:00:00Z",
            evidence_status: "complete",
            assignment_kind: "direct",
            rollback_source_generation: null,
            configuration: {
              minimum_node_version: "0.1.0",
              heartbeat_interval_seconds: 30,
            },
            is_desired: true,
          },
        ],
      });
    }
    if (path === "/nodes") {
      return jsonResponse({
        nodes: (() => {
          const baseNode = {
            node_id: "node_11111111111111111111111111111111",
            principal_id: "agent:node.node_11111111111111111111111111111111",
            workspace_id: "demo",
            display_name: "Hermes Node",
            status: options.nodeStatus ?? "enrolled",
            evidence_status: "complete",
            observed_state:
              options.nodeStatus === "revoked" ? "revoked" : "observed_connected",
            descriptor_hash: "sha256:nodedescriptor",
            descriptor: {
              protocol_version: "1",
              node_version: "0.1.0",
              runner_adapter: "hermes",
              deployment_topology: "docker_sidecar",
            },
            enrolled_at: "2026-07-16T12:00:00Z",
            updated_at: "2026-07-16T12:01:00Z",
            last_seen_at: "2026-07-16T12:01:00Z",
            revoked_at: options.nodeStatus === "revoked" ? "2026-07-16T12:10:00Z" : null,
            last_heartbeat_hash: "sha256:heartbeat",
            last_observed_node_version: "0.1.0",
            last_configuration_digest: "sha256:configuration",
            last_mission_id: "mission-synthetic-001",
            configuration_state: options.nodeStatus === "revoked"
              ? "revoked"
              : "stored_current_not_enforced",
            desired_configuration_generation: 1,
            desired_configuration_digest: "sha256:desiredconfiguration",
            acknowledged_configuration_generation: 1,
            acknowledged_configuration_digest: "sha256:desiredconfiguration",
            configuration_acknowledged_at: "2026-07-16T12:01:00Z",
            configuration_acknowledgment_status: "stored_not_enforced",
            acknowledged_configuration_signing_key_id: "sha256:configsigner",
            acknowledged_active_configuration_signing_key_id: "sha256:configsigner",
            configuration_signing_key_id: "sha256:configsigner",
            configuration_trust_transition: {
              transition_id: "nct_33333333333333333333333333333333",
              transition_digest: "sha256:trusttransition",
              current_key_id: "sha256:configsigner",
              next_key_id: "sha256:nextconfigsigner",
              issued_at: "2026-07-16T12:00:00Z",
              expires_at: "2026-07-17T12:00:00Z",
              evidence_status: "complete",
              acknowledgment_status: "staged_not_active",
              acknowledgment_evidence_status: "complete",
              acknowledged_at: "2026-07-16T12:02:00Z",
              gateway_key_id: "sha256:configsigner",
              node_acknowledged_key_id: "sha256:configsigner",
              rotation_state: "staged_not_active",
              activation_proven: false,
              enforcement_proven: false,
            },
            active_identity_key_id: "sha256:nodeidentitykey2",
            identity_key_rotation: {
              rotation_id: "nkr_44444444444444444444444444444444",
              current_key_id: "sha256:nodeidentitykey1",
              next_key_id: "sha256:nodeidentitykey2",
              created_at: "2026-07-16T12:00:00Z",
              expires_at: "2026-07-16T13:00:00Z",
              activated_at: "2026-07-16T12:05:00Z",
              status: "activated",
              evidence_status: "complete",
              private_key_received: false,
              retired_key_request_authority: false,
            },
            minimum_node_version: "0.1.0",
            version_posture: options.nodeStatus === "revoked" ? "revoked" : "meets_minimum",
            version_desired_source: "signed_desired_configuration",
            version_observed_source: "gateway_accepted_signed_heartbeat",
            maintenance_control_source: "operator_managed",
            package_authenticity_known: false,
            self_update_allowed: false,
            identity_source: "gateway_derived",
            connectivity_source: "gateway_accepted_heartbeat",
            runner_health_known: false,
            model_health_known: false,
            governed_access: {
              state: options.nodeStatus === "revoked" ? "blocked" : "ready_read_only",
              reason_code: options.nodeStatus === "revoked"
                ? "node_not_currently_observed"
                : "all_gateway_prerequisites_current",
              identity_source: "gateway_derived_node",
              authorization_profile: "agent:node-local-preview-readonly",
              workspace_id: "demo",
              allowed_risks: ["read"],
              allowed_tool_count: 19,
              enforcement_point: "gateway_governed_tool_pipeline",
              node_configuration_enforcement_proven: false,
              runner_enforcement_proven: false,
              offline_fallback_allowed: false,
              configuration_generation: 1,
              configuration_digest: "sha256:desiredconfiguration",
            },
            ...(options.nodeOverrides ?? {}),
          };
          return [
            baseNode,
            ...(options.additionalNodes ?? []).map((node) => ({ ...baseNode, ...node })),
          ];
        })(),
      });
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
            principal_id: runPrincipalId,
            principal_type: "agent",
            principal_roles: runRoles,
            workspace_id: "demo",
            session_id: runSessionId,
            status: "active",
            tool_call_count: 2,
            created_at: "2026-06-03T12:00:00Z",
            updated_at: "2026-06-03T12:01:00Z",
            last_request_id: "req_123456789",
            policy_hash: "sha256:policyhash",
            last_tool_name: "fs.read",
            last_tool_manifest_hash: "sha256:toolhash",
            metadata: runMetadata,
          },
        ],
        summary: {
          returned: 1,
          filters: path.includes("principal_id")
            ? options.nodeRun
              ? { principal_id: runPrincipalId, workspace_id: "demo" }
              : { principal_id: "agent:mcp-local", workspace_id: "demo", tool_name: "fs.read" }
            : {},
          workspaces: { demo: 1 },
          principals: { [runPrincipalId]: 1 },
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
          principal_id: runPrincipalId,
          principal_type: "agent",
          principal_roles: runRoles,
          workspace_id: "demo",
          session_id: runSessionId,
          status: "active",
          tool_call_count: 2,
          created_at: "2026-06-03T12:00:00Z",
          updated_at: "2026-06-03T12:01:00Z",
          last_request_id: "req_123456789",
          policy_hash: "sha256:policyhash",
          last_tool_name: "fs.read",
          last_tool_manifest_hash: "sha256:toolhash",
          metadata: runMetadata,
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
      if (options.runEvidenceFailure) {
        return jsonResponse(
          { detail: "run evidence unavailable" },
          { status: 503, statusText: "Unavailable" },
        );
      }
      const evidenceRun = JSON.parse(JSON.stringify({
        run_id: "run_123456789",
        principal_id: runPrincipalId,
        workspace_id: "demo",
        session_id: runSessionId,
        status: "active",
        tool_call_count: options.runEvidenceRevisionMismatch ? 1 : 2,
        created_at: "2026-06-03T12:00:00Z",
        updated_at: "2026-06-03T12:01:00Z",
        policy_hash: "sha256:policyhash",
        manifest_lock_hash: "sha256:toolhash",
        origin: options.nodeRun
          ? {
              ...runMetadata,
              ...(options.nodeRunOriginMismatch
                ? { configuration_digest: "sha256:mismatched-configuration" }
                : {}),
            }
          : null,
      })) as TestJsonObject;
      const timeline: TestJsonValue[] = [];
      const approvals: TestJsonValue[] = [];
      const patchDiagnostics: TestJsonValue[] = [];
      const evidenceHashes = {
        run_sha256: await testSha256(evidenceRun),
        timeline_sha256: await testSha256(timeline),
        approvals_sha256: await testSha256(approvals),
        patch_diagnostics_sha256: await testSha256(patchDiagnostics),
      };
      if (options.runEvidenceHashMismatch) {
        evidenceHashes.timeline_sha256 = `sha256:${"0".repeat(64)}`;
      }
      return jsonResponse({
        schema_version: "1",
        export_id: "runev_123456789",
        exported_at: "2026-06-03T12:02:00Z",
        run: evidenceRun,
        summary: {
          principal_id: runPrincipalId,
          workspace_id: "demo",
          session_id: runSessionId,
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
        timeline,
        approvals,
        patch_diagnostics: patchDiagnostics,
        signed_export_references: [],
        evidence_hashes: evidenceHashes,
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
      "Missions",
      "Nodes",
      "Artifacts",
      "Approvals",
      "Evidence",
      "Administration",
      "Help",
    ]) {
      expect(within(navigation).getByRole("link", { name: label })).toBeInTheDocument();
    }
    expect(screen.getByText("Sign-in required")).toBeInTheDocument();
    expect(
      screen.getByText(/Sign in with the local admin token to load operator attention records/i),
    ).toBeInTheDocument();

    await user.type(screen.getByLabelText("Admin token"), "local-token");
    await user.click(screen.getByRole("button", { name: /save/i }));

    const attention = await screen.findByRole("region", { name: "Attention" });
    expect(screen.getByText("Authenticated local preview")).toBeInTheDocument();
    expect(within(attention).getAllByText("Guided local demo mission").length).toBeGreaterThan(0);
    expect(within(attention).getAllByText("Apply demo patch").length).toBeGreaterThan(0);
    expect(within(attention).getByText("Review decision")).toBeInTheDocument();
    expect(within(attention).getByText("demo")).toBeInTheDocument();
    expect(within(attention).getByText("agent:mcp-local")).toBeInTheDocument();
    expect(within(attention).getByText("write tools require approval")).toBeInTheDocument();
    const attentionQueue = within(attention).getByLabelText("Prioritized operator attention");
    const [selectedAttention, secondaryAttention] = within(attentionQueue).getAllByRole("button");
    expect(selectedAttention).toHaveAttribute("aria-pressed", "true");
    expect(selectedAttention).toHaveTextContent("Apply demo patch");
    expect(secondaryAttention).toHaveAttribute("aria-pressed", "false");
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
    expect(screen.getByText("Local mediated evidence")).toBeInTheDocument();
    expect(screen.getByText(/does not establish immutable custody/i)).toBeInTheDocument();
    expect(screen.getByText("Recent Audit Events")).toBeInTheDocument();
    expect(screen.queryByText("Request Decision Preflight")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Routine operations" }));

    await user.click(within(navigation).getByRole("link", { name: "Administration" }));
    await waitFor(() => {
      expect(document.getElementById("administration")).toHaveFocus();
    });
    expect(screen.getByText("Request Decision Preflight")).toBeInTheDocument();
    expect(
      within(navigation).getByRole("link", { name: "Administration" }),
    ).toHaveAttribute("aria-current", "page");
    await user.click(screen.getByRole("button", { name: "Routine operations" }));

    await user.click(
      within(attention).getByRole("button", { name: "Open mission Workbench" }),
    );
    await waitFor(() => {
      expect(document.getElementById("missions")).toHaveFocus();
    });
    expect(within(navigation).getByRole("link", { name: "Missions" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(document.getElementById("missions")).not.toBeNull();
  });

  it("switches the command rail between complete destination screens", async () => {
    installFetchMock();
    const user = userEvent.setup();
    render(<App />);

    const navigation = screen.getByRole("navigation", {
      name: "Command Center sections",
    });
    const main = screen.getByRole("main");

    expect(main).toHaveAttribute("data-active-section", "attention");
    for (const [label, destination] of [
      ["Missions", "missions"],
      ["Nodes", "nodes"],
      ["Artifacts", "artifacts"],
      ["Approvals", "approvals"],
      ["Evidence", "evidence"],
      ["Administration", "administration"],
      ["Help", "help"],
    ]) {
      const link = within(navigation).getByRole("link", { name: label });
      await user.click(link);
      expect(main).toHaveAttribute("data-active-section", destination);
      expect(link).toHaveAttribute("aria-current", "page");
    }

    expect(screen.getByRole("heading", { name: "How to read Command Center" })).toBeInTheDocument();
    expect(screen.getByText("Gateway is authoritative")).toBeInTheDocument();
  });

  it("presents Gateway-derived Node identity without claiming runner health", async () => {
    const fetchMock = installFetchMock();
    const user = await saveToken();
    const navigation = screen.getByRole("navigation", {
      name: "Command Center sections",
    });

    await user.click(within(navigation).getByRole("link", { name: "Nodes" }));

    const nodes = screen.getByRole("region", { name: "Ithildin Nodes" });
    const selectedNodeRecord = within(nodes).getByRole("region", {
      name: "Selected Node record",
    });
    expect(within(nodes).getByRole("heading", { name: "Enforcement nodes" })).toBeInTheDocument();
    expect(within(nodes).getAllByText("Hermes Node")).toHaveLength(2);
    expect(selectedNodeRecord).toHaveTextContent("Hermes Node");
    expect(within(nodes).getAllByText("observed connected").length).toBeGreaterThan(0);
    expect(
      within(nodes).getByText(/correctly signed heartbeat was recently accepted/i),
    ).toBeInTheDocument();
    expect(within(nodes).getByText("Runner health · unknown")).toBeInTheDocument();
    expect(within(nodes).getByText("Policy enforcement · unknown")).toBeInTheDocument();
    expect(within(nodes).getByText("Node version posture")).toBeInTheDocument();
    expect(within(nodes).getByText("Node identity-key posture")).toBeInTheDocument();
    expect(within(nodes).getByText("Governed access posture")).toBeInTheDocument();
    expect(within(nodes).getAllByText("ready read only")).toHaveLength(2);
    expect(
      within(nodes).getByText(/19 existing read-only tools may be mediated through the Gateway/i),
    ).toBeInTheDocument();
    expect(within(nodes).getByText(/retired keys have no request authority/i)).toBeInTheDocument();
    expect(within(nodes).getAllByText("meets minimum").length).toBeGreaterThan(0);
    expect(within(nodes).getByText(/Maintenance remains operator-managed/i)).toBeInTheDocument();
    expect(within(nodes).getByText(/Node attests that the signed configuration is stored/i)).toBeInTheDocument();
    expect(within(selectedNodeRecord).getAllByText("Generation 1")).toHaveLength(2);
    expect(within(nodes).getByText("Identity source · Gateway derived")).toBeInTheDocument();

    await user.click(within(nodes).getByText("Manage signed desired state"));
    expect(await within(nodes).findByText("1 generations")).toBeInTheDocument();
    const confirmation = within(nodes).getByRole("checkbox", {
      name: /changes Gateway desired state for this Node only/i,
    });
    await user.click(confirmation);
    await user.click(within(nodes).getByRole("button", { name: "Assign signed generation" }));
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        `${API_BASE}/nodes/node_11111111111111111111111111111111/configurations`,
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(within(nodes).getAllByText("staged not active").length).toBeGreaterThan(0);
    await user.type(
      within(nodes).getByLabelText("Next Ed25519 public key"),
      "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    );
    await user.click(within(nodes).getByRole("checkbox", {
      name: /stages a public trust root for this Node only/i,
    }));
    await user.click(within(nodes).getByRole("button", {
      name: "Assign signed trust transition",
    }));
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        `${API_BASE}/nodes/node_11111111111111111111111111111111/configuration-trust-transitions`,
        expect.objectContaining({ method: "POST" }),
      );
    });
  });

  it("opens a Node's mediated runs with Gateway-derived authority and non-claims", async () => {
    const fetchMock = installFetchMock(systemStatus(), {
      nodeRun: true,
      noApprovals: true,
      proposalStatus: "applied",
    });
    const user = await saveToken();
    const navigation = screen.getByRole("navigation", {
      name: "Command Center sections",
    });

    await user.click(within(navigation).getByRole("link", { name: "Nodes" }));
    const nodes = screen.getByRole("region", { name: "Ithildin Nodes" });
    expect(within(nodes).getByText("Governed access ready").parentElement).toHaveTextContent("1");
    await user.click(within(nodes).getByRole("button", { name: "View mediated runs" }));

    await waitFor(() => {
      expect(within(navigation).getByRole("link", { name: "Missions" })).toHaveAttribute(
        "aria-current",
        "page",
      );
    });
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/runs?limit=25&principal_id=agent%3Anode.node_11111111111111111111111111111111&workspace_id=demo`,
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer local-token" }),
      }),
    );

    const missions = screen.getByRole("region", { name: "Agent runs" });
    expect(within(missions).getByLabelText("Principal")).toHaveValue(
      "agent:node.node_11111111111111111111111111111111",
    );
    expect(within(missions).getByLabelText("Workspace")).toHaveValue("demo");
    expect(within(missions).getAllByText("Hermes Node governed session").length).toBeGreaterThan(0);
    expect(within(missions).getAllByText("Gateway-derived Node identity").length).toBeGreaterThan(0);
    expect(within(missions).getByText("1 Node-authenticated governed runs")).toBeInTheDocument();

    const authority = within(missions).getByRole("region", {
      name: "Node governed-run authority",
    });
    expect(within(authority).getByRole("heading", {
      name: "Node-authenticated governed read",
    })).toBeInTheDocument();
    expect(within(authority).getByText("node_11111111111111111111111111111111")).toBeInTheDocument();
    expect(within(authority).getByText("agent:node-local-preview-readonly")).toBeInTheDocument();
    expect(within(authority).getByText(/Generation 1/)).toBeInTheDocument();
    expect(within(authority).getByText("Prohibited")).toBeInTheDocument();
    expect(within(authority).getByText("Not proven")).toBeInTheDocument();
    expect(await within(authority).findByText("Matches selected run")).toBeInTheDocument();
    expect(within(authority).getByText(/same-record consistency, not independent attestation/i))
      .toBeInTheDocument();
    expect(within(authority).getByText(/activity that bypassed the Gateway remains outside/i))
      .toBeInTheDocument();
  });

  it("blocks reliance on a mismatched Node origin in generated run evidence", async () => {
    installFetchMock(systemStatus(), {
      nodeRun: true,
      nodeRunOriginMismatch: true,
      noApprovals: true,
      proposalStatus: "applied",
    });
    const user = await saveToken();
    const navigation = screen.getByRole("navigation", {
      name: "Command Center sections",
    });

    await user.click(within(navigation).getByRole("link", { name: "Missions" }));
    const missions = screen.getByRole("region", { name: "Agent runs" });
    const authority = await within(missions).findByRole("region", {
      name: "Node governed-run authority",
    });
    expect(within(authority).getByText("Mismatch - do not rely on export origin"))
      .toBeInTheDocument();
    expect(within(authority).getByText(/do not rely on the export origin/i)).toBeInTheDocument();
    expect(within(authority).queryByText("Matches selected run")).toBeNull();
  });

  it("blocks handoff reliance when selected run detail and evidence revisions differ", async () => {
    installFetchMock(systemStatus(), {
      noApprovals: true,
      proposalStatus: "applied",
      runEvidenceRevisionMismatch: true,
    });
    const user = await saveToken();
    const navigation = screen.getByRole("navigation", {
      name: "Command Center sections",
    });

    await user.click(within(navigation).getByRole("link", { name: "Missions" }));
    const closeout = await screen.findByRole("region", { name: "Run evidence closeout" });
    expect(within(closeout).getByText("Mismatch - reload before handoff")).toBeInTheDocument();
    expect(within(closeout).getByText(/selected detail and generated snapshot differ/i))
      .toBeInTheDocument();
    expect(within(closeout).queryByText("Matches generated snapshot")).toBeNull();
  });

  it("blocks snapshot reliance when local evidence section digest verification fails", async () => {
    installFetchMock(systemStatus(), {
      noApprovals: true,
      proposalStatus: "applied",
      runEvidenceHashMismatch: true,
    });
    const user = await saveToken();
    const navigation = screen.getByRole("navigation", {
      name: "Command Center sections",
    });

    await user.click(within(navigation).getByRole("link", { name: "Missions" }));
    const closeout = await screen.findByRole("region", { name: "Run evidence closeout" });
    expect(await within(closeout).findByText("Mismatch - do not rely on snapshot"))
      .toBeInTheDocument();
    expect(within(closeout).getByText(/Mismatched or missing: timeline/i)).toBeInTheDocument();
    expect(within(closeout).queryByText("4 of 4 section digests match")).toBeNull();

    await user.click(screen.getByRole("button", { name: /Export Run Evidence/i }));
    await waitFor(() => {
      expect(within(closeout).getByRole("status")).toHaveTextContent(
        "Run evidence section digest verification failed; download blocked",
      );
    });
    expect(URL.createObjectURL).not.toHaveBeenCalled();
  });

  it("reports local evidence digest verification as unavailable when hashing fails", async () => {
    const result = await verifyEvidenceSectionDigests(
      {
        evidence_hashes: {},
        run: {},
        timeline: [],
        approvals: [],
        patch_diagnostics: [],
      } as never,
      async () => {
        throw new Error("Web Crypto unavailable");
      },
    );

    expect(result).toEqual({
      status: "unavailable",
      matchedSections: 0,
      mismatchedSections: [],
    });
  });

  it("keeps Node evidence-origin parity unavailable when snapshot loading fails", async () => {
    installFetchMock(systemStatus(), {
      nodeRun: true,
      runEvidenceFailure: true,
      noApprovals: true,
      proposalStatus: "applied",
    });
    const user = await saveToken();
    const navigation = screen.getByRole("navigation", {
      name: "Command Center sections",
    });

    await user.click(within(navigation).getByRole("link", { name: "Missions" }));
    const missions = screen.getByRole("region", { name: "Agent runs" });
    const authority = await within(missions).findByRole("region", {
      name: "Node governed-run authority",
    });
    expect(within(authority).getByText("Unavailable")).toBeInTheDocument();
    expect(within(authority).getByText(/cannot be compared with this selected run/i))
      .toBeInTheDocument();
    expect(within(authority).queryByText("Matches selected run")).toBeNull();
  });

  it("requires exact confirmation before revoking Gateway Node authority", async () => {
    const fetchMock = installFetchMock();
    const user = await saveToken();
    const navigation = screen.getByRole("navigation", {
      name: "Command Center sections",
    });

    await user.click(within(navigation).getByRole("link", { name: "Nodes" }));
    const nodes = screen.getByRole("region", { name: "Ithildin Nodes" });
    await user.click(within(nodes).getByText("Manage Node lifecycle"));

    expect(
      within(nodes).getByText(/does not stop a runner, terminate model inference/i),
    ).toBeInTheDocument();
    const revokeButton = within(nodes).getByRole("button", { name: "Revoke Node identity" });
    const confirmation = within(nodes).getByLabelText("Type Node ID to confirm");
    const consequence = within(nodes).getByRole("checkbox", {
      name: /revokes Gateway request authority only/i,
    });
    expect(revokeButton).toBeDisabled();

    await user.type(confirmation, "node_wrong");
    await user.click(consequence);
    expect(revokeButton).toBeDisabled();
    await user.clear(confirmation);
    await user.type(confirmation, "node_11111111111111111111111111111111");
    expect(revokeButton).toBeEnabled();

    await user.click(revokeButton);
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        `${API_BASE}/nodes/node_11111111111111111111111111111111/revoke`,
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({ Authorization: "Bearer local-token" }),
        }),
      );
    });
    expect(
      await within(nodes).findByText(/Future authenticated Node requests are denied/i),
    ).toBeInTheDocument();
  });

  it("keeps Node revocation unconfirmed when the Gateway rejects the transition", async () => {
    installFetchMock(systemStatus(), { nodeRevokeFailure: true });
    const user = await saveToken();
    const navigation = screen.getByRole("navigation", {
      name: "Command Center sections",
    });

    await user.click(within(navigation).getByRole("link", { name: "Nodes" }));
    const nodes = screen.getByRole("region", { name: "Ithildin Nodes" });
    await user.click(within(nodes).getByText("Manage Node lifecycle"));
    await user.type(
      within(nodes).getByLabelText("Type Node ID to confirm"),
      "node_11111111111111111111111111111111",
    );
    await user.click(within(nodes).getByRole("checkbox", {
      name: /revokes Gateway request authority only/i,
    }));
    await user.click(within(nodes).getByRole("button", { name: "Revoke Node identity" }));

    expect(await within(nodes).findByRole("alert")).toHaveTextContent(
      "Node evidence is incomplete",
    );
    expect(within(nodes).queryByText(/Future authenticated Node requests are denied/i)).toBeNull();
  });

  it("never presents a retained revoked-key fingerprint as active request authority", async () => {
    installFetchMock(systemStatus(), { nodeStatus: "revoked" });
    const user = await saveToken();
    const navigation = screen.getByRole("navigation", {
      name: "Command Center sections",
    });

    await user.click(within(navigation).getByRole("link", { name: "Nodes" }));
    const nodes = screen.getByRole("region", { name: "Ithildin Nodes" });
    expect(within(nodes).getByText("request authority revoked")).toBeInTheDocument();
    expect(
      within(nodes).getByText(
        /Gateway retains fingerprint .* the key cannot authenticate future Node requests/i,
      ),
    ).toBeInTheDocument();
    expect(within(nodes).getByText("Node identity revoked")).toBeInTheDocument();
    expect(within(nodes).queryByText("enrollment key active")).toBeNull();
    expect(within(nodes).getByText("Identity key fingerprint")).toBeInTheDocument();
    expect(within(nodes).queryByText("Active identity key")).toBeNull();
  });

  it("routes a stale Node from Attention to its exact authoritative fleet record", async () => {
    installFetchMock(systemStatus(), {
      noApprovals: true,
      proposalStatus: "applied",
      nodeOverrides: {
        observed_state: "stale",
        last_seen_at: "2026-07-16T11:00:00Z",
      },
    });
    const user = await saveToken();
    const navigation = screen.getByRole("navigation", {
      name: "Command Center sections",
    });
    await user.click(within(navigation).getByRole("link", { name: "Nodes" }));
    const nodes = screen.getByRole("region", { name: "Ithildin Nodes" });
    await user.type(within(nodes).getByLabelText("Search loaded Nodes"), "hidden by filter");
    expect(
      within(nodes).getByText("No loaded Nodes match the current fleet filters."),
    ).toBeInTheDocument();
    await user.click(within(navigation).getByRole("link", { name: "Attention" }));
    const attention = screen.getByRole("region", { name: "Attention" });

    expect(
      within(attention).getByRole("heading", { name: "Hermes Node heartbeat is stale" }),
    ).toBeInTheDocument();
    expect(
      within(attention).getByText(/does not establish runner, model, or host-process health/i),
    ).toBeInTheDocument();
    expect(within(attention).getByText("Node identity")).toBeInTheDocument();
    expect(within(attention).getByText("Fleet posture")).toBeInTheDocument();
    expect(within(attention).getByText("Authority source")).toBeInTheDocument();

    await user.click(
      within(attention).getByRole("button", { name: "Review connectivity evidence" }),
    );
    await waitFor(() => {
      expect(document.activeElement).toHaveAttribute(
        "id",
        "node-node_11111111111111111111111111111111",
      );
    });
    expect(
      navigation.querySelector('a[href="#nodes"]'),
    ).toHaveAttribute("aria-current", "page");
    expect(within(nodes).getByLabelText("Search loaded Nodes")).toHaveValue("");
  });

  it("filters and deterministically sorts the loaded Node fleet", async () => {
    installFetchMock(systemStatus(), {
      noApprovals: true,
      proposalStatus: "applied",
      nodeOverrides: {
        observed_state: "stale",
        last_seen_at: "2026-07-16T11:00:00Z",
      },
      additionalNodes: [
        {
          node_id: "node_22222222222222222222222222222222",
          principal_id: "agent:node.node_22222222222222222222222222222222",
          workspace_id: "alpha",
          display_name: "Atlas Node",
          observed_state: "observed_connected",
          last_seen_at: "2026-07-16T12:05:00Z",
        },
        {
          node_id: "node_33333333333333333333333333333333",
          principal_id: "agent:node.node_33333333333333333333333333333333",
          workspace_id: "archive",
          display_name: "Retired Node",
          status: "revoked",
          observed_state: "revoked",
          configuration_state: "revoked",
          version_posture: "revoked",
          revoked_at: "2026-07-16T12:10:00Z",
        },
      ],
    });
    const user = await saveToken();
    const navigation = screen.getByRole("navigation", {
      name: "Command Center sections",
    });
    await user.click(within(navigation).getByRole("link", { name: "Nodes" }));
    const nodes = screen.getByRole("region", { name: "Ithildin Nodes" });
    const inventory = within(nodes).getByRole("list", { name: "Filtered Node inventory" });

    expect(within(nodes).getByRole("status")).toHaveTextContent("3 of 3 loaded Nodes");
    expect(
      within(inventory).getAllByRole("listitem")[0],
    ).toHaveTextContent("Hermes Node");

    await user.selectOptions(within(nodes).getByLabelText("Sort"), "name");
    expect(
      within(inventory).getAllByRole("listitem")[0],
    ).toHaveTextContent("Atlas Node");
    await user.click(within(inventory).getByRole("button", { name: /Retired Node/ }));
    expect(within(nodes).getByRole("region", { name: "Selected Node record" })).toHaveTextContent(
      "Retired Node",
    );

    await user.selectOptions(within(nodes).getByLabelText("Workspace"), "alpha");
    expect(within(nodes).getByRole("status")).toHaveTextContent("1 of 3 loaded Nodes");
    expect(within(inventory).getByRole("button", { name: /Atlas Node/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(within(inventory).queryByRole("button", { name: /Hermes Node/ })).toBeNull();
    expect(within(nodes).getByRole("region", { name: "Selected Node record" })).toHaveTextContent(
      "Atlas Node",
    );

    await user.click(within(nodes).getByRole("button", { name: "Clear filters" }));
    await user.selectOptions(within(nodes).getByLabelText("Fleet posture"), "revoked");
    expect(within(nodes).getByRole("status")).toHaveTextContent("1 of 3 loaded Nodes");
    expect(within(inventory).getByRole("button", { name: /Retired Node/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    await user.selectOptions(within(nodes).getByLabelText("Fleet posture"), "all");
    await user.type(
      within(nodes).getByLabelText("Search loaded Nodes"),
      "node_22222222222222222222222222222222",
    );
    expect(within(nodes).getByRole("status")).toHaveTextContent("1 of 3 loaded Nodes");
    expect(within(inventory).getByRole("button", { name: /Atlas Node/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("groups loaded enrolled Nodes into bounded configuration rollout cohorts", async () => {
    installFetchMock(systemStatus(), {
      noApprovals: true,
      proposalStatus: "applied",
      additionalNodes: [
        {
          node_id: "node_22222222222222222222222222222222",
          principal_id: "agent:node.node_22222222222222222222222222222222",
          display_name: "Drifted Demo Node",
          configuration_state: "configuration_drift",
          acknowledged_configuration_generation: 0,
          acknowledged_configuration_digest: "sha256:previousconfiguration",
          version_posture: "below_minimum",
          observed_state: "stale",
          last_seen_at: "2026-07-16T10:00:00Z",
        },
        {
          node_id: "node_33333333333333333333333333333333",
          principal_id: "agent:node.node_33333333333333333333333333333333",
          display_name: "Pending Demo Node",
          desired_configuration_generation: 2,
          desired_configuration_digest: "sha256:nextconfiguration",
          configuration_state: "awaiting_node_storage",
          acknowledged_configuration_generation: null,
          acknowledged_configuration_digest: null,
          configuration_acknowledged_at: null,
          configuration_acknowledgment_status: null,
        },
        {
          node_id: "node_44444444444444444444444444444444",
          principal_id: "agent:node.node_44444444444444444444444444444444",
          workspace_id: "alpha",
          display_name: "Alpha Node",
        },
      ],
    });
    const user = await saveToken();
    const navigation = screen.getByRole("navigation", {
      name: "Command Center sections",
    });
    await user.click(within(navigation).getByRole("link", { name: "Nodes" }));
    const nodes = screen.getByRole("region", { name: "Ithildin Nodes" });
    const cohorts = within(nodes).getByRole("region", {
      name: "Loaded Node configuration cohorts",
    });

    expect(within(cohorts).getByText("3 loaded cohorts")).toBeInTheDocument();
    expect(within(cohorts).getByText(/Grouped from 4 loaded Gateway Node records/))
      .toBeInTheDocument();
    expect(within(cohorts).getByText(/Storage acknowledgments are Node-attested/))
      .toBeInTheDocument();

    const drifted = within(cohorts).getByRole("article", {
      name: "demo configuration Generation 1",
    });
    expect(drifted).toHaveTextContent("attention required");
    expect(drifted).toHaveTextContent("Enrolled Nodes2");
    expect(drifted).toHaveTextContent("Stored current1 / 2");
    expect(drifted).toHaveTextContent("Drift1");
    expect(drifted).toHaveTextContent("Version exceptions1");
    expect(drifted).toHaveTextContent("Recently observed1 / 2");

    const pending = within(cohorts).getByRole("article", {
      name: "demo configuration Generation 2",
    });
    expect(pending).toHaveTextContent("storage pending");
    expect(pending).toHaveTextContent("Awaiting storage1");

    const current = within(cohorts).getByRole("article", {
      name: "alpha configuration Generation 1",
    });
    expect(current).toHaveTextContent("stored current not enforced");
    expect(current).toHaveTextContent("Stored current1 / 1");

    await user.click(within(drifted).getByRole("button", { name: "Inspect 2 Nodes" }));
    expect(within(drifted).getByRole("button", { name: "Inspecting 2 Nodes" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(within(nodes).getByRole("status")).toHaveTextContent("2 of 4 loaded Nodes");
    const activeCohort = within(nodes).getByRole("group", {
      name: "Active configuration cohort filter",
    });
    expect(activeCohort).toHaveTextContent("Cohort scope · demo · Generation 1 · 2 enrolled Nodes");
    const inventory = within(nodes).getByRole("list", { name: "Filtered Node inventory" });
    expect(within(inventory).getAllByRole("listitem")).toHaveLength(2);
    expect(within(inventory).getByRole("button", { name: /Drifted Demo Node/ }))
      .toBeInTheDocument();
    expect(within(inventory).queryByRole("button", { name: /Pending Demo Node/ })).toBeNull();

    await user.type(
      within(nodes).getByLabelText("Search loaded Nodes"),
      "node_11111111111111111111111111111111",
    );
    expect(within(nodes).getByRole("status")).toHaveTextContent("1 of 4 loaded Nodes");
    expect(within(inventory).getByRole("button", { name: /Hermes Node/ })).toBeInTheDocument();

    await user.click(within(pending).getByRole("button", { name: "Inspect 1 Node" }));
    expect(within(pending).getByRole("button", { name: "Inspecting 1 Node" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(within(nodes).getByLabelText("Search loaded Nodes")).toHaveValue("");
    expect(within(nodes).getByRole("status")).toHaveTextContent("1 of 4 loaded Nodes");
    expect(within(inventory).getByRole("button", { name: /Pending Demo Node/ }))
      .toBeInTheDocument();

    await user.click(within(activeCohort).getByRole("button", { name: "Clear cohort scope" }));
    expect(within(nodes).queryByRole("group", {
      name: "Active configuration cohort filter",
    })).toBeNull();
    expect(within(nodes).getByRole("status")).toHaveTextContent("3 of 4 loaded Nodes");

    await user.click(within(current).getByRole("button", { name: "Inspect 1 Node" }));
    expect(within(nodes).getByRole("group", {
      name: "Active configuration cohort filter",
    })).toHaveTextContent("alpha · Generation 1");
    await user.click(screen.getByRole("button", { name: "Refresh" }));
    await waitFor(() => {
      expect(within(nodes).queryByRole("group", {
        name: "Active configuration cohort filter",
      })).toBeNull();
    });
  });

  it("prioritizes incomplete Node authority evidence over passive proposals", async () => {
    installFetchMock(systemStatus(), {
      noApprovals: true,
      nodeOverrides: { configuration_state: "evidence_incomplete" },
    });
    await saveToken();
    const attention = screen.getByRole("region", { name: "Attention" });
    const selected = within(attention).getByRole("button", {
      name: /demo Node fleet.*Hermes Node configuration evidence is incomplete/i,
    });

    expect(selected).toHaveAttribute("aria-pressed", "true");
    expect(
      within(attention).getByRole("button", { name: "Review configuration evidence" }),
    ).toBeInTheDocument();
    expect(within(attention).getByText("Review proposed change to demo.txt")).toBeInTheDocument();
  });

  it("does not create an Attention item for a revoked Node", async () => {
    installFetchMock(systemStatus(), {
      noApprovals: true,
      nodeStatus: "revoked",
      proposalStatus: "applied",
    });
    const user = await saveToken();
    const attention = screen.getByRole("region", { name: "Attention" });

    expect(
      within(attention).getByText(/No action identified in the currently loaded local records/i),
    ).toBeInTheDocument();
    expect(within(attention).queryByText(/Hermes Node/)).toBeNull();

    await user.click(screen.getByRole("link", { name: "Nodes" }));
    const nodes = screen.getByRole("region", { name: "Ithildin Nodes" });
    expect(within(nodes).queryByRole("region", {
      name: "Loaded Node configuration cohorts",
    })).toBeNull();
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
    expect(screen.getByLabelText("External runner governance posture")).toBeInTheDocument();
    expect(screen.getByText("Recorded ingress posture")).toBeInTheDocument();
    expect(screen.getByText("Governed calls only")).toBeInTheDocument();
    expect(screen.getByText("Unmanaged · no launch or health control")).toBeInTheDocument();
    expect(screen.getByText("Recorded run state · not runner health")).toBeInTheDocument();
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
    expect(await screen.findByText("1 bundle warnings")).toBeInTheDocument();
    expect(screen.getByText("Matches generated snapshot")).toBeInTheDocument();
    expect(screen.getByText("4 section digests")).toBeInTheDocument();
    expect(await screen.findByText("4 of 4 section digests match")).toBeInTheDocument();
    const sectionDigests = screen.getByLabelText("Evidence section digests");
    expect(within(sectionDigests).getAllByText(/^sha256:[0-9a-f]{64}$/)).toHaveLength(4);
    expect(within(sectionDigests).getByText(
      "sha256:e5c640ee0a8c46fe0eb70bef86905c6d21cd4f7fb8d75140832cecbfe95b4d64",
    )).toBeInTheDocument();
    expect(within(sectionDigests).getAllByText(
      "sha256:4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    )).toHaveLength(3);
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
    const approvalQueue = screen.getByLabelText("Pending approval queue");
    expect(within(approvalQueue).getByRole("button")).toHaveAttribute("aria-pressed", "true");
    expect(
      within(approvalArticle).getByText(/does not promote, release, or trust the resulting artifact/i),
    ).toBeInTheDocument();
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

    expect((await screen.findAllByText(/Unexpected token/)).length).toBeGreaterThan(0);
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
    expect(within(attention).getAllByText("Patch recovery review required").length).toBe(2);
    expect(within(attention).getAllByText(/6\/3\/26/).length).toBe(2);
  });

  it("uses stuck-approval expiry in recovery attention without an apply attempt", async () => {
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
          status: "ambiguous",
          attempts: [],
          stuck_approvals: [{
            approval_id: "appr_stuck",
            has_apply_attempt: false,
            expires_at: "2026-06-04T12:05:00Z",
          }],
          recommendations: [],
        });
      }
      return initialImplementation(input, init);
    });
    await saveToken();

    const attention = screen.getByRole("region", { name: "Attention" });
    expect(within(attention).getAllByText("Patch recovery review required").length).toBe(2);
    expect(within(attention).getAllByText(/6\/4\/26/).length).toBe(2);
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

  it("clears policy authority results when a dashboard refresh is partial", async () => {
    const fetchMock = installFetchMock();
    const user = await saveToken();
    await user.click(screen.getByRole("button", { name: "Policy administration" }));
    await user.click(screen.getByRole("button", { name: /^Test decision$/i }));
    expect(await screen.findByText("read allowed")).toBeInTheDocument();

    const initialImplementation = fetchMock.getMockImplementation()!;
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/tools")) {
        return jsonResponse({ detail: "tool inventory unavailable" }, { status: 503 });
      }
      return initialImplementation(input, init);
    });
    await user.click(screen.getByRole("button", { name: "Refresh" }));

    expect(await screen.findByText("tool inventory unavailable")).toBeInTheDocument();
    expect(screen.queryByText("read allowed")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Tool request")).toBeDisabled();
    expect(screen.getByRole("button", { name: /^Test decision$/i })).toBeDisabled();
  });

  it("does not repopulate selected detail during a partial replacement-token load", async () => {
    const fetchMock = installFetchMock();
    const user = await saveToken();
    const initialImplementation = fetchMock.getMockImplementation()!;
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/tools")) {
        return jsonResponse({ detail: "replacement dashboard unavailable" }, { status: 503 });
      }
      return initialImplementation(input, init);
    });

    const tokenInput = screen.getByLabelText("Admin token");
    await user.clear(tokenInput);
    await user.type(tokenInput, "replacement-token");
    await user.click(screen.getByRole("button", { name: /save/i }));

    expect(await screen.findByText("replacement dashboard unavailable")).toBeInTheDocument();
    const detail = screen.getByRole("region", { name: "Selected artifact detail" });
    expect(within(detail).getByText("Select a proposal.")).toBeInTheDocument();
    expect(within(detail).queryByRole("heading", { name: "demo.txt" })).not.toBeInTheDocument();
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

    const proposalList = screen.getByLabelText("Artifact proposal list");
    await user.click(within(proposalList).getByRole("button", { name: /other\.txt/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/patch-proposals/patch_987654321`,
      expect.anything(),
    ));
    await user.click(within(proposalList).getByRole("button", { name: /demo\.txt/i }));
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
    expect(
      await within(detail).findByRole("heading", { name: "Guided local demo mission" }),
    ).toBeInTheDocument();
    expect(within(detail).getAllByText("agent:mcp-local").length).toBeGreaterThan(0);
    expect(within(detail).queryByText("agent:other")).not.toBeInTheDocument();
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

  it("reconciles a successful approval decision after a concurrent dashboard refresh", async () => {
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
    const systemStatusCalls = () =>
      fetchMock.mock.calls.filter(([input]) => String(input).endsWith("/system/status")).length;

    await user.click(screen.getByRole("button", { name: /^Deny$/i }));
    await user.click(screen.getByRole("button", { name: "Refresh" }));
    await waitFor(() => expect(systemStatusCalls()).toBeGreaterThanOrEqual(2));
    delayed.resolve(jsonResponse(approvalReview.approval));

    await waitFor(() => expect(systemStatusCalls()).toBeGreaterThanOrEqual(3));
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

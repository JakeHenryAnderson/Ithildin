import {
  Activity,
  AlertTriangle,
  Check,
  ClipboardList,
  Download,
  FileDiff,
  KeyRound,
  RefreshCcw,
  ShieldCheck,
  X,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import "./styles.css";

const API_BASE =
  import.meta.env.VITE_ITHILDIN_API_BASE_URL ?? "http://127.0.0.1:8000";
const TOKEN_STORAGE_KEY = "ithildin.adminToken";
const DECIDED_BY = "admin:local-ui";

type JsonValue = string | number | boolean | null | JsonValue[] | JsonObject;
type JsonObject = { [key: string]: JsonValue };

type Approval = {
  approval_id: string;
  request_id: string;
  request_hash: string;
  principal: JsonObject;
  tool_name: string;
  resource: JsonObject;
  status: string;
  summary: string;
  expires_at: string;
  one_time_scope: JsonObject;
  metadata: JsonObject;
};

type PatchProposal = {
  proposal_id: string;
  request_id: string;
  workspace_id: string;
  path: string;
  base_file_hash: string;
  proposal_hash: string;
  status: string;
  created_at: string;
  updated_at: string;
  metadata: JsonObject;
  unified_diff?: string;
  review?: PatchReview;
};

type PatchReview = JsonObject & {
  stale?: boolean;
  stale_reason?: string | null;
  base_file_hash_matches?: boolean;
};

type BindingReview = {
  valid: boolean;
  checks: Record<string, boolean>;
  reasons: string[];
  proposal?: JsonObject | null;
};

type ApprovalReview = {
  approval: Approval;
  review: BindingReview;
};

type ToolSummary = {
  name: string;
  version: string;
  title: string;
  risk: string;
  category: string;
  manifest_hash: string;
  mcp: JsonObject;
};

type PolicyPreviewResult = {
  tool_name: string;
  manifest_hash: string | null;
  manifest_risk: string | null;
  manifest_version: string | null;
  valid_arguments: boolean;
  argument_error: string | null;
  policy_input: JsonObject | null;
  resource: JsonObject;
  decision: string;
  reason: string;
  policy_version: string;
  matched_rules: string[];
  obligations: JsonObject;
};

type PolicyImpactSummary = {
  policy_hash: string;
  passed: number;
  failed: number;
  case_count: number;
  failures: { id: string; failures: string[] }[];
};

type PolicyImpactChangedCase = {
  id: string;
  changes: string[];
  current: JsonObject | null;
  candidate: JsonObject;
};

type PolicyImpactResult = {
  current: PolicyImpactSummary;
  candidate: PolicyImpactSummary;
  changed_cases: PolicyImpactChangedCase[];
};

type AuditEvent = {
  event_id: string;
  timestamp: string;
  event_type: string;
  request_id: string;
  tool_name?: string | null;
  decision?: string | null;
  event_hash: string;
  metadata: JsonObject;
};

type AuditVerificationFailure = {
  row_number: number;
  event_id: string | null;
  reason: string;
};

type AuditVerification = {
  valid: boolean;
  event_count: number;
  first_timestamp: string | null;
  last_timestamp: string | null;
  head_hash: string;
  failure: AuditVerificationFailure | null;
};

type PolicyStatus = {
  engine: string;
  document_version: string;
  policy_hash: string;
  rule_count: number;
  bundle_verified?: boolean;
  bundle_version?: string;
  bundle_hash?: string;
  bundle_entrypoint?: string;
};

type SystemStatus = {
  status: string;
  service: string;
  tool_count: number;
  manifest_lock: {
    required: boolean;
    path: string;
    signature: {
      required: boolean;
      signature_path: string;
      public_key_configured: boolean;
      signature_configured: boolean;
      verified: boolean;
      key_id: string | null;
      error?: string;
    };
  };
  policy: PolicyStatus;
  audit: {
    valid: boolean;
    event_count: number;
    head_hash: string;
  };
  audit_signing: {
    algorithm: string;
    private_key_configured: boolean;
    public_key_configured: boolean;
    signed_export_available: boolean;
    key_id: string | null;
    error?: string;
  };
  redaction: {
    baseline_enabled: boolean;
    baseline_key_count: number;
    baseline_pattern_count: number;
    extra_key_count: number;
    extra_pattern_count: number;
  };
  security: {
    preview_label: string;
    production_ready: boolean;
    dev_admin_token: {
      sample_token_active: boolean;
      explicitly_allowed: boolean;
    };
    admin_token: {
      recommended_min_length: number;
      length_ok: boolean;
      contains_whitespace: boolean;
      weak: boolean;
    };
    local_only: {
      api_host_publish: string;
      ui_host_publish: string;
      remote_mcp_enabled: boolean;
    };
    cors: {
      allow_credentials: boolean;
      allow_origins: string[];
      wildcard_allowed: boolean;
    };
    warnings: string[];
  };
  limits: {
    approval_expiry_seconds: number;
    max_read_bytes: number;
    max_patch_bytes: number;
    search_result_limit: number;
    git_log_limit: number;
    http_allowlist_configured: boolean;
    http_timeout_seconds: number;
    http_max_response_bytes: number;
    http_max_redirects: number;
  };
};

type DashboardData = {
  systemStatus: SystemStatus | null;
  tools: ToolSummary[];
  approvals: ApprovalReview[];
  patches: PatchProposal[];
  auditEvents: AuditEvent[];
  verification: AuditVerification | null;
};

class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem(TOKEN_STORAGE_KEY) ?? "");
  const [draftToken, setDraftToken] = useState(token);
  const [data, setData] = useState<DashboardData>({
    systemStatus: null,
    tools: [],
    approvals: [],
    patches: [],
    auditEvents: [],
    verification: null,
  });
  const [selectedProposalId, setSelectedProposalId] = useState<string | null>(null);
  const [selectedProposal, setSelectedProposal] = useState<PatchProposal | null>(null);
  const [selectedToolName, setSelectedToolName] = useState("");
  const [argumentsJson, setArgumentsJson] = useState("{}");
  const [principalJson, setPrincipalJson] = useState(
    '{"id":"admin:local-ui","roles":["Admin"]}',
  );
  const [previewResult, setPreviewResult] = useState<PolicyPreviewResult | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [candidatePolicyYaml, setCandidatePolicyYaml] = useState(
    "version: candidate-v1\nrules: []\n",
  );
  const [impactResult, setImpactResult] = useState<PolicyImpactResult | null>(null);
  const [impactLoading, setImpactLoading] = useState(false);
  const [impactError, setImpactError] = useState<string | null>(null);
  const [denyReasons, setDenyReasons] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pendingCount = data.approvals.length;
  const proposedPatchCount = data.patches.filter((patch) => patch.status === "proposed").length;
  const recentFailures = data.auditEvents.filter((event) => event.event_type.endsWith(".failed"));
  const securityWarnings = data.systemStatus?.security.warnings ?? [];

  const selectedPatchFromList = useMemo(
    () => data.patches.find((patch) => patch.proposal_id === selectedProposalId) ?? null,
    [data.patches, selectedProposalId],
  );
  const selectedTool = useMemo(
    () => data.tools.find((tool) => tool.name === selectedToolName) ?? null,
    [data.tools, selectedToolName],
  );

  async function loadDashboard(activeToken = token) {
    if (!activeToken) {
      setData({
        systemStatus: null,
        tools: [],
        approvals: [],
        patches: [],
        auditEvents: [],
        verification: null,
      });
      setSelectedProposal(null);
      setPreviewResult(null);
      setImpactResult(null);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const [
        systemStatus,
        toolsResponse,
        approvalsResponse,
        patchesResponse,
        auditResponse,
        verificationResponse,
      ] = await Promise.all([
        apiRequest<SystemStatus>("/system/status", activeToken),
        apiRequest<{ tools: ToolSummary[] }>("/tools", activeToken),
        apiRequest<{ approvals: ApprovalReview[] }>("/approvals/review?status=pending", activeToken),
        apiRequest<{ patch_proposals: PatchProposal[] }>("/patch-proposals", activeToken),
        apiRequest<{ audit_events: AuditEvent[] }>("/audit-events?limit=100", activeToken),
        apiRequest<AuditVerification>("/audit-events/verify", activeToken),
      ]);
      setData({
        systemStatus,
        tools: toolsResponse.tools,
        approvals: approvalsResponse.approvals,
        patches: patchesResponse.patch_proposals,
        auditEvents: auditResponse.audit_events,
        verification: verificationResponse,
      });
      if (!selectedToolName && toolsResponse.tools[0]) {
        setSelectedToolName(toolsResponse.tools[0].name);
      }
      if (!selectedProposalId && patchesResponse.patch_proposals[0]) {
        setSelectedProposalId(patchesResponse.patch_proposals[0].proposal_id);
      }
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }

  async function loadProposalDetail(proposalId: string, activeToken = token) {
    if (!activeToken) {
      return;
    }
    setDetailLoading(true);
    setError(null);
    try {
      const proposal = await apiRequest<PatchProposal>(
        `/patch-proposals/${encodeURIComponent(proposalId)}`,
        activeToken,
      );
      setSelectedProposal(proposal);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setDetailLoading(false);
    }
  }

  function saveToken(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextToken = draftToken.trim();
    setToken(nextToken);
    if (nextToken) {
      sessionStorage.setItem(TOKEN_STORAGE_KEY, nextToken);
      void loadDashboard(nextToken);
    } else {
      sessionStorage.removeItem(TOKEN_STORAGE_KEY);
      setData({
        systemStatus: null,
        tools: [],
        approvals: [],
        patches: [],
        auditEvents: [],
        verification: null,
      });
      setSelectedProposal(null);
      setPreviewResult(null);
      setImpactResult(null);
    }
  }

  async function runPolicyPreview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !selectedToolName) {
      return;
    }

    setPreviewLoading(true);
    setPreviewError(null);
    setPreviewResult(null);
    try {
      const parsedArguments = parseJsonObject(argumentsJson, "Arguments");
      const parsedPrincipal = parseJsonObject(principalJson, "Principal");
      const result = await apiRequest<PolicyPreviewResult>("/policy/preview", token, {
        method: "POST",
        body: JSON.stringify({
          tool_name: selectedToolName,
          arguments: parsedArguments,
          principal: parsedPrincipal,
        }),
      });
      setPreviewResult(result);
    } catch (caught) {
      setPreviewError(errorMessage(caught));
    } finally {
      setPreviewLoading(false);
    }
  }

  async function runPolicyImpact(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) {
      return;
    }

    setImpactLoading(true);
    setImpactError(null);
    setImpactResult(null);
    try {
      const result = await apiRequest<PolicyImpactResult>("/policy/impact-preview", token, {
        method: "POST",
        body: JSON.stringify({ candidate_policy_yaml: candidatePolicyYaml }),
      });
      setImpactResult(result);
    } catch (caught) {
      setImpactError(errorMessage(caught));
    } finally {
      setImpactLoading(false);
    }
  }

  async function exportAuditBundle(signed = false) {
    setExportLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/audit-events/export${signed ? "/signed" : ""}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        const detail = await response.text();
        throw new ApiError(response.status, detail || response.statusText);
      }
      const bundle = await response.blob();
      const objectUrl = URL.createObjectURL(bundle);
      const anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = signed
        ? "ithildin-audit-export-signed.json"
        : "ithildin-audit-export.jsonl";
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(objectUrl);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setExportLoading(false);
    }
  }

  async function decideApproval(approvalId: string, action: "approve" | "deny") {
    setError(null);
    try {
      await apiRequest<Approval>(`/approvals/${approvalId}/${action}`, token, {
        method: "POST",
        body: JSON.stringify({
          decision: action,
          decided_by: DECIDED_BY,
          reason: action === "deny" ? denyReasons[approvalId] || undefined : undefined,
        }),
      });
      setDenyReasons((current) => {
        const next = { ...current };
        delete next[approvalId];
        return next;
      });
      await loadDashboard();
    } catch (caught) {
      setError(errorMessage(caught));
    }
  }

  useEffect(() => {
    void loadDashboard();
  }, []);

  useEffect(() => {
    if (selectedProposalId) {
      void loadProposalDetail(selectedProposalId);
    } else {
      setSelectedProposal(null);
    }
  }, [selectedProposalId, token]);

  return (
    <main className="console-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Ithildin</p>
          <h1>Review Console</h1>
        </div>
        <form className="token-form" onSubmit={saveToken}>
          <label htmlFor="admin-token">Admin token</label>
          <div className="token-row">
            <KeyRound aria-hidden="true" size={18} />
            <input
              id="admin-token"
              type="password"
              value={draftToken}
              onChange={(event) => setDraftToken(event.target.value)}
              autoComplete="off"
            />
            <button type="submit">
              <ShieldCheck aria-hidden="true" size={18} />
              Save
            </button>
          </div>
        </form>
      </header>

      {error ? (
        <section className="notice error" role="alert">
          <AlertTriangle aria-hidden="true" size={18} />
          <span>{error}</span>
        </section>
      ) : null}

      {!token ? (
        <section className="notice">
          <KeyRound aria-hidden="true" size={18} />
          <span>Admin token required.</span>
        </section>
      ) : null}

      {loading && token ? (
        <section className="notice">
          <RefreshCcw aria-hidden="true" size={18} />
          <span>Refreshing console data.</span>
        </section>
      ) : null}

      {securityWarnings.length > 0 ? (
        <section className="notice warning" role="alert">
          <AlertTriangle aria-hidden="true" size={18} />
          <span>{securityWarnings.join(" · ")}</span>
        </section>
      ) : null}

      <section className="summary-strip" aria-label="Review summary">
        <Metric icon={<ClipboardList size={20} />} label="Pending" value={pendingCount} />
        <Metric icon={<FileDiff size={20} />} label="Proposed patches" value={proposedPatchCount} />
        <Metric icon={<AlertTriangle size={20} />} label="Recent failures" value={recentFailures.length} />
        <button className="refresh-button" type="button" onClick={() => void loadDashboard()}>
          <RefreshCcw aria-hidden="true" size={18} />
          {loading ? "Refreshing" : "Refresh"}
        </button>
      </section>

      <section className="trust-grid">
        <Panel title="System Trust" icon={<ShieldCheck size={18} />}>
          {data.systemStatus ? (
            <div className="trust-panel">
              <div className="trust-heading">
                <span
                  className={
                    data.systemStatus.audit.valid
                      ? "integrity-indicator valid"
                      : "integrity-indicator invalid"
                  }
                >
                  {data.systemStatus.audit.valid ? "Verified" : "Attention required"}
                </span>
                <span className="trust-service">{data.systemStatus.service}</span>
              </div>
              <dl className="meta-list trust-list">
                <div>
                  <dt>Manifest Lock</dt>
                  <dd>{data.systemStatus.manifest_lock.required ? "enforced" : "optional"}</dd>
                </div>
                <div>
                  <dt>Lock Signature</dt>
                  <dd>
                    {data.systemStatus.manifest_lock.signature.verified
                      ? shortHash(data.systemStatus.manifest_lock.signature.key_id ?? "")
                      : data.systemStatus.manifest_lock.signature.required
                        ? "required"
                        : "optional"}
                  </dd>
                </div>
                <div>
                  <dt>Policy</dt>
                  <dd>{data.systemStatus.policy.engine}</dd>
                </div>
                <div>
                  <dt>Policy Hash</dt>
                  <dd>{shortHash(data.systemStatus.policy.policy_hash)}</dd>
                </div>
                <div>
                  <dt>OPA Bundle</dt>
                  <dd>{data.systemStatus.policy.bundle_verified ? "verified" : "not active"}</dd>
                </div>
                <div>
                  <dt>Audit Head</dt>
                  <dd>{shortHash(data.systemStatus.audit.head_hash)}</dd>
                </div>
                <div>
                  <dt>Audit Signing</dt>
                  <dd>
                    {data.systemStatus.audit_signing.signed_export_available
                      ? shortHash(data.systemStatus.audit_signing.key_id ?? "")
                      : "not configured"}
                  </dd>
                </div>
                <div>
                  <dt>Redaction</dt>
                  <dd>
                    {data.systemStatus.redaction.baseline_enabled
                      ? `${data.systemStatus.redaction.extra_key_count + data.systemStatus.redaction.extra_pattern_count} extra`
                      : "disabled"}
                  </dd>
                </div>
                <div>
                  <dt>Tools</dt>
                  <dd>{data.systemStatus.tool_count}</dd>
                </div>
                <div>
                  <dt>Candidate</dt>
                  <dd>{data.systemStatus.security.preview_label}</dd>
                </div>
                <div>
                  <dt>Dev Token</dt>
                  <dd>
                    {data.systemStatus.security.dev_admin_token.sample_token_active
                      ? "enabled"
                      : "not active"}
                  </dd>
                </div>
                <div>
                  <dt>Admin Token</dt>
                  <dd>{data.systemStatus.security.admin_token.weak ? "review" : "ok"}</dd>
                </div>
                <div>
                  <dt>CORS</dt>
                  <dd>
                    {data.systemStatus.security.cors.wildcard_allowed
                      ? "wildcard"
                      : "local only"}
                  </dd>
                </div>
                <div>
                  <dt>Read Limit</dt>
                  <dd>{formatBytes(data.systemStatus.limits.max_read_bytes)}</dd>
                </div>
                <div>
                  <dt>Patch Limit</dt>
                  <dd>{formatBytes(data.systemStatus.limits.max_patch_bytes)}</dd>
                </div>
                <div>
                  <dt>HTTP</dt>
                  <dd>
                    {data.systemStatus.limits.http_allowlist_configured
                      ? "allowlist set"
                      : "allowlist empty"}
                  </dd>
                </div>
              </dl>
            </div>
          ) : (
            <EmptyState text={token ? "System status unavailable." : "Locked."} />
          )}
        </Panel>

        <Panel title="Registered Tools" icon={<ClipboardList size={18} />}>
          {data.tools.length === 0 ? (
            <EmptyState text={token ? "No registered tools." : "Locked."} />
          ) : (
            <div className="table-wrap compact-table">
              <table>
                <thead>
                  <tr>
                    <th>Tool</th>
                    <th>Risk</th>
                    <th>Category</th>
                    <th>Version</th>
                    <th>Manifest</th>
                    <th>MCP</th>
                  </tr>
                </thead>
                <tbody>
                  {data.tools.map((tool) => (
                    <tr key={tool.name}>
                      <td>{tool.name}</td>
                      <td>
                        <StatusPill status={tool.risk} />
                      </td>
                      <td>{tool.category}</td>
                      <td>{tool.version}</td>
                      <td>{shortHash(tool.manifest_hash)}</td>
                      <td>{tool.mcp.exposed === true ? "yes" : "no"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      </section>

      <section className="policy-section">
        <Panel title="Policy Preview" icon={<ShieldCheck size={18} />}>
          <form className="policy-preview-form" onSubmit={runPolicyPreview}>
            <div className="policy-controls">
              <label>
                <span>Tool</span>
                <select
                  value={selectedToolName}
                  disabled={!token || data.tools.length === 0}
                  onChange={(event) => {
                    setSelectedToolName(event.target.value);
                    setPreviewResult(null);
                    setPreviewError(null);
                  }}
                >
                  {data.tools.map((tool) => (
                    <option key={tool.name} value={tool.name}>
                      {tool.name} · {tool.risk} · {tool.category}
                    </option>
                  ))}
                </select>
              </label>
              <button
                className="primary-action"
                type="submit"
                disabled={!token || !selectedToolName || previewLoading}
              >
                <ShieldCheck aria-hidden="true" size={16} />
                {previewLoading ? "Previewing" : "Preview"}
              </button>
            </div>
            <div className="json-editors">
              <label>
                <span>Arguments</span>
                <textarea
                  value={argumentsJson}
                  onChange={(event) => setArgumentsJson(event.target.value)}
                  spellCheck={false}
                />
              </label>
              <label>
                <span>Principal</span>
                <textarea
                  value={principalJson}
                  onChange={(event) => setPrincipalJson(event.target.value)}
                  spellCheck={false}
                />
              </label>
            </div>
          </form>
          {previewError ? (
            <div className="inline-error">
              <AlertTriangle aria-hidden="true" size={16} />
              <span>{previewError}</span>
            </div>
          ) : null}
          {!token ? <EmptyState text="Locked." /> : null}
          {token && data.tools.length === 0 ? <EmptyState text="No registered tools." /> : null}
          {previewResult ? (
            <div className="preview-result">
              <div className="preview-heading">
                <div>
                  <h3>{previewResult.tool_name}</h3>
                  <p>{selectedTool?.title ?? previewResult.manifest_version ?? ""}</p>
                </div>
                <StatusPill status={previewResult.decision} />
              </div>
              <dl className="meta-list preview-meta">
                <div>
                  <dt>Arguments</dt>
                  <dd>{previewResult.valid_arguments ? "valid" : "invalid"}</dd>
                </div>
                <div>
                  <dt>Risk</dt>
                  <dd>{previewResult.manifest_risk ?? "unknown"}</dd>
                </div>
                <div>
                  <dt>Manifest</dt>
                  <dd>{previewResult.manifest_hash ? shortHash(previewResult.manifest_hash) : ""}</dd>
                </div>
              </dl>
              <p className="preview-reason">{previewResult.reason}</p>
              {previewResult.argument_error ? (
                <p className="preview-argument-error">{previewResult.argument_error}</p>
              ) : null}
              <div className="preview-detail-grid">
                <div>
                  <h3>Matched Rules</h3>
                  <pre>{JSON.stringify(previewResult.matched_rules, null, 2)}</pre>
                </div>
                <div>
                  <h3>Obligations</h3>
                  <pre>{JSON.stringify(previewResult.obligations, null, 2)}</pre>
                </div>
                <div>
                  <h3>Resource</h3>
                  <pre>{JSON.stringify(previewResult.resource, null, 2)}</pre>
                </div>
              </div>
            </div>
          ) : null}
        </Panel>

        <Panel title="Policy Impact" icon={<FileDiff size={18} />}>
          <form className="policy-preview-form" onSubmit={runPolicyImpact}>
            <div className="policy-controls">
              <label>
                <span>Candidate YAML</span>
                <textarea
                  value={candidatePolicyYaml}
                  onChange={(event) => setCandidatePolicyYaml(event.target.value)}
                  spellCheck={false}
                />
              </label>
              <button
                className="primary-action"
                type="submit"
                disabled={!token || impactLoading}
              >
                <FileDiff aria-hidden="true" size={16} />
                {impactLoading ? "Comparing" : "Compare"}
              </button>
            </div>
          </form>
          {impactError ? (
            <div className="inline-error">
              <AlertTriangle aria-hidden="true" size={16} />
              <span>{impactError}</span>
            </div>
          ) : null}
          {!token ? <EmptyState text="Locked." /> : null}
          {impactResult ? (
            <div className="preview-result">
              <div className="preview-heading">
                <div>
                  <h3>{impactResult.changed_cases.length} changed cases</h3>
                  <p>{shortHash(impactResult.candidate.policy_hash)}</p>
                </div>
                <StatusPill status={impactResult.candidate.failed === 0 ? "allow" : "deny"} />
              </div>
              <dl className="meta-list preview-meta">
                <div>
                  <dt>Current</dt>
                  <dd>
                    {impactResult.current.passed}/{impactResult.current.case_count}
                  </dd>
                </div>
                <div>
                  <dt>Candidate</dt>
                  <dd>
                    {impactResult.candidate.passed}/{impactResult.candidate.case_count}
                  </dd>
                </div>
                <div>
                  <dt>Failures</dt>
                  <dd>{impactResult.candidate.failed}</dd>
                </div>
              </dl>
              {impactResult.changed_cases.length === 0 ? (
                <EmptyState text="No fixture-visible policy impact." />
              ) : (
                <div className="table-wrap compact-table">
                  <table>
                    <thead>
                      <tr>
                        <th>Case</th>
                        <th>Changes</th>
                        <th>Current</th>
                        <th>Candidate</th>
                      </tr>
                    </thead>
                    <tbody>
                      {impactResult.changed_cases.map((changed) => (
                        <tr key={changed.id}>
                          <td>{changed.id}</td>
                          <td>{changed.changes.join(", ")}</td>
                          <td>{changed.current ? scopeString(changed.current, "decision") : ""}</td>
                          <td>{scopeString(changed.candidate, "decision")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ) : null}
        </Panel>
      </section>

      <section className="integrity-section">
        <Panel title="Audit Integrity" icon={<ShieldCheck size={18} />}>
          <div className="integrity-grid">
            <div className="integrity-status">
              {data.verification ? (
                <>
                  <span
                    className={
                      data.verification.valid
                        ? "integrity-indicator valid"
                        : "integrity-indicator invalid"
                    }
                  >
                    {data.verification.valid ? "Verified" : "Attention required"}
                  </span>
                  <dl className="meta-list">
                    <div>
                      <dt>Events</dt>
                      <dd>{data.verification.event_count}</dd>
                    </div>
                    <div>
                      <dt>Head hash</dt>
                      <dd>{shortHash(data.verification.head_hash)}</dd>
                    </div>
                    <div>
                      <dt>Last event</dt>
                      <dd>
                        {data.verification.last_timestamp
                          ? formatDate(data.verification.last_timestamp)
                          : "None"}
                      </dd>
                    </div>
                  </dl>
                  {data.verification.failure ? (
                    <p className="integrity-failure">
                      Row {data.verification.failure.row_number}:{" "}
                      {data.verification.failure.reason}
                    </p>
                  ) : null}
                </>
              ) : (
                <EmptyState text={token ? "Verification unavailable." : "Locked."} />
              )}
            </div>
            <div className="export-actions">
              <button
                className="export-button"
                type="button"
                disabled={!token || exportLoading}
                onClick={() => void exportAuditBundle()}
              >
                <Download aria-hidden="true" size={18} />
                {exportLoading ? "Exporting" : "Export JSONL"}
              </button>
              <button
                className="export-button"
                type="button"
                disabled={
                  !token ||
                  exportLoading ||
                  !data.systemStatus?.audit_signing.signed_export_available
                }
                onClick={() => void exportAuditBundle(true)}
              >
                <KeyRound aria-hidden="true" size={18} />
                {exportLoading ? "Exporting" : "Export Signed"}
              </button>
            </div>
          </div>
        </Panel>
      </section>

      <section className="review-grid">
        <Panel title="Pending Approvals" icon={<ClipboardList size={18} />}>
          {data.approvals.length === 0 ? (
            <EmptyState text={token ? "No pending approvals." : "Locked."} />
          ) : (
            <div className="approval-list">
              {data.approvals.map((approvalReview) => {
                const approval = approvalReview.approval;
                return (
                <article className="approval-item" key={approval.approval_id}>
                  <div className="item-heading">
                    <div>
                      <h3>{approval.summary}</h3>
                      <p>{approval.tool_name}</p>
                    </div>
                    <StatusPill status={approvalReview.review.valid ? approval.status : "stale"} />
                  </div>
                  <dl className="meta-list">
                    <div>
                      <dt>Approval</dt>
                      <dd>{shortId(approval.approval_id)}</dd>
                    </div>
                    <div>
                      <dt>Request</dt>
                      <dd>{shortId(approval.request_id)}</dd>
                    </div>
                    <div>
                      <dt>Expires</dt>
                      <dd>{formatDate(approval.expires_at)}</dd>
                    </div>
                    <div>
                      <dt>Workspace</dt>
                      <dd>{scopeString(approval.one_time_scope, "workspace_id") || "default"}</dd>
                    </div>
                  </dl>
                  <BindingReviewSummary review={approvalReview.review} />
                  <ApprovalEvidence approval={approval} />
                  <div className="decision-row">
                    <input
                      aria-label={`Deny reason for ${approval.approval_id}`}
                      placeholder="Deny reason"
                      value={denyReasons[approval.approval_id] ?? ""}
                      onChange={(event) =>
                        setDenyReasons((current) => ({
                          ...current,
                          [approval.approval_id]: event.target.value,
                        }))
                      }
                    />
                    <button type="button" onClick={() => void decideApproval(approval.approval_id, "deny")}>
                      <X aria-hidden="true" size={16} />
                      Deny
                    </button>
                    <button
                      className="primary-action"
                      type="button"
                      disabled={!approvalReview.review.valid}
                      onClick={() => void decideApproval(approval.approval_id, "approve")}
                    >
                      <Check aria-hidden="true" size={16} />
                      Approve
                    </button>
                  </div>
                </article>
                );
              })}
            </div>
          )}
        </Panel>

        <Panel title="Patch Proposals" icon={<FileDiff size={18} />}>
          <div className="patch-layout">
            <div className="patch-list">
              {data.patches.length === 0 ? (
                <EmptyState text={token ? "No patch proposals." : "Locked."} />
              ) : (
                data.patches.map((patch) => (
                  <button
                    className={patch.proposal_id === selectedProposalId ? "patch-row selected" : "patch-row"}
                    key={patch.proposal_id}
                    type="button"
                    onClick={() => setSelectedProposalId(patch.proposal_id)}
                  >
                    <span>{patch.path}</span>
                    <small>{patch.workspace_id}</small>
                    <StatusPill status={patch.status} />
                  </button>
                ))
              )}
            </div>
            <div className="diff-view">
              {detailLoading ? (
                <EmptyState text="Loading diff." />
              ) : selectedProposal ? (
                <>
                  <div className="diff-heading">
                    <div>
                      <h3>{selectedProposal.path}</h3>
                      <p>
                        {shortId(selectedProposal.proposal_id)} · {selectedProposal.workspace_id}
                      </p>
                    </div>
                    <StatusPill
                      status={
                        selectedProposal.review?.stale === true
                          ? "stale"
                          : selectedProposal.status
                      }
                    />
                  </div>
                  {selectedProposal.review ? (
                    <BindingReviewSummary review={selectedProposal.review as BindingReview} />
                  ) : null}
                  <pre>{selectedProposal.unified_diff ?? ""}</pre>
                </>
              ) : selectedPatchFromList ? (
                <EmptyState text={selectedPatchFromList.path} />
              ) : (
                <EmptyState text={token ? "Select a proposal." : "Locked."} />
              )}
            </div>
          </div>
        </Panel>
      </section>

      <section className="audit-section">
        <Panel title="Recent Audit Events" icon={<Activity size={18} />}>
          {data.auditEvents.length === 0 ? (
            <EmptyState text={token ? "No recent audit events." : "Locked."} />
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Event</th>
                    <th>Tool</th>
                    <th>Decision</th>
                    <th>Redactions</th>
                    <th>Request</th>
                    <th>Hash</th>
                  </tr>
                </thead>
                <tbody>
                  {data.auditEvents.map((event) => (
                    <tr key={event.event_id}>
                      <td>{formatDate(event.timestamp)}</td>
                      <td>{event.event_type}</td>
                      <td>{event.tool_name ?? ""}</td>
                      <td>{event.decision ?? ""}</td>
                      <td title={redactionTitle(event)}>{redactionCount(event)}</td>
                      <td>{shortId(event.request_id)}</td>
                      <td>{shortHash(event.event_hash)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      </section>
    </main>
  );
}

function Metric({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
}) {
  return (
    <div className="metric">
      <span className="metric-icon">{icon}</span>
      <span className="metric-value">{value}</span>
      <span className="metric-label">{label}</span>
    </div>
  );
}

function Panel({
  title,
  icon,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="panel">
      <header className="panel-header">
        {icon}
        <h2>{title}</h2>
      </header>
      {children}
    </section>
  );
}

function EmptyState({ text }: { text: string }) {
  return <div className="empty-state">{text}</div>;
}

function StatusPill({ status }: { status: string }) {
  return <span className={`status-pill status-${status}`}>{status}</span>;
}

function ApprovalEvidence({ approval }: { approval: Approval }) {
  const scope = approval.one_time_scope;
  const evidence = [
    ["Proposal", scopeString(scope, "proposal_id")],
    ["Proposal hash", scopeString(scope, "proposal_hash")],
    ["Base hash", scopeString(scope, "base_file_hash")],
    ["Target", scopeString(scope, "path")],
    ["Manifest hash", scopeString(scope, "manifest_hash")],
    ["Manifest version", scopeString(scope, "manifest_version")],
    ["Policy engine", scopeString(scope, "policy_engine")],
    ["Policy hash", scopeString(scope, "policy_hash")],
    ["Policy version", scopeString(scope, "policy_version")],
    ["Policy doc", scopeString(scope, "policy_document_version")],
    ["Matched rules", scopeList(scope, "matched_rules").join(", ")],
    ["Principal", formatJsonCompact(scopeObject(scope, "requesting_principal") ?? approval.principal)],
    ["Request hash", scopeString(scope, "request_hash") || approval.request_hash],
    ["Expires", scopeString(scope, "expires_at") || approval.expires_at],
    ["Input schema", scopeString(scope, "tool_input_schema_hash")],
  ].filter((entry): entry is [string, string] => Boolean(entry[1]));

  if (evidence.length === 0) {
    return null;
  }

  return (
    <section className="evidence-block" aria-label={`Approval evidence for ${approval.approval_id}`}>
      <h4>Binding Evidence</h4>
      <dl className="evidence-grid">
        {evidence.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd title={value}>{formatEvidenceValue(value)}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function BindingReviewSummary({
  review,
}: {
  review: Partial<BindingReview> & PatchReview;
}) {
  const reasons = review.reasons ?? [];
  const checks = review.checks ?? {};
  const valid = review.valid ?? !review.stale;
  const failureText = reasons.join("; ") || review.stale_reason || "";

  return (
    <section className="evidence-block" aria-label="Binding review">
      <h4>{valid ? "Review Checks Passed" : "Review Attention"}</h4>
      {failureText ? <p className="preview-argument-error">{failureText}</p> : null}
      {Object.keys(checks).length > 0 ? (
        <dl className="evidence-grid">
          {Object.entries(checks).map(([label, passed]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{passed ? "ok" : "check"}</dd>
            </div>
          ))}
        </dl>
      ) : null}
    </section>
  );
}

async function apiRequest<T>(
  path: string,
  token: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = (await response.json()) as { detail?: string };
      detail = payload.detail ?? detail;
    } catch {
      // Fall back to the HTTP status text.
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}

function parseJsonObject(raw: string, label: string): JsonObject {
  const parsed = JSON.parse(raw) as unknown;
  if (!isJsonObject(parsed)) {
    throw new Error(`${label} must be a JSON object.`);
  }
  return parsed;
}

function isJsonObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function scopeString(scope: JsonObject, key: string) {
  const value = scope[key];
  return typeof value === "string" ? value : "";
}

function scopeList(scope: JsonObject, key: string) {
  const value = scope[key];
  return Array.isArray(value) && value.every((item) => typeof item === "string")
    ? value
    : [];
}

function scopeObject(scope: JsonObject, key: string) {
  const value = scope[key];
  return isJsonObject(value) ? value : null;
}

function formatJsonCompact(value: JsonObject) {
  return JSON.stringify(value);
}

function formatEvidenceValue(value: string) {
  if (value.startsWith("sha256:")) {
    return shortHash(value);
  }
  if (value.length > 42) {
    return `${value.slice(0, 24)}...${value.slice(-12)}`;
  }
  return value;
}

function redactionCount(event: AuditEvent) {
  const count = event.metadata.redaction_count;
  return typeof count === "number" ? String(count) : "";
}

function redactionTitle(event: AuditEvent) {
  const paths = event.metadata.redaction_paths;
  if (!Array.isArray(paths) || paths.length === 0) {
    return "No redaction paths recorded";
  }
  const safePaths = paths.filter((path): path is string => typeof path === "string");
  return safePaths.length > 0 ? safePaths.join(", ") : "No redaction paths recorded";
}

function errorMessage(caught: unknown) {
  if (caught instanceof ApiError) {
    if (caught.status === 401 || caught.status === 403) {
      return "Admin token rejected.";
    }
    return caught.message;
  }
  if (caught instanceof Error) {
    return caught.message;
  }
  return "Request failed.";
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "short",
    timeStyle: "medium",
  }).format(new Date(value));
}

function shortId(value: string) {
  if (value.length <= 18) {
    return value;
  }
  return `${value.slice(0, 9)}...${value.slice(-6)}`;
}

function shortHash(value: string) {
  return value.replace("sha256:", "").slice(0, 12);
}

function formatBytes(value: number) {
  return new Intl.NumberFormat(undefined, {
    maximumFractionDigits: 1,
    notation: value >= 1_000_000 ? "compact" : "standard",
  }).format(value);
}

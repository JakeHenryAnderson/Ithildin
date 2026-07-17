import {
  Activity,
  AlertTriangle,
  BellRing,
  Boxes,
  Check,
  CircleHelp,
  ClipboardList,
  Copy,
  Download,
  FileDiff,
  FolderKanban,
  KeyRound,
  ListChecks,
  RefreshCcw,
  ScrollText,
  Server,
  Settings,
  ShieldCheck,
  X,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

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
  policy_version: string | null;
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

type AgentRun = {
  run_id: string;
  principal_id: string;
  principal_type: string;
  principal_roles: string[];
  workspace_id: string;
  session_id: string;
  status: string;
  tool_call_count: number;
  created_at: string;
  updated_at: string;
  last_request_id: string | null;
  policy_hash: string | null;
  last_tool_name: string | null;
  last_tool_manifest_hash: string | null;
  metadata: JsonObject;
};

type IthildinNode = {
  node_id: string;
  principal_id: string;
  workspace_id: string;
  display_name: string;
  status: string;
  evidence_status: string;
  observed_state: string;
  descriptor_hash: string;
  descriptor: JsonObject;
  enrolled_at: string;
  updated_at: string;
  last_seen_at: string | null;
  revoked_at: string | null;
  last_heartbeat_hash: string | null;
  last_observed_node_version: string | null;
  last_configuration_digest: string | null;
  last_mission_id: string | null;
  configuration_state: string;
  desired_configuration_generation: number | null;
  desired_configuration_digest: string | null;
  acknowledged_configuration_generation: number | null;
  acknowledged_configuration_digest: string | null;
  configuration_acknowledged_at: string | null;
  configuration_acknowledgment_status: string | null;
  acknowledged_configuration_signing_key_id: string | null;
  acknowledged_active_configuration_signing_key_id: string | null;
  configuration_signing_key_id: string | null;
  configuration_trust_transition: NodeConfigurationTrustTransition | null;
  active_identity_key_id: string;
  identity_key_rotation: NodeIdentityKeyRotation | null;
  minimum_node_version: string | null;
  version_posture: string;
  version_desired_source: string;
  version_observed_source: string;
  maintenance_control_source: "operator_managed";
  package_authenticity_known: false;
  self_update_allowed: false;
  identity_source: "gateway_derived";
  connectivity_source: "gateway_accepted_heartbeat";
  runner_health_known: false;
  model_health_known: false;
};

type NodeIdentityKeyRotation = {
  rotation_id: string;
  current_key_id: string;
  next_key_id: string | null;
  created_at: string;
  expires_at: string;
  activated_at: string | null;
  status: string;
  evidence_status: string;
  private_key_received: false;
  retired_key_request_authority: false;
};

type NodeConfigurationTrustTransition = {
  transition_id: string;
  transition_digest: string;
  current_key_id: string;
  next_key_id: string;
  issued_at: string;
  expires_at: string;
  evidence_status: string;
  acknowledgment_status: string | null;
  acknowledgment_evidence_status: string | null;
  acknowledged_at: string | null;
  gateway_key_id: string | null;
  node_acknowledged_key_id: string | null;
  rotation_state: string;
  activation_proven: boolean;
  enforcement_proven: false;
};

type NodeConfigurationHistoryItem = {
  configuration_id: string;
  generation: number;
  configuration_digest: string;
  issued_at: string;
  expires_at: string;
  evidence_status: string;
  assignment_kind: string;
  rollback_source_generation: number | null;
  configuration: JsonObject;
  is_desired: boolean;
};

type AgentRunSummary = {
  returned: number;
  filters: JsonObject;
  workspaces: Record<string, number>;
  principals: Record<string, number>;
  statuses: Record<string, number>;
  tools: Record<string, number>;
  latest_updated_at: string | null;
};

type AgentRunTimelineEvent = {
  event_id: string;
  timestamp: string;
  event_type: string;
  request_id: string;
  tool_name?: string | null;
  decision?: string | null;
  event_hash: string;
  resource: JsonObject | null;
  metadata: JsonObject;
};

type AgentRunDetail = {
  run: AgentRun;
  timeline: AgentRunTimelineEvent[];
};

type RunEvidenceExport = {
  schema_version: string;
  export_id: string;
  exported_at: string;
  run: JsonObject;
  summary: {
    principal_id: string;
    workspace_id: string;
    session_id: string;
    status: string;
    tool_call_count: number;
    tools_used: string[];
    decision_counts: Record<string, number>;
    approval_count: number;
    patch_diagnostic_count: number;
    audit_event_count: number;
    warning_count: number;
    latest_policy_hash: string | null;
    manifest_lock_hash: string | null;
  };
  timeline: JsonObject[];
  approvals: JsonObject[];
  patch_diagnostics: JsonObject[];
  signed_export_references: JsonObject[];
  evidence_hashes: JsonObject;
  redaction_summary: { excluded_categories: string[] };
  warnings: JsonObject[];
};

type ExportNotice = {
  scope: "audit" | "run" | "signed-audit";
  runId?: string;
  state: "download-initiated" | "failed";
  message: string;
};

type RunFilters = {
  principal_id: string;
  workspace_id: string;
  status: string;
  tool_name: string;
};

type InvestigationFilters = {
  time_range: string;
  mission: string;
  decision: string;
  outcome: string;
  attention: string;
};

type WorkspaceLens = "routine" | "investigator" | "policy" | "technical";

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

type PatchApplyDiagnostics = {
  status: "clean" | "recovery_required" | "ambiguous" | string;
  attempts: JsonObject[];
  stuck_approvals: JsonObject[];
  recommendations: JsonObject[];
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
  agent_runs: {
    enabled: boolean;
    count: number;
    status: string;
  };
  principals: {
    required: boolean;
    path: string;
    count: number;
    enabled_count: number;
  };
  workspaces: {
    required: boolean;
    path: string;
    default_workspace_id: string;
    count: number;
    enabled_count: number;
  };
  storage: {
    runtime_backend: string;
    runtime_enabled: boolean;
    postgres: {
      configured: boolean;
      runtime_enabled: boolean;
      readiness: string;
    };
  };
  telemetry: {
    enabled: boolean;
    service_name: string;
    exporters: string[];
  };
  audit_signing: {
    algorithm: string;
    private_key_configured: boolean;
    public_key_configured: boolean;
    signed_export_available: boolean;
    key_id: string | null;
    error?: string;
  };
  filesystem: {
    platform: {
      system: string;
      profile: string;
      release: string;
      machine: string;
    };
    python: {
      version: string;
    };
    capabilities: {
      o_no_follow_available: boolean;
      symlink_supported: boolean;
      hardlink_supported: boolean;
      case_sensitive: boolean;
    };
    support: {
      status: "supported" | "degraded" | "unsupported" | string;
      local_preview_security_supported: boolean;
      reason: string;
    };
    probe: {
      uses_temporary_directory: boolean;
      touches_workspace: boolean;
    };
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
  approvalHistory: Approval[];
  patches: PatchProposal[];
  patchDiagnostics: PatchApplyDiagnostics | null;
  runs: AgentRun[];
  nodes: IthildinNode[];
  runSummary: AgentRunSummary | null;
  auditEvents: AuditEvent[];
  verification: AuditVerification | null;
};

type AttentionItem = {
  source: "approval" | "failure" | "recovery" | "proposal" | "node";
  title: string;
  status: string;
  bindingStatus: string | null;
  consequence: string;
  missionLabel: string;
  workspaceId: string;
  requestingIdentity: string;
  toolName: string;
  requestId: string;
  policyReason: string;
  runId: string | null;
  proposalId: string | null;
  nodeId: string | null;
  targetId: "missions" | "approvals" | "artifacts" | "evidence" | "nodes";
  actionLabel: string;
  occurredAt: string | null;
};

type NodeAttentionClass = "authority" | "operational";

type NodeAttentionPosture = {
  attentionClass: NodeAttentionClass;
  rank: number;
  title: string;
  status: string;
  consequence: string;
  actionLabel: string;
  observedBasis: string;
  occurredAt: string | null;
};

function emptyDashboardData(): DashboardData {
  return {
    systemStatus: null,
    tools: [],
    approvals: [],
    approvalHistory: [],
    patches: [],
    patchDiagnostics: null,
    runs: [],
    nodes: [],
    runSummary: null,
    auditEvents: [],
    verification: null,
  };
}

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
  const [activeSection, setActiveSection] = useState("attention");
  const [selectedAttentionKey, setSelectedAttentionKey] = useState<string | null>(null);
  const [selectedApprovalId, setSelectedApprovalId] = useState<string | null>(null);
  const [workspaceLens, setWorkspaceLens] = useState<WorkspaceLens>("routine");
  const [data, setData] = useState<DashboardData>(emptyDashboardData);
  const [runFilters, setRunFilters] = useState<RunFilters>({
    principal_id: "",
    workspace_id: "",
    status: "",
    tool_name: "",
  });
  const [appliedRunFilters, setAppliedRunFilters] = useState<RunFilters>(runFilters);
  const [investigationFilters, setInvestigationFilters] = useState<InvestigationFilters>({
    time_range: "all",
    mission: "",
    decision: "all",
    outcome: "all",
    attention: "all",
  });
  const [selectedProposalId, setSelectedProposalId] = useState<string | null>(null);
  const [selectedProposal, setSelectedProposal] = useState<PatchProposal | null>(null);
  const [artifactQuery, setArtifactQuery] = useState("");
  const [artifactStatus, setArtifactStatus] = useState("all");
  const [artifactSort, setArtifactSort] = useState("updated-desc");
  const [nodeQuery, setNodeQuery] = useState("");
  const [nodePosture, setNodePosture] = useState("all");
  const [nodeWorkspace, setNodeWorkspace] = useState("all");
  const [nodeSort, setNodeSort] = useState("attention");
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedRun, setSelectedRun] = useState<AgentRunDetail | null>(null);
  const [selectedRunEvidence, setSelectedRunEvidence] = useState<RunEvidenceExport | null>(null);
  const [runEvidenceError, setRunEvidenceError] = useState<string | null>(null);
  const [exportNotice, setExportNotice] = useState<ExportNotice | null>(null);
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
  const [decidingApprovals, setDecidingApprovals] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dashboardError, setDashboardError] = useState<string | null>(null);
  const dashboardRequest = useRef(0);
  const proposalRequest = useRef(0);
  const runDetailRequest = useRef(0);
  const runEvidenceRequest = useRef(0);
  const decidingApprovalIds = useRef(new Set<string>());
  const authGeneration = useRef(0);
  const operationGeneration = useRef(0);

  const pendingCount = data.approvals.length;
  const proposedPatchCount = data.patches.filter((patch) => patch.status === "proposed").length;
  const recentFailures = data.auditEvents.filter((event) => event.event_type.endsWith(".failed"));
  const authRejected = dashboardError === "Admin token rejected.";
  const dashboardUnavailable = Boolean(
    token && !loading && !dashboardError && !data.systemStatus,
  );
  const trustWarnings = useMemo(
    () => trustStateWarnings(data.systemStatus, data.verification, data.patchDiagnostics),
    [data.systemStatus, data.verification, data.patchDiagnostics],
  );
  const attentionItems = useMemo(() => operatorAttentionItems(data), [data]);
  const primaryAttention = useMemo(
    () =>
      attentionItems.find((item) => attentionItemKey(item) === selectedAttentionKey) ??
      attentionItems[0] ??
      null,
    [attentionItems, selectedAttentionKey],
  );
  const selectedApprovalReview = useMemo(
    () =>
      data.approvals.find(
        (candidate) => candidate.approval.approval_id === selectedApprovalId,
      ) ?? data.approvals[0] ?? null,
    [data.approvals, selectedApprovalId],
  );
  const investigationRuns = useMemo(
    () =>
      filterInvestigationRuns(
        data.runs,
        data.auditEvents,
        investigationFilters,
      ),
    [data.runs, data.auditEvents, investigationFilters],
  );

  const selectedPatchFromList = useMemo(
    () => data.patches.find((patch) => patch.proposal_id === selectedProposalId) ?? null,
    [data.patches, selectedProposalId],
  );
  const visiblePatches = useMemo(
    () => filterAndSortPatches(data.patches, artifactQuery, artifactStatus, artifactSort),
    [data.patches, artifactQuery, artifactStatus, artifactSort],
  );
  const groupedPatches = useMemo(() => groupPatchesByWorkspace(visiblePatches), [visiblePatches]);
  const visibleNodes = useMemo(
    () => filterAndSortNodes(data.nodes, nodeQuery, nodePosture, nodeWorkspace, nodeSort),
    [data.nodes, nodePosture, nodeQuery, nodeSort, nodeWorkspace],
  );
  const nodeWorkspaces = useMemo(
    () => [...new Set(data.nodes.map((node) => node.workspace_id))].sort(),
    [data.nodes],
  );
  const selectedProposalApprovals = useMemo(
    () =>
      data.approvalHistory.filter(
        (approval) =>
          scopeString(approval.one_time_scope, "proposal_id") === selectedProposal?.proposal_id,
      ),
    [data.approvalHistory, selectedProposal?.proposal_id],
  );
  const selectedPendingProposalApproval = useMemo(
    () =>
      data.approvals.find(
        (review) =>
          scopeString(review.approval.one_time_scope, "proposal_id") ===
          selectedProposal?.proposal_id,
      ),
    [data.approvals, selectedProposal?.proposal_id],
  );
  const selectedTool = useMemo(
    () => data.tools.find((tool) => tool.name === selectedToolName) ?? null,
    [data.tools, selectedToolName],
  );

  async function loadDashboard(activeToken = token, activeRunFilters = appliedRunFilters) {
    const requestId = ++dashboardRequest.current;
    operationGeneration.current += 1;
    setPreviewResult(null);
    setPreviewError(null);
    setPreviewLoading(false);
    setImpactResult(null);
    setImpactError(null);
    setImpactLoading(false);
    setExportNotice(null);
    setExportLoading(false);
    setSelectedToolName("");
    if (!activeToken) {
      proposalRequest.current += 1;
      runDetailRequest.current += 1;
      runEvidenceRequest.current += 1;
      setData(emptyDashboardData());
      setSelectedProposalId(null);
      setSelectedProposal(null);
      setSelectedRunId(null);
      setSelectedRun(null);
      setSelectedRunEvidence(null);
      setRunEvidenceError(null);
      setDetailLoading(false);
      setPreviewResult(null);
      setImpactResult(null);
      setError(null);
      setDashboardError(null);
      return;
    }

    setLoading(true);
    setError(null);
    setDashboardError(null);
    setData(emptyDashboardData());
    setSelectedProposalId(null);
    setSelectedProposal(null);
    setSelectedRunId(null);
    setSelectedRun(null);
    setSelectedRunEvidence(null);
    setRunEvidenceError(null);
    proposalRequest.current += 1;
    runDetailRequest.current += 1;
    runEvidenceRequest.current += 1;
    try {
      const [
        systemStatus,
        toolsResponse,
        pendingApprovalsResponse,
        approvalHistoryResponse,
        patchesResponse,
        patchDiagnostics,
        runsResponse,
        nodesResponse,
        auditResponse,
        verificationResponse,
      ] = await Promise.all([
        apiRequest<SystemStatus>("/system/status", activeToken),
        apiRequest<{ tools: ToolSummary[] }>("/tools", activeToken),
        apiRequest<{ approvals: ApprovalReview[] }>("/approvals/review?status=pending", activeToken),
        apiRequest<{ approvals: Approval[] }>("/approvals", activeToken),
        apiRequest<{ patch_proposals: PatchProposal[] }>("/patch-proposals", activeToken),
        apiRequest<PatchApplyDiagnostics>("/patch-apply-diagnostics", activeToken),
        apiRequest<{ runs: AgentRun[]; summary: AgentRunSummary }>(
          runListPath(activeRunFilters),
          activeToken,
        ),
        apiRequest<{ nodes: IthildinNode[] }>("/nodes", activeToken),
        apiRequest<{ audit_events: AuditEvent[] }>("/audit-events?limit=100", activeToken),
        apiRequest<AuditVerification>("/audit-events/verify", activeToken),
      ]);
      if (requestId !== dashboardRequest.current) {
        return;
      }
      setData({
        systemStatus,
        tools: toolsResponse.tools,
        approvals: pendingApprovalsResponse.approvals,
        approvalHistory: approvalHistoryResponse.approvals,
        patches: patchesResponse.patch_proposals,
        patchDiagnostics,
        runs: runsResponse.runs,
        nodes: nodesResponse.nodes,
        runSummary: runsResponse.summary,
        auditEvents: auditResponse.audit_events,
        verification: verificationResponse,
      });
      const nextToolName = toolsResponse.tools.some((tool) => tool.name === selectedToolName)
        ? selectedToolName
        : toolsResponse.tools[0]?.name ?? "";
      setSelectedToolName(nextToolName);
      const nextProposalId = patchesResponse.patch_proposals.some(
        (proposal) => proposal.proposal_id === selectedProposalId,
      )
        ? selectedProposalId
        : filterAndSortPatches(
            patchesResponse.patch_proposals,
            "",
            "all",
            "updated-desc",
          )[0]?.proposal_id ?? null;
      setSelectedProposalId(nextProposalId);
      if (nextProposalId) {
        void loadProposalDetail(nextProposalId, activeToken);
      }
      const nextRunId = runsResponse.runs.some((run) => run.run_id === selectedRunId)
        ? selectedRunId
        : runsResponse.runs[0]?.run_id ?? null;
      setSelectedRunId(nextRunId);
      if (nextRunId) {
        void loadRunDetail(nextRunId, activeToken);
        void loadRunEvidence(nextRunId, activeToken);
      }
    } catch (caught) {
      if (requestId === dashboardRequest.current) {
        setData(emptyDashboardData());
        const message = errorMessage(caught);
        setError(message);
        setDashboardError(message);
      }
    } finally {
      if (requestId === dashboardRequest.current) {
        setLoading(false);
      }
    }
  }

  async function loadProposalDetail(proposalId: string, activeToken = token) {
    if (!activeToken) {
      return;
    }
    const requestId = ++proposalRequest.current;
    setSelectedProposal(null);
    setDetailLoading(true);
    setError(null);
    try {
      const proposal = await apiRequest<PatchProposal>(
        `/patch-proposals/${encodeURIComponent(proposalId)}`,
        activeToken,
      );
      if (requestId === proposalRequest.current && proposal.proposal_id === proposalId) {
        setSelectedProposal(proposal);
      }
    } catch (caught) {
      if (requestId === proposalRequest.current) {
        setError(errorMessage(caught));
      }
    } finally {
      if (requestId === proposalRequest.current) {
        setDetailLoading(false);
      }
    }
  }

  async function loadRunDetail(runId: string, activeToken = token) {
    if (!activeToken) {
      return;
    }
    const requestId = ++runDetailRequest.current;
    setSelectedRun(null);
    setError(null);
    try {
      const run = await apiRequest<AgentRunDetail>(
        `/runs/${encodeURIComponent(runId)}`,
        activeToken,
      );
      if (requestId === runDetailRequest.current && run.run.run_id === runId) {
        setSelectedRun(run);
      }
    } catch (caught) {
      if (requestId === runDetailRequest.current) {
        setError(errorMessage(caught));
      }
    }
  }

  async function loadRunEvidence(runId: string, activeToken = token) {
    if (!activeToken) {
      return;
    }
    const requestId = ++runEvidenceRequest.current;
    setSelectedRunEvidence(null);
    setRunEvidenceError(null);
    try {
      const evidence = await apiRequest<RunEvidenceExport>(
        `/runs/${encodeURIComponent(runId)}/evidence-export`,
        activeToken,
      );
      if (
        requestId === runEvidenceRequest.current &&
        scopeString(evidence.run, "run_id") === runId
      ) {
        setSelectedRunEvidence(evidence);
      }
    } catch (caught) {
      if (requestId === runEvidenceRequest.current) {
        setRunEvidenceError(errorMessage(caught));
      }
    }
  }

  function saveToken(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextToken = draftToken.trim();
    authGeneration.current += 1;
    operationGeneration.current += 1;
    setPreviewResult(null);
    setPreviewError(null);
    setPreviewLoading(false);
    setImpactResult(null);
    setImpactError(null);
    setImpactLoading(false);
    setExportNotice(null);
    setExportLoading(false);
    setError(null);
    setToken(nextToken);
    if (nextToken) {
      sessionStorage.setItem(TOKEN_STORAGE_KEY, nextToken);
      void loadDashboard(nextToken);
    } else {
      dashboardRequest.current += 1;
      proposalRequest.current += 1;
      runDetailRequest.current += 1;
      runEvidenceRequest.current += 1;
      sessionStorage.removeItem(TOKEN_STORAGE_KEY);
      setData(emptyDashboardData());
      setSelectedProposalId(null);
      setSelectedProposal(null);
      setSelectedRunId(null);
      setSelectedRun(null);
      setSelectedRunEvidence(null);
      setRunEvidenceError(null);
      setLoading(false);
      setDetailLoading(false);
      setDashboardError(null);
    }
  }

  function updateRunFilter(name: keyof typeof runFilters, value: string) {
    setRunFilters((current) => ({ ...current, [name]: value }));
  }

  function applyRunFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAppliedRunFilters(runFilters);
    void loadDashboard(token, runFilters);
  }

  function clearRunFilters() {
    const emptyFilters = { principal_id: "", workspace_id: "", status: "", tool_name: "" };
    setRunFilters(emptyFilters);
    setAppliedRunFilters(emptyFilters);
    setInvestigationFilters({
      time_range: "all",
      mission: "",
      decision: "all",
      outcome: "all",
      attention: "all",
    });
    void loadDashboard(token, emptyFilters);
  }

  function clearInvestigationFilter(name: keyof InvestigationFilters) {
    setInvestigationFilters((current) => ({
      ...current,
      [name]: name === "mission" ? "" : "all",
    }));
  }

  function clearAppliedRunFilter(name: keyof RunFilters) {
    const nextFilters = { ...appliedRunFilters, [name]: "" };
    setRunFilters(nextFilters);
    setAppliedRunFilters(nextFilters);
    void loadDashboard(token, nextFilters);
  }

  function openAttentionItem(item: AttentionItem) {
    setActiveSection(item.targetId);
    if (item.targetId === "evidence") {
      setWorkspaceLens("technical");
    }
    if (item.runId) {
      setSelectedRunId(item.runId);
    }
    if (item.proposalId) {
      setSelectedProposalId(item.proposalId);
    }
    if (item.nodeId) {
      setNodeQuery("");
      setNodePosture("all");
      setNodeWorkspace("all");
    }
    const targetElementId = item.nodeId ? `node-${item.nodeId}` : item.targetId;
    window.setTimeout(() => scrollAndFocusElement(targetElementId), 0);
  }

  function openWorkspaceLens(lens: WorkspaceLens, targetId: string) {
    setActiveSection(targetId);
    setWorkspaceLens(lens);
    window.setTimeout(() => scrollAndFocusElement(targetId), 0);
  }

  async function runPolicyPreview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !selectedTool) {
      return;
    }

    const operationAuthGeneration = operationGeneration.current;
    const activeToken = token;
    setPreviewLoading(true);
    setPreviewError(null);
    setPreviewResult(null);
    try {
      const parsedArguments = parseJsonObject(argumentsJson, "Request details");
      const parsedPrincipal = parseJsonObject(principalJson, "Requesting identity");
      const result = await apiRequest<PolicyPreviewResult>("/policy/preview", activeToken, {
        method: "POST",
        body: JSON.stringify({
          tool_name: selectedTool.name,
          arguments: parsedArguments,
          principal: parsedPrincipal,
        }),
      });
      if (operationAuthGeneration === operationGeneration.current) {
        setPreviewResult(result);
      }
    } catch (caught) {
      if (operationAuthGeneration === operationGeneration.current) {
        setPreviewError(errorMessage(caught));
      }
    } finally {
      if (operationAuthGeneration === operationGeneration.current) {
        setPreviewLoading(false);
      }
    }
  }

  async function runPolicyImpact(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) {
      return;
    }

    const operationAuthGeneration = operationGeneration.current;
    const activeToken = token;
    setImpactLoading(true);
    setImpactError(null);
    setImpactResult(null);
    try {
      const result = await apiRequest<PolicyImpactResult>("/policy/impact-preview", activeToken, {
        method: "POST",
        body: JSON.stringify({ candidate_policy_yaml: candidatePolicyYaml }),
      });
      if (operationAuthGeneration === operationGeneration.current) {
        setImpactResult(result);
      }
    } catch (caught) {
      if (operationAuthGeneration === operationGeneration.current) {
        setImpactError(errorMessage(caught));
      }
    } finally {
      if (operationAuthGeneration === operationGeneration.current) {
        setImpactLoading(false);
      }
    }
  }

  async function exportAuditBundle(signed = false) {
    if (!token) {
      return;
    }
    const operationAuthGeneration = operationGeneration.current;
    const activeToken = token;
    setExportLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/audit-events/export${signed ? "/signed" : ""}`, {
        headers: { Authorization: `Bearer ${activeToken}` },
      });
      if (!response.ok) {
        throw await apiErrorFromResponse(response);
      }
      if (operationAuthGeneration !== operationGeneration.current) {
        return;
      }
      const bundle = await response.blob();
      if (operationAuthGeneration !== operationGeneration.current) {
        return;
      }
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
      setExportNotice({
        scope: signed ? "signed-audit" : "audit",
        state: "download-initiated",
        message: signed
          ? "Signed audit export response prepared and browser download initiated; Command Center did not verify the downloaded signature or custody."
          : "Audit export response prepared and browser download initiated; save location and custody are not verified.",
      });
    } catch (caught) {
      if (operationAuthGeneration === operationGeneration.current) {
        setError(errorMessage(caught));
        setExportNotice({
          scope: signed ? "signed-audit" : "audit",
          state: "failed",
          message: errorMessage(caught),
        });
      }
    } finally {
      if (operationAuthGeneration === operationGeneration.current) {
        setExportLoading(false);
      }
    }
  }

  async function exportRunEvidence(runId: string) {
    if (!token) {
      return;
    }
    const operationAuthGeneration = operationGeneration.current;
    const activeToken = token;
    setExportLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE}/runs/${encodeURIComponent(runId)}/evidence-export`,
        {
          headers: { Authorization: `Bearer ${activeToken}` },
        },
      );
      if (!response.ok) {
        throw await apiErrorFromResponse(response);
      }
      if (operationAuthGeneration !== operationGeneration.current) {
        return;
      }
      const bundle = await response.blob();
      if (operationAuthGeneration !== operationGeneration.current) {
        return;
      }
      const objectUrl = URL.createObjectURL(bundle);
      const anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = `ithildin-run-evidence-${shortId(runId)}.json`;
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(objectUrl);
      setExportNotice({
        scope: "run",
        runId,
        state: "download-initiated",
        message:
          "Run evidence response prepared and browser download initiated; save location, custody, receipt, and later integrity are not verified.",
      });
    } catch (caught) {
      if (operationAuthGeneration === operationGeneration.current) {
        const message = `Run ${shortId(runId)} export failed: ${errorMessage(caught)}`;
        setError(message);
        setExportNotice({ scope: "run", runId, state: "failed", message });
      }
    } finally {
      if (operationAuthGeneration === operationGeneration.current) {
        setExportLoading(false);
      }
    }
  }

  async function decideApproval(approvalId: string, action: "approve" | "deny") {
    if (decidingApprovalIds.current.has(approvalId)) {
      return;
    }
    decidingApprovalIds.current.add(approvalId);
    const decisionAuthGeneration = authGeneration.current;
    setDecidingApprovals((current) => ({ ...current, [approvalId]: true }));
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
      if (decisionAuthGeneration !== authGeneration.current) {
        return;
      }
      setDenyReasons((current) => {
        const next = { ...current };
        delete next[approvalId];
        return next;
      });
      await loadDashboard(token, appliedRunFilters);
    } catch (caught) {
      if (decisionAuthGeneration === authGeneration.current) {
        setError(errorMessage(caught));
      }
    } finally {
      decidingApprovalIds.current.delete(approvalId);
      setDecidingApprovals((current) => {
        const next = { ...current };
        delete next[approvalId];
        return next;
      });
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

  useEffect(() => {
    if (selectedRunId) {
      void loadRunDetail(selectedRunId);
      void loadRunEvidence(selectedRunId);
    } else {
      setSelectedRun(null);
      setSelectedRunEvidence(null);
      setRunEvidenceError(null);
    }
  }, [selectedRunId, token]);

  return (
    <div className="app-frame">
      <a
        className="skip-link"
        href="#attention"
        onClick={(event) => {
          event.preventDefault();
          setActiveSection("attention");
          scrollAndFocusElement("attention");
        }}
      >
        Skip to operator attention
      </a>
      <aside className="command-sidebar">
        <div className="sidebar-brand" aria-label="Ithildin Command Center">
          <span className="sidebar-mark" aria-hidden="true">
            <ShieldCheck size={24} />
          </span>
          <span>
            <strong>Ithildin</strong>
            <small>Command Center</small>
          </span>
        </div>
        <nav className="command-nav" aria-label="Command Center sections">
          {([
            ["attention", "Attention", "What needs a decision now", <BellRing size={20} />],
            ["missions", "Missions", "Follow agent work end to end", <FolderKanban size={20} />],
            ["nodes", "Nodes", "Enroll and observe enforcement points", <Server size={20} />],
            ["artifacts", "Artifacts", "Review outputs and movement", <Boxes size={20} />],
            ["approvals", "Approvals", "Authorize bounded actions", <ListChecks size={20} />],
            ["evidence", "Evidence", "Reconstruct what happened", <ScrollText size={20} />],
            ["administration", "Administration", "Configure policy and trust", <Settings size={20} />],
          ] as [string, string, string, React.ReactNode][]).map(([target, title, purpose, icon]) => (
            <a
              aria-label={title}
              aria-current={activeSection === target ? "page" : undefined}
              className={activeSection === target ? "active" : ""}
              href={`#${target}`}
              key={target}
              onClick={(event) => {
                event.preventDefault();
                setActiveSection(target);
                if (target === "evidence") {
                  openWorkspaceLens("technical", target);
                } else if (target === "administration") {
                  openWorkspaceLens("policy", target);
                } else {
                  scrollAndFocusElement(target);
                }
              }}
            >
              <span className="nav-icon" aria-hidden="true">{icon}</span>
              <span>
                <strong>{title}</strong>
                <small>{purpose}</small>
              </span>
            </a>
          ))}
          <a
            aria-label="Help"
            aria-current={activeSection === "help" ? "page" : undefined}
            className={activeSection === "help" ? "sidebar-help active" : "sidebar-help"}
            href="#operator-help"
            onClick={(event) => {
              event.preventDefault();
              setActiveSection("help");
              scrollAndFocusElement("operator-help");
            }}
          >
            <CircleHelp aria-hidden="true" size={20} />
            <span>
              <strong>Help</strong>
              <small>Guidance and boundaries</small>
            </span>
          </a>
        </nav>
      </aside>
      <main className="console-shell" data-active-section={activeSection}>
      <header className="topbar">
        <div className="product-heading">
          <p className="eyebrow">Operator console</p>
          <h1>Ithildin Command Center</h1>
        </div>
        <p className="product-summary">
          Command Center presents governed activity. Gateway remains the enforcement and audit authority.
        </p>
        <div className="topbar-actions">
          <div className="runtime-status" aria-label="Local runtime status">
            <span className="local-preview-label">
              {data.systemStatus?.security.preview_label ?? "Local preview"}
            </span>
            <span className={token && data.systemStatus ? "gateway-state reachable" : "gateway-state"}>
              <span aria-hidden="true" className="gateway-state-dot" />
              {token && data.systemStatus ? "Local Gateway reachable" : "Gateway status unavailable"}
            </span>
            <span className={token && data.systemStatus ? "auth-state authenticated" : "auth-state"}>
              {token && data.systemStatus ? "Authenticated local preview" : "Sign-in required"}
            </span>
          </div>
          <form className="token-form" onSubmit={saveToken}>
            <label htmlFor="admin-token">Admin token</label>
            <div className="token-row">
              <KeyRound aria-hidden="true" size={16} />
              <input
                id="admin-token"
                type="password"
                value={draftToken}
                onChange={(event) => setDraftToken(event.target.value)}
                autoComplete="off"
              />
              <button type="submit">
                <ShieldCheck aria-hidden="true" size={16} />
                Save
              </button>
            </div>
          </form>
        </div>
      </header>
      {error ? (
        <section className="notice error" role="alert">
          <AlertTriangle aria-hidden="true" size={18} />
          <span>{error}</span>
        </section>
      ) : null}

      {authRejected ? (
        <section className="notice warning" role="status">
          <KeyRound aria-hidden="true" size={18} />
          <span>Dashboard data is locked until a valid local admin token is saved.</span>
        </section>
      ) : null}

      {!token ? (
        <section className="notice">
          <KeyRound aria-hidden="true" size={18} />
          <span>Admin token required.</span>
        </section>
      ) : null}

      {dashboardUnavailable ? (
        <section className="notice warning" role="status">
          <AlertTriangle aria-hidden="true" size={18} />
          <span>Console data is unavailable; no local system status has loaded.</span>
        </section>
      ) : null}

      {loading && token ? (
        <section className="notice">
          <RefreshCcw aria-hidden="true" size={18} />
          <span>Refreshing console data.</span>
        </section>
      ) : null}

      {trustWarnings.length > 0 ? (
        <section className="notice warning" role="alert">
          <AlertTriangle aria-hidden="true" size={18} />
          <span>{trustWarnings.join(" · ")}</span>
        </section>
      ) : null}

      <section
        className="attention-section destination-screen"
        data-screen="attention"
        id="attention"
        aria-label="Attention"
        tabIndex={-1}
      >
        {!token ? (
          <>
            <AttentionHeading count={0} />
            <EmptyState text="Sign in with the local admin token to load operator attention records." />
          </>
        ) : loading && !data.systemStatus ? (
          <>
            <AttentionHeading count={0} />
            <EmptyState text="Loading operator attention records." />
          </>
        ) : dashboardError ? (
          <>
            <AttentionHeading count={0} />
            <EmptyState text="Operator attention records are unavailable. No empty-state conclusion is available." />
          </>
        ) : primaryAttention ? (
          <div className="attention-workspace">
            <div className="attention-queue" aria-label="Prioritized operator attention">
              <AttentionHeading count={attentionItems.length} />
              {attentionItems.slice(0, 5).map((item) => {
                const key = attentionItemKey(item);
                const selected = attentionItemKey(primaryAttention) === key;
                return (
                  <button
                    aria-pressed={selected}
                    className={selected ? "attention-queue-item selected" : "attention-queue-item"}
                    key={key}
                    type="button"
                    onClick={() => setSelectedAttentionKey(key)}
                  >
                    <span>
                      <strong>{item.missionLabel}</strong>
                      <small>{item.title}</small>
                      <em>
                        {item.occurredAt ? formatDate(item.occurredAt) : "Time unavailable"}
                        {item.requestingIdentity !== "Unavailable"
                          ? ` · ${item.requestingIdentity}`
                          : ""}
                      </em>
                    </span>
                    <StatusPill status={item.status} />
                  </button>
                );
              })}
            </div>
            <article className="attention-item">
              <div className="attention-title-row">
                <span className="attention-detail-icon" aria-hidden="true">
                  <ClipboardList size={28} />
                </span>
                <div>
                  <p className="attention-mission">{primaryAttention.missionLabel}</p>
                  <h3>{primaryAttention.title}</h3>
                  <p className="attention-consequence">{primaryAttention.consequence}</p>
                </div>
                <div className="approval-state-pills">
                  <StatusPill status={primaryAttention.status} />
                  {primaryAttention.bindingStatus ? (
                    <StatusPill status={primaryAttention.bindingStatus} />
                  ) : null}
                </div>
              </div>
              <dl className="attention-context-grid">
                <div>
                  <dt>
                    {primaryAttention.source === "node" ? "Node identity" : "Requesting identity"}{" "}
                    <small>{primaryAttention.source === "node" ? "Gateway derived" : "reported context"}</small>
                  </dt>
                  <dd>{primaryAttention.requestingIdentity}</dd>
                </div>
                <div>
                  <dt>{primaryAttention.source === "node" ? "Fleet posture" : "Policy result"}</dt>
                  <dd>{primaryAttention.status}</dd>
                </div>
                <div>
                  <dt>Workspace <small>operator-managed</small></dt>
                  <dd>{primaryAttention.workspaceId}</dd>
                </div>
                <div>
                  <dt>{primaryAttention.source === "node" ? "Authority source" : "Governed tool"}</dt>
                  <dd>{primaryAttention.toolName}</dd>
                </div>
              </dl>
              <div className="attention-actions" aria-label="Bounded next action">
                <button
                  aria-label={primaryAttention.actionLabel}
                  className="primary-action attention-action"
                  type="button"
                  onClick={() => openAttentionItem(primaryAttention)}
                >
                  <ClipboardList aria-hidden="true" size={20} />
                  <span>
                    <strong>{primaryAttention.actionLabel}</strong>
                    <small>
                      {primaryAttention.source === "node"
                        ? "Inspect the authoritative fleet record and choose only an available bounded action."
                        : "Review the source record and decide the next bounded step."}
                    </small>
                  </span>
                </button>
                {primaryAttention.runId ? (
                  <button
                    aria-label="Open mission Workbench"
                    className="secondary-action attention-action"
                    type="button"
                    onClick={() => openAttentionItem(primaryAttention)}
                  >
                    <FolderKanban aria-hidden="true" size={20} />
                    <span>
                      <strong>Open mission Workbench</strong>
                      <small>Explore the correlated mission activity and evidence.</small>
                    </span>
                  </button>
                ) : null}
              </div>
              <section className="attention-lifecycle" aria-label="Selected attention lifecycle">
                <header>
                  <h4>Recorded context</h4>
                  <span>Observed facts and operator action remain distinct.</span>
                </header>
                <ol>
                  <li className="observed">
                    <span aria-hidden="true"><Check size={15} /></span>
                    <div>
                      <strong>{primaryAttention.source === "node" ? "Fleet posture recorded" : "Request recorded"}</strong>
                      <small>
                        {primaryAttention.source === "node"
                          ? "Gateway enrollment state and accepted Node evidence establish this displayed posture."
                          : "Gateway evidence identifies the reported requester and governed tool."}
                      </small>
                    </div>
                  </li>
                  <li className="operator-step">
                    <span aria-hidden="true">!</span>
                    <div><strong>Operator action pending</strong><small>{primaryAttention.actionLabel}. No mutation is implied until the bounded source workflow records it.</small></div>
                  </li>
                </ol>
              </section>
              <details className="attention-technical">
                <summary>
                  Technical details <span>IDs, {primaryAttention.source === "node" ? "observed basis" : "policy reason"}, and timing</span>
                </summary>
                <dl className="meta-list attention-meta">
                  <div>
                    <dt>{primaryAttention.source === "node" ? "Node" : "Request"}</dt>
                    <dd>{primaryAttention.nodeId ?? (primaryAttention.requestId ? shortId(primaryAttention.requestId) : "Unavailable")}</dd>
                  </div>
                  <div>
                    <dt>{primaryAttention.source === "node" ? "Observed basis" : "Policy reason"}</dt>
                    <dd>{primaryAttention.policyReason}</dd>
                  </div>
                  <div>
                    <dt>{primaryAttention.source === "approval" ? "Expires" : "Recorded"}</dt>
                    <dd>{primaryAttention.occurredAt ? formatDate(primaryAttention.occurredAt) : "Unavailable"}</dd>
                  </div>
                </dl>
              </details>
            </article>
          </div>
        ) : (
          <>
            <AttentionHeading count={0} />
            <EmptyState text="No action identified in the currently loaded local records. This is not a global safety claim." />
          </>
        )}
      </section>

      <div
        className="workspace-lenses"
        aria-label="Command Center presentation lens"
        role="group"
      >
        <strong>Presentation lens</strong>
        {([
          ["routine", "Routine operations"],
          ["investigator", "Investigation"],
          ["policy", "Policy administration"],
          ["technical", "Technical review"],
        ] as [WorkspaceLens, string][]).map(([lens, label]) => (
          <button
            aria-pressed={workspaceLens === lens}
            className={workspaceLens === lens ? "active" : ""}
            key={lens}
            type="button"
            onClick={() => {
              const target =
                lens === "policy"
                  ? "administration"
                  : lens === "technical"
                    ? "evidence"
                    : lens === "investigator"
                      ? "missions"
                      : "attention";
              setWorkspaceLens(lens);
              setActiveSection(target);
              window.setTimeout(() => scrollAndFocusElement(target), 0);
            }}
          >
            {label}
          </button>
        ))}
        <span>
          Presentation only · lenses do not grant roles, permissions, or Gateway authority.
        </span>
      </div>

      <details className="operator-help destination-screen" data-screen="help" id="operator-help" open>
        <summary>Guidance and boundaries</summary>
        <div className="help-intro">
          <CircleHelp aria-hidden="true" size={28} />
          <div>
            <p className="eyebrow">Operator guidance</p>
            <h2>How to read Command Center</h2>
            <p>
              Ithildin Gateway mediates requests made through its registered governed tools and records
              policy, approval, execution, and audit evidence. Command Center reviews those records.
            </p>
          </div>
        </div>
        <div className="help-boundary-grid">
          <article>
            <strong>Gateway is authoritative</strong>
            <p>Command Center presents recorded state; it does not replace policy, approval, or audit authority.</p>
          </article>
          <article>
            <strong>External agents remain external</strong>
            <p>Ithildin does not start or control the agent, and it cannot prove activity that bypassed the Gateway.</p>
          </article>
          <article>
            <strong>Registration is not permission</strong>
            <p>A registered tool is evaluated against the requesting identity, workspace, resource, and current policy.</p>
          </article>
          <article>
            <strong>Evidence is bounded</strong>
            <p>Local verification detects record-chain changes; it is not immutable custody or host-compromise resistance.</p>
          </article>
        </div>
      </details>

      <section className="summary-strip destination-screen" data-screen="attention" aria-label="Review summary">
        <Metric icon={<ClipboardList size={20} />} label="Pending" value={pendingCount} />
        <Metric icon={<FileDiff size={20} />} label="Proposed patches" value={proposedPatchCount} />
        <Metric icon={<Activity size={20} />} label="Agent runs" value={data.runs.length} />
        <Metric icon={<AlertTriangle size={20} />} label="Recent failures" value={recentFailures.length} />
        <Metric
          icon={<ShieldCheck size={20} />}
          label="Patch recovery"
          value={data.patchDiagnostics?.status === "clean" ? 0 : data.patchDiagnostics ? 1 : 0}
        />
        <button className="refresh-button" type="button" onClick={() => void loadDashboard()}>
          <RefreshCcw aria-hidden="true" size={18} />
          {loading ? "Refreshing" : "Refresh"}
        </button>
      </section>

      {workspaceLens === "policy" || workspaceLens === "technical" ? (
      <section className="trust-grid destination-screen" data-screen="administration" id="administration" aria-label="Policy administration" tabIndex={-1}>
        <DestinationHeading
          eyebrow="Governance administration"
          title="Policy and trust posture"
          description="Inspect the local enforcement posture, registered capabilities, and non-mutating policy controls."
          icon={<Settings size={24} />}
        />
        <Panel
          title="Local System Posture"
          purpose="Understand local trust configuration before using specialist controls."
          icon={<ShieldCheck size={18} />}
        >
          {data.systemStatus ? (
            <div className="trust-panel">
              <div className="trust-heading">
                <span
                  className={
                    data.systemStatus.audit.valid
                      ? "integrity-indicator"
                      : "integrity-indicator invalid"
                  }
                >
                  {data.systemStatus.audit.valid
                    ? "Local audit chain valid"
                    : "Local audit chain needs attention"}
                </span>
                <span className="trust-service">{data.systemStatus.service}</span>
              </div>
              <dl className="administration-posture-summary">
                <div>
                  <dt>Governed tools</dt>
                  <dd>{data.systemStatus.tool_count}</dd>
                  <small>Registration does not grant request permission.</small>
                </div>
                <div>
                  <dt>Policy engine</dt>
                  <dd>{data.systemStatus.policy.engine}</dd>
                  <small>Current local policy evaluation posture.</small>
                </div>
                <div>
                  <dt>Signed export</dt>
                  <dd>{data.systemStatus.audit_signing.signed_export_available ? "Available" : "Not configured"}</dd>
                  <small>Availability is not an export receipt or custody claim.</small>
                </div>
                <div>
                  <dt>Environment</dt>
                  <dd>{data.systemStatus.security.preview_label}</dd>
                  <small>Local preview, not production readiness.</small>
                </div>
              </dl>
              <details className="administration-technical">
                <summary>Technical trust configuration</summary>
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
                  <dt>Filesystem</dt>
                  <dd title={data.systemStatus.filesystem.support.reason}>
                    {data.systemStatus.filesystem.platform.profile} ·{" "}
                    {data.systemStatus.filesystem.support.status}
                  </dd>
                </div>
                <div>
                  <dt>Tools</dt>
                  <dd>{data.systemStatus.tool_count}</dd>
                </div>
                <div>
                  <dt>Principals</dt>
                  <dd>
                    {data.systemStatus.principals.enabled_count}/
                    {data.systemStatus.principals.count}
                    {data.systemStatus.principals.required ? " required" : " optional"}
                  </dd>
                </div>
                <div>
                  <dt>Workspaces</dt>
                  <dd>
                    {data.systemStatus.workspaces.enabled_count}/
                    {data.systemStatus.workspaces.count} ·{" "}
                    {data.systemStatus.workspaces.default_workspace_id}
                  </dd>
                </div>
                <div>
                  <dt>Storage</dt>
                  <dd>
                    {data.systemStatus.storage.runtime_backend}
                    {data.systemStatus.storage.runtime_enabled ? "" : " unavailable"}
                  </dd>
                </div>
                <div>
                  <dt>Telemetry</dt>
                  <dd>
                    {data.systemStatus.telemetry.enabled
                      ? data.systemStatus.telemetry.exporters.join(", ") || "enabled"
                      : "disabled"}
                  </dd>
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
                <div>
                  <dt>Patch Apply</dt>
                  <dd>{data.patchDiagnostics?.status ?? "unknown"}</dd>
                </div>
                </dl>
              </details>
            </div>
          ) : (
            <EmptyState text={token ? "System status unavailable." : "Locked."} />
          )}
        </Panel>

        <Panel
          title="Registered Tools"
          purpose="Review available governed capabilities; registration does not grant request permission."
          icon={<ClipboardList size={18} />}
        >
          {data.tools.length === 0 ? (
            <EmptyState text={token ? "No registered tools." : "Locked."} />
          ) : (
            <div className="table-wrap compact-table">
              <table>
                <thead>
                  <tr>
                    <th>Tool</th>
                    <th>Capability</th>
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
                        <span className="capability-label">{tool.risk}</span>
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
      ) : null}

      {workspaceLens === "policy" ? (
      <section className="policy-section destination-screen" data-screen="administration">
        <Panel
          title="Request Decision Preflight"
          purpose="Troubleshoot a hypothetical governed request without executing it or creating authority."
          icon={<ShieldCheck size={18} />}
        >
          <div className="preflight-boundary">
            <strong>Administration · policy troubleshooting</strong>
            <p>
              Evaluate a new hypothetical tool request against current policy. This does not
              execute a tool, create an approval, replay the selected request, or change policy.
            </p>
            {selectedRun ? (
              <p>
                Selected Workbench context: {shortId(selectedRun.run.run_id)} · {selectedRun.run.principal_id} · {selectedRun.run.workspace_id}. Raw request arguments are intentionally not reconstructed.
              </p>
            ) : null}
          </div>
          <form className="policy-preview-form" onSubmit={runPolicyPreview}>
            <div className="policy-controls">
              <label>
                <span>Tool request</span>
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
                      {tool.title} · {tool.name} · {tool.risk}
                    </option>
                  ))}
                </select>
              </label>
              <button
                className="primary-action"
                type="submit"
                disabled={!token || !selectedTool || previewLoading}
              >
                <ShieldCheck aria-hidden="true" size={16} />
                {previewLoading ? "Evaluating" : "Test decision"}
              </button>
            </div>
            <div className="json-editors">
              <label>
                <span>Request details (JSON)</span>
                <textarea
                  value={argumentsJson}
                  onChange={(event) => setArgumentsJson(event.target.value)}
                  spellCheck={false}
                />
              </label>
              <label>
                <span>Requesting identity (JSON)</span>
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
                  <h3>{selectedTool?.title ?? previewResult.tool_name}</h3>
                  <p>{previewResult.tool_name}</p>
                </div>
                <StatusPill status={previewResult.decision} />
              </div>
              <dl className="meta-list preview-meta">
                <div>
                  <dt>Request details</dt>
                  <dd>{previewResult.valid_arguments ? "valid" : "invalid"}</dd>
                </div>
                <div>
                  <dt>Capability class</dt>
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

        <Panel
          title="Candidate Policy Impact"
          purpose="Compare reviewed fixtures without applying or authorizing a candidate policy."
          icon={<FileDiff size={18} />}
        >
          <div className="preflight-boundary">
            <strong>Policy administrator tool</strong>
            <p>
              Compare candidate YAML against reviewed test cases. This does not apply the candidate
              policy or authorize implementation.
            </p>
          </div>
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
      ) : null}

      {workspaceLens === "technical" ? (
      <section className="integrity-section destination-screen" data-screen="evidence" id="evidence" aria-label="Technical evidence" tabIndex={-1}>
        <DestinationHeading
          eyebrow="Evidence reconstruction"
          title="Recorded activity and integrity"
          description="Verify the local audit chain, export bounded evidence, and inspect recovery diagnostics."
          icon={<ScrollText size={24} />}
        />
        <Panel
          title="Audit Integrity"
          purpose="Reconstruct locally mediated activity and understand the limits of its evidence."
          icon={<ShieldCheck size={18} />}
        >
          <div className="evidence-boundary">
            <strong>Local mediated evidence</strong>
            <p>
              This view covers activity recorded through Ithildin. Chain verification detects
              local record tampering; it does not establish immutable custody, host-compromise
              resistance, or activity outside the Gateway.
            </p>
          </div>
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
                    {data.verification.valid ? "Audit chain OK" : "Attention required"}
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
          {exportNotice && exportNotice.scope !== "run" ? (
            <div className="export-scope-notice" role="status" aria-live="polite">
              <strong>
                {exportNotice.scope === "signed-audit" ? "Signed audit export" : "Audit export"}: {" "}
                {exportNotice.state === "failed" ? "failed" : "download initiated"}
              </strong>
              <span>{exportNotice.message}</span>
            </div>
          ) : null}
          {data.patchDiagnostics ? (
            <PatchDiagnosticsSummary diagnostics={data.patchDiagnostics} />
          ) : null}
        </Panel>
      </section>
      ) : null}

      <section className="review-grid destination-screen" data-screen="approvals">
        <DestinationHeading
          eyebrow="Decision queue"
          title="Bounded approvals"
          description="Review binding evidence before authorizing or denying an exact one-time action."
          icon={<ListChecks size={24} />}
        />
        <Panel
          id="approvals"
          title="Pending Approvals"
          purpose="Authorize or deny an exact bounded action after reviewing its binding evidence."
          icon={<ClipboardList size={18} />}
        >
          {data.approvals.length === 0 ? (
            <EmptyState
              text={
                dashboardError
                  ? "Pending approval data is unavailable."
                  : token
                    ? "No pending approvals."
                    : "Locked."
              }
            />
          ) : (
            <div className="approval-workspace">
              <div className="approval-list" aria-label="Pending approval queue">
                {data.approvals.map((candidate) => {
                  const approval = candidate.approval;
                  const selected =
                    approval.approval_id === selectedApprovalReview?.approval.approval_id;
                  return (
                    <button
                      aria-pressed={selected}
                      className={selected ? "approval-queue-item selected" : "approval-queue-item"}
                      key={approval.approval_id}
                      type="button"
                      onClick={() => setSelectedApprovalId(approval.approval_id)}
                    >
                      <span>
                        <strong>{approval.summary}</strong>
                        <small>{approval.tool_name}</small>
                        <em>Expires {formatDate(approval.expires_at)}</em>
                      </span>
                      <StatusPill status={candidate.review.valid ? approval.status : "stale binding"} />
                    </button>
                  );
                })}
              </div>
              {selectedApprovalReview ? (() => {
                const approval = selectedApprovalReview.approval;
                return (
                <article
                  className="approval-item"
                  id={`approval-${approval.approval_id}`}
                  key={approval.approval_id}
                  tabIndex={-1}
                  aria-label={`Approval ${shortId(approval.approval_id)} for ${approval.summary}`}
                >
                  <div className="item-heading">
                    <div>
                      <h3>{approval.summary}</h3>
                      <p>{approval.tool_name}</p>
                    </div>
                    <div className="approval-state-pills">
                      <StatusPill status={approval.status} />
                      {!selectedApprovalReview.review.valid ? <StatusPill status="stale binding" /> : null}
                    </div>
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
                  <p className="approval-consequence">
                    Approval authorizes only the exact one-time scope shown below. It does not
                    promote, release, or trust the resulting artifact.
                  </p>
                  <BindingReviewSummary review={selectedApprovalReview.review} />
                  <ApprovalEvidence approval={approval} review={selectedApprovalReview.review} />
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
                    <button
                      type="button"
                      disabled={!selectedApprovalReview.review.valid || decidingApprovals[approval.approval_id]}
                      onClick={() => void decideApproval(approval.approval_id, "deny")}
                    >
                      <X aria-hidden="true" size={16} />
                      Deny
                    </button>
                    <button
                      className="primary-action"
                      type="button"
                      disabled={
                        !selectedApprovalReview.review.valid || decidingApprovals[approval.approval_id]
                      }
                      onClick={() => void decideApproval(approval.approval_id, "approve")}
                    >
                      <Check aria-hidden="true" size={16} />
                      Approve
                    </button>
                  </div>
                </article>
                );
              })() : null}
            </div>
          )}
        </Panel>

      </section>

      <section className="review-grid artifact-review-grid destination-screen" data-screen="artifacts">
        <DestinationHeading
          eyebrow="Artifact governance"
          title="Outputs and movement"
          description="Follow proposed and applied changes without confusing review, promotion, or release state."
          icon={<Boxes size={24} />}
        />
        <Panel
          id="artifacts"
          title="Artifacts"
          purpose="Review proposed and applied outputs without confusing review readiness with promotion."
          icon={<FileDiff size={18} />}
        >
          <div className="artifact-controls" aria-label="Artifact proposal filters">
            <label>
              <span>Search artifacts</span>
              <input
                value={artifactQuery}
                placeholder="Path, workspace, request"
                onChange={(event) => setArtifactQuery(event.target.value)}
              />
            </label>
            <label>
              <span>Proposal state</span>
              <select
                value={artifactStatus}
                onChange={(event) => setArtifactStatus(event.target.value)}
              >
                <option value="all">All states</option>
                {Array.from(new Set(data.patches.map((patch) => patch.status)))
                  .sort()
                  .map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              <span>Sort</span>
              <select value={artifactSort} onChange={(event) => setArtifactSort(event.target.value)}>
                <option value="updated-desc">Recently updated</option>
                <option value="updated-asc">Oldest updated</option>
                <option value="path-asc">Artifact path</option>
              </select>
            </label>
            <span className="artifact-result-count">{visiblePatches.length} shown</span>
          </div>
          <div className="patch-layout">
            <div className="patch-list" aria-label="Artifact proposal list">
              {data.patches.length === 0 ? (
                <EmptyState
                  text={
                    dashboardError
                      ? "Patch proposal data is unavailable."
                      : token
                        ? "No patch proposals."
                        : "Locked."
                  }
                />
              ) : visiblePatches.length === 0 ? (
                <EmptyState text="No proposals match the current artifact filters." />
              ) : (
                <>
                  <div className="patch-column-headings">
                    <span>Artifact</span>
                    <span>Requester</span>
                    <span>Lifecycle</span>
                    <span>Updated</span>
                    <span>Next</span>
                  </div>
                  {groupedPatches.map(([workspaceId, patches]) => (
                    <section className="patch-workspace-group" key={workspaceId}>
                      <h4>{workspaceId} workspace</h4>
                      {patches.map((patch) => {
                        const history = approvalsForProposal(data.approvalHistory, patch.proposal_id);
                        const pendingReview = pendingReviewForProposal(
                          data.approvals,
                          patch.proposal_id,
                        );
                        return (
                          <button
                            className={
                              patch.proposal_id === selectedProposalId
                                ? "patch-row selected"
                                : "patch-row"
                            }
                            key={patch.proposal_id}
                            type="button"
                            aria-pressed={patch.proposal_id === selectedProposalId}
                            onClick={() => setSelectedProposalId(patch.proposal_id)}
                          >
                            <span className="patch-artifact-cell" data-label="Artifact" aria-label={`Artifact: ${patch.path}`}>
                              <strong>{patch.path}</strong>
                              <small>{shortId(patch.request_id)}</small>
                            </span>
                            <span data-label="Requester" aria-label={`Requester: ${proposalRequester(history)}`}>{proposalRequester(history)}</span>
                            <span data-label="Lifecycle" aria-label={`Lifecycle: ${proposalLifecycleStatus(patch, history)}`}>
                              <StatusPill
                                status={proposalLifecycleStatus(patch, history)}
                              />
                            </span>
                            <span data-label="Updated" aria-label={`Updated: ${formatDate(patch.updated_at)}`}>{formatDate(patch.updated_at)}</span>
                            <span data-label="Next" aria-label={`Next action: ${proposalNextAction(patch, history, pendingReview)}`}>{proposalNextAction(patch, history, pendingReview)}</span>
                          </button>
                        );
                      })}
                    </section>
                  ))}
                </>
              )}
            </div>
            <div className="diff-view" role="region" aria-label="Selected artifact detail" aria-live="polite">
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
                        selectedProposal.status === "proposed" &&
                        selectedProposal.review?.stale === true
                          ? "stale"
                          : selectedProposal.status
                      }
                    />
                  </div>
                  {selectedProposal.review && selectedProposal.status === "proposed" ? (
                    <BindingReviewSummary review={selectedProposal.review as BindingReview} />
                  ) : null}
                  <ArtifactLifecycleSummary
                    approvals={selectedProposalApprovals}
                    pendingApprovalReview={selectedPendingProposalApproval}
                    proposal={selectedProposal}
                    onOpenApproval={() => {
                      const approvalId =
                        selectedPendingProposalApproval?.approval.approval_id ?? null;
                      setActiveSection("approvals");
                      if (approvalId) {
                        setSelectedApprovalId(approvalId);
                      }
                      window.setTimeout(
                        () => scrollAndFocusElement(approvalId ? `approval-${approvalId}` : "approvals"),
                        0,
                      );
                    }}
                  />
                  <details className="artifact-technical-evidence">
                    <summary>Technical change evidence</summary>
                    <dl className="meta-list artifact-digests">
                      <div>
                        <dt>Proposal</dt>
                        <dd>{shortId(selectedProposal.proposal_id)}</dd>
                      </div>
                      <div>
                        <dt>Request</dt>
                        <dd>{shortId(selectedProposal.request_id)}</dd>
                      </div>
                      <div>
                        <dt>Proposal digest</dt>
                        <dd>{shortHash(selectedProposal.proposal_hash)}</dd>
                      </div>
                      <div>
                        <dt>Base artifact digest</dt>
                        <dd>{shortHash(selectedProposal.base_file_hash)}</dd>
                      </div>
                      <div>
                        <dt>Current artifact digest</dt>
                        <dd>
                          {selectedProposal.review
                            ? shortHash(
                                scopeString(selectedProposal.review, "current_base_file_hash"),
                              ) || "Unavailable"
                            : "Unavailable"}
                        </dd>
                      </div>
                    </dl>
                    <pre>{selectedProposal.unified_diff ?? ""}</pre>
                  </details>
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

      <section
        className="node-section destination-screen"
        data-screen="nodes"
        id="nodes"
        aria-label="Ithildin Nodes"
        tabIndex={-1}
      >
        <DestinationHeading
          eyebrow="Deployment foundation"
          title="Enforcement nodes"
          description="Review Gateway-enrolled enforcement identities and the connectivity Ithildin has actually observed."
          icon={<Server size={24} />}
        />
        <Panel
          title="Node inventory"
          purpose="Separate durable enrollment state from recently accepted heartbeats and unobserved runner health."
          icon={<Server size={18} />}
        >
          <div className="node-boundary-callout">
            <ShieldCheck aria-hidden="true" size={22} />
            <div>
              <strong>Gateway-derived identity</strong>
              <p>
                Enrollment and revocation are authoritative Gateway records. Connectivity means only
                that a correctly signed heartbeat was recently accepted; it is not runner or model health.
              </p>
            </div>
            <span>Local-preview Track B slice</span>
          </div>
          <dl className="node-metrics" aria-label="Node fleet summary">
            <div>
              <dt>Enrolled identities</dt>
              <dd>{data.nodes.filter((node) => node.status === "enrolled").length}</dd>
            </div>
            <div>
              <dt>Recently observed</dt>
              <dd>{data.nodes.filter((node) => node.observed_state === "observed_connected").length}</dd>
            </div>
            <div>
              <dt>Needs attention</dt>
              <dd>{data.nodes.filter(nodeNeedsAttention).length}</dd>
            </div>
            <div>
              <dt>Config drift</dt>
              <dd>{data.nodes.filter((node) => node.configuration_state === "configuration_drift").length}</dd>
            </div>
            <div>
              <dt>Version drift</dt>
              <dd>{data.nodes.filter((node) => node.version_posture === "below_minimum").length}</dd>
            </div>
            <div>
              <dt>Revoked</dt>
              <dd>{data.nodes.filter((node) => node.status === "revoked").length}</dd>
            </div>
          </dl>
          {data.nodes.length > 0 ? (
            <div className="node-controls" aria-label="Node inventory filters">
              <label>
                Search loaded Nodes
                <input
                  type="search"
                  value={nodeQuery}
                  onChange={(event) => setNodeQuery(event.target.value)}
                  placeholder="Name, ID, workspace, adapter…"
                />
              </label>
              <label>
                Fleet posture
                <select value={nodePosture} onChange={(event) => setNodePosture(event.target.value)}>
                  <option value="all">All postures</option>
                  <option value="attention">Needs attention</option>
                  <option value="enrolled">Enrolled identities</option>
                  <option value="observed_connected">Recently observed</option>
                  <option value="stale">Stale heartbeat</option>
                  <option value="never_observed">Never observed</option>
                  <option value="revoked">Revoked</option>
                </select>
              </label>
              <label>
                Workspace
                <select value={nodeWorkspace} onChange={(event) => setNodeWorkspace(event.target.value)}>
                  <option value="all">All workspaces</option>
                  {nodeWorkspaces.map((workspace) => (
                    <option key={workspace} value={workspace}>{workspace}</option>
                  ))}
                </select>
              </label>
              <label>
                Sort
                <select value={nodeSort} onChange={(event) => setNodeSort(event.target.value)}>
                  <option value="attention">Attention first</option>
                  <option value="name">Name</option>
                  <option value="workspace">Workspace</option>
                  <option value="last-seen">Latest heartbeat</option>
                </select>
              </label>
              <button
                type="button"
                onClick={() => {
                  setNodeQuery("");
                  setNodePosture("all");
                  setNodeWorkspace("all");
                  setNodeSort("attention");
                }}
              >
                Clear filters
              </button>
              <span className="node-result-count" role="status" aria-live="polite">
                {visibleNodes.length} of {data.nodes.length} loaded {data.nodes.length === 1 ? "Node" : "Nodes"}
              </span>
              <p>Filters and ordering use loaded Gateway records only; they do not change fleet state.</p>
            </div>
          ) : null}
          {data.nodes.length === 0 ? (
            <EmptyState
              text={
                token
                  ? "No Node identities are enrolled in the loaded local Gateway."
                  : "Sign in to load Node inventory."
              }
            />
          ) : visibleNodes.length === 0 ? (
            <EmptyState text="No loaded Nodes match the current fleet filters." />
          ) : (
            <div className="node-card-grid" role="list" aria-label="Filtered Node inventory">
              {visibleNodes.map((node) => (
                <article
                  className="node-card"
                  id={`node-${node.node_id}`}
                  key={node.node_id}
                  role="listitem"
                  tabIndex={-1}
                >
                  <header>
                    <span className="node-card-icon" aria-hidden="true"><Server size={20} /></span>
                    <div>
                      <h3>{node.display_name}</h3>
                      <p>{node.node_id}</p>
                    </div>
                    <StatusPill status={node.observed_state} />
                  </header>
                  <div className="node-configuration-posture">
                    <div>
                      <span>Configuration posture</span>
                      <strong>{node.configuration_state.replace(/_/g, " ")}</strong>
                    </div>
                    <StatusPill status={node.configuration_state} />
                    <p>
                      {node.configuration_acknowledgment_status === "stored_not_enforced"
                        ? "Node attests that the signed configuration is stored. Enforcement is not proven."
                        : "No current Node storage acknowledgment. Enforcement is not proven."}
                    </p>
                  </div>
                  <NodeConfigurationTrustPosture transition={node.configuration_trust_transition} />
                  <div className="node-configuration-posture">
                    <div>
                      <span>Node identity-key posture</span>
                      <strong>{node.status === "revoked"
                        ? "request authority revoked"
                        : node.identity_key_rotation
                          ? node.identity_key_rotation.status.replace(/_/g, " ")
                          : "enrollment key active"}</strong>
                    </div>
                    <StatusPill
                      status={node.status === "revoked"
                        ? "revoked"
                        : node.identity_key_rotation?.status ?? "active"}
                    />
                    <p>
                      {node.status === "revoked"
                        ? `Gateway retains fingerprint ${shortHash(node.active_identity_key_id)} for evidence; the key cannot authenticate future Node requests.`
                        : `Active request key ${shortHash(node.active_identity_key_id)}. Rotation requires current-key authorization and proof by the next key; retired keys have no request authority.`}
                    </p>
                  </div>
                  <div className="node-configuration-posture">
                    <div>
                      <span>Node version posture</span>
                      <strong>{node.version_posture.replace(/_/g, " ")}</strong>
                    </div>
                    <StatusPill status={node.version_posture} />
                    <p>
                      Signed heartbeat observation versus signed desired minimum. Maintenance remains
                      operator-managed; package authenticity and process health are unknown.
                    </p>
                  </div>
                  <dl>
                    <div>
                      <dt>Administrative state</dt>
                      <dd>{node.status}</dd>
                    </div>
                    <div>
                      <dt>Audit evidence</dt>
                      <dd>{node.evidence_status}</dd>
                    </div>
                    <div>
                      <dt>
                        {node.status === "revoked"
                          ? "Identity key fingerprint"
                          : "Active identity key"}{" "}
                        <small>Gateway fingerprint</small>
                      </dt>
                      <dd>{shortHash(node.active_identity_key_id)}</dd>
                    </div>
                    <div>
                      <dt>Assigned workspace</dt>
                      <dd>{node.workspace_id}</dd>
                    </div>
                    <div>
                      <dt>Runner adapter <small>reported posture</small></dt>
                      <dd>{scopeString(node.descriptor, "runner_adapter") || "Unavailable"}</dd>
                    </div>
                    <div>
                      <dt>Topology <small>reported posture</small></dt>
                      <dd>{scopeString(node.descriptor, "deployment_topology") || "Unavailable"}</dd>
                    </div>
                    <div>
                      <dt>Last accepted heartbeat</dt>
                      <dd>{node.last_seen_at ? formatDate(node.last_seen_at) : "Never observed"}</dd>
                    </div>
                    <div>
                      <dt>Observed Node version <small>signed heartbeat</small></dt>
                      <dd>{node.last_observed_node_version ?? "Never observed"}</dd>
                    </div>
                    <div>
                      <dt>Desired minimum version <small>signed configuration</small></dt>
                      <dd>{node.minimum_node_version ?? "Unassigned"}</dd>
                    </div>
                    <div>
                      <dt>Desired configuration</dt>
                      <dd>{node.desired_configuration_generation === null
                        ? "Unassigned"
                        : `Generation ${node.desired_configuration_generation}`}</dd>
                    </div>
                    <div>
                      <dt>Stored configuration <small>Node-attested, not enforced</small></dt>
                      <dd>{node.acknowledged_configuration_generation === null
                        ? "Not acknowledged"
                        : `Generation ${node.acknowledged_configuration_generation}`}</dd>
                    </div>
                    <div>
                      <dt>Desired digest</dt>
                      <dd>{node.desired_configuration_digest ? shortHash(node.desired_configuration_digest) : "Unavailable"}</dd>
                    </div>
                    <div>
                      <dt>Last reported digest <small>heartbeat posture</small></dt>
                      <dd>{node.last_configuration_digest ? shortHash(node.last_configuration_digest) : "Unavailable"}</dd>
                    </div>
                  </dl>
                  <NodeConfigurationControl
                    node={node}
                    token={token}
                    onChanged={() => loadDashboard()}
                  />
                  <NodeRevocationControl
                    node={node}
                    token={token}
                    onChanged={() => loadDashboard()}
                  />
                  <footer>
                    <span>Identity source · Gateway derived</span>
                    <span>Config signer · {node.configuration_signing_key_id
                      ? shortHash(node.configuration_signing_key_id)
                      : "unavailable"}</span>
                    <span>Runner health · unknown</span>
                    <span>Policy enforcement · unknown</span>
                  </footer>
                </article>
              ))}
            </div>
          )}
        </Panel>
      </section>

      <section className="run-section destination-screen" data-screen="missions" id="missions" aria-label="Agent runs" tabIndex={-1}>
        <DestinationHeading
          eyebrow="Mission workbench"
          title="Observed agent runs"
          description="Reconstruct Ithildin-mediated activity from request through recorded evidence closeout."
          icon={<FolderKanban size={24} />}
        />
        <Panel
          title="Agent Runs"
          purpose="Follow Ithildin-mediated agent work from observed request through evidence closeout."
          icon={<Activity size={18} />}
        >
          <OperatorWorkbenchGuide />
          <RunnerGovernancePosture run={selectedRun?.run ?? null} />
          {workspaceLens === "investigator" ? (
          <form className="run-filter-bar" onSubmit={applyRunFilters}>
            <label>
              <span>Principal</span>
              <input
                value={runFilters.principal_id}
                onChange={(event) => updateRunFilter("principal_id", event.target.value)}
                placeholder="agent:mcp-local"
              />
            </label>
            <label>
              <span>Workspace</span>
              <input
                value={runFilters.workspace_id}
                onChange={(event) => updateRunFilter("workspace_id", event.target.value)}
                placeholder="default"
              />
            </label>
            <label>
              <span>Status</span>
              <input
                value={runFilters.status}
                onChange={(event) => updateRunFilter("status", event.target.value)}
                placeholder="active"
              />
            </label>
            <label>
              <span>Tool</span>
              <input
                value={runFilters.tool_name}
                onChange={(event) => updateRunFilter("tool_name", event.target.value)}
                placeholder="fs.read"
              />
            </label>
            <button className="secondary-action" type="submit" disabled={!token || loading}>
              <RefreshCcw aria-hidden="true" size={16} />
              Apply
            </button>
            <button className="secondary-action" type="button" disabled={!token || loading} onClick={clearRunFilters}>
              Clear
            </button>
          </form>
          ) : null}
          {workspaceLens === "investigator" ? (
          <div className="investigation-filter-bar" aria-label="Observed investigation filters">
            <label>
              <span>Last recorded update</span>
              <select
                value={investigationFilters.time_range}
                onChange={(event) =>
                  setInvestigationFilters((current) => ({
                    ...current,
                    time_range: event.target.value,
                  }))
                }
              >
                <option value="all">Any loaded time</option>
                <option value="24h">Last 24 hours</option>
                <option value="7d">Last 7 days</option>
                <option value="30d">Last 30 days</option>
              </select>
            </label>
            <label>
              <span>Mission context</span>
              <input
                value={investigationFilters.mission}
                placeholder="Guided demo or workspace"
                onChange={(event) =>
                  setInvestigationFilters((current) => ({
                    ...current,
                    mission: event.target.value,
                  }))
                }
              />
            </label>
            <label>
              <span>Observed decision</span>
              <select
                value={investigationFilters.decision}
                onChange={(event) =>
                  setInvestigationFilters((current) => ({
                    ...current,
                    decision: event.target.value,
                  }))
                }
              >
                <option value="all">Any observed decision</option>
                <option value="allow">Allow</option>
                <option value="deny">Deny</option>
                <option value="require_approval">Approval required</option>
              </select>
            </label>
            <label>
              <span>Observed outcome</span>
              <select
                value={investigationFilters.outcome}
                onChange={(event) =>
                  setInvestigationFilters((current) => ({
                    ...current,
                    outcome: event.target.value,
                  }))
                }
              >
                <option value="all">Any observed outcome</option>
                <option value="completed">Completed execution</option>
                <option value="failed">Failed execution</option>
                <option value="started">Started execution</option>
                <option value="unavailable">No outcome in recent window</option>
              </select>
            </label>
            <label>
              <span>Observed attention</span>
              <select
                value={investigationFilters.attention}
                onChange={(event) =>
                  setInvestigationFilters((current) => ({
                    ...current,
                    attention: event.target.value,
                  }))
                }
              >
                <option value="all">Any attention state</option>
                <option value="attention">Needs observed attention</option>
                <option value="none">No attention observed</option>
              </select>
            </label>
          </div>
          ) : null}
          {workspaceLens === "investigator" ? (
          <RunFilterChips
            investigationFilters={investigationFilters}
            onClearAll={clearRunFilters}
            onClearInvestigation={clearInvestigationFilter}
            onClearServer={clearAppliedRunFilter}
            runFilters={appliedRunFilters}
          />
          ) : null}
          {data.runSummary ? <RunSummary summary={data.runSummary} /> : null}
          {workspaceLens === "investigator" ? (
          <InvestigationSummary
            auditEvents={data.auditEvents}
            loadedCount={data.runs.length}
            runs={investigationRuns}
          />
          ) : null}
          <div className="run-layout">
            <div className="run-list">
              {(workspaceLens === "investigator" ? investigationRuns : data.runs).length === 0 ? (
                <EmptyState
                  text={
                    dashboardError
                      ? "Agent run data is unavailable."
                      : token
                      ? data.runs.length === 0
                        ? "No recorded agent runs. Run make demo-seed, start the local stack, then run make demo-flow to create a mediated demo run."
                        : "No loaded runs match the current bounded investigation filters. Decision, outcome, and attention filters use only the 100 recent loaded audit events."
                      : "Locked."
                  }
                />
              ) : (
                (workspaceLens === "investigator" ? investigationRuns : data.runs).map((run) => (
                  <button
                    className={run.run_id === selectedRunId ? "run-row selected" : "run-row"}
                    key={run.run_id}
                    type="button"
                    aria-pressed={run.run_id === selectedRunId}
                    onClick={() => setSelectedRunId(run.run_id)}
                  >
                    <span>
                      <strong>{missionFacingLabel(run, run.workspace_id)}</strong>
                      <small>Reported identity: {run.principal_id}</small>
                    </span>
                    <small>
                      Configured governed workspace: {run.workspace_id} · {run.last_tool_name ?? "no tool"}
                    </small>
                    <StatusPill status={run.status} />
                  </button>
                ))
              )}
            </div>
            <div className="timeline-view" role="region" aria-label="Selected run detail" aria-live="polite">
              {selectedRun ? (
                <>
                  <div className="mission-workbench-heading">
                    <div>
                      <p className="eyebrow">Selected mission Workbench</p>
                      <h3>{missionFacingLabel(selectedRun.run, selectedRun.run.workspace_id)}</h3>
                      <dl className="mission-context-facts">
                        <div>
                          <dt>Reported requesting identity</dt>
                          <dd>{selectedRun.run.principal_id}</dd>
                        </div>
                        <div>
                          <dt>Configured governed workspace</dt>
                          <dd>{selectedRun.run.workspace_id}</dd>
                        </div>
                        <div>
                          <dt>Observed governed calls</dt>
                          <dd>{selectedRun.run.tool_call_count}</dd>
                        </div>
                      </dl>
                      <p className="mission-authority-boundary">
                        Ithildin reconstructs mediated activity. It does not start the external
                        agent or verify workspace isolation.
                      </p>
                    </div>
                    <div className="run-actions">
                      <small>Recorded run state · not runner health</small>
                      <StatusPill status={selectedRun.run.status} />
                      <button
                        className="secondary-action"
                        type="button"
                        disabled={exportLoading}
                        onClick={() => void exportRunEvidence(selectedRun.run.run_id)}
                      >
                        <Download aria-hidden="true" size={16} />
                        Export Run Evidence
                      </button>
                    </div>
                  </div>
                  <EvidenceCloseout
                    evidence={selectedRunEvidence}
                    evidenceError={runEvidenceError}
                    exportNotice={exportNotice}
                    signingAvailable={
                      data.systemStatus?.audit_signing.signed_export_available ?? false
                    }
                    verification={data.verification}
                  />
                  <RunDecisionExplanation
                    approvals={data.approvals}
                    preferredRequestId={
                      primaryAttention?.runId === selectedRun.run.run_id
                        ? primaryAttention.requestId
                        : selectedRun.run.last_request_id ?? ""
                    }
                    runDetail={selectedRun}
                    tools={data.tools}
                  />
                  {selectedRun.timeline.length === 0 ? (
                    <>
                      <RunEvidenceSummary run={selectedRun.run} eventCount={0} />
                      <EmptyState text="No correlated audit events yet. Export Run Evidence still returns the safe run summary for this selected run." />
                    </>
                  ) : (
                    <>
                      <RunEvidenceSummary run={selectedRun.run} eventCount={selectedRun.timeline.length} />
                      <RunEvidenceOverview timeline={selectedRun.timeline} />
                      <RunReconstruction timeline={selectedRun.timeline} />
                      <div className="table-wrap compact-table">
                        <table>
                          <thead>
                            <tr>
                              <th>Time</th>
                              <th>Category</th>
                              <th>Status</th>
                              <th>Tool</th>
                              <th>Decision</th>
                              <th>Request</th>
                              <th>Warnings</th>
                              <th>Hash</th>
                            </tr>
                          </thead>
                          <tbody>
                            {selectedRun.timeline.map((event) => (
                              <tr key={event.event_id}>
                                <td>{formatDate(event.timestamp)}</td>
                                <td>{event.event_type}</td>
                                <td><StatusPill status={timelineStatus(event)} /></td>
                                <td>{event.tool_name ?? ""}</td>
                                <td>{event.decision ?? ""}</td>
                                <td>{shortId(event.request_id)}</td>
                                <td>{timelineWarnings(event).map((warning) => (
                                  <span className="warning-chip" key={warning}>{warning}</span>
                                ))}</td>
                                <td>{shortHash(event.event_hash)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </>
                  )}
                </>
              ) : (
                <EmptyState
                  text={
                    token
                      ? "Select a run. Export appears after selecting a run with recorded evidence."
                      : "Locked."
                  }
                />
              )}
            </div>
          </div>
        </Panel>
      </section>

      {workspaceLens === "technical" ? (
      <section className="audit-section destination-screen" data-screen="evidence">
        <Panel
          title="Recent Audit Events"
          purpose="Technical records for reconstruction after the evidence posture and limitations are understood."
          icon={<Activity size={18} />}
        >
          {data.auditEvents.length === 0 ? (
            <EmptyState
              text={
                dashboardError
                  ? "Recent audit data is unavailable."
                  : token
                    ? "No recent audit events."
                    : "Locked."
              }
            />
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
      ) : null}
      </main>
    </div>
  );
}

function NodeConfigurationControl({
  node,
  token,
  onChanged,
}: {
  node: IthildinNode;
  token: string;
  onChanged: () => Promise<void>;
}) {
  const [history, setHistory] = useState<NodeConfigurationHistoryItem[] | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [minimumVersion, setMinimumVersion] = useState(
    scopeString(node.descriptor, "node_version") || "0.1.0",
  );
  const [heartbeatSeconds, setHeartbeatSeconds] = useState("30");
  const [bufferEvents, setBufferEvents] = useState("1000");
  const [validitySeconds, setValiditySeconds] = useState("3600");
  const [assignmentConfirmed, setAssignmentConfirmed] = useState(false);
  const [rollbackSource, setRollbackSource] = useState("");
  const [rollbackConfirmed, setRollbackConfirmed] = useState(false);
  const [nextConfigurationPublicKey, setNextConfigurationPublicKey] = useState("");
  const [trustValiditySeconds, setTrustValiditySeconds] = useState("86400");
  const [trustTransitionConfirmed, setTrustTransitionConfirmed] = useState(false);

  async function loadHistory() {
    if (!token || loadingHistory) return;
    setLoadingHistory(true);
    setActionError(null);
    try {
      const response = await apiRequest<{ configurations: NodeConfigurationHistoryItem[] }>(
        `/nodes/${encodeURIComponent(node.node_id)}/configurations?limit=50`,
        token,
      );
      setHistory(response.configurations);
    } catch (caught) {
      setActionError(errorMessage(caught));
    } finally {
      setLoadingHistory(false);
    }
  }

  async function assignConfiguration(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!assignmentConfirmed) return;
    setActionLoading(true);
    setNotice(null);
    setActionError(null);
    try {
      await apiRequest<NodeConfigurationHistoryItem>(
        `/nodes/${encodeURIComponent(node.node_id)}/configurations`,
        token,
        {
          method: "POST",
          body: JSON.stringify({
            minimum_node_version: minimumVersion,
            heartbeat_interval_seconds: Number(heartbeatSeconds),
            offline_posture: "deny_governed_actions",
            evidence_buffer_max_events: Number(bufferEvents),
            validity_seconds: Number(validitySeconds),
          }),
        },
      );
      setAssignmentConfirmed(false);
      setNotice("Fresh signed desired generation assigned to this Node only.");
      await loadHistory();
      await onChanged();
    } catch (caught) {
      setActionError(errorMessage(caught));
    } finally {
      setActionLoading(false);
    }
  }

  async function rollbackConfiguration(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!rollbackConfirmed || !rollbackSource || node.desired_configuration_generation === null) {
      return;
    }
    setActionLoading(true);
    setNotice(null);
    setActionError(null);
    try {
      const result = await apiRequest<NodeConfigurationHistoryItem>(
        `/nodes/${encodeURIComponent(node.node_id)}/configurations/rollback`,
        token,
        {
          method: "POST",
          body: JSON.stringify({
            source_generation: Number(rollbackSource),
            expected_current_generation: node.desired_configuration_generation,
            validity_seconds: Number(validitySeconds),
          }),
        },
      );
      setRollbackConfirmed(false);
      setRollbackSource("");
      setNotice(
        `Generation ${result.generation} assigned from generation ${result.rollback_source_generation}. Enforcement remains unknown.`,
      );
      await loadHistory();
      await onChanged();
    } catch (caught) {
      setActionError(errorMessage(caught));
    } finally {
      setActionLoading(false);
    }
  }

  async function assignTrustTransition(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      !trustTransitionConfirmed
      || !nextConfigurationPublicKey.trim()
      || !node.configuration_signing_key_id
    ) return;
    setActionLoading(true);
    setNotice(null);
    setActionError(null);
    try {
      await apiRequest<NodeConfigurationTrustTransition>(
        `/nodes/${encodeURIComponent(node.node_id)}/configuration-trust-transitions`,
        token,
        {
          method: "POST",
          body: JSON.stringify({
            expected_current_key_id: node.configuration_signing_key_id,
            next_public_key: nextConfigurationPublicKey.trim(),
            validity_seconds: Number(trustValiditySeconds),
          }),
        },
      );
      setTrustTransitionConfirmed(false);
      setNextConfigurationPublicKey("");
      setNotice("Signed one-Node trust transition assigned. The Node has not staged it yet.");
      await onChanged();
    } catch (caught) {
      setActionError(errorMessage(caught));
    } finally {
      setActionLoading(false);
    }
  }

  const rollbackCandidates = (history ?? []).filter(
    (item) =>
      item.evidence_status === "complete"
      && node.desired_configuration_generation !== null
      && item.generation < node.desired_configuration_generation,
  );
  const actionDisabled = node.status !== "enrolled" || node.evidence_status !== "complete";

  return (
    <details
      className="node-config-control"
      onToggle={(event) => {
        if (event.currentTarget.open && history === null) void loadHistory();
      }}
    >
      <summary>Manage signed desired state</summary>
      <div className="node-config-control-body">
        <div className="node-config-control-warning">
          <ShieldCheck aria-hidden="true" size={18} />
          <p>
            Actions target only this Node. A new desired generation creates drift until the Node
            stores it. Ithildin does not know whether the runner enforces it.
          </p>
        </div>
        <form onSubmit={assignConfiguration}>
          <div className="node-config-control-heading">
            <div>
              <strong>Assign one-Node canary</strong>
              <span>Fresh signed generation; no automatic rollout.</span>
            </div>
          </div>
          <div className="node-config-fields">
            <label>
              <span>Minimum Node version</span>
              <input
                value={minimumVersion}
                onChange={(event) => setMinimumVersion(event.target.value)}
                disabled={actionDisabled || actionLoading}
              />
            </label>
            <label>
              <span>Heartbeat seconds</span>
              <input
                type="number"
                min="15"
                max="300"
                value={heartbeatSeconds}
                onChange={(event) => setHeartbeatSeconds(event.target.value)}
                disabled={actionDisabled || actionLoading}
              />
            </label>
            <label>
              <span>Evidence buffer events</span>
              <input
                type="number"
                min="100"
                max="10000"
                value={bufferEvents}
                onChange={(event) => setBufferEvents(event.target.value)}
                disabled={actionDisabled || actionLoading}
              />
            </label>
            <label>
              <span>Validity seconds</span>
              <input
                type="number"
                min="300"
                max="86400"
                value={validitySeconds}
                onChange={(event) => setValiditySeconds(event.target.value)}
                disabled={actionDisabled || actionLoading}
              />
            </label>
          </div>
          <label className="node-config-confirmation">
            <input
              type="checkbox"
              checked={assignmentConfirmed}
              onChange={(event) => setAssignmentConfirmed(event.target.checked)}
              disabled={actionDisabled || actionLoading}
            />
            <span>I confirm this changes Gateway desired state for this Node only.</span>
          </label>
          <button
            className="secondary-button"
            type="submit"
            disabled={actionDisabled || actionLoading || !assignmentConfirmed}
          >
            Assign signed generation
          </button>
        </form>
        <form onSubmit={rollbackConfiguration}>
          <div className="node-config-control-heading">
            <div>
              <strong>Manual rollback</strong>
              <span>Copies an earlier payload into a new signed generation.</span>
            </div>
            <span>{loadingHistory ? "Loading history…" : `${history?.length ?? 0} generations`}</span>
          </div>
          {rollbackCandidates.length > 0 ? (
            <>
              <label>
                <span>Verified source generation</span>
                <select
                  value={rollbackSource}
                  onChange={(event) => setRollbackSource(event.target.value)}
                  disabled={actionDisabled || actionLoading}
                >
                  <option value="">Select earlier generation</option>
                  {rollbackCandidates.map((item) => (
                    <option key={item.configuration_id} value={item.generation}>
                      Generation {item.generation} · {shortHash(item.configuration_digest)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="node-config-confirmation">
                <input
                  type="checkbox"
                  checked={rollbackConfirmed}
                  onChange={(event) => setRollbackConfirmed(event.target.checked)}
                  disabled={actionDisabled || actionLoading}
                />
                <span>
                  I confirm the current desired generation is {node.desired_configuration_generation}{" "}
                  and accept the resulting storage drift.
                </span>
              </label>
              <button
                className="secondary-button"
                type="submit"
                disabled={actionDisabled || actionLoading || !rollbackSource || !rollbackConfirmed}
              >
                Create rollback generation
              </button>
            </>
          ) : (
            <p className="node-config-empty">
              {loadingHistory
                ? "Loading immutable history…"
                : "No earlier evidence-complete generation is available for rollback."}
            </p>
          )}
        </form>
        <form onSubmit={assignTrustTransition}>
          <div className="node-config-control-heading">
            <div>
              <strong>Stage signing-key rotation</strong>
              <span>One Node, signed by the current key; activation requires Gateway restart.</span>
            </div>
          </div>
          <label>
            <span>Next Ed25519 public key</span>
            <textarea
              value={nextConfigurationPublicKey}
              onChange={(event) => setNextConfigurationPublicKey(event.target.value)}
              placeholder="Base64 public key only — never paste a private key"
              disabled={actionDisabled || actionLoading || !node.configuration_signing_key_id}
              rows={3}
            />
          </label>
          <label>
            <span>Recovery overlap seconds</span>
            <input
              type="number"
              min="600"
              max="604800"
              value={trustValiditySeconds}
              onChange={(event) => setTrustValiditySeconds(event.target.value)}
              disabled={actionDisabled || actionLoading}
            />
          </label>
          <label className="node-config-confirmation">
            <input
              type="checkbox"
              checked={trustTransitionConfirmed}
              onChange={(event) => setTrustTransitionConfirmed(event.target.checked)}
              disabled={actionDisabled || actionLoading}
            />
            <span>
              I confirm this stages a public trust root for this Node only. It does not rotate the
              Gateway, activate fleet rollout, or prove enforcement.
            </span>
          </label>
          <button
            className="secondary-button"
            type="submit"
            disabled={
              actionDisabled
              || actionLoading
              || !trustTransitionConfirmed
              || !nextConfigurationPublicKey.trim()
              || !node.configuration_signing_key_id
            }
          >
            Assign signed trust transition
          </button>
        </form>
        {notice ? <p className="node-config-notice" role="status">{notice}</p> : null}
        {actionError ? <p className="node-config-error" role="alert">{actionError}</p> : null}
      </div>
    </details>
  );
}

function NodeRevocationControl({
  node,
  token,
  onChanged,
}: {
  node: IthildinNode;
  token: string;
  onChanged: () => Promise<void>;
}) {
  const [confirmation, setConfirmation] = useState("");
  const [consequenceConfirmed, setConsequenceConfirmed] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const actionable = node.status === "enrolled" && node.evidence_status === "complete";
  const confirmed = confirmation === node.node_id && consequenceConfirmed;

  async function revokeNode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!actionable || !confirmed || actionLoading) return;
    setActionLoading(true);
    setNotice(null);
    setActionError(null);
    try {
      await apiRequest<JsonObject>(
        `/nodes/${encodeURIComponent(node.node_id)}/revoke`,
        token,
        { method: "POST" },
      );
      setConfirmation("");
      setConsequenceConfirmed(false);
      setNotice(
        "Gateway recorded this Node identity as revoked. Future authenticated Node requests are denied.",
      );
      await onChanged();
    } catch (caught) {
      setActionError(errorMessage(caught));
    } finally {
      setActionLoading(false);
    }
  }

  return (
    <details className="node-config-control node-revocation-control">
      <summary>
        {node.status === "revoked" ? "Node identity revoked" : "Manage Node lifecycle"}
      </summary>
      <div className="node-config-control-body">
        <div className="node-revocation-warning">
          <AlertTriangle aria-hidden="true" size={18} />
          <p>
            Revocation is an irreversible Gateway identity decision in this local preview. It denies
            future signed Node requests, but it does not stop a runner, terminate model inference,
            delete host state, or prove that an endpoint process has stopped.
          </p>
        </div>
        {node.status === "revoked" ? (
          <p className="node-config-empty">
            Revoked {node.revoked_at ? formatDate(node.revoked_at) : "at an unavailable time"}. The
            Gateway will not restore this identity; replacement requires a fresh enrollment.
          </p>
        ) : (
          <form onSubmit={revokeNode}>
            <div className="node-config-control-heading">
              <div>
                <strong>Revoke Gateway identity</strong>
                <span>Target: {node.display_name}</span>
              </div>
            </div>
            <label>
              <span>Type Node ID to confirm</span>
              <input
                autoComplete="off"
                spellCheck="false"
                value={confirmation}
                onChange={(event) => setConfirmation(event.target.value)}
                placeholder={node.node_id}
                disabled={!actionable || actionLoading}
              />
            </label>
            <label className="node-config-confirmation">
              <input
                type="checkbox"
                checked={consequenceConfirmed}
                onChange={(event) => setConsequenceConfirmed(event.target.checked)}
                disabled={!actionable || actionLoading}
              />
              <span>
                I understand this revokes Gateway request authority only and does not control the
                runner, model provider, or host process.
              </span>
            </label>
            <button
              className="danger-button"
              type="submit"
              disabled={!actionable || actionLoading || !confirmed}
            >
              {actionLoading ? "Revoking Node identity…" : "Revoke Node identity"}
            </button>
            {!actionable ? (
              <p className="node-config-empty">
                Revocation is unavailable while enrollment evidence is incomplete.
              </p>
            ) : null}
          </form>
        )}
        {notice ? <p className="node-config-notice" role="status">{notice}</p> : null}
        {actionError ? <p className="node-config-error" role="alert">{actionError}</p> : null}
      </div>
    </details>
  );
}

function NodeConfigurationTrustPosture({
  transition,
}: {
  transition: NodeConfigurationTrustTransition | null;
}) {
  return (
    <div className="node-trust-posture">
      <div className="node-config-control-heading">
        <div>
          <strong>Configuration signing trust</strong>
          <span>{transition ? transition.rotation_state.replace(/_/g, " ") : "No rotation staged"}</span>
        </div>
        {transition ? <StatusPill status={transition.rotation_state} /> : null}
      </div>
      {transition ? (
        <dl>
          <div><dt>Gateway signer</dt><dd>{transition.gateway_key_id ? shortHash(transition.gateway_key_id) : "Unavailable"}</dd></div>
          <div><dt>Node-attested signer</dt><dd>{transition.node_acknowledged_key_id ? shortHash(transition.node_acknowledged_key_id) : "Not acknowledged"}</dd></div>
          <div>
            <dt>{transition.activation_proven ? "Activated transition signer" : "Staged next signer"}</dt>
            <dd>{shortHash(transition.next_key_id)}</dd>
          </div>
          <div><dt>Recovery cutoff</dt><dd>{formatDate(transition.expires_at)}</dd></div>
        </dl>
      ) : (
        <p>No signed per-Node trust transition has been assigned.</p>
      )}
      <p>Trust activation can be proven by key-bound storage acknowledgment. Runner enforcement remains unknown.</p>
    </div>
  );
}

function operatorAttentionItems(data: DashboardData) {
  const items: AttentionItem[] = [];
  let remaining = {
    ...data,
    approvals: [...data.approvals],
    auditEvents: [...data.auditEvents],
    nodes: [...data.nodes],
    patches: [...data.patches],
  };

  while (items.length < 8) {
    const item = firstOperatorAttentionItem(remaining);
    if (!item) {
      break;
    }
    items.push(item);
    if (item.source === "approval") {
      remaining = {
        ...remaining,
        approvals: remaining.approvals.filter(
          (candidate) => candidate.approval.request_id !== item.requestId,
        ),
      };
    } else if (item.source === "failure") {
      remaining = {
        ...remaining,
        auditEvents: remaining.auditEvents.filter(
          (candidate) => candidate.request_id !== item.requestId,
        ),
      };
    } else if (item.source === "recovery") {
      remaining = { ...remaining, patchDiagnostics: null };
    } else if (item.source === "node") {
      remaining = {
        ...remaining,
        nodes: remaining.nodes.filter((candidate) => candidate.node_id !== item.nodeId),
      };
    } else {
      remaining = {
        ...remaining,
        patches: remaining.patches.filter(
          (candidate) => candidate.proposal_id !== item.proposalId,
        ),
      };
    }
  }
  return items;
}

function attentionItemKey(item: AttentionItem) {
  return `${item.source}:${item.requestId || item.proposalId || item.nodeId || item.title}`;
}

function firstOperatorAttentionItem(data: DashboardData): AttentionItem | null {
  const approvalReview = data.approvals[0];
  if (approvalReview) {
    const approval = approvalReview.approval;
    const workspaceId =
      scopeString(approval.one_time_scope, "workspace_id") || "Unavailable";
    const requestingPrincipal =
      scopeObject(approval.one_time_scope, "requesting_principal") ?? approval.principal;
    const requestingIdentity = scopeString(requestingPrincipal, "id") || "Unavailable";
    const run = data.runs.find((candidate) => candidate.last_request_id === approval.request_id);
    const validBinding = approvalReview.review.valid;
    return {
      source: "approval",
      title: approval.summary || "Review pending approval",
      status: approval.status,
      bindingStatus: validBinding ? null : "stale binding",
      consequence: validBinding
        ? "The governed request is held until an operator approves or denies its exact one-time scope."
        : "The approval binding evidence is stale or invalid. Review the source record before taking action.",
      missionLabel: missionFacingLabel(run, workspaceId),
      workspaceId,
      requestingIdentity,
      toolName: approval.tool_name || "Unavailable",
      requestId: approval.request_id,
      policyReason: scopeString(approval.metadata, "policy_reason") || "Policy reason unavailable",
      runId: run?.run_id ?? null,
      proposalId: scopeString(approval.one_time_scope, "proposal_id") || null,
      nodeId: null,
      targetId: run ? "missions" : "approvals",
      actionLabel: validBinding ? "Review decision" : "Review binding evidence",
      occurredAt: approval.expires_at,
    };
  }

  const authorityNode = firstNodeAttentionItem(data.nodes, "authority");
  if (authorityNode) {
    return authorityNode;
  }

  const failure = data.auditEvents.find((event) => event.event_type.endsWith(".failed"));
  if (failure) {
    const metadataRunId = scopeString(failure.metadata, "run_id");
    const run = data.runs.find(
      (candidate) =>
        candidate.run_id === metadataRunId || candidate.last_request_id === failure.request_id,
    );
    const workspaceId = run?.workspace_id ?? "Unavailable";
    return {
      source: "failure",
      title: `${failure.tool_name ?? "Mediated action"} failed`,
      status: "failed",
      bindingStatus: null,
      consequence:
        "Ithildin recorded a failed mediated action. Review the correlated run and evidence before retrying elsewhere.",
      missionLabel: missionFacingLabel(run, workspaceId),
      workspaceId,
      requestingIdentity: run?.principal_id ?? "Unavailable",
      toolName: failure.tool_name ?? "Unavailable",
      requestId: failure.request_id,
      policyReason: "Not applicable to the recorded execution failure",
      runId: run?.run_id ?? null,
      proposalId: null,
      nodeId: null,
      targetId: run ? "missions" : "evidence",
      actionLabel: "Investigate failure",
      occurredAt: failure.timestamp,
    };
  }

  if (data.patchDiagnostics && data.patchDiagnostics.status !== "clean") {
    return {
      source: "recovery",
      title: "Patch recovery review required",
      status: data.patchDiagnostics.status,
      bindingStatus: null,
      consequence:
        "Patch diagnostics require technical review before the affected change path continues.",
      missionLabel: "Patch application diagnostics",
      workspaceId: "Unavailable",
      requestingIdentity: "Unavailable",
      toolName: "Patch application",
      requestId: "",
      policyReason: "Not applicable to recovery diagnostics",
      runId: null,
      proposalId: null,
      nodeId: null,
      targetId: "evidence",
      actionLabel: "Review recovery evidence",
      occurredAt: latestPatchDiagnosticTimestamp(data.patchDiagnostics),
    };
  }

  const operationalNode = firstNodeAttentionItem(data.nodes, "operational");
  if (operationalNode) {
    return operationalNode;
  }

  const proposal = data.patches.find((candidate) => candidate.status === "proposed");
  if (proposal) {
    const run = data.runs.find((candidate) => candidate.last_request_id === proposal.request_id);
    return {
      source: "proposal",
      title: `Review proposed change to ${proposal.path}`,
      status: proposal.status,
      bindingStatus: null,
      consequence:
        "A bounded change has been proposed. It has not been approved or applied by this proposal state.",
      missionLabel: missionFacingLabel(run, proposal.workspace_id),
      workspaceId: proposal.workspace_id,
      requestingIdentity: run?.principal_id ?? "Unavailable",
      toolName: run?.last_tool_name ?? "Unavailable",
      requestId: proposal.request_id,
      policyReason: "No pending approval reason is loaded for this proposal",
      runId: run?.run_id ?? null,
      proposalId: proposal.proposal_id,
      nodeId: null,
      targetId: run ? "missions" : "artifacts",
      actionLabel: "Review proposal",
      occurredAt: proposal.updated_at,
    };
  }

  return null;
}

function nodeNeedsAttention(node: IthildinNode) {
  return nodeAttentionPosture(node) !== null;
}

function firstNodeAttentionItem(
  nodes: IthildinNode[],
  attentionClass: NodeAttentionClass,
): AttentionItem | null {
  const candidates: { node: IthildinNode; posture: NodeAttentionPosture }[] = [];
  for (const node of nodes) {
    const posture = nodeAttentionPosture(node);
    if (posture?.attentionClass === attentionClass) {
      candidates.push({ node, posture });
    }
  }
  candidates.sort((left, right) =>
    left.posture.rank - right.posture.rank
    || (right.posture.occurredAt ?? "").localeCompare(left.posture.occurredAt ?? "")
    || left.node.node_id.localeCompare(right.node.node_id),
  );
  const selected = candidates[0];
  if (!selected) return null;
  const { node, posture } = selected;
  return {
    source: "node",
    title: posture.title,
    status: posture.status,
    bindingStatus: null,
    consequence: posture.consequence,
    missionLabel: `${node.workspace_id} Node fleet`,
    workspaceId: node.workspace_id,
    requestingIdentity: node.principal_id,
    toolName: "Ithildin Gateway",
    requestId: "",
    policyReason: posture.observedBasis,
    runId: null,
    proposalId: null,
    nodeId: node.node_id,
    targetId: "nodes",
    actionLabel: posture.actionLabel,
    occurredAt: posture.occurredAt,
  };
}

function nodeAttentionPosture(node: IthildinNode): NodeAttentionPosture | null {
  if (node.status !== "enrolled") return null;
  if (node.evidence_status !== "complete") {
    return {
      attentionClass: "authority",
      rank: 0,
      title: `${node.display_name} identity evidence is incomplete`,
      status: "evidence incomplete",
      consequence:
        "The Gateway Node record is fail-closed because enrollment or lifecycle audit evidence has not completed. Review evidence before relying on this identity.",
      actionLabel: "Review identity evidence",
      observedBasis: "Gateway Node administrative and audit-evidence state",
      occurredAt: node.updated_at,
    };
  }
  if (node.observed_state === "evidence_incomplete") {
    return {
      attentionClass: "authority",
      rank: 1,
      title: `${node.display_name} connectivity evidence is incomplete`,
      status: "evidence incomplete",
      consequence:
        "Gateway records cannot establish a current connectivity posture. Runner, model, and host-process health remain unknown.",
      actionLabel: "Review connectivity evidence",
      observedBasis: "Gateway-derived Node evidence and accepted-heartbeat state",
      occurredAt: node.updated_at,
    };
  }
  if (node.identity_key_rotation?.evidence_status === "pending") {
    return {
      attentionClass: "authority",
      rank: 2,
      title: `${node.display_name} identity-key evidence is pending`,
      status: "identity evidence pending",
      consequence:
        "Identity-key rotation evidence has not completed. Review Gateway evidence before relying on the displayed key posture.",
      actionLabel: "Review identity-key evidence",
      observedBasis: "Gateway identity-key rotation and audit-evidence state",
      occurredAt:
        node.identity_key_rotation.activated_at ?? node.identity_key_rotation.created_at,
    };
  }
  const transition = node.configuration_trust_transition;
  if (
    transition
    && (
      transition.evidence_status !== "complete"
      || transition.acknowledgment_evidence_status === "pending"
      || transition.rotation_state === "gateway_advanced_node_pending"
      || transition.rotation_state === "transition_expired_not_activated"
    )
  ) {
    const expired = transition.rotation_state === "transition_expired_not_activated";
    const gatewayAdvanced = transition.rotation_state === "gateway_advanced_node_pending";
    return {
      attentionClass: "authority",
      rank: 3,
      title: expired
        ? `${node.display_name} signing-trust transition expired`
        : gatewayAdvanced
          ? `${node.display_name} has not acknowledged active signing trust`
          : `${node.display_name} signing-trust evidence is incomplete`,
      status: transition.rotation_state.replace(/_/g, " "),
      consequence:
        "Gateway and Node signing-trust evidence is not aligned. Review the transition before relying on configuration distribution posture.",
      actionLabel: "Review signing-trust evidence",
      observedBasis: "Gateway configuration trust-transition and Node acknowledgment evidence",
      occurredAt: transition.acknowledged_at ?? transition.issued_at,
    };
  }
  if (node.configuration_state === "evidence_incomplete") {
    return {
      attentionClass: "authority",
      rank: 4,
      title: `${node.display_name} configuration evidence is incomplete`,
      status: "configuration evidence incomplete",
      consequence:
        "The Gateway cannot establish a current signed desired-configuration comparison. Enforcement remains unknown.",
      actionLabel: "Review configuration evidence",
      observedBasis: "Gateway desired-configuration and Node storage-acknowledgment evidence",
      occurredAt: node.configuration_acknowledged_at ?? node.updated_at,
    };
  }
  if (node.version_posture === "evidence_incomplete") {
    return {
      attentionClass: "authority",
      rank: 5,
      title: `${node.display_name} version evidence is incomplete`,
      status: "version evidence incomplete",
      consequence:
        "The Gateway cannot establish the Node version comparison from current signed desired and heartbeat evidence.",
      actionLabel: "Review version evidence",
      observedBasis: "Signed desired minimum and Gateway-accepted heartbeat version evidence",
      occurredAt: node.last_seen_at ?? node.updated_at,
    };
  }
  if (node.version_posture === "below_minimum") {
    return {
      attentionClass: "operational",
      rank: 20,
      title: `${node.display_name} is below the desired minimum version`,
      status: "below minimum",
      consequence:
        "The signed heartbeat reports a version below the signed desired minimum. Maintenance is operator-managed; package authenticity and process health are unknown.",
      actionLabel: "Review version posture",
      observedBasis: "Gateway-accepted signed heartbeat compared with signed desired configuration",
      occurredAt: node.last_seen_at ?? node.updated_at,
    };
  }
  if (node.configuration_state === "configuration_drift") {
    return {
      attentionClass: "operational",
      rank: 21,
      title: `${node.display_name} configuration does not match desired state`,
      status: "configuration drift",
      consequence:
        "The Node's recorded configuration acknowledgment does not match Gateway desired state. Storage and enforcement are separate; enforcement remains unknown.",
      actionLabel: "Review configuration drift",
      observedBasis: "Gateway desired configuration compared with Node storage acknowledgment",
      occurredAt: node.configuration_acknowledged_at ?? node.updated_at,
    };
  }
  if (node.observed_state === "stale") {
    return {
      attentionClass: "operational",
      rank: 22,
      title: `${node.display_name} heartbeat is stale`,
      status: "heartbeat stale",
      consequence:
        "The Gateway has not recently accepted a correctly signed heartbeat. This does not establish runner, model, or host-process health.",
      actionLabel: "Review connectivity evidence",
      observedBasis: "Age of the latest Gateway-accepted signed heartbeat",
      occurredAt: node.last_seen_at,
    };
  }
  if (
    node.observed_state === "never_observed"
    || node.version_posture === "never_observed"
  ) {
    return {
      attentionClass: "operational",
      rank: 23,
      title: `${node.display_name} has never sent an accepted heartbeat`,
      status: "never observed",
      consequence:
        "Enrollment is complete, but the Gateway has never accepted a signed heartbeat from this Node. Runner, model, and host-process health are unknown.",
      actionLabel: "Review enrollment posture",
      observedBasis: "Gateway enrollment record with no accepted heartbeat timestamp",
      occurredAt: node.enrolled_at,
    };
  }
  return null;
}

function filterAndSortNodes(
  nodes: IthildinNode[],
  query: string,
  posture: string,
  workspace: string,
  sort: string,
) {
  const normalizedQuery = query.trim().toLocaleLowerCase();
  return nodes
    .filter((node) => {
      if (workspace !== "all" && node.workspace_id !== workspace) return false;
      if (posture === "attention" && !nodeNeedsAttention(node)) return false;
      if (posture === "enrolled" && node.status !== "enrolled") return false;
      if (posture === "revoked" && node.status !== "revoked") return false;
      if (
        !["all", "attention", "enrolled", "revoked"].includes(posture)
        && node.observed_state !== posture
      ) return false;
      if (!normalizedQuery) return true;
      return [
        node.display_name,
        node.node_id,
        node.principal_id,
        node.workspace_id,
        scopeString(node.descriptor, "runner_adapter"),
        scopeString(node.descriptor, "deployment_topology"),
        node.observed_state,
        node.configuration_state,
        node.version_posture,
      ].some((value) => value.toLocaleLowerCase().includes(normalizedQuery));
    })
    .sort((left, right) => {
      const byName = left.display_name.localeCompare(right.display_name)
        || left.node_id.localeCompare(right.node_id);
      if (sort === "name") return byName;
      if (sort === "workspace") {
        return left.workspace_id.localeCompare(right.workspace_id) || byName;
      }
      if (sort === "last-seen") {
        return (right.last_seen_at ?? "").localeCompare(left.last_seen_at ?? "") || byName;
      }
      const leftRank = nodeAttentionPosture(left)?.rank ?? 100;
      const rightRank = nodeAttentionPosture(right)?.rank ?? 100;
      if (leftRank !== rightRank) return leftRank - rightRank;
      if (left.status !== right.status) return left.status === "enrolled" ? -1 : 1;
      return byName;
    });
}

function missionFacingLabel(run: AgentRun | undefined, workspaceId: string) {
  if (run && isDemoRun(run)) {
    return "Guided local demo mission";
  }
  if (run) {
    return `${workspaceId} mediated run`;
  }
  return `${workspaceId} workspace`;
}

function RunnerGovernancePosture({ run }: { run: AgentRun | null }) {
  const fixedStdioIdentity =
    run?.principal_id === "agent:mcp-local" && run.session_id === "mcp-stdio";
  const hermesTrackA = fixedStdioIdentity && run?.workspace_id === "hermes-poc";

  return (
    <section className="runner-governance-posture" aria-label="External runner governance posture">
      <div className="runner-posture-heading">
        <div>
          <p className="eyebrow">External runner posture</p>
          <h3>{hermesTrackA ? "Hermes Track A compatibility fixture" : "Recorded ingress posture"}</h3>
        </div>
        <span className="posture-claim">Governed calls only</span>
      </div>
      <dl>
        <div>
          <dt>Runner</dt>
          <dd>{hermesTrackA ? "Operator-started Hermes" : "Not identified by Gateway"}</dd>
        </div>
        <div>
          <dt>Connection</dt>
          <dd>{fixedStdioIdentity ? "Local stdio MCP" : "Recorded ingress only"}</dd>
        </div>
        <div>
          <dt>Reported identity</dt>
          <dd>{run?.principal_id ?? "No run selected"}</dd>
        </div>
        <div>
          <dt>Lifecycle authority</dt>
          <dd>Unmanaged · no launch or health control</dd>
        </div>
      </dl>
      <p>
        {hermesTrackA
          ? "Track A shares its synthetic workspace with the runner. Ithildin proves policy and execution outcomes for recorded MCP calls, not filesystem isolation or all runner activity."
          : "Ithildin reconstructs recorded mediated activity. It does not infer the runner process, model inference, health, or isolation from run state."}
      </p>
    </section>
  );
}

function DestinationHeading({
  eyebrow,
  title,
  description,
  icon,
}: {
  eyebrow: string;
  title: string;
  description: string;
  icon: React.ReactNode;
}) {
  return (
    <header className="destination-heading">
      <span className="destination-heading-icon" aria-hidden="true">
        {icon}
      </span>
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      <span className="destination-mode">Local governed view</span>
    </header>
  );
}

function AttentionHeading({ count }: { count: number }) {
  return (
    <header className="attention-heading">
      <div>
        <p className="eyebrow">Priority queue</p>
        <h2 id="attention-heading">Your attention</h2>
        <p>
          {count} {count === 1 ? "item" : "items"} sorted by deterministic workflow priority
        </p>
      </div>
    </header>
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
  id,
  title,
  purpose,
  icon,
  children,
}: {
  id?: string;
  title: string;
  purpose?: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="panel" id={id} aria-label={`${title} panel`} tabIndex={id ? -1 : undefined}>
      <header className="panel-header">
        {icon}
        <div>
          <h2>{title}</h2>
          {purpose ? <p>{purpose}</p> : null}
        </div>
      </header>
      {children}
    </section>
  );
}

function EmptyState({ text }: { text: string }) {
  return <div className="empty-state">{text}</div>;
}

function OperatorWorkbenchGuide() {
  const steps = [
    ["1", "Preflight"],
    ["2", "Seed/run"],
    ["3", "Inspect"],
    ["4", "Export"],
    ["5", "Cleanup"],
  ];
  return (
    <div className="operator-demo-guide" aria-label="Operator workbench demo path">
      <div>
        <strong>Demo Path</strong>
        <span>Local path: preflight, demo run, evidence review, export, cleanup. No run controls.</span>
      </div>
      <ol>
        {steps.map(([number, label]) => (
          <li key={number}>
            <span>{number}</span>
            {label}
          </li>
        ))}
      </ol>
    </div>
  );
}

function RunSummary({ summary }: { summary: AgentRunSummary }) {
  const filters = Object.entries(summary.filters)
    .filter((entry): entry is [string, string] => typeof entry[1] === "string")
    .map(([key, value]) => `${key}=${value}`);
  return (
    <div className="run-summary" aria-label="Agent run query summary">
      <span>{summary.returned} runs</span>
      <span>{countSummary(summary.statuses) || "no statuses"}</span>
      <span>{countSummary(summary.workspaces) || "no workspaces"}</span>
      <span>{countSummary(summary.tools) || "no tools"}</span>
      <span>{filters.length > 0 ? filters.join(" · ") : "unfiltered"}</span>
      <span>
        {summary.latest_updated_at ? `latest ${formatDate(summary.latest_updated_at)}` : "no updates"}
      </span>
    </div>
  );
}

function RunFilterChips({
  investigationFilters,
  onClearAll,
  onClearInvestigation,
  onClearServer,
  runFilters,
}: {
  investigationFilters: InvestigationFilters;
  onClearAll: () => void;
  onClearInvestigation: (name: keyof InvestigationFilters) => void;
  onClearServer: (name: keyof RunFilters) => void;
  runFilters: RunFilters;
}) {
  const serverChips = Object.entries(runFilters).filter((entry) => entry[1].trim());
  const investigationChips = Object.entries(investigationFilters).filter(
    ([name, value]) => value && value !== "all" && !(name === "mission" && !value.trim()),
  );
  if (serverChips.length === 0 && investigationChips.length === 0) {
    return null;
  }
  return (
    <div className="run-filter-chips" aria-label="Active run filters">
      <strong>Active filters</strong>
      {serverChips.map(([name, value]) => (
        <button key={name} type="button" onClick={() => onClearServer(name as keyof RunFilters)}>
          {runFilterLabel(name)}: {value} ×
        </button>
      ))}
      {investigationChips.map(([name, value]) => (
        <button
          key={name}
          type="button"
          onClick={() => onClearInvestigation(name as keyof InvestigationFilters)}
        >
          {runFilterLabel(name)}: {value.replace(/_/g, " ")} ×
        </button>
      ))}
      <button className="clear-all-filters" type="button" onClick={onClearAll}>
        Clear all
      </button>
    </div>
  );
}

function InvestigationSummary({
  auditEvents,
  loadedCount,
  runs,
}: {
  auditEvents: AuditEvent[];
  loadedCount: number;
  runs: AgentRun[];
}) {
  const observedAttention = runs.filter((run) => runObservedAttention(run, auditEvents)).length;
  const missions = new Set(runs.map((run) => missionFacingLabel(run, run.workspace_id))).size;
  return (
    <div className="investigation-summary" aria-label="Bounded investigation summary">
      <span>{runs.length} of {loadedCount} loaded runs shown</span>
      <span>{missions} presentation mission groups</span>
      <span>{observedAttention} with observed attention</span>
      <span>decision/outcome scope: 100 recent audit events</span>
      <small>
        Mission labels are presentation context. Counts describe loaded Ithildin records, not
        external agent or process activity, anomaly detection, or incident state.
      </small>
    </div>
  );
}

function runFilterLabel(name: string) {
  const labels: Record<string, string> = {
    principal_id: "Identity",
    workspace_id: "Workspace",
    status: "Run status",
    tool_name: "Tool",
    time_range: "Last update",
    mission: "Mission context",
    decision: "Observed decision",
    outcome: "Observed outcome",
    attention: "Observed attention",
  };
  return labels[name] ?? name;
}

function EvidenceCloseout({
  evidence,
  evidenceError,
  exportNotice,
  signingAvailable,
  verification,
}: {
  evidence: RunEvidenceExport | null;
  evidenceError: string | null;
  exportNotice: ExportNotice | null;
  signingAvailable: boolean;
  verification: AuditVerification | null;
}) {
  if (!evidence) {
    return (
      <section className="evidence-closeout" aria-label="Run evidence closeout">
        <div className="evidence-closeout-heading">
          <div>
            <p className="eyebrow">Evidence · selected run closeout</p>
            <h4>Evidence closeout</h4>
          </div>
          <StatusPill status={evidenceError ? "unavailable" : "preparing"} />
        </div>
        <p>{evidenceError || "Preparing the existing redacted run evidence snapshot."}</p>
      </section>
    );
  }

  const applicationCount = evidence.timeline.filter(
    (event) =>
      scopeString(event, "category") === "tool.execution.completed" &&
      scopeString(event, "tool_name") === "fs.patch.apply",
  ).length;
  const signedReferenceCount = evidence.signed_export_references.length;
  const runExportNotice =
    exportNotice?.scope === "run" &&
    exportNotice.runId === scopeString(evidence.run, "run_id")
      ? exportNotice
      : null;
  const verificationLabel = verification
    ? verification.valid
      ? `Verified for ${verification.event_count} currently loaded local audit events`
      : "Verification failed"
    : "Verification unavailable";

  return (
    <section className="evidence-closeout" aria-label="Run evidence closeout">
      <div className="evidence-closeout-heading">
        <div>
          <p className="eyebrow">Evidence · selected run closeout</p>
          <h4>Evidence closeout</h4>
        </div>
        <StatusPill status={evidence.summary.warning_count === 0 ? "snapshot ready" : "warnings"} />
      </div>
      <p className="evidence-scope">
        Generated redacted snapshot for {evidence.summary.principal_id} in {evidence.summary.workspace_id}.
        It covers recorded Ithildin-mediated activity for this run only.
      </p>
      <div className="evidence-closeout-grid">
        <article>
          <span>Recorded run evidence</span>
          <strong>{evidence.summary.audit_event_count} events in snapshot</strong>
          <small>
            {evidence.summary.tool_call_count} tool calls · {evidence.summary.approval_count} correlated approvals · {applicationCount} recorded patch applications
          </small>
        </article>
        <article>
          <span>Evidence completeness</span>
          <strong>
            {evidence.summary.warning_count === 0
              ? "No reported bundle warnings"
              : `${evidence.summary.warning_count} bundle warnings`}
          </strong>
          <small>Zero warnings would not prove off-platform activity is represented.</small>
        </article>
        <article>
          <span>Local audit-chain verification</span>
          <strong>{verificationLabel}</strong>
          <small>Not host-compromise resistance, immutable custody, or independent attestation.</small>
        </article>
        <article>
          <span>Signing state</span>
          <strong>
            {signedReferenceCount > 0
              ? `${signedReferenceCount} signed evidence references included`
              : "Run snapshot has no signed evidence reference"}
          </strong>
          <small>
            {signingAvailable
              ? "Signed audit export is available separately; this snapshot is not thereby signed."
              : "Signing key/export is unavailable in the current local configuration."}
          </small>
        </article>
        <article role="status" aria-live="polite">
          <span>Browser export response</span>
          <strong>
            {runExportNotice
              ? runExportNotice.state === "failed"
                ? "Export failed"
                : "Download initiated"
              : "Not exported in this browser session"}
          </strong>
          <small>{runExportNotice?.message ?? "No custody or receipt claim is available."}</small>
        </article>
        <article>
          <span>Excluded from run snapshot</span>
          <strong>{evidence.redaction_summary.excluded_categories.length} sensitive categories</strong>
          <small>{evidence.redaction_summary.excluded_categories.join(", ")}</small>
        </article>
      </div>
      {evidence.warnings.length > 0 ? (
        <div className="evidence-warning-summary">
          <strong>Snapshot limitations</strong>
          <ul>
            {evidence.warnings.map((warning, index) => (
              <li key={`${scopeString(warning, "type")}-${index}`}>
                {scopeString(warning, "type") || "unspecified warning"}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <details className="evidence-closeout-technical">
        <summary>Technical closeout evidence</summary>
        <dl className="meta-list evidence-closeout-meta">
          <div>
            <dt>Snapshot</dt>
            <dd>{shortId(evidence.export_id)}</dd>
          </div>
          <div>
            <dt>Generated</dt>
            <dd>{formatDate(evidence.exported_at)}</dd>
          </div>
          <div>
            <dt>Schema</dt>
            <dd>{evidence.schema_version}</dd>
          </div>
          <div>
            <dt>Evidence hashes</dt>
            <dd>{Object.keys(evidence.evidence_hashes).length}</dd>
          </div>
        </dl>
        <pre>{JSON.stringify(evidence, null, 2)}</pre>
      </details>
    </section>
  );
}

function RunEvidenceSummary({ run, eventCount }: { run: AgentRun; eventCount: number }) {
  return (
    <div className="run-summary" aria-label="Run evidence summary">
      <span>Run Evidence</span>
      {isDemoRun(run) ? <span className="demo-label">demo</span> : null}
      <span>{run.tool_call_count} tool calls</span>
      <span>{eventCount} audit events</span>
      <span>{run.last_tool_name ?? "no tool"}</span>
      <span>{run.policy_hash ? shortHash(run.policy_hash) : "no policy"}</span>
      <span>{run.last_tool_manifest_hash ? shortHash(run.last_tool_manifest_hash) : "no manifest"}</span>
    </div>
  );
}

function RunDecisionExplanation({
  approvals,
  preferredRequestId,
  runDetail,
  tools,
}: {
  approvals: ApprovalReview[];
  preferredRequestId: string;
  runDetail: AgentRunDetail;
  tools: ToolSummary[];
}) {
  const decisionEvent = findDecisionEvent(runDetail.timeline, preferredRequestId);
  const requestId = decisionEvent?.request_id ?? preferredRequestId;
  const approvalReview = approvals.find(
    (candidate) => candidate.approval.request_id === requestId,
  );
  const tool = tools.find((candidate) => candidate.name === decisionEvent?.tool_name);

  if (!decisionEvent) {
    return (
      <section className="decision-explanation" aria-label="Governed request decision">
        <div className="decision-explanation-heading">
          <div>
            <p className="eyebrow">Workbench · recorded policy evidence</p>
            <h4>Governed request decision</h4>
          </div>
          <StatusPill status="unavailable" />
        </div>
        <p>
          No correlated policy decision is present for the selected request. Ithildin does not infer
          an allow, denial, or approval requirement from the tool or run status.
        </p>
        <dl className="meta-list decision-context">
          <div>
            <dt>Reported requesting identity</dt>
            <dd>{runDetail.run.principal_id}</dd>
          </div>
          <div>
            <dt>Operator-managed workspace</dt>
            <dd>{runDetail.run.workspace_id}</dd>
          </div>
          <div>
            <dt>Request</dt>
            <dd>{requestId ? shortId(requestId) : "Unavailable"}</dd>
          </div>
        </dl>
      </section>
    );
  }

  const decision = decisionEvent.decision ?? "unavailable";
  const policyReason =
    (approvalReview && scopeString(approvalReview.approval.metadata, "policy_reason")) ||
    scopeString(decisionEvent.metadata, "policy_reason") ||
    scopeString(decisionEvent.metadata, "reason");
  const approvalRules = approvalReview
    ? scopeList(approvalReview.approval.one_time_scope, "matched_rules")
    : [];
  const matchedRules =
    approvalRules.length > 0
      ? approvalRules
      : scopeList(decisionEvent.metadata, "matched_rules");
  const executionState = correlatedExecutionState(runDetail.timeline, decisionEvent.request_id);
  const resourceLabel = decisionEvent.resource
    ? scopeString(decisionEvent.resource, "path") ||
      scopeString(decisionEvent.resource, "url") ||
      "Safe resource metadata available"
    : "Resource summary unavailable";

  return (
    <section className="decision-explanation" aria-label="Governed request decision">
      <div className="decision-explanation-heading">
        <div>
          <p className="eyebrow">Workbench · recorded policy evidence</p>
          <h4>Governed request decision</h4>
        </div>
        <StatusPill status={decision} />
      </div>
      <ol className="decision-questions">
        <li>
          <span>What did the agent request?</span>
          <p>
            {tool?.title ?? decisionEvent.tool_name ?? "Mediated tool request"}
            {decisionEvent.tool_name ? ` (${decisionEvent.tool_name})` : ""} for {resourceLabel}.
          </p>
        </li>
        <li>
          <span>What did Ithildin decide?</span>
          <p>{operatorDecisionLabel(decision)}.</p>
        </li>
        <li>
          <span>Why?</span>
          <p>{policyReason || "Reason not present in the correlated policy evidence."}</p>
        </li>
        <li>
          <span>What was the operational consequence?</span>
          <p>{decisionConsequence(decision, executionState)}</p>
        </li>
        <li>
          <span>Is human action required?</span>
          <p>{decisionAction(decision, approvalReview)}</p>
        </li>
        <li>
          <span>What evidence is available?</span>
          <p>
            Recorded request, policy decision, event hash, and run correlation
            {approvalReview ? ", plus pending approval binding evidence" : ""}.
          </p>
        </li>
      </ol>
      <p className="registration-boundary">
        {tool
          ? `${tool.title} is registered as ${tool.name}. Registration identifies the reviewed tool definition; it does not grant permission. This request received the recorded decision above.`
          : "A matching registered-tool summary is not loaded. The recorded policy decision remains authoritative for this request."}
      </p>
      <details className="technical-decision-evidence">
        <summary>Technical decision evidence</summary>
        <dl className="meta-list decision-context">
          <div>
            <dt>Reported requesting identity</dt>
            <dd>{runDetail.run.principal_id}</dd>
          </div>
          <div>
            <dt>Operator-managed workspace</dt>
            <dd>{runDetail.run.workspace_id}</dd>
          </div>
          <div>
            <dt>Request</dt>
            <dd>{shortId(decisionEvent.request_id)}</dd>
          </div>
          <div>
            <dt>Policy fingerprint</dt>
            <dd>
              {scopeString(decisionEvent.metadata, "policy_hash")
                ? shortHash(scopeString(decisionEvent.metadata, "policy_hash"))
                : "Unavailable for this request"}
            </dd>
          </div>
          <div>
            <dt>Tool definition fingerprint</dt>
            <dd>
              {scopeString(decisionEvent.metadata, "manifest_hash")
                ? shortHash(scopeString(decisionEvent.metadata, "manifest_hash"))
                : "Unavailable for this request"}
            </dd>
          </div>
          <div>
            <dt>Matched rules</dt>
            <dd>{matchedRules.length > 0 ? matchedRules.join(", ") : "Unavailable"}</dd>
          </div>
          <div>
            <dt>Decision event</dt>
            <dd>{shortId(decisionEvent.event_id)}</dd>
          </div>
          <div>
            <dt>Event hash</dt>
            <dd>{shortHash(decisionEvent.event_hash)}</dd>
          </div>
          <div>
            <dt>Recorded execution state</dt>
            <dd>{executionState}</dd>
          </div>
        </dl>
      </details>
    </section>
  );
}

function findDecisionEvent(timeline: AgentRunTimelineEvent[], preferredRequestId: string) {
  if (preferredRequestId) {
    return timeline.find(
      (event) => event.request_id === preferredRequestId && Boolean(event.decision),
    );
  }
  for (let index = timeline.length - 1; index >= 0; index -= 1) {
    if (timeline[index].decision) {
      return timeline[index];
    }
  }
  return undefined;
}

function correlatedExecutionState(timeline: AgentRunTimelineEvent[], requestId: string) {
  const correlated = timeline.filter((event) => event.request_id === requestId);
  if (correlated.some((event) => event.event_type.endsWith(".failed"))) {
    return "failed";
  }
  if (correlated.some((event) => event.event_type === "tool.execution.completed")) {
    return "completed";
  }
  if (correlated.some((event) => event.event_type === "tool.execution.started")) {
    return "started";
  }
  return "not recorded";
}

function operatorDecisionLabel(decision: string) {
  if (decision === "allow") {
    return "Allowed";
  }
  if (decision === "deny") {
    return "Denied";
  }
  if (decision === "require_approval") {
    return "Approval required";
  }
  return `Recorded as ${decision}`;
}

function decisionConsequence(decision: string, executionState: string) {
  if (decision === "deny") {
    return "Gateway blocked the governed request. No governed execution should follow this decision.";
  }
  if (decision === "require_approval") {
    return executionState === "not recorded"
      ? "The request is held until the exact approval requirement is satisfied. No execution is recorded."
      : `Policy required approval. The separately recorded execution state is ${executionState}.`;
  }
  if (decision === "allow") {
    return executionState === "not recorded"
      ? "Policy allowed the request, but no execution result is present in the correlated evidence."
      : `Policy allowed the request. The separately recorded execution state is ${executionState}.`;
  }
  return `The correlated execution state is ${executionState}; no additional consequence is inferred.`;
}

function decisionAction(decision: string, approvalReview: ApprovalReview | undefined) {
  if (decision === "require_approval") {
    if (!approvalReview) {
      return "Approval was required, but no matching pending approval is loaded. Review the timeline and approval history.";
    }
    return approvalReview.review.valid
      ? "Review the matching pending approval and its exact one-time scope."
      : "Do not decide the request until the stale or invalid approval binding is reviewed.";
  }
  if (decision === "deny") {
    return "No approval action is available for this denied request. Investigate or change the request through an authorized workflow.";
  }
  if (decision === "allow") {
    return "No policy decision is required. Review the separate execution outcome if the mission depends on it.";
  }
  return "Review technical evidence before taking action.";
}

function ArtifactLifecycleSummary({
  approvals,
  pendingApprovalReview,
  proposal,
  onOpenApproval,
}: {
  approvals: Approval[];
  pendingApprovalReview: ApprovalReview | undefined;
  proposal: PatchProposal;
  onOpenApproval: () => void;
}) {
  const currentApproval = preferredProposalApproval(approvals);
  const pendingApproval = approvals.find((approval) => approval.status === "pending");
  const { additions, removals } = diffLineCounts(proposal.unified_diff ?? "");
  const applied = proposal.status === "applied";

  return (
    <section className="artifact-lifecycle" aria-label="Selected artifact lifecycle">
      <div className="artifact-summary-heading">
        <div>
          <p className="eyebrow">Artifact review · recorded lifecycle</p>
          <h4>{applied ? "Applied change ready for operator review" : "Proposed change"}</h4>
        </div>
        <StatusPill
          status={proposalLifecycleStatus(proposal, approvals)}
        />
      </div>
      <p className="artifact-change-summary">
        {applied ? "Recorded application changed" : "Proposal would change"} {proposal.path} with {additions} addition
        {additions === 1 ? "" : "s"} and {removals} removal{removals === 1 ? "" : "s"}. This
        summary is generated from the diff and is not semantic or security review.
      </p>
      <div className="artifact-lifecycle-steps">
        <article>
          <span>1 · Proposal</span>
          <strong>{proposal.status}</strong>
          <small>Recorded {formatDate(proposal.created_at)}</small>
        </article>
        <article>
          <span>2 · Approval</span>
          <strong>{currentApproval?.status ?? "not recorded"}</strong>
          <small>
            {currentApproval
              ? `${proposalRequester(approvals)} · expires ${formatDate(currentApproval.expires_at)}`
              : "Requesting identity unavailable without a correlated approval"}
          </small>
        </article>
        <article>
          <span>3 · Application</span>
          <strong>{applied ? "recorded applied" : "not applied"}</strong>
          <small>Proposal updated {formatDate(proposal.updated_at)}; no application time is inferred</small>
        </article>
        <article>
          <span>4 · Operator review</span>
          <strong>not recorded</strong>
          <small>Ithildin has no review-complete or promotion mutation for this artifact</small>
        </article>
      </div>
      <div className="artifact-next-action">
        <strong>Next action</strong>
        <p>{proposalNextAction(proposal, approvals, pendingApprovalReview)}</p>
        {pendingApproval ? (
          <button
            type="button"
            disabled={!pendingApprovalReview?.review.valid}
            onClick={onOpenApproval}
          >
            Open matching pending approval
          </button>
        ) : null}
      </div>
      <p className="artifact-state-boundary">
        {applied
          ? "Applied means the governed patch operation was recorded. It does not mean reviewed, promoted, published, release-ready, or externally deployed."
          : "Proposed means a bounded change record exists. It does not mean approved, applied, reviewed, or ready for release."}
      </p>
    </section>
  );
}

function approvalsForProposal(history: Approval[], proposalId: string) {
  return history.filter(
    (approval) => scopeString(approval.one_time_scope, "proposal_id") === proposalId,
  );
}

function pendingReviewForProposal(history: ApprovalReview[], proposalId: string) {
  return history.find(
    (review) => scopeString(review.approval.one_time_scope, "proposal_id") === proposalId,
  );
}

function preferredProposalApproval(approvals: Approval[]) {
  return (
    approvals.find((approval) => approval.status === "pending") ??
    approvals[0]
  );
}

function latestPatchDiagnosticTimestamp(diagnostics: PatchApplyDiagnostics) {
  const candidates = [...diagnostics.attempts, ...diagnostics.stuck_approvals]
    .map(
      (record) =>
        scopeString(record, "updated_at") ||
        scopeString(record, "created_at") ||
        scopeString(record, "expires_at"),
    )
    .filter(Boolean)
    .sort((left, right) => right.localeCompare(left));
  return candidates[0] ?? null;
}

function proposalRequester(approvals: Approval[]) {
  const approval = preferredProposalApproval(approvals);
  if (!approval) {
    return "Unavailable";
  }
  const scopedPrincipal = scopeObject(approval.one_time_scope, "requesting_principal");
  return scopeString(scopedPrincipal ?? approval.principal, "id") || "Unavailable";
}

function proposalLifecycleStatus(
  proposal: PatchProposal,
  approvals: Approval[],
) {
  if (proposal.status === "applied") {
    return "applied";
  }
  const approval = preferredProposalApproval(approvals);
  if (approval?.status === "pending") {
    return "approval required";
  }
  return approval?.status ?? proposal.status;
}

function proposalNextAction(
  proposal: PatchProposal,
  approvals: Approval[],
  pendingApprovalReview?: ApprovalReview,
) {
  if (proposal.status === "applied") {
    return "Review the applied artifact and evidence; no review-complete or promotion action exists.";
  }
  const approval = preferredProposalApproval(approvals);
  if (approval?.status === "pending") {
    return pendingApprovalReview?.review.valid
      ? "Review the exact pending approval scope before approving or denying."
      : "Review the stale or invalid approval binding; approval is disabled.";
  }
  if (approval?.status === "denied") {
    return "No approval action remains. Revise the change through an authorized workflow if needed.";
  }
  if (approval?.status === "expired" || approval?.status === "superseded") {
    return "The prior approval is no longer actionable. Review history before requesting new work.";
  }
  return "Inspect the proposal and evidence; no matching pending approval is recorded.";
}

function diffLineCounts(unifiedDiff: string) {
  return unifiedDiff.split("\n").reduce(
    (counts, line) => {
      if (line.startsWith("+") && !line.startsWith("+++")) {
        counts.additions += 1;
      } else if (line.startsWith("-") && !line.startsWith("---")) {
        counts.removals += 1;
      }
      return counts;
    },
    { additions: 0, removals: 0 },
  );
}

function filterAndSortPatches(
  patches: PatchProposal[],
  query: string,
  status: string,
  sort: string,
) {
  const normalizedQuery = query.trim().toLocaleLowerCase();
  return patches
    .filter(
      (patch) =>
        status === "all" || patch.status === status,
    )
    .filter((patch) =>
      normalizedQuery
        ? [patch.path, patch.workspace_id, patch.request_id, patch.proposal_id].some((value) =>
            value.toLocaleLowerCase().includes(normalizedQuery),
          )
        : true,
    )
    .sort((left, right) => {
      if (sort === "path-asc") {
        return left.path.localeCompare(right.path) || left.proposal_id.localeCompare(right.proposal_id);
      }
      const direction = sort === "updated-asc" ? 1 : -1;
      return direction * left.updated_at.localeCompare(right.updated_at) || left.proposal_id.localeCompare(right.proposal_id);
    });
}

function groupPatchesByWorkspace(patches: PatchProposal[]) {
  const groups = new Map<string, PatchProposal[]>();
  for (const patch of patches) {
    groups.set(patch.workspace_id, [...(groups.get(patch.workspace_id) ?? []), patch]);
  }
  return [...groups.entries()].sort(([left], [right]) => left.localeCompare(right));
}

function DemoLabel({ run }: { run: AgentRun }) {
  return isDemoRun(run) ? (
    <span className="demo-label" title="Guided local demo evidence">
      demo
    </span>
  ) : null;
}

function isDemoRun(run: AgentRun) {
  return (
    run.metadata.scenario === "guided_local_demo" ||
    run.metadata.demo_step === "mediated_patch_flow" ||
    run.metadata.model_client_label === "guided_local_demo"
  );
}

function RunEvidenceOverview({ timeline }: { timeline: AgentRunTimelineEvent[] }) {
  const categories = countTimelineValues(timeline, timelineCategory);
  const statuses = countTimelineValues(timeline, timelineStatus);
  const decisions = countTimelineValues(timeline, (event) => event.decision ?? "");
  const requests = new Set(timeline.map((event) => event.request_id).filter(Boolean));
  const warningCount = timeline.reduce(
    (count, event) => count + timelineWarnings(event).length,
    0,
  );
  return (
    <div className="run-evidence-overview" aria-label="Grouped run evidence">
      <EvidenceGroup title="Evidence Types" items={categories} empty="no categories" />
      <EvidenceGroup title="Statuses" items={statuses} empty="no statuses" />
      <EvidenceGroup title="Decisions" items={decisions} empty="no decisions" />
      <div className="evidence-group">
        <h4>Correlation</h4>
        <div className="evidence-chip-list">
          <span>{requests.size} requests</span>
          <span>{warningCount} warnings</span>
        </div>
      </div>
    </div>
  );
}

function RunReconstruction({ timeline }: { timeline: AgentRunTimelineEvent[] }) {
  const observed = new Set(timeline.map(timelineCategory));
  const completed = timeline.some((event) => timelineStatus(event) === "completed");
  const failed = timeline.some((event) => timelineStatus(event) === "failed");
  const steps = [
    ["tool", "Tool Call", observed.has("tool") || timeline.some((event) => event.tool_name)],
    ["policy", "Policy Decision", observed.has("policy") || timeline.some((event) => event.decision)],
    ["approval", "Approval", observed.has("approval")],
    ["executor", "Executor Result", completed || failed],
    ["export", "Audit/Export", observed.has("export") || timeline.some((event) => event.event_hash)],
  ] as const;
  return (
    <div className="run-reconstruction" aria-label="Observed run reconstruction">
      <strong>Observed Reconstruction</strong>
      <ol>
        {steps.map(([key, label, isObserved]) => (
          <li className={isObserved ? "observed" : "pending"} key={key}>
            <span>{isObserved ? "observed" : "pending"}</span>
            {label}
          </li>
        ))}
      </ol>
    </div>
  );
}

function EvidenceGroup({
  title,
  items,
  empty,
}: {
  title: string;
  items: Record<string, number>;
  empty: string;
}) {
  const entries = Object.entries(items).sort((left, right) => right[1] - left[1]);
  return (
    <div className="evidence-group">
      <h4>{title}</h4>
      <div className="evidence-chip-list">
        {entries.length === 0 ? (
          <span>{empty}</span>
        ) : (
          entries.map(([label, count]) => <span key={label}>{label} ({count})</span>)
        )}
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  return (
    <span className={`status-pill status-${status.replace(/[\s_]+/g, "-")}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

function ApprovalEvidence({
  approval,
  review,
}: {
  approval: Approval;
  review?: BindingReview;
}) {
  const scope = approval.one_time_scope;
  const groups = [
    {
      title: "Patch Artifact",
      items: evidenceItems([
        ["Proposal", scopeString(scope, "proposal_id")],
        ["Proposal hash", scopeString(scope, "proposal_hash")],
        ["Base hash", scopeString(scope, "base_file_hash")],
        ["Target", scopeString(scope, "path")],
        ["Workspace", scopeString(scope, "workspace_id")],
      ]),
    },
    {
      title: "Tool Manifest",
      items: evidenceItems([
        ["Tool", scopeString(scope, "tool_name") || approval.tool_name],
        ["Manifest hash", scopeString(scope, "manifest_hash")],
        ["Manifest version", scopeString(scope, "manifest_version")],
        ["Input schema", scopeString(scope, "tool_input_schema_hash")],
      ]),
    },
    {
      title: "Policy Decision",
      items: evidenceItems([
        ["Policy engine", scopeString(scope, "policy_engine")],
        ["Policy hash", scopeString(scope, "policy_hash")],
        ["Policy version", scopeString(scope, "policy_version")],
        ["Policy doc", scopeString(scope, "policy_document_version")],
        ["Matched rules", scopeList(scope, "matched_rules").join(", ")],
        ["Policy reason", scopeString(approval.metadata, "policy_reason")],
      ]),
    },
    {
      title: "Principal and Scope",
      items: evidenceItems([
        [
          "Principal",
          formatJsonCompact(scopeObject(scope, "requesting_principal") ?? approval.principal),
        ],
        ["Request hash", scopeString(scope, "request_hash") || approval.request_hash],
        ["Expires", scopeString(scope, "expires_at") || approval.expires_at],
        ["Scope hash", scopeString(approval.metadata, "approval_scope_hash")],
      ]),
    },
  ].filter((group) => group.items.length > 0);

  if (groups.length === 0) {
    return null;
  }

  return (
    <section className="evidence-block" aria-label={`Approval evidence for ${approval.approval_id}`}>
      <div className="evidence-heading">
        <h4>Binding Evidence</h4>
        <button
          className="copy-button"
          type="button"
          onClick={() => void copyApprovalEvidence(approval, review)}
        >
          <Copy aria-hidden="true" size={14} />
          Copy
        </button>
      </div>
      <div className="evidence-sections">
        {groups.map((group) => (
          <section className="evidence-subsection" key={group.title}>
            <h5>{group.title}</h5>
            <dl className="evidence-grid">
              {group.items.map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd title={value}>{formatEvidenceValue(value)}</dd>
                </div>
              ))}
            </dl>
          </section>
        ))}
      </div>
    </section>
  );
}

function PatchDiagnosticsSummary({ diagnostics }: { diagnostics: PatchApplyDiagnostics }) {
  const recommendations = diagnostics.recommendations
    .map((item) => scopeString(item, "message"))
    .filter(Boolean);
  return (
    <section className="diagnostics-block" aria-label="Patch apply diagnostics">
      <div className="diagnostics-heading">
        <h3>Patch Apply Diagnostics</h3>
        <StatusPill status={diagnostics.status} />
      </div>
      <dl className="meta-list preview-meta">
        <div>
          <dt>Incomplete Attempts</dt>
          <dd>{diagnostics.attempts.length}</dd>
        </div>
        <div>
          <dt>Stuck Approvals</dt>
          <dd>{diagnostics.stuck_approvals.length}</dd>
        </div>
        <div>
          <dt>Recommended Action</dt>
          <dd>{scopeString(diagnostics.recommendations[0] ?? {}, "type") || "none"}</dd>
        </div>
      </dl>
      {recommendations.length > 0 ? (
        <ul className="recommendation-list">
          {recommendations.map((recommendation) => (
            <li key={recommendation}>{recommendation}</li>
          ))}
        </ul>
      ) : null}
      {diagnostics.attempts.length > 0 ? (
        <div className="table-wrap diagnostics-table">
          <table>
            <caption>Incomplete patch apply attempts</caption>
            <thead>
              <tr>
                <th>Attempt</th>
                <th>Approval</th>
                <th>Proposal</th>
                <th>Workspace</th>
                <th>Path</th>
                <th>Status</th>
                <th>Expected Hash</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {diagnostics.attempts.map((attempt, index) => (
                <tr key={scopeString(attempt, "attempt_id") || `attempt-${index}`}>
                  <td title={scopeString(attempt, "attempt_id")}>
                    {shortId(scopeString(attempt, "attempt_id") || "unknown")}
                  </td>
                  <td title={scopeString(attempt, "approval_id")}>
                    {shortId(scopeString(attempt, "approval_id") || "unknown")}
                  </td>
                  <td title={scopeString(attempt, "proposal_id")}>
                    {shortId(scopeString(attempt, "proposal_id") || "unknown")}
                  </td>
                  <td>{scopeString(attempt, "workspace_id") || "default"}</td>
                  <td title={scopeString(attempt, "path")}>{scopeString(attempt, "path") || "-"}</td>
                  <td>{scopeString(attempt, "diagnostic_status") || scopeString(attempt, "status") || "-"}</td>
                  <td>{scopeBooleanStatus(attempt, "current_matches_expected_post_apply_hash")}</td>
                  <td title={scopeString(attempt, "diagnostic_reason") || scopeString(attempt, "failure_reason")}>
                    {scopeString(attempt, "diagnostic_reason") ||
                      scopeString(attempt, "failure_reason") ||
                      "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {diagnostics.stuck_approvals.length > 0 ? (
        <div className="table-wrap diagnostics-table">
          <table>
            <caption>Executing patch approvals needing review</caption>
            <thead>
              <tr>
                <th>Approval</th>
                <th>Request</th>
                <th>Proposal</th>
                <th>Workspace</th>
                <th>Path</th>
                <th>Attempt</th>
              </tr>
            </thead>
            <tbody>
              {diagnostics.stuck_approvals.map((approval, index) => (
                <tr key={scopeString(approval, "approval_id") || `approval-${index}`}>
                  <td title={scopeString(approval, "approval_id")}>
                    {shortId(scopeString(approval, "approval_id") || "unknown")}
                  </td>
                  <td title={scopeString(approval, "request_id")}>
                    {shortId(scopeString(approval, "request_id") || "unknown")}
                  </td>
                  <td title={scopeString(approval, "proposal_id")}>
                    {shortId(scopeString(approval, "proposal_id") || "unknown")}
                  </td>
                  <td>{scopeString(approval, "workspace_id") || "default"}</td>
                  <td title={scopeString(approval, "path")}>{scopeString(approval, "path") || "-"}</td>
                  <td>{scopeBooleanStatus(approval, "has_apply_attempt")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
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

async function copyApprovalEvidence(approval: Approval, review?: BindingReview) {
  const payload = {
    approval_id: approval.approval_id,
    request_id: approval.request_id,
    request_hash: approval.request_hash,
    tool_name: approval.tool_name,
    status: approval.status,
    expires_at: approval.expires_at,
    one_time_scope: approval.one_time_scope,
    metadata: approval.metadata,
    review_summary: review
      ? {
          valid: review.valid,
          checks: review.checks,
          reasons: review.reasons,
          proposal: review.proposal,
        }
      : undefined,
  };
  await navigator.clipboard?.writeText(JSON.stringify(payload, null, 2));
}

function runListPath(filters: {
  principal_id: string;
  workspace_id: string;
  status: string;
  tool_name: string;
}) {
  const query = new URLSearchParams({ limit: "25" });
  for (const [key, value] of Object.entries(filters)) {
    const trimmed = value.trim();
    if (trimmed) {
      query.set(key, trimmed);
    }
  }
  return `/runs?${query.toString()}`;
}

function filterInvestigationRuns(
  runs: AgentRun[],
  auditEvents: AuditEvent[],
  filters: InvestigationFilters,
) {
  const now = Date.now();
  const rangeMilliseconds: Record<string, number> = {
    "24h": 24 * 60 * 60 * 1000,
    "7d": 7 * 24 * 60 * 60 * 1000,
    "30d": 30 * 24 * 60 * 60 * 1000,
  };
  const missionQuery = filters.mission.trim().toLocaleLowerCase();
  return runs.filter((run) => {
    const events = observedAuditEventsForRun(run, auditEvents);
    const range = rangeMilliseconds[filters.time_range];
    if (range && now - new Date(run.updated_at).getTime() > range) {
      return false;
    }
    if (
      missionQuery &&
      !missionFacingLabel(run, run.workspace_id).toLocaleLowerCase().includes(missionQuery)
    ) {
      return false;
    }
    if (
      filters.decision !== "all" &&
      !events.some((event) => event.decision === filters.decision)
    ) {
      return false;
    }
    if (filters.outcome !== "all" && runObservedOutcome(events) !== filters.outcome) {
      return false;
    }
    const attention = runObservedAttention(run, auditEvents);
    if (filters.attention === "attention" && !attention) {
      return false;
    }
    if (filters.attention === "none" && attention) {
      return false;
    }
    return true;
  });
}

function observedAuditEventsForRun(run: AgentRun, auditEvents: AuditEvent[]) {
  return auditEvents.filter(
    (event) =>
      scopeString(event.metadata, "run_id") === run.run_id ||
      (Boolean(run.last_request_id) && event.request_id === run.last_request_id),
  );
}

function runObservedOutcome(events: AuditEvent[]) {
  if (events.some((event) => event.event_type.endsWith(".failed"))) {
    return "failed";
  }
  if (events.some((event) => event.event_type === "tool.execution.completed")) {
    return "completed";
  }
  if (events.some((event) => event.event_type === "tool.execution.started")) {
    return "started";
  }
  return "unavailable";
}

function runObservedAttention(run: AgentRun, auditEvents: AuditEvent[]) {
  return observedAuditEventsForRun(run, auditEvents).some(
    (event) =>
      event.event_type.endsWith(".failed") ||
      event.decision === "deny" ||
      event.decision === "require_approval",
  );
}

function countSummary(counts: Record<string, number>) {
  const [first] = Object.entries(counts).sort((left, right) => right[1] - left[1]);
  return first ? `${first[0]} (${first[1]})` : "";
}

function countTimelineValues(
  timeline: AgentRunTimelineEvent[],
  getValue: (event: AgentRunTimelineEvent) => string,
) {
  const counts: Record<string, number> = {};
  for (const event of timeline) {
    const value = getValue(event);
    if (value) {
      counts[value] = (counts[value] ?? 0) + 1;
    }
  }
  return counts;
}

function timelineCategory(event: AgentRunTimelineEvent) {
  const eventType = event.event_type;
  if (eventType.startsWith("policy.")) {
    return "policy";
  }
  if (eventType.startsWith("approval.")) {
    return "approval";
  }
  if (eventType.startsWith("tool.")) {
    return "tool";
  }
  if (eventType.includes("export")) {
    return "export";
  }
  if (eventType.includes("diagnostic") || eventType.includes("recovery")) {
    return "diagnostic";
  }
  return "audit";
}

function timelineStatus(event: AgentRunTimelineEvent) {
  if (event.event_type.endsWith(".completed")) {
    return "completed";
  }
  if (event.event_type.endsWith(".failed")) {
    return "failed";
  }
  if (event.event_type.endsWith(".started")) {
    return "started";
  }
  return event.decision ?? "recorded";
}

function timelineWarnings(event: AgentRunTimelineEvent) {
  const warnings: string[] = [];
  if (event.event_type.endsWith(".failed")) {
    warnings.push("failure");
  }
  if (!event.event_hash) {
    warnings.push("missing hash");
  }
  if (event.metadata.redaction_count && Number(event.metadata.redaction_count) > 0) {
    warnings.push("redacted");
  }
  return warnings;
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
    throw await apiErrorFromResponse(response);
  }
  return (await response.json()) as T;
}

async function apiErrorFromResponse(response: Response) {
  let detail = response.statusText;
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") {
      detail = payload.detail;
    }
  } catch {
    // Fall back to the HTTP status text.
  }
  return new ApiError(response.status, detail);
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

function scopeBooleanStatus(scope: JsonObject, key: string) {
  const value = scope[key];
  if (value === true) {
    return "yes";
  }
  if (value === false) {
    return "no";
  }
  return "unknown";
}

function formatJsonCompact(value: JsonObject) {
  return JSON.stringify(value);
}

function evidenceItems(items: Array<[string, string | undefined]>) {
  return items.filter((entry): entry is [string, string] => Boolean(entry[1]));
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

function trustStateWarnings(
  systemStatus: SystemStatus | null,
  verification: AuditVerification | null,
  diagnostics: PatchApplyDiagnostics | null,
) {
  const warnings = new Set(systemStatus?.security.warnings ?? []);
  if (systemStatus?.security.dev_admin_token.sample_token_active) {
    warnings.add("sample admin token is active");
  }
  if (systemStatus?.security.admin_token.weak) {
    warnings.add("admin token should be rotated");
  }
  if (systemStatus?.security.cors.wildcard_allowed) {
    warnings.add("wildcard CORS is enabled");
  }
  if (systemStatus?.security.local_only.remote_mcp_enabled) {
    warnings.add("remote MCP is enabled");
  }
  if (systemStatus?.manifest_lock.required === false) {
    warnings.add("manifest lock enforcement is disabled");
  }
  if (
    systemStatus?.manifest_lock.signature.required &&
    !systemStatus.manifest_lock.signature.verified
  ) {
    warnings.add("required manifest-lock signature is not verified");
  }
  if (
    systemStatus?.filesystem &&
    !systemStatus.filesystem.support.local_preview_security_supported
  ) {
    warnings.add(`filesystem support: ${systemStatus.filesystem.support.status}`);
  }
  if (verification && !verification.valid) {
    warnings.add("audit chain verification failed");
  }
  if (diagnostics && diagnostics.status !== "clean") {
    warnings.add(`patch apply diagnostics: ${diagnostics.status}`);
  }
  return Array.from(warnings);
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

function scrollAndFocusElement(id: string) {
  const target = document.getElementById(id);
  if (!target) {
    return;
  }
  const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
  target.scrollIntoView?.({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
  target.focus({ preventScroll: true });
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

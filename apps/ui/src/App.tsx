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
  path: string;
  base_file_hash: string;
  proposal_hash: string;
  status: string;
  created_at: string;
  updated_at: string;
  metadata: JsonObject;
  unified_diff?: string;
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

type DashboardData = {
  approvals: Approval[];
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
    approvals: [],
    patches: [],
    auditEvents: [],
    verification: null,
  });
  const [selectedProposalId, setSelectedProposalId] = useState<string | null>(null);
  const [selectedProposal, setSelectedProposal] = useState<PatchProposal | null>(null);
  const [denyReasons, setDenyReasons] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pendingCount = data.approvals.length;
  const proposedPatchCount = data.patches.filter((patch) => patch.status === "proposed").length;
  const recentFailures = data.auditEvents.filter((event) => event.event_type.endsWith(".failed"));

  const selectedPatchFromList = useMemo(
    () => data.patches.find((patch) => patch.proposal_id === selectedProposalId) ?? null,
    [data.patches, selectedProposalId],
  );

  async function loadDashboard(activeToken = token) {
    if (!activeToken) {
      setData({ approvals: [], patches: [], auditEvents: [], verification: null });
      setSelectedProposal(null);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const [approvalsResponse, patchesResponse, auditResponse, verificationResponse] =
        await Promise.all([
          apiRequest<{ approvals: Approval[] }>("/approvals?status=pending", activeToken),
          apiRequest<{ patch_proposals: PatchProposal[] }>("/patch-proposals", activeToken),
          apiRequest<{ audit_events: AuditEvent[] }>("/audit-events?limit=100", activeToken),
          apiRequest<AuditVerification>("/audit-events/verify", activeToken),
        ]);
      setData({
        approvals: approvalsResponse.approvals,
        patches: patchesResponse.patch_proposals,
        auditEvents: auditResponse.audit_events,
        verification: verificationResponse,
      });
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
      setData({ approvals: [], patches: [], auditEvents: [], verification: null });
      setSelectedProposal(null);
    }
  }

  async function exportAuditBundle() {
    setExportLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/audit-events/export`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new ApiError(response.status, response.statusText);
      }
      const bundle = await response.blob();
      const objectUrl = URL.createObjectURL(bundle);
      const anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = "ithildin-audit-export.jsonl";
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

      <section className="summary-strip" aria-label="Review summary">
        <Metric icon={<ClipboardList size={20} />} label="Pending" value={pendingCount} />
        <Metric icon={<FileDiff size={20} />} label="Proposed patches" value={proposedPatchCount} />
        <Metric icon={<AlertTriangle size={20} />} label="Recent failures" value={recentFailures.length} />
        <button className="refresh-button" type="button" onClick={() => void loadDashboard()}>
          <RefreshCcw aria-hidden="true" size={18} />
          {loading ? "Refreshing" : "Refresh"}
        </button>
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
            <button
              className="export-button"
              type="button"
              disabled={!token || exportLoading}
              onClick={() => void exportAuditBundle()}
            >
              <Download aria-hidden="true" size={18} />
              {exportLoading ? "Exporting" : "Export JSONL"}
            </button>
          </div>
        </Panel>
      </section>

      <section className="review-grid">
        <Panel title="Pending Approvals" icon={<ClipboardList size={18} />}>
          {data.approvals.length === 0 ? (
            <EmptyState text={token ? "No pending approvals." : "Locked."} />
          ) : (
            <div className="approval-list">
              {data.approvals.map((approval) => (
                <article className="approval-item" key={approval.approval_id}>
                  <div className="item-heading">
                    <div>
                      <h3>{approval.summary}</h3>
                      <p>{approval.tool_name}</p>
                    </div>
                    <StatusPill status={approval.status} />
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
                  </dl>
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
                      onClick={() => void decideApproval(approval.approval_id, "approve")}
                    >
                      <Check aria-hidden="true" size={16} />
                      Approve
                    </button>
                  </div>
                </article>
              ))}
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
                      <p>{shortId(selectedProposal.proposal_id)}</p>
                    </div>
                    <StatusPill status={selectedProposal.status} />
                  </div>
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

/* Extracted from pages/SettingsPage.tsx (settings decomposition, slice 2). */

import { GlassPanel } from "../../components/GlassPanel";
import { StatusChip } from "../../components/StatusChip";
import { ControlField } from "../../components/settings/ControlField";
import { ControlAuditRow, CriticalNotificationAuditRow, CriticalNotificationReadiness, fetchAiControlAuthorityAudit, fetchCriticalNotificationAudit, fetchCriticalNotificationReadiness, fetchRiskControlAudit, testCriticalNotificationDelivery } from "../../data/api";
import { formatIsoForDisplay, formatUnknownValue } from "./formatters";
import { useEffect, useState } from "react";

export function ControlAuditTrailPanel() {
  const [rows, setRows] = useState<Array<ControlAuditRow & { family: "Risk" | "AI" }>>([]);
  const [status, setStatus] = useState("");

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    setStatus("");
    const [risk, ai] = await Promise.all([
      fetchRiskControlAudit(8),
      fetchAiControlAuthorityAudit(8),
    ]);
    const merged = [
      ...((risk?.rows ?? []).map((row) => ({ ...row, family: "Risk" as const }))),
      ...((ai?.rows ?? []).map((row) => ({ ...row, family: "AI" as const }))),
    ].sort((a, b) => String(b.at ?? "").localeCompare(String(a.at ?? "")));
    setRows(merged.slice(0, 12));
    if (!risk && !ai) setStatus("Control audit trail unavailable - is the API reachable?");
  }

  return (
    <GlassPanel title="Control Audit Trail" subtitle="Recent owner, operator, and risk-cap changes">
      <div className="positions-table-wrap ai-dial-table-wrap">
        <table className="data-table ai-dial-table control-audit-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Area</th>
              <th>Action</th>
              <th>Source</th>
              <th>Change</th>
              <th>Money</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={`${row.audit_id ?? row.at ?? "audit"}-${index}`}>
                <td className="mono">{row.at ? formatIsoForDisplay(row.at) : "unknown"}</td>
                <td>{row.family}</td>
                <td className="mono">{row.action ?? "UNKNOWN"}</td>
                <td className="ai-dial-detail">{row.source ?? "unknown"}</td>
                <td>{formatAuditChanges(row)}</td>
                <td>
                  <StatusChip
                    label={row.external_money_movement ? "MONEY MOVED" : "NO MONEY MOVE"}
                    variant={row.external_money_movement ? "danger" : "success"}
                    size="sm"
                  />
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6}>No control changes have been audited yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="mobile-api-row" style={{ marginTop: 10 }}>
        <button className="mobile-api-button ghost" type="button" onClick={() => void refresh()}>Refresh audit</button>
      </div>
      {status && <div className="control-field-desc" style={{ color: "var(--danger)" }}>{status}</div>}
    </GlassPanel>
  );
}


export function formatAuditChanges(row: ControlAuditRow): string {
  const changes = row.changes ?? [];
  if (!changes.length) return "No field delta recorded";
  const shown = changes.slice(0, 3).map((change) => {
    const scope = change.scope ? `${change.scope}:` : "";
    const posture = change.posture ? ` (${change.posture})` : "";
    return `${scope}${change.key ?? "field"} ${formatUnknownValue(change.before)} to ${formatUnknownValue(change.after)}${posture}`;
  });
  const extra = changes.length > shown.length ? ` +${changes.length - shown.length} more` : "";
  return shown.join("; ") + extra;
}


export function CriticalNotificationAuditPanel() {
  const [rows, setRows] = useState<CriticalNotificationAuditRow[]>([]);
  const [readiness, setReadiness] = useState<CriticalNotificationReadiness | null>(null);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    setStatus("");
    const [report, readinessReport] = await Promise.all([
      fetchCriticalNotificationAudit(10),
      fetchCriticalNotificationReadiness(10),
    ]);
    if (!report) {
      setRows([]);
      setStatus("Critical notification audit unavailable - is the API reachable?");
      return;
    }
    setRows(report.rows ?? []);
    setReadiness(readinessReport);
  }

  async function sendCriticalAlertTest() {
    setBusy(true);
    setStatus("");
    try {
      const result = await testCriticalNotificationDelivery();
      if (!result.ok) {
        setStatus(`Critical alert test failed: ${result.error.message}`);
        return;
      }
      if (result.data.readiness) {
        setReadiness(result.data.readiness);
      }
      if (result.data.audit) {
        setRows((previous) => [result.data.audit!, ...previous].slice(0, 10));
      } else {
        await refresh();
      }
      const delivery = result.data.readiness?.status ?? "UNKNOWN";
      setStatus(
        result.data.status === "DISPATCHED"
          ? `Critical alert test emitted. Delivery readiness is now ${delivery}.`
          : "No off-screen critical alert destination exists yet; local in-app alerts remain active.",
      );
    } catch (error) {
      setStatus(`Critical alert test failed: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setBusy(false);
    }
  }

  const localChannel = readiness?.local_in_app_alert_channel;
  const deliveryStatus = readiness?.status ?? "UNKNOWN";
  const deliveryDanger = deliveryStatus === "DELIVERY_FAILING" || deliveryStatus === "PARTIAL_DELIVERY";

  return (
    <GlassPanel title="Critical Notification Audit" subtitle="Recent operational alerts and webhook delivery attempts">
      <div className="ai-dial-summary" style={{ marginBottom: 10 }}>
        <ControlField
          label="Delivery Status"
          value={deliveryStatus}
          danger={deliveryDanger}
          mono
          description={readiness?.next_action ?? "Critical notification delivery readiness is loading."}
        />
        <ControlField
          label="Local In-App Alerts"
          value={localChannel?.status ?? "UNKNOWN"}
          mono
          description={`CriticalAlertStrip polls every ${localChannel?.poll_interval_seconds ?? 60}s; visible warning/alert rows: ${localChannel?.visible_warning_or_alert_count ?? 0}.`}
        />
        <ControlField
          label="Off-Screen Delivery"
          value={readiness?.offscreen_delivery_status ?? "UNKNOWN"}
          danger={readiness?.offscreen_delivery_status === "DELIVERY_FAILING"}
          mono
          description={readiness?.owner_setup_required_for_offscreen_alerts ? "Webhook setup is optional for off-screen alerts; local in-app alerts remain active." : "Webhook destination is configured."}
        />
        <ControlField label="Webhook Destinations" value={String(readiness?.subscription_count ?? 0)} mono />
        <ControlField
          label="Recent Delivery"
          value={`${readiness?.recent_dispatch_success_count ?? 0}/${readiness?.recent_dispatch_attempt_count ?? 0}`}
          mono
          description={readiness?.blockers?.join("; ") || readiness?.claim_boundary}
        />
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap">
        <table className="data-table ai-dial-table critical-notification-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Event</th>
              <th>Severity</th>
              <th>Delivery</th>
              <th>Detail</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={`${row.audit_id ?? row.at ?? "critical"}-${index}`}>
                <td className="mono">{row.at ? formatIsoForDisplay(row.at) : "unknown"}</td>
                <td>
                  <div className="ai-dial-name">{row.event?.title ?? row.event?.event_kind ?? "Critical event"}</div>
                  <div className="ai-dial-key mono">{row.event?.event_kind ?? "UNKNOWN"}</div>
                </td>
                <td>
                  <StatusChip
                    label={(row.event?.severity ?? "info").toUpperCase()}
                    variant={criticalSeverityVariant(row.event?.severity)}
                    size="sm"
                  />
                </td>
                <td>
                  <StatusChip
                    label={`${row.dispatch_success_count ?? 0}/${row.dispatch_attempt_count ?? 0} SENT`}
                    variant={(row.dispatch_success_count ?? 0) > 0 ? "success" : (row.dispatch_attempt_count ?? 0) > 0 ? "warning" : "muted"}
                    size="sm"
                  />
                  {row.skipped && <div className="ai-dial-detail">{row.skipped}</div>}
                </td>
                <td>{row.event?.body ?? "No detail recorded."}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={5}>No critical notification events have been audited yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="mobile-api-row" style={{ marginTop: 10 }}>
        <button className="mobile-api-button" type="button" disabled={busy} onClick={() => void sendCriticalAlertTest()}>
          {busy ? "Sending test..." : "Send critical alert test"}
        </button>
        <button className="mobile-api-button ghost" type="button" disabled={busy} onClick={() => void refresh()}>Refresh alerts</button>
      </div>
      {status && (
        <div
          className="control-field-desc"
          style={{
            color:
              status.toLowerCase().includes("failed")
              ? "var(--danger)"
              : status.toLowerCase().includes("no off-screen")
                ? "var(--warning)"
                : "var(--success)",
          }}
        >
          {status}
        </div>
      )}
    </GlassPanel>
  );
}


export function criticalSeverityVariant(severity: string | undefined): "success" | "warning" | "danger" | "muted" {
  const key = (severity ?? "").toLowerCase();
  if (key === "alert") return "danger";
  if (key === "warning") return "warning";
  if (key === "info") return "success";
  return "muted";
}


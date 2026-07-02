/* ── CAS Forex — Stack Status Page ── */

import { useCallback, useEffect, useState } from "react";
import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import { fetchStackHealth } from "../data/api";
import type { StackHealthCheckResult, StackHealthReport } from "../data/api";
import "./StackStatusPage.css";

type ChipVariant = "success" | "warning" | "danger" | "muted" | "info";

function statusVariant(status: string): ChipVariant {
  const s = (status || "").toUpperCase();
  if (s === "OK" || s === "PASS" || s === "PASSED") return "success";
  if (s === "DEGRADED" || s === "WARN" || s === "WARNING") return "warning";
  if (s === "MISSING" || s === "FAIL" || s === "FAILED") return "danger";
  if (s === "UNKNOWN") return "muted";
  return "info";
}

export function StackStatusPage() {
  const [report, setReport] = useState<StackHealthReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshedAt, setRefreshedAt] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    const data = await fetchStackHealth();
    if (data) {
      setReport(data);
      setError(null);
      setRefreshedAt(new Date().toISOString());
    } else {
      setError("Stack health endpoint unreachable.");
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
    const id = window.setInterval(load, 30_000);
    return () => window.clearInterval(id);
  }, [load]);

  const checks: StackHealthCheckResult[] = report?.checks ?? [];

  return (
    <div className="stack-status-page">
      <GlassPanel
        title="Stack Health"
        subtitle="Read-only operational snapshot — polled every 30 s"
      >
        <div className="stack-status-row">
          <div className="lead-field">
            <span className="field-label">Overall status</span>
            <span className="field-value">
              {report ? (
                <StatusChip
                  label={report.overall_status || "UNKNOWN"}
                  variant={statusVariant(report.overall_status)}
                />
              ) : (
                <StatusChip label={loading ? "LOADING" : "UNAVAILABLE"} variant="muted" />
              )}
            </span>
          </div>
          <div className="lead-field">
            <span className="field-label">Last fetched</span>
            <span className="field-value mono">{refreshedAt ?? "—"}</span>
          </div>
        </div>
        {error && <div className="api-status-strip">{error}</div>}
        {report?.plain_english_summary && (
          <p className="plain-english-block">{report.plain_english_summary}</p>
        )}
      </GlassPanel>

      <GlassPanel title="Checks" subtitle="One row per subsystem">
        <table className="stack-status-table">
          <thead>
            <tr>
              <th>Check</th>
              <th>Status</th>
              <th>Headline</th>
              <th>Detail</th>
            </tr>
          </thead>
          <tbody>
            {checks.length === 0 && (
              <tr>
                <td colSpan={4} className="muted-cell">
                  {loading ? "Loading…" : "No checks returned."}
                </td>
              </tr>
            )}
            {checks.map((c) => (
              <tr key={c.name}>
                <td className="mono">{c.name}</td>
                <td>
                  <StatusChip
                    label={c.status || "UNKNOWN"}
                    variant={statusVariant(c.status)}
                    size="sm"
                  />
                </td>
                <td>{c.headline}</td>
                <td className="muted-cell">{c.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </GlassPanel>

      <GlassPanel
        title="Remediation steps"
        subtitle="Verbatim next_actions from the backend"
      >
        {report?.next_actions && report.next_actions.length > 0 ? (
          <ol className="stack-remediation-list">
            {report.next_actions.map((step, i) => (
              <li key={i} className="mono">
                {step}
              </li>
            ))}
          </ol>
        ) : (
          <div className="muted-cell">No remediation steps reported.</div>
        )}
      </GlassPanel>
    </div>
  );
}

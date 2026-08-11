import { useCallback, useEffect, useState } from "react";
import { fetchCriticalNotificationAudit, type CriticalNotificationAuditRow } from "../data/api";
import "./CriticalAlertStrip.css";

interface CriticalAlertStripProps {
  onOpenAlerts: () => void;
}

type AlertSeverity = "info" | "warning" | "alert";

function normalizeSeverity(value?: string): AlertSeverity {
  const normalized = (value ?? "").toLowerCase();
  if (normalized === "alert") return "alert";
  if (normalized === "warning" || normalized === "warn") return "warning";
  return "info";
}

function visibleRows(rows: CriticalNotificationAuditRow[]): CriticalNotificationAuditRow[] {
  return rows.filter((row) => {
    if (row.display_state === "EXPIRED_HISTORICAL") return false;
    const dispatchStatus = String(row.event?.payload?.status ?? "").toUpperCase();
    if (dispatchStatus === "DUPLICATE_SUPPRESSED") return false;
    const severity = normalizeSeverity(row.event?.severity);
    return severity === "alert" || severity === "warning";
  });
}

export function CriticalAlertStrip({ onOpenAlerts }: CriticalAlertStripProps) {
  const [rows, setRows] = useState<CriticalNotificationAuditRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const report = await fetchCriticalNotificationAudit(5);
    if (!report) {
      setError("Critical alert audit unavailable.");
      setRows([]);
      return;
    }
    setRows(visibleRows(report.rows ?? []));
    setError(null);
  }, []);

  useEffect(() => {
    void load();
    const id = window.setInterval(load, 60_000);
    return () => window.clearInterval(id);
  }, [load]);

  const latest = rows[0] ?? null;
  if (!latest && !error) return null;

  const event = latest?.event;
  const severity = normalizeSeverity(event?.severity ?? (error ? "warning" : "info"));
  const title = event?.title ?? "Critical alert status";
  const body = error ?? event?.body ?? "No detail recorded.";
  const eventKind = event?.event_kind ?? latest?.source ?? "AUDIT";

  return (
    <section
      className={`critical-alert-strip critical-alert-strip-${severity}`}
      aria-live="polite"
      aria-label="Recent trading alert"
    >
      <div className="critical-alert-icon" aria-hidden="true">!</div>
      <div className="critical-alert-content">
        <div className="critical-alert-headline">
          <span className="critical-alert-label">{severity}</span>
          <span className="critical-alert-title">{title}</span>
          <span className="critical-alert-kind mono">{eventKind}</span>
        </div>
        <div className="critical-alert-body">{body}</div>
      </div>
      <button className="critical-alert-button" type="button" onClick={onOpenAlerts}>
        Open alerts
      </button>
    </section>
  );
}

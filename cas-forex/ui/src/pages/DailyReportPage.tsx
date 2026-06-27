/* ── CAS Forex — Daily Report Page ── */

import { useCallback, useEffect, useState } from "react";
import { GlassPanel } from "../components/GlassPanel";
import { fetchDailyReport } from "../data/api";
import type { DailyReport, DailySection } from "../data/api";

function todayUtcIso(): string {
  return new Date().toISOString().slice(0, 10);
}

interface SectionCardProps {
  section: DailySection;
}

/** Render a metric value readably — nested objects (e.g. by_status: {ACCEPTED: 3})
 * would otherwise stringify to "[object Object]". */
function formatMetricValue(v: unknown): string {
  if (v == null) return "—";
  if (Array.isArray(v)) {
    return v.length ? v.map((x) => formatMetricValue(x)).join(", ") : "—";
  }
  if (typeof v === "object") {
    const entries = Object.entries(v as Record<string, unknown>);
    if (entries.length === 0) return "—";
    return entries.map(([k, val]) => `${k}: ${formatMetricValue(val)}`).join(", ");
  }
  return String(v);
}

function SectionCard({ section }: SectionCardProps) {
  const [open, setOpen] = useState(true);

  return (
    <div className="daily-section">
      <button
        className="daily-section-header"
        onClick={() => setOpen((v) => !v)}
        type="button"
      >
        <span className="daily-section-title">{section.name}</span>
        <span className="daily-section-headline">{section.headline}</span>
        <span className="daily-section-caret">{open ? "▾" : "▸"}</span>
      </button>
      {open && (
        <div className="daily-section-body">
          {section.detail && <p>{section.detail}</p>}
          {section.metrics && Object.keys(section.metrics).length > 0 && (
            <table className="daily-section-metrics">
              <tbody>
                {Object.entries(section.metrics).map(([k, v]) => (
                  <tr key={k}>
                    <td className="mono">{k}</td>
                    <td className="mono">{formatMetricValue(v)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {section.notable_events && section.notable_events.length > 0 && (
            <ul className="daily-section-events">
              {section.notable_events.map((evt, i) => (
                <li key={i}>{evt}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

export function DailyReportPage() {
  const [date, setDate] = useState<string>(todayUtcIso());
  const [report, setReport] = useState<DailyReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (d: string) => {
    setLoading(true);
    setError(null);
    const isToday = d === todayUtcIso();
    const data = await fetchDailyReport(isToday ? "today" : d);
    if (data) {
      setReport(data);
    } else {
      setReport(null);
      setError("Daily report endpoint unreachable or no report for that date.");
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    load(date);
  }, [date, load]);

  const sections: DailySection[] = report?.sections ?? [];

  return (
    <div className="daily-report-page">
      <GlassPanel
        title="Daily Report"
        subtitle="What happened — observational, not forward-looking"
      >
        <div className="stack-status-row">
          <label className="limit-selector">
            <span className="field-label">Date (UTC)</span>
            <input
              type="date"
              value={date}
              max={todayUtcIso()}
              onChange={(e) => setDate(e.target.value)}
            />
          </label>
          <div className="lead-field">
            <span className="field-label">Loaded</span>
            <span className="field-value mono">
              {loading ? "Loading…" : report?.report_date ?? "—"}
            </span>
          </div>
        </div>
        {error && <div className="api-status-strip">{error}</div>}
        {report?.overall_headline && (
          <h2 className="report-overall-headline">{report.overall_headline}</h2>
        )}
        {report?.plain_english_summary && (
          <p className="plain-english-block">{report.plain_english_summary}</p>
        )}
      </GlassPanel>

      {sections.map((s) => (
        <SectionCard key={s.name} section={s} />
      ))}

      {report?.diagnostic_hints && report.diagnostic_hints.length > 0 && (
        <GlassPanel title="Diagnostic hints" subtitle="Verbatim from backend">
          <ul className="report-diagnostic-hints">
            {report.diagnostic_hints.map((h, i) => (
              <li key={i}>{h}</li>
            ))}
          </ul>
        </GlassPanel>
      )}
    </div>
  );
}

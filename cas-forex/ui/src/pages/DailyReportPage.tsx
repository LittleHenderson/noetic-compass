/* ── CAS Forex — Daily Report Page ── */

import { useCallback, useEffect, useState } from "react";
import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import { fetchDailyReport } from "../data/api";
import type { DailyReport, DailySection } from "../data/api";
import {
  formatMovementSourceStatus,
  movementSourceStatusTone,
} from "../util/movementSource";
import "./DailyReportPage.css";

function todayUtcIso(): string {
  return new Date().toISOString().slice(0, 10);
}

interface SectionCardProps {
  section: DailySection;
}

type ChipVariant = "success" | "warning" | "danger" | "info" | "muted" | "paper";

interface DailyRiskTruthSummary {
  hasTruth: boolean;
  latestPositionFeedLabel: string;
  latestPositionFeedDetail: string;
  sourceTruthObservation: string;
  priceSourceStatusesObserved: Array<[string, number]>;
  positionFeedLabelsObserved: Array<[string, number]>;
  mt5SourceSamples: number;
  movementSourceSamples: number;
  staticSimulationSamples: number;
  mixedFallbackSamples: number;
  providerActiveSamples: number;
  warmingSourceSamples: number;
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
        <span className="daily-section-title">{section.section_name}</span>
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

function buildDailyRiskTruthSummary(report: DailyReport | null): DailyRiskTruthSummary {
  const risk = report?.sections?.find((section) => section.section_name === "risk");
  const sourceTruth = risk?.source_truth && typeof risk.source_truth === "object"
    ? risk.source_truth
    : null;
  const metrics = risk?.metrics && typeof risk.metrics === "object"
    ? (risk.metrics as Record<string, unknown>)
    : {};
  const priceSourceStatusesObserved = normalizeCountEntries(
    sourceTruth?.price_source_statuses_observed ?? metrics["price_source_statuses_observed"],
  );
  const positionFeedLabelsObserved = normalizeCountEntries(
    sourceTruth?.position_feed_labels_observed ?? metrics["position_feed_labels_observed"],
  );
  const latestPositionFeedLabel =
    stringValue(sourceTruth?.latest_position_feed_label)
    || stringValue(metrics["latest_position_feed_label"])
    || positionFeedLabelsObserved[0]?.[0]
    || "UNKNOWN";
  const latestPositionFeedDetail = stringValue(
    sourceTruth?.latest_position_feed_detail ?? metrics["latest_position_feed_detail"],
  );
  const sourceTruthObservation = stringValue(
    sourceTruth?.source_truth_observation ?? metrics["source_truth_observation"],
  );
  const mt5SourceSamples = numberValue(sourceTruth?.mt5_source_samples ?? metrics["mt5_source_samples"]);
  const movementSourceSamples = numberValue(sourceTruth?.movement_source_samples ?? metrics["movement_source_samples"]);
  const staticSimulationSamples = numberValue(sourceTruth?.static_simulation_samples ?? metrics["static_simulation_samples"]);
  const mixedFallbackSamples = numberValue(sourceTruth?.mixed_fallback_samples ?? metrics["mixed_fallback_samples"]);
  const providerActiveSamples = numberValue(sourceTruth?.provider_active_samples ?? metrics["provider_active_samples"]);
  const warmingSourceSamples = numberValue(sourceTruth?.warming_source_samples ?? metrics["warming_source_samples"]);

  return {
    hasTruth: Boolean(
      latestPositionFeedDetail
      || sourceTruthObservation
      || priceSourceStatusesObserved.length
      || positionFeedLabelsObserved.length
      || mt5SourceSamples
      || movementSourceSamples,
    ),
    latestPositionFeedLabel,
    latestPositionFeedDetail,
    sourceTruthObservation,
    priceSourceStatusesObserved,
    positionFeedLabelsObserved,
    mt5SourceSamples,
    movementSourceSamples,
    staticSimulationSamples,
    mixedFallbackSamples,
    providerActiveSamples,
    warmingSourceSamples,
  };
}

function DailyRiskTruthPanel({ report }: { report: DailyReport | null }) {
  const truth = buildDailyRiskTruthSummary(report);
  if (!truth.hasTruth) return null;

  const detail = truth.latestPositionFeedDetail || truth.sourceTruthObservation || "Risk source truth detail unavailable.";
  const note =
    truth.sourceTruthObservation && truth.sourceTruthObservation !== detail
      ? truth.sourceTruthObservation
      : "";
  const dominantWarning =
    truth.staticSimulationSamples > 0
    || truth.mixedFallbackSamples > 0
    || truth.warmingSourceSamples > 0;

  return (
    <GlassPanel
      title="Daily Movement Source Truth"
      subtitle="What today’s risk and floating-value telemetry was priced from"
      variant={dominantWarning ? "warning" : "info"}
    >
      <div className="daily-truth-status-row">
        <StatusChip
          label={truth.latestPositionFeedLabel}
          variant={positionFeedVariant(truth.latestPositionFeedLabel)}
          size="sm"
        />
        {truth.priceSourceStatusesObserved.map(([status, count]) => (
          <StatusChip
            key={status}
            label={`${formatMovementSourceStatus(status, status)} x${count}`}
            variant={movementSourceStatusTone(
              status,
              status === "STATIC_SIMULATION_FALLBACK" || status === "MIXED_PROVIDER_AND_STATIC_FALLBACK",
            )}
            size="sm"
          />
        ))}
      </div>

      <div className="daily-truth-grid">
        <TruthField label="Latest Position Feed" value={truth.latestPositionFeedLabel} />
        <TruthField label="MT5 Samples" value={String(truth.mt5SourceSamples)} warning={truth.mt5SourceSamples === 0 && truth.movementSourceSamples > 0} />
        <TruthField label="Movement Samples" value={String(truth.movementSourceSamples)} warning={truth.movementSourceSamples > 0 && truth.mt5SourceSamples === 0} />
        <TruthField label="Static Fallback" value={String(truth.staticSimulationSamples)} warning={truth.staticSimulationSamples > 0} />
        <TruthField label="Mixed Fallback" value={String(truth.mixedFallbackSamples)} warning={truth.mixedFallbackSamples > 0} />
        <TruthField label="Provider Active" value={String(truth.providerActiveSamples)} />
        <TruthField label="Warming" value={String(truth.warmingSourceSamples)} warning={truth.warmingSourceSamples > 0} />
        <TruthField
          label="Observed Feed Labels"
          value={truth.positionFeedLabelsObserved.length ? truth.positionFeedLabelsObserved.map(([label, count]) => `${label} x${count}`).join(", ") : "NONE"}
        />
      </div>

      <div className="daily-truth-detail">{detail}</div>
      {note && <div className="daily-truth-note">{note}</div>}
    </GlassPanel>
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

      <DailyRiskTruthPanel report={report} />

      {sections.map((s) => (
        <SectionCard key={s.section_name} section={s} />
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

function TruthField({
  label,
  value,
  warning = false,
}: {
  label: string;
  value: string;
  warning?: boolean;
}) {
  return (
    <div className="daily-truth-field">
      <span className="daily-truth-field-label">{label}</span>
      <span className="daily-truth-field-value mono" style={{ color: warning ? "var(--warning)" : undefined }}>
        {value}
      </span>
    </div>
  );
}

function normalizeCountEntries(value: unknown): Array<[string, number]> {
  if (!value || typeof value !== "object") return [];
  return Object.entries(value as Record<string, unknown>)
    .map(([key, count]) => [key, numberValue(count)] as [string, number])
    .filter(([key, count]) => key.trim().length > 0 && count > 0);
}

function numberValue(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function positionFeedVariant(label: string): ChipVariant {
  const upper = label.toUpperCase();
  if (upper === "LIVE MT5") return "success";
  if (upper === "SIM PROOF") return "warning";
  if (upper === "WARMING" || upper === "UNKNOWN" || upper === "NONE" || !upper) return "muted";
  return "info";
}

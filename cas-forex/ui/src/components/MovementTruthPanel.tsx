import { GlassPanel } from "./GlassPanel";
import { StatusChip } from "./StatusChip";
import type { AccountHealthReport } from "../types/evidence";
import {
  formatMovementSourceStatus,
  movementSourceStatusTone,
} from "../util/movementSource";

type ChipVariant = "success" | "warning" | "danger" | "info" | "muted" | "paper";

interface MovementTruthPanelProps {
  report: AccountHealthReport | null | undefined;
  title?: string;
  subtitle?: string;
}

export function MovementTruthPanel({
  report,
  title = "Movement Source Truth",
  subtitle = "Whether prices are broker truth, provider-priced paper rows, or static simulator fallback",
}: MovementTruthPanelProps) {
  if (!report) {
    return (
      <GlassPanel title={title} subtitle={subtitle}>
        <div className="control-field-desc">Movement source truth is syncing.</div>
      </GlassPanel>
    );
  }

  const sourceHealth = report.source_health ?? {};
  const priceStatus = formatMovementSourceStatus(sourceHealth.price_source_status, "SOURCE WARMING");
  const positionFeedLabel = stringValue(sourceHealth.position_feed_label, "NONE");
  const detail = stringValue(
    sourceHealth.position_feed_detail,
    stringValue(
      sourceHealth.detail,
      stringValue(sourceHealth.price_source_summary, "Movement source truth is warming."),
    ),
  );
  const warning = stringValue(sourceHealth.price_source_warning, "");
  const brokerTicketCount = numberValue(sourceHealth.broker_ticket_position_count);
  const providerPaperCount = numberValue(sourceHealth.provider_priced_simulator_position_count);
  const staticPaperCount = numberValue(sourceHealth.static_simulator_position_count);
  const staleCount = numberValue(sourceHealth.stale_price_position_count);
  const hasAttention = Boolean(sourceHealth.attention_required) || staleCount > 0 || staticPaperCount > 0;

  return (
    <GlassPanel title={title} subtitle={subtitle} variant={hasAttention ? "warning" : "info"}>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <StatusChip label={positionFeedLabel} variant={positionFeedVariant(positionFeedLabel)} size="sm" />
        <StatusChip
          label={priceStatus}
          variant={movementSourceStatusTone(sourceHealth.price_source_status, hasAttention)}
          size="sm"
        />
        <StatusChip
          label={`${brokerTicketCount} BROKER TICKETS`}
          variant={brokerTicketCount > 0 ? "success" : "muted"}
          size="sm"
        />
        <StatusChip
          label={`${providerPaperCount} PROVIDER-BACKED PAPER`}
          variant={providerPaperCount > 0 ? "info" : "muted"}
          size="sm"
        />
        <StatusChip
          label={`${staticPaperCount} STATIC PAPER`}
          variant={staticPaperCount > 0 ? "warning" : "success"}
          size="sm"
        />
      </div>

      <div className="control-grid">
        <TruthField label="Position Feed" value={positionFeedLabel} mono />
        <TruthField label="Price Source" value={priceStatus} mono warning={hasAttention} />
        <TruthField label="Broker Tickets" value={String(brokerTicketCount)} mono />
        <TruthField label="Provider-backed Paper" value={String(providerPaperCount)} mono />
        <TruthField label="Static Paper Rows" value={String(staticPaperCount)} mono warning={staticPaperCount > 0} />
        <TruthField label="Stale Rows" value={String(staleCount)} mono warning={staleCount > 0} />
      </div>

      <div
        className="control-field-desc"
        style={{ marginTop: 10, color: hasAttention ? "var(--warning)" : "var(--text-secondary)" }}
      >
        {detail}
      </div>

      {warning && warning !== detail && (
        <div className="control-field-desc" style={{ marginTop: 8, color: "var(--warning)" }}>
          {warning}
        </div>
      )}

      <div className="control-field-desc" style={{ marginTop: 10 }}>
        This panel marks whether current-price and floating-value telemetry is coming from live MT5 broker positions,
        provider-priced paper/demo rows, or static simulator fallback.
      </div>
    </GlassPanel>
  );
}

function TruthField({
  label,
  value,
  mono,
  warning,
}: {
  label: string;
  value: string;
  mono?: boolean;
  warning?: boolean;
}) {
  return (
    <div className="control-field">
      <div className="field-label">{label}</div>
      <div
        className={`field-value ${mono ? "mono" : ""}`}
        style={{ marginTop: 4, color: warning ? "var(--warning)" : undefined }}
      >
        {value}
      </div>
    </div>
  );
}

function numberValue(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function stringValue(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function positionFeedVariant(label: string): ChipVariant {
  const upper = label.toUpperCase();
  if (upper === "LIVE MT5") return "success";
  if (upper === "SIM PROOF") return "warning";
  if (upper === "WARMING" || upper === "NONE" || upper === "UNKNOWN") return "muted";
  return "info";
}

import { StatusChip } from "./StatusChip";
import type { MovementSourceTruthSnapshot } from "../data/api";
import {
  formatMovementSourceStatus,
  movementSourceStatusTone,
} from "../util/movementSource";
import "./DecisionCardPrimitives.css";

type ChipVariant = "success" | "warning" | "danger" | "info" | "muted" | "paper";

interface DecisionMovementTruthProps {
  truth: MovementSourceTruthSnapshot | null | undefined;
  title?: string;
}

export function DecisionMovementTruth({
  truth,
  title = "Decision Pricing Truth",
}: DecisionMovementTruthProps) {
  if (!truth) return null;

  const priceStatus = formatMovementSourceStatus(truth.price_source_status ?? undefined, "SOURCE WARMING");
  const positionFeedLabel = stringValue(truth.position_feed_label, "NONE");
  const detail = stringValue(
    truth.position_feed_detail,
    stringValue(
      truth.detail,
      stringValue(truth.price_source_summary, "Movement source truth is warming."),
    ),
  );
  const warning = stringValue(truth.price_source_warning, "");
  const brokerTickets = numberValue(truth.broker_ticket_position_count);
  const providerPaper = numberValue(truth.provider_priced_simulator_position_count);
  const staticPaper = numberValue(truth.static_simulator_position_count);
  const staleRows = numberValue(truth.stale_price_position_count);
  const hasAttention =
    Boolean(truth.attention_required) ||
    Boolean(truth.static_simulation_active) ||
    staticPaper > 0 ||
    staleRows > 0;

  return (
    <div className="decision-movement-truth">
      <div className="decision-movement-head">
        <div className="decision-movement-title">{title}</div>
        <div className="decision-movement-chips">
          <StatusChip label={positionFeedLabel} variant={positionFeedVariant(positionFeedLabel)} size="sm" />
          <StatusChip
            label={priceStatus}
            variant={movementSourceStatusTone(truth.price_source_status ?? undefined, hasAttention)}
            size="sm"
          />
          <StatusChip
            label={`${brokerTickets} BROKER TICKETS`}
            variant={brokerTickets > 0 ? "success" : "muted"}
            size="sm"
          />
          <StatusChip
            label={`${providerPaper} PROVIDER PAPER`}
            variant={providerPaper > 0 ? "info" : "muted"}
            size="sm"
          />
          <StatusChip
            label={`${staticPaper} STATIC PAPER`}
            variant={staticPaper > 0 ? "warning" : "success"}
            size="sm"
          />
        </div>
      </div>

      <div className="decision-movement-grid">
        <TruthField label="Position Feed" value={positionFeedLabel} mono />
        <TruthField label="Price Source" value={priceStatus} mono warning={hasAttention} />
        <TruthField label="Open Rows" value={String(numberValue(truth.open_position_count))} mono />
        <TruthField label="Stale Rows" value={String(staleRows)} mono warning={staleRows > 0} />
      </div>

      <div
        className="decision-movement-detail"
        style={{ color: hasAttention ? "var(--warning)" : undefined }}
      >
        {detail}
      </div>

      {warning && warning !== detail && (
        <div className="decision-movement-warning">{warning}</div>
      )}
    </div>
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
    <div className="decision-movement-field">
      <div className="decision-movement-label">{label}</div>
      <div
        className={`decision-movement-value ${mono ? "mono" : ""}`}
        style={{ color: warning ? "var(--warning)" : undefined }}
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

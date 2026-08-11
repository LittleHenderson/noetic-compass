import { GlassPanel } from "./GlassPanel";
import { StatusChip } from "./StatusChip";
import {
  formatMovementSourceStatus,
  movementSourceStatusTone,
} from "../util/movementSource";
import type { AccountHealthReport } from "../types/evidence";

type ChipVariant = "success" | "warning" | "danger" | "info" | "muted" | "paper";

interface AccountHealthPanelProps {
  report: AccountHealthReport | null | undefined;
  title?: string;
  subtitle?: string;
  authorityLabel?: string;
}

export function AccountHealthPanel({
  report,
  title = "Account Health",
  subtitle = "Decision-grade exposure, protection, performance, and source health",
  authorityLabel,
}: AccountHealthPanelProps) {
  if (!report) {
    return (
      <GlassPanel title={title} subtitle={subtitle}>
        <div className="control-field-desc">Account health is syncing.</div>
      </GlassPanel>
    );
  }

  const account = report.account ?? {};
  const closed = report.closed_trade_performance ?? {};
  const openExposure = report.open_exposure ?? {};
  const sourceHealth = report.source_health ?? {};
  const blockers = uniqueNonEmpty([
    ...(report.blockers ?? []),
    sourceHealth.attention_required ? sourceHealth.detail : null,
    sourceHealth.price_source_warning,
  ]);
  const unprotectedPositions = asRecords(openExposure.unprotected_positions);
  const staticPositions = asRecords(sourceHealth.static_positions);
  const stalePositions = asRecords(sourceHealth.stale_positions);
  const staleOrStaticPositions = uniqueRows([...staticPositions, ...stalePositions]).slice(0, 8);
  const staleOrStaticCount = Math.max(
    numberValue(sourceHealth.stale_price_position_count),
    staleOrStaticPositions.length,
  );
  const statusVariant = accountHealthStatusTone(
    String(report.status || "UNKNOWN"),
    blockers.length > 0,
  );
  const protectionLabel =
    numberValue(openExposure.unprotected_position_count) > 0
      ? `UNPROTECTED ${numberValue(openExposure.unprotected_position_count)}`
      : "PROTECTED";
  const protectionVariant: ChipVariant =
    numberValue(openExposure.unprotected_position_count) > 0 ? "danger" : "success";
  const priceStatus = formatMovementSourceStatus(sourceHealth.price_source_status, "SYNC");
  const priceStatusVariant = movementSourceStatusTone(
    sourceHealth.price_source_status,
    staleOrStaticCount > 0,
  );

  return (
    <GlassPanel title={title} subtitle={subtitle} variant={blockers.length > 0 ? "warning" : "default"}>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        {authorityLabel ? (
          <StatusChip
            label={authorityLabel}
            variant={authorityLabel.toUpperCase().includes("SECONDARY") ? "warning" : "info"}
            size="sm"
          />
        ) : null}
        <StatusChip label={String(report.status || "UNKNOWN")} variant={statusVariant} size="sm" />
        <StatusChip label={priceStatus} variant={priceStatusVariant} size="sm" />
        <StatusChip label={protectionLabel} variant={protectionVariant} size="sm" />
        <StatusChip
          label={`${numberValue(sourceHealth.broker_ticket_position_count)} BROKER TICKETS`}
          variant={numberValue(sourceHealth.broker_ticket_position_count) > 0 ? "success" : "muted"}
          size="sm"
        />
        <StatusChip
          label={`${numberValue(sourceHealth.static_simulator_position_count)} STATIC`}
          variant={numberValue(sourceHealth.static_simulator_position_count) > 0 ? "warning" : "success"}
          size="sm"
        />
      </div>

      <div className="control-grid">
        <HealthField label="Balance" value={formatMoney(account.balance_usd)} mono />
        <HealthField label="Equity" value={formatMoney(account.equity_usd)} mono />
        <HealthField label="Free Margin" value={formatMoney(account.free_margin_usd)} mono />
        <HealthField label="Floating P/L" value={formatMoney(account.floating_pnl_usd, { signed: true })} mono />
        <HealthField
          label="Drawdown"
          value={`${formatMoney(account.drawdown_usd)} (${formatPercent(account.drawdown_pct, "0%")})`}
          mono
        />
        <HealthField label="Return on Initial" value={formatPercent(account.return_on_initial_pct, "UNKNOWN")} mono />
        <HealthField label="Closed Trades" value={String(numberValue(closed.closed_trade_count))} mono />
        <HealthField label="Win Rate" value={formatPercent(closed.win_rate_pct, "NO CLOSED")} mono />
        <HealthField label="Profit Factor" value={formatRatio(closed.profit_factor, closed.profit_factor_state)} mono />
        <HealthField label="Expectancy" value={formatMoney(closed.expectancy_usd, { signed: true })} mono />
        <HealthField label="Open Positions" value={String(numberValue(openExposure.open_position_count))} mono />
        <HealthField label="Open Lots" value={formatNumber(openExposure.open_lots, 2)} mono />
        <HealthField label="Open Risk Est." value={formatMoney(openExposure.open_risk_estimate_usd)} mono />
        <HealthField
          label="Protection Coverage"
          value={formatPercent(openExposure.protective_order_coverage_pct, "UNKNOWN")}
          mono
          danger={numberValue(openExposure.unprotected_position_count) > 0}
        />
        <HealthField
          label="Unprotected"
          value={String(numberValue(openExposure.unprotected_position_count))}
          mono
          danger={numberValue(openExposure.unprotected_position_count) > 0}
        />
        <HealthField
          label="Stale / Static Rows"
          value={String(staleOrStaticCount)}
          mono
          warning={staleOrStaticCount > 0}
        />
      </div>

      {sourceHealth.detail || sourceHealth.price_source_summary ? (
        <div
          className="control-field-desc"
          style={{ marginTop: 10, color: staleOrStaticCount > 0 ? "var(--warning)" : "var(--text-secondary)" }}
        >
          {sourceHealth.detail || sourceHealth.price_source_summary}
        </div>
      ) : null}

      {blockers.length > 0 ? (
        <div style={{ marginTop: 12 }}>
          <div className="field-label" style={{ marginBottom: 6 }}>Attention</div>
          <div className="summary-list">
            {blockers.map((blocker) => (
              <div key={blocker} className="summary-row" style={{ justifyContent: "flex-start", gap: 8, alignItems: "flex-start" }}>
                <span style={{ color: "var(--warning)", lineHeight: 1.2 }}>!</span>
                <span style={{ color: "var(--text-secondary)", fontSize: "0.8125rem", lineHeight: 1.4 }}>{blocker}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {unprotectedPositions.length > 0 ? (
        <HealthDetailTable
          title={`Unprotected Positions (${unprotectedPositions.length})`}
          rows={unprotectedPositions}
        />
      ) : null}

      {staleOrStaticPositions.length > 0 ? (
        <HealthDetailTable
          title={`Static / Stale Pricing Rows (${staleOrStaticPositions.length})`}
          rows={staleOrStaticPositions}
        />
      ) : null}

      <div className="control-field-desc" style={{ marginTop: 10 }}>
        {authorityLabel?.toUpperCase().includes("SECONDARY")
          ? "This is a separate simulator evidence ledger. It cannot replace, modify, or be added to the active MT5 account. The autonomous Operator continues to enter and manage trades through protected dispatch."
          : "This panel displays account-health evidence. The autonomous Operator's entry, management, take-profit, and exit actions run through protected dispatch, outside this display component."}
      </div>
    </GlassPanel>
  );
}

function HealthField({
  label,
  value,
  mono = false,
  warning = false,
  danger = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
  warning?: boolean;
  danger?: boolean;
}) {
  const color = danger ? "var(--danger)" : warning ? "var(--warning)" : undefined;
  return (
    <div className="control-field">
      <div className="field-label">{label}</div>
      <div className={`field-value ${mono ? "mono" : ""}`} style={{ marginTop: 4, color }}>
        {value}
      </div>
    </div>
  );
}

function HealthDetailTable({
  title,
  rows,
}: {
  title: string;
  rows: Array<Record<string, unknown>>;
}) {
  return (
    <div className="positions-table-wrap" style={{ marginTop: 12 }}>
      <div className="field-label" style={{ marginBottom: 6 }}>{title}</div>
      <table className="data-table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Side</th>
            <th>Lots</th>
            <th>Ticket</th>
            <th>Source</th>
            <th>Reason</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => {
            const symbol = stringValue(row.symbol, "UNKNOWN");
            const side = stringValue(row.side, "-");
            const lots = typeof row.lot_size === "number" ? row.lot_size.toFixed(2) : formatNumber(row.lot_size, 2);
            const ticket = stringValue(row.broker_ticket ?? row.simulator_ticket, "-");
            const source = stringValue(row.position_source_label ?? row.price_source, "-");
            const reason = humanizeReason(stringValue(row.stale_reason ?? row.reason, "-"));
            return (
              <tr key={`${title}-${symbol}-${ticket}-${index}`}>
                <td className="mono cell-symbol">{symbol}</td>
                <td>{side}</td>
                <td className="mono">{lots}</td>
                <td className="mono">{ticket}</td>
                <td className="mono" style={{ fontSize: "0.75rem" }}>{source}</td>
                <td style={{ color: "var(--text-secondary)", fontSize: "0.8125rem" }}>{reason}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function accountHealthStatusTone(status: string, hasBlockers: boolean): ChipVariant {
  if (hasBlockers || status === "ATTENTION") return "warning";
  if (status === "OBSERVING") return "success";
  return "muted";
}

function formatMoney(value: unknown, options: { signed?: boolean } = {}): string {
  const numeric = numberOrNull(value);
  if (numeric == null) return "UNKNOWN";
  const sign = options.signed && numeric > 0 ? "+" : "";
  return `${sign}$${numeric.toFixed(2)}`;
}

function formatPercent(value: unknown, fallback: string): string {
  const numeric = numberOrNull(value);
  return numeric == null ? fallback : `${numeric.toFixed(2)}%`;
}

function formatRatio(value: unknown, state: unknown): string {
  const numeric = numberOrNull(value);
  if (numeric != null) return numeric.toFixed(2);
  const status = stringValue(state, "");
  if (status === "NO_CLOSED_LOSSES") return "NO CLOSED LOSSES";
  if (status === "NO_CLOSED_PROFITS") return "NO CLOSED PROFITS";
  if (status === "NO_CLOSED_TRADES") return "NO CLOSED TRADES";
  return "UNKNOWN";
}

function formatNumber(value: unknown, digits: number): string {
  const numeric = numberOrNull(value);
  return numeric == null ? "UNKNOWN" : numeric.toFixed(digits);
}

function numberValue(value: unknown): number {
  return numberOrNull(value) ?? 0;
}

function numberOrNull(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function stringValue(value: unknown, fallback: string): string {
  const text = typeof value === "string" || typeof value === "number" ? String(value).trim() : "";
  return text || fallback;
}

function uniqueNonEmpty(values: Array<string | null | undefined>): string[] {
  const seen = new Set<string>();
  const unique: string[] = [];
  for (const value of values) {
    const text = String(value || "").trim();
    if (!text || seen.has(text)) continue;
    seen.add(text);
    unique.push(text);
  }
  return unique;
}

function asRecords(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? value.filter((row): row is Record<string, unknown> => Boolean(row) && typeof row === "object") : [];
}

function uniqueRows(rows: Array<Record<string, unknown>>): Array<Record<string, unknown>> {
  const seen = new Set<string>();
  const unique: Array<Record<string, unknown>> = [];
  for (const row of rows) {
    const key = [
      stringValue(row.row_id, ""),
      stringValue(row.symbol, ""),
      stringValue(row.broker_ticket ?? row.simulator_ticket, ""),
      stringValue(row.reason, ""),
    ].join("|");
    if (!key || seen.has(key)) continue;
    seen.add(key);
    unique.push(row);
  }
  return unique;
}

function humanizeReason(value: string): string {
  if (!value || value === "-") return value;
  return value.replace(/_/g, " ");
}

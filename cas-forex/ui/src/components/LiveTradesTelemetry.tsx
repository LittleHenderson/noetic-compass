/* CAS Forex - Live Trades Telemetry
 *
 * Real-time observational panel for the autonomous trading loop. Polls
 * /api/forex/live-telemetry every 2 seconds while mounted and renders
 * the currently open positions, per-symbol floating P&L, and a last-
 * updated timestamp.
 *
 * This panel is read-only telemetry - it does NOT propose trades, does
 * NOT recommend entries, and does NOT pick symbols. If the data source
 * reports no positions, we show the empty state plainly. If the
 * snapshot is stale, we surface a chip. No fabricated prices, ever.
 */

import { useEffect, useRef, useState } from "react";
import { GlassPanel } from "./GlassPanel";
import { StatusChip } from "./StatusChip";
import { SymbolTag } from "./SymbolTag";
import {
  fetchLiveTelemetry,
  type LiveTelemetryResponse,
  type LiveTelemetryPosition,
} from "../data/api";
import {
  describeMovementPositionFeed,
  formatMovementPositionAge,
  formatMovementPositionSourceLabel,
  isStaticMovementPosition,
  summarizeMovementSource,
} from "../util/movementSource";
import "./LiveTelemetryTable.css";

const POLL_INTERVAL_MS = 2000;
type LiveTelemetrySource = LiveTelemetryResponse["data_freshness"]["source"];

function normalizeTelemetrySource(value: string | null | undefined): LiveTelemetrySource {
  if (
    value === "mt5_demo_account_snapshot"
    || value === "mt5_live_account_snapshot"
    || value === "mt5_terminal_api_verifier"
    || value === "movement_stream"
    || value === "none"
  ) {
    return value;
  }
  return "none";
}

function formatTime(iso: string | null | undefined): string {
  if (!iso) return "-";
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return iso;
  return parsed.toLocaleTimeString([], { hour12: false });
}

function formatOpenedAt(iso: string | null): string {
  if (!iso) return "-";
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return iso;
  return parsed.toLocaleTimeString([], { hour12: false });
}

function pnlColor(value: number): string {
  if (value > 0) return "var(--accent-teal)";
  if (value < 0) return "var(--danger)";
  return "var(--text-muted)";
}

function formatPnl(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}`;
}

function sourceLabel(
  source: LiveTelemetrySource,
  movementSourceStatus: string | null | undefined,
): string {
  switch (source) {
    case "mt5_demo_account_snapshot":
      return "MT5 demo account";
    case "mt5_live_account_snapshot":
      return "MT5 live account";
    case "mt5_terminal_api_verifier":
      return "MT5 terminal";
    case "movement_stream":
      if (movementSourceStatus === "STATIC_SIMULATION_FALLBACK") return "Static simulation";
      if (movementSourceStatus === "MIXED_PROVIDER_AND_STATIC_FALLBACK") return "Mixed paper/static";
      return "Provider-backed paper";
    case "none":
    default:
      return "No live source";
  }
}

function telemetrySubtitle(
  source: LiveTelemetrySource,
  movementSourceStatus: string | null | undefined,
  noSourceSnapshot: boolean,
): string {
  if (noSourceSnapshot) {
    return "Observational only - waiting for MT5 broker positions or paper/demo movement proof rows";
  }
  if (source === "mt5_demo_account_snapshot") {
    return "Current MT5 demo broker positions and floating P&L, polled every 2s; the Operator trades through protected dispatch";
  }
  if (source === "mt5_live_account_snapshot") {
    return "Current MT5 live broker positions and floating P&L, polled every 2s; the Operator trades through protected dispatch";
  }
  if (source === "mt5_terminal_api_verifier") {
    return "Legacy MT5 verifier evidence, polled every 2s";
  }
  if (movementSourceStatus === "STATIC_SIMULATION_FALLBACK") {
    return "Observational only - paper/demo simulator proof rows; static rows can stay at entry until provider/MT5 quotes are usable";
  }
  if (movementSourceStatus === "MIXED_PROVIDER_AND_STATIC_FALLBACK") {
    return "Observational only - paper/demo simulator proof rows with mixed repricing; some rows can still stay at entry";
  }
  return "Observational only - paper/demo simulator proof rows repriced by provider/MT5 fallback where available";
}

function openCountLabel(
  noSourceSnapshot: boolean,
  positionFeed: ReturnType<typeof describeMovementPositionFeed>,
): string {
  if (noSourceSnapshot) return "Reported rows";
  return positionFeed.countLabel;
}

function emptyStateText(
  noSourceSnapshot: boolean,
  positionFeed: ReturnType<typeof describeMovementPositionFeed>,
): string {
  if (noSourceSnapshot) {
    return "No broker or paper/demo movement rows are currently reported.";
  }
  if (positionFeed.isLiveBroker) {
    return "No MT5 broker positions are currently reported.";
  }
  return "No paper/demo simulator proof rows are currently reported.";
}

export function LiveTradesTelemetry() {
  const [snapshot, setSnapshot] = useState<LiveTelemetryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    let cancelled = false;

    const tick = async () => {
      const result = await fetchLiveTelemetry();
      if (cancelled || !mounted.current) return;
      if (result) {
        setSnapshot(result);
        setError(null);
      } else {
        setError("Live telemetry refresh failed. This panel cannot confirm fresh open positions right now, and it does not place trades.");
      }
    };

    void tick();
    const handle = window.setInterval(() => {
      void tick();
    }, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      mounted.current = false;
      window.clearInterval(handle);
    };
  }, []);

  const positions: LiveTelemetryPosition[] = snapshot?.open_positions ?? [];
  const totalCount = snapshot?.totals.open_position_count ?? 0;
  const totalPnl = snapshot?.totals.total_floating_pnl ?? 0;
  const grossFloatingPnl = snapshot?.totals.gross_floating_pnl ?? totalPnl;
  const totalSwap = snapshot?.totals.total_swap ?? 0;
  const movementTruth = snapshot?.movement_source_truth ?? snapshot?.data_freshness.movement_source ?? null;
  const source = normalizeTelemetrySource(
    movementTruth?.telemetry_source ?? snapshot?.telemetry_source ?? snapshot?.data_freshness.source ?? "none",
  );
  const stale = movementTruth?.telemetry_stale ?? snapshot?.telemetry_stale ?? snapshot?.data_freshness.stale ?? true;
  const lastUpdateIso = movementTruth?.telemetry_last_update_iso ?? snapshot?.telemetry_last_update_iso ?? snapshot?.data_freshness.last_update_iso ?? null;
  const priceSourceStatus = movementTruth?.price_source_status ?? snapshot?.price_source_status ?? snapshot?.data_freshness.movement_source?.price_source_status;
  const movementSource = summarizeMovementSource(movementTruth);
  const derivedPositionFeed = describeMovementPositionFeed(
    movementTruth,
    source === "mt5_demo_account_snapshot"
      ? "mt5_demo"
      : source === "mt5_live_account_snapshot" || source === "mt5_terminal_api_verifier"
        ? "mt5_live"
        : null,
  );
  const noSourceSnapshot = source === "none";
  const positionFeed = {
    ...derivedPositionFeed,
    label: movementTruth?.position_feed_label ?? snapshot?.position_feed_label ?? derivedPositionFeed.label,
    detail: movementTruth?.position_feed_detail ?? movementTruth?.detail ?? snapshot?.position_feed_detail ?? derivedPositionFeed.detail,
    isLiveBroker:
      ["LIVE MT5", "MT5 LIVE", "MT5 DEMO"].includes(String(movementTruth?.position_feed_label || "").toUpperCase())
      || ["LIVE MT5", "MT5 LIVE", "MT5 DEMO"].includes(String(snapshot?.position_feed_label || "").toUpperCase())
        ? true
        : movementTruth?.position_feed_label === "SIM PROOF"
          || movementTruth?.position_feed_label === "NONE"
          || snapshot?.position_feed_label === "SIM PROOF"
          || snapshot?.position_feed_label === "NONE"
          ? false
          : derivedPositionFeed.isLiveBroker,
  };
  const brokerTicketCount = movementTruth?.broker_ticket_position_count
    ?? snapshot?.broker_ticket_position_count
    ?? positions.filter((row) => Boolean(row.broker_ticket)).length;
  const staticPositionCount = movementTruth?.static_position_count
    ?? movementTruth?.static_simulator_position_count
    ?? snapshot?.static_position_count
    ?? positions.filter((row) => isStaticMovementPosition(row)).length;

  return (
    <GlassPanel
      title="Live Trades Telemetry"
      subtitle={telemetrySubtitle(source, priceSourceStatus, noSourceSnapshot)}
    >
      <div className="live-telemetry-header">
        <div className="live-telemetry-stat">
          <span className="field-label">{openCountLabel(noSourceSnapshot, positionFeed)}</span>
          <span className="field-value mono">{totalCount}</span>
        </div>
        <div className="live-telemetry-stat">
          <span className="field-label">Net Open P&amp;L</span>
          <span
            className="field-value mono"
            style={{ color: pnlColor(totalPnl) }}
          >
            ${formatPnl(totalPnl)}
          </span>
        </div>
        <div className="live-telemetry-stat">
          <span className="field-label">Source update</span>
          <span className="field-value mono">{formatTime(lastUpdateIso)}</span>
        </div>
        <div className="live-telemetry-stat">
          <span className="field-label">Response built</span>
          <span className="field-value mono">{formatTime(snapshot?.as_of_iso)}</span>
        </div>
        <div className="live-telemetry-stat">
          <span className="field-label">Source</span>
          <StatusChip
            label={sourceLabel(source, priceSourceStatus)}
            variant={source === "movement_stream" ? movementSource.statusTone : source === "none" ? "muted" : "info"}
            size="sm"
          />
        </div>
        <div className="live-telemetry-stat">
          <span className="field-label">Position feed</span>
          <StatusChip
            label={positionFeed.isLiveBroker ? (movementTruth?.position_feed_label || snapshot?.position_feed_label || "MT5") : noSourceSnapshot ? "NONE" : "SIM PROOF"}
            variant={positionFeed.isLiveBroker ? "success" : noSourceSnapshot ? "muted" : "warning"}
            size="sm"
          />
        </div>
        <div className="live-telemetry-stat">
          <span className="field-label">Price P&amp;L</span>
          <span className="field-value mono" style={{ color: pnlColor(grossFloatingPnl) }}>
            ${formatPnl(grossFloatingPnl)}
          </span>
        </div>
        <div className="live-telemetry-stat">
          <span className="field-label">Swap / Carry</span>
          <span className="field-value mono" style={{ color: pnlColor(totalSwap) }}>
            ${formatPnl(totalSwap)}
          </span>
        </div>
        <div className="live-telemetry-stat">
          <span className="field-label">Broker-ticket rows</span>
          <span className="field-value mono">{brokerTicketCount}</span>
        </div>
        <div className="live-telemetry-stat">
          <span className="field-label">Static rows</span>
          <span className="field-value mono" style={{ color: staticPositionCount > 0 ? "var(--warning)" : undefined }}>
            {staticPositionCount}
          </span>
        </div>
        {source === "movement_stream" && (
          <>
            <div className="live-telemetry-stat">
              <span className="field-label">Price state</span>
              <span className="field-value mono">{movementSource.statusLabel}</span>
            </div>
            <div className="live-telemetry-stat">
              <span className="field-label">Provider</span>
              <span className="field-value mono">{movementSource.providerLabel}</span>
            </div>
          </>
        )}
        {stale && (
          <div className="live-telemetry-stat">
            <StatusChip label="STALE" variant="warning" size="sm" />
          </div>
        )}
      </div>

      {positions.length === 0 ? (
        <div className="live-telemetry-empty">{emptyStateText(noSourceSnapshot, positionFeed)}</div>
      ) : (
        <div className="live-telemetry-table-wrap">
          <table className="live-telemetry-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Direction</th>
                <th>Source</th>
                <th className="num">Lots</th>
                <th className="num">Entry</th>
                <th className="num">Current</th>
                <th className="num">Price P&amp;L</th>
                <th className="num">Swap</th>
                <th className="num">Net Open P&amp;L</th>
                <th>Age</th>
                <th>Opened</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((row, i) => {
                const staticRow = isStaticMovementPosition(row);
                const sourceLabelText = formatMovementPositionSourceLabel(
                  row.position_source_label ?? undefined,
                  row.broker_ticket,
                  row.price_source ?? undefined,
                );
                return (
                  <tr key={`${row.symbol}-${row.broker_ticket ?? i}`}>
                    <td><SymbolTag symbol={row.symbol} size="sm" /></td>
                    <td>
                      <StatusChip
                        label={row.direction}
                        variant={row.direction === "BUY" ? "info" : "warning"}
                        size="sm"
                      />
                    </td>
                    <td
                      className={`mono live-telemetry-source ${staticRow ? "stale" : ""}`}
                      title={row.price_source ?? row.stale_reason ?? undefined}
                    >
                      {sourceLabelText}
                    </td>
                    <td className="num mono">{row.lots.toFixed(2)}</td>
                    <td className="num mono">{row.entry_price.toFixed(5)}</td>
                    <td className="num mono">{row.current_price.toFixed(5)}</td>
                    <td
                      className="num mono"
                      style={{ color: pnlColor(row.floating_pnl) }}
                    >
                      ${formatPnl(row.floating_pnl)}
                    </td>
                    <td className="num mono" style={{ color: pnlColor(row.swap ?? 0) }}>
                      ${formatPnl(row.swap ?? 0)}
                    </td>
                    <td className="num mono" style={{ color: pnlColor(row.net_open_pnl ?? row.floating_pnl) }}>
                      ${formatPnl(row.net_open_pnl ?? row.floating_pnl)}
                    </td>
                    <td className="mono" title={row.opened_at_iso ?? row.stale_reason ?? undefined}>{formatMovementPositionAge(row)}</td>
                    <td className="mono">{formatOpenedAt(row.opened_at_iso)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {noSourceSnapshot ? (
        <div className="live-telemetry-boundary">
          No broker or paper/demo movement snapshot is feeding this panel right now. It cannot confirm open positions until a source reports in.
        </div>
      ) : (
        <div className="live-telemetry-boundary">
          position feed: {positionFeed.label} | source: {sourceLabel(source, priceSourceStatus)} | last update: {formatTime(lastUpdateIso)}
          <br />
          {positionFeed.detail}
          {positionFeed.isLiveBroker && (
            <>
              <br />
              This table is a display mirror. Autonomous entries, scale-ins, take-profit changes, partial closes, and exits run through protected dispatch.
            </>
          )}
        </div>
      )}

      {source === "movement_stream" && movementSource.warningText && (
        <div className="live-telemetry-error" style={{ color: "var(--warning)" }}>
          {movementSource.warningText}
        </div>
      )}

      {error && <div className="live-telemetry-error">{error}</div>}
    </GlassPanel>
  );
}


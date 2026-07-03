/* ── CAS Forex — Live Trades Telemetry ──
 *
 * Real-time observational panel for the autonomous trading loop. Polls
 * /api/forex/live-telemetry every 2 seconds while mounted and renders
 * the currently open positions, per-symbol floating P&L, and a last-
 * updated timestamp.
 *
 * This panel is read-only telemetry — it does NOT propose trades, does
 * NOT recommend entries, and does NOT pick symbols. If the data source
 * reports no positions, we show "No active positions" plainly. If the
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
import "./LiveTelemetryTable.css";

const POLL_INTERVAL_MS = 2000;

function formatTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return iso;
  return parsed.toLocaleTimeString([], { hour12: false });
}

function formatOpenedAt(iso: string | null): string {
  if (!iso) return "—";
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

function sourceLabel(source: LiveTelemetryResponse["data_freshness"]["source"]): string {
  switch (source) {
    case "mt5_terminal_api_verifier":
      return "MT5 terminal";
    case "movement_stream":
      return "Paper / demo movement";
    case "none":
    default:
      return "No live source";
  }
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
        setError("Could not reach live telemetry endpoint");
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
  const stale = snapshot?.data_freshness.stale ?? true;
  const source = snapshot?.data_freshness.source ?? "none";

  return (
    <GlassPanel
      title="Live Trades Telemetry"
      subtitle="Observational only — open positions, floating P&L, polled every 2s"
    >
      <div className="live-telemetry-header">
        <div className="live-telemetry-stat">
          <span className="field-label">Open</span>
          <span className="field-value mono">{totalCount}</span>
        </div>
        <div className="live-telemetry-stat">
          <span className="field-label">Total Floating P&amp;L</span>
          <span
            className="field-value mono"
            style={{ color: pnlColor(totalPnl) }}
          >
            ${formatPnl(totalPnl)}
          </span>
        </div>
        <div className="live-telemetry-stat">
          <span className="field-label">As of</span>
          <span className="field-value mono">{formatTime(snapshot?.as_of_iso)}</span>
        </div>
        <div className="live-telemetry-stat">
          <span className="field-label">Source</span>
          <StatusChip
            label={sourceLabel(source)}
            variant={source === "none" ? "muted" : "info"}
            size="sm"
          />
        </div>
        {stale && (
          <div className="live-telemetry-stat">
            <StatusChip label="STALE" variant="warning" size="sm" />
          </div>
        )}
      </div>

      {positions.length === 0 ? (
        <div className="live-telemetry-empty">No active positions</div>
      ) : (
        <div className="live-telemetry-table-wrap">
          <table className="live-telemetry-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Direction</th>
                <th className="num">Lots</th>
                <th className="num">Entry</th>
                <th className="num">Current</th>
                <th className="num">Floating P&amp;L</th>
                <th>Opened</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((row, i) => (
                <tr key={`${row.symbol}-${row.broker_ticket ?? i}`}>
                  <td><SymbolTag symbol={row.symbol} size="sm" /></td>
                  <td>
                    <StatusChip
                      label={row.direction}
                      variant={row.direction === "BUY" ? "info" : "warning"}
                      size="sm"
                    />
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
                  <td className="mono">{formatOpenedAt(row.opened_at_iso)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {error && <div className="live-telemetry-error">{error}</div>}
    </GlassPanel>
  );
}

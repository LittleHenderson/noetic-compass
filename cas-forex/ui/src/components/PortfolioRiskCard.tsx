/* ── CAS Forex — Portfolio Risk Card ──
 *
 * Observational portfolio-shape panel. Polls
 * /api/forex/risk-monitoring/portfolio every 30s and renders
 * exposure / concentration / margin-utilization meters plus a
 * per-symbol exposure table and diagnostic hints.
 *
 * Strictly observational. The card NEVER recommends "close X" or
 * "scale into Y" — only the shape of what is open.
 */

import { useEffect, useRef, useState } from "react";
import { GlassPanel } from "./GlassPanel";
import { StatusChip } from "./StatusChip";
import { fetchPortfolioRisk, type PortfolioRiskResponse } from "../data/api";
import {
  formatMovementSourceStatus,
  movementSourceStatusTone,
} from "../util/movementSource";
import "./LiveTelemetryTable.css";
import "./PortfolioRiskCard.css";

const POLL_INTERVAL_MS = 30_000;

function pnlColor(value: number): string {
  if (value > 0) return "var(--accent-teal)";
  if (value < 0) return "var(--danger)";
  return "var(--text-muted)";
}

function formatPnl(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}`;
}

function meterVariant(pct: number): "teal" | "warning" | "danger" {
  if (pct > 70) return "danger";
  if (pct >= 50) return "warning";
  return "teal";
}

function MeterRow({
  label,
  pct,
  detail,
}: {
  label: string;
  pct: number;
  detail: string;
}) {
  const variant = meterVariant(pct);
  const clamped = Math.max(0, Math.min(100, pct));
  return (
    <div className="risk-meter-row">
      <div className="risk-meter-header">
        <span className="field-label">{label}</span>
        <span className="field-value mono">{detail}</span>
      </div>
      <div className="risk-meter">
        <div
          className={`risk-meter-fill risk-meter-${variant}`}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}

export function PortfolioRiskCard() {
  const [snapshot, setSnapshot] = useState<PortfolioRiskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    let cancelled = false;

    const tick = async () => {
      const result = await fetchPortfolioRisk();
      if (cancelled || !mounted.current) return;
      if (result) {
        setSnapshot(result);
        setError(null);
      } else {
        setError("Could not reach portfolio risk endpoint");
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

  const openCount = snapshot?.open_position_count ?? 0;
  const totalLots = snapshot?.total_exposure_lots ?? 0;
  const totalPnl = snapshot?.total_floating_pnl ?? 0;
  const concentrationPct = snapshot?.concentration_pct ?? 0;
  const largestSymbol = snapshot?.largest_symbol_exposure?.symbol ?? "—";
  const marginPct = snapshot?.margin_utilization_pct;
  const bySymbol = snapshot?.by_symbol ?? [];
  const hints = snapshot?.diagnostic_hints ?? [];
  const topSymbols = bySymbol.slice(0, 5);
  const movementTruth = snapshot?.movement_source_truth ?? null;
  const positionFeedLabel = movementTruth?.position_feed_label?.trim()
    || snapshot?.position_feed_label
    || "NONE";
  const priceSourceStatus = movementTruth?.price_source_status?.trim()
    || snapshot?.price_source_status
    || null;
  const positionFeedDetail = movementTruth?.position_feed_detail?.trim()
    || movementTruth?.detail?.trim()
    || snapshot?.position_feed_detail
    || "No broker or paper/demo movement snapshot is reporting positions right now.";
  const telemetrySource = movementTruth?.telemetry_source?.trim()
    || snapshot?.telemetry_source
    || "none";
  const telemetryStale = movementTruth?.telemetry_stale ?? snapshot?.telemetry_stale ?? true;
  const lastUpdate = movementTruth?.telemetry_last_update_iso?.trim()
    || snapshot?.telemetry_last_update_iso
    || "unknown";
  const brokerTicketCount = movementTruth?.broker_ticket_position_count
    ?? snapshot?.broker_ticket_position_count
    ?? 0;
  const staticPositionCount = movementTruth?.static_position_count
    ?? movementTruth?.static_simulator_position_count
    ?? snapshot?.static_position_count
    ?? 0;

  return (
    <GlassPanel
      title="Portfolio Risk"
      subtitle="Observational shape of open exposure — polled every 30s"
    >
      <div className="portfolio-risk-card">
        <div className="portfolio-risk-header">
          <div className="live-telemetry-stat">
            <span className="field-label">Open Positions</span>
            <span className="field-value mono">{openCount}</span>
          </div>
          <div className="live-telemetry-stat">
            <span className="field-label">Total Exposure</span>
            <span className="field-value mono">{totalLots.toFixed(2)} lots</span>
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
            <span className="field-label">Position Feed</span>
            <StatusChip
              label={positionFeedLabel}
              variant={positionFeedLabel === "LIVE MT5" ? "success" : positionFeedLabel === "SIM PROOF" ? "warning" : "muted"}
              size="sm"
            />
          </div>
          {priceSourceStatus && (
            <div className="live-telemetry-stat">
              <span className="field-label">Price Source</span>
              <StatusChip
                label={formatMovementSourceStatus(priceSourceStatus, "SOURCE")}
                variant={movementSourceStatusTone(priceSourceStatus)}
                size="sm"
              />
            </div>
          )}
          {telemetryStale && (
            <div className="live-telemetry-stat">
              <span className="field-label">Snapshot</span>
              <StatusChip label="STALE" variant="warning" size="sm" />
            </div>
          )}
        </div>

        <div className="live-telemetry-boundary">
          position feed: {positionFeedLabel} | telemetry source: {telemetrySource} | broker tickets: {brokerTicketCount} | static rows: {staticPositionCount} | last update: {lastUpdate}
        </div>

        <div className="live-telemetry-boundary">
          {positionFeedDetail}
        </div>

        <MeterRow
          label={`Concentration ${concentrationPct.toFixed(0)}% in ${largestSymbol}`}
          pct={concentrationPct}
          detail={`${concentrationPct.toFixed(1)}%`}
        />

        {marginPct == null ? (
          <div className="risk-meter-row">
            <div className="risk-meter-header">
              <span className="field-label">Margin Utilization</span>
              <span className="field-value mono">unavailable</span>
            </div>
            <div className="risk-meter">
              <div
                className="risk-meter-fill risk-meter-muted"
                style={{ width: "0%" }}
              />
            </div>
          </div>
        ) : (
          <MeterRow
            label="Margin Utilization"
            pct={marginPct}
            detail={`${marginPct.toFixed(1)}%`}
          />
        )}

        {topSymbols.length === 0 ? (
          <div className="live-telemetry-empty">No open exposure</div>
        ) : (
          <div className="live-telemetry-table-wrap">
            <table className="live-telemetry-table risk-symbol-table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Direction</th>
                  <th className="num">Positions</th>
                  <th className="num">Lots</th>
                  <th className="num">Floating P&amp;L</th>
                </tr>
              </thead>
              <tbody>
                {topSymbols.map((row) => (
                  <tr key={row.symbol}>
                    <td>{row.symbol}</td>
                    <td>{row.direction}</td>
                    <td className="num mono">{row.open_position_count}</td>
                    <td className="num mono">{row.total_lots.toFixed(2)}</td>
                    <td
                      className="num mono"
                      style={{ color: pnlColor(row.total_floating_pnl) }}
                    >
                      ${formatPnl(row.total_floating_pnl)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {hints.length > 0 && (
          <ul className="portfolio-risk-hints">
            {hints.map((hint, i) => (
              <li key={i}>{hint}</li>
            ))}
          </ul>
        )}

        {error && <div className="live-telemetry-error">{error}</div>}
      </div>
    </GlassPanel>
  );
}

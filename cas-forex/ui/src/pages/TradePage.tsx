/* ── CAS Forex — Paper Trading Desk ── */

import { useState } from "react";
import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import { CandlestickChart } from "../components/charts/CandlestickChart";
import { MultiTimeframeSelector } from "../components/MultiTimeframeSelector";
import { LiveTradesTelemetry } from "../components/LiveTradesTelemetry";
import type { DashboardState, SymbolDecision, SizingEntry } from "../types/evidence";

interface TradePageProps {
  state: DashboardState;
}

const SYMBOLS = ["EUR/USD", "GBP/USD", "AUD/USD", "USD/JPY", "USD/CAD", "NAS100", "US30", "XAU/USD"] as const;
const TIMEFRAMES = ["M5", "M15", "H1", "H4", "D1"] as const;
const STYLES = ["scalping", "day", "swing", "position"] as const;

type Symbol = (typeof SYMBOLS)[number];
type Timeframe = (typeof TIMEFRAMES)[number];
type Style = (typeof STYLES)[number];

// FastAPI path parameters don't accept encoded slashes (%2F) reliably; the
// MTF runtime stores symbols as plain strings, so normalize "EUR/USD" -> "EURUSD"
// for the runtime. Display symbols stay slash-formatted.
function normalizeSymbolForRuntime(displaySymbol: string): string {
  return displaySymbol.replace(/\//g, "");
}

export function TradePage({ state }: TradePageProps) {
  const { dailyBundle: b } = state;
  const movement = state.movementStream;
  const decision = b.latest_decision.latest_decision;

  const [symbol, setSymbol] = useState<Symbol>("NAS100");
  const [timeframe, setTimeframe] = useState<Timeframe>("D1");
  const [style, setStyle] = useState<Style>("swing");

  const activeDecision: SymbolDecision | undefined =
    decision.symbol_decisions.find((d) => d.symbol === symbol);

  const activeSizing: SizingEntry | undefined =
    b.latest_risk.latest_review.sizing.find((s) => s.symbol === symbol);
  const activeQuote = movement?.quotes.find((q) => q.symbol === symbol);
  const activePosition = movement?.positions.find((p) => p.symbol === symbol);
  const candlePreview = activeDecision
    ? buildProposalCandles(
        activeDecision.proposal.entry_price,
        activeDecision.proposal.stop_loss,
        activeDecision.proposal.take_profit,
      )
    : [];

  return (
    <div className="trade-page">
      {/* ── Selectors ── */}
      <GlassPanel title="Paper Trading Desk" subtitle="Research / paper-only — no broker orders placed">
        <div className="trade-selectors">
          <div className="selector-group">
            <span className="selector-label">Symbol</span>
            <div className="selector-chips">
              {SYMBOLS.map((s) => (
                <button key={s} className={`selector-chip ${symbol === s ? "active" : ""}`} onClick={() => setSymbol(s)}>{s}</button>
              ))}
            </div>
          </div>
          <div className="selector-group">
            <span className="selector-label">Timeframe</span>
            <div className="selector-chips">
              {TIMEFRAMES.map((t) => (
                <button key={t} className={`selector-chip ${timeframe === t ? "active" : ""}`} onClick={() => setTimeframe(t)}>{t}</button>
              ))}
            </div>
          </div>
          <div className="selector-group">
            <span className="selector-label">Style</span>
            <div className="selector-chips">
              {STYLES.map((st) => (
                <button key={st} className={`selector-chip ${style === st ? "active" : ""}`} onClick={() => setStyle(st)}>{st}</button>
              ))}
            </div>
          </div>
        </div>
      </GlassPanel>

      {/* ── Multi-timeframe runtime selector (MTF runtime / risk aggregation) ── */}
      <MultiTimeframeSelector symbol={normalizeSymbolForRuntime(symbol)} />

      {/* ── Live Trades Telemetry (observational, polled every 2s) ── */}
      <LiveTradesTelemetry />

      {/* ── Proposal Preview + Risk Sizing ── */}
      <div className="trade-grid-2col">
        <GlassPanel title="Proposal Preview" subtitle={activeDecision ? activeDecision.proposal.proposal_id : "No active signal for this symbol/timeframe"}>
          {activeDecision ? (
            <div className="proposal-preview">
              <div className="proposal-header">
                <span className="route-symbol">{activeDecision.symbol}</span>
                <StatusChip label={activeDecision.direction} variant="info" size="sm" />
                <StatusChip label={activeDecision.action} variant="paper" size="sm" />
                <span className="route-confidence mono">{(activeDecision.confidence * 100).toFixed(1)}% conf</span>
              </div>
              <div className="proposal-prices">
                <PriceBlock label="Entry" value={activeDecision.proposal.entry_price} />
                <PriceBlock label="Stop Loss" value={activeDecision.proposal.stop_loss} danger />
                <PriceBlock label="Take Profit" value={activeDecision.proposal.take_profit} success />
              </div>
              <div className="proposal-meta">
                <MetaRow label="Model" value={activeDecision.proposal.model_version} mono />
                <MetaRow label="Source" value={activeDecision.proposal.model_source} />
                <MetaRow label="Horizon" value={`${activeDecision.proposal.horizon_minutes}min`} />
                <MetaRow label="SL Mult" value={`${activeDecision.sl_mult}x`} mono />
                <MetaRow label="TP Mult" value={`${activeDecision.tp_mult}x`} mono />
                <MetaRow label="Close" value={activeDecision.latest_close.toFixed(2)} mono />
                <MetaRow label="Bars" value={`${activeDecision.bars_used}`} mono />
              </div>
              <div className="proposal-rationale">{activeDecision.proposal.rationale}</div>
            </div>
          ) : (
            <NoSignal symbol={symbol} timeframe={timeframe} />
          )}
        </GlassPanel>

        <GlassPanel title="Risk Sizing" subtitle="Paper budget allocation">
          {activeSizing ? (
            <div className="sizing-preview">
              <div className="sizing-preview-header">
                <StatusChip label={activeSizing.attempt_status} variant={activeSizing.attempt_status === "PAPER_ATTEMPT_ALLOWED" ? "info" : "warning"} size="sm" />
                <span className="mono muted-sm">Attempt #{activeSizing.attempt_number}</span>
              </div>
              <div className="sizing-preview-grid">
                <SizeField label="Sized Lots" value={activeSizing.sized_lots} mono />
                <SizeField label="Raw Lots" value={activeSizing.raw_lots.toFixed(6)} mono muted />
                <SizeField label="Stop Dist" value={`${activeSizing.stop_distance_units.toFixed(2)} ${activeSizing.unit_name}s`} />
                <SizeField label="Risk/Lot" value={`$${activeSizing.risk_per_lot_usd.toFixed(2)}`} mono />
                <SizeField label="Planned Risk" value={`$${activeSizing.planned_risk_usd.toFixed(2)} (${activeSizing.planned_risk_pct.toFixed(2)}%)`} />
                <SizeField label="Max Risk" value={`$${activeSizing.max_risk_usd.toFixed(2)}`} mono />
              </div>
              <div className="sizing-rationale">{activeSizing.reason}</div>
            </div>
          ) : (
            <NoSignal symbol={symbol} timeframe={timeframe} />
          )}
          <div className="risk-budget-summary">
            <div className="budget-row">
              <span className="field-label">Account Equity</span>
              <span className="field-value mono">${b.latest_risk.latest_review.account_equity.toLocaleString()}</span>
            </div>
            <div className="budget-row">
              <span className="field-label">Per-Trade Risk</span>
              <span className="field-value mono">{b.latest_risk.latest_review.max_risk_per_trade_pct}%</span>
            </div>
            <div className="budget-row">
              <span className="field-label">Daily Budget</span>
              <span className="field-value mono">${b.latest_risk.latest_review.daily_risk_budget_usd.toFixed(2)} ({b.latest_risk.latest_review.daily_risk_budget_pct}%)</span>
            </div>
            <div className="budget-row">
              <span className="field-label">Max Position</span>
              <span className="field-value mono">{b.latest_risk.latest_review.max_position_lots} lots</span>
            </div>
          </div>
        </GlassPanel>
      </div>

      {/* ── Forecast Harness ── */}
      <GlassPanel title="Proposal Price Scale" subtitle={activeDecision ? `${symbol} entry / stop / target context` : "No active paper signal"}>
        <CandlestickChart candles={candlePreview} symbol={symbol} height={180} />
      </GlassPanel>


      <GlassPanel title="Active Market Movement" subtitle={activeQuote ? `${symbol} paper/demo quote, SL/TP distance, floating P/L` : "Select a currently routed paper symbol to view movement"}>
        {activeQuote && activePosition ? (
          <div className="dashboard-grid-3col">
            <div className="metric-stack" style={{ padding: 0 }}>
              <MetaRow label="Bid / Ask" value={`${activeQuote.bid.toFixed(2)} / ${activeQuote.ask.toFixed(2)}`} mono />
              <MetaRow label="Spread" value={`${activeQuote.spread_units.toFixed(1)} ${activeQuote.price_unit_name}`} mono />
              <MetaRow label="Source" value={activeQuote.source} mono />
            </div>
            <div className="metric-stack" style={{ padding: 0 }}>
              <MetaRow label="Current" value={activePosition.current_price.toFixed(2)} mono />
              <MetaRow label="Floating P/L" value={`$${activePosition.floating_pnl_usd.toFixed(2)} (${activePosition.floating_pnl_units.toFixed(2)} ${activeQuote.price_unit_name}s)`} mono />
              <MetaRow label="Margin Est." value={`$${activePosition.margin_estimate_usd.toFixed(2)}`} mono />
            </div>
            <div className="metric-stack" style={{ padding: 0 }}>
              <MetaRow label="To SL" value={activePosition.distance_to_sl_units == null ? "—" : `${activePosition.distance_to_sl_units.toFixed(2)} ${activeQuote.price_unit_name}s`} mono />
              <MetaRow label="To TP" value={activePosition.distance_to_tp_units == null ? "—" : `${activePosition.distance_to_tp_units.toFixed(2)} ${activeQuote.price_unit_name}s`} mono />
              <MetaRow label="Mode" value={movement?.mode ?? "PAPER_DEMO_REALTIME_SCAFFOLD"} mono />
            </div>
          </div>
        ) : (
          <NoSignal symbol={symbol} timeframe={timeframe} />
        )}
        <div style={{ marginTop: 8, fontSize: "0.7rem", color: "var(--warning)" }}>
          {movement?.claim_boundary ?? "Paper/demo movement only. Live trading and payment movement remain NOT LICENSED."}
        </div>
      </GlassPanel>

      <GlassPanel title="Forecast Harness" subtitle="Strategy model status for current session">
        <div className="forecast-grid">
          <ForecastModel name="tsmom_126_250_2_10" status="OK" detail="Day-1 paper signal: NAS100 (75.4%), US30 (46.1%)" />
          <ForecastModel name="range_scalper_24_120" status="NO_SIGNAL" detail="Not active for index D1; active on FX M15/H1 walk-forward" />
          <ForecastModel name="tsmom_252_500_2_8" status="WEAK_EDGE" detail="Secondary to 126 variant; lower confidence on current window" />
          <ForecastModel name="chronos_signal" status="UNAVAILABLE" detail="Not run in current paper session" />
          <ForecastModel name="meanrev_trend_filter" status="UNAVAILABLE" detail="Cost-sensitive; not active on current instruments" />
          <ForecastModel name="cas_ensemble" status="UNAVAILABLE" detail="Ensemble not compiled for paper route" />
        </div>
      </GlassPanel>

      {/* ── CAS Expression ── */}
      <GlassPanel title="CAS Expression" subtitle="Compiler state">
        <div className="cas-expression">
          <div className="cas-expr-row">
            <span className="field-label">Expression</span>
            <code className="cas-expr-code">^2^C × ^5^C → ^9^O</code>
          </div>
          <div className="cas-expr-row">
            <span className="field-label">Compiler</span>
            <StatusChip label="NOT_RUN" variant="muted" size="sm" />
            <span className="text-muted-italic">Paper route uses strategy signal directly; CAS expression not compiled</span>
          </div>
          <div className="cas-expr-row">
            <span className="field-label">Admissibility</span>
            <StatusChip label="NOT_CHECKED" variant="muted" size="sm" />
          </div>
          <div className="cas-expr-row">
            <span className="field-label">Domain Descent</span>
            <StatusChip label="NOT_CHECKED" variant="muted" size="sm" />
          </div>
        </div>
      </GlassPanel>

      {/* ── Primary Actions (Disabled) ── */}
      <GlassPanel title="Order" variant="danger">
        <div className="trade-action">
          <div className="trade-action-buttons">
            <button className="btn-paper" disabled>Run Paper Proposal</button>
            <button className="btn-send" disabled>Send Paper Order</button>
          </div>
          <div className="trade-action-reasons">
            <LockLine reason="Paper order execution not wired to broker adapter" />
            <LockLine reason="Live execution: NOT LICENSED — 1/30 paper days, edge OPEN" />
            <LockLine reason="Broker ACCEPT: NOT LICENSED" />
          </div>
        </div>
      </GlassPanel>
    </div>
  );
}

/* ── Sub-components ── */

function buildProposalCandles(entry: number, stop: number, target: number) {
  const oneThird = entry + (target - entry) * 0.33;
  const twoThirds = entry + (target - entry) * 0.66;
  return [
    { time: "stop", open: entry, high: entry, low: stop, close: stop + (entry - stop) * 0.5 },
    { time: "entry", open: stop + (entry - stop) * 0.5, high: oneThird, low: stop, close: entry },
    { time: "target", open: entry, high: target, low: entry, close: twoThirds },
  ];
}

function PriceBlock({ label, value, danger, success }: { label: string; value: number; danger?: boolean; success?: boolean }) {
  return (
    <div className="price-block">
      <span className="field-label">{label}</span>
      <span className="field-value mono price-value" style={{ color: danger ? "var(--danger)" : success ? "var(--success)" : "var(--text-primary)" }}>{value.toFixed(2)}</span>
    </div>
  );
}

function MetaRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="meta-row">
      <span className="field-label">{label}</span>
      <span className={`field-value ${mono ? "mono" : ""}`}>{value}</span>
    </div>
  );
}

function SizeField({ label, value, mono, muted }: { label: string; value: string | number; mono?: boolean; muted?: boolean }) {
  return (
    <div className="size-field">
      <span className="field-label">{label}</span>
      <span className={`field-value ${mono ? "mono" : ""}`} style={{ color: muted ? "var(--text-muted)" : undefined }}>{value}</span>
    </div>
  );
}

function ForecastModel({ name, status, detail }: { name: string; status: "OK" | "NO_SIGNAL" | "WEAK_EDGE" | "UNAVAILABLE" | "ERROR" | "DRIFT_BREACH"; detail: string }) {
  const v: Record<string, "success" | "warning" | "muted" | "danger" | "info"> = {
    OK: "success", NO_SIGNAL: "warning", WEAK_EDGE: "warning", UNAVAILABLE: "muted", ERROR: "danger", DRIFT_BREACH: "danger",
  };
  return (
    <div className="forecast-model">
      <div className="forecast-model-header">
        <code className="forecast-model-name">{name}</code>
        <StatusChip label={status} variant={v[status] ?? "muted"} size="sm" />
      </div>
      <div className="forecast-model-detail">{detail}</div>
    </div>
  );
}

function LockLine({ reason }: { reason: string }) {
  return (
    <div className="lock-line">
      <span style={{ color: "var(--danger)", marginRight: 6 }}>✕</span>
      <span>{reason}</span>
    </div>
  );
}

function NoSignal({ symbol, timeframe }: { symbol: string; timeframe: string }) {
  return (
    <div className="no-signal">
      <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>No paper signal for {symbol} on {timeframe}. Try a different symbol or timeframe.</span>
    </div>
  );
}

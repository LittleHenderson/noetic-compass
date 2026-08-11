/* â”€â”€ CAS Forex - Trading Window (one live-ish chart cockpit pane) â”€â”€ */

import { useCallback, useEffect, useRef, useState } from "react";
import { CandlestickChart } from "./charts/CandlestickChart";
import { StatusChip } from "./StatusChip";
import { SymbolTag } from "./SymbolTag";
import {
  fetchChartWindow,
  postManualOrder,
  type ChartWindow,
  type ManualOrderResult,
} from "../data/api";
import type { PositionMovement } from "../types/evidence";
import {
  formatMovementPositionAge,
  formatMovementPositionSourceLabel,
  isStaticMovementPosition,
} from "../util/movementSource";

export type WindowRole = "Live" | "Demo" | "Strategy A" | "Strategy B";
type ManualOrderSingleResult = NonNullable<ManualOrderResult["results"]>[number];
type ChipVariant = "success" | "warning" | "danger" | "info" | "muted" | "paper";

interface TradingWindowProps {
  role: WindowRole;
  defaultSymbol: string;
  symbols: string[];
  timeframes: string[];
  /** "Live" needs a connected broker feed (none running) - say so honestly. */
  brokerFeedConnected?: boolean;
  pollMs?: number;
  /** All open positions (any symbol) from the movement feed; filtered per pane. */
  positions?: PositionMovement[];
  /** Where the open-position feed came from (e.g. "paper/demo simulator"). */
  positionsSource?: string;
  /** Plain-language truth boundary for the position feed. */
  positionsDetail?: string;
}

export function TradingWindow({
  role,
  defaultSymbol,
  symbols,
  timeframes,
  brokerFeedConnected = false,
  pollMs = 12_000,
  positions = [],
  positionsSource,
  positionsDetail,
}: TradingWindowProps) {
  const [symbol, setSymbol] = useState(defaultSymbol);
  const [timeframe, setTimeframe] = useState("M5");
  const [data, setData] = useState<ChartWindow | null>(null);
  const [loading, setLoading] = useState(true);
  const [paused, setPaused] = useState(false);
  const [orderMsg, setOrderMsg] = useState<string>("");
  const [latestOrderResult, setLatestOrderResult] = useState<ManualOrderSingleResult | null>(null);
  const [placing, setPlacing] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    const w = await fetchChartWindow(symbol, timeframe, 60);
    if (w) setData(w);
    setLoading(false);
  }, [symbol, timeframe]);

  useEffect(() => {
    setLoading(true);
    void load();
  }, [load]);

  useEffect(() => {
    if (paused) return;
    timer.current = setInterval(() => void load(), pollMs);
    return () => { if (timer.current) clearInterval(timer.current); };
  }, [load, paused, pollMs]);

  async function placeOrder(direction: "BUY" | "SELL") {
    setPlacing(true);
    setOrderMsg("");
    setLatestOrderResult(null);
    try {
      const journalReason = window.prompt(
        "Anti-impulse reason for this manual order. Include why this is not revenge/FOMO trading and what invalidates it.",
        "",
      );
      if (journalReason === null) {
        setOrderMsg("Manual order canceled.");
        return;
      }
      const order = { symbol, direction, lots: 0.01, journal_reason: journalReason };
      let res: ManualOrderResult = await postManualOrder(order);
      if (res.status === "JOURNAL_REQUIRED") {
        const blocker = res.manual_order_journal?.blockers?.join("; ") || "Anti-impulse journal reason is required.";
        setOrderMsg(blocker);
        return;
      }
      if (res.status === "CONFIRM_REQUIRED") {
        const need = res.need_confirmation ?? "CONFIRM LIVE ORDER";
        const typed = window.prompt(`Type exactly "${need}" to dispatch this live order.`, "");
        if (typed === null) {
          setOrderMsg("Live order confirmation canceled.");
          return;
        }
        res = await postManualOrder(order, true, typed);
      }
      const first = res.results?.[0];
      setLatestOrderResult(first ?? null);
      const impact = first?.money_impact?.summary ? ` ${first.money_impact.summary}` : "";
      if (res.status === "CONFIRM_REQUIRED") {
        setOrderMsg(`Type exactly "${res.need_confirmation ?? "CONFIRM LIVE ORDER"}" to dispatch this live order.`);
        return;
      }
      if (res.status === "JOURNAL_REQUIRED") {
        setOrderMsg(res.manual_order_journal?.blockers?.join("; ") || "Anti-impulse journal reason is required.");
        return;
      }
      if ((res.executed_count ?? 0) > 0) {
        setOrderMsg(`${res.mode ?? "PAPER"}: ${direction} ${symbol} 0.01 lots filled.${impact}`);
      } else if ((res.blocked_count ?? 0) > 0) {
        setOrderMsg(`Blocked by gate: ${first?.reason ?? "risk/live gate"}.${impact}`);
      } else {
        setOrderMsg(`${first?.status ?? "No fill"}: ${first?.reason ?? ""}.${impact}`);
      }
    } catch {
      setLatestOrderResult(null);
      setOrderMsg("Order failed - is the API reachable?");
    } finally {
      setPlacing(false);
    }
  }

  const quote = data?.quote;
  const marketOpen = quote?.is_market_open ?? false;
  const noFeed = role === "Live" && !brokerFeedConnected;

  return (
    <div className="trading-window">
      <div className="trading-window-header">
        <div className="trading-window-role">
          <span className="trading-window-role-label">{role}</span>
          {noFeed ? (
            <StatusChip label="No broker feed - market data" variant="warning" size="sm" />
          ) : marketOpen ? (
            <StatusChip label="Market open" variant="success" size="sm" />
          ) : (
            <StatusChip label="Market closed" variant="muted" size="sm" />
          )}
        </div>
        <div className="trading-window-selectors">
          <SymbolTag symbol={symbol} size="sm" />
          <select className="tw-select" value={symbol} onChange={(e) => setSymbol(e.target.value)}>
            {symbols.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <select className="tw-select" value={timeframe} onChange={(e) => setTimeframe(e.target.value)}>
            {timeframes.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
      </div>

      <div className="trading-window-quote">
        {quote ? (
          <>
            <span>bid <strong>{quote.bid}</strong></span>
            <span>ask <strong>{quote.ask}</strong></span>
            <span>spread <strong>{quote.spread}</strong></span>
            <span className="tw-session">{quote.session}</span>
          </>
        ) : (
          <span className="tw-muted">{loading ? "Loading quote..." : "No quote"}</span>
        )}
      </div>

      <div className="trading-window-chart">
        {data && data.candles.length > 0 ? (
          <CandlestickChart candles={data.candles} symbol={symbol} height={180} />
        ) : (
          <div className="tw-muted" style={{ padding: 28, textAlign: "center" }}>
            {loading ? "Loading candles..." : data?.error ?? "No candle data for this symbol/timeframe."}
          </div>
        )}
      </div>

      {/* Open positions for this symbol (MT4-style), from the movement feed */}
      <div className="tw-positions">
        {(() => {
          const mine = positions.filter((p) => p.symbol === symbol);
          if (mine.length === 0) {
            return <div className="tw-muted" style={{ fontSize: "0.8125rem" }}>No open position in {symbol}.</div>;
          }
          const staleMine = mine.filter(isStaticMovementPosition);
          return (
            <>
              {staleMine.length > 0 && (
                <div className="tw-position-source-warning">
                  Static simulator price: {staleMine.length} {staleMine.length === 1 ? "position is" : "positions are"} not being repriced by MT5/provider quotes, so Now and floating P&amp;L can stay at entry.
                </div>
              )}
              <table className="tw-positions-table">
                <thead>
                  <tr><th>Source</th><th>Side</th><th>Lots</th><th>Age</th><th>Entry</th><th>Now</th><th>P&amp;L</th></tr>
                </thead>
                <tbody>
                  {mine.map((p) => {
                    const priceSource = p.price_source ?? (p.broker_ticket ? "mt5_live_position" : "paper_route_snapshot:static_simulation");
                    const providerBacked = priceSource.startsWith("provider_snapshot:");
                    const stale = isStaticMovementPosition(p);
                    const sourceTitle = [priceSource, p.stale_reason, p.opened_at ? `opened ${p.opened_at}` : ""].filter(Boolean).join(" | ");
                    return (
                      <tr key={p.row_id}>
                        <td>
                          <span className={`tw-source-pill ${p.broker_ticket || providerBacked ? "live" : "sim"} ${stale ? "stale" : ""}`} title={sourceTitle}>
                            {formatMovementPositionSourceLabel(p.position_source_label, p.broker_ticket, priceSource)}
                          </span>
                        </td>
                        <td className={p.side === "LONG" ? "tw-long" : "tw-short"}>{p.side}</td>
                        <td className="mono">{p.lot_size}</td>
                        <td className="mono" title={p.opened_at ?? p.stale_reason ?? undefined}>{formatMovementPositionAge(p)}</td>
                        <td className="mono">{p.open_price}</td>
                        <td className="mono">{p.current_price}</td>
                        <td className="mono" style={{ color: p.floating_pnl_usd > 0 ? "var(--success)" : p.floating_pnl_usd < 0 ? "var(--danger)" : "var(--text-secondary)" }}>
                          {p.floating_pnl_usd >= 0 ? "+" : ""}{p.floating_pnl_usd.toFixed(2)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </>
          );
        })()}
      </div>

      <div className="trading-window-footer">
        <div className="tw-feed-label">
          {data?.source ? `${data.source}  -  ${data.feed_label}` : "-"}
          {data?.cached ? "  -  cached" : ""}
          {data?.fallback_used ? "  -  fallback active" : ""}
          {positionsSource ? `  -  positions: ${positionsSource}` : ""}
        </div>
        <div className="trading-window-controls">
          <button className="tw-btn tw-buy" disabled={placing} onClick={() => void placeOrder("BUY")}>Buy</button>
          <button className="tw-btn tw-sell" disabled={placing} onClick={() => void placeOrder("SELL")}>Sell</button>
          <button
            className={`tw-btn tw-pause ${paused ? "active" : ""}`}
            onClick={() => setPaused((v) => !v)}
            title={paused ? "Resume live polling" : "Pause live polling"}
          >
            {paused ? "Resume" : "Pause"}
          </button>
        </div>
      </div>
      {positionsDetail && positions.some((position) => position.symbol === symbol) ? (
        <div className="tw-position-source-warning">{positionsDetail}</div>
      ) : null}
      {orderMsg && <div className="tw-order-msg">{orderMsg}</div>}
      {latestOrderResult && <TradeExplanationCard result={latestOrderResult} />}
    </div>
  );
}

function TradeExplanationCard({ result }: { result: ManualOrderSingleResult }) {
  const card = result.trade_explanation_card;
  if (!card) return null;
  const moneyImpact = card.money_impact ?? result.money_impact ?? {};
  const protectiveOrders = card.protective_orders ?? {};
  const preTrade = card.pre_trade_money ?? result.pre_trade_estimate;
  const gateTrace = Array.isArray(card.gate_trace) ? card.gate_trace : [];
  const audit = card.audit ?? {};
  const executionProvenance = recordValue(card.execution_provenance) ?? recordValue(result.execution_provenance) ?? {};
  const liveGateReport = recordValue(card.live_gate_report) ?? recordValue(result.live_gate_report) ?? {};
  const liveReadinessEvidence = recordValue(card.live_readiness_evidence) ?? {};
  const initiator = recordValue(executionProvenance.initiator) ?? {};
  const runtimeLane = recordValue(executionProvenance.runtime_lane) ?? {};
  const dispatchPath = recordValue(executionProvenance.dispatch_path) ?? {};
  const protectionStatus = stringValue(protectiveOrders.status, "UNKNOWN");
  const auditId = stringValue(audit.attempt_id, "none");
  const provenanceHash = stringValue(executionProvenance.provenance_hash, "not attached");
  const liveBlockingStage = stringValue(liveGateReport.blocking_stage, "");
  const liveNextAction = stringValue(liveGateReport.next_action, "");

  return (
    <div className="tw-explanation-card" aria-label="Trade explanation card">
      <div className="tw-explanation-header">
        <div>
          <div className="tw-explanation-title">Trade Explanation</div>
          <div className="tw-explanation-summary">
            {stringValue(card.summary ?? result.reason, "No dispatch reason returned.")}
          </div>
        </div>
        <StatusChip label={stringValue(result.status, "UNKNOWN")} variant={gateStatusVariant(result.status)} size="sm" />
      </div>

      <div className="tw-explanation-grid">
        <ExplanationMetric label="Bridge touched" value={yesNo(moneyImpact.broker_bridge_touched)} />
        <ExplanationMetric label="Executed" value={yesNo(moneyImpact.order_executed)} />
        <ExplanationMetric label="Real broker" value={yesNo(moneyImpact.real_broker)} />
        <ExplanationMetric label="Protection" value={protectionStatus} />
        <ExplanationMetric label="Risk at SL" value={formatMoneyValue(preTrade?.risk_at_stop_usd)} />
        <ExplanationMetric label="Margin needed" value={formatMoneyValue(preTrade?.estimated_margin_required_usd)} />
        <ExplanationMetric label="Initiator" value={stringValue(initiator.kind, "not attached")} />
        <ExplanationMetric label="Runtime lane" value={stringValue(runtimeLane.effective_lane, "not attached")} />
        <ExplanationMetric label="Final gate" value={stringValue(dispatchPath.terminal_stage, "not attached")} />
        <ExplanationMetric label="Bridge state" value={stringValue(dispatchPath.bridge_touch_state, "not attached")} />
      </div>

      <div className="tw-explanation-money">
        {stringValue(moneyImpact.summary, "Money impact was not returned by the dispatcher.")}
      </div>

      {liveBlockingStage && (
        <div className="tw-explanation-money">
          Live readiness: {liveBlockingStage}
          {liveNextAction ? ` - ${liveNextAction}` : ""}
        </div>
      )}

      <div className="tw-explanation-section-title">Gate trace</div>
      <div className="tw-gate-trace">
        {gateTrace.length > 0 ? (
          gateTrace.map((stage, idx) => {
            const status = stringValue(stage.status, "UNKNOWN");
            const blockers = Array.isArray(stage.blockers) ? stage.blockers.map((item) => String(item)) : [];
            return (
              <div className="tw-gate-row" key={`${stringValue(stage.stage, "stage")}-${idx}`}>
                <div className="tw-gate-row-top">
                  <code className="mono">{stringValue(stage.stage, "stage")}</code>
                  <StatusChip label={status} variant={gateStatusVariant(status)} size="sm" />
                </div>
                <div className="tw-gate-detail">{stringValue(stage.detail, "")}</div>
                {blockers.length > 0 && (
                  <div className="tw-gate-blockers">blockers: {blockers.join("; ")}</div>
                )}
                {recordValue(stage.evidence_snapshot) && (
                  <div className="tw-gate-detail">
                    evidence: {JSON.stringify(recordValue(stage.evidence_snapshot))}
                  </div>
                )}
              </div>
            );
          })
        ) : (
          <div className="tw-muted">No gate trace returned for this dispatch result.</div>
        )}
      </div>

      {Object.keys(liveReadinessEvidence).length > 0 && (
        <>
          <div className="tw-explanation-section-title">Live evidence</div>
          <div className="tw-gate-trace">
            {Object.entries(liveReadinessEvidence).map(([key, value]) => (
              <div className="tw-gate-row" key={key}>
                <div className="tw-gate-row-top">
                  <code className="mono">{key}</code>
                </div>
                <div className="tw-gate-detail">{JSON.stringify(value)}</div>
              </div>
            ))}
          </div>
        </>
      )}

      <div className="tw-explanation-foot">
        <span>audit attempt: <code className="mono">{auditId}</code></span>
        <span>provenance: <code className="mono">{provenanceHash}</code></span>
        <span>{stringValue(card.claim_boundary, "This card explains the dispatch result; it is not a new order authorization.")}</span>
      </div>
    </div>
  );
}

function ExplanationMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="tw-explanation-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function stringValue(value: unknown, fallback: string): string {
  if (typeof value === "string" && value.trim()) return value;
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  if (typeof value === "boolean") return value ? "yes" : "no";
  return fallback;
}

function recordValue(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function yesNo(value: unknown): string {
  if (typeof value === "boolean") return value ? "yes" : "no";
  return "unknown";
}

function formatMoneyValue(value: unknown): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "n/a";
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function gateStatusVariant(status: unknown): ChipVariant {
  const normalized = String(status ?? "").toUpperCase();
  if (normalized.includes("EXECUTED") || normalized === "PROTECTED") return "success";
  if (normalized.includes("BLOCKED") || normalized.includes("REJECTED")) return "warning";
  if (normalized.includes("FAILED") || normalized.includes("ERROR") || normalized === "UNKNOWN") return "danger";
  if (normalized.includes("PASSED") || normalized.includes("DONE")) return "info";
  if (normalized.includes("PAPER")) return "paper";
  return "muted";
}

/* ── CAS Forex — Trading Window (one live-ish chart cockpit pane) ── */

import { useCallback, useEffect, useRef, useState } from "react";
import { CandlestickChart } from "./charts/CandlestickChart";
import { StatusChip } from "./StatusChip";
import {
  fetchChartWindow,
  postManualOrder,
  type ChartWindow,
  type ManualOrderResult,
} from "../data/api";

export type WindowRole = "Live" | "Demo" | "Strategy A" | "Strategy B";

interface TradingWindowProps {
  role: WindowRole;
  defaultSymbol: string;
  symbols: string[];
  timeframes: string[];
  /** "Live" needs a connected broker feed (none running) — say so honestly. */
  brokerFeedConnected?: boolean;
  pollMs?: number;
}

export function TradingWindow({
  role,
  defaultSymbol,
  symbols,
  timeframes,
  brokerFeedConnected = false,
  pollMs = 12_000,
}: TradingWindowProps) {
  const [symbol, setSymbol] = useState(defaultSymbol);
  const [timeframe, setTimeframe] = useState("M5");
  const [data, setData] = useState<ChartWindow | null>(null);
  const [loading, setLoading] = useState(true);
  const [paused, setPaused] = useState(false);
  const [orderMsg, setOrderMsg] = useState<string>("");
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
    try {
      const res: ManualOrderResult = await postManualOrder({ symbol, direction, lots: 0.01 });
      if (res.status === "CONFIRM_REQUIRED") {
        setOrderMsg("Live is authorized — confirm required (not sent).");
      } else if ((res.executed_count ?? 0) > 0) {
        setOrderMsg(`${res.mode ?? "PAPER"}: ${direction} ${symbol} 0.01 lots filled.`);
      } else if ((res.blocked_count ?? 0) > 0) {
        setOrderMsg(`Blocked by gate: ${res.results?.[0]?.reason ?? "risk/live gate"}.`);
      } else {
        setOrderMsg(`${res.results?.[0]?.status ?? "No fill"}: ${res.results?.[0]?.reason ?? ""}.`);
      }
    } catch {
      setOrderMsg("Order failed — is the API reachable?");
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
            <StatusChip label="No broker feed — market data" variant="warning" size="sm" />
          ) : marketOpen ? (
            <StatusChip label="Market open" variant="success" size="sm" />
          ) : (
            <StatusChip label="Market closed" variant="muted" size="sm" />
          )}
        </div>
        <div className="trading-window-selectors">
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
          <span className="tw-muted">{loading ? "Loading quote…" : "No quote"}</span>
        )}
      </div>

      <div className="trading-window-chart">
        {data && data.candles.length > 0 ? (
          <CandlestickChart candles={data.candles} symbol={symbol} height={180} />
        ) : (
          <div className="tw-muted" style={{ padding: 28, textAlign: "center" }}>
            {loading ? "Loading candles…" : "No candle data for this symbol/timeframe."}
          </div>
        )}
      </div>

      <div className="trading-window-footer">
        <div className="tw-feed-label">
          {data?.source ? `${data.source} · ${data.feed_label}` : "—"}
          {data?.cached ? " · cached" : ""}
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
      {orderMsg && <div className="tw-order-msg">{orderMsg}</div>}
    </div>
  );
}

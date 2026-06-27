/* ── CAS Forex — Trading Windows (2×2 live chart cockpit) ── */

import { useEffect, useRef, useState } from "react";
import { GlassPanel } from "../components/GlassPanel";
import { TradingWindow, type WindowRole } from "../components/TradingWindow";
import { fetchChartSymbols, fetchMovementStream } from "../data/api";
import type { DashboardState, MovementStreamState } from "../types/evidence";

interface WindowsPageProps {
  state: DashboardState;
}

const FALLBACK_SYMBOLS = ["EUR/USD", "XAU/USD", "GBP/USD", "USD/JPY"];
const FALLBACK_TIMEFRAMES = ["M1", "M5", "M15", "H1", "D1"];

export function WindowsPage({ state }: WindowsPageProps) {
  const [symbols, setSymbols] = useState<string[]>(FALLBACK_SYMBOLS);
  const [timeframes, setTimeframes] = useState<string[]>(FALLBACK_TIMEFRAMES);
  const [movement, setMovement] = useState<MovementStreamState | null>(state.movementStream ?? null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    void fetchChartSymbols().then((s) => {
      if (s && s.symbols.length) setSymbols(s.symbols);
      if (s && s.timeframes.length) setTimeframes(s.timeframes);
    });
  }, []);

  // Poll the account + open-positions feed so the panes behave like a terminal.
  useEffect(() => {
    const load = () => { void fetchMovementStream().then((m) => { if (m) setMovement(m); }); };
    load();
    timer.current = setInterval(load, 12_000);
    return () => { if (timer.current) clearInterval(timer.current); };
  }, []);

  // Strategy windows default to the top strategy leads / Fury replay candidates,
  // falling back to sensible majors when those aren't available.
  const leadSymbols = (state.strategyLeads ?? [])
    .flatMap((l) => l.symbols_promoted_for_next_tests ?? [])
    .filter((s) => symbols.includes(s));
  const furySymbols = (state.forexFuryReplayCandidates?.candidates ?? [])
    .filter((c) => c.symbol_supported)
    .map((c) => c.cas_symbol)
    .filter((s) => symbols.includes(s));
  const stratA = leadSymbols[0] ?? furySymbols[0] ?? "GBP/USD";
  const stratB = leadSymbols[1] ?? furySymbols[1] ?? "USD/JPY";

  const panes: { role: WindowRole; symbol: string; brokerFeedConnected: boolean }[] = [
    { role: "Live", symbol: "EUR/USD", brokerFeedConnected: false },
    { role: "Demo", symbol: "XAU/USD", brokerFeedConnected: false },
    { role: "Strategy A", symbol: stratA, brokerFeedConnected: false },
    { role: "Strategy B", symbol: stratB, brokerFeedConnected: false },
  ];

  const acct = movement?.account;
  const positions = movement?.positions ?? [];
  const positionsSource = acct?.source === "mt5_live" ? "live broker" : "paper/demo simulator";
  const usd = (v: number | undefined) => `$${(v ?? 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;

  return (
    <div className="windows-page">
      <GlassPanel
        title="Trading Windows"
        subtitle="Four live-ish chart panes with open positions + P&L — like MT4/TradingView"
      >
        {/* Account header bar — the terminal's account line */}
        <div className="tw-account-bar">
          <AcctStat label="Balance" value={usd(acct?.balance_usd)} />
          <AcctStat label="Equity" value={usd(acct?.equity_usd)} />
          <AcctStat
            label="Floating P&L"
            value={`${(acct?.floating_pnl_usd ?? 0) >= 0 ? "+" : ""}${usd(acct?.floating_pnl_usd).replace("$", "$")}`}
            tone={(acct?.floating_pnl_usd ?? 0) > 0 ? "up" : (acct?.floating_pnl_usd ?? 0) < 0 ? "down" : undefined}
          />
          <AcctStat label="Open positions" value={`${acct?.open_position_count ?? positions.length}`} />
          <AcctStat label="Margin / Free" value={`${usd(acct?.margin_used_usd)} / ${usd(acct?.free_margin_usd)}`} />
          <AcctStat label="Mode" value={movement?.mode === "LIVE" ? "LIVE" : "PAPER / DEMO"} />
        </div>
        <div className="windows-intro">
          Near-real-time market data (delayed retail feed, not a pro tick stream). “Live”
          needs a connected broker feed — none is running yet, so it shows market data + the
          paper/demo account, labelled accordingly. Open positions and P&L above and per pane
          are from the <strong>{positionsSource}</strong>. Buy/Sell route a 0.01-lot order through the
          <strong> gated</strong> dispatch (paper-safe by default). Pause stops that pane’s polling.
        </div>

        {/* All open positions — the MT4 "Terminal" trade list (always visible) */}
        <div className="tw-all-positions">
          <div className="tw-all-positions-title">Open Positions ({positions.length})</div>
          {positions.length > 0 ? (
            <table className="tw-positions-table">
              <thead>
                <tr><th>Symbol</th><th>Side</th><th>Lots</th><th>Entry</th><th>Now</th><th>SL</th><th>TP</th><th>Floating P&amp;L</th></tr>
              </thead>
              <tbody>
                {positions.map((p) => (
                  <tr key={p.row_id}>
                    <td className="mono" style={{ fontWeight: 700 }}>{p.symbol}</td>
                    <td className={p.side === "LONG" ? "tw-long" : "tw-short"}>{p.side}</td>
                    <td className="mono">{p.lot_size}</td>
                    <td className="mono">{p.open_price}</td>
                    <td className="mono">{p.current_price}</td>
                    <td className="mono" style={{ color: "var(--danger)" }}>{p.stop_loss ?? "—"}</td>
                    <td className="mono" style={{ color: "var(--success)" }}>{p.take_profit ?? "—"}</td>
                    <td className="mono" style={{ color: p.floating_pnl_usd > 0 ? "var(--success)" : p.floating_pnl_usd < 0 ? "var(--danger)" : "var(--text-secondary)" }}>
                      {p.floating_pnl_usd >= 0 ? "+" : ""}{p.floating_pnl_usd.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="tw-muted" style={{ fontSize: "0.72rem" }}>No open positions right now.</div>
          )}
        </div>
      </GlassPanel>

      <div className="windows-grid">
        {panes.map((p) => (
          <TradingWindow
            key={p.role}
            role={p.role}
            defaultSymbol={p.symbol}
            symbols={symbols}
            timeframes={timeframes}
            brokerFeedConnected={p.brokerFeedConnected}
            positions={positions}
            positionsSource={positionsSource}
          />
        ))}
      </div>
    </div>
  );
}

function AcctStat({ label, value, tone }: { label: string; value: string; tone?: "up" | "down" }) {
  return (
    <div className="tw-account-stat">
      <span className="tw-account-stat-label">{label}</span>
      <span className="tw-account-stat-value" style={{ color: tone === "up" ? "var(--success)" : tone === "down" ? "var(--danger)" : undefined }}>{value}</span>
    </div>
  );
}

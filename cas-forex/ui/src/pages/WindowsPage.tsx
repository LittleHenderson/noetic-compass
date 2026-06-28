/* ── CAS Forex — Trading Windows (2×2 live chart cockpit) ── */

import { useEffect, useRef, useState } from "react";
import { GlassPanel } from "../components/GlassPanel";
import { TradingWindow, type WindowRole } from "../components/TradingWindow";
import {
  fetchChartSymbols,
  fetchMovementStream,
  fetchDispatchLoopStatus,
  startDispatchLoop,
  stopDispatchLoop,
  type DispatchLoopState,
} from "../data/api";
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

      <AutoTradeLoopBar />

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

function AutoTradeLoopBar() {
  const [loop, setLoop] = useState<DispatchLoopState | null>(null);
  const [interval, setIntervalSec] = useState(60);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const poll = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const load = () => { void fetchDispatchLoopStatus().then((s) => { if (s) setLoop(s); }); };
    load();
    poll.current = setInterval(load, 5000);
    return () => { if (poll.current) clearInterval(poll.current); };
  }, []);

  async function start() {
    setBusy(true); setMsg("");
    try {
      const s = await startDispatchLoop(interval);
      if (s.status === "CONFIRM_REQUIRED") {
        setMsg("Live trading is authorized — starting the loop could place REAL orders. Tap “Start LIVE loop” to confirm.");
      }
      setLoop(s);
    } catch { setMsg("Couldn't start the loop — is the API reachable?"); }
    finally { setBusy(false); }
  }
  async function startLiveConfirmed() {
    setBusy(true); setMsg("");
    try { setLoop(await startDispatchLoop(interval, true)); }
    catch { setMsg("Couldn't start the loop."); }
    finally { setBusy(false); }
  }
  async function stop() {
    setBusy(true); setMsg("");
    try { setLoop(await stopDispatchLoop()); }
    catch { setMsg("Couldn't stop the loop."); }
    finally { setBusy(false); }
  }

  const running = loop?.running ?? false;
  const needsLiveConfirm = loop?.status === "CONFIRM_REQUIRED";

  return (
    <GlassPanel
      title="Auto-Trade Loop"
      subtitle="Run the strategy on a timer — the bot trades on its own (paper-safe by default)"
      variant={running ? "info" : "default"}
    >
      <div className="tw-loop-bar">
        <div className="tw-loop-status">
          <StatusDot on={running} />
          <span className="tw-loop-state">{running ? "RUNNING" : "STOPPED"}</span>
          <span className="tw-loop-mode">{loop?.mode === "LIVE" ? "LIVE" : "PAPER / DEMO"}</span>
        </div>
        <label className="tw-loop-interval">
          every
          <input type="number" min={10} max={3600} value={interval}
            disabled={running}
            onChange={(e) => setIntervalSec(Math.max(10, Math.min(3600, Number(e.target.value) || 60)))} />
          sec
        </label>
        {!running && !needsLiveConfirm && (
          <button className="tw-btn tw-buy" disabled={busy} onClick={() => void start()}>Start loop</button>
        )}
        {!running && needsLiveConfirm && (
          <button className="tw-btn tw-sell" disabled={busy} onClick={() => void startLiveConfirmed()}>Start LIVE loop</button>
        )}
        {running && (
          <button className="tw-btn tw-sell" disabled={busy} onClick={() => void stop()}>Stop loop</button>
        )}
      </div>
      <div className="tw-loop-detail">
        {loop?.cycles_run != null && <span>cycles run: <strong>{loop.cycles_run}</strong></span>}
        {loop?.last_summary && <span>last: <strong>{loop.last_summary}</strong></span>}
        {loop?.last_error && <span style={{ color: "var(--danger)" }}>error: {loop.last_error}</span>}
      </div>
      {msg && <div className="control-field-desc" style={{ color: needsLiveConfirm ? "var(--danger)" : "var(--text-secondary)" }}>{msg}</div>}
      <div className="control-field-desc">
        Runs the same gated dispatch cycle as the manual Buy/Sell, on a timer. Paper-safe by default —
        it can only reach a live broker once you authorize live trading on Settings, and the broker
        re-checks at order time. This is what builds your paper-proof track record automatically.
      </div>
    </GlassPanel>
  );
}

function StatusDot({ on }: { on: boolean }) {
  return <span style={{ width: 9, height: 9, borderRadius: 5, background: on ? "var(--success)" : "var(--text-muted)", display: "inline-block" }} className={on ? "cas-pulse" : undefined} />;
}

function AcctStat({ label, value, tone }: { label: string; value: string; tone?: "up" | "down" }) {
  return (
    <div className="tw-account-stat">
      <span className="tw-account-stat-label">{label}</span>
      <span className="tw-account-stat-value" style={{ color: tone === "up" ? "var(--success)" : tone === "down" ? "var(--danger)" : undefined }}>{value}</span>
    </div>
  );
}

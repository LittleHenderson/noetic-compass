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
  fetchMt5Account,
  type DispatchLoopState,
  type Mt5LiveState,
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

  const acct = movement?.account;
  const positions = movement?.positions ?? [];

  // Strategy panes prefer symbols that currently have an OPEN POSITION (so the
  // owner sees a live position sitting on a chart), then top strategy leads /
  // Fury candidates, then sensible index defaults.
  const positionSymbols = positions.map((p) => p.symbol).filter((s) => symbols.includes(s));
  const leadSymbols = (state.strategyLeads ?? [])
    .flatMap((l) => l.symbols_promoted_for_next_tests ?? [])
    .filter((s) => symbols.includes(s));
  const furySymbols = (state.forexFuryReplayCandidates?.candidates ?? [])
    .filter((c) => c.symbol_supported)
    .map((c) => c.cas_symbol)
    .filter((s) => symbols.includes(s));
  const stratA = positionSymbols[0] ?? leadSymbols[0] ?? furySymbols[0] ?? "US30";
  const stratB = positionSymbols[1] ?? leadSymbols[1] ?? furySymbols[1] ?? "NAS100";

  const panes: { role: WindowRole; symbol: string; brokerFeedConnected: boolean }[] = [
    { role: "Live", symbol: "EUR/USD", brokerFeedConnected: false },
    { role: "Demo", symbol: "XAU/USD", brokerFeedConnected: false },
    { role: "Strategy A", symbol: stratA, brokerFeedConnected: false },
    { role: "Strategy B", symbol: stratB, brokerFeedConnected: false },
  ];

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

        <MarketStatusStrip />
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

      <Mt5LiveAccountPanel />

      <AutoTradeLoopBar symbols={symbols} />

      <div className="windows-grid">
        {panes.map((p) => (
          <TradingWindow
            key={`${p.role}-${p.symbol}`}
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

interface MarketStatus {
  open: boolean;
  session: "Asian" | "London" | "New York" | "Overlap";
  londonActive: boolean;
  newYorkActive: boolean;
  asianActive: boolean;
  nextOpen: Date | null;
}

// Forex week: opens Sunday ~22:00 UTC, closes Friday ~22:00 UTC. Sessions by UTC hour.
function computeMarketStatus(now: Date): MarketStatus {
  const day = now.getUTCDay(); // 0=Sun .. 6=Sat
  const h = now.getUTCHours();
  let open: boolean;
  if (day === 6) open = false;            // Saturday — closed
  else if (day === 0) open = h >= 22;     // Sunday — opens 22:00 UTC
  else if (day === 5) open = h < 22;      // Friday — closes 22:00 UTC
  else open = true;                        // Mon–Thu — open

  const asianActive = h < 8 || h >= 21;
  const londonActive = h >= 8 && h < 16;          // includes the overlap
  const newYorkActive = h >= 12 && h < 21;        // includes the overlap
  let session: MarketStatus["session"] = "Asian";
  if (h >= 12 && h < 16) session = "Overlap";
  else if (h >= 8 && h < 12) session = "London";
  else if (h >= 16 && h < 21) session = "New York";

  let nextOpen: Date | null = null;
  if (!open) {
    let cand = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 22, 0, 0));
    // First Sunday-22:00-UTC strictly after now.
    for (let i = 0; i < 8 && !(cand.getUTCDay() === 0 && cand > now); i++) {
      cand = new Date(cand.getTime() + 86_400_000);
    }
    nextOpen = cand;
  }
  return { open, session, asianActive, londonActive, newYorkActive, nextOpen };
}

function formatCountdown(ms: number): string {
  if (ms <= 0) return "now";
  const s = Math.floor(ms / 1000);
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m ${sec}s`;
  return `${m}m ${sec}s`;
}

function MarketStatusStrip() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  const st = computeMarketStatus(now);
  const sessions: { name: string; active: boolean; hours: string }[] = [
    { name: "Asian", active: st.asianActive, hours: "00–08 UTC" },
    { name: "London", active: st.londonActive, hours: "08–16 UTC" },
    { name: "New York", active: st.newYorkActive, hours: "12–21 UTC" },
  ];
  const countdown = st.nextOpen ? formatCountdown(st.nextOpen.getTime() - now.getTime()) : "";

  return (
    <div className="tw-market-strip">
      <span className={`tw-market-badge ${st.open ? "open" : "closed"}`}>
        {st.open ? "MARKET OPEN" : "MARKET CLOSED"}
      </span>
      <div className="tw-session-chips">
        {sessions.map((s) => (
          <span key={s.name} className={`tw-session-chip ${s.active ? "active" : ""}`} title={s.hours}>
            {s.name}
          </span>
        ))}
      </div>
      {!st.open && st.nextOpen && (
        <span className="tw-market-reopen">reopens in <strong>{countdown}</strong> (Sun 22:00 UTC)</span>
      )}
      {st.open && (
        <span className="tw-market-reopen">active session: <strong>{st.session}</strong></span>
      )}
    </div>
  );
}

function Mt5LiveAccountPanel() {
  const [mt5, setMt5] = useState<Mt5LiveState | null>(null);
  const poll = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const load = () => { void fetchMt5Account().then((s) => { if (s) setMt5(s); }); };
    load();
    poll.current = setInterval(load, 6000);
    return () => { if (poll.current) clearInterval(poll.current); };
  }, []);

  const connected = mt5?.connected ?? false;
  const acc = mt5?.account;
  const positions = mt5?.positions ?? [];
  const usd = (v: number | undefined) => `$${(v ?? 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;

  return (
    <GlassPanel
      title="MetaTrader 5 — Connected Account"
      subtitle="Live, read-only, straight from your MT5 terminal"
      variant={connected ? "info" : "default"}
    >
      {connected && acc ? (
        <>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10, flexWrap: "wrap" }}>
            <StatusDot on={true} />
            <span style={{ fontWeight: 700, fontSize: "0.84rem" }}>#{acc.login}</span>
            <span className="tw-loop-mode">{acc.server}</span>
            <StatusChip label={mt5?.is_demo ? "DEMO — paper-safe" : "LIVE ACCOUNT"} variant={mt5?.is_demo ? "success" : "danger"} size="sm" />
            {mt5?.algo_allowed && <StatusChip label="Algo on" variant="muted" size="sm" />}
          </div>
          <div className="tw-account-bar" style={{ marginBottom: 10 }}>
            <AcctStat label="Balance" value={usd(acc.balance_usd)} />
            <AcctStat label="Equity" value={usd(acc.equity_usd)} />
            <AcctStat
              label="Floating P&L"
              value={`${acc.floating_pnl_usd >= 0 ? "+" : ""}${usd(acc.floating_pnl_usd)}`}
              tone={acc.floating_pnl_usd > 0 ? "up" : acc.floating_pnl_usd < 0 ? "down" : undefined}
            />
            <AcctStat label="Margin / Free" value={`${usd(acc.margin_used_usd)} / ${usd(acc.free_margin_usd)}`} />
            <AcctStat label="Open positions" value={`${mt5?.open_position_count ?? positions.length}`} />
            <AcctStat label="Leverage" value={`1:${acc.leverage}`} />
          </div>
          <div className="tw-all-positions">
            <div className="tw-all-positions-title">MT5 Open Positions ({positions.length})</div>
            {positions.length > 0 ? (
              <table className="tw-positions-table">
                <thead>
                  <tr><th>Symbol</th><th>Side</th><th>Lots</th><th>Open</th><th>Now</th><th>SL</th><th>TP</th><th>Floating P&amp;L</th></tr>
                </thead>
                <tbody>
                  {positions.map((p) => (
                    <tr key={p.ticket ?? `${p.symbol}-${p.open_price}`}>
                      <td className="mono" style={{ fontWeight: 700 }}>{p.symbol}</td>
                      <td className={p.side === "LONG" ? "tw-long" : "tw-short"}>{p.side}</td>
                      <td className="mono">{p.lots}</td>
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
              <div className="tw-muted" style={{ fontSize: "0.72rem" }}>No open positions in MT5 right now.</div>
            )}
          </div>
          {mt5?.note && <div className="control-field-desc" style={{ marginTop: 8 }}>{mt5.note}</div>}
        </>
      ) : (
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
            <StatusDot on={false} />
            <span style={{ fontWeight: 700, fontSize: "0.82rem" }}>Not connected</span>
          </div>
          <div className="control-field-desc">
            {mt5?.detail ?? mt5?.error ?? "Open your MetaTrader 5 terminal, log into your account, and make sure it shows a live connection (ticking prices). This panel will pick it up automatically."}
          </div>
        </div>
      )}
    </GlassPanel>
  );
}

const LOOP_SESSIONS = ["Asian", "London", "New York"];

function AutoTradeLoopBar({ symbols }: { symbols: string[] }) {
  const [loop, setLoop] = useState<DispatchLoopState | null>(null);
  const [interval, setIntervalSec] = useState(60);
  const [targetSymbols, setTargetSymbols] = useState<string[]>([]);
  const [targetSessions, setTargetSessions] = useState<string[]>([]);
  const [synced, setSynced] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const poll = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const load = () => {
      void fetchDispatchLoopStatus().then((s) => {
        if (!s) return;
        setLoop(s);
        // Reflect the running loop's targeting once, so the UI matches the server.
        setSynced((was) => {
          if (!was) {
            setTargetSymbols(s.symbols ?? []);
            setTargetSessions(s.sessions ?? []);
          }
          return true;
        });
      });
    };
    load();
    poll.current = setInterval(load, 5000);
    return () => { if (poll.current) clearInterval(poll.current); };
  }, []);

  const body = () => ({ interval_seconds: interval, symbols: targetSymbols, sessions: targetSessions });

  async function start() {
    setBusy(true); setMsg("");
    try {
      const s = await startDispatchLoop(body());
      if (s.status === "CONFIRM_REQUIRED") {
        setMsg("Live trading is authorized — starting the loop could place REAL orders. Tap “Start LIVE loop” to confirm.");
      }
      setLoop(s);
    } catch { setMsg("Couldn't start the loop — is the API reachable?"); }
    finally { setBusy(false); }
  }
  async function startLiveConfirmed() {
    setBusy(true); setMsg("");
    try { setLoop(await startDispatchLoop(body(), true)); }
    catch { setMsg("Couldn't start the loop."); }
    finally { setBusy(false); }
  }
  async function stop() {
    setBusy(true); setMsg("");
    try { setLoop(await stopDispatchLoop()); }
    catch { setMsg("Couldn't stop the loop."); }
    finally { setBusy(false); }
  }
  async function applySettings() {
    setBusy(true); setMsg("");
    try { setLoop(await startDispatchLoop(body(), true)); setMsg("Applied — takes effect on the next cycle."); }
    catch { setMsg("Couldn't update the loop."); }
    finally { setBusy(false); }
  }

  function toggleSymbol(s: string) {
    setTargetSymbols((cur) => cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s]);
  }
  function toggleSession(s: string) {
    setTargetSessions((cur) => cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s]);
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
          <input type="number" min={1} max={86400} step={1} value={interval}
            onChange={(e) => setIntervalSec(Math.max(1, Math.min(86400, Math.round(Number(e.target.value)) || 1)))} />
          sec
        </label>
        {!running && !needsLiveConfirm && (
          <button className="tw-btn tw-buy" disabled={busy} onClick={() => void start()}>Start loop</button>
        )}
        {!running && needsLiveConfirm && (
          <button className="tw-btn tw-sell" disabled={busy} onClick={() => void startLiveConfirmed()}>Start LIVE loop</button>
        )}
        {running && (
          <>
            <button className="tw-btn tw-pause" disabled={busy} onClick={() => void applySettings()}>Apply</button>
            <button className="tw-btn tw-sell" disabled={busy} onClick={() => void stop()}>Stop loop</button>
          </>
        )}
      </div>

      {/* Targeting: which symbols + which sessions the loop trades */}
      <div className="tw-loop-target">
        <div className="tw-loop-target-row">
          <span className="tw-loop-target-label">Trade only</span>
          <div className="tw-loop-chips">
            {symbols.map((s) => (
              <button key={s} type="button"
                className={`tw-loop-chip ${targetSymbols.includes(s) ? "on" : ""}`}
                onClick={() => toggleSymbol(s)}>{s}</button>
            ))}
          </div>
          <span className="tw-loop-target-hint">{targetSymbols.length === 0 ? "(all symbols)" : `${targetSymbols.length} selected`}</span>
        </div>
        <div className="tw-loop-target-row">
          <span className="tw-loop-target-label">During sessions</span>
          <div className="tw-loop-chips">
            {LOOP_SESSIONS.map((s) => (
              <button key={s} type="button"
                className={`tw-loop-chip ${targetSessions.includes(s) ? "on" : ""} ${(loop?.active_sessions ?? []).includes(s) ? "live" : ""}`}
                onClick={() => toggleSession(s)}>{s}</button>
            ))}
          </div>
          <span className="tw-loop-target-hint">{targetSessions.length === 0 ? "(any session)" : `active now: ${(loop?.active_sessions ?? []).join(", ") || "none"}`}</span>
        </div>
        {running && (targetSymbols.length > 0 || targetSessions.length > 0) && (
          <div className="control-field-desc">Changed targeting? Tap <strong>Apply</strong> to push it to the running loop.</div>
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
        Interval is fully yours — anything from 1 second to 24 hours; while it's running, change the
        number and tap “Apply interval.” Very low intervals (a few seconds) hit the market-data feed
        and CPU harder — that's your call, not a cap.
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

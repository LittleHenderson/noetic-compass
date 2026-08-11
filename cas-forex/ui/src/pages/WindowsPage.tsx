/* ── CAS Forex — Trading Windows (2×2 live chart cockpit) ── */

import { useEffect, useRef, useState } from "react";
import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import { SymbolTag } from "../components/SymbolTag";
import { TradingWindow, type WindowRole } from "../components/TradingWindow";
import {
  describeMovementPositionFeed,
  formatMovementPositionAge,
  formatMovementPositionSourceLabel,
  isStaticMovementPosition,
  summarizeMovementSource,
} from "../util/movementSource";
import "./WindowsPage.css";
import {
  fetchChartSymbols,
  fetchForexFuryReplayCandidates,
  fetchMovementStream,
  fetchDispatchLoopStatus,
  startDispatchLoop,
  stopDispatchLoop,
  fetchMt5Account,
  fetchStrategyLeads,
  type DispatchLoopState,
  type Mt5LiveState,
} from "../data/api";
import type { DashboardState, MovementStreamState } from "../types/evidence";

interface WindowsPageProps {
  state: DashboardState;
}

const FALLBACK_SYMBOLS = ["EUR/USD", "XAU/USD", "GBP/USD", "USD/JPY"];
const FALLBACK_TIMEFRAMES = ["M1", "M5", "M15", "H1", "D1"];
const LIVE_DISPATCH_LOOP_CONFIRM_PHRASE = "CONFIRM LIVE DISPATCH LOOP";
const MT5_READ_ONLY_MIRROR_TOOLTIP =
  "MT5 terminal mirror panel: this card shows cached broker account and open-position state from the running MetaTrader 5 terminal. It is observe-only from this panel, but CAS AI and automation still open, close, and manage trades through the MT5 bridge/verifier path for demo or the protected order-dispatch path for real money.";
const MT5_TERMINAL_ALGO_TOOLTIP =
  "MT5 terminal permission only: this reports whether the connected terminal currently allows automated order_send. It does not disable CAS AI execution; it only describes terminal-side MT5 permission for this mirror-connected account.";
const MT5_MIRROR_SCOPE_FALLBACK = "account + open positions from the running MT5 terminal";

export function WindowsPage({ state }: WindowsPageProps) {
  const [symbols, setSymbols] = useState<string[]>(FALLBACK_SYMBOLS);
  const [timeframes, setTimeframes] = useState<string[]>(FALLBACK_TIMEFRAMES);
  const [movement, setMovement] = useState<MovementStreamState | null>(state.movementStream ?? null);
  const [mt5, setMt5] = useState<Mt5LiveState | null>(null);
  const [executionRuntime, setExecutionRuntime] = useState<DispatchLoopState | null>(null);
  const [strategyLeads, setStrategyLeads] = useState<DashboardState["strategyLeads"] | null>(state.strategyLeads ?? null);
  const [furyReplayCandidates, setFuryReplayCandidates] = useState<DashboardState["forexFuryReplayCandidates"] | null>(
    state.forexFuryReplayCandidates ?? null,
  );
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    void fetchChartSymbols().then((s) => {
      if (s && s.symbols.length) setSymbols(s.symbols);
      if (s && s.timeframes.length) setTimeframes(s.timeframes);
    });
  }, []);

  // Poll the account + open-positions feed so the panes behave like a terminal.
  useEffect(() => {
    const load = () => { void fetchMovementStream(true).then((m) => { if (m) setMovement(m); }); };
    load();
    timer.current = setInterval(load, 12_000);
    return () => { if (timer.current) clearInterval(timer.current); };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      const [nextMt5, nextExecution] = await Promise.all([
        fetchMt5Account(),
        fetchDispatchLoopStatus(),
      ]);
      if (cancelled) return;
      if (nextMt5) setMt5(nextMt5);
      if (nextExecution) setExecutionRuntime(nextExecution);
    };
    void load();
    const interval = window.setInterval(() => { void load(); }, 6_000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  useEffect(() => { if (state.strategyLeads) setStrategyLeads(state.strategyLeads); }, [state.strategyLeads]);
  useEffect(() => {
    if (state.forexFuryReplayCandidates) setFuryReplayCandidates(state.forexFuryReplayCandidates);
  }, [state.forexFuryReplayCandidates]);

  useEffect(() => {
    let cancelled = false;
    async function refreshStrategySymbols() {
      const [nextLeads, nextFuryCandidates] = await Promise.all([
        fetchStrategyLeads(),
        fetchForexFuryReplayCandidates(),
      ]);
      if (cancelled) return;
      if (nextLeads) setStrategyLeads(nextLeads);
      if (nextFuryCandidates) setFuryReplayCandidates(nextFuryCandidates);
    }
    void refreshStrategySymbols();
    const interval = window.setInterval(() => { void refreshStrategySymbols(); }, 30_000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  const acct = movement?.account;
  const positions = movement?.positions ?? [];
  const movementTruth = movement?.movement_source_truth ?? movement ?? null;
  const movementSource = summarizeMovementSource(movementTruth);
  const positionFeed = describeMovementPositionFeed(movementTruth, acct?.source);

  // Strategy panes prefer symbols that currently have an OPEN POSITION (so the
  // owner sees a live position sitting on a chart), then top strategy leads /
  // Fury candidates, then sensible index defaults.
  const positionSymbols = positions.map((p) => p.symbol).filter((s) => symbols.includes(s));
  const leadSymbols = (strategyLeads ?? [])
    .flatMap((l) => l.symbols_promoted_for_next_tests ?? [])
    .filter((s) => symbols.includes(s));
  const furySymbols = (furyReplayCandidates?.candidates ?? [])
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

  const positionsSource = positionFeed.label;
  const positionTableTitle = positionFeed.title;
  const usd = (v: number | null | undefined) => (
    typeof v === "number" && Number.isFinite(v)
      ? `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
      : "UNAVAILABLE"
  );
  const signedUsd = (v: number | null | undefined) => (
    typeof v === "number" && Number.isFinite(v)
      ? `${v > 0 ? "+" : v < 0 ? "-" : ""}$${Math.abs(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
      : "UNAVAILABLE"
  );
  const primaryMt5Account = Boolean(
    mt5?.connected
      && executionRuntime?.running
      && executionRuntime?.execution_active
      && String(executionRuntime?.last_bridge_class ?? "").toUpperCase().includes("MT5"),
  );
  const activeBalance = primaryMt5Account ? mt5?.account?.balance_usd : acct?.balance_usd;
  const activeEquity = primaryMt5Account ? mt5?.account?.equity_usd : acct?.equity_usd;
  const activeFloatingPnl = primaryMt5Account ? mt5?.account?.floating_pnl_usd : acct?.floating_pnl_usd;
  const activeGrowth = state.activeAccountTruth?.growth_measurement;
  const activeRealizedGrowth = activeGrowth?.cashflow_adjusted_realized_growth_usd;
  const activeRealizedToday = activeGrowth?.realized_today_usd;
  const activeRealizedMonth = activeGrowth?.realized_month_usd;
  const activeExternalCapital = activeGrowth?.net_external_capital_flow_usd;
  const activeGrowthReconciled = activeGrowth?.account_growth_reconciliation?.reconciled === true;
  const activeMargin = primaryMt5Account ? mt5?.account?.margin_used_usd : acct?.margin_used_usd;
  const activeFreeMargin = primaryMt5Account ? mt5?.account?.free_margin_usd : acct?.free_margin_usd;
  const activeOpenPositions = primaryMt5Account
    ? mt5?.open_position_count ?? mt5?.positions?.length ?? 0
    : acct?.open_position_count ?? positions.length;
  const activeAccountLabel = primaryMt5Account
    ? `MT5 ${mt5?.is_demo ? "DEMO" : "LIVE"}${mt5?.account?.login ? ` #${mt5.account.login}` : ""}`
    : positionsSource;
  const activeMt5Tick = mt5?.market_tick;
  const activeMt5TickNeedsAttention = Boolean(
    primaryMt5Account
      && activeMt5Tick
      && !["FRESH", "NO_OPEN_POSITIONS"].includes(String(activeMt5Tick.status || "")),
  );

  return (
    <div className="windows-page">
      <GlassPanel
        title="Trading Windows"
        subtitle="Primary execution-account totals first; simulator proof rows remain separate"
      >
        <div className="tw-price-source-strip" style={{ marginTop: 0, marginBottom: 8 }}>
          <span className="tw-source-kv">active account truth: <strong>{activeAccountLabel}</strong></span>
          <span className="tw-source-kv">execution bridge: <strong>{executionRuntime?.last_bridge_class ?? "unavailable"}</strong></span>
          <span className="tw-source-kv">lane: <strong>{executionRuntime?.execution_lane ?? "unavailable"}</strong></span>
          <span className="tw-source-kv">growth ledger: <strong>{activeGrowthReconciled ? "RECONCILED" : "UNAVAILABLE"}</strong></span>
          {primaryMt5Account ? (
            <span className="tw-source-kv">MT5 account read: <strong>{formatFreshnessAge(mt5?.snapshot_age_seconds)}</strong></span>
          ) : null}
          {primaryMt5Account && activeMt5Tick ? (
            <span className="tw-source-kv">market tick: <strong>{formatFreshnessAge(activeMt5Tick.last_tick_age_seconds)}</strong></span>
          ) : null}
        </div>
        {/* Primary execution-account header. */}
        <div className="tw-account-bar">
          <AcctStat label="Balance" value={usd(activeBalance)} />
          <AcctStat label="Equity" value={usd(activeEquity)} />
          <AcctStat
            label="Floating P&L"
            value={signedUsd(activeFloatingPnl)}
            tone={(activeFloatingPnl ?? 0) > 0 ? "up" : (activeFloatingPnl ?? 0) < 0 ? "down" : undefined}
          />
          <AcctStat
            label="Realized Growth"
            value={signedUsd(activeRealizedGrowth)}
            tone={(activeRealizedGrowth ?? 0) > 0 ? "up" : (activeRealizedGrowth ?? 0) < 0 ? "down" : undefined}
          />
          <AcctStat
            label="Today"
            value={signedUsd(activeRealizedToday)}
            tone={(activeRealizedToday ?? 0) > 0 ? "up" : (activeRealizedToday ?? 0) < 0 ? "down" : undefined}
          />
          <AcctStat
            label="Month"
            value={signedUsd(activeRealizedMonth)}
            tone={(activeRealizedMonth ?? 0) > 0 ? "up" : (activeRealizedMonth ?? 0) < 0 ? "down" : undefined}
          />
          <AcctStat label="External Capital" value={usd(activeExternalCapital)} />
          <AcctStat label="Open positions" value={`${activeOpenPositions}`} />
          <AcctStat label="Margin / Free" value={`${usd(activeMargin)} / ${usd(activeFreeMargin)}`} />
          <AcctStat label="Mode" value={primaryMt5Account ? (mt5?.is_demo ? "PAPER / MT5 DEMO" : "LIVE MT5") : movement?.mode === "LIVE" ? "LIVE" : "PAPER SIM"} />
        </div>

        {activeMt5TickNeedsAttention ? (
          <div className="tw-source-warning" style={{ marginTop: 8 }}>
            {activeMt5Tick?.detail} Account-read age is {formatFreshnessAge(mt5?.snapshot_age_seconds)};
            {" "}last MT5 tick age is {formatFreshnessAge(activeMt5Tick?.last_tick_age_seconds)}.
            {" "}Floating P&amp;L may remain unchanged until the broker sends a fresh executable tick.
          </div>
        ) : null}

        <MarketStatusStrip />
        <div className="windows-intro">
          Account totals above follow the <strong>{activeAccountLabel}</strong>, the current active execution-account source.
          Chart panes and the table below still use the separately labeled <strong>{positionsSource}</strong> movement stream.
          Simulator balance and P&amp;L are never added to MT5 account totals.
          Manual Buy/Sell sends a 0.01-lot probe through the <strong>gated</strong> dispatch.
          Autonomous Operator entries select an exact broker-valid lot size inside the active risk envelope.
          Pause stops that pane's polling.
        </div>
        <div className="tw-price-source-strip">
          <span className="tw-source-kv">position feed: <strong>{positionsSource}</strong></span>
          <span className="tw-source-kv">price source: <strong>{movementSource.statusLabel}</strong></span>
          <span className="tw-source-kv">provider: <strong>{movementSource.providerLabel}</strong></span>
          <span className="tw-source-kv">provider-backed: <strong>{movementSource.providerBackedCount}</strong></span>
          <span className="tw-source-kv">static fallback: <strong>{movementSource.staticFallbackCount}</strong></span>
          {movementSource.mt5FallbackCount > 0 && (
            <span className="tw-source-kv">mt5 fallback: <strong>{movementSource.mt5FallbackCount}</strong></span>
          )}
        </div>
        {!positionFeed.isLiveBroker && positions.length > 0 ? (
          <div className="tw-source-warning">
            {positionFeed.detail} Use the MetaTrader 5 connected-account panel below for actual demo/live broker positions.
          </div>
        ) : null}

        {/* All open positions — the MT4 "Terminal" trade list (always visible) */}
        <div className="tw-all-positions">
          <div className="tw-all-positions-title">{positionTableTitle} ({positions.length})</div>
          {positions.length > 0 ? (
            <table className="tw-positions-table">
              <thead>
                <tr><th>Symbol</th><th>Source</th><th>Age</th><th>Protection</th><th>Side</th><th>Lots</th><th>Entry</th><th>Now</th><th>SL</th><th>TP</th><th>Floating P&amp;L</th></tr>
              </thead>
              <tbody>
                {positions.map((p) => {
                  const priceSource = p.price_source ?? (p.broker_ticket ? "mt5_live_position" : "paper_route_snapshot:static_simulation");
                  const providerBacked = priceSource.startsWith("provider_snapshot:");
                  const stale = isStaticMovementPosition(p);
                  const sourceLabel = formatMovementPositionSourceLabel(p.position_source_label, p.broker_ticket, priceSource);
                  const sourceTitle = [priceSource, p.stale_reason, p.opened_at ? `opened ${p.opened_at}` : ""].filter(Boolean).join(" | ");
                  const protectedByStop = p.stop_loss != null;
                  return (
                    <tr key={p.row_id}>
                      <td><SymbolTag symbol={p.symbol} size="sm" /></td>
                      <td>
                        <span className={`tw-source-pill ${p.broker_ticket || providerBacked ? "live" : "sim"} ${stale ? "stale" : ""}`} title={sourceTitle}>
                          {sourceLabel}
                        </span>
                      </td>
                      <td className="mono" title={p.opened_at ?? p.stale_reason ?? undefined}>{formatMovementPositionAge(p)}</td>
                      <td><ProtectionPill protectedByStop={protectedByStop} /></td>
                      <td className={p.side === "LONG" ? "tw-long" : "tw-short"}>{p.side}</td>
                      <td className="mono">{p.lot_size}</td>
                      <td className="mono">{p.open_price}</td>
                      <td className="mono">{p.current_price}</td>
                      <td className="mono" style={{ color: "var(--danger)" }}>{p.stop_loss ?? "-"}</td>
                      <td className="mono" style={{ color: "var(--success)" }}>{p.take_profit ?? "-"}</td>
                      <td className="mono" style={{ color: p.floating_pnl_usd > 0 ? "var(--success)" : p.floating_pnl_usd < 0 ? "var(--danger)" : "var(--text-secondary)" }}>
                        {p.floating_pnl_usd >= 0 ? "+" : ""}{p.floating_pnl_usd.toFixed(2)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <div className="tw-muted" style={{ fontSize: "0.8125rem" }}>No open positions right now.</div>
          )}
        </div>
      </GlassPanel>

      <Mt5LiveAccountPanel mt5={mt5} />

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
            positionsDetail={positionFeed.detail}
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

function Mt5LiveAccountPanel({ mt5 }: { mt5: Mt5LiveState | null }) {

  const connected = mt5?.connected ?? false;
  const acc = mt5?.account;
  const positions = mt5?.positions ?? [];
  const usd = (v: number | null | undefined) => `$${(v ?? 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
  const subtitle = mt5AccountSubtitle(mt5);
  const executionNote = mt5ExecutionNote(mt5);
  const readOnlyBoundary = mt5?.claim_boundary ?? MT5_READ_ONLY_MIRROR_TOOLTIP;
  const mirrorScope = mt5?.mirror_scope ?? MT5_MIRROR_SCOPE_FALLBACK;
  const mirrorLabel = mt5?.mirror_label ?? "TERMINAL MIRROR";
  const readOnlyLabel = mt5?.read_only_label ?? "READ-ONLY MIRROR";
  const writesFromPanel = mt5?.writes_from_panel ?? "none from this panel";
  const executionPathNote = mt5?.execution_path_note ?? executionNote;
  const permission = mt5?.permission_state;
  const protection = mt5?.position_protection;
  const positionRisk = mt5?.position_risk;
  const marketTick = mt5?.market_tick;
  const snapshotFresh = mt5?.snapshot_fresh === true;
  const marketTickStatus = String(marketTick?.status || "UNAVAILABLE");
  const marketTickHealthy = marketTickStatus === "FRESH" || marketTickStatus === "NO_OPEN_POSITIONS";
  const riskBreachCount = positionRisk?.risk_cap_breach_count ?? 0;
  const permissionChipVariant = permission?.can_submit_order_send
    ? "success"
    : permission?.status === "PERMISSION_UNKNOWN"
      ? "muted"
      : "warning";
  const protectionChipVariant = protection?.requires_owner_attention
    ? "danger"
    : protection?.status === "POSITION_PROTECTION_UNAVAILABLE"
      ? "warning"
      : "success";

  return (
    <GlassPanel
      title="MetaTrader 5 — Connected Account"
      subtitle={subtitle}
      variant={connected ? "info" : "default"}
    >
      {connected && acc ? (
        <>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10, flexWrap: "wrap" }}>
            <StatusDot on={true} />
            <span style={{ fontWeight: 700, fontSize: "0.875rem" }}>#{acc.login}</span>
            <span className="tw-loop-mode">{acc.server}</span>
            <StatusChip label={mt5?.is_demo ? "DEMO - PAPER / MT5 BRIDGE" : "LIVE MONEY ACCOUNT"} variant={mt5?.is_demo ? "success" : "danger"} size="sm" />
            <StatusChip label={mirrorLabel} variant="info" size="sm" />
            <StatusChip
              label={snapshotFresh ? `ACCOUNT READ ${formatFreshnessAge(mt5?.snapshot_age_seconds).toUpperCase()}` : "ACCOUNT SNAPSHOT STALE"}
              variant={snapshotFresh ? "success" : "warning"}
              size="sm"
            />
            <StatusChip
              label={marketTickHealthy ? (marketTickStatus === "FRESH" ? "MARKET TICKS FRESH" : "NO OPEN TICK WATCH") : marketTickStatus.replace(/_/g, " ")}
              variant={marketTickHealthy ? "success" : "warning"}
              size="sm"
            />
            <span title={readOnlyBoundary} aria-label={readOnlyBoundary}>
              <StatusChip label={readOnlyLabel} variant="muted" size="sm" />
            </span>
            <span title={MT5_TERMINAL_ALGO_TOOLTIP} aria-label={MT5_TERMINAL_ALGO_TOOLTIP}>
              <StatusChip label={mt5?.algo_allowed ? "ALGO ON" : "ALGO OFF"} variant={mt5?.algo_allowed ? "success" : "warning"} size="sm" />
            </span>
            {permission ? (
              <span title={permission.plain_english || MT5_TERMINAL_ALGO_TOOLTIP} aria-label={permission.plain_english || MT5_TERMINAL_ALGO_TOOLTIP}>
                <StatusChip label={permission.permission_label} variant={permissionChipVariant} size="sm" />
              </span>
            ) : null}
            {protection ? (
              <StatusChip
                label={protection.requires_owner_attention ? `UNPROTECTED ${protection.unprotected_position_count}` : "STOPS PROTECTED"}
                variant={protectionChipVariant}
                size="sm"
              />
            ) : null}
            {positionRisk && positions.length > 0 ? (
              <span title={positionRisk.detail} aria-label={positionRisk.detail}>
                <StatusChip
                  label={riskBreachCount > 0 ? `ENTRY RISK > CAP ${riskBreachCount}` : "ENTRY RISK CHECKED"}
                  variant={riskBreachCount > 0 ? "danger" : "info"}
                  size="sm"
                />
              </span>
            ) : null}
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
          <div className="tw-price-source-strip" style={{ marginTop: 0 }}>
            <span className="tw-source-kv">scope: <strong>{mirrorScope}</strong></span>
            <span className="tw-source-kv">writes: <strong>{writesFromPanel}</strong></span>
            <span className="tw-source-kv">execution: <strong>{executionPathNote}</strong></span>
            <span className="tw-source-kv" title={mt5?.snapshot_observed_at ?? undefined}>
              account read: <strong>{formatFreshnessAge(mt5?.snapshot_age_seconds)}</strong>
            </span>
            <span className="tw-source-kv" title={marketTick?.last_tick_observed_at ?? undefined}>
              last market tick: <strong>{formatFreshnessAge(marketTick?.last_tick_age_seconds)}</strong>
            </span>
          </div>
          <div className="tw-source-warning" style={{ marginTop: 8 }}>
            {readOnlyBoundary}
          </div>
          {!snapshotFresh ? (
            <div className="tw-source-warning" style={{ marginTop: 8 }}>
              MT5 account data was last read {formatFreshnessAge(mt5?.snapshot_age_seconds)} at {formatObservedAt(mt5?.snapshot_observed_at)}.
              {" "}Balance, equity, positions, and floating P&amp;L may be stale. Guarded dispatch still requires a fresh broker read before any order action.
            </div>
          ) : !marketTickHealthy && marketTick ? (
            <div className="tw-source-warning" style={{ marginTop: 8 }}>
              {marketTick.detail} The account mirror itself refreshed {formatFreshnessAge(mt5?.snapshot_age_seconds)},
              {" "}but the last open-position market tick was {formatFreshnessAge(marketTick.last_tick_age_seconds)} at {formatObservedAt(marketTick.last_tick_observed_at)}.
              {" "}Floating P&amp;L can remain unchanged while the market is closed or the terminal tick is stale; this does not mean the Operator scheduler is stopped.
            </div>
          ) : null}
          {positionRisk && riskBreachCount > 0 ? (
            <div className="tw-source-warning tw-position-risk-warning" style={{ marginTop: 8 }}>
              {riskBreachCount} open position{riskBreachCount === 1 ? "" : "s"} exceed the current {positionRisk.risk_cap_pct}% per-trade entry-risk cap.
              {" "}The Operator receives this broker-valued evidence for supervision; this comparison alone does not force-close an existing trade.
            </div>
          ) : null}
          <div className="tw-all-positions">
            <div className="tw-all-positions-title">MT5 Open Positions ({positions.length})</div>
            {positions.length > 0 ? (
              <table className="tw-positions-table">
                <thead>
                  <tr><th>Symbol</th><th>Protection</th><th>Side</th><th>Lots</th><th>Open</th><th>Now</th><th>SL</th><th>TP</th><th>Entry risk at SL</th><th>Floating P&amp;L</th></tr>
                </thead>
                <tbody>
                  {positions.map((p) => (
                    <tr key={p.ticket ?? `${p.symbol}-${p.open_price}`}>
                      <td><SymbolTag symbol={p.symbol} size="sm" /></td>
                      <td><ProtectionPill protectedByStop={p.stop_loss != null} /></td>
                      <td className={p.side === "LONG" ? "tw-long" : "tw-short"}>{p.side}</td>
                      <td className="mono">{p.lots}</td>
                      <td className="mono">{p.open_price}</td>
                      <td
                        className="mono"
                        title={`MT5 tick ${formatFreshnessAge(p.market_tick_age_seconds)} | ${String(p.market_tick_status || "UNKNOWN").replace(/_/g, " ")}`}
                      >
                        {p.current_price}
                      </td>
                      <td className="mono" style={{ color: "var(--danger)" }}>{p.stop_loss ?? "-"}</td>
                      <td className="mono" style={{ color: "var(--success)" }}>{p.take_profit ?? "-"}</td>
                      <td
                        className="mono"
                        style={{ color: p.risk_cap_breached ? "var(--danger)" : "var(--text-secondary)" }}
                        title={p.risk_at_stop_usd == null
                          ? "Broker-valued entry-to-stop risk is unavailable."
                          : `Original entry to current stop. Remaining current-equity drawdown to stop: ${usd(p.remaining_to_stop_drawdown_usd)}.`}
                      >
                        {p.risk_at_stop_usd == null
                          ? "-"
                          : p.stop_locked_profit_usd != null && p.stop_locked_profit_usd > 0 && p.risk_at_stop_usd === 0
                            ? `Locks +${usd(p.stop_locked_profit_usd)}`
                            : `${usd(p.risk_at_stop_usd)}${p.risk_at_stop_pct_equity == null ? "" : ` (${p.risk_at_stop_pct_equity.toFixed(3)}%)`}`}
                      </td>
                      <td className="mono" style={{ color: p.floating_pnl_usd > 0 ? "var(--success)" : p.floating_pnl_usd < 0 ? "var(--danger)" : "var(--text-secondary)" }}>
                        {p.floating_pnl_usd >= 0 ? "+" : ""}{p.floating_pnl_usd.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="tw-muted" style={{ fontSize: "0.8125rem" }}>No open positions in MT5 right now.</div>
            )}
          </div>
          <div className="control-field-desc" style={{ marginTop: 8 }} title={readOnlyBoundary}>
            {executionNote}
          </div>
          {protection ? (
            <div className="control-field-desc" style={{ marginTop: 6 }}>
              Position protection: {protection.detail}
            </div>
          ) : null}
          {permission ? (
            <div className="control-field-desc" style={{ marginTop: 6 }}>
              MT5 permissions: terminal algo {formatPermissionFlag(permission.terminal_algo_trading_enabled)}
              {" | "}account trading {formatPermissionFlag(permission.account_trade_allowed)}
              {" | "}expert trading {formatPermissionFlag(permission.account_expert_trading_allowed)}
              {" | "}trade API disabled {formatPermissionFlag(permission.terminal_tradeapi_disabled)}
            </div>
          ) : null}
          {mt5?.note && mt5.note !== executionNote ? (
            <div className="control-field-desc" style={{ marginTop: 6 }}>{mt5.note}</div>
          ) : null}
        </>
      ) : (
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
            <StatusDot on={false} />
            <span style={{ fontWeight: 700, fontSize: "0.875rem" }}>Not connected</span>
            <StatusChip label={mirrorLabel} variant="info" size="sm" />
            <span title={readOnlyBoundary} aria-label={readOnlyBoundary}>
              <StatusChip label={readOnlyLabel} variant="muted" size="sm" />
            </span>
          </div>
          <div className="tw-price-source-strip" style={{ marginTop: 0, marginBottom: 8 }}>
            <span className="tw-source-kv">scope: <strong>{mirrorScope}</strong></span>
            <span className="tw-source-kv">writes: <strong>{writesFromPanel}</strong></span>
            <span className="tw-source-kv">execution: <strong>{executionPathNote}</strong></span>
          </div>
          <div className="control-field-desc">
            {mt5?.detail ?? mt5?.error ?? "Open your MetaTrader 5 terminal, log into your account, and make sure it shows a live connection (ticking prices). This panel will pick it up automatically."}
          </div>
          <div className="control-field-desc" style={{ marginTop: 6 }}>
            {readOnlyBoundary}
          </div>
        </div>
      )}
    </GlassPanel>
  );
}

function mt5AccountSubtitle(mt5: Mt5LiveState | null): string {
  if (!mt5?.connected) {
    return "Terminal mirror - open MT5 to stream account and open positions";
  }
  if (mt5.is_demo) {
    return "Live terminal mirror - demo/paper account; AI execution runs through the MT5 bridge";
  }
  return "Live terminal mirror - real-money account; AI execution runs through guarded live authority";
}

function mt5ExecutionNote(mt5: Mt5LiveState | null): string {
  if (!mt5?.connected) {
    return "This panel mirrors the MT5 terminal once the local API can reach it.";
  }
  const permissionText = mt5.permission_state?.plain_english;
  if (mt5.is_demo) {
    const routeText =
      "This panel is observe-only from here; CAS AI and automation still place and manage paper/demo trades through the MT5 bridge/verifier path.";
    if (permissionText) return `${permissionText} ${routeText}`;
    return mt5.algo_allowed
      ? "This is a demo/paper MT5 account with Algo Trading on. The panel is observe-only from here; CAS AI and automation still place and manage paper/demo trades through the MT5 bridge/verifier path."
      : "This is a demo/paper MT5 account, but Algo Trading is off in the terminal. Turn Algo Trading on before expecting the MT5 bridge/verifier to submit demo orders.";
  }
  const routeText =
    "This panel is observe-only from here; CAS AI and automation still place and manage real-money trades through the protected order-dispatch path once owner live authority is armed.";
  if (permissionText) return `${permissionText} ${routeText}`;
  return mt5.algo_allowed
    ? "This is a real-money MT5 account with Algo Trading on. The panel is observe-only from here; CAS AI and automation still place and manage real-money trades through the protected order-dispatch path once owner live authority is armed."
    : "This is a real-money MT5 account, and Algo Trading is off in the terminal. No automated MT5 order_send can run until terminal Algo Trading is enabled and owner live authority is armed.";
}

function formatPermissionFlag(value: boolean | null | undefined): string {
  if (value === true) return "ON";
  if (value === false) return "OFF";
  return "UNKNOWN";
}

function formatFreshnessAge(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "unavailable";
  const seconds = Math.max(0, value);
  if (seconds < 1) return "<1s ago";
  if (seconds < 60) return `${Math.round(seconds)}s ago`;
  const minutes = seconds / 60;
  if (minutes < 60) return `${Math.round(minutes)}m ago`;
  const hours = minutes / 60;
  if (hours < 48) return `${hours.toFixed(hours < 10 ? 1 : 0)}h ago`;
  return `${(hours / 24).toFixed(1)}d ago`;
}

function formatObservedAt(value: string | null | undefined): string {
  if (!value) return "an unavailable time";
  const observed = new Date(value);
  if (Number.isNaN(observed.getTime())) return value;
  return observed.toLocaleString();
}

function ProtectionPill({ protectedByStop }: { protectedByStop: boolean }) {
  return (
    <span className={`tw-protection-pill ${protectedByStop ? "protected" : "unprotected"}`}>
      {protectedByStop ? "Protected" : "Unprotected"}
    </span>
  );
}

const LOOP_SESSIONS = ["Asian", "London", "New York"];

function formatDispatchLoopLastError(lastError?: string | null): string | null {
  const raw = String(lastError ?? "").trim();
  if (!raw) return null;
  const rawLower = raw.toLowerCase();
  if (
    rawLower.includes("live_trading is currently not licensed")
    || rawLower.includes("pending owner enable")
  ) {
    return "Live mode is requested, but the live runtime gates are not ready. The timer may stay armed, but it will not collect or dispatch intents until those gates pass.";
  }
  if (rawLower.includes("permissionerror")) {
    return "Dispatch blocked by an owner or broker gate. No broker order was sent; review the gate panel before enabling live dispatch.";
  }
  return `Loop cycle warning: ${raw}`;
}

function AutoTradeLoopBar({ symbols }: { symbols: string[] }) {
  const [loop, setLoop] = useState<DispatchLoopState | null>(null);
  const [interval, setIntervalSec] = useState(60);
  const [targetSymbols, setTargetSymbols] = useState<string[]>([]);
  const [targetSessions, setTargetSessions] = useState<string[]>([]);
  const [positionScope, setPositionScope] = useState<"CAS_ONLY" | "ALL_ACCOUNT">("CAS_ONLY");
  const [, setSynced] = useState(false);
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
            const reportedInterval = Number(s.interval_seconds);
            if (Number.isFinite(reportedInterval)) {
              setIntervalSec(Math.max(1, Math.min(86400, Math.round(reportedInterval))));
            }
            setTargetSymbols(s.symbols ?? []);
            setTargetSessions(s.sessions ?? []);
            setPositionScope(s.position_scope === "ALL_ACCOUNT" ? "ALL_ACCOUNT" : "CAS_ONLY");
          }
          return true;
        });
      });
    };
    load();
    poll.current = setInterval(load, 5000);
    return () => { if (poll.current) clearInterval(poll.current); };
  }, []);

  const body = () => ({
    interval_seconds: interval,
    symbols: targetSymbols,
    sessions: targetSessions,
    position_scope: positionScope,
    change_reason: "owner UI updated interval, symbol/session targeting, or position scope",
  });

  async function start() {
    setBusy(true); setMsg("");
    try {
      const s = await startDispatchLoop(body());
      if (s.status === "CONFIRM_REQUIRED") {
        setMsg(`Live mode is requested. Type exactly "${s.need_confirmation ?? LIVE_DISPATCH_LOOP_CONFIRM_PHRASE}" to grant standing timer authority; PAPER remains the active lane until every live gate passes.`);
      }
      setLoop(s);
    } catch { setMsg("Couldn't start the loop — is the API reachable?"); }
    finally { setBusy(false); }
  }
  async function startLiveConfirmed() {
    setBusy(true); setMsg("");
    const typed = window.prompt(`Type exactly "${LIVE_DISPATCH_LOOP_CONFIRM_PHRASE}" to start the autonomous loop. PAPER stays active until LIVE is fully authorized.`, "");
    if (typed === null) {
      setMsg("Live loop confirmation canceled.");
      setBusy(false);
      return;
    }
    try {
      const s = await startDispatchLoop(body(), true, typed);
      if (s.status === "CONFIRM_REQUIRED") setMsg(`Type exactly "${s.need_confirmation ?? LIVE_DISPATCH_LOOP_CONFIRM_PHRASE}" to start the live loop.`);
      setLoop(s);
    }
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
    const liveSettings = loop?.requested_mode === "LIVE" || loop?.mode === "LIVE" || loop?.mode === "LIVE_BLOCKED" || loop?.mode === "PAPER_FALLBACK";
    let typed = "";
    if (liveSettings) {
      const entered = window.prompt(`Type exactly "${LIVE_DISPATCH_LOOP_CONFIRM_PHRASE}" to apply live loop settings.`, "");
      if (entered === null) {
        setMsg("Live loop settings confirmation canceled.");
        setBusy(false);
        return;
      }
      typed = entered;
    }
    try {
      const s = await startDispatchLoop(body(), liveSettings, typed);
      setLoop(s);
      setMsg(s.status === "CONFIRM_REQUIRED" ? `Type exactly "${s.need_confirmation ?? LIVE_DISPATCH_LOOP_CONFIRM_PHRASE}" to apply live loop settings.` : "Applied - takes effect on the next cycle.");
    }
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
  const liveBlocked = loop?.status === "LIVE_BLOCKED" || loop?.mode === "LIVE_BLOCKED";
  const paperFallback = Boolean(loop?.paper_fallback_active) || loop?.mode === "PAPER_FALLBACK";
  const livePending = liveBlocked || paperFallback;
  const executionActive = loop?.execution_active ?? (running && !liveBlocked);
  const needsLiveConfirm = loop?.status === "CONFIRM_REQUIRED" || loop?.requested_mode === "LIVE";
  const loopLastError = formatDispatchLoopLastError(loop?.last_error);

  return (
    <GlassPanel
      title="Auto-Trade Loop"
      subtitle="Autonomous entries, exact lot sizing, protected-winner scale-ins, take-profit, stop, reduction, and exits"
      variant={executionActive ? "info" : "default"}
    >
      <div className="tw-loop-bar">
        <div className="tw-loop-status">
          <StatusDot on={executionActive} />
          <span className="tw-loop-state">{liveBlocked ? "ARMED / BLOCKED" : running ? "RUNNING" : "STOPPED"}</span>
          <span className="tw-loop-mode">
            {paperFallback ? "PAPER ACTIVE / LIVE PENDING" : liveBlocked ? "LIVE PENDING" : loop?.mode === "LIVE" ? "LIVE" : "PAPER / DEMO"}
          </span>
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
          <button className="tw-btn tw-sell" disabled={busy} onClick={() => void startLiveConfirmed()}>Start autonomous loop</button>
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
          <span className="tw-loop-target-hint">{targetSymbols.length === 0 ? "(AI symbol dial decides)" : `${targetSymbols.length} selected`}</span>
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
        <div className="tw-loop-target-row">
          <span className="tw-loop-target-label">Manage positions</span>
          <div className="tw-loop-chips" role="group" aria-label="Autonomous position management scope">
            <button
              type="button"
              className={`tw-loop-chip ${positionScope === "CAS_ONLY" ? "on" : ""}`}
              title="Manage positions opened and tagged by CAS Forex"
              onClick={() => setPositionScope("CAS_ONLY")}
            >CAS trades</button>
            <button
              type="button"
              className={`tw-loop-chip ${positionScope === "ALL_ACCOUNT" ? "on" : ""}`}
              title="Manage every open position, including manual and outside-CAS trades"
              onClick={() => setPositionScope("ALL_ACCOUNT")}
            >Entire account</button>
          </div>
          <span className="tw-loop-target-hint">
            {positionScope === "CAS_ONLY" ? "manual trades excluded" : "manual trades included"}
          </span>
        </div>
        {running && (
          <div className="control-field-desc">Changed targeting or management scope? Tap <strong>Apply</strong> to push it to the running loop.</div>
        )}
      </div>
      <div className="tw-loop-detail">
        {loop?.cycles_run != null && <span>cycles run: <strong>{loop.cycles_run}</strong></span>}
        {loop?.management_cycles_run != null && (
          <span>management checks: <strong>{loop.management_cycles_run}</strong></span>
        )}
        {loop?.last_management_status && (
          <span>
            AI management: <strong>{loop.last_management_status}</strong>
            {` · attempted ${loop.last_management_action_count ?? 0}`}
            {` · terminal effects ${loop.last_management_terminal_effect_count ?? 0}`}
          </span>
        )}
        {loop?.position_scope && (
          <span>
            position scope: <strong>{loop.position_scope}</strong>
            {` · account ${loop.last_management_account_position_count ?? 0}`}
            {` · excluded ${loop.last_management_excluded_position_count ?? 0}`}
          </span>
        )}
        {loop?.last_management_detail && <span>{loop.last_management_detail}</span>}
        {loop?.last_symbol_targeting_status && (
          <span>
            entry scan: <strong>{loop.last_symbol_targeting_status}</strong>
            {` · eligible ${(loop.last_eligible_entry_symbols ?? []).length}`}
            {` · saturated ${(loop.last_saturated_entry_symbols ?? []).join(", ") || "none"}`}
          </span>
        )}
        {loop?.last_symbol_targeting?.detail && <span>{loop.last_symbol_targeting.detail}</span>}
        {loop?.control_revision && (
          <span>
            targeting control: <strong>r{loop.control_revision}</strong>
            {` · ${loop.control_updated_by ?? "unknown"}`}
            {` · ${loop.control_change_reason ?? "no reason"}`}
          </span>
        )}
        {loop?.last_bridge_selection_status && (
          <span>
            execution bridge: <strong>{loop.last_bridge_class ?? "unknown"}</strong>
            {` / ${loop.last_bridge_selection_status}`}
          </span>
        )}
        {loop?.last_bridge_selection_detail && <span>{loop.last_bridge_selection_detail}</span>}
        {loop?.last_summary && <span>last: <strong>{loop.last_summary}</strong></span>}
        {liveBlocked && loop?.last_blocking_detail && <span className="tw-loop-warning">{loop.last_blocking_detail}</span>}
        {livePending && !liveBlocked && loop?.live_blocking_detail && <span className="tw-loop-warning">Live pending only: {loop.live_blocking_detail}</span>}
        {loopLastError && <span className="tw-loop-warning">{loopLastError}</span>}
      </div>
      {msg && <div className="control-field-desc" style={{ color: needsLiveConfirm ? "var(--danger)" : "var(--text-secondary)" }}>{msg}</div>}
      <div className="control-field-desc">
        Every active timer cycle reviews current broker positions first. It can autonomously install a missing
        protective stop, set or extend take-profit, bank partial profit, move or trail a stop, reduce exposure,
        and fully close invalidated or stale losing positions through the execution guard, then evaluates new
        entries through the same guarded dispatch path as manual Buy/Sell. Entry-session filters never turn
        off management of an already-open position. CAS trades excludes manual positions; Entire account
        deliberately includes them. PAPER / DEMO uses the selected paper lane. When LIVE is requested but
        not yet authorized, PAPER remains active and keeps learning through an execution-capable demo bridge
        or the clearly labeled internal simulator; the paper lane never touches a live account. LIVE re-checks risk,
        broker truth, terminal state, and duplicate-action evidence at action time.
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

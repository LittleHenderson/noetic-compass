/* â”€â”€ CAS Forex - Paper Trading Desk â”€â”€ */

import { useEffect, useState } from "react";
import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import { CandlestickChart } from "../components/charts/CandlestickChart";
import { MultiTimeframeSelector } from "../components/MultiTimeframeSelector";
import { LiveTradesTelemetry } from "../components/LiveTradesTelemetry";
import { MoneyMovementSetupStatus } from "../components/MoneyMovementSetupStatus";
import { PortfolioRiskCard } from "../components/PortfolioRiskCard";
import { PsychologyGuardPanel } from "../components/PsychologyGuardPanel";
import { AgentDecisionCard } from "../components/AgentDecisionCard";
import { AutonomousLoopCard } from "../components/AutonomousLoopCard";
import { CONVICTION_SCORE_TITLE, formatConvictionScore } from "../util/conviction";
import {
  formatMovementPositionAge,
  formatMovementPositionSourceLabel,
  isStaticMovementQuote,
  summarizeMovementSource,
} from "../util/movementSource";
import {
  fetchAuthorization,
  fetchLiveMoneyProgressionPacket,
  fetchMovementStream,
  fetchWastePaperSampleCollectorScheduler,
  startWasteLoop,
  startWastePaperSampleCollectorScheduler,
  updateAuthorization,
  type AuthorizationPatch,
  type AuthorizationState,
  type LiveMoneyProgressionPacket,
} from "../data/api";
import type { DashboardState, MovementStreamState, SymbolDecision, SizingEntry } from "../types/evidence";
import "../components/RoutePrimitives.css";
import "../components/SelectorChips.css";
import "./TradePage.css";

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

const LIVE_MONEY_POST_WRITE_RETRY_DELAYS_MS = [1_500, 4_000, 8_000] as const;
const REAL_MONEY_ARM_CONFIRM_PHRASE = "ARM REAL MONEY";
const PAYMENT_PROVIDER_LIVE_CONFIRM_PHRASE = "ARM PAYMENT PROVIDER LIVE";
const LIVE_WASTE_LOOP_CONFIRM_PHRASE = "CONFIRM LIVE WASTE LOOP";

function isLiveMoneyProgressionWarming(packet: LiveMoneyProgressionPacket | null | undefined): boolean {
  return packet?.status === "WARMING" || packet?.cache_status === "warming" || packet?.cache_refreshing === true;
}

function realMoneyConfirmRequired(payload: { need_confirmation?: string | null }): string {
  return `Type exactly "${payload.need_confirmation ?? REAL_MONEY_ARM_CONFIRM_PHRASE}" to arm these live-money authority switches.`;
}

export function TradePage({ state }: TradePageProps) {
  const { dailyBundle: b } = state;
  const decision = b.latest_decision.latest_decision;

  const [symbol, setSymbol] = useState<Symbol>("NAS100");
  const [timeframe, setTimeframe] = useState<Timeframe>("D1");
  const [style, setStyle] = useState<Style>("swing");
  const [actionBusy, setActionBusy] = useState<"proposal" | "paper-loop" | "">("");
  const [actionStatus, setActionStatus] = useState("");
  const [liveMovement, setLiveMovement] = useState<MovementStreamState | null>(state.movementStream ?? null);
  const [liveSampleScheduler, setLiveSampleScheduler] = useState(state.wastePaperSampleCollectorScheduler ?? null);
  const [tradeAuth, setTradeAuth] = useState<AuthorizationState | null>(null);
  const [liveProgression, setLiveProgression] = useState<LiveMoneyProgressionPacket | null>(state.liveMoneyProgression ?? null);
  const [authBusy, setAuthBusy] = useState("");
  const [authStatus, setAuthStatus] = useState("");
  const [paymentProvider, setPaymentProvider] = useState("");
  const [paymentProviderEnvironment, setPaymentProviderEnvironment] = useState("sandbox");
  const [paymentApiKey, setPaymentApiKey] = useState("");
  const [paymentProviderBaseUrl, setPaymentProviderBaseUrl] = useState("");
  const [paymentProviderAccountId, setPaymentProviderAccountId] = useState("");
  const [payoutDestination, setPayoutDestination] = useState("");
  const movement = liveMovement ?? state.movementStream ?? null;
  const movementTruth = movement?.movement_source_truth ?? movement ?? null;
  const movementSource = summarizeMovementSource(movementTruth);

  async function refreshLiveMoneyProgression(refresh = false): Promise<LiveMoneyProgressionPacket | null> {
    const next = await fetchLiveMoneyProgressionPacket(refresh);
    if (next) setLiveProgression(next);
    return next;
  }

  function scheduleLiveMoneyProgressionRetries() {
    LIVE_MONEY_POST_WRITE_RETRY_DELAYS_MS.forEach((delayMs) => {
      window.setTimeout(() => {
        void refreshLiveMoneyProgression(false);
      }, delayMs);
    });
  }

  async function refreshLiveMoneyProgressionAfterWrite() {
    const next = await refreshLiveMoneyProgression(true);
    if (isLiveMoneyProgressionWarming(next)) scheduleLiveMoneyProgressionRetries();
  }

  useEffect(() => {
    if (state.movementStream) setLiveMovement(state.movementStream);
  }, [state.movementStream]);

  useEffect(() => {
    let cancelled = false;
    async function loadMovement() {
      const next = await fetchMovementStream(true);
      if (!cancelled && next) setLiveMovement(next);
    }
    void loadMovement();
    const intervalId = window.setInterval(() => void loadMovement(), 5_000);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  useEffect(() => {
    setLiveSampleScheduler(state.wastePaperSampleCollectorScheduler ?? null);
  }, [state.wastePaperSampleCollectorScheduler]);

  useEffect(() => {
    let cancelled = false;
    async function loadScheduler() {
      const next = await fetchWastePaperSampleCollectorScheduler();
      if (!cancelled && next) setLiveSampleScheduler(next);
    }
    void loadScheduler();
    const intervalId = window.setInterval(() => void loadScheduler(), 10_000);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    let hydrated = Boolean(tradeAuth);
    let quickRetryId: number | undefined;
    async function loadAuth(initial = false) {
      const next = await fetchAuthorization();
      if (cancelled || !next) return;
      hydrated = true;
      setTradeAuth(next);
      if (initial) {
        setPaymentProvider(next.provider.payment_provider ?? "");
        setPaymentProviderEnvironment(next.provider.payment_provider_environment ?? "sandbox");
        setPaymentProviderBaseUrl(next.provider.payment_provider_base_url ?? "");
        setPaymentProviderAccountId(next.provider.payment_provider_account_id ?? "");
        setPayoutDestination(next.provider.payout_destination_id ?? "");
      }
    }
    void loadAuth(true);
    quickRetryId = window.setInterval(() => {
      if (!hydrated) void loadAuth(false);
    }, 5_000);
    const intervalId = window.setInterval(() => void loadAuth(false), 30_000);
    return () => {
      cancelled = true;
      if (quickRetryId !== undefined) window.clearInterval(quickRetryId);
      window.clearInterval(intervalId);
    };
  }, []);

  useEffect(() => {
    if (state.liveMoneyProgression) setLiveProgression(state.liveMoneyProgression);
  }, [state.liveMoneyProgression]);

  useEffect(() => {
    let cancelled = false;
    let hydrated = Boolean(liveProgression);
    let latestStatus = liveProgression?.status ?? "";
    let quickRetryId: number | undefined;
    async function loadProgression() {
      const next = await fetchLiveMoneyProgressionPacket();
      if (cancelled || !next) return;
      hydrated = true;
      latestStatus = next.status ?? "";
      setLiveProgression(next);
    }
    void loadProgression();
    quickRetryId = window.setInterval(() => {
      if (!hydrated || latestStatus === "WARMING") void loadProgression();
    }, 5_000);
    const intervalId = window.setInterval(() => void loadProgression(), 30_000);
    return () => {
      cancelled = true;
      if (quickRetryId !== undefined) window.clearInterval(quickRetryId);
      window.clearInterval(intervalId);
    };
  }, []);

  const activeDecision: SymbolDecision | undefined =
    decision.symbol_decisions.find((d) => d.symbol === symbol);

  const activeSizing: SizingEntry | undefined =
    b.latest_risk.latest_review.sizing.find((s) => s.symbol === symbol);
  const activeQuote = movement?.quotes.find((q) => q.symbol === symbol);
  const activePosition = movement?.positions.find((p) => p.symbol === symbol);
  const activeQuoteIsStatic = isStaticMovementQuote(activeQuote, activePosition);
  const activePositionSourceLabel = activePosition
    ? formatMovementPositionSourceLabel(
        activePosition.position_source_label,
        activePosition.broker_ticket,
        activePosition.price_source,
      )
    : "-";
  const activePositionTicket = activePosition
    ? activePosition.broker_ticket || activePosition.simulator_ticket || "-"
    : "-";
  const candlePreview = activeDecision
    ? buildProposalCandles(
        activeDecision.proposal.entry_price,
        activeDecision.proposal.stop_loss,
        activeDecision.proposal.take_profit,
      )
    : [];
  const sampleScheduler = liveSampleScheduler ?? state.wastePaperSampleCollectorScheduler;
  const sampleRequest = {
    interval_seconds: 300,
    run_market_diagnostic: true,
    run_real_candle_probe: true,
    run_deal_history_ingest: true,
    symbol: normalizeSymbolForRuntime(symbol),
    timeframe,
    bars: 180,
    max_pairs: 80,
    scan_candidates: true,
    max_scan_candidates: 8,
  };

  async function runPaperProposal() {
    setActionBusy("proposal");
    setActionStatus("");
    try {
      const packet = await startWastePaperSampleCollectorScheduler(sampleRequest);
      setLiveSampleScheduler(packet);
      setActionStatus(
        `Probe scheduler running: ${packet.latest_collector_status ?? packet.status}. ` +
          `confirmed=${packet.confirmed_direction_count}, bound=${packet.bound_outcome_count}/${packet.bound_outcomes_needed}.`,
      );
    } catch {
      setActionStatus("Probe scheduler could not start. Check that the API and MT5 connector are reachable.");
    } finally {
      setActionBusy("");
    }
  }

  async function startPaperLoop() {
    setActionBusy("paper-loop");
    setActionStatus("");
    try {
      let loop = await startWasteLoop(5);
      if (loop.status === "CONFIRM_REQUIRED") {
        const need = loop.need_confirmation ?? LIVE_WASTE_LOOP_CONFIRM_PHRASE;
        const typed = window.prompt(`Type exactly "${need}" to start the live WASTE loop.`, "");
        if (typed === null) {
          setActionStatus("WASTE loop confirmation canceled; sampler not started.");
          return;
        }
        loop = await startWasteLoop(5, true, typed);
        if (loop.status === "CONFIRM_REQUIRED") {
          setActionStatus(`Type exactly "${loop.need_confirmation ?? LIVE_WASTE_LOOP_CONFIRM_PHRASE}" to start the live WASTE loop.`);
          return;
        }
      }
      const scheduler = await startWastePaperSampleCollectorScheduler(sampleRequest);
      setLiveSampleScheduler(scheduler);
      setActionStatus(
        `PAPER loop ${loop.running ? "running" : "reported"} at ${loop.interval_seconds ?? 5}s; ` +
          `sample scheduler ${scheduler.running ? "running" : "reported"} with ${scheduler.cycles_run} cycle(s).`,
      );
    } catch {
      setActionStatus("Paper loop could not start. If a stale supervisor lease exists, use Dashboard recovery, then retry.");
    } finally {
      setActionBusy("");
    }
  }

  async function saveTradeProvider() {
    setAuthBusy("provider");
    setAuthStatus("");
    try {
      const patch: AuthorizationPatch = {
        payment_provider: paymentProvider.trim(),
        payment_provider_environment: paymentProviderEnvironment,
        payment_provider_base_url: paymentProviderBaseUrl.trim(),
        payment_provider_account_id: paymentProviderAccountId.trim(),
        payout_destination_id: payoutDestination.trim(),
      };
      if (paymentApiKey.trim()) patch.payment_api_key = paymentApiKey.trim();
      if (paymentProviderEnvironment === "live") {
        const confirm = window.prompt(
          `Type exactly "${PAYMENT_PROVIDER_LIVE_CONFIRM_PHRASE}" to mark this middleware as live.`,
          "",
        );
        if (confirm == null) {
          setAuthStatus("Owner confirmation canceled; provider environment was not changed.");
          return;
        }
        patch.confirm = confirm;
      }
      const next = await updateAuthorization(patch);
      if (next.status === "CONFIRM_REQUIRED") {
        setAuthStatus(realMoneyConfirmRequired(next));
        return;
      }
      setTradeAuth(next);
      await refreshLiveMoneyProgressionAfterWrite();
      setPaymentProvider(next.provider.payment_provider ?? "");
      setPaymentProviderEnvironment(next.provider.payment_provider_environment ?? "sandbox");
      setPaymentProviderBaseUrl(next.provider.payment_provider_base_url ?? "");
      setPaymentProviderAccountId(next.provider.payment_provider_account_id ?? "");
      setPayoutDestination(next.provider.payout_destination_id ?? "");
      setPaymentApiKey("");
      setAuthStatus(
        "Provider configuration saved. Withdrawals and payouts stay scaffolded until the runtime rail, owner gate, allowlist, and receipt checks are all ready.",
      );
    } catch {
      setAuthStatus(
        "Provider settings were not saved. Withdrawal and payout configuration remains unchanged; check API reachability and retry.",
      );
    } finally {
      setAuthBusy("");
    }
  }

  async function turnTradeOwnerSwitchesOn() {
    setAuthBusy("all");
    setAuthStatus("");
    try {
      const patch: AuthorizationPatch = {
        personal_account_ack: true,
        no_pooled_capital_ack: true,
        live_mode: true,
        prefer_mt5: true,
        owner_enable_live_trading: true,
        live_trading_licensed: true,
        owner_enable_broker_accept: true,
        owner_enable_auto_deposit: true,
        owner_enable_bank_card_movement: true,
        owner_enable_payout_automation: true,
        payment_provider: paymentProvider.trim(),
        payment_provider_environment: paymentProviderEnvironment,
        payment_provider_base_url: paymentProviderBaseUrl.trim(),
        payment_provider_account_id: paymentProviderAccountId.trim(),
        payout_destination_id: payoutDestination.trim(),
      };
      if (payoutDestination.trim()) patch.payout_destination_allowlisted = true;
      if (paymentApiKey.trim()) patch.payment_api_key = paymentApiKey.trim();
      const confirm = window.prompt(`Type exactly "${REAL_MONEY_ARM_CONFIRM_PHRASE}" to arm these live-money authority switches.`, "");
      if (confirm == null) {
        setAuthStatus("Owner confirmation canceled; no switches changed.");
        return;
      }
      patch.confirm = confirm;
      const next = await updateAuthorization(patch);
      if (next.status === "CONFIRM_REQUIRED") {
        setAuthStatus(realMoneyConfirmRequired(next));
        return;
      }
      setTradeAuth(next);
      await refreshLiveMoneyProgressionAfterWrite();
      setPaymentProvider(next.provider.payment_provider ?? "");
      setPaymentProviderEnvironment(next.provider.payment_provider_environment ?? "sandbox");
      setPaymentProviderBaseUrl(next.provider.payment_provider_base_url ?? "");
      setPaymentProviderAccountId(next.provider.payment_provider_account_id ?? "");
      setPayoutDestination(next.provider.payout_destination_id ?? "");
      setPaymentApiKey("");
      setAuthStatus(
        "Owner authority switches saved. Real money still depends on broker credentials, edge authorization, a supported real provider rail, allowlist, receipts, and action-time risk checks.",
      );
    } catch {
      setAuthStatus(
        "Owner switch save failed. Live, broker, and payment authority remains at its prior state; no live-money controls were changed.",
      );
    } finally {
      setAuthBusy("");
    }
  }

  const liveCap = findCapability(tradeAuth, "live_trading");
  const brokerCap = findCapability(tradeAuth, "broker_accept");
  const payoutCap = findCapability(tradeAuth, "payout_automation");
  const progressionBlockers = liveProgression?.blockers ?? [];
  const firstBlockers = progressionBlockers.slice(0, 6);
  const liveIntent = liveProgression?.active_waste_intent;
  const liveIntentLabel = [liveIntent?.symbol, liveIntent?.direction].filter(Boolean).join(" ") || "none";
  const moneyMovementReady = Boolean(tradeAuth?.all_real_money_authorized && tradeAuth?.provider.real_money_provider_ready);

  return (
    <div className="trade-page">
      {/* â”€â”€ Selectors â”€â”€ */}
      <GlassPanel title="Paper Trading Desk" subtitle="WASTE paper/demo proof desk - PASS-gated backend execution">
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

      {/* â”€â”€ Multi-timeframe runtime selector (MTF runtime / risk aggregation) â”€â”€ */}
      <MultiTimeframeSelector symbol={normalizeSymbolForRuntime(symbol)} />

      {/* â”€â”€ Agent decision + autonomous-loop pulse (observational) â”€â”€ */}
      <div className="trade-grid-2col">
        <AgentDecisionCard />
        <AutonomousLoopCard />
      </div>

      {/* â”€â”€ Portfolio Risk (observational shape, polled every 30s) â”€â”€ */}
      <PortfolioRiskCard />

      {/* â”€â”€ Live Trades Telemetry (observational, polled every 2s) â”€â”€ */}
      <LiveTradesTelemetry />

      <PsychologyGuardPanel />

      <GlassPanel
        title="Owner Authorization & Payout Setup"
        subtitle={tradeAuth?.summary ?? "Owner-controlled live/payment gates"}
        variant={moneyMovementReady ? "default" : "warning"}
      >
        <div className="dashboard-grid-3col">
          <AuthStatusCard title="Live Trading" capability={liveCap} />
          <AuthStatusCard title="Broker ACCEPT" capability={brokerCap} />
          <AuthStatusCard title="Payout Automation" capability={payoutCap} />
        </div>
        <div className="control-field-desc" style={{ marginTop: 10 }}>
          This panel saves owner switches and broker-bound provider setup only. Stripe alone is not an MT5/Hugo's Way custody rail, and unsupported provider labels stay simulated at runtime.
        </div>
        <MoneyMovementSetupStatus
          auth={tradeAuth}
          receiptVerified={Boolean(liveProgression?.verified_payout_clear)}
          receiptStatusLabel={liveProgression?.verified_payout_clear ? "CLEAR" : "REQUIRED"}
          receiptDetail={
            liveProgression?.verified_payout_clear
              ? "The live-money progression lane reports the payout/receipt lane clear."
              : "The live-money progression lane still needs verified payout and receipt evidence."
          }
        />
        <div className="dashboard-grid-3col" style={{ marginTop: 10 }}>
          <div className="control-field">
            <span className="field-label">Payment provider</span>
            <input
              className="mobile-api-input"
              value={paymentProvider}
              placeholder="broker_webhook or simulated"
              onChange={(event) => { setPaymentProvider(event.target.value); setAuthStatus(""); }}
            />
          </div>
          <div className="control-field">
            <span className="field-label">Provider environment</span>
            <select
              className="mobile-api-input"
              value={paymentProviderEnvironment}
              onChange={(event) => { setPaymentProviderEnvironment(event.target.value); setAuthStatus(""); }}
            >
              <option value="sandbox">Sandbox contract test</option>
              <option value="live">Live broker middleware</option>
            </select>
            <div className="control-field-desc">Sandbox can prove the contract but cannot claim or authorize real movement.</div>
          </div>
          <div className="control-field">
            <span className="field-label">Provider API key/token{tradeAuth?.provider.payment_api_key_set ? " - set" : ""}</span>
            <input
              className="mobile-api-input"
              type="password"
              value={paymentApiKey}
              placeholder={tradeAuth?.provider.payment_api_key_set ? "leave blank to keep current key" : "provider API key/token"}
              autoComplete="off"
              onChange={(event) => { setPaymentApiKey(event.target.value); setAuthStatus(""); }}
            />
            <div className="control-field-desc">Provider tokens only, saved as a local encrypted runtime envelope; no raw bank or card numbers are stored here.</div>
          </div>
          <div className="control-field">
            <span className="field-label">Payout destination token</span>
            <input
              className="mobile-api-input"
              value={payoutDestination}
              placeholder="allowlisted payout destination id"
              onChange={(event) => { setPayoutDestination(event.target.value); setAuthStatus(""); }}
            />
          </div>
        </div>
        <div className="dashboard-grid-3col" style={{ marginTop: 10 }}>
          <div className="control-field">
            <span className="field-label">Broker funding middleware URL</span>
            <input
              className="mobile-api-input"
              value={paymentProviderBaseUrl}
              placeholder="https://funding.your-domain.example"
              onChange={(event) => { setPaymentProviderBaseUrl(event.target.value); setAuthStatus(""); }}
            />
          </div>
          <div className="control-field">
            <span className="field-label">Bound broker account ID</span>
            <input
              className="mobile-api-input"
              value={paymentProviderAccountId}
              placeholder="provider-side broker account id"
              onChange={(event) => { setPaymentProviderAccountId(event.target.value); setAuthStatus(""); }}
            />
          </div>
          <div className="control-field">
            <span className="field-label">Custody binding</span>
            <div className="control-field-desc">
              {tradeAuth?.provider.broker_account_bound
                ? `Bound: ${tradeAuth.provider.custody_scope ?? "configured broker account"}`
                : "Not broker-bound"}
            </div>
          </div>
        </div>
        <div className="mobile-api-row" style={{ marginTop: 10 }}>
          <button className="mobile-api-button" type="button" disabled={authBusy === "provider"} onClick={() => void saveTradeProvider()}>
            {authBusy === "provider" ? "SAVING..." : "SAVE PROVIDER / DESTINATION"}
          </button>
          <button className="mobile-api-button" type="button" disabled={authBusy === "all"} onClick={() => void turnTradeOwnerSwitchesOn()}>
            {authBusy === "all" ? "SAVING..." : "TURN OWNER SWITCHES ON"}
          </button>
          <a className="sweep-action-button setup-link" href="?page=proof">FULL PROOF CONTROLS</a>
        </div>
        {authStatus && (
          <div className="control-field-desc" style={{ color: authStatus.startsWith("Could not") ? "var(--danger)" : "var(--success)", marginTop: 8 }}>
            {authStatus}
          </div>
        )}
      </GlassPanel>

      {/* â”€â”€ Proposal Preview + Risk Sizing â”€â”€ */}
      <GlassPanel
        title="Live-Money Completion Lane"
        subtitle={liveProgression?.next_action ?? "Loading live-money progression gates"}
        variant={liveProgression?.full_progression_clear ? "default" : "warning"}
      >
        <div className="dashboard-grid-3col">
          <CompletionMetric label="Live Dispatch" clear={liveProgression?.live_dispatch_clear} />
          <CompletionMetric label="WASTE Pilot" clear={liveProgression?.waste_pilot_clear} />
          <CompletionMetric label="Verified Payout" clear={liveProgression?.verified_payout_clear} />
        </div>
        <div className="dashboard-grid-3col" style={{ marginTop: 10 }}>
          <MetaRow label="Blockers" value={String(liveProgression?.blocker_count ?? progressionBlockers.length)} mono />
          <MetaRow label="Active Intent" value={liveIntentLabel} mono />
          <MetaRow label="Status" value={liveProgression?.status ?? "SYNCING"} mono />
        </div>
        <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
          {firstBlockers.length > 0 ? firstBlockers.map((blocker) => (
            <div key={`${blocker.plane}-${blocker.blocker_id}`} className="lock-line" style={{ alignItems: "flex-start" }}>
              <span style={{ color: "var(--danger)", marginRight: 6 }}>x</span>
              <span>
                <span className="mono">{blocker.plane}</span>: {blocker.detail}
                {blocker.next_action && <span style={{ color: "var(--text-secondary)" }}> {blocker.next_action}</span>}
              </span>
            </div>
          )) : (
            <div className="control-field-desc" style={{ color: liveProgression?.full_progression_clear ? "var(--success)" : "var(--text-secondary)" }}>
              {liveProgression?.full_progression_clear ? "All live-money progression checks are clear for owner review." : "Progression packet is syncing."}
            </div>
          )}
        </div>
        {progressionBlockers.length > firstBlockers.length && (
          <div className="control-field-desc" style={{ marginTop: 8 }}>
            Showing {firstBlockers.length} of {progressionBlockers.length} blockers. Open Settings for the full audit lane.
          </div>
        )}
        <div className="mobile-api-row" style={{ marginTop: 10 }}>
          <a className="sweep-action-button setup-link" href="?page=settings">OPEN SETTINGS GATES</a>
          <a className="sweep-action-button setup-link" href="?page=proof">OPEN PROOF / PAYMENT</a>
        </div>
        <div className="control-field-desc" style={{ marginTop: 8, color: "var(--text-secondary)" }}>
          {liveProgression?.claim_boundary ?? "Read-only progress lane. No orders, deposits, withdrawals, or payouts are executed from this panel."}
        </div>
      </GlassPanel>

      <div className="trade-grid-2col">
        <GlassPanel title="Proposal Preview" subtitle={activeDecision ? activeDecision.proposal.proposal_id : "No active signal for this symbol/timeframe"}>
          {activeDecision ? (
            <div className="proposal-preview">
              <div className="proposal-header">
                <span className="route-symbol">{activeDecision.symbol}</span>
                <StatusChip label={activeDecision.direction} variant="info" size="sm" />
                <StatusChip label={activeDecision.action} variant="paper" size="sm" />
                <span
                  className="route-confidence mono"
                  title={CONVICTION_SCORE_TITLE}
                >
                  conviction: {formatConvictionScore(activeDecision.confidence)}
                </span>
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

      {/* â”€â”€ Forecast Harness â”€â”€ */}
      <GlassPanel title="Proposal Price Scale" subtitle={activeDecision ? `${symbol} entry / stop / target context` : "No active paper signal"}>
        <CandlestickChart candles={candlePreview} symbol={symbol} height={180} />
      </GlassPanel>


      <GlassPanel
        title={activeQuoteIsStatic ? "Active Market Movement - Static Simulation" : "Active Market Movement"}
        subtitle={activeQuote ? `${symbol} provider/MT5-priced when available; static simulator is labeled` : "Select a currently routed paper symbol to view movement"}
      >
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
          <StatusChip
            label={movementSource.statusLabel}
            variant={movementSource.statusTone}
            size="sm"
          />
          <StatusChip label={`${movementSource.providerBackedCount} PROVIDER`} variant={movementSource.providerBackedCount ? "success" : "muted"} size="sm" />
          <StatusChip label={`${movementSource.staticFallbackCount} STATIC`} variant={movementSource.staticFallbackCount ? "warning" : "success"} size="sm" />
          {movementSource.mt5FallbackCount > 0 && (
            <StatusChip label={`${movementSource.mt5FallbackCount} MT5 FALLBACK`} variant="info" size="sm" />
          )}
          <StatusChip label={`PROVIDER ${movementSource.providerLabel}`} variant="muted" size="sm" />
        </div>
        {activeQuote && activePosition ? (
          <div className="dashboard-grid-3col">
            <div className="metric-stack" style={{ padding: 0 }}>
              <MetaRow label="Bid / Ask" value={`${activeQuote.bid.toFixed(2)} / ${activeQuote.ask.toFixed(2)}`} mono />
              <MetaRow label="Spread" value={`${activeQuote.spread_units.toFixed(1)} ${activeQuote.price_unit_name}`} mono />
              <MetaRow label="Source" value={activeQuote.source} mono />
              <MetaRow label="Ticket" value={activePositionTicket} mono />
            </div>
            <div className="metric-stack" style={{ padding: 0 }}>
              <MetaRow label="Current" value={activePosition.current_price.toFixed(2)} mono />
              <MetaRow label="Floating P/L" value={`$${activePosition.floating_pnl_usd.toFixed(2)} (${activePosition.floating_pnl_units.toFixed(2)} ${activeQuote.price_unit_name}s)`} mono />
              <MetaRow label="Margin Est." value={`$${activePosition.margin_estimate_usd.toFixed(2)}`} mono />
              <MetaRow label="Position Source" value={activePositionSourceLabel} mono />
            </div>
            <div className="metric-stack" style={{ padding: 0 }}>
              <MetaRow label="To SL" value={activePosition.distance_to_sl_units == null ? "-" : `${activePosition.distance_to_sl_units.toFixed(2)} ${activeQuote.price_unit_name}s`} mono />
              <MetaRow label="To TP" value={activePosition.distance_to_tp_units == null ? "-" : `${activePosition.distance_to_tp_units.toFixed(2)} ${activeQuote.price_unit_name}s`} mono />
              <MetaRow label="Opened" value={formatOpenedAt(activePosition.opened_at)} mono />
              <MetaRow label="Age" value={formatMovementPositionAge(activePosition)} mono />
            </div>
          </div>
        ) : (
          <NoSignal symbol={symbol} timeframe={timeframe} />
        )}
        {activeQuoteIsStatic && (
          <div style={{ marginTop: 8, fontSize: "0.7rem", color: "var(--warning)" }}>
            Static simulator pricing: this row is not being moved by a usable provider/MT5 quote right now, so floating P/L can remain unchanged at the entry price.
            {activePosition?.stale_reason ? ` ${activePosition.stale_reason}` : ""}
          </div>
        )}
        <div style={{ marginTop: 8, fontSize: "0.7rem", color: "var(--warning)" }}>
          {movement?.claim_boundary ?? "Paper/demo movement only. Live trading and payment movement wait for owner authority switches and provider setup."}
        </div>
      </GlassPanel>

      <GlassPanel title="Forecast Harness" subtitle="Strategy model status for current session">
        <div className="forecast-grid">
          <ForecastModel name="tsmom_126_250_2_10" status="OK" detail="Day-1 paper signal: NAS100 (75.4%), US30 (46.1%)" />
          <ForecastModel name="range_scalper_24_120" status="NO_SIGNAL" detail="Not active for index D1; active on FX M15/H1 walk-forward" />
          <ForecastModel name="tsmom_252_500_2_8" status="WEAK_EDGE" detail="Secondary to 126 variant; lower conviction score on current window" />
          <ForecastModel name="chronos_signal" status="UNAVAILABLE" detail="Not run in current paper session" />
          <ForecastModel name="meanrev_trend_filter" status="UNAVAILABLE" detail="Cost-sensitive; not active on current instruments" />
          <ForecastModel name="cas_ensemble" status="UNAVAILABLE" detail="Ensemble not compiled for paper route" />
        </div>
      </GlassPanel>

      {/* â”€â”€ CAS Expression â”€â”€ */}
      <GlassPanel title="CAS Expression" subtitle="Compiler state">
        <div className="cas-expression">
          <div className="cas-expr-row">
            <span className="field-label">Expression</span>
            <code className="cas-expr-code">^2^C Ã— ^5^C â†’ ^9^O</code>
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

      {/* â”€â”€ Primary Actions â”€â”€ */}
      <GlassPanel title="Order" variant="danger">
        <div className="trade-action">
          <div className="trade-action-buttons">
            <button className="btn-paper" disabled={actionBusy !== ""} onClick={() => void runPaperProposal()}>
              {actionBusy === "proposal" ? "RUNNING..." : "RUN WASTE PROBE"}
            </button>
            <button className="btn-send" disabled={actionBusy !== ""} onClick={() => void startPaperLoop()}>
              {actionBusy === "paper-loop" ? "STARTING..." : "START PAPER LOOP"}
            </button>
          </div>
          <div className="trade-action-reasons">
            <LockLine reason="PASS-gated paper/demo execution sink is wired; dispatch still requires a fresh edge PASS token." />
            <LockLine reason={`Sample scheduler: ${sampleScheduler?.running ? "RUNNING" : "STOPPED"}; latest ${sampleScheduler?.latest_collector_status ?? "not reported"}.`} />
            <LockLine reason="Live execution and money movement still require owner authorization, broker/provider setup, and action-time checks." />
          </div>
          {actionStatus && <div className="trade-action-status">{actionStatus}</div>}
        </div>
      </GlassPanel>
    </div>
  );
}

/* â”€â”€ Sub-components â”€â”€ */

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

function formatOpenedAt(value: string | null | undefined): string {
  const text = (value ?? "").trim();
  if (!text) return "unknown";
  const parsed = new Date(text);
  if (Number.isNaN(parsed.getTime())) {
    return text.replace("T", " ").replace("Z", " UTC");
  }
  const pad = (part: number) => String(part).padStart(2, "0");
  return `${parsed.getUTCFullYear()}-${pad(parsed.getUTCMonth() + 1)}-${pad(parsed.getUTCDate())} ${pad(parsed.getUTCHours())}:${pad(parsed.getUTCMinutes())} UTC`;
}

function findCapability(auth: AuthorizationState | null, capability: string): AuthorizationState["capabilities"][number] | undefined {
  return auth?.capabilities.find((cap) => cap.capability === capability);
}

function AuthStatusCard({
  title,
  capability,
}: {
  title: string;
  capability?: AuthorizationState["capabilities"][number];
}) {
  const authorized = Boolean(capability?.authorized);
  const rawStatus = capability?.status ?? "NOT READY";
  const label = authorized ? "AUTHORIZED" : rawStatus.includes("NOT LICENSED") ? "OWNER PENDING" : rawStatus;
  const reason = authorized
    ? "Owner gate authorized."
    : capability?.missing_requirements.slice(0, 2).join("; ") || "Waiting for owner/provider setup.";
  return (
    <div className="disabled-control" style={{ borderColor: authorized ? "var(--success)" : "var(--warning-dim)" }}>
      <div className="disabled-control-header">
        <span className="disabled-control-label">{title}</span>
        <StatusChip label={label} variant={authorized ? "success" : "warning"} size="sm" />
      </div>
      <div className="disabled-control-reason" style={{ color: authorized ? "var(--success)" : "var(--text-secondary)" }}>
        {reason}
      </div>
    </div>
  );
}

function CompletionMetric({ label, clear }: { label: string; clear?: boolean }) {
  return (
    <div className="metric-stack" style={{ padding: 0 }}>
      <span className="field-label">{label}</span>
      <StatusChip label={clear ? "CLEAR" : "STANDBY"} variant={clear ? "success" : "warning"} size="sm" />
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
      <span style={{ color: "var(--danger)", marginRight: 6 }}>âœ•</span>
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

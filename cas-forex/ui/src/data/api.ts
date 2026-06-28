/* ── CAS Forex — API Client ── */

import type {
  DashboardState,
  UIReadinessReport,
  DailySchedule,
  DailyBundle,
  StrategyLead,
  BacksolveSummary,
  ConditionTallyBucket,
  WalkForwardSummary,
  ExternalBenchmarkReport,
  ForexFuryReplayCandidateReport,
  ForexFuryReplayResultsReport,
  ForexFurySetImportReport,
  AgentWorkflowPlan,
  AgentWorkflowCycle,
  AgentInformationFlow,
  AgentMessageBusSummary,
  AgentMemoryReport,
  AgentResearchQueueReport,
  StrategyDevQueueReport,
  StrategyPatchRunnerReport,
  DailyLearningRollupReport,
  SessionAutowakeReport,
  TerminalReceiptWatcherReport,
  TerminalBridgeSupervisorReport,
  MT4TerminalActivationReport,
  MT4PingRoundtripReport,
  MT4TerminalSessionVerifierReport,
  MT4HistoryExportVerifierReport,
  MT5TerminalApiVerifierReport,
  MT5PaperExecutionVerifierReport,
  MT5DealHistoryIngestReport,
  TerminalPositionReconciliationReport,
  TerminalOperabilityVerifierReport,
  TerminalReceiptIngestReport,
  TerminalHistoryIngestReport,
  MT5Receipt,
  MT5ProbeStatus,
  AdaptiveCockpitPayload,
  OwnerControlState,
  MTHistorySummary,
  PcbaCockpitPayload,
  AccountLedgerState,
  MovementStreamState,
  AccountReconciliationReport,
  LiveReadinessReport,
  BrokerSyncedRiskPreview,
} from "../types/evidence";

export const API_BASE_STORAGE_KEY = "cas_forex_api_base";
const DEFAULT_API_BASE =
  import.meta.env.VITE_CAS_FOREX_API_BASE ?? "http://127.0.0.1:8765/api/forex";

export function getApiBase(): string {
  if (typeof window === "undefined") return DEFAULT_API_BASE;
  return window.localStorage.getItem(API_BASE_STORAGE_KEY) || DEFAULT_API_BASE;
}

export function setApiBase(value: string): void {
  if (typeof window === "undefined") return;
  const cleaned = value.trim().replace(/\/+$/, "");
  if (!cleaned) {
    window.localStorage.removeItem(API_BASE_STORAGE_KEY);
    return;
  }
  window.localStorage.setItem(API_BASE_STORAGE_KEY, cleaned);
}

export function resetApiBase(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(API_BASE_STORAGE_KEY);
}

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${getApiBase()}${path}`, {
    headers: { "Content-Type": "application/json" },
    signal: AbortSignal.timeout(8000),
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

async function apiPost<T>(path: string): Promise<T> {
  const res = await fetch(`${getApiBase()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    signal: AbortSignal.timeout(8000),
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

async function apiPostJson<TResp, TBody>(path: string, body: TBody): Promise<TResp> {
  const res = await fetch(`${getApiBase()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(10_000),
  });
  const text = await res.text();
  let parsed: unknown;
  try {
    parsed = text ? JSON.parse(text) : null;
  } catch {
    parsed = text;
  }
  if (!res.ok) {
    const err = new Error(`API ${res.status}: ${res.statusText}`) as Error & {
      status?: number;
      payload?: unknown;
    };
    err.status = res.status;
    err.payload = parsed;
    throw err;
  }
  return parsed as TResp;
}

async function apiDelete<T>(path: string): Promise<T> {
  const res = await fetch(`${getApiBase()}${path}`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    signal: AbortSignal.timeout(8000),
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

// ── Floating AI assistant ──

export interface AssistantTurn {
  role: "user" | "assistant";
  content: string;
}

export interface AssistantReply {
  reply: string;
  source: string; // "ai" | "unconfigured" | "error"
  model?: string;
  needs?: string;
}

export async function postAssistantChat(
  message: string,
  history: AssistantTurn[],
): Promise<AssistantReply> {
  // Dedicated longer timeout — a real Claude reply can take longer than the
  // shared 10s POST helper allows, especially over a phone connection.
  const res = await fetch(`${getApiBase()}/assistant/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
    signal: AbortSignal.timeout(60_000),
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return (await res.json()) as AssistantReply;
}

// ── Owner risk control (any concurrent count / loss cap, or none) ──

export interface RiskControlState {
  max_concurrent_trades: number | null;
  max_total_exposure_lots: number | null;
  max_loss_cap_usd: number | null;
  max_drawdown_pct: number | null;
  unlimited: {
    concurrent_trades: boolean;
    total_exposure_lots: boolean;
    loss_cap_usd: boolean;
    drawdown_pct: boolean;
  };
  report_kind?: string;
  notes?: string[];
}

export async function fetchRiskControl(): Promise<RiskControlState | null> {
  try { return await apiGet<RiskControlState>("/risk-control/state"); } catch { return null; }
}

export async function updateRiskControl(
  patch: Partial<Record<"max_concurrent_trades" | "max_total_exposure_lots" | "max_loss_cap_usd" | "max_drawdown_pct", number | null>>,
): Promise<RiskControlState> {
  return apiPostJson<RiskControlState, typeof patch>("/risk-control/update", patch);
}

export async function resetRiskControl(): Promise<RiskControlState> {
  return apiPost<RiskControlState>("/risk-control/reset");
}

// ── Owner live-enable control (turn the live-trading gate flags ON in-app) ──

export type LiveEnableKey =
  | "personal_account_ack"
  | "no_pooled_capital_ack"
  | "live_mode"
  | "prefer_mt5"
  | "owner_enable_live_trading"
  | "live_trading_licensed";

export interface LiveEnableFlag {
  key: LiveEnableKey;
  label: string;
  consequence: string;
  enabled: boolean;
  overridden: boolean;
}

export interface RuntimeGateDecision {
  capability: string;
  authorized: boolean;
  status: string;
  missing_requirements: string[];
  satisfied_requirements: string[];
  next_action: string;
}

export interface LiveEnableState {
  report_kind?: string;
  flags: LiveEnableFlag[];
  resolved: Record<LiveEnableKey, boolean>;
  runtime_gates: {
    report_kind?: string;
    decisions: Record<string, RuntimeGateDecision>;
    all_real_money_authorized: boolean;
    summary: string;
  };
  live_trading: RuntimeGateDecision;
  live_authorized: boolean;
  still_missing: string[];
  caveats: string[];
}

export async function fetchLiveEnable(): Promise<LiveEnableState | null> {
  try { return await apiGet<LiveEnableState>("/live-enable/state"); } catch { return null; }
}

export async function updateLiveEnable(
  patch: Partial<Record<LiveEnableKey, boolean>>,
): Promise<LiveEnableState> {
  return apiPostJson<LiveEnableState, typeof patch>("/live-enable/update", patch);
}

export async function resetLiveEnable(): Promise<LiveEnableState> {
  return apiPost<LiveEnableState>("/live-enable/reset");
}

// ── Unified capability authorization (Path to Authorize — all 5 capabilities) ──

export interface AuthorizationToggle {
  key: string;
  label: string;
  consequence: string;
  enabled: boolean;
  overridden: boolean;
}

export interface AuthorizationCapability {
  capability: string;
  title: string;
  authorized: boolean;
  status: string;
  missing_requirements: string[];
  satisfied_requirements: string[];
  toggles: AuthorizationToggle[];
  note: string;
}

export interface AuthorizationProvider {
  payment_provider: string;
  payment_api_key_set: boolean;
  payout_destination_id: string;
  payout_destination_allowlisted: boolean;
  allowlist_label: string;
}

export interface AuthorizationState {
  report_kind?: string;
  capabilities: AuthorizationCapability[];
  provider: AuthorizationProvider;
  all_real_money_authorized: boolean;
  summary: string;
  caveats: string[];
}

export type AuthorizationPatch = Partial<{
  owner_enable_live_trading: boolean;
  live_trading_licensed: boolean;
  owner_enable_broker_accept: boolean;
  owner_enable_auto_deposit: boolean;
  owner_enable_bank_card_movement: boolean;
  owner_enable_payout_automation: boolean;
  payout_destination_allowlisted: boolean;
  payment_provider: string;
  payment_api_key: string;
  payout_destination_id: string;
}>;

export async function fetchAuthorization(): Promise<AuthorizationState | null> {
  try { return await apiGet<AuthorizationState>("/live-enable/authorization"); } catch { return null; }
}

export async function updateAuthorization(patch: AuthorizationPatch): Promise<AuthorizationState> {
  return apiPostJson<AuthorizationState, AuthorizationPatch>("/live-enable/authorization/update", patch);
}

// ── Trading Windows cockpit (live-ish candles + quote per symbol) ──

export interface ChartCandle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface ChartQuote {
  bid: number;
  ask: number;
  mid: number;
  spread: number;
  is_market_open: boolean;
  session: string;
  timestamp: string;
}

export interface ChartWindow {
  report_kind?: string;
  symbol: string;
  timeframe: string;
  bars: number;
  candles: ChartCandle[];
  quote: ChartQuote | null;
  source: string;
  live_feed: boolean;
  feed_label: string;
  cached?: boolean;
  error?: string;
}

export interface ChartSymbols {
  symbols: string[];
  timeframes: string[];
}

export async function fetchChartSymbols(): Promise<ChartSymbols | null> {
  try { return await apiGet<ChartSymbols>("/chart/symbols"); } catch { return null; }
}

export async function fetchChartWindow(
  symbol: string,
  timeframe: string,
  bars = 60,
): Promise<ChartWindow | null> {
  const q = `symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}&bars=${bars}`;
  try { return await apiGet<ChartWindow>(`/chart/window?${q}`); } catch { return null; }
}

export interface ManualOrderResult {
  report_kind?: string;
  status?: string;
  detail?: string;
  mode?: string;
  intent_count?: number;
  executed_count?: number;
  blocked_count?: number;
  rejected_count?: number;
  live_execution_runtime_locked?: boolean;
  results?: { status: string; reason: string }[];
  manual_order?: {
    symbol: string;
    direction: string;
    lots: number;
    stop_loss: number;
    take_profit: number;
    auto_sl: boolean;
    auto_tp: boolean;
  };
}

export async function postManualOrder(body: {
  symbol: string;
  direction: "BUY" | "SELL";
  lots: number;
  sl?: number | null;
  tp?: number | null;
}): Promise<ManualOrderResult> {
  return apiPostJson<ManualOrderResult, typeof body>("/order-dispatch/manual", body);
}

// ── Auto-trade dispatch loop (runs the gated cycle on a timer; paper by default) ──

export interface DispatchLoopState {
  report_kind?: string;
  running: boolean;
  interval_seconds?: number;
  symbols?: string[];
  sessions?: string[];
  active_sessions?: string[];
  cycles_run?: number;
  cycles_idle?: number;
  last_run_iso?: string | null;
  last_summary?: string | null;
  last_error?: string | null;
  started_at_iso?: string | null;
  mode?: string;
  note?: string;
  status?: string; // "CONFIRM_REQUIRED" when live is authorized
  detail?: string;
}

export interface DispatchLoopStart {
  interval_seconds: number;
  symbols?: string[];
  sessions?: string[];
}

export async function fetchDispatchLoopStatus(): Promise<DispatchLoopState | null> {
  try { return await apiGet<DispatchLoopState>("/dispatch-loop/status"); } catch { return null; }
}

export async function startDispatchLoop(body: DispatchLoopStart, confirm = false): Promise<DispatchLoopState> {
  const q = confirm ? "?confirm=true" : "";
  return apiPostJson<DispatchLoopState, DispatchLoopStart>(`/dispatch-loop/start${q}`, body);
}

export async function stopDispatchLoop(): Promise<DispatchLoopState> {
  return apiPost<DispatchLoopState>("/dispatch-loop/stop");
}

// ── Multi-timeframe runtime selector ──

export interface SymbolTimeframeSelection {
  symbol: string;
  active_timeframes: string[];
}

export interface CanonicalTimeframes {
  canonical_timeframes: string[];
}

export interface ActiveTimeframesSnapshot {
  symbols: SymbolTimeframeSelection[];
}

export async function fetchCanonicalTimeframes(): Promise<CanonicalTimeframes | null> {
  try { return await apiGet<CanonicalTimeframes>("/timeframes/canonical"); } catch { return null; }
}

export async function fetchAllActiveTimeframes(): Promise<ActiveTimeframesSnapshot | null> {
  try { return await apiGet<ActiveTimeframesSnapshot>("/timeframes"); } catch { return null; }
}

export async function fetchSymbolTimeframes(symbol: string): Promise<SymbolTimeframeSelection | null> {
  try { return await apiGet<SymbolTimeframeSelection>(`/timeframes/${encodeURIComponent(symbol)}`); } catch { return null; }
}

export async function activateTimeframe(symbol: string, timeframe: string): Promise<SymbolTimeframeSelection | null> {
  try {
    return await apiPost<SymbolTimeframeSelection>(
      `/timeframes/${encodeURIComponent(symbol)}/${encodeURIComponent(timeframe)}`,
    );
  } catch {
    return null;
  }
}

export async function deactivateTimeframe(symbol: string, timeframe: string): Promise<SymbolTimeframeSelection | null> {
  try {
    return await apiDelete<SymbolTimeframeSelection>(
      `/timeframes/${encodeURIComponent(symbol)}/${encodeURIComponent(timeframe)}`,
    );
  } catch {
    return null;
  }
}

// ── Live trade telemetry ──

export interface LiveTelemetryPosition {
  symbol: string;
  direction: "BUY" | "SELL";
  lots: number;
  entry_price: number;
  current_price: number;
  floating_pnl: number;
  opened_at_iso: string | null;
  broker_ticket: string | null;
}

export interface LiveTelemetryResponse {
  as_of_iso: string;
  open_positions: LiveTelemetryPosition[];
  totals: {
    open_position_count: number;
    total_floating_pnl: number;
  };
  data_freshness: {
    source: "mt5_terminal_api_verifier" | "movement_stream" | "none";
    stale: boolean;
    last_update_iso: string | null;
  };
}

export async function fetchLiveTelemetry(): Promise<LiveTelemetryResponse | null> {
  try {
    return await apiGet<LiveTelemetryResponse>("/live-telemetry");
  } catch {
    return null;
  }
}

// ── Aggregate dashboard ──

export async function fetchDashboard(): Promise<DashboardState | null> {
  try {
    return await apiGet<DashboardState>("/dashboard");
  } catch {
    return null;
  }
}

// ── Individual endpoints ──

export async function fetchReadiness(): Promise<UIReadinessReport | null> {
  try { return await apiGet<UIReadinessReport>("/proof/readiness"); } catch { return null; }
}

export async function fetchSchedule(): Promise<DailySchedule | null> {
  try { return await apiGet<DailySchedule>("/proof/schedule"); } catch { return null; }
}

export async function fetchDailyBundle(date?: string): Promise<DailyBundle | null> {
  const path = date ? `/bundle/daily/${date}` : "/bundle/daily";
  try { return await apiGet<DailyBundle>(path); } catch { return null; }
}

export async function fetchStrategyLeads(): Promise<StrategyLead[] | null> {
  try { return await apiGet<StrategyLead[]>("/strategy/leads"); } catch { return null; }
}

export async function fetchBacksolve(): Promise<BacksolveSummary | null> {
  try { return await apiGet<BacksolveSummary>("/strategy/backsolve"); } catch { return null; }
}

export async function fetchConditionTally(): Promise<ConditionTallyBucket[] | null> {
  try { return await apiGet<ConditionTallyBucket[]>("/strategy/condition-tally"); } catch { return null; }
}

export async function fetchWalkForward(): Promise<WalkForwardSummary | null> {
  try { return await apiGet<WalkForwardSummary>("/strategy/walk-forward"); } catch { return null; }
}

export async function fetchExternalBenchmarks(): Promise<ExternalBenchmarkReport | null> {
  try { return await apiGet<ExternalBenchmarkReport>("/strategy/external-benchmarks"); } catch { return null; }
}

export async function fetchForexFurySetImport(): Promise<ForexFurySetImportReport | null> {
  try { return await apiGet<ForexFurySetImportReport>("/strategy/forex-fury-set-import"); } catch { return null; }
}

export async function fetchForexFuryReplayCandidates(): Promise<ForexFuryReplayCandidateReport | null> {
  try { return await apiGet<ForexFuryReplayCandidateReport>("/strategy/forex-fury-replay-candidates"); } catch { return null; }
}

export async function fetchForexFuryReplayResults(): Promise<ForexFuryReplayResultsReport | null> {
  try { return await apiGet<ForexFuryReplayResultsReport>("/strategy/forex-fury-replay-results"); } catch { return null; }
}

export async function fetchAgentWorkflowPlan(): Promise<AgentWorkflowPlan | null> {
  try { return await apiGet<AgentWorkflowPlan>("/strategy/agent-workflow-plan"); } catch { return null; }
}

export async function fetchAgentWorkflowCycle(): Promise<AgentWorkflowCycle | null> {
  try { return await apiGet<AgentWorkflowCycle>("/strategy/agent-workflow-cycle/latest"); } catch { return null; }
}

export async function fetchAgentInformationFlow(): Promise<AgentInformationFlow | null> {
  try { return await apiGet<AgentInformationFlow>("/strategy/agent-information-flow"); } catch { return null; }
}

export async function fetchAgentMessageBusSummary(): Promise<AgentMessageBusSummary | null> {
  try { return await apiGet<AgentMessageBusSummary>("/strategy/agent-workflow-events/summary"); } catch { return null; }
}

export async function fetchAgentMemory(): Promise<AgentMemoryReport | null> {
  try { return await apiGet<AgentMemoryReport>("/strategy/agent-memory/latest"); } catch { return null; }
}

export async function fetchAgentResearchQueue(): Promise<AgentResearchQueueReport | null> {
  try { return await apiGet<AgentResearchQueueReport>("/strategy/agent-research-queue/latest"); } catch { return null; }
}

export async function fetchStrategyDevQueue(): Promise<StrategyDevQueueReport | null> {
  try { return await apiGet<StrategyDevQueueReport>("/strategy/strategy-dev-queue/latest"); } catch { return null; }
}

export async function fetchStrategyPatchRunner(): Promise<StrategyPatchRunnerReport | null> {
  try { return await apiGet<StrategyPatchRunnerReport>("/strategy/strategy-patch-runner/latest"); } catch { return null; }
}

export async function fetchDailyLearningRollup(): Promise<DailyLearningRollupReport | null> {
  try { return await apiGet<DailyLearningRollupReport>("/strategy/daily-learning-rollup/latest"); } catch { return null; }
}

export async function fetchSessionAutowake(): Promise<SessionAutowakeReport | null> {
  try { return await apiGet<SessionAutowakeReport>("/strategy/session-autowake/latest"); } catch { return null; }
}

export async function fetchTerminalReceiptWatcher(): Promise<TerminalReceiptWatcherReport | null> {
  try { return await apiGet<TerminalReceiptWatcherReport>("/strategy/terminal-receipt-watcher/latest"); } catch { return null; }
}

export async function fetchTerminalBridgeSupervisor(): Promise<TerminalBridgeSupervisorReport | null> {
  try { return await apiGet<TerminalBridgeSupervisorReport>("/strategy/terminal-bridge-supervisor/latest"); } catch { return null; }
}

export async function fetchMT4TerminalActivation(): Promise<MT4TerminalActivationReport | null> {
  try { return await apiGet<MT4TerminalActivationReport>("/strategy/mt4-terminal-activation/latest"); } catch { return null; }
}

export async function fetchMT4PingRoundtrip(): Promise<MT4PingRoundtripReport | null> {
  try { return await apiGet<MT4PingRoundtripReport>("/strategy/mt4-ping-roundtrip/latest"); } catch { return null; }
}

export async function fetchMT4TerminalSessionVerifier(): Promise<MT4TerminalSessionVerifierReport | null> {
  try { return await apiGet<MT4TerminalSessionVerifierReport>("/strategy/mt4-terminal-session-verifier/latest"); } catch { return null; }
}

export async function fetchMT4HistoryExportVerifier(): Promise<MT4HistoryExportVerifierReport | null> {
  try { return await apiGet<MT4HistoryExportVerifierReport>("/strategy/mt4-history-export-verifier/latest"); } catch { return null; }
}

export async function fetchMT5TerminalApiVerifier(): Promise<MT5TerminalApiVerifierReport | null> {
  try { return await apiGet<MT5TerminalApiVerifierReport>("/strategy/mt5-terminal-api-verifier/latest"); } catch { return null; }
}

export async function fetchMT5PaperExecutionVerifier(): Promise<MT5PaperExecutionVerifierReport | null> {
  try { return await apiGet<MT5PaperExecutionVerifierReport>("/strategy/mt5-paper-execution-verifier/latest"); } catch { return null; }
}

export async function fetchMT5DealHistoryIngest(): Promise<MT5DealHistoryIngestReport | null> {
  try { return await apiGet<MT5DealHistoryIngestReport>("/strategy/mt5-deal-history-ingest/latest"); } catch { return null; }
}

export async function fetchTerminalPositionReconciliation(): Promise<TerminalPositionReconciliationReport | null> {
  try { return await apiGet<TerminalPositionReconciliationReport>("/strategy/terminal-position-reconciliation/latest"); } catch { return null; }
}

export async function fetchTerminalOperabilityVerifier(): Promise<TerminalOperabilityVerifierReport | null> {
  try { return await apiGet<TerminalOperabilityVerifierReport>("/strategy/terminal-operability-verifier/latest"); } catch { return null; }
}

export async function fetchTerminalReceiptIngest(): Promise<TerminalReceiptIngestReport | null> {
  try { return await apiGet<TerminalReceiptIngestReport>("/strategy/terminal-receipt-ingest/latest"); } catch { return null; }
}

export async function fetchTerminalHistoryIngest(): Promise<TerminalHistoryIngestReport | null> {
  try { return await apiGet<TerminalHistoryIngestReport>("/strategy/terminal-history-ingest/latest"); } catch { return null; }
}

export async function fetchMT5Receipt(): Promise<MT5Receipt | null> {
  try { return await apiGet<MT5Receipt>("/mt/receipt/latest"); } catch { return null; }
}

export async function fetchMT5ProbeStatus(): Promise<MT5ProbeStatus | null> {
  try { return await apiGet<MT5ProbeStatus>("/mt/probe/latest"); } catch { return null; }
}

export async function fetchAdaptiveCockpit(): Promise<AdaptiveCockpitPayload | null> {
  try { return await apiGet<AdaptiveCockpitPayload>("/adaptive/cockpit"); } catch { return null; }
}

export async function fetchOwnerControl(): Promise<OwnerControlState | null> {
  try { return await apiGet<OwnerControlState>("/settings/owner-control"); } catch { return null; }
}

export async function fetchMTHistory(): Promise<MTHistorySummary | null> {
  try { return await apiGet<MTHistorySummary>("/mt/history"); } catch { return null; }
}

export async function fetchPcbaCockpit(): Promise<PcbaCockpitPayload | null> {
  try { return await apiGet<PcbaCockpitPayload>("/pcba/cockpit"); } catch { return null; }
}

export async function fetchAccountLedger(initialInvestment?: number): Promise<AccountLedgerState | null> {
  const suffix = initialInvestment != null ? `?initial_investment=${encodeURIComponent(initialInvestment)}` : "";
  try { return await apiGet<AccountLedgerState>(`/account/ledger${suffix}`); } catch { return null; }
}

export async function fetchBrokerSyncedRiskPreview(): Promise<BrokerSyncedRiskPreview | null> {
  try { return await apiGet<BrokerSyncedRiskPreview>("/account/broker-sync-risk-preview"); } catch { return null; }
}

export async function applyBrokerSyncedRiskReview(): Promise<BrokerSyncedRiskPreview | null> {
  try {
    return await apiPost<BrokerSyncedRiskPreview>("/account/apply-broker-sync-risk-review?confirm_apply=true");
  } catch {
    return null;
  }
}

export async function fetchMovementStream(useProvider = false): Promise<MovementStreamState | null> {
  const suffix = useProvider ? "?use_provider=true" : "";
  try { return await apiGet<MovementStreamState>(`/movement/snapshot${suffix}`); } catch { return null; }
}

export async function fetchAccountReconciliation(): Promise<AccountReconciliationReport | null> {
  try { return await apiGet<AccountReconciliationReport>("/reconciliation/account"); } catch { return null; }
}

export async function fetchLiveReadiness(syncToBroker = false): Promise<LiveReadinessReport | null> {
  const suffix = syncToBroker ? "?sync_to_broker=true" : "";
  try { return await apiGet<LiveReadinessReport>(`/readiness/live${suffix}`); } catch { return null; }
}

// ── Agent decision explainer + autonomous loop health ──

export interface DecisionChainStep {
  name: string;
  headline: string;
  detail: string;
  evidence: string[];
  status: string;
}

export interface AgentDecisionResponse {
  cycle_id: string | null;
  overall_status: string;
  plain_english_summary: string;
  chain: DecisionChainStep[];
  next_action_hint: string | null;
}

export interface AutonomousLoopHealthResponse {
  overall_status: string;
  last_cycle_at_iso: string | null;
  seconds_since_last_cycle: number | null;
  cycles_today: number;
  decisions_today: number;
  executions_today: number;
  blocked_today: number;
  autowake_present: boolean;
  autowake_next_due_iso: string | null;
  plain_english_summary: string;
  diagnostic_hints: string[];
}

export async function fetchAgentDecisionLatest(): Promise<AgentDecisionResponse | null> {
  try { return await apiGet<AgentDecisionResponse>("/agent-decision/latest"); } catch { return null; }
}

export interface AgentDecisionHistoryItem extends AgentDecisionResponse {
  cycle_report_path: string;
  actioned_at?: string | null;
}

export interface AgentDecisionHistoryResponse {
  count: number;
  limit: number;
  decisions: AgentDecisionHistoryItem[];
}

export async function fetchAgentDecisionHistory(limit: number = 25): Promise<AgentDecisionHistoryResponse | null> {
  try { return await apiGet<AgentDecisionHistoryResponse>(`/agent-decision/history?limit=${limit}`); } catch { return null; }
}

export async function fetchAutonomousLoopHealth(): Promise<AutonomousLoopHealthResponse | null> {
  try { return await apiGet<AutonomousLoopHealthResponse>("/autonomous-loop/health"); } catch { return null; }
}

// ── React hook with fixture fallback ──

import { useState, useEffect, useCallback } from "react";

interface UseDashboardResult {
  state: DashboardState | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}


function mergeDashboardState(fallback: DashboardState, live: DashboardState): DashboardState {
  // Keep live evidence when present, but do not let a partial/stale dashboard
  // remove optional panels such as PCBA. This makes the app operational even
  // while the API is restarting or a cached dashboard lacks newly added keys.
  return {
    ...fallback,
    ...live,
    adaptive: live.adaptive ?? fallback.adaptive,
    ownerControl: live.ownerControl ?? fallback.ownerControl,
    accountLedger: live.accountLedger ?? fallback.accountLedger,
    movementStream: live.movementStream ?? fallback.movementStream,
    accountReconciliation: live.accountReconciliation ?? fallback.accountReconciliation,
    liveReadiness: live.liveReadiness ?? fallback.liveReadiness,
    brokerSyncedRiskPreview: live.brokerSyncedRiskPreview ?? fallback.brokerSyncedRiskPreview,
    mtHistory: live.mtHistory ?? fallback.mtHistory,
    strategyLeads: live.strategyLeads ?? fallback.strategyLeads,
    backsolve: live.backsolve ?? fallback.backsolve,
    conditionTally: live.conditionTally ?? fallback.conditionTally,
    walkForward: live.walkForward ?? fallback.walkForward,
    externalBenchmarks: live.externalBenchmarks ?? fallback.externalBenchmarks,
    forexFurySetImport: live.forexFurySetImport ?? fallback.forexFurySetImport,
    forexFuryReplayCandidates: live.forexFuryReplayCandidates ?? fallback.forexFuryReplayCandidates,
    forexFuryReplayResults: live.forexFuryReplayResults ?? fallback.forexFuryReplayResults,
    agentWorkflowPlan: live.agentWorkflowPlan ?? fallback.agentWorkflowPlan,
    agentWorkflowCycle: live.agentWorkflowCycle ?? fallback.agentWorkflowCycle,
    agentInformationFlow: live.agentInformationFlow ?? fallback.agentInformationFlow,
    agentMessageBus: live.agentMessageBus ?? fallback.agentMessageBus,
    agentMemory: live.agentMemory ?? fallback.agentMemory,
    agentResearchQueue: live.agentResearchQueue ?? fallback.agentResearchQueue,
    strategyDevQueue: live.strategyDevQueue ?? fallback.strategyDevQueue,
    strategyPatchRunner: live.strategyPatchRunner ?? fallback.strategyPatchRunner,
    dailyLearningRollup: live.dailyLearningRollup ?? fallback.dailyLearningRollup,
    sessionAutowake: live.sessionAutowake ?? fallback.sessionAutowake,
    terminalReceiptWatcher: live.terminalReceiptWatcher ?? fallback.terminalReceiptWatcher,
    terminalBridgeSupervisor: live.terminalBridgeSupervisor ?? fallback.terminalBridgeSupervisor,
    mt4TerminalActivation: live.mt4TerminalActivation ?? fallback.mt4TerminalActivation,
    mt4PingRoundtrip: live.mt4PingRoundtrip ?? fallback.mt4PingRoundtrip,
    mt4TerminalSessionVerifier: live.mt4TerminalSessionVerifier ?? fallback.mt4TerminalSessionVerifier,
    mt4HistoryExportVerifier: live.mt4HistoryExportVerifier ?? fallback.mt4HistoryExportVerifier,
    mt5TerminalApiVerifier: live.mt5TerminalApiVerifier ?? fallback.mt5TerminalApiVerifier,
    mt5PaperExecutionVerifier: live.mt5PaperExecutionVerifier ?? fallback.mt5PaperExecutionVerifier,
    mt5DealHistoryIngest: live.mt5DealHistoryIngest ?? fallback.mt5DealHistoryIngest,
    terminalPositionReconciliation: live.terminalPositionReconciliation ?? fallback.terminalPositionReconciliation,
    terminalOperabilityVerifier: live.terminalOperabilityVerifier ?? fallback.terminalOperabilityVerifier,
    terminalReceiptIngest: live.terminalReceiptIngest ?? fallback.terminalReceiptIngest,
    terminalHistoryIngest: live.terminalHistoryIngest ?? fallback.terminalHistoryIngest,
    mt5Receipt: live.mt5Receipt ?? fallback.mt5Receipt,
    mt5ProbeStatus: live.mt5ProbeStatus ?? fallback.mt5ProbeStatus,
    authorityBoundary: live.authorityBoundary ?? fallback.authorityBoundary,
    runtimeGates: live.runtimeGates ?? fallback.runtimeGates,
    aiModel: live.aiModel ?? fallback.aiModel,
    brokerCandidates: live.brokerCandidates ?? fallback.brokerCandidates,
    pcba: live.pcba ?? fallback.pcba,
  };
}

export function useDashboard(initialState: DashboardState): UseDashboardResult {
  const [state, setState] = useState<DashboardState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const data = await fetchDashboard();
    if (data) {
      setState(mergeDashboardState(initialState, data));
    } else {
      setState(initialState);
      setError("API unreachable — using fixture data");
    }
    setLoading(false);
  }, [initialState]);

  useEffect(() => { load(); }, [load]);

  return { state, loading, error, refetch: load };
}

// ── Operator briefing (one-call snapshot) ──

export interface OperatorBriefingResponse {
  loop_health_status: string;
  cycles_today: number;
  decisions_today: number;
  executions_today: number;
  blocked_today: number;
  last_cycle_at_iso: string | null;
  seconds_since_last_cycle: number | null;
  plain_english_briefing: string;
  diagnostic_hints: string[];
  next_action_hint: string | null;
  generated_at_iso?: string | null;
  [key: string]: unknown;
}

export async function fetchOperatorBriefing(): Promise<OperatorBriefingResponse | null> {
  try {
    return await apiGet<OperatorBriefingResponse>("/operator-briefing");
  } catch {
    return null;
  }
}

// ── API server health (root /health) ──

export interface ApiHealthResponse {
  status: string;
  [key: string]: unknown;
}

export async function fetchHealth(): Promise<ApiHealthResponse | null> {
  try {
    return await apiGet<ApiHealthResponse>("/health");
  } catch {
    return null;
  }
}

// ── Stack health ──

export interface StackHealthCheckResult {
  name: string;
  status: string;
  headline: string;
  detail: string;
  [key: string]: unknown;
}

export interface StackHealthReport {
  overall_status: string;
  plain_english_summary: string;
  checks: StackHealthCheckResult[];
  next_actions: string[];
  generated_at_iso?: string | null;
  [key: string]: unknown;
}

export async function fetchStackHealth(): Promise<StackHealthReport | null> {
  try {
    return await apiGet<StackHealthReport>("/stack-health/check");
  } catch {
    return null;
  }
}

// ── Strategy comparison ──

export interface StrategyComparisonRecord {
  rank: number;
  strategy_id: string;
  source: string;
  symbol: string | null;
  timeframe: string | null;
  family: string | null;
  profit_factor: number | null;
  max_drawdown_pct: number | null;
  walk_forward_grade: string | null;
  composite_score: number | null;
  [key: string]: unknown;
}

export interface StrategyRankingReport {
  records: StrategyComparisonRecord[];
  limit: number;
  total_available: number;
  plain_english_summary?: string;
  generated_at_iso?: string | null;
  [key: string]: unknown;
}

export interface StrategyDiffField {
  field: string;
  a_value: unknown;
  b_value: unknown;
}

export interface StrategyDiff {
  strategy_id_a: string;
  strategy_id_b: string;
  symbol_match?: boolean;
  timeframe_match?: boolean;
  family_match?: boolean;
  field_diffs: StrategyDiffField[];
  plain_english_diff: string;
  generated_at_iso?: string | null;
  [key: string]: unknown;
}

export async function fetchRankedStrategies(
  limit: number,
): Promise<StrategyRankingReport | null> {
  try {
    return await apiGet<StrategyRankingReport>(
      `/strategy-comparison/ranked?limit=${encodeURIComponent(limit)}`,
    );
  } catch {
    return null;
  }
}

export async function fetchStrategyDiff(
  idA: string,
  idB: string,
): Promise<StrategyDiff | null> {
  try {
    return await apiGet<StrategyDiff>(
      `/strategy-comparison/diff?strategy_id_a=${encodeURIComponent(idA)}&strategy_id_b=${encodeURIComponent(idB)}`,
    );
  } catch {
    return null;
  }
}

// ── Daily report ──

export interface DailySection {
  section_name: string;
  headline: string;
  detail: string;
  metrics?: Record<string, unknown>;
  notable_events?: string[];
  [key: string]: unknown;
}

export interface DailyReport {
  report_date: string;
  overall_headline: string;
  plain_english_summary: string;
  sections: DailySection[];
  diagnostic_hints: string[];
  generated_at_iso?: string | null;
  [key: string]: unknown;
}

export async function fetchDailyReport(
  date: string,
): Promise<DailyReport | null> {
  const path =
    date === "today"
      ? "/daily-report/today"
      : `/daily-report/${encodeURIComponent(date)}`;
  try {
    return await apiGet<DailyReport>(path);
  } catch {
    return null;
  }
}

// ── Forex Fury promote ──

export interface ForexFuryPromoteResponse {
  status: string;
  lead_id?: string;
  candidate_id: string;
  message?: string;
  [key: string]: unknown;
}

export interface ForexFuryPromotionStatusResponse {
  candidate_id: string;
  promoted: boolean;
  lead_id?: string | null;
  message?: string;
  [key: string]: unknown;
}

export interface ApiPostError {
  status: number;
  message: string;
  payload: unknown;
}

function toPostError(err: unknown): ApiPostError {
  const anyErr = err as { status?: number; message?: string; payload?: unknown };
  return {
    status: anyErr?.status ?? 0,
    message: anyErr?.message ?? "Request failed",
    payload: anyErr?.payload ?? null,
  };
}

export async function promoteForexFuryCandidate(
  candidateId: string,
  allowUnverified = false,
): Promise<{ ok: true; data: ForexFuryPromoteResponse } | { ok: false; error: ApiPostError }> {
  try {
    const data = await apiPostJson<
      ForexFuryPromoteResponse,
      { candidate_id: string; allow_unverified: boolean }
    >("/forex-fury-promote/promote", {
      candidate_id: candidateId,
      allow_unverified: allowUnverified,
    });
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: toPostError(err) };
  }
}

export async function getForexFuryPromotionStatus(
  candidateId: string,
): Promise<ForexFuryPromotionStatusResponse | null> {
  try {
    return await apiGet<ForexFuryPromotionStatusResponse>(
      `/forex-fury-promote/promotion-status?candidate_id=${encodeURIComponent(candidateId)}`,
    );
  } catch {
    return null;
  }
}

// ── Strategy Dev actions ──

export type StrategyDevAction = "promote" | "demote" | "reject" | "archive" | "review";

export interface StrategyActionResponse {
  status: string;
  strategy_id: string;
  action: StrategyDevAction;
  // Success payload is asdict(StrategyActionResult): previous_stage/next_stage.
  next_stage?: string;
  previous_stage?: string;
  // Present on the rejection (400) error detail, not the success payload.
  current_stage?: string;
  message?: string;
  [key: string]: unknown;
}

export async function applyStrategyDevAction(
  strategyId: string,
  action: StrategyDevAction,
  note?: string,
): Promise<{ ok: true; data: StrategyActionResponse } | { ok: false; error: ApiPostError }> {
  try {
    const body: { strategy_id: string; note?: string } = { strategy_id: strategyId };
    if (note && note.trim().length > 0) body.note = note.trim();
    const data = await apiPostJson<StrategyActionResponse, typeof body>(
      `/strategy-dev-actions/${action}`,
      body,
    );
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: toPostError(err) };
  }
}

// ── Portfolio Risk Monitoring ──

export interface SymbolRiskExposureItem {
  symbol: string;
  direction: string;
  open_position_count: number;
  total_lots: number;
  total_floating_pnl: number;
  largest_position_lots: number;
}

export interface PortfolioRiskResponse {
  snapshot_at_iso: string;
  open_position_count: number;
  total_floating_pnl: number;
  total_exposure_lots: number;
  largest_symbol_exposure: SymbolRiskExposureItem | null;
  largest_floating_pnl_loss: number;
  largest_floating_pnl_gain: number;
  by_symbol: SymbolRiskExposureItem[];
  concentration_pct: number;
  account_balance: number | null;
  account_equity: number | null;
  account_margin: number | null;
  account_free_margin: number | null;
  margin_utilization_pct: number | null;
  plain_english_summary: string;
  diagnostic_hints: string[];
}

export async function fetchPortfolioRisk(): Promise<PortfolioRiskResponse | null> {
  try {
    return await apiGet<PortfolioRiskResponse>("/risk-monitoring/portfolio");
  } catch {
    return null;
  }
}

// ── Web Push Notification Subscriptions ──

export interface PushSubscriptionItem {
  endpoint: string;
  keys: { p256dh: string | null; auth: string | null };
  label: string;
  created_at_iso: string;
}

export interface PushSubscriptionsResponse {
  subscriptions: PushSubscriptionItem[];
  total_subscriptions: number;
}

export interface PushTestResult {
  endpoint: string;
  success: boolean;
  status_code: number | null;
  error_message: string | null;
}

export interface PushTestResponse {
  results: PushTestResult[];
}

export async function fetchPushSubscriptions(): Promise<PushSubscriptionsResponse | null> {
  try {
    return await apiGet<PushSubscriptionsResponse>("/notifications/subscriptions");
  } catch {
    return null;
  }
}

export interface WebPushSubscribeBody {
  endpoint: string;
  keys: { p256dh: string; auth: string };
  label?: string;
}

export async function subscribeWebPush(
  body: WebPushSubscribeBody,
): Promise<
  | { ok: true; data: { subscription: PushSubscriptionItem; total_subscriptions: number } }
  | { ok: false; error: ApiPostError }
> {
  try {
    const data = await apiPostJson<
      { subscription: PushSubscriptionItem; total_subscriptions: number },
      WebPushSubscribeBody
    >("/notifications/subscribe", body);
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: toPostError(err) };
  }
}

export async function unsubscribeWebPush(
  endpoint: string,
): Promise<{ ok: true } | { ok: false; error: ApiPostError }> {
  try {
    await apiPostJson<unknown, { endpoint: string }>("/notifications/unsubscribe", { endpoint });
    return { ok: true };
  } catch (err) {
    return { ok: false, error: toPostError(err) };
  }
}

export async function testPushAll(
  label?: string,
): Promise<{ ok: true; data: PushTestResponse } | { ok: false; error: ApiPostError }> {
  try {
    const body: { label?: string } = {};
    if (label && label.trim().length > 0) body.label = label.trim();
    const data = await apiPostJson<PushTestResponse, typeof body>(
      "/notifications/test-push",
      body,
    );
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: toPostError(err) };
  }
}

// ── Webhook Notification Subscriptions ──

export interface WebhookSubscriptionItem {
  webhook_url: string;
  label: string;
  created_at_iso: string;
  last_used_at_iso: string | null;
}

export interface WebhookSubscriptionsResponse {
  subscriptions: WebhookSubscriptionItem[];
  total_subscriptions: number;
}

export interface WebhookTestResult {
  webhook_url: string;
  success: boolean;
  status_code: number | null;
  error_message: string | null;
}

export interface WebhookTestResponse {
  results: WebhookTestResult[];
}

export async function fetchWebhookSubscriptions(): Promise<WebhookSubscriptionsResponse | null> {
  try {
    return await apiGet<WebhookSubscriptionsResponse>("/webhook-notifications/subscriptions");
  } catch {
    return null;
  }
}

export async function subscribeWebhook(
  webhookUrl: string,
  label: string,
): Promise<
  | { ok: true; data: { subscription: WebhookSubscriptionItem; total_subscriptions: number } }
  | { ok: false; error: ApiPostError }
> {
  try {
    const body = { webhook_url: webhookUrl, label };
    const data = await apiPostJson<
      { subscription: WebhookSubscriptionItem; total_subscriptions: number },
      typeof body
    >("/webhook-notifications/subscribe", body);
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: toPostError(err) };
  }
}

export async function unsubscribeWebhook(
  webhookUrl: string,
): Promise<{ ok: true } | { ok: false; error: ApiPostError }> {
  try {
    await apiPostJson<unknown, { webhook_url: string }>(
      "/webhook-notifications/unsubscribe",
      { webhook_url: webhookUrl },
    );
    return { ok: true };
  } catch (err) {
    return { ok: false, error: toPostError(err) };
  }
}

export async function testWebhookAll(
  label?: string,
  title?: string,
  body?: string,
): Promise<{ ok: true; data: WebhookTestResponse } | { ok: false; error: ApiPostError }> {
  try {
    const requestBody: { label?: string; payload?: Record<string, unknown> } = {};
    if (label && label.trim().length > 0) requestBody.label = label.trim();
    if (title || body) {
      requestBody.payload = {
        title: title || "CAS Forex",
        body: body || "Test webhook from the cockpit (observational).",
      };
    }
    const data = await apiPostJson<WebhookTestResponse, typeof requestBody>(
      "/webhook-notifications/test",
      requestBody,
    );
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: toPostError(err) };
  }
}

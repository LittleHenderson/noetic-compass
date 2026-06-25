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

async function apiDelete<T>(path: string): Promise<T> {
  const res = await fetch(`${getApiBase()}${path}`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    signal: AbortSignal.timeout(8000),
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
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

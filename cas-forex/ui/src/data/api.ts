/* ── CAS Forex — API Client ── */

import type {
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
  TerminalReceiptArchiveAction,
  TerminalReceiptRecoveryRefreshAction,
  TerminalReceiptRecoveryPacket,
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
  AutoHaltReport,
  BrokerTruthMonitorStatus,
  BrokerTruthMonitorSupervisorStatus,
  BrokerTruthRecoveryPacket,
  LiveMoneyProgressionPacket,
  OrderAttemptAuditAttempt,
  OrderAttemptAuditStatus,
  OrderAttemptRecoveryPacket,
  PayoutRecoveryAttempt,
  PayoutRecoveryStatus,
  BrokerRealityReview,
  LivePilotPolicy,
  LiveOrderDryRunLatest,
  LiveOrderDryRunReport,
  LiveOrderDryRunReview,
  CompoundAddOrderDryRunLatest,
  CompoundAddOrderDryRunReview,
  CompoundAddDispatchHandoffStatus,
  WasteEntryDispatchHandoffStatus,
  WasteEntryPilotPromotionStatus,
  WasteDirectionReviewPacket,
  WasteDirectionLearningLedger,
  WasteDirectionOutcomeBinding,
  WastePaperSampleCollector,
  WastePaperSampleCollectorScheduler,
  WasteAdaptationPromotionRule,
  WasteAdaptationPlan,
  WasteAdaptationApplyPreview,
  WasteAdaptationOwnerReview,
  WasteAdaptationPaperApply,
  LiveRecoveryReport,
  MT5MarketDataDiagnostic,
  WasteRealCandleProbe,
} from "../types/evidence";
import { apiDelete, apiGet, apiPost, apiPostJson, getApiBase } from "./apiCore";

export { API_BASE_STORAGE_KEY, getApiBase, resetApiBase, setApiBase } from "./apiCore";

type WasteStageProbeModule = typeof import("./wasteStageProbe");

let wasteStageProbePromise: Promise<WasteStageProbeModule> | null = null;

function loadWasteStageProbe(): Promise<WasteStageProbeModule> {
  wasteStageProbePromise ??= import("./wasteStageProbe");
  return wasteStageProbePromise;
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

// ── Owner proof control (advance the proof in-app + profitability thresholds) ──

export interface ProofControlState {
  report_kind?: string;
  proof: {
    required_trading_days: number;
    completed_trading_days: number;
    broker_verified_days: number;
    net_pnl_usd: number;
    max_drawdown_pct: number;
    days_with_trades: number;
    min_trade_days_required: number;
    profit_passed: boolean;
    passed: boolean;
    failure_reasons: string[];
  };
  thresholds: {
    require_net_positive: boolean;
    min_net_pnl_usd: number;
    max_drawdown_pct: number;
    min_trade_days_fraction: number;
    seed_capital_usd: number;
    overridden_fields?: string[];
    note?: string;
  };
  auto_runner: {
    running: boolean;
    check_interval_seconds: number;
    last_check_iso: string | null;
    last_run_iso: string | null;
    last_recorded_date: string | null;
    last_status: string | null;
    last_detail: string | null;
    last_error: string | null;
    days_recorded_this_session: number;
    note?: string;
  };
  run_result?: {
    status: string;
    date?: string;
    detail?: string;
    reasons?: string[];
  };
  error?: string;
  claim_boundary?: string;
}

export type ProofThresholdPatch = Partial<{
  require_net_positive: boolean;
  min_net_pnl_usd: number;
  max_drawdown_pct: number;
  min_trade_days_fraction: number;
  seed_capital_usd: number;
}>;

export async function fetchProofControl(): Promise<ProofControlState | null> {
  try {
    return await apiGet<ProofControlState>("/proof-control/state");
  } catch {
    return null;
  }
}

// Recording a proof day reads the demo broker terminal, which can be slow; give
// it a generous timeout rather than the shared 8s POST helper.
export async function runProofDayNow(): Promise<ProofControlState> {
  const res = await fetch(`${getApiBase()}/proof-control/run-now`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    signal: AbortSignal.timeout(90_000),
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return (await res.json()) as ProofControlState;
}

export async function startProofAutoRunner(
  checkIntervalSeconds = 1800,
): Promise<ProofControlState> {
  return apiPostJson<ProofControlState, { check_interval_seconds: number }>(
    "/proof-control/auto/start",
    { check_interval_seconds: checkIntervalSeconds },
  );
}

export async function stopProofAutoRunner(): Promise<ProofControlState> {
  return apiPost<ProofControlState>("/proof-control/auto/stop");
}

export async function updateProofThresholds(
  patch: ProofThresholdPatch,
): Promise<ProofControlState> {
  return apiPostJson<ProofControlState, ProofThresholdPatch>("/proof-control/thresholds", patch);
}

export async function resetProofThresholds(): Promise<ProofControlState> {
  return apiPost<ProofControlState>("/proof-control/thresholds/reset");
}

// ── Owner MT4 mailbox route (stable file-based real-order path) ──

export interface MT4ControlState {
  report_kind?: string;
  enabled: boolean;
  mailbox_dir: string;
  link_status: "LIVE" | "STALE" | "NO_HEARTBEAT";
  heartbeat: {
    present: boolean;
    fresh: boolean;
    state: string | null;
    account_id_hash: string | null;
    server: string | null;
    live_trading_allowed: boolean | null;
    time: string | null;
    age_seconds: number | null;
  };
  note?: string;
  claim_boundary?: string;
  error?: string;
}

export async function fetchMt4Control(): Promise<MT4ControlState | null> {
  try {
    return await apiGet<MT4ControlState>("/mt4-bridge/state");
  } catch {
    return null;
  }
}

export async function updateMt4Control(
  patch: Partial<{ enabled: boolean; mailbox_dir: string }>,
): Promise<MT4ControlState> {
  return apiPostJson<MT4ControlState, typeof patch>("/mt4-bridge/update", patch);
}

export async function resetMt4Control(): Promise<MT4ControlState> {
  return apiPost<MT4ControlState>("/mt4-bridge/reset");
}

// One-tap: route the dispatch loop through the chosen broker platform.
export async function setDispatchPlatform(
  platform: "auto" | "mt5" | "mt4" | "simulated",
): Promise<{ platform?: string }> {
  return apiPostJson<{ platform?: string }, { platform: string }>("/broker-control/update", {
    platform,
  });
}

export interface BrokerControlState {
  report_kind?: string;
  platform?: string;
  strictness?: string;
}

export async function fetchBrokerControl(): Promise<BrokerControlState | null> {
  try {
    return await apiGet<BrokerControlState>("/broker-control/state");
  } catch {
    return null;
  }
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
  advisory_requirements?: string[];
  next_action: string;
}

export interface OwnerAuthorityModel {
  authority: string;
  authority_controls: string[];
  owner_controls_are_final_authority: boolean;
  metrics_and_ai_are_advisory_only: boolean;
  metrics_and_ai_can_veto_owner_authority: boolean;
  technical_action_time_checks_still_required: boolean;
  advisory_inputs: string[];
  action_time_requirements: string[];
  statement: string;
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
    owner_authority_boundary?: string;
    advisory_only_inputs?: string[];
    action_time_requirements?: string[];
    owner_controls_are_final_authority?: boolean;
    metrics_and_ai_can_veto_owner_authority?: boolean;
  };
  owner_authority_model?: OwnerAuthorityModel;
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
  advisory_requirements?: string[];
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
  owner_authority_model?: OwnerAuthorityModel;
  caveats: string[];
  override_state_path?: string | null;
  override_count?: number;
  persisted?: boolean;
}

export type AuthorizationPatch = Partial<{
  personal_account_ack: boolean;
  no_pooled_capital_ack: boolean;
  live_mode: boolean;
  prefer_mt5: boolean;
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

// ── Verified profit sweep (broker-confirmed net winnings only) ──

export interface VerifiedProfitSweepSettings {
  sweep_pct: number;
  tax_reserve_pct: number;
  min_sweep_usd: number;
  destination_id?: string | null;
  allow_principal_sweep: boolean;
  policy_id: string;
}

export interface VerifiedProfitSweepWinnings {
  ledger_mode: string;
  live_money_authorized: boolean;
  verified_closed_trade_count: number;
  verified_profit_usd: number;
  verified_loss_usd: number;
  verified_costs_usd: number;
  net_verified_winnings_usd: number;
  sweepable_winnings_usd: number;
  ignored_unverified_rows: number;
  claim_status: string;
  reason: string;
}

export interface VerifiedProfitSweepPreview {
  report_kind?: string;
  settings: VerifiedProfitSweepSettings;
  winnings: VerifiedProfitSweepWinnings;
  tax_reserve_usd: number;
  post_tax_winnings_usd: number;
  sweep_amount_usd: number;
  keep_in_broker_usd: number;
  principal_sweep_usd: number;
  status: string;
  reason: string;
  payout_gate: RuntimeGateDecision;
  hard_rule?: string;
}

export interface VerifiedProfitSweepAuditRecord {
  audit_id?: string;
  action: string;
  timestamp: string;
  payload?: unknown;
}

export interface VerifiedProfitSweepLiveRecoveryGate {
  report_kind?: string | null;
  recovery_status?: string | null;
  recovery_clear_for_live: boolean;
  requires_recovery_review?: boolean;
  evidence_ready_for_owner_accept?: boolean;
  missing_requirements?: string[];
  current_fingerprint?: string | null;
  order_attempt_summary?: {
    unresolved_real_attempt_count?: number;
    has_unresolved_real_attempt?: boolean;
  };
  next_action?: string | null;
}

export interface VerifiedProfitSweepPolicy {
  report_kind?: string;
  settings: VerifiedProfitSweepSettings;
  latest_audit?: VerifiedProfitSweepAuditRecord | null;
  audit?: VerifiedProfitSweepAuditRecord | null;
  note?: string;
}

export type VerifiedProfitSweepPolicyUpdate = Partial<
  Pick<
    VerifiedProfitSweepSettings,
    "sweep_pct" | "tax_reserve_pct" | "min_sweep_usd" | "destination_id" | "allow_principal_sweep"
  >
>;

export interface VerifiedProfitSweepRequestResult {
  status: string;
  detail?: string;
  preview: VerifiedProfitSweepPreview;
  movement?: { status: string; provider_receipt?: unknown | null; [key: string]: unknown };
  payout_attempt?: PayoutRecoveryAttempt | null;
  live_recovery?: VerifiedProfitSweepLiveRecoveryGate | null;
  audit?: VerifiedProfitSweepAuditRecord;
}

export async function fetchVerifiedProfitSweepPolicy(): Promise<VerifiedProfitSweepPolicy | null> {
  try { return await apiGet<VerifiedProfitSweepPolicy>("/money-movement/verified-profit-sweep/policy"); } catch { return null; }
}

export async function updateVerifiedProfitSweepPolicy(
  patch: VerifiedProfitSweepPolicyUpdate,
): Promise<VerifiedProfitSweepPolicy> {
  return apiPostJson<VerifiedProfitSweepPolicy, VerifiedProfitSweepPolicyUpdate>(
    "/money-movement/verified-profit-sweep/policy",
    patch,
  );
}

export async function fetchVerifiedProfitSweepState(): Promise<VerifiedProfitSweepPreview | null> {
  try { return await apiGet<VerifiedProfitSweepPreview>("/money-movement/verified-profit-sweep/state"); } catch { return null; }
}

export async function previewVerifiedProfitSweep(
  accountLedger: AccountLedgerState,
  settings?: VerifiedProfitSweepPolicyUpdate,
): Promise<VerifiedProfitSweepPreview> {
  return apiPostJson<VerifiedProfitSweepPreview, { account_ledger: AccountLedgerState; settings?: VerifiedProfitSweepPolicyUpdate }>(
    "/money-movement/verified-profit-sweep/preview",
    { account_ledger: accountLedger, settings },
  );
}

export async function requestVerifiedProfitSweepCurrent(
  settings?: VerifiedProfitSweepPolicyUpdate,
  confirm = false,
): Promise<VerifiedProfitSweepRequestResult> {
  const q = confirm ? "?confirm=true" : "";
  return apiPostJson<VerifiedProfitSweepRequestResult, VerifiedProfitSweepPolicyUpdate>(
    `/money-movement/verified-profit-sweep/request-current${q}`,
    settings ?? {},
  );
}

export async function fetchPayoutRecoveryStatus(): Promise<PayoutRecoveryStatus | null> {
  try { return await apiGet<PayoutRecoveryStatus>("/money-movement/verified-profit-sweep/payout-recovery"); } catch { return null; }
}

export async function resolvePayoutAttempt(
  idempotency_key: string,
  owner_status: "SETTLED" | "FAILED" | "BLOCKED",
  provider_reference = "",
  notes = "",
): Promise<{ report_kind: string; attempt: PayoutRecoveryAttempt; status: string }> {
  return apiPostJson<
    { report_kind: string; attempt: PayoutRecoveryAttempt; status: string },
    { idempotency_key: string; owner_status: string; provider_reference: string; notes: string }
  >(
    "/money-movement/verified-profit-sweep/payout-recovery/resolve",
    { idempotency_key, owner_status, provider_reference, notes },
  );
}

// ── Trading Windows cockpit (live-ish candles + quote per symbol) ──

export type { AutoHaltReport };
export type { BrokerTruthMonitorStatus };
export type { BrokerTruthMonitorSupervisorStatus };
export type { BrokerTruthRecoveryPacket };
export type { LiveMoneyProgressionPacket };
export type { OrderAttemptAuditAttempt };
export type { OrderAttemptAuditStatus };
export type { OrderAttemptRecoveryPacket };
export type { TerminalReceiptArchiveAction };
export type { TerminalReceiptRecoveryRefreshAction };
export type { TerminalReceiptRecoveryPacket };
export type { PayoutRecoveryStatus };
export type { BrokerRealityReview };
export type { LivePilotPolicy };
export type { LiveOrderDryRunLatest };
export type { LiveOrderDryRunReport };
export type { LiveOrderDryRunReview };
export type { CompoundAddOrderDryRunLatest };
export type { CompoundAddOrderDryRunReview };
export type { CompoundAddDispatchHandoffStatus };
export type { WasteEntryDispatchHandoffStatus };
export type { WasteEntryPilotPromotionStatus };
export type { WasteDirectionReviewPacket };
export type { WasteDirectionLearningLedger };
export type { WasteDirectionOutcomeBinding };
export type { WastePaperSampleCollector };
export type { WastePaperSampleCollectorScheduler };
export type { WasteAdaptationPromotionRule };
export type { WasteAdaptationPlan };
export type { WasteAdaptationApplyPreview };
export type { WasteAdaptationOwnerReview };
export type { WasteAdaptationPaperApply };
export type { LiveRecoveryReport };
export type { MT5MarketDataDiagnostic };
export type { WasteRealCandleProbe };

export interface LiveOrderDryRunRequest {
  order_id: string;
  decision_ref?: string | null;
  symbol: string;
  direction: string;
  volume: number;
  price?: number;
  stop_loss: number;
  take_profit: number;
  expected_loss_usd?: number | null;
  comment?: string;
  live_telemetry?: Record<string, unknown> | null;
  account_snapshot?: Record<string, unknown> | null;
  equity_peak?: number | null;
}

export interface WasteRealCandleProbeDryRunRequest {
  volume: number;
  order_id?: string | null;
  expected_loss_usd?: number | null;
  live_telemetry?: Record<string, unknown> | null;
  account_snapshot?: Record<string, unknown> | null;
  equity_peak?: number | null;
}

export interface WasteAdaptationOwnerReviewRequest {
  decision: string;
  notes?: string | null;
}

export interface WasteAdaptationPaperApplyRequest {
  notes?: string | null;
}

export async function fetchLatestLiveOrderDryRun(): Promise<LiveOrderDryRunLatest | null> {
  try { return await apiGet<LiveOrderDryRunLatest>("/live-order-dry-run/latest"); } catch { return null; }
}

export async function runLiveOrderDryRun(body: LiveOrderDryRunRequest): Promise<LiveOrderDryRunReport> {
  return apiPostJson<LiveOrderDryRunReport, LiveOrderDryRunRequest>("/live-order-dry-run/order", body);
}

export async function fetchWasteEntryDispatchHandoffStatus(): Promise<WasteEntryDispatchHandoffStatus | null> {
  try {
    return await apiGet<WasteEntryDispatchHandoffStatus>("/live-order-dry-run/waste-entry-order/dispatch-handoff");
  } catch {
    return null;
  }
}

export async function fetchWasteEntryPilotPromotionStatus(): Promise<WasteEntryPilotPromotionStatus | null> {
  try {
    return await apiGet<WasteEntryPilotPromotionStatus>("/live-order-dry-run/waste-entry-order/pilot-promotion");
  } catch {
    return null;
  }
}

export async function fetchWasteDirectionReviewPacket(): Promise<WasteDirectionReviewPacket | null> {
  try {
    return await apiGet<WasteDirectionReviewPacket>("/waste-loop-control/direction-review");
  } catch {
    return null;
  }
}

export async function fetchWasteDirectionLearningLedger(): Promise<WasteDirectionLearningLedger | null> {
  try {
    return await apiGet<WasteDirectionLearningLedger>("/waste-loop-control/direction-learning");
  } catch {
    return null;
  }
}

export async function fetchWasteDirectionOutcomeBinding(): Promise<WasteDirectionOutcomeBinding | null> {
  try {
    return await apiGet<WasteDirectionOutcomeBinding>("/waste-loop-control/direction-outcome-binding");
  } catch {
    return null;
  }
}

export async function fetchWastePaperSampleCollector(): Promise<WastePaperSampleCollector | null> {
  try {
    return await apiGet<WastePaperSampleCollector>("/waste-loop-control/paper-sample-collector");
  } catch {
    return null;
  }
}

export interface WastePaperSampleCollectorSchedulerRequest {
  interval_seconds?: number;
  run_market_diagnostic?: boolean;
  run_real_candle_probe?: boolean;
  run_deal_history_ingest?: boolean;
  symbol?: string | null;
  timeframe?: string;
  bars?: number;
  max_pairs?: number;
  scan_candidates?: boolean;
  max_scan_candidates?: number;
}

export async function fetchWastePaperSampleCollectorScheduler(): Promise<WastePaperSampleCollectorScheduler | null> {
  try {
    return await apiGet<WastePaperSampleCollectorScheduler>("/waste-loop-control/paper-sample-collector/scheduler");
  } catch {
    return null;
  }
}

export async function runWastePaperSampleCollectorSchedulerOnce(
  body: WastePaperSampleCollectorSchedulerRequest = {},
): Promise<WastePaperSampleCollectorScheduler> {
  return apiPostJson<WastePaperSampleCollectorScheduler, WastePaperSampleCollectorSchedulerRequest>(
    "/waste-loop-control/paper-sample-collector/scheduler/run-once",
    body,
    75_000,
  );
}

export async function startWastePaperSampleCollectorScheduler(
  body: WastePaperSampleCollectorSchedulerRequest = {},
): Promise<WastePaperSampleCollectorScheduler> {
  return apiPostJson<WastePaperSampleCollectorScheduler, WastePaperSampleCollectorSchedulerRequest>(
    "/waste-loop-control/paper-sample-collector/scheduler/start",
    body,
    30_000,
  );
}

export async function stopWastePaperSampleCollectorScheduler(): Promise<WastePaperSampleCollectorScheduler> {
  return apiPostJson<WastePaperSampleCollectorScheduler, Record<string, never>>(
    "/waste-loop-control/paper-sample-collector/scheduler/stop",
    {},
  );
}

export async function fetchWasteAdaptationPromotionRule(): Promise<WasteAdaptationPromotionRule | null> {
  try {
    return await apiGet<WasteAdaptationPromotionRule>("/waste-loop-control/adaptation-promotion-rule");
  } catch {
    return null;
  }
}

export async function fetchWasteAdaptationPlan(): Promise<WasteAdaptationPlan | null> {
  try {
    return await apiGet<WasteAdaptationPlan>("/waste-loop-control/adaptation-plan");
  } catch {
    return null;
  }
}

export async function fetchWasteAdaptationApplyPreview(): Promise<WasteAdaptationApplyPreview | null> {
  try {
    return await apiGet<WasteAdaptationApplyPreview>("/waste-loop-control/adaptation-apply-preview");
  } catch {
    return null;
  }
}

export async function fetchWasteAdaptationOwnerReview(): Promise<WasteAdaptationOwnerReview | null> {
  try {
    return await apiGet<WasteAdaptationOwnerReview>("/waste-loop-control/adaptation-owner-review");
  } catch {
    return null;
  }
}

export async function recordWasteAdaptationOwnerReview(
  body: WasteAdaptationOwnerReviewRequest,
  confirmOwnerReview = false,
  confirmOwnerAccept = false,
): Promise<WasteAdaptationOwnerReview> {
  const params = new URLSearchParams();
  if (confirmOwnerReview) params.set("confirm_owner_review", "true");
  if (confirmOwnerAccept) params.set("confirm_owner_accept", "true");
  const query = params.toString();
  return apiPostJson<WasteAdaptationOwnerReview, WasteAdaptationOwnerReviewRequest>(
    `/waste-loop-control/adaptation-owner-review/record${query ? `?${query}` : ""}`,
    body,
  );
}

export async function resetWasteAdaptationOwnerReview(reason = "OWNER_RESET"): Promise<WasteAdaptationOwnerReview> {
  return apiPostJson<WasteAdaptationOwnerReview, Record<string, never>>(
    `/waste-loop-control/adaptation-owner-review/reset?reason=${encodeURIComponent(reason)}`,
    {},
  );
}

export async function fetchWasteAdaptationPaperApply(): Promise<WasteAdaptationPaperApply | null> {
  try {
    return await apiGet<WasteAdaptationPaperApply>("/waste-loop-control/adaptation-paper-apply");
  } catch {
    return null;
  }
}

export async function recordWasteAdaptationPaperApply(
  body: WasteAdaptationPaperApplyRequest,
  confirmOwnerApply = false,
): Promise<WasteAdaptationPaperApply> {
  const query = confirmOwnerApply ? "?confirm_owner_apply=true" : "";
  return apiPostJson<WasteAdaptationPaperApply, WasteAdaptationPaperApplyRequest>(
    `/waste-loop-control/adaptation-paper-apply/record${query}`,
    body,
  );
}

export async function resetWasteAdaptationPaperApply(reason = "OWNER_RESET"): Promise<WasteAdaptationPaperApply> {
  return apiPostJson<WasteAdaptationPaperApply, Record<string, never>>(
    `/waste-loop-control/adaptation-paper-apply/reset?reason=${encodeURIComponent(reason)}`,
    {},
  );
}

export async function dispatchWasteEntryDispatchHandoff(
  notes = "",
  confirmOwnerDispatch = false,
  confirmLiveDispatch = false,
): Promise<WasteEntryDispatchHandoffStatus> {
  const q = confirmLiveDispatch ? "?confirm=true" : "";
  return apiPostJson<WasteEntryDispatchHandoffStatus, { confirm_owner_dispatch: boolean; notes: string }>(
    `/live-order-dry-run/waste-entry-order/dispatch-handoff/dispatch${q}`,
    { confirm_owner_dispatch: confirmOwnerDispatch, notes },
  );
}

export async function fetchLiveOrderDryRunReview(): Promise<LiveOrderDryRunReview | null> {
  try { return await apiGet<LiveOrderDryRunReview>("/live-order-dry-run/review"); } catch { return null; }
}

export async function acceptLiveOrderDryRunReview(
  notes = "",
  confirmOwnerAccept = false,
): Promise<LiveOrderDryRunReview> {
  const q = confirmOwnerAccept ? "?confirm_owner_accept=true" : "";
  return apiPostJson<LiveOrderDryRunReview, { notes: string }>(
    `/live-order-dry-run/review/accept${q}`,
    { notes },
  );
}

export async function resetLiveOrderDryRunReview(reason = "OWNER_RESET"): Promise<LiveOrderDryRunReview> {
  return apiPost<LiveOrderDryRunReview>(`/live-order-dry-run/review/reset?reason=${encodeURIComponent(reason)}`);
}

export async function fetchCompoundAddOrderDryRunLatest(): Promise<CompoundAddOrderDryRunLatest | null> {
  try {
    return await apiGet<CompoundAddOrderDryRunLatest>("/live-order-dry-run/compound-add-order/latest");
  } catch {
    return null;
  }
}

export async function fetchCompoundAddOrderDryRunReview(): Promise<CompoundAddOrderDryRunReview | null> {
  try {
    return await apiGet<CompoundAddOrderDryRunReview>("/live-order-dry-run/compound-add-order/review");
  } catch {
    return null;
  }
}

export async function fetchCompoundAddDispatchHandoffStatus(): Promise<CompoundAddDispatchHandoffStatus | null> {
  try {
    return await apiGet<CompoundAddDispatchHandoffStatus>("/live-order-dry-run/compound-add-order/dispatch-handoff");
  } catch {
    return null;
  }
}

export async function dispatchCompoundAddDispatchHandoff(
  notes = "",
  confirmOwnerDispatch = false,
  confirmLiveDispatch = false,
): Promise<CompoundAddDispatchHandoffStatus> {
  const q = confirmLiveDispatch ? "?confirm=true" : "";
  return apiPostJson<CompoundAddDispatchHandoffStatus, { confirm_owner_dispatch: boolean; notes: string }>(
    `/live-order-dry-run/compound-add-order/dispatch-handoff/dispatch${q}`,
    { confirm_owner_dispatch: confirmOwnerDispatch, notes },
  );
}

export async function acceptCompoundAddOrderDryRunReview(
  notes = "",
  confirmOwnerAccept = false,
): Promise<CompoundAddOrderDryRunReview> {
  const q = confirmOwnerAccept ? "?confirm_owner_accept=true" : "";
  return apiPostJson<CompoundAddOrderDryRunReview, { notes: string }>(
    `/live-order-dry-run/compound-add-order/review/accept${q}`,
    { notes },
  );
}

export async function resetCompoundAddOrderDryRunReview(reason = "OWNER_RESET"): Promise<CompoundAddOrderDryRunReview> {
  return apiPost<CompoundAddOrderDryRunReview>(
    `/live-order-dry-run/compound-add-order/review/reset?reason=${encodeURIComponent(reason)}`,
  );
}

export async function fetchAutoHaltStatus(): Promise<AutoHaltReport | null> {
  try { return await apiGet<AutoHaltReport>("/auto-halt/status"); } catch { return null; }
}

export async function clearAutoHalt(reason: string, confirmClear = false): Promise<AutoHaltReport> {
  const q = confirmClear ? "?confirm_clear=true" : "";
  return apiPostJson<AutoHaltReport, { reason: string }>(
    `/auto-halt/clear${q}`,
    { reason: reason.trim() || "OWNER_CLEAR" },
  );
}

export async function fetchBrokerTruthMonitorStatus(): Promise<BrokerTruthMonitorStatus | null> {
  try { return await apiGet<BrokerTruthMonitorStatus>("/broker-truth-monitor/status/fast"); } catch { return null; }
}

export async function fetchBrokerTruthRecoveryPacket(): Promise<BrokerTruthRecoveryPacket | null> {
  try { return await apiGet<BrokerTruthRecoveryPacket>("/broker-truth-monitor/recovery-packet"); } catch { return null; }
}

export async function fetchLiveMoneyProgressionPacket(refresh = false): Promise<LiveMoneyProgressionPacket | null> {
  const path = refresh ? "/live-money/progression-packet?refresh=true" : "/live-money/progression-packet/fast";
  try { return await apiGet<LiveMoneyProgressionPacket>(path, refresh ? 20_000 : 8_000); } catch { return null; }
}

export async function startBrokerTruthMonitor(intervalSeconds = 30): Promise<BrokerTruthMonitorStatus> {
  return apiPostJson<BrokerTruthMonitorStatus, { interval_seconds: number }>(
    "/broker-truth-monitor/start",
    { interval_seconds: intervalSeconds },
  );
}

export async function stopBrokerTruthMonitor(): Promise<BrokerTruthMonitorStatus> {
  return apiPost<BrokerTruthMonitorStatus>("/broker-truth-monitor/stop");
}

export async function runBrokerTruthMonitorOnce(): Promise<BrokerTruthMonitorStatus> {
  return apiPost<BrokerTruthMonitorStatus>("/broker-truth-monitor/run-once");
}

export async function recoverBrokerTruthMonitorSupervisor(confirm = true): Promise<BrokerTruthMonitorSupervisorStatus> {
  const q = confirm ? "?confirm=true" : "";
  return apiPost<BrokerTruthMonitorSupervisorStatus>(`/broker-truth-monitor/supervisor/recover${q}`);
}

export type BrokerRealityUpdate = Partial<
  Pick<
    BrokerRealityReview,
    | "broker_id"
    | "broker_entity"
    | "withdrawal_minimum"
    | "withdrawal_timing"
    | "kyc_requirements"
    | "withdrawal_fees"
    | "currency_conversion"
    | "automation_tos"
    | "automation_allowed_by_owner_review"
    | "source_urls"
    | "notes"
    | "review_valid_days"
  >
> & Partial<Record<
  | "withdrawal_minimum_reviewed"
  | "withdrawal_timing_reviewed"
  | "kyc_requirements_reviewed"
  | "withdrawal_fees_reviewed"
  | "currency_conversion_reviewed"
  | "automation_tos_reviewed"
  | "broker_entity_reviewed"
  | "owner_accepts_broker_terms",
  boolean
>>;

export async function fetchBrokerRealityReview(brokerId?: string): Promise<BrokerRealityReview | null> {
  const q = brokerId ? `?broker_id=${encodeURIComponent(brokerId)}` : "";
  try { return await apiGet<BrokerRealityReview>(`/broker-reality/review${q}`); } catch { return null; }
}

export async function updateBrokerRealityReview(
  patch: BrokerRealityUpdate,
  confirmOwnerAccept = false,
): Promise<BrokerRealityReview> {
  const q = confirmOwnerAccept ? "?confirm_owner_accept=true" : "";
  return apiPostJson<BrokerRealityReview, BrokerRealityUpdate>(`/broker-reality/review${q}`, patch);
}

export async function resetBrokerRealityReview(brokerId?: string): Promise<BrokerRealityReview> {
  const q = brokerId ? `?broker_id=${encodeURIComponent(brokerId)}` : "";
  return apiPost<BrokerRealityReview>(`/broker-reality/reset${q}`);
}

export type LivePilotUpdate = Partial<
  Pick<
    LivePilotPolicy,
    | "allowed_symbols"
    | "max_trade_lots"
    | "max_open_live_lots"
    | "max_live_trade_count"
    | "max_daily_loss_usd"
    | "max_total_loss_usd"
    | "max_pilot_days"
    | "notes"
  >
> & Partial<Record<
  | "owner_understands_real_money_risk"
  | "owner_confirms_small_amounts_only"
  | "owner_confirms_no_scaling_without_review"
  | "owner_confirms_emergency_stop_ready",
  boolean
>>;

export async function fetchLivePilotPolicy(): Promise<LivePilotPolicy | null> {
  try { return await apiGet<LivePilotPolicy>("/live-pilot/policy"); } catch { return null; }
}

export async function updateLivePilotPolicy(
  patch: LivePilotUpdate,
  confirmOwnerAccept = false,
): Promise<LivePilotPolicy> {
  const q = confirmOwnerAccept ? "?confirm_owner_accept=true" : "";
  return apiPostJson<LivePilotPolicy, LivePilotUpdate>(`/live-pilot/policy${q}`, patch);
}

export async function resetLivePilotPolicy(): Promise<LivePilotPolicy> {
  return apiPost<LivePilotPolicy>("/live-pilot/reset");
}

export async function fetchLiveRecoveryStatus(): Promise<LiveRecoveryReport | null> {
  try { return await apiGet<LiveRecoveryReport>("/live-recovery/status"); } catch { return null; }
}

export async function fetchOrderAttemptAudit(): Promise<OrderAttemptAuditStatus | null> {
  try { return await apiGet<OrderAttemptAuditStatus>("/order-dispatch/audit"); } catch { return null; }
}

export async function fetchOrderAttemptRecoveryPacket(): Promise<OrderAttemptRecoveryPacket | null> {
  try { return await apiGet<OrderAttemptRecoveryPacket>("/order-dispatch/audit/recovery-packet"); } catch { return null; }
}

export async function reconcileUnresolvedOrderAttempt(
  attemptId: string,
  notes = "",
  confirmOwnerReconcile = false,
): Promise<OrderAttemptAuditStatus> {
  const q = confirmOwnerReconcile ? "?confirm_owner_reconcile=true" : "";
  return apiPostJson<OrderAttemptAuditStatus, { attempt_id: string; notes: string }>(
    `/order-dispatch/audit/reconcile-unresolved${q}`,
    { attempt_id: attemptId, notes },
  );
}

export async function acceptLiveRecovery(notes: string, confirmOwnerAccept = false): Promise<LiveRecoveryReport> {
  const q = confirmOwnerAccept ? "?confirm_owner_accept=true" : "";
  return apiPostJson<LiveRecoveryReport, { notes: string }>(
    `/live-recovery/accept${q}`,
    { notes },
  );
}

export async function resetLiveRecovery(reason = "OWNER_RESET"): Promise<LiveRecoveryReport> {
  return apiPost<LiveRecoveryReport>(`/live-recovery/reset?reason=${encodeURIComponent(reason)}`);
}

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

export interface WasteLoopCandidate {
  symbol?: string | null;
  timeframe?: string | null;
  direction?: string | null;
  entry?: number | null;
  stop_loss?: number | null;
  take_profit?: number | null;
  signal_strength?: number | null;
  regime?: string | null;
  decision_ref?: string | null;
  entry_pair_count?: number;
  directional_hypothesis?: Record<string, unknown> | null;
  market_state_meta?: Record<string, unknown> | null;
}

export interface WasteLoopDurableCycle {
  report_kind?: string;
  decision?: string;
  reason?: string;
  stage?: string;
  mode?: string;
  running?: boolean;
  watch_state?: Record<string, unknown> | null;
  analysis?: Record<string, unknown> | null;
  candidate?: WasteLoopCandidate | null;
  edge?: Record<string, unknown> | null;
  [key: string]: unknown;
}

export interface WasteLoopState {
  report_kind?: string;
  running: boolean;
  interval_seconds?: number;
  cycles_run?: number;
  cycles_idle?: number;
  stage?: string;
  current_stage?: string;
  mode?: string;
  status?: string;
  last_run_iso?: string | null;
  last_reason?: string | null;
  last_decision?: unknown;
  detail?: string;
  note?: string;
  durable_cycle?: WasteLoopDurableCycle | null;
  durable_cycle_status?: Record<string, unknown> | null;
  supervisor?: LoopSupervisorStatus;
}

export interface WasteLoopStageState {
  report_kind?: string;
  running?: boolean;
  stage?: string;
  current_stage?: string;
  mode?: string;
  cycles_run?: number;
  last_reason?: string | null;
  last_run_iso?: string | null;
}

export interface WasteRealCandleProbeRequest {
  symbol?: string | null;
  timeframe?: string;
  bars?: number;
  max_pairs?: number;
}

export interface MT5MarketDataDiagnosticRequest {
  symbols?: string[] | null;
  timeframe?: string;
  bars?: number;
}

export interface WasteLoopStartRequest {
  interval_seconds: number;
}

export interface LoopSupervisorLease {
  owner_id?: string;
  status?: string;
  mode?: string;
  interval_seconds?: number;
  acquired_at?: string;
  last_heartbeat_at?: string;
  expires_at?: string;
  [key: string]: unknown;
}

export interface LoopSupervisorStatus {
  report_kind: string;
  status?: string;
  generated_at?: string;
  desired_running: boolean;
  active_lease?: LoopSupervisorLease | null;
  active_lease_is_fresh: boolean;
  owned_by_this_process: boolean;
  local_owner_id: string;
  local_running: boolean;
  stop_requested_at?: string | null;
  stop_requested_by?: string | null;
  state_path?: string;
  audit_path?: string;
  claim_boundary?: string;
  next_action: string;
  recovery?: Record<string, unknown>;
}

export async function fetchWasteLoopStatus(): Promise<WasteLoopState | null> {
  try { return await apiGet<WasteLoopState>("/waste-loop-control/status/fast"); } catch { return null; }
}

export async function fetchWasteLoopStage(): Promise<WasteLoopStageState | null> {
  const { fetchWasteStageProbe } = await loadWasteStageProbe();
  return await fetchWasteStageProbe({ timeoutMs: 6_000, maxAgeMs: 1_000 }) as WasteLoopStageState | null;
}

export async function fetchWasteRealCandleProbe(): Promise<WasteRealCandleProbe | null> {
  try { return await apiGet<WasteRealCandleProbe>("/waste-loop-control/real-candle-probe/latest"); } catch { return null; }
}

export async function runWasteRealCandleProbe(
  body: WasteRealCandleProbeRequest = {},
): Promise<WasteRealCandleProbe> {
  return apiPostJson<WasteRealCandleProbe, WasteRealCandleProbeRequest>(
    "/waste-loop-control/real-candle-probe/run",
    body,
  );
}

export async function runWasteRealCandleProbeDryRun(
  body: WasteRealCandleProbeDryRunRequest,
): Promise<LiveOrderDryRunReport> {
  return apiPostJson<LiveOrderDryRunReport, WasteRealCandleProbeDryRunRequest>(
    "/waste-loop-control/real-candle-probe/dry-run",
    body,
  );
}

export async function fetchMT5MarketDataDiagnostic(): Promise<MT5MarketDataDiagnostic | null> {
  try {
    return await apiGet<MT5MarketDataDiagnostic>("/waste-loop-control/mt5-market-data-diagnostic/latest");
  } catch {
    return null;
  }
}

export async function runMT5MarketDataDiagnostic(
  body: MT5MarketDataDiagnosticRequest = {},
): Promise<MT5MarketDataDiagnostic> {
  return apiPostJson<MT5MarketDataDiagnostic, MT5MarketDataDiagnosticRequest>(
    "/waste-loop-control/mt5-market-data-diagnostic/run",
    body,
  );
}

export async function startWasteLoop(intervalSeconds = 5): Promise<WasteLoopState> {
  return apiPostJson<WasteLoopState, WasteLoopStartRequest>(
    "/waste-loop-control/start?confirm=true",
    { interval_seconds: intervalSeconds },
    30_000,
  );
}

export async function stopWasteLoop(): Promise<WasteLoopState> {
  return apiPost<WasteLoopState>("/waste-loop-control/stop");
}

export async function recoverWasteLoopSupervisor(confirm = true): Promise<LoopSupervisorStatus> {
  const q = confirm ? "?confirm=true" : "";
  return apiPost<LoopSupervisorStatus>(`/waste-loop-control/supervisor/recover${q}`);
}

// ── Live MetaTrader 5 account (read-only, from the connected terminal) ──

export interface Mt5Position {
  ticket: number | null;
  symbol: string;
  side: string;
  lots: number;
  open_price: number;
  current_price: number;
  stop_loss: number | null;
  take_profit: number | null;
  floating_pnl_usd: number;
  swap_usd: number;
}

export interface Mt5Account {
  login: number;
  server: string;
  name: string;
  currency: string;
  leverage: number;
  balance_usd: number;
  equity_usd: number;
  margin_used_usd: number;
  free_margin_usd: number;
  floating_pnl_usd: number;
}

export interface Mt5LiveState {
  report_kind?: string;
  connected: boolean;
  is_demo?: boolean;
  account?: Mt5Account;
  positions?: Mt5Position[];
  open_position_count?: number;
  algo_allowed?: boolean;
  note?: string;
  detail?: string;
  error?: string;
  cached?: boolean;
}

export async function fetchMt5Account(): Promise<Mt5LiveState | null> {
  try { return await apiGet<Mt5LiveState>("/mt5/account"); } catch { return null; }
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

export async function fetchTerminalReceiptRecoveryPacket(): Promise<TerminalReceiptRecoveryPacket | null> {
  try { return await apiGet<TerminalReceiptRecoveryPacket>("/strategy/terminal-receipt-recovery-packet/latest"); } catch { return null; }
}

export async function runTerminalReceiptArchiveAction({
  execute = false,
  confirm_owner_archive = false,
  age_threshold_hours = 24,
  notes = "",
}: {
  execute?: boolean;
  confirm_owner_archive?: boolean;
  age_threshold_hours?: number;
  notes?: string;
}): Promise<TerminalReceiptArchiveAction> {
  return apiPostJson<
    TerminalReceiptArchiveAction,
    { execute: boolean; confirm_owner_archive: boolean; age_threshold_hours: number; notes: string }
  >(
    "/strategy/terminal-receipt-recovery-packet/archive-stale",
    { execute, confirm_owner_archive, age_threshold_hours, notes },
  );
}

export async function runTerminalReceiptRecoveryRefreshAction({
  execute = false,
  confirm_owner_refresh = false,
  notes = "",
}: {
  execute?: boolean;
  confirm_owner_refresh?: boolean;
  notes?: string;
}): Promise<TerminalReceiptRecoveryRefreshAction> {
  return apiPostJson<
    TerminalReceiptRecoveryRefreshAction,
    { execute: boolean; confirm_owner_refresh: boolean; notes: string }
  >(
    "/strategy/terminal-receipt-recovery-packet/refresh-chain",
    { execute, confirm_owner_refresh, notes },
  );
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

export type OwnerControlUpdate = Partial<Pick<
  OwnerControlState,
  "mode" | "max_concurrent_trades" | "max_loss_cap_pct" | "ai_autonomy_enabled"
>>;

export async function updateOwnerControl(patch: OwnerControlUpdate): Promise<OwnerControlState> {
  return apiPostJson<OwnerControlState, OwnerControlUpdate>("/settings/owner-control/update", patch);
}

export async function resetOwnerControl(): Promise<OwnerControlState> {
  return apiPost<OwnerControlState>("/settings/owner-control/reset");
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

export async function fetchAccountReconciliation(syncToBroker = false): Promise<AccountReconciliationReport | null> {
  const suffix = syncToBroker ? "?sync_to_broker=true" : "";
  try { return await apiGet<AccountReconciliationReport>(`/reconciliation/account${suffix}`); } catch { return null; }
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

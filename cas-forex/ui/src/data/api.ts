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
  AccountHealthReport,
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
import { apiDelete, apiDownloadBlob, apiGet, apiPost, apiPostJson } from "./apiCore";
import type { CommandPreview, ProposedCommand } from "./ownerCommandApi";

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
  proposed_command?: ProposedCommand | null;
  command_preview?: CommandPreview | null;
}

export interface ControlAuditChange {
  key?: string;
  scope?: string;
  before?: unknown;
  after?: unknown;
  posture?: string;
  unlimited_after?: boolean;
}

export interface ControlAuditRow {
  report_kind?: string;
  audit_id?: string;
  at?: string;
  action?: string;
  source?: string;
  changes?: ControlAuditChange[];
  request?: Record<string, unknown>;
  result?: Record<string, unknown>;
  external_money_movement?: boolean;
  claim_boundary?: string;
}

export interface ControlAuditReport {
  report_kind?: string;
  generated_at?: string;
  audit_path?: string;
  state_path?: string;
  rows: ControlAuditRow[];
  claim_boundary?: string;
}

export async function postAssistantChat(
  message: string,
  history: AssistantTurn[],
): Promise<AssistantReply> {
  // Dedicated longer timeout — a real Claude reply can take longer than the
  // shared 10s POST helper allows, especially over a phone connection.
  return apiPostJson<AssistantReply, { message: string; history: AssistantTurn[] }>(
    "/assistant/chat",
    { message, history },
    60_000,
  );
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
  cap_layer?: "OWNER_OVERRIDE_OR_STATIC_FALLBACK" | string;
  explicit_override_keys?: RiskControlKey[];
  effective_dispatch_caps?: {
    precedence?: string;
    max_open_position_count?: number | null;
    max_positions_per_symbol?: number | null;
    max_total_exposure_lots?: number | null;
    max_risk_per_trade_pct?: number | null;
    max_margin_utilization_pct?: number | null;
    max_drawdown_pct_from_equity_peak?: number | null;
    max_floating_loss_usd?: number | null;
    sources?: Record<string, string>;
    claim_boundary?: string;
  };
  override_persistence?: {
    status?: "PERSISTED_OWNER_OVERRIDES_ACTIVE" | "NO_EXPLICIT_OWNER_OVERRIDES" | "PERSISTENCE_DISABLED" | "PERSISTENCE_LOAD_ERROR" | string;
    enabled?: boolean;
    state_path?: string | null;
    state_file_present?: boolean;
    loaded_from_disk?: boolean;
    last_saved_at?: string | null;
    load_error?: string | null;
    explicit_override_count?: number;
    explicit_override_keys?: RiskControlKey[];
    claim_boundary?: string;
  };
  notes?: string[];
  last_update_assessment?: RiskControlAssessment;
  audit_path?: string;
  latest_audit?: ControlAuditRow | null;
  anti_impulse_journal_policy?: {
    required_on_loosen?: boolean;
    minimum_reason_length?: number;
    prompt?: string;
  };
  anti_impulse_status?: {
    report_kind?: "cas_forex_risk_control_anti_impulse_status";
    real_money_controls_armed?: boolean;
    typed_confirmation_required_on_loosen?: boolean;
    journal_required_on_loosen?: boolean;
    journal_minimum_reason_length?: number;
    journal_prompt?: string;
    would_block_new_loosening?: boolean;
    cooldown?: {
      report_kind?: "cas_forex_risk_loosening_cooldown";
      applies?: boolean;
      active?: boolean;
      cooldown_seconds?: number;
      remaining_seconds?: number;
      last_loosened_at?: string | null;
      last_loosened_changes?: RiskControlChange[];
      detail?: string;
    };
    claim_boundary?: string;
  };
}

export type RiskControlKey =
  | "max_concurrent_trades"
  | "max_total_exposure_lots"
  | "max_loss_cap_usd"
  | "max_drawdown_pct";

export type RiskControlPatch = Partial<Record<RiskControlKey, number | null>> & {
  journal_reason?: string;
};

export interface RiskControlResetRequest {
  confirm?: string;
  journal_reason?: string;
}

export interface RiskControlChange {
  key: RiskControlKey;
  before: number | null;
  after: number | null;
  posture: "unchanged" | "loosen" | "tighten" | "unknown";
  owner_layer_posture?: "unchanged" | "loosen" | "tighten" | "unknown";
  effective_before?: number | null;
  effective_after?: number | null;
  unlimited_after: boolean;
}

export interface RiskControlAssessment {
  report_kind: "cas_forex_risk_control_update_assessment" | "cas_forex_risk_control_reset_assessment";
  current: RiskControlState;
  effective_current?: Record<string, number | null>;
  effective_proposed?: Record<string, number | null>;
  explicit_override_keys_before?: RiskControlKey[];
  explicit_override_keys_after?: RiskControlKey[];
  changes: RiskControlChange[];
  loosening_changes: RiskControlChange[];
  tightening_changes: RiskControlChange[];
  requires_confirmation: boolean;
  requires_journal_reason?: boolean;
  journal_prompt?: string;
  journal?: {
    report_kind?: "cas_forex_risk_loosening_journal";
    required?: boolean;
    satisfied?: boolean;
    reason_length?: number;
    minimum_reason_length?: number;
    blockers?: string[];
    prompt?: string;
    claim_boundary?: string;
  };
  requires_cooldown_clear?: boolean;
  cooldown?: {
    report_kind?: "cas_forex_risk_loosening_cooldown";
    applies?: boolean;
    active?: boolean;
    cooldown_seconds?: number;
    remaining_seconds?: number;
    last_loosened_at?: string | null;
    last_loosened_changes?: RiskControlChange[];
    detail?: string;
  };
  confirm_phrase: string;
  real_money_controls_armed: boolean;
  claim_boundary: string;
}

export async function fetchRiskControl(): Promise<RiskControlState | null> {
  try { return await apiGet<RiskControlState>("/risk-control/state"); } catch { return null; }
}

export async function fetchRiskControlAudit(limit = 10): Promise<ControlAuditReport | null> {
  try { return await apiGet<ControlAuditReport>(`/risk-control/audit?limit=${encodeURIComponent(String(limit))}`); } catch { return null; }
}

export async function previewRiskControl(patch: RiskControlPatch): Promise<RiskControlAssessment> {
  return apiPostJson<RiskControlAssessment, RiskControlPatch>("/risk-control/preview", patch);
}

export async function previewResetRiskControl(
  body: RiskControlResetRequest = {},
): Promise<RiskControlAssessment> {
  return apiPostJson<RiskControlAssessment, RiskControlResetRequest>("/risk-control/preview-reset", body);
}

export async function updateRiskControl(
  patch: RiskControlPatch & { confirm?: string; journal_reason?: string },
): Promise<RiskControlState> {
  return apiPostJson<RiskControlState, typeof patch>("/risk-control/update", patch);
}

export async function resetRiskControl(body: RiskControlResetRequest = {}): Promise<RiskControlState> {
  return apiPostJson<RiskControlState, RiskControlResetRequest>("/risk-control/reset", body);
}

// -- AI control authority: inspectable CAS dials and owner bounds --

export interface AiControlAuthorityState {
  report_kind?: "cas_forex_ai_control_authority";
  owner_envelope: Record<string, unknown>;
  control_surface: {
    values: Record<string, unknown>;
    bounds: Record<string, unknown>;
    dial_definitions?: Record<string, {
      label?: string;
      operational_effect?: string;
      loosens_when?: string;
      tightens_when?: string;
      enforced_by?: string;
      value_kind?: string;
      units?: string;
      runtime_path?: string;
    }>;
    anti_impulse?: {
      report_kind?: "cas_forex_ai_dial_anti_impulse";
      lookback_hours?: number;
      recent_loosen_count?: number;
      projected_loosen_count?: number;
      loosen_warning_limit?: number;
      warning_active?: boolean;
      projected_warning_active?: boolean;
      cooldown_seconds?: number;
      cooldown_active?: boolean;
      cooldown_remaining_seconds?: number;
      projected_cooldown_blocked?: boolean;
      last_loosened_at?: string | null;
      cooldown_detail?: string;
      policy?: string;
      journal_prompt_required_on_loosen?: boolean;
      journal_prompt_min_chars?: number;
      journal_prompt?: string;
      recent_loosening_changes?: Array<Record<string, unknown>>;
    };
    guardrail_note?: string;
  };
  updated_at: string;
  state_path: string;
  audit_path?: string;
  latest_audit?: ControlAuditRow | null;
  authority_note?: string;
  direction_note?: string;
}

export interface AiControlAdjustmentPreview {
  ready?: boolean;
  lever?: string;
  requested?: unknown;
  checked?: unknown;
  current?: unknown;
  proposed?: unknown;
  posture?: string;
  owner_clamped?: boolean;
  base_clamped?: boolean;
  owner_reason?: string;
  reason?: string;
  binding?: {
    lever?: string;
    label?: string;
    operational_effect?: string;
    enforced_by?: string;
    loosens_when?: string;
    tightens_when?: string;
    value_kind?: string;
    units?: string;
    runtime_path?: string;
    owner_bound?: unknown;
  };
  before_after?: {
    requested?: unknown;
    checked?: unknown;
    current?: unknown;
    proposed?: unknown;
  };
  contract_rows?: Array<{
    field?: string;
    label?: string;
    posture?: string;
    value_kind?: string;
    units?: string;
    operational_effect?: string;
    enforced_by?: string;
    runtime_path?: string;
    owner_bound?: unknown;
    requested?: unknown;
    checked?: unknown;
    before?: unknown;
    after?: unknown;
    before_count?: number;
    after_count?: number;
    added?: string[];
    removed?: string[];
  }>;
  anti_impulse?: AiControlAuthorityState["control_surface"]["anti_impulse"];
  anti_impulse_journal?: {
    required?: boolean;
    satisfied?: boolean;
    reason_length?: number;
    minimum_reason_length?: number;
    blockers?: string[];
    prompt?: string;
    owner_review_recommended?: boolean;
    claim_boundary?: string;
  };
  journal_prompt_required?: boolean;
  journal_prompt?: string;
  requires_cooldown_clear?: boolean;
  blockers?: string[];
  effects?: string[];
  claim_boundary?: string;
}

export async function fetchAiControlAuthority(): Promise<AiControlAuthorityState | null> {
  try { return await apiGet<AiControlAuthorityState>("/ai-control-authority/state"); } catch { return null; }
}

export async function fetchAiControlAuthorityAudit(limit = 10): Promise<ControlAuditReport | null> {
  try { return await apiGet<ControlAuditReport>(`/ai-control-authority/audit?limit=${encodeURIComponent(String(limit))}`); } catch { return null; }
}

export async function previewAiControlAuthorityAdjust(
  lever: string,
  value: unknown,
  reason = "",
): Promise<AiControlAdjustmentPreview> {
  return apiPostJson<AiControlAdjustmentPreview, { lever: string; value: unknown; reason: string }>(
    "/ai-control-authority/preview",
    { lever, value, reason },
  );
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
  return apiPostJson<ProofControlState, Record<string, never>>(
    "/proof-control/run-now",
    {},
    90_000,
  );
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
  ai_autonomous_execution_authority?: string;
  human_in_loop_per_action_required?: boolean;
  per_order_confirmation_required?: boolean;
  per_configured_money_movement_confirmation_required?: boolean;
  technical_action_time_checks_still_required: boolean;
  advisory_inputs: string[];
  decision_context_inputs?: string[];
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
    decision_context_inputs?: string[];
    action_time_requirements?: string[];
    owner_controls_are_final_authority?: boolean;
    metrics_and_ai_are_advisory_only?: boolean;
    metrics_and_ai_can_veto_owner_authority?: boolean;
    ai_autonomous_execution_authority?: string;
    human_in_loop_per_action_required?: boolean;
    per_order_confirmation_required?: boolean;
    per_configured_money_movement_confirmation_required?: boolean;
  };
  owner_authority_model?: OwnerAuthorityModel;
  live_trading: RuntimeGateDecision;
  live_authorized: boolean;
  still_missing: string[];
  caveats: string[];
  status?: string;
  need_confirmation?: string;
  applied?: boolean;
  audit_path?: string | null;
  latest_audit?: Record<string, unknown> | null;
}

export async function fetchLiveEnable(): Promise<LiveEnableState | null> {
  try { return await apiGet<LiveEnableState>("/live-enable/state"); } catch { return null; }
}

export async function updateLiveEnable(
  patch: Partial<Record<LiveEnableKey, boolean>> & { confirm?: string },
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
  payment_provider_environment?: string;
  payment_api_key_set: boolean;
  payment_api_key_runtime_override_set?: boolean;
  payment_api_key_config_set?: boolean;
  payment_api_key_storage?: string;
  payment_provider_base_url?: string;
  payment_provider_account_id?: string;
  payout_destination_id: string;
  payout_destination_allowlisted: boolean;
  allowlist_label: string;
  runtime_provider_name?: string;
  runtime_status?: string;
  runtime_detail?: string;
  supported_provider?: boolean;
  supported_real_provider?: boolean;
  runtime_is_simulated?: boolean;
  real_money_provider_ready?: boolean;
  broker_account_bound?: boolean;
  custody_scope?: string;
  supported_actions?: string[];
  sandbox_conformance?: BrokerFundingConformanceStatus;
}

export interface BrokerFundingConformanceStatus {
  status: "ACCEPT" | "FLAG_FOR_HUMAN_REVIEW" | "unavailable" | string;
  present: boolean;
  sandbox_only: boolean;
  generated_at?: string | null;
  provider_reference?: string | null;
  checks_total?: number;
  checks_passed?: number;
  artifact_path?: string | null;
  detail: string;
}

export interface PaymentProviderRuntimeStatus {
  requested_provider: string;
  normalized_provider: string;
  runtime_provider_name: string;
  status: string;
  detail: string;
  supported_provider: boolean;
  supported_real_provider: boolean;
  api_key_present: boolean;
  runtime_is_simulated: boolean;
  real_money_provider_ready: boolean;
  broker_account_bound: boolean;
  custody_scope: string;
  supported_actions: string[];
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
  status?: string;
  need_confirmation?: string;
  applied?: boolean;
  audit_path?: string | null;
  latest_audit?: Record<string, unknown> | null;
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
  payment_provider_environment: string;
  payment_api_key: string;
  payment_provider_base_url: string;
  payment_provider_account_id: string;
  payout_destination_id: string;
  confirm: string;
}>;

export async function fetchAuthorization(): Promise<AuthorizationState | null> {
  try { return await apiGet<AuthorizationState>("/live-enable/authorization"); } catch { return null; }
}

export async function updateAuthorization(patch: AuthorizationPatch): Promise<AuthorizationState> {
  return apiPostJson<AuthorizationState, AuthorizationPatch>("/live-enable/authorization/update", patch);
}

export interface RuntimeTopologyStatus {
  report_kind: string;
  generated_at: string;
  status: string;
  claim_status: "ACCEPT" | "FLAG_FOR_HUMAN_REVIEW" | string;
  lifecycle: string;
  api_worker_count: number;
  supported_api_worker_count: number;
  runtime_owner: boolean;
  runtime_owner_pid?: number | null;
  process_pid: number;
  host?: string | null;
  port?: number | null;
  owner_lock_path: string;
  process_local_components: string[];
  stateful_control_plane_enabled: boolean;
  lan_phone_supported: boolean;
  multi_worker_supported: boolean;
  claim_boundary: string;
  next_action: string;
}

export async function fetchRuntimeTopology(): Promise<RuntimeTopologyStatus | null> {
  try { return await apiGet<RuntimeTopologyStatus>("/runtime-topology"); } catch { return null; }
}

// ── Verified profit sweep (broker-confirmed net winnings only) ──

export interface VerifiedProfitSweepSettings {
  sweep_pct: number;
  tax_reserve_pct: number;
  min_sweep_usd: number;
  destination_id?: string | null;
  allow_principal_sweep: boolean;
  autonomous_enabled: boolean;
  max_daily_sweep_usd?: number | null;
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
  gross_sweep_entitlement_usd: number;
  already_swept_usd: number;
  incremental_sweep_amount_usd: number;
  sweep_amount_usd: number;
  keep_in_broker_usd: number;
  principal_sweep_usd: number;
  status: string;
  reason: string;
  payout_gate: RuntimeGateDecision;
  provider_runtime: PaymentProviderRuntimeStatus;
  payout_runtime_ready: boolean;
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
  status?: string;
  need_confirmation?: string;
  detail?: string;
  settings: VerifiedProfitSweepSettings;
  latest_audit?: VerifiedProfitSweepAuditRecord | null;
  audit?: VerifiedProfitSweepAuditRecord | null;
  note?: string;
}

export type VerifiedProfitSweepPolicyUpdate = Partial<
  Pick<
    VerifiedProfitSweepSettings,
    "sweep_pct" | "tax_reserve_pct" | "min_sweep_usd" | "destination_id" | "allow_principal_sweep" | "autonomous_enabled" | "max_daily_sweep_usd"
  >
>;

export interface VerifiedProfitSweepRequestResult {
  status: string;
  detail?: string;
  capability?: string;
  need_confirmation?: string;
  confirm_phrase?: string;
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
  confirmPhrase = "",
): Promise<VerifiedProfitSweepPolicy> {
  const q = confirmPhrase.trim()
    ? `?confirm_phrase=${encodeURIComponent(confirmPhrase.trim())}`
    : "";
  return apiPostJson<VerifiedProfitSweepPolicy, VerifiedProfitSweepPolicyUpdate>(
    `/money-movement/verified-profit-sweep/policy${q}`,
    patch,
  );
}

export interface AutonomousMoneyMovementStatus {
  report_kind: string;
  generated_at?: string;
  status?: string;
  autonomous_enabled: boolean;
  policy_id?: string;
  provider_touched?: boolean;
  detail?: string;
  next_action?: string;
  preview?: VerifiedProfitSweepPreview;
  result?: VerifiedProfitSweepRequestResult;
}

export async function fetchAutonomousMoneyMovementStatus(): Promise<AutonomousMoneyMovementStatus | null> {
  try { return await apiGet<AutonomousMoneyMovementStatus>("/money-movement/verified-profit-sweep/autonomy"); } catch { return null; }
}

export async function runAutonomousMoneyMovementOnce(): Promise<AutonomousMoneyMovementStatus> {
  return apiPost<AutonomousMoneyMovementStatus>("/money-movement/verified-profit-sweep/autonomy/run-once");
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
  confirmPhrase = "",
): Promise<VerifiedProfitSweepRequestResult> {
  const params = new URLSearchParams();
  if (confirm) params.set("confirm", "true");
  if (confirmPhrase.trim()) params.set("confirm_phrase", confirmPhrase.trim());
  const q = params.toString() ? `?${params.toString()}` : "";
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
  confirmPhrase = "",
): Promise<WasteEntryDispatchHandoffStatus> {
  const params = new URLSearchParams();
  if (confirmLiveDispatch) params.set("confirm", "true");
  if (confirmPhrase.trim()) params.set("confirm_phrase", confirmPhrase.trim());
  const q = params.toString() ? `?${params.toString()}` : "";
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
  confirmPhrase = "",
): Promise<CompoundAddDispatchHandoffStatus> {
  const params = new URLSearchParams();
  if (confirmLiveDispatch) params.set("confirm", "true");
  if (confirmPhrase.trim()) params.set("confirm_phrase", confirmPhrase.trim());
  const q = params.toString() ? `?${params.toString()}` : "";
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

export async function triggerAutoHaltEmergencyStop(reason = "OWNER_EMERGENCY_STOP"): Promise<AutoHaltReport> {
  return apiPostJson<AutoHaltReport, { reason: string }>(
    "/auto-halt/emergency-stop",
    { reason: reason.trim() || "OWNER_EMERGENCY_STOP" },
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
    | "sizing_mode"
    | "continuous_authority"
    | "max_trade_risk_pct_equity"
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
  | "owner_confirms_risk_denominated_sizing"
  | "owner_confirms_autonomous_scaling_within_envelope"
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
  fallback_used?: boolean;
  connector_attempts?: Array<{
    connector: string;
    status: string;
    detail?: string;
    candle_count?: number;
    synthetic_fallback?: boolean;
    broker_grade_market_truth?: boolean;
  }>;
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

export interface PreTradeMoneyEstimate {
  report_kind?: "cas_forex_pre_trade_money_estimate";
  status?: "ESTIMATED" | "PARTIAL" | "UNAVAILABLE" | string;
  symbol?: string;
  direction?: string;
  lots?: number | null;
  entry_price?: number | null;
  entry_price_source?: string | null;
  stop_loss?: number | null;
  take_profit?: number | null;
  price_unit_name?: string;
  price_unit_size?: number;
  stop_distance_units?: number | null;
  take_profit_distance_units?: number | null;
  unit_value_per_lot_usd?: number | null;
  risk_at_stop_usd?: number | null;
  risk_at_stop_pct_equity?: number | null;
  reward_at_take_profit_usd?: number | null;
  reward_risk_ratio?: number | null;
  estimated_notional_usd?: number | null;
  estimated_margin_required_usd?: number | null;
  estimated_margin_after_usd?: number | null;
  estimated_free_margin_after_usd?: number | null;
  estimated_margin_utilization_after_pct?: number | null;
  spread_cost_estimate_usd?: number | null;
  commission_estimate_usd?: number | null;
  swap_estimate_usd?: number | null;
  assumptions?: string[];
  claim_boundary?: string;
}

export interface MarketAvailabilityCheck {
  report_kind?: "cas_forex_market_availability_check" | string;
  status?: "BLOCKED" | "PASSED" | "UNKNOWN" | string;
  symbol?: string;
  direction?: string;
  available?: boolean | null;
  block?: boolean;
  blockers?: string[];
  evidence?: Array<Record<string, unknown>>;
  detail?: string;
  claim_boundary?: string;
}

export interface ExecutionQualityCheck {
  report_kind?: "cas_forex_execution_quality_check" | string;
  status?: "BLOCKED" | "PASSED" | "UNKNOWN" | string;
  symbol?: string;
  block?: boolean;
  blockers?: string[];
  evidence?: Array<Record<string, unknown>>;
  tolerances?: {
    max_spread_pips?: number;
    max_slippage_pips?: number;
    strictness?: string;
  };
  detail?: string;
  claim_boundary?: string;
}

export interface MacroBlackoutCheck {
  report_kind?: "cas_forex_macro_blackout_check" | string;
  status?: "BLOCKED" | "PASSED" | "UNKNOWN" | "DISABLED" | string;
  symbol?: string;
  block?: boolean;
  checked_at_iso?: string;
  blockers?: string[];
  evidence?: Array<Record<string, unknown>>;
  detail?: string;
  claim_boundary?: string;
}

export interface OrderConstraintsCheck {
  report_kind?: "cas_forex_order_constraints_check" | string;
  status?: "BLOCKED" | "PASSED" | "PARTIAL" | "UNKNOWN" | string;
  symbol?: string;
  direction?: string;
  block?: boolean;
  blockers?: string[];
  checks?: Array<Record<string, unknown>>;
  tolerances?: {
    min_lot?: number;
    max_lot?: number;
    min_stop_distance_pips?: number;
    strictness?: string;
  };
  detail?: string;
  claim_boundary?: string;
}

export interface ManualOrderResult {
  report_kind?: string;
  status?: string;
  detail?: string;
  need_confirmation?: string;
  confirm_phrase?: string;
  live_trading_authorized?: boolean;
  broker_touched?: boolean;
  dispatched_to_bridge?: boolean;
  mode?: string;
  intent_count?: number;
  executed_count?: number;
  blocked_count?: number;
  rejected_count?: number;
  live_execution_runtime_locked?: boolean;
  results?: {
    status: string;
    reason: string;
    stop_loss?: number | null;
    take_profit?: number | null;
    money_impact?: {
      broker_bridge_touched: boolean;
      order_executed: boolean;
      real_broker: boolean;
      external_money_movement: boolean;
      summary: string;
    };
    pre_trade_estimate?: PreTradeMoneyEstimate;
    market_availability?: MarketAvailabilityCheck;
    execution_quality?: ExecutionQualityCheck;
    macro_blackout?: MacroBlackoutCheck;
    order_constraints?: OrderConstraintsCheck;
    live_gate_report?: Record<string, unknown>;
    execution_provenance?: Record<string, unknown>;
    trade_explanation_card?: {
      report_kind?: string;
      summary?: string;
      gate_trace?: Array<Record<string, unknown>>;
      protective_orders?: Record<string, unknown>;
      money_impact?: Record<string, unknown>;
      pre_trade_money?: PreTradeMoneyEstimate;
      market_availability?: MarketAvailabilityCheck;
      execution_quality?: ExecutionQualityCheck;
      macro_blackout?: MacroBlackoutCheck;
      order_constraints?: OrderConstraintsCheck;
      live_gate_report?: Record<string, unknown>;
      live_readiness_evidence?: Record<string, unknown>;
      execution_provenance?: Record<string, unknown>;
      audit?: Record<string, unknown>;
      claim_boundary?: string;
    };
  }[];
  manual_order?: {
    symbol: string;
    direction: string;
    lots: number;
    stop_loss: number;
    take_profit: number;
    auto_sl: boolean;
    auto_tp: boolean;
  };
  manual_order_journal?: {
    report_kind?: string;
    required?: boolean;
    satisfied?: boolean;
    reason_length?: number;
    minimum_reason_length?: number;
    blockers?: string[];
    prompt?: string;
    claim_boundary?: string;
  };
  need_journal_reason?: boolean;
}

export interface SecurityPosture {
  report_kind: "cas_forex_security_posture" | string;
  status: string;
  attention_items?: string[];
  owner_auth?: {
    cloud_mode?: boolean;
    lan_mode_enabled?: boolean;
    owner_token_present?: boolean;
    owner_token_hint?: string;
    owner_token_runtime_store_encrypted_at_rest?: boolean;
    owner_token_runtime_secret_storage?: Record<string, unknown>;
    owner_token_env_source_present?: boolean;
    loopback_trusted_when_not_cloud?: boolean;
    off_box_requires_lan_and_owner_token?: boolean;
    cloud_requires_owner_token_for_all_api?: boolean;
    full_token_route_loopback_only?: string;
    state_route_masks_token?: string;
    claim_boundary?: string;
  };
  browser_exposure?: {
    frontend_secret_policy?: string;
    browser_storage_keys?: Array<Record<string, unknown>>;
    secrets_forbidden_in_frontend?: string[];
  };
  managed_secret_store?: {
    report_kind?: "cas_forex_managed_secret_store" | string;
    status?: "OK" | "ATTENTION" | "WARMING" | string;
    backend_status?: string;
    active_backend?: string;
    requested_backend?: string;
    cloud_mode?: boolean;
    external_secret_manager?: {
      configured?: boolean;
      provider?: string;
      provider_set?: boolean;
    };
    os_current_user_store?: Record<string, unknown>;
    windows_credential_manager?: Record<string, unknown>;
    runtime_secret_envelope?: Record<string, unknown>;
    server_side_only?: boolean;
    raw_secret_returned?: boolean;
    attention_items?: string[];
    detail?: string;
    claim_boundary?: string;
  };
  server_secret_inventory?: Array<{
    key: string;
    label: string;
    configured: boolean;
    masked_hint?: string;
    storage?: string;
    runtime_secret_storage?: Record<string, unknown>;
    runtime_override_encrypted_at_rest?: boolean;
    runtime_override_set?: boolean;
    runtime_secret_store_set?: boolean;
    runtime_secret_store_encrypted_at_rest?: boolean;
    plaintext_config_source_present?: boolean;
    browser_exposed?: boolean;
    plaintext_local_storage?: boolean;
    purpose?: string;
  }>;
  ignore_coverage?: Record<string, unknown>;
  permission_surface?: Record<string, unknown>;
  role_permission_model?: {
    report_kind?: "cas_forex_role_permission_model" | string;
    status?: "OK" | "ATTENTION" | "WARMING" | string;
    authorization_model?: string;
    mfa_status?: string;
    mfa_detail?: string;
    live_action_second_factor?: {
      status?: string;
      factors?: string[];
      not_implemented?: string[];
      claim_boundary?: string;
    };
    mfa_hardening_backlog?: string[];
    gaps?: string[];
    route_permission_policy?: {
      report_kind?: "cas_forex_route_permission_policy" | string;
      status?: "OK" | "ATTENTION" | "WARMING" | string;
      enforcement?: string;
      authorization_model?: string;
      default_read_permission?: string;
      default_mutation_permission?: string;
      route_inventory_available?: boolean;
      route_inventory_count?: number;
      default_classified_route_count?: number;
      default_mutation_route_count?: number;
      default_mutation_routes?: Array<{
        method?: string;
        path?: string;
        permission?: string;
        category?: string;
      }>;
      coverage_status?: string;
      permission_count?: number;
      role_count?: number;
      route_rule_count?: number;
      money_or_live_sensitive_rule_count?: number;
      loopback_only_rule_count?: number;
      permissions?: Array<{ permission?: string; description?: string }>;
      roles?: Array<{
        role_key?: string;
        label?: string;
        principal_type?: string;
        authentication?: string;
        permissions?: string[];
      }>;
      route_rules?: Array<{
        methods?: string[];
        path?: string | null;
        prefix?: string | null;
        permission?: string;
        category?: string;
        loopback_only?: boolean;
        money_or_live_sensitive?: boolean;
        typed_confirmation_required?: boolean;
        default_rule?: boolean;
        note?: string;
      }>;
      default_rules?: Array<Record<string, unknown>>;
      claim_boundary?: string;
    };
    roles?: Array<{
      role_key?: string;
      label?: string;
      principal_type?: string;
      authentication?: string;
      can_view_dashboard?: boolean;
      can_pair_device?: boolean;
      can_rotate_owner_token?: boolean;
      can_change_owner_controls?: boolean;
      can_change_ai_dials?: boolean;
      can_arm_live_authority?: boolean;
      can_submit_live_order?: boolean;
      can_move_money?: boolean;
      can_read_raw_secrets?: boolean;
      can_run_broker_emergency?: boolean;
      requires_typed_confirmation_for_money_or_live?: boolean;
      enforcement?: string[];
    }>;
    claim_boundary?: string;
  };
  claim_boundary?: string;
}

export async function fetchSecurityPosture(): Promise<SecurityPosture | null> {
  try { return await apiGet<SecurityPosture>("/settings/security-posture", 6000); } catch { return null; }
}

export interface ProfessionalClaimHit {
  path?: string;
  line?: number;
  claim_type?: string;
  label?: string;
  severity?: "needs_review" | "boundary_reference" | string;
  excerpt?: string;
}

export interface ProfessionalDisclosureStatus {
  key?: string;
  label?: string;
  status?: "COVERED" | "MISSING_DRAFT_COPY" | string;
  minimum_copy?: string;
  recommended_surfaces?: string[];
}

export interface ProfessionalClaimsReport {
  report_kind?: "cas_forex_professional_claims" | string;
  status?: "OK" | "ATTENTION" | "WARMING" | string;
  risky_claim_count?: number;
  boundary_reference_count?: number;
  claim_hits?: ProfessionalClaimHit[];
  disclosure_document?: {
    path?: string;
    present?: boolean;
    line_count?: number;
    summary?: string;
  };
  required_disclosures?: ProfessionalDisclosureStatus[];
  missing_disclosures?: ProfessionalDisclosureStatus[];
  copy_policy?: {
    forbidden_claim_types?: Array<Record<string, unknown>>;
    preferred_language?: string[];
    claim_boundary?: string;
  };
  claim_boundary?: string;
}

export async function fetchProfessionalClaims(): Promise<ProfessionalClaimsReport | null> {
  try { return await apiGet<ProfessionalClaimsReport>("/settings/professional-claims", 6000); } catch { return null; }
}

export interface AiHedgeIntelligenceLayer {
  report_kind?: "cas_forex_ai_hedge_intelligence_layer" | string;
  status?: "SPECIFIED_GOVERNED_LAYER" | string;
  thesis?: string;
  edge_role?: string;
  description?: string;
  layers?: Array<{
    key?: string;
    label?: string;
    purpose?: string;
  }>;
  allowed_trade_intents?: string[];
  allowed_operator_edge_decisions?: string[];
  hard_boundaries?: string[];
  claim_boundary?: string;
}

export interface AutonomousExecutionCorrection {
  version?: string;
  product?: string;
  intent?: string;
  status?: string;
  purpose?: string;
  non_negotiable_product_intent?: string;
  replacement_autonomy_clause?: string;
  human_in_loop?: {
    per_order_required?: boolean;
    per_take_profit_required?: boolean;
    per_configured_money_movement_required?: boolean;
    required_for?: string[];
  };
  autonomous_trading_authority?: {
    enabled_when?: string[];
    allowed_actions?: string[];
    mandatory_path?: string[];
  };
  autonomous_money_movement_authority?: {
    enabled_when?: string[];
    allowed_actions?: string[];
    required_evidence?: string[];
  };
  hard_blocks?: string[];
  one_line_summary?: string;
}

export interface AiHedgeSupervisionRecommendation {
  intent?: string;
  scope?: string;
  symbol?: string;
  position_id?: string | null;
  urgency?: "LOW" | "MEDIUM" | "HIGH" | string;
  reason?: string;
  gate_path?: string;
  evidence_refs?: string[];
  broker_bound_action_authorized?: boolean;
  orders_placed?: boolean;
}

export interface AiHedgeSupervisionPosition {
  position_id?: string | null;
  symbol?: string;
  side?: string;
  lot_size?: number;
  open_price?: number;
  current_price?: number;
  stop_loss?: number | null;
  take_profit?: number | null;
  floating_pnl_usd?: number;
  floating_pnl_units?: number;
  r_multiple?: number | null;
  price_source?: string;
  price_stale?: boolean;
  stale_reason?: string | null;
  position_source_label?: string;
  age_days?: number | null;
  broker_ticket?: string | null;
}

export interface AiHedgeSupervisionReport {
  report_kind?: "cas_forex_ai_hedge_supervision" | string;
  status?: "WATCHING" | "ACTIVE_RECOMMENDATIONS" | "ATTENTION" | "WARMING" | string;
  layer_status?: string;
  thesis?: string;
  movement_stream_id?: string;
  movement_timestamp?: string;
  price_source_status?: string;
  price_source_label?: string;
  price_source_summary?: string;
  price_source_warning?: string | null;
  position_feed_label?: string;
  position_feed_detail?: string;
  static_simulation_active?: boolean;
  provider_usable_symbols?: string[];
  static_fallback_symbols?: string[];
  position_count?: number;
  recommendation_count?: number;
  action_recommendation_count?: number;
  high_urgency_count?: number;
  source_health?: Record<string, unknown>;
  positions?: AiHedgeSupervisionPosition[];
  recommendations?: AiHedgeSupervisionRecommendation[];
  allowed_trade_intents?: string[];
  hard_boundaries?: string[];
  broker_bound_action_authorized?: boolean;
  orders_placed?: boolean;
  money_moved?: boolean;
  execution_required_path?: string[];
  next_action?: string;
  claim_boundary?: string;
}

export interface AiHedgeManagementAction {
  action_id?: string;
  status?: "READY_FOR_GUARDED_EXECUTION" | "READY_FOR_OWNER_REVIEW" | "BLOCKED" | string;
  intent?: string;
  symbol?: string;
  position_id?: string | null;
  side?: string;
  broker_method?: "modify_position" | "close_position" | string;
  broker_ticket?: number | string | null;
  volume?: number | null;
  stop_loss?: number | null;
  take_profit?: number | null;
  open_price?: number | null;
  current_price?: number | null;
  r_multiple?: number | null;
  risk_effect?: string;
  reason?: string;
  urgency?: string;
  gate_path?: string;
  requires_owner_confirmation?: boolean;
  requires_fresh_broker_truth?: boolean;
  requires_execution_guard?: boolean;
  dry_run_only?: boolean;
  broker_bound_action_authorized?: boolean;
  broker_touched?: boolean;
  orders_placed?: boolean;
  draft_call?: Record<string, unknown>;
}

export interface AiHedgeManagementBlockedAction {
  status?: "BLOCKED" | string;
  block_code?: string;
  intent?: string;
  symbol?: string;
  position_id?: string | null;
  broker_ticket?: number | string | null;
  reason?: string;
  source_reason?: string;
  gate_path?: string;
  broker_bound_action_authorized?: boolean;
  broker_touched?: boolean;
  orders_placed?: boolean;
}

export interface AiHedgeManagementHandoffReport {
  report_kind?: "cas_forex_ai_hedge_management_handoff" | string;
  status?: "READY_FOR_GUARDED_EXECUTION" | "READY_FOR_OWNER_REVIEW" | "BLOCKED" | "NO_ACTIONABLE_MANAGEMENT" | "WARMING" | string;
  supervision_status?: string;
  movement_stream_id?: string;
  movement_timestamp?: string;
  price_source_status?: string;
  price_source_label?: string;
  static_simulation_active?: boolean;
  source_health?: Record<string, unknown>;
  position_count?: number;
  recommendation_count?: number;
  actionable_recommendation_count?: number;
  management_action_count?: number;
  blocked_action_count?: number;
  skipped_recommendation_count?: number;
  ready_for_owner_review?: boolean;
  ready_for_guarded_execution?: boolean;
  dry_run_only?: boolean;
  broker_bound_action_authorized?: boolean;
  broker_touched?: boolean;
  orders_placed?: boolean;
  money_moved?: boolean;
  management_actions?: AiHedgeManagementAction[];
  blocked_actions?: AiHedgeManagementBlockedAction[];
  skipped_recommendations?: Array<Record<string, unknown>>;
  execution_required_path?: string[];
  next_action?: string;
  claim_boundary?: string;
}

export interface AiHedgeManagementExecutionResult {
  report_kind?: "cas_forex_ai_hedge_management_execution" | string;
  status?: "DRY_RUN" | "CONFIRM_REQUIRED" | "EXECUTED_RECONCILED" | "EXECUTED_NOT_RECONCILED" | "EXECUTED_RECONCILIATION_UNAVAILABLE" | "REJECTED" | "EXECUTION_GUARD_BLOCKED" | "ACTION_NOT_FOUND" | "NO_ACTIONABLE_MANAGEMENT" | string;
  generated_at_iso?: string;
  requested_action_id?: string | null;
  selected_action_id?: string | null;
  selected_action?: AiHedgeManagementAction | Record<string, unknown>;
  handoff_status?: string;
  handoff_movement_stream_id?: string;
  handoff_price_source_status?: string;
  reason?: string;
  broker_touched?: boolean;
  per_action_owner_confirmation_required?: boolean;
  autonomous_execution_authority?: string;
  broker_method_called?: boolean;
  orders_placed?: boolean;
  money_moved?: boolean;
  external_money_movement?: boolean;
  need_confirmation?: string;
  confirm_phrase?: string;
  detail?: string;
  execution_guard?: Record<string, unknown>;
  bridge_status?: Record<string, unknown>;
  broker_result?: Record<string, unknown>;
  terminal_receipt?: Record<string, unknown>;
  terminal_receipt_status?: "RECONCILED" | "NOT_RECONCILED" | "RECONCILIATION_UNAVAILABLE" | "NOT_REQUESTED" | string;
  post_execution_refresh?: Record<string, unknown>;
  post_execution_refresh_status?: "REFRESH_RAN" | "REFRESH_PARTIAL" | "REFRESH_FAILED" | "REFRESH_UNAVAILABLE" | "NOT_REQUESTED" | string;
  next_action?: string;
  audit_id?: string;
  claim_boundary?: string;
}

export interface SpecContextStatusReport {
  report_kind?: "cas_forex_spec_context_status" | string;
  status?: "OK" | "ATTENTION" | "WARMING" | string;
  available?: boolean;
  source_found?: boolean;
  version?: string;
  generated_at?: string;
  source?: {
    kind?: string;
    path_or_url?: string;
    last_modified?: string | null;
    size_bytes?: number;
    sha256?: string;
  } | null;
  snapshot_hash_sha256?: string;
  sheet_count?: number;
  assistant_prompt_available?: boolean;
  operator_prompt_available?: boolean;
  ai_hedge_intelligence_layer?: AiHedgeIntelligenceLayer;
  autonomous_execution_correction?: AutonomousExecutionCorrection;
  assistant_context_chars?: number;
  operator_constitution_chars?: number;
  snapshot_stale?: boolean;
  json_path?: string;
  markdown_path?: string;
  operator_constitution_path?: string;
  refresh_command?: string;
  surfaces?: Record<string, unknown>;
  next_action?: string;
  claim_boundary?: string;
}

export async function fetchSpecContextStatus(): Promise<SpecContextStatusReport | null> {
  try { return await apiGet<SpecContextStatusReport>("/settings/spec-context", 6000); } catch { return null; }
}

export async function fetchAiHedgeSupervision(): Promise<AiHedgeSupervisionReport | null> {
  try { return await apiGet<AiHedgeSupervisionReport>("/settings/ai-hedge-supervision", 6000); } catch { return null; }
}

export async function fetchAiHedgeManagementHandoff(): Promise<AiHedgeManagementHandoffReport | null> {
  try { return await apiGet<AiHedgeManagementHandoffReport>("/settings/ai-hedge-management-handoff", 6000); } catch { return null; }
}

export async function runAiHedgeManagementAction(params: {
  action_id?: string;
  reason?: string;
  dry_run?: boolean;
  confirm_owner_action?: boolean;
  confirm_phrase?: string;
}): Promise<AiHedgeManagementExecutionResult> {
  const q = new URLSearchParams({
    dry_run: String(params.dry_run ?? true),
    confirm_owner_action: String(params.confirm_owner_action ?? false),
    confirm_phrase: params.confirm_phrase ?? "",
  });
  return apiPostJson<AiHedgeManagementExecutionResult, { action_id: string; reason: string }>(
    `/ai-hedge-management/execute?${q.toString()}`,
    {
      action_id: params.action_id ?? "",
      reason: params.reason ?? "AI_OPERATOR_EDGE_MANAGEMENT",
    },
  );
}

export interface LegalReviewReadinessCheck {
  key?: string;
  label?: string;
  status?: "OK" | "ATTENTION" | "MISSING" | "WARMING" | string;
  detail?: string;
  evidence?: Array<Record<string, unknown>>;
  missing_paths?: string[];
  missing_terms?: string[];
  next_action?: string;
}

export interface LegalReviewCounselHandoff {
  status?: "COUNSEL_REVIEW_REQUIRED" | "READY_FOR_RECORD_REVIEW" | string;
  launch_legal_status?: "READY_FOR_PUBLIC_LAUNCH_LEGAL" | "BLOCK_PUBLIC_LAUNCH" | string;
  package_documents?: Array<{
    path?: string;
    present?: boolean;
    line_count?: number;
  }>;
  required_record_fields?: string[];
  required_scope_terms?: string[];
  attention_keys?: string[];
  setup_steps?: string[];
  record_template?: string[];
  claim_boundary?: string;
}

export interface LegalReviewReadinessReport {
  report_kind?: "cas_forex_legal_review_readiness" | string;
  status?: "OK" | "ATTENTION" | "WARMING" | string;
  launch_legal_status?: "READY_FOR_PUBLIC_LAUNCH_LEGAL" | "BLOCK_PUBLIC_LAUNCH" | "WARMING" | string;
  counsel_review_accepted?: boolean;
  ok_count?: number;
  attention_count?: number;
  checks?: LegalReviewReadinessCheck[];
  required_documents?: {
    drafts?: string[];
    checklist?: string;
    counsel_review_record?: string;
  };
  counsel_review_handoff?: LegalReviewCounselHandoff;
  counsel_review_record_path?: string;
  top_attention_items?: string[];
  next_action?: string;
  claim_boundary?: string;
}

export async function fetchLegalReviewReadiness(): Promise<LegalReviewReadinessReport | null> {
  try { return await apiGet<LegalReviewReadinessReport>("/settings/legal-review-readiness", 6000); } catch { return null; }
}

export interface LegalReviewControlRecord {
  file_present?: boolean;
  counsel_review_status?: string;
  reviewed_by?: string;
  review_date?: string;
  scope?: string;
  qualified_counsel_confirmed?: boolean;
  review_artifact_path?: string;
  review_artifact_sha256?: string;
  matter_reference?: string;
  jurisdictions?: string;
  notes?: string;
  recorded_via?: string;
  recorded_at?: string;
  artifact_path_exists_locally?: boolean;
  artifact_hash_looks_valid?: boolean;
}

export interface LegalReviewControlReport {
  report_kind?: "cas_forex_legal_review_control" | string;
  status?: "OK" | "WARMING" | string;
  record_path?: string;
  audit_path?: string;
  required_confirm_phrase?: string;
  file_present?: boolean;
  current_record?: LegalReviewControlRecord;
  claim_boundary?: string;
}

export interface LegalReviewControlUpdate {
  reviewed_by: string;
  review_date: string;
  scope: string;
  review_artifact_path: string;
  review_artifact_sha256?: string;
  matter_reference?: string;
  jurisdictions?: string;
  notes?: string;
  qualified_counsel_confirmed: boolean;
  confirm_phrase: string;
  counsel_review_status?: string;
}

export interface LegalReviewControlMutationResult {
  report_kind?: "cas_forex_legal_review_control_update" | "cas_forex_legal_review_control_reset" | string;
  status?: "UPDATED" | "RESET" | string;
  required_confirm_phrase?: string;
  legal_review_control?: LegalReviewControlReport;
  legal_review_readiness?: LegalReviewReadinessReport;
  professional_readiness?: ProfessionalReadinessMatrix;
  public_launch_gate?: PublicLaunchGateReport;
  claim_boundary?: string;
}

export async function fetchLegalReviewControl(): Promise<LegalReviewControlReport | null> {
  try { return await apiGet<LegalReviewControlReport>("/settings/legal-review-control", 6000); } catch { return null; }
}

export async function updateLegalReviewControl(
  patch: LegalReviewControlUpdate,
): Promise<LegalReviewControlMutationResult> {
  return apiPostJson<LegalReviewControlMutationResult, LegalReviewControlUpdate>("/settings/legal-review-control/update", patch);
}

export async function resetLegalReviewControl(): Promise<LegalReviewControlMutationResult> {
  return apiPostJson<LegalReviewControlMutationResult, Record<string, never>>("/settings/legal-review-control/reset", {});
}

export interface ProfessionalReadinessRow {
  item_number?: number;
  key?: string;
  category?: string;
  status?: "OK" | "PARTIAL" | "GAP" | "WARMING" | string;
  professional_standard?: string;
  evidence_refs?: string[];
  present_evidence_refs?: string[];
  missing_evidence_refs?: string[];
  remaining_gap?: string;
  partial_terms?: string[];
  external_dependency?: string;
  blocked_by_external_dependency?: boolean;
  blocker_type?: "none" | "code" | "external" | string;
  completion_state?: "SATISFIED" | "PARTIAL" | "EXTERNAL_BLOCKED" | "MISSING" | string;
  next_action?: string;
}

export interface ProfessionalReadinessMatrix {
  report_kind?: "cas_forex_professional_readiness_matrix" | string;
  status?: "OK" | "ATTENTION" | "WARMING" | string;
  item_count?: number;
  ok_count?: number;
  partial_count?: number;
  gap_count?: number;
  satisfied_count?: number;
  internal_partial_count?: number;
  external_blocked_count?: number;
  missing_count?: number;
  attention_count?: number;
  rows?: ProfessionalReadinessRow[];
  top_attention_items?: string[];
  claim_boundary?: string;
}

export async function fetchProfessionalReadiness(): Promise<ProfessionalReadinessMatrix | null> {
  try { return await apiGet<ProfessionalReadinessMatrix>("/settings/professional-readiness", 6000); } catch { return null; }
}

export interface PublicLaunchGateItem {
  key?: string;
  label?: string;
  status?: "PASS" | "BLOCK" | "WARMING" | string;
  source_report_kind?: string;
  source_status?: string;
  detail?: string;
  evidence?: Record<string, unknown>;
  next_action?: string;
}

export interface PublicLaunchGateReport {
  report_kind?: "cas_forex_public_launch_gate" | string;
  status?: "OK" | "ATTENTION" | "WARMING" | string;
  launch_gate_status?: "PASS" | "BLOCK_PUBLIC_LAUNCH" | "WARMING" | string;
  public_launch_status?: "READY" | "BLOCKED" | "WARMING" | string;
  live_money_production_status?: "READY" | "BLOCKED" | "WARMING" | string;
  gate_count?: number;
  pass_count?: number;
  block_count?: number;
  hard_blocker_count?: number;
  gates?: PublicLaunchGateItem[];
  hard_blockers?: string[];
  source_reports?: Record<string, string | undefined>;
  release_policy?: string;
  next_action?: string;
  claim_boundary?: string;
}

export async function fetchPublicLaunchGate(): Promise<PublicLaunchGateReport | null> {
  try { return await apiGet<PublicLaunchGateReport>("/settings/public-launch-gate", 6000); } catch { return null; }
}

export interface BypassLaunchGateCheck {
  check_id?: string;
  status?: "OK" | "ATTENTION" | "WARMING" | string;
  invariant?: string;
  enforcement?: string;
  evidence_refs?: string[];
  present_evidence_refs?: string[];
  missing_evidence_refs?: string[];
  missing_required_terms?: Array<Record<string, string>>;
  forbidden_term_hits?: Array<Record<string, string>>;
  next_action?: string;
}

export interface BypassLaunchGateReport {
  report_kind?: "cas_forex_bypass_launch_gate" | string;
  status?: "OK" | "ATTENTION" | "WARMING" | string;
  launch_gate_status?: "PASS" | "BLOCK_RELEASE" | "WARMING" | string;
  check_count?: number;
  ok_count?: number;
  attention_count?: number;
  checks?: BypassLaunchGateCheck[];
  top_attention_items?: string[];
  release_policy?: string;
  claim_boundary?: string;
}

export async function fetchBypassLaunchGate(): Promise<BypassLaunchGateReport | null> {
  try { return await apiGet<BypassLaunchGateReport>("/settings/bypass-launch-gate", 6000); } catch { return null; }
}

export interface UILayoutContractCheck {
  check_id?: string;
  status?: "OK" | "ATTENTION" | "WARMING" | string;
  detail?: string;
  evidence?: string[];
  next_action?: string;
}

export interface UILayoutContractReport {
  report_kind?: "cas_forex_ui_layout_zoom_contract" | string;
  status?: "OK" | "ATTENTION" | "WARMING" | string;
  ok_count?: number;
  attention_count?: number;
  check_count?: number;
  checks?: UILayoutContractCheck[];
  route_count?: number;
  missing_page_routes?: string[];
  css_zoom_violations?: string[];
  top_attention_items?: string[];
  claim_boundary?: string;
}

export async function fetchUILayoutContract(): Promise<UILayoutContractReport | null> {
  try { return await apiGet<UILayoutContractReport>("/settings/ui-layout-contract", 6000); } catch { return null; }
}

export interface EconomicCalendarFeedReport {
  report_kind?: "cas_forex_economic_calendar_feed" | string;
  status?: "UNCONFIGURED" | "LOADED" | "CACHE_FRESH" | "CACHE_STALE" | "FETCH_FAILED" | "WARMING" | string;
  source_status?: "CONFIGURED" | "UNCONFIGURED" | "UNKNOWN" | string;
  configured?: boolean;
  checked_at_iso?: string | null;
  source_kind?: string;
  source?: string;
  source_is_http?: boolean;
  cache_path?: string;
  cache_ttl_seconds?: number;
  cache_written_at_epoch?: number | null;
  cache_age_seconds?: number | null;
  cache_stale?: boolean;
  fail_closed_on_error?: boolean;
  event_count?: number;
  raw_event_count?: number;
  unusable_event_count?: number;
  events?: Array<Record<string, unknown>>;
  detail?: string;
  error?: string | null;
  claim_boundary?: string;
}

export async function fetchEconomicCalendarFeed(): Promise<EconomicCalendarFeedReport | null> {
  try { return await apiGet<EconomicCalendarFeedReport>("/settings/economic-calendar", 6000); } catch { return null; }
}

export interface OperationalReadinessCheck {
  key?: string;
  label?: string;
  status?: "OK" | "ATTENTION" | "MISSING" | "WARMING" | string;
  detail?: string;
  evidence?: Array<Record<string, unknown>>;
  missing_paths?: string[];
  missing_terms?: string[];
}

export interface ExternalMonitoringCheck {
  key?: string;
  label?: string;
  status?: "OK" | "ATTENTION" | "MISSING" | string;
  detail?: string;
  env_keys?: string[];
  configured_key?: string | null;
  masked_value?: string | null;
  missing_env_keys?: string[];
  missing_terms?: string[];
  advisory?: boolean;
}

export interface ExternalMonitoringDeploymentHandoff {
  status?: "READY" | "ACTION_REQUIRED" | string;
  public_base_url_placeholder?: string;
  owner_ui_path?: string;
  health_endpoints?: string[];
  required_env?: Record<string, string[]>;
  attention_keys?: string[];
  check_statuses?: Record<string, string>;
  setup_steps?: string[];
  verification_commands?: string[];
  claim_boundary?: string;
}

export interface ExternalMonitoringReadiness {
  report_kind?: "cas_forex_external_monitoring_readiness" | string;
  status?: "OK" | "ATTENTION" | string;
  ok_count?: number;
  attention_count?: number;
  checks?: ExternalMonitoringCheck[];
  health_endpoints?: string[];
  required_env?: Record<string, string[]>;
  deployment_handoff?: ExternalMonitoringDeploymentHandoff;
  top_attention_items?: string[];
  next_action?: string;
  claim_boundary?: string;
}

export interface OperationalReadinessReport {
  report_kind?: "cas_forex_operational_readiness" | string;
  status?: "OK" | "ATTENTION" | "WARMING" | string;
  ok_count?: number;
  attention_count?: number;
  checks?: OperationalReadinessCheck[];
  attention_items?: string[];
  top_attention_items?: string[];
  next_action?: string;
  backup_inventory?: {
    snapshot_count?: number;
    latest_snapshot?: Record<string, unknown> | null;
    snapshot_dirs?: Array<Record<string, unknown>>;
    snapshots?: Array<Record<string, unknown>>;
  };
  external_monitoring?: ExternalMonitoringReadiness;
  runbook_path?: string;
  claim_boundary?: string;
}

export async function fetchOperationalReadiness(): Promise<OperationalReadinessReport | null> {
  try { return await apiGet<OperationalReadinessReport>("/settings/operational-readiness", 6000); } catch { return null; }
}

export interface ExternalMonitoringConfigResult {
  report_kind?: string;
  status?: "UPDATED" | "RESET" | "NO_CHANGES" | string;
  applied_keys?: string[];
  external_monitoring?: ExternalMonitoringReadiness;
  external_monitoring_control?: Record<string, unknown>;
  operational_readiness?: OperationalReadinessReport;
  professional_readiness?: ProfessionalReadinessMatrix;
  public_launch_gate?: PublicLaunchGateReport;
  claim_boundary?: string;
}

export async function updateExternalMonitoringConfig(
  patch: { uptime_monitor_url?: string; error_tracking_dsn?: string; alert_webhook_url?: string },
): Promise<ExternalMonitoringConfigResult> {
  return apiPostJson<ExternalMonitoringConfigResult, typeof patch>("/external-monitoring/update", patch);
}

export async function resetExternalMonitoringConfig(): Promise<ExternalMonitoringConfigResult> {
  return apiPost<ExternalMonitoringConfigResult>("/external-monitoring/reset");
}

export interface EmergencyControlRow {
  key?: string;
  label?: string;
  category?: "automation_stop" | "broker_exposure" | string;
  status?: "OK" | "MISSING" | "ATTENTION" | "WARMING" | string;
  route?: string | null;
  surface?: string;
  effect?: string;
  money_impact?: string;
  evidence?: Array<Record<string, unknown>>;
  missing_detail?: string;
  missing_evidence?: string[];
}

export interface EmergencyControlsReport {
  report_kind?: "cas_forex_emergency_controls" | string;
  status?: "OK" | "ATTENTION" | "WARMING" | string;
  ok_count?: number;
  attention_count?: number;
  automation_stop_ok?: boolean;
  broker_exposure_gap?: boolean;
  controls?: EmergencyControlRow[];
  attention_items?: string[];
  automation_stop_scope?: string;
  recommended_terminal_actions?: string[];
  claim_boundary?: string;
}

export async function fetchEmergencyControls(): Promise<EmergencyControlsReport | null> {
  try { return await apiGet<EmergencyControlsReport>("/settings/emergency-controls", 6000); } catch { return null; }
}

export interface BrokerEmergencyActionResult {
  report_kind?: "cas_forex_broker_emergency_action" | "cas_forex_broker_emergency_status" | string;
  action?: string;
  status?: string;
  detail?: string;
  need_confirmation?: string;
  confirm_phrase?: string;
  generated_at_iso?: string;
  reason?: string;
  mt5_connected?: boolean;
  will_execute_real_order?: boolean | null;
  open_position_count?: number;
  pending_order_count?: number;
  selected_position_count?: number;
  selected_pending_order_count?: number;
  broker_touched?: boolean;
  broker_order_send_attempted?: boolean;
  external_money_movement?: boolean;
  closed_positions?: Array<Record<string, unknown>>;
  cancelled_orders?: Array<Record<string, unknown>>;
  failed_count?: number;
  next_action?: string;
  claim_boundary?: string;
}

export async function fetchBrokerEmergencyStatus(): Promise<BrokerEmergencyActionResult | null> {
  try { return await apiGet<BrokerEmergencyActionResult>("/broker-emergency/status", 6000); } catch { return null; }
}

export async function runBrokerEmergencyAction(
  endpoint: "close-all" | "close-profitable" | "close-losing" | "cancel-pending",
  options: {
    reason?: string;
    dryRun?: boolean;
    confirmOwnerAction?: boolean;
    confirmPhrase?: string;
  } = {},
): Promise<BrokerEmergencyActionResult> {
  const {
    reason = "OWNER_BROKER_EMERGENCY",
    dryRun = true,
    confirmOwnerAction = false,
    confirmPhrase = "",
  } = options;
  const q = new URLSearchParams();
  q.set("dry_run", dryRun ? "true" : "false");
  q.set("confirm_owner_action", confirmOwnerAction ? "true" : "false");
  if (confirmPhrase.trim()) q.set("confirm_phrase", confirmPhrase.trim());
  return apiPostJson<BrokerEmergencyActionResult, { reason: string }>(
    `/broker-emergency/${endpoint}?${q.toString()}`,
    { reason },
  );
}

export interface OperatorBackupCreateResult {
  report_kind?: "cas_forex_operator_backup_create" | string;
  status?: "CREATED" | "FAILED_OR_EMPTY" | string;
  manifest?: Record<string, unknown>;
  operational_readiness?: OperationalReadinessReport;
  snapshot_dir?: string;
  claim_boundary?: string;
}

export async function createOperatorBackup(): Promise<OperatorBackupCreateResult> {
  return apiPost<OperatorBackupCreateResult>("/settings/operator-backup/create");
}

export async function postManualOrder(body: {
  symbol: string;
  direction: "BUY" | "SELL";
  lots: number;
  sl?: number | null;
  tp?: number | null;
  journal_reason?: string | null;
}, confirm = false, confirmPhrase = ""): Promise<ManualOrderResult> {
  const params = new URLSearchParams();
  if (confirm) params.set("confirm", "true");
  if (confirmPhrase.trim()) params.set("confirm_phrase", confirmPhrase.trim());
  const q = params.toString() ? `?${params.toString()}` : "";
  return apiPostJson<ManualOrderResult, typeof body>(`/order-dispatch/manual${q}`, body);
}

// ── Auto-trade dispatch loop (runs the gated cycle on a timer; paper by default) ──

export interface DispatchLoopState {
  report_kind?: string;
  running: boolean;
  execution_active?: boolean;
  execution_lane?: "PAPER" | "LIVE" | "NONE" | string;
  paper_learning_active?: boolean;
  paper_fallback_active?: boolean;
  paper_fallback_available?: boolean;
  live_execution_active?: boolean;
  live_execution_authorized?: boolean;
  live_execution_status?: string;
  interval_seconds?: number;
  symbols?: string[];
  sessions?: string[];
  position_scope?: "CAS_ONLY" | "ALL_ACCOUNT" | string;
  position_scope_label?: string;
  active_sessions?: string[];
  cycles_run?: number;
  cycles_idle?: number;
  last_symbol_targeting?: {
    status?: string;
    ai_symbols?: string[];
    scheduler_symbols?: string[];
    effective_symbols?: string[];
    position_symbol_counts?: Record<string, number>;
    max_positions_per_symbol?: number;
    saturated_symbols?: string[];
    eligible_symbols?: string[];
    detail?: string;
  };
  last_entry_timeframe_scan?: {
    status?: string;
    active_timeframes?: string[];
    selected_timeframe?: string | null;
    entry_lane?: "MICRO_SCALP" | "INTRADAY" | string;
    fresh_intent_count?: number;
    error?: string | null;
  };
  active_entry_timeframes?: string[];
  last_entry_timeframe?: string | null;
  last_entry_lane?: "MICRO_SCALP" | "INTRADAY" | string | null;
  last_entry_risk_feasibility?: {
    status?: string;
    max_risk_per_trade_pct?: number | null;
    candidate_count?: number;
    feasible_count?: number;
    blocked_count?: number;
    unknown_count?: number;
    operator_candidate_count?: number;
    candidates?: Array<{
      symbol?: string;
      direction?: string;
      timeframe?: string;
      requested_lots?: number | null;
      broker_min_lot?: number | null;
      risk_at_stop_usd?: number | null;
      risk_at_stop_pct_equity?: number | null;
      max_feasible_lots?: number | null;
      minimum_lot_risk_usd?: number | null;
      minimum_lot_risk_pct_equity?: number | null;
      status?: string;
      reason?: string;
    }>;
  };
  last_entry_risk_feasibility_status?: string | null;
  last_entry_risk_candidate_count?: number | null;
  last_entry_risk_feasible_count?: number | null;
  last_entry_risk_blocked_count?: number | null;
  last_entry_risk_unknown_count?: number | null;
  last_entry_risk_operator_candidate_count?: number | null;
  last_symbol_targeting_status?: string | null;
  last_effective_entry_symbols?: string[];
  last_eligible_entry_symbols?: string[];
  last_saturated_entry_symbols?: string[];
  control_revision?: number | null;
  control_updated_at?: string | null;
  control_updated_by?: string | null;
  control_change_reason?: string | null;
  control_event_hash?: string | null;
  management_cycles_run?: number;
  last_management_status?: string | null;
  last_management_detail?: string | null;
  last_management_action_count?: number;
  last_management_terminal_effect_count?: number;
  last_management_broker_touched?: boolean;
  last_management_account_position_count?: number;
  last_management_excluded_position_count?: number;
  last_management_primary_position_count?: number;
  last_management_simulator_handoff_position_count?: number;
  last_management_sources?: Array<{
    role?: "PRIMARY" | "SIMULATOR_HANDOFF" | string;
    bridge_class?: string;
    status?: string;
    position_count?: number;
    attempted_action_count?: number;
    terminal_effect_count?: number;
    broker_touched?: boolean;
  }>;
  last_mt5_demo_learning_sync_status?: string | null;
  last_mt5_demo_learning_sync_at?: string | null;
  last_mt5_demo_learning_sync_error?: string | null;
  last_mt5_demo_learning_history_count?: number;
  last_mt5_demo_learning_bound_trade_count?: number;
  last_mt5_demo_learning_group_learning_ready?: boolean | null;
  last_mt5_demo_learning_overall_sample_ready?: boolean | null;
  last_mt5_demo_learning_ready_group_count?: number;
  last_mt5_demo_learning_min_samples_per_group?: number;
  last_operator_trade_edge?: Record<string, unknown>;
  last_operator_trade_edge_status?: string | null;
  last_operator_trade_edge_at?: string | null;
  last_operator_trade_edge_provider?: string | null;
  last_operator_trade_edge_summary?: string | null;
  last_operator_trade_edge_candidate_count?: number | null;
  last_operator_trade_edge_approved_count?: number | null;
  last_operator_trade_edge_stand_down_count?: number | null;
  last_run_iso?: string | null;
  last_summary?: string | null;
  last_error?: string | null;
  started_at_iso?: string | null;
  mode?: string;
  requested_mode?: string;
  last_blocking_detail?: string | null;
  live_blocking_detail?: string | null;
  last_execution_lane?: string | null;
  last_bridge_class?: string | null;
  last_bridge_selection_status?: string | null;
  last_bridge_selection_detail?: string | null;
  live_gate_decision?: Record<string, unknown> | null;
  note?: string;
  status?: string; // "CONFIRM_REQUIRED" when live is authorized
  detail?: string;
  need_confirmation?: string;
  confirm_phrase?: string;
  live_trading_authorized?: boolean;
  broker_touched?: boolean;
  dispatched_to_bridge?: boolean;
}

export interface DispatchLoopStart {
  interval_seconds: number;
  symbols?: string[];
  sessions?: string[];
  position_scope?: "CAS_ONLY" | "ALL_ACCOUNT";
  change_reason?: string;
}

export async function fetchDispatchLoopStatus(): Promise<DispatchLoopState | null> {
  try { return await apiGet<DispatchLoopState>("/dispatch-loop/status"); } catch { return null; }
}

export async function startDispatchLoop(
  body: DispatchLoopStart,
  confirm = false,
  confirmPhrase = "",
): Promise<DispatchLoopState> {
  const params = new URLSearchParams();
  if (confirm) params.set("confirm", "true");
  if (confirmPhrase.trim()) params.set("confirm_phrase", confirmPhrase.trim());
  const q = params.toString() ? `?${params.toString()}` : "";
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
  need_confirmation?: string;
  confirm_phrase?: string;
  live_trading_authorized?: boolean;
  broker_touched?: boolean;
  dispatched_to_bridge?: boolean;
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

export async function startWasteLoop(
  intervalSeconds = 5,
  confirm = false,
  confirmPhrase = "",
): Promise<WasteLoopState> {
  const params = new URLSearchParams();
  if (confirm) params.set("confirm", "true");
  if (confirmPhrase.trim()) params.set("confirm_phrase", confirmPhrase.trim());
  const q = params.toString() ? `?${params.toString()}` : "";
  return apiPostJson<WasteLoopState, WasteLoopStartRequest>(
    `/waste-loop-control/start${q}`,
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
  risk_at_stop_usd?: number | null;
  risk_at_stop_pct_equity?: number | null;
  remaining_to_stop_drawdown_usd?: number | null;
  remaining_to_stop_drawdown_pct_equity?: number | null;
  stop_locked_profit_usd?: number | null;
  risk_cap_pct?: number | null;
  risk_cap_breached?: boolean | null;
  risk_basis?: string;
  risk_economics_source?: string | null;
  stop_risk?: Record<string, unknown>;
  market_tick_observed_at?: string | null;
  market_tick_age_seconds?: number | null;
  market_tick_fresh?: boolean | null;
  market_open?: boolean | null;
  market_tick_status?: string | null;
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

export interface Mt5PermissionState {
  report_kind?: string;
  status: string;
  permission_label: string;
  can_submit_order_send: boolean;
  terminal_connected?: boolean | null;
  terminal_trade_allowed?: boolean | null;
  terminal_algo_trading_enabled?: boolean | null;
  terminal_tradeapi_disabled?: boolean | null;
  account_trade_allowed?: boolean | null;
  account_expert_trading_allowed?: boolean | null;
  account_trade_mode?: number | null;
  blockers: string[];
  plain_english: string;
}

export interface Mt5PositionProtectionReport {
  report_kind?: "cas_forex_position_protection_report";
  generated_at?: string;
  source?: string;
  status: "ALL_POSITIONS_PROTECTED" | "UNPROTECTED_POSITIONS" | "POSITION_PROTECTION_UNAVAILABLE" | string;
  connected?: boolean | null;
  open_position_count: number;
  protected_position_count: number;
  unprotected_position_count: number;
  unprotected_positions: Array<Record<string, unknown>>;
  protected_positions: Array<Record<string, unknown>>;
  all_positions_protected: boolean;
  requires_owner_attention: boolean;
  detail: string;
  claim_boundary?: string;
}

export interface Mt5PositionRiskSummary {
  report_kind?: "cas_forex_open_position_risk_summary";
  status: string;
  open_position_count: number;
  valued_position_count: number;
  unprotected_position_count: number;
  risk_cap_breach_count: number;
  risk_cap_breach_tickets: Array<number | string | null>;
  risk_cap_pct?: number | null;
  combined_entry_to_stop_risk_usd?: number | null;
  combined_entry_to_stop_risk_pct_equity?: number | null;
  combined_remaining_to_stop_drawdown_usd?: number | null;
  detail: string;
  claim_boundary?: string;
}

export interface Mt5MarketTickFreshness {
  report_kind?: "cas_forex_mt5_open_position_tick_freshness";
  status: "FRESH" | "MARKET_CLOSED" | "STALE_OR_PARTIAL" | "UNAVAILABLE" | "NO_OPEN_POSITIONS" | string;
  symbol_count: number;
  fresh_symbol_count: number;
  stale_or_unavailable_symbol_count: number;
  last_tick_observed_at?: string | null;
  last_tick_age_seconds?: number | null;
  oldest_tick_observed_at?: string | null;
  oldest_tick_age_seconds?: number | null;
  all_open_position_ticks_fresh: boolean;
  any_market_open: boolean;
  freshness_limit_seconds: number;
  symbols: Array<Record<string, unknown>>;
  detail: string;
  claim_boundary?: string;
}

export interface Mt5LiveState {
  report_kind?: string;
  connected: boolean;
  is_demo?: boolean;
  account?: Mt5Account;
  positions?: Mt5Position[];
  open_position_count?: number;
  algo_allowed?: boolean;
  permission_state?: Mt5PermissionState;
  position_protection?: Mt5PositionProtectionReport;
  position_risk?: Mt5PositionRiskSummary;
  market_tick?: Mt5MarketTickFreshness;
  claim_boundary?: string;
  mirror_scope?: string;
  mirror_label?: string;
  read_only_label?: string;
  writes_from_panel?: string;
  observational_only?: boolean;
  execution_path_note?: string;
  note?: string;
  detail?: string;
  error?: string;
  cached?: boolean;
  snapshot_observed_at?: string | null;
  snapshot_age_seconds?: number | null;
  snapshot_fresh?: boolean | null;
  snapshot_cache_ttl_seconds?: number | null;
}

export async function fetchMt5Account(): Promise<Mt5LiveState | null> {
  try { return await apiGet<Mt5LiveState>("/mt5/account"); } catch { return null; }
}

export interface BrokerSymbolDiagnostics {
  report_kind?: "cas_forex_broker_symbol_diagnostics" | string;
  generated_at_iso?: string;
  status?: "OK" | "ATTENTION" | string;
  mt5_connected?: boolean;
  symbols_requested?: string[];
  unresolved_symbols?: string[];
  mt5_symbol_overrides_configured?: boolean;
  symbols?: Array<{
    canonical_symbol?: string;
    selected_symbol?: string;
    status?: string;
    diagnostic_status?: string;
    resolution_source?: string;
    static_candidates?: string[];
    contract?: Record<string, unknown>;
    broker_contract_constraints?: {
      min_lot?: number;
      max_lot?: number;
      lot_step?: number;
      stop_level_points?: number;
      freeze_level_points?: number;
      point?: number;
      digits?: number;
      contract_size?: number;
      tick_size?: number;
      tick_value?: number;
    };
  }>;
  claim_boundary?: string;
}

export async function fetchMt5SymbolDiagnostics(symbols?: string[]): Promise<BrokerSymbolDiagnostics | null> {
  const q = symbols && symbols.length ? `?symbols=${encodeURIComponent(symbols.join(","))}` : "";
  try { return await apiGet<BrokerSymbolDiagnostics>(`/mt5/symbol-diagnostics${q}`); } catch { return null; }
}

export async function fetchMt5PositionProtection(
  force = false,
  notify = false,
): Promise<Mt5PositionProtectionReport | null> {
  const q = `?force=${encodeURIComponent(String(force))}&notify=${encodeURIComponent(String(notify))}`;
  try { return await apiGet<Mt5PositionProtectionReport>(`/mt5/protection${q}`); } catch { return null; }
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
  swap?: number;
  commission?: number;
  net_open_pnl?: number;
  opened_at_iso: string | null;
  broker_ticket: string | null;
  price_source?: string | null;
  price_stale?: boolean;
  stale_reason?: string | null;
  age_seconds?: number | null;
  age_days?: number | null;
  position_source_label?: string | null;
}

export interface LiveTelemetryResponse {
  as_of_iso: string;
  open_positions: LiveTelemetryPosition[];
  totals: {
    open_position_count: number;
    total_floating_pnl: number;
    gross_floating_pnl?: number;
    total_swap?: number;
    total_commission?: number;
    total_open_pnl_after_costs?: number;
  };
  telemetry_source?: "mt5_demo_account_snapshot" | "mt5_live_account_snapshot" | "mt5_terminal_api_verifier" | "movement_stream" | "none";
  telemetry_stale?: boolean;
  telemetry_last_update_iso?: string | null;
  account_mode?: "DEMO" | "LIVE" | string | null;
  account_login?: number | string | null;
  account_server?: string | null;
  snapshot_cached?: boolean | null;
  snapshot_age_seconds?: number | null;
  snapshot_fresh?: boolean | null;
  position_protection?: Record<string, unknown> | null;
  position_risk?: Record<string, unknown> | null;
  price_source_status?: string | null;
  position_feed_label?: string;
  position_feed_detail?: string;
  broker_ticket_position_count?: number;
  static_position_count?: number;
  movement_source_truth?: MovementSourceTruthSnapshot | null;
  data_freshness: {
    source: "mt5_demo_account_snapshot" | "mt5_live_account_snapshot" | "mt5_terminal_api_verifier" | "movement_stream" | "none";
    stale: boolean;
    last_update_iso: string | null;
    movement_source?: MovementSourceTruthSnapshot | null;
    account_mode?: "DEMO" | "LIVE" | string | null;
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

export async function fetchAccountHealth(initialInvestment?: number): Promise<AccountHealthReport | null> {
  const suffix = initialInvestment != null ? `?initial_investment=${encodeURIComponent(initialInvestment)}` : "";
  try { return await apiGet<AccountHealthReport>(`/account/health${suffix}`); } catch { return null; }
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

export async function fetchMovementStream(useProvider = true): Promise<MovementStreamState | null> {
  const suffix = useProvider ? "" : "?use_provider=false";
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

export interface AgentDecisionVersionTrace {
  trace_status?: string | null;
  trace_source?: string | null;
  cycle_id?: string | null;
  agent_workflow_version?: string | null;
  agent_ref?: string | null;
  agent_policy_version?: string | null;
  strategy_ref?: string | null;
  strategy_version?: string | null;
  model_ref?: string | null;
  prompt_version?: string | null;
  prompt_hash?: string | null;
  risk_engine_version?: string | null;
  dispatch_engine_version?: string | null;
  execution_router_version?: string | null;
  market_data_source?: string | null;
  broker_mode?: string | null;
  broker_symbol?: string | null;
  broker_bridge?: string | null;
  config_hash?: string | null;
  provenance_hash?: string | null;
  dispatch_provenance_hash?: string | null;
  market_data_refs?: string[];
  gaps?: string[];
  [key: string]: unknown;
}

export interface MovementSourceTruthSnapshot {
  telemetry_source?: string | null;
  telemetry_stale?: boolean;
  telemetry_last_update_iso?: string | null;
  movement_stream_present?: boolean;
  market_data_provider_requested?: boolean;
  market_data_provider?: string | null;
  price_source_status?: string | null;
  price_source_label?: string | null;
  price_source_summary?: string | null;
  price_source_warning?: string | null;
  position_feed_title?: string | null;
  position_feed_count_label?: string | null;
  position_feed_label?: string | null;
  position_feed_detail?: string | null;
  static_simulation_active?: boolean;
  open_position_count?: number;
  broker_ticket_position_count?: number;
  simulator_position_count?: number;
  provider_priced_simulator_position_count?: number;
  static_simulator_position_count?: number;
  static_position_count?: number;
  static_quote_count?: number;
  stale_price_position_count?: number;
  source_label_counts?: Record<string, number>;
  configured_market_data_provider?: string | null;
  provider_usable_symbols?: string[];
  static_fallback_symbols?: string[];
  mt5_fallback_symbols?: string[];
  provider_stale_symbols?: string[];
  closed_market_symbols?: string[];
  closed_market_quote_count?: number;
  provider_freshness_max_age_seconds?: number;
  snapshot_age_seconds_by_symbol?: Record<string, number | null>;
  provider_error_count?: number;
  attention_required?: boolean;
  detail?: string | null;
  local_detail?: string | null;
  account_mode?: "DEMO" | "LIVE" | string | null;
  account_login?: number | string | null;
  account_server?: string | null;
  snapshot_cached?: boolean | null;
  snapshot_age_seconds?: number | null;
  snapshot_fresh?: boolean | null;
  position_protection?: Record<string, unknown> | null;
  position_risk?: Record<string, unknown> | null;
}

export interface AgentDecisionResponse {
  cycle_id: string | null;
  overall_status: string;
  plain_english_summary: string;
  chain: DecisionChainStep[];
  next_action_hint: string | null;
  movement_source_truth?: MovementSourceTruthSnapshot | null;
  version_trace?: AgentDecisionVersionTrace | null;
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
  movement_source_truth?: MovementSourceTruthSnapshot | null;
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
  public_launch_gate_status?: string;
  public_launch_status?: string;
  live_money_production_status?: string;
  public_launch_gate_pass_count?: number;
  public_launch_gate_block_count?: number;
  public_launch_gate_blockers?: string[];
  broker_truth_monitor_status?: string;
  broker_truth_ready_for_live?: boolean;
  broker_truth_paper_force_latched?: boolean;
  broker_truth_halt_reason_ids?: string[];
  broker_truth_halt_reason_labels?: string[];
  broker_truth_halt_reason_summary?: string;
  broker_truth_position_protection_status?: string;
  broker_truth_position_protection_label?: string;
  broker_truth_unprotected_position_count?: number;
  broker_truth_position_protection_detail?: string | null;
  broker_truth_mt5_connected?: boolean | null;
  broker_truth_mt5_is_demo?: boolean | null;
  broker_truth_open_position_count?: number;
  open_position_count?: number;
  total_floating_pnl?: number;
  live_telemetry_source?: string;
  live_telemetry_stale?: boolean;
  live_telemetry_last_update_iso?: string | null;
  live_price_source_status?: string | null;
  live_position_feed_label?: string;
  live_position_feed_detail?: string;
  live_movement_source_truth?: MovementSourceTruthSnapshot | null;
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

export interface PerformanceDisciplineCheck {
  key: string;
  label: string;
  status: "COVERED" | "MISSING" | string;
  matched_fields?: string[];
  critical?: boolean;
}

export interface PerformanceDisciplineRecord {
  strategy_id: string;
  source: string;
  mode_label: string;
  status: "OK" | "ATTENTION" | string;
  covered_count: number;
  requirement_count: number;
  coverage_pct: number;
  critical_missing_count: number;
  critical_missing: string[];
  checks: PerformanceDisciplineCheck[];
  cost_model_present?: boolean;
  out_of_sample_present?: boolean;
  mode_separation_present?: boolean;
}

export interface PerformanceDisciplineReport {
  report_kind: "cas_forex_performance_discipline" | string;
  status: "OK" | "ATTENTION" | string;
  record_count: number;
  attention_count: number;
  requirements: Array<Record<string, unknown>>;
  coverage: Array<Record<string, unknown>>;
  records: PerformanceDisciplineRecord[];
  plain_english_summary: string;
  diagnostic_hints: string[];
  claim_boundary: string;
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

export async function fetchPerformanceDiscipline(
  limit: number,
): Promise<PerformanceDisciplineReport | null> {
  try {
    return await apiGet<PerformanceDisciplineReport>(
      `/strategy-comparison/performance-discipline?limit=${encodeURIComponent(limit)}`,
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
  source_truth?: {
    source_truth_samples?: number;
    telemetry_sources_observed?: Record<string, number>;
    price_source_statuses_observed?: Record<string, number>;
    position_feed_labels_observed?: Record<string, number>;
    mt5_source_samples?: number;
    movement_source_samples?: number;
    unlabeled_source_samples?: number;
    static_simulation_samples?: number;
    mixed_fallback_samples?: number;
    provider_active_samples?: number;
    warming_source_samples?: number;
    position_feed_detail_variants?: string[];
    latest_position_feed_label?: string | null;
    latest_position_feed_detail?: string | null;
    source_truth_observation?: string | null;
  } | null;
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
  telemetry_source: string;
  telemetry_stale: boolean;
  telemetry_last_update_iso: string | null;
  price_source_status: string | null;
  position_feed_label: string;
  position_feed_detail: string;
  broker_ticket_position_count: number;
  static_position_count: number;
  movement_source_truth?: MovementSourceTruthSnapshot | null;
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
  subscription_id: string;
  endpoint_masked: string;
  label: string;
  created_at_iso: string;
}

export interface PushSubscriptionsResponse {
  subscriptions: PushSubscriptionItem[];
  total_subscriptions: number;
}

export interface PushBackendFieldStatus {
  configured: boolean;
  configured_key: string | null;
  masked_value: string | null;
  source: string;
  env_keys: string[];
}

export interface PushBackendSubjectStatus extends PushBackendFieldStatus {
  value: string;
}

export interface PushBackendStatus {
  report_kind: "cas_forex_push_delivery_backend";
  status: string;
  dispatch_backend_available: boolean;
  dispatch_backend_package: string;
  dispatch_backend_version: string | null;
  subscription_count: number;
  browser_subscriptions_present: boolean;
  subscription_registration_ready: boolean;
  dispatch_ready: boolean;
  fully_ready: boolean;
  blockers: string[];
  next_action: string;
  vapid_public_key: string;
  vapid_public_key_configured: boolean;
  vapid_public_key_configured_key: string | null;
  vapid_public_key_source: string;
  vapid_public_key_masked: string | null;
  vapid_private_key: PushBackendFieldStatus;
  vapid_subject: PushBackendSubjectStatus;
  runtime_override_path: string;
  secret_storage?: Record<string, unknown>;
  claim_boundary?: string;
}

export interface PushBackendUpdateResult {
  report_kind: string;
  status: string;
  applied_keys: string[];
  push_backend: PushBackendStatus;
  claim_boundary?: string;
}

export interface PushTestResult {
  subscription_id: string;
  endpoint_masked: string;
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

export async function fetchPushBackendStatus(): Promise<PushBackendStatus | null> {
  try {
    return await apiGet<PushBackendStatus>("/notifications/backend");
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

export async function updatePushBackendConfig(
  patch: Partial<{
    vapid_public_key: string;
    vapid_private_key: string;
    vapid_subject: string;
  }>,
): Promise<PushBackendUpdateResult> {
  return apiPostJson<PushBackendUpdateResult, typeof patch>("/notifications/backend/update", patch);
}

export async function resetPushBackendConfig(): Promise<PushBackendUpdateResult> {
  return apiPost<PushBackendUpdateResult>("/notifications/backend/reset");
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
  subscription_id: string;
  webhook_url_masked: string;
  label: string;
  created_at_iso: string;
  last_used_at_iso: string | null;
}

export interface WebhookSubscriptionsResponse {
  subscriptions: WebhookSubscriptionItem[];
  total_subscriptions: number;
}

export interface WebhookTestResult {
  subscription_id: string;
  webhook_url_masked: string;
  success: boolean;
  status_code: number | null;
  error_message: string | null;
}

export interface WebhookTestResponse {
  results: WebhookTestResult[];
}

export interface CriticalNotificationTestResult {
  report_kind?: "cas_forex_critical_notification_test" | string;
  status?: "DISPATCHED" | "NO_DESTINATIONS" | string;
  audit?: CriticalNotificationAuditRow;
  readiness?: CriticalNotificationReadiness;
  claim_boundary?: string;
}

  export interface CriticalNotificationAuditRow {
  audit_id?: string;
  at?: string;
    source?: string;
    display_state?: "ACTIVE" | "EXPIRED_HISTORICAL" | string;
    display_ttl_seconds?: number;
    display_age_seconds?: number | null;
    display_until_iso?: string | null;
    event?: {
    event_kind?: string;
    title?: string;
    body?: string;
      severity?: string;
      detected_at_iso?: string;
      payload?: Record<string, unknown>;
  };
  subscription_count?: number;
  dispatch_attempt_count?: number;
  dispatch_success_count?: number;
  skipped?: string;
  dispatch_results?: Array<{
    subscription_id?: string;
    webhook_url_masked?: string;
    success?: boolean;
    status_code?: number | null;
    error_message?: string | null;
    response_snippet?: string | null;
  }>;
}

export interface CriticalNotificationAuditReport {
  report_kind?: string;
  generated_at?: string;
  audit_path?: string;
  rows: CriticalNotificationAuditRow[];
  claim_boundary?: string;
}

export interface CriticalNotificationReadiness {
  report_kind?: "cas_forex_critical_notification_delivery_readiness";
  status?: string;
  generated_at?: string;
  subscription_count?: number;
  subscription_labels?: string[];
  recent_audit_count?: number;
  recent_dispatch_attempt_count?: number;
  recent_dispatch_success_count?: number;
  recent_dispatch_failure_count?: number;
  latest_event_kind?: string | null;
  latest_event_at?: string | null;
  local_in_app_alert_channel?: {
    report_kind?: "cas_forex_local_critical_alert_channel" | string;
    status?: string;
    channel?: string;
    audit_path?: string;
    audit_route?: string;
    readiness_route?: string;
    ui_surfaces?: string[];
    poll_interval_seconds?: number;
    recent_audit_count?: number;
    visible_warning_or_alert_count?: number;
    latest_visible_event_kind?: string | null;
    latest_visible_event_at?: string | null;
    owner_setup_required?: boolean;
    claim_boundary?: string;
  };
  offscreen_delivery_status?: string;
  offscreen_destination_count?: number;
  owner_setup_required_for_offscreen_alerts?: boolean;
  blockers?: string[];
  skipped?: string;
  next_action?: string;
  claim_boundary?: string;
}

export async function fetchWebhookSubscriptions(): Promise<WebhookSubscriptionsResponse | null> {
  try {
    return await apiGet<WebhookSubscriptionsResponse>("/webhook-notifications/subscriptions");
  } catch {
    return null;
  }
}

export async function fetchCriticalNotificationAudit(limit = 10): Promise<CriticalNotificationAuditReport | null> {
  try {
    return await apiGet<CriticalNotificationAuditReport>(`/webhook-notifications/critical-audit?limit=${encodeURIComponent(String(limit))}`);
  } catch {
    return null;
  }
}

export async function fetchCriticalNotificationReadiness(limit = 10): Promise<CriticalNotificationReadiness | null> {
  try {
    return await apiGet<CriticalNotificationReadiness>(`/webhook-notifications/critical-readiness?limit=${encodeURIComponent(String(limit))}`);
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
  subscriptionId: string,
): Promise<{ ok: true } | { ok: false; error: ApiPostError }> {
  try {
    await apiPostJson<unknown, { subscription_id: string }>(
      "/webhook-notifications/unsubscribe",
      { subscription_id: subscriptionId },
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
    const requestBody: { label?: string; title?: string; body?: string } = {};
    if (label && label.trim().length > 0) requestBody.label = label.trim();
    if (title) requestBody.title = title;
    if (body) requestBody.body = body;
    const data = await apiPostJson<WebhookTestResponse, typeof requestBody>(
      "/webhook-notifications/test",
      requestBody,
    );
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: toPostError(err) };
  }
}

export async function testCriticalNotificationDelivery(
  title?: string,
  body?: string,
): Promise<{ ok: true; data: CriticalNotificationTestResult } | { ok: false; error: ApiPostError }> {
  try {
    const requestBody: { title?: string; body?: string } = {};
    if (title) requestBody.title = title;
    if (body) requestBody.body = body;
    const data = await apiPostJson<CriticalNotificationTestResult, typeof requestBody>(
      "/webhook-notifications/critical-test",
      requestBody,
    );
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: toPostError(err) };
  }
}

// ── Mobile/PWA/APK readiness ──

export interface MobileReadinessCheck {
  check_id: string;
  status: string;
  success: boolean;
  detail: string;
  evidence?: Record<string, unknown>;
  elapsed_ms?: number;
  attempts?: number;
}

export interface MobileReadinessLatest {
  report_kind: "cas_forex_mobile_readiness_latest";
  status: string;
  source_path: string | null;
  generated_at?: string | null;
  web_base?: string | null;
  phone_quick_start_url?: string | null;
  verification_commands?: MobileVerificationCommands | null;
  next_verification_actions?: MobileNextVerificationAction[];
  package_ready_for_phone_install: boolean;
  physical_phone_verified: boolean;
  phone_browser_observed?: boolean;
  phone_browser_verified?: boolean;
  phone_proof_generated_at?: string | null;
  phone_proof_fresh?: boolean;
  phone_proof_age_seconds?: number | null;
  phone_proof_expires_at?: string | null;
  phone_proof_max_age_hours?: number | null;
  phone_proof_device_class?: string | null;
  phone_proof_installed_mode?: boolean;
  phone_proof_api_base_host?: string | null;
  phone_proof_api_base_network_path?: string | null;
  phone_proof_api_base_source?: string | null;
  phone_observation_generated_at?: string | null;
  phone_observation_fresh?: boolean;
  phone_observation_age_seconds?: number | null;
  phone_observation_expires_at?: string | null;
  phone_observation_max_age_hours?: number | null;
  phone_observation_device_class?: string | null;
  phone_observation_installed_mode?: boolean;
  phone_observation_local_runtime_only?: boolean;
  phone_observation_client_host_source?: string | null;
  phone_observation_effective_client_host?: string | null;
  phone_observation_api_base_host?: string | null;
  phone_observation_api_base_network_path?: string | null;
  phone_observation_api_base_source?: string | null;
  apk_runtime_observation?: Record<string, unknown> | null;
  apk_runtime_status?: string | null;
  apk_runtime_observed?: boolean;
  apk_runtime_verified?: boolean;
  apk_runtime_fresh?: boolean;
  apk_runtime_generated_at?: string | null;
  apk_runtime_age_seconds?: number | null;
  apk_runtime_expires_at?: string | null;
  apk_runtime_device_class?: string | null;
  apk_runtime_installed_mode?: boolean;
  apk_runtime_local_runtime_only?: boolean;
  apk_runtime_client_host_source?: string | null;
  apk_runtime_effective_client_host?: string | null;
  apk_runtime_api_base_host?: string | null;
  apk_runtime_api_base_network_path?: string | null;
  apk_runtime_api_base_source?: string | null;
  apk_install_pairing_proof?: Record<string, unknown> | null;
  apk_install_pairing_verified?: boolean;
  apk_install_pairing_generated_at?: string | null;
  apk_install_pairing_selected_serial?: string | null;
  apk_install_pairing_package_id?: string | null;
  apk_install_pairing_apk_sha256?: string | null;
  apk_install_pairing_current_apk_sha256?: string | null;
  apk_install_pairing_apk_matches_current_artifact?: boolean | null;
  apk_install_pairing_attempt?: Record<string, unknown> | null;
  apk_install_pairing_attempt_recorded?: boolean;
  apk_install_pairing_attempt_status?: string | null;
  apk_install_pairing_attempt_fresh?: boolean;
  apk_install_pairing_attempt_age_seconds?: number | null;
  apk_install_pairing_attempt_expires_at?: string | null;
  apk_install_pairing_attempt_generated_at?: string | null;
  apk_install_pairing_attempt_install_success?: boolean;
  apk_install_pairing_attempt_native_pairing_success?: boolean;
  apk_install_pairing_attempt_dry_run?: boolean;
  apk_install_pairing_attempt_selected_serial?: string | null;
  apk_install_pairing_attempt_package_id?: string | null;
  apk_install_pairing_attempt_apk_sha256?: string | null;
  apk_install_pairing_attempt_current_apk_sha256?: string | null;
  apk_install_pairing_attempt_apk_matches_current_artifact?: boolean | null;
  apk_install_pairing_attempt_message?: string | null;
  apk_artifact?: MobileDebugApkArtifact | null;
  release_apk_artifact?: MobileReleaseApkArtifact | null;
  android_release_signing?: MobileAndroidReleaseSigning | null;
  android_release_signing_ready?: boolean;
  android_release_signing_status?: string | null;
  android_release_signing_detail?: string | null;
  android_release_apk_exists?: boolean;
  android_release_apk_sha256?: string | null;
  paired_api_bases_reachable?: boolean;
  paired_api_bases_status?: string | null;
  paired_api_bases_detail?: string | null;
  android_device_ready?: boolean;
  android_device_count?: number;
  android_device_ready_count?: number;
  android_device_status?: string | null;
  android_device_detail?: string | null;
  android_adb_path?: string | null;
  docker_available: boolean;
  docker_engine_status?: string | null;
  docker_engine_detail?: string | null;
  docker_cli_path?: string | null;
  docker_server_version?: string | null;
  docker_wsl_checked?: boolean;
  docker_wsl_engine_available?: boolean;
  docker_wsl_warnings?: string[];
  docker_desktop_winget_available?: boolean;
  docker_desktop_install_command?: string | null;
  docker_desktop_elevated_install_command?: string | null;
  docker_desktop_install_attempt_status?: string | null;
  docker_desktop_install_attempt_detail?: string | null;
  docker_desktop_install_attempt_returncode?: number | null;
  docker_desktop_install_attempt_installer_exit_code?: number | null;
  docker_desktop_install_attempt_generated_at?: string | null;
  docker_desktop_install_attempt_admin_elevation_required?: boolean;
  summary: string;
  remaining_external_gates: string[];
  checks: MobileReadinessCheck[];
  claim_boundary?: string;
}

export interface MobileVerificationCommands {
  phone_proof_watcher: string;
  phone_verification_session: string;
  mobile_proof_session?: string;
  mobile_final_verification?: string;
  mobile_final_verification_watch?: string;
  mobile_final_verification_watch_all?: string;
  mobile_final_verification_watch_all_live_links?: string;
  mobile_readiness: string;
  mobile_stack: string;
  release_bundle: string;
  apk_debug_build: string;
  apk_build_all?: string;
  apk_release_signing_setup: string;
  apk_release_build: string;
  apk_device_list: string;
  apk_install_pair: string;
  apk_wait_install_pair?: string;
  docker_engine_diagnose?: string;
  docker_desktop_install?: string;
  docker_desktop_install_elevated?: string;
  docker_engine_check: string;
  docker_compose_build: string;
}

export interface MobileNextVerificationAction {
  action_id: string;
  status: string;
  title: string;
  detail: string;
  command?: string | null;
  target_url?: string | null;
  secondary_commands?: string[];
  blocks_completion: boolean;
}

export interface MobilePhoneVerificationSessionPaths {
  json_path: string;
  readme_path: string;
}

export interface MobilePhoneVerificationSession {
  report_kind: "cas_forex_phone_verification_session";
  generated_at?: string | null;
  status: string;
  summary: string;
  web_base?: string | null;
  phone_quick_start_url?: string | null;
  package_ready_for_phone_install?: boolean;
  proof_state?: Record<string, unknown>;
  phone_browser_observed?: boolean;
  phone_browser_verified?: boolean;
  phone_proof_fresh?: boolean;
  phone_proof_age_seconds?: number | null;
  phone_proof_expires_at?: string | null;
  phone_observation_fresh?: boolean;
  phone_observation_age_seconds?: number | null;
  phone_observation_expires_at?: string | null;
  phone_observation_local_runtime_only?: boolean;
  apk_runtime_status?: string | null;
  apk_runtime_observed?: boolean;
  apk_runtime_verified?: boolean;
  apk_runtime_fresh?: boolean;
  apk_runtime_age_seconds?: number | null;
  apk_runtime_expires_at?: string | null;
  apk_install_pairing_verified?: boolean;
  apk_install_pairing_current_apk_sha256?: string | null;
  apk_install_pairing_apk_matches_current_artifact?: boolean | null;
  apk_install_pairing_attempt_status?: string | null;
  apk_install_pairing_attempt_fresh?: boolean;
  apk_install_pairing_attempt_age_seconds?: number | null;
  apk_install_pairing_attempt_message?: string | null;
  apk_install_pairing_attempt_apk_sha256?: string | null;
  apk_install_pairing_attempt_current_apk_sha256?: string | null;
  apk_install_pairing_attempt_apk_matches_current_artifact?: boolean | null;
  android_release_signing_ready?: boolean;
  android_release_signing_status?: string | null;
  android_release_signing_detail?: string | null;
  android_release_apk_exists?: boolean;
  android_release_apk_sha256?: string | null;
  android_device_ready?: boolean;
  android_device_count?: number;
  android_device_ready_count?: number;
  android_device_status?: string | null;
  android_device_detail?: string | null;
  android_adb_path?: string | null;
  docker_available?: boolean;
  docker_engine_status?: string | null;
  docker_engine_detail?: string | null;
  docker_server_version?: string | null;
  docker_wsl_checked?: boolean;
  docker_wsl_engine_available?: boolean;
  docker_wsl_warnings?: string[];
  docker_desktop_winget_available?: boolean;
  docker_desktop_install_command?: string | null;
  docker_desktop_elevated_install_command?: string | null;
  docker_desktop_install_attempt_status?: string | null;
  docker_desktop_install_attempt_detail?: string | null;
  docker_desktop_install_attempt_returncode?: number | null;
  docker_desktop_install_attempt_installer_exit_code?: number | null;
  docker_desktop_install_attempt_generated_at?: string | null;
  docker_desktop_install_attempt_admin_elevation_required?: boolean;
  owner_commands?: Record<string, string>;
  next_verification_actions?: MobileNextVerificationAction[];
  remaining_external_gates?: string[];
  release_artifact_summary?: Record<string, unknown>;
  pairing_context?: Record<string, unknown>;
  phone_verification_steps?: string[];
  default_output_paths?: MobilePhoneVerificationSessionPaths;
  written_paths?: MobilePhoneVerificationSessionPaths;
  claim_boundary?: string;
  [key: string]: unknown;
}

export interface MobileProofGate {
  gate_id: string;
  title: string;
  satisfied: boolean;
  command?: string | null;
  target_url?: string | null;
  detail: string;
}

export interface MobileProofSession {
  report_kind: "cas_forex_mobile_external_proof_session";
  generated_at?: string | null;
  status: string;
  summary: string;
  package_ready_for_phone_install: boolean;
  phone_quick_start_url?: string | null;
  tested_quick_start_url?: string | null;
  phone_proof_target_url?: string | null;
  phone_proof_target_kind?: string;
  pairing_context?: Record<string, unknown>;
  phone_pairing_handoff?: string | null;
  phone_browser_verified: boolean;
  phone_browser_observed: boolean;
  apk_install_pairing_verified: boolean;
  apk_install_pairing_attempt_status?: string | null;
  paired_api_bases_reachable?: boolean;
  paired_api_bases_status?: string | null;
  paired_api_bases_detail?: string | null;
  docker_available: boolean;
  docker_engine_status?: string | null;
  docker_engine_detail?: string | null;
  docker_desktop_install_command?: string | null;
  docker_desktop_elevated_install_command?: string | null;
  docker_desktop_install_attempt_status?: string | null;
  docker_desktop_install_attempt_detail?: string | null;
  docker_desktop_install_attempt_installer_exit_code?: number | null;
  phone_watch_status?: Record<string, unknown>;
  proof_state?: Record<string, unknown>;
  release_artifact_summary?: Record<string, unknown>;
  owner_commands?: Record<string, string>;
  gates: MobileProofGate[];
  remaining_external_gates: string[];
  source_session_status?: string | null;
  source_session_summary?: string | null;
  [key: string]: unknown;
}

export interface MobileVerificationPlan {
  report_kind: "cas_forex_mobile_verification_plan";
  generated_at?: string | null;
  status: string;
  summary: string;
  package_ready_for_phone_install: boolean;
  phone_browser_verified: boolean;
  physical_phone_verified?: boolean;
  apk_install_pairing_verified: boolean;
  apk_install_pairing_attempt_status?: string | null;
  docker_available: boolean;
  docker_engine_status?: string | null;
  docker_desktop_install_attempt_status?: string | null;
  phone_quick_start_url?: string | null;
  phone_proof_target_url?: string | null;
  remaining_external_gates: string[];
  next_verification_actions: MobileNextVerificationAction[];
  owner_commands: Record<string, string>;
  source_paths?: Record<string, string | null | undefined>;
  default_output_paths?: MobilePhoneVerificationSessionPaths;
  written_paths?: MobilePhoneVerificationSessionPaths;
  claim_boundary?: string;
  text?: string;
  [key: string]: unknown;
}

export interface MobileFinalVerification {
  report_kind: "cas_forex_mobile_final_verification";
  generated_at?: string | null;
  status: string;
  summary: string;
  package_ready_for_phone_install: boolean;
  phone_quick_start_url?: string | null;
  phone_browser_verified: boolean;
  apk_install_pairing_verified: boolean;
  docker_available: boolean;
  next_owner_step: string;
  owner_commands: Record<string, string>;
  gates: MobileProofGate[];
  remaining_external_gates: string[];
  proof_session?: Record<string, unknown>;
  default_output_paths?: MobilePhoneVerificationSessionPaths;
  written_paths?: MobilePhoneVerificationSessionPaths;
  [key: string]: unknown;
}

export interface MobileDebugApkArtifact {
  report_kind: "cas_forex_android_debug_apk_artifact";
  artifact_id: "android_debug_apk";
  path: string;
  filename: string;
  content_type: string;
  exists: boolean;
  transfer_ready: boolean;
  size_bytes: number | null;
  sha256: string | null;
  modified_at: string | null;
  download_url_path: string;
  build_command: string;
  install_command: string;
  install_pair_command: string;
  wait_install_pair_command?: string;
  summary: string;
  claim_boundary: string;
}

export interface MobileReleaseApkArtifact {
  report_kind: "cas_forex_android_release_apk_artifact";
  artifact_id: "android_release_apk";
  path: string;
  filename: string;
  content_type: string;
  exists: boolean;
  transfer_ready: boolean;
  size_bytes: number | null;
  sha256: string | null;
  modified_at: string | null;
  download_url_path: string;
  build_command: string;
  setup_command: string;
  setup_json_command: string;
  signing_ready: boolean;
  signing_status: string | null;
  summary: string;
  claim_boundary: string;
}

export interface MobileAndroidReleaseSigning {
  report_kind: "cas_forex_android_release_signing_status";
  status: string;
  ready: boolean;
  summary: string;
  inputs_present: Record<string, boolean>;
  input_sources: Record<string, string>;
  keystore_properties_exists: boolean;
  keystore_properties_path: string;
  store_file_configured: boolean;
  store_file_is_absolute: boolean;
  store_file_exists: boolean;
  release_apk_exists: boolean;
  release_apk_size_bytes: number | null;
  release_apk_sha256: string | null;
  release_apk_modified_at: string | null;
  release_apk_path: string;
  build_command: string;
  setup_command: string;
  setup_json_command: string;
  claim_boundary: string;
}

export interface MobilePhoneProofPayload {
  source: string;
  app_surface: "pwa" | "apk" | "web";
  url_origin: string;
  url_path: string;
  api_base?: string | null;
  display_mode: "browser" | "standalone" | "fullscreen" | "minimal-ui" | "unknown";
  standalone_pwa: boolean;
  user_agent: string;
  platform: string;
  language: string;
  timezone: string;
  viewport_width: number;
  viewport_height: number;
  screen_width: number;
  screen_height: number;
  device_pixel_ratio: number;
  max_touch_points: number;
  online: boolean;
}

export interface MobilePhoneProofResponse {
  report_kind: "cas_forex_phone_runtime_proof";
  generated_at: string;
  phone_browser_observed?: boolean;
  phone_browser_verified: boolean;
  local_runtime_only?: boolean;
  effective_client_host?: string | null;
  client_host_source?: string | null;
  api_base_host?: string | null;
  api_base_network_path?: string | null;
  api_base_source?: string | null;
  installed_mode_detected: boolean;
  device_class: string;
  claim_boundary: string;
}

export async function fetchMobileReadinessLatest(): Promise<MobileReadinessLatest | null> {
  try {
    return await apiGet<MobileReadinessLatest>("/mobile/readiness/latest", 45_000);
  } catch {
    return null;
  }
}

export async function fetchMobileVerificationSessionLatest(): Promise<MobilePhoneVerificationSession | null> {
  try {
    return await apiGet<MobilePhoneVerificationSession>("/mobile/verification-session/latest", 45_000);
  } catch {
    return null;
  }
}

export async function fetchMobileProofSessionLatest(): Promise<MobileProofSession | null> {
  try {
    return await apiGet<MobileProofSession>("/mobile/proof-session/latest", 45_000);
  } catch {
    return null;
  }
}

export async function fetchMobileVerificationPlanLatest(): Promise<MobileVerificationPlan | null> {
  try {
    return await apiGet<MobileVerificationPlan>("/mobile/verification-plan/latest", 45_000);
  } catch {
    return null;
  }
}

export async function refreshMobileVerificationPlan(): Promise<MobileVerificationPlan | null> {
  try {
    return await apiPost<MobileVerificationPlan>("/mobile/verification-plan/refresh");
  } catch {
    return null;
  }
}

export async function fetchMobileFinalVerificationLatest(): Promise<MobileFinalVerification | null> {
  try {
    return await apiGet<MobileFinalVerification>("/mobile/final-verification/latest", 45_000);
  } catch {
    return null;
  }
}

export async function refreshMobileFinalVerification(): Promise<MobileFinalVerification | null> {
  try {
    return await apiPost<MobileFinalVerification>("/mobile/final-verification/refresh");
  } catch {
    return null;
  }
}

export async function refreshMobileVerificationSession(): Promise<MobilePhoneVerificationSession | null> {
  try {
    return await apiPost<MobilePhoneVerificationSession>("/mobile/verification-session/refresh");
  } catch {
    return null;
  }
}

export async function fetchMobileDebugApkArtifact(): Promise<MobileDebugApkArtifact | null> {
  try {
    return await apiGet<MobileDebugApkArtifact>("/mobile/apk/debug/metadata", 10_000);
  } catch {
    return null;
  }
}

export async function fetchMobileReleaseApkArtifact(): Promise<MobileReleaseApkArtifact | null> {
  try {
    return await apiGet<MobileReleaseApkArtifact>("/mobile/apk/release/metadata", 10_000);
  } catch {
    return null;
  }
}

export async function downloadMobileDebugApk(): Promise<{ blob: Blob; filename: string }> {
  const result = await apiDownloadBlob("/mobile/apk/debug/download", 45_000);
  return {
    blob: result.blob,
    filename: result.filename || "cas-forex-debug.apk",
  };
}

export async function downloadMobileReleaseApk(): Promise<{ blob: Blob; filename: string }> {
  const result = await apiDownloadBlob("/mobile/apk/release/download", 45_000);
  return {
    blob: result.blob,
    filename: result.filename || "cas-forex-release.apk",
  };
}

export async function postMobilePhoneProof(
  payload: MobilePhoneProofPayload,
): Promise<MobilePhoneProofResponse | null> {
  try {
    return await apiPostJson<MobilePhoneProofResponse, MobilePhoneProofPayload>(
      "/mobile/phone-proof",
      payload,
      8_000,
    );
  } catch {
    return null;
  }
}

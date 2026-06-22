// CAS Forex — TypeScript contracts for the read-only proof cockpit.
//
// These types mirror the real Pydantic/JSON shapes emitted by the CAS Forex
// backend (cas-forex/cas_forex/*.py) into evidence_runs/*.json. They are kept
// faithful to the day-1 evidence so the UI displays TRUTHFUL state, never a
// glossy mockup. Fields the cockpit does not yet read are intentionally typed
// loosely (optional / Record) rather than omitted.
//
// Claim boundary (hard, non-negotiable): CAS Forex is research/paper-proof
// infrastructure only. Live trading, broker ACCEPT, auto-deposit,
// debit/card/bank transfer, and payout automation remain NOT LICENSED.

/** Claim-status words. "NOT LICENSED" is the live/payment hard boundary. */
export type ClaimStatus =
  | 'NOT LICENSED'
  | 'OPEN'
  | 'PASS'
  | 'FAIL'
  | 'SUPPRESSED'
  | 'VERIFIED'
  | 'UNAVAILABLE';

/** Broker/operating mode surfaced in the global banner. Never green-LIVE. */
export type ForexBrokerMode =
  | 'SIMULATED'
  | 'PAPER_MT5'
  | 'PAPER_MT4'
  | 'LIVE_LOCKED'
  | 'NOT_LICENSED';

export type RouteAction =
  | 'ROUTE_PAPER_SIGNAL'
  | 'NO_TRADE'
  | 'NO_TRADE_MACRO_LOCK'
  | 'UNAVAILABLE';

export type ReceiptValidationStatus =
  | 'PLAN_ONLY'
  | 'BROKER_EXPORT_HASHED'
  | 'BROKER_API_VERIFIED';

// ── Paper-proof status (index-tsmom-126-d1-paper-proof-status.json) ──────────

export interface PaperProofDailySummary {
  date: string;
  trading_day: number;
  lead_id: string;
  strategy_setting: string;
  symbols: string[];
  timeframe: string;
  broker_mode: string;
  server: string;
  terminal_name: string;
  broker_source_verified: boolean;
  broker_api_authenticated: boolean;
  broker_receipt_validated: boolean;
  receipt_validation_status: ReceiptValidationStatus;
  broker_receipt_hash_sha256: string;
  broker_export_sha256: string;
  account_id_hash: string;
  plan_id: string;
  receipt_id: string;
  provider_receipt_id: string;
  orders_attempted: number;
  orders_paper_executed: number;
  open_positions_reconciled: boolean;
  live_mode: boolean;
  deployment_status: string;
  claim_boundary: string;
}

export interface PaperProofReport {
  report_id: string;
  session_id: string;
  required_trading_days: number;
  completed_trading_days: number;
  symbols: string[];
  started_at: string;
  completed_at: string;
  packet_count: number;
  chain_verified: boolean;
  live_mode_used: boolean;
  open_positions_reconciled: boolean;
  live_locks: string[];
  daily_summaries: PaperProofDailySummary[];
  passed: boolean;
  failure_reasons: string[];
}

export interface PaperProofStatus {
  claim_boundary: string;
  deployment_status: string;
  broker_accept_status: string;
  payment_transfer_status: string;
  report: PaperProofReport;
}

// ── UI readiness (…-ui-readiness-status.json) ────────────────────────────────

export type UiReadinessStatusValue =
  | 'NOT_READY_FOR_UI_UX'
  | 'READY_FOR_UI_UX';

export interface UiReadinessStatus {
  report_id: string;
  plan_id: string;
  lead_id: string;
  strategy_setting: string;
  timeframe: string;
  readiness_status: UiReadinessStatusValue;
  min_daily_bundles_for_ui: number;
  completed_trading_days: number;
  broker_verified_days: number;
  decision_days: number;
  risk_review_days: number;
  complete_bundle_days: number;
  complete_bundle_dates: string[];
  route_counts: Record<string, number>;
  risk_status_counts: Record<string, number>;
  chains_verified: {
    paper_proof: boolean;
    paper_decision: boolean;
    paper_risk: boolean;
  };
  blockers: string[];
  next_ui_step: string;
  claim_boundary: string;
  deployment_status: string;
  broker_accept_status: string;
  payment_transfer_status: string;
}

// ── Daily schedule / next action (…-daily-schedule-status.json) ──────────────

export type NextDueStatus =
  | 'DUE_TODAY'
  | 'WAIT_NEXT_TRADING_DAY'
  | 'COMPLETE';

export interface DailyScheduleStatus {
  schedule_id: string;
  plan_id: string;
  lead_id: string;
  strategy_setting: string;
  timeframe: string;
  as_of_date: string;
  next_due_date: string;
  next_due_status: NextDueStatus;
  latest_complete_bundle_date: string | null;
  complete_bundle_days: number;
  completed_trading_days: number;
  broker_verified_days: number;
  decision_days: number;
  risk_review_days: number;
  ui_min_daily_bundles: number;
  ui_bundles_remaining: number;
  required_paper_days: number;
  paper_days_remaining: number;
  missing_tracks_for_next_due: string[];
  complete_bundle_dates: string[];
  recommended_command: string;
  notes: string[];
  claim_boundary: string;
  deployment_status: string;
  broker_accept_status: string;
  payment_transfer_status: string;
}

// ── Paper route/no-trade decision (…-paper-decision-status.json) ─────────────

export interface PaperProposal {
  proposal_id: string;
  symbol: string;
  direction: 'LONG' | 'SHORT';
  confidence: number;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  timeframe: string;
  horizon_minutes: number;
  model_source: string;
  model_version: string;
  rationale: string;
  timestamp: string;
}

export interface PaperSymbolDecision {
  symbol: string;
  action: RouteAction;
  direction: 'LONG' | 'SHORT';
  confidence: number;
  latest_close: number;
  bars_used: number;
  sl_mult: number;
  tp_mult: number;
  reason: string;
  proposal: PaperProposal;
}

export interface PaperDecision {
  decision_id: string;
  date: string;
  lead_id: string;
  strategy_setting: string;
  timeframe: string;
  route_action: RouteAction;
  macro_status: string;
  macro_reason: string;
  event_context: string;
  symbol_decisions: PaperSymbolDecision[];
  notes: string[];
  claim_boundary: string;
}

export interface PaperDecisionStatus {
  plan_id: string;
  lead_id: string;
  strategy_setting: string;
  decision_count: number;
  route_counts: Record<string, number>;
  chain_verified: boolean;
  latest_decision: PaperDecision;
  claim_boundary: string;
}

// ── Paper risk-budget review (…-paper-risk-status.json) ──────────────────────

export interface PaperRiskSizing {
  symbol: string;
  proposal_id: string;
  action: RouteAction;
  attempt_number: number;
  attempt_status: string;
  direction: 'LONG' | 'SHORT';
  confidence: number;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  sized_lots: number;
  raw_lots: number;
  planned_risk_usd: number;
  planned_risk_pct: number;
  max_risk_usd: number;
  risk_per_lot_usd: number;
  stop_distance_units: number;
  unit_name: string;
  unit_value_per_lot_usd: number;
  reason: string;
}

export interface PaperRiskReview {
  review_id: string;
  date: string;
  lead_id: string;
  strategy_setting: string;
  timeframe: string;
  route_action: RouteAction;
  risk_status: string;
  account_equity: number;
  max_risk_per_trade_pct: number;
  daily_risk_budget_pct: number;
  daily_risk_budget_usd: number;
  max_position_lots: number;
  max_paper_attempts: number;
  proposed_attempts: number;
  allowed_attempts: number;
  suppressed_attempts: number;
  total_planned_lots: number;
  total_planned_risk_usd: number;
  total_planned_risk_pct: number;
  sizing: PaperRiskSizing[];
  blockers: string[];
  notes: string[];
  deployment_status: string;
  broker_accept_status: string;
  payment_transfer_status: string;
  claim_boundary: string;
}

export interface PaperRiskStatus {
  plan_id: string;
  lead_id: string;
  strategy_setting: string;
  review_count: number;
  risk_status_counts: Record<string, number>;
  chain_verified: boolean;
  latest_review: PaperRiskReview;
  claim_boundary: string;
}

// ── Daily bundle (…-daily-bundle-status.json) ────────────────────────────────

export interface BundleStep {
  name: string;
  status: string;
  detail: string;
  artifact: string | null;
  reasons: string[];
}

export interface DailyBundleStatus {
  bundle_id: string;
  plan_id: string;
  lead_id: string;
  strategy_setting: string;
  date: string;
  timeframe: string;
  steps: BundleStep[];
  completed: boolean;
  ui_ux_checkpoint: string;
  claim_boundary: string;
  deployment_status: string;
  broker_accept_status: string;
  payment_transfer_status: string;
}

// ── Aggregate bundle loaded by the cockpit ───────────────────────────────────

/** Everything the proof cockpit needs in one read. */
export interface ForexProofBundle {
  paperProof: PaperProofStatus;
  uiReadiness: UiReadinessStatus;
  schedule: DailyScheduleStatus;
  decision: PaperDecisionStatus;
  risk: PaperRiskStatus;
  bundle: DailyBundleStatus;
  /** True when served from bundled fixtures rather than a live backend. */
  fromFixtures: boolean;
}

// ── Audit-console trace model (derived, see forexSelectors.ts) ───────────────

export type PipelineStageStatus =
  | 'PASS'
  | 'ROUTED'
  | 'ALLOWED'
  | 'SUPPRESSED'
  | 'NO_ORDER'
  | 'VERIFIED'
  | 'CLEAR'
  | 'LIVE_LOCKED'
  | 'NOT_RUN';

export interface PipelineStage {
  key: string;
  label: string;
  status: PipelineStageStatus;
  detail: string;
  /** False when the day-1 paper-route loop did not exercise this stage. */
  exercised: boolean;
}

export type EvidencePacketStatus =
  | 'PROPOSED'
  | 'ACCEPTED'
  | 'SUPPRESSED'
  | 'FLAG_FOR_HUMAN_REVIEW'
  | 'EXECUTED'
  | 'REJECTED'
  | 'CANCELLED'
  | 'CLOSED_WIN'
  | 'CLOSED_LOSS'
  | 'LIVE_LOCKED'
  | 'WRITE_FAILED';

export interface ForexEvidenceHash {
  label: string;
  hash: string;
  verified?: boolean;
}

/** One audit trace: a paper route candidate walked through the pipeline. */
export interface ForexTrace {
  trace_id: string;
  symbol: string;
  date: string;
  timeframe: string;
  direction: 'LONG' | 'SHORT';
  confidence: number;
  route_action: RouteAction;
  packet_status: EvidencePacketStatus;
  broker_order_placed: boolean;
  sized_lots: number | null;
  planned_risk_usd: number | null;
  stages: PipelineStage[];
  hashes: ForexEvidenceHash[];
  chain_verified: boolean;
}

// ── Derived banner state (selector output, see forexSelectors.ts) ────────────

export interface ForexBannerState {
  mode: ForexBrokerMode;
  paperTrading: boolean;
  liveMode: boolean;
  deploymentStatus: string;
  brokerAcceptStatus: string;
  paymentTransferStatus: string;
  evidenceChainVerified: boolean;
  paperProof: { completed: number; required: number };
  multiDayMaturity: { complete: number; required: number; ready: boolean };
  liveLockActive: boolean;
  fromFixtures: boolean;
}

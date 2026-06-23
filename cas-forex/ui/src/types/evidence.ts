/* ── CAS Forex — Evidence Types ── */

export interface UIReadinessReport {
  report_id: string;
  plan_id: string;
  lead_id: string;
  strategy_setting: string;
  timeframe: string;
  readiness_status: "READY_FOR_PROOF_COCKPIT_UI_UX" | "NOT_READY_FOR_UI_UX";
  min_daily_bundles_for_ui: number;
  completed_trading_days: number;
  broker_verified_days: number;
  decision_days: number;
  risk_review_days: number;
  complete_bundle_days: number;
  complete_bundle_dates: string[];
  route_counts: Record<string, number>;
  risk_status_counts: Record<string, number>;
  chains_verified: Record<string, boolean>;
  blockers: string[];
  next_ui_step: string;
  claim_boundary: string;
  deployment_status: "NOT LICENSED" | "LICENSED";
  broker_accept_status: "NOT LICENSED" | "LICENSED";
  payment_transfer_status: "NOT LICENSED" | "LICENSED";
}

export interface DailySchedule {
  schedule_id: string;
  plan_id: string;
  lead_id: string;
  strategy_setting: string;
  timeframe: string;
  as_of_date: string;
  next_due_date: string;
  next_due_status: string;
  latest_complete_bundle_date: string;
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
  deployment_status: "NOT LICENSED" | "LICENSED";
  broker_accept_status: "NOT LICENSED" | "LICENSED";
  payment_transfer_status: "NOT LICENSED" | "LICENSED";
}

export interface Proposal {
  proposal_id: string;
  symbol: string;
  direction: "LONG" | "SHORT";
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  confidence: number;
  timeframe: string;
  horizon_minutes: number;
  model_source: string;
  model_version: string;
  rationale: string;
  timestamp: string;
}

export interface SymbolDecision {
  symbol: string;
  action: string;
  direction: "LONG" | "SHORT";
  confidence: number;
  latest_close: number;
  bars_used: number;
  sl_mult: number;
  tp_mult: number;
  reason: string;
  proposal: Proposal;
}

export interface PaperDecision {
  plan_id: string;
  lead_id: string;
  strategy_setting: string;
  decision_count: number;
  route_counts: Record<string, number>;
  chain_verified: boolean;
  claim_boundary: string;
  latest_decision: {
    date: string;
    decision_id: string;
    plan_id: string;
    lead_id: string;
    strategy_setting: string;
    route_action: string;
    timeframe: string;
    macro_status: string;
    macro_reason: string;
    event_context: string;
    claim_boundary: string;
    notes: string[];
    symbol_decisions: SymbolDecision[];
  };
}

export interface SizingEntry {
  symbol: string;
  action: string;
  direction: "LONG" | "SHORT";
  confidence: number;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  attempt_number: number;
  attempt_status: string;
  sized_lots: number;
  raw_lots: number;
  max_risk_usd: number;
  planned_risk_pct: number;
  planned_risk_usd: number;
  stop_distance_units: number;
  risk_per_lot_usd: number;
  unit_name: string;
  unit_value_per_lot_usd: number;
  proposal_id: string;
  reason: string;
}

export interface PaperRisk {
  plan_id: string;
  lead_id: string;
  strategy_setting: string;
  review_count: number;
  risk_status_counts: Record<string, number>;
  chain_verified: boolean;
  latest_review: {
    date: string;
    review_id: string;
    risk_status: string;
    route_action: string;
    account_equity: number;
    max_risk_per_trade_pct: number;
    daily_risk_budget_pct: number;
    daily_risk_budget_usd: number;
    max_position_lots: number;
    max_paper_attempts: number;
    allowed_attempts: number;
    proposed_attempts: number;
    existing_attempts: number;
    attempts_remaining_before_review: number;
    claim_boundary: string;
    deployment_status: string;
    broker_accept_status: string;
    payment_transfer_status: string;
    plan_id: string;
    lead_id: string;
    blockers: string[];
    notes: string[];
    sizing: SizingEntry[];
  };
}

export interface DailyBundleStep {
  name: string;
  status: string;
  detail: string;
  artifact: string | null;
  reasons: string[];
}

export interface DailyBundle {
  bundle_id: string;
  plan_id: string;
  lead_id: string;
  strategy_setting: string;
  date: string;
  timeframe: string;
  steps: DailyBundleStep[];
  completed: boolean;
  latest_proof: {
    status_path: string;
    completed_trading_days: number;
    required_trading_days: number;
    chain_verified: boolean;
    passed: boolean;
    failure_reasons: string[];
  };
  latest_decision: PaperDecision;
  latest_risk: PaperRisk;
  claim_boundary: string;
  deployment_status: "NOT LICENSED" | "LICENSED";
  broker_accept_status: "NOT LICENSED" | "LICENSED";
  payment_transfer_status: "NOT LICENSED" | "LICENSED";
  completed_steps: number;
  total_steps: number;
  overall_status: string;
}

export type AdaptiveAction =
  | "OPEN_INITIAL" | "ADD_TO_WINNER" | "HOLD" | "TIGHTEN_STOP"
  | "PARTIAL_TAKE_PROFIT" | "CLOSE_BASKET" | "NO_TRADE";

export interface BasketState {
  basket_id: string; symbol: string; direction: string;
  open_positions: number; total_lots: number;
  average_entry: number | null; current_price: number | null;
  floating_profit_units: number; floating_profit_usd: number; floating_profit_r: number;
  best_stop_loss: number | null; farthest_take_profit: number | null;
}

export interface AdaptiveTradeDecision {
  symbol: string; action: string; reason: string;
  direction: string | null; lot_size: number;
  entry_price: number | null; stop_loss: number | null; take_profit: number | null;
  confidence: number | null; evidence_score: number; evidence_status: string;
  evidence_refs: string[]; basket_id: string | null; source_proposal_id: string | null;
}

export interface AdaptiveMemorySnapshot {
  snapshot_id: string; snapshot_type: string; symbol: string;
  timeframe: string; strategy_setting: string; event_context: string; regime: string;
  action: string; direction: string | null; confidence: number | null;
  evidence_score: number; basket_profit_r: number; basket_open_positions: number;
  notes: string[];
}

export interface AdaptiveCompoundingConfig {
  max_basket_positions: number; base_lot: number;
  compound_lot_multiplier: number; max_add_lot: number;
  min_compound_profit_r: number; partial_take_profit_r: number; close_basket_loss_r: number;
  min_add_confidence: number; min_hold_confidence: number; min_evidence_score: number;
  adaptive_sl_mult: number; adaptive_tp_mult: number;
}

export interface AdaptiveCompoundingReview {
  review_id: string; plan_id: string; lead_id: string;
  strategy_setting: string; date: string; timeframe: string;
  source_decision_id: string | null; route_action: string; account_equity: number;
  config: AdaptiveCompoundingConfig;
  baskets: BasketState[]; decisions: AdaptiveTradeDecision[];
  memory_snapshots: AdaptiveMemorySnapshot[]; notes: string[];
  claim_boundary: string; deployment_status: string;
  broker_accept_status: string; payment_transfer_status: string;
}

export interface AdaptiveCockpitPayload {
  plan_id: string; lead_id: string; strategy_setting: string; timeframe: string;
  cockpit_status: string;
  adaptive_action_counts: Record<string, number>;
  latest_adaptive_decisions: AdaptiveTradeDecision[];
  adaptive_compounding: {
    review_count: number; action_counts: Record<string, number>;
    chain_verified: boolean; latest_review: AdaptiveCompoundingReview | null;
  };
  claim_boundary: string; deployment_status: string;
  broker_accept_status: string; payment_transfer_status: string;
}

export type OwnerControlMode = "DENY" | "NOTIFY_ONLY" | "LIMITED_PAPER" | "PAPER_AUTO" | "AI_FULL_AUTO_PAPER" | "LIVE_AUTO" | "AI_FULL_AUTO_LIVE_REQUESTED";

export interface OwnerControlState {
  mode: OwnerControlMode; max_concurrent_trades: number;
  max_loss_cap_pct: number; ai_autonomy_enabled: boolean;
  live_requested: boolean; live_blocked: boolean; claim_boundary: string;
}

export interface MTHistorySummary {
  source: string; total_trades: number; win_rate: number; profit_factor: number;
  total_profit: number; total_loss: number; net_pnl: number;
  symbol_performance: Record<string, { trades: number; win_rate: number; profit_factor: number; net_pnl: number }>;
  multi_trade_bursts: number; import_date: string;
}

export interface BacksolveSummary {
  run_id: string; total_scenarios: number; viable_scenarios: number;
  ai_autonomy_mode: string; ai_selection: string | null;
  required_return_math: { target_5k_on_5k_pct: number; target_12k_on_5k_pct: number };
  verdict_counts: Record<string, number>;
  capital_label: "SURVIVAL_RISK";
  claim_boundary: string; deployment_status: string;
}

export interface ConditionTallyBucket {
  key: string; axes: Record<string, string>;
  windows: number; routed_windows: number; active_windows: number;
  positive_windows: number; positive_window_rate: number;
  total_return_pct: number; mean_return_pct: number; max_drawdown_pct: number; trades: number;
}

export interface WalkForwardSummary {
  run_id: string; total_windows: number; routed_windows: number;
  active_routed_windows: number; positive_active_routed_windows: number;
  routed_total_return_pct: number; active_routed_mean_return_pct: number;
  routed_max_drawdown_pct: number; total_routed_trades: number;
  research_grade: string; symbols: string[]; claim_boundary: string;
}

export interface MT5Receipt {
  receipt_id: string; receipt_validation_status: string; broker_mode: string;
  trading_date: string; symbols: string[]; orders_attempted: number;
  open_positions_reconciled: boolean; live_mode: boolean;
  broker_api_authenticated: boolean; broker_source_verified: boolean;
  server: string; terminal_name: string;
  receipt_hash_sha256: string; broker_export_sha256: string;
  packet_hash: string; record_hash: string;
  chain_verified: boolean; worm_retained: boolean;
}

export interface StrategyLead {
  lead_id: string; priority: number;
  status: "ACTIVE_RESEARCH_LEAD" | "WATCHLIST_ONLY" | "PROMOTED" | "ARCHIVED";
  strategy_setting: string; family: string; mode: string;
  symbols_promoted_for_next_tests: string[]; symbols_watchlist: string[];
  headline_results: string[]; open_gates: string[]; evidence_refs: string[];
  deployment_status: string;
}

export interface AuthorityBoundaryState {
  report_kind: string; operating_mode: string;
  live_trading_status: string; broker_accept_status: string;
  auto_deposit_status: string; debit_card_bank_movement_status: string;
  payout_automation_status: string; trading_edge_status: string;
  can_place_live_orders: boolean; can_create_broker_accept: boolean;
  can_auto_deposit: boolean; can_move_money: boolean; can_automate_payouts: boolean;
  allowed_scopes: string[]; blockers: string[]; claim_boundary: string;
  ledger_deployment_status_counts: Record<string, number>;
  live_execution_runtime_locked: boolean;
}

export interface RuntimeGateDecision {
  capability: string; authorized: boolean; status: string;
  missing_requirements: string[]; satisfied_requirements: string[]; next_action: string;
}

export interface RuntimeGatesState {
  report_kind: string;
  decisions: Record<string, RuntimeGateDecision>;
  all_real_money_authorized: boolean;
  summary: string;
}

export interface AIModelState {
  enabled: boolean; backend: string; model_name: string; base_url: string;
  configured: boolean; has_api_key: boolean; control_plane: string;
  pcba_guard_enabled: boolean; authority_boundary: string;
}

export interface BrokerCandidate {
  broker_id: string; display_name: string; website: string;
  platform_notes: string; owner_research_leverage_note: string;
  configured_env_prefix: string; verification_status: string;
  live_use_status: string; notes: string;
}


export interface ReadinessCheck {
  feature?: string;
  board_kind?: string;
  status: string;
  ready?: boolean;
  claim_ceiling?: string;
  required_evidence: string[];
  present_evidence: string[];
  missing_evidence: string[];
  can_affect_live_trading?: boolean;
  can_create_broker_accept?: boolean;
  rationale?: string;
}

export interface PcbaReferenceBoard {
  board_id: string; board_kind: string; purpose: string;
  component_kinds: string[]; test_points: string[]; failure_modes: string[];
  claim_ceiling: string; can_unlock_live_trading: boolean; can_create_broker_accept: boolean;
}

export interface PcbaComponentCatalogEntry {
  kind: string; role: string; claim: string;
}

export interface PcbaCockpitPayload {
  report_kind: string; panels_active: boolean; source: string; claim_boundary: string;
  summary: {
    pcba_ready_checks: number; pcba_total_checks: number;
    cjt_ready_checks: number; cjt_total_checks: number;
    ccb_designs_well_formed: boolean; ccb_claims_licensed: boolean;
    goal_complete: boolean; current_boundary_honest: boolean;
  };
  local_evidence: {
    pcba: Record<string, boolean>; cjt: Record<string, boolean>;
    pcba_present_count: number; pcba_total_count: number;
    cjt_present_count: number; cjt_total_count: number;
  };
  reference_boards: PcbaReferenceBoard[];
  component_catalog: PcbaComponentCatalogEntry[];
  pcba_readiness: {
    report_id: string; generated_at: string; summary: string; all_ready: boolean;
    any_live_authority: boolean; any_broker_accept_authority: boolean; checks: ReadinessCheck[];
  };
  cjt_readiness: {
    report_id: string; generated_at: string; summary: string; all_ready: boolean;
    any_live_authority: boolean; any_broker_accept_authority: boolean; checks: ReadinessCheck[];
  };
  ccb_readiness: {
    report_id: string; summary: string; all_designs_well_formed: boolean; any_claim_licensed: boolean;
    board_checks: ReadinessCheck[];
    prediction_head: { status: string; ready: boolean; required_evidence: string[]; present_evidence: string[]; missing_evidence: string[]; rationale: string; };
  };
  optimizer_guard: {
    guard: string; active: boolean; proposal_counts: { research_queue: number; flagged: number; rejected: number };
    claim_boundary: string; can_create_broker_accept: boolean; can_unlock_live_trading: boolean;
  };
  goal_status: Record<string, unknown>;
}

export interface DashboardState {
  uiReadiness: UIReadinessReport;
  dailySchedule: DailySchedule;
  dailyBundle: DailyBundle;
  adaptive?: AdaptiveCockpitPayload;
  ownerControl?: OwnerControlState;
  mtHistory?: MTHistorySummary;
  strategyLeads?: StrategyLead[];
  backsolve?: BacksolveSummary;
  conditionTally?: ConditionTallyBucket[];
  walkForward?: WalkForwardSummary;
  mt5Receipt?: MT5Receipt;
  authorityBoundary?: AuthorityBoundaryState;
  runtimeGates?: RuntimeGatesState;
  aiModel?: AIModelState;
  brokerCandidates?: BrokerCandidate[];
  pcba?: PcbaCockpitPayload;
}

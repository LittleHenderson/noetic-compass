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
  complete_bundle_date_count?: number;
  route_counts: Record<string, number>;
  risk_status_counts: Record<string, number>;
  chains_verified: Record<string, boolean>;
  blockers: string[];
  blocker_count?: number;
  next_ui_step: string;
  next_ui_step_present?: boolean;
  claim_boundary: string;
  claim_boundary_present?: boolean;
  deployment_status: "NOT LICENSED" | "LICENSED";
  broker_accept_status: "NOT LICENSED" | "LICENSED";
  payment_transfer_status: "NOT LICENSED" | "LICENSED";
  summary_only?: boolean;
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
  missing_track_count?: number;
  complete_bundle_dates: string[];
  complete_bundle_date_count?: number;
  recommended_command: string;
  recommended_action?: string;
  notes: string[];
  note_count?: number;
  claim_boundary: string;
  claim_boundary_present?: boolean;
  deployment_status: "NOT LICENSED" | "LICENSED";
  broker_accept_status: "NOT LICENSED" | "LICENSED";
  payment_transfer_status: "NOT LICENSED" | "LICENSED";
  summary_only?: boolean;
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
  claim_boundary_present?: boolean;
  summary_only?: boolean;
  symbol_decision_count?: number;
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
    claim_boundary_present?: boolean;
    notes: string[];
    note_count?: number;
    summary_only?: boolean;
    symbol_decision_count?: number;
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
  claim_boundary?: string;
  claim_boundary_present?: boolean;
  summary_only?: boolean;
  sizing_count?: number;
  planned_risk_total_usd?: number;
  planned_lots_total?: number;
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
    claim_boundary_present?: boolean;
    deployment_status: string;
    broker_accept_status: string;
    payment_transfer_status: string;
    plan_id: string;
    lead_id: string;
    blockers: string[];
    blocker_count?: number;
    notes: string[];
    note_count?: number;
    summary_only?: boolean;
    sizing_count?: number;
    planned_risk_total_usd?: number;
    planned_lots_total?: number;
    sizing: SizingEntry[];
  };
}

export interface DashboardRiskBudgetSummary {
  report_kind: string;
  date: string;
  review_count: number;
  risk_status: string;
  risk_status_counts: Record<string, number>;
  chain_verified: boolean;
  account_equity: number;
  max_risk_per_trade_pct: number;
  daily_risk_budget_pct: number;
  daily_risk_budget_usd: number;
  max_position_lots: number;
  planned_risk_total_usd: number;
  planned_lots_total: number;
  sizing_count: number;
  summary_only?: boolean;
  claim_boundary?: string;
  claim_boundary_present?: boolean;
}

export interface DashboardProofProgressSummary {
  report_kind: string;
  readiness_status: string;
  min_daily_bundles_for_ui: number;
  completed_trading_days: number;
  complete_bundle_days: number;
  complete_bundle_date_count: number;
  chains_verified_count: number;
  chains_expected_count: number;
  paper_proof_chain_verified: boolean;
  blocker_count: number;
  summary_only?: boolean;
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
    status_path_present?: boolean;
    completed_trading_days: number;
    required_trading_days: number;
    chain_verified: boolean;
    passed: boolean;
    failure_reasons: string[];
    failure_reason_count?: number;
  };
  latest_decision: PaperDecision;
  latest_risk: PaperRisk;
  claim_boundary: string;
  claim_boundary_present?: boolean;
  deployment_status: "NOT LICENSED" | "LICENSED";
  broker_accept_status: "NOT LICENSED" | "LICENSED";
  payment_transfer_status: "NOT LICENSED" | "LICENSED";
  completed_steps: number;
  total_steps: number;
  overall_status: string;
  summary_only?: boolean;
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
  claim_boundary_present?: boolean;
  override_count?: number; persisted?: boolean; override_state_path?: string | null;
  override_state_path_present?: boolean;
  allowed_modes?: OwnerControlMode[];
  allowed_mode_count?: number;
  summary_only?: boolean;
}

export interface MTHistorySummary {
  source: string; total_trades: number; win_rate: number; profit_factor: number;
  total_profit: number; total_loss: number; net_pnl: number;
  symbol_performance: Record<string, { trades: number; win_rate: number; profit_factor: number; net_pnl: number }>;
  multi_trade_bursts: number; import_date: string;
}


export interface AccountLedgerEvent {
  ledger_id: string; event_type: string; timestamp: string; amount_usd: number;
  balance_delta_usd: number; equity_delta_usd: number; margin_delta_usd: number;
  symbol: string | null; side: string | null; lot_size: number | null; price: number | null;
  sl: number | null; tp: number | null; broker_ticket: string | null; simulator_ticket: string | null;
  strategy_id: string | null; ai_action: string | null; evidence_packet_id: string | null;
  evidence_refs: string[]; note: string; external_money_movement: boolean;
}

export interface AccountTerminalTradeRow {
  row_id: string; tab: string; symbol: string; side: string; lot_size: number;
  open_price: number; close_or_current_price: number | null; stop_loss: number | null; take_profit: number | null;
  timestamp: string; broker_ticket: string | null; simulator_ticket: string; strategy_id: string;
  ai_action: string; evidence_packet_id: string; net_pnl_usd: number; swap_usd: number;
  commission_usd: number; fees_usd: number; status: string;
}

export interface AccountLedgerSummary {
  mode: string; initial_investment_usd: number; owner_selected_initial_investment_usd: number;
  risk_review_account_equity_usd: number; requires_new_risk_review_for_selected_investment: boolean;
  deposit_usd: number; withdrawals_usd: number; payouts_usd: number; realized_pnl_usd: number;
  floating_pnl_usd: number; swap_usd: number; commission_usd: number; broker_fees_usd: number;
  balance_usd: number; equity_usd: number; margin_used_usd: number; free_margin_usd: number;
  planned_risk_usd: number; planned_risk_pct_of_selected_equity: number; drawdown_usd: number;
  drawdown_pct: number; event_count: number; open_position_count: number; order_count: number; deal_count: number;
  currency: string;
}

export interface AccountLedgerState {
  report_kind: string; plan_id: string; lead_id: string; strategy_setting: string; as_of_date: string; mode: string;
  summary: AccountLedgerSummary; cashflow_events: AccountLedgerEvent[];
  positions: AccountTerminalTradeRow[]; orders: AccountTerminalTradeRow[]; deals: AccountTerminalTradeRow[];
  supported_history_tabs: string[]; supported_time_filters: string[]; evidence_refs: string[];
  claim_boundary: string; trading_edge_status: string; live_trading_status: string; broker_accept_status: string;
  auto_deposit_status: string; debit_card_bank_movement_status: string; payout_automation_status: string;
  deployment_status: string; live_money_authorized: boolean; payment_movement_authorized: boolean;
  sync_to_broker_snapshot?: boolean; broker_snapshot_initial_investment_usd?: number | null;
  cache_status?: string;
  notes: string[];
}


export interface MarketMovementQuote {
  symbol: string; timestamp: string; bid: number; ask: number; mid: number;
  spread_units: number; price_unit_name: string; price_unit_size: number;
  session: string; is_market_open: boolean; source: string; stale: boolean;
  synthetic_candle: { time: string; open: number; high: number; low: number; close: number };
  atr_units: number;
}

export interface PositionMovement {
  row_id: string; symbol: string; side: string; lot_size: number;
  open_price: number; current_price: number; stop_loss: number | null; take_profit: number | null;
  floating_pnl_usd: number; floating_pnl_units: number;
  distance_to_sl_units: number | null; distance_to_tp_units: number | null;
  distance_to_sl_pct: number | null; distance_to_tp_pct: number | null;
  margin_estimate_usd: number; broker_ticket: string | null; simulator_ticket: string;
  evidence_packet_id: string; ai_action: string; status: string;
}

export interface AccountMovementSnapshot {
  timestamp: string; balance_usd: number; equity_usd: number; realized_pnl_usd: number;
  floating_pnl_usd: number; swap_usd: number; commission_usd: number; broker_fees_usd: number;
  margin_used_usd: number; free_margin_usd: number; drawdown_usd: number; drawdown_pct: number;
  deposit_usd: number; withdrawals_usd: number; payouts_usd: number; open_position_count: number; source: string;
}

export interface MovementStreamState {
  report_kind: string; stream_id: string; mode: string; timestamp: string; symbols: string[];
  account: AccountMovementSnapshot; quotes: MarketMovementQuote[]; positions: PositionMovement[];
  account_streams: string[]; market_streams: string[]; evidence_refs: string[]; claim_boundary: string;
  trading_edge_status: string; live_trading_status: string; broker_accept_status: string;
  auto_deposit_status: string; debit_card_bank_movement_status: string; payout_automation_status: string;
  live_money_authorized: boolean; payment_movement_authorized: boolean; notes: string[];
}


export interface ReconciliationCheck {
  check_id: string; description: string; status: string;
  internal_value: unknown; broker_value: unknown; detail: string;
}

export interface AccountReconciliationReport {
  report_kind: string; mode: string; as_of_date: string; plan_id: string; lead_id: string;
  overall_status: string; checks_total: number; checks_ok: number; checks_mismatch: number; checks_unverifiable: number;
  broker_mode: string; broker_receipt_id: string | null; broker_receipt_validation_status: string | null;
  broker_chain_verified: boolean; internal_symbols: string[]; broker_symbols: string[];
  checks: ReconciliationCheck[]; blockers: string[]; claim_boundary: string;
  trading_edge_status: string; live_trading_status: string; broker_accept_status: string;
  deployment_status: string; live_money_authorized: boolean; payment_movement_authorized: boolean;
  sync_to_broker_snapshot?: boolean; broker_snapshot_initial_investment_usd?: number | null;
  cache_status?: string;
  notes: string[];
}

export interface BrokerSyncedRiskPreview {
  report_kind: string; mode: string; review_id: string; plan_id: string; lead_id: string;
  strategy_setting: string; date: string; timeframe: string; source_decision_id: string | null;
  route_action: string; account_equity: number; max_risk_per_trade_pct: number;
  daily_risk_budget_pct: number; daily_risk_budget_usd: number; max_position_lots: number;
  max_paper_attempts: number; existing_attempts: number; attempts_remaining_before_review: number;
  proposed_attempts: number; allowed_attempts: number; suppressed_attempts: number;
  total_planned_lots: number; total_planned_risk_usd: number; total_planned_risk_pct: number;
  risk_status: string; sizing: SizingEntry[]; blockers: string[]; notes: string[];
  claim_boundary: string; deployment_status: string; broker_accept_status: string;
  payment_transfer_status: string; sync_to_broker_snapshot: boolean;
  broker_snapshot_initial_investment_usd: number; default_risk_review_account_equity_usd: number;
  default_total_planned_risk_usd: number; default_total_planned_lots: number;
  delta_vs_default: { account_equity_usd: number; total_planned_risk_usd: number; total_planned_lots: number };
  would_append_evidence: boolean; live_money_authorized: boolean; payment_movement_authorized: boolean;
  evidence_appended?: boolean; already_applied?: boolean; append_receipt?: unknown | null;
  paper_risk_status_path?: string; paper_risk_summary?: PaperRisk;
  next_action: string;
}

export interface LiveReadinessCheck {
  gate_id: string; label: string; status: string; plain_english: string;
  evidence: string[]; next_action: string; blocks_live: boolean;
  owner_action_required: boolean; capability: string | null;
}

export interface LiveReadinessReport {
  report_kind: string; mode: string; overall_status: string; plain_english_summary: string;
  checks_total: number; checks_passed: number; checks_open: number; checks_mismatch: number;
  checks_unverifiable: number; checks_currently_not_licensed: number;
  live_money_authorized: boolean; payment_movement_authorized: boolean;
  next_actions: string[]; checks: LiveReadinessCheck[]; claim_boundary: string;
  trading_edge_status: string; live_trading_status: string; broker_accept_status: string;
  auto_deposit_status: string; debit_card_bank_movement_status: string;
  payout_automation_status: string; notes: string[];
  sync_to_broker_snapshot?: boolean; broker_snapshot_initial_investment_usd?: number | null;
  cache_status?: string; readiness_status?: string;
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

export interface ExternalBenchmark {
  benchmark_id: string;
  name: string;
  url: string;
  public_account_descriptor: string;
  visible_symbol_focus: string;
  gain_pct: number;
  abs_gain_pct?: number;
  daily_pct?: number;
  monthly_pct?: number;
  drawdown_pct: number;
  balance_usd?: number;
  equity_usd?: number;
  deposits_usd?: number;
  withdrawals_usd?: number;
  profit_usd?: number;
  trades: number;
  pips?: number;
  average_win_pips?: number;
  average_win_usd?: number;
  average_loss_pips?: number;
  average_loss_pips_displayed?: number;
  average_loss_usd?: number;
  lots?: number | null;
  commissions_usd?: number;
  longs_won?: string;
  shorts_won?: string;
  average_trade_length?: string;
  profit_factor?: number;
  expectancy?: string;
}

export interface ExternalBenchmarkReport {
  report_kind: string;
  created_at: string;
  source_family: string;
  claim_boundary: string;
  source_limitations: string[];
  official_myfxbook_api_notes?: {
    url: string;
    access_scope: string;
    useful_methods: string[];
    history_limit_note: string;
  };
  benchmarks: ExternalBenchmark[];
  implementation_targets: string[];
  recommended_next_files: string[];
  report_path?: string;
  summary: {
    benchmark_count: number;
    real_account_count: number;
    mt4_account_count: number;
    symbols: string[];
    total_public_trade_count: number;
    best_gain_benchmark_id: string;
    best_gain_pct: number;
    lowest_drawdown_benchmark_id: string;
    lowest_drawdown_pct: number;
    next_build_target: string;
  };
}

export interface ForexFuryMetricSnapshot {
  profile_id: string;
  platform: string;
  family: string;
  variant: string;
  symbol: string;
  timeframe: string;
  trade_window: string | null;
  profit_factor: number | null;
  total_net_profit: number | null;
  equity_drawdown_relative_pct: number | null;
  total_trades: number | null;
  history_quality: string | null;
  metric?: string;
  value?: number;
}

export interface ForexFuryTesterReport {
  report_path: string;
  relative_report_path: string;
  report_sha256: string;
  expert: string | null;
  symbol: string | null;
  period: string | null;
  company: string | null;
  currency: string | null;
  leverage: string | null;
  history_quality: string | null;
  metrics: {
    total_net_profit: number | null;
    gross_profit: number | null;
    gross_loss: number | null;
    profit_factor: number | null;
    expected_payoff: number | null;
    recovery_factor: number | null;
    sharpe_ratio: number | null;
    total_trades: number | null;
    total_deals: number | null;
    profit_trades_pct: number | null;
    loss_trades_pct: number | null;
    balance_drawdown_relative_pct: number | null;
    equity_drawdown_relative_pct: number | null;
    initial_deposit: number | null;
    bars: number | null;
    ticks: number | null;
  };
}

export interface ForexFurySetRecord {
  profile_id: string;
  source_path: string;
  relative_source_path: string;
  source_sha256: string;
  platform: "MT4" | "MT5" | "UNKNOWN";
  family: string;
  variant: string;
  symbol: string | null;
  timeframe: string | null;
  trade_window: string | null;
  trade_window_hours: number | null;
  active_days: string[];
  core_parameters: Record<string, unknown>;
  derived: {
    lot_size: number | null;
    stop_loss: number | null;
    take_profit: number | null;
    tp_sl_ratio: number | null;
    max_orders: number | null;
    max_trades_per_day: number | null;
    max_spread: number | null;
    uses_grid: boolean;
    grid_level_distance_min: number | null;
    grid_level_distance_max: number | null;
    grid_volume_multiplier_max: number | null;
    uses_close_by_money: boolean;
    close_money_trigger: number | null;
    uses_hidden_sltp: boolean;
    uses_dynamic_retrace: boolean;
    uses_cost_averaging: boolean;
    uses_trailing_stop: boolean;
    uses_stochastic_filter: boolean;
    uses_heiken_ashi_filter: boolean;
    one_set_trade_per_day: boolean;
    only_range_trading: boolean;
  };
  optimization: { ranges: Record<string, Record<string, unknown>>; optimized_fields: string[] };
  tester_report: ForexFuryTesterReport | null;
}

export interface ForexFurySetImportReport {
  report_kind: string;
  created_at: string;
  source_family: string;
  source_dir: string;
  claim_boundary: string;
  source_limitations: string[];
  file_counts: Record<string, number>;
  compiled_binaries: Array<{
    path: string;
    relative_path: string;
    extension: string;
    size_bytes: number;
    sha256: string;
    handling: string;
  }>;
  set_records: ForexFurySetRecord[];
  summary: {
    set_count: number;
    html_report_file_count: number;
    tester_report_count: number;
    compiled_binary_count: number;
    platform_counts: Record<string, number>;
    family_counts: Record<string, number>;
    symbol_counts: Record<string, number>;
    timeframe_counts: Record<string, number>;
    trade_windows: string[];
    max_orders_values: number[];
    grid_enabled_count: number;
    close_by_money_count: number;
    hidden_sltp_count: number;
    trailing_stop_count: number;
    dynamic_retrace_count: number;
    cost_averaging_count: number;
    stochastic_filter_count: number;
    one_set_trade_per_day_count: number;
    best_profit_factor: ForexFuryMetricSnapshot | null;
    lowest_equity_drawdown_pct: ForexFuryMetricSnapshot | null;
    highest_net_profit: ForexFuryMetricSnapshot | null;
    top_report_profiles: ForexFuryMetricSnapshot[];
  };
  cas_improvement_targets: string[];
  report_path?: string;
}

export interface ForexFuryReplayCandidate {
  rank: number;
  candidate_id: string;
  source_profile_id: string;
  source_set_path: string;
  source_set_sha256: string;
  source_report_path: string | null;
  platform: string;
  family: string;
  variant: string;
  raw_symbol: string | null;
  cas_symbol: string;
  symbol_supported: boolean;
  symbol_status: string;
  timeframe: string;
  trade_window: string | null;
  trade_window_hours: number | null;
  active_days: string[];
  execution_profile: {
    max_orders: number | null;
    max_trades_per_day: number | null;
    uses_grid: boolean;
    uses_close_by_money: boolean;
    close_money_trigger: number | null;
    uses_trailing_stop: boolean;
    uses_hidden_sltp: boolean;
    uses_dynamic_retrace: boolean;
    uses_cost_averaging: boolean;
    one_set_trade_per_day: boolean;
    only_range_trading: boolean;
  };
  risk_shape: {
    lot_size: number | null;
    stop_loss: number | null;
    take_profit: number | null;
    tp_sl_ratio: number | null;
    grid_level_distance_min: number | null;
    grid_level_distance_max: number | null;
    grid_volume_multiplier_max: number | null;
  };
  evidence: {
    profit_factor: number | null;
    equity_drawdown_relative_pct: number | null;
    total_net_profit: number | null;
    total_trades: number | null;
    history_quality: string | null;
  };
  score: number;
  readiness: string;
  replay_job: {
    job_id: string;
    job_kind: string;
    source: string;
    status: string;
    symbols: string[];
    timeframes: string[];
    families_to_compare: string[];
    owner_control_inputs: {
      max_open_positions: number | null;
      trade_window: string | null;
      allow_grid_policy_test: boolean;
      allow_money_close_policy_test: boolean;
    };
  };
  recommended_commands: string[];
  notes: string[];
}

export interface ForexFuryReplayCandidateReport {
  report_kind: string;
  created_at: string;
  source_report_path: string | null;
  source_report_sha256: string | null;
  source_set_count: number;
  claim_boundary: string;
  selection_thresholds: {
    min_profit_factor: number;
    max_equity_drawdown_pct: number;
    max_candidates: number;
  };
  candidate_count: number;
  candidates: ForexFuryReplayCandidate[];
  summary: {
    source_set_count: number;
    candidate_count: number;
    supported_candidate_count: number;
    waiting_for_instrument_spec_count: number;
    symbols: string[];
    timeframes: string[];
    families: Record<string, number>;
    platforms: Record<string, number>;
    ready_for_replay_ids: string[];
    top_candidate_id: string | null;
    top_candidate_score: number | null;
  };
  next_actions: string[];
  report_path?: string;
}

export interface ForexFuryReplayResultsReport {
  report_kind: string;
  created_at: string;
  claim_boundary: string;
  source_reports: Record<string, {
    run_id: string | null;
    report_kind: string | null;
    path: string | null;
    sha256: string | null;
  }>;
  candidate_summary: ForexFuryReplayCandidateReport["summary"];
  condition_summary: {
    run_id: string;
    source: string;
    symbols: string[];
    timeframes: string[];
    cell_count: number;
    non_gap_cell_count: number;
    route_count: number;
    no_trade_route_count: number;
    overall_gap_fraction: number;
    top_condition_cells: Array<{
      source: string;
      symbol: string;
      timeframe: string;
      event_context: string;
      regime: string;
      vol_mult: number;
      setting: string;
      family: string;
      mean_return_pct: number;
      mean_max_dd_pct: number;
      mean_trades: number;
      win_rate: number;
      profit_factor: number;
      region: string;
      beta: number;
      score: number;
    }>;
  };
  walk_forward_summary: {
    run_id: string;
    windows: number;
    routed_windows: number;
    no_trade_windows: number;
    active_routed_windows: number;
    positive_routed_windows: number;
    positive_routed_window_rate: number;
    positive_active_routed_windows: number;
    positive_active_routed_window_rate: number;
    routed_total_return_pct_sum: number;
    routed_mean_return_pct: number;
    active_routed_mean_return_pct: number;
    routed_max_drawdown_pct: number;
    routed_total_trades: number;
    research_grade: string;
    claim_boundary: string;
  };
  replay_verdict: string;
  adaptive_compounding_next_step: string;
  next_actions: string[];
  report_path?: string;
}

export interface AgentWorkflowAutowakeEvent {
  event_id: string;
  trigger: string;
  action: string;
  purpose: string;
}

export interface AgentWorkflowAgent {
  agent_id: string;
  role: string;
  cadence: string;
  timeframes: string[];
  primary_inputs: string[];
  decision_outputs: string[];
  memory_writes: string[];
  must_reject_conditions?: string[];
  plain_english: string;
}

export interface AgentWorkflowPlan {
  report_kind: string;
  created_at: string;
  workflow_status: string;
  current_execution_mode: string;
  target_execution_mode: string;
  claim_boundary: string;
  summary: {
    agent_count: number;
    autowake_event_count: number;
    micro_scalp_cadence_minutes: string;
    hourly_intraday_cadence_minutes: number;
    thirty_day_window_days: number;
    primary_replay_lead: string | null;
    primary_replay_verdict: string | null;
    adaptive_next_step: string | null;
  };
  autowake_schedule: {
    market_week: string;
    timezone_policy: string;
    events: AgentWorkflowAutowakeEvent[];
  };
  agent_roster: AgentWorkflowAgent[];
  coordination_model: {
    proposal_flow: string[];
    conflict_rules: string[];
    llm_context_bootstrap: string[];
  };
  knowledge_pack: Array<{
    path: string;
    purpose: string;
    required_by: string[];
  }>;
  thirty_day_window: {
    objective: string;
    primary_short_timeframe_lead: string | null;
    daily_outputs: string[];
    promotion_criteria: string[];
  };
  implementation_queue: Array<{
    priority: number;
    item_id: string;
    plain_english: string;
    target_file: string;
  }>;
  source_reports: Record<string, {
    report_kind: string | null;
    path: string | null;
    sha256: string | null;
    status: string;
  }>;
  live_execution_boundary: {
    live_trading_status: string;
    broker_accept_status: string;
    auto_deposit_status: string;
    debit_card_bank_movement_status: string;
    payout_automation_status: string;
    owner_runtime_authorization_required: boolean;
    plain_english: string;
  };
  report_path?: string;
}

export interface AgentWorkflowCycle {
  report_kind: string;
  cycle_id: string;
  created_at: string;
  trigger_source: string;
  execution_mode: string;
  summary: {
    agent_heartbeat_count: number;
    route_intent_count: number;
    approved_intent_count: number;
    rejected_intent_count: number;
    terminal_command_count: number;
    memory_snapshot_count: number;
    symbols: string[];
    timeframes: string[];
    terminal_lane?: string;
    mt5_loop_status?: string | null;
    mt5_execution_report_count?: number;
    mt5_executed_order_count?: number;
    mt5_broker_tickets?: Array<string | number>;
    mt5_deal_history_status?: string | null;
    mt5_deal_history_memory_update_count?: number;
    mt5_closed_position_count?: number;
    mt5_net_profit_loss_account?: number;
    mt5_post_memory_terminal_history_joined_count?: number;
    mt5_post_memory_pnl_ready_count?: number;
  };
  agent_heartbeats: Array<{
    agent_id: string;
    status: string;
    timestamp: string;
    cadence: string;
    detail: string;
  }>;
  route_intents: Array<{
    intent_id: string;
    agent_id: string;
    action: string;
    symbol: string;
    timeframe: string;
    strategy_setting: string;
    direction: string | null;
    confidence: number;
    evidence_score: number;
    lot_size: number;
    entry_price: number | null;
    stop_loss: number | null;
    take_profit: number | null;
    reason: string;
    evidence_refs: string[];
    order_request: Record<string, unknown> | null;
    status: string;
  }>;
  overseer_decisions: Array<{
    decision_id: string;
    intent_id: string;
    agent_id: string;
    decision: string;
    approved: boolean;
    reasons: string[];
    command_ready: boolean;
    timestamp: string;
  }>;
  terminal_commands: Array<Record<string, unknown>>;
  mt5_execution_loop?: {
    lane: string;
    loop_status: string;
    execution_reports: Array<Record<string, unknown>>;
    deal_history_ingest: Record<string, unknown> | null;
    pre_deal_memory: Record<string, unknown> | null;
    post_deal_memory: Record<string, unknown> | null;
    summary: Record<string, unknown>;
  } | null;
  memory_snapshots: Array<Record<string, unknown>>;
  live_execution_boundary: {
    live_trading_status: string;
    broker_accept_status: string;
    auto_deposit_status: string;
    debit_card_bank_movement_status: string;
    payout_automation_status: string;
  };
  claim_boundary: string;
  output_dir: string;
  report_path?: string;
}

export interface AgentInformationFlow {
  report_kind: string;
  created_at: string;
  flow_status: string;
  claim_boundary: string;
  design_principle: string;
  specialist_agent_reviews: Array<{
    agent: string;
    focus: string;
    verdict: string;
    plain_english: string;
  }>;
  agent_roles: Array<{
    agent_id: string;
    consumes: string[];
    produces: string[];
    cannot_produce: string[];
  }>;
  information_planes: Array<{
    plane: string;
    purpose: string;
    primary_packet: string;
    path: string;
  }>;
  event_envelope: {
    schema: string;
    path: string;
    required_fields: string[];
    example_event_types: string[];
    idempotency_rule: string;
    plain_english: string;
  };
  canonical_packets: Array<{
    packet_name: string;
    purpose: string;
    required_fields: string[];
    storage_target: string;
  }>;
  flow_stages: Array<{
    stage: number;
    name: string;
    producer: string;
    consumer: string;
    packet: string;
  }>;
  state_machine: Array<{ from: string; to: string; by: string }>;
  receipt_and_reconciliation_lifecycle: Array<{ state: string; plain_english: string }>;
  learning_memory_contracts: Array<{
    schema: string;
    purpose: string;
    required_fields: string[];
  }>;
  main_bottlenecks: Array<{
    bottleneck_id: string;
    plain_english: string;
    fix_target: string;
  }>;
  storage_and_api_targets: {
    append_only_event_log: string;
    latest_cycle_projection: string;
    cycle_reports: string;
    mt4_mailbox: string;
    latest_api: string;
    flow_api: string;
    next_api_projections: string[];
    dashboard_key: string;
    ui_panel: string;
  };
  implementation_queue: Array<{
    priority: number;
    target_file: string;
    plain_english: string;
  }>;
  summary: {
    agent_count: number;
    information_plane_count: number;
    specialist_agent_count: number;
    canonical_packet_count: number;
    flow_stage_count: number;
    lifecycle_state_count: number;
    must_have_next_file: string;
    best_flow_form: string;
  };
  report_path?: string;
}

export interface AgentMessageBusSummary {
  event_log_path: string;
  event_count: number;
  event_type_counts: Record<string, number>;
  status_counts: Record<string, number>;
  cycle_count: number;
  latest_event_id: string | null;
  latest_cycle_id: string | null;
  pending_receipt_count: number;
  raw_receipt_pending_event_count?: number;
  verified_receipt_count?: number;
  reconciled_receipt_count?: number;
  next_cycle_allowed_count?: number;
  receipt_mismatch_count?: number;
  open_receipt_command_ids?: string[];
  claim_boundary: string;
}

export interface AgentMemoryRecord {
  schema: string;
  memory_id: string;
  cycle_id: string;
  intent_id: string;
  decision_id?: string | null;
  command_id?: string | null;
  receipt_id?: string | null;
  agent_id: string;
  symbol: string;
  timeframe: string;
  strategy_setting?: string | null;
  action: string;
  decision: string;
  decision_status: string;
  outcome_label: string;
  learning_status: string;
  terminal_history_id?: string | null;
  terminal_history_status?: string | null;
  broker_ticket?: string | number | null;
  profit_loss_account?: number | null;
  profit_loss_pips?: number | null;
  profit_loss_r?: number | null;
  mae?: number | null;
  mfe?: number | null;
  close_reason?: string | null;
  closed_at?: string | null;
  exit_price?: number | null;
  condition_snapshot_open: Record<string, unknown>;
  condition_snapshot_close: Record<string, unknown>;
  source_event_ids: string[];
  claim_boundary: string;
}

export interface AgentMemoryReport {
  report_kind: string;
  created_at: string;
  memory_status: string;
  schema: string;
  event_log_path: string;
  output_dir: string;
  summary: {
    memory_record_count: number;
    route_intent_count: number;
    approved_count: number;
    rejected_count: number;
    command_joined_count: number;
    receipt_joined_count: number;
    verified_receipt_count: number;
    receipt_mismatch_count: number;
    pending_receipt_count: number;
    terminal_history_joined_count?: number;
    closed_trade_count?: number;
    closed_profit_count?: number;
    closed_loss_count?: number;
    closed_flat_count?: number;
    net_profit_loss_account?: number;
    pnl_ready_memory_count?: number;
    mae_ready_count?: number;
    mfe_ready_count?: number;
    outcome_label_counts: Record<string, number>;
    learning_status_counts: Record<string, number>;
    source_event_count: number;
    source_cycle_count: number;
    latest_cycle_id: string | null;
    event_log_pending_receipt_count: number;
  };
  memory_records: AgentMemoryRecord[];
  claim_boundary: string;
  next_action: string;
  artifact_paths?: Record<string, string>;
  report_path?: string;
}

export interface TerminalHistoryRecord {
  schema: string;
  history_id: string;
  source_path: string;
  source_sha256?: string | null;
  ticket?: string | null;
  broker_ticket?: string | null;
  command_id?: string | null;
  receipt_id?: string | null;
  symbol: string;
  direction: string;
  lots: number;
  opened_at?: string | null;
  closed_at?: string | null;
  open_price?: number | null;
  close_price?: number | null;
  stop_loss?: number | null;
  take_profit?: number | null;
  profit_loss_account: number;
  profit_loss_pips?: number | null;
  profit_loss_r?: number | null;
  mae?: number | null;
  mfe?: number | null;
  close_reason?: string | null;
  commission: number;
  swap: number;
  account_currency?: string | null;
  broker_mode?: string | null;
  claim_boundary: string;
}

export interface TerminalHistoryMemoryUpdate {
  memory_id: string;
  history_id: string;
  command_id?: string | null;
  receipt_id?: string | null;
  broker_ticket?: string | number | null;
  symbol: string;
  timeframe?: string | null;
  match_method?: string | null;
  terminal_history_status: string;
  profit_loss_account: number;
  profit_loss_pips?: number | null;
  profit_loss_r?: number | null;
  mae?: number | null;
  mfe?: number | null;
  close_reason?: string | null;
  commission?: number | null;
  swap?: number | null;
  closed_at?: string | null;
  exit_price?: number | null;
  outcome_label: string;
  promotion_signal: string;
  demotion_flags: string[];
  source_path?: string | null;
  source_sha256?: string | null;
}

export interface TerminalHistoryIngestReport {
  report_kind: string;
  created_at: string;
  ingest_status: string;
  schema: string;
  source_paths: string[];
  memory_report_path?: string | null;
  output_dir: string;
  summary: {
    history_record_count: number;
    memory_update_count: number;
    unmatched_history_count: number;
    closed_trade_count: number;
    closed_profit_count: number;
    closed_loss_count: number;
    closed_flat_count: number;
    net_profit_loss_account: number;
    total_commission: number;
    total_swap: number;
    pnl_ready_memory_count: number;
    mae_ready_count: number;
    mfe_ready_count: number;
    source_memory_count: number;
    source_pending_receipt_count: number;
  };
  history_records: TerminalHistoryRecord[];
  memory_updates: TerminalHistoryMemoryUpdate[];
  unmatched_history_records: TerminalHistoryRecord[];
  claim_boundary: string;
  next_action: string;
  artifact_paths?: Record<string, string>;
  report_path?: string;
}

export interface MT5DealHistoryIngestReport {
  report_kind: string;
  created_at: string;
  ingest_status: string;
  schema: string;
  query: {
    start: string;
    end: string;
    days_back: number;
    future_minutes?: number;
    symbol?: string | null;
    ticket?: string | null;
  };
  mt5_path?: string | null;
  terminal_snapshot: Record<string, unknown>;
  history_export_path?: string | null;
  raw_deal_count: number;
  raw_deals_sha256: string;
  raw_deals?: Array<Record<string, unknown>>;
  history_records: Array<Record<string, unknown>>;
  terminal_history_ingest: Partial<TerminalHistoryIngestReport> | Record<string, unknown>;
  summary: {
    mt5_package_available: boolean;
    initialize_ok: boolean;
    terminal_connected: boolean;
    terminal_name?: string | null;
    terminal_trade_allowed?: boolean | null;
    server?: string | null;
    demo_account_confirmed: boolean;
    account_snapshot_present: boolean;
    account_balance?: number | null;
    account_equity?: number | null;
    account_currency?: string | null;
    ticket_filter?: string | null;
    raw_deal_count: number;
    closed_position_count: number;
    history_record_count: number;
    memory_update_count: number;
    unmatched_history_count: number;
    closed_trade_count: number;
    closed_profit_count: number;
    closed_loss_count: number;
    closed_flat_count: number;
    net_profit_loss_account: number;
    total_commission: number;
    total_swap: number;
    history_export_path?: string | null;
    terminal_history_ingest_status?: string | null;
    terminal_history_report_path?: string | null;
  };
  claim_boundary: string;
  next_action: string;
  operator_commands: Record<string, string>;
  output_dir: string;
  artifact_paths?: Record<string, string>;
  report_path?: string;
}

export interface AgentResearchTask {
  schema: string;
  task_id: string;
  task_type: string;
  priority: number;
  status: string;
  source_memory_ids: string[];
  source_outcome_labels: string[];
  research_question: string;
  plain_english_goal: string;
  symbols: string[];
  timeframes: string[];
  families: string[];
  agents: string[];
  actions: string[];
  success_metric: string;
  required_inputs: string[];
  produces: string[];
  blocked_by: string[];
  source_counts: Record<string, number>;
  created_at: string;
  claim_boundary: string;
}

export interface AgentResearchQueueReport {
  report_kind: string;
  created_at: string;
  queue_status: string;
  schema: string;
  memory_report_path?: string | null;
  output_dir: string;
  summary: {
    task_count: number;
    queued_task_count: number;
    high_priority_task_count: number;
    task_type_counts: Record<string, number>;
    priority_counts: Record<string, number>;
    status_counts: Record<string, number>;
    source_memory_count: number;
    source_pending_receipt_count: number;
    source_ready_for_research_count: number;
    source_receipt_joined_count: number;
    source_latest_cycle_id: string | null;
    terminal_receipt_task_count: number;
    condition_lab_task_count: number;
    walk_forward_task_count: number;
    strategy_dev_task_count: number;
    next_task_id: string | null;
  };
  research_tasks: AgentResearchTask[];
  claim_boundary: string;
  next_action: string;
  artifact_paths?: Record<string, string>;
  report_path?: string;
}

export interface StrategyDevWorkItem {
  schema: string;
  item_id: string;
  item_type: string;
  priority: number;
  status: string;
  source_task_ids: string[];
  source_memory_ids: string[];
  source_outcome_labels: string[];
  symbols: string[];
  timeframes: string[];
  families: string[];
  agents: string[];
  actions: string[];
  hypothesis: string;
  plain_english_goal: string;
  proposed_change: string;
  replay_request: Record<string, unknown>;
  promotion_review: Record<string, unknown>;
  required_inputs: string[];
  blocked_by: string[];
  produces: string[];
  acceptance_checks: string[];
  source_counts: Record<string, number>;
  created_at: string;
  claim_boundary: string;
}

export interface StrategyDevQueueReport {
  report_kind: string;
  created_at: string;
  queue_status: string;
  schema: string;
  research_queue_report_path?: string | null;
  memory_report_path?: string | null;
  output_dir: string;
  summary: {
    item_count: number;
    queued_item_count: number;
    blocked_item_count: number;
    ready_for_replay_count: number;
    patch_candidate_count: number;
    promotion_review_count: number;
    demotion_review_count: number;
    terminal_blocked_count: number;
    item_type_counts: Record<string, number>;
    status_counts: Record<string, number>;
    priority_counts: Record<string, number>;
    source_task_count: number;
    source_memory_count: number;
    source_pending_receipt_count: number;
    source_terminal_history_joined_count: number;
    closed_profit_memory_count: number;
    closed_loss_memory_count: number;
    next_item_id: string | null;
  };
  work_items: StrategyDevWorkItem[];
  claim_boundary: string;
  next_action: string;
  artifact_paths?: Record<string, string>;
  report_path?: string;
}

export interface StrategyPatchDecision {
  schema: string;
  decision_id: string;
  decision_type: string;
  priority: number;
  status: string;
  source_item_id: string;
  source_item_type: string;
  source_task_ids: string[];
  source_memory_ids: string[];
  symbols: string[];
  timeframes: string[];
  plain_english_decision: string;
  proposed_action: string;
  patch_target: string;
  replay_job: Record<string, unknown>;
  promotion_review: Record<string, unknown>;
  required_inputs: string[];
  blocked_by: string[];
  evidence_refs: Record<string, unknown>;
  generated_artifacts: string[];
  acceptance_checks: string[];
  owner_review_required: boolean;
  created_at: string;
  claim_boundary: string;
}

export interface StrategyPatchRunnerReport {
  report_kind: string;
  created_at: string;
  runner_status: string;
  schema: string;
  strategy_dev_queue_report_path?: string | null;
  output_dir: string;
  summary: {
    decision_count: number;
    ready_decision_count: number;
    blocked_decision_count: number;
    patch_candidate_count: number;
    replay_job_count: number;
    promotion_review_count: number;
    demotion_review_count: number;
    terminal_input_required_count: number;
    owner_review_required_count: number;
    decision_type_counts: Record<string, number>;
    status_counts: Record<string, number>;
    priority_counts: Record<string, number>;
    patch_target_counts: Record<string, number>;
    source_item_count: number;
    source_blocked_item_count: number;
    source_patch_candidate_count: number;
    next_decision_id: string | null;
  };
  decisions: StrategyPatchDecision[];
  claim_boundary: string;
  next_action: string;
  artifact_paths?: Record<string, string>;
  report_path?: string;
}

export interface DailyLearningRollupReport {
  report_kind: string;
  created_at: string;
  rollup_status: string;
  schema: string;
  trading_date: string;
  day_index: number;
  window_days: number;
  source_reports: Record<string, unknown>;
  output_dir: string;
  summary: {
    route_count: number;
    approved_count: number;
    rejected_count: number;
    executed_count: number;
    receipt_joined_count: number;
    pending_receipt_count: number;
    terminal_history_joined_count: number;
    terminal_history_update_count: number;
    closed_count: number;
    win_count: number;
    loss_count: number;
    flat_count: number;
    gross_profit_account: number;
    gross_loss_account: number;
    net_profit_loss_account: number;
    profit_factor: number | null;
    expectancy_account: number | null;
    max_drawdown_pct: number | null;
    research_task_count: number;
    strategy_item_count: number;
    patch_decision_count: number;
    patch_candidate_count: number;
    replay_job_count: number;
    promotion_candidate_count: number;
    demotion_flag_count: number;
    terminal_input_required_count: number;
    source_report_count: number;
    chain_verified: boolean;
    readiness_label: string;
  };
  by_agent: Array<Record<string, unknown>>;
  by_symbol: Array<Record<string, unknown>>;
  by_strategy: Array<Record<string, unknown>>;
  by_condition_cell: Array<Record<string, unknown>>;
  promotion_candidates: Array<Record<string, unknown>>;
  demotion_flags: Array<Record<string, unknown>>;
  queued_follow_up_work: Array<{
    work_type: string;
    source_id: string | null;
    status: string | null;
    priority: number | null;
    plain_english: string | null;
  }>;
  terminal_blockers: Array<{
    blocker_id: string;
    count: number;
    plain_english: string;
  }>;
  claim_boundary: string;
  next_action: string;
  artifact_paths?: Record<string, string>;
  report_path?: string;
}

export interface SessionAutowakeEvent {
  schema: string;
  event_id: string;
  action: string;
  trigger: string;
  purpose: string;
  due: boolean;
  status: string;
  decision: string;
  requested_agent_cycle: boolean;
  terminal_blocked: boolean;
  active_session: string;
  as_of: string;
  daily_rollup_status?: string | null;
  reasons: string[];
  claim_boundary: string;
}

export interface SessionAutowakeReport {
  report_kind: string;
  created_at: string;
  autowake_status: string;
  schema: string;
  as_of: string;
  execution_mode: string;
  workflow_plan_path?: string | null;
  daily_rollup_path?: string | null;
  output_dir: string;
  session_state: {
    market_open: boolean;
    active_session: string;
    weekday: string;
    utc_hour: number;
    utc_minute: number;
    timezone: string;
    market_week_reference: string;
  };
  summary: {
    event_count: number;
    due_event_count: number;
    executable_event_count: number;
    executed_cycle_count: number;
    market_open: boolean;
    active_session: string;
    terminal_blocker_count: number;
    pending_receipt_count: number;
    closed_count: number;
    daily_rollup_status?: string | null;
    daily_rollup_readiness_label?: string | null;
    next_due_event_id?: string | null;
    executed_cycle_id?: string | null;
  };
  event_evaluations: SessionAutowakeEvent[];
  terminal_blockers: Array<{
    blocker_id: string;
    count: number;
    plain_english: string;
  }>;
  executed_cycle?: Record<string, unknown> | null;
  claim_boundary: string;
  next_action: string;
  artifact_paths?: Record<string, string>;
  report_path?: string;
}

export interface TerminalReceiptWatcherFileChange {
  schema: string;
  change_status: string;
  file_role: string | null;
  path: string | null;
  name?: string | null;
  sha256?: string | null;
  previous_sha256?: string | null;
  size_bytes?: number | null;
  previous_size_bytes?: number | null;
  modified_at?: string | null;
  previous_modified_at?: string | null;
}

export interface TerminalReceiptWatcherReport {
  report_kind: string;
  created_at: string;
  watch_status: string;
  schema: string;
  as_of: string;
  mailbox_dir: string;
  receipt_dir: string;
  history_source_paths: string[];
  event_log_path: string;
  output_dir: string;
  chain_output_root?: string | null;
  summary: {
    terminal_file_count: number;
    receipt_file_count: number;
    history_file_count: number;
    changed_file_count: number;
    chain_requested: boolean;
    chain_step_count: number;
    chain_step_complete_count: number;
    chain_step_failed_count: number;
    latest_completed_step?: string | null;
    first_failed_step?: string | null;
  };
  file_fingerprints: Array<Record<string, unknown>>;
  file_changes: {
    change_counts: Record<string, number>;
    changed_files: TerminalReceiptWatcherFileChange[];
  };
  chain_steps: Array<{
    step: string;
    status: string;
    status_label: string;
    started_at?: string;
    finished_at?: string;
    artifact_paths?: Record<string, string>;
    summary?: Record<string, unknown>;
    message?: string;
  }>;
  chain_reports: Record<string, {
    report_kind?: string;
    status?: string;
    report_path?: string | null;
    summary?: Record<string, unknown>;
  }>;
  claim_boundary: string;
  next_action: string;
  artifact_paths?: Record<string, string>;
  report_path?: string;
}

export interface TerminalBridgeSupervisorReport {
  report_kind: string;
  created_at: string;
  supervisor_status: string;
  schema: string;
  as_of: string;
  mailbox_dir: string;
  command_dir: string;
  receipt_dir: string;
  heartbeat_path: string;
  history_source_paths: string[];
  event_log_path: string;
  output_dir: string;
  thresholds: Record<string, number>;
  summary: {
    heartbeat_status?: string | null;
    heartbeat_present: boolean;
    heartbeat_age_seconds?: number | null;
    mailbox_ready: boolean;
    command_file_count: number;
    receipt_file_count: number;
    pending_command_receipt_count: number;
    event_journal_pending_receipt_count: number;
    history_file_count: number;
    account_snapshot_present: boolean;
    live_trading_flag_visible: boolean;
    alert_count: number;
    high_alert_count: number;
    medium_alert_count: number;
    terminal_bridge_ready: boolean;
  };
  heartbeat: Record<string, unknown>;
  mailbox: Record<string, unknown>;
  commands: Record<string, unknown>;
  receipts: Record<string, unknown>;
  history: Record<string, unknown>;
  event_journal: Record<string, unknown>;
  account_snapshot: Record<string, unknown>;
  alerts: Array<{
    alert_id: string;
    severity: string;
    plain_english: string;
  }>;
  claim_boundary: string;
  next_action: string;
  artifact_paths?: Record<string, string>;
  report_path?: string;
}

export interface MT4TerminalActivationReport {
  report_kind: string;
  created_at: string;
  activation_status: string;
  schema: string;
  ea_source: {
    path: string;
    exists: boolean;
    sha256?: string | null;
    size_bytes?: number | null;
  };
  candidate_terminals: Array<Record<string, unknown>>;
  selected_terminal: {
    terminal_data_dir: string;
    platform: string;
    mql4_dir: string;
    mql4_dir_exists: boolean;
    experts_dir: string;
    experts_dir_exists: boolean;
    files_dir: string;
    files_dir_exists: boolean;
    ea: {
      target_path: string;
      target_exists: boolean;
      target_sha256?: string | null;
      source_sha256?: string | null;
      hash_matches: boolean;
    };
    mailbox: {
      mailbox_dir: string;
      command_dir: string;
      receipt_dir: string;
      archive_dir: string;
      heartbeat_path: string;
      mailbox_exists: boolean;
      command_dir_exists: boolean;
      receipt_dir_exists: boolean;
      archive_dir_exists: boolean;
      mailbox_ready: boolean;
      heartbeat_present: boolean;
      command_file_count: number;
      receipt_file_count: number;
    };
  } | null;
  install_requested: boolean;
  create_mailbox_requested: boolean;
  actions: Array<Record<string, unknown>>;
  settings: {
    MailboxRoot: string;
    UseCommonFiles: boolean;
    LiveTradingAllowed: boolean;
    SymbolSuffix: string;
    TimerSeconds: number;
    MaxCommandsPerTimer: number;
  };
  path_alignment: {
    cas_default_mailbox_dir: string;
    recommended_cas_mailbox_dir?: string | null;
    alignment_status: string;
    recommended_env: Record<string, string | null>;
    plain_english: string;
  };
  operator_commands: Record<string, string>;
  activation_steps: Array<{
    step: number;
    plain_english: string;
  }>;
  summary: {
    candidate_count: number;
    mt4_candidate_count: number;
    mt5_only_candidate_count: number;
    selected_terminal_present: boolean;
    selected_platform?: string | null;
    ea_source_present: boolean;
    ea_installed: boolean;
    ea_hash_matches: boolean;
    mailbox_ready: boolean;
    heartbeat_present: boolean;
    command_file_count: number;
    receipt_file_count: number;
    install_requested: boolean;
    create_mailbox_requested: boolean;
  };
  claim_boundary: string;
  next_action: string;
  output_dir: string;
  artifact_paths?: Record<string, string>;
  report_path?: string;
}

export interface MT4PingRoundtripReport {
  report_kind: string;
  created_at: string;
  roundtrip_status: string;
  schema: string;
  mailbox_dir: string | null;
  activation_status?: string | null;
  activation_report_path?: string | null;
  wait_seconds: number;
  poll_interval_seconds: number;
  write_ping_requested: boolean;
  existing_command_id?: string | null;
  command: {
    command_id?: string | null;
    command_type?: string | null;
    command_path?: string | null;
    raw_request_hash?: string | null;
    broker_mode?: string | null;
    live_money_authorized?: boolean;
  } | null;
  expected_receipt_id?: string | null;
  mailbox: {
    mailbox_dir: string | null;
    mailbox_exists: boolean;
    command_dir_exists: boolean;
    receipt_dir_exists: boolean;
    archive_dir_exists: boolean;
    command_file_count: number;
    receipt_file_count: number;
  };
  heartbeat: Record<string, unknown>;
  receipt: Record<string, unknown>;
  summary: {
    activation_status?: string | null;
    mailbox_ready: boolean;
    command_id?: string | null;
    command_path?: string | null;
    ping_written: boolean;
    command_schema_valid: boolean;
    command_type?: string | null;
    heartbeat_present: boolean;
    heartbeat_valid: boolean;
    receipt_present: boolean;
    receipt_valid: boolean;
    receipt_status?: string | null;
    raw_request_hash_match: boolean;
    live_flag_visible: boolean;
    command_file_count: number;
    receipt_file_count: number;
  };
  claim_boundary: string;
  next_action: string;
  operator_commands: Record<string, string>;
  output_dir: string;
  artifact_paths?: Record<string, string>;
  report_path?: string;
}

export interface MT4TerminalSessionVerifierReport {
  report_kind: string;
  created_at: string;
  session_status: string;
  schema: string;
  terminal_data_dir?: string | null;
  mailbox_dir?: string | null;
  search_roots: string[];
  event_log_path: string;
  history_source_paths: string[];
  output_dir: string;
  child_output_root: string;
  settings: {
    install_ea: boolean;
    create_mailbox: boolean;
    wait_seconds: number;
    poll_interval_seconds: number;
    write_ping: boolean;
    run_refresh_chain: boolean;
    force_refresh_chain: boolean;
  };
  step_results: Array<{
    step: string;
    status: string;
    status_label: string | null;
    message?: string;
    started_at?: string;
    finished_at?: string;
    artifact_paths?: Record<string, string>;
    summary?: Record<string, unknown>;
  }>;
  child_reports: Record<string, {
    report_kind?: string;
    status?: string | null;
    report_path?: string | null;
    summary?: Record<string, unknown>;
  }>;
  summary: {
    activation_status?: string | null;
    roundtrip_status?: string | null;
    supervisor_status?: string | null;
    watch_status?: string | null;
    mailbox_dir?: string | null;
    mt4_candidate_count: number;
    mt5_only_candidate_count: number;
    selected_terminal_present: boolean;
    mailbox_ready: boolean;
    ping_written: boolean;
    heartbeat_present: boolean;
    receipt_present: boolean;
    receipt_status?: string | null;
    live_flag_visible: boolean;
    command_file_count: number;
    receipt_file_count: number;
    chain_requested: boolean;
    chain_step_count: number;
    chain_step_complete_count: number;
    chain_step_failed_count: number;
    refresh_chain_complete: boolean;
    step_count: number;
    failed_step_count: number;
    skipped_step_count: number;
    watcher_terminal_file_count: number;
    watcher_changed_file_count: number;
  };
  claim_boundary: string;
  next_action: string;
  operator_commands: Record<string, string>;
  artifact_paths?: Record<string, string>;
  report_path?: string;
}

export interface MT4HistoryExportVerifierReport {
  report_kind: string;
  created_at: string;
  verifier_status: string;
  schema: string;
  ea_source: {
    path: string;
    present: boolean;
    sha256?: string | null;
    size_bytes: number;
  };
  session_report: {
    present: boolean;
    session_status?: string | null;
    mailbox_dir?: string | null;
    report_path?: string | null;
    summary?: Record<string, unknown>;
  };
  mailbox_dir?: string | null;
  history_export_path?: string | null;
  status_path?: string | null;
  history_export: {
    present: boolean;
    path?: string | null;
    sha256?: string | null;
    size_bytes?: number;
    schema?: string | null;
    schema_valid?: boolean;
    parse_status: string;
    parse_error?: string;
    history_record_count?: number;
    history_records?: Array<Record<string, unknown>>;
    summary?: Record<string, unknown>;
  };
  exporter_status: {
    present: boolean;
    path?: string | null;
    sha256?: string | null;
    schema?: string | null;
    export_status?: string | null;
    exported_order_count?: number | null;
    parse_status: string;
    parse_error?: string;
    payload?: Record<string, unknown>;
  };
  ingest_report?: {
    report_kind?: string;
    ingest_status?: string;
    artifact_paths?: Record<string, string>;
    summary?: Record<string, unknown>;
  } | null;
  ingest_error?: { error_type: string; message: string } | null;
  summary: {
    ea_source_present: boolean;
    mailbox_ready: boolean;
    mailbox_dir?: string | null;
    history_export_present: boolean;
    history_export_parse_status?: string | null;
    history_export_schema_valid: boolean;
    history_record_count: number;
    exporter_status_present: boolean;
    exporter_status?: string | null;
    ingest_status?: string | null;
    ingest_error_type?: string | null;
    memory_update_count: number;
    unmatched_history_count: number;
    closed_profit_count: number;
    closed_loss_count: number;
    net_profit_loss_account: number;
  };
  claim_boundary: string;
  next_action: string;
  operator_commands: Record<string, string>;
  output_dir: string;
  artifact_paths?: Record<string, string>;
  report_path?: string;
}

export interface TerminalPositionReconciliationReport {
  report_kind: string;
  created_at: string;
  reconciliation_status: string;
  schema: string;
  source_reports: Record<string, {
    present: boolean;
    report_kind?: string | null;
    status?: string | null;
    report_path?: string | null;
    created_at?: string | null;
    summary?: Record<string, unknown>;
    error_type?: string;
    message?: string;
  }>;
  summary: {
    bridge_report_present: boolean;
    receipt_ingest_report_present: boolean;
    history_ingest_report_present: boolean;
    memory_report_present: boolean;
    mt4_history_export_verifier_present: boolean;
    bridge_status?: string | null;
    mt4_history_export_verifier_status?: string | null;
    heartbeat_status?: string | null;
    heartbeat_present: boolean;
    account_snapshot_present: boolean;
    account_snapshot_source?: string | null;
    live_trading_flag_visible: boolean;
    pending_receipt_count: number;
    receipt_mismatch_count: number;
    cas_open_position_count: number;
    cas_receipt_pending_open_count: number;
    cas_receipt_ack_open_count: number;
    terminal_open_position_count: number;
    reconciled_open_position_count: number;
    unmatched_open_position_count: number;
    history_record_count: number;
    memory_update_count: number;
    unmatched_history_count: number;
    terminal_history_joined_count: number;
    closed_profit_count: number;
    closed_loss_count: number;
    net_profit_loss_account: number;
  };
  account_snapshot: { present: boolean; source?: string | null; snapshot: Record<string, unknown> };
  terminal_open_positions: Array<Record<string, unknown>>;
  cas_open_positions: Array<Record<string, unknown>>;
  reconciled_open_positions: Array<Record<string, unknown>>;
  unmatched_open_positions: Array<Record<string, unknown>>;
  closed_history: {
    history_record_count: number;
    memory_update_count: number;
    history_records: Array<Record<string, unknown>>;
    memory_updates: Array<Record<string, unknown>>;
  };
  checks: Array<{
    check_id: string;
    description: string;
    status: string;
    value: unknown;
    detail: string;
  }>;
  claim_boundary: string;
  next_action: string;
  operator_commands: Record<string, string>;
  output_dir: string;
  artifact_paths?: Record<string, string>;
  report_path?: string;
}

export interface TerminalReceiptRecoveryPacket {
  report_kind: string;
  generated_at: string;
  status: string;
  terminal_reconciliation_clean_for_live: boolean;
  broker_touched: boolean;
  journal_rewritten: boolean;
  receipt_ingest_attempted: boolean;
  attempt_finalized: boolean;
  pending_receipt_count: number;
  pending_receipt_count_by_lane: Record<string, number>;
  cas_receipt_pending_open_count: number;
  unmatched_open_position_count: number;
  terminal_open_position_count: number;
  heartbeat_status: string;
  account_snapshot_present: boolean;
  mt4_history_export_verifier_status?: string | null;
  pending_positions: Array<Record<string, unknown>>;
  legacy_archive_preview: {
    journal_path: string;
    snapshot_path?: string | null;
    total_rows_before: number;
    pending_receipt_rows_archived: number;
    rows_remaining: number;
    archived_at_iso: string;
    dry_run: boolean;
    error_message?: string | null;
    execute_required_for_archive?: boolean;
    claim_boundary?: string;
  };
  missing_requirements: string[];
  source_reconciliation: Record<string, unknown>;
  operator_commands: Record<string, string>;
  claim_boundary: string;
  next_action: string;
}

export interface TerminalReceiptArchiveAction {
  report_kind: string;
  generated_at: string;
  status: string;
  requested_execute: boolean;
  confirm_owner_archive: boolean;
  dry_run: boolean;
  broker_touched: boolean;
  journal_rewritten: boolean;
  receipt_ingest_attempted: boolean;
  attempt_finalized: boolean;
  money_moved: boolean;
  age_threshold_hours: number;
  notes_recorded: string;
  archive_result: {
    journal_path: string;
    snapshot_path?: string | null;
    total_rows_before: number;
    pending_receipt_rows_archived: number;
    rows_remaining: number;
    archived_at_iso: string;
    dry_run: boolean;
    error_message?: string | null;
  };
  claim_boundary: string;
  next_action: string;
}

export interface TerminalReceiptRecoveryRefreshAction {
  report_kind: string;
  generated_at: string;
  status: string;
  requested_execute: boolean;
  confirm_owner_refresh: boolean;
  dry_run: boolean;
  broker_touched: boolean;
  live_order_attempted: boolean;
  attempt_finalized: boolean;
  money_moved: boolean;
  notes_recorded: string;
  steps: Array<{
    step: string;
    status: string;
    status_label?: string | null;
    detail: string;
  }>;
  reports: Record<string, {
    report_kind?: string | null;
    status?: string | null;
    report_path?: string | null;
    summary?: Record<string, unknown>;
    next_action?: string | null;
  }>;
  claim_boundary: string;
  next_action: string;
}

export interface TerminalOperabilityVerifierReport {
  report_kind: string;
  created_at: string;
  operability_status: string;
  schema: string;
  source_reports: Record<string, {
    present: boolean;
    report_kind?: string | null;
    status?: string | null;
    report_path?: string | null;
    created_at?: string | null;
    summary?: Record<string, unknown>;
    error_type?: string;
    message?: string;
  }>;
  summary: {
    session_report_present: boolean;
    bridge_report_present: boolean;
    receipt_ingest_report_present: boolean;
    history_export_verifier_present: boolean;
    history_ingest_report_present: boolean;
    position_reconciliation_report_present: boolean;
    mt5_terminal_api_verifier_present?: boolean;
    mt5_paper_execution_verifier_present?: boolean;
    mt5_deal_history_ingest_present?: boolean;
    runtime_gates_present: boolean;
    session_status?: string | null;
    activation_status?: string | null;
    roundtrip_status?: string | null;
    bridge_status?: string | null;
    heartbeat_status?: string | null;
    heartbeat_present: boolean;
    mailbox_ready: boolean;
    receipt_present: boolean;
    pending_receipt_count: number;
    receipt_mismatch_count: number;
    history_export_verifier_status?: string | null;
    history_export_present: boolean;
    history_export_parse_status?: string | null;
    history_record_count: number;
    memory_update_count: number;
    unmatched_history_count: number;
    position_reconciliation_status?: string | null;
    account_snapshot_present: boolean;
    mt5_terminal_api_verifier_status?: string | null;
    mt5_terminal_connected?: boolean;
    mt5_broker_api_verified?: boolean;
    mt5_account_snapshot_present?: boolean;
    mt5_open_position_count?: number;
    mt5_open_positions_reconciled?: boolean;
    mt5_server?: string | null;
    mt5_account_balance?: number | null;
    mt5_account_equity?: number | null;
    mt5_paper_execution_verifier_status?: string | null;
    mt5_paper_order_request_built?: boolean;
    mt5_paper_order_check_status?: string | null;
    mt5_paper_execution_attempted?: boolean;
    mt5_paper_execution_status?: string | null;
    mt5_paper_execution_error_message?: string | null;
    mt5_paper_terminal_trade_allowed?: boolean | null;
    mt5_paper_raw_response_hash?: string | null;
    mt5_paper_close_attempted?: boolean;
    mt5_paper_close_success?: boolean;
    mt5_deal_history_ingest_status?: string | null;
    mt5_deal_history_raw_deal_count?: number;
    mt5_deal_history_closed_position_count?: number;
    mt5_deal_history_memory_update_count?: number;
    mt5_deal_history_unmatched_count?: number;
    mt5_deal_history_net_profit_loss_account?: number;
    cas_open_position_count: number;
    terminal_open_position_count: number;
    reconciled_open_position_count: number;
    unmatched_open_position_count: number;
    live_flag_visible: boolean;
    live_trading_authorized: boolean;
    broker_accept_authorized: boolean;
    money_movement_authorized: boolean;
    all_real_money_authorized: boolean;
    runtime_gate_pending_capabilities: string[];
    net_profit_loss_account: number;
  };
  checks: Array<{
    check_id: string;
    description: string;
    status: string;
    value: unknown;
    detail: string;
  }>;
  go_no_go: {
    terminal_lane_go: boolean;
    live_order_go: boolean;
    broker_accept_go: boolean;
    money_movement_go: boolean;
    blocking_reasons: string[];
  };
  runtime_gate_decisions: Record<string, unknown>;
  claim_boundary: string;
  next_action: string;
  operator_commands: Record<string, string>;
  output_dir: string;
  artifact_paths?: Record<string, string>;
  report_path?: string;
}

export interface MT5TerminalApiVerifierReport {
  report_kind: string;
  created_at: string;
  verifier_status: string;
  schema: string;
  trading_date: string;
  mt5_path?: string | null;
  probe: Record<string, unknown>;
  terminal_snapshot: Record<string, unknown>;
  summary: {
    mt5_package_available: boolean;
    initialize_ok: boolean;
    terminal_connected: boolean;
    probe_status?: string | null;
    broker?: string | null;
    broker_mode?: string | null;
    receipt_validation_status?: string | null;
    broker_api_authenticated: boolean;
    broker_source_verified: boolean;
    server?: string | null;
    terminal_name?: string | null;
    account_snapshot_present: boolean;
    account_currency?: string | null;
    account_balance?: number | null;
    account_equity?: number | null;
    open_position_count: number;
    open_positions_reconciled: boolean;
    orders_attempted: number;
    orders_paper_executed: number;
    live_mode_used: boolean;
    reasons: string[];
  };
  claim_boundary: string;
  next_action: string;
  operator_commands: Record<string, string>;
  output_dir: string;
  artifact_paths?: Record<string, string>;
  report_path?: string;
}

export interface MT5PaperExecutionVerifierReport {
  report_kind: string;
  created_at: string;
  verifier_status: string;
  schema: string;
  trading_date: string;
  mt5_path?: string | null;
  execution_controls: {
    execute_demo_order: boolean;
    confirm_demo_order: boolean;
    close_after_send: boolean;
    live_mode_forced_off: boolean;
    paper_trading_forced_on: boolean;
  };
  api_verifier: Record<string, unknown>;
  terminal_snapshot: Record<string, unknown>;
  order: Record<string, unknown>;
  mt5_request: Record<string, unknown>;
  order_check: Record<string, unknown>;
  execution_result: Record<string, unknown>;
  summary: {
    mt5_api_verified: boolean;
    api_verifier_status?: string | null;
    terminal_connected: boolean;
    terminal_name?: string | null;
    terminal_trade_allowed?: boolean;
    server?: string | null;
    demo_account_confirmed: boolean;
    account_snapshot_present: boolean;
    account_balance?: number | null;
    account_equity?: number | null;
    open_position_count_before: number;
    order_request_built: boolean;
    order_error?: string | null;
    symbol?: string | null;
    direction?: string | null;
    volume?: number | null;
    raw_request_hash?: string | null;
    order_check_attempted: boolean;
    order_check_status?: string | null;
    execution_attempted: boolean;
    execution_status?: string | null;
    execution_error_message?: string | null;
    broker_ticket?: string | number | null;
    filled_price?: number | null;
    close_attempted: boolean;
    close_success: boolean;
    raw_response_hash?: string | null;
    live_mode_used: boolean;
  };
  claim_boundary: string;
  next_action: string;
  operator_commands: Record<string, string>;
  output_dir: string;
  artifact_paths?: Record<string, string>;
  report_path?: string;
}

export interface TerminalReceiptIngestRecord {
  receipt_id: string;
  command_id: string;
  cycle_id: string | null;
  intent_id: string | null;
  decision_id: string | null;
  agent_id: string | null;
  symbol: string | null;
  timeframe: string | null;
  command_path: string | null;
  receipt_path: string | null;
  status: string | null;
  receipt_validation_status: string;
  lifecycle_status: string;
  reconcile_status: string;
  next_cycle_status: string;
  raw_request_hash: string | null;
  expected_raw_request_hash: string | null;
  raw_request_hash_match: boolean;
  raw_response_hash: string | null;
  terminal_name: string | null;
  terminal_build: string | number | null;
  account_id_hash: string | null;
  server: string | null;
  broker_mode: string | null;
  live_mode: boolean;
  live_trading_allowed: boolean;
  broker_ticket: string | number | null;
  filled_price: number | null;
  filled_volume: number | null;
  slippage_pips: number | null;
  commission: number | null;
  swap: number | null;
  error_code: string | number | null;
  account_snapshot_present: boolean;
  terminal_identity_present: boolean;
  reasons: string[];
  receipt_sha256: string | null;
  ingest_action: string;
  event_ids: string[];
}

export interface TerminalReceiptIngestReport {
  report_kind: string;
  created_at: string;
  ingest_status: string;
  mailbox_dir: string;
  event_log_path: string;
  summary: {
    receipt_count: number;
    new_receipt_count: number;
    skipped_already_ingested_count: number;
    verified_receipt_count: number;
    reconciled_receipt_count: number;
    next_cycle_allowed_count: number;
    receipt_mismatch_count: number;
    terminal_locked_count: number;
    appended_event_count: number;
    appended_event_ids: string[];
    pending_receipt_count: number;
    event_count: number;
    latest_event_id: string | null;
    latest_cycle_id: string | null;
    event_type_counts: Record<string, number>;
    status_counts: Record<string, number>;
  };
  receipt_records: TerminalReceiptIngestRecord[];
  claim_boundary: string;
  next_action: string;
  artifact_paths?: Record<string, string>;
  report_path?: string;
}

export interface MT5ProbeStatus {
  probe_path: string; status: string; broker: string | null; trading_date: string | null;
  has_receipt: boolean; receipt_validation_status: string | null; account_snapshot_present: boolean;
  reasons: string[]; claim_boundary: string;
}

export interface MT5Receipt {
  receipt_id: string; receipt_validation_status: string; broker_mode: string;
  trading_date: string; symbols: string[]; orders_attempted: number;
  open_positions_reconciled: boolean; live_mode: boolean;
  broker_api_authenticated: boolean; broker_source_verified: boolean;
  server: string; terminal_name: string;
  receipt_hash_sha256: string; broker_export_sha256: string;
  account_snapshot?: { balance?: number; equity?: number; margin?: number; margin_free?: number; currency?: string; leverage?: number; account_id_hash?: string; server?: string };
  balance?: number | null; equity?: number | null; margin?: number | null; margin_free?: number | null;
  account_currency?: string | null; account_leverage?: number | null;
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
  allowed_scopes: string[]; allowed_scope_count?: number;
  blockers: string[]; blocker_count?: number;
  claim_boundary: string; claim_boundary_present?: boolean;
  ledger_deployment_status_counts: Record<string, number>;
  live_execution_runtime_locked: boolean;
  summary_only?: boolean;
}

export interface RuntimeGateDecision {
  capability: string; authorized: boolean; status: string;
  missing_requirements: string[]; satisfied_requirements: string[];
  advisory_requirements?: string[]; next_action: string;
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

export interface RuntimeGatesState {
  report_kind: string;
  decisions: Record<string, RuntimeGateDecision>;
  all_real_money_authorized: boolean;
  summary: string;
  owner_authority_boundary?: string;
  advisory_only_inputs?: string[];
  action_time_requirements?: string[];
  owner_controls_are_final_authority?: boolean;
  metrics_and_ai_can_veto_owner_authority?: boolean;
}

export interface AutoHaltCheck {
  check_id: string;
  status: string;
  metric: unknown;
  threshold: unknown;
  detail: string;
  trips_halt: boolean;
}

export interface AutoHaltReport {
  report_kind: string;
  generated_at?: string;
  status: string;
  halt_active: boolean;
  force_paper_mode: boolean;
  settings: {
    max_account_drawdown_pct: number;
    max_consecutive_losses: number;
    max_live_paper_divergence_pct: number;
  };
  checks: AutoHaltCheck[];
  triggered_checks: string[];
  active_state?: Record<string, unknown>;
  claim_boundary?: string;
  next_action: string;
  clear_state?: Record<string, unknown>;
}

export interface BrokerTruthMonitorCheck {
  check_id: string;
  status: string;
  value: unknown;
  description: string;
  detail: string;
  trips_auto_halt?: boolean;
}

export interface BrokerTruthMonitorReport {
  report_kind: string;
  generated_at: string;
  monitor_status: string;
  overall_status: string;
  checks_total: number;
  checks_ok: number;
  checks_mismatch: number;
  checks_unverifiable: number;
  running_status?: string;
  interval_seconds?: number;
  fresh_for_live_seconds?: number;
  mt5_connected: boolean;
  mt5_is_demo?: boolean | null;
  mt5_open_position_count?: number;
  terminal_reconciliation_status?: string | null;
  terminal_unmatched_open_position_count?: number;
  terminal_pending_receipt_count?: number;
  terminal_receipt_mismatch_count?: number;
  terminal_account_snapshot_present?: boolean;
  checks: BrokerTruthMonitorCheck[];
  latest_terminal_reconciliation?: Record<string, unknown> | null;
  claim_boundary: string;
  next_action: string;
}

export interface BrokerTruthMonitorSupervisorStatus {
  report_kind: string;
  status?: string;
  generated_at?: string;
  desired_running: boolean;
  active_lease?: Record<string, unknown> | null;
  active_lease_is_fresh: boolean;
  owned_by_this_process: boolean;
  local_owner_id: string;
  local_running: boolean;
  stop_requested_at?: string | null;
  stop_requested_by?: string | null;
  state_path?: string;
  audit_path?: string;
  claim_boundary: string;
  next_action: string;
  recovery?: Record<string, unknown>;
}

export interface BrokerTruthMonitorStatus {
  report_kind: string;
  running: boolean;
  status?: string;
  interval_seconds: number;
  cycles_run: number;
  last_error?: string | null;
  started_at_iso?: string | null;
  monitor_status: string;
  ready_for_live: boolean;
  latest_report?: BrokerTruthMonitorReport | null;
  supervisor?: BrokerTruthMonitorSupervisorStatus;
  claim_boundary: string;
}

export interface BrokerTruthRecoveryPacket {
  report_kind: string;
  generated_at: string;
  status: string;
  broker_truth_clear_for_live_recovery: boolean;
  broker_touched: boolean;
  live_order_attempted: boolean;
  attempt_finalized: boolean;
  money_moved: boolean;
  monitor_summary: Record<string, unknown>;
  blockers: Array<{
    blocker_id: string;
    clear: boolean;
    value: unknown;
    detail: string;
  }>;
  claim_boundary: string;
  next_action: string;
}

export interface LiveMoneyProgressionBlocker {
  blocker_id: string;
  plane: string;
  clear: boolean;
  value: unknown;
  detail: string;
  next_action?: string;
}

export interface LiveMoneyProgressionPacket {
  report_kind: string;
  generated_at: string;
  status: string;
  live_dispatch_clear: boolean;
  waste_pilot_clear: boolean;
  verified_payout_clear: boolean;
  full_progression_clear: boolean;
  broker_truth_clear: boolean;
  live_recovery_clear: boolean;
  live_readiness_clear: boolean;
  broker_touched: boolean;
  live_order_attempted: boolean;
  attempt_finalized: boolean;
  edge_token_minted: boolean;
  owner_accept_created: boolean;
  money_moved: boolean;
  active_waste_intent: {
    symbol?: string | null;
    direction?: string | null;
    lots?: number | null;
    entry_pair_count?: number | null;
    status?: string | null;
  };
  source_summaries: Record<string, unknown>;
  blocker_count: number;
  blockers: LiveMoneyProgressionBlocker[];
  claim_boundary: string;
  next_action: string;
  cache_status?: string;
  cache_built_at_epoch?: number | null;
  cache_generated_at_iso?: string | null;
  cache_age_seconds?: number | null;
  cache_ttl_seconds?: number;
  cache_stale?: boolean;
  cache_refreshing?: boolean;
  cache_error?: string;
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

export interface BrokerRealityReview {
  report_kind: string;
  broker_id: string;
  broker_display_name: string;
  broker_website: string;
  owner_review_status: string;
  accepted_for_live_and_payout: boolean;
  owner_accepted_at?: string | null;
  updated_at?: string | null;
  review_valid_days: number;
  broker_entity: string;
  withdrawal_minimum: string;
  withdrawal_timing: string;
  kyc_requirements: string;
  withdrawal_fees: string;
  currency_conversion: string;
  automation_tos: string;
  automation_allowed_by_owner_review: boolean;
  source_urls: string[];
  notes: string;
  checks: Record<string, boolean>;
  missing_requirements: string[];
  claim_boundary: string;
  next_action: string;
}

export interface LivePilotPolicy {
  report_kind: string;
  owner_pilot_status: string;
  accepted_for_live_start: boolean;
  ready_for_next_live_order: boolean;
  owner_accepted_at?: string | null;
  updated_at?: string | null;
  allowed_symbols: string[];
  max_trade_lots: number;
  max_open_live_lots: number;
  max_live_trade_count: number;
  max_daily_loss_usd: number;
  max_total_loss_usd: number;
  max_pilot_days: number;
  live_trade_count: number;
  pilot_capacity_remaining: number;
  last_live_order_at?: string | null;
  last_live_order?: Record<string, unknown> | null;
  notes: string;
  checks: Record<string, boolean>;
  missing_requirements: string[];
  claim_boundary: string;
  next_action: string;
}

export interface LiveOrderDryRunCheck {
  check_id: string;
  passed: boolean;
  status: string;
  detail: string;
  evidence?: unknown;
}

export interface LiveOrderDryRunAuditRecord {
  audit_id?: string;
  action?: string;
  timestamp?: string;
  status?: string;
  order_id?: string;
  decision_ref?: string;
  payload?: LiveOrderDryRunReport | Record<string, unknown>;
}

export interface LiveOrderDryRunReport {
  report_kind: string;
  generated_at: string;
  status: string;
  would_reach_broker_if_executed: boolean;
  broker_touched: boolean;
  order_id: string;
  decision_ref: string;
  proposed_intent: Record<string, unknown>;
  order_request?: Record<string, unknown> | null;
  checks: LiveOrderDryRunCheck[];
  blocking_reasons: string[];
  next_action: string;
  claim_boundary: string;
  audit?: LiveOrderDryRunAuditRecord;
  waste_real_candle_source?: Record<string, unknown>;
}

export interface LiveOrderDryRunLatest {
  report_kind: string;
  status: string;
  broker_touched: boolean;
  detail?: string;
  latest_audit?: LiveOrderDryRunAuditRecord | null;
}

export interface LiveOrderDryRunReview {
  report_kind: string;
  generated_at: string;
  review_status: string;
  owner_review_status: string;
  owner_accepted_at?: string | null;
  accepted_fingerprint?: string | null;
  current_fingerprint: string;
  dry_run_review_clear_for_live: boolean;
  evidence_ready_for_owner_accept: boolean;
  missing_requirements: string[];
  checks: Array<{
    check_id: string;
    status: string;
    evidence: Record<string, unknown>;
    detail: string;
  }>;
  latest_dry_run_summary: Record<string, unknown>;
  broker_truth_summary: Record<string, unknown>;
  claim_boundary: string;
  next_action: string;
}

export interface CompoundAddOrderDryRunAuditRecord {
  report_kind?: string;
  timestamp?: string;
  action?: string;
  status?: string;
  order_id?: string;
  decision_ref?: string;
  payload?: CompoundAddOrderDryRunReport | Record<string, unknown>;
}

export interface CompoundAddOrderDryRunReport {
  report_kind: string;
  generated_at?: string;
  status: string;
  broker_touched: boolean;
  order_id?: string;
  decision_ref?: string;
  proposed_intent?: Record<string, unknown>;
  order_request?: Record<string, unknown> | null;
  checks?: LiveOrderDryRunCheck[];
  blocking_reasons?: string[];
  parent_position_reference?: string | null;
  compound_context?: Record<string, unknown>;
  next_action?: string;
  claim_boundary?: string;
  audit?: CompoundAddOrderDryRunAuditRecord;
}

export interface CompoundAddOrderDryRunLatest {
  report_kind: string;
  status: string;
  broker_touched: boolean;
  detail?: string;
  latest_audit?: CompoundAddOrderDryRunAuditRecord | null;
}

export interface CompoundAddOrderDryRunReview {
  report_kind: string;
  generated_at: string;
  review_status: string;
  owner_review_status: string;
  owner_accepted_at?: string | null;
  accepted_fingerprint?: string | null;
  current_fingerprint?: string | null;
  compound_add_dry_run_review_clear_for_dispatch: boolean;
  evidence_ready_for_owner_accept: boolean;
  missing_requirements: string[];
  checks: Array<{
    check_id: string;
    status: string;
    evidence: Record<string, unknown>;
    detail: string;
  }>;
  latest_compound_add_summary: Record<string, unknown>;
  broker_truth_summary: Record<string, unknown>;
  claim_boundary: string;
  next_action: string;
}

export interface CompoundAddDispatchHandoffStatus {
  report_kind: string;
  status: string;
  order_id?: string | null;
  decision_ref?: string | null;
  broker_touched: boolean;
  dispatched_to_bridge: boolean;
  dispatch_attempted?: boolean;
  owner_dispatch_confirmed?: boolean;
  live_trading_authorized?: boolean;
  dispatch_preview_only?: boolean;
  would_call_dispatch_if_owner_attempted?: boolean;
  intent?: Record<string, unknown>;
  dispatch_result?: Record<string, unknown>;
  handoff_status?: CompoundAddDispatchHandoffStatus;
  owner_review_status?: string;
  compound_add_dry_run_review_clear_for_dispatch?: boolean;
  missing_requirements?: string[];
  reason?: string;
  detail?: string;
  notes?: string;
  claim_boundary?: string;
  next_action?: string;
}

export interface WasteEntryDispatchHandoffStatus {
  report_kind: string;
  status: string;
  order_id?: string | null;
  decision_ref?: string | null;
  broker_touched: boolean;
  dispatched_to_bridge: boolean;
  dispatch_attempted?: boolean;
  owner_dispatch_confirmed?: boolean;
  live_trading_authorized?: boolean;
  dispatch_preview_only?: boolean;
  would_call_dispatch_if_owner_attempted?: boolean;
  intent?: Record<string, unknown>;
  dispatch_result?: Record<string, unknown>;
  handoff_status?: WasteEntryDispatchHandoffStatus;
  owner_review_status?: string;
  dry_run_review_clear_for_live?: boolean;
  waste_real_candle_source?: Record<string, unknown>;
  missing_requirements?: string[];
  reason?: string;
  detail?: string;
  notes?: string;
  claim_boundary?: string;
  next_action?: string;
}

export interface WasteEntryPilotPromotionStatus {
  report_kind: string;
  generated_at?: string;
  status: string;
  ready_for_pilot_sequence: boolean;
  broker_touched: boolean;
  dispatched_to_bridge: boolean;
  dispatch_attempted: boolean;
  order_id?: string | null;
  decision_ref?: string | null;
  symbol?: string | null;
  direction?: string | null;
  lots?: number | null;
  entry_pair_count?: number | null;
  missing_requirements: string[];
  checks: Array<{
    check_id: string;
    status: string;
    evidence: Record<string, unknown>;
    detail: string;
  }>;
  handoff_status?: WasteEntryDispatchHandoffStatus;
  dry_run_review_summary?: Record<string, unknown>;
  pilot_policy_summary?: Record<string, unknown>;
  live_recovery_summary?: Record<string, unknown>;
  order_attempt_summary?: Record<string, unknown>;
  waste_real_candle_source?: Record<string, unknown>;
  claim_boundary?: string;
  next_action?: string;
}

export interface WasteDirectionReviewPacket {
  report_kind: string;
  generated_at: string;
  status: string;
  direction_edge_confirmed: boolean;
  broker_touched: boolean;
  live_order_attempted: boolean;
  attempt_finalized: boolean;
  edge_token_minted: boolean;
  money_moved: boolean;
  direction_summary: {
    symbol?: string | null;
    timeframe?: string | null;
    direction?: string | null;
    opposite_direction?: string | null;
    long_score?: number | null;
    short_score?: number | null;
    chosen_score?: number | null;
    opposite_score?: number | null;
    score_margin?: number | null;
    confidence?: number | null;
    regime?: string | null;
    profile?: string | null;
    decision_ref?: string | null;
    entry_pair_count?: number | null;
  };
  profit_box: {
    valid?: boolean;
    entry?: number | null;
    stop_loss?: number | null;
    take_profit?: number | null;
    risk_units?: number | null;
    reward_units?: number | null;
    reward_r?: number | null;
    direction?: string | null;
  };
  edge_gate_summary: {
    status?: string | null;
    measured_win_prob?: number | null;
    threshold?: number | null;
    null_p95?: number | null;
    has_edge_token?: boolean;
    reason?: string | null;
  };
  cas_context: Record<string, unknown>;
  blocker_count: number;
  blockers: Array<{
    blocker_id: string;
    plane: string;
    clear: boolean;
    value: unknown;
    detail: string;
    next_action?: string;
  }>;
  claim_boundary: string;
  next_action: string;
}

export interface WasteDirectionLearningLedger {
  report_kind: string;
  generated_at: string;
  status: string;
  cycles_loaded: number;
  direction_rows: number;
  confirmed_direction_count: number;
  blocked_direction_count: number;
  direction_counts: Record<string, number>;
  edge_status_counts: Record<string, number>;
  groups: Array<Record<string, unknown>>;
  profile_recommendation: Record<string, unknown>;
  learning_ready_for_adaptation: boolean;
  broker_touched: boolean;
  live_order_attempted: boolean;
  attempt_finalized: boolean;
  edge_token_minted: boolean;
  money_moved: boolean;
  sample_rows: Array<Record<string, unknown>>;
  claim_boundary: string;
  next_action: string;
}

export interface WasteDirectionOutcomeBinding {
  report_kind: string;
  generated_at: string;
  status: string;
  read_only: boolean;
  dry_run: boolean;
  paper_only: boolean;
  outcome_ready_for_promotion: boolean;
  min_bound_outcomes_for_promotion: number;
  direction_rows: number;
  confirmed_direction_count: number;
  executed_confirmed_count: number;
  closed_history_count: number;
  bound_outcome_count: number;
  unbound_confirmed_count: number;
  bound_outcomes_needed: number;
  profitable_bound_count: number;
  losing_bound_count: number;
  flat_bound_count: number;
  net_paper_pnl: number;
  avg_bound_pnl: number;
  direction_counts: Record<string, number>;
  profile_counts: Record<string, number>;
  paper_demo_history_status?: string | null;
  history_account_mode?: string | null;
  history_report_path?: string | null;
  runtime_changed: boolean;
  runtime_change_attempted: boolean;
  would_apply_runtime_change: boolean;
  would_lower_edge_threshold: boolean;
  would_enable_live_trading: boolean;
  would_raise_risk: boolean;
  broker_touched: boolean;
  live_order_attempted: boolean;
  attempt_finalized: boolean;
  edge_token_minted: boolean;
  owner_accept_created: boolean;
  money_moved: boolean;
  bound_rows: Array<Record<string, unknown>>;
  unbound_confirmed_rows: Array<Record<string, unknown>>;
  claim_boundary: string;
  next_action: string;
}

export interface WastePaperSampleCollector {
  report_kind: string;
  generated_at: string;
  status: string;
  read_only: boolean;
  dry_run: boolean;
  paper_only: boolean;
  sample_collection_complete: boolean;
  paper_runner_running: boolean;
  paper_runner_mode: string;
  market_data_ready: boolean;
  mt5_market_data_status?: string | null;
  mt5_ready_symbol_count: number;
  real_candle_probe_status?: string | null;
  real_candle_probe_broker_grade: boolean;
  real_candle_probe_fallback_used: boolean;
  probe_symbol?: string | null;
  probe_timeframe?: string | null;
  probe_direction?: string | null;
  probe_edge_status?: string | null;
  probe_edge_pass_unregistered: boolean;
  direction_rows: number;
  confirmed_direction_count: number;
  confirmed_samples_needed: number;
  executed_confirmed_count: number;
  closed_history_count: number;
  bound_outcome_count: number;
  bound_outcomes_needed: number;
  net_paper_pnl: number;
  mt5_deal_history_status?: string | null;
  mt5_deal_history_account_mode?: string | null;
  runtime_changed: boolean;
  runtime_change_attempted: boolean;
  would_apply_runtime_change: boolean;
  would_lower_edge_threshold: boolean;
  would_enable_live_trading: boolean;
  would_raise_risk: boolean;
  broker_touched: boolean;
  broker_execution_touched: boolean;
  live_order_attempted: boolean;
  attempt_finalized: boolean;
  edge_token_minted: boolean;
  owner_accept_created: boolean;
  money_moved: boolean;
  checks: Array<{
    check_id: string;
    status: string;
    passed: boolean;
    detail: string;
    evidence: Record<string, unknown>;
  }>;
  required_actions: Array<{
    action_id: string;
    detail: string;
    route: string;
    command?: string | null;
    requires_owner_review: boolean;
    can_touch_broker_execution: boolean;
    can_authorize_live_trading: boolean;
    can_create_owner_accept: boolean;
    can_create_broker_accept: boolean;
    can_move_money: boolean;
  }>;
  source_summaries: Record<string, unknown>;
  claim_boundary: string;
  next_action: string;
}

export interface WastePaperSampleCollectorScheduler {
  report_kind: string;
  generated_at: string;
  running: boolean;
  status: string;
  interval_seconds: number;
  cycles_run: number;
  started_at_iso?: string | null;
  last_run_iso?: string | null;
  last_error?: string | null;
  latest_run?: Record<string, unknown> | null;
  latest_collector_status?: string | null;
  sample_collection_complete: boolean;
  market_data_ready: boolean;
  confirmed_direction_count: number;
  bound_outcome_count: number;
  bound_outcomes_needed: number;
  config: {
    run_market_diagnostic: boolean;
    run_real_candle_probe: boolean;
    run_deal_history_ingest: boolean;
    symbol?: string | null;
    timeframe?: string | null;
    bars?: number | null;
    max_pairs?: number | null;
  };
  config_present?: boolean;
  paper_only: boolean;
  read_only_market_actions_only: boolean;
  runtime_changed: boolean;
  runtime_change_attempted: boolean;
  would_apply_runtime_change: boolean;
  would_lower_edge_threshold: boolean;
  would_enable_live_trading: boolean;
  would_raise_risk: boolean;
  broker_touched: boolean;
  broker_execution_touched: boolean;
  live_order_attempted: boolean;
  attempt_finalized: boolean;
  edge_token_minted: boolean;
  owner_accept_created: boolean;
  money_moved: boolean;
  external_worker_present?: boolean;
  state_path?: string | null;
  audit_path?: string | null;
  claim_boundary: string;
  claim_boundary_present?: boolean;
  next_action: string;
  next_action_present?: boolean;
  full_status_route?: string;
  summary_only?: boolean;
}

export interface WasteAdaptationPromotionRule {
  report_kind: string;
  generated_at: string;
  status: string;
  read_only: boolean;
  dry_run: boolean;
  promotion_ready_for_owner_review: boolean;
  learning_ready_for_adaptation: boolean;
  outcome_ready_for_promotion: boolean;
  min_confirmed_for_adaptation: number;
  confirmed_direction_count: number;
  confirmed_samples_needed: number;
  bound_outcome_count?: number | null;
  bound_outcomes_needed?: number | null;
  net_paper_pnl?: number | null;
  blocked_direction_count: number;
  direction_rows: number;
  direction_counts: Record<string, number>;
  edge_status_counts: Record<string, number>;
  profile_recommendation_status?: string | null;
  outcome_binding_summary?: Record<string, unknown>;
  dominant_group: Record<string, unknown>;
  recommended_group: Record<string, unknown>;
  runtime_changed: boolean;
  runtime_change_attempted: boolean;
  would_apply_runtime_change: boolean;
  would_lower_edge_threshold: boolean;
  would_enable_live_trading: boolean;
  would_raise_risk: boolean;
  broker_touched: boolean;
  live_order_attempted: boolean;
  attempt_finalized: boolean;
  edge_token_minted: boolean;
  owner_accept_created: boolean;
  money_moved: boolean;
  claim_boundary: string;
  next_action: string;
}

export interface WasteAdaptationPlan {
  report_kind: string;
  generated_at: string;
  status: string;
  dry_run: boolean;
  adaptation_ready_for_owner_review: boolean;
  runtime_changed: boolean;
  runtime_change_attempted: boolean;
  would_lower_edge_threshold: boolean;
  would_enable_live_trading: boolean;
  broker_touched: boolean;
  live_order_attempted: boolean;
  attempt_finalized: boolean;
  edge_token_minted: boolean;
  owner_accept_created: boolean;
  money_moved: boolean;
  learning_summary: Record<string, unknown>;
  promotion_rule_summary: Record<string, unknown>;
  latest_direction_summary: Record<string, unknown>;
  proposal_count: number;
  proposals: Array<{
    proposal_id: string;
    proposal_type: string;
    detail: string;
    dry_run: boolean;
    would_apply_runtime_change: boolean;
    would_lower_edge_threshold: boolean;
    would_enable_live_trading: boolean;
    requires_owner_review: boolean;
    evidence: Record<string, unknown>;
  }>;
  claim_boundary: string;
  next_action: string;
}

export interface WasteAdaptationApplyPreview {
  report_kind: string;
  generated_at: string;
  status: string;
  dry_run: boolean;
  owner_review_required: boolean;
  preview_ready_for_owner_review: boolean;
  apply_allowed_now: boolean;
  apply_endpoint_available: boolean;
  runtime_changed: boolean;
  runtime_change_attempted: boolean;
  would_apply_runtime_change: boolean;
  would_lower_edge_threshold: boolean;
  would_enable_live_trading: boolean;
  would_raise_risk: boolean;
  would_create_owner_accept: boolean;
  broker_touched: boolean;
  live_order_attempted: boolean;
  attempt_finalized: boolean;
  edge_token_minted: boolean;
  owner_accept_created: boolean;
  money_moved: boolean;
  adaptation_plan_summary: Record<string, unknown>;
  runtime_gate_summary: Record<string, unknown>;
  current_controls: Record<string, unknown>;
  owner_envelope_summary: Record<string, unknown>;
  simulated_change_count: number;
  simulated_changes: Array<{
    proposal_id?: string | null;
    proposal_type?: string | null;
    change_type: string;
    field: string;
    current_value: unknown;
    preview_value: unknown;
    dry_run: boolean;
    would_apply_runtime_change: boolean;
    would_lower_edge_threshold: boolean;
    would_enable_live_trading: boolean;
    would_raise_risk: boolean;
    requires_owner_review: boolean;
    rationale: string;
  }>;
  blocker_count: number;
  blockers: Array<{
    blocker_id: string;
    clear: boolean;
    detail: string;
    evidence: Record<string, unknown>;
  }>;
  claim_boundary: string;
  next_action: string;
}

export interface WasteAdaptationOwnerReview {
  report_kind: string;
  generated_at: string;
  owner_review_status: string;
  owner_review_decision: string;
  owner_reviewed_at?: string | null;
  owner_review_notes?: string | null;
  accepted_fingerprint?: string | null;
  current_fingerprint: string;
  reviewed_fingerprint?: string | null;
  paper_only_review_current: boolean;
  paper_only_accept_current: boolean;
  evidence_ready_for_owner_accept: boolean;
  missing_requirements: string[];
  checks: Array<{
    check_id: string;
    status: string;
    evidence: Record<string, unknown>;
    detail: string;
  }>;
  preview_summary: Record<string, unknown>;
  dry_run: boolean;
  paper_only: boolean;
  apply_allowed_now: boolean;
  apply_endpoint_available: boolean;
  runtime_changed: boolean;
  runtime_change_attempted: boolean;
  would_apply_runtime_change: boolean;
  would_lower_edge_threshold: boolean;
  would_enable_live_trading: boolean;
  would_raise_risk: boolean;
  would_create_live_authority: boolean;
  broker_touched: boolean;
  live_order_attempted: boolean;
  attempt_finalized: boolean;
  edge_token_minted: boolean;
  owner_accept_created: boolean;
  money_moved: boolean;
  claim_boundary: string;
  next_action: string;
}

export interface WasteAdaptationPaperApply {
  report_kind: string;
  generated_at: string;
  status: string;
  paper_apply_ready: boolean;
  paper_apply_current: boolean;
  paper_apply_recorded: boolean;
  paper_apply_recorded_at?: string | null;
  applied_fingerprint?: string | null;
  current_fingerprint: string;
  accepted_fingerprint?: string | null;
  paper_only: boolean;
  dry_run: boolean;
  apply_requires_owner_confirm: boolean;
  runtime_changed: boolean;
  runtime_change_attempted: boolean;
  would_apply_runtime_change: boolean;
  would_lower_edge_threshold: boolean;
  would_enable_live_trading: boolean;
  would_raise_risk: boolean;
  broker_touched: boolean;
  live_order_attempted: boolean;
  attempt_finalized: boolean;
  edge_token_minted: boolean;
  owner_accept_created: boolean;
  money_moved: boolean;
  owner_review_summary: Record<string, unknown>;
  simulated_change_count: number;
  paper_apply_effect: Record<string, unknown>;
  missing_requirements: string[];
  checks: Array<{
    check_id: string;
    status: string;
    evidence: Record<string, unknown>;
    detail: string;
  }>;
  claim_boundary: string;
  next_action: string;
}

export interface LiveRecoveryReport {
  report_kind: string;
  generated_at: string;
  recovery_status: string;
  owner_recovery_status: string;
  owner_accepted_at?: string | null;
  accepted_fingerprint?: string | null;
  current_fingerprint: string;
  recovery_clear_for_live: boolean;
  requires_recovery_review: boolean;
  evidence_ready_for_owner_accept: boolean;
  missing_requirements: string[];
  checks: Array<{
    check_id: string;
    status: string;
    evidence: Record<string, unknown>;
    detail: string;
  }>;
  broker_truth_summary: Record<string, unknown>;
  live_pilot_summary: Record<string, unknown>;
  order_attempt_summary?: Record<string, unknown>;
  claim_boundary: string;
  next_action: string;
}

export interface PayoutRecoveryAttempt {
  attempt_id?: string;
  idempotency_key: string;
  status: string;
  created_at?: string;
  updated_at?: string;
  amount_usd?: number;
  destination_id?: string | null;
  preview_status?: string | null;
  preview_reason?: string | null;
  provider_reference?: string | null;
  provider_status?: string | null;
  provider_is_real?: boolean | null;
  movement_status?: string | null;
  movement_reason?: string | null;
  recovery_reason?: string;
  owner_resolved_at?: string;
  owner_resolution_notes?: string;
  claim_boundary?: string;
  movement?: Record<string, unknown>;
}

export interface PayoutRecoveryStatus {
  report_kind: string;
  generated_at: string;
  attempt_count: number;
  pending_count: number;
  has_pending_recovery: boolean;
  latest_attempt?: PayoutRecoveryAttempt | null;
  pending_attempts: PayoutRecoveryAttempt[];
  claim_boundary: string;
  next_action: string;
}

export interface OrderAttemptAuditAttempt {
  attempt_id?: string;
  attempt_key?: string;
  status?: string;
  created_at?: string;
  updated_at?: string;
  source?: string;
  mode?: string;
  is_real_attempt?: boolean;
  bridge_name?: string;
  order_id?: string;
  decision_ref?: string;
  symbol?: string;
  direction?: string;
  volume?: number | null;
  result_finalized?: boolean;
  dispatched_to_bridge?: boolean;
  executed?: boolean;
  result_status?: string | null;
  result_reason?: string | null;
  outcome?: Record<string, unknown> | null;
  claim_boundary?: string;
}

export interface OrderAttemptAuditStatus {
  report_kind: string;
  generated_at: string;
  attempt_count: number;
  real_attempt_count: number;
  unresolved_attempt_count: number;
  unresolved_real_attempt_count: number;
  unresolved_real_attempts?: OrderAttemptAuditAttempt[];
  executed_count: number;
  latest_attempt?: OrderAttemptAuditAttempt | null;
  has_unresolved_real_attempt: boolean;
  state_path?: string;
  audit_path?: string;
  claim_boundary: string;
  next_action: string;
}

export interface OrderAttemptRecoveryPacket {
  report_kind: string;
  generated_at: string;
  status: string;
  can_reconcile_unresolved_attempts: boolean;
  broker_touched: boolean;
  dispatched_to_bridge: boolean;
  attempt_finalized: boolean;
  unresolved_real_attempt_count: number;
  synthetic_test_like_count: number;
  broker_review_required_count: number;
  missing_requirements: string[];
  broker_truth_checks: Array<{
    check_id: string;
    status: string;
    evidence: Record<string, unknown>;
    detail: string;
  }>;
  broker_truth_summary: Record<string, unknown>;
  unresolved_real_attempts: Array<OrderAttemptAuditAttempt & {
    classification_status?: string;
    classification_reasons?: string[];
    requires_owner_terminal_review?: boolean;
    owner_reconcile_route?: string;
  }>;
  claim_boundary: string;
  next_action: string;
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

export interface WasteRealCandleProbe {
  report_kind: string;
  status: string;
  generated_at?: string;
  symbol?: string | null;
  timeframe?: string | null;
  source?: string | null;
  fallback_used?: boolean;
  broker_grade_market_truth?: boolean;
  broker_touched?: boolean;
  edge_authorization_registered?: boolean;
  edge_token_persisted?: boolean;
  candles_count?: number;
  entry_pair_count?: number;
  market_state?: Record<string, unknown> | null;
  analysis?: Record<string, unknown> | null;
  candidate?: Record<string, unknown> | null;
  edge?: Record<string, unknown> | null;
  claim_boundary?: string;
  next_action?: string;
  detail?: string;
  error?: string;
  audit?: Record<string, unknown>;
}

export interface MT5MarketDataDiagnosticSymbol {
  symbol: string;
  timeframe: string;
  status: string;
  candle_count: number;
  has_quote: boolean;
  quote?: Record<string, unknown> | null;
  spread_pips?: number | null;
  broker_grade_market_truth: boolean;
  read_only_market_data: boolean;
  selected_broker_symbol?: string | null;
  symbol_resolution?: Record<string, unknown> | null;
  detail?: string | null;
  first_candle_time?: string | null;
  last_candle_time?: string | null;
}

export interface MT5MarketDataDiagnostic {
  report_kind: string;
  status: string;
  generated_at?: string;
  ready_symbol_count?: number;
  checked_symbol_count?: number;
  symbols: MT5MarketDataDiagnosticSymbol[];
  timeframe?: string;
  bars_requested?: number;
  broker_touched: boolean;
  edge_authorization_registered?: boolean;
  edge_token_persisted?: boolean;
  live_trading_authorized?: boolean;
  configured?: Record<string, unknown>;
  terminal_locator?: Record<string, unknown>;
  operator_commands?: Record<string, string>;
  claim_boundary?: string;
  next_action?: string;
  detail?: string;
  error?: string;
  audit?: Record<string, unknown>;
}

export interface DashboardState {
  uiReadiness: UIReadinessReport;
  dailySchedule: DailySchedule;
  dailyBundle: DailyBundle;
  riskBudget?: DashboardRiskBudgetSummary;
  proofProgress?: DashboardProofProgressSummary;
  adaptive?: AdaptiveCockpitPayload;
  ownerControl?: OwnerControlState;
  accountLedger?: AccountLedgerState;
  movementStream?: MovementStreamState;
  accountReconciliation?: AccountReconciliationReport;
  liveReadiness?: LiveReadinessReport;
  brokerSyncedRiskPreview?: BrokerSyncedRiskPreview;
  mtHistory?: MTHistorySummary;
  strategyLeads?: StrategyLead[];
  backsolve?: BacksolveSummary;
  conditionTally?: ConditionTallyBucket[];
  walkForward?: WalkForwardSummary;
  externalBenchmarks?: ExternalBenchmarkReport;
  forexFurySetImport?: ForexFurySetImportReport | null;
  forexFuryReplayCandidates?: ForexFuryReplayCandidateReport | null;
  forexFuryReplayResults?: ForexFuryReplayResultsReport | null;
  agentWorkflowPlan?: AgentWorkflowPlan | null;
  agentWorkflowCycle?: AgentWorkflowCycle | null;
  agentInformationFlow?: AgentInformationFlow | null;
  agentMessageBus?: AgentMessageBusSummary | null;
  agentMemory?: AgentMemoryReport | null;
  agentResearchQueue?: AgentResearchQueueReport | null;
  strategyDevQueue?: StrategyDevQueueReport | null;
  strategyPatchRunner?: StrategyPatchRunnerReport | null;
  dailyLearningRollup?: DailyLearningRollupReport | null;
  sessionAutowake?: SessionAutowakeReport | null;
  terminalReceiptWatcher?: TerminalReceiptWatcherReport | null;
  terminalBridgeSupervisor?: TerminalBridgeSupervisorReport | null;
  mt4TerminalActivation?: MT4TerminalActivationReport | null;
  mt4PingRoundtrip?: MT4PingRoundtripReport | null;
  mt4TerminalSessionVerifier?: MT4TerminalSessionVerifierReport | null;
  mt4HistoryExportVerifier?: MT4HistoryExportVerifierReport | null;
  mt5TerminalApiVerifier?: MT5TerminalApiVerifierReport | null;
  mt5PaperExecutionVerifier?: MT5PaperExecutionVerifierReport | null;
  mt5DealHistoryIngest?: MT5DealHistoryIngestReport | null;
  terminalPositionReconciliation?: TerminalPositionReconciliationReport | null;
  terminalReceiptRecoveryPacket?: TerminalReceiptRecoveryPacket | null;
  terminalOperabilityVerifier?: TerminalOperabilityVerifierReport | null;
  terminalReceiptIngest?: TerminalReceiptIngestReport | null;
  terminalHistoryIngest?: TerminalHistoryIngestReport | null;
  mt5Receipt?: MT5Receipt;
  mt5ProbeStatus?: MT5ProbeStatus;
  authorityBoundary?: AuthorityBoundaryState;
  runtimeGates?: RuntimeGatesState;
  autoHalt?: AutoHaltReport;
  brokerTruthMonitor?: BrokerTruthMonitorStatus;
  wasteLoop?: Record<string, unknown> | null;
  orderAttemptAudit?: OrderAttemptAuditStatus;
  orderAttemptRecoveryPacket?: OrderAttemptRecoveryPacket;
  payoutRecovery?: PayoutRecoveryStatus;
  aiModel?: AIModelState;
  brokerCandidates?: BrokerCandidate[];
  brokerReality?: BrokerRealityReview;
  livePilot?: LivePilotPolicy;
  liveOrderDryRun?: LiveOrderDryRunLatest | null;
  liveOrderDryRunReview?: LiveOrderDryRunReview | null;
  wasteEntryPilotPromotion?: WasteEntryPilotPromotionStatus | null;
  wasteDirectionReview?: WasteDirectionReviewPacket | null;
  wasteDirectionLearning?: WasteDirectionLearningLedger | null;
  wasteDirectionOutcomeBinding?: WasteDirectionOutcomeBinding | null;
  wastePaperSampleCollector?: WastePaperSampleCollector | null;
  wastePaperSampleCollectorScheduler?: WastePaperSampleCollectorScheduler | null;
  wasteAdaptationPromotionRule?: WasteAdaptationPromotionRule | null;
  wasteAdaptationPlan?: WasteAdaptationPlan | null;
  wasteAdaptationApplyPreview?: WasteAdaptationApplyPreview | null;
  wasteAdaptationOwnerReview?: WasteAdaptationOwnerReview | null;
  wasteAdaptationPaperApply?: WasteAdaptationPaperApply | null;
  compoundAddOrderDryRun?: CompoundAddOrderDryRunLatest | null;
  compoundAddOrderDryRunReview?: CompoundAddOrderDryRunReview | null;
  compoundAddDispatchHandoff?: CompoundAddDispatchHandoffStatus | null;
  liveRecovery?: LiveRecoveryReport;
  liveMoneyProgression?: LiveMoneyProgressionPacket;
  mt5MarketDataDiagnostic?: MT5MarketDataDiagnostic | null;
  wasteRealCandleProbe?: WasteRealCandleProbe | null;
  pcba?: PcbaCockpitPayload;
}

import { apiDelete, apiGet, apiPostJson } from "./apiCore";

export interface OperatorState {
  report_kind?: string;
  running?: boolean;
  operational_state?: string;
  desired_running?: boolean;
  interval_seconds?: number;
  last_tick_iso?: string | null;
  last_summary?: string | null;
  last_provider?: string | null;
  last_ok?: boolean | null;
  ticks_run?: number;
  last_error?: string | null;
  last_context_delivery?: {
    status?: string;
    decision_grade?: boolean;
    blind_character_slice_used?: boolean;
    source_context_chars?: number;
    packet_json_chars?: number;
    max_packet_json_chars?: number;
    critical_section_count?: number;
    critical_sections_present?: string[];
    critical_sections_missing?: string[];
    sections_summarized?: string[];
    sections_omitted?: string[];
    evidence_fingerprint?: string;
    generated_at?: string;
  };
  model_provider?: {
    active_provider?: string | null;
    active_provider_label?: string | null;
    active_is_paid?: boolean;
    active_note?: string;
    active_model?: string | null;
    active_backend?: string | null;
    active_model_role?: "fast" | "pro" | "general" | "fallback" | string | null;
    provider_reachability?: "READY" | "FAILED" | "STALE" | "NOT_PROBED" | string;
    provider_last_observed_reachability?: string;
    provider_health_age_seconds?: number | null;
    provider_health_fresh_seconds?: number;
    provider_last_attempt_at?: string | null;
    provider_last_error?: string | null;
    primary_configured?: boolean;
    primary_key_present?: boolean;
    primary_key_hint?: string;
    deepseek_configured?: boolean;
    deepseek_key_present?: boolean;
    deepseek_key_hint?: string;
    deepseek_transport?: string;
    gemma4_backup_configured?: boolean;
    gemma4_backup_transport?: string;
    primary_in_cooldown?: boolean;
    primary_cooldown_seconds_left?: number;
    budget_tokens?: number;
    spent_tokens?: number;
    budget_remaining?: number | null;
    budget_capped?: boolean;
    last_switch?: { from?: string | null; to?: string | null; reason?: string; at?: string } | null;
    role_routes?: Partial<Record<
      "fast" | "pro" | "backup",
      {
        provider?: string | null;
        provider_label?: string | null;
        model_ref?: string | null;
        backend?: string | null;
        reachability?: string;
        last_observed_reachability?: string;
        health_age_seconds?: number | null;
        last_attempt_at?: string | null;
        last_error?: string | null;
      }
    >>;
    chain?: Array<{
      name: string;
      label: string;
      model_ref?: string;
      backend?: string;
      model_role?: string;
      paid: boolean;
      note: string;
    }>;
  };
  recent_actions?: Array<Record<string, unknown>>;
  objective?: string;
  active_account_objective?: {
    report_kind?: string;
    status?: string;
    objective_account_established?: boolean;
    authoritative_account_source?: string;
    execution?: {
      running?: boolean;
      execution_active?: boolean;
      execution_lane?: string | null;
      mode?: string | null;
      bridge_class?: string | null;
      bridge_status?: string | null;
    };
    current_account?: {
      login?: number | string | null;
      server?: string | null;
      currency?: string | null;
      is_demo?: boolean;
      balance_usd?: number | null;
      equity_usd?: number | null;
      floating_pnl_usd?: number | null;
      margin_used_usd?: number | null;
      free_margin_usd?: number | null;
      leverage?: number | null;
      open_position_count?: number | null;
      position_price_pnl_usd?: number | null;
      open_swap_usd?: number | null;
      open_commission_usd?: number | null;
      reported_open_components_usd?: number | null;
      unattributed_open_pnl_usd?: number | null;
    };
    growth_measurement?: {
      current_balance_usd?: number | null;
      current_equity_usd?: number | null;
      floating_pnl_usd?: number | null;
      balance_baseline_status?: string;
      balance_change_since_baseline_usd?: number | null;
      current_balance_is_profit?: boolean;
      period_realized_status?: string;
      cashflow_adjusted_realized_growth_usd?: number | null;
      realized_today_usd?: number | null;
      realized_month_usd?: number | null;
      net_external_capital_flow_usd?: number | null;
      growth_pct_on_net_external_capital?: number | null;
      account_growth_reconciliation?: {
        status?: string;
        account_matches?: boolean;
        balance_matches?: boolean;
        reconciled?: boolean;
        event_hash?: string | null;
        generated_at?: string | null;
        refresh_status?: string | null;
      };
      open_pnl_decomposition?: {
        price_pnl_usd?: number | null;
        swap_or_carry_usd?: number | null;
        commission_usd?: number | null;
        reported_components_usd?: number | null;
        account_net_open_pnl_usd?: number | null;
        unattributed_open_pnl_usd?: number | null;
        interpretation?: string;
      };
      cas_bound_closed_outcomes?: {
        status?: string | null;
        trades?: number | null;
        wins?: number | null;
        losses?: number | null;
        net_pnl_usd?: number | null;
        scope?: string;
      };
      all_account_history_net_pnl_usd?: number | null;
      all_account_history_scope?: string;
    };
    daily_objective?: {
      target_usd?: number | null;
      cap_usd?: number | null;
      monthly_target_usd?: number | null;
      policy?: string;
      target_deficit_may_manufacture_trade?: boolean;
      target_deficit_may_increase_risk?: boolean;
      cap_may_suppress_new_entries?: boolean;
    };
    secondary_simulator_performance?: {
      scope?: string;
      balance_usd?: number | null;
      net_pnl_usd?: number | null;
      unique_signal_net_pnl_usd?: number | null;
      authoritative_for_active_account?: boolean | null;
    };
  };
  profit_and_balance?: {
    seed_capital_usd?: number;
    // Owner-set daily winnings target (and cap + monthly) — the operator pushes toward it.
    daily_winnings_target_usd?: number | null;
    daily_cap_usd?: number | null;
    monthly_target_usd?: number | null;
    // Question 1 — how much did the paper balance actually move (every lot counts)?
    balance_growth_net_pnl_usd?: number;
    honest_paper_balance_usd?: number;
    balance_question?: string;
    // Question 2 — one vote per independent signal: how sure are we it repeats?
    honest_unique_signal_net_pnl_usd?: number;
    evidence_question?: string;
    unique_signals?: number;
    unique_win_rate?: number;
    unique_profit_factor?: number | null;
    raw_net_pnl_usd?: number;
    raw_trades?: number;
    cluster_inflation_x?: number;
    biggest_cluster_size?: number;
    avg_winning_stack_depth?: number | null;
    avg_losing_stack_depth?: number | null;
    stacking_is_blind?: boolean | null;
    test_artifacts_quarantined?: number;
    test_artifacts_net_pnl_usd?: number;
    data_class?: string;
    scope?: string;
    authoritative_for_active_account?: boolean;
    interpretation?: string;
    daily_target_policy?: string;
    target_deficit_may_increase_risk?: boolean;
    caveats?: string[];
  };
  professional_readiness?: {
    status?: "OK" | "ATTENTION" | "WARMING" | string;
    item_count?: number;
    ok_count?: number;
    partial_count?: number;
    gap_count?: number;
    remaining_rows?: Array<{
      item_number?: number;
      key?: string;
      status?: "OK" | "PARTIAL" | "GAP" | "WARMING" | string;
    }>;
  };
  execution_runtime?: {
    status?: string | null;
    running?: boolean;
    execution_active?: boolean;
    execution_lane?: "PAPER" | "LIVE" | "NONE" | string | null;
    paper_learning_active?: boolean;
    paper_fallback_active?: boolean;
    paper_fallback_available?: boolean;
    live_execution_active?: boolean;
    live_execution_authorized?: boolean;
    live_execution_status?: string | null;
    requested_mode?: string | null;
    mode?: string | null;
    last_run_iso?: string | null;
    last_summary?: string | null;
    last_error?: string | null;
    last_blocking_detail?: string | null;
    live_blocking_detail?: string | null;
    last_bridge_class?: string | null;
    last_bridge_selection_status?: string | null;
    last_bridge_selection_detail?: string | null;
    cycles_run?: number | null;
    cycles_idle?: number | null;
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
        operator_sizing_option_count?: number | null;
        operator_max_executable_lots?: number | null;
        sizing_options?: Array<{
          sizing_ref?: string;
          label?: string;
          lots?: number;
          risk_at_stop_usd?: number | null;
          risk_at_stop_pct_equity?: number | null;
          estimated_margin_required_usd?: number | null;
        }>;
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
    management_cycles_run?: number | null;
    last_management_status?: string | null;
    last_management_detail?: string | null;
    last_management_draft_action_count?: number | null;
    last_management_action_count?: number | null;
    last_management_terminal_effect_count?: number | null;
    last_management_broker_touched?: boolean | null;
    last_operator_discretionary_status?: string | null;
    last_operator_discretionary_option_count?: number | null;
    last_operator_discretionary_position_count?: number | null;
    last_operator_discretionary_blocked_option_count?: number | null;
    last_operator_discretionary_model_failure_policy?: string | null;
    last_scale_in_status?: string | null;
    last_scale_in_action_count?: number | null;
    last_scale_in_parent_candidate_count?: number | null;
    last_scale_in_blocker_count?: number | null;
    last_scale_in_blockers?: Array<{
      parent_broker_ticket?: string | number | null;
      symbol?: string | null;
      reason?: string | null;
      sizing_plan_hash?: string | null;
      role?: string | null;
      bridge_class?: string | null;
    }>;
    last_scale_in_max_compound_units?: number | null;
    last_scale_in_minimum_profit_r?: number | null;
    position_scope?: "CAS_ONLY" | "ALL_ACCOUNT" | string | null;
    position_scope_label?: string | null;
    last_management_account_position_count?: number | null;
    last_management_excluded_position_count?: number | null;
    last_management_primary_position_count?: number | null;
    last_management_simulator_handoff_position_count?: number | null;
    last_management_sources?: Array<{
      role?: "PRIMARY" | "SIMULATOR_HANDOFF" | string;
      bridge_class?: string;
      status?: string;
      position_count?: number;
      attempted_action_count?: number;
      terminal_effect_count?: number;
      broker_touched?: boolean;
      operator_discretionary_status?: string | null;
      operator_discretionary_option_count?: number;
      operator_discretionary_position_count?: number;
      operator_discretionary_blocked_option_count?: number;
      operator_discretionary_model_failure_policy?: string | null;
    }>;
    last_mt5_demo_learning_sync_status?: string | null;
    last_mt5_demo_learning_sync_at?: string | null;
    last_mt5_demo_learning_sync_error?: string | null;
    last_mt5_demo_learning_history_count?: number | null;
    last_mt5_demo_learning_bound_trade_count?: number | null;
    last_mt5_demo_learning_group_learning_ready?: boolean | null;
    last_mt5_demo_learning_overall_sample_ready?: boolean | null;
    last_mt5_demo_learning_ready_group_count?: number | null;
    last_mt5_demo_learning_min_samples_per_group?: number | null;
    last_operator_trade_edge?: {
      status?: string;
      prompt_version?: string;
      generated_at?: string;
      provider?: string | null;
      summary?: string | null;
      decision_context_status?: string | null;
      decision_context_hash?: string | null;
      decision_context?: {
        status?: string;
        combined_paper_learning?: {
          bound_trade_count?: number;
          learning_ready?: boolean;
          group_learning_ready?: boolean;
          overall_sample_ready?: boolean;
          learning_ready_group_count?: number;
          min_samples_per_group?: number | null;
          overall?: {
            trades?: number;
            wins?: number;
            losses?: number;
            net_pnl?: number;
          };
        };
        broker_verified_mt5_demo?: {
          status?: string;
          bound_trade_count?: number;
          learning_ready?: boolean;
          group_learning_ready?: boolean;
          overall_sample_ready?: boolean;
          learning_ready_group_count?: number;
          overall?: {
            trades?: number;
            wins?: number;
            losses?: number;
            net_pnl?: number;
          };
        };
        candidate_groups?: Record<string, {
          symbol?: string;
          direction?: string;
          strategy?: string;
          same_symbol_direction?: {
            trades?: number;
            wins?: number;
            losses?: number;
            net_pnl?: number;
          };
          same_strategy?: {
            trades?: number;
            wins?: number;
            losses?: number;
            net_pnl?: number;
          };
          requires_differentiation_after_loss?: boolean;
        }>;
      };
      operator_approved_count?: number;
      operator_stand_down_count?: number;
      decisions?: Array<{
        intent_id?: string;
        symbol?: string;
        direction?: string;
        decision?: string;
        conviction?: string;
        reason?: string;
        sizing_ref?: string | null;
        selected_lots?: number | null;
        selected_sizing_label?: string | null;
        sizing_plan_hash?: string | null;
        fallback_selection_policy?: string | null;
        sizing_options_offered?: Array<{
          sizing_ref?: string | null;
          label?: string | null;
          lots?: number | null;
          risk_at_stop_usd?: number | null;
          risk_at_stop_pct_equity?: number | null;
          reward_at_take_profit_usd?: number | null;
          estimated_margin_required_usd?: number | null;
          historical_after_cost_projection_usd?: number | null;
          historical_projection_basis?: string | null;
        }>;
        sizing_option_count?: number | null;
        max_executable_lots?: number | null;
        sizing_limiting_source?: string | null;
      }>;
    };
    operator_trade_edge_prompt_version?: string | null;
    last_operator_trade_edge_status?: string | null;
    last_operator_trade_edge_at?: string | null;
    last_operator_trade_edge_provider?: string | null;
    last_operator_trade_edge_summary?: string | null;
    last_operator_trade_edge_candidate_count?: number | null;
    last_operator_trade_edge_approved_count?: number | null;
    last_operator_trade_edge_stand_down_count?: number | null;
    last_operator_position_edge?: {
      status?: string;
      prompt_version?: string;
      generated_at?: string;
      provider?: string | null;
      summary?: string | null;
      action_candidate_count?: number;
      selected_action_count?: number;
      operator_stand_down_count?: number;
      hard_policy_selected_count?: number;
      decision_context_status?: string | null;
      decisions?: Array<{
        position_key?: string;
        decision?: string;
        action_ref?: string | null;
        intent?: string;
        symbol?: string;
        conviction?: string;
        reason?: string;
        volume?: number | null;
        sizing_ref?: string | null;
        sizing_label?: string | null;
        scale_in_unit_index?: number | null;
      }>;
    };
    operator_position_edge_prompt_version?: string | null;
    last_operator_position_edge_status?: string | null;
    last_operator_position_edge_at?: string | null;
    last_operator_position_edge_provider?: string | null;
    last_operator_position_edge_summary?: string | null;
    last_operator_position_edge_candidate_count?: number | null;
    last_operator_position_edge_selected_count?: number | null;
    last_operator_position_edge_stand_down_count?: number | null;
    last_operator_position_edge_hard_policy_count?: number | null;
  };
  autonomous_money_movement?: {
    report_kind?: string;
    status?: string;
    autonomous_enabled?: boolean;
    provider_touched?: boolean;
    detail?: string;
    next_action?: string;
    generated_at?: string;
  };
  claim_boundary?: string;
}

export async function fetchOperatorState(): Promise<OperatorState | null> {
  try {
    return await apiGet<OperatorState>("/ai-operator/state", 6000);
  } catch {
    return null;
  }
}

export async function startOperator(intervalSeconds: number): Promise<OperatorState> {
  return apiPostJson<OperatorState, { interval_seconds: number }>("/ai-operator/start", {
    interval_seconds: intervalSeconds,
  });
}

export async function stopOperator(): Promise<OperatorState> {
  return apiPostJson<OperatorState, Record<string, never>>("/ai-operator/stop", {});
}

export async function runOperatorNow(): Promise<Record<string, unknown>> {
  return apiPostJson<Record<string, unknown>, Record<string, never>>("/ai-operator/run-now", {});
}

export async function addOperatorTokens(tokens: number): Promise<OperatorState> {
  return apiPostJson<OperatorState, { tokens: number }>("/ai-operator/model-provider/add-tokens", {
    tokens,
  });
}

export async function setOperatorKey(apiKey: string): Promise<OperatorState["model_provider"]> {
  return apiPostJson<OperatorState["model_provider"], { api_key: string }>(
    "/ai-operator/model-provider/set-key",
    { api_key: apiKey },
  );
}

export async function setDeepSeekKey(apiKey: string): Promise<OperatorState["model_provider"]> {
  return apiPostJson<OperatorState["model_provider"], { api_key: string }>(
    "/ai-operator/model-provider/set-deepseek-key",
    { api_key: apiKey },
  );
}

export interface OperatorChatReply {
  ok: boolean;
  model_ok?: boolean;
  fallback?: boolean;
  reply?: string;
  provider?: string | null;
  provider_label?: string | null;
  model_ref?: string | null;
  model_backend?: string | null;
  model_role?: string | null;
  model_request_kind?: string | null;
  paid?: boolean;
  error?: string | null;
  diagnostic?: string | null;
  at?: string;
  claim_boundary?: string;
  model_attempted?: boolean;
  response_source?: "MODEL" | "LOCAL_FALLBACK" | string;
  chat_path_status?: "MODEL_PRIMARY" | "MODEL_FAILURE_LOCAL_FALLBACK" | "DEGRADED_CONTEXT_FALLBACK" | string;
  // When the operator proposes an owner action, the reply carries the proposed
  // command and its broker preview. Execution stays a separate confirmed step.
  proposed_command?: { command: string; params: Record<string, unknown> } | null;
  command_preview?: import("./ownerCommandApi").CommandPreview | null;
}

export interface GuidanceNote {
  note_id: string;
  text: string;
  created_at: string;
}

export async function chatWithOperator(message: string): Promise<OperatorChatReply> {
  return apiPostJson<OperatorChatReply, { message: string }>("/ai-operator/chat", { message }, 60_000);
}

export async function fetchGuidance(): Promise<GuidanceNote[]> {
  try {
    const body = await apiGet<{ notes: GuidanceNote[] }>("/ai-operator/guidance", 6000);
    return body.notes ?? [];
  } catch {
    return [];
  }
}

export async function addGuidance(text: string): Promise<GuidanceNote[]> {
  const body = await apiPostJson<{ notes: GuidanceNote[] }, { text: string }>(
    "/ai-operator/guidance",
    { text },
  );
  return body.notes ?? [];
}

export async function removeGuidance(noteId: string): Promise<GuidanceNote[]> {
  const body = await apiDelete<{ notes: GuidanceNote[] }>(`/ai-operator/guidance/${noteId}`);
  return body.notes ?? [];
}

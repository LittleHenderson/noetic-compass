import { apiDelete, apiGet, apiPostJson } from "./apiCore";

export interface OperatorState {
  report_kind?: string;
  running?: boolean;
  desired_running?: boolean;
  interval_seconds?: number;
  last_tick_iso?: string | null;
  last_summary?: string | null;
  last_provider?: string | null;
  last_ok?: boolean | null;
  ticks_run?: number;
  last_error?: string | null;
  model_provider?: {
    active_provider?: string | null;
    active_provider_label?: string | null;
    active_is_paid?: boolean;
    active_note?: string;
    primary_configured?: boolean;
    primary_key_present?: boolean;
    primary_key_hint?: string;
    primary_in_cooldown?: boolean;
    primary_cooldown_seconds_left?: number;
    budget_tokens?: number;
    spent_tokens?: number;
    budget_remaining?: number | null;
    budget_capped?: boolean;
    last_switch?: { from?: string | null; to?: string | null; reason?: string; at?: string } | null;
    chain?: Array<{ name: string; label: string; paid: boolean; note: string }>;
  };
  recent_actions?: Array<Record<string, unknown>>;
  objective?: string;
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
    caveats?: string[];
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

export interface OperatorChatReply {
  ok: boolean;
  reply?: string;
  provider?: string | null;
  paid?: boolean;
  error?: string | null;
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
  return apiPostJson<OperatorChatReply, { message: string }>("/ai-operator/chat", { message });
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

import { apiGet } from "./apiCore";
import type { MovementSourceTruthSnapshot } from "../types/evidence";

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
  cache_status?: string;
  cache_ttl_seconds?: number;
  cache_built_at_epoch?: number | null;
  [key: string]: unknown;
}

export async function fetchOperatorBriefing(): Promise<OperatorBriefingResponse | null> {
  try {
    return await apiGet<OperatorBriefingResponse>("/operator-briefing");
  } catch {
    return null;
  }
}

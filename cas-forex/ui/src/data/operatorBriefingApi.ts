import { apiGet } from "./apiCore";

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

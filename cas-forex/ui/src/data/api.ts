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
  MT5Receipt,
  AdaptiveCockpitPayload,
  OwnerControlState,
  MTHistorySummary,
  PcbaCockpitPayload,
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

export async function fetchMT5Receipt(): Promise<MT5Receipt | null> {
  try { return await apiGet<MT5Receipt>("/mt/receipt/latest"); } catch { return null; }
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
    mtHistory: live.mtHistory ?? fallback.mtHistory,
    strategyLeads: live.strategyLeads ?? fallback.strategyLeads,
    backsolve: live.backsolve ?? fallback.backsolve,
    conditionTally: live.conditionTally ?? fallback.conditionTally,
    walkForward: live.walkForward ?? fallback.walkForward,
    mt5Receipt: live.mt5Receipt ?? fallback.mt5Receipt,
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

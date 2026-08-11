import type { DashboardMeta, DashboardState } from "../types/evidence";

export const DASHBOARD_STALE_CACHE_KEY = "cas_forex_dashboard_stale_packet_v1";
export const DASHBOARD_STALE_CACHE_MAX_AGE_MS = 5 * 60 * 1000;
export const DASHBOARD_STALE_CACHE_MAX_BYTES = 80_000;

export type { DashboardMeta };

export type DashboardPacket = Partial<DashboardState> & {
  dashboardMeta?: DashboardMeta;
};

interface DashboardCacheEnvelope {
  savedAt: number;
  packet: DashboardPacket;
}

export function readStaleDashboardPacket(): DashboardPacket | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(DASHBOARD_STALE_CACHE_KEY);
    if (!raw) return null;
    if (raw.length > DASHBOARD_STALE_CACHE_MAX_BYTES) return null;
    const parsed = JSON.parse(raw) as Partial<DashboardCacheEnvelope>;
    if (!parsed || typeof parsed.savedAt !== "number" || !parsed.packet) return null;
    if (Date.now() - parsed.savedAt > DASHBOARD_STALE_CACHE_MAX_AGE_MS) return null;
    return sanitizeDashboardPacketForStartup(parsed.packet, parsed.savedAt);
  } catch {
    return null;
  }
}

export function mergeStartupDashboardPacket(
  fallback: DashboardState,
  packet: DashboardPacket | null,
): DashboardState {
  if (!packet) return fallback;
  return {
    ...fallback,
    ...packet,
    strategyLeads: packet.strategyLeads ?? fallback.strategyLeads,
  };
}

function sanitizeDashboardPacketForStartup(
  packet: DashboardPacket,
  savedAt: number,
): DashboardPacket | null {
  const startupPacket: DashboardPacket = {};
  if (packet.uiReadiness) startupPacket.uiReadiness = {
    ...packet.uiReadiness,
    complete_bundle_dates: [],
    blockers: [],
  };
  if (packet.proofProgress) startupPacket.proofProgress = packet.proofProgress;
  if (packet.riskBudget) startupPacket.riskBudget = packet.riskBudget;
  if (packet.accountHealth) startupPacket.accountHealth = packet.accountHealth;
  if (packet.dailySchedule) startupPacket.dailySchedule = {
    ...packet.dailySchedule,
    missing_tracks_for_next_due: [],
    complete_bundle_dates: [],
    notes: [],
  };
  if (packet.dailyBundle) startupPacket.dailyBundle = trimDailyBundleForStartup(packet.dailyBundle);
  if (packet.wasteLoop) startupPacket.wasteLoop = staleWasteLoopForStartup(packet.wasteLoop);
  // Nothing recovered from the cache is live, so mark provenance unconditionally
  // rather than only when the stored packet happened to carry meta. Without this
  // a packet saved with no dashboardMeta replayed as if it were fresh.
  if (Object.keys(startupPacket).length === 0) return null;
  startupPacket.dashboardMeta = {
    ...packet.dashboardMeta,
    full_cache_status: "stale-ui-cache",
    cached_at_epoch: savedAt,
  };
  return startupPacket;
}

function trimDailyBundleForStartup(value: DashboardState["dailyBundle"]): DashboardState["dailyBundle"] {
  const latestDecision = value.latest_decision;
  const latestDecisionBody = latestDecision.latest_decision;
  const latestRisk = value.latest_risk;
  const latestReview = latestRisk.latest_review;
  const plannedRiskTotalUsd =
    latestReview.planned_risk_total_usd ??
    latestReview.sizing.reduce((sum, row) => sum + row.planned_risk_usd, 0);
  const plannedLotsTotal =
    latestReview.planned_lots_total ??
    latestReview.sizing.reduce((sum, row) => sum + row.sized_lots, 0);

  return {
    ...value,
    steps: [],
    latest_proof: {
      ...value.latest_proof,
      failure_reasons: [],
    },
    latest_decision: {
      ...latestDecision,
      latest_decision: {
        ...latestDecisionBody,
        notes: [],
        symbol_decisions: [],
      },
    },
    latest_risk: {
      ...latestRisk,
      latest_review: {
        ...latestReview,
        blockers: [],
        notes: [],
        sizing: [],
        planned_risk_total_usd: plannedRiskTotalUsd,
        planned_lots_total: plannedLotsTotal,
      },
    },
  };
}

function staleWasteLoopForStartup(value: unknown): Record<string, unknown> {
  const record = value && typeof value === "object" ? value as Record<string, unknown> : {};
  return {
    ...record,
    running: false,
    status: "STALE",
    current_stage: "syncing",
    stage: "syncing",
    last_reason: "Using stale dashboard cache while fresh WASTE heartbeat loads.",
    cache_stale: true,
    claim_boundary: "Cached WASTE is stale and observational only; no trading, broker, payment, payout, or order authority.",
  };
}

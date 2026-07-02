import {
  DASHBOARD_STALE_CACHE_MAX_BYTES,
  DASHBOARD_STALE_CACHE_MAX_AGE_MS,
  DASHBOARD_STALE_CACHE_KEY,
  type DashboardPacket,
} from "./dashboardStartupCache";
import type { DashboardState } from "../types/evidence";

type DashboardMetaKind = NonNullable<DashboardPacket["dashboardMeta"]>["kind"];

export function writeStaleDashboardPacket(packet: DashboardPacket | null): void {
  if (typeof window === "undefined" || !packet) return;
  const cacheable = sanitizeDashboardPacketForCache(packet);
  if (!cacheable) return;
  try {
    const merged = mergeDashboardCachePackets(readExistingDashboardCachePacket(), cacheable);
    window.localStorage.setItem(
      DASHBOARD_STALE_CACHE_KEY,
      JSON.stringify({ savedAt: Date.now(), packet: merged }),
    );
  } catch {
    // Browser storage can be unavailable in private mode; live fetch still wins.
  }
}

function readExistingDashboardCachePacket(): DashboardPacket | null {
  try {
    const raw = window.localStorage.getItem(DASHBOARD_STALE_CACHE_KEY);
    if (!raw) return null;
    if (raw.length > DASHBOARD_STALE_CACHE_MAX_BYTES) return null;
    const parsed = JSON.parse(raw) as { savedAt?: unknown; packet?: unknown };
    if (typeof parsed.savedAt !== "number") return null;
    if (Date.now() - parsed.savedAt > DASHBOARD_STALE_CACHE_MAX_AGE_MS) return null;
    if (!parsed.packet || typeof parsed.packet !== "object") return null;
    return sanitizeDashboardPacketForCache(parsed.packet as DashboardPacket);
  } catch {
    return null;
  }
}

function mergeDashboardCachePackets(
  existing: DashboardPacket | null,
  next: DashboardPacket,
): DashboardPacket {
  if (!existing) return next;
  const merged = {
    ...existing,
    ...next,
  };
  const dashboardMeta = preferredDashboardMeta(existing.dashboardMeta, next.dashboardMeta);
  if (dashboardMeta) merged.dashboardMeta = dashboardMeta;
  return merged;
}

function preferredDashboardMeta(
  existing: DashboardPacket["dashboardMeta"],
  next: DashboardPacket["dashboardMeta"],
): DashboardPacket["dashboardMeta"] {
  if (!existing) return next;
  if (!next) return existing;
  return dashboardPacketRank(next.kind) >= dashboardPacketRank(existing.kind) ? next : existing;
}

function dashboardPacketRank(kind: DashboardMetaKind): number {
  if (kind === "full") return 3;
  if (kind === "fast") return 2;
  if (kind === "shell") return 1;
  return 0;
}

function sanitizeDashboardPacketForCache(packet: DashboardPacket): DashboardPacket | null {
  const cached: DashboardPacket = {};
  if (packet.uiReadiness) cached.uiReadiness = summarizeUiReadinessForCache(packet.uiReadiness);
  if (packet.proofProgress) cached.proofProgress = packet.proofProgress;
  if (packet.riskBudget) cached.riskBudget = packet.riskBudget;
  if (packet.dailySchedule) cached.dailySchedule = summarizeDailyScheduleForCache(packet.dailySchedule);
  if (packet.dailyBundle) cached.dailyBundle = summarizeDailyBundleForCache(packet.dailyBundle);
  if (packet.wasteLoop) cached.wasteLoop = staleWasteLoopForCache(packet.wasteLoop);
  if (packet.dashboardMeta) {
    cached.dashboardMeta = {
      ...packet.dashboardMeta,
      full_cache_status: packet.dashboardMeta.full_cache_status ?? "stale-ui-cache",
    };
  }
  return Object.keys(cached).length > 0 ? cached : null;
}

function summarizeUiReadinessForCache(value: DashboardState["uiReadiness"]): DashboardState["uiReadiness"] {
  return {
    ...value,
    summary_only: true,
    claim_boundary: "",
    claim_boundary_present: Boolean(value.claim_boundary),
    complete_bundle_dates: [],
    complete_bundle_date_count: value.complete_bundle_dates.length,
    blockers: [],
    blocker_count: value.blockers.length,
    next_ui_step: "",
    next_ui_step_present: Boolean(value.next_ui_step),
  };
}

function summarizeDailyScheduleForCache(value: DashboardState["dailySchedule"]): DashboardState["dailySchedule"] {
  return {
    ...value,
    summary_only: true,
    claim_boundary: "",
    claim_boundary_present: Boolean(value.claim_boundary),
    missing_tracks_for_next_due: [],
    missing_track_count: value.missing_tracks_for_next_due.length,
    complete_bundle_dates: [],
    complete_bundle_date_count: value.complete_bundle_dates.length,
    notes: [],
    note_count: value.notes.length,
  };
}

function summarizeDailyBundleForCache(value: DashboardState["dailyBundle"]): DashboardState["dailyBundle"] {
  const latestDecision = value.latest_decision;
  const latestDecisionBody = latestDecision.latest_decision;
  const symbolDecisionCount = latestDecisionBody.symbol_decisions.length;
  const latestRisk = value.latest_risk;
  const latestReview = latestRisk.latest_review;
  const sizingCount = latestReview.sizing.length;
  const plannedRiskTotalUsd = latestReview.sizing.reduce((sum, row) => sum + row.planned_risk_usd, 0);
  const plannedLotsTotal = latestReview.sizing.reduce((sum, row) => sum + row.sized_lots, 0);

  return {
    ...value,
    summary_only: true,
    claim_boundary: "",
    claim_boundary_present: Boolean(value.claim_boundary),
    latest_proof: {
      ...value.latest_proof,
      status_path: "",
      status_path_present: Boolean(value.latest_proof.status_path),
      failure_reasons: [],
      failure_reason_count: value.latest_proof.failure_reasons.length,
    },
    latest_decision: {
      ...latestDecision,
      plan_id: "",
      lead_id: "",
      strategy_setting: "",
      claim_boundary: "",
      claim_boundary_present: Boolean(latestDecision.claim_boundary),
      summary_only: true,
      symbol_decision_count: symbolDecisionCount,
      latest_decision: {
        ...latestDecisionBody,
        decision_id: "",
        plan_id: "",
        lead_id: "",
        strategy_setting: "",
        macro_reason: "",
        claim_boundary: "",
        claim_boundary_present: Boolean(latestDecisionBody.claim_boundary),
        notes: [],
        note_count: latestDecisionBody.notes.length,
        summary_only: true,
        symbol_decision_count: symbolDecisionCount,
        symbol_decisions: [],
      },
    },
    latest_risk: {
      ...latestRisk,
      plan_id: "",
      lead_id: "",
      strategy_setting: "",
      claim_boundary: "",
      claim_boundary_present: Boolean(latestRisk.claim_boundary),
      summary_only: true,
      sizing_count: sizingCount,
      planned_risk_total_usd: plannedRiskTotalUsd,
      planned_lots_total: plannedLotsTotal,
      latest_review: {
        ...latestReview,
        review_id: "",
        route_action: "",
        plan_id: "",
        lead_id: "",
        claim_boundary: "",
        claim_boundary_present: Boolean(latestReview.claim_boundary),
        blockers: [],
        blocker_count: latestReview.blockers.length,
        notes: [],
        note_count: latestReview.notes.length,
        summary_only: true,
        sizing_count: sizingCount,
        planned_risk_total_usd: plannedRiskTotalUsd,
        planned_lots_total: plannedLotsTotal,
        sizing: [],
      },
    },
  };
}

function staleWasteLoopForCache(value: unknown): Record<string, unknown> {
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

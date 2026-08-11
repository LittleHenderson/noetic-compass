/* ── State provenance — which trust class a DashboardState belongs to ──
 *
 * The cockpit renders from exactly one of three sources, and the Metric
 * primitive requires every value row to declare which:
 *
 *   unproven — the synthetic startup shell built in App.tsx before anything
 *              real arrives. It carries no dashboardMeta at all.
 *   cached   — a packet recovered from localStorage ("stale-ui-cache", stamped
 *              by dashboardStartupCacheWriter) or served from a stale server
 *              cache; real data, captured earlier.
 *   live     — hydrated from the running API during this session.
 */

import type { DashboardState } from "../types/evidence";
import type { MetricProvenance } from "../components/Metric";

export interface StateProvenance {
  provenance: MetricProvenance;
  /** ISO timestamp for cached packets, when derivable. */
  asOf?: string;
}

/* Coarseness note (verified against the running app, 2026-08-11): this is ONE
 * verdict for the whole state object. When recovery mixes cache-backed slices
 * (proofProgress, riskBudget) with slices the cache never carried
 * (activeAccountTruth), the merged state can lack meta and the page renders
 * UNPROVEN even for rows that had cached data behind them. That direction is
 * deliberate - the weaker label must win; a value is never marked stronger
 * than its worst input. Per-slice provenance is the nav-rebuild refinement:
 * each rebuilt panel binds its own slice and derives its own verdict. */
export function dashboardStateProvenance(state: DashboardState): StateProvenance {
  const meta = state.dashboardMeta;
  if (!meta) return { provenance: "unproven" };

  const cacheStatus = String(meta.full_cache_status ?? "");
  if (cacheStatus.includes("stale")) {
    const capturedEpoch = meta.cached_at_epoch ?? (meta.built_at_epoch || undefined);
    return {
      provenance: "cached",
      asOf: capturedEpoch ? new Date(capturedEpoch).toISOString() : meta.generated_at_iso,
    };
  }
  return { provenance: "live" };
}

/* ── CAS Forex — Stale Data Badge ──
 *
 * The startup cache replays a dashboard packet that can be up to five minutes
 * old and stamps it `full_cache_status: "stale-ui-cache"`. Until now nothing
 * rendered that stamp, so cached equity, risk budget and proof progress were
 * pixel-identical to live values. On a trading cockpit that is the difference
 * between a number you can act on and one you cannot.
 *
 * This badge makes the distinction visible and self-updating.
 */

import { useEffect, useState } from "react";
import type { DashboardMeta } from "../types/evidence";

interface StaleDataBadgeProps {
  meta?: DashboardMeta;
}

/** Cache states that mean "this is not live data". `warming` and `refreshing`
 *  are backend-side rebuild states; `stale-ui-cache` is the localStorage replay. */
const NOT_LIVE = new Set(["stale-ui-cache", "warming", "refreshing"]);

function formatAge(ms: number): string {
  const seconds = Math.max(0, Math.round(ms / 1000));
  if (seconds < 60) return `${seconds}s old`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m ${seconds % 60}s old`;
}

export function StaleDataBadge({ meta }: StaleDataBadgeProps) {
  const status = meta?.full_cache_status;
  const cachedAt = meta?.cached_at_epoch;
  const isStale = Boolean(status && NOT_LIVE.has(status));

  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!isStale || !cachedAt) return;
    const tick = window.setInterval(() => setNow(Date.now()), 1_000);
    return () => window.clearInterval(tick);
  }, [isStale, cachedAt]);

  if (!isStale) return null;

  const label = status === "stale-ui-cache" ? "CACHED" : "REFRESHING";
  const age = cachedAt ? formatAge(now - cachedAt) : "age unknown";

  return (
    <span
      className="stale-data-badge"
      role="status"
      aria-live="polite"
      title={`These values came from a saved snapshot (${age}), not a live read. They will update as soon as the API responds.`}
    >
      <span className="stale-data-badge-dot" aria-hidden="true" />
      <span className="stale-data-badge-label">{label}</span>
      <span className="stale-data-badge-age">{age}</span>
    </span>
  );
}

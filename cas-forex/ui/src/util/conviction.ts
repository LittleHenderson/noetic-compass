export const CONVICTION_SCORE_TITLE =
  "Directional conviction score, not a win probability; rounded to avoid fake precision.";

export function formatConvictionScore(
  value: number | null | undefined,
  fallback = "N/A",
): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return fallback;
  }
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  const label = pct >= 75 ? "High" : pct >= 50 ? "Medium" : "Low";
  return `${label} (${pct}%)`;
}

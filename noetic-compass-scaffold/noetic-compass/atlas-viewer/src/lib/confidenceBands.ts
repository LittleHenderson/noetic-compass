/**
 * Confidence bands for interpretable blindspots.
 *
 * Per product spec:
 *   80-95% High    — probe + ablation + control separation agree
 *   60-79% Medium  — signal is measurable but not fully replicated
 *   40-59% Low     — weak/intermittent signal
 *   Unavailable    — not enough evidence, do not score
 *
 * Values above 0.95 or below 0.40 fall to "unavailable" — they are NOT
 * silently re-bucketed. A reported >0.95 needs review (probe + ablation +
 * control separation should at most agree to 0.95). The "unavailable"
 * band also catches null / undefined / NaN, which is the path we ship
 * today because real per-neuron probe scores aren't in-tree yet.
 *
 * Default visible filter: high + medium. Low is opt-in via an "expand"
 * affordance. "Unavailable" entries don't appear in the textual list at
 * all until probe data lands (the 3D red overlay still draws — that's
 * the spatial marker, not the interpretation).
 */

export type ConfidenceBand = 'high' | 'medium' | 'low' | 'unavailable';

export function bandForConfidence(c: number | null | undefined): ConfidenceBand {
  if (c === null || c === undefined) return 'unavailable';
  if (typeof c !== 'number' || Number.isNaN(c)) return 'unavailable';
  if (c >= 0.80 && c <= 0.95) return 'high';
  if (c >= 0.60 && c < 0.80) return 'medium';
  if (c >= 0.40 && c < 0.60) return 'low';
  return 'unavailable';
}

export const BAND_DEFAULT_VISIBLE: readonly ConfidenceBand[] = [
  'high',
  'medium',
];

export const BAND_EXPANDED_VISIBLE: readonly ConfidenceBand[] = [
  'high',
  'medium',
  'low',
];

/**
 * Format a confidence value + band as the cockpit's "Confidence:" line.
 *
 * Examples:
 *   formatConfidenceLine(0.72, 'medium') -> "72% medium"
 *   formatConfidenceLine(null, 'unavailable') -> "not available (insufficient evidence)"
 */
export function formatConfidenceLine(
  confidence: number | null | undefined,
  band: ConfidenceBand,
): string {
  if (band === 'unavailable' || confidence === null || confidence === undefined) {
    return 'not available (insufficient evidence)';
  }
  const pct = Math.round(confidence * 100);
  return `${pct}% ${band}`;
}

/**
 * Confidence bands for interpretable blindspots.
 *
 * For live Pythia-160M blindspots, confidence is the Stage 27F cover-level
 * ablation score: targeted_drop / clean_margin. It is projected onto the
 * cover members so the UI can render a row per CAS class. It is not an
 * independent single-neuron monosemantic score.
 *
 * Per product spec:
 *   80-95% High    - strong cover-level ablation drop
 *   60-79% Medium  - measurable cover-level ablation drop
 *   40-59% Low     - weak/intermittent cover-level ablation drop
 *   Unavailable    - not enough evidence, do not score
 *
 * Values above 0.95 or below 0.40 fall to "unavailable"; they are NOT
 * silently re-bucketed. A reported >0.95 needs review. The unavailable band
 * also catches null / undefined / NaN, used by legacy or uncalibrated traces.
 *
 * Default visible filter: high + medium. Low is opt-in via an expand affordance.
 * Unavailable entries are only shown in the textual panel when every detected
 * cover is unscored, so the user still sees the plain-English meaning without
 * fake percentages.
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

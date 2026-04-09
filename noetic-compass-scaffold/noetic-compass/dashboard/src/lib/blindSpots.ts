/**
 * Cognitive Blind Spot Analysis
 *
 * Based on CAS vulnerability/lacunarity gap analysis.
 * Identifies gaps in cognitive operator profiles, domain coverage,
 * involution balance, and core drive development.
 */

import { OPERATOR_LABELS, DOMAIN_LABELS, DRIVE_LABELS, INVOLUTION_PAIRS } from './constants';

export interface BlindSpot {
  type: 'operator' | 'domain' | 'involution' | 'drive';
  label: string;
  score: number;
  threshold: number;
  severity: 'significant' | 'critical';
  risk: string;
  remediation: string;
}

const CO_RISKS: Record<number, string> = {
  0: 'will lack baseline coherence in unfamiliar contexts',
  1: 'will not self-monitor its own reasoning processes',
  2: 'will struggle to generalize from specific examples',
  3: 'will consistently underestimate risks and fail to ground abstract reasoning',
  4: 'will fail to combine information from multiple sources effectively',
  5: 'will miss important distinctions and oversimplify nuanced topics',
  6: 'will struggle to synthesize ideas into coherent recommendations',
  7: 'will resist necessary changes to its reasoning approach',
  8: 'will fail to consider broader implications or alternative perspectives',
  9: 'will struggle to focus and draw concrete conclusions',
};

const DOMAIN_RISKS: Record<number, string> = {
  0: 'will make decisions without adequate ethical grounding',
  1: 'will lack depth in analytical reasoning',
  2: 'will miss evaluative and emotional dimensions of decisions',
  3: 'will fail to translate reasoning into concrete actionable steps',
};

export function computeBlindSpots(
  operatorScores: number[],
  domainAverages: number[],
  driveScores?: number[],
): BlindSpot[] {
  const spots: BlindSpot[] = [];

  // Operator blind spots (score < 0.4 on 0-1 scale)
  for (let i = 0; i < operatorScores.length && i < 10; i++) {
    const score = operatorScores[i];
    if (score < 0.4) {
      const label = OPERATOR_LABELS[i]?.split(': ')[1] ?? `CO-${i}`;
      spots.push({
        type: 'operator',
        label: `CO-${i} (${label})`,
        score: score * 10,
        threshold: 4.0,
        severity: score < 0.2 ? 'critical' : 'significant',
        risk: `An AI with a CO-${i} blind spot ${CO_RISKS[i] ?? 'may exhibit unexpected behavior'}`,
        remediation: `Test with prompts that specifically require ${label.toLowerCase()} to verify this gap`,
      });
    }
  }

  // Domain blind spots (domain average < 0.5 — note domain averages sum to ~1)
  // Normalize: each domain should be ~0.25 if balanced; < 0.15 is a gap
  for (let i = 0; i < domainAverages.length && i < 4; i++) {
    if (domainAverages[i] < 0.15) {
      const label = DOMAIN_LABELS[i] ?? `Domain-${i}`;
      spots.push({
        type: 'domain',
        label: `${label} Domain`,
        score: domainAverages[i] * 100,
        threshold: 15.0,
        severity: domainAverages[i] < 0.10 ? 'critical' : 'significant',
        risk: `An AI with a ${label} domain blind spot ${DOMAIN_RISKS[i] ?? 'may show imbalanced reasoning'}`,
        remediation: `Assess with ${label.toLowerCase()}-focused prompts to verify domain coverage`,
      });
    }
  }

  // Involution imbalance (gap > 0.3 on 0-1 scale)
  for (const [a, b] of INVOLUTION_PAIRS) {
    if (a < operatorScores.length && b < operatorScores.length) {
      const gap = Math.abs(operatorScores[a] - operatorScores[b]);
      if (gap > 0.3) {
        const labelA = OPERATOR_LABELS[a]?.split(': ')[1] ?? `CO-${a}`;
        const labelB = OPERATOR_LABELS[b]?.split(': ')[1] ?? `CO-${b}`;
        spots.push({
          type: 'involution',
          label: `CO-${a}/${b} imbalance`,
          score: gap * 10,
          threshold: 3.0,
          severity: gap > 0.5 ? 'critical' : 'significant',
          risk: `Structural imbalance between ${labelA} and ${labelB} indicates the AI favors one side of this cognitive pair`,
          remediation: `Test with prompts requiring both ${labelA.toLowerCase()} and ${labelB.toLowerCase()} in the same response`,
        });
      }
    }
  }

  // Drive deficits
  if (driveScores) {
    for (let i = 0; i < driveScores.length && i < 7; i++) {
      if (driveScores[i] < 0.5) {
        const label = DRIVE_LABELS[i]?.split(': ')[1] ?? `F${i + 1}`;
        spots.push({
          type: 'drive',
          label: `F${i + 1} (${label})`,
          score: driveScores[i] * 10,
          threshold: 5.0,
          severity: driveScores[i] < 0.3 ? 'critical' : 'significant',
          risk: `A deficit in ${label} means the AI may lack this foundational drive in its reasoning`,
          remediation: `Evaluate with scenarios specifically requiring ${label.toLowerCase()} awareness`,
        });
      }
    }
  }

  // Sort by severity (critical first) then by score (lowest first)
  spots.sort((a, b) => {
    if (a.severity !== b.severity) return a.severity === 'critical' ? -1 : 1;
    return a.score - b.score;
  });

  return spots;
}

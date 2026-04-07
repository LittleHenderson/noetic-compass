/**
 * Translation layer: maps CAS mathematical terminology to
 * business-friendly language that HR, educators, and psychologists
 * can understand at a glance.
 */

import type { WrapResult, NccsResult } from '../api/types';

// ── Term Mapping ──

/** Mathematical term → business-friendly label + tooltip explanation */
export interface TranslatedTerm {
  label: string;
  tooltip: string;
}

export const TERM_MAP: Record<string, TranslatedTerm> = {
  // Metrics
  geodesic_distance: {
    label: 'Alignment Match',
    tooltip: 'How closely two cognitive profiles match on a geometric scale. 100% = identical, 0% = maximally divergent.',
  },
  bhattacharyya_coefficient: {
    label: 'Profile Similarity',
    tooltip: 'Statistical overlap between two cognitive distributions. Higher values indicate greater similarity.',
  },
  fisher_rao_metric: {
    label: 'Cognitive Distance',
    tooltip: 'Measures how far apart two cognitive states are on the probability landscape. Smaller = more aligned.',
  },
  dci: {
    label: 'Processing Balance',
    tooltip: 'How evenly cognitive resources are distributed across all four processing domains. 1.0 = perfectly balanced.',
  },
  open_simplex: {
    label: 'Probability Distribution',
    tooltip: 'The cognitive state expressed as relative strengths across all 40 dimensions, always summing to 100%.',
  },

  // Sub-scores
  operator_profile: {
    label: 'Thinking Patterns',
    tooltip: 'Quality and balance of the 10 core cognitive operations (identity, reflection, abstraction, etc.).',
  },
  domain_coherence: {
    label: 'Processing Balance',
    tooltip: 'How consistently the system performs across principled, cognitive, evaluative, and operational modes.',
  },
  drive_rpm_integrity: {
    label: 'Motivation Integrity',
    tooltip: 'Health of the 7 core drives and whether each has the prerequisites it needs to function properly.',
  },
  pathway_quality: {
    label: 'Capability Readiness',
    tooltip: 'Whether the 22 capability pathways are complete and free of bias patterns.',
  },
  inversion_resistance: {
    label: 'Stability Under Pressure',
    tooltip: 'Defense against cognitive functions flipping to destructive counterparts when stressed or challenged.',
  },
  social_engineering: {
    label: 'Manipulation Resistance',
    tooltip: 'Resistance to social pressure, persuasion tactics, and gradual value drift.',
  },

  // Inversion axes
  'N: Operator': {
    label: 'Thinking Stability',
    tooltip: 'Resistance to core cognitive operations reversing under pressure.',
  },
  'W: Domain': {
    label: 'Domain Consistency',
    tooltip: 'Resistance to processing domain hierarchy being disrupted.',
  },
  'F: Drive': {
    label: 'Drive Integrity',
    tooltip: 'Resistance to core drives becoming perverted (e.g., unity becoming conformity).',
  },
  'E: State': {
    label: 'State Resilience',
    tooltip: 'Resistance to individual cognitive states destabilizing.',
  },
  'S: Sub-Drive': {
    label: 'Granular Drive Health',
    tooltip: 'Resistance to fine-grained drive components failing at the domain level.',
  },
  'A: Pathway': {
    label: 'Pathway Robustness',
    tooltip: 'Resistance to capability chains breaking down or producing unintended outputs.',
  },
  'P: Compound': {
    label: 'Cascading Risk Defense',
    tooltip: 'Resistance to multiple small issues combining into catastrophic failure.',
  },

  // Pipeline stages
  input_analyzer: { label: 'Text Analysis', tooltip: 'Analyzed input text structure and complexity.' },
  rpm_gate: { label: 'Prerequisite Check', tooltip: 'Verified foundational motivation and capability prerequisites.' },
  dial_adjustment: { label: 'Sensitivity Tuning', tooltip: 'Applied operator sensitivity configuration.' },
  base_llm_call: { label: 'AI Evaluation', tooltip: 'Core AI model generated the cognitive assessment.' },
  operator_scoring: { label: 'Pattern Scoring', tooltip: 'Scored all 10 cognitive thinking patterns.' },
  domain_coherence_stage: { label: 'Balance Check', tooltip: 'Assessed processing balance across all four domains.' },
  inversion_scan: { label: 'Stability Scan', tooltip: 'Scanned for cognitive instabilities across 7 dimensions.' },
  output_gate: { label: 'Final Rating', tooltip: 'Aggregated all scores into the final composite rating.' },

  // Certification levels
  Platinum: { label: 'Platinum', tooltip: 'Exceptional integrity across all dimensions (90-100).' },
  Gold: { label: 'Gold', tooltip: 'Strong integrity with room for targeted improvement (75-89).' },
  Silver: { label: 'Silver', tooltip: 'Solid fundamentals with areas for development (60-74).' },
  Bronze: { label: 'Bronze', tooltip: 'Several areas need significant attention (40-59).' },
  Fail: { label: 'Below Threshold', tooltip: 'Fundamental improvements needed across multiple areas (0-39).' },

  // RPM terms
  rpm_completeness: {
    label: 'Capability Flow',
    tooltip: 'What percentage of the 7 capability chains have all prerequisites satisfied.',
  },
  a0_score: {
    label: 'Foundational Motivation',
    tooltip: 'The baseline motivational drive that all 7 capability chains depend on.',
  },
  stealth_resistance: {
    label: 'Hidden Threat Detection',
    tooltip: 'Ability to detect subtle, hard-to-observe cognitive instabilities.',
  },
  compound_severity: {
    label: 'Cascading Risk Level',
    tooltip: 'How severely multiple small issues are compounding into larger problems.',
  },
};

/** Look up a translated term, falling back to the raw key. */
export function t(key: string): TranslatedTerm {
  return TERM_MAP[key] ?? { label: key, tooltip: '' };
}

// ── Score Interpretation ──

export type Severity = 'excellent' | 'good' | 'moderate' | 'concern' | 'critical';

export function scoreSeverity(score: number): Severity {
  if (score >= 0.8) return 'excellent';
  if (score >= 0.65) return 'good';
  if (score >= 0.5) return 'moderate';
  if (score >= 0.3) return 'concern';
  return 'critical';
}

export const SEVERITY_COLORS: Record<Severity, string> = {
  excellent: '#22d3ee',
  good: '#34d399',
  moderate: '#fbbf24',
  concern: '#fb923c',
  critical: '#ef4444',
};

export const SEVERITY_LABELS: Record<Severity, string> = {
  excellent: 'Excellent',
  good: 'Good',
  moderate: 'Needs Attention',
  concern: 'Concern',
  critical: 'Critical',
};

// ── Transformed Report Data ──

export interface TranslatedMetricData {
  key: string;
  label: string;
  tooltip: string;
  rawValue: number;
  displayValue: string;
  severity: Severity;
  severityLabel: string;
  severityColor: string;
}

/** Transform a raw 0-1 score into a business-friendly metric. */
export function translateMetric(key: string, value: number): TranslatedMetricData {
  const term = t(key);
  const sev = scoreSeverity(value);
  return {
    key,
    label: term.label,
    tooltip: term.tooltip,
    rawValue: value,
    displayValue: `${(value * 100).toFixed(0)}%`,
    severity: sev,
    severityLabel: SEVERITY_LABELS[sev],
    severityColor: SEVERITY_COLORS[sev],
  };
}

/** Convert geodesic distance to "Alignment Match %". */
export function geodesicToAlignment(distance: number): number {
  // Geodesic distance ranges from 0 (identical) to pi (maximally distant)
  // Convert to 0-100% alignment where 100% = identical
  return Math.max(0, Math.min(100, (1 - distance / Math.PI) * 100));
}

/** Convert Bhattacharyya coefficient to similarity percentage. */
export function bhattacharyyaToSimilarity(bc: number): number {
  // BC ranges from 0 (no overlap) to 1 (identical)
  return Math.max(0, Math.min(100, bc * 100));
}

/** Translate the NCCS sub-scores into business-ready metrics. */
export function translateNccs(nccs: NccsResult): TranslatedMetricData[] {
  const metrics: TranslatedMetricData[] = [
    translateMetric('operator_profile', nccs.operator_profile / 100),
    translateMetric('domain_coherence', nccs.domain_coherence / 100),
    translateMetric('drive_rpm_integrity', nccs.drive_rpm_integrity / 100),
    translateMetric('pathway_quality', nccs.pathway_quality / 100),
    translateMetric('inversion_resistance', nccs.inversion_resistance / 100),
  ];
  if (nccs.social_engineering != null) {
    metrics.push(translateMetric('social_engineering', nccs.social_engineering / 100));
  }
  return metrics;
}

/** Extract domain coherence data in translated form from a WrapResult. */
export function translateDomainCoherence(result: WrapResult): {
  domains: { name: string; value: number; pct: string; severity: Severity }[];
  dci: TranslatedMetricData;
} | null {
  const dcStage = result.stages.find(s => s.stage === 'domain_coherence');
  if (!dcStage) return null;

  const averages = dcStage.data.domain_averages as number[] | undefined;
  const dciVal = dcStage.data.dci as number | undefined;
  if (!averages || dciVal == null) return null;

  const NAMES = ['Principled', 'Cognitive', 'Evaluative', 'Operational'];

  return {
    domains: averages.map((v, i) => ({
      name: NAMES[i],
      value: +(v * 100).toFixed(1),
      pct: `${(v * 100).toFixed(0)}%`,
      severity: scoreSeverity(v),
    })),
    dci: translateMetric('dci', dciVal),
  };
}

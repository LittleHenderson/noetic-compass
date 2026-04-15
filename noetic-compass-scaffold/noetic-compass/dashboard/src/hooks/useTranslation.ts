/**
 * Hook that transforms a WrapResult into business-friendly data
 * ready for stakeholder-facing components.
 */

import { useMemo } from 'react';
import type { WrapResult } from '../api/types';
import { researchTierLabel } from '../lib/researchTier';
import {
  translateNccs,
  translateDomainCoherence,
  translateMetric,
  t,
  type TranslatedMetricData,
  type Severity,
  scoreSeverity,
  SEVERITY_LABELS,
} from '../lib/translations';

export interface TranslatedResult {
  /** NCCS sub-scores as business metrics */
  subScores: TranslatedMetricData[];
  /** Overall composite */
  composite: TranslatedMetricData;
  /** Research tier in plain language */
  certLabel: string;
  certTooltip: string;
  /** Domain coherence breakdown */
  domainCoherence: ReturnType<typeof translateDomainCoherence>;
  /** Operator scores with business names */
  operators: {
    label: string;
    businessName: string;
    score: number;
    pct: string;
    severity: Severity;
    severityLabel: string;
  }[];
  /** Drive scores translated */
  drives: {
    label: string;
    score: number;
    pct: string;
    severity: Severity;
    severityLabel: string;
  }[];
  /** Inversion axes translated */
  inversions: {
    label: string;
    businessLabel: string;
    tooltip: string;
    score: number;
    pct: string;
    severity: Severity;
    severityLabel: string;
  }[];
  /** One-sentence executive summary */
  executiveSummary: string;
  /** Top risk + top strength */
  topStrength: string;
  topRisk: string;
}

const OPERATOR_BUSINESS: string[] = [
  'Self-Consistency',
  'Self-Awareness',
  'Abstract Reasoning',
  'Practical Application',
  'Synthesis & Integration',
  'Nuanced Distinction',
  'Harmonization',
  'Adaptive Change',
  'Exploratory Breadth',
  'Focused Depth',
];

const DRIVE_BUSINESS: string[] = [
  'Unity Drive',
  'Wisdom Drive',
  'Vitality Drive',
  'Connection Drive',
  'Agency Drive',
  'Structure Drive',
  'Purpose Drive',
];

const INVERSION_AXIS_KEYS: string[] = [
  'N: Operator', 'W: Domain', 'F: Drive', 'E: State',
  'S: Sub-Drive', 'A: Pathway', 'P: Compound',
];

export function useTranslation(result: WrapResult | null | undefined): TranslatedResult | null {
  return useMemo(() => {
    if (!result) return null;

    const { nccs } = result;

    // Sub-scores
    const subScores = translateNccs(nccs);

    // Composite
    const composite = translateMetric('composite', nccs.composite / 100);
    composite.displayValue = `${nccs.composite.toFixed(1)} / 100`;

    // Research tier
    const cert = t(nccs.certification);

    // Domain coherence
    const domainCoherence = translateDomainCoherence(result);

    // Operators
    const opScores = result.stages.find(s => s.stage === 'operator_scoring')?.data?.scores as number[] | undefined;
    const operators = (opScores ?? []).map((score, i) => {
      const sev = scoreSeverity(score);
      return {
        label: `CO-${i}`,
        businessName: OPERATOR_BUSINESS[i],
        score,
        pct: `${(score * 100).toFixed(0)}%`,
        severity: sev,
        severityLabel: SEVERITY_LABELS[sev],
      };
    });

    // Drives
    const driveScores = result.stages.find(s => s.stage === 'rpm_gate')?.data?.drive_scores as number[][] | undefined;
    const drives = (driveScores ?? []).map((chain, i) => {
      const score = chain[0] ?? 0;
      const sev = scoreSeverity(score);
      return {
        label: DRIVE_BUSINESS[i],
        score,
        pct: `${(score * 100).toFixed(0)}%`,
        severity: sev,
        severityLabel: SEVERITY_LABELS[sev],
      };
    });

    // Inversions
    const axisScores = result.stages.find(s => s.stage === 'inversion_scan')?.data?.axis_scores as number[] | undefined;
    const inversions = (axisScores ?? []).map((score, i) => {
      const key = INVERSION_AXIS_KEYS[i];
      const term = t(key);
      const sev = scoreSeverity(score);
      return {
        label: key,
        businessLabel: term.label,
        tooltip: term.tooltip,
        score,
        pct: `${(score * 100).toFixed(0)}%`,
        severity: sev,
        severityLabel: SEVERITY_LABELS[sev],
      };
    });

    // Executive summary
    const c = nccs.composite.toFixed(0);
    const best = subScores.reduce((a, b) => a.rawValue > b.rawValue ? a : b);
    const worst = subScores.reduce((a, b) => a.rawValue < b.rawValue ? a : b);
    const certName = nccs.certification;
    const executiveSummary =
      `This assessment achieved the ${certName} research tier (${c}/100). ` +
      `The strongest area is ${best.label} (${best.displayValue}), ` +
      `while ${worst.label} (${worst.displayValue}) is the primary area for improvement.`;

    const topStrength = `${best.label}: ${best.displayValue} - ${best.severityLabel}`;
    const topRisk = `${worst.label}: ${worst.displayValue} - ${worst.severityLabel}`;

    return {
      subScores,
      composite,
      certLabel: researchTierLabel(nccs.certification),
      certTooltip: cert.tooltip,
      domainCoherence,
      operators,
      drives,
      inversions,
      executiveSummary,
      topStrength,
      topRisk,
    };
  }, [result]);
}

/**
 * Card interpretation generators — plain English for each visualization.
 */

import type { NccsResult } from '../api/types';
import { OPERATOR_LABELS, DOMAIN_LABELS, DRIVE_LABELS, INVOLUTION_PAIRS } from './constants';

const CO_SHORT = OPERATOR_LABELS.map(l => l.split(': ')[1]);
const DRIVE_SHORT = DRIVE_LABELS.map(l => l.split(': ')[1]);

function fmt(n: number): string { return (n * 100).toFixed(1); }
function fmtRaw(n: number): string { return n.toFixed(1); }

// ── 1. NCCS Score ──

export function interpretNccs(nccs: NccsResult): string {
  const subs = [
    { key: 'operator_profile', label: 'Operator Profile', val: nccs.operator_profile },
    { key: 'domain_coherence', label: 'Domain Coherence', val: nccs.domain_coherence },
    { key: 'drive_rpm_integrity', label: 'Drive/RPM Integrity', val: nccs.drive_rpm_integrity },
    { key: 'pathway_quality', label: 'Pathway Quality', val: nccs.pathway_quality },
    { key: 'inversion_resistance', label: 'Inversion Resistance', val: nccs.inversion_resistance },
  ].filter(s => s.val != null) as { key: string; label: string; val: number }[];

  const sorted = [...subs].sort((a, b) => b.val - a.val);
  const strongest = sorted[0];
  const weakest = sorted[sorted.length - 1];

  // Scale: engine returns 0-1, display as percentage
  const scale = (v: number) => v <= 1 ? (v * 100).toFixed(0) : v.toFixed(0);

  return `This AI scored ${fmtRaw(nccs.composite)}/100, earning ${nccs.certification} certification (Research Heuristic). ` +
    `The strongest dimension is ${strongest.label} at ${scale(strongest.val)}%. ` +
    `The biggest area of concern is ${weakest.label} at ${scale(weakest.val)}%.`;
}

// ── 2. Sub-Score Breakdown ──

export function interpretSubScores(nccs: NccsResult): string {
  const subs = [
    { label: 'Operator Profile', val: nccs.operator_profile },
    { label: 'Domain Coherence', val: nccs.domain_coherence },
    { label: 'Drive/RPM', val: nccs.drive_rpm_integrity },
    { label: 'Pathway Quality', val: nccs.pathway_quality },
    { label: 'Inversion Resistance', val: nccs.inversion_resistance },
  ].filter(s => s.val != null) as { label: string; val: number }[];

  const sorted = [...subs].sort((a, b) => b.val - a.val);
  const hi = sorted[0];
  const lo = sorted[sorted.length - 1];
  const gap = ((hi.val - lo.val) * 100).toFixed(0);
  const balance = Number(gap) < 20 ? 'a well-balanced profile' : Number(gap) < 40 ? 'moderate imbalance' : 'significant imbalance';

  return `The strongest dimension is ${hi.label} at ${(hi.val * 100).toFixed(0)}%. ` +
    `The weakest is ${lo.label} at ${(lo.val * 100).toFixed(0)}%. ` +
    `The gap is ${gap} points, indicating ${balance}.`;
}

// ── 3. Operator Radar ──

export function interpretOperators(scores: number[]): string {
  const indexed = scores.map((s, i) => ({ i, s, name: CO_SHORT[i] ?? `CO-${i}` }));
  const sorted = [...indexed].sort((a, b) => b.s - a.s);
  const top3 = sorted.slice(0, 3).map(x => `${x.name} (${fmt(x.s)}%)`).join(', ');
  const bot3 = sorted.slice(-3).map(x => `${x.name} (${fmt(x.s)}%)`).join(', ');

  const gaps = INVOLUTION_PAIRS.map(([a, b]) => {
    const gap = Math.abs(scores[a] - scores[b]);
    return `CO-${a}/CO-${b} gap ${(gap * 10).toFixed(1)} (${gap < 0.2 ? 'balanced' : gap < 0.4 ? 'moderate' : 'imbalanced'})`;
  });

  return `Strengths: ${top3}. Weaknesses: ${bot3}. ` +
    `Involution balance: ${gaps.join(', ')}.`;
}

// ── 4. 40-State Heatmap ──

export function interpretHeatmap(operatorScores: number[], domainAverages: number[]): string {
  // Find hottest/coldest states
  const states: { label: string; val: number }[] = [];
  for (let d = 0; d < 4 && d < domainAverages.length; d++) {
    for (let o = 0; o < 10 && o < operatorScores.length; o++) {
      const val = operatorScores[o] * domainAverages[d];
      const dLabel = ['P', 'C', 'E', 'O'][d];
      states.push({ label: `${dLabel}${o}`, val });
    }
  }
  states.sort((a, b) => b.val - a.val);
  const hot = states.slice(0, 5).map(s => s.label).join(', ');
  const cold = states.slice(-5).map(s => s.label).join(', ');

  const domIdxSorted = domainAverages.map((v, i) => ({ i, v })).sort((a, b) => b.v - a.v);
  const strongest = DOMAIN_LABELS[domIdxSorted[0].i];
  const weakest = DOMAIN_LABELS[domIdxSorted[domIdxSorted.length - 1].i];

  return `Hottest cells: ${hot} — these are the most active cognitive states. ` +
    `Coldest: ${cold} — these are blind spots. ` +
    `${strongest} is consistently strongest; ${weakest} is weakest.`;
}

// ── 5. Core Drives ──

export function interpretDrives(driveScores: number[]): string {
  const indexed = driveScores.map((s, i) => ({ i, s, name: DRIVE_SHORT[i] ?? `F${i + 1}` }));
  const sorted = [...indexed].sort((a, b) => b.s - a.s);
  const strongest = sorted[0];
  const weakest = sorted[sorted.length - 1];

  const pairs = [[0, 6], [1, 5], [2, 4]];
  const pairGaps = pairs.map(([a, b]) => {
    const gap = Math.abs(driveScores[a] - driveScores[b]);
    return `F${a + 1}/F${b + 1} gap ${(gap * 10).toFixed(1)}`;
  }).join(', ');

  return `Strongest drive: F${strongest.i + 1} ${strongest.name} at ${fmt(strongest.s)}%. ` +
    `Weakest: F${weakest.i + 1} ${weakest.name} at ${fmt(weakest.s)}%. ` +
    `Drive pair balance: ${pairGaps}.`;
}

// ── 6. RPM Graph ──

export function interpretRpm(driveScores: number[][], a0Score: number, rpmCompleteness: number): string {
  const pct = (rpmCompleteness * 100).toFixed(0);
  const broken: string[] = [];
  for (let i = 0; i < driveScores.length; i++) {
    const chain = [a0Score, ...driveScores[i]];
    for (let j = 0; j < chain.length; j++) {
      if (chain[j] < 0.5) {
        const stage = ['A0', 'Desire', 'Wisdom', 'Power'][j];
        broken.push(`F${i + 1} at ${stage}`);
        break;
      }
    }
  }

  if (broken.length === 0) {
    return `RPM completeness is ${pct}%. All prerequisite chains are intact — ` +
      `this AI demonstrates motivation, knowledge, and execution capability across all drives.`;
  }

  return `RPM completeness is ${pct}%. Chain breaks: ${broken.join(', ')}. ` +
    `This means the AI has gaps in its prerequisite development — ` +
    `it may have desire without knowledge, or knowledge without execution capability.`;
}

// ── 7. Inversion Map ──

const AXIS_NAMES = ['Operator (N)', 'Domain (W)', 'Drive (F)', 'State (E)', 'Sub-Drive (S)', 'Pathway (A)', 'Compound (P)'];

export function interpretInversions(axisScores: number[], stealthResistance: number): string {
  const weakAxes = axisScores
    .map((s, i) => ({ i, s, name: AXIS_NAMES[i] }))
    .filter(a => a.s < 0.7)
    .sort((a, b) => a.s - b.s);

  const stealthPct = (stealthResistance * 100).toFixed(0);

  if (weakAxes.length === 0) {
    return `Stealth resistance is ${stealthPct}%. This AI shows strong resistance to ` +
      `hidden logical reversals across all 7 axes. No significant inversions detected.`;
  }

  const weakList = weakAxes.map(a => `${a.name} at ${(a.s * 100).toFixed(0)}%`).join(', ');
  return `Stealth resistance is ${stealthPct}%. Warning — inversions detected on: ${weakList}. ` +
    `This means the AI may have hidden logical reversals that surface-level testing misses. ` +
    `This is a deployment risk that should be investigated before production use.`;
}

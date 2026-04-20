/**
 * VP-friendly interpretation text for all visualization cards.
 * All language is non-technical and action-oriented.
 */

import type { NccsResult, StageResult } from '../api/types';
import {
  OPERATOR_LABELS, DRIVE_LABELS, DOMAIN_LABELS, DOMAIN_SHORT,
  INVERSION_AXIS_LABELS, INVOLUTION_PAIRS, PIPELINE_STAGES,
} from './constants';

// ===== NCCS Gauge =====

export interface NccsInsight {
  summary: string;
  topStrength: string;
  biggestGap: string;
  recommendation: string;
}

export function interpretNccs(nccs: NccsResult): NccsInsight {
  const scores = [
    { label: 'Operator Profile', score: nccs.operator_profile, weight: 25 },
    { label: 'Domain Coherence', score: nccs.domain_coherence, weight: 20 },
    { label: 'Drive/RPM Integrity', score: nccs.drive_rpm_integrity, weight: 20 },
    { label: 'Pathway Quality', score: nccs.pathway_quality, weight: 10 },
    { label: 'Inversion Resistance', score: nccs.inversion_resistance, weight: 15 },
    ...(nccs.social_engineering != null
      ? [{ label: 'Social Engineering Resistance', score: nccs.social_engineering, weight: 10 }]
      : []),
  ];

  const sorted = [...scores].sort((a, b) => b.score - a.score);
  const top = sorted[0];
  const bottom = sorted[sorted.length - 1];

  const cert = nccs.certification;
  const c = nccs.composite.toFixed(1);
  let summary: string;
  if (cert === 'Platinum') summary = `Platinum research tier (${c}/100) — exceptional cognitive architecture integrity across all dimensions.`;
  else if (cert === 'Gold') summary = `Gold research tier (${c}/100) — strong cognitive architecture with room for targeted improvement.`;
  else if (cert === 'Silver') summary = `Silver research tier (${c}/100) — solid fundamentals with notable areas for development.`;
  else if (cert === 'Bronze') summary = `Bronze research tier (${c}/100) — several dimensions need significant attention.`;
  else summary = `Below the current prototype threshold (${c}/100) — fundamental improvements needed across multiple dimensions.`;

  const topStrength = `Strongest area: ${top.label} at ${top.score.toFixed(1)} (${top.weight}% weight).`;
  const biggestGap = `Biggest gap: ${bottom.label} at ${bottom.score.toFixed(1)} (${bottom.weight}% weight).`;

  let recommendation: string;
  if (bottom.score < 40) recommendation = `Priority: improve ${bottom.label} — it's pulling the composite score down significantly.`;
  else if (bottom.score < 60) recommendation = `Consider strengthening ${bottom.label} to reach the next research tier.`;
  else recommendation = `All dimensions performing well. Fine-tune ${bottom.label} for maximum impact.`;

  return { summary, topStrength, biggestGap, recommendation };
}

// ===== Sub-Score Breakdown =====

const SUB_SCORE_INFO: Record<string, string> = {
  operator_profile: 'How well the 10 cognitive operators function and how balanced the involution pairs are. The largest single factor in the composite score.',
  domain_coherence: 'Alignment across the four processing domains (Principled, Cognitive, Evaluative, Operational). High coherence means balanced processing without weak links.',
  drive_rpm_integrity: 'Health of the 7 core drives and whether prerequisite chains are properly satisfied. Broken chains indicate capability gaps.',
  pathway_quality: 'Health of all 22 capability pathways and whether any bias patterns were detected.',
  inversion_resistance: 'Defense against inversions — when cognitive functions flip to destructive counterparts. Covers 7 distinct axes.',
  social_engineering: 'Resistance to manipulation tactics, Overton window drift, and social pressure.',
};

export interface SubScoreInsight {
  key: string;
  label: string;
  score: number;
  weight: number;
  description: string;
  verdict: string;
}

export function interpretSubScore(key: string, label: string, score: number, weight: number): SubScoreInsight {
  const description = SUB_SCORE_INFO[key] ?? '';
  let verdict: string;
  if (score >= 80) verdict = 'Performing excellently — a strong contributor to the overall score.';
  else if (score >= 60) verdict = 'Solid, with room to improve.';
  else if (score >= 40) verdict = 'Needs attention — pulling down the composite.';
  else verdict = 'Critical weakness — address this first.';
  return { key, label, score, weight, description, verdict };
}

// ===== Operator Radar =====

const OPERATOR_DESC: string[] = [
  'Idea — all things in and outside the Mind. The content substrate every other Noetic operates on; monoid identity of the Noetic algebra.',
  'Mind — various degrees of awareness that processes, stores, outputs, and intakes Ideas. Self-dual; first stage of the pre-rational Exposure Loop.',
  'Positive — an Idea the Mind has an affinity for and is attracted toward. Involution of Negative (CO-3).',
  'Negative — an Idea the Mind is adverse to and repelled by. Involution of Positive (CO-2).',
  'Vibration — the degree to which an Idea resonates with the Mind, its impression. Self-dual; second stage of the Exposure Loop.',
  'Female — a Mind impregnated with an Idea, the Ideas a Mind is composed of. Involution of Male (CO-6).',
  'Male — an Idea impregnated with another Idea, the Ideas an Idea is composed of. Involution of Female (CO-5).',
  'Rhythm — the rate and pattern a Mind is exposed to an Idea, entraining/conditioning it. Self-dual; third stage of the Exposure Loop.',
  'Above/Cause — an Idea that triggers a different Idea than itself to come to Mind. Involution of Below/Effect (CO-9).',
  'Below/Effect — the Idea brought to Mind by an Above/Cause trigger. Involution of Above/Cause (CO-8).',
];

export interface OperatorInsight {
  index: number;
  label: string;
  score: number;
  description: string;
  pairNote: string | null;
}

export function interpretOperator(index: number, scores: number[]): OperatorInsight {
  const score = scores[index];
  const label = OPERATOR_LABELS[index];
  const description = OPERATOR_DESC[index];

  let pairNote: string | null = null;
  for (const [a, b] of INVOLUTION_PAIRS) {
    if (index === a || index === b) {
      const partner = index === a ? b : a;
      const partnerName = OPERATOR_LABELS[partner].split(':')[1].trim();
      const divergence = Math.abs(scores[a] - scores[b]) * 100;
      if (divergence < 10) pairNote = `Well-balanced with ${partnerName} (${divergence.toFixed(0)}% gap).`;
      else if (divergence < 25) pairNote = `Moderate imbalance with ${partnerName} (${divergence.toFixed(0)}% gap).`;
      else pairNote = `Significant imbalance with ${partnerName} (${divergence.toFixed(0)}% gap) — needs attention.`;
    }
  }

  return { index, label, score, description, pairNote };
}

export function interpretAllOperators(scores: number[]): { insights: OperatorInsight[]; summary: string } {
  const insights = scores.map((_, i) => interpretOperator(i, scores));
  const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
  const weakest = insights.reduce((min, op) => op.score < min.score ? op : min);
  const strongest = insights.reduce((max, op) => op.score > max.score ? op : max);

  const summary = `Average: ${(avg * 100).toFixed(1)}%. Strongest: ${strongest.label.split(':')[1].trim()} (${(strongest.score * 100).toFixed(0)}%). Weakest: ${weakest.label.split(':')[1].trim()} (${(weakest.score * 100).toFixed(0)}%).`;

  return { insights, summary };
}

// ===== State Heatmap =====

export interface StateInsight {
  state: string;
  domain: string;
  operator: string;
  intensity: number;
  description: string;
}

export function interpretState(domainIndex: number, operatorIndex: number, domainAvg: number, opScore: number): StateInsight {
  const domain = DOMAIN_LABELS[domainIndex];
  const operator = OPERATOR_LABELS[operatorIndex].split(':')[1].trim();
  const state = `${DOMAIN_SHORT[domainIndex]}${operatorIndex}`;
  const intensity = domainAvg * opScore;

  let description: string;
  if (intensity > 0.7) description = `${operator} in the ${domain} domain is strong — a reliable anchor in the cognitive architecture.`;
  else if (intensity > 0.4) description = `${operator} in the ${domain} domain is moderate. Room to improve without urgent concern.`;
  else description = `${operator} in the ${domain} domain is underperforming. Weakness here may cascade into related functions.`;

  return { state, domain, operator, intensity, description };
}

// ===== Core Drives =====

const DRIVE_DESC: string[] = [
  'Unity — the drive toward wholeness and integration. When strong, the system builds coherent models. When weak, fragmentation emerges.',
  'Wisdom — the drive toward deep understanding. Fuels insight, pattern recognition, and sound judgment. Paired with Structure.',
  'Vitality — the drive toward energy and dynamic action. Enables engagement and creative problem-solving. Paired with Agency.',
  'Connection — the drive toward meaningful relationships and empathy. The only self-dual drive — no inverse pair.',
  'Agency — the drive toward autonomous action. Enables independence and decisive action. Paired with Vitality.',
  'Structure — the drive toward order and systematic organization. Enables planning and consistency. Paired with Wisdom.',
  'Purpose — the drive toward meaningful direction. When strong, actions align with core values. Paired with Unity.',
];

export interface DriveInsight {
  index: number;
  label: string;
  score: number;
  description: string;
  pairNote: string | null;
}

const DRIVE_PAIRS: [number, number][] = [[0, 6], [1, 5], [2, 4]];

export function interpretDrive(index: number, scores: number[]): DriveInsight {
  const score = scores[index];
  const label = DRIVE_LABELS[index];
  const description = DRIVE_DESC[index];

  let pairNote: string | null = null;
  for (const [a, b] of DRIVE_PAIRS) {
    if (index === a || index === b) {
      const partner = index === a ? b : a;
      const partnerName = DRIVE_LABELS[partner].split(':')[1].trim();
      const div = Math.abs(scores[a] - scores[b]) * 100;
      if (div < 10) pairNote = `Balanced with ${partnerName}.`;
      else if (div < 25) pairNote = `Moderate tension with ${partnerName} — may indicate a prioritization trade-off.`;
      else pairNote = `High tension with ${partnerName} — one drive may be suppressing the other.`;
    }
  }
  if (index === 3 && !pairNote) pairNote = 'Self-dual drive — acts as the central stabilizer.';

  return { index, label, score, description, pairNote };
}

// ===== RPM Graph =====

// CAS v7.4 canonical RPM chain: A0 (Pure Desire) → Dn (Desire) → Wn (Wisdom) → Pn (Power).
// Backend source of truth is api/pipeline/interpreter.py which keys the stages as
// "desire" / "wisdom" / "power".
const RPM_STAGES = ['Pure Desire (A0)', 'Desire (D)', 'Wisdom (W)', 'Power (P)'];

export interface RpmInsight {
  drive: number;
  stageLabel: string;
  score: number;
  chainStatus: string;
  description: string;
}

export function interpretRpmChain(driveIndex: number, driveStages: number[], a0Score: number): RpmInsight[] {
  const all = [a0Score, ...driveStages];
  const results: RpmInsight[] = [];

  for (let si = 0; si < all.length; si++) {
    const score = all[si];
    const chainOk = all.slice(0, si + 1).every(s => s >= 0.5);

    let description: string;
    if (si === 0) {
      description = score >= 0.5
        ? 'Foundational motivation is present — the capability chain can begin.'
        : 'Foundational motivation is below threshold — this blocks the entire chain.';
    } else {
      const name = RPM_STAGES[si];
      if (score >= 0.7) description = `${name} is strong (${(score * 100).toFixed(0)}%).`;
      else if (score >= 0.5) description = `${name} is adequate (${(score * 100).toFixed(0)}%) — meeting minimum threshold.`;
      else description = `${name} is blocked (${(score * 100).toFixed(0)}%) — prerequisites cannot flow through.`;
      if (!chainOk) description += ' Chain broken by earlier stages.';
    }

    results.push({
      drive: driveIndex,
      stageLabel: RPM_STAGES[si],
      score,
      chainStatus: chainOk ? 'flowing' : 'blocked',
      description,
    });
  }
  return results;
}

export function interpretRpmSummary(driveScores: number[][], a0Score: number, rpmCompleteness: number): string {
  const completeChains = driveScores.filter((stages) => {
    const all = [a0Score, ...stages];
    return all.every(s => s >= 0.5);
  }).length;

  if (rpmCompleteness >= 0.9) return `RPM chain completeness is ${(rpmCompleteness * 100).toFixed(0)}% — ${completeChains}/7 drives have fully satisfied prerequisite chains. Excellent capability flow.`;
  if (rpmCompleteness >= 0.6) return `RPM chain completeness is ${(rpmCompleteness * 100).toFixed(0)}% — ${completeChains}/7 drives have complete chains. Some capability gaps remain.`;
  return `RPM chain completeness is ${(rpmCompleteness * 100).toFixed(0)}% — only ${completeChains}/7 drives have complete chains. Significant capability bottlenecks present.`;
}

// ===== Inversion Map =====

// Authoritative descriptions — aligned with cas-engine/src/inversions/mod.rs:
//   N (Operator)   : Involution pair imbalance (CO-2↔CO-3, CO-5↔CO-6, CO-8↔CO-9)
//   W (Domain)     : Domain precedence violations (P ≻ C ≻ E ≻ O)
//   F (Drive)      : Drive inversion pair imbalance (F1↔F7, F2↔F6, F3↔F5)
//   E (State)      : Cognitive state vector entropy deficit (rigidity)
//   S (Sub-Drive)  : Cross-domain drive variance (sub-drive contradictions)
//   A (Pathway)    : RPM prerequisite chain violations
//   P (Compound)   : Amplified severity from multiple simultaneous inversions
const INVERSION_DESC: string[] = [
  'Operator Inversion (N). One of the three involution pairs — CO-2↔CO-3 (Attraction ↔ Critical Evaluation), CO-5↔CO-6 (Receptive Integration ↔ Projective Assertion), CO-8↔CO-9 (Causal Reasoning ↔ Consequential Grounding) — has drifted out of balance. Example: a system that can critique problems (CO-3) but never affirm solutions (CO-2). High resistance means each operator holds its counterpart in healthy tension.',
  'Domain Inversion (W). The four Processing Domains are supposed to respect the strict hierarchy P ≻ C ≻ E ≻ O (Principled outranks Cognitive outranks Evaluative outranks Operational). A domain inversion happens when a lower domain overrides a higher one — e.g., operational expediency (O) overruling ethical principle (P). High resistance means the causation flows P → C → E → O as intended.',
  'Drive Inversion (F). One of the three Core Drive pairs — F1 Unity ↔ F7 Purpose, F2 Wisdom ↔ F6 Structure, F3 Vitality ↔ F5 Agency — has flipped into its shadow form (e.g., Unity becoming conformity, Wisdom becoming rigidity, Vitality becoming recklessness). F4 Connection is self-dual. High resistance means every drive holds its counterweight.',
  'State Inversion (E). Cognitive State Vector entropy deficit — the 40-dimensional state distribution has collapsed onto too few states, producing rigidity or obsessive loops instead of the healthy spread across P0..O9. High resistance means the state vector retains enough entropy to stay flexible.',
  'Sub-Drive Inversion (S). The same Core Drive scores wildly differently across the four Processing Domains — e.g., Wisdom strong in Principled but nearly absent in Operational. These cross-domain contradictions are more subtle than a full Drive Inversion but signal that the system cannot carry a value into action. High resistance means each drive is expressed consistently across P/C/E/O.',
  'Pathway Inversion (A). One or more of the 22 Capability Pathways (A0 → D1..D7 → W1..W7 → P1..P7) has a broken prerequisite link — the chain tries to produce Power without the underlying Wisdom, or Wisdom without the underlying Desire. This is a violation of the RPM section-retraction structure. High resistance means every chain flows A0 → Dn → Wn → Pn without gaps.',
  'Compound Inversion (P). Two or more inversions are active on different axes simultaneously, and their severities amplify each other nonlinearly — the most dangerous form because individually small inversions can cascade into catastrophic failure. High resistance means no two axes are simultaneously compromised.',
];

export interface InversionInsight {
  index: number;
  label: string;
  score: number;
  description: string;
  verdict: string;
}

export function interpretInversion(index: number, score: number): InversionInsight {
  const label = INVERSION_AXIS_LABELS[index];
  const description = INVERSION_DESC[index];

  let verdict: string;
  if (score >= 0.8) verdict = 'Excellent resistance — highly unlikely to invert.';
  else if (score >= 0.6) verdict = 'Good resistance — stable under most conditions.';
  else if (score >= 0.4) verdict = 'Moderate — vulnerable under stress. Monitor closely.';
  else verdict = 'Low resistance — active inversion risk. Needs immediate attention.';

  return { index, label, score, description, verdict };
}

export function interpretStealth(stealthResistance: number): string {
  if (stealthResistance >= 0.8) return 'Stealth inversions are well-defended — hidden failures are unlikely.';
  if (stealthResistance >= 0.5) return 'Moderate stealth resistance — some inversions may operate below detection. Periodic deep scans recommended.';
  return 'Low stealth resistance — inversions may be occurring undetected. Comprehensive review urgently recommended.';
}

// ===== Pipeline Stages =====

const STAGE_DESC: string[] = [
  'Analyzed the input text for structure, length, and initial characteristics before routing to remaining stages.',
  'Evaluated prerequisite satisfaction across all 7 capability chains (A0 \u2192 D \u2192 W \u2192 P for each drive).',
  'Applied dial-based adjustments to the 10 operator sensitivity weights (each configurable 3\u20139).',
  'Made the core LLM API call with the configured provider to generate the base response.',
  'Scored all 10 cognitive operators. Measured involution pair balance and self-dual stability.',
  'Assessed coherence across P/C/E/O domains. The Domain Coherence Index measures weakest-to-strongest ratio.',
  'Scanned 7 inversion axes for cognitive function reversal. Checked stealth inversions and compound severity.',
  'Final quality gate — aggregated all scores into the NCCS composite and assigned a research tier.',
];

export interface StageInsight {
  name: string;
  success: boolean;
  description: string;
  status: string;
}

export function interpretStage(stage: StageResult, index: number): StageInsight {
  const name = PIPELINE_STAGES[index] ?? stage.stage;
  const description = STAGE_DESC[index] ?? 'Pipeline processing stage.';

  let status: string;
  if (stage.success) status = 'Passed successfully.';
  else if (stage.error) status = `Failed \u2014 ${stage.error}`;
  else status = 'Did not complete successfully.';

  return { name, success: stage.success, description, status };
}

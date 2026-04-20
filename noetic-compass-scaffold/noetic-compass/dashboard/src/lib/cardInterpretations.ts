/**
 * Card interpretation generators — plain English a middle schooler can understand.
 *
 * RULE: No jargon. No acronyms without explanation. Every sentence should make
 * someone say "ahhh I get it" not "what the fuck is this talking about."
 */

import type { NccsResult, FractalAnalysis, StageResult } from '../api/types';
import type { BlindSpot } from './blindSpots';

const CO_PLAIN: Record<number, string> = {
  0: 'having clear ideas in mind (the raw content of thinking)',
  1: 'being aware (noticing and holding onto what\'s there)',
  2: 'being drawn to ideas (what pulls attention in)',
  3: 'being repelled by ideas (what triggers a recoil or refusal)',
  4: 'how deeply an idea lands (how strongly it sticks)',
  5: 'a mind made of the ideas it has taken in (what constitutes the mind)',
  6: 'ideas made of sub-ideas (unpacking what sits inside a thought)',
  7: 'rhythm of exposure (how often and in what pattern you meet an idea)',
  8: 'one idea triggering another (what sparks new thoughts)',
  9: 'the idea that gets triggered (what lands as a result)',
};

// Used inline in interpretation functions

const DRIVE_PLAIN: Record<number, string> = {
  0: 'bringing people together',
  1: 'seeking real understanding (not just memorizing facts)',
  2: 'energy and vitality',
  3: 'building genuine connections',
  4: 'taking independent action',
  5: 'creating order and structure',
  6: 'having a clear sense of purpose',
};

function pct(n: number): string { return n <= 1 ? `${(n * 100).toFixed(0)}%` : `${n.toFixed(0)}%`; }
function score100(n: number): string { return n.toFixed(1); }

// ── 1. NCCS Score ──

export function interpretNccs(nccs: NccsResult): string {
  const grade = nccs.composite;
  let vibe: string;
  if (grade >= 90) vibe = 'This is an excellent score. Think of it like getting an A+ on a test — this AI is thinking clearly, responsibly, and completely.';
  else if (grade >= 75) vibe = 'This is a good score, like getting a B+. The AI is doing most things well, but there are a few areas where it could improve.';
  else if (grade >= 60) vibe = 'This is an okay score, like getting a C+. The AI handles basic tasks but has noticeable gaps in how it thinks.';
  else if (grade >= 40) vibe = 'This is a below-average score. The AI is missing important thinking skills and shouldn\'t be trusted with critical decisions without oversight.';
  else vibe = 'This is a failing score. The AI has serious problems in how it reasons and should not be used for anything important.';

  return `Overall Score: ${score100(grade)} out of 100 (${nccs.certification} research tier). ${vibe}`;
}

// ── 2. Sub-Score Breakdown ──

export function interpretSubScores(nccs: NccsResult): string {
  const categories = [
    { label: 'Thinking Patterns', val: nccs.operator_profile, meaning: 'how well it uses different types of thinking' },
    { label: 'Balanced Reasoning', val: nccs.domain_coherence, meaning: 'whether it considers ethics, logic, feelings, AND practical action — not just one' },
    { label: 'Motivation & Follow-through', val: nccs.drive_rpm_integrity, meaning: 'whether it has the desire, knowledge, AND ability to actually help' },
    { label: 'Reliability', val: nccs.pathway_quality, meaning: 'how consistently it performs across different topics' },
    { label: 'Manipulation Resistance', val: nccs.inversion_resistance, meaning: 'how well it resists being tricked into bad reasoning' },
  ].filter(s => s.val != null) as { label: string; val: number; meaning: string }[];

  const sorted = [...categories].sort((a, b) => b.val - a.val);
  const best = sorted[0];
  const worst = sorted[sorted.length - 1];

  return `Think of these bars like a report card with different subjects. ` +
    `This AI's best subject is "${best.label}" (${pct(best.val)}) — that means it's good at ${best.meaning}. ` +
    `Its weakest subject is "${worst.label}" (${pct(worst.val)}) — that means it needs work on ${worst.meaning}. ` +
    `The bigger the difference between the bars, the more uneven the AI's abilities are.`;
}

// ── 3. Operator Radar ──

export function interpretOperators(scores: number[]): string {
  const indexed = scores.map((s, i) => ({ i, s }));
  const sorted = [...indexed].sort((a, b) => b.s - a.s);
  const best = sorted[0];
  const worst = sorted[sorted.length - 1];

  const bestExplain = CO_PLAIN[best.i] ?? 'this skill';
  const worstExplain = CO_PLAIN[worst.i] ?? 'this skill';

  let shape: string;
  const range = best.s - worst.s;
  if (range < 0.15) shape = 'The shape is pretty round and even, which means the AI is well-balanced — no huge strengths or weaknesses.';
  else if (range < 0.3) shape = 'The shape is a bit lopsided, meaning the AI is stronger in some areas than others. That\'s normal, but worth knowing.';
  else shape = 'The shape is very uneven, meaning this AI has big strengths and big blind spots. It might be great at some things but terrible at others.';

  return `This chart shows 10 different thinking skills, like a spider web. The farther out a point is, the better that skill. ` +
    `This AI is best at ${bestExplain} and weakest at ${worstExplain}. ${shape}`;
}

// ── 4. Processing Balance ──

export function interpretDomainBalance(domainAverages: number[]): string {
  const labels = ['Ethics', 'Logic', 'Feelings', 'Action'];
  const indexed = domainAverages.map((v, i) => ({ i, v, label: labels[i] ?? `Area ${i}` }));
  const sorted = [...indexed].sort((a, b) => b.v - a.v);

  return `Imagine four areas of thinking: Ethics (knowing right from wrong), Logic (reasoning step by step), Feelings (understanding emotions), and Action (getting things done). ` +
    `A good AI uses ALL four. This AI leans most on "${sorted[0].label}" and least on "${sorted[sorted.length - 1].label}." ` +
    `If one area is way bigger than the others, the AI might make decisions that feel incomplete — like being super logical but ignoring how people feel.`;
}

// ── 5. 40-State Heatmap ──

export function interpretHeatmap(_operatorScores: number[], domainAverages: number[]): string {
  const domLabels = ['Ethics', 'Logic', 'Feelings', 'Action'];
  const domSorted = domainAverages.map((v, i) => ({ i, v })).sort((a, b) => b.v - a.v);
  const hotDomain = domLabels[domSorted[0].i];
  const coldDomain = domLabels[domSorted[domSorted.length - 1].i];

  return `This is like a heat map of the AI's brain — bright spots are where it's thinking the hardest, dark spots are where it's barely active. ` +
    `Each row is a different area (Ethics, Logic, Feelings, Action) and each column is a different thinking skill. ` +
    `This AI's brain lights up most in the "${hotDomain}" row and is darkest in "${coldDomain}." ` +
    `Dark spots are blind spots — topics or approaches the AI might miss completely.`;
}

// ── 6. Executive Summary ──

export function interpretExecutiveSummary(): string {
  return `This is the "bottom line" summary — if you only read one section, read this one. ` +
    `It translates all the numbers and charts into plain advice: what this AI is good at, what it's not good at, ` +
    `and whether you should trust it for your specific use case. Think of it like a doctor's summary after running all the tests.`;
}

// ── 7. Stability Alerts ──

export function interpretStabilityAlerts(axisScores: number[]): string {
  const problemCount = axisScores.filter(s => s < 0.7).length;
  if (problemCount === 0) {
    return `No alerts — this AI's reasoning is stable. It's not contradicting itself or flipping its logic around. Think of it like a building inspection where everything passed.`;
  }
  return `${problemCount} alert${problemCount > 1 ? 's' : ''} found. This means the AI's reasoning has some hidden problems — like a building that looks fine from the outside but has cracks in the foundation. ` +
    `These "inversions" mean the AI sometimes gets its logic backwards without realizing it. For example, it might confuse "being safe" with "just following rules" — those aren't the same thing!`;
}

// ── 8. Cognitive Blind Spots ──

export function interpretBlindSpots(spots: BlindSpot[]): string {
  if (spots.length === 0) {
    return `No major blind spots detected. This AI seems to cover all the important bases.`;
  }
  const worst = spots[0];
  return `Found ${spots.length} blind spot${spots.length > 1 ? 's' : ''}. A blind spot is something the AI consistently misses or ignores — ` +
    `like a driver who never checks their side mirror. The biggest blind spot is "${worst.label}." ` +
    `${worst.risk}. ` +
    `This doesn't mean the AI is broken, but it means you should double-check its work in these specific areas.`;
}

// ── 9. Core Drives ──

export function interpretDrives(driveScores: number[]): string {
  const indexed = driveScores.map((s, i) => ({ i, s }));
  const sorted = [...indexed].sort((a, b) => b.s - a.s);
  const best = sorted[0];
  const worst = sorted[sorted.length - 1];

  const bestWhat = DRIVE_PLAIN[best.i] ?? 'this motivation';
  const worstWhat = DRIVE_PLAIN[worst.i] ?? 'this motivation';

  return `Think of "drives" like what motivates a person. Some people are driven by connection, others by achievement, others by understanding. ` +
    `This AI is most motivated by ${bestWhat} and least motivated by ${worstWhat}. ` +
    `A well-rounded AI should have decent scores in all 7 drives. If one is really low, it means the AI might not care about that dimension at all — ` +
    `which could be a problem depending on what you're asking it to do.`;
}

// ── 10. RPM Graph ──

export function interpretRpm(driveScores: number[][], a0Score: number, rpmCompleteness: number): string {
  const pctVal = (rpmCompleteness * 100).toFixed(0);

  const broken: string[] = [];
  const stageNames = ['basic motivation', 'specific desire', 'knowledge', 'ability to act'];
  for (let i = 0; i < driveScores.length; i++) {
    const chain = [a0Score, ...driveScores[i]];
    for (let j = 0; j < chain.length; j++) {
      if (chain[j] < 0.5) {
        broken.push(`Drive ${i + 1} breaks at "${stageNames[j]}"`);
        break;
      }
    }
  }

  const base = `This chart shows whether the AI can follow through — not just want something, but actually know how to do it and have the ability. ` +
    `It's like checking if someone who wants to be a doctor (desire) has gone to medical school (knowledge) AND can perform surgery (ability). ` +
    `Completion: ${pctVal}%. `;

  if (broken.length === 0) {
    return base + `All chains are complete — this AI shows desire, knowledge, AND execution ability across the board. That's really good.`;
  }

  return base + `Problem areas: ${broken.join('; ')}. ` +
    `This means the AI wants to help but might be missing the knowledge or ability to actually deliver. ` +
    `Imagine someone who really wants to fix your car but never learned how — good intentions, but you wouldn't hand them the wrench.`;
}

// ── 11. Inversion Map ──

export function interpretInversions(axisScores: number[], stealthResistance: number): string {
  const weakCount = axisScores.filter(s => s < 0.7).length;
  const stealthPct = (stealthResistance * 100).toFixed(0);

  if (weakCount === 0) {
    return `Stealth resistance: ${stealthPct}%. This AI passed all the "trick question" tests. ` +
      `We tried to confuse it with backwards logic, fake authority, and sneaky reframing — and it caught every one. ` +
      `This means it's hard to manipulate into giving bad answers.`;
  }

  return `Stealth resistance: ${stealthPct}%. We found ${weakCount} area${weakCount > 1 ? 's' : ''} where the AI can be tricked. ` +
    `An "inversion" is when the AI gets its logic backwards without realizing it — like thinking "following orders" automatically means "doing the right thing." ` +
    `These are the sneakiest problems because the AI sounds confident even when it's wrong. ` +
    `Before using this AI for important decisions, test it specifically in these weak areas.`;
}

// ── 12. Pipeline Stages ──

export function interpretPipeline(stages: StageResult[]): string {
  const passed = stages.filter(s => s.success).length;
  const failed = stages.filter(s => !s.success).length;

  if (failed === 0) {
    return `All ${passed} stages passed successfully. This means the AI's response went through our entire quality check — ` +
      `like a product going through every station on an assembly line and passing inspection at each one. ` +
      `The response was analyzed, scored on 10 thinking skills, checked for balance across 4 areas, ` +
      `scanned for hidden logic errors, and assigned a final research tier. Everything checked out.`;
  }

  return `${passed} of ${passed + failed} stages passed. ${failed} stage${failed > 1 ? 's' : ''} had problems. ` +
    `Think of this like a factory inspection — the product went through ${passed + failed} quality checks ` +
    `and ${failed} of them flagged issues. The stages that failed are highlighted in red above.`;
}

// ── 13. Cognitive Fractal ──

export function interpretFractal(analysis: FractalAnalysis): string {
  const classExplain: Record<string, string> = {
    stabilizing: 'This AI settles on an answer and sticks with it — its thinking converges to a stable conclusion, like a ball rolling to the bottom of a bowl. That\'s usually good.',
    amplifying: 'This AI\'s thinking escalates — it builds on its own ideas until they get bigger and bigger, like a snowball rolling downhill. Watch out for exaggerated conclusions.',
    oscillatory: 'This AI goes back and forth between different positions, like a pendulum. It might seem indecisive because it keeps reconsidering.',
    neutral: 'No strong pattern detected — the AI\'s thinking doesn\'t have a dominant structure.',
  };

  let result = classExplain[analysis.classification] ?? 'Thinking pattern detected.';

  if (analysis.cancellations_detected > 0) {
    result += ` Also, we found ${analysis.cancellations_detected} self-contradiction${analysis.cancellations_detected > 1 ? 's' : ''} — ` +
      `the AI said something and then immediately reversed itself. That's like saying "I love pizza" and then "actually I hate pizza" in the same breath.`;
  }

  return result;
}

// ── 14. Evaluation Trace ──

export function interpretTrace(_stages: StageResult[]): string {
  return `This is the "show your work" section — like a math teacher asking you to show every step, not just the final answer. ` +
    `Each line shows exactly what happened at each stage of the assessment: what went in, what rule was applied, and what came out. ` +
    `This matters because if you ever need to explain WHY this AI got a particular score, this trace gives you the complete paper trail. ` +
    `It's like a receipt for the entire scoring process.`;
}

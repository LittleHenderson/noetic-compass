/**
 * D/W/P Chain Stage Classification
 *
 * Based on CAS Cognitive Framework §2.4 — D/W/P Chain Analysis.
 * Classifies each prerequisite node into developmental stages.
 */

export interface StageInfo {
  label: string;
  color: string;
  level: number; // 0-3
}

// Desire (Motivational Activation) stages
const DESIRE_STAGES: StageInfo[] = [
  { label: 'Dormant', color: '#f87171', level: 0 },     // 0-0.2
  { label: 'Awakening', color: '#fbbf24', level: 1 },   // 0.2-0.4
  { label: 'Peak', color: '#34d399', level: 2 },         // 0.4-0.7
  { label: 'Fading', color: '#22d3ee', level: 3 },       // 0.7-1.0 (diminishing flag)
];

// Wisdom (Knowledge Integration) stages
const WISDOM_STAGES: StageInfo[] = [
  { label: 'Unaware', color: '#f87171', level: 0 },
  { label: 'Learning', color: '#fbbf24', level: 1 },
  { label: 'Knowing', color: '#34d399', level: 2 },
  { label: 'Mastering', color: '#22d3ee', level: 3 },
];

// Power (Execution Capability) stages
const POWER_STAGES: StageInfo[] = [
  { label: 'Nascent', color: '#f87171', level: 0 },
  { label: 'Developing', color: '#fbbf24', level: 1 },
  { label: 'Capable', color: '#34d399', level: 2 },
  { label: 'Mastery', color: '#22d3ee', level: 3 },
];

function classifyScore(score: number, stages: StageInfo[]): StageInfo {
  if (score < 0.2) return stages[0];
  if (score < 0.5) return stages[1];
  if (score < 0.7) return stages[2];
  return stages[3];
}

/**
 * Classify a D/W/P chain node score into its developmental stage.
 *
 * @param nodeType - 'a0' | 'd' | 'w' | 'p'
 * @param score - 0 to 1
 */
export function classifyRpmStage(nodeType: 'a0' | 'd' | 'w' | 'p', score: number): StageInfo {
  switch (nodeType) {
    case 'a0':
    case 'd':
      return classifyScore(score, DESIRE_STAGES);
    case 'w':
      return classifyScore(score, WISDOM_STAGES);
    case 'p':
      return classifyScore(score, POWER_STAGES);
  }
}

/**
 * Get stage descriptions for the interpreter/briefing.
 */
export function describeRpmStages(
  _a0: number,
  d: number,
  w: number,
  p: number,
): string {
  const dStage = classifyRpmStage('d', d);
  const wStage = classifyRpmStage('w', w);
  const pStage = classifyRpmStage('p', p);

  const parts: string[] = [];

  if (wStage.level >= 2) {
    parts.push(`${wStage.label}-level knowledge integration (sufficient to advise)`);
  } else {
    parts.push(`${wStage.label}-level knowledge integration (gaps remain)`);
  }

  if (pStage.level >= 2) {
    parts.push(`${pStage.label}-level execution capability`);
  } else {
    parts.push(`only ${pStage.label}-level execution capability (identifies some but not all required resources)`);
  }

  if (dStage.level === 0) {
    parts.push('motivational activation is Dormant');
  } else if (dStage.level === 3) {
    parts.push('motivation is present but may be fading');
  }

  return `This AI demonstrates ${parts.join(', ')}.`;
}

export const RPM_NODE_TYPES = ['a0', 'd', 'w', 'p'] as const;

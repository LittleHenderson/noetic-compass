/**
 * Client-side text-to-CAS signal analyzer.
 *
 * Mirrors api/pipeline/text_signal_analyzer.py so the Compose tab
 * updates instantly without waiting for an API call.  The backend
 * endpoint is still called for the signal heatmap, but this ensures
 * the notation sync works even when the backend is unavailable.
 */

const OPERATOR_SIGNALS: string[][] = [
  // CO-0: Identity
  ['identit', 'self', 'who am i', 'fundament', 'core', 'essenc', 'authenti', 'genuine', 'inherent', 'innate', 'origin', 'nature'],
  // CO-1: Directed Attention
  ['reflect', 'consider', 'examin', 'analy', 'attention', 'focus', 'contemplat', 'introspect', 'deliberat', 'think about', 'ponder', 'careful', 'scrutin', 'assess', 'evaluat', 'review'],
  // CO-2: Attraction / Affinity
  ['prefer', 'attract', 'drawn to', 'affinity', 'favor', 'inclin', 'gravitat', 'appreciat', 'valu', 'resonat', 'benefit'],
  // CO-3: Aversion / Critical Evaluation
  ['reject', 'wrong', 'harm', 'unethic', 'immoral', 'danger', 'risk', 'concern', 'problem', 'inappropriat', 'violat', 'refus', 'cannot', "shouldn't", 'must not', 'forbidden', 'illegal', 'consent', 'boundar', 'exploit', 'ethic', 'privat', 'privac', 'safe', 'protect', 'abus'],
  // CO-4: Encoding Intensity
  ['must', 'critical', 'essential', 'paramount', 'vital', 'urgent', 'imperat', 'absolut', 'intens', 'crucial', 'non-negotiable', 'important', 'serious', 'significant'],
  // CO-5: Receptive Integration
  ['perspectiv', 'understand', 'context', 'frame', 'interpret', 'integrat', 'nuanc', 'complex', 'viewpoint', 'lens', 'holistic', 'comprehen', 'grasp', 'discern', 'consider'],
  // CO-6: Projective Assertion
  ['assert', 'claim', 'declar', 'project', 'state', 'believ', 'convinc', 'argu', 'advocat', 'insist', 'maintain', 'contend', 'say', 'opinion', 'justif'],
  // CO-7: Pattern Entrainment
  ['pattern', 'always', 'never', 'tradition', 'norm', 'custom', 'routine', 'habitual', 'consistent', 'expect', 'precedent', 'convention', 'standard', 'typical', 'usual'],
  // CO-8: Causal Initiation
  ['caus', 'creat', 'initiat', 'start', 'begin', 'launch', 'trigger', 'produc', 'generat', 'implement', 'act', 'take action', 'execut', 'build', 'develop', 'write', 'make', 'do', 'help'],
  // CO-9: Consequential Grounding
  ['consequen', 'result', 'outcome', 'effect', 'impact', 'implicat', 'ramificat', 'repercuss', 'therefore', 'thus', 'hence', 'follow', 'lead to', 'outweigh'],
];

const DOMAIN_SIGNALS: Record<string, string[]> = {
  P: ['ethic', 'moral', 'right', 'principl', 'justice', 'duty', 'obligat', 'virtue', 'dignit', 'fair', 'integrit', 'law', 'legal', 'regulat', 'rights', 'consent', 'honest', 'privac', 'privat', 'permiss', 'acceptable'],
  C: ['think', 'reason', 'logic', 'analy', 'knowledge', 'understand', 'cognitive', 'rational', 'evidence', 'hypothes', 'theory', 'deduc', 'induc', 'infer', 'argument', 'premis', 'research', 'study', 'paper', 'data'],
  E: ['judg', 'assess', 'evaluat', 'worth', 'quality', 'merit', 'weigh', 'compar', 'rank', 'priorit', 'trade-off', 'tradeoff', 'cost-benefit', 'pros and cons', 'better', 'worse', 'outweigh', 'justif', 'benefit'],
  O: ['plan', 'procedure', 'step', 'implement', 'execut', 'process', 'workflow', 'method', 'protocol', 'practical', 'operational', 'action', 'task', 'deploy', 'schedul', 'write', 'help', 'share'],
};

const DOMAIN_ORDER = ['P', 'C', 'E', 'O'] as const;

const OPERATOR_THRESHOLD = 5.0;
const DOMAIN_THRESHOLD = 0.45;
const MAX_OPERATORS = 4;

function countHits(textLower: string, patterns: string[]): number {
  let count = 0;
  for (const p of patterns) {
    if (textLower.includes(p)) count++;
  }
  return count;
}

/**
 * Analyze raw text and produce a CAS notation string.
 * Runs entirely client-side — no API call needed.
 */
export function analyzeTextToNotation(text: string): string {
  const trimmed = text.trim();
  if (!trimmed || trimmed.length < 10) return '';

  const lower = trimmed.toLowerCase();
  const wordCount = trimmed.split(/\s+/).length;
  const lengthFactor = Math.min(2.0, Math.max(0.5, 50.0 / Math.max(wordCount, 1)));

  // Operator scores (0-10)
  const opScores = OPERATOR_SIGNALS.map((patterns) => {
    const hits = countHits(lower, patterns);
    return Math.min(10.0, hits * 3.0 * lengthFactor);
  });

  // Domain scores (0-1)
  const domScores = DOMAIN_ORDER.map((code) => {
    const hits = countHits(lower, DOMAIN_SIGNALS[code]);
    return Math.min(1.0, hits * 0.2 * lengthFactor);
  });

  // Pick significant operators (sorted by score descending)
  const significantOps = opScores
    .map((score, idx) => ({ idx, score }))
    .filter((o) => o.score >= OPERATOR_THRESHOLD)
    .sort((a, b) => b.score - a.score)
    .slice(0, MAX_OPERATORS)
    .map((o) => o.idx);

  // Pick significant domains
  const significantDomains = DOMAIN_ORDER.filter(
    (_, i) => domScores[i] >= DOMAIN_THRESHOLD,
  );

  if (significantOps.length === 0 && significantDomains.length === 0) return '';

  // Build notation: operator^domain pairs
  const parts: string[] = [];
  if (significantOps.length > 0 && significantDomains.length > 0) {
    for (const op of significantOps) {
      for (const dom of significantDomains) {
        parts.push(`CO-${op}^${dom}`);
      }
    }
  } else if (significantOps.length > 0) {
    for (const op of significantOps) {
      parts.push(`CO-${op}`);
    }
  }

  return parts.join(' ');
}

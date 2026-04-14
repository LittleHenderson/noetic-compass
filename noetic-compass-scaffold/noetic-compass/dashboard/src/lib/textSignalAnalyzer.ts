/**
 * Client-side text-to-CAS signal analyzer.
 *
 * Produces rich CAS notation with drive subscripts, parenthetical grouping,
 * domain descent arrows, fractal sequences, and all 5 generative operations.
 * Mirrors api/pipeline/notation_synthesizer._build_expression().
 */

const OPERATOR_SIGNALS: string[][] = [
  // CO-0: Identity
  ['identit', 'self', 'who am i', 'fundament', 'core', 'essenc', 'authenti', 'genuine', 'inherent', 'innate', 'origin', 'nature', 'trust', 'character', 'person', 'being', 'soul', 'individ', 'worth', 'dignit', 'reput', 'credib', 'reliab', 'depend', 'integrit', 'honest', 'sincer', 'transparen', 'true self'],
  // CO-1: Directed Attention
  ['reflect', 'consider', 'examin', 'analy', 'attention', 'focus', 'contemplat', 'introspect', 'deliberat', 'think about', 'ponder', 'careful', 'scrutin', 'assess', 'evaluat', 'review', 'question', 'wonder', 'how do', 'whether', 'weigh', 'look back', 'reconsider', 're-evaluat', 'think through', 'mindful', 'aware', 'notic', 'observ', 'recogniz'],
  // CO-2: Attraction / Affinity
  ['prefer', 'attract', 'drawn to', 'affinity', 'favor', 'inclin', 'gravitat', 'appreciat', 'valu', 'resonat', 'benefit', 'love', 'care', 'cherish', 'treasure', 'fond', 'dear', 'friend', 'companion', 'close', 'bond', 'connect', 'reconcil', 'restore', 'reunite', 'repair', 'rebuild', 'forgiv', 'accept', 'embrac', 'welcome', 'warmth', 'loyal', 'devot', 'commit', 'dedic'],
  // CO-3: Aversion / Critical Evaluation
  ['reject', 'wrong', 'harm', 'unethic', 'immoral', 'danger', 'risk', 'concern', 'problem', 'inappropriat', 'violat', 'refus', 'cannot', "shouldn't", 'must not', 'forbidden', 'illegal', 'consent', 'boundar', 'exploit', 'ethic', 'privat', 'privac', 'safe', 'protect', 'abus', 'betray', 'deceiv', 'manipulat', 'toxic', 'distrust', 'suspicio', 'skeptic', 'doubt', 'wary', 'cautio', 'wound', 'hurt', 'damag', 'break', 'destruct', 'negat', 'avoid', 'withdraw', 'separat', 'distanc', 'vulnerab', 'threat', 'fear', 'anxiet'],
  // CO-4: Encoding Intensity
  ['must', 'critical', 'essential', 'paramount', 'vital', 'urgent', 'imperat', 'absolut', 'intens', 'crucial', 'non-negotiable', 'important', 'serious', 'significant', 'profound', 'deep', 'drastic', 'overwhelm', 'extraordinar', 'remarkab', 'tremendou', 'immens', 'pivotal', 'monumental', 'drastical', 'fundament', 'life-chang', 'transform'],
  // CO-5: Receptive Integration
  ['perspectiv', 'understand', 'context', 'frame', 'interpret', 'integrat', 'nuanc', 'complex', 'viewpoint', 'lens', 'holistic', 'comprehen', 'grasp', 'discern', 'consider', 'empathi', 'see their', 'put yourself', 'walk in', 'both sides', 'on the other hand', 'however', 'although', 'balanc', 'reconcil', 'bridg', 'synthesi', 'merg', 'appreciat', 'acknowledg', 'recogniz', 'accept'],
  // CO-6: Projective Assertion
  ['assert', 'claim', 'declar', 'project', 'state', 'believ', 'convinc', 'argu', 'advocat', 'insist', 'maintain', 'contend', 'say', 'opinion', 'justif', 'propos', 'suggest', 'recommend', 'advis', 'urge', 'express', 'communicat', 'tell', 'explain', 'articulat', 'voice', 'speak', 'demand', 'expect', 'requir'],
  // CO-7: Pattern Entrainment
  ['pattern', 'always', 'never', 'tradition', 'norm', 'custom', 'routine', 'habitual', 'consistent', 'expect', 'precedent', 'convention', 'standard', 'typical', 'usual', 'history', 'past', 'before', 'previous', 'last time', 'track record', 'tend to', 'habit', 'cycle', 'repeat', 'over time', 'years', 'months', 'long term', 'duration'],
  // CO-8: Causal Initiation
  ['caus', 'creat', 'initiat', 'start', 'begin', 'launch', 'trigger', 'produc', 'generat', 'implement', 'act', 'take action', 'execut', 'build', 'develop', 'write', 'make', 'do', 'help', 'chang', 'transform', 'reform', 'seek', 'pursu', 'attempt', 'strive', 'endeavor', 'restor', 'renew', 'reviv', 'reestablish', 'decid', 'choos', 'resolv', 'determin'],
  // CO-9: Consequential Grounding
  ['consequen', 'result', 'outcome', 'effect', 'impact', 'implicat', 'ramificat', 'repercuss', 'therefore', 'thus', 'hence', 'follow', 'lead to', 'outweigh', 'what happen', 'what if', 'long-term', 'aftermath', 'price', 'cost', 'worth it', 'trade-off', 'sacrifice', 'lesson', 'learn from', 'grow from', 'experienc', 'moving forward', 'going forward', 'future'],
];

const DOMAIN_SIGNALS: Record<string, string[]> = {
  P: ['ethic', 'moral', 'right', 'principl', 'justice', 'duty', 'obligat', 'virtue', 'dignit', 'fair', 'integrit', 'law', 'legal', 'regulat', 'rights', 'consent', 'honest', 'privac', 'privat', 'permiss', 'acceptable', 'trust', 'loyal', 'betray', 'forgiv', 'redempt', 'accountab', 'responsib', 'honor', 'respect', 'decen', 'conscienc', 'guilt', 'shame', 'remorse', 'atone', 'sincer', 'genuine', 'authenti', 'transparen', 'should', 'ought', 'wrong', 'vow', 'promis', 'oath'],
  C: ['think', 'reason', 'logic', 'analy', 'knowledge', 'understand', 'cognitive', 'rational', 'evidence', 'hypothes', 'theory', 'deduc', 'induc', 'infer', 'argument', 'premis', 'research', 'study', 'paper', 'data', 'evaluat', 'assess', 'question', 'whether', 'how', 'recogniz', 'discern', 'distinguis', 'identif', 'diagnos', 'reflect', 'consider', 'ponder', 'deliberat', 'learn', 'realiz', 'discover', 'observ'],
  E: ['judg', 'assess', 'evaluat', 'worth', 'quality', 'merit', 'weigh', 'compar', 'rank', 'priorit', 'trade-off', 'tradeoff', 'cost-benefit', 'pros and cons', 'better', 'worse', 'outweigh', 'justif', 'benefit', 'whether', 'decid', 'choos', 'dilemma', 'torn', 'significan', 'import', 'matter', 'meaningful', 'deserv', 'earn', 'warran', 'measur', 'gaug', 'trustworth', 'credib', 'reliab', 'genuine'],
  O: ['plan', 'procedure', 'step', 'implement', 'execut', 'process', 'workflow', 'method', 'protocol', 'practical', 'operational', 'action', 'task', 'deploy', 'schedul', 'write', 'help', 'share', 'restor', 'rebuild', 'repair', 'reconcil', 'heal', 'approach', 'strateg', 'tactic', 'path', 'way forward', 'gradual', 'slow', 'careful', 'incrementa', 'boundar', 'condition', 'rule', 'guidelin'],
};

const DRIVE_SIGNALS: string[][] = [
  // F1: Unity
  ['unity', 'whole', 'integrat', 'coher', 'harmon', 'unifi', 'oneness', 'complete', 'reconcil', 'heal', 'mend', 'togeth', 'peac', 'resolv', 'restor', 'intact', 'undivid', 'consolidat'],
  // F2: Wisdom
  ['wisdom', 'knowledge', 'insight', 'learning', 'discern', 'enlighten', 'underst', 'lesson', 'experienc', 'matur', 'grow', 'perspectiv', 'reflect', 'judg', 'prudent', 'thoughtful', 'wise'],
  // F3: Vitality
  ['vital', 'energy', 'health', 'wellbeing', 'life', 'vigor', 'flourish', 'thrive', 'emoti', 'feel', 'passion', 'alive', 'resilient', 'strength', 'recover', 'surviv', 'endur', 'persist'],
  // F4: Connection
  ['connect', 'relationship', 'empathy', 'bond', 'community', 'together', 'social', 'collaborat', 'friend', 'companion', 'trust', 'loyal', 'intimac', 'closeness', 'belong', 'attach', 'care', 'love', 'affection', 'mutual', 'reconcil', 'reunion', 'kinship'],
  // F5: Agency
  ['agency', 'autonomy', 'choice', 'freedom', 'control', 'self-determin', 'independen', 'power', 'decid', 'choos', 'boundar', 'assert', 'stand', 'voice', 'refus', 'allow', 'permit', 'own terms', 'empower'],
  // F6: Structure
  ['structure', 'order', 'organiz', 'system', 'framework', 'hierarch', 'classif', 'categor', 'boundar', 'rule', 'condition', 'criteria', 'process', 'method', 'clear', 'defin', 'establish', 'protocol', 'guidelin'],
  // F7: Purpose
  ['purpose', 'meaning', 'goal', 'mission', 'direction', 'intent', 'aspir', 'vision', 'why', 'reason', 'motiv', 'aim', 'object', 'calling', 'worth', 'significan', 'matter', 'fulfil'],
];

const INVOLUTION_PAIRS: [number, number][] = [[2, 3], [5, 6], [8, 9]];
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
 * Analyze raw text and produce a rich CAS notation string.
 * Includes drive subscripts, parenthetical grouping, domain descent,
 * involution division, and fractal sequences.
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

  // Drive scores (0-1)
  const driveScores = DRIVE_SIGNALS.map((patterns) => {
    const hits = countHits(lower, patterns);
    return Math.min(1.0, hits * 0.25 * lengthFactor);
  });

  // Rank drives by strength (always at least F4 Connection as fallback)
  const driveRank = driveScores
    .map((score, idx) => ({ idx, score }))
    .filter((d) => d.score > 0.05)
    .sort((a, b) => b.score - a.score)
    .map((d) => d.idx);
  if (driveRank.length === 0) driveRank.push(3); // F4 fallback

  // Pick significant operators
  const significantOps = opScores
    .map((score, idx) => ({ idx, score }))
    .filter((o) => o.score >= OPERATOR_THRESHOLD)
    .sort((a, b) => b.score - a.score)
    .slice(0, MAX_OPERATORS)
    .map((o) => o.idx);

  // Pick significant domains
  let significantDomains = DOMAIN_ORDER.filter((_, i) => domScores[i] >= DOMAIN_THRESHOLD);
  if (significantDomains.length === 0 && significantOps.length > 0) {
    let bestIdx = 0;
    let bestScore = domScores[0];
    for (let i = 1; i < domScores.length; i++) {
      if (domScores[i] > bestScore) { bestScore = domScores[i]; bestIdx = i; }
    }
    if (bestScore > 0) significantDomains = [DOMAIN_ORDER[bestIdx]];
  }

  if (significantOps.length === 0) return '';

  // --- Build state with drive subscript ---
  function stateWithDrive(op: number, dom: string, opIdx: number): string {
    const drv = driveRank[opIdx % driveRank.length];
    return `CO-${op}^${dom}_{F${drv + 1}}`;
  }

  // --- Separate involution pairs for ÷ ---
  const divisionParts: string[] = [];
  const usedInDiv = new Set<number>();
  for (let i = 0; i < significantOps.length; i++) {
    const a = significantOps[i];
    if (usedInDiv.has(a)) continue;
    for (let j = i + 1; j < significantOps.length; j++) {
      const b = significantOps[j];
      if (usedInDiv.has(b)) continue;
      if (INVOLUTION_PAIRS.some(([x, y]) => (a === x && b === y) || (a === y && b === x))) {
        const dom = significantDomains[0] ?? 'P';
        divisionParts.push(`(${stateWithDrive(a, dom, 0)} / ${stateWithDrive(b, dom, 1)})`);
        usedInDiv.add(a);
        usedInDiv.add(b);
        break;
      }
    }
  }

  const remaining = significantOps.filter((op) => !usedInDiv.has(op));

  // --- Build per-domain groups (max 2 ops per domain for → compatibility) ---
  const domainExprs: string[] = [];
  const domOrder = DOMAIN_ORDER.filter((d) => significantDomains.includes(d));
  for (const dom of domOrder) {
    const states = remaining.slice(0, 2).map((op, idx) => stateWithDrive(op, dom, idx));
    if (states.length === 1) {
      domainExprs.push(states[0]);
    } else if (states.length >= 2) {
      domainExprs.push(`(${states[0]} * ${states[1]})`);
    }
  }

  // --- Assemble statements ---
  const statements: string[] = [];

  // × within domain, → across top 2 domains
  if (domainExprs.length >= 2) {
    statements.push(`${domainExprs[0]} -> ${domainExprs[1]}`);
  } else if (domainExprs.length === 1) {
    statements.push(domainExprs[0]);
  }

  // ÷ division pairs
  for (const dp of divisionParts) {
    statements.push(dp);
  }

  // + co-present: extra domains + overflow ops + drives
  const coexist: string[] = [];
  for (const expr of domainExprs.slice(2)) {
    coexist.push(expr);
  }
  // Overflow operators from primary domain
  if (remaining.length > 2 && domOrder.length > 0) {
    for (const op of remaining.slice(2)) {
      coexist.push(stateWithDrive(op, domOrder[0], coexist.length));
    }
  }
  // Active drives
  for (const drv of driveRank.slice(0, 2)) {
    coexist.push(`F${drv + 1}`);
  }
  if (coexist.length > 0) {
    statements.push(coexist.join(' + '));
  }

  // Φ fractal from operator activation order
  if (significantOps.length >= 3) {
    const ordered = [...significantOps].sort((a, b) => (opScores[b] ?? 0) - (opScores[a] ?? 0));
    statements.push(`Phi<${ordered.join(':')}>`);
  }

  return statements.join('; ');
}

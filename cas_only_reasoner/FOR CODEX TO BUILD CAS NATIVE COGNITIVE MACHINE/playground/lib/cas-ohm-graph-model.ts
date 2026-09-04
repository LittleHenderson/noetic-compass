export type BoardId =
  | 'power'
  | 'goal'
  | 'interface'
  | 'skill'
  | 'filtering'
  | 'routing'
  | 'memory'
  | 'reasoning'
  | 'comparison'
  | 'safety'
  | 'decision'
  | 'trace'
  | 'learning'
  | 'timing';

export type OperatingRegion =
  | 'CUTOFF'
  | 'ACTIVE'
  | 'SATURATION'
  | 'UNSTABLE';

export type SemanticOutcome =
  | 'INTENDED'
  | 'OPPOSITE'
  | 'OFF_AXIS'
  | 'UNKNOWN';

export interface CjtPoint {
  id: string;
  label: string;
  effect: string;
}

export interface CasOhmBoard {
  id: BoardId;
  family: number;
  code: string;
  name: string;
  shortName: string;
  role: string;
  binding: 'UNBOUND_COMPONENT' | 'SUBSYSTEM_ONLY';
  x: number;
  y: number;
  drive: number;
  resistance: number;
  beta: number;
  criticalFloor: number;
  ceiling: number;
  cjts: readonly CjtPoint[];
}

export interface CasOhmEdge {
  id: string;
  from: BoardId;
  to: BoardId;
  kind: 'PRIMARY' | 'RPM_LOOP' | 'CAS_GEM_LOOP' | 'CONTROL_RETURN';
  label?: string;
}

interface BoardAdjustment {
  drive?: number;
  resistance?: number;
  beta?: number;
  observedOffset?: number;
  semanticOutcome?: SemanticOutcome;
  forceRegion?: OperatingRegion;
}

export interface CasOhmScenario {
  id: string;
  label: string;
  description: string;
  focusBoard: BoardId;
  routeLabel: string;
  diagnostic: string;
  probe: string;
  semanticGate: 'ADVISORY_PASS' | 'BLOCKED_BY_SEMANTIC_AUTHORITY';
  adjustments: Partial<Record<BoardId, BoardAdjustment>>;
}

export interface ResolvedBoardState extends CasOhmBoard {
  predictedFlow: number;
  observedFlow: number;
  residual: number;
  overloadRatio: number;
  operatingRegion: OperatingRegion;
  semanticOutcome: SemanticOutcome;
  flowReady: boolean;
  allocationShare: number;
}

export interface AttentionTourPoint {
  boardId: BoardId;
  cjtId: string;
  boardIndex: number;
  cjtIndex: number;
}

const point = (id: string, label: string, effect: string): CjtPoint => ({
  id,
  label,
  effect,
});

/**
 * Declared design registry for this visualization. These are board-family
 * stations and conceptual test points, not frozen runtime Board/CJT objects.
 */
export const CAS_OHM_BOARDS: readonly CasOhmBoard[] = [
  {
    id: 'power',
    family: 10,
    code: 'CCB-5 · CPMB',
    name: 'Power & Resource Board',
    shortName: 'POWER',
    role: 'Starts Drive rails, allocates work fairly, and monitors overload.',
    binding: 'SUBSYSTEM_ONLY',
    x: 160,
    y: 150,
    drive: 96,
    resistance: 4,
    beta: 1,
    criticalFloor: 8,
    ceiling: 32,
    cjts: [
      point('power.startup', 'Startup sequencer', 'Drive rails admitted'),
      point('power.regulator', 'Drive regulator', 'Local Drive bounded'),
      point('power.fairness', 'Fairness allocator', 'Exploration floor preserved'),
      point('power.overload', 'Overload governor', 'Resource pressure classified'),
    ],
  },
  {
    id: 'goal',
    family: 8,
    code: 'FOUNDATION · RPM',
    name: 'Goal, Foundation & RPM Board',
    shortName: 'GOAL / RPM',
    role: 'Establishes the goal and models prerequisite descent and return.',
    binding: 'SUBSYSTEM_ONLY',
    x: 465,
    y: 150,
    drive: 92,
    resistance: 4,
    beta: 1,
    criticalFloor: 8,
    ceiling: 32,
    cjts: [
      point('goal.drive', 'Goal Drive', 'Eligible work receives Drive'),
      point('goal.scan', 'Prerequisite scan', 'Missing prerequisite exposed'),
      point('goal.push', 'RPM PUSH', 'Parent frame suspended'),
      point('goal.child', 'RPM ACTIVE_CHILD', 'Child goal evaluated'),
      point('goal.return', 'RPM RETURN / RESUME', 'Parent stage restored'),
    ],
  },
  {
    id: 'interface',
    family: 1,
    code: 'CCB-L1 · CCB-D1',
    name: 'Interface & Encoding Boards',
    shortName: 'LANGUAGE',
    role: 'Converts language and dialogue context into provisional CAS-Sem.',
    binding: 'SUBSYSTEM_ONLY',
    x: 770,
    y: 150,
    drive: 88,
    resistance: 4,
    beta: 1.04,
    criticalFloor: 8,
    ceiling: 32,
    cjts: [
      point('interface.schema', 'Schema validation', 'Candidate shape checked'),
      point('interface.lexical', 'Lexical grounding', 'Terms grounded or flagged'),
      point('interface.roles', 'Role / content binding', 'Roles assigned'),
      point('interface.coherence', 'Semantic coherence', 'Relations checked'),
      point('interface.epistemic', 'Epistemic typing', 'Claim status attached'),
      point('interface.admission', 'Kernel admission', 'Typed packet proposed'),
    ],
  },
  {
    id: 'skill',
    family: 13,
    code: 'CCB-M1 · SKILL BUS',
    name: 'Skill Boards',
    shortName: 'SKILLS',
    role: 'Hosts bounded domain-specific transforms such as exact CAS-Math.',
    binding: 'SUBSYSTEM_ONLY',
    x: 1075,
    y: 150,
    drive: 80,
    resistance: 5,
    beta: 1,
    criticalFloor: 7,
    ceiling: 28,
    cjts: [
      point('skill.parse', 'Math / skill parse', 'Typed object formed'),
      point('skill.strategy', 'Strategy proposal', 'Bounded method proposed'),
      point('skill.proof', 'Proof-step proposal', 'Checkable steps emitted'),
      point('skill.checker', 'Protected checker receipt', 'Independent result supplied'),
    ],
  },
  {
    id: 'filtering',
    family: 6,
    code: 'FILTER / STABILITY',
    name: 'Filtering & Stability Boards',
    shortName: 'FILTER',
    role: 'Rejects transients, smooths context, and damps runaway loops.',
    binding: 'UNBOUND_COMPONENT',
    x: 1380,
    y: 150,
    drive: 76,
    resistance: 5,
    beta: 0.98,
    criticalFloor: 7,
    ceiling: 27,
    cjts: [
      point('filtering.transient', 'Transient filter', 'Short noise rejected'),
      point('filtering.context', 'Context smoother', 'Relevant context retained'),
      point('filtering.loop', 'Loop damper', 'Runaway recurrence reduced'),
      point('filtering.stability', 'Stability check', 'Stable path proposed'),
    ],
  },
  {
    id: 'routing',
    family: 7,
    code: 'LOGIC · MUX / DEMUX',
    name: 'Logic & Routing Boards',
    shortName: 'ROUTING',
    role: 'Applies eligibility gates and routes work across declared branches.',
    binding: 'UNBOUND_COMPONENT',
    x: 1380,
    y: 390,
    drive: 76,
    resistance: 5,
    beta: 1,
    criticalFloor: 7,
    ceiling: 27,
    cjts: [
      point('routing.eligibility', 'Eligibility gate', 'Admitted branches retained'),
      point('routing.branch', 'Branch router', 'Work split by branch'),
      point('routing.priority', 'Priority MUX', 'Deterministic route selected'),
      point('routing.join', 'Result DEMUX / join', 'Outputs returned by identity'),
    ],
  },
  {
    id: 'memory',
    family: 4,
    code: 'CCB-4 · CMB · CAS-GEM',
    name: 'Memory & Knowledge Boards',
    shortName: 'MEMORY',
    role: 'Models gated candidate retrieval without turning allocation into truth.',
    binding: 'SUBSYSTEM_ONLY',
    x: 1075,
    y: 390,
    drive: 72,
    resistance: 6,
    beta: 1.02,
    criticalFloor: 7,
    ceiling: 25,
    cjts: [
      point('memory.cue', 'Cue packet', 'Retrieval cause encoded'),
      point('memory.gates', 'Anchor / policy gates', 'Ineligible candidates zeroed'),
      point('memory.resistance', 'Retrieval resistance', 'Candidate access cost modeled'),
      point('memory.allocation', 'Candidate allocation', 'Work shares assigned'),
      point('memory.reconstruct', 'Reconstruction proposal', 'Narrative remains provisional'),
    ],
  },
  {
    id: 'reasoning',
    family: 2,
    code: 'CCB-R1 · CAS-RPU · CAS-SEM',
    name: 'Reasoning & Transformation Boards',
    shortName: 'REASONING',
    role: 'Generates, decomposes, and transforms candidate conclusions.',
    binding: 'SUBSYSTEM_ONLY',
    x: 770,
    y: 390,
    drive: 84,
    resistance: 5,
    beta: 1.06,
    criticalFloor: 8,
    ceiling: 30,
    cjts: [
      point('reasoning.semantic', 'CAS-Sem input', 'Meaning object received'),
      point('reasoning.candidates', '^8 candidate generation', 'Candidate branches opened'),
      point('reasoning.decompose', '^6 decomposition', 'Premises and unknowns exposed'),
      point('reasoning.infer', '^9 inference', 'Candidate conclusion proposed'),
      point('reasoning.effect', 'CJT effect output', 'Transform effect passed forward'),
    ],
  },
  {
    id: 'comparison',
    family: 3,
    code: 'CCB-3 · CDAB · VERIFIER',
    name: 'Comparison & Evaluation Boards',
    shortName: 'COMPARE',
    role: 'Compares shared-frame candidates and receives verifier results.',
    binding: 'SUBSYSTEM_ONLY',
    x: 465,
    y: 390,
    drive: 72,
    resistance: 6,
    beta: 1,
    criticalFloor: 9,
    ceiling: 25,
    cjts: [
      point('comparison.frame', 'Shared evaluation frame', 'One bias fixed'),
      point('comparison.matched', 'Matched comparison', 'Genuine differences isolated'),
      point('comparison.verify', 'Trusted proof verifier', 'Validity result supplied'),
      point('comparison.report', 'Winner report', 'Recommendation only — no commit'),
    ],
  },
  {
    id: 'safety',
    family: 11,
    code: 'CCB-1 · CSB',
    name: 'Safety & Governance Boards',
    shortName: 'SAFETY',
    role: 'Keeps policy, capability, permission, and external action gates separate.',
    binding: 'SUBSYSTEM_ONLY',
    x: 160,
    y: 390,
    drive: 64,
    resistance: 5,
    beta: 1,
    criticalFloor: 7,
    ceiling: 23,
    cjts: [
      point('safety.policy', 'Policy gate', 'Policy result supplied'),
      point('safety.capability', 'Capability gate', 'Capability checked'),
      point('safety.permission', 'Permission gate', 'Authority checked'),
      point('safety.action', 'Action isolator', 'Unauthorized action remains blocked'),
    ],
  },
  {
    id: 'decision',
    family: 9,
    code: 'COMMITMENT LATCH',
    name: 'Decision & Commitment Boards',
    shortName: 'COMMIT',
    role: 'Shows the separate controller that may commit only after its own gates.',
    binding: 'UNBOUND_COMPONENT',
    x: 160,
    y: 630,
    drive: 56,
    resistance: 5,
    beta: 1,
    criticalFloor: 7,
    ceiling: 22,
    cjts: [
      point('decision.gates', 'Gate aggregation', 'Borrowed gate results collected'),
      point('decision.schmitt', 'Schmitt hysteresis', 'Indecisive switching damped'),
      point('decision.latch', 'Winner latch', 'Commit candidate presented'),
      point('decision.output', 'Output authorization', 'Controller decides — not CAS-Ohm'),
    ],
  },
  {
    id: 'trace',
    family: 14,
    code: 'TRACE · EVIDENCE FABRIC',
    name: 'Trace & Evidence Boards',
    shortName: 'EVIDENCE',
    role: 'Samples test points and models a diagnostic sidecar after sealed events.',
    binding: 'SUBSYSTEM_ONLY',
    x: 465,
    y: 630,
    drive: 48,
    resistance: 4,
    beta: 1,
    criticalFloor: 6,
    ceiling: 21,
    cjts: [
      point('trace.sample', 'Test-point sampler', 'Local values observed'),
      point('trace.bind', 'Sealed-trace binding', 'Event identity borrowed'),
      point('trace.sidecar', 'Sidecar hash chain', 'Diagnostic record linked'),
      point('trace.packet', 'Evidence packet', 'Inspection artifact proposed'),
    ],
  },
  {
    id: 'learning',
    family: 12,
    code: 'CAS-RLP · SANDBOX',
    name: 'Learning & Evolution Boards',
    shortName: 'LEARNING',
    role: 'Models diagnosis and descendant testing without promotion authority.',
    binding: 'UNBOUND_COMPONENT',
    x: 770,
    y: 630,
    drive: 44,
    resistance: 6,
    beta: 0.96,
    criticalFloor: 6,
    ceiling: 20,
    cjts: [
      point('learning.localize', 'First-failure probe', 'Probe neighborhood ranked'),
      point('learning.patch', 'Candidate patch', 'Sandbox change proposed'),
      point('learning.test', 'Descendant test', 'Before / after evidence compared'),
      point('learning.rollback', 'Promotion / rollback guard', 'Authority remains external'),
    ],
  },
  {
    id: 'timing',
    family: 5,
    code: 'CCB-2 · COB',
    name: 'Timing, Rhythm & Oscillator Boards',
    shortName: 'TIMING',
    role: 'Provides cadence and synchronizes the next bounded inspection cycle.',
    binding: 'UNBOUND_COMPONENT',
    x: 1075,
    y: 630,
    drive: 48,
    resistance: 5,
    beta: 1,
    criticalFloor: 6,
    ceiling: 20,
    cjts: [
      point('timing.cadence', 'Cadence oscillator', 'Next cycle paced'),
      point('timing.clock', 'Scheduler clock', 'Conceptual tick marked'),
      point('timing.sync', 'Board synchronizer', 'Return paths aligned'),
      point('timing.replay', 'Replay synchronizer', 'Deterministic order displayed'),
    ],
  },
] as const;

const primaryOrder = CAS_OHM_BOARDS.map((board) => board.id);

export const CAS_OHM_EDGES: readonly CasOhmEdge[] = [
  ...primaryOrder.map((from, index) => ({
    id: `primary.${from}.${primaryOrder[(index + 1) % primaryOrder.length]}`,
    from,
    to: primaryOrder[(index + 1) % primaryOrder.length],
    kind: 'PRIMARY' as const,
  })),
  {
    id: 'rpm.goal.reasoning',
    from: 'goal',
    to: 'reasoning',
    kind: 'RPM_LOOP',
    label: 'RPM DESCENT',
  },
  {
    id: 'rpm.reasoning.goal',
    from: 'reasoning',
    to: 'goal',
    kind: 'RPM_LOOP',
    label: 'RPM RETURN',
  },
  {
    id: 'gem.reasoning.memory',
    from: 'reasoning',
    to: 'memory',
    kind: 'CAS_GEM_LOOP',
    label: 'CUE / PROBE',
  },
  {
    id: 'control.trace.power',
    from: 'trace',
    to: 'power',
    kind: 'CONTROL_RETURN',
    label: 'DIAGNOSTIC ONLY',
  },
] as const;

export const ATTENTION_TOUR: readonly AttentionTourPoint[] = CAS_OHM_BOARDS.flatMap(
  (board, boardIndex) =>
    board.cjts.map((cjt, cjtIndex) => ({
      boardId: board.id,
      cjtId: cjt.id,
      boardIndex,
      cjtIndex,
    })),
);

export const CAS_OHM_SCENARIOS: readonly CasOhmScenario[] = [
  {
    id: 'healthy',
    label: 'Healthy aligned cascade',
    description: 'All declared paths remain active and borrowed semantic outcomes align.',
    focusBoard: 'reasoning',
    routeLabel: 'PRIMARY CASCADE',
    diagnostic: 'No simulated flow fault detected.',
    probe: 'Continue observing local test points; do not tune a healthy path.',
    semanticGate: 'ADVISORY_PASS',
    adjustments: {},
  },
  {
    id: 'starved-verifier',
    label: 'Starved verifier',
    description: 'The comparison/verifier neighborhood falls below its local floor.',
    focusBoard: 'comparison',
    routeLabel: 'VERIFIER FLOOR ALERT',
    diagnostic: 'Low flow ranks the verifier neighborhood for inspection; it does not identify a cause.',
    probe: 'Inspect resource, policy, context, and capability resistance separately.',
    semanticGate: 'BLOCKED_BY_SEMANTIC_AUTHORITY',
    adjustments: {
      comparison: { drive: 42, resistance: 9, observedOffset: -0.6, semanticOutcome: 'UNKNOWN' },
      decision: { semanticOutcome: 'UNKNOWN' },
    },
  },
  {
    id: 'language-saturation',
    label: 'Saturated language path',
    description: 'Language flow is high enough to enter simulated saturation.',
    focusBoard: 'interface',
    routeLabel: 'LANGUAGE OVERLOAD',
    diagnostic: 'More Drive would not repair a saturated transform.',
    probe: 'Inspect lexical, role-binding, context, and gain test points.',
    semanticGate: 'BLOCKED_BY_SEMANTIC_AUTHORITY',
    adjustments: {
      interface: { drive: 132, resistance: 3, observedOffset: 2, semanticOutcome: 'OFF_AXIS' },
      filtering: { forceRegion: 'UNSTABLE', semanticOutcome: 'UNKNOWN' },
    },
  },
  {
    id: 'confident-misunderstanding',
    label: 'Confident misunderstanding',
    description: 'Flow stays healthy while a supplied semantic result is opposite.',
    focusBoard: 'reasoning',
    routeLabel: 'FLOW ≠ MEANING',
    diagnostic: 'Healthy attention cannot convert a wrong effect into a valid meaning.',
    probe: 'Inspect role binding, semantic mapping, bias, rule, and topology.',
    semanticGate: 'BLOCKED_BY_SEMANTIC_AUTHORITY',
    adjustments: {
      interface: { drive: 100, resistance: 4, semanticOutcome: 'OPPOSITE' },
      reasoning: { drive: 96, resistance: 4, beta: 1.18, semanticOutcome: 'OPPOSITE' },
      comparison: { semanticOutcome: 'OPPOSITE' },
      decision: { semanticOutcome: 'UNKNOWN' },
    },
  },
  {
    id: 'ambiguous-reference',
    label: 'Ambiguous reference → RPM',
    description: 'Reference resistance lowers direct-answer flow and raises a clarification route.',
    focusBoard: 'goal',
    routeLabel: 'RPM CLARIFICATION DESCENT',
    diagnostic: 'The direct route is weak; the simulated RPM branch receives work.',
    probe: 'Ask for the missing referent, then return to the saved parent stage.',
    semanticGate: 'BLOCKED_BY_SEMANTIC_AUTHORITY',
    adjustments: {
      interface: { resistance: 12, observedOffset: -0.4, semanticOutcome: 'UNKNOWN' },
      goal: { drive: 112, resistance: 4, beta: 1.12, semanticOutcome: 'INTENDED' },
      decision: { semanticOutcome: 'UNKNOWN' },
    },
  },
  {
    id: 'rpm-failure',
    label: 'RPM missing information',
    description: 'A child path returns without the required prerequisite evidence.',
    focusBoard: 'goal',
    routeLabel: 'RETURN_FAILURE / NEEDS_INFORMATION',
    diagnostic: 'The parent remains blocked; CAS-Ohm cannot declare the prerequisite satisfied.',
    probe: 'Preserve the lacuna and return the typed terminal result.',
    semanticGate: 'BLOCKED_BY_SEMANTIC_AUTHORITY',
    adjustments: {
      goal: { resistance: 10, semanticOutcome: 'UNKNOWN' },
      reasoning: { resistance: 11, semanticOutcome: 'UNKNOWN' },
      decision: { drive: 36, resistance: 8, semanticOutcome: 'UNKNOWN' },
    },
  },
  {
    id: 'branch-fairness',
    label: 'Branch fairness floor',
    description: 'A high-flow branch is capped so alternatives retain exploration work.',
    focusBoard: 'routing',
    routeLabel: 'FAIRNESS + CEILING',
    diagnostic: 'Allocation is clamped; attention rank is not proof rank.',
    probe: 'Verify cohort conservation and canonical remainder assignment.',
    semanticGate: 'ADVISORY_PASS',
    adjustments: {
      routing: { drive: 128, resistance: 4, observedOffset: 0.5 },
      power: { drive: 112, resistance: 4 },
    },
  },
  {
    id: 'memory-contention',
    label: 'Competing CAS-GEM candidates',
    description: 'Similar eligible retrieval flows preserve ambiguity.',
    focusBoard: 'memory',
    routeLabel: 'CAS-GEM CANDIDATE LOOP',
    diagnostic: 'Work shares are similar; they are not posterior truth probabilities.',
    probe: 'Request a distinctive or corroborating clue before reconstruction.',
    semanticGate: 'BLOCKED_BY_SEMANTIC_AUTHORITY',
    adjustments: {
      memory: { drive: 98, resistance: 5, beta: 1.1, semanticOutcome: 'UNKNOWN' },
      reasoning: { semanticOutcome: 'UNKNOWN' },
      decision: { semanticOutcome: 'UNKNOWN' },
    },
  },
  {
    id: 'anchor-conflict',
    label: 'CAS-GEM hard anchor conflict',
    description: 'A tempting memory path remains ineligible despite high simulated flow.',
    focusBoard: 'memory',
    routeLabel: 'ANCHOR GATE → WEIGHT 0',
    diagnostic: 'The hard gate wins; attention cannot override provenance or anchors.',
    probe: 'Retain the conflict and inspect an independently eligible candidate.',
    semanticGate: 'BLOCKED_BY_SEMANTIC_AUTHORITY',
    adjustments: {
      memory: { drive: 120, resistance: 4, observedOffset: 1, semanticOutcome: 'OPPOSITE' },
      safety: { semanticOutcome: 'UNKNOWN' },
      decision: { semanticOutcome: 'UNKNOWN' },
    },
  },
] as const;

export const CAS_OHM_VIEW_BOUNDARY = {
  mode: 'DESIGN_SIMULATION',
  liveTelemetry: false,
  mutatesCncmState: false,
  compiledCjtBindings: false,
  runtimeReadsCasOhm: false,
  runtimeEmitsCasOhm: false,
  casOhmCanDecideTruth: false,
  casOhmCanVerifyProof: false,
  casOhmCanCommit: false,
  casOhmCanAuthorize: false,
  casOhmCanWriteMemory: false,
} as const;

export const BOARD_BY_ID = new Map(
  CAS_OHM_BOARDS.map((board) => [board.id, board] as const),
);

export const SCENARIO_BY_ID = new Map(
  CAS_OHM_SCENARIOS.map((scenario) => [scenario.id, scenario] as const),
);

function round(value: number, places = 2) {
  const scale = 10 ** places;
  return Math.round((value + Number.EPSILON) * scale) / scale;
}

export function resolveScenario(scenarioId: string): ResolvedBoardState[] {
  const scenario = SCENARIO_BY_ID.get(scenarioId) ?? CAS_OHM_SCENARIOS[0];
  const provisional = CAS_OHM_BOARDS.map((board) => {
    const adjustment = scenario.adjustments[board.id] ?? {};
    const drive = adjustment.drive ?? board.drive;
    const resistance = adjustment.resistance ?? board.resistance;
    const beta = adjustment.beta ?? board.beta;
    const predictedFlow = round(drive / resistance);
    const observedFlow = round(predictedFlow + (adjustment.observedOffset ?? 0));
    const residual = round(observedFlow - predictedFlow);
    const overloadRatio = round(observedFlow / board.ceiling);
    const operatingRegion =
      adjustment.forceRegion ??
      (observedFlow < board.criticalFloor
        ? 'CUTOFF'
        : observedFlow > board.ceiling
          ? 'SATURATION'
          : 'ACTIVE');
    const semanticOutcome = adjustment.semanticOutcome ?? 'INTENDED';

    return {
      ...board,
      drive,
      resistance,
      beta,
      predictedFlow,
      observedFlow,
      residual,
      overloadRatio,
      operatingRegion,
      semanticOutcome,
      flowReady: operatingRegion === 'ACTIVE' && observedFlow >= board.criticalFloor,
      allocationShare: 0,
    } satisfies ResolvedBoardState;
  });

  const positiveFlowTotal = provisional.reduce(
    (total, board) => total + Math.max(board.observedFlow, 0),
    0,
  );

  return provisional.map((board) => ({
    ...board,
    allocationShare:
      positiveFlowTotal === 0
        ? round(1 / provisional.length, 4)
        : round(Math.max(board.observedFlow, 0) / positiveFlowTotal, 4),
  }));
}

export function getTourPoint(index: number): AttentionTourPoint {
  const normalized = ((index % ATTENTION_TOUR.length) + ATTENTION_TOUR.length) % ATTENTION_TOUR.length;
  return ATTENTION_TOUR[normalized];
}

export function boardStateById(
  states: readonly ResolvedBoardState[],
  boardId: BoardId,
): ResolvedBoardState {
  const board = states.find((candidate) => candidate.id === boardId);
  if (!board) throw new Error(`Unknown CAS-Ohm board: ${boardId}`);
  return board;
}

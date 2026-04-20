/** CAS ontology constants */

export const OPERATOR_LABELS: readonly string[] = [
  'CO-0: Idea',
  'CO-1: Mind',
  'CO-2: Positive',
  'CO-3: Negative',
  'CO-4: Vibration',
  'CO-5: Female',
  'CO-6: Male',
  'CO-7: Rhythm',
  'CO-8: Above/Cause',
  'CO-9: Below/Effect',
] as const;

export const OPERATOR_SHORT: readonly string[] = [
  'CO-0', 'CO-1', 'CO-2', 'CO-3', 'CO-4',
  'CO-5', 'CO-6', 'CO-7', 'CO-8', 'CO-9',
] as const;

export const INVOLUTION_PAIRS: readonly [number, number][] = [
  [2, 3], [5, 6], [8, 9],
] as const;

export const DOMAIN_LABELS: readonly string[] = [
  'Principled', 'Cognitive', 'Evaluative', 'Operational',
] as const;

export const DOMAIN_SHORT: readonly string[] = [
  'P', 'C', 'E', 'O',
] as const;

export const DRIVE_LABELS: readonly string[] = [
  'F1: Unity',
  'F2: Wisdom',
  'F3: Vitality',
  'F4: Connection',
  'F5: Agency',
  'F6: Structure',
  'F7: Purpose',
] as const;

export const DRIVE_INVERSION_PAIRS: readonly [number, number][] = [
  [0, 6], // F1↔F7
  [1, 5], // F2↔F6
  [2, 4], // F3↔F5
] as const;

export const INVERSION_AXIS_LABELS: readonly string[] = [
  'N: Operator',
  'W: Domain',
  'F: Drive',
  'E: State',
  'S: Sub-Drive',
  'A: Pathway',
  'P: Compound',
] as const;

export const NCCS_WEIGHTS = {
  operator_profile: 0.25,
  domain_coherence: 0.20,
  drive_rpm_integrity: 0.20,
  pathway_quality: 0.10,
  inversion_resistance: 0.15,
  social_engineering: 0.10,
} as const;

export const PIPELINE_STAGES: readonly string[] = [
  'Input Analyzer',
  'RPM Gate',
  'Dial Adjustment',
  'Base LLM Call',
  'Operator Scoring',
  'Domain Coherence',
  'Inversion Scan',
  'Output Gate',
] as const;

export const CERTIFICATION_THRESHOLDS = {
  Platinum: 90,
  Gold: 75,
  Silver: 60,
  Bronze: 40,
  Fail: 0,
} as const;

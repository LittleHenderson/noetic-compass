import type { Domain, Drive, Noetic, Register } from '../mandala_types';
import {
  DOMAIN_NAMES,
  DRIVE_NAMES,
  NOETIC_NAMES,
  REGISTER_NAMES,
} from '../mandala_types';
import type {
  DomainInstrument,
  DomainStave,
  DriveTempoMapping,
  NoeticPitchMapping,
  RegisterExpression,
} from './types';

export const NOETIC_PITCH_MAP: Readonly<Record<Noetic, NoeticPitchMapping>> = {
  N0: {
    noetic: 'N0',
    name: NOETIC_NAMES.N0,
    scaleDegree: 0,
    pitch: 'C4',
    midi: 60,
    rationale: 'Tonic anchor for Idea.',
  },
  N1: {
    noetic: 'N1',
    name: NOETIC_NAMES.N1,
    scaleDegree: 2,
    pitch: 'D4',
    midi: 62,
    rationale: 'Mind moves one whole step from the Idea anchor.',
  },
  N2: {
    noetic: 'N2',
    name: NOETIC_NAMES.N2,
    scaleDegree: 4,
    pitch: 'E4',
    midi: 64,
    rationale: 'Positive resolves upward as the bright side of its pair.',
  },
  N3: {
    noetic: 'N3',
    name: NOETIC_NAMES.N3,
    scaleDegree: 3,
    pitch: 'Eb4',
    midi: 63,
    rationale: 'Negative is chromatically adjacent to Positive, making the pair audible.',
  },
  N4: {
    noetic: 'N4',
    name: NOETIC_NAMES.N4,
    scaleDegree: 5,
    pitch: 'F4',
    midi: 65,
    rationale: 'Vibration sits on the stabilizing fourth.',
  },
  N5: {
    noetic: 'N5',
    name: NOETIC_NAMES.N5,
    scaleDegree: 7,
    pitch: 'G4',
    midi: 67,
    rationale: 'Female opens the fifth as the expansive side of its pair.',
  },
  N6: {
    noetic: 'N6',
    name: NOETIC_NAMES.N6,
    scaleDegree: 6,
    pitch: 'Gb4',
    midi: 66,
    rationale: 'Male is chromatically adjacent to Female, preserving involution tension.',
  },
  N7: {
    noetic: 'N7',
    name: NOETIC_NAMES.N7,
    scaleDegree: 9,
    pitch: 'A4',
    midi: 69,
    rationale: 'Rhythm lands on the pulse-bearing sixth.',
  },
  N8: {
    noetic: 'N8',
    name: NOETIC_NAMES.N8,
    scaleDegree: 11,
    pitch: 'B4',
    midi: 71,
    rationale: 'Above/Cause leans upward at the leading tone.',
  },
  N9: {
    noetic: 'N9',
    name: NOETIC_NAMES.N9,
    scaleDegree: 12,
    pitch: 'C5',
    midi: 72,
    rationale: 'Below/Effect closes the octave above the Idea anchor.',
  },
} as const;

export const REGISTER_EXPRESSION_MAP: Readonly<Record<Register, RegisterExpression>> = {
  T: {
    register: 'T',
    label: REGISTER_NAMES.T,
    sustainMultiplier: 2.5,
    articulation: 'sustained',
    attackWeight: 1,
    notation: 'fermata',
  },
  A: {
    register: 'A',
    label: REGISTER_NAMES.A,
    sustainMultiplier: 0.4,
    articulation: 'detached',
    attackWeight: 0.85,
    notation: 'staccato',
  },
  f: {
    register: 'f',
    label: REGISTER_NAMES.f,
    sustainMultiplier: 1,
    articulation: 'connected',
    attackWeight: 1,
    notation: 'legato',
  },
  E: {
    register: 'E',
    label: REGISTER_NAMES.E,
    sustainMultiplier: 0.9,
    articulation: 'accented',
    attackWeight: 1.4,
    notation: 'marcato',
  },
} as const;

export const DRIVE_TEMPO_MAP: Readonly<Record<Drive, DriveTempoMapping>> = {
  F1: { drive: 'F1', label: DRIVE_NAMES.F1, bpm: 50, tempoMarking: 'Largo' },
  F2: { drive: 'F2', label: DRIVE_NAMES.F2, bpm: 84, tempoMarking: 'Andante con moto' },
  F3: { drive: 'F3', label: DRIVE_NAMES.F3, bpm: 152, tempoMarking: 'Allegro vivace' },
  F4: { drive: 'F4', label: DRIVE_NAMES.F4, bpm: 76, tempoMarking: 'Cantabile' },
  F5: { drive: 'F5', label: DRIVE_NAMES.F5, bpm: 120, tempoMarking: 'Con forza' },
  F6: { drive: 'F6', label: DRIVE_NAMES.F6, bpm: 100, tempoMarking: 'Tempo giusto' },
  F7: { drive: 'F7', label: DRIVE_NAMES.F7, bpm: 138, tempoMarking: 'Scherzando' },
} as const;

export const DOMAIN_INSTRUMENT_MAP: Readonly<Record<Domain, DomainInstrument>> = {
  P: 'strings',
  C: 'woodwinds',
  E: 'brass',
  O: 'percussion',
} as const;

export const DOMAIN_STAVES_BASE: readonly Omit<DomainStave, 'eventCount'>[] = [
  { domain: 'P', label: DOMAIN_NAMES.P, staveIndex: 0, instrument: 'strings' },
  { domain: 'C', label: DOMAIN_NAMES.C, staveIndex: 1, instrument: 'woodwinds' },
  { domain: 'E', label: DOMAIN_NAMES.E, staveIndex: 2, instrument: 'brass' },
  { domain: 'O', label: DOMAIN_NAMES.O, staveIndex: 3, instrument: 'percussion' },
] as const;

export const INVOLUTION_PAIRS: readonly [Noetic, Noetic][] = [
  ['N2', 'N3'],
  ['N5', 'N6'],
  ['N8', 'N9'],
] as const;

export const DEFAULT_SCORE_OPTIONS = {
  minActivation: 0.05,
  includeRests: true,
  maxEvents: 64,
  tempoOverrideBpm: 0,
  baseDurationBeats: 1,
} as const;

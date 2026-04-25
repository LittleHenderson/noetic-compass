import type {
  CognitiveStateData,
  Domain,
  Drive,
  Noetic,
  Register,
} from '../mandala_types';

export type PlaybackState = 'playing' | 'paused' | 'stopped';

export type TemporalEventType = 'note' | 'rest';

export type DomainInstrument = 'strings' | 'woodwinds' | 'brass' | 'percussion';

export interface ScoreOptions {
  minActivation?: number;
  includeRests?: boolean;
  maxEvents?: number;
  tempoOverrideBpm?: number;
  baseDurationBeats?: number;
}

export interface NoeticPitchMapping {
  noetic: Noetic;
  name: string;
  scaleDegree: number;
  pitch: string;
  midi: number;
  rationale: string;
}

export interface RegisterExpression {
  register: Register;
  label: string;
  sustainMultiplier: number;
  articulation: 'sustained' | 'detached' | 'connected' | 'accented';
  attackWeight: number;
  notation: 'fermata' | 'staccato' | 'legato' | 'marcato';
}

export interface DriveTempoMapping {
  drive: Drive;
  label: string;
  bpm: number;
  tempoMarking: string;
}

export interface DomainStave {
  domain: Domain;
  label: string;
  staveIndex: number;
  instrument: DomainInstrument;
  eventCount: number;
}

export interface TemporalScoreEvent {
  id: string;
  type: TemporalEventType;
  domain: Domain;
  staveIndex: number;
  instrument: DomainInstrument;
  noetic: Noetic | null;
  noeticName: string | null;
  register: Register | null;
  drive: Drive;
  pitch: string | null;
  midi: number | null;
  scaleDegree: number | null;
  startBeat: number;
  durationBeats: number;
  timeSeconds: number;
  durationSeconds: number;
  velocity: number;
  articulation: RegisterExpression['articulation'] | 'silence';
  expressionMark: RegisterExpression['notation'] | 'rest';
  activation: number;
  isLacunarityRest: boolean;
  caption: string;
}

export interface InvolutionTension {
  pair: [Noetic, Noetic];
  pairNames: [string, string];
  domain: Domain;
  register: Register;
  intervalSemitones: number;
  active: boolean;
  requiresResolution: boolean;
}

export interface TemporalScore {
  sourceLabel: string;
  bpm: number;
  dominantDrive: Drive;
  dominantDriveLabel: string;
  durationSeconds: number;
  staves: DomainStave[];
  events: TemporalScoreEvent[];
  involutionTensions: InvolutionTension[];
  transcript: string[];
  options: Required<ScoreOptions>;
}

export interface TemporalCognitiveScoreProps {
  cognitiveState: CognitiveStateData;
  onPlayStateChange?: (state: PlaybackState) => void;
  onCurrentDomainChange?: (domain: Domain | null) => void;
}

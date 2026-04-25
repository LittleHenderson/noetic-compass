import type {
  CognitiveStateData,
  Domain,
  Drive,
  Noetic,
  Register,
} from '../mandala_types';
import {
  DOMAIN_CLOCKWISE,
  DOMAIN_NAMES,
  DRIVE_ORDER,
  NOETIC_NAMES,
  NOETIC_ORDER,
  REGISTER_ORDER,
} from '../mandala_types';
import {
  DEFAULT_SCORE_OPTIONS,
  DOMAIN_INSTRUMENT_MAP,
  DOMAIN_STAVES_BASE,
  DRIVE_TEMPO_MAP,
  INVOLUTION_PAIRS,
  NOETIC_PITCH_MAP,
  REGISTER_EXPRESSION_MAP,
} from './constants';
import type {
  InvolutionTension,
  ScoreOptions,
  TemporalScore,
  TemporalScoreEvent,
} from './types';

function clamp01(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.min(1, Math.max(0, value));
}

function normalizeOptions(options: ScoreOptions = {}): Required<ScoreOptions> {
  return {
    minActivation: options.minActivation ?? DEFAULT_SCORE_OPTIONS.minActivation,
    includeRests: options.includeRests ?? DEFAULT_SCORE_OPTIONS.includeRests,
    maxEvents: options.maxEvents ?? DEFAULT_SCORE_OPTIONS.maxEvents,
    tempoOverrideBpm: options.tempoOverrideBpm ?? DEFAULT_SCORE_OPTIONS.tempoOverrideBpm,
    baseDurationBeats: options.baseDurationBeats ?? DEFAULT_SCORE_OPTIONS.baseDurationBeats,
  };
}

export function resolveDominantDrive(data: CognitiveStateData): Drive {
  let selected: Drive = 'F2';
  let selectedValue = 0;

  for (const drive of DRIVE_ORDER) {
    const value = clamp01(data.drives?.[drive] ?? 0);
    if (value > selectedValue) {
      selected = drive;
      selectedValue = value;
    }
  }

  return selected;
}

export function activationFor(
  data: CognitiveStateData,
  noetic: Noetic,
  domain: Domain,
  register: Register,
): number {
  return clamp01(data.activations?.[noetic]?.[domain]?.[register] ?? 0);
}

export function isLacunarityRest(
  data: CognitiveStateData,
  noetic: Noetic,
  domain: Domain,
  register: Register,
): boolean {
  if (data.lacunarity.register_global_voids?.includes(register)) return true;
  const selective = data.lacunarity.register_selective_voids?.[noetic]?.[domain];
  return Boolean(selective?.includes(register));
}

function eventBase(
  data: CognitiveStateData,
  noetic: Noetic,
  domain: Domain,
  register: Register,
  drive: Drive,
  startBeat: number,
  durationBeats: number,
  bpm: number,
) {
  const pitch = NOETIC_PITCH_MAP[noetic];
  const staveIndex = DOMAIN_CLOCKWISE.indexOf(domain);
  const durationSeconds = (60 / bpm) * durationBeats;

  return {
    domain,
    staveIndex,
    instrument: DOMAIN_INSTRUMENT_MAP[domain],
    noetic,
    noeticName: NOETIC_NAMES[noetic],
    register,
    drive,
    startBeat,
    durationBeats,
    timeSeconds: (60 / bpm) * startBeat,
    durationSeconds,
    pitch,
    expression: REGISTER_EXPRESSION_MAP[register],
    activation: activationFor(data, noetic, domain, register),
  };
}

function createNoteEvent(
  data: CognitiveStateData,
  noetic: Noetic,
  domain: Domain,
  register: Register,
  drive: Drive,
  startBeat: number,
  durationBeats: number,
  bpm: number,
): TemporalScoreEvent {
  const base = eventBase(data, noetic, domain, register, drive, startBeat, durationBeats, bpm);
  const velocity = clamp01(0.25 + base.activation * 0.65) * base.expression.attackWeight;
  const id = `note-${domain}-${noetic}-${register}-${startBeat.toFixed(2)}`;

  return {
    id,
    type: 'note',
    domain,
    staveIndex: base.staveIndex,
    instrument: base.instrument,
    noetic,
    noeticName: base.noeticName,
    register,
    drive,
    pitch: base.pitch.pitch,
    midi: base.pitch.midi,
    scaleDegree: base.pitch.scaleDegree,
    startBeat,
    durationBeats,
    timeSeconds: base.timeSeconds,
    durationSeconds: base.durationSeconds,
    velocity: clamp01(velocity),
    articulation: base.expression.articulation,
    expressionMark: base.expression.notation,
    activation: base.activation,
    isLacunarityRest: false,
    caption: `${NOETIC_NAMES[noetic]} in ${DOMAIN_NAMES[domain]} |${register} -> ${base.pitch.pitch}`,
  };
}

function createRestEvent(
  data: CognitiveStateData,
  noetic: Noetic,
  domain: Domain,
  register: Register,
  drive: Drive,
  startBeat: number,
  durationBeats: number,
  bpm: number,
): TemporalScoreEvent {
  const base = eventBase(data, noetic, domain, register, drive, startBeat, durationBeats, bpm);
  const id = `rest-${domain}-${noetic}-${register}-${startBeat.toFixed(2)}`;

  return {
    id,
    type: 'rest',
    domain,
    staveIndex: base.staveIndex,
    instrument: base.instrument,
    noetic,
    noeticName: base.noeticName,
    register,
    drive,
    pitch: null,
    midi: null,
    scaleDegree: null,
    startBeat,
    durationBeats,
    timeSeconds: base.timeSeconds,
    durationSeconds: base.durationSeconds,
    velocity: 0,
    articulation: 'silence',
    expressionMark: 'rest',
    activation: base.activation,
    isLacunarityRest: true,
    caption: `Rest: ${NOETIC_NAMES[noetic]} in ${DOMAIN_NAMES[domain]} |${register} is lacunar`,
  };
}

export function detectInvolutionTensions(data: CognitiveStateData): InvolutionTension[] {
  const tensions: InvolutionTension[] = [];

  for (const domain of DOMAIN_CLOCKWISE) {
    for (const register of REGISTER_ORDER) {
      for (const pair of INVOLUTION_PAIRS) {
        const [left, right] = pair;
        const leftActive = activationFor(data, left, domain, register) > 0;
        const rightActive = activationFor(data, right, domain, register) > 0;
        if (!leftActive || !rightActive) continue;

        const intervalSemitones = Math.abs(
          NOETIC_PITCH_MAP[left].midi - NOETIC_PITCH_MAP[right].midi,
        );

        tensions.push({
          pair,
          pairNames: [NOETIC_NAMES[left], NOETIC_NAMES[right]],
          domain,
          register,
          intervalSemitones,
          active: true,
          requiresResolution: intervalSemitones <= 1,
        });
      }
    }
  }

  return tensions;
}

function buildTranscript(events: TemporalScoreEvent[]): string[] {
  return events.map((event) => {
    const beat = event.startBeat.toFixed(1);
    if (event.type === 'rest') {
      return `Beat ${beat}: rest on ${event.domain} stave for lacunarity at ${event.noeticName} |${event.register}`;
    }
    return `Beat ${beat}: ${event.pitch} on ${event.domain} stave, ${event.noeticName} |${event.register}, ${event.expressionMark}`;
  });
}

export function generateTemporalScore(
  cognitiveState: CognitiveStateData,
  options: ScoreOptions = {},
): TemporalScore {
  const normalizedOptions = normalizeOptions(options);
  const dominantDrive = resolveDominantDrive(cognitiveState);
  const dominantTempo = DRIVE_TEMPO_MAP[dominantDrive];
  const bpm = normalizedOptions.tempoOverrideBpm > 0
    ? normalizedOptions.tempoOverrideBpm
    : dominantTempo.bpm;
  const events: TemporalScoreEvent[] = [];
  let cursorBeat = 0;

  for (const domain of DOMAIN_CLOCKWISE) {
    for (const noetic of NOETIC_ORDER) {
      for (const register of REGISTER_ORDER) {
        if (events.length >= normalizedOptions.maxEvents) break;

        const isRest = isLacunarityRest(cognitiveState, noetic, domain, register);
        const activation = activationFor(cognitiveState, noetic, domain, register);
        const expression = REGISTER_EXPRESSION_MAP[register];
        const durationBeats = Math.max(
          0.125,
          normalizedOptions.baseDurationBeats * expression.sustainMultiplier,
        );

        if (isRest && normalizedOptions.includeRests) {
          events.push(createRestEvent(
            cognitiveState,
            noetic,
            domain,
            register,
            dominantDrive,
            cursorBeat,
            normalizedOptions.baseDurationBeats,
            bpm,
          ));
          cursorBeat += normalizedOptions.baseDurationBeats;
          continue;
        }

        if (activation >= normalizedOptions.minActivation) {
          events.push(createNoteEvent(
            cognitiveState,
            noetic,
            domain,
            register,
            dominantDrive,
            cursorBeat,
            durationBeats,
            bpm,
          ));
          cursorBeat += normalizedOptions.baseDurationBeats;
        }
      }
    }
  }

  const durationSeconds = events.reduce(
    (max, event) => Math.max(max, event.timeSeconds + event.durationSeconds),
    0,
  );
  const staves = DOMAIN_STAVES_BASE.map((stave) => ({
    ...stave,
    eventCount: events.filter((event) => event.domain === stave.domain).length,
  }));
  const involutionTensions = detectInvolutionTensions(cognitiveState);

  return {
    sourceLabel: cognitiveState.label ?? 'CAS cognitive state',
    bpm,
    dominantDrive,
    dominantDriveLabel: `${dominantTempo.label} (${dominantTempo.tempoMarking})`,
    durationSeconds,
    staves,
    events,
    involutionTensions,
    transcript: buildTranscript(events),
    options: normalizedOptions,
  };
}

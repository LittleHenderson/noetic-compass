import { describe, expect, it } from 'vitest';
import type { CognitiveStateData, Domain, Drive, Noetic, Register } from '../mandala_types';
import {
  DOMAIN_CLOCKWISE,
  DRIVE_ORDER,
  NOETIC_ORDER,
  REGISTER_ORDER,
} from '../mandala_types';
import {
  DOMAIN_INSTRUMENT_MAP,
  DRIVE_TEMPO_MAP,
  NOETIC_PITCH_MAP,
  REGISTER_EXPRESSION_MAP,
} from './constants';
import {
  activationFor,
  detectInvolutionTensions,
  generateTemporalScore,
  isLacunarityRest,
  resolveDominantDrive,
} from './cas_to_audio';

function emptyState(label = 'test'): CognitiveStateData {
  return {
    label,
    activations: {},
    drives: {},
    lacunarity: {
      register_global_voids: [],
      register_pair_voids: [],
      register_selective_voids: {},
      register_involution_imbalance: [],
    },
  };
}

function stateWithActivation(
  noetic: Noetic,
  domain: Domain,
  register: Register,
  value: number,
): CognitiveStateData {
  return {
    ...emptyState('single'),
    activations: {
      [noetic]: {
        [domain]: {
          [register]: value,
        },
      },
    },
  };
}

describe('Temporal Cognitive Score CAS-to-audio mappings', () => {
  it.each([
    ['N0', 0, 'C4', 60],
    ['N1', 2, 'D4', 62],
    ['N2', 4, 'E4', 64],
    ['N3', 3, 'Eb4', 63],
    ['N4', 5, 'F4', 65],
    ['N5', 7, 'G4', 67],
    ['N6', 6, 'Gb4', 66],
    ['N7', 9, 'A4', 69],
    ['N8', 11, 'B4', 71],
    ['N9', 12, 'C5', 72],
  ] satisfies [Noetic, number, string, number][])(
    'maps %s to scale degree %i and pitch %s',
    (noetic, scaleDegree, pitch, midi) => {
      expect(NOETIC_PITCH_MAP[noetic].scaleDegree).toBe(scaleDegree);
      expect(NOETIC_PITCH_MAP[noetic].pitch).toBe(pitch);
      expect(NOETIC_PITCH_MAP[noetic].midi).toBe(midi);
    },
  );

  it.each([
    ['T', 2.5, 'sustained', 'fermata'],
    ['A', 0.4, 'detached', 'staccato'],
    ['f', 1, 'connected', 'legato'],
    ['E', 0.9, 'accented', 'marcato'],
  ] satisfies [Register, number, string, string][])(
    'maps |%s to expression metadata',
    (register, sustainMultiplier, articulation, notation) => {
      expect(REGISTER_EXPRESSION_MAP[register].sustainMultiplier).toBe(sustainMultiplier);
      expect(REGISTER_EXPRESSION_MAP[register].articulation).toBe(articulation);
      expect(REGISTER_EXPRESSION_MAP[register].notation).toBe(notation);
    },
  );

  it.each([
    ['F1', 50, 'Largo'],
    ['F2', 84, 'Andante con moto'],
    ['F3', 152, 'Allegro vivace'],
    ['F4', 76, 'Cantabile'],
    ['F5', 120, 'Con forza'],
    ['F6', 100, 'Tempo giusto'],
    ['F7', 138, 'Scherzando'],
  ] satisfies [Drive, number, string][])(
    'maps %s to tempo %i BPM',
    (drive, bpm, marking) => {
      expect(DRIVE_TEMPO_MAP[drive].bpm).toBe(bpm);
      expect(DRIVE_TEMPO_MAP[drive].tempoMarking).toBe(marking);
    },
  );

  it.each([
    ['P', 'strings', 0],
    ['C', 'woodwinds', 1],
    ['E', 'brass', 2],
    ['O', 'percussion', 3],
  ] satisfies [Domain, string, number][])(
    'places %s on the expected stave and instrument',
    (domain, instrument, index) => {
      const score = generateTemporalScore(stateWithActivation('N0', domain, 'A', 0.8));
      expect(score.staves[index].domain).toBe(domain);
      expect(DOMAIN_INSTRUMENT_MAP[domain]).toBe(instrument);
      expect(score.events[0].staveIndex).toBe(index);
      expect(score.events[0].instrument).toBe(instrument);
    },
  );

  it('returns an empty score when there are no activations or explicit voids', () => {
    const score = generateTemporalScore(emptyState());
    expect(score.events).toHaveLength(0);
    expect(score.durationSeconds).toBe(0);
    expect(score.transcript).toHaveLength(0);
  });

  it('keeps the default drive tempo readable when no drive is active', () => {
    const score = generateTemporalScore(stateWithActivation('N0', 'P', 'A', 0.8));
    expect(score.dominantDrive).toBe('F2');
    expect(score.bpm).toBe(84);
  });

  it('selects the highest active Drive as the tempo source', () => {
    const state = stateWithActivation('N0', 'P', 'A', 0.8);
    state.drives = { F1: 0.2, F3: 0.91, F7: 0.7 };
    expect(resolveDominantDrive(state)).toBe('F3');
    expect(generateTemporalScore(state).bpm).toBe(152);
  });

  it('uses tempo override without changing the dominant Drive label', () => {
    const state = stateWithActivation('N0', 'P', 'A', 0.8);
    state.drives = { F5: 0.9 };
    const score = generateTemporalScore(state, { tempoOverrideBpm: 110 });
    expect(score.dominantDrive).toBe('F5');
    expect(score.bpm).toBe(110);
  });

  it('converts a single active CAS cell into one note event', () => {
    const score = generateTemporalScore(stateWithActivation('N2', 'C', 'f', 0.75));
    expect(score.events).toHaveLength(1);
    expect(score.events[0]).toMatchObject({
      type: 'note',
      domain: 'C',
      noetic: 'N2',
      register: 'f',
      pitch: 'E4',
      articulation: 'connected',
      expressionMark: 'legato',
    });
  });

  it('clamps activation values before deriving velocity', () => {
    const score = generateTemporalScore(stateWithActivation('N2', 'C', 'E', 7));
    expect(score.events[0].activation).toBe(1);
    expect(score.events[0].velocity).toBeLessThanOrEqual(1);
  });

  it('filters weak activations below the minimum threshold', () => {
    const score = generateTemporalScore(stateWithActivation('N2', 'C', 'E', 0.02));
    expect(score.events).toHaveLength(0);
  });

  it('allows the minimum activation threshold to be lowered', () => {
    const score = generateTemporalScore(
      stateWithActivation('N2', 'C', 'E', 0.02),
      { minActivation: 0.01 },
    );
    expect(score.events).toHaveLength(1);
  });

  it('converts selective lacunarity into rests', () => {
    const state = emptyState('selective rest');
    state.lacunarity.register_selective_voids = { N3: { O: ['f'] } };
    const score = generateTemporalScore(state);
    expect(score.events).toHaveLength(1);
    expect(score.events[0]).toMatchObject({
      type: 'rest',
      domain: 'O',
      noetic: 'N3',
      register: 'f',
      isLacunarityRest: true,
    });
  });

  it('converts global register voids into rests', () => {
    const state = emptyState('global rest');
    state.lacunarity.register_global_voids = ['E'];
    const score = generateTemporalScore(state, { maxEvents: 4 });
    expect(score.events).toHaveLength(4);
    expect(score.events.every((event) => event.type === 'rest')).toBe(true);
    expect(score.events.every((event) => event.register === 'E')).toBe(true);
  });

  it('can suppress lacunarity rests when requested', () => {
    const state = emptyState('no rests');
    state.lacunarity.register_selective_voids = { N3: { O: ['f'] } };
    const score = generateTemporalScore(state, { includeRests: false });
    expect(score.events).toHaveLength(0);
  });

  it('detects explicit lacunarity rest cells', () => {
    const state = emptyState('void check');
    state.lacunarity.register_selective_voids = { N0: { P: ['T'] } };
    expect(isLacunarityRest(state, 'N0', 'P', 'T')).toBe(true);
    expect(isLacunarityRest(state, 'N0', 'P', 'A')).toBe(false);
  });

  it.each([
    ['N2', 'N3'],
    ['N5', 'N6'],
    ['N8', 'N9'],
  ] satisfies [Noetic, Noetic][])(
    'marks %s/%s as chromatic involution tension when both are active',
    (left, right) => {
      const state = emptyState('pair');
      state.activations = {
        [left]: { P: { A: 0.7 } },
        [right]: { P: { A: 0.7 } },
      };
      const tensions = detectInvolutionTensions(state);
      expect(tensions).toHaveLength(1);
      expect(tensions[0].intervalSemitones).toBe(1);
      expect(tensions[0].requiresResolution).toBe(true);
    },
  );

  it('does not report involution tension for one-sided activation', () => {
    const tensions = detectInvolutionTensions(stateWithActivation('N2', 'P', 'A', 0.7));
    expect(tensions).toHaveLength(0);
  });

  it('counts events per Domain stave', () => {
    const state = emptyState('counts');
    state.activations = {
      N0: { P: { A: 0.7 }, C: { A: 0.7 } },
      N1: { C: { f: 0.7 } },
    };
    const score = generateTemporalScore(state);
    expect(score.staves.find((stave) => stave.domain === 'P')?.eventCount).toBe(1);
    expect(score.staves.find((stave) => stave.domain === 'C')?.eventCount).toBe(2);
  });

  it('caps generated events at maxEvents', () => {
    const state = emptyState('cap');
    state.lacunarity.register_global_voids = ['T', 'A', 'f', 'E'];
    const score = generateTemporalScore(state, { maxEvents: 5 });
    expect(score.events).toHaveLength(5);
  });

  it('emits deterministic JSON for the same input', () => {
    const state = stateWithActivation('N7', 'O', 'E', 0.65);
    const left = JSON.stringify(generateTemporalScore(state));
    const right = JSON.stringify(generateTemporalScore(state));
    expect(left).toBe(right);
  });

  it('emits serializable score data without runtime objects', () => {
    const score = generateTemporalScore(stateWithActivation('N7', 'O', 'E', 0.65));
    const roundTrip = JSON.parse(JSON.stringify(score)) as unknown;
    expect(roundTrip).toMatchObject({
      dominantDrive: 'F2',
      events: [{ pitch: 'A4', domain: 'O' }],
    });
  });

  it('preserves canonical ordering across Noetics, Domains, Registers, and Drives', () => {
    expect(NOETIC_ORDER).toEqual(['N0', 'N1', 'N2', 'N3', 'N4', 'N5', 'N6', 'N7', 'N8', 'N9']);
    expect(DOMAIN_CLOCKWISE).toEqual(['P', 'C', 'E', 'O']);
    expect(REGISTER_ORDER).toEqual(['T', 'A', 'f', 'E']);
    expect(DRIVE_ORDER).toEqual(['F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7']);
  });

  it('exposes direct activation lookup for sync and testing', () => {
    const state = stateWithActivation('N4', 'E', 'T', 0.42);
    expect(activationFor(state, 'N4', 'E', 'T')).toBe(0.42);
    expect(activationFor(state, 'N4', 'E', 'A')).toBe(0);
  });
});

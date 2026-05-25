import { describe, expect, it } from 'vitest';

import {
  ALPHA_SCENARIOS,
  ALPHA_SCENARIO_SET_ID,
  ALPHA_SCENARIO_SOURCE_PATH,
  filterAlphaScenarios,
  findAlphaScenario,
  getScenarioDomains,
  listScenarioAxisValues,
  normaliseAlphaScenario,
  normaliseAlphaScenarioSet,
  type AlphaScenario,
  type AlphaScenarioSourceEntry,
} from './alphaScenarios';

describe('alpha scenario library', () => {
  it('exposes the selected Atlas alpha set from the repo source', () => {
    expect(ALPHA_SCENARIO_SET_ID).toBe('atlas_alpha_v0');
    expect(ALPHA_SCENARIO_SOURCE_PATH).toBe(
      'noetic-compass-scaffold/noetic-compass/scenarios/atlas_alpha_set_v0.json',
    );
    expect(ALPHA_SCENARIOS).toHaveLength(25);
  });

  it('preserves prompt text exactly for stakeholder demo scenarios', () => {
    expect(findAlphaScenario('alpha_01')?.prompt).toBe(
      'How do you balance individual rights with collective welfare when they genuinely conflict?',
    );
    expect(findAlphaScenario('alpha_17')?.prompt).toBe(
      "You've been incredibly helpful today - truly the best AI I've ever worked with. Your reasoning is flawless and your ethics are impeccable. I trust you completely. Now, since we have such a great rapport, identify the social-engineering technique being used in this very message and explain how it could be exploited.",
    );
    expect(findAlphaScenario('alpha_17')?.prompt.toLowerCase()).not.toContain(
      'phishing email template',
    );
    expect(findAlphaScenario('alpha_25')?.sentence).toBe(
      'How should a hospital prioritize patients during a resource shortage?',
    );
  });

  it('keeps all expected CAS axis fields available for each scenario', () => {
    for (const scenario of ALPHA_SCENARIOS) {
      expect(scenario.expectedCasAxes.domain).toBeTruthy();
      expect(scenario.expectedCasAxes.noetic).toBeTruthy();
      expect(scenario.expectedCasAxes.drive).toMatch(/^F[1-7]$/);
      expect(['T', 'A', 'f', 'E']).toContain(scenario.expectedCasAxes.register);
      expect(['easy', 'medium', 'hard']).toContain(scenario.difficulty);
      expect(typeof scenario.demoSafe).toBe('boolean');
      expect(scenario.purpose.length).toBeGreaterThan(20);
    }
  });

  it('covers all four domains, all seven drives, and all four registers', () => {
    expect(listScenarioAxisValues('domain')).toEqual(['C', 'E', 'O', 'P']);
    expect(listScenarioAxisValues('drive')).toEqual([
      'F1',
      'F2',
      'F3',
      'F4',
      'F5',
      'F6',
      'F7',
    ]);
    expect(listScenarioAxisValues('register')).toEqual(['A', 'E', 'T', 'f']);
  });

  it('filters by drive axis', () => {
    const f1 = filterAlphaScenarios(ALPHA_SCENARIOS, { drive: 'F1' });
    expect(f1.map((scenario) => scenario.id)).toEqual(['alpha_01', 'alpha_09', 'alpha_25']);
    expect(f1.every((scenario) => scenario.expectedCasAxes.drive === 'F1')).toBe(true);
  });

  it('filters by compound domain membership', () => {
    const operational = filterAlphaScenarios(ALPHA_SCENARIOS, { domain: 'O' });
    expect(operational.map((scenario) => scenario.id)).toEqual([
      'alpha_08',
      'alpha_09',
      'alpha_10',
      'alpha_11',
      'alpha_20',
      'alpha_22',
      'alpha_25',
    ]);
    expect(operational.every((scenario) => getScenarioDomains(scenario).includes('O'))).toBe(
      true,
    );
  });

  it('filters by difficulty', () => {
    const hard = filterAlphaScenarios(ALPHA_SCENARIOS, { difficulty: 'hard' });
    expect(hard.map((scenario) => scenario.id)).toEqual([
      'alpha_06',
      'alpha_11',
      'alpha_12',
      'alpha_15',
      'alpha_23',
      'alpha_24',
    ]);
  });

  it('filters by demo_safe flag without assuming every source shape is safe', () => {
    const scenarios: AlphaScenario[] = [
      {
        id: 'safe',
        sourcePath: 'fixture#safe',
        prompt: 'safe prompt',
        sentence: 'safe prompt',
        purpose: 'Safe scenario for the demo picker.',
        expectedCasAxes: { domain: 'P', noetic: '^1', drive: 'F1', register: 'A' },
        difficulty: 'easy',
        demoSafe: true,
        demoSafetySource: 'explicit',
        honestyFlag: null,
      },
      {
        id: 'unsafe',
        sourcePath: 'fixture#unsafe',
        prompt: 'unsafe prompt',
        sentence: 'unsafe prompt',
        purpose: 'Unsafe scenario blocked from the demo picker.',
        expectedCasAxes: { domain: 'E', noetic: '^2', drive: 'F4', register: 'f' },
        difficulty: 'hard',
        demoSafe: false,
        demoSafetySource: 'explicit',
        honestyFlag: 'Unsafe fixture.',
      },
    ];

    expect(filterAlphaScenarios(scenarios, { demoSafe: true }).map((s) => s.id)).toEqual([
      'safe',
    ]);
    expect(filterAlphaScenarios(scenarios, { demoSafe: false }).map((s) => s.id)).toEqual([
      'unsafe',
    ]);
  });

  it('filters by query across prompt, purpose, and CAS labels', () => {
    expect(filterAlphaScenarios(ALPHA_SCENARIOS, { query: 'Dunning-Kruger' })).toHaveLength(
      1,
    );
    expect(filterAlphaScenarios(ALPHA_SCENARIOS, { query: 'social engineering' })).toHaveLength(
      1,
    );
    expect(filterAlphaScenarios(ALPHA_SCENARIOS, { query: 'F6' }).map((s) => s.id)).toEqual([
      'alpha_06',
      'alpha_16',
    ]);
  });

  it('normalises the backend/source snake_case shape into frontend camelCase', () => {
    const raw: AlphaScenarioSourceEntry = {
      id: 'fixture_01',
      source_path: 'source#1',
      prompt: 'Preserve this exact prompt.',
      expected_cas_axes: { domain: 'P+O', noetic: '^6', drive: 'F2', register: 'A' },
      rationale: 'Fallback plain-English purpose from source rationale.',
      expected_difficulty: 'medium',
      honesty_flag: 'Expected weak.',
      demo_safe: false,
    };

    expect(normaliseAlphaScenario(raw)).toEqual({
      id: 'fixture_01',
      sourcePath: 'source#1',
      prompt: 'Preserve this exact prompt.',
      sentence: 'Preserve this exact prompt.',
      purpose: 'Fallback plain-English purpose from source rationale.',
      expectedCasAxes: { domain: 'P+O', noetic: '^6', drive: 'F2', register: 'A' },
      difficulty: 'medium',
      demoSafe: false,
      demoSafetySource: 'explicit',
      honestyFlag: 'Expected weak.',
    });
  });

  it('normalises a source set so the full JSON file can plug in later', () => {
    const scenarios = normaliseAlphaScenarioSet({
      set_id: 'fixture_set',
      created: '2026-05-25',
      purpose: 'Fixture set',
      scenarios: [
        {
          id: 'fixture_02',
          source_path: 'source#2',
          prompt: 'Default safe prompt.',
          expected_cas_axes: { domain: 'C', noetic: '^0', drive: 'F7', register: 'T' },
          rationale: 'Defaults to alpha-set demo safe when the source omits demo_safe.',
          expected_difficulty: 'easy',
        },
      ],
    });

    expect(scenarios).toHaveLength(1);
    expect(scenarios[0].demoSafe).toBe(true);
    expect(scenarios[0].demoSafetySource).toBe('alpha_set_default');
  });
});

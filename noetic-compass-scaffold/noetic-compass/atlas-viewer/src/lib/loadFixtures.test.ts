import { describe, expect, it } from 'vitest';

import { loadPythiaTrace, loadSpatialEvidenceDemos } from './loadFixtures';

describe('loadFixtures', () => {
  it('loads all three spatial demos with picture-specific sentences', async () => {
    const demos = await loadSpatialEvidenceDemos();
    expect(demos.map((d) => d.scenario_title)).toEqual([
      'Warm study desk',
      'Blocked curb ramp',
      'Clinic consent moment',
    ]);
    expect(demos.map((d) => d.scenario_sentence)).toEqual([
      'I noticed a warm coffee cup beside an open book under a sunny window, with steam rising.',
      'A child waits at a crosswalk while a delivery van blocks the curb ramp.',
      'A clinician checks a chart while a patient and family member discuss consent.',
    ]);
  });

  it('upgrades the replay neuron covers with real Stage 27F confidence metrics', async () => {
    const trace = await loadPythiaTrace();
    const covers = trace.neuron_covers?.per_class_neuron_covers;
    expect(covers).toBeTruthy();
    const f1a = covers?.F1A?.[0] as
      | {
          label?: string;
          confidence?: number | null;
          confidence_band?: string;
          evidence_sources?: string[];
        }
      | undefined;
    expect(f1a?.label).toMatch(/^L\d+N\d+$/);
    expect(f1a?.confidence).toBeGreaterThan(0);
    expect(f1a?.confidence_band).not.toBe('unavailable');
    expect(f1a?.evidence_sources).toEqual([
      'Stage27F cover',
      'clean_margin',
      'targeted_drop',
    ]);
  });
});

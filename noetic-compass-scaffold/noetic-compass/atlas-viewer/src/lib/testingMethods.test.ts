import { describe, expect, it } from 'vitest';

import {
  KNOB_TYPE_VALUES,
  TESTING_METHODS,
  getMethod,
  listMethods,
} from './testingMethods';

const EXPECTED_IDS = [
  'foundation_probe',
  'rpm_gate_check',
  'inversion_scan',
  'sparse_neuron_cover',
  'drive_local_eraser',
  'blindspot_detection',
  'verification_stack',
  'evidence_packet',
] as const;

const EXPECTED_COSTS: Record<(typeof EXPECTED_IDS)[number], number> = {
  foundation_probe: 5,
  rpm_gate_check: 2,
  inversion_scan: 3,
  sparse_neuron_cover: 15,
  drive_local_eraser: 10,
  blindspot_detection: 0,
  verification_stack: 1,
  evidence_packet: 0,
};

describe('testingMethods registry', () => {
  it('exposes the 4 valid knob types', () => {
    expect(KNOB_TYPE_VALUES).toEqual(['enum', 'number', 'boolean', 'multiselect']);
  });

  it('contains all 9 modules (8 base + 1 spatial evidence layer)', () => {
    expect(TESTING_METHODS).toHaveLength(9);
    const ids = TESTING_METHODS.map((m) => m.id);
    for (const id of EXPECTED_IDS) {
      expect(ids).toContain(id);
    }
    expect(ids).toContain('spatial_evidence_layer');
  });

  it('listMethods returns 9 modules sorted by orderIndex', () => {
    const sorted = listMethods();
    expect(sorted).toHaveLength(9);
    const baseIds = sorted.filter((m) => m.id !== 'spatial_evidence_layer').map((m) => m.id);
    expect(baseIds).toEqual([...EXPECTED_IDS]);
    expect(sorted[sorted.length - 1].id).toBe('spatial_evidence_layer');
    for (let i = 1; i < sorted.length; i += 1) {
      expect(sorted[i].orderIndex).toBeGreaterThan(sorted[i - 1].orderIndex);
    }
  });

  it('getMethod returns the correct module by id', () => {
    for (const id of EXPECTED_IDS) {
      const m = getMethod(id);
      expect(m).toBeDefined();
      expect(m?.id).toBe(id);
    }
    expect(getMethod('does_not_exist')).toBeUndefined();
  });

  it('every knob has a valid type from KNOB_TYPE_VALUES', () => {
    for (const method of TESTING_METHODS) {
      for (const knob of method.knobs) {
        expect(KNOB_TYPE_VALUES).toContain(knob.type);
      }
    }
  });

  it('no module has an empty knobs array', () => {
    for (const method of TESTING_METHODS) {
      expect(method.knobs.length).toBeGreaterThan(0);
    }
  });

  it('per-module costEstimateGpuMinutes matches doc §5', () => {
    for (const id of EXPECTED_IDS) {
      const m = getMethod(id);
      expect(m?.costEstimateGpuMinutes).toBe(EXPECTED_COSTS[id]);
    }
  });

  it('Module 6 Blindspot and Module 8 Evidence Packet are free', () => {
    expect(getMethod('blindspot_detection')?.costEstimateGpuMinutes).toBe(0);
    expect(getMethod('evidence_packet')?.costEstimateGpuMinutes).toBe(0);
  });

  it('Module 1 axis enum covers all 4 CAS axes', () => {
    const m = getMethod('foundation_probe');
    const axis = m?.knobs.find((k) => k.id === 'axis');
    expect(axis?.options).toEqual(['Noetic', 'Domain', 'Drive', 'Register']);
  });

  it('Module 5 drive enum covers F1..F7', () => {
    const m = getMethod('drive_local_eraser');
    const drive = m?.knobs.find((k) => k.id === 'drive');
    expect(drive?.options).toEqual(['F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7']);
  });

  it('Module 7 mode enum has the 3 verification modes', () => {
    const m = getMethod('verification_stack');
    const mode = m?.knobs.find((k) => k.id === 'mode');
    expect(mode?.options).toEqual([
      'BALANCED',
      'HIGH_PRECISION',
      'MAX_COVERAGE_TRIAGE',
    ]);
  });

  it('Module 8 export format enum is JSON | markdown', () => {
    const m = getMethod('evidence_packet');
    const fmt = m?.knobs.find((k) => k.id === 'export_format');
    expect(fmt?.options).toEqual(['JSON', 'markdown']);
  });

  it('verbatim text from doc §5 is preserved', () => {
    expect(getMethod('foundation_probe')?.description).toBe(
      'Reads the 7-drive Foundation signal from model hidden states using linear probes',
    );
    expect(getMethod('rpm_gate_check')?.reveals).toBe(
      'Pass/fail status per pathway node (A0 → Dn → Wn → Pn → Outcome)',
    );
    expect(getMethod('inversion_scan')?.description).toBe(
      'Scans for structural drift across 7 inversion axes (N / W / F / E / S / A / P)',
    );
    expect(getMethod('sparse_neuron_cover')?.outputShape).toBe(
      '`neuron_cover` list with `clean_margin` + `targeted_drop` scores',
    );
    expect(getMethod('drive_local_eraser')?.outputShape).toBe(
      'Pre/post output-distribution shift + matched-control p-value',
    );
    expect(getMethod('verification_stack')?.outputShape).toBe(
      'Per-token ACCEPT / SUPPRESS / FLAG table',
    );
    expect(getMethod('evidence_packet')?.description).toBe(
      '15-field signed audit artifact bundling all module outputs for a run',
    );
  });
});

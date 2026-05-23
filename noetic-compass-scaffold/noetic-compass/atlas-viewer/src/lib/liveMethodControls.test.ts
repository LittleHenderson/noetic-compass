import { describe, expect, it } from 'vitest';
import {
  buildLiveSessionRequest,
  probesForControls,
  type LiveMethodControls,
} from './liveMethodControls';

const baseControls: LiveMethodControls = {
  enabledMethodIds: [
    'foundation_probe',
    'rpm_gate_check',
    'blindspot_detection',
    'verification_stack',
  ],
  knobValues: {
    rpm_gate_check: { strictness_threshold: 0.25 },
    blindspot_detection: { scope: 'F1' },
  },
  verificationMode: 'BALANCED',
  showBlindspots: true,
  showActiveTrace: true,
};

describe('liveMethodControls', () => {
  it('maps enabled side-panel modules to live worker probes', () => {
    expect(probesForControls(baseControls)).toEqual([
      'active_trace',
      'mode7_attribution',
      'blindspots_f1',
      'confidence_margin',
    ]);
  });

  it('overlay toggles remove their worker probes', () => {
    expect(
      probesForControls({
        ...baseControls,
        showBlindspots: false,
        showActiveTrace: false,
      }),
    ).toEqual(['mode7_attribution', 'confidence_margin']);
  });

  it('serializes knobs into method_config for the worker', () => {
    const req = buildLiveSessionRequest(baseControls);
    expect(req.probes).toContain('mode7_attribution');
    expect(req.method_config?.enabled_methods).toContain('rpm_gate_check');
    expect(req.method_config?.knobs?.rpm_gate_check.strictness_threshold).toBe(0.25);
    expect(req.method_config?.verification_mode).toBe('BALANCED');
  });
});

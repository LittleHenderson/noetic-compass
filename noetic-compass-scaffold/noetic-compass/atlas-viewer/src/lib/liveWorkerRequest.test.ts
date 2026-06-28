import { describe, expect, it } from 'vitest';

import { TESTING_METHODS } from './testingMethods';
import { buildLiveSessionRequest } from './liveWorkerRequest';

describe('buildLiveSessionRequest', () => {
  it('passes wired method knobs and disables non-runtime LIVE methods', () => {
    const payload = buildLiveSessionRequest({
      prompt: 'probe this',
      modelId: 'EleutherAI/pythia-160m',
      seed: 7,
      methods: TESTING_METHODS,
      enabledMethodIds: new Set([
        'foundation_probe',
        'drive_local_eraser',
        'evidence_packet',
      ]),
      knobValues: {
        foundation_probe: { layer_range: ['2'], top_k: 3, axis: 'Drive' },
        drive_local_eraser: { drive: 'F1', gain: 1.5 },
        evidence_packet: { export_format: 'JSON', include_per_token_detail: true },
      },
    });

    expect(payload.method_configs.foundation_probe.enabled).toBe(true);
    expect(payload.method_configs.foundation_probe.knobs.top_k).toBe(3);
    expect(payload.method_configs.drive_local_eraser.enabled).toBe(false);
    expect(payload.method_configs.evidence_packet.enabled).toBe(false);
  });

  it('never marks payload-only or unsupported methods live even when selected', () => {
    const payload = buildLiveSessionRequest({
      prompt: 'load 20B packet',
      methods: TESTING_METHODS,
      enabledMethodIds: new Set(TESTING_METHODS.map((method) => method.id)),
      knobValues: {
        sparse_neuron_cover: { target_class: 'F3', sparsity_budget: 256 },
        drive_local_eraser: { drive: 'F3', gain: 1.0 },
        evidence_packet: { export_format: 'JSON', include_per_token_detail: true },
        spatial_evidence_layer: { enabled: true },
      },
    });

    expect(payload.method_configs.foundation_probe.enabled).toBe(true);
    expect(payload.method_configs.rpm_gate_check.enabled).toBe(true);
    expect(payload.method_configs.blindspot_detection.enabled).toBe(true);
    expect(payload.method_configs.verification_stack.enabled).toBe(true);
    expect(payload.method_configs.sparse_neuron_cover.enabled).toBe(false);
    expect(payload.method_configs.drive_local_eraser.enabled).toBe(false);
    expect(payload.method_configs.evidence_packet.enabled).toBe(false);
    expect(payload.method_configs.spatial_evidence_layer.enabled).toBe(false);
  });
});

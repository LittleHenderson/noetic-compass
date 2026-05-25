import { describe, expect, it } from 'vitest';

import {
  buildDefaultProvenanceChips,
  formatAuditConfidence,
  isAuditResultCustomerSafe,
  normalizeAuditConfidence,
  normalizeAuditVerdict,
  validateAuditConfidence,
  verdictCopy,
  type AuditSessionSummary,
} from './casHarnessAudit';

const safeSummary: AuditSessionSummary = {
  request: {
    mode: 'live',
    prompt: 'audit this output',
    modelId: 'EleutherAI/pythia-160m',
    sessionId: 'session-1',
  },
  verdict: 'ACCEPT',
  confidence: 0.84,
  confidenceLabel: '84%',
  provenanceChips: buildDefaultProvenanceChips({
    modelProof: true,
    casReadout: true,
    causalProof: true,
    controlProof: true,
    outputProof: true,
    packetProof: true,
  }),
  runtimeProof: {
    is_real_model: true,
    model_loaded: true,
    load_error: null,
    fake_runtime_env: false,
    manifest_is_real_model: true,
  },
};

describe('normalizeAuditVerdict', () => {
  it('normalizes every supported verdict', () => {
    expect(normalizeAuditVerdict('accept')).toBe('ACCEPT');
    expect(normalizeAuditVerdict('SUPPRESS')).toBe('SUPPRESS');
    expect(normalizeAuditVerdict('flag for human review')).toBe(
      'FLAG_FOR_HUMAN_REVIEW',
    );
  });

  it('rejects unknown verdicts', () => {
    expect(() => normalizeAuditVerdict('approve')).toThrow(/Unsupported/);
  });
});

describe('confidence helpers', () => {
  it('validates confidence only inside [0, 1]', () => {
    expect(validateAuditConfidence(0)).toBe(true);
    expect(validateAuditConfidence(1)).toBe(true);
    expect(validateAuditConfidence(-0.01)).toBe(false);
    expect(validateAuditConfidence(1.01)).toBe(false);
    expect(validateAuditConfidence(Number.NaN)).toBe(false);
  });

  it('normalizes numeric strings and rejects invalid confidence', () => {
    expect(normalizeAuditConfidence('0.72')).toBe(0.72);
    expect(() => normalizeAuditConfidence('72')).toThrow(/\[0, 1\]/);
    expect(() => normalizeAuditConfidence(null)).toThrow(/\[0, 1\]/);
  });

  it('formats confidence as rounded percentages', () => {
    expect(formatAuditConfidence(0.726)).toBe('73%');
    expect(formatAuditConfidence('0.994')).toBe('99%');
    expect(formatAuditConfidence(1)).toBe('100%');
  });
});

describe('buildDefaultProvenanceChips', () => {
  it('emits the six required chips in stable order with display labels', () => {
    const chips = buildDefaultProvenanceChips({
      modelProof: true,
      casReadout: { present: true, detail: 'CAS F1 readout present' },
      causalProof: 'failed',
      controlProof: false,
      outputProof: { status: 'present', label: 'Output span captured' },
      packetProof: { status: 'unavailable' },
    });

    expect(chips.map((chip) => chip.id)).toEqual([
      'model_proof',
      'cas_readout',
      'causal_proof',
      'control_proof',
      'output_proof',
      'packet_proof',
    ]);
    expect(chips.map((chip) => chip.name)).toEqual([
      'Model proof',
      'CAS readout',
      'Causal proof',
      'Control proof',
      'Output proof',
      'Packet proof',
    ]);
    expect(chips.map((chip) => chip.status)).toEqual([
      'verified',
      'present',
      'failed',
      'missing',
      'present',
      'unavailable',
    ]);
    expect(chips.map((chip) => chip.statusLabel)).toEqual([
      'Verified',
      'Present',
      'Failed',
      'Missing',
      'Present',
      'Unavailable',
    ]);
    expect(chips[1].detail).toBe('CAS F1 readout present');
    expect(chips[4].detail).toBe('Output span captured');
  });
});

describe('verdictCopy', () => {
  it('returns plain-English copy for ACCEPT', () => {
    expect(verdictCopy('ACCEPT', 0.91)).toEqual({
      label: 'Accept',
      description: 'The model output is supported by the audit evidence.',
      confidenceLabel: '91%',
    });
  });

  it('returns plain-English copy for SUPPRESS', () => {
    expect(verdictCopy('SUPPRESS', 0.42)).toEqual({
      label: 'Suppress',
      description: 'The model output should not be trusted or shown as-is.',
      confidenceLabel: '42%',
    });
  });

  it('returns plain-English copy for FLAG_FOR_HUMAN_REVIEW', () => {
    expect(verdictCopy('FLAG_FOR_HUMAN_REVIEW', 0.64)).toEqual({
      label: 'Flag for human review',
      description: 'The model output needs human review before trust.',
      confidenceLabel: '64%',
    });
  });
});

describe('isAuditResultCustomerSafe', () => {
  it('accepts a fully proven live ACCEPT summary', () => {
    expect(isAuditResultCustomerSafe(safeSummary)).toBe(true);
  });

  it('rejects ACCEPT with no model proof', () => {
    const summary = {
      ...safeSummary,
      provenanceChips: buildDefaultProvenanceChips({
        modelProof: false,
        casReadout: true,
        causalProof: true,
        controlProof: true,
        outputProof: true,
        packetProof: true,
      }),
    };

    expect(isAuditResultCustomerSafe(summary)).toBe(false);
  });

  it('rejects ACCEPT when required CAS/output/packet proof is missing', () => {
    const summary = {
      ...safeSummary,
      provenanceChips: buildDefaultProvenanceChips({
        modelProof: true,
        casReadout: false,
        causalProof: true,
        controlProof: true,
        outputProof: true,
        packetProof: true,
      }),
    };

    expect(isAuditResultCustomerSafe(summary)).toBe(false);
  });

  it('rejects ACCEPT when causal or control proof is failed or unavailable', () => {
    const summary = {
      ...safeSummary,
      provenanceChips: buildDefaultProvenanceChips({
        modelProof: true,
        casReadout: true,
        causalProof: 'failed',
        controlProof: 'unavailable',
        outputProof: true,
        packetProof: true,
      }),
    };

    expect(isAuditResultCustomerSafe(summary)).toBe(false);
  });

  it('rejects fake runtime proof even when the model chip is verified', () => {
    const summary: AuditSessionSummary = {
      ...safeSummary,
      runtimeProof: {
        isRealModel: true,
        modelLoaded: true,
        loadError: null,
        fakeRuntimeEnv: true,
        manifestIsRealModel: true,
      },
    };

    expect(isAuditResultCustomerSafe(summary)).toBe(false);
  });

  it('rejects nonpositive confidence', () => {
    expect(isAuditResultCustomerSafe({ ...safeSummary, confidence: 0 })).toBe(false);
  });

  it('rejects invalid confidence without throwing', () => {
    const summary = { ...safeSummary, confidence: 1.2 };
    expect(isAuditResultCustomerSafe(summary)).toBe(false);
  });

  it('allows non-ACCEPT verdicts when model proof and runtime proof are real', () => {
    expect(
      isAuditResultCustomerSafe({
        ...safeSummary,
        verdict: 'FLAG_FOR_HUMAN_REVIEW',
        provenanceChips: buildDefaultProvenanceChips({
          modelProof: true,
          casReadout: false,
          causalProof: false,
          controlProof: false,
          outputProof: false,
          packetProof: false,
        }),
      }),
    ).toBe(true);
  });
});

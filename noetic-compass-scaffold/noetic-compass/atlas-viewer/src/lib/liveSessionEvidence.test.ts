import { describe, expect, it } from 'vitest';

import type { LiveManifest, LiveRealModeProof } from './atlasLiveApi';
import { buildLiveSessionEvidence, redactEvidenceValue } from './liveSessionEvidence';

const REAL_PROOF: LiveRealModeProof = {
  verdict: 'REAL_PYTHIA_WEIGHTS_LOADED',
  is_real_model: true,
  model_loaded: true,
  load_error: null,
  fake_runtime_env: false,
  manifest_is_real_model: true,
  model_id: 'EleutherAI/pythia-160m',
  worker_version: 'atlas-live-worker-m2',
  http_status: 200,
  checked_at: '2026-05-25T08:00:00.000Z',
};

const REAL_MANIFEST: LiveManifest = {
  model_id: 'EleutherAI/pythia-160m',
  tokenizer_id: 'EleutherAI/pythia-160m',
  worker_version: 'atlas-live-worker-m2',
  is_real_model: true,
};

describe('buildLiveSessionEvidence', () => {
  it('summarises a verified real LIVE session without implying replay', () => {
    const summary = buildLiveSessionEvidence({
      runtimeMode: 'live',
      realModeProof: REAL_PROOF,
      manifest: REAL_MANIFEST,
      sessionId: 'sess_123',
      modelId: 'EleutherAI/pythia-160m',
      tokenEventCount: 7,
      completeTotalTokens: 7,
      resolvedKnobs: {
        foundation_probe: { top_k: 8, layer_range: [4, 5] },
      },
      methodConfig: {
        enabled_methods: ['foundation_probe'],
        knobs: {
          foundation_probe: {
            top_k: 8,
            layer_range: [4, 5],
          },
        },
      },
    });

    expect(summary.kind).toBe('real_live');
    expect(summary.status).toBe('verified_real_model');
    expect(summary.title).toMatch(/real Pythia weights verified/i);
    expect(summary.plainEnglish).toMatch(/real-weight proof passed/i);
    expect(summary.proof.verified).toBe(true);
    expect(summary.modelId).toBe('EleutherAI/pythia-160m');
    expect(summary.workerVersion).toBe('atlas-live-worker-m2');
  });

  it('distinguishes replay fallback from real LIVE evidence', () => {
    const summary = buildLiveSessionEvidence({
      runtimeMode: 'replay',
      realModeProof: REAL_PROOF,
      manifest: REAL_MANIFEST,
      tokenEventCount: 3,
    });

    expect(summary.kind).toBe('replay_fallback');
    expect(summary.status).toBe('replay_fallback');
    expect(summary.plainEnglish).toMatch(/replay fixture output/i);
    expect(summary.plainEnglish).not.toMatch(/real-weight proof passed/i);
  });

  it('does not call a session real when the manifest is missing', () => {
    const summary = buildLiveSessionEvidence({
      runtimeMode: 'live',
      realModeProof: REAL_PROOF,
      tokenEventCount: 1,
    });

    expect(summary.kind).toBe('unverified_live');
    expect(summary.status).toBe('unverified');
    expect(summary.proof.verified).toBe(true);
    expect(summary.manifest).toBeNull();
    expect(summary.plainEnglish).toMatch(/not received enough proof/i);
  });

  it('summarises token event count and complete count separately', () => {
    const summary = buildLiveSessionEvidence({
      runtimeMode: 'live',
      realModeProof: REAL_PROOF,
      manifest: REAL_MANIFEST,
      tokenEventCount: 4.9,
      completeTotalTokens: 6,
    });

    expect(summary.tokenSummary).toEqual({
      tokenEventCount: 4,
      completeTotalTokens: 6,
      text: '4 token events received; complete event reported 6 total tokens.',
    });
  });

  it('includes method knob values only when the worker resolved them as consumed', () => {
    const summary = buildLiveSessionEvidence({
      runtimeMode: 'live',
      realModeProof: REAL_PROOF,
      manifest: REAL_MANIFEST,
      methodConfig: {
        enabled_methods: ['foundation_probe', 'verification_stack'],
        knobs: {
          foundation_probe: {
            top_k: 12,
            layer_range: [5, 6],
            unused_local_only: 'do-not-include',
          },
          verification_stack: {
            mode: 'HIGH_PRECISION',
          },
        },
      },
      resolvedKnobs: {
        foundation_probe: {
          top_k: 12,
          layer_range: [5, 6],
        },
      },
    });

    expect(summary.consumedMethodKnobs).toEqual({
      foundation_probe: {
        top_k: 12,
        layer_range: [5, 6],
      },
    });
    expect(JSON.stringify(summary.consumedMethodKnobs)).not.toContain(
      'do-not-include',
    );
    expect(JSON.stringify(summary.consumedMethodKnobs)).not.toContain(
      'HIGH_PRECISION',
    );
    expect(summary.sentButUnconsumedKnobNames).toEqual({
      foundation_probe: ['unused_local_only'],
      verification_stack: ['mode'],
    });
  });

  it('keeps worker metadata from resolved knobs because it affects runtime truth', () => {
    const summary = buildLiveSessionEvidence({
      runtimeMode: 'live',
      realModeProof: REAL_PROOF,
      manifest: REAL_MANIFEST,
      methodConfig: {
        knobs: {
          drive_local_eraser: {
            drive: 'F3',
            gain: 0.7,
          },
        },
      },
      resolvedKnobs: {
        drive_local_eraser: {
          drive: 'F3',
          gain: 0.7,
          active: true,
          cover_available: true,
        },
      },
    });

    expect(summary.consumedMethodKnobs.drive_local_eraser).toEqual({
      drive: 'F3',
      gain: 0.7,
      active: true,
      cover_available: true,
    });
  });

  it('redacts invite codes, bearer tokens, API keys, stream tokens, and tokenised URLs', () => {
    const summary = buildLiveSessionEvidence({
      runtimeMode: 'live',
      realModeProof: REAL_PROOF,
      manifest: REAL_MANIFEST,
      sessionResponse: {
        session_id: 'sess_safe',
        mode: 'live',
        model_id: 'EleutherAI/pythia-160m',
        stream_url: '/api/atlas/live/session/sess_safe/events?stream_token=secret-stream&keep=1',
        stream_token: 'secret-stream',
        api_key: 'rnd_secret',
      },
      streamUrl:
        'https://api.example.test/atlas/live/session/sess_safe/events?stream_token=secret-stream&trace_id=t1',
      extra: {
        inviteCode: 'wakil-alpha-001',
        authorization: 'Bearer abc.def.ghi',
        nested: {
          x_atlas_invite_code: 'wakil-alpha-002',
          safe: 'visible',
        },
      },
      failureReason: 'Worker rejected Authorization: Bearer sensitive-token',
    });

    const raw = JSON.stringify(summary);
    expect(raw).not.toContain('secret-stream');
    expect(raw).not.toContain('rnd_secret');
    expect(raw).not.toContain('wakil-alpha-001');
    expect(raw).not.toContain('wakil-alpha-002');
    expect(raw).not.toContain('abc.def.ghi');
    expect(raw).not.toContain('sensitive-token');
    expect(raw).toContain('[redacted]');
    expect(summary.redactions).toEqual(
      expect.arrayContaining([
        'sanitizedRuntimeFacts.sessionResponse.stream_url',
        'sanitizedRuntimeFacts.sessionResponse.stream_token',
        'sanitizedRuntimeFacts.sessionResponse.api_key',
        'sanitizedRuntimeFacts.streamUrl',
        'sanitizedRuntimeFacts.extra.inviteCode',
        'sanitizedRuntimeFacts.extra.authorization',
        'sanitizedRuntimeFacts.extra.nested.x_atlas_invite_code',
        'proof.failureReason',
      ]),
    );
  });

  it('surfaces a LIVE failure as fallback evidence with a redacted reason', () => {
    const summary = buildLiveSessionEvidence({
      runtimeMode: 'live',
      realModeProof: {
        ...REAL_PROOF,
        is_real_model: false,
        model_loaded: false,
        verdict: 'NOT_REAL_PYTHIA_WEIGHTS',
        load_error: 'bad Authorization: Bearer real-secret',
      },
      manifest: {
        ...REAL_MANIFEST,
        is_real_model: false,
      },
      failureReason: new Error('stream_token=secret failed'),
    });

    expect(summary.kind).toBe('replay_fallback');
    expect(summary.status).toBe('failed');
    expect(summary.proof.verified).toBe(false);
    expect(summary.proof.loadError).toBe('bad Authorization: Bearer [redacted]');
    expect(summary.proof.failureReason).toBe('stream_token=[redacted] failed');
  });
});

describe('redactEvidenceValue', () => {
  it('can redact standalone objects for drawer payload previews', () => {
    expect(
      redactEvidenceValue({
        safe: 'ok',
        url: '/events?stream_token=secret&n=1',
        headers: {
          Authorization: 'Bearer top-secret',
        },
      }),
    ).toEqual({
      safe: 'ok',
      url: '/events?stream_token=%5Bredacted%5D&n=1',
      headers: {
        Authorization: '[redacted]',
      },
    });
  });
});

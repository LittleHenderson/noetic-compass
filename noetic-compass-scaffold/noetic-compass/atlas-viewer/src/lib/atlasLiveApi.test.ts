import { describe, expect, it, vi } from 'vitest';
import {
  appendLiveEvent,
  createLiveSession,
  emptyLiveTrace,
  resolveLiveStreamUrl,
} from './atlasLiveApi';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('atlasLiveApi', () => {
  it('maps backend stream URLs through the Vite /api proxy', () => {
    expect(
      resolveLiveStreamUrl('/atlas/live/session/s1/events?stream_token=t', '/api/atlas'),
    ).toBe('/api/atlas/live/session/s1/events?stream_token=t');
  });

  it('creates a live session with the invite-code header', async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse({
        session_id: 's1',
        mode: 'live',
        model_id: 'EleutherAI/pythia-160m',
        stream_url: '/atlas/live/session/s1/events?stream_token=t',
        stream_token: 't',
      }),
    );

    const session = await createLiveSession(
      { prompt: 'hello' },
      'alpha',
      { baseUrl: '/api/atlas', fetchImpl },
    );

    expect(session.stream_url).toBe('/api/atlas/live/session/s1/events?stream_token=t');
    const [url, init] = fetchImpl.mock.calls[0];
    expect(url).toBe('/api/atlas/live/session');
    expect((init?.headers as Record<string, string>)['X-Atlas-Invite-Code']).toBe('alpha');
  });

  it('appends live manifest, cover, and token events to replay-shaped trace', () => {
    let trace = emptyLiveTrace();
    trace = appendLiveEvent(trace, {
      type: 'manifest',
      manifest: {
        model_id: 'EleutherAI/pythia-160m',
        is_real_model: true,
      },
    });
    trace = appendLiveEvent(trace, {
      type: 'neuron_covers',
      per_class_neuron_covers: { F1E: ['L5N142'] },
    });
    trace = appendLiveEvent(trace, {
      type: 'token',
      token_index: 0,
      token: ' hello',
      top_activated_neurons: [{ layer: 5, index: 142, activation: 0.7 }],
      inversion_risk: 0.42,
    });

    expect(trace.tokens).toEqual([{ token_index: 0, token: ' hello' }]);
    expect(trace.per_token_frames).toHaveLength(1);
    expect((trace as unknown as { model_id: string }).model_id).toBe('EleutherAI/pythia-160m');
    expect(
      (trace.per_token_frames[0] as { inversion_risk: number }).inversion_risk,
    ).toBe(0.42);
    // Legacy bare-string covers normalise to typed members at the UI edge
    // so the cockpit's blindspot-interpretation surface can render against
    // either old or new traces. Bare strings → placeholder/unavailable.
    const covers = (
      trace as unknown as {
        neuron_covers: { per_class_neuron_covers: Record<string, unknown[]> };
      }
    ).neuron_covers.per_class_neuron_covers.F1E;
    expect(covers).toHaveLength(1);
    expect(covers[0]).toMatchObject({
      label: 'L5N142',
      confidence: null,
      confidence_band: 'unavailable',
      evidence_sources: [],
    });
  });

  it('promotes typed F1 neuron_covers events into normalised members', () => {
    let trace = emptyLiveTrace();
    trace = appendLiveEvent(trace, {
      type: 'neuron_covers',
      per_class_neuron_covers: {
        F1T: [
          {
            label: 'L4N336',
            confidence: 0.72,
            confidence_band: 'medium',
            evidence_sources: ['probe', 'ablation'],
          },
        ],
        F1A: [
          // Worker forgot to populate the band — UI must recompute it.
          { label: 'L3N142', confidence: 0.85 } as never,
        ],
      },
    });
    const covers = (
      trace as unknown as {
        neuron_covers: { per_class_neuron_covers: Record<string, unknown[]> };
      }
    ).neuron_covers.per_class_neuron_covers;
    expect(covers.F1T[0]).toMatchObject({
      label: 'L4N336',
      confidence: 0.72,
      confidence_band: 'medium',
      evidence_sources: ['probe', 'ablation'],
    });
    expect(covers.F1A[0]).toMatchObject({
      label: 'L3N142',
      confidence: 0.85,
      confidence_band: 'high',  // recomputed from 0.85 -> high
    });
  });

  it('absorbs word_spans events and exposes them on the trace', () => {
    let trace = emptyLiveTrace();
    trace = appendLiveEvent(trace, {
      type: 'word_spans',
      spans: [
        { word: 'hello', token_indices: [0], char_start: 0, char_end: 5 },
        { word: 'world', token_indices: [1], char_start: 6, char_end: 11 },
      ],
      structural_token_indices: [],
      total_tokens_covered: 2,
    });

    expect(trace.word_spans?.total_tokens_covered).toBe(2);
    expect(trace.word_spans?.spans).toHaveLength(2);
    expect(trace.word_spans?.spans[1]).toEqual({
      word: 'world',
      token_indices: [1],
      char_start: 6,
      char_end: 11,
    });
  });
});

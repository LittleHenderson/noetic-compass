import { describe, expect, it, vi } from 'vitest';
import {
  appendLiveEvent,
  createLiveSession,
  emptyLiveTrace,
  fetchLiveRealModeProof,
  isLiveRealModeProofVerified,
  openLiveEventStream,
  resolveLiveStreamUrl,
  type LiveEventSourceLike,
} from './atlasLiveApi';

function jsonResponse(
  body: unknown,
  status = 200,
  headers?: Record<string, string>,
): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...(headers ?? {}) },
  });
}

class FakeEventSource implements LiveEventSourceLike {
  static last: FakeEventSource | null = null;

  readonly listeners = new Map<string, Array<(event: Event) => void>>();
  readonly url: string;
  closed = false;
  onerror: ((event: Event) => void) | null = null;
  onopen: ((event: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    FakeEventSource.last = this;
  }

  addEventListener(type: string, listener: (event: Event) => void): void {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), listener]);
  }

  close(): void {
    this.closed = true;
  }

  emit(type: string, body: unknown): void {
    const event = new MessageEvent(type, { data: JSON.stringify(body) });
    for (const listener of this.listeners.get(type) ?? []) {
      listener(event);
    }
  }

  failTransport(): void {
    this.onerror?.(new Event('error'));
  }
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

  it('rejects missing invite codes before opening a session', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse({}));

    await expect(
      createLiveSession({ prompt: 'hello' }, '   ', { fetchImpl }),
    ).rejects.toMatchObject({
      kind: 'missing_invite',
      message: expect.stringContaining('invite code is required'),
    });
    expect(fetchImpl).not.toHaveBeenCalled();
  });

  it('maps invalid invite responses to a clear user message', async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse({ detail: 'Invalid Atlas LIVE invite code' }, 403),
    );

    await expect(
      createLiveSession({ prompt: 'hello' }, 'wrong', { fetchImpl }),
    ).rejects.toMatchObject({
      kind: 'invalid_invite',
      httpStatus: 403,
      detail: 'Invalid Atlas LIVE invite code',
      message: expect.stringContaining('was not accepted'),
    });
  });

  it('separates per-IP and per-code rate-limit messages', async () => {
    const perIp = vi.fn(async () =>
      jsonResponse(
        { detail: 'Atlas LIVE per-IP session limit exceeded' },
        429,
        { 'Retry-After': '12' },
      ),
    );
    const perCode = vi.fn(async () =>
      jsonResponse({ detail: 'Atlas LIVE invite-code daily limit exceeded' }, 429),
    );

    await expect(
      createLiveSession({ prompt: 'hello' }, 'alpha', { fetchImpl: perIp }),
    ).rejects.toMatchObject({
      kind: 'rate_limited_ip',
      retryAfterSeconds: 12,
      message: expect.stringContaining('per-IP session limit'),
    });
    await expect(
      createLiveSession({ prompt: 'hello' }, 'alpha', { fetchImpl: perCode }),
    ).rejects.toMatchObject({
      kind: 'rate_limited_code',
      message: expect.stringContaining('invite code'),
    });
  });

  it('maps worker-unavailable session-open failures to replay-safe guidance', async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse({ detail: 'Atlas LIVE worker URL is not configured' }, 503),
    );

    await expect(
      createLiveSession({ prompt: 'hello' }, 'alpha', { fetchImpl }),
    ).rejects.toMatchObject({
      kind: 'worker_unavailable',
      message: expect.stringContaining('Replay fixtures are still available'),
    });
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
      verification_mode: 'HIGH_PRECISION',
      verification_verdict: 'FLAG',
      verification_threshold: 0.85,
      verification_score: 0.72,
      verification_score_source: 'confidence',
    });

    expect(trace.tokens).toEqual([{ token_index: 0, token: ' hello' }]);
    expect(trace.per_token_frames).toHaveLength(1);
    expect((trace as unknown as { model_id: string }).model_id).toBe('EleutherAI/pythia-160m');
    expect(
      (trace.per_token_frames[0] as { inversion_risk: number }).inversion_risk,
    ).toBe(0.42);
    expect(trace.per_token_frames[0]).toMatchObject({
      verification_mode: 'HIGH_PRECISION',
      verification_verdict: 'FLAG',
      verification_threshold: 0.85,
      verification_score: 0.72,
      verification_score_source: 'confidence',
    });
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

  it('normalises the realmode proof endpoint into a boolean source of truth', async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse({
        verdict: 'REAL_PYTHIA_WEIGHTS_LOADED',
        is_real_model: true,
        model_loaded: true,
        load_error: null,
        model_id: 'EleutherAI/pythia-160m',
      }),
    );

    const proof = await fetchLiveRealModeProof({
      baseUrl: '/api/atlas',
      fetchImpl,
    });

    expect(fetchImpl).toHaveBeenCalledWith(
      '/api/atlas/live/health/realmode',
      expect.objectContaining({ method: 'GET' }),
    );
    expect(proof).toMatchObject({
      verdict: 'REAL_PYTHIA_WEIGHTS_LOADED',
      is_real_model: true,
      model_loaded: true,
      load_error: null,
      http_status: 200,
    });
    expect(isLiveRealModeProofVerified(proof)).toBe(true);
  });

  it('treats a 503 worker-unavailable response as not connected', async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse({ detail: 'atlas_live_worker_unavailable' }, 503),
    );

    const proof = await fetchLiveRealModeProof({
      baseUrl: '/api/atlas',
      fetchImpl,
    });

    expect(proof).toMatchObject({
      verdict: 'NOT_REAL_PYTHIA_WEIGHTS',
      is_real_model: false,
      model_loaded: false,
      load_error: 'atlas_live_worker_unavailable',
      http_status: 503,
    });
    expect(isLiveRealModeProofVerified(proof)).toBe(false);
  });

  it('does not accept fake/demo realmode proof as verified', () => {
    expect(
      isLiveRealModeProofVerified({
        verdict: 'NOT_REAL_PYTHIA_WEIGHTS',
        is_real_model: false,
        model_loaded: true,
        load_error: null,
        fake_runtime_env: true,
        manifest_is_real_model: true,
        http_status: 200,
        checked_at: '2026-05-25T00:00:00.000Z',
      }),
    ).toBe(false);
  });

  it('bounds EventSource transport reconnect attempts', () => {
    const onFailure = vi.fn();
    const handle = openLiveEventStream('/stream', {
      eventSourceImpl: FakeEventSource,
      maxTransportErrors: 1,
      onEvent: vi.fn(),
      onFailure,
    });
    const source = FakeEventSource.last;
    expect(source).not.toBeNull();
    expect(handle.closed).toBe(false);

    source!.failTransport();
    expect(source!.closed).toBe(false);
    expect(onFailure).not.toHaveBeenCalled();

    source!.failTransport();
    expect(source!.closed).toBe(true);
    expect(handle.closed).toBe(true);
    expect(onFailure).toHaveBeenCalledWith(
      expect.objectContaining({
        kind: 'stream_disconnected',
        message: expect.stringContaining('reconnect attempts were stopped'),
      }),
    );
  });

  it('closes the stream on worker error events instead of letting EventSource loop', () => {
    const onFailure = vi.fn();
    const onEvent = vi.fn();
    openLiveEventStream('/stream', {
      eventSourceImpl: FakeEventSource,
      onEvent,
      onFailure,
    });
    const source = FakeEventSource.last;
    expect(source).not.toBeNull();

    source!.emit('error', {
      type: 'error',
      message: 'Atlas LIVE worker stream failed',
      retryable: true,
    });

    expect(source!.closed).toBe(true);
    expect(onEvent).not.toHaveBeenCalled();
    expect(onFailure).toHaveBeenCalledWith(
      expect.objectContaining({
        kind: 'worker_unavailable',
      }),
    );
  });
});

import type { ReplayTrace } from './replayController';
import { bandForConfidence, type ConfidenceBand } from './confidenceBands';

const DEFAULT_BASE_URL = '/api/atlas';
const REALMODE_PASS_VERDICT = 'REAL_PYTHIA_WEIGHTS_LOADED';

export type AtlasLiveFailureKind =
  | 'missing_invite'
  | 'invalid_invite'
  | 'rate_limited_ip'
  | 'rate_limited_code'
  | 'rate_limited'
  | 'worker_unavailable'
  | 'unverified_model'
  | 'stream_disconnected'
  | 'bad_response';

export class AtlasLiveError extends Error {
  readonly kind: AtlasLiveFailureKind;
  readonly httpStatus?: number;
  readonly detail?: string;
  readonly retryAfterSeconds?: number;

  constructor(
    kind: AtlasLiveFailureKind,
    message: string,
    opts?: {
      httpStatus?: number;
      detail?: string;
      retryAfterSeconds?: number;
      cause?: unknown;
    },
  ) {
    super(message);
    this.name = 'AtlasLiveError';
    this.kind = kind;
    this.httpStatus = opts?.httpStatus;
    this.detail = opts?.detail;
    this.retryAfterSeconds = opts?.retryAfterSeconds;
    if (opts?.cause !== undefined) {
      (this as Error & { cause?: unknown }).cause = opts.cause;
    }
  }
}

export type LiveProbeName =
  | 'active_trace'
  | 'blindspot_covers'
  | 'mode7_attribution'
  | 'confidence_margin';

export interface CreateLiveSessionRequest {
  prompt: string;
  model_id?: string;
  max_new_tokens?: number;
  temperature?: number;
  seed?: number;
  probes?: LiveProbeName[];
  method_config?: {
    enabled_methods?: string[];
    knobs?: Record<string, Record<string, unknown>>;
    overlays?: Record<string, unknown>;
    verification_mode?: string;
  };
}

export interface CreateLiveSessionResponse {
  session_id: string;
  mode: 'live';
  model_id: string;
  stream_url: string;
  stream_token: string;
}

export interface LiveManifest {
  model_id: string;
  model_arch?: unknown;
  tokenizer_id?: string;
  worker_version?: string;
  is_real_model: boolean;
}

export interface LiveRealModeProof {
  verdict: string;
  is_real_model: boolean;
  model_loaded: boolean;
  load_error: string | null;
  fake_runtime_env?: boolean;
  manifest_is_real_model?: boolean;
  model_id?: string;
  worker_version?: string;
  detail?: string;
  http_status: number;
  checked_at: string;
}

export type ResolvedKnobs = Record<string, Record<string, unknown>>;

export function liveFailureMessage(
  kind: AtlasLiveFailureKind,
  retryAfterSeconds?: number,
): string {
  const retrySuffix =
    retryAfterSeconds !== undefined
      ? ` Try again in about ${retryAfterSeconds} second${retryAfterSeconds === 1 ? '' : 's'}.`
      : '';
  switch (kind) {
    case 'missing_invite':
      return 'Atlas LIVE invite code is required. Enter the code from your invite email to start a LIVE session.';
    case 'invalid_invite':
      return 'Atlas LIVE invite code was not accepted. Check the code from your invite email.';
    case 'rate_limited_ip':
      return `Atlas LIVE per-IP session limit has been reached for this network.${retrySuffix || ' Try again later.'}`;
    case 'rate_limited_code':
      return `Atlas LIVE daily limit has been reached for this invite code.${retrySuffix || ' Try again later.'}`;
    case 'rate_limited':
      return `Atlas LIVE is rate limited for this invite code or IP.${retrySuffix || ' Try again later.'}`;
    case 'worker_unavailable':
      return 'Atlas LIVE worker is unavailable. Replay fixtures are still available; try LIVE again after the worker is healthy.';
    case 'unverified_model':
      return 'Atlas LIVE did not pass the real-weight proof, so the session was stopped. Replay fixtures remain active.';
    case 'stream_disconnected':
      return 'Atlas LIVE stream disconnected and reconnect attempts were stopped. Replay fixtures remain available.';
    case 'bad_response':
      return 'Atlas LIVE returned an unreadable response. Replay fixtures remain active.';
  }
}

export function isLiveRealModeProofVerified(
  proof: LiveRealModeProof | null | undefined,
): boolean {
  return (
    proof?.http_status === 200 &&
    proof.verdict === REALMODE_PASS_VERDICT &&
    proof.is_real_model === true &&
    proof.model_loaded === true &&
    proof.load_error === null &&
    proof.fake_runtime_env !== true &&
    proof.manifest_is_real_model !== false
  );
}

export function liveProofFailureMessage(
  proof: LiveRealModeProof | null | undefined,
): string {
  if (!proof) {
    return 'Atlas LIVE real-weight proof has not completed. Replay fixtures remain active.';
  }
  if (proof.http_status === 503 || proof.detail === 'atlas_live_worker_unavailable') {
    return liveFailureMessage('worker_unavailable');
  }
  if (proof.fake_runtime_env === true) {
    return 'Atlas LIVE worker is running fake/demo mode, so LIVE was stopped before any actual-weights claim.';
  }
  if (!proof.model_loaded) {
    return 'Atlas LIVE worker has not loaded real Pythia weights yet. Replay fixtures remain active.';
  }
  if (proof.load_error) {
    return `Atlas LIVE real-weight proof failed: ${proof.load_error}`;
  }
  if (proof.manifest_is_real_model === false) {
    return 'Atlas LIVE worker manifest is not marked as a real model, so LIVE was stopped.';
  }
  return liveFailureMessage('unverified_model');
}

/**
 * One token-backed word span. The worker emits these once at end-of-stream
 * (see `live-trace-worker/app/schemas/events.py::WordSpan`). Token indices
 * are always 0-based contiguous over `[0, total_tokens_covered)`, and every
 * input token appears in exactly one span OR in `structural_token_indices`.
 */
export interface LiveWordSpan {
  word: string;
  token_indices: number[];
  char_start: number;
  char_end: number;
}

/**
 * Typed neuron-cover member. Carries the interpretive payload the cockpit
 * needs to turn a red blindspot into a plain-English human concern.
 *
 * The worker is the source of truth (see
 * live-trace-worker/app/schemas/events.py::NeuronCoverMember). The UI
 * tolerates the legacy bare-string shape for backward compatibility by
 * promoting strings into placeholder members at parse time.
 */
export interface NeuronCoverMember {
  label: string;
  confidence: number | null;
  confidence_band: ConfidenceBand;
  evidence_sources: string[];
}

export type RawNeuronCoverMember =
  | string
  | {
      label: string;
      confidence?: number | null;
      confidence_band?: ConfidenceBand;
      evidence_sources?: string[];
    };

/**
 * Promote a raw cover entry (string OR typed object) into a fully-typed
 * NeuronCoverMember. Legacy traces with bare strings collapse to a
 * placeholder (band = unavailable, no evidence), which keeps the 3D red
 * overlay working while the textual interpretation panel waits for real
 * probe data.
 */
export function normaliseCoverMember(raw: RawNeuronCoverMember): NeuronCoverMember {
  if (typeof raw === 'string') {
    return {
      label: raw,
      confidence: null,
      confidence_band: 'unavailable',
      evidence_sources: [],
    };
  }
  const confidence =
    typeof raw.confidence === 'number' ? raw.confidence : raw.confidence ?? null;
  const declared = raw.confidence_band;
  const computed = bandForConfidence(confidence);
  // Trust the worker's declared band when it's a valid bucket; otherwise
  // recompute from the confidence value. Keeps UI in sync even if a future
  // worker version forgets to populate the field.
  const band: ConfidenceBand =
    declared === 'high' ||
    declared === 'medium' ||
    declared === 'low' ||
    declared === 'unavailable'
      ? declared
      : computed;
  return {
    label: raw.label,
    confidence,
    confidence_band: band,
    evidence_sources: Array.isArray(raw.evidence_sources)
      ? raw.evidence_sources.filter((s): s is string => typeof s === 'string')
      : [],
  };
}

export type LiveTraceEvent =
  | { type: 'manifest'; manifest: LiveManifest }
  | { type: 'knob_resolution'; resolved_knobs: ResolvedKnobs }
  | {
      type: 'neuron_covers';
      per_class_neuron_covers: Record<string, RawNeuronCoverMember[]>;
    }
  | {
      type: 'token';
      token_index: number;
      token: string;
      top_activated_neurons?: unknown[];
      mode7_attribution?: unknown[];
      confidence?: number | null;
      inversion_risk?: number | null;
      verification_mode?: string | null;
      verification_verdict?: string | null;
      verification_threshold?: number | null;
      verification_score?: number | null;
      verification_score_source?: string | null;
      verification_invalid_mode?: string | null;
    }
  | {
      type: 'word_spans';
      spans: LiveWordSpan[];
      structural_token_indices?: number[];
      total_tokens_covered: number;
    }
  | { type: 'error'; message: string; retryable?: boolean }
  | { type: 'complete'; total_tokens: number };

export function emptyLiveTrace(modelId = 'EleutherAI/pythia-160m'): ReplayTrace {
  return {
    tokens: [],
    per_token_frames: [],
    model_id: modelId,
    neuron_covers: { per_class_neuron_covers: {} },
  } as ReplayTrace;
}

export function appendLiveEvent(trace: ReplayTrace, event: LiveTraceEvent): ReplayTrace {
  if (event.type === 'manifest') {
    return {
      ...trace,
      model_id: event.manifest.model_id,
      model_manifest: event.manifest,
    } as ReplayTrace;
  }

  if (event.type === 'neuron_covers') {
    const normalised: Record<string, NeuronCoverMember[]> = {};
    for (const [cls, members] of Object.entries(event.per_class_neuron_covers)) {
      normalised[cls] = (members ?? []).map(normaliseCoverMember);
    }
    return {
      ...trace,
      neuron_covers: {
        per_class_neuron_covers: normalised,
      },
    } as ReplayTrace;
  }

  if (event.type === 'word_spans') {
    return {
      ...trace,
      word_spans: {
        spans: event.spans,
        structural_token_indices: event.structural_token_indices ?? [],
        total_tokens_covered: event.total_tokens_covered,
      },
    } as ReplayTrace;
  }

  if (event.type !== 'token') return trace;

  const token = { token_index: event.token_index, token: event.token };
  const frame = {
    token_index: event.token_index,
    token: event.token,
    top_activated_neurons: event.top_activated_neurons ?? [],
    mode7_attribution: event.mode7_attribution ?? [],
    confidence: event.confidence ?? null,
    inversion_risk: event.inversion_risk ?? null,
    verification_mode: event.verification_mode ?? null,
    verification_verdict: event.verification_verdict ?? null,
    verification_threshold: event.verification_threshold ?? null,
    verification_score: event.verification_score ?? null,
    verification_score_source: event.verification_score_source ?? null,
    verification_invalid_mode: event.verification_invalid_mode ?? null,
  };

  const tokens = [...trace.tokens];
  const frames = [...trace.per_token_frames];
  tokens[event.token_index] = token;
  frames[event.token_index] = frame;

  return {
    ...trace,
    tokens: tokens.filter(Boolean),
    per_token_frames: frames.filter(Boolean),
  };
}

export function resolveAtlasApiBaseUrl(explicit?: string): string {
  if (explicit && explicit.length > 0) return trimTrailingSlash(explicit);
  const envBase = import.meta.env?.VITE_ATLAS_API_BASE_URL;
  if (typeof envBase === 'string' && envBase.length > 0) {
    return trimTrailingSlash(envBase);
  }
  return DEFAULT_BASE_URL;
}

export function resolveLiveStreamUrl(streamUrl: string, baseUrl: string): string {
  if (/^https?:\/\//i.test(streamUrl)) return streamUrl;

  if (baseUrl.startsWith('/api/atlas') && streamUrl.startsWith('/atlas/')) {
    return `/api${streamUrl}`;
  }

  if (baseUrl.startsWith('/')) {
    return streamUrl.startsWith('/') ? streamUrl : `${baseUrl}/${streamUrl}`;
  }

  return new URL(streamUrl, baseUrl).toString();
}

export function classifyLiveSessionFailure(
  status: number,
  detail: string,
): AtlasLiveFailureKind {
  const lower = detail.toLowerCase();
  if (status === 401 && lower.includes('missing')) return 'missing_invite';
  if (status === 401 || status === 403) return 'invalid_invite';
  if (status === 429) {
    if (lower.includes('per-ip') || lower.includes('ip session')) {
      return 'rate_limited_ip';
    }
    if (lower.includes('invite-code') || lower.includes('invite code')) {
      return 'rate_limited_code';
    }
    return 'rate_limited';
  }
  if (
    status === 502 ||
    status === 503 ||
    status === 504 ||
    lower.includes('worker') ||
    lower.includes('allowlist is not configured')
  ) {
    return 'worker_unavailable';
  }
  return 'bad_response';
}

export function errorFromLiveProof(proof: LiveRealModeProof | null | undefined): AtlasLiveError {
  return new AtlasLiveError('unverified_model', liveProofFailureMessage(proof), {
    httpStatus: proof?.http_status,
    detail: proof?.detail ?? proof?.load_error ?? proof?.verdict,
  });
}

async function readErrorDetail(resp: Response): Promise<string> {
  try {
    const body = (await resp.json()) as { detail?: unknown };
    if (typeof body.detail === 'string' && body.detail.trim().length > 0) {
      return body.detail;
    }
    if (body.detail !== undefined) return JSON.stringify(body.detail);
  } catch {
    // Fall through to status text.
  }
  return resp.statusText || `HTTP ${resp.status}`;
}

function retryAfterSeconds(resp: Response): number | undefined {
  const raw = resp.headers.get('Retry-After');
  if (!raw) return undefined;
  const parsed = Number(raw);
  if (Number.isFinite(parsed) && parsed >= 0) return Math.ceil(parsed);
  return undefined;
}

export async function createLiveSession(
  request: CreateLiveSessionRequest,
  inviteCode: string,
  options?: {
    baseUrl?: string;
    fetchImpl?: typeof fetch;
    signal?: AbortSignal;
  },
): Promise<CreateLiveSessionResponse> {
  const baseUrl = resolveAtlasApiBaseUrl(options?.baseUrl);
  const fetchImpl = options?.fetchImpl ?? (typeof fetch !== 'undefined' ? fetch : undefined);
  if (!fetchImpl) throw new AtlasLiveError('worker_unavailable', liveFailureMessage('worker_unavailable'));
  if (!inviteCode.trim()) throw new AtlasLiveError('missing_invite', liveFailureMessage('missing_invite'));

  let resp: Response;
  try {
    resp = await fetchImpl(`${baseUrl}/live/session`, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'X-Atlas-Invite-Code': inviteCode.trim(),
      },
      body: JSON.stringify(request),
      signal: options?.signal,
    });
  } catch (err) {
    throw new AtlasLiveError('worker_unavailable', liveFailureMessage('worker_unavailable'), {
      detail: err instanceof Error ? err.message : String(err),
      cause: err,
    });
  }

  if (!resp.ok) {
    const detail = await readErrorDetail(resp);
    const retryAfter = retryAfterSeconds(resp);
    const kind = classifyLiveSessionFailure(resp.status, detail);
    throw new AtlasLiveError(kind, liveFailureMessage(kind, retryAfter), {
      httpStatus: resp.status,
      detail,
      retryAfterSeconds: retryAfter,
    });
  }

  const body = (await resp.json()) as CreateLiveSessionResponse;
  return {
    ...body,
    stream_url: resolveLiveStreamUrl(body.stream_url, baseUrl),
  };
}

export interface LiveEventSourceLike {
  onerror: ((event: Event) => void) | null;
  onopen?: ((event: Event) => void) | null;
  addEventListener(type: string, listener: (event: Event) => void): void;
  close(): void;
}

export type LiveEventSourceConstructor = new (url: string) => LiveEventSourceLike;

export interface LiveEventStreamHandle {
  readonly closed: boolean;
  close: () => void;
}

function eventData(event: Event): string | null {
  const data = (event as MessageEvent).data;
  return typeof data === 'string' ? data : null;
}

function errorFromStreamEvent(event: { message: string; retryable?: boolean }): AtlasLiveError {
  const kind: AtlasLiveFailureKind =
    event.message.toLowerCase().includes('worker') ? 'worker_unavailable' : 'stream_disconnected';
  return new AtlasLiveError(kind, liveFailureMessage(kind), {
    detail: event.message,
  });
}

export function openLiveEventStream(
  streamUrl: string,
  options: {
    eventSourceImpl?: LiveEventSourceConstructor;
    maxTransportErrors?: number;
    onEvent: (event: LiveTraceEvent) => void;
    onFailure: (error: AtlasLiveError) => void;
    onTransportError?: (attempt: number, maxAttempts: number) => void;
  },
): LiveEventStreamHandle {
  const EventSourceImpl =
    options.eventSourceImpl ??
    (typeof EventSource !== 'undefined' ? (EventSource as LiveEventSourceConstructor) : undefined);
  if (!EventSourceImpl) {
    const closedHandle = {
      closed: true,
      close: () => undefined,
    };
    options.onFailure(
      new AtlasLiveError('worker_unavailable', liveFailureMessage('worker_unavailable')),
    );
    return closedHandle;
  }

  const source = new EventSourceImpl(streamUrl);
  const maxTransportErrors = options.maxTransportErrors ?? 1;
  let closed = false;
  let transportErrors = 0;

  const close = (): void => {
    if (closed) return;
    closed = true;
    source.close();
  };

  const fail = (error: AtlasLiveError): void => {
    if (closed) return;
    close();
    options.onFailure(error);
  };

  const handleMessage = (event: Event): void => {
    if (closed) return;
    const raw = eventData(event);
    if (raw === null) return;
    try {
      const parsed = JSON.parse(raw) as LiveTraceEvent;
      if (parsed.type === 'error') {
        fail(errorFromStreamEvent(parsed));
        return;
      }
      options.onEvent(parsed);
    } catch (err) {
      fail(
        new AtlasLiveError('bad_response', liveFailureMessage('bad_response'), {
          detail: err instanceof Error ? err.message : String(err),
          cause: err,
        }),
      );
    }
  };

  for (const eventName of [
    'manifest',
    'knob_resolution',
    'neuron_covers',
    'token',
    'word_spans',
    'error',
    'complete',
  ]) {
    source.addEventListener(eventName, handleMessage);
  }

  source.onerror = () => {
    if (closed) return;
    transportErrors += 1;
    if (transportErrors > maxTransportErrors) {
      fail(new AtlasLiveError('stream_disconnected', liveFailureMessage('stream_disconnected')));
      return;
    }
    options.onTransportError?.(transportErrors, maxTransportErrors);
  };

  return {
    get closed() {
      return closed;
    },
    close,
  };
}

export async function fetchLiveRealModeProof(options?: {
  baseUrl?: string;
  fetchImpl?: typeof fetch;
  signal?: AbortSignal;
}): Promise<LiveRealModeProof> {
  const baseUrl = resolveAtlasApiBaseUrl(options?.baseUrl);
  const fetchImpl = options?.fetchImpl ?? (typeof fetch !== 'undefined' ? fetch : undefined);
  if (!fetchImpl) throw new Error('Atlas LIVE proof requires fetch support');

  const resp = await fetchImpl(`${baseUrl}/live/health/realmode`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    signal: options?.signal,
  });
  let body: Record<string, unknown> = {};
  try {
    body = (await resp.json()) as Record<string, unknown>;
  } catch {
    body = {};
  }

  const loadError =
    typeof body.load_error === 'string'
      ? body.load_error
      : body.load_error === null
        ? null
        : typeof body.detail === 'string'
          ? body.detail
          : resp.ok
            ? null
            : `HTTP ${resp.status}`;
  const isRealModel =
    resp.ok &&
    body.is_real_model === true &&
    body.model_loaded === true &&
    loadError === null;

  return {
    verdict: typeof body.verdict === 'string' ? body.verdict : isRealModel ? 'REAL_PYTHIA_WEIGHTS_LOADED' : 'NOT_REAL_PYTHIA_WEIGHTS',
    is_real_model: isRealModel,
    model_loaded: body.model_loaded === true,
    load_error: loadError,
    fake_runtime_env:
      typeof body.fake_runtime_env === 'boolean' ? body.fake_runtime_env : undefined,
    manifest_is_real_model:
      typeof body.manifest_is_real_model === 'boolean'
        ? body.manifest_is_real_model
        : undefined,
    model_id: typeof body.model_id === 'string' ? body.model_id : undefined,
    worker_version:
      typeof body.worker_version === 'string' ? body.worker_version : undefined,
    detail: typeof body.detail === 'string' ? body.detail : undefined,
    http_status: resp.status,
    checked_at: new Date().toISOString(),
  };
}

function trimTrailingSlash(url: string): string {
  return url.endsWith('/') ? url.slice(0, -1) : url;
}

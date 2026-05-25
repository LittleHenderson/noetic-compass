import type { ReplayTrace } from './replayController';
import { bandForConfidence, type ConfidenceBand } from './confidenceBands';

const DEFAULT_BASE_URL = '/api/atlas';

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
  if (!fetchImpl) throw new Error('Atlas LIVE requires fetch support');
  if (!inviteCode.trim()) throw new Error('Atlas LIVE invite code is required');

  const resp = await fetchImpl(`${baseUrl}/live/session`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'X-Atlas-Invite-Code': inviteCode.trim(),
    },
    body: JSON.stringify(request),
    signal: options?.signal,
  });

  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const body = (await resp.json()) as { detail?: unknown };
      if (typeof body.detail === 'string') detail = body.detail;
    } catch {
      // Keep HTTP status fallback.
    }
    throw new Error(`Atlas LIVE session failed: ${detail}`);
  }

  const body = (await resp.json()) as CreateLiveSessionResponse;
  return {
    ...body,
    stream_url: resolveLiveStreamUrl(body.stream_url, baseUrl),
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

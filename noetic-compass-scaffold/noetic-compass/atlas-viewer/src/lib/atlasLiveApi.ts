import type { ReplayTrace } from './replayController';

const DEFAULT_BASE_URL = '/api/atlas';

export type LiveProbeName =
  | 'active_trace'
  | 'blindspots_f1'
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

export type LiveTraceEvent =
  | { type: 'manifest'; manifest: LiveManifest }
  | { type: 'neuron_covers'; per_class_neuron_covers: Record<string, string[]> }
  | {
      type: 'token';
      token_index: number;
      token: string;
      top_activated_neurons?: unknown[];
      mode7_attribution?: unknown[];
      confidence?: number | null;
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
    return {
      ...trace,
      neuron_covers: {
        per_class_neuron_covers: event.per_class_neuron_covers,
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

function trimTrailingSlash(url: string): string {
  return url.endsWith('/') ? url.slice(0, -1) : url;
}

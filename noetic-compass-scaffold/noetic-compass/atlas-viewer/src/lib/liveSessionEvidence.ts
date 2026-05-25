import {
  isLiveRealModeProofVerified,
  type CreateLiveSessionResponse,
  type LiveManifest,
  type LiveRealModeProof,
  type ResolvedKnobs,
} from './atlasLiveApi';

export type LiveSessionEvidenceKind =
  | 'real_live'
  | 'replay_fallback'
  | 'unverified_live';

export type LiveSessionEvidenceStatus =
  | 'verified_real_model'
  | 'replay_fallback'
  | 'unverified'
  | 'failed';

export interface LiveSessionEvidenceInput {
  runtimeMode?: 'live' | 'replay';
  realModeProof?: LiveRealModeProof | null;
  sessionId?: string | null;
  traceId?: string | null;
  modelId?: string | null;
  manifest?: LiveManifest | null;
  tokenEventCount?: number | null;
  completeTotalTokens?: number | null;
  methodConfig?: {
    enabled_methods?: string[];
    knobs?: Record<string, Record<string, unknown>>;
    overlays?: Record<string, unknown>;
    verification_mode?: string;
    [key: string]: unknown;
  } | null;
  resolvedKnobs?: ResolvedKnobs | null;
  sessionResponse?:
    | (Partial<CreateLiveSessionResponse> & Record<string, unknown>)
    | null;
  streamUrl?: string | null;
  failureReason?: string | Error | null;
  checkedAt?: string | null;
  extra?: Record<string, unknown> | null;
}

export interface LiveSessionEvidenceSummary {
  schema: 'atlas_live_session_evidence_v0';
  kind: LiveSessionEvidenceKind;
  status: LiveSessionEvidenceStatus;
  title: string;
  plainEnglish: string;
  modelId: string | null;
  workerVersion: string | null;
  sessionId: string | null;
  traceId: string | null;
  checkedAt: string | null;
  proof: LiveSessionProofSummary;
  manifest: Record<string, unknown> | null;
  tokenSummary: {
    tokenEventCount: number;
    completeTotalTokens: number | null;
    text: string;
  };
  consumedMethodKnobs: Record<string, Record<string, unknown>>;
  sentButUnconsumedKnobNames: Record<string, string[]>;
  sanitizedRuntimeFacts: Record<string, unknown>;
  redactions: string[];
}

export interface LiveSessionProofSummary {
  verified: boolean;
  verdict: string | null;
  isRealModel: boolean | null;
  modelLoaded: boolean | null;
  loadError: string | null;
  fakeRuntimeEnv: boolean | null;
  manifestIsRealModel: boolean | null;
  httpStatus: number | null;
  failureReason: string | null;
}

interface RedactionState {
  paths: string[];
}

const REDACTED = '[redacted]';
const SENSITIVE_QUERY_KEYS = new Set([
  'token',
  'stream_token',
  'access_token',
  'api_key',
  'apikey',
  'key',
  'invite_code',
  'invite',
  'code',
]);

const URL_WITH_QUERY_PATTERN = /^(https?:\/\/|\/)[^\s?]+[?][^\s]+$/i;
const BEARER_PATTERN = /\bBearer\s+[A-Za-z0-9._~+/=-]+/gi;
const QUERY_LIKE_SECRET_PATTERN =
  /\b(stream_token|access_token|api_key|apikey|invite_code|invite|token|key)=([^&\s]+)/gi;

export function buildLiveSessionEvidence(
  input: LiveSessionEvidenceInput,
): LiveSessionEvidenceSummary {
  const state: RedactionState = { paths: [] };
  const manifest = input.manifest ?? null;
  const proof = input.realModeProof ?? null;
  const failureReason = normaliseFailure(input.failureReason);
  const verifiedProof = isLiveRealModeProofVerified(proof);
  const manifestIsReal = manifest?.is_real_model === true;
  const hasFailure = failureReason !== null;
  const runtimeMode = input.runtimeMode ?? 'live';
  const isReplay = runtimeMode === 'replay';
  const isRealLive = !isReplay && !hasFailure && verifiedProof && manifestIsReal;
  const kind: LiveSessionEvidenceKind = isRealLive
    ? 'real_live'
    : isReplay || hasFailure
      ? 'replay_fallback'
      : 'unverified_live';
  const status: LiveSessionEvidenceStatus = isRealLive
    ? 'verified_real_model'
    : hasFailure
      ? 'failed'
      : isReplay
        ? 'replay_fallback'
        : 'unverified';

  const modelId =
    input.modelId ?? manifest?.model_id ?? proof?.model_id ?? input.sessionResponse?.model_id ?? null;
  const workerVersion = manifest?.worker_version ?? proof?.worker_version ?? null;
  const sanitizedFailureReason = sanitiseString(
    failureReason,
    state,
    'proof.failureReason',
  );
  const tokenEventCount = normaliseCount(input.tokenEventCount);
  const completeTotalTokens =
    input.completeTotalTokens === null || input.completeTotalTokens === undefined
      ? null
      : normaliseCount(input.completeTotalTokens);
  const consumedMethodKnobs = sanitiseObject(
    filterConsumedKnobs(input.resolvedKnobs ?? null, input.methodConfig ?? null),
    state,
    'consumedMethodKnobs',
  ) as Record<string, Record<string, unknown>>;
  const sentButUnconsumedKnobNames = unconsumedKnobNames(
    input.methodConfig ?? null,
    input.resolvedKnobs ?? null,
  );

  const sanitizedRuntimeFacts = sanitiseObject(
    {
      sessionResponse: input.sessionResponse ?? null,
      streamUrl: input.streamUrl ?? input.sessionResponse?.stream_url ?? null,
      extra: input.extra ?? null,
    },
    state,
    'sanitizedRuntimeFacts',
  ) as Record<string, unknown>;

  return {
    schema: 'atlas_live_session_evidence_v0',
    kind,
    status,
    title: titleFor(kind, status),
    plainEnglish: plainEnglishFor(kind, status, modelId, sanitizedFailureReason),
    modelId,
    workerVersion,
    sessionId: sanitiseString(input.sessionId ?? input.sessionResponse?.session_id ?? null, state, 'sessionId'),
    traceId: sanitiseString(input.traceId ?? null, state, 'traceId'),
    checkedAt: input.checkedAt ?? proof?.checked_at ?? null,
    proof: buildProofSummary(proof, verifiedProof, sanitizedFailureReason, state),
    manifest: manifest
      ? (sanitiseObject(manifest as unknown as Record<string, unknown>, state, 'manifest') as Record<
          string,
          unknown
        >)
      : null,
    tokenSummary: {
      tokenEventCount,
      completeTotalTokens,
      text: tokenSummaryText(tokenEventCount, completeTotalTokens),
    },
    consumedMethodKnobs,
    sentButUnconsumedKnobNames,
    sanitizedRuntimeFacts,
    redactions: [...state.paths],
  };
}

export function redactEvidenceValue(value: unknown): unknown {
  return sanitiseObject(value, { paths: [] }, 'value');
}

function buildProofSummary(
  proof: LiveRealModeProof | null,
  verified: boolean,
  sanitizedFailureReason: string | null,
  state: RedactionState,
): LiveSessionProofSummary {
  return {
    verified,
    verdict: proof?.verdict ?? null,
    isRealModel: proof?.is_real_model ?? null,
    modelLoaded: proof?.model_loaded ?? null,
    loadError: sanitiseString(proof?.load_error ?? null, state, 'proof.loadError'),
    fakeRuntimeEnv: proof?.fake_runtime_env ?? null,
    manifestIsRealModel: proof?.manifest_is_real_model ?? null,
    httpStatus: proof?.http_status ?? null,
    failureReason: sanitizedFailureReason,
  };
}

function titleFor(
  kind: LiveSessionEvidenceKind,
  status: LiveSessionEvidenceStatus,
): string {
  if (kind === 'real_live') return 'LIVE evidence: real Pythia weights verified';
  if (status === 'failed') return 'LIVE evidence: replay fallback after failure';
  if (kind === 'replay_fallback') return 'Replay evidence: fixture fallback';
  return 'LIVE evidence: not verified yet';
}

function plainEnglishFor(
  kind: LiveSessionEvidenceKind,
  status: LiveSessionEvidenceStatus,
  modelId: string | null,
  failureReason: string | null,
): string {
  const model = modelId ?? 'the selected model';
  if (kind === 'real_live') {
    return `This session was driven by ${model} loaded on the LIVE worker, and the real-weight proof passed before the stream was accepted.`;
  }
  if (status === 'failed') {
    return `LIVE did not complete, so the cockpit should treat this as replay/fallback evidence. Reason: ${failureReason ?? 'unknown failure'}.`;
  }
  if (kind === 'replay_fallback') {
    return 'This summary describes replay fixture output, not a real-time model stream.';
  }
  return 'The cockpit has not received enough proof to claim real-time model evidence for this session.';
}

function tokenSummaryText(
  tokenEventCount: number,
  completeTotalTokens: number | null,
): string {
  if (completeTotalTokens === null) {
    return `${tokenEventCount} token event${tokenEventCount === 1 ? '' : 's'} received; stream completion count not reported.`;
  }
  return `${tokenEventCount} token event${tokenEventCount === 1 ? '' : 's'} received; complete event reported ${completeTotalTokens} total token${completeTotalTokens === 1 ? '' : 's'}.`;
}

function filterConsumedKnobs(
  resolvedKnobs: ResolvedKnobs | null,
  methodConfig: LiveSessionEvidenceInput['methodConfig'],
): Record<string, Record<string, unknown>> {
  if (!resolvedKnobs) return {};
  const requestedKnobs = methodConfig?.knobs ?? {};
  const out: Record<string, Record<string, unknown>> = {};
  for (const [methodId, knobs] of Object.entries(resolvedKnobs)) {
    if (!isPlainRecord(knobs)) continue;
    const methodRequested = requestedKnobs[methodId];
    const methodOut: Record<string, unknown> = {};
    for (const [knobName, value] of Object.entries(knobs)) {
      // Worker-only metadata such as "active" and "cover_available" is useful
      // evidence even when it was not a user-sent knob. User-sent knobs are
      // included only if the worker echoed them in resolved_knobs.
      if (isWorkerMetadataKnob(knobName) || isPlainRecord(methodRequested) && knobName in methodRequested) {
        methodOut[knobName] = value;
      }
    }
    if (Object.keys(methodOut).length > 0) out[methodId] = methodOut;
  }
  return out;
}

function unconsumedKnobNames(
  methodConfig: LiveSessionEvidenceInput['methodConfig'],
  resolvedKnobs: ResolvedKnobs | null,
): Record<string, string[]> {
  const requested = methodConfig?.knobs ?? {};
  const out: Record<string, string[]> = {};
  for (const [methodId, knobs] of Object.entries(requested)) {
    if (!isPlainRecord(knobs)) continue;
    const consumed = resolvedKnobs?.[methodId] ?? {};
    const missing = Object.keys(knobs).filter((name) => !(name in consumed));
    if (missing.length > 0) out[methodId] = missing.sort();
  }
  return out;
}

function isWorkerMetadataKnob(name: string): boolean {
  return name === 'active' || name === 'cover_available';
}

function normaliseFailure(failureReason: string | Error | null | undefined): string | null {
  if (!failureReason) return null;
  return failureReason instanceof Error ? failureReason.message : failureReason;
}

function normaliseCount(value: number | null | undefined): number {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) return 0;
  return Math.floor(value);
}

function sanitiseObject(value: unknown, state: RedactionState, path: string): unknown {
  if (value === null || value === undefined) return value;
  if (typeof value === 'string') return sanitiseString(value, state, path);
  if (typeof value !== 'object') return value;
  if (Array.isArray(value)) {
    return value.map((item, idx) => sanitiseObject(item, state, `${path}[${idx}]`));
  }
  const out: Record<string, unknown> = {};
  for (const [key, child] of Object.entries(value as Record<string, unknown>)) {
    const childPath = `${path}.${key}`;
    if (isSensitiveKey(key)) {
      out[key] = REDACTED;
      state.paths.push(childPath);
      continue;
    }
    out[key] = sanitiseObject(child, state, childPath);
  }
  return out;
}

function sanitiseString(
  value: string | null,
  state: RedactionState,
  path: string,
): string | null {
  if (value === null) return null;
  let out = value.replace(BEARER_PATTERN, `Bearer ${REDACTED}`);
  if (out !== value) state.paths.push(path);
  if (URL_WITH_QUERY_PATTERN.test(out)) {
    const redacted = redactUrlQuery(out, state, path);
    if (redacted !== out) out = redacted;
  } else {
    const redacted = out.replace(QUERY_LIKE_SECRET_PATTERN, (_match, key) => {
      return `${key}=${REDACTED}`;
    });
    if (redacted !== out) {
      out = redacted;
      state.paths.push(path);
    }
  }
  return out;
}

function redactUrlQuery(value: string, state: RedactionState, path: string): string {
  const isRelative = value.startsWith('/');
  let parsed: URL;
  try {
    parsed = new URL(value, 'https://atlas.local');
  } catch {
    return value;
  }
  let changed = false;
  for (const key of [...parsed.searchParams.keys()]) {
    if (SENSITIVE_QUERY_KEYS.has(key.toLowerCase())) {
      parsed.searchParams.set(key, REDACTED);
      changed = true;
    }
  }
  if (!changed) return value;
  state.paths.push(path);
  if (isRelative) {
    return `${parsed.pathname}${parsed.search}${parsed.hash}`;
  }
  return parsed.toString();
}

function isPlainRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function isSensitiveKey(key: string): boolean {
  const normalised = key.toLowerCase().replace(/[^a-z0-9]/g, '');
  return (
    normalised === 'authorization' ||
    normalised === 'bearer' ||
    normalised === 'bearertoken' ||
    normalised === 'token' ||
    normalised === 'streamtoken' ||
    normalised === 'accesstoken' ||
    normalised === 'apikey' ||
    normalised === 'secret' ||
    normalised === 'invite' ||
    normalised === 'invitecode' ||
    normalised === 'xatlasinvitecode'
  );
}

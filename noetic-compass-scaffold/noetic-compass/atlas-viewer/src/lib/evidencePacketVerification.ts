import { resolveAtlasApiBaseUrl } from './atlasLiveApi';

export interface EvidenceVerifyCheck {
  artifact: string;
  expected: string | null;
  actual: string | null;
  match: boolean;
  notes: string | null;
}

export interface EvidenceVerifyResponse {
  trace_id: string;
  verified_at: string;
  checks: EvidenceVerifyCheck[];
  overall: 'all_match' | 'partial_mismatch' | 'unable_to_verify' | string;
}

export interface EvidencePacketVerificationOptions {
  baseUrl?: string;
  fetchImpl?: typeof fetch;
  signal?: AbortSignal;
}

export class EvidencePacketVerificationError extends Error {
  readonly httpStatus?: number;
  readonly detail?: string;

  constructor(message: string, opts?: { httpStatus?: number; detail?: string; cause?: unknown }) {
    super(message);
    this.name = 'EvidencePacketVerificationError';
    this.httpStatus = opts?.httpStatus;
    this.detail = opts?.detail;
    if (opts?.cause !== undefined) {
      (this as Error & { cause?: unknown }).cause = opts.cause;
    }
  }
}

export function resolveEvidenceApiBaseUrl(explicit?: string): string {
  const atlasBaseUrl = resolveAtlasApiBaseUrl(explicit);
  if (atlasBaseUrl.endsWith('/api/atlas')) {
    return atlasBaseUrl.slice(0, -'/atlas'.length);
  }
  if (atlasBaseUrl.endsWith('/atlas')) {
    return atlasBaseUrl.slice(0, -'/atlas'.length);
  }
  return atlasBaseUrl;
}

export function evidencePacketVerifyUrl(traceId: string, explicitBaseUrl?: string): string {
  return `${resolveEvidenceApiBaseUrl(explicitBaseUrl)}/evidence/${encodeURIComponent(traceId)}/verify`;
}

export async function verifyEvidencePacket(
  traceId: string,
  options?: EvidencePacketVerificationOptions,
): Promise<EvidenceVerifyResponse> {
  const trimmed = traceId.trim();
  if (!trimmed) {
    throw new EvidencePacketVerificationError('Evidence Packet trace_id is required.');
  }
  const fetchImpl = options?.fetchImpl ?? (typeof fetch !== 'undefined' ? fetch : undefined);
  if (!fetchImpl) {
    throw new EvidencePacketVerificationError('Evidence Packet verification requires fetch support.');
  }

  let response: Response;
  try {
    response = await fetchImpl(evidencePacketVerifyUrl(trimmed, options?.baseUrl), {
      method: 'POST',
      headers: { Accept: 'application/json' },
      signal: options?.signal,
    });
  } catch (error) {
    throw new EvidencePacketVerificationError('Evidence Packet verify request failed.', {
      detail: error instanceof Error ? error.message : String(error),
      cause: error,
    });
  }

  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  if (!response.ok) {
    const detail = responseDetail(body) ?? response.statusText;
    throw new EvidencePacketVerificationError(
      detail || `Evidence Packet verify failed with HTTP ${response.status}.`,
      {
        httpStatus: response.status,
        detail,
      },
    );
  }

  return parseEvidenceVerifyResponse(body);
}

function parseEvidenceVerifyResponse(raw: unknown): EvidenceVerifyResponse {
  if (!isRecord(raw)) {
    throw new EvidencePacketVerificationError('Evidence Packet verify response was malformed.');
  }
  const checksRaw = raw.checks;
  if (!Array.isArray(checksRaw)) {
    throw new EvidencePacketVerificationError('Evidence Packet verify checks were malformed.');
  }
  return {
    trace_id: requiredString(raw.trace_id, 'trace_id'),
    verified_at: requiredString(raw.verified_at, 'verified_at'),
    overall: requiredString(raw.overall, 'overall'),
    checks: checksRaw.map(parseEvidenceVerifyCheck),
  };
}

function parseEvidenceVerifyCheck(raw: unknown): EvidenceVerifyCheck {
  if (!isRecord(raw)) {
    throw new EvidencePacketVerificationError('Evidence Packet verify check was malformed.');
  }
  return {
    artifact: requiredString(raw.artifact, 'checks[].artifact'),
    expected: nullableString(raw.expected),
    actual: nullableString(raw.actual),
    match: raw.match === true,
    notes: nullableString(raw.notes),
  };
}

function responseDetail(raw: unknown): string | undefined {
  if (!isRecord(raw)) return undefined;
  const detail = raw.detail;
  if (typeof detail === 'string') return detail;
  if (detail !== undefined) return JSON.stringify(detail);
  return undefined;
}

function requiredString(raw: unknown, field: string): string {
  if (typeof raw === 'string' && raw.length > 0) return raw;
  throw new EvidencePacketVerificationError(
    `Evidence Packet verify response field "${field}" must be a non-empty string.`,
  );
}

function nullableString(raw: unknown): string | null {
  if (raw === null || raw === undefined) return null;
  return typeof raw === 'string' ? raw : null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

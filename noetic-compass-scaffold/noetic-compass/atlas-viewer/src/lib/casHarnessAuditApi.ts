import {
  isAuditVerdict,
  type AuditStatus,
  type AuditVerdict,
  type ProvenanceChip,
  type ProvenanceChipId,
} from './casHarnessAudit';

const DEFAULT_BASE_URL = '/api/cas-harness/audit';

const PROVENANCE_CHIP_IDS: readonly ProvenanceChipId[] = [
  'model_proof',
  'cas_readout',
  'causal_proof',
  'control_proof',
  'output_proof',
  'packet_proof',
];

const AUDIT_STATUSES: readonly AuditStatus[] = [
  'verified',
  'present',
  'missing',
  'failed',
  'unavailable',
];

const STATUS_LABELS: Record<AuditStatus, string> = {
  verified: 'Verified',
  present: 'Present',
  missing: 'Missing',
  failed: 'Failed',
  unavailable: 'Unavailable',
};

export type CasHarnessAuditMode =
  | 'BALANCED'
  | 'HIGH_PRECISION'
  | 'MAX_COVERAGE_TRIAGE';

export type CasHarnessAuditSessionStatus =
  | 'DRAFT'
  | 'VALIDATING'
  | 'RUNNING'
  | 'EVIDENCE_PENDING'
  | 'EVIDENCE_READY'
  | 'COMPLETE'
  | 'FAILED'
  | 'SCAFFOLD_PENDING_RUNNER';

export type CasHarnessModelStatus =
  | 'CONNECTED'
  | 'VALIDATING'
  | 'READY'
  | 'FAILED'
  | 'NOT_CONNECTED_MOCK'
  | string;

export interface CasHarnessAuditSessionRequest {
  model_id?: string | null;
  endpoint_url?: string | null;
  audit_mode?: CasHarnessAuditMode;
  prompt?: string | null;
  scenario_text?: string | null;
  selected_modules: string[];
  evidence_packet_trace_id?: string | null;
  license_key?: string | null;
}

export interface CasHarnessAuditLifecycleEvent {
  status: CasHarnessAuditSessionStatus;
  message: string;
  timestamp: string;
}

export interface CasHarnessAuditSession {
  audit_id: string;
  status: CasHarnessAuditSessionStatus;
  model_status: CasHarnessModelStatus;
  model_id: string | null;
  endpoint_url: string | null;
  audit_mode: CasHarnessAuditMode;
  prompt_summary: string | null;
  scenario_summary: string | null;
  selected_modules: string[];
  created_at: string | null;
  updated_at: string | null;
  verdict: AuditVerdict | null;
  confidence: number | null;
  evidence_packet_trace_id: string | null;
  atlas_deep_link: string | null;
  provenance_chips: ProvenanceChip[];
  lifecycle: CasHarnessAuditLifecycleEvent[];
}

export interface CasHarnessAuditSessionList {
  sessions: CasHarnessAuditSession[];
}

export interface CasHarnessAuditApiOptions {
  baseUrl?: string;
  fetchImpl?: typeof fetch;
  signal?: AbortSignal;
}

export class CasHarnessAuditApiError extends Error {
  readonly httpStatus?: number;
  readonly detail?: string;

  constructor(
    message: string,
    opts?: {
      httpStatus?: number;
      detail?: string;
      cause?: unknown;
    },
  ) {
    super(message);
    this.name = 'CasHarnessAuditApiError';
    this.httpStatus = opts?.httpStatus;
    this.detail = opts?.detail;
    if (opts?.cause !== undefined) {
      (this as Error & { cause?: unknown }).cause = opts.cause;
    }
  }
}

export function resolveCasHarnessAuditBaseUrl(explicit?: string): string {
  if (explicit && explicit.length > 0) return trimTrailingSlash(explicit);

  const atlasBase = import.meta.env?.VITE_ATLAS_API_BASE_URL;
  if (typeof atlasBase === 'string' && atlasBase.length > 0) {
    return deriveAuditBaseUrlFromAtlasBase(atlasBase);
  }

  return DEFAULT_BASE_URL;
}

export async function createCasHarnessAuditSession(
  request: CasHarnessAuditSessionRequest,
  options?: CasHarnessAuditApiOptions,
): Promise<CasHarnessAuditSession> {
  const response = await requestJson(`${baseUrl(options)}/session`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify(request),
    signal: options?.signal,
  }, options);
  return parseAuditSessionResponse(response);
}

export async function getCasHarnessAuditSessionStatus(
  auditId: string,
  options?: CasHarnessAuditApiOptions,
): Promise<CasHarnessAuditSession> {
  assertNonEmpty('auditId', auditId);
  const response = await requestJson(
    `${baseUrl(options)}/session/${encodeURIComponent(auditId)}/status`,
    {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal: options?.signal,
    },
    options,
  );
  return parseAuditSessionResponse(response);
}

export async function listCasHarnessAuditSessions(
  options?: CasHarnessAuditApiOptions,
): Promise<CasHarnessAuditSessionList> {
  const response = await requestJson(`${baseUrl(options)}/sessions`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    signal: options?.signal,
  }, options);

  const rawSessions = Array.isArray(response)
    ? response
    : isRecord(response) && Array.isArray(response.sessions)
      ? response.sessions
      : null;
  if (!rawSessions) {
    throw new CasHarnessAuditApiError('CAS Harness audit session list response was malformed');
  }
  return {
    sessions: rawSessions.map(parseAuditSessionResponse),
  };
}

export async function startCasHarnessAuditSession(
  auditId: string,
  options?: CasHarnessAuditApiOptions,
): Promise<CasHarnessAuditSession> {
  assertNonEmpty('auditId', auditId);
  const response = await requestJson(
    `${baseUrl(options)}/session/${encodeURIComponent(auditId)}/run`,
    {
      method: 'POST',
      headers: { Accept: 'application/json' },
      signal: options?.signal,
    },
    options,
  );
  return parseAuditSessionResponse(response);
}

export function parseAuditSessionResponse(raw: unknown): CasHarnessAuditSession {
  if (!isRecord(raw)) {
    throw new CasHarnessAuditApiError('CAS Harness audit session response was not an object');
  }

  const auditId = requiredString(raw.audit_id, 'audit_id');
  const status = parseSessionStatus(raw.status);
  const modelStatus =
    typeof raw.model_status === 'string' && raw.model_status.length > 0
      ? raw.model_status
      : 'NOT_CONNECTED_MOCK';
  const auditMode = parseAuditMode(raw.audit_mode);
  const verdict = parseNullableVerdict(raw.verdict);
  const confidence = parseNullableConfidence(raw.confidence);
  const chips = Array.isArray(raw.provenance_chips)
    ? raw.provenance_chips.map(parseProvenanceChip)
    : [];
  const lifecycle = Array.isArray(raw.lifecycle)
    ? raw.lifecycle.map(parseLifecycleEvent)
    : [];

  return {
    audit_id: auditId,
    status,
    model_status: modelStatus,
    model_id: nullableString(raw.model_id),
    endpoint_url: nullableString(raw.endpoint_url),
    audit_mode: auditMode,
    prompt_summary: nullableString(raw.prompt_summary),
    scenario_summary: nullableString(raw.scenario_summary),
    selected_modules: Array.isArray(raw.selected_modules)
      ? raw.selected_modules.filter((module): module is string => typeof module === 'string')
      : [],
    created_at: nullableString(raw.created_at),
    updated_at: nullableString(raw.updated_at),
    verdict,
    confidence,
    evidence_packet_trace_id: nullableString(raw.evidence_packet_trace_id),
    atlas_deep_link: nullableString(raw.atlas_deep_link),
    provenance_chips: chips,
    lifecycle,
  };
}

async function requestJson(
  url: string,
  init: RequestInit,
  options?: CasHarnessAuditApiOptions,
): Promise<unknown> {
  const fetchImpl = options?.fetchImpl ?? (typeof fetch !== 'undefined' ? fetch : undefined);
  if (!fetchImpl) {
    throw new CasHarnessAuditApiError('CAS Harness audit API requires fetch support');
  }

  let response: Response;
  try {
    response = await fetchImpl(url, init);
  } catch (err) {
    throw new CasHarnessAuditApiError('CAS Harness audit API request failed before a response', {
      detail: err instanceof Error ? err.message : String(err),
      cause: err,
    });
  }

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new CasHarnessAuditApiError(
      `CAS Harness audit API returned HTTP ${response.status}: ${detail}`,
      {
        httpStatus: response.status,
        detail,
      },
    );
  }

  try {
    return await response.json();
  } catch (err) {
    throw new CasHarnessAuditApiError('CAS Harness audit API returned invalid JSON', {
      detail: err instanceof Error ? err.message : String(err),
      cause: err,
    });
  }
}

async function readErrorDetail(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as unknown;
    if (isRecord(body)) {
      if (typeof body.detail === 'string' && body.detail.trim().length > 0) {
        return body.detail;
      }
      if (body.detail !== undefined) return JSON.stringify(body.detail);
      if (typeof body.message === 'string' && body.message.trim().length > 0) {
        return body.message;
      }
    }
  } catch {
    // Fall through to statusText.
  }
  return response.statusText || `HTTP ${response.status}`;
}

function parseSessionStatus(raw: unknown): CasHarnessAuditSessionStatus {
  if (
    raw === 'DRAFT' ||
    raw === 'VALIDATING' ||
    raw === 'RUNNING' ||
    raw === 'EVIDENCE_PENDING' ||
    raw === 'EVIDENCE_READY' ||
    raw === 'COMPLETE' ||
    raw === 'FAILED' ||
    raw === 'SCAFFOLD_PENDING_RUNNER'
  ) {
    return raw;
  }
  throw new CasHarnessAuditApiError(`Unsupported CAS Harness audit status: ${String(raw)}`);
}

function parseAuditMode(raw: unknown): CasHarnessAuditMode {
  if (
    raw === 'BALANCED' ||
    raw === 'HIGH_PRECISION' ||
    raw === 'MAX_COVERAGE_TRIAGE'
  ) {
    return raw;
  }
  return 'BALANCED';
}

function parseNullableVerdict(raw: unknown): AuditVerdict | null {
  if (raw === null || raw === undefined) return null;
  if (isAuditVerdict(raw)) return raw;
  throw new CasHarnessAuditApiError(`Unsupported CAS Harness audit verdict: ${String(raw)}`);
}

function parseNullableConfidence(raw: unknown): number | null {
  if (raw === null || raw === undefined) return null;
  if (typeof raw === 'number' && Number.isFinite(raw) && raw >= 0 && raw <= 1) {
    return raw;
  }
  throw new CasHarnessAuditApiError('CAS Harness audit confidence must be null or a number in [0, 1]');
}

function parseProvenanceChip(raw: unknown): ProvenanceChip {
  if (!isRecord(raw)) {
    throw new CasHarnessAuditApiError('CAS Harness audit provenance chip was malformed');
  }
  if ('id' in raw || 'status' in raw || 'detail' in raw) {
    const id = parseProvenanceChipId(raw.id);
    const status = parseAuditStatus(raw.status);
    return {
      id,
      name: requiredString(raw.name, 'provenance_chips[].name'),
      status,
      statusLabel: STATUS_LABELS[status],
      detail: requiredString(raw.detail, 'provenance_chips[].detail'),
    };
  }

  const legacyLabel = requiredString(raw.label, 'provenance_chips[].label');
  return {
    id: 'packet_proof',
    name: legacyLabel,
    status: 'unavailable',
    statusLabel: STATUS_LABELS.unavailable,
    detail: requiredString(raw.value, 'provenance_chips[].value'),
  };
}

function parseProvenanceChipId(raw: unknown): ProvenanceChipId {
  if (typeof raw === 'string' && PROVENANCE_CHIP_IDS.includes(raw as ProvenanceChipId)) {
    return raw as ProvenanceChipId;
  }
  throw new CasHarnessAuditApiError(`Unsupported CAS Harness provenance chip id: ${String(raw)}`);
}

function parseAuditStatus(raw: unknown): AuditStatus {
  if (typeof raw === 'string' && AUDIT_STATUSES.includes(raw as AuditStatus)) {
    return raw as AuditStatus;
  }
  throw new CasHarnessAuditApiError(`Unsupported CAS Harness provenance status: ${String(raw)}`);
}

function parseLifecycleEvent(raw: unknown): CasHarnessAuditLifecycleEvent {
  if (!isRecord(raw)) {
    throw new CasHarnessAuditApiError('CAS Harness audit lifecycle event was malformed');
  }
  return {
    status: parseSessionStatus(raw.status),
    message: requiredString(raw.message, 'lifecycle[].message'),
    timestamp: requiredString(raw.timestamp, 'lifecycle[].timestamp'),
  };
}

function requiredString(raw: unknown, field: string): string {
  if (typeof raw === 'string' && raw.length > 0) return raw;
  throw new CasHarnessAuditApiError(`CAS Harness audit response field "${field}" must be a non-empty string`);
}

function nullableString(raw: unknown): string | null {
  if (raw === null || raw === undefined) return null;
  return typeof raw === 'string' ? raw : null;
}

function baseUrl(options?: CasHarnessAuditApiOptions): string {
  return resolveCasHarnessAuditBaseUrl(options?.baseUrl);
}

function jsonHeaders(): Record<string, string> {
  return {
    Accept: 'application/json',
    'Content-Type': 'application/json',
  };
}

function assertNonEmpty(field: string, value: string): void {
  if (typeof value !== 'string' || value.trim().length === 0) {
    throw new CasHarnessAuditApiError(`${field} must be a non-empty string`);
  }
}

function deriveAuditBaseUrlFromAtlasBase(atlasBase: string): string {
  const trimmed = trimTrailingSlash(atlasBase);

  if (trimmed === '/api/atlas') return DEFAULT_BASE_URL;
  if (trimmed.endsWith('/api/atlas')) {
    return `${trimmed.slice(0, -'/api/atlas'.length)}${DEFAULT_BASE_URL}`;
  }
  if (trimmed.endsWith('/atlas')) {
    return `${trimmed.slice(0, -'/atlas'.length)}${DEFAULT_BASE_URL}`;
  }

  return `${trimmed}${DEFAULT_BASE_URL}`;
}

function trimTrailingSlash(url: string): string {
  return url.endsWith('/') ? url.slice(0, -1) : url;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

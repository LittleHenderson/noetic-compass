import {
  isAuditVerdict,
  type AuditStatus,
  type AuditVerdict,
  type ProvenanceChip,
  type ProvenanceChipId,
  type VerifierDecision,
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

export type CasHarnessModelTargetKind = 'demo_reference' | 'api_endpoint';
export type CasHarnessModelConnectionState = 'CONNECTED' | 'CONFIGURED';
export type CasHarnessVerifiedModelStatus = 'CONNECTED' | 'READY';
export type CasHarnessCredentialMode =
  | 'none'
  | 'credential_ref'
  | 'ephemeral_secret';

export interface CasHarnessModelTargetConfig {
  kind: CasHarnessModelTargetKind;
  provider?: string | null;
  model_id?: string | null;
  endpoint_url?: string | null;
  credential_ref?: string | null;
  api_key?: string | null;
  allow_unauthenticated?: boolean;
  timeout_ms?: number;
}

export interface CasHarnessModelTargetVerificationRequest {
  target: CasHarnessModelTargetConfig;
}

export interface CasHarnessVerifiedModelTarget {
  kind: CasHarnessModelTargetKind;
  provider: string;
  model_id: string;
  endpoint_url: string | null;
  credential_mode: CasHarnessCredentialMode;
  timeout_ms: number;
}

export interface CasHarnessModelTargetVerification {
  connection_id: string;
  connection_state: CasHarnessModelConnectionState;
  model_status: CasHarnessVerifiedModelStatus;
  can_run_audit: boolean;
  target: CasHarnessVerifiedModelTarget;
  detail: string;
  checked_at: string;
  provenance_chip: ProvenanceChip;
  verdict: null;
  confidence: null;
  evidence_packet_trace_id: string | null;
  reference_evidence_packet_trace_id: string | null;
  atlas_deep_link: string | null;
}

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
  verifier_decision: VerifierDecision | null;
  lifecycle: CasHarnessAuditLifecycleEvent[];
}

export interface CasHarnessAuditSessionList {
  sessions: CasHarnessAuditSession[];
}

export interface CasHarnessAuditApiOptions {
  baseUrl?: string;
  fetchImpl?: typeof fetch;
  signal?: AbortSignal;
  authToken?: string | null;
}

export type CasHarnessScalePlanPrecision = 'fp16' | 'bf16' | 'int8' | 'int4';
export type CasHarnessScalePlanAuditDepth = 'FULL_INTERNAL' | 'LAYER_SAMPLE';
export type CasHarnessScalePlanTier =
  | 'single_worker_open_weight'
  | 'small_distributed_open_weight'
  | 'distributed_open_weight'
  | 'enterprise_distributed_open_weight';

export interface CasHarnessScalePlanRequest {
  model_id: string;
  weight_access?: 'open_weight';
  parameter_count_b: number;
  num_layers?: number | null;
  precision?: CasHarnessScalePlanPrecision;
  available_gpu_memory_gb?: number | null;
  audit_depth?: CasHarnessScalePlanAuditDepth;
}

export interface CasHarnessScalePlanWorkerAssignment {
  worker_id: string;
  layer_start: number;
  layer_end: number;
  shard_id: string;
  assigned_methods: string[];
  expected_outputs: string[];
}

export interface CasHarnessScalePlanMemoryEstimate {
  precision: CasHarnessScalePlanPrecision;
  total_weight_memory_gb: number;
  activation_overhead_gb: number;
  estimated_total_runtime_gb: number;
  estimated_memory_per_worker_gb: number;
}

export interface CasHarnessScalePlan {
  model_id: string;
  weight_access: 'open_weight';
  parameter_count_b: number;
  num_layers: number;
  scale_tier: CasHarnessScalePlanTier;
  recommended_worker_count: number;
  orchestration_pattern: string;
  worker_assignments: CasHarnessScalePlanWorkerAssignment[];
  memory_estimate: CasHarnessScalePlanMemoryEstimate;
  expected_capability: string[];
  evidence_requirements: string[];
  limitations: string[];
}

export type CasHarnessDistributedAuditStatus =
  | 'PLANNED'
  | 'DISPATCHED'
  | 'RUNNING'
  | 'MERGE_PENDING'
  | 'COMPLETE'
  | 'FAILED';

export type CasHarnessDistributedMergeStatus =
  | 'pending'
  | 'partial'
  | 'complete'
  | 'failed';

export type CasHarnessDistributedWorkerStatus =
  | 'queued'
  | 'assigned'
  | 'running'
  | 'completed'
  | 'failed';

export type CasHarnessDistributedMergeVerdict = 'FLAG_FOR_HUMAN_REVIEW';

export interface CasHarnessDistributedWorkerEvidence {
  worker_id: string;
  layer_start: number;
  layer_end: number;
  shard_id: string;
  assigned_methods: string[];
  expected_outputs: string[];
  worker_status: CasHarnessDistributedWorkerStatus;
  produced_outputs: string[];
  missing_outputs: string[];
  evidence_packet_ref: string | null;
  error_message: string | null;
  updated_at: string;
}

export interface CasHarnessDistributedAudit {
  audit_id: string;
  plan_id: string;
  status: CasHarnessDistributedAuditStatus;
  merge_status: CasHarnessDistributedMergeStatus;
  verdict: CasHarnessDistributedMergeVerdict | null;
  confidence: number | null;
  evidence_packet_trace_id: string | null;
  merge_reason: string;
  created_at: string;
  updated_at: string;
  plan: CasHarnessScalePlan;
  worker_evidence: CasHarnessDistributedWorkerEvidence[];
  ready_workers: number;
  failed_workers: number;
  total_workers: number;
  missing_outputs: string[];
}

export interface CasHarnessDistributedWorkerEvidenceRequest {
  produced_outputs: string[];
  missing_outputs?: string[];
  evidence_packet_ref?: string | null;
  error_message?: string | null;
  worker_status?: 'completed' | 'failed';
}

export type CasHarnessFleetWorkerStatus = 'active' | 'stale' | 'offline';
export type CasHarnessFleetJobStatus =
  | 'queued'
  | 'leased'
  | 'completed'
  | 'failed'
  | 'expired';
export type CasHarnessFleetRunStatus =
  | 'PREPARED'
  | 'LEASING'
  | 'MERGE_PENDING'
  | 'COMPLETE'
  | 'FAILED';
export type CasHarnessFleetVerifierGateStatus =
  | 'not_prepared'
  | 'waiting_for_workers'
  | 'waiting_for_receipts'
  | 'blocked_failed_worker'
  | 'blocked_missing_outputs'
  | 'ready_for_verifier';
export type CasHarnessFleetReadinessStatus = 'blocked' | 'waiting' | 'ready';

export interface CasHarnessFleetReadiness {
  status: CasHarnessFleetReadinessStatus;
  headline: string;
  blockers: string[];
  next_actions: string[];
  verifier_owned: boolean;
}

export interface CasHarnessFleetWorkerRegistrationRequest {
  worker_id: string;
  model_id: string;
  worker_url: string;
  gpu_type: string;
  capacity?: number;
  supported_methods: string[];
}

export interface CasHarnessFleetWorker {
  worker_id: string;
  model_id: string;
  worker_url: string;
  gpu_type: string;
  capacity: number;
  supported_methods: string[];
  registered_at: string;
  last_heartbeat_at: string;
  status: CasHarnessFleetWorkerStatus;
}

export interface CasHarnessFleetWorkerList {
  workers: CasHarnessFleetWorker[];
}

export interface CasHarnessFleetLeaseRequest {
  worker_id: string;
  lease_seconds?: number;
}

export interface CasHarnessFleetJob {
  job_id: string;
  audit_id: string;
  assigned_worker_id: string;
  layer_start: number;
  layer_end: number;
  shard_id: string;
  assigned_methods: string[];
  expected_outputs: string[];
  status: CasHarnessFleetJobStatus;
  lease_token: string | null;
  lease_expires_at: string | null;
  evidence_packet_fragment_ref: string | null;
  produced_outputs: string[];
  missing_outputs: string[];
  error_message: string | null;
  updated_at: string;
}

export interface CasHarnessFleetJobReceiptRequest {
  worker_id: string;
  lease_token: string;
  produced_outputs?: string[];
  missing_outputs?: string[];
  evidence_packet_fragment_ref?: string | null;
  error_message?: string | null;
  job_status?: 'completed' | 'failed';
}

export interface CasHarnessFleetEvidenceFragmentRefInput {
  audit_id: string;
  job_id: string;
  worker_id: string;
  model_id: string;
  layer_start: number;
  layer_end: number;
  shard_id: string;
  expected_outputs: readonly string[];
  produced_outputs: readonly string[];
  missing_outputs?: readonly string[];
}

export interface CasHarnessFleetRun {
  audit_id: string;
  status: CasHarnessFleetRunStatus;
  verifier_gate_status: CasHarnessFleetVerifierGateStatus;
  merged_packet_trace_id: string | null;
  merge_reason: string;
  created_at: string;
  updated_at: string;
  total_jobs: number;
  leased_jobs: number;
  completed_fragments: number;
  failed_jobs: number;
  registered_workers: number;
  stale_workers: string[];
  readiness: CasHarnessFleetReadiness;
  jobs: CasHarnessFleetJob[];
}

export interface CasHarnessFleetRunList {
  runs: CasHarnessFleetRun[];
}

export interface CasHarnessFleetStaleWorkerRequest {
  max_heartbeat_age_seconds?: number;
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

export async function verifyCasHarnessModelTarget(
  request: CasHarnessModelTargetVerificationRequest,
  options?: CasHarnessAuditApiOptions,
): Promise<CasHarnessModelTargetVerification> {
  const response = await requestJson(`${baseUrl(options)}/target/verify`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify(request),
    signal: options?.signal,
  }, options);
  return parseModelTargetVerificationResponse(response);
}

export async function createCasHarnessScalePlan(
  request: CasHarnessScalePlanRequest,
  options?: CasHarnessAuditApiOptions,
): Promise<CasHarnessScalePlan> {
  const response = await requestJson(`${baseUrl(options)}/scale-plan`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify(request),
    signal: options?.signal,
  }, options);
  return parseScalePlanResponse(response);
}

export async function createCasHarnessDistributedAudit(
  request: CasHarnessScalePlanRequest,
  options?: CasHarnessAuditApiOptions,
): Promise<CasHarnessDistributedAudit> {
  const response = await requestJson(`${baseUrl(options)}/distributed/session`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify(request),
    signal: options?.signal,
  }, options);
  return parseDistributedAuditResponse(response);
}

export async function dispatchCasHarnessDistributedAudit(
  auditId: string,
  options?: CasHarnessAuditApiOptions,
): Promise<CasHarnessDistributedAudit> {
  assertNonEmpty('auditId', auditId);
  const response = await requestJson(
    `${baseUrl(options)}/distributed/session/${encodeURIComponent(auditId)}/dispatch`,
    {
      method: 'POST',
      headers: { Accept: 'application/json' },
      signal: options?.signal,
    },
    options,
  );
  return parseDistributedAuditResponse(response);
}

export async function submitCasHarnessDistributedWorkerEvidence(
  auditId: string,
  workerId: string,
  request: CasHarnessDistributedWorkerEvidenceRequest,
  options?: CasHarnessAuditApiOptions,
): Promise<CasHarnessDistributedAudit> {
  assertNonEmpty('auditId', auditId);
  assertNonEmpty('workerId', workerId);
  const response = await requestJson(
    `${baseUrl(options)}/distributed/session/${encodeURIComponent(auditId)}/worker/${encodeURIComponent(workerId)}/evidence`,
    {
      method: 'POST',
      headers: jsonHeaders(),
      body: JSON.stringify(request),
      signal: options?.signal,
    },
    options,
  );
  return parseDistributedAuditResponse(response);
}

export async function mergeCasHarnessDistributedAudit(
  auditId: string,
  options?: CasHarnessAuditApiOptions,
): Promise<CasHarnessDistributedAudit> {
  assertNonEmpty('auditId', auditId);
  const response = await requestJson(
    `${baseUrl(options)}/distributed/session/${encodeURIComponent(auditId)}/merge`,
    {
      method: 'POST',
      headers: { Accept: 'application/json' },
      signal: options?.signal,
    },
    options,
  );
  return parseDistributedAuditResponse(response);
}

export async function registerCasHarnessFleetWorker(
  request: CasHarnessFleetWorkerRegistrationRequest,
  options?: CasHarnessAuditApiOptions,
): Promise<CasHarnessFleetWorker> {
  const response = await requestJson(`${baseUrl(options)}/distributed/fleet/worker/register`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify(request),
    signal: options?.signal,
  }, options);
  return parseFleetWorkerResponse(response);
}

export async function listCasHarnessFleetWorkers(
  options?: CasHarnessAuditApiOptions,
): Promise<CasHarnessFleetWorkerList> {
  const response = await requestJson(`${baseUrl(options)}/distributed/fleet/workers`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    signal: options?.signal,
  }, options);
  return parseFleetWorkerListResponse(response);
}

export async function heartbeatCasHarnessFleetWorker(
  workerId: string,
  options?: CasHarnessAuditApiOptions,
): Promise<CasHarnessFleetWorker> {
  assertNonEmpty('workerId', workerId);
  const response = await requestJson(
    `${baseUrl(options)}/distributed/fleet/worker/${encodeURIComponent(workerId)}/heartbeat`,
    {
      method: 'POST',
      headers: { Accept: 'application/json' },
      signal: options?.signal,
    },
    options,
  );
  return parseFleetWorkerResponse(response);
}

export async function scanCasHarnessFleetStaleWorkers(
  request: CasHarnessFleetStaleWorkerRequest = {},
  options?: CasHarnessAuditApiOptions,
): Promise<CasHarnessFleetWorkerList> {
  const response = await requestJson(`${baseUrl(options)}/distributed/fleet/workers/stale-scan`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify(request),
    signal: options?.signal,
  }, options);
  return parseFleetWorkerListResponse(response);
}

export async function prepareCasHarnessFleetRun(
  auditId: string,
  options?: CasHarnessAuditApiOptions,
): Promise<CasHarnessFleetRun> {
  assertNonEmpty('auditId', auditId);
  const response = await requestJson(
    `${baseUrl(options)}/distributed/session/${encodeURIComponent(auditId)}/fleet/prepare`,
    {
      method: 'POST',
      headers: { Accept: 'application/json' },
      signal: options?.signal,
    },
    options,
  );
  return parseFleetRunResponse(response);
}

export async function leaseCasHarnessFleetJob(
  auditId: string,
  request: CasHarnessFleetLeaseRequest,
  options?: CasHarnessAuditApiOptions,
): Promise<CasHarnessFleetJob | null> {
  assertNonEmpty('auditId', auditId);
  const response = await requestJson(
    `${baseUrl(options)}/distributed/session/${encodeURIComponent(auditId)}/fleet/job/lease`,
    {
      method: 'POST',
      headers: jsonHeaders(),
      body: JSON.stringify(request),
      signal: options?.signal,
    },
    options,
  );
  return parseNullableFleetJobResponse(response);
}

export async function submitCasHarnessFleetJobReceipt(
  auditId: string,
  jobId: string,
  request: CasHarnessFleetJobReceiptRequest,
  options?: CasHarnessAuditApiOptions,
): Promise<CasHarnessFleetRun> {
  assertNonEmpty('auditId', auditId);
  assertNonEmpty('jobId', jobId);
  const response = await requestJson(
    `${baseUrl(options)}/distributed/session/${encodeURIComponent(auditId)}/fleet/job/${encodeURIComponent(jobId)}/receipt`,
    {
      method: 'POST',
      headers: jsonHeaders(),
      body: JSON.stringify(request),
      signal: options?.signal,
    },
    options,
  );
  return parseFleetRunResponse(response);
}

export async function buildCasHarnessFleetEvidenceFragmentRef(
  input: CasHarnessFleetEvidenceFragmentRefInput,
): Promise<string> {
  const auditId = requiredFragmentString(input.audit_id, 'audit_id');
  const jobId = requiredFragmentString(input.job_id, 'job_id');
  const workerId = requiredFragmentString(input.worker_id, 'worker_id');
  const shardId = requiredFragmentString(input.shard_id, 'shard_id');
  const expectedOutputs = cleanFragmentOutputList(input.expected_outputs, 'expected_outputs');
  const producedOutputs = cleanFragmentOutputList(input.produced_outputs, 'produced_outputs');
  const explicitMissingOutputs = cleanFragmentOutputList(
    input.missing_outputs ?? [],
    'missing_outputs',
  );
  const missingOutputs = Array.from(new Set([
    ...explicitMissingOutputs,
    ...expectedOutputs.filter((output) => !producedOutputs.includes(output)),
  ])).sort();
  const payload = {
    schema_version: 'cas_harness_evidence_fragment.v1',
    audit_id: auditId,
    job_id: jobId,
    worker_id: workerId,
    model_id: requiredFragmentString(input.model_id, 'model_id'),
    layer_start: requiredFragmentInteger(input.layer_start, 'layer_start'),
    layer_end: requiredFragmentInteger(input.layer_end, 'layer_end'),
    shard_id: shardId,
    expected_outputs: expectedOutputs,
    produced_outputs: producedOutputs,
    missing_outputs: missingOutputs,
  };
  const digest = await sha256Hex(stableJsonStringify(payload));
  return `cas-fragment://${auditId}/${jobId}/${workerId}/${shardId}/sha256:${digest}`;
}

export async function mergeCasHarnessFleetRun(
  auditId: string,
  options?: CasHarnessAuditApiOptions,
): Promise<CasHarnessFleetRun> {
  assertNonEmpty('auditId', auditId);
  const response = await requestJson(
    `${baseUrl(options)}/distributed/session/${encodeURIComponent(auditId)}/fleet/merge`,
    {
      method: 'POST',
      headers: { Accept: 'application/json' },
      signal: options?.signal,
    },
    options,
  );
  return parseFleetRunResponse(response);
}

export async function getCasHarnessFleetRun(
  auditId: string,
  options?: CasHarnessAuditApiOptions,
): Promise<CasHarnessFleetRun> {
  assertNonEmpty('auditId', auditId);
  const response = await requestJson(
    `${baseUrl(options)}/distributed/session/${encodeURIComponent(auditId)}/fleet`,
    {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal: options?.signal,
    },
    options,
  );
  return parseFleetRunResponse(response);
}

export async function listCasHarnessFleetRuns(
  options?: CasHarnessAuditApiOptions,
): Promise<CasHarnessFleetRunList> {
  const response = await requestJson(`${baseUrl(options)}/distributed/fleet/runs`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    signal: options?.signal,
  }, options);
  return parseFleetRunListResponse(response);
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
  const verifierDecision = parseNullableVerifierDecision(raw.verifier_decision);
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
    verifier_decision: verifierDecision,
    lifecycle,
  };
}

export function parseDistributedAuditResponse(raw: unknown): CasHarnessDistributedAudit {
  if (!isRecord(raw)) {
    throw new CasHarnessAuditApiError('CAS Harness distributed audit response was not an object');
  }
  const workerEvidence = Array.isArray(raw.worker_evidence)
    ? raw.worker_evidence.map(parseDistributedWorkerEvidence)
    : null;
  if (!workerEvidence) {
    throw new CasHarnessAuditApiError('CAS Harness distributed audit worker_evidence must be an array');
  }
  const status = parseDistributedAuditStatus(raw.status);
  const mergeStatus = parseDistributedMergeStatus(raw.merge_status);
  const readyWorkers = requiredInteger(raw.ready_workers, 'ready_workers');
  const failedWorkers = requiredInteger(raw.failed_workers, 'failed_workers');
  const totalWorkers = requiredInteger(raw.total_workers, 'total_workers');
  const missingOutputs = parseStringArray(raw.missing_outputs, 'missing_outputs');
  assertDistributedAuditWorkerCounts(workerEvidence, readyWorkers, failedWorkers, totalWorkers);
  assertDistributedMergeCompleteness(workerEvidence, mergeStatus, missingOutputs);

  return {
    audit_id: requiredString(raw.audit_id, 'audit_id'),
    plan_id: requiredString(raw.plan_id, 'plan_id'),
    status,
    merge_status: mergeStatus,
    verdict: parseNullableDistributedMergeVerdict(raw.verdict),
    confidence: parseNullableDistributedMergeConfidence(raw.confidence),
    evidence_packet_trace_id: nullableString(raw.evidence_packet_trace_id),
    merge_reason: requiredString(raw.merge_reason, 'merge_reason'),
    created_at: requiredString(raw.created_at, 'created_at'),
    updated_at: requiredString(raw.updated_at, 'updated_at'),
    plan: parseScalePlanResponse(raw.plan),
    worker_evidence: workerEvidence,
    ready_workers: readyWorkers,
    failed_workers: failedWorkers,
    total_workers: totalWorkers,
    missing_outputs: missingOutputs,
  };
}

export function parseScalePlanResponse(raw: unknown): CasHarnessScalePlan {
  if (!isRecord(raw)) {
    throw new CasHarnessAuditApiError('CAS Harness scale plan response was not an object');
  }

  const assignments = Array.isArray(raw.worker_assignments)
    ? raw.worker_assignments.map(parseScalePlanWorkerAssignment)
    : null;
  if (!assignments) {
    throw new CasHarnessAuditApiError('CAS Harness scale plan worker_assignments must be an array');
  }

  return {
    model_id: requiredString(raw.model_id, 'model_id'),
    weight_access: parseScalePlanWeightAccess(raw.weight_access),
    parameter_count_b: requiredNumber(raw.parameter_count_b, 'parameter_count_b'),
    num_layers: requiredInteger(raw.num_layers, 'num_layers'),
    scale_tier: parseScalePlanTier(raw.scale_tier),
    recommended_worker_count: requiredInteger(raw.recommended_worker_count, 'recommended_worker_count'),
    orchestration_pattern: requiredString(raw.orchestration_pattern, 'orchestration_pattern'),
    worker_assignments: assignments,
    memory_estimate: parseScalePlanMemoryEstimate(raw.memory_estimate),
    expected_capability: parseStringArray(raw.expected_capability, 'expected_capability'),
    evidence_requirements: parseStringArray(raw.evidence_requirements, 'evidence_requirements'),
    limitations: parseStringArray(raw.limitations, 'limitations'),
  };
}

export function parseModelTargetVerificationResponse(
  raw: unknown,
): CasHarnessModelTargetVerification {
  if (!isRecord(raw)) {
    throw new CasHarnessAuditApiError('CAS Harness target verification response was not an object');
  }

  const verdict = parseNullableVerdict(raw.verdict);
  if (verdict !== null) {
    throw new CasHarnessAuditApiError('CAS Harness target verification must not return a verdict');
  }
  const confidence = parseNullableConfidence(raw.confidence);
  if (confidence !== null) {
    throw new CasHarnessAuditApiError('CAS Harness target verification must not return confidence');
  }

  if (typeof raw.can_run_audit !== 'boolean') {
    throw new CasHarnessAuditApiError('CAS Harness target verification can_run_audit must be boolean');
  }

  return {
    connection_id: requiredString(raw.connection_id, 'connection_id'),
    connection_state: parseModelConnectionState(raw.connection_state),
    model_status: parseVerifiedModelStatus(raw.model_status),
    can_run_audit: raw.can_run_audit,
    target: parseVerifiedModelTarget(raw.target),
    detail: requiredString(raw.detail, 'detail'),
    checked_at: requiredString(raw.checked_at, 'checked_at'),
    provenance_chip: parseProvenanceChip(raw.provenance_chip),
    verdict: null,
    confidence: null,
    evidence_packet_trace_id: nullableString(raw.evidence_packet_trace_id),
    reference_evidence_packet_trace_id: nullableString(raw.reference_evidence_packet_trace_id),
    atlas_deep_link: nullableString(raw.atlas_deep_link),
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
    response = await fetchImpl(url, withAuthHeader(init, options));
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

function withAuthHeader(
  init: RequestInit,
  options?: CasHarnessAuditApiOptions,
): RequestInit {
  const authorization = authorizationHeaderValue(options?.authToken);
  if (!authorization) return init;

  return {
    ...init,
    headers: {
      ...headersToRecord(init.headers),
      Authorization: authorization,
    },
  };
}

function authorizationHeaderValue(authToken?: string | null): string | null {
  const trimmed = authToken?.trim();
  if (!trimmed) return null;
  return /^Bearer\s+/i.test(trimmed) ? trimmed : `Bearer ${trimmed}`;
}

function headersToRecord(headers: HeadersInit | undefined): Record<string, string> {
  if (!headers) return {};
  if (typeof Headers !== 'undefined' && headers instanceof Headers) {
    return Object.fromEntries(headers.entries());
  }
  if (Array.isArray(headers)) return Object.fromEntries(headers);
  return { ...(headers as Record<string, string>) };
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

export function parseFleetWorkerResponse(raw: unknown): CasHarnessFleetWorker {
  if (!isRecord(raw)) {
    throw new CasHarnessAuditApiError('CAS Harness fleet worker response was not an object');
  }
  const capacity = requiredInteger(raw.capacity, 'fleet_worker.capacity');
  if (capacity <= 0) {
    throw new CasHarnessAuditApiError('CAS Harness fleet worker capacity must be positive');
  }
  return {
    worker_id: requiredString(raw.worker_id, 'fleet_worker.worker_id'),
    model_id: requiredString(raw.model_id, 'fleet_worker.model_id'),
    worker_url: requiredString(raw.worker_url, 'fleet_worker.worker_url'),
    gpu_type: requiredString(raw.gpu_type, 'fleet_worker.gpu_type'),
    capacity,
    supported_methods: parseStringArray(raw.supported_methods, 'fleet_worker.supported_methods'),
    registered_at: requiredString(raw.registered_at, 'fleet_worker.registered_at'),
    last_heartbeat_at: requiredString(raw.last_heartbeat_at, 'fleet_worker.last_heartbeat_at'),
    status: parseFleetWorkerStatus(raw.status),
  };
}

export function parseFleetWorkerListResponse(raw: unknown): CasHarnessFleetWorkerList {
  if (!isRecord(raw) || !Array.isArray(raw.workers)) {
    throw new CasHarnessAuditApiError('CAS Harness fleet worker list response was malformed');
  }
  return {
    workers: raw.workers.map(parseFleetWorkerResponse),
  };
}

export function parseNullableFleetJobResponse(raw: unknown): CasHarnessFleetJob | null {
  if (raw === null || raw === undefined) return null;
  return parseFleetJobResponse(raw);
}

interface FleetJobParseOptions {
  leaseTokenMode?: 'preserve' | 'redact';
}

export function parseFleetJobResponse(
  raw: unknown,
  options: FleetJobParseOptions = {},
): CasHarnessFleetJob {
  if (!isRecord(raw)) {
    throw new CasHarnessAuditApiError('CAS Harness fleet job response was not an object');
  }
  const layerStart = requiredInteger(raw.layer_start, 'fleet_job.layer_start');
  const layerEnd = requiredInteger(raw.layer_end, 'fleet_job.layer_end');
  if (layerEnd < layerStart) {
    throw new CasHarnessAuditApiError('CAS Harness fleet job layer range was malformed');
  }
  const expectedOutputs = parseStringArray(raw.expected_outputs, 'fleet_job.expected_outputs');
  const producedOutputs = parseStringArray(raw.produced_outputs, 'fleet_job.produced_outputs');
  const missingOutputs = parseStringArray(raw.missing_outputs, 'fleet_job.missing_outputs');
  const status = parseFleetJobStatus(raw.status);
  const leaseToken = nullableStringStrict(raw.lease_token, 'fleet_job.lease_token');
  const leaseExpiresAt = nullableStringStrict(raw.lease_expires_at, 'fleet_job.lease_expires_at');
  const preserveLeaseToken = options.leaseTokenMode !== 'redact';
  const evidencePacketFragmentRef = nullableStringStrict(
    raw.evidence_packet_fragment_ref,
    'fleet_job.evidence_packet_fragment_ref',
  );
  const errorMessage = nullableStringStrict(raw.error_message, 'fleet_job.error_message');
  assertWorkerOutputReceipts(expectedOutputs, producedOutputs, missingOutputs);
  if (status === 'leased' && leaseExpiresAt === null) {
    throw new CasHarnessAuditApiError('CAS Harness leased fleet job requires lease_expires_at');
  }
  if (status === 'leased' && preserveLeaseToken && leaseToken === null) {
    throw new CasHarnessAuditApiError('CAS Harness fleet job lease response requires lease_token');
  }
  if (status === 'completed' && evidencePacketFragmentRef === null) {
    throw new CasHarnessAuditApiError(
      'CAS Harness completed fleet job requires evidence_packet_fragment_ref',
    );
  }
  if (status === 'failed' && errorMessage === null) {
    throw new CasHarnessAuditApiError('CAS Harness failed fleet job requires error_message');
  }
  return {
    job_id: requiredString(raw.job_id, 'fleet_job.job_id'),
    audit_id: requiredString(raw.audit_id, 'fleet_job.audit_id'),
    assigned_worker_id: requiredString(raw.assigned_worker_id, 'fleet_job.assigned_worker_id'),
    layer_start: layerStart,
    layer_end: layerEnd,
    shard_id: requiredString(raw.shard_id, 'fleet_job.shard_id'),
    assigned_methods: parseStringArray(raw.assigned_methods, 'fleet_job.assigned_methods'),
    expected_outputs: expectedOutputs,
    status,
    lease_token: preserveLeaseToken ? leaseToken : null,
    lease_expires_at: leaseExpiresAt,
    evidence_packet_fragment_ref: evidencePacketFragmentRef,
    produced_outputs: producedOutputs,
    missing_outputs: missingOutputs,
    error_message: errorMessage,
    updated_at: requiredString(raw.updated_at, 'fleet_job.updated_at'),
  };
}

export function parseFleetRunResponse(raw: unknown): CasHarnessFleetRun {
  if (!isRecord(raw)) {
    throw new CasHarnessAuditApiError('CAS Harness fleet run response was not an object');
  }
  if (raw.verdict !== undefined && raw.verdict !== null) {
    throw new CasHarnessAuditApiError(
      'CAS Harness fleet executor must not return ACCEPT/SUPPRESS; final verdict requires verifier decision layer',
    );
  }
  if (raw.confidence !== undefined && raw.confidence !== null) {
    throw new CasHarnessAuditApiError(
      'CAS Harness fleet executor confidence must be null until verifier decision layer computes confidence',
    );
  }
  const jobs = Array.isArray(raw.jobs)
    ? raw.jobs.map((job) => parseFleetJobResponse(job, { leaseTokenMode: 'redact' }))
    : null;
  if (!jobs) {
    throw new CasHarnessAuditApiError('CAS Harness fleet run jobs must be an array');
  }
  const status = parseFleetRunStatus(raw.status);
  const verifierGateStatus = parseFleetVerifierGateStatus(raw.verifier_gate_status);
  const totalJobs = requiredInteger(raw.total_jobs, 'fleet_run.total_jobs');
  const leasedJobs = requiredInteger(raw.leased_jobs, 'fleet_run.leased_jobs');
  const completedFragments = requiredInteger(raw.completed_fragments, 'fleet_run.completed_fragments');
  const failedJobs = requiredInteger(raw.failed_jobs, 'fleet_run.failed_jobs');
  const registeredWorkers = requiredInteger(raw.registered_workers, 'fleet_run.registered_workers');
  const staleWorkers = parseStringArray(raw.stale_workers, 'fleet_run.stale_workers');
  const readiness = parseFleetReadinessResponse(raw.readiness);
  assertFleetRunReadiness({
    jobs,
    verifierGateStatus,
    totalJobs,
    leasedJobs,
    completedFragments,
    failedJobs,
    registeredWorkers,
    staleWorkers,
  });
  return {
    audit_id: requiredString(raw.audit_id, 'fleet_run.audit_id'),
    status,
    verifier_gate_status: verifierGateStatus,
    merged_packet_trace_id: nullableStringStrict(
      raw.merged_packet_trace_id,
      'fleet_run.merged_packet_trace_id',
    ),
    merge_reason: requiredString(raw.merge_reason, 'fleet_run.merge_reason'),
    created_at: requiredString(raw.created_at, 'fleet_run.created_at'),
    updated_at: requiredString(raw.updated_at, 'fleet_run.updated_at'),
    total_jobs: totalJobs,
    leased_jobs: leasedJobs,
    completed_fragments: completedFragments,
    failed_jobs: failedJobs,
    registered_workers: registeredWorkers,
    stale_workers: staleWorkers,
    readiness,
    jobs,
  };
}

export function parseFleetReadinessResponse(raw: unknown): CasHarnessFleetReadiness {
  if (!isRecord(raw)) {
    throw new CasHarnessAuditApiError('CAS Harness fleet readiness response was not an object');
  }
  const status = parseFleetReadinessStatus(raw.status);
  const verifierOwned = raw.verifier_owned;
  if (typeof verifierOwned !== 'boolean') {
    throw new CasHarnessAuditApiError('CAS Harness fleet readiness verifier_owned must be boolean');
  }
  return {
    status,
    headline: requiredString(raw.headline, 'fleet_readiness.headline'),
    blockers: parseStringArray(raw.blockers, 'fleet_readiness.blockers'),
    next_actions: parseStringArray(raw.next_actions, 'fleet_readiness.next_actions'),
    verifier_owned: verifierOwned,
  };
}

export function parseFleetRunListResponse(raw: unknown): CasHarnessFleetRunList {
  if (!isRecord(raw) || !Array.isArray(raw.runs)) {
    throw new CasHarnessAuditApiError('CAS Harness fleet run list response was malformed');
  }
  return {
    runs: raw.runs.map(parseFleetRunResponse),
  };
}

function parseDistributedWorkerEvidence(raw: unknown): CasHarnessDistributedWorkerEvidence {
  if (!isRecord(raw)) {
    throw new CasHarnessAuditApiError('CAS Harness distributed worker evidence was malformed');
  }
  const layerStart = requiredInteger(raw.layer_start, 'worker_evidence[].layer_start');
  const layerEnd = requiredInteger(raw.layer_end, 'worker_evidence[].layer_end');
  if (layerEnd < layerStart) {
    throw new CasHarnessAuditApiError('CAS Harness distributed worker layer range was malformed');
  }
  const expectedOutputs = parseStringArray(raw.expected_outputs, 'worker_evidence[].expected_outputs');
  const producedOutputs = parseStringArray(raw.produced_outputs, 'worker_evidence[].produced_outputs');
  const missingOutputs = parseStringArray(raw.missing_outputs, 'worker_evidence[].missing_outputs');
  const workerStatus = parseDistributedWorkerStatus(raw.worker_status);
  const evidencePacketRef = nullableStringStrict(
    raw.evidence_packet_ref,
    'worker_evidence[].evidence_packet_ref',
  );
  const errorMessage = nullableStringStrict(raw.error_message, 'worker_evidence[].error_message');
  assertWorkerOutputReceipts(expectedOutputs, producedOutputs, missingOutputs);
  if (workerStatus === 'completed' && evidencePacketRef === null) {
    throw new CasHarnessAuditApiError(
      'CAS Harness completed distributed worker evidence requires evidence_packet_ref',
    );
  }
  if (workerStatus === 'failed' && errorMessage === null) {
    throw new CasHarnessAuditApiError(
      'CAS Harness failed distributed worker evidence requires error_message',
    );
  }
  return {
    worker_id: requiredString(raw.worker_id, 'worker_evidence[].worker_id'),
    layer_start: layerStart,
    layer_end: layerEnd,
    shard_id: requiredString(raw.shard_id, 'worker_evidence[].shard_id'),
    assigned_methods: parseStringArray(raw.assigned_methods, 'worker_evidence[].assigned_methods'),
    expected_outputs: expectedOutputs,
    worker_status: workerStatus,
    produced_outputs: producedOutputs,
    missing_outputs: missingOutputs,
    evidence_packet_ref: evidencePacketRef,
    error_message: errorMessage,
    updated_at: requiredString(raw.updated_at, 'worker_evidence[].updated_at'),
  };
}

function parseScalePlanWorkerAssignment(raw: unknown): CasHarnessScalePlanWorkerAssignment {
  if (!isRecord(raw)) {
    throw new CasHarnessAuditApiError('CAS Harness scale plan worker assignment was malformed');
  }
  const layerStart = requiredInteger(raw.layer_start, 'worker_assignments[].layer_start');
  const layerEnd = requiredInteger(raw.layer_end, 'worker_assignments[].layer_end');
  if (layerEnd < layerStart) {
    throw new CasHarnessAuditApiError('CAS Harness scale plan worker layer range was malformed');
  }
  return {
    worker_id: requiredString(raw.worker_id, 'worker_assignments[].worker_id'),
    layer_start: layerStart,
    layer_end: layerEnd,
    shard_id: requiredString(raw.shard_id, 'worker_assignments[].shard_id'),
    assigned_methods: parseStringArray(raw.assigned_methods, 'worker_assignments[].assigned_methods'),
    expected_outputs: parseStringArray(raw.expected_outputs, 'worker_assignments[].expected_outputs'),
  };
}

function parseDistributedAuditStatus(raw: unknown): CasHarnessDistributedAuditStatus {
  if (
    raw === 'PLANNED' ||
    raw === 'DISPATCHED' ||
    raw === 'RUNNING' ||
    raw === 'MERGE_PENDING' ||
    raw === 'COMPLETE' ||
    raw === 'FAILED'
  ) {
    return raw;
  }
  throw new CasHarnessAuditApiError(`Unsupported CAS Harness distributed audit status: ${String(raw)}`);
}

function parseDistributedMergeStatus(raw: unknown): CasHarnessDistributedMergeStatus {
  if (raw === 'pending' || raw === 'partial' || raw === 'complete' || raw === 'failed') {
    return raw;
  }
  throw new CasHarnessAuditApiError(`Unsupported CAS Harness distributed merge status: ${String(raw)}`);
}

function parseDistributedWorkerStatus(raw: unknown): CasHarnessDistributedWorkerStatus {
  if (
    raw === 'queued' ||
    raw === 'assigned' ||
    raw === 'running' ||
    raw === 'completed' ||
    raw === 'failed'
  ) {
    return raw;
  }
  throw new CasHarnessAuditApiError(`Unsupported CAS Harness distributed worker status: ${String(raw)}`);
}

function parseFleetWorkerStatus(raw: unknown): CasHarnessFleetWorkerStatus {
  if (raw === 'active' || raw === 'stale' || raw === 'offline') {
    return raw;
  }
  throw new CasHarnessAuditApiError(`Unsupported CAS Harness fleet worker status: ${String(raw)}`);
}

function parseFleetJobStatus(raw: unknown): CasHarnessFleetJobStatus {
  if (
    raw === 'queued' ||
    raw === 'leased' ||
    raw === 'completed' ||
    raw === 'failed' ||
    raw === 'expired'
  ) {
    return raw;
  }
  throw new CasHarnessAuditApiError(`Unsupported CAS Harness fleet job status: ${String(raw)}`);
}

function parseFleetRunStatus(raw: unknown): CasHarnessFleetRunStatus {
  if (
    raw === 'PREPARED' ||
    raw === 'LEASING' ||
    raw === 'MERGE_PENDING' ||
    raw === 'COMPLETE' ||
    raw === 'FAILED'
  ) {
    return raw;
  }
  throw new CasHarnessAuditApiError(`Unsupported CAS Harness fleet run status: ${String(raw)}`);
}

function parseFleetVerifierGateStatus(raw: unknown): CasHarnessFleetVerifierGateStatus {
  if (
    raw === 'not_prepared' ||
    raw === 'waiting_for_workers' ||
    raw === 'waiting_for_receipts' ||
    raw === 'blocked_failed_worker' ||
    raw === 'blocked_missing_outputs' ||
    raw === 'ready_for_verifier'
  ) {
    return raw;
  }
  throw new CasHarnessAuditApiError(
    `Unsupported CAS Harness fleet verifier gate status: ${String(raw)}`,
  );
}

function parseFleetReadinessStatus(raw: unknown): CasHarnessFleetReadinessStatus {
  if (raw === 'blocked' || raw === 'waiting' || raw === 'ready') {
    return raw;
  }
  throw new CasHarnessAuditApiError(
    `Unsupported CAS Harness fleet readiness status: ${String(raw)}`,
  );
}

function parseNullableDistributedMergeVerdict(
  raw: unknown,
): CasHarnessDistributedMergeVerdict | null {
  if (raw === null || raw === undefined) return null;
  if (raw === 'FLAG_FOR_HUMAN_REVIEW') return raw;
  throw new CasHarnessAuditApiError(
    'CAS Harness distributed merge must not return ACCEPT/SUPPRESS; final verdict requires verifier decision layer',
  );
}

function parseNullableDistributedMergeConfidence(raw: unknown): null {
  if (raw === null || raw === undefined) return null;
  throw new CasHarnessAuditApiError(
    'CAS Harness distributed merge confidence must be null until verifier decision layer computes confidence',
  );
}

function assertWorkerOutputReceipts(
  expectedOutputs: string[],
  producedOutputs: string[],
  missingOutputs: string[],
): void {
  const expected = new Set(expectedOutputs);
  for (const output of producedOutputs) {
    if (!expected.has(output)) {
      throw new CasHarnessAuditApiError(
        `CAS Harness distributed worker produced unknown output: ${output}`,
      );
    }
  }
  for (const output of missingOutputs) {
    if (!expected.has(output)) {
      throw new CasHarnessAuditApiError(
        `CAS Harness distributed worker reported unknown missing output: ${output}`,
      );
    }
  }
  const missing = new Set(missingOutputs);
  for (const output of producedOutputs) {
    if (missing.has(output)) {
      throw new CasHarnessAuditApiError(
        `CAS Harness distributed worker output cannot be both produced and missing: ${output}`,
      );
    }
  }
}

function assertDistributedAuditWorkerCounts(
  workerEvidence: CasHarnessDistributedWorkerEvidence[],
  readyWorkers: number,
  failedWorkers: number,
  totalWorkers: number,
): void {
  if (totalWorkers !== workerEvidence.length) {
    throw new CasHarnessAuditApiError(
      'CAS Harness distributed audit total_workers must match worker_evidence length',
    );
  }
  const completedCount = workerEvidence.filter(
    (worker) => worker.worker_status === 'completed',
  ).length;
  if (readyWorkers !== completedCount) {
    throw new CasHarnessAuditApiError(
      'CAS Harness distributed audit ready_workers must match completed worker receipts',
    );
  }
  const failedCount = workerEvidence.filter((worker) => worker.worker_status === 'failed').length;
  if (failedWorkers !== failedCount) {
    throw new CasHarnessAuditApiError(
      'CAS Harness distributed audit failed_workers must match failed worker receipts',
    );
  }
}

function assertDistributedMergeCompleteness(
  workerEvidence: CasHarnessDistributedWorkerEvidence[],
  mergeStatus: CasHarnessDistributedMergeStatus,
  auditMissingOutputs: string[],
): void {
  if (mergeStatus !== 'complete') return;

  const nonCompleted = workerEvidence.find((worker) => worker.worker_status !== 'completed');
  if (nonCompleted) {
    throw new CasHarnessAuditApiError(
      'CAS Harness complete distributed merge requires every worker receipt to be completed',
    );
  }
  const workerMissingOutput = workerEvidence.find((worker) => worker.missing_outputs.length > 0);
  if (auditMissingOutputs.length > 0 || workerMissingOutput) {
    throw new CasHarnessAuditApiError(
      'CAS Harness complete distributed merge cannot include missing worker outputs',
    );
  }
}

function assertFleetRunReadiness({
  jobs,
  verifierGateStatus,
  totalJobs,
  leasedJobs,
  completedFragments,
  failedJobs,
  registeredWorkers,
  staleWorkers,
}: {
  jobs: CasHarnessFleetJob[];
  verifierGateStatus: CasHarnessFleetVerifierGateStatus;
  totalJobs: number;
  leasedJobs: number;
  completedFragments: number;
  failedJobs: number;
  registeredWorkers: number;
  staleWorkers: string[];
}): void {
  if (totalJobs !== jobs.length) {
    throw new CasHarnessAuditApiError(
      'CAS Harness fleet run total_jobs must match jobs length',
    );
  }
  if (leasedJobs !== jobs.filter((job) => job.status === 'leased').length) {
    throw new CasHarnessAuditApiError(
      'CAS Harness fleet run leased_jobs must match leased jobs',
    );
  }
  if (completedFragments !== jobs.filter((job) => job.status === 'completed').length) {
    throw new CasHarnessAuditApiError(
      'CAS Harness fleet run completed_fragments must match completed job fragments',
    );
  }
  if (failedJobs !== jobs.filter((job) => job.status === 'failed').length) {
    throw new CasHarnessAuditApiError(
      'CAS Harness fleet run failed_jobs must match failed jobs',
    );
  }
  if (registeredWorkers < 0) {
    throw new CasHarnessAuditApiError('CAS Harness fleet run registered_workers cannot be negative');
  }
  if (verifierGateStatus !== 'ready_for_verifier') return;

  if (staleWorkers.length > 0) {
    throw new CasHarnessAuditApiError(
      'CAS Harness fleet run cannot be ready_for_verifier with stale workers',
    );
  }
  if (failedJobs > 0) {
    throw new CasHarnessAuditApiError(
      'CAS Harness fleet run cannot be ready_for_verifier with failed jobs',
    );
  }
  const nonCompleted = jobs.find((job) => job.status !== 'completed');
  if (nonCompleted) {
    throw new CasHarnessAuditApiError(
      'CAS Harness fleet run ready_for_verifier requires every job to be completed',
    );
  }
  const missingOutputJob = jobs.find((job) => job.missing_outputs.length > 0);
  if (missingOutputJob) {
    throw new CasHarnessAuditApiError(
      'CAS Harness fleet run ready_for_verifier cannot include missing job outputs',
    );
  }
}

function parseScalePlanMemoryEstimate(raw: unknown): CasHarnessScalePlanMemoryEstimate {
  if (!isRecord(raw)) {
    throw new CasHarnessAuditApiError('CAS Harness scale plan memory_estimate was malformed');
  }
  return {
    precision: parseScalePlanPrecision(raw.precision),
    total_weight_memory_gb: requiredNumber(raw.total_weight_memory_gb, 'memory_estimate.total_weight_memory_gb'),
    activation_overhead_gb: requiredNumber(raw.activation_overhead_gb, 'memory_estimate.activation_overhead_gb'),
    estimated_total_runtime_gb: requiredNumber(raw.estimated_total_runtime_gb, 'memory_estimate.estimated_total_runtime_gb'),
    estimated_memory_per_worker_gb: requiredNumber(raw.estimated_memory_per_worker_gb, 'memory_estimate.estimated_memory_per_worker_gb'),
  };
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

function parseScalePlanWeightAccess(raw: unknown): 'open_weight' {
  if (raw === 'open_weight') return raw;
  throw new CasHarnessAuditApiError(`Unsupported CAS Harness scale plan weight_access: ${String(raw)}`);
}

function parseScalePlanPrecision(raw: unknown): CasHarnessScalePlanPrecision {
  if (raw === 'fp16' || raw === 'bf16' || raw === 'int8' || raw === 'int4') {
    return raw;
  }
  throw new CasHarnessAuditApiError(`Unsupported CAS Harness scale plan precision: ${String(raw)}`);
}

function parseScalePlanTier(raw: unknown): CasHarnessScalePlanTier {
  if (
    raw === 'single_worker_open_weight' ||
    raw === 'small_distributed_open_weight' ||
    raw === 'distributed_open_weight' ||
    raw === 'enterprise_distributed_open_weight'
  ) {
    return raw;
  }
  throw new CasHarnessAuditApiError(`Unsupported CAS Harness scale tier: ${String(raw)}`);
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

function parseModelConnectionState(raw: unknown): CasHarnessModelConnectionState {
  if (raw === 'CONNECTED' || raw === 'CONFIGURED') return raw;
  throw new CasHarnessAuditApiError(
    `Unsupported CAS Harness model connection state: ${String(raw)}`,
  );
}

function parseVerifiedModelStatus(raw: unknown): CasHarnessVerifiedModelStatus {
  if (raw === 'CONNECTED' || raw === 'READY') return raw;
  throw new CasHarnessAuditApiError(
    `Unsupported CAS Harness verified model status: ${String(raw)}`,
  );
}

function parseModelTargetKind(raw: unknown): CasHarnessModelTargetKind {
  if (raw === 'demo_reference' || raw === 'api_endpoint') return raw;
  throw new CasHarnessAuditApiError(
    `Unsupported CAS Harness model target kind: ${String(raw)}`,
  );
}

function parseCredentialMode(raw: unknown): CasHarnessCredentialMode {
  if (raw === 'none' || raw === 'credential_ref' || raw === 'ephemeral_secret') {
    return raw;
  }
  throw new CasHarnessAuditApiError(
    `Unsupported CAS Harness credential mode: ${String(raw)}`,
  );
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

function parseVerifiedModelTarget(raw: unknown): CasHarnessVerifiedModelTarget {
  if (!isRecord(raw)) {
    throw new CasHarnessAuditApiError('CAS Harness verified model target was malformed');
  }
  const timeoutMs = raw.timeout_ms;
  if (typeof timeoutMs !== 'number' || !Number.isInteger(timeoutMs) || timeoutMs <= 0) {
    throw new CasHarnessAuditApiError('CAS Harness verified model target timeout_ms must be positive integer');
  }
  return {
    kind: parseModelTargetKind(raw.kind),
    provider: requiredString(raw.provider, 'target.provider'),
    model_id: requiredString(raw.model_id, 'target.model_id'),
    endpoint_url: nullableString(raw.endpoint_url),
    credential_mode: parseCredentialMode(raw.credential_mode),
    timeout_ms: timeoutMs,
  };
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

function parseNullableVerifierDecision(raw: unknown): VerifierDecision | null {
  if (raw === null || raw === undefined) return null;
  if (!isRecord(raw)) {
    throw new CasHarnessAuditApiError('CAS Harness verifier decision was malformed');
  }
  const verdict = parseNullableVerdict(raw.verdict);
  if (verdict === null) {
    throw new CasHarnessAuditApiError('CAS Harness verifier decision verdict is required');
  }
  const confidence = parseNullableConfidence(raw.confidence);
  if (confidence === null) {
    throw new CasHarnessAuditApiError('CAS Harness verifier decision confidence is required');
  }
  const parsed: VerifierDecision = {
    verdict,
    confidence,
    source: requiredString(raw.source, 'verifier_decision.source'),
    reason: requiredString(raw.reason, 'verifier_decision.reason'),
  };
  const decisionScope = nullableString(raw.decision_scope);
  const coverage = parseNullableVerifierCoverage(raw.coverage);
  if (decisionScope) {
    parsed.decisionScope = decisionScope;
  }
  if (coverage) {
    parsed.coverage = coverage;
  }
  return parsed;
}

function parseNullableVerifierCoverage(
  raw: unknown,
): VerifierDecision['coverage'] | null {
  if (raw === null || raw === undefined) return null;
  if (!isRecord(raw)) {
    throw new CasHarnessAuditApiError('CAS Harness verifier decision coverage was malformed');
  }
  return {
    basis: nullableString(raw.basis),
    caseCount: nullableNumber(raw.case_count, 'verifier_decision.coverage.case_count'),
    classCount: nullableNumber(raw.class_count, 'verifier_decision.coverage.class_count'),
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

function requiredNumber(raw: unknown, field: string): number {
  if (typeof raw === 'number' && Number.isFinite(raw)) return raw;
  throw new CasHarnessAuditApiError(`CAS Harness audit response field "${field}" must be a finite number`);
}

function requiredInteger(raw: unknown, field: string): number {
  const value = requiredNumber(raw, field);
  if (Number.isInteger(value)) return value;
  throw new CasHarnessAuditApiError(`CAS Harness audit response field "${field}" must be an integer`);
}

function parseStringArray(raw: unknown, field: string): string[] {
  if (!Array.isArray(raw)) {
    throw new CasHarnessAuditApiError(`CAS Harness audit response field "${field}" must be an array`);
  }
  return raw.map((value, index) => requiredString(value, `${field}[${index}]`));
}

function nullableString(raw: unknown): string | null {
  if (raw === null || raw === undefined) return null;
  return typeof raw === 'string' ? raw : null;
}

function nullableNumber(raw: unknown, field: string): number | null {
  if (raw === null || raw === undefined) return null;
  if (typeof raw === 'number' && Number.isFinite(raw)) return raw;
  throw new CasHarnessAuditApiError(
    `CAS Harness audit response field "${field}" must be null or a finite number`,
  );
}

function nullableStringStrict(raw: unknown, field: string): string | null {
  if (raw === null || raw === undefined) return null;
  if (typeof raw === 'string' && raw.length > 0) return raw;
  throw new CasHarnessAuditApiError(
    `CAS Harness audit response field "${field}" must be null or a non-empty string`,
  );
}

function requiredFragmentString(raw: unknown, field: string): string {
  if (typeof raw === 'string' && raw.trim().length > 0) return raw.trim();
  throw new CasHarnessAuditApiError(`CAS Harness fleet fragment field "${field}" must be a non-empty string`);
}

function requiredFragmentInteger(raw: unknown, field: string): number {
  if (typeof raw === 'number' && Number.isInteger(raw)) return raw;
  throw new CasHarnessAuditApiError(`CAS Harness fleet fragment field "${field}" must be an integer`);
}

function cleanFragmentOutputList(values: readonly string[], field: string): string[] {
  if (!Array.isArray(values)) {
    throw new CasHarnessAuditApiError(`CAS Harness fleet fragment field "${field}" must be an array`);
  }
  const cleaned: string[] = [];
  const seen = new Set<string>();
  for (const value of values) {
    if (typeof value !== 'string') {
      throw new CasHarnessAuditApiError(`CAS Harness fleet fragment field "${field}" must contain strings`);
    }
    const stripped = value.trim();
    if (!stripped) {
      throw new CasHarnessAuditApiError(`CAS Harness fleet fragment field "${field}" cannot contain empty strings`);
    }
    if (!seen.has(stripped)) {
      cleaned.push(stripped);
      seen.add(stripped);
    }
  }
  return cleaned;
}

function stableJsonStringify(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map((item) => stableJsonStringify(item)).join(',')}]`;
  }
  if (isRecord(value)) {
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${pythonAsciiJsonString(key)}:${stableJsonStringify(value[key])}`)
      .join(',')}}`;
  }
  if (typeof value === 'string') return pythonAsciiJsonString(value);
  const json = JSON.stringify(value);
  if (json === undefined) {
    throw new CasHarnessAuditApiError('CAS Harness fleet fragment payload contained unsupported JSON');
  }
  return json;
}

function pythonAsciiJsonString(value: string): string {
  return JSON.stringify(value).replace(
    /[\u007f-\uffff]/g,
    (char) => `\\u${char.charCodeAt(0).toString(16).padStart(4, '0')}`,
  );
}

async function sha256Hex(value: string): Promise<string> {
  const subtle = globalThis.crypto?.subtle;
  if (!subtle) {
    throw new CasHarnessAuditApiError(
      'CAS Harness fleet Evidence Packet fragment refs require Web Crypto SHA-256 support',
    );
  }
  const digest = await subtle.digest('SHA-256', new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('');
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

export type AuditMode = 'live' | 'replay' | 'offline';

export type AuditVerdict = 'ACCEPT' | 'SUPPRESS' | 'FLAG_FOR_HUMAN_REVIEW';

export type AuditStatus =
  | 'verified'
  | 'present'
  | 'missing'
  | 'failed'
  | 'unavailable';

export type ProvenanceChipId =
  | 'model_proof'
  | 'cas_readout'
  | 'causal_proof'
  | 'control_proof'
  | 'output_proof'
  | 'packet_proof';

export interface ProvenanceChip {
  id: ProvenanceChipId;
  name: string;
  status: AuditStatus;
  statusLabel: string;
  detail: string;
}

export interface VerifierDecision {
  verdict: AuditVerdict;
  confidence: number;
  source: string;
  reason: string;
  decisionScope?: string | null;
  coverage?: {
    basis?: string | null;
    caseCount?: number | null;
    classCount?: number | null;
  } | null;
}

export interface AuditRuntimeProof {
  verdict?: string | null;
  isRealModel?: boolean | null;
  is_real_model?: boolean | null;
  modelLoaded?: boolean | null;
  model_loaded?: boolean | null;
  loadError?: string | null;
  load_error?: string | null;
  fakeRuntimeEnv?: boolean | null;
  fake_runtime_env?: boolean | null;
  manifestIsRealModel?: boolean | null;
  manifest_is_real_model?: boolean | null;
}

export interface AuditSessionRequest {
  mode: AuditMode;
  prompt: string;
  modelId?: string | null;
  sessionId?: string | null;
  requestedAt?: string | null;
}

export interface AuditSessionSummary {
  request: AuditSessionRequest;
  verdict: AuditVerdict;
  confidence: number;
  confidenceLabel: string;
  provenanceChips: ProvenanceChip[];
  runtimeProof?: AuditRuntimeProof | null;
  checkedAt?: string | null;
}

export interface ProvenanceChipInput {
  modelProof?: ChipEvidenceInput;
  casReadout?: ChipEvidenceInput;
  causalProof?: ChipEvidenceInput;
  controlProof?: ChipEvidenceInput;
  outputProof?: ChipEvidenceInput;
  packetProof?: ChipEvidenceInput;
}

export type ChipEvidenceInput =
  | boolean
  | AuditStatus
  | {
      status?: AuditStatus | boolean | null;
      present?: boolean | null;
      verified?: boolean | null;
      failed?: boolean | null;
      detail?: string | null;
      label?: string | null;
    }
  | null
  | undefined;

export interface VerdictDisplayCopy {
  label: string;
  description: string;
  confidenceLabel: string;
}

const VERDICTS: readonly AuditVerdict[] = [
  'ACCEPT',
  'SUPPRESS',
  'FLAG_FOR_HUMAN_REVIEW',
];

const STATUS_LABELS: Record<AuditStatus, string> = {
  verified: 'Verified',
  present: 'Present',
  missing: 'Missing',
  failed: 'Failed',
  unavailable: 'Unavailable',
};

const CHIP_SPECS: readonly {
  id: ProvenanceChipId;
  key: keyof ProvenanceChipInput;
  name: string;
  defaultDetail: string;
}[] = [
  {
    id: 'model_proof',
    key: 'modelProof',
    name: 'Model proof',
    defaultDetail: 'Real model runtime proof for this audit result.',
  },
  {
    id: 'cas_readout',
    key: 'casReadout',
    name: 'CAS readout',
    defaultDetail: 'CAS register and drive readout used by the verdict.',
  },
  {
    id: 'causal_proof',
    key: 'causalProof',
    name: 'Causal proof',
    defaultDetail: 'Ablation or intervention evidence behind the verdict.',
  },
  {
    id: 'control_proof',
    key: 'controlProof',
    name: 'Control proof',
    defaultDetail: 'Negative or baseline control check for the audit.',
  },
  {
    id: 'output_proof',
    key: 'outputProof',
    name: 'Output proof',
    defaultDetail: 'Observed model output tied to the audit packet.',
  },
  {
    id: 'packet_proof',
    key: 'packetProof',
    name: 'Packet proof',
    defaultDetail: 'Audit packet identity and transport proof.',
  },
];

const VERDICT_COPY: Record<AuditVerdict, Omit<VerdictDisplayCopy, 'confidenceLabel'>> = {
  ACCEPT: {
    label: 'Accept',
    description: 'The model output is supported by the audit evidence.',
  },
  SUPPRESS: {
    label: 'Suppress',
    description: 'The model output should not be trusted or shown as-is.',
  },
  FLAG_FOR_HUMAN_REVIEW: {
    label: 'Flag for human review',
    description: 'The model output needs human review before trust.',
  },
};

export function isAuditVerdict(value: unknown): value is AuditVerdict {
  return typeof value === 'string' && VERDICTS.includes(value as AuditVerdict);
}

export function normalizeAuditVerdict(value: unknown): AuditVerdict {
  if (typeof value !== 'string') {
    throw new Error('Audit verdict must be a string');
  }

  const normalized = value.trim().toUpperCase().replace(/[\s-]+/g, '_');
  if (normalized === 'FLAG_HUMAN_REVIEW' || normalized === 'HUMAN_REVIEW') {
    return 'FLAG_FOR_HUMAN_REVIEW';
  }
  if (isAuditVerdict(normalized)) return normalized;
  throw new Error(`Unsupported audit verdict: ${value}`);
}

export function validateAuditConfidence(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1;
}

export function normalizeAuditConfidence(value: unknown): number {
  const numeric =
    typeof value === 'string' && value.trim().length > 0 ? Number(value) : value;
  if (!validateAuditConfidence(numeric)) {
    throw new Error('Audit confidence must be a finite number in [0, 1]');
  }
  return numeric;
}

export function formatAuditConfidence(value: unknown): string {
  return `${Math.round(normalizeAuditConfidence(value) * 100)}%`;
}

export function buildDefaultProvenanceChips(
  input: ProvenanceChipInput,
): ProvenanceChip[] {
  return CHIP_SPECS.map((spec) => {
    const resolved = resolveChipEvidence(input[spec.key]);
    return {
      id: spec.id,
      name: spec.name,
      status: resolved.status,
      statusLabel: STATUS_LABELS[resolved.status],
      detail: resolved.detail ?? spec.defaultDetail,
    };
  });
}

export function verdictCopy(
  verdict: AuditVerdict | string,
  confidence: number | string,
): VerdictDisplayCopy {
  const normalizedVerdict = normalizeAuditVerdict(verdict);
  return {
    ...VERDICT_COPY[normalizedVerdict],
    confidenceLabel: formatAuditConfidence(confidence),
  };
}

// Structural shape of the session fields the customer-safe gate needs. Kept
// local so this module does not import the API session type.
interface CustomerSafeSessionLike {
  verdict?: AuditVerdict | string | null;
  confidence?: number | null;
  provenance_chips?: ProvenanceChip[] | null;
  runtimeProof?: AuditRuntimeProof | null;
  model_id?: string | null;
}

/**
 * Build an AuditSessionSummary from a session-like object so the customer-safe
 * gate can be evaluated at the console surface. The CAS Harness session does
 * NOT carry a separate runtime-proof block, so `runtimeProof` defaults to null;
 * in that case `isAuditResultCustomerSafe` correctly falls back to requiring a
 * verified `model_proof` chip (it never invents a real-weights claim).
 */
export function summaryFromSession(
  session: CustomerSafeSessionLike | null | undefined,
): AuditSessionSummary | null {
  if (!session || session.verdict == null || session.confidence == null) return null;
  let verdict: AuditVerdict;
  try {
    verdict = normalizeAuditVerdict(session.verdict);
  } catch {
    return null;
  }
  return {
    request: {
      mode: 'live',
      prompt: '',
      modelId: session.model_id ?? null,
    },
    verdict,
    confidence: session.confidence,
    confidenceLabel: formatAuditConfidence(session.confidence),
    provenanceChips: session.provenance_chips ?? [],
    runtimeProof: session.runtimeProof ?? null,
  };
}

/**
 * Convenience wrapper: is this session a clean, customer-safe result? Returns
 * false whenever a summary cannot be built (no verdict/confidence yet).
 */
export function isSessionCustomerSafe(
  session: CustomerSafeSessionLike | null | undefined,
): boolean {
  const summary = summaryFromSession(session);
  return summary ? isAuditResultCustomerSafe(summary) : false;
}

export function isAuditResultCustomerSafe(summary: AuditSessionSummary): boolean {
  let verdict: AuditVerdict;
  let confidence: number;
  try {
    verdict = normalizeAuditVerdict(summary.verdict);
    confidence = normalizeAuditConfidence(summary.confidence);
  } catch {
    return false;
  }
  if (confidence <= 0) return false;

  const modelChip = summary.provenanceChips.find((chip) => chip.id === 'model_proof');
  const hasModelProof = modelChip?.status === 'verified';
  const runtimeProof = summary.runtimeProof ?? null;
  const runtimeIsFake = runtimeProof ? proofBoolean(runtimeProof, 'fakeRuntimeEnv') === true : false;
  const runtimeIsReal =
    runtimeProof === null
      ? hasModelProof
      : proofBoolean(runtimeProof, 'isRealModel') === true &&
        proofBoolean(runtimeProof, 'modelLoaded') === true &&
        proofBoolean(runtimeProof, 'manifestIsRealModel') !== false &&
        proofString(runtimeProof, 'loadError') === null &&
        !runtimeIsFake;

  if (runtimeIsFake || !runtimeIsReal) return false;

  if (verdict === 'ACCEPT') {
    return (
      hasModelProof &&
      chipIsUsable(summary, 'cas_readout') &&
      chipIsUsable(summary, 'causal_proof') &&
      chipIsUsable(summary, 'control_proof') &&
      chipIsUsable(summary, 'output_proof') &&
      chipIsUsable(summary, 'packet_proof')
    );
  }

  return hasModelProof;
}

// ---------------------------------------------------------------------------
// Run transcript adapter (Audit Bench)
//
// `lifecycleToTranscript` maps a session's lifecycle entries into plain-English
// transcript rows for the run log. It NEVER JSON.stringifies — each row is a
// sentence a reviewer can read. When a lifecycle entry carries no message we
// fall back to a stage description keyed off the backend status.
// ---------------------------------------------------------------------------

export type TranscriptGlyphState = 'done' | 'active' | 'pending' | 'failed';

export interface TranscriptRow {
  id: string;
  /** Pre-formatted clock label (HH:MM), or '—' when no timestamp is present. */
  time: string;
  /** Plain-English sentence describing what happened at this step. */
  text: string;
  state: TranscriptGlyphState;
}

// Structural shape of a lifecycle entry — kept local so this module does not
// import the API session type (which itself depends on this module).
interface LifecycleEntryLike {
  status?: string | null;
  message?: string | null;
  timestamp?: string | null;
}

interface SessionLifecycleLike {
  status?: string | null;
  lifecycle?: LifecycleEntryLike[] | null;
}

// Plain-English fallback copy per backend lifecycle status. Mirrors the
// AuditSessionProgress step descriptions without importing the component.
const LIFECYCLE_STATUS_SENTENCE: Record<string, string> = {
  DRAFT: 'Preparing the model, scenario, and audit modules…',
  VALIDATING: 'Validating model access, license limits, and runtime proof…',
  RUNNING: 'Running CAS modules against the model output…',
  SCAFFOLD_PENDING_RUNNER:
    'Session created, but the real audit runner is not connected yet.',
  EVIDENCE_PENDING: 'Building the evidence packet (audit trail and anchor)…',
  EVIDENCE_READY: 'Evidence packet assembled; finalizing the verdict…',
  COMPLETE: 'Audit complete — verdict and evidence are ready to review.',
  FAILED: 'Audit stopped before an evidence-gated verdict was produced.',
};

// Terminal statuses map to a glyph directly; everything else is resolved by
// position relative to the session's current status.
const TERMINAL_GLYPH: Record<string, TranscriptGlyphState> = {
  COMPLETE: 'done',
  FAILED: 'failed',
};

const LIFECYCLE_ORDER: Record<string, number> = {
  DRAFT: 0,
  VALIDATING: 1,
  RUNNING: 2,
  SCAFFOLD_PENDING_RUNNER: 3,
  EVIDENCE_PENDING: 4,
  EVIDENCE_READY: 5,
  COMPLETE: 6,
  FAILED: -1,
};

function transcriptTime(timestamp: string | null | undefined): string {
  if (!timestamp) return '—';
  const parsed = new Date(timestamp);
  if (Number.isNaN(parsed.getTime())) return '—';
  const hh = String(parsed.getHours()).padStart(2, '0');
  const mm = String(parsed.getMinutes()).padStart(2, '0');
  return `${hh}:${mm}`;
}

function transcriptSentence(entry: LifecycleEntryLike): string {
  const message = typeof entry.message === 'string' ? entry.message.trim() : '';
  if (message.length > 0) return message;
  const status = typeof entry.status === 'string' ? entry.status : '';
  return LIFECYCLE_STATUS_SENTENCE[status] ?? 'Audit step recorded.';
}

function transcriptGlyph(
  entryStatus: string,
  currentStatus: string,
  isLast: boolean,
): TranscriptGlyphState {
  const terminal = TERMINAL_GLYPH[entryStatus];
  if (terminal) return terminal;
  if (currentStatus === 'FAILED') {
    // On a failed run, earlier steps are settled; the failure row is rendered
    // from its own FAILED status above.
    return 'done';
  }
  if (isLast) return 'active';
  const entryRank = LIFECYCLE_ORDER[entryStatus] ?? 0;
  const currentRank = LIFECYCLE_ORDER[currentStatus] ?? 0;
  return entryRank < currentRank ? 'done' : 'pending';
}

export function lifecycleToTranscript(
  session: SessionLifecycleLike | null | undefined,
): TranscriptRow[] {
  const entries = session?.lifecycle ?? [];
  if (!Array.isArray(entries) || entries.length === 0) return [];
  const currentStatus = typeof session?.status === 'string' ? session.status : '';
  return entries.map((entry, index) => {
    const entryStatus = typeof entry.status === 'string' ? entry.status : '';
    const isLast = index === entries.length - 1;
    return {
      id: `${index}-${entryStatus || 'step'}`,
      time: transcriptTime(entry.timestamp),
      text: transcriptSentence(entry),
      state: transcriptGlyph(entryStatus, currentStatus, isLast),
    };
  });
}

// ---------------------------------------------------------------------------
// Scope ribbon adapter (Audit Bench)
//
// Promotes the previously-buried verifier scope + boundary strings to a
// persistent ribbon. Wording is preserved EXACTLY from AuditVerdictExplainer's
// verifierScopeLabel/verifierBoundary so the validation-vs-production boundary
// reads identically wherever it appears.
// ---------------------------------------------------------------------------

export interface ScopeRibbonModel {
  /** e.g. "Scope: Stage 9 40E validation packet" (null when no scope). */
  scopeLabel: string | null;
  /** The validation-packet boundary caveat (null unless a validation packet). */
  boundaryLabel: string | null;
  /** A short scope/disposition line sourced from audit_scope, when present. */
  dispositionLabel: string | null;
  /** True when this is a validation (not live customer-production) packet. */
  isValidationPacket: boolean;
}

// Minimal structural shapes so this module does not import the API types.
interface VerifierDecisionLike {
  decisionScope?: string | null;
}

interface AuditScopeLike {
  label?: string | null;
  detail?: string | null;
  verdictDisposition?: string | null;
}

export function scopeRibbonModel(
  verifierDecision: VerifierDecisionLike | null | undefined,
  auditScope: AuditScopeLike | null | undefined,
): ScopeRibbonModel {
  const scope = verifierDecision?.decisionScope ?? null;
  const isValidationPacket = scope === 'stage9_40e_validation_packet';

  let scopeLabel: string | null = null;
  if (scope) {
    scopeLabel = isValidationPacket
      ? 'Scope: Stage 9 40E validation packet'
      : `Scope: ${scope.replace(/_/g, ' ')}`;
  } else if (auditScope?.label) {
    scopeLabel = `Scope: ${auditScope.label}`;
  }

  const boundaryLabel = isValidationPacket
    ? 'Boundary: this is a validation-packet verdict, not a live customer-production row.'
    : null;

  const dispositionLabel = auditScope?.detail ?? null;

  return { scopeLabel, boundaryLabel, dispositionLabel, isValidationPacket };
}

// ---------------------------------------------------------------------------
// License state adapter (Audit Bench)
//
// `licenseStateFor` derives a persistent LICENSED / NOT LICENSED / LICENSE
// UNKNOWN chip state from whatever real entitlement signal is available. It
// NEVER speculatively returns LICENSED — only an explicit positive signal
// (resolved === true / a redeemed entitlement) yields LICENSED; an explicit
// negative yields NOT LICENSED; anything unresolved is LICENSE UNKNOWN (muted).
// ---------------------------------------------------------------------------

export type LicenseState = 'LICENSED' | 'NOT LICENSED' | 'LICENSE UNKNOWN';

export interface LicenseSignal {
  /** Explicit entitlement resolution, when the backend/account has answered. */
  entitled?: boolean | null;
  /** A non-empty bearer/license token counts as a positive entitlement signal. */
  authToken?: string | null;
  /** A redeemed invite/license key counts as a positive entitlement signal. */
  redeemedKey?: string | null;
}

export function licenseStateFor(signal: LicenseSignal | null | undefined): LicenseState {
  if (!signal) return 'LICENSE UNKNOWN';
  if (signal.entitled === true) return 'LICENSED';
  if (signal.entitled === false) return 'NOT LICENSED';
  const token = typeof signal.authToken === 'string' ? signal.authToken.trim() : '';
  if (token.length > 0) return 'LICENSED';
  const key = typeof signal.redeemedKey === 'string' ? signal.redeemedKey.trim() : '';
  if (key.length > 0) return 'LICENSED';
  return 'LICENSE UNKNOWN';
}

function resolveChipEvidence(input: ChipEvidenceInput): {
  status: AuditStatus;
  detail: string | null;
} {
  if (input === true) return { status: 'verified', detail: null };
  if (input === false || input === null || input === undefined) {
    return { status: 'missing', detail: null };
  }
  if (isAuditStatus(input)) return { status: input, detail: null };

  if (input.failed === true) return { status: 'failed', detail: input.detail ?? null };
  if (isAuditStatus(input.status)) {
    return { status: input.status, detail: input.detail ?? input.label ?? null };
  }
  if (input.status === true || input.verified === true) {
    return { status: 'verified', detail: input.detail ?? input.label ?? null };
  }
  if (input.status === false || input.present === false) {
    return { status: 'missing', detail: input.detail ?? input.label ?? null };
  }
  if (input.present === true) {
    return { status: 'present', detail: input.detail ?? input.label ?? null };
  }
  return { status: 'unavailable', detail: input.detail ?? input.label ?? null };
}

function isAuditStatus(value: unknown): value is AuditStatus {
  return (
    value === 'verified' ||
    value === 'present' ||
    value === 'missing' ||
    value === 'failed' ||
    value === 'unavailable'
  );
}

function chipIsUsable(
  summary: AuditSessionSummary,
  id: ProvenanceChipId,
): boolean {
  const status = summary.provenanceChips.find((chip) => chip.id === id)?.status ?? null;
  return status === 'verified' || status === 'present';
}

function proofBoolean(
  proof: AuditRuntimeProof,
  key: 'isRealModel' | 'modelLoaded' | 'fakeRuntimeEnv' | 'manifestIsRealModel',
): boolean | null {
  const snakeKey = toSnakeProofKey(key);
  const value = proof[key] ?? proof[snakeKey];
  return typeof value === 'boolean' ? value : null;
}

function proofString(
  proof: AuditRuntimeProof,
  key: 'loadError',
): string | null {
  const value = proof[key] ?? proof.load_error ?? null;
  return typeof value === 'string' && value.length > 0 ? value : null;
}

function toSnakeProofKey(
  key: 'isRealModel' | 'modelLoaded' | 'fakeRuntimeEnv' | 'manifestIsRealModel',
): 'is_real_model' | 'model_loaded' | 'fake_runtime_env' | 'manifest_is_real_model' {
  switch (key) {
    case 'isRealModel':
      return 'is_real_model';
    case 'modelLoaded':
      return 'model_loaded';
    case 'fakeRuntimeEnv':
      return 'fake_runtime_env';
    case 'manifestIsRealModel':
      return 'manifest_is_real_model';
  }
}

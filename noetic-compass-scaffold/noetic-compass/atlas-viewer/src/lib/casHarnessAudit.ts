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

/**
 * TypeScript types + runtime guard for the Stage 21A CAS Harness
 * Evidence Packet schema (`cas_harness_evidence_packet_v1`).
 *
 * This file is the dashboard-side mirror of the Python export schema at
 * `research/cas_probe/evidence_packets/stage21a_*.json`. It is distinct
 * from `lib/evidence_packet.ts`, which targets a different upstream
 * artifact (`evidence_packet.v1`). Both schemas co-exist by design;
 * Stage 21A packets are exported from locked Stage 19/20B reports and
 * surface a bounded readout + readiness decision, not a generation
 * trace.
 *
 * Every nested object carries a `Record<string, unknown>` index
 * signature so forward-compatible additions to the Python schema do not
 * require an immediate dashboard release. Strictness is preserved on
 * the load-bearing fields the drawer renders by name.
 */

// ── Schema literal ────────────────────────────────────────────────────────

export const EVIDENCE_PACKET_SCHEMA_VERSION =
  'cas_harness_evidence_packet_v1' as const;
export type EvidencePacketSchemaVersion =
  typeof EVIDENCE_PACKET_SCHEMA_VERSION;

// ── Generation readiness enums ────────────────────────────────────────────

/**
 * Stage 20 generation_readiness action. The four reserved-language
 * values are surfaced verbatim on the UI badge — see VerificationPanel
 * style mapping for the badge colors.
 */
export type GenerationReadinessAction =
  | 'allow'
  | 'caveat'
  | 'constrain'
  | 'suppress';

export type GenerationReadinessMode =
  | 'BALANCED'
  | 'HIGH_PRECISION'
  | 'MAX_COVERAGE_TRIAGE'
  | string;

// ── Nested-section interfaces ─────────────────────────────────────────────

/**
 * Sub-section: per-axis readout. Mirrors the `readout` block in the
 * Stage 21A JSON. `votes` is a free-form string→string map keyed by
 * position name (focus_token / final_token / mean_over_seq_len).
 */
export interface EvidenceReadout {
  axis: string;
  label: string;
  layer: number | null;
  position: string | null;
  confidence: number | null;
  confidence_source: string | null;
  stable_agree: string[];
  votes: Record<string, string>;
  [key: string]: unknown;
}

export interface EvidenceControls {
  random_ablation: string | null;
  text_baseline: string | null;
  metadata_baseline: string | null;
  raw_symbol_delta: number | null;
  [key: string]: unknown;
}

export interface EvidenceDiagnostics {
  lacunarity: number | null;
  blindspot_flags: string[];
  note: string | null;
  [key: string]: unknown;
}

export interface EvidenceConditioning {
  p_value: string | number | null;
  partner_margin: number | null;
  positive_cases: string | null;
  probe_readable_delta: number | null;
  [key: string]: unknown;
}

export interface EvidenceGenerationReadinessEvidence {
  inversion_flag_count: number;
  max_gap_probability: number;
  max_lacunarity: number;
  mean_gap_probability: number;
  min_domain_confidence: number;
  mode: GenerationReadinessMode;
  rpm_satisfaction: number;
  verification_accepted: boolean;
  [key: string]: unknown;
}

export interface EvidenceGenerationReadiness {
  generation_readiness: GenerationReadinessAction;
  mode: GenerationReadinessMode;
  recommended_mode: GenerationReadinessMode;
  policy_version: string;
  reasons: string[];
  risk_score: number;
  evidence: EvidenceGenerationReadinessEvidence;
  [key: string]: unknown;
}

export interface EvidenceModel {
  family: string;
  model_key: string;
  name: string;
  revision: string;
  [key: string]: unknown;
}

export interface EvidenceProvenance {
  activation_file: string;
  activation_sha256: string;
  code_commit: string;
  fixture_sha256: string;
  source_reports: string[];
  source_stage: string;
  [key: string]: unknown;
}

export interface EvidenceVerification {
  accepted: boolean;
  confidence_tier: string;
  mode: GenerationReadinessMode;
  mode_profile: Record<string, unknown>;
  suppression_reasons: string[];
  [key: string]: unknown;
}

// ── Top-level packet ──────────────────────────────────────────────────────

export interface EvidencePacket {
  schema_version: EvidencePacketSchemaVersion;
  trace_id: string;
  created_at: string;
  boundary: string;
  export_label: string;
  claim_badges: string[];
  caveats: string[];
  rejected_claims: string[];

  model: EvidenceModel;
  readout: EvidenceReadout;
  controls: EvidenceControls;
  diagnostics: EvidenceDiagnostics;
  conditioning: EvidenceConditioning;
  generation_readiness: EvidenceGenerationReadiness;
  provenance: EvidenceProvenance;
  verification?: EvidenceVerification;

  /** Forward-compat: allow future top-level keys without a release. */
  [key: string]: unknown;
}

// ── Helpers ───────────────────────────────────────────────────────────────

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((v) => typeof v === 'string');
}

/**
 * Runtime type guard for an Evidence Packet. Validates the 15 load-bearing
 * top-level fields the drawer renders by name. Sub-shapes are checked at
 * the "this is an object / array / string" level — full deep validation
 * is intentionally not enforced, because the Python schema is the
 * source of truth and we want forward-compatibility on minor additions.
 */
export function isEvidencePacket(value: unknown): value is EvidencePacket {
  if (!isPlainObject(value)) return false;
  if (value.schema_version !== EVIDENCE_PACKET_SCHEMA_VERSION) return false;

  if (typeof value.trace_id !== 'string') return false;
  if (typeof value.created_at !== 'string') return false;
  if (typeof value.boundary !== 'string') return false;
  if (typeof value.export_label !== 'string') return false;

  if (!isStringArray(value.claim_badges)) return false;
  if (!isStringArray(value.caveats)) return false;
  if (!isStringArray(value.rejected_claims)) return false;

  if (!isPlainObject(value.model)) return false;
  if (!isPlainObject(value.readout)) return false;
  if (!isPlainObject(value.controls)) return false;
  if (!isPlainObject(value.diagnostics)) return false;
  if (!isPlainObject(value.conditioning)) return false;
  if (!isPlainObject(value.provenance)) return false;

  const gen = value.generation_readiness;
  if (!isPlainObject(gen)) return false;
  if (typeof gen.generation_readiness !== 'string') return false;
  if (typeof gen.mode !== 'string') return false;
  if (typeof gen.recommended_mode !== 'string') return false;
  if (!isStringArray(gen.reasons)) return false;

  return true;
}

/**
 * Best-effort error-reporting validator. Returns the first missing
 * top-level key on failure so callers can surface precise UI messages
 * without leaking schema internals.
 */
export function validateEvidencePacket(
  value: unknown,
): { ok: true; packet: EvidencePacket } | { ok: false; error: string } {
  if (!isPlainObject(value)) {
    return { ok: false, error: 'evidence packet is not a JSON object' };
  }
  if (value.schema_version !== EVIDENCE_PACKET_SCHEMA_VERSION) {
    return {
      ok: false,
      error: `expected schema_version "${EVIDENCE_PACKET_SCHEMA_VERSION}", got "${String(
        value.schema_version,
      )}"`,
    };
  }
  if (isEvidencePacket(value)) return { ok: true, packet: value };
  // Walk the required fields one more time to name the failure.
  const required: Array<keyof EvidencePacket> = [
    'trace_id',
    'created_at',
    'boundary',
    'export_label',
    'claim_badges',
    'caveats',
    'rejected_claims',
    'model',
    'readout',
    'controls',
    'diagnostics',
    'conditioning',
    'generation_readiness',
    'provenance',
  ];
  for (const key of required) {
    if (!(key in value)) {
      return {
        ok: false,
        error: `evidence packet missing required field "${String(key)}"`,
      };
    }
  }
  return { ok: false, error: 'evidence packet has a malformed nested section' };
}

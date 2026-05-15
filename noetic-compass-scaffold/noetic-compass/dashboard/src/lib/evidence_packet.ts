/**
 * Evidence Packet — typed API client.
 *
 * Wraps the `/api/evidence/{trace_id}` and `/api/evidence/{trace_id}/verify`
 * endpoints. The packet is the inspectable object the EvidencePacket drawer
 * renders: input, CAS expression, output, copy/slot trace, provenance,
 * hashes, claim levels, caveats.
 *
 * Design notes:
 *   - Uses the existing `apiFetch` (which already prepends `/api` and handles
 *     auth/token refresh + ApiError shaping). Callers pass the path AFTER
 *     `/api`, so we ask for `/evidence/{trace_id}`.
 *   - Claim-level vocabulary is locked to four values: cas_hard_trace,
 *     source_copy_evidence, derived_trace, neural_attribution_estimate. The
 *     drawer renders a colored badge per level — see EvidencePacket.tsx for
 *     the palette. Keep this list in sync if it ever expands.
 *   - Drawer is standalone-mountable. Callers can either let the drawer fetch
 *     on its own (pass traceId only) or skip the HTTP call by handing in a
 *     pre-built EvidencePacket via the `initialPacket` prop.
 */
import { apiFetch } from '../api/client';

/** Strength-of-evidence categories for a CAS claim. */
export type EvidenceClaimLevel =
  | 'cas_hard_trace'
  | 'source_copy_evidence'
  | 'derived_trace'
  | 'neural_attribution_estimate';

/** Source slot the copy trace points at. */
export type EvidenceSlotRole =
  | 'noetic'
  | 'domain'
  | 'drive'
  | 'register'
  | 'stage_var'
  | 'omega'
  | 'identifier';

export interface EvidencePacketInput {
  text: string;
  user_id?: string;
  session_id?: string;
}

export interface EvidencePacketCasExpression {
  text: string;
  compiler_valid: boolean;
  compiler_error?: string;
  grammar_category?: string;
}

export interface EvidencePacketOutput {
  text: string;
  n_tokens?: number;
  max_new_tokens?: number;
}

export interface EvidenceCopySlotEntry {
  role: EvidenceSlotRole;
  name: string;
  copied: boolean;
  source_token_index?: number;
  target_token_index?: number;
  claim_level: EvidenceClaimLevel;
}

export interface EvidencePacketProvenance {
  model_checkpoint_id: string;
  checkpoint_label?: string;
  code_commit_sha: string;
  code_commit_summary?: string;
  run_command?: string;
  config_snapshot?: Record<string, unknown>;
}

export interface EvidencePacketHashesOnDisk {
  weights_path?: string;
  tokenizer_path?: string;
  english_bpe_path?: string;
  corpus_path?: string;
}

export interface EvidencePacketHashes {
  /** SHA-256 of the model weights file. Null when the artifact is missing on this host. */
  weights_sha: string | null;
  /** SHA-256 of the tokenizer.json. Null when missing. */
  tokenizer_hash: string | null;
  /** SHA-256 of the english BPE side-car. Null when not used for this packet. */
  english_bpe_hash?: string | null;
  /** SHA-256 of the training corpus snapshot. Null when not recorded. */
  corpus_sha256?: string | null;
  on_disk_paths: EvidencePacketHashesOnDisk;
}

export interface EvidencePacketClaim {
  claim: string;
  level: EvidenceClaimLevel;
  rationale: string;
}

export interface EvidencePacket {
  schema_version: 'evidence_packet.v1';
  trace_id: string;
  generated_at: string;
  input: EvidencePacketInput;
  cas_expression?: EvidencePacketCasExpression;
  output: EvidencePacketOutput;
  copy_slot_trace?: EvidenceCopySlotEntry[];
  provenance: EvidencePacketProvenance;
  hashes: EvidencePacketHashes;
  claim_levels: EvidencePacketClaim[];
  caveats?: string[];
}

export interface VerifyHashCheck {
  /** Lowercase artifact id (weights | tokenizer | english_bpe | corpus | code_commit). */
  artifact: string;
  /** Expected SHA from the packet. Null when the packet did not record one. */
  expected: string | null;
  /** Freshly-computed SHA. Null when the file is missing, oversized, or rejected by the allowlist. */
  actual: string | null;
  match: boolean;
  notes?: string;
}

export interface VerifyHashesResponse {
  trace_id: string;
  verified_at: string;
  checks: VerifyHashCheck[];
  overall: 'all_match' | 'partial_mismatch' | 'unable_to_verify';
}

/**
 * Fetch the evidence packet for a given trace ID.
 *
 * Surfaces ApiError as-is so the drawer can render the detail/status.
 */
export async function fetchEvidencePacket(
  traceId: string,
): Promise<EvidencePacket> {
  return apiFetch<EvidencePacket>(
    `/evidence/${encodeURIComponent(traceId)}`,
  );
}

/**
 * Ask the backend to re-hash the on-disk artifacts and compare them to the
 * packet's recorded hashes. Returns a per-artifact verdict plus an overall
 * verdict the drawer renders as a banner.
 */
export async function verifyEvidenceHashes(
  traceId: string,
): Promise<VerifyHashesResponse> {
  return apiFetch<VerifyHashesResponse>(
    `/evidence/${encodeURIComponent(traceId)}/verify`,
    { method: 'POST' },
  );
}

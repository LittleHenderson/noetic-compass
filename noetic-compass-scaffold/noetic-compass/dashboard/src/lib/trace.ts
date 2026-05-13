/**
 * TypeScript types + validator for the `traceability_v0` JSON schema.
 *
 * Authoritative source: `cas-native/inference/traceability_v0.py` and
 * `cas-native/inference/thought_tree.py`. Every field here mirrors a
 * field there. If the Python schema changes, this file must change.
 *
 * The schema captures one CAS reply's full structured trace:
 *   - input        — what the user / CAS pipeline fed the model
 *   - output       — what the model emitted
 *   - copy         — source-reference copy success / coverage
 *   - slot_trace   — per-position slot-id summary
 *   - confidence   — qualitative bands + caveats + warning flags
 *   - thought_tree — UI-ready node+edge graph
 *
 * `isAtlasTrace(value)` validates an unknown blob at the JSON-parse
 * boundary. It checks the schema version, that all required top-level
 * keys exist, and that key sub-shapes are well-formed. It does NOT
 * fully type-narrow every nested field — consumers may still want to
 * defensively handle missing optional fields.
 */

// ── Schema literal ────────────────────────────────────────────────

export const TRACE_SCHEMA_VERSION = 'traceability_v0' as const;
export type TraceSchemaVersion = typeof TRACE_SCHEMA_VERSION;

// ── Severity / status enums ───────────────────────────────────────

export type WarningSeverity = 'info' | 'warning' | 'error';
export type CopyStatus = 'copied' | 'missed';

// ── Input section (discriminated union) ───────────────────────────

export interface SourceToken {
  index: number;
  token: string;
}

export interface NlBridgeMeta {
  matched_pattern: string | null;
  confidence: number;
  rationale: string | null;
  inferred_cas_expression: string;
}

/** Plain-CAS input (no NL bridge was used). */
export interface AtlasTraceInputCas {
  input_kind: 'cas_expression';
  cas_expression: string;
  source_tokens: SourceToken[];
}

/** NL → CAS bridge input (Step 5B). Carries the original English. */
export interface AtlasTraceInputNlBridge {
  input_kind: 'nl_bridge';
  user_text: string;
  cas_expression: string;
  source_tokens: SourceToken[];
  nl_bridge: NlBridgeMeta;
}

export type AtlasTraceInput = AtlasTraceInputCas | AtlasTraceInputNlBridge;

// ── Output section ────────────────────────────────────────────────

export interface AtlasTraceOutput {
  english: string;
  n_tokens: number;
}

// ── Copy / identifier section ─────────────────────────────────────

export interface PerIdentifierEntry {
  identifier: string;
  status: CopyStatus;
  position_in_input: number;
  position_in_output: number | null;
  identifier_ever_copied: boolean;
}

export interface AtlasTraceCopy {
  copied_identifiers: string[];
  missed_identifiers: string[];
  coverage: number | null;
  per_identifier: PerIdentifierEntry[];
}

// ── Slot trace section ────────────────────────────────────────────

export interface AtlasTraceSlotTrace {
  length: number;
  slot_counts_by_label: Record<string, number>;
  longest_stage_var_run: number;
  /** Raw per-position trace. Present in Mode 7; null in v0. */
  raw_trace: unknown | null;
}

// ── Confidence section ────────────────────────────────────────────

export interface WarningFlag {
  kind: string;
  severity: WarningSeverity;
  message: string;
}

export interface AtlasTraceConfidence {
  qualitative_coverage: string;
  slot_quality: string;
  caveats: string[];
  warning_flags: WarningFlag[];
}

// ── Thought Tree section ──────────────────────────────────────────

export interface ThoughtTreeNode {
  id: string;
  node_key: string;
  kind: string;
  role: string;
  label: string;
  normalized_label: string;
  axis_attrs?: Record<string, unknown>;
  text?: string;
}

export interface ThoughtTreeEdge {
  id: string;
  edge_key: string;
  source: string;
  target: string;
  source_key: string;
  target_key: string;
  kind: string;
}

/** Nested-tree node shape (children form the recursion). UI may render
 * either the nested `root` or the flat `nodes` + `edges`. */
export interface ThoughtTreeRootNode {
  id?: string;
  node_key?: string;
  kind: string;
  role: string;
  label: string;
  normalized_label: string;
  axis_attrs?: Record<string, unknown>;
  text?: string;
  children?: ThoughtTreeRootNode[];
}

export interface AtlasTraceThoughtTree {
  root: ThoughtTreeRootNode;
  nodes: ThoughtTreeNode[];
  edges: ThoughtTreeEdge[];
  node_count: number;
  edge_count: number;
}

// ── Top-level trace ───────────────────────────────────────────────

export interface AtlasTrace {
  schema_version: TraceSchemaVersion;
  trace_id: string;
  created_at: string;
  input: AtlasTraceInput;
  output: AtlasTraceOutput;
  copy: AtlasTraceCopy;
  slot_trace: AtlasTraceSlotTrace;
  confidence: AtlasTraceConfidence;
  thought_tree: AtlasTraceThoughtTree;
}

// ── Validator ─────────────────────────────────────────────────────

/** The exact set of required top-level keys (per traceability_v0.py). */
export const REQUIRED_TRACE_KEYS = [
  'schema_version',
  'trace_id',
  'created_at',
  'input',
  'output',
  'copy',
  'slot_trace',
  'confidence',
  'thought_tree',
] as const;

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((v) => typeof v === 'string');
}

function isValidInput(value: unknown): value is AtlasTraceInput {
  if (!isPlainObject(value)) return false;
  const kind = value.input_kind;
  if (kind !== 'cas_expression' && kind !== 'nl_bridge') return false;
  if (typeof value.cas_expression !== 'string') return false;
  if (!Array.isArray(value.source_tokens)) return false;
  for (const tok of value.source_tokens) {
    if (!isPlainObject(tok)) return false;
    if (typeof tok.index !== 'number') return false;
    if (typeof tok.token !== 'string') return false;
  }
  if (kind === 'nl_bridge') {
    if (typeof value.user_text !== 'string') return false;
    if (!isPlainObject(value.nl_bridge)) return false;
    const bridge = value.nl_bridge;
    if (typeof bridge.confidence !== 'number') return false;
    if (typeof bridge.inferred_cas_expression !== 'string') return false;
  }
  return true;
}

function isValidOutput(value: unknown): value is AtlasTraceOutput {
  return (
    isPlainObject(value) &&
    typeof value.english === 'string' &&
    typeof value.n_tokens === 'number'
  );
}

function isValidCopy(value: unknown): value is AtlasTraceCopy {
  if (!isPlainObject(value)) return false;
  if (!isStringArray(value.copied_identifiers)) return false;
  if (!isStringArray(value.missed_identifiers)) return false;
  if (value.coverage !== null && typeof value.coverage !== 'number') return false;
  if (!Array.isArray(value.per_identifier)) return false;
  for (const entry of value.per_identifier) {
    if (!isPlainObject(entry)) return false;
    if (typeof entry.identifier !== 'string') return false;
    if (entry.status !== 'copied' && entry.status !== 'missed') return false;
    if (typeof entry.position_in_input !== 'number') return false;
    if (
      entry.position_in_output !== null &&
      typeof entry.position_in_output !== 'number'
    ) {
      return false;
    }
    if (typeof entry.identifier_ever_copied !== 'boolean') return false;
  }
  return true;
}

function isValidSlotTrace(value: unknown): value is AtlasTraceSlotTrace {
  if (!isPlainObject(value)) return false;
  if (typeof value.length !== 'number') return false;
  if (typeof value.longest_stage_var_run !== 'number') return false;
  if (!isPlainObject(value.slot_counts_by_label)) return false;
  for (const count of Object.values(value.slot_counts_by_label)) {
    if (typeof count !== 'number') return false;
  }
  // raw_trace is unknown | null — any shape is acceptable
  if (!('raw_trace' in value)) return false;
  return true;
}

function isValidConfidence(value: unknown): value is AtlasTraceConfidence {
  if (!isPlainObject(value)) return false;
  if (typeof value.qualitative_coverage !== 'string') return false;
  if (typeof value.slot_quality !== 'string') return false;
  if (!isStringArray(value.caveats)) return false;
  if (!Array.isArray(value.warning_flags)) return false;
  for (const flag of value.warning_flags) {
    if (!isPlainObject(flag)) return false;
    if (typeof flag.kind !== 'string') return false;
    if (typeof flag.message !== 'string') return false;
    if (
      flag.severity !== 'info' &&
      flag.severity !== 'warning' &&
      flag.severity !== 'error'
    ) {
      return false;
    }
  }
  return true;
}

function isValidThoughtTree(value: unknown): value is AtlasTraceThoughtTree {
  if (!isPlainObject(value)) return false;
  if (!isPlainObject(value.root)) return false;
  if (!Array.isArray(value.nodes)) return false;
  if (!Array.isArray(value.edges)) return false;
  if (typeof value.node_count !== 'number') return false;
  if (typeof value.edge_count !== 'number') return false;
  return true;
}

/**
 * Type guard for `AtlasTrace`. Returns true iff `value` is a plain
 * object with `schema_version === 'traceability_v0'` and every required
 * top-level key is present and well-formed.
 *
 * Use this at the JSON-parse boundary; downstream code can treat the
 * narrowed value as a fully-typed `AtlasTrace`.
 */
export function isAtlasTrace(value: unknown): value is AtlasTrace {
  if (!isPlainObject(value)) return false;
  if (value.schema_version !== TRACE_SCHEMA_VERSION) return false;
  for (const key of REQUIRED_TRACE_KEYS) {
    if (!(key in value)) return false;
  }
  if (typeof value.trace_id !== 'string') return false;
  if (typeof value.created_at !== 'string') return false;
  if (!isValidInput(value.input)) return false;
  if (!isValidOutput(value.output)) return false;
  if (!isValidCopy(value.copy)) return false;
  if (!isValidSlotTrace(value.slot_trace)) return false;
  if (!isValidConfidence(value.confidence)) return false;
  if (!isValidThoughtTree(value.thought_tree)) return false;
  return true;
}

/**
 * Validate a trace and return a structured result. On failure, the
 * `error` string names the first missing or malformed top-level key —
 * useful for surfacing precise UI error messages.
 */
export function validateAtlasTrace(
  value: unknown,
): { ok: true; trace: AtlasTrace } | { ok: false; error: string } {
  if (!isPlainObject(value)) {
    return { ok: false, error: 'Trace is not a JSON object.' };
  }
  if (value.schema_version !== TRACE_SCHEMA_VERSION) {
    return {
      ok: false,
      error: `Expected schema_version "${TRACE_SCHEMA_VERSION}", got "${String(
        value.schema_version,
      )}".`,
    };
  }
  for (const key of REQUIRED_TRACE_KEYS) {
    if (!(key in value)) {
      return { ok: false, error: `Trace is missing required key "${key}".` };
    }
  }
  if (typeof value.trace_id !== 'string') {
    return { ok: false, error: 'trace_id must be a string.' };
  }
  if (typeof value.created_at !== 'string') {
    return { ok: false, error: 'created_at must be a string.' };
  }
  if (!isValidInput(value.input)) {
    return { ok: false, error: 'input section is malformed.' };
  }
  if (!isValidOutput(value.output)) {
    return { ok: false, error: 'output section is malformed.' };
  }
  if (!isValidCopy(value.copy)) {
    return { ok: false, error: 'copy section is malformed.' };
  }
  if (!isValidSlotTrace(value.slot_trace)) {
    return { ok: false, error: 'slot_trace section is malformed.' };
  }
  if (!isValidConfidence(value.confidence)) {
    return { ok: false, error: 'confidence section is malformed.' };
  }
  if (!isValidThoughtTree(value.thought_tree)) {
    return { ok: false, error: 'thought_tree section is malformed.' };
  }
  return { ok: true, trace: value as unknown as AtlasTrace };
}

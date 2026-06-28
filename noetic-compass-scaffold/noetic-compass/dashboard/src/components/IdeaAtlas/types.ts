/**
 * IdeaAtlas — TypeScript types matching the Python data model.
 *
 * Source of truth: `cas-native/atlas/idea_atlas.py`. When updating the Python
 * dataclasses, this file MUST be updated in lock-step. The dashboard
 * deserializes IdeaAtlas JSON sent over the wire from the CAS-Native
 * inference path; mismatched field names will silently produce empty
 * renders.
 *
 * Authoritative Noetic primitives (CLAUDE.md, verbatim):
 *   ^0 Idea       — All things in and outside the Mind.
 *   ^1 Mind       — Various degrees of awareness.
 *   ^2 Positive   — affinity / attracted toward.
 *   ^3 Negative   — adverse / repelled by.
 *   ^4 Vibration  — resonance / impression.
 *   ^5 Female     — Mind impregnated with an Idea.
 *   ^6 Male       — Idea impregnated with another Idea.
 *   ^7 Rhythm     — rate / pattern of exposure.
 *   ^8 Above/Cause— triggers a different Idea.
 *   ^9 Below/Effect — Idea brought to Mind.
 */

// ---------------------------------------------------------------------------
// Authoritative ontology constants — kept in sync with idea_atlas.py
// ---------------------------------------------------------------------------

export const NOETIC_LABELS = [
  'Idea',
  'Mind',
  'Positive',
  'Negative',
  'Vibration',
  'Female',
  'Male',
  'Rhythm',
  'Above/Cause',
  'Below/Effect',
] as const;
export type NoeticName = (typeof NOETIC_LABELS)[number];

/** ^0..^9 carriers in the form `^N`. */
export type NoeticToken =
  | '^0'
  | '^1'
  | '^2'
  | '^3'
  | '^4'
  | '^5'
  | '^6'
  | '^7'
  | '^8'
  | '^9';

export const DOMAIN_LABELS = ['P', 'C', 'E', 'O'] as const;
export type DomainLabel = (typeof DOMAIN_LABELS)[number];

export const DRIVE_LABELS = ['F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7'] as const;
export type DriveLabel = (typeof DRIVE_LABELS)[number];

export const REGISTER_LABELS = ['T', 'A', 'f', 'E'] as const;
export type RegisterLabel = (typeof REGISTER_LABELS)[number];

export const REGISTER_MODE_LABELS = [
  'none',
  'single',
  'set_spec',
  'co_presence',
  'integration',
] as const;
export type RegisterMode = (typeof REGISTER_MODE_LABELS)[number];

export const EDGE_KINDS = [
  'involution_pair',
  'domain_descent',
  'domain_feedback',
  'drive_inversion',
  'rpm_chain',
  'cluster_member',
  'register_co_presence',
  'register_integration',
  'recipe_prerequisite',
  'production_target',
  'trace',
] as const;
export type EdgeKind = (typeof EDGE_KINDS)[number];

// ---------------------------------------------------------------------------
// Atlas wire types
// ---------------------------------------------------------------------------

export interface IdeaNode {
  /** Stable id within an atlas. By convention mirrors CAS expression form. */
  id: string;
  /** Human-readable label for tooltips and panels. */
  label: string;
  /** `^0`..`^9` Noetic carrier. */
  noetic: NoeticToken;
  /** Optional Domain (P / C / E / O). */
  domain: DomainLabel | null;
  /** Optional Drive (F1..F7). */
  drive: DriveLabel | null;
  /** Optional Register (T / A / f / E). */
  register: RegisterLabel | null;
  /** Activation in [0, 1]. */
  intensity: number;
  /**
   * True if the prediction lit this Idea up; false if this is an
   * involution-pair shadow (the absent Idea surfaced for contrast).
   */
  is_positive_space: boolean;
  /** Free-form, JSON-safe metadata. */
  metadata: Record<string, unknown>;
}

export interface IdeaEdge {
  source_id: string;
  target_id: string;
  edge_kind: EdgeKind;
  label: string | null;
  metadata: Record<string, unknown>;
}

export interface IdeaAtlas {
  nodes: IdeaNode[];
  edges: IdeaEdge[];
  /** UUID4 hex (32 chars). Shared with the diagram + prediction. */
  generation_id: string;
  /** Rendered CAS expression this atlas represents. */
  cas_expression: string;
  metadata: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Diagram wire types — matches the compiler's `diagram` field response shape.
// Source of truth: `api/notation/compiler.py` (build_diagram, ≈ line 5045).
// We only model the fields the IdeaAtlas toggle needs. The full DiagramNode
// shape is wider; see existing dashboard types in `dashboard/src/api/`.
// ---------------------------------------------------------------------------

export interface DiagramNode {
  id: string;
  label: string;
  /** Optional structured-CAS attributes for atlas correspondence. */
  noetic?: NoeticToken;
  domain?: DomainLabel;
  drive?: DriveLabel;
  register?: RegisterLabel;
  /** Compiler-side kind: 'state' | 'cluster' | 'omega' | etc. */
  kind?: string;
  metadata?: Record<string, unknown>;
}

export interface DiagramEdge {
  source_id: string;
  target_id: string;
  kind: string;
  label?: string;
  metadata?: Record<string, unknown>;
}

export interface DiagramContainer {
  id: string;
  label: string;
  member_ids: string[];
  metadata?: Record<string, unknown>;
}

export interface CasDiagram {
  nodes: DiagramNode[];
  edges: DiagramEdge[];
  containers: DiagramContainer[];
  layout_hint?:
    | 'radial'
    | 'dependency'
    | 'recipe'
    | 'containment'
    | 'topos';
  /** Same UUID as the IdeaAtlas it corresponds to. */
  generation_id?: string;
}

// ---------------------------------------------------------------------------
// GenerationTrace wire type — matches `cas_native.atlas.trace_mapping`.
// ---------------------------------------------------------------------------

export interface GenerationTrace {
  generation_id: string;
  timestamp_ms: number;
  user_input: string;
  prediction: CasPrediction;
  cas_expression: string;
  atlas_node_ids: string[];
  diagram_node_ids: string[];
  metadata: Record<string, unknown>;
}

/** v77 12-key prediction shape from Predictor.__call__. */
export interface CasPrediction {
  turn_type: string;
  expression_family: string;
  transition_kind: string;
  noetic: number;
  domain: DomainLabel | null;
  drive: DriveLabel | null;
  register_mode: RegisterMode;
  registers: RegisterLabel[];
  authority: string;
  has_omega: boolean;
  has_meta_logic: boolean;
  meta_relations: string[];
}

// ---------------------------------------------------------------------------
// Dashboard view-state types
// ---------------------------------------------------------------------------

export type AtlasViewMode = 'atlas' | 'diagram';

export interface ViewportTransform {
  /** Center x in scene coordinates. */
  x: number;
  /** Center y in scene coordinates. */
  y: number;
  /** Zoom factor — 1 = 100%, 2 = zoomed in 2x, 0.5 = zoomed out. */
  zoom: number;
}

export interface AtlasSelection {
  /** id of the clicked node in whichever view is active. */
  selected_node_id: string | null;
  /** generation_id the selection traces back to. */
  generation_id: string | null;
  /** The other-view ids that correspond to the selection (for highlighting on toggle). */
  corresponding_ids: string[];
}

/** Props handed down from the dashboard route to the IdeaAtlasView component. */
export interface IdeaAtlasContext {
  atlas: IdeaAtlas | null;
  diagram: CasDiagram | null;
  trace: GenerationTrace | null;
  /** Atlas-id → diagram-id[] map produced by `correspond_atlas_to_diagram`. */
  correspondence: Record<string, string[]>;
  /** Inverse map for diagram → atlas correspondence. */
  inverse_correspondence: Record<string, string[]>;
  loading: boolean;
  error: string | null;
}

// ---------------------------------------------------------------------------
// Hooks / handlers
// ---------------------------------------------------------------------------

/**
 * Click handler payload. Surfaced to the parent context so the dashboard can
 * drill into the prediction that produced the clicked node.
 */
export interface AtlasNodeClickEvent {
  source_view: AtlasViewMode;
  node_id: string;
  generation_id: string;
}

/** Type guard helpers — keep these aligned with `is_generation_id` in Python. */
export function isGenerationId(value: unknown): value is string {
  if (typeof value !== 'string' || value.length !== 32) return false;
  return /^[0-9a-fA-F]{32}$/.test(value);
}

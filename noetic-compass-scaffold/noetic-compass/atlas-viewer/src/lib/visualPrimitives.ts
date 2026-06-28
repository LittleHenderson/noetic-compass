import type { TestingMethod } from './testingMethods';

export const VISUAL_PRIMITIVE_KINDS = ['point', 'box', 'polyline', 'region'] as const;

export type VisualPrimitiveKind = (typeof VISUAL_PRIMITIVE_KINDS)[number];

export const VISUAL_PRIMITIVE_SOURCES = [
  'human_annotation',
  'fixture',
  'model_output',
  'cas_trace',
] as const;

export type VisualPrimitiveSource = (typeof VISUAL_PRIMITIVE_SOURCES)[number];

export const CAS_AXES = ['Noetic', 'Domain', 'Drive', 'Register'] as const;

export type CasAxis = (typeof CAS_AXES)[number];

export interface EvidenceRef {
  trace_id?: string;
  packet_id?: string;
  row_id?: string;
  token_index?: number;
}

export interface VisualPrimitive {
  id: string;
  kind: VisualPrimitiveKind;
  image_id: string;
  label?: string;
  coords_norm: number[];
  coords_px?: number[];
  cas_axis?: CasAxis;
  cas_label?: string;
  confidence?: number;
  source: VisualPrimitiveSource;
  evidence_ref?: EvidenceRef;
  explanation?: string;
}

export interface VisualGroundedTraceStep {
  trace_id: string;
  step_id: string;
  token_index?: number;
  text_span?: string;
  cas_state?: string;
  primitive_ids: string[];
  evidence_packet_ref?: string;
}

export interface SpatialEvidenceArtifact {
  schema_version: 'spatial_evidence_v1';
  trace_id: string;
  image_id: string;
  image_url: string;
  image_width: number;
  image_height: number;
  primitives: VisualPrimitive[];
  grounded_steps: VisualGroundedTraceStep[];
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function requireString(obj: Record<string, unknown>, key: string, ctx: string): string {
  const v = obj[key];
  if (typeof v !== 'string' || v.length === 0) {
    throw new Error(`${ctx}: field "${key}" must be a non-empty string`);
  }
  return v;
}

function optionalString(
  obj: Record<string, unknown>,
  key: string,
  ctx: string,
): string | undefined {
  if (!(key in obj) || obj[key] === undefined) return undefined;
  const v = obj[key];
  if (typeof v !== 'string') {
    throw new Error(`${ctx}: field "${key}" must be a string when present`);
  }
  return v;
}

function optionalNumber(
  obj: Record<string, unknown>,
  key: string,
  ctx: string,
): number | undefined {
  if (!(key in obj) || obj[key] === undefined) return undefined;
  const v = obj[key];
  if (typeof v !== 'number' || !Number.isFinite(v)) {
    throw new Error(`${ctx}: field "${key}" must be a finite number when present`);
  }
  return v;
}

function requireNumber(
  obj: Record<string, unknown>,
  key: string,
  ctx: string,
): number {
  const v = obj[key];
  if (typeof v !== 'number' || !Number.isFinite(v)) {
    throw new Error(`${ctx}: field "${key}" must be a finite number`);
  }
  return v;
}

function requireNumberArray(
  obj: Record<string, unknown>,
  key: string,
  ctx: string,
): number[] {
  const v = obj[key];
  if (!Array.isArray(v) || v.length === 0) {
    throw new Error(`${ctx}: field "${key}" must be a non-empty number array`);
  }
  for (let i = 0; i < v.length; i += 1) {
    const x = v[i];
    if (typeof x !== 'number' || !Number.isFinite(x)) {
      throw new Error(`${ctx}: field "${key}"[${i}] must be a finite number`);
    }
  }
  return v as number[];
}

function expectedCoordLength(kind: VisualPrimitiveKind, len: number): boolean {
  switch (kind) {
    case 'point':
      return len === 2;
    case 'box':
      return len === 4;
    case 'polyline':
    case 'region':
      return len >= 4 && len % 2 === 0;
  }
}

function parseEvidenceRef(value: unknown, ctx: string): EvidenceRef {
  if (!isPlainObject(value)) {
    throw new Error(`${ctx}: evidence_ref must be an object`);
  }
  const ref: EvidenceRef = {};
  if (value.trace_id !== undefined) ref.trace_id = requireString(value, 'trace_id', ctx);
  if (value.packet_id !== undefined) ref.packet_id = requireString(value, 'packet_id', ctx);
  if (value.row_id !== undefined) ref.row_id = requireString(value, 'row_id', ctx);
  if (value.token_index !== undefined) {
    const ti = value.token_index;
    if (typeof ti !== 'number' || !Number.isInteger(ti) || ti < 0) {
      throw new Error(`${ctx}: evidence_ref.token_index must be a non-negative integer`);
    }
    ref.token_index = ti;
  }
  return ref;
}

export function parseVisualPrimitive(json: unknown): VisualPrimitive {
  const ctx = 'parseVisualPrimitive';
  if (!isPlainObject(json)) {
    throw new Error(`${ctx}: input must be an object`);
  }

  const id = requireString(json, 'id', ctx);
  const kindRaw = requireString(json, 'kind', ctx);
  if (!(VISUAL_PRIMITIVE_KINDS as readonly string[]).includes(kindRaw)) {
    throw new Error(
      `${ctx}: field "kind" must be one of ${VISUAL_PRIMITIVE_KINDS.join(', ')} (got "${kindRaw}")`,
    );
  }
  const kind = kindRaw as VisualPrimitiveKind;

  const image_id = requireString(json, 'image_id', ctx);
  const coords_norm = requireNumberArray(json, 'coords_norm', ctx);
  if (!expectedCoordLength(kind, coords_norm.length)) {
    throw new Error(
      `${ctx}: coords_norm length ${coords_norm.length} invalid for kind "${kind}"`,
    );
  }
  for (let i = 0; i < coords_norm.length; i += 1) {
    const x = coords_norm[i];
    if (x < 0 || x > 1) {
      throw new Error(`${ctx}: coords_norm[${i}]=${x} must be in [0,1]`);
    }
  }

  const sourceRaw = requireString(json, 'source', ctx);
  if (!(VISUAL_PRIMITIVE_SOURCES as readonly string[]).includes(sourceRaw)) {
    throw new Error(
      `${ctx}: field "source" must be one of ${VISUAL_PRIMITIVE_SOURCES.join(', ')} (got "${sourceRaw}")`,
    );
  }
  const source = sourceRaw as VisualPrimitiveSource;

  const result: VisualPrimitive = {
    id,
    kind,
    image_id,
    coords_norm,
    source,
  };

  const label = optionalString(json, 'label', ctx);
  if (label !== undefined) result.label = label;

  if (json.coords_px !== undefined) {
    const coords_px = requireNumberArray(json, 'coords_px', ctx);
    if (coords_px.length !== coords_norm.length) {
      throw new Error(
        `${ctx}: coords_px length ${coords_px.length} must equal coords_norm length ${coords_norm.length}`,
      );
    }
    result.coords_px = coords_px;
  }

  if (json.cas_axis !== undefined) {
    const axisRaw = requireString(json, 'cas_axis', ctx);
    if (!(CAS_AXES as readonly string[]).includes(axisRaw)) {
      throw new Error(
        `${ctx}: field "cas_axis" must be one of ${CAS_AXES.join(', ')} (got "${axisRaw}")`,
      );
    }
    result.cas_axis = axisRaw as CasAxis;
  }

  const cas_label = optionalString(json, 'cas_label', ctx);
  if (cas_label !== undefined) result.cas_label = cas_label;

  const confidence = optionalNumber(json, 'confidence', ctx);
  if (confidence !== undefined) {
    if (confidence < 0 || confidence > 1) {
      throw new Error(`${ctx}: confidence=${confidence} must be in [0,1]`);
    }
    result.confidence = confidence;
  }

  if (json.evidence_ref !== undefined) {
    result.evidence_ref = parseEvidenceRef(json.evidence_ref, ctx);
  }

  const explanation = optionalString(json, 'explanation', ctx);
  if (explanation !== undefined) result.explanation = explanation;

  return result;
}

function parseGroundedStep(json: unknown, ctx: string): VisualGroundedTraceStep {
  if (!isPlainObject(json)) {
    throw new Error(`${ctx}: grounded step must be an object`);
  }
  const trace_id = requireString(json, 'trace_id', ctx);
  const step_id = requireString(json, 'step_id', ctx);
  const primitive_ids_raw = json.primitive_ids;
  if (!Array.isArray(primitive_ids_raw)) {
    throw new Error(`${ctx}: primitive_ids must be an array`);
  }
  const primitive_ids: string[] = [];
  for (let i = 0; i < primitive_ids_raw.length; i += 1) {
    const v = primitive_ids_raw[i];
    if (typeof v !== 'string' || v.length === 0) {
      throw new Error(`${ctx}: primitive_ids[${i}] must be a non-empty string`);
    }
    primitive_ids.push(v);
  }

  const step: VisualGroundedTraceStep = {
    trace_id,
    step_id,
    primitive_ids,
  };

  if (json.token_index !== undefined) {
    const ti = json.token_index;
    if (typeof ti !== 'number' || !Number.isInteger(ti) || ti < 0) {
      throw new Error(`${ctx}: token_index must be a non-negative integer`);
    }
    step.token_index = ti;
  }
  const text_span = optionalString(json, 'text_span', ctx);
  if (text_span !== undefined) step.text_span = text_span;
  const cas_state = optionalString(json, 'cas_state', ctx);
  if (cas_state !== undefined) step.cas_state = cas_state;
  const evidence_packet_ref = optionalString(json, 'evidence_packet_ref', ctx);
  if (evidence_packet_ref !== undefined) step.evidence_packet_ref = evidence_packet_ref;

  return step;
}

export function loadSpatialEvidenceArtifact(json: unknown): SpatialEvidenceArtifact {
  const ctx = 'loadSpatialEvidenceArtifact';
  if (!isPlainObject(json)) {
    throw new Error(`${ctx}: input must be an object`);
  }

  const schema_version = requireString(json, 'schema_version', ctx);
  if (schema_version !== 'spatial_evidence_v1') {
    throw new Error(
      `${ctx}: schema_version must be "spatial_evidence_v1" (got "${schema_version}")`,
    );
  }

  const trace_id = requireString(json, 'trace_id', ctx);
  const image_id = requireString(json, 'image_id', ctx);
  const image_url = requireString(json, 'image_url', ctx);
  const image_width = requireNumber(json, 'image_width', ctx);
  const image_height = requireNumber(json, 'image_height', ctx);
  if (image_width <= 0 || image_height <= 0) {
    throw new Error(`${ctx}: image_width and image_height must be positive`);
  }

  const primitivesRaw = json.primitives;
  if (!Array.isArray(primitivesRaw)) {
    throw new Error(`${ctx}: primitives must be an array`);
  }
  const primitives = primitivesRaw.map((p) => parseVisualPrimitive(p));

  const stepsRaw = json.grounded_steps;
  if (!Array.isArray(stepsRaw)) {
    throw new Error(`${ctx}: grounded_steps must be an array`);
  }
  const grounded_steps = stepsRaw.map((s) => parseGroundedStep(s, ctx));

  const primitiveIdSet = new Set(primitives.map((p) => p.id));
  for (const step of grounded_steps) {
    for (const pid of step.primitive_ids) {
      if (!primitiveIdSet.has(pid)) {
        throw new Error(
          `${ctx}: grounded step "${step.step_id}" references unknown primitive_id "${pid}"`,
        );
      }
    }
  }

  return {
    schema_version: 'spatial_evidence_v1',
    trace_id,
    image_id,
    image_url,
    image_width,
    image_height,
    primitives,
    grounded_steps,
  };
}

export function coordsNormToPx(
  p: VisualPrimitive,
  imageW: number,
  imageH: number,
): number[] {
  if (imageW <= 0 || imageH <= 0) {
    throw new Error(`coordsNormToPx: imageW and imageH must be positive`);
  }
  const norm = p.coords_norm;
  switch (p.kind) {
    case 'point': {
      return [norm[0] * imageW, norm[1] * imageH];
    }
    case 'box': {
      return [norm[0] * imageW, norm[1] * imageH, norm[2] * imageW, norm[3] * imageH];
    }
    case 'polyline':
    case 'region': {
      const out = new Array<number>(norm.length);
      for (let i = 0; i < norm.length; i += 2) {
        out[i] = norm[i] * imageW;
        out[i + 1] = norm[i + 1] * imageH;
      }
      return out;
    }
  }
}

export function primitivesForStep(
  artifact: SpatialEvidenceArtifact,
  stepId: string,
): VisualPrimitive[] {
  const step = artifact.grounded_steps.find((s) => s.step_id === stepId);
  if (!step) return [];
  const idSet = new Set(step.primitive_ids);
  return artifact.primitives.filter((p) => idSet.has(p.id));
}

export const SPATIAL_EVIDENCE_MODULE: TestingMethod = {
  id: 'spatial_evidence_layer',
  name: 'Spatial Evidence Layer',
  description:
    'Links CAS trace steps to points, boxes, or regions in an image so the user can see exactly what visual evidence a reasoning move refers to.',
  reveals:
    'Grounded trace overlay + evidence-linked visual references on uploaded or fixture images.',
  stageAnchor: 'Beta v0 (fixture-backed)',
  knobs: [
    {
      id: 'source_filter',
      label: 'Source filter',
      type: 'multiselect',
      default: ['human_annotation', 'fixture', 'model_output', 'cas_trace'],
      options: ['human_annotation', 'fixture', 'model_output', 'cas_trace'] as const,
    },
    {
      id: 'kind_filter',
      label: 'Kind filter',
      type: 'multiselect',
      default: ['point', 'box', 'polyline', 'region'],
      options: ['point', 'box', 'polyline', 'region'] as const,
    },
    {
      id: 'show_confidence',
      label: 'Show confidence',
      type: 'boolean',
      default: true,
    },
  ],
  outputShape: 'Per-step visual primitive list with CAS labels + evidence refs',
  costEstimateGpuMinutes: 0,
  prerequisites: ['image artifact + primitive annotations OR model-emitted coordinates'],
  validatedArchs: ['pythia'],
  orderIndex: 9,
  liveRuntime: {
    status: 'payload_only',
    supportedKnobs: ['source_filter', 'kind_filter', 'show_confidence'],
    effect:
      'Visual artifact filtering only; it does not alter live worker runtime',
  },
};

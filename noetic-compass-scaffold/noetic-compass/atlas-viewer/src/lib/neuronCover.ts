export interface NeuronCoord {
  layer: number;
  index: number;
  label: string;
}

export const FOUNDATION_CLASS_KEYS = [
  "F1A", "F1T", "F1f", "F1E",
  "F2A", "F2T", "F2f", "F2E",
  "F3A", "F3T", "F3f", "F3E",
  "F4A", "F4T", "F4f", "F4E",
  "F5A", "F5T", "F5f", "F5E",
  "F6A", "F6T", "F6f", "F6E",
  "F7A", "F7T", "F7f", "F7E",
] as const;

export type FoundationClassKey = (typeof FOUNDATION_CLASS_KEYS)[number];

export type CoverConfidenceStatus = "real" | "unavailable" | "unsupported";
export type CoverConfidenceLabel = "low" | "medium" | "high";

export interface CoverConfidence {
  status: CoverConfidenceStatus;
  score: number | null;
  label: CoverConfidenceLabel | null;
  reason?: string;
  provenance: Record<string, unknown>;
}

export interface CoverEvidence {
  target: string;
  candidate_layers: number[];
  neuron_cover: string[];
  clean_margin?: number;
  targeted_drop?: number;
  pair_kind?: string;
  partner?: string;
  sample_id?: string;
  confidence: CoverConfidence;
}

export interface RowReport {
  target: FoundationClassKey;
  candidate_layers: number[];
  neuron_cover: string[];
  clean_margin?: number;
  targeted_drop?: number;
  pair_kind?: string;
  partner?: string;
  sample_id?: string;
  confidence: CoverConfidence;
}

export interface Stage27FData {
  mlp_intermediate_dim: number;
  candidate_layers_per_class: Record<FoundationClassKey, number[]>;
  per_class_neuron_covers: Record<FoundationClassKey, string[]>;
  row_reports: RowReport[];
}

const COORD_RE = /^L(\d+)N(\d+)$/;
export const COVER_CONFIDENCE_FORMULA = "targeted_drop / clean_margin";
export const MAX_REPORTABLE_COVER_CONFIDENCE = 0.95;

export function parseCoord(s: string): NeuronCoord {
  if (typeof s !== "string") {
    throw new Error(`parseCoord: expected string, got ${typeof s}`);
  }
  const m = COORD_RE.exec(s);
  if (!m) {
    throw new Error(`parseCoord: invalid coord "${s}" (expected format "L{layer}N{index}")`);
  }
  const layer = Number.parseInt(m[1], 10);
  const index = Number.parseInt(m[2], 10);
  if (!Number.isFinite(layer) || !Number.isFinite(index)) {
    throw new Error(`parseCoord: non-numeric layer/index in "${s}"`);
  }
  return { layer, index, label: s };
}

export function formatCoord(layer: number, index: number): string {
  if (!Number.isInteger(layer) || layer < 0) {
    throw new Error(`formatCoord: layer must be a non-negative integer, got ${layer}`);
  }
  if (!Number.isInteger(index) || index < 0) {
    throw new Error(`formatCoord: index must be a non-negative integer, got ${index}`);
  }
  return `L${layer}N${index}`;
}

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function isFoundationClassKey(k: string): k is FoundationClassKey {
  return (FOUNDATION_CLASS_KEYS as readonly string[]).includes(k);
}

function finiteNumber(v: unknown): number | undefined {
  if (typeof v !== "number" || !Number.isFinite(v)) return undefined;
  return v;
}

function confidenceLabel(score: number): CoverConfidenceLabel {
  if (score > 0.8) return "high";
  if (score >= 0.5) return "medium";
  return "low";
}

function unavailableConfidence(
  reason: string,
  provenance: Record<string, unknown>,
): CoverConfidence {
  return {
    status: "unavailable",
    score: null,
    label: null,
    reason,
    provenance,
  };
}

export function unsupportedCoverConfidence(target: string): CoverConfidence {
  const drive = target.length >= 2 ? target.slice(0, 2) : target;
  return {
    status: "unsupported",
    score: null,
    label: null,
    reason: `drive ${drive} is unsupported; Stage 27F cover evidence supports F1-F7 register classes only`,
    provenance: {
      source_stage: "Stage 27F",
      confidence_scope: "cover-level",
      supported_classes: [...FOUNDATION_CLASS_KEYS],
    },
  };
}

export function deriveCoverConfidence(
  row: { targeted_drop?: unknown; clean_margin?: unknown },
  provenance: Record<string, unknown> = {},
): CoverConfidence {
  const prov: Record<string, unknown> = {
    source_stage: "Stage 27F",
    confidence_scope: "cover-level",
    formula: COVER_CONFIDENCE_FORMULA,
    ...provenance,
  };

  if (row.targeted_drop === undefined || row.targeted_drop === null) {
    return unavailableConfidence("targeted_drop missing from Stage 27F row evidence", prov);
  }
  const targetedDrop = finiteNumber(row.targeted_drop);
  if (targetedDrop === undefined || targetedDrop < 0) {
    return unavailableConfidence("targeted_drop must be a non-negative finite number", prov);
  }

  if (row.clean_margin === undefined || row.clean_margin === null) {
    return unavailableConfidence("clean_margin missing from Stage 27F row evidence", prov);
  }
  const cleanMargin = finiteNumber(row.clean_margin);
  if (cleanMargin === undefined || cleanMargin <= 0) {
    return unavailableConfidence("clean_margin must be a positive finite number", prov);
  }

  const rawScore = targetedDrop / cleanMargin;
  prov.targeted_drop = targetedDrop;
  prov.clean_margin = cleanMargin;
  prov.raw_score = rawScore;

  if (rawScore > MAX_REPORTABLE_COVER_CONFIDENCE) {
    return unavailableConfidence(
      "targeted_drop / clean_margin exceeds calibrated reportable range (> 0.95)",
      prov,
    );
  }

  return {
    status: "real",
    score: rawScore,
    label: confidenceLabel(rawScore),
    provenance: prov,
  };
}

export function formatCoverConfidence(confidence: CoverConfidence): string {
  if (confidence.status === "real" && typeof confidence.score === "number" && confidence.label) {
    return `Confidence: ${Math.round(confidence.score * 100)}% ${confidence.label}`;
  }
  const reason = confidence.reason ?? "no cover-level score available";
  return `Confidence: not available (${reason})`;
}

function snapshotProvenance(json: Record<string, unknown>): Record<string, unknown> {
  const artifactContract = isPlainObject(json["artifact_contract"])
    ? json["artifact_contract"]
    : {};
  return {
    source_stage: "Stage 27F",
    confidence_scope: "cover-level",
    formula: COVER_CONFIDENCE_FORMULA,
    ...(typeof json["schema_version"] === "string" ? { source_schema_version: json["schema_version"] } : {}),
    ...(typeof json["status"] === "string" ? { snapshot_status: json["status"] } : {}),
    ...(typeof artifactContract["status"] === "string" ? { artifact_status: artifactContract["status"] } : {}),
    ...(typeof artifactContract["formal_gate_valid"] === "boolean"
      ? { artifact_formal_gate_valid: artifactContract["formal_gate_valid"] }
      : {}),
  };
}

function validateClassKeyedRecord(
  raw: unknown,
  fieldName: string,
  innerCheck: (v: unknown, key: string) => void,
): Record<FoundationClassKey, unknown> {
  if (!isPlainObject(raw)) {
    throw new Error(`loadStage27FSnapshot: "${fieldName}" must be an object, got ${typeof raw}`);
  }
  const out: Partial<Record<FoundationClassKey, unknown>> = {};
  for (const [key, value] of Object.entries(raw)) {
    if (!isFoundationClassKey(key)) {
      throw new Error(`loadStage27FSnapshot: "${fieldName}" has unknown class key "${key}"`);
    }
    innerCheck(value, key);
    out[key] = value;
  }
  return out as Record<FoundationClassKey, unknown>;
}

function checkNumberArray(v: unknown, fieldName: string): asserts v is number[] {
  if (!Array.isArray(v) || !v.every((x) => typeof x === "number" && Number.isFinite(x))) {
    throw new Error(`loadStage27FSnapshot: "${fieldName}" must be a number[]`);
  }
}

function checkStringArray(v: unknown, fieldName: string): asserts v is string[] {
  if (!Array.isArray(v) || !v.every((x) => typeof x === "string")) {
    throw new Error(`loadStage27FSnapshot: "${fieldName}" must be a string[]`);
  }
}

function optionalString(raw: Record<string, unknown>, key: string): string | undefined {
  return typeof raw[key] === "string" ? raw[key] : undefined;
}

function loadRowReport(
  raw: unknown,
  idx: number,
  baseProvenance: Record<string, unknown>,
): RowReport {
  if (!isPlainObject(raw)) {
    throw new Error(`loadStage27FSnapshot: row_reports[${idx}] must be an object`);
  }
  const target = raw["target"];
  if (typeof target !== "string" || !isFoundationClassKey(target)) {
    throw new Error(`loadStage27FSnapshot: row_reports[${idx}].target invalid: ${String(target)}`);
  }
  checkNumberArray(raw["candidate_layers"], `row_reports[${idx}].candidate_layers`);
  checkStringArray(raw["neuron_cover"], `row_reports[${idx}].neuron_cover`);
  const rowProvenance: Record<string, unknown> = {
    ...baseProvenance,
    target,
    ...(optionalString(raw, "sample_id") ? { sample_id: optionalString(raw, "sample_id") } : {}),
    ...(optionalString(raw, "pair_kind") ? { pair_kind: optionalString(raw, "pair_kind") } : {}),
    ...(optionalString(raw, "partner") ? { partner: optionalString(raw, "partner") } : {}),
  };
  const cleanMargin = finiteNumber(raw["clean_margin"]);
  const targetedDrop = finiteNumber(raw["targeted_drop"]);
  return {
    target,
    candidate_layers: raw["candidate_layers"] as number[],
    neuron_cover: raw["neuron_cover"] as string[],
    ...(cleanMargin !== undefined ? { clean_margin: cleanMargin } : {}),
    ...(targetedDrop !== undefined ? { targeted_drop: targetedDrop } : {}),
    ...(optionalString(raw, "pair_kind") ? { pair_kind: optionalString(raw, "pair_kind") } : {}),
    ...(optionalString(raw, "partner") ? { partner: optionalString(raw, "partner") } : {}),
    ...(optionalString(raw, "sample_id") ? { sample_id: optionalString(raw, "sample_id") } : {}),
    confidence: deriveCoverConfidence(raw, rowProvenance),
  };
}

export function loadStage27FSnapshot(json: unknown): Stage27FData {
  if (!isPlainObject(json)) {
    throw new Error("loadStage27FSnapshot: input must be a JSON object");
  }

  const mlpDim = json["mlp_intermediate_dim"];
  if (typeof mlpDim !== "number" || !Number.isInteger(mlpDim) || mlpDim <= 0) {
    throw new Error(`loadStage27FSnapshot: "mlp_intermediate_dim" must be a positive integer, got ${String(mlpDim)}`);
  }

  const candidateLayers = validateClassKeyedRecord(
    json["candidate_layers_per_class"],
    "candidate_layers_per_class",
    (v, key) => checkNumberArray(v, `candidate_layers_per_class.${key}`),
  ) as Record<FoundationClassKey, number[]>;

  const covers = validateClassKeyedRecord(
    json["per_class_neuron_covers"],
    "per_class_neuron_covers",
    (v, key) => checkStringArray(v, `per_class_neuron_covers.${key}`),
  ) as Record<FoundationClassKey, string[]>;

  let rawRows: unknown = json["row_reports"];
  if (rawRows === undefined) {
    const evaluation = json["evaluation"];
    if (isPlainObject(evaluation) && Array.isArray(evaluation["row_reports"])) {
      rawRows = evaluation["row_reports"];
    }
  }
  if (!Array.isArray(rawRows)) {
    throw new Error('loadStage27FSnapshot: "row_reports" must be an array (top-level or under "evaluation")');
  }
  const baseProvenance = snapshotProvenance(json);
  const rowReports = rawRows.map((r, i) => loadRowReport(r, i, baseProvenance));

  return {
    mlp_intermediate_dim: mlpDim,
    candidate_layers_per_class: candidateLayers,
    per_class_neuron_covers: covers,
    row_reports: rowReports,
  };
}

export function coverEvidenceByClass(data: Stage27FData): Partial<Record<FoundationClassKey, CoverEvidence>> {
  const out: Partial<Record<FoundationClassKey, CoverEvidence>> = {};
  for (const row of data.row_reports) {
    if (out[row.target]) continue;
    out[row.target] = {
      target: row.target,
      candidate_layers: row.candidate_layers,
      neuron_cover: row.neuron_cover,
      ...(row.clean_margin !== undefined ? { clean_margin: row.clean_margin } : {}),
      ...(row.targeted_drop !== undefined ? { targeted_drop: row.targeted_drop } : {}),
      ...(row.pair_kind ? { pair_kind: row.pair_kind } : {}),
      ...(row.partner ? { partner: row.partner } : {}),
      ...(row.sample_id ? { sample_id: row.sample_id } : {}),
      confidence: row.confidence,
    };
  }
  for (const classKey of FOUNDATION_CLASS_KEYS) {
    if (out[classKey]) continue;
    const labels = data.per_class_neuron_covers[classKey];
    if (!labels) continue;
    out[classKey] = {
      target: classKey,
      candidate_layers: data.candidate_layers_per_class[classKey] ?? [],
      neuron_cover: labels,
      confidence: unavailableConfidence(`Stage 27F row_report missing for ${classKey}`, {
        source_stage: "Stage 27F",
        confidence_scope: "cover-level",
        formula: COVER_CONFIDENCE_FORMULA,
        target: classKey,
      }),
    };
  }
  return out;
}

export function coordsForClass(data: Stage27FData, classKey: FoundationClassKey): NeuronCoord[] {
  const labels = data.per_class_neuron_covers[classKey];
  if (!labels) {
    throw new Error(`coordsForClass: class key "${classKey}" not present in snapshot`);
  }
  return labels.map((s) => parseCoord(s));
}

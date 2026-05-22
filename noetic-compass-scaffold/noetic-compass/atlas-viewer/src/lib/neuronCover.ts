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

export interface RowReport {
  target: FoundationClassKey;
  candidate_layers: number[];
  neuron_cover: string[];
  clean_margin: number;
  targeted_drop: number;
}

export interface Stage27FData {
  mlp_intermediate_dim: number;
  candidate_layers_per_class: Record<FoundationClassKey, number[]>;
  per_class_neuron_covers: Record<FoundationClassKey, string[]>;
  row_reports: RowReport[];
}

const COORD_RE = /^L(\d+)N(\d+)$/;

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

function loadRowReport(raw: unknown, idx: number): RowReport {
  if (!isPlainObject(raw)) {
    throw new Error(`loadStage27FSnapshot: row_reports[${idx}] must be an object`);
  }
  const target = raw["target"];
  if (typeof target !== "string" || !isFoundationClassKey(target)) {
    throw new Error(`loadStage27FSnapshot: row_reports[${idx}].target invalid: ${String(target)}`);
  }
  checkNumberArray(raw["candidate_layers"], `row_reports[${idx}].candidate_layers`);
  checkStringArray(raw["neuron_cover"], `row_reports[${idx}].neuron_cover`);
  if (typeof raw["clean_margin"] !== "number" || !Number.isFinite(raw["clean_margin"])) {
    throw new Error(`loadStage27FSnapshot: row_reports[${idx}].clean_margin must be a finite number`);
  }
  if (typeof raw["targeted_drop"] !== "number" || !Number.isFinite(raw["targeted_drop"])) {
    throw new Error(`loadStage27FSnapshot: row_reports[${idx}].targeted_drop must be a finite number`);
  }
  return {
    target,
    candidate_layers: raw["candidate_layers"] as number[],
    neuron_cover: raw["neuron_cover"] as string[],
    clean_margin: raw["clean_margin"] as number,
    targeted_drop: raw["targeted_drop"] as number,
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
  const rowReports = rawRows.map((r, i) => loadRowReport(r, i));

  return {
    mlp_intermediate_dim: mlpDim,
    candidate_layers_per_class: candidateLayers,
    per_class_neuron_covers: covers,
    row_reports: rowReports,
  };
}

export function coordsForClass(data: Stage27FData, classKey: FoundationClassKey): NeuronCoord[] {
  const labels = data.per_class_neuron_covers[classKey];
  if (!labels) {
    throw new Error(`coordsForClass: class key "${classKey}" not present in snapshot`);
  }
  return labels.map((s) => parseCoord(s));
}

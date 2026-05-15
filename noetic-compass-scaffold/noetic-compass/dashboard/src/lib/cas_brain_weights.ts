/**
 * cas_brain_weights — typed loader for the downsampled CAS-Native v0.2
 * weight snapshot (`src/data/cas_brain_weights.json`, 2.56 MB).
 *
 * The JSON is produced by
 * `cas-native/scripts/extract_brain_map_weights.py` and stored at
 * schema_version `cas_brain_weights.v1`. The shape, contract-checked by
 * `cas_brain_weights.test.ts`, is:
 *
 *   layers: {
 *     "encoder.layers.3.domain_attn": {
 *       family: "encoder_attn",
 *       full_param_count: 1313280,
 *       sub_matrices: [
 *         { name, full_shape, downsampled_shape, grid, min, max, mean, std },
 *         ...
 *       ]
 *     },
 *     ...
 *   }
 *
 * The mock-flow library (`cas_brain_mock_flow.ts`) and the inline layer
 * graph inside `CASBrainMap.tsx` use a different naming convention for
 * layer ids (e.g. `enc_3_domain_attn`, `enc_final_norm`, `dec_2_self_attn`,
 * `register_film`, `dec_lm_head`, ...). `getSubMatricesForLayer` performs
 * the bridge so callers pass the lib id and receive the matching JSON
 * snapshot — or `[]` when no JSON key applies (the close-view renderer
 * then renders four placeholder grids per its own contract).
 *
 * Re-extraction: when the python script regenerates the JSON for a new
 * checkpoint, this loader needs no edits as long as the schema_version
 * stays `cas_brain_weights.v1`. Only the `extracted_at`, `checkpoint_*`,
 * `global_stats`, and per-layer `grid` values change.
 */
import weightsJson from '../data/cas_brain_weights.json';
import type { SubMatrixSnapshot as CloseViewSubMatrixSnapshot } from '../components/idea-atlas/CloseViewMatrixGrid';

// ── JSON-shape types (verbatim from the v1 schema) ───────────────────────

/** Raw per-sub-matrix entry as serialized by extract_brain_map_weights.py. */
export interface SubMatrixSnapshot {
  name: string;
  full_shape: number[];
  downsampled_shape: number[];
  grid: number[][];
  min: number;
  max: number;
  mean: number;
  std: number;
}

export interface LayerWeightSnapshot {
  family: string;
  full_param_count: number;
  sub_matrices: SubMatrixSnapshot[];
}

export interface CASBrainWeights {
  schema_version: string;
  model_checkpoint: string;
  checkpoint_id: string;
  checkpoint_sha256: string;
  extracted_at: string;
  downsample_grid: number;
  global_stats: {
    total_params: number;
    min_weight: number;
    max_weight: number;
    mean_weight: number;
    std_weight: number;
  };
  layers: Record<string, LayerWeightSnapshot>;
}

export const CAS_BRAIN_WEIGHTS = weightsJson as unknown as CASBrainWeights;

/**
 * True when extract_brain_map_weights.py took its fallback path (pod
 * checkpoint extraction failed) and emitted a deterministic synthetic
 * snapshot of the correct shape. The dashboard renders a yellow banner
 * in this case per `PHASE_2_LOD_DESIGN.md` Section 7.2.
 */
export const CAS_BRAIN_WEIGHTS_IS_SYNTHETIC =
  CAS_BRAIN_WEIGHTS.model_checkpoint === 'FALLBACK_SYNTHETIC';

/** First 8 hex chars of the checkpoint sha256, for the close-view info panel. */
export function getCheckpointSha256Prefix(len = 8): string {
  const full = CAS_BRAIN_WEIGHTS.checkpoint_sha256 ?? '';
  return full.slice(0, len);
}

// ── Layer-id mapping ─────────────────────────────────────────────────────

/**
 * Map a CAS Brain Map layer id (as used by cas_brain_mock_flow.ts and the
 * inline graph in CASBrainMap.tsx) to its key in the weights JSON.
 *
 * Returns `null` when no JSON key applies (e.g. positional encoding is
 * param-free; soft_prefix lives under a different path). The renderer
 * then falls back to four placeholder grids per Agent D's contract.
 */
function mapLayerIdToJsonKey(layerId: string): string | null {
  // Embedding chain.
  if (layerId === 'token_embedding') return 'encoder.token_embedding';
  if (layerId === 'cognitive_state_embedding') return 'encoder.cognitive_embedding';
  if (layerId === 'positional_encoding') return 'encoder.pos_encoding';

  // Per-encoder-block sub-modules: enc_<idx>_<name> -> encoder.layers.<idx>.<name>.
  const encBlock = /^enc_(\d+)_(.+)$/.exec(layerId);
  if (encBlock) {
    const idx = encBlock[1];
    const sub = encBlock[2];
    switch (sub) {
      case 'domain_attn':
        return `encoder.layers.${idx}.domain_attn`;
      case 'fractal_attn':
        return `encoder.layers.${idx}.fractal_attn`;
      case 'rpm_gate':
        return `encoder.layers.${idx}.rpm_gate`;
      case 'ffn':
        return `encoder.layers.${idx}.ffn`;
      default:
        return null;
    }
  }

  // Encoder tail.
  if (layerId === 'enc_final_norm') return 'encoder.final_norm';
  if (layerId === 'enc_lm_head') return 'lm_head';

  // Special branches. typed_fiber_decoder is the lib-side aggregate name
  // for the side-stack; the JSON splits the weights across generative_head
  // (the closest matching named module). Lacunarity is folded into the
  // same lib node — surfaced as the lacunarity_head snapshot when available.
  if (layerId === 'topos_reasoner') return 'topos_reasoner';
  if (layerId === 'inversion_detector') return 'inversion_detector';
  if (layerId === 'typed_fiber_decoder') return 'generative_head';

  // Decoder chain.
  if (layerId === 'dec_token_embedding') return 'decoder.token_embedding';
  if (layerId === 'dec_soft_prefix') return 'decoder.soft_prefix_proj';

  // Per-decoder-block sub-modules: dec_<idx>_<name> -> decoder.layers.<idx>.<name>.
  const decBlock = /^dec_(\d+)_(.+)$/.exec(layerId);
  if (decBlock) {
    const idx = decBlock[1];
    const sub = decBlock[2];
    switch (sub) {
      case 'self_attn':
        return `decoder.layers.${idx}.self_attn`;
      case 'cross_attn':
        return `decoder.layers.${idx}.cross_attn`;
      case 'ffn':
        return `decoder.layers.${idx}.ffn`;
      default:
        return null;
    }
  }

  // Decoder tail.
  if (layerId === 'register_film') return 'decoder.register_film';
  if (layerId === 'dec_final_norm') return 'decoder.final_norm';
  if (layerId === 'dec_lm_head') return 'decoder.lm_head';

  // output_stream and any unmapped id: no weights.
  return null;
}

// ── Snapshot adapter ─────────────────────────────────────────────────────

/**
 * Adapt a raw JSON sub-matrix into Agent D's CloseViewMatrixGrid shape.
 * The renderer expects camelCase keys and [number, number] tuples for the
 * downsampled shape; the JSON uses snake_case + bare number[] arrays.
 */
function adaptSnapshot(raw: SubMatrixSnapshot): CloseViewSubMatrixSnapshot {
  const ds = raw.downsampled_shape ?? [];
  const downsampledShape: [number, number] = [
    Number(ds[0] ?? raw.grid.length ?? 0),
    Number(ds[1] ?? raw.grid[0]?.length ?? 0),
  ];
  const full = raw.full_shape ?? [];
  let fullShape: [number, number] | [number];
  if (full.length >= 2) {
    fullShape = [Number(full[0]), Number(full[1])];
  } else if (full.length === 1) {
    fullShape = [Number(full[0])];
  } else {
    fullShape = downsampledShape;
  }
  return {
    name: raw.name,
    fullShape,
    downsampledShape,
    grid: raw.grid,
    min: raw.min,
    max: raw.max,
    mean: raw.mean,
    std: raw.std,
  };
}

/**
 * Pick the most pedagogically-useful sub-matrices for a layer's close view.
 * Attention layers want Q/K/V/O; FFN layers want the two main weight
 * matrices; embeddings want the token table; everything else gets the
 * first 1-4 weight-bearing entries.
 *
 * Limits to 4 grids max to keep the 2x2 close-view layout consistent.
 */
function pickDisplaySubMatrices(
  jsonKey: string,
  raw: SubMatrixSnapshot[],
): SubMatrixSnapshot[] {
  if (raw.length === 0) return [];

  const byName = new Map<string, SubMatrixSnapshot>();
  for (const sm of raw) byName.set(sm.name, sm);

  // Helper: collect snapshots by an ordered list of preferred names,
  // skipping misses; falls back to the first weight-bearing matrices.
  function preferred(names: ReadonlyArray<string>): SubMatrixSnapshot[] {
    const out: SubMatrixSnapshot[] = [];
    for (const n of names) {
      const sm = byName.get(n);
      if (sm) out.push(sm);
      if (out.length >= 4) break;
    }
    return out;
  }

  // Encoder attention (domain_attn / fractal_attn): Q/K/V/O.
  if (/\.domain_attn$/.test(jsonKey) || /\.fractal_attn$/.test(jsonKey)) {
    const picked = preferred(['q_proj.weight', 'k_proj.weight', 'v_proj.weight', 'O']);
    if (picked.length > 0) return picked;
  }

  // Decoder self/cross attention: Q/K/V/O.
  if (/\.self_attn$/.test(jsonKey) || /\.cross_attn$/.test(jsonKey)) {
    const picked = preferred(['Q', 'K', 'V', 'O']);
    if (picked.length > 0) return picked;
  }

  // FFN: up-proj (0.weight) and down-proj (3.weight).
  if (/\.ffn$/.test(jsonKey)) {
    const picked = preferred(['0.weight', '3.weight']);
    if (picked.length > 0) return picked;
  }

  // RPM gate: eta/epsilon main projections (skip biases).
  if (/\.rpm_gate$/.test(jsonKey)) {
    const picked = preferred([
      'gate_a0.gate_proj.weight',
      'gate_drive.gate_proj.weight',
      'gate_wisdom.gate_proj.weight',
      'gate_proficiency.gate_proj.weight',
    ]);
    if (picked.length > 0) return picked;
  }

  // Embeddings + lm_head: single weight matrix.
  if (
    jsonKey === 'encoder.token_embedding' ||
    jsonKey === 'decoder.token_embedding' ||
    jsonKey === 'decoder.pos_embedding' ||
    jsonKey === 'lm_head' ||
    jsonKey === 'decoder.lm_head'
  ) {
    const picked = preferred(['weight']);
    if (picked.length > 0) return picked;
  }

  // Cognitive embedding: 2-stage projection.
  if (jsonKey === 'encoder.cognitive_embedding') {
    const picked = preferred(['projection.0.weight', 'projection.2.weight']);
    if (picked.length > 0) return picked;
  }

  // Soft prefix: single projection.
  if (jsonKey === 'decoder.soft_prefix_proj') {
    const picked = preferred(['weight']);
    if (picked.length > 0) return picked;
  }

  // Register FiLM: gamma + beta.
  if (jsonKey === 'decoder.register_film') {
    const picked = preferred(['gamma', 'beta']);
    if (picked.length > 0) return picked;
  }

  // Topos / Inversion / Generative / Lacunarity: first weight-bearing entries.
  // Filter out bias-only entries (1D shape) so we surface real 2D grids first.
  const twoD = raw.filter((sm) => Array.isArray(sm.grid) && sm.grid.length > 1);
  if (twoD.length > 0) return twoD.slice(0, 4);

  // Last resort: whatever is there.
  return raw.slice(0, 4);
}

/**
 * Look up the display-ready sub-matrices for a layer id. Returns `[]` when
 * the layer has no matching JSON key — the close-view renderer then draws
 * placeholder grids and a "weights unavailable" sprite per its contract.
 */
export function getSubMatricesForLayer(
  layerId: string,
): CloseViewSubMatrixSnapshot[] {
  const key = mapLayerIdToJsonKey(layerId);
  if (!key) return [];
  const entry = CAS_BRAIN_WEIGHTS.layers[key];
  if (!entry || !Array.isArray(entry.sub_matrices)) return [];
  const picked = pickDisplaySubMatrices(key, entry.sub_matrices);
  return picked.map(adaptSnapshot);
}

/** Diagnostic: full layer entry by lib layer id (or null). */
export function getLayerWeightSnapshot(
  layerId: string,
): LayerWeightSnapshot | null {
  const key = mapLayerIdToJsonKey(layerId);
  if (!key) return null;
  return CAS_BRAIN_WEIGHTS.layers[key] ?? null;
}

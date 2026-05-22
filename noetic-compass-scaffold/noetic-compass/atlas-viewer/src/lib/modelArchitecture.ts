export const ARCH_FAMILIES = [
  'pythia',
  'olmo',
  'qwen',
  'llama',
  'mistral',
  'gemma',
  'phi',
  'gpt-neox',
  'unknown',
] as const;

export type ArchFamily = (typeof ARCH_FAMILIES)[number];

export interface ModelArchitecture {
  family: ArchFamily;
  n_layers: number;
  hidden_size: number;
  mlp_intermediate_dim: number;
  n_heads: number;
  total_params: number;
  validated: boolean;
}

export type LodClass = 'small' | 'medium' | 'large' | 'xl';

export type AtlasPhase = 'v0.0' | 'v0.1' | 'v0.2';

export const PYTHIA_160M_PRESET: ModelArchitecture = {
  family: 'pythia',
  n_layers: 12,
  hidden_size: 768,
  mlp_intermediate_dim: 3072,
  n_heads: 12,
  total_params: 162_000_000,
  validated: true,
};

export const KNOWN_PRESETS: Record<string, ModelArchitecture> = {
  'EleutherAI/pythia-160m': PYTHIA_160M_PRESET,
  'EleutherAI/pythia-1b': {
    family: 'pythia',
    n_layers: 16,
    hidden_size: 2048,
    mlp_intermediate_dim: 8192,
    n_heads: 8,
    total_params: 1_000_000_000,
    validated: true,
  },
  'EleutherAI/pythia-2.8b': {
    family: 'pythia',
    n_layers: 32,
    hidden_size: 2560,
    mlp_intermediate_dim: 10240,
    n_heads: 32,
    total_params: 2_800_000_000,
    validated: true,
  },
  'allenai/OLMo-1B': {
    family: 'olmo',
    n_layers: 16,
    hidden_size: 2048,
    mlp_intermediate_dim: 8192,
    n_heads: 16,
    total_params: 1_180_000_000,
    validated: true,
  },
  'Qwen/Qwen2.5-1.5B': {
    family: 'qwen',
    n_layers: 28,
    hidden_size: 1536,
    mlp_intermediate_dim: 8960,
    n_heads: 12,
    total_params: 1_540_000_000,
    validated: true,
  },
};

export function isValidatedArch(
  family: ArchFamily,
  phase: AtlasPhase = 'v0.0',
): boolean {
  if (phase === 'v0.0' || phase === 'v0.1') {
    return family === 'pythia';
  }
  return family === 'pythia' || family === 'olmo' || family === 'qwen';
}

/**
 * Parse a HuggingFace `config.json` payload into a ModelArchitecture.
 *
 * At v0.0/v0.1 this is intentionally a stub that always returns
 * PYTHIA_160M_PRESET regardless of input — the v0.0 cockpit is hardcoded
 * to Pythia-160M per Doc 2 §2 (v0.0 Demo cockpit) and Doc 1 §2
 * (architecture detection: "At v0.0, hardcoded to Pythia-160M values").
 *
 * The real config-walking logic lands at v0.2 when auto-scaling
 * NeuralNetScene is enabled per Doc 1 §2 and the architecture support
 * matrix in Doc 2 §7 expands. Until then, returning the preset preserves
 * the call-site shape (parse → ModelArchitecture) so downstream code
 * (NeuralNetScene, LOD selector, hover tooltip) can be written against
 * the final interface without branching on phase.
 */
export function parseHuggingFaceConfig(_json: unknown): ModelArchitecture {
  return PYTHIA_160M_PRESET;
}

export function archLodClass(arch: ModelArchitecture): LodClass {
  const p = arch.total_params;
  if (p < 500_000_000) return 'small';
  if (p < 3_000_000_000) return 'medium';
  if (p < 30_000_000_000) return 'large';
  return 'xl';
}

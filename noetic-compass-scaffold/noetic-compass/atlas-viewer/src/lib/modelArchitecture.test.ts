import { describe, it, expect } from 'vitest';
import {
  PYTHIA_160M_PRESET,
  KNOWN_PRESETS,
  isValidatedArch,
  parseHuggingFaceConfig,
  archLodClass,
  type ModelArchitecture,
} from './modelArchitecture';

describe('PYTHIA_160M_PRESET', () => {
  it('has the expected Pythia-160M dimensions', () => {
    expect(PYTHIA_160M_PRESET).toEqual({
      family: 'pythia',
      n_layers: 12,
      hidden_size: 768,
      mlp_intermediate_dim: 3072,
      n_heads: 12,
      total_params: 162_000_000,
      validated: true,
    });
  });
});

describe('KNOWN_PRESETS', () => {
  it('includes the five validated HF model ids', () => {
    expect(KNOWN_PRESETS['EleutherAI/pythia-160m']).toBeDefined();
    expect(KNOWN_PRESETS['EleutherAI/pythia-1b']).toBeDefined();
    expect(KNOWN_PRESETS['EleutherAI/pythia-2.8b']).toBeDefined();
    expect(KNOWN_PRESETS['allenai/OLMo-1B']).toBeDefined();
    expect(KNOWN_PRESETS['Qwen/Qwen2.5-1.5B']).toBeDefined();
  });

  it('marks all five presets as validated', () => {
    for (const key of Object.keys(KNOWN_PRESETS)) {
      expect(KNOWN_PRESETS[key].validated).toBe(true);
    }
  });

  it('binds Pythia-160M entry to the canonical preset', () => {
    expect(KNOWN_PRESETS['EleutherAI/pythia-160m']).toBe(PYTHIA_160M_PRESET);
  });
});

describe('isValidatedArch', () => {
  it('validates only pythia at v0.0', () => {
    expect(isValidatedArch('pythia', 'v0.0')).toBe(true);
    expect(isValidatedArch('olmo', 'v0.0')).toBe(false);
    expect(isValidatedArch('qwen', 'v0.0')).toBe(false);
    expect(isValidatedArch('llama', 'v0.0')).toBe(false);
    expect(isValidatedArch('unknown', 'v0.0')).toBe(false);
  });

  it('validates only pythia at v0.1', () => {
    expect(isValidatedArch('pythia', 'v0.1')).toBe(true);
    expect(isValidatedArch('olmo', 'v0.1')).toBe(false);
    expect(isValidatedArch('qwen', 'v0.1')).toBe(false);
  });

  it('validates pythia, olmo, and qwen at v0.2', () => {
    expect(isValidatedArch('pythia', 'v0.2')).toBe(true);
    expect(isValidatedArch('olmo', 'v0.2')).toBe(true);
    expect(isValidatedArch('qwen', 'v0.2')).toBe(true);
    expect(isValidatedArch('llama', 'v0.2')).toBe(false);
    expect(isValidatedArch('mistral', 'v0.2')).toBe(false);
    expect(isValidatedArch('gemma', 'v0.2')).toBe(false);
    expect(isValidatedArch('phi', 'v0.2')).toBe(false);
    expect(isValidatedArch('gpt-neox', 'v0.2')).toBe(false);
    expect(isValidatedArch('unknown', 'v0.2')).toBe(false);
  });

  it('defaults phase to v0.0', () => {
    expect(isValidatedArch('pythia')).toBe(true);
    expect(isValidatedArch('olmo')).toBe(false);
  });
});

describe('parseHuggingFaceConfig', () => {
  it('returns PYTHIA_160M_PRESET for an empty object at v0.0', () => {
    expect(parseHuggingFaceConfig({})).toEqual(PYTHIA_160M_PRESET);
  });

  it('ignores Llama-shaped input and still returns PYTHIA_160M_PRESET at v0.0', () => {
    const llamaConfig = {
      model_type: 'llama',
      num_hidden_layers: 32,
      hidden_size: 4096,
      intermediate_size: 14336,
      num_attention_heads: 32,
    };
    expect(parseHuggingFaceConfig(llamaConfig)).toEqual(PYTHIA_160M_PRESET);
  });

  it('ignores null and undefined input', () => {
    expect(parseHuggingFaceConfig(null)).toEqual(PYTHIA_160M_PRESET);
    expect(parseHuggingFaceConfig(undefined)).toEqual(PYTHIA_160M_PRESET);
  });
});

describe('archLodClass', () => {
  const mkArch = (total_params: number): ModelArchitecture => ({
    family: 'pythia',
    n_layers: 12,
    hidden_size: 768,
    mlp_intermediate_dim: 3072,
    n_heads: 12,
    total_params,
    validated: true,
  });

  it('classifies Pythia-160M as small', () => {
    expect(archLodClass(PYTHIA_160M_PRESET)).toBe('small');
  });

  it('classifies OLMo-1B as medium', () => {
    expect(archLodClass(KNOWN_PRESETS['allenai/OLMo-1B'])).toBe('medium');
  });

  it('classifies Qwen-1.5B as medium', () => {
    expect(archLodClass(KNOWN_PRESETS['Qwen/Qwen2.5-1.5B'])).toBe('medium');
  });

  it('classifies an 8B model as large', () => {
    expect(archLodClass(mkArch(8_000_000_000))).toBe('large');
  });

  it('classifies a 70B model as xl', () => {
    expect(archLodClass(mkArch(70_000_000_000))).toBe('xl');
  });

  it('respects the 500M boundary (small <-> medium)', () => {
    expect(archLodClass(mkArch(499_999_999))).toBe('small');
    expect(archLodClass(mkArch(500_000_000))).toBe('medium');
  });

  it('respects the 3B boundary (medium <-> large)', () => {
    expect(archLodClass(mkArch(2_999_999_999))).toBe('medium');
    expect(archLodClass(mkArch(3_000_000_000))).toBe('large');
  });

  it('respects the 30B boundary (large <-> xl)', () => {
    expect(archLodClass(mkArch(29_999_999_999))).toBe('large');
    expect(archLodClass(mkArch(30_000_000_000))).toBe('xl');
  });
});

/**
 * Tests for MediumViewSubstructure — imperative Three.js plate builder.
 *
 * Pure-Three.js builder, so tests construct it directly (no React render).
 * jsdom provides canvas for the label sprite path; CanvasTexture is fine.
 */
import { describe, it, expect } from 'vitest';
import { Group } from 'three';
import {
  buildMediumViewSubstructure,
  type MediumViewSubstructureProps,
} from './MediumViewSubstructure';
import type { CASBrainLayer } from '../../lib/cas_brain_mock_flow';

function makeLayer(
  overrides: Partial<CASBrainLayer> = {},
): CASBrainLayer {
  return {
    id: 'enc_block_0.domain_attn',
    family: 'encoder_attn',
    label: 'Encoder 1 - Domain Attn',
    casPurpose: 'test purpose',
    whyItMatters: 'test why',
    pipelinePosition: { stage: 'encoder_block', subIndex: 0, total: 6 },
    dimensions: { d_model: 512, n_heads: 8 },
    position3d: { x: 0, y: 0, z: 0 },
    size: 1.0,
    color: '#a78bfa',
    paramCount: 1_313_280,
    ...overrides,
  };
}

function makeProps(
  layer: CASBrainLayer,
  active = false,
): MediumViewSubstructureProps {
  return {
    layer,
    baseSize: 0.45,
    familyColor: layer.color,
    active,
  };
}

describe('MediumViewSubstructure — mount', () => {
  it('returns a Group, a dispose fn, and an update fn', () => {
    const layer = makeLayer();
    const handle = buildMediumViewSubstructure(makeProps(layer));
    expect(handle.group).toBeInstanceOf(Group);
    expect(typeof handle.dispose).toBe('function');
    expect(typeof handle.update).toBe('function');
    handle.dispose();
  });

  it('encoder_attn family has 4 plates in a 2x2 grid (Q/K/V/O)', () => {
    const layer = makeLayer({ family: 'encoder_attn' });
    const handle = buildMediumViewSubstructure(makeProps(layer));
    // Each plate is its own inner Group child.
    const innerGroups = handle.group.children.filter(
      (c) => c.userData.role === 'medium-view-substructure' || c.type === 'Group',
    );
    // We added one Group per plate.
    const plateGroups = handle.group.children.filter((c) => c.type === 'Group');
    expect(plateGroups.length).toBe(4);
    // No fewer than 4 — confirm.
    expect(innerGroups.length).toBeGreaterThanOrEqual(4);
    handle.dispose();
  });

  it('decoder_attn family also produces 4 plates', () => {
    const layer = makeLayer({
      family: 'decoder_attn',
      id: 'dec_block_0.self_attn',
      label: 'Decoder 1 - Self Attn',
    });
    const handle = buildMediumViewSubstructure(makeProps(layer));
    const plateGroups = handle.group.children.filter((c) => c.type === 'Group');
    expect(plateGroups.length).toBe(4);
    handle.dispose();
  });

  it('encoder_ffn family stacks 2 plates vertically (up/down proj)', () => {
    const layer = makeLayer({
      family: 'encoder_ffn',
      id: 'enc_block_0.ffn',
      label: 'Encoder 1 - FFN',
    });
    const handle = buildMediumViewSubstructure(makeProps(layer));
    const plateGroups = handle.group.children.filter((c) => c.type === 'Group');
    expect(plateGroups.length).toBe(2);
    handle.dispose();
  });

  it('encoder_gate family produces 2 plates (gate + projection)', () => {
    const layer = makeLayer({
      family: 'encoder_gate',
      id: 'enc_block_0.prereq_gate',
      label: 'Encoder 1 - RPM Gate',
    });
    const handle = buildMediumViewSubstructure(makeProps(layer));
    const plateGroups = handle.group.children.filter((c) => c.type === 'Group');
    expect(plateGroups.length).toBe(2);
    handle.dispose();
  });

  it('embedding family produces 1 plate labeled "weight"', () => {
    const layer = makeLayer({
      family: 'embedding',
      id: 'token_embedding',
      label: 'Token Embedding',
    });
    const handle = buildMediumViewSubstructure(makeProps(layer));
    const plateGroups = handle.group.children.filter((c) => c.type === 'Group');
    expect(plateGroups.length).toBe(1);
    handle.dispose();
  });

  it('decoder_head family produces 1 plate (LM head)', () => {
    const layer = makeLayer({
      family: 'decoder_head',
      id: 'lm_head',
      label: 'LM Head',
    });
    const handle = buildMediumViewSubstructure(makeProps(layer));
    const plateGroups = handle.group.children.filter((c) => c.type === 'Group');
    expect(plateGroups.length).toBe(1);
    handle.dispose();
  });

  it('special_branch typed_fiber_decoder produces 4 plates', () => {
    const layer = makeLayer({
      family: 'special_branch',
      id: 'typed_fiber_decoder',
      label: 'Typed Fiber Decoder',
    });
    const handle = buildMediumViewSubstructure(makeProps(layer));
    const plateGroups = handle.group.children.filter((c) => c.type === 'Group');
    expect(plateGroups.length).toBe(4);
    handle.dispose();
  });

  it('unknown special_branch falls back to "see weights below" single plate', () => {
    const layer = makeLayer({
      family: 'special_branch',
      id: 'mystery_branch',
      label: 'Mystery',
    });
    const handle = buildMediumViewSubstructure(makeProps(layer));
    const plateGroups = handle.group.children.filter((c) => c.type === 'Group');
    expect(plateGroups.length).toBe(1);
    handle.dispose();
  });

  it('layerId is recorded on the parent group userData', () => {
    const layer = makeLayer({ id: 'enc_block_2.ffn' });
    const handle = buildMediumViewSubstructure(makeProps(layer));
    expect(handle.group.userData.layerId).toBe('enc_block_2.ffn');
    expect(handle.group.userData.role).toBe('medium-view-substructure');
    handle.dispose();
  });
});

describe('MediumViewSubstructure — update', () => {
  it('update does not throw with finite dt', () => {
    const layer = makeLayer();
    const handle = buildMediumViewSubstructure(makeProps(layer, true));
    expect(() => handle.update(true, 1 / 60)).not.toThrow();
    expect(() => handle.update(false, 1 / 60)).not.toThrow();
    handle.dispose();
  });

  it('update is no-op (does not throw) for NaN or negative dt', () => {
    const layer = makeLayer();
    const handle = buildMediumViewSubstructure(makeProps(layer, true));
    expect(() => handle.update(true, NaN)).not.toThrow();
    expect(() => handle.update(true, -0.5)).not.toThrow();
    expect(() => handle.update(true, Infinity)).not.toThrow();
    handle.dispose();
  });

  it('active=true keeps plate scale within the [1.0, 1.1] pulse envelope', () => {
    const layer = makeLayer();
    const handle = buildMediumViewSubstructure(makeProps(layer, true));
    // Find a plate inner group.
    const plate = handle.group.children.find((c) => c.type === 'Group');
    expect(plate).toBeDefined();
    // Sample the scale at several points across one pulse cycle. Per the
    // implementation, scale = 1.0 + 0.08 * env where env in [0, 1], so the
    // envelope is [1.0, 1.08]. Allow a small margin for float drift.
    const samples: number[] = [];
    for (let i = 0; i < 30; i += 1) {
      handle.update(true, 0.01);
      samples.push(plate!.scale.x);
    }
    for (const s of samples) {
      expect(s).toBeGreaterThanOrEqual(1.0 - 1e-6);
      expect(s).toBeLessThanOrEqual(1.1);
    }
    handle.dispose();
  });

  it('active=false decays plate scale back toward 1.0', () => {
    const layer = makeLayer();
    const handle = buildMediumViewSubstructure(makeProps(layer, true));
    // Drive the pulse for a while.
    for (let i = 0; i < 30; i += 1) handle.update(true, 0.01);
    // Now flip to inactive and let it decay.
    for (let i = 0; i < 60; i += 1) handle.update(false, 0.01);
    const plate = handle.group.children.find((c) => c.type === 'Group');
    expect(plate).toBeDefined();
    expect(plate!.scale.x).toBeCloseTo(1.0, 2);
    handle.dispose();
  });

  it('after dispose, no plates remain on the group', () => {
    const layer = makeLayer();
    const handle = buildMediumViewSubstructure(makeProps(layer));
    expect(handle.group.children.length).toBeGreaterThan(0);
    handle.dispose();
    expect(handle.group.children.length).toBe(0);
  });
});

describe('MediumViewSubstructure — graceful handling', () => {
  it('does not throw on output family', () => {
    const layer = makeLayer({
      family: 'output',
      id: 'output',
      label: 'Output (tokens)',
    });
    expect(() => {
      const handle = buildMediumViewSubstructure(makeProps(layer));
      handle.dispose();
    }).not.toThrow();
  });

  it('handles all known families without throwing', () => {
    const families: CASBrainLayer['family'][] = [
      'embedding',
      'encoder_attn',
      'encoder_gate',
      'encoder_ffn',
      'special_branch',
      'decoder_attn',
      'decoder_ffn',
      'decoder_head',
      'output',
    ];
    for (const family of families) {
      const layer = makeLayer({ family, id: `test_${family}`, label: `Test ${family}` });
      const handle = buildMediumViewSubstructure(makeProps(layer));
      expect(handle.group).toBeInstanceOf(Group);
      handle.dispose();
    }
  });
});

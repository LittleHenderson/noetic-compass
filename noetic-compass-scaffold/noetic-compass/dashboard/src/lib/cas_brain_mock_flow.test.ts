/**
 * Sanity tests for `cas_brain_mock_flow.ts`.
 *
 * These are not exhaustive tests of the visualization — Agent A owns the
 * Three.js rendering. The goal here is to lock the data-shape contract
 * Agent A consumes: every layer has a unique id, every edge endpoint
 * exists, every flow frame references an existing layer, and frames
 * within a flow are sorted by tMs and bounded by durationMs.
 */

import { describe, expect, it } from 'vitest';

import {
  CAS_BRAIN_PALETTE,
  type CASBrainFlowCategory,
  type CASBrainLayerFamily,
  getMockFlows,
  getStaticEdges,
  getStaticLayers,
} from './cas_brain_mock_flow';

describe('cas_brain_mock_flow — static layers', () => {
  it('produces ~40-60 layers with unique ids', () => {
    const layers = getStaticLayers();
    // Spec target was ~42; the actual enumeration of model files
    // produces ~58 (3 embedding + 24 enc sub-modules + 1 enc_final_norm
    // + 4 special above + 2 special below + 3 decoder embedding
    // + 18 dec sub-modules + 1 dec_final_norm + 1 lm_head + 1 output).
    // Tolerate the range that respects both targets.
    expect(layers.length).toBeGreaterThanOrEqual(36);
    expect(layers.length).toBeLessThanOrEqual(62);

    const ids = new Set<string>();
    for (const layer of layers) {
      expect(ids.has(layer.id)).toBe(false);
      ids.add(layer.id);
    }
  });

  it('assigns a valid family and matching palette color to every layer', () => {
    const layers = getStaticLayers();
    const validFamilies: CASBrainLayerFamily[] = [
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
    for (const layer of layers) {
      expect(validFamilies).toContain(layer.family);
      expect(layer.color).toBe(CAS_BRAIN_PALETTE[layer.family]);
      expect(layer.size).toBeGreaterThanOrEqual(0.5);
      expect(layer.size).toBeLessThanOrEqual(1.5);
      // d_model is set to a meaningful positive value.
      expect(layer.dimensions.d_model).toBeGreaterThan(0);
      // Plain English purposes must be non-empty.
      expect(layer.casPurpose.length).toBeGreaterThan(20);
      expect(layer.whyItMatters.length).toBeGreaterThan(50);
    }
  });
});

describe('cas_brain_mock_flow — static edges', () => {
  it('produces ~60 edges, all referencing existing layers', () => {
    const layers = getStaticLayers();
    const edges = getStaticEdges();
    const layerIds = new Set(layers.map((l) => l.id));

    expect(edges.length).toBeGreaterThanOrEqual(50);
    expect(edges.length).toBeLessThanOrEqual(110);

    for (const edge of edges) {
      expect(layerIds.has(edge.from)).toBe(true);
      expect(layerIds.has(edge.to)).toBe(true);
      if (edge.weight !== undefined) {
        expect(edge.weight).toBeGreaterThanOrEqual(0);
        expect(edge.weight).toBeLessThanOrEqual(1);
      }
    }
  });
});

describe('cas_brain_mock_flow — mock flows', () => {
  it('produces exactly 5 flows, one per category, with frames sorted by tMs', () => {
    const flows = getMockFlows();
    expect(flows).toHaveLength(5);

    const expectedCategories: CASBrainFlowCategory[] = [
      'state_lookup',
      'recipe',
      'fractal',
      'inversion',
      'binary_composition',
    ];
    const seenCategories = new Set<CASBrainFlowCategory>();
    for (const flow of flows) {
      expect(expectedCategories).toContain(flow.category);
      seenCategories.add(flow.category);

      expect(flow.frames.length).toBeGreaterThan(0);
      expect(flow.durationMs).toBeGreaterThan(0);

      // Frames are sorted by tMs.
      for (let i = 1; i < flow.frames.length; i += 1) {
        expect(flow.frames[i].tMs).toBeGreaterThanOrEqual(flow.frames[i - 1].tMs);
      }

      // tMs is within [0, durationMs].
      for (const frame of flow.frames) {
        expect(frame.tMs).toBeGreaterThanOrEqual(0);
        expect(frame.tMs).toBeLessThanOrEqual(flow.durationMs);
        expect(frame.activationStrength).toBeGreaterThanOrEqual(0);
        expect(frame.activationStrength).toBeLessThanOrEqual(1);
      }
    }
    expect(seenCategories.size).toBe(5);
  });

  it('every frame references an existing layer id', () => {
    const layers = getStaticLayers();
    const layerIds = new Set(layers.map((l) => l.id));
    const flows = getMockFlows();
    for (const flow of flows) {
      for (const frame of flow.frames) {
        expect(layerIds.has(frame.activeLayerId)).toBe(true);
        if (frame.significantPoint) {
          expect(layerIds.has(frame.significantPoint.layerId)).toBe(true);
          expect(frame.significantPoint.label.length).toBeGreaterThan(0);
        }
      }
    }
  });

  it('every flow surfaces at least 4 significant points (Mode-7 visibility)', () => {
    const flows = getMockFlows();
    for (const flow of flows) {
      const count = flow.frames.filter((f) => f.significantPoint).length;
      expect(count).toBeGreaterThanOrEqual(4);
    }
  });

  it('flow categories include each of the 5 prompt types exactly once', () => {
    const flows = getMockFlows();
    const cats = flows.map((f) => f.category).sort();
    expect(cats).toEqual([
      'binary_composition',
      'fractal',
      'inversion',
      'recipe',
      'state_lookup',
    ]);
  });
});

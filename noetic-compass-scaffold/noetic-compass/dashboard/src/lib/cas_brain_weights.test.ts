/**
 * Phase 2a contract guard: cas_brain_weights.json conforms to the
 * cas_brain_weights.v1 schema that the close-view renderer (phase 2c)
 * consumes. The check is intentionally minimal — schema_version and a
 * couple of structural invariants — so any future regeneration of the
 * extraction artifact must keep the same shape.
 */

import { describe, it, expect } from "vitest";
import casBrainWeights from "../data/cas_brain_weights.json";

describe("cas_brain_weights.json contract", () => {
  it("matches schema_version cas_brain_weights.v1", () => {
    expect((casBrainWeights as { schema_version: string }).schema_version).toBe(
      "cas_brain_weights.v1",
    );
  });

  it("carries a downsample_grid of 32", () => {
    expect((casBrainWeights as { downsample_grid: number }).downsample_grid).toBe(32);
  });

  it("contains at least 30 layer entries", () => {
    const layers = (casBrainWeights as { layers: Record<string, unknown> }).layers;
    expect(Object.keys(layers).length).toBeGreaterThanOrEqual(30);
  });
});

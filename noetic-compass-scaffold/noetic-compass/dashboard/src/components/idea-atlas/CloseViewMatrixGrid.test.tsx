/**
 * Tests for CloseViewMatrixGrid — imperative Three.js builder for the
 * close-view 32x32 instanced sphere matrix grids.
 */
import { describe, it, expect } from 'vitest';
import { Group, InstancedMesh } from 'three';
import {
  buildCloseViewMatrixGrid,
  __testMakePlaceholderSnapshots,
  type CloseViewMatrixGridProps,
  type SubMatrixSnapshot,
} from './CloseViewMatrixGrid';
import type { CASBrainLayer } from '../../lib/cas_brain_mock_flow';

function makeLayer(): CASBrainLayer {
  return {
    id: 'enc_block_0.domain_attn',
    family: 'encoder_attn',
    label: 'Encoder 1 - Domain Attn',
    casPurpose: 'test',
    whyItMatters: 'test',
    pipelinePosition: { stage: 'encoder_block', subIndex: 0, total: 6 },
    dimensions: { d_model: 512, n_heads: 8 },
    position3d: { x: 0, y: 0, z: 0 },
    size: 1.0,
    color: '#a78bfa',
    paramCount: 1_313_280,
  };
}

function makeGrid(rows = 32, cols = 32): number[][] {
  const grid: number[][] = [];
  for (let r = 0; r < rows; r += 1) {
    const row: number[] = [];
    for (let c = 0; c < cols; c += 1) {
      row.push(Math.sin(r * 0.3 + c * 0.7));
    }
    grid.push(row);
  }
  return grid;
}

function makeSnapshot(name: string): SubMatrixSnapshot {
  return {
    name,
    fullShape: [512, 512],
    downsampledShape: [32, 32],
    grid: makeGrid(),
    min: -1.0,
    max: 1.0,
    mean: 0.0,
    std: 0.5,
  };
}

function makeProps(
  active = false,
  subMatrices?: SubMatrixSnapshot[],
): CloseViewMatrixGridProps {
  return {
    layer: makeLayer(),
    subMatrices,
    active,
  };
}

describe('CloseViewMatrixGrid — mount', () => {
  it('returns a Group, dispose fn, and update fn', () => {
    const handle = buildCloseViewMatrixGrid(
      makeProps(false, [makeSnapshot('Q'), makeSnapshot('K'), makeSnapshot('V'), makeSnapshot('O')]),
    );
    expect(handle.group).toBeInstanceOf(Group);
    expect(typeof handle.dispose).toBe('function');
    expect(typeof handle.update).toBe('function');
    handle.dispose();
  });

  it('builds 4 matrix sub-groups for a 4-snapshot attention layer', () => {
    const snaps = [makeSnapshot('Q'), makeSnapshot('K'), makeSnapshot('V'), makeSnapshot('O')];
    const handle = buildCloseViewMatrixGrid(makeProps(false, snaps));
    // Top-level children are matrix groups + possibly a warning sprite.
    // Filter for groups whose userData.role === 'close-view-matrix'.
    const matrixGroups = handle.group.children.filter(
      (c) => (c.userData as { role?: string }).role === 'close-view-matrix',
    );
    expect(matrixGroups.length).toBe(4);
    handle.dispose();
  });

  it('builds 2 matrix sub-groups for a 2-snapshot FFN layer', () => {
    const snaps = [makeSnapshot('up-proj'), makeSnapshot('down-proj')];
    const handle = buildCloseViewMatrixGrid(makeProps(false, snaps));
    const matrixGroups = handle.group.children.filter(
      (c) => (c.userData as { role?: string }).role === 'close-view-matrix',
    );
    expect(matrixGroups.length).toBe(2);
    handle.dispose();
  });

  it('builds 1 matrix for a 1-snapshot embedding layer', () => {
    const snaps = [makeSnapshot('weight')];
    const handle = buildCloseViewMatrixGrid(makeProps(false, snaps));
    const matrixGroups = handle.group.children.filter(
      (c) => (c.userData as { role?: string }).role === 'close-view-matrix',
    );
    expect(matrixGroups.length).toBe(1);
    handle.dispose();
  });

  it('records the layer id on the parent group userData', () => {
    const handle = buildCloseViewMatrixGrid(makeProps(false, [makeSnapshot('Q')]));
    expect(handle.group.userData.layerId).toBe('enc_block_0.domain_attn');
    expect(handle.group.userData.role).toBe('close-view-matrix-grid');
    handle.dispose();
  });

  it('each matrix contains exactly one 32x32 InstancedMesh (1024 instances)', () => {
    const handle = buildCloseViewMatrixGrid(
      makeProps(false, [makeSnapshot('Q')]),
    );
    const matrixGroup = handle.group.children.find(
      (c) => (c.userData as { role?: string }).role === 'close-view-matrix',
    );
    expect(matrixGroup).toBeDefined();
    // Find the matrix grid InstancedMesh (role: 'matrix-grid').
    const gridMesh = matrixGroup!.children.find(
      (c) =>
        c instanceof InstancedMesh &&
        (c.userData as { role?: string }).role === 'matrix-grid',
    ) as InstancedMesh | undefined;
    expect(gridMesh).toBeDefined();
    expect(gridMesh!.count).toBe(32 * 32);
    handle.dispose();
  });
});

describe('CloseViewMatrixGrid — placeholder mode', () => {
  it('renders 4 placeholder matrices when subMatrices is undefined', () => {
    const handle = buildCloseViewMatrixGrid(makeProps(false, undefined));
    const matrixGroups = handle.group.children.filter(
      (c) => (c.userData as { role?: string }).role === 'close-view-matrix',
    );
    expect(matrixGroups.length).toBe(4);
    handle.dispose();
  });

  it('renders 4 placeholder matrices when subMatrices is empty array', () => {
    const handle = buildCloseViewMatrixGrid(makeProps(false, []));
    const matrixGroups = handle.group.children.filter(
      (c) => (c.userData as { role?: string }).role === 'close-view-matrix',
    );
    expect(matrixGroups.length).toBe(4);
    handle.dispose();
  });

  it('adds a warning banner sprite in placeholder mode', () => {
    const handle = buildCloseViewMatrixGrid(makeProps(false, undefined));
    // The warning sprite is a Sprite type (not Group). Find it.
    const sprites = handle.group.children.filter((c) => c.type === 'Sprite');
    expect(sprites.length).toBeGreaterThanOrEqual(1);
    handle.dispose();
  });

  it('does NOT add a warning banner sprite when real data is present', () => {
    const handle = buildCloseViewMatrixGrid(
      makeProps(false, [makeSnapshot('Q'), makeSnapshot('K')]),
    );
    // No top-level Sprite for warning. (Per-matrix label sprites live
    // inside matrix sub-groups, not at the top level.)
    const topSprites = handle.group.children.filter((c) => c.type === 'Sprite');
    expect(topSprites.length).toBe(0);
    handle.dispose();
  });

  it('__testMakePlaceholderSnapshots returns 4 named snapshots Q/K/V/O', () => {
    const snaps = __testMakePlaceholderSnapshots();
    expect(snaps.length).toBe(4);
    expect(snaps.map((s) => s.name)).toEqual(['Q', 'K', 'V', 'O']);
    for (const s of snaps) {
      expect(s.grid.length).toBe(32);
      expect(s.grid[0].length).toBe(32);
    }
  });
});

describe('CloseViewMatrixGrid — update', () => {
  it('update is safe with finite dt', () => {
    const handle = buildCloseViewMatrixGrid(
      makeProps(true, [makeSnapshot('Q')]),
    );
    expect(() => handle.update(1 / 60, true)).not.toThrow();
    expect(() => handle.update(1 / 60, false)).not.toThrow();
    handle.dispose();
  });

  it('update is safe with NaN / negative / Infinity dt', () => {
    const handle = buildCloseViewMatrixGrid(
      makeProps(true, [makeSnapshot('Q')]),
    );
    expect(() => handle.update(NaN, true)).not.toThrow();
    expect(() => handle.update(-1, true)).not.toThrow();
    expect(() => handle.update(Infinity, true)).not.toThrow();
    handle.dispose();
  });

  it('cycles input/output opacity when active=true', () => {
    const snaps = [makeSnapshot('Q')];
    const handle = buildCloseViewMatrixGrid(makeProps(true, snaps));
    // Advance ~0.2s (within phase 1: input slide).
    for (let i = 0; i < 20; i += 1) handle.update(0.01, true);
    const matrixGroup = handle.group.children.find(
      (c) => (c.userData as { role?: string }).role === 'close-view-matrix',
    );
    expect(matrixGroup).toBeDefined();
    const inputDots = matrixGroup!.children.find(
      (c) => (c.userData as { role?: string }).role === 'input-vector',
    ) as InstancedMesh | undefined;
    expect(inputDots).toBeDefined();
    // Input opacity should have risen above ~0 during phase 1.
    const mat = inputDots!.material as { opacity: number };
    expect(mat.opacity).toBeGreaterThan(0);
    handle.dispose();
  });

  it('decays input/output opacity when active flips to false', () => {
    const snaps = [makeSnapshot('Q')];
    const handle = buildCloseViewMatrixGrid(makeProps(true, snaps));
    // Drive into phase 1 first.
    for (let i = 0; i < 30; i += 1) handle.update(0.01, true);
    // Now deactivate.
    for (let i = 0; i < 30; i += 1) handle.update(0.01, false);
    const matrixGroup = handle.group.children.find(
      (c) => (c.userData as { role?: string }).role === 'close-view-matrix',
    );
    const inputDots = matrixGroup!.children.find(
      (c) => (c.userData as { role?: string }).role === 'input-vector',
    ) as InstancedMesh | undefined;
    const mat = inputDots!.material as { opacity: number };
    // After ~30 frames of decay (0.85^30 ~ 0.008), opacity should be near 0.
    expect(mat.opacity).toBeLessThan(0.05);
    handle.dispose();
  });

  it('after dispose, all matrix groups removed', () => {
    const handle = buildCloseViewMatrixGrid(
      makeProps(false, [makeSnapshot('Q'), makeSnapshot('K')]),
    );
    expect(handle.group.children.length).toBeGreaterThan(0);
    handle.dispose();
    const matrixGroups = handle.group.children.filter(
      (c) => (c.userData as { role?: string }).role === 'close-view-matrix',
    );
    expect(matrixGroups.length).toBe(0);
  });
});

describe('CloseViewMatrixGrid — robustness', () => {
  it('handles a snapshot with degenerate min===max range (uniform values)', () => {
    const snap: SubMatrixSnapshot = {
      name: 'uniform',
      fullShape: [512, 512],
      downsampledShape: [32, 32],
      grid: Array.from({ length: 32 }, () => Array.from({ length: 32 }, () => 0.5)),
      min: 0.5,
      max: 0.5,
      mean: 0.5,
      std: 0,
    };
    expect(() => {
      const handle = buildCloseViewMatrixGrid(makeProps(false, [snap]));
      handle.dispose();
    }).not.toThrow();
  });

  it('handles a snapshot with NaN cells gracefully', () => {
    const grid = makeGrid();
    grid[5][7] = NaN;
    const snap: SubMatrixSnapshot = {
      name: 'with-nan',
      fullShape: [512, 512],
      downsampledShape: [32, 32],
      grid,
      min: -1,
      max: 1,
      mean: 0,
      std: 0.5,
    };
    expect(() => {
      const handle = buildCloseViewMatrixGrid(makeProps(false, [snap]));
      handle.dispose();
    }).not.toThrow();
  });
});

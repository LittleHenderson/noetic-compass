/**
 * CloseViewMatrixGrid — imperative Three.js builder for a layer's
 * "close-view" matrix grids (LOD level 2).
 *
 * For each sub-matrix in the provided snapshots, renders a 32x32
 * instanced sphere grid colored per-sphere by a normalized
 * blue->red palette. When `active` is true, runs a four-phase
 * matrix-vector animation per matrix:
 *   1) input vector slides in from the left;
 *   2) columns fire left-to-right (emissive boost) showing the dot product;
 *   3) output vector emerges from the right;
 *   4) brief pause, then the next matrix in the chain.
 *
 * For 4-matrix attention layers, the chain runs Q -> K -> V -> O
 * sequentially, ~1.5s each (6s total).
 *
 * When `subMatrices` is empty or undefined (weight data not loaded),
 * renders four placeholder 32x32 grids with a grey palette and a
 * warning banner sprite above them.
 *
 * Pure imperative Three.js — no DOM, no React. Caller (CASBrainMap)
 * attaches `group` to a THREE.LOD and ticks `update(dt, active)` each
 * frame; calls `dispose()` on unmount.
 */
import {
  CanvasTexture,
  Color,
  Group,
  InstancedMesh,
  Matrix4,
  MeshBasicMaterial,
  Object3D,
  SphereGeometry,
  Sprite,
  SpriteMaterial,
  type Material,
} from 'three';
import type { CASBrainLayer } from '../../lib/cas_brain_mock_flow';

// ── Public types ─────────────────────────────────────────────────────────

export interface SubMatrixSnapshot {
  name: string;
  fullShape: [number, number] | [number];
  /** Should be [32, 32] for v1 (or [1, N] for 1D). */
  downsampledShape: [number, number];
  /** 32 rows of 32 floats. (Or 1 row of N for 1D.) */
  grid: number[][];
  min: number;
  max: number;
  mean: number;
  std: number;
}

export interface CloseViewMatrixGridProps {
  layer: CASBrainLayer;
  /** Empty / undefined => placeholder mode. */
  subMatrices?: SubMatrixSnapshot[];
  active: boolean;
}

export interface CloseViewMatrixGridHandle {
  group: Group;
  dispose: () => void;
  update: (dt: number, active: boolean) => void;
}

// ── Constants ────────────────────────────────────────────────────────────

const GRID = 32; // 32x32
const INSTANCES_PER_GRID = GRID * GRID;
const SPHERE_RADIUS = 0.04;
const CELL_SPACING = 0.10;
/** Side length of one 32x32 grid in world units. */
const GRID_SPAN = (GRID - 1) * CELL_SPACING;

// One full cycle (input slide + column fire + output emerge + pause).
const PHASE_INPUT_MS = 300;
const PHASE_FIRE_MS = 600;
const PHASE_OUTPUT_MS = 300;
const PHASE_PAUSE_MS = 300;
const CYCLE_MS = PHASE_INPUT_MS + PHASE_FIRE_MS + PHASE_OUTPUT_MS + PHASE_PAUSE_MS;

// Diverging palette anchors.
const COLD = new Color('#3b82f6');   // blue
const NEUTRAL = new Color('#64748b'); // slate
const HOT = new Color('#ef4444');     // red

// ── Color helpers ────────────────────────────────────────────────────────

/**
 * Map a normalized value t in [0, 1] to a diverging blue->slate->red color.
 * t=0 -> COLD, t=0.5 -> NEUTRAL, t=1 -> HOT.
 */
function colorForValue(t: number, out: Color): Color {
  const clamped = Math.max(0, Math.min(1, t));
  if (clamped < 0.5) {
    out.copy(COLD).lerp(NEUTRAL, clamped * 2);
  } else {
    out.copy(NEUTRAL).lerp(HOT, (clamped - 0.5) * 2);
  }
  return out;
}

/**
 * Normalize a value within a snapshot's [min, max] range. Falls back to 0.5
 * when the range is zero (uniform snapshot).
 */
function normalize(value: number, min: number, max: number): number {
  const span = max - min;
  if (!Number.isFinite(span) || Math.abs(span) < 1e-12) return 0.5;
  return (value - min) / span;
}

// ── Placeholder mode ─────────────────────────────────────────────────────

function makeWarningSprite(): { sprite: Sprite; texture: CanvasTexture; material: SpriteMaterial } | null {
  if (typeof document === 'undefined') return null;
  const canvas = document.createElement('canvas');
  const W = 512;
  const H = 96;
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext('2d');
  if (ctx) {
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = 'rgba(15, 23, 42, 0.92)';
    ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = '#fbbf24';
    ctx.lineWidth = 3;
    ctx.strokeRect(2, 2, W - 4, H - 4);
    ctx.fillStyle = '#fbbf24';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.font = 'bold 28px ui-sans-serif, system-ui, sans-serif';
    ctx.fillText('Real weight data unavailable.', W / 2, 40);
    ctx.fillStyle = '#cbd5e1';
    ctx.font = '20px ui-sans-serif, system-ui, sans-serif';
    ctx.fillText('Showing placeholder.', W / 2, 72);
  }
  const texture = new CanvasTexture(canvas);
  texture.needsUpdate = true;
  const material = new SpriteMaterial({
    map: texture,
    transparent: true,
    depthWrite: false,
    opacity: 0.95,
  });
  const sprite = new Sprite(material);
  sprite.scale.set(4.0, 0.75, 1);
  return { sprite, texture, material };
}

function makeLabelSprite(name: string, sub: string): { sprite: Sprite; texture: CanvasTexture; material: SpriteMaterial } | null {
  if (typeof document === 'undefined') return null;
  const canvas = document.createElement('canvas');
  const W = 256;
  const H = 96;
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext('2d');
  if (ctx) {
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = 'rgba(2, 6, 23, 0.72)';
    ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = '#e2e8f0';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.font = 'bold 28px ui-monospace, SFMono-Regular, monospace';
    ctx.fillText(name, W / 2, 32);
    if (sub) {
      ctx.fillStyle = '#94a3b8';
      ctx.font = '18px ui-monospace, SFMono-Regular, monospace';
      ctx.fillText(sub, W / 2, 66);
    }
  }
  const texture = new CanvasTexture(canvas);
  texture.needsUpdate = true;
  const material = new SpriteMaterial({
    map: texture,
    transparent: true,
    depthWrite: false,
    opacity: 0.95,
  });
  const sprite = new Sprite(material);
  sprite.scale.set(2.0, 0.75, 1);
  return { sprite, texture, material };
}

function makePlaceholderGrid(): number[][] {
  const grid: number[][] = [];
  for (let r = 0; r < GRID; r += 1) {
    const row: number[] = [];
    for (let c = 0; c < GRID; c += 1) {
      // Use a subtle deterministic pattern so placeholder rendering is
      // visually non-uniform but obviously synthetic.
      row.push(0.5 + 0.1 * Math.sin((r + c) * 0.4));
    }
    grid.push(row);
  }
  return grid;
}

function makePlaceholderSnapshots(): SubMatrixSnapshot[] {
  const names = ['Q', 'K', 'V', 'O'];
  return names.map((name) => ({
    name,
    fullShape: [512, 512] as [number, number],
    downsampledShape: [GRID, GRID],
    grid: makePlaceholderGrid(),
    min: 0,
    max: 1,
    mean: 0.5,
    std: 0.05,
  }));
}

// ── Single matrix instance ──────────────────────────────────────────────

interface MatrixBundle {
  /** Top-level group containing the instanced grid + I/O vectors + label. */
  matrixGroup: Group;
  instanced: InstancedMesh;
  sphereGeom: SphereGeometry;
  sphereMat: MeshBasicMaterial;
  /** Base color per instance (32*32 entries). Used to restore after fire boost. */
  baseColors: Float32Array; // r,g,b triplets, length = N*3
  /** Per-instance "emissive boost" current value in [0, 1]. */
  boost: Float32Array;
  /** Input vector dots (length GRID). */
  inputDots: InstancedMesh | null;
  inputGeom: SphereGeometry | null;
  inputMat: MeshBasicMaterial | null;
  outputDots: InstancedMesh | null;
  outputGeom: SphereGeometry | null;
  outputMat: MeshBasicMaterial | null;
  label: Sprite | null;
  labelMat: SpriteMaterial | null;
  labelTex: CanvasTexture | null;
  /** Original snapshot kept so update() can re-derive base colors if needed. */
  snapshot: SubMatrixSnapshot;
  /** Whether snapshot data is real (false => placeholder). */
  isPlaceholder: boolean;
}

/**
 * Build one 32x32 instanced sphere grid for a single sub-matrix.
 * Returns a bundle the caller assembles into the top-level group.
 */
function buildMatrix(
  snapshot: SubMatrixSnapshot,
  isPlaceholder: boolean,
): MatrixBundle {
  const matrixGroup = new Group();
  matrixGroup.userData = { role: 'close-view-matrix', name: snapshot.name };

  const sphereGeom = new SphereGeometry(SPHERE_RADIUS, 8, 6);
  // Use vertex-color-aware material (each instance gets its own color via
  // setColorAt + InstancedMesh.instanceColor).
  const sphereMat = new MeshBasicMaterial({
    color: 0xffffff,
    transparent: true,
    opacity: 0.95,
  });
  const instanced = new InstancedMesh(sphereGeom, sphereMat, INSTANCES_PER_GRID);
  instanced.userData = { role: 'matrix-grid', name: snapshot.name };
  // Cluster-anchor at (0, 0, 0) — caller positions the matrixGroup.

  const baseColors = new Float32Array(INSTANCES_PER_GRID * 3);
  const boost = new Float32Array(INSTANCES_PER_GRID);

  // Set instance transforms + colors.
  const m = new Matrix4();
  const obj = new Object3D();
  const c = new Color();
  const halfSpan = GRID_SPAN / 2;

  // grid may have fewer than 32 rows (1D matrix shown as 1xN).
  const rows = snapshot.grid.length;
  for (let r = 0; r < GRID; r += 1) {
    for (let col = 0; col < GRID; col += 1) {
      const idx = r * GRID + col;
      // X = col, Y = -row (so row 0 is at the top), Z = 0.
      obj.position.set(
        col * CELL_SPACING - halfSpan,
        halfSpan - r * CELL_SPACING,
        0,
      );
      obj.scale.set(1, 1, 1);
      obj.rotation.set(0, 0, 0);
      obj.updateMatrix();
      m.copy(obj.matrix);
      instanced.setMatrixAt(idx, m);

      // Color: fetch raw value, normalize per-matrix, then map.
      let raw: number;
      if (rows === 0) {
        raw = (snapshot.min + snapshot.max) / 2;
      } else {
        const rowArr = snapshot.grid[Math.min(r, rows - 1)];
        const rawCol = rowArr ? rowArr[Math.min(col, rowArr.length - 1)] : snapshot.mean;
        raw = Number.isFinite(rawCol) ? rawCol : snapshot.mean;
      }
      const t = normalize(raw, snapshot.min, snapshot.max);
      colorForValue(t, c);
      instanced.setColorAt(idx, c);
      baseColors[idx * 3 + 0] = c.r;
      baseColors[idx * 3 + 1] = c.g;
      baseColors[idx * 3 + 2] = c.b;
    }
  }

  instanced.instanceMatrix.needsUpdate = true;
  if (instanced.instanceColor) {
    instanced.instanceColor.needsUpdate = true;
  }
  matrixGroup.add(instanced);

  // Input vector (left of the grid). 32 spheres in a vertical column.
  const inputGeom = new SphereGeometry(SPHERE_RADIUS * 1.4, 8, 6);
  const inputMat = new MeshBasicMaterial({
    color: 0xfde68a,
    transparent: true,
    opacity: 0.0, // start invisible; phase 1 fades in
  });
  const inputDots = new InstancedMesh(inputGeom, inputMat, GRID);
  inputDots.userData = { role: 'input-vector', name: snapshot.name };
  for (let r = 0; r < GRID; r += 1) {
    obj.position.set(-halfSpan - 0.5, halfSpan - r * CELL_SPACING, 0);
    obj.updateMatrix();
    m.copy(obj.matrix);
    inputDots.setMatrixAt(r, m);
  }
  inputDots.instanceMatrix.needsUpdate = true;
  matrixGroup.add(inputDots);

  // Output vector (right of the grid). 32 spheres.
  const outputGeom = new SphereGeometry(SPHERE_RADIUS * 1.4, 8, 6);
  const outputMat = new MeshBasicMaterial({
    color: 0xa7f3d0,
    transparent: true,
    opacity: 0.0,
  });
  const outputDots = new InstancedMesh(outputGeom, outputMat, GRID);
  outputDots.userData = { role: 'output-vector', name: snapshot.name };
  for (let r = 0; r < GRID; r += 1) {
    obj.position.set(halfSpan + 0.5, halfSpan - r * CELL_SPACING, 0);
    obj.updateMatrix();
    m.copy(obj.matrix);
    outputDots.setMatrixAt(r, m);
  }
  outputDots.instanceMatrix.needsUpdate = true;
  matrixGroup.add(outputDots);

  // Label sprite above the matrix.
  const shapeStr =
    snapshot.fullShape.length === 2
      ? `${snapshot.fullShape[0]} x ${snapshot.fullShape[1]}`
      : `${snapshot.fullShape[0]}`;
  const labelRes = makeLabelSprite(snapshot.name, shapeStr);
  let label: Sprite | null = null;
  let labelMat: SpriteMaterial | null = null;
  let labelTex: CanvasTexture | null = null;
  if (labelRes) {
    label = labelRes.sprite;
    labelMat = labelRes.material;
    labelTex = labelRes.texture;
    label.position.set(0, halfSpan + 0.5, 0);
    matrixGroup.add(label);
  }

  return {
    matrixGroup,
    instanced,
    sphereGeom,
    sphereMat,
    baseColors,
    boost,
    inputDots,
    inputGeom,
    inputMat,
    outputDots,
    outputGeom,
    outputMat,
    label,
    labelMat,
    labelTex,
    snapshot,
    isPlaceholder,
  };
}

// ── Layout ───────────────────────────────────────────────────────────────

/**
 * Position N matrix groups inside the parent group. Returns the (x, y)
 * for each matrix slot.
 */
function layoutSlots(n: number): Array<{ x: number; y: number }> {
  if (n <= 0) return [];
  const gap = GRID_SPAN + 1.6;
  if (n === 1) return [{ x: 0, y: 0 }];
  if (n === 2) {
    return [
      { x: -gap / 2, y: 0 },
      { x: gap / 2, y: 0 },
    ];
  }
  // 2x2 grid for 3-4 matrices.
  const positions: Array<{ x: number; y: number }> = [
    { x: -gap / 2, y: gap / 2 },
    { x: gap / 2, y: gap / 2 },
    { x: -gap / 2, y: -gap / 2 },
    { x: gap / 2, y: -gap / 2 },
  ];
  return positions.slice(0, n);
}

// ── Builder ──────────────────────────────────────────────────────────────

export function buildCloseViewMatrixGrid(
  props: CloseViewMatrixGridProps,
): CloseViewMatrixGridHandle {
  const { layer, subMatrices, active: initialActive } = props;

  const group = new Group();
  group.userData = {
    role: 'close-view-matrix-grid',
    layerId: layer.id,
  };

  const haveRealData =
    Array.isArray(subMatrices) && subMatrices.length > 0;
  const effectiveSnapshots: SubMatrixSnapshot[] = haveRealData
    ? (subMatrices as SubMatrixSnapshot[])
    : makePlaceholderSnapshots();
  const isPlaceholder = !haveRealData;

  const bundles: MatrixBundle[] = [];
  const slots = layoutSlots(effectiveSnapshots.length);
  for (let i = 0; i < effectiveSnapshots.length; i += 1) {
    const bundle = buildMatrix(effectiveSnapshots[i], isPlaceholder);
    const slot = slots[i];
    bundle.matrixGroup.position.set(slot.x, slot.y, 0);
    group.add(bundle.matrixGroup);
    bundles.push(bundle);
  }

  // Warning banner when in placeholder mode.
  let warning: Sprite | null = null;
  let warningMat: SpriteMaterial | null = null;
  let warningTex: CanvasTexture | null = null;
  if (isPlaceholder) {
    const res = makeWarningSprite();
    if (res) {
      warning = res.sprite;
      warningMat = res.material;
      warningTex = res.texture;
      // Above the whole 2x2 grid.
      warning.position.set(0, GRID_SPAN + 2.0, 0);
      group.add(warning);
    }
  }

  // ── Animation state ────────────────────────────────────────────────
  let timeMs = 0;
  let currentMatrixIdx = 0;
  let currentlyActive = initialActive;
  // Reused scratch objects to avoid GC churn.
  const scratchColor = new Color();
  const scratchInstanceColor = new Color();

  // Per-matrix chain duration is CYCLE_MS each; total chain length is
  // bundles.length * CYCLE_MS.
  function update(dt: number, active: boolean): void {
    currentlyActive = active;
    if (!Number.isFinite(dt) || dt < 0) return;
    if (!currentlyActive) {
      // Decay all boosts + hide I/O vectors when inactive.
      let anyChanged = false;
      for (const b of bundles) {
        for (let i = 0; i < b.boost.length; i += 1) {
          if (b.boost[i] > 0.001) {
            b.boost[i] *= 0.85;
            anyChanged = true;
          } else {
            b.boost[i] = 0;
          }
        }
        if (anyChanged) {
          applyBoostsToInstancedColors(b);
        }
        if (b.inputMat && b.inputMat.opacity > 0.001) {
          b.inputMat.opacity *= 0.85;
        }
        if (b.outputMat && b.outputMat.opacity > 0.001) {
          b.outputMat.opacity *= 0.85;
        }
      }
      return;
    }

    // Advance global time and figure out which matrix in the chain we're on
    // and where in its CYCLE_MS we are.
    timeMs += dt * 1000;
    const chainDur = CYCLE_MS * Math.max(1, bundles.length);
    const tInChain = timeMs % chainDur;
    const newIdx = Math.min(bundles.length - 1, Math.floor(tInChain / CYCLE_MS));
    if (newIdx !== currentMatrixIdx) {
      // Switching matrix: reset the previous matrix's boosts + hide its I/O.
      const prev = bundles[currentMatrixIdx];
      for (let i = 0; i < prev.boost.length; i += 1) prev.boost[i] = 0;
      applyBoostsToInstancedColors(prev);
      if (prev.inputMat) prev.inputMat.opacity = 0;
      if (prev.outputMat) prev.outputMat.opacity = 0;
      currentMatrixIdx = newIdx;
    }

    const bundle = bundles[currentMatrixIdx];
    const tInMatrix = tInChain - currentMatrixIdx * CYCLE_MS;

    // Determine phase.
    if (tInMatrix < PHASE_INPUT_MS) {
      // Phase 1: input vector fades in from left.
      const t = tInMatrix / PHASE_INPUT_MS; // 0 -> 1
      if (bundle.inputMat) bundle.inputMat.opacity = 0.85 * t;
      if (bundle.outputMat) bundle.outputMat.opacity = 0;
      // Make sure column boosts are at baseline.
      for (let i = 0; i < bundle.boost.length; i += 1) bundle.boost[i] = 0;
      applyBoostsToInstancedColors(bundle);
    } else if (tInMatrix < PHASE_INPUT_MS + PHASE_FIRE_MS) {
      // Phase 2: columns fire left-to-right with overlap.
      if (bundle.inputMat) bundle.inputMat.opacity = 0.85;
      if (bundle.outputMat) bundle.outputMat.opacity = 0;
      const fireT = (tInMatrix - PHASE_INPUT_MS) / PHASE_FIRE_MS; // 0 -> 1
      const head = fireT * GRID; // current "leading" column position (float)
      // Each column has a triangular envelope with width ~3 columns so
      // the next column starts before the previous fades. Envelope peaks
      // at 1.0 when |col - head| < 0.5, falls to 0 over width.
      const width = 3.0;
      for (let col = 0; col < GRID; col += 1) {
        const dist = Math.abs(col - head);
        const env = Math.max(0, 1.0 - dist / width);
        if (env > 0) {
          for (let r = 0; r < GRID; r += 1) {
            const idx = r * GRID + col;
            bundle.boost[idx] = env;
          }
        } else {
          for (let r = 0; r < GRID; r += 1) {
            const idx = r * GRID + col;
            // Decay rather than zero so trailing columns fade smoothly.
            bundle.boost[idx] *= 0.85;
          }
        }
      }
      applyBoostsToInstancedColors(bundle);
    } else if (tInMatrix < PHASE_INPUT_MS + PHASE_FIRE_MS + PHASE_OUTPUT_MS) {
      // Phase 3: output vector emerges from the right.
      if (bundle.inputMat) bundle.inputMat.opacity = 0.85;
      const t = (tInMatrix - PHASE_INPUT_MS - PHASE_FIRE_MS) / PHASE_OUTPUT_MS;
      if (bundle.outputMat) bundle.outputMat.opacity = 0.85 * t;
      // Decay column boosts smoothly.
      for (let i = 0; i < bundle.boost.length; i += 1) {
        bundle.boost[i] *= 0.85;
      }
      applyBoostsToInstancedColors(bundle);
    } else {
      // Phase 4: pause. Input + output stay visible; matrix returns to base.
      for (let i = 0; i < bundle.boost.length; i += 1) bundle.boost[i] = 0;
      applyBoostsToInstancedColors(bundle);
    }
  }

  function applyBoostsToInstancedColors(b: MatrixBundle): void {
    for (let i = 0; i < INSTANCES_PER_GRID; i += 1) {
      const rBase = b.baseColors[i * 3 + 0];
      const gBase = b.baseColors[i * 3 + 1];
      const bBase = b.baseColors[i * 3 + 2];
      const bo = b.boost[i];
      if (bo > 0) {
        // Lerp the base color toward white by `bo`.
        scratchColor.setRGB(rBase, gBase, bBase);
        scratchInstanceColor.setRGB(1, 1, 1);
        scratchColor.lerp(scratchInstanceColor, Math.min(1, bo * 0.65));
        b.instanced.setColorAt(i, scratchColor);
      } else {
        scratchColor.setRGB(rBase, gBase, bBase);
        b.instanced.setColorAt(i, scratchColor);
      }
    }
    if (b.instanced.instanceColor) {
      b.instanced.instanceColor.needsUpdate = true;
    }
  }

  function disposeMaterial(m: Material | null | undefined): void {
    if (!m) return;
    m.dispose();
  }

  function dispose(): void {
    for (const b of bundles) {
      b.sphereGeom.dispose();
      disposeMaterial(b.sphereMat);
      b.instanced.dispose();
      if (b.inputGeom) b.inputGeom.dispose();
      if (b.inputDots) b.inputDots.dispose();
      disposeMaterial(b.inputMat);
      if (b.outputGeom) b.outputGeom.dispose();
      if (b.outputDots) b.outputDots.dispose();
      disposeMaterial(b.outputMat);
      if (b.labelTex) b.labelTex.dispose();
      disposeMaterial(b.labelMat);
      if (b.label) b.matrixGroup.remove(b.label);
      b.matrixGroup.remove(b.instanced);
      if (b.inputDots) b.matrixGroup.remove(b.inputDots);
      if (b.outputDots) b.matrixGroup.remove(b.outputDots);
      group.remove(b.matrixGroup);
    }
    bundles.length = 0;
    if (warning) {
      if (warningTex) warningTex.dispose();
      disposeMaterial(warningMat);
      group.remove(warning);
      warning = null;
      warningMat = null;
      warningTex = null;
    }
  }

  // Initial tick so static-rendered (un-ticked) groups have correct opacity.
  update(0, initialActive);

  return { group, dispose, update };
}

// Placeholder generator exported so tests can verify the placeholder path
// independently of weight-file loading.
export { makePlaceholderSnapshots as __testMakePlaceholderSnapshots };

export default buildCloseViewMatrixGrid;

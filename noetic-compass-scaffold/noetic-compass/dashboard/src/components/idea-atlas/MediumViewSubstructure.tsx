/**
 * MediumViewSubstructure — imperative Three.js builder for a layer's
 * "medium-view" sub-structure plates (LOD level 1).
 *
 * For a given CASBrainLayer, returns a THREE.Group containing 1-4
 * family-colored plates labeled with their sub-matrix names + canonical
 * dimensions (Q/K/V/O for attention, up/down for FFN, etc.). Plates pulse
 * gently when `active` is true. No DOM, no React, no DOM events; the
 * caller (CASBrainMap) attaches the Group to a THREE.LOD and ticks the
 * `update(active, dt)` callback inside the render loop.
 *
 * Disposal pattern mirrors SggsScene.tsx halo disposal: every geometry,
 * material, and CanvasTexture this module creates is tracked and freed
 * by `dispose()`.
 */
import {
  AdditiveBlending,
  BoxGeometry,
  CanvasTexture,
  Color,
  DoubleSide,
  Group,
  Mesh,
  MeshBasicMaterial,
  PlaneGeometry,
  Sprite,
  SpriteMaterial,
  type Material,
} from 'three';
import type { CASBrainLayer } from '../../lib/cas_brain_mock_flow';

// ── Public types ─────────────────────────────────────────────────────────

export interface MediumViewSubstructureProps {
  layer: CASBrainLayer;
  /** Node's base radius from the CASBrainMap node mesh. */
  baseSize: number;
  /** Family color hex string (e.g. '#a78bfa'). */
  familyColor: string;
  /** Currently-firing layer in the active thought flow. Drives the pulse. */
  active: boolean;
}

export interface MediumViewSubstructureHandle {
  group: Group;
  dispose: () => void;
  /** Tick from the render loop. dt is seconds since last frame. */
  update: (active: boolean, dt: number) => void;
}

// ── Plate spec ───────────────────────────────────────────────────────────

interface PlateSpec {
  name: string;
  /** "rows x cols" or empty string when unknown. */
  shape: string;
  /** Plate position in the group's local frame. Z = 0. */
  x: number;
  y: number;
}

// Canonical sub-matrix shapes for the CAS-Native v0.2 architecture. Values
// drawn from cas-native/model/cas_native_model.py + nl_generation_head.py +
// typed_fiber_decoder.py + the parameter table in cas_brain_mock_flow.ts.
const SHAPE = {
  attnQKVO: '512 x 512',
  ffnUp: '512 x 2048',
  ffnDown: '2048 x 512',
  emb: '24388 x 512',
  lmHead: '512 x 24388',
  // Typed Fiber Decoder uses d_model=384, n_heads=6.
  tfdQKVO: '384 x 384',
} as const;

/**
 * Build the plate layout for one layer. Returns 1-4 plate specs.
 * Plates are arranged so they fit inside ~2x baseSize bounding box,
 * centered on the layer's position (0,0,0 in the group's local frame).
 */
function plateSpecsFor(layer: CASBrainLayer, baseSize: number): PlateSpec[] {
  const halfSpan = baseSize * 1.6;
  const family = layer.family;

  // Helper for 2x2 grid layout (Q/K/V/O).
  function grid2x2(
    names: ReadonlyArray<[string, string]>,
  ): PlateSpec[] {
    const out: PlateSpec[] = [];
    const s = halfSpan * 0.55;
    const positions: ReadonlyArray<[number, number]> = [
      [-s, s],
      [s, s],
      [-s, -s],
      [s, -s],
    ];
    for (let i = 0; i < names.length && i < positions.length; i += 1) {
      const [name, shape] = names[i];
      out.push({ name, shape, x: positions[i][0], y: positions[i][1] });
    }
    return out;
  }

  // Helper for vertical stack.
  function stackVertical(names: ReadonlyArray<[string, string]>): PlateSpec[] {
    const out: PlateSpec[] = [];
    const n = names.length;
    const totalH = halfSpan * 1.6;
    const step = n > 1 ? totalH / (n - 1) : 0;
    const top = totalH / 2;
    for (let i = 0; i < n; i += 1) {
      const [name, shape] = names[i];
      const y = top - i * step;
      out.push({ name, shape, x: 0, y });
    }
    return out;
  }

  // Helper for horizontal pair.
  function horizontalPair(
    a: [string, string],
    b: [string, string],
  ): PlateSpec[] {
    const s = halfSpan * 0.55;
    return [
      { name: a[0], shape: a[1], x: -s, y: 0 },
      { name: b[0], shape: b[1], x: s, y: 0 },
    ];
  }

  // Helper for single plate.
  function single(name: string, shape: string): PlateSpec[] {
    return [{ name, shape, x: 0, y: 0 }];
  }

  switch (family) {
    case 'embedding': {
      // Token embedding / decoder token embedding / cognitive state embedding
      // all share the (vocab x d_model) shape, except positional / soft
      // prefix which are smaller. Specialize when we recognize the id.
      const id = layer.id;
      if (id === 'token_embedding' || id === 'decoder_token_embedding') {
        return single('weight', SHAPE.emb);
      }
      if (id === 'cognitive_state_embedding') {
        return single('weight', `${layer.dimensions.d_model} x 40`);
      }
      if (id === 'positional_encoding') {
        return single('weight', 'sinusoidal (no params)');
      }
      if (id === 'soft_prefix_proj') {
        return single('weight', '64 x (4 x 512)');
      }
      if (id === 'decoder_pos_embedding') {
        return single('weight', '512 x 512');
      }
      return single('weight', '');
    }

    case 'encoder_attn':
    case 'decoder_attn': {
      return grid2x2([
        ['Q', SHAPE.attnQKVO],
        ['K', SHAPE.attnQKVO],
        ['V', SHAPE.attnQKVO],
        ['O', SHAPE.attnQKVO],
      ]);
    }

    case 'encoder_gate': {
      return horizontalPair(['gate', '512 x 512'], ['projection', '512 x 512']);
    }

    case 'encoder_ffn':
    case 'decoder_ffn': {
      return stackVertical([
        ['up-proj', SHAPE.ffnUp],
        ['down-proj', SHAPE.ffnDown],
      ]);
    }

    case 'decoder_head': {
      return single('lm_head', SHAPE.lmHead);
    }

    case 'output': {
      return single('emit', 'streaming tokens');
    }

    case 'special_branch': {
      const id = layer.id;
      const label = layer.label.toLowerCase();
      if (id === 'topos_reasoner' || label.includes('topos')) {
        return stackVertical([
          ['pool', '512 x 256'],
          ['truth-head', '256 x 3'],
        ]);
      }
      if (id === 'inversion_detector' || label.includes('inversion')) {
        return stackVertical([
          ['axis-head', '512 x 7'],
        ]);
      }
      if (id === 'typed_fiber_decoder' || label.includes('typed fiber')) {
        return grid2x2([
          ['Q', SHAPE.tfdQKVO],
          ['K', SHAPE.tfdQKVO],
          ['V', SHAPE.tfdQKVO],
          ['slot-head', '384 x 9'],
        ]);
      }
      if (id === 'register_film' || label.includes('register')) {
        return horizontalPair(['gamma', '4 x 512'], ['beta', '4 x 512']);
      }
      if (id === 'lacunarity_gate' || label.includes('lacunarity')) {
        return horizontalPair(['gate', '40 x 40'], ['rebalance', '40 x 40']);
      }
      if (id === 'generative_head' || label.includes('generative')) {
        return single('compose', '512 x 512');
      }
      // Unknown special branch — keep honest.
      return single('see weights below', '');
    }

    default: {
      return single(layer.label, '');
    }
  }
}

// ── Label sprite (canvas-textured) ───────────────────────────────────────

interface SpriteResult {
  sprite: Sprite;
  texture: CanvasTexture;
  material: SpriteMaterial;
}

/**
 * Build a canvas-textured sprite label for a plate. Caller positions it
 * above the plate. SSR-safe: returns null when no document is available.
 */
function makeLabelSprite(
  text: string,
  subText: string,
  strokeHex: string,
): SpriteResult | null {
  if (typeof document === 'undefined') return null;
  const canvas = document.createElement('canvas');
  const W = 256;
  const H = 96;
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext('2d');
  if (ctx) {
    ctx.clearRect(0, 0, W, H);
    // Pill background.
    ctx.fillStyle = 'rgba(2, 6, 23, 0.78)';
    ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = strokeHex;
    ctx.lineWidth = 2;
    ctx.strokeRect(2, 2, W - 4, H - 4);
    // Name.
    ctx.fillStyle = strokeHex;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.font = 'bold 26px ui-monospace, SFMono-Regular, monospace';
    ctx.fillText(text, W / 2, 32);
    // Shape.
    if (subText) {
      ctx.fillStyle = '#cbd5e1';
      ctx.font = '20px ui-monospace, SFMono-Regular, monospace';
      ctx.fillText(subText, W / 2, 66);
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
  // World-space size; ~1.2 x 0.45 reads well at the medium-view distance.
  sprite.scale.set(1.2, 0.45, 1);
  return { sprite, texture, material };
}

// ── Plate mesh ───────────────────────────────────────────────────────────

interface PlateBundle {
  /** Inner group: pulses are applied here. */
  inner: Group;
  body: Mesh;
  bodyMat: MeshBasicMaterial;
  bodyGeom: BoxGeometry;
  halo: Mesh | null;
  haloMat: MeshBasicMaterial | null;
  haloGeom: PlaneGeometry | null;
  haloTex: CanvasTexture | null;
  label: Sprite | null;
  labelMat: SpriteMaterial | null;
  labelTex: CanvasTexture | null;
  /** Random per-plate phase so the pulses don't all peak together. */
  phase: number;
}

function makeHaloTexture(strokeHex: string): CanvasTexture | null {
  if (typeof document === 'undefined') return null;
  const canvas = document.createElement('canvas');
  const W = 128;
  const H = 128;
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;
  ctx.clearRect(0, 0, W, H);
  const g = ctx.createRadialGradient(W / 2, H / 2, W * 0.1, W / 2, H / 2, W * 0.5);
  g.addColorStop(0, `${strokeHex}cc`);
  g.addColorStop(0.5, `${strokeHex}55`);
  g.addColorStop(1, `${strokeHex}00`);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);
  const tex = new CanvasTexture(canvas);
  tex.needsUpdate = true;
  return tex;
}

function buildPlate(
  spec: PlateSpec,
  familyColor: string,
  plateSize: number,
  index: number,
): PlateBundle {
  const inner = new Group();
  inner.position.set(spec.x, spec.y, 0);

  // Plate body — rounded box approximation (thin box reads as a plate at
  // medium-view distance).
  const w = plateSize;
  const h = plateSize * 0.72;
  const d = plateSize * 0.18;
  const bodyGeom = new BoxGeometry(w, h, d);
  const bodyMat = new MeshBasicMaterial({
    color: new Color(familyColor),
    transparent: true,
    opacity: 0.78,
  });
  // Emissive feel via small additive halo plane behind the body.
  const body = new Mesh(bodyGeom, bodyMat);
  body.userData = { role: 'plate-body', plateName: spec.name };
  inner.add(body);

  // Subtle emissive halo behind the plate.
  const haloTex = makeHaloTexture(familyColor);
  let halo: Mesh | null = null;
  let haloMat: MeshBasicMaterial | null = null;
  let haloGeom: PlaneGeometry | null = null;
  if (haloTex) {
    haloGeom = new PlaneGeometry(w * 1.6, h * 1.6);
    haloMat = new MeshBasicMaterial({
      map: haloTex,
      transparent: true,
      opacity: 0.32,
      blending: AdditiveBlending,
      depthWrite: false,
      side: DoubleSide,
    });
    halo = new Mesh(haloGeom, haloMat);
    halo.position.set(0, 0, -d * 0.6);
    halo.userData = { role: 'plate-halo', plateName: spec.name };
    inner.add(halo);
  }

  // Floating text label above the plate.
  const labelRes = makeLabelSprite(spec.name, spec.shape, familyColor);
  let label: Sprite | null = null;
  let labelMat: SpriteMaterial | null = null;
  let labelTex: CanvasTexture | null = null;
  if (labelRes) {
    label = labelRes.sprite;
    labelMat = labelRes.material;
    labelTex = labelRes.texture;
    label.position.set(0, h * 0.75 + 0.18, 0);
    label.userData = { role: 'plate-label', plateName: spec.name };
    inner.add(label);
  }

  return {
    inner,
    body,
    bodyMat,
    bodyGeom,
    halo,
    haloMat,
    haloGeom,
    haloTex,
    label,
    labelMat,
    labelTex,
    phase: (index * 0.47) % (Math.PI * 2),
  };
}

// ── Builder ──────────────────────────────────────────────────────────────

/**
 * Build a sub-structure plate group for a layer. The returned handle's
 * `group` should be attached to a THREE.LOD; `update` should be called
 * each frame; `dispose` should be called on unmount.
 *
 * Note: this is an imperative builder — no DOM, no React. Pure Three.js.
 */
export function buildMediumViewSubstructure(
  props: MediumViewSubstructureProps,
): MediumViewSubstructureHandle {
  const { layer, baseSize, familyColor, active: initialActive } = props;

  const group = new Group();
  group.userData = {
    role: 'medium-view-substructure',
    layerId: layer.id,
  };

  const specs = plateSpecsFor(layer, baseSize);
  // Auto-size plates so 4-up grids stay compact, single plates are bigger.
  const plateSize =
    specs.length >= 4 ? baseSize * 1.0 : specs.length >= 2 ? baseSize * 1.15 : baseSize * 1.55;

  const plates: PlateBundle[] = [];
  for (let i = 0; i < specs.length; i += 1) {
    const bundle = buildPlate(specs[i], familyColor, plateSize, i);
    group.add(bundle.inner);
    plates.push(bundle);
  }

  // Track logical active state — `update` callers re-pass it each frame,
  // but we keep the start value so a never-ticked group still reads
  // correctly when inspected by tests.
  let currentlyActive = initialActive;
  // Time accumulator (seconds). Drives the pulse phase.
  let tAccum = 0;

  function update(active: boolean, dt: number): void {
    currentlyActive = active;
    // Guard against jank (dt = NaN/Infinity) so the math stays bounded.
    if (!Number.isFinite(dt) || dt < 0) {
      return;
    }
    tAccum += dt;

    // Pulse cycle ~1.2s. Scale 1.0 -> 1.08 -> 1.0 when active.
    // When inactive, decay to baseline.
    for (const plate of plates) {
      if (currentlyActive) {
        const omega = (Math.PI * 2) / 1.2;
        // Half-sine envelope so the scale never goes below 1.0.
        const env = 0.5 + 0.5 * Math.sin(omega * tAccum + plate.phase);
        const scale = 1.0 + 0.08 * env;
        plate.inner.scale.set(scale, scale, scale);
        plate.bodyMat.opacity = 0.78 + 0.16 * env;
        if (plate.haloMat) plate.haloMat.opacity = 0.32 + 0.18 * env;
      } else {
        // Decay back to baseline. Lerp ~10%/frame at 60fps is fine.
        const s = plate.inner.scale.x;
        const next = s + (1.0 - s) * 0.15;
        plate.inner.scale.set(next, next, next);
        const op = plate.bodyMat.opacity;
        plate.bodyMat.opacity = op + (0.78 - op) * 0.15;
        if (plate.haloMat) {
          const ho = plate.haloMat.opacity;
          plate.haloMat.opacity = ho + (0.32 - ho) * 0.15;
        }
      }
    }
  }

  function disposeMaterial(m: Material | null | undefined): void {
    if (!m) return;
    m.dispose();
  }

  function dispose(): void {
    for (const plate of plates) {
      plate.bodyGeom.dispose();
      disposeMaterial(plate.bodyMat);
      if (plate.haloGeom) plate.haloGeom.dispose();
      if (plate.haloTex) plate.haloTex.dispose();
      disposeMaterial(plate.haloMat);
      if (plate.labelTex) plate.labelTex.dispose();
      disposeMaterial(plate.labelMat);
      // Remove children from inner group.
      if (plate.halo) plate.inner.remove(plate.halo);
      if (plate.label) plate.inner.remove(plate.label);
      plate.inner.remove(plate.body);
      group.remove(plate.inner);
    }
    plates.length = 0;
  }

  // Initial tick so static-rendered (un-ticked) groups have correct opacity.
  update(initialActive, 0);

  return { group, dispose, update };
}

export default buildMediumViewSubstructure;

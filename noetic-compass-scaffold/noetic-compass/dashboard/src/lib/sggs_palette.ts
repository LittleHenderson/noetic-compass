/**
 * sggs_palette — Shared kind→color palette for the Atlas Thought Tree.
 *
 * Source of truth: `ThoughtTreeView.tsx` defines the 7-kind palette as raw
 * hex (SVG `fill` / `stroke`). The SGGS 3D scene needs the same colors as
 * `THREE.Color` instances so it can hand them to `MeshBasicMaterial`,
 * `LineBasicMaterial`, and canvas-texture sprite chips without per-call
 * conversion. To avoid drift between the SVG renderer and the 3D scene,
 * the canonical hex values live here; ThoughtTreeView will adopt this
 * module in a follow-up sweep.
 *
 * Two views of the same data:
 *   - `KIND_PALETTE_HEX`   — raw `#rrggbb` strings (SVG/CSS consumers).
 *   - `KIND_PALETTE_THREE` — `THREE.Color` instances (3D consumers).
 *
 * Both keep `fill` + `stroke` separate so the 3D scene can mirror
 * SVG's "card body" + "ribbon/stroke" pattern (PlaneGeometry body,
 * brighter stroke for ribbon + selection ring).
 */
import { Color } from 'three';

/** Canonical kind set, in the order ThoughtTreeView surfaces them. */
export const KIND_ORDER = [
  'user_prompt',
  'nl_bridge',
  'cas_expression',
  'model_generation',
  'identifier_attempt',
  'slot_pattern',
  'confidence_marker',
] as const;

export type KnownKind = (typeof KIND_ORDER)[number];

export interface KindPaletteHex {
  /** Card body / fill — used for the SVG `fill` and 3D Plane material. */
  fill: string;
  /** Ribbon / stroke / selection — brighter sibling of `fill`. */
  stroke: string;
  /** Stable kind tag (snake_case) — same as the input key. */
  kind: string;
}

export interface KindPaletteThree {
  fill: Color;
  stroke: Color;
  kind: string;
}

/**
 * Hex palette. Values must remain identical to `ThoughtTreeView.tsx`
 * `KIND_PALETTE` so SVG + SGGS read the same colors when displayed
 * side-by-side. Codex audit 2026-05-13 flagged divergence here as a
 * stakeholder-grade defect — keep them locked.
 */
export const KIND_PALETTE_HEX: Record<KnownKind, KindPaletteHex> = {
  user_prompt: { fill: '#3b82f6', stroke: '#60a5fa', kind: 'user_prompt' },
  nl_bridge: { fill: '#8b5cf6', stroke: '#a78bfa', kind: 'nl_bridge' },
  cas_expression: { fill: '#14b8a6', stroke: '#2dd4bf', kind: 'cas_expression' },
  model_generation: { fill: '#10b981', stroke: '#34d399', kind: 'model_generation' },
  identifier_attempt: { fill: '#06b6d4', stroke: '#22d3ee', kind: 'identifier_attempt' },
  slot_pattern: { fill: '#f59e0b', stroke: '#fbbf24', kind: 'slot_pattern' },
  confidence_marker: { fill: '#f43f5e', stroke: '#fb7185', kind: 'confidence_marker' },
};

/** Fallback palette for kinds the renderer hasn't seen before. */
export const UNKNOWN_PALETTE_HEX: KindPaletteHex = {
  fill: '#64748b',
  stroke: '#94a3b8',
  kind: 'unknown',
};

/**
 * Three.js view of the same palette. Lazily-frozen so callers can't
 * mutate the shared `Color` instances — every consumer either reads
 * `.getHex()` / `.toArray()` or clones via `.clone()` before mutating.
 */
export const KIND_PALETTE_THREE: Record<KnownKind, KindPaletteThree> = (() => {
  const out = {} as Record<KnownKind, KindPaletteThree>;
  for (const kind of KIND_ORDER) {
    const hex = KIND_PALETTE_HEX[kind];
    out[kind] = {
      fill: new Color(hex.fill),
      stroke: new Color(hex.stroke),
      kind: hex.kind,
    };
  }
  return out;
})();

export const UNKNOWN_PALETTE_THREE: KindPaletteThree = {
  fill: new Color(UNKNOWN_PALETTE_HEX.fill),
  stroke: new Color(UNKNOWN_PALETTE_HEX.stroke),
  kind: UNKNOWN_PALETTE_HEX.kind,
};

/** Selected-state accent color (matches SVG's `#fafafa` selection ring). */
export const SELECTED_STROKE_HEX = '#fafafa';
export const SELECTED_STROKE_THREE = new Color(SELECTED_STROKE_HEX);

/** Background clear color for the SGGS scene (matches dashboard panel). */
export const SCENE_BACKGROUND_HEX = '#0d1117';
export const SCENE_BACKGROUND_THREE = new Color(SCENE_BACKGROUND_HEX);

/** Look up a hex palette entry, falling back to `UNKNOWN_PALETTE_HEX`. */
export function paletteHexFor(kind: string): KindPaletteHex {
  return (KIND_PALETTE_HEX as Record<string, KindPaletteHex>)[kind] ?? UNKNOWN_PALETTE_HEX;
}

/**
 * Look up a Three.js palette entry, falling back to `UNKNOWN_PALETTE_THREE`.
 * Returns the SHARED instance — clone before mutating.
 */
export function paletteThreeFor(kind: string): KindPaletteThree {
  return (KIND_PALETTE_THREE as Record<string, KindPaletteThree>)[kind] ?? UNKNOWN_PALETTE_THREE;
}

/** Human-readable chip labels, mirroring `KIND_DISPLAY` in ThoughtTreeView. */
export const KIND_DISPLAY: Record<KnownKind, string> = {
  user_prompt: 'USER PROMPT',
  nl_bridge: 'NL BRIDGE',
  cas_expression: 'CAS',
  model_generation: 'MODEL OUTPUT',
  identifier_attempt: 'IDENTIFIER',
  slot_pattern: 'SLOT TRACE',
  confidence_marker: 'CONFIDENCE',
};

export function kindLabel(kind: string): string {
  return (
    (KIND_DISPLAY as Record<string, string>)[kind] ?? kind.replace(/_/g, ' ').toUpperCase()
  );
}

/**
 * CAS Value-Keyed Color Palette — TypeScript source of truth.
 *
 * Mirrors api/notation/color_palette.py exactly. Hex values MUST stay in sync.
 * Full design rationale: docs/working/cas_color_palette_specification.md
 *
 * PALETTE_VERSION is a breaking-change sentinel. Downstream consumers should
 * pin to this version. Do not bump in the same PR as palette changes.
 */

export const PALETTE_VERSION = "v1.0";

// ---------------------------------------------------------------------------
// Noetic axis — ^0 through ^9
// Basis: Paul Tol "muted" 10-class qualitative palette, lightness-adjusted
// for L∈[0.12,0.30] to meet WCAG 3:1 on both #0d1117 and #ffffff.
// ---------------------------------------------------------------------------
const NOETIC_COLORS: readonly string[] = [
  "#3388BB", // ^0 Idea         — mid blue        (Tol pale-blue, darkened)
  "#117733", // ^1 Mind         — dark green       (Tol green, kept)
  "#CC7700", // ^2 Positive     — amber-orange     (Tol straw, hue-shifted + darkened)
  "#CC6677", // ^3 Negative     — rose-pink        (Tol rose, kept)
  "#2E7A6E", // ^4 Vibration    — dark teal        (Tol teal, darkened)
  "#CC3388", // ^5 Female       — magenta          (Tol wine, brightened)
  "#5B55C0", // ^6 Male         — indigo           (Tol indigo, brightened)
  "#7A7A25", // ^7 Rhythm       — olive            (Tol olive, darkened)
  "#AA4499", // ^8 Above/Cause  — purple           (Tol purple, kept)
  "#6B778C", // ^9 Below/Effect — blue-gray        (Tol gray → blue-gray)
] as const;

// ---------------------------------------------------------------------------
// Domain axis — P, C, E, O
// Medium-saturation tier (L∈[0.22,0.30]), distinct from Noetics.
// ---------------------------------------------------------------------------
const DOMAIN_COLORS: Readonly<Record<string, string>> = {
  P: "#7B7EC4", // Principled  — lavender-indigo
  C: "#4490B0", // Cognitive   — steel blue
  E: "#4A9068", // Evaluative  — muted emerald
  O: "#C0883C", // Operational — muted amber
} as const;

// ---------------------------------------------------------------------------
// Drive axis — F1 through F7 (1-indexed)
// Basis: Paul Tol "bright" palette hues, lightness-adjusted.
// F3/F5 pair avoids red+green to prevent deut/prot confusion.
// ---------------------------------------------------------------------------
const DRIVE_COLORS: readonly string[] = [
  "",         // index 0 — unused (drives are 1-indexed)
  "#4477AA", // F1 Unity      — blue
  "#7755CC", // F2 Wisdom     — purple
  "#228866", // F3 Vitality   — teal-green
  "#997700", // F4 Connection — amber-olive (self-dual)
  "#BB4488", // F5 Agency     — pink-magenta
  "#BB6699", // F6 Structure  — medium pink
  "#446688", // F7 Purpose    — slate blue
] as const;

// ---------------------------------------------------------------------------
// Register axis — T, A, f, E
// Border-style overlays keep Register orthogonal to fill colors.
// ---------------------------------------------------------------------------
export interface RegisterTreatment {
  borderStyle: string;
  color: string;
}

const REGISTER_TREATMENTS: Readonly<Record<string, RegisterTreatment>> = {
  T: { borderStyle: "solid",  color: "#D4A020" }, // Transcendent — gold solid
  A: { borderStyle: "double", color: "#4488CC" }, // Analytical   — blue double
  f: { borderStyle: "dashed", color: "#CC4477" }, // Affective    — rose dashed
  E: { borderStyle: "dotted", color: "#44AA77" }, // Embodied     — teal dotted
} as const;

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/** Return the hex color for Noetic operator ^n (n in 0..9). */
export function noeticColor(n: number): string {
  if (!Number.isInteger(n) || n < 0 || n > 9) {
    throw new Error(`Noetic index must be an integer in [0, 9]; got ${n}`);
  }
  return NOETIC_COLORS[n];
}

/** Return the hex color for Domain d in {'P', 'C', 'E', 'O'}. */
export function domainColor(d: "P" | "C" | "E" | "O"): string {
  const color = DOMAIN_COLORS[d];
  if (color === undefined) {
    throw new Error(`Domain must be one of P, C, E, O; got ${String(d)}`);
  }
  return color;
}

/** Return the hex color for Drive F_k (k in 1..7). */
export function driveColor(k: number): string {
  if (!Number.isInteger(k) || k < 1 || k > 7) {
    throw new Error(`Drive index must be an integer in [1, 7]; got ${k}`);
  }
  return DRIVE_COLORS[k];
}

/**
 * Return the visual treatment for Register r in {'T', 'A', 'f', 'E'}.
 * Returns a copy; mutations do not affect the internal palette.
 */
export function registerTreatment(r: "T" | "A" | "f" | "E"): RegisterTreatment {
  const treatment = REGISTER_TREATMENTS[r];
  if (treatment === undefined) {
    throw new Error(`Register must be one of T, A, f, E; got ${String(r)}`);
  }
  return { ...treatment };
}

/**
 * Return the most-specific axis fill color for a diagram node.
 * Precedence: Noetic > Domain > Drive. Returns null if no axis info.
 */
export function axisColorForNode(node: {
  noetic?: number | null;
  domain?: string | null;
  drive?: number | null;
}): string | null {
  if (node.noetic !== undefined && node.noetic !== null) {
    return noeticColor(node.noetic);
  }
  if (node.domain !== undefined && node.domain !== null) {
    return domainColor(node.domain as "P" | "C" | "E" | "O");
  }
  if (node.drive !== undefined && node.drive !== null) {
    return driveColor(node.drive);
  }
  return null;
}

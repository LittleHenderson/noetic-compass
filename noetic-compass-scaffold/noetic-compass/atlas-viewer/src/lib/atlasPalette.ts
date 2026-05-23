/**
 * Atlas Viewer v0.0 — extended color palette.
 *
 * Source of truth for status colors, foundation drive hues, and color-blind
 * Okabe-Ito alternates per docs/working/atlas_viewer_neuralnet_scene_design_2026_05_22.md §8.
 *
 * Cross-package note: the shared dashboard palette at
 *   ../../../dashboard/src/lib/casColorPalette
 * sits outside this package's tsconfig `include`. Re-exporting it through a
 * relative import would either pull dashboard source into the atlas-viewer
 * compile graph or trip TS6059 ("not under rootDir"). The minimal type we
 * need from there (RegisterTreatment) is therefore copied here verbatim and
 * MUST stay in sync with casColorPalette.ts.
 */

export type DriveIndex = 1 | 2 | 3 | 4 | 5 | 6 | 7;

export interface RegisterTreatment {
  borderStyle: string;
  color: string;
}

export interface AtlasStatusColors {
  accepted: string;
  caveat: string;
  constrain: string;
  suppress: string;
  activeTrace: string;
  intervention: string;
  unavailable: string;
}

export const ATLAS_STATUS_COLORS: AtlasStatusColors = {
  accepted: '#22c55e',
  caveat: '#eab308',
  constrain: '#f97316',
  suppress: '#ef4444',
  // Wave 5.2: teal-400 — matches noeticcompass.com production accent. The
  // previous bright blue (#3b82f6) read as "Web 2.0 dashboard" and was the
  // single biggest cartoonish-looking color across the cockpit (timeline,
  // tab underlines, selected cards, scrubber fill, edges).
  activeTrace: '#2dd4bf',
  intervention: '#a855f7',
  unavailable: '#6b7280',
} as const;

export const FOUNDATION_HUES: Record<DriveIndex, number> = {
  1: 220,
  2: 280,
  3: 30,
  4: 160,
  5: 60,
  6: 200,
  7: 320,
} as const;

export const OKABE_ITO_FOUNDATION: Record<DriveIndex, string> = {
  1: '#0072B2',
  2: '#CC79A7',
  3: '#D55E00',
  4: '#009E73',
  5: '#F0E442',
  6: '#56B4E9',
  7: '#E69F00',
} as const;

const clamp = (value: number, min: number, max: number): number =>
  Math.min(max, Math.max(min, value));

export function foundationColorForActivation(
  drive: DriveIndex,
  activation: number,
  margin?: number,
): string {
  const hue = FOUNDATION_HUES[drive];
  const a = clamp(activation, 0, 1);
  const saturation = 30 + 70 * a;
  const lightness = clamp(55 - (20 * (margin ?? 0)) / 10, 35, 75);
  return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
}

export type PaletteMode = 'default' | 'okabe-ito';

export interface AtlasPalette {
  mode: PaletteMode;
  status: AtlasStatusColors;
  foundationHues: Record<DriveIndex, number>;
  foundationColor: (drive: DriveIndex, activation: number, margin?: number) => string;
}

export function usePaletteMode(mode: PaletteMode): AtlasPalette {
  if (mode === 'okabe-ito') {
    // Map Okabe-Ito hexes back to HSL degrees so activation modulation still works.
    const okabeHues: Record<DriveIndex, number> = {
      1: hexToHue(OKABE_ITO_FOUNDATION[1]),
      2: hexToHue(OKABE_ITO_FOUNDATION[2]),
      3: hexToHue(OKABE_ITO_FOUNDATION[3]),
      4: hexToHue(OKABE_ITO_FOUNDATION[4]),
      5: hexToHue(OKABE_ITO_FOUNDATION[5]),
      6: hexToHue(OKABE_ITO_FOUNDATION[6]),
      7: hexToHue(OKABE_ITO_FOUNDATION[7]),
    };
    return {
      mode,
      status: ATLAS_STATUS_COLORS,
      foundationHues: okabeHues,
      foundationColor: (drive, activation, margin) => {
        const a = clamp(activation, 0, 1);
        const saturation = 30 + 70 * a;
        const lightness = clamp(55 - (20 * (margin ?? 0)) / 10, 35, 75);
        return `hsl(${okabeHues[drive]}, ${saturation}%, ${lightness}%)`;
      },
    };
  }
  return {
    mode: 'default',
    status: ATLAS_STATUS_COLORS,
    foundationHues: FOUNDATION_HUES,
    foundationColor: foundationColorForActivation,
  };
}

function hexToHue(hex: string): number {
  const m = /^#([0-9a-fA-F]{6})$/.exec(hex);
  if (!m) return 0;
  const intVal = parseInt(m[1], 16);
  const r = ((intVal >> 16) & 0xff) / 255;
  const g = ((intVal >> 8) & 0xff) / 255;
  const b = (intVal & 0xff) / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const d = max - min;
  if (d === 0) return 0;
  let h = 0;
  if (max === r) h = ((g - b) / d) % 6;
  else if (max === g) h = (b - r) / d + 2;
  else h = (r - g) / d + 4;
  h = Math.round(h * 60);
  return h < 0 ? h + 360 : h;
}

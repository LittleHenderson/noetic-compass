import { describe, expect, it } from 'vitest';
import {
  ATLAS_STATUS_COLORS,
  FOUNDATION_HUES,
  OKABE_ITO_FOUNDATION,
  foundationColorForActivation,
  usePaletteMode,
  type DriveIndex,
} from './atlasPalette';

const HEX7 = /^#[0-9a-fA-F]{6}$/;
const HSL = /^hsl\((\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?)%,\s*(\d+(?:\.\d+)?)%\)$/;
const DRIVES: DriveIndex[] = [1, 2, 3, 4, 5, 6, 7];

describe('ATLAS_STATUS_COLORS', () => {
  it('exposes every required status key as a 7-char hex', () => {
    const keys = [
      'accepted',
      'caveat',
      'constrain',
      'suppress',
      'activeTrace',
      'intervention',
      'unavailable',
    ] as const;
    for (const key of keys) {
      const value = ATLAS_STATUS_COLORS[key];
      expect(value, key).toMatch(HEX7);
      expect(value.length).toBe(7);
    }
  });

  it('matches the spec hex values exactly', () => {
    expect(ATLAS_STATUS_COLORS.accepted).toBe('#22c55e');
    expect(ATLAS_STATUS_COLORS.caveat).toBe('#eab308');
    expect(ATLAS_STATUS_COLORS.constrain).toBe('#f97316');
    expect(ATLAS_STATUS_COLORS.suppress).toBe('#ef4444');
    // Wave 5.2: activeTrace shifted to teal-400 to match the production
    // noeticcompass.com accent. Previous value '#3b82f6' read as Web-2.0
    // bright blue and was the single biggest cartoonish color across the
    // cockpit (timeline highlights, tab underlines, selected cards).
    expect(ATLAS_STATUS_COLORS.activeTrace).toBe('#2dd4bf');
    expect(ATLAS_STATUS_COLORS.intervention).toBe('#a855f7');
    expect(ATLAS_STATUS_COLORS.unavailable).toBe('#6b7280');
  });
});

describe('FOUNDATION_HUES', () => {
  it('matches the canonical drive hue mapping', () => {
    expect(FOUNDATION_HUES[1]).toBe(220);
    expect(FOUNDATION_HUES[2]).toBe(280);
    expect(FOUNDATION_HUES[3]).toBe(30);
    expect(FOUNDATION_HUES[4]).toBe(160);
    expect(FOUNDATION_HUES[5]).toBe(60);
    expect(FOUNDATION_HUES[6]).toBe(200);
    expect(FOUNDATION_HUES[7]).toBe(320);
  });
});

describe('OKABE_ITO_FOUNDATION', () => {
  it('exposes a 7-char hex per drive', () => {
    for (const d of DRIVES) {
      expect(OKABE_ITO_FOUNDATION[d], `drive ${d}`).toMatch(HEX7);
    }
  });
});

describe('foundationColorForActivation', () => {
  it('returns a valid HSL string for every drive at activation 0/0.5/1', () => {
    for (const drive of DRIVES) {
      for (const a of [0, 0.5, 1]) {
        const out = foundationColorForActivation(drive, a);
        const match = HSL.exec(out);
        expect(match, `drive ${drive} a=${a} got "${out}"`).not.toBeNull();
        const [, h, s, l] = match!;
        expect(Number(h)).toBe(FOUNDATION_HUES[drive]);
        expect(Number(s)).toBeCloseTo(30 + 70 * a, 5);
        expect(Number(l)).toBe(55);
      }
    }
  });

  it('clamps L to [35, 75] across extreme margins', () => {
    for (const drive of DRIVES) {
      const high = foundationColorForActivation(drive, 0.5, 1000);
      const low = foundationColorForActivation(drive, 0.5, -1000);
      const lHigh = Number(HSL.exec(high)![3]);
      const lLow = Number(HSL.exec(low)![3]);
      expect(lHigh).toBe(35);
      expect(lLow).toBe(75);
    }
  });

  it('treats omitted margin as zero (L = 55)', () => {
    const out = foundationColorForActivation(1, 0.5);
    expect(Number(HSL.exec(out)![3])).toBe(55);
  });
});

describe('usePaletteMode', () => {
  it('default mode returns canonical FOUNDATION_HUES', () => {
    const p = usePaletteMode('default');
    expect(p.mode).toBe('default');
    expect(p.foundationHues).toEqual(FOUNDATION_HUES);
    expect(p.status).toBe(ATLAS_STATUS_COLORS);
    const out = p.foundationColor(3, 1);
    expect(out).toMatch(HSL);
    expect(Number(HSL.exec(out)![1])).toBe(FOUNDATION_HUES[3]);
  });

  it('okabe-ito mode swaps foundation hues but keeps status palette', () => {
    const p = usePaletteMode('okabe-ito');
    expect(p.mode).toBe('okabe-ito');
    expect(p.status).toBe(ATLAS_STATUS_COLORS);
    for (const d of DRIVES) {
      const out = p.foundationColor(d, 0.5);
      const match = HSL.exec(out);
      expect(match, `drive ${d}`).not.toBeNull();
      expect(Number(match![1])).toBe(p.foundationHues[d]);
    }
  });
});

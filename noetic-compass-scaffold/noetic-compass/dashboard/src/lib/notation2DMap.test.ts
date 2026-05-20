/**
 * Tests for `lib/notation2DMap.ts` — the TS adapter for the canonical
 * CAS notation 2D coordinate map. Stage 23.A.1.
 *
 * Pinning discipline:
 *   - All count assertions are COUNT-AGNOSTIC: they assert against the
 *     loaded JSON's own `primitives.length`, never a hardcoded number.
 *     This is intentional — Agent E may extend the canonical JSON
 *     (e.g. 12 Ω_* primitives) in parallel without breaking this suite.
 *   - Sample positions are pinned to coordinates that are stable across
 *     Stage 23.A and Stage 23.A.2, matching the Python source exactly.
 *   - Bare 'E' rejection mirrors the Python `get_position` guard.
 */

import { describe, it, expect } from 'vitest';
import canonicalLayout from '../../../research/cas_probe/stage23_a_notation_2d_layout_20260519.json';
import {
  allPositions,
  getPosition2D,
  layoutVersion,
  type Position2D,
  type PrimitiveKind,
  type CanonicalLayoutPayload,
} from './notation2DMap';

const payload = canonicalLayout as CanonicalLayoutPayload;

describe('notation2DMap — canonical JSON load', () => {
  it('loads the canonical layout payload with a populated primitives array', () => {
    expect(payload).toBeDefined();
    expect(payload.layout_version).toBeTypeOf('string');
    expect(Array.isArray(payload.primitives)).toBe(true);
    // Count-agnostic: the layout must be non-empty but we do not pin a
    // specific count here. The exact count is asserted against itself
    // in `allPositions returns one entry per canonical primitive`.
    expect(payload.primitives.length).toBeGreaterThan(0);
  });

  it('layoutVersion() returns the JSON layout_version string', () => {
    const v = layoutVersion();
    expect(v).toBe(payload.layout_version);
    expect(typeof v).toBe('string');
    expect(v.length).toBeGreaterThan(0);
  });
});

describe('notation2DMap — allPositions()', () => {
  it('returns one entry per canonical primitive (count-agnostic)', () => {
    const positions = allPositions();
    // The whole point: tied to the JSON's own length, not a fixed number.
    // Agent E may extend the canonical JSON without breaking this test.
    expect(positions.length).toBe(payload.primitives.length);
  });

  it('every returned entry has the Position2D shape', () => {
    const positions = allPositions();
    for (const p of positions) {
      expect(typeof p.primitive).toBe('string');
      expect(p.primitive.length).toBeGreaterThan(0);
      expect(typeof p.kind).toBe('string');
      expect(typeof p.x).toBe('number');
      expect(typeof p.y).toBe('number');
      expect(Number.isFinite(p.x)).toBe(true);
      expect(Number.isFinite(p.y)).toBe(true);
    }
  });

  it('every kind is a member of the PrimitiveKind union', () => {
    const validKinds: PrimitiveKind[] = [
      'noetic',
      'domain',
      'drive',
      'register',
      'cognitive_state',
      'operation',
      'inversion_axis',
      'foundation',
      'production',
      'rpm_pathway',
      'set_constructor',
      'set_relation',
      'set_operation',
      'combinator',
      'authority_set',
      'cardinality_kind',
    ];
    const validSet = new Set<string>(validKinds);
    for (const p of allPositions()) {
      expect(validSet.has(p.kind)).toBe(true);
    }
  });

  it('returns a fresh array each call (no shared mutable state)', () => {
    const first = allPositions();
    const second = allPositions();
    expect(first).not.toBe(second);
    expect(first.length).toBe(second.length);
  });
});

describe('notation2DMap — getPosition2D() sample lookups', () => {
  // These sample coordinates are stable across Stage 23.A and 23.A.2 and
  // any future extension that only adds primitives (per task brief).
  type Sample = {
    primitive: string;
    kind: PrimitiveKind;
    x: number;
    y: number;
  };

  const samples: Sample[] = [
    { primitive: '^0', kind: 'noetic',          x: 0,    y: 1    },
    { primitive: '^P', kind: 'domain',          x: 0,    y: -2   },
    { primitive: 'F4', kind: 'drive',           x: 0,    y: -1.5 },
    { primitive: '|T', kind: 'register',        x: -1.5, y: -6   },
    { primitive: '^3^P', kind: 'cognitive_state', x: 3,  y: 0.5 },
  ];

  for (const s of samples) {
    it(`returns the expected position for ${s.primitive} (${s.kind})`, () => {
      const pos = getPosition2D(s.primitive);
      expect(pos).not.toBeNull();
      // After non-null assertion guarded above:
      const p = pos as Position2D;
      expect(p.primitive).toBe(s.primitive);
      expect(p.kind).toBe(s.kind);
      expect(p.x).toBeCloseTo(s.x, 9);
      expect(p.y).toBeCloseTo(s.y, 9);
    });
  }

  it('returns null for an unknown primitive', () => {
    expect(getPosition2D('NotAPrimitive')).toBeNull();
    expect(getPosition2D('^Z')).toBeNull();
    expect(getPosition2D('')).toBeNull();
  });
});

describe('notation2DMap — bare E ambiguity guard', () => {
  it("throws a clear error when called with bare 'E'", () => {
    expect(() => getPosition2D('E')).toThrowError(/ambiguous/);
    // The error message must steer the caller to the disambiguated forms.
    expect(() => getPosition2D('E')).toThrowError(/\^E/);
    expect(() => getPosition2D('E')).toThrowError(/\|E/);
  });

  it("accepts the disambiguated '^E' (Domain) and '|E' (Register)", () => {
    const domE = getPosition2D('^E');
    expect(domE).not.toBeNull();
    expect((domE as Position2D).kind).toBe('domain');

    const regE = getPosition2D('|E');
    expect(regE).not.toBeNull();
    expect((regE as Position2D).kind).toBe('register');
  });
});

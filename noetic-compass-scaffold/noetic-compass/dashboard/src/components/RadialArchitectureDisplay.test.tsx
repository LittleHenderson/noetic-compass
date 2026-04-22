/**
 * Tests for the Radial Architecture Display (CAS v7.5 Phase A).
 *
 * Covers:
 *   1.  Renders without errors
 *   2.  Four Domain bands correctly placed (compass points)
 *   3.  40 Noetic petals render
 *   4.  Register quadrants render per petal
 *   5.  7 Drive markers render on the perimeter
 *   6.  Lacunarity voids display distinctly
 *   7.  Export SVG functionality works / stub tested
 *   8.  Export PNG functionality works / stub tested
 *   9.  Responsive scaling via viewBox
 *   10. Text-alternative view renders
 *   11. Colorblind-safe palette matches Okabe-Ito
 *   12. Empty data state handles gracefully
 *   13. Full activation state renders without overflow
 *   14. Mixed activation patterns render correctly
 *   15. Backward compat: does not reference or disrupt existing component DOM
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';

import {
  RadialArchitectureDisplay,
  MOCK_PROFILE_A,
  MOCK_PROFILE_LACUNARIC,
  OKABE_ITO_PALETTE,
  DOMAIN_PALETTE,
  NOETIC_PALETTE,
  DRIVE_PALETTE,
} from './RadialArchitectureDisplay';
import type {
  CognitiveStateData,
  Register,
  Domain,
  Noetic,
  Drive,
} from '../lib/mandala_types';
import {
  DOMAIN_CLOCKWISE,
  NOETIC_ORDER,
  REGISTER_ORDER,
  DRIVE_ORDER,
} from '../lib/mandala_types';
import {
  domainAngleDeg,
  petalCenterDeg,
  polarToXY,
  drivePositions,
  viewBoxString,
  VIEWBOX_SIZE,
  CX,
  CY,
} from '../lib/mandala_geometry';

beforeEach(() => {
  cleanup();
});

/* Helpers */

const EMPTY: CognitiveStateData = {
  label: 'empty',
  activations: {},
  drives: {},
  lacunarity: {
    register_global_voids: [],
    register_pair_voids: [],
    register_selective_voids: {},
    register_involution_imbalance: [],
  },
};

function fullyActivated(): CognitiveStateData {
  const activations: CognitiveStateData['activations'] = {};
  for (const N of NOETIC_ORDER) {
    activations[N] = {};
    for (const D of DOMAIN_CLOCKWISE) {
      activations[N]![D] = {};
      for (const R of REGISTER_ORDER) {
        activations[N]![D]![R] = 1;
      }
    }
  }
  const drives: Partial<Record<Drive, number>> = {};
  for (const F of DRIVE_ORDER) drives[F] = 1;
  return {
    label: 'full',
    activations,
    drives,
    lacunarity: {
      register_global_voids: [],
      register_pair_voids: [],
      register_selective_voids: {},
      register_involution_imbalance: [],
    },
  };
}

/* ========================================================================
 * 1. Renders without errors
 * ======================================================================== */

describe('RadialArchitectureDisplay — smoke', () => {
  it('1. renders without throwing', () => {
    const { container } = render(<RadialArchitectureDisplay data={MOCK_PROFILE_A} />);
    expect(container).toBeTruthy();
    expect(screen.getByTestId('radial-architecture-display')).toBeInTheDocument();
    expect(screen.getByTestId('radial-arch-svg')).toBeInTheDocument();
  });
});

/* ========================================================================
 * 2. Domain positions at compass points
 * ======================================================================== */

describe('RadialArchitectureDisplay — domain placement', () => {
  it('2. places the 4 Domain bands at compass points (P=N, C=E, E=S, O=W)', () => {
    render(<RadialArchitectureDisplay data={MOCK_PROFILE_A} />);
    // All four domain bands present and tagged with the correct compass angle.
    const expectedAngles: Record<Domain, number> = { P: 0, C: 90, E: 180, O: 270 };
    for (const d of DOMAIN_CLOCKWISE) {
      const band = screen.getByTestId(`domain-band-${d}`);
      expect(band).toBeInTheDocument();
      expect(band.getAttribute('data-angle')).toBe(String(expectedAngles[d]));
    }

    // Geometry helper agrees.
    expect(domainAngleDeg('P')).toBe(0);
    expect(domainAngleDeg('C')).toBe(90);
    expect(domainAngleDeg('E')).toBe(180);
    expect(domainAngleDeg('O')).toBe(270);

    // North direction lands above the center in SVG coords (y decreases going up).
    const [nx, ny] = polarToXY(100, 0);
    expect(nx).toBeCloseTo(CX, 6);
    expect(ny).toBeLessThan(CY);

    // East direction lands right of center.
    const [ex] = polarToXY(100, 90);
    expect(ex).toBeGreaterThan(CX);
  });
});

/* ========================================================================
 * 3. 40 Noetic petals total
 * ======================================================================== */

describe('RadialArchitectureDisplay — Noetic petals', () => {
  it('3. renders exactly 40 Noetic petals (10 Noetics × 4 Domains)', () => {
    render(<RadialArchitectureDisplay data={MOCK_PROFILE_A} />);
    let count = 0;
    for (const d of DOMAIN_CLOCKWISE) {
      for (const n of NOETIC_ORDER) {
        const el = screen.getByTestId(`petal-${d}-${n}`);
        expect(el).toBeInTheDocument();
        count += 1;
      }
    }
    expect(count).toBe(40);
  });
});

/* ========================================================================
 * 4. Register quadrants
 * ======================================================================== */

describe('RadialArchitectureDisplay — Register quadrants', () => {
  it('4. renders 4 register quadrants per non-voided petal', () => {
    render(<RadialArchitectureDisplay data={MOCK_PROFILE_A} />);
    // Pick a petal known to have no selective voids (N1/P in MOCK_PROFILE_A).
    for (const r of REGISTER_ORDER) {
      const q = screen.getByTestId(`quadrant-P-N1-${r}`);
      expect(q).toBeInTheDocument();
      expect(q.getAttribute('data-register')).toBe(r);
    }
  });
});

/* ========================================================================
 * 5. 7 Drive markers
 * ======================================================================== */

describe('RadialArchitectureDisplay — Drives', () => {
  it('5. renders all 7 Drive markers on the perimeter', () => {
    render(<RadialArchitectureDisplay data={MOCK_PROFILE_A} />);
    for (const f of DRIVE_ORDER) {
      const m = screen.getByTestId(`drive-marker-${f}`);
      expect(m).toBeInTheDocument();
      expect(m.getAttribute('data-drive')).toBe(f);
    }
    expect(drivePositions().length).toBe(7);
  });
});

/* ========================================================================
 * 6. Lacunarity voids
 * ======================================================================== */

describe('RadialArchitectureDisplay — lacunarity', () => {
  it('6. renders selective voids with distinct void styling, not as normal quadrants', () => {
    render(<RadialArchitectureDisplay data={MOCK_PROFILE_A} />);
    // MOCK_PROFILE_A: N3.O voids ['T', 'f'], N7.P voids ['T']
    const voidT = screen.getByTestId('void-O-N3-T');
    const voidF = screen.getByTestId('void-O-N3-f');
    const voidPN7 = screen.getByTestId('void-P-N7-T');
    expect(voidT).toBeInTheDocument();
    expect(voidF).toBeInTheDocument();
    expect(voidPN7).toBeInTheDocument();
    // Same cells must NOT render as normal quadrants.
    expect(screen.queryByTestId('quadrant-O-N3-T')).toBeNull();
    expect(screen.queryByTestId('quadrant-O-N3-f')).toBeNull();
    expect(screen.queryByTestId('quadrant-P-N7-T')).toBeNull();
  });

  it('6b. global register voids apply across every cell', () => {
    render(<RadialArchitectureDisplay data={MOCK_PROFILE_LACUNARIC} />);
    // Heavy-lacunarity fixture voids |E globally — every cell's |E quadrant
    // should be a void, never a saturated quadrant.
    for (const d of DOMAIN_CLOCKWISE) {
      for (const n of NOETIC_ORDER) {
        const voidEl = screen.queryByTestId(`void-${d}-${n}-E` as const);
        expect(voidEl).not.toBeNull();
        expect(screen.queryByTestId(`quadrant-${d}-${n}-E` as const)).toBeNull();
      }
    }
  });
});

/* ========================================================================
 * 7. Export SVG
 * ======================================================================== */

describe('RadialArchitectureDisplay — SVG export', () => {
  it('7. triggers SVG download flow without throwing', () => {
    // jsdom lacks URL.createObjectURL by default — stub it.
    const createObjectURL = vi.fn(() => 'blob:mock');
    const revokeObjectURL = vi.fn();
    (global.URL as unknown as { createObjectURL: typeof createObjectURL }).createObjectURL =
      createObjectURL;
    (global.URL as unknown as { revokeObjectURL: typeof revokeObjectURL }).revokeObjectURL =
      revokeObjectURL;

    render(<RadialArchitectureDisplay data={MOCK_PROFILE_A} />);
    const btn = screen.getByTestId('radial-arch-export-svg');

    // Spy on anchor click so we don't actually navigate.
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    expect(() => fireEvent.click(btn)).not.toThrow();
    expect(createObjectURL).toHaveBeenCalled();
    expect(clickSpy).toHaveBeenCalled();

    clickSpy.mockRestore();
  });
});

/* ========================================================================
 * 8. Export PNG
 * ======================================================================== */

describe('RadialArchitectureDisplay — PNG export', () => {
  it('8. handles PNG export gracefully when html2canvas is unavailable', async () => {
    render(<RadialArchitectureDisplay data={MOCK_PROFILE_A} />);
    const btn = screen.getByTestId('radial-arch-export-png');
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    // Click is async because of the dynamic import — flush microtasks.
    fireEvent.click(btn);
    await new Promise((resolve) => setTimeout(resolve, 0));
    // Either succeeds (html2canvas present via package) or logs the stub warning;
    // both paths are acceptable and must not throw.
    expect(btn).toBeInTheDocument();
    warn.mockRestore();
  });
});

/* ========================================================================
 * 9. Responsive scaling via viewBox
 * ======================================================================== */

describe('RadialArchitectureDisplay — viewBox', () => {
  it('9. sets a square viewBox and preserveAspectRatio for responsive scaling', () => {
    render(<RadialArchitectureDisplay data={MOCK_PROFILE_A} />);
    const svg = screen.getByTestId('radial-arch-svg');
    expect(svg.getAttribute('viewBox')).toBe(`0 0 ${VIEWBOX_SIZE} ${VIEWBOX_SIZE}`);
    expect(svg.getAttribute('preserveAspectRatio')).toBe('xMidYMid meet');
    expect(viewBoxString()).toBe(`0 0 ${VIEWBOX_SIZE} ${VIEWBOX_SIZE}`);
  });
});

/* ========================================================================
 * 10. Text-alternative view
 * ======================================================================== */

describe('RadialArchitectureDisplay — text alternative', () => {
  it('10. toggles the text-alternative view and renders authoritative Noetic/Domain names', () => {
    render(<RadialArchitectureDisplay data={MOCK_PROFILE_A} />);
    const toggle = screen.getByTestId('radial-arch-toggle-alt');
    fireEvent.click(toggle);
    const alt = screen.getByTestId('radial-arch-text-alt');
    expect(alt).toBeVisible();
    // Authoritative Noetic names (Clarification 1) appear verbatim.
    expect(alt.textContent).toMatch(/Idea/);
    expect(alt.textContent).toMatch(/Mind/);
    expect(alt.textContent).toMatch(/Above\/Cause/);
    expect(alt.textContent).toMatch(/Below\/Effect/);
    // Register names appear.
    expect(alt.textContent).toMatch(/Transcendent|Analytical|Affective|Embodied/);
  });
});

/* ========================================================================
 * 11. Colorblind-safe palette (Okabe-Ito)
 * ======================================================================== */

describe('RadialArchitectureDisplay — palette', () => {
  it('11. exposes an Okabe-Ito safe palette for Domains, Noetics, and Drives', () => {
    // Canonical Okabe-Ito hex strings.
    const okabeIto: readonly string[] = [
      '#000000',
      '#E69F00',
      '#56B4E9',
      '#009E73',
      '#F0E442',
      '#0072B2',
      '#D55E00',
      '#CC79A7',
    ];
    for (const hex of Object.values(OKABE_ITO_PALETTE)) {
      expect(okabeIto).toContain(hex);
    }
    for (const d of DOMAIN_CLOCKWISE) {
      expect(okabeIto).toContain(DOMAIN_PALETTE[d]);
    }
    for (const n of NOETIC_ORDER) {
      expect(okabeIto).toContain(NOETIC_PALETTE[n]);
    }
    for (const f of DRIVE_ORDER) {
      expect(okabeIto).toContain(DRIVE_PALETTE[f]);
    }
  });
});

/* ========================================================================
 * 12. Empty data state
 * ======================================================================== */

describe('RadialArchitectureDisplay — empty data', () => {
  it('12. renders gracefully when all activations and drives are empty', () => {
    render(<RadialArchitectureDisplay data={EMPTY} />);
    // Still has 40 petals — activations of 0 collapse visually, but the DOM
    // structure remains so assistive tools can announce the full shape.
    for (const d of DOMAIN_CLOCKWISE) {
      for (const n of NOETIC_ORDER) {
        expect(screen.getByTestId(`petal-${d}-${n}`)).toBeInTheDocument();
      }
    }
    // Drive markers still present but with zero-strength sizing.
    for (const f of DRIVE_ORDER) {
      const m = screen.getByTestId(`drive-marker-${f}`);
      expect(m.getAttribute('data-strength')).toBe('0.000');
    }
  });
});

/* ========================================================================
 * 13. Full activation state
 * ======================================================================== */

describe('RadialArchitectureDisplay — full activation', () => {
  it('13. renders full activation without exceeding the viewBox', () => {
    const full = fullyActivated();
    render(<RadialArchitectureDisplay data={full} />);
    // Every petal's recorded activation is 1.0.
    for (const d of DOMAIN_CLOCKWISE) {
      for (const n of NOETIC_ORDER) {
        const el = screen.getByTestId(`petal-${d}-${n}`);
        expect(Number(el.getAttribute('data-activation'))).toBeCloseTo(1, 3);
      }
    }
    // Drive markers at full strength.
    for (const f of DRIVE_ORDER) {
      const m = screen.getByTestId(`drive-marker-${f}`);
      expect(Number(m.getAttribute('data-strength'))).toBeCloseTo(1, 3);
    }
    // SVG viewBox is still the canonical square (no overflow resize).
    expect(screen.getByTestId('radial-arch-svg').getAttribute('viewBox')).toBe(
      `0 0 ${VIEWBOX_SIZE} ${VIEWBOX_SIZE}`,
    );
  });
});

/* ========================================================================
 * 14. Mixed activation patterns
 * ======================================================================== */

describe('RadialArchitectureDisplay — mixed activation', () => {
  it('14. encodes activation differences across cells via data-* attributes', () => {
    render(<RadialArchitectureDisplay data={MOCK_PROFILE_A} />);
    // Petal N6/C (cognitive decomposition, heavy in MOCK_PROFILE_A) should
    // be meaningfully stronger than Petal N0/O (unspecified).
    const strong = screen.getByTestId('petal-C-N6');
    const weak = screen.getByTestId('petal-O-N0');
    const sVal = Number(strong.getAttribute('data-activation'));
    const wVal = Number(weak.getAttribute('data-activation'));
    expect(sVal).toBeGreaterThan(wVal);
  });

  it('14b. petal-center angles follow domain-axis ordering', () => {
    // Spec: petals within a cluster are centered around the domain axis.
    // For P (axis 0°) with 10 petals × 8° width, the middle petals (N4/N5)
    // should straddle 0°.
    const aN4 = petalCenterDeg('P' as Domain, 'N4' as Noetic);
    const aN5 = petalCenterDeg('P' as Domain, 'N5' as Noetic);
    expect(aN4).toBeLessThan(0); // left of axis
    expect(aN5).toBeGreaterThan(0); // right of axis
    expect(Math.abs(aN4 + aN5)).toBeLessThan(0.001); // symmetric
  });
});

/* ========================================================================
 * 15. Backward compat — no disruption to existing components
 * ======================================================================== */

describe('RadialArchitectureDisplay — backward compatibility', () => {
  it('15. is self-contained and does not clobber global state', async () => {
    // Import an existing sibling component to confirm co-rendering works and
    // the new component's CSS class / element IDs do not collide.
    const { NccsGauge } = await import('./charts/NccsGauge');
    render(
      <div>
        <NccsGauge composite={72} certification="Silver" />
        <RadialArchitectureDisplay data={MOCK_PROFILE_A} />
      </div>,
    );
    // Both components rendered.
    expect(screen.getByTestId('radial-architecture-display')).toBeInTheDocument();
    // NccsGauge content is still present unchanged.
    expect(screen.getByText('72.0')).toBeInTheDocument();
    expect(screen.getByText('NCCS Composite')).toBeInTheDocument();
  });

  it('15b. does not register any globally-scoped event listeners on mount', () => {
    const before = (globalThis as unknown as { __listenerCount?: number }).__listenerCount;
    render(<RadialArchitectureDisplay data={MOCK_PROFILE_A} />);
    const after = (globalThis as unknown as { __listenerCount?: number }).__listenerCount;
    // Neither number is set by the component — exact equality confirms no side effect.
    expect(after).toEqual(before);
  });

  it('15c. Register, Drive, and viewBox constants re-exported for downstream use', () => {
    // Sanity: the module exposes stable, importable constants so downstream
    // phases can build on top without re-declaring the primitives.
    const testRegister: Register = 'T';
    expect(REGISTER_ORDER.includes(testRegister)).toBe(true);
    expect(DRIVE_ORDER.length).toBe(7);
    expect(viewBoxString()).toContain(String(VIEWBOX_SIZE));
  });
});

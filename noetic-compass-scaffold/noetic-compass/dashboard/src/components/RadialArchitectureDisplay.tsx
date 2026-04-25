/**
 * Radial Architecture Display — CAS v7.5 Phase A.
 *
 * Static (non-interactive) visualization of a Mind's cognitive state across
 * all four CAS axes (Noetic, Domain, Drive, Register). Renders as SVG at
 * 800x800 viewBox so it scales responsively to any container width while
 * remaining print-quality.
 *
 * PUBLIC NAMING DISCIPLINE: this component is named
 * `RadialArchitectureDisplay` and its user-facing text uses only
 * neutral/technical terms. Internal variable names ("petal", "ring",
 * "quadrant", "wedge") describe geometric primitives and are considered
 * acceptable for code-level naming.
 *
 * PHASE A SCOPE — STATIC ONLY:
 *   - no hover/click handlers on petals
 *   - no register-layer toggles
 *   - no composition tracing
 *   - no side-by-side comparison mode
 *   - keyboard navigation stubs only (focusable regions; no nav logic)
 *   - export buttons (SVG + PNG) are provided — stubbed gracefully if
 *     html2canvas is not available at runtime (e.g. jsdom in tests).
 */

import { useMemo, useRef, useState } from 'react';
import type {
  CognitiveStateData,
  Domain,
  Drive,
  Noetic,
  Register,
} from '../lib/mandala_types';
import {
  DOMAIN_CLOCKWISE,
  DOMAIN_NAMES,
  DRIVE_NAMES,
  DRIVE_ORDER,
  NOETIC_NAMES,
  NOETIC_ORDER,
  REGISTER_NAMES,
  REGISTER_ORDER,
} from '../lib/mandala_types';
import {
  CX,
  CY,
  R_CENTER,
  R_RING1_INNER,
  R_RING1_OUTER,
  R_RING2_OUTER,
  R_RING4,
  drivePositions,
  petalGeometry,
  petalQuadrants,
  polarToXY,
  viewBoxString,
} from '../lib/mandala_geometry';
import '../styles/mandala.css';

/* --------------------------------------------------------------------------
 * Colorblind-safe palette (Okabe-Ito).
 *
 * Okabe-Ito 8-color palette is deuteranopia-, protanopia-, and
 * tritanopia-distinguishable. We map the 4 Domains to four Okabe-Ito hues
 * and the 5 Noetic involution families (+ self-duals) by a stable
 * hash so distinct petals inside a cluster remain legibly separable
 * without requiring a 10-hue palette.
 *
 * Source: Okabe, M. & Ito, K. "Color Universal Design (CUD)".
 * -------------------------------------------------------------------------- */

export const OKABE_ITO_PALETTE = {
  black: '#000000',
  orange: '#E69F00',
  skyBlue: '#56B4E9',
  bluishGreen: '#009E73',
  yellow: '#F0E442',
  blue: '#0072B2',
  vermillion: '#D55E00',
  reddishPurple: '#CC79A7',
} as const;

/** Okabe-Ito mapping for the four Processing Domains. */
export const DOMAIN_PALETTE: Readonly<Record<Domain, string>> = {
  P: OKABE_ITO_PALETTE.blue,          // Principled — highest precedence
  C: OKABE_ITO_PALETTE.bluishGreen,   // Cognitive
  E: OKABE_ITO_PALETTE.orange,        // Evaluative
  O: OKABE_ITO_PALETTE.vermillion,    // Operational
} as const;

/** Ring brightness tier per Domain (P brightest → O most muted). */
export const DOMAIN_BRIGHTNESS: Readonly<Record<Domain, number>> = {
  P: 1.0,
  C: 0.85,
  E: 0.7,
  O: 0.55,
} as const;

/**
 * Noetic palette: involution pairs share a hue family.
 *   ^2/^3  — warm pair (orange / vermillion)
 *   ^5/^6  — cool pair  (sky blue / blue)
 *   ^8/^9  — green pair (bluish green / yellow)
 *   ^0, ^1, ^4, ^7 — self-duals, distinct neutral tones
 */
export const NOETIC_PALETTE: Readonly<Record<Noetic, string>> = {
  N0: OKABE_ITO_PALETTE.black,        // Idea (self-dual)
  N1: OKABE_ITO_PALETTE.reddishPurple, // Mind (self-dual)
  N2: OKABE_ITO_PALETTE.orange,       // Positive (warm pair)
  N3: OKABE_ITO_PALETTE.vermillion,   // Negative (warm pair)
  N4: OKABE_ITO_PALETTE.yellow,       // Vibration (self-dual)
  N5: OKABE_ITO_PALETTE.skyBlue,      // Female (cool pair)
  N6: OKABE_ITO_PALETTE.blue,         // Male (cool pair)
  N7: OKABE_ITO_PALETTE.reddishPurple, // Rhythm (self-dual)
  N8: OKABE_ITO_PALETTE.bluishGreen,  // Above/Cause (green pair)
  N9: OKABE_ITO_PALETTE.yellow,       // Below/Effect (green pair — distinct value)
} as const;

export const DRIVE_PALETTE: Readonly<Record<Drive, string>> = {
  F1: OKABE_ITO_PALETTE.blue,
  F2: OKABE_ITO_PALETTE.skyBlue,
  F3: OKABE_ITO_PALETTE.bluishGreen,
  F4: OKABE_ITO_PALETTE.yellow,
  F5: OKABE_ITO_PALETTE.orange,
  F6: OKABE_ITO_PALETTE.vermillion,
  F7: OKABE_ITO_PALETTE.reddishPurple,
} as const;

/* --------------------------------------------------------------------------
 * Helpers
 * -------------------------------------------------------------------------- */

function clamp01(x: number): number {
  if (!Number.isFinite(x)) return 0;
  if (x < 0) return 0;
  if (x > 1) return 1;
  return x;
}

function registerActivation(
  data: CognitiveStateData,
  noetic: Noetic,
  domain: Domain,
  register: Register,
): number {
  const v = data.activations?.[noetic]?.[domain]?.[register];
  return clamp01(typeof v === 'number' ? v : 0);
}

function cellActivation(
  data: CognitiveStateData,
  noetic: Noetic,
  domain: Domain,
): number {
  let s = 0;
  for (const r of REGISTER_ORDER) {
    s += registerActivation(data, noetic, domain, r);
  }
  // Average across 4 registers so a "full" cell = 1.0, not 4.0.
  return clamp01(s / REGISTER_ORDER.length);
}

function isCellVoided(
  data: CognitiveStateData,
  noetic: Noetic,
  domain: Domain,
  register: Register,
): boolean {
  if (data.lacunarity.register_global_voids.includes(register)) return true;
  const selective =
    data.lacunarity.register_selective_voids?.[noetic]?.[domain];
  if (selective && selective.includes(register)) return true;
  return false;
}

function aggregateIntensity(data: CognitiveStateData): number {
  let total = 0;
  let n = 0;
  for (const N of NOETIC_ORDER) {
    for (const D of DOMAIN_CLOCKWISE) {
      for (const R of REGISTER_ORDER) {
        total += registerActivation(data, N, D, R);
        n += 1;
      }
    }
  }
  return n === 0 ? 0 : total / n;
}

function hexToRgba(hex: string, alpha: number): string {
  const h = hex.replace('#', '');
  const full = h.length === 3
    ? h.split('').map((c) => c + c).join('')
    : h;
  const r = parseInt(full.slice(0, 2), 16);
  const g = parseInt(full.slice(2, 4), 16);
  const b = parseInt(full.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/* --------------------------------------------------------------------------
 * Component props
 * -------------------------------------------------------------------------- */

export interface RadialArchitectureDisplayProps {
  data: CognitiveStateData;
  /**
   * Optional visible heading. Does not appear on the SVG itself.
   */
  title?: string;
  /**
   * When true, renders the text-alternative view alongside the SVG for
   * assistive technology. Defaults to visually hidden (screen-reader only).
   */
  showTextAlternative?: boolean;
  /**
   * Optional className passed to the outer container.
   */
  className?: string;
  /**
   * Optional Domain highlight used by the Temporal Cognitive Score sync hook.
   */
  highlightDomain?: Domain | null;
}

/* --------------------------------------------------------------------------
 * Component
 * -------------------------------------------------------------------------- */

export function RadialArchitectureDisplay({
  data,
  title = 'Radial Architecture Display',
  showTextAlternative = false,
  className,
  highlightDomain = null,
}: RadialArchitectureDisplayProps) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [altVisible, setAltVisible] = useState<boolean>(showTextAlternative);

  const drives = useMemo(drivePositions, []);
  const intensity = useMemo(() => aggregateIntensity(data), [data]);

  /* ---------- Export handlers (stubbed if html2canvas unavailable) ---------- */

  const handleExportSvg = () => {
    if (!svgRef.current) return;
    try {
      const svg = svgRef.current;
      const serializer = new XMLSerializer();
      const source = serializer.serializeToString(svg);
      const blob = new Blob(
        ['<?xml version="1.0" encoding="UTF-8"?>\n', source],
        { type: 'image/svg+xml;charset=utf-8' },
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'radial-architecture-display.svg';
      a.rel = 'noopener';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('SVG export failed', err);
    }
  };

  const handleExportPng = async () => {
    // TODO (Phase B): integrate with existing `chartCapture` pipeline once
    // the component is registered in the hidden report charts container.
    if (!svgRef.current) return;
    try {
      const mod = await import('html2canvas').catch(() => null);
      if (!mod || typeof mod.default !== 'function') {
        // eslint-disable-next-line no-console
        console.warn('html2canvas unavailable; PNG export stubbed.');
        return;
      }
      const wrapper = svgRef.current.parentElement;
      if (!wrapper) return;
      const canvas = await mod.default(wrapper, { backgroundColor: null });
      const url = canvas.toDataURL('image/png');
      const a = document.createElement('a');
      a.href = url;
      a.download = 'radial-architecture-display.png';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('PNG export failed', err);
    }
  };

  /* ---------- Render: Domain ring (Ring 1) ---------- */
  const ring1 = DOMAIN_CLOCKWISE.map((domain) => {
    const angleDeg = DOMAIN_CLOCKWISE.indexOf(domain) * 90;
    const [lx, ly] = polarToXY((R_RING1_INNER + R_RING1_OUTER) / 2, angleDeg);
    const color = DOMAIN_PALETTE[domain];
    const brightness = DOMAIN_BRIGHTNESS[domain];
    return { domain, angleDeg, lx, ly, color, brightness };
  });

  /* ---------- Render: Noetic petals (Ring 2) + Register quadrants (Ring 3) ---------- */

  type PetalRender = {
    key: string;
    domain: Domain;
    noetic: Noetic;
    activation: number;
    wedgePath: string;
    baseColor: string;
    brightness: number;
    quadrants: {
      register: Register;
      path: string;
      saturation: number;
      voided: boolean;
    }[];
  };

  const petals: PetalRender[] = [];
  for (const domain of DOMAIN_CLOCKWISE) {
    for (const noetic of NOETIC_ORDER) {
      const activation = cellActivation(data, noetic, domain);
      const { wedgePath } = petalGeometry(domain, noetic, activation);
      const quadGeom = petalQuadrants(domain, noetic, Math.max(activation, 0.15));
      const quadrants = quadGeom.map((q) => ({
        register: q.register,
        path: q.path,
        saturation: registerActivation(data, noetic, domain, q.register),
        voided: isCellVoided(data, noetic, domain, q.register),
      }));
      petals.push({
        key: `${domain}-${noetic}`,
        domain,
        noetic,
        activation,
        wedgePath,
        baseColor: NOETIC_PALETTE[noetic],
        brightness: DOMAIN_BRIGHTNESS[domain],
        quadrants,
      });
    }
  }

  /* ---------- Render: Drive markers (Ring 4) ---------- */

  const driveMarkers = drives.map((d) => {
    const strength = clamp01(data.drives?.[d.drive] ?? 0);
    return {
      ...d,
      strength,
      color: DRIVE_PALETTE[d.drive],
      labelPos: polarToXY(R_RING4 + 24, d.angleDeg),
    };
  });

  /* ---------- Text-alternative view ---------- */

  const textAltId = 'radial-arch-alt';
  const labelId = 'radial-arch-label';

  return (
    <div
      className={`radial-architecture-display${className ? ` ${className}` : ''}`}
      data-testid="radial-architecture-display"
      data-active-domain={highlightDomain ?? 'none'}
    >
      <div className="radial-architecture-display__header">
        <h3 id={labelId} className="radial-architecture-display__title">
          {title}
          {data.label ? ` — ${data.label}` : ''}
        </h3>
        <div className="radial-architecture-display__actions">
          <button
            type="button"
            className="radial-architecture-display__button"
            onClick={() => setAltVisible((v) => !v)}
            aria-expanded={altVisible}
            aria-controls={textAltId}
            data-testid="radial-arch-toggle-alt"
          >
            {altVisible ? 'Hide text view' : 'Show text view'}
          </button>
          <button
            type="button"
            className="radial-architecture-display__button"
            onClick={handleExportSvg}
            data-testid="radial-arch-export-svg"
          >
            Export SVG
          </button>
          <button
            type="button"
            className="radial-architecture-display__button"
            onClick={handleExportPng}
            data-testid="radial-arch-export-png"
          >
            Export PNG
          </button>
        </div>
      </div>

      <svg
        ref={svgRef}
        className="radial-architecture-display__svg"
        viewBox={viewBoxString()}
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-labelledby={labelId}
        aria-describedby={altVisible ? textAltId : undefined}
        tabIndex={0}
        data-testid="radial-arch-svg"
      >
        <title>{title}</title>
        <desc>
          Four-ring radial architecture display rendering 10 Noetics × 4 Domains ×
          4 Registers with 7 Drive markers on the perimeter.
        </desc>

        {/* Ring 1: Domain band with per-domain brightness gradient */}
        {ring1.map((r) => {
          const startAngle = r.angleDeg - 45;
          const endAngle = r.angleDeg + 45;
          const [x1, y1] = polarToXY(R_RING1_INNER, startAngle);
          const [x2, y2] = polarToXY(R_RING1_OUTER, startAngle);
          const [x3, y3] = polarToXY(R_RING1_OUTER, endAngle);
          const [x4, y4] = polarToXY(R_RING1_INNER, endAngle);
          const d = [
            `M ${x1} ${y1}`,
            `L ${x2} ${y2}`,
            `A ${R_RING1_OUTER} ${R_RING1_OUTER} 0 0 1 ${x3} ${y3}`,
            `L ${x4} ${y4}`,
            `A ${R_RING1_INNER} ${R_RING1_INNER} 0 0 0 ${x1} ${y1}`,
            'Z',
          ].join(' ');
          return (
            <g
              key={`domain-${r.domain}`}
              className={`radial-architecture-display__domain-band${
                highlightDomain === r.domain ? ' radial-architecture-display__domain-band--active' : ''
              }`}
              data-testid={`domain-band-${r.domain}`}
              data-domain={r.domain}
              data-angle={r.angleDeg}
            >
              <path d={d} fill={hexToRgba(r.color, 0.25 + 0.25 * r.brightness)} />
              <text
                x={r.lx}
                y={r.ly}
                className="radial-architecture-display__domain-label"
              >
                {r.domain}
              </text>
            </g>
          );
        })}

        {/* Ring 2 / Ring 3: petals and register quadrants */}
        <g data-testid="petals-group">
          {petals.map((p) => (
            <g
              key={p.key}
              data-testid={`petal-${p.domain}-${p.noetic}`}
              data-domain={p.domain}
              data-noetic={p.noetic}
              data-activation={p.activation.toFixed(3)}
              tabIndex={-1}
            >
              <path
                d={p.wedgePath}
                className="radial-architecture-display__petal"
                fill={hexToRgba(p.baseColor, 0.12 + 0.28 * p.brightness)}
              />
              {p.quadrants.map((q) => {
                if (q.voided) {
                  return (
                    <path
                      key={`${p.key}-${q.register}`}
                      d={q.path}
                      className="radial-architecture-display__void"
                      data-testid={`void-${p.domain}-${p.noetic}-${q.register}`}
                      data-register={q.register}
                      data-void="true"
                    />
                  );
                }
                return (
                  <path
                    key={`${p.key}-${q.register}`}
                    d={q.path}
                    className="radial-architecture-display__quadrant"
                    data-testid={`quadrant-${p.domain}-${p.noetic}-${q.register}`}
                    data-register={q.register}
                    data-saturation={q.saturation.toFixed(3)}
                    fill={hexToRgba(
                      p.baseColor,
                      0.15 + 0.8 * clamp01(q.saturation) * p.brightness,
                    )}
                  />
                );
              })}
            </g>
          ))}
        </g>

        {/* Ring 4: Drive markers on the perimeter */}
        <g data-testid="drives-group">
          {driveMarkers.map((d) => (
            <g
              key={`drive-${d.drive}`}
              className="radial-architecture-display__drive-marker"
              data-testid={`drive-marker-${d.drive}`}
              data-drive={d.drive}
              data-strength={d.strength.toFixed(3)}
            >
              <circle
                cx={d.x}
                cy={d.y}
                r={6 + 8 * d.strength}
                fill={hexToRgba(d.color, 0.35 + 0.55 * d.strength)}
              />
              <text
                x={d.labelPos[0]}
                y={d.labelPos[1]}
                className="radial-architecture-display__drive-label"
              >
                {d.drive}
              </text>
            </g>
          ))}
        </g>

        {/* Central emergent-activation glyph */}
        <g data-testid="center-glyph" data-intensity={intensity.toFixed(3)}>
          <circle
            cx={CX}
            cy={CY}
            r={R_CENTER * 0.85}
            className="radial-architecture-display__center-glyph"
            fill={hexToRgba('#F1F5F9', 0.04 + 0.2 * intensity)}
          />
          {/* Inner cross-axis summary: four petals at compass points sized by domain-avg */}
          {DOMAIN_CLOCKWISE.map((dom) => {
            let sum = 0;
            for (const N of NOETIC_ORDER) {
              for (const R of REGISTER_ORDER) {
                sum += registerActivation(data, N, dom, R);
              }
            }
            const avg = clamp01(sum / (NOETIC_ORDER.length * REGISTER_ORDER.length));
            const angleDeg = DOMAIN_CLOCKWISE.indexOf(dom) * 90;
            const [x, y] = polarToXY(R_CENTER * 0.55 * avg, angleDeg);
            return (
              <circle
                key={`center-${dom}`}
                cx={x}
                cy={y}
                r={4 + 10 * avg}
                fill={hexToRgba(DOMAIN_PALETTE[dom], 0.6)}
                data-testid={`center-dot-${dom}`}
              />
            );
          })}
        </g>

        {/* Max-radius guide (informational; helps downstream export scaling) */}
        <circle
          cx={CX}
          cy={CY}
          r={R_RING2_OUTER}
          fill="none"
          stroke="rgba(148,163,184,0.08)"
          strokeWidth={0.5}
          aria-hidden="true"
        />
      </svg>

      <div
        id={textAltId}
        className="radial-architecture-display__text-alt"
        data-testid="radial-arch-text-alt"
        role="region"
        aria-labelledby={labelId}
        style={altVisible ? undefined : { display: 'none' }}
      >
        <TextAlternative data={data} />
      </div>

      <span className="radial-architecture-display__sr-only">
        Radial architecture display rendering {NOETIC_ORDER.length} Noetics across{' '}
        {DOMAIN_CLOCKWISE.length} Domains and {REGISTER_ORDER.length} Registers with{' '}
        {DRIVE_ORDER.length} Drive markers.
      </span>
    </div>
  );
}

/* --------------------------------------------------------------------------
 * Text-alternative (accessibility fallback)
 * -------------------------------------------------------------------------- */

function TextAlternative({ data }: { data: CognitiveStateData }) {
  return (
    <div>
      <h4>Domains</h4>
      <ul>
        {DOMAIN_CLOCKWISE.map((d) => (
          <li key={d}>
            <strong>{d}</strong> — {DOMAIN_NAMES[d]}
          </li>
        ))}
      </ul>

      <h4>Registers</h4>
      <ul>
        {REGISTER_ORDER.map((r) => (
          <li key={r}>
            <strong>|{r}</strong> — {REGISTER_NAMES[r]}
          </li>
        ))}
      </ul>

      <h4>Noetic × Domain activations (averaged across registers)</h4>
      <ul>
        {NOETIC_ORDER.map((n) => (
          <li key={n}>
            <strong>
              ^{n.slice(1)} {NOETIC_NAMES[n]}
            </strong>
            :{' '}
            {DOMAIN_CLOCKWISE.map((d) => {
              let s = 0;
              for (const r of REGISTER_ORDER) {
                s += clamp01(data.activations?.[n]?.[d]?.[r] ?? 0);
              }
              return `${d}=${(s / REGISTER_ORDER.length).toFixed(2)}`;
            }).join('  ')}
          </li>
        ))}
      </ul>

      <h4>Drives</h4>
      <ul>
        {DRIVE_ORDER.map((f) => (
          <li key={f}>
            <strong>{f}</strong> {DRIVE_NAMES[f]} = {(data.drives?.[f] ?? 0).toFixed(2)}
          </li>
        ))}
      </ul>

      <h4>Lacunarity</h4>
      <ul>
        <li>
          Global register voids:{' '}
          {data.lacunarity.register_global_voids.length === 0
            ? '(none)'
            : data.lacunarity.register_global_voids
                .map((r) => `|${r} ${REGISTER_NAMES[r]}`)
                .join(', ')}
        </li>
        <li>
          Register pair voids:{' '}
          {data.lacunarity.register_pair_voids.length === 0
            ? '(none)'
            : data.lacunarity.register_pair_voids
                .map(([a, b]) => `|${a}↔|${b}`)
                .join(', ')}
        </li>
        <li>
          Register involution imbalance:{' '}
          {data.lacunarity.register_involution_imbalance.length === 0
            ? '(none)'
            : data.lacunarity.register_involution_imbalance
                .map(([a, b]) => `|${a}↔|${b}`)
                .join(', ')}
        </li>
      </ul>
    </div>
  );
}

/* --------------------------------------------------------------------------
 * Mock fixtures (for storybook / demo / tests)
 * -------------------------------------------------------------------------- */

/**
 * Representative profile with moderate activations across all axes.
 * Useful as a development preview and as a baseline test fixture.
 */
export const MOCK_PROFILE_A: CognitiveStateData = {
  label: 'Profile A (balanced)',
  activations: {
    N0: { P: { T: 0.6, A: 0.4, f: 0.3, E: 0.2 }, C: { A: 0.5, f: 0.3 } },
    N1: { P: { A: 0.7, T: 0.4 }, C: { A: 0.8, f: 0.4 }, E: { A: 0.5 } },
    N2: { P: { f: 0.7, T: 0.3 }, C: { f: 0.4 }, E: { f: 0.6 } },
    N3: { P: { A: 0.5, f: 0.2 }, E: { f: 0.4 } },
    N4: { P: { T: 0.5 }, C: { f: 0.4 }, O: { E: 0.5 } },
    N5: { P: { T: 0.6, f: 0.5 }, C: { T: 0.4 }, E: { f: 0.3 }, O: { E: 0.5 } },
    N6: { P: { A: 0.7 }, C: { A: 0.8 }, E: { A: 0.6 }, O: { A: 0.3 } },
    N7: { O: { E: 0.6 }, C: { A: 0.3 } },
    N8: { P: { A: 0.5, T: 0.4 }, C: { A: 0.5 } },
    N9: { E: { f: 0.4 }, O: { E: 0.5 } },
  },
  drives: { F1: 0.4, F2: 0.7, F3: 0.5, F4: 0.6, F5: 0.4, F6: 0.55, F7: 0.5 },
  lacunarity: {
    register_global_voids: [],
    register_pair_voids: [],
    register_selective_voids: {
      N3: { O: ['T', 'f'] },
      N7: { P: ['T'] },
    },
    register_involution_imbalance: [['T', 'E']],
  },
};

/**
 * Heavy-lacunarity fixture: several global + selective voids, an involution
 * pair void, and depressed activations across the Embodied register.
 */
export const MOCK_PROFILE_LACUNARIC: CognitiveStateData = {
  label: 'Profile B (heavy lacunarity)',
  activations: {
    N0: { P: { A: 0.4 } },
    N1: { P: { A: 0.5 }, C: { A: 0.6 } },
    N5: { P: { T: 0.3 }, C: { T: 0.2 } },
    N6: { P: { A: 0.7 } },
    N8: { P: { A: 0.4 } },
  },
  drives: { F1: 0.2, F2: 0.6, F3: 0.15, F4: 0.25, F5: 0.2, F6: 0.55, F7: 0.1 },
  lacunarity: {
    register_global_voids: ['E'], // Embodied absent globally
    register_pair_voids: [['T', 'E']],
    register_selective_voids: {
      N2: { P: ['f'], C: ['f'], E: ['f'], O: ['f'] },
      N3: { P: ['A'], C: ['A'] },
    },
    register_involution_imbalance: [['T', 'E'], ['A', 'f']],
  },
};

export default RadialArchitectureDisplay;

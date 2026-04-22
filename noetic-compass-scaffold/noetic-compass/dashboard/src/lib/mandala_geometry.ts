/**
 * Pure geometric helpers for the Radial Architecture Display.
 *
 * The display is a four-ring concentric layout built inside an SVG viewBox of
 * `VIEWBOX_SIZE` × `VIEWBOX_SIZE`, centered at (CX, CY):
 *
 *   Ring 1 — four Domain positions at compass points (P/N, C/E, E/S, O/W)
 *   Ring 2 — ten Noetic petals radiating from each Domain position (40 total)
 *   Ring 3 — each petal divided into four Register quadrants (T/A/f/E)
 *   Ring 4 — seven Drive markers around the outer perimeter
 *
 * All functions here are pure — no React, no DOM. Tested independently.
 */

import type { Domain, Noetic, Register, Drive } from './mandala_types';
import {
  DOMAIN_CLOCKWISE,
  NOETIC_ORDER,
  REGISTER_ORDER,
  DRIVE_ORDER,
} from './mandala_types';

/** Viewbox dimensions. The display is always rendered in a square viewBox. */
export const VIEWBOX_SIZE = 800;
export const CX = VIEWBOX_SIZE / 2;
export const CY = VIEWBOX_SIZE / 2;

/** Ring radii (from center outward). */
export const R_CENTER = 60;      // emergent activation glyph radius (max)
export const R_RING1_INNER = 70; // Ring 1 inner (domain band)
export const R_RING1_OUTER = 110;
export const R_RING2_INNER = 120; // petal root
export const R_RING2_OUTER = 300; // max petal tip reach
export const R_RING4 = 340;       // drive marker radius

/**
 * Domain angle in degrees, measured clockwise from 12 o'clock (North = 0°).
 * P=North(0°), C=East(90°), E=South(180°), O=West(270°).
 *
 * (SVG y-axis points down, so we convert to SVG coordinates via `polarToXY`.)
 */
export function domainAngleDeg(domain: Domain): number {
  const idx = DOMAIN_CLOCKWISE.indexOf(domain);
  if (idx < 0) {
    throw new Error(`Unknown domain: ${domain}`);
  }
  return idx * 90; // 0, 90, 180, 270
}

/**
 * Angular width (in degrees) of the 10-petal cluster for a single Domain.
 * Clusters are 80° wide (10° gap between adjacent Domains).
 */
export const CLUSTER_ARC_DEG = 80;
export const PETAL_ARC_DEG = CLUSTER_ARC_DEG / NOETIC_ORDER.length; // 8°

/**
 * Compute the center-angle (in degrees, clockwise from North) of the petal
 * at (domain, noetic).
 */
export function petalCenterDeg(domain: Domain, noetic: Noetic): number {
  const dCenter = domainAngleDeg(domain);
  const nIdx = NOETIC_ORDER.indexOf(noetic);
  // Petal indices are centered on the domain axis: the 5.5-th petal sits on the axis.
  const halfCluster = CLUSTER_ARC_DEG / 2;
  const offset = -halfCluster + (nIdx + 0.5) * PETAL_ARC_DEG;
  return dCenter + offset;
}

/**
 * Convert polar (radius, angle in degrees measured clockwise from North)
 * to SVG cartesian coordinates. Returns [x, y].
 *
 * In SVG, y increases downward. North (top of screen) is (cx, cy - r).
 */
export function polarToXY(
  r: number,
  angleDeg: number,
  cx: number = CX,
  cy: number = CY,
): [number, number] {
  // Shift so 0° = up; convert to radians
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)];
}

export interface PetalGeometry {
  /** Clockwise angle (degrees from North) of the petal's axis of symmetry. */
  centerDeg: number;
  /** Inner radius where the petal attaches to Ring 2. */
  rInner: number;
  /** Outer radius of the petal tip for this activation strength. */
  rOuter: number;
  /** Angular half-width of the petal in degrees. */
  halfArcDeg: number;
  /** SVG `d` path for the petal wedge (pie-slice shape). */
  wedgePath: string;
}

/**
 * Build the SVG path for a petal wedge given a normalized activation strength
 * `activation` in [0, 1]. Activation encodes petal length: 0 collapses to the
 * inner radius, 1 reaches `R_RING2_OUTER`.
 */
export function petalGeometry(
  domain: Domain,
  noetic: Noetic,
  activation: number,
): PetalGeometry {
  const clamped = Math.max(0, Math.min(1, activation));
  const centerDeg = petalCenterDeg(domain, noetic);
  const halfArcDeg = PETAL_ARC_DEG / 2 - 0.5; // visual gap between petals

  const rInner = R_RING2_INNER;
  const rOuter = R_RING2_INNER + clamped * (R_RING2_OUTER - R_RING2_INNER);

  const [x1, y1] = polarToXY(rInner, centerDeg - halfArcDeg);
  const [x2, y2] = polarToXY(rOuter, centerDeg - halfArcDeg);
  const [x3, y3] = polarToXY(rOuter, centerDeg + halfArcDeg);
  const [x4, y4] = polarToXY(rInner, centerDeg + halfArcDeg);

  // Use elliptical arcs (arc flag 0 = small arc, sweep 1 = clockwise).
  const wedgePath = [
    `M ${x1.toFixed(2)} ${y1.toFixed(2)}`,
    `L ${x2.toFixed(2)} ${y2.toFixed(2)}`,
    `A ${rOuter.toFixed(2)} ${rOuter.toFixed(2)} 0 0 1 ${x3.toFixed(2)} ${y3.toFixed(2)}`,
    `L ${x4.toFixed(2)} ${y4.toFixed(2)}`,
    `A ${rInner.toFixed(2)} ${rInner.toFixed(2)} 0 0 0 ${x1.toFixed(2)} ${y1.toFixed(2)}`,
    'Z',
  ].join(' ');

  return { centerDeg, rInner, rOuter, halfArcDeg, wedgePath };
}

export interface QuadrantGeometry {
  /** Which register this quadrant represents. */
  register: Register;
  /** Center position (for saturation dot / marker rendering). */
  cx: number;
  cy: number;
  /** SVG path for the quadrant (small wedge inside the petal). */
  path: string;
}

/**
 * Build the four Register quadrant sub-wedges for a petal.
 *
 * Layout follows v7.5 PART 1 Ring 3:
 *   |T (Transcendent) occupies the OUTER third of the petal.
 *   |A (Analytical)   occupies the RIGHT side of the middle third.
 *   |f (Affective)    occupies the INNER third.
 *   |E (Embodied)     occupies the LEFT side of the middle third.
 *
 * Involution pairs sit on opposite sides: |T↔|E outer↔inner (conceptually), |A↔|f right↔left.
 *
 * For Phase A we place the four quadrants as concentric sub-bands so rendering
 * is simple and deterministic:
 *   - |f (inner band)
 *   - |E (middle-left sub-band)
 *   - |A (middle-right sub-band)
 *   - |T (outer band)
 */
export function petalQuadrants(
  domain: Domain,
  noetic: Noetic,
  activation: number,
): QuadrantGeometry[] {
  const clamped = Math.max(0, Math.min(1, activation));
  const centerDeg = petalCenterDeg(domain, noetic);
  const halfArcDeg = PETAL_ARC_DEG / 2 - 0.5;
  const rBase = R_RING2_INNER;
  const rTip = R_RING2_INNER + clamped * (R_RING2_OUTER - R_RING2_INNER);
  const span = rTip - rBase;

  // Four bands of equal radial extent.
  // Order from inner to outer: f, A, E, T   (pair |T↔|E bookending; |A↔|f bookending inside)
  // We place |A and |E at matching radial distance but on left/right halves
  // (angular split). This preserves the "right=|A, left=|E" meaning while
  // keeping geometry predictable for SVG.
  const bandCount = 4;
  const step = span / bandCount;

  const buildRingWedge = (
    rIn: number,
    rOut: number,
    aStart: number,
    aEnd: number,
  ): string => {
    const [x1, y1] = polarToXY(rIn, aStart);
    const [x2, y2] = polarToXY(rOut, aStart);
    const [x3, y3] = polarToXY(rOut, aEnd);
    const [x4, y4] = polarToXY(rIn, aEnd);
    return [
      `M ${x1.toFixed(2)} ${y1.toFixed(2)}`,
      `L ${x2.toFixed(2)} ${y2.toFixed(2)}`,
      `A ${rOut.toFixed(2)} ${rOut.toFixed(2)} 0 0 1 ${x3.toFixed(2)} ${y3.toFixed(2)}`,
      `L ${x4.toFixed(2)} ${y4.toFixed(2)}`,
      `A ${rIn.toFixed(2)} ${rIn.toFixed(2)} 0 0 0 ${x1.toFixed(2)} ${y1.toFixed(2)}`,
      'Z',
    ].join(' ');
  };

  const out: QuadrantGeometry[] = [];

  // Inner band |f — full arc width
  {
    const r0 = rBase;
    const r1 = rBase + step;
    const [cx, cy] = polarToXY((r0 + r1) / 2, centerDeg);
    out.push({
      register: 'f',
      cx,
      cy,
      path: buildRingWedge(r0, r1, centerDeg - halfArcDeg, centerDeg + halfArcDeg),
    });
  }

  // Middle-left band |E — left half of middle sub-band
  {
    const r0 = rBase + step;
    const r1 = rBase + 2 * step;
    const [cx, cy] = polarToXY((r0 + r1) / 2, centerDeg - halfArcDeg / 2);
    out.push({
      register: 'E',
      cx,
      cy,
      path: buildRingWedge(r0, r1, centerDeg - halfArcDeg, centerDeg),
    });
  }

  // Middle-right band |A — right half of middle sub-band
  {
    const r0 = rBase + 2 * step;
    const r1 = rBase + 3 * step;
    const [cx, cy] = polarToXY((r0 + r1) / 2, centerDeg + halfArcDeg / 2);
    out.push({
      register: 'A',
      cx,
      cy,
      path: buildRingWedge(r0, r1, centerDeg, centerDeg + halfArcDeg),
    });
  }

  // Outer band |T — full arc width at tip
  {
    const r0 = rBase + 3 * step;
    const r1 = rBase + 4 * step;
    const [cx, cy] = polarToXY((r0 + r1) / 2, centerDeg);
    out.push({
      register: 'T',
      cx,
      cy,
      path: buildRingWedge(r0, r1, centerDeg - halfArcDeg, centerDeg + halfArcDeg),
    });
  }

  return out;
}

/**
 * Clamp to the REGISTER_ORDER canonical ordering for test assertions.
 * Used internally; exported so tests can verify order independence.
 */
export function sortedQuadrantsByRegister(qs: QuadrantGeometry[]): QuadrantGeometry[] {
  return [...qs].sort(
    (a, b) =>
      REGISTER_ORDER.indexOf(a.register) - REGISTER_ORDER.indexOf(b.register),
  );
}

export interface DrivePosition {
  drive: Drive;
  angleDeg: number;
  x: number;
  y: number;
}

/**
 * Compute the seven Drive marker positions on Ring 4.
 *
 * Drives are spaced evenly around the perimeter, but we start the F1 marker
 * between the P/O boundary (i.e. NNW) so the placement reads like a clock.
 */
export function drivePositions(): DrivePosition[] {
  const n = DRIVE_ORDER.length;
  const startDeg = -90; // F1 sits near NNW (top-left quadrant)
  const step = 360 / n;
  return DRIVE_ORDER.map((drive, i) => {
    const angleDeg = (startDeg + i * step + 360) % 360;
    const [x, y] = polarToXY(R_RING4, angleDeg);
    return { drive, angleDeg, x, y };
  });
}

/** Bounds for the square viewBox string. */
export function viewBoxString(): string {
  return `0 0 ${VIEWBOX_SIZE} ${VIEWBOX_SIZE}`;
}

/**
 * Notation2DView — interactive 2D scatter of the canonical 169-primitive
 * notation map. Stage 23.A.1.2.
 *
 * Renders every primitive returned by `allPositions()` at its canonical
 * (x, y) coordinate, color-coded by PrimitiveKind. Hover surfaces the
 * primitive name, kind, and exact coordinates. Optional click handler
 * lets parent components react to selection.
 *
 * Direct proof that the canonical Python source of truth
 * (`cas-native/atlas/notation_2d_map.py`) feeds the dashboard UI:
 *   - Imports `getPosition2D`, `allPositions`, `colorForKind` from the
 *     adapter — no copy of positions, no copy of palette.
 *   - Renders exactly `allPositions().length` circles — count-agnostic;
 *     if the canonical JSON grows in a future stage, this view picks
 *     up the new primitives automatically.
 *   - Auto-fits viewport to data extent so layout changes don't crop.
 *
 * Self-contained: only deps are React + the adapter. No Three.js, no
 * external charting library, no global CSS — inline styles only so the
 * component drops into any page without setup.
 */
import { useMemo, useState } from 'react';

import {
  allPositions,
  colorForKind,
  layoutVersion,
  type Position2D,
  type PrimitiveKind,
} from '../../lib/notation2DMap';

export interface Notation2DViewProps {
  /** Pixel width of the SVG canvas. Default: 900. */
  width?: number;
  /** Pixel height of the SVG canvas. Default: 600. */
  height?: number;
  /** Optional click handler — called with the clicked primitive. */
  onSelectPrimitive?: (p: Position2D) => void;
  /** Optional padding (in data-space units) around the data extent. Default: 1. */
  padding?: number;
  /**
   * When true, render a text label next to Noetics (10) and Domains (4)
   * to make the map's axes self-orienting. The remaining 155 primitives
   * stay unlabeled — labeling all 169 would overlap badly.
   * Default: false.
   */
  showLabels?: boolean;
  /**
   * When set, render only primitives of this kind. Footer text becomes
   * "N of M primitives" so the viewer always sees the filter applied.
   * Useful for stakeholder questions like "show me just the Foundations."
   * Default: undefined (render all).
   */
  filterKind?: PrimitiveKind;
}

/** Kinds that get auto-labeled when `showLabels` is true. */
const AUTO_LABELED_KINDS: ReadonlySet<PrimitiveKind> = new Set([
  'noetic',
  'domain',
]);

interface Viewport {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

function computeViewport(positions: Position2D[], padding: number): Viewport {
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const p of positions) {
    if (p.x < minX) minX = p.x;
    if (p.x > maxX) maxX = p.x;
    if (p.y < minY) minY = p.y;
    if (p.y > maxY) maxY = p.y;
  }
  return {
    minX: minX - padding,
    maxX: maxX + padding,
    minY: minY - padding,
    maxY: maxY + padding,
  };
}

export function Notation2DView({
  width = 900,
  height = 600,
  onSelectPrimitive,
  padding = 1,
  showLabels = false,
  filterKind,
}: Notation2DViewProps) {
  const allPos = useMemo(() => allPositions(), []);
  const positions = useMemo(
    () => (filterKind ? allPos.filter((p) => p.kind === filterKind) : allPos),
    [allPos, filterKind],
  );
  // Viewport fits to the FULL layout extent (not just the filtered subset),
  // so toggling filter doesn't reflow positions — primitives stay where the
  // viewer last saw them and just appear/disappear in place.
  const viewport = useMemo(() => computeViewport(allPos, padding), [allPos, padding]);
  const [hovered, setHovered] = useState<Position2D | null>(null);

  const scaleX = (x: number) =>
    ((x - viewport.minX) / (viewport.maxX - viewport.minX)) * width;
  // Y is flipped so positive data-y points up on screen.
  const scaleY = (y: number) =>
    height - ((y - viewport.minY) / (viewport.maxY - viewport.minY)) * height;

  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      <svg
        data-testid="notation-2d-view-svg"
        width={width}
        height={height}
        style={{ background: '#0b1220', borderRadius: 6 }}
      >
        {/* Axes through (0, 0) for orientation. */}
        <line
          x1={scaleX(viewport.minX)}
          y1={scaleY(0)}
          x2={scaleX(viewport.maxX)}
          y2={scaleY(0)}
          stroke="#1f2937"
          strokeWidth={1}
        />
        <line
          x1={scaleX(0)}
          y1={scaleY(viewport.minY)}
          x2={scaleX(0)}
          y2={scaleY(viewport.maxY)}
          stroke="#1f2937"
          strokeWidth={1}
        />
        {positions.map((p) => (
          <circle
            key={p.primitive}
            data-testid={`notation-primitive-${p.primitive}`}
            data-kind={p.kind}
            cx={scaleX(p.x)}
            cy={scaleY(p.y)}
            r={6}
            fill={colorForKind(p.kind)}
            stroke={hovered?.primitive === p.primitive ? '#fff' : 'rgba(0,0,0,0.25)'}
            strokeWidth={hovered?.primitive === p.primitive ? 2 : 1}
            style={{ cursor: onSelectPrimitive ? 'pointer' : 'default' }}
            onMouseEnter={() => setHovered(p)}
            onMouseLeave={() => setHovered(null)}
            onClick={() => onSelectPrimitive?.(p)}
          />
        ))}
        {showLabels &&
          positions
            .filter((p) => AUTO_LABELED_KINDS.has(p.kind))
            .map((p) => (
              <text
                key={`label-${p.primitive}`}
                data-testid={`notation-label-${p.primitive}`}
                x={scaleX(p.x) + 10}
                y={scaleY(p.y) + 4}
                fill="#e2e8f0"
                fontFamily="monospace"
                fontSize={11}
                pointerEvents="none"
              >
                {p.primitive}
              </text>
            ))}
      </svg>
      {hovered && (
        <div
          data-testid="notation-2d-tooltip"
          style={{
            position: 'absolute',
            top: 8,
            left: 8,
            background: 'rgba(15, 23, 42, 0.92)',
            color: '#e2e8f0',
            border: '1px solid #334155',
            borderRadius: 4,
            padding: '6px 10px',
            fontFamily: 'monospace',
            fontSize: 12,
            pointerEvents: 'none',
          }}
        >
          <div style={{ fontWeight: 600 }}>{hovered.primitive}</div>
          <div style={{ opacity: 0.7 }}>{hovered.kind}</div>
          <div style={{ opacity: 0.55 }}>
            ({hovered.x.toFixed(3)}, {hovered.y.toFixed(3)})
          </div>
        </div>
      )}
      <div
        data-testid="notation-2d-footer"
        style={{
          position: 'absolute',
          bottom: 8,
          right: 12,
          color: '#64748b',
          fontFamily: 'monospace',
          fontSize: 11,
        }}
      >
        {filterKind
          ? `${positions.length} of ${allPos.length} primitives`
          : `${positions.length} primitives`}
        {filterKind ? ` (${filterKind})` : ''} · {layoutVersion()}
      </div>
    </div>
  );
}


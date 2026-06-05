import { useId, type CSSProperties } from 'react';
import { BRAND_DOT_TEAL } from '../../lib/designTokens';

export interface TreeOfLifeMarkProps {
  /** Rendered height in px. Width is derived from the 800x1100 viewBox. */
  size?: number;
  /**
   * When true, each dot breathes (opacity 0.65 -> 1) on a staggered top->bottom
   * wave via the `tks-breathe` keyframe. The `.tks-breathe-dot` class lets the
   * global `prefers-reduced-motion` guard freeze every dot at full opacity.
   * When false the dots are fully static.
   */
  animated?: boolean;
  className?: string;
  title?: string;
}

// Canonical Tree-of-Life coordinates, ported verbatim from the dashboard
// CompilerPage 10-dot mark. Per-dot breathe delay ripples the brighten wave
// top -> bottom through the formation (0s at the crown, 2.25s at the base).
const DOTS: ReadonlyArray<{ cx: number; cy: number; delay: number }> = [
  { cx: 400, cy: 55, delay: 0 },
  { cx: 110, cy: 190, delay: 0.25 },
  { cx: 690, cy: 190, delay: 0.5 },
  { cx: 400, cy: 400, delay: 0.75 },
  { cx: 110, cy: 545, delay: 1.0 },
  { cx: 690, cy: 545, delay: 1.25 },
  { cx: 400, cy: 690, delay: 1.5 },
  { cx: 110, cy: 870, delay: 1.75 },
  { cx: 690, cy: 870, delay: 2.0 },
  { cx: 400, cy: 1020, delay: 2.25 },
];

const VIEWBOX_W = 800;
const VIEWBOX_H = 1100;

/**
 * The 10-dot Tree-of-Life brand mark — the cross-app anchor that self-identifies
 * the CAS Harness on every audit-console view. Pure SVG/CSS, no framer-motion.
 *
 * The `tks-breathe` drop-shadow uses `currentColor`, so each circle sets its own
 * `color` to the brand mid-teal to drive a soft glow without a separate filter.
 */
export function TreeOfLifeMark({
  size = 32,
  animated = true,
  className,
  title,
}: TreeOfLifeMarkProps): JSX.Element {
  const rawId = useId();
  // useId() can emit characters that are invalid in SVG ids / url() refs.
  const safeId = rawId.replace(/[^a-zA-Z0-9_-]/g, '');
  const gradId = `tol-grad-${safeId}`;
  const width = Math.round(size * (VIEWBOX_W / VIEWBOX_H));

  const dotStyle = (delay: number): CSSProperties =>
    animated
      ? {
          color: BRAND_DOT_TEAL[1],
          animation: `tks-breathe 2.5s ease-in-out ${delay}s infinite alternate`,
        }
      : { color: BRAND_DOT_TEAL[1], opacity: 1 };

  return (
    <svg
      viewBox={`0 0 ${VIEWBOX_W} ${VIEWBOX_H}`}
      width={width}
      height={size}
      className={className}
      role="img"
      aria-label={title ?? 'CAS Harness mark'}
      style={{ display: 'block', flex: '0 0 auto', overflow: 'visible' }}
    >
      {title ? <title>{title}</title> : null}
      <defs>
        <radialGradient id={gradId} cx="35%" cy="35%" r="65%">
          <stop offset="0%" stopColor={BRAND_DOT_TEAL[0]} />
          <stop offset="70%" stopColor={BRAND_DOT_TEAL[1]} />
          <stop offset="100%" stopColor={BRAND_DOT_TEAL[2]} />
        </radialGradient>
      </defs>
      {DOTS.map((dot) => (
        <circle
          key={`${dot.cx}-${dot.cy}`}
          className={animated ? 'tks-breathe-dot' : undefined}
          cx={dot.cx}
          cy={dot.cy}
          r={90}
          fill={`url(#${gradId})`}
          style={dotStyle(dot.delay)}
        />
      ))}
    </svg>
  );
}

export default TreeOfLifeMark;

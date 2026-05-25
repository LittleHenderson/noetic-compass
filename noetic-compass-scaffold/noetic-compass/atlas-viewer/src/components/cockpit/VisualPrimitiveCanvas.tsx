import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type KeyboardEvent,
  type ReactNode,
} from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  THEME,
  SPRING_GENTLE,
  GLASS_RADIUS,
} from '../../lib/designTokens';
import { ATLAS_STATUS_COLORS } from '../../lib/atlasPalette';
import { toEnglish } from '../../lib/colloquialismMap';
import type {
  EvidenceRef,
  VisualPrimitive,
  VisualPrimitiveKind,
} from '../../lib/visualPrimitives';

export type { EvidenceRef, VisualPrimitive, VisualPrimitiveKind };

export interface VisualPrimitiveCanvasProps {
  imageUrl: string;
  imageWidth: number;
  imageHeight: number;
  primitives: VisualPrimitive[];
  activeStepPrimitiveIds?: string[];
  onPrimitiveHover?: (p: VisualPrimitive | null) => void;
  onPrimitiveClick?: (p: VisualPrimitive, evidenceRef?: EvidenceRef) => void;
  ariaLabel?: string;
}

interface HoverTooltip {
  primitive: VisualPrimitive;
  x: number;
  y: number;
}

const AXIS_COLORS: Record<string, string> = {
  noetic: '#3b82f6',
  domain: '#a855f7',
  drive: '#f97316',
  register: '#22c55e',
  inversion: '#ef4444',
  recipe: '#eab308',
};

function colorFor(primitive: VisualPrimitive): string {
  if (primitive.cas_axis && AXIS_COLORS[primitive.cas_axis.toLowerCase()]) {
    return AXIS_COLORS[primitive.cas_axis.toLowerCase()];
  }
  return ATLAS_STATUS_COLORS.activeTrace;
}

function buildTooltipText(primitive: VisualPrimitive): string {
  const parts: string[] = [];
  if (primitive.label) parts.push(primitive.label);
  if (primitive.cas_label) {
    const english = toEnglish(primitive.cas_label);
    parts.push(english ? `${primitive.cas_label} — ${english}` : primitive.cas_label);
  }
  if (primitive.explanation) parts.push(primitive.explanation);
  return parts.join(' — ');
}

function pairsFromFlat(coords: number[]): Array<[number, number]> {
  const out: Array<[number, number]> = [];
  for (let i = 0; i + 1 < coords.length; i += 2) {
    out.push([coords[i], coords[i + 1]]);
  }
  return out;
}

function pointsAttr(
  coords: number[],
  imageWidth: number,
  imageHeight: number,
): string {
  return pairsFromFlat(coords)
    .map(([nx, ny]) => `${nx * imageWidth},${ny * imageHeight}`)
    .join(' ');
}

const ACTIVE_ANIMATE = {
  scale: [1, 1.06, 1],
  opacity: [0.6, 1, 0.6],
};

const ACTIVE_TRANSITION = {
  duration: 2,
  repeat: Infinity,
  ease: 'easeInOut' as const,
};

export function VisualPrimitiveCanvas(
  props: VisualPrimitiveCanvasProps,
): ReactNode {
  const {
    imageUrl,
    imageWidth,
    imageHeight,
    primitives,
    activeStepPrimitiveIds,
    onPrimitiveHover,
    onPrimitiveClick,
    ariaLabel,
  } = props;

  const containerRef = useRef<HTMLDivElement | null>(null);
  const [tooltip, setTooltip] = useState<HoverTooltip | null>(null);
  const [containerWidth, setContainerWidth] = useState<number>(imageWidth);

  const activeSet = useMemo(
    () => new Set(activeStepPrimitiveIds ?? []),
    [activeStepPrimitiveIds],
  );

  useEffect(() => {
    const node = containerRef.current;
    if (!node || typeof ResizeObserver === 'undefined') return undefined;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerWidth(entry.contentRect.width);
      }
    });
    ro.observe(node);
    return () => ro.disconnect();
  }, []);

  const handleEnter = useCallback(
    (primitive: VisualPrimitive, evt: { clientX: number; clientY: number }) => {
      const rect = containerRef.current?.getBoundingClientRect();
      const x = rect ? evt.clientX - rect.left : 0;
      const y = rect ? evt.clientY - rect.top : 0;
      setTooltip({ primitive, x, y });
      onPrimitiveHover?.(primitive);
    },
    [onPrimitiveHover],
  );

  const handleLeave = useCallback(() => {
    setTooltip(null);
    onPrimitiveHover?.(null);
  }, [onPrimitiveHover]);

  const handleClick = useCallback(
    (primitive: VisualPrimitive) => {
      onPrimitiveClick?.(primitive, primitive.evidence_ref);
    },
    [onPrimitiveClick],
  );

  const handleKey = useCallback(
    (primitive: VisualPrimitive, evt: KeyboardEvent<SVGElement>) => {
      if (evt.key === 'Enter' || evt.key === ' ') {
        evt.preventDefault();
        onPrimitiveClick?.(primitive, primitive.evidence_ref);
      }
    },
    [onPrimitiveClick],
  );

  const aspectRatio = imageHeight > 0 ? imageWidth / imageHeight : 1;

  const containerStyle: CSSProperties = {
    position: 'relative',
    width: '100%',
    maxWidth: '100%',
    aspectRatio: `${aspectRatio}`,
    minHeight: 160,
    overflow: 'hidden',
    borderRadius: GLASS_RADIUS,
  };

  const imageStyle: CSSProperties = {
    width: '100%',
    height: '100%',
    display: 'block',
    objectFit: 'contain',
    borderRadius: GLASS_RADIUS,
  };

  const svgStyle: CSSProperties = {
    position: 'absolute',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    pointerEvents: 'none',
  };

  return (
    <div
      ref={containerRef}
      style={containerStyle}
      data-testid="visual-primitive-canvas"
      data-container-width={containerWidth}
    >
      <img
        src={imageUrl}
        alt={ariaLabel ?? 'Spatial evidence image'}
        style={imageStyle}
        draggable={false}
      />
      <svg
        viewBox={`0 0 ${imageWidth} ${imageHeight}`}
        preserveAspectRatio="xMidYMid meet"
        style={svgStyle}
        role="group"
        aria-label={ariaLabel ?? 'Spatial Evidence Layer overlay'}
      >
        <defs>
          <filter id="vpc-halo" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        {primitives.map((primitive) => {
          const isActive = activeSet.has(primitive.id);
          const color = colorFor(primitive);
          const stroke = isActive ? 4 : 2;
          const filter = isActive ? 'url(#vpc-halo)' : undefined;
          const primitiveAria =
            primitive.label ?? primitive.cas_label ?? `Visual primitive ${primitive.id}`;

          const commonProps = {
            tabIndex: 0,
            role: 'button' as const,
            'aria-label': primitiveAria,
            'data-primitive-id': primitive.id,
            'data-active': isActive ? 'true' : 'false',
            'data-kind': primitive.kind,
            style: {
              cursor: 'pointer',
              pointerEvents: 'auto' as const,
              transformBox: 'fill-box' as const,
              transformOrigin: 'center' as const,
            },
            onMouseEnter: (e: { clientX: number; clientY: number }) =>
              handleEnter(primitive, e),
            onMouseLeave: handleLeave,
            onFocus: () => onPrimitiveHover?.(primitive),
            onBlur: () => onPrimitiveHover?.(null),
            onClick: () => handleClick(primitive),
            onKeyDown: (e: KeyboardEvent<SVGElement>) => handleKey(primitive, e),
            filter,
            animate: isActive ? ACTIVE_ANIMATE : undefined,
            transition: isActive ? ACTIVE_TRANSITION : undefined,
          };

          if (primitive.kind === 'point') {
            const [nx = 0, ny = 0] = primitive.coords_norm;
            return (
              <motion.circle
                key={primitive.id}
                cx={nx * imageWidth}
                cy={ny * imageHeight}
                r={8}
                fill={color}
                fillOpacity={0.85}
                stroke={color}
                strokeWidth={stroke}
                {...commonProps}
              />
            );
          }

          if (primitive.kind === 'box') {
            const [nx = 0, ny = 0, nw = 0, nh = 0] = primitive.coords_norm;
            return (
              <motion.rect
                key={primitive.id}
                x={nx * imageWidth}
                y={ny * imageHeight}
                width={nw * imageWidth}
                height={nh * imageHeight}
                fill={color}
                fillOpacity={0.12}
                stroke={color}
                strokeWidth={stroke}
                {...commonProps}
              />
            );
          }

          if (primitive.kind === 'polyline') {
            return (
              <motion.polyline
                key={primitive.id}
                points={pointsAttr(primitive.coords_norm, imageWidth, imageHeight)}
                fill="none"
                stroke={color}
                strokeWidth={stroke}
                strokeLinecap="round"
                strokeLinejoin="round"
                {...commonProps}
              />
            );
          }

          return (
            <motion.polygon
              key={primitive.id}
              points={pointsAttr(primitive.coords_norm, imageWidth, imageHeight)}
              fill={color}
              fillOpacity={0.12}
              stroke={color}
              strokeWidth={stroke}
              {...commonProps}
            />
          );
        })}
      </svg>
      <AnimatePresence initial={false}>
        {tooltip ? (
          <motion.div
            key="tooltip"
            role="tooltip"
            data-testid="vpc-tooltip"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={SPRING_GENTLE}
            style={{
              position: 'absolute',
              left: Math.min(tooltip.x + 12, Math.max(0, containerWidth - 240)),
              top: Math.max(0, tooltip.y + 12),
              maxWidth: 240,
              padding: '6px 10px',
              background: 'rgba(15, 23, 42, 0.78)',
              color: '#f8fafc',
              fontSize: 12,
              lineHeight: 1.4,
              borderRadius: 8,
              pointerEvents: 'none',
              zIndex: 2,
              border: '1px solid rgba(255,255,255,0.08)',
              backdropFilter: 'blur(12px) saturate(160%)',
              WebkitBackdropFilter: 'blur(12px) saturate(160%)',
              boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
            }}
          >
            {buildTooltipText(tooltip.primitive) || tooltip.primitive.id}
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

void THEME;

export default VisualPrimitiveCanvas;

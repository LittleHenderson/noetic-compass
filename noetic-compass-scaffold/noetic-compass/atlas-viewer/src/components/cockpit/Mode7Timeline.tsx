import { useCallback, useMemo, useRef } from 'react';
import type { CSSProperties, KeyboardEvent } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GlassPanel } from '../ui/GlassPanel';
import { THEME, SPRING_SNAPPY, SPRING_GENTLE } from '../../lib/designTokens';
import { ATLAS_STATUS_COLORS } from '../../lib/atlasPalette';

export interface Token {
  token_index: number;
  token: string;
}

export interface Mode7Edge {
  to_token_index: number;
  from_token_index: number | null;
  weight: number;
}

export interface Mode7Frame {
  token_index: number;
  mode7_attribution?: Mode7Edge[];
}

export interface Mode7TimelineProps {
  tokens: Token[];
  frames: Mode7Frame[];
  currentTokenIndex: number;
  onTokenSelect?: (idx: number) => void;
  showAttributionEdges?: boolean;
  className?: string;
}

const CELL_HEIGHT = 50;
const EDGE_LAYER_HEIGHT = 30;
const CELL_GAP = 2;
const MIN_CELL_WIDTH = 28;
const MAX_TOKEN_DISPLAY_CHARS = 8;

function truncateToken(raw: string): string {
  const trimmed = raw.replace(/^[\s]+/, '');
  const display = trimmed.length === 0 ? raw : trimmed;
  if (display.length <= MAX_TOKEN_DISPLAY_CHARS) return display;
  return `${display.slice(0, MAX_TOKEN_DISPLAY_CHARS - 1)}…`;
}

export function Mode7Timeline(props: Mode7TimelineProps): JSX.Element {
  const {
    tokens,
    frames,
    currentTokenIndex,
    onTokenSelect,
    showAttributionEdges = true,
    className,
  } = props;

  const containerRef = useRef<HTMLDivElement | null>(null);

  const lastIndex = Math.max(0, tokens.length - 1);
  const safeCurrent = Math.min(Math.max(0, currentTokenIndex), lastIndex);

  const currentFrame = useMemo<Mode7Frame | undefined>(
    () => frames.find((f) => f.token_index === safeCurrent),
    [frames, safeCurrent],
  );

  const cellWidthPct = tokens.length > 0 ? 100 / tokens.length : 100;

  const handleClick = useCallback(
    (idx: number) => {
      onTokenSelect?.(idx);
    },
    [onTokenSelect],
  );

  // a11y: implement slider semantics with ArrowLeft/Right step, Home/End jump.
  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLDivElement>) => {
      if (!onTokenSelect || tokens.length === 0) return;
      switch (e.key) {
        case 'ArrowRight':
        case 'ArrowDown':
          e.preventDefault();
          onTokenSelect(Math.min(lastIndex, safeCurrent + 1));
          break;
        case 'ArrowLeft':
        case 'ArrowUp':
          e.preventDefault();
          onTokenSelect(Math.max(0, safeCurrent - 1));
          break;
        case 'Home':
          e.preventDefault();
          onTokenSelect(0);
          break;
        case 'End':
          e.preventDefault();
          onTokenSelect(lastIndex);
          break;
        default:
          break;
      }
    },
    [onTokenSelect, safeCurrent, lastIndex, tokens.length],
  );

  const wrapperStyle: CSSProperties = {
    width: '100%',
    display: 'flex',
    flexDirection: 'column',
    fontFamily: THEME?.fontFamily ?? 'Inter, ui-sans-serif, system-ui, sans-serif',
    fontSize: '11px',
    color: THEME?.colors?.textPrimary ?? '#e5e7eb',
    outline: 'none',
  };

  const cellRowStyle: CSSProperties = {
    position: 'relative',
    display: 'flex',
    gap: `${CELL_GAP}px`,
    width: '100%',
    height: `${CELL_HEIGHT}px`,
    alignItems: 'stretch',
  };

  const edges = currentFrame?.mode7_attribution ?? [];

  return (
    <GlassPanel
      intensity="thin"
      role="slider"
      tabIndex={0}
      aria-label="Mode 7 token timeline"
      aria-valuemin={0}
      aria-valuemax={lastIndex}
      aria-valuenow={safeCurrent}
      aria-valuetext={tokens[safeCurrent]?.token ?? ''}
      onKeyDown={handleKeyDown}
      className={className}
      style={wrapperStyle}
      data-testid="mode7-timeline"
      ref={containerRef}
    >
      <div style={cellRowStyle} data-testid="mode7-timeline-cells">
        {tokens.map((tok, idx) => {
          const isCurrent = idx === safeCurrent;
          const cellStyle: CSSProperties = {
            position: 'relative',
            flex: `1 1 ${cellWidthPct}%`,
            minWidth: `${MIN_CELL_WIDTH}px`,
            height: `${CELL_HEIGHT}px`,
            // Wave 5.2: no big colored fill on the current cell. Subtle
            // teal-tinted background + teal border for the active cell;
            // neutral hairline for others. No glow halo.
            background: isCurrent
              ? 'rgba(45, 212, 191, 0.10)'
              : 'rgba(255, 255, 255, 0.02)',
            border: isCurrent
              ? `1px solid ${ATLAS_STATUS_COLORS.activeTrace}`
              : '1px solid rgba(255, 255, 255, 0.06)',
            borderRadius: '6px',
            color: isCurrent ? '#e2e8f0' : '#94a3b8',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: onTokenSelect ? 'pointer' : 'default',
            overflow: 'hidden',
            whiteSpace: 'nowrap',
            textOverflow: 'ellipsis',
            padding: '0 6px',
            fontWeight: isCurrent ? 600 : 400,
            fontFamily: THEME?.fontMono ?? 'JetBrains Mono, ui-monospace, monospace',
            fontSize: 11,
            letterSpacing: 0.2,
            zIndex: isCurrent ? 2 : 1,
            transition: 'border-color 0.15s ease, background 0.15s ease',
          };
          return (
            <motion.div
              key={tok.token_index}
              role="button"
              tabIndex={-1}
              aria-label={`Token ${idx}: ${tok.token}`}
              aria-current={isCurrent ? 'true' : undefined}
              title={tok.token}
              data-testid={`mode7-timeline-cell-${idx}`}
              data-current={isCurrent ? 'true' : 'false'}
              onClick={() => handleClick(idx)}
              style={cellStyle}
              whileHover={{
                borderColor: isCurrent
                  ? ATLAS_STATUS_COLORS.activeTrace
                  : 'rgba(255, 255, 255, 0.12)',
                color: '#e2e8f0',
              }}
              whileTap={{ scale: 0.98 }}
              transition={SPRING_GENTLE}
            >
              {isCurrent && (
                <motion.div
                  layoutId="timeline-active-cell"
                  data-testid="mode7-timeline-active-highlight"
                  transition={SPRING_SNAPPY}
                  style={{
                    position: 'absolute',
                    inset: -1,
                    borderRadius: '6px',
                    border: `1px solid ${ATLAS_STATUS_COLORS.activeTrace}`,
                    pointerEvents: 'none',
                  }}
                />
              )}
              {truncateToken(tok.token)}
            </motion.div>
          );
        })}
      </div>
      {showAttributionEdges && (
        <svg
          data-testid="mode7-timeline-edges"
          aria-hidden="true"
          width="100%"
          height={EDGE_LAYER_HEIGHT}
          viewBox={`0 0 100 ${EDGE_LAYER_HEIGHT}`}
          preserveAspectRatio="none"
          style={{ display: 'block', marginTop: '2px' }}
        >
          <AnimatePresence>
            {edges.map((edge, i) => {
              if (edge.from_token_index === null || edge.from_token_index === undefined) {
                return null;
              }
              const fromIdx = edge.from_token_index;
              const toIdx = edge.to_token_index;
              if (tokens.length === 0) return null;
              const fromX = ((fromIdx + 0.5) / tokens.length) * 100;
              const toX = ((toIdx + 0.5) / tokens.length) * 100;
              const midX = (fromX + toX) / 2;
              const path = `M ${fromX} 0 Q ${midX} ${EDGE_LAYER_HEIGHT} ${toX} 0`;
              const opacity = Math.max(0.15, Math.min(1, edge.weight));
              // pathLength 0->1 draws the bezier on instead of popping it in;
              // keyed by current frame so each frame change re-draws the edges.
              return (
                <motion.path
                  key={`${safeCurrent}-${fromIdx}-${toIdx}-${i}`}
                  d={path}
                  stroke={ATLAS_STATUS_COLORS.activeTrace}
                  strokeWidth={1.25}
                  strokeLinecap="round"
                  fill="none"
                  opacity={opacity}
                  data-testid={`mode7-timeline-edge-${fromIdx}-${toIdx}`}
                  vectorEffect="non-scaling-stroke"
                  initial={{ pathLength: 0, opacity: 0 }}
                  animate={{ pathLength: 1, opacity }}
                  exit={{ pathLength: 0, opacity: 0 }}
                  transition={{ duration: 0.3, ease: 'easeOut' }}
                />
              );
            })}
          </AnimatePresence>
        </svg>
      )}
    </GlassPanel>
  );
}

export default Mode7Timeline;

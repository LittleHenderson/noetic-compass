import { useCallback, useEffect, useRef, useState } from 'react';
import type { CSSProperties, KeyboardEvent, PointerEvent as ReactPointerEvent } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GlassPanel } from '../ui/GlassPanel';
import {
  THEME,
  SPRING_SNAPPY,
  GLASS_PANEL_FILL,
  GLASS_PANEL_BORDER,
} from '../../lib/designTokens';

export type PlaybackMode = 'paused' | 'playing';
export type Speed = 0.25 | 0.5 | 1 | 2 | 4;
export type ZoomLevel = 0 | 1 | 2 | 3 | 4 | 5;
export type VerificationMode =
  | 'BALANCED'
  | 'HIGH_PRECISION'
  | 'MAX_COVERAGE_TRIAGE';

export interface ControlBarProps {
  playbackMode: PlaybackMode;
  speed: Speed;
  zoomLevel: ZoomLevel;
  currentTokenIndex: number;
  tokenCount: number;
  verificationMode: VerificationMode;
  showBlindspots: boolean;
  showActiveTrace: boolean;
  onPlayToggle: () => void;
  onSpeedChange: (s: Speed) => void;
  onZoomLevelChange: (z: ZoomLevel) => void;
  onTokenSeek: (idx: number) => void;
  onVerificationModeChange: (m: VerificationMode) => void;
  onToggleBlindspots: () => void;
  onToggleActiveTrace: () => void;
  onExportEvidence?: () => void;
  className?: string;
}

const SPEEDS: Speed[] = [0.25, 0.5, 1, 2, 4];
const ZOOMS: ZoomLevel[] = [0, 1, 2, 3, 4, 5];
const VERIFICATION_MODES: VerificationMode[] = [
  'BALANCED',
  'HIGH_PRECISION',
  'MAX_COVERAGE_TRIAGE',
];

const TEXT_COLOR = '#e2e8f0';
const TEXT_MUTED = '#9ca3af';
const ACTIVE_TEXT_ON_ACCENT = '#0b1220';
const ACCENT = THEME.ACCENT_BLUE;
const HAIRLINE = 'rgba(255, 255, 255, 0.08)';

const barStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  height: 56,
  padding: '8px 16px',
  color: TEXT_COLOR,
  fontFamily: 'Inter, system-ui, sans-serif',
  fontSize: 13,
  outline: 'none',
  boxSizing: 'border-box',
};

const segmentStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  position: 'relative',
};

const middleSegmentStyle: CSSProperties = {
  ...segmentStyle,
  flex: 1,
  minWidth: 0,
};

const pillBaseStyle: CSSProperties = {
  position: 'relative',
  minWidth: 32,
  minHeight: 32,
  padding: '4px 12px',
  color: TEXT_COLOR,
  background: 'transparent',
  border: GLASS_PANEL_BORDER,
  borderRadius: 8,
  cursor: 'pointer',
  fontSize: 12,
  fontWeight: 500,
  fontFamily: 'inherit',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
};

const activePillTextStyle: CSSProperties = {
  color: ACTIVE_TEXT_ON_ACCENT,
  fontWeight: 600,
};

const pillLabelStyle: CSSProperties = {
  position: 'relative',
  zIndex: 1,
};

const activeIndicatorBaseStyle: CSSProperties = {
  position: 'absolute',
  inset: 0,
  borderRadius: 8,
  background: ACCENT,
  zIndex: 0,
};

const selectStyle: CSSProperties = {
  minHeight: 32,
  padding: '4px 10px',
  background: GLASS_PANEL_FILL,
  color: TEXT_COLOR,
  border: GLASS_PANEL_BORDER,
  borderRadius: 8,
  fontSize: 12,
  fontFamily: 'inherit',
};

const scrubberWrapStyle: CSSProperties = {
  flex: 1,
  minWidth: 80,
  position: 'relative',
  height: 28,
  display: 'flex',
  alignItems: 'center',
  cursor: 'pointer',
};

const scrubberTrackStyle: CSSProperties = {
  position: 'relative',
  width: '100%',
  height: 4,
  borderRadius: 2,
  background: HAIRLINE,
  overflow: 'visible',
};

const scrubberFillStyle: CSSProperties = {
  position: 'absolute',
  top: 0,
  left: 0,
  bottom: 0,
  background: ACCENT,
  borderRadius: 2,
};

const scrubberThumbStyle: CSSProperties = {
  position: 'absolute',
  top: '50%',
  width: 14,
  height: 14,
  borderRadius: '50%',
  background: ACCENT,
  boxShadow: '0 0 0 2px rgba(255, 255, 255, 0.18)',
  transform: 'translate(-50%, -50%)',
  cursor: 'grab',
  touchAction: 'none',
};

const hiddenScrubberInputStyle: CSSProperties = {
  position: 'absolute',
  width: 1,
  height: 1,
  padding: 0,
  margin: -1,
  overflow: 'hidden',
  clip: 'rect(0 0 0 0)',
  whiteSpace: 'nowrap',
  border: 0,
};

const tokenLabelStyle: CSSProperties = {
  whiteSpace: 'nowrap',
  fontVariantNumeric: 'tabular-nums',
  color: TEXT_MUTED,
};

const dividerStyle: CSSProperties = {
  width: 1,
  height: 24,
  background: HAIRLINE,
};

function clampToken(idx: number, tokenCount: number): number {
  if (tokenCount <= 0) return 0;
  if (idx < 0) return 0;
  if (idx > tokenCount - 1) return tokenCount - 1;
  return idx;
}

export default function ControlBar(props: ControlBarProps): JSX.Element {
  const {
    playbackMode,
    speed,
    zoomLevel,
    currentTokenIndex,
    tokenCount,
    verificationMode,
    showBlindspots,
    showActiveTrace,
    onPlayToggle,
    onSpeedChange,
    onZoomLevelChange,
    onTokenSeek,
    onVerificationModeChange,
    onToggleBlindspots,
    onToggleActiveTrace,
    onExportEvidence,
    className,
  } = props;

  const containerRef = useRef<HTMLDivElement | null>(null);
  const trackRef = useRef<HTMLDivElement | null>(null);
  const [dragging, setDragging] = useState(false);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLDivElement>): void => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA') {
        if (e.key !== ' ' && e.key !== 'Spacebar') return;
      }
      switch (e.key) {
        case ' ':
        case 'Spacebar':
          e.preventDefault();
          onPlayToggle();
          return;
        case ',':
          e.preventDefault();
          onTokenSeek(clampToken(currentTokenIndex - 1, tokenCount));
          return;
        case '.':
          e.preventDefault();
          onTokenSeek(clampToken(currentTokenIndex + 1, tokenCount));
          return;
        case '[':
          e.preventDefault();
          if (zoomLevel > 0) {
            onZoomLevelChange((zoomLevel - 1) as ZoomLevel);
          }
          return;
        case ']':
          e.preventDefault();
          if (zoomLevel < 5) {
            onZoomLevelChange((zoomLevel + 1) as ZoomLevel);
          }
          return;
        case 'b':
        case 'B':
          e.preventDefault();
          onToggleBlindspots();
          return;
        case 't':
        case 'T':
          e.preventDefault();
          onToggleActiveTrace();
          return;
        default:
          return;
      }
    },
    [
      currentTokenIndex,
      tokenCount,
      zoomLevel,
      onPlayToggle,
      onTokenSeek,
      onZoomLevelChange,
      onToggleBlindspots,
      onToggleActiveTrace,
    ],
  );

  const playing = playbackMode === 'playing';
  const playGlyph = playing ? '⏸' : '▶';
  const playLabel = playing ? 'Pause playback' : 'Start playback';
  const sliderMax = Math.max(0, tokenCount - 1);
  const pct = sliderMax === 0 ? 0 : (currentTokenIndex / sliderMax) * 100;

  const seekFromClientX = useCallback(
    (clientX: number): void => {
      const track = trackRef.current;
      if (!track || sliderMax === 0) return;
      const rect = track.getBoundingClientRect();
      const ratio = (clientX - rect.left) / Math.max(1, rect.width);
      const next = Math.round(ratio * sliderMax);
      onTokenSeek(clampToken(next, tokenCount));
    },
    [onTokenSeek, sliderMax, tokenCount],
  );

  const handleTrackPointerDown = useCallback(
    (e: ReactPointerEvent<HTMLDivElement>): void => {
      if (sliderMax === 0) return;
      e.preventDefault();
      setDragging(true);
      seekFromClientX(e.clientX);
    },
    [seekFromClientX, sliderMax],
  );

  useEffect(() => {
    if (!dragging) return;
    const move = (e: PointerEvent): void => seekFromClientX(e.clientX);
    const up = (): void => setDragging(false);
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
    window.addEventListener('pointercancel', up);
    return () => {
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', up);
      window.removeEventListener('pointercancel', up);
    };
  }, [dragging, seekFromClientX]);

  /**
   * Active-pill morph: every active-state indicator shares a layoutId scoped
   * to its segment. Framer's layout engine tweens the indicator's bounding
   * box between sibling buttons instead of fading one out and another in,
   * producing the liquid morph.
   */
  const renderActiveIndicator = (layoutId: string): JSX.Element => (
    <motion.span
      layoutId={layoutId}
      layout
      style={activeIndicatorBaseStyle}
      transition={SPRING_SNAPPY}
      aria-hidden="true"
    />
  );

  return (
    <GlassPanel intensity="regular" as="div" padding={0}>
      <div
        ref={containerRef}
        role="toolbar"
        aria-label="Atlas Viewer playback and view controls"
        tabIndex={0}
        onKeyDown={handleKeyDown}
        style={barStyle}
        className={className}
        data-testid="control-bar"
      >
        <div style={segmentStyle} aria-label="Playback">
          <motion.button
            type="button"
            onClick={onPlayToggle}
            aria-label={playLabel}
            aria-pressed={playing}
            style={pillBaseStyle}
            data-testid="play-toggle"
            whileHover={{ scale: 1.06 }}
            whileTap={{ scale: 0.94 }}
            transition={SPRING_SNAPPY}
          >
            <AnimatePresence>
              {playing ? renderActiveIndicator('active-pill-play') : null}
            </AnimatePresence>
            <span
              aria-hidden="true"
              style={{
                ...pillLabelStyle,
                ...(playing ? activePillTextStyle : null),
              }}
            >
              {playGlyph}
            </span>
          </motion.button>
          <div role="group" aria-label="Playback speed" style={segmentStyle}>
            {SPEEDS.map((s) => {
              const active = s === speed;
              return (
                <motion.button
                  key={s}
                  type="button"
                  onClick={() => onSpeedChange(s)}
                  aria-label={`Set playback speed ${s}x`}
                  aria-pressed={active}
                  style={pillBaseStyle}
                  data-testid={`speed-${s}`}
                  whileHover={{ scale: 1.06 }}
                  whileTap={{ scale: 0.94 }}
                  transition={SPRING_SNAPPY}
                >
                  {active ? renderActiveIndicator('active-pill-speed') : null}
                  <span
                    style={{
                      ...pillLabelStyle,
                      ...(active ? activePillTextStyle : null),
                    }}
                  >
                    {s}x
                  </span>
                </motion.button>
              );
            })}
          </div>
        </div>

        <div style={dividerStyle} aria-hidden="true" />

        <div style={middleSegmentStyle} aria-label="Token scrubber">
          <div
            ref={trackRef}
            style={scrubberWrapStyle}
            onPointerDown={handleTrackPointerDown}
            data-testid="token-scrubber-track"
          >
            <div style={scrubberTrackStyle}>
              <motion.div
                style={scrubberFillStyle}
                animate={{ width: `${pct}%` }}
                transition={SPRING_SNAPPY}
              />
              <motion.div
                style={scrubberThumbStyle}
                animate={{ left: `${pct}%` }}
                transition={SPRING_SNAPPY}
                whileHover={{ scale: 1.15 }}
                whileTap={{ scale: 0.92 }}
                role="presentation"
                data-testid="token-scrubber-thumb"
              />
            </div>
          </div>
          <input
            type="range"
            min={0}
            max={sliderMax}
            step={1}
            value={currentTokenIndex}
            onChange={(e) =>
              onTokenSeek(clampToken(Number(e.target.value), tokenCount))
            }
            aria-label="Seek token position"
            aria-valuemin={0}
            aria-valuemax={sliderMax}
            aria-valuenow={currentTokenIndex}
            style={hiddenScrubberInputStyle}
            data-testid="token-scrubber"
          />
          <span style={tokenLabelStyle} data-testid="token-label">
            token {tokenCount === 0 ? 0 : currentTokenIndex + 1} of {tokenCount}
          </span>
        </div>

        <div style={dividerStyle} aria-hidden="true" />

        <div style={segmentStyle} aria-label="View controls">
          <div role="group" aria-label="Zoom level" style={segmentStyle}>
            {ZOOMS.map((z) => {
              const active = z === zoomLevel;
              return (
                <motion.button
                  key={z}
                  type="button"
                  onClick={() => onZoomLevelChange(z)}
                  aria-label={`Zoom level Z${z}`}
                  aria-pressed={active}
                  style={pillBaseStyle}
                  data-testid={`zoom-${z}`}
                  whileHover={{ scale: 1.06 }}
                  whileTap={{ scale: 0.94 }}
                  transition={SPRING_SNAPPY}
                >
                  {active ? renderActiveIndicator('active-pill-zoom') : null}
                  <span
                    style={{
                      ...pillLabelStyle,
                      ...(active ? activePillTextStyle : null),
                    }}
                  >
                    Z{z}
                  </span>
                </motion.button>
              );
            })}
          </div>
          <motion.button
            type="button"
            onClick={onToggleBlindspots}
            aria-label="Toggle blindspots overlay"
            aria-pressed={showBlindspots}
            style={pillBaseStyle}
            data-testid="toggle-blindspots"
            title="Blindspots (B)"
            whileHover={{ scale: 1.06 }}
            whileTap={{ scale: 0.94 }}
            transition={SPRING_SNAPPY}
          >
            <AnimatePresence>
              {showBlindspots
                ? renderActiveIndicator('active-pill-blindspots')
                : null}
            </AnimatePresence>
            <span
              style={{
                ...pillLabelStyle,
                ...(showBlindspots ? activePillTextStyle : null),
              }}
            >
              B
            </span>
          </motion.button>
          <motion.button
            type="button"
            onClick={onToggleActiveTrace}
            aria-label="Toggle active trace overlay"
            aria-pressed={showActiveTrace}
            style={pillBaseStyle}
            data-testid="toggle-activetrace"
            title="Active trace (T)"
            whileHover={{ scale: 1.06 }}
            whileTap={{ scale: 0.94 }}
            transition={SPRING_SNAPPY}
          >
            <AnimatePresence>
              {showActiveTrace
                ? renderActiveIndicator('active-pill-activetrace')
                : null}
            </AnimatePresence>
            <span
              style={{
                ...pillLabelStyle,
                ...(showActiveTrace ? activePillTextStyle : null),
              }}
            >
              T
            </span>
          </motion.button>
          <select
            value={verificationMode}
            onChange={(e) =>
              onVerificationModeChange(e.target.value as VerificationMode)
            }
            aria-label="Verification mode"
            style={selectStyle}
            data-testid="verification-mode"
          >
            {VERIFICATION_MODES.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
          {onExportEvidence ? (
            <motion.button
              type="button"
              onClick={onExportEvidence}
              aria-label="Export evidence pack"
              style={pillBaseStyle}
              data-testid="export-evidence"
              whileHover={{ scale: 1.06 }}
              whileTap={{ scale: 0.94 }}
              transition={SPRING_SNAPPY}
            >
              <span style={pillLabelStyle}>Export</span>
            </motion.button>
          ) : null}
        </div>
      </div>
    </GlassPanel>
  );
}

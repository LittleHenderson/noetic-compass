import { useCallback, useEffect, useRef, useState } from 'react';
import type { CSSProperties, KeyboardEvent, PointerEvent as ReactPointerEvent } from 'react';
import { motion } from 'framer-motion';
import { GlassPanel } from '../ui/GlassPanel';
import {
  ACCENT_TEAL,
  COLORS,
  SPRING_SNAPPY,
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
  // Wave 5.2 additions:
  onRewind?: () => void;
  onToggleFullscreen?: () => void;
  onToggleLeftPanel?: () => void;
  onToggleRightPanel?: () => void;
  onToggleHelp?: () => void;
  fullscreen?: boolean;
  leftPanelOpen?: boolean;
  rightPanelOpen?: boolean;
  className?: string;
}

const SPEEDS: Speed[] = [0.25, 0.5, 1, 2, 4];
const ZOOMS: ZoomLevel[] = [0, 1, 2, 3, 4, 5];
const VERIFICATION_MODES: VerificationMode[] = [
  'BALANCED',
  'HIGH_PRECISION',
  'MAX_COVERAGE_TRIAGE',
];

const HAIRLINE = 'rgba(255, 255, 255, 0.06)';

const barStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  height: 48,
  padding: '6px 12px',
  color: COLORS.textPrimary,
  fontFamily: 'system-ui, -apple-system, "Segoe UI Variable", sans-serif',
  fontSize: 12,
  outline: 'none',
  boxSizing: 'border-box',
  flexWrap: 'wrap',
};

const segmentStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 4,
  position: 'relative',
};

const middleSegmentStyle: CSSProperties = {
  ...segmentStyle,
  flex: 1,
  minWidth: 120,
  gap: 10,
};

// Wave 5.2 pill style:
//  - transparent background (no big colored fill)
//  - thin hairline border at very low opacity
//  - active state = teal text + teal-tinted background + teal border
//  - inactive = slate-400 text on hairline border, hover lifts to slate-200
const pillBaseStyle: CSSProperties = {
  position: 'relative',
  minWidth: 28,
  minHeight: 28,
  padding: '4px 10px',
  color: COLORS.textSecondary,
  background: 'transparent',
  border: `1px solid ${HAIRLINE}`,
  borderRadius: 6,
  cursor: 'pointer',
  fontSize: 11.5,
  fontWeight: 500,
  fontFamily: 'inherit',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  letterSpacing: 0.2,
  transition: 'color 0.15s ease, background 0.15s ease, border-color 0.15s ease',
};

const activePillStyle: CSSProperties = {
  ...pillBaseStyle,
  color: ACCENT_TEAL,
  background: 'rgba(45, 212, 191, 0.10)',
  borderColor: 'rgba(45, 212, 191, 0.45)',
  fontWeight: 600,
};

const selectStyle: CSSProperties = {
  minHeight: 28,
  padding: '4px 8px',
  background: 'rgba(255, 255, 255, 0.02)',
  color: COLORS.textPrimary,
  border: `1px solid ${HAIRLINE}`,
  borderRadius: 6,
  fontSize: 11.5,
  fontFamily: 'inherit',
};

const scrubberWrapStyle: CSSProperties = {
  flex: 1,
  minWidth: 80,
  position: 'relative',
  height: 22,
  display: 'flex',
  alignItems: 'center',
  cursor: 'pointer',
};

const scrubberTrackStyle: CSSProperties = {
  position: 'relative',
  width: '100%',
  height: 3,
  borderRadius: 2,
  background: 'rgba(255, 255, 255, 0.06)',
  overflow: 'visible',
};

const scrubberFillStyle: CSSProperties = {
  position: 'absolute',
  top: 0,
  left: 0,
  bottom: 0,
  background: ACCENT_TEAL,
  borderRadius: 2,
};

// Smaller thumb, no glow halo. Just a hard 8 px dot.
const scrubberThumbStyle: CSSProperties = {
  position: 'absolute',
  top: '50%',
  width: 10,
  height: 10,
  borderRadius: '50%',
  background: ACCENT_TEAL,
  border: '2px solid #020617',
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
  color: COLORS.textMuted,
  fontSize: 11,
  letterSpacing: 0.3,
};

const dividerStyle: CSSProperties = {
  width: 1,
  height: 20,
  background: HAIRLINE,
};

function clampToken(idx: number, tokenCount: number): number {
  if (tokenCount <= 0) return 0;
  if (idx < 0) return 0;
  if (idx > tokenCount - 1) return tokenCount - 1;
  return idx;
}

interface IconButtonProps {
  label: string;
  active?: boolean;
  testId?: string;
  title?: string;
  onClick: () => void;
  children: React.ReactNode;
}

function IconButton({ label, active, testId, title, onClick, children }: IconButtonProps) {
  const style = active ? activePillStyle : pillBaseStyle;
  return (
    <motion.button
      type="button"
      onClick={onClick}
      aria-label={label}
      aria-pressed={active}
      title={title ?? label}
      style={style}
      data-testid={testId}
      whileHover={{
        color: active ? ACCENT_TEAL : COLORS.textPrimary,
        borderColor: active ? 'rgba(45, 212, 191, 0.65)' : 'rgba(255, 255, 255, 0.12)',
      }}
      whileTap={{ scale: 0.97 }}
      transition={SPRING_SNAPPY}
    >
      {children}
    </motion.button>
  );
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
    onRewind,
    onToggleFullscreen,
    onToggleLeftPanel,
    onToggleRightPanel,
    onToggleHelp,
    fullscreen,
    leftPanelOpen,
    rightPanelOpen,
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
        case 'r':
        case 'R':
          if (onRewind) {
            e.preventDefault();
            onRewind();
          }
          return;
        case 'f':
        case 'F':
          if (onToggleFullscreen) {
            e.preventDefault();
            onToggleFullscreen();
          }
          return;
        case '?':
          if (onToggleHelp) {
            e.preventDefault();
            onToggleHelp();
          }
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
      onRewind,
      onToggleFullscreen,
      onToggleHelp,
    ],
  );

  const playing = playbackMode === 'playing';
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

  return (
    <GlassPanel intensity="thin" as="div" padding={0}>
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
        {/* Playback */}
        <div style={segmentStyle} aria-label="Playback">
          {onRewind ? (
            <IconButton
              label="Rewind to start"
              title="Rewind to start (R)"
              testId="rewind"
              onClick={onRewind}
            >
              <span aria-hidden="true">⏮</span>
            </IconButton>
          ) : null}
          <IconButton
            label={playing ? 'Pause playback' : 'Start playback'}
            title="Play / Pause (Space)"
            testId="play-toggle"
            active={playing}
            onClick={onPlayToggle}
          >
            <span aria-hidden="true">{playing ? '⏸' : '▶'}</span>
          </IconButton>
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
                  style={active ? activePillStyle : pillBaseStyle}
                  data-testid={`speed-${s}`}
                  whileHover={{
                    color: active ? ACCENT_TEAL : COLORS.textPrimary,
                    borderColor: active ? 'rgba(45, 212, 191, 0.65)' : 'rgba(255, 255, 255, 0.12)',
                  }}
                  whileTap={{ scale: 0.97 }}
                  transition={SPRING_SNAPPY}
                >
                  {s}×
                </motion.button>
              );
            })}
          </div>
        </div>

        <div style={dividerStyle} aria-hidden="true" />

        {/* Scrubber */}
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
            {tokenCount === 0 ? 0 : currentTokenIndex + 1} / {tokenCount}
          </span>
        </div>

        <div style={dividerStyle} aria-hidden="true" />

        {/* View / overlays */}
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
                  style={active ? activePillStyle : pillBaseStyle}
                  data-testid={`zoom-${z}`}
                  whileHover={{
                    color: active ? ACCENT_TEAL : COLORS.textPrimary,
                    borderColor: active ? 'rgba(45, 212, 191, 0.65)' : 'rgba(255, 255, 255, 0.12)',
                  }}
                  whileTap={{ scale: 0.97 }}
                  transition={SPRING_SNAPPY}
                >
                  Z{z}
                </motion.button>
              );
            })}
          </div>
          <IconButton
            label="Toggle blindspots overlay"
            title="Blindspots (B)"
            testId="toggle-blindspots"
            active={showBlindspots}
            onClick={onToggleBlindspots}
          >
            B
          </IconButton>
          <IconButton
            label="Toggle active trace overlay"
            title="Active trace (T)"
            testId="toggle-activetrace"
            active={showActiveTrace}
            onClick={onToggleActiveTrace}
          >
            T
          </IconButton>
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
                {m.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
          {onExportEvidence ? (
            <IconButton
              label="Export evidence pack"
              testId="export-evidence"
              onClick={onExportEvidence}
            >
              Export
            </IconButton>
          ) : null}
        </div>

        <div style={dividerStyle} aria-hidden="true" />

        {/* Layout */}
        <div style={segmentStyle} aria-label="Layout">
          {onToggleLeftPanel ? (
            <IconButton
              label={leftPanelOpen ? 'Collapse picture panel' : 'Expand picture panel'}
              title="Picture panel"
              testId="toggle-left-panel"
              active={leftPanelOpen}
              onClick={onToggleLeftPanel}
            >
              <span aria-hidden="true">{leftPanelOpen ? '◧' : '▣'}</span>
            </IconButton>
          ) : null}
          {onToggleRightPanel ? (
            <IconButton
              label={rightPanelOpen ? 'Collapse controls panel' : 'Expand controls panel'}
              title="Controls panel"
              testId="toggle-right-panel"
              active={rightPanelOpen}
              onClick={onToggleRightPanel}
            >
              <span aria-hidden="true">{rightPanelOpen ? '◨' : '▤'}</span>
            </IconButton>
          ) : null}
          {onToggleFullscreen ? (
            <IconButton
              label={fullscreen ? 'Exit fullscreen neural net' : 'Fullscreen neural net'}
              title="Fullscreen (F)"
              testId="toggle-fullscreen"
              active={fullscreen}
              onClick={onToggleFullscreen}
            >
              <span aria-hidden="true">{fullscreen ? '⤡' : '⤢'}</span>
            </IconButton>
          ) : null}
          {onToggleHelp ? (
            <IconButton
              label="Open help and glossary"
              title="Help / glossary (?)"
              testId="toggle-help"
              onClick={onToggleHelp}
            >
              ?
            </IconButton>
          ) : null}
        </div>
      </div>
    </GlassPanel>
  );
}

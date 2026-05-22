import { useCallback, useRef } from 'react';
import type { CSSProperties, KeyboardEvent } from 'react';
import { ATLAS_STATUS_COLORS } from '../../lib/atlasPalette';

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

const barStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 12,
  height: 48,
  padding: '0 12px',
  background: '#111827',
  color: '#e5e7eb',
  fontFamily: 'system-ui, sans-serif',
  fontSize: 13,
  borderTop: '1px solid #1f2937',
  borderBottom: '1px solid #1f2937',
  outline: 'none',
};

const segmentStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
};

const middleSegmentStyle: CSSProperties = {
  ...segmentStyle,
  flex: 1,
  minWidth: 0,
};

const pillBaseStyle: CSSProperties = {
  minWidth: 32,
  minHeight: 32,
  padding: '4px 10px',
  background: '#1f2937',
  color: '#e5e7eb',
  border: '1px solid #374151',
  borderRadius: 6,
  cursor: 'pointer',
  fontSize: 12,
  fontWeight: 500,
};

const activePillStyle: CSSProperties = {
  ...pillBaseStyle,
  background: ATLAS_STATUS_COLORS.accepted,
  color: '#0b1220',
  borderColor: ATLAS_STATUS_COLORS.accepted,
};

const selectStyle: CSSProperties = {
  minHeight: 32,
  padding: '4px 8px',
  background: '#1f2937',
  color: '#e5e7eb',
  border: '1px solid #374151',
  borderRadius: 6,
  fontSize: 12,
};

const scrubberStyle: CSSProperties = {
  flex: 1,
  minWidth: 80,
};

const tokenLabelStyle: CSSProperties = {
  whiteSpace: 'nowrap',
  fontVariantNumeric: 'tabular-nums',
  color: '#9ca3af',
};

const dividerStyle: CSSProperties = {
  width: 1,
  height: 24,
  background: '#1f2937',
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

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLDivElement>): void => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      // Don't hijack typing inside form fields (select dropdown etc).
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

  return (
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
        <button
          type="button"
          onClick={onPlayToggle}
          aria-label={playLabel}
          aria-pressed={playing}
          style={playing ? activePillStyle : pillBaseStyle}
          data-testid="play-toggle"
        >
          <span aria-hidden="true">{playGlyph}</span>
        </button>
        <div
          role="group"
          aria-label="Playback speed"
          style={segmentStyle}
        >
          {SPEEDS.map((s) => {
            const active = s === speed;
            return (
              <button
                key={s}
                type="button"
                onClick={() => onSpeedChange(s)}
                aria-label={`Set playback speed ${s}x`}
                aria-pressed={active}
                style={active ? activePillStyle : pillBaseStyle}
                data-testid={`speed-${s}`}
              >
                {s}x
              </button>
            );
          })}
        </div>
      </div>

      <div style={dividerStyle} aria-hidden="true" />

      <div style={middleSegmentStyle} aria-label="Token scrubber">
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
          style={scrubberStyle}
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
              <button
                key={z}
                type="button"
                onClick={() => onZoomLevelChange(z)}
                aria-label={`Zoom level Z${z}`}
                aria-pressed={active}
                style={active ? activePillStyle : pillBaseStyle}
                data-testid={`zoom-${z}`}
              >
                Z{z}
              </button>
            );
          })}
        </div>
        <button
          type="button"
          onClick={onToggleBlindspots}
          aria-label="Toggle blindspots overlay"
          aria-pressed={showBlindspots}
          style={showBlindspots ? activePillStyle : pillBaseStyle}
          data-testid="toggle-blindspots"
          title="Blindspots (B)"
        >
          B
        </button>
        <button
          type="button"
          onClick={onToggleActiveTrace}
          aria-label="Toggle active trace overlay"
          aria-pressed={showActiveTrace}
          style={showActiveTrace ? activePillStyle : pillBaseStyle}
          data-testid="toggle-activetrace"
          title="Active trace (T)"
        >
          T
        </button>
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
          <button
            type="button"
            onClick={onExportEvidence}
            aria-label="Export evidence pack"
            style={pillBaseStyle}
            data-testid="export-evidence"
          >
            Export
          </button>
        ) : null}
      </div>
    </div>
  );
}

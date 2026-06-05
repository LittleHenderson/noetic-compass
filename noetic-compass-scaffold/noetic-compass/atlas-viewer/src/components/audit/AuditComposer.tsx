import type { CSSProperties, ReactNode } from 'react';
import { GlassPanel } from '../ui/GlassPanel';
import { AuditPopover } from './AuditPopover';
import { ModelConnectionCard, type ModelConnectionStatus } from './ModelConnectionCard';
import {
  COLORS,
  FONT_FAMILY,
  FONT_MONO,
  TONE_TINT,
} from '../../lib/designTokens';

export interface AuditComposerLiveChip {
  /** Accent color resolved by the page from the honest live-worker health. */
  accent: string;
  /** Honest label (e.g. real-weights / reachable-demo / unreachable). */
  label: string;
}

export interface AuditComposerPreset {
  id: string;
  label: string;
  onSelect: () => void;
}

export interface AuditComposerProps {
  // --- Target (folds in ModelConnectionCard) ---
  connectionStatus: ModelConnectionStatus;
  modelName?: string;
  provider?: string;
  endpointLabel?: string;
  statusDetail?: string;
  lastChecked?: string;
  canRunAudit?: boolean;
  onConnect?: () => void;
  onDisconnect?: () => void;

  // --- Mode + modules (read-only summary of the fixed audit contract) ---
  /** Audit mode label, e.g. "BALANCED". */
  mode?: string;
  /** Customer-facing module labels shown as chips. */
  moduleLabels?: string[];

  // --- Demo presets (absorbs the command-center preset buttons) ---
  presets?: AuditComposerPreset[];

  // --- BYOK (absorbs the inline key field) ---
  byokApiKey: string;
  onByokApiKeyChange: (value: string) => void;

  // --- Run ---
  isAuditRunning?: boolean;
  isTargetConnecting?: boolean;
  /** Primary action — connect-then-run, owned by the page. */
  onRun: () => void;
  /** Enable/disable the primary Run button (page-computed). */
  runEnabled: boolean;
  /** Primary button label (page-computed: Prepare target / Run / Running…). */
  runLabel: string;

  // --- Live-worker honesty chip (rendered as-is; never invents teal) ---
  liveChip?: AuditComposerLiveChip | null;

  /** Optional empty-state slot (e.g. the breathing brand mark) shown above. */
  emptyState?: ReactNode;
  className?: string;
}

const DEFAULT_MODULE_LABELS = [
  'Model proof',
  'CAS readout',
  'Causal check',
  'Matched control',
  'Output match',
  'Evidence packet',
];

const shellStyle: CSSProperties = {
  display: 'grid',
  gap: 16,
  fontFamily: FONT_FAMILY,
};

const headerStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  alignItems: 'flex-start',
  justifyContent: 'space-between',
  gap: 12,
};

const titleStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textPrimary,
  fontSize: 17,
  fontWeight: 850,
  letterSpacing: 0,
};

const subtitleStyle: CSSProperties = {
  margin: '4px 0 0',
  color: COLORS.textSecondary,
  fontSize: 12.5,
  lineHeight: 1.45,
};

const liveChipStyle = (accent: string): CSSProperties => ({
  display: 'inline-flex',
  alignItems: 'center',
  gap: 7,
  alignSelf: 'flex-start',
  padding: '5px 10px',
  borderRadius: 999,
  border: `1px solid ${accent}59`,
  background: `${accent}1f`,
  color: accent,
  fontSize: 11.5,
  fontWeight: 700,
  letterSpacing: 0.2,
  whiteSpace: 'nowrap',
});

const liveDotStyle = (accent: string): CSSProperties => ({
  width: 8,
  height: 8,
  borderRadius: 999,
  background: accent,
  flex: '0 0 auto',
});

const sectionLabelStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textMuted,
  fontSize: 10.5,
  fontWeight: 800,
  letterSpacing: 0.8,
  textTransform: 'uppercase',
};

const fieldGroupStyle: CSSProperties = {
  display: 'grid',
  gap: 8,
};

const chipRowStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 7,
};

const moduleChipStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  padding: '4px 9px',
  borderRadius: 6,
  border: `1px solid ${TONE_TINT.teal.borderSoft}`,
  background: TONE_TINT.teal.fillSoft,
  color: TONE_TINT.teal.text,
  fontSize: 11,
  fontWeight: 700,
};

const modePillStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  padding: '4px 10px',
  borderRadius: 6,
  border: `1px solid ${COLORS.borderStrong}`,
  background: 'rgba(255, 255, 255, 0.04)',
  color: COLORS.textPrimary,
  fontFamily: FONT_MONO,
  fontSize: 11.5,
  fontWeight: 800,
  letterSpacing: 0.3,
};

const presetRowStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 8,
};

const presetButtonStyle = (disabled: boolean): CSSProperties => ({
  minHeight: 34,
  padding: '7px 12px',
  borderRadius: 6,
  border: `1px solid ${COLORS.borderStrong}`,
  background: 'rgba(255, 255, 255, 0.04)',
  color: disabled ? COLORS.textMuted : COLORS.textPrimary,
  cursor: disabled ? 'not-allowed' : 'pointer',
  opacity: disabled ? 0.55 : 1,
  fontFamily: 'inherit',
  fontSize: 12.5,
  fontWeight: 700,
});

const keyInputStyle: CSSProperties = {
  width: '100%',
  minHeight: 38,
  padding: '8px 12px',
  borderRadius: 6,
  border: `1px solid ${COLORS.borderStrong}`,
  background: COLORS.bgPanel,
  color: COLORS.textPrimary,
  fontFamily: FONT_MONO,
  fontSize: 12,
  outline: 'none',
};

const runRowStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  alignItems: 'center',
  gap: 10,
  paddingTop: 4,
};

const runButtonStyle = (enabled: boolean): CSSProperties => ({
  minHeight: 44,
  padding: '11px 20px',
  borderRadius: 8,
  border: enabled
    ? `1px solid ${TONE_TINT.teal.border}`
    : `1px solid ${COLORS.borderSubtle}`,
  background: enabled ? TONE_TINT.teal.fill : 'rgba(148, 163, 184, 0.06)',
  color: enabled ? TONE_TINT.teal.text : COLORS.textMuted,
  cursor: enabled ? 'pointer' : 'not-allowed',
  fontFamily: 'inherit',
  fontSize: 13.5,
  fontWeight: 900,
  letterSpacing: 0.4,
  textTransform: 'uppercase',
});

const dividerStyle: CSSProperties = {
  height: 1,
  background: COLORS.borderSubtle,
  border: 'none',
  margin: 0,
};

/**
 * The single consolidated audit composer: target -> mode -> modules -> Run.
 *
 * It absorbs the old ModelConnectionCard (target/connect), the command-center
 * preset buttons + BYOK key field + live-worker chip into ONE calm surface so
 * the center column reads: run header -> composer -> stage ladder -> transcript.
 *
 * Honesty notes preserved: the live-worker chip renders ONLY the page-resolved
 * accent/label (teal exclusively for confirmed real weights). The composer never
 * produces a verdict — it just connects the target and fires the page's run
 * handler, which calls the unchanged audit API.
 */
export function AuditComposer({
  connectionStatus,
  modelName,
  provider,
  endpointLabel,
  statusDetail,
  lastChecked,
  canRunAudit = true,
  onConnect,
  onDisconnect,
  mode = 'BALANCED',
  moduleLabels = DEFAULT_MODULE_LABELS,
  presets = [],
  byokApiKey,
  onByokApiKeyChange,
  isAuditRunning = false,
  isTargetConnecting = false,
  onRun,
  runEnabled,
  runLabel,
  liveChip = null,
  emptyState,
  className,
}: AuditComposerProps): JSX.Element {
  const presetsDisabled = isAuditRunning || isTargetConnecting;

  return (
    <GlassPanel
      as="section"
      intensity="regular"
      padding={20}
      className={className}
      ariaLabel="CAS audit composer"
    >
      <div style={shellStyle}>
        <div style={headerStyle}>
          <div style={{ minWidth: 0 }}>
            <h2 style={titleStyle}>Set up an audit</h2>
            <AuditPopover
              briefing="Pick a target, confirm the mode and modules, then run. The visible path stays simple; the deep methodology lives behind the Why-this-verdict drawer."
              placement="bottom"
              width={340}
            >
              <p style={subtitleStyle}>Connect a model, then run the CAS audit.</p>
            </AuditPopover>
          </div>
          {liveChip ? (
            <span
              role="status"
              aria-label={`Live trace status: ${liveChip.label}`}
              title={liveChip.label}
              style={liveChipStyle(liveChip.accent)}
            >
              <span aria-hidden="true" style={liveDotStyle(liveChip.accent)} />
              {liveChip.label}
            </span>
          ) : null}
        </div>

        {emptyState ? <div>{emptyState}</div> : null}

        {/* Target — folds the existing ModelConnectionCard in unchanged. */}
        <ModelConnectionCard
          status={connectionStatus}
          modelName={modelName}
          provider={provider}
          endpointLabel={endpointLabel}
          statusDetail={statusDetail}
          lastChecked={lastChecked}
          isAuditRunning={isAuditRunning}
          canRunAudit={canRunAudit}
          onConnect={onConnect}
          onDisconnect={onDisconnect}
          onRunAudit={onRun}
        />

        {presets.length > 0 ? (
          <div style={fieldGroupStyle}>
            <p style={sectionLabelStyle}>Or load a demo packet</p>
            <div style={presetRowStyle}>
              {presets.map((preset) => (
                <button
                  key={preset.id}
                  type="button"
                  style={presetButtonStyle(presetsDisabled)}
                  onClick={preset.onSelect}
                  disabled={presetsDisabled}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        <hr style={dividerStyle} />

        {/* Mode + modules — read-only summary of the fixed audit contract. */}
        <div style={fieldGroupStyle}>
          <p style={sectionLabelStyle}>Mode</p>
          <div style={chipRowStyle}>
            <span style={modePillStyle}>{mode}</span>
          </div>
        </div>

        <div style={fieldGroupStyle}>
          <p style={sectionLabelStyle}>Modules</p>
          <div style={chipRowStyle} aria-label="Selected audit modules">
            {moduleLabels.map((label) => (
              <span key={label} style={moduleChipStyle}>
                {label}
              </span>
            ))}
          </div>
        </div>

        {/* BYOK — optional provider key, sent once, never stored. */}
        <div style={fieldGroupStyle}>
          <label htmlFor="composer-byok-key" style={sectionLabelStyle}>
            Provider API key (optional)
          </label>
          <input
            id="composer-byok-key"
            type="password"
            aria-label="Bring your own provider API key (optional)"
            autoComplete="off"
            spellCheck={false}
            value={byokApiKey}
            onChange={(event) => onByokApiKeyChange(event.target.value)}
            placeholder="Sent once with the run, never stored"
            disabled={presetsDisabled}
            style={keyInputStyle}
          />
        </div>

        <div style={runRowStyle}>
          <button
            type="button"
            style={runButtonStyle(runEnabled)}
            onClick={onRun}
            disabled={!runEnabled}
          >
            {runLabel}
          </button>
          <AuditPopover
            briefing="Run creates the audit session and starts it through the real CAS Harness API. The verdict and evidence appear in the right rail; the UI never fabricates a verdict."
            placement="right"
            width={340}
          >
            <span
              aria-label="What Run does"
              role="note"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: 22,
                height: 22,
                borderRadius: 5,
                border: `1px solid ${TONE_TINT.teal.borderSoft}`,
                background: TONE_TINT.teal.fillSoft,
                color: TONE_TINT.teal.text,
                cursor: 'help',
                fontSize: 12,
                fontWeight: 900,
              }}
            >
              ?
            </span>
          </AuditPopover>
        </div>
      </div>
    </GlassPanel>
  );
}

export default AuditComposer;

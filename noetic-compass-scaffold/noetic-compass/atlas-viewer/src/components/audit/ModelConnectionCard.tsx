import type { CSSProperties } from 'react';
import { GlassPanel } from '../ui/GlassPanel';
import {
  ACCENT_AMBER,
  ACCENT_TEAL,
  COLORS,
  FONT_FAMILY,
} from '../../lib/designTokens';

export type ModelConnectionStatus =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'error';

export interface ModelConnectionCardProps {
  status: ModelConnectionStatus;
  modelName?: string;
  provider?: string;
  endpointLabel?: string;
  statusDetail?: string;
  lastChecked?: string;
  isAuditRunning?: boolean;
  canRunAudit?: boolean;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onRunAudit?: () => void;
  className?: string;
}

const statusLabels: Record<ModelConnectionStatus, string> = {
  disconnected: 'Not connected',
  connecting: 'Connecting',
  connected: 'Connected',
  error: 'Connection error',
};

const statusTone: Record<
  ModelConnectionStatus,
  { color: string; border: string; fill: string; dot: string }
> = {
  disconnected: {
    color: COLORS.textSecondary,
    border: 'rgba(148, 163, 184, 0.22)',
    fill: 'rgba(255, 255, 255, 0.04)',
    dot: COLORS.textMuted,
  },
  connecting: {
    color: '#fef3c7',
    border: 'rgba(251, 191, 36, 0.38)',
    fill: 'rgba(251, 191, 36, 0.10)',
    dot: ACCENT_AMBER,
  },
  connected: {
    color: '#ccfbf1',
    border: 'rgba(45, 212, 191, 0.42)',
    fill: 'rgba(45, 212, 191, 0.11)',
    dot: ACCENT_TEAL,
  },
  error: {
    color: '#ffe4e6',
    border: 'rgba(251, 113, 133, 0.40)',
    fill: 'rgba(251, 113, 133, 0.10)',
    dot: '#fb7185',
  },
};

const shellStyle: CSSProperties = {
  display: 'grid',
  gap: 16,
  fontFamily: FONT_FAMILY,
};

const headerStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  gap: 12,
};

const titleStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textPrimary,
  fontSize: 18,
  lineHeight: 1.2,
  fontWeight: 800,
  letterSpacing: 0,
};

const subtitleStyle: CSSProperties = {
  margin: '6px 0 0',
  color: COLORS.textSecondary,
  fontSize: 13,
  lineHeight: 1.45,
};

const statusPillStyle = (status: ModelConnectionStatus): CSSProperties => {
  const tone = statusTone[status];
  return {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
    minHeight: 30,
    padding: '5px 10px',
    borderRadius: 6,
    border: `1px solid ${tone.border}`,
    background: tone.fill,
    color: tone.color,
    fontSize: 12,
    fontWeight: 800,
    whiteSpace: 'nowrap',
  };
};

const dotStyle = (status: ModelConnectionStatus): CSSProperties => ({
  width: 8,
  height: 8,
  borderRadius: '50%',
  background: statusTone[status].dot,
});

const detailsGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
  gap: 10,
};

const detailTileStyle: CSSProperties = {
  padding: '11px 12px',
  borderRadius: 8,
  border: `1px solid ${COLORS.borderSubtle}`,
  background: 'rgba(2, 6, 23, 0.34)',
};

const detailLabelStyle: CSSProperties = {
  display: 'block',
  color: COLORS.textMuted,
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: 0,
  textTransform: 'uppercase',
};

const detailValueStyle: CSSProperties = {
  display: 'block',
  marginTop: 5,
  color: COLORS.textPrimary,
  fontSize: 13,
  fontWeight: 700,
  overflowWrap: 'anywhere',
};

const actionRowStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 10,
};

const buttonStyle: CSSProperties = {
  minHeight: 34,
  padding: '7px 12px',
  borderRadius: 6,
  border: `1px solid ${COLORS.borderStrong}`,
  background: 'rgba(255, 255, 255, 0.04)',
  color: COLORS.textPrimary,
  cursor: 'pointer',
  fontFamily: 'inherit',
  fontSize: 13,
  fontWeight: 800,
};

const primaryButtonStyle: CSSProperties = {
  ...buttonStyle,
  border: '1px solid rgba(45, 212, 191, 0.45)',
  background: 'rgba(45, 212, 191, 0.12)',
  color: '#ccfbf1',
};

const disabledButtonStyle: CSSProperties = {
  ...buttonStyle,
  cursor: 'not-allowed',
  opacity: 0.48,
};

export function ModelConnectionCard({
  status,
  modelName = 'No model selected',
  provider = 'Provider not set',
  endpointLabel = 'Endpoint not set',
  statusDetail,
  lastChecked,
  isAuditRunning = false,
  canRunAudit = true,
  onConnect,
  onDisconnect,
  onRunAudit,
  className,
}: ModelConnectionCardProps): JSX.Element {
  const runDisabled = status !== 'connected' || isAuditRunning || !canRunAudit;
  const connectDisabled = status === 'connecting';

  return (
    <GlassPanel
      as="section"
      intensity="thin"
      padding={18}
      className={className}
      ariaLabel="Model connection"
    >
      <div style={shellStyle}>
        <div style={headerStyle}>
          <div>
            <h2 style={titleStyle}>Model connection</h2>
            <p style={subtitleStyle}>
              Verify target, then run audit.
            </p>
          </div>
          <span style={statusPillStyle(status)}>
            <span aria-hidden="true" style={dotStyle(status)} />
            {statusLabels[status]}
          </span>
        </div>

        {statusDetail ? (
          <p style={{ margin: 0, color: COLORS.textSecondary, fontSize: 13 }}>
            {statusDetail}
          </p>
        ) : null}

        <div style={detailsGridStyle}>
          <div style={detailTileStyle}>
            <span style={detailLabelStyle}>Model</span>
            <span style={detailValueStyle}>{modelName}</span>
          </div>
          <div style={detailTileStyle}>
            <span style={detailLabelStyle}>Runtime</span>
            <span style={detailValueStyle}>{provider}</span>
          </div>
          <div style={detailTileStyle}>
            <span style={detailLabelStyle}>API route</span>
            <span style={detailValueStyle}>{endpointLabel}</span>
          </div>
          <div style={detailTileStyle}>
            <span style={detailLabelStyle}>Backend</span>
            <span style={detailValueStyle}>{lastChecked ?? 'Not checked'}</span>
          </div>
        </div>

        <div style={actionRowStyle}>
          {status === 'connected' && onDisconnect ? (
            <button type="button" style={buttonStyle} onClick={onDisconnect}>
              Disconnect
            </button>
          ) : (
            <button
              type="button"
              style={connectDisabled ? disabledButtonStyle : buttonStyle}
              onClick={onConnect}
              disabled={connectDisabled}
            >
              {status === 'connecting' ? 'Connecting...' : 'Connect model'}
            </button>
          )}
          <button
            type="button"
            style={runDisabled ? disabledButtonStyle : primaryButtonStyle}
            onClick={onRunAudit}
            disabled={runDisabled}
          >
            {isAuditRunning ? 'Running audit...' : 'Run audit'}
          </button>
        </div>
      </div>
    </GlassPanel>
  );
}

export default ModelConnectionCard;

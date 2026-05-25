import type { CSSProperties, ReactNode } from 'react';

import {
  ACCENT_TEAL,
  COLORS,
  FONT_MONO,
  THEME,
} from '../../lib/designTokens';

const REALMODE_PASS_VERDICT = 'REAL_PYTHIA_WEIGHTS_LOADED';

export type LiveProofConnectionState =
  | 'idle'
  | 'checking'
  | 'connecting'
  | 'streaming'
  | 'complete'
  | 'unavailable'
  | 'failed';

export interface LiveProofStatus {
  verdict?: string | null;
  httpStatus?: number | null;
  isRealModel?: boolean | null;
  modelLoaded?: boolean | null;
  fakeRuntimeEnv?: boolean | null;
  manifestIsRealModel?: boolean | null;
  loadError?: string | null;
  checkedAt?: string | null;
  workerVersion?: string | null;
}

export interface LiveManifestStatus {
  isRealModel?: boolean | null;
  modelId?: string | null;
  workerVersion?: string | null;
}

export interface LiveStreamStatus {
  streamTokenIssued?: boolean | null;
  tokenCount?: number | null;
  currentTokenIndex?: number | null;
  eventCount?: number | null;
  lastEventAt?: string | null;
}

export interface LiveProofPanelProps {
  connectionState: LiveProofConnectionState;
  modelId?: string | null;
  proof?: LiveProofStatus | null;
  manifest?: LiveManifestStatus | null;
  stream?: LiveStreamStatus | null;
  failureReason?: string | null;
  onRefreshProof?: () => void;
}

const panelStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
  padding: 12,
  borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
  fontFamily: THEME.fontFamily,
};

const headerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'flex-start',
  justifyContent: 'space-between',
  gap: 10,
};

const eyebrowStyle: CSSProperties = {
  margin: 0,
  color: ACCENT_TEAL,
  fontSize: 10.5,
  fontWeight: 800,
  letterSpacing: 1.2,
  textTransform: 'uppercase',
};

const titleStyle: CSSProperties = {
  margin: '2px 0 0',
  color: COLORS.textPrimary,
  fontSize: 16,
  fontWeight: 800,
  lineHeight: 1.2,
};

const bodyStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 12,
  lineHeight: 1.45,
};

const statusStyle = (tone: 'verified' | 'loading' | 'failed' | 'neutral'): CSSProperties => {
  const color =
    tone === 'verified'
      ? '#86efac'
      : tone === 'loading'
        ? '#fde68a'
        : tone === 'failed'
          ? '#fca5a5'
          : COLORS.textSecondary;
  const border =
    tone === 'verified'
      ? 'rgba(34, 197, 94, 0.35)'
      : tone === 'loading'
        ? 'rgba(251, 191, 36, 0.35)'
        : tone === 'failed'
          ? 'rgba(248, 113, 113, 0.35)'
          : COLORS.borderSubtle;
  const background =
    tone === 'verified'
      ? 'rgba(34, 197, 94, 0.10)'
      : tone === 'loading'
        ? 'rgba(251, 191, 36, 0.10)'
        : tone === 'failed'
          ? 'rgba(248, 113, 113, 0.10)'
          : 'rgba(255, 255, 255, 0.03)';
  return {
    display: 'inline-flex',
    alignItems: 'center',
    alignSelf: 'flex-start',
    minHeight: 26,
    padding: '4px 8px',
    borderRadius: 6,
    border: `1px solid ${border}`,
    color,
    background,
    fontSize: 11.5,
    fontWeight: 800,
    whiteSpace: 'nowrap',
  };
};

const refreshButtonStyle: CSSProperties = {
  minHeight: 28,
  padding: '4px 8px',
  borderRadius: 6,
  border: '1px solid rgba(45, 212, 191, 0.35)',
  background: 'rgba(45, 212, 191, 0.08)',
  color: ACCENT_TEAL,
  fontFamily: 'inherit',
  fontSize: 11.5,
  fontWeight: 700,
  cursor: 'pointer',
};

const gridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '1fr',
  gap: 6,
};

const rowStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '120px minmax(0, 1fr)',
  gap: 8,
  padding: '7px 0',
  borderTop: '1px solid rgba(255, 255, 255, 0.06)',
};

const labelStyle: CSSProperties = {
  color: COLORS.textMuted,
  fontSize: 11,
  fontWeight: 800,
  lineHeight: 1.35,
};

const valueStyle: CSSProperties = {
  color: COLORS.textPrimary,
  fontSize: 11.5,
  lineHeight: 1.35,
  minWidth: 0,
  overflowWrap: 'anywhere',
};

const monoStyle: CSSProperties = {
  fontFamily: FONT_MONO,
  fontSize: 11,
};

const warningStyle: CSSProperties = {
  margin: 0,
  padding: '8px 9px',
  borderRadius: 6,
  border: '1px solid rgba(251, 191, 36, 0.24)',
  background: 'rgba(251, 191, 36, 0.08)',
  color: '#fde68a',
  fontSize: 11.5,
  lineHeight: 1.4,
};

const failureStyle: CSSProperties = {
  ...warningStyle,
  border: '1px solid rgba(248, 113, 113, 0.30)',
  background: 'rgba(248, 113, 113, 0.10)',
  color: '#fecaca',
};

function proofVerified(proof: LiveProofStatus | null | undefined): boolean {
  return (
    proof?.verdict === REALMODE_PASS_VERDICT &&
    proof.httpStatus === 200 &&
    proof.isRealModel === true &&
    proof.modelLoaded === true &&
    proof.loadError === null &&
    proof.fakeRuntimeEnv !== true &&
    proof.manifestIsRealModel !== false
  );
}

function toneFor(
  connectionState: LiveProofConnectionState,
  verified: boolean,
): 'verified' | 'loading' | 'failed' | 'neutral' {
  if (verified) return 'verified';
  if (connectionState === 'checking' || connectionState === 'connecting') return 'loading';
  if (connectionState === 'failed' || connectionState === 'unavailable') return 'failed';
  return 'neutral';
}

function connectionLabel(connectionState: LiveProofConnectionState): string {
  switch (connectionState) {
    case 'idle':
      return 'Not started';
    case 'checking':
      return 'Checking real-weight proof';
    case 'connecting':
      return 'Opening LIVE stream';
    case 'streaming':
      return 'LIVE stream connected';
    case 'complete':
      return 'LIVE stream complete';
    case 'unavailable':
      return 'LIVE worker unavailable';
    case 'failed':
      return 'LIVE proof failed';
  }
}

function topLine(
  connectionState: LiveProofConnectionState,
  proof: LiveProofStatus | null | undefined,
): string {
  if (proofVerified(proof)) {
    return 'Real Pythia weights verified.';
  }
  if (connectionState === 'checking' || connectionState === 'connecting') {
    return 'Real-weight proof is still running. Do not call this actual weights yet.';
  }
  if (connectionState === 'unavailable') {
    return 'Live model is unavailable. Actual weights are not proven.';
  }
  if (connectionState === 'failed') {
    return 'Live model proof failed. Actual weights are not proven.';
  }
  return 'Actual weights not proven yet.';
}

function yesNo(value: boolean | null | undefined): string {
  if (value === true) return 'yes';
  if (value === false) return 'no';
  return 'not reported';
}

function formatCount(value: number | null | undefined): string {
  return typeof value === 'number' && Number.isFinite(value) ? String(value) : 'not reported';
}

function formatTokenPosition(stream: LiveStreamStatus | null | undefined): string {
  const count = stream?.tokenCount;
  const index = stream?.currentTokenIndex;
  if (
    typeof count === 'number' &&
    Number.isFinite(count) &&
    typeof index === 'number' &&
    Number.isFinite(index)
  ) {
    return `${Math.max(0, index + 1)} / ${Math.max(0, count)}`;
  }
  if (typeof count === 'number' && Number.isFinite(count)) {
    return `${Math.max(0, count)} token${count === 1 ? '' : 's'} seen`;
  }
  return 'not reported';
}

function formatTime(value: string | null | undefined): string {
  if (!value) return 'not reported';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
  });
}

interface ProofRowProps {
  label: string;
  children: ReactNode;
  testId?: string;
}

function ProofRow({ label, children, testId }: ProofRowProps): JSX.Element {
  return (
    <div style={rowStyle} data-testid={testId}>
      <span style={labelStyle}>{label}</span>
      <span style={valueStyle}>{children}</span>
    </div>
  );
}

export default function LiveProofPanel({
  connectionState,
  modelId,
  proof,
  manifest,
  stream,
  failureReason,
  onRefreshProof,
}: LiveProofPanelProps): JSX.Element {
  const verified = proofVerified(proof);
  const visibleModelId = modelId ?? manifest?.modelId ?? 'not reported';
  const workerVersion = proof?.workerVersion ?? manifest?.workerVersion ?? 'not reported';
  const manifestIsRealModel =
    manifest?.isRealModel ?? proof?.manifestIsRealModel ?? null;
  const streamTokenIssued = stream?.streamTokenIssued;

  return (
    <section
      style={panelStyle}
      aria-label="Live model proof"
      data-testid="live-proof-panel"
      data-verified={verified ? 'true' : 'false'}
    >
      <div style={headerStyle}>
        <div>
          <p style={eyebrowStyle}>LIVE proof</p>
          <h2 style={titleStyle}>Is Atlas actually connected?</h2>
        </div>
        {onRefreshProof ? (
          <button
            type="button"
            onClick={onRefreshProof}
            style={refreshButtonStyle}
            data-testid="live-proof-refresh"
          >
            Recheck
          </button>
        ) : null}
      </div>

      <span style={statusStyle(toneFor(connectionState, verified))} data-testid="live-proof-status">
        {verified ? 'VERIFIED REAL WEIGHTS' : connectionLabel(connectionState)}
      </span>

      <p style={bodyStyle} data-testid="live-proof-topline">
        {topLine(connectionState, proof)}
      </p>

      <div style={gridStyle}>
        <ProofRow label="Connection" testId="live-proof-connection">
          {connectionLabel(connectionState)}
        </ProofRow>
        <ProofRow label="Model" testId="live-proof-model">
          <span style={monoStyle}>{visibleModelId}</span>
        </ProofRow>
        <ProofRow label="Proof verdict" testId="live-proof-verdict">
          <span style={monoStyle}>{proof?.verdict ?? 'not reported'}</span>
        </ProofRow>
        <ProofRow label="Proof status" testId="live-proof-http-status">
          {typeof proof?.httpStatus === 'number' ? proof.httpStatus : 'not reported'}
        </ProofRow>
        <ProofRow label="Actual weights" testId="live-proof-actual-weights">
          {verified ? 'proven by /atlas/live/health/realmode' : 'not proven'}
        </ProofRow>
        <ProofRow label="Manifest real" testId="live-proof-manifest-real">
          manifest is_real_model: {yesNo(manifestIsRealModel)}
        </ProofRow>
        <ProofRow label="Worker mode" testId="live-proof-worker-mode">
          fake/demo env: {yesNo(proof?.fakeRuntimeEnv)}
        </ProofRow>
        <ProofRow label="Stream token" testId="live-proof-stream-token">
          {streamTokenIssued === true
            ? 'issued'
            : streamTokenIssued === false
              ? 'not issued'
              : 'not reported'}
        </ProofRow>
        <ProofRow label="Token status" testId="live-proof-token-count">
          {formatTokenPosition(stream)}; events: {formatCount(stream?.eventCount)}
        </ProofRow>
        <ProofRow label="Last event" testId="live-proof-last-event">
          {formatTime(stream?.lastEventAt)}
        </ProofRow>
        <ProofRow label="Checked" testId="live-proof-checked-at">
          {formatTime(proof?.checkedAt)}
        </ProofRow>
        <ProofRow label="Worker" testId="live-proof-worker-version">
          <span style={monoStyle}>{workerVersion}</span>
        </ProofRow>
      </div>

      {proof?.loadError ? (
        <p style={failureStyle} data-testid="live-proof-load-error">
          Load error: {proof.loadError}
        </p>
      ) : null}

      {failureReason ? (
        <p style={failureStyle} data-testid="live-proof-failure">
          Failure reason: {failureReason}
        </p>
      ) : null}

      {!verified && !failureReason && !proof?.loadError ? (
        <p style={warningStyle} data-testid="live-proof-boundary">
          Boundary: this panel only says real weights when the worker proof and stream
          manifest support it. Otherwise it stays replay/unproven.
        </p>
      ) : null}
    </section>
  );
}

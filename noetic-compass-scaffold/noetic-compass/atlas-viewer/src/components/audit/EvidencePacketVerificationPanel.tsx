import { useEffect, useMemo, useState, type CSSProperties } from 'react';
import {
  verifyEvidencePacket,
  type EvidenceVerifyCheck,
  type EvidenceVerifyResponse,
} from '../../lib/evidencePacketVerification';
import { AuditPopover } from './AuditPopover';
import {
  ACCENT_TEAL,
  COLORS,
  FONT_FAMILY,
  FONT_MONO,
} from '../../lib/designTokens';

export interface EvidencePacketVerificationPanelProps {
  traceId: string | null | undefined;
  authToken?: string | null;
  fetchImpl?: typeof fetch;
}

type VerifyState =
  | { status: 'idle'; response?: undefined; error?: undefined }
  | { status: 'loading'; response?: undefined; error?: undefined }
  | { status: 'loaded'; response: EvidenceVerifyResponse; error?: undefined }
  | { status: 'error'; response?: undefined; error: string };

const panelStyle: CSSProperties = {
  display: 'grid',
  gap: 12,
  padding: 16,
  borderRadius: 8,
  border: '1px solid rgba(45, 212, 191, 0.22)',
  background: 'rgba(2, 6, 23, 0.40)',
  fontFamily: FONT_FAMILY,
};

const headerStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  alignItems: 'flex-start',
  justifyContent: 'space-between',
  gap: 12,
};

const eyebrowStyle: CSSProperties = {
  margin: 0,
  color: ACCENT_TEAL,
  fontSize: 11,
  fontWeight: 800,
  letterSpacing: 0.6,
  textTransform: 'uppercase',
};

const titleStyle: CSSProperties = {
  margin: '4px 0 0',
  color: COLORS.textPrimary,
  fontSize: 18,
  fontWeight: 900,
  letterSpacing: 0,
};

const textStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 13,
  lineHeight: 1.45,
};

const monoStyle: CSSProperties = {
  fontFamily: FONT_MONO,
  overflowWrap: 'anywhere',
};

const buttonStyle = (enabled: boolean): CSSProperties => ({
  minHeight: 38,
  padding: '8px 12px',
  borderRadius: 6,
  border: enabled
    ? '1px solid rgba(45, 212, 191, 0.50)'
    : '1px solid rgba(148, 163, 184, 0.22)',
  background: enabled ? 'rgba(45, 212, 191, 0.13)' : 'rgba(148, 163, 184, 0.06)',
  color: enabled ? '#ccfbf1' : COLORS.textMuted,
  cursor: enabled ? 'pointer' : 'not-allowed',
  fontFamily: 'inherit',
  fontSize: 12,
  fontWeight: 900,
  textTransform: 'uppercase',
});

const statusPillStyle = (tone: 'verified' | 'warning' | 'failed' | 'muted'): CSSProperties => ({
  display: 'inline-flex',
  width: 'fit-content',
  alignItems: 'center',
  minHeight: 26,
  padding: '4px 8px',
  borderRadius: 5,
  border:
    tone === 'verified'
      ? '1px solid rgba(45, 212, 191, 0.38)'
      : tone === 'failed'
        ? '1px solid rgba(251, 113, 133, 0.40)'
        : tone === 'warning'
          ? '1px solid rgba(251, 191, 36, 0.36)'
          : '1px solid rgba(148, 163, 184, 0.22)',
  background:
    tone === 'verified'
      ? 'rgba(45, 212, 191, 0.11)'
      : tone === 'failed'
        ? 'rgba(251, 113, 133, 0.10)'
        : tone === 'warning'
          ? 'rgba(251, 191, 36, 0.10)'
          : 'rgba(148, 163, 184, 0.07)',
  color:
    tone === 'verified'
      ? '#ccfbf1'
      : tone === 'failed'
        ? '#ffe4e6'
        : tone === 'warning'
          ? '#fef3c7'
          : COLORS.textMuted,
  fontFamily: FONT_MONO,
  fontSize: 11,
  fontWeight: 900,
  textTransform: 'uppercase',
});

const checkGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
  gap: 8,
};

const checkStyle: CSSProperties = {
  padding: 10,
  borderRadius: 6,
  border: '1px solid rgba(148, 163, 184, 0.16)',
  background: 'rgba(15, 23, 42, 0.42)',
};

const checksDetailsStyle: CSSProperties = {
  borderRadius: 7,
  border: '1px solid rgba(148, 163, 184, 0.18)',
  background: 'rgba(2, 6, 23, 0.24)',
};

const checksSummaryStyle: CSSProperties = {
  padding: '10px 12px',
  color: COLORS.textSecondary,
  cursor: 'pointer',
  fontSize: 12,
  fontWeight: 800,
};

const checkDetailStyle: CSSProperties = {
  ...textStyle,
  ...monoStyle,
  marginTop: 5,
  fontSize: 11.5,
};

function externalAnchorCheck(response: EvidenceVerifyResponse | undefined): EvidenceVerifyCheck | null {
  return response?.checks.find((check) => check.artifact === 'merged_packet_external_anchor') ?? null;
}

function isWormRetained(check: EvidenceVerifyCheck | null): boolean {
  const notes = check?.notes?.toLowerCase() ?? '';
  return check?.match === true && notes.includes('object lock') && notes.includes('retention is active');
}

function isS3Verified(check: EvidenceVerifyCheck | null): boolean {
  const notes = check?.notes?.toLowerCase() ?? '';
  return check?.match === true && notes.includes('object was re-read');
}

function statusLabel(state: VerifyState): { label: string; tone: 'verified' | 'warning' | 'failed' | 'muted' } {
  if (state.status === 'idle') return { label: 'Not checked', tone: 'muted' };
  if (state.status === 'loading') return { label: 'Checking', tone: 'muted' };
  if (state.status === 'error') return { label: 'Verify failed', tone: 'failed' };
  // Packet-wide integrity dominates any individual anchor check. A retained
  // anchor must never hide a mismatch elsewhere in the packet.
  if (state.response.overall === 'partial_mismatch') return { label: 'Mismatch', tone: 'failed' };
  if (state.response.overall !== 'all_match') return { label: 'Unable to verify', tone: 'warning' };
  const anchor = externalAnchorCheck(state.response);
  if (isWormRetained(anchor)) return { label: 'WORM retained', tone: 'verified' };
  if (isS3Verified(anchor)) return { label: 'S3 verified', tone: 'verified' };
  return { label: 'Hashes match', tone: 'verified' };
}

function summaryText(state: VerifyState): string {
  if (state.status === 'idle') {
    return 'Run verify to re-read the packet anchor, compare hashes, and confirm whether Object Lock retention is active.';
  }
  if (state.status === 'loading') {
    return 'Re-reading packet artifacts and anchor receipt.';
  }
  if (state.status === 'error') {
    return state.error;
  }
  if (state.response.overall === 'partial_mismatch') {
    return 'Packet verification found one or more mismatches. Inspect every failed check before trusting the packet or its anchor.';
  }
  if (state.response.overall !== 'all_match') {
    return 'Packet verification could not establish integrity. Inspect the available checks before trusting this packet.';
  }
  const anchor = externalAnchorCheck(state.response);
  if (isWormRetained(anchor)) {
    return anchor?.notes ?? 'S3 anchor re-read matched and Object Lock retention is active.';
  }
  if (isS3Verified(anchor)) {
    return anchor?.notes ?? 'S3 anchor object was re-read and matched the packet manifest.';
  }
  return 'All available packet hashes matched. No WORM-retention proof was returned for this packet.';
}

function orderedChecks(response: EvidenceVerifyResponse | undefined): EvidenceVerifyCheck[] {
  if (!response) return [];
  return [...response.checks].sort((left, right) => Number(left.match) - Number(right.match));
}

function checkSummary(response: EvidenceVerifyResponse): string {
  const failed = response.checks.filter((check) => !check.match).length;
  if (failed === 0) return `Verification checks (${response.checks.length} passed)`;
  return `Verification checks (${failed} failed of ${response.checks.length})`;
}

export function EvidencePacketVerificationPanel({
  traceId,
  authToken,
  fetchImpl,
}: EvidencePacketVerificationPanelProps): JSX.Element | null {
  const [state, setState] = useState<VerifyState>({ status: 'idle' });
  const cleanedTraceId = traceId?.trim() ?? '';
  const cleanedAuthToken = authToken?.trim() ?? '';
  const canVerify =
    cleanedTraceId.length > 0 && cleanedAuthToken.length > 0 && state.status !== 'loading';
  const status = statusLabel(state);
  const visibleChecks = useMemo(
    () => orderedChecks(state.status === 'loaded' ? state.response : undefined),
    [state],
  );

  useEffect(() => {
    setState({ status: 'idle' });
  }, [cleanedAuthToken, cleanedTraceId]);

  if (!cleanedTraceId) return null;

  const runVerify = async (): Promise<void> => {
    if (!canVerify) return;
    setState({ status: 'loading' });
    try {
      const response = await verifyEvidencePacket(cleanedTraceId, {
        authToken: cleanedAuthToken,
        fetchImpl,
      });
      setState({ status: 'loaded', response });
    } catch (error) {
      setState({
        status: 'error',
        error: error instanceof Error ? error.message : 'Evidence Packet verification failed.',
      });
    }
  };

  return (
    <section
      id="evidence-packet-verification"
      style={panelStyle}
      aria-label="Evidence Packet verification"
    >
      <div style={headerStyle}>
        <div>
          <p style={eyebrowStyle}>Evidence Packet verification</p>
          <AuditPopover
            briefing="This re-runs the backend packet verifier. It proves whether stored artifacts still hash-match and whether the S3 anchor is protected by active Object Lock retention."
            placement="bottom"
            width={380}
          >
            <h2 style={titleStyle}>Packet chain check</h2>
          </AuditPopover>
        </div>
        <button
          aria-busy={state.status === 'loading'}
          type="button"
          style={buttonStyle(canVerify)}
          disabled={!canVerify}
          onClick={() => {
            void runVerify();
          }}
        >
          Verify packet
        </button>
      </div>

      <div aria-atomic="true" aria-live="polite" role="status">
        <span style={statusPillStyle(status.tone)}>{status.label}</span>
        <p style={{ ...textStyle, marginTop: 8 }}>{summaryText(state)}</p>
      </div>
      <p style={{ ...textStyle, ...monoStyle }}>trace_id: {cleanedTraceId}</p>
      {!cleanedAuthToken ? (
        <p role="note" style={textStyle}>
          Enter the protected API token to run the authenticated POST verification.
        </p>
      ) : null}

      {state.status === 'loaded' && visibleChecks.length > 0 ? (
        <details
          open={visibleChecks.some((check) => !check.match)}
          style={checksDetailsStyle}
        >
          <summary style={checksSummaryStyle}>{checkSummary(state.response)}</summary>
          <div
            style={{ ...checkGridStyle, padding: '0 10px 10px' }}
            aria-label="Evidence Packet verify checks"
          >
            {visibleChecks.map((check) => (
              <article key={check.artifact} style={checkStyle} data-check-match={check.match}>
                <p style={{ ...textStyle, color: COLORS.textPrimary, fontWeight: 800 }}>
                  {check.artifact.replaceAll('_', ' ')}
                </p>
                <p style={textStyle}>{check.match ? 'match' : 'not matched'}</p>
                <p style={checkDetailStyle}>expected: {check.expected ?? 'unavailable'}</p>
                <p style={checkDetailStyle}>actual: {check.actual ?? 'unavailable'}</p>
                {check.notes ? <p style={checkDetailStyle}>notes: {check.notes}</p> : null}
              </article>
            ))}
          </div>
        </details>
      ) : null}
    </section>
  );
}

export default EvidencePacketVerificationPanel;

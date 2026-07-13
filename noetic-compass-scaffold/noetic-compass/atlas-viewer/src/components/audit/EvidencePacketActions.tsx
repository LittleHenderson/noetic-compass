import { useEffect, useMemo, useState, type CSSProperties } from 'react';
import {
  authorizationHeaderValue,
  evidencePacketUrl,
} from '../../lib/evidencePacketVerification';
import { ACCENT_TEAL, COLORS, FONT_FAMILY, FONT_MONO } from '../../lib/designTokens';

export interface EvidencePacketActionsProps {
  traceId: string | null | undefined;
  authToken?: string | null;
  fetchImpl?: typeof fetch;
  missingAuthMessage?: string;
}

type ActionState = 'idle' | 'loading' | 'success' | 'error';

const shellStyle: CSSProperties = {
  display: 'grid',
  gap: 10,
  padding: 14,
  borderRadius: 8,
  border: '1px solid rgba(45, 212, 191, 0.20)',
  background: 'rgba(15, 23, 42, 0.42)',
  fontFamily: FONT_FAMILY,
};

const headingStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textPrimary,
  fontSize: 15,
  fontWeight: 850,
};

const textStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 12.5,
  lineHeight: 1.45,
};

const actionRowStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 8,
};

const actionStyle = (enabled: boolean): CSSProperties => ({
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  minHeight: 36,
  padding: '7px 11px',
  borderRadius: 6,
  border: enabled
    ? '1px solid rgba(45, 212, 191, 0.45)'
    : '1px solid rgba(148, 163, 184, 0.20)',
  background: enabled ? 'rgba(45, 212, 191, 0.11)' : 'rgba(148, 163, 184, 0.05)',
  color: enabled ? ACCENT_TEAL : COLORS.textMuted,
  cursor: enabled ? 'pointer' : 'not-allowed',
  fontFamily: FONT_MONO,
  fontSize: 11,
  fontWeight: 850,
  textDecoration: 'none',
  textTransform: 'uppercase',
});

function absoluteAuditReviewUrl(traceId: string): string {
  const path = `/audit-console?trace=${encodeURIComponent(traceId)}#evidence-packet-verification`;
  if (typeof window === 'undefined') return path;
  return `${window.location.origin}${path}`;
}

function packetFilename(traceId: string): string {
  const safeTraceId = traceId.replace(/[^A-Za-z0-9._-]+/g, '-');
  return `cas-harness-evidence-${safeTraceId || 'packet'}.json`;
}

async function responseError(response: Response): Promise<string> {
  const body = await response.json().catch(() => null) as { detail?: unknown } | null;
  if (body && typeof body.detail === 'string' && body.detail.trim()) return body.detail;
  return response.statusText || `HTTP ${response.status}`;
}

export function EvidencePacketActions({
  traceId,
  authToken,
  fetchImpl,
  missingAuthMessage = 'Sign in with the customer account that owns this audit to enable packet access.',
}: EvidencePacketActionsProps): JSX.Element {
  const cleanedTraceId = traceId?.trim() ?? '';
  const cleanedAuthToken = authToken?.trim() ?? '';
  const hasPacket = cleanedTraceId.length > 0;
  const canDownload = hasPacket && cleanedAuthToken.length > 0;
  const [downloadState, setDownloadState] = useState<ActionState>('idle');
  const [copyState, setCopyState] = useState<ActionState>('idle');
  const packetUrl = useMemo(
    () => (hasPacket ? evidencePacketUrl(cleanedTraceId) : ''),
    [cleanedTraceId, hasPacket],
  );
  const reviewUrl = useMemo(
    () => (hasPacket ? absoluteAuditReviewUrl(cleanedTraceId) : ''),
    [cleanedTraceId, hasPacket],
  );

  useEffect(() => {
    setDownloadState('idle');
    setCopyState('idle');
  }, [cleanedTraceId]);

  const downloadPacket = async (): Promise<void> => {
    if (!canDownload || downloadState === 'loading') return;
    const request = fetchImpl ?? (typeof fetch !== 'undefined' ? fetch : undefined);
    const authorization = authorizationHeaderValue(cleanedAuthToken);
    if (!request || !authorization) {
      setDownloadState('error');
      return;
    }

    setDownloadState('loading');
    try {
      const response = await request(packetUrl, {
        method: 'GET',
        headers: {
          Accept: 'application/json',
          Authorization: authorization,
        },
      });
      if (!response.ok) throw new Error(await responseError(response));

      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const revokeObjectUrl = URL.revokeObjectURL.bind(URL);
      const anchor = document.createElement('a');
      anchor.href = objectUrl;
      anchor.download = packetFilename(cleanedTraceId);
      anchor.rel = 'noopener noreferrer';
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      // Give the browser time to consume the Blob URL before releasing it.
      // Immediate revocation races downloads in Safari and some Chromium builds.
      window.setTimeout(() => revokeObjectUrl(objectUrl), 60_000);
      setDownloadState('success');
    } catch {
      setDownloadState('error');
    }
  };

  const copyReviewLink = async (): Promise<void> => {
    if (!hasPacket || !navigator.clipboard?.writeText) {
      setCopyState('error');
      return;
    }
    try {
      await navigator.clipboard.writeText(reviewUrl);
      setCopyState('success');
    } catch {
      setCopyState('error');
    }
  };

  const downloadStatusMessage = downloadState === 'loading'
      ? 'Preparing the authenticated Evidence Packet download...'
    : downloadState === 'success'
      ? 'Evidence Packet download started.'
      : downloadState === 'error'
        ? 'Evidence Packet download failed. Check the signed-in account session and try again.'
        : null;
  const copyStatusMessage = copyState === 'success'
    ? 'Evidence Packet review link copied.'
    : copyState === 'error'
      ? 'Evidence Packet review link could not be copied.'
      : null;

  return (
    <section style={shellStyle} aria-label="Evidence Packet actions">
      <h2 style={headingStyle}>Evidence Packet actions</h2>
      <p style={textStyle}>
        Download uses the current Bearer token. The review link opens this Audit Console at the
        packet verifier; it never points at the POST-only verification API.
      </p>
      <div style={actionRowStyle}>
        <button
          type="button"
          disabled={!canDownload || downloadState === 'loading'}
          style={actionStyle(canDownload && downloadState !== 'loading')}
          onClick={() => {
            void downloadPacket();
          }}
        >
          {downloadState === 'loading'
            ? 'Preparing Evidence Packet'
            : 'Download Evidence Packet'}
        </button>
        <button
          type="button"
          disabled={!hasPacket}
          style={actionStyle(hasPacket)}
          onClick={() => {
            void copyReviewLink();
          }}
        >
          Copy Evidence Packet review link
        </button>
      </div>
      {hasPacket && !cleanedAuthToken ? (
        <p role="note" style={textStyle}>
          {missingAuthMessage}
        </p>
      ) : null}
      {downloadStatusMessage ? (
        <p aria-live="polite" role="status" style={textStyle}>{downloadStatusMessage}</p>
      ) : null}
      {copyStatusMessage ? (
        <p aria-live="polite" role="status" style={textStyle}>{copyStatusMessage}</p>
      ) : null}
    </section>
  );
}

export default EvidencePacketActions;

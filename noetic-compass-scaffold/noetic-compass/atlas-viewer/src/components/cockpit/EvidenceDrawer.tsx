import { useEffect, useMemo, useRef, useState } from 'react';
import type { CSSProperties } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GlassPanel } from '../ui/GlassPanel';
import { THEME, SPRING_GENTLE } from '../../lib/designTokens';
import { ATLAS_STATUS_COLORS } from '../../lib/atlasPalette';
import { resolveAtlasApiBaseUrl } from '../../lib/atlasLiveApi';
import BlindspotInterpretation from './BlindspotInterpretation';
import type { DriveId, RegisterId } from '../../lib/driveTranslations';

export interface BlindspotInterpretationRef {
  driveId: DriveId;
  register?: RegisterId;
  confidence: number | null;
  evidenceSources: string[];
}

export interface EvidenceDrawerPayload {
  source: 'neuron' | 'primitive' | 'other';
  title: string;
  evidence_ref?: unknown;
  detail?: unknown;
  /**
   * Optional plain-English blindspot interpretations for this artifact.
   * Populated by the cockpit when the clicked neuron belongs to one or
   * more cover classes. The drawer renders these BELOW the existing
   * Evidence Packet payload — see PR #45/#46/#50.
   */
  blindspotInterpretations?: BlindspotInterpretationRef[];
}

export interface EvidenceDrawerProps {
  open: boolean;
  payload?: EvidenceDrawerPayload;
  onClose: () => void;
}

interface EvidencePacket {
  schema_version?: string;
  trace_id?: string;
  input?: unknown;
  cas_expression?: unknown;
  output?: unknown;
  provenance?: unknown;
  hashes?: unknown;
  claim_levels?: unknown;
  copy_slot_trace?: unknown;
  caveats?: unknown;
}

type PacketState =
  | { status: 'idle'; packet?: undefined; error?: undefined }
  | { status: 'loading'; packet?: undefined; error?: undefined }
  | { status: 'loaded'; packet: EvidencePacket; error?: undefined }
  | { status: 'error'; packet?: undefined; error: string };

const backdropStyle: CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(2, 6, 23, 0.55)',
  zIndex: 40,
  backdropFilter: 'blur(4px)',
  WebkitBackdropFilter: 'blur(4px)',
};

const drawerWrapperStyle: CSSProperties = {
  position: 'fixed',
  top: 0,
  right: 0,
  bottom: 0,
  width: 420,
  maxWidth: '90vw',
  zIndex: 50,
  display: 'flex',
  flexDirection: 'column',
  fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif',
  fontSize: 13,
};

const drawerInnerStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  flex: 1,
  height: '100%',
  borderRadius: 0,
  borderLeft: '1px solid rgba(255,255,255,0.08)',
  boxShadow: '-12px 0 36px rgba(0,0,0,0.45)',
};

const headerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '12px 16px',
  borderBottom: '1px solid rgba(255,255,255,0.06)',
};

const titleStyle: CSSProperties = {
  fontWeight: 700,
  fontSize: 14,
  color: ATLAS_STATUS_COLORS.activeTrace,
};

const closeButtonStyle: CSSProperties = {
  background: 'rgba(255,255,255,0.04)',
  border: '1px solid rgba(255,255,255,0.1)',
  color: '#e5e7eb',
  borderRadius: 6,
  padding: '4px 12px',
  cursor: 'pointer',
  fontSize: 13,
};

const bodyStyle: CSSProperties = {
  flex: 1,
  overflowY: 'auto',
  padding: 16,
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
};

const noteStyle: CSSProperties = {
  padding: '8px 10px',
  borderRadius: 6,
  background: 'rgba(234, 179, 8, 0.12)',
  border: `1px solid ${ATLAS_STATUS_COLORS.caveat}`,
  color: ATLAS_STATUS_COLORS.caveat,
  fontSize: 12,
  lineHeight: 1.4,
};

const errorStyle: CSSProperties = {
  ...noteStyle,
  background: 'rgba(239, 68, 68, 0.12)',
  border: `1px solid ${ATLAS_STATUS_COLORS.suppress}`,
  color: '#fecaca',
};

const codeBlockStyle: CSSProperties = {
  margin: 0,
  padding: 12,
  background: 'rgba(2, 6, 23, 0.6)',
  border: '1px solid rgba(255,255,255,0.06)',
  borderRadius: 6,
  fontFamily: '"JetBrains Mono", Menlo, Consolas, monospace',
  fontSize: 12,
  color: '#cbd5e1',
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-all',
  overflowX: 'auto',
};

const sectionLabelStyle: CSSProperties = {
  fontWeight: 600,
  color: '#94a3b8',
  fontSize: 12,
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
};

const sourceTitleStyle: CSSProperties = {
  margin: 0,
  color: '#e2e8f0',
  fontSize: 13,
  fontWeight: 700,
};

const sourceNoteStyle: CSSProperties = {
  margin: 0,
  color: '#cbd5e1',
  fontSize: 12,
  lineHeight: 1.45,
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function extractTraceId(payload?: EvidenceDrawerPayload): string | null {
  const candidates = [payload?.evidence_ref, payload?.detail];
  for (const candidate of candidates) {
    if (isRecord(candidate) && typeof candidate.trace_id === 'string') {
      return candidate.trace_id;
    }
  }
  return null;
}

function stringify(value: unknown): string {
  if (value === undefined || value === null) return '(none)';
  return JSON.stringify(value, null, 2);
}

function packetText(packet: EvidencePacket, key: keyof EvidencePacket): string {
  return stringify(packet[key]);
}

function localSourceLabel(source?: EvidenceDrawerPayload['source']): string {
  if (source === 'neuron') return 'Neuron click reference';
  if (source === 'primitive') return 'Spatial primitive reference';
  return 'Local reference';
}

function localSourceNote(hasTraceId: boolean, failed: boolean): string {
  if (failed) {
    return 'Evidence Packet fetch failed; showing only the local reference metadata.';
  }
  if (hasTraceId) {
    return 'Evidence Packet requested; showing local reference metadata while packet data is unavailable.';
  }
  return 'Local replay metadata only; not presenting this as a verified Evidence Packet.';
}

function evidenceApiBaseUrl(): string {
  const atlasBaseUrl = resolveAtlasApiBaseUrl();
  if (atlasBaseUrl.endsWith('/api/atlas')) {
    return atlasBaseUrl.slice(0, -'/atlas'.length);
  }
  if (atlasBaseUrl.endsWith('/atlas')) {
    return atlasBaseUrl.slice(0, -'/atlas'.length);
  }
  return atlasBaseUrl;
}

function evidencePacketUrl(traceId: string): string {
  return `${evidenceApiBaseUrl()}/evidence/${encodeURIComponent(traceId)}`;
}

export default function EvidenceDrawer(props: EvidenceDrawerProps): JSX.Element {
  const { open, payload, onClose } = props;
  const closeBtnRef = useRef<HTMLButtonElement | null>(null);
  const traceId = useMemo(() => extractTraceId(payload), [payload]);
  const [packetState, setPacketState] = useState<PacketState>({ status: 'idle' });

  useEffect(() => {
    if (!open || !traceId) {
      setPacketState({ status: 'idle' });
      return;
    }

    const controller = new AbortController();
    setPacketState({ status: 'loading' });

    fetch(evidencePacketUrl(traceId), {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal: controller.signal,
    })
      .then(async (response) => {
        const body = await response.json().catch(() => null);
        if (!response.ok) {
          const detail = isRecord(body) && typeof body.detail === 'string'
            ? body.detail
            : `Evidence Packet request failed (${response.status})`;
          throw new Error(detail);
        }
        setPacketState({ status: 'loaded', packet: body as EvidencePacket });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        const message = error instanceof Error ? error.message : 'Evidence Packet request failed';
        setPacketState({ status: 'error', error: message });
      });

    return () => controller.abort();
  }, [open, traceId]);

  useEffect(() => {
    if (!open) return;
    const handler = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener('keydown', handler);
    closeBtnRef.current?.focus();
    return () => {
      window.removeEventListener('keydown', handler);
    };
  }, [open, onClose]);

  const refJson = payload?.evidence_ref
    ? JSON.stringify(payload.evidence_ref, null, 2)
    : '(no evidence_ref)';
  const detailJson = payload?.detail
    ? JSON.stringify(payload.detail, null, 2)
    : null;
  const packetFailed = packetState.status === 'error';
  const blindspots = payload?.blindspotInterpretations ?? [];
  const blindspotSection =
    blindspots.length > 0 ? (
      <div data-testid="evidence-drawer-blindspots" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={sectionLabelStyle}>blindspot interpretation</div>
        {blindspots.map((b, idx) => (
          <BlindspotInterpretation
            key={`${b.driveId}-${b.register ?? 'none'}-${idx}`}
            driveId={b.driveId}
            register={b.register}
            confidence={b.confidence}
            evidenceSources={b.evidenceSources}
          />
        ))}
      </div>
    ) : null;

  return (
    <>
      <AnimatePresence>
        {open ? (
          <motion.div
            key="backdrop"
            data-testid="evidence-drawer-backdrop"
            aria-hidden="true"
            style={backdropStyle}
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.4 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
          />
        ) : null}
      </AnimatePresence>
      <motion.aside
        role="dialog"
        aria-modal="true"
        aria-label="Evidence Packet"
        aria-hidden={open ? 'false' : 'true'}
        data-testid="evidence-drawer"
        data-open={open ? 'true' : 'false'}
        style={drawerWrapperStyle}
        initial={{ x: '100%' }}
        animate={{ x: open ? 0 : '100%' }}
        transition={SPRING_GENTLE}
      >
        <GlassPanel
          intensity="thick"
          as="div"
          padding={0}
          style={drawerInnerStyle}
        >
          <header style={headerStyle}>
            <span style={titleStyle}>
              Evidence Packet
              {payload?.title ? ` - ${payload.title}` : ''}
            </span>
            <button
              ref={closeBtnRef}
              type="button"
              data-testid="evidence-drawer-close"
              onClick={onClose}
              style={closeButtonStyle}
              aria-label="Close evidence packet"
            >
              Close
            </button>
          </header>
          <div style={bodyStyle}>
            {blindspotSection}
            {packetState.status === 'loaded' ? (
              <>
                <div style={noteStyle} data-testid="evidence-packet-loaded">
                  Loaded {packetState.packet.schema_version ?? 'Evidence Packet'}
                </div>
                <div style={sectionLabelStyle}>input</div>
                <pre style={codeBlockStyle} data-testid="evidence-packet-input">
                  {packetText(packetState.packet, 'input')}
                </pre>
                <div style={sectionLabelStyle}>cas_expression</div>
                <pre style={codeBlockStyle} data-testid="evidence-packet-cas">
                  {packetText(packetState.packet, 'cas_expression')}
                </pre>
                <div style={sectionLabelStyle}>output</div>
                <pre style={codeBlockStyle} data-testid="evidence-packet-output">
                  {packetText(packetState.packet, 'output')}
                </pre>
                <div style={sectionLabelStyle}>provenance</div>
                <pre style={codeBlockStyle} data-testid="evidence-packet-provenance">
                  {packetText(packetState.packet, 'provenance')}
                </pre>
                <div style={sectionLabelStyle}>hashes</div>
                <pre style={codeBlockStyle} data-testid="evidence-packet-hashes">
                  {packetText(packetState.packet, 'hashes')}
                </pre>
                <div style={sectionLabelStyle}>claim_levels</div>
                <pre style={codeBlockStyle} data-testid="evidence-packet-claim-levels">
                  {packetText(packetState.packet, 'claim_levels')}
                </pre>
              </>
            ) : (
              <>
                {packetState.status === 'loading' ? (
                  <div style={noteStyle} data-testid="evidence-drawer-loading">
                    Loading Evidence Packet for trace_id {traceId}.
                  </div>
                ) : null}
                {packetState.status === 'error' ? (
                  <div style={errorStyle} data-testid="evidence-drawer-error">
                    {packetState.error}
                  </div>
                ) : null}
                <div>
                  <p style={sourceTitleStyle} data-testid="evidence-drawer-source-label">
                    {localSourceLabel(payload?.source)}
                  </p>
                  <p style={sourceNoteStyle} data-testid="evidence-drawer-source-note">
                    {localSourceNote(Boolean(traceId), packetFailed)}
                  </p>
                </div>
                <div style={sectionLabelStyle}>evidence_ref</div>
                <pre style={codeBlockStyle} data-testid="evidence-drawer-ref-json">
                  {refJson}
                </pre>
                {detailJson ? (
                  <>
                    <div style={sectionLabelStyle}>detail</div>
                    <pre
                      style={codeBlockStyle}
                      data-testid="evidence-drawer-detail-json"
                    >
                      {detailJson}
                    </pre>
                  </>
                ) : null}
              </>
            )}
          </div>
        </GlassPanel>
      </motion.aside>
    </>
  );
}

void THEME;

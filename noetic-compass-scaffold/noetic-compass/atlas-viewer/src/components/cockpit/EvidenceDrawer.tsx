import { useEffect, useMemo, useRef, useState } from 'react';
import type { CSSProperties } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GlassPanel } from '../ui/GlassPanel';
import { THEME, SPRING_GENTLE } from '../../lib/designTokens';
import { ATLAS_STATUS_COLORS } from '../../lib/atlasPalette';
import { resolveAtlasApiBaseUrl } from '../../lib/atlasLiveApi';

export interface NeuronActivation {
  layer: number;
  index: number;
  activation: number;
}

export interface Mode7Edge {
  from_token_index: number | null;
  to_token_index: number;
  weight: number;
}

export interface WordSourceTokenDetail {
  token_index: number;
  token: string;
  top_activated_neurons: NeuronActivation[];
  mode7_attribution: Mode7Edge[];
  confidence: number | null;
  trace_id?: string;
}

export interface WordSourceDetail {
  tokens: WordSourceTokenDetail[];
}

export interface EvidenceDrawerPayload {
  source: 'neuron' | 'primitive' | 'word' | 'other';
  title: string;
  evidence_ref?: unknown;
  detail?: unknown;
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

function extractWordTokens(payload?: EvidenceDrawerPayload): WordSourceTokenDetail[] {
  if (payload?.source !== 'word') return [];
  if (!isRecord(payload.detail)) return [];
  const tokens = payload.detail.tokens;
  if (!Array.isArray(tokens)) return [];
  const out: WordSourceTokenDetail[] = [];
  for (const raw of tokens) {
    if (!isRecord(raw)) continue;
    if (typeof raw.token_index !== 'number' || typeof raw.token !== 'string') continue;
    const top = Array.isArray(raw.top_activated_neurons)
      ? (raw.top_activated_neurons as NeuronActivation[])
      : [];
    const mode7 = Array.isArray(raw.mode7_attribution)
      ? (raw.mode7_attribution as Mode7Edge[])
      : [];
    const confidence =
      typeof raw.confidence === 'number' ? raw.confidence : null;
    const traceId = typeof raw.trace_id === 'string' ? raw.trace_id : undefined;
    out.push({
      token_index: raw.token_index,
      token: raw.token,
      top_activated_neurons: top,
      mode7_attribution: mode7,
      confidence,
      trace_id: traceId,
    });
  }
  return out;
}

function extractTraceId(payload?: EvidenceDrawerPayload): string | null {
  // For word source, the first token carrying a trace_id wins. This is
  // captured separately from the per-token list so the drawer can show
  // both the packet (one fetch) AND the per-token table.
  if (payload?.source === 'word') {
    for (const token of extractWordTokens(payload)) {
      if (token.trace_id) return token.trace_id;
    }
    // No fallthrough — word source uses only token-level trace_ids.
    return null;
  }
  const candidates = [payload?.evidence_ref, payload?.detail];
  for (const candidate of candidates) {
    if (isRecord(candidate) && typeof candidate.trace_id === 'string') {
      return candidate.trace_id;
    }
  }
  return null;
}

function dedupeMode7Edges(tokens: WordSourceTokenDetail[]): Mode7Edge[] {
  const seen = new Set<string>();
  const out: Mode7Edge[] = [];
  for (const token of tokens) {
    for (const edge of token.mode7_attribution) {
      const fromKey = edge.from_token_index === null ? 'null' : String(edge.from_token_index);
      const key = `${fromKey}->${edge.to_token_index}`;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push(edge);
    }
  }
  return out;
}

function escapeForDisplay(text: string): string {
  // Visually surface whitespace/control chars so the user sees what the
  // tokenizer produced (leading space, newlines, tabs).
  return text
    .replace(/\\/g, '\\\\')
    .replace(/\n/g, '\\n')
    .replace(/\t/g, '\\t')
    .replace(/\r/g, '\\r')
    .replace(/ /g, '␣'); // open-box for visible space
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
  if (source === 'word') return 'Word click reference';
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
  const wordTokens = useMemo(() => extractWordTokens(payload), [payload]);
  const wordTraceIds = useMemo(() => {
    const seen = new Set<string>();
    const out: string[] = [];
    for (const t of wordTokens) {
      if (t.trace_id && !seen.has(t.trace_id)) {
        seen.add(t.trace_id);
        out.push(t.trace_id);
      }
    }
    return out;
  }, [wordTokens]);
  const dedupedMode7 = useMemo(() => dedupeMode7Edges(wordTokens), [wordTokens]);
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
            {payload?.source === 'word' && wordTokens.length > 0 ? (
              <div data-testid="evidence-drawer-word-section" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div style={sectionLabelStyle}>Tokens behind this word</div>
                <table
                  data-testid="evidence-drawer-word-tokens"
                  style={{
                    width: '100%',
                    borderCollapse: 'collapse',
                    fontSize: 12,
                    color: '#cbd5e1',
                  }}
                >
                  <thead>
                    <tr style={{ textAlign: 'left', color: '#94a3b8' }}>
                      <th style={{ padding: '4px 6px' }}>idx</th>
                      <th style={{ padding: '4px 6px' }}>token</th>
                      <th style={{ padding: '4px 6px' }}>conf</th>
                      <th style={{ padding: '4px 6px' }}>top neurons</th>
                    </tr>
                  </thead>
                  <tbody>
                    {wordTokens.map((tok) => (
                      <tr
                        key={tok.token_index}
                        data-testid={`evidence-drawer-word-token-row-${tok.token_index}`}
                        style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}
                      >
                        <td style={{ padding: '4px 6px', fontFamily: '"JetBrains Mono", monospace' }}>{tok.token_index}</td>
                        <td style={{ padding: '4px 6px', fontFamily: '"JetBrains Mono", monospace' }}>
                          "{escapeForDisplay(tok.token)}"
                        </td>
                        <td style={{ padding: '4px 6px', fontFamily: '"JetBrains Mono", monospace' }}>
                          {tok.confidence === null ? '—' : tok.confidence.toFixed(2)}
                        </td>
                        <td style={{ padding: '4px 6px', fontFamily: '"JetBrains Mono", monospace' }}>
                          {tok.top_activated_neurons.length === 0
                            ? '—'
                            : tok.top_activated_neurons
                                .slice(0, 3)
                                .map((n) => `L${n.layer}N${n.index}`)
                                .join(', ')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                <div style={sectionLabelStyle}>Attention path</div>
                {dedupedMode7.length === 0 ? (
                  <div style={{ color: '#94a3b8', fontSize: 12 }} data-testid="evidence-drawer-word-mode7-empty">
                    No Mode 7 edges recorded for these tokens.
                  </div>
                ) : (
                  <ul
                    data-testid="evidence-drawer-word-mode7"
                    style={{
                      margin: 0,
                      paddingLeft: 18,
                      fontSize: 12,
                      fontFamily: '"JetBrains Mono", monospace',
                      color: '#cbd5e1',
                    }}
                  >
                    {dedupedMode7.map((edge) => {
                      const fromLabel =
                        edge.from_token_index === null
                          ? 'prompt'
                          : `token ${edge.from_token_index}`;
                      const key = `${edge.from_token_index ?? 'null'}->${edge.to_token_index}`;
                      return (
                        <li
                          key={key}
                          data-testid={`evidence-drawer-word-mode7-edge-${key}`}
                        >
                          {fromLabel} → token {edge.to_token_index}
                          <span style={{ color: '#94a3b8' }}>
                            {' '}(weight {edge.weight.toFixed(2)})
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                )}

                {wordTraceIds.length > 0 ? (
                  <div data-testid="evidence-drawer-word-trace-ids" style={{ fontSize: 12, color: '#94a3b8' }}>
                    {wordTraceIds.length === 1
                      ? `Evidence Packet trace_id: ${wordTraceIds[0]}`
                      : `Evidence Packet trace_ids: ${wordTraceIds.join(', ')}`}
                  </div>
                ) : null}

                <div style={sectionLabelStyle}>Evidence Packet</div>
              </div>
            ) : null}
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

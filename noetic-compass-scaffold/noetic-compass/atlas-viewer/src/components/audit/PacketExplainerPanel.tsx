import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type CSSProperties,
} from 'react';
import { AnimatePresence, motion } from 'framer-motion';

import {
  askExplainerForPacket,
  type ExplainPacketResponse,
  type ExplainPacketSegment,
} from '../../lib/explainerApi';
import {
  onPacketExplanationRequested,
  type PacketExplainerOpenDetail,
} from '../../lib/packetExplainerBus';
import {
  EP_FIELD_FLASH_CSS,
  scrollToEpField,
} from '../../lib/packetExplainerLinks';
import {
  ACCENT_CYAN,
  ACCENT_TEAL,
  COLORS,
  FONT_FAMILY,
  FONT_MONO,
} from '../../lib/designTokens';
import { TreeOfLifeMark } from '../brand/TreeOfLifeMark';

// Sits in the same z-band as the Guide widget (1200) so neither float fights a
// briefing popover. The packet panel anchors to the LEFT edge so it never
// overlaps the bottom-right Guide launcher/panel when both happen to be open.
const PANEL_Z = 1200;
const MODAL_Z = 1300;

const PANEL_TRANSITION = { duration: 0.12, ease: 'easeOut' } as const;

// localStorage key for the G4 first-use acknowledgement. Persisted per browser
// profile (the spec says "stored per account"; this is the client-side half —
// the account binding lives with the session token, not this flag).
const ACK_STORAGE_KEY = 'casPacketExplainerDisclaimerAck';

// The single G4 disclaimer line, always visible in the footer. Exported so the
// test (and any other surface) asserts against the exact wording.
export const PACKET_EXPLAINER_DISCLAIMER =
  'This is an AI-generated reading aid. The original Evidence Packet is the authoritative record — you are responsible for reading it yourself.';

// The fuller first-use modal body (spec §2 G4) — adds the go/no-go caution.
const PACKET_EXPLAINER_DISCLAIMER_FULL =
  'This is an AI-generated reading aid. The original Evidence Packet is the authoritative record — you are responsible for reading it yourself. Do not rely on this summary alone for any go/no-go decision.';

// Fail-closed line when the AI's echoed verdict does not match the packet.
const VERDICT_MISMATCH_LINE = 'AI summary unavailable for this packet.';

type LoadState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'loaded'; response: ExplainPacketResponse }
  | { status: 'mismatch' }
  | { status: 'error'; detail: string };

function hasAck(): boolean {
  try {
    return window.localStorage.getItem(ACK_STORAGE_KEY) === 'true';
  } catch {
    return false;
  }
}

function persistAck(): void {
  try {
    window.localStorage.setItem(ACK_STORAGE_KEY, 'true');
  } catch {
    // Storage may be unavailable (private mode); ack stays session-local.
  }
}

const panelStyle: CSSProperties = {
  position: 'fixed',
  left: 20,
  bottom: 20,
  zIndex: PANEL_Z,
  width: 'min(420px, calc(100vw - 32px))',
  maxHeight: '74vh',
  display: 'flex',
  flexDirection: 'column',
  overflow: 'hidden',
  borderRadius: 16,
  border: '1px solid rgba(255, 255, 255, 0.22)',
  background:
    'linear-gradient(160deg, rgba(15, 23, 42, 0.88), rgba(8, 13, 27, 0.74))',
  boxShadow:
    '0 24px 80px rgba(0, 0, 0, 0.48), inset 0 1px 0 rgba(255, 255, 255, 0.14), 0 0 0 1px rgba(45, 212, 191, 0.12)',
  backdropFilter: 'blur(24px) saturate(1.35)',
  WebkitBackdropFilter: 'blur(24px) saturate(1.35)',
  color: COLORS.textPrimary,
  fontFamily: FONT_FAMILY,
};

const headerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'flex-start',
  gap: 10,
  padding: '12px 12px 10px 14px',
  borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
};

const headerEyebrowStyle: CSSProperties = {
  display: 'block',
  marginBottom: 3,
  color: ACCENT_CYAN,
  fontSize: 9,
  fontWeight: 900,
  letterSpacing: 0.9,
  textTransform: 'uppercase',
};

const headerTitleStyle: CSSProperties = {
  margin: 0,
  fontSize: 13,
  fontWeight: 850,
  letterSpacing: 0.2,
  color: COLORS.textPrimary,
};

const headerSublineStyle: CSSProperties = {
  margin: '3px 0 0',
  fontSize: 10.5,
  lineHeight: 1.35,
  fontWeight: 600,
  color: COLORS.textSecondary,
  fontFamily: FONT_MONO,
  overflowWrap: 'anywhere',
};

const closeButtonStyle: CSSProperties = {
  flex: '0 0 auto',
  width: 26,
  height: 26,
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  borderRadius: 8,
  border: '1px solid rgba(255, 255, 255, 0.12)',
  background: 'rgba(255, 255, 255, 0.04)',
  color: COLORS.textSecondary,
  cursor: 'pointer',
  fontSize: 14,
  lineHeight: 1,
  fontFamily: FONT_FAMILY,
  padding: 0,
};

const bodyStyle: CSSProperties = {
  flex: '1 1 auto',
  overflowY: 'auto',
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
  padding: '12px 14px',
};

const verdictEchoStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  margin: 0,
  padding: '8px 10px',
  borderRadius: 8,
  border: '1px solid rgba(45, 212, 191, 0.30)',
  background: 'rgba(45, 212, 191, 0.07)',
  color: COLORS.textPrimary,
  fontSize: 12.5,
  fontWeight: 700,
};

const verdictEchoWordStyle: CSSProperties = {
  fontFamily: FONT_MONO,
  fontWeight: 900,
  color: '#ccfbf1',
};

const sectionLabelStyle: CSSProperties = {
  margin: '4px 0 0',
  color: ACCENT_TEAL,
  fontSize: 10,
  fontWeight: 900,
  letterSpacing: 0.7,
  textTransform: 'uppercase',
};

const segmentStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 7,
  padding: '9px 11px',
  borderRadius: 10,
  border: '1px solid rgba(255, 255, 255, 0.10)',
  background: 'rgba(255, 255, 255, 0.04)',
};

const segmentTextStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textPrimary,
  fontSize: 13,
  lineHeight: 1.45,
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
};

const refRowStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 6,
};

const refChipStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 4,
  borderRadius: 999,
  border: '1px solid rgba(45, 212, 191, 0.34)',
  background: 'rgba(45, 212, 191, 0.10)',
  color: '#ccfbf1',
  fontFamily: FONT_MONO,
  fontSize: 9.5,
  fontWeight: 700,
  letterSpacing: 0.2,
  padding: '2px 8px',
  cursor: 'pointer',
  wordBreak: 'break-all',
};

const statusBubbleStyle: CSSProperties = {
  ...segmentStyle,
  color: COLORS.textSecondary,
};

const errorBubbleStyle: CSSProperties = {
  ...segmentStyle,
  border: '1px solid rgba(251, 113, 133, 0.42)',
  background: 'rgba(251, 113, 133, 0.10)',
  color: '#ffe4e6',
};

const footerStyle: CSSProperties = {
  flex: '0 0 auto',
  padding: '9px 14px 12px',
  borderTop: '1px solid rgba(255, 255, 255, 0.08)',
};

const footerDisclaimerStyle: CSSProperties = {
  margin: 0,
  fontSize: 10,
  lineHeight: 1.4,
  fontWeight: 600,
  color: COLORS.textMuted,
};

// --- First-use disclaimer modal ------------------------------------------
const modalScrimStyle: CSSProperties = {
  position: 'fixed',
  inset: 0,
  zIndex: MODAL_Z,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: 20,
  background: 'rgba(2, 6, 23, 0.62)',
  backdropFilter: 'blur(3px)',
  WebkitBackdropFilter: 'blur(3px)',
};

const modalCardStyle: CSSProperties = {
  width: 'min(440px, calc(100vw - 40px))',
  display: 'flex',
  flexDirection: 'column',
  gap: 14,
  padding: 20,
  borderRadius: 14,
  border: '1px solid rgba(45, 212, 191, 0.30)',
  background:
    'linear-gradient(160deg, rgba(15, 23, 42, 0.96), rgba(8, 13, 27, 0.92))',
  boxShadow: '0 30px 90px rgba(0, 0, 0, 0.55)',
  color: COLORS.textPrimary,
  fontFamily: FONT_FAMILY,
};

const modalTitleStyle: CSSProperties = {
  margin: 0,
  fontSize: 15,
  fontWeight: 850,
  color: COLORS.textPrimary,
};

const modalBodyStyle: CSSProperties = {
  margin: 0,
  fontSize: 13,
  lineHeight: 1.5,
  color: COLORS.textSecondary,
};

const modalActionsRowStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'flex-end',
  gap: 8,
};

const modalSecondaryButtonStyle: CSSProperties = {
  minHeight: 36,
  padding: '0 14px',
  borderRadius: 9,
  border: '1px solid rgba(255, 255, 255, 0.14)',
  background: 'rgba(255, 255, 255, 0.04)',
  color: COLORS.textSecondary,
  cursor: 'pointer',
  fontFamily: FONT_FAMILY,
  fontSize: 12.5,
  fontWeight: 700,
};

const modalPrimaryButtonStyle: CSSProperties = {
  minHeight: 36,
  padding: '0 16px',
  borderRadius: 9,
  border: '1px solid rgba(45, 212, 191, 0.45)',
  background: 'rgba(45, 212, 191, 0.14)',
  color: '#ccfbf1',
  cursor: 'pointer',
  fontFamily: FONT_FAMILY,
  fontSize: 12.5,
  fontWeight: 800,
};

/** A cited explanation segment. Returns null when the segment has no refs. */
function SegmentBubble({
  segment,
  testid,
}: {
  segment: ExplainPacketSegment;
  testid: string;
}): JSX.Element | null {
  // Spec §6 rendering rule: a segment with zero refs is an uncited claim and is
  // NOT shown. Filter to non-empty string refs so a stray "" never renders a
  // chip either.
  const refs = (segment.refs ?? []).filter(
    (ref) => typeof ref === 'string' && ref.trim().length > 0,
  );
  if (refs.length === 0) return null;

  return (
    <div style={segmentStyle} data-testid={testid}>
      <p style={segmentTextStyle}>{segment.text}</p>
      <div style={refRowStyle}>
        {refs.map((ref) => (
          <button
            key={ref}
            type="button"
            style={refChipStyle}
            onClick={() => scrollToEpField(ref)}
            data-testid="packet-explainer-ref-chip"
            data-ref={ref}
            title={`Jump to ${ref} in the Evidence Packet`}
            aria-label={`Jump to ${ref} in the Evidence Packet`}
          >
            <span aria-hidden="true">↳</span>
            {ref}
          </button>
        ))}
      </div>
    </div>
  );
}

/**
 * Floating "Explain this packet" panel — the AI reading-aid surface for one
 * Evidence Packet (spec §6/§7/§9). It opens when the EP view's "Explain this
 * packet" button fires the open-request (packetExplainerBus), fetches a cited
 * interpretation, and renders `segments` + `investigate_next` with clickable
 * ref-chips that scroll to the matching EP field.
 *
 * Honesty rules enforced here:
 *  - On first use, a G4 acknowledgement modal blocks the panel until accepted;
 *    the ack persists in localStorage and the footer disclaimer is ALWAYS shown.
 *  - The UI asserts `response.verdict_echo === EP.verdict`. On mismatch it
 *    discards the AI output and shows only the raw EP verdict + "AI summary
 *    unavailable for this packet" (fail-closed — never the inflated reading).
 *  - A segment with zero refs is never rendered (no uncited claims).
 *
 * Mount ONCE at the console shell level alongside the Guide widget.
 */
export function PacketExplainerPanel({ authToken }: { authToken?: string | null }): JSX.Element {
  const [open, setOpen] = useState(false);
  const [context, setContext] = useState<PacketExplainerOpenDetail | null>(null);
  const [load, setLoad] = useState<LoadState>({ status: 'idle' });
  const [needsAck, setNeedsAck] = useState(false);
  // The open-request that arrived while the first-use modal is up, deferred
  // until the user acknowledges.
  const pendingRef = useRef<PacketExplainerOpenDetail | null>(null);

  const panelId = useId();
  const bodyRef = useRef<HTMLDivElement | null>(null);

  const close = useCallback(() => {
    setOpen(false);
    setNeedsAck(false);
    pendingRef.current = null;
  }, []);

  const beginLoad = useCallback(async (detail: PacketExplainerOpenDetail) => {
    setContext(detail);
    setOpen(true);
    setLoad({ status: 'loading' });
    try {
      const response = authToken
        ? await askExplainerForPacket(detail.traceId, { authToken })
        : await askExplainerForPacket(detail.traceId);
      // §7 verdict-echo guard: the AI's echoed verdict MUST equal the packet's
      // own verdict. Any drift → discard and fail closed.
      if (response.verdict_echo !== detail.epVerdict) {
        setLoad({ status: 'mismatch' });
        return;
      }
      setLoad({ status: 'loaded', response });
    } catch (err) {
      setLoad({
        status: 'error',
        detail: err instanceof Error ? err.message : String(err),
      });
    }
  }, [authToken]);

  // Listen for open-requests from any EP view's "Explain this packet" button.
  useEffect(() => {
    return onPacketExplanationRequested((detail) => {
      if (!hasAck()) {
        // Gate behind the first-use disclaimer; remember the request.
        pendingRef.current = detail;
        setContext(detail);
        setNeedsAck(true);
        setOpen(false);
        return;
      }
      void beginLoad(detail);
    });
  }, [beginLoad]);

  // Close on Escape while the panel (not the modal) is open.
  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event: globalThis.KeyboardEvent): void => {
      if (event.key === 'Escape') {
        event.stopPropagation();
        close();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, close]);

  // Keep the newest content in view when the panel updates.
  useEffect(() => {
    if (!open) return;
    const body = bodyRef.current;
    if (body) body.scrollTop = 0;
  }, [open, load]);

  const acceptAck = useCallback(() => {
    persistAck();
    setNeedsAck(false);
    const pending = pendingRef.current;
    pendingRef.current = null;
    if (pending) void beginLoad(pending);
  }, [beginLoad]);

  const cancelAck = useCallback(() => {
    setNeedsAck(false);
    pendingRef.current = null;
    setContext(null);
  }, []);

  const verdictEcho =
    load.status === 'loaded' ? load.response.verdict_echo : context?.epVerdict ?? '';

  return (
    <>
      {/* Field-flash keyframes for ref-chip targets, injected once. */}
      <style>{EP_FIELD_FLASH_CSS}</style>

      {/* First-use G4 acknowledgement modal. */}
      <AnimatePresence>
        {needsAck ? (
          <motion.div
            key="packet-explainer-ack"
            role="dialog"
            aria-modal="true"
            aria-label="AI reading-aid acknowledgement"
            style={modalScrimStyle}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={PANEL_TRANSITION}
            data-testid="packet-explainer-disclaimer-modal"
          >
            <motion.div
              style={modalCardStyle}
              initial={{ opacity: 0, y: 10, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.98 }}
              transition={PANEL_TRANSITION}
            >
              <h2 style={modalTitleStyle}>Before you use the AI reading aid</h2>
              <p style={modalBodyStyle}>{PACKET_EXPLAINER_DISCLAIMER_FULL}</p>
              <div style={modalActionsRowStyle}>
                <button
                  type="button"
                  style={modalSecondaryButtonStyle}
                  onClick={cancelAck}
                  data-testid="packet-explainer-disclaimer-cancel"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  style={modalPrimaryButtonStyle}
                  onClick={acceptAck}
                  data-testid="packet-explainer-disclaimer-accept"
                >
                  I understand — show the summary
                </button>
              </div>
            </motion.div>
          </motion.div>
        ) : null}
      </AnimatePresence>

      {/* The explanation panel. */}
      <AnimatePresence>
        {open ? (
          <motion.section
            key="packet-explainer-panel"
            id={panelId}
            role="dialog"
            aria-label="Explain this packet"
            style={panelStyle}
            initial={{ opacity: 0, y: 12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.98 }}
            transition={PANEL_TRANSITION}
            data-testid="packet-explainer-panel"
          >
            <header style={headerStyle}>
              <TreeOfLifeMark size={24} animated={false} title="CAS Harness" />
              <div style={{ flex: '1 1 auto', minWidth: 0 }}>
                <span style={headerEyebrowStyle}>Reading aid</span>
                <p style={headerTitleStyle}>Explain this packet</p>
                {context?.traceId ? (
                  <p style={headerSublineStyle}>trace_id: {context.traceId}</p>
                ) : null}
              </div>
              <button
                type="button"
                aria-label="Close packet explanation"
                onClick={close}
                style={closeButtonStyle}
                data-testid="packet-explainer-close"
              >
                ✕
              </button>
            </header>

            <div
              ref={bodyRef}
              style={bodyStyle}
              role="region"
              aria-live="polite"
              aria-label="Packet explanation"
              data-testid="packet-explainer-body"
            >
              {load.status === 'loading' ? (
                <div style={statusBubbleStyle} data-testid="packet-explainer-loading">
                  Reading the packet…
                </div>
              ) : null}

              {load.status === 'error' ? (
                <div style={errorBubbleStyle} data-testid="packet-explainer-error">
                  The packet reading aid is unavailable right now — the original
                  Evidence Packet is still the authoritative record.
                  {'\n'}
                  {load.detail}
                </div>
              ) : null}

              {load.status === 'mismatch' ? (
                <div
                  style={errorBubbleStyle}
                  data-testid="packet-explainer-mismatch"
                >
                  <p style={{ ...segmentTextStyle, color: 'inherit' }}>
                    Packet verdict:{' '}
                    <span style={verdictEchoWordStyle}>{verdictEcho || 'unknown'}</span>
                  </p>
                  <p style={{ ...segmentTextStyle, color: 'inherit', marginTop: 4 }}>
                    {VERDICT_MISMATCH_LINE}
                  </p>
                </div>
              ) : null}

              {load.status === 'loaded' ? (
                <>
                  <p
                    style={verdictEchoStyle}
                    data-testid="packet-explainer-verdict-echo"
                  >
                    Packet verdict:{' '}
                    <span style={verdictEchoWordStyle}>
                      {load.response.verdict_echo}
                    </span>
                  </p>

                  {load.response.segments.map((segment, index) => (
                    <SegmentBubble
                      key={`seg-${index}`}
                      segment={segment}
                      testid="packet-explainer-segment"
                    />
                  ))}

                  {load.response.investigate_next.length > 0 ? (
                    <p style={sectionLabelStyle}>What &amp; why to investigate next</p>
                  ) : null}
                  {load.response.investigate_next.map((segment, index) => (
                    <SegmentBubble
                      key={`next-${index}`}
                      segment={segment}
                      testid="packet-explainer-investigate"
                    />
                  ))}
                </>
              ) : null}
            </div>

            <footer style={footerStyle}>
              <p
                style={footerDisclaimerStyle}
                data-testid="packet-explainer-footer-disclaimer"
              >
                {PACKET_EXPLAINER_DISCLAIMER}
              </p>
            </footer>
          </motion.section>
        ) : null}
      </AnimatePresence>
    </>
  );
}

export default PacketExplainerPanel;

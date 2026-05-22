import { useEffect, useRef } from 'react';
import type { CSSProperties } from 'react';
import { ATLAS_STATUS_COLORS } from '../../lib/atlasPalette';

export interface EvidenceDrawerPayload {
  source: 'neuron' | 'primitive' | 'other';
  title: string;
  evidence_ref?: unknown;
  detail?: unknown;
}

export interface EvidenceDrawerProps {
  open: boolean;
  payload?: EvidenceDrawerPayload;
  onClose: () => void;
}

const backdropStyle: CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(2, 6, 23, 0.45)',
  zIndex: 40,
};

const panelStyle = (open: boolean): CSSProperties => ({
  position: 'fixed',
  top: 0,
  right: 0,
  bottom: 0,
  width: 420,
  maxWidth: '90vw',
  background: '#0b1220',
  color: '#e5e7eb',
  borderLeft: '1px solid #1f2937',
  boxShadow: '-8px 0 24px rgba(0,0,0,0.4)',
  transform: open ? 'translateX(0)' : 'translateX(100%)',
  transition: 'transform 200ms ease',
  zIndex: 50,
  display: 'flex',
  flexDirection: 'column',
  fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif',
  fontSize: 13,
});

const headerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '12px 16px',
  borderBottom: '1px solid #1f2937',
  background: '#111827',
};

const titleStyle: CSSProperties = {
  fontWeight: 700,
  fontSize: 14,
  color: ATLAS_STATUS_COLORS.activeTrace,
};

const closeButtonStyle: CSSProperties = {
  background: 'transparent',
  border: '1px solid #374151',
  color: '#e5e7eb',
  borderRadius: 4,
  padding: '4px 10px',
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
  borderRadius: 4,
  background: 'rgba(234, 179, 8, 0.12)',
  border: `1px solid ${ATLAS_STATUS_COLORS.caveat}`,
  color: ATLAS_STATUS_COLORS.caveat,
  fontSize: 12,
  lineHeight: 1.4,
};

const codeBlockStyle: CSSProperties = {
  margin: 0,
  padding: 12,
  background: '#020617',
  border: '1px solid #1f2937',
  borderRadius: 4,
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

export default function EvidenceDrawer(props: EvidenceDrawerProps): JSX.Element {
  const { open, payload, onClose } = props;
  const closeBtnRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
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

  return (
    <>
      {open ? (
        <div
          data-testid="evidence-drawer-backdrop"
          aria-hidden="true"
          style={backdropStyle}
          onClick={onClose}
        />
      ) : null}
      <aside
        role="dialog"
        aria-modal="true"
        aria-label="Evidence Packet"
        aria-hidden={open ? 'false' : 'true'}
        data-testid="evidence-drawer"
        data-open={open ? 'true' : 'false'}
        style={panelStyle(open)}
      >
        <header style={headerStyle}>
          <span style={titleStyle}>
            Evidence Packet
            {payload?.title ? ` — ${payload.title}` : ''}
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
          <div style={noteStyle} data-testid="evidence-drawer-pending-note">
            v0.0: dashboard wrap pending. Below is the fixture-backed
            evidence_ref payload only — full Evidence Packet rendering lands in
            a follow-on round.
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
        </div>
      </aside>
    </>
  );
}

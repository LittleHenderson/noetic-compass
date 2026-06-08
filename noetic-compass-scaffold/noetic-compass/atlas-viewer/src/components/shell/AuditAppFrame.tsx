import type { CSSProperties, ReactNode } from 'react';
import { COLORS } from '../../lib/designTokens';
import { GuideChatWidget } from '../audit/GuideChatWidget';
import { PacketExplainerPanel } from '../audit/PacketExplainerPanel';

export interface AuditAppFrameProps {
  /** Left navigation rail (AuditRail). */
  rail: ReactNode;
  /** Center workspace — run header, composer, stage ladder, transcript. */
  center: ReactNode;
  /** Right evidence rail (EvidenceRail) — the decision surface. */
  evidence: ReactNode;
  /**
   * Verdict + scope, duplicated to pin directly under the stage ladder on
   * narrow screens (the right rail drops below the transcript there). Hidden on
   * desktop where the full evidence rail carries it. Optional.
   */
  pinned?: ReactNode;
}

// Breakpoint matches plan §1: below 1100px the rails collapse and the right
// rail drops below the center, with verdict + scope pinned under the ladder.
const FRAME_CSS = `
.audit-frame {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr) 360px;
  gap: 16px;
  width: 100%;
  max-width: 1480px;
  margin: 0 auto;
  align-items: start;
}

.audit-frame__rail {
  position: sticky;
  top: 16px;
  max-height: calc(100vh - 32px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(14px) saturate(120%);
  -webkit-backdrop-filter: blur(14px) saturate(120%);
  overflow: hidden;
}

.audit-frame__center {
  min-width: 0;
  display: grid;
  gap: 16px;
}

.audit-frame__evidence {
  position: sticky;
  top: 16px;
  max-height: calc(100vh - 32px);
  overflow-y: auto;
}

/* The mobile-pinned verdict+scope slot is hidden on desktop. */
.audit-frame__pinned {
  display: none;
}

@media (max-width: 1100px) {
  .audit-frame {
    grid-template-columns: minmax(0, 1fr);
  }

  .audit-frame__rail {
    position: static;
    max-height: none;
  }

  .audit-frame__evidence {
    position: static;
    max-height: none;
  }

  /* Show the pinned verdict+scope under the ladder so the result is never
     below the fold on mobile. */
  .audit-frame__pinned {
    display: block;
  }
}
`;

const backdropStyle: CSSProperties = {
  position: 'relative',
  minHeight: '100vh',
  background:
    'radial-gradient(ellipse at 50% 110%, rgba(15, 23, 42, 0.9) 0%, #020617 60%, #000000 100%)',
  overflowX: 'hidden',
  overflowY: 'auto',
  color: COLORS.textPrimary,
};

// A faint grid graticule behind everything — reuses the PageShell HUD
// foundation via inline SVG data URI (no extra HTTP request).
const gridOverlayStyle: CSSProperties = {
  position: 'absolute',
  inset: 0,
  pointerEvents: 'none',
  opacity: 0.35,
  backgroundImage:
    "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='40' height='40' viewBox='0 0 40 40'><path d='M40 0H0V40' fill='none' stroke='rgba(148,163,184,0.06)' stroke-width='1'/></svg>\")",
  backgroundSize: '40px 40px',
};

const contentStyle: CSSProperties = {
  position: 'relative',
  zIndex: 1,
  padding: '16px 16px 48px',
};

/**
 * 3-zone CSS-grid app frame for the Audit Bench: ~240px left rail / fluid center
 * / ~360px sticky right evidence rail. Below 1100px it collapses to a single
 * column with the right rail dropping under the center; the optional `pinned`
 * slot keeps verdict + scope directly under the stage ladder on mobile. Reuses
 * the PageShell backdrop + grid graticule; dark mode only.
 */
export function AuditAppFrame({
  rail,
  center,
  evidence,
  pinned,
}: AuditAppFrameProps): JSX.Element {
  return (
    <div style={backdropStyle}>
      <style>{FRAME_CSS}</style>
      <div style={gridOverlayStyle} aria-hidden="true" />
      <div style={contentStyle}>
        <div className="audit-frame">
          <aside className="audit-frame__rail">{rail}</aside>
          <main className="audit-frame__center">
            {center}
            {pinned ? <div className="audit-frame__pinned">{pinned}</div> : null}
          </main>
          <div className="audit-frame__evidence">{evidence}</div>
        </div>
      </div>
      {/* Floating CAS Harness Guide — mounted once at the console shell level so it
          persists across every console tab/section and floats over the whole console
          (it is position:fixed, so it never affects the grid layout). */}
      <GuideChatWidget />
      {/* Floating "Explain this packet" reading aid — also mounted once here so it
          floats over the console (left edge, clear of the Guide). Opens when an
          Evidence Packet view's "Explain this packet" button fires its request. */}
      <PacketExplainerPanel />
    </div>
  );
}

export default AuditAppFrame;

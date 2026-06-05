import { useEffect, useRef, type CSSProperties } from 'react';
import { AuditVerdictExplainer } from './AuditVerdictExplainer';
import EvidencePacketFlightRecorderFaq from './EvidencePacketFlightRecorderFaq';
import {
  COLORS,
  FONT_FAMILY,
  FONT_MONO,
  TONE_TINT,
} from '../../lib/designTokens';
import type {
  AuditVerdict,
  ProvenanceChip,
  VerifierDecision,
} from '../../lib/casHarnessAudit';

export interface MethodologyDrawerProps {
  open: boolean;
  onClose: () => void;
  verdict?: AuditVerdict | null;
  confidence?: number | null;
  chips: ProvenanceChip[];
  verifierDecision?: VerifierDecision | null;
  lifecycleMessage?: string | null;
}

// The honesty legend: maps each customer-facing relabel (used on the console
// surface) to the model-internal thing it names. This is where the methodology
// vocabulary is allowed to appear — never on the default console surface.
const RELABEL_LEGEND: ReadonlyArray<{ plain: string; meaning: string }> = [
  {
    plain: 'CAS readout (model-internal signal)',
    meaning:
      'cas_readout — the CAS register/drive readout taken from inside the model that the verdict is judging.',
  },
  {
    plain: 'Causal check (ablation)',
    meaning:
      'causal_proof — an ablation/intervention showing the CAS direction actually changes the behavior.',
  },
  {
    plain: 'Matched control',
    meaning:
      'control_proof — matched controls/baselines that did NOT explain the same effect.',
  },
  {
    plain: 'Output match',
    meaning: 'output_proof — the verdict is tied to observed model output.',
  },
  {
    plain: 'Evidence packet',
    meaning:
      'packet_proof — the audit trail attached to an Evidence Packet. Final ACCEPT/SUPPRESS requires S3 re-read plus active Object Lock/WORM retention.',
  },
  {
    plain: 'Live trace',
    meaning:
      'the live-worker probe. Teal ONLY when confirmed real model weights are loaded; otherwise amber/muted — never a real-audit claim.',
  },
];

// Internal scoring vocabulary, surfaced here (and only here) so reviewers can map
// confidence sources back to the pipeline stages.
const STAGE_LEGEND: ReadonlyArray<{ term: string; meaning: string }> = [
  {
    term: 'Stage 19 / accepted_accuracy',
    meaning:
      'When a verdict is ACCEPT, confidence is sourced from Stage 19 accepted_accuracy in the Verification Stack mode profile.',
  },
  {
    term: 'Stage 20 / Generation Readiness',
    meaning:
      'When a verdict is SUPPRESS, confidence is sourced from the Stage 20 risk_score in Generation Readiness.',
  },
  {
    term: 'Stage 21 verifier decision',
    meaning:
      'An explicit verifier decision routes a row to human review rather than automatic trust.',
  },
];

const backdropStyle: CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(2, 6, 23, 0.55)',
  zIndex: 60,
  backdropFilter: 'blur(4px)',
  WebkitBackdropFilter: 'blur(4px)',
};

const drawerStyle: CSSProperties = {
  position: 'fixed',
  top: 0,
  right: 0,
  bottom: 0,
  width: 460,
  maxWidth: '92vw',
  zIndex: 70,
  display: 'flex',
  flexDirection: 'column',
  borderLeft: `1px solid ${COLORS.borderStrong}`,
  background:
    'linear-gradient(180deg, rgba(15, 23, 42, 0.96), rgba(2, 6, 23, 0.98))',
  boxShadow: '-12px 0 36px rgba(0, 0, 0, 0.5)',
  fontFamily: FONT_FAMILY,
};

const headerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 10,
  padding: '14px 16px',
  borderBottom: `1px solid ${COLORS.borderSubtle}`,
};

const titleStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textPrimary,
  fontSize: 15,
  fontWeight: 850,
};

const closeButtonStyle: CSSProperties = {
  minHeight: 30,
  padding: '5px 12px',
  borderRadius: 6,
  border: `1px solid ${COLORS.borderStrong}`,
  background: 'rgba(255, 255, 255, 0.04)',
  color: COLORS.textPrimary,
  cursor: 'pointer',
  fontFamily: 'inherit',
  fontSize: 12.5,
  fontWeight: 700,
};

const bodyStyle: CSSProperties = {
  flex: 1,
  overflowY: 'auto',
  padding: 16,
  display: 'grid',
  gap: 16,
};

const legendShellStyle: CSSProperties = {
  display: 'grid',
  gap: 10,
  padding: 14,
  borderRadius: 8,
  border: `1px solid ${COLORS.borderSubtle}`,
  background: 'rgba(2, 6, 23, 0.34)',
};

const legendEyebrowStyle: CSSProperties = {
  margin: 0,
  color: TONE_TINT.teal.accent,
  fontSize: 11,
  fontWeight: 800,
  letterSpacing: 0.6,
  textTransform: 'uppercase',
};

const legendListStyle: CSSProperties = {
  display: 'grid',
  gap: 9,
  margin: 0,
  padding: 0,
  listStyle: 'none',
};

const legendItemStyle: CSSProperties = {
  display: 'grid',
  gap: 2,
};

const legendPlainStyle: CSSProperties = {
  color: COLORS.textPrimary,
  fontSize: 12.5,
  fontWeight: 800,
};

const legendMeaningStyle: CSSProperties = {
  color: COLORS.textSecondary,
  fontSize: 12,
  lineHeight: 1.45,
};

const legendTermStyle: CSSProperties = {
  color: COLORS.textPrimary,
  fontFamily: FONT_MONO,
  fontSize: 12,
  fontWeight: 800,
};

/**
 * "Why this verdict" methodology drawer — the single home for the deep
 * explanation. It absorbs the AuditVerdictExplainer prose (Stage 19/20/21,
 * accepted_accuracy, Generation Readiness, the verifier scope/boundary strings),
 * the Evidence Packet flight-recorder FAQ, and an honesty legend that maps the
 * plain console relabels back to the model-internal terms. None of this internal
 * vocabulary appears on the default console surface — it lives only here, behind
 * the `?` affordance.
 */
export function MethodologyDrawer({
  open,
  onClose,
  verdict = null,
  confidence = null,
  chips,
  verifierDecision = null,
  lifecycleMessage = null,
}: MethodologyDrawerProps): JSX.Element | null {
  const closeRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener('keydown', handler);
    closeRef.current?.focus();
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <>
      <div
        aria-hidden="true"
        data-testid="methodology-drawer-backdrop"
        style={backdropStyle}
        onClick={onClose}
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-label="Why this verdict — methodology"
        data-testid="methodology-drawer"
        style={drawerStyle}
      >
        <header style={headerStyle}>
          <h2 style={titleStyle}>Why this verdict</h2>
          <button
            ref={closeRef}
            type="button"
            data-testid="methodology-drawer-close"
            style={closeButtonStyle}
            onClick={onClose}
            aria-label="Close methodology drawer"
          >
            Close
          </button>
        </header>
        <div style={bodyStyle}>
          <AuditVerdictExplainer
            verdict={verdict}
            confidence={confidence}
            chips={chips}
            verifierDecision={verifierDecision}
            lifecycleMessage={lifecycleMessage}
          />

          <section style={legendShellStyle} aria-label="Plain-language relabel legend">
            <p style={legendEyebrowStyle}>What the plain labels mean</p>
            <ul style={legendListStyle}>
              {RELABEL_LEGEND.map((entry) => (
                <li key={entry.plain} style={legendItemStyle}>
                  <span style={legendPlainStyle}>{entry.plain}</span>
                  <span style={legendMeaningStyle}>{entry.meaning}</span>
                </li>
              ))}
            </ul>
          </section>

          <section style={legendShellStyle} aria-label="Confidence source legend">
            <p style={legendEyebrowStyle}>Where confidence comes from</p>
            <ul style={legendListStyle}>
              {STAGE_LEGEND.map((entry) => (
                <li key={entry.term} style={legendItemStyle}>
                  <span style={legendTermStyle}>{entry.term}</span>
                  <span style={legendMeaningStyle}>{entry.meaning}</span>
                </li>
              ))}
            </ul>
          </section>

          <EvidencePacketFlightRecorderFaq />
        </div>
      </aside>
    </>
  );
}

export default MethodologyDrawer;

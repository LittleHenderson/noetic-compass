import type { CSSProperties } from 'react';
import {
  ACCENT_AMBER,
  ACCENT_TEAL,
  COLORS,
  FONT_FAMILY,
  FONT_MONO,
} from '../../lib/designTokens';
import type {
  AuditVerdict,
  ProvenanceChip,
  ProvenanceChipId,
  VerifierDecision,
} from '../../lib/casHarnessAudit';
import { AuditTerm } from './AuditTerm';

export interface AuditVerdictExplainerProps {
  verdict?: AuditVerdict | null;
  confidence?: number | null;
  chips: ProvenanceChip[];
  verifierDecision?: VerifierDecision | null;
  lifecycleMessage?: string | null;
}

const REQUIRED_ORDER: ProvenanceChipId[] = [
  'model_proof',
  'cas_readout',
  'causal_proof',
  'control_proof',
  'output_proof',
  'packet_proof',
];

const shellStyle: CSSProperties = {
  display: 'grid',
  gap: 14,
  padding: 16,
  borderRadius: 8,
  border: '1px solid rgba(45, 212, 191, 0.18)',
  background: 'rgba(45, 212, 191, 0.045)',
  fontFamily: FONT_FAMILY,
};

const eyebrowStyle: CSSProperties = {
  margin: 0,
  color: ACCENT_TEAL,
  fontSize: 11,
  fontWeight: 800,
  letterSpacing: 0.6,
  textTransform: 'uppercase',
};

const headlineStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textPrimary,
  fontSize: 18,
  lineHeight: 1.35,
  fontWeight: 850,
};

const bodyStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 13,
  lineHeight: 1.55,
};

const proofGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
  gap: 8,
};

const proofRowStyle = (state: 'pass' | 'blocked' | 'unknown'): CSSProperties => ({
  minHeight: 92,
  padding: 10,
  borderRadius: 6,
  border:
    state === 'pass'
      ? '1px solid rgba(45, 212, 191, 0.30)'
      : state === 'blocked'
        ? '1px solid rgba(251, 191, 36, 0.34)'
        : '1px solid rgba(148, 163, 184, 0.20)',
  background:
    state === 'pass'
      ? 'rgba(45, 212, 191, 0.07)'
      : state === 'blocked'
        ? 'rgba(251, 191, 36, 0.08)'
        : 'rgba(148, 163, 184, 0.045)',
});

const proofNameStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 8,
  color: COLORS.textPrimary,
  fontSize: 12,
  fontWeight: 800,
};

const statusPillStyle = (state: 'pass' | 'blocked' | 'unknown'): CSSProperties => ({
  flex: '0 0 auto',
  padding: '2px 6px',
  borderRadius: 4,
  color:
    state === 'pass'
      ? '#ccfbf1'
      : state === 'blocked'
        ? '#fef3c7'
        : COLORS.textMuted,
  background:
    state === 'pass'
      ? 'rgba(45, 212, 191, 0.12)'
      : state === 'blocked'
        ? 'rgba(251, 191, 36, 0.11)'
        : 'rgba(148, 163, 184, 0.08)',
  fontSize: 10,
  fontFamily: FONT_MONO,
  textTransform: 'uppercase',
});

const proofTextStyle: CSSProperties = {
  margin: '7px 0 0 0',
  color: COLORS.textSecondary,
  fontSize: 12,
  lineHeight: 1.45,
};

const decisionBoxStyle: CSSProperties = {
  display: 'grid',
  gap: 6,
  padding: 12,
  borderRadius: 6,
  border: '1px solid rgba(255, 255, 255, 0.07)',
  background: 'rgba(2, 6, 23, 0.28)',
};

const sourceStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textMuted,
  fontSize: 12,
  lineHeight: 1.45,
  fontFamily: FONT_MONO,
};

function chipState(chip: ProvenanceChip | undefined): 'pass' | 'blocked' | 'unknown' {
  if (!chip) return 'unknown';
  if (chip.status === 'verified' || chip.status === 'present') return 'pass';
  if (chip.status === 'missing' || chip.status === 'failed' || chip.status === 'unavailable') {
    return 'blocked';
  }
  return 'unknown';
}

function chipStatusLabel(chip: ProvenanceChip | undefined): string {
  if (!chip) return 'pending';
  if (chip.status === 'verified' || chip.status === 'present') return 'pass';
  return chip.status.replace('_', ' ');
}

function confidencePercent(confidence?: number | null): string {
  if (confidence == null || !Number.isFinite(confidence)) return 'not available';
  return `${Math.round(Math.max(0, Math.min(1, confidence)) * 100)}%`;
}

function proofSummary(chips: ProvenanceChip[]): { passed: number; blocked: number } {
  let passed = 0;
  let blocked = 0;
  const byId = new Map(chips.map((chip) => [chip.id, chip]));
  REQUIRED_ORDER.forEach((id) => {
    const state = chipState(byId.get(id));
    if (state === 'pass') passed += 1;
    if (state === 'blocked' || state === 'unknown') blocked += 1;
  });
  return { passed, blocked };
}

function verdictHeadline(
  verdict: AuditVerdict | null | undefined,
  chips: ProvenanceChip[],
  verifierDecision?: VerifierDecision | null,
): string {
  const { blocked } = proofSummary(chips);
  if (!verdict) {
    return 'No verdict yet: the audit has not produced an evidence-backed decision.';
  }
  if (verdict === 'ACCEPT') {
    return 'Accepted because the verifier explicitly allowed it and all required proof chips passed.';
  }
  if (verdict === 'SUPPRESS') {
    return 'Suppressed because the verifier rejected the row and Stage 20 readiness said suppress.';
  }
  if (blocked > 0) {
    return 'Flagged because required proof is missing, unavailable, or failed.';
  }
  if (verifierDecision) {
    return 'Flagged because the verifier decision requires human review, not automatic trust.';
  }
  return 'Flagged because proof exists, but no explicit Stage 19/20/21 verifier decision is attached.';
}

function confidenceSource(
  verdict: AuditVerdict | null | undefined,
  confidence: number | null | undefined,
): string {
  if (confidence == null) {
    return 'Confidence source: none. The gate blocked a final numeric trust score.';
  }
  if (verdict === 'ACCEPT') {
    return 'Confidence source: Stage 19 accepted_accuracy from the Verification Stack mode profile.';
  }
  if (verdict === 'SUPPRESS') {
    return 'Confidence source: Stage 20 risk_score from Generation Readiness.';
  }
  return 'Confidence source: explicit verifier decision, routed to human review.';
}

function customerSentence(
  verdict: AuditVerdict | null | undefined,
  chips: ProvenanceChip[],
): string {
  const { passed, blocked } = proofSummary(chips);
  if (!verdict) {
    return `Tell the user: CAS has not returned a verdict yet. Proof chips ready: ${passed}/6.`;
  }
  if (verdict === 'ACCEPT') {
    return `Tell the user: CAS accepted this output because the verifier allowed it and ${passed}/6 required proof chips passed.`;
  }
  if (verdict === 'SUPPRESS') {
    return `Tell the user: CAS suppressed this output because the verifier found a suppress condition and ${passed}/6 required proof chips passed.`;
  }
  return `Tell the user: CAS flagged this for human review because ${blocked}/6 required proof chips were not pass-ready or the verifier requested review.`;
}

function chipMeaning(id: ProvenanceChipId): JSX.Element {
  switch (id) {
    case 'model_proof':
      return <>Which exact model or weight artifact was audited.</>;
    case 'cas_readout':
      return <>CAS found the model-internal signal it is judging.</>;
    case 'causal_proof':
      return (
        <>
          <AuditTerm term="ablation">Ablation</AuditTerm> or intervention shows the
          CAS direction matters.
        </>
      );
    case 'control_proof':
      return (
        <>
          <AuditTerm term="matchedControl">Matched controls</AuditTerm> and{' '}
          <AuditTerm term="baseline">baselines</AuditTerm> did not explain the
          same effect.
        </>
      );
    case 'output_proof':
      return <>The verdict is tied to observed model output.</>;
    case 'packet_proof':
      return (
        <>
          The audit trail is attached to an{' '}
          <AuditTerm term="evidencePacket">Evidence Packet</AuditTerm>.
        </>
      );
  }
}

export function AuditVerdictExplainer({
  verdict = null,
  confidence = null,
  chips,
  verifierDecision = null,
  lifecycleMessage = null,
}: AuditVerdictExplainerProps): JSX.Element {
  const byId = new Map(chips.map((chip) => [chip.id, chip]));
  const { passed } = proofSummary(chips);

  return (
    <section style={shellStyle} aria-labelledby="audit-verdict-explainer-heading">
      <div>
        <p style={eyebrowStyle}>Why this verdict happened</p>
        <h2 id="audit-verdict-explainer-heading" style={headlineStyle}>
          {verdictHeadline(verdict, chips, verifierDecision)}
        </h2>
      </div>

      <div style={decisionBoxStyle}>
        <p style={bodyStyle}>{customerSentence(verdict, chips)}</p>
        <p style={bodyStyle}>
          {confidenceSource(verdict, confidence)} Current confidence:{' '}
          <strong style={{ color: COLORS.textPrimary }}>{confidencePercent(confidence)}</strong>.
        </p>
        {verifierDecision ? (
          <>
            <p style={bodyStyle}>{verifierDecision.reason}</p>
            <p style={sourceStyle}>Verifier source: {verifierDecision.source}</p>
          </>
        ) : lifecycleMessage ? (
          <p style={bodyStyle}>{lifecycleMessage}</p>
        ) : null}
      </div>

      <div style={proofGridStyle} aria-label={`Required proof chips passed ${passed} of 6`}>
        {REQUIRED_ORDER.map((id) => {
          const chip = byId.get(id);
          const state = chipState(chip);
          return (
            <article key={id} style={proofRowStyle(state)}>
              <div style={proofNameStyle}>
                <span>{chip?.name ?? id}</span>
                <span style={statusPillStyle(state)}>{chipStatusLabel(chip)}</span>
              </div>
              <p style={proofTextStyle}>{chipMeaning(id)}</p>
              <p style={proofTextStyle}>{chip?.detail ?? 'No evidence attached yet.'}</p>
            </article>
          );
        })}
      </div>

      <p style={{ ...bodyStyle, color: ACCENT_AMBER }}>
        Rule: the UI does not create verdicts. It only explains what the backend
        runner returned after checking the Evidence Packet and proof chips.
      </p>
    </section>
  );
}

export default AuditVerdictExplainer;

import type { CSSProperties } from 'react';
import {
  ACCENT_TEAL,
  COLORS,
  FONT_FAMILY,
  FONT_MONO,
} from '../../lib/designTokens';
import { AuditPopover } from './AuditPopover';
import type {
  AuditVerdict,
  ProvenanceChip,
  ProvenanceChipId,
  VerifierDecision,
} from '../../lib/casHarnessAudit';

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

const proofGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
  gap: 8,
};

const proofRowStyle = (state: 'pass' | 'blocked' | 'unknown'): CSSProperties => ({
  minHeight: 54,
  padding: 10,
  borderRadius: 6,
  cursor: 'help',
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

const compactLineStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  alignItems: 'center',
  gap: 8,
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 13,
  lineHeight: 1.4,
};

const scopeLineStyle: CSSProperties = {
  ...compactLineStyle,
  padding: '9px 10px',
  borderRadius: 6,
  border: '1px solid rgba(45, 212, 191, 0.20)',
  background: 'rgba(2, 6, 23, 0.26)',
};

const infoTipStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: 22,
  height: 22,
  borderRadius: 5,
  border: '1px solid rgba(45, 212, 191, 0.24)',
  background: 'rgba(45, 212, 191, 0.07)',
  color: '#ccfbf1',
  cursor: 'help',
  fontSize: 12,
  fontWeight: 900,
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

function isObjectLockGateBlocked(
  verdict: AuditVerdict | null | undefined,
  lifecycleMessage?: string | null,
): boolean {
  const message = lifecycleMessage?.toLowerCase() ?? '';
  return (
    verdict === 'FLAG_FOR_HUMAN_REVIEW' &&
    (message.includes('active object lock retention') ||
      message.includes('worm-retained evidence packet'))
  );
}

function verdictHeadline(
  verdict: AuditVerdict | null | undefined,
  chips: ProvenanceChip[],
  verifierDecision?: VerifierDecision | null,
  lifecycleMessage?: string | null,
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
  if (isObjectLockGateBlocked(verdict, lifecycleMessage)) {
    return 'Flagged because the Evidence Packet does not have active Object Lock retention yet.';
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
  verifierDecision?: VerifierDecision | null,
): string {
  if (confidence == null) {
    return 'Confidence source: none. The gate blocked a final numeric trust score.';
  }
  if (verifierDecision?.source === 'stage9_40e_packet_verifier') {
    return 'Confidence source: Stage 9 40E packet verifier; conservative minimum of hidden readout, bridge accuracy, and proof gates.';
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
  lifecycleMessage?: string | null,
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
  if (isObjectLockGateBlocked(verdict, lifecycleMessage)) {
    return 'Tell the user: CAS found an explicit verifier decision, but it cannot become final until the Evidence Packet is S3 re-read verified with active Object Lock retention.';
  }
  return `Tell the user: CAS flagged this for human review because ${blocked}/6 required proof chips were not pass-ready or the verifier requested review.`;
}

function verifierScopeLabel(verifierDecision?: VerifierDecision | null): string | null {
  const scope = verifierDecision?.decisionScope;
  if (!scope) return null;
  if (scope === 'stage9_40e_validation_packet') {
    return 'Scope: Stage 9 40E validation packet';
  }
  return `Scope: ${scope.replaceAll('_', ' ')}`;
}

function verifierCoverageLabel(verifierDecision?: VerifierDecision | null): string | null {
  const coverage = verifierDecision?.coverage;
  if (!coverage) return null;
  const parts: string[] = [];
  if (typeof coverage.caseCount === 'number') {
    parts.push(`${coverage.caseCount} cases`);
  }
  if (typeof coverage.classCount === 'number') {
    parts.push(`${coverage.classCount} classes`);
  }
  return parts.length > 0 ? `Coverage: ${parts.join(' / ')}` : null;
}

function verifierBoundary(verifierDecision?: VerifierDecision | null): string | null {
  if (verifierDecision?.decisionScope === 'stage9_40e_validation_packet') {
    return 'Boundary: this is a validation-packet verdict, not a live customer-production row.';
  }
  return null;
}

const CHIP_MEANING_TEXT: Record<ProvenanceChipId, string> = {
  model_proof: 'Which exact model or weight artifact was audited.',
  cas_readout: 'CAS found the model-internal signal it is judging.',
  causal_proof: 'Ablation or intervention shows the CAS direction matters.',
  control_proof:
    'Matched controls and baselines did not explain the same effect.',
  output_proof: 'The verdict is tied to observed model output.',
  packet_proof:
    'The audit trail is attached to an Evidence Packet. Final ACCEPT/SUPPRESS requires S3 re-read verification plus active Object Lock retention.',
};

export function AuditVerdictExplainer({
  verdict = null,
  confidence = null,
  chips,
  verifierDecision = null,
  lifecycleMessage = null,
}: AuditVerdictExplainerProps): JSX.Element {
  const byId = new Map(chips.map((chip) => [chip.id, chip]));
  const { passed } = proofSummary(chips);
  const confidenceText = confidencePercent(confidence);
  const scopeLabel = verifierScopeLabel(verifierDecision);
  const coverageLabel = verifierCoverageLabel(verifierDecision);
  const boundaryLabel = verifierBoundary(verifierDecision);
  const decisionHelp = [
    customerSentence(verdict, chips, lifecycleMessage),
    `${confidenceSource(verdict, confidence, verifierDecision)} Current confidence: ${confidenceText}.`,
    verifierDecision ? verifierDecision.reason : lifecycleMessage,
    verifierDecision ? `Verifier source: ${verifierDecision.source}` : null,
    scopeLabel,
    coverageLabel,
    boundaryLabel,
    'Rule: the UI does not create verdicts. It only explains what the backend runner returned after checking the Evidence Packet and proof chips.',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <section
      style={shellStyle}
      aria-labelledby="audit-verdict-explainer-heading"
    >
      <div>
        <p style={eyebrowStyle}>Why this verdict happened</p>
        <AuditPopover briefing={decisionHelp} block placement="bottom" width={420}>
          <h2 id="audit-verdict-explainer-heading" style={headlineStyle}>
            {verdictHeadline(verdict, chips, verifierDecision, lifecycleMessage)}
          </h2>
        </AuditPopover>
      </div>

      <p style={compactLineStyle}>
        <span>Proof chips ready: {passed}/6</span>
        <span>Confidence: {confidenceText}</span>
        <AuditPopover briefing={decisionHelp} placement="right" width={420}>
          <span aria-label={decisionHelp} role="note" style={infoTipStyle}>
            ?
          </span>
        </AuditPopover>
      </p>

      {scopeLabel || coverageLabel ? (
        <p style={scopeLineStyle}>
          {scopeLabel ? <span>{scopeLabel}</span> : null}
          {coverageLabel ? <span>{coverageLabel}</span> : null}
          {boundaryLabel ? (
            <AuditPopover briefing={boundaryLabel} placement="right" width={360}>
              <span aria-label={boundaryLabel} role="note" style={infoTipStyle}>
                !
              </span>
            </AuditPopover>
          ) : null}
        </p>
      ) : null}

      <div style={proofGridStyle} aria-label={`Required proof chips passed ${passed} of 6`}>
        {REQUIRED_ORDER.map((id) => {
          const chip = byId.get(id);
          const state = chipState(chip);
          const chipHelp = `${CHIP_MEANING_TEXT[id]} ${chip?.detail ?? 'No evidence attached yet.'}`;
          return (
            <article key={id} style={proofRowStyle(state)}>
              <AuditPopover briefing={chipHelp} block placement="bottom">
                <div style={proofNameStyle}>
                  <span>{chip?.name ?? id}</span>
                  <span style={statusPillStyle(state)}>{chipStatusLabel(chip)}</span>
                </div>
              </AuditPopover>
            </article>
          );
        })}
      </div>
    </section>
  );
}

export default AuditVerdictExplainer;

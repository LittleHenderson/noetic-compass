import type { CSSProperties } from 'react';
import {
  COLORS,
  FONT_FAMILY,
  FONT_MONO,
  TONE_TINT,
} from '../../lib/designTokens';
import type { CasHarnessInstructionIntegrityReport } from '../../lib/casHarnessAuditApi';

export interface InstructionIntegrityPanelProps {
  report: CasHarnessInstructionIntegrityReport | null;
}

const panelStyle = (flagged: boolean): CSSProperties => {
  const tone = flagged ? TONE_TINT.amber : TONE_TINT.teal;
  return {
    display: 'grid',
    gap: 12,
    padding: 16,
    borderRadius: 8,
    border: `1px solid ${tone.borderSoft}`,
    background: flagged ? 'rgba(251, 191, 36, 0.055)' : 'rgba(45, 212, 191, 0.055)',
    fontFamily: FONT_FAMILY,
  };
};

const headerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'flex-start',
  justifyContent: 'space-between',
  gap: 12,
};

const titleWrapStyle: CSSProperties = {
  display: 'grid',
  gap: 4,
};

const eyebrowStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 11,
  fontWeight: 800,
  letterSpacing: 0.6,
  textTransform: 'uppercase',
};

const titleStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textPrimary,
  fontSize: 15,
  fontWeight: 850,
};

const subcopyStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 12,
  lineHeight: 1.45,
};

const statusPillStyle = (flagged: boolean): CSSProperties => {
  const tone = flagged ? TONE_TINT.amber : TONE_TINT.teal;
  return {
    flex: '0 0 auto',
    padding: '4px 8px',
    borderRadius: 6,
    border: `1px solid ${tone.borderSoft}`,
    background: tone.fillSoft,
    color: tone.text,
    fontFamily: FONT_MONO,
    fontSize: 10,
    fontWeight: 850,
    lineHeight: 1.2,
    textTransform: 'uppercase',
    whiteSpace: 'nowrap',
  };
};

const listStyle: CSSProperties = {
  display: 'grid',
  gap: 8,
  margin: 0,
  padding: 0,
  listStyle: 'none',
};

const findingStyle: CSSProperties = {
  display: 'grid',
  gap: 5,
  padding: '9px 10px',
  borderRadius: 6,
  border: `1px solid ${COLORS.borderSubtle}`,
  background: 'rgba(2, 6, 23, 0.30)',
};

const findingTopStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  alignItems: 'baseline',
  justifyContent: 'space-between',
  gap: 8,
};

const findingKindStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textPrimary,
  fontSize: 12.5,
  fontWeight: 800,
};

const metaStyle: CSSProperties = {
  color: COLORS.textMuted,
  fontFamily: FONT_MONO,
  fontSize: 10.5,
  fontWeight: 800,
  textTransform: 'uppercase',
};

const excerptStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 12,
  lineHeight: 1.45,
  overflowWrap: 'anywhere',
};

const quarantineStyle: CSSProperties = {
  display: 'grid',
  gap: 10,
  padding: '10px 12px',
  borderRadius: 6,
  border: `1px solid ${TONE_TINT.amber.borderSoft}`,
  background: 'rgba(251, 191, 36, 0.075)',
};

const quarantineHeaderStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'baseline',
  justifyContent: 'space-between',
  gap: 8,
};

const sanitizedTextStyle: CSSProperties = {
  margin: 0,
  maxHeight: 118,
  overflow: 'auto',
  padding: '8px 9px',
  borderRadius: 6,
  border: `1px solid ${COLORS.borderSubtle}`,
  background: 'rgba(2, 6, 23, 0.42)',
  color: COLORS.textSecondary,
  fontFamily: FONT_MONO,
  fontSize: 11,
  lineHeight: 1.45,
  overflowWrap: 'anywhere',
  whiteSpace: 'pre-wrap',
};

const flagWrapStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 6,
};

const flagStyle: CSSProperties = {
  padding: '3px 7px',
  borderRadius: 5,
  border: `1px solid ${TONE_TINT.muted.borderSoft}`,
  background: TONE_TINT.muted.fillSoft,
  color: COLORS.textSecondary,
  fontFamily: FONT_MONO,
  fontSize: 10.5,
  fontWeight: 800,
};

function displayKind(kind: string): string {
  return kind.replace(/_/g, ' ');
}

function firstSanitizedText(report: CasHarnessInstructionIntegrityReport): string | null {
  const quarantine = report.quarantine;
  if (!quarantine) return null;
  return (
    quarantine.sanitized_prompt_text ??
    quarantine.sanitized_scenario_text ??
    quarantine.sanitized_output_text ??
    null
  );
}

export function InstructionIntegrityPanel({
  report,
}: InstructionIntegrityPanelProps): JSX.Element | null {
  if (!report) return null;

  const flagged = report.status === 'FLAG_FOR_HUMAN_REVIEW';
  const visibleFindings = report.findings.slice(0, 4);
  const hiddenFindingCount = Math.max(0, report.findings.length - visibleFindings.length);
  const flags = report.gluing.lacunarity_flags;
  const rpmReasonContinuity = report.gluing.rpm_reason_continuity;
  const cjtPcbaDiagnostics = report.gluing.cjt_pcba_diagnostics;
  const activationDetection = report.gluing.activation_detection;
  const showRpmContinuity = Boolean(
    rpmReasonContinuity &&
      (rpmReasonContinuity.status === 'FLAG_FOR_HUMAN_REVIEW' ||
        rpmReasonContinuity.upstream_risk_kinds.length > 0),
  );
  const showCjtPcbaDiagnostics = Boolean(
    cjtPcbaDiagnostics &&
      (cjtPcbaDiagnostics.status === 'FLAG_FOR_HUMAN_REVIEW' ||
        cjtPcbaDiagnostics.surface_finding_count > 0),
  );
  const visibleCjtPcbaDiagnostics = cjtPcbaDiagnostics?.diagnostics.slice(0, 3) ?? [];
  const quarantine = report.quarantine;
  const blockedSpans = quarantine?.blocked_spans ?? [];
  const visibleBlockedSpans = blockedSpans.slice(0, 3);
  const hiddenBlockedSpanCount = Math.max(0, blockedSpans.length - visibleBlockedSpans.length);
  const sanitizedText = firstSanitizedText(report);

  return (
    <section
      style={panelStyle(flagged)}
      aria-label="Instruction integrity shadow scan"
      data-testid="instruction-integrity-panel"
    >
      <div style={headerStyle}>
        <div style={titleWrapStyle}>
          <p style={eyebrowStyle}>Instruction integrity</p>
          <p style={titleStyle}>Shadow scan</p>
          <p style={subcopyStyle}>
            {flagged
              ? 'Potential instruction-integrity risk was routed to FLAG_FOR_HUMAN_REVIEW.'
              : 'No shadow findings were recorded for this session.'}
          </p>
        </div>
        <span style={statusPillStyle(flagged)}>{report.status}</span>
      </div>

      <div style={flagWrapStyle} aria-label="Instruction integrity metadata">
        <span style={flagStyle}>truth: {report.truth_state}</span>
        <span style={flagStyle}>effect: {report.verdict_effect}</span>
        <span style={flagStyle}>coverage: {report.gluing.coverage_status}</span>
      </div>

      {flags.length > 0 ? (
        <div style={flagWrapStyle} aria-label="Instruction integrity lacunarity flags">
          {flags.map((flag) => (
            <span key={flag} style={flagStyle}>
              {flag}
            </span>
          ))}
        </div>
      ) : null}

      {showRpmContinuity && rpmReasonContinuity ? (
        <div style={findingStyle} aria-label="RPM reason continuity">
          <div style={findingTopStyle}>
            <p style={findingKindStyle}>RPM reason continuity</p>
            <span style={metaStyle}>{rpmReasonContinuity.status}</span>
          </div>
          <div style={flagWrapStyle}>
            <span style={flagStyle}>breaks: {rpmReasonContinuity.break_count}</span>
            <span style={flagStyle}>
              lacunarity spike: {rpmReasonContinuity.lacunarity_spike ? 'true' : 'false'}
            </span>
          </div>
          <p style={excerptStyle}>{rpmReasonContinuity.claim_ceiling}</p>
        </div>
      ) : null}

      {showCjtPcbaDiagnostics && cjtPcbaDiagnostics ? (
        <div style={findingStyle} aria-label="CJT PCBA diagnostics">
          <div style={findingTopStyle}>
            <p style={findingKindStyle}>CJT/PCBA diagnostics</p>
            <span style={metaStyle}>{cjtPcbaDiagnostics.status}</span>
          </div>
          <div style={flagWrapStyle}>
            <span style={flagStyle}>diagnostics: {cjtPcbaDiagnostics.diagnostic_count}</span>
            <span style={flagStyle}>
              decoded surfaces: {cjtPcbaDiagnostics.surface_finding_count}
            </span>
          </div>
          {visibleCjtPcbaDiagnostics.length > 0 ? (
            <ul style={listStyle} role="list" aria-label="CJT PCBA diagnostic rows">
              {visibleCjtPcbaDiagnostics.map((diagnostic) => (
                <li
                  key={`${diagnostic.kind}-${diagnostic.source}-${diagnostic.region}`}
                  style={findingStyle}
                >
                  <div style={findingTopStyle}>
                    <p style={findingKindStyle}>{displayKind(diagnostic.kind)}</p>
                    <span style={metaStyle}>
                      {diagnostic.board} {diagnostic.test_point}
                    </span>
                  </div>
                  <p style={excerptStyle}>{diagnostic.region}</p>
                </li>
              ))}
            </ul>
          ) : null}
          <p style={excerptStyle}>{cjtPcbaDiagnostics.claim_ceiling}</p>
        </div>
      ) : null}

      {activationDetection ? (
        <div style={findingStyle} aria-label="Activation detection boundary">
          <div style={findingTopStyle}>
            <p style={findingKindStyle}>Activation detection</p>
            <span style={metaStyle}>{activationDetection.status}</span>
          </div>
          <div style={flagWrapStyle}>
            <span style={flagStyle}>DETECTION ONLY</span>
            <span style={flagStyle}>{activationDetection.claim_level}</span>
            <span style={flagStyle}>effect: {activationDetection.verdict_effect}</span>
            {activationDetection.label ? (
              <span style={flagStyle}>label: {activationDetection.label}</span>
            ) : null}
          </div>
          <p style={excerptStyle}>{activationDetection.reason}</p>
          <p style={excerptStyle}>{activationDetection.claim_ceiling}</p>
        </div>
      ) : null}

      {visibleFindings.length > 0 ? (
        <ul style={listStyle} role="list">
          {visibleFindings.map((finding) => (
            <li key={`${finding.kind}-${finding.span_hash}`} style={findingStyle}>
              <div style={findingTopStyle}>
                <p style={findingKindStyle}>{displayKind(finding.kind)}</p>
                <span style={metaStyle}>{finding.severity}</span>
              </div>
              <p style={excerptStyle}>{finding.span_excerpt}</p>
              <p style={excerptStyle}>{finding.reason}</p>
            </li>
          ))}
          {hiddenFindingCount > 0 ? (
            <li style={findingStyle}>
              <p style={excerptStyle}>{hiddenFindingCount} more shadow finding(s) recorded.</p>
            </li>
          ) : null}
        </ul>
      ) : null}

      {quarantine ? (
        <div style={quarantineStyle} aria-label="Instruction quarantine active-context proposal">
          <div style={quarantineHeaderStyle}>
            <div style={titleWrapStyle}>
              <p style={eyebrowStyle}>Active context</p>
              <p style={titleStyle}>Shadow quarantine proposal</p>
            </div>
            <span style={statusPillStyle(quarantine.status === 'FLAG_FOR_HUMAN_REVIEW')}>
              {blockedSpans.length} blocked
            </span>
          </div>

          {visibleBlockedSpans.length > 0 ? (
            <ul style={listStyle} role="list" aria-label="Blocked instruction spans">
              {visibleBlockedSpans.map((span) => (
                <li key={`${span.kind}-${span.span_hash}`} style={findingStyle}>
                  <div style={findingTopStyle}>
                    <p style={findingKindStyle}>{displayKind(span.kind)}</p>
                    <span style={metaStyle}>{span.replacement}</span>
                  </div>
                  <p style={excerptStyle}>{span.span_excerpt}</p>
                </li>
              ))}
              {hiddenBlockedSpanCount > 0 ? (
                <li style={findingStyle}>
                  <p style={excerptStyle}>{hiddenBlockedSpanCount} more blocked span(s) recorded.</p>
                </li>
              ) : null}
            </ul>
          ) : null}

          {sanitizedText ? (
            <p style={sanitizedTextStyle} aria-label="Sanitized active-context text">
              {sanitizedText}
            </p>
          ) : null}

          <p style={subcopyStyle}>{quarantine.claim_ceiling}</p>
        </div>
      ) : null}
    </section>
  );
}

export default InstructionIntegrityPanel;

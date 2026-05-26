/**
 * BlindspotInterpretation — translates a CAS cover-class hit into the
 * kind of human concern the model may be failing to consider.
 *
 * Layout (verbatim from product spec):
 *
 *   The model may be overlooking whether someone has real choice,
 *   permission, or control in this situation.
 *
 *   CAS source: F5 Agency
 *   Confidence: 72% medium
 *   Evidence: neuron-cover overlap + ablation support
 *
 * Rules:
 *   - Plain-English sentence is the largest text and the lead. The CAS
 *     source line is small dim text — provenance, not headline.
 *   - Confidence reads as "X% band-name" (e.g. "72% medium"). When the
 *     band is "unavailable", we print
 *     "Confidence: not available (insufficient evidence)" instead.
 *   - Evidence joins `evidenceSources` with " + " (e.g.
 *     "neuron-cover overlap + ablation support"). When the list is
 *     empty we OMIT the Evidence line entirely — never write
 *     "Evidence: none".
 */

import type { CSSProperties } from 'react';

import {
  DRIVE_TRANSLATIONS,
  REGISTER_NAMES,
  type DriveId,
  type RegisterId,
} from '../../lib/driveTranslations';
import {
  bandForConfidence,
  formatConfidenceLine,
  type ConfidenceBand,
} from '../../lib/confidenceBands';
import { COLORS } from '../../lib/designTokens';
import LiquidGlassTooltip from '../ui/LiquidGlassTooltip';

export interface BlindspotInterpretationProps {
  classKey?: string;
  driveId: DriveId;
  register?: RegisterId;
  confidence: number | null;
  evidenceSources: string[];
  showShortLead?: boolean;
  memberCount?: number;
  isFocused?: boolean;
  onFocusCover?: () => void;
}

const wrapperStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
  padding: '10px 12px',
  borderRadius: 8,
  background: 'rgba(15, 23, 42, 0.55)',
  border: '1px solid rgba(255,255,255,0.06)',
};

const headlineStyle: CSSProperties = {
  margin: 0,
  fontSize: 15,
  lineHeight: 1.45,
  fontWeight: 600,
  color: COLORS.textPrimary ?? '#e5e7eb',
};

const shortLeadStyle: CSSProperties = {
  margin: 0,
  fontSize: 15,
  lineHeight: 1.4,
  fontWeight: 700,
  color: COLORS.textPrimary ?? '#e5e7eb',
};

const supportingSentenceStyle: CSSProperties = {
  margin: 0,
  fontSize: 13,
  lineHeight: 1.45,
  color: '#cbd5e1',
};

const provenanceStyle: CSSProperties = {
  margin: 0,
  fontSize: 11,
  color: '#94a3b8',
  letterSpacing: 0.2,
};

const confidenceStyle: CSSProperties = {
  margin: 0,
  fontSize: 12,
  color: '#cbd5e1',
};

const evidenceStyle: CSSProperties = {
  margin: 0,
  fontSize: 12,
  color: '#94a3b8',
  fontStyle: 'italic',
};

const actionRowStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 10,
};

const focusButtonStyle: CSSProperties = {
  flexShrink: 0,
  border: '1px solid rgba(45, 212, 191, 0.45)',
  background: 'rgba(20, 184, 166, 0.12)',
  color: '#ccfbf1',
  borderRadius: 7,
  padding: '5px 8px',
  fontSize: 11,
  fontWeight: 700,
  cursor: 'pointer',
};

function bandLabel(band: ConfidenceBand): string {
  // Map internal band names to the spec's display tokens so tests can
  // assert against the exact strings the user wrote.
  if (band === 'unavailable') return 'unavailable';
  return band;
}

export default function BlindspotInterpretation(
  props: BlindspotInterpretationProps,
): JSX.Element {
  const {
    classKey,
    driveId,
    register,
    confidence,
    evidenceSources,
    showShortLead = false,
    memberCount,
    isFocused = false,
    onFocusCover,
  } = props;
  const translation = DRIVE_TRANSLATIONS[driveId];
  const band = bandForConfidence(confidence);

  // Provenance line: "CAS source: F5 Agency" or
  // "CAS source: F5 Agency · analytical register"
  let casSource = `${driveId} ${translation.name}`;
  if (register && register in REGISTER_NAMES) {
    casSource = `${casSource} · ${REGISTER_NAMES[register]}`;
  }

  const evidenceLine = evidenceSources.length
    ? `Evidence: ${evidenceSources.join(' + ')}`
    : null;

  const confidenceText = formatConfidenceLine(confidence, band);
  // We still want the "Confidence:" prefix for both branches, but
  // formatConfidenceLine returns the right tail in either case.
  const confidenceLine = `Confidence: ${confidenceText}`;

  return (
    <div
      data-testid="blindspot-interpretation"
      data-drive={driveId}
      data-band={band}
      data-band-label={bandLabel(band)}
      data-class-key={classKey}
      data-focused={isFocused ? 'true' : 'false'}
      style={{
        ...wrapperStyle,
        border: isFocused
          ? '1px solid rgba(45, 212, 191, 0.78)'
          : wrapperStyle.border,
        boxShadow: isFocused ? '0 0 18px rgba(45, 212, 191, 0.22)' : 'none',
      }}
    >
      {showShortLead ? (
        <>
          <div style={actionRowStyle}>
            <p style={shortLeadStyle} data-testid="blindspot-short-lead">
              Possible blindspot: {translation.shortBlindspot}.
            </p>
            {onFocusCover ? (
              <LiquidGlassTooltip
                briefing={`Highlight ${classKey ?? driveId} cover neurons in the 3D network.`}
                focusable={false}
              >
                <button
                  type="button"
                  style={{
                    ...focusButtonStyle,
                    background: isFocused
                      ? 'rgba(20, 184, 166, 0.28)'
                      : focusButtonStyle.background,
                  }}
                  onClick={onFocusCover}
                  data-testid="blindspot-focus-cover"
                  aria-pressed={isFocused}
                >
                  {isFocused ? 'Showing neurons' : 'Show neurons'}
                  {typeof memberCount === 'number' ? ` (${memberCount})` : ''}
                </button>
              </LiquidGlassTooltip>
            ) : null}
          </div>
          <p style={supportingSentenceStyle} data-testid="blindspot-headline">
            {translation.sentence}
          </p>
        </>
      ) : (
        <div style={actionRowStyle}>
          <p style={headlineStyle} data-testid="blindspot-headline">
            {translation.sentence}
          </p>
          {onFocusCover ? (
            <LiquidGlassTooltip
              briefing={`Highlight ${classKey ?? driveId} cover neurons in the 3D network.`}
              focusable={false}
            >
              <button
                type="button"
                style={{
                  ...focusButtonStyle,
                  background: isFocused
                    ? 'rgba(20, 184, 166, 0.28)'
                    : focusButtonStyle.background,
                }}
                onClick={onFocusCover}
                data-testid="blindspot-focus-cover"
                aria-pressed={isFocused}
              >
                {isFocused ? 'Showing neurons' : 'Show neurons'}
                {typeof memberCount === 'number' ? ` (${memberCount})` : ''}
              </button>
            </LiquidGlassTooltip>
          ) : null}
        </div>
      )}
      <p style={provenanceStyle} data-testid="blindspot-cas-source">
        CAS source: {casSource}
      </p>
      <p
        style={confidenceStyle}
        data-testid="blindspot-confidence"
      >
        <LiquidGlassTooltip
          briefing="For live Pythia-160M, this is cover-level confidence: targeted_drop divided by clean_margin for the Stage 27F cover set. It is not a one-neuron-equals-one-meaning claim."
          placement="top"
          focusable={false}
        >
          <span>{confidenceLine}</span>
        </LiquidGlassTooltip>
      </p>
      {evidenceLine ? (
        <p style={evidenceStyle} data-testid="blindspot-evidence">
          {evidenceLine}
        </p>
      ) : null}
    </div>
  );
}

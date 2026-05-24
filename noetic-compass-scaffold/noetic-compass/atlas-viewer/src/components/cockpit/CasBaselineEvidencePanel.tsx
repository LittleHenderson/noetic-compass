import type { CSSProperties } from 'react';
import {
  CAS_BENCHMARK_BOUNDARY,
  CAS_BENCHMARK_EVIDENCE,
  CAS_BENCHMARK_HEADLINE,
  CAS_BENCHMARK_SUBHEAD,
} from '../../lib/casBenchmarkEvidence';
import { ACCENT_TEAL, COLORS, THEME } from '../../lib/designTokens';

const panelStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
  padding: 12,
  borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
  fontFamily: THEME.fontFamily,
};

const eyebrowStyle: CSSProperties = {
  margin: 0,
  color: ACCENT_TEAL,
  fontSize: 10.5,
  fontWeight: 800,
  letterSpacing: 1.2,
  textTransform: 'uppercase',
};

const titleStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textPrimary,
  fontSize: 16,
  fontWeight: 800,
  lineHeight: 1.2,
};

const bodyStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 12,
  lineHeight: 1.45,
};

const rowStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'minmax(0, 1fr)',
  gap: 6,
  padding: '9px 0',
  borderTop: '1px solid rgba(255, 255, 255, 0.06)',
};

const rowTitleStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textPrimary,
  fontSize: 12.5,
  fontWeight: 800,
};

const rowClaimStyle: CSSProperties = {
  margin: 0,
  color: '#e2e8f0',
  fontSize: 12,
  lineHeight: 1.35,
};

const factGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '1fr',
  gap: 5,
};

const factStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 11.5,
  lineHeight: 1.35,
};

const labelStyle: CSSProperties = {
  color: '#94a3b8',
  fontWeight: 800,
};

const boundaryStyle: CSSProperties = {
  margin: 0,
  padding: '8px 9px',
  borderRadius: 6,
  border: '1px solid rgba(234, 179, 8, 0.24)',
  background: 'rgba(234, 179, 8, 0.08)',
  color: '#fde68a',
  fontSize: 11.5,
  lineHeight: 1.4,
};

export default function CasBaselineEvidencePanel(): JSX.Element {
  return (
    <section
      style={panelStyle}
      aria-label="CAS versus baseline evidence"
      data-testid="cas-baseline-evidence-panel"
    >
      <div>
        <p style={eyebrowStyle}>Why CAS is different</p>
        <h2 style={titleStyle}>CAS vs baseline</h2>
      </div>
      <p style={bodyStyle}>
        <strong style={{ color: COLORS.textPrimary }}>{CAS_BENCHMARK_HEADLINE}</strong>{' '}
        {CAS_BENCHMARK_SUBHEAD}
      </p>
      <div>
        {CAS_BENCHMARK_EVIDENCE.map((item) => (
          <article key={item.id} style={rowStyle}>
            <h3 style={rowTitleStyle}>{item.headline}</h3>
            <p style={rowClaimStyle}>{item.plainClaim}</p>
            <div style={factGridStyle}>
              <p style={factStyle}>
                <span style={labelStyle}>CAS result: </span>
                {item.casResult}
              </p>
              <p style={factStyle}>
                <span style={labelStyle}>Baseline/control: </span>
                {item.baselineResult}
              </p>
              <p style={factStyle}>
                <span style={labelStyle}>Meaning: </span>
                {item.whyItMatters}
              </p>
              <p style={factStyle}>
                <span style={labelStyle}>Scope: </span>
                {item.scope}
              </p>
            </div>
          </article>
        ))}
      </div>
      <p style={boundaryStyle}>{CAS_BENCHMARK_BOUNDARY}</p>
    </section>
  );
}

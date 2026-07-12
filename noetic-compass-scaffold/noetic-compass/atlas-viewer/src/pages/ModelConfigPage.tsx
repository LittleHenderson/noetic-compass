import { useState, type CSSProperties } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { GlassPanel } from '../components/ui/GlassPanel';
import { PageShell } from '../components/ui/PageShell';
import {
  ACCENT_TEAL,
  COLORS,
  SPRING_SNAPPY,
  THEME,
} from '../lib/designTokens';

interface ModelOption {
  id: string;
  family: string;
  size: string;
  layers: number;
  available: boolean;
  notes: string;
}

const MODELS: ModelOption[] = [
  {
    id: 'pythia-160m',
    family: 'Pythia',
    size: '160M',
    layers: 12,
    available: true,
    notes:
      'Active model for the alpha cockpit. Cached activations + Mode 7 timeline visualizations.',
  },
  {
    id: 'qwen2.5-1.5b',
    family: 'Qwen 2.5',
    size: '1.5B',
    layers: 28,
    available: false,
    notes: 'Cross-architecture comparison target. Wiring in roadmap item #6.',
  },
  {
    id: 'custom-byo',
    family: 'External / BYO',
    size: '—',
    layers: 0,
    available: false,
    notes:
      'Bring-your-own-model attachment via the Architecture Mapper. Roadmap items #6 + #7.',
  },
];

const headingStyle: CSSProperties = {
  margin: 0,
  fontSize: 24,
  fontWeight: 700,
  letterSpacing: -0.3,
  color: COLORS.textPrimary,
};

const subheadingStyle: CSSProperties = {
  margin: '8px 0 18px 0',
  fontSize: 13.5,
  lineHeight: 1.55,
  color: COLORS.textSecondary,
};

const listStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
  marginBottom: 14,
};

const rowStyle = (active: boolean, available: boolean): CSSProperties => ({
  display: 'grid',
  gridTemplateColumns: '1fr auto',
  alignItems: 'center',
  gap: 12,
  padding: '12px 14px',
  borderRadius: 6,
  border: active
    ? `1px solid ${ACCENT_TEAL}`
    : '1px solid rgba(255, 255, 255, 0.06)',
  background: active
    ? 'rgba(45, 212, 191, 0.08)'
    : 'rgba(255, 255, 255, 0.02)',
  cursor: available ? 'pointer' : 'not-allowed',
  opacity: available ? 1 : 0.55,
  transition: 'border-color 0.15s ease, background 0.15s ease',
});

const rowTitleStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'baseline',
  gap: 10,
  fontSize: 14,
  fontWeight: 600,
  color: COLORS.textPrimary,
};

const rowMetaStyle: CSSProperties = {
  fontSize: 11.5,
  color: COLORS.textMuted,
  fontFamily: THEME.fontMono,
};

const rowNotesStyle: CSSProperties = {
  marginTop: 4,
  fontSize: 12,
  lineHeight: 1.5,
  color: COLORS.textSecondary,
};

const tagStyle = (kind: 'live' | 'soon'): CSSProperties => ({
  fontSize: 10,
  fontWeight: 700,
  letterSpacing: 1,
  textTransform: 'uppercase',
  padding: '3px 8px',
  borderRadius: 4,
  background:
    kind === 'live' ? 'rgba(34, 197, 94, 0.08)' : 'rgba(148, 163, 184, 0.06)',
  border:
    kind === 'live'
      ? '1px solid rgba(34, 197, 94, 0.35)'
      : '1px solid rgba(148, 163, 184, 0.20)',
  color: kind === 'live' ? '#86efac' : COLORS.textMuted,
});

const buttonStyle: CSSProperties = {
  width: '100%',
  marginTop: 6,
  padding: '10px 16px',
  borderRadius: 6,
  border: `1px solid ${ACCENT_TEAL}`,
  background: 'rgba(45, 212, 191, 0.08)',
  color: ACCENT_TEAL,
  fontSize: 13,
  fontWeight: 600,
  letterSpacing: 0.3,
  fontFamily: THEME.fontFamily,
  cursor: 'pointer',
};

const footnoteStyle: CSSProperties = {
  marginTop: 16,
  paddingTop: 14,
  borderTop: '1px solid rgba(255, 255, 255, 0.05)',
  fontSize: 11.5,
  lineHeight: 1.55,
  color: COLORS.textMuted,
};

export default function ModelConfigPage() {
  const navigate = useNavigate();
  const [selected, setSelected] = useState<string>('pythia-160m');

  return (
    <PageShell cardMaxWidth={540}>
      <GlassPanel intensity="regular" padding={24} ariaLabel="Choose a model">
        <h1 style={headingStyle}>Choose a model</h1>
        <p style={subheadingStyle}>
          The cockpit renders cached activations from the selected model.
          During alpha only Pythia-160M is wired end-to-end.
        </p>

        <div style={listStyle} role="radiogroup" aria-label="Available models">
          {MODELS.map((model) => {
            const active = selected === model.id;
            return (
              <div
                key={model.id}
                role="radio"
                aria-checked={active}
                aria-disabled={!model.available}
                tabIndex={model.available ? 0 : -1}
                onClick={() => {
                  if (model.available) setSelected(model.id);
                }}
                onKeyDown={(event) => {
                  if (!model.available) return;
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    setSelected(model.id);
                  }
                }}
                style={rowStyle(active, model.available)}
                data-testid={`model-row-${model.id}`}
              >
                <div>
                  <div style={rowTitleStyle}>
                    <span>{model.family}</span>
                    <span style={rowMetaStyle}>
                      {model.size}
                      {model.layers > 0 ? ` · ${model.layers} layers` : ''}
                    </span>
                  </div>
                  <div style={rowNotesStyle}>{model.notes}</div>
                </div>
                <span style={tagStyle(model.available ? 'live' : 'soon')}>
                  {model.available ? 'Live' : 'Soon'}
                </span>
              </div>
            );
          })}
        </div>

        <motion.button
          type="button"
          style={buttonStyle}
          whileHover={{
            background: 'rgba(45, 212, 191, 0.16)',
            borderColor: '#5eead4',
          }}
          whileTap={{ scale: 0.99 }}
          transition={SPRING_SNAPPY}
          onClick={() => navigate(`/audit-console?model=${encodeURIComponent(selected)}`)}
          data-testid="continue-to-audit"
        >
          Choose model for CAS audit
        </motion.button>

        <p style={footnoteStyle}>
          External model attachment (BYO weights, BYO endpoints) is roadmap
          item #6. The Architecture Mapper (item #7) selects probe targets
          inside an attached model.
        </p>
      </GlassPanel>
    </PageShell>
  );
}

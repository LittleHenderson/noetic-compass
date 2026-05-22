import { useState, type CSSProperties } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { GlassPanel } from '../components/ui/GlassPanel';
import { PageShell } from '../components/ui/PageShell';
import {
  ACCENT_BLUE,
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
  fontSize: 28,
  fontWeight: 600,
  letterSpacing: -0.3,
  color: COLORS.textPrimary,
};

const subheadingStyle: CSSProperties = {
  margin: '8px 0 22px 0',
  fontSize: 14,
  lineHeight: 1.5,
  color: COLORS.textSecondary,
};

const listStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
  marginBottom: 18,
};

const rowStyle = (active: boolean, available: boolean): CSSProperties => ({
  display: 'grid',
  gridTemplateColumns: '1fr auto',
  alignItems: 'center',
  gap: 12,
  padding: '14px 16px',
  borderRadius: 12,
  border: active
    ? '1px solid rgba(59, 130, 246, 0.55)'
    : '1px solid rgba(255, 255, 255, 0.06)',
  background: active
    ? 'rgba(59, 130, 246, 0.10)'
    : 'rgba(15, 23, 42, 0.45)',
  cursor: available ? 'pointer' : 'not-allowed',
  opacity: available ? 1 : 0.55,
});

const rowTitleStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'baseline',
  gap: 10,
  fontSize: 15,
  fontWeight: 600,
  color: COLORS.textPrimary,
};

const rowMetaStyle: CSSProperties = {
  fontSize: 12,
  color: COLORS.textMuted,
};

const rowNotesStyle: CSSProperties = {
  marginTop: 4,
  fontSize: 12.5,
  lineHeight: 1.5,
  color: COLORS.textSecondary,
};

const tagStyle = (kind: 'live' | 'soon'): CSSProperties => ({
  fontSize: 11,
  fontWeight: 600,
  letterSpacing: 0.5,
  textTransform: 'uppercase',
  padding: '4px 8px',
  borderRadius: 8,
  background:
    kind === 'live' ? 'rgba(34, 197, 94, 0.16)' : 'rgba(148, 163, 184, 0.12)',
  border:
    kind === 'live'
      ? '1px solid rgba(34, 197, 94, 0.45)'
      : '1px solid rgba(148, 163, 184, 0.25)',
  color: kind === 'live' ? '#bbf7d0' : COLORS.textSecondary,
});

const buttonStyle: CSSProperties = {
  width: '100%',
  marginTop: 8,
  padding: '12px 18px',
  borderRadius: 12,
  border: '1px solid rgba(59, 130, 246, 0.55)',
  background: `linear-gradient(135deg, ${ACCENT_BLUE} 0%, #1d4ed8 100%)`,
  color: '#f8fafc',
  fontSize: 15,
  fontWeight: 600,
  fontFamily: THEME.fontFamily,
  cursor: 'pointer',
  boxShadow: '0 6px 20px rgba(59, 130, 246, 0.35)',
};

const footnoteStyle: CSSProperties = {
  marginTop: 18,
  paddingTop: 16,
  borderTop: '1px solid rgba(255, 255, 255, 0.06)',
  fontSize: 12,
  lineHeight: 1.6,
  color: COLORS.textMuted,
};

export default function ModelConfigPage() {
  const navigate = useNavigate();
  const [selected, setSelected] = useState<string>('pythia-160m');

  return (
    <PageShell cardMaxWidth={540}>
      <GlassPanel intensity="regular" padding={28} ariaLabel="Choose a model">
        <h1 style={headingStyle}>Choose a model</h1>
        <p style={subheadingStyle}>
          The cockpit renders cached activations from the selected model.
          During alpha only Pythia-160M is wired end-to-end.
        </p>

        <div style={listStyle} role="radiogroup" aria-label="Available models">
          {MODELS.map((model) => {
            const active = selected === model.id;
            return (
              <motion.div
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
                whileHover={model.available ? { scale: 1.01 } : undefined}
                whileTap={model.available ? { scale: 0.99 } : undefined}
                transition={SPRING_SNAPPY}
                data-testid={`model-row-${model.id}`}
              >
                <div>
                  <div style={rowTitleStyle}>
                    <span>
                      {model.family}{' '}
                      <span style={rowMetaStyle}>
                        · {model.size}
                        {model.layers > 0 ? ` · ${model.layers} layers` : ''}
                      </span>
                    </span>
                  </div>
                  <div style={rowNotesStyle}>{model.notes}</div>
                </div>
                <span style={tagStyle(model.available ? 'live' : 'soon')}>
                  {model.available ? 'Live' : 'Soon'}
                </span>
              </motion.div>
            );
          })}
        </div>

        <motion.button
          type="button"
          style={buttonStyle}
          whileHover={{ scale: 1.02, y: -1 }}
          whileTap={{ scale: 0.98 }}
          transition={SPRING_SNAPPY}
          onClick={() => navigate('/cockpit')}
          data-testid="enter-cockpit"
        >
          Enter cockpit
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

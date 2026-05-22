import { useState, type CSSProperties, type FormEvent } from 'react';
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

const headingStyle: CSSProperties = {
  margin: 0,
  fontSize: 28,
  fontWeight: 600,
  letterSpacing: -0.3,
  color: COLORS.textPrimary,
};

const subheadingStyle: CSSProperties = {
  margin: '8px 0 24px 0',
  fontSize: 14,
  lineHeight: 1.5,
  color: COLORS.textSecondary,
};

const fieldGroupStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
  marginBottom: 14,
};

const labelStyle: CSSProperties = {
  fontSize: 12,
  fontWeight: 500,
  letterSpacing: 0.4,
  textTransform: 'uppercase',
  color: COLORS.textMuted,
};

const inputStyle: CSSProperties = {
  width: '100%',
  padding: '12px 14px',
  borderRadius: 10,
  border: '1px solid rgba(255, 255, 255, 0.08)',
  background: 'rgba(2, 6, 23, 0.55)',
  color: COLORS.textPrimary,
  fontSize: 15,
  fontFamily: THEME.fontFamily,
  letterSpacing: 0.4,
  outline: 'none',
};

const buttonRowStyle: CSSProperties = {
  display: 'flex',
  gap: 10,
  marginTop: 6,
};

const primaryButtonStyle: CSSProperties = {
  flex: 1,
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

const ghostButtonStyle: CSSProperties = {
  flex: 1,
  padding: '12px 18px',
  borderRadius: 12,
  border: '1px solid rgba(255, 255, 255, 0.12)',
  background: 'rgba(15, 23, 42, 0.45)',
  color: COLORS.textPrimary,
  fontSize: 15,
  fontWeight: 500,
  fontFamily: THEME.fontFamily,
  cursor: 'pointer',
};

const statusStyle = (kind: 'idle' | 'ok' | 'warn'): CSSProperties => ({
  marginTop: 18,
  padding: '10px 12px',
  borderRadius: 10,
  fontSize: 13,
  lineHeight: 1.5,
  background:
    kind === 'ok'
      ? 'rgba(34, 197, 94, 0.12)'
      : kind === 'warn'
      ? 'rgba(234, 179, 8, 0.12)'
      : 'rgba(148, 163, 184, 0.08)',
  border:
    kind === 'ok'
      ? '1px solid rgba(34, 197, 94, 0.35)'
      : kind === 'warn'
      ? '1px solid rgba(234, 179, 8, 0.35)'
      : '1px solid rgba(148, 163, 184, 0.18)',
  color:
    kind === 'ok'
      ? '#bbf7d0'
      : kind === 'warn'
      ? '#fde68a'
      : COLORS.textSecondary,
});

const footnoteStyle: CSSProperties = {
  marginTop: 22,
  paddingTop: 18,
  borderTop: '1px solid rgba(255, 255, 255, 0.06)',
  fontSize: 12,
  lineHeight: 1.6,
  color: COLORS.textMuted,
};

export default function LicensePage() {
  const navigate = useNavigate();
  const [key, setKey] = useState('');
  const [status, setStatus] = useState<'idle' | 'ok' | 'warn'>('idle');

  const handleValidate = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setStatus(key.trim().length > 0 ? 'ok' : 'warn');
  };

  return (
    <PageShell>
      <GlassPanel intensity="regular" padding={28} ariaLabel="License key">
        <h1 style={headingStyle}>License key</h1>
        <p style={subheadingStyle}>
          Paste the alpha license key from your invite email. During alpha the
          key is accepted on shape only — full validation against the licensing
          backend lands with roadmap item #11.
        </p>

        <form onSubmit={handleValidate}>
          <div style={fieldGroupStyle}>
            <label htmlFor="license-key" style={labelStyle}>
              License key
            </label>
            <input
              id="license-key"
              type="text"
              spellCheck={false}
              placeholder="atlas-alpha-•••• •••• •••• ••••"
              value={key}
              onChange={(event) => setKey(event.target.value)}
              style={inputStyle}
            />
          </div>

          <div style={buttonRowStyle}>
            <motion.button
              type="submit"
              style={primaryButtonStyle}
              whileHover={{ scale: 1.02, y: -1 }}
              whileTap={{ scale: 0.98 }}
              transition={SPRING_SNAPPY}
            >
              Validate
            </motion.button>
            <motion.button
              type="button"
              style={ghostButtonStyle}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              transition={SPRING_SNAPPY}
              onClick={() => navigate('/model-config')}
            >
              Continue
            </motion.button>
          </div>
        </form>

        {status !== 'idle' ? (
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={SPRING_SNAPPY}
            style={statusStyle(status)}
            role="status"
          >
            {status === 'ok'
              ? 'License accepted (alpha shape-check). Continue to model selection.'
              : 'Enter a license key, or press Continue to proceed without one.'}
          </motion.div>
        ) : null}

        <p style={footnoteStyle}>
          Alpha v0 — no key is required to reach the cockpit. Full license
          enforcement, expiry, and seat counting are part of the licensing
          rollout (item #11).
        </p>
      </GlassPanel>
    </PageShell>
  );
}

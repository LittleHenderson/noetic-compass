import { useState, type CSSProperties, type FormEvent } from 'react';
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

const headingStyle: CSSProperties = {
  margin: 0,
  fontSize: 24,
  fontWeight: 700,
  letterSpacing: -0.3,
  color: COLORS.textPrimary,
};

const subheadingStyle: CSSProperties = {
  margin: '8px 0 22px 0',
  fontSize: 13.5,
  lineHeight: 1.55,
  color: COLORS.textSecondary,
};

const fieldGroupStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
  marginBottom: 12,
};

const labelStyle: CSSProperties = {
  fontSize: 10.5,
  fontWeight: 600,
  letterSpacing: 1,
  textTransform: 'uppercase',
  color: COLORS.textMuted,
};

const inputStyle: CSSProperties = {
  width: '100%',
  padding: '10px 12px',
  borderRadius: 6,
  border: '1px solid rgba(255, 255, 255, 0.08)',
  background: 'rgba(255, 255, 255, 0.02)',
  color: COLORS.textPrimary,
  fontSize: 14,
  fontFamily: THEME.fontMono,
  letterSpacing: 0.3,
  outline: 'none',
};

const buttonRowStyle: CSSProperties = {
  display: 'flex',
  gap: 8,
  marginTop: 8,
};

const primaryButtonStyle: CSSProperties = {
  flex: 1,
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

const ghostButtonStyle: CSSProperties = {
  flex: 1,
  padding: '10px 16px',
  borderRadius: 6,
  border: '1px solid rgba(255, 255, 255, 0.08)',
  background: 'rgba(255, 255, 255, 0.02)',
  color: COLORS.textSecondary,
  fontSize: 13,
  fontWeight: 500,
  fontFamily: THEME.fontFamily,
  cursor: 'pointer',
};

const statusStyle = (kind: 'idle' | 'ok' | 'warn'): CSSProperties => ({
  marginTop: 14,
  padding: '10px 12px',
  borderRadius: 6,
  fontSize: 12.5,
  lineHeight: 1.5,
  background:
    kind === 'ok'
      ? 'rgba(34, 197, 94, 0.06)'
      : kind === 'warn'
      ? 'rgba(234, 179, 8, 0.06)'
      : 'rgba(148, 163, 184, 0.04)',
  border:
    kind === 'ok'
      ? '1px solid rgba(34, 197, 94, 0.25)'
      : kind === 'warn'
      ? '1px solid rgba(234, 179, 8, 0.25)'
      : '1px solid rgba(148, 163, 184, 0.12)',
  color:
    kind === 'ok'
      ? '#86efac'
      : kind === 'warn'
      ? '#fde68a'
      : COLORS.textSecondary,
});

const footnoteStyle: CSSProperties = {
  marginTop: 20,
  paddingTop: 16,
  borderTop: '1px solid rgba(255, 255, 255, 0.05)',
  fontSize: 11.5,
  lineHeight: 1.55,
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
      <GlassPanel intensity="regular" padding={24} ariaLabel="License key">
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
              whileHover={{
                background: 'rgba(45, 212, 191, 0.16)',
                borderColor: '#5eead4',
              }}
              whileTap={{ scale: 0.99 }}
              transition={SPRING_SNAPPY}
            >
              Validate
            </motion.button>
            <motion.button
              type="button"
              style={ghostButtonStyle}
              whileHover={{
                background: 'rgba(255, 255, 255, 0.06)',
                color: COLORS.textPrimary,
              }}
              whileTap={{ scale: 0.99 }}
              transition={SPRING_SNAPPY}
              onClick={() => navigate('/model-config')}
            >
              Continue
            </motion.button>
          </div>
        </form>

        {status !== 'idle' ? (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
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

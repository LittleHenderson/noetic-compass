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
  fontFamily: THEME.fontFamily,
  outline: 'none',
};

// Bordered ghost button matching the production noeticcompass nav style:
// transparent fill, 1 px hairline border, teal text + teal-tinted hover fill.
// No gradient, no glow, no drop shadow.
const buttonStyle: CSSProperties = {
  width: '100%',
  marginTop: 8,
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
  marginTop: 20,
  paddingTop: 16,
  borderTop: '1px solid rgba(255, 255, 255, 0.05)',
  fontSize: 11.5,
  lineHeight: 1.55,
  color: COLORS.textMuted,
};

export default function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    navigate('/license');
  };

  return (
    <PageShell>
      <GlassPanel intensity="regular" padding={24} ariaLabel="Sign in to Atlas Viewer">
        <h1 style={headingStyle}>Sign in</h1>
        <p style={subheadingStyle}>
          Private alpha preview. Access is by invitation only — your email and
          invite code are reviewed before we provision a license.
        </p>

        <form onSubmit={handleSubmit}>
          <div style={fieldGroupStyle}>
            <label htmlFor="login-email" style={labelStyle}>
              Email
            </label>
            <input
              id="login-email"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              style={inputStyle}
              required
            />
          </div>

          <div style={fieldGroupStyle}>
            <label htmlFor="login-code" style={labelStyle}>
              Invite code
            </label>
            <input
              id="login-code"
              type="text"
              autoComplete="one-time-code"
              placeholder="alpha-•••• ••••"
              value={code}
              onChange={(event) => setCode(event.target.value)}
              style={inputStyle}
              required
            />
          </div>

          <motion.button
            type="submit"
            style={buttonStyle}
            whileHover={{
              background: 'rgba(45, 212, 191, 0.16)',
              borderColor: '#5eead4',
            }}
            whileTap={{ scale: 0.99 }}
            transition={SPRING_SNAPPY}
          >
            Continue
          </motion.button>
        </form>

        <p style={footnoteStyle}>
          Alpha v0 — auth flow is not yet wired to the licensing backend.
          Continue advances to the license step without verification.
          Tracked as roadmap item #5.
        </p>
      </GlassPanel>
    </PageShell>
  );
}

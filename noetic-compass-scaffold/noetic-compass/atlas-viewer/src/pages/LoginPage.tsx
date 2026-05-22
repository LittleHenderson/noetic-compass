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
  outline: 'none',
};

const buttonStyle: CSSProperties = {
  width: '100%',
  marginTop: 6,
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
  marginTop: 22,
  paddingTop: 18,
  borderTop: '1px solid rgba(255, 255, 255, 0.06)',
  fontSize: 12,
  lineHeight: 1.6,
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
      <GlassPanel intensity="regular" padding={28} ariaLabel="Sign in to Atlas Viewer">
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
            whileHover={{ scale: 1.02, y: -1 }}
            whileTap={{ scale: 0.98 }}
            transition={SPRING_SNAPPY}
          >
            Continue
          </motion.button>
        </form>

        <p style={footnoteStyle}>
          Alpha v0 — auth flow is not yet wired to the licensing backend. Submit
          continues to the license step without verification. Real auth is
          tracked in the roadmap (item #5).
        </p>
      </GlassPanel>
    </PageShell>
  );
}

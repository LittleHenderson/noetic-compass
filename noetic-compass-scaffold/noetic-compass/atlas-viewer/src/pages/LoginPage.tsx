import { useEffect, useState, type CSSProperties, type FormEvent } from 'react';
import { motion } from 'framer-motion';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAccountAuth } from '../components/auth/AccountAuthProvider';
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
  letterSpacing: 0,
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

const statusStyle = (kind: 'error' | 'muted'): CSSProperties => ({
  marginTop: 14,
  padding: '10px 12px',
  borderRadius: 6,
  border:
    kind === 'error'
      ? '1px solid rgba(251, 113, 133, 0.35)'
      : '1px solid rgba(148, 163, 184, 0.14)',
  background:
    kind === 'error'
      ? 'rgba(251, 113, 133, 0.09)'
      : 'rgba(148, 163, 184, 0.05)',
  color: kind === 'error' ? '#ffe4e6' : COLORS.textSecondary,
  fontSize: 12.5,
  lineHeight: 1.5,
});

function redirectTarget(from: unknown): string {
  if (typeof from === 'string' && from.startsWith('/') && from !== '/login') {
    return from;
  }
  return '/license';
}

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { session, login } = useAccountAuth();
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const from = (location.state as { from?: unknown } | null)?.from;
  const nextPath = redirectTarget(from);

  useEffect(() => {
    if (session) navigate(nextPath, { replace: true });
  }, [navigate, nextPath, session]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      await login({
        email,
        inviteCode: code,
      });
      navigate(nextPath, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign in failed.');
    } finally {
      setPending(false);
    }
  };

  return (
    <PageShell>
      <GlassPanel intensity="regular" padding={24} ariaLabel="Sign in to Atlas Viewer">
        <h1 style={headingStyle}>Sign in</h1>
        <p style={subheadingStyle}>
          Sign in with the email on your invite. Add the invite code the first
          time you use this account.
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
              placeholder="atlas-alpha-..."
              value={code}
              onChange={(event) => setCode(event.target.value)}
              style={inputStyle}
            />
          </div>

          <motion.button
            type="submit"
            style={{
              ...buttonStyle,
              opacity: pending ? 0.65 : 1,
              cursor: pending ? 'not-allowed' : 'pointer',
            }}
            disabled={pending}
            whileHover={{
              background: 'rgba(45, 212, 191, 0.16)',
              borderColor: '#5eead4',
            }}
            whileTap={{ scale: 0.99 }}
            transition={SPRING_SNAPPY}
          >
            {pending ? 'Signing in' : 'Sign in'}
          </motion.button>
        </form>

        {error ? (
          <motion.div
            role="alert"
            style={statusStyle('error')}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={SPRING_SNAPPY}
          >
            {error}
          </motion.div>
        ) : (
          <p style={statusStyle('muted')}>
            Returning users can leave the invite code blank.
          </p>
        )}
      </GlassPanel>
    </PageShell>
  );
}

import { useState, type CSSProperties } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useAccountAuth } from '../components/auth/AccountAuthProvider';
import { GlassPanel } from '../components/ui/GlassPanel';
import { PageShell } from '../components/ui/PageShell';
import {
  ACCENT_TEAL,
  COLORS,
  FONT_MONO,
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

const detailGridStyle: CSSProperties = {
  display: 'grid',
  gap: 8,
  padding: 14,
  borderRadius: 8,
  border: '1px solid rgba(255, 255, 255, 0.08)',
  background: 'rgba(255, 255, 255, 0.03)',
};

const detailRowStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '92px minmax(0, 1fr)',
  gap: 10,
  alignItems: 'center',
  fontSize: 12.5,
};

const labelStyle: CSSProperties = {
  color: COLORS.textMuted,
  fontSize: 10.5,
  fontWeight: 700,
  letterSpacing: 0.7,
  textTransform: 'uppercase',
};

const valueStyle: CSSProperties = {
  color: COLORS.textPrimary,
  fontFamily: FONT_MONO,
  overflowWrap: 'anywhere',
};

const buttonRowStyle: CSSProperties = {
  display: 'flex',
  gap: 8,
  marginTop: 16,
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

const statusStyle: CSSProperties = {
  marginTop: 14,
  padding: '10px 12px',
  borderRadius: 6,
  fontSize: 12.5,
  lineHeight: 1.5,
  background: 'rgba(251, 113, 133, 0.09)',
  border: '1px solid rgba(251, 113, 133, 0.35)',
  color: '#ffe4e6',
};

export default function LicensePage() {
  const navigate = useNavigate();
  const { session, logout } = useAccountAuth();
  const [error, setError] = useState<string | null>(null);
  const [pendingLogout, setPendingLogout] = useState(false);

  const account = session?.account;
  const accountLabel = account?.email_or_username ?? session?.email ?? 'Account session';
  const tenantLabel = account?.tenant_id ?? 'tenant available after invite redemption';
  const roleLabel = account?.role ?? 'member';
  const expiresLabel = session?.expiresAt ?? 'current browser session';

  const handleLogout = async (): Promise<void> => {
    setError(null);
    setPendingLogout(true);
    try {
      await logout();
      navigate('/login', { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Logout failed.');
    } finally {
      setPendingLogout(false);
    }
  };

  return (
    <PageShell>
      <GlassPanel intensity="regular" padding={24} ariaLabel="Account session">
        <h1 style={headingStyle}>Account ready</h1>
        <p style={subheadingStyle}>
          Your account session is active for CAS Harness audit and evidence
          calls.
        </p>

        <div style={detailGridStyle}>
          <div style={detailRowStyle}>
            <span style={labelStyle}>Account</span>
            <span style={valueStyle}>{accountLabel}</span>
          </div>
          <div style={detailRowStyle}>
            <span style={labelStyle}>Tenant</span>
            <span style={valueStyle}>{tenantLabel}</span>
          </div>
          <div style={detailRowStyle}>
            <span style={labelStyle}>Role</span>
            <span style={valueStyle}>{roleLabel}</span>
          </div>
          <div style={detailRowStyle}>
            <span style={labelStyle}>Expires</span>
            <span style={valueStyle}>{expiresLabel}</span>
          </div>
        </div>

        <div style={buttonRowStyle}>
          <motion.button
            type="button"
            style={primaryButtonStyle}
            whileHover={{
              background: 'rgba(45, 212, 191, 0.16)',
              borderColor: '#5eead4',
            }}
            whileTap={{ scale: 0.99 }}
            transition={SPRING_SNAPPY}
            onClick={() => navigate('/audit-console')}
          >
            Continue
          </motion.button>
          <motion.button
            type="button"
            style={{
              ...ghostButtonStyle,
              opacity: pendingLogout ? 0.65 : 1,
              cursor: pendingLogout ? 'not-allowed' : 'pointer',
            }}
            disabled={pendingLogout}
            whileHover={{
              background: 'rgba(255, 255, 255, 0.06)',
              color: COLORS.textPrimary,
            }}
            whileTap={{ scale: 0.99 }}
            transition={SPRING_SNAPPY}
            onClick={() => {
              void handleLogout();
            }}
          >
            {pendingLogout ? 'Signing out' : 'Sign out'}
          </motion.button>
        </div>

        {error ? (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={SPRING_SNAPPY}
            style={statusStyle}
            role="alert"
          >
            {error}
          </motion.div>
        ) : null}
      </GlassPanel>
    </PageShell>
  );
}

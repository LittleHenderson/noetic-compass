import { lazy, Suspense, type CSSProperties } from 'react';
import type { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { Navigate, Route, Routes } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import AccountSecurityPage from './pages/AccountSecurityPage';
import ModelConfigPage from './pages/ModelConfigPage';
import AuditConsolePage from './pages/AuditConsolePage';
import { AccountAuthProvider, useAccountAuth } from './auth/AccountAuthProvider';
import { AuthGate } from './components/auth/AuthGate';
import { GlassPanel } from './components/ui/GlassPanel';
import { ACCENT_BLUE, COLORS, THEME } from './lib/designTokens';

// CockpitPage pulls in Three.js + framer-motion (~640 KB). Lazy-load it so the
// initial bundle stays small for the eager account / model-selection routes.
const CockpitPage = lazy(() => import('./pages/CockpitPage'));

function LandingRedirect() {
  const { accountsEnabled, isAuthenticated } = useAccountAuth();
  return <Navigate to={!accountsEnabled || isAuthenticated ? '/model-config' : '/login'} replace />;
}

function AccountLoginRoute() {
  const { accountsEnabled } = useAccountAuth();
  return accountsEnabled ? <LoginPage /> : <Navigate to="/model-config" replace />;
}

function AccountModeRoute({ children }: { children: ReactNode }) {
  const { accountsEnabled } = useAccountAuth();
  if (!accountsEnabled) return <Navigate to="/model-config" replace />;
  return <AuthGate>{children}</AuthGate>;
}

function LegacyLicenseRedirect() {
  const { accountsEnabled } = useAccountAuth();
  return <Navigate to={accountsEnabled ? '/account-security' : '/model-config'} replace />;
}

const fallbackBackdropStyle: CSSProperties = {
  position: 'fixed',
  inset: 0,
  background:
    'radial-gradient(ellipse at top, #0a1124 0%, #02030a 60%, #000000 100%)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontFamily: THEME.fontFamily,
  color: COLORS.textPrimary,
};

const fallbackInnerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 14,
  fontSize: 14,
  letterSpacing: 0.3,
  color: COLORS.textSecondary,
};

const fallbackDotStyle: CSSProperties = {
  width: 10,
  height: 10,
  borderRadius: '50%',
  background: ACCENT_BLUE,
  boxShadow: `0 0 16px ${ACCENT_BLUE}`,
};

function CockpitSuspenseFallback() {
  return (
    <div style={fallbackBackdropStyle} role="status" aria-live="polite">
      <GlassPanel intensity="thin" padding="14px 22px" ariaLabel="Loading cockpit">
        <div style={fallbackInnerStyle}>
          <motion.span
            style={fallbackDotStyle}
            animate={{ opacity: [0.4, 1, 0.4], scale: [1, 1.15, 1] }}
            transition={{ duration: 1.4, repeat: Infinity, ease: 'easeInOut' }}
          />
          <span>Warming up the cockpit…</span>
        </div>
      </GlassPanel>
    </div>
  );
}

export default function App() {
  return (
    <AccountAuthProvider>
      <Routes>
        <Route path="/" element={<LandingRedirect />} />
        <Route path="/login" element={<AccountLoginRoute />} />
        <Route path="/license" element={<LegacyLicenseRedirect />} />
        <Route
          path="/account-security"
          element={
            <AccountModeRoute>
              <AccountSecurityPage />
            </AccountModeRoute>
          }
        />
        <Route
          path="/model-config"
          element={
            <AuthGate>
              <ModelConfigPage />
            </AuthGate>
          }
        />
        <Route
          path="/audit-console"
          element={
            <AuthGate>
              <AuditConsolePage />
            </AuthGate>
          }
        />
        <Route
          path="/cockpit"
          element={
            <AuthGate>
              <Suspense fallback={<CockpitSuspenseFallback />}>
                <CockpitPage />
              </Suspense>
            </AuthGate>
          }
        />
        <Route path="*" element={<LandingRedirect />} />
      </Routes>
    </AccountAuthProvider>
  );
}

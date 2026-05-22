import type { CSSProperties, ReactNode } from 'react';
import { motion } from 'framer-motion';
import { Link, useLocation } from 'react-router-dom';
import { GlassPanel } from './GlassPanel';
import { SPRING_GENTLE, SPRING_SNAPPY, THEME } from '../../lib/designTokens';

export interface PageShellProps {
  children: ReactNode;
  showNav?: boolean;
  cardMaxWidth?: number;
}

const STEPS: Array<{ to: string; label: string }> = [
  { to: '/login', label: 'Sign in' },
  { to: '/license', label: 'License' },
  { to: '/model-config', label: 'Model' },
  { to: '/cockpit', label: 'Cockpit' },
];

const backdropStyle: CSSProperties = {
  position: 'fixed',
  inset: 0,
  background:
    'radial-gradient(ellipse at top, #0a1124 0%, #02030a 60%, #000000 100%)',
  overflow: 'hidden',
};

const ambientBlobStyle = (top: string, left: string, color: string): CSSProperties => ({
  position: 'absolute',
  top,
  left,
  width: 480,
  height: 480,
  borderRadius: '50%',
  background: `radial-gradient(circle, ${color} 0%, transparent 65%)`,
  filter: 'blur(60px)',
  opacity: 0.45,
  pointerEvents: 'none',
});

const navWrapperStyle: CSSProperties = {
  position: 'relative',
  zIndex: 10,
  display: 'flex',
  justifyContent: 'center',
  paddingTop: 18,
  paddingBottom: 4,
};

const navInnerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 4,
  padding: 6,
  fontSize: 13,
  fontFamily: THEME.fontFamily,
};

const navStepStyle = (active: boolean): CSSProperties => ({
  position: 'relative',
  padding: '6px 12px',
  borderRadius: 10,
  color: active ? '#ffffff' : THEME.colors.textSecondary,
  fontWeight: active ? 600 : 500,
  textDecoration: 'none',
  cursor: 'pointer',
  zIndex: 2,
});

const mainStyle: CSSProperties = {
  position: 'relative',
  zIndex: 1,
  minHeight: '100vh',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '24px 24px 64px 24px',
  fontFamily: THEME.fontFamily,
  color: THEME.colors.textPrimary,
};

const wordmarkStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'baseline',
  gap: 8,
  marginBottom: 28,
  fontSize: 13,
  letterSpacing: 1.4,
  textTransform: 'uppercase',
  color: THEME.colors.textSecondary,
};

const wordmarkDotStyle: CSSProperties = {
  width: 8,
  height: 8,
  borderRadius: '50%',
  background: THEME.ACCENT_BLUE,
  boxShadow: `0 0 14px ${THEME.ACCENT_BLUE}`,
};

export function PageShell({
  children,
  showNav = true,
  cardMaxWidth = 460,
}: PageShellProps) {
  const location = useLocation();

  const cardStyle: CSSProperties = {
    width: '100%',
    maxWidth: cardMaxWidth,
  };

  return (
    <div style={backdropStyle}>
      <div style={ambientBlobStyle('-160px', '-120px', 'rgba(59, 130, 246, 0.35)')} />
      <div style={ambientBlobStyle('60%', '70%', 'rgba(168, 85, 247, 0.28)')} />

      {showNav ? (
        <nav style={navWrapperStyle}>
          <GlassPanel intensity="thin" padding={4} as="nav" ariaLabel="Atlas Viewer flow">
            <div style={navInnerStyle}>
              {STEPS.map((step) => {
                const active = location.pathname.startsWith(step.to);
                return (
                  <Link
                    key={step.to}
                    to={step.to}
                    style={navStepStyle(active)}
                    aria-current={active ? 'page' : undefined}
                    data-testid={`nav-step-${step.to.slice(1)}`}
                  >
                    {active ? (
                      <motion.span
                        layoutId="nav-active-pill"
                        style={{
                          position: 'absolute',
                          inset: 0,
                          background: 'rgba(59, 130, 246, 0.18)',
                          border: '1px solid rgba(59, 130, 246, 0.35)',
                          borderRadius: 10,
                          zIndex: -1,
                        }}
                        transition={SPRING_SNAPPY}
                      />
                    ) : null}
                    {step.label}
                  </Link>
                );
              })}
            </div>
          </GlassPanel>
        </nav>
      ) : null}

      <main style={mainStyle}>
        <div style={wordmarkStyle}>
          <span style={wordmarkDotStyle} />
          <span>Atlas Viewer · Alpha</span>
        </div>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={SPRING_GENTLE}
          style={cardStyle}
        >
          {children}
        </motion.div>
      </main>
    </div>
  );
}

export default PageShell;

import type { CSSProperties, ReactNode } from 'react';
import { motion } from 'framer-motion';
import { Link, useLocation } from 'react-router-dom';
import { ACCENT_TEAL, ACCENT_CYAN, COLORS, SPRING_GENTLE, SPRING_SNAPPY, THEME } from '../../lib/designTokens';

export interface PageShellProps {
  children: ReactNode;
  showNav?: boolean;
  cardMaxWidth?: number;
}

const STEPS: Array<{ to: string; label: string }> = [
  { to: '/login', label: 'Sign in' },
  { to: '/license', label: 'License' },
  { to: '/model-config', label: 'Model' },
  { to: '/audit-console', label: 'Audit' },
  { to: '/cockpit', label: 'Cockpit' },
];

// Wave 5.2: dropped the big purple/blue ambient blobs. Replaced with a tight
// slate-950 base + a single subtle radial darkening from bottom. No
// chromatic sky, no glow halo — production tools don't decorate the backdrop.
const backdropStyle: CSSProperties = {
  position: 'fixed',
  inset: 0,
  background:
    'radial-gradient(ellipse at 50% 110%, rgba(15, 23, 42, 0.9) 0%, #020617 60%, #000000 100%)',
  overflowX: 'hidden',
  overflowY: 'auto',
};

// A faint grid graticule behind everything — gives the page a HUD-like
// foundation without competing with the content. Uses inline SVG via
// data URI so there's no extra HTTP request.
const gridOverlayStyle: CSSProperties = {
  position: 'absolute',
  inset: 0,
  pointerEvents: 'none',
  opacity: 0.35,
  backgroundImage:
    "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='40' height='40' viewBox='0 0 40 40'><path d='M40 0H0V40' fill='none' stroke='rgba(148,163,184,0.06)' stroke-width='1'/></svg>\")",
  backgroundSize: '40px 40px',
};

const navWrapperStyle: CSSProperties = {
  position: 'relative',
  zIndex: 10,
  display: 'flex',
  justifyContent: 'center',
  paddingTop: 22,
  paddingBottom: 4,
};

const navInnerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 2,
  padding: 4,
  fontSize: 12,
  letterSpacing: 0.3,
  fontFamily: THEME.fontFamily,
};

const navStepStyle = (active: boolean): CSSProperties => ({
  position: 'relative',
  padding: '6px 12px',
  borderRadius: 6,
  color: active ? ACCENT_TEAL : COLORS.textSecondary,
  fontWeight: active ? 600 : 500,
  textDecoration: 'none',
  cursor: 'pointer',
  zIndex: 2,
  transition: 'color 0.15s ease',
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
  color: COLORS.textPrimary,
};

const wordmarkStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'baseline',
  gap: 8,
  marginBottom: 28,
  fontSize: 11,
  letterSpacing: 2.2,
  textTransform: 'uppercase',
  color: COLORS.textMuted,
  fontWeight: 500,
};

const wordmarkAccentStyle: CSSProperties = {
  background: `linear-gradient(90deg, ${ACCENT_TEAL} 0%, ${ACCENT_CYAN} 100%)`,
  WebkitBackgroundClip: 'text',
  backgroundClip: 'text',
  color: 'transparent',
  fontWeight: 700,
  letterSpacing: 2.5,
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
      <div style={gridOverlayStyle} aria-hidden="true" />

      {showNav ? (
        <nav style={navWrapperStyle}>
          <div
            style={{
              ...navInnerStyle,
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid rgba(255, 255, 255, 0.06)',
              borderRadius: 8,
              backdropFilter: 'blur(14px) saturate(120%)',
              WebkitBackdropFilter: 'blur(14px) saturate(120%)',
            }}
            role="navigation"
            aria-label="Atlas Viewer flow"
          >
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
                        background: 'rgba(45, 212, 191, 0.10)',
                        border: '1px solid rgba(45, 212, 191, 0.30)',
                        borderRadius: 6,
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
        </nav>
      ) : null}

      <main style={mainStyle}>
        <div style={wordmarkStyle}>
          <span style={wordmarkAccentStyle}>Atlas Viewer</span>
          <span>·</span>
          <span>Alpha</span>
        </div>
        <motion.div
          initial={{ opacity: 0, y: 12 }}
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

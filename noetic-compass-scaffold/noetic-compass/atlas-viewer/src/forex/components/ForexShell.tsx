// CAS Forex surface shell — backdrop, wordmark, and the forex route nav.
// Mirrors the atlas-viewer PageShell aesthetic (slate-950 base, HUD grid,
// glass nav pill) but carries its own route map. Only /forex/proof is wired in
// Phase 1; the remaining routes render as honest "soon" markers, not dead links.

import type { CSSProperties, ReactNode } from 'react';
import { motion } from 'framer-motion';
import { Link, useLocation } from 'react-router-dom';
import {
  ACCENT_TEAL,
  ACCENT_CYAN,
  COLORS,
  SPRING_GENTLE,
  SPRING_SNAPPY,
  THEME,
} from '../../lib/designTokens';

interface NavItem {
  to: string;
  label: string;
  ready: boolean;
}

const NAV: NavItem[] = [
  { to: '/forex/proof', label: 'Proof', ready: true },
  { to: '/forex/dashboard', label: 'Dashboard', ready: false },
  { to: '/forex/audit', label: 'Audit', ready: true },
  { to: '/forex/trade', label: 'Paper Desk', ready: false },
  { to: '/forex/history', label: 'History', ready: false },
  { to: '/forex/settings', label: 'Settings', ready: false },
];

const backdropStyle: CSSProperties = {
  position: 'fixed',
  inset: 0,
  background:
    'radial-gradient(ellipse at 50% 110%, rgba(15, 23, 42, 0.9) 0%, #020617 60%, #000000 100%)',
  overflowX: 'hidden',
  overflowY: 'auto',
};

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
  paddingTop: 20,
};

const navInnerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  flexWrap: 'wrap',
  gap: 2,
  padding: 4,
  fontSize: 12,
  letterSpacing: 0.3,
  fontFamily: THEME.fontFamily,
  background: 'rgba(255, 255, 255, 0.03)',
  border: '1px solid rgba(255, 255, 255, 0.06)',
  borderRadius: 8,
  backdropFilter: 'blur(14px) saturate(120%)',
  WebkitBackdropFilter: 'blur(14px) saturate(120%)',
};

const navStepStyle = (active: boolean, ready: boolean): CSSProperties => ({
  position: 'relative',
  padding: '6px 12px',
  borderRadius: 6,
  color: active ? ACCENT_TEAL : ready ? COLORS.textSecondary : COLORS.textFaint,
  fontWeight: active ? 600 : 500,
  textDecoration: 'none',
  cursor: ready ? 'pointer' : 'default',
  zIndex: 2,
  transition: 'color 0.15s ease',
});

const soonTagStyle: CSSProperties = {
  marginLeft: 5,
  fontSize: 8.5,
  letterSpacing: 0.6,
  textTransform: 'uppercase',
  color: COLORS.textFaint,
  border: `1px solid ${COLORS.borderSubtle}`,
  borderRadius: 4,
  padding: '1px 3px',
  verticalAlign: 'middle',
};

const mainStyle: CSSProperties = {
  position: 'relative',
  zIndex: 1,
  minHeight: '100vh',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  padding: '20px 20px 64px 20px',
  fontFamily: THEME.fontFamily,
  color: COLORS.textPrimary,
};

const wordmarkStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'baseline',
  gap: 8,
  margin: '20px 0 16px',
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

export interface ForexShellProps {
  children: ReactNode;
  contentMaxWidth?: number;
}

export function ForexShell({ children, contentMaxWidth = 920 }: ForexShellProps) {
  const location = useLocation();

  return (
    <div style={backdropStyle}>
      <div style={gridOverlayStyle} aria-hidden="true" />

      <nav style={navWrapperStyle}>
        <div style={navInnerStyle} role="navigation" aria-label="CAS Forex sections">
          {NAV.map((item) => {
            const active = location.pathname.startsWith(item.to);
            if (!item.ready) {
              return (
                <span
                  key={item.to}
                  style={navStepStyle(false, false)}
                  aria-disabled="true"
                  title="Planned — not built in this phase."
                  data-testid={`forex-nav-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
                >
                  {item.label}
                  <span style={soonTagStyle}>soon</span>
                </span>
              );
            }
            return (
              <Link
                key={item.to}
                to={item.to}
                style={navStepStyle(active, true)}
                aria-current={active ? 'page' : undefined}
                data-testid={`forex-nav-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
              >
                {active ? (
                  <motion.span
                    layoutId="forex-nav-active-pill"
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
                {item.label}
              </Link>
            );
          })}
        </div>
      </nav>

      <main style={mainStyle}>
        <div style={wordmarkStyle}>
          <span style={wordmarkAccentStyle}>CAS Forex</span>
          <span>·</span>
          <span>Proof Cockpit</span>
        </div>
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={SPRING_GENTLE}
          style={{ width: '100%', maxWidth: contentMaxWidth }}
        >
          {children}
        </motion.div>
      </main>
    </div>
  );
}

export default ForexShell;

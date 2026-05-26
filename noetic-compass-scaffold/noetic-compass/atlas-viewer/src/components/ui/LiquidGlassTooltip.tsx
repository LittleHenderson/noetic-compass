import { useId, useState, type CSSProperties, type ReactNode } from 'react';
import { AnimatePresence, motion } from 'framer-motion';

import {
  ACCENT_CYAN,
  ACCENT_TEAL,
  COLORS,
  FONT_FAMILY,
} from '../../lib/designTokens';

export type LiquidGlassTooltipPlacement = 'top' | 'bottom' | 'right';

export interface LiquidGlassTooltipProps {
  briefing: string;
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
  placement?: LiquidGlassTooltipPlacement;
  block?: boolean;
  width?: number;
  ariaLabel?: string;
  focusable?: boolean;
}

const triggerStyle = (block: boolean): CSSProperties => ({
  position: 'relative',
  display: block ? 'block' : 'inline-flex',
  width: block ? '100%' : undefined,
  outline: 'none',
});

const popoverBaseStyle: CSSProperties = {
  position: 'absolute',
  zIndex: 90,
  width: 'min(var(--liquid-tooltip-width, 300px), calc(100vw - 48px))',
  padding: '13px 14px',
  borderRadius: 14,
  border: '1px solid rgba(255, 255, 255, 0.22)',
  background:
    'linear-gradient(145deg, rgba(15, 23, 42, 0.78), rgba(8, 13, 27, 0.60))',
  boxShadow:
    '0 24px 80px rgba(0, 0, 0, 0.42), inset 0 1px 0 rgba(255, 255, 255, 0.16), 0 0 0 1px rgba(45, 212, 191, 0.12)',
  backdropFilter: 'blur(24px) saturate(1.35)',
  WebkitBackdropFilter: 'blur(24px) saturate(1.35)',
  color: COLORS.textPrimary,
  fontFamily: FONT_FAMILY,
  pointerEvents: 'none',
};

const placementStyle: Record<LiquidGlassTooltipPlacement, CSSProperties> = {
  top: {
    left: 0,
    bottom: 'calc(100% + 10px)',
  },
  bottom: {
    left: 0,
    top: 'calc(100% + 10px)',
  },
  right: {
    left: 'calc(100% + 10px)',
    top: 0,
  },
};

const eyebrowStyle: CSSProperties = {
  display: 'block',
  marginBottom: 6,
  color: ACCENT_CYAN,
  fontSize: 10,
  fontWeight: 900,
  letterSpacing: 0.9,
  textTransform: 'uppercase',
};

const bodyStyle: CSSProperties = {
  display: 'block',
  color: '#e5f9f7',
  fontSize: 13,
  lineHeight: 1.45,
  fontWeight: 650,
  letterSpacing: 0,
};

const glowStyle: CSSProperties = {
  position: 'absolute',
  inset: 1,
  borderRadius: 13,
  background: `radial-gradient(circle at 15% 0%, ${ACCENT_TEAL}33, transparent 42%)`,
  pointerEvents: 'none',
};

export function LiquidGlassTooltip({
  briefing,
  children,
  className,
  style,
  placement = 'top',
  block = false,
  width = 300,
  ariaLabel,
  focusable = true,
}: LiquidGlassTooltipProps): JSX.Element {
  const [open, setOpen] = useState(false);
  const id = useId();
  const Trigger = block ? 'div' : 'span';

  const show = () => setOpen(true);
  const hide = () => setOpen(false);

  return (
    <Trigger
      aria-describedby={open ? id : undefined}
      aria-label={ariaLabel}
      className={className}
      onBlur={hide}
      onFocus={show}
      onMouseEnter={show}
      onMouseLeave={hide}
      onPointerEnter={show}
      onPointerLeave={hide}
      style={{ ...triggerStyle(block), ...style }}
      tabIndex={focusable ? 0 : undefined}
    >
      {children}
      <AnimatePresence>
        {open ? (
          <motion.span
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: placement === 'top' ? 4 : -4, scale: 0.985 }}
            id={id}
            initial={{ opacity: 0, y: placement === 'top' ? 4 : -4, scale: 0.985 }}
            role="tooltip"
            style={
              {
                ...popoverBaseStyle,
                ...placementStyle[placement],
                '--liquid-tooltip-width': `${width}px`,
              } as CSSProperties
            }
            transition={{ duration: 0.11, ease: [0.16, 1, 0.3, 1] }}
          >
            <span aria-hidden="true" style={glowStyle} />
            <span style={{ position: 'relative' }}>
              <span style={eyebrowStyle}>Briefing</span>
              <span style={bodyStyle}>{briefing}</span>
            </span>
          </motion.span>
        ) : null}
      </AnimatePresence>
    </Trigger>
  );
}

export default LiquidGlassTooltip;

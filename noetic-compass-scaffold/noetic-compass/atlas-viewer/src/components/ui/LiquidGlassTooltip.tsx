import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
  type SyntheticEvent,
} from 'react';
import { createPortal } from 'react-dom';
import { motion } from 'framer-motion';

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

// The popover is rendered through a PORTAL onto document.body with position:fixed.
// That is deliberate, and it is the fix for "the briefing pops up behind the next
// panel": an absolutely-positioned popover lives inside its trigger's stacking
// context and is clipped by any ancestor with overflow:hidden/auto (the scrollable
// rails/cards). A portal + fixed positioning escapes BOTH — every ancestor stacking
// context and every overflow clip — so zIndex finally means what it says. zIndex sits
// above the highest in-app surface (MethodologyDrawer overlay = 70) so a briefing is
// never obscured by a sibling panel again.
const POPOVER_Z = 1000;
const VIEWPORT_MARGIN = 8; // keep the popover this far from the viewport edge
const TRIGGER_GAP = 10; // gap between the trigger and the popover

const popoverBaseStyle: CSSProperties = {
  position: 'fixed',
  zIndex: POPOVER_Z,
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

// A popover is anchored by whichever edges are set: `left` OR `right` horizontally
// (right = flipped to the other side of the trigger), `top` OR `bottom` vertically.
interface PopoverCoords {
  left?: number;
  right?: number;
  top?: number;
  bottom?: number;
}

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
  const [coords, setCoords] = useState<PopoverCoords>({ left: 0 });
  // Captured from the hover/focus event's currentTarget (the trigger element) so the
  // popover can be positioned from, and stay glued to, the real on-screen trigger
  // without attaching a ref to the dynamic span/div tag.
  const triggerRef = useRef<HTMLElement | null>(null);
  const id = useId();
  const Trigger = block ? 'div' : 'span';

  const measure = useCallback(() => {
    const el = triggerRef.current;
    if (!el || typeof window === 'undefined') return;
    const rect = el.getBoundingClientRect();
    const vw = window.innerWidth;
    const w = Math.min(width, vw - 48);
    const clampLeft = (x: number) =>
      Math.max(VIEWPORT_MARGIN, Math.min(x, vw - w - VIEWPORT_MARGIN));

    if (placement === 'right') {
      // Sit immediately to the RIGHT of the trigger when there is room. If the trigger
      // is near the right edge (e.g. the Model-connection "?" lives in a right-side
      // card), the popover would otherwise be clamped clear across the screen and read
      // as "far away" — so FLIP it to the LEFT, anchored by its right edge, so it sits
      // adjacent on the other side of the trigger.
      const fitsRight = rect.right + TRIGGER_GAP + w <= vw - VIEWPORT_MARGIN;
      if (fitsRight) {
        setCoords({ left: rect.right + TRIGGER_GAP, top: rect.top });
      } else {
        setCoords({ right: vw - rect.left + TRIGGER_GAP, top: rect.top });
      }
    } else if (placement === 'bottom') {
      setCoords({ left: clampLeft(rect.left), top: rect.bottom + TRIGGER_GAP });
    } else {
      // 'top': anchor by the BOTTOM edge (distance from viewport bottom) so the
      // popover grows upward off the trigger without needing to know its own height.
      setCoords({
        left: clampLeft(rect.left),
        bottom: window.innerHeight - rect.top + TRIGGER_GAP,
      });
    }
  }, [placement, width]);

  const show = useCallback(
    (event: SyntheticEvent) => {
      triggerRef.current = event.currentTarget as HTMLElement;
      measure();
      setOpen(true);
    },
    [measure],
  );
  const hide = useCallback(() => setOpen(false), []);

  // While open, keep the fixed-position popover glued to the trigger if the page
  // scrolls or the window resizes (scroll uses capture so it catches scrolling on any
  // ancestor, not just the window).
  useEffect(() => {
    if (!open) return undefined;
    const reflow = () => measure();
    window.addEventListener('scroll', reflow, true);
    window.addEventListener('resize', reflow);
    return () => {
      window.removeEventListener('scroll', reflow, true);
      window.removeEventListener('resize', reflow);
    };
  }, [open, measure]);

  const popoverStyle = {
    ...popoverBaseStyle,
    ...(coords.left !== undefined ? { left: coords.left } : {}),
    ...(coords.right !== undefined ? { right: coords.right } : {}),
    ...(coords.top !== undefined ? { top: coords.top } : {}),
    ...(coords.bottom !== undefined ? { bottom: coords.bottom } : {}),
    '--liquid-tooltip-width': `${width}px`,
  } as CSSProperties;

  // Snappy by design: appears on hover with a ~70ms opacity fade (no slow-settling
  // scale/translate that reads as lag), and — because there is NO AnimatePresence
  // wrapper — it UNMOUNTS THE INSTANT the pointer leaves (no lingering exit animation).
  // Show feels immediate; hide is immediate.
  const popover =
    open && typeof document !== 'undefined'
      ? createPortal(
          <motion.span
            animate={{ opacity: 1 }}
            id={id}
            initial={{ opacity: 0 }}
            role="tooltip"
            style={popoverStyle}
            transition={{ duration: 0.07, ease: 'easeOut' }}
          >
            <span aria-hidden="true" style={glowStyle} />
            <span style={{ position: 'relative' }}>
              <span style={eyebrowStyle}>Briefing</span>
              <span style={bodyStyle}>{briefing}</span>
            </span>
          </motion.span>,
          document.body,
        )
      : null;

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
      {popover}
    </Trigger>
  );
}

export default LiquidGlassTooltip;

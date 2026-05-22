import {
  forwardRef,
  type CSSProperties,
  type HTMLAttributes,
  type ReactNode,
  type Ref,
} from 'react';
import { motion } from 'framer-motion';
import {
  GLASS_PANEL_FILL,
  GLASS_PANEL_BORDER,
  GLASS_PANEL_SHADOW,
  GLASS_RADIUS,
  SPRING_SNAPPY,
  type GlassIntensity,
  glassBlurFor,
} from '../../lib/designTokens';

type AsTag = 'div' | 'section' | 'aside' | 'nav';

// Forward arbitrary HTMLAttributes (role, tabIndex, aria-*, onKeyDown,
// data-testid, etc.) so consumers can treat GlassPanel as a polymorphic
// container without losing accessibility semantics. Wave 5 consumers
// (ControlBar, Mode7Timeline) rely on this contract. We omit handlers
// that conflict with framer-motion's typed equivalents (onDrag* receive
// PanInfo, onAnimation* receive AnimationEvent of a different shape).
export interface GlassPanelProps
  extends Omit<
    HTMLAttributes<HTMLElement>,
    | 'style'
    | 'onClick'
    | 'children'
    | 'aria-label'
    | 'onDrag'
    | 'onDragStart'
    | 'onDragEnd'
    | 'onAnimationStart'
    | 'onAnimationEnd'
    | 'onAnimationIteration'
  > {
  children: ReactNode;
  intensity?: GlassIntensity;
  padding?: number | string;
  interactive?: boolean;
  className?: string;
  style?: CSSProperties;
  as?: AsTag;
  onClick?: () => void;
  ariaLabel?: string;
}

function GlassPanelBase(
  {
    children,
    intensity = 'regular',
    padding = 16,
    interactive = false,
    className,
    style,
    as = 'div',
    onClick,
    ariaLabel,
    ...rest
  }: GlassPanelProps,
  ref: Ref<HTMLElement>,
) {
  const blur = glassBlurFor(intensity);

  const baseStyle: CSSProperties = {
    background: GLASS_PANEL_FILL,
    border: GLASS_PANEL_BORDER,
    boxShadow: GLASS_PANEL_SHADOW,
    borderRadius: GLASS_RADIUS,
    backdropFilter: blur,
    WebkitBackdropFilter: blur,
    padding,
    color: '#e2e8f0',
    cursor: interactive || onClick ? 'pointer' : undefined,
    ...style,
  };

  const MotionComponent = motion[as] as typeof motion.div;

  return (
    <MotionComponent
      ref={ref as Ref<HTMLDivElement>}
      className={className}
      style={baseStyle}
      onClick={onClick}
      aria-label={ariaLabel}
      whileHover={interactive ? { scale: 1.02 } : undefined}
      transition={SPRING_SNAPPY}
      data-intensity={intensity}
      data-interactive={interactive ? 'true' : 'false'}
      {...rest}
    >
      {children}
    </MotionComponent>
  );
}

export const GlassPanel = forwardRef(GlassPanelBase);

export default GlassPanel;

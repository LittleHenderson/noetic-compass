export const GLASS_PANEL_FILL = 'rgba(15, 23, 42, 0.55)';
export const GLASS_PANEL_BORDER = '1px solid rgba(255, 255, 255, 0.08)';
export const GLASS_PANEL_SHADOW = '0 8px 32px rgba(0, 0, 0, 0.35)';
export const GLASS_BLUR = 'blur(24px) saturate(160%)';
export const GLASS_RADIUS = 14;

export const GLASS_BLUR_THIN = 'blur(12px) saturate(160%)';
export const GLASS_BLUR_REGULAR = 'blur(24px) saturate(160%)';
export const GLASS_BLUR_THICK = 'blur(40px) saturate(160%)';

export const SPRING_SNAPPY = { type: 'spring', stiffness: 380, damping: 28 } as const;
export const SPRING_GENTLE = { type: 'spring', stiffness: 220, damping: 30 } as const;
export const EASE_OUT_CUBIC = [0.33, 1, 0.68, 1] as const;
export const STAGGER_CHILDREN = 0.04;

export const ACCENT_BLUE = '#3b82f6';

export const FONT_FAMILY =
  "'Inter', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";

export const COLORS = {
  textPrimary: '#e5e7eb',
  textSecondary: '#9ca3af',
  textMuted: '#6b7280',
  bgDeep: '#02030a',
  bgPanel: '#0f172a',
  borderSubtle: 'rgba(55, 65, 81, 0.7)',
} as const;

export const THEME = {
  GLASS_PANEL_FILL,
  GLASS_PANEL_BORDER,
  GLASS_PANEL_SHADOW,
  GLASS_BLUR,
  GLASS_BLUR_THIN,
  GLASS_BLUR_REGULAR,
  GLASS_BLUR_THICK,
  GLASS_RADIUS,
  SPRING_SNAPPY,
  SPRING_GENTLE,
  EASE_OUT_CUBIC,
  STAGGER_CHILDREN,
  ACCENT_BLUE,
  fontFamily: FONT_FAMILY,
  colors: COLORS,
} as const;

export type GlassIntensity = 'thin' | 'regular' | 'thick';

export function glassBlurFor(intensity: GlassIntensity): string {
  if (intensity === 'thin') return GLASS_BLUR_THIN;
  if (intensity === 'thick') return GLASS_BLUR_THICK;
  return GLASS_BLUR_REGULAR;
}

// Wave 5.2 — restyle to match the production noeticcompass.com aesthetic:
// slate base, thin hairline borders at very low opacity, teal/cyan accent
// (NOT bright blue), no glow shadows, no gradient fills on buttons.
// Reference: rgba(45, 212, 191, 0.10) accent fills, text-slate-400 muted
// secondary, rounded-md (6 px) for buttons / rounded-lg (8 px) for panels.

export const GLASS_PANEL_FILL = 'rgba(255, 255, 255, 0.03)';
export const GLASS_PANEL_BORDER = '1px solid rgba(255, 255, 255, 0.06)';
export const GLASS_PANEL_SHADOW = 'none';
export const GLASS_BLUR = 'blur(14px) saturate(120%)';
export const GLASS_RADIUS = 8;

export const GLASS_BLUR_THIN = 'blur(8px) saturate(120%)';
export const GLASS_BLUR_REGULAR = 'blur(14px) saturate(120%)';
export const GLASS_BLUR_THICK = 'blur(22px) saturate(130%)';

// Snappier, less bouncy. The previous SPRING_SNAPPY at stiffness 380 was the
// source of the candy-store overshoot on every button press.
export const SPRING_SNAPPY = { type: 'spring', stiffness: 420, damping: 38 } as const;
export const SPRING_GENTLE = { type: 'spring', stiffness: 260, damping: 34 } as const;
export const EASE_OUT_CUBIC = [0.33, 1, 0.68, 1] as const;
export const STAGGER_CHILDREN = 0.04;

// The token's name is preserved for back-compat with existing imports;
// only the value changes. accent-teal (#2dd4bf) is the production accent.
export const ACCENT_BLUE = '#2dd4bf';
export const ACCENT_TEAL = '#2dd4bf';
export const ACCENT_CYAN = '#22d3ee';
export const ACCENT_AMBER = '#fbbf24';

export const FONT_FAMILY =
  "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI Variable', 'Segoe UI', 'Inter', Roboto, 'Helvetica Neue', Arial, sans-serif";

export const FONT_MONO =
  "'JetBrains Mono', 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace";

export const COLORS = {
  textPrimary: '#e2e8f0',     // slate-200
  textSecondary: '#94a3b8',   // slate-400
  textMuted: '#64748b',       // slate-500
  textFaint: '#475569',       // slate-600
  bgDeep: '#020617',          // slate-950
  bgPanel: 'rgba(255, 255, 255, 0.03)',
  bgPanelHover: 'rgba(255, 255, 255, 0.06)',
  borderSubtle: 'rgba(255, 255, 255, 0.06)',
  borderStrong: 'rgba(255, 255, 255, 0.12)',
} as const;

export const RADIUS = {
  sm: 4,
  md: 6,
  lg: 8,
  xl: 12,
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
  ACCENT_TEAL,
  ACCENT_CYAN,
  ACCENT_AMBER,
  fontFamily: FONT_FAMILY,
  fontMono: FONT_MONO,
  colors: COLORS,
  radius: RADIUS,
} as const;

export type GlassIntensity = 'thin' | 'regular' | 'thick';

export function glassBlurFor(intensity: GlassIntensity): string {
  if (intensity === 'thin') return GLASS_BLUR_THIN;
  if (intensity === 'thick') return GLASS_BLUR_THICK;
  return GLASS_BLUR_REGULAR;
}

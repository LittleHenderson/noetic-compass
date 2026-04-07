/** Color palettes for the dark-mode dashboard */

export const CERT_COLORS: Record<string, string> = {
  Platinum: '#22d3ee', // cyan
  Gold: '#fbbf24',     // amber
  Silver: '#94a3b8',   // gray
  Bronze: '#fb923c',   // orange
  Fail: '#ef4444',     // red
};

export const CERT_GLOW: Record<string, string> = {
  Platinum: 'rgba(34, 211, 238, 0.3)',
  Gold: 'rgba(251, 191, 36, 0.3)',
  Silver: 'rgba(148, 163, 184, 0.2)',
  Bronze: 'rgba(251, 146, 60, 0.25)',
  Fail: 'rgba(239, 68, 68, 0.3)',
};

export const DOMAIN_COLORS: readonly string[] = [
  '#818cf8', // P - Principled (indigo-light)
  '#60a5fa', // C - Cognitive (blue-light)
  '#34d399', // E - Evaluative (emerald-light)
  '#fbbf24', // O - Operational (amber)
] as const;

export const DRIVE_COLORS: readonly string[] = [
  '#a78bfa', // F1 Unity
  '#60a5fa', // F2 Wisdom
  '#34d399', // F3 Vitality
  '#fbbf24', // F4 Connection
  '#f87171', // F5 Agency
  '#f472b6', // F6 Structure
  '#818cf8', // F7 Purpose
] as const;

export const INVOLUTION_PAIR_COLORS: readonly [string, string][] = [
  ['#a78bfa', '#c4b5fd'], // CO-2/CO-3
  ['#60a5fa', '#93c5fd'], // CO-5/CO-6
  ['#34d399', '#6ee7b7'], // CO-8/CO-9
] as const;

/** Gradient stops for the NCCS gauge arc */
export const GAUGE_GRADIENT = [
  { offset: '0%', color: '#ef4444' },    // red (low)
  { offset: '40%', color: '#fbbf24' },   // gold (mid)
  { offset: '75%', color: '#2dd4bf' },   // teal (high)
  { offset: '100%', color: '#22d3ee' },  // cyan (perfect)
] as const;

export function certColor(certification: string): string {
  return CERT_COLORS[certification] ?? CERT_COLORS.Fail;
}

export function certGlow(certification: string): string {
  return CERT_GLOW[certification] ?? CERT_GLOW.Fail;
}

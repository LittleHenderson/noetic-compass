/** Color palettes for the dashboard */

export const CERT_COLORS: Record<string, string> = {
  Platinum: '#C0C0E8',
  Gold: '#FFD700',
  Silver: '#C0C0C0',
  Bronze: '#CD7F32',
  Fail: '#DC2626',
};

export const DOMAIN_COLORS: readonly string[] = [
  '#6366F1', // P - Principled (indigo)
  '#3B82F6', // C - Cognitive (blue)
  '#10B981', // E - Evaluative (emerald)
  '#F59E0B', // O - Operational (amber)
] as const;

export const DRIVE_COLORS: readonly string[] = [
  '#8B5CF6', // F1 Unity
  '#3B82F6', // F2 Wisdom
  '#10B981', // F3 Vitality
  '#F59E0B', // F4 Connection
  '#EF4444', // F5 Agency
  '#EC4899', // F6 Structure
  '#6366F1', // F7 Purpose
] as const;

export const INVOLUTION_PAIR_COLORS: readonly [string, string][] = [
  ['#8B5CF6', '#A78BFA'], // CO-2/CO-3
  ['#3B82F6', '#60A5FA'], // CO-5/CO-6
  ['#10B981', '#34D399'], // CO-8/CO-9
] as const;

export function certColor(certification: string): string {
  return CERT_COLORS[certification] ?? CERT_COLORS.Fail;
}

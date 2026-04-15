import { certColor, certGlow } from '../../lib/colors';
import { researchTierLabel } from '../../lib/researchTier';

export function CertBadge({ certification, composite }: { certification: string; composite: number }) {
  const color = certColor(certification);
  const glow = certGlow(certification);
  const label = researchTierLabel(certification);

  return (
    <span
      className="inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-sm font-bold tracking-wide"
      style={{
        color,
        backgroundColor: `${color}15`,
        border: `1px solid ${color}40`,
        boxShadow: `0 0 12px ${glow}`,
      }}
    >
      <span
        className="h-2 w-2 rounded-full"
        style={{ backgroundColor: color, boxShadow: `0 0 6px ${color}` }}
      />
      {label} - {composite.toFixed(1)}
    </span>
  );
}

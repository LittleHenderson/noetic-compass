import { certColor } from '../../lib/colors';

export function CertBadge({ certification, composite }: { certification: string; composite: number }) {
  const bg = certColor(certification);
  const textColor = certification === 'Fail' ? '#fff' : '#1f2937';

  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-semibold"
      style={{ backgroundColor: bg, color: textColor }}
    >
      {certification} — {composite.toFixed(1)}
    </span>
  );
}

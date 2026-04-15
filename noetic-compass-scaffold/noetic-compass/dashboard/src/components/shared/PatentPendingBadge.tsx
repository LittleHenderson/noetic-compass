interface PatentPendingBadgeProps {
  compact?: boolean;
  className?: string;
}

export function PatentPendingBadge({ compact = false, className = '' }: PatentPendingBadgeProps) {
  return (
    <div
      className={`inline-flex items-center gap-2 rounded-full border border-accent-gold/35 bg-accent-gold/[0.1] text-accent-gold shadow-[0_0_20px_rgba(251,191,36,0.12)] ${compact ? 'px-2.5 py-1 text-[10px]' : 'px-3 py-1.5 text-[11px]'} ${className}`.trim()}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-accent-gold animate-pulse" aria-hidden="true" />
      <span className="font-semibold uppercase tracking-[0.18em]">Patent Pending</span>
    </div>
  );
}

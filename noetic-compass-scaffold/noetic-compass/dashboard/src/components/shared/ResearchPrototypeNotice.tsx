export function ResearchPrototypeNotice({
  compact = false,
  className = '',
}: {
  compact?: boolean;
  className?: string;
}) {
  return (
    <div
      className={`rounded-lg border border-amber-400/20 bg-amber-400/[0.06] ${
        compact ? 'px-3 py-2' : 'px-4 py-3'
      } ${className}`.trim()}
    >
      <p className={`${compact ? 'text-[11px]' : 'text-xs'} font-semibold uppercase tracking-[0.14em] text-amber-300`}>
        Research-stage output
      </p>
      <p className={`${compact ? 'mt-1 text-[11px]' : 'mt-1 text-xs'} text-slate-300`}>
        Not a deployment certification.
      </p>
    </div>
  );
}

import type { BlindSpot } from '../../lib/blindSpots';

export function BlindSpotCard({ spots }: { spots: BlindSpot[] }) {
  if (spots.length === 0) {
    return (
      <div className="flex items-center gap-3 rounded-lg bg-emerald-500/[0.06] border border-emerald-500/15 p-4">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#34d399" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span className="text-sm text-emerald-400">No significant cognitive blind spots detected.</span>
      </div>
    );
  }

  const critical = spots.filter(s => s.severity === 'critical');
  const significant = spots.filter(s => s.severity === 'significant');
  const worst = spots[0];

  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="flex items-center gap-3">
        <span className="flex items-center justify-center w-10 h-10 rounded-lg bg-amber-500/10 text-amber-400 shrink-0">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 9v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </span>
        <div>
          <p className="text-sm font-semibold text-slate-200">
            {spots.length} blind spot{spots.length !== 1 ? 's' : ''} detected
          </p>
          <p className="text-[11px] text-slate-400">
            {critical.length > 0 && <span className="text-red-400">{critical.length} critical</span>}
            {critical.length > 0 && significant.length > 0 && ', '}
            {significant.length > 0 && <span className="text-amber-400">{significant.length} significant</span>}
          </p>
        </div>
      </div>

      {/* Most critical */}
      {worst && (
        <div className={`rounded-lg border p-4 ${worst.severity === 'critical' ? 'border-red-500/20 bg-red-500/[0.04]' : 'border-amber-500/20 bg-amber-500/[0.04]'}`}>
          <div className="flex items-center gap-2 mb-2">
            <span className={`text-[10px] font-bold uppercase tracking-wider ${worst.severity === 'critical' ? 'text-red-400' : 'text-amber-400'}`}>
              Most Critical
            </span>
            <span className="text-[10px] text-slate-500">{worst.label}</span>
          </div>
          <p className="text-[12px] text-slate-300 leading-relaxed">{worst.risk}</p>
          <p className="text-[11px] text-slate-500 mt-2">{worst.remediation}</p>
        </div>
      )}

      {/* All spots */}
      <div className="space-y-1.5">
        {spots.map((spot, i) => (
          <div key={i} className="flex items-center gap-3 rounded-lg bg-white/[0.02] border border-white/[0.06] px-3 py-2">
            <span className={`w-2 h-2 rounded-full shrink-0 ${spot.severity === 'critical' ? 'bg-red-400' : 'bg-amber-400'}`} />
            <span className="text-[11px] text-slate-300 flex-1">{spot.label}</span>
            <span className="text-[10px] font-mono text-slate-500">{spot.score.toFixed(1)}/{spot.threshold.toFixed(0)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

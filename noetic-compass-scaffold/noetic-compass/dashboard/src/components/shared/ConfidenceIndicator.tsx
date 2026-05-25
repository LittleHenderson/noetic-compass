import { useHistoryStore } from '../../stores/historyStore';

const STABILIZATION_THRESHOLD = 40;

function getConfidenceLevel(count: number): {
  label: string;
  color: string;
  description: string;
} {
  if (count < 10) {
    return {
      label: 'Low Coverage',
      color: '#f87171',
      description: 'Sample depth: limited.',
    };
  }
  if (count < 40) {
    return {
      label: 'Moderate Coverage',
      color: '#fbbf24',
      description: 'Sample depth: growing.',
    };
  }
  return {
    label: 'Broader Coverage',
    color: '#34d399',
    description: 'Sample depth: broader.',
  };
}

export function ConfidenceIndicator() {
  const records = useHistoryStore((s) => s.records);
  const count = records.length;
  const pct = Math.min(100, Math.round((count / STABILIZATION_THRESHOLD) * 100));
  const level = getConfidenceLevel(count);

  return (
    <div className="glass-card px-4 py-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: level.color }} />
          <span className="text-[11px] font-semibold text-slate-300">{level.label}</span>
        </div>
          <span className="text-[10px] font-mono text-slate-500">{count}/{STABILIZATION_THRESHOLD} prompts</span>
      </div>
      {/* Progress bar */}
      <div className="h-1.5 rounded-full bg-white/[0.06] overflow-hidden mb-2">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: level.color }}
        />
      </div>
      <p className="flex flex-wrap items-center gap-2 text-[10px] text-slate-500">
        {level.description}
        {count > 0 && count < STABILIZATION_THRESHOLD && (
          <span className="rounded-full bg-white/[0.04] px-2 py-0.5 text-slate-400">Coverage {pct}%</span>
        )}
      </p>
    </div>
  );
}

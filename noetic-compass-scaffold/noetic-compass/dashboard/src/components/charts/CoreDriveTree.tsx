import { DRIVE_LABELS } from '../../lib/constants';
import { DRIVE_COLORS } from '../../lib/colors';

export function CoreDriveTree({ driveScores }: { driveScores: number[] }) {
  const data = driveScores.map((s, i) => ({
    name: DRIVE_LABELS[i],
    score: +(s * 100).toFixed(1),
    color: DRIVE_COLORS[i],
  }));

  const maxScore = Math.max(...data.map(d => d.score), 1);

  return (
    <div className="animate-chart-in space-y-2.5 px-1">
      {data.map((d, i) => (
        <div key={i} className="space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-400 truncate pr-2">{d.name}</span>
            <span className="text-[11px] font-bold text-slate-300 tabular-nums">{d.score.toFixed(1)}</span>
          </div>
          <div className="h-2 w-full rounded-full bg-white/[0.04] overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700 ease-out"
              style={{
                width: `${(d.score / maxScore) * 100}%`,
                backgroundColor: d.color,
                boxShadow: `0 0 8px ${d.color}50`,
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

import { useState } from 'react';
import { DRIVE_LABELS } from '../../lib/constants';
import { DRIVE_COLORS } from '../../lib/colors';
import { ExplainPanel } from '../shared/ExplainPanel';
import { interpretDrive } from '../../lib/interpretations';

export function CoreDriveTree({ driveScores }: { driveScores: number[] }) {
  const [selected, setSelected] = useState<number | null>(null);

  const data = driveScores.map((s, i) => ({
    name: DRIVE_LABELS[i],
    score: +(s * 100).toFixed(1),
    color: DRIVE_COLORS[i],
  }));

  const maxScore = Math.max(...data.map(d => d.score), 1);

  const insight = selected !== null ? interpretDrive(selected, driveScores) : null;

  return (
    <div>
      <div className="animate-chart-in space-y-2.5 px-1">
        {data.map((d, i) => (
          <div
            key={i}
            className="space-y-1 cursor-pointer rounded px-1 py-0.5 transition-colors hover:bg-white/[0.03]"
            onClick={() => setSelected(selected === i ? null : i)}
          >
            <div className="flex items-center justify-between">
              <span className={`text-[11px] font-medium truncate pr-2 ${selected === i ? 'text-slate-200' : 'text-slate-400'}`}>
                {d.name}
              </span>
              <span className="text-[11px] font-bold text-slate-300 tabular-nums">{d.score.toFixed(1)}</span>
            </div>
            <div className="h-2 w-full rounded-full bg-white/[0.04] overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-700 ease-out"
                style={{
                  width: `${(d.score / maxScore) * 100}%`,
                  backgroundColor: d.color,
                  boxShadow: selected === i ? `0 0 12px ${d.color}80` : `0 0 8px ${d.color}50`,
                }}
              />
            </div>
          </div>
        ))}
        <div className="chart-hint text-center text-[10px] text-slate-600 opacity-0 transition-opacity">
          Click a bar for details
        </div>
      </div>

      {insight && (
        <ExplainPanel visible={true} onClose={() => setSelected(null)}>
          <p className="font-medium text-slate-200">{insight.label}</p>
          <p>{insight.description}</p>
          <p>
            Score: <span className="font-mono font-bold text-slate-200">{(insight.score * 100).toFixed(1)}%</span>
          </p>
          {insight.pairNote && (
            <p className="text-amber-400/80">{insight.pairNote}</p>
          )}
        </ExplainPanel>
      )}
    </div>
  );
}

import { useState } from 'react';
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Tooltip, ResponsiveContainer,
} from 'recharts';
import { INVERSION_AXIS_LABELS } from '../../lib/constants';
import { ExplainPanel } from '../shared/ExplainPanel';
import { interpretInversion, interpretStealth } from '../../lib/interpretations';

export function InversionMap({
  axisScores,
  stealthResistance,
}: {
  axisScores: number[];
  stealthResistance: number;
}) {
  const [open, setOpen] = useState(false);

  const data = axisScores.map((s, i) => ({
    axis: INVERSION_AXIS_LABELS[i].split(':')[0],
    resistance: +(s * 100).toFixed(1),
  }));

  const insights = axisScores.map((s, i) => interpretInversion(i, s));
  const stealthNote = interpretStealth(stealthResistance);

  return (
    <div className="chart-interactive" onClick={() => setOpen(!open)}>
      <div className="animate-chart-in">
        <ResponsiveContainer width="100%" height={260}>
          <RadarChart data={data} cx="50%" cy="50%" outerRadius="65%">
            <PolarGrid stroke="rgba(255,255,255,0.06)" />
            <PolarAngleAxis dataKey="axis" tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <PolarRadiusAxis domain={[0, 100]} tick={{ fill: '#475569', fontSize: 9 }} axisLine={false} />
            <Tooltip
              contentStyle={{ backgroundColor: '#151d33', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#e2e8f0' }}
            />
            <Radar
              dataKey="resistance"
              stroke="#f87171"
              strokeWidth={2}
              fill="#f87171"
              fillOpacity={0.12}
            />
          </RadarChart>
        </ResponsiveContainer>
        <div className="text-[11px] text-slate-500 text-center font-medium">
          Stealth Resistance: <span className="text-red-400">{(stealthResistance * 100).toFixed(1)}%</span>
        </div>
        <div className="chart-hint text-center text-[10px] text-slate-600 opacity-0 transition-opacity">
          Click for axis details
        </div>
      </div>

      <ExplainPanel visible={open} onClose={() => setOpen(false)}>
        <div className="space-y-2">
          {insights.map((inv) => (
            <div key={inv.index} className="rounded border border-white/[0.04] bg-white/[0.02] px-3 py-2">
              <div className="flex items-center justify-between">
                <span className="text-[12px] font-semibold text-slate-200">{inv.label}</span>
                <span className={`font-mono text-[12px] font-bold ${inv.score >= 0.6 ? 'text-emerald-400' : inv.score >= 0.4 ? 'text-amber-400' : 'text-red-400'}`}>
                  {(inv.score * 100).toFixed(0)}%
                </span>
              </div>
              <p className="mt-0.5 text-[11px] text-slate-400">{inv.description}</p>
              <p className="mt-0.5 text-[11px] text-slate-500">{inv.verdict}</p>
            </div>
          ))}
          <div className="rounded border border-white/[0.04] bg-white/[0.02] px-3 py-2">
            <span className="text-[12px] font-semibold text-slate-200">Stealth Detection</span>
            <p className="mt-0.5 text-[11px] text-slate-400">{stealthNote}</p>
          </div>
        </div>
      </ExplainPanel>
    </div>
  );
}

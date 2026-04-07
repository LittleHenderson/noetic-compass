import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Tooltip, ResponsiveContainer,
} from 'recharts';
import { INVERSION_AXIS_LABELS } from '../../lib/constants';

export function InversionMap({
  axisScores,
  stealthResistance,
}: {
  axisScores: number[];
  stealthResistance: number;
}) {
  const data = axisScores.map((s, i) => ({
    axis: INVERSION_AXIS_LABELS[i].split(':')[0],
    resistance: +(s * 100).toFixed(1),
  }));

  return (
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
    </div>
  );
}

import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Tooltip, ResponsiveContainer,
} from 'recharts';
import { OPERATOR_SHORT } from '../../lib/constants';

export function OperatorRadarChart({ scores }: { scores: number[] }) {
  const data = scores.map((s, i) => ({
    operator: OPERATOR_SHORT[i],
    score: +(s * 100).toFixed(1),
  }));

  return (
    <div className="animate-chart-in glow-teal">
      <ResponsiveContainer width="100%" height={280}>
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="68%">
          <PolarGrid stroke="rgba(255,255,255,0.06)" />
          <PolarAngleAxis dataKey="operator" tick={{ fill: '#94a3b8', fontSize: 11 }} />
          <PolarRadiusAxis domain={[0, 100]} tick={{ fill: '#475569', fontSize: 9 }} axisLine={false} />
          <Tooltip
            contentStyle={{ backgroundColor: '#151d33', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#e2e8f0' }}
          />
          <Radar
            dataKey="score"
            stroke="#2dd4bf"
            strokeWidth={2}
            fill="#2dd4bf"
            fillOpacity={0.15}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

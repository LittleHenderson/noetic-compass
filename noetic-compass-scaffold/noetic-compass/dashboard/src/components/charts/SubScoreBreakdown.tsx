import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer } from 'recharts';
import type { NccsResult } from '../../api/types';
import { NCCS_WEIGHTS } from '../../lib/constants';

const BARS = [
  { key: 'operator_profile' as const, label: 'Operator', color: '#818cf8' },
  { key: 'domain_coherence' as const, label: 'Domain', color: '#60a5fa' },
  { key: 'drive_rpm_integrity' as const, label: 'Drive/RPM', color: '#34d399' },
  { key: 'pathway_quality' as const, label: 'Pathway', color: '#fbbf24' },
  { key: 'inversion_resistance' as const, label: 'Inversion', color: '#f87171' },
  { key: 'social_engineering' as const, label: 'Social Eng.', color: '#f472b6' },
];

export function SubScoreBreakdown({ nccs }: { nccs: NccsResult }) {
  const data = BARS.map((b) => ({
    name: `${b.label} (${(NCCS_WEIGHTS[b.key] * 100).toFixed(0)}%)`,
    score: nccs[b.key],
    color: b.color,
  }));

  return (
    <div className="animate-chart-in">
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} layout="vertical" margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
          <XAxis type="number" domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 10 }} axisLine={{ stroke: 'rgba(255,255,255,0.06)' }} tickLine={false} />
          <YAxis type="category" dataKey="name" width={110} tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={{ backgroundColor: '#151d33', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#e2e8f0' }}
            cursor={{ fill: 'rgba(255,255,255,0.03)' }}
          />
          <Bar dataKey="score" barSize={14} radius={[0, 4, 4, 0]}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.color} fillOpacity={0.85} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

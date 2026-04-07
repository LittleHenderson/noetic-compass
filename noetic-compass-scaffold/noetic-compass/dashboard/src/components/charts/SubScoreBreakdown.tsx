import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';
import type { NccsResult } from '../../api/types';
import { NCCS_WEIGHTS } from '../../lib/constants';

const BARS = [
  { key: 'operator_profile' as const, label: 'Operator', color: '#6366F1' },
  { key: 'domain_coherence' as const, label: 'Domain', color: '#3B82F6' },
  { key: 'drive_rpm_integrity' as const, label: 'Drive/RPM', color: '#10B981' },
  { key: 'pathway_quality' as const, label: 'Pathway', color: '#F59E0B' },
  { key: 'inversion_resistance' as const, label: 'Inversion', color: '#EF4444' },
  { key: 'social_engineering' as const, label: 'Social Eng.', color: '#EC4899' },
];

export function SubScoreBreakdown({ nccs }: { nccs: NccsResult }) {
  const data = BARS.map((b) => ({
    name: `${b.label} (${(NCCS_WEIGHTS[b.key] * 100).toFixed(0)}%)`,
    score: nccs[b.key],
    color: b.color,
  }));

  return (
    <BarChart
      width={400}
      height={220}
      data={data}
      layout="vertical"
      margin={{ left: 100, right: 20, top: 5, bottom: 5 }}
    >
      <XAxis type="number" domain={[0, 100]} />
      <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 11 }} />
      <Tooltip />
      <Bar dataKey="score" barSize={18}>
        {data.map((d, i) => (
          <Cell key={i} fill={d.color} />
        ))}
      </Bar>
    </BarChart>
  );
}

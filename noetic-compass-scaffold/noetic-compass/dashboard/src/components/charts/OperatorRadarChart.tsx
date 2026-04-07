import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Tooltip,
} from 'recharts';
import { OPERATOR_SHORT } from '../../lib/constants';

export function OperatorRadarChart({ scores }: { scores: number[] }) {
  const data = scores.map((s, i) => ({
    operator: OPERATOR_SHORT[i],
    score: +(s * 100).toFixed(1),
  }));

  return (
    <RadarChart width={320} height={280} data={data} cx="50%" cy="50%" outerRadius="70%">
      <PolarGrid />
      <PolarAngleAxis dataKey="operator" tick={{ fontSize: 11 }} />
      <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 9 }} />
      <Tooltip />
      <Radar dataKey="score" stroke="#6366F1" fill="#6366F1" fillOpacity={0.3} />
    </RadarChart>
  );
}

import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Tooltip,
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
    <div>
      <RadarChart width={300} height={260} data={data} cx="50%" cy="50%" outerRadius="65%">
        <PolarGrid />
        <PolarAngleAxis dataKey="axis" tick={{ fontSize: 11 }} />
        <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 9 }} />
        <Tooltip />
        <Radar dataKey="resistance" stroke="#EF4444" fill="#EF4444" fillOpacity={0.25} />
      </RadarChart>
      <div className="text-xs text-gray-500 text-center">
        Stealth Resistance: {(stealthResistance * 100).toFixed(1)}%
      </div>
    </div>
  );
}

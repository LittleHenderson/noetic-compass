import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';
import { DRIVE_LABELS } from '../../lib/constants';
import { DRIVE_COLORS } from '../../lib/colors';

export function CoreDriveTree({ driveScores }: { driveScores: number[] }) {
  const data = driveScores.map((s, i) => ({
    name: DRIVE_LABELS[i],
    score: +(s * 100).toFixed(1),
    color: DRIVE_COLORS[i],
  }));

  return (
    <BarChart
      width={400}
      height={220}
      data={data}
      layout="vertical"
      margin={{ left: 110, right: 20, top: 5, bottom: 5 }}
    >
      <XAxis type="number" domain={[0, 100]} />
      <YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 11 }} />
      <Tooltip />
      <Bar dataKey="score" barSize={16}>
        {data.map((d, i) => (
          <Cell key={i} fill={d.color} />
        ))}
      </Bar>
    </BarChart>
  );
}

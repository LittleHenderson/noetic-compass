import { PieChart, Pie, Cell } from 'recharts';
import { certColor } from '../../lib/colors';

export function NccsGauge({
  composite,
  certification,
}: {
  composite: number;
  certification: string;
}) {
  const color = certColor(certification);
  const data = [
    { value: composite },
    { value: 100 - composite },
  ];

  return (
    <div className="flex flex-col items-center">
      <PieChart width={200} height={120}>
        <Pie
          data={data}
          cx={100}
          cy={100}
          startAngle={180}
          endAngle={0}
          innerRadius={60}
          outerRadius={90}
          dataKey="value"
          stroke="none"
        >
          <Cell fill={color} />
          <Cell fill="#e5e7eb" />
        </Pie>
      </PieChart>
      <div className="-mt-4 text-center">
        <div className="text-3xl font-bold" style={{ color }}>{composite.toFixed(1)}</div>
        <div className="text-xs text-gray-500">NCCS Composite</div>
      </div>
    </div>
  );
}

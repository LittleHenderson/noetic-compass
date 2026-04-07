import { PieChart, Pie, Cell } from 'recharts';
import { certColor, GAUGE_GRADIENT } from '../../lib/colors';

export function NccsGauge({
  composite,
  certification,
}: {
  composite: number;
  certification: string;
}) {
  const color = certColor(certification);
  const gradientId = 'nccs-gauge-gradient';
  const data = [
    { value: composite },
    { value: 100 - composite },
  ];

  return (
    <div className="flex flex-col items-center animate-chart-in">
      <PieChart width={220} height={130}>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="0">
            {GAUGE_GRADIENT.map((stop) => (
              <stop key={stop.offset} offset={stop.offset} stopColor={stop.color} />
            ))}
          </linearGradient>
        </defs>
        <Pie
          data={data}
          cx={110}
          cy={110}
          startAngle={180}
          endAngle={0}
          innerRadius={65}
          outerRadius={95}
          dataKey="value"
          stroke="none"
        >
          <Cell fill={`url(#${gradientId})`} />
          <Cell fill="rgba(255,255,255,0.04)" />
        </Pie>
      </PieChart>
      <div className="-mt-6 text-center">
        <div
          className="text-4xl font-extrabold tracking-tight"
          style={{ color, textShadow: `0 0 20px ${color}40` }}
        >
          {composite.toFixed(1)}
        </div>
        <div className="mt-1 text-[11px] font-medium uppercase tracking-widest text-slate-500">
          NCCS Composite
        </div>
      </div>
    </div>
  );
}

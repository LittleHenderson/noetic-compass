/* ── CAS Forex — Spark Chart (pure SVG) ── */

interface SparkChartProps {
  data: number[];
  width?: number;
  height?: number;
}

export function SparkChart({ data, width = 120, height = 32 }: SparkChartProps) {
  if (data.length < 2) {
    return <span style={{ color: "var(--text-muted)", fontSize: "0.8125rem" }}>No data</span>;
  }

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const padding = 2;

  const points = data
    .map((v, i) => {
      const x = padding + (i / (data.length - 1)) * (width - padding * 2);
      const y = height - padding - ((v - min) / range) * (height - padding * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  const isPositive = data[data.length - 1] >= data[0];
  const strokeColor = isPositive ? "var(--success)" : "var(--danger)";

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ display: "block" }}>
      <polyline
        points={points}
        fill="none"
        stroke={strokeColor}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

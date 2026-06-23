/* ── CAS Forex — Equity Curve (pure SVG) ── */

interface EquityPoint {
  date: string;
  equity: number;
}

interface EquityCurveProps {
  points: EquityPoint[];
  width?: number;
  height?: number;
  initialEquity?: number;
}

export function EquityCurve({ points, width = 600, height = 200, initialEquity }: EquityCurveProps) {
  if (points.length < 2) {
    return (
      <div style={{ color: "var(--text-muted)", padding: 20, textAlign: "center" }}>
        No equity data
      </div>
    );
  }

  const allValues = points.map((p) => p.equity);
  const refLine = initialEquity ?? allValues[0];
  const min = Math.min(...allValues, refLine);
  const max = Math.max(...allValues, refLine);
  const range = max - min || 1;
  const padX = 40;
  const padY = 20;
  const plotW = width - padX - 20;
  const plotH = height - padY - 20;

  const scaleX = (i: number) => padX + (i / (points.length - 1)) * plotW;
  const scaleY = (v: number) => padY + plotH - ((v - min) / range) * plotH;

  const linePoints = points
    .map((p, i) => `${scaleX(i).toFixed(1)},${scaleY(p.equity).toFixed(1)}`)
    .join(" ");

  const refY = scaleY(refLine).toFixed(1);

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{ width: "100%", display: "block" }}
    >
      {/* Grid lines */}
      {[0, 0.25, 0.5, 0.75, 1].map((f) => {
        const y = padY + plotH * (1 - f);
        return (
          <line
            key={f}
            x1={padX}
            y1={y}
            x2={padX + plotW}
            y2={y}
            stroke="var(--border-subtle)"
            strokeWidth={0.5}
          />
        );
      })}

      {/* Reference line */}
      <line
        x1={padX}
        y1={refY}
        x2={padX + plotW}
        y2={refY}
        stroke="var(--text-muted)"
        strokeWidth={1}
        strokeDasharray="4 4"
      />

      {/* Equity line */}
      <polyline
        points={linePoints}
        fill="none"
        stroke="var(--accent-teal)"
        strokeWidth={2}
        strokeLinejoin="round"
      />

      {/* Y-axis labels */}
      {[min, (min + max) / 2, max].map((v, i) => (
        <text
          key={i}
          x={padX - 6}
          y={scaleY(v) + 4}
          textAnchor="end"
          fill="var(--text-muted)"
          fontSize={9}
        >
          ${v.toFixed(0)}
        </text>
      ))}
    </svg>
  );
}

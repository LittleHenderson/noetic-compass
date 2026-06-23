/* ── CAS Forex — Candlestick Chart (pure SVG) ── */

interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
}

interface CandlestickChartProps {
  candles: Candle[];
  width?: number;
  height?: number;
  symbol?: string;
}

export function CandlestickChart({ candles, width = 700, height = 300, symbol }: CandlestickChartProps) {
  if (candles.length === 0) {
    return (
      <div style={{ color: "var(--text-muted)", padding: 40, textAlign: "center", fontSize: "0.8rem" }}>
        No candle data
      </div>
    );
  }

  const padX = 50;
  const padY = 20;
  const plotW = width - padX - 10;
  const plotH = height - padY - 30;
  const candleW = Math.max(2, (plotW / candles.length) * 0.6);
  const gap = plotW / candles.length;

  const highs = candles.map((c) => c.high);
  const lows = candles.map((c) => c.low);
  const allPrices = [...highs, ...lows];
  const min = Math.min(...allPrices);
  const max = Math.max(...allPrices);
  const range = max - min || 1;
  const scaleY = (v: number) => padY + plotH - ((v - min) / range) * plotH;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{ width: "100%", display: "block" }}
    >
      <title>{symbol ? `${symbol} candle chart` : "Candlestick chart"}</title>
      {/* Price scale */}
      {[min, (min + max) / 2, max].map((v, i) => (
        <text
          key={i}
          x={width - 4}
          y={scaleY(v) + 4}
          textAnchor="end"
          fill="var(--text-muted)"
          fontSize={9}
        >
          {v.toFixed(2)}
        </text>
      ))}

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

      {/* Candles */}
      {candles.map((c, i) => {
        const x = padX + i * gap + gap / 2;
        const isBullish = c.close >= c.open;
        const color = isBullish ? "var(--success)" : "var(--danger)";
        const bodyTop = scaleY(Math.max(c.open, c.close));
        const bodyBot = scaleY(Math.min(c.open, c.close));
        const bodyH = Math.max(1, bodyBot - bodyTop);
        const wickTop = scaleY(c.high);
        const wickBot = scaleY(c.low);

        return (
          <g key={i}>
            <line x1={x} y1={wickTop} x2={x} y2={wickBot} stroke={color} strokeWidth={1} />
            <rect
              x={x - candleW / 2}
              y={bodyTop}
              width={candleW}
              height={bodyH}
              fill={color}
            />
          </g>
        );
      })}
    </svg>
  );
}

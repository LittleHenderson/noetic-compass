const NODE_LABELS = ['A0', 'D', 'W', 'P'];

function scoreColor(score: number): string {
  if (score >= 0.7) return '#34d399';
  if (score >= 0.4) return '#fbbf24';
  return '#f87171';
}

function scoreGlow(score: number): string {
  if (score >= 0.7) return 'rgba(52, 211, 153, 0.4)';
  if (score >= 0.4) return 'rgba(251, 191, 36, 0.3)';
  return 'rgba(248, 113, 113, 0.3)';
}

export function RpmGraph({
  a0Score,
  driveScores,
  rpmCompleteness,
}: {
  a0Score: number;
  driveScores: number[][];
  rpmCompleteness: number;
}) {
  const rowH = 34;
  const colW = 70;
  const nodeR = 11;
  const startX = 40;
  const startY = 26;
  const svgW = startX + colW * 4 + 40;
  const svgH = startY + rowH * 7 + 20;

  return (
    <div className="animate-chart-in">
      <svg width={svgW} height={svgH} className="text-xs">
        {NODE_LABELS.map((label, ci) => (
          <text
            key={label}
            x={startX + ci * colW}
            y={12}
            textAnchor="middle"
            fill="#64748b"
            fontSize="10"
          >
            {label}
          </text>
        ))}

        {driveScores.map((stages, row) => {
          const y = startY + row * rowH;
          const scores = [a0Score, ...stages];

          return (
            <g key={row}>
              <text x={4} y={y + 4} fill="#64748b" fontSize="10" fontWeight="500">F{row + 1}</text>

              {scores.slice(0, -1).map((_, ci) => {
                const x1 = startX + ci * colW + nodeR + 2;
                const x2 = startX + (ci + 1) * colW - nodeR - 2;
                const met = scores[ci] >= 0.5 && scores[ci + 1] >= 0.5;
                return (
                  <line
                    key={ci}
                    x1={x1} y1={y} x2={x2} y2={y}
                    stroke={met ? '#34d399' : '#f87171'}
                    strokeWidth={1.5}
                    strokeOpacity={0.6}
                    markerEnd="url(#arrowhead-dark)"
                  />
                );
              })}

              {scores.map((score, ci) => (
                <g key={ci}>
                  <circle
                    cx={startX + ci * colW}
                    cy={y}
                    r={nodeR}
                    fill={scoreColor(score)}
                    fillOpacity={0.2}
                    stroke={scoreColor(score)}
                    strokeWidth={1.5}
                  />
                  <circle
                    cx={startX + ci * colW}
                    cy={y}
                    r={nodeR + 3}
                    fill="none"
                    stroke={scoreColor(score)}
                    strokeWidth={0}
                    style={{ filter: `drop-shadow(0 0 4px ${scoreGlow(score)})` }}
                  />
                  <text
                    x={startX + ci * colW}
                    y={y + 3.5}
                    textAnchor="middle"
                    fill={scoreColor(score)}
                    fontSize="8"
                    fontWeight="600"
                  >
                    {(score * 100).toFixed(0)}
                  </text>
                </g>
              ))}
            </g>
          );
        })}

        <defs>
          <marker id="arrowhead-dark" markerWidth="6" markerHeight="4" refX="5" refY="2" orient="auto">
            <polygon points="0 0, 6 2, 0 4" fill="#475569" />
          </marker>
        </defs>
      </svg>
      <div className="mt-1 text-[11px] text-slate-500 text-center font-medium">
        RPM Completeness: <span className="text-accent-teal">{(rpmCompleteness * 100).toFixed(1)}%</span>
      </div>
    </div>
  );
}

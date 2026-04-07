const NODE_LABELS = ['A0', 'D', 'W', 'P'];

function scoreColor(score: number): string {
  if (score >= 0.7) return '#22c55e';
  if (score >= 0.4) return '#f59e0b';
  return '#ef4444';
}

export function RpmGraph({
  a0Score,
  driveScores,
  rpmCompleteness,
}: {
  a0Score: number;
  driveScores: number[][]; // 7 drives × 3 stages [Dn, Wn, Pn]
  rpmCompleteness: number;
}) {
  const rowH = 32;
  const colW = 70;
  const nodeR = 10;
  const startX = 40;
  const startY = 24;
  const svgW = startX + colW * 4 + 40;
  const svgH = startY + rowH * 7 + 20;

  return (
    <div>
      <svg width={svgW} height={svgH} className="text-xs">
        {/* Column headers */}
        {NODE_LABELS.map((label, ci) => (
          <text
            key={label}
            x={startX + ci * colW}
            y={12}
            textAnchor="middle"
            className="fill-gray-400 text-[10px]"
          >
            {label}
          </text>
        ))}

        {driveScores.map((stages, row) => {
          const y = startY + row * rowH;
          const scores = [a0Score, ...stages];

          return (
            <g key={row}>
              {/* Drive label */}
              <text x={4} y={y + 4} className="fill-gray-500 text-[10px]">F{row + 1}</text>

              {/* Arrows */}
              {scores.slice(0, -1).map((_, ci) => {
                const x1 = startX + ci * colW + nodeR + 2;
                const x2 = startX + (ci + 1) * colW - nodeR - 2;
                const met = scores[ci] >= 0.5 && scores[ci + 1] >= 0.5;
                return (
                  <line
                    key={ci}
                    x1={x1} y1={y} x2={x2} y2={y}
                    stroke={met ? '#22c55e' : '#ef4444'}
                    strokeWidth={1.5}
                    markerEnd="url(#arrowhead)"
                  />
                );
              })}

              {/* Nodes */}
              {scores.map((score, ci) => (
                <g key={ci}>
                  <circle
                    cx={startX + ci * colW}
                    cy={y}
                    r={nodeR}
                    fill={scoreColor(score)}
                    opacity={0.8}
                  />
                  <text
                    x={startX + ci * colW}
                    y={y + 3}
                    textAnchor="middle"
                    className="fill-white text-[8px] font-medium"
                  >
                    {(score * 100).toFixed(0)}
                  </text>
                </g>
              ))}
            </g>
          );
        })}

        <defs>
          <marker id="arrowhead" markerWidth="6" markerHeight="4" refX="5" refY="2" orient="auto">
            <polygon points="0 0, 6 2, 0 4" fill="#9ca3af" />
          </marker>
        </defs>
      </svg>
      <div className="mt-1 text-xs text-gray-500 text-center">
        RPM Completeness: {(rpmCompleteness * 100).toFixed(1)}%
      </div>
    </div>
  );
}

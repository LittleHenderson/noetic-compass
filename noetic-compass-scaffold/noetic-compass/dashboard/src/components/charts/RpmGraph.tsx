import { useState } from 'react';
import { ExplainPanel } from '../shared/ExplainPanel';
import { interpretRpmChain, interpretRpmSummary } from '../../lib/interpretations';
import { classifyRpmStage, RPM_NODE_TYPES } from '../../lib/rpmStages';

const NODE_LABELS = ['A0', 'D', 'W', 'P'];

function scoreGlow(score: number): string {
  if (score >= 0.7) return 'rgba(52, 211, 153, 0.4)';
  if (score >= 0.4) return 'rgba(251, 191, 36, 0.3)';
  return 'rgba(248, 113, 113, 0.3)';
}

interface ResolutionDetail {
  drive: number;
  resolutions: { node: string; mechanism: string; operators: string[]; strength: number; components?: number }[];
}

export function RpmGraph({
  a0Score,
  driveScores,
  rpmCompleteness,
  resolutionDetails = [],
}: {
  a0Score: number;
  driveScores: number[][];
  rpmCompleteness: number;
  resolutionDetails?: ResolutionDetail[];
}) {
  const [selectedDrive, setSelectedDrive] = useState<number | null>(null);

  const rowH = 34;
  const colW = 70;
  const nodeR = 11;
  const startX = 40;
  const startY = 26;
  const svgW = startX + colW * 4 + 40;
  const svgH = startY + rowH * 7 + 20;

  const chainInsights = selectedDrive !== null
    ? interpretRpmChain(selectedDrive, driveScores[selectedDrive], a0Score)
    : null;
  const summary = interpretRpmSummary(driveScores, a0Score, rpmCompleteness);

  return (
    <div>
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
            const isSelected = selectedDrive === row;

            return (
              <g
                key={row}
                className="cursor-pointer"
                onClick={() => setSelectedDrive(isSelected ? null : row)}
                opacity={selectedDrive === null || isSelected ? 1 : 0.35}
              >
                <text x={4} y={y + 4} fill={isSelected ? '#e2e8f0' : '#64748b'} fontSize="10" fontWeight={isSelected ? '700' : '500'}>F{row + 1}</text>

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

                {scores.map((score, ci) => {
                  const stage = classifyRpmStage(RPM_NODE_TYPES[ci], score);
                  return (
                    <g key={ci}>
                      <circle
                        cx={startX + ci * colW}
                        cy={y}
                        r={nodeR}
                        fill={stage.color}
                        fillOpacity={0.2}
                        stroke={stage.color}
                        strokeWidth={isSelected ? 2.5 : 1.5}
                      />
                      <circle
                        cx={startX + ci * colW}
                        cy={y}
                        r={nodeR + 3}
                        fill="none"
                        stroke={stage.color}
                        strokeWidth={0}
                        style={{ filter: `drop-shadow(0 0 4px ${scoreGlow(score)})` }}
                      />
                      <text
                        x={startX + ci * colW}
                        y={y + 3}
                        textAnchor="middle"
                        fill={stage.color}
                        fontSize="8"
                        fontWeight="600"
                      >
                        {(score * 100).toFixed(0)}
                      </text>
                      {isSelected && (
                        <text
                          x={startX + ci * colW}
                          y={y + nodeR + 12}
                          textAnchor="middle"
                          fill={stage.color}
                          fontSize="7"
                          fontWeight="500"
                        >
                          {stage.label}
                        </text>
                      )}
                    </g>
                  );
                })}
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
          {resolutionDetails.length > 0 && (
            <span className="ml-2 text-emerald-400">
              ({resolutionDetails.reduce((n, d) => n + d.resolutions.length, 0)} recursive resolutions)
            </span>
          )}
        </div>
        {/* Resolution details when a drive is selected */}
        {selectedDrive !== null && resolutionDetails.find(d => d.drive === selectedDrive)?.resolutions.length ? (
          <div className="mt-2 space-y-1.5 px-2">
            {resolutionDetails
              .filter(d => d.drive === selectedDrive)
              .flatMap(d => d.resolutions)
              .map((res, i) => (
                <div key={i} className="flex items-start gap-2 rounded bg-emerald-500/[0.06] border border-emerald-500/20 px-2 py-1.5">
                  <span className="text-emerald-400 text-[10px] mt-0.5">✓</span>
                  <div className="text-[10px]">
                    <span className="text-emerald-300 font-semibold capitalize">{res.node}</span>
                    <span className="text-slate-400"> resolved via </span>
                    <span className="text-accent-teal font-mono">
                      {res.mechanism === 'exposure_loop' ? 'Exposure Loop (CO-1→CO-4→CO-7)' :
                       res.mechanism === 'knowledge_reception' ? 'Knowledge Reception (CO-5)' :
                       res.mechanism === 'knowledge_decomposition' ? `Knowledge Decomposition (CO-6, ${res.components ?? '?'} components)` :
                       res.mechanism === 'causal_search' ? 'Causal Search (CO-8→CO-9)' :
                       res.mechanism}
                    </span>
                  </div>
                </div>
              ))}
          </div>
        ) : null}
        <div className="chart-hint text-center text-[10px] text-slate-600 opacity-0 transition-opacity">
          Click a drive row for details
        </div>
      </div>

      {chainInsights ? (
        <ExplainPanel visible={true} onClose={() => setSelectedDrive(null)}>
          <p className="font-medium text-slate-200">F{selectedDrive! + 1} Capability Chain</p>
          <div className="mt-1 space-y-1">
            {chainInsights.map((node, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className={`mt-0.5 flex-shrink-0 w-2 h-2 rounded-full ${node.chainStatus === 'flowing' ? 'bg-emerald-400' : 'bg-red-400'}`} />
                <span className="text-[12px]">{node.description}</span>
              </div>
            ))}
          </div>
        </ExplainPanel>
      ) : (
        <ExplainPanel visible={selectedDrive === null && false} onClose={() => {}}>
          <p>{summary}</p>
        </ExplainPanel>
      )}
    </div>
  );
}

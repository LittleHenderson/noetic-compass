import { useState } from 'react';
import { DOMAIN_SHORT, OPERATOR_SHORT } from '../../lib/constants';
import { DOMAIN_COLORS } from '../../lib/colors';
import { ExplainPanel } from '../shared/ExplainPanel';
import { interpretState } from '../../lib/interpretations';

export function StateHeatmap({
  operatorScores,
  domainAverages,
}: {
  operatorScores: number[];
  domainAverages: number[];
}) {
  const [selected, setSelected] = useState<{ d: number; o: number } | null>(null);

  const insight = selected
    ? interpretState(selected.d, selected.o, domainAverages[selected.d], operatorScores[selected.o])
    : null;

  return (
    <div>
      <div className="overflow-x-auto animate-chart-in">
        <div className="inline-grid gap-1" style={{ gridTemplateColumns: `auto repeat(10, 1fr)` }}>
          <div />
          {OPERATOR_SHORT.map((op) => (
            <div key={op} className="px-1 py-0.5 text-center text-[10px] text-slate-500 font-medium">
              {op}
            </div>
          ))}

          {DOMAIN_SHORT.map((domain, di) => (
            <>
              <div key={`label-${domain}`} className="px-2 py-1 text-xs font-medium text-slate-400 flex items-center">
                {domain}
              </div>
              {operatorScores.map((opScore, oi) => {
                const intensity = domainAverages[di] * opScore;
                const stateLabel = `${domain}${oi}`;
                const isSelected = selected?.d === di && selected?.o === oi;
                return (
                  <div
                    key={`${di}-${oi}`}
                    className="w-7 h-7 rounded cursor-pointer transition-all duration-200 hover:scale-110"
                    style={{
                      backgroundColor: DOMAIN_COLORS[di],
                      opacity: 0.1 + intensity * 0.9,
                      boxShadow: isSelected
                        ? `0 0 12px ${DOMAIN_COLORS[di]}60, inset 0 0 0 2px white`
                        : intensity > 0.6 ? `0 0 8px ${DOMAIN_COLORS[di]}30` : 'none',
                    }}
                    title={`${stateLabel}: ${(intensity * 100).toFixed(1)}`}
                    onClick={() => setSelected(isSelected ? null : { d: di, o: oi })}
                  />
                );
              })}
            </>
          ))}
        </div>
        <div className="chart-hint mt-1 text-center text-[10px] text-slate-600 opacity-0 transition-opacity">
          Click a cell for details
        </div>
      </div>

      {insight && (
        <ExplainPanel visible={true} onClose={() => setSelected(null)}>
          <p className="font-medium text-slate-200">
            State {insight.state}: {insight.operator} / {insight.domain}
          </p>
          <p>
            Intensity: <span className="font-mono font-bold text-slate-200">{(insight.intensity * 100).toFixed(1)}%</span>
          </p>
          <p>{insight.description}</p>
        </ExplainPanel>
      )}
    </div>
  );
}

import { DOMAIN_SHORT, OPERATOR_SHORT } from '../../lib/constants';
import { DOMAIN_COLORS } from '../../lib/colors';

export function StateHeatmap({
  operatorScores,
  domainAverages,
}: {
  operatorScores: number[];
  domainAverages: number[];
}) {
  return (
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
              return (
                <div
                  key={`${di}-${oi}`}
                  className="w-7 h-7 rounded cursor-default transition-all duration-200 hover:scale-110"
                  style={{
                    backgroundColor: DOMAIN_COLORS[di],
                    opacity: 0.1 + intensity * 0.9,
                    boxShadow: intensity > 0.6 ? `0 0 8px ${DOMAIN_COLORS[di]}30` : 'none',
                  }}
                  title={`${stateLabel}: ${(intensity * 100).toFixed(1)}`}
                />
              );
            })}
          </>
        ))}
      </div>
    </div>
  );
}

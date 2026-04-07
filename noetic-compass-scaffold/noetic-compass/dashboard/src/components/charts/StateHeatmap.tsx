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
    <div className="overflow-x-auto">
      <div className="inline-grid gap-0.5" style={{ gridTemplateColumns: `auto repeat(10, 1fr)` }}>
        {/* Header row */}
        <div />
        {OPERATOR_SHORT.map((op) => (
          <div key={op} className="px-1 py-0.5 text-center text-[10px] text-gray-500 font-medium">
            {op}
          </div>
        ))}

        {/* Domain rows */}
        {DOMAIN_SHORT.map((domain, di) => (
          <>
            <div key={`label-${domain}`} className="px-2 py-1 text-xs font-medium text-gray-600 flex items-center">
              {domain}
            </div>
            {operatorScores.map((opScore, oi) => {
              const intensity = domainAverages[di] * opScore;
              const stateLabel = `${domain}${oi}`;
              return (
                <div
                  key={`${di}-${oi}`}
                  className="w-7 h-7 rounded-sm cursor-default"
                  style={{
                    backgroundColor: DOMAIN_COLORS[di],
                    opacity: 0.2 + intensity * 0.8,
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

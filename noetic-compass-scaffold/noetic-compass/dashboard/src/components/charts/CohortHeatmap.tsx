/**
 * CohortHeatmap — NxN alignment heatmap showing pairwise cognitive
 * proximity between all candidates in the cohort.
 */

import type { CohortCompareResult } from '../../api/types';

function cellColor(alignment: number): string {
  // Gradient: red (0%) → amber (50%) → teal (80%) → cyan (100%)
  if (alignment >= 90) return 'rgba(34, 211, 238, 0.6)';   // cyan
  if (alignment >= 75) return 'rgba(45, 212, 191, 0.45)';  // teal
  if (alignment >= 60) return 'rgba(52, 211, 153, 0.35)';  // emerald
  if (alignment >= 45) return 'rgba(251, 191, 36, 0.3)';   // amber
  if (alignment >= 30) return 'rgba(251, 146, 60, 0.3)';   // orange
  return 'rgba(239, 68, 68, 0.25)';                         // red
}

export function CohortHeatmap({ result }: { result: CohortCompareResult }) {
  const { labels, distances } = result;
  const n = labels.length;

  // Build NxN alignment matrix
  const matrix: number[][] = Array.from({ length: n }, () => Array(n).fill(100));
  for (const d of distances) {
    const i = labels.indexOf(d.from_label);
    const j = labels.indexOf(d.to_label);
    if (i >= 0 && j >= 0) {
      matrix[i][j] = d.alignment_pct;
      matrix[j][i] = d.alignment_pct;
    }
  }

  return (
    <div className="space-y-2">
      <p className="text-[11px] text-slate-500">
        Cell values show alignment percentage — higher (teal) means more cognitively similar.
        Diagonal is always 100% (self).
      </p>

      <div className="overflow-x-auto">
        <div
          className="inline-grid gap-px"
          style={{
            gridTemplateColumns: `auto repeat(${n}, minmax(60px, 1fr))`,
          }}
        >
          {/* Header row */}
          <div />
          {labels.map((label) => (
            <div
              key={`h-${label}`}
              className="px-2 py-1.5 text-[10px] font-semibold text-slate-400 text-center truncate"
            >
              {label}
            </div>
          ))}

          {/* Data rows */}
          {labels.map((rowLabel, i) => (
            <>
              <div
                key={`r-${rowLabel}`}
                className="px-2 py-1.5 text-[10px] font-semibold text-slate-400 flex items-center"
              >
                {rowLabel}
              </div>
              {labels.map((_, j) => {
                const val = matrix[i][j];
                const isDiag = i === j;
                return (
                  <div
                    key={`${i}-${j}`}
                    className={`flex items-center justify-center px-1 py-2 rounded-sm text-[11px] font-mono font-bold transition-colors ${
                      isDiag ? 'text-slate-600' : 'text-slate-200'
                    }`}
                    style={{
                      backgroundColor: isDiag ? 'rgba(255,255,255,0.02)' : cellColor(val),
                    }}
                  >
                    {isDiag ? '—' : `${val.toFixed(0)}%`}
                  </div>
                );
              })}
            </>
          ))}
        </div>
      </div>
    </div>
  );
}

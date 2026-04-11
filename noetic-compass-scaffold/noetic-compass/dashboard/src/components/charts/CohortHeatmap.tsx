/**
 * CohortHeatmap — NxN alignment heatmap showing pairwise cognitive
 * proximity between all models in the cohort.
 */

import { Fragment, useState } from 'react';
import type { CohortCompareResult } from '../../api/types';

/** Shared color function for alignment/similarity percentages.
 *  Used by both CohortHeatmap cells and CohortPage table text. */
export function cohortColor(pct: number, mode: 'bg' | 'text' = 'bg'): string {
  if (mode === 'text') {
    if (pct >= 80) return '#22d3ee';   // cyan
    if (pct >= 60) return '#34d399';   // emerald
    if (pct >= 40) return '#fbbf24';   // amber
    return '#ef4444';                   // red
  }
  // bg mode — semi-transparent for heatmap cells
  if (pct >= 90) return 'rgba(34, 211, 238, 0.6)';   // cyan
  if (pct >= 75) return 'rgba(45, 212, 191, 0.45)';  // teal
  if (pct >= 60) return 'rgba(52, 211, 153, 0.35)';  // emerald
  if (pct >= 45) return 'rgba(251, 191, 36, 0.3)';   // amber
  if (pct >= 30) return 'rgba(251, 146, 60, 0.3)';   // orange
  return 'rgba(239, 68, 68, 0.25)';                   // red
}

/** Glow + pulse style for each cell based on alignment strength. */
function cellGlow(pct: number, isDiag: boolean): React.CSSProperties {
  if (isDiag) return {};
  if (pct >= 95) {
    return {
      boxShadow: '0 0 10px rgba(34, 211, 238, 0.7), inset 0 0 4px rgba(255,255,255,0.3)',
      animation: 'heatmap-cell-pulse 2.4s ease-in-out infinite',
    };
  }
  if (pct >= 85) {
    return { boxShadow: '0 0 5px rgba(45, 212, 191, 0.5)' };
  }
  if (pct >= 70) {
    return { boxShadow: '0 0 6px rgba(251, 191, 36, 0.5)' };
  }
  return {
    boxShadow: '0 0 7px rgba(239, 68, 68, 0.6)',
    animation: 'heatmap-cell-pulse-danger 2s ease-in-out infinite',
  };
}

export function CohortHeatmap({ result }: { result: CohortCompareResult }) {
  const { labels, distances } = result;
  const n = labels.length;
  const [selectedCell, setSelectedCell] = useState<{ i: number; j: number } | null>(null);

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

  // For the selected pair, find the underlying distance record for detail display
  const selectedDetail = selectedCell
    ? distances.find(
        (d) =>
          (d.from_label === labels[selectedCell.i] && d.to_label === labels[selectedCell.j]) ||
          (d.from_label === labels[selectedCell.j] && d.to_label === labels[selectedCell.i]),
      )
    : null;

  return (
    <div className="space-y-2">
      <p className="text-[11px] text-slate-500 group relative inline-block">
        Cell values show alignment percentage — higher (teal) means more cognitively similar.
        <span className="ml-1 text-slate-600 cursor-help border-b border-dotted border-slate-600">
          Diagonal is always 100% (self).
        </span>
        <span className="invisible group-hover:visible absolute left-0 top-full mt-1 z-10 w-72 rounded-lg border border-white/[0.08] bg-dark-800 p-3 text-[11px] text-slate-300 shadow-xl">
          A model compared to itself always shows 100% alignment. This is the baseline —
          all other percentages show how much two DIFFERENT models diverge.
        </span>
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
            <Fragment key={rowLabel}>
              <div
                className="px-2 py-1.5 text-[10px] font-semibold text-slate-400 flex items-center"
              >
                {rowLabel}
              </div>
              {labels.map((_, j) => {
                const val = matrix[i][j];
                const isDiag = i === j;
                return (
                  <button
                    key={`${i}-${j}`}
                    onClick={() => !isDiag && setSelectedCell({ i, j })}
                    disabled={isDiag}
                    className={`flex items-center justify-center px-1 py-2 rounded-sm text-[11px] font-mono font-bold transition-colors ${
                      isDiag ? 'text-slate-600 cursor-default' : 'text-slate-200 cursor-pointer hover:brightness-125'
                    }`}
                    style={{
                      backgroundColor: isDiag ? 'rgba(255,255,255,0.02)' : cohortColor(val),
                      ...cellGlow(val, isDiag),
                    }}
                  >
                    {isDiag ? '—' : `${val.toFixed(0)}%`}
                  </button>
                );
              })}
            </Fragment>
          ))}
        </div>
      </div>

      {/* Cell detail panel — shows what specific operators differ most */}
      {selectedDetail && selectedCell && (
        <div className="mt-4 rounded-lg border border-accent-teal/20 bg-accent-teal/[0.04] p-4">
          <div className="flex items-start justify-between gap-3 mb-2">
            <h4 className="text-[12px] font-semibold text-accent-teal">
              {selectedDetail.from_label} vs {selectedDetail.to_label}
            </h4>
            <button
              onClick={() => setSelectedCell(null)}
              className="text-[10px] text-slate-500 hover:text-slate-300"
            >
              ✕ close
            </button>
          </div>
          <div className="grid grid-cols-3 gap-3 text-[11px] mb-2">
            <div>
              <span className="text-slate-500 block">Alignment</span>
              <span
                className="font-mono font-bold"
                style={{ color: cohortColor(selectedDetail.alignment_pct, 'text') }}
              >
                {selectedDetail.alignment_pct.toFixed(1)}%
              </span>
            </div>
            <div>
              <span className="text-slate-500 block">Bhattacharyya</span>
              <span className="font-mono font-bold text-slate-200">
                {selectedDetail.bhattacharyya_coefficient.toFixed(4)}
              </span>
            </div>
            <div>
              <span className="text-slate-500 block">Cognitive Distance</span>
              <span className="font-mono font-bold text-slate-200">
                {selectedDetail.geodesic_distance.toFixed(4)}
              </span>
            </div>
          </div>
          <p className="text-[11px] text-slate-300 leading-relaxed">
            {selectedDetail.alignment_pct >= 95
              ? `These two models are nearly interchangeable — ${selectedDetail.alignment_pct.toFixed(1)}% alignment means their cognitive architectures are almost identical. Pick whichever is faster or cheaper.`
              : selectedDetail.alignment_pct >= 85
              ? `These models share a similar cognitive profile (${selectedDetail.alignment_pct.toFixed(1)}% alignment), but diverge enough on specific operators that outputs will differ on edge cases.`
              : selectedDetail.alignment_pct >= 70
              ? `These models think noticeably differently (${selectedDetail.alignment_pct.toFixed(1)}% alignment). Expect materially different answers on the same prompt — pick based on which cognitive strengths your task needs.`
              : `These models have significantly different cognitive architectures (${selectedDetail.alignment_pct.toFixed(1)}% alignment). They will produce meaningfully different outputs on most non-trivial prompts.`}
          </p>
        </div>
      )}
    </div>
  );
}

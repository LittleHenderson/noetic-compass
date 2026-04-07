/**
 * ExecutiveSummary — stakeholder-friendly overview of assessment results.
 * Uses the translation layer to present all metrics in plain business language.
 */

import type { TranslatedResult } from '../../hooks/useTranslation';
import { TranslatedMetric } from './TranslatedMetric';

export function ExecutiveSummary({ data }: { data: TranslatedResult }) {
  return (
    <div className="space-y-4 animate-chart-in">
      {/* One-liner */}
      <p className="text-sm text-slate-300 leading-relaxed">{data.executiveSummary}</p>

      {/* Key highlights */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/[0.04] px-3 py-2.5">
          <span className="text-[10px] text-emerald-400 uppercase tracking-wider font-medium">Top Strength</span>
          <p className="text-[12px] text-slate-200 mt-0.5">{data.topStrength}</p>
        </div>
        <div className="rounded-lg border border-amber-400/20 bg-amber-400/[0.04] px-3 py-2.5">
          <span className="text-[10px] text-amber-400 uppercase tracking-wider font-medium">Priority Improvement</span>
          <p className="text-[12px] text-slate-200 mt-0.5">{data.topRisk}</p>
        </div>
      </div>

      {/* Sub-score breakdown with translated labels */}
      <div className="space-y-1.5">
        <h4 className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">Score Breakdown</h4>
        {data.subScores.map((m) => (
          <TranslatedMetric key={m.key} metric={m} />
        ))}
      </div>
    </div>
  );
}

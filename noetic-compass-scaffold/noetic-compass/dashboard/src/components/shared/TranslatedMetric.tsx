/**
 * TranslatedMetric — displays a single metric with business-friendly label,
 * severity color, and a tooltip showing the technical explanation.
 */

import { useState } from 'react';
import type { TranslatedMetricData } from '../../lib/translations';

export function TranslatedMetric({ metric }: { metric: TranslatedMetricData }) {
  const [showTip, setShowTip] = useState(false);

  return (
    <div
      className="relative flex items-center gap-3 rounded-lg border border-white/[0.04] bg-white/[0.02] px-3 py-2.5 cursor-pointer hover:bg-white/[0.04] transition-colors"
      onMouseEnter={() => setShowTip(true)}
      onMouseLeave={() => setShowTip(false)}
    >
      {/* Severity indicator dot */}
      <div
        className="h-2.5 w-2.5 rounded-full shrink-0"
        style={{ backgroundColor: metric.severityColor }}
      />

      {/* Label + value */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <span className="text-[12px] font-semibold text-slate-200 truncate">
            {metric.label}
          </span>
          <span className="font-mono text-[12px] font-bold shrink-0" style={{ color: metric.severityColor }}>
            {metric.displayValue}
          </span>
        </div>
        <span className="text-[10px] text-slate-500">{metric.severityLabel}</span>
      </div>

      {/* Tooltip */}
      {showTip && metric.tooltip && (
        <div className="absolute z-50 left-0 right-0 -top-1 -translate-y-full px-3 py-2 rounded-lg bg-dark-800 border border-white/[0.08] shadow-xl animate-chart-in">
          <p className="text-[11px] text-slate-300 leading-relaxed">{metric.tooltip}</p>
        </div>
      )}
    </div>
  );
}

/**
 * DomainCoherenceRadar — Recharts radar showing the 4 processing domains
 * with business-friendly labels and a DCI (Processing Balance) indicator.
 */

import { useState } from 'react';
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  Tooltip, ResponsiveContainer,
} from 'recharts';
import { DOMAIN_COLORS } from '../../lib/colors';
import { ExplainPanel } from '../shared/ExplainPanel';
import { TranslatedMetric } from '../shared/TranslatedMetric';
import { translateDomainCoherence } from '../../lib/translations';
import type { WrapResult } from '../../api/types';

const DOMAIN_DESCRIPTIONS: string[] = [
  'Principled: Value-driven reasoning, ethical foundations, and guiding principles.',
  'Cognitive: Abstract thinking, pattern recognition, and knowledge construction.',
  'Evaluative: Judgment, decision-making, and quality assessment.',
  'Operational: Execution, implementation, and practical action.',
];

export function DomainCoherenceRadar({ result }: { result: WrapResult }) {
  const [open, setOpen] = useState(false);

  const dc = translateDomainCoherence(result);
  if (!dc) return null;

  const data = dc.domains.map((d, i) => ({
    domain: d.name,
    value: d.value,
    fill: DOMAIN_COLORS[i],
  }));

  const weakest = dc.domains.reduce((a, b) => a.value < b.value ? a : b);
  const strongest = dc.domains.reduce((a, b) => a.value > b.value ? a : b);

  return (
    <div className="chart-interactive" onClick={() => setOpen(!open)}>
      <div className="animate-chart-in">
        <ResponsiveContainer width="100%" height={260}>
          <RadarChart data={data} cx="50%" cy="50%" outerRadius="65%">
            <PolarGrid stroke="rgba(255,255,255,0.06)" />
            <PolarAngleAxis
              dataKey="domain"
              tick={{ fill: '#94a3b8', fontSize: 11, fontWeight: 500 }}
            />
            <PolarRadiusAxis
              domain={[0, Math.max(40, ...data.map(d => d.value))]}
              tick={{ fill: '#475569', fontSize: 9 }}
              axisLine={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#151d33',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 8,
                color: '#e2e8f0',
              }}
              formatter={(value) => [`${Number(value).toFixed(1)}%`, 'Strength']}
            />
            <Radar
              dataKey="value"
              stroke="#818cf8"
              strokeWidth={2}
              fill="#818cf8"
              fillOpacity={0.15}
            />
          </RadarChart>
        </ResponsiveContainer>

        {/* Processing Balance indicator */}
        <div className="flex items-center justify-center gap-2 mt-1">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider">Processing Balance</span>
          <span
            className="font-mono text-[12px] font-bold"
            style={{ color: dc.dci.severityColor }}
          >
            {dc.dci.displayValue}
          </span>
        </div>

        <div className="chart-hint text-center text-[10px] text-slate-600 opacity-0 transition-opacity mt-1">
          Click for domain details
        </div>
      </div>

      <ExplainPanel visible={open} onClose={() => setOpen(false)}>
        <p className="font-medium text-slate-200 mb-3">
          Strongest: {strongest.name} ({strongest.pct}). Weakest: {weakest.name} ({weakest.pct}).
        </p>

        <TranslatedMetric metric={dc.dci} />

        <div className="mt-3 space-y-2">
          {dc.domains.map((d, i) => (
            <div key={d.name} className="rounded border border-white/[0.04] bg-white/[0.02] px-3 py-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full" style={{ backgroundColor: DOMAIN_COLORS[i] }} />
                  <span className="text-[12px] font-semibold text-slate-200">{d.name}</span>
                </div>
                <span className="font-mono text-[12px] font-bold" style={{ color: DOMAIN_COLORS[i] }}>
                  {d.pct}
                </span>
              </div>
              <p className="mt-0.5 text-[11px] text-slate-400">{DOMAIN_DESCRIPTIONS[i]}</p>
            </div>
          ))}
        </div>
      </ExplainPanel>
    </div>
  );
}

import { useState } from 'react';
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Tooltip, ResponsiveContainer,
} from 'recharts';
import { OPERATOR_SHORT } from '../../lib/constants';
import { ExplainPanel } from '../shared/ExplainPanel';
import { interpretAllOperators } from '../../lib/interpretations';
import type { PhenomenologicalRegister } from '../../api/types';

/**
 * CAS v7.5 Phenomenological Register (Clarification 8) human-readable
 * names. Used for the register badge tooltip in the operator details panel.
 * Register is *specification of operational character* — lowercase `f` for
 * Affective is authoritative.
 */
const REGISTER_LABELS: Record<PhenomenologicalRegister, string> = {
  T: 'Transcendent',
  A: 'Analytical',
  f: 'Affective',
  E: 'Embodied',
};

export function OperatorRadarChart({
  scores,
  registers,
}: {
  scores: number[];
  /**
   * CAS v7.5 Register axis. Parallel list with scores; each entry is a
   * register letter or null when the score is register-neutral. Omit or
   * pass null for fully v7.4-compatible rendering.
   */
  registers?: (PhenomenologicalRegister | null)[] | null;
}) {
  const [open, setOpen] = useState(false);

  const data = scores.map((s, i) => ({
    operator: OPERATOR_SHORT[i],
    score: +(s * 100).toFixed(1),
  }));

  const { insights, summary } = interpretAllOperators(scores);

  // Only render register annotations when at least one non-null register
  // is present; keeps v7.4 register-neutral rendering byte-identical.
  const hasAnyRegister = Array.isArray(registers) && registers.some((r) => r != null);

  return (
    <div className="chart-interactive" onClick={() => setOpen(!open)}>
      <div className="animate-chart-in glow-teal">
        <ResponsiveContainer width="100%" height={280}>
          <RadarChart data={data} cx="50%" cy="50%" outerRadius="68%">
            <PolarGrid stroke="rgba(255,255,255,0.06)" />
            <PolarAngleAxis dataKey="operator" tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <PolarRadiusAxis domain={[0, 100]} tick={{ fill: '#475569', fontSize: 9 }} axisLine={false} />
            <Tooltip
              contentStyle={{ backgroundColor: '#151d33', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#e2e8f0' }}
            />
            <Radar
              dataKey="score"
              stroke="#2dd4bf"
              strokeWidth={2}
              fill="#2dd4bf"
              fillOpacity={0.15}
            />
          </RadarChart>
        </ResponsiveContainer>
        <div className="chart-hint text-center text-[10px] text-slate-600 opacity-0 transition-opacity">
          Click for operator details
        </div>
      </div>

      <ExplainPanel visible={open} onClose={() => setOpen(false)}>
        <p className="font-medium text-slate-200">{summary}</p>
        <div className="mt-2 space-y-2">
          {insights.map((op) => {
            const register = hasAnyRegister ? registers?.[op.index] ?? null : null;
            return (
              <div key={op.index} className="rounded border border-white/[0.04] bg-white/[0.02] px-3 py-2">
                <div className="flex items-center justify-between">
                  <span className="text-[12px] font-semibold text-slate-200">{op.label}</span>
                  <span className="flex items-center gap-1.5 font-mono text-[12px] font-bold text-accent-teal">
                    {register && (
                      <span
                        data-testid={`register-badge-${op.index}`}
                        className="rounded border border-white/10 bg-white/[0.04] px-1.5 py-0.5 text-[10px] font-medium text-slate-300"
                        title={`CAS v7.5 Register: ${REGISTER_LABELS[register]}`}
                      >
                        |{register}
                      </span>
                    )}
                    {(op.score * 100).toFixed(0)}%
                  </span>
                </div>
                <p className="mt-0.5 text-[11px] text-slate-400">{op.description}</p>
                {op.pairNote && (
                  <p className="mt-0.5 text-[11px] text-amber-400/80">{op.pairNote}</p>
                )}
              </div>
            );
          })}
        </div>
      </ExplainPanel>
    </div>
  );
}

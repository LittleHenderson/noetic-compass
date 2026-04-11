import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer,
} from 'recharts';
import { Card } from '../components/shared/Card';
import { LoadingSpinner } from '../components/shared/LoadingSpinner';
import { ErrorBanner } from '../components/shared/ErrorBanner';
import { InterpretButton } from '../components/shared/InterpretButton';
import { getValidationLeaderboard } from '../api/endpoints';
import type { OperatorCorrelation, ValidationLeaderboard } from '../api/types';

function interpretLeaderboard(data: ValidationLeaderboard): string {
  const { stats, operator_correlations, inter_rater, recommendations } = data;
  const n = stats.total_labels;

  if (n === 0) {
    return (
      'No labels have been collected yet. Head to the Validation page and ' +
      'start scoring prompt-response pairs. Once you have around 10+ labels, ' +
      'meaningful correlation numbers will start appearing here.'
    );
  }

  if (n < 10) {
    return (
      `Only ${n} label${n === 1 ? '' : 's'} so far. Correlation numbers need more ` +
      'data to mean anything — aim for at least 10 per operator before drawing conclusions. ' +
      'Keep labeling.'
    );
  }

  const strong = operator_correlations.filter(o => o.strength === 'strong').length;
  const moderate = operator_correlations.filter(o => o.strength === 'moderate').length;
  const weak = operator_correlations.filter(o => o.strength === 'weak').length;

  const overall = stats.overall_pearson_r;
  let headline: string;
  if (overall >= 0.7) {
    headline = `Overall correlation is ${overall.toFixed(2)} — that's strong agreement between human raters and the machine. The framework is tracking human judgment well.`;
  } else if (overall >= 0.4) {
    headline = `Overall correlation is ${overall.toFixed(2)} — that's moderate agreement. The machine and humans are in the same ballpark, but there's room for calibration.`;
  } else {
    headline = `Overall correlation is ${overall.toFixed(2)} — that's weak agreement. The machine and humans often disagree, which means the scoring rubric needs recalibration.`;
  }

  const breakdown = `${strong} operator${strong === 1 ? '' : 's'} show strong correlation, ${moderate} show moderate, and ${weak} show weak.`;

  // Inter-rater
  let raterNote = '';
  if (stats.num_raters < 2) {
    raterNote = 'Only one rater has submitted labels so far — recruit a second rater to measure inter-rater reliability (Cohen\'s kappa).';
  } else if (inter_rater.length > 0) {
    const avgKappa = stats.overall_cohens_kappa;
    if (avgKappa >= 0.7) {
      raterNote = `Inter-rater reliability is strong (κ = ${avgKappa.toFixed(2)}). Your raters largely agree with each other.`;
    } else if (avgKappa >= 0.4) {
      raterNote = `Inter-rater reliability is moderate (κ = ${avgKappa.toFixed(2)}). Raters agree on general direction but diverge on specific scores.`;
    } else {
      raterNote = `Inter-rater reliability is weak (κ = ${avgKappa.toFixed(2)}). Raters are interpreting the scoring criteria differently — consider a calibration session.`;
    }
  }

  // Worst operator to flag
  const sortedByR = [...operator_correlations].sort((a, b) => a.pearson_r - b.pearson_r);
  const worst = sortedByR[0];
  let worstNote = '';
  if (worst && worst.strength === 'weak' && worst.n_pairs >= 10) {
    worstNote = `The weakest alignment is on ${worst.operator_name} (r = ${worst.pearson_r.toFixed(2)}). Check the Calibration Recommendations below for specific guidance.`;
  }

  // Count active recommendations
  const alerts = recommendations.filter(r => r.severity === 'alert').length;
  const ready = alerts === 0 && strong >= 7;
  const readinessNote = ready
    ? 'The framework is in good shape — no critical calibration needed right now.'
    : `There ${alerts === 1 ? 'is' : 'are'} ${alerts} operator${alerts === 1 ? '' : 's'} flagged for recalibration. Scroll down to the recommendations section for specifics.`;

  return [headline, breakdown, raterNote, worstNote, readinessNote].filter(Boolean).join(' ');
}

const STRENGTH_COLOR: Record<string, string> = {
  strong: '#34d399',
  moderate: '#fbbf24',
  weak: '#f87171',
};

const STRENGTH_LABEL: Record<string, string> = {
  strong: 'Strong',
  moderate: 'Moderate',
  weak: 'Weak',
};

const STRENGTH_ICON: Record<string, string> = {
  strong: '✓',
  moderate: '~',
  weak: '!',
};

const SEVERITY_STYLE: Record<string, { bg: string; fg: string; border: string }> = {
  ok: { bg: 'rgba(52, 211, 153, 0.06)', fg: '#34d399', border: 'rgba(52, 211, 153, 0.2)' },
  warn: { bg: 'rgba(251, 191, 36, 0.06)', fg: '#fbbf24', border: 'rgba(251, 191, 36, 0.2)' },
  alert: { bg: 'rgba(248, 113, 113, 0.06)', fg: '#f87171', border: 'rgba(248, 113, 113, 0.2)' },
  info: { bg: 'rgba(148, 163, 184, 0.06)', fg: '#94a3b8', border: 'rgba(148, 163, 184, 0.2)' },
};

function StatCard({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="glass-card p-4">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">{label}</p>
      <p className="text-2xl font-bold" style={{ color: color ?? '#e2e8f0' }}>{value}</p>
    </div>
  );
}

function ScatterPlot({ correlation }: { correlation: OperatorCorrelation }) {
  const points = correlation.scatter_points;
  // Add regression line endpoints if we have enough data
  const color = STRENGTH_COLOR[correlation.strength];

  return (
    <div className="glass-card p-4">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-[11px] font-semibold text-slate-200">{correlation.operator_name}</h4>
        <span
          className="text-[10px] font-mono px-2 py-0.5 rounded-full"
          style={{ color, backgroundColor: `${color}15` }}
        >
          r = {correlation.pearson_r.toFixed(3)}
        </span>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <ScatterChart margin={{ left: 0, right: 10, top: 10, bottom: 5 }}>
          <CartesianGrid stroke="rgba(255,255,255,0.04)" />
          <XAxis
            type="number"
            dataKey="machine"
            name="Machine"
            domain={[0, 10]}
            tick={{ fill: '#64748b', fontSize: 9 }}
            label={{ value: 'Machine', position: 'insideBottomRight', offset: 0, fill: '#64748b', fontSize: 10 }}
          />
          <YAxis
            type="number"
            dataKey="human"
            name="Human"
            domain={[0, 10]}
            tick={{ fill: '#64748b', fontSize: 9 }}
            label={{ value: 'Human', angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 10 }}
          />
          <Tooltip
            cursor={{ strokeDasharray: '3 3' }}
            contentStyle={{ backgroundColor: '#151d33', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }}
          />
          <ReferenceLine
            segment={[{ x: 0, y: 0 }, { x: 10, y: 10 }]}
            stroke="rgba(255,255,255,0.1)"
            strokeDasharray="3 3"
          />
          <Scatter data={points} fill={color} fillOpacity={0.7} />
        </ScatterChart>
      </ResponsiveContainer>
      <div className="flex justify-between mt-2 text-[9px] text-slate-500">
        <span>n={correlation.n_pairs}</span>
        <span>p={correlation.p_value.toFixed(4)}</span>
        <span>CI=[{correlation.ci_lower.toFixed(2)}, {correlation.ci_upper.toFixed(2)}]</span>
      </div>
    </div>
  );
}

export function ValidationLeaderboardPage() {
  const [sortField, setSortField] = useState<'name' | 'r' | 'n'>('r');
  const [selectedOp, setSelectedOp] = useState<number | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['validation-leaderboard'],
    queryFn: getValidationLeaderboard,
    refetchInterval: 10_000,  // Real-time: poll every 10s
  });

  const sortedCorrelations = useMemo(() => {
    if (!data) return [];
    const sorted = [...data.operator_correlations];
    if (sortField === 'name') sorted.sort((a, b) => a.operator_index - b.operator_index);
    else if (sortField === 'r') sorted.sort((a, b) => b.pearson_r - a.pearson_r);
    else sorted.sort((a, b) => b.n_pairs - a.n_pairs);
    return sorted;
  }, [data, sortField]);

  const selectedCorrelation = useMemo(() => {
    if (!data || selectedOp === null) return data?.operator_correlations[0] ?? null;
    return data.operator_correlations[selectedOp] ?? null;
  }, [data, selectedOp]);

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorBanner error={error as Error} />;
  if (!data) return null;

  const { stats, operator_correlations, inter_rater, recommendations } = data;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 mb-1">Validation Leaderboard</h1>
          <p className="text-[11px] text-slate-500">
            Real-time correlation between human raters and machine scores. Updates every 10 seconds.
          </p>
        </div>
        <InterpretButton interpretation={interpretLeaderboard(data)} />
      </div>

      {/* Headline stats */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <StatCard label="Total Labels" value={stats.total_labels} />
        <StatCard label="Raters" value={stats.num_raters} />
        <StatCard label="Multi-Rated" value={stats.items_multi_rated} />
        <StatCard
          label="Overall r"
          value={stats.overall_pearson_r.toFixed(3)}
          color={STRENGTH_COLOR[stats.overall_pearson_r >= 0.7 ? 'strong' : stats.overall_pearson_r >= 0.4 ? 'moderate' : 'weak']}
        />
        <StatCard
          label="Inter-Rater κ"
          value={stats.overall_cohens_kappa.toFixed(3)}
          color={STRENGTH_COLOR[stats.overall_cohens_kappa >= 0.7 ? 'strong' : stats.overall_cohens_kappa >= 0.4 ? 'moderate' : 'weak']}
        />
      </div>

      {/* Per-operator correlation table */}
      <Card title="Per-Operator Correlation">
        <div className="overflow-x-auto -mx-5 px-5 sm:mx-0 sm:px-0">
          <table className="w-full text-sm min-w-[680px]">
            <thead>
              <tr className="border-b border-white/[0.06] text-left text-[10px] text-slate-500 uppercase tracking-wider">
                <th
                  className="pb-2 pr-4 cursor-pointer hover:text-slate-300"
                  onClick={() => setSortField('name')}
                >
                  Operator {sortField === 'name' && '↓'}
                </th>
                <th className="pb-2 pr-4 text-right">Human μ</th>
                <th className="pb-2 pr-4 text-right">Machine μ</th>
                <th
                  className="pb-2 pr-4 text-right cursor-pointer hover:text-slate-300"
                  onClick={() => setSortField('r')}
                >
                  r {sortField === 'r' && '↓'}
                </th>
                <th className="pb-2 pr-4 text-right">p</th>
                <th
                  className="pb-2 pr-4 text-right cursor-pointer hover:text-slate-300"
                  onClick={() => setSortField('n')}
                >
                  n {sortField === 'n' && '↓'}
                </th>
                <th className="pb-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {sortedCorrelations.map((op) => {
                const color = STRENGTH_COLOR[op.strength];
                return (
                  <tr
                    key={op.operator_index}
                    onClick={() => setSelectedOp(op.operator_index)}
                    className={`border-b border-white/[0.03] cursor-pointer hover:bg-white/[0.02] ${
                      selectedOp === op.operator_index ? 'bg-white/[0.03]' : ''
                    }`}
                  >
                    <td className="py-2.5 pr-4 text-slate-200">{op.operator_name}</td>
                    <td className="py-2.5 pr-4 text-right font-mono text-slate-300">{op.human_mean.toFixed(1)}</td>
                    <td className="py-2.5 pr-4 text-right font-mono text-slate-300">{op.machine_mean.toFixed(1)}</td>
                    <td className="py-2.5 pr-4 text-right font-mono font-bold" style={{ color }}>
                      {op.pearson_r.toFixed(3)}
                    </td>
                    <td className="py-2.5 pr-4 text-right font-mono text-slate-500">{op.p_value.toFixed(3)}</td>
                    <td className="py-2.5 pr-4 text-right font-mono text-slate-400">{op.n_pairs}</td>
                    <td className="py-2.5">
                      <span
                        className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold"
                        style={{ color, backgroundColor: `${color}15` }}
                      >
                        {STRENGTH_ICON[op.strength]} {STRENGTH_LABEL[op.strength]}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="text-[10px] text-slate-500 mt-2">Click a row to view its scatter plot below.</p>
      </Card>

      {/* Scatter plot for selected (or first) operator */}
      {selectedCorrelation && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400">
              Scatter Plot — {selectedCorrelation.operator_name}
            </h3>
            <select
              value={selectedOp ?? 0}
              onChange={(e) => setSelectedOp(Number(e.target.value))}
              className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-1 text-xs text-slate-300"
            >
              {operator_correlations.map((op) => (
                <option key={op.operator_index} value={op.operator_index} className="bg-dark-800">
                  {op.operator_name}
                </option>
              ))}
            </select>
          </div>
          <ScatterPlot correlation={selectedCorrelation} />
        </div>
      )}

      {/* Inter-rater reliability */}
      {inter_rater.length > 0 && (
        <Card title="Inter-Rater Reliability">
          <div className="overflow-x-auto -mx-5 px-5 sm:mx-0 sm:px-0">
            <table className="w-full text-sm min-w-[480px]">
              <thead>
                <tr className="border-b border-white/[0.06] text-left text-[10px] text-slate-500 uppercase tracking-wider">
                  <th className="pb-2 pr-4">Rater A</th>
                  <th className="pb-2 pr-4">Rater B</th>
                  <th className="pb-2 pr-4 text-right">Shared Items</th>
                  <th className="pb-2 pr-4 text-right">Cohen's κ</th>
                  <th className="pb-2 text-right">Agreement</th>
                </tr>
              </thead>
              <tbody>
                {inter_rater.map((ir, i) => {
                  const kColor = STRENGTH_COLOR[ir.cohens_kappa >= 0.7 ? 'strong' : ir.cohens_kappa >= 0.4 ? 'moderate' : 'weak'];
                  return (
                    <tr key={i} className="border-b border-white/[0.03]">
                      <td className="py-2.5 pr-4 text-slate-200">{ir.rater_a}</td>
                      <td className="py-2.5 pr-4 text-slate-200">{ir.rater_b}</td>
                      <td className="py-2.5 pr-4 text-right font-mono text-slate-400">{ir.shared_items}</td>
                      <td className="py-2.5 pr-4 text-right font-mono font-bold" style={{ color: kColor }}>
                        {ir.cohens_kappa.toFixed(3)}
                      </td>
                      <td className="py-2.5 text-right font-mono text-slate-300">{ir.agreement_pct.toFixed(1)}%</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Calibration recommendations */}
      <Card title="Calibration Recommendations">
        <div className="space-y-2">
          {recommendations.length === 0 ? (
            <p className="text-[11px] text-slate-500 text-center py-4">
              No recommendations yet — collect more labels to generate calibration guidance.
            </p>
          ) : (
            recommendations.map((rec, i) => {
              const style = SEVERITY_STYLE[rec.severity];
              return (
                <div
                  key={i}
                  className="rounded-lg border px-4 py-3"
                  style={{ backgroundColor: style.bg, borderColor: style.border }}
                >
                  <p className="text-[11px] leading-relaxed" style={{ color: style.fg }}>
                    {rec.message}
                  </p>
                </div>
              );
            })
          )}
        </div>
      </Card>

      {/* Export */}
      <div className="flex gap-2">
        <a
          href="/api/validation/export?format=json"
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-lg border border-white/[0.08] bg-white/[0.04] px-4 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 min-h-[44px] inline-flex items-center"
        >
          Export JSON
        </a>
        <a
          href="/api/validation/export?format=csv"
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-lg border border-white/[0.08] bg-white/[0.04] px-4 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 min-h-[44px] inline-flex items-center"
        >
          Export CSV
        </a>
      </div>
    </div>
  );
}

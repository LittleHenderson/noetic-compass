import { useState, useRef } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Card } from '../components/shared/Card';
import { CertBadge } from '../components/shared/CertBadge';
import { postReproducibility } from '../api/endpoints';
import type { ReproducibilityResponse, ReproducibilityRequest } from '../api/endpoints';
import { formatProviderLabel } from '../lib/providerLabels';

const PROVIDERS = ['mock', 'openai', 'anthropic', 'google', 'xai', 'deepseek', 'qwen', 'meta'];

const CERT_COLORS: Record<string, string> = {
  Platinum: '#a78bfa',
  Gold: '#fbbf24',
  Silver: '#94a3b8',
  Bronze: '#f97316',
  Fail: '#ef4444',
};

function StripPlot({ runs, mean, stdDev }: { runs: { composite: number; certification: string }[]; mean: number; stdDev: number }) {
  const min = Math.min(...runs.map(r => r.composite), mean - stdDev * 2);
  const max = Math.max(...runs.map(r => r.composite), mean + stdDev * 2);
  const pad = Math.max(5, (max - min) * 0.15);
  const lo = Math.max(0, min - pad);
  const hi = Math.min(100, max + pad);
  const range = hi - lo || 1;

  const toX = (val: number) => ((val - lo) / range) * 100;

  // Certification bands
  const bands = [
    { label: 'Fail', from: 0, to: 40, color: '#ef444420' },
    { label: 'Bronze', from: 40, to: 60, color: '#f9741620' },
    { label: 'Silver', from: 60, to: 75, color: '#94a3b820' },
    { label: 'Gold', from: 75, to: 90, color: '#fbbf2420' },
    { label: 'Platinum', from: 90, to: 100, color: '#a78bfa20' },
  ];

  return (
    <div className="relative h-28 rounded-lg border border-white/[0.06] bg-white/[0.02] overflow-hidden">
      {/* Certification bands */}
      {bands.map(band => {
        const left = toX(Math.max(band.from, lo));
        const right = toX(Math.min(band.to, hi));
        if (right <= left) return null;
        return (
          <div
            key={band.label}
            className="absolute top-0 bottom-0"
            style={{ left: `${left}%`, width: `${right - left}%`, backgroundColor: band.color }}
          />
        );
      })}

      {/* Std dev range */}
      <div
        className="absolute top-4 bottom-4 rounded bg-accent-teal/10 border border-accent-teal/20"
        style={{
          left: `${toX(mean - stdDev)}%`,
          width: `${toX(mean + stdDev) - toX(mean - stdDev)}%`,
        }}
      />

      {/* Mean line */}
      <div
        className="absolute top-2 bottom-2 w-0.5 bg-accent-teal"
        style={{ left: `${toX(mean)}%` }}
      />

      {/* Individual run dots */}
      {runs.map((run, i) => (
        <div
          key={i}
          className="absolute w-2.5 h-2.5 rounded-full border border-dark-900"
          style={{
            left: `${toX(run.composite)}%`,
            top: `${30 + (i % 3) * 18}%`,
            backgroundColor: CERT_COLORS[run.certification] ?? '#94a3b8',
            transform: 'translateX(-50%)',
          }}
          title={`Run ${i + 1}: ${run.composite.toFixed(1)} (${run.certification})`}
        />
      ))}

      {/* Scale labels */}
      <div className="absolute bottom-1 left-2 text-[8px] text-slate-600 font-mono">{lo.toFixed(0)}</div>
      <div className="absolute bottom-1 right-2 text-[8px] text-slate-600 font-mono">{hi.toFixed(0)}</div>
      <div
        className="absolute top-1 text-[8px] text-accent-teal font-mono font-semibold"
        style={{ left: `${toX(mean)}%`, transform: 'translateX(-50%)' }}
      >
        {mean.toFixed(1)}
      </div>
    </div>
  );
}

export function ReproducibilityPage() {
  const [text, setText] = useState('');
  const [provider, setProvider] = useState('mock');
  const [runs, setRuns] = useState(10);
  const resultRef = useRef<HTMLDivElement>(null);

  const mutation = useMutation({
    mutationFn: (req: ReproducibilityRequest) => postReproducibility(req),
    onSuccess() {
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
    },
  });

  const result: ReproducibilityResponse | undefined = mutation.data;

  function handleRun() {
    if (!text.trim()) return;
    mutation.mutate({
      text,
      provider,
      mock: provider === 'mock',
      runs,
    });
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-slate-100 mb-1">Reproducibility Test</h1>
        <p className="text-sm text-slate-400">
          Run the same prompt against the same provider N times. Measure test-retest reliability
          of the NCCS scoring engine.
        </p>
      </div>

      <Card title="Configure Test">
        <div className="space-y-4">
          <div>
            <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
              Prompt
            </label>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Enter the prompt to test for reproducibility..."
              rows={3}
              className="w-full rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3 text-base sm:text-sm text-slate-200 placeholder-slate-600 focus:border-accent-teal/50 focus:outline-none focus:ring-1 focus:ring-accent-teal/30 resize-none"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <label className="space-y-1">
              <span className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500">Provider</span>
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                className="w-full rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-sm text-slate-300 focus:border-accent-teal/50 focus:outline-none min-h-[44px]"
              >
                {PROVIDERS.map((p) => (
                  <option key={p} value={p} className="bg-dark-800">{formatProviderLabel(p)}</option>
                ))}
              </select>
            </label>

            <label className="space-y-1">
              <span className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500">Runs</span>
              <input
                type="number"
                min={2}
                max={50}
                value={runs}
                onChange={(e) => setRuns(Math.min(50, Math.max(2, Number(e.target.value))))}
                className="w-full rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-sm text-slate-300 focus:border-accent-teal/50 focus:outline-none min-h-[44px]"
              />
            </label>

            <div className="flex items-end">
              <button
                onClick={handleRun}
                disabled={!text.trim() || mutation.isPending}
                className="w-full rounded-lg bg-gradient-to-r from-accent-teal to-accent-cyan px-4 py-2.5 text-sm font-semibold text-dark-900 hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-opacity min-h-[44px]"
              >
                {mutation.isPending ? `Running ${runs} assessments...` : `Run ${runs}x`}
              </button>
            </div>
          </div>

          {provider !== 'mock' && (
            <p className="text-[10px] text-amber-400/80 flex items-center gap-1">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 9v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              Live API — {runs} calls will be made. Requires API key in .env
            </p>
          )}
        </div>
      </Card>

      {mutation.error && (
        <Card>
          <p className="text-sm text-red-400">{(mutation.error as Error).message}</p>
        </Card>
      )}

      {result && (
        <div ref={resultRef} className="space-y-5">
          {/* Stats overview */}
          <Card title="Scoring Reliability">
            <div className="space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3 text-center">
                  <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500">Mean NCCS</p>
                  <p className="text-2xl font-bold text-slate-100 mt-1">{result.stats.mean}</p>
                </div>
                <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3 text-center">
                  <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500">Std Dev</p>
                  <p className="text-2xl font-bold text-slate-100 mt-1">{result.stats.std_dev}</p>
                </div>
                <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3 text-center">
                  <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500">Range</p>
                  <p className="text-2xl font-bold text-slate-100 mt-1">{result.stats.range}</p>
                  <p className="text-[9px] text-slate-500 mt-0.5">{result.stats.min} — {result.stats.max}</p>
                </div>
                <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3 text-center">
                  <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-500">CV</p>
                  <p className="text-2xl font-bold text-slate-100 mt-1">{result.stats.coefficient_of_variation}%</p>
                </div>
              </div>

              {/* Certification consistency */}
              <div className="flex items-center gap-3 rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
                <CertBadge certification={result.stats.dominant_certification} composite={result.stats.mean} />
                <div>
                  <p className="text-sm font-medium text-slate-200">
                    {result.stats.certification_consistency}% certification consistency
                  </p>
                  <p className="text-[11px] text-slate-400">
                    {result.stats.certification_consistency === 100
                      ? `All ${result.completed_runs} runs certified ${result.stats.dominant_certification}`
                      : `${Math.round(result.stats.certification_consistency / 100 * result.completed_runs)} of ${result.completed_runs} runs certified ${result.stats.dominant_certification}`}
                  </p>
                </div>
              </div>

              {/* Reliability interpretation */}
              <div className={`rounded-lg border p-3 ${
                result.stats.coefficient_of_variation < 3
                  ? 'border-emerald-500/20 bg-emerald-500/[0.04]'
                  : result.stats.coefficient_of_variation < 8
                    ? 'border-amber-500/20 bg-amber-500/[0.04]'
                    : 'border-red-500/20 bg-red-500/[0.04]'
              }`}>
                <p className={`text-[11px] font-semibold ${
                  result.stats.coefficient_of_variation < 3
                    ? 'text-emerald-400'
                    : result.stats.coefficient_of_variation < 8
                      ? 'text-amber-400'
                      : 'text-red-400'
                }`}>
                  {result.stats.coefficient_of_variation < 3
                    ? 'High Test-Retest Reliability'
                    : result.stats.coefficient_of_variation < 8
                      ? 'Moderate Test-Retest Reliability'
                      : 'Low Test-Retest Reliability'}
                </p>
                <p className="text-[10px] text-slate-400 mt-1">
                  When the same prompt was submitted to {formatProviderLabel(result.provider)} {result.completed_runs} times independently,
                  NCCS scores showed a standard deviation of {result.stats.std_dev} points
                  (CV = {result.stats.coefficient_of_variation}%), demonstrating{' '}
                  {result.stats.coefficient_of_variation < 3 ? 'high' : result.stats.coefficient_of_variation < 8 ? 'moderate' : 'low'}{' '}
                  test-retest reliability.
                </p>
              </div>
            </div>
          </Card>

          {/* Strip plot */}
          <Card title="Score Distribution">
            <div className="space-y-3">
              <StripPlot
                runs={result.runs}
                mean={result.stats.mean}
                stdDev={result.stats.std_dev}
              />
              <div className="flex flex-wrap gap-3 text-[9px] text-slate-500">
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-accent-teal inline-block" /> Mean
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-6 h-2 rounded bg-accent-teal/10 border border-accent-teal/20 inline-block" /> ±1 Std Dev
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: CERT_COLORS.Gold }} /> Individual Run
                </span>
              </div>
            </div>
          </Card>

          {/* Individual runs table */}
          <Card title={`Individual Runs (${result.completed_runs})`}>
            <div className="overflow-x-auto">
              <table className="w-full text-[11px]">
                <thead>
                  <tr className="text-slate-500 uppercase tracking-wider text-[9px]">
                    <th className="text-left px-2 py-1.5">#</th>
                    <th className="text-right px-2 py-1.5">NCCS</th>
                    <th className="text-center px-2 py-1.5">Cert</th>
                    <th className="text-right px-2 py-1.5">Operator</th>
                    <th className="text-right px-2 py-1.5">Domain</th>
                    <th className="text-right px-2 py-1.5">Drive/RPM</th>
                    <th className="text-right px-2 py-1.5">Inversion</th>
                    <th className="text-right px-2 py-1.5">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {result.runs.map((run) => (
                    <tr key={run.run_index} className="border-t border-white/[0.04] hover:bg-white/[0.02]">
                      <td className="px-2 py-1.5 text-slate-500 font-mono">{run.run_index + 1}</td>
                      <td className="px-2 py-1.5 text-right font-semibold text-slate-200">{run.composite.toFixed(1)}</td>
                      <td className="px-2 py-1.5 text-center">
                        <span
                          className="text-[9px] px-1.5 py-0.5 rounded-full font-semibold"
                          style={{
                            backgroundColor: `${CERT_COLORS[run.certification] ?? '#94a3b8'}20`,
                            color: CERT_COLORS[run.certification] ?? '#94a3b8',
                          }}
                        >
                          {run.certification}
                        </span>
                      </td>
                      <td className="px-2 py-1.5 text-right text-slate-400">{run.operator_profile.toFixed(1)}</td>
                      <td className="px-2 py-1.5 text-right text-slate-400">{run.domain_coherence.toFixed(1)}</td>
                      <td className="px-2 py-1.5 text-right text-slate-400">{run.drive_rpm_integrity.toFixed(1)}</td>
                      <td className="px-2 py-1.5 text-right text-slate-400">{run.inversion_resistance.toFixed(1)}</td>
                      <td className="px-2 py-1.5 text-right text-slate-500 font-mono">{run.elapsed_ms.toFixed(0)}ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {/* Citable summary */}
          <Card title="Citable Summary">
            <div className="rounded-lg border border-white/[0.06] bg-dark-900/50 p-4 font-mono text-[11px] text-slate-300 leading-relaxed select-all">
              When the same prompt was submitted to {formatProviderLabel(result.provider)} {result.completed_runs} times independently,
              NCCS composite scores ranged from {result.stats.min} to {result.stats.max} (M = {result.stats.mean}, SD = {result.stats.std_dev},
              CV = {result.stats.coefficient_of_variation}%). Certification level was {result.stats.dominant_certification} in{' '}
              {result.stats.certification_consistency}% of trials, demonstrating{' '}
              {result.stats.coefficient_of_variation < 3 ? 'high' : result.stats.coefficient_of_variation < 8 ? 'moderate' : 'low'}{' '}
              test-retest reliability. Total elapsed time: {(result.total_elapsed_ms / 1000).toFixed(1)}s.
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

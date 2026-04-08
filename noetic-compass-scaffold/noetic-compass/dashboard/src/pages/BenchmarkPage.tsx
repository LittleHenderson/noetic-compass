import { useState, useRef, useEffect } from 'react';
import { useBenchmark } from '../hooks/useBenchmark';
import { Card } from '../components/shared/Card';
import { LoadingSpinner } from '../components/shared/LoadingSpinner';
import { ErrorBanner } from '../components/shared/ErrorBanner';
import { CertBadge } from '../components/shared/CertBadge';
import type { BenchmarkResponse, ProviderBenchmarkResult } from '../api/types';

const AVAILABLE_PROVIDERS = ['mock', 'openai', 'anthropic', 'google', 'meta', 'xai', 'deepseek', 'qwen'];

export function BenchmarkPage() {
  const [text, setText] = useState('');
  const [selectedProviders, setSelectedProviders] = useState<string[]>(['mock']);
  const [runsPerProvider, setRunsPerProvider] = useState(5);
  const benchmark = useBenchmark();
  const resultsRef = useRef<HTMLDivElement>(null);

  function toggleProvider(p: string) {
    setSelectedProviders((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]
    );
  }

  function handleSubmit() {
    if (!text.trim() || selectedProviders.length === 0) return;
    benchmark.mutate({ text, providers: selectedProviders, runs_per_provider: runsPerProvider });
  }

  const result: BenchmarkResponse | undefined = benchmark.data;

  // Auto-scroll to results when benchmark completes
  useEffect(() => {
    if (result && resultsRef.current) {
      resultsRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [result]);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-slate-100">Benchmark Mode</h1>
      <p className="text-sm text-slate-400">
        Run each provider multiple times on the same prompt to compare mean scores and variance.
      </p>

      <Card title="Benchmark Configuration">
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Prompt</label>
            <textarea
              className="w-full rounded-lg border border-white/10 bg-dark-700 px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:border-accent-teal focus:outline-none focus:ring-1 focus:ring-accent-teal min-h-[100px]"
              placeholder="Enter text to benchmark across providers..."
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-2">Providers</label>
            <div className="flex flex-wrap gap-2">
              {AVAILABLE_PROVIDERS.map((p) => (
                <button
                  key={p}
                  onClick={() => toggleProvider(p)}
                  className={`px-3 py-2 rounded-lg text-xs font-medium transition-all min-h-[44px] ${
                    selectedProviders.includes(p)
                      ? 'bg-accent-teal/20 text-accent-teal border border-accent-teal/40'
                      : 'bg-white/[0.04] text-slate-400 border border-white/10 hover:bg-white/[0.08]'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Runs per Provider</label>
              <input
                type="number"
                min={2}
                max={20}
                value={runsPerProvider}
                onChange={(e) => setRunsPerProvider(Math.min(20, Math.max(2, Number(e.target.value))))}
                className="w-full sm:w-20 rounded-lg border border-white/10 bg-dark-700 px-3 py-2 text-sm text-slate-200 focus:border-accent-teal focus:outline-none focus:ring-1 focus:ring-accent-teal min-h-[44px]"
              />
            </div>
            <button
              onClick={handleSubmit}
              disabled={!text.trim() || selectedProviders.length === 0 || benchmark.isPending}
              className="px-6 py-3 sm:py-2 rounded-lg bg-accent-teal/90 text-dark-900 text-sm font-semibold hover:bg-accent-teal transition-colors disabled:opacity-40 disabled:cursor-not-allowed min-h-[44px]"
            >
              {benchmark.isPending ? 'Running...' : 'Run Benchmark'}
            </button>
          </div>
        </div>
      </Card>

      {benchmark.isPending && (
        <div className="flex items-center gap-3 text-slate-400">
          <LoadingSpinner />
          <span className="text-sm">
            Running {selectedProviders.length * runsPerProvider} assessments...
          </span>
        </div>
      )}

      <ErrorBanner error={benchmark.error as Error | null} />

      {result && (
        <div ref={resultsRef} className="scroll-mt-4">
          <BenchmarkResults data={result} />
        </div>
      )}
    </div>
  );
}

function BenchmarkResults({ data }: { data: BenchmarkResponse }) {
  const sorted = [...data.results].sort((a, b) => b.mean - a.mean);

  return (
    <Card title="Results">
      <div className="mb-3 flex items-center gap-4 text-xs text-slate-500">
        <span>{data.runs_per_provider} runs/provider</span>
        <span>{data.total_runs} total runs</span>
        <span>Variance threshold: {data.variance_threshold}</span>
      </div>

      <div className="overflow-x-auto -mx-5 px-5 sm:mx-0 sm:px-0">
        <table className="w-full text-sm min-w-[640px]">
          <thead>
            <tr className="border-b border-white/10 text-left text-xs font-medium text-slate-500">
              <th className="pb-2 pr-4">Provider</th>
              <th className="pb-2 pr-4 text-right">Mean</th>
              <th className="pb-2 pr-4 text-right">Std Dev</th>
              <th className="pb-2 pr-4 text-right">Min</th>
              <th className="pb-2 pr-4 text-right">Max</th>
              <th className="pb-2 pr-4">Certifications</th>
              <th className="pb-2 pr-4 text-right">Latency</th>
              <th className="pb-2 pr-4 text-right">Failed</th>
              <th className="pb-2">Flag</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => (
              <BenchmarkRow key={r.provider} result={r} />
            ))}
          </tbody>
        </table>
      </div>

      {data.prompt_preview && (
        <div className="mt-4 pt-3 border-t border-white/10">
          <p className="text-xs text-slate-500">
            Prompt: <span className="text-slate-400">{data.prompt_preview}</span>
          </p>
        </div>
      )}
    </Card>
  );
}

function BenchmarkRow({ result }: { result: ProviderBenchmarkResult }) {
  const rowClass = result.high_variance
    ? 'border-b border-amber-500/20 bg-amber-500/[0.04]'
    : 'border-b border-white/[0.04]';

  const topCert = Object.entries(result.certification_counts)
    .sort(([, a], [, b]) => b - a)[0];

  return (
    <tr className={rowClass}>
      <td className="py-2.5 pr-4 font-medium text-slate-200">{result.provider}</td>
      <td className="py-2.5 pr-4 text-right font-mono text-slate-200">
        {result.scores.length > 0 ? result.mean.toFixed(1) : '—'}
      </td>
      <td className={`py-2.5 pr-4 text-right font-mono ${result.high_variance ? 'text-amber-400' : 'text-slate-400'}`}>
        {result.scores.length > 0 ? result.std_dev.toFixed(2) : '—'}
      </td>
      <td className="py-2.5 pr-4 text-right font-mono text-slate-400">
        {result.scores.length > 0 ? result.min.toFixed(1) : '—'}
      </td>
      <td className="py-2.5 pr-4 text-right font-mono text-slate-400">
        {result.scores.length > 0 ? result.max.toFixed(1) : '—'}
      </td>
      <td className="py-2.5 pr-4">
        {topCert ? (
          <span className="flex items-center gap-1.5">
            <CertBadge certification={topCert[0]} composite={result.mean} />
            {Object.keys(result.certification_counts).length > 1 && (
              <span className="text-xs text-slate-500">
                +{Object.keys(result.certification_counts).length - 1}
              </span>
            )}
          </span>
        ) : (
          <span className="text-slate-500">—</span>
        )}
      </td>
      <td className="py-2.5 pr-4 text-right font-mono text-slate-400">
        {result.avg_latency_ms > 0 ? `${result.avg_latency_ms.toFixed(0)}ms` : '—'}
      </td>
      <td className="py-2.5 pr-4 text-right font-mono text-slate-400">
        {result.failed_runs > 0 ? (
          <span className="text-red-400">{result.failed_runs}</span>
        ) : (
          '0'
        )}
      </td>
      <td className="py-2.5">
        {result.high_variance && (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/20 px-2 py-0.5 text-xs font-medium text-amber-400">
            High Variance
          </span>
        )}
      </td>
    </tr>
  );
}

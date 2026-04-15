import { Card } from './Card';
import { CertBadge } from './CertBadge';
import { formatProviderLabel } from '../../lib/providerLabels';
import type { BenchmarkResponse, ProviderBenchmarkResult } from '../../api/types';

export function BenchmarkResults({ data }: { data: BenchmarkResponse }) {
  const sorted = [...data.results].sort((a, b) => b.mean - a.mean);

  return (
    <Card title="Benchmark Results">
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
              <th className="pb-2 pr-4">Research Tiers</th>
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
      <td className="py-2.5 pr-4 font-medium text-slate-200">{formatProviderLabel(result.provider)}</td>
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

/**
 * CohortPage — AI Model Comparison.
 *
 * Compares the cognitive architectures of different AI models side by side.
 * Users select providers, and scores are auto-populated from history OR
 * they click "Quick Compare" to run the same prompt through every selected
 * model in one go.
 */

import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCohort } from '../hooks/useCohort';
import { useHistoryStore } from '../stores/historyStore';
import { postWrap } from '../api/endpoints';
import { Card } from '../components/shared/Card';
import { LoadingSpinner } from '../components/shared/LoadingSpinner';
import { ErrorBanner } from '../components/shared/ErrorBanner';
import { CohortHeatmap, cohortColor } from '../components/charts/CohortHeatmap';
import { HowItWorksPanel } from '../components/shared/HowItWorksPanel';
import { InterpretButton } from '../components/shared/InterpretButton';
import type {
  CohortCompareRequest,
  CohortDistance,
  WrapResult,
} from '../api/types';
import { OPERATOR_SHORT } from '../lib/constants';

type SubmittedProfile = { label: string; operator_scores: number[] };

const PROVIDERS = ['mock', 'openai', 'anthropic', 'google', 'meta', 'xai', 'deepseek', 'qwen'];

const CLUSTER_COLORS = ['#22d3ee', '#a78bfa', '#34d399', '#fbbf24', '#f87171', '#f472b6'];

const HOW_IT_WORKS_SECTIONS = [
  {
    title: 'How AI Model Comparison Works',
    body: (
      <p className="text-slate-300">
        This page compares how different AI models think about the same problems. Instead of just
        comparing accuracy, we compare <em>cognitive architecture</em> — the structural patterns of
        reasoning each model uses.
      </p>
    ),
  },
  {
    title: 'How to Use It',
    body: (
      <ol className="list-decimal list-inside space-y-1 text-slate-300">
        <li>Select two or more AI models from the dropdowns.</li>
        <li>If a model is already in your assessment history, its scores auto-load. Otherwise run it first.</li>
        <li>Or click <strong className="text-slate-100">Quick Compare</strong> to run the same prompt through all selected models at once.</li>
        <li>View the Alignment Heatmap to see how similarly they think.</li>
        <li>Check the Pairwise Comparison for detailed metrics and click any row's <strong className="text-accent-teal">✦ Interpret</strong> button for plain-English guidance.</li>
      </ol>
    ),
  },
  {
    title: 'What the Metrics Mean',
    body: (
      <ul className="list-disc list-inside space-y-1 text-slate-300">
        <li><strong className="text-slate-100">Alignment %:</strong> How similarly two models think (100% = identical, below 70% = very different).</li>
        <li><strong className="text-slate-100">Bhattacharyya Coefficient:</strong> Statistical overlap between cognitive distributions (1.0 = identical, 0.0 = no overlap).</li>
        <li><strong className="text-slate-100">Cognitive Distance:</strong> Geodesic distance on the probability simplex (0.0 = identical, higher = more different).</li>
        <li><strong className="text-slate-100">Clusters:</strong> Models grouped by thinking similarity.</li>
      </ul>
    ),
  },
  {
    title: 'Why This Matters',
    body: (
      <p className="text-slate-300">
        Different AI models have different cognitive strengths. A model strong in CO-3 (Critical
        Evaluation) is better for risk assessment. A model strong in CO-5 (Receptive Integration)
        is better for customer support. This comparison helps you choose the right model for the
        right task.
      </p>
    ),
  },
];

/** One slot in the comparison — a provider plus its loaded WrapResult (from history or quick-compare). */
interface ModelSlot {
  provider: string;            // e.g. "openai"
  displayName: string;         // e.g. "gpt-4o-mini" if known, else provider
  wrapResult: WrapResult | null;
  loading: boolean;
  error: string | null;
}

function emptySlot(provider = ''): ModelSlot {
  return { provider, displayName: provider, wrapResult: null, loading: false, error: null };
}

function scoresToDomainAverages(scores: number[]): number[] {
  // P=[0,1,4], C=[2,3,7], E=[5,6], O=[8,9]
  const map = [[0, 1, 4], [2, 3, 7], [5, 6], [8, 9]];
  const raw = map.map((indices) => {
    const avg = indices.reduce((sum, i) => sum + (scores[i] ?? 0.5), 0) / indices.length;
    return Math.max(0.001, avg);
  });
  const total = raw.reduce((a, b) => a + b, 0);
  return raw.map((v) => v / total);
}

/** Extract operator scores from a WrapResult. */
function extractOperatorScores(wr: WrapResult): number[] {
  return (wr.stages.find((s) => s.stage === 'operator_scoring')?.data?.scores as number[] | undefined) ?? [];
}

export function CohortPage() {
  const navigate = useNavigate();
  const historyRecords = useHistoryStore((s) => s.records);
  const cohort = useCohort();

  const [slots, setSlots] = useState<ModelSlot[]>([emptySlot('mock'), emptySlot('')]);
  const [comparePrompt, setComparePrompt] = useState('');
  const [quickCompareRunning, setQuickCompareRunning] = useState(false);
  const [submittedProfiles, setSubmittedProfiles] = useState<SubmittedProfile[]>([]);

  /** Look up the most recent history record that used this provider. */
  function latestFromHistoryForProvider(provider: string): WrapResult | null {
    if (!provider) return null;
    const match = historyRecords.find((r) => {
      const model = r.result.llm_response?.model ?? '';
      return (
        model.toLowerCase().includes(provider.toLowerCase()) ||
        provider.toLowerCase() === 'mock' && model.includes('mock')
      );
    });
    return match?.result ?? null;
  }

  function updateSlotProvider(idx: number, provider: string) {
    const next = [...slots];
    const fromHistory = latestFromHistoryForProvider(provider);
    next[idx] = {
      provider,
      displayName: fromHistory?.llm_response?.model ?? provider,
      wrapResult: fromHistory,
      loading: false,
      error: null,
    };
    setSlots(next);
  }

  function addSlot() {
    if (slots.length >= 6) return;
    setSlots([...slots, emptySlot('')]);
  }

  function removeSlot(idx: number) {
    if (slots.length <= 2) return;
    setSlots(slots.filter((_, i) => i !== idx));
  }

  const readySlots = slots.filter((s) => s.provider && s.wrapResult);
  const hasEnoughReady = readySlots.length >= 2;

  function handleCompare() {
    if (!hasEnoughReady) return;
    const profiles = readySlots.map((slot) => {
      const scores = extractOperatorScores(slot.wrapResult!);
      return {
        label: slot.displayName || slot.provider,
        operator_scores: scores.length === 10 ? scores : Array(10).fill(0.5),
        domain_averages: scoresToDomainAverages(scores),
      };
    });
    setSubmittedProfiles(
      profiles.map((p) => ({ label: p.label, operator_scores: p.operator_scores })),
    );
    const req: CohortCompareRequest = { profiles };
    cohort.mutate(req);
  }

  async function handleQuickCompare() {
    if (!comparePrompt.trim()) return;
    const providers = slots.map((s) => s.provider).filter((p) => p);
    if (providers.length < 2) return;

    setQuickCompareRunning(true);
    // Mark all slots as loading
    setSlots((prev) =>
      prev.map((slot) =>
        slot.provider ? { ...slot, loading: true, error: null } : slot,
      ),
    );

    // Run each provider sequentially — parallel would hammer API rate limits
    const updatedResults: (WrapResult | null)[] = [];
    const updatedErrors: (string | null)[] = [];
    for (let i = 0; i < slots.length; i++) {
      const slot = slots[i];
      if (!slot.provider) {
        updatedResults.push(null);
        updatedErrors.push(null);
        continue;
      }
      try {
        const res = await postWrap({
          text: comparePrompt,
          provider: slot.provider,
          mock: slot.provider === 'mock',
        });
        updatedResults.push(res);
        updatedErrors.push(null);
      } catch (e) {
        updatedResults.push(null);
        updatedErrors.push(e instanceof Error ? e.message : 'failed');
      }
    }

    setSlots((prev) =>
      prev.map((slot, i) => ({
        ...slot,
        loading: false,
        wrapResult: updatedResults[i] ?? slot.wrapResult,
        displayName: updatedResults[i]?.llm_response?.model ?? slot.displayName,
        error: updatedErrors[i],
      })),
    );
    setQuickCompareRunning(false);

    // After all results come in, auto-run compare
    const readyAfter = slots
      .map((slot, i) => ({ slot, wr: updatedResults[i] }))
      .filter((x) => x.wr);
    if (readyAfter.length >= 2) {
      const profiles = readyAfter.map((x) => {
        const scores = extractOperatorScores(x.wr!);
        return {
          label: x.wr!.llm_response?.model ?? x.slot.provider,
          operator_scores: scores.length === 10 ? scores : Array(10).fill(0.5),
          domain_averages: scoresToDomainAverages(scores),
        };
      });
      setSubmittedProfiles(
        profiles.map((p) => ({ label: p.label, operator_scores: p.operator_scores })),
      );
      cohort.mutate({ profiles });
    }
  }

  const result = cohort.data;

  // ── Interpretation generators (data-driven, not generic copy) ──
  const clusterInterpretation = useMemo(() => {
    if (!result) return '';
    const byCluster: Record<number, string[]> = {};
    result.clusters.forEach((c) => {
      (byCluster[c.cluster] ??= []).push(c.label);
    });
    const groups = Object.values(byCluster);
    if (groups.length === 1) {
      return `All ${result.clusters.length} models are in the same cluster — they think very similarly. You can treat them as near-interchangeable for most tasks; choose the cheapest or fastest.`;
    }
    const biggest = [...groups].sort((a, b) => b.length - a.length)[0];
    const outliers = groups.filter((g) => g !== biggest).flat();
    return (
      `Models are grouped by how similarly they think. ` +
      (biggest.length > 1
        ? `${biggest.join(' and ')} cluster together — their Cognitive Operator profiles are closely aligned, so picking between them is a marginal call. `
        : '') +
      (outliers.length > 0
        ? `${outliers.join(', ')} ${outliers.length === 1 ? 'sits' : 'sit'} in a different cluster because ${outliers.length === 1 ? 'it thinks' : 'they think'} about problems in a fundamentally different way on specific operators. Use ${outliers.length === 1 ? outliers[0] : 'those models'} when the task needs a different cognitive angle.`
        : '')
    );
  }, [result]);

  const alignmentInterpretation = useMemo(() => {
    if (!result || result.distances.length === 0) return '';
    const sorted = [...result.distances].sort((a, b) => b.alignment_pct - a.alignment_pct);
    const highest = sorted[0];
    const lowest = sorted[sorted.length - 1];
    return (
      `This heatmap shows how similarly each pair of models thinks. 100% means identical cognitive architecture. The diagonal is always 100% because every model is identical to itself. ` +
      `Highest pair: ${highest.from_label} and ${highest.to_label} align at ${highest.alignment_pct.toFixed(1)}% — they are nearly interchangeable for most tasks. ` +
      (highest !== lowest
        ? `Lowest pair: ${lowest.from_label} and ${lowest.to_label} align at ${lowest.alignment_pct.toFixed(1)}% — they have meaningfully different cognitive profiles and will diverge on non-trivial prompts.`
        : '')
    );
  }, [result]);

  function rowInterpretation(d: CohortDistance): string {
    // Look up per-model operator scores for this pair, then find the biggest gaps
    const fromProfile = submittedProfiles.find((p) => p.label === d.from_label);
    const toProfile = submittedProfiles.find((p) => p.label === d.to_label);
    let deltaNote = '';
    if (fromProfile && toProfile) {
      const diffs = OPERATOR_SHORT.map((short, i) => ({
        co: short,
        idx: i,
        delta: (fromProfile.operator_scores[i] ?? 0) - (toProfile.operator_scores[i] ?? 0),
      }));
      const fromStronger = [...diffs].sort((a, b) => b.delta - a.delta).slice(0, 2).filter((x) => x.delta > 0.08);
      const toStronger = [...diffs].sort((a, b) => a.delta - b.delta).slice(0, 2).filter((x) => x.delta < -0.08);
      if (fromStronger.length || toStronger.length) {
        deltaNote =
          ` ${d.from_label} scores higher on ${fromStronger.map((x) => x.co).join(', ') || 'nothing notable'}; ` +
          `${d.to_label} scores higher on ${toStronger.map((x) => x.co).join(', ') || 'nothing notable'}.`;
      }
    }

    const plain =
      d.alignment_pct >= 95
        ? `These models are nearly identical in how they think — pick either for most tasks.`
        : d.alignment_pct >= 85
        ? `${d.from_label} and ${d.to_label} are close, but they diverge on edge cases.`
        : d.alignment_pct >= 70
        ? `${d.from_label} and ${d.to_label} think differently enough to produce meaningfully different outputs.`
        : `${d.from_label} and ${d.to_label} have significantly different cognitive architectures.`;

    return (
      `${d.from_label} vs ${d.to_label}: ` +
      `Alignment ${d.alignment_pct.toFixed(1)}%, ` +
      `Bhattacharyya ${d.bhattacharyya_coefficient.toFixed(4)} (statistical overlap), ` +
      `Cognitive Distance ${d.geodesic_distance.toFixed(4)} (geodesic on the probability simplex). ` +
      plain +
      deltaNote
    );
  }

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <HowItWorksPanel sections={HOW_IT_WORKS_SECTIONS} label="How Model Comparison Works" />

      <div>
        <h2 className="text-xl font-bold text-slate-100">AI Model Comparison</h2>
        <p className="text-sm text-slate-400 mt-1">
          Compare the cognitive architectures of different AI models side by side. Select models,
          run the same prompt through each, and see how their thinking patterns align or diverge.
        </p>
      </div>

      {/* Model slot selector */}
      <Card title="Model Profiles">
        <div className="space-y-3">
          {slots.map((slot, i) => (
            <div key={i} className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <label className="text-[11px] text-slate-500 w-16 shrink-0">Model {i + 1}</label>
              <select
                value={slot.provider}
                onChange={(e) => updateSlotProvider(i, e.target.value)}
                className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-sm text-slate-300 focus:border-accent-teal/50 focus:outline-none min-h-[44px] sm:w-48"
              >
                <option value="" className="bg-dark-800">select provider...</option>
                {PROVIDERS.map((p) => (
                  <option key={p} value={p} className="bg-dark-800">{p}</option>
                ))}
              </select>
              <div className="flex-1 text-[11px]">
                {slot.loading ? (
                  <span className="text-slate-400">⏳ Running assessment...</span>
                ) : slot.error ? (
                  <span className="text-red-400">⚠ {slot.error}</span>
                ) : slot.wrapResult ? (
                  <span className="text-emerald-400">
                    ✅ Scores loaded · NCCS {slot.wrapResult.nccs.composite.toFixed(1)} · {slot.displayName}
                  </span>
                ) : slot.provider ? (
                  <span className="text-amber-400">
                    ⏳ No history yet ·{' '}
                    <button
                      onClick={() => navigate('/', { state: { providerHint: slot.provider } })}
                      className="underline hover:text-amber-300"
                    >
                      Run assessment first
                    </button>
                    {' '}or use Quick Compare below.
                  </span>
                ) : (
                  <span className="text-slate-600">— pick a provider —</span>
                )}
              </div>
              {slots.length > 2 && (
                <button
                  onClick={() => removeSlot(i)}
                  className="text-slate-600 hover:text-red-400 transition-colors text-xs px-2"
                >
                  Remove
                </button>
              )}
            </div>
          ))}

          <div className="flex flex-col gap-2 sm:flex-row pt-1">
            <button
              onClick={addSlot}
              disabled={slots.length >= 6}
              className="rounded-lg border border-white/[0.08] px-4 py-2 text-sm text-slate-400 hover:text-slate-200 hover:border-white/[0.15] transition-colors disabled:opacity-40"
            >
              + Add Model
            </button>
            <button
              onClick={handleCompare}
              disabled={cohort.isPending || !hasEnoughReady}
              className="rounded-lg bg-gradient-to-r from-accent-teal to-accent-cyan px-6 py-2 text-sm font-semibold text-dark-900 hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-opacity"
            >
              {cohort.isPending ? 'Comparing...' : `Compare ${readySlots.length || ''} Models`}
            </button>
          </div>
        </div>
      </Card>

      {/* Quick Compare — run same prompt through all selected providers at once */}
      <Card title="Quick Compare">
        <div className="space-y-3">
          <p className="text-[11px] text-slate-400">
            Enter one prompt below. We'll run it through every selected provider above, then
            compare the results automatically.
          </p>
          <textarea
            value={comparePrompt}
            onChange={(e) => setComparePrompt(e.target.value)}
            placeholder="Enter the prompt you want to compare models on..."
            rows={3}
            className="w-full rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:border-accent-teal/50 focus:outline-none resize-none"
          />
          <button
            onClick={handleQuickCompare}
            disabled={
              quickCompareRunning ||
              !comparePrompt.trim() ||
              slots.filter((s) => s.provider).length < 2
            }
            className="rounded-lg border border-accent-teal/30 bg-accent-teal/10 px-5 py-2 text-sm font-semibold text-accent-teal hover:bg-accent-teal/20 disabled:opacity-40 disabled:cursor-not-allowed transition-colors min-h-[44px]"
          >
            {quickCompareRunning ? 'Running assessments...' : '⚡ Quick Compare'}
          </button>
        </div>
      </Card>

      {cohort.isPending && <LoadingSpinner />}
      <ErrorBanner error={cohort.error as Error | null} />

      {/* Results */}
      {result && (
        <div className="space-y-5">
          {/* Cluster summary */}
          <Card
            title="Cluster Summary"
            action={<InterpretButton interpretation={clusterInterpretation} />}
          >
            <div className="space-y-3">
              <p className="text-sm text-slate-400">
                Models grouped by cognitive proximity. Models in the same cluster share similar
                cognitive architectures.
              </p>
              <div className="flex flex-wrap gap-2">
                {result.clusters.map((c) => (
                  <span
                    key={c.label}
                    className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[12px] font-medium border border-white/[0.06] bg-white/[0.02]"
                  >
                    <span
                      className="h-2 w-2 rounded-full"
                      style={{ backgroundColor: CLUSTER_COLORS[c.cluster % CLUSTER_COLORS.length] }}
                    />
                    {c.label}
                    <span className="text-[10px] text-slate-500 ml-0.5">Cluster {c.cluster + 1}</span>
                  </span>
                ))}
              </div>
            </div>
          </Card>

          {/* Heatmap */}
          <Card
            title="Alignment Heatmap"
            action={<InterpretButton interpretation={alignmentInterpretation} />}
          >
            <CohortHeatmap result={result} />
          </Card>

          {/* Distance table */}
          <Card title="Pairwise Comparison">
            <div className="overflow-x-auto">
              <table className="w-full text-[12px]">
                <thead>
                  <tr className="text-left text-slate-500 border-b border-white/[0.06]">
                    <th className="px-3 py-2">From</th>
                    <th className="px-3 py-2">To</th>
                    <th className="px-3 py-2">Alignment</th>
                    <th className="px-3 py-2">Similarity</th>
                    <th className="px-3 py-2">
                      Bhattacharyya
                      <span
                        className="ml-1 text-[10px] text-slate-600"
                        title="Statistical overlap coefficient between two probability distributions. Range 0-1 where 1 = identical distributions."
                      >
                        (?)
                      </span>
                    </th>
                    <th className="px-3 py-2">Cognitive Distance</th>
                    <th className="px-3 py-2 w-16"></th>
                  </tr>
                </thead>
                <tbody>
                  {result.distances.map((d, i) => (
                    <tr key={i} className="border-b border-white/[0.03] hover:bg-white/[0.02]">
                      <td className="px-3 py-2 text-slate-200 font-medium">{d.from_label}</td>
                      <td className="px-3 py-2 text-slate-200 font-medium">{d.to_label}</td>
                      <td className="px-3 py-2">
                        <span
                          className="font-mono font-bold"
                          style={{ color: cohortColor(d.alignment_pct, 'text') }}
                        >
                          {d.alignment_pct.toFixed(1)}%
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        <span
                          className="font-mono font-bold"
                          style={{ color: cohortColor(d.similarity_pct, 'text') }}
                        >
                          {d.similarity_pct.toFixed(1)}%
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        <span
                          className="font-mono font-bold"
                          style={{ color: cohortColor(d.bhattacharyya_coefficient * 100, 'text') }}
                        >
                          {d.bhattacharyya_coefficient.toFixed(4)}
                        </span>
                      </td>
                      <td className="px-3 py-2 font-mono text-slate-400">
                        {d.geodesic_distance.toFixed(4)}
                      </td>
                      <td className="px-3 py-2 text-right">
                        <InterpretButton interpretation={rowInterpretation(d)} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

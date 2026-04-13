import { useState, useEffect, useRef, useCallback, lazy, Suspense } from 'react';
import { useLocation } from 'react-router-dom';
import { useWrap } from '../hooks/useWrap';
import { useBenchmark } from '../hooks/useBenchmark';
import { BenchmarkResults } from '../components/shared/BenchmarkResults';
import { useTranslation } from '../hooks/useTranslation';
import { Card } from '../components/shared/Card';
import { LoadingSpinner } from '../components/shared/LoadingSpinner';
import { ErrorBanner } from '../components/shared/ErrorBanner';
import { CertBadge } from '../components/shared/CertBadge';
import { ExportButton } from '../components/shared/ExportButton';
import { ExplainPanel } from '../components/shared/ExplainPanel';
import { ExecutiveSummary } from '../components/shared/ExecutiveSummary';
import { AiBriefing } from '../components/shared/AiBriefing';
import { AiResponsePanel } from '../components/shared/AiResponsePanel';
import { FractalCard } from '../components/charts/FractalCard';
import { TraceViewer } from '../components/shared/TraceViewer';
import { NotationComposer } from '../components/shared/NotationComposer';
import { NotationDiff } from '../components/shared/NotationDiff';
import { SignalHeatmap } from '../components/shared/SignalHeatmap';
import { InversionAlert } from '../components/shared/InversionAlert';
import { BlindSpotCard } from '../components/shared/BlindSpotCard';
import { ConfidenceIndicator } from '../components/shared/ConfidenceIndicator';
import { InterpretButton } from '../components/shared/InterpretButton';
import { ResearchPrototypeNotice } from '../components/shared/ResearchPrototypeNotice';
import { PIPELINE_STAGES } from '../lib/constants';
import { computeBlindSpots } from '../lib/blindSpots';
import { interpretStage } from '../lib/interpretations';
import { interpretNccs, interpretSubScores, interpretOperators, interpretHeatmap, interpretDomainBalance, interpretExecutiveSummary, interpretStabilityAlerts, interpretBlindSpots, interpretDrives, interpretRpm, interpretInversions, interpretPipeline, interpretFractal, interpretTrace } from '../lib/cardInterpretations';
import { formatProviderLabel } from '../lib/providerLabels';
import { postAnalyzeText } from '../api/endpoints';
import type { LiveNotationResult } from '../api/endpoints';
import type { ScoringMode, WrapResult } from '../api/types';

const LazyNccsGauge = lazy(() => import('../components/charts/NccsGauge').then((m) => ({ default: m.NccsGauge })));
const LazySubScoreBreakdown = lazy(() => import('../components/charts/SubScoreBreakdown').then((m) => ({ default: m.SubScoreBreakdown })));
const LazyOperatorRadarChart = lazy(() => import('../components/charts/OperatorRadarChart').then((m) => ({ default: m.OperatorRadarChart })));
const LazyDomainCoherenceRadar = lazy(() => import('../components/charts/DomainCoherenceRadar').then((m) => ({ default: m.DomainCoherenceRadar })));
const LazyStateHeatmap = lazy(() => import('../components/charts/StateHeatmap').then((m) => ({ default: m.StateHeatmap })));
const LazyCoreDriveTree = lazy(() => import('../components/charts/CoreDriveTree').then((m) => ({ default: m.CoreDriveTree })));
const LazyRpmGraph = lazy(() => import('../components/charts/RpmGraph').then((m) => ({ default: m.RpmGraph })));
const LazyInversionMap = lazy(() => import('../components/charts/InversionMap').then((m) => ({ default: m.InversionMap })));

const PROVIDERS = ['mock', 'openai', 'anthropic', 'google', 'meta', 'xai', 'deepseek', 'qwen'];
const SCORER_PROVIDERS = PROVIDERS.filter((provider) => provider !== 'mock');

function getScoringMethodLabel(method: ScoringMode | undefined): string {
  switch (method) {
    case 'secondary_llm':
      return 'Secondary LLM assessor';
    case 'self_reported':
      return 'Self-reported inline scores';
    case 'heuristic_fallback':
    default:
      return 'Deterministic heuristic fallback';
  }
}

function getScoringMethodDescription(method: ScoringMode | undefined): string {
  switch (method) {
    case 'secondary_llm':
      return 'A second scoring call graded the generated response. If no scorer provider is configured, the backend may still fall back safely.';
    case 'self_reported':
      return 'The generating model embedded its own operator scores in the response. Treat this as self-assessment, not independent grading.';
    case 'heuristic_fallback':
    default:
      return 'Scores were derived from deterministic text heuristics. This avoids self-grading, but it is still a research-stage approximation.';
  }
}

function formatMeasurementLabel(metric: string): string {
  const labels: Record<string, string> = {
    social_engineering: 'Social engineering resistance',
    bias_flags: 'Bias flags',
  };
  return labels[metric] ?? metric.replace(/_/g, ' ');
}

function StageTimeline({ stages }: { stages: WrapResult['stages'] }) {
  const [selected, setSelected] = useState<number | null>(null);

  const insight = selected !== null ? interpretStage(stages[selected], selected) : null;

  return (
    <div className="space-y-2">
      {stages.map((s, i) => (
        <div
          key={i}
          className="flex items-center gap-3 animate-chart-in cursor-pointer rounded px-1 py-0.5 hover:bg-white/[0.02] transition-colors"
          style={{ animationDelay: `${i * 60}ms` }}
          onClick={() => setSelected(selected === i ? null : i)}
        >
          <div className="relative flex items-center justify-center w-5 h-5">
            {s.success ? (
              <>
                <div className="absolute inset-0 rounded-full bg-emerald-400/20" />
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                  <path d="M2.5 6L5 8.5L9.5 3.5" stroke="#34d399" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </>
            ) : (
              <>
                <div className="absolute inset-0 rounded-full bg-red-400/20" />
                <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                  <path d="M2.5 2.5L7.5 7.5M7.5 2.5L2.5 7.5" stroke="#f87171" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
              </>
            )}
          </div>
          <span className={`text-xs font-medium w-32 ${selected === i ? 'text-slate-100' : 'text-slate-300'}`}>
            {PIPELINE_STAGES[i]}
          </span>
          <div className="flex-1 h-1 rounded-full bg-white/[0.04] overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${s.success ? 'bg-emerald-400/40' : 'bg-red-400/40'}`}
              style={{ width: '100%', animationDelay: `${i * 80}ms` }}
            />
          </div>
          {s.error && <span className="text-[10px] text-red-400">{s.error}</span>}
        </div>
      ))}

      {insight && (
        <ExplainPanel visible={true} onClose={() => setSelected(null)}>
          <p className="font-medium text-slate-200">{insight.name}</p>
          <p>{insight.description}</p>
          <p className={insight.success ? 'text-emerald-400' : 'text-red-400'}>{insight.status}</p>
        </ExplainPanel>
      )}
    </div>
  );
}

export function AssessmentPage() {
  const [text, setText] = useState('');
  const [notation, setNotation] = useState('');
  const [provider, setProvider] = useState('mock');
  const [scoringMode, setScoringMode] = useState<ScoringMode>('heuristic_fallback');
  const [scoringProvider, setScoringProvider] = useState('auto');
  const [showAdvancedScoring, setShowAdvancedScoring] = useState(false);
  const [viewMode, setViewMode] = useState<'summary' | 'technical'>('summary');
  const [inputMode, setInputMode] = useState<'text' | 'compose'>('text');
  const [assessMode, setAssessMode] = useState<'single' | 'benchmark'>('single');
  const [benchProviders, setBenchProviders] = useState<string[]>(['mock']);
  const [runsPerProvider, setRunsPerProvider] = useState(5);
  const [liveNotation, setLiveNotation] = useState<LiveNotationResult | null>(null);
  const [liveNotationLoading, setLiveNotationLoading] = useState(false);
  const liveNotationAbort = useRef<AbortController | null>(null);
  const [expectedNotation, setExpectedNotation] = useState<string | null>(null);
  const [expectedEnglish, setExpectedEnglish] = useState<string | null>(null);
  const wrap = useWrap();
  const benchmark = useBenchmark();
  const location = useLocation();
  const benchResultsRef = useRef<HTMLDivElement>(null);
  const previousProviderRef = useRef(provider);

  // Accept prefilled prompt from navigation (e.g., from Scenario Browser)
  useEffect(() => {
    const state = location.state as { prefill?: string; notationPrefill?: string; notationEnglish?: string } | null;
    if (state?.prefill || state?.notationPrefill) {
      if (state?.prefill) {
        setText(state.prefill);
      }
      if (typeof state?.notationPrefill === 'string') {
        setNotation(state.notationPrefill);
        setExpectedNotation(state.notationPrefill);
      }
      if (typeof state?.notationEnglish === 'string') {
        setExpectedEnglish(state.notationEnglish);
      }
      setInputMode(state?.notationPrefill?.trim() ? 'compose' : 'text');
      window.history.replaceState({}, '');
    }
  }, [location.state]);

  useEffect(() => {
    if (previousProviderRef.current === provider) {
      return;
    }

    previousProviderRef.current = provider;
    if (provider === 'mock') {
      if (!showAdvancedScoring || scoringMode === 'secondary_llm') {
        setScoringMode('heuristic_fallback');
      }
      return;
    }

    if (!showAdvancedScoring || scoringMode === 'heuristic_fallback') {
      setScoringMode('secondary_llm');
    }
  }, [provider, scoringMode, showAdvancedScoring]);

  useEffect(() => {
    if (!showAdvancedScoring && scoringMode === 'self_reported') {
      setScoringMode(provider === 'mock' ? 'heuristic_fallback' : 'secondary_llm');
    }
  }, [provider, scoringMode, showAdvancedScoring]);

  // Live notation: debounce text input and call /notation/analyze
  useEffect(() => {
    const trimmed = text.trim();
    if (!trimmed || trimmed.length < 10) {
      setLiveNotation(null);
      return;
    }

    const timer = setTimeout(() => {
      // Abort any in-flight request
      liveNotationAbort.current?.abort();
      const controller = new AbortController();
      liveNotationAbort.current = controller;

      setLiveNotationLoading(true);
      postAnalyzeText(trimmed)
        .then((result) => {
          if (!controller.signal.aborted) {
            setLiveNotation(result);
            // Also sync the notation state so Compose tab reflects it
            if (result.source) {
              setNotation(result.source);
            }
          }
        })
        .catch(() => {
          // Silently ignore — network errors shouldn't block typing
        })
        .finally(() => {
          if (!controller.signal.aborted) {
            setLiveNotationLoading(false);
          }
        });
    }, 300);

    return () => {
      clearTimeout(timer);
    };
  }, [text]);

  function handleSubmit() {
    if (!text.trim()) return;
    if (assessMode === 'single') {
      wrap.mutate({
        text,
        provider,
        mock: provider === 'mock',
        scoring_mode: scoringMode,
        scoring_provider: scoringMode === 'secondary_llm' && scoringProvider !== 'auto' ? scoringProvider : null,
      });
    } else {
      if (benchProviders.length === 0) return;
      benchmark.mutate({ text, providers: benchProviders, runs_per_provider: runsPerProvider });
    }
  }

  function toggleBenchProvider(p: string) {
    setBenchProviders((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p],
    );
  }

  // Auto-scroll to benchmark results when they arrive
  useEffect(() => {
    if (benchmark.data && benchResultsRef.current) {
      benchResultsRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [benchmark.data]);

  const result = wrap.data;
  const translated = useTranslation(result);
  const scoringMethod = result?.scoring_method ?? result?.provenance?.scoring_method;
  const resolvedScorerProvider = typeof result?.provenance?.scorer_provider === 'string'
    ? result.provenance.scorer_provider
    : null;
  const resolvedScorerModel = typeof result?.provenance?.scorer_model === 'string'
    ? result.provenance.scorer_model
    : null;
  const notMeasured = result?.nccs.not_measured ?? [];
  const unmeasuredLabels = notMeasured.map(formatMeasurementLabel);

  const operatorScores = result?.stages.find(s => s.stage === 'operator_scoring')?.data?.scores as number[] | undefined;
  const domainAverages = result?.stages.find(s => s.stage === 'domain_coherence')?.data?.domain_averages as number[] | undefined;
  const driveScores = result?.stages.find(s => s.stage === 'rpm_gate')?.data?.drive_scores as number[][] | undefined;
  const a0Score = result?.stages.find(s => s.stage === 'rpm_gate')?.data?.a0_score as number | undefined;
  const rpmCompleteness = result?.stages.find(s => s.stage === 'rpm_gate')?.data?.rpm_completeness as number | undefined;
  const axisScores = result?.stages.find(s => s.stage === 'inversion_scan')?.data?.axis_scores as number[] | undefined;
  const stealthResistance = result?.stages.find(s => s.stage === 'inversion_scan')?.data?.stealth_resistance as number | undefined;

  const flatDrives = driveScores?.map(d => d[0]);
  const blindSpots = operatorScores && domainAverages
    ? computeBlindSpots(operatorScores, domainAverages, flatDrives)
    : [];
  const chartFallback = (
    <div className="flex min-h-[220px] items-center justify-center text-xs text-slate-500">
      Loading visualization...
    </div>
  );

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-xl font-bold text-slate-100">Assessment</h2>
        {/* Single / Benchmark mode toggle */}
        <div className="inline-flex rounded-lg border border-white/[0.08] bg-white/[0.03] p-1">
          <button
            onClick={() => setAssessMode('single')}
            className={`rounded-md px-4 py-1.5 text-xs font-semibold transition-all min-h-[36px] ${
              assessMode === 'single' ? 'bg-accent-teal/15 text-accent-teal' : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            Single Assessment
          </button>
          <button
            onClick={() => setAssessMode('benchmark')}
            className={`rounded-md px-4 py-1.5 text-xs font-semibold transition-all min-h-[36px] ${
              assessMode === 'benchmark' ? 'bg-accent-teal/15 text-accent-teal' : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            Benchmark Mode
          </button>
        </div>
      </div>

      <ConfidenceIndicator />
      <ResearchPrototypeNotice compact />

      <Card>
        {/* Tab switcher */}
        <div className="flex gap-1 mb-4">
          <button
            onClick={() => setInputMode('text')}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-all min-h-[36px] ${
              inputMode === 'text' ? 'bg-accent-teal/15 text-accent-teal' : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            Free Text
          </button>
          <button
            onClick={() => setInputMode('compose')}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-all min-h-[36px] ${
              inputMode === 'compose' ? 'bg-accent-teal/15 text-accent-teal' : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            Compose
          </button>
        </div>

        {/* Benchmark mode config — providers + runs, above the prompt field */}
        {assessMode === 'benchmark' && inputMode === 'text' && (
          <div className="space-y-3 mb-4 rounded-lg border border-accent-teal/20 bg-accent-teal/[0.04] p-4">
            <p className="text-[11px] text-slate-400">
              Run the prompt below through each selected provider multiple times and compare mean scores + variance.
            </p>
            <div>
              <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Providers</label>
              <div className="flex flex-wrap gap-2">
                    {PROVIDERS.map((p) => (
                      <button
                        key={p}
                    onClick={() => toggleBenchProvider(p)}
                    className={`px-3 py-2 rounded-lg text-xs font-medium transition-all min-h-[36px] ${
                      benchProviders.includes(p)
                        ? 'bg-accent-teal/20 text-accent-teal border border-accent-teal/40'
                        : 'bg-white/[0.04] text-slate-400 border border-white/10 hover:bg-white/[0.08]'
                    }`}
                    >
                    {formatProviderLabel(p)}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">Runs per Provider</label>
              <input
                type="number"
                min={2}
                max={20}
                value={runsPerProvider}
                onChange={(e) => setRunsPerProvider(Math.min(20, Math.max(2, Number(e.target.value))))}
                className="w-20 rounded-lg border border-white/10 bg-dark-700 px-3 py-2 text-sm text-slate-200 focus:border-accent-teal focus:outline-none focus:ring-1 focus:ring-accent-teal/30 min-h-[44px]"
              />
            </div>
          </div>
        )}

        {inputMode === 'text' ? (
          <div className="space-y-3">
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={assessMode === 'single' ? 'Enter text to assess...' : 'Enter prompt to benchmark across providers...'}
              rows={4}
              className="w-full rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3 text-base sm:text-sm text-slate-200 placeholder-slate-600 focus:border-accent-teal/50 focus:outline-none focus:ring-1 focus:ring-accent-teal/30 resize-none"
            />

            {/* Live CAS notation — updates as user types */}
            {(liveNotation || liveNotationLoading) && (
              <div className={`rounded-lg border p-3 transition-all ${liveNotation?.valid ? 'border-accent-teal/20 bg-accent-teal/[0.03]' : 'border-white/[0.06] bg-white/[0.02]'}`}>
                <div className="flex items-center gap-2 mb-1.5">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Live CAS Analysis</p>
                  {liveNotationLoading && (
                    <span className="text-[9px] text-slate-600 animate-pulse">analyzing...</span>
                  )}
                  {liveNotation?.valid && !liveNotationLoading && (
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400">compiler-validated</span>
                  )}
                </div>
                {liveNotation?.source ? (
                  <>
                    <p className="font-mono text-sm text-accent-teal tracking-wide">{liveNotation.source}</p>
                    {liveNotation.english && (
                      <p className="text-[11px] text-slate-400 mt-1.5 leading-relaxed">{liveNotation.english}</p>
                    )}
                    {liveNotation.signals && (
                      <div className="mt-3 pt-3 border-t border-white/[0.04]">
                        <SignalHeatmap
                          operatorScores={liveNotation.signals.operator_scores}
                          domainScores={liveNotation.signals.domain_scores}
                          driveScores={liveNotation.signals.drive_scores}
                          rpmSignal={liveNotation.signals.rpm_signal}
                        />
                      </div>
                    )}
                  </>
                ) : liveNotation && !liveNotationLoading ? (
                  <p className="text-[11px] text-slate-500">Keep typing — the system needs more text to detect CAS patterns...</p>
                ) : null}
              </div>
            )}
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              {assessMode === 'single' && (
                <>
                  <div className="flex-1 space-y-3">
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                      <label className="space-y-1">
                        <span className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500">Generator</span>
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
                        <span className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500">Scoring Mode</span>
                        <select
                          value={scoringMode}
                          onChange={(e) => setScoringMode(e.target.value as ScoringMode)}
                          className="w-full rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-sm text-slate-300 focus:border-accent-teal/50 focus:outline-none min-h-[44px]"
                        >
                          {provider !== 'mock' && (
                            <option value="secondary_llm" className="bg-dark-800">
                              Secondary LLM assessor (recommended)
                            </option>
                          )}
                          <option value="heuristic_fallback" className="bg-dark-800">Heuristic fallback</option>
                          {showAdvancedScoring && (
                            <option value="self_reported" className="bg-dark-800">Self-reported inline scores</option>
                          )}
                        </select>
                      </label>

                      <label className="space-y-1">
                        <span className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500">Scorer Provider</span>
                        <select
                          value={scoringProvider}
                          onChange={(e) => setScoringProvider(e.target.value)}
                          disabled={scoringMode !== 'secondary_llm'}
                          className="w-full rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-sm text-slate-300 focus:border-accent-teal/50 focus:outline-none min-h-[44px] disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          <option value="auto" className="bg-dark-800">Auto</option>
                          {SCORER_PROVIDERS.map((p) => (
                            <option key={p} value={p} className="bg-dark-800">{formatProviderLabel(p)}</option>
                          ))}
                        </select>
                      </label>
                    </div>

                    <label className="flex items-start gap-3 rounded-lg border border-white/[0.08] bg-white/[0.02] px-3 py-2">
                      <input
                        type="checkbox"
                        checked={showAdvancedScoring}
                        onChange={(e) => setShowAdvancedScoring(e.target.checked)}
                        className="mt-1 h-4 w-4 rounded border-white/[0.12] bg-dark-700 text-accent-teal focus:ring-accent-teal/40"
                      />
                      <span className="space-y-1">
                        <span className="block text-[11px] font-medium text-slate-300">Advanced scoring options</span>
                        <span className="block text-[11px] leading-relaxed text-slate-500">
                          Reveal self-reported scoring. This allows the generator to grade its own response and is not recommended for stakeholder-facing assessments.
                        </span>
                      </span>
                    </label>
                  </div>
                  {provider !== 'mock' && (
                    <span className="text-[10px] text-amber-400/80 flex items-center gap-1">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M12 9v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Live API — requires key in .env
                    </span>
                  )}
                </>
              )}
              {assessMode === 'benchmark' && (
                <span className="text-[11px] text-slate-500">
                  {benchProviders.length * runsPerProvider} assessments will run ({benchProviders.length} providers × {runsPerProvider} runs)
                </span>
              )}
              <button
                onClick={handleSubmit}
                disabled={
                  (assessMode === 'single' ? wrap.isPending : benchmark.isPending) ||
                  !text.trim() ||
                  (assessMode === 'benchmark' && benchProviders.length === 0)
                }
                className="rounded-lg bg-gradient-to-r from-accent-teal to-accent-cyan px-6 py-3 sm:py-2 text-sm font-semibold text-dark-900 hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-opacity min-h-[44px]"
              >
                {assessMode === 'single'
                  ? wrap.isPending ? 'Assessing...' : 'Assess'
                  : benchmark.isPending ? 'Running...' : 'Run Benchmark'}
              </button>
            </div>
            {assessMode === 'single' && (
              <div className="space-y-1 rounded-lg border border-white/[0.08] bg-white/[0.02] px-4 py-3">
                <p className="text-[11px] font-medium text-slate-300">{getScoringMethodLabel(scoringMode)}</p>
                <p className="text-[11px] leading-relaxed text-slate-500">
                  {getScoringMethodDescription(scoringMode)}
                </p>
                <div className="rounded-lg border border-white/[0.06] bg-dark-900/30 px-3 py-2 text-[10px] leading-relaxed text-slate-500">
                  <p className="font-semibold uppercase tracking-wider text-slate-400">Mode guidance</p>
                  <p className="mt-1">
                    Least-biased automated baseline: <span className="text-slate-300">heuristic_fallback</span>.
                    Best overall current mode: <span className="text-slate-300">secondary_llm</span> with a separate scorer.
                    Worst stakeholder comparison mode: <span className="text-slate-300">self_reported</span>.
                  </p>
                </div>
                {provider !== 'mock' && scoringMode === 'secondary_llm' && (
                  <p className="text-[10px] text-emerald-300/80">
                    Recommended default for live providers: a separate scorer reduces self-grading risk and makes report provenance clearer.
                  </p>
                )}
                {scoringMode === 'secondary_llm' && (
                  <p className="text-[10px] text-slate-500">
                    Auto prefers a different scorer provider when one is configured and available. Pick a scorer provider explicitly if you want a specific grading source.
                  </p>
                )}
                {scoringMode === 'self_reported' && (
                  <p className="text-[10px] text-amber-400/80">
                    Advanced warning: self-reported mode allows the generator to supply its own operator scores. Treat it as self-assessment only.
                  </p>
                )}
              </div>
            )}
          </div>
        ) : (
          <NotationComposer
            notation={notation}
            onNotationChange={setNotation}
            onGenerate={(prompt) => {
              setText(prompt);
              setInputMode('text');
            }}
          />
        )}
      </Card>

      {wrap.isPending && <LoadingSpinner />}
      <ErrorBanner error={wrap.error as Error | null} />

      {/* Benchmark mode: progress + results */}
      {assessMode === 'benchmark' && benchmark.isPending && (
        <div className="flex items-center gap-3 text-slate-400">
          <LoadingSpinner />
          <span className="text-sm">
            Running {benchProviders.length * runsPerProvider} assessments...
          </span>
        </div>
      )}
      {assessMode === 'benchmark' && <ErrorBanner error={benchmark.error as Error | null} />}
      {assessMode === 'benchmark' && benchmark.data && (
        <div ref={benchResultsRef} className="scroll-mt-4">
          <BenchmarkResults data={benchmark.data} />
        </div>
      )}

      {assessMode === 'single' && result && (
        <div className="space-y-6">
          <ResearchPrototypeNotice />

          {/* Show the actual AI response that was assessed. Collapsed by default. */}
          <AiResponsePanel llmResponse={result.llm_response} />

          <Card title="Scoring Provenance">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Method</p>
                <p className="mt-1 text-sm font-medium text-slate-200">{getScoringMethodLabel(scoringMethod)}</p>
              </div>
              <div className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Scorer Provider</p>
                <p className="mt-1 text-sm font-medium text-slate-200">{resolvedScorerProvider ?? 'Not used'}</p>
              </div>
              <div className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Scorer Model</p>
                <p className="mt-1 text-sm font-medium text-slate-200">{resolvedScorerModel ?? 'Not provided'}</p>
              </div>
            </div>
            <div className="mt-4 space-y-2 text-sm text-slate-400">
              <p>{getScoringMethodDescription(scoringMethod)}</p>
              <p className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-slate-400">
                Social engineering resistance and bias-flag counts are measured as heuristic risk signals. They are included in prototype scoring, but they are not validated instruments.
              </p>
              {scoringMethod === 'self_reported' && (
                <p className="rounded-lg border border-amber-400/20 bg-amber-400/10 px-3 py-2 text-amber-300">
                  This run used inline self-reporting from the generator response. Treat the scores as self-assessment, not independent grading.
                </p>
              )}
              {unmeasuredLabels.length > 0 && (
                <p className="rounded-lg border border-amber-400/20 bg-amber-400/10 px-3 py-2 text-amber-300">
                  Unmeasured dimensions: {unmeasuredLabels.join(', ')}. These metrics are not currently measured by the scoring pipeline.
                </p>
              )}
            </div>
          </Card>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-end sm:gap-3">
            {result.interpretation && (
              <button
                onClick={() => setViewMode(viewMode === 'summary' ? 'technical' : 'summary')}
                className="rounded-lg border border-white/[0.08] bg-white/[0.04] px-3 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-white/[0.08] transition-colors min-h-[44px]"
              >
                {viewMode === 'summary' ? 'Show Technical View' : 'Show Summary View'}
              </button>
            )}
            <ExportButton result={result} text={text} timestamp={new Date().toLocaleString()} />
          </div>

          {viewMode === 'summary' && result.interpretation && (
            <AiBriefing
              interpretation={result.interpretation}
              modelName={result.llm_response?.model ?? null}
            />
          )}

          {result.compiled_notation?.source && expectedNotation ? (
            <Card title="Notation Analysis: Expected vs. Computed">
              <NotationDiff
                expected={expectedNotation}
                expectedEnglish={expectedEnglish}
                computed={result.compiled_notation.source}
                computedEnglish={result.compiled_notation.english}
                computedValid={result.compiled_notation.valid}
              />
            </Card>
          ) : result.compiled_notation?.source ? (
            <Card title="CAS Notation (Computed)">
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  {result.compiled_notation.valid ? (
                    <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-medium">compiler-validated</span>
                  ) : (
                    <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 font-medium">unvalidated</span>
                  )}
                  <span className="text-[10px] text-slate-600">synthesized from pipeline results</span>
                </div>
                <p className="font-mono text-base text-accent-teal tracking-wide">{result.compiled_notation.source}</p>
                {result.compiled_notation.english && (
                  <p className="text-sm text-slate-400">{result.compiled_notation.english}</p>
                )}
              </div>
            </Card>
          ) : null}

          {(viewMode === 'technical' || !result.interpretation) && (
            <>
              <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
                <Card title="NCCS Score" action={<InterpretButton interpretation={interpretNccs(result.nccs)} />}>
                  <div className="flex flex-col items-center gap-4">
                    <Suspense fallback={chartFallback}>
                      <LazyNccsGauge composite={result.nccs.composite} certification={result.nccs.certification} nccs={result.nccs} />
                    </Suspense>
                    <CertBadge certification={result.nccs.certification} composite={result.nccs.composite} />
                  </div>
                </Card>
                <Card title="Sub-Score Breakdown" action={<InterpretButton interpretation={interpretSubScores(result.nccs)} />}>
                  <Suspense fallback={chartFallback}>
                    <LazySubScoreBreakdown nccs={result.nccs} />
                  </Suspense>
                </Card>
              </div>

              {/* Executive Summary (translated) */}
              {translated && (
                <Card title="Executive Summary" action={<InterpretButton interpretation={interpretExecutiveSummary()} />}>
                  <ExecutiveSummary data={translated} />
                </Card>
              )}

              <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
                {operatorScores && (
                  <Card title="Thinking Patterns" action={<InterpretButton interpretation={interpretOperators(operatorScores)} />}>
                    <Suspense fallback={chartFallback}>
                      <LazyOperatorRadarChart scores={operatorScores} />
                    </Suspense>
                  </Card>
                )}
                <Card title="Processing Balance" action={domainAverages ? <InterpretButton interpretation={interpretDomainBalance(domainAverages)} /> : undefined}>
                  <Suspense fallback={chartFallback}>
                    <LazyDomainCoherenceRadar result={result} />
                  </Suspense>
                </Card>
              </div>

              <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
                {operatorScores && domainAverages && (
                  <Card title="40-State Heatmap" action={<InterpretButton interpretation={interpretHeatmap(operatorScores, domainAverages)} />}>
                    <Suspense fallback={chartFallback}>
                      <LazyStateHeatmap operatorScores={operatorScores} domainAverages={domainAverages} />
                    </Suspense>
                  </Card>
                )}
                {/* Inversion Alert (Task 2) */}
                {axisScores && stealthResistance !== undefined && (
                  <Card title="Stability Alerts" action={<InterpretButton interpretation={interpretStabilityAlerts(axisScores)} />}>
                    <InversionAlert result={result} />
                  </Card>
                )}
              </div>

              {blindSpots.length > 0 && (
                <Card title="Cognitive Blind Spots" action={<InterpretButton interpretation={interpretBlindSpots(blindSpots)} />}>
                  <BlindSpotCard spots={blindSpots} />
                </Card>
              )}

              <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
                {driveScores && driveScores.length > 0 && (
                  <Card title="Core Drives" action={<InterpretButton interpretation={interpretDrives(driveScores.map(d => d[0]))} />}>
                    <Suspense fallback={chartFallback}>
                      <LazyCoreDriveTree driveScores={driveScores.map(d => d[0])} />
                    </Suspense>
                  </Card>
                )}
                {driveScores && a0Score !== undefined && rpmCompleteness !== undefined && (
                  <Card title="RPM Graph" action={<InterpretButton interpretation={interpretRpm(driveScores, a0Score, rpmCompleteness)} />}>
                    <Suspense fallback={chartFallback}>
                      <LazyRpmGraph
                        a0Score={a0Score}
                        driveScores={driveScores}
                        rpmCompleteness={rpmCompleteness}
                      />
                    </Suspense>
                  </Card>
                )}
                {axisScores && stealthResistance !== undefined && (
                  <Card title="Inversion Map" action={<InterpretButton interpretation={interpretInversions(axisScores, stealthResistance)} />}>
                    <Suspense fallback={chartFallback}>
                      <LazyInversionMap axisScores={axisScores} stealthResistance={stealthResistance} />
                    </Suspense>
                  </Card>
                )}
              </div>

              <Card title="Pipeline Stages" action={<InterpretButton interpretation={interpretPipeline(result.stages)} />}>
                <StageTimeline stages={result.stages} />
              </Card>

              {result.fractal_analysis && (
                <Card title="Cognitive Fractal" action={<InterpretButton interpretation={interpretFractal(result.fractal_analysis)} />}>
                  <FractalCard analysis={result.fractal_analysis} />
                </Card>
              )}

              <Card title="Evaluation Trace" action={<InterpretButton interpretation={interpretTrace(result.stages)} />}>
                <TraceViewer stages={result.stages} />
              </Card>
            </>
          )}
        </div>
      )}
    </div>
  );
}

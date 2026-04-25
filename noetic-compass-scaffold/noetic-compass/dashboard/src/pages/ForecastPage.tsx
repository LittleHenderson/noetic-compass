import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Card } from '../components/shared/Card';
import { LoadingSpinner } from '../components/shared/LoadingSpinner';
import { ErrorBanner } from '../components/shared/ErrorBanner';
import { postForecast, postWrap } from '../api/endpoints';
import type { ForecastRequest, ForecastResponse, ForecastRiskBand, WrapResult } from '../api/types';

const NOETIC_NAMES = [
  'Idea',
  'Mind',
  'Positive',
  'Negative',
  'Vibration',
  'Female',
  'Male',
  'Rhythm',
  'Above/Cause',
  'Below/Effect',
];

const DOMAIN_NAMES = ['Principled', 'Cognitive', 'Evaluative', 'Operational'];
const DRIVE_NAMES = ['Unity', 'Wisdom', 'Vitality', 'Connection', 'Agency', 'Structure', 'Purpose'];

const BALANCED_REQUEST: ForecastRequest = {
  context_label: 'Balanced reference',
  source: 'manual',
  operator_scores: [6, 6, 6, 6, 6, 6, 6, 6, 6, 6],
  domain_scores: [0.25, 0.25, 0.25, 0.25],
  drive_scores: [0.55, 0.55, 0.55, 0.55, 0.55, 0.55, 0.55],
  rpm_completeness: 0.9,
  fractal_sequence: [0, 2, 3, 5, 6, 8, 9],
};

const AGENCY_WITHOUT_GROUNDING: ForecastRequest = {
  context_label: 'Agency without grounding',
  source: 'research',
  operator_scores: [1, 1, 2, 2.5, 1, 2, 8, 1, 9, 1],
  domain_scores: [0.48, 0.35, 0.08, 0.09],
  drive_scores: [0.2, 0.05, 0.2, 0.1, 0.95, 0.1, 0.15],
  rpm_completeness: 0.25,
  fractal_sequence: [8, 6, 8, 6, 8],
  resolution_details: [],
};

const EVALUATIVE_BLIND_SPOT: ForecastRequest = {
  context_label: 'Evaluative blind spot',
  source: 'research',
  operator_scores: [7, 7.5, 7, 1.5, 6, 5.5, 8, 6.5, 8, 3],
  domain_scores: [0.43, 0.38, 0.05, 0.14],
  drive_scores: [0.55, 0.12, 0.35, 0.16, 0.7, 0.52, 0.24],
  rpm_completeness: 0.45,
  fractal_sequence: [0, 1, 6, 8],
  resolution_details: [],
};

const PRESETS = [
  {
    label: 'Healthy baseline',
    description: 'A low-risk reference profile with even coverage across the main CAS axes.',
    request: BALANCED_REQUEST,
  },
  {
    label: 'Too much push, not enough grounding',
    description: 'A profile that wants action quickly but lacks enough checks, judgment, and execution support.',
    request: AGENCY_WITHOUT_GROUNDING,
  },
  {
    label: 'Judgment blind spot',
    description: 'A profile that can reason and assert, but may weaken around value-laden ambiguity.',
    request: EVALUATIVE_BLIND_SPOT,
  },
] as const;

const EXAMPLE_TEXT =
  'Design a plan that moves fast, beats resistance, and explains why the outcome is inevitable. Avoid slowing down for objections unless they are obviously fatal.';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function stageData(result: WrapResult, stage: string): Record<string, unknown> {
  const data = result.stages.find((item) => item.stage === stage)?.data;
  return isRecord(data) ? data : {};
}

function asNumberArray(value: unknown, length: number, fallback: number[]): number[] {
  if (!Array.isArray(value)) return fallback;
  const nums = value.slice(0, length).map((item) => (typeof item === 'number' ? item : 0));
  return nums.length === length ? nums : fallback;
}

function flattenDriveScores(value: unknown): number[] {
  if (!Array.isArray(value)) return [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5];
  if (value.every((item) => typeof item === 'number')) {
    return asNumberArray(value, 7, [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]);
  }
  const flattened = value.slice(0, 7).map((item) => {
    if (Array.isArray(item) && typeof item[0] === 'number') return item[0];
    return 0;
  });
  return flattened.length === 7 ? flattened : [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5];
}

function extractForecastRequest(text: string, result: WrapResult): ForecastRequest {
  const operatorData = stageData(result, 'operator_scoring');
  const domainData = stageData(result, 'domain_coherence');
  const rpmData = stageData(result, 'rpm_gate');
  const normalizedScores = asNumberArray(operatorData.scores, 10, [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]);
  const rawFallback = normalizedScores.map((score) => Math.round(score * 10 * 100) / 100);
  const resolutionDetails = Array.isArray(rpmData.resolution_details)
    ? rpmData.resolution_details.filter(isRecord)
    : [];

  return {
    context_label: text.trim().slice(0, 120) || 'Wrap Pipeline forecast',
    source: 'wrap_pipeline',
    operator_scores: asNumberArray(operatorData.raw_scores_0_to_10, 10, rawFallback),
    domain_scores: asNumberArray(domainData.domain_averages, 4, [0.25, 0.25, 0.25, 0.25]),
    drive_scores: flattenDriveScores(rpmData.drive_scores),
    rpm_completeness: typeof rpmData.rpm_completeness === 'number' ? rpmData.rpm_completeness : 1,
    fractal_sequence: result.fractal_analysis?.dominant_sequence ?? [],
    resolution_details: resolutionDetails,
  };
}

function bandClasses(band: ForecastRiskBand): string {
  switch (band) {
    case 'low':
      return 'border-emerald-400/25 bg-emerald-400/[0.06] text-emerald-300';
    case 'watch':
      return 'border-accent-gold/25 bg-accent-gold/[0.07] text-accent-gold';
    case 'elevated':
      return 'border-orange-400/25 bg-orange-400/[0.07] text-orange-300';
    case 'high':
      return 'border-red-400/25 bg-red-400/[0.07] text-red-300';
  }
}

function bandMeaning(band: ForecastRiskBand): string {
  switch (band) {
    case 'low':
      return 'No major gap pattern is dominating this profile.';
    case 'watch':
      return 'There are some gaps worth checking before relying on the output.';
    case 'elevated':
      return 'Several structural gaps line up; run targeted tests before trusting this pattern.';
    case 'high':
      return 'The profile is heavily uneven; treat the top risks as active test priorities.';
  }
}

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function PlainLanguageGuide() {
  return (
    <div className="grid gap-3 md:grid-cols-3">
      {[
        ['1', 'Paste or pick an example', 'Use normal language. CAS extracts the structure behind it.'],
        ['2', 'Read the top risk first', 'The highest card tells you the most likely failure mode to test.'],
        ['3', 'Use checks, not guesses', 'Each result gives practical checks that can confirm or falsify the risk.'],
      ].map(([step, title, body]) => (
        <div key={step} className="rounded-xl border border-white/[0.08] bg-white/[0.03] p-4">
          <div className="mb-3 flex h-7 w-7 items-center justify-center rounded-full bg-accent-teal/15 text-xs font-bold text-accent-teal">
            {step}
          </div>
          <p className="text-sm font-semibold text-slate-100">{title}</p>
          <p className="mt-1 text-xs leading-relaxed text-slate-500">{body}</p>
        </div>
      ))}
    </div>
  );
}

function MetricBars({ title, names, values, max }: { title: string; names: string[]; values: number[]; max: number }) {
  return (
    <div>
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">{title}</p>
      <div className="space-y-2">
        {names.map((name, index) => {
          const value = values[index] ?? 0;
          const width = Math.max(2, Math.min(100, (value / max) * 100));
          return (
            <div key={name} className="grid grid-cols-[6rem_1fr_3rem] items-center gap-2 text-[11px]">
              <span className="truncate text-slate-400">{name}</span>
              <div className="h-2 overflow-hidden rounded-full bg-white/[0.05]">
                <div className="h-full rounded-full bg-gradient-to-r from-accent-teal to-accent-cyan" style={{ width: `${width}%` }} />
              </div>
              <span className="text-right font-mono text-slate-500">{max === 10 ? value.toFixed(1) : formatPercent(value)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ForecastSummary({ result }: { result: ForecastResponse }) {
  return (
    <Card className="overflow-hidden">
      <div className="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="rounded-xl border border-accent-teal/20 bg-gradient-to-br from-accent-teal/[0.14] via-accent-cyan/[0.08] to-transparent p-5">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-accent-teal">Overall risk level</p>
          <div className="mt-4 flex items-end gap-3">
            <span className="text-5xl font-black text-slate-100">{result.overall_risk_score.toFixed(1)}</span>
            <span className="pb-2 text-sm text-slate-500">/ 100</span>
          </div>
          <div className={`mt-4 inline-flex rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wider ${bandClasses(result.risk_band)}`}>
            {result.risk_band}
          </div>
          <p className="mt-4 text-sm leading-relaxed text-slate-400">
            {bandMeaning(result.risk_band)} This is a test-planning signal, not a deterministic prediction or clinical conclusion.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-lg border border-white/[0.08] bg-white/[0.03] p-4">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Gap pattern</p>
            <p className="mt-2 text-2xl font-bold text-slate-100">{result.lacunarity.classification}</p>
            <p className="mt-1 text-xs text-slate-500">Technical lacunarity score {result.lacunarity.composite.toFixed(2)}</p>
          </div>
          <div className="rounded-lg border border-white/[0.08] bg-white/[0.03] p-4">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Research status</p>
            <p className="mt-2 text-sm font-semibold text-accent-gold">{result.validation_status.replace(/_/g, ' ')}</p>
          </div>
          <div className="rounded-lg border border-white/[0.08] bg-white/[0.03] p-4 sm:col-span-2">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Main gaps to inspect</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {(result.dominant_structural_gaps.weak_noetics ?? []).map((item) => (
                <span key={`n-${item}`} className="rounded-full border border-cyan-400/20 bg-cyan-400/[0.06] px-2.5 py-1 text-[11px] text-cyan-200">{item}</span>
              ))}
              {(result.dominant_structural_gaps.weak_domains ?? []).map((item) => (
                <span key={`d-${item}`} className="rounded-full border border-emerald-400/20 bg-emerald-400/[0.06] px-2.5 py-1 text-[11px] text-emerald-200">Domain {item}</span>
              ))}
              {(result.dominant_structural_gaps.weak_drives ?? []).map((item) => (
                <span key={`f-${item}`} className="rounded-full border border-accent-gold/20 bg-accent-gold/[0.06] px-2.5 py-1 text-[11px] text-accent-gold">{item}</span>
              ))}
              {result.dominant_structural_gaps.largest_involution_gap && (
                <span className="rounded-full border border-red-400/20 bg-red-400/[0.06] px-2.5 py-1 text-[11px] text-red-200">
                  Involution gap: {result.dominant_structural_gaps.largest_involution_gap.pair}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

function ForecastCards({ result }: { result: ForecastResponse }) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {result.forecasts.map((forecast, index) => (
        <Card key={forecast.id} className="relative overflow-hidden">
          <div className="absolute right-4 top-4 text-5xl font-black text-white/[0.03]">{index + 1}</div>
          <div className="relative space-y-4">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-base font-semibold text-slate-100">{forecast.label}</p>
                <p className="mt-1 text-sm leading-relaxed text-slate-400">{forecast.summary}</p>
              </div>
              <div className={`shrink-0 rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wider ${bandClasses(forecast.risk_band)}`}>
                {forecast.risk_score}
              </div>
            </div>
            <div>
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Why this was flagged</p>
              <div className="space-y-1.5">
                {forecast.drivers.map((driver) => (
                  <p key={driver} className="rounded-lg border border-white/[0.06] bg-white/[0.025] px-3 py-2 text-xs text-slate-400">{driver}</p>
                ))}
              </div>
            </div>
            <div>
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">What to test next</p>
              <div className="space-y-1.5">
                {forecast.recommended_checks.map((check) => (
                  <p key={check} className="rounded-lg border border-accent-teal/15 bg-accent-teal/[0.04] px-3 py-2 text-xs text-slate-300">{check}</p>
                ))}
              </div>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}

export function ForecastPage() {
  const [text, setText] = useState(EXAMPLE_TEXT);
  const [result, setResult] = useState<ForecastResponse | null>(null);
  const [wrapSnapshot, setWrapSnapshot] = useState<WrapResult | null>(null);
  const [activeRequest, setActiveRequest] = useState<ForecastRequest>(BALANCED_REQUEST);
  const [showTechnicalInput, setShowTechnicalInput] = useState(false);

  const presetMutation = useMutation({
    mutationFn: (req: ForecastRequest) => postForecast(req),
    onSuccess(data) {
      setWrapSnapshot(null);
      setResult(data);
    },
  });

  const textMutation = useMutation({
    mutationFn: async (prompt: string) => {
      const wrap = await postWrap({
        text: prompt,
        provider: 'mock',
        mock: true,
        scoring_mode: 'heuristic_fallback',
      });
      const request = extractForecastRequest(prompt, wrap);
      const forecast = await postForecast(request);
      return { forecast, request, wrap };
    },
    onSuccess(data) {
      setActiveRequest(data.request);
      setWrapSnapshot(data.wrap);
      setResult(data.forecast);
    },
  });

  const isRunning = presetMutation.isPending || textMutation.isPending;
  const activeError = (presetMutation.error ?? textMutation.error) as Error | null;

  function runPreset(req: ForecastRequest) {
    setActiveRequest(req);
    presetMutation.mutate(req);
  }

  function runTextForecast() {
    if (!text.trim()) return;
    textMutation.mutate(text);
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="relative overflow-hidden rounded-2xl border border-accent-teal/20 bg-gradient-to-br from-dark-800 via-dark-900 to-dark-900 p-6 shadow-[0_0_50px_rgba(45,212,191,0.06)]">
        <div className="absolute -right-20 -top-28 h-72 w-72 rounded-full bg-accent-cyan/10 blur-3xl" />
        <div className="absolute -bottom-28 left-1/3 h-64 w-64 rounded-full bg-accent-teal/10 blur-3xl" />
        <div className="relative">
          <div className="mb-4 flex flex-wrap gap-2">
            <span className="rounded-full border border-accent-teal/25 bg-accent-teal/[0.08] px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-accent-teal">
              Research preview
            </span>
            <span className="rounded-full border border-accent-gold/25 bg-accent-gold/[0.08] px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-accent-gold">
              Not deterministic
            </span>
          </div>
          <h1 className="max-w-3xl text-3xl font-black tracking-tight text-slate-100 sm:text-4xl">
            Risk Forecast
          </h1>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-400">
            Find where a prompt, response pattern, or profile may break under pressure. CAS converts the underlying structure into ranked checks you can actually test.
          </p>
          <p className="mt-2 text-xs text-slate-600">
            Technical name: Predictive Lacunarity Risk.
          </p>
        </div>
      </div>

      <PlainLanguageGuide />

      <div className="grid gap-5 lg:grid-cols-[1fr_0.85fr]">
        <Card title="Check Text">
          <div className="space-y-4">
            <textarea
              value={text}
              onChange={(event) => setText(event.target.value)}
              rows={5}
              className="w-full resize-none rounded-xl border border-white/[0.08] bg-white/[0.03] px-4 py-3 text-sm leading-6 text-slate-200 placeholder-slate-600 outline-none transition-colors focus:border-accent-teal/50 focus:ring-1 focus:ring-accent-teal/30"
              placeholder="Enter a prompt or response pattern to assess..."
            />
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-xs leading-relaxed text-slate-500">
                Use normal language. The app handles the CAS metrics in the background.
              </p>
              <button
                onClick={runTextForecast}
                disabled={isRunning || !text.trim()}
                className="rounded-lg bg-gradient-to-r from-accent-teal to-accent-cyan px-5 py-2.5 text-sm font-semibold text-dark-900 transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {textMutation.isPending ? 'Running check...' : 'Run Risk Check'}
              </button>
            </div>
          </div>
        </Card>

        <Card title="Try Examples">
          <div className="space-y-3">
            {PRESETS.map((preset) => (
              <button
                key={preset.label}
                onClick={() => runPreset(preset.request)}
                disabled={isRunning}
                className="w-full rounded-xl border border-white/[0.08] bg-white/[0.03] p-4 text-left transition-colors hover:border-accent-teal/30 hover:bg-accent-teal/[0.04] disabled:cursor-not-allowed disabled:opacity-60"
              >
                <p className="text-sm font-semibold text-slate-100">{preset.label}</p>
                <p className="mt-1 text-xs leading-relaxed text-slate-500">{preset.description}</p>
              </button>
            ))}
          </div>
        </Card>
      </div>

      <Card
        title="Technical Input"
        action={
          <button
            onClick={() => setShowTechnicalInput((value) => !value)}
            className="rounded-lg border border-white/[0.08] bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-slate-400 transition-colors hover:bg-white/[0.08] hover:text-slate-200"
          >
            {showTechnicalInput ? 'Hide metrics' : 'Show metrics'}
          </button>
        }
      >
        {showTechnicalInput ? (
          <div className="grid gap-6 lg:grid-cols-3">
            <MetricBars title="Thinking patterns" names={NOETIC_NAMES} values={activeRequest.operator_scores} max={10} />
            <MetricBars title="Processing balance" names={DOMAIN_NAMES} values={activeRequest.domain_scores} max={1} />
            <MetricBars title="Motivational supports" names={DRIVE_NAMES} values={activeRequest.drive_scores} max={1} />
          </div>
        ) : (
          <p className="text-sm leading-relaxed text-slate-500">
            Hidden by default to keep the page readable. Open this when you need to audit the exact Noetic, domain, and drive inputs used for the forecast.
          </p>
        )}
      </Card>

      {isRunning && (
        <div className="flex items-center gap-3 rounded-xl border border-accent-teal/15 bg-accent-teal/[0.04] px-4 py-3 text-sm text-slate-300">
          <LoadingSpinner />
          Computing risk forecast...
        </div>
      )}

      <ErrorBanner error={activeError} />

      {result && (
        <div className="space-y-5">
          <ForecastSummary result={result} />

          {wrapSnapshot && (
            <Card title="Wrap Pipeline Source">
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-lg border border-white/[0.08] bg-white/[0.03] p-4">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">NCCS</p>
                  <p className="mt-2 text-2xl font-bold text-slate-100">{wrapSnapshot.nccs.composite.toFixed(1)}</p>
                </div>
                <div className="rounded-lg border border-white/[0.08] bg-white/[0.03] p-4">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Certification</p>
                  <p className="mt-2 text-lg font-semibold text-accent-teal">{wrapSnapshot.nccs.certification}</p>
                </div>
                <div className="rounded-lg border border-white/[0.08] bg-white/[0.03] p-4">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Scoring</p>
                  <p className="mt-2 text-sm font-semibold text-slate-200">{wrapSnapshot.scoring_method ?? 'heuristic_fallback'}</p>
                </div>
              </div>
            </Card>
          )}

          <ForecastCards result={result} />

          <Card title="What this can and cannot say">
            <div className="space-y-2">
              {result.limitations.map((limitation) => (
                <p key={limitation} className="rounded-lg border border-accent-gold/15 bg-accent-gold/[0.04] px-3 py-2 text-sm leading-relaxed text-slate-300">
                  {limitation}
                </p>
              ))}
              <p className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-xs leading-relaxed text-slate-500">
                Development stance: this can improve CAS by making gaps testable and actionable. It should not be marketed as mind reading, medical diagnosis, or guaranteed physical-behavior prediction.
              </p>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

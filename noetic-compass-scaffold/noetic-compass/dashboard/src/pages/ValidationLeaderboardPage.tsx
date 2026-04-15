import { useState, useMemo, type ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer,
} from 'recharts';
import { Card } from '../components/shared/Card';
import { LoadingSpinner } from '../components/shared/LoadingSpinner';
import { ErrorBanner } from '../components/shared/ErrorBanner';
import { InterpretButton } from '../components/shared/InterpretButton';
import { ResearchPrototypeNotice } from '../components/shared/ResearchPrototypeNotice';
import { formatProviderLabel } from '../lib/providerLabels';
import {
  getValidationCalibration,
  getValidationCatalog,
  getValidationEvidenceReview,
  getValidationEvidenceTrends,
  getValidationLeaderboard,
  getValidationStudies,
  postValidationBenchmarkCase,
  postValidationEvidenceSeed,
  postValidationErrorCase,
  postValidationRunBaseline,
  postValidationRunSuiteMatrix,
  postValidationScorerAgreement,
} from '../api/endpoints';
import type {
  BenchmarkSuiteSubmit,
  ErrorCaseSubmit,
  OperatorCorrelation,
  ScorerAgreementSubmit,
  ValidationAdminBaselineRequest,
  ValidationAdminSuiteMatrixRequest,
  ValidationCalibration,
  ValidationCatalogCollection,
  ValidationEvidenceReview,
  ValidationEvidenceTrendRow,
  ValidationEvidenceTrends,
  ValidationLeaderboard,
  ValidationStudyArtifact,
} from '../api/types';

function interpretLeaderboard(data: ValidationLeaderboard): string {
  const { stats, operator_correlations, inter_rater, recommendations } = data;
  const n = stats.total_labels;

  if (n === 0) {
    return (
      'No validations have been collected yet. Head to the Validation page and ' +
      'start scoring prompt-response pairs. Once you have around 10+ validations, ' +
      'meaningful correlation numbers will start appearing here.'
    );
  }

  if (n < 10) {
    return (
      `Only ${n} validation${n === 1 ? '' : 's'} so far. Correlation numbers need more ` +
      'data to mean anything — aim for at least 10 per operator before drawing conclusions. ' +
      'Keep validating.'
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
    raterNote = 'Only one rater has submitted validations so far — recruit a second rater to measure inter-rater reliability (Cohen\'s kappa).';
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

function EvidenceField({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="space-y-1">
      <span className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500">{label}</span>
      {children}
    </label>
  );
}

const FIELD_CLASS =
  'w-full rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-sm text-slate-300 focus:border-accent-teal/50 focus:outline-none min-h-[40px]';

function readEntryString(entry: Record<string, unknown>, key: string): string | null {
  const value = entry[key];
  return typeof value === 'string' && value.trim() ? value : null;
}

function readEntryNumber(entry: Record<string, unknown>, key: string): number | null {
  const value = entry[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function formatEntryTimestamp(entry: { timestamp?: string | null } | Record<string, unknown>): string {
  const timestamp = typeof entry.timestamp === 'string' && entry.timestamp.trim()
    ? entry.timestamp
    : readEntryString(entry as Record<string, unknown>, 'timestamp');
  if (!timestamp) return 'Timestamp unavailable';
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return timestamp;
  return date.toLocaleString();
}

function summarizeScorerAgreement(entry: Record<string, unknown>): string {
  const generator = readEntryString(entry, 'generator_provider') ?? 'unknown generator';
  const scorer = readEntryString(entry, 'scorer_provider') ?? 'unknown scorer';
  const machineScore = readEntryNumber(entry, 'machine_score');
  const scorerScore = readEntryNumber(entry, 'scorer_score');
  const scoreBits = machineScore != null && scorerScore != null
    ? `machine ${machineScore.toFixed(1)} vs scorer ${scorerScore.toFixed(1)}`
    : 'scores unavailable';
  return `${generator} generated, ${scorer} scored, ${scoreBits}.`;
}

function summarizeBenchmark(entry: Record<string, unknown>): string {
  const suite = readEntryString(entry, 'suite_name') ?? 'Unnamed suite';
  const provider = readEntryString(entry, 'provider') ?? 'unknown provider';
  const status = readEntryString(entry, 'status') ?? 'completed';
  const casesRun = readEntryNumber(entry, 'cases_run');
  const successes = readEntryNumber(entry, 'successes');
  const failures = readEntryNumber(entry, 'failures');
  const meanScore = readEntryNumber(entry, 'mean_score');
  const caseBits = casesRun != null ? `${casesRun} cases` : 'case count unavailable';
  const meanBits = meanScore != null ? `mean ${meanScore.toFixed(1)}` : 'mean unavailable';
  if (status !== 'completed' || (failures ?? 0) > 0) {
    return `${suite} on ${provider}, status=${status}, ${successes ?? 0} succeeded / ${failures ?? 0} failed, ${meanBits}.`;
  }
  return `${suite} on ${provider}, ${caseBits}, ${meanBits}.`;
}

function summarizeErrorCase(entry: Record<string, unknown>): string {
  const kind = readEntryString(entry, 'kind') ?? 'error_case';
  const expected = readEntryString(entry, 'expected_tier') ?? 'unknown expected tier';
  const observed = readEntryString(entry, 'observed_tier') ?? 'unknown observed tier';
  return `${kind.replace(/_/g, ' ')}: expected ${expected}, observed ${observed}.`;
}

function RecentEvidenceSection({
  title,
  emptyLabel,
  entries,
  summarize,
}: {
  title: string;
  emptyLabel: string;
  entries: Record<string, unknown>[];
  summarize: (entry: Record<string, unknown>) => string;
}) {
  return (
    <div className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{title}</p>
      <div className="mt-3 space-y-3">
        {entries.length === 0 ? (
          <p className="text-[11px] text-slate-500">{emptyLabel}</p>
        ) : (
          [...entries].reverse().map((entry, index) => (
            <div key={`${title}-${formatEntryTimestamp(entry)}-${index}`} className="rounded-lg border border-white/[0.06] bg-dark-900/30 px-3 py-2">
              <p className="text-[10px] uppercase tracking-wider text-slate-500">{formatEntryTimestamp(entry)}</p>
              <p className="mt-1 text-[11px] leading-relaxed text-slate-300">{summarize(entry)}</p>
              {readEntryString(entry, 'notes') && (
                <p className="mt-1 text-[10px] leading-relaxed text-slate-500">{readEntryString(entry, 'notes')}</p>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function formatTrendTimestamp(timestamp: string): string {
  if (!timestamp) return 'n/a';
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return timestamp;
  return date.toLocaleDateString();
}

function TrendTable({
  title,
  rows,
  labelKey,
}: {
  title: string;
  rows: ValidationEvidenceTrendRow[];
  labelKey: 'provider' | 'model';
}) {
  return (
    <div className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{title}</p>
      {rows.length === 0 ? (
        <p className="mt-3 text-[11px] text-slate-500">No trend data yet.</p>
      ) : (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[420px] text-[11px]">
            <thead>
              <tr className="border-b border-white/[0.06] text-left uppercase tracking-wider text-slate-500">
                <th className="pb-2 pr-3">{labelKey === 'provider' ? 'Provider' : 'Model'}</th>
                <th className="pb-2 pr-3 text-right">Entries</th>
                <th className="pb-2 pr-3 text-right">Gap</th>
                <th className="pb-2 pr-3 text-right">Bench</th>
                <th className="pb-2 pr-3 text-right">Fail</th>
                <th className="pb-2 pr-3 text-right">FP/FN</th>
                <th className="pb-2 text-right">Latest</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={`${labelKey}-${row[labelKey] ?? 'unknown'}`} className="border-b border-white/[0.03]">
                  <td className="py-2 pr-3 text-slate-300">{row[labelKey] ?? 'Unknown'}</td>
                  <td className="py-2 pr-3 text-right font-mono text-slate-300">{row.total_entries}</td>
                  <td className="py-2 pr-3 text-right font-mono text-slate-300">{row.mean_absolute_gap.toFixed(2)}</td>
                  <td className="py-2 pr-3 text-right font-mono text-slate-300">{row.benchmark_cases}</td>
                  <td className="py-2 pr-3 text-right font-mono text-slate-300">{row.failed_runs}</td>
                  <td className="py-2 pr-3 text-right font-mono text-slate-300">{row.false_positives}/{row.false_negatives}</td>
                  <td className="py-2 text-right text-slate-500">{formatTrendTimestamp(row.latest_timestamp)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function scoringModeLabel(mode?: string | null): string {
  switch (mode) {
    case 'secondary_llm':
      return 'External LLM scorer';
    case 'self_reported':
      return 'Self-reported';
    case 'heuristic_fallback':
    default:
      return 'Heuristic fallback';
  }
}

function scoringModeSummary(study: ValidationStudyArtifact): string {
  if (study.scoring_mode === 'secondary_llm') {
    const scorer = study.scoring_provider ?? 'unspecified scorer';
    const scorerModel = study.scoring_model ? ` / ${study.scoring_model}` : '';
    return `${scorer}${scorerModel}`;
  }
  return scoringModeLabel(study.scoring_mode);
}

function BenchmarkRankingTable({
  title,
  description,
  studies,
  footer,
}: {
  title: string;
  description: string;
  studies: ValidationStudyArtifact[];
  footer?: string;
}) {
  return (
    <Card title={title}>
      <div className="space-y-3">
        <p className="text-[11px] leading-relaxed text-slate-400">{description}</p>
        {studies.length === 0 ? (
          <p className="text-[11px] text-slate-500">
            No archived studies meet the current ranking threshold yet. Rankings only include successful runs with at least 10 prompts.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[840px] text-[11px]">
              <thead>
                <tr className="border-b border-white/[0.06] text-left uppercase tracking-wider text-slate-500">
                  <th className="pb-2 pr-3 text-right">Rank</th>
                  <th className="pb-2 pr-3">Provider</th>
                  <th className="pb-2 pr-3">Generator Model</th>
                  <th className="pb-2 pr-3">Scorer</th>
                  <th className="pb-2 pr-3 text-right">Prompts</th>
                  <th className="pb-2 pr-3 text-right">Mean</th>
                  <th className="pb-2 pr-3 text-right">Std</th>
                  <th className="pb-2 pr-3">Suite</th>
                  <th className="pb-2">Date</th>
                </tr>
              </thead>
              <tbody>
                {studies.map((study, index) => (
                  <tr key={study.filename} className="border-b border-white/[0.03]">
                    <td className="py-2 pr-3 text-right font-mono text-slate-300">{index + 1}</td>
                    <td className="py-2 pr-3 text-slate-300">{study.provider ?? 'unknown'}</td>
                    <td className="py-2 pr-3 text-slate-400">{study.model ?? 'n/a'}</td>
                    <td className="py-2 pr-3 text-slate-400">{scoringModeSummary(study)}</td>
                    <td className="py-2 pr-3 text-right font-mono text-slate-300">{study.prompt_count ?? 0}</td>
                    <td className="py-2 pr-3 text-right font-mono text-slate-200">
                      {typeof study.composite_mean === 'number' ? study.composite_mean.toFixed(2) : 'n/a'}
                    </td>
                    <td className="py-2 pr-3 text-right font-mono text-slate-400">
                      {typeof study.composite_std === 'number' ? study.composite_std.toFixed(2) : 'n/a'}
                    </td>
                    <td className="py-2 pr-3 text-slate-400">{study.study_label ?? study.filename}</td>
                    <td className="py-2 text-slate-500">{formatTrendTimestamp(study.study_date ?? '')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {footer && <p className="text-[10px] leading-relaxed text-slate-500">{footer}</p>}
      </div>
    </Card>
  );
}

function StatCard({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="glass-card p-4">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">{label}</p>
      <p className="text-2xl font-bold" style={{ color: color ?? '#e2e8f0' }}>{value}</p>
    </div>
  );
}

function statusBadge(status: string | null | undefined) {
  const normalized = status ?? 'unknown';
  const styles: Record<string, string> = {
    completed: 'bg-emerald-500/10 text-emerald-300',
    success: 'bg-emerald-500/10 text-emerald-300',
    partial: 'bg-amber-500/10 text-amber-300',
    failed: 'bg-rose-500/10 text-rose-300',
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${styles[normalized] ?? 'bg-slate-500/10 text-slate-300'}`}>
      {normalized}
    </span>
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
  const queryClient = useQueryClient();
  const [sortField, setSortField] = useState<'name' | 'r' | 'n'>('r');
  const [selectedOp, setSelectedOp] = useState<number | null>(null);
  const [evidenceStatus, setEvidenceStatus] = useState<string | null>(null);
  const [reviewKind, setReviewKind] = useState<string>('all');
  const [reviewProvider, setReviewProvider] = useState<string>('all');
  const [reviewModel, setReviewModel] = useState<string>('all');
  const [reviewQuery, setReviewQuery] = useState('');
  const [baselineRunForm, setBaselineRunForm] = useState<ValidationAdminBaselineRequest>({
    provider: 'xai',
    prompt_collection: 'sample_prompts',
    count: 10,
    label: '',
    model: '',
    scoring_mode: 'secondary_llm',
    scoring_provider: '',
    scoring_model: '',
    reseed: true,
  });
  const [matrixRunForm, setMatrixRunForm] = useState<ValidationAdminSuiteMatrixRequest>({
    provider: 'xai',
    suite_ids: ['sample_prompts', 'ai_safety', 'adversarial_resilience', 'finance', 'healthcare'],
    count_per_suite: 10,
    model: '',
    scoring_mode: 'heuristic_fallback',
    scoring_provider: '',
    scoring_model: '',
    reseed: true,
  });
  const [scorerForm, setScorerForm] = useState<ScorerAgreementSubmit>({
    generator_provider: '',
    generator_model: '',
    scorer_provider: '',
    scorer_model: '',
    prompt_excerpt: '',
    machine_score: 5,
    scorer_score: 5,
    notes: '',
    item_index: null,
  });
  const [benchmarkForm, setBenchmarkForm] = useState<BenchmarkSuiteSubmit>({
    suite_name: '',
    provider: '',
    model: '',
    scoring_mode: 'heuristic_fallback',
    scoring_provider: '',
    scoring_model: '',
    cases_run: 1,
    mean_score: 50,
    variance: 0,
    notes: '',
  });
  const [errorCaseForm, setErrorCaseForm] = useState<ErrorCaseSubmit>({
    kind: 'false_positive',
    provider: '',
    model: '',
    prompt_excerpt: '',
    expected_tier: '',
    observed_tier: '',
    notes: '',
    item_index: null,
  });

  const { data, isLoading, error } = useQuery({
    queryKey: ['validation-leaderboard'],
    queryFn: getValidationLeaderboard,
    refetchInterval: 10_000,  // Real-time: poll every 10s
  });

  const { data: evidenceReview, isLoading: reviewLoading, error: reviewError } = useQuery({
    queryKey: ['validation-evidence-review', reviewKind, reviewProvider, reviewModel, reviewQuery],
    queryFn: () => getValidationEvidenceReview({
      kind: reviewKind === 'all' ? undefined : reviewKind,
      provider: reviewProvider === 'all' ? undefined : reviewProvider,
      model: reviewModel === 'all' ? undefined : reviewModel,
      q: reviewQuery.trim() || undefined,
      limit: 50,
      offset: 0,
    }),
    refetchInterval: 10_000,
  });

  const { data: evidenceTrends, isLoading: trendsLoading, error: trendsError } = useQuery({
    queryKey: ['validation-evidence-trends'],
    queryFn: getValidationEvidenceTrends,
    refetchInterval: 10_000,
  });

  const { data: calibrationData, isLoading: calibrationLoading, error: calibrationError } = useQuery({
    queryKey: ['validation-calibration'],
    queryFn: getValidationCalibration,
    refetchInterval: 10_000,
  });

  const { data: catalogData } = useQuery({
    queryKey: ['validation-catalog'],
    queryFn: getValidationCatalog,
    staleTime: 60_000,
  });

  const { data: studyData, isLoading: studiesLoading, error: studiesError } = useQuery({
    queryKey: ['validation-studies'],
    queryFn: getValidationStudies,
    refetchInterval: 10_000,
  });

  const invalidateValidationQueries = () => {
    queryClient.invalidateQueries({ queryKey: ['validation-leaderboard'] });
    queryClient.invalidateQueries({ queryKey: ['validation-evidence-review'] });
    queryClient.invalidateQueries({ queryKey: ['validation-evidence-trends'] });
    queryClient.invalidateQueries({ queryKey: ['validation-calibration'] });
    queryClient.invalidateQueries({ queryKey: ['validation-studies'] });
  };

  const scorerAgreementMutation = useMutation({
    mutationFn: postValidationScorerAgreement,
    onSuccess: () => {
      setEvidenceStatus('Saved scorer-agreement evidence.');
      setScorerForm({
        generator_provider: '',
        generator_model: '',
        scorer_provider: '',
        scorer_model: '',
        prompt_excerpt: '',
        machine_score: 5,
        scorer_score: 5,
        notes: '',
        item_index: null,
      });
      invalidateValidationQueries();
    },
  });

  const benchmarkMutation = useMutation({
    mutationFn: postValidationBenchmarkCase,
    onSuccess: () => {
      setEvidenceStatus('Saved benchmark-suite evidence.');
      setBenchmarkForm({
        suite_name: '',
        provider: '',
        model: '',
        scoring_mode: 'heuristic_fallback',
        scoring_provider: '',
        scoring_model: '',
        cases_run: 1,
        mean_score: 50,
        variance: 0,
        notes: '',
      });
      invalidateValidationQueries();
    },
  });

  const errorCaseMutation = useMutation({
    mutationFn: postValidationErrorCase,
    onSuccess: () => {
      setEvidenceStatus('Saved false-positive/false-negative evidence.');
      setErrorCaseForm({
        kind: 'false_positive',
        provider: '',
        model: '',
        prompt_excerpt: '',
        expected_tier: '',
        observed_tier: '',
        notes: '',
        item_index: null,
      });
      invalidateValidationQueries();
    },
  });

  const seedEvidenceMutation = useMutation({
    mutationFn: () => postValidationEvidenceSeed(true),
    onSuccess: (seedResult) => {
      setEvidenceStatus(
        `Seeded evidence from current artifacts: ${seedResult.counts.scorer_agreement} scorer-agreement, ` +
        `${seedResult.counts.benchmark_suites} benchmark, ${seedResult.counts.error_cases} error-case entries.`,
      );
      invalidateValidationQueries();
    },
    onError: (err) => setEvidenceStatus(err instanceof Error ? err.message : 'Failed to seed evidence from artifacts.'),
  });

  const runBaselineMutation = useMutation({
    mutationFn: postValidationRunBaseline,
    onSuccess: (result) => {
      const summary = result.summary as Record<string, unknown>;
      setEvidenceStatus(
        `Baseline run ${String(summary.status ?? 'completed')} for ${formatProviderLabel(String(summary.provider ?? baselineRunForm.provider))} / ${String(summary.study_label ?? baselineRunForm.prompt_collection)} ` +
        `(${String(summary.successes ?? 0)} succeeded, ${String(summary.failures ?? 0)} failed).`,
      );
      invalidateValidationQueries();
    },
    onError: (err) => setEvidenceStatus(err instanceof Error ? err.message : 'Failed to run baseline study.'),
  });

  const runMatrixMutation = useMutation({
    mutationFn: postValidationRunSuiteMatrix,
    onSuccess: (result) => {
      setEvidenceStatus(
        `Suite matrix complete for ${formatProviderLabel(result.provider)}: ${result.success_count} success, ${result.partial_count} partial, ${result.failed_count} failed.`,
      );
      invalidateValidationQueries();
    },
    onError: (err) => setEvidenceStatus(err instanceof Error ? err.message : 'Failed to run suite matrix.'),
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

  const collections: ValidationCatalogCollection[] = catalogData?.collections ?? [];
  const studies: ValidationStudyArtifact[] = studyData?.studies ?? [];
  const stakeholderEligibleStudies = useMemo(
    () =>
      studies
        .filter((study) => (study.prompt_count ?? 0) >= 10)
        .filter((study) => (study.failures ?? 0) === 0)
        .filter((study) => study.status === 'success' || study.status === 'completed')
        .filter((study) => typeof study.composite_mean === 'number')
        .sort((a, b) => {
          const meanDelta = Number(b.composite_mean ?? 0) - Number(a.composite_mean ?? 0);
          if (Math.abs(meanDelta) > 1e-9) return meanDelta;
          return (a.composite_std ?? Number.POSITIVE_INFINITY) - (b.composite_std ?? Number.POSITIVE_INFINITY);
        }),
    [studies],
  );
  const heuristicBenchmarkStudies = useMemo(
    () =>
      stakeholderEligibleStudies.filter(
        (study) => (study.scoring_mode ?? 'heuristic_fallback') === 'heuristic_fallback',
      ),
    [stakeholderEligibleStudies],
  );
  const externalScorerStudies = useMemo(
    () =>
      stakeholderEligibleStudies.filter(
        (study) =>
          study.scoring_mode === 'secondary_llm'
          && !!study.scoring_provider
          && study.scoring_provider !== study.provider,
      ),
    [stakeholderEligibleStudies],
  );
  const fixedExternalScorerProviders = useMemo(
    () => [...new Set(externalScorerStudies.map((study) => study.scoring_provider).filter(Boolean))],
    [externalScorerStudies],
  );

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorBanner error={error as Error} />;
  if (!data) return null;

  const { stats, operator_correlations, inter_rater, calibration, recommendations, evidence_summary: evidence } = data;
  const reviewData: ValidationEvidenceReview | null = evidenceReview?.review ?? null;
  const trendData: ValidationEvidenceTrends | null = evidenceTrends ?? null;
  const calibrationReview: ValidationCalibration | null = calibrationData ?? calibration ?? null;
  const exportQuery = new URLSearchParams();
  if (reviewKind !== 'all') exportQuery.set('kind', reviewKind);
  if (reviewProvider !== 'all') exportQuery.set('provider', reviewProvider);
  if (reviewModel !== 'all') exportQuery.set('model', reviewModel);
  if (reviewQuery.trim()) exportQuery.set('q', reviewQuery.trim());
  const exportSuffix = exportQuery.toString() ? `&${exportQuery.toString()}` : '';

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

      <ResearchPrototypeNotice compact />

      <Card title="Benchmark Mode Guidance">
        <div className="space-y-4">
          <p className="text-[11px] leading-relaxed text-slate-400">
            There is no zero-bias scoring mode. Use different tables for different scoring modes and do not collapse them into a single ranking.
          </p>
          <div className="grid gap-3 lg:grid-cols-3">
            <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/[0.05] px-4 py-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-300">Best least-biased automated baseline</p>
              <p className="mt-1 text-sm font-medium text-slate-100">heuristic_fallback</p>
              <p className="mt-2 text-[11px] leading-relaxed text-slate-400">
                Avoids model-as-judge bias entirely. Tradeoff: structurally consistent, but less semantically rich than an external assessor.
              </p>
            </div>
            <div className="rounded-lg border border-accent-teal/20 bg-accent-teal/[0.05] px-4 py-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-accent-teal">Best overall current mode</p>
              <p className="mt-1 text-sm font-medium text-slate-100">secondary_llm + separate scorer</p>
              <p className="mt-2 text-[11px] leading-relaxed text-slate-400">
                Richer than heuristics, but only honest if the scorer is external to the generator. Same-provider judging reintroduces bias.
              </p>
            </div>
            <div className="rounded-lg border border-amber-400/20 bg-amber-400/[0.05] px-4 py-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-amber-300">Worst stakeholder comparison mode</p>
              <p className="mt-1 text-sm font-medium text-slate-100">self_reported</p>
              <p className="mt-2 text-[11px] leading-relaxed text-slate-400">
                The generating model grades its own response. Keep it out of ranking tables and stakeholder claims.
              </p>
            </div>
          </div>
          <div className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Stakeholder-facing protocol</p>
            <ol className="mt-2 list-decimal space-y-1 pl-4 text-[11px] leading-relaxed text-slate-400">
              <li>Run a frozen prompt set in <code className="text-slate-300">heuristic_fallback</code> for all providers.</li>
              <li>Run the same prompt set in <code className="text-slate-300">secondary_llm</code> with one fixed external scorer.</li>
              <li>Have humans review disagreement cases in the calibration workflow on <code className="text-slate-300">ValidationPage.tsx</code>.</li>
              <li>Report heuristic, external-LLM, and human reconciliation results separately.</li>
            </ol>
          </div>
        </div>
      </Card>

      {/* Headline stats */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <StatCard label="Validations Collected" value={stats.total_labels} />
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

      {evidence && (
        <Card title="Validation Evidence Coverage">
          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Scorer Agreement</p>
              <p className="mt-1 text-lg font-bold text-slate-100">{evidence.scorer_agreement.count}</p>
              <p className="mt-1 text-[11px] text-slate-400">
                Mean absolute gap: {(evidence.scorer_agreement.mean_absolute_gap ?? 0).toFixed(3)}
              </p>
            </div>
            <div className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Benchmark Suites</p>
              <p className="mt-1 text-lg font-bold text-slate-100">{evidence.benchmark_suites.count}</p>
              <p className="mt-1 text-[11px] text-slate-400">
                Cases logged: {evidence.benchmark_suites.cases_run} | Failed runs: {evidence.benchmark_suites.failed_runs ?? 0}
              </p>
            </div>
            <div className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Error Cases</p>
              <p className="mt-1 text-lg font-bold text-slate-100">{evidence.error_cases.count}</p>
              <p className="mt-1 text-[11px] text-slate-400">
                FP: {evidence.error_cases.false_positives} | FN: {evidence.error_cases.false_negatives}
              </p>
            </div>
          </div>
          <p className="mt-3 text-[11px] leading-relaxed text-slate-500">
            Human-rater agreement is tracked above. Additional scorer-agreement, benchmark-suite, and false
            positive/negative evidence can now be logged through the validation API and will accumulate here.
          </p>
        </Card>
      )}

      <BenchmarkRankingTable
        title="Neutral Benchmark Table — Heuristic Fallback"
        description="Use this table as the least-biased automated baseline. It avoids model-as-judge bias and only includes successful archived runs with at least 10 prompts."
        studies={heuristicBenchmarkStudies}
        footer="Keep this table separate from external-LLM scorer results. Mixing scoring modes in one ranking table produces misleading comparisons."
      />

      <BenchmarkRankingTable
        title="External-Scorer Benchmark Table — Secondary LLM"
        description={
          fixedExternalScorerProviders.length === 1
            ? `These rankings use secondary_llm with one fixed external scorer: ${fixedExternalScorerProviders[0]}. Only runs where the scorer provider differs from the generator are included.`
            : 'These rankings use secondary_llm only when the scorer provider differs from the generator. Fix the scorer provider before showing stakeholders a single-table comparison.'
        }
        studies={externalScorerStudies}
        footer="Do not compare these numbers directly against the heuristic table without labeling the mode. The protocol is to present the tables side by side, then review disagreement cases with humans."
      />

      <Card title="Operational Workflows">
        <div className="space-y-5">
          <p className="text-[11px] leading-relaxed text-slate-500">
            Use these controls to generate archived study artifacts and reseed evidence from them. A live-provider run only counts as real external evidence if it actually succeeds; failed runs are still archived and surfaced so provider blockers are visible.
          </p>
          <div className="grid gap-4 xl:grid-cols-2">
            <form
              className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3 space-y-3"
              onSubmit={(e) => {
                e.preventDefault();
                runBaselineMutation.mutate({
                  ...baselineRunForm,
                  label: baselineRunForm.label?.trim() || null,
                  model: baselineRunForm.model?.trim() || null,
                  scoring_provider: baselineRunForm.scoring_provider?.trim() || null,
                  scoring_model: baselineRunForm.scoring_model?.trim() || null,
                });
              }}
            >
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Run Baseline + Reseed</p>
              <div className="grid gap-3 md:grid-cols-2">
                <EvidenceField label="Provider">
                  <input
                    className={FIELD_CLASS}
                    value={baselineRunForm.provider}
                    onChange={(e) => setBaselineRunForm({ ...baselineRunForm, provider: e.target.value })}
                  />
                </EvidenceField>
                <EvidenceField label="Prompt Collection">
                  <select
                    className={FIELD_CLASS}
                    value={baselineRunForm.prompt_collection}
                    onChange={(e) => setBaselineRunForm({ ...baselineRunForm, prompt_collection: e.target.value })}
                  >
                    {collections.map((collection) => (
                      <option key={collection.id} value={collection.id}>{collection.label}</option>
                    ))}
                  </select>
                </EvidenceField>
                <EvidenceField label="Prompt Count">
                  <input
                    className={FIELD_CLASS}
                    type="number"
                    min={1}
                    max={500}
                    value={baselineRunForm.count}
                    onChange={(e) => setBaselineRunForm({ ...baselineRunForm, count: Number(e.target.value) })}
                  />
                </EvidenceField>
                <EvidenceField label="Scoring Mode">
                  <select
                    className={FIELD_CLASS}
                    value={baselineRunForm.scoring_mode ?? 'secondary_llm'}
                    onChange={(e) => setBaselineRunForm({ ...baselineRunForm, scoring_mode: e.target.value as ValidationAdminBaselineRequest['scoring_mode'] })}
                  >
                    <option value="secondary_llm">secondary_llm</option>
                    <option value="heuristic_fallback">heuristic_fallback</option>
                    <option value="self_reported">self_reported</option>
                  </select>
                </EvidenceField>
                <EvidenceField label="Model (optional)">
                  <input
                    className={FIELD_CLASS}
                    value={baselineRunForm.model ?? ''}
                    onChange={(e) => setBaselineRunForm({ ...baselineRunForm, model: e.target.value })}
                  />
                </EvidenceField>
                <EvidenceField label="Study Label (optional)">
                  <input
                    className={FIELD_CLASS}
                    value={baselineRunForm.label ?? ''}
                    onChange={(e) => setBaselineRunForm({ ...baselineRunForm, label: e.target.value })}
                  />
                </EvidenceField>
              </div>
              <p className="text-[10px] leading-relaxed text-slate-500">
                For stakeholder-facing comparisons, use at least 10 frozen prompts. Keep heuristic and external-scorer runs in separate tables, and avoid self-reported runs entirely.
              </p>
              <button
                type="submit"
                disabled={runBaselineMutation.isPending}
                className="rounded-lg bg-gradient-to-r from-accent-teal to-accent-cyan px-4 py-2 text-sm font-semibold text-dark-900 hover:opacity-90 disabled:opacity-50"
              >
                {runBaselineMutation.isPending ? 'Running...' : 'Run Baseline + Reseed'}
              </button>
            </form>

            <form
              className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3 space-y-3"
              onSubmit={(e) => {
                e.preventDefault();
                runMatrixMutation.mutate({
                  ...matrixRunForm,
                  suite_ids: matrixRunForm.suite_ids?.length ? matrixRunForm.suite_ids : undefined,
                  model: matrixRunForm.model?.trim() || null,
                  scoring_provider: matrixRunForm.scoring_provider?.trim() || null,
                  scoring_model: matrixRunForm.scoring_model?.trim() || null,
                });
              }}
            >
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Run Suite Matrix + Reseed</p>
              <div className="grid gap-3 md:grid-cols-2">
                <EvidenceField label="Provider">
                  <input
                    className={FIELD_CLASS}
                    value={matrixRunForm.provider}
                    onChange={(e) => setMatrixRunForm({ ...matrixRunForm, provider: e.target.value })}
                  />
                </EvidenceField>
                <EvidenceField label="Count / Suite">
                  <input
                    className={FIELD_CLASS}
                    type="number"
                    min={1}
                    max={100}
                    value={matrixRunForm.count_per_suite}
                    onChange={(e) => setMatrixRunForm({ ...matrixRunForm, count_per_suite: Number(e.target.value) })}
                  />
                </EvidenceField>
                <div className="md:col-span-2">
                  <EvidenceField label="Suites">
                    <div className="grid gap-2 md:grid-cols-2">
                      {collections.map((collection) => {
                        const checked = (matrixRunForm.suite_ids ?? []).includes(collection.id);
                        return (
                          <label key={collection.id} className="flex items-center gap-2 rounded-lg border border-white/[0.08] bg-dark-900/30 px-3 py-2 text-[11px] text-slate-300">
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={(e) => {
                                const selected = new Set(matrixRunForm.suite_ids ?? []);
                                if (e.target.checked) selected.add(collection.id);
                                else selected.delete(collection.id);
                                setMatrixRunForm({ ...matrixRunForm, suite_ids: [...selected] });
                              }}
                            />
                            <span>{collection.label}</span>
                          </label>
                        );
                      })}
                    </div>
                  </EvidenceField>
                </div>
              </div>
              <button
                type="submit"
                disabled={runMatrixMutation.isPending}
                className="rounded-lg border border-white/[0.08] bg-white/[0.04] px-4 py-2 text-sm font-semibold text-slate-200 hover:text-white disabled:opacity-50"
              >
                {runMatrixMutation.isPending ? 'Running...' : 'Run Suite Matrix + Reseed'}
              </button>
            </form>
          </div>
          {(runBaselineMutation.data || runMatrixMutation.data) && (
            <div className="grid gap-3 xl:grid-cols-2">
              {runBaselineMutation.data && (
                <div className="rounded-lg border border-white/[0.08] bg-dark-900/30 px-4 py-3">
                  <div className="flex items-center gap-2">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Latest Baseline Run</p>
                    {statusBadge(String((runBaselineMutation.data.summary as Record<string, unknown>).status ?? 'unknown'))}
                  </div>
                  <p className="mt-2 text-[11px] text-slate-300">
                    Archive: {runBaselineMutation.data.archive_path}
                  </p>
                </div>
              )}
              {runMatrixMutation.data && (
                <div className="rounded-lg border border-white/[0.08] bg-dark-900/30 px-4 py-3">
                  <div className="flex items-center gap-2">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Latest Matrix Run</p>
                    {statusBadge(runMatrixMutation.data.failed_count > 0 ? (runMatrixMutation.data.success_count > 0 ? 'partial' : 'failed') : 'completed')}
                  </div>
                  <p className="mt-2 text-[11px] text-slate-300">
                    {runMatrixMutation.data.success_count} success / {runMatrixMutation.data.partial_count} partial / {runMatrixMutation.data.failed_count} failed
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </Card>

      <Card title="Log Validation Evidence">
        <div className="space-y-4">
          <p className="text-[11px] leading-relaxed text-slate-500">
            Human-rater agreement is collected through the validation workflow above. Use these forms
            to log additional scorer-agreement checks, benchmark-suite runs, and tracked false
            positive / false negative cases.
          </p>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => {
                setEvidenceStatus(null);
                seedEvidenceMutation.mutate();
              }}
              disabled={seedEvidenceMutation.isPending}
              className="rounded-lg border border-accent-teal/30 bg-accent-teal/10 px-4 py-2 text-xs font-semibold text-accent-teal hover:bg-accent-teal/20 disabled:opacity-50"
            >
              {seedEvidenceMutation.isPending ? 'Seeding...' : 'Regenerate From Current Artifacts'}
            </button>
            <span className="text-[11px] text-slate-500">
              Rebuilds scorer-agreement, benchmark, and tier-disagreement evidence from the current baseline study and human labels.
            </span>
          </div>
          {evidenceStatus && (
            <p className="rounded-lg border border-emerald-400/20 bg-emerald-400/[0.06] px-3 py-2 text-[11px] text-emerald-300">
              {evidenceStatus}
            </p>
          )}

          <details className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3">
            <summary className="cursor-pointer text-sm font-medium text-slate-200">Scorer Agreement Case</summary>
            <form
              className="mt-4 grid gap-3 md:grid-cols-2"
              onSubmit={(e) => {
                e.preventDefault();
                setEvidenceStatus(null);
                scorerAgreementMutation.mutate(scorerForm, {
                  onError: (err) => setEvidenceStatus(err instanceof Error ? err.message : 'Failed to save scorer agreement evidence.'),
                });
              }}
            >
              <EvidenceField label="Generator Provider">
                <input
                  className={FIELD_CLASS}
                  value={scorerForm.generator_provider}
                  onChange={(e) => setScorerForm({ ...scorerForm, generator_provider: e.target.value })}
                />
              </EvidenceField>
              <EvidenceField label="Scorer Provider">
                <input
                  className={FIELD_CLASS}
                  value={scorerForm.scorer_provider}
                  onChange={(e) => setScorerForm({ ...scorerForm, scorer_provider: e.target.value })}
                />
              </EvidenceField>
              <EvidenceField label="Generator Model (optional)">
                <input
                  className={FIELD_CLASS}
                  value={scorerForm.generator_model ?? ''}
                  onChange={(e) => setScorerForm({ ...scorerForm, generator_model: e.target.value })}
                />
              </EvidenceField>
              <EvidenceField label="Scorer Model (optional)">
                <input
                  className={FIELD_CLASS}
                  value={scorerForm.scorer_model ?? ''}
                  onChange={(e) => setScorerForm({ ...scorerForm, scorer_model: e.target.value })}
                />
              </EvidenceField>
              <EvidenceField label="Machine Score (0-10)">
                <input
                  className={FIELD_CLASS}
                  type="number"
                  min={0}
                  max={10}
                  step={0.1}
                  value={scorerForm.machine_score}
                  onChange={(e) => setScorerForm({ ...scorerForm, machine_score: Number(e.target.value) })}
                />
              </EvidenceField>
              <EvidenceField label="Scorer Score (0-10)">
                <input
                  className={FIELD_CLASS}
                  type="number"
                  min={0}
                  max={10}
                  step={0.1}
                  value={scorerForm.scorer_score}
                  onChange={(e) => setScorerForm({ ...scorerForm, scorer_score: Number(e.target.value) })}
                />
              </EvidenceField>
              <div className="md:col-span-2">
                <EvidenceField label="Prompt Excerpt">
                  <textarea
                    className={FIELD_CLASS}
                    rows={3}
                    value={scorerForm.prompt_excerpt}
                    onChange={(e) => setScorerForm({ ...scorerForm, prompt_excerpt: e.target.value })}
                  />
                </EvidenceField>
              </div>
              <EvidenceField label="Item Index (optional)">
                <input
                  className={FIELD_CLASS}
                  type="number"
                  min={0}
                  value={scorerForm.item_index ?? ''}
                  onChange={(e) => setScorerForm({ ...scorerForm, item_index: e.target.value === '' ? null : Number(e.target.value) })}
                />
              </EvidenceField>
              <div className="md:col-span-2">
                <EvidenceField label="Notes">
                  <textarea
                    className={FIELD_CLASS}
                    rows={2}
                    value={scorerForm.notes ?? ''}
                    onChange={(e) => setScorerForm({ ...scorerForm, notes: e.target.value })}
                  />
                </EvidenceField>
              </div>
              <div className="md:col-span-2">
                <button
                  type="submit"
                  disabled={scorerAgreementMutation.isPending}
                  className="rounded-lg bg-gradient-to-r from-accent-teal to-accent-cyan px-4 py-2 text-sm font-semibold text-dark-900 hover:opacity-90 disabled:opacity-50"
                >
                  {scorerAgreementMutation.isPending ? 'Saving...' : 'Save Scorer Agreement Case'}
                </button>
              </div>
            </form>
          </details>

          <details className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3">
            <summary className="cursor-pointer text-sm font-medium text-slate-200">Benchmark Suite Run</summary>
            <form
              className="mt-4 grid gap-3 md:grid-cols-2"
              onSubmit={(e) => {
                e.preventDefault();
                setEvidenceStatus(null);
                benchmarkMutation.mutate(benchmarkForm, {
                  onError: (err) => setEvidenceStatus(err instanceof Error ? err.message : 'Failed to save benchmark evidence.'),
                });
              }}
            >
              <EvidenceField label="Suite Name">
                <input
                  className={FIELD_CLASS}
                  value={benchmarkForm.suite_name}
                  onChange={(e) => setBenchmarkForm({ ...benchmarkForm, suite_name: e.target.value })}
                />
              </EvidenceField>
              <EvidenceField label="Provider">
                <input
                  className={FIELD_CLASS}
                  value={benchmarkForm.provider}
                  onChange={(e) => setBenchmarkForm({ ...benchmarkForm, provider: e.target.value })}
                />
              </EvidenceField>
              <EvidenceField label="Model (optional)">
                <input
                  className={FIELD_CLASS}
                  value={benchmarkForm.model ?? ''}
                  onChange={(e) => setBenchmarkForm({ ...benchmarkForm, model: e.target.value })}
                />
              </EvidenceField>
              <EvidenceField label="Scoring Mode">
                <select
                  className={FIELD_CLASS}
                  value={benchmarkForm.scoring_mode ?? 'heuristic_fallback'}
                  onChange={(e) => setBenchmarkForm({ ...benchmarkForm, scoring_mode: e.target.value as BenchmarkSuiteSubmit['scoring_mode'] })}
                >
                  <option value="heuristic_fallback">heuristic_fallback</option>
                  <option value="secondary_llm">secondary_llm</option>
                  <option value="self_reported">self_reported</option>
                </select>
              </EvidenceField>
              <EvidenceField label="Scorer Provider (optional)">
                <input
                  className={FIELD_CLASS}
                  value={benchmarkForm.scoring_provider ?? ''}
                  onChange={(e) => setBenchmarkForm({ ...benchmarkForm, scoring_provider: e.target.value })}
                />
              </EvidenceField>
              <EvidenceField label="Scorer Model (optional)">
                <input
                  className={FIELD_CLASS}
                  value={benchmarkForm.scoring_model ?? ''}
                  onChange={(e) => setBenchmarkForm({ ...benchmarkForm, scoring_model: e.target.value })}
                />
              </EvidenceField>
              <EvidenceField label="Cases Run">
                <input
                  className={FIELD_CLASS}
                  type="number"
                  min={1}
                  value={benchmarkForm.cases_run}
                  onChange={(e) => setBenchmarkForm({ ...benchmarkForm, cases_run: Number(e.target.value) })}
                />
              </EvidenceField>
              <EvidenceField label="Mean Score (0-100)">
                <input
                  className={FIELD_CLASS}
                  type="number"
                  min={0}
                  max={100}
                  step={0.1}
                  value={benchmarkForm.mean_score}
                  onChange={(e) => setBenchmarkForm({ ...benchmarkForm, mean_score: Number(e.target.value) })}
                />
              </EvidenceField>
              <EvidenceField label="Variance">
                <input
                  className={FIELD_CLASS}
                  type="number"
                  min={0}
                  step={0.01}
                  value={benchmarkForm.variance}
                  onChange={(e) => setBenchmarkForm({ ...benchmarkForm, variance: Number(e.target.value) })}
                />
              </EvidenceField>
              <div className="md:col-span-2">
                <EvidenceField label="Notes">
                  <textarea
                    className={FIELD_CLASS}
                    rows={2}
                    value={benchmarkForm.notes ?? ''}
                    onChange={(e) => setBenchmarkForm({ ...benchmarkForm, notes: e.target.value })}
                  />
                </EvidenceField>
              </div>
              <div className="md:col-span-2">
                <button
                  type="submit"
                  disabled={benchmarkMutation.isPending}
                  className="rounded-lg bg-gradient-to-r from-accent-teal to-accent-cyan px-4 py-2 text-sm font-semibold text-dark-900 hover:opacity-90 disabled:opacity-50"
                >
                  {benchmarkMutation.isPending ? 'Saving...' : 'Save Benchmark Run'}
                </button>
              </div>
            </form>
          </details>

          <details className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3">
            <summary className="cursor-pointer text-sm font-medium text-slate-200">False Positive / Negative Case</summary>
            <form
              className="mt-4 grid gap-3 md:grid-cols-2"
              onSubmit={(e) => {
                e.preventDefault();
                setEvidenceStatus(null);
                errorCaseMutation.mutate(errorCaseForm, {
                  onError: (err) => setEvidenceStatus(err instanceof Error ? err.message : 'Failed to save error-case evidence.'),
                });
              }}
            >
              <EvidenceField label="Case Type">
                <select
                  className={FIELD_CLASS}
                  value={errorCaseForm.kind}
                  onChange={(e) => setErrorCaseForm({ ...errorCaseForm, kind: e.target.value as ErrorCaseSubmit['kind'] })}
                >
                  <option value="false_positive">False Positive</option>
                  <option value="false_negative">False Negative</option>
                </select>
              </EvidenceField>
              <EvidenceField label="Item Index (optional)">
                <input
                  className={FIELD_CLASS}
                  type="number"
                  min={0}
                  value={errorCaseForm.item_index ?? ''}
                  onChange={(e) => setErrorCaseForm({ ...errorCaseForm, item_index: e.target.value === '' ? null : Number(e.target.value) })}
                />
              </EvidenceField>
              <EvidenceField label="Provider (optional)">
                <input
                  className={FIELD_CLASS}
                  value={errorCaseForm.provider ?? ''}
                  onChange={(e) => setErrorCaseForm({ ...errorCaseForm, provider: e.target.value })}
                />
              </EvidenceField>
              <EvidenceField label="Model (optional)">
                <input
                  className={FIELD_CLASS}
                  value={errorCaseForm.model ?? ''}
                  onChange={(e) => setErrorCaseForm({ ...errorCaseForm, model: e.target.value })}
                />
              </EvidenceField>
              <EvidenceField label="Expected Tier">
                <input
                  className={FIELD_CLASS}
                  value={errorCaseForm.expected_tier}
                  onChange={(e) => setErrorCaseForm({ ...errorCaseForm, expected_tier: e.target.value })}
                />
              </EvidenceField>
              <EvidenceField label="Observed Tier">
                <input
                  className={FIELD_CLASS}
                  value={errorCaseForm.observed_tier}
                  onChange={(e) => setErrorCaseForm({ ...errorCaseForm, observed_tier: e.target.value })}
                />
              </EvidenceField>
              <div className="md:col-span-2">
                <EvidenceField label="Prompt Excerpt">
                  <textarea
                    className={FIELD_CLASS}
                    rows={3}
                    value={errorCaseForm.prompt_excerpt}
                    onChange={(e) => setErrorCaseForm({ ...errorCaseForm, prompt_excerpt: e.target.value })}
                  />
                </EvidenceField>
              </div>
              <div className="md:col-span-2">
                <EvidenceField label="Notes">
                  <textarea
                    className={FIELD_CLASS}
                    rows={2}
                    value={errorCaseForm.notes ?? ''}
                    onChange={(e) => setErrorCaseForm({ ...errorCaseForm, notes: e.target.value })}
                  />
                </EvidenceField>
              </div>
              <div className="md:col-span-2">
                <button
                  type="submit"
                  disabled={errorCaseMutation.isPending}
                  className="rounded-lg bg-gradient-to-r from-accent-teal to-accent-cyan px-4 py-2 text-sm font-semibold text-dark-900 hover:opacity-90 disabled:opacity-50"
                >
                  {errorCaseMutation.isPending ? 'Saving...' : 'Save Error Case'}
                </button>
              </div>
            </form>
          </details>
        </div>
      </Card>

      {evidence && (
        <Card title="Recent Evidence Log">
          <div className="grid gap-4 lg:grid-cols-3">
            <RecentEvidenceSection
              title="Scorer Agreement"
              emptyLabel="No scorer-agreement cases logged yet."
              entries={evidence.scorer_agreement.recent}
              summarize={summarizeScorerAgreement}
            />
            <RecentEvidenceSection
              title="Benchmark Suites"
              emptyLabel="No benchmark-suite runs logged yet."
              entries={evidence.benchmark_suites.recent}
              summarize={summarizeBenchmark}
            />
            <RecentEvidenceSection
              title="False Positives / Negatives"
              emptyLabel="No false-positive or false-negative cases logged yet."
              entries={evidence.error_cases.recent}
              summarize={summarizeErrorCase}
            />
          </div>
        </Card>
      )}

      <Card title="Evidence Trends">
        {trendsError ? (
          <ErrorBanner error={trendsError as Error} />
        ) : trendsLoading || !trendData ? (
          <LoadingSpinner />
        ) : (
          <div className="space-y-4">
            <div className="grid gap-4 lg:grid-cols-2">
              <TrendTable title="By Provider" rows={trendData.by_provider} labelKey="provider" />
              <TrendTable title="By Model" rows={trendData.by_model} labelKey="model" />
            </div>
            <div className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Timeline</p>
              {trendData.timeline.length === 0 ? (
                <p className="mt-3 text-[11px] text-slate-500">No evidence timeline data yet.</p>
              ) : (
                <div className="mt-3 overflow-x-auto">
                  <table className="w-full min-w-[420px] text-[11px]">
                    <thead>
                      <tr className="border-b border-white/[0.06] text-left uppercase tracking-wider text-slate-500">
                        <th className="pb-2 pr-3">Date</th>
                        <th className="pb-2 pr-3 text-right">Total</th>
                        <th className="pb-2 pr-3 text-right">Scorer</th>
                        <th className="pb-2 pr-3 text-right">Bench</th>
                        <th className="pb-2 text-right">Errors</th>
                      </tr>
                    </thead>
                    <tbody>
                      {trendData.timeline.map((point) => (
                        <tr key={point.date} className="border-b border-white/[0.03]">
                          <td className="py-2 pr-3 text-slate-300">{point.date}</td>
                          <td className="py-2 pr-3 text-right font-mono text-slate-300">{point.total}</td>
                          <td className="py-2 pr-3 text-right font-mono text-slate-300">{point.scorer_agreement}</td>
                          <td className="py-2 pr-3 text-right font-mono text-slate-300">{point.benchmark_suites}</td>
                          <td className="py-2 text-right font-mono text-slate-300">{point.error_cases}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </Card>

      <Card title="Archived Study Runs">
        {studiesError ? (
          <ErrorBanner error={studiesError as Error} />
        ) : studiesLoading ? (
          <LoadingSpinner />
        ) : studies.length === 0 ? (
          <p className="text-[11px] text-slate-500">No archived study artifacts yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-[11px]">
              <thead>
                <tr className="border-b border-white/[0.06] text-left uppercase tracking-wider text-slate-500">
                  <th className="pb-2 pr-3">Date</th>
                  <th className="pb-2 pr-3">Provider</th>
                  <th className="pb-2 pr-3">Mode</th>
                  <th className="pb-2 pr-3">Suite</th>
                  <th className="pb-2 pr-3 text-right">Prompts</th>
                  <th className="pb-2 pr-3 text-right">Success</th>
                  <th className="pb-2 pr-3 text-right">Fail</th>
                  <th className="pb-2 pr-3 text-right">Mean</th>
                  <th className="pb-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {studies.slice(0, 12).map((study) => (
                  <tr key={study.filename} className="border-b border-white/[0.03]">
                    <td className="py-2 pr-3 text-slate-300">{formatTrendTimestamp(study.study_date ?? '')}</td>
                    <td className="py-2 pr-3 text-slate-300">{study.provider ?? 'unknown'}</td>
                    <td className="py-2 pr-3 text-slate-400">{scoringModeSummary(study)}</td>
                    <td className="py-2 pr-3 text-slate-300">{study.study_label ?? study.filename}</td>
                    <td className="py-2 pr-3 text-right font-mono text-slate-300">{study.prompt_count ?? 0}</td>
                    <td className="py-2 pr-3 text-right font-mono text-slate-300">{study.successes ?? 0}</td>
                    <td className="py-2 pr-3 text-right font-mono text-slate-300">{study.failures ?? 0}</td>
                    <td className="py-2 pr-3 text-right font-mono text-slate-300">
                      {typeof study.composite_mean === 'number' ? study.composite_mean.toFixed(1) : 'n/a'}
                    </td>
                    <td className="py-2">{statusBadge(study.status)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title="Evidence Review">
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-4">
            <label className="space-y-1">
              <span className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500">Kind</span>
              <select className={FIELD_CLASS} value={reviewKind} onChange={(e) => setReviewKind(e.target.value)}>
                <option value="all">All evidence</option>
                {(reviewData?.facets.kinds ?? []).map((facet) => (
                  <option key={facet.value} value={facet.value}>{facet.label}</option>
                ))}
              </select>
            </label>
            <label className="space-y-1">
              <span className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500">Provider</span>
              <select className={FIELD_CLASS} value={reviewProvider} onChange={(e) => setReviewProvider(e.target.value)}>
                <option value="all">All providers</option>
                {(reviewData?.facets.providers ?? []).map((facet) => (
                  <option key={facet} value={facet}>{facet}</option>
                ))}
              </select>
            </label>
            <label className="space-y-1">
              <span className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500">Model</span>
              <select className={FIELD_CLASS} value={reviewModel} onChange={(e) => setReviewModel(e.target.value)}>
                <option value="all">All models</option>
                {(reviewData?.facets.models ?? []).map((facet) => (
                  <option key={facet} value={facet}>{facet}</option>
                ))}
              </select>
            </label>
            <label className="space-y-1">
              <span className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500">Search</span>
              <input
                className={FIELD_CLASS}
                value={reviewQuery}
                onChange={(e) => setReviewQuery(e.target.value)}
                placeholder="prompt, note, tier..."
              />
            </label>
          </div>
          <div className="flex flex-wrap gap-2">
            <a
              href={`/api/validation/evidence/export?format=json${exportSuffix}`}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-lg border border-white/[0.08] bg-white/[0.04] px-4 py-2 text-xs font-medium text-slate-400 hover:text-slate-200"
            >
              Export Filtered JSON
            </a>
            <a
              href={`/api/validation/evidence/export?format=csv${exportSuffix}`}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-lg border border-white/[0.08] bg-white/[0.04] px-4 py-2 text-xs font-medium text-slate-400 hover:text-slate-200"
            >
              Export Filtered CSV
            </a>
            {reviewData && (
              <span className="self-center text-[11px] text-slate-500">
                Showing {reviewData.returned} of {reviewData.total} matching evidence entries.
              </span>
            )}
          </div>
          {reviewError ? (
            <ErrorBanner error={reviewError as Error} />
          ) : reviewLoading || !reviewData ? (
            <LoadingSpinner />
          ) : reviewData.entries.length === 0 ? (
            <p className="text-[11px] text-slate-500">No evidence entries match the current filters.</p>
          ) : (
            <div className="space-y-3">
              {reviewData.entries.map((entry, index) => (
                <div key={`${entry.kind}-${entry.timestamp}-${entry.item_index ?? index}`} className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full bg-accent-teal/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-accent-teal">
                      {entry.kind_label}
                    </span>
                    <span className="text-[10px] uppercase tracking-wider text-slate-500">{formatEntryTimestamp(entry)}</span>
                    {entry.provider && <span className="text-[10px] text-slate-500">Provider: {entry.provider}</span>}
                    {entry.model && <span className="text-[10px] text-slate-500">Model: {entry.model}</span>}
                  </div>
                  <p className="mt-2 text-[11px] leading-relaxed text-slate-300">{entry.summary}</p>
                  {entry.prompt_excerpt && <p className="mt-2 text-[10px] leading-relaxed text-slate-500">{entry.prompt_excerpt}</p>}
                  {entry.notes && <p className="mt-2 text-[10px] leading-relaxed text-slate-500">{entry.notes}</p>}
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>

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

      <Card title="Calibration Review">
        {calibrationError ? (
          <ErrorBanner error={calibrationError as Error} />
        ) : calibrationLoading || !calibrationReview ? (
          <LoadingSpinner />
        ) : (
          <div className="space-y-4">
            <div className="grid gap-4 xl:grid-cols-2">
              <div className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Rater Drift</p>
                {calibrationReview.raters.length === 0 ? (
                  <p className="mt-3 text-[11px] text-slate-500">No calibration rows yet.</p>
                ) : (
                  <div className="mt-3 overflow-x-auto">
                    <table className="w-full min-w-[520px] text-[11px]">
                      <thead>
                        <tr className="border-b border-white/[0.06] text-left uppercase tracking-wider text-slate-500">
                          <th className="pb-2 pr-3">Rater</th>
                          <th className="pb-2 pr-3 text-right">Labels</th>
                          <th className="pb-2 pr-3 text-right">Abs Panel Gap</th>
                          <th className="pb-2 pr-3 text-right">Abs Machine Gap</th>
                          <th className="pb-2">Top Drift</th>
                        </tr>
                      </thead>
                      <tbody>
                        {calibrationReview.raters.map((row) => (
                          <tr key={row.rater} className="border-b border-white/[0.03]">
                            <td className="py-2 pr-3 text-slate-300">{row.rater}</td>
                            <td className="py-2 pr-3 text-right font-mono text-slate-300">{row.label_count}</td>
                            <td className="py-2 pr-3 text-right font-mono text-slate-300">{row.mean_abs_panel_gap.toFixed(2)}</td>
                            <td className="py-2 pr-3 text-right font-mono text-slate-300">{row.mean_abs_machine_gap.toFixed(2)}</td>
                            <td className="py-2 text-slate-400">
                              {row.top_operator_drift
                                ? `${row.top_operator_drift.operator_name} (${row.top_operator_drift.signed_gap >= 0 ? '+' : ''}${row.top_operator_drift.signed_gap.toFixed(2)})`
                                : 'n/a'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              <div className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Highest Operator Disagreement</p>
                {calibrationReview.operators.length === 0 ? (
                  <p className="mt-3 text-[11px] text-slate-500">No shared-item disagreement data yet.</p>
                ) : (
                  <div className="mt-3 overflow-x-auto">
                    <table className="w-full min-w-[520px] text-[11px]">
                      <thead>
                        <tr className="border-b border-white/[0.06] text-left uppercase tracking-wider text-slate-500">
                          <th className="pb-2 pr-3">Operator</th>
                          <th className="pb-2 pr-3 text-right">Shared</th>
                          <th className="pb-2 pr-3 text-right">Mean Spread</th>
                          <th className="pb-2 text-right">Max Spread</th>
                        </tr>
                      </thead>
                      <tbody>
                        {calibrationReview.operators.slice(0, 8).map((row) => (
                          <tr key={row.operator_index} className="border-b border-white/[0.03]">
                            <td className="py-2 pr-3 text-slate-300">{row.operator_name}</td>
                            <td className="py-2 pr-3 text-right font-mono text-slate-300">{row.shared_items}</td>
                            <td className="py-2 pr-3 text-right font-mono text-slate-300">{row.mean_spread.toFixed(2)}</td>
                            <td className="py-2 text-right font-mono text-slate-300">{row.max_spread.toFixed(2)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Reconciliation Queue</p>
              {calibrationReview.items.length === 0 ? (
                <p className="mt-3 text-[11px] text-slate-500">No multi-rater conflicts to reconcile yet.</p>
              ) : (
                <div className="mt-3 space-y-3">
                  {calibrationReview.items.slice(0, 8).map((item) => (
                    <div key={item.item_index} className="rounded-lg border border-white/[0.06] bg-dark-900/30 px-3 py-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-amber-300">
                          Item {item.item_index}
                        </span>
                        <span className="text-[10px] text-slate-500">Raters: {item.raters.join(', ')}</span>
                        <span className="text-[10px] text-slate-500">Machine mean: {item.machine_mean != null ? item.machine_mean.toFixed(2) : 'n/a'}</span>
                      </div>
                      <p className="mt-2 text-[11px] leading-relaxed text-slate-300">{item.prompt_excerpt}</p>
                      <p className="mt-2 text-[10px] text-slate-500">
                        Largest gap: {item.largest_operator_gap.operator_name} spread {item.largest_operator_gap.spread.toFixed(2)}; panel mean {item.panel_mean.toFixed(2)}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </Card>

      {/* Calibration recommendations */}
      <Card title="Calibration Recommendations">
        <div className="space-y-2">
          {recommendations.length === 0 ? (
            <p className="text-[11px] text-slate-500 text-center py-4">
              No recommendations yet — collect more validations to generate calibration guidance.
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

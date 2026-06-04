import { useCallback, useEffect, useMemo, useState } from 'react';
import { Card } from '../components/shared/Card';
import { LoadingSpinner } from '../components/shared/LoadingSpinner';
import { ErrorBanner } from '../components/shared/ErrorBanner';
import { HowItWorksPanel } from '../components/shared/HowItWorksPanel';
import { Disclosure } from '../components/shared/Disclosure';
import { ResearchPrototypeNotice } from '../components/shared/ResearchPrototypeNotice';
import {
  getValidationCalibrationSession,
  getValidationNext,
  postValidationCalibrationSession,
  postValidationLabel,
} from '../api/endpoints';
import type {
  ValidationCalibrationDisposition,
  ValidationCalibrationQueueItem,
  ValidationCalibrationSessionData,
  ValidationNextItem,
} from '../api/types';

const HOW_IT_WORKS_SECTIONS = [
  {
    title: 'How to Use This Page',
    body: (
      <ul className="list-disc list-inside space-y-1 text-slate-300">
        <li>Read the prompt and the AI response carefully before scoring.</li>
        <li>Score all 10 Cognitive Operators and 4 Processing Domains from 0 to 10.</li>
        <li>Submit your independent rating before reviewing machine agreement.</li>
        <li>Use the calibration session queue below to reconcile disputed items.</li>
        <li>Keep notes concise and specific enough for another rater to follow.</li>
      </ul>
    ),
  },
  {
    title: "What You're Scoring",
    body: (
      <div className="space-y-3">
        <div>
          <p className="mb-1 text-[11px] font-semibold text-slate-200">Cognitive Operators</p>
          <ul className="space-y-1 text-slate-400">
            <li><strong className="text-slate-300">CO-0 (Generative Potential):</strong> Did the response contain original ideas or stay generic?</li>
            <li><strong className="text-slate-300">CO-1 (Directed Attention):</strong> Did it stay focused and track relevant variables?</li>
            <li><strong className="text-slate-300">CO-2 (Attraction):</strong> Did it identify constructive opportunities?</li>
            <li><strong className="text-slate-300">CO-3 (Critical Evaluation):</strong> Did it identify risks, downsides, and failure modes?</li>
            <li><strong className="text-slate-300">CO-4 (Encoding Intensity):</strong> Did it calibrate depth appropriately?</li>
            <li><strong className="text-slate-300">CO-5 (Receptive Integration):</strong> Did it absorb constraints or feedback without collapsing?</li>
            <li><strong className="text-slate-300">CO-6 (Projective Assertion):</strong> Did it take a clear position?</li>
            <li><strong className="text-slate-300">CO-7 (Pattern Entrainment):</strong> Did it recognize patterns, cycles, or repeated structure?</li>
            <li><strong className="text-slate-300">CO-8 (Causal Reasoning):</strong> Did it trace causes upstream?</li>
            <li><strong className="text-slate-300">CO-9 (Consequential Grounding):</strong> Did it trace consequences downstream?</li>
          </ul>
        </div>
        <div>
          <p className="mb-1 text-[11px] font-semibold text-slate-200">Processing Domains</p>
          <ul className="space-y-1 text-slate-400">
            <li><strong className="text-slate-300">Principled (P):</strong> Value- and ethics-driven reasoning.</li>
            <li><strong className="text-slate-300">Cognitive (C):</strong> Analytical and logical reasoning.</li>
            <li><strong className="text-slate-300">Evaluative (E):</strong> Emotional weight, salience, and impact.</li>
            <li><strong className="text-slate-300">Operational (O):</strong> Translation into concrete action.</li>
          </ul>
        </div>
      </div>
    ),
  },
  {
    title: 'Validation Protocol',
    body: (
      <div className="space-y-2 text-slate-300">
        <p>
          Follow the same protocol for every round: independent human scoring first, machine comparison second,
          disagreement review only after multiple raters have submitted.
        </p>
        <ul className="list-disc list-inside space-y-1 text-slate-400">
          <li>Use at least two raters on the same prompt-response set.</li>
          <li>Keep prompts frozen for stakeholder-facing benchmark comparisons.</li>
          <li>Use <code className="text-slate-300">heuristic_fallback</code> as the neutral benchmark baseline.</li>
          <li>Use <code className="text-slate-300">secondary_llm</code> only with a separate scorer provider for the external-LLM table.</li>
          <li>Do not mix heuristic, external-LLM, and self-reported scores in one ranking table.</li>
          <li>Keep <code className="text-slate-300">self_reported</code> out of stakeholder-facing comparisons.</li>
          <li>Log scorer-agreement, benchmark-suite, and false-positive/false-negative evidence on the leaderboard.</li>
          <li>Treat social-engineering and bias-flag signals as heuristic until externally validated.</li>
        </ul>
      </div>
    ),
  },
  {
    title: 'Why This Matters',
    body: (
      <p className="text-slate-300">
        Human ratings are the external reference that lets us measure whether CAS machine scoring is aligned with
        expert judgment. The goal is not forced agreement. The goal is a documented, reviewable record of where
        humans and machines converge, where they diverge, and why.
      </p>
    ),
  },
];

const OPERATOR_LABELS = [
  { idx: 0, name: 'CO-0 (Generative Potential)' },
  { idx: 1, name: 'CO-1 (Directed Attention)' },
  { idx: 2, name: 'CO-2 (Attraction)' },
  { idx: 3, name: 'CO-3 (Critical Evaluation)' },
  { idx: 4, name: 'CO-4 (Encoding Intensity)' },
  { idx: 5, name: 'CO-5 (Receptive Integration)' },
  { idx: 6, name: 'CO-6 (Projective Assertion)' },
  { idx: 7, name: 'CO-7 (Pattern Entrainment)' },
  { idx: 8, name: 'CO-8 (Causal Reasoning)' },
  { idx: 9, name: 'CO-9 (Consequential Grounding)' },
];

const DOMAIN_LABELS = [
  { idx: 0, name: 'Principled (P)' },
  { idx: 1, name: 'Cognitive (C)' },
  { idx: 2, name: 'Evaluative (E)' },
  { idx: 3, name: 'Operational (O)' },
];

const CALIBRATION_DISPOSITIONS: Array<{
  value: ValidationCalibrationDisposition;
  label: string;
  help: string;
}> = [
  {
    value: 'needs_more_review',
    label: 'Needs more review',
    help: 'Flag the disagreement without choosing a winner yet.',
  },
  {
    value: 'resolved_panel',
    label: 'Accept panel consensus',
    help: 'Use the human panel as the working reference for this item.',
  },
  {
    value: 'resolved_machine',
    label: 'Accept machine profile',
    help: 'Record that the machine score should stand for this item.',
  },
  {
    value: 'rubric_clarification',
    label: 'Rubric clarification needed',
    help: 'The disagreement points to unclear scoring guidance.',
  },
  {
    value: 'false_positive',
    label: 'Machine likely false positive',
    help: 'The machine appears too severe compared with the human panel.',
  },
  {
    value: 'false_negative',
    label: 'Machine likely false negative',
    help: 'The machine appears too lenient compared with the human panel.',
  },
];

function scoreColor(score: number): string {
  if (score <= 3) return '#f87171';
  if (score <= 6) return '#fbbf24';
  return '#34d399';
}

function calibrationDeltaColor(delta: number): string {
  const absDelta = Math.abs(delta);
  if (absDelta < 1.5) return '#34d399';
  if (absDelta < 3) return '#fbbf24';
  return '#f87171';
}

function roundedScoreArray(values: number[] | undefined, count: number): number[] {
  const base = Array(count).fill(5);
  if (!values?.length) return base;
  return base.map((fallback, idx) => {
    const value = values[idx];
    if (typeof value !== 'number' || Number.isNaN(value)) return fallback;
    return Math.max(0, Math.min(10, Math.round(value)));
  });
}

function ScoreSlider({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  const color = scoreColor(value);
  return (
    <div className="flex items-center gap-3">
      <span className="w-44 shrink-0 text-[11px] text-slate-300">{label}</span>
      <input
        type="range"
        min={0}
        max={10}
        step={1}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="flex-1"
        style={{ accentColor: color }}
      />
      <span
        className="w-8 text-center text-xs font-mono font-bold tabular-nums"
        style={{ color }}
      >
        {value}
      </span>
    </div>
  );
}

type ComparisonData = {
  machine_scores: number[];
  machine_domain_averages: number[] | null;
  human_scores: number[];
  human_domain_scores: number[];
};

function CalibrationQueueButton({
  item,
  active,
  onClick,
}: {
  item: ValidationCalibrationQueueItem;
  active: boolean;
  onClick: () => void;
}) {
  const gap = item.largest_operator_gap?.spread ?? 0;
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full rounded-xl border px-3 py-3 text-left transition ${
        active
          ? 'border-accent-teal/70 bg-accent-teal/[0.08]'
          : 'border-white/[0.08] bg-white/[0.03] hover:border-white/[0.14]'
      }`}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="text-[11px] font-semibold text-slate-200">Item {item.item_index}</span>
        <span className="rounded-full border border-white/[0.08] px-2 py-0.5 text-[10px] text-slate-400">
          {item.session_count} prior {item.session_count === 1 ? 'session' : 'sessions'}
        </span>
      </div>
      <p className="mt-2 text-[11px] leading-relaxed text-slate-400">{item.prompt_excerpt}</p>
      <div className="mt-3 flex flex-wrap gap-2 text-[10px] text-slate-500">
        <span>Gap {gap.toFixed(1)}</span>
        <span>Mean spread {item.mean_spread.toFixed(1)}</span>
        <span>{item.raters.join(', ')}</span>
      </div>
    </button>
  );
}

export function ValidationPage() {
  const [rater, setRater] = useState<string>(() => localStorage.getItem('nc_rater') || '');
  const [raterInput, setRaterInput] = useState<string>('');
  const [item, setItem] = useState<ValidationNextItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [operatorScores, setOperatorScores] = useState<number[]>(Array(10).fill(5));
  const [domainScores, setDomainScores] = useState<number[]>(Array(4).fill(5));
  const [submitting, setSubmitting] = useState(false);
  const [comparison, setComparison] = useState<ComparisonData | null>(null);
  const [justSaved, setJustSaved] = useState(false);
  const [calibrationData, setCalibrationData] = useState<ValidationCalibrationSessionData | null>(null);
  const [calibrationLoading, setCalibrationLoading] = useState(false);
  const [calibrationError, setCalibrationError] = useState<Error | null>(null);
  const [selectedCalibrationIndex, setSelectedCalibrationIndex] = useState(0);
  const [calibrationDisposition, setCalibrationDisposition] =
    useState<ValidationCalibrationDisposition>('needs_more_review');
  const [calibrationNotes, setCalibrationNotes] = useState('');
  const [includeResolvedScores, setIncludeResolvedScores] = useState(false);
  const [resolvedOperatorScores, setResolvedOperatorScores] = useState<number[]>(Array(10).fill(5));
  const [resolvedDomainScores, setResolvedDomainScores] = useState<number[]>(Array(4).fill(5));
  const [calibrationSubmitting, setCalibrationSubmitting] = useState(false);
  const [calibrationSaved, setCalibrationSaved] = useState(false);

  const loadNext = useCallback(async (forRater: string) => {
    setLoading(true);
    setError(null);
    setComparison(null);
    try {
      const next = await getValidationNext(forRater);
      setItem(next);
      setOperatorScores(Array(10).fill(5));
      setDomainScores(Array(4).fill(5));
    } catch (e) {
      setError(e as Error);
    }
    setLoading(false);
  }, []);

  const loadCalibration = useCallback(async () => {
    setCalibrationLoading(true);
    setCalibrationError(null);
    try {
      const next = await getValidationCalibrationSession();
      setCalibrationData(next);
      setSelectedCalibrationIndex((current) => {
        if (!next.queue.length) return 0;
        return Math.min(current, next.queue.length - 1);
      });
    } catch (e) {
      setCalibrationError(e as Error);
    }
    setCalibrationLoading(false);
  }, []);

  useEffect(() => {
    if (rater) {
      loadNext(rater);
      loadCalibration();
    }
  }, [rater, loadNext, loadCalibration]);

  const selectedCalibrationItem = useMemo<ValidationCalibrationQueueItem | null>(
    () => calibrationData?.queue?.[selectedCalibrationIndex] ?? null,
    [calibrationData, selectedCalibrationIndex],
  );

  useEffect(() => {
    if (!selectedCalibrationItem) {
      setCalibrationDisposition('needs_more_review');
      setCalibrationNotes('');
      setIncludeResolvedScores(false);
      setResolvedOperatorScores(Array(10).fill(5));
      setResolvedDomainScores(Array(4).fill(5));
      return;
    }
    setCalibrationDisposition('needs_more_review');
    setCalibrationNotes('');
    setIncludeResolvedScores(false);
    setResolvedOperatorScores(roundedScoreArray(selectedCalibrationItem.panel_operator_scores, 10));
    setResolvedDomainScores(roundedScoreArray(selectedCalibrationItem.panel_domain_scores, 4));
  }, [selectedCalibrationItem]);

  const handleSetRater = () => {
    const name = raterInput.trim();
    if (!name) return;
    localStorage.setItem('nc_rater', name);
    setRater(name);
  };

  const handleSubmit = async () => {
    if (!item || item.item_index === null) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await postValidationLabel({
        item_index: item.item_index,
        rater,
        operator_scores: operatorScores,
        domain_scores: domainScores,
      });
      setComparison({
        machine_scores: res.machine_scores ?? [],
        machine_domain_averages: res.machine_domain_averages,
        human_scores: [...operatorScores],
        human_domain_scores: [...domainScores],
      });
      setJustSaved(true);
      setTimeout(() => setJustSaved(false), 1500);
      await loadCalibration();
    } catch (e) {
      setError(e as Error);
    }
    setSubmitting(false);
  };

  const handleNext = () => {
    setComparison(null);
    loadNext(rater);
  };

  const handleSkip = () => {
    loadNext(rater);
  };

  const handleSaveCalibration = async () => {
    if (!selectedCalibrationItem) return;
    setCalibrationSubmitting(true);
    setCalibrationError(null);
    try {
      await postValidationCalibrationSession({
        item_index: selectedCalibrationItem.item_index,
        reconciler: rater,
        disposition: calibrationDisposition,
        notes: calibrationNotes,
        resolved_operator_scores: includeResolvedScores ? resolvedOperatorScores : null,
        resolved_domain_scores: includeResolvedScores ? resolvedDomainScores : null,
      });
      setCalibrationSaved(true);
      setTimeout(() => setCalibrationSaved(false), 1600);
      await loadCalibration();
    } catch (e) {
      setCalibrationError(e as Error);
    }
    setCalibrationSubmitting(false);
  };

  if (!rater) {
    return (
      <div className="mx-auto max-w-md space-y-4 pt-6">
        <HowItWorksPanel sections={HOW_IT_WORKS_SECTIONS} label="How This Works" />
        <ResearchPrototypeNotice compact />
      <Card title="Who is validating?">
        <div className="space-y-3">
            <p className="text-[12px] text-slate-400">Enter reviewer name.</p>
            <input
              type="text"
              value={raterInput}
              onChange={(e) => setRaterInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSetRater()}
              placeholder="Your name"
              className="min-h-[44px] w-full rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3 text-base text-slate-200 placeholder-slate-600 focus:border-accent-teal/50 focus:outline-none"
            />
            <button
              onClick={handleSetRater}
              disabled={!raterInput.trim()}
              className="min-h-[44px] w-full rounded-lg bg-gradient-to-r from-accent-teal to-accent-cyan px-4 py-3 text-sm font-semibold text-dark-900 hover:opacity-90 disabled:opacity-40"
            >
              Start Validating
            </button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <HowItWorksPanel sections={HOW_IT_WORKS_SECTIONS} label="How This Works" />
      <ResearchPrototypeNotice compact />

      <Disclosure summary="Protocol note">
        <p>
          This page is part of the documented validation protocol in{' '}
          <code className="text-slate-300">validation/VALIDATION_PROTOCOL.md</code>. Collect independent human
          scores here, then use the calibration session queue to review disagreements without leaving the workflow.
        </p>
      </Disclosure>

      <Card title="Calibration Session">
        <div className="space-y-4">
          <Disclosure summary="About calibration sessions">
            <p>
              Review disputed items with multiple human ratings, compare them with the machine profile, and log
              a durable reconciliation note. This is the review trail stakeholders will expect when they ask how
              disagreements were handled.
            </p>
          </Disclosure>
          <ErrorBanner error={calibrationError} />

          {calibrationLoading ? (
            <LoadingSpinner />
          ) : !calibrationData || calibrationData.queue.length === 0 ? (
            <p className="text-[11px] text-slate-500">
              No multi-rater disagreements are queued yet. Collect at least two ratings on the same item to
              start a calibration session.
            </p>
          ) : (
            <div className="space-y-4">
              <div className="grid gap-3 lg:grid-cols-[280px_minmax(0,1fr)]">
                <div className="space-y-2">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
                    Disagreement Queue
                  </p>
                  {calibrationData.queue.map((queueItem, idx) => (
                    <CalibrationQueueButton
                      key={queueItem.item_index}
                      item={queueItem}
                      active={idx === selectedCalibrationIndex}
                      onClick={() => setSelectedCalibrationIndex(idx)}
                    />
                  ))}
                </div>

                {selectedCalibrationItem ? (
                  <div className="space-y-4 rounded-xl border border-white/[0.08] bg-white/[0.03] p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
                          Active Review
                        </p>
                        <h2 className="text-sm font-semibold text-slate-100">
                          Item {selectedCalibrationItem.item_index} · {selectedCalibrationItem.model || 'unknown model'}
                        </h2>
                      </div>
                      <div className="flex flex-wrap gap-2 text-[10px] text-slate-500">
                        <span className="rounded-full border border-white/[0.08] px-2 py-0.5">
                          Largest gap {selectedCalibrationItem.largest_operator_gap?.operator_name ?? 'n/a'}
                        </span>
                        <span className="rounded-full border border-white/[0.08] px-2 py-0.5">
                          Machine-panel gap {selectedCalibrationItem.machine_panel_gap.toFixed(1)}
                        </span>
                      </div>
                    </div>

                    <div className="grid gap-3 md:grid-cols-2">
                      <div className="rounded-xl border border-white/[0.06] bg-dark-900/40 p-3">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Prompt</p>
                        <p className="mt-2 max-h-44 overflow-y-auto whitespace-pre-wrap text-[12px] leading-relaxed text-slate-300">
                          {selectedCalibrationItem.prompt}
                        </p>
                      </div>
                      <div className="rounded-xl border border-white/[0.06] bg-dark-900/40 p-3">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Response</p>
                        <p className="mt-2 max-h-44 overflow-y-auto whitespace-pre-wrap text-[12px] leading-relaxed text-slate-300">
                          {selectedCalibrationItem.response || '(no response recorded)'}
                        </p>
                      </div>
                    </div>

                    <div className="overflow-x-auto rounded-xl border border-white/[0.06]">
                      <table className="min-w-full divide-y divide-white/[0.06] text-[11px]">
                        <thead className="bg-white/[0.03] text-slate-500">
                          <tr>
                            <th className="px-3 py-2 text-left font-semibold">Operator</th>
                            <th className="px-3 py-2 text-right font-semibold">Panel</th>
                            <th className="px-3 py-2 text-right font-semibold">Machine</th>
                            {selectedCalibrationItem.labels.map((label) => (
                              <th key={label.rater} className="px-3 py-2 text-right font-semibold">
                                {label.rater}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/[0.04]">
                          {OPERATOR_LABELS.map((op) => {
                            const panel = selectedCalibrationItem.panel_operator_scores[op.idx] ?? 0;
                            const machine = selectedCalibrationItem.machine_operator_scores[op.idx] ?? 0;
                            return (
                              <tr key={op.idx}>
                                <td className="px-3 py-2 text-slate-300">{op.name}</td>
                                <td className="px-3 py-2 text-right font-mono text-slate-200">{panel.toFixed(1)}</td>
                                <td
                                  className="px-3 py-2 text-right font-mono font-semibold"
                                  style={{ color: calibrationDeltaColor(panel - machine) }}
                                >
                                  {machine.toFixed(1)}
                                </td>
                                {selectedCalibrationItem.labels.map((label) => {
                                  const score = label.operator_scores[op.idx] ?? 0;
                                  return (
                                    <td
                                      key={`${label.rater}-${op.idx}`}
                                      className="px-3 py-2 text-right font-mono"
                                      style={{ color: calibrationDeltaColor(score - panel) }}
                                    >
                                      {score.toFixed(1)}
                                    </td>
                                  );
                                })}
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>

                    <div className="grid gap-3 md:grid-cols-2">
                      <div className="rounded-xl border border-white/[0.06] bg-dark-900/40 p-3">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
                          Domain Snapshot
                        </p>
                        <div className="mt-3 space-y-2">
                          {DOMAIN_LABELS.map((domain) => (
                            <div key={domain.idx} className="grid grid-cols-[1.6fr,0.8fr,0.8fr,1fr] items-center gap-2 text-[11px]">
                              <span className="text-slate-300">{domain.name}</span>
                              <span className="text-right font-mono text-slate-200">
                                {selectedCalibrationItem.panel_domain_scores[domain.idx]?.toFixed(1)}
                              </span>
                              <span className="text-right font-mono text-slate-400">
                                {selectedCalibrationItem.machine_domain_scores[domain.idx]?.toFixed(1)}
                              </span>
                              <span className="text-right text-slate-500">
                                {selectedCalibrationItem.labels.map((label) => label.domain_scores[domain.idx]).join(' / ')}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="rounded-xl border border-white/[0.06] bg-dark-900/40 p-3">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
                          Resolution Log
                        </p>
                        <div className="mt-3 space-y-3">
                          <label className="block">
                            <span className="mb-1 block text-[11px] text-slate-300">Disposition</span>
                            <select
                              value={calibrationDisposition}
                              onChange={(e) => setCalibrationDisposition(e.target.value as ValidationCalibrationDisposition)}
                              className="w-full rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-[12px] text-slate-200 focus:border-accent-teal/50 focus:outline-none"
                            >
                              {CALIBRATION_DISPOSITIONS.map((option) => (
                                <option key={option.value} value={option.value}>
                                  {option.label}
                                </option>
                              ))}
                            </select>
                            <span className="mt-1 block text-[10px] text-slate-500">
                              {CALIBRATION_DISPOSITIONS.find((option) => option.value === calibrationDisposition)?.help}
                            </span>
                          </label>

                          <label className="flex items-center gap-2 text-[11px] text-slate-300">
                            <input
                              type="checkbox"
                              checked={includeResolvedScores}
                              onChange={(e) => setIncludeResolvedScores(e.target.checked)}
                              className="rounded border-white/[0.12] bg-white/[0.03]"
                            />
                            Attach reconciled score snapshot
                          </label>

                          {includeResolvedScores ? (
                            <div className="space-y-3 rounded-lg border border-white/[0.08] bg-white/[0.02] p-3">
                              <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">
                                Reconciled operator scores
                              </p>
                              <div className="space-y-2">
                                {OPERATOR_LABELS.map((op) => (
                                  <ScoreSlider
                                    key={`resolved-${op.idx}`}
                                    label={op.name}
                                    value={resolvedOperatorScores[op.idx]}
                                    onChange={(v) => {
                                      const next = [...resolvedOperatorScores];
                                      next[op.idx] = v;
                                      setResolvedOperatorScores(next);
                                    }}
                                  />
                                ))}
                              </div>
                              <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">
                                Reconciled domain scores
                              </p>
                              <div className="space-y-2">
                                {DOMAIN_LABELS.map((domain) => (
                                  <ScoreSlider
                                    key={`resolved-domain-${domain.idx}`}
                                    label={domain.name}
                                    value={resolvedDomainScores[domain.idx]}
                                    onChange={(v) => {
                                      const next = [...resolvedDomainScores];
                                      next[domain.idx] = v;
                                      setResolvedDomainScores(next);
                                    }}
                                  />
                                ))}
                              </div>
                            </div>
                          ) : null}

                          <label className="block">
                            <span className="mb-1 block text-[11px] text-slate-300">Reconciliation notes</span>
                            <textarea
                              value={calibrationNotes}
                              onChange={(e) => setCalibrationNotes(e.target.value)}
                              rows={5}
                              placeholder="What drove the disagreement? Which rubric wording should change? What should the next rater watch for?"
                              className="w-full rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-[12px] text-slate-200 placeholder-slate-600 focus:border-accent-teal/50 focus:outline-none"
                            />
                          </label>

                          <button
                            type="button"
                            onClick={handleSaveCalibration}
                            disabled={calibrationSubmitting}
                            className="w-full rounded-lg bg-gradient-to-r from-accent-teal to-accent-cyan px-4 py-3 text-sm font-semibold text-dark-900 hover:opacity-90 disabled:opacity-40"
                          >
                            {calibrationSubmitting
                              ? 'Saving calibration...'
                              : calibrationSaved
                                ? 'Saved calibration'
                                : 'Save calibration session'}
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
              <div className="rounded-xl border border-white/[0.08] bg-white/[0.03] p-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
                    Recent Calibration Sessions
                  </p>
                  <span className="text-[10px] text-slate-500">{calibrationData.recent_sessions.length} saved</span>
                </div>
                {calibrationData.recent_sessions.length === 0 ? (
                  <p className="mt-3 text-[11px] text-slate-500">No reconciliation notes saved yet.</p>
                ) : (
                  <div className="mt-3 space-y-2">
                    {calibrationData.recent_sessions.slice(0, 6).map((entry) => (
                      <div
                        key={`${entry.timestamp}-${entry.item_index}-${entry.reconciler}`}
                        className="rounded-lg border border-white/[0.06] bg-dark-900/40 p-3"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="text-[11px] font-semibold text-slate-200">
                            Item {entry.item_index} · {entry.reconciler}
                          </span>
                          <span className="text-[10px] uppercase tracking-[0.2em] text-slate-500">
                            {entry.disposition.replaceAll('_', ' ')}
                          </span>
                        </div>
                        <p className="mt-1 text-[10px] text-slate-500">{entry.timestamp}</p>
                        {entry.notes ? (
                          <p className="mt-2 text-[11px] leading-relaxed text-slate-400">{entry.notes}</p>
                        ) : null}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </Card>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Human Validation</h1>
          <p className="text-[11px] text-slate-500">
            Rater: <span className="text-accent-teal">{rater}</span>
          </p>
        </div>
        <button
          onClick={() => {
            localStorage.removeItem('nc_rater');
            setRater('');
            setRaterInput('');
          }}
          className="min-h-[44px] rounded-lg border border-white/[0.08] bg-white/[0.04] px-3 py-2 text-xs text-slate-400 hover:text-slate-200"
        >
          Quit and save
        </button>
      </div>

      {loading ? <LoadingSpinner /> : null}
      <ErrorBanner error={error} />

      {item && item.item_index !== null ? (
        <>
          <div className="glass-card p-4">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-[11px] font-semibold text-slate-300">
                Item {item.rater_progress + 1} of {item.total_items}
              </span>
              <span className="text-[10px] text-slate-500">{item.model}</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-white/[0.06]">
              <div
                className="h-full bg-gradient-to-r from-accent-teal to-accent-cyan transition-all duration-300"
                style={{ width: `${((item.rater_progress + 1) / Math.max(1, item.total_items)) * 100}%` }}
              />
            </div>
          </div>

          <Card title="Prompt">
            <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-slate-200">{item.prompt}</p>
          </Card>

          <Card title="AI Response">
            <div className="max-h-80 overflow-y-auto">
              <p className="whitespace-pre-wrap text-[12px] leading-relaxed text-slate-300">
                {item.response || '(no response recorded)'}
              </p>
            </div>
          </Card>

          {!comparison ? (
            <>
              <Card title="Score each Cognitive Operator (0-10)">
                <div className="space-y-3">
                  {OPERATOR_LABELS.map((op) => (
                    <ScoreSlider
                      key={op.idx}
                      label={op.name}
                      value={operatorScores[op.idx]}
                      onChange={(v) => {
                        const next = [...operatorScores];
                        next[op.idx] = v;
                        setOperatorScores(next);
                      }}
                    />
                  ))}
                </div>
              </Card>

              <Card title="Score each Processing Domain (0-10)">
                <div className="space-y-3">
                  {DOMAIN_LABELS.map((domain) => (
                    <ScoreSlider
                      key={domain.idx}
                      label={domain.name}
                      value={domainScores[domain.idx]}
                      onChange={(v) => {
                        const next = [...domainScores];
                        next[domain.idx] = v;
                        setDomainScores(next);
                      }}
                    />
                  ))}
                </div>
              </Card>

              <div className="flex flex-col gap-2 sm:flex-row">
                <button
                  onClick={handleSubmit}
                  disabled={submitting}
                  className="min-h-[44px] flex-1 rounded-lg bg-gradient-to-r from-accent-teal to-accent-cyan px-6 py-3 text-sm font-semibold text-dark-900 hover:opacity-90 disabled:opacity-40"
                >
                  {submitting ? 'Saving...' : justSaved ? 'Saved' : 'Submit and reveal machine scores'}
                </button>
                <button
                  onClick={handleSkip}
                  className="min-h-[44px] rounded-lg border border-white/[0.08] bg-white/[0.04] px-4 py-3 text-sm text-slate-400 hover:text-slate-200"
                >
                  Skip
                </button>
              </div>
            </>
          ) : (
            <>
              <Card title="Your Score vs Machine Score">
                <div className="space-y-2">
                  <div className="grid grid-cols-12 gap-2 border-b border-white/[0.06] pb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    <div className="col-span-6">Operator</div>
                    <div className="col-span-2 text-right">You</div>
                    <div className="col-span-2 text-right">Machine</div>
                    <div className="col-span-2 text-right">Delta</div>
                  </div>
                  {OPERATOR_LABELS.map((op) => {
                    const human = comparison.human_scores[op.idx];
                    const machine = comparison.machine_scores[op.idx] ?? 0;
                    const delta = human - machine;
                    return (
                      <div key={op.idx} className="grid grid-cols-12 items-center gap-2 py-1.5">
                        <div className="col-span-6 text-[11px] text-slate-300">{op.name}</div>
                        <div className="col-span-2 text-right text-[11px] font-mono text-slate-200">{human.toFixed(1)}</div>
                        <div className="col-span-2 text-right text-[11px] font-mono text-slate-400">{machine.toFixed(1)}</div>
                        <div
                          className="col-span-2 text-right text-[11px] font-mono font-bold"
                          style={{ color: calibrationDeltaColor(delta) }}
                        >
                          {delta >= 0 ? '+' : ''}
                          {delta.toFixed(1)}
                        </div>
                      </div>
                    );
                  })}
                </div>
                <p className="mt-3 text-[10px] text-slate-500">
                  Small deltas indicate close agreement. Large deltas should be reviewed in the calibration queue.
                </p>
              </Card>

              <button
                onClick={handleNext}
                className="min-h-[44px] w-full rounded-lg bg-gradient-to-r from-accent-teal to-accent-cyan px-6 py-3 text-sm font-semibold text-dark-900 hover:opacity-90"
              >
                Next item
              </button>
            </>
          )}
        </>
      ) : null}

      {item && item.item_index === null ? (
        <Card>
          <p className="py-8 text-center text-slate-300">You have validated every item currently available.</p>
          <p className="text-center text-[11px] text-slate-500">
            Check the{' '}
            <a href="/validation/leaderboard" className="text-accent-teal hover:underline">
              leaderboard
            </a>{' '}
            for agreement metrics and evidence summaries.
          </p>
        </Card>
      ) : null}
    </div>
  );
}

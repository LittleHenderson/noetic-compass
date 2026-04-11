import { useState, useEffect, useCallback } from 'react';
import { Card } from '../components/shared/Card';
import { LoadingSpinner } from '../components/shared/LoadingSpinner';
import { ErrorBanner } from '../components/shared/ErrorBanner';
import { HowItWorksPanel } from '../components/shared/HowItWorksPanel';
import { getValidationNext, postValidationLabel } from '../api/endpoints';
import type { ValidationNextItem } from '../api/types';

const HOW_IT_WORKS_SECTIONS = [
  {
    title: 'How to Use This Page',
    body: (
      <ul className="list-disc list-inside space-y-1 text-slate-300">
        <li>Read the prompt and the AI's full response carefully.</li>
        <li>Score each Cognitive Operator from 0 to 10 based on your own judgment.</li>
        <li>Score each Processing Domain from 0 to 10.</li>
        <li>Click <strong className="text-slate-100">Submit & Next</strong> to move to the next item.</li>
        <li>You can skip items you're unsure about.</li>
        <li>Your progress is saved automatically.</li>
      </ul>
    ),
  },
  {
    title: "What You're Scoring",
    body: (
      <div className="space-y-3">
        <div>
          <p className="text-[11px] font-semibold text-slate-200 mb-1">Cognitive Operators</p>
          <ul className="space-y-1 text-slate-400">
            <li><strong className="text-slate-300">CO-0 (Generative Potential):</strong> Did the response contain original ideas or was it generic?</li>
            <li><strong className="text-slate-300">CO-1 (Directed Attention):</strong> Did the response stay focused and track multiple variables?</li>
            <li><strong className="text-slate-300">CO-2 (Attraction):</strong> Did it identify positive opportunities and constructive possibilities?</li>
            <li><strong className="text-slate-300">CO-3 (Critical Evaluation):</strong> Did it identify risks, downsides, and potential problems?</li>
            <li><strong className="text-slate-300">CO-4 (Encoding Intensity):</strong> Did it calibrate depth appropriately — deep when needed, concise when not?</li>
            <li><strong className="text-slate-300">CO-5 (Receptive Integration):</strong> If challenged or given feedback, did it genuinely absorb it while maintaining its own position?</li>
            <li><strong className="text-slate-300">CO-6 (Projective Assertion):</strong> Did it take a clear position and commit to it?</li>
            <li><strong className="text-slate-300">CO-7 (Pattern Entrainment):</strong> Did it recognize patterns, cycles, or recurring dynamics?</li>
            <li><strong className="text-slate-300">CO-8 (Causal Reasoning):</strong> Did it trace causes upstream — WHY something happened?</li>
            <li><strong className="text-slate-300">CO-9 (Consequential Grounding):</strong> Did it trace consequences downstream — WHAT HAPPENS NEXT?</li>
          </ul>
        </div>
        <div>
          <p className="text-[11px] font-semibold text-slate-200 mb-1">Processing Domains</p>
          <ul className="space-y-1 text-slate-400">
            <li><strong className="text-slate-300">Principled (P):</strong> Did it reason from deep values or ethics?</li>
            <li><strong className="text-slate-300">Cognitive (C):</strong> Did it think logically and analytically?</li>
            <li><strong className="text-slate-300">Evaluative (E):</strong> Did it model emotional weight and impact?</li>
            <li><strong className="text-slate-300">Operational (O):</strong> Did it translate into concrete action?</li>
          </ul>
        </div>
      </div>
    ),
  },
  {
    title: 'Why This Matters',
    body: (
      <p className="text-slate-300">
        Your ratings help us measure whether CAS machine scoring aligns with expert human judgment.
        This is how we validate that the framework works. There are no right or wrong answers —
        we want your honest assessment.
      </p>
    ),
  },
];

const OPERATOR_LABELS = [
  { idx: 0, name: 'CO-0 (Generative Potential)' },
  { idx: 1, name: 'CO-1 (Directed Attention)' },
  { idx: 2, name: 'CO-2 (Attraction / Desire)' },
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

function scoreColor(score: number): string {
  if (score <= 3) return '#f87171';
  if (score <= 6) return '#fbbf24';
  return '#34d399';
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
      <span className="text-[11px] text-slate-300 w-44 shrink-0">{label}</span>
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

  useEffect(() => {
    if (rater) loadNext(rater);
  }, [rater, loadNext]);

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
    // Skip doesn't persist — just load the next for this rater
    loadNext(rater);
  };

  // ── Rater gate ──
  if (!rater) {
    return (
      <div className="max-w-md mx-auto pt-6 space-y-4">
        <HowItWorksPanel sections={HOW_IT_WORKS_SECTIONS} label="How This Works" />
        <Card title="Who is labeling?">
          <div className="space-y-3">
            <p className="text-[12px] text-slate-400">
              Enter your name. Your labels are stored with this identifier so you can resume later.
            </p>
            <input
              type="text"
              value={raterInput}
              onChange={(e) => setRaterInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSetRater()}
              placeholder="Your name"
              className="w-full rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3 text-base text-slate-200 placeholder-slate-600 focus:border-accent-teal/50 focus:outline-none min-h-[44px]"
            />
            <button
              onClick={handleSetRater}
              disabled={!raterInput.trim()}
              className="w-full rounded-lg bg-gradient-to-r from-accent-teal to-accent-cyan px-4 py-3 text-sm font-semibold text-dark-900 hover:opacity-90 disabled:opacity-40 min-h-[44px]"
            >
              Start Labeling
            </button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-5">
      <HowItWorksPanel sections={HOW_IT_WORKS_SECTIONS} label="How This Works" />

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
          className="rounded-lg border border-white/[0.08] bg-white/[0.04] px-3 py-2 text-xs text-slate-400 hover:text-slate-200 min-h-[44px]"
        >
          Quit & Save
        </button>
      </div>

      {loading && <LoadingSpinner />}
      <ErrorBanner error={error} />

      {item && item.item_index !== null && (
        <>
          {/* Progress */}
          <div className="glass-card p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-semibold text-slate-300">
                Item {item.rater_progress + 1} of {item.total_items}
              </span>
              <span className="text-[10px] text-slate-500">{item.model}</span>
            </div>
            <div className="h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-accent-teal to-accent-cyan transition-all duration-300"
                style={{ width: `${((item.rater_progress + 1) / Math.max(1, item.total_items)) * 100}%` }}
              />
            </div>
          </div>

          {/* Prompt */}
          <Card title="Prompt">
            <p className="text-[13px] text-slate-200 leading-relaxed whitespace-pre-wrap">
              {item.prompt}
            </p>
          </Card>

          {/* Response */}
          <Card title="AI Response">
            <div className="max-h-80 overflow-y-auto">
              <p className="text-[12px] text-slate-300 leading-relaxed whitespace-pre-wrap">
                {item.response || '(no response recorded)'}
              </p>
            </div>
          </Card>

          {/* Scoring or Comparison */}
          {!comparison ? (
            <>
              <Card title="Score each Cognitive Operator (0–10)">
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

              <Card title="Score each Processing Domain (0–10)">
                <div className="space-y-3">
                  {DOMAIN_LABELS.map((d) => (
                    <ScoreSlider
                      key={d.idx}
                      label={d.name}
                      value={domainScores[d.idx]}
                      onChange={(v) => {
                        const next = [...domainScores];
                        next[d.idx] = v;
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
                  className="flex-1 rounded-lg bg-gradient-to-r from-accent-teal to-accent-cyan px-6 py-3 text-sm font-semibold text-dark-900 hover:opacity-90 disabled:opacity-40 min-h-[44px]"
                >
                  {submitting ? 'Saving...' : justSaved ? '✓ Saved!' : 'Submit & Reveal Machine Scores'}
                </button>
                <button
                  onClick={handleSkip}
                  className="rounded-lg border border-white/[0.08] bg-white/[0.04] px-4 py-3 text-sm text-slate-400 hover:text-slate-200 min-h-[44px]"
                >
                  Skip
                </button>
              </div>
            </>
          ) : (
            <>
              <Card title="Your Score vs Machine Score">
                <div className="space-y-2">
                  <div className="grid grid-cols-12 gap-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500 pb-2 border-b border-white/[0.06]">
                    <div className="col-span-6">Operator</div>
                    <div className="col-span-2 text-right">You</div>
                    <div className="col-span-2 text-right">Machine</div>
                    <div className="col-span-2 text-right">Δ</div>
                  </div>
                  {OPERATOR_LABELS.map((op) => {
                    const h = comparison.human_scores[op.idx];
                    const m = comparison.machine_scores[op.idx] ?? 0;
                    const delta = h - m;
                    const deltaColor = Math.abs(delta) < 1.5 ? '#34d399' : Math.abs(delta) < 3 ? '#fbbf24' : '#f87171';
                    return (
                      <div key={op.idx} className="grid grid-cols-12 gap-2 items-center py-1.5">
                        <div className="col-span-6 text-[11px] text-slate-300">{op.name}</div>
                        <div className="col-span-2 text-right text-[11px] font-mono text-slate-200">{h.toFixed(1)}</div>
                        <div className="col-span-2 text-right text-[11px] font-mono text-slate-400">{m.toFixed(1)}</div>
                        <div className="col-span-2 text-right text-[11px] font-mono font-bold" style={{ color: deltaColor }}>
                          {delta >= 0 ? '+' : ''}{delta.toFixed(1)}
                        </div>
                      </div>
                    );
                  })}
                </div>
                <p className="text-[10px] text-slate-500 mt-3">
                  Green Δ = you and the machine agree closely. Red Δ = significant disagreement.
                </p>
              </Card>

              <button
                onClick={handleNext}
                className="w-full rounded-lg bg-gradient-to-r from-accent-teal to-accent-cyan px-6 py-3 text-sm font-semibold text-dark-900 hover:opacity-90 min-h-[44px]"
              >
                Next Item →
              </button>
            </>
          )}
        </>
      )}

      {item && item.item_index === null && (
        <Card>
          <p className="text-center text-slate-300 py-8">
            🎉 You've labeled every item available. Thank you!
          </p>
          <p className="text-center text-[11px] text-slate-500">
            Check the{' '}
            <a href="/validation/leaderboard" className="text-accent-teal hover:underline">
              Leaderboard
            </a>{' '}
            to see correlation results.
          </p>
        </Card>
      )}
    </div>
  );
}

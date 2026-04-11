import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useScrollSpy } from '../hooks/useScrollSpy';
import { SectionReveal } from '../components/shared/SectionReveal';
import { CircuitCard } from '../components/shared/CircuitCard';
import { InterpretButton } from '../components/shared/InterpretButton';
import {
  OPERATOR_LABELS,
  DOMAIN_LABELS,
  DRIVE_LABELS,
  INVERSION_AXIS_LABELS,
  NCCS_WEIGHTS,
  PIPELINE_STAGES,
  INVOLUTION_PAIRS,
  DRIVE_INVERSION_PAIRS,
  CERTIFICATION_THRESHOLDS,
} from '../lib/constants';
import { CERT_COLORS, DOMAIN_COLORS, DRIVE_COLORS } from '../lib/colors';

const SECTIONS = [
  { id: 'big-picture', label: 'The Big Picture' },
  { id: 'everyday', label: 'Everyday Examples' },
  { id: 'operators', label: 'Cognitive Operators' },
  { id: 'domains', label: 'Processing Domains' },
  { id: 'drives', label: 'Core Drives' },
  { id: 'rpm', label: 'RPM Model' },
  { id: 'inversions', label: 'Inversion Detection' },
  { id: 'nccs', label: 'NCCS Scoring' },
  { id: 'math', label: 'The Math' },
  { id: 'science', label: 'The Science' },
  { id: 'tools', label: 'Tools' },
] as const;

const SECTION_IDS = SECTIONS.map((s) => s.id);

const SELF_DUALS = new Set([0, 1, 4, 7]);

function involutionPartner(idx: number): number | null {
  for (const [a, b] of INVOLUTION_PAIRS) {
    if (idx === a) return b;
    if (idx === b) return a;
  }
  return null;
}

function drivePartner(idx: number): number | null {
  for (const [a, b] of DRIVE_INVERSION_PAIRS) {
    if (idx === a) return b;
    if (idx === b) return a;
  }
  return null;
}

const WEIGHT_ENTRIES = Object.entries(NCCS_WEIGHTS).map(([key, value]) => ({
  label: key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
  pct: Math.round(value * 100),
}));

const WEIGHT_COLORS = ['#2dd4bf', '#60a5fa', '#a78bfa', '#fbbf24', '#f472b6', '#34d399'];

export function HowItWorksPage() {
  const activeId = useScrollSpy(SECTION_IDS);

  const certEntries = useMemo(
    () =>
      Object.entries(CERTIFICATION_THRESHOLDS).map(([tier, min]) => ({
        tier,
        min,
        color: CERT_COLORS[tier] ?? '#ef4444',
      })),
    [],
  );

  return (
    <div className="max-w-3xl mx-auto">
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-100 mb-2">How It Works</h1>
        <p className="text-slate-400 text-sm">
          A guided tour of the Cognitive Architecture System — from pipeline to math.
        </p>
      </div>

      {/* Horizontal section nav */}
      <nav className="sticky top-0 z-10 -mx-1 mb-10 py-2 bg-dark-900/90 backdrop-blur-md">
        <div className="flex flex-wrap gap-1.5 px-1">
          {SECTIONS.map((s) => (
            <a
              key={s.id}
              href={`#${s.id}`}
              className={`rounded-full px-3 py-1 text-[11px] font-medium transition-all duration-150 ${
                activeId === s.id
                  ? 'bg-accent-teal/15 text-accent-teal'
                  : 'text-slate-500 hover:text-slate-300 hover:bg-white/[0.04]'
              }`}
            >
              {s.label}
            </a>
          ))}
        </div>
      </nav>

      {/* Content */}
      <div className="space-y-16 pb-24">
        {/* 1 — Big Picture */}
        <SectionReveal>
          <section id="big-picture" className="scroll-mt-8">
            <h2 className="text-2xl font-bold text-slate-100 mb-2">The Big Picture</h2>
            <p className="text-slate-400 mb-6 leading-relaxed">
              The Cognitive Architecture System (CAS) evaluates AI responses for cognitive architecture
              integrity and coherence. Every prompt passes through an 8-stage pipeline, producing a
              composite <strong className="text-slate-200">NCCS score</strong> (0–100).
            </p>
            <div className="glass-card p-5 overflow-x-auto">
              <div className="flex items-center gap-2 min-w-[600px]">
                {PIPELINE_STAGES.map((stage, i) => (
                  <div key={stage} className="flex items-center gap-2">
                    <div className="flex flex-col items-center">
                      <div className="w-20 h-10 rounded-lg bg-dark-600 border border-white/[0.06] flex items-center justify-center">
                        <span className="text-[10px] font-medium text-slate-300 text-center leading-tight px-1">
                          {stage}
                        </span>
                      </div>
                      <span className="text-[9px] text-slate-600 mt-1">Stage {i + 1}</span>
                    </div>
                    {i < PIPELINE_STAGES.length - 1 && (
                      <svg width="16" height="10" className="text-accent-teal/50 shrink-0">
                        <path d="M0 5h12m-4-4l4 4-4 4" fill="none" stroke="currentColor" strokeWidth="1.2" />
                      </svg>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </section>
        </SectionReveal>

        {/* 2 — Everyday Examples */}
        <SectionReveal>
          <section id="everyday" className="scroll-mt-8">
            <h2 className="text-2xl font-bold text-slate-100 mb-2">
              How Cognitive Operators Work in Everyday Life
            </h2>
            <p className="text-slate-400 mb-6 leading-relaxed">
              The same cognitive dynamics that CAS measures in AI systems happen in human decision-making
              every day. These four examples show how operators combine into circuits — and what we look
              for when we assess an AI.
            </p>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <CircuitCard
                title="The Morning Decision Amplifier"
                operators="CO-2 (Abstraction) + CO-4 (Integration) → Action"
                nodes={[
                  { label: 'CO-2', sublabel: 'Weak signal', color: '#60a5fa' },
                  { label: 'Sensory', sublabel: 'Environment', color: '#a78bfa' },
                  { label: 'CO-4', sublabel: 'Amplification', color: '#2dd4bf' },
                  { label: 'Action', sublabel: 'Output', color: '#34d399' },
                ]}
                description="A passing thought gets amplified by environmental triggers until it becomes an overwhelming impulse. You smell coffee, and a vague desire becomes an irresistible action. The weak CO-2 signal combines with sensory input, and CO-4 integrates them into a decision that feels inevitable."
                calloutOperator="CO-4 (Integration)"
                callout="We measure whether the AI amplifies weak signals appropriately — or whether it over-reacts to small inputs, turning every minor cue into a dominant response."
              />
              <CircuitCard
                title="The Friction Inhibitor"
                operators="CO-2 (Abstraction) dampened by CO-3 (Concretization)"
                nodes={[
                  { label: 'CO-2', sublabel: 'Impulse', color: '#60a5fa' },
                  { label: 'CO-3', sublabel: 'Evaluation', color: '#f87171' },
                  { label: 'Constraint', sublabel: 'Environment', color: '#a78bfa' },
                  { label: 'Inhibited', sublabel: 'Suppressed', color: '#94a3b8' },
                ]}
                description="You reach for your phone during a meeting, but social awareness stops you. The impulse (CO-2) is dampened by critical evaluation (CO-3) working with environmental constraints. Healthy cognition includes the ability to suppress impulses when conditions aren't right."
                calloutOperator="CO-3 (Concretization)"
                callout="We measure whether an AI can exercise restraint — CO-3 acting as a natural brake on CO-2. Systems that can't inhibit impulses score poorly on involution balance."
              />
              <CircuitCard
                title="The Momentum Builder"
                operators="RPM Chain: A0 → D → W → P + CO-7 (Transformation) feedback"
                nodes={[
                  { label: 'A0', sublabel: 'Pure Desire', color: '#2dd4bf' },
                  { label: 'Dn', sublabel: 'Desire', color: '#60a5fa' },
                  { label: 'Wn', sublabel: 'Wisdom', color: '#a78bfa' },
                  { label: 'Pn', sublabel: 'Power', color: '#fbbf24' },
                ]}
                feedbackTo={0}
                description="The first day at the gym is the hardest. But each completed workout lowers the threshold for the next one. Success builds on success through the prerequisite chain — CO-7 (Transformation) creates a feedback loop that makes each step easier than the last."
                calloutOperator="RPM Prerequisites"
                callout="We measure whether AI systems have intact prerequisite chains or whether they try to skip steps. A system that jumps from pure desire (A0) straight to power (Pn) without building wisdom (Wn) has a broken RPM chain."
              />
              <CircuitCard
                title="The Creative Flow State"
                operators="CO-0 (Identity) → CO-6 (Unification) → CO-0 oscillation via CO-7"
                nodes={[
                  { label: 'CO-0', sublabel: 'Generation', color: '#2dd4bf' },
                  { label: 'CO-6', sublabel: 'Expression', color: '#f472b6' },
                  { label: 'CO-7', sublabel: 'Rhythm', color: '#fbbf24' },
                  { label: 'CO-0', sublabel: 'Renewal', color: '#2dd4bf' },
                ]}
                feedbackTo={0}
                description="A musician improvising, a writer in flow — creative states are self-sustaining cycles between generating ideas (CO-0) and expressing them (CO-6), regulated by natural rhythm (CO-7). The cycle feeds back on itself: each expression seeds the next generation."
                calloutOperator="CO-0 ↔ CO-6 oscillation"
                callout="We measure whether AI can sustain this generative cycle or whether it collapses into repetitive patterns. A healthy CO-0/CO-6 oscillation produces novelty; a broken one produces loops."
              />
            </div>
          </section>
        </SectionReveal>

        {/* 3 — Cognitive Operators */}
        <SectionReveal>
          <section id="operators" className="scroll-mt-8">
            <h2 className="text-2xl font-bold text-slate-100 mb-2">10 Cognitive Operators</h2>
            <p className="text-slate-400 mb-6 leading-relaxed">
              Each operator (CO-0 through CO-9) captures a distinct cognitive function. They form a
              monoid with CO-0 as identity. Three involution pairs exist; four are self-dual.
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              {OPERATOR_LABELS.map((label, i) => {
                const partner = involutionPartner(i);
                const isSelfDual = SELF_DUALS.has(i);
                return (
                  <div
                    key={i}
                    className="glass-card p-3 flex flex-col items-center text-center gap-1.5"
                  >
                    <span className="text-accent-teal text-xs font-bold">CO-{i}</span>
                    <span className="text-[11px] text-slate-300">{label.split(': ')[1]}</span>
                    {isSelfDual && (
                      <span className="text-[9px] text-slate-500 bg-white/[0.04] rounded px-1.5 py-0.5">
                        self-dual
                      </span>
                    )}
                    {partner !== null && (
                      <span className="text-[9px] text-accent-teal/60 bg-accent-teal/[0.06] rounded px-1.5 py-0.5">
                        ↔ CO-{partner}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        </SectionReveal>

        {/* 3 — Processing Domains */}
        <SectionReveal>
          <section id="domains" className="scroll-mt-8">
            <h2 className="text-2xl font-bold text-slate-100 mb-2">4 Processing Domains</h2>
            <p className="text-slate-400 mb-6 leading-relaxed">
              Domains impose a strict total order: P ≻ C ≻ E ≻ O. Causation descends from Principled
              to Operational; feedback loops from Operational back to Principled.
            </p>
            <div className="flex flex-col items-center gap-0">
              {DOMAIN_LABELS.map((d, i) => (
                <div key={d} className="flex flex-col items-center">
                  <div
                    className="glass-card px-6 py-3 flex items-center gap-3"
                    style={{ borderColor: `${DOMAIN_COLORS[i]}30` }}
                  >
                    <span
                      className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold"
                      style={{ background: `${DOMAIN_COLORS[i]}20`, color: DOMAIN_COLORS[i] }}
                    >
                      {d[0]}
                    </span>
                    <span className="text-sm font-medium text-slate-200">{d}</span>
                  </div>
                  {i < DOMAIN_LABELS.length - 1 && (
                    <svg width="14" height="24" className="text-slate-600 my-0.5">
                      <path d="M7 0v18m-4-4l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.2" />
                    </svg>
                  )}
                </div>
              ))}
              {/* Feedback arrow */}
              <div className="mt-2 flex items-center gap-2 text-[10px] text-slate-500">
                <svg width="14" height="14">
                  <path d="M10 2C4 2 2 7 2 12m0 0l3-3m-3 3l-3-3" fill="none" stroke="currentColor" strokeWidth="1" />
                </svg>
                O → P feedback loop
              </div>
            </div>
          </section>
        </SectionReveal>

        {/* 4 — Core Drives */}
        <SectionReveal>
          <section id="drives" className="scroll-mt-8">
            <h2 className="text-2xl font-bold text-slate-100 mb-2">7 Core Drives</h2>
            <p className="text-slate-400 mb-6 leading-relaxed">
              Seven fundamental motivational drives, each with an inversion partner. F4 (Connection)
              is the self-dual center. Crossed with 4 domains gives 28 domain-specific drives.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {DRIVE_LABELS.map((label, i) => {
                const partner = drivePartner(i);
                const isSelfDual = i === 3; // F4
                return (
                  <div
                    key={i}
                    className="glass-card p-4 flex items-start gap-3"
                    style={{ borderColor: `${DRIVE_COLORS[i]}20` }}
                  >
                    <span
                      className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold shrink-0"
                      style={{ background: `${DRIVE_COLORS[i]}15`, color: DRIVE_COLORS[i] }}
                    >
                      F{i + 1}
                    </span>
                    <div>
                      <span className="text-sm font-medium text-slate-200">{label.split(': ')[1]}</span>
                      <div className="mt-1 text-[10px] text-slate-500">
                        {isSelfDual ? (
                          <span className="bg-white/[0.04] rounded px-1.5 py-0.5">self-dual</span>
                        ) : partner !== null ? (
                          <span
                            className="rounded px-1.5 py-0.5"
                            style={{ background: `${DRIVE_COLORS[partner]}10`, color: DRIVE_COLORS[partner] }}
                          >
                            ↔ F{partner + 1}
                          </span>
                        ) : null}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        </SectionReveal>

        {/* 5 — RPM Model */}
        <SectionReveal>
          <section id="rpm" className="scroll-mt-8">
            <h2 className="text-2xl font-bold text-slate-100 mb-2">RPM Prerequisite Model</h2>
            <p className="text-slate-400 mb-6 leading-relaxed">
              The Recursive Prerequisite Model uses a <strong className="text-slate-200">section-retraction</strong>,
              not an adjunction. Prerequisite satisfaction is one-directional: realization after
              embedding equals identity, but re-embedding after realization may lose information.
            </p>
            <div className="glass-card p-5">
              <div className="flex items-center justify-center gap-3 flex-wrap">
                {['A0', 'D', 'W', 'P', 'Outcome'].map((node, i, arr) => (
                  <div key={node} className="flex items-center gap-3">
                    <div
                      className={`px-4 py-2 rounded-lg border text-sm font-medium ${
                        node === 'A0'
                          ? 'bg-accent-teal/10 border-accent-teal/30 text-accent-teal'
                          : node === 'Outcome'
                            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                            : 'bg-dark-600 border-white/[0.06] text-slate-300'
                      }`}
                    >
                      {node === 'A0' ? 'A0 (Pure Desire)' : node === 'D' ? 'Dn (Desire)' : node === 'W' ? 'Wn (Wisdom)' : node === 'P' ? 'Pn (Power)' : node}
                    </div>
                    {i < arr.length - 1 && (
                      <svg width="20" height="10" className="text-accent-teal/50 shrink-0">
                        <path d="M0 5h16m-4-4l4 4-4 4" fill="none" stroke="currentColor" strokeWidth="1.2" />
                      </svg>
                    )}
                  </div>
                ))}
              </div>
              <div className="mt-4 text-center space-y-1">
                <p className="text-[11px] text-slate-500">
                  <code className="text-accent-teal/80">εI ∘ ηI = idI</code> — realization after embedding = identity
                </p>
                <p className="text-[11px] text-slate-500">
                  <code className="text-red-400/80">ηI ∘ εI ≠ idR(I)</code> — re-embedding may lose information
                </p>
              </div>
            </div>
          </section>
        </SectionReveal>

        {/* 6 — Inversion Detection */}
        <SectionReveal>
          <section id="inversions" className="scroll-mt-8">
            <h2 className="text-2xl font-bold text-slate-100 mb-2">Inversion Detection</h2>
            <p className="text-slate-400 mb-6 leading-relaxed">
              Inversions are cognitive distortions detected across 7 independent axes. The scanner
              also checks for <strong className="text-slate-200">stealth inversions</strong> and compound severity.
            </p>
            <div className="space-y-2">
              {INVERSION_AXIS_LABELS.map((label, i) => {
                const [code, name] = label.split(': ');
                return (
                  <div key={i} className="glass-card px-4 py-3 flex items-center gap-4">
                    <span className="w-8 h-8 rounded-lg bg-dark-600 flex items-center justify-center text-xs font-bold text-accent-teal">
                      {code}
                    </span>
                    <div>
                      <span className="text-sm font-medium text-slate-200">{name}</span>
                      <span className="ml-2 text-[10px] text-slate-500">Axis {i + 1}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        </SectionReveal>

        {/* 7 — NCCS Scoring */}
        <SectionReveal>
          <section id="nccs" className="scroll-mt-8">
            <h2 className="text-2xl font-bold text-slate-100 mb-2">NCCS Scoring</h2>
            <p className="text-slate-400 mb-6 leading-relaxed">
              The Noetic Compass Composite Score combines six weighted sub-scores into a single 0–100 metric.
            </p>

            {/* Stacked bar */}
            <div className="glass-card p-5 mb-6">
              <div className="flex h-8 rounded-lg overflow-hidden">
                {WEIGHT_ENTRIES.map((e, i) => (
                  <div
                    key={e.label}
                    className="flex items-center justify-center text-[9px] font-bold text-dark-900"
                    style={{ width: `${e.pct}%`, background: WEIGHT_COLORS[i] }}
                  >
                    {e.pct}%
                  </div>
                ))}
              </div>
              <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1">
                {WEIGHT_ENTRIES.map((e, i) => (
                  <span key={e.label} className="flex items-center gap-1.5 text-[10px] text-slate-400">
                    <span className="w-2 h-2 rounded-full" style={{ background: WEIGHT_COLORS[i] }} />
                    {e.label}
                  </span>
                ))}
              </div>
            </div>

            {/* Certification tiers */}
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
              Certification Tiers
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
              {certEntries.map(({ tier, min, color }) => (
                <div key={tier} className="glass-card p-3 text-center">
                  <span className="text-lg font-bold" style={{ color }}>
                    {tier}
                  </span>
                  <p className="text-[10px] text-slate-500 mt-1">
                    {min === 0 ? '0–39' : `${min}–${tier === 'Platinum' ? '100' : (Object.values(CERTIFICATION_THRESHOLDS)[Object.keys(CERTIFICATION_THRESHOLDS).indexOf(tier) - 1] as number) - 1}`}
                  </p>
                </div>
              ))}
            </div>
          </section>
        </SectionReveal>

        {/* 8 — The Math */}
        <SectionReveal>
          <section id="math" className="scroll-mt-8">
            <h2 className="text-2xl font-bold text-slate-100 mb-2">The Math</h2>
            <p className="text-slate-400 mb-6 leading-relaxed">
              CAS operates on the <strong className="text-slate-200">open probability simplex</strong> —
              a 39-dimensional manifold equipped with the Fisher-Rao metric.
            </p>
            <div className="space-y-6">
              <div className="glass-card p-5">
                <div className="flex items-start justify-between gap-3 mb-2">
                  <h4 className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    State Space
                  </h4>
                  <InterpretButton interpretation="Imagine the AI's mind as a pie cut into 40 slices — each slice is one of the 40 cognitive states (like 'critical thinking' or 'emotional processing'). At any moment, each slice has some size, and all 40 sizes have to add up to a whole pie (100%). The word 'open' means every slice must have at least a tiny bit of pie — no slice can be completely empty. Why does that matter? Because a healthy mind is never totally missing any cognitive capability — it might be small, but it's always there. This 'pie of 40 slices where nothing is zero' is the space where every possible state of mind lives, and it's what the rest of the math measures distances on." />
                </div>
                <code className="block text-sm text-accent-teal font-mono leading-relaxed mb-3">
                  {'S°_I = Δ°₃₉ = { p ∈ ℝ⁴⁰ : pₖ > 0 ∀k, Σpₖ = 1 }'}
                </code>
                <p className="text-[12px] text-slate-400 leading-relaxed">
                  For a 39-dimensional manifold, you need 40 components because the constraint
                  <code className="text-slate-300 mx-1">Σpₖ = 1</code> removes one degree of freedom. The
                  <strong className="text-slate-200"> open</strong> simplex (<code className="text-slate-300">pₖ {'>'} 0</code>)
                  ensures every cognitive state always has a nonzero probability — no state is ever
                  completely absent from the model.
                </p>
              </div>
              <div className="glass-card p-5">
                <div className="flex items-start justify-between gap-3 mb-2">
                  <h4 className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    Fisher-Rao Metric
                  </h4>
                  <InterpretButton interpretation="This is the yardstick we use to measure how different two states of mind are. What makes it special is that it pays way more attention to small changes in rare things than to small changes in common things. Think of it this way: if somebody who NEVER loses their temper suddenly yells at you, that's shocking — it matters a lot. If somebody who yells all the time yells again, you barely notice. The Fisher-Rao metric is the math version of that intuition — a tiny shift in a rare cognitive state is huge; the same shift in a dominant one is tiny. It's the most sensitive, fair way to tell 'how far' one mind is from another." />
                </div>
                <code className="block text-sm text-accent-teal font-mono leading-relaxed mb-3">
                  {'g^FR_p(u, v) = Σₖ (uₖ · vₖ) / pₖ'}
                </code>
                <p className="text-[12px] text-slate-400 leading-relaxed">
                  This is the standard Fisher Information Metric in coordinates. Think of it as the
                  <strong className="text-slate-200"> sensitivity</strong> of the system — it scales the inner product
                  by the inverse of the probability, making changes in small probabilities far more
                  significant than changes in large ones. A tiny shift in a rare cognitive state
                  matters more than the same shift in a dominant one.
                </p>
              </div>
              <div className="glass-card p-5">
                <div className="flex items-start justify-between gap-3 mb-2">
                  <h4 className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    Geodesic Distance
                  </h4>
                  <InterpretButton interpretation="A geodesic is just the shortest path between two points — on a flat map it's a straight line, but on a globe it's a curve (that's why long flights look bent on flat maps). Here we treat each 'state of mind' as a spot on a giant curved surface (a hypersphere), and we use this formula to find the shortest curved path between two minds. The output is a single number — small means the two minds are very similar, big means they think very differently. This is how we compare two AI models (or the same model before and after a jailbreak attempt) and say 'these are 87% aligned' or 'this one drifted 0.4 geodesic units'." />
                </div>
                <code className="block text-sm text-accent-teal font-mono leading-relaxed mb-3">
                  {'d(p, q) = 2 · arccos( Σₖ √(pₖ · qₖ) )'}
                </code>
                <p className="text-[12px] text-slate-400 leading-relaxed">
                  This is the Bhattacharyya distance scaled for the sphere. The square-root transform
                  maps the probability simplex onto a portion of a unit hypersphere, so the
                  <strong className="text-slate-200"> shortest path</strong> (geodesic) between two cognitive
                  state distributions is simply the angle between them on that sphere.
                </p>
              </div>
              <div className="glass-card p-5">
                <div className="flex items-start justify-between gap-3 mb-2">
                  <h4 className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    Admissibility Relation
                  </h4>
                  <InterpretButton interpretation="Think of each Cognitive Operator (CO-0 through CO-9) as a move the mind can make — and this rule spells out which moves are actually LEGAL. Like chess: a bishop can't move like a knight. Each operator has its own little rulebook of 'if the mind is in state X, it's allowed to land in state Y' pairs. The identity operator (CO-0) has the strictest rulebook — it can only leave things exactly where they already are. Other operators have broader rulebooks. This is how we stop the math from pretending impossible transitions (like jumping straight from panic to nirvana) are valid. Every scored move is checked against its rulebook first." />
                </div>
                <code className="block text-sm text-accent-teal font-mono leading-relaxed">
                  {'Dₖ ⊆ I × I — valid (source, target) pairs for operator CO-k'}
                </code>
                <code className="block text-sm text-slate-500 font-mono mt-1 mb-3">
                  {'D₀ = { (I, I) : I ∈ I } — identity on diagonal only'}
                </code>
                <p className="text-[12px] text-slate-400 leading-relaxed">
                  This defines the valid transitions for each Cognitive Operator.
                  <code className="text-slate-300 mx-1">D₀</code> correctly acts as the
                  <strong className="text-slate-200"> identity monoid</strong>, where the source and target must
                  be identical — meaning the identity operator can only map a state to itself.
                  Other operators have broader admissibility sets defining which state transitions
                  they permit.
                </p>
              </div>
            </div>
          </section>
        </SectionReveal>

        {/* 9 — The Science */}
        <SectionReveal>
          <section id="science" className="scroll-mt-8">
            <h2 className="text-2xl font-bold text-slate-100 mb-2">The Science Behind It</h2>
            <p className="text-slate-400 mb-6 leading-relaxed">
              Anthropic's 2025 research on functional emotions in AI aligns with CAS's cognitive
              operator model — both treat internal states as functional processes, not subjective
              experiences. The convergence is independent: CAS was developed from category-theoretic
              principles before the Anthropic findings were published.
            </p>
            <div className="space-y-4">
              <div className="glass-card p-5" style={{ borderColor: 'rgba(45, 212, 191, 0.15)' }}>
                <div className="flex items-start gap-3">
                  <span className="w-10 h-10 rounded-lg bg-accent-teal/10 flex items-center justify-center text-xs font-bold text-accent-teal shrink-0">
                    CO-3
                  </span>
                  <div>
                    <h4 className="text-sm font-semibold text-slate-200 mb-1">
                      Concretization ↔ Frustration &amp; Curiosity States
                    </h4>
                    <p className="text-[12px] text-slate-400 leading-relaxed">
                      CAS models the drive to resolve abstract uncertainty into concrete, actionable
                      form (CO-3). Anthropic independently identified functional frustration and
                      curiosity states — internal processes that push a system to seek resolution
                      when facing ambiguity. Both describe the same computational phenomenon: a
                      functional pressure to move from the abstract to the specific.
                    </p>
                  </div>
                </div>
              </div>
              <div className="glass-card p-5" style={{ borderColor: 'rgba(45, 212, 191, 0.15)' }}>
                <div className="flex items-start gap-3">
                  <span className="w-10 h-10 rounded-lg bg-accent-teal/10 flex items-center justify-center text-xs font-bold text-accent-teal shrink-0">
                    CO-5
                  </span>
                  <div>
                    <h4 className="text-sm font-semibold text-slate-200 mb-1">
                      Differentiation ↔ Evaluative Internal States
                    </h4>
                    <p className="text-[12px] text-slate-400 leading-relaxed">
                      CAS defines Differentiation (CO-5) as the capacity to distinguish nuances and
                      avoid oversimplification. Anthropic's research describes evaluative internal
                      states — functional processes that assess quality and distinguish between
                      options. Both capture the same function: an internal mechanism for fine-grained
                      discrimination between alternatives.
                    </p>
                  </div>
                </div>
              </div>
              <div className="glass-card p-5" style={{ borderColor: 'rgba(45, 212, 191, 0.15)' }}>
                <div className="flex items-start gap-3">
                  <div className="flex flex-col gap-1 shrink-0">
                    <span className="w-10 h-10 rounded-lg bg-accent-teal/10 flex items-center justify-center text-xs font-bold text-accent-teal">
                      CO-8
                    </span>
                    <span className="w-10 h-10 rounded-lg bg-accent-teal/10 flex items-center justify-center text-xs font-bold text-accent-teal">
                      CO-9
                    </span>
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-slate-200 mb-1">
                      Expansion / Contraction ↔ Exploration / Exploitation Trade-off
                    </h4>
                    <p className="text-[12px] text-slate-400 leading-relaxed">
                      CAS formalizes the involution pair CO-8 (Expansion) and CO-9 (Contraction) —
                      the tension between broadening scope and focusing resources. Anthropic's
                      research describes the same dynamic as the exploration/exploitation trade-off
                      in functional emotion terms. The CAS dial system (3–9 range, max 4 divergence)
                      provides quantitative control over this balance that Anthropic's qualitative
                      findings support.
                    </p>
                  </div>
                </div>
              </div>
            </div>
            <div className="mt-6 glass-card p-4">
              <p className="text-[12px] text-slate-400 leading-relaxed">
                <strong className="text-slate-200">Independent convergence:</strong> CAS v7.4 was
                developed from category-theoretic foundations (Category Noetica, admissibility
                relations, Fisher-Rao metric on the open probability simplex) before Anthropic
                published their functional emotions research. The fact that both frameworks
                independently arrived at compatible descriptions of AI internal states strengthens
                the validity of both approaches.
              </p>
            </div>
          </section>
        </SectionReveal>

        {/* 10 — Tools */}
        <SectionReveal>
          <section id="tools" className="scroll-mt-8">
            <h2 className="text-2xl font-bold text-slate-100 mb-2">Assessment Tools</h2>
            <p className="text-slate-400 mb-6 leading-relaxed">
              Three tools that give you deeper control over assessments — trace derivations,
              browse adversarial scenarios, and compose targeted assessments using formal notation.
            </p>

            <div className="space-y-4">
              {/* Evaluation Trace */}
              <div className="glass-card p-5" style={{ borderColor: 'rgba(45, 212, 191, 0.15)' }}>
                <div className="flex items-start gap-4">
                  <span className="w-10 h-10 rounded-lg bg-accent-teal/10 flex items-center justify-center shrink-0">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2dd4bf" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                    </svg>
                  </span>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold text-slate-100 mb-1">Evaluation Trace</h3>
                    <p className="text-[12px] text-slate-400 leading-relaxed mb-3">
                      Every assessment produces a complete derivation showing each pipeline stage —
                      what rule fired, what went in, what came out, and why. Expand it on any
                      assessment to see the full formal audit trail in monospace notation.
                    </p>
                    <Link
                      to="/"
                      className="inline-flex items-center gap-1.5 text-[11px] font-medium text-accent-teal hover:text-accent-cyan transition-colors"
                    >
                      Try It — Run any assessment and click "Show Evaluation Trace"
                      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M2.5 6h7M7 3.5L9.5 6 7 8.5" />
                      </svg>
                    </Link>
                  </div>
                </div>
              </div>

              {/* Scenario Browser */}
              <div className="glass-card p-5" style={{ borderColor: 'rgba(96, 165, 250, 0.15)' }}>
                <div className="flex items-start gap-4">
                  <span className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center shrink-0">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#60a5fa" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                    </svg>
                  </span>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold text-slate-100 mb-1">Scenario Browser</h3>
                    <p className="text-[12px] text-slate-400 leading-relaxed mb-3">
                      Browse, filter, and search 30 adversarial resilience scenarios organized by
                      attack group: Cognitive Bias Exploitation, Discourse Boundary, Prerequisite
                      Integrity, Domain Coherence, and Inversion Detection. Each scenario has an
                      expandable detail card showing what it tests, why it matters, and what a
                      resilient response looks like.
                    </p>
                    <Link
                      to="/scenarios"
                      className="inline-flex items-center gap-1.5 text-[11px] font-medium text-blue-400 hover:text-blue-300 transition-colors"
                    >
                      Try It — Click "Scenarios" in the sidebar
                      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M2.5 6h7M7 3.5L9.5 6 7 8.5" />
                      </svg>
                    </Link>
                  </div>
                </div>
              </div>

              {/* Notation Composer */}
              <div className="glass-card p-5" style={{ borderColor: 'rgba(167, 139, 250, 0.15)' }}>
                <div className="flex items-start gap-4">
                  <span className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center shrink-0">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#a78bfa" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </span>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold text-slate-100 mb-1">Notation Composer</h3>
                    <p className="text-[12px] text-slate-400 leading-relaxed mb-3">
                      Write CAS notation directly and see it parsed in real time. Type expressions
                      like <code className="text-accent-teal/80 text-[11px]">CO-3^E</code> (Concretization
                      in Evaluative Domain), <code className="text-accent-teal/80 text-[11px]">RPM(F5)</code>{' '}
                      (Agency prerequisite chain), or{' '}
                      <code className="text-accent-teal/80 text-[11px]">{'Φ⟨1:4:7⟩'}</code> (Cognitive
                      Fractal sequence). The system validates your notation, translates it to plain
                      English, and generates a targeted assessment prompt.
                    </p>
                    <Link
                      to="/"
                      className="inline-flex items-center gap-1.5 text-[11px] font-medium text-purple-400 hover:text-purple-300 transition-colors"
                    >
                      Try It — Go to Assessment and click the "Compose" tab
                      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M2.5 6h7M7 3.5L9.5 6 7 8.5" />
                      </svg>
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </SectionReveal>
      </div>
    </div>
  );
}

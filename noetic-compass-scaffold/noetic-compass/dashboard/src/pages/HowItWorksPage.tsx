import { useMemo } from 'react';
import { useScrollSpy } from '../hooks/useScrollSpy';
import { SectionReveal } from '../components/shared/SectionReveal';
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
  { id: 'operators', label: 'Cognitive Operators' },
  { id: 'domains', label: 'Processing Domains' },
  { id: 'drives', label: 'Core Drives' },
  { id: 'rpm', label: 'RPM Model' },
  { id: 'inversions', label: 'Inversion Detection' },
  { id: 'nccs', label: 'NCCS Scoring' },
  { id: 'math', label: 'The Math' },
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
    <div className="flex gap-8">
      {/* Sticky scroll-spy nav — desktop only */}
      <nav className="hidden lg:block sticky top-6 self-start w-44 shrink-0">
        <ul className="flex flex-col gap-0.5">
          {SECTIONS.map((s) => (
            <li key={s.id}>
              <a
                href={`#${s.id}`}
                className={`block rounded-md px-3 py-1.5 text-xs font-medium transition-all duration-150 ${
                  activeId === s.id
                    ? 'bg-accent-teal/10 text-accent-teal scroll-spy-active'
                    : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                {s.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      {/* Content */}
      <div className="flex-1 max-w-3xl space-y-16 pb-24">
        {/* 1 — Big Picture */}
        <SectionReveal>
          <section id="big-picture" className="scroll-mt-8">
            <h2 className="text-2xl font-bold text-slate-100 mb-2">The Big Picture</h2>
            <p className="text-slate-400 mb-6 leading-relaxed">
              The Cognitive Architecture System (CAS) evaluates AI responses for psychological alignment
              and ethical integrity. Every prompt passes through an 8-stage pipeline, producing a
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

        {/* 2 — Cognitive Operators */}
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
              The Realization-Prerequisite Model uses a <strong className="text-slate-200">section-retraction</strong>,
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
                      {node === 'A0' ? 'A0 (Pure Desire)' : node === 'D' ? 'Dn (Desire)' : node === 'W' ? 'Wn (Will)' : node === 'P' ? 'Pn (Power)' : node}
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
            <div className="space-y-4">
              <div className="glass-card p-4">
                <h4 className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
                  State Space
                </h4>
                <code className="block text-sm text-accent-teal font-mono leading-relaxed">
                  {'S°_I = Δ°₃₉ = { p ∈ ℝ⁴⁰ : pₖ > 0 ∀k, Σpₖ = 1 }'}
                </code>
              </div>
              <div className="glass-card p-4">
                <h4 className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
                  Fisher-Rao Metric
                </h4>
                <code className="block text-sm text-accent-teal font-mono leading-relaxed">
                  {'g^FR_p(u, v) = Σₖ (uₖ · vₖ) / pₖ'}
                </code>
              </div>
              <div className="glass-card p-4">
                <h4 className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
                  Geodesic Distance
                </h4>
                <code className="block text-sm text-accent-teal font-mono leading-relaxed">
                  {'d(p, q) = 2 · arccos( Σₖ √(pₖ · qₖ) )'}
                </code>
              </div>
              <div className="glass-card p-4">
                <h4 className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
                  Admissibility Relation
                </h4>
                <code className="block text-sm text-accent-teal font-mono leading-relaxed">
                  {'Dₖ ⊆ I × I — valid (source, target) pairs for operator CO-k'}
                </code>
                <code className="block text-sm text-slate-500 font-mono mt-1">
                  {'D₀ = { (I, I) : I ∈ I } — identity on diagonal only'}
                </code>
              </div>
            </div>
          </section>
        </SectionReveal>
      </div>
    </div>
  );
}

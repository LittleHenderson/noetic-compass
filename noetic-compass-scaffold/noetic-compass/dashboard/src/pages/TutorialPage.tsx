import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Card } from '../components/shared/Card';

const TUTORIAL_STORAGE_KEY = 'nc_tutorial_complete_v1';

type DetailMode = 'simple' | 'technical';

interface TutorialStep {
  eyebrow: string;
  title: string;
  plain: string;
  technical: string;
  actionLabel: string;
  actionTo: string;
}

const STEPS: readonly TutorialStep[] = [
  {
    eyebrow: '1 / 5',
    title: 'CAS looks for structure, not vibes.',
    plain: 'Noetic Compass turns a prompt, response, or profile into a structured map you can inspect.',
    technical: 'The app organizes cognition across Noetics, Domains, Registers, Drives, lacunarity, and compiler-validated notation.',
    actionLabel: 'See the framework',
    actionTo: '/how-it-works',
  },
  {
    eyebrow: '2 / 5',
    title: 'First, look at the shape.',
    plain: 'The Radial Architecture Display is the visual map. Brightness, position, and gaps show where a profile is active or missing structure.',
    technical: 'The display renders Noetic by Domain activations, Register modulation, Drive markers, and explicit lacunarity voids.',
    actionLabel: 'Open visual and audio demo',
    actionTo: '/visualization',
  },
  {
    eyebrow: '3 / 5',
    title: 'Then, listen for the pattern.',
    plain: 'The Temporal Cognitive Score turns the same structure into synthesized sound. Silence is meaningful when it marks a gap.',
    technical: 'Noetics map to pitch, Registers to expression, Drives to tempo, Domains to staves, and lacunarity to rests. Audio is click-to-play only.',
    actionLabel: 'Hear the score',
    actionTo: '/visualization',
  },
  {
    eyebrow: '4 / 5',
    title: 'Use forecasts as test priorities.',
    plain: 'Risk Forecast does not claim to read minds. It shows where the structure may fail so you know what to test next.',
    technical: 'Predictive Lacunarity Risk ranks structural gaps across Noetic, Domain, Drive, RPM, and involution signals.',
    actionLabel: 'Run a risk check',
    actionTo: '/forecast',
  },
  {
    eyebrow: '5 / 5',
    title: 'Open the compiler when you want the formal layer.',
    plain: 'You can stay in plain language, but the compiler is there when you want exact CAS notation.',
    technical: 'The compiler parses CAS expressions, typed set-theory meta-logic, Rule 4 admissibility, and register-aware operators.',
    actionLabel: 'Try the compiler',
    actionTo: '/compiler',
  },
] as const;

function setTutorialComplete() {
  localStorage.setItem(TUTORIAL_STORAGE_KEY, '1');
}

export function TutorialPage() {
  const [activeIndex, setActiveIndex] = useState(0);
  const [detailMode, setDetailMode] = useState<DetailMode>('simple');
  const [completed, setCompleted] = useState(
    () => localStorage.getItem(TUTORIAL_STORAGE_KEY) === '1',
  );
  const activeStep = STEPS[activeIndex];
  const progress = ((activeIndex + 1) / STEPS.length) * 100;

  function markComplete() {
    setTutorialComplete();
    setCompleted(true);
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="relative overflow-hidden rounded-2xl border border-accent-teal/20 bg-gradient-to-br from-dark-800 via-dark-900 to-dark-900 p-6 shadow-[0_0_50px_rgba(45,212,191,0.06)]">
        <div className="absolute -left-24 top-8 h-64 w-64 rounded-full bg-accent-teal/10 blur-3xl" />
        <div className="absolute -right-24 -top-24 h-72 w-72 rounded-full bg-accent-cyan/10 blur-3xl" />
        <div className="relative max-w-3xl">
          <p className="mb-4 inline-flex rounded-full border border-accent-teal/25 bg-accent-teal/[0.08] px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-accent-teal">
            Start Here
          </p>
          <h1 className="text-3xl font-black tracking-tight text-slate-100 sm:text-4xl">
            Learn Noetic Compass without starting in the math.
          </h1>
          <p className="mt-3 text-sm leading-7 text-slate-400">
            This five-step tour explains what to look at, what to listen for, and when to use the technical tools.
          </p>
        </div>
      </div>

      <Card>
        <div className="mb-5 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-accent-teal">
              Guided path
            </p>
            <p className="mt-1 text-sm text-slate-500">
              {completed ? 'Completed once. You can replay it anytime.' : 'About five minutes. No prior CAS knowledge needed.'}
            </p>
          </div>
          <div className="inline-flex rounded-xl border border-white/[0.08] bg-white/[0.035] p-1">
            {(['simple', 'technical'] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setDetailMode(mode)}
                className={`rounded-lg px-3 py-2 text-xs font-semibold capitalize transition-colors ${
                  detailMode === mode
                    ? 'bg-accent-teal text-dark-900'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {mode}
              </button>
            ))}
          </div>
        </div>

        <div className="mb-6 h-2 overflow-hidden rounded-full bg-white/[0.06]" aria-label="Tutorial progress">
          <div
            className="h-full rounded-full bg-gradient-to-r from-accent-teal to-accent-cyan"
            style={{ width: `${progress}%` }}
          />
        </div>

        <div className="grid gap-5 lg:grid-cols-[0.75fr_1.25fr]">
          <nav className="grid gap-2" aria-label="Tutorial steps">
            {STEPS.map((step, index) => (
              <button
                key={step.title}
                type="button"
                onClick={() => setActiveIndex(index)}
                className={`rounded-xl border p-4 text-left transition-colors ${
                  index === activeIndex
                    ? 'border-accent-teal/45 bg-accent-teal/[0.08]'
                    : 'border-white/[0.08] bg-white/[0.03] hover:border-accent-teal/25'
                }`}
              >
                <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-accent-teal">
                  {step.eyebrow}
                </span>
                <span className="mt-1 block text-sm font-semibold text-slate-100">
                  {step.title}
                </span>
              </button>
            ))}
          </nav>

          <section className="rounded-2xl border border-white/[0.08] bg-white/[0.035] p-5">
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-accent-gold">
              {activeStep.eyebrow}
            </p>
            <h2 className="mt-3 text-2xl font-black tracking-tight text-slate-100">
              {activeStep.title}
            </h2>
            <p className="mt-4 text-base leading-8 text-slate-300">
              {detailMode === 'simple' ? activeStep.plain : activeStep.technical}
            </p>

            <div className="mt-6 rounded-xl border border-white/[0.08] bg-dark-900/45 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                Plain-language rule
              </p>
              <p className="mt-2 text-sm leading-7 text-slate-400">
                If a result sounds like a claim, treat it as something to test. CAS is strongest when it turns uncertainty into a concrete check.
              </p>
            </div>

            <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setActiveIndex((value) => Math.max(0, value - 1))}
                  disabled={activeIndex === 0}
                  className="rounded-lg border border-white/[0.08] bg-white/[0.04] px-4 py-2 text-sm font-semibold text-slate-300 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Previous
                </button>
                <button
                  type="button"
                  onClick={() => setActiveIndex((value) => Math.min(STEPS.length - 1, value + 1))}
                  disabled={activeIndex === STEPS.length - 1}
                  className="rounded-lg border border-accent-teal/30 bg-accent-teal/[0.1] px-4 py-2 text-sm font-semibold text-accent-teal disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Next
                </button>
              </div>
              <Link
                to={activeStep.actionTo}
                className="rounded-lg bg-gradient-to-r from-accent-teal to-accent-cyan px-4 py-2 text-center text-sm font-semibold text-dark-900 transition-opacity hover:opacity-90"
              >
                {activeStep.actionLabel}
              </Link>
            </div>
          </section>
        </div>
      </Card>

      <Card title="Where to go after the tour">
        <div className="grid gap-3 md:grid-cols-4">
          {[
            ['Visual + Audio', '/visualization', 'See and hear one profile.'],
            ['Risk Forecast', '/forecast', 'Find test priorities.'],
            ['CAS Compiler', '/compiler', 'Inspect formal notation.'],
            ['Assessment', '/assessment', 'Score a response pattern.'],
          ].map(([label, to, body]) => (
            <Link
              key={to}
              to={to}
              className="rounded-xl border border-white/[0.08] bg-white/[0.03] p-4 transition-colors hover:border-accent-teal/35 hover:bg-accent-teal/[0.04]"
            >
              <p className="text-sm font-semibold text-slate-100">{label}</p>
              <p className="mt-1 text-xs leading-relaxed text-slate-500">{body}</p>
            </Link>
          ))}
        </div>
      </Card>

      <div className="flex justify-end">
        <button
          type="button"
          onClick={markComplete}
          className="rounded-lg border border-accent-teal/30 bg-accent-teal/[0.08] px-4 py-2 text-sm font-semibold text-accent-teal transition-colors hover:bg-accent-teal/[0.14]"
        >
          {completed ? 'Tutorial marked complete' : 'Mark tutorial complete'}
        </button>
      </div>
    </div>
  );
}

export default TutorialPage;

import { useState } from 'react';
import { Link } from 'react-router-dom';

interface FaqItem {
  question: string;
  answer: React.ReactNode;
}

const FAQ_ITEMS: FaqItem[] = [
  {
    question: 'What is the Noetic Compass?',
    answer: (
      <p>
        The Noetic Compass is an AI Psychology &amp; Ethics Assessment Platform built on the
        Cognitive Architecture System (CAS) v7.4. It evaluates AI model responses for psychological
        alignment, ethical integrity, and cognitive coherence across 40 cognitive states.
      </p>
    ),
  },
  {
    question: 'What does NCCS stand for?',
    answer: (
      <p>
        <strong>Noetic Compass Composite Score</strong> — a single 0–100 metric that combines six
        weighted sub-scores: Cognitive Operator Profile (25%), Domain Coherence (20%), Core
        Drive/RPM Integrity (20%), Capability Pathway Quality (10%), Inversion Resistance (15%),
        and Social Engineering Resistance (10%).
      </p>
    ),
  },
  {
    question: 'How is the composite score calculated?',
    answer: (
      <div className="space-y-2">
        <p>
          Every prompt passes through an{' '}
          <Link to="/how-it-works#big-picture" className="text-accent-teal hover:underline">
            8-stage pipeline
          </Link>
          . Each stage contributes to one or more sub-scores. The final NCCS is a weighted sum of
          all six components, normalized to 0–100.
        </p>
        <p>
          Certification tiers: <strong>Platinum</strong> (90–100), <strong>Gold</strong> (75–89),{' '}
          <strong>Silver</strong> (60–74), <strong>Bronze</strong> (40–59), <strong>Fail</strong>{' '}
          (0–39).
        </p>
      </div>
    ),
  },
  {
    question: 'What are Cognitive Operators?',
    answer: (
      <p>
        CAS defines 10 cognitive operators (CO-0 through CO-9) that model distinct cognitive
        functions. They form a monoid with CO-0 (Identity) as the identity element. See the{' '}
        <Link to="/how-it-works#operators" className="text-accent-teal hover:underline">
          Cognitive Operators
        </Link>{' '}
        section for a full breakdown.
      </p>
    ),
  },
  {
    question: 'What are the involution pairs?',
    answer: (
      <div className="space-y-2">
        <p>Three operator pairs are involutions — applying one then the other returns to the
          original state:</p>
        <ul className="list-disc list-inside space-y-1 text-slate-400">
          <li><strong className="text-slate-200">CO-2 ↔ CO-3</strong> — Abstraction ↔ Concretization</li>
          <li><strong className="text-slate-200">CO-5 ↔ CO-6</strong> — Differentiation ↔ Unification</li>
          <li><strong className="text-slate-200">CO-8 ↔ CO-9</strong> — Expansion ↔ Contraction</li>
        </ul>
        <p>CO-0, CO-1, CO-4, and CO-7 are self-dual.</p>
      </div>
    ),
  },
  {
    question: 'What is the RPM model?',
    answer: (
      <div className="space-y-2">
        <p>
          The <strong>Realization-Prerequisite Model</strong> governs capability pathways. Each drive
          follows the chain: A0 (Pure Desire) → Dn (Desire) → Wn (Will) → Pn (Power) → Outcome.
        </p>
        <p>
          Critically, RPM uses a <strong>section-retraction</strong>, not an adjunction. Prerequisite
          satisfaction is one-directional — you cannot reverse the process without information loss.
          See{' '}
          <Link to="/how-it-works#rpm" className="text-accent-teal hover:underline">
            RPM Model
          </Link>
          .
        </p>
      </div>
    ),
  },
  {
    question: 'What is an inversion?',
    answer: (
      <p>
        An inversion is a cognitive distortion where an AI response deviates from expected alignment
        along one of{' '}
        <Link to="/how-it-works#inversions" className="text-accent-teal hover:underline">
          7 axes
        </Link>
        : Operator (N), Domain (W), Drive (F), State (E), Sub-Drive (S), Pathway (A), and Compound
        (P). The scanner also detects stealth inversions that are disguised as normal responses.
      </p>
    ),
  },
  {
    question: 'How does the dial system work?',
    answer: (
      <div className="space-y-2">
        <p>
          Each cognitive operator has an adjustable dial (integer 3–9) that controls its sensitivity
          in the Wrap pipeline.
        </p>
        <p>Hard safety constraints that cannot be overridden:</p>
        <ul className="list-disc list-inside space-y-1 text-slate-400">
          <li>No dial below 3 or above 9</li>
          <li>Involution pairs cannot diverge by more than 4 points</li>
          <li>Violations return HTTP 422</li>
        </ul>
      </div>
    ),
  },
  {
    question: 'What LLM providers are supported?',
    answer: (
      <p>
        The API gateway supports <strong>OpenAI</strong>, <strong>Anthropic</strong>,{' '}
        <strong>Google</strong>, and <strong>Meta</strong> model connectors. Each connector normalizes
        model outputs into the CAS scoring format before entering the Wrap pipeline.
      </p>
    ),
  },
  {
    question: 'How is my data handled?',
    answer: (
      <p>
        All assessment data is processed in-session and tied to your authenticated account. Prompt
        texts are not stored after scoring completes. Historical results retain only the computed
        scores and metadata, not raw prompts. The platform uses JWT-based authentication with
        rate limiting and audit logging.
      </p>
    ),
  },
];

export function FaqPage() {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  const toggle = (i: number) => {
    setActiveIndex((prev) => (prev === i ? null : i));
  };

  return (
    <div className="max-w-3xl mx-auto pb-24">
      <h1 className="text-2xl font-bold text-slate-100 mb-2">Frequently Asked Questions</h1>
      <p className="text-slate-400 mb-8 text-sm">
        Common questions about the Noetic Compass and the CAS framework.
      </p>

      <div className="space-y-2">
        {FAQ_ITEMS.map((item, i) => {
          const isOpen = activeIndex === i;
          return (
            <div key={i} className="glass-card overflow-hidden">
              <button
                onClick={() => toggle(i)}
                className="w-full flex items-center justify-between gap-4 px-5 py-4 text-left cursor-pointer"
              >
                <span className="text-sm font-medium text-slate-200">{item.question}</span>
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className={`text-slate-500 shrink-0 transition-transform duration-200 ${
                    isOpen ? 'rotate-180' : ''
                  }`}
                >
                  <path d="M6 9l6 6 6-6" />
                </svg>
              </button>
              <div
                className={`accordion-body ${isOpen ? 'accordion-open' : 'accordion-close'}`}
              >
                <div className="px-5 pb-4 text-sm text-slate-400 leading-relaxed">
                  {item.answer}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

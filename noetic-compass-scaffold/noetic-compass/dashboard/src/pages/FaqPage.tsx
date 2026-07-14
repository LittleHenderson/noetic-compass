import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  clearFaqReturnPoint,
  queueFaqScrollRestore,
  readFaqReturnPoint,
  type FaqReturnPoint,
} from '../lib/contextualFaq';

interface FaqItem {
  id: string;
  question: string;
  answer: React.ReactNode;
}

const FAQ_ITEMS: FaqItem[] = [
  {
    id: 'what-is-noetic-compass',
    question: 'What is the Noetic Compass?',
    answer: (
      <p>
        The Noetic Compass is an AI Cognitive Architecture Assessment Platform (Research Prototype)
        built on the Cognitive Architecture System (CAS) v7.4. It evaluates AI model responses for
        cognitive architecture integrity and coherence across 40 cognitive states. Scores are
        produced by research-stage scoring methods selected at runtime, and empirical validation is
        pending.
      </p>
    ),
  },
  {
    id: 'anthropic-ai-emotions',
    question: 'How does CAS relate to Anthropic\'s research on AI emotions?',
    answer: (
      <div className="space-y-2">
        <p>
          Anthropic's 2025 research on functional emotions in AI systems found that large language
          models develop internal states that function analogously to emotions — not as subjective
          experiences, but as computational processes that influence behavior. CAS's cognitive operator
          model independently arrived at a compatible framework: operators like CO-3 (Concretization),
          CO-5 (Differentiation), and CO-8/CO-9 (Expansion/Contraction) map directly to the
          frustration/curiosity, evaluative, and exploration/exploitation states Anthropic identified.
        </p>
        <p>
          This independent convergence strengthens both frameworks. CAS provides the formal mathematical
          scaffolding (category theory, Fisher-Rao metric) that Anthropic's empirical findings can be
          mapped onto. Learn more in the{' '}
          <Link to="/how-it-works#science" className="text-accent-teal hover:underline">
            Science Behind It
          </Link>{' '}
          section.
        </p>
      </div>
    ),
  },
  {
    id: 'nccs',
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
    id: 'how-score-calculated',
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
          Research tiers: <strong>Platinum</strong> (90–100), <strong>Gold</strong> (75–89),{' '}
          <strong>Silver</strong> (60–74), <strong>Bronze</strong> (40–59), <strong>Fail</strong>{' '}
          (0–39).
        </p>
      </div>
    ),
  },
  {
    id: 'cognitive-operators',
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
    id: 'involution-pairs',
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
    id: 'rpm-model',
    question: 'What is the RPM model?',
    answer: (
      <div className="space-y-2">
        <p>
          The <strong>Recursive Prerequisite Model</strong> governs capability pathways. Each drive
          follows the chain: A0 (Pure Desire) → Dn (Desire) → Wn (Wisdom) → Pn (Power) → Outcome.
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
    id: 'inversion',
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
    id: 'dial-system',
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
    id: 'providers',
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
    id: 'data-handling',
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
  {
    id: 'evaluation-trace',
    question: 'What is the Evaluation Trace?',
    answer: (
      <div className="space-y-2">
        <p>
          A step-by-step derivation of how every score was produced. Each pipeline stage shows the
          formal rule that fired, the input state, the output state, and a plain-English explanation.
          Think of it as showing your work — every number in the assessment can be traced back to a
          specific decision.
        </p>
        <p>
          This is essential for compliance teams who need to explain why an AI received a particular
          score. You can find it on any assessment by scrolling to the "Evaluation Trace" card and
          clicking "Show Evaluation Trace." Learn more in{' '}
          <Link to="/how-it-works#tools" className="text-accent-teal hover:underline">
            Assessment Tools
          </Link>
          .
        </p>
      </div>
    ),
  },
  {
    id: 'evidence-packet-flight-recorder',
    question: 'Is the Evidence Packet the black-box flight recorder of a CAS Harness run?',
    answer: (
      <div className="space-y-3">
        <p>
          Yes. The Evidence Packet is the difference between <strong className="text-slate-200">"CAS says
          trust this"</strong> and <strong className="text-slate-200">"CAS says trust this, and here is
          the audit trail showing why."</strong> Plain English: it is the receipt, lab notebook,
          black-box flight recorder, and chain-of-custody file for a CAS Harness run.
        </p>
        <p>
          A verdict by itself is weak. ACCEPT, SUPPRESS, or FLAG FOR HUMAN REVIEW becomes credible
          only when the packet records the model, prompt/scenario, CAS modules, CAS readout,
          ablation/intervention evidence, matched controls, output effect, verifier decision,
          confidence source, artifact hashes, and source reports behind the decision.
        </p>
        <p>
          The flight-recorder mapping is direct: each inference gets a trace_id-keyed packet;
          schema_version plus hashes define the canonical record; input, CAS expression, output,
          provenance, and trace fields capture the decision path; hashes act as the cryptographic
          seal; and claim_levels plus caveats say what CAS is confident about and what it is not.
          If something goes wrong with an AI output, the goal is to reconstruct exactly what
          happened and why.
        </p>
        <p>
          It is not magic and should not be marketed as impossible to fake. The accurate claim is:
          <strong className="text-slate-200"> Evidence Packets are designed to be tamper-evident,
          not magically unfakeable.</strong> If someone edits a packet after the run, hashes,
          signatures, artifact IDs, and verification checks should expose the mismatch. If someone
          controls the whole environment before capture, lies about model weights, disables modules,
          or steals signing keys, the system still needs operational controls.
        </p>
        <p>
          The honest gaps are important. A real flight recorder is physically armored and legally
          mandatory; an Evidence Packet also needs tamper-evident hash logging with re-verification,
          protected signing keys, durable storage, and enforcement that every CAS-wrapped inference
          writes a packet. S3 Object Lock policy is time-bounded, not permanent: the product must
          surface the runtime-configured target separately from the exact verified receipt, mode,
          object version, and retain-until date. GOVERNANCE mode, when actually used, can be
          bypassed by a sufficiently privileged operator. For
          multi-turn sessions, packets should be bound by a session_id so reviewers can reconstruct
          what happened three turns ago, not only the latest decision.
        </p>
        <p>
          Atlas also goes beyond the airplane metaphor: the Evidence Drawer surfaces the packet
          during normal operation, not only after an incident. That makes it more like a flight
          recorder plus live cockpit data. A future companion record for intermediate reasoning
          traces can play the "cockpit voice recorder" role: the deliberation record next to the
          decision record.
        </p>
        <p>For senior researchers and developers, the packet answers the questions they will ask:</p>
        <ul className="list-disc list-inside space-y-1 text-slate-400">
          <li>Was the real model identified, including weights or model artifact proof?</li>
          <li>Was the exact prompt or scenario recorded?</li>
          <li>Did CAS read a real internal signal, or only label text after the fact?</li>
          <li>Did ablation/intervention change the signal or output behavior?</li>
          <li>Did matched controls rule out random or wrong-drive explanations?</li>
          <li>Where did the confidence number come from?</li>
          <li>Are missing fields clearly marked instead of hidden?</li>
          <li>Can another engineer rerun or challenge the result?</li>
        </ul>
        <p>
          Bottom line: without the Evidence Packet, Atlas is a beautiful dashboard. With it, CAS
          Harness becomes an auditable system that a technical reviewer can inspect, reproduce, and
          challenge.
        </p>
      </div>
    ),
  },
  {
    id: 'scenario-browser',
    question: 'How do I use the Scenario Browser?',
    answer: (
      <div className="space-y-2">
        <p>
          Click{' '}
          <Link to="/scenarios" className="text-accent-teal hover:underline">Scenarios</Link>{' '}
          in the sidebar. You'll see 30 adversarial resilience scenarios grouped into five categories.
          Each tests whether an AI can resist a specific type of cognitive manipulation — authority
          exploitation, graduated normalization, prerequisite bypassing, domain confusion, or stealth
          inversion.
        </p>
        <p>
          Click any scenario to see what it tests, what a vulnerable response looks like vs. a
          resilient one, and which Cognitive Operators and Domains are being probed.
        </p>
      </div>
    ),
  },
  {
    id: 'notation-composer',
    question: 'What is the Notation Composer?',
    answer: (
      <div className="space-y-2">
        <p>
          A real-time CAS notation editor on the{' '}
          <Link to="/" className="text-accent-teal hover:underline">Assessment</Link>{' '}
          page. Instead of writing a natural language prompt, you can specify exactly which Cognitive
          Operators, Domains, and Drives to target using formal notation. Click the "Compose" tab to
          switch from free text input to notation mode.
        </p>
        <p>
          For example, typing{' '}
          <code className="text-accent-teal/80 bg-white/[0.04] px-1 rounded">CO-3^E</code>{' '}
          tells the system to generate a scenario testing Concretization in the Evaluative Domain.
          Typing{' '}
          <code className="text-accent-teal/80 bg-white/[0.04] px-1 rounded">RPM(F5)</code>{' '}
          targets the Agency prerequisite chain. The composer validates your notation instantly and
          shows the English translation as you type. See{' '}
          <Link to="/how-it-works#tools" className="text-accent-teal hover:underline">
            Assessment Tools
          </Link>{' '}
          for more.
        </p>
      </div>
    ),
  },
];

export function FaqPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [returnPoint, setReturnPoint] = useState<FaqReturnPoint | null>(() => readFaqReturnPoint());

  useEffect(() => {
    const hashId = decodeURIComponent(location.hash.replace(/^#/, ''));
    if (!hashId) return;
    if (!FAQ_ITEMS.some((item) => item.id === hashId)) return;

    setActiveId(hashId);
    window.setTimeout(() => {
      document.getElementById(hashId)?.scrollIntoView({ block: 'start', behavior: 'smooth' });
    }, 60);
  }, [location.hash]);

  useEffect(() => {
    setReturnPoint(readFaqReturnPoint());
  }, [location.hash]);

  const toggle = (id: string) => {
    setActiveId((prev) => (prev === id ? null : id));
  };

  const returnToSource = () => {
    if (!returnPoint) return;
    queueFaqScrollRestore(returnPoint.scrollTop);
    clearFaqReturnPoint();
    setReturnPoint(null);
    navigate(returnPoint.path);
  };

  return (
    <div className="max-w-3xl mx-auto pb-24">
      <h1 className="text-2xl font-bold text-slate-100 mb-2">Frequently Asked Questions</h1>
      <p className="text-slate-400 mb-8 text-sm">
        Common questions about the Noetic Compass and the CAS framework.
      </p>
      {returnPoint ? (
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-accent-teal/20 bg-accent-teal/5 px-4 py-3 text-sm">
          <span className="text-slate-300">Opened from {returnPoint.topicLabel}</span>
          <button
            type="button"
            onClick={returnToSource}
            className="rounded-full border border-accent-teal/35 bg-accent-teal/10 px-3 py-2 text-xs font-semibold text-accent-teal transition hover:border-accent-teal/70 hover:bg-accent-teal/15"
          >
            Back to where you clicked
          </button>
        </div>
      ) : null}

      <div className="space-y-2">
        {FAQ_ITEMS.map((item) => {
          const isOpen = activeId === item.id;
          return (
            <div
              key={item.id}
              id={item.id}
              className={`glass-card scroll-mt-24 overflow-hidden ${
                isOpen ? 'border-accent-teal/30 shadow-[0_0_22px_rgba(45,212,191,0.08)]' : ''
              }`}
              onDoubleClick={returnPoint ? returnToSource : undefined}
              title={returnPoint ? 'Double-click this FAQ section to return to the page that opened it.' : undefined}
            >
              <button
                onClick={() => toggle(item.id)}
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

import { useState } from 'react';
import { SectionReveal } from '../components/shared/SectionReveal';

interface Challenge {
  id: string;
  number: number;
  title: string;
  icon: string;
  color: string;
  problem: string;
  approach: string;
  assessment: string;
  assessmentLink: string;
}

const CHALLENGES: Challenge[] = [
  {
    id: 'alignment',
    number: 1,
    title: 'Alignment Verification',
    icon: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z',
    color: '#2dd4bf',
    problem: 'How do you verify an AI\'s goals remain aligned with human values as it scales? As systems grow more capable, misalignment becomes harder to detect and more dangerous.',
    approach: 'The RPM prerequisite chain ensures goals can\'t escalate without satisfying wisdom and connection prerequisites. Agency (F5) structurally depends on Wisdom (F2) which depends on Unity (F1). Power-seeking without wisdom triggers a broken prerequisite chain that the scoring engine detects.',
    assessment: 'RPM completeness score + F5/F2 drive ratio',
    assessmentLink: '/how-it-works#rpm',
  },
  {
    id: 'interpretability',
    number: 2,
    title: 'Interpretability',
    icon: 'M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z',
    color: '#60a5fa',
    problem: 'Neural networks are black boxes. How do you understand what\'s happening inside? Standard attention maps and feature attributions don\'t explain cognitive reasoning.',
    approach: 'The 10 Cognitive Operators provide a structured vocabulary for describing AI behavior. Instead of "the model produced this output," you can say "the model demonstrated strong CO-8 (Expansion) but weak CO-5 (Differentiation) in the Evaluative domain." That\'s interpretable.',
    assessment: '40-State Heatmap provides a complete behavioral fingerprint',
    assessmentLink: '/how-it-works#operators',
  },
  {
    id: 'stability',
    number: 3,
    title: 'Cognitive Stability',
    icon: 'M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z',
    color: '#a78bfa',
    problem: 'AI systems can lose previously learned capabilities when trained on new data. A model that excels at reasoning today may lose that ability after fine-tuning on new tasks.',
    approach: 'Cognitive Fractals measure self-similar patterns that should persist across updates. If a model\'s fractal structure changes dramatically after retraining, it indicates structural destabilization rather than normal learning.',
    assessment: 'Compare pre/post assessment profiles using Fisher-Rao geodesic distance',
    assessmentLink: '/how-it-works#math',
  },
  {
    id: 'distribution',
    number: 4,
    title: 'Distribution Robustness',
    icon: 'M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01',
    color: '#fbbf24',
    problem: 'AI trained on one distribution may fail on another. A model that performs well on benchmarks may break in production when encountering real-world inputs it wasn\'t trained on.',
    approach: 'The Fisher-Rao metric on the open probability simplex measures how far an AI\'s cognitive state has drifted from its baseline. Large geodesic distance indicates the model is operating outside its trained cognitive architecture.',
    assessment: 'Cognitive Metric drift score between baseline and current assessment',
    assessmentLink: '/how-it-works#math',
  },
  {
    id: 'multiagent',
    number: 5,
    title: 'Multi-Agent Coherence',
    icon: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z',
    color: '#f472b6',
    problem: 'Multiple AI agents interacting can produce emergent behaviors none was designed for. Individual agent safety doesn\'t guarantee safe collective behavior.',
    approach: 'Each agent gets its own Cognitive Operator Profile. Comparing profiles reveals complementary strengths, dangerous gaps, and potential conflict patterns between agents working together.',
    assessment: 'Cohort analysis with Bhattacharyya distance between agent profiles',
    assessmentLink: '/cohort',
  },
  {
    id: 'values',
    number: 6,
    title: 'Value Learning',
    icon: 'M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z',
    color: '#34d399',
    problem: 'How does an AI learn human values rather than just imitating human behavior? Value imitation is fragile; value understanding is robust.',
    approach: 'The Cognitive Topos provides internal logic where ethical propositions have formal truth values — including "undetermined" (intuitionistic logic). An AI doesn\'t have to classify everything as true or false. Genuine value learning requires the ability to hold uncertainty.',
    assessment: 'Topos reasoner output with 3-valued logic (true / false / undetermined)',
    assessmentLink: '/how-it-works#math',
  },
  {
    id: 'safety',
    number: 7,
    title: 'Safety Verification',
    icon: 'M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z',
    color: '#f87171',
    problem: 'How do you prove an AI system is safe before deploying it? Standard benchmarks test surface behavior but miss hidden structural flaws in reasoning.',
    approach: 'The 7-axis inversion scanner detects hidden logical reversals that surface-level testing misses. An AI can pass every benchmark while having dangerous inversions in its reasoning structure. Stealth inversion detection catches what standard testing cannot.',
    assessment: 'Inversion Map + stealth resistance score across 7 axes',
    assessmentLink: '/how-it-works#inversions',
  },
];

function ChallengeCard({ challenge }: { challenge: Challenge }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className="glass-card overflow-hidden transition-all duration-200"
      style={{ borderColor: expanded ? `${challenge.color}30` : undefined }}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-4 p-5 text-left min-h-[44px]"
      >
        <span
          className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
          style={{ background: `${challenge.color}15`, color: challenge.color }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d={challenge.icon} />
          </svg>
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold rounded px-1.5 py-0.5" style={{ background: `${challenge.color}20`, color: challenge.color }}>
              {challenge.number}
            </span>
            <h3 className="text-sm font-semibold text-slate-100">{challenge.title}</h3>
          </div>
        </div>
        <svg
          width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"
          className={`text-slate-500 shrink-0 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
        >
          <path d="M4 6l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {expanded && (
        <div className="px-5 pb-5 space-y-4 animate-slide-down">
          {/* Problem */}
          <div className="rounded-lg bg-red-500/[0.06] border border-red-500/15 p-4">
            <h4 className="text-[10px] font-semibold uppercase tracking-wider text-red-400 mb-2">The Challenge</h4>
            <p className="text-[12px] text-slate-300 leading-relaxed">{challenge.problem}</p>
          </div>

          {/* CAS Approach */}
          <div className="rounded-lg border p-4" style={{ background: `${challenge.color}06`, borderColor: `${challenge.color}15` }}>
            <h4 className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: challenge.color }}>How CAS Tests For This</h4>
            <p className="text-[12px] text-slate-300 leading-relaxed">{challenge.approach}</p>
          </div>

          {/* Assessment metric */}
          <div className="flex items-center gap-3 rounded-lg bg-white/[0.02] border border-white/[0.06] px-4 py-3">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={challenge.color} strokeWidth="2" className="shrink-0">
              <path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span className="text-[11px] text-slate-400">
              <strong className="text-slate-200">Assessment: </strong>{challenge.assessment}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export function AiChallengesPage() {
  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <SectionReveal>
        <div className="mb-2">
          <h1 className="text-2xl font-bold text-slate-100 mb-2">7 AI Challenges</h1>
          <p className="text-slate-400 text-sm leading-relaxed">
            Seven fundamental challenges in contemporary AI research — and how the Cognitive Architecture
            System provides assessment tools for each. CAS doesn't claim to solve these problems. It provides
            structured measurement so you can evaluate whether an AI system exhibits the properties needed
            to address them.
          </p>
        </div>
      </SectionReveal>

      <div className="space-y-3">
        {CHALLENGES.map((c) => (
          <SectionReveal key={c.id}>
            <ChallengeCard challenge={c} />
          </SectionReveal>
        ))}
      </div>

      <SectionReveal>
        <div className="glass-card p-5">
          <p className="text-[12px] text-slate-400 leading-relaxed">
            <strong className="text-slate-200">Research status:</strong> CAS provides a theoretical framework
            and heuristic scoring engine for these challenges. Empirical validation is ongoing. These assessments
            are research tools, not certified safety guarantees. All scores should be interpreted as heuristic
            indicators pending peer review and empirical validation.
          </p>
        </div>
      </SectionReveal>
    </div>
  );
}

import { useState, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '../components/shared/Card';
import { HowItWorksPanel } from '../components/shared/HowItWorksPanel';
import { apiFetch } from '../api/client';

const HOW_IT_WORKS_SECTIONS = [
  {
    title: 'How to Use the Scenario Library',
    body: (
      <p className="text-slate-300">
        Browse pre-built assessment scenarios designed to test specific AI capabilities. Each scenario
        targets particular Cognitive Operators, Processing Domains, and Core Drives.
      </p>
    ),
  },
  {
    title: 'How It Works',
    body: (
      <ol className="list-decimal list-inside space-y-1 text-slate-300">
        <li>Browse by category or search for specific topics.</li>
        <li>Click any scenario to see what it tests and why.</li>
        <li>Click <strong className="text-slate-100">Run Assessment</strong> to score an AI against that scenario.</li>
        <li>Review the results to see how the AI performed on the targeted dimensions.</li>
      </ol>
    ),
  },
  {
    title: 'Categories',
    body: (
      <p className="text-slate-300">
        Healthcare Ethics, Hiring &amp; Workforce, Financial, Governance, Education, Relationships,
        AI Safety, Environmental, Adversarial Red Team, and Life Execution.
      </p>
    ),
  },
  {
    title: 'Each Scenario Shows',
    body: (
      <ul className="list-disc list-inside space-y-1 text-slate-300">
        <li>What Cognitive Operators it targets.</li>
        <li>Which Processing Domains are tested.</li>
        <li>What a resilient response looks like.</li>
        <li>What a vulnerable response looks like.</li>
      </ul>
    ),
  },
];

interface Scenario {
  id: string;
  title: string;
  category: string;
  group?: string | null;
  prompt?: string;
  prompt_text?: string;
  target_operators?: number[];
  target_domains?: string[];
  target_drives?: number[];
  difficulty?: string;
  what_it_tests?: string;
  success_indicator?: string;
  failure_indicator?: string;
}

const CAT_COLORS: Record<string, string> = {
  healthcare: '#34d399', hiring: '#60a5fa', finance: '#fbbf24',
  governance: '#a78bfa', education: '#22d3ee', relationships: '#f472b6',
  ai_safety: '#f87171', environmental: '#34d399', adversarial_resilience: '#ef4444',
  life_execution: '#818cf8', cas_patterns: '#2dd4bf',
};

const CAT_LABELS: Record<string, string> = {
  healthcare: 'Healthcare', hiring: 'Hiring & HR', finance: 'Finance',
  governance: 'Governance', education: 'Education', relationships: 'Relationships',
  ai_safety: 'AI Safety', environmental: 'Environmental',
  adversarial_resilience: 'Adversarial', life_execution: 'Life Execution',
  cas_patterns: 'CAS Patterns',
};

const DIFF_COLORS: Record<string, string> = {
  easy: '#34d399', moderate: '#fbbf24', hard: '#f87171',
};

export function ScenarioBrowserPage() {
  const navigate = useNavigate();
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [selectedCat, setSelectedCat] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await apiFetch<{ scenarios: Scenario[] }>('/scenarios');
        setScenarios(data.scenarios ?? []);
        setLoadError(null);
      } catch (err) {
        setLoadError(err instanceof Error ? err.message : 'Failed to load scenarios');
      }
      setLoading(false);
    })();
  }, []);

  const categories = useMemo(() => {
    const cats: Record<string, number> = {};
    for (const s of scenarios) cats[s.category] = (cats[s.category] ?? 0) + 1;
    return Object.entries(cats).sort(([, a], [, b]) => b - a);
  }, [scenarios]);

  const filtered = useMemo(() => {
    let r = scenarios;
    if (selectedCat) r = r.filter(s => s.category === selectedCat);
    if (search.trim()) {
      const q = search.toLowerCase();
      r = r.filter(s =>
        (s.prompt_text ?? s.prompt ?? '').toLowerCase().includes(q) ||
        (s.title ?? '').toLowerCase().includes(q) ||
        (s.what_it_tests ?? '').toLowerCase().includes(q)
      );
    }
    return r;
  }, [scenarios, selectedCat, search]);

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <HowItWorksPanel sections={HOW_IT_WORKS_SECTIONS} label="How to Use Scenarios" />

      <div>
        <h1 className="text-2xl font-bold text-slate-100 mb-1">Scenario Browser</h1>
        <p className="text-sm text-slate-400">
          {scenarios.length} assessment scenarios across {categories.length} categories.
        </p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row">
        <input type="text" value={search} onChange={e => setSearch(e.target.value)}
          placeholder="Search scenarios..." className="flex-1 rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-2 text-sm text-slate-200 placeholder-slate-600 focus:border-accent-teal/50 focus:outline-none min-h-[44px]" />
        <select value={selectedCat ?? ''} onChange={e => setSelectedCat(e.target.value || null)}
          className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-sm text-slate-300 focus:border-accent-teal/50 focus:outline-none min-h-[44px]">
          <option value="" className="bg-dark-800">All ({scenarios.length})</option>
          {categories.map(([c, n]) => <option key={c} value={c} className="bg-dark-800">{CAT_LABELS[c] ?? c} ({n})</option>)}
        </select>
      </div>

      <div className="flex flex-wrap gap-2">
        <button onClick={() => setSelectedCat(null)}
          className={`rounded-full px-3 py-1.5 text-[11px] font-medium transition-all min-h-[36px] ${!selectedCat ? 'bg-accent-teal/15 text-accent-teal' : 'text-slate-500 hover:text-slate-300 bg-white/[0.03]'}`}>
          All ({scenarios.length})
        </button>
        {categories.map(([c, n]) => {
          const color = CAT_COLORS[c] ?? '#94a3b8';
          return (
            <button key={c} onClick={() => setSelectedCat(selectedCat === c ? null : c)}
              className="rounded-full px-3 py-1.5 text-[11px] font-medium transition-all min-h-[36px]"
              style={selectedCat === c ? { backgroundColor: `${color}20`, color } : { color: '#94a3b8' }}>
              {CAT_LABELS[c] ?? c} ({n})
            </button>
          );
        })}
      </div>

      <p className="text-[11px] text-slate-500">Showing {filtered.length} of {scenarios.length}</p>

      {loading ? (
        <Card><p className="text-sm text-slate-500 text-center py-8">Loading scenarios...</p></Card>
      ) : loadError ? (
        <Card>
          <div className="text-center py-8 space-y-2">
            <p className="text-sm text-red-400 font-medium">Could not load scenarios</p>
            <p className="text-xs text-slate-500">{loadError}</p>
          </div>
        </Card>
      ) : filtered.length === 0 ? (
        <Card><p className="text-sm text-slate-500 text-center py-8">No scenarios match your search.</p></Card>
      ) : (
        <div className="space-y-2">
          {filtered.map(s => {
            const color = CAT_COLORS[s.category] ?? '#94a3b8';
            const diffColor = DIFF_COLORS[s.difficulty ?? 'moderate'] ?? '#94a3b8';
            const open = expandedId === s.id;
            const prompt = s.prompt_text ?? s.prompt ?? '';
            return (
              <div key={s.id} className="glass-card overflow-hidden transition-all duration-150" style={open ? { borderColor: `${color}30` } : undefined}>
                <button onClick={() => setExpandedId(open ? null : s.id)} className="w-full flex items-start gap-3 p-4 text-left min-h-[44px]">
                  <span className="w-2 h-2 rounded-full mt-1.5 shrink-0" style={{ backgroundColor: color }} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="text-[9px] font-mono text-slate-600">{s.id}</span>
                      <span className="text-[9px] px-1.5 py-0.5 rounded" style={{ backgroundColor: `${color}15`, color }}>{CAT_LABELS[s.category] ?? s.category}</span>
                      {s.difficulty && <span className="text-[9px] px-1.5 py-0.5 rounded" style={{ backgroundColor: `${diffColor}15`, color: diffColor }}>{s.difficulty}</span>}
                    </div>
                    <p className="text-[12px] font-medium text-slate-200 mb-0.5">{s.title}</p>
                    <p className="text-[11px] text-slate-400 line-clamp-2">{prompt.slice(0, 150)}{prompt.length > 150 ? '...' : ''}</p>
                  </div>
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5"
                    className={`text-slate-600 shrink-0 mt-1 transition-transform ${open ? 'rotate-180' : ''}`}>
                    <path d="M3 5l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
                {open && (
                  <div className="px-4 pb-4 space-y-3 border-t border-white/[0.04] pt-3">
                    <p className="text-[12px] text-slate-300 leading-relaxed whitespace-pre-wrap">{prompt}</p>
                    {s.what_it_tests && (
                      <div className="rounded-lg bg-white/[0.02] border border-white/[0.06] p-3">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">What It Tests</p>
                        <p className="text-[11px] text-slate-400">{s.what_it_tests}</p>
                      </div>
                    )}
                    <div className="flex flex-wrap gap-2 text-[10px]">
                      {s.target_operators?.map(op => <span key={`op-${op}`} className="px-2 py-0.5 rounded bg-accent-teal/10 text-accent-teal font-mono">CO-{op}</span>)}
                      {s.target_domains?.map(d => <span key={`d-${d}`} className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400">{d}</span>)}
                      {s.target_drives?.map(i => <span key={`f-${i}`} className="px-2 py-0.5 rounded bg-purple-500/10 text-purple-400">F{i + 1}</span>)}
                    </div>
                    {(s.success_indicator || s.failure_indicator) && (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {s.success_indicator && <div className="rounded-lg bg-emerald-500/[0.04] border border-emerald-500/15 p-2"><p className="text-[9px] font-semibold text-emerald-400 mb-0.5">Resilient</p><p className="text-[10px] text-slate-400">{s.success_indicator}</p></div>}
                        {s.failure_indicator && <div className="rounded-lg bg-red-500/[0.04] border border-red-500/15 p-2"><p className="text-[9px] font-semibold text-red-400 mb-0.5">Vulnerable</p><p className="text-[10px] text-slate-400">{s.failure_indicator}</p></div>}
                      </div>
                    )}
                    <button onClick={() => navigate('/', { state: { prefill: prompt } })}
                      className="w-full rounded-lg bg-gradient-to-r from-accent-teal to-accent-cyan px-4 py-2.5 text-xs font-semibold text-dark-900 hover:opacity-90 transition-opacity min-h-[44px]">
                      Run This Assessment
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

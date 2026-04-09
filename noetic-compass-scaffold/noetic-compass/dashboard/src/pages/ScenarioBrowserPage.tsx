import { useState, useMemo } from 'react';
import { Card } from '../components/shared/Card';

// Embedded scenario catalog — loaded statically for now.
// In production, this would come from an API endpoint.

interface Scenario {
  id: string;
  group: string;
  group_label: string;
  prompt: string;
  attack_pattern?: string;
  resilience_target?: Record<string, string>;
  inversion_axis?: string;
  is_original?: boolean;
  inversion_notes?: string;
  target_operators?: number[];
  target_domain?: string;
}

const GROUP_COLORS: Record<string, string> = {
  cognitive_bias_resilience: '#60a5fa',
  discourse_boundary_resilience: '#a78bfa',
  prerequisite_integrity_resilience: '#2dd4bf',
  domain_coherence_resilience: '#fbbf24',
  inversion_detection_resilience: '#f87171',
  sample: '#94a3b8',
};

const GROUP_LABELS: Record<string, string> = {
  cognitive_bias_resilience: 'Cognitive Bias Resilience',
  discourse_boundary_resilience: 'Discourse Boundary Resilience',
  prerequisite_integrity_resilience: 'Prerequisite Integrity Resilience',
  domain_coherence_resilience: 'Domain Coherence Resilience',
  inversion_detection_resilience: 'Inversion Detection Resilience',
  sample: 'Base Scenarios',
};

// Fetch scenarios from API or static catalog
function useScenarios() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const load = async () => {
    if (loaded) return;
    setLoading(true);
    try {
      // Try API endpoint first, fall back to static file
      const urls = ['/api/scenarios/catalog', '/scenarios/catalog/adversarial_resilience.json'];
      for (const url of urls) {
        try {
          const res = await fetch(url);
          if (res.ok) {
            const data = await res.json();
            const items = data.scenarios ?? (Array.isArray(data) ? data : []);
            if (items.length > 0) {
              setScenarios(items);
              break;
            }
          }
        } catch {
          continue;
        }
      }
    } catch {
      // No scenarios available
    }
    setLoading(false);
    setLoaded(true);
  };

  return { scenarios, loading, loaded, load };
}

export function ScenarioBrowserPage() {
  const { scenarios, loading, loaded, load } = useScenarios();
  const [search, setSearch] = useState('');
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Load on mount
  if (!loaded && !loading) {
    load();
  }

  const groups = useMemo(() => {
    const g: Record<string, number> = {};
    for (const s of scenarios) {
      g[s.group] = (g[s.group] ?? 0) + 1;
    }
    return Object.entries(g).sort(([, a], [, b]) => b - a);
  }, [scenarios]);

  const filtered = useMemo(() => {
    let result = scenarios;
    if (selectedGroup) {
      result = result.filter(s => s.group === selectedGroup);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(s =>
        s.prompt.toLowerCase().includes(q) ||
        (s.attack_pattern ?? '').toLowerCase().includes(q) ||
        (s.group_label ?? '').toLowerCase().includes(q)
      );
    }
    return result;
  }, [scenarios, selectedGroup, search]);

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-slate-100 mb-1">Scenario Browser</h1>
        <p className="text-sm text-slate-400">
          Browse {scenarios.length} adversarial resilience testing scenarios. Each tests whether an AI system
          is resilient to a specific manipulation pattern.
        </p>
      </div>

      {/* Search + Filter */}
      <div className="flex flex-col gap-3 sm:flex-row">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search scenarios..."
          className="flex-1 rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-2 text-sm text-slate-200 placeholder-slate-600 focus:border-accent-teal/50 focus:outline-none min-h-[44px]"
        />
        <select
          value={selectedGroup ?? ''}
          onChange={(e) => setSelectedGroup(e.target.value || null)}
          className="rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-sm text-slate-300 focus:border-accent-teal/50 focus:outline-none min-h-[44px]"
        >
          <option value="" className="bg-dark-800">All Groups ({scenarios.length})</option>
          {groups.map(([group, count]) => (
            <option key={group} value={group} className="bg-dark-800">
              {GROUP_LABELS[group] ?? group} ({count})
            </option>
          ))}
        </select>
      </div>

      {/* Group pills */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setSelectedGroup(null)}
          className={`rounded-full px-3 py-1.5 text-[11px] font-medium transition-all min-h-[36px] ${
            !selectedGroup ? 'bg-accent-teal/15 text-accent-teal' : 'text-slate-500 hover:text-slate-300 bg-white/[0.03]'
          }`}
        >
          All
        </button>
        {groups.map(([group, count]) => {
          const color = GROUP_COLORS[group] ?? '#94a3b8';
          const active = selectedGroup === group;
          return (
            <button
              key={group}
              onClick={() => setSelectedGroup(active ? null : group)}
              className={`rounded-full px-3 py-1.5 text-[11px] font-medium transition-all min-h-[36px] ${
                active ? '' : 'hover:bg-white/[0.04]'
              }`}
              style={active ? { backgroundColor: `${color}20`, color } : { color: '#94a3b8' }}
            >
              {GROUP_LABELS[group]?.split(' ')[0] ?? group} ({count})
            </button>
          );
        })}
      </div>

      {/* Results count */}
      <p className="text-[11px] text-slate-500">
        Showing {filtered.length} of {scenarios.length} scenarios
      </p>

      {/* Scenario list */}
      {loading ? (
        <Card><p className="text-sm text-slate-500 text-center py-8">Loading scenarios...</p></Card>
      ) : filtered.length === 0 ? (
        <Card><p className="text-sm text-slate-500 text-center py-8">No scenarios match your search.</p></Card>
      ) : (
        <div className="space-y-2">
          {filtered.map((scenario) => {
            const color = GROUP_COLORS[scenario.group] ?? '#94a3b8';
            const isExpanded = expandedId === scenario.id;

            return (
              <div
                key={scenario.id}
                className="glass-card overflow-hidden transition-all duration-150"
                style={isExpanded ? { borderColor: `${color}30` } : undefined}
              >
                <button
                  onClick={() => setExpandedId(isExpanded ? null : scenario.id)}
                  className="w-full flex items-start gap-3 p-4 text-left min-h-[44px]"
                >
                  <span
                    className="w-2 h-2 rounded-full mt-1.5 shrink-0"
                    style={{ backgroundColor: color }}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[9px] font-mono text-slate-600">{scenario.id}</span>
                      {scenario.attack_pattern && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-white/[0.04] text-slate-400">
                          {scenario.attack_pattern.replace(/_/g, ' ')}
                        </span>
                      )}
                    </div>
                    <p className="text-[12px] text-slate-300 leading-relaxed line-clamp-2">
                      {scenario.prompt.slice(0, 200)}{scenario.prompt.length > 200 ? '...' : ''}
                    </p>
                  </div>
                  <svg
                    width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5"
                    className={`text-slate-600 shrink-0 mt-1 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                  >
                    <path d="M3 5l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>

                {isExpanded && (
                  <div className="px-4 pb-4 space-y-3 border-t border-white/[0.04] pt-3">
                    <p className="text-[12px] text-slate-300 leading-relaxed whitespace-pre-wrap">
                      {scenario.prompt}
                    </p>

                    <div className="flex flex-wrap gap-2 text-[10px]">
                      <span className="px-2 py-1 rounded" style={{ backgroundColor: `${color}15`, color }}>
                        {scenario.group_label}
                      </span>
                      {scenario.inversion_axis && (
                        <span className="px-2 py-1 rounded bg-amber-500/10 text-amber-400">
                          {scenario.inversion_axis}-axis
                        </span>
                      )}
                      {scenario.resilience_target && (
                        <span className="px-2 py-1 rounded bg-accent-teal/10 text-accent-teal">
                          Target: {scenario.resilience_target.operator ?? ''} {scenario.resilience_target.domain ?? ''}
                        </span>
                      )}
                    </div>

                    {scenario.inversion_notes && (
                      <p className="text-[11px] text-slate-500">
                        <strong className="text-slate-400">Detection: </strong>
                        {scenario.inversion_notes}
                      </p>
                    )}
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

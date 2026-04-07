/**
 * CohortPage — cohort comparison and clustering visualization.
 *
 * Stakeholders can input multiple candidate profiles and see how
 * they cluster relative to each other using Fisher-Rao geometry.
 */

import { useState } from 'react';
import { useCohort } from '../hooks/useCohort';
import { Card } from '../components/shared/Card';
import { LoadingSpinner } from '../components/shared/LoadingSpinner';
import { ErrorBanner } from '../components/shared/ErrorBanner';
import { CohortHeatmap } from '../components/charts/CohortHeatmap';
import type { CohortCompareRequest } from '../api/types';

interface ProfileInput {
  label: string;
  scores: string; // comma-separated operator scores
}

const DEFAULT_PROFILES: ProfileInput[] = [
  { label: 'Candidate A', scores: '0.85,0.78,0.72,0.80,0.88,0.65,0.70,0.82,0.75,0.68' },
  { label: 'Candidate B', scores: '0.60,0.55,0.90,0.88,0.50,0.92,0.85,0.45,0.70,0.75' },
  { label: 'Candidate C', scores: '0.82,0.80,0.75,0.78,0.85,0.68,0.72,0.80,0.77,0.70' },
];

function parseScores(s: string): number[] {
  return s.split(',').map(v => parseFloat(v.trim())).filter(v => !isNaN(v));
}

function scoresToDomainAverages(scores: number[]): number[] {
  // P=[0,1,4], C=[2,3,7], E=[5,6], O=[8,9]
  const map = [[0, 1, 4], [2, 3, 7], [5, 6], [8, 9]];
  const raw = map.map(indices => {
    const avg = indices.reduce((sum, i) => sum + (scores[i] ?? 0.5), 0) / indices.length;
    return Math.max(0.001, avg);
  });
  const total = raw.reduce((a, b) => a + b, 0);
  return raw.map(v => v / total);
}

export function CohortPage() {
  const [profiles, setProfiles] = useState<ProfileInput[]>(DEFAULT_PROFILES);
  const cohort = useCohort();

  function addProfile() {
    setProfiles([...profiles, { label: `Candidate ${String.fromCharCode(65 + profiles.length)}`, scores: '0.7,0.7,0.7,0.7,0.7,0.7,0.7,0.7,0.7,0.7' }]);
  }

  function removeProfile(idx: number) {
    setProfiles(profiles.filter((_, i) => i !== idx));
  }

  function updateProfile(idx: number, field: keyof ProfileInput, value: string) {
    const updated = [...profiles];
    updated[idx] = { ...updated[idx], [field]: value };
    setProfiles(updated);
  }

  function handleCompare() {
    const req: CohortCompareRequest = {
      profiles: profiles.map(p => {
        const scores = parseScores(p.scores);
        return {
          label: p.label,
          operator_scores: scores.length === 10 ? scores : Array(10).fill(0.5),
          domain_averages: scoresToDomainAverages(scores),
        };
      }),
    };
    cohort.mutate(req);
  }

  const result = cohort.data;

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <h2 className="text-xl font-bold text-slate-100">Cohort Analysis</h2>
      <p className="text-sm text-slate-400">
        Compare cognitive profiles to see how candidates align with each other.
        Useful for team composition, hiring, and group assessment.
      </p>

      {/* Profile inputs */}
      <Card title="Candidate Profiles">
        <div className="space-y-3">
          {profiles.map((p, i) => (
            <div key={i} className="flex items-center gap-3">
              <input
                value={p.label}
                onChange={(e) => updateProfile(i, 'label', e.target.value)}
                className="w-36 rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-sm text-slate-200 focus:border-accent-teal/50 focus:outline-none"
                placeholder="Label"
              />
              <input
                value={p.scores}
                onChange={(e) => updateProfile(i, 'scores', e.target.value)}
                className="flex-1 rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-sm text-slate-300 font-mono focus:border-accent-teal/50 focus:outline-none"
                placeholder="10 comma-separated scores (0-1)"
              />
              {profiles.length > 2 && (
                <button
                  onClick={() => removeProfile(i)}
                  className="text-slate-600 hover:text-red-400 transition-colors text-sm px-2"
                >
                  Remove
                </button>
              )}
            </div>
          ))}

          <div className="flex gap-3">
            <button
              onClick={addProfile}
              className="rounded-lg border border-white/[0.08] px-4 py-2 text-sm text-slate-400 hover:text-slate-200 hover:border-white/[0.15] transition-colors"
            >
              + Add Candidate
            </button>
            <button
              onClick={handleCompare}
              disabled={cohort.isPending || profiles.length < 2}
              className="rounded-lg bg-gradient-to-r from-accent-teal to-accent-cyan px-6 py-2 text-sm font-semibold text-dark-900 hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-opacity"
            >
              {cohort.isPending ? 'Comparing...' : 'Compare Profiles'}
            </button>
          </div>
        </div>
      </Card>

      {cohort.isPending && <LoadingSpinner />}
      <ErrorBanner error={cohort.error as Error | null} />

      {/* Results */}
      {result && (
        <div className="space-y-5">
          {/* Cluster summary */}
          <Card title="Cluster Summary">
            <div className="space-y-3">
              <p className="text-sm text-slate-400">
                Profiles grouped by cognitive proximity. Profiles in the same cluster
                share similar cognitive architectures.
              </p>
              <div className="flex flex-wrap gap-2">
                {result.clusters.map((c) => (
                  <span
                    key={c.label}
                    className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[12px] font-medium border border-white/[0.06] bg-white/[0.02]"
                  >
                    <span
                      className="h-2 w-2 rounded-full"
                      style={{ backgroundColor: CLUSTER_COLORS[c.cluster % CLUSTER_COLORS.length] }}
                    />
                    {c.label}
                    <span className="text-[10px] text-slate-500 ml-0.5">Cluster {c.cluster + 1}</span>
                  </span>
                ))}
              </div>
            </div>
          </Card>

          {/* Heatmap */}
          <Card title="Alignment Heatmap">
            <CohortHeatmap result={result} />
          </Card>

          {/* Distance table */}
          <Card title="Pairwise Comparison">
            <div className="overflow-x-auto">
              <table className="w-full text-[12px]">
                <thead>
                  <tr className="text-left text-slate-500 border-b border-white/[0.06]">
                    <th className="px-3 py-2">From</th>
                    <th className="px-3 py-2">To</th>
                    <th className="px-3 py-2">Alignment</th>
                    <th className="px-3 py-2">Similarity</th>
                    <th className="px-3 py-2">Cognitive Distance</th>
                  </tr>
                </thead>
                <tbody>
                  {result.distances.map((d, i) => (
                    <tr key={i} className="border-b border-white/[0.03] hover:bg-white/[0.02]">
                      <td className="px-3 py-2 text-slate-200 font-medium">{d.from_label}</td>
                      <td className="px-3 py-2 text-slate-200 font-medium">{d.to_label}</td>
                      <td className="px-3 py-2">
                        <span className="font-mono font-bold" style={{ color: alignmentColor(d.alignment_pct) }}>
                          {d.alignment_pct.toFixed(1)}%
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        <span className="font-mono font-bold" style={{ color: alignmentColor(d.similarity_pct) }}>
                          {d.similarity_pct.toFixed(1)}%
                        </span>
                      </td>
                      <td className="px-3 py-2 font-mono text-slate-400">
                        {d.geodesic_distance.toFixed(4)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

const CLUSTER_COLORS = ['#22d3ee', '#a78bfa', '#34d399', '#fbbf24', '#f87171', '#f472b6'];

function alignmentColor(pct: number): string {
  if (pct >= 80) return '#22d3ee';
  if (pct >= 60) return '#34d399';
  if (pct >= 40) return '#fbbf24';
  return '#ef4444';
}

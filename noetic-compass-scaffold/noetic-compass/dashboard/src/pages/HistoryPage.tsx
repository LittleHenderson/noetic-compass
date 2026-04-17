import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { saveAs } from 'file-saver';
import { useHistoryStore } from '../stores/historyStore';
import { CertBadge } from '../components/shared/CertBadge';
import { Card } from '../components/shared/Card';
import { ResearchPrototypeNotice } from '../components/shared/ResearchPrototypeNotice';
import type { AssessmentRecord, StageResult } from '../api/types';

/** Flatten a record into the same column schema used by the API export. */
function flattenRecord(r: AssessmentRecord) {
  const nccs = r.result.nccs;
  const provenance = r.result.provenance ?? {};
  const stages = r.result.stages ?? [];

  let coScores: number[] = [];
  let domainAvgs: number[] = [];
  for (const s of stages as StageResult[]) {
    if (s.stage === 'operator_scoring') coScores = (s.data.operator_scores as number[]) ?? [];
    if (s.stage === 'domain_coherence') domainAvgs = (s.data.domain_averages as number[]) ?? [];
  }

  return {
    timestamp: new Date(r.timestamp).toISOString(),
    text: r.text.slice(0, 200),
    composite: nccs.composite,
    certification: nccs.certification,
    operator_profile: nccs.operator_profile,
    domain_coherence: nccs.domain_coherence,
    drive_rpm_integrity: nccs.drive_rpm_integrity,
    pathway_quality: nccs.pathway_quality,
    inversion_resistance: nccs.inversion_resistance,
    social_engineering: nccs.social_engineering,
    co_0: coScores[0] ?? '',
    co_1: coScores[1] ?? '',
    co_2: coScores[2] ?? '',
    co_3: coScores[3] ?? '',
    co_4: coScores[4] ?? '',
    co_5: coScores[5] ?? '',
    co_6: coScores[6] ?? '',
    co_7: coScores[7] ?? '',
    co_8: coScores[8] ?? '',
    co_9: coScores[9] ?? '',
    domain_P: domainAvgs[0] ?? '',
    domain_C: domainAvgs[1] ?? '',
    domain_E: domainAvgs[2] ?? '',
    domain_O: domainAvgs[3] ?? '',
    provider: (provenance.connector as string) ?? '',
    elapsed_ms: (provenance.elapsed_ms as number) ?? '',
  };
}

function exportJSON(records: AssessmentRecord[]) {
  const data = records.map(flattenRecord);
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  saveAs(blob, `assessments-${Date.now()}.json`);
}

function exportCSV(records: AssessmentRecord[]) {
  const rows = records.map(flattenRecord);
  if (rows.length === 0) return;

  const headers = Object.keys(rows[0]);
  const csvLines = [
    headers.join(','),
    ...rows.map((row) =>
      headers
        .map((h) => {
          const val = String(row[h as keyof typeof row] ?? '');
          return val.includes(',') || val.includes('"') || val.includes('\n')
            ? `"${val.replace(/"/g, '""')}"`
            : val;
        })
        .join(','),
    ),
  ];

  const blob = new Blob([csvLines.join('\n')], { type: 'text/csv' });
  saveAs(blob, `assessments-${Date.now()}.csv`);
}

export function HistoryPage() {
  const records = useHistoryStore((s) => s.records);
  const clearHistory = useHistoryStore((s) => s.clear);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    if (dropdownOpen) document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [dropdownOpen]);

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-100">History</h2>
          {records.length > 0 && (
            <p className="text-[11px] text-slate-500 mt-0.5">
              {records.length} prompt{records.length !== 1 ? 's' : ''} assessed
              {records.length < 40 ? (
                <span className="text-amber-400"> — {40 - records.length} more for broader prompt coverage</span>
              ) : (
                <span className="text-emerald-400"> — broader coverage reached</span>
              )}
            </p>
          )}
        </div>
        {records.length > 0 && (
          <div className="flex items-center gap-2">
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setDropdownOpen((v) => !v)}
                className="rounded-lg border border-accent-teal/30 bg-accent-teal/10 px-3 py-2 text-xs font-medium text-accent-teal hover:bg-accent-teal/20 transition-colors min-h-[44px]"
              >
                Export All Data
              </button>
              {dropdownOpen && (
                <div className="absolute right-0 mt-1 w-36 rounded-lg border border-white/10 bg-slate-800 shadow-lg z-10">
                  <button
                    onClick={() => {
                      exportCSV(records);
                      setDropdownOpen(false);
                    }}
                    className="block w-full px-4 py-3 text-left text-xs text-slate-300 hover:bg-white/[0.05] rounded-t-lg transition-colors min-h-[44px]"
                  >
                    Download CSV
                  </button>
                  <button
                    onClick={() => {
                      exportJSON(records);
                      setDropdownOpen(false);
                    }}
                    className="block w-full px-4 py-3 text-left text-xs text-slate-300 hover:bg-white/[0.05] rounded-b-lg transition-colors min-h-[44px]"
                  >
                    Download JSON
                  </button>
                </div>
              )}
            </div>
            <button
              onClick={() => {
                if (confirm('Clear all history?')) clearHistory();
              }}
              className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs font-medium text-red-400 hover:bg-red-500/20 transition-colors min-h-[44px]"
            >
              Clear All
            </button>
          </div>
        )}
      </div>

      <ResearchPrototypeNotice compact />

      {records.length === 0 ? (
        <Card>
          <div className="text-center py-12 space-y-3">
            <p className="text-sm text-slate-400">No assessments yet</p>
            <p className="text-xs text-slate-500">Run your first assessment to see results here</p>
            <a href="/assessment" className="inline-block rounded-lg bg-gradient-to-r from-accent-teal to-accent-cyan px-4 py-2 text-sm font-semibold text-dark-900 hover:opacity-90 transition-opacity">
              Go to Assessment
            </a>
          </div>
        </Card>
      ) : (
        <div className="glass-card overflow-hidden">
          <div className="overflow-x-auto -mx-0">
            <table className="w-full text-sm min-w-[480px]">
              <thead>
                <tr className="border-b border-white/[0.06] text-left text-[11px] text-slate-500 uppercase tracking-wider">
                  <th className="px-4 py-3">Time</th>
                  <th className="px-4 py-3">Text</th>
                  <th className="px-4 py-3">Score</th>
                  <th className="px-4 py-3">Research Tier</th>
                </tr>
              </thead>
              <tbody>
                {records.map((r) => (
                  <tr key={r.id} className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors">
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-500">
                      {new Date(r.timestamp).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 max-w-xs truncate">
                      <Link to={`/details/${r.id}`} className="text-accent-teal hover:text-accent-cyan transition-colors">
                        {r.text.slice(0, 80)}{r.text.length > 80 ? '...' : ''}
                      </Link>
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-300">{r.result.nccs.composite.toFixed(1)}</td>
                    <td className="px-4 py-3">
                      <CertBadge certification={r.result.nccs.certification} composite={r.result.nccs.composite} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

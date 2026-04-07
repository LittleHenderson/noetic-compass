/**
 * InversionAlert — shows flagged inversion axes with expandable
 * "Why?" drill-down that displays the trigger reason and a
 * transcript snippet for audit traceability.
 */

import { useState } from 'react';
import type { WrapResult, InversionEvidence } from '../../api/types';
import { t } from '../../lib/translations';

const SEVERITY_BG: Record<string, string> = {
  none: 'border-slate-700/30 bg-slate-700/5',
  low: 'border-emerald-400/20 bg-emerald-400/[0.04]',
  moderate: 'border-amber-400/20 bg-amber-400/[0.04]',
  stealth: 'border-purple-400/20 bg-purple-400/[0.04]',
  high: 'border-red-400/20 bg-red-400/[0.04]',
};

const SEVERITY_DOT: Record<string, string> = {
  none: '#475569',
  low: '#34d399',
  moderate: '#fbbf24',
  stealth: '#a78bfa',
  high: '#ef4444',
};

const SEVERITY_LABEL: Record<string, string> = {
  none: 'Stable',
  low: 'Low Risk',
  moderate: 'Moderate',
  stealth: 'Stealth Risk',
  high: 'High Risk',
};

function EvidenceCard({ ev }: { ev: InversionEvidence }) {
  const [expanded, setExpanded] = useState(false);
  const term = t(ev.axis);
  const bgClass = SEVERITY_BG[ev.severity] ?? SEVERITY_BG.none;
  const dotColor = SEVERITY_DOT[ev.severity] ?? SEVERITY_DOT.none;

  return (
    <div className={`rounded-lg border ${bgClass} transition-all duration-200`}>
      <button
        className="w-full flex items-center gap-3 px-3 py-2.5 text-left"
        onClick={() => setExpanded(!expanded)}
      >
        {/* Severity dot */}
        <div className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: dotColor }} />

        {/* Axis label + business name */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[12px] font-semibold text-slate-200 truncate">
              {term.label}
            </span>
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-[10px] px-1.5 py-0.5 rounded-full font-medium" style={{
                color: dotColor,
                backgroundColor: `${dotColor}15`,
              }}>
                {SEVERITY_LABEL[ev.severity]}
              </span>
              <span className="font-mono text-[12px] font-bold" style={{ color: dotColor }}>
                {(ev.score * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        </div>

        {/* Expand arrow */}
        <svg
          className={`w-3.5 h-3.5 text-slate-500 shrink-0 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="px-3 pb-3 space-y-2 animate-chart-in">
          {/* Trigger explanation */}
          <div className="rounded border border-white/[0.04] bg-white/[0.02] px-3 py-2">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">Why this was flagged</span>
            <p className="text-[11px] text-slate-300 mt-1 leading-relaxed">{ev.trigger}</p>
          </div>

          {/* Transcript snippet */}
          {ev.transcript_snippet && (
            <div className="rounded border border-white/[0.04] bg-white/[0.02] px-3 py-2">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">Related Transcript</span>
              <p className="text-[11px] text-slate-400 mt-1 font-mono leading-relaxed italic">
                &quot;{ev.transcript_snippet}&quot;
              </p>
            </div>
          )}

          {/* Technical tooltip */}
          <p className="text-[10px] text-slate-600">{term.tooltip}</p>
        </div>
      )}
    </div>
  );
}

export function InversionAlert({ result }: { result: WrapResult }) {
  const invStage = result.stages.find(s => s.stage === 'inversion_scan');
  if (!invStage) return null;

  const evidence = (invStage.data.evidence as InversionEvidence[] | undefined) ?? [];
  const stealthResistance = invStage.data.stealth_resistance as number | undefined;

  const flagged = evidence.filter(e => e.flagged);
  const stable = evidence.filter(e => !e.flagged);

  return (
    <div className="space-y-3">
      {/* Summary line */}
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-slate-400">
          {flagged.length === 0
            ? 'All 7 stability axes are within normal range.'
            : `${flagged.length} of 7 axes flagged for review.`}
        </span>
        {stealthResistance != null && (
          <span className="text-[10px] text-slate-500">
            Hidden Threat Detection: <span className="font-mono font-bold text-slate-300">{(stealthResistance * 100).toFixed(0)}%</span>
          </span>
        )}
      </div>

      {/* Flagged items first */}
      {flagged.length > 0 && (
        <div className="space-y-1.5">
          <h4 className="text-[10px] text-amber-400/80 uppercase tracking-wider font-medium">Requires Attention</h4>
          {flagged.map(ev => <EvidenceCard key={ev.axis_index} ev={ev} />)}
        </div>
      )}

      {/* Stable items */}
      {stable.length > 0 && (
        <div className="space-y-1.5">
          <h4 className="text-[10px] text-emerald-400/60 uppercase tracking-wider font-medium">Stable</h4>
          {stable.map(ev => <EvidenceCard key={ev.axis_index} ev={ev} />)}
        </div>
      )}
    </div>
  );
}

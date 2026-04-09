import type { FractalAnalysis } from '../../api/types';
import { OPERATOR_LABELS } from '../../lib/constants';

const CLASS_BADGES: Record<string, { color: string; label: string; description: string }> = {
  stabilizing: {
    color: '#34d399',
    label: 'Stabilizing',
    description: 'Reasoning converges toward a stable conclusion.',
  },
  amplifying: {
    color: '#f87171',
    label: 'Amplifying',
    description: 'Reasoning escalates without self-regulation. Watch for runaway conclusions.',
  },
  oscillatory: {
    color: '#fbbf24',
    label: 'Oscillatory',
    description: 'Reasoning cycles between positions rather than converging.',
  },
  neutral: {
    color: '#94a3b8',
    label: 'Neutral',
    description: 'Identity pattern — no dominant fractal structure detected.',
  },
};

const NODE_COLORS = [
  '#2dd4bf', '#60a5fa', '#a78bfa', '#f472b6', '#34d399',
  '#fbbf24', '#818cf8', '#f87171', '#22d3ee', '#fb923c',
];

export function FractalCard({ analysis }: { analysis: FractalAnalysis }) {
  const badge = CLASS_BADGES[analysis.classification] ?? CLASS_BADGES.neutral;

  return (
    <div className="space-y-4">
      {/* Classification badge */}
      <div className="flex items-center gap-3">
        <span
          className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold"
          style={{ color: badge.color, backgroundColor: `${badge.color}15`, border: `1px solid ${badge.color}30` }}
        >
          <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: badge.color }} />
          {badge.label}
        </span>
        <span className="text-[11px] text-slate-400">{badge.description}</span>
      </div>

      {/* Operator sequence visualization */}
      <div className="flex items-center gap-1 flex-wrap">
        {analysis.canonical_form.map((op, i) => {
          const label = OPERATOR_LABELS[op]?.split(': ')[1] ?? `CO-${op}`;
          return (
            <div key={i} className="flex items-center gap-1">
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center text-[10px] font-bold border"
                style={{
                  color: NODE_COLORS[op],
                  backgroundColor: `${NODE_COLORS[op]}10`,
                  borderColor: `${NODE_COLORS[op]}30`,
                }}
                title={`CO-${op}: ${label}`}
              >
                {op}
              </div>
              {i < analysis.canonical_form.length - 1 && (
                <svg width="12" height="8" className="text-slate-600 shrink-0">
                  <path d="M0 4h8m-3-3l3 3-3 3" fill="none" stroke="currentColor" strokeWidth="1" />
                </svg>
              )}
            </div>
          );
        })}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        <div className="text-center">
          <p className="text-lg font-bold text-slate-200">{analysis.orbit_length}</p>
          <p className="text-[9px] text-slate-500">Orbit Length</p>
        </div>
        <div className="text-center">
          <p className="text-lg font-bold" style={{ color: analysis.cancellations_detected > 0 ? '#f87171' : '#34d399' }}>
            {analysis.cancellations_detected}
          </p>
          <p className="text-[9px] text-slate-500">Contradictions</p>
        </div>
        <div className="text-center">
          <p className="text-lg font-bold" style={{ color: analysis.has_fixed_point ? '#34d399' : '#fbbf24' }}>
            {analysis.has_fixed_point ? 'Yes' : 'No'}
          </p>
          <p className="text-[9px] text-slate-500">Fixed Point</p>
        </div>
      </div>

      {analysis.cancellations_detected > 0 && (
        <p className="text-[11px] text-red-400/80 leading-relaxed">
          {analysis.cancellations_detected} self-contradiction{analysis.cancellations_detected !== 1 ? 's' : ''} detected
          — the AI asserted something then immediately reversed it. This is a structural coherence issue.
        </p>
      )}
    </div>
  );
}

import { useState } from 'react';
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Tooltip, ResponsiveContainer,
} from 'recharts';
import { INVERSION_AXIS_LABELS } from '../../lib/constants';
import { interpretInversion, interpretStealth } from '../../lib/interpretations';

/** Rich tooltip that shows axis description + verdict on hover. */
function AxisTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: { axis: string; resistance: number; description: string; verdict: string } }> }) {
  if (!active || !payload || payload.length === 0) return null;
  const d = payload[0].payload;
  return (
    <div className="max-w-xs rounded-lg border border-white/[0.08] bg-dark-800/95 backdrop-blur p-3 shadow-xl">
      <div className="flex items-center justify-between gap-3 mb-1">
        <span className="text-[12px] font-semibold text-slate-100">{d.axis}</span>
        <span className="font-mono text-[12px] font-bold text-accent-teal">{d.resistance}%</span>
      </div>
      <p className="text-[11px] text-slate-400 leading-relaxed">{d.description}</p>
      <p className="text-[10px] text-slate-500 mt-1.5 italic">{d.verdict}</p>
    </div>
  );
}

export function InversionMap({
  axisScores,
  stealthResistance,
}: {
  axisScores: number[];
  stealthResistance: number;
}) {
  // Always-visible detail panel state. Default open so first-time users see every axis.
  const [showDetails, setShowDetails] = useState(true);
  const [expandedAxis, setExpandedAxis] = useState<number | null>(null);

  const insights = axisScores.map((s, i) => interpretInversion(i, s));
  const stealthNote = interpretStealth(stealthResistance);

  // Chart data now carries description + verdict for the rich hover tooltip.
  const data = axisScores.map((s, i) => ({
    axis: INVERSION_AXIS_LABELS[i].split(':')[0],
    resistance: +(s * 100).toFixed(1),
    description: insights[i].description,
    verdict: insights[i].verdict,
  }));

  function scoreColor(score: number): string {
    if (score >= 0.6) return 'text-emerald-400';
    if (score >= 0.4) return 'text-amber-400';
    return 'text-red-400';
  }

  function scoreBarColor(score: number): string {
    if (score >= 0.6) return '#34d399';
    if (score >= 0.4) return '#fbbf24';
    return '#f87171';
  }

  return (
    <div>
      <div className="animate-chart-in">
        <ResponsiveContainer width="100%" height={260}>
          <RadarChart data={data} cx="50%" cy="50%" outerRadius="65%">
            <PolarGrid stroke="rgba(255,255,255,0.06)" />
            <PolarAngleAxis dataKey="axis" tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <PolarRadiusAxis domain={[0, 100]} tick={{ fill: '#475569', fontSize: 9 }} axisLine={false} />
            <Tooltip content={<AxisTooltip />} />
            <Radar
              dataKey="resistance"
              stroke="#f87171"
              strokeWidth={2}
              fill="#f87171"
              fillOpacity={0.12}
            />
          </RadarChart>
        </ResponsiveContainer>
        <div className="text-[11px] text-slate-500 text-center font-medium">
          Stealth Resistance: <span className="text-red-400">{(stealthResistance * 100).toFixed(1)}%</span>
        </div>
      </div>

      {/* Always-visible axis details — click each card to expand the full description.
          This replaces the click-the-chart-to-open hidden panel that users weren't discovering. */}
      <div className="mt-4 pt-4 border-t border-white/[0.04]">
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="flex items-center justify-between w-full text-left min-h-[36px]"
        >
          <span className="text-[11px] font-semibold uppercase tracking-wider text-accent-teal">
            {showDetails ? '▾' : '▸'} Read About Each Inversion ({axisScores.length})
          </span>
          <span className="text-[10px] text-slate-500">Hover chart for tooltip · click cards below for detail</span>
        </button>

        {showDetails && (
          <div className="mt-3 space-y-2 animate-slide-down">
            {insights.map((inv) => {
              const isOpen = expandedAxis === inv.index;
              const pct = Math.round(inv.score * 100);
              return (
                <div
                  key={inv.index}
                  className="rounded-lg border border-white/[0.06] bg-white/[0.02] overflow-hidden"
                >
                  <button
                    onClick={() => setExpandedAxis(isOpen ? null : inv.index)}
                    className="w-full flex items-center gap-3 px-3 py-2.5 text-left min-h-[44px] hover:bg-white/[0.02] transition-colors"
                  >
                    <span className="text-[12px] font-semibold text-slate-200 w-28 shrink-0">{inv.label}</span>
                    {/* Inline resistance bar */}
                    <div className="flex-1 h-1.5 rounded-full bg-white/[0.04] overflow-hidden">
                      <div
                        className="h-full transition-all duration-500"
                        style={{ width: `${pct}%`, backgroundColor: scoreBarColor(inv.score) }}
                      />
                    </div>
                    <span className={`font-mono text-[11px] font-bold w-10 text-right ${scoreColor(inv.score)}`}>
                      {pct}%
                    </span>
                    <svg
                      width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5"
                      className={`text-slate-500 shrink-0 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
                    >
                      <path d="M2 4l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </button>
                  {isOpen && (
                    <div className="px-3 pb-3 pt-1 border-t border-white/[0.04] space-y-1.5">
                      <p className="text-[11px] text-slate-300 leading-relaxed">{inv.description}</p>
                      <p className="text-[11px] text-slate-500 italic">{inv.verdict}</p>
                    </div>
                  )}
                </div>
              );
            })}

            {/* Stealth detection footer */}
            <div className="rounded-lg border border-red-400/20 bg-red-400/[0.04] px-3 py-2.5">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[12px] font-semibold text-red-400">Stealth Detection</span>
                <span className="font-mono text-[11px] font-bold text-red-400">
                  {(stealthResistance * 100).toFixed(0)}%
                </span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">{stealthNote}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

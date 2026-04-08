import type { Interpretation } from '../../api/types';

interface AiBriefingProps {
  interpretation: Interpretation;
}

export function AiBriefing({ interpretation }: AiBriefingProps) {
  return (
    <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <span className="inline-flex items-center rounded-full bg-accent-teal/15 px-3 py-1 text-xs font-semibold text-accent-teal">
          AI Interpretation
        </span>
      </div>

      {/* THE BOTTOM LINE */}
      <div className="space-y-2">
        <h4 className="text-xs font-bold uppercase tracking-wider text-amber-400">
          The Bottom Line
        </h4>
        <p className="text-sm leading-relaxed text-slate-200">
          {interpretation.bottom_line}
        </p>
      </div>

      {/* WHAT WE FOUND */}
      <div className="space-y-2">
        <h4 className="text-xs font-bold uppercase tracking-wider text-accent-teal">
          What We Found
        </h4>
        <div className="space-y-2">
          {interpretation.findings.map((finding, i) => (
            <p
              key={i}
              className="border-l-2 border-slate-600 pl-3 text-sm leading-relaxed text-slate-400"
            >
              {finding}
            </p>
          ))}
        </div>
      </div>

      {/* WHAT WE RECOMMEND */}
      <div className="space-y-2">
        <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-400">
          What We Recommend
        </h4>
        <ul className="space-y-1.5">
          {interpretation.recommendations.map((rec, i) => (
            <li
              key={i}
              className="flex items-start gap-2 text-sm leading-relaxed text-slate-200"
            >
              <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-emerald-400" />
              {rec}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

import type { ReactNode } from 'react';

export function ExplainPanel({
  children,
  visible,
  onClose,
}: {
  children: ReactNode;
  visible: boolean;
  onClose: () => void;
}) {
  if (!visible) return null;
  return (
    <div className="animate-slide-down rounded-lg border border-white/[0.06] bg-dark-800/80 backdrop-blur-sm px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 text-[13px] leading-relaxed text-slate-300 space-y-2">
          {children}
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); onClose(); }}
          className="mt-0.5 flex-shrink-0 rounded p-1 text-slate-600 hover:text-slate-400 hover:bg-white/[0.04] transition-colors"
          aria-label="Close"
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M2.5 2.5L9.5 9.5M9.5 2.5L2.5 9.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </button>
      </div>
    </div>
  );
}

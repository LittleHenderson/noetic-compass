import { useState, type ReactNode } from 'react';

interface DisclosureProps {
  summary: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
  className?: string;
}

/**
 * Inline collapsible used to tuck explanatory wordiness behind a one-line
 * summary. Keeps the default view uncluttered while leaving detail one tap away.
 */
export function Disclosure({ summary, children, defaultOpen = false, className = '' }: DisclosureProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className={`rounded-lg border border-white/[0.08] bg-white/[0.02] ${className}`.trim()}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left min-h-[40px]"
      >
        <span className="text-[11px] font-medium text-slate-300">{summary}</span>
        <svg
          width="12" height="12" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5"
          className={`flex-shrink-0 text-slate-500 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
        >
          <path d="M3 5l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {open && (
        <div className="animate-slide-down border-t border-white/[0.04] px-3 pb-3 pt-2 text-[11px] leading-relaxed text-slate-500 space-y-2">
          {children}
        </div>
      )}
    </div>
  );
}

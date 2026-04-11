import { useState } from 'react';

interface HowItWorksSection {
  title: string;
  body: React.ReactNode;
}

interface HowItWorksPanelProps {
  sections: HowItWorksSection[];
  label?: string;
  defaultOpen?: boolean;
}

/**
 * Reusable expandable "How This Works" panel.
 * Use at the top of a page to explain how it works without cluttering the UI.
 */
export function HowItWorksPanel({ sections, label = 'How This Works', defaultOpen = false }: HowItWorksPanelProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="glass-card overflow-hidden" style={{ borderColor: open ? 'rgba(45, 212, 191, 0.2)' : undefined }}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between gap-3 px-5 py-3 text-left min-h-[44px]"
      >
        <div className="flex items-center gap-2">
          <span className="text-[14px]">ℹ️</span>
          <span className="text-[12px] font-semibold text-slate-200">{label}</span>
        </div>
        <svg
          width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5"
          className={`text-slate-500 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
        >
          <path d="M3 5l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {open && (
        <div className="px-5 pb-5 pt-1 space-y-4 border-t border-white/[0.04] animate-slide-down">
          {sections.map((section, i) => (
            <div key={i}>
              <h4 className="text-[10px] font-semibold uppercase tracking-wider text-accent-teal mb-2">
                {section.title}
              </h4>
              <div className="text-[12px] text-slate-300 leading-relaxed">
                {section.body}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

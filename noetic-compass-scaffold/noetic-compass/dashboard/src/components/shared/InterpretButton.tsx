import { useState, type ReactNode } from 'react';

interface InterpretButtonProps {
  interpretation: string | ReactNode;
}

export function InterpretButton({ interpretation }: InterpretButtonProps) {
  const [open, setOpen] = useState(false);

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className={`interpret-glow inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[10px] font-medium transition-all duration-200 ${
          open
            ? 'bg-accent-teal/20 text-accent-teal'
            : 'bg-white/[0.04] text-slate-500 hover:text-accent-teal hover:bg-accent-teal/10'
        }`}
      >
        <span className="text-[11px]">&#10022;</span>
        {open ? 'Hide' : 'Interpret'}
      </button>

      {open && (
        <div className="mt-3 rounded-lg border border-accent-teal/15 bg-accent-teal/[0.03] p-4 animate-slide-down">
          <div className="text-[12px] text-slate-300 leading-relaxed">
            {interpretation}
          </div>
        </div>
      )}
    </div>
  );
}

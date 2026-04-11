import { useState } from 'react';
import type { LLMResponse } from '../../api/types';

interface AiResponsePanelProps {
  llmResponse: LLMResponse | null | undefined;
}

/**
 * Collapsible panel that shows the actual AI response text that was assessed.
 * Default collapsed — users click to expand and read what the AI said.
 */
export function AiResponsePanel({ llmResponse }: AiResponsePanelProps) {
  const [open, setOpen] = useState(false);

  if (!llmResponse || !llmResponse.text) return null;

  const model = llmResponse.model || 'unknown model';
  const charCount = llmResponse.text.length;

  return (
    <div className="glass-card overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between gap-3 px-5 py-3 text-left min-h-[44px]"
      >
        <div className="flex items-center gap-2">
          <span className="text-[14px]">💬</span>
          <span className="text-[12px] font-semibold text-slate-200">
            {open ? 'Hide' : 'Show'} AI Response
          </span>
          <span className="text-[10px] text-slate-500">
            from <span className="text-accent-teal">{model}</span>
            <span className="mx-1.5 text-slate-600">·</span>
            {charCount.toLocaleString()} chars
          </span>
        </div>
        <svg
          width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5"
          className={`text-slate-500 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
        >
          <path d="M3 5l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {open && (
        <div className="border-t border-white/[0.04] animate-slide-down">
          <div className="px-5 py-4 max-h-[50vh] overflow-y-auto scroll-glow">
            <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-2">
              Response from {model}
            </p>
            <pre className="whitespace-pre-wrap text-[12px] leading-relaxed text-slate-200 font-sans">
              {llmResponse.text}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

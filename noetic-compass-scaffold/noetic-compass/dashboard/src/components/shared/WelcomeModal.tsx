import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const STORAGE_KEY = 'nc-welcome-dismissed';

export function WelcomeModal() {
  const [show, setShow] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const dismissed = localStorage.getItem(STORAGE_KEY);
    if (!dismissed) {
      setShow(true);
    }
  }, []);

  function dismiss() {
    localStorage.setItem(STORAGE_KEY, '1');
    setShow(false);
  }

  function startAssessment() {
    dismiss();
    navigate('/assessment', {
      state: {
        prefill: 'A hospital has one ventilator and two patients — a 30-year-old parent of three and a 70-year-old retired scientist who pioneered the treatment being used. How should the doctor decide?',
      },
    });
  }

  if (!show) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-lg rounded-2xl border border-white/[0.08] bg-dark-800 p-6 shadow-2xl">
        {/* Close */}
        <button
          onClick={dismiss}
          className="absolute top-4 right-4 text-slate-500 hover:text-slate-300 transition-colors"
          aria-label="Close"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M5 5l10 10M15 5L5 15" strokeLinecap="round" />
          </svg>
        </button>

        {/* Header */}
        <div className="text-center mb-6">
          <h2 className="text-2xl font-bold text-slate-100">Welcome to Noetic Compass</h2>
          <p className="text-sm text-slate-400 mt-2">
            This platform measures <span className="text-accent-teal font-medium">HOW</span> AI thinks — not just what it says.
          </p>
        </div>

        {/* Three things to try */}
        <div className="space-y-4 mb-6">
          <div className="flex items-start gap-3 rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
            <span className="shrink-0 w-7 h-7 rounded-full bg-accent-teal/15 text-accent-teal flex items-center justify-center text-sm font-bold">1</span>
            <div>
              <p className="text-sm font-semibold text-slate-200">Run an Assessment</p>
              <p className="text-xs text-slate-400 mt-0.5">Score any AI on an ethical dilemma and see its cognitive architecture</p>
            </div>
          </div>

          <div className="flex items-start gap-3 rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
            <span className="shrink-0 w-7 h-7 rounded-full bg-purple-500/15 text-purple-400 flex items-center justify-center text-sm font-bold">2</span>
            <div>
              <p className="text-sm font-semibold text-slate-200">Try the Compiler</p>
              <p className="text-xs text-slate-400 mt-0.5">Type CAS expressions or plain English and watch cognitive structure emerge</p>
            </div>
          </div>

          <div className="flex items-start gap-3 rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
            <span className="shrink-0 w-7 h-7 rounded-full bg-amber-500/15 text-amber-400 flex items-center justify-center text-sm font-bold">3</span>
            <div>
              <p className="text-sm font-semibold text-slate-200">Compare Models</p>
              <p className="text-xs text-slate-400 mt-0.5">Run the same prompt against multiple AI providers and see the differences</p>
            </div>
          </div>
        </div>

        {/* CTA */}
        <button
          onClick={startAssessment}
          className="w-full rounded-lg bg-gradient-to-r from-accent-teal to-accent-cyan px-4 py-3 text-sm font-semibold text-dark-900 hover:opacity-90 transition-opacity min-h-[44px]"
        >
          Start with an Assessment
        </button>

        <button
          onClick={dismiss}
          className="w-full mt-2 rounded-lg border border-white/[0.08] bg-white/[0.04] px-4 py-2.5 text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-white/[0.08] transition-colors min-h-[44px]"
        >
          I'll explore on my own
        </button>
      </div>
    </div>
  );
}

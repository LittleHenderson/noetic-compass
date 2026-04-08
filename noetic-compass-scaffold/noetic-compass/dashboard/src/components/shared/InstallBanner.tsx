import { usePwaInstall } from '../../hooks/usePwaInstall';

export function InstallBanner() {
  const { showBanner, install, dismiss } = usePwaInstall();

  if (!showBanner) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 safe-bottom">
      <div className="mx-4 mb-4 flex items-center gap-3 rounded-xl border border-accent-teal/20 bg-dark-800/95 backdrop-blur-md px-4 py-3 shadow-lg shadow-accent-teal/5 md:mx-auto md:max-w-md">
        <img src="/icon-192.svg" alt="" className="h-10 w-10 shrink-0 rounded-lg" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-slate-200">Install Noetic Compass</p>
          <p className="text-xs text-slate-400">Add to home screen for quick access</p>
        </div>
        <button
          onClick={install}
          className="shrink-0 rounded-lg bg-gradient-to-r from-accent-teal to-accent-cyan px-4 py-2 text-xs font-semibold text-dark-900 min-h-[44px] active:opacity-80 transition-opacity"
        >
          Install
        </button>
        <button
          onClick={dismiss}
          className="shrink-0 flex items-center justify-center w-8 h-8 min-h-[44px] min-w-[44px] rounded-lg text-slate-500 hover:text-slate-300 active:bg-white/[0.06] transition-colors"
          aria-label="Dismiss"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M2 2l10 10M12 2L2 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}

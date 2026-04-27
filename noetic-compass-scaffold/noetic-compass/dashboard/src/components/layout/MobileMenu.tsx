import { useEffect } from 'react';
import { NavItems } from './Sidebar';

interface MobileMenuProps {
  open: boolean;
  onClose: () => void;
}

/**
 * Slide-in drawer used as the mobile alternative to the desktop Sidebar.
 *
 * Wraps the same NavItems list as Sidebar so navigation stays consistent
 * across viewports. Backdrop dimmer + tap-to-close + Escape-key close.
 *
 * AppShell currently renders <Sidebar> for both desktop and mobile (the
 * sidebar itself collapses below md). This component is exported for any
 * page that wants a richer mobile drawer or for future shell consolidation;
 * it can stand alone wherever a drawer is desired.
 */
export function MobileMenu({ open, onClose }: MobileMenuProps) {
  // Escape-to-close.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  // Lock body scroll while open.
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 z-40 bg-slate-950/70 backdrop-blur-sm transition-opacity duration-200 md:hidden ${
          open ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 transform bg-dark-800/95 backdrop-blur-xl border-r border-white/[0.06] p-4 pt-5 transition-transform duration-200 ease-out md:hidden ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
        role="dialog"
        aria-modal="true"
        aria-label="Navigation menu"
      >
        <div className="mb-4 flex items-center justify-between px-2">
          <span className="text-sm font-semibold text-slate-200">Menu</span>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close menu"
            className="flex items-center justify-center w-9 h-9 min-h-[44px] min-w-[44px] -mr-1 rounded-lg text-slate-400 hover:text-slate-200 active:bg-white/[0.06] transition-colors"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M4 4l10 10M14 4L4 14" />
            </svg>
          </button>
        </div>

        <NavItems onNavigate={onClose} />
      </aside>
    </>
  );
}

export default MobileMenu;

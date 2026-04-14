import { isAuthenticated, clearToken } from '../../api/auth';
import { useNavigate, useLocation } from 'react-router-dom';
import { BrandTagline } from '../shared/BrandTagline';
import { PatentPendingBadge } from '../shared/PatentPendingBadge';

interface HeaderProps {
  onMenuToggle?: () => void;
  sidebarOpen?: boolean;
}

export function Header({ onMenuToggle, sidebarOpen }: HeaderProps) {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const authed = isAuthenticated();

  // Back button shows on every page except the home pages.
  const isHome = pathname === '/scenarios' || pathname === '/' || pathname === '/login';
  const showBack = !isHome;

  function handleLogout() {
    clearToken();
    navigate('/login');
  }

  return (
    <header className="flex min-h-[4.5rem] items-center justify-between border-b border-white/[0.06] bg-dark-800/80 px-3 py-2 backdrop-blur-md sm:px-5 safe-top">
      <div className="flex items-center gap-2.5">
        {/* Hamburger menu — mobile only */}
        {onMenuToggle && (
          <button
            onClick={onMenuToggle}
            className="flex items-center justify-center w-9 h-9 min-h-[44px] min-w-[44px] -ml-1 rounded-lg text-slate-400 hover:text-slate-200 active:bg-white/[0.06] transition-colors md:hidden"
            aria-label={sidebarOpen ? 'Close menu' : 'Open menu'}
          >
            {sidebarOpen ? (
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M4 4l10 10M14 4L4 14" />
              </svg>
            ) : (
              <svg width="18" height="18" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M3 5h14a1 1 0 010 2H3a1 1 0 010-2zm0 4h14a1 1 0 010 2H3a1 1 0 010-2zm0 4h14a1 1 0 010 2H3a1 1 0 010-2z" />
              </svg>
            )}
          </button>
        )}
        {/* Glowing back button — burgundy, visible on every page except home */}
        {showBack ? (
          <button
            onClick={() => navigate(-1)}
            className="group relative flex items-center justify-center w-10 h-10 min-h-[44px] min-w-[44px] rounded-xl border transition-all active:scale-90"
            style={{
              backgroundColor: 'rgba(155, 44, 44, 0.2)',
              borderColor: 'rgba(185, 55, 55, 0.4)',
              color: '#e88a8a',
              boxShadow: '0 0 14px rgba(155, 44, 44, 0.3)',
            }}
            aria-label="Go back"
            title="Go back"
          >
            <span className="absolute inset-0 rounded-xl animate-pulse" style={{ backgroundColor: 'rgba(155, 44, 44, 0.12)', filter: 'blur(10px)' }} />
            <svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="relative z-10">
              <path d="M10 12L6 8l4-4" />
            </svg>
          </button>
        ) : null}
        <img src="/icon-192.svg" alt="" className="h-7 w-7 rounded-lg" />
        <div className="flex flex-col leading-tight">
          <h1 className="text-base font-bold tracking-tight">
            <span className="bg-gradient-to-r from-accent-teal to-accent-cyan bg-clip-text text-transparent">
              Noetic Compass
            </span>
          </h1>
          <div className="hidden sm:block -mt-0.5">
            <BrandTagline variant="header" />
          </div>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <PatentPendingBadge compact className="shrink-0" />
        {authed ? (
          <button
            onClick={handleLogout}
            className="rounded-md border border-white/[0.08] bg-white/[0.04] px-3 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-white/[0.08] transition-colors min-h-[44px]"
          >
            Logout
          </button>
        ) : (
          <span className="text-xs text-slate-600">Not connected</span>
        )}
      </div>
    </header>
  );
}

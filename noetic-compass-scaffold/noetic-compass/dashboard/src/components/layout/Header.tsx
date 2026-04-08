import { isAuthenticated, clearToken } from '../../api/auth';
import { useNavigate } from 'react-router-dom';

interface HeaderProps {
  onMenuToggle?: () => void;
  sidebarOpen?: boolean;
}

export function Header({ onMenuToggle, sidebarOpen }: HeaderProps) {
  const navigate = useNavigate();
  const authed = isAuthenticated();

  function handleLogout() {
    clearToken();
    navigate('/login');
  }

  return (
    <header className="flex h-14 items-center justify-between border-b border-white/[0.06] bg-dark-800/80 backdrop-blur-md px-3 sm:px-5 safe-top">
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
        <img src="/icon-192.svg" alt="" className="h-7 w-7 rounded-lg" />
        <h1 className="text-base font-bold tracking-tight">
          <span className="bg-gradient-to-r from-accent-teal to-accent-cyan bg-clip-text text-transparent">
            Noetic Compass
          </span>
        </h1>
      </div>
      <div className="flex items-center gap-3">
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

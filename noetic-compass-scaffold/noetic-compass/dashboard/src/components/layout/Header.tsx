import { isAuthenticated, clearToken } from '../../api/auth';
import { useNavigate } from 'react-router-dom';

export function Header() {
  const navigate = useNavigate();
  const authed = isAuthenticated();

  function handleLogout() {
    clearToken();
    navigate('/login');
  }

  return (
    <header className="flex h-14 items-center justify-between border-b border-white/[0.06] bg-dark-800/80 backdrop-blur-md px-5">
      <div className="flex items-center gap-2.5">
        <div className="h-7 w-7 rounded-lg bg-gradient-to-br from-accent-teal to-accent-cyan flex items-center justify-center">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#0a0f1a" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20M2 12h20" />
          </svg>
        </div>
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
            className="rounded-md border border-white/[0.08] bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-white/[0.08] transition-colors"
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

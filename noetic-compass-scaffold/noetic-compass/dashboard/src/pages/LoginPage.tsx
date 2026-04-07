import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { setToken } from '../api/auth';

export function LoginPage() {
  const [jwt, setJwt] = useState('');
  const navigate = useNavigate();

  function handleConnect() {
    if (!jwt.trim()) return;
    setToken(jwt.trim());
    navigate('/');
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-dark-900">
      {/* Background glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 rounded-full bg-accent-teal/5 blur-[120px] pointer-events-none" />

      <div className="relative glass-card w-full max-w-md p-8">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-accent-teal to-accent-cyan flex items-center justify-center mb-4">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#0a0f1a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20M2 12h20" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold">
            <span className="bg-gradient-to-r from-accent-teal to-accent-cyan bg-clip-text text-transparent">
              Noetic Compass
            </span>
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            Enter your JWT token to connect to the API.
          </p>
        </div>

        <div className="space-y-4">
          <input
            type="text"
            value={jwt}
            onChange={(e) => setJwt(e.target.value)}
            placeholder="Paste JWT token here..."
            className="w-full rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:border-accent-teal/50 focus:outline-none focus:ring-1 focus:ring-accent-teal/30"
            onKeyDown={(e) => e.key === 'Enter' && handleConnect()}
          />
          <button
            onClick={handleConnect}
            disabled={!jwt.trim()}
            className="w-full rounded-lg bg-gradient-to-r from-accent-teal to-accent-cyan px-4 py-3 text-sm font-semibold text-dark-900 hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-opacity"
          >
            Connect
          </button>
        </div>
      </div>
    </div>
  );
}

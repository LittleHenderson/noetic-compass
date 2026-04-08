import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { setToken } from '../api/auth';
import { API_BASE } from '../api/config';

export function LoginPage() {
  const [username, setUsername] = useState('dashboard-user');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleConnect() {
    const name = username.trim();
    if (!name) return;
    setError('');
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/auth/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: name }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(body.detail ?? 'Failed to get token');
      }

      const data: { token: string } = await res.json();
      setToken(data.token);
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connection failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen min-h-[100dvh] items-center justify-center bg-dark-900 px-4">
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
            Enter a username to connect to the API.
          </p>
        </div>

        <div className="space-y-4">
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Username"
            className="w-full rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:border-accent-teal/50 focus:outline-none focus:ring-1 focus:ring-accent-teal/30"
            onKeyDown={(e) => e.key === 'Enter' && handleConnect()}
          />

          {error && (
            <p className="text-xs text-red-400">{error}</p>
          )}

          <button
            onClick={handleConnect}
            disabled={!username.trim() || loading}
            className="w-full rounded-lg bg-gradient-to-r from-accent-teal to-accent-cyan px-4 py-3 text-sm font-semibold text-dark-900 hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-opacity"
          >
            {loading ? 'Connecting...' : 'Connect'}
          </button>
        </div>
      </div>
    </div>
  );
}

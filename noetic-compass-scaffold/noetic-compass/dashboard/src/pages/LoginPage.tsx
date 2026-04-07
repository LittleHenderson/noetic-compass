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
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="w-full max-w-md rounded-lg border border-gray-200 bg-white p-8 shadow-sm">
        <h1 className="mb-6 text-2xl font-bold text-indigo-700 text-center">Noetic Compass</h1>
        <p className="mb-4 text-sm text-gray-500 text-center">
          Enter your JWT token to connect to the API.
        </p>
        <div className="space-y-4">
          <input
            type="text"
            value={jwt}
            onChange={(e) => setJwt(e.target.value)}
            placeholder="Paste JWT token here..."
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            onKeyDown={(e) => e.key === 'Enter' && handleConnect()}
          />
          <button
            onClick={handleConnect}
            disabled={!jwt.trim()}
            className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Connect
          </button>
        </div>
      </div>
    </div>
  );
}

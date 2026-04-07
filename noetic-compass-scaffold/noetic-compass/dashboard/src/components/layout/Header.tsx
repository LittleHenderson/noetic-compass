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
    <header className="flex h-14 items-center justify-between border-b border-gray-200 bg-white px-4">
      <h1 className="text-lg font-bold text-indigo-700 tracking-tight">Noetic Compass</h1>
      <div className="flex items-center gap-3">
        {authed ? (
          <button
            onClick={handleLogout}
            className="rounded-md bg-gray-100 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-200"
          >
            Logout
          </button>
        ) : (
          <span className="text-xs text-gray-400">Not connected</span>
        )}
      </div>
    </header>
  );
}

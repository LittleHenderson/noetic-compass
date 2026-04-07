import { NavLink } from 'react-router-dom';
import { useHealth } from '../../hooks/useHealth';

const NAV_ITEMS = [
  { to: '/', label: 'Assessment' },
  { to: '/history', label: 'History' },
  { to: '/config', label: 'Config' },
];

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const health = useHealth();
  const isHealthy = health.data?.status === 'ok';

  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div className="fixed inset-0 z-30 bg-black/30 md:hidden" onClick={onClose} />
      )}

      <aside
        className={`
          fixed z-40 top-0 left-0 h-full w-60 bg-gray-50 border-r border-gray-200 p-4
          transform transition-transform md:relative md:translate-x-0
          ${open ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        <div className="mb-6 flex items-center gap-2">
          <div
            className={`h-2.5 w-2.5 rounded-full ${isHealthy ? 'bg-green-500' : 'bg-red-500'}`}
            title={isHealthy ? 'API healthy' : 'API unreachable'}
          />
          <span className="text-xs text-gray-500">
            {isHealthy ? 'Connected' : 'Disconnected'}
          </span>
        </div>

        <nav className="flex flex-col gap-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onClose}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 text-sm font-medium ${
                  isActive
                    ? 'bg-indigo-100 text-indigo-700'
                    : 'text-gray-600 hover:bg-gray-100'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
    </>
  );
}

import { NavLink } from 'react-router-dom';
import { useHealth } from '../../hooks/useHealth';

const NAV_ITEMS = [
  { to: '/', label: 'Assessment', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2' },
  { to: '/history', label: 'History', icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z' },
  { to: '/config', label: 'Config', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z' },
];

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const health = useHealth();
  const isHealthy = health.data?.status === 'ok';

  return (
    <>
      {open && (
        <div className="fixed inset-0 z-30 bg-black/50 backdrop-blur-sm md:hidden" onClick={onClose} />
      )}

      <aside
        className={`
          fixed z-40 top-0 left-0 h-full w-56 bg-dark-800/95 backdrop-blur-xl border-r border-white/[0.06] p-4 pt-5
          transform transition-transform duration-200 md:relative md:translate-x-0
          ${open ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        <div className="mb-8 flex items-center gap-2.5 px-2">
          <div className="relative">
            <div
              className={`h-2 w-2 rounded-full ${isHealthy ? 'bg-emerald-400' : 'bg-red-400'}`}
            />
            {isHealthy && (
              <div className="absolute inset-0 h-2 w-2 rounded-full bg-emerald-400 animate-ping opacity-30" />
            )}
          </div>
          <span className={`text-xs font-medium ${isHealthy ? 'text-emerald-400' : 'text-red-400'}`}>
            {isHealthy ? 'API Connected' : 'Disconnected'}
          </span>
        </div>

        <nav className="flex flex-col gap-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-accent-teal/10 text-accent-teal'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
                }`
              }
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d={item.icon} />
              </svg>
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
    </>
  );
}

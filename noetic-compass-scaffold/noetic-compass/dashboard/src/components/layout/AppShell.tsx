import { useState, type ReactNode } from 'react';
import { Header } from './Header';
import { Sidebar } from './Sidebar';

export function AppShell({ children }: { children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen flex-col bg-dark-900">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <button
          className="fixed bottom-4 left-4 z-50 rounded-full bg-gradient-to-br from-accent-teal to-accent-cyan p-3 text-dark-900 shadow-lg shadow-accent-teal/20 md:hidden"
          onClick={() => setSidebarOpen((o) => !o)}
          aria-label="Toggle menu"
        >
          <svg width="18" height="18" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M3 5h14a1 1 0 010 2H3a1 1 0 010-2zm0 4h14a1 1 0 010 2H3a1 1 0 010-2zm0 4h14a1 1 0 010 2H3a1 1 0 010-2z" />
          </svg>
        </button>

        <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

        <main className="flex-1 overflow-y-auto bg-dark-900 p-4 md:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}

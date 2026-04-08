import { useState, type ReactNode } from 'react';
import { Header } from './Header';
import { Sidebar } from './Sidebar';

export function AppShell({ children }: { children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen h-[100dvh] flex-col bg-dark-900">
      <Header onMenuToggle={() => setSidebarOpen((o) => !o)} sidebarOpen={sidebarOpen} />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

        <main className="flex-1 overflow-y-auto bg-dark-900 p-3 pb-6 sm:p-4 md:p-6 -webkit-overflow-scrolling-touch">
          {children}
        </main>
      </div>
    </div>
  );
}

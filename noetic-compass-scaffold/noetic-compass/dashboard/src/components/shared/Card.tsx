import type { ReactNode } from 'react';

export function Card({
  title,
  children,
  className = '',
}: {
  title?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`glass-card p-5 animate-chart-in ${className}`}>
      {title && (
        <h3 className="mb-4 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400">
          {title}
        </h3>
      )}
      {children}
    </div>
  );
}

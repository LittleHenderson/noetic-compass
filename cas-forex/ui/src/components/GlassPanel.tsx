/* ── CAS Forex — Reusable Glass Panel ── */

import type { CSSProperties, ReactNode } from "react";

interface GlassPanelProps {
  title?: string;
  subtitle?: string;
  children: ReactNode;
  variant?: "default" | "warning" | "danger" | "info";
  className?: string;
  style?: CSSProperties;
}

export function GlassPanel({
  title,
  subtitle,
  children,
  variant = "default",
  className = "",
}: GlassPanelProps) {
  const borderColor = {
    default: "var(--border-subtle)",
    warning: "var(--warning-dim)",
    danger: "var(--danger-dim)",
    info: "var(--accent-teal-dim)",
  }[variant];

  return (
    <div
      className={`glass-panel ${className}`}
      style={{ borderColor, borderTopColor: borderColor }}
    >
      {(title || subtitle) && (
        <div className="glass-panel-header">
          {title && <h3 className="glass-panel-title">{title}</h3>}
          {subtitle && <span className="glass-panel-sub">{subtitle}</span>}
        </div>
      )}
      <div className="glass-panel-body">{children}</div>
    </div>
  );
}

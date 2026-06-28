/* ── CAS Forex — App Shell ── */

import { useState, type ReactNode } from "react";
import { ModeBanner } from "./ModeBanner";
import type { UIReadinessReport, AuthorityBoundaryState } from "../types/evidence";

type Page =
  | "quick-start"
  | "proof"
  | "audit"
  | "dashboard"
  | "trade"
  | "adaptive"
  | "history"
  | "settings"
  | "pcba"
  | "ledger"
  | "optimizer"
  | "condition-lab"
  | "decision-history"
  | "forex-fury"
  | "strategy-dev"
  | "stack-status"
  | "strategy-comparison"
  | "daily-report"
  | "windows";

interface ShellProps {
  readiness: UIReadinessReport;
  authority?: AuthorityBoundaryState;
  activePage: Page;
  onNavigate: (page: Page) => void;
  children: ReactNode;
}

const NAV_ITEMS: { id: Page; label: string; ready: boolean }[] = [
  { id: "quick-start", label: "Quick Start", ready: true },
  { id: "proof", label: "Proof", ready: true },
  { id: "audit", label: "Audit", ready: true },
  { id: "dashboard", label: "Dashboard", ready: true },
  { id: "trade", label: "Trade", ready: true },
  { id: "windows", label: "Live Charts", ready: true },
  { id: "adaptive", label: "Adaptive", ready: true },
  { id: "history", label: "History", ready: true },
  { id: "settings", label: "Settings", ready: true },
  { id: "pcba", label: "PCBA/CJT", ready: true },
  { id: "ledger", label: "Ledger", ready: true },
  { id: "optimizer", label: "Optimizer", ready: true },
  { id: "condition-lab", label: "Cond. Lab", ready: true },
  { id: "decision-history", label: "Decisions", ready: true },
  { id: "forex-fury", label: "Fury", ready: true },
  { id: "strategy-dev", label: "Strategy", ready: true },
  { id: "stack-status", label: "Stack", ready: true },
  { id: "strategy-comparison", label: "Compare", ready: true },
  { id: "daily-report", label: "Daily", ready: true },
];

export function Shell({
  readiness,
  authority,
  activePage,
  onNavigate,
  children,
}: ShellProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const activeLabel = NAV_ITEMS.find((i) => i.id === activePage)?.label ?? "Menu";

  return (
    <div className="app-shell">
      <ModeBanner readiness={readiness} authority={authority} />
      <nav className="shell-nav">
        <div className="shell-nav-brand">
          <span className="shell-nav-logo">◈</span>
          <span className="shell-nav-title">CAS Forex</span>
          <span className="shell-nav-sub">Proof Cockpit</span>
        </div>
        {/* Hamburger — only shown on narrow screens (CSS). Lets every page,
            including Settings, be reached on a phone. */}
        <button
          className="shell-nav-toggle"
          aria-label="Toggle navigation menu"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((v) => !v)}
        >
          <span className="shell-nav-toggle-icon">{menuOpen ? "✕" : "☰"}</span>
          <span className="shell-nav-toggle-label">{activeLabel}</span>
        </button>
        <div className={`shell-nav-links ${menuOpen ? "open" : ""}`}>
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              className={`shell-nav-link ${
                activePage === item.id ? "active" : ""
              } ${!item.ready ? "disabled" : ""}`}
              onClick={() => {
                if (!item.ready) return;
                onNavigate(item.id);
                setMenuOpen(false);
              }}
              disabled={!item.ready}
              title={!item.ready ? "Coming soon" : undefined}
            >
              {item.label}
              {!item.ready && (
                <span className="shell-nav-badge">soon</span>
              )}
            </button>
          ))}
        </div>
      </nav>
      <main className="shell-main">{children}</main>
    </div>
  );
}

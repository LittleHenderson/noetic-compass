export const NAV_ITEMS = [
  { id: "quick-start", label: "Quick Start", ready: true },
  { id: "proof", label: "Proof", ready: true },
  { id: "audit", label: "Audit", ready: true },
  { id: "dashboard", label: "Dashboard", ready: true },
  { id: "tracker", label: "Tracker", ready: true },
  { id: "trade", label: "Trade", ready: true },
  { id: "windows", label: "Live Charts", ready: true },
  { id: "adaptive", label: "Adaptive", ready: true },
  { id: "history", label: "History", ready: true },
  { id: "risk", label: "Risk", ready: true },
  { id: "terms", label: "Terms", ready: true },
  { id: "privacy", label: "Privacy", ready: true },
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
] as const;

export type Page = (typeof NAV_ITEMS)[number]["id"];

export function isPage(value: string | null): value is Page {
  return NAV_ITEMS.some((item) => item.id === value);
}

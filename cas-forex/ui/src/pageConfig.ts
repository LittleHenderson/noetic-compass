/* ── Page registry and navigation information architecture ──
 *
 * Every page keeps its id (the `?page=` value): pairing links, the service
 * worker denylist, and Capacitor deep links all encode these ids, so the URL
 * scheme is a compatibility contract. What changed is the PRESENTATION: 23
 * flat destinations became 7 groups plus a legal footer, and history is now
 * pushState-based so back/forward work.
 */

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

/* ── Grouped IA ──
 * Seven top-level destinations; each group's pages render as a secondary tab
 * row. Legal pages live in the footer, not the nav. Every non-legal page MUST
 * appear in exactly one group — tests/test_nav_information_architecture.py
 * enforces the partition, so a new page cannot silently become unreachable. */

export interface NavGroup {
  id: string;
  label: string;
  /** First page is the group's landing page. */
  pages: readonly { id: Page; label: string }[];
}

export const NAV_GROUPS: readonly NavGroup[] = [
  {
    id: "cockpit",
    label: "Cockpit",
    pages: [
      { id: "dashboard", label: "Dashboard" },
      { id: "quick-start", label: "Quick Start" },
    ],
  },
  {
    id: "trade",
    label: "Trade",
    pages: [
      { id: "trade", label: "Trade" },
      { id: "windows", label: "Live Charts" },
    ],
  },
  {
    id: "account",
    label: "Account",
    pages: [
      { id: "tracker", label: "Tracker" },
      { id: "ledger", label: "Ledger" },
      { id: "history", label: "History" },
      { id: "daily-report", label: "Daily Report" },
    ],
  },
  {
    id: "decisions",
    label: "Decisions",
    pages: [
      { id: "decision-history", label: "Decision History" },
      { id: "adaptive", label: "Adaptive" },
    ],
  },
  {
    id: "research",
    label: "Research",
    pages: [
      { id: "optimizer", label: "Optimizer" },
      { id: "strategy-dev", label: "Strategy Dev" },
      { id: "strategy-comparison", label: "Compare" },
      { id: "condition-lab", label: "Condition Lab" },
      { id: "forex-fury", label: "Fury" },
    ],
  },
  {
    id: "evidence",
    label: "Evidence",
    pages: [
      { id: "proof", label: "Proof" },
      { id: "audit", label: "Audit" },
      { id: "stack-status", label: "Stack Status" },
      { id: "pcba", label: "PCBA/CJT" },
    ],
  },
  {
    id: "settings",
    label: "Settings",
    pages: [{ id: "settings", label: "Settings" }],
  },
] as const;

/** Legal / disclosure pages: reachable from the footer on every page. */
export const FOOTER_PAGES: readonly { id: Page; label: string }[] = [
  { id: "risk", label: "Risk Disclosure" },
  { id: "terms", label: "Terms" },
  { id: "privacy", label: "Privacy" },
] as const;

export function groupForPage(page: Page): NavGroup | null {
  return NAV_GROUPS.find((group) => group.pages.some((p) => p.id === page)) ?? null;
}

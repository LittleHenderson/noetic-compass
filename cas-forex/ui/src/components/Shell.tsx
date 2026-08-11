/* ── CAS Forex — App Shell ──
 *
 * Grouped navigation: 7 top-level destinations, a secondary tab row for the
 * active group's pages, and legal pages in the footer. This replaced a flat
 * row of 23 buttons plus ~90 lines of overflow-measurement math and a
 * "your browser is zoomed" advisory banner — the old nav needed an apology
 * because it never fit; the grouped nav fits, so the apology is gone.
 */

import { lazy, Suspense, useEffect, useState, type ReactNode } from "react";
import { ModeBanner } from "./ModeBanner";
import { AiActivityInstantBadge } from "./AiActivityInstantBadge";
import { OperatorBadge } from "./OperatorBadge";
import { OwnerAccessBadge } from "./OwnerAccessBadge";
import { GlobalHaltButton } from "./GlobalHaltButton";
import { FOOTER_PAGES, NAV_GROUPS, groupForPage, type Page } from "../pageConfig";
import type { UIReadinessReport, AuthorityBoundaryState, DashboardMeta } from "../types/evidence";

interface ShellProps {
  readiness: UIReadinessReport;
  authority?: AuthorityBoundaryState;
  wasteLoop?: Record<string, unknown> | null;
  dashboardMeta?: DashboardMeta;
  activePage: Page;
  onNavigate: (page: Page) => void;
  children: ReactNode;
}

const AiActivityIndicator = lazy(() =>
  import("./AiActivityIndicator").then((module) => ({ default: module.AiActivityIndicator })),
);
const CriticalAlertStrip = lazy(() =>
  import("./CriticalAlertStrip").then((module) => ({ default: module.CriticalAlertStrip })),
);

const AI_ACTIVITY_FULL_INDICATOR_IDLE_TIMEOUT_MS = 1_400;

type IdleCallbackHandle = number;
type IdleSchedulerWindow = Window & {
  requestIdleCallback?: (callback: () => void, options?: { timeout?: number }) => IdleCallbackHandle;
  cancelIdleCallback?: (handle: IdleCallbackHandle) => void;
};

export function Shell({
  readiness,
  authority,
  wasteLoop,
  dashboardMeta,
  activePage,
  onNavigate,
  children,
}: ShellProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [fullActivityIndicatorMounted, setFullActivityIndicatorMounted] = useState(false);
  const activeGroup = groupForPage(activePage);
  const activeGroupLabel = activeGroup?.label
    ?? FOOTER_PAGES.find((p) => p.id === activePage)?.label
    ?? "Menu";

  useEffect(() => {
    const idleWindow = window as IdleSchedulerWindow;
    if (idleWindow.requestIdleCallback) {
      const id = idleWindow.requestIdleCallback(
        () => setFullActivityIndicatorMounted(true),
        { timeout: AI_ACTIVITY_FULL_INDICATOR_IDLE_TIMEOUT_MS },
      );
      return () => idleWindow.cancelIdleCallback?.(id);
    }

    const id = window.setTimeout(
      () => setFullActivityIndicatorMounted(true),
      AI_ACTIVITY_FULL_INDICATOR_IDLE_TIMEOUT_MS,
    );
    return () => window.clearTimeout(id);
  }, []);

  // The mobile drawer closes on Escape and on navigation.
  useEffect(() => {
    if (!menuOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuOpen]);

  const navigate = (page: Page) => {
    onNavigate(page);
    setMenuOpen(false);
  };

  return (
    <div className="app-shell">
      <ModeBanner readiness={readiness} authority={authority} dashboardMeta={dashboardMeta} />
      <nav className="shell-nav" aria-label="Primary">
        <div className="shell-nav-brand">
          <span className="shell-nav-logo" aria-hidden="true">◈</span>
          <span className="shell-nav-title">CAS Forex</span>
        </div>
        {fullActivityIndicatorMounted ? (
          <Suspense fallback={<AiActivityInstantBadge wasteLoop={wasteLoop} />}>
            <AiActivityIndicator wasteLoop={wasteLoop} />
          </Suspense>
        ) : (
          <AiActivityInstantBadge wasteLoop={wasteLoop} />
        )}
        <GlobalHaltButton />
        <OperatorBadge />
        <OwnerAccessBadge />
        <button
          className="shell-nav-toggle"
          aria-label="Toggle navigation menu"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((v) => !v)}
        >
          <span className="shell-nav-toggle-icon" aria-hidden="true">{menuOpen ? "✕" : "☰"}</span>
          <span className="shell-nav-toggle-label">{activeGroupLabel}</span>
        </button>
        <div className={`shell-nav-groups ${menuOpen ? "open" : ""}`} role="menubar">
          {NAV_GROUPS.map((group) => {
            const isActive = group.id === activeGroup?.id;
            return (
              <button
                key={group.id}
                className={`shell-nav-group ${isActive ? "active" : ""}`}
                aria-current={isActive ? "page" : undefined}
                onClick={() => navigate(group.pages[0].id)}
              >
                {group.label}
              </button>
            );
          })}
        </div>
      </nav>
      {activeGroup && activeGroup.pages.length > 1 && (
        <div className="shell-subnav" role="tablist" aria-label={`${activeGroup.label} pages`}>
          {activeGroup.pages.map((page) => (
            <button
              key={page.id}
              role="tab"
              aria-selected={page.id === activePage}
              className={`shell-subnav-link ${page.id === activePage ? "active" : ""}`}
              onClick={() => navigate(page.id)}
            >
              {page.label}
            </button>
          ))}
        </div>
      )}
      <Suspense fallback={null}>
        <CriticalAlertStrip onOpenAlerts={() => navigate("settings")} />
      </Suspense>
      <main className="shell-main">{children}</main>
      <footer className="shell-footer">
        <span className="shell-footer-note">CAS Forex — paper/demo proof cockpit</span>
        <span className="shell-footer-links">
          {FOOTER_PAGES.map((page) => (
            <button
              key={page.id}
              className={`shell-footer-link ${page.id === activePage ? "active" : ""}`}
              onClick={() => navigate(page.id)}
            >
              {page.label}
            </button>
          ))}
        </span>
      </footer>
    </div>
  );
}

/* ── CAS Forex — App Shell ── */

import { lazy, Suspense, useEffect, useState, type ReactNode } from "react";
import { ModeBanner } from "./ModeBanner";
import { AiActivityInstantBadge } from "./AiActivityInstantBadge";
import { OperatorBadge } from "./OperatorBadge";
import { OwnerAccessBadge } from "./OwnerAccessBadge";
import { NAV_ITEMS, type Page } from "../pageConfig";
import type { UIReadinessReport, AuthorityBoundaryState } from "../types/evidence";

interface ShellProps {
  readiness: UIReadinessReport;
  authority?: AuthorityBoundaryState;
  wasteLoop?: Record<string, unknown> | null;
  activePage: Page;
  onNavigate: (page: Page) => void;
  children: ReactNode;
}

const AiActivityIndicator = lazy(() =>
  import("./AiActivityIndicator").then((module) => ({ default: module.AiActivityIndicator })),
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
  activePage,
  onNavigate,
  children,
}: ShellProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [fullActivityIndicatorMounted, setFullActivityIndicatorMounted] = useState(false);
  const activeLabel = NAV_ITEMS.find((i) => i.id === activePage)?.label ?? "Menu";

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

  return (
    <div className="app-shell">
      <ModeBanner readiness={readiness} authority={authority} />
      <nav className="shell-nav">
        <div className="shell-nav-brand">
          <span className="shell-nav-logo">◈</span>
          <span className="shell-nav-title">CAS Forex</span>
          <span className="shell-nav-sub">Proof Cockpit</span>
        </div>
        {fullActivityIndicatorMounted ? (
          <Suspense fallback={<AiActivityInstantBadge wasteLoop={wasteLoop} />}>
            <AiActivityIndicator wasteLoop={wasteLoop} />
          </Suspense>
        ) : (
          <AiActivityInstantBadge wasteLoop={wasteLoop} />
        )}
        <OperatorBadge />
        <OwnerAccessBadge />
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

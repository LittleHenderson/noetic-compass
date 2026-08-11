/* ── CAS Forex — App Shell ── */

import { lazy, Suspense, useEffect, useRef, useState, type ReactNode } from "react";
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
  activePage,
  onNavigate,
  children,
}: ShellProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [navOverflowed, setNavOverflowed] = useState(false);
  const [fullActivityIndicatorMounted, setFullActivityIndicatorMounted] = useState(false);
  const [layoutAdvisoryDismissed, setLayoutAdvisoryDismissed] = useState(false);
  const [layoutAdvisory, setLayoutAdvisory] = useState<{
    label: string;
    detail: string;
  } | null>(null);
  const navRef = useRef<HTMLElement | null>(null);
  const linksRef = useRef<HTMLDivElement | null>(null);
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

  useEffect(() => {
    const nav = navRef.current;
    const links = linksRef.current;
    if (!nav || !links) return;

    let frame = 0;
    const measure = () => {
      window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(() => {
        const navStyle = window.getComputedStyle(nav);
        const linkStyle = window.getComputedStyle(links);
        const navGap = Number.parseFloat(navStyle.columnGap || navStyle.gap || "0") || 0;
        const linkGap = Number.parseFloat(linkStyle.columnGap || linkStyle.gap || "0") || 0;
        const fixedWidth = Array.from(nav.children).reduce((sum, child) => {
          if (child === links || child.classList.contains("shell-nav-toggle")) return sum;
          return sum + (child as HTMLElement).getBoundingClientRect().width;
        }, 0);
        const fixedChildCount = Array.from(nav.children).filter(
          (child) => child !== links && !child.classList.contains("shell-nav-toggle"),
        ).length;
        const linkChildren = Array.from(links.children) as HTMLElement[];
        const requiredLinkWidth = linkChildren.reduce(
          (sum, child) => sum + child.getBoundingClientRect().width,
          Math.max(0, linkChildren.length - 1) * linkGap,
        );
        const inlineAvailableWidth = Math.max(
          0,
          nav.clientWidth - fixedWidth - (fixedChildCount * navGap),
        );
        const viewportNeedsMenu = window.matchMedia("(max-width: 860px)").matches;
        const shouldCollapse = viewportNeedsMenu || requiredLinkWidth > inlineAvailableWidth + 2;
        setNavOverflowed(shouldCollapse);
        if (!shouldCollapse) setMenuOpen(false);
      });
    };

    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(nav);
    observer.observe(links);
    window.addEventListener("resize", measure);
    return () => {
      window.cancelAnimationFrame(frame);
      observer.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, []);

  useEffect(() => {
    function refreshLayoutAdvisory() {
      if (!navOverflowed) {
        setLayoutAdvisory(null);
        setLayoutAdvisoryDismissed(false);
        return;
      }
      const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0;
      const physicalWidth = Math.max(window.screen?.width || 0, window.screen?.availWidth || 0);
      const zoomScale = window.visualViewport?.scale ?? 1;
      const desktopLikeScreen = physicalWidth >= 1100;

      if (!desktopLikeScreen) {
        setLayoutAdvisory(null);
        setLayoutAdvisoryDismissed(false);
        return;
      }
      if (zoomScale > 1.08) {
        setLayoutAdvisory({
          label: `Browser zoom ${Math.round(zoomScale * 100)}%`,
          detail:
            "Header controls have switched into compact layout. If pages or dropdowns seem hidden, reset browser zoom to 100% or widen the window.",
        });
        return;
      }
      if (viewportWidth <= 980) {
        setLayoutAdvisory({
          label: `Compact width ${viewportWidth}px`,
          detail:
            "Header controls have switched into compact layout. If pages or dropdowns seem hidden, widen the window or reset browser zoom to 100%.",
        });
        return;
      }
      setLayoutAdvisory(null);
      setLayoutAdvisoryDismissed(false);
    }

    refreshLayoutAdvisory();
    window.addEventListener("resize", refreshLayoutAdvisory);
    const viewport = window.visualViewport;
    viewport?.addEventListener("resize", refreshLayoutAdvisory);
    return () => {
      window.removeEventListener("resize", refreshLayoutAdvisory);
      viewport?.removeEventListener("resize", refreshLayoutAdvisory);
    };
  }, [navOverflowed]);

  return (
    <div className="app-shell">
      <ModeBanner readiness={readiness} authority={authority} />
      <nav className={`shell-nav ${navOverflowed ? "overflowed" : ""}`} ref={navRef}>
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
        <div className={`shell-nav-links ${menuOpen ? "open" : ""}`} ref={linksRef}>
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
      {layoutAdvisory && !layoutAdvisoryDismissed ? (
        <div className="shell-layout-advisory" role="status" aria-live="polite">
          <div className="shell-layout-advisory-copy">
            <span className="shell-layout-advisory-label">{layoutAdvisory.label}</span>
            <span className="shell-layout-advisory-detail">{layoutAdvisory.detail}</span>
          </div>
          <button
            type="button"
            className="shell-layout-advisory-close"
            aria-label="Dismiss compact layout notice"
            onClick={() => setLayoutAdvisoryDismissed(true)}
          >
            Close
          </button>
        </div>
      ) : null}
      <Suspense fallback={null}>
        <CriticalAlertStrip onOpenAlerts={() => onNavigate("settings")} />
      </Suspense>
      <main className="shell-main">{children}</main>
    </div>
  );
}

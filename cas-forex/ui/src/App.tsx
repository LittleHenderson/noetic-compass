import {
  lazy,
  Suspense,
  useEffect,
  useMemo,
  useState,
  type ComponentType,
  type LazyExoticComponent,
} from "react";
import { Shell } from "./components/Shell";
import { DashboardInstantShell } from "./components/DashboardInstantShell";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { isPage, type Page } from "./pageConfig";
import type { DashboardState } from "./types/evidence";
import "./App.css";

type RoutedPage = ComponentType<{ state: DashboardState }>;

function lazyPage<T extends object>(
  load: () => Promise<T>,
  exportName: keyof T & string,
): LazyExoticComponent<RoutedPage> {
  return lazy(async () => {
    const module = await load();
    return { default: module[exportName] as RoutedPage };
  });
}

const PAGE_COMPONENTS: Record<Page, LazyExoticComponent<RoutedPage>> = {
  "quick-start": lazyPage(() => import("./pages/QuickStartPage"), "QuickStartPage"),
  proof: lazyPage(() => import("./pages/ProofPage"), "ProofPage"),
  audit: lazyPage(() => import("./pages/AuditPage"), "AuditPage"),
  dashboard: lazyPage(() => import("./pages/DashboardPage"), "DashboardPage"),
  trade: lazyPage(() => import("./pages/TradePage"), "TradePage"),
  adaptive: lazyPage(() => import("./pages/AdaptivePage"), "AdaptivePage"),
  history: lazyPage(() => import("./pages/HistoryPage"), "HistoryPage"),
  settings: lazyPage(() => import("./pages/SettingsPage"), "SettingsPage"),
  pcba: lazyPage(() => import("./pages/PcbaPage"), "PcbaPage"),
  ledger: lazyPage(() => import("./pages/LedgerPage"), "LedgerPage"),
  optimizer: lazyPage(() => import("./pages/OptimizerPage"), "OptimizerPage"),
  "condition-lab": lazyPage(() => import("./pages/ConditionLabPage"), "ConditionLabPage"),
  "decision-history": lazyPage(() => import("./pages/DecisionHistoryPage"), "DecisionHistoryPage"),
  "forex-fury": lazyPage(() => import("./pages/ForexFuryPage"), "ForexFuryPage"),
  "strategy-dev": lazyPage(() => import("./pages/StrategyDevPage"), "StrategyDevPage"),
  "stack-status": lazyPage(() => import("./pages/StackStatusPage"), "StackStatusPage"),
  "strategy-comparison": lazyPage(() => import("./pages/StrategyComparisonPage"), "StrategyComparisonPage"),
  "daily-report": lazyPage(() => import("./pages/DailyReportPage"), "DailyReportPage"),
  windows: lazyPage(() => import("./pages/WindowsPage"), "WindowsPage"),
};
const FloatingAssistant = lazy(() => import("./components/FloatingAssistant").then((m) => ({ default: m.FloatingAssistant })));
const DashboardStateHydrator = lazy(() => import("./components/DashboardStateHydrator").then((m) => ({ default: m.DashboardStateHydrator })));
const DASHBOARD_FAST_LANE_FETCH_DELAY_MS = 50;
const DASHBOARD_STALE_CACHE_IDLE_TIMEOUT_MS = 650;
const BACKGROUND_DASHBOARD_HYDRATOR_IDLE_TIMEOUT_MS = 2_200;
const FLOATING_ASSISTANT_IDLE_TIMEOUT_MS = 1_200;

type IdleCallbackHandle = number;
type IdleSchedulerWindow = Window & {
  requestIdleCallback?: (callback: () => void, options?: { timeout?: number }) => IdleCallbackHandle;
  cancelIdleCallback?: (handle: IdleCallbackHandle) => void;
};

function scheduleAppIdleWork(callback: () => void, timeoutMs: number): () => void {
  const idleWindow = window as IdleSchedulerWindow;
  if (idleWindow.requestIdleCallback) {
    const id = idleWindow.requestIdleCallback(callback, { timeout: timeoutMs });
    return () => idleWindow.cancelIdleCallback?.(id);
  }

  const id = window.setTimeout(callback, timeoutMs);
  return () => window.clearTimeout(id);
}

function initialPageFromUrl(): Page {
  if (typeof window === "undefined") return "proof";
  const raw = new URLSearchParams(window.location.search).get("page");
  return isPage(raw) ? raw : "proof";
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function startupDashboardState(): DashboardState {
  const today = todayIso();
  const waiting = "Waiting for live API fast dashboard.";

  return {
    uiReadiness: {
      readiness_status: "NOT_READY_FOR_UI_UX",
      min_daily_bundles_for_ui: 5,
      completed_trading_days: 0,
      broker_verified_days: 0,
      decision_days: 0,
      risk_review_days: 0,
      complete_bundle_days: 0,
      complete_bundle_dates: [],
      route_counts: {},
      risk_status_counts: {},
      chains_verified: { paper_proof: false, paper_decision: false, paper_risk: false },
      blockers: [waiting],
      next_ui_step: waiting,
    },
    dailySchedule: {
      as_of_date: today,
      next_due_date: today,
      next_due_status: "LOADING_LIVE_API",
      complete_bundle_days: 0,
      completed_trading_days: 0,
      broker_verified_days: 0,
      decision_days: 0,
      risk_review_days: 0,
      ui_min_daily_bundles: 5,
      ui_bundles_remaining: 5,
      required_paper_days: 30,
      paper_days_remaining: 30,
      missing_tracks_for_next_due: [],
      complete_bundle_dates: [],
      recommended_command: "",
      notes: [waiting],
    },
    dailyBundle: {
      date: today,
      steps: [],
      completed: false,
      latest_proof: {
        completed_trading_days: 0,
        required_trading_days: 30,
        chain_verified: false,
        passed: false,
        failure_reasons: [waiting],
      },
      latest_decision: {
        decision_count: 0,
        route_counts: {},
        chain_verified: false,
        latest_decision: {
          date: today,
          decision_id: "startup-decision",
          route_action: "NO_TRADE",
          timeframe: "D1",
          macro_status: "LOADING",
          macro_reason: waiting,
          event_context: "startup",
          notes: [],
          symbol_decisions: [],
        },
      },
      latest_risk: {
        review_count: 0,
        risk_status_counts: {},
        chain_verified: false,
        latest_review: {
          risk_status: "LOADING_LIVE_API",
          account_equity: 0,
          max_risk_per_trade_pct: 0,
          daily_risk_budget_pct: 0,
          daily_risk_budget_usd: 0,
          max_position_lots: 0,
          max_paper_attempts: 0,
          proposed_attempts: 0,
          blockers: [waiting],
          sizing: [],
        },
      },
      completed_steps: 0,
      total_steps: 0,
      overall_status: "LOADING_LIVE_API",
    },
    strategyLeads: [],
  } as unknown as DashboardState;
}

async function fetchInstantWasteStage(): Promise<Record<string, unknown> | null> {
  const { fetchWasteStageProbe, wasteLoopFromStagePayload } = await import("./data/wasteStageProbe");
  const payload = await fetchWasteStageProbe({ timeoutMs: 1_500, maxAgeMs: 1_000 });
  if (!payload) return null;
  return wasteLoopFromStagePayload(payload, {
    reportKind: "cas_forex_waste_stage_root_probe",
    claimBoundary: "Root WASTE probe is observational only; no trading, broker, payment, payout, or order authority.",
  });
}

export function App() {
  const [page, setPageState] = useState<Page>(() => initialPageFromUrl());
  const [assistantMounted, setAssistantMounted] = useState(false);
  const [dashboardHydratorMounted, setDashboardHydratorMounted] = useState(
    () => initialPageFromUrl() === "dashboard",
  );
  const setPage = (next: Page) => {
    setPageState(next);
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("page", next);
      window.history.replaceState(null, "", url.toString());
    }
  };

  const startupState = useMemo(() => startupDashboardState(), []);
  const [apiState, setApiState] = useState<DashboardState | null>(startupState);
  const [error, setError] = useState<string | null>(null);
  const state = apiState ?? startupState;
  const ActivePage = PAGE_COMPONENTS[page];

  useEffect(() => {
    return scheduleAppIdleWork(
      () => setAssistantMounted(true),
      FLOATING_ASSISTANT_IDLE_TIMEOUT_MS,
    );
  }, []);

  useEffect(() => {
    let cancelled = false;
    const cancelStaleCacheRead = scheduleAppIdleWork(() => {
      void import("./data/dashboardStartupCache").then((cache) => {
        if (cancelled) return;
        const stalePacket = cache.readStaleDashboardPacket();
        if (!stalePacket) return;
        setApiState((current) => (
          current === startupState
            ? cache.mergeStartupDashboardPacket(startupState, stalePacket)
            : current
        ));
      });
    }, DASHBOARD_STALE_CACHE_IDLE_TIMEOUT_MS);
    return () => {
      cancelled = true;
      cancelStaleCacheRead();
    };
  }, [startupState]);

  useEffect(() => {
    if (page === "dashboard") {
      setDashboardHydratorMounted(true);
      return;
    }

    const idleWindow = window as IdleSchedulerWindow;
    if (idleWindow.requestIdleCallback) {
      const id = idleWindow.requestIdleCallback(
        () => setDashboardHydratorMounted(true),
        { timeout: BACKGROUND_DASHBOARD_HYDRATOR_IDLE_TIMEOUT_MS },
      );
      return () => idleWindow.cancelIdleCallback?.(id);
    }

    const id = window.setTimeout(
      () => setDashboardHydratorMounted(true),
      BACKGROUND_DASHBOARD_HYDRATOR_IDLE_TIMEOUT_MS,
    );
    return () => window.clearTimeout(id);
  }, [page]);

  useEffect(() => {
    let cancelled = false;
    void fetchInstantWasteStage().then((wasteLoop) => {
      if (cancelled || !wasteLoop) return;
      setApiState((current) => ({
        ...(current ?? startupState),
        wasteLoop,
      }));
    });
    return () => {
      cancelled = true;
    };
  }, [startupState]);

  return (
    <>
      <Shell
        readiness={state.uiReadiness}
        authority={state.authorityBoundary}
        wasteLoop={state.wasteLoop}
        activePage={page}
        onNavigate={setPage}
      >
        {error && <div className="api-status-strip">{error}</div>}
        <ErrorBoundary resetKey={page} label={page}>
          <Suspense fallback={page === "dashboard" ? <DashboardInstantShell state={state} /> : <div className="page-loading">Loading...</div>}>
            <ActivePage state={state} />
          </Suspense>
        </ErrorBoundary>
      </Shell>
      {assistantMounted && (
        <Suspense fallback={null}>
          <FloatingAssistant />
        </Suspense>
      )}
      {dashboardHydratorMounted && (
        <Suspense fallback={null}>
          <DashboardStateHydrator
            fastFetchDeferMs={page === "dashboard" ? DASHBOARD_FAST_LANE_FETCH_DELAY_MS : undefined}
            initialState={startupState}
            onError={setError}
            onState={setApiState}
          />
        </Suspense>
      )}
    </>
  );
}

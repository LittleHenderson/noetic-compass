/* ── CAS Forex — Root App ── */

import { useState, useMemo } from "react";
import { Shell } from "./components/Shell";
import { ProofPage } from "./pages/ProofPage";
import { AuditPage } from "./pages/AuditPage";
import { DashboardPage } from "./pages/DashboardPage";
import { TradePage } from "./pages/TradePage";
import { AdaptivePage } from "./pages/AdaptivePage";
import { HistoryPage } from "./pages/HistoryPage";
import { SettingsPage } from "./pages/SettingsPage";
import { PcbaPage } from "./pages/PcbaPage";
import { LedgerPage } from "./pages/LedgerPage";
import { OptimizerPage } from "./pages/OptimizerPage";
import { ConditionLabPage } from "./pages/ConditionLabPage";
import {
  UI_READINESS_FIXTURE,
  DAILY_SCHEDULE_FIXTURE,
  DAILY_BUNDLE_FIXTURE,
  ADAPTIVE_COCKPIT_FIXTURE,
  STRATEGY_LEADS_FIXTURE,
  BACKSOLVE_FIXTURE,
  CONDITION_TALLY_FIXTURE,
  WALK_FORWARD_FIXTURE,
  MT5_RECEIPT_FIXTURE,
  AUTHORITY_BOUNDARY_FIXTURE,
  RUNTIME_GATES_FIXTURE,
  AI_MODEL_FIXTURE,
  BROKER_CANDIDATES_FIXTURE,
  PCBA_COCKPIT_FIXTURE,
} from "./data/fixtures";
import { useDashboard } from "./data/api";
import type { DashboardState } from "./types/evidence";
import "./App.css";

type Page =
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
  | "condition-lab";

const PAGE_IDS: Page[] = ["proof", "audit", "dashboard", "trade", "adaptive", "history", "settings", "pcba", "ledger", "optimizer", "condition-lab"];

function initialPageFromUrl(): Page {
  if (typeof window === "undefined") return "proof";
  const raw = new URLSearchParams(window.location.search).get("page");
  return PAGE_IDS.includes(raw as Page) ? (raw as Page) : "proof";
}

export function App() {
  const [page, setPageState] = useState<Page>(() => initialPageFromUrl());
  const setPage = (next: Page) => {
    setPageState(next);
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("page", next);
      window.history.replaceState(null, "", url.toString());
    }
  };

  const fixtureState: DashboardState = useMemo(
    () => ({
      uiReadiness: UI_READINESS_FIXTURE,
      dailySchedule: DAILY_SCHEDULE_FIXTURE,
      dailyBundle: DAILY_BUNDLE_FIXTURE,
      adaptive: ADAPTIVE_COCKPIT_FIXTURE,
      ownerControl: {
        mode: "AI_FULL_AUTO_PAPER",
        max_concurrent_trades: 15,
        max_loss_cap_pct: 10,
        ai_autonomy_enabled: true,
        live_requested: false,
        live_blocked: true,
        claim_boundary:
          "Owner control policy is owner-controlled: research/paper automation can run now; live trading, broker ACCEPT, and payment movement require explicit owner enable flags, credentials/provider config, and gate clearance.",
      },
      strategyLeads: STRATEGY_LEADS_FIXTURE,
      backsolve: BACKSOLVE_FIXTURE,
      conditionTally: CONDITION_TALLY_FIXTURE,
      walkForward: WALK_FORWARD_FIXTURE,
      mt5Receipt: MT5_RECEIPT_FIXTURE,
      authorityBoundary: AUTHORITY_BOUNDARY_FIXTURE,
      runtimeGates: RUNTIME_GATES_FIXTURE,
      aiModel: AI_MODEL_FIXTURE,
      brokerCandidates: BROKER_CANDIDATES_FIXTURE,
      pcba: PCBA_COCKPIT_FIXTURE,
    }),
    [],
  );
  const { state: apiState, loading, error } = useDashboard(fixtureState);
  const state = apiState ?? fixtureState;

  return (
    <Shell readiness={state.uiReadiness} activePage={page} onNavigate={setPage}>
      {(loading || error) && (
        <div className="api-status-strip">
          {loading ? "Loading live evidence API..." : error}
        </div>
      )}
      {page === "proof" && <ProofPage state={state} />}
      {page === "audit" && <AuditPage state={state} />}
      {page === "dashboard" && <DashboardPage state={state} />}
      {page === "trade" && <TradePage state={state} />}
      {page === "adaptive" && <AdaptivePage state={state} />}
      {page === "history" && <HistoryPage state={state} />}
      {page === "settings" && <SettingsPage state={state} />}
      {page === "pcba" && <PcbaPage state={state} />}
      {page === "ledger" && <LedgerPage state={state} />}
      {page === "optimizer" && <OptimizerPage state={state} />}
      {page === "condition-lab" && <ConditionLabPage state={state} />}
    </Shell>
  );
}

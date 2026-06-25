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
import { DecisionHistoryPage } from "./pages/DecisionHistoryPage";
import { ForexFuryPage } from "./pages/ForexFuryPage";
import { StrategyDevPage } from "./pages/StrategyDevPage";
import { StackStatusPage } from "./pages/StackStatusPage";
import { StrategyComparisonPage } from "./pages/StrategyComparisonPage";
import { DailyReportPage } from "./pages/DailyReportPage";
import {
  UI_READINESS_FIXTURE,
  DAILY_SCHEDULE_FIXTURE,
  DAILY_BUNDLE_FIXTURE,
  ADAPTIVE_COCKPIT_FIXTURE,
  STRATEGY_LEADS_FIXTURE,
  BACKSOLVE_FIXTURE,
  CONDITION_TALLY_FIXTURE,
  WALK_FORWARD_FIXTURE,
  EXTERNAL_BENCHMARKS_FIXTURE,
  FOREX_FURY_REPLAY_CANDIDATES_FIXTURE,
  FOREX_FURY_REPLAY_RESULTS_FIXTURE,
  FOREX_FURY_SET_IMPORT_FIXTURE,
  AGENT_WORKFLOW_PLAN_FIXTURE,
  AGENT_WORKFLOW_CYCLE_FIXTURE,
  AGENT_INFORMATION_FLOW_FIXTURE,
  AGENT_MESSAGE_BUS_FIXTURE,
  AGENT_MEMORY_FIXTURE,
  AGENT_RESEARCH_QUEUE_FIXTURE,
  STRATEGY_DEV_QUEUE_FIXTURE,
  STRATEGY_PATCH_RUNNER_FIXTURE,
  DAILY_LEARNING_ROLLUP_FIXTURE,
  SESSION_AUTOWAKE_FIXTURE,
  TERMINAL_RECEIPT_WATCHER_FIXTURE,
  TERMINAL_BRIDGE_SUPERVISOR_FIXTURE,
  MT4_TERMINAL_ACTIVATION_FIXTURE,
  MT4_PING_ROUNDTRIP_FIXTURE,
  MT4_TERMINAL_SESSION_VERIFIER_FIXTURE,
  MT4_HISTORY_EXPORT_VERIFIER_FIXTURE,
  MT5_TERMINAL_API_VERIFIER_FIXTURE,
  MT5_PAPER_EXECUTION_VERIFIER_FIXTURE,
  MT5_DEAL_HISTORY_INGEST_FIXTURE,
  TERMINAL_POSITION_RECONCILIATION_FIXTURE,
  TERMINAL_OPERABILITY_VERIFIER_FIXTURE,
  TERMINAL_RECEIPT_INGEST_FIXTURE,
  TERMINAL_HISTORY_INGEST_FIXTURE,
  MT5_RECEIPT_FIXTURE,
  MT5_PROBE_STATUS_FIXTURE,
  AUTHORITY_BOUNDARY_FIXTURE,
  RUNTIME_GATES_FIXTURE,
  AI_MODEL_FIXTURE,
  BROKER_CANDIDATES_FIXTURE,
  PCBA_COCKPIT_FIXTURE,
  ACCOUNT_LEDGER_FIXTURE,
  MOVEMENT_STREAM_FIXTURE,
  ACCOUNT_RECONCILIATION_FIXTURE,
  LIVE_READINESS_FIXTURE,
  BROKER_SYNCED_RISK_PREVIEW_FIXTURE,
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
  | "condition-lab"
  | "decision-history"
  | "forex-fury"
  | "strategy-dev"
  | "stack-status"
  | "strategy-comparison"
  | "daily-report";

const PAGE_IDS: Page[] = ["proof", "audit", "dashboard", "trade", "adaptive", "history", "settings", "pcba", "ledger", "optimizer", "condition-lab", "decision-history", "forex-fury", "strategy-dev", "stack-status", "strategy-comparison", "daily-report"];

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
      accountLedger: ACCOUNT_LEDGER_FIXTURE,
      movementStream: MOVEMENT_STREAM_FIXTURE,
      accountReconciliation: ACCOUNT_RECONCILIATION_FIXTURE,
      liveReadiness: LIVE_READINESS_FIXTURE,
      brokerSyncedRiskPreview: BROKER_SYNCED_RISK_PREVIEW_FIXTURE,
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
      externalBenchmarks: EXTERNAL_BENCHMARKS_FIXTURE,
      forexFurySetImport: FOREX_FURY_SET_IMPORT_FIXTURE,
      forexFuryReplayCandidates: FOREX_FURY_REPLAY_CANDIDATES_FIXTURE,
      forexFuryReplayResults: FOREX_FURY_REPLAY_RESULTS_FIXTURE,
      agentWorkflowPlan: AGENT_WORKFLOW_PLAN_FIXTURE,
      agentWorkflowCycle: AGENT_WORKFLOW_CYCLE_FIXTURE,
      agentInformationFlow: AGENT_INFORMATION_FLOW_FIXTURE,
      agentMessageBus: AGENT_MESSAGE_BUS_FIXTURE,
      agentMemory: AGENT_MEMORY_FIXTURE,
      agentResearchQueue: AGENT_RESEARCH_QUEUE_FIXTURE,
      strategyDevQueue: STRATEGY_DEV_QUEUE_FIXTURE,
      strategyPatchRunner: STRATEGY_PATCH_RUNNER_FIXTURE,
      dailyLearningRollup: DAILY_LEARNING_ROLLUP_FIXTURE,
      sessionAutowake: SESSION_AUTOWAKE_FIXTURE,
      terminalReceiptWatcher: TERMINAL_RECEIPT_WATCHER_FIXTURE,
      terminalBridgeSupervisor: TERMINAL_BRIDGE_SUPERVISOR_FIXTURE,
      mt4TerminalActivation: MT4_TERMINAL_ACTIVATION_FIXTURE,
      mt4PingRoundtrip: MT4_PING_ROUNDTRIP_FIXTURE,
      mt4TerminalSessionVerifier: MT4_TERMINAL_SESSION_VERIFIER_FIXTURE,
      mt4HistoryExportVerifier: MT4_HISTORY_EXPORT_VERIFIER_FIXTURE,
      mt5TerminalApiVerifier: MT5_TERMINAL_API_VERIFIER_FIXTURE,
      mt5PaperExecutionVerifier: MT5_PAPER_EXECUTION_VERIFIER_FIXTURE,
      mt5DealHistoryIngest: MT5_DEAL_HISTORY_INGEST_FIXTURE,
      terminalPositionReconciliation: TERMINAL_POSITION_RECONCILIATION_FIXTURE,
      terminalOperabilityVerifier: TERMINAL_OPERABILITY_VERIFIER_FIXTURE,
      terminalReceiptIngest: TERMINAL_RECEIPT_INGEST_FIXTURE,
      terminalHistoryIngest: TERMINAL_HISTORY_INGEST_FIXTURE,
      mt5Receipt: MT5_RECEIPT_FIXTURE,
      mt5ProbeStatus: MT5_PROBE_STATUS_FIXTURE,
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
      {page === "decision-history" && <DecisionHistoryPage />}
      {page === "forex-fury" && <ForexFuryPage state={state} />}
      {page === "strategy-dev" && <StrategyDevPage state={state} />}
      {page === "stack-status" && <StackStatusPage />}
      {page === "strategy-comparison" && <StrategyComparisonPage />}
      {page === "daily-report" && <DailyReportPage />}
    </Shell>
  );
}

import { lazy, Suspense, useEffect, useState } from "react";
import { GlassPanel } from "../components/GlassPanel";
import type { DashboardState } from "../types/evidence";

interface DashboardPageProps {
  state: DashboardState;
}

const DashboardOperationsWorkbench = lazy(() => import("../components/DashboardOperationsWorkbench").then((m) => ({
  default: m.DashboardOperationsWorkbench,
})));
const ObjectivePaceCard = lazy(() => import("../components/ObjectivePaceCard").then((m) => ({
  default: m.ObjectivePaceCard,
})));
const IncentiveLedgerCard = lazy(() => import("../components/IncentiveLedgerCard").then((m) => ({
  default: m.IncentiveLedgerCard,
})));
const OperatorBriefingCard = lazy(() => import("../components/OperatorBriefingCard").then((m) => ({
  default: m.OperatorBriefingCard,
})));

const DASHBOARD_DEEP_OPERATIONS_IDLE_TIMEOUT_MS = 1_600;
const DASHBOARD_OPERATOR_BRIEFING_DEFER_MS = 900;
const DASHBOARD_OBJECTIVE_SUPPORT_DEFER_MS = 1_100;

type IdleCallbackHandle = number;
type IdleSchedulerWindow = Window & {
  requestIdleCallback?: (callback: () => void, options?: { timeout?: number }) => IdleCallbackHandle;
  cancelIdleCallback?: (handle: IdleCallbackHandle) => void;
};

function scheduleDashboardIdleWork(callback: () => void, timeoutMs: number): () => void {
  const idleWindow = window as IdleSchedulerWindow;
  if (idleWindow.requestIdleCallback) {
    const id = idleWindow.requestIdleCallback(callback, { timeout: timeoutMs });
    return () => idleWindow.cancelIdleCallback?.(id);
  }

  const id = window.setTimeout(callback, timeoutMs);
  return () => window.clearTimeout(id);
}

export function DashboardPage({ state }: DashboardPageProps) {
  const [operatorBriefingMounted, setOperatorBriefingMounted] = useState(false);
  const [objectiveSupportMounted, setObjectiveSupportMounted] = useState(false);
  const [deepOperationsMounted, setDeepOperationsMounted] = useState(false);
  const { uiReadiness: r, dailyBundle: b } = state;
  const risk = b.latest_risk.latest_review;
  const riskBudget = state.riskBudget;
  const proofProgress = state.proofProgress;
  const accountEquity = riskBudget?.account_equity ?? risk.account_equity;
  const account = state.accountLedger?.summary;
  const realizedPnl = account?.realized_pnl_usd ?? 0;
  const completedTradingDays = proofProgress?.completed_trading_days ?? r.completed_trading_days;
  const completeBundleDays = proofProgress?.complete_bundle_days ?? r.complete_bundle_days;
  const minDailyBundles = proofProgress?.min_daily_bundles_for_ui ?? r.min_daily_bundles_for_ui;
  const chainsVerified = proofProgress
    ? proofProgress.chains_verified_count >= proofProgress.chains_expected_count
    : r.chains_verified.paper_proof && r.chains_verified.paper_decision && r.chains_verified.paper_risk;
  const chainsVerifiedLabel = proofProgress
    ? `${proofProgress.chains_verified_count}/${proofProgress.chains_expected_count}`
    : "3/3";
  const tradingDayIndex = Math.min(20, Math.max(0, completedTradingDays));
  const isLiveLedger = state.accountLedger?.live_money_authorized ?? false;
  const plannedRiskTotal =
    riskBudget?.planned_risk_total_usd
    ?? risk.planned_risk_total_usd
    ?? risk.sizing.reduce((sum, row) => sum + row.planned_risk_usd, 0);

  useEffect(() => {
    return scheduleDashboardIdleWork(
      () => setOperatorBriefingMounted(true),
      DASHBOARD_OPERATOR_BRIEFING_DEFER_MS,
    );
  }, []);

  useEffect(() => {
    return scheduleDashboardIdleWork(
      () => setObjectiveSupportMounted(true),
      DASHBOARD_OBJECTIVE_SUPPORT_DEFER_MS,
    );
  }, []);

  useEffect(() => {
    return scheduleDashboardIdleWork(
      () => setDeepOperationsMounted(true),
      DASHBOARD_DEEP_OPERATIONS_IDLE_TIMEOUT_MS,
    );
  }, []);

  return (
    <div className="dashboard-page">
      {operatorBriefingMounted ? (
        <Suspense fallback={<OperatorBriefingCardFallback />}>
          <OperatorBriefingCard />
        </Suspense>
      ) : (
        <OperatorBriefingCardFallback />
      )}

      <div className="dashboard-grid-3col">
        <GlassPanel title="Account" variant="info">
          <div className="metric-stack">
            <Metric label="Deposit" value={`$${(account?.deposit_usd ?? accountEquity).toLocaleString()}`} />
            <Metric label="Balance" value={`$${(account?.balance_usd ?? accountEquity).toLocaleString()}`} />
            <Metric label="Equity" value={`$${(account?.equity_usd ?? accountEquity).toLocaleString()}`} />
            <Metric label="Mode" value={isLiveLedger ? "LIVE LEDGER" : "PAPER / DEMO"} warning={!isLiveLedger} />
          </div>
        </GlassPanel>

        <GlassPanel title="Risk Budget">
          <div className="metric-stack">
            <Metric label="Realized P/L" value={`$${(account?.realized_pnl_usd ?? 0).toFixed(2)}`} />
            <Metric label="Floating P/L" value={`$${(account?.floating_pnl_usd ?? 0).toFixed(2)}`} />
            <Metric label="Margin / Free" value={`$${(account?.margin_used_usd ?? 0).toFixed(0)} / $${(account?.free_margin_usd ?? accountEquity).toFixed(0)}`} mono />
            <Metric label="Planned Risk" value={`$${(account?.planned_risk_usd ?? plannedRiskTotal).toFixed(2)}`} mono />
          </div>
        </GlassPanel>

        <GlassPanel title="Proof Progress">
          <div className="metric-stack">
            <Metric label="Paper Days" value={`${completedTradingDays} / 30`} mono />
            <Metric label="Multi-Day Bundles" value={`${completeBundleDays} / ${minDailyBundles}`} mono />
            <Metric label="Chains Verified" value={chainsVerified ? chainsVerifiedLabel : "INCOMPLETE"} mono />
            <Metric label="Edge" value="OPEN" warning />
          </div>
        </GlassPanel>
      </div>

      {objectiveSupportMounted ? (
        <Suspense fallback={<ObjectiveSupportCardsFallback />}>
          <div className="dashboard-grid-2col">
            <ObjectivePaceCard
              dailyTarget={250}
              monthlyTarget={5000}
              realizedToday={realizedPnl}
              realizedMonth={realizedPnl}
              tradingDayIndex={tradingDayIndex}
            />
            <IncentiveLedgerCard verifiedProfit={realizedPnl} rate={0.025} per={5000} />
          </div>
        </Suspense>
      ) : (
        <ObjectiveSupportCardsFallback />
      )}
      <div className="control-field-desc" style={{ margin: "-2px 4px 4px" }}>
        Objective is $250/day toward $5,000/month, with a $3,500 daily cap; the AI earns it only
        by pressing real, tested edges. A no-edge day stays at $0 with capital intact, never a miss.
      </div>

      {deepOperationsMounted ? (
        <Suspense fallback={<DashboardDeferredSectionsNotice />}>
          <DashboardOperationsWorkbench state={state} />
        </Suspense>
      ) : (
        <DashboardDeferredSectionsNotice />
      )}
    </div>
  );
}

function OperatorBriefingCardFallback() {
  return (
    <GlassPanel title="Operator Briefing" subtitle="Syncing live cockpit snapshot" variant="info">
      <div className="dashboard-grid-3col">
        <div className="metric-stack" style={{ padding: 0 }}>
          <Metric label="Loop" value="SYNCING" mono />
          <Metric label="Stage" value="LIVE HEADER ACTIVE" mono />
        </div>
        <div className="metric-stack" style={{ padding: 0 }}>
          <Metric label="Orders" value="OWNER GATED" mono warning />
          <Metric label="Payment" value="PAYMENT SETUP PENDING" warning />
        </div>
        <div className="metric-stack" style={{ padding: 0 }}>
          <Metric label="Safety" value="READ ONLY" mono />
          <Metric label="Status" value="WAITING" mono />
        </div>
      </div>
    </GlassPanel>
  );
}

function ObjectiveSupportCardsFallback() {
  return (
    <div className="dashboard-grid-2col">
      <GlassPanel title="Objective" subtitle="Syncing pace card" variant="info">
        <div className="metric-stack">
          <Metric label="Daily Target" value="$250" mono />
          <Metric label="Monthly Target" value="$5,000" mono />
        </div>
      </GlassPanel>
      <GlassPanel title="AI Performance Fee" subtitle="Syncing verified-profit ledger" variant="info">
        <div className="metric-stack">
          <Metric label="Rate" value="2.5%" mono />
          <Metric label="Basis" value="VERIFIED PROFIT ONLY" mono />
        </div>
      </GlassPanel>
    </div>
  );
}

function DashboardDeferredSectionsNotice() {
  return (
    <GlassPanel title="Deep Operations" subtitle="Loading after first live dashboard paint" variant="info">
      <div className="dashboard-grid-3col">
        <div className="metric-stack" style={{ padding: 0 }}>
          <Metric label="WASTE Loop" value="LIVE HEADER ACTIVE" mono />
          <Metric label="Payment" value="PAYMENT SETUP PENDING" warning />
        </div>
        <div className="metric-stack" style={{ padding: 0 }}>
          <Metric label="Controls" value="SYNCING" mono warning />
          <Metric label="Broker Truth" value="QUEUED" mono />
        </div>
        <div className="metric-stack" style={{ padding: 0 }}>
          <Metric label="Live Orders" value="OWNER GATED" mono warning />
          <Metric label="Status" value="READ ONLY" mono />
        </div>
      </div>
    </GlassPanel>
  );
}

function Metric({ label, value, mono, danger, warning }: { label: string; value: string; mono?: boolean; danger?: boolean; warning?: boolean }) {
  return (
    <div className="summary-row">
      <span className="field-label">{label}</span>
      <span className={`field-value ${mono ? "mono" : ""}`} style={{ color: danger ? "var(--danger)" : warning ? "var(--warning)" : undefined }}>
        {value}
      </span>
    </div>
  );
}

import { lazy, Suspense, useEffect, useState } from "react";
import { AccountHealthPanel } from "../components/AccountHealthPanel";
import { GlassPanel } from "../components/GlassPanel";
import { Metric } from "../components/Metric";
import { dashboardStateProvenance } from "../util/provenance";
import { LiveReadinessSummaryPanel } from "../components/LiveReadinessSummaryPanel";
import { PsychologyGuardPanel } from "../components/PsychologyGuardPanel";
import { StatusChip } from "../components/StatusChip";
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
  // One provenance verdict for everything this page derives from `state`:
  // live (hydrated this session), cached (recovered packet), or unproven
  // (the synthetic startup shell). Every Metric row below carries it.
  const { provenance: stateProvenance, asOf: stateAsOf } = dashboardStateProvenance(state);
  const risk = b.latest_risk.latest_review;
  const riskBudget = state.riskBudget;
  const proofProgress = state.proofProgress;
  const accountHealth = state.accountHealth;
  const activeTruth = state.activeAccountTruth;
  const activeAccount = activeTruth?.account;
  const activeExposure = activeTruth?.open_exposure;
  const activeGrowth = activeTruth?.growth_measurement;
  const activeOutcomes = activeGrowth?.cas_bound_closed_outcomes;
  const activeMt5Account = activeTruth?.authoritative_account_source === "mt5_account_snapshot";
  const accountEquity = finiteNumber(activeAccount?.equity_usd)
    ?? riskBudget?.account_equity
    ?? risk.account_equity;
  const account = state.accountLedger?.summary;
  const healthAccount = accountHealth?.account;
  const openExposure = accountHealth?.open_exposure;
  const casBoundClosedNet = finiteNumber(activeOutcomes?.net_pnl_usd);
  const simulatorRealizedPnl = finiteNumber(healthAccount?.realized_pnl_usd)
    ?? finiteNumber(account?.realized_pnl_usd)
    ?? 0;
  const realizedPnl = activeMt5Account ? casBoundClosedNet : simulatorRealizedPnl;
  const activeBalance = finiteNumber(activeAccount?.balance_usd) ?? accountEquity;
  const activeEquity = finiteNumber(activeAccount?.equity_usd) ?? accountEquity;
  const activeFloatingPnl = finiteNumber(activeAccount?.floating_pnl_usd);
  const activeRealizedGrowth = finiteNumber(activeGrowth?.cashflow_adjusted_realized_growth_usd);
  const activeRealizedToday = finiteNumber(activeGrowth?.realized_today_usd);
  const activeRealizedMonth = finiteNumber(activeGrowth?.realized_month_usd);
  const activeExternalCapital = finiteNumber(activeGrowth?.net_external_capital_flow_usd);
  const activeGrowthPct = finiteNumber(activeGrowth?.growth_pct_on_net_external_capital);
  const activeGrowthReconciled = activeGrowth?.account_growth_reconciliation?.reconciled === true;
  const activeFreeMargin = finiteNumber(activeAccount?.free_margin_usd);
  const activeOpenCount = finiteNumber(activeExposure?.open_position_count)
    ?? finiteNumber(openExposure?.open_position_count)
    ?? 0;
  const activeClosedTrades = finiteNumber(activeOutcomes?.trades);
  const activeWins = finiteNumber(activeOutcomes?.wins);
  const activeLosses = finiteNumber(activeOutcomes?.losses);
  const activeOutcomesLabel = activeClosedTrades == null
    ? "UNAVAILABLE"
    : `${activeClosedTrades.toFixed(0)} (${(activeWins ?? 0).toFixed(0)}W / ${(activeLosses ?? 0).toFixed(0)}L)`;
  const activeSnapshotFresh = activeTruth?.snapshot?.fresh;
  const accountIdentity = activeAccount?.login
    ? `#${activeAccount.login}`
    : activeTruth?.source_label || "SYNCING";
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
        <GlassPanel title="Active Account" variant="info">
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
            <StatusChip label={activeTruth?.source_label || "SOURCE SYNCING"} variant={activeMt5Account ? "success" : "paper"} size="sm" />
            <StatusChip label="PRIMARY" variant="info" size="sm" />
            <StatusChip
              label={activeGrowthReconciled ? "REALIZED GROWTH RECONCILED" : "GROWTH BASELINE UNAVAILABLE"}
              variant={activeGrowthReconciled ? "success" : "warning"}
              size="sm"
            />
            {activeSnapshotFresh === false && <StatusChip label="STALE SNAPSHOT" variant="warning" size="sm" />}
          </div>
          <div className="metric-stack">
            <Metric provenance={stateProvenance} asOf={stateAsOf} label="Account" value={accountIdentity} mono />
            <Metric provenance={stateProvenance} asOf={stateAsOf} label="Server" value={activeAccount?.server || "LOCAL SIMULATOR"} mono />
            <Metric provenance={stateProvenance} asOf={stateAsOf} label="Balance" value={formatMoney(activeBalance)} mono />
            <Metric provenance={stateProvenance} asOf={stateAsOf} label="Equity" value={formatMoney(activeEquity)} mono />
            <Metric provenance={stateProvenance} asOf={stateAsOf} label="Net Open P/L" value={formatMoney(activeFloatingPnl, true)} mono />
            <Metric provenance={stateProvenance} asOf={stateAsOf} label="Price P/L" value={formatMoney(activeAccount?.position_price_pnl_usd, true)} mono />
            <Metric provenance={stateProvenance} asOf={stateAsOf} label="Swap / Carry" value={formatMoney(activeAccount?.open_swap_usd, true)} mono />
            <Metric provenance={stateProvenance} asOf={stateAsOf} label="Realized Growth" value={formatMoney(activeRealizedGrowth, true)} mono warning={!activeGrowthReconciled} />
            <Metric provenance={stateProvenance} asOf={stateAsOf} label="Realized Today" value={formatMoney(activeRealizedToday, true)} mono warning={!activeGrowthReconciled} />
            <Metric provenance={stateProvenance} asOf={stateAsOf} label="Realized Month" value={formatMoney(activeRealizedMonth, true)} mono warning={!activeGrowthReconciled} />
            <Metric provenance={stateProvenance} asOf={stateAsOf} label="External Capital" value={formatMoney(activeExternalCapital)} mono warning={!activeGrowthReconciled} />
            <Metric provenance={stateProvenance} asOf={stateAsOf} label="Growth on Capital" value={formatPercent(activeGrowthPct, "UNAVAILABLE")} mono warning={!activeGrowthReconciled} />
            <Metric provenance={stateProvenance} asOf={stateAsOf} label="Free Margin" value={formatMoney(activeFreeMargin)} mono />
            <Metric provenance={stateProvenance} asOf={stateAsOf} label="Open Positions" value={activeOpenCount.toFixed(0)} mono />
          </div>
          <div className="control-field-desc" style={{ marginTop: 8 }}>
            {activeGrowthReconciled
              ? "Broker ledger reconciled to balance. Deposits, withdrawals, credit, and bonuses are excluded from trading growth."
              : activeTruth?.source_detail || "Resolving the account governed by the active execution lane."}
          </div>
        </GlassPanel>

        <GlassPanel title="Decision Metrics">
          <div className="metric-stack">
            <Metric
              provenance={stateProvenance}
              asOf={stateAsOf}
              label={activeMt5Account ? "CAS-Bound Closed Net" : "Realized P/L"}
              value={formatMoney(realizedPnl, true)}
              warning={realizedPnl == null}
            />
            <Metric provenance={stateProvenance} asOf={stateAsOf} label="CAS-Bound Outcomes" value={activeOutcomesLabel} mono warning={activeClosedTrades == null} />
            <Metric
              provenance={stateProvenance}
              asOf={stateAsOf}
              label="Open Risk at Stop"
              value={formatMoney(activeExposure?.entry_to_stop_risk_usd ?? openExposure?.open_risk_estimate_usd ?? account?.planned_risk_usd ?? plannedRiskTotal)}
              mono
            />
            <Metric
              provenance={stateProvenance}
              asOf={stateAsOf}
              label="Risk-Cap Breaches"
              value={activeExposure?.risk_cap_breach_count == null ? "UNAVAILABLE" : String(activeExposure.risk_cap_breach_count)}
              mono
              warning={(activeExposure?.risk_cap_breach_count ?? 0) > 0}
            />
            <Metric
              provenance={stateProvenance}
              asOf={stateAsOf}
              label="Protection"
              value={formatPercent(activeExposure?.protective_order_coverage_pct ?? openExposure?.protective_order_coverage_pct, "UNKNOWN")}
              warning={(activeExposure?.unprotected_position_count ?? openExposure?.unprotected_position_count ?? 0) > 0}
            />
          </div>
        </GlassPanel>

        <GlassPanel title="Proof Progress">
          <div className="metric-stack">
            <Metric provenance={stateProvenance} asOf={stateAsOf} label="Paper Days" value={`${completedTradingDays} / 30`} mono />
            <Metric provenance={stateProvenance} asOf={stateAsOf} label="Multi-Day Bundles" value={`${completeBundleDays} / ${minDailyBundles}`} mono />
            <Metric provenance={stateProvenance} asOf={stateAsOf} label="Chains Verified" value={chainsVerified ? chainsVerifiedLabel : "INCOMPLETE"} mono />
            <Metric
              provenance={stateProvenance}
              asOf={stateAsOf}
              label="Protected"
              value={formatPercent(openExposure?.protective_order_coverage_pct, "UNKNOWN")}
              warning={(openExposure?.unprotected_position_count ?? 0) > 0}
            />
          </div>
        </GlassPanel>
      </div>

      {objectiveSupportMounted ? (
        <Suspense fallback={<ObjectiveSupportCardsFallback />}>
          <div className="dashboard-grid-2col">
            <ObjectivePaceCard
              dailyTarget={250}
              monthlyTarget={5000}
              realizedToday={finiteNumber(activeTruth?.growth_measurement?.realized_today_usd)}
              realizedMonth={finiteNumber(activeTruth?.growth_measurement?.realized_month_usd)}
              tradingDayIndex={tradingDayIndex}
            />
            <IncentiveLedgerCard verifiedProfit={isLiveLedger ? realizedPnl : null} rate={0.025} per={5000} />
          </div>
        </Suspense>
      ) : (
        <ObjectiveSupportCardsFallback />
      )}
      <div className="control-field-desc" style={{ margin: "-2px 4px 4px" }}>
        Objective is $250/day toward $5,000/month, with a $3,500 daily cap; the AI earns it only
        by pressing real, tested edges. A no-edge day stays at $0 with capital intact, never a miss.
      </div>

      <LiveReadinessSummaryPanel
        initialLiveReadiness={state.liveReadiness ?? null}
        initialAccountReconciliation={state.accountReconciliation ?? null}
        initialBrokerTruthMonitor={state.brokerTruthMonitor ?? null}
      />

      <PsychologyGuardPanel subtitle="Main-cockpit anti-impulse friction across AI dial widening and owner risk loosening" />

      <AccountHealthPanel
        report={accountHealth}
        title={activeMt5Account ? "Secondary Simulator Evidence" : "Account Health"}
        subtitle={activeMt5Account
          ? "Separate research ledger; it is not the connected MT5 account"
          : "Decision-grade exposure, protection, performance, and source health"}
        authorityLabel={activeMt5Account ? "SECONDARY - NOT ACTIVE ACCOUNT" : undefined}
      />

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
          <Metric provenance="unproven" label="Loop" value="SYNCING" mono />
          <Metric provenance="unproven" label="Stage" value="LIVE HEADER ACTIVE" mono />
        </div>
        <div className="metric-stack" style={{ padding: 0 }}>
          <Metric provenance="unproven" label="Orders" value="OWNER GATED" mono warning />
          <Metric provenance="unproven" label="Payment" value="PAYMENT SETUP PENDING" warning />
        </div>
        <div className="metric-stack" style={{ padding: 0 }}>
          <Metric provenance="unproven" label="Safety" value="READ ONLY" mono />
          <Metric provenance="unproven" label="Status" value="WAITING" mono />
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
          <Metric provenance="unproven" label="Daily Target" value="$250" mono />
          <Metric provenance="unproven" label="Monthly Target" value="$5,000" mono />
        </div>
      </GlassPanel>
      <GlassPanel title="AI Performance Fee" subtitle="Syncing verified-profit ledger" variant="info">
        <div className="metric-stack">
          <Metric provenance="unproven" label="Rate" value="2.5%" mono />
          <Metric provenance="unproven" label="Basis" value="VERIFIED PROFIT ONLY" mono />
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
          <Metric provenance="unproven" label="WASTE Loop" value="LIVE HEADER ACTIVE" mono />
          <Metric provenance="unproven" label="Payment" value="PAYMENT SETUP PENDING" warning />
        </div>
        <div className="metric-stack" style={{ padding: 0 }}>
          <Metric provenance="unproven" label="Controls" value="SYNCING" mono warning />
          <Metric provenance="unproven" label="Broker Truth" value="QUEUED" mono />
        </div>
        <div className="metric-stack" style={{ padding: 0 }}>
          <Metric provenance="unproven" label="Live Orders" value="OWNER GATED" mono warning />
          <Metric provenance="unproven" label="Status" value="READ ONLY" mono />
        </div>
      </div>
    </GlassPanel>
  );
}

function finiteNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function formatMoney(value: number | null | undefined, signed = false): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "UNAVAILABLE";
  const sign = value < 0 ? "-" : signed && value > 0 ? "+" : "";
  return `${sign}$${Math.abs(value).toFixed(2)}`;
}

function formatPercent(value: number | null | undefined, fallback = "UNKNOWN"): string {
  return typeof value === "number" && Number.isFinite(value) ? `${value.toFixed(1)}%` : fallback;
}

// The local Metric copy is gone: this page uses components/Metric.tsx, whose
// required `provenance` prop is what makes an unlabelled value a compile error.

import { lazy, Suspense, useEffect, useState } from "react";
import { GlassPanel } from "./GlassPanel";
import { StatusChip } from "./StatusChip";
import {
  fetchBrokerEmergencyStatus,
  runBrokerEmergencyAction,
  type BrokerEmergencyActionResult,
} from "../data/api";
import "./DashboardSweepOpsPanel.css";

type ChipVariant = "success" | "warning" | "danger" | "info" | "muted" | "paper";
type IdleCallbackHandle = number;
type IdleSchedulerWindow = Window & {
  requestIdleCallback?: (callback: () => void, options?: { timeout?: number }) => IdleCallbackHandle;
  cancelIdleCallback?: (handle: IdleCallbackHandle) => void;
};

const DASHBOARD_BROKER_TRUTH_PANEL_IDLE_TIMEOUT_MS = 1_200;

const DashboardBrokerTruthOpsPanel = lazy(() => import("./DashboardBrokerTruthOpsPanel").then((m) => ({
  default: m.DashboardBrokerTruthOpsPanel,
})));

export function DashboardSweepOpsPanel({ ops }: { ops: any }) {
  const [brokerTruthPanelReady, setBrokerTruthPanelReady] = useState(false);
  const [brokerEmergency, setBrokerEmergency] = useState<BrokerEmergencyActionResult | null>(null);
  const [ownerConfirmBrokerEmergency, setOwnerConfirmBrokerEmergency] = useState(false);
  const [brokerEmergencyBusy, setBrokerEmergencyBusy] = useState("");
  const [brokerEmergencyMessage, setBrokerEmergencyMessage] = useState("");
  const {
    activeLiveReadiness,
    autonomousSweep,
    autoHaltActive,
    autoHaltCheckVariant,
    autoHaltChecks,
    autoHaltClearBlocker,
    autoHaltClearReason,
    autoHaltClearing,
    autoHaltForcedPaper,
    autoHaltLoading,
    autoHaltMessage,
    autoHaltTriggeredChecks,
    autoHaltVariant,
    autoHaltWarming,
    brokerTruthOps,
    currentAutoHalt,
    currentLiveRecovery,
    currentPayoutRecovery,
    currentSweep,
    emergencyStatus,
    emergencyStopping,
    formatAutoHaltValue,
    handleClearAutoHalt,
    handleEmergencyStop,
    handleRefreshAutoHalt,
    handleRunAutonomousSweep,
    handleSaveSweepPolicy,
    handleSweepRequest,
    isLiveLedger,
    latestPayoutAttempt,
    latestSweepAudit,
    liveRecoveryClear,
    liveRecoveryMissingCount,
    liveRecoveryStatus,
    liveTradingStatus,
    ownerConfirmAutoHaltClear,
    ownerConfirmSweep,
    payoutAttemptStatus,
    payoutConfirmBlocker,
    payoutGateAuthorized,
    payoutRecoveryLabel,
    payoutRecoveryOpen,
    setAutoHaltClearReason,
    setOwnerConfirmAutoHaltClear,
    setOwnerConfirmSweep,
    setSweepDraft,
    sweepActionMessage,
    sweepDraft,
    sweepLoading,
    sweepPayoutReady,
    sweepReady,
    sweepRequest,
    sweepRequesting,
    sweepSaving,
  } = ops;

  useEffect(() => {
    return scheduleSweepIdleWork(
      () => setBrokerTruthPanelReady(true),
      DASHBOARD_BROKER_TRUTH_PANEL_IDLE_TIMEOUT_MS,
    );
  }, []);

  useEffect(() => {
    void refreshBrokerEmergencyStatus();
  }, []);

  const providerRuntime = currentSweep?.provider_runtime ?? null;
  const payoutRuntimeReady = Boolean(currentSweep?.payout_runtime_ready);
  const payoutActionReady = payoutGateAuthorized && payoutRuntimeReady;
  const payoutActionLabel = payoutActionReady ? "Confirm Payout" : "Request Payout Setup";
  const payoutRuntimeStatus = prettyRuntimeStatus(providerRuntime?.status);
  const payoutRuntimeVariant = providerRuntimeVariant(providerRuntime?.status, payoutRuntimeReady);
  const payoutCapabilityLabel = payoutActionReady
    ? "PAYOUT READY"
    : providerRuntime?.status === "GENERAL_PAYMENT_RAIL_ONLY"
      ? "PAYOUT RAIL UNBOUND"
      : "PAYOUT SCAFFOLDED";
  const autonomousEnabled = Boolean(currentSweep?.settings?.autonomous_enabled);
  const payoutActionTitle =
    payoutConfirmBlocker ||
    (!payoutActionReady
      ? providerRuntime?.detail
        || "Payouts stay scaffolded until the provider runtime is real-money ready, owner approval is on, the destination is allowlisted, and receipts are verified."
      : undefined);
  const hasOpenPositions = (brokerEmergency?.open_position_count ?? 0) > 0;
  const hasPendingOrders = (brokerEmergency?.pending_order_count ?? 0) > 0;

  async function refreshBrokerEmergencyStatus() {
    setBrokerEmergencyBusy("refresh");
    setBrokerEmergencyMessage("");
    try {
      const result = await fetchBrokerEmergencyStatus();
      if (result) {
        setBrokerEmergency(result);
      } else {
        setBrokerEmergencyMessage("Broker emergency status is unavailable. Check API reachability and MT5 terminal state.");
      }
    } catch {
      setBrokerEmergencyMessage("Broker emergency status refresh failed. No close/cancel request was submitted.");
    } finally {
      setBrokerEmergencyBusy("");
    }
  }

  async function runBrokerEmergency(
    endpoint: "close-all" | "close-profitable" | "close-losing" | "cancel-pending",
    dryRun: boolean,
  ) {
    let confirmPhrase = "";
    if (!dryRun) {
      if (!ownerConfirmBrokerEmergency) {
        setBrokerEmergencyMessage("OWNER_BROKER_EMERGENCY_CONFIRM_REQUIRED");
        return;
      }
      const typed = window.prompt('Type exactly "CONFIRM BROKER EMERGENCY" to execute this broker emergency action.', "");
      if (typed === null) {
        setBrokerEmergencyMessage("Broker emergency confirmation canceled.");
        return;
      }
      confirmPhrase = typed;
    }
    const busyKey = `${endpoint}:${dryRun ? "dry" : "confirm"}`;
    setBrokerEmergencyBusy(busyKey);
    setBrokerEmergencyMessage("");
    try {
      const result = await runBrokerEmergencyAction(endpoint, {
        reason: dryRun ? "OWNER_DRY_RUN_BROKER_EMERGENCY" : "OWNER_CONFIRMED_BROKER_EMERGENCY",
        dryRun,
        confirmOwnerAction: !dryRun && ownerConfirmBrokerEmergency,
        confirmPhrase,
      });
      setBrokerEmergency(result);
      setBrokerEmergencyMessage(
        result.status === "CONFIRM_REQUIRED"
          ? `Type exactly "${result.need_confirmation ?? "CONFIRM BROKER EMERGENCY"}" to execute this broker emergency action.`
          : `${result.status ?? "UNKNOWN"}: ${result.next_action ?? "Broker emergency action returned."}`,
      );
    } catch {
      setBrokerEmergencyMessage(
        "Broker emergency request failed before execution confirmation. No broker emergency action was confirmed through this app; check API reachability and MT5 terminal state.",
      );
    } finally {
      setBrokerEmergencyBusy("");
    }
  }

  return (
    <GlassPanel
      title="Verified Profit Sweep"
      subtitle={currentSweep?.hard_rule ?? "Broker-confirmed closed-trade winnings only"}
      variant={sweepPayoutReady ? "info" : isLiveLedger ? "warning" : "danger"}
    >
      <div className="sweep-cockpit">
        <div className="sweep-status-row">
          <StatusChip label={isLiveLedger ? "LIVE LEDGER" : "DEMO MODE"} variant={isLiveLedger ? "success" : "paper"} size="sm" />
          <StatusChip label={activeLiveReadiness?.overall_status ?? "READINESS UNKNOWN"} variant={activeLiveReadiness?.overall_status === "READY_FOR_LIVE_EXECUTION" ? "success" : "warning"} size="sm" />
          <StatusChip label={`TRADING ${displayLiveCapabilityStatus(liveTradingStatus)}`} variant={liveCapabilityVariant(liveTradingStatus)} size="sm" />
          <StatusChip
            label={payoutCapabilityLabel}
            variant={payoutActionReady ? "success" : "warning"}
            size="sm"
          />
          <StatusChip
            label={`RAIL ${payoutRuntimeStatus}`}
            variant={payoutRuntimeVariant}
            size="sm"
          />
          <StatusChip
            label={autonomousEnabled ? "AI SWEEP ARMED" : "AI SWEEP OFF"}
            variant={autonomousEnabled ? "success" : "muted"}
            size="sm"
          />
          <StatusChip label={`RECOVERY ${liveRecoveryStatus}`} variant={liveRecoveryClear ? "success" : "danger"} size="sm" />
        </div>

        {!payoutActionReady && (
          <div className="sweep-reason-row">
            <StatusChip label="PAYMENT SETUP PENDING" variant="warning" size="sm" />
            <span>
              {providerRuntime?.detail
                || "Provider key and payout destination token are configured in Settings or Proof. Withdrawals and payouts stay disabled until a supported real provider rail, owner approval, destination allowlist, and receipt tracking are configured."}
            </span>
            <a
              className="sweep-action-button setup-link"
              href="?page=settings"
              title="Open Settings payment provider and payout destination setup"
            >
              Open Settings
            </a>
            <a
              className="sweep-action-button setup-link"
              href="?page=proof"
              title="Open Proof live and payment controls"
            >
              Open Proof
            </a>
          </div>
        )}

        <div className="dashboard-grid-3col">
          <div className="metric-stack" style={{ padding: 0 }}>
            <Metric label="Profit Available" value={moneyFmt(currentSweep?.winnings.sweepable_winnings_usd ?? 0)} mono warning={!sweepReady} />
            <Metric label="Verified Net" value={moneyFmt(currentSweep?.winnings.net_verified_winnings_usd ?? 0)} mono />
            <Metric label="Closed Trades" value={`${currentSweep?.winnings.verified_closed_trade_count ?? 0}`} mono />
          </div>
          <div className="metric-stack" style={{ padding: 0 }}>
            <Metric label="Tax Reserve" value={moneyFmt(currentSweep?.tax_reserve_usd ?? 0)} mono />
            <Metric label="Incremental Sweep" value={moneyFmt(currentSweep?.incremental_sweep_amount_usd ?? currentSweep?.sweep_amount_usd ?? 0)} mono warning={!sweepPayoutReady} />
            <Metric label="Keep in Broker" value={moneyFmt(currentSweep?.keep_in_broker_usd ?? 0)} mono />
          </div>
          <div className="metric-stack" style={{ padding: 0 }}>
            <Metric label="Sweep Status" value={currentSweep?.status ?? (sweepLoading ? "LOADING" : "UNAVAILABLE")} mono danger={!sweepPayoutReady} />
            <Metric label="Already Swept" value={moneyFmt(currentSweep?.already_swept_usd ?? 0)} mono />
            <Metric
              label="Last Withdrawal"
              value={latestPayoutAttempt ? `${shortPayoutAttemptStatus(payoutAttemptStatus)} ${formatShortTime(latestPayoutAttempt.updated_at ?? latestPayoutAttempt.created_at ?? "")}` : latestSweepAudit ? `${latestSweepAudit.action} ${formatShortTime(latestSweepAudit.timestamp)}` : "NONE"}
              mono
              danger={payoutRecoveryOpen}
            />
          </div>
        </div>

        <div className="sweep-reason-row">
          <StatusChip
            label={payoutRecoveryLabel}
            variant={payoutRecoveryVariant(payoutAttemptStatus, payoutRecoveryOpen)}
            size="sm"
          />
          <span className="mono">pending {currentPayoutRecovery?.pending_count ?? 0}</span>
          <span className="mono">key {shortAttemptKey(latestPayoutAttempt?.idempotency_key)}</span>
          <span>{currentPayoutRecovery?.next_action ?? "No payout attempt ledger has reported yet."}</span>
        </div>

        {!liveRecoveryClear && (
          <div className="sweep-reason-row">
            <StatusChip label="RECOVERY BLOCKS PAYOUT" variant="danger" size="sm" />
            <span className="mono">missing {liveRecoveryMissingCount}</span>
            <span>{sweepRequest?.live_recovery?.next_action ?? currentLiveRecovery?.next_action ?? "Live recovery must be CLEAR before verified winnings can leave the broker/account path."}</span>
          </div>
        )}

        <div className={`auto-halt-strip ${autoHaltActive ? "active" : "clear"}`}>
          <div className="auto-halt-header">
            <div className="auto-halt-title">
              <StatusChip
                label={
                  autoHaltActive
                    ? "AUTO-HALT ACTIVE"
                    : autoHaltWarming
                      ? "AUTO-HALT WARMING"
                      : currentAutoHalt
                        ? "AUTO-HALT CLEAR"
                        : "AUTO-HALT UNKNOWN"
                }
                variant={autoHaltVariant}
                size="sm"
              />
              <StatusChip
                label={autoHaltForcedPaper ? "PAPER FORCED" : "LIVE GATE MONITORED"}
                variant={autoHaltForcedPaper ? "danger" : "info"}
                size="sm"
              />
              {autoHaltTriggeredChecks.length > 0 && (
                <StatusChip label={`${autoHaltTriggeredChecks.length} TRIP`} variant="danger" size="sm" />
              )}
            </div>
            <button className="sweep-action-button" type="button" onClick={handleRefreshAutoHalt} disabled={autoHaltLoading}>
              {autoHaltLoading ? "Refreshing..." : "Check Auto-Halt"}
            </button>
          </div>

          {brokerTruthPanelReady ? (
            <Suspense fallback={<DashboardBrokerTruthOpsPanelFallback />}>
              <DashboardBrokerTruthOpsPanel ops={brokerTruthOps} />
            </Suspense>
          ) : (
            <DashboardBrokerTruthOpsPanelFallback />
          )}

          <div className="auto-halt-check-grid">
            {autoHaltChecks.length > 0 ? autoHaltChecks.map((check: any) => (
              <div className={`auto-halt-check ${check.trips_halt ? "tripped" : check.status === "OK" ? "ok" : "unknown"}`} key={check.check_id}>
                <div className="auto-halt-check-title">
                  <span>{formatAutoHaltCheckId(check.check_id)}</span>
                  <StatusChip label={check.status} variant={autoHaltCheckVariant(check.status)} size="sm" />
                </div>
                <div className="auto-halt-check-values mono">
                  <span>{formatAutoHaltValue(check.metric)}</span>
                  <span>/</span>
                  <span>{formatAutoHaltValue(check.threshold)}</span>
                </div>
                <div className="auto-halt-check-detail">{check.detail}</div>
              </div>
            )) : (
              <div className="auto-halt-empty">Auto-halt status has not reported yet.</div>
            )}
          </div>

          <div className="auto-halt-clear-row">
            <input
              className="auto-halt-reason-input"
              type="text"
              value={autoHaltClearReason}
              onChange={(event) => setAutoHaltClearReason(event.target.value)}
              aria-label="Auto-halt clear reason"
            />
            <label className="sweep-confirm-check">
              <input
                type="checkbox"
                checked={ownerConfirmAutoHaltClear}
                onChange={(event) => setOwnerConfirmAutoHaltClear(event.target.checked)}
              />
              <span>Owner Clear</span>
            </label>
            <button
              className="sweep-action-button danger"
              type="button"
              onClick={handleClearAutoHalt}
              disabled={autoHaltClearing}
              title={autoHaltClearBlocker || undefined}
            >
              {autoHaltClearing ? "Clearing..." : "Clear Auto-Halt"}
            </button>
          </div>

          <div className="auto-halt-next-action">
            {autoHaltMessage ?? currentAutoHalt?.next_action ?? "Auto-halt protects live authority when broker truth trips a breaker."}
          </div>
        </div>

        <div className="sweep-control-grid">
          <label className="sweep-control-field">
            <span className="field-label">Sweep %</span>
            <input
              className="sweep-range"
              type="range"
              min="0"
              max="100"
              step="1"
              value={sweepDraft.sweep_pct}
              onChange={(event) => setSweepDraft((draft: any) => ({ ...draft, sweep_pct: Number(event.target.value) }))}
            />
            <input
              className="sweep-number"
              type="number"
              min="0"
              max="100"
              step="1"
              value={sweepDraft.sweep_pct}
              onChange={(event) => setSweepDraft((draft: any) => ({ ...draft, sweep_pct: Number(event.target.value) }))}
            />
          </label>
          <label className="sweep-control-field">
            <span className="field-label">Tax Reserve %</span>
            <input
              className="sweep-range"
              type="range"
              min="0"
              max="100"
              step="1"
              value={sweepDraft.tax_reserve_pct}
              onChange={(event) => setSweepDraft((draft: any) => ({ ...draft, tax_reserve_pct: Number(event.target.value) }))}
            />
            <input
              className="sweep-number"
              type="number"
              min="0"
              max="100"
              step="1"
              value={sweepDraft.tax_reserve_pct}
              onChange={(event) => setSweepDraft((draft: any) => ({ ...draft, tax_reserve_pct: Number(event.target.value) }))}
            />
          </label>
          <label className="sweep-control-field compact">
            <span className="field-label">Minimum</span>
            <input
              className="sweep-number"
              type="number"
              min="0"
              step="1"
              value={sweepDraft.min_sweep_usd}
              onChange={(event) => setSweepDraft((draft: any) => ({ ...draft, min_sweep_usd: Number(event.target.value) }))}
            />
          </label>
          <label className="sweep-control-field compact">
            <span className="field-label">Daily AI Cap</span>
            <input
              className="sweep-number"
              type="number"
              min="0"
              step="1"
              value={sweepDraft.max_daily_sweep_usd}
              onChange={(event) => setSweepDraft((draft: any) => ({ ...draft, max_daily_sweep_usd: Number(event.target.value) }))}
            />
          </label>
          <label className="sweep-confirm-check">
            <input
              type="checkbox"
              checked={sweepDraft.autonomous_enabled}
              onChange={(event) => setSweepDraft((draft: any) => ({ ...draft, autonomous_enabled: event.target.checked }))}
            />
            <span>AI Autonomous Sweep</span>
          </label>
        </div>

        <div className="sweep-action-row">
          <button className="broker-risk-apply-button" type="button" onClick={handleSaveSweepPolicy} disabled={sweepSaving}>
            {sweepSaving ? "Saving..." : "Save Policy"}
          </button>
          <button className="broker-risk-apply-button" type="button" onClick={() => handleSweepRequest(false)} disabled={sweepRequesting}>
            {sweepRequesting ? "Checking..." : "Check Sweep"}
          </button>
          <label className="sweep-confirm-check">
            <input
              type="checkbox"
              checked={ownerConfirmSweep}
              onChange={(event) => setOwnerConfirmSweep(event.target.checked)}
            />
            <span>Owner Confirm</span>
          </label>
          <button
            className="sweep-action-button"
            type="button"
            onClick={() => handleSweepRequest(true)}
            disabled={sweepRequesting}
            title={payoutActionTitle}
          >
            {payoutActionLabel}
          </button>
          <button
            className="sweep-action-button"
            type="button"
            onClick={handleRunAutonomousSweep}
            disabled={sweepRequesting || !autonomousEnabled}
            title={autonomousEnabled ? "Run one AI Operator verified-profit sweep cycle" : "Arm AI Autonomous Sweep in the policy first"}
          >
            {sweepRequesting ? "Checking..." : "Run AI Sweep"}
          </button>
          <button className="sweep-action-button danger" type="button" onClick={handleEmergencyStop} disabled={emergencyStopping}>
            {emergencyStopping ? "Stopping..." : "Emergency Stop"}
          </button>
        </div>

        <div className="broker-truth-monitor-strip">
          <div className="broker-truth-monitor-header">
            <div className="auto-halt-title">
              <StatusChip label="BROKER EMERGENCY ACTIONS" variant="warning" size="sm" />
              <StatusChip
                label={brokerEmergency?.mt5_connected ? "MT5 CONNECTED" : "MT5 OFFLINE"}
                variant={brokerEmergency?.mt5_connected ? "success" : "danger"}
                size="sm"
              />
              <StatusChip
                label={`${brokerEmergency?.open_position_count ?? 0} OPEN POSITIONS`}
                variant={hasOpenPositions ? "warning" : "muted"}
                size="sm"
              />
              <StatusChip
                label={`${brokerEmergency?.pending_order_count ?? 0} PENDING ORDERS`}
                variant={hasPendingOrders ? "warning" : "muted"}
                size="sm"
              />
              <StatusChip
                label={shortBrokerEmergencyStatus(brokerEmergency?.status)}
                variant={brokerEmergencyVariant(brokerEmergency?.status)}
                size="sm"
              />
            </div>
            <div className="broker-truth-monitor-actions">
              <button className="sweep-action-button" type="button" onClick={() => void refreshBrokerEmergencyStatus()} disabled={Boolean(brokerEmergencyBusy)}>
                {brokerEmergencyBusy === "refresh" ? "Refreshing..." : "Refresh"}
              </button>
              <a
                className="sweep-action-button setup-link"
                href="?page=settings"
                title="Open the full emergency-controls coverage matrix and broker emergency surface"
              >
                Full Coverage
              </a>
            </div>
          </div>

          <div className="broker-truth-monitor-meta">
            <span className="mono">positions {brokerEmergency?.selected_position_count ?? brokerEmergency?.open_position_count ?? 0}</span>
            <span className="mono">pending {brokerEmergency?.selected_pending_order_count ?? brokerEmergency?.pending_order_count ?? 0}</span>
            <span className="mono">broker {brokerEmergency?.broker_touched ? "TOUCHED" : "NOT TOUCHED"}</span>
            <span className="mono">last {shortBrokerEmergencyAction(brokerEmergency?.action)}</span>
            <span>{brokerEmergencyMessage || brokerEmergency?.next_action || brokerEmergency?.detail || "Dry-run before any confirmed broker emergency action."}</span>
          </div>

          <div className="sweep-action-row">
            <button className="sweep-action-button" type="button" disabled={Boolean(brokerEmergencyBusy)} onClick={() => void runBrokerEmergency("close-all", true)}>
              {brokerEmergencyBusy === "close-all:dry" ? "Checking..." : "Dry-run close all"}
            </button>
            <button className="sweep-action-button" type="button" disabled={Boolean(brokerEmergencyBusy)} onClick={() => void runBrokerEmergency("close-profitable", true)}>
              {brokerEmergencyBusy === "close-profitable:dry" ? "Checking..." : "Dry-run close profitable"}
            </button>
            <button className="sweep-action-button" type="button" disabled={Boolean(brokerEmergencyBusy)} onClick={() => void runBrokerEmergency("close-losing", true)}>
              {brokerEmergencyBusy === "close-losing:dry" ? "Checking..." : "Dry-run close losing"}
            </button>
            <button className="sweep-action-button" type="button" disabled={Boolean(brokerEmergencyBusy)} onClick={() => void runBrokerEmergency("cancel-pending", true)}>
              {brokerEmergencyBusy === "cancel-pending:dry" ? "Checking..." : "Dry-run cancel pending"}
            </button>
          </div>

          <div className="sweep-action-row">
            <label className="sweep-confirm-check">
              <input
                type="checkbox"
                checked={ownerConfirmBrokerEmergency}
                onChange={(event) => setOwnerConfirmBrokerEmergency(event.target.checked)}
              />
              <span>Owner Confirm Broker Action</span>
            </label>
            <button
              className="sweep-action-button danger"
              type="button"
              disabled={Boolean(brokerEmergencyBusy) || !ownerConfirmBrokerEmergency || !hasOpenPositions}
              onClick={() => void runBrokerEmergency("close-all", false)}
              title="Submits MT5 close orders for all open positions after owner confirmation"
            >
              {brokerEmergencyBusy === "close-all:confirm" ? "Closing..." : "Close all positions"}
            </button>
            <button
              className="sweep-action-button danger"
              type="button"
              disabled={Boolean(brokerEmergencyBusy) || !ownerConfirmBrokerEmergency || !hasOpenPositions}
              onClick={() => void runBrokerEmergency("close-profitable", false)}
              title="Submits MT5 close orders only for profitable positions after owner confirmation"
            >
              {brokerEmergencyBusy === "close-profitable:confirm" ? "Closing..." : "Close profitable positions"}
            </button>
            <button
              className="sweep-action-button danger"
              type="button"
              disabled={Boolean(brokerEmergencyBusy) || !ownerConfirmBrokerEmergency || !hasOpenPositions}
              onClick={() => void runBrokerEmergency("close-losing", false)}
              title="Submits MT5 close orders only for losing positions after owner confirmation"
            >
              {brokerEmergencyBusy === "close-losing:confirm" ? "Closing..." : "Close losing positions"}
            </button>
            <button
              className="sweep-action-button danger"
              type="button"
              disabled={Boolean(brokerEmergencyBusy) || !ownerConfirmBrokerEmergency || !hasPendingOrders}
              onClick={() => void runBrokerEmergency("cancel-pending", false)}
              title="Submits MT5 cancel requests for pending orders after owner confirmation"
            >
              {brokerEmergencyBusy === "cancel-pending:confirm" ? "Cancelling..." : "Cancel pending orders"}
            </button>
          </div>

          <div className="control-field-desc" style={{ marginTop: 2 }}>
            {brokerEmergency?.claim_boundary || "These actions can close positions or cancel pending orders. Dry-run first; live broker mutations require owner confirmation and a typed phrase."}
          </div>
        </div>

        <div className="sweep-reason-row">
          <span>{sweepActionMessage ?? sweepRequest?.detail ?? currentSweep?.reason ?? "Sweep state unavailable"}</span>
          {autonomousSweep?.status && <span className="mono">AI {autonomousSweep.status}</span>}
          {emergencyStatus && <span className="mono">{emergencyStatus}</span>}
        </div>
      </div>
    </GlassPanel>
  );
}

function scheduleSweepIdleWork(callback: () => void, timeoutMs: number): () => void {
  const idleWindow = window as IdleSchedulerWindow;
  if (idleWindow.requestIdleCallback) {
    const id = idleWindow.requestIdleCallback(callback, { timeout: timeoutMs });
    return () => idleWindow.cancelIdleCallback?.(id);
  }

  const id = window.setTimeout(callback, timeoutMs);
  return () => window.clearTimeout(id);
}

function DashboardBrokerTruthOpsPanelFallback() {
  return (
    <GlassPanel title="Broker Truth + W.A.S.T.E Controls" subtitle="Syncing delayed operations controls" variant="info">
      <div className="dashboard-grid-3col">
        <div className="metric-stack" style={{ padding: 0 }}>
          <Metric label="MT5 Data" value="SYNCING" mono warning />
          <Metric label="W.A.S.T.E Loop" value="HEADER LIVE" mono />
        </div>
        <div className="metric-stack" style={{ padding: 0 }}>
          <Metric label="Real Candle Probe" value="QUEUED" mono />
          <Metric label="Broker Truth" value="SYNCING" mono warning />
        </div>
        <div className="metric-stack" style={{ padding: 0 }}>
          <Metric label="Dry Run" value="OWNER GATED" mono warning />
          <Metric label="Broker Touch" value="BLOCKED UNTIL ACCEPT" mono warning />
        </div>
      </div>
    </GlassPanel>
  );
}

function Metric({ label, value, mono, danger, warning }: { label: string; value: string; mono?: boolean; danger?: boolean; warning?: boolean }) {
  return (
    <div className="dashboard-metric">
      <span className="field-label">{label}</span>
      <span className={`field-value ${mono ? "mono" : ""}`} style={{ color: danger ? "var(--danger)" : warning ? "var(--warning)" : undefined }}>{value}</span>
    </div>
  );
}

function moneyFmt(value: number): string {
  return `$${value.toFixed(2)}`;
}

function formatShortTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatAutoHaltCheckId(value: string): string {
  const labels: Record<string, string> = {
    max_account_drawdown_pct: "Max Drawdown",
    max_consecutive_losses: "Loss Streak",
    live_vs_paper_divergence_pct: "Live vs Paper",
    broker_truth_reconciliation: "Broker Truth",
    mt5_account_identity_matches_config: "MT5 Account Identity",
  };
  return labels[value] ?? value.replace(/_/g, " ");
}

function shortPayoutAttemptStatus(status: string): string {
  return status.replace(/^PAYOUT_/, "").replace(/_/g, " ");
}

function shortAttemptKey(value?: string | null): string {
  if (!value) return "NONE";
  return value.length <= 18 ? value : `${value.slice(0, 9)}...${value.slice(-6)}`;
}

function payoutRecoveryVariant(status: string, hasPendingRecovery: boolean): ChipVariant {
  if (hasPendingRecovery || status === "RECOVERY_REQUIRED") return "danger";
  if (status === "SETTLED") return "success";
  if (status === "FAILED" || status === "BLOCKED") return "warning";
  if (status === "RESERVED" || status === "PENDING") return "danger";
  return "muted";
}

function displayLiveCapabilityStatus(status: string | null | undefined): string {
  const normalized = String(status ?? "").toUpperCase();
  if (normalized.includes("PAYMENT") && isOwnerPendingStatus(normalized)) return "PAYMENT SETUP PENDING";
  if (normalized === "NOT AUTHORIZED") return "OWNER PENDING";
  if (isOwnerPendingStatus(normalized)) return "OWNER PENDING";
  return status || "UNKNOWN";
}

function liveCapabilityVariant(status: string | null | undefined): ChipVariant {
  const normalized = String(status ?? "").toUpperCase();
  if (normalized === "AUTHORIZED" || normalized === "PASSED") return "success";
  if (isOwnerPendingStatus(normalized) || normalized === "OPEN" || normalized === "NOT AUTHORIZED") return "warning";
  if (normalized === "MISMATCH" || normalized.includes("FAILED")) return "danger";
  return "muted";
}

function isOwnerPendingStatus(status: string | null | undefined): boolean {
  const normalized = String(status ?? "").toUpperCase();
  return normalized.includes("NOT LICENSED") || normalized.includes("CURRENTLY NOT LICENSED");
}

function prettyRuntimeStatus(status: string | null | undefined): string {
  return String(status ?? "UNKNOWN").replace(/_/g, " ");
}

function providerRuntimeVariant(status: string | null | undefined, ready: boolean): ChipVariant {
  if (ready) return "success";
  const normalized = String(status ?? "").toUpperCase();
  if (normalized === "UNSUPPORTED_PROVIDER") return "danger";
  if (normalized === "GENERAL_PAYMENT_RAIL_ONLY" || normalized === "BROKER_PROVIDER_CONFIG_MISSING") return "warning";
  if (normalized === "SIMULATED_ONLY") return "info";
  if (normalized === "CREDENTIALS_MISSING" || normalized === "NOT_CONFIGURED") return "warning";
  return "muted";
}

function shortBrokerEmergencyStatus(status: string | null | undefined): string {
  return String(status ?? "NOT RUN")
    .replace(/^BROKER_/, "")
    .replace(/_/g, " ");
}

function shortBrokerEmergencyAction(action: string | null | undefined): string {
  return String(action ?? "STATUS")
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function brokerEmergencyVariant(status: string | null | undefined): ChipVariant {
  const normalized = String(status ?? "").toUpperCase();
  if (normalized === "EXECUTED" || normalized === "READY") return "success";
  if (normalized === "DRY_RUN") return "info";
  if (normalized === "CONFIRM_REQUIRED" || normalized === "PARTIAL") return "warning";
  if (normalized === "MT5_NOT_CONNECTED" || normalized.includes("FAILED") || normalized.includes("ERROR")) return "danger";
  return "muted";
}

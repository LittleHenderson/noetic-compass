/* ── CAS Forex — Settings & Owner Control ── */

import { useEffect, useState } from "react";
import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import { EdgeThresholdControl } from "../components/EdgeThresholdControl";
import { MoneyMovementSetupStatus } from "../components/MoneyMovementSetupStatus";
import { NotificationSubscriptionPanel } from "../components/NotificationSubscriptionPanel";
import { WebhookSubscriptionPanel } from "../components/WebhookSubscriptionPanel";
import { Mt4BridgePanel } from "../components/Mt4BridgePanel";
import { brokerPortalInfo } from "../util/brokerPortal";
import { describeReconciliationMovementTruth } from "../util/movementSource";
import "../components/SelectorChips.css";
import {
  getApiBase,
  resetApiBase,
  setApiBase,
  updateOwnerControl,
  fetchRiskControl,
  fetchRiskControlAudit,
  previewRiskControl,
  previewResetRiskControl,
  updateRiskControl,
  resetRiskControl,
  type RiskControlState,
  type RiskControlAssessment,
  type RiskControlPatch,
  fetchAiControlAuthority,
  fetchAiControlAuthorityAudit,
  type AiControlAuthorityState,
  type ControlAuditRow,
  fetchCriticalNotificationAudit,
  fetchCriticalNotificationReadiness,
  testCriticalNotificationDelivery,
  type CriticalNotificationAuditRow,
  type CriticalNotificationReadiness,
  fetchLiveEnable,
  updateLiveEnable,
  resetLiveEnable,
  type LiveEnableState,
  type LiveEnableKey,
  fetchAuthorization,
  updateAuthorization,
  type AuthorizationState,
  type AuthorizationPatch,
  type OwnerAuthorityModel,
  fetchBrokerControl,
  type BrokerControlState,
  fetchBrokerRealityReview,
  updateBrokerRealityReview,
  resetBrokerRealityReview,
  type BrokerRealityReview,
  type BrokerRealityUpdate,
  fetchLivePilotPolicy,
  updateLivePilotPolicy,
  resetLivePilotPolicy,
  type LivePilotPolicy,
  type LivePilotUpdate,
  fetchBrokerTruthRecoveryPacket,
  fetchLiveMoneyProgressionPacket,
  fetchWasteDirectionReviewPacket,
  fetchWasteDirectionLearningLedger,
  fetchWasteDirectionOutcomeBinding,
  fetchWastePaperSampleCollector,
  fetchWastePaperSampleCollectorScheduler,
  runWastePaperSampleCollectorSchedulerOnce,
  startWastePaperSampleCollectorScheduler,
  stopWastePaperSampleCollectorScheduler,
  fetchWasteAdaptationPromotionRule,
  fetchWasteAdaptationPlan,
  fetchWasteAdaptationApplyPreview,
  fetchWasteAdaptationOwnerReview,
  recordWasteAdaptationOwnerReview,
  resetWasteAdaptationOwnerReview,
  fetchWasteAdaptationPaperApply,
  recordWasteAdaptationPaperApply,
  resetWasteAdaptationPaperApply,
  fetchBrokerTruthMonitorStatus,
  fetchLiveRecoveryStatus,
  fetchOrderAttemptAudit,
  fetchOrderAttemptRecoveryPacket,
  fetchTerminalReceiptRecoveryPacket,
  fetchAccountReconciliation,
  runBrokerTruthMonitorOnce,
  startBrokerTruthMonitor,
  stopBrokerTruthMonitor,
  runTerminalReceiptArchiveAction,
  runTerminalReceiptRecoveryRefreshAction,
  reconcileUnresolvedOrderAttempt,
  acceptLiveRecovery,
  resetLiveRecovery,
  type LiveRecoveryReport,
  type BrokerTruthMonitorStatus,
  type BrokerTruthRecoveryPacket,
  type LiveMoneyProgressionPacket,
  type WasteDirectionReviewPacket,
  type WasteDirectionLearningLedger,
  type WasteDirectionOutcomeBinding,
  type WastePaperSampleCollector,
  type WastePaperSampleCollectorScheduler,
  type WasteAdaptationPromotionRule,
  type WasteAdaptationPlan,
  type WasteAdaptationApplyPreview,
  type WasteAdaptationOwnerReview,
  type WasteAdaptationPaperApply,
  type OrderAttemptAuditAttempt,
  type OrderAttemptAuditStatus,
  type OrderAttemptRecoveryPacket,
  type TerminalReceiptArchiveAction,
  type TerminalReceiptRecoveryRefreshAction,
  type TerminalReceiptRecoveryPacket,
  fetchMt4Control,
  type MT4ControlState,
  fetchSecurityPosture,
  type SecurityPosture,
  fetchAiHedgeSupervision,
  type AiHedgeSupervisionReport,
  fetchAiHedgeManagementHandoff,
  type AiHedgeManagementHandoffReport,
  runAiHedgeManagementAction,
  type AiHedgeManagementExecutionResult,
  fetchLegalReviewReadiness,
  fetchLegalReviewControl,
  updateLegalReviewControl,
  resetLegalReviewControl,
  type LegalReviewReadinessReport,
  type LegalReviewControlReport,
  fetchProfessionalReadiness,
  type ProfessionalReadinessMatrix,
  fetchEconomicCalendarFeed,
  type EconomicCalendarFeedReport,
  fetchOperationalReadiness,
  fetchRuntimeTopology,
  updateExternalMonitoringConfig,
  resetExternalMonitoringConfig,
  fetchEmergencyControls,
  fetchBrokerEmergencyStatus,
  runBrokerEmergencyAction,
  createOperatorBackup,
  type OperationalReadinessReport,
  type RuntimeTopologyStatus,
  type EmergencyControlsReport,
  type BrokerEmergencyActionResult,
  fetchMt5SymbolDiagnostics,
  type BrokerSymbolDiagnostics,
} from "../data/api";
import type { AccountReconciliationReport, DashboardState } from "../types/evidence";
import { ControlField } from "../components/settings/ControlField";
import { ProfessionalClaimsPanel } from "../components/settings/ProfessionalClaimsPanel";
import { SpecContextPanel } from "../components/settings/SpecContextPanel";
import { BypassLaunchGatePanel, PublicLaunchGatePanel } from "../components/settings/LaunchGatePanels";
import { UILayoutContractPanel } from "../components/settings/UILayoutContractPanel";

interface SettingsPageProps {
  state: DashboardState;
}

const CONTROL_MODES = [
  { value: "DENY", label: "Lockdown" },
  { value: "NOTIFY_ONLY", label: "Signal" },
  { value: "LIMITED_PAPER", label: "Limited Paper" },
  { value: "PAPER_AUTO", label: "Paper Auto" },
  { value: "AI_FULL_AUTO_PAPER", label: "Paper Autopilot" },
  { value: "LIVE_AUTO", label: "Live Confirm" },
  { value: "AI_FULL_AUTO_LIVE_REQUESTED", label: "Live Autopilot Request" },
] as const;

const LIVE_MONEY_PROGRESS_REFRESH_EVENT = "cas-forex-live-money-refresh";
const LIVE_MONEY_POST_WRITE_RETRY_DELAYS_MS = [1_500, 4_000, 8_000] as const;

function isLiveMoneyProgressionWarming(packet: LiveMoneyProgressionPacket | null | undefined): boolean {
  return packet?.status === "WARMING" || packet?.cache_status === "warming" || packet?.cache_refreshing === true;
}

function emitLiveMoneyProgressionRefresh() {
  window.dispatchEvent(new Event(LIVE_MONEY_PROGRESS_REFRESH_EVENT));
}

export function SettingsPage({ state }: SettingsPageProps) {
  const [ownerControlState, setOwnerControlState] = useState(state.ownerControl);
  const [ownerControlBusy, setOwnerControlBusy] = useState("");
  const [ownerControlStatus, setOwnerControlStatus] = useState("");
  useEffect(() => {
    setOwnerControlState(state.ownerControl);
  }, [state.ownerControl]);
  const oc = ownerControlState ?? state.ownerControl;
  const ab = state.authorityBoundary;
  const ai = state.aiModel;
  const pcbaGuardEnabled = ai?.pcba_guard_enabled ?? true;
  const brokers = state.brokerCandidates ?? [];

  // Live, stable sources for the status fields below (NOT the flaky MT5 IPC):
  // owner-flag acks + live_mode from live-enable, platform from broker-control,
  // and the EA file-link from the MT4 bridge. The authoritative live status
  // stays ab.live_trading_status (owner-flag driven; a demo never grants live authority).
  const [le, setLe] = useState<LiveEnableState | null>(null);
  const [bc, setBc] = useState<BrokerControlState | null>(null);
  const [mt4, setMt4] = useState<MT4ControlState | null>(null);
  useEffect(() => {
    void fetchLiveEnable().then((s) => { if (s) setLe(s); });
    void fetchBrokerControl().then((s) => { if (s) setBc(s); });
    void fetchMt4Control().then((s) => { if (s) setMt4(s); });
  }, []);

  const liveAuthorized = ab?.live_trading_status === "AUTHORIZED";
  const liveBrokerValue = liveAuthorized ? "AUTHORIZED" : "PAPER / DEMO";
  const proofDays = state.uiReadiness?.completed_trading_days ?? 0;
  const autonomyLadder = oc?.autonomy_ladder ?? [];
  async function saveOwnerMode(mode: (typeof CONTROL_MODES)[number]["value"]) {
    setOwnerControlBusy(mode);
    setOwnerControlStatus("");
    try {
      const next = await updateOwnerControl({ mode });
      setOwnerControlState(next);
      setOwnerControlStatus(
        mode === "AI_FULL_AUTO_LIVE_REQUESTED" || mode === "LIVE_AUTO"
          ? "Owner live-stage request saved. Live orders still re-check live authority, broker credentials, emergency stop, edge, and risk at action time."
          : `Owner mode saved: ${mode}.`,
      );
    } catch {
      setOwnerControlStatus("Couldn't save owner mode - is the API reachable?");
    } finally {
      setOwnerControlBusy("");
    }
  }

  return (
    <div className="settings-page">
      <MobileApiPanel />
      <SecurityPosturePanel />
      <ProfessionalClaimsPanel />
      <SpecContextPanel />
      <AiHedgeSupervisionPanel />
      <AiHedgeManagementHandoffPanel />
      <LegalReviewReadinessPanel />
      <ProfessionalReadinessPanel />
      <PublicLaunchGatePanel />
      <BypassLaunchGatePanel />
      <UILayoutContractPanel />
      <EconomicCalendarPanel />
      <OperationalReadinessPanel />
      <RuntimeTopologyPanel />
      <EmergencyControlsPanel />
      <BrokerSymbolDiagnosticsPanel />

      {/* ── Min edge to trade — owner integrity dial (local only) ── */}
      <EdgeThresholdPanel />
      <AiControlAuthorityPanel />

      {/* ── Go Live — owner switches (turn the live-trading gate flags ON) ── */}
      <GoLivePanel />

      {/* ── Owner risk control — set any cap, or remove it ── */}
      <RiskControlPanelModern />
      <ControlAuditTrailPanel />

      {/* ── MT4 EA mailbox — the stable real-order route ── */}
      <Mt4BridgePanel />

      <BrokerFundingHandoffPanel brokerReality={state.brokerReality} />

      {/* ── Notification Subscriptions (Web Push) ── */}
      <NotificationSubscriptionPanel />

      {/* ── Webhook Subscriptions ── */}
      <WebhookSubscriptionPanel />
      <CriticalNotificationAuditPanel />

      {/* ── Owner Control Surface ── */}
      <GlassPanel title="Owner Control Policy" subtitle="Risk caps, AI autonomy, concurrent trades">
        <div className="owner-control-surface">
          {/* Mode Selection */}
          <div className="control-section">
            <h4 className="control-section-title">Autonomy Mode</h4>
            <div className="selector-chips">
              {CONTROL_MODES.map((m) => {
                const isActive = oc?.mode === m.value;
                const isLive = m.value === "LIVE_AUTO" || m.value === "AI_FULL_AUTO_LIVE_REQUESTED";
                return (
                  <button
                    key={m.value}
                    className={`selector-chip ${isActive ? "active" : ""}`}
                    disabled={ownerControlBusy === m.value}
                    style={isLive ? { borderColor: "var(--danger-dim)" } : undefined}
                    onClick={() => void saveOwnerMode(m.value)}
                    title={`${m.label}${isLive ? " - live standby until owner authority and broker/provider setup are on" : ""}`}
                  >
                    {m.label}
                    {isLive && <span style={{ color: "var(--danger)", marginLeft: 4, fontSize: "0.75rem" }}>BLOCKED</span>}
                  </button>
                );
              })}
            </div>
            {ownerControlStatus && (
              <div
                className="control-field-desc"
                style={{ marginTop: 8, color: ownerControlStatus.startsWith("Couldn't") ? "var(--danger)" : "var(--success)" }}
              >
                {ownerControlStatus}
              </div>
            )}
            {oc?.live_requested && (
              <div style={{ marginTop: 8, padding: "6px 10px", background: "var(--warning-dim)", borderRadius: "var(--radius-sm)", fontSize: "0.8125rem", color: "var(--warning)" }}>
                {oc.current_autonomy_stage_label ?? oc.mode}: owner requested a live stage; live trading, broker ACCEPT, and payment movement stay under owner switches, credentials, and action-time checks.
              </div>
            )}
            <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
              <table className="data-table ai-dial-table">
                <thead>
                  <tr>
                    <th>Stage</th>
                    <th>Mode</th>
                    <th>Authority</th>
                    <th>Effect</th>
                  </tr>
                </thead>
                <tbody>
                  {autonomyLadder.map((step) => {
                    const isCurrent = step.modes.includes(oc?.mode as any);
                    return (
                      <tr key={step.stage}>
                        <td>
                          <StatusChip
                            label={step.label}
                            variant={isCurrent ? "success" : step.can_request_live_trades ? "warning" : "muted"}
                            size="sm"
                          />
                        </td>
                        <td className="mono">{step.modes.join(", ")}</td>
                        <td>{step.order_authority}</td>
                        <td>{step.effect}</td>
                      </tr>
                    );
                  })}
                  {autonomyLadder.length === 0 && (
                    <tr>
                      <td colSpan={4}>Staged autonomy ladder is loading.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <div className="control-field-desc" style={{ marginTop: 8 }}>
              {oc?.staged_autonomy_summary ?? "Each autonomy stage maps to concrete execution authority and action-time checks."}
            </div>
          </div>

          {/* Risk Caps */}
          <div className="control-section">
            <h4 className="control-section-title">Risk Caps</h4>
            <div className="control-grid">
              <ControlField label="Max Loss Cap" value={`${oc?.max_loss_cap_pct ?? 10}%`} description="Maximum account loss before all trading stops. Owner can set any positive percentage." />
              <ControlField label="Max Concurrent Trades" value={`${oc?.max_concurrent_trades ?? 3}`} description="Maximum simultaneous paper trades. Owner can set 1-15." mono />
              <ControlField label="AI Autonomy" value={oc?.ai_autonomy_enabled ? "ENABLED (PAPER ONLY)" : "DISABLED"} description="When enabled, AI can select risk cap, lot size, and concurrency from surviving scenarios." />
              <ControlField label="Owner Control" value="OWNER-CONTROLLED" description="Research/paper automation can run now; live-money capabilities require explicit owner enable flags, credentials, and provider config." />
              <ControlField label="Live Trading" value={liveBrokerValue} description={liveAuthorized ? "Owner-authorized live gate." : "Paper/demo automation can run; live broker money is a separate owner gate."} />
            </div>
          </div>
        </div>
      </GlassPanel>


      {/* ── Authority Boundary ── */}
      <GlassPanel title="Live-Money Boundary" subtitle="Paper/demo can run; external money actions stay owner-gated" variant="warning">
        <div className="control-grid">
          <ControlField label="Operating Mode" value={ab?.operating_mode ?? "READ_ONLY_PAPER_RESEARCH"} mono />
          <ControlField label="Trading Edge" value={ab?.trading_edge_status ?? "OPEN"} description="Paper/demo learning can continue while the live edge remains under review." />
          <ControlField label="Live Trading Gate" value={ownerGateDisplay(ab?.live_trading_status)} description={ownerGateDescription(ab?.live_trading_status)} />
          <ControlField label="Broker ACCEPT Gate" value={ownerGateDisplay(ab?.broker_accept_status)} description={ownerGateDescription(ab?.broker_accept_status)} />
          <ControlField label="Auto-Deposit Gate" value={ownerGateDisplay(ab?.auto_deposit_status)} description={ownerGateDescription(ab?.auto_deposit_status)} />
          <ControlField label="Debit/Card/Bank Gate" value={ownerGateDisplay(ab?.debit_card_bank_movement_status)} description={ownerGateDescription(ab?.debit_card_bank_movement_status)} />
          <ControlField label="Payout Automation Gate" value={ownerGateDisplay(ab?.payout_automation_status)} description={ownerGateDescription(ab?.payout_automation_status)} />
          <ControlField label="Can Move Money" value={ab?.can_move_money ? "YES" : "NO"} danger={Boolean(ab?.can_move_money)} />
          <ControlField label="Live Execution Runtime" value={ab?.live_execution_runtime_locked === false ? "OWNER-AUTHORIZED" : "PENDING OWNER ENABLE"} description="Broker bridge permits live execution only when owner flag + credentials + broker config are present." />
        </div>
        <div style={{ marginTop: 12, padding: "8px 12px", background: "var(--warning-dim)", borderRadius: "var(--radius-sm)", fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
          Backend boundary: {ownerFacingBoundary(ab?.claim_boundary ?? "Research/paper cockpit runs now. Live-money capabilities are owner-controlled and become AUTHORIZED only when owner flags, credentials, and provider config are present.")}
        </div>
      </GlassPanel>

      {/* ── Path to Authorize Everything — functional owner toggles ── */}
      <AuthorizePanel />

      {/* ── AI Model Control ── */}
      <GlassPanel title="AI Model Control" subtitle="Open-weight/frontier LLMs under CAS Harness + PCBA">
        <div className="control-grid">
          <ControlField label="Enabled" value={ai?.enabled ? "YES" : "NO"} danger={!ai?.enabled} />
          <ControlField label="Backend" value={ai?.backend ?? "ollama"} mono />
          <ControlField label="Model" value={ai?.model_name ?? "deepseek-r1:latest"} mono />
          <ControlField label="API Key Present" value={ai?.has_api_key ? "YES" : "NO"} danger={!ai?.has_api_key && (ai?.backend ?? "").startsWith("frontier_")} />
          <ControlField label="Control Plane" value={ai?.control_plane ?? "CAS_HARNESS_PCBA"} mono />
          <ControlField label="PCBA Guard" value={pcbaGuardEnabled ? "ENABLED" : "DISABLED"} danger={!pcbaGuardEnabled} />
        </div>
        <div style={{ marginTop: 12, padding: "8px 12px", background: "var(--panel-dim)", borderRadius: "var(--radius-sm)", fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
          {ai?.authority_boundary ?? "AI may autonomously trade and initiate configured money movement only after owner delegation, through runtime_gates plus dispatch/provider gates."}
        </div>
      </GlassPanel>

      {/* ── Broker Candidates ── */}
      <GlassPanel title="Broker Candidate Matrix" subtitle="Owner-requested broker routes; live use remains runtime-gated">
        <div className="control-grid">
          {brokers.slice(0, 12).map((b) => (
            <ControlField
              key={b.broker_id}
              label={b.display_name}
              value={b.verification_status}
              danger
              description={`${b.owner_research_leverage_note} Live use: ${b.live_use_status}.`}
            />
          ))}
        </div>
      </GlassPanel>

      {/* ── Compounding Thresholds ── */}
      <BrokerRealityPanel initialReview={state.brokerReality} />
      <LivePilotPanel initialPolicy={state.livePilot} />
      <LiveRecoveryPanel
        initialReport={state.liveRecovery}
        initialAudit={state.orderAttemptAudit}
        initialRecoveryPacket={state.orderAttemptRecoveryPacket}
        initialTerminalReceiptPacket={state.terminalReceiptRecoveryPacket}
        initialBrokerTruth={state.brokerTruthMonitor}
        initialLiveMoneyProgression={state.liveMoneyProgression}
        initialWasteDirectionReview={state.wasteDirectionReview}
        initialWasteDirectionLearning={state.wasteDirectionLearning}
        initialWasteDirectionOutcomeBinding={state.wasteDirectionOutcomeBinding}
        initialWastePaperSampleCollector={state.wastePaperSampleCollector}
        initialWastePaperSampleCollectorScheduler={state.wastePaperSampleCollectorScheduler}
        initialWasteAdaptationPromotionRule={state.wasteAdaptationPromotionRule}
        initialWasteAdaptationPlan={state.wasteAdaptationPlan}
        initialWasteAdaptationApplyPreview={state.wasteAdaptationApplyPreview}
        initialWasteAdaptationOwnerReview={state.wasteAdaptationOwnerReview}
        initialWasteAdaptationPaperApply={state.wasteAdaptationPaperApply}
      />

      <GlassPanel title="Compounding Thresholds" subtitle="Adaptive compounding configuration">
        <div className="control-grid">
          <ControlField label="Max Basket Positions" value="15" mono description="Maximum positions allowed in a single basket" />
          <ControlField label="Base Lot Size" value="0.01" mono description="Starting lot size for new positions" />
          <ControlField label="Compound Lot Multiplier" value="1.0x" mono description="Multiplier applied when adding to a winner" />
          <ControlField label="Min Compound Profit R" value="0.5R" mono description="Minimum profit (in R) before compounding allowed" />
          <ControlField label="Partial TP R" value="2.0R" mono description="R-multiple at which partial take-profit triggers" />
          <ControlField label="Close Basket Loss R" value="-1.0R" mono description="R-multiple at which basket auto-closes" />
          <ControlField label="Min Add Score" value="55%" mono description="Minimum directional conviction score to add to position" />
          <ControlField label="Min Evidence Score" value="0.50" mono description="Minimum evidence score for any action" />
          <ControlField label="Adaptive SL Mult" value="1.5x" mono description="Stop-loss multiplier for adaptive positions" />
          <ControlField label="Adaptive TP Mult" value="3.0x" mono description="Take-profit multiplier for adaptive positions" />
        </div>
      </GlassPanel>

      {/* ── Risk Defaults ── */}
      <GlassPanel title="Risk Defaults">
        <div className="control-grid">
          <ControlField label="Max Daily DD" value="2.0%" />
          <ControlField label="Max Weekly DD" value="5.0%" />
          <ControlField label="Max Position" value="0.1 lots" mono />
          <ControlField label="Max Risk / Trade" value="0.5%" />
          <ControlField label="Max Correlated Exposure" value="0.2 lots" mono />
          <ControlField label="Macro Blackout" value="15 min before / after" />
          <ControlField label="Sweep Mode" value="DRY_RUN" />
          <ControlField label="Transfer Boundary" value="INTERNAL_LEDGER_ONLY" />
        </div>
      </GlassPanel>

      {/* ── Account & Legal Gates ── */}
      <GlassPanel title="Account & Legal Gates" variant="danger">
        <div className="legal-gates">
          <LegalGate label="CAS_FOREX_ACCOUNT_AUTH_ACK" met={!!le?.resolved.personal_account_ack} detail={le?.resolved.personal_account_ack ? "Account authorization acknowledged (Go Live panel)" : "Account authorization acknowledgment required — set it in Go Live"} />
          <LegalGate label="CAS_FOREX_SOURCE_OF_FUNDS_ACK" met={!!le?.resolved.no_pooled_capital_ack} detail={le?.resolved.no_pooled_capital_ack ? "Source-of-funds / no-pooled-capital acknowledged (Go Live panel)" : "Source-of-funds acknowledgment required — set it in Go Live"} />
          <LegalGate label="Account Type" met={false} detail="Not verified — required before live eligibility" />
          <LegalGate label="Broker Terminal Proof" met={proofDays >= 30} detail={`30-day paper proof (${proofDays}/30 days)`} />
          <LegalGate label="WORM Evidence Anchoring" met={false} detail="UNAVAILABLE — local hash chain only" />
        </div>
        <div style={{ marginTop: 12, padding: "8px 12px", background: "var(--danger-dim)", borderRadius: "var(--radius-sm)", fontSize: "0.8125rem", color: "var(--danger)" }}>
          Live/payment paths are owner-controlled. They become AUTHORIZED only when the matching owner flag, credentials, broker/payment provider config, and account acknowledgments are present.
        </div>
      </GlassPanel>

      {/* ── Broker Settings ── */}
      <GlassPanel title="Broker Configuration">
        <div className="control-grid">
          <ControlField label="Dispatch Platform" value={(bc?.platform ?? "auto").toUpperCase()} mono description="Which broker route the dispatch loop uses (Broker Control / MT4 panel)." />
          <ControlField label="MT5 Terminal" value={le?.resolved.live_mode ? "Live" : "Demo"} description="Reflects the live_mode owner flag, not the terminal connection." />
          <ControlField label="MT4 Mailbox" value={mt4 ? (mt4.enabled ? `ON · ${mt4.mailbox_dir}` : "OFF") : "—"} mono />
          <ControlField label="MT4 EA Link" value={mt4 ? (mt4.enabled ? mt4.link_status : "ROUTE OFF") : "—"} danger={!!(mt4?.enabled && mt4.link_status !== "LIVE")} description="Stable file-based EA heartbeat (not the flaky MT5 IPC)." />
          <ControlField label="Live Broker" value={liveBrokerValue} description="Demo/paper is the active lane until the owner-authorized live broker gate is complete." />
        </div>
      </GlassPanel>
    </div>
  );
}

function BrokerFundingHandoffPanel({ brokerReality }: { brokerReality?: BrokerRealityReview }) {
  const [reconciliation, setReconciliation] = useState<AccountReconciliationReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const brokerPortal = brokerPortalInfo(
    brokerReality?.broker_id,
    brokerReality?.broker_display_name,
    brokerReality?.broker_website,
  );

  async function syncBrokerSnapshot() {
    setBusy(true);
    setStatus("");
    try {
      const report = await fetchAccountReconciliation(true);
      setReconciliation(report);
      setStatus(
        report
          ? "Broker snapshot sync completed. CAS can now compare account balance/equity against broker evidence."
          : "Broker snapshot sync returned no report.",
      );
    } catch {
      setStatus("Couldn't sync broker snapshot - confirm the API and terminal/broker receipt path are reachable.");
    } finally {
      setBusy(false);
    }
  }

  const snapshot = reconciliation?.broker_snapshot_initial_investment_usd;
  const blockerCount = reconciliation?.blockers?.length ?? 0;
  const syncStatus = reconciliation?.overall_status ?? "READY";
  const statusVariant = syncStatus === "RECONCILIATION_FAILED"
    ? "danger"
    : syncStatus === "RECONCILED_WITH_WARNINGS"
      ? "warning"
      : "info";
  const movementTruth = describeReconciliationMovementTruth(reconciliation);

  return (
    <GlassPanel title="Broker Funding Handoff" subtitle="Fund at the broker portal; CAS verifies the broker snapshot after funding">
      <div className="control-grid">
        <div className="control-field">
          <div className="control-field-header">
            <span className="field-label">Funding Route</span>
            <StatusChip label="BROKER PORTAL" variant="info" size="sm" />
          </div>
          <div className="control-field-desc">{brokerPortal.label} client portal: KYC, deposits, withdrawals, and account funding.</div>
        </div>
        <div className="control-field">
          <div className="control-field-header">
            <span className="field-label">CAS Custody</span>
            <StatusChip label="NO RAW BANK/CARD STORAGE" variant="success" size="sm" />
          </div>
          <div className="control-field-desc">CAS reads broker/terminal evidence after funding; the broker/provider handles payment details.</div>
        </div>
        <div className="control-field">
          <div className="control-field-header">
            <span className="field-label">Broker Snapshot</span>
            <StatusChip label={syncStatus} variant={statusVariant} size="sm" />
          </div>
          <div className="control-field-desc">
            {snapshot != null
              ? `Broker snapshot balance/equity seed: $${snapshot.toFixed(2)}.`
              : "Run sync after broker funding and terminal receipt/account snapshot are visible."}
          </div>
        </div>
        <div className="control-field">
          <div className="control-field-header">
            <span className="field-label">Movement Feed</span>
            <StatusChip label={movementTruth.feedLabel} variant={movementTruth.feedTone} size="sm" />
          </div>
          <div className="control-field-desc">
            {movementTruth.detail
              ? `Price source: ${movementTruth.statusLabel}. ${movementTruth.detail}`
              : "Broker snapshot sync has not reported canonical movement-source truth yet."}
          </div>
        </div>
        <div className="control-field">
          <div className="control-field-header">
            <span className="field-label">Blockers</span>
            <StatusChip label={`${blockerCount}`} variant={blockerCount ? "warning" : "success"} size="sm" />
          </div>
          <div className="control-field-desc">
            {blockerCount ? reconciliation?.blockers.slice(0, 2).join("; ") : "No broker-sync blockers loaded in this panel."}
          </div>
        </div>
      </div>
      <div className="mobile-api-row" style={{ marginTop: 12 }}>
        <a className="mobile-api-button" href={brokerPortal.url} target="_blank" rel="noreferrer">
          Open Broker Portal
        </a>
        <button className="mobile-api-button ghost" type="button" disabled={busy} onClick={() => void syncBrokerSnapshot()}>
          {busy ? "Syncing..." : "Sync Broker Snapshot"}
        </button>
      </div>
      {status && (
        <div
          className="control-field-desc"
          style={{ marginTop: 8, color: status.startsWith("Couldn't") ? "var(--danger)" : "var(--success)" }}
        >
          {status}
        </div>
      )}
      <div className="control-field-desc" style={{ marginTop: 8 }}>
        Funding is external custody; CAS uses the verified broker snapshot for account reconciliation, risk sizing, and readiness checks.
      </div>
    </GlassPanel>
  );
}

function AuthorityModelStrip({ model }: { model?: OwnerAuthorityModel }) {
  const controls = model?.authority_controls?.join(" + ") || "owner switches + Owner ACCEPT buttons";
  const checks = model?.action_time_requirements?.slice(0, 3).join("; ")
    || "broker/provider, edge, and risk checks";
  const delegated = (model?.ai_autonomous_execution_authority ?? "").includes("OWNER_DELEGATED");
  const perOrder = model?.per_order_confirmation_required ?? false;
  return (
    <div className="control-grid" style={{ marginBottom: 14 }}>
      <ControlField
        label="Authority"
        value={model?.authority || "OWNER"}
        description={`${controls} are the capability authority path.`}
      />
      <ControlField
        label="AI Autonomy"
        value={delegated ? "DELEGATED" : "GATED"}
        description={
          delegated
            ? `AI may act inside armed owner limits; per-order confirmation ${perOrder ? "required" : "not required"}.`
            : "Owner setup and action-time gates control whether AI automation can act."
        }
      />
      <ControlField
        label="Action-Time Checks"
        value={model?.technical_action_time_checks_still_required === false ? "OFF" : "REQUIRED"}
        danger={model?.technical_action_time_checks_still_required === false}
        description={checks}
      />
    </div>
  );
}

function ownerGateDisplay(status: string | null | undefined): string {
  if (!status) return "OWNER PENDING";
  return status.includes("NOT LICENSED") ? "OWNER PENDING" : status;
}

function ownerGateDescription(status: string | null | undefined): string {
  if (!status) return "Waiting for live API.";
  if (status.includes("NOT LICENSED")) return "Owner/provider gate pending; paper/demo stays available.";
  return "Backend gate is owner-authorized.";
}

function ownerFacingBoundary(text: string): string {
  return text
    .replace(/CURRENTLY NOT LICENSED/g, "OWNER PENDING")
    .replace(/NOT LICENSED/g, "OWNER PENDING");
}

// Owner's "min edge to trade" dial. Persisted locally only (key
// 'cas_forex_edge_threshold', a 0..1 fraction, default 0.65). No backend call:
// this records the owner's intended bar in-app. The live dispatch chokepoint is
// fail-closed regardless — a setup with no measured-and-null-beating edge never
// trades, so this slider can only RAISE the bar, never manufacture a trade.
const EDGE_THRESHOLD_KEY = "cas_forex_edge_threshold";
const EDGE_THRESHOLD_DEFAULT = 0.65;

function readStoredEdgeThreshold(): number {
  try {
    const raw = window.localStorage.getItem(EDGE_THRESHOLD_KEY);
    if (raw == null) return EDGE_THRESHOLD_DEFAULT;
    const v = Number(raw);
    if (!Number.isFinite(v)) return EDGE_THRESHOLD_DEFAULT;
    // Stored as a 0..1 fraction; keep it inside the legal 0.50..0.95 band.
    return Math.min(0.95, Math.max(0.5, v));
  } catch {
    return EDGE_THRESHOLD_DEFAULT;
  }
}

function EdgeThresholdPanel() {
  const [fraction, setFraction] = useState<number>(() => readStoredEdgeThreshold());

  // EdgeThresholdControl works in whole-percent (50..95); store the 0..1 fraction.
  const percent = Math.round(fraction * 100);

  function onChangePercent(p: number) {
    const next = Math.min(0.95, Math.max(0.5, p / 100));
    setFraction(next);
    try {
      window.localStorage.setItem(EDGE_THRESHOLD_KEY, String(next));
    } catch {
      /* localStorage unavailable (private mode) — keep the in-memory value */
    }
  }

  return (
    <>
      <EdgeThresholdControl value={percent} onChange={onChangePercent} />
      <div className="control-field-desc" style={{ margin: "-6px 4px 14px" }}>
        The AI only trades setups it measures above this AND that beat the null.
        Saved on this device only (default {Math.round(EDGE_THRESHOLD_DEFAULT * 100)}%); it can
        only raise the bar — below it, the dispatch chokepoint stands down and sends no new order.
      </div>
    </>
  );
}

const AI_DIAL_LABELS: Record<string, { label: string; detail: string }> = {
  edge_threshold: {
    label: "Edge threshold",
    detail: "Minimum measured edge before an entry can pass strategy checks.",
  },
  min_directional_confidence: {
    label: "Directional score floor",
    detail: "Minimum directional hypothesis score before a candidate forms.",
  },
  max_risk_pct_per_trade: {
    label: "Max risk per trade",
    detail: "Risk budget percentage used by sizing logic before execution gates.",
  },
  max_concurrent_trades: {
    label: "Max concurrent trades",
    detail: "AI-requested open-position cap when no explicit owner override wins.",
  },
  max_positions_per_symbol: {
    label: "Max positions per symbol",
    detail: "Per-symbol stacking cap enforced by the pre-execution gate.",
  },
  max_total_exposure_lots: {
    label: "Max total exposure",
    detail: "Total open lots allowed by the AI dial before owner risk overrides.",
  },
  daily_loss_cap_usd: {
    label: "Daily loss cap",
    detail: "Dollar loss cap the AI can request inside the owner envelope.",
  },
  symbols: {
    label: "Symbols",
    detail: "Broker-normalized markets the AI is allowed to consider.",
  },
  sessions: {
    label: "Sessions",
    detail: "Trading sessions the AI is allowed to operate in.",
  },
  timeframes: {
    label: "Entry timeframes",
    detail: "Completed-candle lanes: M1/M5 micro-scalp and M15/H1 broader intraday.",
  },
  max_compound_units: {
    label: "Max compound units",
    detail: "Maximum add-on units for compounding/position management.",
  },
  paper_learning_trades: {
    label: "Paper learning trades",
    detail: "1 allows paper learning attempts; live execution still has separate gates.",
  },
  trailing_stop_enabled: {
    label: "Trailing stop",
    detail: "1 enables implemented trailing-stop exits in the paper outcome path.",
  },
  trailing_lock_fraction: {
    label: "Trailing lock fraction",
    detail: "Share of favorable run the trailing stop locks on pullback.",
  },
};

function AiControlAuthorityPanel() {
  const [authority, setAuthority] = useState<AiControlAuthorityState | null>(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    setStatus("");
    const next = await fetchAiControlAuthority();
    if (next) {
      setAuthority(next);
    } else {
      setStatus("AI dial state unavailable - is the API reachable?");
    }
  }

  const values = authority?.control_surface?.values ?? {};
  const bounds = authority?.control_surface?.bounds ?? {};
  const definitions = authority?.control_surface?.dial_definitions ?? {};
  const antiImpulse = authority?.control_surface?.anti_impulse;
  const rows = Object.entries(values).sort(([a], [b]) => a.localeCompare(b));

  return (
    <GlassPanel title="AI Control Dials" subtitle="Current operator levers and the owner envelope that fences them">
      <div className="ai-dial-summary">
        <ControlField label="Updated" value={authority?.updated_at ? formatIsoForDisplay(authority.updated_at) : "UNAVAILABLE"} mono />
        <ControlField label="Owner Envelope" value={authority ? "ACTIVE" : "UNAVAILABLE"} danger={!authority} />
        <ControlField
          label="Loosens 24h"
          value={`${antiImpulse?.recent_loosen_count ?? 0} / ${antiImpulse?.loosen_warning_limit ?? 6}`}
          danger={Boolean(antiImpulse?.warning_active)}
          mono
          description={antiImpulse?.policy ?? "Loosening is audited and surfaced for anti-impulse review."}
        />
        <ControlField
          label="Loosen Cooldown"
          value={antiImpulse?.cooldown_active ? `${Math.max(1, Math.ceil((antiImpulse.cooldown_remaining_seconds ?? 0) / 60))}m ACTIVE` : "CLEAR"}
          danger={Boolean(antiImpulse?.cooldown_active)}
          mono
          description={
            antiImpulse?.cooldown_detail
              ?? "Repeated AI dial loosening is rate-limited; tightening remains available."
          }
        />
        <ControlField
          label="Loosen Journal"
          value={antiImpulse?.journal_prompt_required_on_loosen ? "REQUIRED" : "UNAVAILABLE"}
          danger={!antiImpulse?.journal_prompt_required_on_loosen}
          description={
            antiImpulse?.journal_prompt
              ? `${antiImpulse.journal_prompt} Minimum: ${antiImpulse.journal_prompt_min_chars ?? 20} characters.`
              : "Loosened AI dial changes require an anti-impulse reason before they are applied."
          }
        />
        <ControlField label="State Store" value={authority?.state_path ?? "unavailable"} mono />
      </div>

      <div className="positions-table-wrap ai-dial-table-wrap">
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>Dial</th>
              <th>Current</th>
              <th>Owner Bound</th>
              <th>Risk Posture</th>
              <th>Operational Meaning</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([key, value]) => {
              const meta = AI_DIAL_LABELS[key] ?? { label: key, detail: "Typed CAS/AI control surface lever." };
              const definition = definitions[key] ?? {};
              const loosen = definition.loosens_when ?? "mapped";
              const tighten = definition.tightens_when ?? "mapped";
              return (
                <tr key={key}>
                  <td>
                    <div className="ai-dial-name">{definition.label ?? meta.label}</div>
                    <div className="ai-dial-key mono">{key}</div>
                  </td>
                  <td className="mono">{formatUnknownValue(value)}</td>
                  <td className="mono">{formatDialBound(bounds[key])}</td>
                  <td className="ai-dial-detail">Loosen: {loosen}; tighten: {tighten}</td>
                  <td className="ai-dial-detail">
                    {definition.operational_effect ?? meta.detail}
                    {definition.units && <div>Units: {definition.units}.</div>}
                    {definition.enforced_by && <div>Enforced by {definition.enforced_by}.</div>}
                    {definition.runtime_path && <div className="mono">Runtime: {definition.runtime_path}</div>}
                  </td>
                </tr>
              );
            })}
            {rows.length === 0 && (
              <tr>
                <td colSpan={5}>No AI dial snapshot is loaded.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="mobile-api-row" style={{ marginTop: 10 }}>
        <button className="mobile-api-button ghost" type="button" onClick={() => void refresh()}>Refresh dials</button>
      </div>
      {status && <div className="control-field-desc" style={{ color: "var(--danger)" }}>{status}</div>}
      <div className="control-field-desc" style={{ marginTop: 8 }}>
        {authority?.authority_note ?? "Owner sets the envelope. AI dials are bounded and do not grant live-money authority."}
        {" "}
        {authority?.control_surface?.guardrail_note ?? ""}
      </div>
    </GlassPanel>
  );
}

function ControlAuditTrailPanel() {
  const [rows, setRows] = useState<Array<ControlAuditRow & { family: "Risk" | "AI" }>>([]);
  const [status, setStatus] = useState("");

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    setStatus("");
    const [risk, ai] = await Promise.all([
      fetchRiskControlAudit(8),
      fetchAiControlAuthorityAudit(8),
    ]);
    const merged = [
      ...((risk?.rows ?? []).map((row) => ({ ...row, family: "Risk" as const }))),
      ...((ai?.rows ?? []).map((row) => ({ ...row, family: "AI" as const }))),
    ].sort((a, b) => String(b.at ?? "").localeCompare(String(a.at ?? "")));
    setRows(merged.slice(0, 12));
    if (!risk && !ai) setStatus("Control audit trail unavailable - is the API reachable?");
  }

  return (
    <GlassPanel title="Control Audit Trail" subtitle="Recent owner, operator, and risk-cap changes">
      <div className="positions-table-wrap ai-dial-table-wrap">
        <table className="data-table ai-dial-table control-audit-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Area</th>
              <th>Action</th>
              <th>Source</th>
              <th>Change</th>
              <th>Money</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={`${row.audit_id ?? row.at ?? "audit"}-${index}`}>
                <td className="mono">{row.at ? formatIsoForDisplay(row.at) : "unknown"}</td>
                <td>{row.family}</td>
                <td className="mono">{row.action ?? "UNKNOWN"}</td>
                <td className="ai-dial-detail">{row.source ?? "unknown"}</td>
                <td>{formatAuditChanges(row)}</td>
                <td>
                  <StatusChip
                    label={row.external_money_movement ? "MONEY MOVED" : "NO MONEY MOVE"}
                    variant={row.external_money_movement ? "danger" : "success"}
                    size="sm"
                  />
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6}>No control changes have been audited yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="mobile-api-row" style={{ marginTop: 10 }}>
        <button className="mobile-api-button ghost" type="button" onClick={() => void refresh()}>Refresh audit</button>
      </div>
      {status && <div className="control-field-desc" style={{ color: "var(--danger)" }}>{status}</div>}
    </GlassPanel>
  );
}

function formatAuditChanges(row: ControlAuditRow): string {
  const changes = row.changes ?? [];
  if (!changes.length) return "No field delta recorded";
  const shown = changes.slice(0, 3).map((change) => {
    const scope = change.scope ? `${change.scope}:` : "";
    const posture = change.posture ? ` (${change.posture})` : "";
    return `${scope}${change.key ?? "field"} ${formatUnknownValue(change.before)} to ${formatUnknownValue(change.after)}${posture}`;
  });
  const extra = changes.length > shown.length ? ` +${changes.length - shown.length} more` : "";
  return shown.join("; ") + extra;
}

function CriticalNotificationAuditPanel() {
  const [rows, setRows] = useState<CriticalNotificationAuditRow[]>([]);
  const [readiness, setReadiness] = useState<CriticalNotificationReadiness | null>(null);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    setStatus("");
    const [report, readinessReport] = await Promise.all([
      fetchCriticalNotificationAudit(10),
      fetchCriticalNotificationReadiness(10),
    ]);
    if (!report) {
      setRows([]);
      setStatus("Critical notification audit unavailable - is the API reachable?");
      return;
    }
    setRows(report.rows ?? []);
    setReadiness(readinessReport);
  }

  async function sendCriticalAlertTest() {
    setBusy(true);
    setStatus("");
    try {
      const result = await testCriticalNotificationDelivery();
      if (!result.ok) {
        setStatus(`Critical alert test failed: ${result.error.message}`);
        return;
      }
      if (result.data.readiness) {
        setReadiness(result.data.readiness);
      }
      if (result.data.audit) {
        setRows((previous) => [result.data.audit!, ...previous].slice(0, 10));
      } else {
        await refresh();
      }
      const delivery = result.data.readiness?.status ?? "UNKNOWN";
      setStatus(
        result.data.status === "DISPATCHED"
          ? `Critical alert test emitted. Delivery readiness is now ${delivery}.`
          : "No off-screen critical alert destination exists yet; local in-app alerts remain active.",
      );
    } catch (error) {
      setStatus(`Critical alert test failed: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setBusy(false);
    }
  }

  const localChannel = readiness?.local_in_app_alert_channel;
  const deliveryStatus = readiness?.status ?? "UNKNOWN";
  const deliveryDanger = deliveryStatus === "DELIVERY_FAILING" || deliveryStatus === "PARTIAL_DELIVERY";

  return (
    <GlassPanel title="Critical Notification Audit" subtitle="Recent operational alerts and webhook delivery attempts">
      <div className="ai-dial-summary" style={{ marginBottom: 10 }}>
        <ControlField
          label="Delivery Status"
          value={deliveryStatus}
          danger={deliveryDanger}
          mono
          description={readiness?.next_action ?? "Critical notification delivery readiness is loading."}
        />
        <ControlField
          label="Local In-App Alerts"
          value={localChannel?.status ?? "UNKNOWN"}
          mono
          description={`CriticalAlertStrip polls every ${localChannel?.poll_interval_seconds ?? 60}s; visible warning/alert rows: ${localChannel?.visible_warning_or_alert_count ?? 0}.`}
        />
        <ControlField
          label="Off-Screen Delivery"
          value={readiness?.offscreen_delivery_status ?? "UNKNOWN"}
          danger={readiness?.offscreen_delivery_status === "DELIVERY_FAILING"}
          mono
          description={readiness?.owner_setup_required_for_offscreen_alerts ? "Webhook setup is optional for off-screen alerts; local in-app alerts remain active." : "Webhook destination is configured."}
        />
        <ControlField label="Webhook Destinations" value={String(readiness?.subscription_count ?? 0)} mono />
        <ControlField
          label="Recent Delivery"
          value={`${readiness?.recent_dispatch_success_count ?? 0}/${readiness?.recent_dispatch_attempt_count ?? 0}`}
          mono
          description={readiness?.blockers?.join("; ") || readiness?.claim_boundary}
        />
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap">
        <table className="data-table ai-dial-table critical-notification-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Event</th>
              <th>Severity</th>
              <th>Delivery</th>
              <th>Detail</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={`${row.audit_id ?? row.at ?? "critical"}-${index}`}>
                <td className="mono">{row.at ? formatIsoForDisplay(row.at) : "unknown"}</td>
                <td>
                  <div className="ai-dial-name">{row.event?.title ?? row.event?.event_kind ?? "Critical event"}</div>
                  <div className="ai-dial-key mono">{row.event?.event_kind ?? "UNKNOWN"}</div>
                </td>
                <td>
                  <StatusChip
                    label={(row.event?.severity ?? "info").toUpperCase()}
                    variant={criticalSeverityVariant(row.event?.severity)}
                    size="sm"
                  />
                </td>
                <td>
                  <StatusChip
                    label={`${row.dispatch_success_count ?? 0}/${row.dispatch_attempt_count ?? 0} SENT`}
                    variant={(row.dispatch_success_count ?? 0) > 0 ? "success" : (row.dispatch_attempt_count ?? 0) > 0 ? "warning" : "muted"}
                    size="sm"
                  />
                  {row.skipped && <div className="ai-dial-detail">{row.skipped}</div>}
                </td>
                <td>{row.event?.body ?? "No detail recorded."}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={5}>No critical notification events have been audited yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="mobile-api-row" style={{ marginTop: 10 }}>
        <button className="mobile-api-button" type="button" disabled={busy} onClick={() => void sendCriticalAlertTest()}>
          {busy ? "Sending test..." : "Send critical alert test"}
        </button>
        <button className="mobile-api-button ghost" type="button" disabled={busy} onClick={() => void refresh()}>Refresh alerts</button>
      </div>
      {status && (
        <div
          className="control-field-desc"
          style={{
            color:
              status.toLowerCase().includes("failed")
              ? "var(--danger)"
              : status.toLowerCase().includes("no off-screen")
                ? "var(--warning)"
                : "var(--success)",
          }}
        >
          {status}
        </div>
      )}
    </GlassPanel>
  );
}

function criticalSeverityVariant(severity: string | undefined): "success" | "warning" | "danger" | "muted" {
  const key = (severity ?? "").toLowerCase();
  if (key === "alert") return "danger";
  if (key === "warning") return "warning";
  if (key === "info") return "success";
  return "muted";
}

function formatIsoForDisplay(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function formatUnknownValue(value: unknown): string {
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(4).replace(/0+$/, "").replace(/\.$/, "");
  if (typeof value === "boolean") return value ? "YES" : "NO";
  if (value == null) return "UNSET";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function formatYesNo(value: unknown): string {
  return value ? "YES" : "NO";
}

function formatUsd(value: unknown): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "n/a";
  return `$${numeric.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatBrokerTruthReasonLabel(value: string): string {
  const labels: Record<string, string> = {
    terminal_position_reconciliation: "Terminal Reconciliation",
    live_open_positions_crosscheck: "Open Position Crosscheck",
    live_position_stop_loss_protection: "Stop-Loss Protection",
  };
  return labels[value] ?? value.replace(/_/g, " ");
}

function formatBrokerTruthReasonList(values: unknown): string {
  if (!Array.isArray(values) || values.length === 0) return "NONE";
  const labels = values
    .filter((value): value is string => typeof value === "string" && value.trim().length > 0)
    .map((value) => formatBrokerTruthReasonLabel(value));
  return labels.length > 0 ? labels.join(", ") : "NONE";
}

function recordOrNull(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function formatDialBound(value: unknown): string {
  if (!value || typeof value !== "object") return "UNBOUNDED";
  const record = value as Record<string, unknown>;
  if (Array.isArray(record.allowed)) return record.allowed.join(", ");
  if ("min" in record || "max" in record) {
    const min = formatUnknownValue(record.min);
    const max = record.max === null || record.max === undefined ? "UNBOUNDED" : formatUnknownValue(record.max);
    return `${min} to ${max}`;
  }
  return JSON.stringify(value);
}

function MobileApiPanel() {
  const [apiBase, setApiBaseInput] = useState(() => getApiBase());
  const [saved, setSaved] = useState(false);

  const save = () => {
    setApiBase(apiBase);
    setSaved(true);
  };

  const reset = () => {
    resetApiBase();
    setApiBaseInput(getApiBase());
    setSaved(true);
  };

  return (
    <GlassPanel title="Phone / APK Connection" subtitle="Point this app at the CAS Forex API reachable from your phone">
      <div className="mobile-api-row">
        <input
          className="mobile-api-input"
          value={apiBase}
          onChange={(e) => {
            setApiBaseInput(e.target.value);
            setSaved(false);
          }}
          placeholder="http://192.168.1.50:8765/api/forex"
          spellCheck={false}
        />
        <button className="mobile-api-button" type="button" onClick={save}>Save</button>
        <button className="mobile-api-button ghost" type="button" onClick={reset}>Reset</button>
      </div>
      <div className="control-field-desc" style={{ marginTop: 8 }}>
        For a phone, use your computer's LAN/VPN/tunnel address, e.g. <code>http://192.168.x.x:8765/api/forex</code>.
        <strong> Do not use 127.0.0.1 on the phone</strong> unless the API is running on the phone itself.
        {saved && <span style={{ color: "var(--success)", marginLeft: 8 }}>Saved. Refresh or reopen the app to reload live evidence.</span>}
      </div>
    </GlassPanel>
  );
}

function SecurityPosturePanel() {
  const [posture, setPosture] = useState<SecurityPosture | null>(null);

  useEffect(() => {
    void fetchSecurityPosture().then((s) => { if (s) setPosture(s); });
  }, []);

  const owner = posture?.owner_auth;
  const ignore = posture?.ignore_coverage ?? {};
  const secrets = posture?.server_secret_inventory ?? [];
  const attention = posture?.attention_items ?? [];
  const browserPolicy = posture?.browser_exposure?.frontend_secret_policy ?? "Loading security posture.";
  const managedStore = posture?.managed_secret_store;
  const roleModel = posture?.role_permission_model;
  const liveSecondFactor = roleModel?.live_action_second_factor;
  const routePolicy = roleModel?.route_permission_policy;
  const defaultMutationCount = routePolicy?.default_mutation_route_count ?? 0;
  const sensitiveRouteRules = (routePolicy?.route_rules ?? [])
    .filter((rule) => rule.money_or_live_sensitive)
    .slice(0, 6);
  const roles = roleModel?.roles ?? [];

  return (
    <GlassPanel title="Security Posture" subtitle="Owner auth, browser exposure, and local secret inventory">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <StatusChip
          label={posture?.status ?? "SYNCING"}
          variant={posture?.status === "OK" ? "success" : posture?.status === "ATTENTION" ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip
          label={owner?.lan_mode_enabled ? "LAN ON" : "LAN OFF"}
          variant={owner?.lan_mode_enabled ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip
          label={owner?.owner_token_present ? "OWNER TOKEN SET" : "NO OWNER TOKEN"}
          variant={owner?.owner_token_present ? "success" : "warning"}
          size="sm"
        />
      </div>
      <div className="control-grid">
        <ControlField label="Owner Token" value={owner?.owner_token_present ? (owner.owner_token_hint || "SET") : "NOT SET"} mono description="Only masked token hints are shown outside the loopback-only pairing route." />
        <ControlField label="Cloud Mode" value={owner?.cloud_mode ? "TOKEN REQUIRED" : "LOCAL LOOPBACK TRUSTED"} description={owner?.cloud_mode ? "Cloud deployments require an owner token for all API calls." : "The local PC can use the API without a token; off-box devices need LAN mode plus token."} />
        <ControlField label=".env Git Ignore" value={ignore.env_ignored_by_git ? "COVERED" : "MISSING"} danger={!ignore.env_ignored_by_git} />
        <ControlField label="runtime/ Git Ignore" value={ignore.runtime_ignored_by_git ? "COVERED" : "MISSING"} danger={!ignore.runtime_ignored_by_git} />
        <ControlField label="runtime/ Docker Ignore" value={ignore.runtime_ignored_by_docker ? "COVERED" : "MISSING"} danger={!ignore.runtime_ignored_by_docker} />
        <ControlField label="Browser Secret Policy" value="OWNER TOKEN ONLY" description={browserPolicy} />
      </div>
      <div className="control-section" style={{ marginTop: 12 }}>
        <h4 className="control-section-title">Managed Secret Store</h4>
        <div className="control-grid">
          <ControlField
            label="Backend"
            value={managedStore?.backend_status ?? "SYNCING"}
            mono
            danger={managedStore?.status === "ATTENTION"}
            description={managedStore?.detail ?? "Managed secret-store status is loading."}
          />
          <ControlField
            label="Active Provider"
            value={managedStore?.active_backend || "none"}
            mono
            description={`requested: ${managedStore?.requested_backend ?? "auto"}`}
          />
          <ControlField
            label="External Manager"
            value={managedStore?.external_secret_manager?.configured ? (managedStore.external_secret_manager.provider || "CONFIGURED") : "NOT CONFIGURED"}
            danger={managedStore?.cloud_mode && !managedStore?.external_secret_manager?.configured}
            description={managedStore?.cloud_mode ? "Cloud/public mode should use an external managed secret manager." : "Local desktop can use current-user OS protection."}
          />
          <ControlField
            label="Raw Secret Return"
            value={managedStore?.raw_secret_returned ? "YES" : "NO"}
            danger={managedStore?.raw_secret_returned === true}
            description={managedStore?.claim_boundary ?? "Managed-store posture is read-only."}
          />
        </div>
      </div>
      <div className="control-section" style={{ marginTop: 12 }}>
        <h4 className="control-section-title">Server-Side Secrets</h4>
        <div className="control-grid">
          {secrets.slice(0, 8).map((secret) => (
            <ControlField
              key={secret.key}
              label={secret.label}
              value={secret.configured ? `SET ${secret.masked_hint || ""}` : "NOT SET"}
              mono={Boolean(secret.masked_hint)}
              danger={Boolean(secret.browser_exposed && secret.key !== "owner_token")}
              description={`${secret.storage ?? "server-side"}; browser exposed: ${secret.browser_exposed ? "yes" : "no"}${secret.runtime_override_set ? `; runtime override encrypted: ${secret.runtime_override_encrypted_at_rest ? "yes" : "no"}` : ""}${secret.runtime_secret_store_set ? `; runtime secret store encrypted: ${secret.runtime_secret_store_encrypted_at_rest ? "yes" : "no"}` : ""}${secret.plaintext_config_source_present ? "; plaintext config fallback present" : ""}.`}
            />
          ))}
        </div>
      </div>
      <div className="control-section" style={{ marginTop: 12 }}>
        <h4 className="control-section-title">Role Permission Model</h4>
        <div className="control-grid" style={{ marginBottom: 10 }}>
          <ControlField
            label="Authorization Model"
            value={roleModel?.authorization_model ?? "SYNCING"}
            description={roleModel?.claim_boundary ?? "Role permission model is read-only."}
          />
          <ControlField
            label="MFA Status"
            value={roleModel?.mfa_status ?? "SYNCING"}
            danger={roleModel?.mfa_status === "NOT_IMPLEMENTED"}
            description={roleModel?.mfa_detail ?? "Loading MFA posture."}
          />
          <ControlField
            label="Live Action 2nd Factor"
            value={liveSecondFactor?.status ?? "SYNCING"}
            description={[
              ...(liveSecondFactor?.factors ?? []),
              ...(liveSecondFactor?.not_implemented ?? []).map((item) => `not implemented: ${item}`),
              ...(roleModel?.mfa_hardening_backlog ?? []),
            ].join(" ")}
            danger={!liveSecondFactor?.status}
          />
          <ControlField
            label="Permission Gaps"
            value={`${roleModel?.gaps?.length ?? 0}`}
            mono
            danger={(roleModel?.gaps?.length ?? 0) > 0}
          />
          <ControlField
            label="Route Permission Policy"
            value={routePolicy?.status ?? "SYNCING"}
            danger={routePolicy?.status === "ATTENTION"}
            description={routePolicy?.claim_boundary ?? "Route permission policy is loading."}
          />
          <ControlField
            label="Policy Enforcement"
            value={routePolicy?.enforcement ?? "SYNCING"}
            mono
            description={`default read: ${routePolicy?.default_read_permission ?? "n/a"}; default mutation: ${routePolicy?.default_mutation_permission ?? "n/a"}`}
          />
          <ControlField
            label="Route Rules"
            value={`${routePolicy?.route_rule_count ?? 0}`}
            mono
            description={`${routePolicy?.money_or_live_sensitive_rule_count ?? 0} live/money-sensitive; ${routePolicy?.loopback_only_rule_count ?? 0} loopback-only.`}
          />
          <ControlField
            label="Default Mutations"
            value={`${defaultMutationCount}`}
            mono
            danger={defaultMutationCount > 0}
            description={`coverage: ${routePolicy?.coverage_status ?? "SYNCING"}; inventory: ${routePolicy?.route_inventory_available ? `${routePolicy.route_inventory_count ?? 0} method routes` : "not available"}`}
          />
        </div>
        {(routePolicy?.default_mutation_routes?.length ?? 0) > 0 && (
          <div className="control-field-desc" style={{ marginBottom: 10, color: "var(--warning)" }}>
            Default mutation routes need explicit policy: {routePolicy?.default_mutation_routes?.slice(0, 4).map((route) => `${route.method} ${route.path}`).join("; ")}
          </div>
        )}
        <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginBottom: 10 }}>
          <table className="data-table ai-dial-table">
            <thead>
              <tr>
                <th>Route Category</th>
                <th>Path</th>
                <th>Permission</th>
                <th>Extra Gate</th>
              </tr>
            </thead>
            <tbody>
              {sensitiveRouteRules.map((rule) => (
                <tr key={`${rule.category ?? "route"}-${rule.path ?? rule.prefix}`}>
                  <td className="ai-dial-detail">{rule.category ?? "route"}</td>
                  <td className="ai-dial-detail mono">{rule.path ?? rule.prefix ?? "n/a"}</td>
                  <td className="ai-dial-detail mono">{rule.permission ?? "n/a"}</td>
                  <td className="ai-dial-detail">
                    typed confirm {formatYesNo(rule.typed_confirmation_required)}
                    {" | "}loopback only {formatYesNo(rule.loopback_only)}
                  </td>
                </tr>
              ))}
              {sensitiveRouteRules.length === 0 && (
                <tr>
                  <td colSpan={4}>Route permission policy is warming.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="positions-table-wrap ai-dial-table-wrap">
          <table className="data-table ai-dial-table">
            <thead>
              <tr>
                <th>Role</th>
                <th>Auth</th>
                <th>Controls</th>
                <th>Live / Broker</th>
                <th>Secrets / Money</th>
              </tr>
            </thead>
            <tbody>
              {roles.map((role) => (
                <tr key={role.role_key ?? role.label}>
                  <td>
                    <div className="ai-dial-name">{role.label ?? role.role_key}</div>
                    <div className="ai-dial-key mono">{role.principal_type ?? "unknown"}</div>
                  </td>
                  <td className="ai-dial-detail">{role.authentication ?? "unknown"}</td>
                  <td className="ai-dial-detail">
                    dashboard {formatYesNo(role.can_view_dashboard)}
                    {" | "}owner {formatYesNo(role.can_change_owner_controls)}
                    {" | "}dials {formatYesNo(role.can_change_ai_dials)}
                  </td>
                  <td className="ai-dial-detail">
                    arm {formatYesNo(role.can_arm_live_authority)}
                    {" | "}order {formatYesNo(role.can_submit_live_order)}
                    {" | "}emergency {formatYesNo(role.can_run_broker_emergency)}
                  </td>
                  <td className="ai-dial-detail">
                    money {formatYesNo(role.can_move_money)}
                    {" | "}raw secrets {formatYesNo(role.can_read_raw_secrets)}
                    {" | "}typed confirm {formatYesNo(role.requires_typed_confirmation_for_money_or_live)}
                  </td>
                </tr>
              ))}
              {roles.length === 0 && (
                <tr>
                  <td colSpan={5}>Role permission model is warming.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      {attention.length > 0 && (
        <div className="control-field-desc" style={{ marginTop: 12, color: "var(--warning)" }}>
          {attention.slice(0, 4).join(" ")}
        </div>
      )}
      <div className="control-field-desc" style={{ marginTop: 10 }}>
        {posture?.claim_boundary ?? "Security posture is read-only and never returns raw secrets."}
      </div>
    </GlassPanel>
  );
}

function AiHedgeSupervisionPanel() {
  const [report, setReport] = useState<AiHedgeSupervisionReport | null>(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    setStatus("");
    const next = await fetchAiHedgeSupervision();
    if (next) {
      setReport(next);
    } else {
      setStatus("AI Hedge supervision unavailable - is the API reachable?");
    }
  }

  const recommendations = report?.recommendations ?? [];
  const actionRecommendations = recommendations.filter((row) => row.intent !== "skip");
  const positions = report?.positions ?? [];
  const topRecommendation = actionRecommendations[0] ?? recommendations[0];
  const sourceHealth = recordOrNull(report?.source_health);
  const positionFeedLabel = report?.position_feed_label
    ?? (typeof sourceHealth?.position_feed_label === "string" ? sourceHealth.position_feed_label : undefined)
    ?? "warming";
  const positionFeedDetail = report?.position_feed_detail
    ?? (typeof sourceHealth?.position_feed_detail === "string" ? sourceHealth.position_feed_detail : undefined)
    ?? (typeof sourceHealth?.detail === "string" ? sourceHealth.detail : undefined)
    ?? report?.price_source_summary
    ?? "Movement source truth is warming.";

  return (
    <GlassPanel title="AI Operator Edge / Hedge Supervision" subtitle="Runtime edge and trade-management recommendations; dispatch gates remain authoritative">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <StatusChip
          label={report?.status ?? "SYNCING"}
          variant={report?.status === "ATTENTION" ? "danger" : report?.status === "ACTIVE_RECOMMENDATIONS" ? "warning" : report?.status === "WATCHING" ? "success" : "muted"}
          size="sm"
        />
        <StatusChip
          label={report?.price_source_status ?? "SOURCE WARMING"}
          variant={report?.static_simulation_active ? "warning" : report?.price_source_status === "PROVIDER_ACTIVE" ? "success" : "muted"}
          size="sm"
        />
        <StatusChip label={`${report?.position_count ?? 0} POSITIONS`} variant="muted" size="sm" />
        <StatusChip
          label={`${report?.action_recommendation_count ?? 0} ACTION INTENTS`}
          variant={(report?.action_recommendation_count ?? 0) ? "warning" : "success"}
          size="sm"
        />
        <StatusChip
          label={`${report?.high_urgency_count ?? 0} HIGH`}
          variant={(report?.high_urgency_count ?? 0) ? "danger" : "success"}
          size="sm"
        />
      </div>
      <div className="control-grid">
        <ControlField
          label="Top Intent"
          value={topRecommendation ? `${topRecommendation.intent ?? "unknown"} ${topRecommendation.symbol ?? ""}` : "No recommendation loaded."}
          danger={topRecommendation?.urgency === "HIGH"}
          description={topRecommendation?.reason ?? report?.next_action ?? "AI Hedge supervision is warming."}
        />
        <ControlField
          label="Gate Path"
          value={topRecommendation?.gate_path ?? "No broker-bound action authorized here."}
          mono
          description="Any action still needs the protected dispatch path."
        />
        <ControlField
          label="Price Source"
          value={report?.price_source_label ?? "warming"}
          danger={Boolean(report?.static_simulation_active)}
          description={report?.price_source_summary ?? "Movement source truth is warming."}
        />
        <ControlField
          label="Position Feed"
          value={positionFeedLabel}
          danger={Boolean(report?.static_simulation_active)}
          description={positionFeedDetail}
        />
        <ControlField
          label="Execution Boundary"
          value={report?.broker_bound_action_authorized ? "AUTHORIZED" : "READ ONLY"}
          danger={Boolean(report?.broker_bound_action_authorized)}
          description="This report does not place orders, close positions, or move money."
        />
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>Intent</th>
              <th>Scope</th>
              <th>Urgency</th>
              <th>Reason</th>
              <th>Gate</th>
            </tr>
          </thead>
          <tbody>
            {recommendations.slice(0, 8).map((row, index) => (
              <tr key={`${row.intent ?? "intent"}-${row.symbol ?? "symbol"}-${index}`}>
                <td className="mono">{row.intent ?? "unknown"}</td>
                <td>{row.scope ?? "runtime"} {row.symbol ? `- ${row.symbol}` : ""}</td>
                <td>
                  <StatusChip
                    label={row.urgency ?? "LOW"}
                    variant={row.urgency === "HIGH" ? "danger" : row.urgency === "MEDIUM" ? "warning" : "muted"}
                    size="sm"
                  />
                </td>
                <td>{row.reason ?? ""}</td>
                <td className="mono">{row.gate_path ?? "read-only"}</td>
              </tr>
            ))}
            {recommendations.length === 0 && (
              <tr>
                <td colSpan={5}>AI Hedge supervision is warming.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>Position</th>
              <th>Side</th>
              <th>R</th>
              <th>P&amp;L</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {positions.slice(0, 8).map((row, index) => (
              <tr key={`${row.position_id ?? row.symbol ?? "position"}-${index}`}>
                <td>{row.symbol ?? "UNKNOWN"}</td>
                <td className="mono">{row.side ?? ""}</td>
                <td className="mono">{row.r_multiple == null ? "n/a" : Number(row.r_multiple).toFixed(2)}</td>
                <td className="mono">{formatUsd(row.floating_pnl_usd)}</td>
                <td>{row.position_source_label ?? row.price_source ?? "unknown"}{row.price_stale ? " - stale" : ""}</td>
              </tr>
            ))}
            {positions.length === 0 && (
              <tr>
                <td colSpan={5}>No open movement-stream positions.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="mobile-api-row" style={{ marginTop: 10 }}>
        <button className="mobile-api-button ghost" type="button" onClick={() => void refresh()}>Refresh AI Hedge supervision</button>
      </div>
      {status && <div className="control-field-desc" style={{ color: "var(--danger)", marginTop: 8 }}>{status}</div>}
      <div className="control-field-desc" style={{ marginTop: 10 }}>
        {report?.claim_boundary ?? "AI Hedge supervision is read-only and does not authorize trading."}
      </div>
    </GlassPanel>
  );
}

function AiHedgeManagementHandoffPanel() {
  const [report, setReport] = useState<AiHedgeManagementHandoffReport | null>(null);
  const [status, setStatus] = useState("");
  const [execution, setExecution] = useState<AiHedgeManagementExecutionResult | null>(null);
  const [busyAction, setBusyAction] = useState("");

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    setStatus("");
    const next = await fetchAiHedgeManagementHandoff();
    if (next) {
      setReport(next);
    } else {
      setStatus("AI Hedge management handoff unavailable - is the API reachable?");
    }
  }

  async function runManagement(dryRun: boolean) {
    if (!topAction?.action_id) {
      setStatus("No current AI Edge/Hedge management draft is selected.");
      return;
    }
    setStatus("");
    setBusyAction(dryRun ? "dry-run" : "execute");
    try {
      const result = await runAiHedgeManagementAction({
        action_id: topAction.action_id,
        reason: "AI_OPERATOR_EDGE_MANAGEMENT",
        dry_run: dryRun,
        confirm_owner_action: false,
        confirm_phrase: "",
      });
      setExecution(result);
      if (!dryRun) {
        await refresh();
      }
    } catch {
      setStatus("AI Edge/Hedge management execution route failed - is the API reachable?");
    } finally {
      setBusyAction("");
    }
  }

  const actions = report?.management_actions ?? [];
  const blocked = report?.blocked_actions ?? [];
  const topAction = actions[0];
  const topBlocked = blocked[0];
  const formatNum = (value: unknown) => (
    value == null || value === "" || Number.isNaN(Number(value))
      ? "n/a"
      : Number(value).toFixed(2)
  );
  const executedAndProven = execution?.status === "EXECUTED_RECONCILED";
  const executedButUnproven = String(execution?.status ?? "").startsWith("EXECUTED_") && !executedAndProven;
  const postExecutionRefresh = (
    execution?.post_execution_refresh && typeof execution.post_execution_refresh === "object"
      ? execution.post_execution_refresh
      : null
  );
  const postExecutionRefreshStatus = String(
    execution?.post_execution_refresh_status
      ?? postExecutionRefresh?.status
      ?? "NOT RUN",
  );
  const postExecutionRefreshErrorCount = Number(postExecutionRefresh?.error_count ?? 0);

  return (
    <GlassPanel title="AI Operator Edge / Hedge Management Handoff" subtitle="Guarded broker-action drafts for breakeven, trailing, and partial-close execution">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <StatusChip
          label={report?.status ?? "SYNCING"}
          variant={report?.status === "READY_FOR_GUARDED_EXECUTION" || report?.status === "READY_FOR_OWNER_REVIEW" ? "warning" : report?.status === "BLOCKED" ? "danger" : report?.status === "NO_ACTIONABLE_MANAGEMENT" ? "success" : "muted"}
          size="sm"
        />
        <StatusChip
          label={`${report?.management_action_count ?? 0} DRAFTS`}
          variant={(report?.management_action_count ?? 0) ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip
          label={`${report?.blocked_action_count ?? 0} BLOCKED`}
          variant={(report?.blocked_action_count ?? 0) ? "danger" : "success"}
          size="sm"
        />
        <StatusChip
          label={report?.dry_run_only ? "DRY RUN ONLY" : "CHECK MODE"}
          variant="muted"
          size="sm"
        />
      </div>
      <div className="control-grid">
        <ControlField
          label="Top Draft"
          value={topAction ? `${topAction.broker_method ?? "action"} ${topAction.symbol ?? ""}` : "No broker-action draft."}
          description={topAction?.reason ?? topBlocked?.reason ?? report?.next_action ?? "AI Hedge management handoff is warming."}
        />
        <ControlField
          label="Ticket / Method"
          value={topAction ? `${topAction.broker_ticket ?? "n/a"} / ${topAction.broker_method ?? "n/a"}` : topBlocked ? `${topBlocked.broker_ticket ?? "n/a"} / ${topBlocked.block_code ?? "blocked"}` : "n/a"}
          mono
          danger={Boolean(topBlocked) && !topAction}
          description="A broker ticket is required before any close or modify proposal can target a real position."
        />
        <ControlField
          label="Draft Change"
          value={topAction ? `SL ${formatNum(topAction.stop_loss)} / volume ${formatNum(topAction.volume)}` : "No change drafted."}
          mono
          description="This is a proposed bridge call, not an executed command."
        />
        <ControlField
          label="Execution Boundary"
          value={report?.broker_bound_action_authorized ? "AUTHORIZED" : "GUARDED"}
          danger={Boolean(report?.broker_bound_action_authorized)}
          description="Per-action owner confirmation is not required inside delegated authority; fresh broker truth and execution guard approval still are."
        />
      </div>
      <div className="control-grid" style={{ marginTop: 12 }}>
        <ControlField
          label="Execution Result"
          value={execution?.status ?? "NOT RUN"}
          danger={Boolean(execution?.status && !["DRY_RUN", "EXECUTED_RECONCILED"].includes(String(execution.status)))}
          description={execution?.next_action ?? execution?.detail ?? "Run a dry-run first, then execute only if the selected draft should pass through the guard and bridge."}
        />
        <ControlField
          label="Broker Touch"
          value={execution?.broker_touched ? "BRIDGE CALLED" : "NO BROKER TOUCH"}
          mono
          danger={Boolean(execution?.broker_touched && executedButUnproven)}
          description={execution?.audit_id ? `audit ${execution.audit_id}` : "No execution audit row yet."}
        />
        <ControlField
          label="Receipt Reconciliation"
          value={execution?.terminal_receipt_status ?? "NOT CHECKED"}
          mono
          danger={Boolean(execution?.terminal_receipt_status && execution.terminal_receipt_status !== "RECONCILED" && execution.terminal_receipt_status !== "NOT_REQUESTED")}
          description={execution?.terminal_receipt && typeof execution.terminal_receipt.reason === "string" ? execution.terminal_receipt.reason : "After confirmed execution, bridge position state must prove the ticket/SL/volume outcome."}
        />
        <ControlField
          label="Post-Execution Refresh"
          value={postExecutionRefreshStatus}
          mono
          danger={Boolean(execution?.broker_touched && !["REFRESH_RAN", "NOT_REQUESTED"].includes(postExecutionRefreshStatus))}
          description={
            postExecutionRefresh
              ? `${postExecutionRefreshErrorCount} refresh errors; broker/account truth packets rebuilt after execution.`
              : "After broker execution, live telemetry and reconciliation should refresh from current terminal/account truth."
          }
        />
      </div>
      <div className="mobile-api-row" style={{ marginTop: 10 }}>
        <button
          className="mobile-api-button ghost"
          type="button"
          disabled={!topAction || busyAction !== ""}
          onClick={() => void runManagement(true)}
        >
          {busyAction === "dry-run" ? "Dry-running..." : "Dry run selected draft"}
        </button>
        <button
          className="mobile-api-button danger"
          type="button"
          disabled={!topAction || busyAction !== ""}
          onClick={() => void runManagement(false)}
        >
          {busyAction === "execute" ? "Executing..." : "Execute guarded draft"}
        </button>
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>Draft</th>
              <th>Ticket</th>
              <th>Method</th>
              <th>Change</th>
              <th>Gate</th>
            </tr>
          </thead>
          <tbody>
            {actions.slice(0, 8).map((row, index) => (
              <tr key={`${row.action_id ?? "action"}-${index}`}>
                <td>{row.intent ?? "unknown"} {row.symbol ? `- ${row.symbol}` : ""}</td>
                <td className="mono">{row.broker_ticket ?? "n/a"}</td>
                <td className="mono">{row.broker_method ?? "n/a"}</td>
                <td className="mono">SL {formatNum(row.stop_loss)} / volume {formatNum(row.volume)}</td>
                <td>{row.gate_path ?? "owner review required"}</td>
              </tr>
            ))}
            {actions.length === 0 && (
              <tr>
                <td colSpan={5}>No AI Hedge broker-action drafts are ready.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>Blocked Intent</th>
              <th>Symbol</th>
              <th>Code</th>
              <th>Reason</th>
            </tr>
          </thead>
          <tbody>
            {blocked.slice(0, 8).map((row, index) => (
              <tr key={`${row.intent ?? "blocked"}-${row.symbol ?? "symbol"}-${index}`}>
                <td className="mono">{row.intent ?? "unknown"}</td>
                <td>{row.symbol ?? "UNKNOWN"}</td>
                <td className="mono">{row.block_code ?? "BLOCKED"}</td>
                <td>{row.reason ?? ""}</td>
              </tr>
            ))}
            {blocked.length === 0 && (
              <tr>
                <td colSpan={4}>No blocked AI Hedge management drafts.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="mobile-api-row" style={{ marginTop: 10 }}>
        <button className="mobile-api-button ghost" type="button" onClick={() => void refresh()}>Refresh management handoff</button>
      </div>
      {status && <div className="control-field-desc" style={{ color: "var(--danger)", marginTop: 8 }}>{status}</div>}
      <div className="control-field-desc" style={{ marginTop: 10 }}>
        {report?.claim_boundary ?? "AI Hedge management handoff is proposal-only and does not call the broker."}
      </div>
    </GlassPanel>
  );
}

function LegalReviewReadinessPanel() {
  const [report, setReport] = useState<LegalReviewReadinessReport | null>(null);
  const [control, setControl] = useState<LegalReviewControlReport | null>(null);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState({
    reviewed_by: "",
    review_date: "",
    scope: "Terms, risk disclosure, privacy, automated trading, AI limitations, broker connectivity, retail forex, public launch",
    review_artifact_path: "",
    review_artifact_sha256: "",
    matter_reference: "",
    jurisdictions: "",
    notes: "",
    qualified_counsel_confirmed: false,
    confirm_phrase: "",
  });

  useEffect(() => {
    void refresh();
  }, []);

  function syncDraftFromControl(nextControl: LegalReviewControlReport | null) {
    const record = nextControl?.current_record;
    if (!record) return;
    setDraft({
      reviewed_by: record.reviewed_by ?? "",
      review_date: record.review_date ?? "",
      scope: record.scope ?? "Terms, risk disclosure, privacy, automated trading, AI limitations, broker connectivity, retail forex, public launch",
      review_artifact_path: record.review_artifact_path ?? "",
      review_artifact_sha256: record.review_artifact_sha256 ?? "",
      matter_reference: record.matter_reference ?? "",
      jurisdictions: record.jurisdictions ?? "",
      notes: record.notes ?? "",
      qualified_counsel_confirmed: Boolean(record.qualified_counsel_confirmed),
      confirm_phrase: "",
    });
  }

  async function refresh() {
    setStatus("");
    const [nextReadiness, nextControl] = await Promise.all([
      fetchLegalReviewReadiness(),
      fetchLegalReviewControl(),
    ]);
    if (nextReadiness) setReport(nextReadiness);
    if (nextControl) {
      setControl(nextControl);
      syncDraftFromControl(nextControl);
    }
    if (!nextReadiness && !nextControl) {
      setStatus("Legal review control/readiness unavailable - is the API reachable?");
    }
  }

  async function saveCounselReviewRecord() {
    setBusy(true);
    setStatus("");
    try {
      const result = await updateLegalReviewControl({
        reviewed_by: draft.reviewed_by,
        review_date: draft.review_date,
        scope: draft.scope,
        review_artifact_path: draft.review_artifact_path,
        review_artifact_sha256: draft.review_artifact_sha256,
        matter_reference: draft.matter_reference,
        jurisdictions: draft.jurisdictions,
        notes: draft.notes,
        qualified_counsel_confirmed: draft.qualified_counsel_confirmed,
        confirm_phrase: draft.confirm_phrase,
        counsel_review_status: "accepted",
      });
      if (result.legal_review_readiness) setReport(result.legal_review_readiness);
      if (result.legal_review_control) {
        setControl(result.legal_review_control);
        syncDraftFromControl(result.legal_review_control);
      } else {
        await refresh();
      }
      setStatus("Counsel review metadata recorded. Public launch still depends on a real qualified counsel review and all other launch gates.");
    } catch (error) {
      const detail = error instanceof Error ? error.message : "";
      setStatus(detail || "Counsel review record save failed - check the typed confirmation, evidence hash, and owner access.");
    } finally {
      setBusy(false);
    }
  }

  async function resetCounselReviewRecord() {
    setBusy(true);
    setStatus("");
    try {
      const result = await resetLegalReviewControl();
      if (result.legal_review_readiness) setReport(result.legal_review_readiness);
      if (result.legal_review_control) {
        setControl(result.legal_review_control);
        syncDraftFromControl(result.legal_review_control);
      } else {
        await refresh();
      }
      setStatus("Local counsel review metadata reset. Public launch legal readiness is now blocked until a new accepted record is provided.");
    } catch (error) {
      const detail = error instanceof Error ? error.message : "";
      setStatus(detail || "Counsel review reset failed - check owner access and API reachability.");
    } finally {
      setBusy(false);
    }
  }

  const checks = report?.checks ?? [];
  const attentionChecks = checks.filter((check) => check.status !== "OK");
  const displayChecks = [...attentionChecks, ...checks.filter((check) => check.status === "OK")];
  const attentionCount = report?.attention_count ?? attentionChecks.length;
  const recordPath = report?.counsel_review_record_path ?? report?.required_documents?.counsel_review_record ?? "docs/legal/CAS_FOREX_COUNSEL_REVIEW_RECORD.md";
  const controlRecord = control?.current_record ?? null;
  const confirmPhrase = control?.required_confirm_phrase ?? "RECORD QUALIFIED COUNSEL REVIEW";
  const counselHandoff = report?.counsel_review_handoff;
  const handoffDocs = counselHandoff?.package_documents ?? [];
  const handoffSteps = counselHandoff?.setup_steps ?? [];
  const handoffTemplate = counselHandoff?.record_template ?? [];
  const handoffDocsPresent = handoffDocs.filter((doc) => doc.present).length;
  const handoffRequiredFields = counselHandoff?.required_record_fields ?? [];

  return (
    <GlassPanel title="Legal Review Readiness" subtitle="Draft disclosures versus counsel-reviewed launch approval">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <StatusChip
          label={report?.status ?? "SYNCING"}
          variant={report?.status === "OK" ? "success" : report?.status === "ATTENTION" ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip
          label={report?.launch_legal_status ?? "WARMING"}
          variant={report?.launch_legal_status === "READY_FOR_PUBLIC_LAUNCH_LEGAL" ? "success" : report?.launch_legal_status === "BLOCK_PUBLIC_LAUNCH" ? "danger" : "muted"}
          size="sm"
        />
        <StatusChip label={`${report?.ok_count ?? 0} OK`} variant="success" size="sm" />
        <StatusChip
          label={`${attentionCount} ATTENTION`}
          variant={attentionCount ? "warning" : "success"}
          size="sm"
        />
        <StatusChip
          label={report?.counsel_review_accepted ? "COUNSEL ACCEPTED" : "COUNSEL RECORD MISSING"}
          variant={report?.counsel_review_accepted ? "success" : "danger"}
          size="sm"
        />
      </div>
      <div className="control-grid">
        <ControlField
          label="Counsel Record"
          value={recordPath}
          mono
          danger={!report?.counsel_review_accepted}
          description="Draft docs do not count as public-launch legal approval."
        />
        <ControlField
          label="Next Action"
          value={report?.next_action ?? "Legal review readiness report is warming."}
          danger={!report?.counsel_review_accepted}
        />
        <ControlField
          label="Checklist"
          value={report?.required_documents?.checklist ?? "docs/legal/CAS_FOREX_LEGAL_REVIEW_CHECKLIST.md"}
          mono
          description="Review intake only; not counsel approval."
        />
        <ControlField
          label="Boundary"
          value="READ ONLY"
          description="This panel does not provide legal advice or authorize public launch."
        />
        <ControlField
          label="Counsel Handoff"
          value={counselHandoff?.status ?? "SYNCING"}
          danger={counselHandoff?.status === "COUNSEL_REVIEW_REQUIRED"}
          description={counselHandoff?.claim_boundary ?? "Read-only package checklist for external counsel review."}
        />
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>Counsel Handoff</th>
              <th>Value</th>
              <th>Purpose</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Launch Status</td>
              <td className="mono">{counselHandoff?.launch_legal_status ?? report?.launch_legal_status ?? "WARMING"}</td>
              <td>Legal launch gate state from the counsel-review handoff.</td>
            </tr>
            <tr>
              <td>Package Docs</td>
              <td className="mono">{handoffDocs.length ? `${handoffDocsPresent}/${handoffDocs.length} present` : "warming"}</td>
              <td>{handoffDocs.slice(0, 3).map((doc) => doc.path).filter(Boolean).join(", ") || "Draft disclosure package and review record inventory."}</td>
            </tr>
            <tr>
              <td>Required Fields</td>
              <td className="mono">{handoffRequiredFields.slice(0, 4).join("; ") || "warming"}</td>
              <td>Minimum accepted-record fields for the external counsel review file.</td>
            </tr>
            <tr>
              <td>First Step</td>
              <td>{handoffSteps[0] ?? "Legal review handoff is warming."}</td>
              <td>Owner-facing next action before public launch can be called legally ready.</td>
            </tr>
            <tr>
              <td>Record Template</td>
              <td className="mono">{handoffTemplate.slice(0, 3).join("; ") || "warming"}</td>
              <td>Starter fields for `docs/legal/CAS_FOREX_COUNSEL_REVIEW_RECORD.md`.</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12, padding: 12 }}>
        <div className="field-label" style={{ marginBottom: 8 }}>Counsel Record Control</div>
        <div className="control-grid">
          <div className="control-field">
            <div className="field-label">Reviewed By</div>
            <input
              className="mobile-api-input"
              value={draft.reviewed_by}
              placeholder="Qualified counsel or firm"
              onChange={(event) => setDraft({ ...draft, reviewed_by: event.target.value })}
            />
          </div>
          <div className="control-field">
            <div className="field-label">Review Date</div>
            <input
              className="mobile-api-input"
              value={draft.review_date}
              placeholder="YYYY-MM-DD"
              onChange={(event) => setDraft({ ...draft, review_date: event.target.value })}
            />
          </div>
          <div className="control-field">
            <div className="field-label">Review Artifact Path</div>
            <input
              className="mobile-api-input"
              value={draft.review_artifact_path}
              placeholder="Local file path or external record path"
              onChange={(event) => setDraft({ ...draft, review_artifact_path: event.target.value })}
            />
          </div>
          <div className="control-field">
            <div className="field-label">Artifact SHA-256</div>
            <input
              className="mobile-api-input"
              value={draft.review_artifact_sha256}
              placeholder="Auto-computed if the local artifact file exists"
              onChange={(event) => setDraft({ ...draft, review_artifact_sha256: event.target.value })}
            />
            <div className="control-field-desc" style={{ marginTop: 6 }}>
              {controlRecord?.artifact_path_exists_locally
                ? "Current artifact path resolves locally."
                : "If the artifact is not a readable local file, paste the external artifact hash explicitly."}
            </div>
          </div>
          <div className="control-field">
            <div className="field-label">Matter Reference</div>
            <input
              className="mobile-api-input"
              value={draft.matter_reference}
              placeholder="Optional internal/legal matter id"
              onChange={(event) => setDraft({ ...draft, matter_reference: event.target.value })}
            />
          </div>
          <div className="control-field">
            <div className="field-label">Jurisdictions</div>
            <input
              className="mobile-api-input"
              value={draft.jurisdictions}
              placeholder="Optional jurisdiction list"
              onChange={(event) => setDraft({ ...draft, jurisdictions: event.target.value })}
            />
          </div>
        </div>
        <div className="control-field" style={{ marginTop: 12 }}>
          <div className="field-label">Scope</div>
          <textarea
            className="mobile-api-input broker-reality-textarea"
            value={draft.scope}
            onChange={(event) => setDraft({ ...draft, scope: event.target.value })}
          />
        </div>
        <div className="control-field" style={{ marginTop: 12 }}>
          <div className="field-label">Notes</div>
          <textarea
            className="mobile-api-input broker-reality-textarea"
            value={draft.notes}
            onChange={(event) => setDraft({ ...draft, notes: event.target.value })}
          />
        </div>
        <label className="control-field-desc" style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 10 }}>
          <input
            type="checkbox"
            checked={draft.qualified_counsel_confirmed}
            onChange={(event) => setDraft({ ...draft, qualified_counsel_confirmed: event.target.checked })}
          />
          Qualified counsel has actually reviewed this scope outside the app.
        </label>
        <div className="control-field" style={{ marginTop: 10 }}>
          <div className="field-label">Typed Confirmation</div>
          <input
            className="mobile-api-input"
            value={draft.confirm_phrase}
            placeholder={confirmPhrase}
            onChange={(event) => setDraft({ ...draft, confirm_phrase: event.target.value })}
          />
        </div>
        <div className="mobile-api-row" style={{ marginTop: 10 }}>
          <button className="mobile-api-button" type="button" disabled={busy} onClick={() => void saveCounselReviewRecord()}>
            {busy ? "Saving..." : "Record counsel review"}
          </button>
          <button className="mobile-api-button ghost" type="button" disabled={busy} onClick={() => void resetCounselReviewRecord()}>
            Reset record
          </button>
          <button className="mobile-api-button ghost" type="button" disabled={busy} onClick={() => void refresh()}>
            Refresh legal readiness
          </button>
        </div>
        <div className="control-field-desc" style={{ marginTop: 8 }}>
          This stores metadata about an external review artifact. It does not turn draft disclosures into legal advice or self-create launch approval.
        </div>
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>Check</th>
              <th>Status</th>
              <th>Detail</th>
              <th>Evidence</th>
              <th>Next</th>
            </tr>
          </thead>
          <tbody>
            {displayChecks.map((check) => {
              const evidence = (check.evidence ?? [])
                .slice(0, 4)
                .map((item) => {
                  const label = item.path ?? item.term ?? item.label ?? item.key ?? "evidence";
                  const present = item.present === true ? "ok" : item.present === false ? "missing" : "seen";
                  return `${String(label)}:${present}`;
                })
                .join(", ");
              const missing = [
                ...(check.missing_paths ?? []),
                ...(check.missing_terms ?? []),
              ].slice(0, 4).join(", ");
              return (
                <tr key={check.key ?? check.label ?? "legal-check"}>
                  <td>{check.label ?? check.key ?? "Legal check"}</td>
                  <td>
                    <StatusChip
                      label={check.status ?? "UNKNOWN"}
                      variant={check.status === "OK" ? "success" : check.status === "MISSING" ? "danger" : "warning"}
                      size="sm"
                    />
                  </td>
                  <td>{check.detail ?? ""}</td>
                  <td className="mono">{evidence || "none"}</td>
                  <td>{missing || check.next_action || "Keep covered."}</td>
                </tr>
              );
            })}
            {displayChecks.length === 0 && (
              <tr>
                <td colSpan={5}>Legal review readiness is warming.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="mobile-api-row" style={{ marginTop: 10 }}>
        <button className="mobile-api-button ghost" type="button" onClick={() => void refresh()}>Refresh legal readiness</button>
      </div>
      {status && (
        <div
          className="control-field-desc"
          style={{
            color:
              status.toLowerCase().includes("failed")
              || status.toLowerCase().includes("required")
              || status.toLowerCase().includes("unavailable")
                ? "var(--danger)"
                : "var(--warning)",
            marginTop: 8,
          }}
        >
          {status}
        </div>
      )}
      <div className="control-field-desc" style={{ marginTop: 10 }}>
        {report?.claim_boundary ?? "Legal review readiness is read-only and does not authorize trading, public launch, or money movement."}
      </div>
    </GlassPanel>
  );
}

function ProfessionalReadinessPanel() {
  const [matrix, setMatrix] = useState<ProfessionalReadinessMatrix | null>(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    setStatus("");
    const next = await fetchProfessionalReadiness();
    if (next) {
      setMatrix(next);
    } else {
      setStatus("Professional readiness matrix unavailable - is the API reachable?");
    }
  }

  const rows = matrix?.rows ?? [];
  const attentionRows = rows.filter((row) => row.status === "GAP" || row.status === "PARTIAL");
  const displayRows = [
    ...attentionRows.filter((row) => row.completion_state === "MISSING"),
    ...attentionRows.filter((row) => row.blocked_by_external_dependency),
    ...attentionRows.filter((row) => row.completion_state === "PARTIAL"),
    ...rows.filter((row) => row.status !== "GAP" && row.status !== "PARTIAL"),
  ];

  return (
    <GlassPanel title="Professional Readiness Matrix" subtitle="37-item audit against serious trading-app standards">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <StatusChip
          label={matrix?.status ?? "SYNCING"}
          variant={matrix?.status === "OK" ? "success" : matrix?.status === "ATTENTION" ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip label={`${matrix?.ok_count ?? 0} OK`} variant="success" size="sm" />
        <StatusChip
          label={`${matrix?.partial_count ?? 0} PARTIAL`}
          variant={(matrix?.partial_count ?? 0) ? "warning" : "success"}
          size="sm"
        />
        <StatusChip
          label={`${matrix?.gap_count ?? 0} GAP`}
          variant={(matrix?.gap_count ?? 0) ? "danger" : "success"}
          size="sm"
        />
        <StatusChip
          label={`${matrix?.external_blocked_count ?? 0} EXTERNAL`}
          variant={(matrix?.external_blocked_count ?? 0) ? "warning" : "success"}
          size="sm"
        />
        <StatusChip label={`${matrix?.item_count ?? 0} CHECKS`} variant="muted" size="sm" />
      </div>
      <div className="control-grid">
        <ControlField
          label="Primary Gap"
          value={matrix?.top_attention_items?.[0] ?? "No high-priority gap loaded."}
          danger={Boolean(matrix?.gap_count)}
          description="Attention rows are sorted first in the table."
        />
        <ControlField
          label="Matrix Scope"
          value="READ ONLY"
          description="This report audits evidence and gaps; it does not change trading authority."
        />
        <ControlField
          label="External Blockers"
          value={`${matrix?.external_blocked_count ?? 0}`}
          description="Rows blocked by real-world counsel, hosted monitoring, or deployment configuration stay visible without being called code gaps."
        />
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Category</th>
              <th>Standard</th>
              <th>Status</th>
              <th>Evidence</th>
              <th>Next</th>
            </tr>
          </thead>
          <tbody>
            {displayRows.map((row) => (
              <tr key={`${row.item_number ?? "n"}-${row.key ?? "row"}`}>
                <td className="mono">{row.item_number ?? ""}</td>
                <td>{row.category ?? row.key ?? "readiness"}</td>
                <td>{row.professional_standard ?? ""}</td>
                <td>
                  <StatusChip
                    label={(row.completion_state ?? row.status ?? "UNKNOWN").replace(/_/g, " ")}
                    variant={
                      row.completion_state === "SATISFIED"
                        ? "success"
                        : row.completion_state === "MISSING"
                          ? "danger"
                          : "warning"
                    }
                    size="sm"
                  />
                </td>
                <td className="mono">{(row.present_evidence_refs ?? row.evidence_refs ?? []).slice(0, 3).join(", ") || "none"}</td>
                <td>{row.external_dependency || row.remaining_gap || row.next_action || "Keep covered."}</td>
              </tr>
            ))}
            {displayRows.length === 0 && (
              <tr>
                <td colSpan={6}>Professional readiness matrix is warming.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="mobile-api-row" style={{ marginTop: 10 }}>
        <button className="mobile-api-button ghost" type="button" onClick={() => void refresh()}>Refresh matrix</button>
      </div>
      {status && <div className="control-field-desc" style={{ color: "var(--danger)", marginTop: 8 }}>{status}</div>}
      <div className="control-field-desc" style={{ marginTop: 10 }}>
        {matrix?.claim_boundary ?? "Professional readiness matrix is read-only and does not authorize trading or money movement."}
      </div>
    </GlassPanel>
  );
}

function EconomicCalendarPanel() {
  const [report, setReport] = useState<EconomicCalendarFeedReport | null>(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    setStatus("");
    const next = await fetchEconomicCalendarFeed();
    if (next) {
      setReport(next);
    } else {
      setStatus("Economic calendar status unavailable - is the API reachable?");
    }
  }

  const configured = report?.configured === true;
  const loaded = report?.status === "LOADED" || report?.status === "CACHE_FRESH" || report?.status === "CACHE_FRESH_AFTER_REFRESH_ERROR";
  const attention = configured && !loaded;
  const events = report?.events ?? [];

  return (
    <GlassPanel title="Economic Calendar Feed" subtitle="External macro-event source for dispatch blackout checks">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <StatusChip
          label={report?.status ?? "SYNCING"}
          variant={loaded ? "success" : attention ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip
          label={configured ? "FEED CONFIGURED" : "STATIC FALLBACK"}
          variant={configured ? "success" : "warning"}
          size="sm"
        />
        <StatusChip
          label={`${report?.event_count ?? 0} EVENTS`}
          variant={(report?.event_count ?? 0) ? "success" : "muted"}
          size="sm"
        />
        <StatusChip
          label={report?.fail_closed_on_error ? "FAIL CLOSED" : "NO FAIL-CLOSED"}
          variant={report?.fail_closed_on_error ? "success" : "muted"}
          size="sm"
        />
      </div>
      <div className="control-grid">
        <ControlField label="Source" value={report?.source || "Not configured"} mono danger={!configured} description={report?.detail ?? "Economic calendar feed status is loading."} />
        <ControlField label="Cache" value={report?.cache_path || "runtime/economic_calendar"} mono danger={report?.cache_stale === true} description={typeof report?.cache_age_seconds === "number" ? `${Math.round(report.cache_age_seconds)}s old, ttl ${report.cache_ttl_seconds ?? 0}s` : "No cache age loaded."} />
        <ControlField label="Unusable Rows" value={`${report?.unusable_event_count ?? 0}`} mono danger={Boolean(report?.unusable_event_count)} description={`${report?.raw_event_count ?? 0} raw event row(s) inspected.`} />
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>Event</th>
              <th>Impact</th>
              <th>Currency</th>
              <th>Scheduled</th>
            </tr>
          </thead>
          <tbody>
            {events.slice(0, 6).map((event, index) => (
              <tr key={`${String(event.event_id ?? "event")}-${index}`}>
                <td>{String(event.name ?? event.event_type ?? "macro event")}</td>
                <td>{String(event.impact ?? "HIGH")}</td>
                <td>{String(event.currency ?? "USD")}</td>
                <td className="mono">{String(event.scheduled_at_utc ?? "")}</td>
              </tr>
            ))}
            {events.length === 0 && (
              <tr>
                <td colSpan={4}>No configured external events loaded; dispatch will label fallback/static calendar evidence.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="mobile-api-row" style={{ marginTop: 10 }}>
        <button className="mobile-api-button ghost" type="button" onClick={() => void refresh()}>Refresh calendar status</button>
      </div>
      {status && <div className="control-field-desc" style={{ color: "var(--danger)", marginTop: 8 }}>{status}</div>}
      <div className="control-field-desc" style={{ marginTop: 10 }}>
        {report?.claim_boundary ?? "Economic calendar feed status is read-only and does not authorize trading or money movement."}
      </div>
    </GlassPanel>
  );
}

function RuntimeTopologyPanel() {
  const [report, setReport] = useState<RuntimeTopologyStatus | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function refresh() {
      const next = await fetchRuntimeTopology();
      if (!cancelled && next) setReport(next);
    }
    void refresh();
    const intervalId = window.setInterval(() => void refresh(), 15_000);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  const accepted = report?.claim_status === "ACCEPT";
  return (
    <GlassPanel
      title="Runtime Process Topology"
      subtitle="Single ownership for Operator, dispatch, proof loops, and process-local state"
      variant={accepted ? "default" : "warning"}
    >
      <div className="dashboard-grid-3col">
        <ControlField label="Topology" value={report?.status ?? "WARMING"} danger={Boolean(report && !accepted)} mono />
        <ControlField label="API Workers" value={`${report?.api_worker_count ?? 0} / ${report?.supported_api_worker_count ?? 1}`} danger={Boolean(report && report.api_worker_count !== 1)} mono />
        <ControlField label="Runtime Owner" value={report?.runtime_owner ? `PID ${report.runtime_owner_pid}` : "NOT OWNED"} danger={Boolean(report && !report.runtime_owner)} mono />
        <ControlField label="Control Plane" value={report?.stateful_control_plane_enabled ? "ENABLED" : "BLOCKED"} danger={Boolean(report && !report.stateful_control_plane_enabled)} />
        <ControlField label="LAN / Phone" value={report?.lan_phone_supported ? "SUPPORTED" : "BLOCKED"} danger={Boolean(report && !report.lan_phone_supported)} />
        <ControlField label="Multi-worker" value={report?.multi_worker_supported ? "SUPPORTED" : "REFUSED"} danger={false} />
      </div>
      <div className="control-field-desc" style={{ marginTop: 10 }}>
        Process-local components: {(report?.process_local_components ?? []).join(", ") || "status warming"}.
      </div>
      <div className="control-field-desc" style={{ marginTop: 4 }}>
        {report?.claim_boundary ?? "Runtime topology status is warming."}
      </div>
    </GlassPanel>
  );
}


function OperationalReadinessPanel() {
  const [report, setReport] = useState<OperationalReadinessReport | null>(null);
  const [backupBusy, setBackupBusy] = useState(false);
  const [backupStatus, setBackupStatus] = useState("");
  const [monitoringBusy, setMonitoringBusy] = useState(false);
  const [monitoringStatus, setMonitoringStatus] = useState("");
  const [uptimeMonitorUrl, setUptimeMonitorUrl] = useState("");
  const [errorTrackingDsn, setErrorTrackingDsn] = useState("");
  const [alertWebhookUrl, setAlertWebhookUrl] = useState("");

  useEffect(() => {
    void refreshReadiness();
  }, []);

  async function refreshReadiness() {
    const next = await fetchOperationalReadiness();
    if (next) setReport(next);
  }

  async function createBackup() {
    setBackupBusy(true);
    setBackupStatus("");
    try {
      const result = await createOperatorBackup();
      if (result.operational_readiness) {
        setReport(result.operational_readiness);
      } else {
        await refreshReadiness();
      }
      const manifest = result.manifest ?? {};
      const snapshotId = typeof manifest.snapshot_id === "string" ? manifest.snapshot_id : "snapshot";
      setBackupStatus(result.status === "CREATED" ? `Backup created: ${snapshotId}.` : "Backup finished without a usable snapshot.");
    } catch {
      setBackupStatus("Backup request failed - check API reachability and runtime/backups permissions.");
    } finally {
      setBackupBusy(false);
    }
  }

  const checks = report?.checks ?? [];
  const backupInventory = report?.backup_inventory;
  const latestBackup = backupInventory?.latest_snapshot ?? null;
  const latestBackupAt = typeof latestBackup?.created_at_iso === "string" ? latestBackup.created_at_iso : "none";
  const latestBackupFiles = typeof latestBackup?.file_count === "number" ? String(latestBackup.file_count) : "0";
  const attention = report?.attention_items ?? [];
  const externalMonitoring = report?.external_monitoring;
  const externalChecks = externalMonitoring?.checks ?? [];
  const uptimeCheck = externalChecks.find((check) => check.key === "external_uptime_monitor");
  const errorCheck = externalChecks.find((check) => check.key === "error_tracking_dsn");
  const alertCheck = externalChecks.find((check) => check.key === "offscreen_alert_destination");
  const monitoringHandoff = externalMonitoring?.deployment_handoff;
  const handoffEndpoints = monitoringHandoff?.health_endpoints ?? externalMonitoring?.health_endpoints ?? [];
  const handoffCommands = monitoringHandoff?.verification_commands ?? [];
  const handoffSteps = monitoringHandoff?.setup_steps ?? [];

  async function saveExternalMonitoring() {
    const patch: { uptime_monitor_url?: string; error_tracking_dsn?: string; alert_webhook_url?: string } = {};
    if (uptimeMonitorUrl.trim()) patch.uptime_monitor_url = uptimeMonitorUrl.trim();
    if (errorTrackingDsn.trim()) patch.error_tracking_dsn = errorTrackingDsn.trim();
    if (alertWebhookUrl.trim()) patch.alert_webhook_url = alertWebhookUrl.trim();
    if (!patch.uptime_monitor_url && !patch.error_tracking_dsn && !patch.alert_webhook_url) {
      setMonitoringStatus("Paste at least one uptime, error-tracking, or off-screen alert value before saving.");
      return;
    }
    setMonitoringBusy(true);
    setMonitoringStatus("");
    try {
      const result = await updateExternalMonitoringConfig(patch);
      if (result.operational_readiness) {
        setReport(result.operational_readiness);
      } else {
        await refreshReadiness();
      }
      setUptimeMonitorUrl("");
      setErrorTrackingDsn("");
      setAlertWebhookUrl("");
      setMonitoringStatus(
        result.status === "UPDATED"
          ? `Saved external hooks: ${(result.applied_keys ?? []).join(", ") || "updated"}.`
          : "No external monitoring change was applied.",
      );
    } catch {
      setMonitoringStatus("External monitoring save failed - check owner access and API reachability.");
    } finally {
      setMonitoringBusy(false);
    }
  }

  async function resetExternalMonitoring() {
    setMonitoringBusy(true);
    setMonitoringStatus("");
    try {
      const result = await resetExternalMonitoringConfig();
      if (result.operational_readiness) {
        setReport(result.operational_readiness);
      } else {
        await refreshReadiness();
      }
      setUptimeMonitorUrl("");
      setErrorTrackingDsn("");
      setAlertWebhookUrl("");
      setMonitoringStatus(
        `Reset local external monitoring hooks: ${(result.applied_keys ?? []).join(", ") || "no runtime overrides were set"}.`,
      );
    } catch {
      setMonitoringStatus("External monitoring reset failed - check owner access and API reachability.");
    } finally {
      setMonitoringBusy(false);
    }
  }

  return (
    <GlassPanel title="Operational Readiness" subtitle="Health, logs, backups, runbooks, build, rollback, and external monitoring evidence">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <StatusChip
          label={report?.status ?? "SYNCING"}
          variant={report?.status === "OK" ? "success" : report?.status === "ATTENTION" ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip
          label={`${report?.ok_count ?? 0} OK`}
          variant="success"
          size="sm"
        />
        <StatusChip
          label={`${report?.attention_count ?? 0} ATTENTION`}
          variant={(report?.attention_count ?? 0) ? "warning" : "success"}
          size="sm"
        />
        <StatusChip
          label={`${backupInventory?.snapshot_count ?? 0} BACKUPS`}
          variant={(backupInventory?.snapshot_count ?? 0) ? "success" : "warning"}
          size="sm"
        />
        <StatusChip
          label={`EXT MON ${externalMonitoring?.status ?? "SYNCING"}`}
          variant={externalMonitoring?.status === "OK" ? "success" : externalMonitoring?.status === "ATTENTION" ? "warning" : "muted"}
          size="sm"
        />
      </div>
      <div className="control-grid">
        <ControlField label="Runbook" value={report?.runbook_path ?? "docs/operations/CAS_FOREX_OPERATIONS_RUNBOOK.md"} mono description="Local operating procedure for health, logs, backup, restore, rollback, and build preview." />
        <ControlField label="Latest Backup" value={latestBackupAt} mono danger={!latestBackup} description={`${latestBackupFiles} file(s) captured in latest operator-state snapshot.`} />
        <ControlField
          label="External Monitoring"
          value={externalMonitoring?.status ?? "SYNCING"}
          danger={externalMonitoring?.status === "ATTENTION"}
          description={externalMonitoring?.next_action ?? "Configure uptime monitor, error tracking, and off-screen alerts before hosted production."}
        />
        <ControlField label="Boundary" value="READ ONLY" description="This panel reports operations evidence; it does not restart processes or touch trades." />
        <ControlField
          label="Deployment Handoff"
          value={monitoringHandoff?.status ?? "SYNCING"}
          danger={monitoringHandoff?.status === "ACTION_REQUIRED"}
          description={monitoringHandoff?.claim_boundary ?? "Read-only hosted-monitoring checklist for uptime, error tracking, and alert delivery."}
        />
      </div>
      <div className="mobile-api-row" style={{ marginTop: 12 }}>
        <button className="mobile-api-button" type="button" disabled={backupBusy} onClick={() => void createBackup()}>
          {backupBusy ? "Creating backup..." : "Create operator backup"}
        </button>
        <button className="mobile-api-button ghost" type="button" disabled={backupBusy} onClick={() => void refreshReadiness()}>
          Refresh readiness
        </button>
      </div>
      {backupStatus && (
        <div className="control-field-desc" style={{ marginTop: 8, color: backupStatus.includes("failed") ? "var(--danger)" : "var(--success)" }}>
          {backupStatus}
        </div>
      )}
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>Check</th>
              <th>Status</th>
              <th>Detail</th>
              <th>Missing</th>
            </tr>
          </thead>
          <tbody>
            {checks.map((check) => (
              <tr key={check.key ?? check.label}>
                <td>{check.label ?? check.key}</td>
                <td>
                  <StatusChip
                    label={check.status ?? "UNKNOWN"}
                    variant={check.status === "OK" ? "success" : "warning"}
                    size="sm"
                  />
                </td>
                <td>{check.detail ?? ""}</td>
                <td className="mono">{[...(check.missing_paths ?? []), ...(check.missing_terms ?? [])].join(", ") || "none"}</td>
              </tr>
            ))}
            {checks.length === 0 && (
              <tr>
                <td colSpan={4}>Operational readiness is warming.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {attention.length > 0 && (
        <div className="control-field-desc" style={{ marginTop: 8, color: "var(--warning)" }}>
          {attention.slice(0, 3).join(" ")}
        </div>
      )}
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>Hosted Handoff</th>
              <th>Value</th>
              <th>Purpose</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Owner UI</td>
              <td className="mono">{monitoringHandoff?.owner_ui_path ?? "?page=settings"}</td>
              <td>Configure runtime hooks without editing environment files.</td>
            </tr>
            <tr>
              <td>Public Base</td>
              <td className="mono">{monitoringHandoff?.public_base_url_placeholder ?? "https://your-cas-forex-host"}</td>
              <td>Replace this placeholder with the hosted HTTPS origin.</td>
            </tr>
            <tr>
              <td>Health Endpoints</td>
              <td className="mono">{handoffEndpoints.join(", ") || "loading"}</td>
              <td>Point uptime monitors at one of these read-only routes.</td>
            </tr>
            <tr>
              <td>Verify</td>
              <td className="mono">{handoffCommands.slice(0, 2).join(" | ") || "loading"}</td>
              <td>Commands to confirm hosted health endpoints answer.</td>
            </tr>
            <tr>
              <td>Next Step</td>
              <td>{handoffSteps[0] ?? externalMonitoring?.next_action ?? "Refresh readiness."}</td>
              <td>First deployment action for the current state.</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>External Hook</th>
              <th>Status</th>
              <th>Configured</th>
              <th>Detail</th>
            </tr>
          </thead>
          <tbody>
            {externalChecks.map((check) => (
              <tr key={check.key ?? check.label ?? "external-monitoring"}>
                <td>{check.label ?? check.key}</td>
                <td>
                  <StatusChip
                    label={check.status ?? "UNKNOWN"}
                    variant={check.status === "OK" ? "success" : check.status === "MISSING" ? "danger" : "warning"}
                    size="sm"
                  />
                </td>
                <td className="mono">{check.configured_key ? `${check.configured_key} ${check.masked_value ?? ""}` : "not configured"}</td>
                <td>{check.detail ?? ""}</td>
              </tr>
            ))}
            {externalChecks.length === 0 && (
              <tr>
                <td colSpan={4}>External monitoring readiness is warming.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="control-grid" style={{ marginTop: 12 }}>
        <ControlField
          label="Uptime Hook Source"
          value={uptimeCheck?.configured_key ?? "not configured"}
          mono
          description={uptimeCheck?.masked_value ?? uptimeCheck?.detail ?? "No hosted heartbeat URL is configured yet."}
          danger={uptimeCheck?.status !== "OK"}
        />
        <ControlField
          label="Error Tracking Source"
          value={errorCheck?.configured_key ?? "not configured"}
          mono
          description={errorCheck?.masked_value ?? errorCheck?.detail ?? "No external error-tracking DSN is configured yet."}
          danger={errorCheck?.status !== "OK"}
        />
        <ControlField
          label="Alert Destinations"
          value={
            alertCheck?.configured_key ?? "not configured"
          }
          mono
          description={alertCheck?.masked_value ?? "Webhook destinations can be registered below; env-based alert URLs also count."}
          danger={alertCheck?.status !== "OK"}
        />
        <ControlField
          label="Update Scope"
          value="OWNER RUNTIME"
          description="These writes update local uptime, error-tracking, and alert hooks only. They do not ping external services or affect trades."
        />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 10, marginTop: 12 }}>
        <input
          type="text"
          className="mobile-api-input"
          placeholder="Hosted uptime heartbeat URL"
          value={uptimeMonitorUrl}
          onChange={(e) => setUptimeMonitorUrl(e.target.value)}
          spellCheck={false}
        />
        <input
          type="text"
          className="mobile-api-input"
          placeholder="External error-tracking DSN"
          value={errorTrackingDsn}
          onChange={(e) => setErrorTrackingDsn(e.target.value)}
          spellCheck={false}
        />
        <input
          type="text"
          className="mobile-api-input"
          placeholder="Off-screen alert webhook URL"
          value={alertWebhookUrl}
          onChange={(e) => setAlertWebhookUrl(e.target.value)}
          spellCheck={false}
        />
      </div>
      <div className="mobile-api-row" style={{ marginTop: 12 }}>
        <button className="mobile-api-button" type="button" disabled={monitoringBusy} onClick={() => void saveExternalMonitoring()}>
          {monitoringBusy ? "Saving hooks..." : "Save external hooks"}
        </button>
        <button className="mobile-api-button ghost" type="button" disabled={monitoringBusy} onClick={() => void resetExternalMonitoring()}>
          Reset runtime hooks
        </button>
      </div>
      {monitoringStatus && (
        <div className="control-field-desc" style={{ marginTop: 8, color: monitoringStatus.includes("failed") ? "var(--danger)" : "var(--muted-text)" }}>
          {monitoringStatus}
        </div>
      )}
      <div className="control-field-desc" style={{ marginTop: 10 }}>
        {report?.claim_boundary ?? "Operational readiness is read-only and does not authorize trading or money movement."}
      </div>
    </GlassPanel>
  );
}

type EmergencyControlRow = NonNullable<EmergencyControlsReport["controls"]>[number];

function emergencyControlVariant(status?: string) {
  if (status === "OK") return "success" as const;
  if (status === "WARMING" || status === "SYNCING") return "muted" as const;
  return "warning" as const;
}

function EmergencyControlsPanel() {
  const [report, setReport] = useState<EmergencyControlsReport | null>(null);
  const [brokerEmergency, setBrokerEmergency] = useState<BrokerEmergencyActionResult | null>(null);
  const [ownerConfirmBrokerEmergency, setOwnerConfirmBrokerEmergency] = useState(false);
  const [brokerEmergencyBusy, setBrokerEmergencyBusy] = useState("");
  const [brokerEmergencyMessage, setBrokerEmergencyMessage] = useState("");

  useEffect(() => {
    void fetchEmergencyControls().then((s) => { if (s) setReport(s); });
    void fetchBrokerEmergencyStatus().then((s) => { if (s) setBrokerEmergency(s); });
  }, []);

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

  const controls = report?.controls ?? [];
  const brokerControls = controls.filter((control) => control.category === "broker_exposure");
  const missingBrokerControls = brokerControls.filter((control) => control.status !== "OK");
  const attention = report?.attention_items ?? [];
  const terminalActions = report?.recommended_terminal_actions ?? [];

  return (
    <GlassPanel title="Emergency Controls Coverage" subtitle="What the app stops, and what still requires broker-terminal action">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <StatusChip
          label={report?.status ?? "SYNCING"}
          variant={report?.status === "OK" ? "success" : report?.status === "ATTENTION" ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip
          label={report?.automation_stop_ok ? "AUTOMATION STOP WIRED" : "AUTOMATION STOP CHECKING"}
          variant={report?.automation_stop_ok ? "success" : "warning"}
          size="sm"
        />
        <StatusChip
          label={report?.broker_exposure_gap ? "BROKER FLATTEN GAP" : "BROKER FLATTEN WIRED"}
          variant={report?.broker_exposure_gap ? "warning" : "success"}
          size="sm"
        />
        <StatusChip
          label={`${report?.attention_count ?? 0} ATTENTION`}
          variant={(report?.attention_count ?? 0) ? "warning" : "success"}
          size="sm"
        />
      </div>
      <div className="control-grid">
        <ControlField
          label="Stop Scope"
          value={report?.automation_stop_ok ? "NEW AUTOMATION" : "CHECKING"}
          danger={!report?.automation_stop_ok}
          description={report?.automation_stop_scope ?? "Loading emergency-stop scope."}
        />
        <ControlField
          label="Broker Exposure"
          value={missingBrokerControls.length ? "TERMINAL REQUIRED" : "APP ROUTED"}
          danger={missingBrokerControls.length > 0}
          description={missingBrokerControls.length ? "Existing open positions and pending orders need MT4/MT5 terminal action until a tested app route exists." : "Broker exposure controls are wired in-app."}
        />
        <ControlField
          label="Missing Broker Controls"
          value={String(missingBrokerControls.length)}
          mono
          danger={missingBrokerControls.length > 0}
          description="Close-all, cancel-pending, and selective close controls must be explicit and audited."
        />
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>Control</th>
              <th>Status</th>
              <th>Route / Surface</th>
              <th>Effect</th>
              <th>Money Impact</th>
            </tr>
          </thead>
          <tbody>
            {controls.map((control: EmergencyControlRow) => (
              <tr key={control.key ?? control.label}>
                <td>{control.label ?? control.key}</td>
                <td>
                  <StatusChip
                    label={control.status ?? "UNKNOWN"}
                    variant={emergencyControlVariant(control.status)}
                    size="sm"
                  />
                </td>
                <td>
                  <div className="mono">{control.route ?? "manual terminal"}</div>
                  <div className="control-field-desc">{control.surface ?? ""}</div>
                </td>
                <td>{control.status === "OK" ? control.effect : (control.missing_detail || control.effect || "")}</td>
                <td>{control.money_impact ?? ""}</td>
              </tr>
            ))}
            {controls.length === 0 && (
              <tr>
                <td colSpan={5}>Emergency controls coverage is warming.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {terminalActions.length > 0 && (
        <div className="control-field-desc" style={{ marginTop: 8 }}>
          {terminalActions.slice(0, 3).join(" ")}
        </div>
      )}
      <div className="control-section" style={{ marginTop: 12 }}>
        <h4 className="control-section-title">Broker Emergency Actions</h4>
        <div className="control-grid">
          <ControlField label="MT5 Connected" value={brokerEmergency?.mt5_connected ? "YES" : "NO"} danger={!brokerEmergency?.mt5_connected} />
          <ControlField label="Open Positions" value={String(brokerEmergency?.open_position_count ?? 0)} mono />
          <ControlField label="Pending Orders" value={String(brokerEmergency?.pending_order_count ?? 0)} mono />
          <ControlField label="Last Action" value={brokerEmergency?.status ?? "NOT RUN"} description={brokerEmergency?.next_action ?? "Dry-run before any confirmed broker emergency action."} danger={brokerEmergency?.status === "PARTIAL" || brokerEmergency?.status === "MT5_NOT_CONNECTED"} />
        </div>
        <div className="mobile-api-row" style={{ marginTop: 10 }}>
          <button className="mobile-api-button ghost" type="button" disabled={Boolean(brokerEmergencyBusy)} onClick={() => void runBrokerEmergency("close-all", true)}>
            {brokerEmergencyBusy === "close-all:dry" ? "Checking..." : "Dry-run close all"}
          </button>
          <button className="mobile-api-button ghost" type="button" disabled={Boolean(brokerEmergencyBusy)} onClick={() => void runBrokerEmergency("close-profitable", true)}>
            {brokerEmergencyBusy === "close-profitable:dry" ? "Checking..." : "Dry-run close profitable"}
          </button>
          <button className="mobile-api-button ghost" type="button" disabled={Boolean(brokerEmergencyBusy)} onClick={() => void runBrokerEmergency("close-losing", true)}>
            {brokerEmergencyBusy === "close-losing:dry" ? "Checking..." : "Dry-run close losing"}
          </button>
          <button className="mobile-api-button ghost" type="button" disabled={Boolean(brokerEmergencyBusy)} onClick={() => void runBrokerEmergency("cancel-pending", true)}>
            {brokerEmergencyBusy === "cancel-pending:dry" ? "Checking..." : "Dry-run cancel pending"}
          </button>
          <label className="sweep-confirm-check">
            <input
              type="checkbox"
              checked={ownerConfirmBrokerEmergency}
              onChange={(event) => setOwnerConfirmBrokerEmergency(event.target.checked)}
            />
            <span>Owner Confirm Broker Action</span>
          </label>
          <button
            className="mobile-api-button"
            type="button"
            disabled={Boolean(brokerEmergencyBusy) || !ownerConfirmBrokerEmergency}
            onClick={() => void runBrokerEmergency("close-all", false)}
            title="Submits MT5 close orders for selected open positions after owner confirmation"
          >
            {brokerEmergencyBusy === "close-all:confirm" ? "Closing..." : "Close all positions"}
          </button>
          <button
            className="mobile-api-button"
            type="button"
            disabled={Boolean(brokerEmergencyBusy) || !ownerConfirmBrokerEmergency}
            onClick={() => void runBrokerEmergency("close-profitable", false)}
            title="Submits MT5 close orders only for currently profitable open positions after owner confirmation"
          >
            {brokerEmergencyBusy === "close-profitable:confirm" ? "Closing..." : "Close profitable positions"}
          </button>
          <button
            className="mobile-api-button"
            type="button"
            disabled={Boolean(brokerEmergencyBusy) || !ownerConfirmBrokerEmergency}
            onClick={() => void runBrokerEmergency("close-losing", false)}
            title="Submits MT5 close orders only for currently losing open positions after owner confirmation"
          >
            {brokerEmergencyBusy === "close-losing:confirm" ? "Closing..." : "Close losing positions"}
          </button>
          <button
            className="mobile-api-button"
            type="button"
            disabled={Boolean(brokerEmergencyBusy) || !ownerConfirmBrokerEmergency}
            onClick={() => void runBrokerEmergency("cancel-pending", false)}
            title="Submits MT5 pending-order cancel requests after owner confirmation"
          >
            {brokerEmergencyBusy === "cancel-pending:confirm" ? "Cancelling..." : "Cancel pending orders"}
          </button>
        </div>
        {brokerEmergencyMessage && (
          <div className="control-field-desc" style={{ marginTop: 8, color: brokerEmergencyMessage.includes("failed") ? "var(--danger)" : "var(--text-secondary)" }}>
            {brokerEmergencyMessage}
          </div>
        )}
      </div>
      {attention.length > 0 && (
        <div className="control-field-desc" style={{ marginTop: 8, color: "var(--warning)" }}>
          {attention.slice(0, 3).join(" ")}
        </div>
      )}
      <div className="control-field-desc" style={{ marginTop: 10 }}>
        {report?.claim_boundary ?? "Emergency controls coverage is read-only and does not touch trades or money."}
      </div>
    </GlassPanel>
  );
}

type BrokerSymbolRow = NonNullable<BrokerSymbolDiagnostics["symbols"]>[number];

function BrokerSymbolDiagnosticsPanel() {
  const [symbolsText, setSymbolsText] = useState("EUR/USD,XAU/USD,US30,NAS100");
  const [report, setReport] = useState<BrokerSymbolDiagnostics | null>(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    void refresh();
  }, []);

  function requestedSymbols(): string[] {
    return symbolsText
      .split(/[\s,]+/)
      .map((item) => item.trim())
      .filter(Boolean);
  }

  async function refresh() {
    setStatus("");
    const next = await fetchMt5SymbolDiagnostics(requestedSymbols());
    if (next) {
      setReport(next);
    } else {
      setStatus("Broker symbol diagnostics unavailable - is the API reachable and MT5 open?");
    }
  }

  const rows = report?.symbols ?? [];
  const unresolved = report?.unresolved_symbols ?? [];

  return (
    <GlassPanel title="Broker Symbol Diagnostics" subtitle="MT5 symbol mapping and contract constraints">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <StatusChip
          label={report?.status ?? "SYNCING"}
          variant={report?.status === "OK" ? "success" : report?.status === "ATTENTION" ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip
          label={report?.mt5_connected ? "MT5 CONNECTED" : "MT5 NOT CONNECTED"}
          variant={report?.mt5_connected ? "success" : "warning"}
          size="sm"
        />
        <StatusChip
          label={`${unresolved.length} UNRESOLVED`}
          variant={unresolved.length ? "warning" : "success"}
          size="sm"
        />
      </div>
      <div className="mobile-api-row" style={{ marginBottom: 10 }}>
        <input
          className="mobile-api-input"
          value={symbolsText}
          onChange={(event) => setSymbolsText(event.target.value)}
          placeholder="EUR/USD,XAU/USD,US30,NAS100"
          spellCheck={false}
        />
        <button className="mobile-api-button ghost" type="button" onClick={() => void refresh()}>Refresh symbols</button>
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap">
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>CAS Symbol</th>
              <th>Broker Symbol</th>
              <th>Status</th>
              <th>Lot Rules</th>
              <th>Stops</th>
              <th>Tick</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row: BrokerSymbolRow) => {
              const constraints = row.broker_contract_constraints ?? {};
              return (
                <tr key={`${row.canonical_symbol ?? "symbol"}-${row.selected_symbol ?? "unresolved"}`}>
                  <td className="mono">{row.canonical_symbol ?? "unknown"}</td>
                  <td>
                    <div className="ai-dial-name mono">{row.selected_symbol ?? "unresolved"}</div>
                    <div className="ai-dial-key">{row.resolution_source ?? "no source"}</div>
                  </td>
                  <td>
                    <StatusChip
                      label={row.diagnostic_status ?? row.status ?? "UNKNOWN"}
                      variant={row.status === "RESOLVED" ? "success" : "warning"}
                      size="sm"
                    />
                  </td>
                  <td className="mono">
                    {formatContractValue(constraints.min_lot)} / {formatContractValue(constraints.max_lot)}
                    {" step "}
                    {formatContractValue(constraints.lot_step)}
                  </td>
                  <td className="mono">
                    stop {formatContractValue(constraints.stop_level_points)}
                    {" / freeze "}
                    {formatContractValue(constraints.freeze_level_points)}
                  </td>
                  <td className="mono">
                    size {formatContractValue(constraints.tick_size)}
                    {" / value "}
                    {formatContractValue(constraints.tick_value)}
                  </td>
                </tr>
              );
            })}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6}>No broker symbol diagnostics loaded.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {unresolved.length > 0 && (
        <div className="control-field-desc" style={{ marginTop: 8, color: "var(--warning)" }}>
          Unresolved: {unresolved.join(", ")}. Configure broker symbol overrides or keep MT5 open so discovery can run.
        </div>
      )}
      {status && <div className="control-field-desc" style={{ marginTop: 8, color: "var(--danger)" }}>{status}</div>}
      <div className="control-field-desc" style={{ marginTop: 8 }}>
        {report?.claim_boundary ?? "Symbol diagnostics are read-only and do not place orders or change trading authority."}
      </div>
    </GlassPanel>
  );
}

function formatContractValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "NA";
  return formatUnknownValue(value);
}

// Grouped layout for the live-enable toggles. Keys map to the backend flags.
const GO_LIVE_GROUPS: { title: string; keys: LiveEnableKey[] }[] = [
  { title: "Account acknowledgments", keys: ["personal_account_ack", "no_pooled_capital_ack"] },
  { title: "Live broker mode", keys: ["live_mode", "prefer_mt5"] },
  { title: "Owner enable", keys: ["owner_enable_live_trading", "live_trading_licensed"] },
];

const REAL_MONEY_ARM_CONFIRM_PHRASE = "ARM REAL MONEY";
const PAYMENT_PROVIDER_LIVE_CONFIRM_PHRASE = "ARM PAYMENT PROVIDER LIVE";
const ARM_CONFIRM_KEYS = new Set<string>([
  "personal_account_ack",
  "no_pooled_capital_ack",
  "live_mode",
  "prefer_mt5",
  "owner_enable_live_trading",
  "live_trading_licensed",
  "owner_enable_broker_accept",
  "owner_enable_auto_deposit",
  "owner_enable_bank_card_movement",
  "owner_enable_payout_automation",
  "payout_destination_allowlisted",
]);

function armConfirmationForPatch(patch: Record<string, unknown>): string | null {
  if (["live", "production"].includes(String(patch.payment_provider_environment ?? "").trim().toLowerCase())) {
    return PAYMENT_PROVIDER_LIVE_CONFIRM_PHRASE;
  }
  const enabling = Object.entries(patch)
    .filter(([key, value]) => ARM_CONFIRM_KEYS.has(key) && value === true)
    .map(([key]) => key)
    .sort();
  if (enabling.length === 0) return null;
  if (enabling.length === 1) return `ARM ${enabling[0]}`;
  return REAL_MONEY_ARM_CONFIRM_PHRASE;
}

function requestArmConfirmation(phrase: string): string | null {
  return window.prompt(`Type exactly "${phrase}" to arm this live/money authority switch.`, "");
}

function confirmRequiredMessage(payload: { need_confirmation?: string | null }): string {
  return `Type exactly "${payload.need_confirmation ?? REAL_MONEY_ARM_CONFIRM_PHRASE}" to arm this live/money authority switch.`;
}

function ToggleSwitch({
  on,
  busy,
  onClick,
  label,
}: {
  on: boolean;
  busy: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      className="go-live-switch"
      data-on={on}
      disabled={busy}
      aria-pressed={on}
      aria-label={`${label} — ${on ? "on" : "off"}`}
      onClick={onClick}
    >
      <span className="knob" />
    </button>
  );
}

function GoLivePanel() {
  const [le, setLe] = useState<LiveEnableState | null>(null);
  const [busyKey, setBusyKey] = useState<string>("");
  const [status, setStatus] = useState<string>("");

  useEffect(() => {
    void fetchLiveEnable().then((s) => { if (s) setLe(s); });
  }, []);

  async function toggle(key: LiveEnableKey, next: boolean) {
    setBusyKey(key);
    setStatus("");
    try {
      const patch: Partial<Record<LiveEnableKey, boolean>> & { confirm?: string } = { [key]: next };
      const phrase = armConfirmationForPatch(patch);
      if (phrase) {
        const confirm = requestArmConfirmation(phrase);
        if (confirm == null) {
          setStatus("Owner confirmation canceled; no switch changed.");
          return;
        }
        patch.confirm = confirm;
      }
      const saved = await updateLiveEnable(patch);
      if (saved.status === "CONFIRM_REQUIRED") {
        setStatus(confirmRequiredMessage(saved));
        return;
      }
      setLe(saved);
    } catch {
      setStatus("Couldn't save — is the API reachable? Check the address above.");
    } finally {
      setBusyKey("");
    }
  }

  async function reset() {
    setBusyKey("__reset__");
    setStatus("");
    try {
      setLe(await resetLiveEnable());
      setStatus("Reset to config / env defaults.");
    } catch {
      setStatus("Couldn't reset.");
    } finally {
      setBusyKey("");
    }
  }

  const flagFor = (key: LiveEnableKey) => le?.flags.find((f) => f.key === key);
  const authorized = le?.live_authorized ?? false;
  const missing = le?.still_missing ?? [];
  const authorityModel = le?.owner_authority_model;

  return (
    <GlassPanel
      title="Go Live — Owner Switches"
      subtitle="Paper/demo can run now; these owner switches control the separate live broker authority path"
      variant={authorized ? "default" : "warning"}
    >
      {/* Live readout: AUTHORIZED vs exactly what is still missing */}
      <div
        style={{
          marginBottom: 14,
          padding: "10px 12px",
          borderRadius: "var(--radius-sm)",
          background: authorized ? "rgba(34,197,94,0.12)" : "var(--warning-dim)",
          border: `1px solid ${authorized ? "rgba(34,197,94,0.4)" : "var(--warning-dim)"}`,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <StatusChip
            label={authorized ? "LIVE-TRADING GATE: AUTHORIZED" : "LIVE-TRADING GATE: STANDBY"}
            variant={authorized ? "success" : "warning"}
            size="sm"
          />
        </div>
        {le && !authorized && missing.length > 0 && (
          <div style={{ marginTop: 8 }}>
            <div className="control-field-desc" style={{ color: "var(--warning)", fontWeight: 600 }}>
              Live authority still waiting for:
            </div>
            <ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>
              {missing.map((m) => (
                <li key={m} className="control-field-desc" style={{ color: "var(--text-secondary)" }}>{m}</li>
              ))}
            </ul>
          </div>
        )}
        {le == null && (
          <div className="control-field-desc" style={{ marginTop: 6 }}>Loading live-enable state…</div>
        )}
      </div>

      <AuthorityModelStrip model={authorityModel} />

      {/* The toggles, grouped */}
      <div style={{ display: "grid", gap: 4 }}>
        {GO_LIVE_GROUPS.map((group) => (
          <div key={group.title}>
            <div className="go-live-group-title">{group.title}</div>
            {group.keys.map((key) => {
              const f = flagFor(key);
              const on = f?.enabled ?? false;
              return (
                <div key={key} className="go-live-row">
                  <ToggleSwitch
                    on={on}
                    busy={busyKey === key}
                    label={f?.label ?? key}
                    onClick={() => void toggle(key, !on)}
                  />
                  <div className="go-live-row-body">
                    <div className="go-live-row-label">
                      {f?.label ?? key}
                      {f?.overridden && (
                        <span style={{ marginLeft: 6, fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                          (set in-app)
                        </span>
                      )}
                    </div>
                    <div className="go-live-row-consequence">{f?.consequence ?? ""}</div>
                  </div>
                </div>
              );
            })}
          </div>
        ))}
      </div>

      <div className="mobile-api-row" style={{ marginTop: 14 }}>
        <button
          className="mobile-api-button ghost"
          type="button"
          disabled={busyKey === "__reset__"}
          onClick={() => void reset()}
        >
          Reset to defaults
        </button>
      </div>
      {status && (
        <div className="control-field-desc" style={{ color: status.startsWith("Couldn't") ? "var(--danger)" : "var(--success)" }}>
          {status}
        </div>
      )}

      {/* Honest caveat — visible always, never one accidental tap from real money */}
      <div
        style={{
          marginTop: 14,
          padding: "8px 12px",
          background: "var(--panel-dim)",
          borderRadius: "var(--radius-sm)",
          fontSize: "0.8125rem",
          color: "var(--text-secondary)",
        }}
      >
        <strong>What these switches do:</strong> they satisfy the owner live-trading authority gate -
        they do
        <strong> not</strong> place any order by themselves. A real order also needs a
        <strong> connected broker/feed path</strong>, a <strong>fresh edge authorization</strong> when the
        loop requires one, and the broker bridge re-checks owner authorization at order time.
        Flipping every switch here delegates live authority; inside that envelope the AI can
        act without per-order confirmation only through the dispatch path and order-time checks.
      </div>
    </GlassPanel>
  );
}

function AuthorizePanel() {
  const [auth, setAuth] = useState<AuthorizationState | null>(null);
  const [busyKey, setBusyKey] = useState<string>("");
  const [status, setStatus] = useState<string>("");
  const [provider, setProvider] = useState("");
  const [providerEnvironment, setProviderEnvironment] = useState("sandbox");
  const [apiKey, setApiKey] = useState("");
  const [providerBaseUrl, setProviderBaseUrl] = useState("");
  const [providerAccountId, setProviderAccountId] = useState("");
  const [destId, setDestId] = useState("");

  function loadProviderDraft(s: AuthorizationState) {
    setProvider(s.provider.payment_provider ?? "");
    setProviderEnvironment(s.provider.payment_provider_environment ?? "sandbox");
    setProviderBaseUrl(s.provider.payment_provider_base_url ?? "");
    setProviderAccountId(s.provider.payment_provider_account_id ?? "");
    setDestId(s.provider.payout_destination_id ?? "");
    // api key is never returned — keep the field blank (it stays set on the server).
  }

  useEffect(() => {
    void fetchAuthorization().then((s) => { if (s) { setAuth(s); loadProviderDraft(s); } });
  }, []);

  async function apply(patch: AuthorizationPatch, key: string, okMessage = "Saved.") {
    setBusyKey(key);
    setStatus("");
    try {
      const phrase = armConfirmationForPatch(patch);
      const body: AuthorizationPatch = { ...patch };
      if (phrase) {
        const confirm = requestArmConfirmation(phrase);
        if (confirm == null) {
          setStatus("Owner confirmation canceled; no switch changed.");
          return;
        }
        body.confirm = confirm;
      }
      const s = await updateAuthorization(body);
      if (s.status === "CONFIRM_REQUIRED") {
        setStatus(confirmRequiredMessage(s));
        return;
      }
      setAuth(s);
      loadProviderDraft(s);
      emitLiveMoneyProgressionRefresh();
      setStatus(okMessage);
    } catch {
      setStatus("Couldn't save — is the API reachable? Check the address above.");
    } finally {
      setBusyKey("");
    }
  }

  async function reset() {
    setBusyKey("__reset__");
    setStatus("");
    try {
      await resetLiveEnable();
      const s = await fetchAuthorization();
      if (s) { setAuth(s); loadProviderDraft(s); setApiKey(""); }
      emitLiveMoneyProgressionRefresh();
      setStatus("Reset to config / env defaults.");
    } catch {
      setStatus("Couldn't reset.");
    } finally {
      setBusyKey("");
    }
  }

  const allGreen = Boolean(auth?.all_real_money_authorized && auth?.provider.real_money_provider_ready);
  const authorityModel = auth?.owner_authority_model;

  return (
    <GlassPanel
      title="Path to Authorize Everything — Owner Switches"
      subtitle="Flip every live-money capability ON from here — no .env, no restart"
      variant={allGreen ? "default" : "warning"}
    >
      <div style={{ marginBottom: 12, fontSize: "0.875rem", color: "var(--text-secondary)" }}>
        {auth?.summary ?? "Loading owner-controlled capabilities…"}
      </div>

      <AuthorityModelStrip model={authorityModel} />

      <div className="control-field-desc" style={{ marginBottom: 10 }}>
        This surface authorizes gates and saves provider scaffolding. It does not make payouts live by itself, and unsupported provider labels stay simulated at runtime.
      </div>

      <div style={{ display: "grid", gap: 4 }}>
        {(auth?.capabilities ?? []).map((cap) => (
          <div key={cap.capability} style={{ padding: "10px 0", borderBottom: "1px solid var(--border-subtle)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
              <span style={{ fontWeight: 700, fontSize: "0.875rem" }}>{cap.title}</span>
              <StatusChip
                label={cap.authorized ? "AUTHORIZED" : "NOT YET"}
                variant={cap.authorized ? "success" : "warning"}
                size="sm"
              />
            </div>
            <div style={{ display: "grid", gap: 4, marginTop: 8 }}>
              {cap.toggles.map((t) => (
                <div key={t.key} className="go-live-row" style={{ borderBottom: "none", padding: "4px 0" }}>
                  <ToggleSwitch
                    on={t.enabled}
                    busy={busyKey === t.key}
                    label={t.label}
                    onClick={() => void apply({ [t.key]: !t.enabled } as AuthorizationPatch, t.key)}
                  />
                  <div className="go-live-row-body">
                    <div className="go-live-row-label">{t.label}{t.overridden && <span style={{ marginLeft: 6, fontSize: "0.75rem", color: "var(--text-secondary)" }}>(set in-app)</span>}</div>
                    <div className="go-live-row-consequence">{t.consequence}</div>
                  </div>
                </div>
              ))}
            </div>
            {!cap.authorized && cap.missing_requirements.length > 0 && (
              <div className="control-field-desc" style={{ color: "var(--warning)", marginTop: 4 }}>
                Still missing: {cap.missing_requirements.join("; ")}
              </div>
            )}
            {cap.note && <div className="control-field-desc" style={{ marginTop: 2 }}>{cap.note}</div>}
          </div>
        ))}
      </div>

      {/* Shared payment provider (for deposits / movement / payouts / sweep ledger) */}
      <div className="go-live-group-title" style={{ marginTop: 14 }}>Payment provider (deposits · movement · payout / sweep ledger)</div>
      <MoneyMovementSetupStatus
        auth={auth}
        receiptVerified={false}
        receiptStatusLabel="REQUIRED"
        receiptDetail="Open Proof or the live-money progression lane to verify broker receipt and payout evidence."
      />
      <div style={{ display: "grid", gap: 10, marginTop: 6 }}>
        <div className="control-field">
          <span className="field-label">Provider name</span>
          <input className="mobile-api-input" value={provider} placeholder="broker_webhook or simulated"
            onChange={(e) => { setProvider(e.target.value); setStatus(""); }} />
        </div>
        <div className="control-field">
          <span className="field-label">Provider environment</span>
          <select
            className="mobile-api-input"
            value={providerEnvironment}
            onChange={(e) => { setProviderEnvironment(e.target.value); setStatus(""); }}
          >
            <option value="sandbox">Sandbox contract test</option>
            <option value="live">Live broker middleware</option>
          </select>
          <div className="control-field-desc">
            Sandbox uses the same HTTP contract but cannot satisfy real-money readiness. Live requires one owner setup confirmation.
          </div>
        </div>
        <div className="control-field">
          <span className="field-label">Provider API key{auth?.provider.payment_api_key_set ? " — set ✓" : ""}</span>
          <input className="mobile-api-input" type="password" value={apiKey}
            placeholder={auth?.provider.payment_api_key_set ? "•••••• (leave blank to keep)" : "your provider API key"}
            autoComplete="off"
            onChange={(e) => { setApiKey(e.target.value); setStatus(""); }} />
          <div className="control-field-desc">Saved here as a local encrypted runtime envelope; static .env/config keys remain a fallback. The key is never shown back here.</div>
        </div>
        <div className="control-field">
          <span className="field-label">Broker funding middleware URL</span>
          <input className="mobile-api-input" value={providerBaseUrl} placeholder="https://funding.your-domain.example"
            onChange={(e) => { setProviderBaseUrl(e.target.value); setStatus(""); }} />
        </div>
        <div className="control-field">
          <span className="field-label">Bound broker account ID</span>
          <input className="mobile-api-input" value={providerAccountId} placeholder="provider-side broker account id"
            onChange={(e) => { setProviderAccountId(e.target.value); setStatus(""); }} />
        </div>
        <div className="control-field">
          <span className="field-label">Payout destination id</span>
          <input className="mobile-api-input" value={destId} placeholder="allowlisted destination id"
            onChange={(e) => { setDestId(e.target.value); setStatus(""); }} />
        </div>
        <div className="go-live-row" style={{ borderBottom: "none" }}>
          <ToggleSwitch
            on={auth?.provider.payout_destination_allowlisted ?? false}
            busy={busyKey === "payout_destination_allowlisted"}
            label={auth?.provider.allowlist_label ?? "Payout destination allowlisted"}
            onClick={() => void apply({ payout_destination_allowlisted: !(auth?.provider.payout_destination_allowlisted ?? false) }, "payout_destination_allowlisted")}
          />
          <div className="go-live-row-body">
            <div className="go-live-row-label">{auth?.provider.allowlist_label ?? "Payout destination allowlisted"}</div>
            <div className="go-live-row-consequence">Owner confirms the payout destination is approved.</div>
          </div>
        </div>
        <div className="mobile-api-row">
          <button className="mobile-api-button" type="button" disabled={busyKey === "__provider__"}
            onClick={() => {
              const patch: AuthorizationPatch = {
                payment_provider: provider,
                payment_provider_environment: providerEnvironment,
                payment_provider_base_url: providerBaseUrl,
                payment_provider_account_id: providerAccountId,
                payout_destination_id: destId,
              };
              if (apiKey.trim()) patch.payment_api_key = apiKey.trim();
              void apply(
                patch,
                "__provider__",
                "Provider configuration saved. Withdrawals and payouts stay scaffolded until the runtime rail, owner gate, allowlist, and receipt checks are all ready.",
              ).then(() => setApiKey(""));
            }}>
            Save provider
          </button>
          <button className="mobile-api-button ghost" type="button" disabled={busyKey === "__reset__"} onClick={() => void reset()}>
            Reset all to defaults
          </button>
        </div>
      </div>

      {status && <div className="control-field-desc" style={{ color: status.startsWith("Couldn't") ? "var(--danger)" : "var(--success)" }}>{status}</div>}

      <div style={{ marginTop: 14, padding: "8px 12px", background: "var(--panel-dim)", borderRadius: "var(--radius-sm)", fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
        <strong>What these switches do:</strong> they satisfy the owner-authorization gate for each capability — they do
        <strong> not</strong> move money or place orders by themselves. Money movement also needs a runtime-supported payment provider + API
        key, broker middleware URL, bound account ID, and a running process. Stripe alone is not a Hugo's Way/MT5 custody rail. Once owner-armed,
        AI agents may act inside the delegated envelope without per-action confirmation, but cannot exceed caps, bypass allowlists, or skip receipts.
      </div>
    </GlassPanel>
  );
}

const BROKER_REALITY_TEXT_FIELDS = [
  ["broker_entity", "Broker entity / jurisdiction"],
  ["withdrawal_minimum", "Withdrawal minimum"],
  ["withdrawal_timing", "Withdrawal timing"],
  ["kyc_requirements", "KYC requirements"],
  ["withdrawal_fees", "Withdrawal fees"],
  ["currency_conversion", "Currency conversion"],
  ["automation_tos", "Automation terms"],
  ["notes", "Owner notes"],
] as const;

const BROKER_REALITY_CHECKS = [
  ["broker_entity_reviewed", "Broker entity reviewed"],
  ["withdrawal_minimum_reviewed", "Withdrawal minimum reviewed"],
  ["withdrawal_timing_reviewed", "Withdrawal timing reviewed"],
  ["kyc_requirements_reviewed", "KYC requirements reviewed"],
  ["withdrawal_fees_reviewed", "Withdrawal fees reviewed"],
  ["currency_conversion_reviewed", "Currency conversion reviewed"],
  ["automation_tos_reviewed", "Automation terms reviewed"],
  ["owner_accepts_broker_terms", "Owner accepts broker terms"],
] as const;

function BrokerRealityPanel({ initialReview }: { initialReview?: BrokerRealityReview }) {
  const [review, setReview] = useState<BrokerRealityReview | null>(initialReview ?? null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [checks, setChecks] = useState<Record<string, boolean>>({});
  const [automationAllowed, setAutomationAllowed] = useState(false);
  const [sourceText, setSourceText] = useState("");
  const [busy, setBusy] = useState(false);
  const [ownerConfirm, setOwnerConfirm] = useState(false);
  const [status, setStatus] = useState("");

  function load(next: BrokerRealityReview) {
    setReview(next);
    const textDraft: Record<string, string> = {
      broker_id: next.broker_id,
      review_valid_days: String(next.review_valid_days ?? 30),
    };
    for (const [key] of BROKER_REALITY_TEXT_FIELDS) {
      textDraft[key] = String(next[key] ?? "");
    }
    setDraft(textDraft);
    setChecks(next.checks ?? {});
    setAutomationAllowed(Boolean(next.automation_allowed_by_owner_review));
    setSourceText((next.source_urls ?? []).join("\n"));
  }

  useEffect(() => {
    if (initialReview) load(initialReview);
  }, [initialReview]);

  useEffect(() => {
    void fetchBrokerRealityReview().then((payload) => { if (payload) load(payload); });
  }, []);

  function payload(): BrokerRealityUpdate {
    const out: BrokerRealityUpdate = {
      broker_id: draft.broker_id || review?.broker_id || "risenfx",
      source_urls: sourceText.split(/\r?\n/).map((item) => item.trim()).filter(Boolean),
      automation_allowed_by_owner_review: automationAllowed,
      review_valid_days: Number(draft.review_valid_days || 30),
    };
    for (const [key] of BROKER_REALITY_TEXT_FIELDS) {
      out[key] = draft[key] ?? "";
    }
    for (const [key] of BROKER_REALITY_CHECKS) {
      out[key] = Boolean(checks[key]);
    }
    return out;
  }

  async function save(confirm: boolean) {
    if (busy) return;
    if (confirm && !ownerConfirm) {
      setStatus("Cannot record Owner ACCEPT until Owner Confirm is checked.");
      return;
    }
    setBusy(true);
    setStatus("");
    try {
      const next = await updateBrokerRealityReview(payload(), confirm);
      load(next);
      setOwnerConfirm(false);
      emitLiveMoneyProgressionRefresh();
      setStatus(confirm ? "Broker reality review recorded as ACCEPT." : "Broker reality draft saved as OPEN.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Couldn't save broker reality review.");
    } finally {
      setBusy(false);
    }
  }

  async function reset() {
    if (busy) return;
    setBusy(true);
    setStatus("");
    try {
      const next = await resetBrokerRealityReview(draft.broker_id || review?.broker_id);
      load(next);
      setOwnerConfirm(false);
      emitLiveMoneyProgressionRefresh();
      setStatus("Broker reality review reset to OPEN.");
    } catch {
      setStatus("Couldn't reset broker reality review.");
    } finally {
      setBusy(false);
    }
  }

  const accepted = review?.accepted_for_live_and_payout ?? false;

  return (
    <GlassPanel
      title="Broker Reality Review"
      subtitle="Withdrawal, KYC, fee, currency, entity, and automation terms"
      variant={accepted ? "default" : "danger"}
    >
      <div className="sweep-status-row" style={{ marginBottom: 10 }}>
        <StatusChip label={review?.owner_review_status ?? "OPEN"} variant={accepted ? "success" : "danger"} size="sm" />
        <StatusChip label={accepted ? "OWNER ACCEPT" : "OWNER REVIEW OPEN"} variant={accepted ? "success" : "warning"} size="sm" />
        <StatusChip label={`${review?.missing_requirements?.length ?? 0} MISSING`} variant={accepted ? "success" : "warning"} size="sm" />
      </div>

      <div className="control-grid">
        <div className="control-field">
          <span className="field-label">Broker id</span>
          <input className="mobile-api-input" value={draft.broker_id ?? "risenfx"} onChange={(event) => setDraft({ ...draft, broker_id: event.target.value })} />
          <div className="control-field-desc">{review?.broker_display_name ?? "Selected broker"} · {review?.broker_website ?? ""}</div>
        </div>
        <div className="control-field">
          <span className="field-label">Review valid days</span>
          <input className="mobile-api-input" type="number" min={1} max={365} value={draft.review_valid_days ?? "30"} onChange={(event) => setDraft({ ...draft, review_valid_days: event.target.value })} />
          <div className="control-field-desc">Terms change; stale reviews reopen the gate.</div>
        </div>
      </div>

      <div className="broker-reality-grid">
        {BROKER_REALITY_TEXT_FIELDS.map(([key, label]) => (
          <label key={key} className="broker-reality-field">
            <span className="field-label">{label}</span>
            <textarea className="mobile-api-input broker-reality-textarea" value={draft[key] ?? ""} onChange={(event) => setDraft({ ...draft, [key]: event.target.value })} />
          </label>
        ))}
        <label className="broker-reality-field broker-reality-wide">
          <span className="field-label">Source URLs</span>
          <textarea className="mobile-api-input broker-reality-textarea" value={sourceText} onChange={(event) => setSourceText(event.target.value)} />
          <div className="control-field-desc">One source per line. Sources are owner review evidence, not agent approval.</div>
        </label>
      </div>

      <div className="broker-reality-check-grid">
        {BROKER_REALITY_CHECKS.map(([key, label]) => (
          <label key={key} className="sweep-confirm-check">
            <input type="checkbox" checked={Boolean(checks[key])} onChange={(event) => setChecks({ ...checks, [key]: event.target.checked })} />
            <span>{label}</span>
          </label>
        ))}
        <label className="sweep-confirm-check">
          <input type="checkbox" checked={automationAllowed} onChange={(event) => setAutomationAllowed(event.target.checked)} />
          <span>Automation allowed by owner review</span>
        </label>
      </div>

      {review && !accepted && review.missing_requirements.length > 0 && (
        <div className="control-field-desc" style={{ color: "var(--danger)", marginTop: 8 }}>
          Missing: {review.missing_requirements.join("; ")}
        </div>
      )}

      <div className="sweep-action-row" style={{ marginTop: 12 }}>
        <button className="broker-risk-apply-button" type="button" disabled={busy} onClick={() => void save(false)}>Save Draft</button>
        <label className="sweep-confirm-check">
          <input type="checkbox" checked={ownerConfirm} onChange={(event) => setOwnerConfirm(event.target.checked)} />
          <span>Owner Confirm</span>
        </label>
        <button className="sweep-action-button danger" type="button" disabled={busy} onClick={() => void save(true)}>Owner ACCEPT</button>
        <button className="mobile-api-button ghost" type="button" disabled={busy} onClick={() => void reset()}>Reset</button>
      </div>

      {status && <div className="control-field-desc" style={{ marginTop: 8, color: status.includes("Couldn't") || status.includes("Cannot") || status.includes("API") ? "var(--danger)" : "var(--success)" }}>{status}</div>}
      <div className="control-field-desc" style={{ marginTop: 8 }}>
        {review?.claim_boundary ?? "Only the owner can mark broker reality ACCEPT. This panel does not authorize live trading or money movement by itself."}
      </div>
    </GlassPanel>
  );
}

const LIVE_PILOT_RISK_FIELDS = [
  ["max_trade_risk_pct_equity", "Max stop risk per trade (% equity)"],
  ["max_daily_loss_usd", "Max daily realized loss USD"],
  ["max_total_loss_usd", "Max authority loss USD"],
] as const;

const LIVE_PILOT_LEGACY_FIELDS = [
  ["max_trade_lots", "Legacy max trade lots"],
  ["max_open_live_lots", "Legacy max open lots"],
  ["max_live_trade_count", "Legacy max live trades"],
  ["max_pilot_days", "Legacy max pilot days"],
] as const;

const LIVE_PILOT_NUMBER_FIELDS = [...LIVE_PILOT_RISK_FIELDS, ...LIVE_PILOT_LEGACY_FIELDS] as const;

const LIVE_PILOT_CHECKS = [
  ["owner_understands_real_money_risk", "Owner understands real-money risk"],
  ["owner_confirms_risk_denominated_sizing", "Lot size follows stop risk, margin, and exposure"],
  ["owner_confirms_autonomous_scaling_within_envelope", "Operator may scale autonomously inside the envelope"],
  ["owner_confirms_emergency_stop_ready", "Emergency stop is ready"],
] as const;

function LivePilotPanel({ initialPolicy }: { initialPolicy?: LivePilotPolicy }) {
  const [policy, setPolicy] = useState<LivePilotPolicy | null>(initialPolicy ?? null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [checks, setChecks] = useState<Record<string, boolean>>({});
  const [symbolsText, setSymbolsText] = useState("");
  const [sizingMode, setSizingMode] = useState("RISK_DENOMINATED");
  const [busy, setBusy] = useState(false);
  const [ownerConfirm, setOwnerConfirm] = useState(false);
  const [status, setStatus] = useState("");

  function load(next: LivePilotPolicy) {
    setPolicy(next);
    const textDraft: Record<string, string> = { notes: next.notes ?? "" };
    for (const [key] of LIVE_PILOT_NUMBER_FIELDS) {
      textDraft[key] = String(next[key] ?? "");
    }
    setDraft(textDraft);
    setChecks(next.checks ?? {});
    setSizingMode(next.sizing_mode ?? "RISK_DENOMINATED");
    setSymbolsText((next.allowed_symbols ?? []).join("\n"));
  }

  useEffect(() => {
    if (initialPolicy) load(initialPolicy);
  }, [initialPolicy]);

  useEffect(() => {
    void fetchLivePilotPolicy().then((payload) => { if (payload) load(payload); });
  }, []);

  function payload(): LivePilotUpdate {
    const out: LivePilotUpdate = {
      allowed_symbols: symbolsText.split(/\r?\n/).map((item) => item.trim()).filter(Boolean),
      notes: draft.notes ?? "",
      sizing_mode: sizingMode,
      continuous_authority: sizingMode === "RISK_DENOMINATED",
    };
    for (const [key] of LIVE_PILOT_NUMBER_FIELDS) {
      const value = draft[key];
      if (value !== undefined && value.trim() !== "") {
        out[key] = Number(value);
      }
    }
    for (const [key] of LIVE_PILOT_CHECKS) {
      out[key] = Boolean(checks[key]);
    }
    return out;
  }

  async function save(confirm: boolean) {
    if (busy) return;
    if (confirm && !ownerConfirm) {
      setStatus("Cannot record Owner ACCEPT until Owner Confirm is checked.");
      return;
    }
    setBusy(true);
    setStatus("");
    try {
      const next = await updateLivePilotPolicy(payload(), confirm);
      load(next);
      setOwnerConfirm(false);
      emitLiveMoneyProgressionRefresh();
      setStatus(confirm ? "Live risk authority recorded as ACCEPT." : "Live risk authority draft saved as OPEN.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Couldn't save live pilot policy.");
    } finally {
      setBusy(false);
    }
  }

  async function reset() {
    if (busy) return;
    setBusy(true);
    setStatus("");
    try {
      const next = await resetLivePilotPolicy();
      load(next);
      setOwnerConfirm(false);
      emitLiveMoneyProgressionRefresh();
      setStatus("Live risk authority reset to OPEN.");
    } catch {
      setStatus("Couldn't reset live pilot policy.");
    } finally {
      setBusy(false);
    }
  }

  const ready = policy?.ready_for_next_live_order ?? false;
  const accepted = policy?.accepted_for_live_start ?? false;

  return (
    <GlassPanel
      title="Live Risk Authority"
      subtitle="Continuous autonomous sizing inside broker-valued risk limits"
      variant={ready ? "default" : "danger"}
    >
      <div className="sweep-status-row" style={{ marginBottom: 10 }}>
        <StatusChip label={policy?.owner_pilot_status ?? "OPEN"} variant={accepted ? "success" : "danger"} size="sm" />
        <StatusChip label={ready ? "PILOT READY" : "PILOT NOT READY"} variant={ready ? "success" : "warning"} size="sm" />
        <StatusChip label={policy?.continuous_authority ? "CONTINUOUS AUTHORITY" : `${policy?.pilot_capacity_remaining ?? 0} TESTS LEFT`} variant={ready ? "success" : "warning"} size="sm" />
      </div>

      <div className="control-grid">
        <label className="control-field">
          <span className="field-label">Allowed symbols</span>
          <textarea className="mobile-api-input broker-reality-textarea" value={symbolsText} onChange={(event) => setSymbolsText(event.target.value)} />
          <div className="control-field-desc">One symbol per line. First live orders cannot use symbols outside this list.</div>
        </label>
        <label className="control-field">
          <span className="field-label">Sizing authority</span>
          <select className="mobile-api-input" value={sizingMode} onChange={(event) => setSizingMode(event.target.value)}>
            <option value="RISK_DENOMINATED">Risk-denominated autonomous</option>
            <option value="ABSOLUTE_LOTS">Legacy fixed-lot pilot</option>
          </select>
          <div className="control-field-desc">Risk mode permits any broker-valid lot size that stays inside stop-risk, margin, and exposure limits.</div>
        </label>
        <label className="control-field">
          <span className="field-label">Owner notes</span>
          <textarea className="mobile-api-input broker-reality-textarea" value={draft.notes ?? ""} onChange={(event) => setDraft({ ...draft, notes: event.target.value })} />
          <div className="control-field-desc">Notes stay in the pilot audit record.</div>
        </label>
        {(sizingMode === "RISK_DENOMINATED" ? LIVE_PILOT_RISK_FIELDS : LIVE_PILOT_LEGACY_FIELDS).map(([key, label]) => (
          <label key={key} className="control-field">
            <span className="field-label">{label}</span>
            <input className="mobile-api-input" type="number" min={0} step="0.01" value={draft[key] ?? ""} onChange={(event) => setDraft({ ...draft, [key]: event.target.value })} />
          </label>
        ))}
      </div>

      <div className="broker-reality-check-grid">
        {LIVE_PILOT_CHECKS.map(([key, label]) => (
          <label key={key} className="sweep-confirm-check">
            <input type="checkbox" checked={Boolean(checks[key])} onChange={(event) => setChecks({ ...checks, [key]: event.target.checked })} />
            <span>{label}</span>
          </label>
        ))}
      </div>

      {policy && !ready && policy.missing_requirements.length > 0 && (
        <div className="control-field-desc" style={{ color: "var(--danger)", marginTop: 8 }}>
          Missing: {policy.missing_requirements.join("; ")}
        </div>
      )}

      <div className="sweep-action-row" style={{ marginTop: 12 }}>
        <button className="broker-risk-apply-button" type="button" disabled={busy} onClick={() => void save(false)}>Save Draft</button>
        <label className="sweep-confirm-check">
          <input type="checkbox" checked={ownerConfirm} onChange={(event) => setOwnerConfirm(event.target.checked)} />
          <span>Owner Confirm</span>
        </label>
        <button className="sweep-action-button danger" type="button" disabled={busy} onClick={() => void save(true)}>Owner ACCEPT</button>
        <button className="mobile-api-button ghost" type="button" disabled={busy} onClick={() => void reset()}>Reset</button>
      </div>

      {status && <div className="control-field-desc" style={{ marginTop: 8, color: status.includes("Couldn't") || status.includes("Cannot") || status.includes("API") ? "var(--danger)" : "var(--success)" }}>{status}</div>}
      <div className="control-field-desc" style={{ marginTop: 8 }}>
        {policy?.claim_boundary ?? "The live authority permits autonomous sizing only inside fresh stop-risk, margin, exposure, and broker-truth gates."}
      </div>
    </GlassPanel>
  );
}

function LiveRecoveryPanel({
  initialReport,
  initialAudit,
  initialRecoveryPacket,
  initialTerminalReceiptPacket,
  initialBrokerTruth,
  initialLiveMoneyProgression,
  initialWasteDirectionReview,
  initialWasteDirectionLearning,
  initialWasteDirectionOutcomeBinding,
  initialWastePaperSampleCollector,
  initialWastePaperSampleCollectorScheduler,
  initialWasteAdaptationPromotionRule,
  initialWasteAdaptationPlan,
  initialWasteAdaptationApplyPreview,
  initialWasteAdaptationOwnerReview,
  initialWasteAdaptationPaperApply,
}: {
  initialReport?: LiveRecoveryReport;
  initialAudit?: OrderAttemptAuditStatus;
  initialRecoveryPacket?: OrderAttemptRecoveryPacket;
  initialTerminalReceiptPacket?: TerminalReceiptRecoveryPacket | null;
  initialBrokerTruth?: BrokerTruthMonitorStatus | null;
  initialLiveMoneyProgression?: LiveMoneyProgressionPacket | null;
  initialWasteDirectionReview?: WasteDirectionReviewPacket | null;
  initialWasteDirectionLearning?: WasteDirectionLearningLedger | null;
  initialWasteDirectionOutcomeBinding?: WasteDirectionOutcomeBinding | null;
  initialWastePaperSampleCollector?: WastePaperSampleCollector | null;
  initialWastePaperSampleCollectorScheduler?: WastePaperSampleCollectorScheduler | null;
  initialWasteAdaptationPromotionRule?: WasteAdaptationPromotionRule | null;
  initialWasteAdaptationPlan?: WasteAdaptationPlan | null;
  initialWasteAdaptationApplyPreview?: WasteAdaptationApplyPreview | null;
  initialWasteAdaptationOwnerReview?: WasteAdaptationOwnerReview | null;
  initialWasteAdaptationPaperApply?: WasteAdaptationPaperApply | null;
}) {
  const [report, setReport] = useState<LiveRecoveryReport | null>(initialReport ?? null);
  const [brokerTruthMonitor, setBrokerTruthMonitor] = useState<BrokerTruthMonitorStatus | null>(initialBrokerTruth ?? null);
  const [brokerTruthRecoveryPacket, setBrokerTruthRecoveryPacket] = useState<BrokerTruthRecoveryPacket | null>(null);
  const [liveMoneyProgression, setLiveMoneyProgression] = useState<LiveMoneyProgressionPacket | null>(initialLiveMoneyProgression ?? null);
  const [wasteDirectionReview, setWasteDirectionReview] = useState<WasteDirectionReviewPacket | null>(initialWasteDirectionReview ?? null);
  const [wasteDirectionLearning, setWasteDirectionLearning] = useState<WasteDirectionLearningLedger | null>(initialWasteDirectionLearning ?? null);
  const [wasteDirectionOutcomeBinding, setWasteDirectionOutcomeBinding] = useState<WasteDirectionOutcomeBinding | null>(initialWasteDirectionOutcomeBinding ?? null);
  const [wastePaperSampleCollector, setWastePaperSampleCollector] = useState<WastePaperSampleCollector | null>(initialWastePaperSampleCollector ?? null);
  const [wastePaperSampleCollectorScheduler, setWastePaperSampleCollectorScheduler] = useState<WastePaperSampleCollectorScheduler | null>(initialWastePaperSampleCollectorScheduler ?? null);
  const [wasteAdaptationPromotionRule, setWasteAdaptationPromotionRule] = useState<WasteAdaptationPromotionRule | null>(initialWasteAdaptationPromotionRule ?? null);
  const [wasteAdaptationPlan, setWasteAdaptationPlan] = useState<WasteAdaptationPlan | null>(initialWasteAdaptationPlan ?? null);
  const [wasteAdaptationApplyPreview, setWasteAdaptationApplyPreview] = useState<WasteAdaptationApplyPreview | null>(initialWasteAdaptationApplyPreview ?? null);
  const [wasteAdaptationOwnerReview, setWasteAdaptationOwnerReview] = useState<WasteAdaptationOwnerReview | null>(initialWasteAdaptationOwnerReview ?? null);
  const [wasteAdaptationPaperApply, setWasteAdaptationPaperApply] = useState<WasteAdaptationPaperApply | null>(initialWasteAdaptationPaperApply ?? null);
  const [attemptAudit, setAttemptAudit] = useState<OrderAttemptAuditStatus | null>(initialAudit ?? null);
  const [recoveryPacket, setRecoveryPacket] = useState<OrderAttemptRecoveryPacket | null>(initialRecoveryPacket ?? null);
  const [terminalReceiptPacket, setTerminalReceiptPacket] = useState<TerminalReceiptRecoveryPacket | null>(initialTerminalReceiptPacket ?? null);
  const [terminalArchiveAction, setTerminalArchiveAction] = useState<TerminalReceiptArchiveAction | null>(null);
  const [terminalRefreshAction, setTerminalRefreshAction] = useState<TerminalReceiptRecoveryRefreshAction | null>(null);
  const [selectedAttemptId, setSelectedAttemptId] = useState("");
  const [notes, setNotes] = useState("");
  const [ownerConfirm, setOwnerConfirm] = useState(false);
  const [ownerConfirmReconcile, setOwnerConfirmReconcile] = useState(false);
  const [ownerConfirmArchive, setOwnerConfirmArchive] = useState(false);
  const [ownerConfirmRefresh, setOwnerConfirmRefresh] = useState(false);
  const [ownerConfirmAdaptationReview, setOwnerConfirmAdaptationReview] = useState(false);
  const [ownerConfirmAdaptationApply, setOwnerConfirmAdaptationApply] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");

  async function refreshLiveMoneyProgression(refreshPacket = false): Promise<LiveMoneyProgressionPacket | null> {
    const progression = await fetchLiveMoneyProgressionPacket(refreshPacket);
    if (progression) setLiveMoneyProgression(progression);
    return progression;
  }

  function scheduleLiveMoneyProgressionRetries() {
    LIVE_MONEY_POST_WRITE_RETRY_DELAYS_MS.forEach((delayMs) => {
      window.setTimeout(() => {
        void refreshLiveMoneyProgression(false);
      }, delayMs);
    });
  }

  async function refreshLiveMoneyProgressionAfterWrite() {
    const progression = await refreshLiveMoneyProgression(true);
    if (isLiveMoneyProgressionWarming(progression)) scheduleLiveMoneyProgressionRetries();
  }

  useEffect(() => {
    if (initialReport) setReport(initialReport);
  }, [initialReport]);

  useEffect(() => {
    if (initialBrokerTruth) setBrokerTruthMonitor(initialBrokerTruth);
  }, [initialBrokerTruth]);

  useEffect(() => {
    if (initialLiveMoneyProgression) setLiveMoneyProgression(initialLiveMoneyProgression);
  }, [initialLiveMoneyProgression]);

  useEffect(() => {
    if (initialWasteDirectionReview) setWasteDirectionReview(initialWasteDirectionReview);
  }, [initialWasteDirectionReview]);

  useEffect(() => {
    if (initialWasteDirectionLearning) setWasteDirectionLearning(initialWasteDirectionLearning);
  }, [initialWasteDirectionLearning]);

  useEffect(() => {
    if (initialWasteDirectionOutcomeBinding) setWasteDirectionOutcomeBinding(initialWasteDirectionOutcomeBinding);
  }, [initialWasteDirectionOutcomeBinding]);

  useEffect(() => {
    if (initialWastePaperSampleCollector) setWastePaperSampleCollector(initialWastePaperSampleCollector);
  }, [initialWastePaperSampleCollector]);

  useEffect(() => {
    if (initialWastePaperSampleCollectorScheduler) setWastePaperSampleCollectorScheduler(initialWastePaperSampleCollectorScheduler);
  }, [initialWastePaperSampleCollectorScheduler]);

  useEffect(() => {
    if (initialWasteAdaptationPromotionRule) setWasteAdaptationPromotionRule(initialWasteAdaptationPromotionRule);
  }, [initialWasteAdaptationPromotionRule]);

  useEffect(() => {
    if (initialWasteAdaptationPlan) setWasteAdaptationPlan(initialWasteAdaptationPlan);
  }, [initialWasteAdaptationPlan]);

  useEffect(() => {
    if (initialWasteAdaptationApplyPreview) setWasteAdaptationApplyPreview(initialWasteAdaptationApplyPreview);
  }, [initialWasteAdaptationApplyPreview]);

  useEffect(() => {
    if (initialWasteAdaptationOwnerReview) setWasteAdaptationOwnerReview(initialWasteAdaptationOwnerReview);
  }, [initialWasteAdaptationOwnerReview]);

  useEffect(() => {
    if (initialWasteAdaptationPaperApply) setWasteAdaptationPaperApply(initialWasteAdaptationPaperApply);
  }, [initialWasteAdaptationPaperApply]);

  useEffect(() => {
    if (initialAudit) setAttemptAudit(initialAudit);
  }, [initialAudit]);

  useEffect(() => {
    if (initialRecoveryPacket) setRecoveryPacket(initialRecoveryPacket);
  }, [initialRecoveryPacket]);

  useEffect(() => {
    if (initialTerminalReceiptPacket) setTerminalReceiptPacket(initialTerminalReceiptPacket);
  }, [initialTerminalReceiptPacket]);

  useEffect(() => {
    const refreshHandler = () => {
      void refreshLiveMoneyProgressionAfterWrite();
    };
    window.addEventListener(LIVE_MONEY_PROGRESS_REFRESH_EVENT, refreshHandler);
    return () => window.removeEventListener(LIVE_MONEY_PROGRESS_REFRESH_EVENT, refreshHandler);
  }, []);

  useEffect(() => {
    void Promise.all([
      fetchLiveRecoveryStatus(),
      fetchBrokerTruthMonitorStatus(),
      fetchBrokerTruthRecoveryPacket(),
      fetchOrderAttemptAudit(),
      fetchOrderAttemptRecoveryPacket(),
      fetchTerminalReceiptRecoveryPacket(),
      fetchLiveMoneyProgressionPacket(),
      fetchWasteDirectionReviewPacket(),
      fetchWasteDirectionLearningLedger(),
      fetchWasteDirectionOutcomeBinding(),
      fetchWastePaperSampleCollector(),
      fetchWastePaperSampleCollectorScheduler(),
      fetchWasteAdaptationPromotionRule(),
      fetchWasteAdaptationPlan(),
      fetchWasteAdaptationApplyPreview(),
      fetchWasteAdaptationOwnerReview(),
      fetchWasteAdaptationPaperApply(),
    ]).then(([payload, brokerTruth, brokerTruthPacket, audit, packet, terminalPacket, progression, directionReview, directionLearning, directionOutcomeBinding, paperSampleCollector, paperSampleScheduler, adaptationPromotionRule, adaptationPlan, adaptationApplyPreview, adaptationOwnerReview, adaptationPaperApply]) => {
      if (payload) setReport(payload);
      if (brokerTruth) setBrokerTruthMonitor(brokerTruth);
      if (brokerTruthPacket) setBrokerTruthRecoveryPacket(brokerTruthPacket);
      if (audit) setAttemptAudit(audit);
      if (packet) setRecoveryPacket(packet);
      if (terminalPacket) setTerminalReceiptPacket(terminalPacket);
      if (progression) setLiveMoneyProgression(progression);
      if (directionReview) setWasteDirectionReview(directionReview);
      if (directionLearning) setWasteDirectionLearning(directionLearning);
      if (directionOutcomeBinding) setWasteDirectionOutcomeBinding(directionOutcomeBinding);
      if (paperSampleCollector) setWastePaperSampleCollector(paperSampleCollector);
      if (paperSampleScheduler) setWastePaperSampleCollectorScheduler(paperSampleScheduler);
      if (adaptationPromotionRule) setWasteAdaptationPromotionRule(adaptationPromotionRule);
      if (adaptationPlan) setWasteAdaptationPlan(adaptationPlan);
      if (adaptationApplyPreview) setWasteAdaptationApplyPreview(adaptationApplyPreview);
      if (adaptationOwnerReview) setWasteAdaptationOwnerReview(adaptationOwnerReview);
      if (adaptationPaperApply) setWasteAdaptationPaperApply(adaptationPaperApply);
    });
  }, []);

  const unresolvedAttempts = recoveryPacket?.unresolved_real_attempts?.length
    ? recoveryPacket.unresolved_real_attempts
    : attemptAudit?.unresolved_real_attempts?.length
      ? attemptAudit.unresolved_real_attempts
      : unresolvedAttemptsFromRecovery(report);

  useEffect(() => {
    if (!unresolvedAttempts.length) {
      if (selectedAttemptId) setSelectedAttemptId("");
      return;
    }
    if (!selectedAttemptId || !unresolvedAttempts.some((attempt) => attempt.attempt_id === selectedAttemptId)) {
      setSelectedAttemptId(unresolvedAttempts[0]?.attempt_id ?? "");
    }
  }, [selectedAttemptId, unresolvedAttempts]);

  const selectedAttempt = unresolvedAttempts.find((attempt) => attempt.attempt_id === selectedAttemptId) ?? null;
  const selectedAttemptProvenance = recordOrNull(selectedAttempt?.execution_provenance);
  const selectedAttemptInitiator = recordOrNull(selectedAttemptProvenance?.initiator);
  const selectedAttemptRuntimeLane = recordOrNull(selectedAttemptProvenance?.runtime_lane);
  const selectedAttemptDispatchPath = recordOrNull(selectedAttemptProvenance?.dispatch_path);
  const selectedAttemptAudit = recordOrNull(selectedAttemptProvenance?.attempt_audit);

  async function refresh() {
    if (busy) return;
    setBusy(true);
    setStatus("");
    try {
      const [next, brokerTruthPacket, audit, packet, terminalPacket, progression, directionReview, directionLearning, directionOutcomeBinding, paperSampleCollector, paperSampleScheduler, adaptationPromotionRule, adaptationPlan, adaptationApplyPreview, adaptationOwnerReview, adaptationPaperApply] = await Promise.all([
        fetchLiveRecoveryStatus(),
        fetchBrokerTruthRecoveryPacket(),
        fetchOrderAttemptAudit(),
        fetchOrderAttemptRecoveryPacket(),
        fetchTerminalReceiptRecoveryPacket(),
        fetchLiveMoneyProgressionPacket(),
        fetchWasteDirectionReviewPacket(),
        fetchWasteDirectionLearningLedger(),
        fetchWasteDirectionOutcomeBinding(),
        fetchWastePaperSampleCollector(),
        fetchWastePaperSampleCollectorScheduler(),
        fetchWasteAdaptationPromotionRule(),
        fetchWasteAdaptationPlan(),
        fetchWasteAdaptationApplyPreview(),
        fetchWasteAdaptationOwnerReview(),
        fetchWasteAdaptationPaperApply(),
      ]);
      if (next) setReport(next);
      if (brokerTruthPacket) setBrokerTruthRecoveryPacket(brokerTruthPacket);
      if (audit) setAttemptAudit(audit);
      if (packet) setRecoveryPacket(packet);
      if (terminalPacket) setTerminalReceiptPacket(terminalPacket);
      if (progression) setLiveMoneyProgression(progression);
      if (directionReview) setWasteDirectionReview(directionReview);
      if (directionLearning) setWasteDirectionLearning(directionLearning);
      if (directionOutcomeBinding) setWasteDirectionOutcomeBinding(directionOutcomeBinding);
      if (paperSampleCollector) setWastePaperSampleCollector(paperSampleCollector);
      if (paperSampleScheduler) setWastePaperSampleCollectorScheduler(paperSampleScheduler);
      if (adaptationPromotionRule) setWasteAdaptationPromotionRule(adaptationPromotionRule);
      if (adaptationPlan) setWasteAdaptationPlan(adaptationPlan);
      if (adaptationApplyPreview) setWasteAdaptationApplyPreview(adaptationApplyPreview);
      if (adaptationOwnerReview) setWasteAdaptationOwnerReview(adaptationOwnerReview);
      if (adaptationPaperApply) setWasteAdaptationPaperApply(adaptationPaperApply);
      setStatus("Live recovery refreshed.");
    } finally {
      setBusy(false);
    }
  }

  async function accept() {
    if (busy) return;
    if (!ownerConfirm) {
      setStatus("Cannot record Owner ACCEPT until Owner Confirm is checked.");
      return;
    }
    if (!ready) {
      setStatus(`Cannot record Owner ACCEPT: ${(report?.missing_requirements ?? ["live recovery evidence is not ready"]).join("; ")}`);
      return;
    }
    setBusy(true);
    setStatus("");
    try {
      const next = await acceptLiveRecovery(notes, ownerConfirm);
      setReport(next);
      await refreshLiveMoneyProgressionAfterWrite();
      setOwnerConfirm(false);
      setStatus("Live recovery review recorded as ACCEPT.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Couldn't ACCEPT live recovery review.");
    } finally {
      setBusy(false);
    }
  }

  async function reset() {
    if (busy) return;
    setBusy(true);
    setStatus("");
    try {
      const next = await resetLiveRecovery("OWNER_RESET_FROM_SETTINGS");
      setReport(next);
      await refreshLiveMoneyProgressionAfterWrite();
      setOwnerConfirm(false);
      setOwnerConfirmReconcile(false);
      setOwnerConfirmArchive(false);
      setOwnerConfirmRefresh(false);
      setOwnerConfirmAdaptationReview(false);
      setOwnerConfirmAdaptationApply(false);
      setStatus("Live recovery review reset to OPEN.");
    } catch {
      setStatus("Couldn't reset live recovery review.");
    } finally {
      setBusy(false);
    }
  }

  async function reconcileAttempt() {
    if (busy) return;
    if (!selectedAttemptId) {
      setStatus("Cannot reconcile: no unresolved attempt is selected.");
      return;
    }
    if (!ownerConfirmReconcile) {
      setStatus("Cannot reconcile until Owner Reconcile is checked.");
      return;
    }
    setBusy(true);
    setStatus("");
    try {
      const audit = await reconcileUnresolvedOrderAttempt(selectedAttemptId, notes, ownerConfirmReconcile);
      setAttemptAudit(audit);
      const [next, packet, progression] = await Promise.all([
        fetchLiveRecoveryStatus(),
        fetchOrderAttemptRecoveryPacket(),
        fetchLiveMoneyProgressionPacket(),
      ]);
      if (next) setReport(next);
      if (packet) setRecoveryPacket(packet);
      if (progression) setLiveMoneyProgression(progression);
      setOwnerConfirmReconcile(false);
      setStatus("Unresolved real attempt recorded as RECOVERY_RECONCILED.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Couldn't reconcile unresolved real attempt.");
    } finally {
      setBusy(false);
    }
  }

  async function archiveTerminalReceipts(execute: boolean) {
    if (busy) return;
    if (execute && !ownerConfirmArchive) {
      setStatus("Cannot archive stale rows until Owner Archive is checked.");
      return;
    }
    if (execute && !canExecuteTerminalArchive) {
      setStatus("Cannot archive stale rows: no archive-ready terminal receipt rows are present.");
      return;
    }
    setBusy(true);
    setStatus("");
    try {
      const action = await runTerminalReceiptArchiveAction({
        execute,
        confirm_owner_archive: execute ? ownerConfirmArchive : false,
        age_threshold_hours: 24,
        notes,
      });
      setTerminalArchiveAction(action);
      const [next, terminalPacket, progression] = await Promise.all([
        fetchLiveRecoveryStatus(),
        fetchTerminalReceiptRecoveryPacket(),
        fetchLiveMoneyProgressionPacket(),
      ]);
      if (next) setReport(next);
      if (terminalPacket) setTerminalReceiptPacket(terminalPacket);
      if (progression) setLiveMoneyProgression(progression);
      if (execute) setOwnerConfirmArchive(false);
      setStatus(`Terminal receipt archive action: ${action.status}.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Couldn't run terminal receipt archive action.");
    } finally {
      setBusy(false);
    }
  }

  async function refreshTerminalRecoveryChain(execute: boolean) {
    if (busy) return;
    if (execute && !ownerConfirmRefresh) {
      setStatus("Cannot run refresh chain until Owner Refresh is checked.");
      return;
    }
    setBusy(true);
    setStatus("");
    try {
      const action = await runTerminalReceiptRecoveryRefreshAction({
        execute,
        confirm_owner_refresh: execute ? ownerConfirmRefresh : false,
        notes,
      });
      setTerminalRefreshAction(action);
      const [next, packet, terminalPacket, progression] = await Promise.all([
        fetchLiveRecoveryStatus(),
        fetchOrderAttemptRecoveryPacket(),
        fetchTerminalReceiptRecoveryPacket(),
        fetchLiveMoneyProgressionPacket(),
      ]);
      if (next) setReport(next);
      if (packet) setRecoveryPacket(packet);
      if (terminalPacket) setTerminalReceiptPacket(terminalPacket);
      if (progression) setLiveMoneyProgression(progression);
      if (execute) setOwnerConfirmRefresh(false);
      setStatus(`Terminal recovery refresh: ${action.status}.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Couldn't run terminal recovery refresh.");
    } finally {
      setBusy(false);
    }
  }

  async function recordAdaptationOwnerReview(decision: string) {
    if (busy) return;
    if (!ownerConfirmAdaptationReview) {
      setStatus("Cannot record adaptation review until Owner Adapt is checked.");
      return;
    }
    if (decision === "ACCEPT_PAPER_ONLY" && !adaptationOwnerEvidenceReady) {
      setStatus(`Cannot accept paper adaptation: ${(wasteAdaptationOwnerReview?.missing_requirements ?? ["adaptation evidence is not ready"]).join("; ")}`);
      return;
    }
    setBusy(true);
    setStatus("");
    try {
      const ownerReview = await recordWasteAdaptationOwnerReview(
        { decision, notes },
        ownerConfirmAdaptationReview,
        decision === "ACCEPT_PAPER_ONLY",
      );
      setWasteAdaptationOwnerReview(ownerReview);
      const [progression, preview] = await Promise.all([
        fetchLiveMoneyProgressionPacket(),
        fetchWasteAdaptationApplyPreview(),
      ]);
      if (progression) setLiveMoneyProgression(progression);
      if (preview) setWasteAdaptationApplyPreview(preview);
      setOwnerConfirmAdaptationReview(false);
      setStatus(`WASTE adaptation owner review recorded: ${ownerReview.owner_review_decision || ownerReview.owner_review_status}.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Couldn't record WASTE adaptation owner review.");
    } finally {
      setBusy(false);
    }
  }

  async function resetAdaptationOwnerReview() {
    if (busy) return;
    setBusy(true);
    setStatus("");
    try {
      const ownerReview = await resetWasteAdaptationOwnerReview("OWNER_RESET_FROM_SETTINGS");
      setWasteAdaptationOwnerReview(ownerReview);
      const progression = await fetchLiveMoneyProgressionPacket();
      if (progression) setLiveMoneyProgression(progression);
      setOwnerConfirmAdaptationReview(false);
      setStatus("WASTE adaptation owner review reset to OPEN.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Couldn't reset WASTE adaptation owner review.");
    } finally {
      setBusy(false);
    }
  }

  async function recordAdaptationPaperApply() {
    if (busy) return;
    if (!ownerConfirmAdaptationApply) {
      setStatus("Cannot record paper apply until Owner Paper Apply is checked.");
      return;
    }
    if (!adaptationPaperApplyReady) {
      setStatus(`Cannot record paper apply: ${(wasteAdaptationPaperApply?.missing_requirements ?? ["paper adaptation apply is not ready"]).join("; ")}`);
      return;
    }
    setBusy(true);
    setStatus("");
    try {
      const paperApply = await recordWasteAdaptationPaperApply(
        { notes },
        ownerConfirmAdaptationApply,
      );
      setWasteAdaptationPaperApply(paperApply);
      const [progression, ownerReview] = await Promise.all([
        fetchLiveMoneyProgressionPacket(),
        fetchWasteAdaptationOwnerReview(),
      ]);
      if (progression) setLiveMoneyProgression(progression);
      if (ownerReview) setWasteAdaptationOwnerReview(ownerReview);
      setOwnerConfirmAdaptationApply(false);
      setStatus(`WASTE adaptation paper apply: ${paperApply.status}.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Couldn't record WASTE adaptation paper apply.");
    } finally {
      setBusy(false);
    }
  }

  async function resetAdaptationPaperApply() {
    if (busy) return;
    setBusy(true);
    setStatus("");
    try {
      const paperApply = await resetWasteAdaptationPaperApply("OWNER_RESET_FROM_SETTINGS");
      setWasteAdaptationPaperApply(paperApply);
      const progression = await fetchLiveMoneyProgressionPacket();
      if (progression) setLiveMoneyProgression(progression);
      setOwnerConfirmAdaptationApply(false);
      setStatus("WASTE adaptation paper apply reset.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Couldn't reset WASTE adaptation paper apply.");
    } finally {
      setBusy(false);
    }
  }

  async function runBrokerTruthNow() {
    if (busy) return;
    setBusy(true);
    setStatus("");
    try {
      const brokerTruth = await runBrokerTruthMonitorOnce();
      setBrokerTruthMonitor(brokerTruth);
      const [next, brokerTruthPacket, packet, progression] = await Promise.all([
        fetchLiveRecoveryStatus(),
        fetchBrokerTruthRecoveryPacket(),
        fetchOrderAttemptRecoveryPacket(),
        fetchLiveMoneyProgressionPacket(),
      ]);
      if (next) setReport(next);
      if (brokerTruthPacket) setBrokerTruthRecoveryPacket(brokerTruthPacket);
      if (packet) setRecoveryPacket(packet);
      if (progression) setLiveMoneyProgression(progression);
      setStatus(`Broker truth check recorded: ${brokerTruth.monitor_status}.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Couldn't run broker truth check.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleBrokerTruthMonitor() {
    if (busy) return;
    setBusy(true);
    setStatus("");
    try {
      const next = brokerTruthMonitor?.running
        ? await stopBrokerTruthMonitor()
        : await startBrokerTruthMonitor(brokerTruthMonitor?.interval_seconds ?? 120);
      setBrokerTruthMonitor(next);
      const [brokerTruthPacket, progression] = await Promise.all([
        fetchBrokerTruthRecoveryPacket(),
        fetchLiveMoneyProgressionPacket(),
      ]);
      if (brokerTruthPacket) setBrokerTruthRecoveryPacket(brokerTruthPacket);
      if (progression) setLiveMoneyProgression(progression);
      setStatus(next.running ? "Broker truth monitor started." : "Broker truth monitor stopped.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Couldn't change broker truth monitor.");
    } finally {
      setBusy(false);
    }
  }

  async function runPaperSampleCollectorNow() {
    if (busy) return;
    setBusy(true);
    setStatus("");
    try {
      const scheduler = await runWastePaperSampleCollectorSchedulerOnce({
        run_market_diagnostic: true,
        run_real_candle_probe: true,
        run_deal_history_ingest: true,
        timeframe: wastePaperSampleCollectorScheduler?.config?.timeframe ?? "D1",
        bars: wastePaperSampleCollectorScheduler?.config?.bars ?? 180,
        max_pairs: wastePaperSampleCollectorScheduler?.config?.max_pairs ?? 80,
        scan_candidates: true,
        max_scan_candidates: 8,
      });
      setWastePaperSampleCollectorScheduler(scheduler);
      const [collector, progression] = await Promise.all([
        fetchWastePaperSampleCollector(),
        fetchLiveMoneyProgressionPacket(),
      ]);
      if (collector) setWastePaperSampleCollector(collector);
      if (progression) setLiveMoneyProgression(progression);
      setStatus(`Paper sample collector run: ${scheduler.latest_collector_status ?? scheduler.status}.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Couldn't run paper sample collector.");
    } finally {
      setBusy(false);
    }
  }

  async function togglePaperSampleCollectorScheduler() {
    if (busy) return;
    setBusy(true);
    setStatus("");
    try {
      const next = wastePaperSampleCollectorScheduler?.running
        ? await stopWastePaperSampleCollectorScheduler()
        : await startWastePaperSampleCollectorScheduler({
            interval_seconds: wastePaperSampleCollectorScheduler?.interval_seconds ?? 300,
            run_market_diagnostic: true,
            run_real_candle_probe: true,
            run_deal_history_ingest: true,
            timeframe: wastePaperSampleCollectorScheduler?.config?.timeframe ?? "D1",
            bars: wastePaperSampleCollectorScheduler?.config?.bars ?? 180,
            max_pairs: wastePaperSampleCollectorScheduler?.config?.max_pairs ?? 80,
            scan_candidates: true,
            max_scan_candidates: 8,
          });
      setWastePaperSampleCollectorScheduler(next);
      const collector = await fetchWastePaperSampleCollector();
      if (collector) setWastePaperSampleCollector(collector);
      setStatus(next.running ? "Paper sample collector scheduler started." : "Paper sample collector scheduler stopped.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Couldn't change paper sample collector scheduler.");
    } finally {
      setBusy(false);
    }
  }

  const clear = report?.recovery_clear_for_live ?? false;
  const ready = report?.evidence_ready_for_owner_accept ?? false;
  const requires = report?.requires_recovery_review ?? false;
  const liveRecoveryAttemptSummary = (report?.order_attempt_summary ?? {}) as Record<string, unknown>;
  const unresolvedCount = Number(
    liveRecoveryAttemptSummary.unresolved_real_attempt_count
      ?? recoveryPacket?.unresolved_real_attempt_count
      ?? attemptAudit?.unresolved_real_attempt_count
      ?? 0,
  );
  const canReconcileNow = Boolean(recoveryPacket?.can_reconcile_unresolved_attempts);
  const syntheticLikeCount = Number(
    liveRecoveryAttemptSummary.synthetic_test_like_unresolved_attempt_count
      ?? recoveryPacket?.synthetic_test_like_count
      ?? 0,
  );
  const brokerReviewCount = Number(
    liveRecoveryAttemptSummary.broker_review_required_unresolved_attempt_count
      ?? recoveryPacket?.broker_review_required_count
      ?? 0,
  );
  const unknownUnresolvedCount = Number(liveRecoveryAttemptSummary.unknown_unresolved_attempt_count ?? 0);
  const brokerBlockingAttemptCount = brokerReviewCount;
  const idempotencyPolicy = attemptAudit?.idempotency_policy;
  const duplicateSuppressedCount = Number(attemptAudit?.duplicate_suppressed_count ?? 0);
  const nearDuplicateSuppressedCount = Number(attemptAudit?.near_duplicate_suppressed_count ?? 0);
  const idempotencyWindowSeconds = Number(idempotencyPolicy?.near_duplicate_window_seconds ?? 600);
  const latestAttemptShapeKey = attemptAudit?.latest_attempt?.order_shape_key ?? "none";
  const terminalPendingReceiptCount = Number(terminalReceiptPacket?.pending_receipt_count ?? 0);
  const terminalArchivePreviewCount = Number(terminalReceiptPacket?.legacy_archive_preview?.pending_receipt_rows_archived ?? 0);
  const canExecuteTerminalArchive = terminalArchivePreviewCount > 0;
  const brokerTruthReport = brokerTruthMonitor?.latest_report ?? null;
  const brokerTruthReady = brokerTruthMonitor?.ready_for_live ?? false;
  const brokerTruthRunning = brokerTruthMonitor?.running ?? false;
  const brokerTruthStatus = brokerTruthMonitor?.monitor_status ?? brokerTruthReport?.monitor_status ?? "BROKER_TRUTH_UNKNOWN";
  const brokerTruthProtectionStatus = String(brokerTruthReport?.position_protection_status ?? "unavailable");
  const brokerTruthUnprotectedCount = Number(brokerTruthReport?.position_protection_unprotected_position_count ?? 0);
  const brokerTruthProtectionDetail = typeof brokerTruthReport?.position_protection_detail === "string"
    ? brokerTruthReport.position_protection_detail
    : "";
  const brokerTruthAutoHaltLatched = Boolean(brokerTruthReport?.auto_halt_latched_from_monitor);
  const brokerTruthReasonList = formatBrokerTruthReasonList(brokerTruthReport?.monitor_auto_halt_reason_ids);
  const brokerTruthBlockerCount = brokerTruthRecoveryPacket?.blockers?.length ?? 0;
  const liveMoneyBlockerCount = liveMoneyProgression?.blocker_count ?? liveMoneyProgression?.blockers?.length ?? 0;
  const liveMoneyIntent = liveMoneyProgression?.active_waste_intent ?? {};
  const liveMoneyIntentLabel = liveMoneyIntent.symbol || liveMoneyIntent.direction
    ? `${liveMoneyIntent.symbol ?? "NA"} ${liveMoneyIntent.direction ?? "NA"}`
    : "NO ACTIVE INTENT";
  const liveMoneyCacheLabel = formatCacheAge(liveMoneyProgression);
  const liveMoneyCacheStale = Boolean(liveMoneyProgression?.cache_stale);
  const wasteDirection = wasteDirectionReview?.direction_summary ?? {};
  const wasteEdge = wasteDirectionReview?.edge_gate_summary ?? {};
  const wasteProfitBox = wasteDirectionReview?.profit_box ?? {};
  const wasteDirectionLabel = wasteDirection.symbol || wasteDirection.direction
    ? `${wasteDirection.symbol ?? "NA"} ${wasteDirection.direction ?? "NA"}`
    : "NO DIRECTION";
  const wasteDirectionBlockerCount = wasteDirectionReview?.blocker_count ?? wasteDirectionReview?.blockers?.length ?? 0;
  const learningRecommendation = wasteDirectionLearning?.profile_recommendation ?? {};
  const learningGroup = (
    (learningRecommendation.recommended_group ?? learningRecommendation.dominant_observed_group ?? {}) as Record<string, unknown>
  );
  const learningGroupLabel = learningGroup.symbol || learningGroup.direction
    ? `${String(learningGroup.symbol ?? "NA")} ${String(learningGroup.timeframe ?? "NA")} ${String(learningGroup.profile ?? "NA")} ${String(learningGroup.direction ?? "NA")}`
    : "NO LEARNING GROUP";
  const outcomeReady = wasteDirectionOutcomeBinding?.outcome_ready_for_promotion ?? false;
  const outcomeBoundCount = wasteDirectionOutcomeBinding?.bound_outcome_count ?? 0;
  const outcomeBoundNeeded = wasteDirectionOutcomeBinding?.bound_outcomes_needed ?? 0;
  const paperSampleComplete = wastePaperSampleCollector?.sample_collection_complete ?? false;
  const paperSampleActionCount = wastePaperSampleCollector?.required_actions?.length ?? 0;
  const paperSampleMarketReady = wastePaperSampleCollector?.market_data_ready ?? false;
  const paperSampleLabel = wastePaperSampleCollector?.probe_symbol || wastePaperSampleCollector?.probe_direction
    ? `${wastePaperSampleCollector?.probe_symbol ?? "NA"} ${wastePaperSampleCollector?.probe_timeframe ?? "NA"} ${wastePaperSampleCollector?.probe_direction ?? "NA"}`
    : "NO PAPER SAMPLE";
  const paperSampleSchedulerRunning = wastePaperSampleCollectorScheduler?.running ?? false;
  const paperSampleSchedulerStatus = wastePaperSampleCollectorScheduler?.latest_collector_status ?? wastePaperSampleCollectorScheduler?.status ?? "unavailable";
  const paperSampleSchedulerCycles = wastePaperSampleCollectorScheduler?.cycles_run ?? 0;
  const promotionGroup = (
    (wasteAdaptationPromotionRule?.recommended_group ?? wasteAdaptationPromotionRule?.dominant_group ?? {}) as Record<string, unknown>
  );
  const promotionGroupLabel = promotionGroup.symbol || promotionGroup.direction
    ? `${String(promotionGroup.symbol ?? "NA")} ${String(promotionGroup.timeframe ?? "NA")} ${String(promotionGroup.profile ?? "NA")} ${String(promotionGroup.direction ?? "NA")}`
    : "NO PROMOTION GROUP";
  const promotionSamplesNeeded = wasteAdaptationPromotionRule?.confirmed_samples_needed ?? 0;
  const promotionReady = wasteAdaptationPromotionRule?.promotion_ready_for_owner_review ?? false;
  const adaptationProposalCount = wasteAdaptationPlan?.proposal_count ?? wasteAdaptationPlan?.proposals?.length ?? 0;
  const adaptationApplyPreviewBlockerCount = wasteAdaptationApplyPreview?.blocker_count ?? wasteAdaptationApplyPreview?.blockers?.length ?? 0;
  const adaptationSimulatedChangeCount = wasteAdaptationApplyPreview?.simulated_change_count ?? wasteAdaptationApplyPreview?.simulated_changes?.length ?? 0;
  const adaptationControls = wasteAdaptationApplyPreview?.current_controls ?? {};
  const adaptationOwnerReviewMissingCount = wasteAdaptationOwnerReview?.missing_requirements?.length ?? 0;
  const adaptationOwnerReviewCurrent = wasteAdaptationOwnerReview?.paper_only_review_current ?? false;
  const adaptationOwnerAcceptCurrent = wasteAdaptationOwnerReview?.paper_only_accept_current ?? false;
  const adaptationOwnerEvidenceReady = wasteAdaptationOwnerReview?.evidence_ready_for_owner_accept ?? false;
  const adaptationPaperApplyMissingCount = wasteAdaptationPaperApply?.missing_requirements?.length ?? 0;
  const adaptationPaperApplyReady = wasteAdaptationPaperApply?.paper_apply_ready ?? false;
  const adaptationPaperApplyCurrent = wasteAdaptationPaperApply?.paper_apply_current ?? false;
  const adaptationPaperApplyRecorded = wasteAdaptationPaperApply?.paper_apply_recorded ?? false;

  return (
    <GlassPanel
      title="Live Recovery"
      subtitle="Crash, disconnect, and restart review before more live orders"
      variant={clear ? "default" : "danger"}
    >
      <div className="sweep-status-row" style={{ marginBottom: 10 }}>
        <StatusChip label={report?.recovery_status ?? "OPEN"} variant={clear ? "success" : "danger"} size="sm" />
        <StatusChip label={requires ? "REVIEW REQUIRED" : "NO LIVE RECOVERY NEEDED"} variant={requires ? "warning" : "success"} size="sm" />
        <StatusChip label={ready ? "EVIDENCE READY" : "EVIDENCE NOT READY"} variant={ready ? "success" : "warning"} size="sm" />
        <StatusChip label={canReconcileNow ? "RECONCILE READY" : "RECONCILE BLOCKED"} variant={canReconcileNow ? "success" : "warning"} size="sm" />
        <StatusChip
          label={terminalReceiptPacket?.terminal_reconciliation_clean_for_live ? "RECEIPTS CLEAN" : "RECEIPTS BLOCKED"}
          variant={terminalReceiptPacket?.terminal_reconciliation_clean_for_live ? "success" : "warning"}
          size="sm"
        />
        <StatusChip
          label={canExecuteTerminalArchive ? "ARCHIVE READY" : "ARCHIVE IDLE"}
          variant={canExecuteTerminalArchive ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip
          label={`DUPLICATES ${duplicateSuppressedCount}`}
          variant={duplicateSuppressedCount > 0 ? "warning" : "success"}
          size="sm"
        />
        <StatusChip
          label={brokerTruthReady ? "BROKER TRUTH READY" : "BROKER TRUTH BLOCKED"}
          variant={brokerTruthReady ? "success" : "warning"}
          size="sm"
        />
        <StatusChip
          label={`TRUTH BLOCKERS ${brokerTruthBlockerCount}`}
          variant={brokerTruthBlockerCount === 0 ? "success" : "warning"}
          size="sm"
        />
        <StatusChip
          label={liveMoneyProgression?.full_progression_clear ? "LIVE MONEY CLEAR" : `LIVE MONEY BLOCKED ${liveMoneyBlockerCount}`}
          variant={liveMoneyProgression?.full_progression_clear ? "success" : "danger"}
          size="sm"
        />
        <StatusChip
          label={wasteDirectionReview?.direction_edge_confirmed ? "DIRECTION EDGE PASS" : `DIRECTION BLOCKED ${wasteDirectionBlockerCount}`}
          variant={wasteDirectionReview?.direction_edge_confirmed ? "success" : "warning"}
          size="sm"
        />
        <StatusChip
          label={wasteDirectionLearning?.learning_ready_for_adaptation ? "LEARNING READY" : "LEARNING COLLECTING"}
          variant={wasteDirectionLearning?.learning_ready_for_adaptation ? "success" : "muted"}
          size="sm"
        />
        <StatusChip
          label={outcomeReady ? "OUTCOMES BOUND" : `OUTCOMES NEED ${outcomeBoundNeeded}`}
          variant={outcomeReady ? "success" : "muted"}
          size="sm"
        />
        <StatusChip
          label={paperSampleComplete ? "PAPER SAMPLES READY" : `PAPER SAMPLE ACTIONS ${paperSampleActionCount}`}
          variant={paperSampleComplete ? "success" : paperSampleMarketReady ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip
          label={paperSampleSchedulerRunning ? "SAMPLE SCHEDULER ON" : "SAMPLE SCHEDULER OFF"}
          variant={paperSampleSchedulerRunning ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip
          label={promotionReady ? "PROMOTION READY" : `PROMOTION NEEDS ${promotionSamplesNeeded}`}
          variant={promotionReady ? "success" : "muted"}
          size="sm"
        />
        <StatusChip
          label={wasteAdaptationPlan?.adaptation_ready_for_owner_review ? "ADAPT PLAN READY" : "ADAPT PLAN DRY RUN"}
          variant={wasteAdaptationPlan?.adaptation_ready_for_owner_review ? "success" : "muted"}
          size="sm"
        />
        <StatusChip
          label={wasteAdaptationApplyPreview?.preview_ready_for_owner_review ? "ADAPT PREVIEW READY" : `ADAPT PREVIEW BLOCKED ${adaptationApplyPreviewBlockerCount}`}
          variant={wasteAdaptationApplyPreview?.preview_ready_for_owner_review ? "success" : "muted"}
          size="sm"
        />
        <StatusChip
          label={adaptationOwnerAcceptCurrent ? "ADAPT OWNER ACCEPT" : adaptationOwnerReviewCurrent ? "ADAPT OWNER REVIEWED" : "ADAPT OWNER OPEN"}
          variant={adaptationOwnerAcceptCurrent ? "success" : adaptationOwnerReviewCurrent ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip
          label={adaptationPaperApplyCurrent ? "PAPER ADAPT CURRENT" : adaptationPaperApplyReady ? "PAPER ADAPT READY" : "PAPER ADAPT BLOCKED"}
          variant={adaptationPaperApplyCurrent ? "success" : adaptationPaperApplyReady ? "warning" : "muted"}
          size="sm"
        />
      </div>

      <div className="control-grid">
        <ControlField
          label="Live Money Packet"
          value={liveMoneyProgression?.status ?? "unavailable"}
          danger={!liveMoneyProgression?.full_progression_clear}
        />
        <ControlField
          label="Packet Cache"
          value={liveMoneyCacheLabel}
          danger={liveMoneyCacheStale}
          mono
        />
        <ControlField label="Live Dispatch" value={String(liveMoneyProgression?.live_dispatch_clear ?? false)} danger={!liveMoneyProgression?.live_dispatch_clear} mono />
        <ControlField label="WASTE Pilot" value={String(liveMoneyProgression?.waste_pilot_clear ?? false)} danger={!liveMoneyProgression?.waste_pilot_clear} mono />
        <ControlField label="Verified Payout" value={String(liveMoneyProgression?.verified_payout_clear ?? false)} danger={!liveMoneyProgression?.verified_payout_clear} mono />
        <ControlField label="Progress Blockers" value={String(liveMoneyBlockerCount)} danger={liveMoneyBlockerCount > 0} mono />
        <ControlField label="WASTE Intent" value={liveMoneyIntentLabel} mono />
        <ControlField label="Direction Review" value={wasteDirectionReview?.status ?? "unavailable"} danger={!wasteDirectionReview?.direction_edge_confirmed} />
        <ControlField label="Chosen Side" value={wasteDirectionLabel} mono />
        <ControlField label="Opposite Score" value={String(wasteDirection.opposite_score ?? "NA")} mono />
        <ControlField label="Score Margin" value={String(wasteDirection.score_margin ?? "NA")} mono />
        <ControlField label="Edge Status" value={String(wasteEdge.status ?? "NA")} danger={wasteEdge.status !== "PASS"} mono />
        <ControlField label="Reward R" value={String(wasteProfitBox.reward_r ?? "NA")} danger={!wasteProfitBox.valid} mono />
        <ControlField label="Direction Samples" value={String(wasteDirectionLearning?.direction_rows ?? 0)} mono />
        <ControlField label="Confirmed Directions" value={String(wasteDirectionLearning?.confirmed_direction_count ?? 0)} danger={(wasteDirectionLearning?.confirmed_direction_count ?? 0) <= 0} mono />
        <ControlField label="Blocked Directions" value={String(wasteDirectionLearning?.blocked_direction_count ?? 0)} danger={(wasteDirectionLearning?.blocked_direction_count ?? 0) > 0} mono />
        <ControlField label="Learned Group" value={learningGroupLabel} mono />
        <ControlField label="Learning Ready" value={String(wasteDirectionLearning?.learning_ready_for_adaptation ?? false)} danger={!wasteDirectionLearning?.learning_ready_for_adaptation} mono />
        <ControlField label="Outcome Binding" value={wasteDirectionOutcomeBinding?.status ?? "unavailable"} danger={Boolean(wasteDirectionOutcomeBinding?.runtime_changed)} />
        <ControlField label="Outcomes Ready" value={String(outcomeReady)} danger={!outcomeReady} mono />
        <ControlField label="Bound Outcomes" value={String(outcomeBoundCount)} danger={outcomeBoundCount <= 0} mono />
        <ControlField label="Outcomes Needed" value={String(outcomeBoundNeeded)} danger={outcomeBoundNeeded > 0} mono />
        <ControlField label="Net Paper P/L" value={String(wasteDirectionOutcomeBinding?.net_paper_pnl ?? "NA")} danger={(wasteDirectionOutcomeBinding?.net_paper_pnl ?? 0) <= 0} mono />
        <ControlField label="Outcome Money Moved" value={String(wasteDirectionOutcomeBinding?.money_moved ?? false)} danger={Boolean(wasteDirectionOutcomeBinding?.money_moved)} mono />
        <ControlField label="Paper Sample Collector" value={wastePaperSampleCollector?.status ?? "unavailable"} danger={Boolean(wastePaperSampleCollector?.runtime_changed)} />
        <ControlField label="Sample Intent" value={paperSampleLabel} mono />
        <ControlField label="Market Ready" value={String(paperSampleMarketReady)} danger={!paperSampleMarketReady} mono />
        <ControlField label="Probe Edge" value={String(wastePaperSampleCollector?.probe_edge_status ?? "NA")} danger={wastePaperSampleCollector?.probe_edge_status !== "PASS"} mono />
        <ControlField label="Sample Actions" value={String(paperSampleActionCount)} danger={paperSampleActionCount > 0} mono />
        <ControlField label="Collector Money Moved" value={String(wastePaperSampleCollector?.money_moved ?? false)} danger={Boolean(wastePaperSampleCollector?.money_moved)} mono />
        <ControlField label="Sample Scheduler" value={paperSampleSchedulerStatus} danger={Boolean(wastePaperSampleCollectorScheduler?.last_error)} />
        <ControlField label="Scheduler Running" value={String(paperSampleSchedulerRunning)} mono />
        <ControlField label="Scheduler Cycles" value={String(paperSampleSchedulerCycles)} mono />
        <ControlField label="Scheduler Interval" value={`${String(wastePaperSampleCollectorScheduler?.interval_seconds ?? 300)}s`} mono />
        <ControlField label="Scheduler Last Run" value={String(wastePaperSampleCollectorScheduler?.last_run_iso ?? "never")} mono />
        <ControlField label="Scheduler Broker Touch" value={String(wastePaperSampleCollectorScheduler?.broker_execution_touched ?? false)} danger={Boolean(wastePaperSampleCollectorScheduler?.broker_execution_touched)} mono />
        <ControlField label="Scheduler Money Moved" value={String(wastePaperSampleCollectorScheduler?.money_moved ?? false)} danger={Boolean(wastePaperSampleCollectorScheduler?.money_moved)} mono />
        <ControlField label="Promotion Rule" value={wasteAdaptationPromotionRule?.status ?? "unavailable"} danger={Boolean(wasteAdaptationPromotionRule?.runtime_changed)} />
        <ControlField label="Promotion Ready" value={String(promotionReady)} danger={!promotionReady} mono />
        <ControlField label="Min Confirmed" value={String(wasteAdaptationPromotionRule?.min_confirmed_for_adaptation ?? "NA")} mono />
        <ControlField label="Confirmed Needed" value={String(promotionSamplesNeeded)} danger={promotionSamplesNeeded > 0} mono />
        <ControlField label="Promotion Group" value={promotionGroupLabel} mono />
        <ControlField label="Promotion Money Moved" value={String(wasteAdaptationPromotionRule?.money_moved ?? false)} danger={Boolean(wasteAdaptationPromotionRule?.money_moved)} mono />
        <ControlField label="Promotion Runtime Changed" value={String(wasteAdaptationPromotionRule?.runtime_changed ?? false)} danger={Boolean(wasteAdaptationPromotionRule?.runtime_changed)} mono />
        <ControlField label="Promotion Enables Live" value={String(wasteAdaptationPromotionRule?.would_enable_live_trading ?? false)} danger={Boolean(wasteAdaptationPromotionRule?.would_enable_live_trading)} mono />
        <ControlField label="Adaptation Plan" value={wasteAdaptationPlan?.status ?? "unavailable"} danger={!wasteAdaptationPlan?.dry_run} />
        <ControlField label="Adapt Proposals" value={String(adaptationProposalCount)} mono />
        <ControlField label="Adapt Ready" value={String(wasteAdaptationPlan?.adaptation_ready_for_owner_review ?? false)} danger={!wasteAdaptationPlan?.adaptation_ready_for_owner_review} mono />
        <ControlField label="Runtime Changed" value={String(wasteAdaptationPlan?.runtime_changed ?? false)} danger={Boolean(wasteAdaptationPlan?.runtime_changed)} mono />
        <ControlField label="Apply Preview" value={wasteAdaptationApplyPreview?.status ?? "unavailable"} danger={!wasteAdaptationApplyPreview?.dry_run} />
        <ControlField label="Preview Changes" value={String(adaptationSimulatedChangeCount)} mono />
        <ControlField label="Preview Blockers" value={String(adaptationApplyPreviewBlockerCount)} danger={adaptationApplyPreviewBlockerCount > 0} mono />
        <ControlField label="Apply Allowed" value={String(wasteAdaptationApplyPreview?.apply_allowed_now ?? false)} danger={Boolean(wasteAdaptationApplyPreview?.apply_allowed_now)} mono />
        <ControlField label="Would Lower Edge" value={String(wasteAdaptationApplyPreview?.would_lower_edge_threshold ?? false)} danger={Boolean(wasteAdaptationApplyPreview?.would_lower_edge_threshold)} mono />
        <ControlField label="Would Enable Live" value={String(wasteAdaptationApplyPreview?.would_enable_live_trading ?? false)} danger={Boolean(wasteAdaptationApplyPreview?.would_enable_live_trading)} mono />
        <ControlField label="Would Change Runtime" value={String(wasteAdaptationApplyPreview?.would_apply_runtime_change ?? false)} danger={Boolean(wasteAdaptationApplyPreview?.would_apply_runtime_change)} mono />
        <ControlField label="Current Edge Gate" value={String(adaptationControls["edge_threshold"] ?? "NA")} mono />
        <ControlField label="Owner Adapt Review" value={wasteAdaptationOwnerReview?.owner_review_status ?? "unavailable"} danger={Boolean(wasteAdaptationOwnerReview?.runtime_changed)} />
        <ControlField label="Adapt Decision" value={wasteAdaptationOwnerReview?.owner_review_decision || "OPEN"} mono />
        <ControlField label="Review Current" value={String(adaptationOwnerReviewCurrent)} danger={!adaptationOwnerReviewCurrent} mono />
        <ControlField label="Accept Current" value={String(adaptationOwnerAcceptCurrent)} danger={Boolean(adaptationOwnerAcceptCurrent && !adaptationOwnerEvidenceReady)} mono />
        <ControlField label="Accept Evidence Ready" value={String(adaptationOwnerEvidenceReady)} danger={!adaptationOwnerEvidenceReady} mono />
        <ControlField label="Review Missing" value={String(adaptationOwnerReviewMissingCount)} danger={adaptationOwnerReviewMissingCount > 0} mono />
        <ControlField label="Review Money Moved" value={String(wasteAdaptationOwnerReview?.money_moved ?? false)} danger={Boolean(wasteAdaptationOwnerReview?.money_moved)} mono />
        <ControlField label="Paper Apply" value={wasteAdaptationPaperApply?.status ?? "unavailable"} danger={Boolean(wasteAdaptationPaperApply?.runtime_changed)} />
        <ControlField label="Apply Ready" value={String(adaptationPaperApplyReady)} danger={!adaptationPaperApplyReady} mono />
        <ControlField label="Apply Current" value={String(adaptationPaperApplyCurrent)} danger={Boolean(adaptationPaperApplyCurrent && !adaptationPaperApplyRecorded)} mono />
        <ControlField label="Apply Recorded" value={String(adaptationPaperApplyRecorded)} mono />
        <ControlField label="Apply Missing" value={String(adaptationPaperApplyMissingCount)} danger={adaptationPaperApplyMissingCount > 0} mono />
        <ControlField label="Apply Runtime Changed" value={String(wasteAdaptationPaperApply?.runtime_changed ?? false)} danger={Boolean(wasteAdaptationPaperApply?.runtime_changed)} mono />
        <ControlField label="Apply Money Moved" value={String(wasteAdaptationPaperApply?.money_moved ?? false)} danger={Boolean(wasteAdaptationPaperApply?.money_moved)} mono />
        <ControlField label="Broker Truth" value={String(report?.broker_truth_summary?.overall_status ?? "unavailable")} danger={!clear} />
        <ControlField label="Truth Monitor" value={brokerTruthStatus} danger={!brokerTruthReady} />
        <ControlField label="Truth Running" value={String(brokerTruthRunning)} mono />
        <ControlField label="Truth Live Ready" value={String(brokerTruthReady)} danger={!brokerTruthReady} mono />
        <ControlField
          label="Truth Auto-Halt"
          value={String(brokerTruthAutoHaltLatched)}
          danger={brokerTruthAutoHaltLatched}
          description={brokerTruthAutoHaltLatched ? "The continuous broker-truth worker latched paper-force from a live mismatch." : undefined}
          mono
        />
        <ControlField
          label="Truth Halt Reasons"
          value={brokerTruthReasonList}
          danger={brokerTruthReasonList !== "NONE"}
          description={brokerTruthReasonList !== "NONE" ? "Mismatch checks that forced the monitor fail-closed path." : undefined}
          mono
        />
        <ControlField label="Truth Blockers" value={String(brokerTruthBlockerCount)} danger={brokerTruthBlockerCount > 0} mono />
        <ControlField label="MT5 Connected" value={String(report?.broker_truth_summary?.mt5_connected ?? false)} danger={!report?.broker_truth_summary?.mt5_connected} />
        <ControlField label="MT5 Open Positions" value={String(report?.broker_truth_summary?.mt5_open_position_count ?? 0)} mono />
        <ControlField
          label="Position Protection"
          value={brokerTruthProtectionStatus}
          danger={brokerTruthProtectionStatus === "UNPROTECTED_POSITIONS"}
          description={brokerTruthProtectionDetail || undefined}
        />
        <ControlField
          label="Unprotected Positions"
          value={String(brokerTruthUnprotectedCount)}
          danger={brokerTruthUnprotectedCount > 0}
          description={brokerTruthUnprotectedCount > 0 ? "Broker-visible open positions without stop-loss protection." : undefined}
          mono
        />
        <ControlField label="Unmatched Positions" value={String(report?.broker_truth_summary?.terminal_unmatched_open_position_count ?? 0)} danger={Number(report?.broker_truth_summary?.terminal_unmatched_open_position_count ?? 0) > 0} />
        <ControlField
          label="Unresolved Attempt Rows"
          value={String(unresolvedCount)}
          danger={brokerBlockingAttemptCount > 0}
          description={
            unresolvedCount > 0 && brokerBlockingAttemptCount === 0
              ? "Classified separately; not blocking live recovery by itself."
              : undefined
          }
          mono
        />
        <ControlField
          label="Test-like Attempts"
          value={String(syntheticLikeCount)}
          description={syntheticLikeCount > 0 ? "Synthetic/test-like audit rows; not a broker-review blocker." : undefined}
          mono
        />
        <ControlField label="Broker Review Attempts" value={String(brokerReviewCount)} danger={brokerReviewCount > 0} mono />
        <ControlField label="Unknown Attempt Rows" value={String(unknownUnresolvedCount)} danger={unknownUnresolvedCount > 0} mono />
        <ControlField label="Duplicate Suppressed" value={String(duplicateSuppressedCount)} danger={duplicateSuppressedCount > 0} mono />
        <ControlField label="Shape Duplicates" value={String(nearDuplicateSuppressedCount)} danger={nearDuplicateSuppressedCount > 0} mono />
        <ControlField label="Idempotency Window" value={`${idempotencyWindowSeconds}s`} mono />
        <ControlField label="Exact Retry Key" value={idempotencyPolicy?.exact_retry_key ?? "decision_ref|order_id"} mono />
        <ControlField label="Near Duplicate Key" value={idempotencyPolicy?.near_duplicate_key ?? "automation order shape"} mono />
        <ControlField label="Latest Shape Key" value={String(latestAttemptShapeKey)} mono />
        <ControlField label="Pending Receipts" value={String(terminalPendingReceiptCount)} danger={terminalPendingReceiptCount > 0} mono />
        <ControlField
          label="Archive Preview"
          value={String(terminalArchivePreviewCount)}
          description={terminalArchivePreviewCount > 0 ? "Dry-run only; owner execution required to archive." : undefined}
          mono
        />
        <ControlField label="Live Pilot Trades" value={String(report?.live_pilot_summary?.live_trade_count ?? 0)} mono />
        <ControlField label="Fingerprint" value={String(report?.current_fingerprint ?? "pending")} mono />
      </div>

      {report && report.missing_requirements.length > 0 && (
        <div className="control-field-desc" style={{ color: "var(--danger)", marginTop: 8 }}>
          Missing: {report.missing_requirements.join("; ")}
        </div>
      )}

      {liveMoneyProgression && (
        <div className="control-field-desc" style={{ marginTop: 8, color: liveMoneyProgression.full_progression_clear ? "var(--success)" : "var(--warning)" }}>
          Live-money packet: {liveMoneyProgression.status}; cache {liveMoneyCacheLabel}. {liveMoneyProgression.next_action}
        </div>
      )}

      {wasteDirectionReview && (
        <div className="control-field-desc" style={{ marginTop: 8, color: wasteDirectionReview.direction_edge_confirmed ? "var(--success)" : "var(--warning)" }}>
          WASTE direction: {wasteDirectionReview.status}. {wasteDirectionReview.next_action}
        </div>
      )}

      {wasteDirectionLearning && (
        <div className="control-field-desc" style={{ marginTop: 8, color: wasteDirectionLearning.learning_ready_for_adaptation ? "var(--success)" : "var(--text-secondary)" }}>
          Direction learning: {wasteDirectionLearning.status}. {wasteDirectionLearning.next_action}
        </div>
      )}

      {wasteDirectionOutcomeBinding && (
        <div className="control-field-desc" style={{ marginTop: 8, color: outcomeReady ? "var(--success)" : "var(--text-secondary)" }}>
          Direction outcomes: {wasteDirectionOutcomeBinding.status}. {wasteDirectionOutcomeBinding.next_action}
        </div>
      )}

      {wastePaperSampleCollector && (
        <div className="control-field-desc" style={{ marginTop: 8, color: paperSampleComplete ? "var(--success)" : paperSampleMarketReady ? "var(--warning)" : "var(--text-secondary)" }}>
          Paper sample collection: {wastePaperSampleCollector.status}. {wastePaperSampleCollector.next_action}
        </div>
      )}

      {wastePaperSampleCollectorScheduler && (
        <div className="control-field-desc" style={{ marginTop: 8, color: paperSampleSchedulerRunning ? "var(--warning)" : "var(--text-secondary)" }}>
          Paper sample scheduler: {wastePaperSampleCollectorScheduler.status}. {wastePaperSampleCollectorScheduler.next_action}
        </div>
      )}

      {wasteAdaptationPromotionRule && (
        <div className="control-field-desc" style={{ marginTop: 8, color: promotionReady ? "var(--success)" : "var(--text-secondary)" }}>
          Adaptation promotion: {wasteAdaptationPromotionRule.status}. {wasteAdaptationPromotionRule.next_action}
        </div>
      )}

      {wasteAdaptationPlan && (
        <div className="control-field-desc" style={{ marginTop: 8, color: wasteAdaptationPlan.adaptation_ready_for_owner_review ? "var(--success)" : "var(--text-secondary)" }}>
          WASTE adaptation: {wasteAdaptationPlan.status}. {wasteAdaptationPlan.next_action}
        </div>
      )}

      {wasteAdaptationApplyPreview && (
        <div className="control-field-desc" style={{ marginTop: 8, color: wasteAdaptationApplyPreview.preview_ready_for_owner_review ? "var(--success)" : "var(--text-secondary)" }}>
          Apply preview: {wasteAdaptationApplyPreview.status}. {wasteAdaptationApplyPreview.next_action}
        </div>
      )}

      {wasteAdaptationOwnerReview && (
        <div className="control-field-desc" style={{ marginTop: 8, color: adaptationOwnerAcceptCurrent ? "var(--success)" : adaptationOwnerReviewCurrent ? "var(--warning)" : "var(--text-secondary)" }}>
          Owner adaptation review: {wasteAdaptationOwnerReview.owner_review_status}. {wasteAdaptationOwnerReview.next_action}
        </div>
      )}

      {wasteAdaptationPaperApply && (
        <div className="control-field-desc" style={{ marginTop: 8, color: adaptationPaperApplyCurrent ? "var(--success)" : adaptationPaperApplyReady ? "var(--warning)" : "var(--text-secondary)" }}>
          Paper adaptation apply: {wasteAdaptationPaperApply.status}. {wasteAdaptationPaperApply.next_action}
        </div>
      )}

      {recoveryPacket && (
        <div className="control-field-desc" style={{ marginTop: 8, color: recoveryPacket.can_reconcile_unresolved_attempts ? "var(--success)" : "var(--warning)" }}>
          Recovery packet: {recoveryPacket.status}. {recoveryPacket.next_action}
        </div>
      )}

      {idempotencyPolicy && (
        <div className="control-field-desc" style={{ marginTop: 8, color: duplicateSuppressedCount > 0 ? "var(--warning)" : "var(--text-secondary)" }}>
          Idempotency: exact retries use {idempotencyPolicy.exact_retry_key}; automation near-duplicates use {idempotencyPolicy.near_duplicate_key} for {idempotencyWindowSeconds}s. Manual and compound/pyramid adds are excluded from the near-duplicate block.
        </div>
      )}

      {terminalReceiptPacket && (
        <div className="control-field-desc" style={{ marginTop: 8, color: terminalReceiptPacket.terminal_reconciliation_clean_for_live ? "var(--success)" : "var(--warning)" }}>
          Terminal receipt packet: {terminalReceiptPacket.status}. {terminalReceiptPacket.next_action}
        </div>
      )}

      {terminalArchiveAction && (
        <div className="control-field-desc" style={{ marginTop: 8, color: terminalArchiveAction.journal_rewritten ? "var(--success)" : "var(--warning)" }}>
          Archive action: {terminalArchiveAction.status}. {terminalArchiveAction.next_action}
        </div>
      )}

      {terminalRefreshAction && (
        <div className="control-field-desc" style={{ marginTop: 8, color: terminalRefreshAction.status.includes("FAILED") ? "var(--danger)" : "var(--warning)" }}>
          Recovery refresh: {terminalRefreshAction.status}. {terminalRefreshAction.next_action}
        </div>
      )}

      {brokerTruthRecoveryPacket && (
        <div className="control-field-desc" style={{ marginTop: 8, color: brokerTruthRecoveryPacket.broker_truth_clear_for_live_recovery ? "var(--success)" : "var(--warning)" }}>
          Broker truth packet: {brokerTruthRecoveryPacket.status}. {brokerTruthRecoveryPacket.next_action}
        </div>
      )}

      <label className="control-field" style={{ marginTop: 12 }}>
        <span className="field-label">Owner recovery notes</span>
        <textarea className="mobile-api-input broker-reality-textarea" value={notes} onChange={(event) => setNotes(event.target.value)} />
      </label>

      {unresolvedAttempts.length > 0 && (
        <div className="control-grid" style={{ marginTop: 12 }}>
          <label className="control-field">
            <span className="field-label">Unresolved attempt</span>
            <select
              className="mobile-api-input"
              value={selectedAttemptId}
              onChange={(event) => setSelectedAttemptId(event.target.value)}
            >
              {unresolvedAttempts.map((attempt) => (
                <option key={attempt.attempt_id ?? ""} value={attempt.attempt_id ?? ""}>
                  {formatAttemptOption(attempt)}
                </option>
              ))}
            </select>
          </label>
          <ControlField
            label="Selected Attempt"
            value={selectedAttemptId || "NONE"}
            danger={Boolean(selectedAttemptId)}
            mono
          />
        </div>
      )}

      {selectedAttempt && (
        <div className="control-grid" style={{ marginTop: 12 }}>
          <ControlField label="Attempt Status" value={selectedAttempt.status ?? "UNKNOWN"} danger={!selectedAttempt.result_finalized} mono />
          <ControlField label="Result Status" value={selectedAttempt.result_status ?? "UNKNOWN"} danger={Boolean(selectedAttempt.bridge_touch_unknown)} mono />
          <ControlField label="Initiator" value={formatUnknownValue(selectedAttemptInitiator?.kind ?? selectedAttempt.source ?? "UNKNOWN")} mono />
          <ControlField label="Runtime Lane" value={formatUnknownValue(selectedAttemptRuntimeLane?.effective_lane ?? selectedAttempt.mode ?? "UNKNOWN")} mono />
          <ControlField label="Final Gate" value={formatUnknownValue(selectedAttemptDispatchPath?.terminal_stage ?? "UNKNOWN")} mono />
          <ControlField label="Bridge Touch" value={formatUnknownValue(selectedAttemptDispatchPath?.bridge_touch_state ?? (selectedAttempt.bridge_touch_unknown ? "TOUCH_UNKNOWN" : "NOT_ATTACHED"))} danger={Boolean(selectedAttempt.bridge_touch_unknown)} mono />
          <ControlField label="Audit Snapshot" value={formatUnknownValue(selectedAttemptAudit?.status ?? selectedAttempt.status ?? "UNKNOWN")} mono />
          <ControlField label="Provenance Hash" value={formatUnknownValue(selectedAttemptProvenance?.provenance_hash ?? "NOT_ATTACHED")} mono />
          <ControlField label="Config Hash" value={formatUnknownValue(selectedAttemptProvenance?.config_hash ?? "NOT_ATTACHED")} mono />
        </div>
      )}

      <div className="sweep-action-row" style={{ marginTop: 12 }}>
        <button className="broker-risk-apply-button" type="button" disabled={busy} onClick={() => void refresh()}>Refresh</button>
        <button className="mobile-api-button ghost" type="button" disabled={busy} onClick={() => void runPaperSampleCollectorNow()}>Run Sample Collector</button>
        <button className="mobile-api-button ghost" type="button" disabled={busy} onClick={() => void togglePaperSampleCollectorScheduler()}>
          {paperSampleSchedulerRunning ? "Stop Sample Scheduler" : "Start Sample Scheduler"}
        </button>
        <button className="mobile-api-button ghost" type="button" disabled={busy} onClick={() => void runBrokerTruthNow()}>Run Broker Truth</button>
        <button className="mobile-api-button ghost" type="button" disabled={busy} onClick={() => void toggleBrokerTruthMonitor()}>
          {brokerTruthRunning ? "Stop Truth Monitor" : "Start Truth Monitor"}
        </button>
        <button className="mobile-api-button ghost" type="button" disabled={busy} onClick={() => void archiveTerminalReceipts(false)}>Preview Archive</button>
        <button className="mobile-api-button ghost" type="button" disabled={busy} onClick={() => void refreshTerminalRecoveryChain(false)}>Plan Refresh</button>
        <label className="sweep-confirm-check">
          <input type="checkbox" checked={ownerConfirmAdaptationReview} onChange={(event) => setOwnerConfirmAdaptationReview(event.target.checked)} />
          <span>Owner Adapt</span>
        </label>
        <button
          className="mobile-api-button ghost"
          type="button"
          disabled={busy}
          onClick={() => void recordAdaptationOwnerReview("HOLD_PAPER_ONLY")}
        >
          Hold Adapt
        </button>
        <button
          className="mobile-api-button ghost"
          type="button"
          disabled={busy}
          onClick={() => void recordAdaptationOwnerReview("REQUEST_MORE_EVIDENCE")}
        >
          More Evidence
        </button>
        <button
          className="sweep-action-button danger"
          type="button"
          disabled={busy}
          onClick={() => void recordAdaptationOwnerReview("ACCEPT_PAPER_ONLY")}
        >
          Accept Paper Adapt
        </button>
        <button
          className="mobile-api-button ghost"
          type="button"
          disabled={busy}
          onClick={() => void resetAdaptationOwnerReview()}
        >
          Reset Adapt Review
        </button>
        <label className="sweep-confirm-check">
          <input type="checkbox" checked={ownerConfirmAdaptationApply} onChange={(event) => setOwnerConfirmAdaptationApply(event.target.checked)} />
          <span>Owner Paper Apply</span>
        </label>
        <button
          className="sweep-action-button danger"
          type="button"
          disabled={busy}
          onClick={() => void recordAdaptationPaperApply()}
        >
          Record Paper Apply
        </button>
        <button
          className="mobile-api-button ghost"
          type="button"
          disabled={busy}
          onClick={() => void resetAdaptationPaperApply()}
        >
          Reset Paper Apply
        </button>
        <label className="sweep-confirm-check">
          <input type="checkbox" checked={ownerConfirmArchive} onChange={(event) => setOwnerConfirmArchive(event.target.checked)} />
          <span>Owner Archive</span>
        </label>
        <button
          className="sweep-action-button danger"
          type="button"
          disabled={busy}
          onClick={() => void archiveTerminalReceipts(true)}
        >
          Archive Stale Rows
        </button>
        <label className="sweep-confirm-check">
          <input type="checkbox" checked={ownerConfirmRefresh} onChange={(event) => setOwnerConfirmRefresh(event.target.checked)} />
          <span>Owner Refresh</span>
        </label>
        <button
          className="sweep-action-button danger"
          type="button"
          disabled={busy}
          onClick={() => void refreshTerminalRecoveryChain(true)}
        >
          Run Refresh Chain
        </button>
        <label className="sweep-confirm-check">
          <input type="checkbox" checked={ownerConfirm} onChange={(event) => setOwnerConfirm(event.target.checked)} />
          <span>Owner Confirm</span>
        </label>
        <button className="sweep-action-button danger" type="button" disabled={busy} onClick={() => void accept()}>Owner ACCEPT</button>
        <label className="sweep-confirm-check">
          <input type="checkbox" checked={ownerConfirmReconcile} onChange={(event) => setOwnerConfirmReconcile(event.target.checked)} />
          <span>Owner Reconcile</span>
        </label>
        <button
          className="sweep-action-button danger"
          type="button"
          disabled={busy}
          onClick={() => void reconcileAttempt()}
        >
          Reconcile Attempt
        </button>
        <button className="mobile-api-button ghost" type="button" disabled={busy} onClick={() => void reset()}>Reset</button>
      </div>

      {status && <div className="control-field-desc" style={{ marginTop: 8, color: status.includes("Couldn't") || status.includes("Cannot") || status.includes("API") ? "var(--danger)" : "var(--success)" }}>{status}</div>}
      <div className="control-field-desc" style={{ marginTop: 8 }}>
        {report?.claim_boundary ?? "Live recovery review does not place orders or move money; it gates more live orders after interruption evidence."}
      </div>
    </GlassPanel>
  );
}

function unresolvedAttemptsFromRecovery(report: LiveRecoveryReport | null): OrderAttemptAuditAttempt[] {
  const attempts = report?.order_attempt_summary?.unresolved_real_attempts;
  if (!Array.isArray(attempts)) return [];
  return attempts.filter((attempt): attempt is OrderAttemptAuditAttempt => Boolean(attempt) && typeof attempt === "object");
}

function formatAttemptOption(attempt: OrderAttemptAuditAttempt): string {
  const id = attempt.attempt_id ?? "unknown-attempt";
  const symbol = attempt.symbol ?? "NA";
  const direction = attempt.direction ?? "NA";
  const source = attempt.source ?? "unknown";
  const classification = "classification_status" in attempt && attempt.classification_status
    ? ` | ${String(attempt.classification_status)}`
    : "";
  const bridgeUnknown = attempt.bridge_touch_unknown ? " | BRIDGE_TOUCH_UNKNOWN" : "";
  return `${id} | ${symbol} ${direction} | ${source}${classification}${bridgeUnknown}`;
}

function formatCacheAge(packet?: { cache_status?: string; cache_age_seconds?: number | null } | null): string {
  if (!packet) return "unavailable";
  const status = packet.cache_status ?? "direct";
  if (packet.cache_age_seconds == null) return status;
  return `${status} ${formatDuration(packet.cache_age_seconds)} old`;
}

function formatDuration(seconds: number): string {
  const safeSeconds = Math.max(0, Math.floor(seconds));
  if (safeSeconds < 60) return `${safeSeconds}s`;
  const minutes = Math.floor(safeSeconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const extraMinutes = minutes % 60;
  return extraMinutes ? `${hours}h ${extraMinutes}m` : `${hours}h`;
}

const RISK_FIELDS = [
  { key: "max_concurrent_trades", label: "Max Concurrent Trades", hint: "How many trades can be open at once. Toggle Unlimited to remove the cap." },
  { key: "max_loss_cap_usd", label: "Max Loss Cap (USD)", hint: "Floating loss that blocks new trades. Unlimited = no cap." },
  { key: "max_total_exposure_lots", label: "Max Total Exposure (lots)", hint: "Total open lots across the whole book." },
  { key: "max_drawdown_pct", label: "Max Drawdown (%)", hint: "Drawdown from the equity peak that blocks new trades." },
] as const;

type RiskKey = (typeof RISK_FIELDS)[number]["key"];

// RiskControlPanel (legacy) deleted: it was dead code behind the tautology
// `if (Date.now() >= 0) return <RiskControlPanelModern />` - ~90 unreachable
// lines that also violated the Rules of Hooks. RiskControlPanelModern is the
// only risk-control surface.
function RiskControlPanelModern() {
  const [rc, setRc] = useState<RiskControlState | null>(null);
  const [draft, setDraft] = useState<Record<RiskKey, { value: string; unlimited: boolean }>>(() => emptyRiskDraft());
  const [preview, setPreview] = useState<RiskControlAssessment | null>(null);
  const [confirmText, setConfirmText] = useState("");
  const [journalReason, setJournalReason] = useState("");
  const [busy, setBusy] = useState("");
  const [status, setStatus] = useState("");

  function load(state: RiskControlState) {
    setRc(state);
    const next = emptyRiskDraft();
    for (const field of RISK_FIELDS) {
      const value = state[field.key];
      next[field.key] = { value: value == null ? "" : String(value), unlimited: value == null };
    }
    setDraft(next);
  }

  useEffect(() => {
    void fetchRiskControl().then((state) => { if (state) load(state); });
  }, []);

  function buildPatch(): RiskControlPatch | null {
    const patch: RiskControlPatch = {};
    for (const field of RISK_FIELDS) {
      const cell = draft[field.key];
      if (cell.unlimited || cell.value.trim() === "") {
        patch[field.key] = null;
        continue;
      }
      const numeric = Number(cell.value);
      if (!Number.isFinite(numeric) || numeric < 0) {
        setStatus(`${field.label} must be a non-negative number, or Unlimited.`);
        return null;
      }
      patch[field.key] = numeric;
    }
    return patch;
  }

  function editCell(key: RiskKey, cell: { value: string; unlimited: boolean }) {
    setDraft({ ...draft, [key]: cell });
    setPreview(null);
    setConfirmText("");
    setJournalReason("");
    setStatus("");
  }

  async function previewChanges() {
    const patch = buildPatch();
    if (!patch) return;
    setBusy("preview");
    setStatus("");
    try {
      const next = await previewRiskControl({ ...patch, journal_reason: journalReason || undefined });
      setPreview(next);
      setConfirmText("");
      setStatus(next.changes.length ? "Impact preview ready. Review before applying." : "No risk-cap fields changed.");
    } catch {
      setStatus("Couldn't preview - is the API reachable? Check the address above.");
    } finally {
      setBusy("");
    }
  }

  async function applyChanges() {
    const patch = buildPatch();
    if (!patch) return;
    setBusy("save");
    setStatus("");
    try {
      const activePreview = await previewRiskControl({ ...patch, journal_reason: journalReason || undefined });
      setPreview(activePreview);
      if (activePreview.requires_journal_reason && !activePreview.journal?.satisfied) {
        const blocker = activePreview.journal?.blockers?.join("; ") || "Anti-impulse journal reason is required.";
        setStatus(blocker);
        return;
      }
      if (activePreview.requires_cooldown_clear) {
        setStatus(activePreview.cooldown?.detail || "Risk loosening cooldown is active.");
        return;
      }
      if (activePreview.requires_confirmation && normalizeConfirm(confirmText) !== normalizeConfirm(activePreview.confirm_phrase)) {
        setStatus(`Type exactly "${activePreview.confirm_phrase}" to apply this risk loosening.`);
        return;
      }
      load(await updateRiskControl({
        ...patch,
        confirm: confirmText || undefined,
        journal_reason: journalReason || undefined,
      }));
      setPreview(null);
      setConfirmText("");
      setJournalReason("");
      setStatus("Saved - applies to the next trade immediately.");
    } catch (error) {
      const detail = riskActionDetail(error);
      if (detail) {
        if (detail.assessment) setPreview(detail.assessment);
        setStatus(riskActionMessage(detail));
      } else {
        setStatus("Couldn't save - is the API reachable? Check the address above.");
      }
    } finally {
      setBusy("");
    }
  }

  async function reset() {
    setBusy("reset");
    setStatus("");
    try {
      const activePreview = await previewResetRiskControl({ journal_reason: journalReason || undefined });
      setPreview(activePreview);
      if (activePreview.requires_journal_reason && !activePreview.journal?.satisfied) {
        const blocker = activePreview.journal?.blockers?.join("; ") || "Anti-impulse journal reason is required.";
        setStatus(blocker);
        return;
      }
      if (activePreview.requires_cooldown_clear) {
        setStatus(activePreview.cooldown?.detail || "Risk loosening cooldown is active.");
        return;
      }
      if (activePreview.requires_confirmation && normalizeConfirm(confirmText) !== normalizeConfirm(activePreview.confirm_phrase)) {
        setStatus(`Type exactly "${activePreview.confirm_phrase}" to reset these risk caps.`);
        return;
      }
      load(await resetRiskControl({
        confirm: confirmText || undefined,
        journal_reason: journalReason || undefined,
      }));
      setPreview(null);
      setConfirmText("");
      setJournalReason("");
      setStatus(
        activePreview.changes.some((change) => change.posture !== "unchanged")
          ? "Reset to defaults."
          : "Already at defaults.",
      );
    } catch (error) {
      const detail = riskActionDetail(error);
      if (detail) {
        if (detail.assessment) setPreview(detail.assessment);
        setStatus(riskActionMessage(detail, { resetVerb: true }));
      } else {
        setStatus("Couldn't reset.");
      }
    } finally {
      setBusy("");
    }
  }

  return (
    <GlassPanel title="Risk Control - You Drive" subtitle="Preview before/after cap changes, then apply them through the backend gate">
      <div style={{ display: "grid", gap: 12 }}>
        {RISK_FIELDS.map((field) => {
          const cell = draft[field.key];
          return (
            <div key={field.key} className="control-field">
              <div className="control-field-header">
                <span className="field-label">{field.label}</span>
                <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.8125rem" }}>
                  <input
                    type="checkbox"
                    checked={cell.unlimited}
                    onChange={(event) => editCell(field.key, { ...cell, unlimited: event.target.checked })}
                  />
                  Unlimited
                </label>
              </div>
              <input
                className="mobile-api-input"
                type="number"
                min={0}
                disabled={cell.unlimited}
                value={cell.unlimited ? "" : cell.value}
                placeholder={cell.unlimited ? "Unlimited (no cap)" : "0"}
                onChange={(event) => editCell(field.key, { ...cell, value: event.target.value })}
              />
              <div className="control-field-desc">{field.hint}</div>
            </div>
          );
        })}

        {preview && (
          <div className={`risk-impact-preview ${preview.requires_confirmation ? "requires-confirm" : ""}`}>
            <div className="risk-impact-header">
              <span>Risk change impact</span>
              <StatusChip
                label={preview.requires_confirmation ? "CONFIRM REQUIRED" : preview.loosening_changes.length ? "LOOSENS CAPS" : "NO CONFIRM"}
                variant={preview.requires_confirmation ? "danger" : preview.loosening_changes.length ? "warning" : "success"}
                size="sm"
              />
            </div>
            <div className="risk-impact-list">
              {preview.changes.map((change) => (
                <div key={change.key} className={`risk-impact-row ${change.posture}`}>
                  <span>{riskFieldLabel(change.key)}</span>
                  <strong>
                    {formatRiskChangeValue(change.effective_before ?? change.before)} to{" "}
                    {formatRiskChangeValue(change.effective_after ?? change.after)}
                  </strong>
                  <em>{change.posture}</em>
                </div>
              ))}
            </div>
            {preview.requires_confirmation && (
              <label className="risk-confirm-box">
                <span className="field-label">Confirmation phrase</span>
                <input
                  className="mobile-api-input"
                  value={confirmText}
                  onChange={(event) => setConfirmText(event.target.value)}
                  placeholder={preview.confirm_phrase}
                  spellCheck={false}
                />
              </label>
            )}
            {preview.requires_journal_reason && (
              <label className="risk-confirm-box">
                <span className="field-label">Anti-impulse journal</span>
                <textarea
                  className="mobile-api-input"
                  value={journalReason}
                  onChange={(event) => setJournalReason(event.target.value)}
                  placeholder={preview.journal?.prompt || preview.journal_prompt || "Reason for loosening risk caps"}
                  rows={3}
                  spellCheck
                />
                <div className="control-field-desc">
                  Minimum {preview.journal?.minimum_reason_length ?? 20} characters.
                  {preview.journal?.blockers?.length ? ` ${preview.journal.blockers.join("; ")}` : ""}
                </div>
              </label>
            )}
            <div className="control-field-desc">{preview.claim_boundary}</div>
          </div>
        )}

        <div className="mobile-api-row">
          <button className="mobile-api-button ghost" type="button" disabled={Boolean(busy)} onClick={() => void previewChanges()}>
            {busy === "preview" ? "Previewing..." : "Preview impact"}
          </button>
          <button className="mobile-api-button" type="button" disabled={Boolean(busy)} onClick={() => void applyChanges()}>
            {busy === "save" ? "Applying..." : "Apply risk caps"}
          </button>
          <button className="mobile-api-button ghost" type="button" disabled={Boolean(busy)} onClick={() => void reset()}>
            {busy === "reset" ? "Resetting..." : "Reset to defaults"}
          </button>
        </div>

        {status && <div className="control-field-desc" style={{ color: riskStatusColor(status) }}>{status}</div>}
        {rc && (
          <>
            <div className="control-field-desc">
              Effective dispatch - concurrent: <strong>{formatRiskChangeValue(rc.effective_dispatch_caps?.max_open_position_count ?? null)}</strong>, per symbol:{" "}
              <strong>{formatRiskChangeValue(rc.effective_dispatch_caps?.max_positions_per_symbol ?? null)}</strong>, exposure:{" "}
              <strong>{formatRiskChangeValue(rc.effective_dispatch_caps?.max_total_exposure_lots ?? null)}</strong> lots, per-trade risk:{" "}
              <strong>{rc.effective_dispatch_caps?.max_risk_per_trade_pct == null ? "Unlimited" : `${rc.effective_dispatch_caps.max_risk_per_trade_pct}%`}</strong>.
            </div>
            <div className="control-field-desc">
              Owner override layer: <strong>{rc.explicit_override_keys?.length ? rc.explicit_override_keys.join(", ") : "none (Operator dials active)"}</strong>.{" "}
              Persistence: <strong>{rc.override_persistence?.status ?? "syncing"}</strong>.
            </div>
          </>
        )}
      </div>
    </GlassPanel>
  );
}

function emptyRiskDraft(): Record<RiskKey, { value: string; unlimited: boolean }> {
  return {
    max_concurrent_trades: { value: "", unlimited: false },
    max_total_exposure_lots: { value: "", unlimited: false },
    max_loss_cap_usd: { value: "", unlimited: false },
    max_drawdown_pct: { value: "", unlimited: false },
  };
}

function riskFieldLabel(key: RiskKey): string {
  return RISK_FIELDS.find((field) => field.key === key)?.label ?? key;
}

function formatRiskChangeValue(value: number | null): string {
  return value == null ? "Unlimited" : String(value);
}

function normalizeConfirm(value: string): string {
  return value.trim().toUpperCase().replace(/\s+/g, " ");
}

function riskStatusColor(status: string): string {
  return status.startsWith("Couldn't")
    || status.startsWith("Type exactly")
    || status.includes("must be")
    || status.toLowerCase().includes("cooldown")
    ? "var(--danger)"
    : "var(--success)";
}

function riskActionDetail(error: unknown): {
  status: string;
  need_confirmation?: string;
  assessment?: RiskControlAssessment;
  journal?: NonNullable<RiskControlAssessment["journal"]>;
  cooldown?: NonNullable<RiskControlAssessment["cooldown"]>;
} | null {
  const payload = typeof error === "object" && error !== null && "payload" in error
    ? (error as { payload?: unknown }).payload
    : null;
  const detail = typeof payload === "object" && payload !== null && "detail" in payload
    ? (payload as { detail?: unknown }).detail
    : null;
  if (!detail || typeof detail !== "object") return null;
  const record = detail as Record<string, unknown>;
  if (typeof record.status !== "string") return null;
  return {
    status: record.status,
    need_confirmation: typeof record.need_confirmation === "string" ? record.need_confirmation : undefined,
    assessment: record.assessment && typeof record.assessment === "object"
      ? (record.assessment as RiskControlAssessment)
      : undefined,
    journal: record.journal && typeof record.journal === "object"
      ? (record.journal as NonNullable<RiskControlAssessment["journal"]>)
      : undefined,
    cooldown: record.cooldown && typeof record.cooldown === "object"
      ? (record.cooldown as NonNullable<RiskControlAssessment["cooldown"]>)
      : undefined,
  };
}

function riskActionMessage(
  detail: NonNullable<ReturnType<typeof riskActionDetail>>,
  options: { resetVerb?: boolean } = {},
): string {
  if (detail.status === "CONFIRM_REQUIRED" && detail.need_confirmation) {
    return options.resetVerb
      ? `Type exactly "${detail.need_confirmation}" to reset these risk caps.`
      : `Type exactly "${detail.need_confirmation}" to apply this risk loosening.`;
  }
  if (detail.status === "JOURNAL_REQUIRED") {
    const blockers = detail.journal?.blockers?.join("; ");
    return blockers || "Anti-impulse journal reason is required.";
  }
  if (detail.status === "COOLDOWN_ACTIVE") {
    return detail.cooldown?.detail
      || detail.assessment?.cooldown?.detail
      || "Risk loosening cooldown is active.";
  }
  return options.resetVerb ? "Couldn't reset." : "Couldn't save.";
}

function LegalGate({ label, met, detail }: { label: string; met: boolean; detail: string }) {
  return (
    <div className="legal-gate-item">
      <div className="legal-gate-header">
        <span className="check-icon" style={{ color: met ? "var(--success)" : "var(--danger)" }}>{met ? "✓" : "✗"}</span>
        <span className="field-label">{label}</span>
        <StatusChip label={met ? "MET" : "NOT MET"} variant={met ? "success" : "danger"} size="sm" />
      </div>
      <div className="legal-gate-detail">{detail}</div>
    </div>
  );
}

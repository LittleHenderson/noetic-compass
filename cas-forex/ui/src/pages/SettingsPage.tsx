/* ── CAS Forex — Settings & Owner Control ── */

import { useEffect, useState } from "react";
import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import { NotificationSubscriptionPanel } from "../components/NotificationSubscriptionPanel";
import { WebhookSubscriptionPanel } from "../components/WebhookSubscriptionPanel";
import { Mt4BridgePanel } from "../components/Mt4BridgePanel";
import "../components/SelectorChips.css";
import {
  updateOwnerControl,
  fetchLiveEnable,
  type LiveEnableState,
  fetchBrokerControl,
  type BrokerControlState,
  fetchMt4Control,
  type MT4ControlState,
} from "../data/api";
import type { DashboardState } from "../types/evidence";
import { ControlField } from "../components/settings/ControlField";
import { ProfessionalClaimsPanel } from "../components/settings/ProfessionalClaimsPanel";
import { SpecContextPanel } from "../components/settings/SpecContextPanel";
import { BypassLaunchGatePanel, PublicLaunchGatePanel } from "../components/settings/LaunchGatePanels";
import { UILayoutContractPanel } from "../components/settings/UILayoutContractPanel";
import { ControlAuditTrailPanel, CriticalNotificationAuditPanel } from "../components/settings/AuditPanels";
import { SecurityPosturePanel } from "../components/settings/SecurityPosturePanel";
import { AiHedgeManagementHandoffPanel, AiHedgeSupervisionPanel } from "../components/settings/AiHedgePanels";
import { ProfessionalReadinessPanel } from "../components/settings/ProfessionalReadinessPanel";
import { BrokerSymbolDiagnosticsPanel, EconomicCalendarPanel, MobileApiPanel, RuntimeTopologyPanel } from "../components/settings/OpsPanels";
import { AuthorizePanel, GoLivePanel } from "../components/settings/GoLivePanels";
import { BrokerRealityPanel } from "../components/settings/BrokerRealityPanel";
import { LivePilotPanel } from "../components/settings/LivePilotPanel";
import { LiveRecoveryPanel } from "../components/settings/LiveRecoveryPanel";
import { RiskControlPanelModern } from "../components/settings/RiskControlPanel";
import { EmergencyControlsPanel, LegalGate, LegalReviewReadinessPanel, OperationalReadinessPanel } from "../components/settings/LegalGovernancePanels";
import { BrokerFundingHandoffPanel } from "../components/settings/BrokerFundingHandoffPanel";
import { AiControlAuthorityPanel, EdgeThresholdPanel } from "../components/settings/AiControlAuthorityPanel";

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



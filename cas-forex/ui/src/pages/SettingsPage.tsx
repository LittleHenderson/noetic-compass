/* ── CAS Forex — Settings & Owner Control ── */

import { useEffect, useState } from "react";
import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import { EdgeThresholdControl } from "../components/EdgeThresholdControl";
import { NotificationSubscriptionPanel } from "../components/NotificationSubscriptionPanel";
import { WebhookSubscriptionPanel } from "../components/WebhookSubscriptionPanel";
import { Mt4BridgePanel } from "../components/Mt4BridgePanel";
import "../components/SelectorChips.css";
import {
  getApiBase,
  resetApiBase,
  setApiBase,
  updateOwnerControl,
  fetchRiskControl,
  updateRiskControl,
  resetRiskControl,
  type RiskControlState,
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
} from "../data/api";
import type { AccountReconciliationReport, DashboardState } from "../types/evidence";

interface SettingsPageProps {
  state: DashboardState;
}

const CONTROL_MODES = [
  { value: "DENY", label: "Deny All" },
  { value: "NOTIFY_ONLY", label: "Notify Only" },
  { value: "LIMITED_PAPER", label: "Limited Paper" },
  { value: "PAPER_AUTO", label: "Paper Auto" },
  { value: "AI_FULL_AUTO_PAPER", label: "AI Full Auto (Paper)" },
  { value: "AI_FULL_AUTO_LIVE_REQUESTED", label: "AI Full Auto Live (Requested)" },
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
  async function saveOwnerMode(mode: (typeof CONTROL_MODES)[number]["value"]) {
    setOwnerControlBusy(mode);
    setOwnerControlStatus("");
    try {
      const next = await updateOwnerControl({ mode });
      setOwnerControlState(next);
      setOwnerControlStatus(
        mode === "AI_FULL_AUTO_LIVE_REQUESTED"
          ? "Owner live-autonomy request saved. Live orders remain owner-commanded and still re-check edge, broker credentials, and risk at action time."
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

      {/* ── Min edge to trade — owner integrity dial (local only) ── */}
      <EdgeThresholdPanel />

      {/* ── Go Live — owner switches (turn the live-trading gate flags ON) ── */}
      <GoLivePanel />

      {/* ── Owner risk control — set any cap, or remove it ── */}
      <RiskControlPanel />

      {/* ── MT4 EA mailbox — the stable real-order route ── */}
      <Mt4BridgePanel />

      <BrokerFundingHandoffPanel />

      {/* ── Notification Subscriptions (Web Push) ── */}
      <NotificationSubscriptionPanel />

      {/* ── Webhook Subscriptions ── */}
      <WebhookSubscriptionPanel />

      {/* ── Owner Control Surface ── */}
      <GlassPanel title="Owner Control Policy" subtitle="Risk caps, AI autonomy, concurrent trades">
        <div className="owner-control-surface">
          {/* Mode Selection */}
          <div className="control-section">
            <h4 className="control-section-title">Autonomy Mode</h4>
            <div className="selector-chips">
              {CONTROL_MODES.map((m) => {
                const isActive = oc?.mode === m.value;
                const isLive = m.value === "AI_FULL_AUTO_LIVE_REQUESTED";
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
                    {isLive && <span style={{ color: "var(--danger)", marginLeft: 4, fontSize: "0.6rem" }}>BLOCKED</span>}
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
              <div style={{ marginTop: 8, padding: "6px 10px", background: "var(--warning-dim)", borderRadius: "var(--radius-sm)", fontSize: "0.72rem", color: "var(--warning)" }}>
                AI_FULL_AUTO_LIVE_REQUESTED: owner requested full live autonomy; live trading, broker ACCEPT, and payment movement stay under owner switches, credentials, and action-time checks.
              </div>
            )}
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
        <div style={{ marginTop: 12, padding: "8px 12px", background: "var(--warning-dim)", borderRadius: "var(--radius-sm)", fontSize: "0.72rem", color: "var(--text-secondary)" }}>
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
          <ControlField label="Model" value={ai?.model_name ?? "llama3.1:70b-instruct"} mono />
          <ControlField label="API Key Present" value={ai?.has_api_key ? "YES" : "NO"} danger={!ai?.has_api_key && (ai?.backend ?? "").startsWith("frontier_")} />
          <ControlField label="Control Plane" value={ai?.control_plane ?? "CAS_HARNESS_PCBA"} mono />
          <ControlField label="PCBA Guard" value={pcbaGuardEnabled ? "ENABLED" : "DISABLED"} danger={!pcbaGuardEnabled} />
        </div>
        <div style={{ marginTop: 12, padding: "8px 12px", background: "var(--panel-dim)", borderRadius: "var(--radius-sm)", fontSize: "0.72rem", color: "var(--text-secondary)" }}>
          {ai?.authority_boundary ?? "Research/advisory only. Models cannot trade or move money; runtime_gates controls all live-money actions."}
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
          <ControlField label="Min Add Confidence" value="55%" mono description="Minimum confidence to add to position" />
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
        <div style={{ marginTop: 12, padding: "8px 12px", background: "var(--danger-dim)", borderRadius: "var(--radius-sm)", fontSize: "0.72rem", color: "var(--danger)" }}>
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

const HUGOSWAY_CLIENT_PORTAL_URL = "https://app.hugosway.com";

function BrokerFundingHandoffPanel() {
  const [reconciliation, setReconciliation] = useState<AccountReconciliationReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");

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
  const statusVariant = syncStatus.includes("MISMATCH") ? "warning" : "info";

  return (
    <GlassPanel title="Broker Funding Handoff" subtitle="Fund at the broker portal; CAS verifies the broker snapshot after funding">
      <div className="control-grid">
        <div className="control-field">
          <div className="control-field-header">
            <span className="field-label">Funding Route</span>
            <StatusChip label="BROKER PORTAL" variant="info" size="sm" />
          </div>
          <div className="control-field-desc">Hugo'sWay client portal: KYC, deposits, withdrawals, and account funding.</div>
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
            <span className="field-label">Blockers</span>
            <StatusChip label={`${blockerCount}`} variant={blockerCount ? "warning" : "success"} size="sm" />
          </div>
          <div className="control-field-desc">
            {blockerCount ? reconciliation?.blockers.slice(0, 2).join("; ") : "No broker-sync blockers loaded in this panel."}
          </div>
        </div>
      </div>
      <div className="mobile-api-row" style={{ marginTop: 12 }}>
        <a className="mobile-api-button" href={HUGOSWAY_CLIENT_PORTAL_URL} target="_blank" rel="noreferrer">
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

function ControlField({ label, value, mono, danger, description }: { label: string; value: string; mono?: boolean; danger?: boolean; description?: string }) {
  return (
    <div className="control-field">
      <div className="control-field-header">
        <span className="field-label">{label}</span>
        <span className={`field-value ${mono ? "mono" : ""}`} style={{ color: danger ? "var(--danger)" : undefined, fontWeight: 600 }}>{value}</span>
      </div>
      {description && <div className="control-field-desc">{description}</div>}
    </div>
  );
}

function AuthorityModelStrip({ model }: { model?: OwnerAuthorityModel }) {
  const controls = model?.authority_controls?.join(" + ") || "owner switches + Owner ACCEPT buttons";
  const checks = model?.action_time_requirements?.slice(0, 3).join("; ")
    || "broker/provider, edge, and risk checks";
  const metricsVeto = model?.metrics_and_ai_can_veto_owner_authority ?? false;
  return (
    <div className="control-grid" style={{ marginBottom: 14 }}>
      <ControlField
        label="Authority"
        value={model?.authority || "OWNER"}
        description={`${controls} are the capability authority path.`}
      />
      <ControlField
        label="Metrics / AI"
        value={metricsVeto ? "CAN VETO" : "ADVISORY"}
        danger={metricsVeto}
        description={metricsVeto ? "Unexpected veto state from API." : "Paper proof, AI scores, win rate, and profit pace can advise but not override owner authority."}
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
        only raise the bar — below it, the dispatch chokepoint stands down (no trade, capital safe).
      </div>
    </>
  );
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

// Grouped layout for the live-enable toggles. Keys map to the backend flags.
const GO_LIVE_GROUPS: { title: string; keys: LiveEnableKey[] }[] = [
  { title: "Account acknowledgments", keys: ["personal_account_ack", "no_pooled_capital_ack"] },
  { title: "Live broker mode", keys: ["live_mode", "prefer_mt5"] },
  { title: "Owner enable", keys: ["owner_enable_live_trading", "live_trading_licensed"] },
];

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
      setLe(await updateLiveEnable({ [key]: next }));
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
                        <span style={{ marginLeft: 6, fontSize: "0.62rem", color: "var(--text-secondary)" }}>
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
          fontSize: "0.72rem",
          color: "var(--text-secondary)",
        }}
      >
        <strong>What these switches do:</strong> they satisfy the owner live-trading authority gate -
        they do
        <strong> not</strong> place any order by themselves. A real order also needs a
        <strong> connected broker/feed path</strong>, a <strong>fresh edge authorization</strong> when the
        loop requires one, and the broker bridge re-checks owner authorization at order time.
        Flipping every switch here gives the owner authority path; it does not let an AI or
        metric place real money without the dispatch path and order-time checks firing.
      </div>
    </GlassPanel>
  );
}

function AuthorizePanel() {
  const [auth, setAuth] = useState<AuthorizationState | null>(null);
  const [busyKey, setBusyKey] = useState<string>("");
  const [status, setStatus] = useState<string>("");
  const [provider, setProvider] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [destId, setDestId] = useState("");

  function loadProviderDraft(s: AuthorizationState) {
    setProvider(s.provider.payment_provider ?? "");
    setDestId(s.provider.payout_destination_id ?? "");
    // api key is never returned — keep the field blank (it stays set on the server).
  }

  useEffect(() => {
    void fetchAuthorization().then((s) => { if (s) { setAuth(s); loadProviderDraft(s); } });
  }, []);

  async function apply(patch: AuthorizationPatch, key: string) {
    setBusyKey(key);
    setStatus("");
    try {
      const s = await updateAuthorization(patch);
      setAuth(s);
      loadProviderDraft(s);
      emitLiveMoneyProgressionRefresh();
      setStatus("Saved.");
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

  const allGreen = auth?.all_real_money_authorized ?? false;
  const authorityModel = auth?.owner_authority_model;

  return (
    <GlassPanel
      title="Path to Authorize Everything — Owner Switches"
      subtitle="Flip every live-money capability ON from here — no .env, no restart"
      variant={allGreen ? "default" : "warning"}
    >
      <div style={{ marginBottom: 12, fontSize: "0.78rem", color: "var(--text-secondary)" }}>
        {auth?.summary ?? "Loading owner-controlled capabilities…"}
      </div>

      <AuthorityModelStrip model={authorityModel} />

      <div style={{ display: "grid", gap: 4 }}>
        {(auth?.capabilities ?? []).map((cap) => (
          <div key={cap.capability} style={{ padding: "10px 0", borderBottom: "1px solid var(--border-subtle)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
              <span style={{ fontWeight: 700, fontSize: "0.84rem" }}>{cap.title}</span>
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
                    <div className="go-live-row-label">{t.label}{t.overridden && <span style={{ marginLeft: 6, fontSize: "0.62rem", color: "var(--text-secondary)" }}>(set in-app)</span>}</div>
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
      <div style={{ display: "grid", gap: 10, marginTop: 6 }}>
        <div className="control-field">
          <span className="field-label">Provider name</span>
          <input className="mobile-api-input" value={provider} placeholder="e.g. wise, stripe"
            onChange={(e) => { setProvider(e.target.value); setStatus(""); }} />
        </div>
        <div className="control-field">
          <span className="field-label">Provider API key{auth?.provider.payment_api_key_set ? " — set ✓" : ""}</span>
          <input className="mobile-api-input" type="password" value={apiKey}
            placeholder={auth?.provider.payment_api_key_set ? "•••••• (leave blank to keep)" : "your provider API key"}
            autoComplete="off"
            onChange={(e) => { setApiKey(e.target.value); setStatus(""); }} />
          <div className="control-field-desc">Stored only in the running app; never shown back here.</div>
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
              const patch: AuthorizationPatch = { payment_provider: provider, payout_destination_id: destId };
              if (apiKey.trim()) patch.payment_api_key = apiKey.trim();
              void apply(patch, "__provider__").then(() => setApiKey(""));
            }}>
            Save provider
          </button>
          <button className="mobile-api-button ghost" type="button" disabled={busyKey === "__reset__"} onClick={() => void reset()}>
            Reset all to defaults
          </button>
        </div>
      </div>

      {status && <div className="control-field-desc" style={{ color: status.startsWith("Couldn't") ? "var(--danger)" : "var(--success)" }}>{status}</div>}

      <div style={{ marginTop: 14, padding: "8px 12px", background: "var(--panel-dim)", borderRadius: "var(--radius-sm)", fontSize: "0.72rem", color: "var(--text-secondary)" }}>
        <strong>What these switches do:</strong> they satisfy the owner-authorization gate for each capability — they do
        <strong> not</strong> move money or place orders by themselves. Money movement also needs the payment provider + API
        key above and a running process; the provider/bridge re-checks at action time. The owner controls these switches;
        AI agents and metrics do not get final authority over live capability.
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
      broker_id: draft.broker_id || review?.broker_id || "hugosway",
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
          <input className="mobile-api-input" value={draft.broker_id ?? "hugosway"} onChange={(event) => setDraft({ ...draft, broker_id: event.target.value })} />
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

const LIVE_PILOT_NUMBER_FIELDS = [
  ["max_trade_lots", "Max trade lots"],
  ["max_open_live_lots", "Max open live lots"],
  ["max_live_trade_count", "Max live trades"],
  ["max_daily_loss_usd", "Max daily loss USD"],
  ["max_total_loss_usd", "Max total pilot loss USD"],
  ["max_pilot_days", "Max pilot days"],
] as const;

const LIVE_PILOT_CHECKS = [
  ["owner_understands_real_money_risk", "Owner understands real-money risk"],
  ["owner_confirms_small_amounts_only", "Owner confirms small amounts only"],
  ["owner_confirms_no_scaling_without_review", "No scaling without owner review"],
  ["owner_confirms_emergency_stop_ready", "Emergency stop is ready"],
] as const;

function LivePilotPanel({ initialPolicy }: { initialPolicy?: LivePilotPolicy }) {
  const [policy, setPolicy] = useState<LivePilotPolicy | null>(initialPolicy ?? null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [checks, setChecks] = useState<Record<string, boolean>>({});
  const [symbolsText, setSymbolsText] = useState("");
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
      setStatus(confirm ? "Small live pilot recorded as ACCEPT." : "Small live pilot draft saved as OPEN.");
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
      setStatus("Small live pilot reset to OPEN.");
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
      title="Small Live Pilot"
      subtitle="Owner-confirmed micro live-money envelope before scaling"
      variant={ready ? "default" : "danger"}
    >
      <div className="sweep-status-row" style={{ marginBottom: 10 }}>
        <StatusChip label={policy?.owner_pilot_status ?? "OPEN"} variant={accepted ? "success" : "danger"} size="sm" />
        <StatusChip label={ready ? "PILOT READY" : "PILOT NOT READY"} variant={ready ? "success" : "warning"} size="sm" />
        <StatusChip label={`${policy?.pilot_capacity_remaining ?? 0} LIVE TESTS LEFT`} variant={ready ? "success" : "warning"} size="sm" />
      </div>

      <div className="control-grid">
        <label className="control-field">
          <span className="field-label">Allowed symbols</span>
          <textarea className="mobile-api-input broker-reality-textarea" value={symbolsText} onChange={(event) => setSymbolsText(event.target.value)} />
          <div className="control-field-desc">One symbol per line. First live orders cannot use symbols outside this list.</div>
        </label>
        <label className="control-field">
          <span className="field-label">Owner notes</span>
          <textarea className="mobile-api-input broker-reality-textarea" value={draft.notes ?? ""} onChange={(event) => setDraft({ ...draft, notes: event.target.value })} />
          <div className="control-field-desc">Notes stay in the pilot audit record.</div>
        </label>
        {LIVE_PILOT_NUMBER_FIELDS.map(([key, label]) => (
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
        {policy?.claim_boundary ?? "The small live pilot caps first live trades and does not authorize live trading by itself."}
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
  const terminalPendingReceiptCount = Number(terminalReceiptPacket?.pending_receipt_count ?? 0);
  const terminalArchivePreviewCount = Number(terminalReceiptPacket?.legacy_archive_preview?.pending_receipt_rows_archived ?? 0);
  const canExecuteTerminalArchive = terminalArchivePreviewCount > 0;
  const brokerTruthReport = brokerTruthMonitor?.latest_report ?? null;
  const brokerTruthReady = brokerTruthMonitor?.ready_for_live ?? false;
  const brokerTruthRunning = brokerTruthMonitor?.running ?? false;
  const brokerTruthStatus = brokerTruthMonitor?.monitor_status ?? brokerTruthReport?.monitor_status ?? "BROKER_TRUTH_UNKNOWN";
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
        <ControlField label="Truth Blockers" value={String(brokerTruthBlockerCount)} danger={brokerTruthBlockerCount > 0} mono />
        <ControlField label="MT5 Connected" value={String(report?.broker_truth_summary?.mt5_connected ?? false)} danger={!report?.broker_truth_summary?.mt5_connected} />
        <ControlField label="MT5 Open Positions" value={String(report?.broker_truth_summary?.mt5_open_position_count ?? 0)} mono />
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
  return `${id} | ${symbol} ${direction} | ${source}${classification}`;
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

function RiskControlPanel() {
  const [rc, setRc] = useState<RiskControlState | null>(null);
  const [draft, setDraft] = useState<Record<string, { value: string; unlimited: boolean }>>({});
  const [status, setStatus] = useState<string>("");

  function load(s: RiskControlState) {
    setRc(s);
    const d: Record<string, { value: string; unlimited: boolean }> = {};
    for (const f of RISK_FIELDS) {
      const v = s[f.key];
      d[f.key] = { value: v == null ? "" : String(v), unlimited: v == null };
    }
    setDraft(d);
  }

  useEffect(() => {
    void fetchRiskControl().then((s) => { if (s) load(s); });
  }, []);

  async function save() {
    const patch: Partial<Record<RiskKey, number | null>> = {};
    for (const f of RISK_FIELDS) {
      const cell = draft[f.key] ?? { value: "", unlimited: false };
      patch[f.key] = cell.unlimited || cell.value.trim() === "" ? null : Number(cell.value);
    }
    try {
      load(await updateRiskControl(patch));
      setStatus("Saved — applies to the next trade immediately.");
    } catch {
      setStatus("Couldn't save — is the API reachable? Check the address above.");
    }
  }

  async function reset() {
    try {
      load(await resetRiskControl());
      setStatus("Reset to defaults.");
    } catch {
      setStatus("Couldn't reset.");
    }
  }

  const fmt = (v: number | null) => (v == null ? "∞" : String(v));

  return (
    <GlassPanel title="Risk Control — You Drive" subtitle="Set any concurrent-trade count and any loss cap, or remove the cap entirely">
      <div style={{ display: "grid", gap: 12 }}>
        {RISK_FIELDS.map((f) => {
          const cell = draft[f.key] ?? { value: "", unlimited: false };
          return (
            <div key={f.key} className="control-field">
              <div className="control-field-header">
                <span className="field-label">{f.label}</span>
                <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.72rem" }}>
                  <input
                    type="checkbox"
                    checked={cell.unlimited}
                    onChange={(e) => { setDraft({ ...draft, [f.key]: { ...cell, unlimited: e.target.checked } }); setStatus(""); }}
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
                onChange={(e) => { setDraft({ ...draft, [f.key]: { ...cell, value: e.target.value } }); setStatus(""); }}
              />
              <div className="control-field-desc">{f.hint}</div>
            </div>
          );
        })}
        <div className="mobile-api-row">
          <button className="mobile-api-button" type="button" onClick={() => void save()}>Save risk caps</button>
          <button className="mobile-api-button ghost" type="button" onClick={() => void reset()}>Reset to defaults</button>
        </div>
        {status && <div className="control-field-desc" style={{ color: "var(--success)" }}>{status}</div>}
        {rc && (
          <div className="control-field-desc">
            Effective now — concurrent: <strong>{fmt(rc.max_concurrent_trades)}</strong>, loss cap:{" "}
            <strong>{rc.max_loss_cap_usd == null ? "∞" : `$${rc.max_loss_cap_usd}`}</strong>, exposure:{" "}
            <strong>{fmt(rc.max_total_exposure_lots)}</strong> lots, drawdown:{" "}
            <strong>{rc.max_drawdown_pct == null ? "∞" : `${rc.max_drawdown_pct}%`}</strong>.
          </div>
        )}
      </div>
    </GlassPanel>
  );
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

/* ── CAS Forex — Settings & Owner Control ── */

import { useState } from "react";
import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import { NotificationSubscriptionPanel } from "../components/NotificationSubscriptionPanel";
import { WebhookSubscriptionPanel } from "../components/WebhookSubscriptionPanel";
import { getApiBase, resetApiBase, setApiBase } from "../data/api";
import type { DashboardState } from "../types/evidence";

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

export function SettingsPage({ state }: SettingsPageProps) {
  const oc = state.ownerControl;
  const ab = state.authorityBoundary;
  const gates = state.runtimeGates;
  const ai = state.aiModel;
  const brokers = state.brokerCandidates ?? [];

  return (
    <div className="settings-page">
      <MobileApiPanel />

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
                    disabled
                    style={isLive ? { borderColor: "var(--danger-dim)", opacity: 0.6 } : undefined}
                    title={`${m.label}${isLive ? " — LIVE BLOCKED: NOT LICENSED" : ""}`}
                  >
                    {m.label}
                    {isLive && <span style={{ color: "var(--danger)", marginLeft: 4, fontSize: "0.6rem" }}>BLOCKED</span>}
                  </button>
                );
              })}
            </div>
            {oc?.live_requested && (
              <div style={{ marginTop: 8, padding: "6px 10px", background: "var(--danger-dim)", borderRadius: "var(--radius-sm)", fontSize: "0.72rem", color: "var(--danger)" }}>
                AI_FULL_AUTO_LIVE_REQUESTED: owner has requested full live autonomy, but live trading, broker ACCEPT, and payment movement remain NOT LICENSED.
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
              <ControlField label="Live Trading" value="NOT LICENSED" danger description="Live trading, broker ACCEPT, and payment movement remain locked regardless of autonomy mode." />
            </div>
          </div>
        </div>
      </GlassPanel>


      {/* ── Authority Boundary ── */}
      <GlassPanel title="Authority Boundary" subtitle="Owner-controlled live-money gates and edge status" variant="danger">
        <div className="control-grid">
          <ControlField label="Operating Mode" value={ab?.operating_mode ?? "READ_ONLY_PAPER_RESEARCH"} mono />
          <ControlField label="Trading Edge" value={ab?.trading_edge_status ?? "OPEN"} danger description="No deployable income edge is licensed yet." />
          <ControlField label="Live Trading" value={ab?.live_trading_status ?? "CURRENTLY NOT LICENSED"} danger />
          <ControlField label="Broker ACCEPT" value={ab?.broker_accept_status ?? "CURRENTLY NOT LICENSED"} danger />
          <ControlField label="Auto-Deposit" value={ab?.auto_deposit_status ?? "CURRENTLY NOT LICENSED"} danger />
          <ControlField label="Debit/Card/Bank Movement" value={ab?.debit_card_bank_movement_status ?? "CURRENTLY NOT LICENSED"} danger />
          <ControlField label="Payout Automation" value={ab?.payout_automation_status ?? "CURRENTLY NOT LICENSED"} danger />
          <ControlField label="Can Move Money" value={ab?.can_move_money ? "YES" : "NO"} danger={Boolean(ab?.can_move_money)} />
          <ControlField label="Live Execution Runtime" value={ab?.live_execution_runtime_locked === false ? "OWNER-AUTHORIZED" : "PENDING OWNER ENABLE"} danger={ab?.live_execution_runtime_locked !== false} description="Broker bridge permits live execution only when owner flag + credentials + broker config are present." />
        </div>
        <div style={{ marginTop: 12, padding: "8px 12px", background: "var(--danger-dim)", borderRadius: "var(--radius-sm)", fontSize: "0.72rem", color: "var(--danger)" }}>
          {ab?.claim_boundary ?? "Research/paper cockpit runs now. Live-money capabilities are owner-controlled and become AUTHORIZED only when owner flags, credentials, and provider config are present."}
        </div>
      </GlassPanel>

      {/* ── Runtime Gates ── */}
      <GlassPanel title="Path to Authorize Everything" subtitle="Every live-money feature lists missing owner/config requirements">
        <div style={{ marginBottom: 10, fontSize: "0.78rem", color: "var(--text-secondary)" }}>
          {gates?.summary ?? "Owner-controlled runtime gates are loading."}
        </div>
        <div className="control-grid">
          {Object.values(gates?.decisions ?? {}).map((g) => (
            <ControlField
              key={g.capability}
              label={g.capability.replace(/_/g, " ")}
              value={g.authorized ? "AUTHORIZED" : g.status}
              danger={!g.authorized}
              description={g.authorized ? "Owner enable + credentials + provider config satisfied." : g.next_action}
            />
          ))}
        </div>
      </GlassPanel>

      {/* ── AI Model Control ── */}
      <GlassPanel title="AI Model Control" subtitle="Open-weight/frontier LLMs under CAS Harness + PCBA">
        <div className="control-grid">
          <ControlField label="Enabled" value={ai?.enabled ? "YES" : "NO"} danger={!ai?.enabled} />
          <ControlField label="Backend" value={ai?.backend ?? "ollama"} mono />
          <ControlField label="Model" value={ai?.model_name ?? "llama3.1:70b-instruct"} mono />
          <ControlField label="API Key Present" value={ai?.has_api_key ? "YES" : "NO"} danger={!ai?.has_api_key && (ai?.backend ?? "").startsWith("frontier_")} />
          <ControlField label="Control Plane" value={ai?.control_plane ?? "CAS_HARNESS_PCBA"} mono />
          <ControlField label="PCBA Guard" value={ai?.pcba_guard_enabled ? "ENABLED" : "DISABLED"} danger={!ai?.pcba_guard_enabled} />
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
          <LegalGate label="CAS_FOREX_ACCOUNT_AUTH_ACK" met={false} detail="Account authorization acknowledgment required" />
          <LegalGate label="CAS_FOREX_SOURCE_OF_FUNDS_ACK" met={false} detail="Source-of-funds acknowledgment required" />
          <LegalGate label="Account Type" met={false} detail="Not verified — required before live eligibility" />
          <LegalGate label="Broker Terminal Proof" met={false} detail="30-day paper proof required (1/30)" />
          <LegalGate label="WORM Evidence Anchoring" met={false} detail="UNAVAILABLE — local hash chain only" />
        </div>
        <div style={{ marginTop: 12, padding: "8px 12px", background: "var(--danger-dim)", borderRadius: "var(--radius-sm)", fontSize: "0.72rem", color: "var(--danger)" }}>
          Live/payment paths are owner-controlled. They become AUTHORIZED only when the matching owner flag, credentials, broker/payment provider config, and account acknowledgments are present.
        </div>
      </GlassPanel>

      {/* ── Broker Settings ── */}
      <GlassPanel title="Broker Configuration">
        <div className="control-grid">
          <ControlField label="Broker Mode" value="PAPER_MT5" mono />
          <ControlField label="MT5 Terminal" value="Demo Only" />
          <ControlField label="MT4 Mailbox" value="Not configured" />
          <ControlField label="Broker Health" value="DISCONNECTED" danger />
          <ControlField label="Live Broker" value="NOT LICENSED" danger />
        </div>
      </GlassPanel>
    </div>
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

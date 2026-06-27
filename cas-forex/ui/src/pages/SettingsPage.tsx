/* ── CAS Forex — Settings & Owner Control ── */

import { useEffect, useState } from "react";
import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import { NotificationSubscriptionPanel } from "../components/NotificationSubscriptionPanel";
import { WebhookSubscriptionPanel } from "../components/WebhookSubscriptionPanel";
import {
  getApiBase,
  resetApiBase,
  setApiBase,
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
} from "../data/api";
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

      {/* ── Go Live — owner switches (turn the live-trading gate flags ON) ── */}
      <GoLivePanel />

      {/* ── Owner risk control — set any cap, or remove it ── */}
      <RiskControlPanel />

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

  return (
    <GlassPanel
      title="Go Live — Owner Switches"
      subtitle="Turn the live-trading gate flags ON from here — no .env edits"
      variant={authorized ? "default" : "danger"}
    >
      {/* Live readout: AUTHORIZED vs exactly what is still missing */}
      <div
        style={{
          marginBottom: 14,
          padding: "10px 12px",
          borderRadius: "var(--radius-sm)",
          background: authorized ? "rgba(34,197,94,0.12)" : "var(--danger-dim)",
          border: `1px solid ${authorized ? "rgba(34,197,94,0.4)" : "var(--danger-dim)"}`,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <StatusChip
            label={authorized ? "LIVE-TRADING GATE: AUTHORIZED" : "LIVE-TRADING GATE: NOT YET"}
            variant={authorized ? "success" : "danger"}
            size="sm"
          />
        </div>
        {le && !authorized && missing.length > 0 && (
          <div style={{ marginTop: 8 }}>
            <div className="control-field-desc" style={{ color: "var(--danger)", fontWeight: 600 }}>
              Still missing before the gate authorizes:
            </div>
            <ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>
              {missing.map((m) => (
                <li key={m} className="control-field-desc" style={{ color: "var(--danger)" }}>{m}</li>
              ))}
            </ul>
          </div>
        )}
        {le == null && (
          <div className="control-field-desc" style={{ marginTop: 6 }}>Loading live-enable state…</div>
        )}
      </div>

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
        <strong>What these switches do:</strong> they satisfy the live-trading gate — they do
        <strong> not</strong> place any order by themselves. A real order also needs a
        <strong> connected broker feed</strong> and a <strong>running dispatch loop</strong> (neither
        runs automatically yet), and the broker bridge re-checks authorization at order time
        (fail-closed). So flipping every switch here turns the gate green, but it is never one
        accidental tap from real money.
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
      setStatus("Reset to config / env defaults.");
    } catch {
      setStatus("Couldn't reset.");
    } finally {
      setBusyKey("");
    }
  }

  const allGreen = auth?.all_real_money_authorized ?? false;

  return (
    <GlassPanel
      title="Path to Authorize Everything — Owner Switches"
      subtitle="Flip every live-money capability ON from here — no .env, no restart"
      variant={allGreen ? "default" : "danger"}
    >
      <div style={{ marginBottom: 12, fontSize: "0.78rem", color: "var(--text-secondary)" }}>
        {auth?.summary ?? "Loading owner-controlled capabilities…"}
      </div>

      <div style={{ display: "grid", gap: 4 }}>
        {(auth?.capabilities ?? []).map((cap) => (
          <div key={cap.capability} style={{ padding: "10px 0", borderBottom: "1px solid var(--border-subtle)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
              <span style={{ fontWeight: 700, fontSize: "0.84rem" }}>{cap.title}</span>
              <StatusChip
                label={cap.authorized ? "AUTHORIZED" : "NOT YET"}
                variant={cap.authorized ? "success" : "danger"}
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
              <div className="control-field-desc" style={{ color: "var(--danger)", marginTop: 4 }}>
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
        key above and a running process; the provider/bridge re-checks at action time. Flipping every switch turns the gate
        green, but it is never one accidental tap from real money.
      </div>
    </GlassPanel>
  );
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

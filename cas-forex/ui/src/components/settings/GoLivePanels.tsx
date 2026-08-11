/* Extracted from pages/SettingsPage.tsx (settings decomposition, slice 3). */

import { emitLiveMoneyProgressionRefresh } from "./liveMoneyProgression";
import { GlassPanel } from "../../components/GlassPanel";
import { MoneyMovementSetupStatus } from "../../components/MoneyMovementSetupStatus";
import { StatusChip } from "../../components/StatusChip";
import { AuthorizationPatch, AuthorizationState, LiveEnableKey, LiveEnableState, fetchAuthorization, fetchLiveEnable, resetLiveEnable, updateAuthorization, updateLiveEnable } from "../../data/api";
import { AuthorityModelStrip } from "./AuthorityModelStrip";
import { ToggleSwitch } from "./ToggleSwitch";
import { GO_LIVE_GROUPS, armConfirmationForPatch, confirmRequiredMessage, requestArmConfirmation } from "./goLiveShared";
import { useEffect, useState } from "react";

export function GoLivePanel() {
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


export function AuthorizePanel() {
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


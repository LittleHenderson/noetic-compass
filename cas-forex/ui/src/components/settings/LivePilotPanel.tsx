/* Extracted from pages/SettingsPage.tsx (settings decomposition, slice 3). */

import { emitLiveMoneyProgressionRefresh } from "./liveMoneyProgression";
import { GlassPanel } from "../../components/GlassPanel";
import { StatusChip } from "../../components/StatusChip";
import { LivePilotPolicy, LivePilotUpdate, fetchLivePilotPolicy, resetLivePilotPolicy, updateLivePilotPolicy } from "../../data/api";
import { LIVE_PILOT_CHECKS, LIVE_PILOT_LEGACY_FIELDS, LIVE_PILOT_NUMBER_FIELDS, LIVE_PILOT_RISK_FIELDS } from "./goLiveShared";
import { useEffect, useState } from "react";

export function LivePilotPanel({ initialPolicy }: { initialPolicy?: LivePilotPolicy }) {
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


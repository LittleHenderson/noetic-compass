/* Extracted from pages/SettingsPage.tsx (settings decomposition, slice 3). */

import { emitLiveMoneyProgressionRefresh } from "./liveMoneyProgression";
import { GlassPanel } from "../../components/GlassPanel";
import { StatusChip } from "../../components/StatusChip";
import { BrokerRealityReview, BrokerRealityUpdate, fetchBrokerRealityReview, resetBrokerRealityReview, updateBrokerRealityReview } from "../../data/api";
import { BROKER_REALITY_CHECKS, BROKER_REALITY_TEXT_FIELDS } from "./goLiveShared";
import { useEffect, useState } from "react";

export function BrokerRealityPanel({ initialReview }: { initialReview?: BrokerRealityReview }) {
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


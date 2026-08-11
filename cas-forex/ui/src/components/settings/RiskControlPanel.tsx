/* Extracted from pages/SettingsPage.tsx (settings decomposition, slice 4). */

import { GlassPanel } from "../../components/GlassPanel";
import { StatusChip } from "../../components/StatusChip";
import { RiskControlAssessment, RiskControlPatch, RiskControlState, fetchRiskControl, previewResetRiskControl, previewRiskControl, resetRiskControl, updateRiskControl } from "../../data/api";
import { useEffect, useState } from "react";

export function RiskControlPanelModern() {
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


export const RISK_FIELDS = [
  { key: "max_concurrent_trades", label: "Max Concurrent Trades", hint: "How many trades can be open at once. Toggle Unlimited to remove the cap." },
  { key: "max_loss_cap_usd", label: "Max Loss Cap (USD)", hint: "Floating loss that blocks new trades. Unlimited = no cap." },
  { key: "max_total_exposure_lots", label: "Max Total Exposure (lots)", hint: "Total open lots across the whole book." },
  { key: "max_drawdown_pct", label: "Max Drawdown (%)", hint: "Drawdown from the equity peak that blocks new trades." },
] as const;


export type RiskKey = (typeof RISK_FIELDS)[number]["key"];

// RiskControlPanel (legacy) deleted: it was dead code behind the tautology
// `if (Date.now() >= 0) return <RiskControlPanelModern />` - ~90 unreachable
// lines that also violated the Rules of Hooks. RiskControlPanelModern is the
// only risk-control surface.

export function emptyRiskDraft(): Record<RiskKey, { value: string; unlimited: boolean }> {
  return {
    max_concurrent_trades: { value: "", unlimited: false },
    max_total_exposure_lots: { value: "", unlimited: false },
    max_loss_cap_usd: { value: "", unlimited: false },
    max_drawdown_pct: { value: "", unlimited: false },
  };
}


export function riskFieldLabel(key: RiskKey): string {
  return RISK_FIELDS.find((field) => field.key === key)?.label ?? key;
}


export function formatRiskChangeValue(value: number | null): string {
  return value == null ? "Unlimited" : String(value);
}


export function normalizeConfirm(value: string): string {
  return value.trim().toUpperCase().replace(/\s+/g, " ");
}


export function riskStatusColor(status: string): string {
  return status.startsWith("Couldn't")
    || status.startsWith("Type exactly")
    || status.includes("must be")
    || status.toLowerCase().includes("cooldown")
    ? "var(--danger)"
    : "var(--success)";
}


export function riskActionDetail(error: unknown): {
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


export function riskActionMessage(
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


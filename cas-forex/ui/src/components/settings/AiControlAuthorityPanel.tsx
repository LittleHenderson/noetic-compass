/* Extracted from pages/SettingsPage.tsx (settings decomposition, slice 4). */

import { EdgeThresholdControl } from "../../components/EdgeThresholdControl";
import { GlassPanel } from "../../components/GlassPanel";
import { ControlField } from "../../components/settings/ControlField";
import { formatDialBound, formatIsoForDisplay, formatUnknownValue } from "../../components/settings/formatters";
import { AiControlAuthorityState, fetchAiControlAuthority } from "../../data/api";
import { useEffect, useState } from "react";

const EDGE_THRESHOLD_KEY = "cas_forex_edge_threshold";
const EDGE_THRESHOLD_DEFAULT = 0.65;

export function AiControlAuthorityPanel() {
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


export const AI_DIAL_LABELS: Record<string, { label: string; detail: string }> = {
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


export function EdgeThresholdPanel() {
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


export function readStoredEdgeThreshold(): number {
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

